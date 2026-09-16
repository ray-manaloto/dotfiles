# Copyright (c) 2026 Raymond Manaloto
"""Typed, detached dispatch for the repository's Codex SDLC team."""

from __future__ import annotations

import argparse
import base64
import contextlib
import enum
import math
import os
import re
import shutil
import signal
import string
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final
from urllib.parse import quote

from dotfiles_setup import codec, lane_result

__all__ = [
    "SDLC_RUNS_DIR",
    "SdlcMode",
    "SdlcSettledStatus",
    "SdlcStatus",
    "SdlcTeamDispatch",
    "SdlcTeamRequest",
    "SdlcTeamSettlement",
    "SpawnReconciliation",
    "build_prompt",
    "dispatch",
    "generate_dispatch_schema",
    "generate_request_schema",
    "generate_settlement_schema",
    "read_status",
    "reconcile_spawns",
    "sdlc_team_main",
]


class SdlcMode(enum.StrEnum):
    """Whether the team reviews the tree or may implement in it."""

    REVIEW = "review"
    IMPLEMENT = "implement"


class SdlcStatus(enum.StrEnum):
    """Immediate dispatch status."""

    DISPATCHED = "dispatched"
    SPEC_MISSING = "spec_missing"
    CLI_MISSING = "cli_missing"
    INVALID_REQUEST = "invalid_request"


class SdlcTeamRequest(codec.Struct, frozen=True):
    """Every caller-controlled input needed to dispatch one SDLC lane."""

    spec_file: str
    mode: SdlcMode = SdlcMode.REVIEW
    effort: str = "xhigh"
    timeout_s: float | None = None
    allowlist: tuple[str, ...] = ()
    run_id: str = ""
    task: str = ""
    prompt_file: str = ""
    output_file: str = ""
    log_file: str = ""
    receipt_json: str = ""
    receipt_md: str = ""


class SdlcTeamDispatch(codec.Struct, frozen=True):
    """Immediate, fully resolved description of a dispatched lane."""

    run_id: str
    status: SdlcStatus
    pid: int | None = None
    argv: tuple[str, ...] = ()
    prompt_file: str = ""
    output_file: str = ""
    log_file: str = ""
    receipt_json: str = ""
    receipt_md: str = ""
    workdir: str = ""
    mode: SdlcMode = SdlcMode.REVIEW
    started_at: str = ""
    errors: tuple[str, ...] = ()


class SdlcSettledStatus(enum.StrEnum):
    """Terminal supervisor status."""

    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    ABANDONED = "abandoned"


class SdlcTeamSettlement(codec.Struct, frozen=True):
    """Terminal outcome atomically written by the detached supervisor."""

    run_id: str
    status: SdlcSettledStatus
    codex_returncode: int | None = None
    codex_pid: int | None = None
    finished_at: str = ""
    duration_s: float = 0.0
    errors: tuple[str, ...] = ()
    parent_thread_id: str | None = None
    specialists_claimed: tuple[str, ...] = ()
    specialists_observed: tuple[str, ...] = ()


class SpawnReconciliation(codec.Struct, frozen=True):
    """Pure claimed-versus-observed spawn reconciliation result."""

    consistent: bool
    parent_thread_id: str | None
    specialists_claimed: tuple[str, ...]
    specialists_observed: tuple[str, ...]
    errors: tuple[str, ...]
    self_report: lane_result.CollectorOutcome


class _SupervisorPayload(codec.Struct, frozen=True):
    """Typed private handoff from the dispatcher to its supervisor."""

    run_id: str
    argv: tuple[str, ...]
    prompt_file: str
    output_file: str
    log_file: str
    receipt_json: str
    receipt_md: str
    settlement_file: str
    workdir: str
    started_at: str
    timeout_s: float | None = None
    sessions_root: str = ""


@dataclass(frozen=True)
class _ClaimedIdentity:
    """One parsed claim and its grammar-bounded identities."""

    node: lane_result.AgentNode
    identities: tuple[str, ...]
    paths: tuple[str, ...]
    roles: tuple[str, ...]


@dataclass(frozen=True)
class _ObservedIdentity:
    """One observed child and its independently recorded identities."""

    node: lane_result.AgentNode
    agent_role: str
    agent_path: str


class _DispatchState(codec.Struct, frozen=True):
    """Non-path fields used while resolving an immediate dispatch result."""

    run_id: str
    status: SdlcStatus
    started_at: str
    errors: tuple[str, ...] = ()
    pid: int | None = None
    argv: tuple[str, ...] = ()


SDLC_RUNS_DIR: Final = ".agent/sdlc-runs"
_SUPERVISE_ACTION: Final = "_supervise"
_SUPERVISE_ARG_COUNT: Final = 2
_TIMEOUT_GRACE_S: Final = 5.0
_ROSTER_IDENTITY = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_PATH_IDENTITY = re.compile(r"^/[A-Za-z0-9_./-]{1,200}$")
_CHILD_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_BACKTICK_TOKEN = re.compile(r"`([^`]+)`")


def _utc_now() -> str:
    """Return an unambiguous UTC timestamp."""
    return datetime.now(UTC).isoformat()


def _safe_run_id(run_id: str) -> str:
    """Encode a caller-visible run id into one non-traversing path component."""
    return quote(run_id, safe="-_.")


def _resolve_path(value: str, default: Path, repo_root: Path) -> Path:
    """Resolve an optional caller path relative to the repository root."""
    candidate = Path(value).expanduser() if value else default
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate.resolve()


def _resolved_dispatch(
    request: SdlcTeamRequest,
    repo_root: Path,
    state: _DispatchState,
) -> tuple[SdlcTeamDispatch, Path]:
    """Resolve every public path even for a pre-launch failure."""
    workdir = repo_root.resolve()
    safe_id = _safe_run_id(state.run_id)
    run_dir = workdir / SDLC_RUNS_DIR / safe_id
    prompt_file = _resolve_path(request.prompt_file, run_dir / "prompt.md", workdir)
    output_file = _resolve_path(request.output_file, run_dir / "output.md", workdir)
    log_file = _resolve_path(request.log_file, run_dir / "codex.log", workdir)
    receipt_json = _resolve_path(
        request.receipt_json,
        workdir / lane_result.LANE_RESULTS_DIR / f"{safe_id}.json",
        workdir,
    )
    receipt_md = _resolve_path(
        request.receipt_md,
        workdir / lane_result.LANE_RESULTS_DIR / f"{safe_id}.md",
        workdir,
    )
    return (
        SdlcTeamDispatch(
            run_id=state.run_id,
            status=state.status,
            pid=state.pid,
            argv=state.argv,
            prompt_file=str(prompt_file),
            output_file=str(output_file),
            log_file=str(log_file),
            receipt_json=str(receipt_json),
            receipt_md=str(receipt_md),
            workdir=str(workdir),
            mode=request.mode,
            started_at=state.started_at,
            errors=state.errors,
        ),
        run_dir / "settlement.json",
    )


def build_prompt(request: SdlcTeamRequest, repo_root: Path) -> str:
    """Build the complete dispatcher brief; callers supply no boilerplate."""
    allowlist = "\n".join(f"- {path}" for path in request.allowlist)
    if not allowlist:
        allowlist = "- (none)"
    review_clauses = ""
    if request.mode is SdlcMode.REVIEW:
        review_clauses = (
            "\nREVIEW MODE: Do not run repository gates. Do not write a report file or "
            "modify the checkout; return the complete report in your final response, "
            "which the supervisor captures via -o.\n"
        )
    task = request.task.strip() or "Execute the authoritative specification."
    return (
        f"You are the SDLC dispatcher for `{repo_root.resolve()}`. Route this to your "
        "specialists per your roster, spawn them in parallel, wait for all, and "
        "synthesize their results.\n\n"
        f"TASK: {task}\n"
        f"SPEC FILE: {Path(request.spec_file).resolve()}\n"
        f"MODE: {request.mode.value}\n"
        f"{review_clauses}\n"
        "STANDING CLAUSE — LICENSED DISSENT: If the specification contradicts "
        "repository rules, observed reality, or itself, stop that work and report the "
        "contradiction with evidence; do not guess.\n\n"
        "STANDING CLAUSE — TEST CRAFT: Use isolated state, test through public "
        "interfaces, and give every assertion a realistic fail arm that fails when "
        "the requested behavior is reverted.\n\n"
        "FILE ALLOWLIST:\n"
        f"{allowlist}\n\n"
        "COMMIT: caller\n\n"
        "If a specialist cannot be spawned, stop and report the spawn failure with "
        "its error text; do not do that specialist's work yourself.\n\n"
        "Never pipe a command into head, tail, sed, awk, or another pager to read its "
        "result; capture and report the command's real exit code.\n\n"
        "End with a Markdown list under `Specialists spawned:` with exactly one item "
        "per spawned specialist, each item formatted as - `<agent_role>` — "
        "`<agent_path>`, and state that no others were spawned.\n"
    )


def _is_none_claim(name: str) -> bool:
    """Return whether a parsed list item is the model's empty-list sentinel."""
    return name.strip().rstrip(string.punctuation).lower() == "none"


def _claimed_identity(node: lane_result.AgentNode) -> _ClaimedIdentity:
    """Extract ordered, grammar-bounded identities from one claimed item."""
    identities: list[str] = []
    role_token = _BACKTICK_TOKEN.search(node.role)
    candidates = (node.name,) + (
        (role_token.group(1),) if role_token is not None else ()
    )
    for candidate in candidates:
        identity = candidate.strip()
        if not (
            _ROSTER_IDENTITY.fullmatch(identity) or _PATH_IDENTITY.fullmatch(identity)
        ):
            continue
        if identity not in identities:
            identities.append(identity)
    return _ClaimedIdentity(
        node=node,
        identities=tuple(identities),
        paths=tuple(
            identity for identity in identities if _PATH_IDENTITY.fullmatch(identity)
        ),
        roles=tuple(
            identity for identity in identities if _ROSTER_IDENTITY.fullmatch(identity)
        ),
    )


def _observed_identity(node: lane_result.AgentNode) -> _ObservedIdentity:
    """Recover the role/path presence encoded by ``collect_session_files``."""
    agent_path = node.role
    agent_role = ""
    if node.name != agent_path and not _CHILD_UUID.fullmatch(node.name):
        agent_role = node.name
    return _ObservedIdentity(
        node=node,
        agent_role=agent_role,
        agent_path=agent_path,
    )


def _reconciliation_error(detail: str) -> str:
    """Prefix one settlement-causal spawn reconciliation error."""
    return f"spawn reconciliation: {detail}"


def _during_run_skip_note(error: str) -> str:
    """Extract the settlement-causal unreadable-rollout note, if present."""
    return next(
        (
            note
            for note in error.split("; ")
            if "unreadable rollout file(s) written during this run" in note
        ),
        "",
    )


def _claim_problem(claim: _ClaimedIdentity) -> str:
    """Return the fail-closed validation error for one claim, if any."""
    if not claim.identities:
        return (
            f"claimed item {claim.node.name!r} names no roster specialist or agent path"
        )
    if len(claim.paths) > 1:
        return (
            f"claimed item {claim.node.name!r} carries more than one path "
            "or role identity"
        )
    return ""


def _path_basename(agent_path: str) -> str:
    """Return the Codex spawn name encoded by an agent path."""
    return agent_path.rsplit("/", maxsplit=1)[-1]


def _candidate_satisfied(
    candidate: str,
    child: _ObservedIdentity,
    *,
    path_anchored: bool,
) -> bool:
    """Return whether one claim constraint agrees with one observed child.

    A roster token is satisfied by the child's recorded ``agent_role``, by the
    spawn name its ``agent_path`` encodes, or — when the child records NO role
    at all and a path candidate of the same claim already anchors this child —
    vacuously: a missing field cannot contradict a claim the path pins down.
    """
    if _PATH_IDENTITY.fullmatch(candidate):
        return candidate == child.agent_path
    if candidate in {child.agent_role, _path_basename(child.agent_path)}:
        return True
    return path_anchored and not child.agent_role


def _claim_anchors_child(
    claim: _ClaimedIdentity,
    child: _ObservedIdentity,
) -> bool:
    """Return whether the claim's own path candidates pin down this child."""
    return bool(claim.paths) and all(path == child.agent_path for path in claim.paths)


def _consistent_child(
    claim: _ClaimedIdentity,
    child: _ObservedIdentity,
) -> bool:
    """Require every grammar-bounded candidate to describe the same child."""
    path_anchored = _claim_anchors_child(claim, child)
    return all(
        _candidate_satisfied(candidate, child, path_anchored=path_anchored)
        for candidate in claim.identities
    )


def _matching_child(
    claim: _ClaimedIdentity,
    children: tuple[_ObservedIdentity, ...],
    unmatched: set[int],
) -> int | None:
    """Choose the first unmatched non-review child consistent with the claim."""
    for child_index in sorted(unmatched):
        if _consistent_child(claim, children[child_index]):
            return child_index
    return None


def _claim_name(claim: _ClaimedIdentity) -> str:
    """Keep the dispatcher's own preferred identity for settlement evidence."""
    if claim.roles:
        return claim.roles[0]
    if claim.paths:
        return claim.paths[0]
    return claim.node.name


def _unmatched_claim_error(
    claim: _ClaimedIdentity,
    children: tuple[_ObservedIdentity, ...],
) -> tuple[str, int | None]:
    """Describe why a well-formed claim matched no observed child."""
    if not claim.paths:
        return f"claimed item {claim.node.name!r} matches no observed child", None

    claimed_path = claim.paths[0]
    path_match = next(
        (
            (child_index, child)
            for child_index, child in enumerate(children)
            if child.node.status != "review-thread" and child.agent_path == claimed_path
        ),
        None,
    )
    if path_match is None:
        return f"claimed path {claimed_path!r} matches no observed child", None

    child_index, child = path_match
    roster_token = next(
        (
            candidate
            for candidate in claim.roles
            if not _candidate_satisfied(candidate, child, path_anchored=True)
        ),
        None,
    )
    if roster_token is None:
        return f"claimed item {claim.node.name!r} matches no observed child", None
    detail = (
        f"claimed {roster_token!r} does not match child at {claimed_path} "
        f"(agent_role {child.agent_role!r}, name {_path_basename(claimed_path)!r})"
    )
    return detail, child_index


def _pair_claims(
    claims: tuple[_ClaimedIdentity, ...],
    children: tuple[_ObservedIdentity, ...],
    *,
    can_pair: bool,
) -> tuple[dict[int, int], set[int], tuple[str, ...]]:
    """Pair report-ordered claims to first consistent unmatched children."""
    matches: dict[int, int] = {}
    unmatched = {
        index
        for index, child in enumerate(children)
        if child.node.status != "review-thread"
    }
    diagnosed_children: set[int] = set()
    errors: list[str] = []
    for claim_index, claim in enumerate(claims):
        problem = _claim_problem(claim)
        if problem:
            errors.append(_reconciliation_error(problem))
            continue
        child_index = _matching_child(claim, children, unmatched) if can_pair else None
        if child_index is None:
            if can_pair:
                detail, diagnosed_child = _unmatched_claim_error(claim, children)
                errors.append(_reconciliation_error(detail))
                if diagnosed_child is not None:
                    diagnosed_children.add(diagnosed_child)
            continue
        matches[claim_index] = child_index
        unmatched.remove(child_index)
    return matches, unmatched - diagnosed_children, tuple(errors)


def _unmatched_child_errors(
    children: tuple[_ObservedIdentity, ...], unmatched: set[int]
) -> tuple[str, ...]:
    """Describe every observed child left after one-to-one pairing."""
    errors: list[str] = []
    for child_index in sorted(unmatched):
        child = children[child_index]
        if not child.agent_role and not child.agent_path:
            detail = (
                f"observed child {child.node.name!r} carries neither "
                "agent_role nor agent_path"
            )
        else:
            path_detail = f" ({child.agent_path})" if child.agent_path else ""
            detail = f"observed child {child.node.name!r}{path_detail} was not claimed"
        errors.append(_reconciliation_error(detail))
    return tuple(errors)


def _canonical_self_report(
    self_report: lane_result.CollectorOutcome,
    claims: tuple[_ClaimedIdentity, ...],
    children: tuple[_ObservedIdentity, ...],
    matches: dict[int, int],
) -> lane_result.CollectorOutcome:
    """Rename matched claims to observed receipt identities."""
    canonical_agents: list[lane_result.AgentNode] = []
    for claim_index, claim in enumerate(claims):
        child_index = matches.get(claim_index)
        if child_index is None:
            canonical_agents.append(claim.node)
            continue
        child = children[child_index]
        canonical_agents.append(
            lane_result.AgentNode(
                name=child.node.name,
                role=child.agent_path,
                parent=claim.node.parent,
                sources=claim.node.sources,
                status=claim.node.status,
            )
        )
    return lane_result.CollectorOutcome(
        source=self_report.source,
        agents=tuple(canonical_agents),
        available=self_report.available,
        error=self_report.error,
    )


def reconcile_spawns(
    parent_thread_id: str | None,
    sessions_root: str,
    self_report: lane_result.CollectorOutcome,
    observed: lane_result.CollectorOutcome,
) -> SpawnReconciliation:
    """Pair claimed items to observed children and fail every unknown or mismatch."""
    errors: list[str] = []
    parent_known = bool(parent_thread_id)
    if not parent_known:
        errors.append(
            _reconciliation_error("parent thread id not found in codex.log banner")
        )
    if not self_report.available:
        detail = self_report.error or "collector supplied no error"
        errors.append(_reconciliation_error(f"self-report unavailable: {detail}"))
    if not observed.available:
        detail = observed.error or "collector supplied no error"
        errors.append(_reconciliation_error(f"observed source unavailable: {detail}"))
    else:
        during_run_skip = _during_run_skip_note(observed.error)
        if during_run_skip:
            errors.append(_reconciliation_error(during_run_skip))

    claims = (
        tuple(
            _claimed_identity(node)
            for node in self_report.agents
            if not _is_none_claim(node.name)
        )
        if self_report.available
        else ()
    )
    children = (
        tuple(_observed_identity(node) for node in observed.agents)
        if parent_known and observed.available
        else ()
    )
    if parent_known and observed.available and not children:
        errors.append(
            _reconciliation_error(
                f"zero specialists observed under {sessions_root or '<unknown>'}"
            )
        )
    can_pair = parent_known and observed.available
    matches, unmatched, pairing_errors = _pair_claims(
        claims, children, can_pair=can_pair
    )
    errors.extend(pairing_errors)
    if can_pair:
        errors.extend(_unmatched_child_errors(children, unmatched))
    canonical_self_report = _canonical_self_report(
        self_report, claims, children, matches
    )
    return SpawnReconciliation(
        consistent=not errors,
        parent_thread_id=parent_thread_id,
        specialists_claimed=tuple(_claim_name(claim) for claim in claims),
        specialists_observed=tuple(sorted(node.name for node in observed.agents)),
        errors=tuple(errors),
        self_report=canonical_self_report,
    )


def _request_error(request: SdlcTeamRequest, repo_root: Path) -> str | None:
    """Validate request invariants that the model type alone cannot express."""
    if not repo_root.resolve().is_dir():
        return f"repository root is not a directory: {repo_root.resolve()}"
    spec_file = Path(request.spec_file).expanduser()
    if not spec_file.is_absolute():
        return "spec_file must be an absolute path"
    if not request.effort or not all(
        character.isalnum() or character in "-_" for character in request.effort
    ):
        return "effort must be a non-empty identifier"
    if request.timeout_s is not None and (
        not math.isfinite(request.timeout_s) or request.timeout_s <= 0
    ):
        return "timeout_s must be a finite positive number or null"
    if any(not path.strip() for path in request.allowlist):
        return "allowlist entries must not be empty"
    return None


def _atomic_write(path: Path, content: bytes) -> None:
    """Publish bytes without exposing a partial JSON or Markdown artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def _write_settlement(path: Path, settlement: SdlcTeamSettlement) -> None:
    """Atomically publish one terminal settlement."""
    if settlement.status is SdlcSettledStatus.ABANDONED:
        msg = "ABANDONED is derived by read_status and cannot be written"
        raise ValueError(msg)
    _atomic_write(path, codec.encode(settlement) + b"\n")


def _payload_argument(payload: _SupervisorPayload) -> str:
    """Encode the private supervisor handoff without another mutable artifact."""
    return base64.urlsafe_b64encode(codec.encode(payload)).decode()


def _decode_payload(value: str) -> _SupervisorPayload:
    """Decode and validate the private supervisor handoff."""
    return codec.decode(base64.urlsafe_b64decode(value.encode()), _SupervisorPayload)


def dispatch(request: SdlcTeamRequest, repo_root: Path) -> SdlcTeamDispatch:
    """Start a detached timeout-owning supervisor and return immediately."""
    run_id = request.run_id or uuid.uuid4().hex
    started_at = _utc_now()
    error = _request_error(request, repo_root)
    if error is not None:
        result, _ = _resolved_dispatch(
            request,
            repo_root,
            _DispatchState(
                run_id=run_id,
                status=SdlcStatus.INVALID_REQUEST,
                started_at=started_at,
                errors=(error,),
            ),
        )
        return result

    spec_file = Path(request.spec_file).expanduser()
    if not spec_file.is_file():
        result, _ = _resolved_dispatch(
            request,
            repo_root,
            _DispatchState(
                run_id=run_id,
                status=SdlcStatus.SPEC_MISSING,
                started_at=started_at,
                errors=(f"specification file does not exist: {spec_file}",),
            ),
        )
        return result

    codex = shutil.which("codex")
    if codex is None:
        result, _ = _resolved_dispatch(
            request,
            repo_root,
            _DispatchState(
                run_id=run_id,
                status=SdlcStatus.CLI_MISSING,
                started_at=started_at,
                errors=("codex executable was not found on PATH",),
            ),
        )
        return result

    paths, settlement_file = _resolved_dispatch(
        request,
        repo_root,
        _DispatchState(
            run_id=run_id,
            status=SdlcStatus.DISPATCHED,
            started_at=started_at,
        ),
    )
    sandbox = "read-only" if request.mode is SdlcMode.REVIEW else "workspace-write"
    # `--ephemeral` is deliberately ABSENT, and re-adding it breaks the team.
    #
    # It means "Run without persisting session files to disk" (`codex exec
    # --help`). A spawned subagent IS a persisted thread — `app-server.md:291`
    # archives "spawned descendant thread logs" and `:747` calls a thread log
    # a JSONL file on disk — so with nothing persisted the router has no thread
    # to attach a descendant to and every spawn dies:
    #
    #     ERROR codex_core::tools::router: error=collab spawn failed:
    #       no thread with id: 01a0a848-…
    #
    # Measured 2026-09-16, same prompt, one variable, evidence on disk rather
    # than from the model's own report:
    #
    #     with    --ephemeral : 3 spawn failures, 0 session files written
    #     without --ephemeral : 0 spawn failures, 2 session files — and the
    #                           child carries "parent_thread_id":"<parent>"
    #                           plus the payload the subagent was asked for
    #
    # Dropping it also makes a lane visible to agentsview, which reads exactly
    # these session files; under `--ephemeral` no lane could ever be audited.
    argv = (
        str(Path(codex).resolve()),
        "exec",
        "-s",
        sandbox,
        "-c",
        f'model_reasoning_effort="{request.effort}"',
        "-C",
        paths.workdir,
        "-o",
        paths.output_file,
        "-",
    )

    try:
        prompt_file = Path(paths.prompt_file)
        prompt_file.parent.mkdir(parents=True, exist_ok=True)
        prompt_file.write_text(build_prompt(request, repo_root))
        settlement_file.unlink(missing_ok=True)
        sessions_root = (
            Path(os.environ.get("CODEX_HOME") or "~/.codex").expanduser() / "sessions"
        ).resolve()
        payload = _SupervisorPayload(
            run_id=run_id,
            argv=argv,
            prompt_file=paths.prompt_file,
            output_file=paths.output_file,
            log_file=paths.log_file,
            receipt_json=paths.receipt_json,
            receipt_md=paths.receipt_md,
            settlement_file=str(settlement_file),
            workdir=paths.workdir,
            started_at=started_at,
            timeout_s=request.timeout_s,
            sessions_root=str(sessions_root),
        )
        supervisor = subprocess.Popen(
            (
                sys.executable,
                "-m",
                "dotfiles_setup.sdlc_team",
                _SUPERVISE_ACTION,
                _payload_argument(payload),
            ),
            cwd=paths.workdir,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as launch_error:
        failed, _ = _resolved_dispatch(
            request,
            repo_root,
            _DispatchState(
                run_id=run_id,
                status=SdlcStatus.INVALID_REQUEST,
                started_at=started_at,
                errors=(f"could not launch supervisor: {launch_error}",),
                argv=argv,
            ),
        )
        return failed

    dispatched, _ = _resolved_dispatch(
        request,
        repo_root,
        _DispatchState(
            run_id=run_id,
            status=SdlcStatus.DISPATCHED,
            started_at=started_at,
            pid=supervisor.pid,
            argv=argv,
        ),
    )
    return dispatched


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    """Terminate, then forcibly kill, the entire Codex process group."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=_TIMEOUT_GRACE_S)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def read_status(
    repo_root: Path, run_id: str, *, pid: int | None
) -> SdlcSettledStatus | None:
    """Derive current status without writing a false in-progress settlement."""
    settlement_file = (
        repo_root.resolve() / SDLC_RUNS_DIR / _safe_run_id(run_id) / "settlement.json"
    )
    if settlement_file.is_file():
        settlement = codec.decode(settlement_file.read_bytes(), SdlcTeamSettlement)
        if settlement.status is SdlcSettledStatus.ABANDONED:
            msg = "on-disk settlements cannot have status ABANDONED"
            raise ValueError(msg)
        return settlement.status
    if pid is None:
        return SdlcSettledStatus.ABANDONED
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return SdlcSettledStatus.ABANDONED
    except PermissionError:
        pass
    return None


def _write_lane_receipts(
    payload: _SupervisorPayload, duration_s: float
) -> tuple[tuple[str, ...], SpawnReconciliation]:
    """Compose truthful lane_result receipts from sources available to this request."""
    errors: list[str] = []
    try:
        report_text = Path(payload.output_file).read_text()
        self_report = lane_result.collect_spawn_report(report_text)
    except (OSError, UnicodeError) as error:
        self_report = lane_result.CollectorOutcome(
            source=lane_result.AgentSource.SELF_REPORT,
            available=False,
            error=f"dispatcher output could not be read: {error}",
        )
    try:
        log_text = Path(payload.log_file).read_text()
    except OSError, UnicodeError:
        parent_thread_id = None
    else:
        parent_thread_id = lane_result.parse_parent_thread_id(log_text)
    if payload.sessions_root:
        observed = lane_result.collect_session_files(
            parent_thread_id or "",
            Path(payload.sessions_root),
            started_at=payload.started_at,
        )
    else:
        observed = lane_result.CollectorOutcome(
            source=lane_result.AgentSource.OBSERVED,
            available=False,
            error="sessions root was not provided",
        )
    reconciliation = reconcile_spawns(
        parent_thread_id,
        payload.sessions_root,
        self_report,
        observed,
    )
    hook = lane_result.collect_hook_events(Path(payload.workdir), payload.run_id)
    agents, disagreements = lane_result.merge_sources(
        reconciliation.self_report, observed, hook
    )
    result = lane_result.LaneResult(
        run_id=payload.run_id,
        lane="codex-sdlc-dispatcher",
        agents=agents,
        disagreements=disagreements,
        started_at=payload.started_at,
        duration_s=duration_s,
    )
    for path, content, label in (
        (Path(payload.receipt_json), codec.encode(result) + b"\n", "JSON"),
        (
            Path(payload.receipt_md),
            lane_result.render_receipt(result).encode(),
            "Markdown",
        ),
    ):
        try:
            _atomic_write(path, content)
        except OSError as error:
            errors.append(f"could not write lane receipt {label}: {error}")
    return tuple(errors), reconciliation


def _supervise(payload: _SupervisorPayload) -> int:
    """Own the Codex child, process-group timeout, receipts, and settlement."""
    started = time.monotonic()
    status = SdlcSettledStatus.FAILED
    returncode: int | None = None
    codex_pid: int | None = None
    errors: list[str] = []
    try:
        log_file = Path(payload.log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with Path(payload.prompt_file).open("rb") as prompt, log_file.open("wb") as log:
            process = subprocess.Popen(
                payload.argv,
                cwd=payload.workdir,
                stdin=prompt,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            codex_pid = process.pid
            try:
                returncode = process.wait(timeout=payload.timeout_s)
                status = (
                    SdlcSettledStatus.COMPLETED
                    if returncode == 0
                    else SdlcSettledStatus.FAILED
                )
            except subprocess.TimeoutExpired:
                _terminate_process_group(process)
                returncode = process.returncode
                status = SdlcSettledStatus.TIMED_OUT
                errors.append(f"codex exceeded timeout of {payload.timeout_s:g}s")
    except OSError as error:
        errors.append(f"could not run codex: {error}")

    duration_s = time.monotonic() - started
    receipt_errors, reconciliation = _write_lane_receipts(payload, duration_s)
    errors.extend(reconciliation.errors)
    errors.extend(receipt_errors)
    if status is SdlcSettledStatus.COMPLETED and not reconciliation.consistent:
        status = SdlcSettledStatus.FAILED
    settlement = SdlcTeamSettlement(
        run_id=payload.run_id,
        status=status,
        codex_returncode=returncode,
        codex_pid=codex_pid,
        finished_at=_utc_now(),
        duration_s=duration_s,
        errors=tuple(errors),
        parent_thread_id=reconciliation.parent_thread_id,
        specialists_claimed=reconciliation.specialists_claimed,
        specialists_observed=reconciliation.specialists_observed,
    )
    try:
        _write_settlement(Path(payload.settlement_file), settlement)
    except OSError as error:
        try:
            with Path(payload.log_file).open("a") as log:
                log.write(f"\nsettlement write failed: {error}\n")
        except OSError:
            pass
        return 1
    return 0 if status is SdlcSettledStatus.COMPLETED else 1


def generate_request_schema() -> dict[str, object]:
    """Generate JSON Schema from the canonical request model."""
    return codec.schema(SdlcTeamRequest)


def generate_dispatch_schema() -> dict[str, object]:
    """Generate JSON Schema from the canonical dispatch model."""
    return codec.schema(SdlcTeamDispatch)


def generate_settlement_schema() -> dict[str, object]:
    """Generate JSON Schema from the canonical settlement model."""
    return codec.schema(SdlcTeamSettlement)


def _invalid_cli_dispatch(repo_root: Path, error: str) -> SdlcTeamDispatch:
    """Build a typed failure when no valid request model could be decoded."""
    request = SdlcTeamRequest(spec_file=str((repo_root / "invalid-request").resolve()))
    result, _ = _resolved_dispatch(
        request,
        repo_root,
        _DispatchState(
            run_id=uuid.uuid4().hex,
            status=SdlcStatus.INVALID_REQUEST,
            started_at=_utc_now(),
            errors=(error,),
        ),
    )
    return result


def sdlc_team_main(argv: list[str] | None = None) -> int:
    """Decode one typed request and emit one typed immediate dispatch result."""
    parser = argparse.ArgumentParser(prog="dotfiles-setup sdlc-team")
    parser.add_argument("request", nargs="?", default="-")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()
    try:
        if args.request == "-":
            request_bytes = sys.stdin.buffer.read()
        else:
            request_bytes = Path(args.request).read_bytes()
        request = codec.decode(request_bytes, SdlcTeamRequest)
        result = dispatch(request, repo_root)
    except (OSError, ValueError, TypeError) as error:
        result = _invalid_cli_dispatch(repo_root, f"invalid request JSON: {error}")
    sys.stdout.write(codec.encode(result).decode() + "\n")
    return 0 if result.status is SdlcStatus.DISPATCHED else 1


def _module_main(argv: list[str] | None = None) -> int:
    """Route the private supervisor action or the public request CLI."""
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) == _SUPERVISE_ARG_COUNT and arguments[0] == _SUPERVISE_ACTION:
        try:
            payload = _decode_payload(arguments[1])
        except (ValueError, TypeError) as error:
            sys.stderr.write(f"invalid supervisor payload: {error}\n")
            return 2
        return _supervise(payload)
    return sdlc_team_main(arguments)


if __name__ == "__main__":
    raise SystemExit(_module_main())
