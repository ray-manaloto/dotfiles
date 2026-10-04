#!/usr/bin/env python3
# Copyright (c) 2026 Raymond Manaloto
"""Codex hook: require a complete research receipt before a research turn ends."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "python" / "src"))

strict_five_verdict = import_module(
    "dotfiles_setup.research_fanout"
).strict_five_verdict

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


def _on_submit(event: dict[str, object], marker: Path) -> dict[str, object]:
    prompt = event.get("prompt")
    if (
        not isinstance(prompt, str)
        or prompt.lstrip().startswith("<heartbeat>")
        or not _needs_research(prompt)
        or event.get("subagent") is not None
    ):
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
        f"exec -- mise -C {REPO_ROOT} run research-fanout -- QUERY "
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
        if verdict.provisional:
            return {
                "systemMessage": "Research receipt PROVISIONAL "
                "(credit-exhausted provider): "
                + "; ".join(verdict.provisional)
                + ". Say so in the answer."
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


def handle(event: dict[str, object], state_root: Path) -> dict[str, object]:
    """Return a Codex hook response without reading transcript_path."""
    paths = _paths(event, state_root)
    if paths is None:
        return {}
    marker, manifest = paths
    if event.get("hook_event_name") == "UserPromptSubmit":
        return _on_submit(event, marker)
    if event.get("hook_event_name") == "Stop" and marker.is_file():
        return _on_stop(event, manifest)
    return {}


def _read_event() -> dict[str, object]:
    event = json.load(sys.stdin)
    if not isinstance(event, dict):
        message = "hook input must be an object"
        raise TypeError(message)
    return event


def main() -> int:
    """Read one hook event and write one JSON response."""
    try:
        event = _read_event()
        result = handle(event, Path.home() / ".codex" / "research-coverage")
    except (OSError, ValueError, TypeError) as exc:
        result = {
            "decision": "block",
            "reason": (
                f"Research hook could not validate evidence: {type(exc).__name__}"
            ),
        }
    sys.stdout.write(json.dumps(result) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
