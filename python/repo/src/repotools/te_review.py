"""repotools te-review: freeze TokenEconomizer's Claude ledger rows of a window into an evidence collection."""

# Pattern: ryoppippi/ccusage@f674ef6 rust/crates/ccusage-core/src/date_utils.rs:205-224 reads --since/--until
# as the half-open instants [since 00:00, the day after until 00:00) in --timezone, over append-only JSONL
# logs, and rust/adapters/claude/src/lib.rs:335-343 collapses a row read twice by its identity key.
# simonmichael/hledger@9ede2b0 hledger-lib/Hledger/Data/Types.hs:489-491 leaves each ledger entry's
# meaning to an owner-set status mark, and hledger/Hledger/Cli/CliOptions.hs:224 ends a period before
# --end. Here the owner's judgment comes later, against the frozen evidence this writes.

import contextlib
import functools
import hashlib
import json
import math
import os
import shutil
import tempfile
from collections import defaultdict
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import te_judgment
from .models import (
    Collection,
    ErrorCode,
    EvidenceRow,
    Label,
    LedgerRead,
    Mirror,
    OverheadRow,
    RowClass,
    RowKind,
    SessionRow,
    SourceFile,
    SourceLine,
    TeReviewCollect,
    TeReviewReceiptsDraft,
    Versions,
    Window,
)
from .te_io import ADAPTER, TeReviewError, absolute, conform, json_lines, listing, present, read_bytes

SCHEMA = 1
# The TokenEconomizer 0.1.0 files whose ledger rows and state files the models mirror, by sha256.
MIRRORS = (
    Mirror(
        path="lib/tokeneconomizer/ledger.py", sha256="24e5af172815691086857664acffe34ec8899bfa350fc09d6a541cb05f2da910"
    ),
    Mirror(
        path="lib/tokeneconomizer/plugin/accounting.py",
        sha256="682eb4f575fc2d8eca0291f1754e77271e6a59d8dec1f930db0f9782b30bc45a",
    ),
    Mirror(
        path="lib/tokeneconomizer/plugin/fold.py",
        sha256="02072acb7112d4a69f4c4d73484028fe83e722180506ba0c5450a3fbdc14528c",
    ),
    Mirror(
        path="lib/tokeneconomizer/plugin/judge.py",
        sha256="b800eb6b080513880299eb6ea1f056bcaba4e7eb6d57c34f02ac436ce23e0e82",
    ),
    Mirror(
        path="lib/tokeneconomizer/plugin/store.py",
        sha256="8f4ef9b2da04e2e0dcc7c9330d4c39d1e4529ee28b77669bf0eff29e904b2445",
    ),
    Mirror(
        path="lib/tokeneconomizer/plugin/paths.py",
        sha256="19606cf3c20b9423e214006e3cbbe04cd0833fcfad3e4700c9c74c77e5dea65b",
    ),
    Mirror(
        path="lib/tokeneconomizer/plugin/controller.py",
        sha256="72cdd314665ada463a017a36f8f371de6f97d7191f1a3a5bf5ce459e01bc569f",
    ),
    Mirror(
        path="lib/tokeneconomizer/plugin/history.py",
        sha256="c897948709856734c9f1854c82fc2705c04c2bb17abbea38f2fd29811d2501aa",
    ),
    Mirror(
        path="lib/tokeneconomizer/plugin/config.py",
        sha256="35c747e91ba7506bee466459ed368ea4f2b39c7e2af109675372d67fc145af23",
    ),
    Mirror(
        path="lib/tokeneconomizer/microskills/lifecycle.py",
        sha256="cae8db6681956c35d7f73bf9e43b466f98f71c341c0c6e6c5b6ce465c216f3db",
    ),
    Mirror(
        path="lib/tokeneconomizer/microskills/distiller.py",
        sha256="9eae456df180cb1a629d3ff6a68d7e4c2fc732eb183e6ba016287e35dcf2a162",
    ),
    Mirror(
        path="lib/tokeneconomizer/microskills/envfacts.py",
        sha256="13f25143be7c5893049e811dd78df863bac908bae1e27299dcffa49c7ad7d591",
    ),
)
# What a charge is, from the class of the session it names.
CHARGE_CLASS = {
    RowClass.in_window: RowClass.matched,
    RowClass.outside_window: RowClass.not_selected,
    RowClass.missing_end: RowClass.not_selected,
    RowClass.conflict: RowClass.ambiguous,
    RowClass.ambiguous: RowClass.ambiguous,
}


def window(options: TeReviewCollect | TeReviewReceiptsDraft) -> Window:
    if options.until < options.since:
        msg = f"--until {options.until} is before --since {options.since}"
        raise TeReviewError(ErrorCode.BAD_WINDOW, msg)
    try:
        zone = ZoneInfo(options.tz)
    # ZoneInfoNotFoundError (a KeyError) for an unknown name, ValueError for a malformed one.
    except KeyError, ValueError:
        raise TeReviewError(ErrorCode.BAD_TIMEZONE, f"--tz {options.tz} is not an IANA time zone") from None
    return Window(
        since=options.since,
        until=options.until,
        tz=options.tz,
        start=datetime.combine(options.since, time(), zone),
        end=datetime.combine(options.until + timedelta(days=1), time(), zone),
    )


def state_root(options: TeReviewCollect | TeReviewReceiptsDraft) -> Path:
    """--te-root, else $TOKENECONOMIZER_HOME, else TokenEconomizer's default (plugin/paths.py state_root)."""
    root = options.te_root or os.environ.get("TOKENECONOMIZER_HOME") or Path.home() / ".tokeneconomizer"
    return Path(root).absolute()


def claude_ledgers(root: Path) -> list[Path]:
    """Every repos/<label>/claude/ledger.jsonl, by label; an unreadable store fails, so none goes missing."""
    return [path for store in listing(root / "repos") if present(path := store / "claude" / "ledger.jsonl")]


def parse(store: str, source: str, data: bytes) -> list[LedgerRead]:
    """Every row of one ledger, or a refusal: no line is skipped."""
    return [
        conform(
            LedgerRead,
            f"{source}:{number}",
            {"store": store, "place": {"source": source, "line": number}, "record": raw, "row": raw},
        )
        for number, raw in json_lines(source, data)
    ]


def session_class(variants: int, stores: int, ended: float | None, span: Window) -> RowClass:
    if variants > 1:
        return RowClass.conflict
    if stores > 1:
        return RowClass.ambiguous
    if ended is None or not math.isfinite(ended):
        return RowClass.missing_end
    inside = span.start.timestamp() <= ended < span.end.timestamp()
    return RowClass.in_window if inside else RowClass.outside_window


def classify(reads: list[LedgerRead], span: Window) -> list[EvidenceRow]:
    """Each distinct row once, in the order first read, with its class and every place it was read."""
    groups: dict[tuple, dict[str, list[LedgerRead]]] = defaultdict(lambda: defaultdict(list))
    stores: dict[str, set[str]] = defaultdict(set)
    ends: dict[tuple, float | None] = {}  # a session's end; when its copies differ, it is a conflict anyway
    for read in reads:
        record = read.record
        job = record.job if isinstance(record, OverheadRow) else None
        key = (RowKind(record.kind), read.store, record.host, record.session_id, job)
        groups[key][json.dumps(read.row, sort_keys=True)].append(read)
        if isinstance(record, SessionRow):
            stores[record.session_id].add(read.store)
            ends[key] = record.ended
    sessions = {
        key[1:4]: session_class(len(variants), len(stores[key[3]]), ends[key], span)
        for key, variants in groups.items()
        if key[0] is RowKind.session
    }
    found: list[tuple[SourceLine, dict]] = []
    for (kind, store, host, session_id, job), variants in groups.items():
        if kind is RowKind.session:
            row_class = sessions[store, host, session_id]
        elif job is None:
            row_class = RowClass.ambiguous
        elif len(variants) > 1:
            row_class = RowClass.conflict
        elif (store, host, session_id) in sessions:
            row_class = CHARGE_CLASS[sessions[store, host, session_id]]
        else:
            row_class = RowClass.unmatched
        found.extend(
            (
                copies[0].place,
                {
                    "kind": kind,
                    "row_class": row_class,
                    "store": store,
                    "host": host,
                    "session_id": session_id,
                    "job": job,
                    "count": len(copies),
                    "lines": [copy.place for copy in copies],
                    "row": copies[0].row,
                },
            )
            for copies in variants.values()
        )
    found.sort(key=lambda item: (item[0].source, item[0].line))
    return [EvidenceRow(ref=f"E{number:05d}", **fields) for number, (_, fields) in enumerate(found, 1)]


def write(into: Path, name: str, data: bytes) -> None:
    """A new private file at name under into; the folders name passes through are made private too."""
    for folder in reversed(Path(name).parents[:-1]):  # parents ends with ".", which is into itself
        (into / folder).mkdir(mode=0o700, exist_ok=True)
    descriptor = os.open(into / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as file:
        file.write(data)


def framed(data: bytes) -> bytes:
    """data behind its length, so that no two sequences of parts hash alike."""
    return len(data).to_bytes(8, "big") + data


def collection_id(span: Window, versions: Versions, sources: dict[str, bytes], evidence: bytes) -> str:
    """sha256 over the window, the versions, each source's path and bytes and evidence.json, each part framed."""
    digest = hashlib.sha256(
        framed(span.model_dump_json().encode()) + framed(versions.model_dump_json(by_alias=True).encode())
    )
    for source, data in sources.items():
        digest.update(framed(source.encode()) + framed(data))
    digest.update(framed(evidence))
    return digest.hexdigest()


def build(root: Path, ledgers: list[Path], options: TeReviewCollect, span: Window, into: Path) -> str:
    """Write evidence.json, collection.json, worksheet.json and a copy of every source into a private folder;
    return the collection id, which hashes only what the folder holds (the worksheet aside, which the owner
    fills), so a reader can check it from the folder alone."""
    origins = {path.relative_to(root).as_posix(): path for path in ledgers}
    origins.update(te_judgment.gather(root, options))
    origins = dict(sorted(origins.items()))  # one order for the bundle, the id and the candidates
    sources = {source: read_bytes(path) for source, path in origins.items()}
    reads = []
    for path in ledgers:
        source = path.relative_to(root).as_posix()
        reads.extend(parse(path.parent.parent.relative_to(root).as_posix(), source, sources[source]))
    judged = te_judgment.judge(classify(reads, span), sources, origins, span)
    # json.dumps, as TokenEconomizer's ledger.py writes rows: pydantic's JSON writes NaN and Infinity as null.
    evidence = (json.dumps(judged.model_dump(), indent=2, default=datetime.isoformat) + "\n").encode()
    write(into, "evidence.json", evidence)
    for source, path in origins.items():
        if read_bytes(path) != sources[source]:
            raise TeReviewError(ErrorCode.SOURCE_CHANGED, f"{source} changed while it was read")
    versions = Versions(adapter=ADAPTER, schema=SCHEMA, mirrors=list(MIRRORS))
    for source, data in sources.items():
        write(into, f"sources/{source}", data)
    collected_at = datetime.now(span.start.tzinfo)
    collection = Collection(
        collection_id=collection_id(span, versions, sources, evidence),
        collected_at=collected_at,
        label=Label.INTERIM if collected_at < span.end else Label.FINAL,
        window=span,
        sources=[
            SourceFile(
                path=source,
                bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
                lines=data.count(b"\n"),
            )
            for source, data in sources.items()
        ],
        versions=versions,
    )
    write(into, "collection.json", (collection.model_dump_json(indent=2, by_alias=True) + "\n").encode())
    sheet = te_judgment.worksheet(collection.collection_id, judged)
    write(into, "worksheet.json", (sheet.model_dump_json(indent=2) + "\n").encode())
    return collection.collection_id


def collect(options: TeReviewCollect) -> None:
    absolute("out", options.out, "the collection's")
    span = window(options)
    root = state_root(options)
    ledgers = claude_ledgers(root)
    if not ledgers:
        raise TeReviewError(ErrorCode.NO_LEDGER, f"{root} holds no repos/*/claude/ledger.jsonl")
    out = Path(options.out)
    # Reserved first, so no other collect takes the name; the build replaces this empty folder.
    try:
        out.mkdir(mode=0o700)
    except FileExistsError:
        raise TeReviewError(ErrorCode.OUT_EXISTS, f"{out} exists; a collection is never rewritten") from None
    # What a failure undoes, last first. Until the build moves in, only the empty reservation is this
    # run's: rmdir removes it, and leaves it, with whatever someone else put in it, if it is not empty.
    undo = [out.rmdir]
    try:
        staging = Path(tempfile.mkdtemp(prefix=f".{out.name}.", dir=out.parent))  # 0700, and only this run's
        undo.append(functools.partial(shutil.rmtree, staging))
        collection_id = build(root, ledgers, options, span, staging)
        staging.rename(out)  # onto the empty reserved folder; fails if anything was put in it
        undo = [functools.partial(shutil.rmtree, out)]  # everything in it now is this run's build
        write(out, "COMPLETE", (collection_id + "\n").encode())
    except BaseException:  # any failure, including an interrupt: leave nothing of this run behind
        for step in reversed(undo):
            with contextlib.suppress(OSError):  # the failure that got here is the one to report
                step()
        raise
