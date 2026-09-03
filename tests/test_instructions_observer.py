# Copyright (c) 2026 Raymond Manaloto
"""Tests for the InstructionsLoaded hot-path observer (#917).

Layers: pure `build_record`/`session_filename` unit tests (the PUBLIC
interface, per `tests/AGENTS.md` — implementation details are exercised
through it, not by reaching into private module state), the C1
stdlib-only-imports assertion (the hot-path cost guarantee), the C1b
foreign-cwd project-root resolution (through a real subprocess), the C1c
real subprocess arm (the `__main__` guard trap — a module missing it
silently no-ops and still exits 0), the C2 fail-open control arm, the C3
session_id sanitizer (including the ABSENT-value cases the spec's premise
pass added), and the C4 record-size and concurrent-append integrity arms.
"""

from __future__ import annotations

import ast
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import instructions_observer as obs

if TYPE_CHECKING:
    import pytest

REPO_ROOT = Path(__file__).parent.parent
_OBSERVER_REL = "python/src/dotfiles_setup/instructions_observer.py"
MODULE_PATH = REPO_ROOT / _OBSERVER_REL
_RECORDS_REL = ".agent/instructions-loaded"


def _run_observer(
    payload: str, *, project_root: Path, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Drive the module as the harness would: `python -m ...`, stdin, env."""
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(project_root)
    env["PYTHONPATH"] = str(REPO_ROOT / "python" / "src")
    return subprocess.run(
        [sys.executable, "-m", "dotfiles_setup.instructions_observer"],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd or project_root),
        env=env,
        timeout=30,
    )


# --------------------------------------------------------------------------
# C1 — hot path stays stdlib-only, at module scope AND below (transitive).
# --------------------------------------------------------------------------


def _imported_top_level_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def test_module_scope_imports_are_stdlib_only() -> None:
    """No `dotfiles_setup` or third-party import anywhere in the source text.

    A regression here silently reintroduces the ~0.27s `dotfiles_setup.main`
    import tax on every one of the ~37 eligible files, per session start,
    times every subagent (C1). ``sys.stdlib_module_names`` is queried live
    rather than hand-listed, so a stdlib addition never produces a false
    failure.

    R11: the negative half (no non-stdlib import) alone is satisfied by a
    stub file containing nothing but ``import json`` — it does no work but
    also imports nothing to object to. The positive half below closes that:
    every stdlib module the real implementation actually needs (JSON
    encoding, the C3 filename sanitizer's charset, C1b's env-var lookup, the
    UTC timestamp, the O_APPEND write, and R4's tempdir fallback) must
    actually be imported, so a gutted stub fails this test too.
    """
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imported = _imported_top_level_names(tree)
    assert imported, "expected at least one import to check"
    non_stdlib = imported - sys.stdlib_module_names
    assert not non_stdlib, f"non-stdlib top-level import(s) found: {non_stdlib}"
    required = {"json", "logging", "os", "sys", "datetime", "pathlib", "tempfile"}
    missing = required - imported
    assert not missing, f"expected stdlib import(s) missing (stub?): {missing}"


def test_runtime_transitive_imports_are_stdlib_only() -> None:
    """Actually IMPORT the module in a clean interpreter and inspect sys.modules.

    The AST check above only proves the SOURCE never names a non-stdlib
    import; it cannot see a stdlib module whose own import graph pulls in
    something heavier. This is the real, dynamic control arm.
    """
    probe = (
        "import sys\n"
        "before = set(sys.modules)\n"
        "import dotfiles_setup.instructions_observer\n"
        "after = set(sys.modules) - before\n"
        "leaked = {\n"
        "    m for m in after\n"
        "    if m.split('.')[0] not in sys.stdlib_module_names\n"
        "    and m.split('.')[0] != 'dotfiles_setup'\n"
        "}\n"
        "print(','.join(sorted(leaked)))\n"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "python" / "src")
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO_ROOT,
        env=env,
    )
    leaked = result.stdout.strip()
    assert leaked == "", f"non-stdlib modules leaked in transitively: {leaked}"


# --------------------------------------------------------------------------
# build_record
# --------------------------------------------------------------------------


def test_build_record_full_payload() -> None:
    payload = {
        "session_id": "abc123",
        "file_path": str(REPO_ROOT / ".claude/rules/md-size-budgets.md"),
        "memory_type": "Project",
        "load_reason": "path_glob_match",
        "globs": ["hk.pkl", "**/CLAUDE.md"],
        "trigger_file_path": str(REPO_ROOT / "hk.pkl"),
        "parent_file_path": None,
        "agent_id": None,
        "agent_type": "main",
    }
    now = "2026-09-03T00:00:00+00:00"
    record = obs.build_record(payload, project_root=REPO_ROOT, now=now)
    assert record["ts"] == now
    assert record["file_path"] == ".claude/rules/md-size-budgets.md"
    assert record["trigger_file_path"] == "hk.pkl"
    assert record["parent_file_path"] is None
    assert record["memory_type"] == "Project"
    assert record["load_reason"] == "path_glob_match"
    assert record["globs"] == ["hk.pkl", "**/CLAUDE.md"]
    assert record["agent_id"] is None
    assert record["agent_type"] == "main"


def test_build_record_absolute_path_outside_project_root_stays_absolute() -> None:
    payload = {"file_path": "/some/other/repo/CLAUDE.md"}
    record = obs.build_record(payload, project_root=REPO_ROOT, now="t")
    assert record["file_path"] == "/some/other/repo/CLAUDE.md"


def test_build_record_globs_absent_for_non_glob_reasons() -> None:
    """C5: `globs` is present ONLY for path_glob_match — must tolerate absence."""
    payload = {"load_reason": "session_start", "file_path": "CLAUDE.md"}
    record = obs.build_record(payload, project_root=REPO_ROOT, now="t")
    assert record["globs"] is None


def test_build_record_globs_wrong_type_is_dropped() -> None:
    payload = {"globs": "not-a-list"}
    record = obs.build_record(payload, project_root=REPO_ROOT, now="t")
    assert record["globs"] is None


def test_build_record_no_extra_fields() -> None:
    """C5: paths and reasons only — no `cwd`, no `transcript_path`."""
    payload = {
        "cwd": str(REPO_ROOT),
        "transcript_path": "/Users/someone/.claude/projects/x/y.jsonl",
        "file_path": "CLAUDE.md",
    }
    record = obs.build_record(payload, project_root=REPO_ROOT, now="t")
    assert "cwd" not in record
    assert "transcript_path" not in record


def test_build_record_missing_fields_are_none() -> None:
    record = obs.build_record({}, project_root=REPO_ROOT, now="t")
    assert record["file_path"] is None
    assert record["session_id"] is None
    assert record["memory_type"] is None
    assert record["load_reason"] is None
    assert record["globs"] is None


# --------------------------------------------------------------------------
# C3 — session_filename sanitization, including the ABSENT-case coverage
# the premise pass added: missing key, None, non-string all fall back.
# --------------------------------------------------------------------------


def test_session_filename_normal_id() -> None:
    assert obs.session_filename("abc123-XYZ_9") == "abc123-XYZ_9.jsonl"


def test_session_filename_strips_traversal_slash() -> None:
    assert obs.session_filename("../../etc/passwd") == "etcpasswd.jsonl"


def test_session_filename_strips_absolute_prefix() -> None:
    assert obs.session_filename("/etc/passwd") == "etcpasswd.jsonl"


def test_session_filename_nul_byte_stripped() -> None:
    assert obs.session_filename("abc\x00def") == "abcdef.jsonl"


def test_session_filename_pure_traversal_falls_back() -> None:
    assert obs.session_filename("../../..") == "unknown.jsonl"


def test_session_filename_empty_string_falls_back() -> None:
    assert obs.session_filename("") == "unknown.jsonl"


def test_session_filename_none_falls_back() -> None:
    assert obs.session_filename(None) == "unknown.jsonl"


def test_session_filename_non_string_falls_back() -> None:
    assert obs.session_filename(12345) == "unknown.jsonl"
    assert obs.session_filename(["a", "b"]) == "unknown.jsonl"


def test_session_filename_length_is_capped() -> None:
    """Truncation, proven behaviorally rather than against the exact cap.

    Two ids sharing a long common prefix but differing only past the cap
    must sanitize to the SAME filename — that can only happen if excess
    length is being truncated away, without this test needing to know (and
    therefore duplicate) the exact cap value.
    """
    base = "a" * 1000
    assert obs.session_filename(base) == obs.session_filename(base + "-extra-tail")
    assert len(obs.session_filename(base)) < len(base)


def test_session_filename_result_stays_inside_directory(tmp_path: Path) -> None:
    """The write path's own containment check holds for a battery of attempts."""
    directory = tmp_path / "records"
    for attempt in ("../escape", "/etc/passwd", "..", "a/b/c", "..\\..\\win"):
        filename = obs.session_filename(attempt)
        target = (directory / filename).resolve()
        assert target.is_relative_to(directory.resolve()), (attempt, filename)


# --------------------------------------------------------------------------
# C1b/C1c — REAL subprocess arms. These are the ones that discriminate a
# missing `__main__` guard: without it, the module does nothing and still
# exits 0, indistinguishable from the C2 fail-open path unless a positive
# arm proves a well-formed payload actually writes a record somewhere.
# --------------------------------------------------------------------------


def test_subprocess_positive_arm_writes_a_record(tmp_path: Path) -> None:
    payload = json.dumps(
        {
            "session_id": "subprocess-positive",
            "file_path": "CLAUDE.md",
            "load_reason": "session_start",
            "memory_type": "Project",
        }
    )
    result = _run_observer(payload, project_root=tmp_path)
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    target = tmp_path / _RECORDS_REL / "subprocess-positive.jsonl"
    assert target.exists(), "the __main__ guard must actually invoke observe_main()"
    record = json.loads(target.read_text().splitlines()[0])
    assert record["file_path"] == "CLAUDE.md"
    assert record["load_reason"] == "session_start"


def test_subprocess_negative_arm_malformed_stdin_fails_open(tmp_path: Path) -> None:
    """C2 control arm, run through the REAL subprocess, not the function."""
    result = _run_observer("not json{{{", project_root=tmp_path)
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    records_dir = tmp_path / _RECORDS_REL
    jsonl_files = list(records_dir.glob("*.jsonl")) if records_dir.is_dir() else []
    assert jsonl_files == []
    error_log = records_dir / "errors.log"
    assert error_log.exists()
    assert "JSONDecodeError" in error_log.read_text()


def test_subprocess_non_dict_payload_writes_nothing(tmp_path: Path) -> None:
    result = _run_observer("[1, 2, 3]", project_root=tmp_path)
    assert result.returncode == 0
    assert not (tmp_path / _RECORDS_REL).exists()


def test_subprocess_foreign_cwd_lands_via_env_var_not_cwd(tmp_path: Path) -> None:
    """C1b: the #343 defect class.

    cwd is a SIBLING directory to the real project root — the record must
    land under the env var's target, never under cwd, and cwd must gain
    nothing.
    """
    real_root = tmp_path / "real-project"
    real_root.mkdir()
    foreign_cwd = tmp_path / "unrelated-sibling"
    foreign_cwd.mkdir()
    payload = json.dumps(
        {
            "session_id": "foreign-cwd",
            "file_path": "CLAUDE.md",
            "load_reason": "session_start",
        }
    )
    result = _run_observer(payload, project_root=real_root, cwd=foreign_cwd)
    assert result.returncode == 0
    assert (real_root / _RECORDS_REL / "foreign-cwd.jsonl").exists()
    assert not (foreign_cwd / ".agent").exists()


# --------------------------------------------------------------------------
# C4 — record byte cap and single-syscall concurrent-append integrity.
# Driven through the public entrypoint (observe_main via subprocess), never
# by reaching into the private writer directly.
# --------------------------------------------------------------------------


def test_oversized_record_is_dropped_and_logged(tmp_path: Path) -> None:
    """R4: a drop path must not return silently — errors.log must trace it."""
    huge_path = "x" * 50_000
    payload = json.dumps(
        {
            "session_id": "oversized",
            "file_path": huge_path,
            "load_reason": "session_start",
        }
    )
    result = _run_observer(payload, project_root=tmp_path)
    assert result.returncode == 0
    target = tmp_path / _RECORDS_REL / "oversized.jsonl"
    assert not target.exists()
    error_log = tmp_path / _RECORDS_REL / "errors.log"
    assert error_log.exists()
    assert "exceeds" in error_log.read_text()


def test_two_records_append_as_two_lines(tmp_path: Path) -> None:
    for i in range(2):
        payload = json.dumps(
            {
                "session_id": "sess",
                "file_path": f"rule-{i}.md",
                "load_reason": "session_start",
            }
        )
        result = _run_observer(payload, project_root=tmp_path)
        assert result.returncode == 0
    target = tmp_path / _RECORDS_REL / "sess.jsonl"
    lines = target.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["file_path"] == "rule-0.md"
    assert json.loads(lines[1])["file_path"] == "rule-1.md"


def test_concurrent_subprocess_appends_never_interleave(tmp_path: Path) -> None:
    """Real concurrency arm for C4.

    N real subprocesses append to ONE session file AT ONCE; every resulting
    line must parse as valid, complete JSON — proof the single unbuffered
    os.write() per record holds under contention.

    R3: the previous version spawned all N processes but then fed each
    one's stdin via a per-process ``proc.communicate(input=..., timeout=30)``
    in a plain loop. Every child blocks in ``sys.stdin.read()`` until FED,
    and ``communicate()`` also waits for the child to fully exit before
    returning — so the loop fed and waited-out process 0 entirely before
    process 1 ever received a byte. All 12 ran strictly serially; no two
    ``os.write()`` calls could ever overlap, so this test could not fail no
    matter how the writer behaved.

    Fixed by writing each child's stdin and closing it in a first pass
    (which unblocks every child's ``read()`` back-to-back, without waiting
    for any of them to exit), THEN waiting for all of them in a second
    pass — the children now genuinely race to append.

    Control arm (R3, `probes-need-a-control-arm.md` rule 2): manually
    mutated `_write_record` to issue the write in two chunks with a
    `time.sleep(0.05)` between them (`os.write(fd, blob[:len(blob)//2]);
    time.sleep(0.05); os.write(fd, blob[len(blob)//2:])`) — the exact
    non-atomic-write defect C4 exists to prevent. Against the OLD
    (serialized) version of this test that mutation passed 12/12 every
    time. Against THIS version it failed on the first run with a
    `json.JSONDecodeError` from an interleaved line, confirming the test
    now discriminates. The mutation was reverted before committing.
    """
    n = 12
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    env["PYTHONPATH"] = str(REPO_ROOT / "python" / "src")
    procs: list[subprocess.Popen[str]] = []
    payloads: list[str] = []
    for i in range(n):
        payload = json.dumps(
            {
                "session_id": "concurrent",
                "file_path": f".claude/rules/rule-{i}.md",
                "load_reason": "path_glob_match",
                "globs": ["some/**/glob"],
            }
        )
        proc = subprocess.Popen(
            [sys.executable, "-m", "dotfiles_setup.instructions_observer"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(tmp_path),
            env=env,
        )
        procs.append(proc)
        payloads.append(payload)
    # Feed every child's stdin and close it, back-to-back, BEFORE waiting on
    # any of them — this is what makes the run genuinely concurrent.
    for proc, payload in zip(procs, payloads, strict=True):
        assert proc.stdin is not None
        proc.stdin.write(payload)
        proc.stdin.close()
    for proc in procs:
        proc.wait(timeout=30)
        assert proc.returncode == 0
    target = tmp_path / _RECORDS_REL / "concurrent.jsonl"
    lines = [line for line in target.read_text().splitlines() if line]
    assert len(lines) == n
    seen_files = set()
    for line in lines:
        record = json.loads(line)  # raises if a line is corrupt/interleaved
        seen_files.add(record["file_path"])
    assert len(seen_files) == n


# --------------------------------------------------------------------------
# R7 — symlinked rule subtrees must normalize the same way scoped_rules_on_
# disk lists them (never resolve() through the symlink).
# --------------------------------------------------------------------------


def test_build_record_symlinked_subtree_normalizes_lexically(tmp_path: Path) -> None:
    """R7: a symlinked `.claude/rules/` subdirectory must still normalize.

    A subdirectory that is physically a symlink to somewhere outside the
    repo — a documented sharing pattern — must still normalize to its
    repo-relative path. The pre-fix code called `.resolve()`, which follows
    the symlink out and returns the absolute target path instead.

    This is deliberately ONE SIDE only — it checks `build_record` against
    the expected string, not against `scoped_rules_on_disk`'s actual
    listing (S3 found `scoped_rules_on_disk` had its own, independent
    symlink gap — `Path.rglob`'s `recurse_symlinks=False` default — that a
    one-sided test on either side could not see). The paired, two-sided
    assertion lives in `test_instructions_paths_consistency.py` (S4).
    """
    real_target = tmp_path / "elsewhere"
    real_target.mkdir()
    project_root = tmp_path / "repo"
    rules_dir = project_root / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "shared").symlink_to(real_target, target_is_directory=True)
    file_path = str(rules_dir / "shared" / "shared-rule.md")
    record = obs.build_record(
        {"file_path": file_path}, project_root=project_root, now="t"
    )
    assert record["file_path"] == ".claude/rules/shared/shared-rule.md"


# --------------------------------------------------------------------------
# R4 — the error channel does not share a fate with what it reports on.
# --------------------------------------------------------------------------


def test_records_dir_unwritable_falls_back_to_tempdir_error_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R4: an unwritable records dir must not silence the error trace too.

    When the primary sibling directory can't be created/written, the error
    line must land somewhere that does NOT depend on it. Driven through the
    PUBLIC entrypoint: `Path.mkdir` is made to raise unconditionally
    (simulating a read-only tree / full disk), which makes `_write_record`'s
    own `mkdir` fail, propagating to `observe_main`'s C2 fail-open handler —
    the realistic path, not a direct call into the private error-logger.
    """
    fallback = Path(tempfile.gettempdir()) / "dotfiles-instructions-observer-errors.log"
    before = fallback.read_text(encoding="utf-8") if fallback.exists() else ""

    def _raise_mkdir(self: Path, *args: object, **kwargs: object) -> None:
        del self, args, kwargs
        message = "simulated read-only tree"
        raise OSError(message)

    monkeypatch.setattr(Path, "mkdir", _raise_mkdir)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    payload = json.dumps(
        {
            "session_id": "unwritable",
            "file_path": "CLAUDE.md",
            "load_reason": "session_start",
        }
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    rc = obs.observe_main()
    assert rc == 0
    after = fallback.read_text(encoding="utf-8")
    assert after.startswith(before)
    assert len(after) > len(before)


# --------------------------------------------------------------------------
# R10 — a short os.write() must be traced, never silently dropped.
# --------------------------------------------------------------------------


def test_short_os_write_is_logged_not_silently_dropped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R10: a short os.write() must be traced, not silently dropped.

    Monkeypatches the syscall itself (the only way to force this rare
    condition) and drives the PUBLIC entrypoint `observe_main`, so the
    short-write path is exercised the same way a real fail-open case would
    be, not by reaching into `_write_record` directly.
    """
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    payload = json.dumps(
        {
            "session_id": "short-write",
            "file_path": "CLAUDE.md",
            "load_reason": "session_start",
        }
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    real_write = os.write

    def _short_write(fd: int, data: bytes) -> int:
        # Actually perform a real, but INCOMPLETE, write — a genuine short
        # write, not a mock that claims one without touching the fd.
        return real_write(fd, data[:-1])

    monkeypatch.setattr(obs.os, "write", _short_write)
    rc = obs.observe_main()
    assert rc == 0
    error_log = tmp_path / _RECORDS_REL / "errors.log"
    assert error_log.exists()
    assert "short os.write" in error_log.read_text()
