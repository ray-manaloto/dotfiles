"""repotools te-review receipts draft: a receipt manifest for collect, from transcripts and TE state."""

import hashlib
import os
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from .models import (
    DraftCounts,
    DraftGap,
    DraftSummary,
    DraftUncovered,
    ErrorCode,
    EvidenceRow,
    FactMechanism,
    HookOutput,
    ManifestRole,
    Receipt,
    ReceiptKind,
    ReceiptManifest,
    RedirectEvent,
    RedirectKind,
    RedirectLink,
    RowClass,
    RowKind,
    TeReviewReceiptsDraft,
    TranscriptAttachment,
    TranscriptRecord,
    Window,
)
from .te_io import TeReviewError, conform, json_file, json_lines, listing, read_bytes
from .te_judgment import learned_facts, manifest, redirect_events, state_files
from .te_review import classify, claude_ledgers, parse, state_root, window

# A transcript stamps in milliseconds, so a record may read as up to 1 ms before the hook logged its event;
# the host runs a PostToolUse or PostToolUseFailure hook for at most its 60 s timeout (the plugin's hooks.json).
CLOCK_S = 0.001
HOOK_S = 60.0
POST_TOOL = ("PostToolUse", "PostToolUseFailure")
# How the notice plugin/controller.py post_tool returns beside a nudge's context opens, up to its reason.
NUDGED = "TokenEconomizer nudged this turn ("
# How its notice of an abort opens, up to its reason; ClaudeCode relays it as context too (plugin/hosts.py).
STUCK = "TokenEconomizer: this turn still looks stuck after a redirect ("
# The heading microskills distiller.py render puts first in the manual it injects at SessionStart.
MANUAL = "# repo operating manual ("


def transcripts(folder: Path, wanted: set[str]) -> dict[str, list[Path]]:
    """Every <session id>.jsonl under folder at any depth, for the wanted ids; an unreadable folder fails."""
    found: dict[str, list[Path]] = {}
    for entry in listing(folder):
        if entry.is_dir(follow_symlinks=False):
            for session_id, paths in transcripts(entry, wanted).items():
                found.setdefault(session_id, []).extend(paths)
        elif entry.suffix == ".jsonl" and entry.stem in wanted:
            found.setdefault(entry.stem, []).append(entry)
    return found


def ended(row: EvidenceRow, span: Window) -> bool:
    """Whether a session row ended in the window, whatever its class."""
    end = row.row["ended"]
    return end is not None and span.start.timestamp() <= end < span.end.timestamp()


def records(path: Path, data: bytes) -> list[tuple[datetime, TranscriptAttachment]]:
    """A transcript's timestamped attachments; a line that is not a record fails the draft."""
    found = []
    for number, raw in json_lines(str(path), data):
        record = conform(TranscriptRecord, f"{path}:{number}", raw)
        if record.attachment is not None and record.timestamp is not None:
            found.append((record.timestamp, record.attachment))
    return found


def notice(event: RedirectEvent) -> tuple[str, str]:
    """How the notice plugin/controller.py post_tool returns for this event opens, and that opening up to the
    event's own reason: a nudge's names its reason; an abort's, its reason and the turn's tool calls."""
    short = event.reason.split(":")[0]
    if event.kind is RedirectKind.abort:
        return STUCK, f"{STUCK}{short}, {event.tool_calls} tool calls). "
    return NUDGED, f"{NUDGED}{short}):"


def printed(source: str, part: TranscriptAttachment, opener: str, notice: str) -> str | None:
    """The context a hook printed beside this event's notice: a hook_success whose stdout, read as the hook's
    JSON, has the notice plugin/controller.py post_tool returns as its systemMessage and a context beside it.
    A nudge's text is never logged and a judge writes its own, and an abort's context is the host's relay of
    its notice, so only the output that printed the notice names it; the command field does not, as
    transcripts show the plugin's path or "command hook N"."""
    if part.type != "hook_success" or part.stdout is None or opener not in part.stdout:
        return None
    output = conform(HookOutput, f"{source}: {part.tool_use_id}'s hook output", json_file(source, part.stdout.encode()))
    context = output.hook_specific_output.additional_context if output.hook_specific_output else None
    message = output.system_message
    return context if message is not None and message.startswith(notice) else None


def candidates(
    source: str, event: RedirectEvent, seen: list[tuple[datetime, TranscriptAttachment]]
) -> list[tuple[datetime, str | None]]:
    """The hook outputs that show the host received this nudge or abort, within the hook's timeout of the event:
    one that printed its notice and context, where the host attached exactly that context to the same tool call."""
    opener, named = notice(event)
    hooked = [(when, part) for when, part in seen if part.hook_event in POST_TOOL and part.tool_use_id is not None]
    attached = {
        (part.tool_use_id, tuple(part.content))
        for _, part in hooked
        if part.type == "hook_additional_context" and isinstance(part.content, list)
    }
    found = []
    for when, part in hooked:
        context = printed(source, part, opener, named)
        if (
            context
            and (part.tool_use_id, (context,)) in attached
            and event.at - CLOCK_S <= when.timestamp() <= event.at + HOOK_S
        ):
            found.append((when, part.tool_use_id))
    return found


def told(seen: list[tuple[datetime, TranscriptAttachment]]) -> list[tuple[datetime, set[str]]]:
    """Each TokenEconomizer manual a SessionStart context shows the agent received, as its lines: a block
    microskills distiller.py render opens with its heading; another hook's block is not the manual."""
    return [
        (when, {line for text in part.content if text.startswith(MANUAL) for line in text.splitlines()[1:]})
        for when, part in seen
        if part.type == "hook_additional_context"
        and part.hook_event == "SessionStart"
        and isinstance(part.content, list)
    ]


def rendered(fact: dict) -> str | None:
    """The line microskills distiller.py renders a manual fact as: its injection, else its claim, else its id."""
    spec = fact["fact"].get("spec")
    text = spec.get("injection", spec.get("claim", spec.get("id"))) if isinstance(spec, dict) else None
    return f"- {text}" if isinstance(text, str) else None


def create(path: Path) -> int:
    """A new file, 0600, for this draft alone: one already there is the owner's, never rewritten."""
    try:
        return os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise TeReviewError(ErrorCode.OUT_EXISTS, f"{path} exists; a draft is never rewritten") from None


def sessions(root: Path, span: Window) -> tuple[dict[str, EvidenceRow], list[str]]:
    """The sessions a receipt can name, each by its one session row in the window, and the ids collect cannot
    resolve to one row: it links a receipt to the one session row with its id across all stores."""
    reads = []
    for path in claude_ledgers(root):
        source = path.relative_to(root).as_posix()
        reads.extend(parse(path.parent.parent.relative_to(root).as_posix(), source, read_bytes(path)))
    named: dict[str, list[EvidenceRow]] = {}
    for row in classify(reads, span):
        if row.kind is RowKind.session:
            named.setdefault(row.session_id, []).append(row)
    chosen = {sid: found[0] for sid, found in named.items() if [row.row_class for row in found] == [RowClass.in_window]}
    shared = [sid for sid, found in named.items() if sid not in chosen and any(ended(row, span) for row in found)]
    return chosen, shared


def manual_lines(state: dict[str, bytes]) -> list[tuple[str, str, str]]:
    """Each manual fact collect can name, as its store, id and rendered line: collect links a fact_injection
    receipt to the one fact with its id, in any store or mechanism."""
    facts = learned_facts(state)
    ids = Counter(found["fact_id"] for found in facts)
    return [
        (found["store"], found["fact_id"], line)
        for found in facts
        if found["mechanism"] is FactMechanism.manual
        and ids[found["fact_id"]] == 1
        and (line := rendered(found)) is not None
    ]


def synthetic_sessions(options: TeReviewReceiptsDraft) -> set[str]:
    if options.synthetic_manifest is None:
        return set()
    given = manifest(ManifestRole.synthetic, read_bytes(Path(options.synthetic_manifest).absolute()))
    return {session_id for listed in given.receipts for session_id in listed.sessions}


def write(path: Path, model: ReceiptManifest) -> None:
    with os.fdopen(create(path), "w") as file:
        file.write(model.model_dump_json(indent=2, exclude_defaults=True) + "\n")


class Drafting:
    """The state a draft reads once, and the receipts and gaps it finds session by session.

    Not a model: it is one draft run's working state, built from the generated RedirectEvent and Receipt and
    never read or written as JSON; what the run writes is the generated ReceiptManifest. pydantic has no place
    to keep a lookup like keys or a running count like undelivered while sessions are read one at a time."""

    def __init__(self, root: Path) -> None:
        state = {source: read_bytes(path) for source, path in state_files(root).items()}
        self.events = [event for _, event in redirect_events(state)]
        # collect links a host_delivery receipt to the one event at its session and time.
        self.keys = Counter((event.session_id, event.at) for event in self.events)
        self.lines = manual_lines(state)
        self.work: list[Receipt] = []
        self.deliveries: list[Receipt] = []
        self.injections: list[Receipt] = []
        self.undelivered: Counter[RedirectKind] = Counter()

    def sent(self, session_id: str) -> list[RedirectEvent]:
        """The session's nudges and aborts a host could have received: a shadow one was never sent."""
        return [event for event in self.events if event.session_id == session_id and not event.shadow]

    def session(self, row: EvidenceRow, path: Path) -> None:
        """The receipts one session's transcript gives: its real work, its delivered nudges and aborts, its
        injected facts."""
        session_id, data = row.session_id, read_bytes(path)
        # Every receipt here is the transcript as read for this draft.
        name, sha = str(path), hashlib.sha256(data).hexdigest()
        mtime = datetime.fromtimestamp(path.stat().st_mtime, UTC)
        self.work.append(
            Receipt(path=name, sha256=sha, timestamp=mtime, kind=ReceiptKind.real_work, sessions=[session_id])
        )
        seen = records(path, data)
        events = self.sent(session_id)
        found = [candidates(name, event, seen) for event in events]
        # A record two events could claim confirms neither: collect would count both delivered.
        claimed = Counter(record for listed in found for record in listed)
        for event, matched in zip(events, found, strict=True):
            if self.keys[(session_id, event.at)] != 1 or len(matched) != 1 or claimed[matched[0]] != 1:
                self.undelivered[event.kind] += 1
                continue
            link = RedirectLink(session_id=session_id, at=event.at)
            self.deliveries.append(
                Receipt(
                    path=name, sha256=sha, timestamp=matched[0][0], kind=ReceiptKind.host_delivery, redirects=[link]
                )
            )
        contexts = told(seen)
        for store, fact_id, line in self.lines:
            times = [when for when, shown in contexts if line in shown]
            if store == row.store and times:
                self.injections.append(
                    Receipt(
                        path=name,
                        sha256=sha,
                        timestamp=min(times),
                        kind=ReceiptKind.fact_injection,
                        sessions=[session_id],
                        facts=[fact_id],
                    )
                )


def draft(options: TeReviewReceiptsDraft) -> None:
    out = Path(options.out)
    # A relative path would land wherever the caller runs from, a checkout under a mise task.
    if not out.is_absolute():
        raise TeReviewError(ErrorCode.RELATIVE_PATH, "--out is relative; give the file's absolute path")
    span = window(options)
    root = state_root(options)
    chosen, shared = sessions(root, span)
    drafting = Drafting(root)
    # collect reads a relative receipt path from the manifest's folder, so every receipt path is absolute.
    projects = Path(options.transcripts or Path.home() / ".claude" / "projects").absolute()
    found = transcripts(projects, set(chosen))
    synthetic = synthetic_sessions(options)
    without = [DraftUncovered(session_id=sid, gap=DraftGap.ambiguous_session) for sid in shared]
    for session_id, row in chosen.items():
        paths = found.get(session_id, [])
        if session_id in synthetic:
            without.append(DraftUncovered(session_id=session_id, gap=DraftGap.synthetic))
        elif len(paths) == 1:
            drafting.session(row, paths[0])
        else:
            gap = DraftGap.many_transcripts if paths else DraftGap.no_transcript
            without.append(DraftUncovered(session_id=session_id, gap=gap))
            drafting.undelivered.update(event.kind for event in drafting.sent(session_id))
    receipts = drafting.work + drafting.deliveries + drafting.injections
    write(out, ReceiptManifest(receipts=receipts))
    counts = DraftCounts(
        real_work=len(drafting.work),
        host_delivery=len(drafting.deliveries),
        fact_injection=len(drafting.injections),
    )
    summary = DraftSummary(
        counts=counts,
        without_receipt=without,
        undelivered_nudges=drafting.undelivered[RedirectKind.nudge],
        undelivered_aborts=drafting.undelivered[RedirectKind.abort],
    )
    sys.stdout.write(summary.model_dump_json() + "\n")
