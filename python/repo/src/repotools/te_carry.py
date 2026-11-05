"""repotools te-review carry: an owner's judgments of one collection, carried to a newer one's new worksheet."""

# Pattern: git/git@0ffa3e3 rerere.c:396-401 keys a recorded conflict resolution by the hash of the conflict's
# content, and rerere.c:640-661 replays it only onto a conflict with that same id, through try_merge, which
# fails rather than forcing it. Here a judgment is keyed by its candidate's digest, replayed only onto B's
# candidate of that digest, and kept only if B's own checks (te_worksheet.checked) accept it.

import json
import sys
from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from .models import (
    Carried,
    CarryConflict,
    CarryReason,
    CarrySection,
    CarrySummary,
    Collection,
    ErrorCode,
    Evidence,
    NotCarried,
    TeReviewCarry,
    Worksheet,
    WorksheetAbort,
    WorksheetFact,
    WorksheetImport,
    WorksheetNotRun,
    WorksheetPaidFact,
    WorksheetRedirect,
)
from .te_io import TeReviewError
from .te_judgment import worksheet
from .te_report import bundle
from .te_review import write
from .te_worksheet import checked, matched, read

# The sections whose entries judge a candidate by its digest; mcp_ab and the decision judge none.
SECTIONS = (
    CarrySection.redirects,
    CarrySection.aborts,
    CarrySection.paid_facts,
    CarrySection.learned_facts,
    CarrySection.imports,
    CarrySection.not_run,
)
REF_FIELDS = ("receipt_ref", "origin_ref", "use_ref", "evidence_ref")


def identity(found: BaseModel, **named: object) -> str:
    """What a row, receipt or candidate is, apart from the refs a collection numbers it by.

    named: the fields that hold refs, given instead as what those refs name.
    """
    shown = found.model_dump(mode="json", exclude={"ref", "digest", "receipts", "path", *named})
    return json.dumps(shown | named, sort_keys=True)


def identities(evidence: Evidence) -> dict[str, str]:
    """Every ref of the evidence, by what it names.

    A candidate is named without its receipts and digest, which hold receipt refs, and a receipt without the
    path of its copy, which holds its own ref; a fold's import and session, and a receipt's links, are named
    by what they name.
    """
    found = {row.ref: identity(row) for row in evidence.rows}
    found |= {candidate.ref: identity(candidate) for candidate in [*evidence.redirects, *evidence.facts]}
    found |= {candidate.ref: identity(candidate) for candidate in evidence.imports}
    found |= {
        fold.ref: identity(fold, import_ref=found[fold.import_ref], session_ref=found[fold.session_ref])
        for fold in evidence.import_folds
    }
    found |= {
        receipt.ref: identity(receipt, links=sorted(found[link] for link in receipt.links))
        for receipt in evidence.receipts
    }
    return found


class Translation:
    """A's refs as B's: the one ref of B that names the same thing, else None.

    Not a model: it holds no data of its own, only lookups into the two generated Evidence models it is built
    from, and is never read or written as JSON; pydantic takes Evidence as it is and has no index to give a
    row, receipt or candidate by what it names, apart from its ref.
    """

    def __init__(self, a: Evidence, b: Evidence) -> None:
        self.a = identities(a)
        self.b: dict[str, list[str]] = {}
        for ref, key in identities(b).items():
            self.b.setdefault(key, []).append(ref)

    def ref(self, ref: str) -> str | None:
        found = self.b.get(self.a[ref], [])
        return found[0] if len(found) == 1 else None


def absolute(flag: str, given: str) -> Path:
    path = Path(given)
    if not path.is_absolute():
        msg = f"--{flag} is relative; give its absolute path"
        raise TeReviewError(ErrorCode.RELATIVE_PATH, msg)
    return path


def judged(folder: Path, collection: Collection, evidence: Evidence, sheet: Worksheet) -> Worksheet:
    """sheet with every section's template entries, once its collection's checks accept it."""
    checked(folder, collection, evidence, sheet)
    template = worksheet(collection.collection_id, evidence)
    return sheet.model_copy(
        update={section: matched(section, getattr(sheet, section), getattr(template, section)) for section in SECTIONS}
    )


def placed[E: (WorksheetRedirect, WorksheetAbort, WorksheetPaidFact, WorksheetFact, WorksheetImport, WorksheetNotRun)](
    entry: E, digests: Counter[str], candidates: list[E], translation: Translation
) -> E | CarryReason:
    """entry as B's worksheet gives it: on B's candidate of its digest, with B's refs; else why it cannot be."""
    targets = [found for found in candidates if found.digest == entry.digest]
    if not targets:
        return CarryReason.changed
    # A digest that names more than one candidate on either side does not say which judgment is whose.
    if len(targets) > 1 or digests[entry.digest] > 1:
        return CarryReason.ambiguous
    refs = {name: translation.ref(ref) for name in REF_FIELDS if (ref := getattr(entry, name, None)) is not None}
    if None in refs.values():
        return CarryReason.ref_not_in_b
    return entry.model_copy(update={"ref": targets[0].ref, **refs})


def carry(options: TeReviewCarry) -> None:
    a, b, out = absolute("from", options.from_), absolute("to", options.to), absolute("out", options.out)
    if out.exists():
        raise TeReviewError(ErrorCode.OUT_EXISTS, f"{out} exists; a worksheet is never rewritten")
    a_collection, a_evidence = bundle(a)
    b_collection, b_evidence = bundle(b)
    given = judged(a, a_collection, a_evidence, read(a, options.worksheet))
    a_template = worksheet(a_collection.collection_id, a_evidence)
    sheet = judged(b, b_collection, b_evidence, read(b, None))
    b_template = worksheet(b_collection.collection_id, b_evidence)
    translation = Translation(a_evidence, b_evidence)
    summary = CarrySummary(collection_id=b_collection.collection_id, carried=[], not_carried=[], conflicts=[])
    for section in SECTIONS:
        candidates = getattr(b_template, section)
        digests = Counter(entry.digest for entry in getattr(a_template, section))
        for entry, template in zip(getattr(given, section), getattr(a_template, section), strict=True):
            if entry == template:
                continue
            moved = placed(entry, digests, candidates, translation)
            if isinstance(moved, CarryReason):
                summary.not_carried.append(NotCarried(section=section, from_ref=entry.ref, reason=moved))
                continue
            current = getattr(sheet, section)
            unjudged = next(found for found in candidates if found.ref == moved.ref)
            # B's own worksheet judges it already, and otherwise: B's judgment stays.
            if next(found for found in current if found.ref == moved.ref) not in (unjudged, moved):
                summary.conflicts.append(CarryConflict(section=section, from_ref=entry.ref, to_ref=moved.ref))
                continue
            entries = [moved if found.ref == moved.ref else found for found in current]
            sheet = sheet.model_copy(update={section: entries})
            summary.carried.append(Carried(section=section, from_ref=entry.ref, to_ref=moved.ref))
    for section in (CarrySection.mcp_ab, CarrySection.decision):
        if getattr(given, section) != getattr(a_template, section):
            summary.not_carried.append(NotCarried(section=section, from_ref=None, reason=CarryReason.no_candidate))
    # The new worksheet is written only once B's checks accept it whole, as report --worksheet reads it.
    checked(b, b_collection, b_evidence, sheet)
    write(out.parent, out.name, (sheet.model_dump_json(indent=2) + "\n").encode())
    sys.stdout.write(summary.model_dump_json() + "\n")
