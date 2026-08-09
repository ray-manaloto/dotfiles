# Copyright (c) 2026 Raymond Manaloto
"""Regenerate the image lockfiles locally, with CI's recipe as a callable (#650).

``.devcontainer/mise-system.lock`` and ``.devcontainer/mise-runtime.lock`` had
no local task: the only thing that knew how to rebuild them was CI's
``.github/actions/lock-refresh/action.yml``, so a session that bumped the shared
fragment had to hand-transcribe the recipe from a workflow file. On 2026-08-08
that cost ~15 turns and produced a near-committed corruption — a regen run on
macOS dropped ``mise-system.lock``'s ``linux-x64`` occurrences 131 -> 64 and
``mise-runtime.lock``'s 35 -> 12, while the tool count never moved (49 and 22),
so the collect step returned ``rc=0`` on it (#648, fixed in
:func:`dotfiles_setup.lock_refresh.collect_system_lock`).

Three gotchas, each of which cost a cycle to learn, are encoded here rather than
left to be rediscovered:

1. **macOS cannot do this at all.** mise on darwin cannot write the linux conda
   checksums (jdx/mise#7700), so a regen there silently truncates. This module
   refuses on a non-linux-x64 host unless it can route itself into the amd64
   devcontainer, which is what produced a faithful result.
2. **Lock every platform the committed lock CARRIES, not just ``linux-x64``.**
   CI passes ``--platform linux-x64`` alone and gets away with it only because
   the committed lock is seeded in as a starting point: the ``macos-x64``
   entries survive untouched. Bump a tool and its entries are *replaced*, so the
   ``macos-x64`` one is lost and ``lock-check`` fails with ``tool uv: lost
   platform(s) ['macos-x64']``. Measured on the committed files —
   ``mise-system.lock`` carries six platforms (46 ``linux-x64`` and **29
   ``macos-x64``** tool entries), ``mise-runtime.lock`` two (11 and **9**).
   :func:`lock_platforms` derives the set from the file instead of naming it.
3. **Verify coverage before writing.** Delegated, not re-implemented:
   :func:`dotfiles_setup.lock_refresh.collect_system_lock` now runs
   :func:`dotfiles_setup.lock_integrity.regressions` against the git-committed
   bytes, so a truncated regen raises instead of landing.

Everything is a parameter with this repo's case as its default — the platform
set, the pass count, the stage directory, the installer fetch, and the container
routing — so the same functions serve another lock, another image, or a test.
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup.lock_integrity import conda_platforms, tool_platforms
from dotfiles_setup.lock_refresh import (
    RUNTIME_ENV,
    collect_system_lock,
    stage_system_lock_dir,
)
from dotfiles_setup.platform_target import (
    expected_uname_machine,
    platform_arch,
    resolve_platform,
)

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

#: The committed lock whose platform coverage defines what a regen must produce.
SYSTEM_LOCK = ".devcontainer/mise-system.lock"

#: Where the pinned mise binary is installed inside the stage directory.
PINNED_MISE_DIRNAME = "mise-pinned"

MISE_INSTALLER_URL = "https://mise.run"

#: `mise lock` resolves through GitHub, and anonymous quota exhausts mid-run;
#: each pass fills what the previous could not. CI uses five and converges.
DEFAULT_PASSES = 5

#: The only host that can write a faithful image lock (gotcha 1).
REQUIRED_OS = "Linux"


def required_machines(target_platform: str | None = None) -> frozenset[str]:
    """Every ``uname -m`` spelling a host may report and still match the image.

    Derived from the one platform parameter (#673) rather than pinned to
    amd64: the lock has to be written on a host of the IMAGE's architecture,
    so when #676 publishes arm64 this gate follows the target instead of
    silently continuing to demand x86_64. Both spellings are accepted because
    ``uname -m`` and docker disagree on the name.
    """
    arch = platform_arch(resolve_platform(target_platform))
    return frozenset({expected_uname_machine(f"linux/{arch}"), arch})


class ImageLockError(RuntimeError):
    """A precondition failed, or a step of the recipe did."""


def lock_platforms(lock_text: str) -> tuple[str, ...]:
    """Every platform the committed lock carries, tool entries and conda alike.

    Derived rather than declared (gotcha 2). A hard-coded ``linux-x64`` is
    correct only while no tool is bumped, which is the one condition under
    which anyone runs this.
    """
    covered: set[str] = set(conda_platforms(lock_text))
    for platforms in tool_platforms(lock_text).values():
        covered |= platforms
    return tuple(sorted(covered))


def host_can_lock(
    system: str | None = None,
    machine: str | None = None,
    *,
    target_platform: str | None = None,
) -> tuple[bool, str]:
    """Can this host write a faithful image lock? Returns the verdict + reason.

    ``target_platform`` is the architecture the lock is being written FOR and
    defaults to the one platform parameter (#673). It is an explicit argument
    so a caller — and a test — can state which image it means, rather than
    inheriting whatever the ambient environment happens to say.
    """
    system = system or platform.system()
    machine = (machine or platform.machine()).lower()
    if system != REQUIRED_OS:
        return False, (
            f"host OS is {system}, not {REQUIRED_OS} — mise cannot write the "
            f"linux conda checksums off linux (jdx/mise#7700), and the tool "
            f"count does not move, so the truncation is silent"
        )
    resolved = resolve_platform(target_platform)
    accepted = required_machines(resolved)
    if machine not in accepted:
        return False, (
            f"host machine is {machine}, not one of {sorted(accepted)} — the "
            f"image targets {resolved}"
        )
    return True, f"{system}/{machine}"


def npm_available(which: Callable[[str], str | None] = shutil.which) -> bool:
    """Is ``npm`` runnable?

    mise's npm backend **execs** node/npm while resolving an ``npm:`` version
    and ENOENT-fails without them. ``bun`` on PATH does not satisfy it despite
    ``npm.package_manager = bun``, which is why this asks for ``npm`` by name.
    """
    return which("npm") is not None


def fetch_installer(url: str = MISE_INSTALLER_URL) -> bytes:
    """The mise install script, via ``curl`` exactly as the CI recipe does.

    Separate from its use so a test never reaches the network. The scheme is
    asserted rather than assumed: the bytes are piped to ``sh``, so an
    ``http://`` or ``file://`` override would be a code-execution primitive
    rather than a convenience.
    """
    if not url.startswith("https://"):
        msg = f"refusing to fetch the mise installer over a non-https URL: {url}"
        raise ImageLockError(msg)
    result = subprocess.run(["curl", "-fsSL", url], capture_output=True, check=False)
    if result.returncode != 0:
        msg = (
            f"fetching {url} failed (rc={result.returncode}): "
            f"{result.stderr.decode(errors='replace').strip()}"
        )
        raise ImageLockError(msg)
    return result.stdout


def install_pinned_mise(
    stage_dir: Path,
    version: str,
    *,
    fetch: Callable[[str], bytes] = fetch_installer,
    url: str = MISE_INSTALLER_URL,
) -> Path:
    """Install the image's exact mise version into ``stage_dir``.

    The pin is not optional: lock formats are **not** cross-version compatible,
    so a lock written by a different mise is one the image's
    ``mise install --locked`` rejects. Same installer and same ``ARG
    MISE_VERSION`` the Dockerfile uses.
    """
    install_path = stage_dir / PINNED_MISE_DIRNAME
    env = {
        **os.environ,
        "MISE_VERSION": f"v{version}",
        "MISE_INSTALL_PATH": str(install_path),
    }
    result = subprocess.run(
        ["sh"], input=fetch(url), env=env, capture_output=True, check=False
    )
    if result.returncode != 0:
        msg = (
            f"installing pinned mise v{version} failed (rc={result.returncode}): "
            f"{result.stderr.decode(errors='replace').strip()}"
        )
        raise ImageLockError(msg)
    if not install_path.exists():
        msg = f"pinned mise installer reported success but {install_path} is absent"
        raise ImageLockError(msg)
    return install_path


def lock_command(
    mise_bin: Path, stage_dir: Path, platforms: tuple[str, ...]
) -> list[str]:
    """The ``mise lock`` argv for one convergence pass."""
    argv = [str(mise_bin), "lock"]
    for name in platforms:
        argv += ["--platform", name]
    return [*argv, "-C", str(stage_dir)]


def run_lock_passes(
    mise_bin: Path,
    stage_dir: Path,
    platforms: tuple[str, ...],
    *,
    passes: int = DEFAULT_PASSES,
    run: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> None:
    """Run the convergence loop; the LAST pass must succeed.

    Earlier passes are allowed to fail — that is what the loop is for, since
    exhausted GitHub quota is the expected mid-run failure. A final failure is
    real: ``mise lock`` has hard-errored on an unresolvable tool since
    2026.6.13, so a genuinely broken tool fails loud here rather than producing
    a quietly short lock.
    """
    argv = lock_command(mise_bin, stage_dir, platforms)
    child_env = {
        **os.environ,
        # Both tiers in one pass: mise writes mise.lock (base) and
        # mise.runtime.lock (runtime tier) under this env (#160 T9).
        "MISE_ENV": RUNTIME_ENV,
        "MISE_TRUSTED_CONFIG_PATHS": str(stage_dir),
    }
    last: subprocess.CompletedProcess[bytes] | None = None
    for attempt in range(1, passes + 1):
        last = run(argv, env=child_env, check=False)
        if last.returncode == 0:
            logger.info("mise lock converged on pass %d/%d", attempt, passes)
            return
        logger.warning(
            "mise lock pass %d/%d exited %d — retrying (rate limits are the "
            "expected cause)",
            attempt,
            passes,
            last.returncode,
        )
    rc = last.returncode if last is not None else -1
    msg = f"mise lock did not converge in {passes} pass(es); last rc={rc}"
    raise ImageLockError(msg)


def container_command(repo_root: Path, extra: tuple[str, ...] = ()) -> list[str]:
    """Re-invoke this task inside the amd64 devcontainer.

    ``devcontainer exec`` and not raw ``docker exec`` (``do-not.md`` #3), and
    the inner call passes ``--no-container`` so the recursion terminates. The
    workspace is bind-mounted, so the inner run's writes land on the host tree.
    """
    return [
        "devcontainer",
        "exec",
        "--workspace-folder",
        str(repo_root),
        "mise",
        "exec",
        "--",
        "uv",
        "run",
        "--project",
        "python",
        "dotfiles-setup",
        "image-lock",
        "--no-container",
        *extra,
    ]


def image_lock_main(
    repo_root: Path,
    *,
    platforms: tuple[str, ...] = (),
    stage: Path | None = None,
    container: bool | None = None,
    passes: int = DEFAULT_PASSES,
) -> int:
    """Stage, install pinned mise, converge, then collect with coverage verified.

    ``container`` is tri-state on purpose: ``None`` routes into the devcontainer
    only when the host cannot do the job itself, ``True`` always routes, and
    ``False`` never does (and therefore fails loudly on a host that cannot).
    """
    capable, reason = host_can_lock()
    if container is True or (container is None and not capable):
        logger.info("routing into the devcontainer: %s", reason)
        extra = tuple(arg for name in platforms for arg in ("--platform", name))
        result = subprocess.run(container_command(repo_root, extra), check=False)
        return result.returncode
    if not capable:
        logger.error(
            "refusing to regenerate the image locks here: %s. Re-run without "
            "--no-container to route into the devcontainer, or run this on a "
            "linux host of the image's own architecture. A regen on the wrong "
            "host truncates the "
            "lock SILENTLY — the tool count does not move (#648, #650).",
            reason,
        )
        return 1
    if not npm_available():
        logger.error(
            "npm is not on PATH. mise's npm backend EXECS node/npm while "
            "resolving an `npm:` version and ENOENT-fails without them; bun "
            "does NOT satisfy it despite npm.package_manager = bun."
        )
        return 1

    if not platforms:
        platforms = lock_platforms((repo_root / SYSTEM_LOCK).read_text())
        logger.info(
            "locking the %d platform(s) the committed lock carries: %s",
            len(platforms),
            ", ".join(platforms),
        )

    owned_stage = stage is None
    stage_dir = (
        Path(tempfile.mkdtemp(prefix="dotfiles-image-lock-")) if owned_stage else stage
    )
    try:
        version = stage_system_lock_dir(repo_root, stage_dir)
        mise_bin = install_pinned_mise(stage_dir, version)
        run_lock_passes(mise_bin, stage_dir, platforms, passes=passes)
        collect_system_lock(repo_root, stage_dir)
    except ImageLockError, ValueError, OSError:
        logger.exception("image-lock failed")
        return 1
    finally:
        if owned_stage:
            shutil.rmtree(stage_dir, ignore_errors=True)
    logger.info(
        "image-lock OK: %s and the runtime lock regenerated with mise v%s "
        "across %d platform(s), coverage verified against HEAD",
        SYSTEM_LOCK,
        version,
        len(platforms),
    )
    return 0
