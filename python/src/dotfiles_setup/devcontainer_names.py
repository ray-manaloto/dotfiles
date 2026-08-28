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
import json
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
    "ARCH_LABEL",
    "ARCH_LABEL_ENV_VAR",
    "HOME_VOLUME_ENV_VAR",
    "ID_FLAGS_ENV_VAR",
    "LEGACY_FOLDER_LABEL",
    "MIGRATION_MARKER",
    "NAME_ENV_VAR",
    "NAME_FIELDS",
    "REFUSED_ACTIONS",
    "RESOURCE_PREFIX",
    "SSH_PORT_BASE",
    "SSH_PORT_ENV_VAR",
    "SSH_PORT_SPAN",
    "WORKSPACE_HASH_ENV_VAR",
    "WORKSPACE_LABEL",
    "WORKSPACE_LABEL_ENV_VAR",
    "DevcontainerNames",
    "HomeVolumeMigration",
    "ImageRefs",
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
    "teardown_container_ids",
    "teardown_image_refs",
    "teardown_images_main",
    "teardown_main",
    "workspace_hash",
]

#: Every resource this repo creates starts with it, so `ps`/`prune` can scope.
RESOURCE_PREFIX = "dotfiles"

WORKSPACE_HASH_ENV_VAR = "DEVCONTAINER_WORKSPACE_HASH"
ARCH_ENV_VAR = "DEVCONTAINER_ARCH"
NAME_ENV_VAR = "DEVCONTAINER_NAME"
HOME_VOLUME_ENV_VAR = "DEVCONTAINER_HOME_VOLUME"
SSH_PORT_ENV_VAR = "DEVCONTAINER_SSH_PORT"
WORKSPACE_LABEL_ENV_VAR = "DEVCONTAINER_WORKSPACE_LABEL"
ARCH_LABEL_ENV_VAR = "DEVCONTAINER_ARCH_LABEL"
ID_FLAGS_ENV_VAR = "DEVCONTAINER_ID_FLAGS"

#: The derived-port window. It opens above the well-known/registered churn and
#: closes below 49152, where macOS starts handing out ephemeral ports to
#: anonymous binds — a derived port inside that range would be stolen
#: intermittently, and R1 would fail on a timer rather than on a defect.
SSH_PORT_BASE = 20000
SSH_PORT_SPAN = 10000

#: What an explicit ``DEVCONTAINER_SSH_PORT`` may be. Unprivileged so the pin
#: works without sudo, and inside the 16-bit space so it can actually bind.
_MIN_PORT = 1024
_MAX_PORT = 65535

#: Length of the workspace hash. Fixed by the deployed volume names — see
#: :func:`workspace_hash`.
_HASH_CHARS = 8

#: What ``dotfiles-setup devcontainer name <field>`` can print.
NAME_FIELDS = (
    "container",
    "volume",
    "legacy-volume",
    "port",
    "hash",
    "arch",
    "workspace-label",
    "arch-label",
)

#: The two id labels that identify one container. **The `--name` is not enough.**
#: `@devcontainers/cli` 0.88.0 looks an existing container up by *id labels*, and
#: with none supplied it infers them from the workspace folder alone
#: (`devContainersSpecCLI.js`, function `bg`: `if (idLabels) return {...}`, else
#: `[devcontainer.local_folder=<folder>]`). Both inferred labels are per-FOLDER,
#: so without these two an arm64 `up` in a directory that already has an amd64
#: container **finds and reuses it** and reports success — the name never gets a
#: chance to matter.
#:
#: Both are required together. `--id-label` REPLACES the inferred set rather
#: than extending it, so the arch label alone would make two clones collide;
#: the workspace label is what the folder inference used to provide.
WORKSPACE_LABEL = "dotfiles.workspace"
ARCH_LABEL = "dotfiles.arch"


def workspace_hash(workspace: str | Path) -> str:
    """The 8-char SHA-256 prefix of ``workspace``'s absolute path.

    Digest-compatible with the retired ``scripts/workspace-hash.sh``
    (``printf '%s' "$PWD" | sha256sum | cut -c1-8``) — asserted by
    ``tests/test_devcontainer_names.py`` against both an independent
    re-derivation and frozen goldens, because a drifting digest renames every
    existing volume and a renamed volume looks like an empty home.

    One deliberate difference: the shell hashed ``$PWD``, the *logical* path
    bash keeps when you ``cd`` through a symlink, while this resolves to the
    *physical* path. They differ only for a workspace reached via a symlink, and
    the physical path is the correct identity — two logical routes to one
    directory are one workspace and must not get two homes. A clone that was
    always reached through a symlink gets a one-time rename, recoverable with
    ``mise run migrate-home-volume``.
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
        # Not a bare int(): that accepts `4_444` (silently 4444), and a plain
        # range check has to follow, because 0 and 70000 parse fine and then
        # fail much later as a docker port-binding error with nothing pointing
        # back at the pin that caused it.
        if not text.isdigit() or not (_MIN_PORT <= int(text) <= _MAX_PORT):
            msg = (
                f"{SSH_PORT_ENV_VAR}={text!r} is not a usable port — expected an "
                f"integer in {_MIN_PORT}-{_MAX_PORT}. Unset it to derive one from "
                f"the workspace and architecture"
            )
            raise ValueError(msg)
        return int(text)
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

    @property
    def workspace_label(self) -> str:
        """``dotfiles.workspace=<hash>`` — which clone this container belongs to."""
        return f"{WORKSPACE_LABEL}={self.hash}"

    @property
    def arch_label(self) -> str:
        """``dotfiles.arch=<arch>`` — the label that makes lookup arch-aware."""
        return f"{ARCH_LABEL}={self.arch}"

    @property
    def id_flags(self) -> str:
        """Both labels as ready-to-splat CLI flags: ``--id-label X --id-label Y``.

        Meant to be used **unquoted** (``devcontainer exec $DEVCONTAINER_ID_FLAGS
        …``) so one variable carries two flag pairs without a bash array — mise
        task bodies are not guaranteed to be bash. That is only safe because
        both values are whitespace-free by construction (a hex digest and one of
        two arch words), which ``tests/test_devcontainer_names.py`` pins.
        """
        return " ".join(f"--id-label {label}" for label in self.id_labels)

    @property
    def id_labels(self) -> tuple[str, ...]:
        """Both id labels, in the order the CLI flags take them.

        Deliberately free of whitespace and shell metacharacters (a hex digest
        and one of two arch words), so a task can interpolate them into
        ``--id-label "..."`` without an array or any quoting ceremony — mise
        task bodies are not guaranteed to be bash.
        """
        return (self.workspace_label, self.arch_label)


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
        WORKSPACE_LABEL_ENV_VAR: names.workspace_label,
        ARCH_LABEL_ENV_VAR: names.arch_label,
        ID_FLAGS_ENV_VAR: names.id_flags,
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
        "workspace-label": names.workspace_label,
        "arch-label": names.arch_label,
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

    action: str
    source: str
    target: str
    commands: tuple[tuple[str, ...], ...]
    reason: str


#: The copier. `busybox` is a ~4MB multi-arch image whose `cp -a` preserves
#: ownership, modes and symlinks; the alternative (`tar` piped through the
#: host) would re-encode the whole home through a shell pipeline for no gain.
_MIGRATION_IMAGE = "busybox:stable"

#: Written into the target as the LAST step of a successful copy, so a later run
#: can tell a finished migration from one that died partway. Without it the only
#: available signal is "is the target empty", and a copy of a 3.5 GB home that
#: dies at 90% leaves a target that is very much not empty — which read as
#: "already migrated" and would have sent the user into a truncated home.
MIGRATION_MARKER = ".dotfiles-migrated-from-pre-677"

#: Separates the two answers :func:`_probe_volume` collects in one container run.
_PROBE_SEPARATOR = "---dotfiles-probe---"
_PROBE_SCRIPT = (
    f"ls -A /probe | head -1; echo {_PROBE_SEPARATOR}; "
    f"if test -e /probe/{MIGRATION_MARKER}; then echo MARKED; else :; fi"
)

#: Plan actions that mean "I will not do this", as opposed to "there is nothing
#: to do". Only these turn an ``--apply`` into a non-zero exit.
REFUSED_ACTIONS = frozenset({"source-in-use", "target-unverified"})


def plan_home_volume_migration(
    names: DevcontainerNames,
    *,
    existing_volumes: tuple[str, ...],
    target_populated: bool = False,
    target_marked: bool = False,
    source_in_use: bool = False,
) -> HomeVolumeMigration:
    """Plan the one-shot copy from the pre-#677 home volume into this one.

    Pure: it decides from facts the caller measured, so the decision is
    testable without a docker daemon.

    **Completion is a marker, not emptiness** (#677 AC: "an interrupted first
    creation leaves a state the next attempt can recover from"). A successful
    copy writes :data:`MIGRATION_MARKER` last; a copy that dies partway through
    a 3.5 GB home leaves a target that is neither empty nor complete. Reading
    "non-empty" as "done" would have reported ``already-migrated`` and sent the
    user into a truncated home — the same torn-home failure ``source_in_use``
    exists to prevent, arriving through the other door.

    A populated-but-unmarked target therefore **refuses** rather than resuming.
    It is genuinely ambiguous: it is either a failed copy, or a home the user
    already created and worked in via ``mise run up``. Nothing on disk
    distinguishes them, so overwriting would risk destroying real work and
    skipping would risk a truncated home. The plan names both possibilities and
    lets the human decide.

    ``source_in_use`` refuses while a container still has the source mounted.
    Copying a live home is not merely untidy — the container is writing caches,
    histories and sqlite files *during* the copy, so ``cp -a`` can capture a
    half-written record and the result is a **torn** home that starts fine and
    misbehaves later. Measured on the real host: the pre-#677 volume was 3.5 GB
    and mounted read-write by a running container.

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
    if target_marked:
        return HomeVolumeMigration(
            action="already-migrated",
            source=names.legacy_home_volume,
            target=names.home_volume,
            commands=(),
            reason=(
                f"{names.home_volume!r} carries {MIGRATION_MARKER} — this "
                f"migration already completed; nothing to do"
            ),
        )
    if target_populated:
        return HomeVolumeMigration(
            action="target-unverified",
            source=names.legacy_home_volume,
            target=names.home_volume,
            commands=(),
            reason=(
                f"{names.home_volume!r} holds a home directory but no "
                f"{MIGRATION_MARKER} — it is EITHER a copy that died partway "
                f"OR a home you already created and worked in. Nothing on disk "
                f"tells them apart, so decide: if it was a failed copy, "
                f"`docker volume rm {names.home_volume}` and retry; if it is "
                f"real work, you do not want this migration at all"
            ),
        )
    if source_in_use:
        return HomeVolumeMigration(
            action="source-in-use",
            source=names.legacy_home_volume,
            target=names.home_volume,
            commands=(),
            reason=(
                f"a container still has {names.legacy_home_volume!r} mounted — "
                f"copying a home directory that is being written to yields a TORN "
                f"copy that starts fine and misbehaves later. Run `mise run stop` "
                f"first, then retry"
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
                # One `sh -c`, and the marker is written LAST under `set -e`, so
                # it can only appear after cp has returned 0. Splitting these
                # into two docker runs would let the process die between them
                # and mark an incomplete copy as complete.
                f"set -e; cp -a /from/. /to/; date -u > /to/{MIGRATION_MARKER}",
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


def _probe_volume(volume: str) -> tuple[bool, bool]:
    """``(populated, marked)`` for an existing volume, in ONE container run.

    Only ever called for a volume already known to exist, because mounting a
    missing one would *create* it — and an empty volume created by the probe
    would then be indistinguishable from an interrupted migration.

    Both facts come from one run so they cannot disagree: two separate probes
    could straddle a concurrent copy and report "populated but unmarked" for a
    volume that was complete by the time anyone acted on it.
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
            # The `else :` matters: a bare `test … && echo` leaves the shell's
            # exit status at test's, so an ABSENT marker would make this probe
            # exit 1 and `check=True` would raise — turning "no marker" into a
            # crash instead of an answer.
            _PROBE_SCRIPT,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    listing, _, marker = proc.stdout.partition(_PROBE_SEPARATOR)
    return bool(listing.strip()), "MARKED" in marker


#: The label `@devcontainers/cli` infers when no `--id-label` is passed. Only
#: pre-#677 containers carry it *without* one of ours, and those are exactly the
#: leftovers a teardown still has to reach.
LEGACY_FOLDER_LABEL = "devcontainer.local_folder"


def _docker_ps_ids(*filters: str) -> list[str]:
    proc = subprocess.run(
        ["docker", "ps", "-aq", *[f"--filter={f}" for f in filters]],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in proc.stdout.split() if line]


def teardown_container_ids(
    names: DevcontainerNames,
    *,
    all_arches: bool = False,
    this_arch: list[str] | None = None,
    legacy: list[str] | None = None,
    legacy_labelled: list[str] | None = None,
) -> list[str]:
    """Container ids ``mise run stop``/``mise run prune`` should remove.

    Two sets, and the second is the whole reason this is not a one-line docker
    filter. **This clone's own container(s)**, found by the workspace label —
    the only one guaranteed to survive `--id-label` replacing the CLI's
    inferred label set. Plus **pre-#677 leftovers**: containers this workspace
    folder owns that carry none of our labels.

    ``all_arches`` decides how wide the first set is. ``stop`` passes nothing
    (``False``): scoped to THIS architecture (workspace label AND arch label)
    — taking down the *other* architecture's container is the regression the
    arch-scoping below exists to prevent, and `persistence` depends on it.
    ``prune`` passes ``True`` (#803): the workspace label alone, so every
    architecture's container is captured — the only way
    :func:`teardown_image_refs`'s ``containers`` default can reach every
    overlay image, since a container already removed can no longer be
    inspected for its ``.Image``.

    Filtering the legacy set on "lacks our workspace label" is what keeps the
    ``all_arches=False`` case arch-scoped. A bare ``devcontainer.local_folder``
    filter would also match the *other* architecture's container once both
    are up, so `stop` would silently take down a container the caller never
    mentioned — and inside the `persistence` gate, bring only one of them
    back.

    The four keyword parameters exist so the decision is testable without a
    docker daemon; each defaults to a real query.
    """
    mine = (
        (
            _docker_ps_ids(f"label={names.workspace_label}")
            if all_arches
            else _docker_ps_ids(
                f"label={names.workspace_label}", f"label={names.arch_label}"
            )
        )
        if this_arch is None
        else this_arch
    )
    folder = (
        _docker_ps_ids(f"label={LEGACY_FOLDER_LABEL}={names.workspace}")
        if legacy is None
        else legacy
    )
    ours = set(
        _docker_ps_ids(f"label={WORKSPACE_LABEL}")
        if legacy_labelled is None
        else legacy_labelled
    )
    ordered = list(mine) + [cid for cid in folder if cid not in ours]
    seen: set[str] = set()
    return [cid for cid in ordered if not (cid in seen or seen.add(cid))]


def teardown_main(*, all_arches: bool = False) -> int:
    """CLI entry: print the container ids ``stop``/``prune`` should remove."""
    for container_id in teardown_container_ids(resolve_names(), all_arches=all_arches):
        sys.stdout.write(f"{container_id}\n")
    return 0


#: The `@devcontainers/cli` overlay tag's fixed prefix, hardcoded in
#: `.devcontainer/devcontainer.json:97`
#: (``--tag=vsc-dotfiles-${...}-${...}``). It happens to equal
#: ``f"vsc-{RESOURCE_PREFIX}"`` today, but the two are NOT the same constant —
#: this one is baked into a JSON file nothing here renders, so it stays a
#: separate literal rather than borrowing ``RESOURCE_PREFIX``, which governs
#: container/volume names instead.
_OVERLAY_TAG_PREFIX = "vsc-dotfiles"

#: `docker image inspect --format '{{.Id}}\t{{json .RepoTags}}\t{{json .RepoDigests}}'`
#: always emits exactly this many tab-separated fields per line.
_IMAGE_INSPECT_FIELDS = 3


@dataclass(frozen=True)
class ImageRefs:
    """One local image's ``docker image inspect`` identity: tags and digests."""

    tags: tuple[str, ...]
    digests: tuple[str, ...]


def _docker_container_images(
    names: DevcontainerNames, container_ids: list[str]
) -> list[tuple[str, bool]]:
    """Each of ``container_ids``' ``(.Image, trusted)``, from one docker call.

    ``.Image``, never ``.ImageID`` or ``.Config.Image``. ``.ImageID`` is not a
    field ``docker inspect`` reports for a *container* on docker 29.x — a hard
    template error, not an empty answer. ``.Config.Image`` reports a TAG, and
    the wrong one: both architectures' containers share the CLI's per-folder
    tag, so reading it would collapse two overlay images into one and lose the
    other silently. ``.Image`` is written at create time and stays correct for
    a stopped container, which matters here — `docker ps -aq` already includes
    exited containers. ``docker container inspect``, not bare ``docker
    inspect``: the bare form falls back to IMAGES when no container matches,
    so a container removed mid-flight would silently resolve as an image
    instead of failing loudly (#803 C11).

    ``trusted`` is whether the container itself carries THIS clone's own
    ``WORKSPACE_LABEL=<hash>`` label — read via the SAME inspect call that
    already fetches ``.Image``, so the check :func:`teardown_image_refs` needs
    for #803 C2 costs nothing extra: a second ``docker ps --filter
    label=...`` call to re-derive it would be exactly the duplicate query
    #803 C6 closed. A container reached only through the legacy folder arm
    (pre-#677, no label of ours) is not trusted, and per #803 E1 contributes
    NOTHING through :func:`_trusted_by_container` — see that function for why.
    The label KEY is interpolated from ``WORKSPACE_LABEL`` rather than
    hardcoded a second time in the template (#803 E3): Go's ``index`` returns
    the empty string on a missing map key rather than erroring, so a literal
    left to drift out of sync with the constant would make every container
    silently untrusted with no error to notice it by.

    Returns ``[]`` without shelling out when there is nothing to ask about:
    ``docker container inspect`` with zero ids is an argument error, not an
    empty answer, and "no containers" must stay a quiet, exit-0 case (I10).
    """
    if not container_ids:
        return []
    proc = subprocess.run(
        [
            "docker",
            "container",
            "inspect",
            "--format",
            '{{.Image}}\t{{index .Config.Labels "' + WORKSPACE_LABEL + '"}}',
            *container_ids,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    pairs: list[tuple[str, bool]] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        image_id, label_value = line.split("\t", maxsplit=1)
        pairs.append((image_id, label_value == names.hash))
    return pairs


def _docker_image_refs() -> dict[str, ImageRefs]:
    """Every local image, keyed by its FULL ``sha256:…`` id.

    One ``docker image inspect`` call over every id ``docker images -aq``
    returns. The dict key comes from that call's OWN ``.Id`` field, never from
    the (possibly truncated) id ``docker images -aq`` printed: a container's
    ``.Image`` is always the full form, and comparing a truncated id against
    it fails silently as "not found" rather than loudly as a mismatch.
    """
    listed = subprocess.run(
        ["docker", "images", "-aq"],
        capture_output=True,
        text=True,
        check=True,
    )
    ids = [line for line in listed.stdout.split() if line]
    if not ids:
        return {}
    proc = subprocess.run(
        [
            "docker",
            "image",
            "inspect",
            "--format",
            "{{.Id}}\t{{json .RepoTags}}\t{{json .RepoDigests}}",
            *ids,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    refs: dict[str, ImageRefs] = {}
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        fields = line.split("\t", maxsplit=2)
        if len(fields) != _IMAGE_INSPECT_FIELDS:
            # #803 C9: name the offending line rather than a bare unpack
            # ValueError, which points at nothing.
            msg = f"docker image inspect: expected 3 tab-separated fields, got {line!r}"
            raise ValueError(msg)
        image_id, tags_json, digests_json = fields
        refs[image_id] = ImageRefs(
            tags=tuple(json.loads(tags_json) or []),
            digests=tuple(json.loads(digests_json) or []),
        )
    return refs


def _is_orphan_tag(tag: str, names: DevcontainerNames) -> bool:
    """Whether ``tag`` names an overlay of THIS clone with no container left.

    Two shapes, both derived exactly rather than guessed (#803 I3):

    * our own per-arch overlay tag, matched on the ``vsc-dotfiles-<hash>``
      PREFIX so one check covers every architecture without enumerating a
      set of arch words that grows whenever a new architecture is added
      (``no_platform_literals`` would not catch a bare word here either —
      its gate matches only the full ``linux/<arch>`` triple and excludes
      ``tests/`` outright, `platform_target.py:123,133-137` — the prefix
      match is still the right design, just for this reason instead);
    * the ``@devcontainers/cli``'s own per-folder tag,
      ``vsc-<basename>-<full-sha256-of-the-workspace-path>``. This is NOT the
      truncated digest :func:`workspace_hash` returns — it is derived fresh
      here from ``<basename>`` plus the FULL digest, never from the
      ``vsc-dotfiles-`` prefix above, which only lines up when the folder
      happens to be named ``dotfiles``.
    """
    full_digest = hashlib.sha256(names.workspace.encode()).hexdigest()
    return tag.startswith(
        (
            f"{_OVERLAY_TAG_PREFIX}-{names.hash}",
            f"vsc-{names.basename}-{full_digest}",
        )
    )


def _has_registry_slash(refs: ImageRefs) -> bool:
    """I5: refuse a candidate whose tags OR digests contain a registry `/`.

    This repo's base is always a ``ghcr.io/…`` reference and this repo's
    overlays are always bare ``vsc-…`` names — never the reverse — so a `/`
    on either field means "not one of ours". (The broader claim, "a registry
    reference always has a `/`", is false in general — ``busybox:stable``
    a few lines above is one of many single-segment Docker Hub images — but
    this guard only needs the narrower, true statement about THIS repo's
    images.) Checked over BOTH fields, not tags alone: docker 29 synthesizes a
    repo digest for a digest-pulled, untagged base image, so a tags-only guard
    misses exactly the shape it exists to catch.
    """
    return any("/" in ref for ref in (*refs.tags, *refs.digests))


def _trusted_by_container(
    container_pairs: list[tuple[str, bool]],
    all_images: dict[str, ImageRefs],
) -> dict[str, ImageRefs]:
    """Images reached through a container carrying OUR OWN workspace label.

    An UNTRUSTED (legacy-arm) container contributes NOTHING here (#803 E1,
    accepted gap — D2): that arm's containers have provenance this repo does
    not control, so an untagged image referenced by one cannot be shown to be
    ours, and admitting it on the folder label alone is precisely the C2
    hazard. r5 tried to soften this with `trusted or
    any(_is_orphan_tag(...))`, but that clause was DEAD CODE — it admits
    exactly what :func:`_orphaned_by_tag` already admits over the same
    ``all_images``, independent of any container at all, so mutating it to a
    bare `if trusted:` left the whole suite green. The cost of the tighter
    rule is real: a pre-#677 container whose overlay tag was later moved to a
    rebuilt image leaves the OLD image dangling and unreachable by either
    arm. Refusing to delete an image we cannot prove is ours is the correct
    side of that trade; the fix if it ever bites is to remove the stale
    container, not to widen this predicate back.

    An id absent from ``all_images`` is refused outright and logged (#803
    C1/E4) — the resolver could not identify it, and "unknown" must not be
    the permissive branch; the two docker calls behind the real default are
    separate processes and can race.
    """
    candidates: dict[str, ImageRefs] = {}
    for image_id, trusted in container_pairs:
        if not trusted:
            continue
        refs = all_images.get(image_id)
        if refs is None:
            logger.warning(
                "teardown-images: container image %s not found by `docker "
                "image inspect` — refusing to remove it rather than "
                "emitting a bare id (#803 C1)",
                image_id,
            )
            continue
        candidates[image_id] = refs
    return candidates


def _orphaned_by_tag(
    all_images: dict[str, ImageRefs],
    already: dict[str, ImageRefs],
    names: DevcontainerNames,
) -> dict[str, ImageRefs]:
    """Every remaining image matching one of our own orphan-tag shapes (I3)."""
    return {
        image_id: refs
        for image_id, refs in all_images.items()
        if image_id not in already
        and any(_is_orphan_tag(tag, names) for tag in refs.tags)
    }


def _removal_args(candidates: dict[str, ImageRefs]) -> list[str]:
    """I4/I5: emit refs (not ids), slash-guarded, de-duplicated over ref strings.

    The slash refusal LOGS, for the same reason the C1 refusal above does: a
    silent skip here and prune's "no overlay image resolved for this clone"
    are indistinguishable to the operator, so a candidate the guard removed
    looks exactly like a clone that owned nothing. Refusing is correct;
    refusing quietly on the one path that feeds `docker rmi` is how a real
    leak gets read as a clean prune.
    """
    result: list[str] = []
    seen: set[str] = set()
    for image_id, refs in candidates.items():
        if _has_registry_slash(refs):
            logger.warning(
                "teardown-images: image %s carries a registry reference "
                "(%s) — refusing to remove it, it is not one of this "
                "clone's locally built overlays (#803 I5)",
                image_id,
                next(ref for ref in (*refs.tags, *refs.digests) if "/" in ref),
            )
            continue
        for ref in refs.tags or (image_id,):
            if ref not in seen:
                seen.add(ref)
                result.append(ref)
    return result


def teardown_image_refs(
    names: DevcontainerNames,
    *,
    containers: list[tuple[str, bool]] | None = None,
    images: dict[str, ImageRefs] | None = None,
) -> list[str]:
    """``docker rmi`` arguments for every overlay image this clone owns.

    An unscoped tag grep (the pre-#803 ``mise run prune``) is neither
    sufficient nor safe: it is blind to an overlay carrying no tag at all,
    and — because ``vsc-dotfiles`` is not scoped to a hash — it matches every
    OTHER clone's overlay too. This resolves images by IDENTITY instead:
    through the container that references them (primary — this is what
    reaches an untagged overlay at all), plus two derivable orphan-tag shapes
    (:func:`_is_orphan_tag`) for an overlay whose container is already gone.

    Returns **refs**, not bare ids: every RepoTag of a resolved image when it
    has any, its bare id only when it has none. ``docker rmi <id>`` refuses an
    image referenced from multiple repositories without ``-f`` — measured,
    this clone's own amd64 overlay carries two — and ``-f`` is rejected
    outright: it also evicts an image a *stopped* container still references,
    which is exactly another clone's parked overlay, i.e. the cross-clone
    destruction this ticket exists to close. Emitting every tag is what makes
    that removal succeed without ``-f``: what is scoped is the IMAGE
    (identity — container or orphan-tag match), not each of its tags — a
    user can ``docker tag`` an admitted image under an unrelated name, and
    that tag is removed along with it too (#803 E9; this is not a claim that
    every tag on an admitted image is itself something we created). An
    untagged image is by definition singly-referenced, so its bare id
    needs no ``-f`` either. :func:`_has_registry_slash` is the
    destructive-path guard on top: a stopped container CAN reference the
    shared base image directly (measured on this host), and that must never
    reach ``docker rmi``.

    ``containers`` — ``(image_id, trusted)`` pairs, one per container this
    clone owns; ``trusted`` is whether the container itself carried OUR
    workspace label (see :func:`_docker_container_images`). A **trusted**
    image is scoped in through this path outright. An **untrusted** one
    (reached only through the pre-#677 legacy folder arm, whose provenance
    this repo does not control — a locally-tagged image unrelated to this
    repo can sit behind it, measured on this host) contributes NOTHING
    through this path at all (#803 E1) — see :func:`_trusted_by_container`
    for why "trust it if it also carries an orphan tag" was tried and found
    to be dead code. A TAGGED image behind an untrusted container is still
    found, independently, by :func:`_orphaned_by_tag`'s plain scan; only an
    UNTAGGED one behind an untrusted container is unreachable, which is the
    accepted gap.

    Callers that also remove containers MUST resolve ``containers``
    themselves and pass it explicitly, captured BEFORE removal (#803 I11):
    the default here calls :func:`teardown_container_ids` fresh, and once
    this clone's containers are gone that call returns ``[]`` — silently
    degrading this whole function to the orphan-tag scan alone.

    One surprise worth naming rather than treating as a defect: the sync
    record at ``~/.local/state/dotfiles/sync-*.json`` is not invalidated by
    this — it will name image ids that no longer exist after a prune, which is
    harmless because sync re-derives from the running container first.
    """
    container_pairs = (
        _docker_container_images(names, teardown_container_ids(names, all_arches=True))
        if containers is None
        else containers
    )
    all_images = _docker_image_refs() if images is None else images

    candidates = _trusted_by_container(container_pairs, all_images)
    candidates.update(_orphaned_by_tag(all_images, candidates, names))
    return _removal_args(candidates)


def teardown_images_main(*, container_ids: str | None = None) -> int:
    """CLI entry: print `docker rmi` refs for every overlay this clone owns.

    ``container_ids`` — whitespace-separated container ids ``mise run
    prune`` already captured via ``teardown --all-arches`` (#803 C6). When
    given (even as an empty string — "captured, and there were none"),
    resolves images from exactly those ids instead of re-running the
    `docker ps` query :func:`teardown_container_ids` would otherwise repeat,
    closing the TOCTOU between the two invocations. Omit it (``None``) to
    resolve everything fresh, e.g. for a standalone call.
    """
    names = resolve_names()
    containers = None
    if container_ids is not None:
        containers = _docker_container_images(names, container_ids.split())
    for ref in teardown_image_refs(names, containers=containers):
        sys.stdout.write(f"{ref}\n")
    return 0


def _volume_is_mounted(volume: str) -> bool:
    """True when any container (running or stopped) still has ``volume`` mounted.

    Stopped containers count: `mise run up` restarts one, and a copy taken while
    the source is attached to something that may resume is not a copy anyone
    should trust.
    """
    proc = subprocess.run(
        ["docker", "ps", "-aq", "--filter", f"volume={volume}"],
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
    populated, marked = (
        _probe_volume(names.home_volume) if target_exists else (False, False)
    )
    plan = plan_home_volume_migration(
        names,
        existing_volumes=volumes,
        target_populated=populated,
        target_marked=marked,
        source_in_use=_volume_is_mounted(names.legacy_home_volume),
    )
    sys.stdout.write(f"{render_plan(plan)}\n")
    # Flush before spawning anything: our stdout is block-buffered when piped,
    # so without this the child's output lands ABOVE the plan that explains it
    # — which is exactly backwards for an operation the reader is meant to
    # approve as it happens. (Observed on the first real --apply run.)
    sys.stdout.flush()
    if not plan.commands:
        # A refusal that exits 0 under --apply is a silent no-op: the caller
        # asked for a copy, got none, and nothing said so. "Nothing to do" and
        # "I will not do this" must not share an exit code.
        return 1 if apply and plan.action in REFUSED_ACTIONS else 0
    if not apply:
        sys.stdout.write("(dry run — pass --apply to execute)\n")
        return 0
    for cmd in plan.commands:
        sys.stdout.write(f"==> {shlex.join(cmd)}\n")
        sys.stdout.flush()
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
