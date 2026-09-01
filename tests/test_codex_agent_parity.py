# Copyright (c) 2026 Raymond Manaloto
"""Tests for the codex agent lane parity gate (dotfiles_setup.codex_agent_parity).

Two layers: isolated logic tests against a synthetic tree (so every failure kind
is exercised without mutating the real one) and real-repo guards (the shipped
lanes must currently pass, and the CLI + hk + mise wiring must exist).

Every failure-kind test mutates the fixture in the shape the REAL regression
would take — a tracked toml overwritten by the exporter, a counterpart file
deleted — not a rename, which leaves the original text as a substring and can
make a substring check a no-op.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import codex_agent_parity as cap

REPO_ROOT = Path(__file__).parent.parent

_GOOD_TOML = """name = "codex-advisor"
description = "A second-opinion advisor."
model_reasoning_effort = "xhigh"
developer_instructions = \'\'\'
You advise. Read `.claude/agents/codex-advisor.md` for the wrapper half.
Claude Code is the harness; `claude mcp add` is the command.
\'\'\'
"""


def _tree(root: Path, *, toml: str = _GOOD_TOML, stem: str = "codex-advisor") -> Path:
    """Build a minimal well-formed two-surface fixture and return its root."""
    (root / cap.CLAUDE_AGENT_DIR).mkdir(parents=True)
    (root / cap.CODEX_AGENT_DIR).mkdir(parents=True)
    (root / cap.CLAUDE_AGENT_DIR / f"{stem}.md").write_text("---\nname: x\n---\n")
    (root / cap.CODEX_AGENT_DIR / f"{stem}.toml").write_text(toml)
    return root


def _kinds(root: Path) -> list[str]:
    return [v.kind for v in cap.find_violations(root)]


# ── the passing arm ──────────────────────────────────────────────────────────


def test_a_well_formed_pair_passes(tmp_path: Path) -> None:
    assert cap.find_violations(_tree(tmp_path)) == []


def test_correct_claude_references_are_not_corruption(tmp_path: Path) -> None:
    """The strings the markers are a corruption OF must not trip the check.

    Control arm: the fixture deliberately carries `Claude Code`, `.claude/` and
    `claude mcp add`. If those tripped it, the check could only ever fail —
    exactly as useless as a check that can only pass.
    """
    root = _tree(tmp_path)
    raw = (root / cap.CODEX_AGENT_DIR / "codex-advisor.toml").read_text()
    assert "Claude Code" in raw
    assert ".claude/" in raw
    assert "claude mcp add" in raw
    assert cap.find_violations(root) == []


# ── the failing arms, one per kind ───────────────────────────────────────────


def test_the_exporter_substitution_signature_fails(tmp_path: Path) -> None:
    """The exporter rewrites a TRACKED toml in place.

    The real regression shape: a blind `claude` -> `Codex` substitution.
    """
    root = _tree(tmp_path)
    p = root / cap.CODEX_AGENT_DIR / "codex-advisor.toml"
    p.write_text(
        p.read_text()
        .replace("Claude Code", "Codex Code")
        .replace(".claude/", ".Codex/")
        .replace("claude mcp add", "Codex mcp add")
    )
    assert "corrupted" in _kinds(root)


def test_each_corruption_marker_is_detected_on_its_own(tmp_path: Path) -> None:
    for i, marker in enumerate(cap.CORRUPTION_MARKERS):
        root = tmp_path / f"case{i}"
        root.mkdir()
        _tree(root, toml=_GOOD_TOML.replace("You advise.", f"You {marker} advise."))
        assert "corrupted" in _kinds(root), marker


def test_a_deleted_codex_counterpart_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / cap.CODEX_AGENT_DIR / "codex-advisor.toml").unlink()
    assert _kinds(root) == ["unpaired"]


def test_a_deleted_claude_counterpart_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / cap.CLAUDE_AGENT_DIR / "codex-advisor.md").unlink()
    assert "unpaired" in _kinds(root)


def test_a_name_disagreeing_with_the_stem_fails(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        toml=_GOOD_TOML.replace('name = "codex-advisor"', 'name = "codex-other"'),
    )
    assert "name-mismatch" in _kinds(root)


def test_a_missing_effort_declaration_fails(tmp_path: Path) -> None:
    """A missing effort line is the silent-downgrade regression.

    Drop it and codex resolves the effort from `~/.codex/config.toml`, running
    at medium — the exact downgrade this lane exists to close.
    """
    root = _tree(
        tmp_path,
        toml="\n".join(
            line
            for line in _GOOD_TOML.splitlines(keepends=True)
            if not line.startswith("model_reasoning_effort")
        ),
    )
    assert "effort" in _kinds(root)


def test_a_downgraded_effort_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path, toml=_GOOD_TOML.replace('"xhigh"', '"medium"'))
    assert "effort" in _kinds(root)


def test_unparsable_toml_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path, toml="name = \nbroken\n")
    assert "unparsable" in _kinds(root)


def test_an_empty_tree_fails_loud_rather_than_passing_vacuously(tmp_path: Path) -> None:
    (tmp_path / cap.CLAUDE_AGENT_DIR).mkdir(parents=True)
    (tmp_path / cap.CODEX_AGENT_DIR).mkdir(parents=True)
    assert _kinds(tmp_path) == ["empty"]


def test_exported_mirrors_without_the_codex_prefix_are_out_of_scope(
    tmp_path: Path,
) -> None:
    """The Codex-app exported mirrors are out of scope.

    They share the directory but carry no `codex-` prefix and stay gitignored.
    Policing them would fail on content we do not author.
    """
    root = _tree(tmp_path)
    (root / cap.CODEX_AGENT_DIR / "claude-code-expert.toml").write_text(
        'name = "wrong"\nx = "Codex Code / .Codex/ / Codex mcp add"\n'
    )
    assert cap.find_violations(root) == []


# ── real-repo guards ─────────────────────────────────────────────────────────


def test_the_real_repo_passes() -> None:
    assert cap.find_violations(REPO_ROOT) == []


def test_the_four_shipped_lanes_are_all_present() -> None:
    shipped = {
        p.stem
        for p in (REPO_ROOT / cap.CODEX_AGENT_DIR).iterdir()
        if p.suffix == ".toml" and p.name.startswith(cap.STEM_PREFIX)
    }
    assert shipped == {
        "codex-advisor",
        "codex-adversarial-critic",
        "codex-staleness-auditor",
        "codex-claude-code-expert",
    }


def test_the_cli_subcommand_is_wired_end_to_end() -> None:
    res = subprocess.run(
        ["uv", "run", "--project", "python", "dotfiles-setup", "codex-agent-parity"],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
        timeout=120,
    )
    assert res.returncode == 0, res.stderr


def test_the_hk_step_and_mise_task_stay_wired() -> None:
    hk = (REPO_ROOT / "hk.pkl").read_text()
    assert '["codex_agent_parity"]' in hk
    assert "dotfiles-setup codex-agent-parity" in hk
    assert "[tasks.codex-agent-parity]" in (REPO_ROOT / "mise.toml").read_text()


def _exclude_entries() -> list[str]:
    """The real `excludePaths` list entries, comments excluded.

    Anchored on purpose: the block's own comment QUOTES the negation form that
    does not work, so a bare substring check over the file would convict the
    documentation of being the defect it documents.
    """
    lines = (REPO_ROOT / "hk-common.pkl").read_text().splitlines()
    start = next(
        i
        for i, line in enumerate(lines)
        if "excludePaths: List<String> = List(" in line
    )
    end = next(i for i, line in enumerate(lines[start:], start) if line.strip() == ")")
    return [
        line.strip().rstrip(",").strip('"')
        for line in lines[start + 1 : end]
        if line.strip().startswith('"')
    ]


def test_hk_can_actually_see_the_tracked_codex_tomls() -> None:
    """The exclusion must not blind hk to the tracked lanes.

    The blanket `.codex/**` entry did: a planted misspelling passed
    `mise run lint` at rc=0 while `typos` on the same file returned rc=2. A
    `!`-negation does NOT fix it — hk's exclude does not honour one, measured on
    the same planted word — so the exclusion is enumerated instead.
    """
    entries = _exclude_entries()
    assert ".codex/**" not in entries
    assert not [e for e in entries if e.startswith("!")]
    assert ".codex/config.toml" in entries
    assert ".codex/hooks.json" in entries
    # Nothing may match the tracked hand-authored lanes.
    assert not [e for e in entries if e.startswith(".codex/agents/")]


def test_the_exclude_parser_is_armed() -> None:
    """`_exclude_entries` must actually find the list.

    Control arm: it must pick up entries the file certainly has. A parser
    returning an empty list would make every assertion above pass vacuously.
    """
    entries = _exclude_entries()
    assert ".agent/**" in entries
    assert "docs/research/kb/**" in entries
    assert len(entries) > 5
