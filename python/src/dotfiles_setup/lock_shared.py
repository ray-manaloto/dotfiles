# Copyright (c) 2026 Raymond Manaloto
"""Re-lock the SHARED host<->image lockfile from linux (#650's sibling).

``.config/mise/mise.lock`` is the lock mise writes for
``.config/mise/conf.d/shared.toml`` — the exact-pinned fragment BOTH the host
lint workflow (root ``mise.toml``) and the devcontainer image
(``.devcontainer/mise-system.toml``) merge in (epic #160 T5). Until this
module, the only way to re-lock a shared tool was the scoped ``mise run lock``
task (:func:`dotfiles_setup.lock_integrity.scoped_lock_main`) — safe against
the #370 whole-file-truncation defect, but blind to a SECOND macOS defect:
mise resolves a different release asset than linux does for at least one
backend, and that choice is made by the RESOLVING host, not by which platform
is being locked for.

Measured 2026-08-27: bumping uv 0.12.4 -> 0.12.6 via ``mise run lock -- uv``
on this macOS host wrote ``uv-x86_64-unknown-linux-gnu.tar.gz`` into
``[tools.uv."platforms.linux-x64"]``. mise on linux resolves the **musl**
asset for that same platform entry and derives the installed bin path from
it, so a linux runner would have downloaded the gnu tarball, extracted it to
a gnu-named directory, and then looked for the binary under the musl path —
``uv: not found``, cascading into every hk step that shells out to it. Every
local gate passed, because on macOS the macOS platform entries are the ones
exercised. Re-locking the same tool inside the amd64 devcontainer produced
the musl asset, confirming the divergence is a property of WHERE the lock is
written — not a :mod:`dotfiles_setup.lock_integrity` regression (a right
platform key with wrong-host content is invisible to a "lost platform
coverage" check) and not a blanket macOS defect (bun/hk/pixi/yq re-locked
identically on both hosts in the same session), which is exactly why it goes
unnoticed until a specific tool trips it.

This module reuses :mod:`dotfiles_setup.image_lock`'s host-capability check
(:func:`~dotfiles_setup.image_lock.host_can_lock`) and id-label resolution
(:func:`~dotfiles_setup.image_lock.devcontainer_exec_prefix`), and
:func:`dotfiles_setup.lock_integrity.scoped_lock_main`'s named-tools-only
safety model, for the one lockfile neither sibling owns: ``lock``/
``lock-tools`` never leave this host, and ``lock-image`` only ever touches
the two ``.devcontainer/*.lock`` files.

The container ignores the workspace's own copy of the shared fragment by
design — ``devcontainer.json``'s ``MISE_IGNORED_CONFIG_PATHS`` names both the
workspace ``mise.toml`` and ``.config/mise/conf.d/shared.toml`` so the
running container always resolves tools against its BAKED-IN system copy
(``/usr/local/share/mise/conf.d/shared.toml``), never the bind-mounted host
repo — "the container reads the baked config, never the host repo"
isolation. Regenerating ``.config/mise/mise.lock`` needs exactly the
opposite for one ``devcontainer exec`` call, so the routed invocation clears
the whole variable via ``--remote-env MISE_IGNORED_CONFIG_PATHS=``. Verified
by hand 2026-08-27: with it cleared, ``mise lock uv`` inside the container
wrote the musl URL to the bind-mounted host tree; left set, mise reports "No
tools configured to lock" and exits 0 — a silent no-op. That is held as an
assumption rather than a documented mise mechanism: it is upstream
config-resolution behaviour, not something this repo's source settles.

**Respec 2026-08-27 (round 1):** the first version routed by re-invoking this
CLI inside the container — ``image_lock.container_command`` generalised to
carry ``subcommand="lock-shared"``, i.e. ``devcontainer exec ... mise exec --
uv run --project python dotfiles-setup lock-shared --no-container <tools>``.
That failed a live integration check: ``mise exec --``, with
``MISE_IGNORED_CONFIG_PATHS`` cleared, resolves mise's ENTIRE declared
toolset before running anything — including host-only tools the image
deliberately can't attest (``.devcontainer/mise-system.toml``'s
``github_attestations = false`` against a host lock entry's ``provenance =
"github-attestations"``) — so it died resolving the wrapper's own tool graph
and never reached ``mise lock``. The fix drops the CLI-re-invocation layer
entirely: the routed command is ``mise lock <tool>`` directly, built from
:func:`~dotfiles_setup.image_lock.devcontainer_exec_prefix` plus
``--remote-env``. There is nothing to resolve first, because ``mise`` itself
is the command, not a Python re-entry point. Coverage verification
(:func:`dotfiles_setup.lock_integrity.main`) now always runs HOST-side, after
the container call returns — it no longer runs via recursion inside the
container, since there is no more recursion.
"""

from __future__ import annotations

import logging
import subprocess
from typing import TYPE_CHECKING

from dotfiles_setup.image_lock import devcontainer_exec_prefix, host_can_lock
from dotfiles_setup.lock_integrity import declared_host_tools
from dotfiles_setup.lock_integrity import main as lock_integrity_main

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

#: The lockfile this task owns. Never `.devcontainer/mise-system.lock` or
#: `mise-runtime.lock` (`lock-image` owns those) and never the root
#: `mise.lock` (`lock`/`lock-tools` owns that) — see the module docstring for
#: why the shared fragment gets its own lockfile at all.
SHARED_LOCK = ".config/mise/mise.lock"

#: Cleared for the routed `mise lock` call — see the module docstring.
IGNORED_CONFIG_PATHS_VAR = "MISE_IGNORED_CONFIG_PATHS"


def _lock_command(repo_root: Path, tool: str, *, route: bool) -> list[str]:
    """The `mise lock <tool>` argv for one tool — local, or routed into the container.

    The routed form is `mise lock` itself, not a re-invocation of this CLI
    (see the module docstring's "Respec" note for why that mattered) — built
    from :func:`~dotfiles_setup.image_lock.devcontainer_exec_prefix` so the
    id-label resolution lives in exactly one place, plus `--remote-env` to
    clear `MISE_IGNORED_CONFIG_PATHS` for this one call.
    """
    if route:
        return [
            *devcontainer_exec_prefix(repo_root),
            "--remote-env",
            f"{IGNORED_CONFIG_PATHS_VAR}=",
            "mise",
            "lock",
            tool,
        ]
    return ["mise", "lock", tool]


def lock_shared_main(
    repo_root: Path,
    tools: list[str],
    *,
    container: bool | None = None,
) -> int:
    """Re-lock exactly the named tools in `.config/mise/mise.lock`, from linux.

    ``container`` is tri-state, matching
    :func:`dotfiles_setup.image_lock.image_lock_main`: ``None`` routes into
    the devcontainer only when this host cannot resolve linux-native assets,
    ``True`` always routes, ``False`` never does — and fails loudly on a host
    that cannot do the job, rather than writing a lock that only fails on the
    platform it targets.

    Tool-name validation happens BEFORE the routing decision: a bad name
    should fail in milliseconds, not after a devcontainer round-trip. Each
    tool is then locked exactly as
    :func:`dotfiles_setup.lock_integrity.scoped_lock_main` locks the root
    lock — a plain scoped `mise lock <tool>` per tool, run locally or (routed)
    via `devcontainer exec` — and coverage is verified HOST-side, after every
    tool has been locked, by calling :func:`dotfiles_setup.lock_integrity.main`
    directly rather than re-implementing the regression check: the predicate
    lives in ONE place (#648), and it already walks every lockfile this repo
    has, including `.config/mise/mise.lock`.
    """
    if not tools:
        logger.error(
            "lock-shared: refusing to run a bare `mise lock` — it re-locks "
            "the WHOLE lockfile for this platform and drops the linux conda "
            "entries the amd64 devcontainer needs (#370). Name the tool(s) "
            'instead: mise run lock-shared -- "uv" — the FULL '
            "backend-qualified key from the config, since a bare short name "
            "exits 0 having silently done nothing."
        )
        return 1
    declared = declared_host_tools(repo_root)
    unknown = [tool for tool in tools if tool not in declared]
    if unknown:
        logger.error(
            "lock-shared: not declared in the host config: %s. `mise lock` "
            "exits 0 without locking anything for a name it does not "
            "recognise, so this would look like success. Use the FULL key "
            "as written in .config/mise/conf.d/shared.toml.",
            unknown,
        )
        return 1

    capable, reason = host_can_lock()
    route = container is True or (container is None and not capable)
    if not route and not capable:
        logger.error(
            "lock-shared: refusing to regenerate %s here: %s. Re-run without "
            "--no-container to route into the devcontainer, or run this on a "
            "linux host. mise resolves a DIFFERENT release asset than macOS "
            "for at least one tool, and the wrong one fails only on the "
            "platform it was written for — SILENTLY, since local gates never "
            "exercise a linux platform entry (measured 2026-08-27: uv wrote "
            "the gnu tarball for linux-x64 while mise on linux resolves "
            "musl).",
            SHARED_LOCK,
            reason,
        )
        return 1
    if route:
        logger.info("lock-shared: routing into the devcontainer: %s", reason)

    for tool in tools:
        argv = _lock_command(repo_root, tool, route=route)
        result = subprocess.run(argv, cwd=None if route else repo_root, check=False)
        if result.returncode != 0:
            logger.error(
                "lock-shared: `mise lock %s` failed (rc=%d)%s",
                tool,
                result.returncode,
                " inside the devcontainer" if route else "",
            )
            return result.returncode
    return lock_integrity_main(repo_root)
