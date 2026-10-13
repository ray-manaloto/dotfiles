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


def _on_submit(
    event: dict[str, object], marker: Path, repo_root: Path
) -> dict[str, object]:
    prompt = event.get("prompt")
    if (
        not isinstance(prompt, str)
        or prompt.lstrip().startswith("<heartbeat>")
        or event.get("subagent") is not None
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
    if not _needs_research(prompt):
        return {}
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
    relative_out = (
        f"~/.codex/research-coverage/{event['session_id']}/{event['turn_id']}"
    )
    context = (
        f"Research strict-five-v2: {_SOURCE_NAMES}. Run "
        "`fnox --config ~/.config/fnox/config.toml --profile codex_research "
        "--no-defaults --no-daemon --non-interactive "
        f"exec -- mise -C {repo_root} run research-fanout -- QUERY "
        "--repo OWNER/REPO --strict-five "
        f"--request-id {event['turn_id']} --last30days-plan PLAN.json "
        f"--out {relative_out}`. Verify manifest and primary sources. "
        "For failed routes report `RESEARCH INCOMPLETE:` and the exact blocker. "
        "A provider out of credits (HTTP 402 or quota 429) is recorded "
        "skipped: credits-exhausted or substituted; the receipt passes "
        "PROVISIONAL; report it."
    )
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }


def _on_stop(event: dict[str, object], manifest: Path) -> dict[str, object]:
    verdict = strict_five_verdict(manifest, str(event["turn_id"]))
    if verdict.passed:
        if verdict.provisional_entries:
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
                "(credit-exhausted provider). Name PROVISIONAL and each of "
                f"these in the answer: {listed}.",
            }
        return {}
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
    if event.get("hook_event_name") == "Stop" and marker.parent.exists():
        return _stop_from_submission(event, marker, manifest)
    return {}


def _read_event() -> dict[str, object]:
    event = json.load(sys.stdin)
    if not isinstance(event, dict):
        message = "hook input must be an object"
        raise TypeError(message)
    return event


def main(*, repo_root: Path) -> int:
    """Read one hook event and write one JSON response."""
    try:
        event = _read_event()
        result = handle(
            event, Path.home() / ".codex" / "research-coverage", repo_root=repo_root
        )
    except (OSError, ValueError, TypeError) as exc:
        result = {
            "decision": "block",
            "reason": (
                f"Research hook could not validate evidence: {type(exc).__name__}"
            ),
        }
    sys.stdout.write(json.dumps(result) + "\n")
    return 0
