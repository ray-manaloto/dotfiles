# Implementation Proposal: Fanout Skill Lane Completion Protocol

**Date:** 2026-10-02  
**Audience:** Ray (decision-maker) + implementation team  
**Format:** Structured specification with explicit decisions needed

## Executive Summary

The fanout orchestrator's lane watcher hangs for 7 days on completed lanes because lanes report as "blocked" (idle at prompt) rather than "done" (terminal state). Research into parallel orchestration systems (Kubernetes, GitHub Actions, Apache Airflow, Zapier) reveals a standard pattern:

**Use artifact existence + status polling as a hybrid completion detector.**

This proposal implements that pattern with minimal changes:
1. Update the lane brief template to require explicit completion markers
2. Enhance the lane watcher to recognize "blocked + marker file exists" as terminal
3. No changes to existing lanes or orchestration schemas

## Current State

**Problem Manifestation:**
- Lane KB2 finishes work at 12:13 PM
- Watcher sees `state: "blocked"` (idle at prompt)
- Watcher keeps checking every 10 minutes
- Watcher stops only after 7 days or user intervention

**Root Cause:**
| Component | Current | Issue |
|-----------|---------|-------|
| Lane Brief | "STOP AT: commit" | Ends naturally at prompt (not a terminal state) |
| Claude Code Status | "blocked" for idle | Conflates "stalled" with "idle-and-done" |
| Lane Watcher | Polls for `done`/`failed`/`stopped` only | Never recognizes idle-as-completion |

## Proposed Solution

### Design Decision 1: Completion Signal Mechanism

**Options Considered:**
- A) Status polling only (would require Claude Code to report "idle" explicitly) — rejected, requires harness change
- B) Report file existence only (fragile: can't distinguish mid-work from done) — rejected
- **C) Hybrid: Status polling + Artifact existence** — adopted, matches industry standard (Kubernetes conditions + status, GitHub conclusion + job state)
- D) Explicit completion message (requires lane to send message) — deferred to v2

**Choice: Option C** — Lane is complete when `state == "blocked"` AND completion marker file exists.

### Design Decision 2: Completion Marker Format

**Options Considered:**
- A) Bare timestamp file (`.agent/completion/<lane>.done`) — minimal, loses context
- **B) Structured JSON with metadata** — adopted, enables future reporting/debugging
- C) Marker + separate report index — more complex, no additional value

**Choice: Option B** with schema:
```json
{
  "lane": "string (lane name)",
  "completed_at": "ISO8601 timestamp",
  "pr_number": "number or null",
  "pr_state": "MERGED|OPEN|CLOSED",
  "final_status": "success|partial|failed",
  "report_path": "string (path to findings)"
}
```

### Design Decision 3: Brief Template Change

**Current:**
```
STOP AT: commit on the branch. Do NOT push, ship or open a PR.
```

**Proposed:**
```
COMPLETION: Write .agent/completion/<lane>.completion.json with:
  {"lane": "<lane>", "completed_at": <ISO8601>, "pr_number": <n or null>,
   "pr_state": "MERGED|OPEN|CLOSED", "final_status": "success|partial|failed",
   "report_path": "<path from PERSIST section>"}
STOP AT: commit on the branch. Do NOT push, ship or open a PR.
```

**Rationale:** Explicit instruction makes it clear this is mandatory for orchestration, not optional nicety.

### Design Decision 4: Watcher Implementation

**Location:** Python module in `dotfiles_setup`, called by lane-watcher orchestrator

**Function Signature:**
```python
def is_lane_complete(
    lane_name: str,
    agent_state: str,
    marker_path: Path | None
) -> bool:
    """Determine if a lane has finished work and signaled completion.
    
    Args:
        lane_name: Name of the lane (for logging)
        agent_state: Current state from `claude agents --json` (e.g., "done", "blocked")
        marker_path: Path to expected completion marker, if any
    
    Returns:
        True if lane is complete, False otherwise
    """
    # Terminal states are always complete (unchanged)
    if agent_state in ("done", "failed", "stopped"):
        return True
    
    # Idle-at-prompt completion pattern (new)
    if agent_state == "blocked" and marker_path and marker_path.exists():
        try:
            data = json.loads(marker_path.read_text())
            # Require both timestamps (proof of execution) and status
            if "completed_at" in data and "final_status" in data:
                return True
        except (json.JSONDecodeError, IOError, ValueError) as e:
            # Log error but don't crash; treat as incomplete
            logger.debug(f"Malformed marker for {lane_name}: {e}")
    
    return False
```

**Error Handling:**
- Malformed JSON → treat as "not complete yet" (lane can re-write)
- Missing file → treat as "not complete yet" (lane hasn't finished)
- File exists but unparseable → log warning, keep waiting

### Design Decision 5: Backwards Compatibility

**Existing Lanes (without completion marker):**
- Watcher still polls agent state normally
- Falls back to checking for explicit terminal states (done/failed/stopped)
- Will eventually timeout (7 days) if agent stays blocked
- No breaking change

**New Lanes (with completion marker instruction):**
- Will stop watcher within 10 minutes of writing marker
- Clean, fast completion detection
- Same error handling as existing lanes

**Migration Path:**
- Phase 1: Update brief template (effective for new briefs)
- Phase 2: No retrofit needed (old lanes work, just slower)
- Phase 3: Optional: add marker retroactively to in-flight lanes if desired

## Changes Required

### 1. `.claude/skills/parallel-work-split/SKILL.md`

Add COMPLETION section to brief template (§5, line ~120):

```markdown
Brief template — every field is required, because a lane cannot ask:

…
COMPLETION: When your work is done and you reach the STOP AT boundary, 
write .agent/completion/<lane>.completion.json with:
{"lane": "<lane>", "completed_at": <ISO8601>, "pr_number": <n or null>,
 "pr_state": "MERGED|OPEN|CLOSED", "final_status": "success|partial|failed",
 "report_path": "<from PERSIST section>"}
STOP AT: commit on the branch. Do NOT push, ship or open a PR.
```

**Justification:** Explicit instruction in mandatory field, follows brief template structure.

### 2. `python/src/dotfiles_setup/orchestration.py` (new or existing module)

Add function and helper:
```python
def is_lane_complete(lane_name: str, agent_state: str, marker_path: Path | None) -> bool:
    # [implementation from Design Decision 4 above]

def validate_completion_marker(marker_path: Path) -> bool:
    """Validate that marker is well-formed JSON with required fields."""
    try:
        data = json.loads(marker_path.read_text())
        required = {"lane", "completed_at", "final_status"}
        return required.issubset(data.keys())
    except Exception:
        return False
```

### 3. `.agent/completion/.gitignore`

```
# Lane completion markers — local only, not tracked
*.completion.json
```

### 4. `python/tests/test_orchestration.py` (new or extended)

Test cases (see spec §6 for details):
- `test_lane_complete_on_blocked_with_marker`
- `test_lane_incomplete_on_blocked_without_marker`
- `test_terminal_state_overrides_marker`
- `test_malformed_marker_ignored`

## Metrics & Acceptance Criteria

| Metric | Target | How Measured |
|--------|--------|--------------|
| Watcher latency (completion detection) | <20 min (2x poll cycle) | Time from marker write to watcher status update |
| False negative rate | <1% | Completed lanes still showing "blocked" after 1 hour |
| False positive rate | 0% | Lanes marked complete while still working |
| Backwards compatibility | 100% | Old lanes without marker still recognized as done eventually |
| Adoption | >80% by month 2 | % of new briefs including completion instruction |

## Timeline

| Phase | Duration | Work |
|-------|----------|------|
| **Phase 1: Immediate** | 1 day | Spec approval + skill template change + unit tests |
| **Phase 2: Integration** | 3-5 days | Orchestration watcher implementation + integration tests |
| **Phase 3: Rollout** | ongoing | Monitor in production, adjust timeout if needed |

## Open Questions for Ray

1. **Timeout behavior**: If a lane is "blocked" without a marker for >2 hours, should the watcher:
   - Keep checking forever? (current behavior)
   - Give up and stop? (recommended: report "stalled")
   - Force-stop the lane? (aggressive)

2. **Marker validation**: Should we add:
   - Cryptographic signature (detect tampering)? → Probably not needed
   - Timestamp freshness check (must be recent)? → Maybe
   - PR validation (confirm PR exists/merged if number given)? → Nice to have, v2

3. **Session reporting**: Should the orchestrator's final summary include:
   - List of lanes + completion markers? → Yes
   - Merge status for each PR? → Yes, from marker
   - Time to completion per lane? → Yes, use timestamps

## Risks & Mitigations

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| Lanes forget to write marker | Medium | Explicit instruction + brief review + testing |
| Marker file corruption | Low | Graceful JSON error handling, lane can retry |
| Watcher still hangs on legacy lanes | Low | Acceptable; they use old brief template |
| Marker collision (two lanes same name) | Very low | Directory structure + lane names are unique per plan |

## References

- `docs/research/kb/raw/fanout-lane-completion-detection-2026-10-02/findings.md` — research report
- `docs/specs/fanout-skill-lane-completion-protocol.md` — detailed protocol spec
- `.claude/rules/agent-report-persistence.md` — existing artifact convention
- `.claude/skills/parallel-work-split/SKILL.md` — brief template (to be updated)
