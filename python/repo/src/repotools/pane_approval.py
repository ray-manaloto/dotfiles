"""A commit needs the reviewer pane's approval of HEAD and the whole index, read from Codex's own session log."""

# Precedent for gating a commit on what is staged: onlygian/G-Forge@5ed9839b hooks/pre-commit:150-155 and
# CEDRIC-code1982/Mivro@715fa888 scripts/review-gate.sh:20,37 compare git write-tree. This hashes ls-files
# instead: write-tree writes objects, and the read-only reviewer must be able to compute the same value.
# A local record: anyone running as this user can edit the log or the pin. See AGENTS.md.

import os
import subprocess
from pathlib import Path
from typing import Any

from .models import Message, PanePin, RolloutLine, SessionMeta, TaskEvent, TurnContext

APPROVAL = "PANE-APPROVE"


def git(*args: str, stdin: str | None = None) -> str:
    return subprocess.run(["git", *args], input=stdin, capture_output=True, check=True, text=True).stdout


def fingerprint() -> str:
    # From the root, the reviewer's own command gives these bytes:
    # { git rev-parse HEAD; git ls-files -s; } | git hash-object --stdin
    # :/ and --full-name keep the whole index when run from a subfolder, where ls-files lists only that folder.
    listing = git("ls-files", "-s", "--full-name", ":/")
    return git("hash-object", "--stdin", stdin=git("rev-parse", "HEAD") + listing).strip()


def pin_file() -> Path:
    return Path(git("rev-parse", "--git-path", "review-python.pane-session").strip())


def pin(session: PanePin) -> None:
    pin_file().write_text(session.session + "\n")


def pinned() -> PanePin:
    path = pin_file()
    if not path.exists():
        msg = "no reviewer session is pinned; mise run //repo:pane-pin <session id>"
        raise ValueError(msg)
    return PanePin(session=path.read_text().strip())


def rollout(session: str) -> str:
    home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    found = sorted((home / "sessions").glob(f"**/rollout-*-{session}.jsonl"))
    if len(found) != 1:
        msg = f"expected one rollout for session {session}, found {len(found)}"
        raise ValueError(msg)
    return found[0].read_text()


def answer_text(message: Message) -> str:
    if len(message.content) != 1 or message.content[0].type != "output_text":
        msg = "a final answer is not one output_text part"
        raise ValueError(msg)
    return message.content[0].text


class Turns:
    """Walks a rollout to its last completed turn; an order the log can't vouch for is refused."""

    def __init__(self, session: str) -> None:
        self.session = session
        self.meta: SessionMeta | None = None
        self.running: str | None = None
        self.context: TurnContext | None = None
        self.answer: str | None = None
        self.done: tuple[TurnContext, str] | None = None

    def session_meta(self, payload: dict[str, Any]) -> None:
        seen = SessionMeta.model_validate(payload)
        if seen.id != self.session or self.meta not in (None, seen):
            msg = f"the rollout holds session {seen.id}, not only {self.session}"
            raise ValueError(msg)
        self.meta = seen

    def turn_context(self, payload: dict[str, Any]) -> None:
        seen = TurnContext.model_validate(payload)
        if seen.turn_id != self.running or self.context not in (None, seen):
            msg = f"turn settings for {seen.turn_id} conflict or belong to no running turn"
            raise ValueError(msg)
        self.context = seen

    def message(self, payload: dict[str, Any]) -> None:
        message = Message.model_validate(payload)
        if message.role == "assistant" and message.phase == "final_answer":
            # Refused, or a later answer outside a turn would leave an older approval standing.
            if self.running is None or self.context is None:
                msg = "a final answer sits outside a turn with settings"
                raise ValueError(msg)
            self.answer = answer_text(message)

    def task_started(self, payload: dict[str, Any]) -> None:
        if self.running is not None:
            msg = f"turn {self.running} never completed"
            raise ValueError(msg)
        self.running = TaskEvent.model_validate(payload).turn_id
        self.context = self.answer = self.done = None

    def task_complete(self, payload: dict[str, Any]) -> None:
        event = TaskEvent.model_validate(payload)
        context, answer = self.context, self.answer
        if event.turn_id != self.running or context is None or answer is None or event.last_agent_message != answer:
            msg = f"turn {event.turn_id} completed without matching settings and answer"
            raise ValueError(msg)
        self.done = (context, answer)
        self.running = None

    def read(self, line: str) -> None:
        record = RolloutLine.model_validate_json(line)
        kind = record.payload.get("type")
        handlers = {
            ("session_meta", kind): self.session_meta,
            ("turn_context", kind): self.turn_context,
            ("response_item", "message"): self.message,
            ("event_msg", "task_started"): self.task_started,
            ("event_msg", "task_complete"): self.task_complete,
        }
        handler = handlers.get((record.type, kind))
        if handler is not None:
            handler(record.payload)


def last_turn(log: str, session: str) -> tuple[SessionMeta, TurnContext, str]:
    turns = Turns(session)
    for line in log.splitlines():
        turns.read(line)
    if turns.meta is None or turns.done is None or turns.running is not None:
        msg = "the rollout has no session or no completed last turn"
        raise ValueError(msg)
    return turns.meta, *turns.done


def read_only(context: TurnContext) -> bool:
    files = context.permission_profile.file_system
    return (
        context.approval_policy == "never"
        and context.sandbox_policy.type == "read-only"
        and files.type == "restricted"
        and bool(files.entries)
        and all(entry.access == "read" for entry in files.entries)
    )


def check() -> None:
    session = pinned().session
    meta, context, answer = last_turn(rollout(session), session)
    root = Path(git("rev-parse", "--show-toplevel").strip()).resolve()
    if meta.forked_from_id is not None or {Path(meta.cwd).resolve(), Path(context.cwd).resolve()} != {root}:
        msg = f"session {session} is a fork or did not run in {root}"
        raise ValueError(msg)
    if not read_only(context):
        msg = f"the last turn of session {session} was not read-only"
        raise ValueError(msg)
    wanted = f"{APPROVAL} {fingerprint()}"
    if answer.split("\n")[-1] != wanted:
        msg = f"the reviewer's last answer does not end with: {wanted}"
        raise ValueError(msg)
