# Copyright (c) 2026 Raymond Manaloto
"""Tests for this repo's eval cases (dotfiles_setup.eval_cases, #354 PR 2/PR 3).

The runner (`kb_setup.evals`) is tested in the knowledge-base repo, where it
lives. What is ours to test is the CASES — and specifically that every gated one
carries a control arm that really fails, because that is the property the whole
harness rests on and the one an author adding a case will forget.

Catching it here rather than only at `mise run eval` time matters: the runner
reports UNARMED at run time, but a test says so at commit time, which is the
difference between a red gate and a red gate you understand.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import eval_cases, hook_guard
from kb_setup import evals

_ROOT = Path(__file__).parent.parent.absolute()


def _cases() -> list[evals.Case]:
    return eval_cases.cases(_ROOT)


def test_every_gated_case_declares_a_control_arm() -> None:
    """Design principle 1, checked statically."""
    naked = [c.name for c in _cases() if c.gated and c.control is None]
    assert naked == [], f"gated cases with no control arm: {naked}"


def test_every_control_arm_actually_fails() -> None:
    """The load-bearing half — and the one that is easy to get wrong.

    A case can carry a control arm that is simply pointed at the wrong thing and
    comes back SKIP or PASS; then the case LOOKS armed and is still a coin with
    one face. This ran red on the first attempt in the sibling repo, because the
    obvious control for the graph canary (a graph path that does not exist)
    returns SKIP by design.
    """
    for case in _cases():
        if not case.gated or case.control is None:
            continue
        outcome = case.control()
        assert outcome.verdict is evals.Verdict.FAIL, (
            f"{case.name}: control arm returned {outcome.verdict.name}, not FAIL "
            f"— the probe cannot be shown to discriminate ({outcome.detail})"
        )


def test_the_expected_cases_are_declared() -> None:
    """A case silently disappearing is the inert declaration one level up."""
    assert {c.name for c in _cases()} == {
        "tier1.lanes-declared-or-degraded",
        "tier1.shared-engine-resolves",
        "tier1.cc-subcommand-dispatches",
        "tier1.graph-answers",
        "tier1.lane-health",
        "tier2.guard-fixtures",
    }


def test_only_the_doctor_case_is_live() -> None:
    """`doctor.sh` has NO offline mode — it is the live half, entirely.

    It takes no flags and fires a real API call per installed CLI, so it can
    never join the free gated tier. If another case is ever marked live, the
    offline gate gets cheaper by doing less, which is the wrong direction.
    """
    assert [c.name for c in _cases() if c.live] == ["tier1.lane-health"]


def test_grok_is_declared_and_the_case_still_passes() -> None:
    """`grok` is named in the doctrine and is NOT installed. That is correct.

    "Availability is discovered at run time, not declared" — so the case must
    assert the DEGRADATION PATH is written down, not that grok exists. A case
    that failed here would be pressure to either install a CLI we do not want or
    delete a lane the doctrine legitimately names.
    """
    assert "grok" in eval_cases.DECLARED_LANES
    outcome = evals.declared_lanes_reconcile(
        eval_cases.DECLARED_LANES,
        fallback_doc=_ROOT / ".claude" / "CLAUDE.md",
        fallback_tokens=eval_cases.FALLBACK_TOKENS,
    )
    assert outcome.verdict is evals.Verdict.PASS


def test_the_fallback_tokens_are_actually_present_in_the_doctrine_doc() -> None:
    """Independent source of truth: the real `.claude/CLAUDE.md` on disk.

    Without this the case above could pass on tokens chosen to match whatever
    the doc happens to say — a tautology. Read the file directly.
    """
    text = (_ROOT / ".claude" / "CLAUDE.md").read_text()
    for token in eval_cases.FALLBACK_TOKENS:
        assert token in text, token


def test_the_shared_engine_probe_names_what_is_missing() -> None:
    """Principle 8: report the status seen, not a prose summary.

    Reached through the case's own declared control arm rather than the private
    helper, so this test exercises exactly what the runner will call.
    """
    case = next(c for c in _cases() if c.name == "tier1.shared-engine-resolves")
    assert case.control is not None
    outcome = case.control()
    assert outcome.verdict is evals.Verdict.FAIL
    assert "kb_setup.definitely_not_a_module" in outcome.detail


def test_the_launcher_marker_is_what_the_pinned_cli_really_prints() -> None:
    """Independent source of truth: drive the real pinned CLI and read it.

    A marker constant chosen to match the probe's own expectation is a
    tautology. This runs `kb-setup cc` — the exact command `mise run cc` runs,
    minus its arguments — and asserts the marker appears in the real output. If
    the launcher's refusal wording changes upstream, this goes red here rather
    than the case quietly going inert.
    """
    exe = shutil.which("kb-setup")
    assert exe is not None, "kb-setup must resolve — `mise run cc` invokes it"
    rc, out = evals.run_command([exe, "cc"])
    assert eval_cases.LAUNCHER_REACHED_MARKER in out, f"rc={rc}: {out}"


def test_rc_alone_cannot_discriminate_the_launcher_probe() -> None:
    """Both directions exit 2 — which is *why* the probe grades the marker.

    #391's failure (`unknown command 'cc'`) and the handler's own
    missing-argument refusal are indistinguishable by exit code. A later edit
    that "simplified" the probe to `rc == 2` would pass in both directions — a
    coin with one face. Pinning the equality here makes that visibly wrong.
    """
    exe = shutil.which("kb-setup")
    assert exe is not None
    reached_rc, _ = evals.run_command([exe, "cc"])
    unknown_rc, unknown_out = evals.run_command([exe, "no-such-subcommand-xyz"])
    assert reached_rc == unknown_rc
    assert eval_cases.LAUNCHER_REACHED_MARKER not in unknown_out


def test_the_graph_case_declares_an_environment_precondition() -> None:
    """Graphify is HOST-ONLY here, so the canary cannot run in the devcontainer.

    Without this the case failed in-container with `rc=-2, No such file or
    directory: 'graphify'` and took the whole postCreate smoke down — caught by
    `sync-full`, which is the reason this test exists rather than a comment.
    """
    case = next(c for c in _cases() if c.name == "tier1.graph-answers")
    assert case.precondition is not None


def test_the_precondition_skips_when_graphify_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both arms of the environment gate, since it decides whether a gate runs.

    A precondition that could only ever return None would silently reintroduce
    the in-container failure; one that could only ever skip would disable the
    case everywhere, which is worse than not having it.
    """
    case = next(c for c in _cases() if c.name == "tier1.graph-answers")
    assert case.precondition is not None

    monkeypatch.setattr(eval_cases.shutil, "which", lambda _name: None)
    gate = case.precondition()
    assert gate is not None
    assert gate.verdict is evals.Verdict.SKIP
    assert "host-only" in gate.detail

    monkeypatch.setattr(eval_cases.shutil, "which", lambda _name: "/usr/bin/graphify")
    assert case.precondition() is None


# --- the tier-2 fixture corpus ------------------------------------------------


def _fixtures(expected: evals.Decision) -> set[str]:
    return {f.command for f in eval_cases.GUARD_FIXTURES if f.expected is expected}


def test_the_guard_corpus_carries_both_halves() -> None:
    """Stated at commit time as well as enforced in the engine at run time.

    The must-ALLOW half is not symmetry for its own sake: bypasses of this guard
    are all-time ZERO while 2 of its 3 recorded denials were false positives, so
    a deny-only corpus would grade only the direction that has never failed.
    """
    assert _fixtures(evals.Decision.DENY), "no must-DENY rows"
    assert _fixtures(evals.Decision.ALLOW), "no must-ALLOW rows"


def test_every_fixture_row_says_what_it_defends() -> None:
    """A row whose `why` is empty is a string nobody can maintain."""
    silent = [f.command for f in eval_cases.GUARD_FIXTURES if not f.why.strip()]
    assert silent == [], f"fixture rows with no stated reason: {silent}"


def test_no_duplicate_fixture_commands() -> None:
    """A duplicated row inflates the corpus without adding coverage."""
    commands = [f.command for f in eval_cases.GUARD_FIXTURES]
    assert len(commands) == len(set(commands))


def test_the_only_measured_defect_class_is_pinned_as_an_allow_row() -> None:
    """#265 verbatim: a `|` inside a quoted regex is not a shell separator.

    Pinned by content rather than by count, because a future edit that drops it
    would otherwise silently remove the row standing on the only defect this
    guard has ever actually had.
    """
    assert 'grep -iE "npx|devcontainer up|gh pr create" docs/' in _fixtures(
        evals.Decision.ALLOW
    )


def test_the_repo_aware_gh_rules_are_pinned_in_all_three_directions() -> None:
    """Dotfiles denies, knowledge-base denies, any OTHER repo allows.

    All three are load-bearing and only the third is obvious in hindsight: the
    unconditional rules that preceded them redirected a KB PR to `mise run
    land`, a dotfiles task that cannot do the job, and KB PRs #1 and #2 had to
    be merged by hand (#349). A deny whose redirect target cannot perform the
    redirected action is not enforcement, it is an outage.
    """
    deny, allow = _fixtures(evals.Decision.DENY), _fixtures(evals.Decision.ALLOW)
    assert "gh pr create --fill" in deny
    assert "gh pr create -R ray-manaloto/knowledge-base --fill" in deny
    assert "gh pr create -R some-other/repo --fill" in allow


def test_every_denied_fixture_names_a_redirect() -> None:
    """A deny with no redirect is a wall, not a guard.

    Reached through the real `decide`, so this also proves every deny row still
    matches a rule at all — the reason string comes from the matched rule.
    """
    silent = [
        f.command
        for f in eval_cases.GUARD_FIXTURES
        if f.expected is evals.Decision.DENY
        and not (hook_guard.decide(f.command) or "").strip()
    ]
    assert silent == [], f"denied with no reason: {silent}"


def test_the_real_offline_run_is_green_on_this_tree() -> None:
    """The live gate: this repo's own offline cases must pass here.

    Skips nothing and hides nothing — a SKIP would be visible in the report, and
    an all-SKIP run exits non-zero by construction.
    """
    rc, report = evals.run(_cases(), live=False)
    assert rc == 0, report
