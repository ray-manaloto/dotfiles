# Fanout Lane Completion Detection — Research & Specification

**Date:** 2026-10-02  
**Trigger:** Side agent note — lane watcher hangs on completed lanes showing "blocked" status  
**Deliverables:** Research findings + protocol spec + implementation proposal

## Problem Summary

The fan-out orchestrator launches parallel lanes via `claude --bg` to distribute work concurrently. When a lane completes its assigned tasks and reaches `STOP AT: commit on the branch`, it naturally becomes idle at the prompt. However:

1. Claude Code reports idle agents as **"blocked"**, not a terminal state
2. The lane watcher only stops when it sees `done`, `failed`, or `stopped`
3. The watcher keeps checking every 10 minutes for **7 days**, sending notifications every 30 minutes
4. Completed lanes are operationally indistinguishable from stalled/hung lanes

This creates false alarms and prevents clean orchestration shutdown.

## Files in This Report

| File | Purpose | Key Finding |
|------|---------|------------|
| `findings.md` | Research into how other projects handle lane completion detection | Multi-agent systems use **hybrid artifact + status polling**, not status alone |
| `implementation-proposal.md` | Structured specification with decision points and acceptance criteria | Implement Option A+B: "blocked + marker file exists" as terminal completion |
| `links/2.md` | Offline mirror of Claude Code hooks documentation | Confirms agent status values and state reporting |
| This file | Index and summary | — |

## Research Findings Summary

### How Other Systems Handle Parallel Completion

| System | Method | Key Insight |
|--------|--------|------------|
| **GitHub Actions** | `conclusion` field (not `status`) + terminal values | Explicit conclusion even for neutral outcomes |
| **Kubernetes** | `job.status.conditions` array with `type: "Complete"` | Make completion explicit via structured conditions |
| **Apache Airflow** | Task state enum: `success`, `failed`, `skipped`, `upstream_failed` | Distinguish "skipped" (not applicable) from "success" (completed) |
| **Zapier** | Explicit terminal states: `completed`, `failed` | Requires agent to report action outcome |

**Common Pattern:** Status polling alone is insufficient. Successful systems use:
1. An explicit completion indicator (field, condition, artifact, or message)
2. A distinction between "working", "idle", and "done" states
3. A fallback timeout to detect truly stalled processes

### The "Idle at Prompt" Problem

Claude Code's brief template naturally ends with `STOP AT: commit on the branch`. This means:
- The agent is **functionally complete** (has done its assigned work)
- The agent is **reporting as "blocked"** (waiting for external input from coordinator)
- The watcher treats this as **stalled** (keeps polling for 7 days)

**Solution:** Introduce an explicit completion marker that the lane writes before stopping, so the watcher can distinguish "idle-and-done" from "idle-and-stalled".

## Proposed Solution

### Three-Part Protocol

1. **Brief Template Change** — Add explicit instruction to write completion marker
   - Minimal change: one new field in brief template
   - No changes to existing lanes (backwards compatible)

2. **Completion Marker Schema** — JSON file with structured metadata
   ```json
   {
     "lane": "feature-x",
     "completed_at": "2026-10-02T14:30:00Z",
     "pr_number": 1234,
     "pr_state": "MERGED",
     "final_status": "success",
     "report_path": "docs/research/kb/reports/agents/feature-x.md"
   }
   ```

3. **Lane Watcher Logic** — Enhanced completion detection
   - Terminal states (done/failed/stopped) → complete (unchanged)
   - "Blocked" + marker file exists → complete (new)
   - "Blocked" + no marker → not complete yet (unchanged)

### Benefits

- **Deterministic:** Watcher stops within 10 minutes of completion, not 7 days
- **Non-breaking:** Old lanes without markers still work (just slower)
- **Simple:** Minimal changes to brief template and watcher code
- **Observable:** Marker file provides debugging info (when done, what status, which PR)
- **Proven:** Matches industry pattern (Kubernetes conditions, GitHub conclusion)

## Implementation Roadmap

### Phase 1: Immediate (1 day)
- Update `.claude/skills/parallel-work-split/SKILL.md` brief template
- Implement `is_lane_complete()` function in `dotfiles_setup`
- Add unit tests

### Phase 2: Integration (3-5 days)
- Wire function into orchestrator's lane watcher
- Integration tests with actual `claude --bg` lanes
- Verify backwards compatibility

### Phase 3: Production (ongoing)
- Monitor completion latency and false positives
- Adjust timeout if needed (currently fixed at 7 days)
- Gather feedback from lane coordinators

## Success Criteria

1. ✅ Watcher stops cleanly — no more 7-day hangs on completed lanes
2. ✅ False negatives rare — >99% of finished lanes recognized within 20 minutes
3. ✅ False positives absent — no lanes marked complete while still working
4. ✅ Backwards compatible — old lanes without markers still work
5. ✅ Transparent — no JSON parsing in coordinator's main loop

## Decision Points for Ray

1. **Timeout behavior:** If lane is "blocked" without marker for >2 hours, should watcher keep checking forever or give up?
   - Current proposal: keep checking (no timeout), allow manual override
   - Alternative: timeout after 2 hours, report "stalled"

2. **Marker validation:** Should watcher validate PR state (confirm merge) or just check file exists?
   - Current proposal: just check file exists (faster, simpler)
   - Alternative: query GitHub API for PR state (adds dependency)

3. **Session reporting:** Should orchestrator's final summary include completion marker data?
   - Current proposal: yes, include PR numbers and completion timestamps
   - Alternative: minimal summary (lane name + status only)

## Next Steps

1. **This session:** Research complete ✓, spec written ✓, proposal ready ✓
2. **Next session:** Ray reviews and approves design decisions
3. **Implementation:** Update parallel-work-split skill + orchestration module
4. **Testing:** Unit + integration tests, dry-run with test lanes
5. **Production:** Rollout to active orchestrations

## Related Documentation

- `.claude/rules/agent-report-persistence.md` — lanes write reports to disk
- `.claude/rules/parallel-work-split/SKILL.md` — brief template (will be updated)
- `.claude/skills/parallel-work-split/SKILL.md` — skill file (will be updated)
- `docs/specs/fanout-skill-lane-completion-protocol.md` — detailed protocol spec
- `docs/specs/research-fanout.md` — existing fanout orchestrator spec

## Document Metadata

- **Author:** Claude Haiku 4.5 (via /research-sweep workflow)
- **Session:** https://claude.ai/code/session_01LYbJYMdhJzozzovZnhCFZJ
- **Research Conducted:** 2026-10-02
- **Word Count:** ~3,500 (across all files)
- **Status:** Ready for review
