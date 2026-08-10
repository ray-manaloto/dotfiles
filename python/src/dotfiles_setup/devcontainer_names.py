# Copyright (c) 2026 Raymond Manaloto
"""Architecture-scoped devcontainer resource names (#677).

Why the architecture has to be in the name
------------------------------------------

The home volume carries architecture-specific *compiled output*:
``~/.local/share/mise/installs``, ``~/.cargo`` and ``~/.rustup`` all live on it.
Mount one volume into an amd64 container and then into an arm64 one and docker
reports nothing — a named volume is created on first mount and reused
thereafter, by design. What you get instead is a home directory holding
binaries of two architectures, surfacing as ``exec format error`` or a wrong
resolve far from its cause. The same shape as #698: **absence and wrongness
that present as success.**

So the arch is a *name* component, not a runtime check. Two architectures
become two containers, two volumes and two ports, and the operating system's
own uniqueness rules do the enforcing.

Where each component comes from
-------------------------------

* the **workspace hash** — an 8-char SHA-256 prefix of the absolute workspace
  path, so sibling clones on one host never share resources. This is a port of
  the retired ``scripts/workspace-hash.sh`` and reproduces it byte-for-byte
  (:func:`workspace_hash`); a different digest would rename every deployed
  volume, and a renamed volume reads as an empty home, not as an error.
* the **architecture word** — resolved through
  :mod:`dotfiles_setup.platform_target`, never written as a literal. The
  ``no_platform_literals`` gate rejects the literal form anyway (#673).
* the **SSH port** — an explicit ``DEVCONTAINER_SSH_PORT`` if set, else derived
  from workspace *and* arch (:func:`ssh_port`), so a second working directory
  and a second architecture each get a distinct port with no configuration.

The port is in the container name and deliberately **not** in the volume name:
changing a port must not orphan a home directory (C10/C11/C12).
"""

from __future__ import annotations

import hashlib
import logging
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from dotfiles_setup.platform_target import (
    PLATFORM_ENV_VAR,
    platform_arch,
    resolve_platform,
)

logger = logging.getLogger(__name__)

__all__ = [
    "ARCH_ENV_VAR",
    "HOME_VOLUME_ENV_VAR",
    "NAME_ENV_VAR",
    "NAME_FIELDS",
    "RESOURCE_PREFIX",
    "SSH_PORT_BASE",
    "SSH_PORT_ENV_VAR",
    "SSH_PORT_SPAN",
    "WORKSPACE_HASH_ENV_VAR",
    "DevcontainerNames",
    "HomeVolumeMigration",
    "devcontainer_env_main",
    "devcontainer_name_main",
    "migrate_home_volume_main",
    "migration_platform_refusal",
    "name_field",
    "names_env",
    "plan_home_volume_migration",
    "render_plan",
    "resolve_names",
    "ssh_port",
    "workspace_hash",
]

#: Every resource this repo creates starts with it, so `ps`/`prune` can scope.
RESOURCE_PREFIX = "dotfiles"

WORKSPACE_HASH_ENV_VAR = "DEVCONTAINER_WORKSPACE_HASH"
ARCH_ENV_VAR = "DEVCONTAINER_ARCH"
NAME_ENV_VAR = "DEVCONTAINER_NAME"
HOME_VOLUME_ENV_VAR = "DEVCONTAINER_HOME_VOLUME"
SSH_PORT_ENV_VAR = "DEVCONTAINER_SSH_PORT"

#: The derived-port window. It opens above the well-known/registered churn and
#: closes below 49152, where macOS starts handing out ephemeral ports to
#: anonymous binds — a derived port inside that range would be stolen
#: intermittently, and R1 would fail on a timer rather than on a defect.
SSH_PORT_BASE = 20000
SSH_PORT_SPAN = 10000

#: Length of the workspace hash. Fixed by the deployed volume names — see
#: :func:`workspace_hash`.
_HASH_CHARS = 8

#: What ``dotfiles-setup devcontainer name <field>`` can print.
NAME_FIELDS = ("container", "volume", "legacy-volume", "port", "hash", "arch")


def workspace_hash(workspace: str | Path) -> str:
    """The 8-char SHA-256 prefix of ``workspace``'s absolute path.

    Byte-compatible with the retired ``scripts/workspace-hash.sh``
    (``printf '%s' "$PWD" | sha256sum | cut -c1-8``) — asserted by
    ``tests/test_devcontainer_names.py`` against both an independent
    re-derivation and frozen goldens, because a drifting digest renames every
    existing volume and a renamed volume looks like an empty home.
    """
    resolved = str(Path(workspace).resolve())
    return hashlib.sha256(resolved.encode()).hexdigest()[:_HASH_CHARS]


def ssh_port(
    workspace: str | Path,
    arch: str,
    *,
    override: str | int | None = None,
) -> int:
    """The host-side SSH port for this workspace and architecture.

    ``override`` wins when it holds a value — that is ``DEVCONTAINER_SSH_PORT``,
    the documented per-clone escape hatch. A *blank* override falls through to
    derivation on purpose: mise renders an unset variable as the empty string
    rather than omitting it, so "unset" reaches Python as ``""``.

    An unparsable override raises rather than falling back, because silently
    deriving a port from a typo'd pin is how a container comes up on a port
    nobody is ssh-ing to.
    """
    if override is not None and str(override).strip():
        text = str(override).strip()
        try:
            return int(text)
        except ValueError:
            msg = (
                f"{SSH_PORT_ENV_VAR}={text!r} is not a port number — unset it to "
                f"derive one from the workspace and architecture"
            )
            raise ValueError(msg) from None
    seed = f"{Path(workspace).resolve()}\0{arch}".encode()
    offset = int(hashlib.sha256(seed).hexdigest()[:_HASH_CHARS], 16) % SSH_PORT_SPAN
    return SSH_PORT_BASE + offset


@dataclass(frozen=True)
class DevcontainerNames:
    """Every docker resource name one workspace+architecture pair owns."""

    workspace: str
    basename: str
    user: str
    arch: str
    hash: str
    ssh_port: int

    @property
    def _stem(self) -> str:
        return f"{RESOURCE_PREFIX}-{self.basename}-{self.user}-{self.hash}"

    @property
    def container(self) -> str:
        """``dotfiles-<basename>-<user>-<hash>-<arch>-<port>``."""
        return f"{self._stem}-{self.arch}-{self.ssh_port}"

    @property
    def home_volume(self) -> str:
        """``dotfiles-<basename>-<user>-<hash>-<arch>-home`` — no port (C10-C12)."""
        return f"{self._stem}-{self.arch}-home"

    @property
    def legacy_home_volume(self) -> str:
        """The pre-#677 single-architecture home volume: the migration source."""
        return f"{self._stem}-home"


def resolve_names(
    *,
    workspace: str | Path | None = None,
    user: str | None = None,
    platform: str | None = None,
    port_override: str | int | None = None,
    env: dict[str, str] | None = None,
) -> DevcontainerNames:
    """Resolve every name for one workspace+architecture.

    Each argument defaults to the ambient reality the devloop runs in: the
    current directory, ``$USER``, and the one platform parameter (#673).
    """
    environ = dict(os.environ) if env is None else env
    source = workspace if workspace is not None else Path.cwd()
    resolved_workspace = Path(source).resolve()
    resolved_user = user if user is not None else environ.get("USER", "")
    arch = platform_arch(resolve_platform(platform, env=environ))
    override = (
        port_override if port_override is not None else environ.get(SSH_PORT_ENV_VAR)
    )
    return DevcontainerNames(
        workspace=str(resolved_workspace),
        basename=resolved_workspace.name,
        user=resolved_user,
        arch=arch,
        hash=workspace_hash(resolved_workspace),
        ssh_port=ssh_port(resolved_workspace, arch, override=override),
    )


def names_env(names: DevcontainerNames) -> dict[str, str]:
    """The ``localEnv`` substitutions ``devcontainer.json`` reads.

    ``devcontainer.json`` composes nothing itself: it names whole values. That
    is what keeps the arch out of a JSON string literal, where
    ``no_platform_literals`` could not see it and a reviewer would not either.
    """
    return {
        WORKSPACE_HASH_ENV_VAR: names.hash,
        ARCH_ENV_VAR: names.arch,
        NAME_ENV_VAR: names.container,
        HOME_VOLUME_ENV_VAR: names.home_volume,
        SSH_PORT_ENV_VAR: str(names.ssh_port),
    }


def name_field(field: str, names: DevcontainerNames | None = None) -> str:
    """One resolved name, addressed by name.

    ``names`` defaults to this workspace's — pass one from :func:`resolve_names`
    to ask about a workspace or architecture that is not the one you are in.
    """
    if names is None:
        names = resolve_names()
    fields = {
        "container": names.container,
        "volume": names.home_volume,
        "legacy-volume": names.legacy_home_volume,
        "port": str(names.ssh_port),
        "hash": names.hash,
        "arch": names.arch,
    }
    if field not in fields:
        msg = (
            f"unknown devcontainer name field {field!r}: expected one of {NAME_FIELDS}"
        )
        raise ValueError(msg)
    return fields[field]


@dataclass(frozen=True)
class HomeVolumeMigration:
    """What (if anything) to do about a pre-#677 home volume."""

    action: str  # "copy" | "already-migrated" | "nothing-to-migrate"
    source: str
    target: str
    commands: tuple[tuple[str, ...], ...]
    reason: str


#: The copier. `busybox` is a ~4MB multi-arch image whose `cp -a` preserves
#: ownership, modes and symlinks; the alternative (`tar` piped through the
#: host) would re-encode the whole home through a shell pipeline for no gain.
_MIGRATION_IMAGE = "busybox:stable"


def plan_home_volume_migration(
    names: DevcontainerNames,
    *,
    existing_volumes: tuple[str, ...],
    target_populated: bool = False,
) -> HomeVolumeMigration:
    """Plan the one-shot copy from the pre-#677 home volume into this one.

    Pure: it decides from facts the caller measured, so the decision is
    testable without a docker daemon.

    Three cases, and the third is the one that matters. A target volume that
    *exists but is empty* is precisely what an interrupted first attempt leaves
    behind — docker created it when the copy container started and the copy
    never finished. Treating "exists" as "done" would strand a half-migrated
    home forever, so emptiness, not existence, is the signal (#677 AC:
    "an interrupted first creation leaves a state the next attempt can recover
    from").

    The source is never deleted here. Until the user has run the new container
    and is satisfied, the legacy volume is the only copy of their home;
    ``mise run prune`` is where removal belongs.
    """
    if names.legacy_home_volume not in existing_volumes:
        return HomeVolumeMigration(
            action="nothing-to-migrate",
            source=names.legacy_home_volume,
            target=names.home_volume,
            commands=(),
            reason=(
                f"no pre-#677 volume {names.legacy_home_volume!r} on this host — "
                f"{names.home_volume!r} will be created empty on first use"
            ),
        )
    if target_populated:
        return HomeVolumeMigration(
            action="already-migrated",
            source=names.legacy_home_volume,
            target=names.home_volume,
            commands=(),
            reason=(
                f"{names.home_volume!r} already holds a home directory — copying "
                f"over it would destroy live state"
            ),
        )
    return HomeVolumeMigration(
        action="copy",
        source=names.legacy_home_volume,
        target=names.home_volume,
        commands=(
            ("docker", "volume", "create", names.home_volume),
            (
                "docker",
                "run",
                "--rm",
                "-v",
                f"{names.legacy_home_volume}:/from:ro",
                "-v",
                f"{names.home_volume}:/to",
                _MIGRATION_IMAGE,
                "sh",
                "-c",
                "cp -a /from/. /to/",
            ),
        ),
        reason=(
            f"copying {names.legacy_home_volume!r} into {names.home_volume!r}; "
            f"the source is left intact — remove it with `mise run prune` once "
            f"the new container is known good"
        ),
    )


def render_plan(plan: HomeVolumeMigration) -> str:
    """The dry-run rendering: the reason plus every command, one per line."""
    lines = [f"home-volume migration: {plan.action} — {plan.reason}"]
    lines.extend(f"  $ {shlex.join(cmd)}" for cmd in plan.commands)
    return "\n".join(lines)


def _docker_volumes() -> tuple[str, ...]:
    """Every named volume on this host."""
    proc = subprocess.run(
        ["docker", "volume", "ls", "--format", "{{.Name}}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return tuple(line for line in proc.stdout.splitlines() if line.strip())


def _volume_is_populated(volume: str) -> bool:
    """True when ``volume`` already holds at least one entry.

    Only ever called for a volume already known to exist, because mounting a
    missing one would *create* it — and an empty volume created by the probe
    would then be indistinguishable from an interrupted migration.
    """
    proc = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{volume}:/probe:ro",
            _MIGRATION_IMAGE,
            "sh",
            "-c",
            "ls -A /probe",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return bool(proc.stdout.strip())


def migration_platform_refusal(
    platform: str | None, env: dict[str, str] | None = None
) -> str | None:
    """Why this migration must not guess an architecture, or ``None`` if it need not.

    The pre-#677 volume carries **no architecture in its name**, so nothing on
    the host records which architecture built its contents. Only the platform
    the caller was targeting does — and :func:`resolve_platform` falls back to
    the *host's* native triple when nothing pins it. Measured on this repo:
    the same command resolves ``amd64`` under ``mise run`` (which supplies the
    repo pin) and ``arm64`` from a bare shell on an M-series Mac. A copy is
    not a probe you can re-run for free, so an unpinned invocation refuses
    rather than picking one.
    """
    if platform:
        return None
    environ = os.environ if env is None else env
    if environ.get(PLATFORM_ENV_VAR, "").strip():
        return None
    return (
        f"refusing to guess an architecture: {PLATFORM_ENV_VAR} is unset, so the "
        f"target volume name would come from this HOST's architecture, not from "
        f"the one that built the home directory being copied. Run "
        f"`mise run migrate-home-volume` (which supplies the repo's pin) or pass "
        f"--platform explicitly"
    )


def migrate_home_volume_main(*, apply: bool, platform: str | None = None) -> int:
    """CLI entry: copy a pre-#677 home volume into the arch-scoped one.

    Dry-run by default. ``--apply`` is required to touch anything, following
    ``reap``'s precedent (#653): a bulk operation whose bare invocation mutates
    is one nobody can safely use to *look*.
    """
    refusal = migration_platform_refusal(platform)
    if refusal is not None:
        logger.error("migrate-home: %s", refusal)
        return 2
    names = resolve_names(platform=platform)
    volumes = _docker_volumes()
    target_exists = names.home_volume in volumes
    populated = _volume_is_populated(names.home_volume) if target_exists else False
    plan = plan_home_volume_migration(
        names, existing_volumes=volumes, target_populated=populated
    )
    sys.stdout.write(f"{render_plan(plan)}\n")
    if not plan.commands:
        return 0
    if not apply:
        sys.stdout.write("(dry run — pass --apply to execute)\n")
        return 0
    for cmd in plan.commands:
        sys.stdout.write(f"==> {shlex.join(cmd)}\n")
        subprocess.run(cmd, check=True)
    sys.stdout.write(
        f"OK: {names.legacy_home_volume} copied into {names.home_volume}; the "
        f"source is untouched\n"
    )
    return 0


def devcontainer_env_main() -> int:
    """CLI entry: print shell ``KEY=value`` exports for the devloop tasks.

    Consumed as ``eval "$(… devcontainer env)"``. Values are shell-quoted, and
    every one of them is derived here rather than in the task body — the whole
    point of [[zero-bash-logic]] is that this decision has exactly one home.
    """
    for key, value in names_env(resolve_names()).items():
        sys.stdout.write(f"export {key}={shlex.quote(value)}\n")
    return 0


def devcontainer_name_main(field: str) -> int:
    """CLI entry: print one resolved devcontainer resource name."""
    sys.stdout.write(f"{name_field(field, resolve_names())}\n")
    return 0
