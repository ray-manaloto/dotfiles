# Copyright (c) 2026 Raymond Manaloto
"""Native, self-updating claude / codex / agy inside the devcontainer.

Ray's ruling (2026-10-01): the Mac and the devcontainer both get the vendors'
NATIVE installers for all three CLIs, and inside the container they
SELF-UPDATE exactly as on the Mac. No mise or npm copy of any of them exists
anywhere. Spec: ``docs/specs/native-cli-devcontainer-2026-10-01.md``.

Two verbs, both run as the container user:

* :func:`install` — called from ``.devcontainer/scripts/on-create.sh``. The
  home directory is a persistent named volume, which hides anything an image
  layer baked under ``$HOME`` once the volume exists. So the install runs at
  container-CREATE time, after the volume is mounted, and lands in the volume
  (``~/.local/bin``, ``~/.local/share/claude``, ``~/.codex/packages``) where the
  vendor updaters can rewrite it and where it survives a re-create. A tool
  already present is left alone: from then on its own updater owns it.
* :func:`check` — called from ``scripts/devcontainer-smoke.sh`` tier 3. Asserts
  PROVENANCE, not a version: ``command -v <tool>`` is the native path, its
  realpath sits under the vendor's own install root (not a mise shim, not an
  npm tree), ``<tool> --version`` exits 0, and ``mise ls`` carries no key that
  provides any of the three.

Every installer is fetched over https only (``curl --proto =https``) to a file,
never piped, and run with a minimal environment so the Doppler-injected
container credentials never reach a vendor script.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

#: A runner takes ``(argv, env)`` and returns ``(rc, combined output)``.
Runner = Callable[[Sequence[str], Mapping[str, str]], tuple[int, str]]

_TIMEOUT_S = 600.0

#: The environment names an installer or a probe may inherit. Everything else —
#: notably the Doppler secrets ``runArgs --env-file`` injects — stays out.
_ENV_PASSTHROUGH = ("HOME", "PATH", "USER", "LOGNAME", "LANG", "SHELL", "TMPDIR")

#: ``MISE_*`` also passes: the container's ``curl`` (and every other tool the
#: installers call) is a mise shim, which cannot resolve without the system
#: config dir / ignored-paths settings. None of them is a credential.
_ENV_PASSTHROUGH_PREFIX = "MISE_"

#: Probe-only updater switches, so ``--version`` never triggers an update
#: mid-smoke. They are set for the probe subprocess alone; the tools' normal
#: runs keep self-updating (ruling 2).
_PROBE_ENV = {"DISABLE_AUTOUPDATER": "1", "AGY_CLI_DISABLE_AUTO_UPDATE": "true"}

#: Normalised mise tool names that would provide one of the three binaries.
_FORBIDDEN_MISE_NAMES = frozenset(
    {"claude", "claude-code", "codex", "agy", "antigravity", "antigravity-cli"}
)


@dataclass(frozen=True)
class NativeCli:
    """One vendor CLI and the facts its install and provenance check need."""

    name: str
    installer_url: str
    interpreter: str
    #: The realpath of ``~/.local/bin/<name>`` must sit under this, relative to
    #: ``$HOME``: the vendor's own install tree.
    install_root: str
    installer_env: Mapping[str, str] = field(default_factory=dict)
    #: A flat binary (agy) must be a regular file AT the native path; a symlink
    #: there would resolve its own root through itself and prove nothing.
    flat: bool = False


#: Measured 2026-10-01 in throwaway containers on the published image, as the
#: container user on a fresh home volume (amd64 and arm64): each installer
#: exits 0 and leaves the layout recorded here.
TOOLS: tuple[NativeCli, ...] = (
    NativeCli(
        name="claude",
        installer_url="https://claude.ai/install.sh",
        interpreter="bash",
        install_root=".local/share/claude/versions",
    ),
    NativeCli(
        name="codex",
        installer_url="https://chatgpt.com/codex/install.sh",
        interpreter="sh",
        install_root=".codex/packages/standalone",
        installer_env={"CODEX_NON_INTERACTIVE": "1"},
    ),
    NativeCli(
        name="agy",
        installer_url="https://antigravity.google/cli/install.sh",
        interpreter="bash",
        # agy is a flat binary: the native path IS its own install root.
        install_root=".local/bin/agy",
        flat=True,
    ),
)


def _minimal_env(base: Mapping[str, str], extra: Mapping[str, str]) -> dict[str, str]:
    env = {
        k: v
        for k, v in base.items()
        if k in _ENV_PASSTHROUGH or k.startswith(_ENV_PASSTHROUGH_PREFIX)
    }
    env.update(extra)
    return env


def _default_run(argv: Sequence[str], env: Mapping[str, str]) -> tuple[int, str]:
    """Run ``argv`` with exactly ``env``; failures collapse to a non-zero rc."""
    try:
        # Fixed argv, no shell; argv[0] is a vendor path or a resolved tool.
        done = subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_S,
            env=dict(env),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return 124, f"{argv[0]}: timed out after {_TIMEOUT_S:g}s"
    except OSError as exc:
        return 127, f"{argv[0]}: {exc}"
    return done.returncode, (done.stdout or "") + (done.stderr or "")


def native_path(tool: NativeCli, home: Path) -> Path:
    """Where the vendor installer puts the user-facing binary."""
    return home / ".local" / "bin" / tool.name


def vendor_finding(tool: NativeCli, home: Path) -> str | None:
    """Why ``~/.local/bin/<tool>`` is not the vendor's install, or ``None``."""
    target = native_path(tool, home)
    if not target.exists():
        return f"{tool.name}: {target} is missing"
    if tool.flat and (target.is_symlink() or not target.is_file()):
        return f"{tool.name}: {target} must be the vendor's flat binary, not a link"
    real = target.resolve()
    root = (home / tool.install_root).resolve()
    if not real.is_relative_to(root):
        return f"{tool.name}: {target} -> {real}, outside the vendor root {root}"
    return None


def _mise_name(key: str) -> str:
    """Normalise a mise tool key: drop the backend and any npm scope/owner."""
    bare = key.split(":", 1)[1] if ":" in key else key
    return bare.rsplit("/", 1)[-1]


def install_one(
    tool: NativeCli,
    *,
    home: Path,
    environ: Mapping[str, str],
    run: Runner = _default_run,
) -> int:
    """Install ``tool`` with its vendor installer unless it is already present.

    Returns 0 when the tool is present afterwards, non-zero otherwise.
    """
    target = native_path(tool, home)
    stale = vendor_finding(tool, home)
    if stale is None:
        logger.info("%s: present at %s; its self-updater owns it", tool.name, target)
        return 0
    if target.is_symlink() or target.exists():
        # A non-vendor file at the native path: on an existing home volume this
        # is the retired chezmoi `mise exec claude-code` wrapper, or a stale
        # link. Move it aside (never delete) so the vendor installer owns the
        # path; the vendor installers would otherwise skip or refuse it.
        aside = target.with_name(f".{tool.name}.pre-native")
        target.replace(aside)
        logger.info("%s: %s; moved it to %s", tool.name, stale, aside)
    curl = shutil.which("curl", path=environ.get("PATH"))
    if curl is None:
        logger.error("%s: curl not found on PATH; cannot fetch installer", tool.name)
        return 127
    env = _minimal_env(environ, tool.installer_env)
    with tempfile.TemporaryDirectory(prefix=f"native-{tool.name}-") as tmp:
        script = Path(tmp) / "install.sh"
        rc, out = run(
            [
                curl,
                "--proto",
                "=https",
                "--tlsv1.2",
                "-fsSL",
                "-o",
                str(script),
                tool.installer_url,
            ],
            env,
        )
        if rc != 0:
            logger.error(
                "%s: fetching %s failed rc=%s: %s",
                tool.name,
                tool.installer_url,
                rc,
                out,
            )
            return rc
        logger.info(
            "%s: running %s (%s)", tool.name, tool.installer_url, tool.interpreter
        )
        rc, out = run([tool.interpreter, str(script)], env)
        logger.info("%s", out.rstrip())
        if rc != 0:
            logger.error("%s: installer exited rc=%s", tool.name, rc)
            return rc
    if (finding := vendor_finding(tool, home)) is not None:
        logger.error("%s: installer exited 0 but %s", tool.name, finding)
        return 1
    return 0


def install(
    *,
    home: Path,
    environ: Mapping[str, str],
    tools: Sequence[NativeCli] = TOOLS,
    run: Runner = _default_run,
) -> int:
    """Install every missing tool; the rc is the first failure's, else 0."""
    failures = [
        rc
        for tool in tools
        if (rc := install_one(tool, home=home, environ=environ, run=run)) != 0
    ]
    return failures[0] if failures else 0


def check_one(
    tool: NativeCli,
    *,
    home: Path,
    environ: Mapping[str, str],
    run: Runner = _default_run,
) -> list[str]:
    """Return the provenance findings for one tool; empty means native."""
    expected = native_path(tool, home)
    found = shutil.which(tool.name, path=environ.get("PATH"))
    if found is None:
        return [f"{tool.name}: not on PATH (expected {expected})"]
    if Path(found) != expected:
        return [f"{tool.name}: PATH resolves {found}, expected the native {expected}"]
    if (finding := vendor_finding(tool, home)) is not None:
        return [finding]
    real = expected.resolve()
    rc, out = run([str(expected), "--version"], _minimal_env(environ, _PROBE_ENV))
    if rc != 0:
        return [
            f"{tool.name}: `{expected} --version` exited rc={rc}: {out.strip()[:200]}"
        ]
    logger.info("%s: native %s -> %s (%s)", tool.name, expected, real, out.strip()[:80])
    return []


def mise_findings(
    *, environ: Mapping[str, str], run: Runner = _default_run
) -> list[str]:
    """Return a finding per active mise tool that would provide a vendor CLI."""
    mise = shutil.which("mise", path=environ.get("PATH"))
    if mise is None:
        return ["mise: not on PATH, so `mise ls` could not be asked"]
    rc, out = run([mise, "ls", "--current", "--json"], dict(environ))
    if rc != 0:
        return [f"mise ls --current --json exited rc={rc}: {out.strip()[:200]}"]
    try:
        payload = json.loads(out)
    except json.JSONDecodeError as exc:
        return [f"mise ls --current --json was not JSON ({exc}): {out.strip()[:200]}"]
    return [
        f"mise: `{key}` is an active mise tool; the native installer owns it"
        for key in sorted(payload)
        if _mise_name(key) in _FORBIDDEN_MISE_NAMES
    ]


def check(
    *,
    home: Path,
    environ: Mapping[str, str],
    tools: Sequence[NativeCli] = TOOLS,
    run: Runner = _default_run,
) -> int:
    """Log every provenance finding; rc 0 only when there are none."""
    findings = [
        finding
        for tool in tools
        for finding in check_one(tool, home=home, environ=environ, run=run)
    ]
    findings.extend(mise_findings(environ=environ, run=run))
    for finding in findings:
        logger.error("FAIL: %s", finding)
    if findings:
        return 1
    logger.info("OK: %s are native installs", ", ".join(t.name for t in tools))
    return 0


def main(command: str) -> int:
    """Dispatch ``devcontainer native-clis <install|check>``."""
    home = Path(os.environ.get("HOME", str(Path.home())))
    if command == "install":
        return install(home=home, environ=os.environ)
    if command == "check":
        return check(home=home, environ=os.environ)
    logger.error("devcontainer native-clis: pick one of install, check")
    return 2
