# Copyright (c) 2026 Raymond Manaloto
"""Tests for typed gate execution and persisted results (#1111)."""

from __future__ import annotations

import itertools
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import msgspec
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import codec, gate_result, main
from dotfiles_setup.config import ContainerConfig, DotfilesConfig, MiseConfig

_STATUS_AXIS_VALUES: dict[str, tuple[object, ...]] = {
    "returncode": (0, 23),
    "known": (False, True),
    "tool_missing": (False, True),
    "timed_out": (False, True),
}

_STATUS_FOR = cast(
    "Callable[..., gate_result.GateStatus]", vars(gate_result)["_status_for"]
)

_STATUS_TABLE: list[tuple[int, bool, bool, bool, gate_result.GateStatus]] = [
    (0, False, False, False, gate_result.GateStatus.NOT_A_GATE),
    (0, False, False, True, gate_result.GateStatus.NOT_A_GATE),
    (0, False, True, False, gate_result.GateStatus.NOT_A_GATE),
    (0, False, True, True, gate_result.GateStatus.NOT_A_GATE),
    (0, True, False, False, gate_result.GateStatus.PASSED),
    (0, True, False, True, gate_result.GateStatus.TIMED_OUT),
    (0, True, True, False, gate_result.GateStatus.TOOL_MISSING),
    (0, True, True, True, gate_result.GateStatus.TOOL_MISSING),
    (23, False, False, False, gate_result.GateStatus.NOT_A_GATE),
    (23, False, False, True, gate_result.GateStatus.NOT_A_GATE),
    (23, False, True, False, gate_result.GateStatus.NOT_A_GATE),
    (23, False, True, True, gate_result.GateStatus.NOT_A_GATE),
    (23, True, False, False, gate_result.GateStatus.FAILED),
    (23, True, False, True, gate_result.GateStatus.TIMED_OUT),
    (23, True, True, False, gate_result.GateStatus.TOOL_MISSING),
    (23, True, True, True, gate_result.GateStatus.TOOL_MISSING),
]


def _fake_mise(tmp_path: Path, body: str) -> Path:
    """Install an isolated executable that stands in for the mise boundary."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    executable = bin_dir / "mise"
    executable.write_text(f"#!/bin/sh\n{body}\n")
    executable.chmod(0o755)
    return bin_dir


def _isolated_config(tmp_path: Path) -> DotfilesConfig:
    """Build CLI configuration without consulting user-owned directories."""
    return DotfilesConfig(
        mise=MiseConfig(install_path=tmp_path / "unused-mise"),
        container=ContainerConfig(host_state_dir=tmp_path / "host-state"),
    )


@pytest.mark.parametrize("row", _STATUS_TABLE)
def test_status_for_complete_truth_table(
    row: tuple[int, bool, bool, bool, gate_result.GateStatus],
) -> None:
    """Every return-code partition and flag combination has one status."""
    returncode, known, tool_missing, timed_out, expected = row
    assert (
        _STATUS_FOR(
            returncode,
            known=known,
            tool_missing=tool_missing,
            timed_out=timed_out,
        )
        is expected
    )


def test_status_for_truth_table_is_exhaustive() -> None:
    """The table crosses the full declared four-axis product."""
    expected_cells = set(itertools.product(*_STATUS_AXIS_VALUES.values()))
    covered = {row[: len(_STATUS_AXIS_VALUES)] for row in _STATUS_TABLE}
    assert covered == expected_cells
    assert len(_STATUS_TABLE) == len(expected_cells) == 16


@pytest.fixture(autouse=True)
def _deterministic_gate_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every exercised gate duration independent of the wall clock."""
    ticks = iter((40.0, 40.25))
    monkeypatch.setattr(gate_result.time, "perf_counter", lambda: next(ticks))


def test_failing_gate_preserves_the_true_child_rc_and_full_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deleting the declared lint wiring must turn this armed failure red."""
    bin_dir = _fake_mise(
        tmp_path,
        "printf '%s\\n' 'setup chatter' 'FAILED synthetic gate'\nexit 23",
    )
    monkeypatch.setenv("PATH", str(bin_dir))

    result = gate_result.run_gate(tmp_path, "lint")

    assert result.status is gate_result.GateStatus.FAILED
    assert result.returncode == 23
    assert result.duration_s == 0.25
    assert result.command == ("mise", "run", "lint")
    assert result.failures == ("FAILED synthetic gate",)
    assert Path(result.log_path or "").read_text() == (
        "setup chatter\nFAILED synthetic gate\n"
    )
    assert gate_result.read_result(tmp_path, "lint") == result


def test_unknown_gate_writes_not_a_gate_without_executing_anything(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deleting the unknown-name guard executes this hostile control arm."""
    marker = tmp_path / "arbitrary-command-ran"
    bin_dir = _fake_mise(
        tmp_path,
        f": > {shlex.quote(str(marker))}\nexit 99",
    )
    monkeypatch.setenv("PATH", str(bin_dir))

    result = gate_result.run_gate(tmp_path, "definitely-not-a-gate")

    assert result.status is gate_result.GateStatus.NOT_A_GATE
    assert result.returncode == 2
    assert result.command == ()
    assert result.log_path is None
    assert not marker.exists()
    assert gate_result.read_result(tmp_path, "definitely-not-a-gate") == result


def test_missing_executable_is_distinct_from_a_failing_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Removing the tool-missing arm collapses this result into FAILED."""
    empty_path = tmp_path / "empty-path"
    empty_path.mkdir()
    monkeypatch.setenv("PATH", str(empty_path))

    result = gate_result.run_gate(tmp_path, "lint")

    assert result.status is gate_result.GateStatus.TOOL_MISSING
    assert result.returncode == 127
    assert result.duration_s == 0.25
    assert result.command == ("mise", "run", "lint")
    assert result.log_path is not None
    assert Path(result.log_path).is_file()


def test_timeout_is_typed_without_waiting_on_wall_clock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An immediate fake timeout retains the killed child's real return code."""

    class TimedOutProcess:
        returncode: int | None = None
        killed = False

        def communicate(self, timeout: float | None = None) -> tuple[bytes, None]:
            if not self.killed:
                assert timeout is not None
                raise subprocess.TimeoutExpired(
                    ("mise", "run", "lint"), timeout, output=b"ERROR partial\n"
                )
            return b"ERROR partial\n", None

        def kill(self) -> None:
            self.killed = True
            self.returncode = -9

    process = TimedOutProcess()
    monkeypatch.setattr(
        gate_result.subprocess, "Popen", lambda *_args, **_kwargs: process
    )

    result = gate_result.run_gate(tmp_path, "lint", timeout_s=0.25)

    assert result.status is gate_result.GateStatus.TIMED_OUT
    assert result.returncode == -9
    assert result.duration_s == 0.25
    assert result.failures == ("ERROR partial",)
    assert Path(result.log_path or "").read_bytes() == b"ERROR partial\n"


def test_main_cli_run_and_read_emit_matching_json_and_exit_codes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Deleting either main.py parser or dispatch wiring breaks this public path."""
    bin_dir = _fake_mise(tmp_path, "printf '%s\\n' 'FAILED cli arm'\nexit 31")
    monkeypatch.setenv("PATH", str(bin_dir))
    args = main.setup_parser().parse_args(["gate", "run", "lint"])

    with pytest.raises(SystemExit) as run_exit:
        main.run_command(args, tmp_path, config=_isolated_config(tmp_path))
    run_output = capsys.readouterr().out

    read_rc = gate_result.gate_main(["--repo-root", str(tmp_path), "read", "lint"])
    read_output = capsys.readouterr().out

    assert run_exit.value.code == 1
    assert read_rc == 1
    assert json.loads(run_output) == json.loads(read_output)
    assert json.loads(read_output)["status"] == "failed"
    assert json.loads(read_output)["returncode"] == 31
    assert json.loads(read_output)["duration_s"] == 0.25


def test_cli_exit_mapping_covers_every_status() -> None:
    """Removing any enum arm leaves no agreed JSON-to-process-rc contract."""
    assert gate_result.STATUS_EXIT_CODES == {
        gate_result.GateStatus.PASSED: 0,
        gate_result.GateStatus.FAILED: 1,
        gate_result.GateStatus.TOOL_MISSING: 127,
        gate_result.GateStatus.TIMED_OUT: 124,
        gate_result.GateStatus.NOT_A_GATE: 2,
    }


def test_result_reader_rejects_a_payload_outside_the_typed_contract(
    tmp_path: Path,
) -> None:
    """Replacing typed decode with unvalidated json.loads makes this pass wrongly."""
    path = gate_result.result_path(tmp_path, "lint")
    path.parent.mkdir(parents=True)
    path.write_text(
        '{"gate":"lint","status":"invented","returncode":0,'
        '"duration_s":0.0,"command":[]}'
    )

    with pytest.raises(msgspec.ValidationError):
        gate_result.read_result(tmp_path, "lint")


def test_generated_schema_is_directly_bound_to_gate_result() -> None:
    """Deleting a model field or enum member changes this generated contract."""
    schema = gate_result.generate_schema()
    definitions = cast("dict[str, dict[str, Any]]", schema["$defs"])
    result_schema = definitions["GateResult"]
    status_schema = definitions["GateStatus"]

    assert schema["$ref"] == "#/$defs/GateResult"
    assert result_schema["required"] == [
        "gate",
        "status",
        "returncode",
        "duration_s",
        "command",
    ]
    assert set(result_schema["properties"]) == {
        "gate",
        "status",
        "returncode",
        "duration_s",
        "command",
        "failures",
        "log_path",
    }
    assert set(status_schema["enum"]) == {
        "passed",
        "failed",
        "tool_missing",
        "timed_out",
        "not_a_gate",
    }


def test_generate_schema_routes_through_the_shared_codec(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A direct msgspec call would bypass this single-owner fail arm."""
    sentinel: dict[str, object] = {"owner": "codec"}
    targets: list[object] = []

    def fake_schema(target: object) -> dict[str, object]:
        targets.append(target)
        return sentinel

    monkeypatch.setattr(codec, "schema", fake_schema)

    assert gate_result.generate_schema() is sentinel
    assert targets == [gate_result.GateResult]


def test_committed_schema_matches_the_generated_model() -> None:
    """Changing the model without regenerating the artifact must turn red."""
    repo_root = Path(__file__).parent.parent
    committed = json.loads((repo_root / "schemas" / "gate-result.json").read_text())
    generated = json.loads(json.dumps(gate_result.generate_schema()))

    assert committed == generated


def test_codec_round_trip_preserves_the_frozen_model(tmp_path: Path) -> None:
    """The typed write/read path must not degrade the enum to a plain string."""
    result = gate_result.GateResult(
        gate="lint",
        status=gate_result.GateStatus.PASSED,
        returncode=0,
        duration_s=0.5,
        command=("mise", "run", "lint"),
        log_path=str(tmp_path / "lint.log"),
    )

    decoded = codec.decode(codec.encode(result), gate_result.GateResult)

    assert decoded == result
    assert decoded.status is gate_result.GateStatus.PASSED
