"""repotools te-review: the receipts and judgment candidates of a collection, and the owner's worksheet."""

# A candidate is only what the state shows: a redirect counts as delivered only with a host_delivery
# receipt, a fact's time of origin only with a fact_snapshot receipt, an import's effect only with a
# history_fold receipt, a session's cohort only with a real_work or synthetic receipt and its cadence only
# with a cadence receipt. Everything else stays unknown, and every judgment in the worksheet starts null.

# Pattern: simonmichael/hledger@9ede2b0 hledger-lib/Hledger/Read/Common.hs:1069-1078 (balance assertions)
# checks an owner-written claim against the journal and refuses the whole read when one fails, rather
# than reporting it beside the data; a receipt whose hash, kind or link does not match is refused the same way.
# The owner-filled template beside frozen evidence follows ryoppippi/ccusage@f674ef6's idea of reading
# only what the logs hold: nothing here infers a judgment that a receipt does not prove.

import hashlib
import itertools
import json
import math
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel, ValidationError

from .models import (
    CadenceLabel,
    CadenceProof,
    CadenceReason,
    CadenceReceipt,
    ErrorCode,
    EventLine,
    Evidence,
    EvidenceReceipt,
    EvidenceRow,
    FactCandidate,
    FactLifeState,
    FactMechanism,
    FactProvenance,
    FoldProvenance,
    HistoryRunState,
    HistoryState,
    ImportCandidate,
    ImportCompletion,
    ImportCoverage,
    ImportEntry,
    ImportFoldCandidate,
    InjectionState,
    ManifestRole,
    MechanismState,
    Receipt,
    ReceiptKind,
    ReceiptManifest,
    RedirectCandidate,
    RedirectEvent,
    RedirectKind,
    RedirectState,
    RowKind,
    SessionCohort,
    SessionEvidence,
    SourceLine,
    TeReviewCollect,
    Window,
    Worksheet,
    WorksheetAb,
    WorksheetAbort,
    WorksheetDecision,
    WorksheetFact,
    WorksheetImport,
    WorksheetNotRun,
    WorksheetPaidFact,
    WorksheetRedirect,
)
from .te_io import TeReviewError, conform, json_file, json_lines, listing, present, read_bytes

# How long after an import finishes its process still folds live sessions: plugin/history.py _run_locked
# sets finished, then folds the sessions that waited for the fold lock in the same process.
NEAR_S = 600.0
MANIFESTS = {ManifestRole.receipts: "manifests/receipts.json", ManifestRole.synthetic: "manifests/synthetic.json"}
CADENCE = "manifests/cadence.json"
STATE = ("events.jsonl", "history.json", "injection.json")
MECHANISMS = {"manual_state": FactMechanism.manual, "envfacts_state": FactMechanism.envfacts}
COMPLETION = {
    HistoryRunState.done: ImportCompletion.completed,
    HistoryRunState.partial: ImportCompletion.partial,
    HistoryRunState.running: ImportCompletion.partial,
    HistoryRunState.stopped: ImportCompletion.partial,
}
CADENCE_LABEL = {1: CadenceLabel.cadence_1, 3: CadenceLabel.cadence_3}
FACT_RECEIPTS = (ReceiptKind.fact_injection, ReceiptKind.fact_use, ReceiptKind.fact_snapshot)
IMPORT_NOTE = {
    ImportCoverage.observed_current_only: "observed current import state; historical operation coverage unknown",
    ImportCoverage.history_receipts: "history_fold receipts cover the operations they name; others unknown",
}


def refuse(error: str) -> TeReviewError:
    return TeReviewError(ErrorCode.BAD_RECEIPT, error)


def manifest(role: ManifestRole, data: bytes) -> ReceiptManifest:
    raw = json_file(MANIFESTS[role], data)
    try:
        found = ReceiptManifest.model_validate(raw)
    except ValidationError as error:
        msg = f"{MANIFESTS[role]}: {error.error_count()} errors against ReceiptManifest"
        raise refuse(msg) from None
    for receipt in found.receipts:
        if (receipt.kind is ReceiptKind.synthetic) != (role is ManifestRole.synthetic):
            where = "--synthetic-manifest" if role is ManifestRole.synthetic else "--receipts"
            msg = f"{where} names a {receipt.kind} receipt, {receipt.path}"
            raise refuse(msg)
    return found


def entries(manifests: dict[ManifestRole, bytes]) -> list[tuple[str, ManifestRole, Receipt, str]]:
    """Each receipt with its ref and the path of its copy, numbered across the manifests in a fixed order."""
    found = []
    for role, data in sorted(manifests.items()):
        for receipt in manifest(role, data).receipts:
            ref = f"R{len(found) + 1:05d}"
            found.append((ref, role, receipt, f"receipts/{ref}-{Path(receipt.path).name}"))
    return found


def state_files(root: Path) -> dict[str, Path]:
    """Every store's state files: events, history, injection and mechanism states, by path under root."""
    origins: dict[str, Path] = {}
    for store in (repo / "claude" for repo in listing(root / "repos")):
        names = [name for name in STATE if present(store / name)]
        names += [
            f"mechanisms/{folder}/{path.name}"
            for folder in MECHANISMS
            for path in listing(store / "mechanisms" / folder)
            if path.suffix == ".json"
        ]
        origins.update({(store / name).relative_to(root).as_posix(): store / name for name in names})
    return origins


def gather(root: Path, options: TeReviewCollect) -> dict[str, Path]:
    """Every state, manifest and receipt file the collection freezes, by its path under sources/."""
    origins = state_files(root)
    given = {ManifestRole.receipts: options.receipts, ManifestRole.synthetic: options.synthetic_manifest}
    manifests = {}
    for role, option in given.items():
        if option is not None:
            origins[MANIFESTS[role]] = Path(option).absolute()
            manifests[role] = read_bytes(origins[MANIFESTS[role]])
    for _, role, receipt, bundle in entries(manifests):
        origins[bundle] = origins[MANIFESTS[role]].parent / receipt.path  # an absolute path stays itself
    if options.cadence_receipt is not None:
        origins[CADENCE] = Path(options.cadence_receipt).absolute()
    return origins


def cadence_receipt(sources: dict[str, bytes]) -> CadenceReceipt | None:
    if CADENCE not in sources:
        return None
    try:
        found = CadenceReceipt.model_validate(json_file(CADENCE, sources[CADENCE]))
    except ValidationError as error:
        msg = f"--cadence-receipt: {error.error_count()} errors against CadenceReceipt"
        raise refuse(msg) from None
    if found.proof is CadenceProof.process_started_after_change:
        problem = (
            "the process did not start after the change"
            if found.process_started <= found.changed_at
            else "an override decides the process's cadence, not the change"
            if found.repo_override or found.env_override
            else None
        )
    else:
        captured = found.captured_config
        shown = captured is not None and captured.microskills_propose_every == found.after
        problem = None if shown else "the captured configuration does not show the new cadence"
    if problem is not None:
        msg = f"--cadence-receipt: {problem}"
        raise refuse(msg)
    return found


def store_of(source: str) -> str:
    return "/".join(source.split("/")[:2])


def sealed[M: BaseModel](candidate: M) -> M:
    """candidate with its digest: sha256 of its canonical JSON, without its ref and digest."""
    body = candidate.model_dump(mode="json", exclude={"ref", "digest"})
    data = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return candidate.model_copy(update={"digest": hashlib.sha256(data).hexdigest()})


def redirect_events(sources: dict[str, bytes]) -> list[tuple[SourceLine, RedirectEvent]]:
    found = []
    for source, data in sources.items():
        if source.startswith("repos/") and source.endswith("/events.jsonl"):
            for number, raw in json_lines(source, data):
                line = conform(EventLine, f"{source}:{number}", raw)
                if line.kind in set(RedirectKind):
                    event = conform(RedirectEvent, f"{source}:{number}", raw)
                    found.append((SourceLine(source=source, line=number), event))
    return found


def learned_facts(sources: dict[str, bytes]) -> list[dict]:
    """Each fact of each mechanism state file, as candidate fields without ref, receipts or provenance."""
    rendered: dict[str, set[str]] = {}
    for source, data in sources.items():
        if source.startswith("repos/") and source.endswith("/claude/injection.json"):
            rendered[store_of(source)] = set(conform(InjectionState, source, json_file(source, data)).rendered_ids)
    found = []
    for source, data in sources.items():
        parts = source.split("/")
        if parts[0] == "repos" and parts[3:4] == ["mechanisms"]:
            state = conform(MechanismState, source, json_file(source, data))
            mechanism = MECHANISMS[parts[4]]
            for fact_id, fact in state.facts.items():
                found.append(
                    {
                        "store": store_of(source),
                        "source": source,
                        "mechanism": mechanism,
                        "paid": mechanism is FactMechanism.manual,
                        "fact_id": fact_id,
                        "life_state": fact.life.state,
                        "retained": fact.life.state is not FactLifeState.RETIRED,
                        "rendered": fact_id in rendered.get(store_of(source), set()),
                        "fact": fact.model_dump(mode="json", by_alias=True, exclude_unset=True),
                    }
                )
    return found


def histories(sources: dict[str, bytes]) -> list[tuple[str, HistoryState]]:
    return [
        (store_of(source), conform(HistoryState, source, json_file(source, data)))
        for source, data in sources.items()
        if source.startswith("repos/") and source.endswith("/claude/history.json")
    ]


def one(refs: list[str], what: str, receipt: Receipt) -> str:
    if len(refs) != 1:
        problem = "names nothing collected" if not refs else f"matches {len(refs)} candidates"
        msg = f"receipt {receipt.path}: {what} {problem}"
        raise refuse(msg)
    return refs[0]


def links(
    receipt: Receipt,
    rows: list[EvidenceRow],
    redirects: dict[str, RedirectEvent],
    facts: dict[str, dict],
    imports: dict[str, str],
) -> list[str]:
    """The refs a receipt names by native id; each must name exactly one thing collected."""
    needs = {
        ReceiptKind.host_delivery: [receipt.redirects],
        ReceiptKind.fact_injection: [receipt.facts, receipt.sessions],
        ReceiptKind.fact_use: [receipt.facts, receipt.sessions],
        ReceiptKind.fact_snapshot: [receipt.facts],
        ReceiptKind.history_fold: [receipt.imports],
        ReceiptKind.synthetic: [receipt.sessions],
        ReceiptKind.real_work: [receipt.sessions],
    }
    if not all(needs.get(receipt.kind, [])):
        msg = f"receipt {receipt.path}: a {receipt.kind} receipt must name what it shows"
        raise refuse(msg)
    found = [
        one(
            [row.ref for row in rows if row.kind is RowKind.session and row.session_id == session_id],
            f"session {session_id}",
            receipt,
        )
        for session_id in receipt.sessions
    ]
    found += [
        one([ref for ref, fact in facts.items() if fact["fact_id"] == fact_id], f"fact {fact_id}", receipt)
        for fact_id in receipt.facts
    ]
    for link in receipt.redirects:
        matches = [
            ref for ref, event in redirects.items() if (event.session_id, event.at) == (link.session_id, link.at)
        ]
        ref = one(matches, f"redirect {link.session_id}@{link.at}", receipt)
        event = redirects[ref]
        # D4: an abort can reach the host too; a shadow event never does.
        if receipt.kind is ReceiptKind.host_delivery and event.shadow:
            what = f"{'shadow ' * event.shadow}{event.kind}"
            msg = f"receipt {receipt.path}: host_delivery of a {what}, which is never delivered"
            raise refuse(msg)
        found.append(ref)
    found += [
        one([ref for ref, store in imports.items() if store == label], f"import {label}", receipt)
        for label in receipt.imports
    ]
    return found


def cadence_reason(row: EvidenceRow, receipt: CadenceReceipt, spans: list[tuple[float, float]]) -> CadenceReason:
    """Proven only when a session's end and its fold sit on one side of the change, outside an older import."""
    ended, folded = row.row["ended"], row.row["folded_at"]
    if ended is None or not math.isfinite(ended):
        return CadenceReason.missing_end
    changed = receipt.changed_at.timestamp()
    if any(started < changed and (row.row.get("imported") or started <= folded <= end) for started, end in spans):
        return CadenceReason.import_process_before_change
    if ended >= changed and folded >= changed:
        # The proof is about one process: a fold before it started ran in an older one.
        proven = folded >= receipt.process_started.timestamp()
        return CadenceReason.after_change if proven else CadenceReason.before_proven_process
    if ended < changed and folded < changed:
        return CadenceReason.before_change_unproven if receipt.before is None else CadenceReason.before_change
    return CadenceReason.straddles_change


def cadence(
    row: EvidenceRow, receipt: CadenceReceipt | None, spans: list[tuple[float, float]]
) -> tuple[CadenceLabel, CadenceReason]:
    """The cadence a session was folded under, and why."""
    if receipt is None:
        return CadenceLabel.unknown, CadenceReason.no_receipt
    # A process's configuration is its repository's and environment's (plugin/context.py): the proof names its sessions.
    reason = cadence_reason(row, receipt, spans) if row.session_id in receipt.sessions else CadenceReason.not_covered
    proven = {CadenceReason.after_change: receipt.after, CadenceReason.before_change: receipt.before}
    value = proven.get(reason)
    return (CadenceLabel.unknown if value is None else CADENCE_LABEL[value]), reason


def receipted(linked: dict[str, list[tuple[str, ReceiptKind]]], target: str, *kinds: ReceiptKind) -> list[str]:
    """The receipts of these kinds that name target."""
    return [ref for ref, kind in linked.get(target, []) if kind in kinds]


def redirect_state(event: RedirectEvent, delivered: list[str]) -> RedirectState:
    if event.shadow:
        return RedirectState.shadow_suppressed
    return RedirectState.delivery_confirmed if delivered else RedirectState.delivery_unknown


def folds(
    imports: list[ImportCandidate],
    rows: list[EvidenceRow],
    linked: dict[str, list[tuple[str, ReceiptKind]]],
    refs: Iterator[str],
) -> list[ImportFoldCandidate]:
    """The live folds an import's process ran after it finished: receipted, or paid and near (plugin/history.py)."""
    found = []
    for done in imports:
        finished = done.history.finished
        for row in rows:
            if row.kind is not RowKind.session or row.store != done.store:
                continue
            mine = receipted(linked, row.ref, ReceiptKind.history_fold)
            both = [ref for ref in receipted(linked, done.ref, ReceiptKind.history_fold) if ref in mine]
            # A paid live fold only; time proximity stands in where no receipt ties it to the import.
            optimizer = (row.row.get("overhead") or {}).get("optimizer_tokens") or 0
            near = finished is not None and finished <= row.row.get("folded_at", -1) <= finished + NEAR_S
            if (both or near) and optimizer > 0 and not row.row.get("imported"):
                provenance = FoldProvenance.receipted if both else FoldProvenance.time_near
                found.append(
                    sealed(
                        ImportFoldCandidate(
                            ref=next(refs),
                            digest="",
                            import_ref=done.ref,
                            session_ref=row.ref,
                            session_id=row.session_id,
                            folded_at=row.row["folded_at"],
                            provenance=provenance,
                            receipts=both,
                        )
                    )
                )
    return found


def sessions(
    rows: list[EvidenceRow],
    linked: dict[str, list[tuple[str, ReceiptKind]]],
    proof: CadenceReceipt | None,
    imports: list[ImportCandidate],
    import_folds: list[ImportFoldCandidate],
) -> list[SessionEvidence]:
    """Each session row's cohort, from receipts only, and its cadence."""
    found_rows = [row for row in rows if row.kind is RowKind.session]
    for name in proof.sessions if proof is not None else []:
        if (count := sum(row.session_id == name for row in found_rows)) != 1:
            msg = f"--cadence-receipt: session {name} matches {count} collected sessions, not 1"
            raise refuse(msg)
    spans: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for done in imports:
        if (started := done.history.started) is not None:
            spans[done.store].append((started, (done.history.finished or done.history.heartbeat or math.inf) + NEAR_S))
            # A fold a receipt ties to the import ran in its process, however late and whatever it cost.
            shared = set(receipted(linked, done.ref, ReceiptKind.history_fold))
            ties = [row.ref for row in found_rows if shared & set(receipted(linked, row.ref, ReceiptKind.history_fold))]
            ties += [fold.session_ref for fold in import_folds if fold.import_ref == done.ref]
            spans.update({ref: [(started, math.inf)] for ref in ties})
    found = []
    for row in found_rows:
        real = receipted(linked, row.ref, ReceiptKind.real_work)
        synthetic = receipted(linked, row.ref, ReceiptKind.synthetic)
        if real and synthetic:
            msg = f"session {row.session_id} has both real_work and synthetic receipts"
            raise refuse(msg)
        cohort = SessionCohort.real_work if real else SessionCohort.synthetic if synthetic else SessionCohort.unknown
        label, reason = cadence(row, proof, spans[row.store] + spans[row.ref])
        found.append(
            SessionEvidence(
                ref=row.ref,
                store=row.store,
                session_id=row.session_id,
                cohort=cohort,
                cohort_receipts=real + synthetic,
                cadence=label,
                cadence_reason=reason,
            )
        )
    return found


def judge(rows: list[EvidenceRow], sources: dict[str, bytes], origins: dict[str, Path], span: Window) -> Evidence:
    """The evidence: rows, receipts and candidates, each candidate sealed by its digest."""
    receipts = entries({role: sources[name] for role, name in MANIFESTS.items() if name in sources})
    for _, _, receipt, bundle in receipts:
        if hashlib.sha256(sources[bundle]).hexdigest() != receipt.sha256:
            msg = f"receipt {origins[bundle]} does not have sha256 {receipt.sha256}"
            raise TeReviewError(ErrorCode.RECEIPT_MISMATCH, msg)
    proof = cadence_receipt(sources)
    start, end = span.start.timestamp(), span.end.timestamp()
    refs = (f"C{number:05d}" for number in itertools.count(1))
    redirects = {next(refs): found for found in redirect_events(sources)}
    facts = {next(refs): fact for fact in learned_facts(sources)}
    states = {next(refs): found for found in histories(sources)}
    linked: dict[str, list[tuple[str, ReceiptKind]]] = defaultdict(list)
    frozen = []
    for ref, role, receipt, bundle in receipts:
        events = {key: event for key, (_, event) in redirects.items()}
        named = links(receipt, rows, events, facts, {key: store for key, (store, _) in states.items()})
        for target in named:
            linked[target].append((ref, receipt.kind))
        frozen.append(
            EvidenceReceipt(
                ref=ref,
                kind=receipt.kind,
                manifest=role,
                timestamp=receipt.timestamp,
                path=bundle,
                origin=str(origins[bundle]),
                sha256=receipt.sha256,
                links=named,
            )
        )
    redirect_candidates = [
        sealed(
            RedirectCandidate(
                ref=ref,
                digest="",
                store=store_of(line.source),
                line=line,
                kind=event.kind,
                session_id=event.session_id,
                at=event.at,
                in_window=start <= event.at < end,
                receipts=receipted(linked, ref, ReceiptKind.host_delivery),
                state=redirect_state(event, receipted(linked, ref, ReceiptKind.host_delivery)),
                event=event.model_dump(mode="json", by_alias=True, exclude_unset=True),
            )
        )
        for ref, (line, event) in redirects.items()
    ]
    fact_candidates = [
        sealed(
            FactCandidate(
                ref=ref,
                digest="",
                receipts=receipted(linked, ref, *FACT_RECEIPTS),
                provenance=FactProvenance.receipted
                if receipted(linked, ref, ReceiptKind.fact_snapshot)
                else FactProvenance.missing,
                **fact,
            )
        )
        for ref, fact in facts.items()
    ]
    import_candidates = [
        sealed(
            ImportCandidate(
                ref=ref,
                digest="",
                store=store,
                completion=COMPLETION.get(history.state, ImportCompletion.unknown),
                in_window=history.finished is not None and start <= history.finished < end,
                sessions=history.imported,
                receipts=receipted(linked, ref, ReceiptKind.history_fold),
                history=history,
            )
        )
        for ref, (store, history) in states.items()
    ]
    coverage = (
        ImportCoverage.history_receipts
        if any(receipt.kind is ReceiptKind.history_fold for receipt in frozen)
        else ImportCoverage.observed_current_only
    )
    import_folds = folds(import_candidates, rows, linked, refs)
    return Evidence(
        rows=rows,
        receipts=frozen,
        cadence_receipt=proof,
        sessions=sessions(rows, linked, proof, import_candidates, import_folds),
        redirects=redirect_candidates,
        facts=fact_candidates,
        imports=import_candidates,
        import_folds=import_folds,
        import_coverage=coverage,
        import_note=IMPORT_NOTE[coverage],
    )


def worksheet(collection_id: str, evidence: Evidence) -> Worksheet:
    """The owner's template: the candidates each section judges, every judgment NOT_REVIEWED (null).

    A redirect or abort collect confirmed carries the host_delivery receipt that confirms it.
    """
    selected = {found.ref for found in evidence.imports if found.in_window}
    # Addendum 4: a partial import with no finished time cannot be placed in the window; it is shown too.
    partial = [
        found
        for found in evidence.imports
        if found.completion is ImportCompletion.partial and found.history.finished is None
    ]
    return Worksheet(
        collection_id=collection_id,
        redirects=[
            WorksheetRedirect(
                ref=found.ref,
                digest=found.digest,
                state=found.state,
                verdict=None,
                like_128=None,
                receipt_ref=next(iter(found.receipts), None),
            )
            for found in evidence.redirects
            if found.in_window and found.kind is RedirectKind.nudge
        ],
        aborts=[
            WorksheetAbort(
                ref=found.ref,
                digest=found.digest,
                state=found.state,
                verdict=None,
                receipt_ref=next(iter(found.receipts), None),
            )
            for found in evidence.redirects
            if found.in_window and found.kind is RedirectKind.abort
        ],
        paid_facts=[
            WorksheetPaidFact(
                ref=found.ref, digest=found.digest, owner_assessment=None, reason=None, origin_ref=None, use_ref=None
            )
            for found in evidence.facts
            if found.paid and found.retained
        ],
        learned_facts=[WorksheetFact(ref=found.ref, digest=found.digest, verdict=None) for found in evidence.facts],
        imports=[
            WorksheetImport(ref=ref, digest=digest, entry=entry, verdict=None, receipt_ref=None)
            for ref, digest, entry in [
                *(
                    (found.ref, found.digest, ImportEntry.finished_in_window)
                    for found in evidence.imports
                    if found.ref in selected
                ),
                *((found.ref, found.digest, ImportEntry.partial) for found in partial),
                *(
                    (found.ref, found.digest, ImportEntry.fold)
                    for found in evidence.import_folds
                    if found.import_ref in selected
                ),
            ]
        ],
        not_run=[
            WorksheetNotRun(
                ref=found.ref,
                digest=found.sha256,
                outcome=None,
                evidence_ref=None,
                reason=None,
                owner=None,
                follow_up=None,
            )
            for found in evidence.receipts
            if found.kind is ReceiptKind.not_run
        ],
        mcp_ab=WorksheetAb(outcome=None, receipt_ref=None),
        decision=WorksheetDecision(decision=None, settings=None),
    )
