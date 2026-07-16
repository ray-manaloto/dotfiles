"""Prove every pinned `[bootstrap.packages]` version is still installable.

`dotfiles-setup apt-pins` (wrapped by `mise run verify-apt-pins`) answers, in
~30 seconds locally, the one question a pin can fail at: **is that exact
version still resolvable, together with all the others?** Today the only thing
that answers it is a cold base rebuild — ~2.5h of CI (`feedback_ci_build_
duration_baseline`). That round-trip is what this replaces; see
`.claude/rules/local-devcontainer-first.md`.

Why a container + apt's SOLVER, and not an index lookup
-------------------------------------------------------
`apt_repo.py` can already answer "is version V of package P in the index?"
in-process, with no docker. That check is **not sufficient**, and the gap is
the whole reason this module exists. Probed in a clean room 2026-07-16 against
the digest-pinned base:

    apt-get install --simulate curl=8.18.0-1ubuntu2      -> FAIL
      curl : Depends: libcurl4t64 (= 8.18.0-1ubuntu2)
             but 8.18.0-1ubuntu2.3 is to be installed

That version IS in the index (`resolute/main`, priority 500) — an index lookup
calls it present and green. It is nonetheless uninstallable, because `curl`
hard-depends on its co-versioned `libcurl4t64` and apt will not drag that
dependency below its candidate. Only the solver sees this. A probe that cannot
observe the failure mode it exists to catch is decoration
(`.claude/rules/probes-need-a-control-arm.md`), so we run the real solver.

`--simulate` is what keeps it cheap: apt resolves against the index and prints
the plan without downloading a single .deb.

Why a throwaway base container, not the running devcontainer
------------------------------------------------------------
The devcontainer already HAS these packages installed at whatever the last base
build picked, so simulating a pin below an installed version reports FAIL for
"apt refuses to downgrade" — a false negative that has nothing to do with the
pin's validity (measured 2026-07-16: identical pins passed clean-room and
failed in-container). The base build's environment is a bare image, so that is
what we reproduce. `docker run --rm` on an ephemeral probe container is not
devcontainer lifecycle, so `.claude/rules/do-not.md` #3 (use @devcontainers/cli
for lifecycle) does not apply — nothing here creates, mutates, or inspects the
devcontainer.

The probe mirrors the Dockerfile's real base-stage sequence deliberately: it
seeds curl/gnupg/ca-certificates UNPINNED, adds apt.llvm.org under the same
fingerprint check, and only then simulates. That ordering is load-bearing —
the seed installs those packages at *candidate* version before
`mise bootstrap packages apply` ever sees the pins, so a pin below candidate is
a build failure in reality too. A probe on a pristine image would miss it.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

from dotfiles_setup.bootstrap_packages import APT_PREFIX

#: `[bootstrap.packages]` values meaning "any installed version satisfies".
UNPINNED = "latest"

#: Where the declarations and the build inputs live, relative to project root.
MISE_SYSTEM_TOML = Path(".devcontainer/mise-system.toml")
DOCKERFILE = Path(".devcontainer/Dockerfile")

#: The probe runs apt's solver only; no .deb is fetched. Two `apt-get update`s
#: against archive.ubuntu.com + apt.llvm.org dominate the wall clock (~30s).
_PROBE_TIMEOUT_S = 600.0

_ARG_RE = r"^ARG\s+{name}=(?P<value>\S+)\s*$"


def dockerfile_arg(dockerfile_text: str, name: str) -> str:
    """Return the default value of a Dockerfile top-level `ARG name=value`.

    The pins must be probed against the SAME base image and the SAME signing
    key the build uses; reading both from the Dockerfile keeps this gate from
    drifting into testing an image nobody builds.
    """
    match = re.search(
        _ARG_RE.format(name=re.escape(name)), dockerfile_text, re.MULTILINE
    )
    if match is None:
        msg = f"no top-level `ARG {name}=...` in the Dockerfile"
        raise ValueError(msg)
    return match.group("value")


def pinned_apt_packages(mise_system_toml: Path) -> dict[str, str]:
    """Return `{package: version}` for every PINNED `apt:` bootstrap entry.

    `"latest"` entries are excluded — they are unpinned by construction and
    have nothing to verify. Returned in declaration order.
    """
    data = tomllib.loads(mise_system_toml.read_text())
    packages = data.get("bootstrap", {}).get("packages", {})
    return {
        key[len(APT_PREFIX) :]: value
        for key, value in packages.items()
        if key.startswith(APT_PREFIX) and value != UNPINNED
    }


def unpinned_apt_packages(mise_system_toml: Path) -> list[str]:
    """Return the `apt:` bootstrap entries still on `"latest"`, sorted."""
    data = tomllib.loads(mise_system_toml.read_text())
    packages = data.get("bootstrap", {}).get("packages", {})
    return sorted(
        key[len(APT_PREFIX) :]
        for key, value in packages.items()
        if key.startswith(APT_PREFIX) and value == UNPINNED
    )


def probe_script(pins: dict[str, str], fingerprint: str) -> str:
    """Render the bash the probe container runs.

    Mirrors the Dockerfile base stage: seed the unpinned bootstrap tools, add
    apt.llvm.org behind the pinned-fingerprint check, then simulate every pin
    in ONE transaction — which is how `mise bootstrap packages apply` installs
    them, and the only way a cross-package conflict shows up.
    """
    specs = " ".join(f"{name}={version}" for name, version in sorted(pins.items()))
    return f"""set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends -qq curl gnupg ca-certificates
install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://apt.llvm.org/llvm-snapshot.gpg.key \
  -o /etc/apt/keyrings/apt-llvm-org.asc
actual="$(gpg --show-keys --with-colons --with-fingerprint \
  /etc/apt/keyrings/apt-llvm-org.asc | awk -F: '/^fpr:/{{print $10; exit}}')"
if [ "$actual" != "{fingerprint}" ]; then
  echo "FAIL: apt.llvm.org key fingerprint $actual != pinned {fingerprint}" >&2
  exit 1
fi
codename="$(. /etc/os-release && echo "$VERSION_CODENAME")"
printf 'Types: deb\\nURIs: https://apt.llvm.org/%s/\\nSuites: llvm-toolchain-%s-22\\n\
Components: main\\nSigned-By: /etc/apt/keyrings/apt-llvm-org.asc\\n' \
  "$codename" "$codename" > /etc/apt/sources.list.d/apt-llvm-org.sources
apt-get update -qq
apt-get install --simulate -qq {specs} >/dev/null
echo "APT_PINS_OK"
"""


def docker_command(base_image: str, script: str) -> list[str]:
    """Build the throwaway-probe `docker run` argv.

    `--platform linux/amd64` because the pins are resolved for the image's
    arch, not this ARM Mac's (`AGENTS.md` R3).
    """
    return [
        "docker",
        "run",
        "--rm",
        "--platform",
        "linux/amd64",
        base_image,
        "bash",
        "-c",
        script,
    ]


@dataclass
class PinProbeResult:
    """The outcome of one pin-resolvability probe."""

    base_image: str
    pinned: int
    unpinned: list[str]
    ok: bool
    detail: str

    def render(self) -> str:
        """Render as a readable report."""
        lines = [
            "apt pin resolvability — [bootstrap.packages]",
            "",
            f"  base image : {self.base_image}",
            f"  pinned     : {self.pinned} package(s) simulated in one transaction",
            f'  unpinned   : {len(self.unpinned)} still "latest"'
            + (f" ({', '.join(self.unpinned)})" if self.unpinned else ""),
            "",
        ]
        verdict = (
            "PASS — every pinned version resolves together." if self.ok else "FAIL"
        )
        lines.append(verdict)
        if not self.ok:
            lines.extend(["", self.detail])
        return "\n".join(lines)


def apt_pins_main(project_root: Path, *, json_output: bool = False) -> int:
    """Entry point for `dotfiles-setup apt-pins`."""
    mise_system = project_root / MISE_SYSTEM_TOML
    dockerfile_text = (project_root / DOCKERFILE).read_text()
    pins = pinned_apt_packages(mise_system)
    unpinned = unpinned_apt_packages(mise_system)
    base_image = dockerfile_arg(dockerfile_text, "BASE_IMAGE")
    fingerprint = dockerfile_arg(dockerfile_text, "LLVM_APT_SIGNING_FINGERPRINT")

    if not pins:
        sys.stderr.write("no pinned apt: entries in [bootstrap.packages]\n")
        return 1
    if shutil.which("docker") is None:
        sys.stderr.write("docker not found; cannot run the pin probe\n")
        return 1

    proc = subprocess.run(
        docker_command(base_image, probe_script(pins, fingerprint)),
        capture_output=True,
        text=True,
        timeout=_PROBE_TIMEOUT_S,
        check=False,
    )
    ok = proc.returncode == 0 and "APT_PINS_OK" in proc.stdout
    result = PinProbeResult(
        base_image=base_image,
        pinned=len(pins),
        unpinned=unpinned,
        ok=ok,
        detail=(proc.stderr or proc.stdout).strip(),
    )
    if json_output:
        sys.stdout.write(json.dumps(asdict(result), indent=2) + "\n")
    else:
        sys.stdout.write(result.render() + "\n")
    return 0 if ok else 1
