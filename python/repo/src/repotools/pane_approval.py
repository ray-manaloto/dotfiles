"""A commit needs the reviewer pane's approval of HEAD, the whole index and the message; a pull request, of its text."""

# The approval is read from Codex's own session log. This repository is public, and the reviewer is its leak check.
# Precedent for gating a commit on what is staged: onlygian/G-Forge@5ed9839b hooks/pre-commit:150-155 and
# CEDRIC-code1982/Mivro@715fa888 scripts/review-gate.sh:20,37 compare git write-tree. This hashes ls-files
# instead: write-tree writes objects, and the read-only reviewer must be able to compute the same value.
# Gerrit's commit-msg hook, as vendored in TYPO3/typo3@d389f860 Build/git-hooks/commit-msg:34-46,175-188, hashes
# the message from $1 after git stripspace with the tree and parent; the message is hashed the same way here.
# A pull request's title and body are hashed as they are sent: GitHub stores and renders the body as given.
# A local record: anyone running as this user can edit the log or the pin. See AGENTS.md.

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from . import process
from .models import CommitText, Message, PanePin, PrText, RolloutLine, SessionMeta, TaskEvent, TurnContext

APPROVAL = "PANE-APPROVE"
CITATION_OPEN = "<oai-mem-citation>"
CITATION_CLOSE = "</oai-mem-citation>"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, check=True, text=True).stdout


def hashed(data: bytes) -> str:
    # Bytes, not text: Python's text mode would turn a body's CRLF into LF before hashing.
    # Git 2.56.0 builtin/hash-object.c:23-35, read offline: hashes stdin before output; fingerprints stay read-only.
    # ast-grep-ignore: no-captured-stdin
    done = subprocess.run(["git", "hash-object", "--stdin"], input=data, capture_output=True, check=True)
    return done.stdout.decode().strip()


def head() -> str:
    """HEAD's commit and a newline, or "unborn" and a newline before a repository's first commit.

    rev-parse --verify -q prints nothing and exits 1 when HEAD names no commit yet; any other failure (128 outside a
    repository) is git's own error, raised.
    """
    done = subprocess.run(["git", "rev-parse", "--verify", "-q", "HEAD"], capture_output=True, check=False, text=True)
    if done.returncode == 1:
        return "unborn\n"
    done.check_returncode()
    return done.stdout


def base() -> str:
    """The branch a pull request goes into: origin's default branch, as this clone recorded it."""
    ref = "refs/remotes/origin/HEAD"
    done = subprocess.run(["git", "symbolic-ref", "--short", ref], capture_output=True, check=False, text=True)
    if done.returncode != 0:
        msg = f"{ref} is not set, so origin's default branch is unknown; run git remote set-head origin --auto"
        raise ValueError(msg)
    return done.stdout.strip().removeprefix("origin/")


def stripped(path: str) -> str:
    # git commit cleans the message the same way before it is stored, so a trailing blank line changes nothing.
    # Git 2.56.0 builtin/stripspace.c:61-70, read offline: reads to EOF before output; fingerprints stay read-only.
    # ast-grep-ignore: no-captured-stdin
    return subprocess.run(
        ["git", "stripspace"], input=Path(path).read_text(), capture_output=True, check=True, text=True
    ).stdout


def fingerprint(text: CommitText | PrText, body: bytes | None = None) -> str:
    """What the reviewer approves. From the root, its own command gives these bytes:

    { git rev-parse --verify -q HEAD || echo unborn; git ls-files -s; echo; git stripspace < MESSAGE; } |
      git hash-object --stdin
    { echo "pull request"; git rev-parse --verify -q HEAD || echo unborn; echo "$TITLE"; echo; cat BODY; } |
      git hash-object --stdin

    Run them in the checkout: outside one, git fails and this command reports it instead of hashing "unborn".

    body, when given, is the body file as already read, so what is checked is what is sent.
    """
    if isinstance(text, PrText):
        sent = Path(text.body_file).read_bytes() if body is None else body
        return hashed(f"pull request\n{head()}{text.title}\n\n".encode() + sent)
    # :/ and --full-name keep the whole index when run from a subfolder, where ls-files lists only that folder.
    listing = git("ls-files", "-s", "--full-name", ":/")
    return hashed(f"{head()}{listing}\n{stripped(text.message)}".encode())


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
    text = message.content[0].text if len(message.content) == 1 else None
    if text is None or message.content[0].type != "output_text":
        msg = "a final answer is not one output_text part"
        raise ValueError(msg)
    return text


def shown(text: str) -> str:
    """The answer as Codex shows it and reports it at the turn's end: memory citations removed.

    Codex 0.166.0 strips them from the agent message (core/src/stream_events_utils.rs:495-498) and
    takes task_complete.last_agent_message from that text (:289). Its strip_citations
    (utils/stream-parser/src/citation.rs:69) matches literally, without nesting, and a citation never
    closed runs to the end (utils/stream-parser/src/inline_hidden_tag.rs:167-177).
    """
    kept: list[str] = []
    rest = text
    while (start := rest.find(CITATION_OPEN)) != -1:
        kept.append(rest[:start])
        end = rest.find(CITATION_CLOSE, start + len(CITATION_OPEN))
        if end == -1:
            return "".join(kept)
        rest = rest[end + len(CITATION_CLOSE) :]
    return "".join([*kept, rest])


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
            self.answer = shown(answer_text(message))

    def task_started(self, payload: dict[str, Any]) -> None:
        if self.running is not None:
            msg = f"turn {self.running} never completed"
            raise ValueError(msg)
        self.running = TaskEvent.model_validate(payload).turn_id
        self.context = self.answer = self.done = None

    def task_complete(self, payload: dict[str, Any]) -> None:
        event = TaskEvent.model_validate(payload)
        context, answer = self.context, self.answer
        if event.turn_id == self.running and answer in (None, "") and event.last_agent_message is None:
            # No answer (refused at the usage limit, #544) or an empty one (#562): like an abort, nothing
            # is approved, because task_started cleared it, and the next turn may run.
            self.running = None
            return
        if event.turn_id != self.running or context is None or answer is None or event.last_agent_message != answer:
            msg = f"turn {event.turn_id} completed without matching settings and answer"
            raise ValueError(msg)
        self.done = (context, answer)
        self.running = None

    def turn_aborted(self, payload: dict[str, Any]) -> None:
        # Interrupted: nothing is approved, because task_started cleared it, and the next turn may run.
        event = TaskEvent.model_validate(payload)
        if event.turn_id != self.running:
            msg = f"the abort of {event.turn_id} belongs to no running turn"
            raise ValueError(msg)
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
            ("event_msg", "turn_aborted"): self.turn_aborted,
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
    # Codex 0.166.0 PermissionProfile (protocol/src/models.rs:426-440): only Managed carries file_system;
    # Disabled is full access, as a resume without a sandbox flag runs under this user's config.
    profile = context.permission_profile
    files = profile.file_system
    return (
        context.approval_policy == "never"
        and context.sandbox_policy.type == "read-only"
        and profile.type == "managed"
        and files is not None
        and files.type == "restricted"
        and bool(files.entries)
        and all(entry.access == "read" for entry in files.entries)
    )


def check(text: CommitText | PrText, body: bytes | None = None) -> None:
    session = pinned().session
    meta, context, answer = last_turn(rollout(session), session)
    root = Path(git("rev-parse", "--show-toplevel").strip()).resolve()
    if meta.forked_from_id is not None or {Path(meta.cwd).resolve(), Path(context.cwd).resolve()} != {root}:
        msg = f"session {session} is a fork or did not run in {root}"
        raise ValueError(msg)
    if not read_only(context):
        msg = f"the last turn of session {session} was not read-only"
        raise ValueError(msg)
    wanted = f"{APPROVAL} {fingerprint(text, body)}"
    if answer.rstrip().split("\n")[-1] != wanted:
        msg = f"the reviewer's last answer does not end with: {wanted}"
        raise ValueError(msg)


def create(text: PrText) -> None:
    """Open the pull request with the body read once: the bytes checked are the bytes gh sends."""
    body = Path(text.body_file).read_bytes()
    check(text, body)
    command = ["gh", "pr", "create", "--base", base(), "--title", text.title, "--body-file", "-"]
    done = process.run(command, body, capture_stdout=False)
    # The helper always captures stderr; only stdout may be None.
    sys.stderr.write(cast("bytes", done.stderr).decode(errors="replace"))
