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

# Advisory hint only, never a binding: research verbs, not everyday words such
# as version, latest or codex (r3 P3-4). One alternation, so the search is linear.
_RESEARCH_VERB = re.compile(
    r"\b(research|look up|web search|search (?:the )?(?:web|internet|online|github))\b",
    re.IGNORECASE,
)
_IDENTIFIER = re.compile(r"^[a-zA-Z0-9_-]{1,100}$")
_DIGEST = re.compile(r"[a-f0-9]{64}")
_SOURCE_NAMES = (
    "GitHub issues/discussions/releases, Exa, Context7, Firecrawl, Last30Days"
)
_AGENT_FIELDS = ("agent_id", "agent_type", "subagent")
_POLICY = "strict-five-v2"
_NOTICE = "Research enforcement did not apply to this turn: "
_ACCEPTED_FORMS = ", ".join(
    f"`[research-scope: {scope}]`"
    for scope in ("research", "implementation", "text-edit", "local-only")
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


def _repeat_submission(record: dict[str, object], prompt: str) -> dict[str, object]:
    """A bound research turn refuses a different submission in the same turn."""
    if record["prompt_sha256"] != hashlib.sha256(prompt.encode()).hexdigest():
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
    marker: Path, event: dict[str, object], prompt: str, *, by_intent: bool
) -> None:
    marker.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "turn_id": event["turn_id"],
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "scope": "research",
        "policy": _POLICY,
        # cg36b: no `binding` field means a directive record.
        **({"binding": "intent"} if by_intent else {}),
    }
    marker.write_text(json.dumps(record), encoding="utf-8")


def _context(text: str) -> dict[str, object]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": text,
        }
    }


# r3 P3-4, security P3-6: a pointer only; no provider command in a work turn.
_ADVISORY = (
    "Research hint: this turn is not research-enforced. A caller requires "
    "research evidence by putting `[research-scope: research]` as line 1. "
    "Do not run paid or metered research providers unless the request asks "
    "for research."
)
# cg36b (D246 item 3): a plain research request binds without a directive.
_OPT_OUT = (
    " Not a research request? Resubmit with `[research-scope: implementation]` "
    "as line 1."
)
_INTENT = (
    "Research enforced: the request reads as research, so this turn is "
    "research-enforced." + _OPT_OUT + " "
)
_LOCAL_ONLY = (
    "Caller authorized local-only research scope for this turn. Do not launch "
    "providers. Retain existing research evidence and report INCOMPLETE "
    "honestly when coverage is incomplete."
)


def _unbound(prompt: str, scope: str | None) -> dict[str, object]:
    """A turn that is not research: it never writes hook state (r3 P2-1)."""
    if scope == "local-only":
        return _context(_LOCAL_ONLY)
    if scope is not None:
        return {}
    result = _context(_ADVISORY) if _RESEARCH_VERB.search(prompt) else {}
    if research_scope.near_miss(prompt):
        result["systemMessage"] = (
            "Research scope directive not recognized, so research is not "
            "enforced for this turn. Line 1 must be exactly one of "
            f"{_ACCEPTED_FORMS}."
        )
    return result


def _retained(
    marker: Path, event: dict[str, object], prompt: str, scope: str | None
) -> dict[str, object] | None:
    """Answer a submission in a turn that already has hook state, if it must."""
    if not (marker.exists() or marker.is_symlink()):
        return None
    record = _research_record(marker, str(event["turn_id"]))
    if isinstance(record, dict):
        return _repeat_submission(record, prompt)
    if scope != "research":
        return None
    # Never rewrite retained state; this turn just is not enforced.
    return {
        "systemMessage": "Research gate state for this turn is not a research "
        f"binding ({record or 'other format'}); research is not enforced for "
        "this turn."
    }


def _bind_research(
    event: dict[str, object],
    marker: Path,
    prompt: str,
    repo_root: Path,
    *,
    by_intent: bool = False,
) -> dict[str, object]:
    lead = _INTENT if by_intent else ""
    result = _context(lead + _research_context(event, repo_root))
    try:
        _write_record(marker, event, prompt, by_intent=by_intent)
    except OSError as exc:
        # D236 fail-open: state that cannot be written never blocks the turn.
        result["systemMessage"] = (
            f"Research gate state unwritable ({type(exc).__name__}); Stop "
            "cannot enforce the research receipt for this turn."
        )
    return result


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
    scope = research_scope.directive(prompt)
    retained = _retained(marker, event, prompt, scope)
    if retained is not None:
        return retained
    if scope == "research":
        return _bind_research(event, marker, prompt, repo_root)
    if (
        scope is None
        and not research_scope.near_miss(prompt)
        and research_scope.intent(prompt)
    ):
        return _bind_research(event, marker, prompt, repo_root, by_intent=True)
    return _unbound(prompt, scope)


def _on_stop(
    event: dict[str, object], manifest: Path, opt_out: str = ""
) -> dict[str, object]:
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
            f"these in the answer: {listed}.{opt_out}",
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
            + opt_out
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


def _research_record(marker: Path, turn_id: str) -> dict[str, object] | str | None:
    """Return a valid research record, a failure word, or None for another format.

    r3 P3-3, security P3-1: every field is type-checked before comparison, so
    a legacy, work-scope or forged record can never raise or bind research.
    """
    try:
        recorded = json.loads(marker.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return "missing"
    except OSError:
        return "unreadable"
    except ValueError:
        recorded = None
    if not isinstance(recorded, dict):
        return "malformed"
    scope = recorded.get("scope")
    if scope is None or (isinstance(scope, str) and scope != "research"):
        return None
    digest = recorded.get("prompt_sha256")
    if (
        scope != "research"
        or recorded.get("turn_id") != turn_id
        or recorded.get("policy") != _POLICY
        or recorded.get("binding") not in (None, "intent")
        or not isinstance(digest, str)
        or _DIGEST.fullmatch(digest) is None
    ):
        return "malformed"
    return recorded


def _on_bound_stop(
    event: dict[str, object], marker: Path, manifest: Path
) -> dict[str, object]:
    """Block only a turn whose retained record is a valid research binding."""
    record = _research_record(marker, str(event["turn_id"]))
    if isinstance(record, dict):
        by_intent = record.get("binding") == "intent"
        return _on_stop(event, manifest, _OPT_OUT if by_intent else "")
    if record is None:
        return {}
    return {"systemMessage": f"{_NOTICE}research submission record {record}."}


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
    # Only a valid retained research record binds a Stop; an unbound turn that
    # left a directory passes with a notice (decision 7, security P3-2).
    if event.get("hook_event_name") == "Stop" and (
        marker.parent.exists() or marker.is_symlink()
    ):
        return _on_bound_stop(event, marker, manifest)
    return {}


def _read_event() -> dict[str, object]:
    event = json.load(sys.stdin)
    if not isinstance(event, dict):
        message = "hook input must be an object"
        raise TypeError(message)
    return event


def _state_error(
    event: dict[str, object], state_root: Path, exc: Exception
) -> dict[str, object]:
    """Fail open unless a valid research record binds this Stop.

    Even then the block keeps the `RESEARCH INCOMPLETE:` escape, so an
    exception can never make a permanent block (security P3-1).
    """
    paths = _paths(event, state_root)
    if (
        paths is not None
        and event.get("hook_event_name") == "Stop"
        and isinstance(_research_record(paths[0], str(event["turn_id"])), dict)
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
        except (OSError, ValueError, TypeError) as exc:
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
