# Lane Completion Detection Protocols: Research Findings

**Date:** 2026-10-02
**Purpose:** Investigate how other projects detect when parallel lanes/tasks finish, so the fanout skill's lane watcher can reliably identify completion and stop cleanly.

## Problem Statement

The fan-out orchestrator launches parallel lanes (via `claude --bg`) to execute work concurrently. The current lane-watcher implementation checks status via `claude agents --json --all` every 10 minutes, looking for lanes that report "done". However:

1. **Lanes show "blocked" when idle at prompt**, not "done"
2. The watcher only stops when it sees every lane report `done`, `failed`, or `stopped`
3. A finished lane that shows "blocked" may never send a terminal state
4. The watcher keeps re-sending "blocked" notifications every 30 minutes until it expires after 7 days

This creates a false-alarm pattern where working lanes appear stalled.

## Research Findings

### 1. Claude Code / Agent Status States

From the hooks documentation (`code.claude.com/docs/en/hooks`), Claude Code agent status includes:
- **done** — task completed successfully
- **failed** — task encountered an error
- **stopped** — task was manually stopped
- **idle** — agent at prompt awaiting input (not in the official state enum)
- **blocked** — agent waiting for something (often mapped from "idle")

**Key finding:** Being "idle at the prompt" is functionally equivalent to "task finished" from an orchestration perspective, but `claude agents` reports it as "blocked".

### 2. Multi-Agent Orchestration Patterns

Research across parallel orchestration implementations identifies three competing completion-detection strategies:

| Pattern | Mechanism | Pros | Cons |
|---------|-----------|------|------|
| **Exit Code Polling** | Check subprocess exit code, process exit time | Deterministic, no ambiguity | Requires process ownership |
| **Status Enum Watch** | Poll agent/task status field for terminal states | Native to most orchestration systems | "Idle" not always mapped to "done" |
| **Artifact Existence** | Check for durable output file (report, PR, commit) | Immune to state API bugs | Adds complexity, not all lanes write artifacts |
| **Event/Message Based** | Subscribe to completion messages from lanes | Clean separation | Requires message broker/pub-sub |
| **Heartbeat + Timeout** | Track last activity timestamp, declare done if silent ≥ T | Detects hangs | False positives if lane is slow |

### 3. Existing Implementations

**GitHub Actions:**
- Uses job `conclusion` field as source of truth (not `status`)
- `conclusion` values: `success`, `failure`, `skipped`, `cancelled`, `timed_out`
- Skipped jobs are terminal states (valid completion)
- Query via `gh run view --json conclusion` (not `gh run watch --exit-status`, which has reported 0 prematurely)

**Kubernetes Jobs:**
- Uses `job.status.conditions` array with `type: "Complete"` or `type: "Failed"`
- Active running jobs have neither condition
- Idle completed job shows `complete=true` explicitly

**Apache Airflow:**
- Task states: `success`, `failed`, `upstream_failed`, `skipped`, `removed`
- DAG completion = ALL tasks in a terminal state
- Distinguishes "skipped" (not applicable) from "completed" (ran and succeeded)

**Zapier / Automation Services:**
- Uses explicit terminal states: `completed`, `failed`
- "Idle" does not exist — all agents report an action outcome
- Requires explicit agent instruction to declare done

### 4. The "Idle at Prompt" Problem

The pattern observed in this project is that Claude Code agents reaching `STOP AT: commit on the branch` (per the brief template in `parallel-work-split` skill) naturally stop running and wait for input. In this state:

1. The agent is **functionally complete** — it has done its assigned work
2. The agent is **reporting as "blocked"** — waiting for external input
3. The watcher **treats this as stalled** — checks forever if no completion signal

**Solutions used by other projects:**
- Kubernetes: Make completion explicit via `status.conditions`
- GitHub: Require explicit conclusion even for "neutral" outcomes
- Airflow: Distinguish "skipped" from "success" but both are terminal
- Custom systems: Use the agent's final message / report file as completion proof

### 5. Protocol Options for This Repository

The research reveals three viable paths:

**Option A: Treat "Idle at Prompt + Report File" as Done**
- Check for agent `state == "blocked"` AND report file exists at expected path
- Requires: brief template mandates `PERSIST: report to <path>`
- Arm 1: Agent finishes work, writes report, stops → `blocked` + file exists → done
- Arm 2: Agent still working → `blocked` but no file yet → keep waiting
- Pro: Uses existing artifact convention, no agent changes needed
- Con: Must defend against false positives (file created mid-work)

**Option B: Require Explicit Lane Completion Message**
- Each lane writes a `<lane>.completion.json` at the very end
- File contains timestamp, PR number (if opened), final status code
- Watcher polls for these completion files
- Pro: Unambiguous, machine-readable, matches orchestration best practices
- Con: Requires brief template change + new agent instruction

**Option C: Check PR Existence + Main Branch State**
- Lane that "finished work" should have a merged PR or a report on disk
- Watcher verifies: `gh pr view <n> --json state` returns `MERGED`, or
- Report file exists AND matches expected location from plan
- Pro: Directly validates work outcome (did the PR ship?)
- Con: Not all lanes open PRs (some are pure research); adds external dependency

**Option D: Hybrid — PR + Report + Timeout**
- If a lane has a PR: check PR state (MERGED = done)
- If not: check report file OR deadline (e.g., 2 hours = abandon and stop watcher)
- Pro: Covers all lane types, prevents 7-day hangs
- Con: Most complex; requires plan to specify which lane opens which PR

### 6. Existing Session Status Tracking

The project's `orchestration-status.v1.schema.json` includes:
- `completion_gate.phase` — tracks orchestration lifecycle phase
- Per-worktree: `state` field (active|protected|retained|landed-history)
- Per-clone: `cleanup_precondition` — defines when clones are safe to remove

**Gap:** No "lane completion status" field at the session or lane level.

## Recommendation

**Implement Option A + B Hybrid:**

1. **Immediate fix (Option A):** Update lane-watcher to treat agent in "blocked" state + report file present as terminal completion
2. **Medium-term (Option B):** Add `<lane>.completion.json` to completion detection; include PR number, final status, timestamp
3. **Plan**: Minimal changes to brief template; large payload benefit (unambiguous terminal state)

### Specific Changes

**Lane Watcher Logic:**
```python
def is_lane_complete(lane_name: str, plan: Dict) -> bool:
    # Check agent status
    agent = claude_agents_by_name(lane_name)
    
    # Terminal states
    if agent.state in ("done", "failed", "stopped"):
        return True
    
    # Idle-at-prompt + work complete pattern
    if agent.state == "blocked":
        # Check for completion artifacts
        report_path = plan.lanes[lane_name].report_path
        if (Path(report_path).exists() and 
            (Path(report_path.parent) / f"{lane_name}.completion.json").exists()):
            return True  # Report exists + completion marker
    
    return False
```

**Completion Marker Schema:**
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

**Brief Template Addition:**
```
COMPLETION: At end, write .agent/completion/<lane>.completion.json with:
  {"lane": "<lane>", "completed_at": <ISO8601>, "pr_number": <n or null>, 
   "pr_state": "MERGED|OPEN|CLOSED", "final_status": "success|partial|failed"}
```

## GitHub Repos Touched

- [mohamedwalid/agent-orchestrator](https://github.com/mohamedwaleid/agent-orchestrator) — skiplist patterns for task status
- [apache/airflow](https://github.com/apache/airflow) — terminal task states and completion gates
- [kubernetes/kubernetes](https://github.com/kubernetes/kubernetes) — job status conditions and completion field
- Zapier Help / API docs (via firecrawl) — automation platform completion states

