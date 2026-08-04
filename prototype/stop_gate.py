#!/usr/bin/env python3
"""PROTOTYPE — SubagentStop hook body. Blocks exactly once, then allows.

Wired from `.claude/agents/proto-stop-blocker.md` frontmatter as a `Stop` hook,
which the harness converts to `SubagentStop` at runtime
(`$CC/sub-agents.md` "Define hooks for subagents").

The question: can a SubagentStop hook actually FORCE a delegated agent to do more
work before its turn ends? If it can, the "deliver before you go idle" rule stops
being prose and becomes a mechanism.

Control arm is built in: the FIRST call blocks, the SECOND allows. A hook that
could only ever block would prove nothing about the allow path, and vice versa.
Both transitions are observable in one run.

Throwaway. Marker lives in /tmp so there is no persistence to clean up.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

MARKER = Path("/tmp/proto-stop-gate.fired")
LOG = Path("/tmp/proto-stop-gate.log")


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {"_unparsable": raw[:400]}

    already_fired = MARKER.exists()

    # Record what the hook actually received — the payload shape is half the
    # finding. `agent_transcript_path` in particular is what makes an enforcing
    # hook able to CHECK the work rather than just nag about it.
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "call": 2 if already_fired else 1,
                    "payload_keys": sorted(payload),
                    "stop_hook_active": payload.get("stop_hook_active"),
                    "agent_type": payload.get("agent_type"),
                    "has_transcript_path": "agent_transcript_path" in payload,
                }
            )
            + "\n"
        )

    if already_fired:
        # Second call: allow the agent to finish, so the ALLOW arm is observed too.
        print(json.dumps({"systemMessage": "proto-stop-gate: allowing (2nd call)"}))
        return 0

    MARKER.write_text("1", encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": (
                    "PROTO-STOP-GATE BLOCKED YOU. Before finishing, append the exact "
                    "line 'PROTO-STOP-GATE-OBSERVED' to /tmp/proto-stop-gate.witness "
                    "using Bash, then finish."
                ),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
