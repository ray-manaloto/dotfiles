# Copyright (c) 2026 Raymond Manaloto
"""Tests for the AskUserQuestion quality gate.

Every rule is tested in BOTH directions (`.claude/rules/probes-need-a-control-arm.md`):
a payload that must be DENIED and the same payload, minimally repaired, that must
be ALLOWED. A gate exercised only on compliant input is decoration.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest
from dotfiles_setup import ask_quality
from dotfiles_setup.hook_guard import decide_payload

GOOD_DESC = "PRO: cheap and reversible. CON: leaves `hk.pkl` untouched."


def question(**overrides: object) -> dict[str, object]:
    """A fully compliant single-select question; override one field per test."""
    base: dict[str, object] = {
        "question": "Which lane owns this, per `.claude/rules/do-not.md`?",
        "header": "Lane",
        "multiSelect": False,
        "options": [
            {"label": "Keep it here (Recommended)", "description": GOOD_DESC},
            {
                "label": "Move it",
                "description": "PRO: tidier. CON: a second place to drift.",
            },
        ],
    }
    base.update(overrides)
    return base


def uncited(**overrides: object) -> dict[str, object]:
    """A question that is compliant except that nothing in it is cited.

    Deliberately NOT built from ``question()``: the citation corpus spans the
    question text AND every option description, so overriding only the question
    text leaves ``hk.pkl`` in ``GOOD_DESC`` satisfying the check. Three tests
    were silently passing for that reason before this helper existed.
    """
    base: dict[str, object] = {
        "question": "Which one do you want?",
        "header": "Pick",
        "multiSelect": False,
        "options": [
            {"label": "A (Recommended)", "description": "PRO: fast. CON: rough."},
            {"label": "B", "description": "PRO: tidy. CON: slow."},
        ],
    }
    base.update(overrides)
    return base


def payload(*questions: dict[str, object]) -> dict[str, object]:
    return {"questions": list(questions)}


def test_uncited_helper_is_uncited_and_otherwise_compliant() -> None:
    """Control arm for the helper itself: exactly one violation, the citation."""
    (violation,) = ask_quality.find_violations(payload(uncited()))
    assert "no citation" in violation


# --- the ALLOW arm ----------------------------------------------------------


def test_compliant_ask_is_allowed() -> None:
    assert ask_quality.find_violations(payload(question())) == []
    assert ask_quality.decide(payload(question())) is None


def test_multiselect_needs_no_recommendation() -> None:
    """A '(Recommended)' pick is incoherent when the user picks several."""
    q = question(
        multiSelect=True,
        options=[
            {"label": "Lint", "description": GOOD_DESC},
            {"label": "Tests", "description": "PRO: catches regressions. CON: slow."},
        ],
    )
    assert ask_quality.find_violations(payload(q)) == []


@pytest.mark.parametrize(
    "citation",
    [
        "see `.claude/rules/do-not.md`",
        "see `hk.pkl`",
        "closed by #431",
        "https://github.com/ray-manaloto/dotfiles/issues/431",
        f"{ask_quality.NO_EVIDENCE_ESCAPE} — nothing in the repo covers this",
    ],
)
def test_every_accepted_citation_form(citation: str) -> None:
    q = question(question=f"Which one? {citation}")
    assert ask_quality.find_violations(payload(q)) == []


def test_citation_may_live_in_an_option_description() -> None:
    q = question(
        question="Which one?",
        options=[
            {
                "label": "A (Recommended)",
                "description": "PRO: matches `mise.toml`. CON: slower.",
            },
            {"label": "B", "description": "PRO: fast. CON: undocumented."},
        ],
    )
    assert ask_quality.find_violations(payload(q)) == []


# --- the DENY arm -----------------------------------------------------------


def test_no_recommendation_is_denied() -> None:
    q = question(
        options=[
            {"label": "Keep it here", "description": GOOD_DESC},
            {"label": "Move it", "description": "PRO: tidier. CON: drift."},
        ]
    )
    (violation,) = ask_quality.find_violations(payload(q))
    assert "no option is marked" in violation


def test_recommendation_not_first_is_denied() -> None:
    q = question(
        options=[
            {"label": "Move it", "description": GOOD_DESC},
            {"label": "Keep it here (Recommended)", "description": "PRO: a. CON: b."},
        ]
    )
    (violation,) = ask_quality.find_violations(payload(q))
    assert "must be FIRST" in violation


def test_two_recommendations_is_denied() -> None:
    q = question(
        options=[
            {"label": "Keep it (Recommended)", "description": GOOD_DESC},
            {"label": "Move it (Recommended)", "description": "PRO: a. CON: b."},
        ]
    )
    (violation,) = ask_quality.find_violations(payload(q))
    assert "exactly one option" in violation


def test_missing_description_is_denied() -> None:
    q = question(
        options=[
            {"label": "Keep it (Recommended)", "description": GOOD_DESC},
            {"label": "Move it", "description": "   "},
        ]
    )
    violations = ask_quality.find_violations(payload(q))
    assert any("no description" in v for v in violations)


@pytest.mark.parametrize(
    "description",
    [
        "PRO: fast, and nothing else.",
        "CON: slow, with no upside stated.",
        "Just a flat claim.",
    ],
)
def test_missing_pro_or_con_is_denied(description: str) -> None:
    q = question(
        options=[
            {"label": "Keep it (Recommended)", "description": GOOD_DESC},
            {"label": "Move it", "description": description},
        ]
    )
    violations = ask_quality.find_violations(payload(q))
    assert any("no trade-off" in v for v in violations)


def test_uncited_ask_is_denied() -> None:
    (violation,) = ask_quality.find_violations(payload(uncited()))
    assert "no citation" in violation


def test_a_bare_backticked_word_is_not_a_citation() -> None:
    """`foo` names nothing readable; `foo.py` or `a/b` does."""
    q = uncited(question="Which `one` do you want?")
    assert any("no citation" in v for v in ask_quality.find_violations(payload(q)))


def test_second_question_is_checked_too() -> None:
    violations = ask_quality.find_violations(payload(question(), uncited()))
    assert len(violations) == 1
    assert violations[0].startswith("question 2:")


def test_deny_reason_names_the_rule_and_forbids_the_prose_fallback() -> None:
    reason = ask_quality.decide(payload(uncited()))
    assert reason is not None
    assert ".claude/rules/clarify-before-acting.md" in reason
    assert "prose" in reason


# --- shapes the gate must NOT brick ----------------------------------------


@pytest.mark.parametrize(
    "tool_input",
    [{}, {"questions": []}, {"questions": "not-a-list"}, {"questions": [None, 7]}],
)
def test_unparsable_shapes_are_allowed(tool_input: dict[str, object]) -> None:
    assert ask_quality.find_violations(tool_input) == []


def test_option_list_without_options_is_allowed() -> None:
    assert ask_quality.find_violations(payload({"question": "hi", "options": []})) == []


# --- dispatch: the Bash path must be untouched ------------------------------


def test_dispatch_routes_askuserquestion_to_the_quality_gate() -> None:
    reason = decide_payload("AskUserQuestion", payload(uncited()))
    assert reason is not None
    assert "AskUserQuestion standard" in reason


def test_dispatch_allows_a_compliant_ask() -> None:
    assert decide_payload("AskUserQuestion", payload(question())) is None


def test_dispatch_still_denies_a_guarded_bash_command() -> None:
    reason = decide_payload("Bash", {"command": "git commit --no-verify -m x"})
    assert reason is not None


def test_dispatch_without_a_tool_name_is_the_legacy_bash_path() -> None:
    """Every pre-existing payload omits tool_name; it must behave as before."""
    assert decide_payload("", {"command": "git commit --no-verify -m x"}) is not None
    assert decide_payload("", {"command": "git status --short"}) is None


def test_an_askuserquestion_payload_is_never_read_as_a_bash_command() -> None:
    assert decide_payload("AskUserQuestion", payload(question())) is None


# --- the wired CLI path (proves the module is reachable as the hook runs it) --


#: The console-script entry point (`python/pyproject.toml` [project.scripts]),
#: driven in a subprocess so the stdin-reading path the real hook uses is
#: actually exercised — an in-process call cannot read stdin under pytest.
_ENTRY = (
    "import sys;"
    "from dotfiles_setup.main import main;"
    "sys.argv = ['dotfiles-setup'] + sys.argv[1:];"
    "main()"
)


def _run_hook(payload_obj: dict[str, object]) -> str:
    proc = subprocess.run(
        [sys.executable, "-c", _ENTRY, "hook", "pretooluse"],
        input=json.dumps(payload_obj),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def test_cli_denies_a_noncompliant_ask() -> None:
    out = _run_hook({"tool_name": "AskUserQuestion", "tool_input": payload(uncited())})
    decision = json.loads(out)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "AskUserQuestion standard" in decision["permissionDecisionReason"]


def test_cli_allows_a_compliant_ask() -> None:
    """The control arm for the test above: same path, same tool, no output."""
    out = _run_hook({"tool_name": "AskUserQuestion", "tool_input": payload(question())})
    assert out.strip() == ""
