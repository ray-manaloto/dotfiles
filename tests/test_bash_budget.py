"""Tests for the zero-bash-logic enforcer (dotfiles_setup.bash_budget).

Two layers: isolated logic tests (monkeypatch the tracked set + ALLOWLIST so
the three failure kinds are exercised without touching the real tree) and
real-repo guards (the allowlist must exactly equal the tracked in-scope set,
the tree must currently pass, and the CLI must wire end-to-end).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import bash_budget

if TYPE_CHECKING:
    import pytest

REPO_ROOT = Path(__file__).parent.parent


def _write(path: Path, n_lines: int) -> None:
    """Write a file whose ``wc -l`` (newline count) is exactly ``n_lines``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x\n" * n_lines)


def _isolate(
    monkeypatch: pytest.MonkeyPatch,
    *,
    allowlist: dict[str, bash_budget.BashAllowance],
    tracked: list[str],
) -> None:
    monkeypatch.setattr(bash_budget, "ALLOWLIST", allowlist)
    monkeypatch.setattr(bash_budget, "tracked_in_scope", lambda _root: tracked)


def test_new_unlisted_script_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _isolate(
        monkeypatch,
        allowlist={"scripts/known.sh": bash_budget.BashAllowance(10, "wrapper")},
        tracked=["scripts/known.sh", "scripts/new.sh"],
    )
    _write(tmp_path / "scripts/known.sh", 5)
    _write(tmp_path / "scripts/new.sh", 3)
    kinds = {(v.path, v.kind) for v in bash_budget.find_violations(tmp_path)}
    assert ("scripts/new.sh", "unlisted") in kinds
    assert ("scripts/known.sh", "growth") not in kinds


def test_growth_past_budget_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _isolate(
        monkeypatch,
        allowlist={"scripts/known.sh": bash_budget.BashAllowance(26, "wrapper")},
        tracked=["scripts/known.sh"],
    )
    _write(tmp_path / "scripts/known.sh", 30)
    violations = bash_budget.find_violations(tmp_path)
    assert [(v.path, v.kind) for v in violations] == [("scripts/known.sh", "growth")]


def test_shrink_and_at_budget_pass(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _isolate(
        monkeypatch,
        allowlist={"scripts/known.sh": bash_budget.BashAllowance(26, "wrapper")},
        tracked=["scripts/known.sh"],
    )
    # Shrink: below budget is always fine.
    _write(tmp_path / "scripts/known.sh", 20)
    assert bash_budget.find_violations(tmp_path) == []
    # Exactly at budget is fine (only strictly-greater fails).
    _write(tmp_path / "scripts/known.sh", 26)
    assert bash_budget.find_violations(tmp_path) == []


def test_stale_allowlist_entry_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _isolate(
        monkeypatch,
        allowlist={"scripts/deleted.sh": bash_budget.BashAllowance(10, "wrapper")},
        tracked=[],
    )
    violations = bash_budget.find_violations(tmp_path)
    assert [(v.path, v.kind) for v in violations] == [("scripts/deleted.sh", "stale")]


def test_allowlist_equals_tracked_in_scope() -> None:
    """Allowlist must equal the tracked in-scope set (no stale, no unlisted)."""
    tracked = set(bash_budget.tracked_in_scope(REPO_ROOT))
    assert set(bash_budget.ALLOWLIST) == tracked


def test_repo_currently_compliant() -> None:
    assert bash_budget.find_violations(REPO_ROOT) == []


def test_budgets_at_or_above_current_size() -> None:
    """Every baseline budget is >= the file's size, so a shrink never trips."""
    for rel, allowance in bash_budget.ALLOWLIST.items():
        actual = bash_budget.line_count(REPO_ROOT / rel)
        assert actual <= allowance.max_lines, (
            f"{rel}: {actual} lines exceeds budget {allowance.max_lines}"
        )


def test_cli_wires_end_to_end() -> None:
    """The `bash-budget` subcommand runs through main.py and passes clean."""
    res = subprocess.run(
        ["uv", "run", "--project", "python", "dotfiles-setup", "bash-budget"],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
        timeout=120,
    )
    assert res.returncode == 0, res.stderr
