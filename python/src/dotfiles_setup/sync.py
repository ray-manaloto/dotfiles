# Copyright (c) 2026 Raymond Manaloto
"""Devcontainer sync: converge onto the latest CI-built image, then verify.

``dotfiles-setup docker sync`` (wrapped by ``mise run sync``) is the one
entrypoint for "make my devcontainer run the newest image ci.yml published
and prove everything works". It handles every starting state:

- **container running / stopped / absent** — detected via this workspace's
  two #677 id labels (``dotfiles.workspace`` + ``dotfiles.arch``, combined
  with AND); ``--id-label`` REPLACES the CLI's inferred
  ``devcontainer.local_folder`` label, so that one no longer identifies
  anything post-#677. The action matrix below converges each state onto a
  running, verified container. A STOPPED container whose overlay id no
  longer matches the last converge's record for this architecture is
  rebuilt rather than reused (#800 F1) — ``container_image_id`` now answers
  for a stopped container too, not just a running one.
- **local tag stale vs registry** — the registry manifest digest
  (``docker buildx imagetools inspect``, no pull) is compared against the
  digest the *local tag* points at. Comparing the local **tag** matters:
  after PR #169 merged, the registry ``:dev`` moved while the local
  ``:dev`` tag silently kept pointing at the pre-merge image — a naive
  "is some current image present" check would have missed it.
- **in-flight CI** — if a ``ci.yml`` run is in progress on the target
  branch, the image about to be synced may be superseded shortly; sync
  reports it and continues (``--wait`` watches the run to completion
  first, cross-checking the API conclusion per
  ``.claude/rules/gh-cli-watch.md``).

Action matrix (``decide_action``):

======  ===============  =========  ==========================================
stale?  overlay current  container  action
======  ===============  =========  ==========================================
yes*    --               any        refresh local tag (buildkit) + dev-rebuild
no      no               any        rebuild (this arch's overlay is stale)
no      yes              running    verify only (digest fast-path)
no      yes              stopped    up (reuse — CLI starts, never recreates)
no      yes              absent     up (create container)
======  ===============  =========  ==========================================

``*`` ``--force`` behaves like stale. "overlay current" is
``SyncStatus.container_current`` — no container found (absent, or the probe
failed) counts as current, the non-destructive default.

When stale, the local tag is refreshed EXPLICITLY via
``docker buildx build --pull`` before ``dev-rebuild`` — the overlay's
``FROM ${BASE_IMAGE}`` resolves against the local image store, so
trusting ``devcontainer up --build-no-cache`` to re-fetch a stale tag
would rebuild on old bytes. Classic ``docker pull`` is never used (it
wedges on the ~38GB image; see ``feedback_mise_local_toml_replaces_task``).

Verification is tiered: the default gate is
:func:`dotfiles_setup.container.verify_latest` (bind-mount currency +
smoke tiers 1-3, incl. the tier-1 image-identity base-currency check);
``--full`` runs the whole ``mise run verify-local`` chain (R1/R2/R3 +
persistence + secrets).

Logic lives here (Python), not in the mise task, per the repo's
zero-bash-logic policy; ``mise run sync`` is a thin caller. Lifecycle
invocations delegate to ``mise run up`` / ``mise run dev-rebuild`` so the
task bodies stay the single source of truth for env (BASE_IMAGE,
DOCKER_DEFAULT_PLATFORM, workspace hash, ssh known-hosts cleanup).
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path as PathLib
from typing import TYPE_CHECKING, Literal

from dotfiles_setup import child_env
from dotfiles_setup.container import verify_latest
from dotfiles_setup.devcontainer_names import resolve_names
from dotfiles_setup.platform_target import published_targets, resolve_platform

if TYPE_CHECKING:
    from pathlib import Path

    from dotfiles_setup.devcontainer_names import DevcontainerNames

logger = logging.getLogger(__name__)

_CI_WORKFLOW = "ci.yml"

# Quick network probes (registry manifest inspect, gh API) — bounded so a
# dead link surfaces instead of blocking.
_PROBE_TIMEOUT_S = 120.0

ContainerState = Literal["running", "stopped", "absent"]
Action = Literal["rebuild", "up", "verify-only"]

_PR_TAG_RE = re.compile(r"^pr-(\d+)$")


@dataclasses.dataclass(frozen=True, kw_only=True)
class SyncOptions:
    """CLI-facing knobs for one sync invocation."""

    tag: str = "dev"
    base_repo: str = "ghcr.io/ray-manaloto/dotfiles-devcontainer"
    force: bool = False
    check_only: bool = False
    full: bool = False
    wait: bool = False

    @property
    def image_ref(self) -> str:
        """Full registry reference the sync converges onto."""
        return f"{self.base_repo}:{self.tag}"


@dataclasses.dataclass(frozen=True)
class SyncStatus:
    """The observed world state sync decides from."""

    image_ref: str
    registry_digest: str | None
    local_digests: tuple[str, ...]
    local_image_id: str | None
    container_state: ContainerState
    container_image_id: str | None = None
    synced_state: SyncRecord | None = None
    arch: str = ""
    workspace_hash: str = ""

    @property
    def stale(self) -> bool:
        """True when the local tag is not known to carry the registry bytes.

        Converged means EITHER the registry manifest digest appears in the
        local tag's RepoDigests (the plain-pull path) OR the sync state
        record says this exact registry digest was refreshed onto this
        exact local image id (the buildkit-refresh path — review finding
        [0]: a buildkit ``--output type=docker`` re-export mints a NEW
        local manifest digest, so RepoDigests can never converge after a
        refresh; the state record is the durable convergence witness).

        A missing local tag counts as stale. An unreachable registry
        (``None``) does NOT: sync must not tear down a working container
        on a network blip.
        """
        if self.registry_digest is None:
            return False
        if self.registry_digest in self.local_digests:
            return False
        return not (
            self.synced_state is not None
            and self.synced_state.registry_digest == self.registry_digest
            and self.synced_state.local_image_id == self.local_image_id
            and self.local_image_id is not None
        )

    @property
    def container_current(self) -> bool:
        """The container's overlay image matches the last converge's record.

        Review finding [1]: verify-only must not bless a container left
        over from an older converge. The container runs the OVERLAY image
        (vsc-…), never the base tag itself, so the comparison is against
        the overlay id captured in the sync record at converge time —
        self-consistent on both sides. No record / unknown ids count as
        current (non-destructive default; smoke tier-1 identity still
        guards config-level staleness in the verify step).

        #800 extends the record to hold one overlay id PER ARCHITECTURE
        (:attr:`SyncRecord.containers`), so a host running both
        architectures from one clone doesn't ping-pong a rebuild every time
        the other architecture syncs. #894 keys those entries by workspace
        AND architecture (:func:`container_key`) — the arch-only key made
        every clone on the host share one entry per arch.

        #894 also drops the two UNSCOPED read fallbacks (the bare-``arch``
        key and ``legacy_container_image_id``). Neither records which
        workspace wrote it, so consulting one reproduces the very defect
        the composite key fixes. A record written under an older shape
        therefore reads as "no entry" and costs this workspace exactly one
        rebuild — the fail-safe direction: an unnecessary rebuild, never a
        wrong image.

        #800 round 2 (F1): a STOPPED container is compared too, not
        auto-blessed by a ``container_state != "running"`` shortcut —
        ``container_image_id`` now answers for a stopped container as well
        as a running one (preferring running when both exist), so a
        container left behind on a superseded base is caught here instead
        of silently reused by ``up``.

        Clause order: ``registry_digest is None`` (offline — F4, never take
        a destructive action on an unreachable registry) → ``container_image_id
        is None`` (absent container, or the probe failed — non-destructive)
        → ``record is None`` → this architecture's recorded overlay id, or
        (#800 F10) the legacy pre-#800 flat id when this architecture has
        never converged under the per-arch record shape.
        """
        if self.registry_digest is None:
            return True
        if self.container_image_id is None:
            return True
        record = self.synced_state
        if record is None:
            return True
        recorded = record.containers.get(container_key(self.workspace_hash, self.arch))
        if recorded is None:
            return False
        return self.container_image_id == recorded


@dataclasses.dataclass(frozen=True)
class SyncRecord:
    """Durable witness of the last successful converge for an image ref.

    One record per ``image_ref`` (buildkit mints a new ``local_image_id`` on
    every refresh — see :attr:`SyncStatus.stale`'s docstring — so the record
    stays shared across architectures, not keyed per-arch). ``containers``
    holds one overlay image id per architecture that has converged onto the
    CURRENT ``local_image_id`` (#800).

    ``legacy_container_image_id`` is parsed but **no longer consulted**
    (#894): it is the pre-#800 flat ``container_image_id`` key, which names
    no workspace, so trusting it lets one clone bless another clone's
    overlay. It stays on the dataclass as a faithful record of what the
    file holds, if the on-disk record
    still carries one. :func:`write_sync_record` never writes it — once a
    record round-trips through this dataclass it only ever carries the new
    per-architecture shape.
    """

    registry_digest: str
    local_image_id: str
    containers: dict[str, str] = dataclasses.field(default_factory=dict)
    legacy_container_image_id: str | None = None


def container_key(workspace_hash: str, arch: str) -> str:
    """The ``containers`` key one workspace+architecture pair owns.

    #894: this key was ``arch`` alone. ``_state_file`` names the record after
    the image ref only, so every clone on the host shares one file — and an
    arch-only key meant clone A's overlay id and clone B's overlay id both
    landed on ``containers["amd64"]``. Whichever clone converged last for an
    architecture was the only one whose state survived.

    The workspace dimension was not overlooked so much as never considered:
    :func:`write_sync_record`'s docstring reasons carefully about preserving
    every OTHER architecture's entry, and never about another workspace's.

    ``registry_digest`` and ``local_image_id`` stay un-keyed on purpose — the
    local image really is one host-wide object. Only ``containers`` is
    per-workspace, so the fix keys the entry rather than splitting the file.
    """
    return f"{workspace_hash}:{arch}"


def _state_file(image_ref: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", image_ref)
    return PathLib.home() / ".local" / "state" / "dotfiles" / f"sync-{safe}.json"


def read_sync_record(image_ref: str) -> SyncRecord | None:
    """The last recorded converge for ``image_ref`` (or None).

    A legacy record (pre-#800, flat ``container_image_id`` key, no
    ``containers``) reads as ``containers={}`` plus
    :attr:`SyncRecord.legacy_container_image_id` set from that flat key
    (#800 F10) — the architecture it names skips a spurious rebuild; every
    OTHER architecture still rebuilds once after the upgrade, because its id
    genuinely differs. A corrupt ``containers`` value (present but not a
    JSON object) degrades to ``{}`` rather than raising, and a corrupt
    legacy value (present but not a string — e.g. a stray number) degrades
    to ``None`` the same way (#800 F8): :attr:`SyncStatus.container_current`
    calls ``.get()`` on ``containers`` and compares against the legacy id
    directly, so a malformed state file must not crash the whole invocation
    or trigger a spurious rebuild.

    The top-level payload itself must also be a JSON object — a state file
    holding a bare list or string has no ``.get`` to call and reads as "no
    record" rather than raising ``AttributeError`` uncaught.
    """
    try:
        data = json.loads(_state_file(image_ref).read_text())
        if not isinstance(data, dict):
            return None
        containers = data.get("containers")
        if not isinstance(containers, dict):
            containers = {}
        legacy = data.get("container_image_id")
        if not isinstance(legacy, str):
            legacy = None
        return SyncRecord(
            registry_digest=data["registry_digest"],
            local_image_id=data["local_image_id"],
            containers=containers,
            legacy_container_image_id=legacy,
        )
    except OSError, json.JSONDecodeError, KeyError:
        return None


def write_sync_record(workspace: Path, image_ref: str, registry: str) -> None:
    """Record that ``registry`` digest now backs ``image_ref`` locally.

    Resolves the workspace+architecture names independently of
    ``observe()`` — safe because ``_mise_env`` (below) copies
    ``os.environ`` for the lifecycle CHILD only and never mutates this
    process's own environment, so both resolutions read identical env.
    ``resolve_names`` can raise ``ValueError`` on a malformed
    ``DOTFILES_PLATFORM``/``DEVCONTAINER_SSH_PORT`` pin; that cannot newly
    happen HERE because ``observe()`` already resolved successfully against
    the same environment earlier in this same converge — do not thread
    ``names`` through as a parameter to guard against it.

    Merges into the existing on-disk record when it is still witness-current
    for this ``image_ref`` (same registry digest AND local image id) —
    that preserves every OTHER architecture's ``containers`` entry, so an
    architecture flip never forces a spurious rebuild. Otherwise (no prior
    record, or the tag genuinely moved) starts a fresh record holding only
    this architecture's entry — a prior architecture's entry described a
    now-superseded local image id and would be a lie to keep.
    """
    image_id = local_image_id(image_ref)
    if image_id is None:
        return
    names = resolve_names(workspace=workspace)
    existing = read_sync_record(image_ref)
    if (
        existing is not None
        and existing.registry_digest == registry
        and existing.local_image_id == image_id
    ):
        containers = dict(existing.containers)
    else:
        containers = {}
    cid = container_image_id(names)
    if cid is not None:
        containers[container_key(names.hash, names.arch)] = cid
    else:
        # #800 F7: a probe failure or an absent container silently dropped
        # this architecture's entry — the record still wrote, just without
        # it, and nothing said so.
        logger.warning(
            "sync record for %s written without a container id for %s",
            image_ref,
            names.arch,
        )
    path = _state_file(image_ref)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(
            {
                "registry_digest": registry,
                "local_image_id": image_id,
                "containers": containers,
            }
        )
        + "\n"
    )
    # #894: the state file is shared by every clone on this host, so a plain
    # write_text lets a concurrent converge read a half-written file. Write to
    # a sibling temp file and rename — rename is atomic within a directory, so
    # a reader sees either the old record or the new one, never a torn one. A
    # lost update (two writers, last wins) is still possible and is fail-safe:
    # the losing clone reads no entry for its key and rebuilds once.
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(payload)
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def _run(
    cmd: list[str], *, timeout: float | None = None
) -> subprocess.CompletedProcess[str]:
    # Review finding [3]: a hung probe must degrade to a failed probe,
    # never crash sync with an uncaught TimeoutExpired. Same for a missing
    # binary (probe-observed: in-container pytest has no docker CLI).
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            env=child_env.without_git_context(),
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=cmd, returncode=124, stdout="", stderr="probe timed out"
        )
    except OSError as exc:
        return subprocess.CompletedProcess(
            args=cmd, returncode=127, stdout="", stderr=str(exc)
        )


def _stream(
    cmd: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> int:
    """Run a long operation streaming to the terminal (never wait blind)."""
    return subprocess.run(
        cmd,
        check=False,
        env=child_env.without_git_context(env),
        cwd=cwd,
    ).returncode


def registry_digest(image_ref: str) -> str | None:
    """Manifest digest the registry serves for ``image_ref`` (no pull).

    Under a multi-architecture tag this is the **index** digest, and #674 asked
    whether that still compares like-for-like against :func:`local_digests`'s
    ``RepoDigests``. Measured, both arms, against a real ghcr index built the
    way ours is — buildx, two architectures, an attestation manifest beside
    each (``ghcr.io/astral-sh/uv:latest``), and cross-checked on a Docker Hub
    index (``alpine:3.20``). ``imagetools inspect --format '{{json
    .Manifest.Digest}}'`` and, after a ``docker pull`` scoped to ONE
    architecture with ``--platform``, ``image inspect --format '{{json
    .RepoDigests}}'`` return the **same index digest** — for *either*
    architecture asked for. A ``--platform`` pull selects which manifest is
    *materialised*, not which digest is *recorded*, so :attr:`SyncStatus.stale`
    needs no per-architecture handling and none was added. Do not "fix" this on
    the strength of the ``can never converge`` comment above — that one is
    about a buildkit re-export, not about manifest lists.
    """
    res = _run(
        [
            "docker",
            "buildx",
            "imagetools",
            "inspect",
            image_ref,
            "--format",
            "{{json .Manifest.Digest}}",
        ],
        timeout=_PROBE_TIMEOUT_S,
    )
    if res.returncode != 0:
        logger.warning(
            "registry inspect failed for %s: %s", image_ref, res.stderr.strip()
        )
        return None
    return json.loads(res.stdout.strip())


def local_digests(image_ref: str) -> tuple[str, ...]:
    """ALL digests the LOCAL tag carries for its repo (empty if absent).

    All, not first: under the containerd store one image can carry
    multiple digests for the same repo (review finding [0] sub-point).
    """
    res = _run(
        ["docker", "image", "inspect", image_ref, "--format", "{{json .RepoDigests}}"]
    )
    if res.returncode != 0:
        return ()
    repo = image_ref.rsplit(":", 1)[0]
    out = []
    for entry in json.loads(res.stdout.strip()):
        entry_repo, _, digest = entry.partition("@")
        if entry_repo == repo:
            out.append(digest)
    return tuple(out)


def local_image_id(image_ref: str) -> str | None:
    """The local image id the tag points at (None if absent)."""
    res = _run(["docker", "image", "inspect", image_ref, "--format", "{{.Id}}"])
    return res.stdout.strip() or None if res.returncode == 0 else None


def container_image_id(names: DevcontainerNames) -> str | None:
    """Image id of the devcontainer for this workspace+arch (or None).

    Filters on BOTH #677 id labels (workspace hash AND arch), combined with
    a logical AND — mirrors ``devcontainer_names.teardown_container_ids``,
    whose docstring explains why a bare workspace filter also matches the
    OTHER architecture's container once both are up.

    Prefers a RUNNING match (``docker ps -q``); only when none is running
    does it fall back to a STOPPED one (``docker ps -aq``), so a non-running
    container's overlay id can be compared for currency too (#800 F1). The
    order matters and is not a bare ``-aq``: ``docker ps -a`` lists
    newest-created first, so a newer exited leftover would otherwise shadow
    a genuinely running container and hand back the wrong id.
    """
    filters = [
        "--filter",
        f"label={names.workspace_label}",
        "--filter",
        f"label={names.arch_label}",
    ]
    cid = _run(["docker", "ps", "-q", *filters]).stdout.strip()
    if not cid:
        cid = _run(["docker", "ps", "-aq", *filters]).stdout.strip()
    if not cid:
        return None
    res = _run(["docker", "inspect", cid.splitlines()[0], "--format", "{{.Image}}"])
    return res.stdout.strip() or None if res.returncode == 0 else None


def container_state(names: DevcontainerNames) -> ContainerState:
    """Devcontainer state for this workspace+arch: running, stopped, absent."""
    res = _run(
        [
            "docker",
            "ps",
            "-a",
            "--filter",
            f"label={names.workspace_label}",
            "--filter",
            f"label={names.arch_label}",
            "--format",
            "{{.State}}",
        ]
    )
    states = res.stdout.strip().splitlines()
    if not states:
        return "absent"
    return "running" if "running" in states else "stopped"


def tag_branch(tag: str) -> str | None:
    """CI branch whose ci.yml publishes ``tag`` (None = not CI-tracked).

    ``dev`` is promoted from main; ``pr-NNN`` is built from that PR's
    head branch (resolved via gh). Anything else (bare shas, hash
    markers) is immutable — no in-flight run can supersede it.
    """
    if tag == "dev":
        return "main"
    match = _PR_TAG_RE.match(tag)
    if match is None:
        return None
    res = _run(
        ["gh", "pr", "view", match.group(1), "--json", "headRefName"],
        timeout=_PROBE_TIMEOUT_S,
    )
    if res.returncode != 0:
        logger.warning("gh pr view %s failed: %s", match.group(1), res.stderr.strip())
        return None
    branch: str = json.loads(res.stdout)["headRefName"]
    return branch


def inflight_ci_runs(branch: str) -> list[dict[str, str]]:
    """Unfinished ci.yml runs on ``branch`` (may supersede the target image)."""
    res = _run(
        [
            "gh",
            "run",
            "list",
            "--workflow",
            _CI_WORKFLOW,
            "--branch",
            branch,
            "--limit",
            "10",
            "--json",
            "databaseId,status,displayTitle,url",
        ],
        timeout=_PROBE_TIMEOUT_S,
    )
    if res.returncode != 0:
        logger.warning("gh run list failed: %s", res.stderr.strip())
        return []
    runs: list[dict[str, str]] = json.loads(res.stdout)
    return [r for r in runs if r["status"] != "completed"]


def wait_for_run(run_id: str) -> bool:
    """Watch a run to completion; conclusion cross-checked via the API.

    ``gh run watch --exit-status`` alone is untrustworthy (has reported 0
    prematurely — see ``feedback_gh_run_watch``); the API ``conclusion``
    field is the evidence.
    """
    _stream(["gh", "run", "watch", run_id, "--exit-status"])
    res = _run(
        ["gh", "run", "view", run_id, "--json", "conclusion", "--jq", ".conclusion"],
        timeout=_PROBE_TIMEOUT_S,
    )
    conclusion = res.stdout.strip()
    logger.info("run %s conclusion: %s", run_id, conclusion)
    return conclusion == "success"


def local_platforms(image_ref: str) -> frozenset[str]:
    """Published platforms PRESENT under the local ``image_ref`` tag.

    ``docker image inspect --platform <p> <ref>`` rc==0 means the local tag
    already carries that manifest (probed against docker 29.7.2: each
    ``published_targets()`` triple matches, including a microarch-level-less
    ARM manifest against arm64's full triple; the level-less spelling of an
    architecture does NOT match a stored microarch-level manifest, so callers
    must probe the full triple, never :func:`platform_target.os_arch`, which
    drops the level). An absent tag, or any probe failure, yields an empty
    set.
    """
    present = set()
    for target in published_targets():
        res = _run(
            [
                "docker",
                "image",
                "inspect",
                "--platform",
                target.platform,
                image_ref,
                "--format",
                "{{.Id}}",
            ]
        )
        if res.returncode == 0:
            present.add(target.platform)
    return frozenset(present)


def refresh_local_tag(image_ref: str) -> bool:
    """Re-anchor the local tag onto the registry's current manifest.

    Buildkit ``--pull`` on a trivial ``FROM`` forces registry resolution
    and loads the result into the docker store under the same tag; layers
    already present locally are reused, so a promote-only retag (new
    manifest pointer, same bytes) costs seconds, not a 38GB pull.

    Requests the UNION of this host's own platform (``resolve_platform()``)
    and whatever published platforms are already present under the local
    tag (:func:`local_platforms`, #800 F2) — not every published platform
    unconditionally. A single-platform ``type=docker`` export CLOBBERS the
    other architecture's layers under the shared ``:dev`` tag, so on a host
    running both architectures from one clone, refreshing only this host's
    platform would break the other arch's ``--pull=never`` verify step
    (measured rc=125, "does not provide the specified platform") — the union
    keeps every platform this local tag already served, while a single-arch
    host that has never seen the other platform never pays to fetch it.

    A ``--output type=docker`` export of MORE than one platform needs the
    containerd image store (Docker Desktop default) — see the failure detail
    ``_converge`` reports; that requirement only bites when the union above
    resolves to two platforms, which it does on a host running both
    architectures.
    """
    platform = resolve_platform()
    wanted = {platform} | local_platforms(image_ref)
    platforms = ",".join(
        target.platform for target in published_targets() if target.platform in wanted
    )
    if not platforms:
        msg = f"{platform!r} is not a published platform; refresh cannot target it"
        raise ValueError(msg)
    proc = subprocess.run(
        [
            "docker",
            "buildx",
            "build",
            "--pull",
            "--platform",
            platforms,
            "--output",
            "type=docker",
            "-t",
            image_ref,
            "-",
        ],
        input=f"FROM {image_ref}\n",
        text=True,
        check=False,
    )
    return proc.returncode == 0


def decide_action(status: SyncStatus, *, force: bool) -> Action:
    """Pure decision matrix — see the module docstring table.

    #800 F1: the currency check moves ABOVE the state check. A stopped
    container the state check alone would send straight to ``up`` (reuse)
    might be sitting on a superseded overlay id — currency has to be
    decided first, or a stale stopped container gets reused and recorded
    "current" forever.
    """
    if force or status.stale:
        return "rebuild"
    if not status.container_current:
        return "rebuild"
    if status.container_state != "running":
        return "up"
    return "verify-only"


def observe(workspace: Path, image_ref: str) -> SyncStatus:
    """Collect the world state the decision matrix needs."""
    names = resolve_names(workspace=workspace)
    return SyncStatus(
        image_ref=image_ref,
        registry_digest=registry_digest(image_ref),
        local_digests=local_digests(image_ref),
        local_image_id=local_image_id(image_ref),
        container_state=container_state(names),
        container_image_id=container_image_id(names),
        synced_state=read_sync_record(image_ref),
        arch=names.arch,
        workspace_hash=names.hash,
    )


def _mise_env(image_ref: str) -> dict[str, str]:
    """Env for lifecycle mise tasks: BASE_IMAGE override for non-:dev tags."""
    env = os.environ.copy()
    env["BASE_IMAGE"] = image_ref
    return env


def _report_inflight(tag: str, *, wait: bool) -> None:
    """Report (or await) unfinished ci.yml runs that may supersede ``tag``."""
    branch = tag_branch(tag)
    if branch is None:
        if wait:
            # Review finding [4]: --wait must fail loud when the CI probe
            # itself failed — 'await CI then sync' silently degrading to
            # 'sync now' breaks the caller's ordering assumption.
            sys.stdout.write(
                "FAIL  --wait requested but the CI branch for this tag could "
                "not be resolved (gh error or untracked tag) — aborting\n"
            )
            raise SystemExit(1)
        return
    runs = inflight_ci_runs(branch)
    if not runs:
        return
    for run in runs:
        sys.stdout.write(
            f"NOTE  ci.yml run {run['databaseId']} is {run['status']} on "
            f"{branch} — the {tag} image may be superseded shortly "
            f"({run['url']})\n"
        )
    if wait:
        newest = runs[0]
        sys.stdout.write(f"==> --wait: watching run {newest['databaseId']}\n")
        if not wait_for_run(str(newest["databaseId"])):
            sys.stdout.write(
                "FAIL  awaited ci.yml run did not conclude success — not "
                "syncing to an image from a failed pipeline\n"
            )
            raise SystemExit(1)


def _converge(workspace: Path, status: SyncStatus, action: Action) -> tuple[bool, str]:
    """Execute the decided action; returns (ok, detail)."""
    if action == "verify-only":
        return True, "local tag current + container running (digest fast-path)"
    if action == "rebuild":
        if status.container_state == "running":
            sys.stdout.write(
                "WARN  rebuilding: in-container sessions will be killed "
                "(workspace bind-mount and home volume persist)\n"
            )
        if status.stale:
            try:
                refreshed = refresh_local_tag(status.image_ref)
            except ValueError as exc:
                return False, str(exc)
            if not refreshed:
                return False, (
                    f"buildkit tag refresh failed for {status.image_ref} "
                    "(multi-platform type=docker export needs the containerd "
                    "image store — Docker Desktop default)"
                )
        rc = _stream(
            ["mise", "run", "dev-rebuild"],
            env=_mise_env(status.image_ref),
            cwd=workspace,
        )
        if rc == 0 and status.registry_digest:
            write_sync_record(workspace, status.image_ref, status.registry_digest)
        return rc == 0, f"dev-rebuild rc={rc}"
    rc = _stream(["mise", "run", "up"], env=_mise_env(status.image_ref), cwd=workspace)
    if rc == 0 and status.registry_digest:
        write_sync_record(workspace, status.image_ref, status.registry_digest)
    return rc == 0, f"up rc={rc}"


def _verify(workspace: Path, *, full: bool, image_ref: str) -> bool:
    """Run the post-converge gate: smoke by default, verify-local on --full."""
    if full:
        # Review finding [28]: verify-local must validate the SAME image
        # this sync targets — without the env override, a `--tag pr-NNN`
        # sync would verify (and its up/persistence steps rebuild) :dev.
        rc = _stream(
            ["mise", "run", "verify-local"],
            env=_mise_env(image_ref),
            cwd=workspace,
        )
        sys.stdout.write(f"{'PASS' if rc == 0 else 'FAIL'}  verify-local rc={rc}\n")
        return rc == 0
    checks = verify_latest(workspace, run_smoke=True)
    for check in checks:
        marker = "PASS" if check.ok else "FAIL"
        sys.stdout.write(f"{marker}  {check.name}: {check.detail}\n")
    return all(c.ok for c in checks)


def sync_main(workspace: Path, options: SyncOptions | None = None) -> int:
    """CLI entry: observe → (report CI) → converge → verify. 0 = verified."""
    opts = options if options is not None else SyncOptions()
    image_ref = opts.image_ref
    _report_inflight(opts.tag, wait=opts.wait)

    status = observe(workspace, image_ref)
    # #800 F4: an unreachable registry makes container_current True
    # unconditionally (never take a destructive action on currency grounds
    # while offline) — so [CONTAINER OUTDATED] goes silent here too even
    # when the record plainly disagrees with the running container. Correct
    # under "staleness unknown", not evidence of currency.
    sys.stdout.write(
        f"==> {image_ref}\n"
        f"    registry: {status.registry_digest or 'UNREACHABLE'}\n"
        f"    local:    {', '.join(status.local_digests) or 'ABSENT'}\n"
        f"    container: {status.container_state}"
        f"{'  [STALE]' if status.stale else ''}"
        f"{'  [CONTAINER OUTDATED]' if not status.container_current else ''}\n"
    )
    if status.registry_digest is None:
        sys.stdout.write(
            "WARN  registry unreachable — staleness unknown; proceeding "
            "against the local tag only\n"
        )

    if opts.check_only:
        # Review finding [2]: an unreachable registry is UNKNOWN, not
        # 'current' — scripts gating on --check must be able to tell
        # 'verified current' (0) from 'could not verify' (2).
        if status.registry_digest is None:
            sys.stdout.write("check: UNKNOWN — registry unreachable\n")
            return 2
        stale = status.stale
        outdated = not status.container_current
        if stale:
            sys.stdout.write("check: STALE — sync would rebuild\n")
        elif outdated:
            sys.stdout.write(
                "check: OUTDATED — sync would rebuild this architecture's container\n"
            )
        else:
            sys.stdout.write("check: current\n")
        return 1 if stale or outdated else 0

    action = decide_action(status, force=opts.force)
    sys.stdout.write(f"==> action: {action}\n")
    ok, detail = _converge(workspace, status, action)
    sys.stdout.write(f"{'PASS' if ok else 'FAIL'}  converge: {detail}\n")
    if not ok:
        return 1

    if not _verify(workspace, full=opts.full, image_ref=image_ref):
        sys.stdout.write(
            "\nsync: verification failed — the container is NOT a valid "
            "environment (see .claude/rules/verify-before-advancing.md)\n"
        )
        return 1
    sys.stdout.write(f"\nsync: OK — container verified on {image_ref}\n")
    return 0
