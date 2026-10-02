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
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from dotfiles_setup.image import IDENTITY_IMAGE_PATHS

logger = logging.getLogger(__name__)

#: A runner takes ``(argv, env)`` and returns ``(rc, combined output)``.
Runner = Callable[[Sequence[str], Mapping[str, str]], tuple[int, str]]

_TIMEOUT_S = 600.0

#: The environment names an installer or a probe may inherit. Everything else —
#: notably the Doppler secrets ``runArgs --env-file`` injects — stays out.
_ENV_PASSTHROUGH = (
    "HOME",
    "PATH",
    "USER",
    "LOGNAME",
    "LANG",
    "SHELL",
    "TMPDIR",
    # Network plumbing: without these a proxied or TLS-intercepted network
    # fails the fetch the container's own curl passes. A proxy URL CAN carry
    # `user:pass@`; it is the operator's own network config (Doppler injects
    # none of these names today), passed as deliberately as curl itself gets it.
    "HTTPS_PROXY",
    "https_proxy",
    "HTTP_PROXY",
    "http_proxy",
    "NO_PROXY",
    "no_proxy",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "CURL_CA_BUNDLE",
)

#: ``MISE_*`` also passes: the container's ``curl`` (and every other tool the
#: installers call) is a mise shim, which cannot resolve without the system
#: config dir / ignored-paths settings.
_ENV_PASSTHROUGH_PREFIX = "MISE_"

#: ...EXCEPT a credential-shaped ``MISE_*`` name. Doppler injects
#: ``MISE_GITHUB_TOKEN`` into the container (``doctor.toml`` ``[fnox].env_true``),
#: and a bare prefix rule handed it to three unpinned vendor scripts (cold
#: review of 93d70c96, finding 1). A shim needs config paths, never a secret.
_CREDENTIAL_NAME = re.compile(r"TOKEN|SECRET|PASSW|KEY|AUTH|CREDENTIAL|COOKIE")

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
        if k in _ENV_PASSTHROUGH
        or (k.startswith(_ENV_PASSTHROUGH_PREFIX) and not _CREDENTIAL_NAME.search(k))
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


def _move_aside(tool: NativeCli, target: Path, stale: str) -> bool:
    """Move a non-vendor file off the native path; False (logged) when it cannot.

    On an existing home volume this is the retired chezmoi `mise exec
    claude-code` wrapper, or a stale link. It is moved aside — never deleted,
    never over an earlier backup — so the vendor installer owns the path; the
    vendor installers would otherwise skip or refuse it.
    """
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    aside = target.with_name(f".{tool.name}.pre-native-{stamp}")
    try:
        target.rename(aside)
    except OSError:
        logger.exception("%s: %s, and moving it aside failed", tool.name, stale)
        return False
    logger.info("%s: %s; moved it to %s", tool.name, stale, aside)
    return True


def _fetch_and_run(tool: NativeCli, *, environ: Mapping[str, str], run: Runner) -> int:
    """Fetch the vendor installer https-only to a file, then run it; its rc."""
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
    return 0


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
    if (target.is_symlink() or target.exists()) and not _move_aside(
        tool, target, stale
    ):
        return 1
    rc = _fetch_and_run(tool, environ=environ, run=run)
    if rc != 0:
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
    found_path = Path(found)
    if (found_path.name, found_path.parent.resolve()) != (
        expected.name,
        expected.parent.resolve(),
    ):
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


MiseTools = Mapping[str, Sequence[Mapping[str, object]]]


def mise_tools(
    *, environ: Mapping[str, str], run: Runner = _default_run
) -> tuple[MiseTools, list[str]]:
    """``mise ls --json`` (installed OR active), or the finding why it failed.

    No ``--current``: an inactive copy in the overlay's installs dir is still a
    second, non-updating install. Runs under the same minimal env as the
    installers.
    """
    mise = shutil.which("mise", path=environ.get("PATH"))
    if mise is None:
        return {}, ["mise: not on PATH, so `mise ls` could not be asked"]
    rc, out = run([mise, "ls", "--json"], _minimal_env(environ, {}))
    if rc != 0:
        return {}, [f"mise ls --json exited rc={rc}: {out.strip()[:200]}"]
    try:
        payload = json.loads(out)
    except json.JSONDecodeError as exc:
        return {}, [f"mise ls --json was not JSON ({exc}): {out.strip()[:200]}"]
    return payload, []


def _forbidden(payload: MiseTools) -> list[str]:
    return sorted(key for key in payload if _mise_name(key) in _FORBIDDEN_MISE_NAMES)


def image_config_files(environ: Mapping[str, str]) -> frozenset[Path]:
    """The image's own mise tool configs, resolved in THIS container.

    The three image build inputs (``IDENTITY_IMAGE_PATHS``, the same map tier 1
    hashes) are COPYed under ``$MISE_SYSTEM_CONFIG_DIR``. Anything a key's
    ``source.path`` names outside this set came from the user's overlay
    (``~/.config/mise/config.toml``) or a ``mise use -g``, not from the base.
    Without ``MISE_SYSTEM_CONFIG_DIR`` nothing counts as baked: fail closed.
    """
    config_dir = environ.get("MISE_SYSTEM_CONFIG_DIR")
    if not config_dir:
        return frozenset()
    root = Path(config_dir)
    system_file = Path(environ.get("MISE_SYSTEM_CONFIG_FILE") or root / "config.toml")
    return frozenset(
        system_file if rel == "@SYS@" else root / rel
        for rel in IDENTITY_IMAGE_PATHS.values()
    )


def _image_source(
    entry: Mapping[str, object], image_configs: frozenset[Path]
) -> str | None:
    """The image config an entry came from, or None when it is not attributable."""
    source = entry.get("source")
    path = source.get("path") if isinstance(source, Mapping) else None
    if not entry.get("install_path") or not isinstance(path, str):
        return None
    return path if Path(path) in image_configs else None


def baked_into_base(payload: MiseTools, image_configs: frozenset[Path]) -> list[str]:
    """Forbidden keys the BASE IMAGE's own config declares (by ``source.path``).

    Such a base predates the native-CLI change: it was built from a config that
    still declared a mise/npm copy, and a container created from it never ran
    `native-clis install`. Asserting provenance there can only fail, and says
    nothing about this change — the same reason tier 1 compares a branch that
    changes an image input against the MERGE-BASE identity.

    Provenance is the ``source.path`` mise reports, NOT ``install_path``: at
    runtime ``MISE_DATA_DIR`` stays ``/usr/local/share/mise`` (Dockerfile ENV),
    so overlay and user installs land outside ``$HOME`` too (cold review of
    fb4c674b, finding 1). An entry with no source or no install path is not
    attributable to the image and is not baked.
    """
    return [
        key
        for key in _forbidden(payload)
        if payload[key]
        and all(_image_source(entry, image_configs) for entry in payload[key])
    ]


def mise_findings(payload: MiseTools) -> list[str]:
    """Return a finding per mise tool that would provide a vendor CLI."""
    return [
        f"mise: `{key}` is a mise tool here; the native installer owns it"
        for key in _forbidden(payload)
    ]


def check(
    *,
    home: Path,
    environ: Mapping[str, str],
    tools: Sequence[NativeCli] = TOOLS,
    run: Runner = _default_run,
) -> int:
    """Log every provenance finding; rc 0 only when there are none.

    A base image that predates the change is a loud SKIP, not a pass and not a
    failure — but only when EVERY forbidden key comes from the image's own
    config; one overlay or user copy alongside them still fails. See
    :func:`baked_into_base`.
    """
    payload, findings = mise_tools(environ=environ, run=run)
    forbidden = _forbidden(payload)
    image_configs = image_config_files(environ)
    baked = baked_into_base(payload, image_configs)
    if forbidden and baked == forbidden:
        sources = sorted(
            {
                str(_image_source(entry, image_configs))
                for key in baked
                for entry in payload[key]
            }
        )
        logger.warning(
            "SKIP: every mise claude/codex/agy copy here (%s) is declared by the "
            "image's own tool config (%s), so this base image predates native "
            "claude/codex/agy and provenance cannot be asserted. Sync the image "
            "built from this change (`mise run sync`, or `-- --tag pr-<N>`).",
            ", ".join(baked),
            ", ".join(sources),
        )
        return 0
    findings.extend(
        finding
        for tool in tools
        for finding in check_one(tool, home=home, environ=environ, run=run)
    )
    findings.extend(mise_findings(payload))
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
