# Proposals: applying watcher 998ab91b's handoff findings (session-2026-10-03f)

Plan subagent of coordinator 27e2bf5c, 2026-10-03 ~14:45 CDT, read-only. Persisted verbatim by the coordinator.

## Applying the findings from watcher 998ab91b's handoff (session-2026-10-03f): cited proposals

This was a read-only review, so nothing is written yet. The coordinator needs to save this report under `docs/research/kb/reports/agents/`.

I checked everything against `origin/main` @ 984d3571. The handoff branch `docs/lane-completion-protocol` is at de9575bd locally and 1dcf0d4b on origin. That branch changes **only docs and reports**: `git diff --name-only origin/main...de9575bd` lists 21 files, none of them a shared skill or rule. So it collides with no lane.

### Verified claims (each checked against a control)
- **The dag-tick fix is not on main.** `origin/main:dag_tick.py:1384` is still `[ctx.claude_bin, "stop", node_id]`, and running `git merge-base --is-ancestor 060de30b origin/main` returns 1. Only `feat/session-autostart-no-prompts` contains 060de30b. That branch already has the test `test_execute_tick_never_stops_a_done_node_with_live_pid` (in `tests/test_dag_tick.py` on the branch). `task_plan.md:2511` says "code fix (A) DONE", which is wrong. `task_plan.md:2517` correctly says "re-enable after 060de30b ships".
- **The bypass alarm in `command_audit.py` cannot see failed commands.** `origin/main:command_audit.py:337` keeps a result only when it is a dict with stdout. `grep -c 'Error: Exit code'` returns 0, while the control `grep -c stdout` returns 9. No branch contains a fix (`git log --all -S`: 0 hits).
  - A live control in this session: hook_guard denied my own unquoted `echo ===`. The guard works; the gap is only the audit's classifier.
- **The auto-recovery brief is stale.** `.agent/plans/handoff-inbox/auto-recovery-handoff.md:7` still points at `recovery-handoff-7541ae79.md`, and `grep -c CONSUMED` on that file returns 0.
  - Both files are gitignored (`.gitignore:125 .agent/`), so they live only in the main checkout.
  - `.agent/state/watch/tick.py:123` passes this brief to every auto-launch.
- **Two issues are missing.** No issue exists for the launchd supervisor or for a universal `/session-handoff`. The same `gh issue list --search` query does work: it returned #578 (closed) for "launchd supervisor" and #910/#891/#623 for the session-handoff query.
  - `task_plan.md:2536` records only "Rec 1 launchd supervisor SEPARATE; lane AFTER llvm23".
- **No `mise run handoff-inbox` task exists.** `mise.toml` has 0 hits, but `coordinator_handoff.py:108` already defines `HANDOFF_INBOX`, which the new task can reuse.
- **The `agentsview_pass.py` bug is real.** `agentsview_pass.py:160,310` use `repo_root.name` as `--project`.
- **The §5/§6 hunk exists only in scratch.** It is at `~/.claude/jobs/998ab91b/tmp/skill-hunk.md` and is not on the branch, so the FIX-NOW for V3 has not been done. `parallel-work-split/SKILL.md` on origin/main has 0 "dag-tick" hits, against 17 "worktree" hits, which confirms R1.

### Measured overlap with lanes in flight
Overlaps are measured from `git diff --name-only origin/main...<branch>` plus `git status`.

| Fix target | In-flight lane touching it | Overlap |
|---|---|---|
| `.claude/skills/parallel-work-split/SKILL.md` | #1606 (hunk @@86), plus the pending §5/§6 hunk | YES |
| `.claude/skills/coordinator-handoff/SKILL.md` | #1606 (@@46, @@58, @@60) | YES |
| `python/src/dotfiles_setup/hook_guard.py` (push-slot rule) | #1606 | YES |
| `.claude/skills/research-sweep/SKILL.md`, `.claude/workflows/research-sweep-run.js`, `tests/test_workflows_js.py` | saved-searches-1502 (uncommitted M) | YES |
| `python/src/dotfiles_setup/main.py` (only if the agentsview fix touches `:2976`) | lock-format (uncommitted M), autostart | YES; avoid it |
| `python/src/dotfiles_setup/dag_tick.py`, `tests/test_dag_tick.py` | autostart (this is the fix itself) | the owner |
| `.claude/skills/session-handoff/SKILL.md` | none today; handoff-automation research will propose changes (sweep §Recommendation 1) | soon |
| `command_audit.py` + its test, `agentsview_pass.py`, `session_orphans.py`, `rules/agent-artifact-conventions.md`, `rules/long-running-command-hangs.md`, `rules/research-repo-enumeration.md`, `rules/agent-report-persistence.md` | none (llvm23 touches only `.github/workflows/refresh.yml`; lock-format touches the `lock-image` skill, workflows and `python/src`, none of these) | NO |

---

### Q1. Sequencing
**A (recommended): apply the report-only fixes on de9575bd's branch first, then ship it at its "watch-push" slot.**
- The fixes: V3 (copy the hunk in as `parallel-work-split-hunk-2026-10-02.md`), V5–V9, V12, V13, and process F7. All of them edit reports that exist only on this branch.
- PRO: the reports reach main already corrected, with no collision, since the branch touches docs only. The hunk leaves job scratch before 998ab91b's job dir is removed. Every later lane can cite paths on main.
- CON: the push is still in the "unruled tail" of `session-2026-10-03e.md:53-55`. The pre-push hook runs the full suite, so it needs a host slot (process F2). Lint and verify are owed first (process F1).

**B: ship de9575bd exactly as it is now, then fix the reports in a follow-up docs PR.**
- PRO: fastest to main, with zero edits to the branch.
- CON: stale claims land on main (V5/V6: R1 "UNCONFIRMED", and R2 assumes auto-compact is on). It costs two docs PRs.

**C: skip the branch and apply the fixes straight to the shared files.**
- CON: the fixes cite reports that are not on main. It breaks the one-writer order in the 10-03f handoff (:34).

### Q2. Grouping (one lane or several)
**A (recommended): five groups, each keyed to the files it touches.**
- **L0 "urgent-code":** `command_audit.py` + `tests/test_command_audit.py`, `agentsview_pass.py` + its test (no `main.py`), `session_orphans.py:83`. This is the only urgent code group with zero overlap, and it can take the next free slot.
- **L1 "docs-rules":**
  - rules: `agent-artifact-conventions.md` (R3, plus ruling (b) and the quoted `"rc=$?"` workaround), `long-running-command-hangs.md` (R7), `research-repo-enumeration.md` + `agent-report-persistence.md` (process F7);
  - `session-handoff/SKILL.md` (R4, R8);
  - memory `feedback_no_compact.md` (R11: user-scope, outside the repo, coordinator writes it).
  - Ship this group before handoff-automation produces a spec.
- **L2 "after-#1606":**
  - `parallel-work-split` R1, R2, R9, the §5/§6 hunk with V10's fix, and S1003f-3 at :141;
  - `coordinator-handoff` R5, R6, and the HOST SLOT line;
  - the push-slot rule in `hook_guard.py`.
  - It rebases onto the #1606 merge. This is also the single follow-up branch that V3's PLAN asks for.
- **L3 "after-1502":** R10 (`research-sweep/SKILL.md:30`) and S1003f-4 (the `research-sweep-run.js` preflight plus a `tests/test_workflows_js.py` arm). It rides behind slot 7 (`session-2026-10-03e.md:44`).
- **L4 "coordinator-direct":** task_plan rows, GitHub comments and issues, and the inbox brief. These are coordinator-owned writes, not a lane.
- PRO: no group edits a file another live lane is editing. L0 and L1 can start now.
- CON: five units to track. L2 and L3 wait behind items 2b and 7.

**B: one lane after llvm23, as the 10-03f handoff (:34) proposes.**
- PRO: a single owner and one PR.
- CON: it collides with #1606 and 1502 anyway, and it delays the HIGH code fixes until after item 9/10, the very end of the queue.

**C: one lane per audit report.**
- CON: three reports each touch `parallel-work-split`, so the reports' lanes would conflict with each other.

### Q3. Classification of all 48 findings
Abbreviations used in this table:
- **Audit files:** DE = dismissed-errors, MR = missing-requests, PC = process-compliance, RO = repeat-offenders, RM = retrieval-misses, VG = vagueness. The number after the colon is the line in that audit file.
- **Targets:** pws = `parallel-work-split/SKILL.md`, ch = `coordinator-handoff/SKILL.md`, sh = `session-handoff/SKILL.md`.
- **Action:** FIX = apply now; TP = add a `task_plan.md` row; ISS = file or comment on a GitHub issue.

| ID | Audit:line | Action | Target | Collides with |
|---|---|---|---|---|
| RO-F1, handoff #2 | RO:28,73 | FIX (L0); TP S1003f-1 to triage again afterwards | `command_audit.py:337` + test | none |
| RO-F5, RM-R1, handoff R-1 | RO:180,200; RM:R1 | FIX: ship autostart (slot 3); TP: correct `:2511`; ISS: doctor check that dag-tick is loaded while main still contains the stop | `dag_tick.py`; pws §6 (L-R1 as a stopgap) | autostart; #1606 |
| VG-V1 | VG:27,42 | FIX (L4): mark the list CONSUMED and rewrite :7 | `handoff-inbox/{auto-recovery-handoff,recovery-handoff-7541ae79}.md` | none (gitignored) |
| VG-V2, MR-F4 | VG:48,60; MR:99,110 | TP + ISS: launchd start-only supervisor | `task_plan` (under the a2ccbbc5/27e2bf5c section) | none |
| MR-F1 | MR:53,68 | TP + ISS: universal unattended `/session-handoff`, linked to research lane 4daaf7e1 | `task_plan` | none |
| VG-V3 | VG:63,79 | FIX: hunk onto the branch (Q1-A); TP: owner line at `:2482` | de9575bd; pws | #1606 |
| VG-V4, MR-F2 | VG:86,106; MR:73,85 | FIX (L4): comment on #1549, #1550 and KB#837; retitle #1550; `:2483` note | GitHub; `task_plan` | none |
| VG-V5–V9, V12, V13 | VG:114–271 | FIX on the branch (Q1-A) | reports R1–R3 on de9575bd | none |
| VG-V6 (PLAN half) | VG:147 | TP: ask Ray whether user-scope `autoCompactEnabled:false` is deliberate, then record it in rules-evidence | `task_plan` | none |
| VG-V10 | VG:205,223 | FIX inside the hunk | pws §6 (L2) | #1606 |
| VG-V11, DE-F5, RO-F2, RO-F7 | VG:228; DE:100; RO:85,220 | ISS: comment on #1552 and #1551 (parity list, reading questions from JSONL, INBOX rc line, `session=`/`head=` labels) | #1551/#1552 module | none |
| DE-F1, RM-R4 | DE:20,38; RM:R4 | FIX (L0): code; FIX (L1): sh §1b line | `agentsview_pass.py:160,310`; sh | lock-format, but only if `main.py` is touched |
| DE-F2, RM-R3 (PLAN), RO-F3 ruling (a) | DE:41,66; RO:120,149 | ISS upstream at anthropics/claude-code, after due diligence (refusal text absent from the repo was checked; still owed: a search of issues, PRs and discussions, plus the harness version); FIX (L1): the R3 rule line | `agent-artifact-conventions.md` | none |
| DE-F3 | DE:69,83 | ISS: comment on #1337 recording the second occurrence; TP | AgentsView daemon | none |
| DE-F4 | DE:86,97 | FIX (L0) + TP | `session_orphans.py:83` | none |
| DE-F6 | DE:117,133 | TP: re-run the sweep with OpenHands and ruflo | `task_plan` | none |
| MR-F3 | MR:88,96 | TP at `:2536`; FIX in `WATCHER.md` | watcher brief | none |
| PC-F1 | PC:52,60 | FIX: run gate lint and verify before the push | de9575bd | none |
| PC-F2 | PC:64,77 | TP + FIX (L2): HOST SLOT line in ch and the watcher brief; pre-push slot check | ch, `hook_guard.py` | #1606 |
| PC-F3, RO-F3 ruling (b) | PC:82,94 | Already RULED "never". FIX (L0b): `mise run handoff-inbox -- append`, reusing `coordinator_handoff.py:108` | new task | none |
| PC-F4 | PC:99,106 | TP: check the coordinator is alive before a non-coordinator writes `task_plan` | `task_plan` | none |
| PC-F5 | PC:109,117 | Verify only: the inventory was persisted on the branch (handoff :21). Confirm it is verbatim, then link #1551 | report | none |
| PC-F6 | PC:121,128 | TP: promote or discard the draft spec before the worktree is removed | `lane-completion/.agent/plans/draft-…UNREVIEWED.md` | none |
| PC-F7 | PC:132,142 | FIX (L1): allow a trailing `## Addendum` | two rules | none |
| RO-F3 (rule half) | RO:149 | FIX (L2) pws :141, plus `WATCHER.md` | pws | #1606 |
| RO-F4, RM-R10 | RO:160,174; RM:R10 | FIX (L3) | workflow js + test; `research-sweep` :30 | 1502 |
| RO-F6 | RO:206,215 | ISS: new follow-up issue "#1606 guard for every lane launch". Do not widen #1606 itself, which is in cold review | `worktree_guard.py` | #1606 |
| RM-R2, R9 | RM:R2,R9 | FIX (L2) | pws :134, §6 | #1606 |
| RM-R5, R6 | RM:R5,R6 | FIX (L2) | ch :24, :57 | #1606 |
| RM-R7 | RM:R7 | FIX (L1) | `long-running-command-hangs.md` rule 2 | none |
| RM-R8 | RM:R8 | FIX (L1) | sh :36 | none |
| RM-R11 | RM:R11 | FIX (L4, memory) | `feedback_no_compact.md` | none |

### Q4. Urgent items first
**A (recommended): do these now, in this order.**
1. **Brief:** the coordinator, working from the main checkout, edits the two inbox files. This is VG-V1's exact text. If the coordinator is worktree-isolated, ruling (b) forbids routing the write through Bash. Then build L0b's `handoff-inbox` task first and use it.
2. **dag-tick:** keep autostart at slot 3, the next real slot after 2b/2b'/2c. Correct `task_plan:2511` to "DONE on feat/session-autostart-no-prompts, NOT on main" now.
3. **L0** goes in parallel with the #1606 gates: it overlaps no files, but its pytest run needs a host slot.
4. **Issues:** file both missing issues now. Routine filing is allowed under the autonomy ruling at `task_plan:2500`.
- PRO: three HIGH findings are closed within the hour, and no queue reorder is needed.
- CON: L0 competes for the host slot with #1606's full gates.

**B: move autostart to item 2b, ahead of #1606.**
- PRO: the outage cause is gone sooner.
- CON: it reorders Ray's ruled queue. dag-tick is already `launchctl disable`d (`:2517`), so the risk is contained.

**C: wait for the single lane after llvm23.**
- CON: the bypass alarm stays blind for the whole queue, and the stale brief stays live for every auto-launch from `tick.py:123`.

### Q5. Making it automatic (handoff findings applied and merged with no human step)
**A (recommended): extend the research lane's own recommendation with an "apply ledger".**
The research lane's recommendation is in `session-handoff-automation-sweep-2026-10-03.md:172-203`: keep `session.measure`, add a role table, ship each lane's handoff on its own branch through `mise run ship`, and auto-merge.
- **Structured findings:** every audit finding becomes typed, with id, severity, disposition (FIX/TP/ISS), target file and exact text. They are emitted to `docs/handoffs/<session>.findings.toml`. A `mise run handoff-apply` task (Python, following zero-bash-logic) does three things:
  - ISS: files or comments through `gh`;
  - TP: queues rows to a coordinator-applied file, because `task_plan` is coordinator-only;
  - FIX: for each target file, opens a gated branch, runs `/code-review`, and runs `mise run ship` with auto-merge.
- **Collision check:** before branching, it runs `git merge-tree` against the live lanes, as `parallel-work-split` already prescribes. A colliding finding is parked behind that lane's merge.
- **Check:** `handoff-check` fails a handoff that has a finding with no disposition receipt (PR, issue or TP row).
- **Writes:** inbox writes go only through `mise run handoff-inbox` (ruling b).
- PRO: this is exactly Ray's standing rule, made checkable. It reuses ship, auto-merge and handoff-check.
- CON: it is new code, and it needs a spec plus a live test (`real-integration-evidence`). The audit lanes' output format must change to typed records.

**B: make the coordinator's handoff checklist require applying every finding.**
- PRO: no code.
- CON: it is still human-shaped. This handoff shows the gap: 48 findings and 0 applied.

**C: native draft PRs from background worktrees.**
- CON: the sweep rejects this (`:183-187`). It is conditional, never merges, and bypasses the gates.

Add (A) as a scope item to the research lane's brief (`brief-handoff-automation-research-20261003.md:30-32`), so its seven-part spec covers both "handoff runs" and "findings land".

## GitHub repos touched
- ray-manaloto/dotfiles: read-only `gh issue list` searches. No writes.
