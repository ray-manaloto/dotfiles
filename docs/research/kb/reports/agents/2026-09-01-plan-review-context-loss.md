# Prioritised review — context loss across `/session-handoff` and `/session-resume`

**Scope:** handoff/resume context fidelity only. No repository files were changed besides this report.

**Method:** compare consecutive `.agent/plans/session-*.md` artifacts, then test their claims against the next artifact, the current skills/tasks, and Phase 15/17 of `task_plan.md`. Absence findings include a same-shape positive control.

**Graph orientation (UNVERIFIED by graph evidence):** `mise run graphify-health` and the required `mise run graphify-query -- "Across consecutive session handoffs and resumes, what facts were omitted or misstated and then had to be re-derived, especially session-state PR status disagreement and Phase 15 defects?"` were attempted first; both were unavailable because `uv` could not initialize `/Users/rmanaloto/Library/Caches/uv` under the sandbox. Source is therefore the authority for this review.

## 1. Ranked next actions

### 1. Fix `session-state` to enumerate terminal PR states and render the owed post-merge verb

**Action:** Replace `--state open` with explicit `--state all`, request `state`/`mergedAt`, model `MERGED` and `CLOSED`, render `MERGED` as `mise run land -- <PR#>`, and handle 0/1/many rows explicitly instead of silently taking `rows[0]`; control-arm merged and multiple-PR fixtures.

**Why #1:** This is a silent gate-skipping failure in the most actionable handoff field. The observed handoff said `#892 OPEN, auto-merge ARMED`, the next resume saw `open PR: none`, while reality was merged and `land -- 892` was owed (`task_plan.md:1035-1040`). The defect remains in the current tree: `_pull_request` still calls `gh pr list --state open`, maps `[]` to `PrState.NONE`, and consumes only `rows[0]` (`python/src/dotfiles_setup/session_state.py:194-229`); rendering still prints `open PR: none` (`python/src/dotfiles_setup/session_state.py:273-286`); and the test suite pins only `none/open/unverifiable`, with no terminal PR state (`tests/test_session_state.py:348-353`). **The plan's own recommended “drop `--state open`” fix is incomplete:** installed GitHub CLI 2.98.0 defaults `gh pr list` to open-only and requires `--state all` to remove that bound (`/Users/rmanaloto/.local/share/mise/installs/gh/2.98.0/gh_2.98.0_macOS_arm64/share/man/man1/gh-pr-list.1:12-14,72-74`); the repo already uses explicit `--state all` for complete PR enumeration (`python/src/dotfiles_setup/pr.py:192-195`). Phase 15's implementation is still `NOT STARTED`, but its proposed command must be corrected before dispatch (`task_plan.md:1077-1081`).

### 2. Make every successor handoff dispose every prior `OWED` item, and make `handoff-check` compare versions

**Action:** Require each prior obligation to reappear as `DONE`, `STILL OWED`, or `SUPERSEDED (reason)` in the successor; make the resume-side prior-list comparison unconditional rather than “when completeness matters.”

**Why #2:** An owed post-merge gate disappeared independently of the `session-state` bug. `session-2026-09-01-b.md` carries both `land -- 892` and `land -- 890` (`.agent/plans/session-2026-09-01-b.md:95-102`); the successor records completion of `land -- 892` (`.agent/plans/session-2026-09-01-c.md:30-35`) but its new `Owed` list omits `land -- 890` without saying done or superseded (`.agent/plans/session-2026-09-01-c.md:114-121`). Its real disposition is **UNVERIFIED**. Absence control run: `rg -n -F 'land -- 890' .agent/plans/session-2026-09-01-c.md` returned 0, while the same command shape for the known-present `land -- 892` returned line 34. The checker explicitly says it does not reconcile claims across versions (`python/src/dotfiles_setup/handoff_check.py:2-7`), and `/session-resume` only asks for prior-owed reconciliation “when completeness matters” (`.claude/skills/session-resume/SKILL.md:93-100`).

### 3. Bind review/gate claims to an exact-SHA durable receipt, not prose

**Action:** A handoff may say “receipt exists” only when it includes the exact HEAD SHA and receipt path verified on disk; otherwise say “review reported clean; receipt unverified.”

**Why #3:** This caused expensive re-derivation, not just confusion. The sending handoff said knowledge-base PR #611 was shipped with a cold-review receipt (`.agent/plans/session-2026-08-29e.md:20-24`). The next session records that `kb-land` refused because no machine-local receipt existed for exact HEAD `e300f810…`; it then had to rerun the cold review, persist a report, create the receipt, and retry land (`.agent/plans/session-2026-08-29f.md:61-73`). That next handoff explicitly extracts the lesson: prose claiming a receipt is not the receipt (`.agent/plans/session-2026-08-29f.md:104-108`). Current self-verification checks cited paths, task names, and gate rc values, but it does not require an exact-SHA receipt citation for a review-coverage claim (`.claude/skills/session-handoff/SKILL.md:220-231`).

### 4. Give every volatile fact an `as of` condition and its transition action

**Action:** For PR/CI state, dependency currency, counts, and branch/SHA relationships, record `observed_at`, the probe scope, and what to do if the state has advanced; `/session-resume` must re-run those probes.

**Why #4:** Consecutive handoffs show the same loss class outside PR state. `session-2026-08-31b.md` records the dependency DoD as simply `MET` (`.agent/plans/session-2026-08-31b.md:24-37`); the next handoff says it re-derived the claim, found aws-cli, pydantic, and ty outdated, and had already shipped while trusting the inherited number (`.agent/plans/session-2026-08-31c.md:39-51`). Likewise the `2026-09-01-b` handoff records 37 branches (`.agent/plans/session-2026-09-01-b.md:49-51`), while the next reports 42 and requires re-enumeration before deletion (`.agent/plans/session-2026-09-01-c.md:123-129`). These may have been true when written; that is precisely why an unqualified snapshot is unsafe. Phase 15 notices the wider class but leaves it only as a pre-fix coverage question (`task_plan.md:1112-1126`).

### 5. Either make the newest handoff truly self-sufficient or load its predecessor chain mechanically

**Action:** Prefer folding the complete current state into each successor; if delta handoffs remain allowed, declare a predecessor and have `/session-resume` read the chain before reconciling.

**Why #5:** The writer contract says the local handoff must be self-sufficient (`.claude/skills/session-handoff/SKILL.md:160-169`), while the reader selects and reads only one newest file (`.claude/skills/session-resume/SKILL.md:22-31`; `python/src/dotfiles_setup/handoff_check.py:51-67`). Real artifacts violate that contract: `session-2026-09-01-b.md` calls itself a delta and tells the reader to open its predecessor for the detail it omitted (`.agent/plans/session-2026-09-01-b.md:1-6,71-83`). The next successor then supersedes that delta (`.agent/plans/session-2026-09-01-c.md:1-8`). This chain makes context retention depend on an agent noticing prose links that the selection/checking mechanism does not follow.

### 6. Run the existing `handoff-check` on the sending side

**Action:** Replace the stale “step-2.5 ref loop” instruction with `mise run handoff-check -- <new-handoff>` as a hard pre-prompt gate; keep its documented limitation that citation success is not completeness.

**Why #6:** `/session-handoff` tells the writer to validate cited paths using a “step-2.5 ref loop” (`.claude/skills/session-handoff/SKILL.md:220-231`), but its own earlier section says the ad-hoc loop was retired and must not be hand-rolled (`.claude/skills/session-handoff/SKILL.md:103-126`). The supported checker already exists (`mise.toml:901-904`) and `/session-resume` invokes it (`.claude/skills/session-resume/SKILL.md:52-60`), but the sender never names it. Absence control run: fixed-string `mise run handoff-check` returned 0 in `session-handoff/SKILL.md` and a hit at line 55 in `session-resume/SKILL.md`.

### 7. Give cross-surface `/resume` the same live reconciliation contract

**Action:** Run `session-state`/`handoff-check` and report disagreements before `/resume` continues; make cross-surface `/handoff` perform session-handoff step 0 as well.

**Why #7:** The same-clone reader explicitly snapshots live state and leads with contradictions (`.claude/skills/session-resume/SKILL.md:42-66`), but cross-surface `/resume` only pulls, reads, restates, and optionally reruns gates (`.claude/skills/resume/SKILL.md:15-59`). Absence control run: the same fixed-string grep found `mise run session-state` at `.claude/skills/session-resume/SKILL.md:47` and 0 hits in `.claude/skills/resume/SKILL.md`. Its sender also says to inherit session-handoff steps **1-4**, skipping mandatory ambiguity-resolution step 0 (`.claude/skills/handoff/SKILL.md:18-27`; `.claude/skills/session-handoff/SKILL.md:19-37`). No measured cross-surface failure was present in the examined local-handoff corpus, so the impact is **UNVERIFIED** and this ranks below the replay-proven losses.

## 2. What is already done (do not rebuild it)

- **No core Phase 15 fix is already done.** The open-only query, `NONE` rendering, and three-state tests remain in the current tree (`python/src/dotfiles_setup/session_state.py:194-229,273-286`; `tests/test_session_state.py:348-353`), so the plan is correct to label the implementation `NOT STARTED` (`task_plan.md:1033-1043`).
- **Failure vs answered-empty is already modeled.** Command failure, malformed JSON, and detached HEAD become `UNVERIFIABLE`; only a successful empty query becomes `NONE` (`python/src/dotfiles_setup/session_state.py:194-217`). Preserve that distinction while widening the query.
- **The task seams already exist.** `session-state` and `handoff-check` are thin mise tasks over Python modules (`mise.toml:896-904`); extend these rather than add a new script or prose-only workaround.
- **Citation validation and its limitation are explicit.** `handoff-check` validates repo-relative file/line citations and mise task names, while explicitly declining completeness/version reconciliation (`python/src/dotfiles_setup/handoff_check.py:2-7,155-169`).
- **The sending skill already carries most manual anti-loss discipline.** It mandates ambiguity resolution and verbatim user answers (`.claude/skills/session-handoff/SKILL.md:19-37`), session/autonomous-process inventory (`.claude/skills/session-handoff/SKILL.md:39-75`), a self-sufficient artifact (`.claude/skills/session-handoff/SKILL.md:160-169`), brief/report coverage (`.claude/skills/session-handoff/SKILL.md:171-184`), and path/task/rc verification (`.claude/skills/session-handoff/SKILL.md:220-231`).
- **Incremental report persistence is already policy.** Findings-bearing reports must be persisted verbatim at receipt, agents must write incrementally, and handoff must reconcile every launch to a brief and report (`.claude/rules/agent-report-persistence.md:20-59`); the notepad likewise requires as-you-go findings (`.claude/rules/notepad-enforcement.md:17-30`).
- **The desired conditional-action wording has already been demonstrated once.** The #892 handoff said “Owed after it merges: `mise run land -- 892`” (`.agent/plans/session-2026-09-01-b.md:32-35`). What remains is making that shape mandatory and machine-reconciled, including an observation timestamp.

## 3. What the plan is missing for this theme

- **An obligation-continuity invariant.** Phase 15 is framed around #892's live transition but does not include the independently vanished `land -- 890` obligation (`task_plan.md:1033-1142`; `.agent/plans/session-2026-09-01-b.md:95-102`; `.agent/plans/session-2026-09-01-c.md:114-121`). Same-scope absence control: fixed-string search of Phase 15 found `#892` five times and `#890` zero times.
- **A corrected primary fix.** Phase 15 recommends dropping `--state open` (`task_plan.md:1077-1081`), but GitHub CLI's default is also open-only; the implementation must pass `--state all` explicitly (`/Users/rmanaloto/.local/share/mise/installs/gh/2.98.0/gh_2.98.0_macOS_arm64/share/man/man1/gh-pr-list.1:12-14,72-74`). Otherwise the motivating #892 replay still returns the same bounded empty set.
- **Replay cases for the other measured losses.** The acceptance matrix should include: merged PR → owed land; predecessor `OWED` item → explicit disposition; false exact-receipt claim → refusal at handoff time; and a volatile DoD/count → forced refresh. Today verification only replays #892 (`task_plan.md:1128-1140`), despite the measured receipt re-review (`.agent/plans/session-2026-08-29f.md:61-73`) and inherited-DoD failure (`.agent/plans/session-2026-08-31c.md:39-51`). Same-scope control: Phase 15 contains `session-state` but zero `receipt` hits.
- **The historical intent/report-loss cases as regression evidence.** A transcript audit found the operator's `/grilling` UI contract absent from 44 reports, issue #847, and the handoff, with a same-shape positive control (`docs/research/kb/reports/agents/2026-08-30d-audit-E-transcript-capture.md:75-81`). It also reconciled 60 launches to 50 reported and 10 unaccounted, including five implementation reports and three review/advisor reports (`docs/research/kb/reports/agents/2026-08-30d-audit-E-transcript-capture.md:83-89,140-151`). Current rules improve this materially, but Phase 15 does not use those incidents to test whether the handoff audit catches missing user decisions and artifacts.
- **A declared policy for delta handoffs.** Current contracts simultaneously require a self-sufficient newest file and permit real successors that outsource detail to predecessors (`.claude/skills/session-handoff/SKILL.md:160-169`; `.agent/plans/session-2026-09-01-b.md:1-6,71-83`). The plan needs to choose consolidation or a mechanically loaded chain.
- **Sending-side use of the checker already built for handoffs.** The writer points to a retired loop instead of `handoff-check` (`.claude/skills/session-handoff/SKILL.md:103-126,220-231`; `mise.toml:901-904`), so citation drift is found only after context has already cleared.
- **Cross-surface parity.** `/resume` lacks the live disagreement pass that `/session-resume` performs, and `/handoff` skips session-handoff step 0 (`.claude/skills/resume/SKILL.md:15-59`; `.claude/skills/handoff/SKILL.md:18-27`). This is absent from Phase 15 and remains **UNVERIFIED** by a cross-surface replay.
- **A correction to Phase 15.3's volatile branch-count example.** The plan says the handoff's 37 became “reality 40” (`task_plan.md:1118-1121`), but the later handoff records 42 and orders another enumeration before deletion (`.agent/plans/session-2026-09-01-c.md:123-129`). The current count is **UNVERIFIED**; the stale example itself demonstrates why counts need `observed_at`.
- **Phase 17 does not record any of this session's context-loss evidence.** Its current findings cover other defects and shipped work (`task_plan.md:1418-1458`). Absence control run over exactly that section: `session-state` returned 0 while known-present `plan-attest` returned one hit.

## 4. Single highest-value next action

**Implement and control-arm Phase 15 end to end: query `gh pr list --state all`, handle 0/1/many rows, return `MERGED`/`CLOSED` with the owed verb, then require the successor handoff to disposition every prior `OWED` item before `/session-resume` can report orientation complete.**
