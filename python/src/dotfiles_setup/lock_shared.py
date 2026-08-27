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
opposite, for the shared fragment ONLY: the routed invocation un-ignores it
alone via ``--remote-env MISE_IGNORED_CONFIG_PATHS=/workspaces/<basename>/
mise.toml`` (the workspace root config stays ignored). Verified by hand
2026-08-27: with the shared fragment un-ignored this way, ``mise lock uv``
inside the container wrote the musl URL to the bind-mounted host tree; left
fully set (both paths ignored), mise reports "No tools configured to lock"
and exits 0 — a silent no-op. See the "Respec round 2" note below for why
clearing the WHOLE variable, tried first, was itself a defect rather than
the fix.

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

**Respec 2026-08-27 (round 2):** a cold review of round 1 found the deeper
cause plus two more defects, all confirmed against the running container:

1. **Clearing the WHOLE var was itself wrong**, not just the CLI-re-invocation
   layered on top of it. ``MISE_IGNORED_CONFIG_PATHS`` names TWO paths — the
   workspace's own root ``mise.toml`` AND the shared fragment
   (``devcontainer.json``) — and round 1's ``--remote-env
   MISE_IGNORED_CONFIG_PATHS=`` cleared both, re-admitting the workspace root
   ``mise.toml`` too. With ``auto_install = true`` set in the container's own
   user-overlay mise config, that resolves and attempts to install all 46 host
   tools before ``mise lock`` runs anything — which is what actually produced
   round 1's ``github-attestations`` death (the CLI-re-invocation layer made
   it WORSE by adding a second full-toolset resolution on top, but the root
   variable was already wrong on its own). The fix un-ignores ONLY the shared
   fragment: the routed ``--remote-env`` value is
   ``MISE_IGNORED_CONFIG_PATHS=/workspaces/<basename>/mise.toml`` — the
   workspace root config stays ignored, the shared fragment does not.
2. **Validation accepted tools this task does not own.** The original
   validation reused :func:`dotfiles_setup.lock_integrity.declared_host_tools`,
   which unions the root ``mise.toml`` (33 keys) and the shared fragment (21
   keys) — so a root-only tool (``aws-cli``, an os-gated ``conda:ffmpeg``, …)
   passed validation and would have been locked into the WRONG file (this
   module never touches the root ``mise.lock``). Fixed by validating against
   :func:`dotfiles_setup.lock_integrity.declared_tools` scoped to
   ``.config/mise/conf.d/shared.toml`` alone — which also closes the
   os-gated-tool case for free, since ``conda:ffmpeg`` is not a shared-fragment
   key at all.
3. **The LOCAL branch (a capable host, or ``--no-container``) inherited
   ``MISE_IGNORED_CONFIG_PATHS`` from ``os.environ`` unexamined.** Run from
   INSIDE the devcontainer directly — which is exactly what this module's own
   refusal message recommends ("run this on a linux host") — the ambient
   value is the container's baked-in ignore of BOTH paths, so `mise lock`
   finds nothing, prints "No tools configured to lock", and exits 0; an
   unchanged file has no coverage regression, so the whole command reports
   success having written NOTHING. Fixed two ways: the local subprocess call
   now pins ``MISE_IGNORED_CONFIG_PATHS`` explicitly too (to THIS process's own
   ``<repo_root>/mise.toml`` — correct whether ``repo_root`` is a bare linux
   host's checkout or the container's own bind-mounted view, since either way
   it is this process's real filesystem path, unlike the routed case's
   ``/workspaces/<basename>`` translation); and, as a general backstop against
   ANY future silent-no-op cause, every ``mise lock`` call's output is checked
   for mise's own "No tools configured to lock" line and treated as a hard
   failure regardless of exit code — coverage-held is not the same as
   written.
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import TYPE_CHECKING

from dotfiles_setup.devcontainer_names import resolve_names
from dotfiles_setup.image_lock import devcontainer_exec_prefix, host_can_lock
from dotfiles_setup.lock_integrity import declared_tools
from dotfiles_setup.lock_integrity import main as lock_integrity_main

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

#: The lockfile this task owns. Never `.devcontainer/mise-system.lock` or
#: `mise-runtime.lock` (`lock-image` owns those) and never the root
#: `mise.lock` (`lock`/`lock-tools` owns that) — see the module docstring for
#: why the shared fragment gets its own lockfile at all.
SHARED_LOCK = ".config/mise/mise.lock"

#: The ONE config file this task validates tool names against — never the root
#: `mise.toml` too (round 2's HIGH 2: that union let root-only tools like
#: `aws-cli` or an os-gated `conda:ffmpeg` pass validation and get locked into
#: the WRONG file).
SHARED_FRAGMENT = ".config/mise/conf.d/shared.toml"

#: Pinned explicitly for every `mise lock` call, local or routed — never left
#: to whatever `os.environ` happens to hold. See the module docstring's
#: "Respec round 2" note.
IGNORED_CONFIG_PATHS_VAR = "MISE_IGNORED_CONFIG_PATHS"

#: mise's own message when `mise lock <tool>` finds nothing to lock — exit
#: code 0 either way, so this is the ONLY signal that distinguishes "ran and
#: processed the tool" from "ran and silently did nothing" (round 2's HIGH 3).
_NO_TOOLS_MARKER = "No tools configured to lock"


def _workspace_mise_toml(repo_root: Path) -> str:
    """The workspace's own root config, as the CONTAINER resolves it.

    Only meaningful for the ROUTED case: `repo_root` there is a HOST path
    (e.g. the macOS clone), but the devcontainer mounts the workspace at
    `/workspaces/<basename>` (`.devcontainer/devcontainer.json`'s
    `${localWorkspaceFolderBasename}` templating) — a different string than
    `repo_root` names on the invoking host. Derived via
    :func:`~dotfiles_setup.devcontainer_names.resolve_names` so the basename
    computation is the same one `devcontainer_exec_prefix`'s id-labels use,
    not a second guess at it.
    """
    basename = resolve_names(workspace=repo_root).basename
    return f"/workspaces/{basename}/mise.toml"


def _lock_command(
    repo_root: Path, tool: str, *, route: bool
) -> tuple[list[str], dict[str, str] | None]:
    """The `mise lock <tool>` argv (+ env override) — local, or routed.

    The routed form is `mise lock` itself, not a re-invocation of this CLI
    (see the module docstring's "Respec round 1" note for why that mattered)
    — built from :func:`~dotfiles_setup.image_lock.devcontainer_exec_prefix`
    so the id-label resolution lives in exactly one place, plus `--remote-env`
    to un-ignore ONLY the shared fragment inside the container.

    Both forms pin `MISE_IGNORED_CONFIG_PATHS` explicitly rather than
    inheriting the ambient environment (round 2's HIGH 1 + HIGH 3): the routed
    form via `--remote-env` (a `devcontainer exec`-native mechanism, so this
    stays zero-bash), the local form via an `env=` override for
    `subprocess.run` — `<repo_root>/mise.toml`, which is correct whether this
    process is running on a bare linux host or inside the devcontainer
    itself, since either way it is this process's own real filesystem path
    (unlike the routed case, which needs the `/workspaces/<basename>`
    translation because it is invoked FROM a different host).
    """
    if route:
        argv = [
            *devcontainer_exec_prefix(repo_root),
            "--remote-env",
            f"{IGNORED_CONFIG_PATHS_VAR}={_workspace_mise_toml(repo_root)}",
            "mise",
            "lock",
            tool,
        ]
        return argv, None
    env = {**os.environ, IGNORED_CONFIG_PATHS_VAR: str(repo_root / "mise.toml")}
    return ["mise", "lock", tool], env


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
    should fail in milliseconds, not after a devcontainer round-trip, and is
    scoped to the SHARED fragment alone — never the root `mise.toml` too
    (round 2's HIGH 2), since a root-only tool is a real declared tool this
    task still must not accept. Each tool is then locked exactly as
    :func:`dotfiles_setup.lock_integrity.scoped_lock_main` locks the root
    lock — a plain scoped `mise lock <tool>` per tool, run locally or (routed)
    via `devcontainer exec` — with its output checked for mise's own
    no-tools-found signal (round 2's HIGH 3) before coverage is verified
    HOST-side, after every tool has been locked, by calling
    :func:`dotfiles_setup.lock_integrity.main` directly rather than
    re-implementing the regression check: the predicate lives in ONE place
    (#648), and it already walks every lockfile this repo has, including
    `.config/mise/mise.lock`.
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
    declared = declared_tools(repo_root, (SHARED_FRAGMENT,))
    unknown = [tool for tool in tools if tool not in declared]
    if unknown:
        logger.error(
            "lock-shared: not declared in %s: %s. `mise lock` exits 0 "
            "without locking anything for a name it does not recognise, so "
            "this would look like success — and a name from the ROOT "
            "mise.toml (aws-cli, an os-gated conda:ffmpeg, …) is a real "
            "declared tool that just isn't one THIS task owns; locking it "
            "here would write the WRONG lockfile. Use the FULL key as "
            "written in %s.",
            SHARED_FRAGMENT,
            unknown,
            SHARED_FRAGMENT,
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
        # `reason` is `host_can_lock`'s CAPABILITY verdict, not a routing
        # motive — on the `container=True` path it explains nothing about WHY
        # we are routing (that was the caller's explicit ask), so don't imply
        # it does.
        if container is True:
            logger.info(
                "lock-shared: routing into the devcontainer (explicitly "
                "requested; host capability: %s)",
                reason,
            )
        else:
            logger.info("lock-shared: routing into the devcontainer: %s", reason)

    for tool in tools:
        argv, env = _lock_command(repo_root, tool, route=route)
        result = subprocess.run(
            argv,
            cwd=None if route else repo_root,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
        for line in output.rstrip("\n").splitlines():
            logger.info("mise lock %s: %s", tool, line)
        if _NO_TOOLS_MARKER in output:
            logger.error(
                "lock-shared: `mise lock %s` reported %r and exited 0 — it "
                "found NOTHING to lock, almost certainly because "
                "MISE_IGNORED_CONFIG_PATHS still hid %s from the child "
                "process. Reporting success here would be exactly the "
                "silent no-op a coverage check cannot see (an unchanged "
                "file has no regression to flag).",
                tool,
                _NO_TOOLS_MARKER,
                SHARED_FRAGMENT,
            )
            return 1
        if result.returncode != 0:
            logger.error(
                "lock-shared: `mise lock %s` failed (rc=%d)%s",
                tool,
                result.returncode,
                " inside the devcontainer" if route else "",
            )
            return result.returncode
    return lock_integrity_main(repo_root)
