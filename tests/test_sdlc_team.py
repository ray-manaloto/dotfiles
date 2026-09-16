# Copyright (c) 2026 Raymond Manaloto
"""Tests for the typed, detached Codex SDLC-team dispatcher."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, cast

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import codec, lane_result, main, sdlc_team
from dotfiles_setup.config import ContainerConfig, DotfilesConfig, MiseConfig

if TYPE_CHECKING:
    from collections.abc import Mapping


class _DetachedProcess:
    """Minimal process returned at the detached-supervisor boundary."""

    pid = 4242


class _CompletedChild:
    """Minimal successful Codex child for supervisor-boundary tests."""

    pid = 8181
    returncode: int | None = None

    def wait(self, timeout: float | None = None) -> int:
        assert timeout is None
        self.returncode = 0
        return 0


def _codex_banner(parent_thread_id: str) -> str:
    """Build the real delimited exec-banner shape captured in codex.log."""
    return (
        "OpenAI Codex v0.154.0\n"
        "--------\n"
        "workdir: /repo\n"
        f"session id: {parent_thread_id}\n"
        "--------\n"
    )


def _write_child_rollout(
    sessions_root: Path,
    filename: str,
    child: Mapping[str, object],
) -> Path:
    """Write the verified first-line Codex child metadata shape."""
    payload: dict[str, object] = {
        "id": child["id"],
        "session_id": child["parent_thread_id"],
        "parent_thread_id": child["parent_thread_id"],
        "originator": "codex_exec",
        "thread_source": "subagent",
        "cwd": "/repo",
    }
    if child.get("agent_role"):
        payload["agent_role"] = child["agent_role"]
    if child.get("agent_path"):
        payload["agent_path"] = child["agent_path"]
    if "source" in child:
        payload["source"] = child["source"]
    path = sessions_root / "2026" / "09" / "16" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": "2026-09-16T06:16:17.947Z",
        "ordinal": 0,
        "type": "session_meta",
        "payload": payload,
    }
    path.write_text(json.dumps(record) + "\n" + '{"type":"session_meta"}\n')
    return path


@dataclass(frozen=True)
class _SupervisorFixture:
    """All external evidence supplied to one isolated supervisor run."""

    report: str
    log_text: str
    children: tuple[Mapping[str, object], ...] = ()
    add_unreadable_rollout: bool = False
    unreadable_mtime: float = 0.0
    started_at: str = "2026-09-15T00:00:00+00:00"


def _run_supervisor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fixture: _SupervisorFixture,
) -> tuple[int, sdlc_team.SdlcTeamSettlement, lane_result.LaneResult]:
    """Run the real supervisor composition around an isolated fake Codex process."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    prompt = tmp_path / "prompt.md"
    output = tmp_path / "output.md"
    sessions_root = tmp_path / "codex-home" / "sessions"
    prompt.write_text("dispatch\n")
    output.write_text(fixture.report)
    sessions_root.mkdir(parents=True)
    for index, child in enumerate(fixture.children):
        _write_child_rollout(
            sessions_root,
            f"rollout-child-{index}.jsonl",
            child,
        )
    if fixture.add_unreadable_rollout:
        unreadable = sessions_root / "rollout-zero.jsonl"
        unreadable.write_text("")
        os.utime(unreadable, (fixture.unreadable_mtime, fixture.unreadable_mtime))

    child_process = _CompletedChild()

    def fake_popen(*_args: object, **kwargs: object) -> _CompletedChild:
        stdout = cast("BinaryIO", kwargs["stdout"])
        stdout.write(fixture.log_text.encode())
        stdout.flush()
        return child_process

    monkeypatch.setattr(sdlc_team.subprocess, "Popen", fake_popen)
    ticks = iter((10.0, 10.25))
    monkeypatch.setattr(sdlc_team.time, "monotonic", lambda: next(ticks))
    payload_type = vars(sdlc_team)["_SupervisorPayload"]
    supervise = vars(sdlc_team)["_supervise"]
    payload = payload_type(
        run_id="spawn-run",
        argv=("/bin/codex", "exec", "-"),
        prompt_file=str(prompt),
        output_file=str(output),
        log_file=str(tmp_path / "codex.log"),
        receipt_json=str(tmp_path / "receipt.json"),
        receipt_md=str(tmp_path / "receipt.md"),
        settlement_file=str(tmp_path / "settlement.json"),
        workdir=str(tmp_path),
        started_at=fixture.started_at,
        sessions_root=str(sessions_root),
    )

    returncode = supervise(payload)
    settlement = codec.decode(
        (tmp_path / "settlement.json").read_bytes(),
        sdlc_team.SdlcTeamSettlement,
    )
    receipt = codec.decode(
        (tmp_path / "receipt.json").read_bytes(), lane_result.LaneResult
    )
    return returncode, settlement, receipt


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
    assert (
        "If a specialist cannot be spawned, stop and report the spawn failure" in prompt
    )
    assert "do the work yourself" not in prompt
    assert "exactly one item per spawned specialist" in prompt
    assert "formatted as - `<agent_role>` — `<agent_path>`" in prompt
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


def test_dispatch_snapshots_codex_home_sessions_in_the_supervisor_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    codex_home = tmp_path / "isolated-codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    _result, calls = _capture_dispatch(tmp_path, monkeypatch, _request(tmp_path))
    supervisor_argv, _options = calls[0]
    decode_payload = vars(sdlc_team)["_decode_payload"]
    payload = decode_payload(supervisor_argv[-1])

    assert payload.sessions_root == str((codex_home / "sessions").resolve())


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


def test_old_seven_field_settlement_decodes_with_new_field_defaults() -> None:
    old_bytes = json.dumps(
        {
            "run_id": "old-run",
            "status": "completed",
            "codex_returncode": 0,
            "codex_pid": 42,
            "finished_at": "2026-09-15T00:00:00+00:00",
            "duration_s": 1.5,
            "errors": [],
        }
    ).encode()

    settlement = codec.decode(old_bytes, sdlc_team.SdlcTeamSettlement)

    assert settlement.parent_thread_id is None
    assert settlement.specialists_claimed == ()
    assert settlement.specialists_observed == ()
    with pytest.raises(ValueError, match="run_id"):
        codec.decode(b'{"status":"completed"}', sdlc_team.SdlcTeamSettlement)


def test_supervisor_fails_when_claimed_specialist_has_no_child_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    returncode, settlement, _receipt = _run_supervisor(
        tmp_path,
        monkeypatch,
        _SupervisorFixture(
            report="Specialists spawned:\n\n- `sdlc-python-specialist`\n",
            log_text=_codex_banner(parent_id),
        ),
    )

    assert returncode == 1
    assert settlement.status is sdlc_team.SdlcSettledStatus.FAILED
    assert settlement.codex_returncode == 0
    assert settlement.codex_pid == _CompletedChild.pid
    assert settlement.parent_thread_id == parent_id
    sessions_root = tmp_path / "codex-home" / "sessions"
    assert settlement.errors == (
        f"spawn reconciliation: zero specialists observed under {sessions_root}",
        (
            "spawn reconciliation: claimed item 'sdlc-python-specialist' matches no "
            "observed child"
        ),
    )
    assert settlement.specialists_claimed == ("sdlc-python-specialist",)
    assert settlement.specialists_observed == ()


def test_supervisor_completes_when_claim_and_child_role_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    returncode, settlement, _receipt = _run_supervisor(
        tmp_path,
        monkeypatch,
        _SupervisorFixture(
            report="Specialists spawned:\n\n- `sdlc-python-specialist`\n",
            log_text=_codex_banner(parent_id),
            children=(
                {
                    "id": "01a0a8db-de4d-7c93-a96f-8d001939aecd",
                    "parent_thread_id": parent_id,
                    "agent_role": "sdlc-python-specialist",
                },
            ),
        ),
    )

    assert returncode == 0
    assert settlement.status is sdlc_team.SdlcSettledStatus.COMPLETED
    assert settlement.parent_thread_id == parent_id
    assert settlement.specialists_claimed == ("sdlc-python-specialist",)
    assert settlement.specialists_observed == ("sdlc-python-specialist",)
    assert settlement.errors == ()


def test_supervisor_fails_with_one_error_per_claimed_and_observed_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    returncode, settlement, _receipt = _run_supervisor(
        tmp_path,
        monkeypatch,
        _SupervisorFixture(
            report="Specialists spawned:\n\n- `sdlc-python-specialist`\n",
            log_text=_codex_banner(parent_id),
            children=(
                {
                    "id": "01a0a8db-de4d-7c93-a96f-8d001939aecd",
                    "parent_thread_id": parent_id,
                    "agent_role": "sdlc-config-specialist",
                    "agent_path": "/root/config_review",
                },
            ),
        ),
    )

    assert returncode == 1
    assert settlement.status is sdlc_team.SdlcSettledStatus.FAILED
    assert settlement.errors == (
        (
            "spawn reconciliation: claimed item 'sdlc-python-specialist' matches no "
            "observed child"
        ),
        (
            "spawn reconciliation: observed child 'sdlc-config-specialist' "
            "(/root/config_review) was not claimed"
        ),
    )


def test_supervisor_fails_closed_when_codex_banner_has_no_parent_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    returncode, settlement, _receipt = _run_supervisor(
        tmp_path,
        monkeypatch,
        _SupervisorFixture(
            report="Specialists spawned:\n\n- `sdlc-python-specialist`\n",
            log_text="Codex output without an exec banner\n",
            children=(
                {
                    "id": "01a0a8db-de4d-7c93-a96f-8d001939aecd",
                    "parent_thread_id": parent_id,
                    "agent_role": "sdlc-python-specialist",
                },
            ),
        ),
    )

    assert returncode == 1
    assert settlement.status is sdlc_team.SdlcSettledStatus.FAILED
    assert settlement.parent_thread_id is None
    assert settlement.errors == (
        "spawn reconciliation: parent thread id not found in codex.log banner",
        (
            "spawn reconciliation: observed source unavailable: parent thread id was "
            "not provided"
        ),
    )
    assert settlement.specialists_claimed == ("sdlc-python-specialist",)
    assert settlement.specialists_observed == ()


def test_path_first_claim_is_canonicalized_once_in_the_lane_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    report = (
        "Specialists spawned:\n\n"
        "- `/root/config_pin_review` — `sdlc-config-specialist`; initial spawn "
        "failed with `no thread with id`, retry succeeded\n"
    )
    returncode, settlement, receipt = _run_supervisor(
        tmp_path,
        monkeypatch,
        _SupervisorFixture(
            report=report,
            log_text=_codex_banner(parent_id),
            children=(
                {
                    "id": "01a0a8db-de4d-7c93-a96f-8d001939aecd",
                    "parent_thread_id": parent_id,
                    "agent_role": "sdlc-config-specialist",
                    "agent_path": "/root/config_pin_review",
                },
            ),
        ),
    )

    assert returncode == 0
    assert settlement.status is sdlc_team.SdlcSettledStatus.COMPLETED
    assert settlement.specialists_claimed == ("sdlc-config-specialist",)
    assert settlement.specialists_observed == ("sdlc-config-specialist",)
    assert settlement.errors == ()
    assert [(agent.name, agent.role) for agent in receipt.agents] == [
        ("sdlc-config-specialist", "/root/config_pin_review")
    ]
    assert all(
        "no thread with id" not in identity
        for identity in (
            *settlement.specialists_claimed,
            *settlement.specialists_observed,
            *(agent.name for agent in receipt.agents),
        )
    )


def test_roleless_child_pairs_by_agent_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    returncode, settlement, _receipt = _run_supervisor(
        tmp_path,
        monkeypatch,
        _SupervisorFixture(
            report=(
                "Specialists spawned:\n\n"
                "- `/root/config_pin_review` — `sdlc-config-specialist`\n"
            ),
            log_text=_codex_banner(parent_id),
            children=(
                {
                    "id": "01a0a8db-de4d-7c93-a96f-8d001939aecd",
                    "parent_thread_id": parent_id,
                    "agent_path": "/root/config_pin_review",
                },
            ),
        ),
    )

    assert returncode == 0
    assert settlement.status is sdlc_team.SdlcSettledStatus.COMPLETED
    # [v7 F3] claimed is the ITEM's own roster identity, never the child's name:
    # here the observed node is named by its path, so the two tuples differ.
    assert settlement.specialists_claimed == ("sdlc-config-specialist",)
    assert settlement.specialists_observed == ("/root/config_pin_review",)
    assert settlement.errors == ()


@pytest.mark.parametrize("empty_item", ["None.", "none"])
def test_none_spawn_item_is_not_treated_as_a_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    empty_item: str,
) -> None:
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    returncode, settlement, _receipt = _run_supervisor(
        tmp_path,
        monkeypatch,
        _SupervisorFixture(
            report=f"Specialists spawned:\n\n- {empty_item}\n",
            log_text=_codex_banner(parent_id),
        ),
    )

    assert returncode == 1
    assert settlement.status is sdlc_team.SdlcSettledStatus.FAILED
    assert settlement.specialists_claimed == ()
    sessions_root = tmp_path / "codex-home" / "sessions"
    assert settlement.errors == (
        f"spawn reconciliation: zero specialists observed under {sessions_root}",
    )


def test_real_shape_uses_closing_spawn_list_and_three_matching_children(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    report = """A finding near the top quotes `Specialists spawned:` in prose.

- `P1` — not a specialist.

The actual closing report follows.

Specialists spawned:

- `sdlc-python-specialist` — `/root/python_review`
- `sdlc-config-specialist` — `/root/config_review`
- `sdlc-documentation-specialist` — `/root/docs_review`

No other specialists were spawned.
"""
    roles_and_paths = (
        ("sdlc-python-specialist", "/root/python_review"),
        ("sdlc-config-specialist", "/root/config_review"),
        ("sdlc-documentation-specialist", "/root/docs_review"),
    )
    children = tuple(
        {
            "id": f"01a0a8db-de4d-7c93-a96f-8d001939aec{index}",
            "parent_thread_id": parent_id,
            "agent_role": role,
            "agent_path": path,
        }
        for index, (role, path) in enumerate(roles_and_paths)
    )

    returncode, settlement, _receipt = _run_supervisor(
        tmp_path,
        monkeypatch,
        _SupervisorFixture(
            report=report,
            log_text=_codex_banner(parent_id),
            children=children,
        ),
    )

    assert returncode == 0
    assert settlement.status is sdlc_team.SdlcSettledStatus.COMPLETED
    assert settlement.specialists_claimed == tuple(
        role for role, _path in roles_and_paths
    )
    assert settlement.specialists_observed == tuple(
        sorted(role for role, _path in roles_and_paths)
    )
    assert settlement.errors == ()


def test_unreadable_rollout_note_stays_in_receipt_and_does_not_fail_settlement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    returncode, settlement, receipt = _run_supervisor(
        tmp_path,
        monkeypatch,
        _SupervisorFixture(
            report="Specialists spawned:\n\n- `sdlc-python-specialist`\n",
            log_text=_codex_banner(parent_id),
            children=(
                {
                    "id": "01a0a8db-de4d-7c93-a96f-8d001939aecd",
                    "parent_thread_id": parent_id,
                    "agent_role": "sdlc-python-specialist",
                },
            ),
            add_unreadable_rollout=True,
        ),
    )

    assert returncode == 0
    assert settlement.status is sdlc_team.SdlcSettledStatus.COMPLETED
    assert settlement.errors == ()
    assert any(
        disagreement == "source observed note: skipped 1 unreadable rollout file(s)"
        for disagreement in receipt.disagreements
    )


def test_identityless_child_fails_with_its_uuid_and_missing_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    child_id = "01a0a8db-de4d-7c93-a96f-8d001939aecd"
    returncode, settlement, _receipt = _run_supervisor(
        tmp_path,
        monkeypatch,
        _SupervisorFixture(
            report="Specialists spawned:\n\n- `sdlc-python-specialist`\n",
            log_text=_codex_banner(parent_id),
            children=({"id": child_id, "parent_thread_id": parent_id},),
        ),
    )

    assert returncode == 1
    assert settlement.status is sdlc_team.SdlcSettledStatus.FAILED
    assert settlement.errors == (
        (
            "spawn reconciliation: claimed item 'sdlc-python-specialist' matches no "
            "observed child"
        ),
        (
            f"spawn reconciliation: observed child {child_id!r} carries neither "
            "agent_role nor agent_path"
        ),
    )


def test_arm_16_real_mixed_list_keeps_json_probe_and_names_only_missing_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    report = """Specialists spawned:

- `sdlc-config-specialist`
- `sdlc-python-specialist`
- `sdlc-documentation-specialist`
- `json_probe` (`default`) — nested JSONL observability probe
- No other specialists or subagents were spawned.
"""
    roster = (
        ("sdlc-config-specialist", "/root/config_review"),
        ("sdlc-python-specialist", "/root/python_review"),
        ("sdlc-documentation-specialist", "/root/docs_review"),
    )
    roster_children = tuple(
        {
            "id": f"01a0a8db-de4d-7c93-a96f-8d001939ae{index:02d}",
            "parent_thread_id": parent_id,
            "agent_role": role,
            "agent_path": path,
        }
        for index, (role, path) in enumerate(roster)
    )
    json_child = {
        "id": "01a0a8dc-de4d-7c93-a96f-8d001939aecd",
        "parent_thread_id": parent_id,
        "agent_role": "default",
        "agent_path": "/root/json_probe",
    }

    positive_rc, positive, _receipt = _run_supervisor(
        tmp_path / "positive",
        monkeypatch,
        _SupervisorFixture(
            report=report,
            log_text=_codex_banner(parent_id),
            children=(*roster_children, json_child),
        ),
    )
    negative_rc, negative, _receipt = _run_supervisor(
        tmp_path / "negative",
        monkeypatch,
        _SupervisorFixture(
            report=report,
            log_text=_codex_banner(parent_id),
            children=roster_children,
        ),
    )

    assert positive_rc == 0
    assert positive.status is sdlc_team.SdlcSettledStatus.COMPLETED
    assert positive.specialists_claimed == (
        "sdlc-config-specialist",
        "sdlc-python-specialist",
        "sdlc-documentation-specialist",
        "json_probe",
    )
    assert positive.errors == ()
    assert negative_rc == 1
    assert negative.status is sdlc_team.SdlcSettledStatus.FAILED
    assert negative.errors == (
        "spawn reconciliation: claimed item 'json_probe' matches no observed child",
    )
    assert all("was not claimed" not in error for error in negative.errors)


def test_arm_17_trailing_backticked_prose_is_not_an_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    returncode, settlement, _receipt = _run_supervisor(
        tmp_path,
        monkeypatch,
        _SupervisorFixture(
            report=(
                "Specialists spawned:\n\n"
                "- `sdlc-python-specialist` — `/root/python_review`; "
                "spawned after `explorer` finished\n"
            ),
            log_text=_codex_banner(parent_id),
            children=(
                {
                    "id": "01a0a8db-de4d-7c93-a96f-8d001939aecd",
                    "parent_thread_id": parent_id,
                    "agent_role": "sdlc-python-specialist",
                    "agent_path": "/root/python_review",
                },
            ),
        ),
    )

    assert returncode == 0
    assert settlement.status is sdlc_team.SdlcSettledStatus.COMPLETED
    assert settlement.errors == ()


def test_arm_18_claimed_roster_comes_only_from_the_dispatcher_item() -> None:
    path_first = lane_result.collect_spawn_report(
        "Specialists spawned:\n\n- `/root/python_review` — `sdlc-python-specialist`\n"
    )
    path_only = lane_result.collect_spawn_report(
        "Specialists spawned:\n\n- `/root/python_review`\n"
    )
    python_child = lane_result.CollectorOutcome(
        source=lane_result.AgentSource.OBSERVED,
        agents=(
            lane_result.AgentNode(
                name="sdlc-python-specialist",
                role="/root/python_review",
                sources=(lane_result.AgentSource.OBSERVED,),
            ),
        ),
    )
    mutated_child = lane_result.CollectorOutcome(
        source=lane_result.AgentSource.OBSERVED,
        agents=(
            lane_result.AgentNode(
                name="sdlc-config-specialist",
                role="/root/python_review",
                sources=(lane_result.AgentSource.OBSERVED,),
            ),
        ),
    )

    path_first_result = sdlc_team.reconcile_spawns(
        "parent", "/sessions", path_first, python_child
    )
    path_only_result = sdlc_team.reconcile_spawns(
        "parent", "/sessions", path_only, mutated_child
    )

    assert path_first_result.consistent is True
    assert path_first_result.specialists_claimed == ("sdlc-python-specialist",)
    assert path_only_result.consistent is True
    assert path_only_result.specialists_claimed == ("/root/python_review",)


def test_arm_19_claimed_paths_must_exist_and_agree_with_roster_tokens() -> None:
    actual_child = lane_result.CollectorOutcome(
        source=lane_result.AgentSource.OBSERVED,
        agents=(
            lane_result.AgentNode(
                name="sdlc-python-specialist",
                role="/root/python_review",
                sources=(lane_result.AgentSource.OBSERVED,),
            ),
        ),
    )
    fabricated_path = lane_result.collect_spawn_report(
        "Specialists spawned:\n\n- `sdlc-python-specialist` — `/root/never_existed`\n"
    )
    fabricated_result = sdlc_team.reconcile_spawns(
        "parent", "/sessions", fabricated_path, actual_child
    )

    swapped_claims = lane_result.collect_spawn_report(
        "Specialists spawned:\n\n"
        "- `sdlc-python-specialist` — `/root/config_review`\n"
        "- `sdlc-config-specialist` — `/root/python_review`\n"
    )
    two_children = lane_result.CollectorOutcome(
        source=lane_result.AgentSource.OBSERVED,
        agents=(
            *actual_child.agents,
            lane_result.AgentNode(
                name="sdlc-config-specialist",
                role="/root/config_review",
                sources=(lane_result.AgentSource.OBSERVED,),
            ),
        ),
    )
    swapped_result = sdlc_team.reconcile_spawns(
        "parent", "/sessions", swapped_claims, two_children
    )
    fabricated_path_error = (
        "spawn reconciliation: claimed path '/root/never_existed' "
        "matches no observed child"
    )

    assert fabricated_result.consistent is False
    assert fabricated_result.errors == (
        fabricated_path_error,
        (
            "spawn reconciliation: observed child 'sdlc-python-specialist' "
            "(/root/python_review) was not claimed"
        ),
    )
    assert swapped_result.consistent is False
    assert swapped_result.errors == (
        (
            "spawn reconciliation: claimed 'sdlc-python-specialist' does not match "
            "child at /root/config_review (agent_role 'sdlc-config-specialist', "
            "name 'config_review')"
        ),
        (
            "spawn reconciliation: claimed 'sdlc-config-specialist' does not match "
            "child at /root/python_review (agent_role 'sdlc-python-specialist', "
            "name 'python_review')"
        ),
    )


def test_arm_20_review_thread_is_observed_but_not_a_roster_spawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    review_id = "01a0a8dc-de4d-7c93-a96f-8d001939aecd"
    roles = (
        "sdlc-config-specialist",
        "sdlc-python-specialist",
        "sdlc-documentation-specialist",
    )
    report = "Specialists spawned:\n\n" + "".join(f"- `{role}`\n" for role in roles)
    children: tuple[Mapping[str, object], ...] = (
        *(
            {
                "id": f"01a0a8db-de4d-7c93-a96f-8d001939ae{index:02d}",
                "parent_thread_id": parent_id,
                "agent_role": role,
                "agent_path": f"/root/review_{index}",
            }
            for index, role in enumerate(roles)
        ),
        {
            "id": review_id,
            "parent_thread_id": parent_id,
            "source": {"subagent": "review"},
        },
    )

    returncode, settlement, receipt = _run_supervisor(
        tmp_path,
        monkeypatch,
        _SupervisorFixture(
            report=report,
            log_text=_codex_banner(parent_id),
            children=children,
        ),
    )

    review_nodes = tuple(node for node in receipt.agents if node.name == review_id)
    assert returncode == 0
    assert settlement.status is sdlc_team.SdlcSettledStatus.COMPLETED
    assert settlement.specialists_observed == tuple(sorted((*roles, review_id)))
    assert review_nodes == (
        lane_result.AgentNode(
            name=review_id,
            sources=(lane_result.AgentSource.OBSERVED,),
            status="review-thread",
        ),
    )


def test_arm_21_removing_source_markers_turns_review_thread_into_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    review_id = "01a0a8dc-de4d-7c93-a96f-8d001939aecd"
    marked_children: tuple[Mapping[str, object], ...] = (
        {
            "id": "01a0a8db-de4d-7c93-a96f-8d001939aecd",
            "parent_thread_id": parent_id,
            "agent_role": "sdlc-python-specialist",
            "agent_path": "/root/python_review",
            "source": {"subagent": {"thread_spawn": {}}},
        },
        {
            "id": review_id,
            "parent_thread_id": parent_id,
            "source": {"subagent": "review"},
        },
    )
    stripped_children = tuple(
        {key: value for key, value in child.items() if key != "source"}
        for child in marked_children
    )
    report = "Specialists spawned:\n\n- `sdlc-python-specialist`\n"
    log_text = _codex_banner(parent_id)

    marked_rc, marked, _receipt = _run_supervisor(
        tmp_path / "marked",
        monkeypatch,
        _SupervisorFixture(
            report=report,
            log_text=log_text,
            children=marked_children,
        ),
    )
    stripped_rc, stripped, _receipt = _run_supervisor(
        tmp_path / "stripped",
        monkeypatch,
        _SupervisorFixture(
            report=report,
            log_text=log_text,
            children=stripped_children,
        ),
    )

    assert marked_rc == 0
    assert marked.status is sdlc_team.SdlcSettledStatus.COMPLETED
    assert stripped_rc == 1
    assert stripped.status is sdlc_team.SdlcSettledStatus.FAILED
    assert stripped.errors == (
        (
            f"spawn reconciliation: observed child {review_id!r} carries neither "
            "agent_role nor agent_path"
        ),
    )


def test_arm_22_pinned_claim_shape_has_no_receipt_role_conflict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    returncode, settlement, receipt = _run_supervisor(
        tmp_path,
        monkeypatch,
        _SupervisorFixture(
            report=(
                "Specialists spawned:\n\n"
                "- `sdlc-python-specialist` — `/root/python_review`\n"
            ),
            log_text=_codex_banner(parent_id),
            children=(
                {
                    "id": "01a0a8db-de4d-7c93-a96f-8d001939aecd",
                    "parent_thread_id": parent_id,
                    "agent_role": "sdlc-python-specialist",
                    "agent_path": "/root/python_review",
                },
            ),
        ),
    )

    hook_path = lane_result.hook_events_path(tmp_path, "spawn-run")
    assert returncode == 0
    assert settlement.status is sdlc_team.SdlcSettledStatus.COMPLETED
    assert receipt.disagreements == (
        f"source hook unavailable: hook log not found: {hook_path}",
    )


def test_arm_23_only_unreadable_rollouts_written_during_the_run_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    started_at = "2026-09-16T06:16:17+00:00"
    started_epoch = datetime.fromisoformat(started_at).timestamp()
    fixture = {
        "report": "Specialists spawned:\n\n- `sdlc-python-specialist`\n",
        "log_text": _codex_banner(parent_id),
        "children": (
            {
                "id": "01a0a8db-de4d-7c93-a96f-8d001939aecd",
                "parent_thread_id": parent_id,
                "agent_role": "sdlc-python-specialist",
            },
        ),
        "add_unreadable_rollout": True,
        "started_at": started_at,
    }

    old_rc, old_settlement, old_receipt = _run_supervisor(
        tmp_path / "old",
        monkeypatch,
        _SupervisorFixture(**fixture, unreadable_mtime=started_epoch - 1),
    )
    new_rc, new_settlement, new_receipt = _run_supervisor(
        tmp_path / "new",
        monkeypatch,
        _SupervisorFixture(**fixture, unreadable_mtime=started_epoch + 1),
    )

    assert old_rc == 0
    assert old_settlement.status is sdlc_team.SdlcSettledStatus.COMPLETED
    assert old_settlement.errors == ()
    assert "source observed note: skipped 1 unreadable rollout file(s)" in (
        old_receipt.disagreements
    )
    assert new_rc == 1
    assert new_settlement.status is sdlc_team.SdlcSettledStatus.FAILED
    assert new_settlement.errors == (
        (
            "spawn reconciliation: skipped 1 unreadable rollout file(s) written "
            "during this run"
        ),
    )
    new_note = (
        "source observed note: skipped 1 unreadable rollout file(s) written "
        "during this run"
    )
    assert new_note in new_receipt.disagreements


def test_arm_25_role_as_spawn_name_pairs_against_path_basename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    roles_and_names = (
        ("sdlc-documentation-specialist", "round3_docs"),
        ("sdlc-python-specialist", "round3_python"),
        ("sdlc-config-specialist", "round3_config"),
        ("sdlc-workflows-specialist", "round3_workflows"),
        ("sdlc-image-specialist", "round3_image"),
    )
    report = "Specialists spawned:\n\n" + "".join(
        f"- `{role}` as `{name}`\n" for role, name in roles_and_names
    )
    report += "- No other specialists were spawned.\n"
    children = tuple(
        {
            "id": f"01a0a8db-de4d-7c93-a96f-8d001939af{index:02d}",
            "parent_thread_id": parent_id,
            "agent_role": role,
            "agent_path": f"/root/{name}",
        }
        for index, (role, name) in enumerate(roles_and_names)
    )

    returncode, settlement, _receipt = _run_supervisor(
        tmp_path,
        monkeypatch,
        _SupervisorFixture(
            report=report,
            log_text=_codex_banner(parent_id),
            children=children,
        ),
    )

    assert returncode == 0
    assert settlement.status is sdlc_team.SdlcSettledStatus.COMPLETED
    assert settlement.specialists_claimed == tuple(
        role for role, _name in roles_and_names
    )
    assert settlement.errors == ()


def test_arm_26_same_line_terminator_stays_in_the_claim_role_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    report = (
        "Specialists spawned:\n\n"
        "- `sdlc-config-specialist` (`config_smoke_review`); "
        "no others were spawned.\n"
    )
    parsed = lane_result.collect_spawn_report(report)
    returncode, settlement, _receipt = _run_supervisor(
        tmp_path,
        monkeypatch,
        _SupervisorFixture(
            report=report,
            log_text=_codex_banner(parent_id),
            children=(
                {
                    "id": "01a0a8db-de4d-7c93-a96f-8d001939aecd",
                    "parent_thread_id": parent_id,
                    "agent_role": "sdlc-config-specialist",
                    "agent_path": "/root/config_smoke_review",
                },
            ),
        ),
    )

    assert parsed.agents == (
        lane_result.AgentNode(
            name="sdlc-config-specialist",
            role="(`config_smoke_review`); no others were spawned.",
            sources=(lane_result.AgentSource.SELF_REPORT,),
        ),
    )
    assert returncode == 0
    assert settlement.status is sdlc_team.SdlcSettledStatus.COMPLETED
    assert settlement.specialists_claimed == ("sdlc-config-specialist",)
    assert settlement.errors == ()


def test_arm_27_aware_start_time_and_unknown_start_fail_in_safe_directions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    utc_now = vars(sdlc_team)["_utc_now"]
    started_at = utc_now()
    started_epoch = datetime.fromisoformat(started_at).timestamp()
    fixture = {
        "report": "Specialists spawned:\n\n- `sdlc-python-specialist`\n",
        "log_text": _codex_banner(parent_id),
        "children": (
            {
                "id": "01a0a8db-de4d-7c93-a96f-8d001939aecd",
                "parent_thread_id": parent_id,
                "agent_role": "sdlc-python-specialist",
            },
        ),
        "add_unreadable_rollout": True,
    }

    after_rc, after, _receipt = _run_supervisor(
        tmp_path / "after",
        monkeypatch,
        _SupervisorFixture(
            **fixture,
            started_at=started_at,
            unreadable_mtime=started_epoch + 1,
        ),
    )
    before_rc, before, before_receipt = _run_supervisor(
        tmp_path / "before",
        monkeypatch,
        _SupervisorFixture(
            **fixture,
            started_at=started_at,
            unreadable_mtime=started_epoch - 1,
        ),
    )
    unknown_rc, unknown, _receipt = _run_supervisor(
        tmp_path / "unknown",
        monkeypatch,
        _SupervisorFixture(
            **fixture,
            started_at="",
            unreadable_mtime=started_epoch - 1,
        ),
    )

    assert after_rc == 1
    assert after.errors == (
        (
            "spawn reconciliation: skipped 1 unreadable rollout file(s) written "
            "during this run"
        ),
    )
    assert before_rc == 0
    assert before.status is sdlc_team.SdlcSettledStatus.COMPLETED
    assert "source observed note: skipped 1 unreadable rollout file(s)" in (
        before_receipt.disagreements
    )
    assert unknown_rc == 1
    assert unknown.errors == (
        (
            "spawn reconciliation: skipped 1 unreadable rollout file(s) written "
            "during this run (start time was unknown)"
        ),
    )


def test_reconciliation_rejects_ambiguous_claim_but_pairs_well_formed_sibling() -> None:
    self_report = lane_result.collect_spawn_report(
        "Specialists spawned:\n\n"
        "- `/root/p1` — `/root/p2`, also `sdlc-python-specialist`\n"
        "- `/root/p2` — `sdlc-python-specialist`\n"
    )
    observed = lane_result.CollectorOutcome(
        source=lane_result.AgentSource.OBSERVED,
        agents=(
            lane_result.AgentNode(
                name="sdlc-python-specialist",
                role="/root/p1",
                sources=(lane_result.AgentSource.OBSERVED,),
            ),
            lane_result.AgentNode(
                name="sdlc-python-specialist",
                role="/root/p2",
                sources=(lane_result.AgentSource.OBSERVED,),
            ),
        ),
    )

    result = sdlc_team.reconcile_spawns("parent", "/sessions", self_report, observed)

    assert result.consistent is False
    assert result.errors == (
        (
            "spawn reconciliation: claimed item '/root/p1' carries more than one path "
            "or role identity"
        ),
        (
            "spawn reconciliation: observed child 'sdlc-python-specialist' (/root/p1) "
            "was not claimed"
        ),
    )
    assert result.specialists_claimed == (
        "/root/p1",
        "sdlc-python-specialist",
    )
    assert result.specialists_observed == (
        "sdlc-python-specialist",
        "sdlc-python-specialist",
    )


def test_reconciliation_pairs_duplicate_roles_by_path_then_by_unmatched_role() -> None:
    observed = lane_result.CollectorOutcome(
        source=lane_result.AgentSource.OBSERVED,
        agents=tuple(
            lane_result.AgentNode(
                name="sdlc-python-specialist",
                role=path,
                sources=(lane_result.AgentSource.OBSERVED,),
            )
            for path in ("/root/python_a", "/root/python_b")
        ),
    )
    by_path = lane_result.collect_spawn_report(
        "Specialists spawned:\n\n"
        "- `sdlc-python-specialist` — `/root/python_a`\n"
        "- `sdlc-python-specialist` — `/root/python_b`\n"
    )
    one_claim = lane_result.collect_spawn_report(
        "Specialists spawned:\n\n- `sdlc-python-specialist` — `/root/python_a`\n"
    )
    by_role = lane_result.collect_spawn_report(
        "Specialists spawned:\n\n"
        "- `sdlc-python-specialist`\n"
        "- `sdlc-python-specialist`\n"
    )

    path_result = sdlc_team.reconcile_spawns("parent", "/sessions", by_path, observed)
    one_result = sdlc_team.reconcile_spawns("parent", "/sessions", one_claim, observed)
    role_result = sdlc_team.reconcile_spawns("parent", "/sessions", by_role, observed)

    assert path_result.consistent is True
    assert path_result.specialists_observed == (
        "sdlc-python-specialist",
        "sdlc-python-specialist",
    )
    assert path_result.errors == ()
    assert one_result.consistent is False
    assert one_result.errors == (
        (
            "spawn reconciliation: observed child 'sdlc-python-specialist' "
            "(/root/python_b) was not claimed"
        ),
    )
    assert role_result.consistent is True
    assert role_result.specialists_claimed == (
        "sdlc-python-specialist",
        "sdlc-python-specialist",
    )
    assert role_result.errors == ()


def test_supervisor_timeout_kills_the_codex_process_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bare-pid kill would leave Codex descendants alive after timeout."""
    prompt = tmp_path / "prompt.md"
    output = tmp_path / "output.md"
    sessions_root = tmp_path / "sessions"
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    prompt.write_text("dispatch\n")
    output.write_text("Specialists spawned:\n\n- `sdlc-python-specialist`\n")
    _write_child_rollout(
        sessions_root,
        "rollout-child.jsonl",
        {
            "id": "01a0a8db-de4d-7c93-a96f-8d001939aecd",
            "parent_thread_id": parent_id,
            "agent_role": "sdlc-python-specialist",
        },
    )

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

    def fake_popen(*_args: object, **kwargs: object) -> TimedOutChild:
        stdout = cast("BinaryIO", kwargs["stdout"])
        stdout.write(_codex_banner(parent_id).encode())
        stdout.flush()
        return child

    monkeypatch.setattr(sdlc_team.subprocess, "Popen", fake_popen)
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
        sessions_root=str(sessions_root),
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


def test_arm_29_prose_led_claim_cannot_pair_with_a_different_specialist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A claim whose name is prose carries no identity and fails closed.

    Before the anchor fix the prose was discarded and the item became the
    path-only claim `/root/python_review`, which paired with the config
    specialist that actually ran there and settled the run `completed`.
    """
    parent_id = "01a0a8da-6d39-74e3-a8fc-fe66f5505378"
    child = {
        "id": "01a0a8db-de4d-7c93-a96f-8d001939aecd",
        "parent_thread_id": parent_id,
        "agent_role": "sdlc-config-specialist",
        "agent_path": "/root/python_review",
    }
    returncode, settlement, _receipt = _run_supervisor(
        tmp_path,
        monkeypatch,
        _SupervisorFixture(
            report=(
                "Specialists spawned:\n\n- Python specialist — `/root/python_review`\n"
            ),
            log_text=_codex_banner(parent_id),
            children=(child,),
        ),
    )

    assert returncode == 1
    assert settlement.status is sdlc_team.SdlcSettledStatus.FAILED
    assert settlement.errors == (
        (
            "spawn reconciliation: claimed item "
            "'Python specialist — `/root/python_review`' names no roster specialist "
            "or agent path"
        ),
        (
            "spawn reconciliation: observed child 'sdlc-config-specialist' "
            "(/root/python_review) was not claimed"
        ),
    )

    control_code, control, _receipt = _run_supervisor(
        tmp_path / "control",
        monkeypatch,
        _SupervisorFixture(
            report=(
                "Specialists spawned:\n\n"
                "- `sdlc-config-specialist` — `/root/python_review`\n"
            ),
            log_text=_codex_banner(parent_id),
            children=(child,),
        ),
    )

    assert control_code == 0
    assert control.status is sdlc_team.SdlcSettledStatus.COMPLETED
    assert control.errors == ()
