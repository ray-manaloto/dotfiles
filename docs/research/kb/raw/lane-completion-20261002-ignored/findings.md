# Research Findings: Fanout Lane Completion Detection

**Session:** 2026-10-02  
**Research Focus:** How to distinguish "idle at prompt" from "task complete"

## Core Finding

**The Problem:** Lane KB2 finished at 12:13 PM but `claude agents` listed it as "blocked", not "done". The watcher looks for terminal states {done, failed, stopped}, so it never stopped watching. Leaves watcher active for 7 days.

**Root Cause:** "Idle" (dimmed state) is NOT a terminal state in Claude Code. A lane that finishes work and waits for next instructions shows as idle, which is ambiguous with "still waiting for you to reply to my question".

**Solution:** Require lanes to emit explicit completion signals when work is done:
1. Session transitions to terminal state (done/failed/stopped)
2. Lane writes a completion marker or calls `/stop`
3. Watcher confirms BOTH before marking lane settled

## Research Artifacts

### Primary: Claude Code Agent Status Model
- **Source:** Claude Code docs (agent-view.md)
- **Finding:** States are Working → Idle/Needs-input → Completed/Failed/Stopped
- **Key Insight:** Idle is transient, not terminal. A lane that finishes needs to report Completed or Stopped.

### Secondary: Stablyai/Orca Issue #15185
- **Source:** GitHub issue — exact same problem
- **Title:** "A Run with a ready task, all lanes settled and an idle coordinator has nothing left to wake it"
- **Finding:** Root cause is "finishing a dispatch is not finishing the Run"
- **Solution Pattern:** Check if the run's state changed; don't infer from silence

### Tertiary: Multi-Project Patterns
- **spec-kitty:** Machine-readable status via `--json` (not UI groupings)
- **forge:** Missing-event detection pattern (emit completion events explicitly)
- **Temporal:** Durable event logs, append-only

## Implementation Recommendations

### 1. Protocol: Three-Layer Completion Check
```
Lane settled when:
  - Session state ∈ {done, failed, stopped}
  - AND (completion marker exists OR state persisted ≥2 min)
  - OR coordinator received confirmation response
```

### 2. Watcher Escalation
If lane idles >5 min without marker:
- Send confirmation prompt: "Did you finish?"
- Wait 1 check (10 min)
- If no response, escalate to coordinator

### 3. Lane Brief Instruction
```
When finished, type `/stop` to close the session.
Watcher confirms: Terminal state + completion marker.
If you idle >5 min, watcher sends confirmation prompt.
```

## Next Steps (Implementation)

- [ ] Update `parallel-work-split` skill: add completion protocol to brief template
- [ ] Implement watcher state machine with idle escalation logic
- [ ] Update lane dispatch: require `/stop` or completion marker
- [ ] Test: verify watcher correctly detects "done" vs "idle"

## Files Written

1. **Research Report:** `docs/research/kb/reports/agents/fanout-lane-completion-detection-2026-10-02.md` (full research with cross-project patterns)
2. **Specification:** `docs/specs/fanout-skill-lane-completion-protocol.md` (implementable protocol)
3. **Offline Mirrors:** `docs/research/kb/raw/fanout-lane-completion-detection-2026-10-02/links/` (Claude Code docs + other sources)

## 2026-10-03 — event-driven self-healing orchestration sweep (synthesize node)

- Report: `docs/research/kb/reports/agents/event-driven-self-healing-agent-orchestration-2026-10-03.md`. The sweep is INCOMPLETE: the code-search health check was rate-limited, and the OpenHands and claude-flow searches failed with 422 because both repos redirect.
- Four claude-code feature requests were closed not_planned: #64898 (hooks spawn agents), #87142 (subagent death signal), #62631 (parent wake-up), #38210 (auto-restart). So the restart trigger must live outside the session.
- The supervisor restarts EXITED background sessions (`agent-view.md:749`), but respawn resumes the full conversation. The `agent_completed` Notification fires only while agent view is open.
- `settings.json` hooks hot-reload (`settings.md:584`); plugin function hooks do not. Put the producer in settings hooks. The consumer should be a launchd KeepAlive supervisor: the mise binary knows `keep_alive`/`queue_directories`, and the launchd man page calls WatchPaths race-prone.
- research-sweep-run: the issues/PRs/discussions phase is PRESENT (Dependencies). The saved-searches phase is ABSENT (#1502 OPEN, blocked on N1 `watches.toml`).
