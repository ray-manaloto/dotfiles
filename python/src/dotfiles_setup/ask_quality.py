"""Quality gate for ``AskUserQuestion`` calls (PreToolUse).

Ray's standing instruction (2026-08-02): *"always use the AskUserQuestion tool
with recommendation based on cited research and pros/cons and the ability to
answer as free form text if the multiple options are not sufficient"*.

Three of those four are enforceable here; the fourth needs no enforcement:

===============  ==========================================================
Component        How it is carried
===============  ==========================================================
the TOOL         Not gateable — no hook can observe an ask that never
                 happened. Carried by ``.claude/rules/clarify-before-acting``
                 and the ``feedback_clarify_before_acting`` memory.
recommendation   **Gated** — a single-select question leads with a
                 ``(Recommended)`` option and no other option claims it.
pros/cons        **Gated** — every option description carries ``PRO:``
                 and ``CON:``.
cited research   **Gated** — each question carries a citation marker (a
                 backticked path, a ``#NNN`` issue ref, or a URL), or the
                 explicit ``[no prior evidence]`` escape.
free-form text   Nothing to enforce: the harness always offers "Other".
===============  ==========================================================

The escape exists because Ray ruled *"cite what exists; label it when thin"* —
a recommendation must not be blocked for want of evidence, only for hiding that
it has none. **If ``[no prior evidence]`` starts showing up routinely, the gate
has been defeated rather than satisfied** — that was the named risk when the
strictest tier was chosen, and it is a thing to audit, not a thing to reach for.

Why a gate at all, when this is judgment-shaped: the same standard has now
drifted three times (2026-06-29 → 2026-07-30-e → 2026-08-02), and
``.claude/rules/mise-tasks-only.md`` records that markdown alone is "relying on
the LLM, never the only layer". What a hook *can* see is the shape of an ask
that did happen, so that is exactly what this checks — never whether asking was
the right call.

Deliberately NOT gated: whether the recommendation is *good*, whether the
citation is *relevant*, or whether the cons are honest. Those are review, not
lint.

Harness contract — every line below is from the vendor's own docs, on disk in the
knowledge-base's offline claude-code tree, cited here as ``$CC`` (see
``.claude/rules/research-doc-sources.md`` step 00 for the path), and confirmed by
a live probe on 2026-08-02:

- ``$CC/hooks.md:1394`` lists ``AskUserQuestion`` **by name** among PreToolUse
  matcher values, and ``$CC/hooks.md:246`` states the matcher runs against
  ``tool_name``. So the dispatch in :func:`hook_guard.decide_payload` is the
  documented seam, not a guess.
- ``$CC/settings.md:177``: Claude Code watches settings files and reloads them,
  and *"this includes ``permissions``, ``hooks``"* — so a matcher edit takes
  effect **without a restart**. (``$CC/hooks.md:616`` says the same for hooks
  specifically.) The gate went live in the session that wrote it.
- ``$CC/hooks.md:1544`` PreToolUse decision control: ``"deny"`` **prevents the tool
  call**, and ``permissionDecisionReason`` for a deny is *"shown to Claude"*.
  That is what makes this gate usable rather than merely obstructive — the
  reason below is the revision instruction, and the user never sees the
  rejected ask.
- The payload shape this module reads (``questions[].question`` / ``header`` /
  ``multiSelect`` / ``options[].label`` / ``description`` / ``preview``) is the
  documented one: ``$CC/hooks.md:1523`` and
  ``$CC/agent-sdk__python.md:2560``.

⚠️ ``$CC/hooks.md:1529``'s own example option is ``{"label": "React"}`` — no
description — so the vendor's illustrative snippet would fail this gate. That is
fine and deliberate: the SDK schema documents ``description`` as a plain ``str``
(not optional), and this is a project standard that is stricter than the tool's
minimum. Do not "fix" the gate to match the snippet.

**Live probe, 2026-08-02** — an otherwise-compliant ask with the citation
removed was DENIED through the real wired path, the reason naming exactly that
one rule (so the recommendation and PRO:/CON: checks passed in the same run) and
the question never reaching the user. Both arms in one call.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

RECOMMENDED_MARKER = "(Recommended)"
PRO_MARKER = "PRO:"
CON_MARKER = "CON:"
NO_EVIDENCE_ESCAPE = "[no prior evidence]"

#: A backticked path-ish token (``hk.pkl``, ``.claude/rules/x.md``), a ``#NNN``
#: issue reference, or a URL. Deliberately permissive: this pattern gates the
#: ALLOW direction, so a false positive only weakens the gate, while a false
#: negative would block a legitimate ask.
_CITATION_RE = re.compile(r"`[^`\n]*[./][^`\n]*`|#\d+|https?://\S")

_DOC = ".claude/rules/clarify-before-acting.md"


# The payload is untrusted JSON, so every accessor takes ``object`` and narrows
# on the way in. Annotating these as ``Mapping[str, object]`` does not type-check:
# ``Mapping`` is INVARIANT in its key type, so ``isinstance(x, Mapping)`` narrows
# only to ``Mapping[Unknown, object]`` and will not pass as a str-keyed mapping.
# Taking ``object`` is also the more honest signature — nothing here has proved
# the keys are strings.
def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _field(obj: object, key: str) -> object:
    """One field of a JSON object, or None when ``obj`` is not one."""
    return obj.get(key) if isinstance(obj, Mapping) else None


def _options(question: object) -> list[object]:
    raw = _field(question, "options")
    if not isinstance(raw, Sequence) or isinstance(raw, str | bytes):
        return []
    return [opt for opt in raw if isinstance(opt, Mapping)]


def _citation_corpus(question: object) -> str:
    parts = [_text(_field(question, "question")), _text(_field(question, "header"))]
    for opt in _options(question):
        parts.append(_text(_field(opt, "description")))
        parts.append(_text(_field(opt, "preview")))
    return "\n".join(parts)


def _check_question(index: int, question: object) -> list[str]:
    """Violations for one question, as actionable sentences."""
    where = f"question {index + 1}"
    options = _options(question)
    if not options:
        # Nothing to judge — the tool's own schema requires 2-4 options, so an
        # empty list means a shape this gate does not understand. Allow.
        return []

    out: list[str] = []

    missing_desc = [
        i + 1
        for i, opt in enumerate(options)
        if not _text(_field(opt, "description")).strip()
    ]
    if missing_desc:
        out.append(
            f"{where}: option(s) {missing_desc} have no description. "
            "Every option must say what it means and what happens if chosen."
        )

    thin = [
        i + 1
        for i, opt in enumerate(options)
        if _text(_field(opt, "description")).strip()
        and not (
            PRO_MARKER in _text(_field(opt, "description"))
            and CON_MARKER in _text(_field(opt, "description"))
        )
    ]
    if thin:
        out.append(
            f"{where}: option(s) {thin} give no trade-off. Each description must "
            f"contain both {PRO_MARKER!r} and {CON_MARKER!r} — an option with no "
            "stated downside is a recommendation in disguise."
        )

    if not _field(question, "multiSelect"):
        labels = [_text(_field(opt, "label")) for opt in options]
        claimed = [
            i + 1 for i, label in enumerate(labels) if RECOMMENDED_MARKER in label
        ]
        if not claimed:
            out.append(
                f"{where}: no option is marked {RECOMMENDED_MARKER!r}. Lead with the "
                "option you would pick — enumerating without recommending pushes the "
                "judgment back onto the user."
            )
        elif claimed != [1]:
            out.append(
                f"{where}: {RECOMMENDED_MARKER!r} is on option(s) {claimed}; it "
                "must be on exactly one option, and that option must be FIRST."
            )

    corpus = _citation_corpus(question)
    if NO_EVIDENCE_ESCAPE not in corpus and not _CITATION_RE.search(corpus):
        out.append(
            f"{where}: no citation. Ground the recommendation in something readable — "
            "a `backticked/path`, a #NNN issue/PR ref, or a URL. If there genuinely is "
            f"no prior evidence, say so with the literal {NO_EVIDENCE_ESCAPE!r} "
            "(and treat needing it as a signal to go look first)."
        )

    return out


def find_violations(tool_input: Mapping[str, object]) -> list[str]:
    """Every quality violation in an ``AskUserQuestion`` payload.

    Args:
        tool_input: The hook's ``tool_input`` object for the pending call.

    Returns:
        Actionable violation sentences; empty when the ask is compliant.
        An unrecognised shape yields no violations — this gate must never
        brick an ask it cannot parse.
    """
    questions = _field(tool_input, "questions")
    if not isinstance(questions, Sequence) or isinstance(questions, str | bytes):
        return []
    out: list[str] = []
    for index, question in enumerate(questions):
        if isinstance(question, Mapping):
            out.extend(_check_question(index, question))
    return out


def decide(tool_input: Mapping[str, object]) -> str | None:
    """Deny reason for an ``AskUserQuestion`` call, or None to allow."""
    violations = find_violations(tool_input)
    if not violations:
        return None
    bullets = "\n".join(f"  - {v}" for v in violations)
    return (
        "This ask does not meet the project's AskUserQuestion standard "
        f"(Ray, 2026-08-02; {_DOC}):\n"
        f"{bullets}\n"
        "Revise and re-ask — do NOT fall back to listing the options in prose, "
        "which costs the user a round-trip and is what this standard exists to stop."
    )
