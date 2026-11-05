"""repotools te-review report: the recorded overhead share of a frozen te-review collection."""

import hashlib
import math
import sys
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .models import (
    AllKeys,
    Cadence,
    CadenceLabel,
    ClassCount,
    Collection,
    Coverage,
    EraCandidate,
    ErrorCode,
    Evidence,
    EvidenceRow,
    ExcludedCount,
    Exclusion,
    OverheadComponents,
    OverheadKey,
    OverheadRow,
    PrivateReport,
    PublicExcludedCount,
    PublicReport,
    RowClass,
    RowKind,
    RowReport,
    SessionClass,
    SessionRow,
    Share,
    ShareStatus,
    TeReviewCollect,
    TeReviewReport,
    Verdict,
)
from .te_review import TeReviewError, collect, collection_id

THRESHOLD = 0.05
# The collection's row class as an exclusion; in_window and matched are none.
ROW_REASON = {
    RowClass.outside_window: Exclusion.NOT_SELECTED,
    RowClass.not_selected: Exclusion.NOT_SELECTED,
    RowClass.missing_end: Exclusion.MISSING_END,
    RowClass.conflict: Exclusion.CONFLICT,
    RowClass.ambiguous: Exclusion.AMBIGUOUS,
    RowClass.unmatched: Exclusion.UNMATCHED,
}
# priced_by as TokenEconomizer's plugin/accounting.py effective writes it; only "model" is eligible,
# and anything else, a missing value included, is UNKNOWN_PRICING_STATUS.
PRICING = {"no_usage": Exclusion.MISSING_USAGE, "fallback": Exclusion.FALLBACK_PRICING}
CLASS_REASON = {SessionClass.synthetic: Exclusion.SYNTHETIC, SessionClass.unknown: Exclusion.UNCLASSIFIED}
# A session's cadence as the report labels it; unknown stays UNKNOWN.
CADENCE = {CadenceLabel.cadence_1: Cadence.field_1, CadenceLabel.cadence_3: Cadence.field_3}
ORDER = list(Exclusion)
KNOWN = set(OverheadKey)
# Fold times a date holds in any tz, a day in from each end of datetime's range; NaN compares false.
EARLIEST = (datetime.min.replace(tzinfo=UTC) + timedelta(days=1)).timestamp()
LATEST = (datetime.max.replace(tzinfo=UTC) - timedelta(days=1)).timestamp()


def bundle(folder: Path) -> tuple[Collection, Evidence]:
    """The collection and its evidence, once COMPLETE is there and every hash matches collection.json."""
    if not folder.is_absolute():
        raise TeReviewError(ErrorCode.RELATIVE_PATH, "--evidence is relative; give the collection's absolute path")
    try:
        complete = (folder / "COMPLETE").read_bytes()
    except OSError:
        raise TeReviewError(ErrorCode.NOT_COMPLETE, f"{folder} has no COMPLETE marker") from None
    try:
        collection = Collection.model_validate_json((folder / "collection.json").read_bytes())
        data = (folder / "evidence.json").read_bytes()
        evidence = Evidence.model_validate_json(data)
        sources = {source.path: (folder / "sources" / source.path).read_bytes() for source in collection.sources}
    # A missing or unreadable file (OSError), or one that is not the model (ValidationError, a ValueError).
    except OSError, ValueError:
        raise TeReviewError(ErrorCode.BAD_BUNDLE, f"{folder} is not a readable te-review collection") from None
    for source in collection.sources:
        held = sources[source.path]
        if (len(held), hashlib.sha256(held).hexdigest(), held.count(b"\n")) != (
            source.bytes,
            source.sha256,
            source.lines,
        ):
            raise TeReviewError(ErrorCode.HASH_MISMATCH, f"sources/{source.path} differs from collection.json")
    computed = collection_id(collection.window, collection.versions, sources, data)
    if computed != collection.collection_id or complete != f"{computed}\n".encode():
        raise TeReviewError(ErrorCode.HASH_MISMATCH, f"{folder} does not hash to its collection id")
    return collection, evidence


def number(value: object) -> float:
    """A value as TokenEconomizer's ledger.py _num sums it: a number as it is, anything else 0."""
    return float(value) if isinstance(value, int | float) else 0.0


def amount(value: object) -> float | None:
    """A finite, non-negative number, else None."""
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value) or value < 0:
        return None
    return float(value)


def record(row: EvidenceRow) -> SessionRow | OverheadRow:
    model = SessionRow if row.kind is RowKind.session else OverheadRow
    return model.model_validate(row.row)


def own_reasons(row: EvidenceRow, rec: SessionRow | OverheadRow, cohort: SessionClass) -> set[Exclusion]:
    """A row's reasons from itself alone, before its session or its charges count."""
    reasons = {ROW_REASON[row.row_class]} if row.row_class in ROW_REASON else set()
    if any(amount(value) is None for value in rec.overhead.values()):
        reasons.add(Exclusion.BAD_AMOUNT)
    if isinstance(rec, SessionRow):
        if rec.imported:
            reasons.add(Exclusion.IMPORTED)
        if rec.error is not None:
            reasons.add(Exclusion.ERROR)
        if rec.priced_by != "model":
            reasons.add(PRICING.get(str(rec.priced_by), Exclusion.UNKNOWN_PRICING_STATUS))
        if (rec.effective_tokens is not None or rec.priced_by == "model") and amount(rec.effective_tokens) is None:
            reasons.add(Exclusion.BAD_AMOUNT)
        if cohort in CLASS_REASON:
            reasons.add(CLASS_REASON[cohort])
    return reasons


def reasons_of(
    rows: list[EvidenceRow], records: list[SessionRow | OverheadRow], cohorts: dict[str, SessionClass]
) -> list[list[Exclusion]]:
    """Every row's reasons in precedence order: a session goes with all its charges, or none of them."""
    own = [
        own_reasons(row, rec, cohorts.get(row.ref, SessionClass.unknown))
        for row, rec in zip(rows, records, strict=True)
    ]
    session_out: dict[tuple[str, str, str], bool] = defaultdict(bool)
    charge_out: dict[tuple[str, str, str], bool] = defaultdict(bool)
    for row, reasons in zip(rows, own, strict=True):
        key = (row.store, row.host, row.session_id)
        flags = session_out if row.kind is RowKind.session else charge_out
        flags[key] = flags[key] or bool(reasons)
    sessions = {(row.store, row.host, row.session_id) for row in rows if row.kind is RowKind.session}
    found = []
    for row, reasons in zip(rows, own, strict=True):
        key = (row.store, row.host, row.session_id)
        if row.kind is RowKind.session and charge_out[key]:
            reasons.add(Exclusion.CHARGE_EXCLUDED)
        # A charge's session is out for its own reasons or for any of its charges', which takes every charge.
        if row.kind is RowKind.overhead and key in sessions and (session_out[key] or charge_out[key]):
            reasons.add(Exclusion.SESSION_EXCLUDED)
        found.append(sorted(reasons, key=ORDER.index))
    return found


def unknown_keys(records: list[SessionRow | OverheadRow]) -> dict[str, float | None]:
    """The sum of each overhead key that ledger.py does not name, as its _num sums it."""
    keys: dict[str, float] = defaultdict(float)
    for rec in records:
        for key, value in rec.overhead.items():
            if key not in KNOWN:
                keys[key] += number(value)
    return {key: total(value) for key, value in keys.items()}


def spent(rec: SessionRow | OverheadRow, *, every_key: bool) -> dict[str, object]:
    """A row's overhead amounts the figures count: the recognized keys, or with every_key all of them. B5:
    an unknown key's amount in a public total could be worked out by subtraction, so public leaves it out."""
    return {key: value for key, value in rec.overhead.items() if every_key or key in KNOWN}


def share(records: list[SessionRow | OverheadRow], *, every_key: bool) -> Share:
    """overhead / (effective + overhead), per TokenEconomizer's plugin/accounting.py summarize."""
    sessions = [rec for rec in records if isinstance(rec, SessionRow)]
    effective = sum(number(rec.effective_tokens) for rec in sessions)
    keys: dict[str, float] = defaultdict(float)
    for rec in records:
        for key, value in spent(rec, every_key=every_key).items():
            keys[key] += number(value)
    overhead = sum(keys.values())
    denominator = effective + overhead
    known = denominator != 0 and math.isfinite(denominator)
    fraction = overhead / denominator if known else None
    verdict = Verdict.UNKNOWN if fraction is None else Verdict.YES if fraction > THRESHOLD else Verdict.NO
    return Share(
        sessions=len(sessions),
        charges=len(records) - len(sessions),
        effective_tokens=total(effective),
        overhead_tokens=total(overhead),
        components=OverheadComponents(**{key: total(keys[key]) for key in OverheadKey}),
        unknown_overhead_keys=len(unknown_keys(records)),
        share=fraction,
        status=ShareStatus.KNOWN if known else ShareStatus.UNKNOWN,
        above_5_percent=verdict,
    )


def grouped(rows: list[EvidenceRow], reasons: list[list[Exclusion]]) -> list[Exclusion | None]:
    """D5: the reason a row's spend goes under in public: a charge's goes with its excluded session's first
    reason, so no reason's total is a session's overhead alone; a headline row has none."""
    sessions: dict[tuple[str, str, str], Exclusion] = {}
    for row, why in zip(rows, reasons, strict=True):
        key = (row.store, row.host, row.session_id)
        if row.kind is RowKind.session and why:
            sessions[key] = min(why[0], sessions.get(key, why[0]), key=ORDER.index)
    return [
        sessions.get((row.store, row.host, row.session_id), why[0]) if why else None
        for row, why in zip(rows, reasons, strict=True)
    ]


def excluded(
    records: list[SessionRow | OverheadRow],
    reasons: list[list[Exclusion]],
    *,
    every_key: bool,
    spend: list[Exclusion | None] | None = None,
) -> list[ExcludedCount]:
    """Each row once, under its first reason, with the spend it recorded under that reason or the one spend
    names."""
    rows: Counter[Exclusion] = Counter()
    effective: dict[Exclusion, float] = defaultdict(float)
    overhead: dict[Exclusion, float] = defaultdict(float)
    invalid: Counter[Exclusion] = Counter()
    under = spend or [why[0] if why else None for why in reasons]
    # A headline row has no reason and is not excluded.
    for rec, row_reason, first in [
        (rec, why[0], into) for rec, why, into in zip(records, reasons, under, strict=True) if why and into
    ]:
        rows[row_reason] += 1
        values = list(spent(rec, every_key=every_key).values())
        if isinstance(rec, SessionRow) and rec.effective_tokens is not None:
            values.append(rec.effective_tokens)
            effective[first] += finite(rec.effective_tokens) or 0.0
        overhead[first] += sum(finite(value) or 0.0 for value in spent(rec, every_key=every_key).values())
        invalid[first] += sum(finite(value) is None for value in values)
    return [
        ExcludedCount(
            reason=reason,
            rows=rows[reason],
            effective_tokens=total(effective[reason]),
            overhead_tokens=total(overhead[reason]),
            invalid_amounts=invalid[reason],
        )
        for reason in ORDER
    ]


def combined(counts: list[ExcludedCount]) -> list[PublicExcludedCount]:
    """D1: public shows each reason's recorded spend as one total; the effective and overhead split would let
    a reader rebuild the private selected share, and so would a total with no effective tokens (D6)."""
    return [
        PublicExcludedCount(
            reason=count.reason,
            rows=count.rows,
            # D6: with no effective tokens the total is overhead alone, part of the selected numerator.
            recorded_tokens=None
            if not count.effective_tokens or count.overhead_tokens is None
            else total(count.effective_tokens + count.overhead_tokens),
            invalid_amounts=count.invalid_amounts,
        )
        for count in counts
    ]


def total(value: float) -> float | None:
    """A sum as the report shows it: JSON has no Infinity or NaN, so a non-finite sum is null."""
    return value if math.isfinite(value) else None


def finite(value: object) -> float | None:
    """A recorded amount as its exclusion's spend sums it: a finite number, negatives included; else None."""
    return float(value) if isinstance(value, int | float) and math.isfinite(value) else None


def folded_on(rec: SessionRow, zone: ZoneInfo) -> date | None:
    """The fold's day in the collection's tz; None for NaN or a time no date holds in every tz."""
    return datetime.fromtimestamp(rec.folded_at, zone).date() if EARLIEST <= rec.folded_at <= LATEST else None


def accounting(collection: Collection, evidence: Evidence) -> PrivateReport:
    rows = evidence.rows
    records = [record(row) for row in rows]
    # A session's class comes from its receipts alone (evidence.sessions); a charge has none of its own.
    cohorts = {found.ref: SessionClass(found.cohort.value) for found in evidence.sessions}
    reasons = reasons_of(rows, records, cohorts)
    imported = {
        (row.store, row.host, row.session_id)
        for row, rec in zip(rows, records, strict=True)
        if isinstance(rec, SessionRow) and rec.imported
    }
    chosen = [
        (row, rec)
        for row, rec in zip(rows, records, strict=True)
        if row.row_class in {RowClass.in_window, RowClass.matched}
        and (row.store, row.host, row.session_id) not in imported
    ]
    selected = [rec for _, rec in chosen]
    sessions = [rec for rec in selected if isinstance(rec, SessionRow)]
    classes = Counter(cohorts.get(row.ref, SessionClass.unknown) for row, rec in chosen if isinstance(rec, SessionRow))
    zone = ZoneInfo(collection.window.tz)
    days = Counter(folded_on(rec, zone) for rec in sessions)
    cohort = [rec for rec, why in zip(records, reasons, strict=True) if not why]
    headline = {row.ref for row, why in zip(rows, reasons, strict=True) if not why and row.kind is RowKind.session}
    # The report's cadence is the one every headline session was proven folded under, else UNKNOWN.
    labels = {CADENCE.get(found.cadence, Cadence.UNKNOWN) for found in evidence.sessions if found.ref in headline}
    public = PublicReport(
        scope="recorded charges",
        label=collection.label,
        since=collection.window.since,
        until=collection.window.until,
        headline=share(cohort, every_key=False),
        coverage=Coverage(
            headline_sessions=sum(isinstance(rec, SessionRow) for rec in cohort),
            selected_sessions=len(sessions),
            no_recorded_usage=sum(rec.error is not None for rec in sessions),
        ),
        excluded=combined(excluded(records, reasons, every_key=False, spend=grouped(rows, reasons))),
        session_classes=[ClassCount(session_class=cls, sessions=classes[cls]) for cls in SessionClass],
        cadence=labels.pop() if len(labels) == 1 else Cadence.UNKNOWN,
        policy_era_candidates=[
            EraCandidate(folded_on=day, sessions=count)
            for day, count in sorted(days.items(), key=lambda item: (item[0] is None, item[0] or date.min))
        ],
        unknown_keys=f"unknown keys: {len(unknown_keys(records))} (excluded from public totals)",
        withheld="a reason with no effective tokens shows no total; that spend is only in --private",
    )
    return PrivateReport(
        collection_id=collection.collection_id,
        tz=collection.window.tz,
        report=public,
        selected=share(selected, every_key=False),
        excluded=excluded(records, reasons, every_key=False),
        all_keys=AllKeys(
            headline=share(cohort, every_key=True),
            selected=share(selected, every_key=True),
            excluded=excluded(records, reasons, every_key=True),
        ),
        unknown_overhead_keys=unknown_keys(selected),
        rows=[
            RowReport(ref=row.ref, kind=row.kind, store=row.store, session_id=row.session_id, job=row.job, reasons=why)
            for row, why in zip(rows, reasons, strict=True)
        ],
    )


def shown(options: TeReviewReport) -> PrivateReport | PublicReport:
    """The report the mode asks for: public unless --private."""
    if options.public and options.private:
        raise TeReviewError(ErrorCode.BAD_MODE, "--public and --private exclude each other")
    full = accounting(*bundle(Path(options.evidence)))
    return full if options.private else full.report


def report(options: TeReviewReport) -> None:
    try:
        chosen = shown(options)
    except TeReviewError as error:
        error.public = not options.private
        raise
    sys.stdout.write(chosen.model_dump_json(indent=2) + "\n")


def dispatch(options: TeReviewCollect | TeReviewReport) -> None:
    match options:
        case TeReviewCollect():
            collect(options)
        case _:
            report(options)
