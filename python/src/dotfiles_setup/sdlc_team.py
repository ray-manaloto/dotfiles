# Copyright (c) 2026 Raymond Manaloto
"""Typed, detached dispatch for the repository's Codex SDLC team."""

from __future__ import annotations

import argparse
import base64
import contextlib
import enum
import math
import os
import shutil
import signal
import subprocess
import sys
import time
import uuid
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
    "build_prompt",
    "dispatch",
    "generate_dispatch_schema",
    "generate_request_schema",
    "generate_settlement_schema",
    "read_status",
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
        "If a specialist spawn fails with `no thread with id` before the agent exists, "
        "retry once without conversation history. If spawning still fails, do the "
        "work yourself and report every spawn failure.\n\n"
        "Never pipe a command into head, tail, sed, awk, or another pager to read its "
        "result; capture and report the command's real exit code.\n\n"
        "End with a Markdown list under `Specialists spawned:` naming every specialist "
        "actually spawned, and confirm that no others were spawned.\n"
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
) -> tuple[str, ...]:
    """Compose truthful lane_result receipts from sources available to this request."""
    errors: list[str] = []
    try:
        report_text = Path(payload.output_file).read_text()
        self_report = lane_result.collect_self_report(report_text)
    except OSError as error:
        self_report = lane_result.CollectorOutcome(
            source=lane_result.AgentSource.SELF_REPORT,
            available=False,
            error=f"dispatcher output could not be read: {error}",
        )
    observed = lane_result.CollectorOutcome(
        source=lane_result.AgentSource.OBSERVED,
        available=False,
        error="parent session id is not carried by SdlcTeamRequest",
    )
    hook = lane_result.collect_hook_events(Path(payload.workdir), payload.run_id)
    agents, disagreements = lane_result.merge_sources(self_report, observed, hook)
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
    return tuple(errors)


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
    errors.extend(_write_lane_receipts(payload, duration_s))
    settlement = SdlcTeamSettlement(
        run_id=payload.run_id,
        status=status,
        codex_returncode=returncode,
        codex_pid=codex_pid,
        finished_at=_utc_now(),
        duration_s=duration_s,
        errors=tuple(errors),
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
