# Session audit (Brief P): vague or misinterpretable docs and plans, session 2026-09-23d (`a6750a24`)

Status: COMPLETE. Read-only lane; this file was the only write. Brief: `session-2026-09-23d-agent-briefs.md`
§ "Session-integrity review … Briefs M-Q" → "Brief P".

**Scope.** I read the authored instruction surfaces this session changed or created, the way a fresh session or
a codex lane would read them:
- the `219e83cc..HEAD` diff: 5 commits, 53 files;
- the 12 `.claude/agents/codex-{sol,astra}-*.md` wrappers;
- `.claude/rules/ai-cli-invocation.md` and `.claude/rules/codex-sdlc-team.md`;
- both `codex-sdlc-team` SKILL mirrors;
- `docs/agents/goal-history.md` iterations 031 and 032, and `docs/agents/plan-pointer.json`;
- `docs/specs/pr-loop-ship-fix-land.md`;
- `task_plan.md` Phase 11 + addendum (`:505-670`), Current Phase (`:672-680`) and the Phase 10 rulings it
  supersedes (`:355-421`);
- `.agent/plans/session-2026-09-23d.md`;
- the #1351 body, fetched live.

The verbatim agent reports under `docs/research/kb/reports/agents/` are records
(`agent-artifact-conventions.md` rule 8). I read them only where an authored doc points into them, and I propose
no rewrites of them.

**Probes run, each with its arm:**
- #1351 body vs the tracked final file: `cmp` rc=0. Control: the non-final `…-issue-body-2026-09-23.md` differs at
  line 274 (rc=1). So the tracked copy is the live body, and findings against one apply to both.
- Plan hash: `shasum task_plan.md` = `ea2b350e…` = the pointer. `.plan-attestation` = `dc4b9265…` (still stale).
- "Printed literals" probe: `echo "lane files: …"` is found at `codex-sol-implementer.md:148` (positive arm) and in
  none of the other five sol wrappers.
- Citation probe: the pwf reports are cited by no rule, skill or agent (rc=1). Control: `codex-call-audit-2026-09-23`
  is cited in 10 agent files, so the probe discriminates.
- Codex version: `mise exec -- codex --version` → `codex-cli 0.154.0`.
- Harness Bash timeouts: `$CC/env-vars.md:185,187` (default 120000 ms, max 600000 ms). No override exists in
  `.claude/settings.json`: the grep returned empty, while the same file does have an `env` block (count 1).

## Findings

Severity ranks how likely a fresh session or codex lane is to act wrongly on the text.

### P1 — HIGH — 10 codex wrappers tell the model to re-assign variables "from the printed literals", but their setup prints none

- **Claim.** Five sol wrappers (advisor, adversarial-critic, claude-code-expert, staleness-auditor, operator) and
  their five generated astra mirrors all say:

  > Run it in TWO Bash calls … Shell variables do not survive between calls: re-assign `LANE_ID`, `PROMPT`, `OUT`
  > and `LOG` from the printed literals at the top of every later call.

  Their setup block prints nothing on success. The only `echo "lane output: $OUT"` sits after the `codex exec`
  line, which runs in the second, backgrounded call.
- **Why it matters.** `LANE_ID` defaults to `$$-$(date +%s)`, which cannot be recovered. A wrapper that
  re-derives it gets new paths. The wait slice then greps a nonexistent `$LOG` and `pgrep`s the wrong `$OUT`. That
  matches signal 2 ("no rc= AND no live process → it died"), which is the same false-failure class the stopgap
  was written to end.
- **Evidence.** `codex-sol-advisor.md:81-108` (setup and launch), then `:110-116` (the instruction).
  `codex-sol-operator.md:45-80`. The implementer does it correctly: `codex-sol-implementer.md:148`
  `echo "lane files: $PROMPT $OUT $LOG"   # print all three — later slices re-assign them`.
- **Control.** The same grep finds the print line in the implementer (positive arm) and in none of the other
  five sol files.
- **Disposition: FIX-NOW** (sol files only, then `mise run codex-lane-mirror`; the astra files say "Do NOT edit").
  In each of the 5 sol wrappers:
  1. Insert directly after the prompt heredoc's closing `EOF`:
     `echo "lane files: $PROMPT $OUT $LOG"   # report $OUT (the coordinator cannot guess it); later calls re-assign all three`
  2. Delete the trailing `echo "lane output: $OUT"   # report this path — the coordinator cannot guess it` line.
  3. In the "Run it in TWO Bash calls" paragraph, replace "Everything above the `cat "$PROMPT" |` line is setup:
     run it first." with "Everything above the `cat "$PROMPT" |` line is setup and ends by printing the three
     lane paths: run it first."

  Arm: a pytest or contract asserting every `codex-*-*.md` wrapper that says "printed literals" also contains
  `echo "lane files:`. Mutation arm: delete the line from one sol file, and the check must fail.

### P2 — HIGH — `task_plan.md` Current Phase names a NEXT step that is already done, and omits two queued `/to-spec`s

- **Claim.** Current Phase (`task_plan.md:674-677`) says "NEXT: Ray invokes `/to-spec` on the design of record
  (`pwf-migration-fable-round3-2026-09-23.md`, T1-T10)". The addendum says `/to-spec` is done:
  - `:665` reads "pwf migration SPEC PUBLISHED: #1351";
  - `:669-670` reads "NEXT: Ray invokes `/mattpocock-skills:to-tickets` on #1351 (Fable model), then `/to-spec` +
    `/to-tickets` on pr-loop (Fable)".

  Current Phase also omits the codex-invocation class fix `/to-spec` (`:658-664`), whose order relative to pr-loop
  is not stated anywhere. `/session-resume` reads Current Phase first, so it would offer a `/to-spec` that already
  ran.
- **Evidence.** The line numbers above. The plan pointer's `active_phase` is the Phase 11 heading, so the pointer
  cannot catch this.
- **Control.** `gh issue view 1351 -R ray-manaloto/dotfiles` → OPEN, labels `enhancement`/`ready-for-agent`, so
  the spec really exists.
- **Disposition: FIX-NOW** (coordinator edit). Replace `task_plan.md:674-680` with:

  > Phase 11 (fix-first resume + verified handoff + binding python standards) — `/to-spec` DONE (#1326) and
  > `/to-tickets` DONE (#1327–#1342). FIRST PRIORITY (Ray, 2026-09-23): the pwf current-workflow migration in the
  > addendum above. Research, three Fable rounds, codex reviews and `/to-spec` are DONE: **spec #1351**, which
  > replaces `pwf-migration-fable-round3-2026-09-23.md` as the design of record. NEXT, each a user-invoked
  > protocol verb (Ray runs it; an agent names the command and stops):
  > (1) `/mattpocock-skills:to-tickets` on #1351 (Fable model);
  > (2) `/to-spec` → `/to-tickets` on `docs/specs/pr-loop-ship-fix-land.md` (Fable; BUILT only after
  > #1329/#1330);
  > (3) `/to-spec` on the codex-invocation class fix (addendum bullet of that name). The order of (2) vs (3), and
  > whether the native codex installer (Phase 10 rulings, "Codex install = native") is promoted ahead of both, is
  > NOT RULED — ask Ray.
  >
  > Then `/implement` the #1351 tickets, then `/mattpocock-skills:implement #1327` (land the #1141 native
  > AgentsView service), then the remaining frontier and the gates ticket in dependency order. Phase 10 step 0
  > (`/implement` of spec dotfiles#1310, KB#793 first) resumes after Phase 11.

### P3 — HIGH — goal-history has no iteration for this session's topology change or its milestone, and the authority wording contradicts itself across three places

- **Claim, part 1.** `.claude/rules/goal-history.md` requires an iteration after an "orchestration-topology change,
  major milestone … or handoff". This session had two such events, neither recorded:
  - `3f2caac6` moved 10 codex wrappers from haiku to sonnet and changed their launch and wait shape;
  - `762396bc` published #1351.

  The latest iteration, 032, still says "Disposition: … `/to-spec` not started" (`goal-history.md`, 032
  Disposition line).
- **Claim, part 2.** Three texts disagree about who changes the task-authority wording:
  - round 5 (`task_plan.md:639`): "Goal-history 032 CHANGES the goal text to name root roadmap + active ticket
    plan as task authority";
  - round 6 (`:650-651`): "the plan migration (T8) appends its own later iteration with the changed goal text";
  - #1351 (body `:422-425`, user story 31) agrees with round 6.

  032's current goal names "a short root roadmap plus one attested ticket plan" and still ends with "Keep
  task_plan.md as the sole task authority". A reader cannot tell which authority rule is in force.
- **Evidence.** The quoted lines. `git log 219e83cc..HEAD` shows 3 commits after 032's commit `7feb4a29`.
- **Control.** 031 → 032 did change the digest (`afd44520…` → `711f7e97…`), so the validator does see goal-text
  changes. The gap here is a missing iteration, not a broken validator.
- **Disposition: FIX-NOW** (coordinator, append-only), in two edits.

  (a) Mark round 5's goal-history sentence superseded. At `task_plan.md:639`, change
  "Goal-history 032 CHANGES the goal text to name root roadmap + active ticket plan as task authority." to
  "~~Goal-history 032 CHANGES the goal text …~~ SUPERSEDED by round 6: 032 records the re-ordering only; the plan
  migration ticket (#1351, T8) appends the iteration whose goal text names root roadmap + attested ticket plan as
  task authority."

  (b) Append iteration 033:

  ```markdown
  ## 2026-09-23 — pwf migration spec #1351 published; codex-wrapper stopgap `3f2caac6`

  - **Iteration ID:** `dotfiles-goal-20260923-033`
  - **Prior goal digest:** `sha256:711f7e97ef6be6f6f54b8386dd098840055b0ddf4b06259ed26635fc51a8518a`
  - **Current goal digest:** `sha256:711f7e97ef6be6f6f54b8386dd098840055b0ddf4b06259ed26635fc51a8518a`
  - **Changed requirement:** None to the goal text. `/to-spec` for the pwf migration is DONE: #1351 replaces
    `pwf-migration-fable-round3-2026-09-23.md` as the design of record. Until the #1351 plan-migration ticket
    appends its own iteration (goal-text wording is a Ray stop), "Keep task_plan.md as the sole task authority"
    means the ROOT roadmap. Orchestration topology changed: the ten codex-{sol,astra} advisor / critic /
    claude-code-expert / staleness-auditor / operator wrappers run on sonnet (was haiku), launch codex with
    `run_in_background` and wait in bounded slices on an `rc=` sentinel. No wrapper passes `--ephemeral`.
    `sdlc_team` passes no `-s`. The 12 wrappers still pass `--sandbox` (commit `3f2caac6`'s title "drop … -s"
    covers `sdlc_team` only).
  - **Reason:** Ray: "Stopgap now, rest as Phase 11" (codex-invocation class fix); spec-v2 design questions 1-5
    ruled as recommended.
  - **Evidence:** `3f2caac6` (commit body: pytest rc=0 3758 passed, lint rc=0, verify rc=0 165 passed,
    lint-docs rc=0, rule-sync rc=0); `762396bc`; the #1351 body is byte-identical to
    `docs/research/kb/reports/agents/pwf-migration-spec-v2-issue-body-final-2026-09-23.md`; audits
    `codex-call-audit-2026-09-23.md`, `codex-routing-gap-2026-09-23.md`,
    `codex-flag-decisions-history-2026-09-23.md`.
  - **Affected tickets:** #1351, #910 (absorbed), #1016, #1327 (after #1351).
  - **Disposition:** `DELIVERED` (spec published; stopgap committed on the branch, not shipped); `/to-tickets`
    on #1351 not started.
  - **Topology and ownership:** One writer, the Claude architect session. Delegates: Fable spec writers,
    codex-astra critics, three read-only Opus audits (codex calls, routing gap, flag history), and read-only
    session-integrity lanes M-Q.

  ### Current goal

  > <copy 032's Current goal paragraph verbatim; the digest is unchanged>

  ### Current workflow

  ```mermaid
  flowchart LR
      S["#1351 spec"] --> T["/to-tickets #1351"] --> I["/implement #1351 tickets"] --> K["/implement #1327"]
      K --> R["rest of Phase 11"] --> P10["Phase 10 step 0 (#1310)"]
      PL["pr-loop /to-spec (build after #1329/#1330)"] -.-> R
      CX["codex class-fix /to-spec (order unruled)"] -.-> R
  ```
  ```

### P4 — MEDIUM — the Phase 11 addendum keeps superseded rulings in place with no marker, and a top-down reader meets them first

- **Claim.** The addendum is a chronological log. Rulings reversed by later rounds read as current:
  - `:592` "Keep `autonomous` and the D4 deny (`f6ee355d`)". Reversed by round 4, `:626`.
  - `:617-620` round-2 Q1 "D4 stays as the upstream-sanctioned hardening". Reversed by round 4.
  - `:622` round 3 "`--force` operator-only". Reversed by round 4, `:634` ("re-derived") and by #1351 `:411`
    ("a clarifying question … rather than a permission").
  - `:604-605` "archive … to gitignored `.planning/archive/`". Contradicted by round 3, `:623-624`:
    "`.planning/.archive/`". The brief's binding list and #1351 both use the hidden `.archive`.
  - `:607-608` "Q4-Q6 (plan-init `--from`, sdlc_team scrub, plan-close operator-only) not yet asked". All three
    were answered in rounds 3-6.
  - `:594-598` "Research first … plan-doctor as a Claude FUNCTION hook and a codex hook". Rejected by #1351 Out
    of Scope (`:520-521`).
- **Evidence.** The quoted lines.
- **Control.** Round 4's text says "SUPERSEDES D4 … AND the round-2 … Q1 ruling". So the reversal is real and
  recorded, just not at the reversed lines.
- **Disposition: FIX-NOW.**

  (a) Insert as the first lines under the heading at `task_plan.md:586`:

  > **Read first — state of this addendum (2026-09-23 end of session):** the design of record is **spec #1351**.
  > Where a bullet below conflicts with #1351 or with a later round, the later one wins. Superseded in place:
  > - D4 / operator-only attestation (`:592`, round-2 Q1, round-3 `--force` operator-only) → round 4;
  > - `.planning/archive/` → `.planning/.archive/` (round 3);
  > - "Q4-Q6 not yet asked" → answered in rounds 3, 5 and 6;
  > - plan-doctor function/codex hook → rejected (#1351 Out of Scope);
  > - round 5's "032 changes the goal text" → round 6 (the plan-migration ticket appends that iteration).

  (b) Also append ` (SUPERSEDED — round 4)` to the ends of the round-2 Q1 and round-3 `--force` sentences, and
  change `:605` `.planning/archive/` to `.planning/.archive/ (round 3)`.

### P5 — MEDIUM — Phase 10's pwf ruling still prescribes what Phase 11 reversed, and #1351 says (falsely, today) that the supersession is recorded there

- **Claim.** Phase 10 is where work resumes after Phase 11, and its "**pwf:**" ruling (`task_plan.md:415-421`)
  still prescribes:
  - "`PWF_PLAN_ROOT` in `.claude/settings.json` `env`";
  - "`PLANNING_DISABLED=1` for `sdlc_team` (+ test)";
  - "lint forbidding `.planning/*/task_plan.md` / `.active_plan`";
  - "Design decisions WAIT for pwf deep extraction".

  None of these carries a SUPERSEDED marker. Its own header says "Rulings (final; superseded ones named)"
  (`:359`), so a reader trusts unmarked bullets as live.

  #1351 body `:385` says "the supersession is recorded in Phase 10's rulings block". That is present tense and
  false today. The supersession is recorded only in the Phase 11 addendum, round 6 (`:647-649`). A lane
  resuming Phase 10 would re-add the sdlc_team scrub that round 5 removed.
- **Control.** The Phase 10 block does use SUPERSEDED markers elsewhere (`:370`, `:389`), so their absence here
  is not a formatting convention.
- **Disposition: FIX-NOW.** Append to the bullet ending at `:421`:
  " **SUPERSEDED 2026-09-23** (Phase 11 addendum round 6; spec #1351): no `PWF_PLAN_ROOT` in tracked settings,
  no `PLANNING_DISABLED=1` for `sdlc_team` (lanes SEE the plan, round 5), no lint forbidding ticket plans or
  `.active_plan`, no deep-extraction hold. Still live: archive target `.planning/.archive/`."

  Once that lands, #1351 `:385` is true. Until then, post a one-line correction as an issue comment (see P9).

### P6 — MEDIUM — `ai-cli-invocation.md`, edited this session, contradicts itself and the code four ways

1. **`--ephemeral`.**
   - The rule: `:29` "Never `--ephemeral`, on ANY lane", while `:9` says "Prefer `mise run codex-lane` for
     repository orchestration".
   - The code: `codex_lane.py:383` passes `"--ephemeral"`, with a justification docstring at `:364-366`.
   - The only record that this is known and owed is `task_plan.md:661` (class fix: "`codex_lane.py`
     `--ephemeral`").

   A lane obeying the rule would either distrust the preferred task or "fix" it outside a spec.
2. **`-s`.**
   - The rule: `:35` "Implementation lanes pass no `-s`".
   - The code: the implementer wrappers pass `--sandbox danger-full-access` (`codex-sol-implementer.md:168`,
     astra `:170`), as do the operators (`codex-sol-operator.md:67`). The advisory wrappers and the rule's own
     research block pass read-only (`:16`), while sdlc-team `review` passes nothing.

   The rule gives no principle for which lane gets which. (History: the 09-15 "stop overriding" ruling
   targeted `sdlc_team`, per `codex-flag-decisions-history-2026-09-23.md:110`.)
3. **Hand-kept argv.**
   - The rule: `:38` "This is the only hand-kept argv block. Agent definitions … point here".
   - The code: all 12 codex wrappers carry full hand-kept argv blocks.
4. **Version heading.**
   - The rule: `:42` "## Codex facts at 0.152.1".
   - Installed: `codex-cli 0.154.0` (probe above). `task_plan.md:713` records the bump. Brief Q owns the version
     itself; this finding is about the stale heading in a file this session edited.

- **Control.** `grep -c -- '--ephemeral' .claude/rules/ai-cli-invocation.md` = 1 (the ban line), and the same
  shape finds `codex_lane.py:383`. So the ban-vs-code split is real, not a probe miss.
- **Disposition: FIX-NOW.** Rule-text rewrites (the sandbox *policy* question is Q1 below):
  - Replace `:9-10` with: "Use `mise run sdlc-team` for routed codex review/implementation. `mise run codex-lane`
    (the DAG review lane) still passes `--ephemeral` (`codex_lane.py:383`) pending the Phase 11 codex-invocation
    class fix — do not copy its argv. Use the direct forms below only when the task genuinely needs a raw CLI
    call."
  - Replace the sentence at `:34-36` ("Implementation lanes pass no `-s` … (#1039, #1142).") with:
    "Sandbox by lane: `mise run sdlc-team` passes no `-s` in either mode (Ray 2026-09-15; `workspace-write` also
    cuts the network, #1039/#1142); the implementer and operator wrappers pin `--sandbox danger-full-access`;
    advisory wrappers and the research block pin `-s read-only`."
  - Replace `:38-40` with: "This is the canonical hand-kept argv block. The 12 `.claude/agents/codex-*` wrappers
    still carry their own blocks until the Phase 11 codex-launcher class fix replaces them; when you change a
    flag here, change them in the same diff (sol files, then `mise run codex-lane-mirror`)."
  - `:42`: "## Codex facts (re-probed at 0.152.1; installed 0.154.0 — re-probe before relying)". Better: re-run
    the probes and restamp.

### P7 — MEDIUM — the pr-loop spec prescribes the one CI-wait shape three repo surfaces forbid

- **Claim.** `docs/specs/pr-loop-ship-fix-land.md:64` says "Wait for a terminal PR state with
  `gh pr checks <n> --watch` (per `gh-cli-watch.md`), bounded". Three surfaces forbid it:
  - `pr.py:23-33`, the module the loop reuses: "no `gh run watch`/`--watch` … ship enables GitHub-native
    auto-merge … and returns", because base-image builds take hours;
  - `hook_guard.py:566-570` denies `gh pr checks … --watch`;
  - `mise-tasks-only.md`'s table redirects `gh pr checks … --watch` to "`ship`/`land` … one-shot read:
    `gh pr checks <n> --json`".

  `gh-cli-watch.md` is the older, generic rule. The `/to-spec` author would inherit a contradiction.
- **Control.** `hook_guard.py:567` regex `gh\s+pr\s+checks\b[^;&|\n]*--watch\b` matches the spec's literal
  command shape.
- **Disposition: FIX-NOW** (draft spec, not yet a ticket). Replace step 2 (`:64-65`) with:
  "2. Read PR state one-shot, never watch: `gh pr checks <n> --json name,bucket,link` + `gh pr view <n> --json
  state,headRefOid,mergeCommit` (`mise-tasks-only.md`; `hook_guard` denies `gh pr checks --watch`; `pr.py:23-33`
  rejects any client-side watch). Any required check `fail` → `CHECKS_FAILED`; MERGED with `headRefOid` = the
  shipped SHA → step 3; otherwise → `MERGE_PENDING` at once."

  Keep the open question at `:121`, reworded: "Whether a bounded wait (via `mise run bounded-wait`) precedes
  `MERGE_PENDING`, or it always returns immediately."

### P8 — MEDIUM — pr-loop re-entry and round counting are undefined for non-failure stops

- **Claim.** `:67-69`: every re-invocation "re-enters at step 1" (`ship`). The skill says `MERGE_PENDING` means
  "re-run later". Re-running then re-ships a branch with no new commits. That either re-pays every gate or hits
  `PREFLIGHT_REFUSED` "no diff" (`:49`). Separately, "Max 2 fix rounds per loop … state file keyed by branch" does
  not say when the counter resets.
- **Evidence.** `:49`, `:50`, `:67-69`, `:100`.
- **Control.** N/A (a textual gap). The two readings named above both follow from the text.
- **Disposition: FIX-NOW.** Replace `:67-69` with:
  "4. Re-entry. `pr-loop` first reads the branch's PR state:
  - an OPEN PR with no local commits past the shipped head → resume at step 2;
  - MERGED → step 3;
  - new local commits after `GATE_FAILED`/`CHECKS_FAILED` → step 1, which is a fix round.

  At most **2** fix rounds. The counter lives in `.agent/state/pr-loop/<branch>.json`, increments only on a
  step-1 re-entry that follows a failure, and is deleted on `LANDED`. Round 3 → `ROUND_LIMIT`."

  Then drop the state-file open question at `:120`.

### P9 — MEDIUM — #1351 carries stale conditional wording and undefined terms, and says nothing about the 12 codex wrappers

- **Stale conditionals.**
  - `:409-410` "kept identical by the mechanism Ray selects in question 3";
  - `:536` "must not start before … question 1 is answered".

  Both questions are ruled (`:549` "all ruled by Ray on 2026-09-23 as recommended").
- **Undefined terms.** The spec is path-free by `/to-spec` convention, so a codex implementer must guess the
  referents of:
  - "the advisory codex lane";
  - "the worker dispatcher" and "Both spawn sites";
  - "the wrapper task and the CLI beneath it";
  - "the initializer", "attester", "selector script", "ledger appender" and "completion check";
  - "the root mode file", "the shared package" and "the hidden archive directory";
  - "the ticket-creation skill" and "the close skill".

  The referents exist only in the tracked draft `pwf-migration-spec-v2-2026-09-23.md`, e.g. `:40` and `:494`
  (`sdlc_team.py:805-818`/`:961-968`, `codex_lane`).
- **Scope gap.** "Worker lanes see the plan" (`:372`, user story 38) is defined over `sdlc_team`'s spawn sites
  only. The 12 `.claude/agents/codex-{sol,astra}-*` wrappers still export `PLANNING_DISABLED=1` and call it
  "load-bearing" (e.g. `codex-sol-implementer.md` "**`PLANNING_DISABLED=1` is load-bearing.**"). The stopgap
  re-affirmed this. They are absent from #1351's consumer inventory (`:391-395`) and Out of Scope (`:514-527`).
  A #1351 implementer will either leave the scrub or "fix" it, with nothing to decide by.
- **Control.** The draft does define the spawn sites (`:40`) and `codex_lane` (`:494`). It never mentions
  `codex-sol`: `grep` = 0 hits, and the same grep finds `PLANNING_DISABLED` at `:40`, `:79` and `:491`.
- **Disposition: FIX-NOW**, as an issue comment. An append leaves the reviewed body intact. If the body is edited
  instead, assert `count(anchor)==1` first, per memory `feedback_issue_body_edit_needs_anchor_assert`. Comment
  text:

  > **Clarifications (session-integrity review, 2026-09-23):**
  > (1) Questions 1 and 3 are ruled (see "Design questions"). Read `:409-410` as "kept identical by the
  > byte-parity gate (question 3)", and `:536` as "must not start before the migration ticket lands".
  > (2) Phase 10's rulings block is updated to record the step-5 supersession by the coordinator (task_plan);
  > `:385` describes that record.
  > (3) Glossary, for implementers:
  > - advisory codex lane = `mise run codex-lane` (`python/src/dotfiles_setup/codex_lane.py`);
  > - worker dispatcher / both spawn sites = `sdlc_team.dispatch` and its supervisor (`sdlc_team.py`, the two
  >   `Popen` calls);
  > - wrapper task / CLI beneath = `mise run plan-attest` / `dotfiles-setup plan-attest`;
  > - initializer / attester / selector / ledger appender / completion check = pwf `init-session.sh` /
  >   `attest-plan.sh` / `set-active-plan.sh` / `ledger-append.sh` / `check-complete.sh`, under the installed
  >   plugin root;
  > - shared package = knowledge-base `kb_setup` (`kb_setup.pwf`, `kb-setup plan …`);
  > - hidden archive = `.planning/.archive/`;
  > - root mode file = the tracked root pwf mode file (`.mode`, currently `autonomous inject-smart`) — verify
  >   the exact filename against the installed 3.20.7 before implementing.
  >
  > (4) Out of scope: the 12 `.claude/agents/codex-{sol,astra}-*` wrapper lanes keep `PLANNING_DISABLED=1` until
  > the Phase 11 codex-launcher class fix replaces them — pending Ray's answer to Q2 of the vagueness audit.

  The mode-file name is UNVERIFIED by me. Brief text (`session-2026-09-23d-agent-briefs.md:12`) says
  "`.mode` = `autonomous inject-smart`". Confirm against the plugin before posting.

### P10 — LOW — the session handoff file predates the session's last two commits and misdescribes the branch

- **Claim.** `.agent/plans/session-2026-09-23d.md` has mtime 21:28, before `3f2caac6` (22:28) and `762396bc`
  (22:34). Its stale lines:
  - `:4-5` names plan sha `56d221f6…`; the file and the pointer are now `ea2b350e…`;
  - `:13` describes the branch as two commits;
  - `:23` says "(no code)", but `3f2caac6` changes `sdlc_team.py` and tests;
  - `:23-24` names round 3 as "Design of record"; it is now #1351;
  - `:29` says "A-F", but briefs now run A-Q.

  It does not list #1351, the stopgap, or the codex audits.
- **Control.** For `:44` ("No rule or skill points to these yet"), the citation probe returned rc=1 for the pwf
  reports, while the codex-call-audit is found in 10 files. So `:44` is still TRUE, and it is not flagged.
- **Disposition: FIX-NOW** (coordinator; the next `/session-handoff` regenerates this file anyway).
  - `:4-5` sha → `ea2b350e223fdffa3215ab7f3d09af7262f236ebfcc596aad060a6ddf6395f50`.
  - `:13` → "`docs/session-2026-09-23d-handoff`: `875dfe26`, `7feb4a29`, `b5af8ecf`, `3f2caac6` (codex stopgap:
    code + tests + 12 agent defs + 2 rules), `762396bc` (#1351 published). Not shipped; run `mise run ship` when
    Ray asks."
  - `:23-24` → "#1350 landed. pwf migration: research + design + spec **#1351** (design of record; supersedes the
    round-3 report). Codex-wrapper stopgap `3f2caac6`."
  - `:29` → "(A-Q; …)".
  - Add row: "codex audits I/J/K → `codex-call-audit-…`, `codex-routing-gap-…`, `codex-flag-decisions-history-…`
    → stopgap `3f2caac6` + class-fix bullet".

### P11 — LOW — the wrapper text's "43% … on this definition's old haiku wrapper" is an aggregate statistic presented per file

- **Claim.** The sentence is pasted into all 10 wrappers (e.g. `codex-sol-advisor.md:120`). The figure is
  aggregate: "23 haiku codex wrappers → >=10 (43%)" (commit `3f2caac6` body). Read per file, it overstates or
  understates each definition's own record.
- **Disposition: FIX-NOW** (sol files + mirror). Replace with: "≥10 of 23 (43%) haiku-wrapped codex lanes across
  these definitions never delivered codex's answer".

### P12 — LOW — sibling wrappers disagree on the harness backgrounding threshold and the default budget, and neither states why

- **Claim.**
  - Threshold: the sonnet wrappers (`codex-sol-advisor.md:114`) say "the harness moves a foreground call to the
    background at 120 s". The implementer (`codex-sol-implementer.md:160`) says "caps a foreground Bash call at
    600 s". Truth (`$CC/env-vars.md:185,187`): default 120000 ms, model-settable up to 600000 ms, and there is
    no project override. Each wrapper states half of it.
  - Budget: default 2400 s in the 10 wrappers vs 1800 s in the implementer (`:152`), with no stated reason.
    Commit `3f2caac6` says "default budget 2400 s", as if uniform.
- **Disposition: FIX-NOW.**
  - In both texts: "a foreground Bash call is backgrounded at its `timeout` (default 120 s; settable up to
    600 s — `$CC/env-vars.md:185-187`)".
  - Either align the implementer to 2400 or add after its `TIMEOUT=1800`:
    `# shorter than the advisory 2400 s: #1154's measured implementer runs` (only if that is the measured reason;
    otherwise align).

### P13 — LOW — three different line counts for the same plan

- **Claim.** The counts disagree:
  - #1351 `:7`: "1,647-line";
  - `task_plan.md:588`: "1,600-line";
  - `task_plan.md:604`: "1,640-line";
  - `wc -l task_plan.md`: 1710.

  Harmless alone, but the migration's archive outcome is "byte-for-byte". A reader checking completeness by line
  count gets three wrong baselines.
- **Disposition: FIX-NOW.** Use "the ~1,700-line root plan (1,710 at 2026-09-23 22:34)" in `task_plan.md:588`
  and `:604`. #1351 is fine as written: it was measured at authoring time.

### P14 — LOW — the pr-loop spec overloads one status and leaves one path undefined

- **Overload.** `:75` routes the "branch closed — new branch + cherry-pick" case to "`CONFLICT`-class" guidance,
  but `CONFLICT` is defined at `:51` as "branch conflicts with main".
- **Undefined path.** `CHECKS_FAILED`'s "run-log path" (`:48`, `:65`) names a GHA log, which is not a local file.
- **Disposition: FIX-NOW.**
  - Add a row after `:51`: "| `BRANCH_CLOSED` | a change is needed while checks are green/pending after arming
    (#544 race) | stop: new branch + cherry-pick, re-run |". In `:75`, replace "`CONFLICT`-class" with
    "`BRANCH_CLOSED`". In the skill draft (`:101`), add `BRANCH_CLOSED` to the stop-and-ask list.
  - In `:56`, add: "for `CHECKS_FAILED`, `log_path` is a local file the loop writes from
    `gh run view <run-id> --log-failed`".

## Checked and clean (no finding)

- The #1351 body is byte-identical to the tracked final file (arms above).
- The `.claude/skills/codex-sdlc-team/SKILL.md` and `.agents/skills/codex-sdlc-team/SKILL.md` diffs are identical.
  Both now say `review` is "asked (not prevented)", which is consistent with `sdlc_team.py:747-757` and
  `codex-sdlc-team.md:28-30,48-50`.
- The operator-only attestation wording in `.claude/CLAUDE.md:20`, `mise-tasks-only.md:31` and `mise.toml:997` is
  still TRUE of enforcement (D4 is live until #1351's first ticket). #1351 user story 37 and "Retired outright"
  (`:228-235`) schedule its removal. The handoff trap (`session-2026-09-23d.md:57-58`) warns of the gap. No new
  finding.
- `mise run reap -- --pattern "$OUT" --kill`, cited by the wait protocol, matches the real CLI:
  - `mise.toml:1668-1670` examples;
  - `reap.py` regex patterns;
  - `DEFAULT_MIN_AGE_S = 300` at `reap.py:85`, which is below the 2400 s budget, so a timed-out lane is old
    enough to reap.

## Questions for Ray

1. **Sandbox posture for the 12 codex wrappers (P6-2).** The 2026-09-15 "stop overriding the machine sandbox"
   ruling was applied to `sdlc_team` only.
   - *(Recommended)* **Keep the explicit pins and fix the rule text.** PRO: read-only is the only thing stopping
     an advisory/critic lane from writing, and the pin survives a changed `~/.codex/config.toml`. CON: this
     leaves two sandbox postures to explain (`codex-flag-decisions-history-2026-09-23.md:108-110`).
   - **Drop `--sandbox` from all 12 wrappers.** PRO: one rule, "no `-s` anywhere". CON: advisory lanes can write,
     and only the prompt forbids it (`codex-sdlc-team.md:48-50`).
2. **Do the codex wrapper lanes see the plan after #1351 (P9-4)?**
   - *(Recommended)* **Keep their `PLANNING_DISABLED=1` until the codex-launcher class fix retires the wrappers,
     and say so in #1351.** PRO: no behaviour change inside an unrelated spec. CON: the implementer lane stays
     plan-blind for a while, which round 5 wanted to end for sdlc_team (`task_plan.md:636`).
   - **Extend round 5 to the wrappers inside #1351.** PRO: one rule for all worker lanes. CON: this widens a
     spec Ray already ruled, touching 12 more files [no prior evidence of a ruling on the wrappers].
3. **Order after `/to-tickets` #1351 (P2).** The candidates are pr-loop `/to-spec`, the codex class-fix
   `/to-spec`, and the native codex installer (Brief Q).
   - *(Recommended)* **Native installer first.** Ray, 2026-09-23: "needs to happen asap". Then the class fix, then
     pr-loop, whose build is gated on #1329/#1330 anyway. CON: this delays pr-loop's spec, which has no build
     dependency on the others (`task_plan.md:652-657`).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): the #1351 body via
  `gh issue view 1351 -R ray-manaloto/dotfiles`, plus local source, rules, agents and specs.
- [anthropics/claude-code docs, offline copy](https://github.com/anthropics/claude-code): `$CC/env-vars.md:185,187`
  for Bash timeout defaults, read from the knowledge-base offline corpus.
