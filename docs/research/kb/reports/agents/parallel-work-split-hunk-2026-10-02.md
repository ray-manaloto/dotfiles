## Proposed change to `.claude/skills/parallel-work-split/SKILL.md`
Source: `docs/research/kb/reports/agents/fanout-lane-completion-detection-2026-10-02.md` (branch `docs/lane-completion-protocol`). The protocol is UNTESTED design synthesis; see the report's Verification section.

### §5 brief template: add these two lines after PERSIST

```text
VERDICT: your LAST act is to end the report file with exactly one line:
  LANE-VERDICT: done|needs-input|failed  commit=<sha|none>  question=<one line or ->
ASK: need a human? Use AskUserQuestion, or write `needs-input` with the question. Never end a turn on a prose question.
```

### §6 monitor and collect: replace the "Check for state == blocked…" paragraph with this

**Classify every lane on every poll.** Read `claude agents --json --all` (always with `--all`) and the lane's
report file. Apply the first row that matches. Alert when a lane's CLASS changes, not on every poll.

| # | Condition | Class | Watcher action |
|---|---|---|---|
| 1 | `status == "waiting"` (`waitingFor` set) | BLOCKED-LIVE | Alert now with `waitingFor` and the prompt from `claude logs <id>`. Ray clears it in `claude agents` → `→` on the row, or `claude attach <id>`. This row outranks every verdict. |
| 2 | verdict `needs-input` | BLOCKED-ASKED | Alert with the question from the verdict line. |
| 3 | verdict `failed`, or `state` ∈ {failed, stopped} with no `done` verdict | TERMINAL-FAIL | Alert. Counts as terminal for exit, but is reported as a failure. |
| 4 | `state == "done"`, verdict `done`, and the commit is reachable on the lane branch | FINISHED | Terminal. |
| 4b | verdict `done` and the commit is reachable, but `state != "done"` | FINISHED-UNCONFIRMED | Alert once with the observed `state` and keep polling. Measured 2026-10-02: KB2 read `blocked` with no `waitingFor` while idle and finished; lane G read `working`/`idle` for over an hour after finishing. |
| 5 | `state == "working"` | RUNNING | Keep waiting. A `working` lane with `status == "idle"` may be waiting on its own background work; alert only after a stale-age bound. |
| 6 | anything else (no verdict) | UNREPORTED-STOP | Alert once and SendMessage the lane to write its verdict. Never counts as finished. |

The watcher exits only when every lane is FINISHED or TERMINAL-FAIL, under an overall deadline. Push signals
(`notify_when_idle`, `agent_completed`, `idle_prompt`) only trigger an earlier poll and never replace it: they
are edge-triggered and lossy (#79570, #20754, #92095). Codex lanes: completion is process exit plus the
`-o` final-message file (as `lane_result.py` and the `sdlc-team` settlement already do).
