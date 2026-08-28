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
  running, verified container.
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

======  =========  ===========================================
stale?  container  action
======  =========  ===========================================
yes*    any        refresh local tag (buildkit) + dev-rebuild
no      running    verify only (digest fast-path)
no      stopped    up (reuse container)
no      absent     up (create container)
======  =========  ===========================================

``*`` ``--force`` behaves like stale.

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
from dotfiles_setup.platform_target import published_targets

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
        """The running container matches the last converge's record.

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
        the other architecture syncs. Clause order matters:
        ``container_image_id is None`` (probe failed — non-destructive)
        MUST be checked before ``containers.get(self.arch) is None``
        (this architecture has never converged onto this tag — that DOES
        mean rebuild, not "unknown, so current").
        """
        if self.container_state != "running":
            return True
        if self.container_image_id is None:
            return True
        record = self.synced_state
        if record is None:
            return True
        recorded = record.containers.get(self.arch)
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
    """

    registry_digest: str
    local_image_id: str
    containers: dict[str, str] = dataclasses.field(default_factory=dict)


def _state_file(image_ref: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", image_ref)
    return PathLib.home() / ".local" / "state" / "dotfiles" / f"sync-{safe}.json"


def read_sync_record(image_ref: str) -> SyncRecord | None:
    """The last recorded converge for ``image_ref`` (or None).

    A legacy record (pre-#800, flat ``container_image_id`` key, no
    ``containers``) reads as ``containers={}`` — every architecture rebuilds
    once after the upgrade (accepted; see #800 spec §3). A corrupt
    ``containers`` value (present but not a JSON object) also degrades to
    ``{}`` rather than raising: :attr:`SyncStatus.container_current` calls
    ``.get()`` on it from inside an f-string at the top of ``sync_main``, so
    a malformed state file must not crash the whole invocation.
    """
    try:
        data = json.loads(_state_file(image_ref).read_text())
        containers = data.get("containers")
        if not isinstance(containers, dict):
            containers = {}
        return SyncRecord(
            registry_digest=data["registry_digest"],
            local_image_id=data["local_image_id"],
            containers=containers,
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
        containers[names.arch] = cid
    path = _state_file(image_ref)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "registry_digest": registry,
                "local_image_id": image_id,
                "containers": containers,
            }
        )
        + "\n"
    )


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
    """Image id of the RUNNING devcontainer for this workspace+arch (or None).

    Filters on BOTH #677 id labels (workspace hash AND arch), combined with
    a logical AND — mirrors ``devcontainer_names.teardown_container_ids``,
    whose docstring explains why a bare workspace filter also matches the
    OTHER architecture's container once both are up.
    """
    cid = _run(
        [
            "docker",
            "ps",
            "-q",
            "--filter",
            f"label={names.workspace_label}",
            "--filter",
            f"label={names.arch_label}",
        ]
    ).stdout.strip()
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


def refresh_local_tag(image_ref: str) -> bool:
    """Re-anchor the local tag onto the registry's current manifest.

    Buildkit ``--pull`` on a trivial ``FROM`` forces registry resolution
    and loads the result into the docker store under the same tag; layers
    already present locally are reused, so a promote-only retag (new
    manifest pointer, same bytes) costs seconds, not a 38GB pull.

    Requests EVERY published platform (#800), not just this host's own
    ``resolve_platform()`` — a single-platform ``type=docker`` export
    CLOBBERS the other architecture's layers under the shared ``:dev`` tag,
    so on a host running both architectures from one clone, each arch's
    refresh broke the other arch's ``--pull=never`` verify step (measured
    rc=125, "does not provide the specified platform").
    """
    # ponytail: a cold refresh now pulls BOTH architectures' layers
    # (~2x20GB) even for a single-arch user. Upgrade path if that cost
    # matters: intersect published_targets() with the platforms already
    # present under the local tag (`docker image ls --tree`) before
    # building this list.
    platforms = ",".join(target.platform for target in published_targets())
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
    """Pure decision matrix — see the module docstring table."""
    if force or status.stale:
        return "rebuild"
    if status.container_state != "running":
        return "up"
    if not status.container_current:
        return "rebuild"
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
        if status.stale and not refresh_local_tag(status.image_ref):
            return False, f"buildkit tag refresh failed for {status.image_ref}"
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
        sys.stdout.write(
            f"check: {'STALE — sync would rebuild' if status.stale else 'current'}\n"
        )
        return 1 if status.stale else 0

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
