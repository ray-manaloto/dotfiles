"""Tests for the cross-repo parity gate (dotfiles_setup.parity, #354 PR 1).

The defect this gate exists for is one level up from the bugs that opened
#354: both repos' docs claim the same orchestration doctrine, and only one
repo's *config* carries it. A declaration in two places that is observed in
one is the same shape as a declaration observed in none — you just cannot see
it from inside either repo.

Every case pins its FAIL direction next to its pass
(`.claude/rules/probes-need-a-control-arm.md`). The two that matter most are
the ones a naive implementation gets backwards: a plugin present-but-`false`
must count as ABSENT, and a run that could not see the other repo must not
report green.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from dotfiles_setup import parity

_ROOT = Path(__file__).parent.parent

_PLUGIN = "fable-orchestrator@fable-orchestrator"
_TRIGGER = "- fable-orchestrator: implementation lane = codex"


def _repo(root: Path, *, plugins: dict[str, bool], claude_md: str = "") -> Path:
    (root / ".claude").mkdir(parents=True, exist_ok=True)
    (root / ".claude" / "settings.json").write_text(
        json.dumps({"enabledPlugins": plugins})
    )
    (root / ".claude" / "CLAUDE.md").write_text(claude_md)
    return root


def _shared(
    *, plugins: tuple[str, ...] = (), lines: tuple[str, ...] = ()
) -> parity.Shared:
    return parity.Shared(plugins=plugins, lines=lines)


# ---------------------------------------------------------------------------
# The declared set is data, not code
# ---------------------------------------------------------------------------


def test_the_repo_declares_a_non_empty_shared_set() -> None:
    """An empty `parity.toml` is a gate that can only pass.

    This is the whole failure mode of #354 reproduced inside its own fix: a
    parity file with nothing in it runs, exits 0, and observes nothing.
    """
    shared = parity.load_shared(_ROOT / "parity.toml")
    assert shared.plugins
    assert shared.lines


def test_the_declared_set_matches_what_dotfiles_actually_carries() -> None:
    """The set must describe THIS repo truthfully, or it is fiction.

    Independent source of truth: the real `settings.json` and `.claude/CLAUDE.md`
    on disk, not anything the parity module computes.
    """
    shared = parity.load_shared(_ROOT / "parity.toml")
    enabled = parity.enabled_plugins(_ROOT)
    assert set(shared.plugins) <= enabled
    text = (_ROOT / ".claude" / "CLAUDE.md").read_text()
    present = {" ".join(one.split()) for one in text.splitlines()}
    for line in shared.lines:
        assert " ".join(line.split()) in present, line


# ---------------------------------------------------------------------------
# Plugin parity
# ---------------------------------------------------------------------------


def test_a_plugin_missing_from_one_repo_is_a_gap(tmp_path: Path) -> None:
    a = _repo(tmp_path / "a", plugins={_PLUGIN: True})
    b = _repo(tmp_path / "b", plugins={})
    gaps = parity.find_parity_gaps({"a": a, "b": b}, _shared(plugins=(_PLUGIN,)))
    assert [(g.repo, g.ref) for g in gaps] == [("b", _PLUGIN)]


def test_a_plugin_present_in_both_is_not_a_gap(tmp_path: Path) -> None:
    """Control arm: without it, an always-fail implementation passes above."""
    a = _repo(tmp_path / "a", plugins={_PLUGIN: True})
    b = _repo(tmp_path / "b", plugins={_PLUGIN: True})
    assert parity.find_parity_gaps({"a": a, "b": b}, _shared(plugins=(_PLUGIN,))) == []


def test_a_plugin_declared_false_counts_as_absent(tmp_path: Path) -> None:
    """`"plugin": false` is the inert declaration in its purest form.

    The key is present, so any check that asks "is it listed?" reports green
    while the plugin is switched off. Enablement is the value, not the key.
    """
    a = _repo(tmp_path / "a", plugins={_PLUGIN: True})
    b = _repo(tmp_path / "b", plugins={_PLUGIN: False})
    gaps = parity.find_parity_gaps({"a": a, "b": b}, _shared(plugins=(_PLUGIN,)))
    assert [(g.repo, g.ref) for g in gaps] == [("b", _PLUGIN)]


def test_a_repo_with_no_settings_file_is_a_gap_not_a_pass(tmp_path: Path) -> None:
    """A settings file we cannot read must never resolve to "it is fine"."""
    a = _repo(tmp_path / "a", plugins={_PLUGIN: True})
    b = tmp_path / "b"
    b.mkdir()
    gaps = parity.find_parity_gaps({"a": a, "b": b}, _shared(plugins=(_PLUGIN,)))
    assert [g.repo for g in gaps] == ["b"]


# ---------------------------------------------------------------------------
# Line parity — the trigger itself
# ---------------------------------------------------------------------------


def test_a_missing_trigger_line_is_a_gap(tmp_path: Path) -> None:
    """THE original bug, now visible from the other repo as well."""
    a = _repo(tmp_path / "a", plugins={}, claude_md=f"{_TRIGGER}\n")
    b = _repo(tmp_path / "b", plugins={}, claude_md="nothing here\n")
    gaps = parity.find_parity_gaps({"a": a, "b": b}, _shared(lines=(_TRIGGER,)))
    assert [(g.repo, g.ref) for g in gaps] == [("b", _TRIGGER)]


def test_a_narrated_trigger_line_is_still_a_gap(tmp_path: Path) -> None:
    """A doc that TALKS ABOUT the trigger has not armed it.

    This is why parity matches whole lines rather than substrings — the repo
    spent an unknown number of sessions in exactly this state.
    """
    a = _repo(tmp_path / "a", plugins={}, claude_md=f"{_TRIGGER}\n")
    b = _repo(tmp_path / "b", plugins={}, claude_md=f"The mode line is `{_TRIGGER}`.\n")
    gaps = parity.find_parity_gaps({"a": a, "b": b}, _shared(lines=(_TRIGGER,)))
    assert [g.repo for g in gaps] == ["b"]


def test_line_matching_tolerates_reindentation(tmp_path: Path) -> None:
    """Control arm for the above: whitespace is normalised, words are not."""
    a = _repo(tmp_path / "a", plugins={}, claude_md=f"  {_TRIGGER}  \n")
    b = _repo(tmp_path / "b", plugins={}, claude_md=f"{_TRIGGER}\n")
    assert parity.find_parity_gaps({"a": a, "b": b}, _shared(lines=(_TRIGGER,))) == []


# ---------------------------------------------------------------------------
# Reachability — a gate that cannot see the other repo must say so
# ---------------------------------------------------------------------------


def test_missing_sibling_repo_skips_locally(tmp_path: Path) -> None:
    """A dev box without the sibling clone gets a loud SKIP, not a fake pass."""
    rc, report = parity.run(_ROOT, kb_path=tmp_path / "nope", in_ci=False)
    assert rc == 0
    assert "SKIP" in report


def test_missing_sibling_repo_fails_in_ci(tmp_path: Path) -> None:
    """In CI the checkout is the gate's own wiring, so absence is a defect.

    If the `actions/checkout` of knowledge-base is ever dropped or renamed,
    a skip-on-absent gate would go quietly green forever — the inert trigger
    reproduced one more level up. CI is the one place "not found" is provably
    a bug rather than a dev box's business.
    """
    rc, report = parity.run(_ROOT, kb_path=tmp_path / "nope", in_ci=True)
    assert rc == 1
    assert "SKIP" not in report


def test_resolve_prefers_the_explicit_path_then_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KB_REPO_PATH", str(tmp_path / "from-env"))
    assert parity.resolve_kb_path(tmp_path / "explicit") == tmp_path / "explicit"
    assert parity.resolve_kb_path(None) == tmp_path / "from-env"
    monkeypatch.delenv("KB_REPO_PATH")
    assert parity.resolve_kb_path(None) == (_ROOT.parent / "knowledge-base")


# ---------------------------------------------------------------------------
# The advisory half — everything NOT gated still gets reported
# ---------------------------------------------------------------------------


def test_divergence_report_names_what_is_not_gated(tmp_path: Path) -> None:
    """Ray's decision was doctrine-core gated + the rest REPORTED.

    A narrow gated set is only honest if the difference it declines to gate is
    still visible. Silent truncation reads as "covered everything".
    """
    a = _repo(tmp_path / "a", plugins={_PLUGIN: True, "extra@x": True})
    b = _repo(tmp_path / "b", plugins={_PLUGIN: True})
    report = parity.divergence_report({"a": a, "b": b})
    assert "extra@x" in report


def test_the_live_repos_pass_the_gated_set() -> None:
    """The gate must be green on the real tree it ships with.

    Skips when the sibling clone is absent — the FAIL direction of this exact
    condition is pinned by `test_missing_sibling_repo_fails_in_ci` above, so
    the skip here cannot hide a broken gate.
    """
    kb = parity.resolve_kb_path(None)
    if not (kb / ".claude").is_dir():
        pytest.skip("knowledge-base clone not present")
    shared = parity.load_shared(_ROOT / "parity.toml")
    gaps = parity.find_parity_gaps({"dotfiles": _ROOT, "knowledge-base": kb}, shared)
    assert gaps == [], [f"{g.repo}: missing {g.kind} {g.ref}" for g in gaps]
