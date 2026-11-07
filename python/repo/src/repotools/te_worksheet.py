"""repotools te-review report: the owner's worksheet, checked against the evidence and counted."""

import math
from collections import Counter
from datetime import datetime
from pathlib import Path

from .models import (
    AbortCounts,
    AbOutcome,
    AbReceipt,
    Collection,
    ConfigSetting,
    Decision,
    DecisionLine,
    EnvfactsEnum,
    ErrorCode,
    Evidence,
    EvidenceGap,
    EvidenceReceipt,
    FactCandidate,
    FactVerdict,
    FollowUpEnum,
    ImportCompletion,
    ImportCounts,
    ImportCoverage,
    ImportEntry,
    ImportOperations,
    ImportVerdict,
    LearnedFactCounts,
    McpResult,
    NotRunCounts,
    NotRunOutcome,
    OverheadKey,
    OwnerAssessment,
    PaidFactCounts,
    ReceiptKind,
    RedirectCandidate,
    RedirectCounts,
    RedirectState,
    RedirectVerdict,
    Review,
    RowKind,
    Section,
    Worksheet,
    WorksheetAbort,
    WorksheetFact,
    WorksheetImport,
    WorksheetNotRun,
    WorksheetPaidFact,
    WorksheetRedirect,
)
from .te_io import TeReviewError, absolute
from .te_judgment import worksheet

# spec.md user story 5: with no useful paid fact the review selects this setting.
ENVFACTS = ConfigSetting(key="microskills", value="envfacts")
USES = (ReceiptKind.fact_injection, ReceiptKind.fact_use)


def bad(error: str) -> TeReviewError:
    return TeReviewError(ErrorCode.BAD_WORKSHEET, error)


def read(folder: Path, given: str | None) -> Worksheet:
    """The worksheet given, else the collection's own, as its model."""
    path = absolute("worksheet", folder / "worksheet.json" if given is None else given, "the worksheet's")
    try:
        data = path.read_bytes()
    except OSError:
        raise TeReviewError(ErrorCode.NO_WORKSHEET, f"{path} cannot be read") from None
    try:
        return Worksheet.model_validate_json(data)
    # Not JSON, or not the worksheet: a bad enum value, a missing or unknown key (ValidationError, a ValueError).
    except ValueError as error:
        msg = f"{path}: {error}"
        raise bad(msg) from None


def matched[E: (WorksheetRedirect, WorksheetAbort, WorksheetPaidFact, WorksheetFact, WorksheetImport, WorksheetNotRun)](
    section: str, given: list[E], template: list[E]
) -> list[E]:
    """Each template entry as the owner filled it; one left out stays as the template has it, NOT_REVIEWED."""
    expected = {entry.ref: entry for entry in template}
    filled: dict[str, E] = {}
    for entry in given:
        ref, digest = entry.ref, entry.digest
        if ref in filled:
            msg = f"{section}: {ref} is judged twice"
            raise bad(msg)
        if ref not in expected:
            msg = f"{section}: {ref} is not one of this section's candidates in the evidence"
            raise TeReviewError(ErrorCode.UNKNOWN_REF, msg)
        if digest != expected[ref].digest:
            msg = f"{section}: {ref} was judged on other content"
            raise TeReviewError(ErrorCode.STALE_WORKSHEET, msg)
        filled[ref] = entry
    return [filled.get(ref, entry) for ref, entry in expected.items()]


class Refs:
    """Every ref the evidence holds, and the receipts and candidates by ref.

    Not a model: it holds no data of its own, only lookups into the generated Evidence it is built from, and
    is never read or written as JSON; pydantic takes Evidence as it is and has no index to give by ref.
    """

    def __init__(self, evidence: Evidence) -> None:
        self.rows = {row.ref: row for row in evidence.rows}
        self.receipts = {receipt.ref: receipt for receipt in evidence.receipts}
        self.redirects = {found.ref: found for found in evidence.redirects}
        self.facts = {found.ref: found for found in evidence.facts}
        self.imports = {found.ref: found.receipts for found in evidence.imports}
        self.imports |= {found.ref: found.receipts for found in evidence.import_folds}
        self.every = {*self.rows, *self.receipts, *self.redirects, *self.facts, *self.imports}

    def known(self, section: str, ref: str | None) -> str | None:
        if ref is not None and ref not in self.every:
            msg = f"{section}: {ref} is not in the evidence"
            raise TeReviewError(ErrorCode.UNKNOWN_REF, msg)
        return ref


def delivered(section: str, entry: WorksheetRedirect | WorksheetAbort, found: RedirectCandidate, refs: Refs) -> bool:
    """delivery_confirmed with one of its own host_delivery receipts; a shadow event stays undeliverable."""
    shadow = RedirectState.shadow_suppressed
    if (entry.state is shadow) != (found.state is shadow):
        msg = f"{section}: {entry.ref} is {found.state} in the evidence"
        raise bad(msg)
    receipt = refs.known(section, entry.receipt_ref)
    if receipt is not None and receipt not in found.receipts:
        msg = f"{section}: {receipt} is not a host_delivery receipt of {entry.ref}"
        raise bad(msg)
    confirmed = entry.state is RedirectState.delivery_confirmed
    if confirmed and receipt is None:
        msg = f"{section}: {entry.ref} is delivery_confirmed without its host_delivery receipt"
        raise bad(msg)
    judged = [entry.verdict, entry.like_128 if isinstance(entry, WorksheetRedirect) else None]
    if not confirmed and any(value is not None for value in judged):
        msg = f"{section}: {entry.ref} is judged but not delivered"
        raise bad(msg)
    return confirmed


def redirects(entries: list[WorksheetRedirect], refs: Refs) -> RedirectCounts:
    shown = [entry for entry in entries if delivered("redirects", entry, refs.redirects[entry.ref], refs)]
    states = Counter(entry.state for entry in entries)
    verdicts = Counter(entry.verdict for entry in shown)
    like = Counter(entry.like_128 for entry in shown)
    return RedirectCounts(
        delivered=len(shown),
        delivery_unknown=states[RedirectState.delivery_unknown],
        shadow_suppressed=states[RedirectState.shadow_suppressed],
        right=verdicts[RedirectVerdict.right],
        wrong=verdicts[RedirectVerdict.wrong],
        unjudged=verdicts[RedirectVerdict.unjudged],
        not_reviewed=verdicts[None],
        like_128=like[True],
        not_like_128=like[False],
        like_128_not_reviewed=like[None],
    )


def aborts(entries: list[WorksheetAbort], refs: Refs) -> AbortCounts:
    shown = [entry for entry in entries if delivered("aborts", entry, refs.redirects[entry.ref], refs)]
    states = Counter(entry.state for entry in entries)
    verdicts = Counter(entry.verdict for entry in shown)
    return AbortCounts(
        aborts=len(entries),
        delivery_confirmed=len(shown),
        delivery_unknown=states[RedirectState.delivery_unknown],
        shadow_suppressed=states[RedirectState.shadow_suppressed],
        right=verdicts[RedirectVerdict.right],
        wrong=verdicts[RedirectVerdict.wrong],
        unjudged=verdicts[RedirectVerdict.unjudged],
        not_reviewed=verdicts[None],
    )


def first_snapshot(found: FactCandidate, refs: Refs, collection: Collection) -> datetime:
    """When the fact first appears: its earliest fact_snapshot receipt, else the collection's own snapshot."""
    times = [
        refs.receipts[ref].timestamp for ref in found.receipts if refs.receipts[ref].kind is ReceiptKind.fact_snapshot
    ]
    return min(times, default=collection.collected_at)


def positive(value: object) -> float | None:
    """A finite number above zero, else None."""
    if isinstance(value, bool) or not isinstance(value, int | float) or not 0 < value < math.inf:
        return None
    return float(value)


# D8b: when a charge was made; a fold writes a session's own optimizer charge into its session row.
CHARGED = {RowKind.overhead: "at", RowKind.session: "folded_at"}


def useful(entry: WorksheetPaidFact, refs: Refs, collection: Collection) -> None:
    """D8: an optimizer charge of the fact's store, charged before the fact first appears, and a use receipt."""
    found = refs.facts[entry.ref]
    origin = refs.rows.get(entry.origin_ref or "")
    charged = positive(origin.row.get(CHARGED[origin.kind])) if origin else None
    if (
        origin is None
        or origin.store != found.store
        or positive((origin.row.get("overhead") or {}).get(OverheadKey.optimizer_tokens)) is None
        or charged is None
        or charged >= first_snapshot(found, refs, collection).timestamp()
    ):
        msg = f"paid_facts: {entry.ref} is useful without an optimizer charge of its store before it first appears"
        raise bad(msg)
    use = refs.receipts.get(entry.use_ref or "")
    if use is None or use.kind not in USES or use.ref not in found.receipts:
        msg = f"paid_facts: {entry.ref} is useful without its fact_injection or fact_use receipt"
        raise bad(msg)


def paid_facts(entries: list[WorksheetPaidFact], refs: Refs, collection: Collection) -> PaidFactCounts:
    for entry in entries:
        if (entry.owner_assessment is None) != (entry.reason is None):
            msg = f"paid_facts: {entry.ref} needs both an assessment and its reason, or neither"
            raise bad(msg)
        refs.known("paid_facts", entry.origin_ref)
        refs.known("paid_facts", entry.use_ref)
        if entry.owner_assessment is OwnerAssessment.useful:
            useful(entry, refs, collection)
    assessed = Counter(entry.owner_assessment for entry in entries)
    return PaidFactCounts(
        useful=assessed[OwnerAssessment.useful],
        not_useful=assessed[OwnerAssessment.not_useful],
        unknown=assessed[OwnerAssessment.unknown],
        not_reviewed=assessed[None],
        origin="owner-asserted",
    )


def imports(
    entries: list[WorksheetImport], template: list[WorksheetImport], refs: Refs, evidence: Evidence
) -> ImportCounts:
    """Section 4 by verdict, and (D13) its import operations by completion beside the collection's import note."""
    kinds = {entry.ref: entry.entry for entry in template}
    for entry in entries:
        receipt = refs.known("imports", entry.receipt_ref)
        if entry.entry is not kinds[entry.ref]:
            msg = f"imports: {entry.ref} is {kinds[entry.ref]} in the evidence"
            raise bad(msg)
        if entry.verdict is ImportVerdict.proven and receipt not in refs.imports[entry.ref]:
            msg = f"imports: {entry.ref} is proven without its history_fold receipt"
            raise bad(msg)
    verdicts = Counter(entry.verdict for entry in entries)
    listed = {entry.ref for entry in template if entry.entry is not ImportEntry.fold}
    completion = Counter(found.completion for found in evidence.imports if found.ref in listed)
    return ImportCounts(
        proven=verdicts[ImportVerdict.proven],
        candidate=verdicts[ImportVerdict.candidate],
        unknown=verdicts[ImportVerdict.unknown],
        not_reviewed=verdicts[None],
        operations=ImportOperations(
            completed=completion[ImportCompletion.completed],
            partial=completion[ImportCompletion.partial],
            unknown=completion[ImportCompletion.unknown],
        ),
        note=evidence.import_note,
    )


def ab(receipt: EvidenceReceipt, folder: Path, refs: Refs) -> McpResult:
    """D8: qualified only when the file is an A/B of named sessions and the denies lower the first request;
    D8a: a file that is not the A/B is refused."""
    try:
        # strict: a count must be a JSON integer, so false, "0" or 1000.0 is not turned into one.
        shown = AbReceipt.model_validate_json((folder / "sources" / receipt.path).read_bytes(), strict=True)
    # D8a: not JSON or not the A/B's shape (ValidationError, a ValueError) is a BAD_RECEIPT refusal.
    except ValueError as error:
        msg = f"mcp_ab: receipt {receipt.ref} is not an A/B: {error}"
        raise TeReviewError(ErrorCode.BAD_RECEIPT, msg) from None
    named = {refs.rows[ref].session_id for ref in receipt.links if ref in refs.rows}
    without, with_denies = shown.without_denies.session_id, shown.with_denies.session_id
    fresh = without != with_denies and {without, with_denies} <= named
    lower = shown.with_denies.first_request_input_tokens < shown.without_denies.first_request_input_tokens
    return McpResult.qualified if fresh and lower else McpResult.failed_ab_protected_unchanged


def mcp(sheet: Worksheet, folder: Path, refs: Refs) -> McpResult:
    receipt = refs.known("mcp_ab", sheet.mcp_ab.receipt_ref)
    match sheet.mcp_ab.outcome:
        case None:
            return McpResult.NOT_REVIEWED
        case AbOutcome.protected_unchanged:
            return McpResult.protected_unchanged
        case _:
            found = refs.receipts.get(receipt or "")
            if found is None or found.kind is not ReceiptKind.ab:
                msg = "mcp_ab: ab_receipt without an ab receipt"
                raise bad(msg)
            return ab(found, folder, refs)


def not_run(sheet: Worksheet, template: Worksheet, refs: Refs) -> NotRunCounts:
    entries = matched("not_run", sheet.not_run, template.not_run)
    for entry in entries:
        evidence = refs.known("not_run", entry.evidence_ref)
        if entry.outcome is NotRunOutcome.run and evidence is None:
            msg = f"not_run: {entry.ref} is run without its evidence_ref"
            raise bad(msg)
        deferral = [entry.reason, (entry.owner or "").strip() or None, entry.follow_up]
        if entry.outcome is NotRunOutcome.re_deferred and None in deferral:
            msg = f"not_run: {entry.ref} is re_deferred without its reason, owner and follow_up"
            raise bad(msg)
    outcomes = Counter(entry.outcome for entry in entries)
    return NotRunCounts(
        run=outcomes[NotRunOutcome.run], re_deferred=outcomes[NotRunOutcome.re_deferred], not_reviewed=outcomes[None]
    )


def review(
    folder: Path, collection: Collection, evidence: Evidence, given: str | None
) -> tuple[Review, list[ConfigSetting] | None]:
    """The review the worksheet given (else the collection's own) records, and the decision's settings."""
    return checked(folder, collection, evidence, read(folder, given))


def checked(
    folder: Path, collection: Collection, evidence: Evidence, sheet: Worksheet
) -> tuple[Review, list[ConfigSetting] | None]:
    """The review sheet records, and the decision's settings; refused unless it fits the evidence."""
    if sheet.collection_id != collection.collection_id:
        raise TeReviewError(ErrorCode.STALE_WORKSHEET, "the worksheet judges another collection")
    template = worksheet(collection.collection_id, evidence)
    refs = Refs(evidence)
    nudges = redirects(matched("redirects", sheet.redirects, template.redirects), refs)
    stopped = aborts(matched("aborts", sheet.aborts, template.aborts), refs)
    paid = paid_facts(matched("paid_facts", sheet.paid_facts, template.paid_facts), refs, collection)
    verdicts = Counter(entry.verdict for entry in matched("learned_facts", sheet.learned_facts, template.learned_facts))
    learned = LearnedFactCounts(
        wrong=verdicts[FactVerdict.wrong],
        ok=verdicts[FactVerdict.ok],
        unknown=verdicts[FactVerdict.unknown],
        not_reviewed=verdicts[None],
    )
    folds = imports(matched("imports", sheet.imports, template.imports), template.imports, refs, evidence)
    carried = not_run(sheet, template, refs)
    result = mcp(sheet, folder, refs)
    unreviewed = {
        Section.redirects: nudges.not_reviewed + nudges.like_128_not_reviewed,
        Section.aborts: stopped.not_reviewed,
        Section.paid_facts: paid.not_reviewed,
        Section.learned_facts: learned.not_reviewed,
        Section.imports: folds.not_reviewed,
        Section.not_run: carried.not_reviewed,
        Section.mcp_ab: result is McpResult.NOT_REVIEWED,
    }
    missing = [section for section in Section if unreviewed[section]]
    # Judgments cannot fill these: only a receipt the collection lacks can. A caveat, not a blocker (D14).
    gapped = {
        EvidenceGap.redirect_delivery_unknown: nudges.delivery_unknown,
        EvidenceGap.abort_delivery_unknown: stopped.delivery_unknown,
        # A history_fold receipt covers only the imports it names: each listed import and fold needs its own.
        EvidenceGap.import_history_unknown: evidence.import_coverage is ImportCoverage.observed_current_only
        or any(not refs.imports[entry.ref] for entry in template.imports),
    }
    gaps = [gap for gap in EvidenceGap if gapped[gap]]
    decision, settings = sheet.decision.decision, sheet.decision.settings
    if decision is Decision.change and not settings:
        msg = "decision: change without its settings"
        raise bad(msg)
    none_useful = not paid.useful
    conflict = none_useful and (
        decision is Decision.keep or (decision is Decision.change and ENVFACTS not in (settings or []))
    )
    return Review(
        redirects=nudges,
        aborts=stopped,
        paid_facts=paid,
        learned_facts=learned,
        imports=folds,
        not_run=carried,
        mcp_ab=result,
        evidence_complete=not missing,
        missing=missing,
        evidence_gaps=gaps,
        decision_recorded=decision is not None,
        decision=DecisionLine(decision) if decision else DecisionLine.PENDING,
        envfacts=EnvfactsEnum.no_paid_fact_proved_useful__select_microskills_envfacts if none_useful else None,
        conflict=conflict,
        follow_up=None if not missing else FollowUpEnum.field_2026_11_17,
    ), settings
