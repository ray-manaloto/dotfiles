"""Tests for the classifier axis gate (dotfiles_setup.classifier_tables).

The gate exists because #601 burned four of seven adversarial review rounds on
one root cause found twice — an axis a sibling predicate already consumed but
the author's enumeration omitted. So these tests are built around the two REAL
defects, reconstructed as source fixtures, rather than invented shapes:

- `_COMMIT1_SOURCE` reproduces `dag_tick.py` at `e9da8cb`, where
  `is_needs_human(state, needs)` omits `queued_prompt` while `is_terminal`
  two functions above already reads it.
- The `illegal_pin` tests cover `tempo` being NAMED and PINNED on the premise
  "only matters for WEDGED" — the premise round 7 shipped in a comment, a
  commit message AND a verification contract, and the one an enumeration check
  alone cannot refute.

Both arms of every check are pinned: a probe that can only pass is not a check
(`.claude/rules/probes-need-a-control-arm.md`).
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import pytest
from dotfiles_setup import classifier_tables

# ---------------------------------------------------------------------------
# Fixtures — the two real #601 defects, as source
# ---------------------------------------------------------------------------

# The shape at commit `e9da8cb`: `is_terminal` reads `queued_prompt`;
# `is_needs_human` two functions below does NOT. Reduced to the classification
# skeleton so the fixture stays readable — the defect itself is verbatim.
_COMMIT1_SOURCE = """
def is_terminal(state, tempo, *, queued_prompt):
    return state in TERMINAL_STATES and tempo != "active" and not queued_prompt


def is_needs_human(state, needs):
    return state == "blocked" and needs is not None


def classify(node: Node, *, pid_alive, state_age_s, stall_after_s=120.0):
    if is_terminal(node.state, node.tempo, queued_prompt=node.queued_prompt):
        return NodeClass.DONE
    if is_needs_human(node.state, node.needs):
        return NodeClass.NEEDS_HUMAN
    if not pid_alive:
        return NodeClass.DEAD
    if node.tempo == "active" and state_age_s and state_age_s > stall_after_s:
        return NodeClass.WEDGED
    return NodeClass.ALIVE
"""

# The same classifier with #601's fix applied — `is_needs_human` now takes
# `queued_prompt`. Nothing else changes, so any difference in the derived set
# is attributable to that one parameter.
_FIXED_SOURCE = _COMMIT1_SOURCE.replace(
    "def is_needs_human(state, needs):\n"
    '    return state == "blocked" and needs is not None',
    "def is_needs_human(state, needs, *, queued_prompt):\n"
    '    return state == "blocked" and needs is not None and not queued_prompt',
).replace(
    "if is_needs_human(node.state, node.needs):",
    "if is_needs_human(node.state, node.needs, queued_prompt=node.queued_prompt):",
)

# A classifier whose predicate takes the WHOLE node — its reads are one frame
# down, invisible to a call-site-only scan. `derive_axes` must follow the call.
_TRANSITIVE_SOURCE = """
def is_escalated(node: Node) -> bool:
    return node.state == "blocked" and node.needs is not None


def classify(node: Node, *, pid_alive):
    if is_escalated(node):
        return NodeClass.NEEDS_HUMAN
    if not pid_alive:
        return NodeClass.DEAD
    return NodeClass.ALIVE
"""

# The cold-review shape. `_COMMIT1_SOURCE` plus ONE line — `n = node` — with
# the field reads renamed to match. Built by `.replace()` off the fixture above
# rather than retyped, so the delta is provably just the rebinding and any
# difference in the derived set is attributable to it alone.
_ALIASED_SOURCE = (
    _COMMIT1_SOURCE.replace(
        "def classify(node: Node, *, pid_alive, state_age_s, stall_after_s=120.0):\n",
        "def classify(node: Node, *, pid_alive, state_age_s, stall_after_s=120.0):\n"
        "    n = node\n",
    )
    .replace("node.state", "n.state")
    .replace("node.tempo", "n.tempo")
    .replace("node.queued_prompt", "n.queued_prompt")
    .replace("node.needs", "n.needs")
)

# The sibling shape, same root cause: a predicate the walk cannot read at all.
# Nothing about `is_escalated` is visible here, so every field it reads is
# invisible — including, in real life, the ones the registry names.
_CROSS_MODULE_SOURCE = """
from other_module import is_escalated


def classify(node: Node, *, pid_alive):
    if is_escalated(node):
        return NodeClass.NEEDS_HUMAN
    if not pid_alive:
        return NodeClass.DEAD
    return NodeClass.ALIVE
"""

_REGISTRY_KEY = "dotfiles_setup.dag_tick:classify"

# A spec pointed at the fixture sources. Built by `dataclasses.replace` off the
# real registry entry so a field added there cannot leave these tests behind.
_BASE_SPEC = classifier_tables.REGISTRY[_REGISTRY_KEY]


def _repo_root() -> Path:
    return Path(__file__).parent.parent


def _derive(
    source: str, spec: classifier_tables.ClassifierSpec
) -> classifier_tables.DerivedAxes:
    derived = classifier_tables.derive_axes(source, spec)
    assert derived is not None
    return derived


def _kinds(
    spec: classifier_tables.ClassifierSpec, source: str, kind: str
) -> list[classifier_tables.AxisViolation]:
    return [
        v
        for v in classifier_tables.violations_for(
            "fixture", spec, _derive(source, spec)
        )
        if v.kind == kind
    ]


# ---------------------------------------------------------------------------
# derive_axes() — the definition, and the two defects
# ---------------------------------------------------------------------------


def test_derive_axes_names_queued_prompt_at_commit_one() -> None:
    """THE #601 defect. `is_needs_human` omits it; `is_terminal` reads it.

    This is the whole point of deriving rather than declaring: an author
    writing commit 1's axis list by hand omits `queued_prompt` and is
    self-consistent. The code is not.
    """
    assert "queued_prompt" in _derive(_COMMIT1_SOURCE, _BASE_SPEC).axes


def test_derive_axes_is_the_documented_union_exactly() -> None:
    """Params (minus the subject) UNION every subject field read, and no more."""
    assert _derive(_COMMIT1_SOURCE, _BASE_SPEC).axes == frozenset(
        {
            # classify()'s own parameters, minus `node`
            "pid_alive",
            "state_age_s",
            "stall_after_s",
            # every `node.<field>` read on the way to a return
            "state",
            "tempo",
            "queued_prompt",
            "needs",
        }
    )
    assert "node" not in _derive(_COMMIT1_SOURCE, _BASE_SPEC).axes


def test_derive_axes_is_identical_before_and_after_the_601_fix() -> None:
    """The control arm: the DERIVED set does not move across the fix.

    `queued_prompt` was always read (by `is_terminal`), so the fix changes the
    code but not the axis set — which is exactly why the gate could have named
    it at commit 1, before anyone knew there was a defect.
    """
    assert _COMMIT1_SOURCE != _FIXED_SOURCE
    assert (
        _derive(_COMMIT1_SOURCE, _BASE_SPEC).axes
        == _derive(_FIXED_SOURCE, _BASE_SPEC).axes
    )


def test_derive_axes_follows_a_predicate_that_takes_the_whole_node() -> None:
    """Transitive reads: a predicate taking `Node` hides its fields a frame down."""
    assert _derive(_TRANSITIVE_SOURCE, _BASE_SPEC).axes == frozenset(
        {"pid_alive", "state", "needs"}
    )


# ---------------------------------------------------------------------------
# The subject-alias inversion, and its sibling — found by cold review
# ---------------------------------------------------------------------------
#
# ⚠️ These are not "a hole". Before the fix, adding `n = node` did not make
# derivation miss the axes — it made it emit `phantom`, instructing the author
# to DELETE the `queued_prompt`/`tempo`/`state`/`needs` declarations that #601
# exists to install. An author who complies strips the protection and the gate
# goes green forever. A miss is a gap; an inverted instruction is a trap, and
# it landed on the fixture that IS the motivating defect.
#
# The control arm throughout is `_COMMIT1_SOURCE` itself: it differs by exactly
# the rebinding, so "the alias case now equals the control" is a statement the
# probe can fail.


def test_derive_axes_follows_a_local_alias_of_the_subject() -> None:
    """`n = node` must derive IDENTICALLY to the un-aliased control.

    Equality with the control, not merely "phantom is gone" — a walk that
    found nothing and stayed quiet would also satisfy the weaker claim, and
    that is the failure mode being fixed.
    """
    assert _ALIASED_SOURCE != _COMMIT1_SOURCE
    assert "    n = node\n" in _ALIASED_SOURCE
    control = _derive(_COMMIT1_SOURCE, _BASE_SPEC)
    aliased = _derive(_ALIASED_SOURCE, _BASE_SPEC)
    assert aliased.axes == control.axes
    assert dict(aliased.gated_classes) == dict(control.gated_classes)
    assert aliased.unresolved == frozenset()


def test_an_alias_never_instructs_deleting_the_601_declarations() -> None:
    """The inversion itself: no `phantom` on the aliased source.

    Armed against a REAL phantom — an axis genuinely removed from the code —
    so this is not a check that can only pass.
    """
    assert _kinds(_BASE_SPEC, _ALIASED_SOURCE, "phantom") == []
    # …and it CAN still say it: stop reading `n.needs` through the alias and
    # `phantom` fires naming it. The mutation is asserted to have landed — the
    # first attempt at this arm silently replaced nothing and "passed".
    unread = _ALIASED_SOURCE.replace(
        "if is_needs_human(n.state, n.needs):", "if is_needs_human(n.state, None):"
    )
    assert unread != _ALIASED_SOURCE
    assert "n.needs" not in unread
    genuine = _kinds(_BASE_SPEC, unread, "phantom")
    assert len(genuine) == 1
    assert "needs" in genuine[0].detail


@pytest.mark.parametrize(
    ("label", "binding"),
    [
        ("chained targets", "    n = m = node\n    m = m\n"),
        ("literal tuple unpack", "    n, _ = node, pid_alive\n"),
        ("annotated by value", "    n: Node = node\n"),
        ("walrus", "    _ = (n := node)\n"),
        ("ternary operand", "    n = node if pid_alive else node\n"),
        ("alias chain", "    _mid = node\n    n = _mid\n"),
    ],
)
def test_every_covered_binding_form_propagates_subject_hood(
    label: str, binding: str
) -> None:
    """Each form `_subject_aliases` claims to cover, held to the control's answer.

    Enumerated rather than testing the single shape the reviewer used — a fix
    that only handles `n = node` is a special case wearing a general name.
    """
    source = _COMMIT1_SOURCE.replace(
        "def classify(node: Node, *, pid_alive, state_age_s, stall_after_s=120.0):\n",
        "def classify(node: Node, *, pid_alive, state_age_s, stall_after_s=120.0):\n"
        + binding,
    )
    for read in ("node.state", "node.tempo", "node.queued_prompt", "node.needs"):
        source = source.replace(read, read.replace("node.", "n."))
    derived = _derive(source, _BASE_SPEC)
    assert derived.axes == _derive(_COMMIT1_SOURCE, _BASE_SPEC).axes, label


def test_a_cross_module_predicate_is_reported_not_assumed_harmless() -> None:
    """An unreadable callee must go RED, never silently clean.

    Following imports is out of scope; pretending the walk was complete is
    not. `is_escalated` is imported, so every field it reads is invisible —
    the derivation is a lower bound and says so.
    """
    derived = _derive(_CROSS_MODULE_SOURCE, _BASE_SPEC)
    assert derived.axes == frozenset({"pid_alive"})
    assert any("is_escalated" in call for call in derived.unresolved)
    kinds = _kinds(_BASE_SPEC, _CROSS_MODULE_SOURCE, "unresolved_subject")
    assert len(kinds) == 1
    assert "is_escalated" in kinds[0].detail


def test_the_same_source_with_a_local_predicate_is_clean() -> None:
    """The control arm for the check above: make the callee readable, go green.

    Without this, `unresolved_subject` could be a check that always fires.
    `_TRANSITIVE_SOURCE` is `_CROSS_MODULE_SOURCE` with the identical predicate
    defined locally instead of imported.
    """
    derived = _derive(_TRANSITIVE_SOURCE, _BASE_SPEC)
    assert derived.unresolved == frozenset()
    assert derived.axes == frozenset({"pid_alive", "state", "needs"})


def test_phantom_is_withheld_while_anything_is_unresolved() -> None:
    """`phantom` is the only kind that instructs a DELETION — so it waits.

    With `state`/`needs` declared and the predicate imported, the pre-fix
    engine emitted `phantom` naming both: an instruction to delete the very
    declarations the imported predicate still reads. Now the run is red on
    `unresolved_subject` and the deletion advice is withheld — and says so.
    """
    spec = dataclasses.replace(
        _BASE_SPEC, axes=frozenset({"state", "needs", "pid_alive"}), pinned_axes={}
    )
    kinds = [
        v.kind
        for v in classifier_tables.violations_for(
            "f", spec, _derive(_CROSS_MODULE_SOURCE, spec)
        )
    ]
    assert "phantom" not in kinds
    assert kinds == ["unresolved_subject"]
    detail = _kinds(spec, _CROSS_MODULE_SOURCE, "unresolved_subject")[0].detail
    assert "WITHHELD" in detail
    assert "'needs'" in detail
    assert "'state'" in detail


def test_a_readable_walk_still_reports_a_real_phantom() -> None:
    """The control: withholding must not be permanent silence.

    Same registry, same missing axes — but a callee the walk can read. The
    verdict is sound here, so `phantom` fires.
    """
    spec = dataclasses.replace(
        _BASE_SPEC,
        axes=frozenset({"state", "needs", "pid_alive", "gone"}),
        pinned_axes={},
    )
    kinds = _kinds(spec, _TRANSITIVE_SOURCE, "phantom")
    assert len(kinds) == 1
    assert "gone" in kinds[0].detail


@pytest.mark.parametrize(
    ("label", "body"),
    [
        ("tuple round-trip", "    pair = (node, pid_alive)\n    n, _ = pair\n"),
        ("dict storage", '    d = {}\n    d["k"] = node\n    n = d["k"]\n'),
        ("call returning the subject", '    n = replace(node, state="x")\n'),
        ("method call taking the subject", "    n = node\n    helper.audit(node)\n"),
    ],
)
def test_an_unmodellable_store_of_the_subject_goes_red(label: str, body: str) -> None:
    """The forms `_subject_aliases` does NOT cover must fail loud, not quiet.

    This is the generalisation, not a second special case: aliasing covers the
    bindings it can prove, and anything that hands the subject somewhere else
    is reported. Otherwise `phantom` returns to its inverted state by a route
    aliasing never touches.
    """
    source = f"""
def classify(node: Node, *, pid_alive):
{body}    if n.state == "done":
        return NodeClass.DONE
    return NodeClass.ALIVE
"""
    spec = dataclasses.replace(
        _BASE_SPEC, axes=frozenset({"state", "pid_alive"}), pinned_axes={}
    )
    assert _kinds(spec, source, "unresolved_subject"), label
    assert _kinds(spec, source, "phantom") == [], label


def test_reading_a_field_into_a_local_is_not_a_store_of_the_subject() -> None:
    """The control arm for the store check: `x = node.state` must stay CLEAN.

    The test is "does this hand over the SUBJECT", not "does it mention the
    subject" — a field read is fully recorded at its own line, so flagging it
    would make `unresolved_subject` fire on ordinary code and the kind would
    be worth nothing.
    """
    source = """
def classify(node: Node, *, pid_alive):
    x = node.state
    if x == "done":
        return NodeClass.DONE
    return NodeClass.ALIVE
"""
    spec = dataclasses.replace(
        _BASE_SPEC, axes=frozenset({"state", "pid_alive"}), pinned_axes={}
    )
    derived = _derive(source, spec)
    assert derived.unresolved == frozenset()
    assert derived.axes == frozenset({"state", "pid_alive"})


def test_the_real_registry_resolves_completely() -> None:
    """Neither shipped classifier hands its subject anywhere unreadable.

    If this ever fails, `unresolved_subject` is telling the truth and the
    classifier needs its predicate brought in-module — it is not licence to
    add an escape hatch to the spec.
    """
    root = _repo_root()
    for spec in classifier_tables.REGISTRY.values():
        derived = classifier_tables.derive_axes(
            (root / spec.module_path).read_text(), spec
        )
        assert derived is not None
        assert derived.unresolved == frozenset(), spec.function


def test_derive_axes_returns_none_for_a_missing_function() -> None:
    """A renamed/removed classifier is `None`, never a silently-empty pass."""
    spec = dataclasses.replace(_BASE_SPEC, function="gone")
    assert classifier_tables.derive_axes(_COMMIT1_SOURCE, spec) is None


def test_gated_classes_separate_tempo_from_the_age_knobs() -> None:
    """`tempo` decides DONE; the age knobs decide only WEDGED.

    This is the fact that makes a PIN checkable instead of trusted, and it is
    the fact round 7's comment, commit message and contract all got wrong.
    """
    derived = _derive(_FIXED_SOURCE, _BASE_SPEC)
    assert "DONE" in derived.gated_classes["tempo"]
    assert derived.gated_classes["state_age_s"] == frozenset({"WEDGED"})
    assert derived.gated_classes["stall_after_s"] == frozenset({"WEDGED"})


# ---------------------------------------------------------------------------
# The violation kinds — each with its passing arm
# ---------------------------------------------------------------------------


def test_undeclared_fires_on_the_commit_one_axis_list() -> None:
    """FAIL arm: commit 1's declaration judged against commit 1's code."""
    spec = dataclasses.replace(
        _BASE_SPEC,
        axes=frozenset({"state", "needs", "pid_alive"}),
        pinned_axes={
            "tempo": "only matters for WEDGED",
            "state_age_s": "knob",
            "stall_after_s": "knob",
        },
    )
    violations = _kinds(spec, _COMMIT1_SOURCE, "undeclared")
    assert len(violations) == 1
    assert "queued_prompt" in violations[0].detail


def test_undeclared_is_silent_when_the_declaration_is_complete() -> None:
    """PASS arm: the same code with `queued_prompt` declared."""
    spec = dataclasses.replace(
        _BASE_SPEC,
        axes=frozenset({"state", "needs", "pid_alive", "queued_prompt", "tempo"}),
    )
    assert _kinds(spec, _COMMIT1_SOURCE, "undeclared") == []


def test_illegal_pin_fires_on_round_sevens_false_premise() -> None:
    """FAIL arm: `tempo` NAMED and pinned — the shape enumeration alone misses."""
    spec = dataclasses.replace(
        _BASE_SPEC,
        axes=frozenset({"state", "needs", "pid_alive", "queued_prompt"}),
        pinned_axes={
            "tempo": "only matters for WEDGED",
            "state_age_s": "knob",
            "stall_after_s": "knob",
        },
    )
    violations = _kinds(spec, _FIXED_SOURCE, "illegal_pin")
    assert len(violations) == 1
    assert "tempo" in violations[0].detail
    assert "DONE" in violations[0].detail


def test_illegal_pin_allows_a_pin_whose_class_the_table_excludes() -> None:
    """PASS arm: the age knobs decide only the excluded WEDGED.

    Without this arm the check would be indistinguishable from "reject every
    pin", which makes the pin mechanism useless rather than honest.
    """
    assert _kinds(_BASE_SPEC, _FIXED_SOURCE, "illegal_pin") == []


def test_illegal_pin_fires_when_the_exclusion_is_withdrawn() -> None:
    """The exclusion is load-bearing: drop WEDGED and both age pins turn illegal."""
    spec = dataclasses.replace(_BASE_SPEC, table_excluded_classes=frozenset())
    details = " ".join(v.detail for v in _kinds(spec, _FIXED_SOURCE, "illegal_pin"))
    assert "state_age_s" in details
    assert "stall_after_s" in details


# ---------------------------------------------------------------------------
# `illegal_pin` across every RETURN SHAPE — found by adversarial critique
# ---------------------------------------------------------------------------
#
# ⚠️ The check that convicts an author of pinning an axis on an unverified
# premise was itself verified against exactly one return shape. Measured across
# seven, FOUR allowed the pin. Each fixture below pins `tempo` on round 7's
# literal false premise under the shipped `table_excluded_classes={"WEDGED"}`;
# every one must refuse it.
#
# `F` is the one that matters: `if tempo == "active": return WEDGED` /
# `else: return DONE` is round 7's own premise written with an `else`. The
# branch reader looked at `body` and never `orelse`, so `tempo` was credited
# with WEDGED alone — an excluded class — and the pin was ALLOWED by the check
# whose docstring promises the opposite. One syntactic rearrangement of the
# code the gate was derived from.

_PIN_HEAD = """
from enum import Enum


class K(Enum):
    DONE = "d"
    WEDGED = "w"
    LIVE = "l"


class Node:
    state: str
    tempo: str
"""

_RETURN_SHAPES = {
    "A_bare_return_control": """
def classify(node: "Node") -> K:
    if node.tempo != "active" and node.state == "done":
        return K.DONE
    return K.LIVE
""",
    "B_ternary": """
def classify(node: "Node") -> K:
    if node.state == "done":
        return K.DONE if node.tempo != "active" else K.LIVE
    return K.LIVE
""",
    "C_match_statement": """
def classify(node: "Node") -> K:
    match (node.state, node.tempo):
        case ("done", "idle"):
            return K.DONE
        case _:
            return K.LIVE
""",
    "D_dict_dispatch": """
_M = {("done", "idle"): K.DONE}


def classify(node: "Node") -> K:
    if (node.state, node.tempo) in _M:
        return _M[(node.state, node.tempo)]
    return K.LIVE
""",
    "E_name_return": """
def classify(node: "Node") -> K:
    if node.tempo != "active" and node.state == "done":
        verdict = K.DONE
        return verdict
    return K.LIVE
""",
    "F_else_branch_only": """
def classify(node: "Node") -> K:
    if node.tempo == "active":
        return K.WEDGED
    else:
        return K.DONE
""",
    "G_method_call_predicate": """
class H:
    def term(self, node: "Node") -> bool:
        return node.tempo != "active"


_h = H()


def classify(node: "Node") -> K:
    if _h.term(node) and node.state == "done":
        return K.DONE
    return K.LIVE
""",
}

_PIN_SPEC = dataclasses.replace(
    _BASE_SPEC,
    axes=frozenset({"state"}),
    pinned_axes={"tempo": "claimed to only matter for WEDGED"},
    table_excluded_classes=frozenset({"WEDGED"}),
)


@pytest.mark.parametrize("shape", sorted(_RETURN_SHAPES))
def test_illegal_pin_refuses_round_sevens_premise_in_every_return_shape(
    shape: str,
) -> None:
    """No return shape may let `tempo` be pinned as "only matters for WEDGED".

    Some shapes are refused because the gate now READS them (`else`, `match`, a
    local assigned a class); others because it cannot read them and therefore
    fails CLOSED (dict dispatch, an unfollowable predicate). Both are correct
    outcomes; what is not correct is the third one it used to give.
    """
    assert _kinds(_PIN_SPEC, _PIN_HEAD + _RETURN_SHAPES[shape], "illegal_pin"), shape


def test_the_shipped_pins_are_still_allowed() -> None:
    """THE control arm: a check that can only deny is not a check.

    `state_age_s`/`stall_after_s` gate only WEDGED, which `dag_tick`'s table
    declares out of scope, so their pins must survive every tightening above.
    If this ever goes red alongside the parametrized test, the fix made the
    kind unconditional rather than correct.
    """
    root = _repo_root()
    for name, spec in classifier_tables.REGISTRY.items():
        derived = classifier_tables.derive_axes(
            (root / spec.module_path).read_text(), spec
        )
        assert derived is not None
        assert classifier_tables.violations_for(name, spec, derived) == [], name
    assert _BASE_SPEC.pinned_axes, "the control arm needs a real pin to be about"


def test_an_else_branch_credits_the_axis_with_both_arms() -> None:
    """F, stated as the mapping rather than the verdict.

    Asserting only "the pin is refused" would also pass if the fix were a
    blanket refusal. The claim is specific: `tempo` gates DONE *and* WEDGED.
    """
    derived = _derive(_PIN_HEAD + _RETURN_SHAPES["F_else_branch_only"], _PIN_SPEC)
    assert derived.gated_classes["tempo"] == frozenset({"DONE", "WEDGED"})


def test_a_local_assigned_a_class_is_resolved_not_merely_failed_closed() -> None:
    """E must be READ, not just refused — and the distinction is invisible above.

    `verdict = K.DONE; return verdict` is ordinary Python. Disabling the local
    resolution entirely still leaves the parametrized test green, because the
    unresolvable return then trips the fail-CLOSED path and the pin is refused
    anyway — the right answer for the wrong reason, which is the one thing a
    passing test cannot tell you (`feedback_test_right_answer_wrong_reason`).
    So assert the mechanism: the return resolves, nothing is unreadable, and
    `tempo` gates exactly DONE.
    """
    derived = _derive(_PIN_HEAD + _RETURN_SHAPES["E_name_return"], _PIN_SPEC)
    assert derived.unreadable_decisions == frozenset()
    assert derived.gated_classes["tempo"] == frozenset({"DONE"})


def test_a_class_reference_is_not_confused_with_a_field_read() -> None:
    """`NodeClass.DONE` and `node.tempo` are both `Attribute(value=Name)`.

    The first version took every one of them as a class, so a probe reported
    `tempo_gates=['DONE', 'LIVE', 'tempo']` — an AXIS listed among the CLASSES.
    It failed closed, so nothing was exploitable; it was still evidence the
    derivation was textual where it claims to be semantic.
    """
    derived = _derive(_PIN_HEAD + _RETURN_SHAPES["B_ternary"], _PIN_SPEC)
    assert derived.gated_classes["tempo"] == frozenset({"DONE", "LIVE"})
    assert "tempo" not in derived.gated_classes["tempo"]
    assert "state" not in derived.gated_classes["tempo"]


def test_an_unreadable_return_is_reported_not_treated_as_no_classes() -> None:
    """The fail-CLOSED trigger, named. `return _M[key]` resolves to no member."""
    derived = _derive(_PIN_HEAD + _RETURN_SHAPES["D_dict_dispatch"], _PIN_SPEC)
    assert derived.unreadable_decisions
    assert any("_M[" in reason for reason in derived.unreadable_decisions)


def test_a_fully_readable_classifier_reports_nothing_unreadable() -> None:
    """Control arm for the trigger above: shape A must be entirely readable."""
    derived = _derive(_PIN_HEAD + _RETURN_SHAPES["A_bare_return_control"], _PIN_SPEC)
    assert derived.unreadable_decisions == frozenset()
    assert derived.unresolved == frozenset()


def test_phantom_fires_on_an_axis_the_code_no_longer_reads() -> None:
    """FAIL arm: a declared axis nothing in the classifier reads."""
    spec = dataclasses.replace(
        _BASE_SPEC, axes=_BASE_SPEC.axes | frozenset({"suggested_reply"})
    )
    violations = _kinds(spec, _FIXED_SOURCE, "phantom")
    assert len(violations) == 1
    assert "suggested_reply" in violations[0].detail


def test_phantom_is_silent_on_the_real_declaration() -> None:
    """PASS arm: every axis the shipped registry declares is really read."""
    assert _kinds(_BASE_SPEC, _FIXED_SOURCE, "phantom") == []


# ---------------------------------------------------------------------------
# find_violations() — against the real repo, and against broken trees
# ---------------------------------------------------------------------------


def test_the_real_registry_is_clean() -> None:
    """The negative control: this repo, as committed, passes its own gate."""
    assert classifier_tables.find_violations(_repo_root()) == []


def test_registry_covers_the_dag_tick_classifier() -> None:
    """The gate guards nothing if the classifier is not registered."""
    assert _REGISTRY_KEY in classifier_tables.REGISTRY


def test_stale_fires_when_the_module_is_gone(tmp_path: Path) -> None:
    """An empty tree: every entry is stale, and none passes silently."""
    violations = classifier_tables.find_violations(tmp_path)
    assert violations
    assert all(v.kind == "stale" for v in violations)


def _stage_repo(tmp_path: Path, *, tables: bool) -> None:
    """Copy every registered module (and optionally its table) into tmp_path."""
    for spec in classifier_tables.REGISTRY.values():
        module = tmp_path / spec.module_path
        module.parent.mkdir(parents=True, exist_ok=True)
        module.write_text((_repo_root() / spec.module_path).read_text())
        table = tmp_path / spec.table_path
        table.parent.mkdir(parents=True, exist_ok=True)
        table.write_text(
            (_repo_root() / spec.table_path).read_text()
            if tables
            else "# a test file with no truth table in it\n"
        )


def test_table_missing_fires_when_the_truth_table_symbol_is_gone(
    tmp_path: Path,
) -> None:
    """FAIL arm: the code is fine but the table the axes justify is absent."""
    _stage_repo(tmp_path, tables=False)
    kinds = [v.kind for v in classifier_tables.find_violations(tmp_path)]
    assert kinds == ["table_missing"] * len(classifier_tables.REGISTRY)


def test_table_missing_rejects_a_mere_mention_of_the_symbol(tmp_path: Path) -> None:
    """A COMMENT naming the table used to satisfy the check.

    `spec.table_symbol not in table_source` was an unanchored substring test —
    the same shape #601's own v1 review filed as a LOW against
    `per_path_tokens`, reproduced inside the gate written to answer that
    review. A file whose entire content is a comment naming `_CLASSIFY_TABLE`
    passed. It must now fail, because nothing in it CROSSES anything.
    """
    _stage_repo(tmp_path, tables=True)
    spec = classifier_tables.REGISTRY[_REGISTRY_KEY]
    (tmp_path / spec.table_path).write_text(
        f"# the {spec.table_symbol} used to live here\n"
        f'"""...and a docstring naming {spec.table_symbol} too."""\n'
    )
    kinds = [
        v.kind
        for v in classifier_tables.find_violations(tmp_path)
        if v.classifier == _REGISTRY_KEY
    ]
    assert "table_missing" in kinds


def test_table_missing_accepts_a_real_binding(tmp_path: Path) -> None:
    """Control arm: an ASSIGNMENT of the symbol satisfies it, so it can pass.

    Both an annotated and a bare assignment, since the two shipped tables use
    the annotated form and a future one may not.
    """
    spec = classifier_tables.REGISTRY[_REGISTRY_KEY]
    for binding in (
        f"{spec.table_symbol}: list[tuple[str, ...]] = []\n",
        f"{spec.table_symbol} = []\n",
    ):
        _stage_repo(tmp_path, tables=True)
        (tmp_path / spec.table_path).write_text(binding)
        kinds = [
            v.kind
            for v in classifier_tables.find_violations(tmp_path)
            if v.classifier == _REGISTRY_KEY
        ]
        assert "table_missing" not in kinds, binding


def test_staged_repo_with_its_tables_is_clean(tmp_path: Path) -> None:
    """PASS arm for the fixture itself — could it have produced the other result?

    Without this, `test_table_missing_...` is satisfied by a fixture that is
    broken for some unrelated reason (`probes-need-a-control-arm.md` rule 8).
    """
    _stage_repo(tmp_path, tables=True)
    assert classifier_tables.find_violations(tmp_path) == []


# ---------------------------------------------------------------------------
# `unlisted` — the kind that makes the registry GROW
# ---------------------------------------------------------------------------

_THIRD_CLASSIFIER = """
import enum


class Verdict(enum.Enum):
    YES = "yes"
    NO = "no"


def decide(flag: bool) -> Verdict:
    if flag:
        return Verdict.YES
    return Verdict.NO
"""

_NOT_A_CLASSIFIER = """
import enum


class Verdict(enum.Enum):
    YES = "yes"


def helper(flag: bool) -> bool:
    return flag


def other(flag: bool) -> str:
    return "x"
"""


def test_classifier_shaped_finds_the_two_real_classifiers() -> None:
    """The discovery predicate, measured against the shipped tree.

    2 hits across 45 modules, zero false positives — the measurement that
    justified making this a gate rather than leaving it a heuristic.
    """
    found = {
        f"{path.name}:{fn}"
        for path in sorted(_repo_root().glob(classifier_tables.SCAN_GLOB))
        for fn in classifier_tables.classifier_shaped(path.read_text())
    }
    assert found == {"dag_tick.py:classify", "branch_guard.py:classify"}


def test_classifier_shaped_ignores_functions_not_returning_a_local_enum() -> None:
    """CONTROL ARM: the predicate must be able to say NO.

    A module that DEFINES an enum but whose functions return `bool`/`str` must
    yield nothing — otherwise the scan would demand a registry entry for every
    helper that happens to live beside an enum.
    """
    assert classifier_tables.classifier_shaped(_NOT_A_CLASSIFIER) == set()
    assert classifier_tables.classifier_shaped(_THIRD_CLASSIFIER) == {"decide"}


def test_unlisted_fires_on_an_unregistered_classifier(tmp_path: Path) -> None:
    """FAIL arm: a classifier-shaped function with no REGISTRY entry.

    This is the mechanism `bash_budget`'s allowlist has and the first version
    of this module lacked — without it the registry guards whatever it happens
    to contain, forever.
    """
    _stage_repo(tmp_path, tables=True)
    new_module = tmp_path / "python/src/dotfiles_setup/newly_added.py"
    new_module.write_text(_THIRD_CLASSIFIER)

    unlisted = [
        v for v in classifier_tables.find_violations(tmp_path) if v.kind == "unlisted"
    ]
    assert len(unlisted) == 1
    assert unlisted[0].classifier == "python/src/dotfiles_setup/newly_added.py:decide"


def test_unlisted_is_silent_for_the_registered_ones(tmp_path: Path) -> None:
    """PASS arm: both real classifiers ARE registered, so the scan is quiet."""
    _stage_repo(tmp_path, tables=True)
    assert [
        v for v in classifier_tables.find_violations(tmp_path) if v.kind == "unlisted"
    ] == []


def test_registry_covers_the_branch_guard_classifier() -> None:
    """The second entry — found by the scan, not by a human."""
    assert "dotfiles_setup.branch_guard:classify" in classifier_tables.REGISTRY


def test_a_subjectless_classifier_derives_its_parameters_as_axes() -> None:
    """`branch_guard.classify(code, lines)` has no subject dataclass at all."""
    spec = classifier_tables.REGISTRY["dotfiles_setup.branch_guard:classify"]
    assert spec.subject_param is None
    source = (_repo_root() / spec.module_path).read_text()
    derived = _derive(source, spec)
    assert derived.axes == frozenset({"code", "lines"})


def test_a_ternary_return_still_yields_its_gated_classes() -> None:
    """`lines` decides RESOLVED vs FALL_BACK inside a TERNARY, not an `if`.

    Requiring a bare `return Enum.MEMBER` made `gated_classes` EMPTY for this
    classifier — and an empty map makes every pin vacuously legal, so
    `illegal_pin` would have failed OPEN on the second entry registered.
    """
    spec = classifier_tables.REGISTRY["dotfiles_setup.branch_guard:classify"]
    source = (_repo_root() / spec.module_path).read_text()
    gated = _derive(source, spec).gated_classes
    assert gated["lines"] == frozenset({"RESOLVED", "FALL_BACK"})
    assert gated["code"] == frozenset({"RESOLVED", "FALL_BACK"})


def test_classifier_axes_main_both_directions(tmp_path: Path) -> None:
    """rc=0 on the real repo, rc=1 on a tree where the module is missing."""
    assert classifier_tables.classifier_axes_main(_repo_root()) == 0
    assert classifier_tables.classifier_axes_main(tmp_path) == 1


@pytest.mark.parametrize(
    "axis", ["state", "needs", "queued_prompt", "pid_alive", "tempo"]
)
def test_every_declared_crossed_axis_is_really_read(axis: str) -> None:
    """Each crossed axis is derivable from the shipped code, one at a time.

    Parametrized so a failure names WHICH axis stopped being read, instead of
    reporting one opaque set inequality.
    """
    source = (_repo_root() / _BASE_SPEC.module_path).read_text()
    assert axis in _derive(source, _BASE_SPEC).axes
