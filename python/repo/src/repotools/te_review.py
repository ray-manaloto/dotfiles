"""repotools te-review: freeze TokenEconomizer's Claude ledger rows of a window into an evidence collection."""

# Pattern: ryoppippi/ccusage@f674ef6 rust/crates/ccusage-core/src/date_utils.rs:205-224 reads --since/--until
# as the half-open instants [since 00:00, the day after until 00:00) in --timezone, over append-only JSONL
# logs, and rust/adapters/claude/src/lib.rs:335-343 collapses a row read twice by its identity key.
# simonmichael/hledger@9ede2b0 hledger-lib/Hledger/Data/Types.hs:489-491 leaves each ledger entry's
# meaning to an owner-set status mark, and hledger/Hledger/Cli/CliOptions.hs:224 ends a period before
# --end. Here the owner's judgment comes later, against the frozen evidence this writes.

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

from pydantic import ValidationError

from .models import (
    CodedFailure,
    Collection,
    ErrorCode,
    Evidence,
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
    Versions,
    Window,
)

ADAPTER = "tokeneconomizer-0.1.0"
SCHEMA = 1
# The TokenEconomizer 0.1.0 files whose ledger rows SessionRow and OverheadRow mirror, by sha256.
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
)
# What a charge is, from the class of the session it names.
CHARGE_CLASS = {
    RowClass.in_window: RowClass.matched,
    RowClass.outside_window: RowClass.not_selected,
    RowClass.missing_end: RowClass.not_selected,
    RowClass.conflict: RowClass.ambiguous,
    RowClass.ambiguous: RowClass.ambiguous,
}


class CollectError(Exception):
    """A refusal; collect leaves nothing behind when it raises one.

    The generated CodedFailure is a pydantic model, not an exception, so it can't be raised: this
    carries it to cli.main, which prints it.
    """

    def __init__(self, code: ErrorCode, error: str) -> None:
        super().__init__(error)
        self.failure = CodedFailure(code=code, error=error)


def window(options: TeReviewCollect) -> Window:
    if options.until < options.since:
        msg = f"--until {options.until} is before --since {options.since}"
        raise CollectError(ErrorCode.BAD_WINDOW, msg)
    try:
        zone = ZoneInfo(options.tz)
    # ZoneInfoNotFoundError (a KeyError) for an unknown name, ValueError for a malformed one.
    except KeyError, ValueError:
        raise CollectError(ErrorCode.BAD_TIMEZONE, f"--tz {options.tz} is not an IANA time zone") from None
    return Window(
        since=options.since,
        until=options.until,
        tz=options.tz,
        start=datetime.combine(options.since, time(), zone),
        end=datetime.combine(options.until + timedelta(days=1), time(), zone),
    )


def state_root(options: TeReviewCollect) -> Path:
    """--te-root, else $TOKENECONOMIZER_HOME, else TokenEconomizer's default (plugin/paths.py state_root)."""
    root = options.te_root or os.environ.get("TOKENECONOMIZER_HOME") or Path.home() / ".tokeneconomizer"
    return Path(root).absolute()


def claude_ledgers(root: Path) -> list[Path]:
    """Every repos/<label>/claude/ledger.jsonl, by label. Path.glob would skip a folder it can't read;
    here that fails the collection, so no store goes missing unnoticed."""
    try:
        stores = sorted((root / "repos").iterdir())
    except FileNotFoundError, NotADirectoryError:
        return []
    except OSError as error:
        raise CollectError(ErrorCode.UNREADABLE, f"{root / 'repos'}: {error.strerror}") from None
    found = []
    for store in stores:
        path = store / "claude" / "ledger.jsonl"
        try:
            path.stat()
        except FileNotFoundError, NotADirectoryError:
            continue  # not a Claude store
        except OSError as error:
            raise CollectError(ErrorCode.UNREADABLE, f"{path}: {error.strerror}") from None
        found.append(path)
    return found


def read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        raise CollectError(ErrorCode.UNREADABLE, f"{path}: {error.strerror}") from None


def parse(store: str, source: str, data: bytes) -> list[LedgerRead]:
    """Every row of one ledger, or a refusal: no line is skipped."""
    lines = data.split(b"\n")
    if lines[-1]:
        raise CollectError(ErrorCode.TRUNCATED_LINE, f"{source}:{len(lines)} has no line end")
    found = []
    for number, line in enumerate(lines[:-1], 1):
        try:
            raw = json.loads(line)
        # json's errors and a line that is not UTF-8 (UnicodeDecodeError) are both ValueErrors.
        except ValueError:
            raise CollectError(ErrorCode.MALFORMED_LINE, f"{source}:{number} is not JSON") from None
        place = {"source": source, "line": number}
        try:
            found.append(LedgerRead.model_validate({"store": store, "place": place, "record": raw, "row": raw}))
        except ValidationError:
            keys = sorted(raw) if isinstance(raw, dict) else [type(raw).__name__]
            fingerprint = hashlib.sha256(json.dumps(keys).encode()).hexdigest()[:12]
            msg = f"{source}:{number} has unknown schema fingerprint {fingerprint} for {ADAPTER}"
            raise CollectError(ErrorCode.UNKNOWN_SCHEMA, msg) from None
    return found


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


def build(root: Path, ledgers: list[Path], span: Window, into: Path) -> str:
    """Write evidence.json, collection.json and a copy of every source into a private folder; return the
    collection id, which hashes only what the folder holds, so a reader can check it from the folder alone."""
    sources: dict[str, bytes] = {}
    reads = []
    for path in ledgers:
        source = path.relative_to(root).as_posix()
        sources[source] = read_bytes(path)
        reads.extend(parse(path.parent.parent.relative_to(root).as_posix(), source, sources[source]))
    evidence = (Evidence(rows=classify(reads, span)).model_dump_json(indent=2) + "\n").encode()
    write(into, "evidence.json", evidence)
    for path in ledgers:
        source = path.relative_to(root).as_posix()
        if read_bytes(path) != sources[source]:
            raise CollectError(ErrorCode.SOURCE_CHANGED, f"{source} changed while it was read")
    versions = Versions(adapter=ADAPTER, schema=SCHEMA, mirrors=list(MIRRORS))
    digest = hashlib.sha256(
        framed(span.model_dump_json().encode()) + framed(versions.model_dump_json(by_alias=True).encode())
    )
    for source, data in sources.items():
        write(into, f"sources/{source}", data)
        digest.update(framed(source.encode()) + framed(data))
    digest.update(framed(evidence))
    collected_at = datetime.now(span.start.tzinfo)
    collection = Collection(
        collection_id=digest.hexdigest(),
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
    return collection.collection_id


def collect(options: TeReviewCollect) -> None:
    span = window(options)
    root = state_root(options)
    ledgers = claude_ledgers(root)
    if not ledgers:
        raise CollectError(ErrorCode.NO_LEDGER, f"{root} holds no repos/*/claude/ledger.jsonl")
    out = Path(options.out).absolute()
    # Reserved first, so no other collect takes the name; the build replaces this empty folder.
    try:
        out.mkdir(mode=0o700)
    except FileExistsError:
        raise CollectError(ErrorCode.OUT_EXISTS, f"{out} exists; a collection is never rewritten") from None
    made = [out]  # what a failure removes: the reserved folder, then the staging folder until it moves
    try:
        staging = Path(tempfile.mkdtemp(prefix=f".{out.name}.", dir=out.parent))  # 0700, and only this run's
        made.append(staging)
        collection_id = build(root, ledgers, span, staging)
        staging.rename(out)  # onto the empty reserved folder; fails if anything was put in it
        made.remove(staging)
        write(out, "COMPLETE", (collection_id + "\n").encode())
    except BaseException:  # any failure, including an interrupt: leave no folder behind
        for folder in made:
            shutil.rmtree(folder)
        raise
