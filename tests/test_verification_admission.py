# Copyright (c) 2026 Raymond Manaloto
"""Saved verifier admission through the public file and execution boundaries."""

from __future__ import annotations

import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import verification_admission

if TYPE_CHECKING:
    from collections.abc import Callable


def communicate_after_output_is_available(
    operation: Callable[[], tuple[bytes, bytes]],
) -> tuple[bytes, bytes]:
    """Bound fixture readiness to 30 short reads before injecting a failure."""
    for _ in range(30):
        try:
            return operation()
        except subprocess.TimeoutExpired as error:
            if error.output:
                raise
    pytest.fail("fixture child did not publish output within the bounded reads")


def test_malformed_verifier_refused_without_start_or_import(tmp_path: Path) -> None:
    """Compiler-only refusal does not execute a product import or consume START."""
    (tmp_path / "product.py").write_text("raise RuntimeError('product imported')\n")
    verifier = tmp_path / "verify.py"
    verifier.write_text("import product\nif True print('broken')\n")
    attempt = tmp_path / "attempt"

    with pytest.raises(verification_admission.AdmissionError, match="compile"):
        verification_admission.start(verifier, helpers=(), attempt_dir=attempt)

    assert not attempt.exists()


def test_admitted_file_and_helper_execute_with_actual_exit(tmp_path: Path) -> None:
    """A saved positive control runs at its original location and keeps its rc."""
    helper = tmp_path / "helper.py"
    helper.write_text("VALUE = 'saved helper'\n")
    verifier = tmp_path / "verify.py"
    verifier.write_text(
        "import helper, sys\n"
        "print(__file__)\nprint(helper.VALUE)\n"
        "print('actual stderr', file=sys.stderr)\nsys.exit(7)\n"
    )
    record = verification_admission.start(
        verifier, helpers=[helper], attempt_dir=tmp_path / "attempt"
    )
    result = verification_admission.execute(record)
    assert result.returncode == 7
    assert result.stdout == f"{verifier}\nsaved helper\n".encode()
    assert result.stderr == b"actual stderr\n"
    evidence = json.loads((record.parent / "execution.json").read_bytes())
    assert evidence["returncode"] == 7
    assert evidence["command"][-1] == str(verifier)


@pytest.mark.parametrize("target", ["verifier", "helper"])
@pytest.mark.parametrize("mutation", ["changed", "missing", "symlink"])
def test_changed_or_missing_bound_code_refused(
    tmp_path: Path, target: str, mutation: str
) -> None:
    """Both bound file roles reject loss/substitution before any execution."""
    verifier = tmp_path / "verify.py"
    verifier.write_text("raise RuntimeError('must not execute')\n")
    helper = tmp_path / "helper.py"
    helper.write_text("VALUE = 1\n")
    record = verification_admission.start(
        verifier, helpers=[helper], attempt_dir=tmp_path / "attempt"
    )
    original = record.read_bytes()
    selected = verifier if target == "verifier" else helper
    if mutation == "changed":
        selected.write_text("raise RuntimeError('substitution')\n")
    else:
        selected.unlink()
        if mutation == "symlink":
            replacement = tmp_path / "replacement.py"
            replacement.write_text("raise RuntimeError('substitution')\n")
            selected.symlink_to(replacement)

    with pytest.raises(verification_admission.AdmissionError):
        verification_admission.execute(record)

    assert record.read_bytes() == original
    assert not (record.parent / "execution.json").exists()


@pytest.mark.parametrize("source", ["return\n", "import product\n", "# coding: bad\n"])
def test_preflight_uses_compiler_without_imports(tmp_path: Path, source: str) -> None:
    """Valid imports are inert; semantic compiler errors still fail preflight."""
    verifier = tmp_path / "verify.py"
    verifier.write_text(source)
    if source == "import product\n":
        binding = verification_admission.preflight(verifier)
        assert binding["helpers"] == []
    else:
        with pytest.raises(verification_admission.AdmissionError, match="compile"):
            verification_admission.preflight(verifier)


@pytest.mark.parametrize("selector", ["-", "-c", "print('inline')", "<<PY\npass\nPY"])
def test_cli_refuses_non_saved_verifiers(tmp_path: Path, selector: str) -> None:
    """Inline, stdin and heredoc text cannot consume a saved-verifier START."""
    command = [
        sys.executable,
        str(Path(__file__).parents[1] / "scripts" / "proof-verification-admission.py"),
        "start",
        f"--verifier={selector}",
        "--attempt-dir",
        str(tmp_path / "attempt"),
    ]
    result = subprocess.run(command, input=b"pass\n", capture_output=True, check=False)
    assert result.returncode == 2
    assert b"saved" in result.stderr
    assert not (tmp_path / "attempt").exists()


def test_start_cannot_overwrite_or_repeat_a_sealed_execution(tmp_path: Path) -> None:
    """Retry requires a fresh attempt; retained START and output stay literal."""
    verifier = tmp_path / "verify.py"
    verifier.write_text("print('sealed output')\n")
    attempt = tmp_path / "attempt"
    record = verification_admission.start(verifier, attempt_dir=attempt)
    verification_admission.execute(record)
    original = (attempt / "execution.json").read_bytes()
    with pytest.raises(verification_admission.AdmissionError, match="used"):
        verification_admission.execute(record)
    with pytest.raises(FileExistsError):
        verification_admission.start(verifier, attempt_dir=attempt)
    assert (attempt / "execution.json").read_bytes() == original


def test_timeout_retains_literal_child_exit_and_partial_output(tmp_path: Path) -> None:
    """Bounded execution retains partial evidence and the child's signal exit."""
    verifier = tmp_path / "verify.py"
    verifier.write_text("import time\nprint('started', flush=True)\ntime.sleep(10)\n")
    record = verification_admission.start(verifier, attempt_dir=tmp_path / "attempt")
    result = verification_admission.execute(record, timeout_s=0.3)
    evidence = json.loads((record.parent / "execution.json").read_bytes())
    assert result.returncode < 0
    assert evidence["returncode"] == result.returncode
    assert evidence["timed_out"] is True
    assert result.stdout == b"started\n"


@pytest.mark.parametrize("exitcode", [0, 7])
def test_public_cli_positive_saved_file_preserves_exit(
    tmp_path: Path, exitcode: int
) -> None:
    """The public entrypoint admits and executes real saved bytes with actual rc."""
    verifier = tmp_path / "verify.py"
    verifier.write_text(f"print('cli output')\nraise SystemExit({exitcode})\n")
    script = Path(__file__).parents[1] / "scripts" / "proof-verification-admission.py"
    admitted = subprocess.run(
        [
            sys.executable,
            str(script),
            "start",
            "--verifier",
            str(verifier),
            "--attempt-dir",
            str(tmp_path / "attempt"),
        ],
        capture_output=True,
        check=False,
    )
    assert admitted.returncode == 0
    record = Path(admitted.stdout.decode().strip())
    executed = subprocess.run(
        [sys.executable, str(script), "execute", "--start", str(record)],
        capture_output=True,
        check=False,
    )
    assert executed.returncode == exitcode
    assert executed.stdout == b"cli output\n"
    assert executed.stderr == b""
    assert (
        json.loads((record.parent / "execution.json").read_bytes())["returncode"]
        == exitcode
    )


def test_stale_helper_bytecode_cannot_replace_admitted_source(tmp_path: Path) -> None:
    """An old timestamp-valid pyc cannot supply different helper bytes."""
    helper = tmp_path / "helper.py"
    helper.write_text("VALUE = 'stale'\n")
    previous = helper.stat()
    py_compile.compile(str(helper), doraise=True)
    helper.write_text("VALUE = 'fresh'\n")
    os.utime(helper, ns=(previous.st_atime_ns, previous.st_mtime_ns))
    verifier = tmp_path / "verify.py"
    verifier.write_text("import helper\nprint(helper.VALUE)\n")
    record = verification_admission.start(
        verifier, helpers=[helper], attempt_dir=tmp_path / "attempt"
    )
    result = verification_admission.execute(record)
    assert result.stdout == b"fresh\n"


@pytest.mark.parametrize("bad_record", ["{}", "null", "{", '{"binding": {}}'])
def test_malformed_start_refused(tmp_path: Path, bad_record: str) -> None:
    """Unreadable bindings cannot execute or claim a sealed attempt."""
    record = tmp_path / "START.json"
    record.write_text(bad_record)
    with pytest.raises(verification_admission.AdmissionError, match="START"):
        verification_admission.execute(record)
    assert not (tmp_path / "execution.claim").exists()


def test_preflight_imports_no_product_modules_in_fresh_process(tmp_path: Path) -> None:
    """A fresh import sentinel refuses any product helper load before START."""
    verifier = tmp_path / "verify.py"
    verifier.write_text("import product\nraise RuntimeError('verifier executed')\n")
    helper = tmp_path / "helper.py"
    helper.write_text("raise RuntimeError('helper executed')\n")
    probe = tmp_path / "probe.py"
    probe.write_text(
        "import importlib.abc, sys\n"
        "from pathlib import Path\n"
        "class ProductImportSentinel(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, fullname, path=None, target=None):\n"
        "        if fullname in ('product', 'helper') or (\n"
        "            fullname.startswith('dotfiles_setup.') and\n"
        "            fullname != 'dotfiles_setup.verification_admission'\n"
        "        ):\n"
        "            raise RuntimeError('product imported: ' + fullname)\n"
        "sys.meta_path.insert(0, ProductImportSentinel())\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "from dotfiles_setup import verification_admission\n"
        "verification_admission.start(Path(sys.argv[2]),\n"
        "    helpers=[Path(sys.argv[3])], attempt_dir=Path(sys.argv[4]))\n"
    )
    result = subprocess.run(
        [
            sys.executable,
            str(probe),
            str(Path(__file__).parents[1] / "python" / "src"),
            str(verifier),
            str(helper),
            str(tmp_path / "attempt"),
        ],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode()
    assert (tmp_path / "attempt" / "START.json").is_file()


def test_cleanup_failure_retains_partial_capture_and_unavailable_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """OS cleanup refusal cannot erase a started attempt or invent its exit."""
    verifier = tmp_path / "verify.py"
    verifier.write_text("import time\nprint('started', flush=True)\ntime.sleep(10)\n")
    record = verification_admission.start(verifier, attempt_dir=tmp_path / "attempt")
    processes: list[subprocess.Popen[bytes]] = []
    real_killpg = os.killpg

    class BriefCommunicate(subprocess.Popen[bytes]):
        def communicate(
            self, *_args: object, timeout: float | None = None, **_kwargs: object
        ) -> tuple[bytes, bytes]:
            if not processes:
                processes.append(self)
                communicate = super().communicate
                return communicate_after_output_is_available(
                    lambda: communicate(timeout=0.1)
                )
            return super().communicate(
                timeout=0.1 if timeout is None else min(timeout, 0.1)
            )

    def refuse_group(pid: int, signum: int) -> None:
        if any(process.pid == pid for process in processes):
            message = "SYNTHETIC_CLEANUP_ERROR"
            raise PermissionError(message)
        real_killpg(pid, signum)

    monkeypatch.setattr(subprocess, "Popen", BriefCommunicate)
    monkeypatch.setattr(os, "killpg", refuse_group)
    try:
        assert verification_admission.main(["execute", "--start", str(record)]) == 2
        evidence = json.loads((record.parent / "execution.json").read_bytes())
        assert evidence["returncode"] is None
        assert evidence["timed_out"] is True
        assert evidence["capture_complete"] is False
        assert evidence["failures"] == [
            {"stage": "cleanup", "type": "os-error"},
            {"stage": "drain", "type": "timeout"},
        ]
        assert (record.parent / "stdout.bin").read_bytes() == b"started\n"
        assert (record.parent / "stderr.bin").read_bytes() == b""
        assert "SYNTHETIC_CLEANUP_ERROR" not in (
            json.dumps(evidence) + capsys.readouterr().err
        )
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=3)


@pytest.mark.parametrize("failure", ["timeout", "os-error"])
def test_second_drain_failure_refuses_completion_with_known_zero_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
) -> None:
    """A literal leader exit0 is retained even when capture settlement fails."""
    verifier = tmp_path / "verify.py"
    verifier.write_text(
        "import sys\nprint('available')\nprint('stderr', file=sys.stderr)\n"
    )
    record = verification_admission.start(verifier, attempt_dir=tmp_path / "attempt")

    class FailedDrain(subprocess.Popen[bytes]):
        calls = 0

        def communicate(
            self, *_args: object, timeout: float | None = None, **_kwargs: object
        ) -> tuple[bytes, bytes]:
            self.calls += 1
            if self.calls == 1:
                stdout, stderr = super().communicate(
                    timeout=3 if timeout is None else min(timeout, 3)
                )
                raise subprocess.TimeoutExpired(
                    self.args, 3, output=stdout, stderr=stderr
                )
            if failure == "os-error":
                message = "SYNTHETIC_DRAIN_ERROR"
                raise OSError(message)
            raise subprocess.TimeoutExpired(self.args, 10)

    monkeypatch.setattr(subprocess, "Popen", FailedDrain)
    assert verification_admission.main(["execute", "--start", str(record)]) == 2
    evidence = json.loads((record.parent / "execution.json").read_bytes())
    assert evidence["returncode"] == 0
    assert evidence["capture_complete"] is False
    assert evidence["failures"] == [{"stage": "drain", "type": failure}]
    assert (record.parent / "stdout.bin").read_bytes() == b"available\n"
    assert (record.parent / "stderr.bin").read_bytes() == b"stderr\n"
    assert "SYNTHETIC_DRAIN_ERROR" not in json.dumps(evidence) + capsys.readouterr().err


@pytest.mark.parametrize("failure", [OSError, KeyboardInterrupt])
def test_initial_capture_error_publishes_after_bounded_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: type[BaseException],
) -> None:
    """Unexpected capture failure and interruption retain drained bytes and rc."""
    verifier = tmp_path / "verify.py"
    verifier.write_text("import time\nprint('available', flush=True)\ntime.sleep(10)\n")
    record = verification_admission.start(verifier, attempt_dir=tmp_path / "attempt")
    processes: list[subprocess.Popen[bytes]] = []

    class FailedCapture(subprocess.Popen[bytes]):
        calls = 0

        def communicate(
            self, *_args: object, timeout: float | None = None, **_kwargs: object
        ) -> tuple[bytes, bytes]:
            self.calls += 1
            if self.calls == 1:
                processes.append(self)
                try:
                    communicate = super().communicate
                    return communicate_after_output_is_available(
                        lambda: communicate(timeout=0.1)
                    )
                except subprocess.TimeoutExpired:
                    message = "SYNTHETIC_CAPTURE_ERROR"
                    raise failure(message) from None
            return super().communicate(timeout=timeout)

    monkeypatch.setattr(subprocess, "Popen", FailedCapture)
    try:
        with pytest.raises(verification_admission.AdmissionError, match="incomplete"):
            verification_admission.execute(record)
        evidence = json.loads((record.parent / "execution.json").read_bytes())
        assert evidence["returncode"] < 0
        assert evidence["capture_complete"] is False
        assert evidence["failures"] == [
            {
                "stage": "communicate",
                "type": "os-error" if failure is OSError else "interrupted",
            }
        ]
        assert (record.parent / "stdout.bin").read_bytes() == b"available\n"
        assert "SYNTHETIC_CAPTURE_ERROR" not in json.dumps(evidence)
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=3)


def test_cleanup_refusal_does_not_mislabel_a_completed_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Capture completeness and cleanup failure remain separate observations."""
    verifier = tmp_path / "verify.py"
    verifier.write_text("print('complete capture')\n")
    record = verification_admission.start(verifier, attempt_dir=tmp_path / "attempt")
    processes: list[subprocess.Popen[bytes]] = []
    real_killpg = os.killpg

    class TimedOutCapture(subprocess.Popen[bytes]):
        calls = 0

        def communicate(
            self, *_args: object, timeout: float | None = None, **_kwargs: object
        ) -> tuple[bytes, bytes]:
            self.calls += 1
            captures = super().communicate(timeout=timeout)
            if self.calls == 1:
                processes.append(self)
                raise subprocess.TimeoutExpired(self.args, 1, output=captures[0])
            return captures

    def refuse_group(pid: int, signum: int) -> None:
        if any(process.pid == pid for process in processes):
            message = "SYNTHETIC_CLEANUP_ERROR"
            raise OSError(message)
        real_killpg(pid, signum)

    monkeypatch.setattr(subprocess, "Popen", TimedOutCapture)
    monkeypatch.setattr(os, "killpg", refuse_group)
    with pytest.raises(verification_admission.AdmissionError, match="incomplete"):
        verification_admission.execute(record)
    evidence = json.loads((record.parent / "execution.json").read_bytes())
    assert evidence["returncode"] == 0
    assert evidence["capture_complete"] is True
    assert evidence["failures"] == [{"stage": "cleanup", "type": "os-error"}]
    assert (record.parent / "stdout.bin").read_bytes() == b"complete capture\n"
