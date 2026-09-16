# Copyright (c) 2026 Raymond Manaloto
"""Tests for the typed, detached Codex SDLC-team dispatcher."""

from __future__ import annotations

import json
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import codec, main, sdlc_team
from dotfiles_setup.config import ContainerConfig, DotfilesConfig, MiseConfig


class _DetachedProcess:
    """Minimal process returned at the detached-supervisor boundary."""

    pid = 4242


def _isolated_config(tmp_path: Path) -> DotfilesConfig:
    """Build CLI configuration without consulting user-owned directories."""
    return DotfilesConfig(
        mise=MiseConfig(install_path=tmp_path / "unused-mise"),
        container=ContainerConfig(host_state_dir=tmp_path / "host-state"),
    )


def _request(tmp_path: Path, **changes: object) -> sdlc_team.SdlcTeamRequest:
    """Create a request backed by an isolated real specification file."""
    spec_file = tmp_path / "spec.md"
    spec_file.write_text("# authoritative spec\n")
    values: dict[str, object] = {
        "spec_file": str(spec_file),
        "run_id": "run-42",
        "task": "Implement the typed dispatcher",
        "allowlist": ("python/src/dotfiles_setup/sdlc_team.py",),
    }
    values.update(changes)
    return sdlc_team.SdlcTeamRequest(**cast("dict[str, Any]", values))


def _capture_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    request: sdlc_team.SdlcTeamRequest,
) -> tuple[sdlc_team.SdlcTeamDispatch, list[tuple[tuple[str, ...], dict[str, object]]]]:
    """Substitute only the executable lookup and process-launch boundaries."""
    codex = tmp_path / "bin" / "codex"
    codex.parent.mkdir(exist_ok=True)
    codex.write_text("#!/bin/sh\nexit 0\n")
    codex.chmod(0o755)
    calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def fake_popen(command: tuple[str, ...], **kwargs: object) -> _DetachedProcess:
        calls.append((command, kwargs))
        return _DetachedProcess()

    monkeypatch.setattr(sdlc_team.shutil, "which", lambda _name: str(codex))
    monkeypatch.setattr(sdlc_team.subprocess, "Popen", fake_popen)
    return sdlc_team.dispatch(request, tmp_path), calls


def test_review_dispatch_is_detached_complete_and_has_no_false_settlement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Removing any dispatch contract arm makes this public result incomplete."""
    request = _request(tmp_path)

    result, calls = _capture_dispatch(tmp_path, monkeypatch, request)

    assert result.status is sdlc_team.SdlcStatus.DISPATCHED
    assert result.pid == _DetachedProcess.pid
    assert not hasattr(result, "codex_pid")
    assert result.argv[-1] == "-"
    assert "--ephemeral" not in result.argv, (
        "--ephemeral means 'Run without persisting session files to disk', and a "
        "spawned subagent IS a persisted thread — under it every spawn dies with "
        "`collab spawn failed: no thread with id`, so the team silently degrades "
        "to one generalist lane (#1142). Measured 2026-09-16 on one variable: 3 "
        "spawn failures and 0 session files with it; 0 failures and 2 files "
        'without, the child carrying "parent_thread_id". It also hides the run '
        "from agentsview, which reads those same files."
    )
    assert result.argv[result.argv.index("-s") + 1] == "read-only"
    assert result.argv[result.argv.index("-o") + 1] == result.output_file
    assert Path(result.argv[0]).is_absolute()
    assert all(
        Path(value).is_absolute()
        for value in (
            result.prompt_file,
            result.output_file,
            result.log_file,
            result.receipt_json,
            result.receipt_md,
            result.workdir,
        )
    )
    assert Path(result.prompt_file).read_text().find("SPEC FILE:") >= 0
    prompt = Path(result.prompt_file).read_text()
    assert "You are the SDLC dispatcher for" in prompt
    assert "STANDING CLAUSE — LICENSED DISSENT" in prompt
    assert "STANDING CLAUSE — TEST CRAFT" in prompt
    assert "COMMIT: caller" in prompt
    assert "retry once without conversation history" in prompt
    assert "Never pipe a command into head, tail, sed, awk" in prompt
    assert "Do not run repository gates" in prompt
    assert "Do not write a report file" in prompt
    assert request.allowlist[0] in prompt
    assert len(calls) == 1
    supervisor_argv, supervisor_options = calls[0]
    assert supervisor_argv[0] == sys.executable
    assert supervisor_options["start_new_session"] is True
    settlement = tmp_path / sdlc_team.SDLC_RUNS_DIR / request.run_id / "settlement.json"
    assert not settlement.exists()


@pytest.mark.parametrize(
    ("mode", "sandbox"),
    [
        (sdlc_team.SdlcMode.REVIEW, "read-only"),
        (sdlc_team.SdlcMode.IMPLEMENT, "workspace-write"),
    ],
)
def test_mode_selects_the_only_compatible_sandbox(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: sdlc_team.SdlcMode,
    sandbox: str,
) -> None:
    """Swapping either mapping turns its independent mode cell red."""
    result, _calls = _capture_dispatch(
        tmp_path, monkeypatch, _request(tmp_path, mode=mode)
    )

    assert result.argv[result.argv.index("-s") + 1] == sandbox


def test_explicit_artifact_locations_are_resolved_and_echoed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ignoring caller locations would silently send artifacts to defaults."""
    request = _request(
        tmp_path,
        prompt_file="artifacts/request-prompt.md",
        output_file="artifacts/final-output.md",
        log_file="artifacts/run.log",
        receipt_json="receipts/lane.json",
        receipt_md="receipts/lane.md",
    )

    result, _calls = _capture_dispatch(tmp_path, monkeypatch, request)

    assert result.prompt_file == str((tmp_path / request.prompt_file).resolve())
    assert result.output_file == str((tmp_path / request.output_file).resolve())
    assert result.log_file == str((tmp_path / request.log_file).resolve())
    assert result.receipt_json == str((tmp_path / request.receipt_json).resolve())
    assert result.receipt_md == str((tmp_path / request.receipt_md).resolve())
    assert Path(result.prompt_file).is_file()


def test_missing_spec_launches_no_process_and_returns_resolved_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deleting the pre-launch existence check executes this hostile arm."""
    request = sdlc_team.SdlcTeamRequest(
        spec_file=str(tmp_path / "missing-spec.md"), run_id="missing"
    )

    def forbidden_popen(*_args: object, **_kwargs: object) -> _DetachedProcess:
        raise AssertionError

    monkeypatch.setattr(sdlc_team.subprocess, "Popen", forbidden_popen)
    result = sdlc_team.dispatch(request, tmp_path)

    assert result.status is sdlc_team.SdlcStatus.SPEC_MISSING
    assert result.pid is None
    assert result.argv == ()
    assert Path(result.prompt_file).is_absolute()
    assert Path(result.receipt_json).is_absolute()


def test_missing_codex_launches_no_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Collapsing CLI_MISSING into a launch error loses this diagnostic arm."""
    request = _request(tmp_path)
    monkeypatch.setattr(sdlc_team.shutil, "which", lambda _name: None)

    def forbidden_popen(*_args: object, **_kwargs: object) -> _DetachedProcess:
        raise AssertionError

    monkeypatch.setattr(sdlc_team.subprocess, "Popen", forbidden_popen)
    result = sdlc_team.dispatch(request, tmp_path)

    assert result.status is sdlc_team.SdlcStatus.CLI_MISSING
    assert result.pid is None
    assert result.argv == ()


def test_reused_run_id_removes_stale_settlement_before_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Restoring a prewritten ABANDONED record makes this live run lie."""
    request = _request(tmp_path, run_id="reused")
    settlement = tmp_path / sdlc_team.SDLC_RUNS_DIR / "reused" / "settlement.json"
    settlement.parent.mkdir(parents=True)
    settlement.write_bytes(
        codec.encode(
            sdlc_team.SdlcTeamSettlement(
                run_id="reused",
                status=sdlc_team.SdlcSettledStatus.COMPLETED,
                codex_returncode=0,
                codex_pid=99,
            )
        )
    )

    result, calls = _capture_dispatch(tmp_path, monkeypatch, request)

    assert result.status is sdlc_team.SdlcStatus.DISPATCHED
    assert len(calls) == 1
    assert not settlement.exists()


def test_read_status_distinguishes_live_abandoned_and_settled_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each settlement-presence and pid-liveness cell has a distinct result."""
    run_id = "status-run"
    settlement_path = tmp_path / sdlc_team.SDLC_RUNS_DIR / run_id / "settlement.json"
    settlement_path.parent.mkdir(parents=True)
    settlement_path.write_bytes(
        codec.encode(
            sdlc_team.SdlcTeamSettlement(
                run_id=run_id,
                status=sdlc_team.SdlcSettledStatus.FAILED,
                codex_returncode=7,
                codex_pid=8080,
            )
        )
    )
    monkeypatch.setattr(
        sdlc_team.os,
        "kill",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("a settlement must win over pid probing")
        ),
    )
    assert (
        sdlc_team.read_status(tmp_path, run_id, pid=4242)
        is sdlc_team.SdlcSettledStatus.FAILED
    )

    settlement_path.unlink()
    probed: list[tuple[int, int]] = []
    monkeypatch.setattr(
        sdlc_team.os, "kill", lambda pid, sig: probed.append((pid, sig))
    )
    assert sdlc_team.read_status(tmp_path, run_id, pid=4242) is None
    assert probed == [(4242, 0)]

    def missing_process(_pid: int, _signal: int) -> None:
        raise ProcessLookupError

    monkeypatch.setattr(sdlc_team.os, "kill", missing_process)
    assert (
        sdlc_team.read_status(tmp_path, run_id, pid=4242)
        is sdlc_team.SdlcSettledStatus.ABANDONED
    )
    assert (
        sdlc_team.read_status(tmp_path, run_id, pid=None)
        is sdlc_team.SdlcSettledStatus.ABANDONED
    )


def test_read_status_rejects_an_on_disk_abandoned_settlement(tmp_path: Path) -> None:
    """Allowing ABANDONED on disk recreates the false-live-settlement defect."""
    path = tmp_path / sdlc_team.SDLC_RUNS_DIR / "bad" / "settlement.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(
        codec.encode(
            sdlc_team.SdlcTeamSettlement(
                run_id="bad", status=sdlc_team.SdlcSettledStatus.ABANDONED
            )
        )
    )

    with pytest.raises(ValueError, match="cannot have status ABANDONED"):
        sdlc_team.read_status(tmp_path, "bad", pid=1)


def test_supervisor_records_child_pid_and_completed_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dropping settlement ownership of codex_pid loses the launched child identity."""
    prompt = tmp_path / "prompt.md"
    output = tmp_path / "output.md"
    prompt.write_text("dispatch\n")
    output.write_text("Specialists spawned:\n\n- `sdlc-python-specialist`\n")

    class CompletedChild:
        pid = 8181
        returncode: int | None = None

        def wait(self, timeout: float | None = None) -> int:
            assert timeout is None
            self.returncode = 0
            return 0

    child = CompletedChild()
    monkeypatch.setattr(sdlc_team.subprocess, "Popen", lambda *_a, **_kw: child)
    ticks = iter((10.0, 10.25))
    monkeypatch.setattr(sdlc_team.time, "monotonic", lambda: next(ticks))
    payload_type = vars(sdlc_team)["_SupervisorPayload"]
    supervise = vars(sdlc_team)["_supervise"]
    payload = payload_type(
        run_id="complete",
        argv=("/bin/codex", "exec", "-"),
        prompt_file=str(prompt),
        output_file=str(output),
        log_file=str(tmp_path / "codex.log"),
        receipt_json=str(tmp_path / "receipt.json"),
        receipt_md=str(tmp_path / "receipt.md"),
        settlement_file=str(tmp_path / "settlement.json"),
        workdir=str(tmp_path),
        started_at="2026-09-15T00:00:00+00:00",
    )

    assert supervise(payload) == 0
    settlement = codec.decode(
        (tmp_path / "settlement.json").read_bytes(),
        sdlc_team.SdlcTeamSettlement,
    )
    assert settlement.status is sdlc_team.SdlcSettledStatus.COMPLETED
    assert settlement.codex_returncode == 0
    assert settlement.codex_pid == child.pid
    assert settlement.duration_s == 0.25
    assert (tmp_path / "receipt.json").is_file()
    assert (tmp_path / "receipt.md").is_file()


def test_supervisor_timeout_kills_the_codex_process_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bare-pid kill would leave Codex descendants alive after timeout."""
    prompt = tmp_path / "prompt.md"
    output = tmp_path / "output.md"
    prompt.write_text("dispatch\n")
    output.write_text("Specialists spawned:\n\n- `sdlc-python-specialist`\n")

    class TimedOutChild:
        pid = 9191
        returncode: int | None = None

        def wait(self, timeout: float | None = None) -> int:
            if timeout == 7.0:
                assert timeout is not None
                raise subprocess.TimeoutExpired(("codex", "exec"), timeout)
            assert timeout == 5.0
            self.returncode = -signal.SIGTERM
            return self.returncode

    child = TimedOutChild()
    monkeypatch.setattr(sdlc_team.subprocess, "Popen", lambda *_a, **_kw: child)
    signals: list[tuple[int, signal.Signals]] = []
    monkeypatch.setattr(
        sdlc_team.os, "killpg", lambda pid, sig: signals.append((pid, sig))
    )
    ticks = iter((20.0, 20.5))
    monkeypatch.setattr(sdlc_team.time, "monotonic", lambda: next(ticks))
    payload_type = vars(sdlc_team)["_SupervisorPayload"]
    supervise = vars(sdlc_team)["_supervise"]
    payload = payload_type(
        run_id="timeout",
        argv=("/bin/codex", "exec", "-"),
        prompt_file=str(prompt),
        output_file=str(output),
        log_file=str(tmp_path / "codex.log"),
        receipt_json=str(tmp_path / "receipt.json"),
        receipt_md=str(tmp_path / "receipt.md"),
        settlement_file=str(tmp_path / "settlement.json"),
        workdir=str(tmp_path),
        started_at="2026-09-15T00:00:00+00:00",
        timeout_s=7.0,
    )

    assert supervise(payload) == 1
    assert signals == [(child.pid, signal.SIGTERM)]
    settlement = codec.decode(
        (tmp_path / "settlement.json").read_bytes(),
        sdlc_team.SdlcTeamSettlement,
    )
    assert settlement.status is sdlc_team.SdlcSettledStatus.TIMED_OUT
    assert settlement.codex_returncode == -signal.SIGTERM
    assert settlement.codex_pid == child.pid
    assert settlement.duration_s == 0.5
    assert settlement.errors == ("codex exceeded timeout of 7s",)


def test_main_cli_registration_emits_typed_missing_spec_result(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Removing parser or handler wiring breaks this public main.py route."""
    request_file = tmp_path / "request.json"
    request_file.write_bytes(
        codec.encode(
            sdlc_team.SdlcTeamRequest(
                spec_file=str(tmp_path / "absent.md"), run_id="cli-run"
            )
        )
    )
    args = main.setup_parser().parse_args(["sdlc-team", str(request_file)])

    with pytest.raises(SystemExit) as cli_exit:
        main.run_command(args, tmp_path, config=_isolated_config(tmp_path))

    result = codec.decode(capsys.readouterr().out.encode(), sdlc_team.SdlcTeamDispatch)
    assert cli_exit.value.code == 1
    assert result.status is sdlc_team.SdlcStatus.SPEC_MISSING
    assert result.pid is None
    assert result.argv == ()


def test_all_generated_schemas_route_through_the_shared_codec(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A direct model-library call bypasses this three-model owner check."""
    targets: list[object] = []

    def fake_schema(target: object) -> dict[str, object]:
        targets.append(target)
        return {"owner": "codec"}

    monkeypatch.setattr(codec, "schema", fake_schema)

    assert sdlc_team.generate_request_schema() == {"owner": "codec"}
    assert sdlc_team.generate_dispatch_schema() == {"owner": "codec"}
    assert sdlc_team.generate_settlement_schema() == {"owner": "codec"}
    assert targets == [
        sdlc_team.SdlcTeamRequest,
        sdlc_team.SdlcTeamDispatch,
        sdlc_team.SdlcTeamSettlement,
    ]


@pytest.mark.parametrize(
    ("filename", "generated"),
    [
        ("sdlc-team-request.json", sdlc_team.generate_request_schema),
        ("sdlc-team-dispatch.json", sdlc_team.generate_dispatch_schema),
        ("sdlc-team-settlement.json", sdlc_team.generate_settlement_schema),
    ],
)
def test_committed_schema_matches_its_canonical_model(
    filename: str, generated: object
) -> None:
    """Changing any model without regenerating its artifact turns red."""
    repo_root = Path(__file__).parent.parent
    committed = json.loads((repo_root / "schemas" / filename).read_text())
    expected = json.loads(json.dumps(cast("Any", generated)()))

    assert committed == expected
