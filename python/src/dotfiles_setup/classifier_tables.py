"""Classifier axis enumeration: a declared axis list, DERIVED from the code.

#601 spent four of its seven adversarial review rounds on one root cause,
found twice, in the same function:

1. Commit 1 wrote ``def is_needs_human(state, needs)`` — a predicate that
   omitted an axis its own sibling ``is_terminal(state, tempo, *,
   queued_prompt)``, two functions above it in the same file, ALREADY
   consumed. That single missing ``queued_prompt`` produced two HIGH
   findings and two whole review rounds.
2. Round 7 found the same shape with ``tempo``: the truth table pinned
   ``tempo="idle"`` and asserted — in a code comment, a commit message AND a
   verification contract — that tempo "only matters for WEDGED". All three
   were wrong (``is_terminal`` requires ``tempo != "active"``). **No test
   could catch it, because the test encoded the same wrong assumption.**

A hand-written axis list cannot catch either: an author who does not know an
axis exists writes a list that omits it, and that list is self-consistent.
The only thing that catches it is DERIVING the list from the code, with this
definition (the post-mortem's, chosen because it is signature-derivable with
**zero judgement**):

    The axes are the union of ``classify()``'s parameters and every ``Node``
    field read by any predicate it calls.

⚠️ **The chain, stated accurately — an earlier draft of this docstring
overclaimed it, which is the failure class this module exists to fix.** It said
"applied at commit 1 that names ``queued_prompt`` … both defects die at commit
1", as if one run emitted ``undeclared: queued_prompt`` + ``illegal_pin: tempo``
+ ``table_missing`` together. A replay of four registry-provenance worlds shows
those three fire in three DIFFERENT worlds and never in one run:
``undeclared: queued_prompt`` only where the entry is BORN at commit 1, but
"applied at commit 1" presumes the gate pre-existed the branch — and in that
world ``derive_axes`` already yields ``queued_prompt`` at ``d070cb5``, one
commit EARLIER, so the gate is silent at commit 1; and ``illegal_pin: tempo``
cannot fire at commit 1 at all, because there was no pin and no table until
commit 8.

What actually happens, and it is a better result than the one claimed: the axis
is named **when the gate is ADOPTED** — at ``d070cb5``, before #601 is even cut.
From there the chain is ``table_missing`` forcing the table to EXIST →
``test_classify_truth_table_axes_match_the_registry`` binding
``frozenset(_AXIS_VALUES) == spec.axes`` (``tests/test_dag_tick.py``) → the
declared ``needs`` forcing a ``needs`` column → the cell
``(blocked, needs≠∅, queued_prompt=True)`` enumerated at commit 1. That cell is
the round-5/6 defect. The round-7 ``tempo`` pin is caught later, by
``illegal_pin``, at the commit that writes it.

Two mechanisms, mirroring :mod:`dotfiles_setup.bash_budget`:

1. **A declarative** :data:`REGISTRY` **gates the DECLARATION.** Each entry
   names a classifier, the axes its truth table CROSSES, and the axes it
   deliberately PINS (each with the reason it is held constant). A derived
   axis absent from both FAILS — that is the #601 defect.
2. **The declaration is checked against the CODE, never against itself.**
   :func:`derive_axes` parses the module with :mod:`ast`; the registry is
   only ever the thing being judged.

⚠️ **A PIN is checked, not trusted — because naming an axis does not prevent
pinning it.** Enumerating alone would have caught round 7 only if the author
had never thought of ``tempo``; an author who thinks of it and pins it on the
premise "only matters for WEDGED" writes a self-consistent declaration and
sails through, which is precisely what round 7 shipped — in a comment, a
commit message AND a verification contract. That premise is derivable, so the
gate derives it: :func:`_gated_classes` maps each axis to the classes it can
decide, and a pin is legal only when every one of them is a class the table
declares out of scope (:attr:`ClassifierSpec.table_excluded_classes`).
``tempo`` reaches ``is_terminal``, which gates ``DONE`` — not excluded — so it
cannot be pinned. ``state_age_s``/``stall_after_s`` reach only ``is_stalled``,
which gates ``WEDGED`` — excluded, and asserted as such by the table itself.

⚠️ **That claim was true only for the return shapes the check could read, and
an adversarial pass measured FOUR OF SEVEN shapes allowing the pin.** The worst
was ``if tempo == "active": return WEDGED`` / ``else: return DONE`` — round 7's
own premise, rearranged with an ``else`` — because the branch reader looked
at ``branch.body`` and never ``branch.orelse``. A ``match``, a
``verdict = K.DONE; return verdict``, and a predicate reached as
``self.pred(node)`` each produced an EMPTY gate map, and an empty map made
every pin vacuously legal. So the check convicted others of exactly what it
was doing. Now: ``else`` and ``match`` are READ (:func:`_decision_at`), a local
assigned an enum member is resolved (:func:`_class_holding_locals`), and
anything still unreadable — a dict dispatch, an unfollowable callee — makes
**every pin illegal** rather than every pin legal (:func:`_unreadable_returns`).
The control arm that keeps this from being a check that can only deny is the
shipped registry: ``state_age_s``/``stall_after_s`` gate only ``WEDGED``, and
their pins are still allowed.

⚠️ **A derivation is only evidence while the walk can SEE.** A cold review
added one line to the commit-1 fixture — ``n = node``, with the field reads
rewritten to ``n.state`` — and the module did not merely miss the axes: it
emitted ``phantom``, telling the author to **delete** the ``queued_prompt``/
``tempo``/``state``/``needs`` declarations #601 exists to install. An author
who complies strips the protection while the gate applauds. A miss is a gap; a
confidently inverted instruction is a trap. Two fixes, and the split matters:
subject-hood now propagates through local rebinding (:func:`_subject_aliases`,
which enumerates the forms it covers and the forms it does not), while a call
whose body cannot be read at all — a cross-module import, a method, a builtin —
is recorded rather than assumed harmless. ``phantom`` is then **withheld**
whenever anything went unresolved: it is the only kind that instructs a
DELETION, so it is the only one whose false positive destroys protection
instead of merely wasting time. "Declared but unread" is a sound verdict only
when the walk saw everything.

That still does not make the gate a substitute for a reviewer: it judges
WHICH classes an axis decides, never whether the table's exclusion is itself
sound. This module is therefore one of a PAIR — the truth table in
``tests/test_dag_tick.py`` derives its axis names from this registry, so a
newly-derived axis forces the table to either cross it or pin it out loud.

The check logic lives here rather than in an inline-bash hk step for the same
reason ``bash_budget.py`` does — the ``classifier_axes`` hk step and the
``classifier-axes`` CLI subcommand are thin wrappers over
:func:`find_violations`.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClassifierSpec:
    """One classifier's declared axis enumeration and where its table lives.

    `axes` is what the truth table CROSSES; `pinned_axes` maps each
    deliberately-held-constant axis to the reason it is safe to hold. Their
    union must equal what :func:`derive_axes` reads out of the code —
    anything derived but undeclared is the #601 defect, anything declared but
    underived is a stale declaration.

    `subject_param`/`subject_type` are `None` for a SUBJECTLESS classifier —
    one whose axes are simply its parameters, with no dataclass to walk
    fields off (`branch_guard.classify(code, lines)`). The field walk is then
    skipped entirely rather than being pointed at a name that does not exist.
    """

    module_path: str
    function: str
    subject_param: str | None
    subject_type: str | None
    axes: frozenset[str]
    table_path: str
    table_symbol: str
    reason: str
    pinned_axes: Mapping[str, str] = field(default_factory=dict)
    table_excluded_classes: frozenset[str] = frozenset()

    def declared(self) -> frozenset[str]:
        """Every axis this spec accounts for — crossed or explicitly pinned."""
        return self.axes | frozenset(self.pinned_axes)


# Declarative registry. Key = `<module>:<function>`, matching the way the
# verification contracts name a call site. Adding a classifier here is what
# forces its axis list to EXIST at commit 1; the gate is what forces the list
# to be true.
REGISTRY: dict[str, ClassifierSpec] = {
    "dotfiles_setup.dag_tick:classify": ClassifierSpec(
        module_path="python/src/dotfiles_setup/dag_tick.py",
        function="classify",
        subject_param="node",
        subject_type="Node",
        axes=frozenset({"state", "needs", "queued_prompt", "pid_alive", "tempo"}),
        pinned_axes={
            "state_age_s": (
                "pinned None in the table — an unknown age is never stalled "
                "(`is_stalled`), so WEDGED stays unreachable and staleness "
                "keeps its own dedicated tests"
            ),
            "stall_after_s": (
                "inert while `state_age_s` is pinned None — it is only ever "
                "compared against a non-None age"
            ),
        },
        table_path="tests/test_dag_tick.py",
        table_symbol="_CLASSIFY_TABLE",
        # The table asserts exactly this: `NodeClass.WEDGED not in reached`.
        # It is what makes pinning `state_age_s`/`stall_after_s` legal — they
        # decide nothing else. `tempo` decides DONE too, so it cannot be
        # pinned, which is the round-7 finding made machine-checkable.
        table_excluded_classes=frozenset({"WEDGED"}),
        reason=(
            "#601: `is_needs_human` omitted `queued_prompt` (round 5/6) and "
            "the first truth table omitted `tempo` (round 7) — both axes were "
            "already read by `is_terminal` at the same call site"
        ),
    ),
    "dotfiles_setup.branch_guard:classify": ClassifierSpec(
        module_path="python/src/dotfiles_setup/branch_guard.py",
        function="classify",
        # SUBJECTLESS: no dataclass, no fields — the axes ARE the parameters.
        subject_param=None,
        subject_type=None,
        # `code` and `lines` are both crossed as the FINITE PARTITIONS the code
        # actually reads, not as their raw types. `code: int` is compared
        # against exactly two values (`0` and `_UNRESOLVED_REF_RC`), so it has
        # three equivalence classes; `lines: list[str]` is asked exactly one
        # question (`len(lines) == _COMBINED_FACT_COUNT`, branch_guard.py:226),
        # so it is a BOOLEAN. Neither is pinned, because both are finitely
        # modellable — pinning a modellable axis is the move `illegal_pin`
        # exists to refuse. Same convention `dag_tick` uses for `needs`: the
        # registry names the axis after the parameter, the table crosses the
        # projection the code reads.
        axes=frozenset({"code", "lines"}),
        table_path="tests/test_branch_guard.py",
        table_symbol="_COMBINED_TABLE",
        # Nothing is out of scope: all three classes are reachable from the
        # 3x2 cross product, so an empty exclusion set is the honest value —
        # and it means NO pin could ever be legal here, which is correct.
        table_excluded_classes=frozenset(),
        reason=(
            "found by the `unlisted` scan, not by a human: a second real "
            "classifier with no truth table at all. Its docstring claims the "
            "`code==0 with a wrong line count` case 'cannot be produced by "
            "any real git' — an UNENFORCEABLE claim about an external tool "
            "(no file:line can enforce it), empirically unobserved across 7 "
            "git states on 2.50.1, and enumerated anyway because the branch "
            "exists precisely to survive a future git that breaks it"
        ),
    ),
    "dotfiles_setup.codex_verdict:edge_for": ClassifierSpec(
        module_path="python/src/dotfiles_setup/codex_verdict.py",
        function="edge_for",
        # SUBJECTLESS, like `branch_guard.classify` — the axes ARE the params.
        subject_param=None,
        subject_type=None,
        # ⚠️ `rework_count` and `max_rework` are two PARAMETERS but ONE
        # question: `edge_for` asks `rework_count >= max_rework` and nothing
        # else of either, so neither has a standalone partition — only the PAIR
        # does. The table crosses them as the two sides of that single boolean,
        # the same convention `branch_guard` uses for `lines` (a list asked
        # exactly one question is a boolean), extended to a question about two
        # parameters rather than one. `verdict` is crossed as the enum, all
        # three members. Nothing is pinned: every axis is finitely modellable,
        # and pinning a modellable axis is the move `illegal_pin` refuses.
        axes=frozenset({"verdict", "rework_count", "max_rework"}),
        table_path="tests/test_codex_verdict.py",
        table_symbol="_EDGE_TABLE",
        # `Edge.NONE` is the no-op a reaper returns when there was nothing to
        # decide — never something a verdict maps to. The table asserts its
        # absence explicitly (`test_edge_table_reaches_every_edge_a_verdict_
        # can_produce`), so declaring it out of scope here is a restatement of
        # an assertion, not a licence granted on trust.
        table_excluded_classes=frozenset({"NONE"}),
        reason=(
            "found by the `unlisted` scan on first contact with #580's merge, "
            "not by a human — the third real classifier in the repo, shipped "
            "after this gate was written and caught the moment the two "
            "branches met. `_EDGE_TABLE` already existed; what was missing is "
            "the binding that makes a NEW axis in `edge_for` fail here instead "
            "of silently going unenumerated, which is #601's defect exactly"
        ),
    ),
}

# Where :func:`classifier_shaped` looks for classifiers that OUGHT to be
# registered. A glob, not `git ls-files`, so the scan behaves identically in a
# `tmp_path` fixture as in the repo — `bash_budget` can use git because its
# subject IS tracked files; here the subject is python semantics.
SCAN_GLOB = "python/src/dotfiles_setup/*.py"

# Base classes that make a class an enum for discovery purposes.
_ENUM_BASES: frozenset[str] = frozenset({"Enum", "StrEnum", "IntEnum", "Flag"})


@dataclass(frozen=True)
class AxisViolation:
    """One axis-enumeration breach found by :func:`find_violations`."""

    classifier: str
    kind: str  # undeclared|illegal_pin|phantom|unresolved_subject|stale|table_missing
    detail: str


def _function_defs(tree: ast.AST) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """Every named function in the parsed module, by name."""
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }


def _positional_params(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Positional parameter names, in call order."""
    return [arg.arg for arg in (*fn.args.posonlyargs, *fn.args.args)]


def _all_params(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Every named parameter — positional, keyword-or-positional, kw-only."""
    return [
        arg.arg for arg in (*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs)
    ]


def _annotation_name(annotation: ast.expr | None) -> str | None:
    """The bare name of a simple annotation (`Node`, `dag_tick.Node`)."""
    if isinstance(annotation, ast.Name):
        return annotation.id
    if isinstance(annotation, ast.Attribute):
        return annotation.attr
    return None


def _params_typed_as_subject(
    fn: ast.FunctionDef | ast.AsyncFunctionDef, subject_type: str
) -> set[str]:
    """Parameters annotated with the subject type — subject holders by type.

    Seeding by annotation as well as by call-site dataflow widens the net
    deliberately: a predicate reached as ``pred(build(x))`` passes no bare
    Name, so dataflow alone would miss every field it reads.
    """
    subjects: set[str] = set()
    for arg in (*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs):
        if _annotation_name(arg.annotation) == subject_type:
            subjects.add(arg.arg)
    return subjects


def _is_subject_expr(expr: ast.expr, subjects: frozenset[str]) -> bool:
    """Whether ``expr`` evaluates to the subject itself (not one of its fields).

    Deliberately shallow — a bare name, either arm of a ternary, or any operand
    of a ``or``/``and`` chain. It does NOT try to see through a call, because
    ``n = replace(node, state="x")`` would need real type inference and a guess
    there is worse than a stated hole (see :func:`_subject_aliases`).
    """
    if isinstance(expr, ast.Name):
        return expr.id in subjects
    if isinstance(expr, ast.IfExp):
        return _is_subject_expr(expr.body, subjects) or _is_subject_expr(
            expr.orelse, subjects
        )
    if isinstance(expr, ast.BoolOp):
        return any(_is_subject_expr(value, subjects) for value in expr.values)
    return False


def _bound_by_assignment(
    target: ast.expr, value: ast.expr, subjects: frozenset[str]
) -> set[str]:
    """Names this one ``target = value`` pair binds to the subject."""
    if isinstance(target, ast.Name) and _is_subject_expr(value, subjects):
        return {target.id}
    if isinstance(target, ast.Tuple | ast.List) and isinstance(
        value, ast.Tuple | ast.List
    ):
        # `a, b = node, other` — positional, and only against a LITERAL tuple.
        # `a, b = pair` is unresolvable without evaluating `pair`.
        return {
            element.id
            for element, source in zip(target.elts, value.elts, strict=False)
            if isinstance(element, ast.Name) and _is_subject_expr(source, subjects)
        }
    return set()


def _aliases_bound_by(
    node: ast.AST, subjects: frozenset[str], subject_type: str
) -> set[str]:
    """Names one statement binds to the subject, by any covered assignment form."""
    if isinstance(node, ast.AnnAssign):
        annotated = _annotation_name(node.annotation) == subject_type
        assigned = node.value is not None and _is_subject_expr(node.value, subjects)
        if isinstance(node.target, ast.Name) and (annotated or assigned):
            return {node.target.id}
        return set()
    if isinstance(node, ast.NamedExpr):
        if isinstance(node.target, ast.Name) and _is_subject_expr(node.value, subjects):
            return {node.target.id}
        return set()
    if not isinstance(node, ast.Assign):
        return set()
    bound: set[str] = set()
    for target in node.targets:
        bound |= _bound_by_assignment(target, node.value, subjects)
    return bound


def _subject_aliases(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
    subjects: frozenset[str],
    subject_type: str,
) -> frozenset[str]:
    """Subject-holding names in ``fn``, extended through local rebinding.

    ⚠️ **The failure this closes was not a miss — it was an INVERSION.** A cold
    review added one line, ``n = node``, and rewrote ``node.state`` to
    ``n.state``: the sort of edit a reviewer waves through as "shorter name
    below". :func:`derive_axes` then reported the axes as
    ``['pid_alive', 'stall_after_s', 'state_age_s']`` and raised a ``phantom``
    telling the author to **delete** the ``state``/``tempo``/``needs``/
    ``queued_prompt`` declarations — the exact declarations #601 exists to
    install. A miss is a gap; an instruction to delete the protection, with the
    gate applauding, is a trap.

    Iterated to a fixpoint so an alias chain (``n = node; m = n``) resolves,
    and computed over the WHOLE function body without regard to statement
    order. That over-approximates — a name rebound away from the subject later
    stays a subject here — and over-approximating is the safe direction: it can
    only ADD derived axes, which pushes toward the fail-loud ``undeclared`` and
    away from the delete-instructing ``phantom``.

    **Covered** binding forms: ``n = node``; chained targets (``n = m =
    node``); tuple/list unpacking from a LITERAL tuple (``a, b = node,
    other``); an annotated assignment (``n: Node = ...``, subject by
    annotation OR by value); a walrus (``n := node``); and a ternary or
    ``and``/``or`` whose operand is the subject.

    **NOT covered**, and each is a real hole rather than an oversight:
    unpacking from a non-literal (``a, b = pair``); a call that returns the
    subject without an annotation (``n = replace(node, ...)``); storage into a
    container or attribute (``d["k"] = node``, ``self.n = node``); ``for``/
    ``with`` binding; and ``global``/``nonlocal`` rebinding. Every one needs
    type inference or dataflow this module deliberately does not have — but
    note that a call is caught by the OTHER half of this fix: handing the
    subject to something unresolvable raises ``unresolved_subject``, so
    ``n = replace(node, ...)`` goes red rather than quiet.
    """
    known = set(subjects)
    while True:
        grown = set(known)
        for node in ast.walk(fn):
            grown |= _aliases_bound_by(node, frozenset(known), subject_type)
        if grown == known:
            return frozenset(known)
        known = grown


def _hands_over_subject(expr: ast.expr, subjects: frozenset[str]) -> bool:
    """Whether ``expr`` yields the subject OBJECT rather than one of its fields.

    ``pred(node)`` hands it over — whatever ``pred`` reads is invisible from
    here. ``pred(node.state)`` does not: the field read is recorded at this
    call site, so the callee can hide nothing.
    """
    if isinstance(expr, ast.Name):
        return expr.id in subjects
    if isinstance(expr, ast.Attribute):
        # `node.state` / `node.parent.state` are field chains, not the subject.
        return _hands_over_subject(expr.value, subjects) and not isinstance(
            expr.value, ast.Name
        )
    return any(
        _hands_over_subject(child, subjects)
        for child in ast.iter_child_nodes(expr)
        if isinstance(child, ast.expr)
    )


def _call_hands_over_subject(call: ast.Call, subjects: frozenset[str]) -> bool:
    """Whether any ARGUMENT of ``call`` hands the subject object over."""
    return any(
        _hands_over_subject(argument, subjects)
        for argument in (*call.args, *(kw.value for kw in call.keywords))
    )


def _call_label(call: ast.Call) -> str:
    """A human-locatable name for a call the walk could not follow."""
    return f"{ast.unparse(call.func)}() at line {call.lineno}"


def _subjects_passed_at_call(
    call: ast.Call,
    callee: ast.FunctionDef | ast.AsyncFunctionDef,
    subjects: frozenset[str],
) -> set[str]:
    """Callee parameters that receive a subject-holding name at this call."""
    positional = _positional_params(callee)
    received: set[str] = set()
    for index, arg in enumerate(call.args):
        if isinstance(arg, ast.Name) and arg.id in subjects and index < len(positional):
            received.add(positional[index])
    for keyword in call.keywords:
        if (
            keyword.arg is not None
            and isinstance(keyword.value, ast.Name)
            and keyword.value.id in subjects
        ):
            received.add(keyword.arg)
    return received


@dataclass
class _SubjectWalk:
    """The invariant half of the subject-field walk: module, type, and memo.

    A class rather than six recursion parameters because the walk carries
    four things that never change per call and two that do — and ruff's
    PLR0913 is right that the flat form was unreadable.
    """

    functions: Mapping[str, ast.FunctionDef | ast.AsyncFunctionDef]
    subject_type: str
    seen: set[tuple[str, frozenset[str]]] = field(default_factory=set)
    fields: set[str] = field(default_factory=set)
    unresolved: set[str] = field(default_factory=set)

    def visit(
        self, fn: ast.FunctionDef | ast.AsyncFunctionDef, subjects: frozenset[str]
    ) -> None:
        """Accumulate every ``<subject>.<field>`` read reachable from ``fn``.

        Follows same-module calls transitively — the #601 case was one level
        deep (``classify`` reads ``node.tempo`` at the ``is_terminal`` call
        site), but a predicate that takes the whole node hides its reads one
        frame down, and "it cannot matter here" is the assumption that
        produced this module.

        ``subjects`` is widened by :func:`_subject_aliases` on entry, so a
        local rebinding (``n = node``) keeps its reads attributed instead of
        erasing them.
        """
        subjects = _subject_aliases(fn, subjects, self.subject_type)
        key = (fn.name, subjects)
        if key in self.seen:
            return
        self.seen.add(key)
        for node in ast.walk(fn):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id in subjects
            ):
                self.fields.add(node.attr)
            elif isinstance(node, ast.Call):
                self._follow(node, fn, subjects)
            elif isinstance(node, ast.Assign | ast.AnnAssign | ast.NamedExpr):
                self._check_binding(node, subjects)

    def _check_binding(
        self, node: ast.Assign | ast.AnnAssign | ast.NamedExpr, subjects: frozenset[str]
    ) -> None:
        """Record a binding that STORES the subject somewhere unmodellable.

        The generalisation of the alias fix, rather than a second special case
        for it. :func:`_subject_aliases` covers the binding forms it can prove;
        this is the complement — the subject was handed to a binding and no
        alias came out of it, so it went somewhere the walk cannot follow:
        ``d["k"] = node``, ``self.n = node``, ``pair = (node, x)`` then
        ``n, _ = pair``. Each would otherwise leave the subsequent field reads
        unattributed and put ``phantom`` back into its inverted state via a
        route aliasing never touches.

        ``x = node.state`` is NOT a store of the subject — the field read is
        recorded at this line — which is why the test is
        :func:`_hands_over_subject` and not "mentions the subject".
        """
        if node.value is None or not _hands_over_subject(node.value, subjects):
            return
        if _aliases_bound_by(node, subjects, self.subject_type):
            return
        self.unresolved.add(
            f"the assignment at line {node.lineno} stores the subject in a "
            f"binding the walk cannot model"
        )

    def _follow(
        self,
        call: ast.Call,
        caller: ast.FunctionDef | ast.AsyncFunctionDef,
        subjects: frozenset[str],
    ) -> None:
        """Recurse into a same-module callee, or record that we could not.

        Three outcomes, and the third is the point: a call that is handed the
        subject OBJECT but whose body this module cannot see is recorded in
        :attr:`unresolved`. Cross-module imports, method calls and builtins all
        land there. Silence was the old behaviour and it is not available — an
        unseen callee can read any field, so a derivation taken while one is in
        the dispatch path is not evidence of anything.
        """
        callee = (
            self.functions.get(call.func.id)
            if isinstance(call.func, ast.Name)
            else None
        )
        if callee is None:
            if _call_hands_over_subject(call, subjects):
                self.unresolved.add(_call_label(call))
            return
        if callee is caller:
            return
        inner = _subjects_passed_at_call(call, callee, subjects)
        inner |= _params_typed_as_subject(callee, self.subject_type)
        if inner:
            self.visit(callee, frozenset(inner))
        elif _call_hands_over_subject(call, subjects):
            # The callee IS in this module, but the subject reached it in a
            # form we cannot map to a parameter (`pred(*args)`, `pred(wrap(n))`)
            # — so we still do not know which of its reads are subject reads.
            self.unresolved.add(_call_label(call))


@dataclass(frozen=True)
class DerivedAxes:
    """What the CODE says about one classifier's axes.

    `axes` is the enumeration itself. `gated_classes` maps each axis to the
    classes whose `return` it can decide — the fact that makes a PIN
    checkable rather than a matter of the author's word.

    `unresolved` names every call that was handed the subject OBJECT and whose
    body the walk could not read. It is the derivation's own admission of
    incompleteness, and it is load-bearing: a non-empty `unresolved` means
    `axes` is a LOWER BOUND, so "declared but unread" stops being a sound
    verdict and `phantom` is withheld (:func:`violations_for`).
    """

    axes: frozenset[str]
    gated_classes: Mapping[str, frozenset[str]]
    unresolved: frozenset[str] = frozenset()
    unreadable_decisions: frozenset[str] = frozenset()


@dataclass(frozen=True)
class _ClassNames:
    """How to tell an enum-member reference from an ordinary attribute read.

    ``ast.walk`` cannot distinguish ``NodeClass.DONE`` from ``node.tempo`` —
    both are ``Attribute(value=Name)``. The first version took every one of
    them as a class, which is why a probe reported ``tempo_gates=['DONE',
    'LIVE', 'tempo']``: an AXIS name listed as a CLASS. It failed closed (a
    wider gated set only refuses more pins) so nothing was exploitable, but a
    derivation that is textual where it claims to be semantic will eventually
    be wrong in the other direction.

    `enums` are the enum classes defined in this module. When the module
    defines any — every real classifier does, since :func:`classifier_shaped`
    requires it — a base name must BE one of them. The fallback (exclude
    subjects and parameters) exists only for reduced source fixtures that
    reference a `NodeClass` they never define.
    """

    enums: frozenset[str]
    subjects: frozenset[str]
    params: frozenset[str]
    locals_: Mapping[str, frozenset[str]] = field(default_factory=dict)

    def holds_a_class(self, name: str) -> bool:
        """Whether ``name.<MEMBER>`` names an enum member rather than a field."""
        if self.enums:
            return name in self.enums
        return name not in self.subjects and name not in self.params


def _enum_class_names(tree: ast.AST) -> frozenset[str]:
    """Enum classes defined in this module — the same test as `classifier_shaped`."""
    return frozenset(
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        and any(_annotation_name(base) in _ENUM_BASES for base in node.bases)
    )


def _class_members(expr: ast.expr, names: _ClassNames) -> set[str]:
    """Every enum member ``expr`` can evaluate to.

    Walks INTO the expression rather than requiring a bare ``Enum.MEMBER``, so
    a ternary return yields both arms, and resolves a local that was assigned
    one (``verdict = K.DONE; return verdict``) through ``names.locals_``.
    """
    found: set[str] = set()
    for node in ast.walk(expr):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and names.holds_a_class(node.value.id)
        ):
            found.add(node.attr)
        elif isinstance(node, ast.Name) and node.id in names.locals_:
            found |= names.locals_[node.id]
    return found


def _class_holding_locals(
    fn: ast.FunctionDef | ast.AsyncFunctionDef, names: _ClassNames
) -> dict[str, frozenset[str]]:
    """Locals assigned an enum member, to a fixpoint.

    ``verdict = K.DONE`` then ``return verdict`` is ordinary Python and the
    first version read it as returning NO class — which made the whole
    classifier's gate map empty, and an empty map makes every pin legal.
    """
    bound: dict[str, frozenset[str]] = {}
    while True:
        grown = dict(bound)
        resolved = replace(names, locals_=grown)
        for node in ast.walk(fn):
            if not isinstance(node, ast.Assign | ast.AnnAssign | ast.NamedExpr):
                continue
            if node.value is None:
                continue
            members = _class_members(node.value, resolved)
            if not members:
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    grown[target.id] = grown.get(target.id, frozenset()) | frozenset(
                        members
                    )
        if grown == bound:
            return bound
        bound = grown


def _returns_in(statements: list[ast.stmt]) -> list[ast.Return]:
    """Every ``return`` reachable from these statements."""
    return [
        node
        for statement in statements
        for node in ast.walk(statement)
        if isinstance(node, ast.Return)
    ]


def _classes_returned(statements: list[ast.stmt], names: _ClassNames) -> set[str]:
    """Enum members any ``return`` in these statements can produce."""
    returned: set[str] = set()
    for node in _returns_in(statements):
        if node.value is not None:
            returned |= _class_members(node.value, names)
    return returned


def _ternary_tests(statements: list[ast.stmt]) -> list[ast.expr]:
    """The conditions of any ternary inside these statements' returns.

    An axis can decide a class WITHOUT appearing in the enclosing ``if`` test:
    ``branch_guard.classify`` splits RESOLVED from FALL_BACK on
    ``len(lines) == _COMBINED_FACT_COUNT`` inside the return expression, while
    the ``if`` above it tests only ``code``. Without these, ``lines`` would
    look like an axis that gates nothing — and therefore be pinnable.
    """
    return [
        inner.test
        for node in _returns_in(statements)
        if node.value is not None
        for inner in ast.walk(node.value)
        if isinstance(inner, ast.IfExp)
    ]


def _unreadable_returns(
    classifier: ast.FunctionDef | ast.AsyncFunctionDef, names: _ClassNames
) -> set[str]:
    """Returns whose class this module cannot name — the fail-CLOSED trigger.

    A classifier's every ``return`` yields one of its classes by definition. So
    a return we cannot resolve to an enum member means the decision structure
    is not fully readable — a dict dispatch (``return _M[key]``), a bare
    ``return``, a call's result. When that happens :func:`_illegal_pins`
    refuses EVERY pin, because "I could not read this" must not keep being
    rendered as "nothing gates anything".
    """
    reasons: set[str] = set()
    for node in _returns_in(classifier.body):
        if node.value is None:
            reasons.add(f"the bare `return` at line {node.lineno} names no class")
        elif not _class_members(node.value, names):
            reasons.add(
                f"the return at line {node.lineno} "
                f"(`{ast.unparse(node.value)}`) resolves to no enum member"
            )
    return reasons


def _axes_in_test(
    test: ast.expr,
    subjects: frozenset[str],
    params: frozenset[str],
    walk_source: _SubjectWalk,
) -> set[str]:
    """Every axis an ``if`` test depends on, directly or via a predicate call."""
    found: set[str] = set()
    for node in ast.walk(test):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id in subjects
        ):
            found.add(node.attr)
        elif isinstance(node, ast.Name) and node.id in params:
            found.add(node.id)
        elif isinstance(node, ast.Call):
            callee = (
                walk_source.functions.get(node.func.id)
                if isinstance(node.func, ast.Name)
                else None
            )
            if callee is None:
                if _call_hands_over_subject(node, subjects):
                    walk_source.unresolved.add(_call_label(node))
                continue
            inner = _subjects_passed_at_call(node, callee, subjects)
            inner |= _params_typed_as_subject(callee, walk_source.subject_type)
            if inner:
                # A fresh walk so `fields` reports only THIS test's reads, but
                # sharing `unresolved` — an unfollowable call inside a decision
                # is the one we most need to hear about.
                nested = _SubjectWalk(
                    functions=walk_source.functions,
                    subject_type=walk_source.subject_type,
                    unresolved=walk_source.unresolved,
                )
                nested.visit(callee, frozenset(inner))
                found |= nested.fields
            elif _call_hands_over_subject(node, subjects):
                walk_source.unresolved.add(_call_label(node))
    return found


def _gated_classes(
    classifier: ast.FunctionDef | ast.AsyncFunctionDef,
    subjects: frozenset[str],
    params: frozenset[str],
    walk_source: _SubjectWalk,
    names: _ClassNames,
) -> dict[str, frozenset[str]]:
    """Map each axis to the classes an ``if`` it participates in can return.

    This is what makes a PIN auditable by machine instead of by trust. Round 7
    pinned ``tempo`` on the premise that it "only matters for WEDGED" — a
    premise that was FALSE, because ``is_terminal`` also reads it and gates
    ``DONE``. Nobody checked, and no test could, because the test encoded the
    same premise. This function checks it: the pin is legal only when every
    class the axis can decide is one the table declares out of scope.
    """
    accumulated: dict[str, set[str]] = {}
    for node in ast.walk(classifier):
        decision = _decision_at(node, names)
        if decision is None:
            continue
        classes, tests = decision
        deciding: set[str] = set()
        for test in tests:
            deciding |= _axes_in_test(test, subjects, params, walk_source)
        for axis in deciding:
            accumulated.setdefault(axis, set()).update(classes)
    return {axis: frozenset(classes) for axis, classes in accumulated.items()}


def _decision_at(
    node: ast.AST, names: _ClassNames
) -> tuple[set[str], list[ast.expr]] | None:
    """The classes one branching construct decides, and the tests that decide them.

    ⚠️ **Both arms, or the check is a coin with one face.** The first version
    read only ``branch.body``, so ``if tempo == "active": return WEDGED`` /
    ``else: return DONE`` credited ``tempo`` with WEDGED alone — and a table
    excluding WEDGED then made the pin legal. That is round 7's own false
    premise ("tempo only matters for WEDGED") written with an ``else``, passing
    the check built to refuse it. One syntactic rearrangement of the code the
    gate was derived from.

    ``match`` is read the same way: the subject expression and every ``case``
    guard decide among the classes ALL the case bodies return. Reading only
    ``ast.If`` meant a ``match`` classifier had no decisions at all, hence an
    empty gate map, hence every pin vacuously legal.
    """
    if isinstance(node, ast.If):
        branch = [*node.body, *node.orelse]
        classes = _classes_returned(branch, names)
        return (classes, [node.test, *_ternary_tests(branch)]) if classes else None
    if isinstance(node, ast.Match):
        bodies = [statement for case in node.cases for statement in case.body]
        classes = _classes_returned(bodies, names)
        tests = [
            node.subject,
            *(case.guard for case in node.cases if case.guard is not None),
            *_ternary_tests(bodies),
        ]
        return (classes, tests) if classes else None
    return None


def derive_axes(source: str, spec: ClassifierSpec) -> DerivedAxes | None:
    """The classifier's REAL axis set, read out of the code.

    The post-mortem's definition, verbatim: the union of the classifier's own
    parameters (minus the subject itself) and every subject field read by the
    classifier or by any same-module function it calls, transitively.

    Returns ``None`` when the classifier function is not in this source — the
    caller turns that into a ``stale`` violation rather than a silent pass.
    """
    tree = ast.parse(source)
    functions = _function_defs(tree)
    classifier = functions.get(spec.function)
    if classifier is None:
        return None

    params = {name for name in _all_params(classifier) if name != spec.subject_param}
    if spec.subject_type is None:
        # Subjectless: the axes ARE the parameters. Seeding the walk with an
        # empty subject set would still be correct, but naming that here keeps
        # the two shapes legible.
        subjects: frozenset[str] = frozenset()
    else:
        subjects = frozenset(
            ({spec.subject_param} if spec.subject_param else set())
            | _params_typed_as_subject(classifier, spec.subject_type)
        )
    subject_type = spec.subject_type or ""
    walk = _SubjectWalk(functions=functions, subject_type=subject_type)
    walk.visit(classifier, subjects)
    # The classifier's OWN aliases, so `_gated_classes` sees `n.state` as a
    # subject read too — otherwise the axis set would be fixed while the pin
    # check silently went blind, which is the same bug one layer down.
    aliased = _subject_aliases(classifier, subjects, subject_type)
    names = _ClassNames(
        enums=_enum_class_names(tree), subjects=aliased, params=frozenset(params)
    )
    names = replace(names, locals_=_class_holding_locals(classifier, names))
    gated = _gated_classes(classifier, aliased, frozenset(params), walk, names)
    # Built LAST: `_gated_classes` walks decision tests and can discover an
    # unfollowable call the field walk never reached.
    return DerivedAxes(
        axes=frozenset(params | walk.fields),
        gated_classes=gated,
        unresolved=frozenset(walk.unresolved),
        unreadable_decisions=frozenset(_unreadable_returns(classifier, names)),
    )


def classifier_shaped(source: str) -> set[str]:
    """Function names in ``source`` that RETURN an enum defined in that module.

    The discovery predicate behind the ``unlisted`` kind, and the reason it is
    a gate rather than a heuristic: measured across all 48 modules in
    ``python/src/dotfiles_setup`` it yields **3 hits, all three real
    classifiers, zero false positives** (re-measured 2026-08-07; it was 2
    across 45 when the gate was written). The third arrived on its own:
    ``codex_verdict.edge_for`` shipped after this module did, and the scan
    named it the moment the two branches met — which is exactly what a gate
    that forces the map to GROW is for.

    ⚠️ That third hit also retires a claim the first measurement invited: the
    original two were **both named** ``classify``, and it would have been easy
    to read the predicate as recognising that name. It does not — ``edge_for``
    is not called ``classify``, and it is found anyway, because the only thing
    tested is whether the return annotation names an enum defined in the SAME
    module.

    Deliberately narrow. It does NOT try to recognise a classifier by name, by
    parameter shape, or by returning an enum imported from elsewhere: a
    predicate that misfires on ordinary functions would be worse than no
    predicate, since every false positive demands a registry entry nobody
    wants to write.
    """
    tree = ast.parse(source)
    enums = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        and any(_annotation_name(base) in _ENUM_BASES for base in node.bases)
    }
    if not enums:
        return set()
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and node.returns is not None
        and _annotation_name(node.returns) in enums
    }


def _illegal_pins(
    name: str, spec: ClassifierSpec, derived: DerivedAxes
) -> list[AxisViolation]:
    """Reject a PIN on an axis that decides an in-scope class.

    The blind spot this closes is not hypothetical — it is round 7's exact
    shape one step over. An author who never thought of ``tempo`` writes it
    into neither list and trips ``undeclared``; an author who thinks of it and
    pins it on the FALSE premise "only matters for WEDGED" would otherwise
    pass, and that premise is what round 7 actually shipped, in a comment, a
    commit message and a contract. The premise is checkable: ``tempo`` is read
    by ``is_terminal``, which gates ``DONE``, which the table does NOT exclude.
    """
    violations: list[AxisViolation] = []
    blockers = sorted(derived.unreadable_decisions | derived.unresolved)
    if blockers and spec.pinned_axes:
        # FAIL CLOSED. An unreadable decision structure yields an empty or
        # partial gate map, and the first version rendered that as "this axis
        # gates nothing" — i.e. every pin vacuously legal. Measured across
        # seven return shapes, four allowed the pin, and the worst was
        # `if tempo == "active": return WEDGED / else: return DONE` — round
        # 7's own false premise, rearranged, sailing through the check written
        # to refuse it. `else` and `match` are now READ; anything still
        # unreadable refuses every pin instead of granting them.
        return [
            AxisViolation(
                name,
                "illegal_pin",
                f"no pin is legal here: {sorted(spec.pinned_axes)} are pinned, "
                f"but the decision structure of {spec.function}() cannot be "
                f"fully read — {blockers}. A pin's legality is decided by "
                f"WHICH classes the axis can gate, so an unreadable branch "
                f"means the answer is unknown, and unknown must not read as "
                f"'gates nothing'. Make the returns resolvable (a bare "
                f"`Enum.MEMBER`, a ternary, a local assigned one) and bring "
                f"the predicates into {spec.module_path}, or cross the axis "
                f"instead of pinning it",
            )
        ]
    for axis in sorted(spec.pinned_axes):
        gated = derived.gated_classes.get(axis, frozenset())
        in_scope = sorted(gated - spec.table_excluded_classes)
        if in_scope:
            violations.append(
                AxisViolation(
                    name,
                    "illegal_pin",
                    f"{axis!r} is pinned with the reason "
                    f"{spec.pinned_axes[axis]!r}, but the code lets it decide "
                    f"{in_scope} — classes the table does not declare out of "
                    f"scope (it excludes "
                    f"{sorted(spec.table_excluded_classes)}). Cross it, or "
                    f"widen table_excluded_classes and say why. This is the "
                    f"#601 round-7 defect: `tempo` was pinned as 'only "
                    f"matters for WEDGED' while `is_terminal` read it to "
                    f"decide DONE",
                )
            )
    return violations


def violations_for(
    name: str, spec: ClassifierSpec, derived: DerivedAxes
) -> list[AxisViolation]:
    """Compare one derived axis set against its declaration, both directions."""
    violations: list[AxisViolation] = []
    declared = spec.declared()
    undeclared = sorted(derived.axes - declared)
    if undeclared:
        violations.append(
            AxisViolation(
                name,
                "undeclared",
                f"the code reads {undeclared} but the registry declares neither "
                f"a crossed nor a pinned axis for them — enumerate each in the "
                f"truth table, or PIN it with the reason it is safe to hold "
                f"constant (python/src/dotfiles_setup/classifier_tables.py). "
                f"This is the #601 defect: {spec.reason}",
            )
        )
    unresolved = sorted(derived.unresolved)
    phantom = sorted(declared - derived.axes)
    if unresolved:
        violations.append(
            AxisViolation(
                name,
                "unresolved_subject",
                f"{spec.function}() hands the subject object to {unresolved}, "
                f"which this module cannot read (imported from another module, "
                f"a method, or a builtin). Every field those calls read is "
                f"invisible, so the derived axis set {sorted(derived.axes)} is "
                f"a LOWER BOUND, not an enumeration. Move the predicate into "
                f"{spec.module_path}, or pass the fields it needs instead of "
                f"the whole subject (`pred(node.state)` is fully derivable, "
                f"`pred(node)` is not)"
                + (
                    f". `phantom` was WITHHELD for {phantom} because of this — "
                    f"'declared but unread' is only sound when the walk saw "
                    f"everything"
                    if phantom
                    else ""
                ),
            )
        )
    elif phantom:
        # Suppressed above on purpose. `phantom` is the only kind that
        # instructs a DELETION, so it is the only one whose false positive
        # actively destroys protection rather than merely annoying someone:
        # an incomplete walk reporting "nothing reads these" tells the author
        # to strip the exact declarations the gate exists to install. A cold
        # review reproduced precisely that on the #601 commit-1 fixture with a
        # one-line `n = node` added. Aliasing is now followed; a call we cannot
        # follow is not, so it withholds the verdict instead of inverting it.
        violations.append(
            AxisViolation(
                name,
                "phantom",
                f"the registry declares {phantom} but no parameter or subject "
                f"field of {spec.function}() reads them any more — drop the "
                f"stale declaration (and the table column it justifies)",
            )
        )
    violations.extend(_illegal_pins(name, spec, derived))
    return violations


def _binds_symbol(source: str, symbol: str) -> bool:
    """Whether ``source`` actually ASSIGNS ``symbol``, not merely mentions it.

    ``symbol not in source`` was a plain substring test, so a COMMENT naming
    the table satisfied it — control-armed both ways: a file containing only
    ``# the _CLASSIFY_TABLE used to live here`` produced no violation, while
    deleting the mention produced ``table_missing``. That is the same
    unanchored-substring shape #601's v1 review filed against `per_path_tokens`,
    reproduced inside the gate written to answer that review.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign | ast.NamedExpr):
            targets = [node.target]
        if any(
            isinstance(target, ast.Name) and target.id == symbol for target in targets
        ):
            return True
    return False


def find_unlisted(repo_root: Path) -> list[AxisViolation]:
    """Classifier-shaped functions with NO :data:`REGISTRY` entry.

    The mechanism ``bash_budget``'s allowlist has and the first version of this
    module lacked: **the map must be forced to GROW.** Five kinds that all
    presuppose an entry cannot see a classifier nobody registered, so the gate
    would have guarded exactly one call site forever — which was the standing
    objection to Fix 7, and it was correct.

    It is not a hypothetical. Running :func:`classifier_shaped` over all 45
    modules found `branch_guard.classify` — a real second classifier with no
    truth table at all — and zero false positives.
    """
    violations: list[AxisViolation] = []
    registered = {(spec.module_path, spec.function) for spec in REGISTRY.values()}
    for module_file in sorted(repo_root.glob(SCAN_GLOB)):
        rel = module_file.relative_to(repo_root).as_posix()
        try:
            source = module_file.read_text()
        except OSError:
            continue
        try:
            shaped = classifier_shaped(source)
        except SyntaxError:
            continue
        violations.extend(
            AxisViolation(
                f"{rel}:{fn}",
                "unlisted",
                f"{fn}() returns an enum defined in {rel} — it is a "
                f"classifier, and it has no REGISTRY entry, so nothing forces "
                f"its axes to be enumerated. Add one in "
                f"python/src/dotfiles_setup/classifier_tables.py (that is how "
                f"#601's defect class is caught at commit 1), or if it "
                f"genuinely is not a classifier, narrow classifier_shaped()",
            )
            for fn in sorted(shaped)
            if (rel, fn) not in registered
        )
    return violations


def find_violations(repo_root: Path) -> list[AxisViolation]:
    """Return every axis-enumeration breach across :data:`REGISTRY`.

    Seven failure kinds:

    - ``unlisted`` — a classifier-shaped function with no registry entry at
      all. The kind that makes the map GROW; see :func:`find_unlisted`.
    - ``undeclared`` — an axis the code reads that the registry accounts for
      neither as crossed nor as pinned. **This is the #601 defect.**
    - ``illegal_pin`` — an axis PINNED although the code lets it decide a
      class the table does not declare out of scope. **This is #601's round-7
      defect** — the shape ``undeclared`` alone misses, because an author who
      names the axis and pins it on a false premise satisfies the first check.
    - ``phantom`` — a declared axis the code no longer reads. **Withheld
      whenever ``unresolved_subject`` fires**, because it is the only kind that
      instructs a deletion and an incomplete walk must not instruct one.
    - ``unresolved_subject`` — the classifier hands the subject object to
      something this module cannot read, so the derivation is a lower bound
      rather than an enumeration.
    - ``stale`` — a registry entry whose module or function no longer exists,
      so the map cannot rot after a rename (same spirit as
      ``bash_budget``'s ``stale`` kind).
    - ``table_missing`` — the declared truth-table symbol is gone from its
      file, so the declaration guards nothing.
    """
    violations: list[AxisViolation] = find_unlisted(repo_root)
    for name, spec in sorted(REGISTRY.items()):
        module_file = repo_root / spec.module_path
        try:
            source = module_file.read_text()
        except OSError:
            violations.append(
                AxisViolation(
                    name,
                    "stale",
                    f"{spec.module_path} is unreadable/missing — remove or "
                    f"repoint the REGISTRY entry",
                )
            )
            continue
        derived = derive_axes(source, spec)
        if derived is None:
            violations.append(
                AxisViolation(
                    name,
                    "stale",
                    f"{spec.function}() no longer exists in {spec.module_path} "
                    f"— remove or repoint the REGISTRY entry",
                )
            )
            continue
        violations.extend(violations_for(name, spec, derived))

        table_file = repo_root / spec.table_path
        try:
            table_source = table_file.read_text()
        except OSError:
            table_source = ""
        if not _binds_symbol(table_source, spec.table_symbol):
            violations.append(
                AxisViolation(
                    name,
                    "table_missing",
                    f"{spec.table_path} does not ASSIGN {spec.table_symbol} — "
                    f"the declared axes guard nothing without the table that "
                    f"crosses them (a comment or a docstring naming the symbol "
                    f"does not count; it used to)",
                )
            )
    return violations


def classifier_axes_main(repo_root: Path) -> int:
    """CLI entry: report violations to stderr; exit 1 if any, else 0."""
    violations = find_violations(repo_root)
    if violations:
        for violation in violations:
            logger.error(
                "classifier-axes %s: %s — %s",
                violation.kind,
                violation.classifier,
                violation.detail,
            )
        return 1
    logger.info(
        "classifier-axes OK: %d registered classifier(s) whose declared axes "
        "match the code, and no unregistered classifier-shaped function",
        len(REGISTRY),
    )
    return 0
