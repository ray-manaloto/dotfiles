# Copyright (c) 2026 Raymond Manaloto
"""Dependency-free Codex PreToolUse entrypoint for the repository writer lease."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotfiles_setup.writer_lease import codex_pretooluse_decision


def main() -> int:
    """Read one Codex hook payload and emit a deterministic deny when needed."""
    try:
        payload: Any = json.load(sys.stdin)
    except json.JSONDecodeError, OSError:
        payload = None
    reason = codex_pretooluse_decision(payload)
    if reason is not None:
        event = payload.get("hook_event_name") if isinstance(payload, dict) else None
        if event in {"PostToolUse", "PostToolUseFailure"}:
            output = {"continue": False, "stopReason": reason}
        else:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        sys.stdout.write(json.dumps(output, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
