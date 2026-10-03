# Lane Completion Detection Protocol for Fan-Out Skills

**Date:** 2026-10-02  
**Status:** Specification  
**Research Basis:** `docs/research/kb/reports/agents/fanout-lane-completion-detection-2026-10-02.md`

---

## Problem Statement

Current fan-out lane monitoring has a detection gap:

1. A lane finishes work and goes idle at the prompt
2. The lane watcher expects one of: {done, failed, stopped}
3. "Idle" is not a terminal state in Claude Code — it's transient
4. A lane showing "idle" or "needs input" is ambiguous: Is it done, or waiting for a next task?
5. This causes the watcher to remain active for up to 7 days, sending repeated notifications

**Root cause:** Lack of explicit completion signals. The watcher cannot distinguish:
- "Finished successfully and waiting for your next instruction" (idle)
- "Finished successfully and ready to close" (completed)

---

## Protocol Requirements

A lane is considered **finished** when ALL of these conditions are met:

### 1. Terminal State Transition

The Claude Code session state must be one of:
- **Completed** (green) — task finished successfully
- **Failed** (red) — task ended with an error
- **Stopped** (grey) — session was stopped

Session states that do NOT indicate completion:
- **Working** (animated) — actively processing
- **Needs input** (yellow) — waiting for user response
- **Idle** (dimmed) — has no current work but is ready for next prompt

### 2. Explicit Completion Signal

The lane must emit a completion signal that is:
- **Durable** — survives session restart
- **Verifiable** — the watcher can confirm it
- **Timestamped** — allows distinguishing stale from fresh

Acceptable completion signals:

**Option A: Session Close Command**
```bash
# Inside the lane session, at the end:
/stop
```
This reports the session as "Stopped" to Claude Code.

**Option B: Completion Marker File**
```bash
# Lane writes this file when work is complete:
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) · completed" > .agent/lane-completion-marker
```

**Option C: Exit with Status**
```bash
# For shell-based lanes:
exit 0  # success
exit 1  # failure
```

### 3. State Persistence

The terminal state must persist for at least 2 minutes (one check interval).

This filters out:
- Brief transitions during normal operation
- Transient network issues

### 4. Age Verification

For idle states: if a session has been idle for >5 minutes WITHOUT a completion marker, the watcher should:
1. Send a confirmation prompt: "Did you finish? Type `/stop` to confirm, or send a follow-up task."
2. Wait 1 check interval (10 min)
3. If no response AND no completion marker, escalate to the coordinator

---

## Watcher Algorithm

A lane is settled when:
- Session state = one of {done, failed, stopped}
- AND completion marker exists OR state persisted ≥2 minutes
- OR a confirmation response received

Unsettled conditions:
- Session still working or needs input
- Idle for >5 min without marker → send confirmation prompt

---

## Lane Dispatch Instructions

Every lane brief must include:

```text
COMPLETION PROTOCOL:
  When finished, type `/stop` to close the session.
  
  Watcher confirmation: Session shows Stopped/Completed + completion marker.
  
  If you finish but session stays Idle, watcher sends confirmation prompt after 5 min.
```

---

## Implementation Checklist

- [ ] Update `parallel-work-split` skill: add completion protocol to lane brief
- [ ] Watcher checks `claude agents --json --all` for state transitions
- [ ] Watcher detects idle >5min without marker → escalate
- [ ] Lane brief instructs `/stop` or write completion marker
- [ ] Test: verify watcher distinguishes "done" from "idle waiting"
- [ ] Test: verify watcher escalates unfinished idle lanes

---

## Related Research

- stablyai/orca #15185 — "Run with ready task, all lanes settled, idle coordinator"
- spec-kitty parallel-implementation-tracking — machine-readable status protocol
- Claude Code agent-view.md — session states and idle behavior
- forge — missing-event detection pattern

