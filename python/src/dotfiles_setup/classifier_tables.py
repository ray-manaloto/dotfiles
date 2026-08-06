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

Applied at commit 1 that names ``queued_prompt`` — because ``is_terminal``
already read it — and it names ``tempo`` for the same reason. Both defects
die at commit 1 instead of at rounds 5, 6 and 7.

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
from dataclasses import dataclass, field
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
    kind: str  # undeclared|illegal_pin|phantom|stale|table_missing
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

    def visit(
        self, fn: ast.FunctionDef | ast.AsyncFunctionDef, subjects: frozenset[str]
    ) -> None:
        """Accumulate every ``<subject>.<field>`` read reachable from ``fn``.

        Follows same-module calls transitively — the #601 case was one level
        deep (``classify`` reads ``node.tempo`` at the ``is_terminal`` call
        site), but a predicate that takes the whole node hides its reads one
        frame down, and "it cannot matter here" is the assumption that
        produced this module.
        """
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
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self._follow(node, fn, subjects)

    def _follow(
        self,
        call: ast.Call,
        caller: ast.FunctionDef | ast.AsyncFunctionDef,
        subjects: frozenset[str],
    ) -> None:
        """Recurse into a same-module callee that receives or types a subject."""
        if not isinstance(call.func, ast.Name):
            return
        callee = self.functions.get(call.func.id)
        if callee is None or callee is caller:
            return
        inner = _subjects_passed_at_call(call, callee, subjects)
        inner |= _params_typed_as_subject(callee, self.subject_type)
        if inner:
            self.visit(callee, frozenset(inner))


@dataclass(frozen=True)
class DerivedAxes:
    """What the CODE says about one classifier's axes.

    `axes` is the enumeration itself. `gated_classes` maps each axis to the
    classes whose `return` it can decide — the fact that makes a PIN
    checkable rather than a matter of the author's word.
    """

    axes: frozenset[str]
    gated_classes: Mapping[str, frozenset[str]]


def _returned_classes(branch: ast.If) -> set[str]:
    """Enum members returned inside an ``if`` branch (not its ``else``).

    Walks INTO each return expression rather than requiring it to be a bare
    ``Enum.MEMBER``, so a ternary return — ``return A if cond else B``, which
    is how ``branch_guard.classify`` picks between RESOLVED and FALL_BACK —
    yields both members instead of none. Requiring the bare form made
    :func:`_gated_classes` return an EMPTY map for that classifier, and an
    empty map makes every pin vacuously legal: the check would have failed
    OPEN on the second classifier registered.
    """
    returned: set[str] = set()
    for statement in branch.body:
        for node in ast.walk(statement):
            if not isinstance(node, ast.Return) or node.value is None:
                continue
            for inner in ast.walk(node.value):
                if isinstance(inner, ast.Attribute) and isinstance(
                    inner.value, ast.Name
                ):
                    returned.add(inner.attr)
    return returned


def _ternary_tests(branch: ast.If) -> list[ast.expr]:
    """The conditions of any ternary inside this branch's returns.

    An axis can decide a class WITHOUT appearing in the enclosing ``if`` test:
    ``branch_guard.classify`` splits RESOLVED from FALL_BACK on
    ``len(lines) == _COMBINED_FACT_COUNT`` inside the return expression, while
    the ``if`` above it tests only ``code``. Without these, ``lines`` would
    look like an axis that gates nothing — and therefore be pinnable.
    """
    tests: list[ast.expr] = []
    for statement in branch.body:
        for node in ast.walk(statement):
            if isinstance(node, ast.Return) and node.value is not None:
                tests.extend(
                    inner.test
                    for inner in ast.walk(node.value)
                    if isinstance(inner, ast.IfExp)
                )
    return tests


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
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            callee = walk_source.functions.get(node.func.id)
            if callee is None:
                continue
            inner = _subjects_passed_at_call(node, callee, subjects)
            inner |= _params_typed_as_subject(callee, walk_source.subject_type)
            if inner:
                nested = _SubjectWalk(
                    functions=walk_source.functions,
                    subject_type=walk_source.subject_type,
                )
                nested.visit(callee, frozenset(inner))
                found |= nested.fields
    return found


def _gated_classes(
    classifier: ast.FunctionDef | ast.AsyncFunctionDef,
    subjects: frozenset[str],
    params: frozenset[str],
    walk_source: _SubjectWalk,
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
        if not isinstance(node, ast.If):
            continue
        classes = _returned_classes(node)
        if not classes:
            continue
        deciding: set[str] = set()
        for test in (node.test, *_ternary_tests(node)):
            deciding |= _axes_in_test(test, subjects, params, walk_source)
        for axis in deciding:
            accumulated.setdefault(axis, set()).update(classes)
    return {axis: frozenset(classes) for axis, classes in accumulated.items()}


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
    walk = _SubjectWalk(functions=functions, subject_type=spec.subject_type or "")
    walk.visit(classifier, subjects)
    return DerivedAxes(
        axes=frozenset(params | walk.fields),
        gated_classes=_gated_classes(classifier, subjects, frozenset(params), walk),
    )


def classifier_shaped(source: str) -> set[str]:
    """Function names in ``source`` that RETURN an enum defined in that module.

    The discovery predicate behind the ``unlisted`` kind, and the reason it is
    a gate rather than a heuristic: measured across all 45 modules in
    ``python/src/dotfiles_setup`` it yields **2 hits, both real classifiers,
    zero false positives** — because this repo's own style is a pure
    ``classify`` returning a module-local enum, split out for testability.

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
    phantom = sorted(declared - derived.axes)
    if phantom:
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

    Six failure kinds:

    - ``unlisted`` — a classifier-shaped function with no registry entry at
      all. The kind that makes the map GROW; see :func:`find_unlisted`.
    - ``undeclared`` — an axis the code reads that the registry accounts for
      neither as crossed nor as pinned. **This is the #601 defect.**
    - ``illegal_pin`` — an axis PINNED although the code lets it decide a
      class the table does not declare out of scope. **This is #601's round-7
      defect** — the shape ``undeclared`` alone misses, because an author who
      names the axis and pins it on a false premise satisfies the first check.
    - ``phantom`` — a declared axis the code no longer reads.
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
        if spec.table_symbol not in table_source:
            violations.append(
                AxisViolation(
                    name,
                    "table_missing",
                    f"{spec.table_symbol} is not in {spec.table_path} — the "
                    f"declared axes guard nothing without the table that "
                    f"crosses them",
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
