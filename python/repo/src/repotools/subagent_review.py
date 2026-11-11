"""The fallback reviewer: a fresh read-only Claude subagent's answer, while the Codex reviewer's quota is depleted."""

# Owner ruling of 2026-11-09 and its amendment of 2026-11-10 (AGENTS.md, "Commit and pull-request approval"): the
# author writes the staged diff to a file and runs a subagent whose tools are only Read, Grep and Glob in its own
# session, with only the checkout, the diff file, the fingerprint and the review rules in its prompt, and pins its
# transcript with pane-pin --subagent. Claude Code writes the transcript as
# <project>/<session>/subagents/agent-<id>.jsonl, with agent-<id>.meta.json beside it. The shapes below were read
# from 1,943 finished transcripts on this Mac (Claude Code 2.1.319). Like the Codex pin, this is a local record that
# anyone running as this user can edit, so it catches mistakes, not a forger.

import re
from pathlib import Path

from .models import AgentLine, AgentMessage, AgentMeta, AgentPart

# What the transcript shows, not the agent type the meta file names: Explore and Plan have Bash, and a shell command
# can write. An allowlist, not a list of the writing tools: an MCP tool or a new built-in one can write too.
TOOLS = frozenset({"Read", "Grep", "Glob"})
# A background subagent's answer reaches its caller only through this call, so it may be the last step and only that.
HANDBACK = "SubagentHandback"
WORKTREE = re.compile(r"^[ \t]*Worktree:[ \t]*`?([^`\s]+)`?[ \t]*$", re.MULTILINE)


def meta_of(transcript: Path) -> AgentMeta:
    path = transcript.with_name(transcript.name.removesuffix(".jsonl") + ".meta.json")
    return AgentMeta.model_validate_json(path.read_text())


def lines_of(transcript: Path) -> list[AgentLine]:
    # Blank lines are skipped; any other line must be one JSON record, or the transcript is cut off or edited.
    return [AgentLine.model_validate_json(line) for line in transcript.read_text().splitlines() if line.strip()]


def parts_of(content: str | list[AgentPart]) -> list[AgentPart]:
    """A message's parts; Claude Code writes a plain prompt as one string, and an empty one has none."""
    if isinstance(content, str):
        return [AgentPart(type="text", text=content)] if content else []
    return content


def text_of(content: str | list[AgentPart]) -> str:
    return "\n".join(part.text or "" for part in parts_of(content) if part.type == "text")


def answer_of(part: AgentPart) -> str:
    """The run's result: its closing text, or the message a background subagent hands back with SubagentHandback.

    A background subagent's plain closing text never reaches its caller; only the handback does.
    """
    if part.type == "text" and part.text is not None:
        return part.text
    message = (part.input or {}).get("message") if part.type == "tool_use" and part.name == HANDBACK else None
    if isinstance(message, str):
        return message
    msg = "the subagent's last step is neither text nor a SubagentHandback message"
    raise ValueError(msg)


def answer(transcript: Path, root: Path, fingerprint: str) -> str:
    """The pinned subagent's final answer, once its run is shown to be a finished, read-only review of this text."""
    meta = meta_of(transcript)
    # finished is written when the run ends; a run still going or killed could answer again or not at all.
    if meta.finished is not True:
        msg = f"subagent {transcript.name} has not finished"
        raise ValueError(msg)
    agent = transcript.name.removeprefix("agent-").removesuffix(".jsonl")
    messages: list[AgentMessage] = []
    for line in lines_of(transcript):
        if line.type not in {"user", "assistant"}:
            continue
        # Every turn is this subagent's own: a copied-in turn of the parent or of another agent would not be.
        if line.agent_id != agent or line.is_sidechain is not True or line.message is None:
            msg = f"transcript {transcript.name} holds turns that are not subagent {agent}'s own"
            raise ValueError(msg)
        messages.append(line.message)
    # The first turn is the author's prompt. A fork starts from the parent's context instead, which is not fresh.
    prompt = text_of(messages[0].content) if messages and messages[0].role == "user" else ""
    # A line "Worktree: <path>" names the checkout, compared whole: not /work/repo/other, /work/repo-other or a file
    # path that only starts with it. A path in backticks counts; the path itself is taken as written.
    named = [match.group(1) for match in WORKTREE.finditer(prompt)]
    if named != [str(root)] or fingerprint not in prompt:
        msg = f"subagent {transcript.name} was not asked to review {root} at fingerprint {fingerprint}"
        raise ValueError(msg)
    turns = [parts_of(message.content) for message in messages if message.role == "assistant"]
    # The last turn answers on its own: an empty one leaves no answer, not the one before it.
    if not turns or not turns[-1]:
        msg = f"subagent {transcript.name} never answered"
        raise ValueError(msg)
    *steps, last = [part for turn in turns for part in turn]
    used = {part.name or "" for part in steps if part.type == "tool_use"} - TOOLS
    if last.type == "tool_use":
        used |= {last.name or ""} - TOOLS - {HANDBACK}
    if used:
        # agentType is only reported: the tools the run called decide, whatever the type was allowed.
        names = ", ".join(sorted(used))
        msg = f"subagent {transcript.name} ({meta.agent_type}) used tools other than Read, Grep and Glob: {names}"
        raise ValueError(msg)
    return answer_of(last)
