# Copyright (c) 2026 Raymond Manaloto
"""Tests for the codex agent lane parity gate (dotfiles_setup.codex_agent_parity).

Three layers: isolated logic tests against a synthetic tree (so every failure
kind is exercised without mutating the real one), the PRODUCTION entry point
driven in the failing direction (`find_violations` being well covered says
nothing about the seam the hk step actually runs), and real-repo guards.

Every failure-kind test mutates the fixture in the shape the REAL regression
would take — a tracked toml overwritten by the exporter, a counterpart file
deleted, a pin dropped — not a rename, which leaves the original text as a
substring and can make a substring check a no-op.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import codex_agent_parity as cap

REPO_ROOT = Path(__file__).parent.parent

# The four Codex Desktop app EXPORTS. Gitignored, so absent from a fresh clone.
EXPORTED_MIRRORS = (
    "adversarial-critic",
    "claude-code-expert",
    "staleness-auditor",
    "dockerfile-reviewer",
)

# TOML multi-line LITERAL delimiter, built rather than escaped: the bodies
# carry backslash line continuations a basic string would eat as escapes.
_TQ = "'" * 3

_GOOD_TOML = f"""# {cap.SENTINEL} (#884)
name = "codex-advisor"
description = "A second-opinion advisor."
model_reasoning_effort = "xhigh"
developer_instructions = {_TQ}
You advise. Read `.claude/agents/codex-advisor.md` for the wrapper half.
Claude Code is the harness; `claude mcp add` is the command.
{_TQ}
"""

_GOOD_MD = """---
name: codex-advisor
model: haiku
description: An advisor.
tools: Bash, Read, Grep, Glob, Write
---

Shell out with both flags explicit:

    cat prompt.md | codex exec --ephemeral --sandbox read-only \\
      --model gpt-5.6-sol \\
      -c model_reasoning_effort="xhigh" -

## Hard limits

- **Never substitute your own reasoning for a failed codex call.** Report the
  failure instead.
"""


def _tree(
    root: Path,
    *,
    toml: str = _GOOD_TOML,
    md: str = _GOOD_MD,
    stem: str = "codex-advisor",
) -> Path:
    """Build a minimal well-formed two-surface fixture and return its root."""
    (root / cap.CLAUDE_AGENT_DIR).mkdir(parents=True, exist_ok=True)
    (root / cap.CODEX_AGENT_DIR).mkdir(parents=True, exist_ok=True)
    (root / cap.CLAUDE_AGENT_DIR / f"{stem}.md").write_text(md)
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


# ── G1: the sentinel is the primary check ────────────────────────────────────


def test_a_missing_sentinel_fails(tmp_path: Path) -> None:
    """The real regression: the exporter overwrites a tracked file wholesale.

    Whatever strings that export happens to contain, our own line is gone.
    """
    root = _tree(tmp_path, toml=_GOOD_TOML.replace(f"# {cap.SENTINEL} (#884)\n", ""))
    assert "sentinel-missing" in _kinds(root)


def test_the_sentinel_is_absent_from_every_exported_mirror() -> None:
    """The sentinel only discriminates while the exporter cannot emit it.

    Pinned so a later tidy-up that makes the sentinel something the export also
    produces fails here immediately rather than silently neutering the gate.
    """
    present = [
        name
        for name in EXPORTED_MIRRORS
        if (p := REPO_ROOT / cap.CODEX_AGENT_DIR / f"{name}.toml").is_file()
        and cap.SENTINEL in p.read_text(encoding="utf-8", errors="replace")
    ]
    assert present == []


def test_real_exporter_output_in_scope_fails(tmp_path: Path) -> None:
    """The decisive arm: real exporter output, in an in-scope path, must fail.

    `.codex/agents/staleness-auditor.toml` is a live corrupted export — it says
    "does Codex Code do X" and `docs/Codex`. The FIRST version of this gate
    scored it 0 on all three of its markers and returned rc=0, which is the
    defect this round exists to close. The mirrors are gitignored, so this skips
    on a clone that has none rather than passing vacuously.
    """
    src = REPO_ROOT / cap.CODEX_AGENT_DIR / "staleness-auditor.toml"
    if not src.is_file():
        pytest.skip("the Codex-app exported mirrors are gitignored and absent here")
    raw = src.read_text(encoding="utf-8", errors="replace")
    if "Codex" not in raw:
        pytest.skip("this machine's mirror is not corrupted; nothing to detect")

    root = _tree(tmp_path, toml=raw)
    kinds = _kinds(root)
    assert "sentinel-missing" in kinds
    assert "corrupted" in kinds
    assert cap.codex_agent_parity_main(root) == 1


def test_a_line_wrap_cannot_hide_a_marker(tmp_path: Path) -> None:
    """Raw scanning misses `Codex Code` split across a newline; flattening does not.

    This is why the markers are secondary: any multi-word content marker is
    defeatable by reflow, whoever owns the words.
    """
    wrapped = _GOOD_TOML.replace("You advise.", "Does Codex\nCode do X?")
    assert "Codex Code" not in wrapped
    assert "corrupted" in _kinds(_tree(tmp_path, toml=wrapped))


def test_each_corruption_marker_is_detected_on_its_own(tmp_path: Path) -> None:
    for i, marker in enumerate(cap.CORRUPTION_MARKERS):
        root = tmp_path / f"case{i}"
        root.mkdir()
        _tree(root, toml=_GOOD_TOML.replace("You advise.", f"You {marker} advise."))
        assert "corrupted" in _kinds(root), marker


# ── the other toml failure arms ──────────────────────────────────────────────


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
        tmp_path, toml=_GOOD_TOML.replace('name = "codex-advisor"', 'name = "codex-x"')
    )
    assert "name-mismatch" in _kinds(root)


def test_a_missing_effort_declaration_fails(tmp_path: Path) -> None:
    """A missing effort line is the silent-downgrade regression.

    Drop it and codex resolves the effort from `~/.codex/config.toml`, running
    at medium — the exact downgrade this lane exists to close.
    """
    root = _tree(
        tmp_path,
        toml="".join(
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
    root = _tree(tmp_path, toml=f"# {cap.SENTINEL}\nname = \nbroken\n")
    assert "unparsable" in _kinds(root)


def test_undecodable_bytes_are_reported_as_a_violation(tmp_path: Path) -> None:
    """G7: a non-UTF-8 toml must name the file, not raise UnicodeDecodeError.

    Undecodable bytes are themselves evidence something overwrote the file, so
    the gate has to say WHICH file rather than dying with an unexplained
    command failure.
    """
    root = _tree(tmp_path)
    (root / cap.CODEX_AGENT_DIR / "codex-advisor.toml").write_bytes(b"\xff\xfe\x00bad")
    kinds = _kinds(root)
    assert "sentinel-missing" in kinds
    assert cap.codex_agent_parity_main(root) == 1


def test_an_empty_tree_fails_loud_rather_than_passing_vacuously(
    tmp_path: Path,
) -> None:
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


# ── G3: the `.md` half ───────────────────────────────────────────────────────


def test_an_md_without_frontmatter_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path, md="no frontmatter here\n")
    assert "md-no-frontmatter" in _kinds(root)


def test_an_md_name_disagreeing_with_the_stem_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path, md=_GOOD_MD.replace("name: codex-advisor", "name: codex-x"))
    assert "md-name-mismatch" in _kinds(root)


def test_an_md_without_a_model_pin_fails(tmp_path: Path) -> None:
    """An unpinned wrapper runs its clerical turns on the session default."""
    root = _tree(tmp_path, md=_GOOD_MD.replace("model: haiku\n", ""))
    assert "md-no-model" in _kinds(root)


def test_the_md_model_value_is_deliberately_not_pinned(tmp_path: Path) -> None:
    """Control arm for the rule above: which model is a tuning decision.

    A check that also pinned the value would fail the moment someone re-tuned a
    lane, which is not a defect.
    """
    root = _tree(tmp_path, md=_GOOD_MD.replace("model: haiku", "model: sonnet"))
    assert cap.find_violations(root) == []


def test_an_md_missing_the_model_flag_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path, md=_GOOD_MD.replace("--model gpt-5.6-sol", "--model auto"))
    assert "md-missing-marker" in _kinds(root)


def test_an_md_missing_the_effort_flag_fails(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        md=_GOOD_MD.replace('model_reasoning_effort="xhigh"', "model_effort=high"),
    )
    assert "md-missing-marker" in _kinds(root)


def test_an_md_missing_the_no_substitute_prohibition_fails(tmp_path: Path) -> None:
    """The realistic regression: someone trims the Hard limits section.

    Deleting the wiring line is what a real edit looks like; renaming a symbol
    would leave the original as a substring and prove nothing.
    """
    root = _tree(
        tmp_path,
        md=_GOOD_MD.replace(
            "- **Never substitute your own reasoning for a failed codex call.** "
            "Report the\n  failure instead.\n",
            "- Report failures.\n",
        ),
    )
    assert "md-missing-marker" in _kinds(root)


def test_an_md_marker_survives_being_reflowed(tmp_path: Path) -> None:
    """Control arm: md markers match flattened text, so a rewrap is not a break."""
    reflowed = _GOOD_MD.replace(
        "- **Never substitute your own reasoning for a failed codex call.** "
        "Report the\n"
        "  failure instead.\n",
        "- **Never substitute your own reasoning for a failed\n"
        "  codex call.** Report the failure instead.\n",
    )
    assert "Never substitute your own reasoning for a failed codex call" not in reflowed
    assert cap.find_violations(_tree(tmp_path, md=reflowed)) == []


# ── G2: the PRODUCTION entry point, in the failing direction ─────────────────


def test_the_entry_point_returns_nonzero_on_a_violation(tmp_path: Path) -> None:
    """`codex_agent_parity_main` itself must return 1, not just find violations.

    The seam between `find_violations` and the CLI is what the hk step runs, and
    it was untested: stubbing this function to `return 0` left the whole suite
    green.
    """
    root = _tree(tmp_path)
    (root / cap.CODEX_AGENT_DIR / "codex-advisor.toml").unlink()
    assert cap.codex_agent_parity_main(root) == 1


def test_the_entry_point_returns_zero_on_a_clean_tree(tmp_path: Path) -> None:
    assert cap.codex_agent_parity_main(_tree(tmp_path)) == 0


def test_the_cli_returns_nonzero_on_a_violating_tree(tmp_path: Path) -> None:
    """The whole chain — main.py dispatch, entry point, logic — through argv.

    Driven against a fixture repo so a real regression in the dispatch table
    (a missing subparser, a lambda that drops the exit code) is caught here and
    not only by the hk step failing to protect anything.
    """
    root = _tree(tmp_path)
    (root / cap.CLAUDE_AGENT_DIR / "codex-advisor.md").unlink()
    res = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; sys.path.insert(0, "
                f"{str(REPO_ROOT / 'python' / 'src')!r}); "
                "from dotfiles_setup.codex_agent_parity import "
                "codex_agent_parity_main; "
                "from pathlib import Path; "
                f"sys.exit(codex_agent_parity_main(Path({str(root)!r})))"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert res.returncode == 1, res.stdout + res.stderr


# ── real-repo guards ─────────────────────────────────────────────────────────


def test_the_real_repo_passes() -> None:
    assert cap.find_violations(REPO_ROOT) == []


def test_the_shipped_lanes_are_all_present() -> None:
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
        "codex-operator",
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
