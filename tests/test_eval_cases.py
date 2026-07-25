"""Tests for this repo's tier-1 eval cases (dotfiles_setup.eval_cases, #354 PR 2).

The runner (`kb_setup.evals`) is tested in the knowledge-base repo, where it
lives. What is ours to test is the CASES — and specifically that every gated one
carries a control arm that really fails, because that is the property the whole
harness rests on and the one an author adding a case will forget.

Catching it here rather than only at `mise run eval` time matters: the runner
reports UNARMED at run time, but a test says so at commit time, which is the
difference between a red gate and a red gate you understand.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import eval_cases
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
        "tier1.graph-answers",
        "tier1.lane-health",
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


def test_the_real_offline_run_is_green_on_this_tree() -> None:
    """The live gate: this repo's own offline cases must pass here.

    Skips nothing and hides nothing — a SKIP would be visible in the report, and
    an all-SKIP run exits non-zero by construction.
    """
    rc, report = evals.run(_cases(), live=False)
    assert rc == 0, report
