# Copyright (c) 2026 Raymond Manaloto
"""Saved verifier admission through the public file and execution boundaries."""

from __future__ import annotations

import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import verification_admission


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
