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

# Advisory hints only: a match adds context, never a binding (round 3). Word
# alternations with no nested quantifier, so each search stays linear.
_EXPLICIT_RESEARCH = re.compile(
    r"\b(research|look up|investigate|best practices|latest|upstream|"
    r"releases?|versions?|search (?:the )?(?:web|internet|online|github))\b",
    re.IGNORECASE,
)
_EXTERNAL_TOPIC = re.compile(
    r"\b(tools?|libraries|frameworks?|plugins?|skills?|models?|agents?|"
    r"workflows?|dependencies|uv|poetry|fnox|codex|mise)\b",
    re.IGNORECASE,
)
_COMPARISON = re.compile(
    r"\b(compare|evaluate|recommend|recommendations?|choose|versus|vs\.?|"
    r"current|newest|modern|recent)\b",
    re.IGNORECASE,
)
_IDENTIFIER = re.compile(r"^[a-zA-Z0-9_-]{1,100}$")
_SOURCE_NAMES = (
    "GitHub issues/discussions/releases, Exa, Context7, Firecrawl, Last30Days"
)
_AGENT_FIELDS = ("agent_id", "agent_type", "subagent")
_WORK_SCOPES = frozenset({"implementation", "text-edit"})


def _needs_research(prompt: str) -> bool:
    return bool(
        _EXPLICIT_RESEARCH.search(prompt)
        or (_COMPARISON.search(prompt) and _EXTERNAL_TOPIC.search(prompt))
    )


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


def _write_record(
    marker: Path, event: dict[str, object], prompt: str, **fields: str
) -> None:
    marker.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "turn_id": event["turn_id"],
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        **fields,
    }
    marker.write_text(json.dumps(record), encoding="utf-8")


def _advisory(event: dict[str, object], repo_root: Path) -> dict[str, object]:
    """Research words without the directive: guidance, never a Stop binding."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": (
                "Research hint (not enforced): no first line "
                "`[research-scope: research]`, so Stop requires no receipt; that "
                "line is how a caller requests enforced research. If this turn "
                "needs external research: "
                + _research_context(event, repo_root)
                + " If research was needed but not run, start the answer with "
                "`RESEARCH INCOMPLETE:`."
            ),
        }
    }


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
    scope = research_scope.directive(prompt)
    if scope in _WORK_SCOPES:
        # Names the caller's scope; Stop never blocks on this record.
        _write_record(marker, event, prompt, scope=scope)
        return {}
    if scope != "research":
        return _advisory(event, repo_root) if _needs_research(prompt) else {}
    result: dict[str, object] = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": _research_context(event, repo_root),
        }
    }
    try:
        _write_record(marker, event, prompt, scope="research", policy="strict-five-v2")
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
    if recorded.get("scope") in _WORK_SCOPES and "policy" not in recorded:
        return {}
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
