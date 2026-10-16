# Copyright (c) 2026 Raymond Manaloto
"""Codex hook: require a complete research receipt before a research turn ends."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from dotfiles_setup import research_scope
from dotfiles_setup.research_fanout import strict_five_verdict

_IDENTIFIER = re.compile(r"^[a-zA-Z0-9_-]{1,100}$")
_SOURCE_NAMES = (
    "GitHub issues/discussions/releases, Exa, Context7, Firecrawl, Last30Days"
)
_AGENT_FIELDS = ("agent_id", "agent_type", "subagent")

# Every pattern runs on text whose blank runs are collapsed to one space, so no
# quantifier repeats over whitespace and each search stays linear (security P2-2).
_BLANKS = re.compile(r"[ \t]+")
_FENCE = re.compile(r" {0,3}(`{3,}|~{3,})")
_BLOCKQUOTE = re.compile(r"^ ?>[^\n]*", re.MULTILINE)
_SPAN = re.compile(
    r"`[^`\n]*`|\"[^\"\n]*\"|\u201c[^\u201d\n]*\u201d|(?<!\w)'[^'\n]*'(?!\w)"
)
# An imperative research verb with an object: line start (list item or
# heading), after clause punctuation and a space, or after a lead word.
# "research" before a noun it modifies ("research gate", "research notes"),
# `check:research` and "investigate why" are not requests.
_RESEARCH_VERB = re.compile(
    r"(?:^ ?(?:(?:[-*+]|\d{1,3}[.)]|#{1,6}) )?|[.!?;:,] |\(|"
    r"\b(?:please|pls|to|and|then|also|now|you|first|next) )"
    r"(?:research(?![ -](?:gate|hooks?|scope|receipts?|coverage|fanout|"
    r"providers?|notes?|reports?|results?|summary|lanes?|team|folder|"
    r"directory|plan|briefs?|runs?|outputs?|evidence|manifests?|tasks?|"
    r"command|ticket|policy|mode|step|stage|incomplete|complete)\b)|"
    r"(?:investigate|look into|look up|find out)(?! (?:why|whether|if|how come)\b))"
    r"(?= [\"'\u201c`]?\w)",
    re.IGNORECASE | re.MULTILINE,
)
_RESEARCH_PHRASE = re.compile(
    r"\bsearch (?:the )?(?:web|internet|online|github)\b|\bbest[ -]practices?\b",
    re.IGNORECASE,
)
_SENTENCE = re.compile(r"[^.!?\n]+")
_ASKS_NEWEST = re.compile(
    r"\b(?:(?:what|which)(?:'s|\u2019s| is| are| was| were)|find(?: out)?) "
    r"(?:the )?(?:latest|newest|best|recommended|most recent)\b",
    re.IGNORECASE,
)
_COMPARISON = re.compile(
    r"\b(?:compar(?:e|es|ing|ison|isons)|evaluat(?:e|es|ing|ion|ions)|"
    r"recommend(?:s|ing|ation|ations)?|alternatives? to)\b",
    re.IGNORECASE,
)
_EXTERNAL_TOPIC = re.compile(
    r"\b(?:tools?|librar(?:y|ies)|frameworks?|plugins?|skills?|models?|agents?|"
    r"workflows?|dependencies|packages?|uv|poetry|fnox|codex|mise)\b",
    re.IGNORECASE,
)
_RELEASE_TOPIC = re.compile(r"\b(?:versions?|releases?)\b", re.IGNORECASE)
# Words that only hint at research: advisory context, never a receipt.
_WEAK = re.compile(
    r"\b(?:latest|newest|upstream|versions?|releases?|research\w*|"
    r"investigat\w*|best practices?)\b",
    re.IGNORECASE,
)


def _normalize(prompt: str) -> str:
    return _BLANKS.sub(" ", prompt.replace("\r\n", "\n").replace("\r", "\n"))


def _strip_fences(text: str) -> str:
    """Drop closed fenced blocks; an unclosed fence strips nothing (CommonMark)."""
    kept: list[str] = []
    block: list[str] = []
    fence = ""
    for line in text.split("\n"):
        if not fence:
            opened = _FENCE.match(line)
            if opened is None:
                kept.append(line)
            else:
                fence, block = opened[1], [line]
            continue
        block.append(line)
        closing = line.strip(" ")
        if len(closing) >= len(fence) and closing == fence[0] * len(closing):
            fence, block = "", []
            kept.append("")
    return "\n".join(kept + block)


def _caller_text(text: str) -> str:
    """Remove quoted material: someone else's words neither request nor waive.

    Short quoted names (`Compare "uv" and "poetry"`) stay caller text.
    """
    text = _BLOCKQUOTE.sub(" ", _strip_fences(text))
    return _SPAN.sub(lambda span: "quoted" if " " in span[0] else span[0], text)


def _requests_research(text: str) -> bool:
    if _RESEARCH_VERB.search(text) or _RESEARCH_PHRASE.search(text):
        return True
    for sentence in _SENTENCE.finditer(text):
        clause = sentence[0]
        external = _EXTERNAL_TOPIC.search(clause)
        if (_COMPARISON.search(clause) and external) or (
            _ASKS_NEWEST.search(clause) and (external or _RELEASE_TOPIC.search(clause))
        ):
            return True
    return False


def _turn_scope(prompt: str) -> str:
    """Classify a native prompt: research, advisory (never blocks) or none.

    Only a first-line directive turns a research request off (decision D236).
    """
    declared = research_scope.directive(prompt)
    if declared is not None:
        return "research" if declared == "research" else "none"
    text = _normalize(prompt)
    if _requests_research(_caller_text(text)):
        return "research"
    return "advisory" if _WEAK.search(text) else "none"


def _paths(event: dict[str, object], state_root: Path) -> tuple[Path, Path] | None:
    session_id = event.get("session_id")
    turn_id = event.get("turn_id")
    if not isinstance(session_id, str) or not _IDENTIFIER.fullmatch(session_id):
        return None
    if not isinstance(turn_id, str) or not _IDENTIFIER.fullmatch(turn_id):
        return None
    root = state_root / session_id / turn_id
    return root / "required.json", root / "manifest.json"


def _repeat_submission(marker: Path, prompt: str) -> dict[str, object]:
    recorded = _read_submission(marker)
    if isinstance(recorded, str):
        return {"decision": "block", "reason": recorded}
    caller_scope = recorded.get("caller_scope")
    prior_digest = (
        caller_scope.get("prompt_sha256")
        if isinstance(caller_scope, dict)
        else recorded.get("prompt_sha256")
    )
    if (
        not isinstance(prior_digest, str)
        or re.fullmatch(r"[a-f0-9]{64}", prior_digest) is None
    ):
        return {"decision": "block", "reason": "Research submission digest invalid."}
    if prior_digest != hashlib.sha256(prompt.encode()).hexdigest():
        return {
            "decision": "block",
            "reason": "Research scope already bound to a different submission.",
        }
    return {}


def _display(path: Path) -> str:
    """Render a checkout under the home directory as ~/... in model context."""
    try:
        return "~/" + path.relative_to(Path.home()).as_posix()
    except ValueError:
        return str(path)


def _research_context(event: dict[str, object], repo_root: Path) -> str:
    relative_out = (
        f"~/.codex/research-coverage/{event['session_id']}/{event['turn_id']}"
    )
    return (
        f"Research strict-five-v2: {_SOURCE_NAMES}. Run "
        "`fnox --config ~/.config/fnox/config.toml --profile codex_research "
        "--no-defaults --no-daemon --non-interactive "
        f"exec -- mise -C {_display(repo_root)} run research-fanout -- QUERY "
        "--repo OWNER/REPO --strict-five "
        f"--request-id {event['turn_id']} --last30days-plan PLAN.json "
        f"--out {relative_out}`. Verify manifest and primary sources. "
        "For failed routes report `RESEARCH INCOMPLETE:` and the exact blocker. "
        "A metered provider that cannot run (credits, quota, auth, missing key, "
        "network, sandbox) is recorded skipped with its code and evidence; the "
        "receipt passes PROVISIONAL; name PROVISIONAL and each skipped provider."
    )


def _on_submit(
    event: dict[str, object], marker: Path, repo_root: Path
) -> dict[str, object]:
    prompt = event.get("prompt")
    if (
        not isinstance(prompt, str)
        or prompt.lstrip().startswith("<heartbeat>")
        or any(event.get(field) not in (None, "") for field in _AGENT_FIELDS)
    ):
        return {}
    binding = research_scope.bind_submission(
        prompt, str(event["session_id"]), str(event["turn_id"])
    )
    if marker.exists():
        return _repeat_submission(marker, prompt)
    if binding is not None:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({"caller_scope": binding}), encoding="utf-8")
        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": (
                    "Caller authorized local-only research scope for this turn. "
                    "Do not launch providers. Retain existing research evidence "
                    "and report INCOMPLETE honestly when coverage is incomplete."
                ),
            }
        }
    scope = _turn_scope(prompt)
    if scope == "none":
        return {}
    if scope == "advisory":
        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": (
                    "Research gate advisory: this turn mentions research words "
                    "but asks for no external research, so Stop requires no "
                    "research receipt. A first line `[research-scope: research]` "
                    "makes one required."
                ),
            }
        }
    result: dict[str, object] = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": _research_context(event, repo_root),
        }
    }
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(
            json.dumps(
                {
                    "turn_id": event["turn_id"],
                    "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                    "policy": "strict-five-v2",
                }
            ),
            encoding="utf-8",
        )
    except OSError as exc:
        # D236 fail-open: state that cannot be written never blocks the turn.
        result["systemMessage"] = (
            f"Research gate state unwritable ({type(exc).__name__}); Stop "
            "cannot enforce the research receipt for this turn."
        )
    return result


def _on_stop(event: dict[str, object], manifest: Path) -> dict[str, object]:
    verdict = strict_five_verdict(manifest, str(event["turn_id"]))
    if verdict.passed:
        if not verdict.provisional_entries:
            return {}
        message = event.get("last_assistant_message")
        tokens = [
            token
            for entry in verdict.provisional_entries
            for token in (
                entry.source,
                *([f"via {entry.route}"] if entry.route else []),
            )
        ]
        named = isinstance(message, str) and all(
            re.search(r"(?<![\w-])" + re.escape(token) + r"(?![\w-])", message)
            for token in ("PROVISIONAL", *tokens)
        )
        if named or event.get("stop_hook_active") is True:
            return {}
        listed = "; ".join(
            entry.source + (f" via {entry.route}" if entry.route else "")
            for entry in verdict.provisional_entries
        )
        return {
            "decision": "block",
            "reason": "Research receipt PROVISIONAL "
            "(skipped or substituted provider). Name PROVISIONAL and each of "
            f"these in the answer: {listed}.",
        }
    reason = verdict.reason
    message = event.get("last_assistant_message")
    if (
        event.get("stop_hook_active") is True
        and isinstance(message, str)
        and message.lstrip().startswith("RESEARCH INCOMPLETE:")
    ):
        return {"systemMessage": f"Research coverage remains incomplete: {reason}"}
    return {
        "decision": "block",
        "reason": (
            f"Research coverage failed: {reason}. Run the strict-five research command "
            f"for request {event['turn_id']} and verify all five provider groups. "
            "If a provider cannot run, start the final answer with "
            "`RESEARCH INCOMPLETE:` "
            "and report its exact blocker; do not claim the research is complete."
        ),
    }


def _invalid_submission(event: dict[str, object], reason: str) -> dict[str, object]:
    """Allow only continued honest incomplete termination of a parsed Stop."""
    message = event.get("last_assistant_message")
    if (
        event.get("stop_hook_active") is True
        and isinstance(message, str)
        and message.lstrip().startswith("RESEARCH INCOMPLETE:")
    ):
        return {"systemMessage": f"Research coverage remains incomplete: {reason}"}
    return {"decision": "block", "reason": reason}


def _read_submission(marker: Path) -> dict[str, object] | str:
    """Return retained authority or a fixed evidence failure class."""
    try:
        recorded = json.loads(marker.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return "Research submission marker missing."
    except OSError:
        return "Research submission marker unreadable."
    except ValueError:
        return "Research submission marker malformed."
    if not isinstance(recorded, dict):
        return "Research submission marker malformed."
    return recorded


def _stop_from_submission(
    event: dict[str, object], marker: Path, manifest: Path
) -> dict[str, object]:
    """Use only retained submission authority, never scope from Stop/model text."""
    recorded = _read_submission(marker)
    if isinstance(recorded, str):
        return _invalid_submission(event, recorded)
    if "caller_scope" in recorded:
        if not research_scope.validates_binding(
            recorded["caller_scope"], str(event["session_id"]), str(event["turn_id"])
        ):
            return _invalid_submission(event, "Caller research scope binding invalid.")
        verdict = strict_five_verdict(manifest, str(event["turn_id"]))
        if not verdict.passed:
            return {
                "systemMessage": (
                    "Caller authorized local work without a new provider run. "
                    "This does not certify existing research. Retain any existing "
                    "INCOMPLETE status. Provider calls remain outside that "
                    "authorization."
                )
            }
        return {}
    return _on_stop(event, manifest)


def handle(
    event: dict[str, object], state_root: Path, *, repo_root: Path
) -> dict[str, object]:
    """Return a Codex hook response without reading transcript_path."""
    paths = _paths(event, state_root)
    if paths is None:
        return {}
    marker, manifest = paths
    if event.get("hook_event_name") == "UserPromptSubmit":
        return _on_submit(event, marker, repo_root)
    # Only a retained submission binds a Stop; a leftover turn directory with
    # no marker (an unbound turn's research run) never blocks (decision 7).
    if event.get("hook_event_name") == "Stop" and (
        marker.exists() or marker.is_symlink()
    ):
        return _stop_from_submission(event, marker, manifest)
    return {}


def _read_event() -> dict[str, object]:
    event = json.load(sys.stdin)
    if not isinstance(event, dict):
        message = "hook input must be an object"
        raise TypeError(message)
    return event


def _state_error(
    event: dict[str, object], state_root: Path, exc: OSError
) -> dict[str, object]:
    """Fail open on hook-state I/O unless a research marker binds this Stop."""
    paths = _paths(event, state_root)
    if (
        paths is not None
        and event.get("hook_event_name") == "Stop"
        and paths[0].is_file()
    ):
        reason = f"Research hook could not validate evidence: {type(exc).__name__}"
        return _invalid_submission(event, reason)
    return {
        "systemMessage": f"Research hook state unavailable ({type(exc).__name__}); "
        "this turn is not bound as research."
    }


def main(*, repo_root: Path) -> int:
    """Read one hook event and write one JSON response."""
    state_root = Path.home() / ".codex" / "research-coverage"
    try:
        event = _read_event()
        try:
            result = handle(event, state_root, repo_root=repo_root)
        except OSError as exc:
            result = _state_error(event, state_root, exc)
    except (OSError, ValueError, TypeError) as exc:
        result = {
            "decision": "block",
            "reason": (
                f"Research hook could not validate evidence: {type(exc).__name__}"
            ),
        }
    sys.stdout.write(json.dumps(result) + "\n")
    return 0
