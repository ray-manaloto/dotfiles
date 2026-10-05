# Copyright (c) 2026 Raymond Manaloto
"""Public aggregate-budget interfaces, with isolated launch-time fixture trees."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from shutil import copyfile
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup.codec import decode
from dotfiles_setup.instruction_total import instruction_total_main, measure_eager
from dotfiles_setup.verify import load_manifest, run_suite

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_TOTAL = 43
ENTRY_TOTAL = 38
UNICODE_FILE_CHARS = 3
IMPORTED_FILE_CHARS = 6
LIVE_IMPORT_CHARS = 5
RAW_COMMENT_CHARS = 9
RAW_RULE_CHARS = 32
EXPECTED_DEFAULT_LIMIT = 140_000
CLI_TIMEOUT = 30
WIRING_SUITE = "workflow.instruction-total-enforcement"


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def eager_tree(tmp_path: Path) -> Path:
    """43 characters: 11 + 3 + 18 + 6 + 5, independent literal expectations."""
    _write(tmp_path, "CLAUDE.md", "@AGENTS.md\n")
    _write(tmp_path, "AGENTS.md", "é🚀\n")
    _write(tmp_path, ".claude/CLAUDE.md", "@token-routing.md\n")
    _write(tmp_path, ".claude/token-routing.md", "route\n")
    _write(tmp_path, ".claude/rules/core.md", "keep\n")
    return tmp_path


def _cli(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "dotfiles_setup.main",
            "instruction-total",
            "--root",
            str(root),
            *arguments,
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
        timeout=CLI_TIMEOUT,
    )


@pytest.mark.parametrize(
    ("limit", "expected_rc", "expected_over"),
    [(44, 0, False), (43, 0, False), (42, 1, True)],
    ids=["under", "boundary", "over"],
)
def test_cli_limit_arms(
    eager_tree: Path, limit: int, expected_rc: int, *, expected_over: bool
) -> None:
    """The boundary belongs to the pass arm; one character more must fail."""
    result = _cli(eager_tree, "--limit", str(limit), "--json")
    assert result.returncode == expected_rc, result.stderr
    assert decode(result.stdout.encode(), dict) == {
        "total": FIXTURE_TOTAL,
        "limit": limit,
        "files": [
            {"path": ".claude/CLAUDE.md", "chars": 18},
            {"path": ".claude/rules/core.md", "chars": 5},
            {"path": ".claude/token-routing.md", "chars": 6},
            {"path": "AGENTS.md", "chars": UNICODE_FILE_CHARS},
            {"path": "CLAUDE.md", "chars": 11},
        ],
        "over": expected_over,
    }


def test_cli_counts_unscoped_rules(eager_tree: Path) -> None:
    """Dropping rule_unscoped changes this required rc 1 into rc 0."""
    with_unscoped_rule = _cli(eager_tree, "--limit", str(ENTRY_TOTAL))
    assert with_unscoped_rule.returncode == 1, with_unscoped_rule.stderr
    assert "43 chars across 5 files" in with_unscoped_rule.stdout
    (eager_tree / ".claude/rules/core.md").unlink()
    without_unscoped_rule = _cli(eager_tree, "--limit", str(ENTRY_TOTAL))
    assert without_unscoped_rule.returncode == 0, without_unscoped_rule.stderr
    assert "38 chars across 4 files" in without_unscoped_rule.stdout


def test_cli_default_limit(eager_tree: Path) -> None:
    """Default is the literal specified limit, with a real over-limit control."""
    default_pass = _cli(eager_tree, "--json")
    assert default_pass.returncode == 0, default_pass.stderr
    assert decode(default_pass.stdout.encode(), dict)["limit"] == EXPECTED_DEFAULT_LIMIT
    _write(eager_tree, ".claude/rules/large.md", "x" * 140_000)
    default_fail = _cli(eager_tree)
    assert default_fail.returncode == 1, default_fail.stderr
    assert "140043 chars" in default_fail.stdout


def test_measure_counts_recursive_rules_and_excludes_scoped(eager_tree: Path) -> None:
    """Lazy stubs, evidence, and paths-frontmatter stay out of the eager set."""
    _write(eager_tree, ".claude/rules/deep/nested.md", "nested\n")
    _write(
        eager_tree, ".claude/rules/scoped.md", '---\npaths: ["python/**"]\n---\nlazy\n'
    )
    _write(eager_tree, "docs/CLAUDE.md", "@AGENTS.md\n")
    _write(eager_tree, "docs/AGENTS.md", "lazy\n")
    _write(eager_tree, "docs/rules-evidence/core.md", "case history\n")
    measured = measure_eager(eager_tree)
    assert measured == {
        ".claude/CLAUDE.md": 18,
        ".claude/rules/core.md": 5,
        ".claude/rules/deep/nested.md": 7,
        ".claude/token-routing.md": 6,
        "AGENTS.md": UNICODE_FILE_CHARS,
        "CLAUDE.md": 11,
    }


def test_measure_keeps_raw_comments_and_frontmatter(eager_tree: Path) -> None:
    """Raw text includes comments and a prose paths: mention never makes it lazy."""
    _write(eager_tree, "AGENTS.md", "<!--é-->\n")
    _write(eager_tree, ".claude/rules/core.md", "---\nname: core\n---\npaths: prose\n")
    measured = measure_eager(eager_tree)
    assert measured["AGENTS.md"] == RAW_COMMENT_CHARS
    assert measured[".claude/rules/core.md"] == RAW_RULE_CHARS


def test_measure_counts_shared_import_once(eager_tree: Path) -> None:
    """A rule imported by a root is still the same eager file, counted once."""
    _write(eager_tree, "CLAUDE.md", "@AGENTS.md\n@.claude/rules/core.md\n")
    _write(eager_tree, ".claude/CLAUDE.md", "@token-routing.md\n@../AGENTS.md\n")
    assert measure_eager(eager_tree) == {
        ".claude/CLAUDE.md": 32,
        ".claude/rules/core.md": 5,
        ".claude/token-routing.md": 6,
        "AGENTS.md": UNICODE_FILE_CHARS,
        "CLAUDE.md": 34,
    }


def test_measure_respects_shared_import_parser(eager_tree: Path) -> None:
    """Real imports count; commented, fenced, and inline examples do not."""
    _write(
        eager_tree,
        "AGENTS.md",
        "@live.md\n<!-- @comment.md -->\n`@inline.md`\n```\n@fenced.md\n```\n",
    )
    for name in ("live", "comment", "inline", "fenced"):
        _write(eager_tree, f"{name}.md", "text\n")
    measured = measure_eager(eager_tree)
    assert measured["live.md"] == LIVE_IMPORT_CHARS
    assert {"comment.md", "inline.md", "fenced.md"}.isdisjoint(measured)


def test_measure_respects_literal_import_punctuation(eager_tree: Path) -> None:
    """A punctuation typo stays unresolved until the import itself is corrected."""
    _write(eager_tree, ".claude/CLAUDE.md", "@token-routing.md.\n")
    measured = measure_eager(eager_tree)
    assert ".claude/token-routing.md" not in measured
    assert sum(measured.values()) == ENTRY_TOTAL
    _write(eager_tree, ".claude/CLAUDE.md", "@token-routing.md\n")
    corrected = measure_eager(eager_tree)
    assert corrected[".claude/token-routing.md"] == IMPORTED_FILE_CHARS
    assert sum(corrected.values()) == FIXTURE_TOTAL


def test_cli_emits_top_five(
    eager_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Over-limit output orders the largest five; passing output omits the list."""
    for name, count in (("big", 90), ("small", 80)):
        _write(eager_tree, f".claude/rules/{name}.md", "x" * count)
    assert instruction_total_main(eager_tree, limit=ENTRY_TOTAL) == 1
    assert capsys.readouterr().out.splitlines()[1:] == [
        "Largest eager files (top 5):",
        "  .claude/rules/big.md: 90 chars",
        "  .claude/rules/small.md: 80 chars",
        "  .claude/CLAUDE.md: 18 chars",
        "  CLAUDE.md: 11 chars",
        "  .claude/token-routing.md: 6 chars",
    ]
    assert instruction_total_main(eager_tree, limit=213) == 0
    assert "Largest" not in capsys.readouterr().out


@pytest.mark.parametrize(
    "problem", ["missing-root", "missing-entry", "rules-file", "entry-directory"]
)
def test_cli_rejects_misconfiguration(eager_tree: Path, problem: str) -> None:
    """Cannot enumerate is rc 2, distinct from a measured over-limit rc 1."""
    passing = _cli(eager_tree, "--json")
    assert passing.returncode == 0, passing.stderr
    root = eager_tree
    if problem == "missing-root":
        root = eager_tree / "missing"
    elif problem == "missing-entry":
        (eager_tree / "CLAUDE.md").unlink()
    elif problem == "rules-file":
        (eager_tree / ".claude/rules/core.md").unlink()
        (eager_tree / ".claude/rules").rmdir()
        _write(eager_tree, ".claude/rules", "not a directory\n")
    else:
        (eager_tree / ".claude/CLAUDE.md").unlink()
        (eager_tree / ".claude/CLAUDE.md").mkdir()
    result = _cli(root, "--json")
    assert result.returncode == 2, result.stderr
    assert "instruction-total error:" in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize(
    "relative", ["CLAUDE.md", "AGENTS.md", ".claude/rules/core.md"]
)
def test_invalid_encoding_fails_closed(
    eager_tree: Path, relative: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unreadable eager member cannot be replaced or dropped into a pass."""
    (eager_tree / relative).write_bytes(b"\xff")
    assert instruction_total_main(eager_tree) == 2
    assert "instruction-total error:" in capsys.readouterr().err
    _write(eager_tree, relative, "fixed\n")
    assert instruction_total_main(eager_tree) == 0


def test_cli_rejects_negative_limit(eager_tree: Path) -> None:
    """Negative budgets are misconfiguration; zero is a valid failing budget."""
    invalid = _cli(eager_tree, "--limit", "-1")
    assert invalid.returncode == 2, invalid.stderr
    assert "limit must be nonnegative" in invalid.stderr
    zero = _cli(eager_tree, "--limit", "0")
    assert zero.returncode == 1, zero.stderr


def _isolated_wiring_contract(tmp_path: Path) -> dict[str, Any]:
    """Copy real contract inputs, using absolute paths instead of patching roots."""
    manifest = REPO_ROOT / "python/verification/suites.toml"
    entry = next(
        suite for suite in load_manifest(manifest) if suite["name"] == WIRING_SUITE
    )
    for relative in entry["paths"]:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        copyfile(REPO_ROOT / relative, target)
    return entry | {
        "paths": [str(tmp_path / relative) for relative in entry["paths"]],
        "per_path_lines": {
            str(tmp_path / relative): lines
            for relative, lines in entry["per_path_lines"].items()
        },
    }


@pytest.mark.parametrize(
    ("relative", "line"),
    [
        ("hk.pkl", '["instruction_total"] {'),
        (
            "hk.pkl",
            'check = "uv run --project python dotfiles-setup instruction-total"',
        ),
        ("mise.toml", "[tasks.instruction-total]"),
        (
            "mise.toml",
            "run = 'uv run --project python dotfiles-setup instruction-total'",
        ),
        ("python/src/dotfiles_setup/main.py", '"instruction-total",'),
        ("python/src/dotfiles_setup/main.py", '"instruction-total": lambda: sys.exit('),
        ("python/src/dotfiles_setup/main.py", "instruction_total_main("),
        (
            "python/src/dotfiles_setup/main.py",
            "_add_instruction_total_subcommand(subparsers)",
        ),
        (
            "python/src/dotfiles_setup/instruction_total.py",
            (
                "from kb_setup.md_budget import classify, has_paths_frontmatter, "
                "resolve_imports"
            ),
        ),
        (
            "python/src/dotfiles_setup/instruction_total.py",
            'if classify(relative) != "rule_unscoped":',
        ),
        (
            "python/src/dotfiles_setup/instruction_total.py",
            "members.update(path.resolve() for path in resolve_imports(entry, root))",
        ),
        (
            "python/src/dotfiles_setup/instruction_total.py",
            'if not has_paths_frontmatter(path.read_text(encoding="utf-8")):',
        ),
        ("tests/test_instruction_total.py", "def test_cli_limit_arms("),
        (
            "tests/test_instruction_total.py",
            "def test_cli_counts_unscoped_rules(eager_tree: Path) -> None:",
        ),
        (
            "tests/test_instruction_total.py",
            "def test_cli_default_limit(eager_tree: Path) -> None:",
        ),
        (
            "tests/test_instruction_total.py",
            "def test_wiring_contract_rejects_missing_or_commented_lines(",
        ),
        (
            "tests/test_instruction_total.py",
            "def test_wiring_contract_rejects_missing_paths(",
        ),
        (
            "tests/test_instruction_total.py",
            "[(44, 0, False), (43, 0, False), (42, 1, True)],",
        ),
        (
            "tests/test_instruction_total.py",
            "assert result.returncode == expected_rc, result.stderr",
        ),
        (
            "tests/test_instruction_total.py",
            "assert decode(result.stdout.encode(), dict) == {",
        ),
        (
            "tests/test_instruction_total.py",
            "assert with_unscoped_rule.returncode == 1, with_unscoped_rule.stderr",
        ),
        (
            "tests/test_instruction_total.py",
            (
                "assert without_unscoped_rule.returncode == 0, "
                "without_unscoped_rule.stderr"
            ),
        ),
        ("tests/test_instruction_total.py", "EXPECTED_DEFAULT_LIMIT = 140_000"),
        (
            "tests/test_instruction_total.py",
            "assert default_pass.returncode == 0, default_pass.stderr",
        ),
        (
            "tests/test_instruction_total.py",
            (
                'assert decode(default_pass.stdout.encode(), dict)["limit"] '
                "== EXPECTED_DEFAULT_LIMIT"
            ),
        ),
        (
            "tests/test_instruction_total.py",
            "assert default_fail.returncode == 1, default_fail.stderr",
        ),
        (
            "tests/test_instruction_total.py",
            'assert line_baseline["status"] == "passed", line_baseline',
        ),
        (
            "tests/test_instruction_total.py",
            'assert line_mutation["status"] == "failed", line_mutation',
        ),
        (
            "tests/test_instruction_total.py",
            'assert path_baseline["status"] == "passed", path_baseline',
        ),
        (
            "tests/test_instruction_total.py",
            'assert path_mutation["status"] == "failed", path_mutation',
        ),
    ],
)
@pytest.mark.parametrize("mutation", ["delete", "comment"])
def test_wiring_contract_rejects_missing_or_commented_lines(
    tmp_path: Path, relative: str, line: str, mutation: str
) -> None:
    """Real declarations pass; removing or commenting a required seam must fail."""
    entry = _isolated_wiring_contract(tmp_path)
    line_baseline = run_suite(entry)
    assert line_baseline["status"] == "passed", line_baseline
    target = tmp_path / relative
    source = target.read_text(encoding="utf-8").splitlines(keepends=True)
    matches = [index for index, raw in enumerate(source) if raw.strip() == line]
    assert len(matches) == 1
    index = matches[0]
    source[index] = "" if mutation == "delete" else f"# {line}\n"
    target.write_text("".join(source), encoding="utf-8")
    line_mutation = run_suite(entry)
    assert line_mutation["status"] == "failed", line_mutation
    assert str(target) in line_mutation["reason"]


@pytest.mark.parametrize(
    "relative",
    [
        "hk.pkl",
        "mise.toml",
        "python/src/dotfiles_setup/main.py",
        "python/src/dotfiles_setup/instruction_total.py",
        "tests/test_instruction_total.py",
    ],
)
def test_wiring_contract_rejects_missing_paths(tmp_path: Path, relative: str) -> None:
    """Any vanished participant fails even when the other files still exist."""
    entry = _isolated_wiring_contract(tmp_path)
    path_baseline = run_suite(entry)
    assert path_baseline["status"] == "passed", path_baseline
    target = tmp_path / relative
    target.unlink()
    path_mutation = run_suite(entry)
    assert path_mutation["status"] == "failed", path_mutation
    assert str(target) in path_mutation["reason"]
