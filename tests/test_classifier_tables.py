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
