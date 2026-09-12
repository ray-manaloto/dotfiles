# Copyright (c) 2026 Raymond Manaloto
"""Tests for the codex astra-lane generator (dotfiles_setup.codex_lane_mirror).

The generator exists so ~270 lines of shared lane body are not maintained twice.
Its whole value is the `--check` arm, so every test here drives that arm in the
FAILING direction as well as the passing one — a mirror check verified only on a
clean tree is decoration (`.claude/rules/probes-need-a-control-arm.md` rule 2).

Each mutation is the shape the real regression takes: an astra lane hand-edited
to a different model, a generated file deleted, a sol source retired while its
astra twin lingers. None is a rename, which would leave the original text as a
substring and let a substring check pass on a broken tree.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import codex_lane_mirror as clm

_MD = """---
name: codex-sol-advisor
model: haiku
---

Runs on `gpt-5.6-sol` at xhigh.

    --model gpt-5.6-sol \\
"""

_TOML = """# dotfiles-hand-authored-codex-lane (#884)
name = "codex-sol-advisor"
description = "Runs on codex (gpt-5.6-sol)."
"""


def _tree(root: Path) -> None:
    """A minimal repo with one authored sol lane and no astra twin yet."""
    (root / clm.CLAUDE_AGENT_DIR).mkdir(parents=True)
    (root / clm.CODEX_AGENT_DIR).mkdir(parents=True)
    (root / clm.CLAUDE_AGENT_DIR / "codex-sol-advisor.md").write_text(_MD)
    (root / clm.CODEX_AGENT_DIR / "codex-sol-advisor.toml").write_text(_TOML)


def test_render_md_substitutes_name_and_model_and_stamps() -> None:
    out = clm.render_md(_MD)
    assert "name: codex-astra-advisor" in out
    assert "--model gpt-6-astra" in out
    # The ONLY sol mention left may be the notice naming its own source.
    assert "gpt-5.6-sol" not in out
    assert clm.GENERATED_NOTICE in out
    # The frontmatter must still open at byte 0 or the agent loader skips it.
    assert out.startswith("---\n")


def test_render_toml_substitutes_and_keeps_the_sentinel() -> None:
    out = clm.render_toml(_TOML)
    assert 'name = "codex-astra-advisor"' in out
    assert "gpt-6-astra" in out
    assert "gpt-5.6-sol" not in out
    # The parity gate's primary check must survive generation.
    assert "dotfiles-hand-authored-codex-lane" in out
    assert out.startswith("# " + clm.GENERATED_NOTICE)


def test_check_fails_when_the_astra_twin_is_missing(tmp_path: Path) -> None:
    _tree(tmp_path)
    findings = clm.find_drift(tmp_path)
    assert len(findings) == 2
    assert all("missing" in f for f in findings)


def test_write_then_check_passes(tmp_path: Path) -> None:
    _tree(tmp_path)
    written = clm.write_mirror(tmp_path)
    assert len(written) == 2
    assert clm.find_drift(tmp_path) == []


def test_check_fails_when_an_astra_lane_is_hand_edited(tmp_path: Path) -> None:
    """The regression the split exists to prevent: astra silently pinned to sol."""
    _tree(tmp_path)
    clm.write_mirror(tmp_path)
    twin = tmp_path / clm.CLAUDE_AGENT_DIR / "codex-astra-advisor.md"
    twin.write_text(twin.read_text().replace("gpt-6-astra", "gpt-5.6-sol"))
    findings = clm.find_drift(tmp_path)
    assert len(findings) == 1
    assert "drifted from" in findings[0]
    # And regenerating restores it, so the gate is not merely loud.
    clm.write_mirror(tmp_path)
    assert clm.find_drift(tmp_path) == []


def test_check_fails_on_a_stale_astra_lane_whose_source_is_gone(
    tmp_path: Path,
) -> None:
    """A retired role must not leave its generated twin behind unnoticed."""
    _tree(tmp_path)
    clm.write_mirror(tmp_path)
    (tmp_path / clm.CLAUDE_AGENT_DIR / "codex-sol-advisor.md").unlink()
    (tmp_path / clm.CODEX_AGENT_DIR / "codex-sol-advisor.toml").unlink()
    findings = clm.find_drift(tmp_path)
    assert len(findings) == 2
    assert all("stale" in f for f in findings)


def test_main_check_exit_codes(tmp_path: Path) -> None:
    _tree(tmp_path)
    assert clm.codex_lane_mirror_main(tmp_path, check=True) == 1
    assert clm.codex_lane_mirror_main(tmp_path) == 0
    assert clm.codex_lane_mirror_main(tmp_path, check=True) == 0


def test_the_real_repo_mirror_is_current() -> None:
    """The tracked tree must already satisfy the gate CI will run."""
    root = Path(__file__).parent.parent
    assert clm.find_drift(root) == []
    # `find_drift == []` is vacuously true over an empty role set, so pin the
    # roles themselves rather than a count. Naming them means adding a role
    # fails HERE with the role's name, instead of failing on a magic number
    # whose only fix is to bump it — and a role silently disappearing is caught
    # in the same assertion.
    assert clm.roles(root) == [
        "adversarial-critic",
        "advisor",
        "claude-code-expert",
        "implementer",
        "operator",
        "staleness-auditor",
    ]
