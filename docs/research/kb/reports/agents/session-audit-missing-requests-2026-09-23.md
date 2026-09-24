# Session audit — missing requests (Brief N), session `a6750a24`, 2026-09-23d

Status: COMPLETE. Brief: `docs/research/kb/reports/agents/session-2026-09-23d-agent-briefs.md` § "Session-integrity
review" + "Brief N". Read-only lane: the only repo file written is this report. I did NOT append to `findings.md` or
`progress.md`, because the brief's "read-only except each brief's report file" is stricter than the SubagentStart
contract. The coordinator should persist the condensed findings.

## Method

- Main transcript: `~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/a6750a24-770a-419d-996e-985bd27de611.jsonl`
  (2,205 JSONL lines, read at 22:44 CDT). Ordinals below are **JSONL line numbers** (`L<n>`).
- Extracted: every `type=user` record with string content that is not `isMeta` and not a `<task-notification>`;
  every `AskUserQuestion` tool_use with its tool_result; every `attachment` of type `queued_command` with
  `commandMode=prompt` (text typed while the agent was busy); every assistant `SendUserMessage` (to see what was
  promised back).
- **Control arms on the extraction:** 25 `user:str` records = 12 human + 13 task-notifications (counted two ways,
  the sum matches); 7 `queued_command` attachments = 6 `task-notification` + 1 `prompt` (L1506, which appears NOWHERE
  as a `user:str` record, so a user-record-only extraction would have missed it); 15 ASK / 15 ANSWER pairs, all
  paired by `tool_use_id`. No tool_result carried a user rejection.
- Landing places checked: `task_plan.md` (1,710 lines, mtime 22:34), `docs/agents/goal-history.md` (iterations
  031/032), commits `219e83cc..HEAD` (5 commits), GitHub issues (via `gh issue view`/`gh api /search/issues`),
  `.agent/plans/session-2026-09-23{c,d}.md`, `.claude/skills/session-handoff/SKILL.md`, auto-memory.
- Every negative grep below had a positive control in the same corpus with the same command shape; each is stated.

## 1. Every user message and answer, mapped

Status legend: MAPPED (landing place cited) · PARTIAL · UNMAPPED · IN-FLIGHT (the session is still acting on it).

| # | Ordinal | Verbatim (Ray) | Request / ruling | Landing place | Status |
|---|---|---|---|---|---|
| 1 | L19/L22/L32/L36 | `/reload-skills`, `/reload-plugins --force`, `/plugin`, `/session-resume` | housekeeping + resume | resume report L115 | MAPPED (no request) |
| 2 | L132 | "run land -- 1350 / wait for that to finish and fix any issues from that / and then run /session-handoff and we will work on /mattpocock-skills:implement #1327 on the next session after /clear" | land #1350; fix; handoff; next = /implement #1327 | land RC=0 (L161, 23d handoff table); handoff commit `875dfe26`; `task_plan.md:678` (#1327 now AFTER the pwf migration, per Ray's later L523 "make it the priority") | MAPPED |
| 3 | L187 (to L186) | "Edit plan + I re-attest (Recommended)" | record /implement #1327 as next; Ray re-attests | `task_plan.md:672-680`; attest owed (23d handoff "Owed") | MAPPED (attest still owed — see F4) |
| 4 | L302 | "can you research why i have to run '! mise run plan-attest' / doesnt pwf have a native way to automate this … only stopping when needing human approval … is this project not setup properly w pwf? / run /agentsview-finding-history and other agentsview features to find research we've done on this already as i keep asking about this and nothing is being done about it" | research + history | `plan-attest-history-2026-09-23.md`; `task_plan.md:599-601`; goal-history 032 Evidence | MAPPED |
| 5 | L459 (to L451) | "what is the native best practices pwf proposes that involves the least amount of changes we need to make so that we dont drift too far from pwf newer releases?" | least-drift principle | `task_plan.md:611-612` (round 2 PRINCIPLE) | MAPPED |
| 6 | L488 | "are we on the legacy workflow for pwf? / we want to follow their most up to date workflow" | migrate to current workflow | `task_plan.md:586-593` | MAPPED |
| 7 | L523 (to L522) | "option 1 and make it the priority" | Add to Phase 11, FIRST priority; option text also said "…and answer #910 with this finding" | `task_plan.md:586` heading; #910 answer: **not done** | PARTIAL → **F6** |
| 8 | L523 | "we should add running /planning-with-files:plan-doctor as a claude function hook and codex hook at the beginning of their sessions or specific turns (research and provide cited proposals w pros/cons)" | plan-doctor hook research | `pwf-plan-doctor-hooks-2026-09-23.md`; recommendation-against presented L701; #1351:366 and :520-521 put both hooks OUT OF SCOPE; `task_plan.md:594-595` still records it only as "research first" — no ruling | PARTIAL → **F8** |
| 9 | L523 | "research these and other /planning-with-files plugin skills … plan-loop … plan-goal" | skills inventory | `pwf-skills-inventory-2026-09-23.md`; #1351 mentions both once | MAPPED |
| 10 | L523 | "have a fable agent synthesize and provide a proposal … especially these: /session-handoff /session-resume" | Fable synthesis incl. skill updates | Fable reports (synthesis/revision/round 3); #1351 (26 "handoff", 12 "resume" hits) | MAPPED |
| 11 | L753 (to L745) | Q1: "have a codex astra agent review the findings of the research and fable adviser's proposal to make sure nothing was missed"; Q2 "Root task_plan.md (Recommended)"; Q3 "Ignored archive + tracked extract (Recommended)" | astra review; root roadmap; archive + extract | `pwf-migration-codex-astra-verdict-2026-09-23.md`; `task_plan.md:602-608`; #1351 "tracked extract" ×3 | MAPPED |
| 12 | L888 (to L887) | Q1: "i still dont understand / are we deviating from how modern best practices for pwf should be setup? / assume what we are doing is wrong and follow that so we can get updates to pwf easier w minimal changes / if necessary we can refactor our existing .planning and task plans to the modern setup" | principle; refactor allowed | `task_plan.md:611-612`; #1351 story 9 + T8 (leftover 2026-09-21 dir, #1351:25,:94,:419) | MAPPED |
| 13 | L888 | Q2: "PLAN_ID per worktree"; Q3: "Fable revision, then /to-spec (Recommended)" | binding; next step | `task_plan.md:613,616`; #1351 "plan id" ×11 | MAPPED |
| 14 | L888 | Q4: "kb and dotfiles should follow the exact same workflow / so we need to review each and merge them to one workflow that supports both / we can add flags and/or skill/mise task/python library module(s)/function(s) arguments/parameters … but maintaing 2 of these will be hard" | one merged KB+dotfiles workflow | `task_plan.md:614-615`; #1351 (KB ×25) | MAPPED |
| 15 | L921 (to L913) | "Upstream + its hardening (Recommended)" | trust posture | `task_plan.md:617-620`; SUPERSEDED by #19 | MAPPED (superseded) |
| 16 | L996 (to L988) | Q1: "are you sure we understand this? / did we research and review pwf github repo issues/prs/discussions to make sure if this has been addressed and/or tracked?" | upstream tracker research | `pwf-upstream-tracker-review-2026-09-23.md` (covers discussion #218); `task_plan.md:624-625` | MAPPED |
| 17 | L996 | Q2 "Agent if complete (Recommended)"; Q3 "kb_setup now (Recommended)"; Q4 ".planning/.archive/ (Recommended)" | plan-close; shared code; archive dir | `task_plan.md:621-624` | MAPPED |
| 18 | L1051 (to L1043) | "Adopt upstream's trust model" | supersede D4; NOT the "File upstream + local stopgap" option | `task_plan.md:626-635`; goal-history 032 | MAPPED — but see **F9** (spec says upstream asks are "filed") |
| 19 | L1071 (to L1063) | Q1: "option 2 / we should only have sdlc_team correct after we retire fable-orchestrator and other plugins that are later in the task plan?" | lanes see plan + a sequencing question | `task_plan.md:636-641`; answered by round 3 (T6 minimal now, rest Phase 10), `task_plan.md:647-649` | MAPPED |
| 20 | L1071 | Q2: "Yes, update goal text (Recommended)" — option text: change "task_plan.md is the sole task authority" to "the root roadmap plus the active ticket plan are task authority" | goal-history 032 goal text changes | `task_plan.md:639` records it; `:650-651` later DEFERS it to T8; goal-history 032's goal text still ends "Keep task_plan.md as the sole task authority." | PARTIAL → **F2** |
| 21 | L1071 | Q3: "Archive via plan-close (Recommended)"; Q4: "Fable round 3 first" | KB 11-day slug; Fable round 3 | `task_plan.md:640-641`; #1351 (round-dag/live slug ×12); round-3 report | MAPPED |
| 22 | L1136 (to L1135) | Q1 "Leave until Phase 10 (Recommended)"; Q2 "option 1 / make sure we follow the modular/re-usable claude/codex skill(s) -> mise task(s) -> python library module(s)/function(s) protocol whenever possible / so that we can have wrapper skill(s) call other skill(s) …"; Q3 "At the dispatch call (Recommended)" | codex_lane; thin plan-init + layering; dispatch check | `task_plan.md:643-647`; #1351:373-380 | MAPPED |
| 23 | L1230 | `/skill-creator:skill-creator` "to write a modular reusable skill that is a wrapper skill that calls the ship and land skills / we really want to run ship and then fix any issues and then run land as one loop / with minimal agent work/tokens/context being used / and follow the requirements of: use code generation tools for model/enums/types; code generated return/error enum codes; universal logger; follow the modular/re-usable skill(s) -> mise task(s) -> python library module(s)/function(s) reusing code as much as possible" | pr-loop | `docs/specs/pr-loop-ship-fix-land.md` (`b5af8ecf`; codegen/enum/logger/exit-code/layering all present); `task_plan.md:652-657` | MAPPED (no tracker issue yet; waits for Fable /to-spec) |
| 24 | L1272 (to L1271) | "Phase 11 ticket after #1329/#1330 (Recommended)"; "Local + CI failures"; "option 1 and the next set of changes committed to be shipped/landed" | pr-loop sequencing, scope, testing | `task_plan.md:653-656` | MAPPED |
| 25 | L1361 | `/mattpocock-skills:to-spec` "but use a fable model for it and the same for /to-tickets after that" | Fable for to-spec and to-tickets | #1351 Fable v2 (`task_plan.md:665`); to-tickets NEXT (`:669-670`) | MAPPED (to-tickets pending; model-invocation disabled, Ray types it — L2207) |
| 26 | L1393 (to L1385) | "option 1 / but only if a fable model was used for /to-spec"; "option 1 / and then we run /to-spec and /to-tickets on a fable model afterwards on pr-loop" | seams; pr-loop separate spec | `task_plan.md:665,670` | MAPPED |
| 27 | L1445 (to L1444) | "have a codex astra model agent review this" | astra review of spec draft | `pwf-migration-spec-codex-astra-verdict-2026-09-23.md`; `task_plan.md:665` | MAPPED |
| 28 | L1506 (queued) | "i think using haiku to trigger codex is causing issues / have agents review all the codex calls we ran and what were the repeated issues/problems that we can improve on and prevent the mistakes/issues from happening again? / dont we already have skill(s) for this? why are we not using them?" | codex call audit + routing gap | `codex-call-audit-2026-09-23.md`, `codex-routing-gap-2026-09-23.md`; `task_plan.md:658-664` | MAPPED |
| 29 | L1613 | "review history and use /agentsview-finding-history we should have removed --ephemeral and added/removed other flags when running codex cli" | flag history | `codex-flag-decisions-history-2026-09-23.md`; `3f2caac6` (drops `--ephemeral` ×12 wrappers, `-s` in sdlc_team); rest `task_plan.md:661-663` | MAPPED |
| 30 | L1846 (to L1845) | "Stopgap now, rest as Phase 11 (Recommended)" | stopgap + Phase 11 class fix | `3f2caac6`; `task_plan.md:658-664` — but absent from Current Phase and from the NEXT line | PARTIAL → **F5** |
| 31 | L2086 (to L2085) | "Main clone only (Recommended)"; "Delete in the cutover (Recommended)"; "Accept all three (Recommended)" | spec v2 Q1-Q5 | `task_plan.md:665-669`; #1351 | MAPPED |
| 32 | L2157 | "have agents review this session and ensure the following: we did not dismiss any errors/repeated mistakes … zero missing requests/issues in the task plan … zero bugs … zero vague documentation/plans…" | Briefs M-Q | briefs file § M-Q; this report | IN-FLIGHT |
| 33 | L2157 | "this should be added (if it doesn't already) into /session-handoff" | handoff gains the four integrity checks | NOT in `session-handoff/SKILL.md`; NOT in `task_plan.md` | UNMAPPED → **F3** |
| 34 | L2157 | "wait for the above to complete and fix any issues related to them and then have a fable model run /to-tickets" | order: fix, then Fable /to-tickets | `task_plan.md:669-670` (to-tickets only; the "fix first" gate is not written) | PARTIAL (folded into F5's rewrite) |
| 35 | L2157 | "the work and task plan items for migrating to the native codex installer needs to happen asap as we are running codex on an old version / - review old session history and task plan on this" | promote codex-native | still Phase 10 step 2, "QUEUED behind Phase 11" (`task_plan.md:349,492,679-680`) | UNMAPPED → **F1** |
| 36 | L2157 | "provide a prompt when to run \"! mise run plan-attest\" / - should be done when there are no longer any background tasks/agents/codex lanes/etc running so it on the latest data" | attest prompt, conditioned on quiescence | promised at L2163 ("The attest prompt comes last, once nothing is running"); not persisted in plan or handoff | IN-FLIGHT → **F4** |

Earlier-handoff owed items:

| Source | Owed item | Landing place | Status |
|---|---|---|---|
| 23c "Owed" | `mise run land -- 1350` | L161 RC=0 | MAPPED |
| 23c/23d "Owed" | Operator `/hooks` trust for #1334/#1336 codex additions | handoffs only; #1334/#1336 bodies have no `/hooks` (control: #1302 body matches the same regex) | UNMAPPED → **F11** |
| 23c/23d "Owed" | #1302 trust-hash probe | #1302 itself (OPEN) | MAPPED |
| 23c/23d state | Harness worktrees `agent-a6e5728e…`/`agent-a82a7019…` safe to remove | handoffs only | UNMAPPED (LOW) → **F13** |
| 23d "Owed" | `! mise run plan-attest` before `/clear` | handoff; conditions updated by #36 | IN-FLIGHT → F4 |
| 23d "Owed" | Startup doctor drift "not triaged": graphify PATH 0.9.67 vs lock 0.9.65; claude-code 2.1.278 vs 2.1.281; listing budget 48,608 > 48,110 | graphify → #1344 (OPEN, not referenced in `task_plan.md`); the other two: nowhere | PARTIAL → **F12** |
| 23d "Owed" | Recover `aaeea08e` (2026-09-02 D4 reports) or record as dropped | not recovered; not in `task_plan.md` | UNMAPPED → **F7** |

## 2. Findings (unmapped or partially mapped only)

### F1 — HIGH — The "native codex installer ASAP" request is not in the plan; it is still queued two phases back

- **Claim:** Ray (L2157): "migrating to the native codex installer needs to happen asap as we are running codex on
  an old version". `task_plan.md` still places it at Phase 10 step 2 (`:492`), under the heading "Phase 10 — QUEUED
  behind Phase 11" (`:349`), and Current Phase says Phase 10 resumes only after Phase 11 (`:679-680`). Codex is
  0.154.0 on both the bare and the mise route (coordinator probe, L2207).
- **Conflict to name:** Phase 10's own ruling says fable-orchestrator removal runs "FIRST — before any step that
  would trigger codex work or agents" (`task_plan.md:431-432`, order item 0 at `:489`), and step 2 bundles
  codex-native with the `gpt-6-sol` model move and a BASE REBUILD (`:492`). "ASAP" collides with both.
- **Control arm:** `grep -c 'native installer' task_plan.md` → 7 (the probe finds the term); every hit is in Phase
  4/10 context (`:804,:938,:1010,:1046,:1095,:1130-1131`), none in Phase 11 or Current Phase.
- **Disposition:** PLAN + a Ray question (Questions §Q1). Brief Q owns the smallest safe path. Proposed plan text
  once Ray rules, appended to the Phase 11 addendum:
  > - **Codex native installer PROMOTED (Ray, 2026-09-23: "needs to happen asap as we are running codex on an old
  >   version").** Codex is 0.154.0 (bare and `mise exec`). Phase 10 step 2's codex-native half moves ahead of the
  >   remaining Phase 11 work, as scoped by `codex-native-installer-status-2026-09-23.md`; the `gpt-6-sol` model move
  >   and the base-rebuild half stay at Phase 10 step 2 unless that report shows they cannot split. Conflict with
  >   Phase 10 order item 0 ("fable-orchestrator removal first") ruled by Ray: <answer>. Route: `/to-spec` (Fable) →
  >   `/to-tickets` → `/implement`.
  Needs `/grilling` only if Brief Q shows the split is not clean.

### F2 — HIGH — Ray's "Yes, update goal text" for goal-history 032 was deferred without asking him

- **Claim:** At L1063 Q2 the option Ray took (L1071) read: "Change 'task_plan.md is the sole task authority' to 'the
  root roadmap plus the active ticket plan are task authority'." `task_plan.md:639` records "Goal-history 032
  CHANGES the goal text". Then round 6 (`task_plan.md:650-651`) says 032 records only the re-ordering and trust
  model, and "the plan migration (T8) appends its own later iteration with the changed goal text". The L1135 round
  asked three other questions; no AskUserQuestion covered this deferral. Goal-history 032's Current goal still ends
  "Keep task_plan.md as the sole task authority." (`docs/agents/goal-history.md`, iteration
  `dotfiles-goal-20260923-032`).
- **Control arm:** the same 032 goal text DOES contain the new layout's words ("a short root roadmap plus one
  attested ticket plan per /implement ticket"), so the probe reads the right iteration. Only the authority sentence
  is unchanged.
- **Why the deferral may be right:** until T8 runs, only the root plan exists, so "root + active ticket plan are
  task authority" would be false today. That is a reason to ask Ray, not to decide for him.
- **Disposition:** Questions §Q2. If Ray keeps his original answer, append iteration 033 (goal-history is
  append-only; 032 cannot be edited) with the authority sentence changed. If he accepts the deferral, replace
  `task_plan.md:639`'s "Goal-history 032 CHANGES the goal text …" with:
  > Goal-history: the authority sentence changes in T8's iteration, not 032 (Ray, <date>: accepted the deferral
  > because no ticket plan exists before T8).

### F3 — HIGH — "Add these checks to /session-handoff" landed nowhere

- **Claim:** Ray (L2157): "this should be added (if it doesn't already) into /session-handoff". The skill has an
  AgentsView pass (`.claude/skills/session-handoff/SKILL.md:121-136`: unbounded waits, AskUserQuestion count, handoff
  position, report writes) but no step for dismissed errors, request→plan mapping, cold bug review or vagueness.
  `task_plan.md` has 0 hits for `integrity`. The coordinator promised it (L2163: "I'll … add the checks to
  `/session-handoff`").
- **Control arm:** `grep -n -i 'integrity' SKILL.md` → line 121, so the probe reads the right file; the same grep
  for `dismiss|missing request|vague|zero bugs` → 0 hits.
- **Disposition:** PLAN (skill text is Phase 11 territory: #1342 owns the handoff verification gate and the
  `writing-for-agents` skill is required for skill edits, `task_plan.md:484`). Addendum text:
  > - **`/session-handoff` gains a session-integrity review (Ray, 2026-09-23, L2157).** Before drafting the handoff,
  >   run four read-only lanes over the session transcript and its subagents: (M) every non-zero rc, error, WARN,
  >   deny and repeated mistake → fixed (cite) or planned (cite) — no dismissals; (N) every user message and
  >   AskUserQuestion answer → its landing place (plan line, issue, commit) — no unmapped requests; (O) a cold,
  >   cross-family review of the session's diff by ref; (P) every changed doc/plan/spec read cold for ambiguity,
  >   contradiction and stale statements. Each finding gets FIX-NOW or PLAN; the handoff is not written while any
  >   finding lacks a disposition. Briefs of record: `session-2026-09-23d-agent-briefs.md` § M-Q. Carried by #1342
  >   (comment it there); edit the skill with `writing-for-agents`.
  Also comment on #1342 with the same text. No `/grilling` needed; the requirement is fully stated.

### F4 — MEDIUM — The attest prompt's quiescence condition is not persisted

- **Claim:** Ray (L2157): the attest prompt "should be done when there are no longer any background
  tasks/agents/codex lanes/etc running so it on the latest data". The coordinator deferred it (L2163). The standing
  handoff still says only "`! mise run plan-attest` before `/clear`" (`.agent/plans/session-2026-09-23d.md`, Owed).
  The attestation is stale (handoff: `dc4b9265…` vs file `56d221f6…`; the pointer was since moved again by
  `762396bc`).
- **Disposition:** FIX-NOW (in the re-run handoff and the final user message). Exact Owed line:
  > - **Operator, LAST, after every background task, agent and codex lane has settled** (check: no running tasks in
  >   the harness, `pgrep -f 'codex exec'` scoped to this repo's scratchpad empty, no uncommitted plan edit pending):
  >   `! mise run plan-attest`, then `/clear`. It is the last manual attest; T1 of #1351 retires the D4 deny.

### F5 — MEDIUM — Current Phase is behind the addendum and omits the codex class fix

- **Claim:** Current Phase (`task_plan.md:676-677`) says "NEXT: Ray invokes `/to-spec` on the design of record
  (`pwf-migration-fable-round3-…`)". That is done: #1351 was published (`task_plan.md:665`, L2141). The addendum's
  NEXT (`:669-670`) lists only `/to-tickets` on #1351 and pr-loop. Neither line names the codex-invocation class fix
  that Ray scheduled into Phase 11 (L1846 "Stopgap now, rest as Phase 11"; recorded only at `:658-664`), nor
  Ray's "fix the review findings first, then Fable /to-tickets" order (L2157).
- **Control arm:** `grep -c '#1351' task_plan.md` → 2 (the addendum), `grep -n 'Codex-invocation'` → `:658` only;
  Current Phase `:672-680` contains neither.
- **Disposition:** FIX-NOW (plan edit; the coordinator is the plan writer). Replace `task_plan.md:674-680` with:
  > Phase 11 (fix-first resume + verified handoff + binding python standards). `/to-spec` DONE (#1326), `/to-tickets`
  > DONE (#1327–#1342). FIRST PRIORITY (Ray, 2026-09-23): the pwf current-workflow migration — spec **#1351**
  > published. NEXT, in order: (1) fix the session-integrity findings (briefs M-Q, `session-2026-09-23d-agent-briefs.md`);
  > (2) Ray types `/mattpocock-skills:to-tickets #1351`, executed by a Fable agent; (3) Fable `/to-spec` +
  > `/to-tickets` on pr-loop (`docs/specs/pr-loop-ship-fix-land.md`); (4) Fable `/to-spec` on the codex-invocation
  > class fix (addendum item "Codex-invocation class fix"); (5) `/implement` #1351's tickets, then #1327 and the
  > rest of the frontier in dependency order. [Codex native installer: per Ray's ruling on F1.] Phase 10 step 0
  > (#1310, KB#793 first) resumes after Phase 11.

### F6 — MEDIUM — #910 was never answered, though Ray's chosen option said to answer it

- **Claim:** The option Ray chose at L523 read "Record a ruling … and answer #910 with this finding." Earlier the
  coordinator asked to comment on #910 (L470). #910 has **0 comments**, last updated 2026-09-16T00:27Z.
  `task_plan.md:593` says the migration "absorbs #910"; #1351 names #910 four times; goal-history 032 says
  "#910 (answered by the design)" — but the issue itself carries no pointer.
- **Control arm:** `gh issue view 910 --json comments --jq '.comments|length'` → 0; the same query on #1307 → 0,
  so that probe reads real counts (a nonzero control: #1351's body grep for `#910` → 4).
- **Disposition:** FIX-NOW via `issue-filer` (own repo, own tracker). Comment text:
  > Answered by the 2026-09-23 design: attestation stays, but under upstream pwf's trust model the orchestrator
  > re-attests at phase boundaries (Ray ruled "Adopt upstream's trust model", superseding D4). Why the manual step
  > existed: `docs/research/kb/reports/agents/plan-attest-history-2026-09-23.md` (#879 autonomous mode + D4).
  > Implementation: spec #1351 (T1 retires the deny). Leave open until #1351's T1 lands.

### F7 — MEDIUM — The 2026-09-02 reports in `aaeea08e` are still stranded, and nothing plans their recovery

- **Claim:** `aaeea08e` holds 13 reports (`2026-09-02-{advisor-pwf,arbiter-pwf,review-attest,codex-install-review,
  pwf-codex-hooks,dd-plandoctor,sanity-plandoctor,upstream-audit,pwf-refactor-draft,graphify-facts,graphify-guide,
  review-session-905,briefs-index}.md`), reachable only from local branch `fix/image-lock-pr-control-arms-887`.
  23d's Owed lists "Recover `aaeea08e` … or record it as intentionally dropped"; `task_plan.md` has 0 hits.
  `3f2caac6` recovered `38ed61f2`'s 09-15 reports, not these. Three of them bear directly on this session's
  requests: `codex-install-review` (Brief Q / F1), `pwf-codex-hooks` and `dd-plandoctor` (Ray's plan-doctor hook
  request, row 8).
- **Control arm:** `git branch --contains aaeea08e` → only `fix/image-lock-pr-control-arms-887`; `ls
  docs/research/kb/reports/agents | grep -i 'attest\|arbiter\|advisor-pwf'` → only 2026-09-13/-23 files (the grep
  works: it returns 3 hits).
- **Disposition:** FIX-NOW on the handoff branch (docs-only, tracked destination per
  `agent-report-persistence.md`):
  `git checkout aaeea08e -- docs/research/kb/reports/agents/2026-09-02-*.md` then commit
  "docs(research): recover the 13 stranded 2026-09-02 reports (`aaeea08e`)". Then point Brief Q's report and the
  plan-doctor decision (F8) at them.

### F8 — MEDIUM — Ray's plan-doctor hook request has a design answer but no recorded ruling

- **Claim:** Ray (L523) asked to add plan-doctor "as a claude function hook and codex hook". Lane B recommended
  against both (a fail-only `pwf-hooks` check in the existing SessionStart doctor instead; codex hook gives a false
  FAIL under `PLANNING_DISABLED=1`). This was reported to Ray at L701; he did not object, but no AskUserQuestion
  asked him, and the plan still frames it as open research (`task_plan.md:594-595`). #1351 then lists "a Claude
  function hook or a codex hook for the plan doctor" as Out of Scope (#1351:520-521) and "no new Claude function hook
  and no new codex hook of any kind" (#1351:366).
- **Control arm:** `grep -c 'plan-doctor' task_plan.md` → 1 (`:594`, the research line); `grep -n -i 'function
  hook' #1351` → the out-of-scope lines, so both probes read their corpora.
- **Disposition:** PLAN. Append to the addendum after `:595`:
  > (a) ANSWERED 2026-09-23: no new Claude function hook and no codex hook for plan-doctor. A fail-only `pwf-hooks`
  > check joins the existing SessionStart `mise run doctor`, which codex already mirrors through `.codex/hooks.json`
  > (`pwf-plan-doctor-hooks-2026-09-23.md`; #1351:366). Reported to Ray at transcript L701 of `a6750a24`, not
  > objected; confirm at `/to-tickets`.

### F9 — MEDIUM — #1351 says the two upstream asks are "filed", but Ray chose the option that did not file them

- **Claim:** At L1043 the options were "File upstream + local stopgap (Recommended)" and "Adopt upstream's trust
  model"; Ray chose the latter (L1051). The coordinator had said filing is outward-facing and would be asked first
  (L1041). #1351 story 52 wants "the two upstream asks filed with the maintainer" (#1351:209), and Out of Scope says
  "the two upstream asks are filed, not blocked on" (#1351:525; also :438-441, :547). No approval for an outward
  filing is on record.
- **Disposition:** Questions §Q3; until Ray answers, `/to-tickets` should mark the upstream-asks ticket as
  "operator approval required before posting".

### F10 — MEDIUM — The coreutils shim tax has no ticket, though two documents say it gets "its own"

- **Claim:** Lane B measured 28 coreutils shadowed by mise shims at ~0.22 s per call, turning a 60 ms pwf hook into
  a 4 s plan-doctor fire, and slowing every shell script on the host (`pwf-plan-doctor-hooks-2026-09-23.md` §2;
  reported at L701). The Fable synthesis made it T11 ("KB-side"); #1351:523-524 says "the knowledge-base's coreutils
  shim tax (its own ticket)". No such ticket exists; `task_plan.md` mentions `conda:coreutils` only as a Phase 10
  step 6 pin (`:496`).
- **Control arm:** `gh api /search/issues?q=repo:ray-manaloto/{dotfiles,knowledge-base}+coreutils` → 4 and 5 hits,
  all older and unrelated (#792, #1020, #993, #1351; KB #314/#542/#636/#651/#638); the same route with `pwf` → 18
  hits, so the search discriminates.
- **Disposition:** PLAN + file via `issue-filer` (repo: wherever the `conda:coreutils` pin lives — Lane B names KB;
  confirm before filing). Plan line:
  > - **coreutils shim tax (Lane B, 2026-09-23):** 28 coreutils resolve to mise shims (~0.22 s/call) and cost every
  >   host shell script; ticket #<n>. Not part of #1351.

### F11 — MEDIUM — The operator `/hooks` trust owed for #1334/#1336 exists only in handoffs

- **Claim:** 23c and 23d both list "Operator: `/hooks` trust will be needed for the codex SessionStart and
  PreToolUse additions (#1336, #1334)". Neither issue body mentions `/hooks`. `task_plan.md` mentions `/hooks` trust
  only for Phase 10's codex PreToolUse deny (`:421`). A handoff is swept by `git clean -xdf`; the step will be lost
  when those tickets are implemented by a lane that never read the handoff.
- **Control arm:** the regex `(?i)/hooks[^\n]{0,80}` on #1302's body returns a hit, on #1334/#1336 none.
- **Disposition:** FIX-NOW: comment on #1334 and #1336: "Operator step before done: grant codex `/hooks` trust for
  this ticket's codex hook addition; `/implement` must stop and name it (the model cannot grant trust). See #1302 for
  the trust-hash probe."

### F12 — LOW — Two of the three startup-doctor drifts are untracked

- **Claim:** 23d Owed: "Startup doctor drift, not triaged". graphify 0.9.67 vs 0.9.65 is covered by #1344 (OPEN,
  created 2026-09-23T23:40Z), which `task_plan.md` never references (0 hits). claude-code 2.1.281 is published while
  the plan's step literal is "2.1.280 bump" (`task_plan.md:490`); no issue mentions 2.1.281 (search → 0, control
  `0.9.67` → 1). The listing budget (48,608 > 48,110 chars) is in no issue body (the one search hit, #1326, has no
  "listing budget" phrase when the body is scanned).
- **Disposition:** PLAN. Add to the Phase 11 addendum:
  > - **Doctor drift at 2026-09-23 startup (untriaged until now):** graphify → #1344; claude-code: Phase 10 step 1's
  >   "2.1.280" means latest stable at implementation (2.1.281 on 2026-09-23); skill-listing budget 48,608 > 48,110
  >   chars → the #1340/#1326 listing work or a new ticket (decide at `/to-tickets`).

### F13 — LOW — Stale harness worktrees carried across two handoffs

- **Claim:** `.claude/worktrees/agent-a6e5728e…` and `agent-a82a7019…` are "safe to `git worktree remove --force`"
  in 23c and 23d; nobody has removed them and nothing schedules it.
- **Disposition:** FIX-NOW if the coordinator confirms nothing live uses them (`git worktree list`); otherwise one
  Owed line in the next handoff.

### F14 — LOW — Memory and the 23d handoff point at a step that is already done

- **Claim:** `MEMORY.md:18` says "START HERE: /to-spec pwf migration"; #1351 is published and the next step is
  `/to-tickets`. `project_session_2026-09-23.md` (mtime 21:19) and `.agent/plans/session-2026-09-23d.md` (mtime
  21:28) predate `3f2caac6` (22:28), `762396bc` (22:34), the codex audits and #1351; the handoff's evidence table
  stops at Brief F.
- **Disposition:** FIX-NOW in the re-run `/session-handoff` (brief P covers the wording; this report only flags that
  the landing places are stale).

## 3. Questions for Ray

- **Q1 (F1) — Where does the native codex installer go, given Phase 10 says fable-orchestrator removal runs first?**
  Recommendation: promote ONLY the codex-native install/record half now (Brief Q's smallest safe path), ahead of
  #1351's `/implement`, and leave the `gpt-6-sol` move and base rebuild in Phase 10 step 2. PRO: gets off 0.154.0
  without dragging a base rebuild and the plugin removal forward. CON: breaks the ruled order at
  `task_plan.md:431-432,489`, so ask explicitly. Evidence: `task_plan.md:361-373,492`; L2157.
- **Q2 (F2) — Goal text: change the authority sentence now (iteration 033) or accept the deferral to T8?**
  Recommendation: accept the deferral. PRO: the sentence stays true until ticket plans exist. CON: overrides your
  "Yes, update goal text" answer, which is why it is asked, not assumed. Evidence: L1063/L1071;
  `task_plan.md:639,650-651`; goal-history 032.
- **Q3 (F9) — File the two upstream pwf asks (root-target attest flag; Claude/Codex analogue of Pi's
  `/plan-execute`)?** Recommendation: yes, draft-then-show before posting. PRO: less local drift over time, which is
  your stated principle. CON: outward-facing, and you picked the option without filing at L1051. Evidence:
  #1351:209,438-441,525; L1041-L1051.

## 4. Carried: nothing contradicts a ruling

All other rulings (rows 2-6, 9-19, 21-31) have a cited landing place. Superseded rulings (row 15) are marked
superseded in `task_plan.md:626-635`.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issues #910, #1302, #1307, #1326, #1327,
  #1334, #1336, #1340, #1342, #1344, #1351 and issue search (coreutils, 0.9.67, 2.1.281, listing budget, pwf
  control); repo files and commits `219e83cc..762396bc`, `aaeea08e`, `3f2caac6`.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — issue search (coreutils) only.
