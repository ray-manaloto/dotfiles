# S2 — Session-integrity DELTA audit: missing requests (2026-09-23, session `a6750a24`)

Status: COMPLETE. Brief: `docs/research/kb/reports/agents/session-2026-09-23d-agent-briefs.md` § "Briefs S1-S4"
(S2), method from § "Brief N". Scope: main-transcript user turns from Ray's "have agents review this session and
ensure the following" (L2157) onward; commits `5e258baf..48a1ee12`; the 18 published tickets (dotfiles
#1352-#1360, knowledge-base #802-#810) against the approved breakdown; Ray's four `/to-tickets` rulings; and a
re-check of every Brief N finding marked fixed. Read-only lane: this report is the only repo file I wrote.
Scratch artifacts (extractor, issue snapshots, edge read-back) are in the session scratchpad (`s2_*`, `s2issues/`).

## Method

- Main transcript `~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/a6750a24-770a-419d-996e-985bd27de611.jsonl`
  (3,170 JSONL lines at 23:46 CDT). Ordinals are JSONL line numbers (`L<n>`), the same convention Brief N used.
- Extractor (scratchpad `s2_extract.py`) collects every `type=user` record that is not `isMeta` and not a
  `<task-notification>` (string content or list text blocks), every `AskUserQuestion` tool_use paired to its
  tool_result by `tool_use_id`, and every `queued_command` attachment with `commandMode=prompt`.
- In-scope counts: 8 human user records (L2157, L2726, L2920, L2921, L2939, L3080, L3081, L3105), 7
  task-notifications, 3 ASK / 3 ANSWER pairs, and 0 queued prompts (all 3 `queued_command`s are task-notifications).
  One ANSWER (L2991) is the ask-quality hook's DENY of L2983, which was re-asked at L2995.
- **Control arm on the extractor:** the same script over the WHOLE transcript returns 19 human records (Brief N's 12
  up to L2205 plus my 7), 18 ASKs (Brief N's 15 plus my 3), and exactly one queued prompt, at L1506, which is the
  one Brief N found. The extractor reproduces Brief N's published counts, so my zero queued prompts in scope is a
  null that discriminates.
- **Draft-vs-published check:** for each of the 18 tickets I diffed the draft's "What to build" and "Acceptance
  criteria" sections against the issue body, after normalising whitespace and issue references. All 36 sections
  match at ratio 1.000 with identical lengths (for example, #1359: 1,032/1,032 and 810/810 chars). **Control:**
  ticket 16's draft compared with #1360's body scores 0.023, so the diff can tell different texts apart.
- **Edges:** `gh api /repos/<o>/<r>/issues/<n>/dependencies/blocked_by` for all 18. **Control:** #1352 and #802
  return `[]` as the draft says, while #1360 returns 6.

## 1. Every in-scope user message and answer, mapped

Status legend: MAPPED (landing place cited) · PARTIAL · UNMAPPED · IN-FLIGHT (the session is still acting on it).

| # | Ordinal | Verbatim (Ray) | Request / ruling | Landing place | Status |
|---|---|---|---|---|---|
| 1 | L2157 | "have agents review this session and ensure the following: - we did not dismiss any errors/repeated mistakes … - there are zero missing requests/issues in the task plan - there are zero bugs - there are zero vague documentation/plans…" | Briefs M-Q | Reports `session-audit-{dismissed-errors,missing-requests,vagueness,codex-cold-review}-2026-09-23.md` + `codex-native-installer-status-2026-09-23.md`, commit `5e258baf` | MAPPED |
| 2 | L2157 | "this should be added (if it doesn't already) into /session-handoff" | Handoff gains an integrity step | `.claude/skills/session-handoff/SKILL.md:137-156` (§1c), `:339-340` (checklist); `task_plan.md:690` | MAPPED |
| 3 | L2157 | "wait for the above to complete and fix any issues related to them and then have a fable model run /to-tickets" | Fixes first, then Fable `/to-tickets` | Fixes in `5e258baf` (04:11Z) before `/to-tickets` (L2939, ~04:29Z); Brief R launched with `model: fable` (L2954) | MAPPED (N F13 was never fixed; see S2-F8) |
| 4 | L2157 | "the work and task plan items for migrating to the native codex installer needs to happen asap as we are running codex on an old version - review old session history and task plan on this" | Codex native, as soon as possible | Host part done: `mise.toml:165-170`, `.github/workflows/ci.yml:70-72`, `task_plan.md:674-677`. Remainder: `task_plan.md:684-689`, Current Phase item 2 (`:721`). History: `codex-native-installer-status-2026-09-23.md` | PARTIAL → **S2-F4** (no implementation slot for the remainder) |
| 5 | L2157 | "provide a prompt when to run \"! mise run plan-attest\" - should be done when there are no longer any background tasks/agents/codex lanes/etc running" | Attest prompt, only once nothing is running | Rule at `SKILL.md:326-329,340`. Prompts at L2908 ("Verification is done and nothing is running") and L3075. No launch between L2977 and L3080. Current: `shasum task_plan.md` = `4a077b45…` = `.plan-attestation` | MAPPED; a re-attest may be owed after S1-S4 (IN-FLIGHT) |
| 6 | L2360 Q1 | "Direct change tonight" (option: "Add the `disable_tools` line on this branch now, keeping npm codex on CI's Linux runners … CON: … leaves CI, the daemon grace setting and the image undecided") | Host config now | Same as #4. CI decided (`ci.yml:72`), image deferred to Phase 10 step 2b (`task_plan.md:676-677`), daemon grace setting (`:684-685`) | MAPPED |
| 7 | L2360 Q2 | "Relabel + comment now (Recommended)" (option: remove `ready-for-agent`, add `needs-triage`, comment, add a "reconcile #1247" plan line) | Relabel #1247 and its children | #1247 = `needs-triage` plus 1 comment. 34/34 sub-issues `needs-triage`, 0 still `ready-for-agent` (control: 130 open `ready-for-agent` repo-wide). Plan line `task_plan.md:689` | MAPPED |
| 8 | L2360 Q3 | "Defer to T8; record now (Recommended)" (option: "Append iteration 033 now for the stopgap's lane change and the #1351 milestone, keeping the current goal text") | Goal text unchanged; 033 appended | `docs/agents/goal-history.md` iteration `dotfiles-goal-20260923-033` (line 1581; prior digest = current digest `711f7e97…`); `task_plan.md:589,678` | MAPPED |
| 9 | L2360 Q4 | "Accept all four (Recommended)": (1) advisory wrappers keep `--sandbox read-only`; the rule says no-`-s` applies only to implementation and sdlc-team; (2) wrappers keep `PLANNING_DISABLED=1`; (3) draft the upstream asks for Ray's review before posting; (4) order after `/to-tickets`: codex 2a → class fix → pr-loop | Four defaults | (1) `.claude/rules/ai-cli-invocation.md:38-40`. All 8 advisory wrappers carry `--sandbox read-only` and all 4 implementer/operator wrappers carry `danger-full-access` (the per-file probe returns both values, so it discriminates). (2) All 12 wrappers launch with `PLANNING_DISABLED=1 mise exec -- codex exec`. (3) `task_plan.md:680`; drafts in `pwf-migration-tickets-draft-2026-09-23.md` § "Not tickets: upstream asks"; #1351 corrections comment item 2. (4) `task_plan.md:680-681`, Current Phase `:721-724` | (1)(2) MAPPED; (3) PARTIAL → **S2-F6**; (4) PARTIAL → **S2-F4** |
| 10 | L2726 | `/verify` | Runtime-verify the wrapper change | `86324c6a` (two live `codex-sol-advisor` runs; run 2 on codex 0.156.1); `task_plan.md` M-6 ✅ | MAPPED |
| 11 | L2920-21 | `! mise run plan-attest` → SHA `5ab1a140…` | Operator attest | Superseded by #13 | MAPPED |
| 12 | L2939 | `/mattpocock-skills:to-tickets #1351` | Fable `/to-tickets` | Brief R (`model: fable`, L2954) → draft `pwf-migration-tickets-draft-2026-09-23.md` → 18 issues (L3046) → `48a1ee12`; Current Phase item 1 (`task_plan.md:717-720`) | MAPPED |
| 13 | L2996 Q1 | "Keep 18 as drafted (Recommended)" | 18 tickets | 18 issues; all 36 sections match the draft at 1.000 (control 0.023) | MAPPED |
| 14 | L2996 Q2 | "One bump (9), small second if needed (Recommended)" (option: "Ticket 9 bumps the pin once tickets 2–7 land; if ticket 8 … lands later, ticket 16 carries a small second bump") | Conditional second pin bump in ticket 16 | #1353 (ticket 9) pins tickets 2-7 ✓. The conditional second bump is in neither #1359 (ticket 16) nor `task_plan.md` | PARTIAL → **S2-F1** |
| 15 | L2996 Q3 | "ready-for-human (Recommended)" for ticket 17 | #1360 label | #1360 = `enhancement`,`ready-for-human` ✓. The draft's executor line ("the Claude orchestrator … NOT a codex lane") was dropped when the ticket was published | MAPPED; detail lost → **S2-F2** |
| 16 | L2996 Q4 | "Publish as drafted (Recommended)" (option: "Keep M-7 in ticket 10 … and ask ticket 18's question when ticket 14 lands. Publish 18 issues in dependency order with native blocked-by links: dotfiles tickets in dotfiles, KB tickets in knowledge-base") | M-7 in ticket 10; timing of ticket 18's question; dependency-ordered publication with native edges; repos | M-7: #1354 body ("…compares the plan digest written in the handoff text with the tracked pointer (integrity-review item M-7)") ✓. Repos ✓ (9 + 9). Edges: 39/39 match the draft graph ✓. **The timing of ticket 18's question is persisted nowhere** | PARTIAL → **S2-F2**; edge count misreported → **S2-F7** |
| 17 | L3080-81 | `! mise run plan-attest` → SHA `4a077b45…` | Operator attest | `.plan-attestation` = `shasum -a 256 task_plan.md` (both `4a077b45de2f08ac…`); `docs/agents/plan-pointer.json` agrees | MAPPED |
| 18 | L3105 | `/session-handoff` | Handoff | This run (S1-S4) | IN-FLIGHT → **S2-F9** lists what it must refresh |

## 2. Brief N findings: were the "fixed" ones actually fixed?

| N finding | Brief N disposition | State in the tree now | Verdict |
|---|---|---|---|
| F1 native codex not promoted | PLAN + ask Ray | Ray ruled (L2360 Q1). `mise.toml:165-170` `disable_tools = ["npm:@openai/codex"]`, `ci.yml:70-72` `MISE_DISABLE_TOOLS: ""`, `task_plan.md:674-689` | FIXED (host); the remainder has no implementation slot → S2-F4 |
| F2 goal text deferral | ask Ray | Ray ruled defer (L2360 Q3); goal-history 033 at `docs/agents/goal-history.md:1581`; read-first note `task_plan.md:589` | FIXED |
| F3 `/session-handoff` checks | PLAN (skill edit) | `.claude/skills/session-handoff/SKILL.md:137-156,339-340`; mirror regenerated (the diffs from `.agents/…` are generator substitutions; see the incidental note) | FIXED |
| F4 attest quiescence | FIX-NOW | `SKILL.md:326-329,340`; handoff `.agent/plans/session-2026-09-23d.md:42` | FIXED |
| F5 Current Phase behind | FIX-NOW | `task_plan.md:714-725` rewritten | FIXED (see S2-F4 on item 5) |
| F6 #910 unanswered | FIX-NOW | #910 comment 2026-09-24T04:03:15Z ("Answer (Ray, 2026-09-23): yes…") | FIXED |
| F7 `aaeea08e` reports stranded | FIX-NOW | 13 `2026-09-02-*.md` files added in `5e258baf` (`git show --stat` count = 13) | FIXED |
| F8 plan-doctor hook ruling | PLAN | `task_plan.md:692` "answered by research, not separately ruled"; delivered as #1356 (D5) | PLANNED; wording stale → S2-F10 |
| F9 upstream asks "filed" | ask Ray | Ray ruled drafts (L2360 Q4(3)); `task_plan.md:680`; #1351 corrections comment item 2 | FIXED; review owed → S2-F6 |
| F10 coreutils shim ticket | PLAN + file | Plan line `task_plan.md:711`; **not filed** (knowledge-base search `coreutils created:>=2026-09-23` → 0; control `pwf` same window → 9) | PLANNED, not filed (acceptable: a plan line is a valid PLAN disposition) |
| F11 `/hooks` trust on #1334/#1336 | FIX-NOW | Comments at 04:03:17Z / 04:03:18Z | FIXED, but `task_plan.md:712` still lists it as a to-do → S2-F9 |
| F12 doctor drift | PLAN | `task_plan.md:706-709` | PLANNED |
| F13 stale harness worktrees | FIX-NOW (if unused) | Both still registered (`git worktree list`); no plan line | **NOT FIXED, NOT PLANNED** → S2-F8 |
| F14 memory/handoff stale | FIX-NOW in the re-run handoff | `MEMORY.md:18` now reads "START HERE: /to-tickets #1351 (Fable)", which is also done now; handoff mtime 23:27, before `48a1ee12` | Stale again → S2-F9 (IN-FLIGHT) |

No regressions: every FIXED row above is still true at `48a1ee12`.

## 3. Findings (unmapped or partially mapped only)

(There is no S2-F3: it was folded into S2-F2, and the other numbers were kept unchanged.)

### S2-F1 — MEDIUM — Ray's conditional second pin bump ("ticket 16 carries a small second bump") landed nowhere

- **Claim:** Ray chose "One bump (9), small second if needed" (L2996 Q2). The option read: "if ticket 8 (the shared
  skill bytes) lands later, ticket 16 carries a small second bump". #1353 (ticket 9) pins "the commit that ships
  tickets 2–7". #1359 (ticket 16) is natively blocked by knowledge-base#808 (ticket 8) and must install ticket 8's
  bytes and run its parity verb ("The shared skill and rule from ticket 8 are installed as byte-identical copies
  and the parity check joins the lint gate"). Its body never says to move the pin, and neither does
  `task_plan.md`. The draft only had the idea in its step-4 question section, and "publish as drafted" copied the
  ticket body verbatim, so the ruling fell out. An implementer of #1359 would find the pinned `kb-setup` missing
  the parity verb and would have no written instruction to bump it.
- **Evidence:** issue bodies as of the audit; draft Q2 (`pwf-migration-tickets-draft-2026-09-23.md`, step-4
  question 2).
- **Control arm:** in #1353's body, "pin" → 9 hits (the probe reads the body). In #1359 and #1353, "bump" → 0 and
  "second" → 0. `grep -n -i -E 'second (small )?(pin )?bump|one bump' task_plan.md` → 0, while the same grep for
  `#810` → 1 hit (`:719`).
- **Disposition:** FIX-NOW. `issue-filer` comments on dotfiles#1359 (our own tracker):
  > **Pin bump (Ray's `/to-tickets` ruling, 2026-09-23: "One bump (9), small second if needed").** If the
  > `kb-setup` SHA pinned by #1353 predates knowledge-base#808, this ticket first moves the pin to a
  > knowledge-base commit that contains #808, and keeps #1353's host-only smoke and minimum-version contract green
  > at the new SHA. If #1353 already pinned a commit containing #808, no bump is needed; say which case applied
  > in the PR.

  Also add a plan sub-bullet under Current Phase item 1 (`task_plan.md:717-720`):
  > Ray's `/to-tickets` rulings (L2996): 18 as drafted; one pin bump in D2 #1353 (tickets 2-7), plus a small
  > second bump inside D8 #1359 if K7 knowledge-base#808 lands after #1353; D9 #1360 `ready-for-human`; ask K9
  > knowledge-base#810's question when K8 knowledge-base#809 lands.

### S2-F2 — LOW-MEDIUM — Publication dropped the draft's per-ticket header lines, losing two ruled details

- **Claim:** The publish script (L3030/L3043) kept the draft's `## Parent / What to build / Acceptance criteria /
  Blocked by` sections and dropped the bold header line above them. Two rulings or decisions lived only in those
  header lines or in the transcript:
  1. Ticket 17 / #1360: "**Executor:** the Claude orchestrator on a branch — NOT a codex lane. Three
     `AskUserQuestion` stops inside." (draft, ticket 17 header). #1360 has 0 hits for "Executor", "codex lane" and
     "AskUserQuestion". It does keep "stop 1/2/3" (3 hits for "stop"), so that probe reads the body. The
     `ready-for-human` label keeps an autonomous lane away, but a human-launched `/implement #1360` has no written
     rule against routing it to a codex lane.
  2. Ticket 18 / knowledge-base#810: the header "**Label:** `ready-for-human` until Ray answers; then
     `ready-for-agent`" was dropped. Ray's ruling "ask ticket 18's question when ticket 14 lands" (L2996 Q4) is in
     neither #810 (0 hits for "when", "ready-for"; "ticket 14" appears once, in the Blocked-by line) nor
     `task_plan.md` (only `:719`, the label).
- **Disposition:** FIX-NOW. Two comments via `issue-filer`:
  - dotfiles#1360: "**Executor (from the approved breakdown):** the Claude orchestrator on a branch, NOT a codex
    lane. It carries three `AskUserQuestion` stops, so Ray must be present; that is why it is `ready-for-human`."
  - knowledge-base#810: "**When to ask (Ray, 2026-09-23):** ask this ticket's round-done question when
    knowledge-base#809 lands, not before. After Ray answers, relabel `ready-for-human` → `ready-for-agent`."

  The plan sub-bullet in S2-F1 carries the timing as well.

### S2-F4 — MEDIUM — "Codex native ASAP" has a spec slot but no implementation slot; the Phase 11 header omits it

- **Claim:** Ray asked that codex-native "happen asap" (L2157) and accepted order (4): "after `/to-tickets` #1351:
  codex 2a, then the codex class fix, then pr-loop", whose PRO read "codex is updated first, as you asked" (L2360).
  The plan schedules only the SPEC work for the step-2a remainder (Current Phase item 2, `task_plan.md:721`).
  Item 5 (`:724`) then says "`/implement`: #1351's tickets first (T1 first), then #1327 and the rest of Phase 11's
  frontier". Read literally, the remainder's tickets would be implemented after all 18 #1351 tickets and #1327.
  Goal-history 033's workflow draws the same order: node B specs "codex 2a remainder" and node E is
  "/implement #1351 T1..T10". The Phase 11 heading (`task_plan.md:506`) reads "#1351 FIRST, then codex class fix,
  pr-loop…" and never names the step-2a remainder.
- **Why it matters:** the remainder includes the `-m gpt-6-sol` live arm, the codex schema regeneration and moving
  the `schemas/sources.toml` pin off npm (`task_plan.md:684-689`). The CI and image codex also stay on 0.154.0
  until it runs.
- **Control arm:** `grep -n '2a' task_plan.md` finds `:681`, `:684` and `:721`, so the term is searchable. None of
  the hits is in item 5 or in the heading at `:506`.
- **Disposition:** PLAN, plus an AskUserQuestion to Ray (the option text is ambiguous between spec order and build
  order). Recommended text for `task_plan.md:724`:
  > 5. Then `/implement`, in this order: the codex step-2a remainder's tickets (Ray, 2026-09-23: "asap"; host-only,
  >    no base rebuild), then #1351's tickets (D1 #1352 and K1 knowledge-base#802 first), then the codex class
  >    fix's tickets, #1327 and the rest of Phase 11's frontier. pr-loop's build waits on #1329/#1330.

  Append "codex step-2a remainder," after "(#1351) FIRST, then" in the heading at `:506`, and mirror the order in
  the next goal-history iteration's workflow.

### S2-F5 — MEDIUM — The 18 tickets, #1351's corrections and #910's answer cite files that exist only on an unpushed local branch

- **Claim:** Every published ticket ends "Implementer anchors: `docs/research/kb/reports/agents/pwf-migration-tickets-draft-2026-09-23.md`".
  The nine knowledge-base tickets cite that path without naming the dotfiles repo. The file exists only on branch
  `docs/session-2026-09-23d-handoff`, which is not on the remote: `git ls-remote origin
  refs/heads/docs/session-2026-09-23d-handoff` returns nothing with rc=0, and no PR exists for that head. The
  handoff records "NOT shipped; `mise run ship` when Ray asks" (`.agent/plans/session-2026-09-23d.md:14`). Nothing
  in the plan makes shipping this branch a prerequisite for dispatching any of the 18 tickets. A lane working in a
  fresh clone of `main`, or in the knowledge-base, cannot open the anchors.
- **Control arm:** `git cat-file -e origin/main:<anchors file>` → rc=128 (absent), and the same probe on
  `session-2026-09-23-agent-briefs.md` → rc=0 (present on main). So the probe can see files that are on `main`.
- **Disposition:** PLAN plus a Ray question (shipping is Ray's call per the handoff). Plan text to add at the top
  of Current Phase:
  > 0. Ship `docs/session-2026-09-23d-handoff` (`mise run ship`, when Ray asks) BEFORE dispatching any #1351
  >    ticket: the tickets' implementer anchors, #1351's evidence reports and #910's evidence exist only on that
  >    branch.

  After the branch ships, comment once on #1351: "Implementer anchors for all 18 tickets:
  `ray-manaloto/dotfiles` `main`, `docs/research/kb/reports/agents/pwf-migration-tickets-draft-2026-09-23.md`
  (appendix)."

### S2-F6 — LOW — Ray's review of the two upstream-ask drafts is owed, but no owed item says so or where the drafts are

- **Claim:** Ray accepted "Draft the two upstream pwf asks for your review before anything is posted" (L2360 Q4(3)).
  The drafts exist in `pwf-migration-tickets-draft-2026-09-23.md` § "Not tickets: upstream asks" (Draft A, Draft
  B). L2981 told Ray "the two upstream asks are drafts for your review, not tickets". No AskUserQuestion ever
  showed Ray the text. `task_plan.md:680` says they are "DRAFTED for Ray's review", without a location, and the
  handoff's Owed list has no entry for them.
- **Control arm:** a regex over in-scope assistant blocks for "Draft A|upstream ask|OthmanAdi" → 7 blocks, none of
  them an AskUserQuestion presenting the drafts. The same method returns 10 blocks for "plan-attest".
- **Disposition:** PLAN. Append to `task_plan.md:680`, after "(not "filed")":
  > — texts: `pwf-migration-tickets-draft-2026-09-23.md` § "Not tickets: upstream asks" (Draft A root-target
  > attest flag; Draft B Claude/Codex analogue of Pi's `/plan-execute`). OWED: show Ray both texts via
  > AskUserQuestion; post to `OthmanAdi/planning-with-files` only on his approval.

  Add the same line to the handoff's Owed list.

### S2-F7 — LOW — "42 blocked-by links" was reported to Ray; 39 were written and 39 exist

- **Claim:** L3071 (to Ray: "42 native blocked-by links, including cross-repo, all written with rc=0"), L3075 and
  commit `48a1ee12` all say 42. The publish log (L3046) holds 39 `edge … rc=0` lines and 18 `created` lines. The API
  read-back returns 39 edges, and they match the draft's dependency graph exactly (`s2_edges.txt`). The number is
  wrong, not the graph.
- **Control arm:** the read-back returns 0 for #1352 and #802 (unblocked in the draft) and 6 for #1360 and #1353, so
  it distinguishes issues with and without blockers.
- **Disposition:** FIX-NOW in the handoff and in the next goal-history iteration: say "39 native blocked-by
  edges, read back and matching the draft graph". The commit message cannot be changed; the handoff should note
  the correction.

### S2-F8 — LOW — Stale harness worktrees: carried a fourth time, still no plan line (Brief N F13 not fixed)

- **Claim:** `.claude/worktrees/agent-a6e5728e0204c312c` (`research/codex-exec-review-settings`) and
  `agent-a82a7019cd7d3bac4` (`research/hk-2-0-impact`) are still registered. Both are clean, and each has one unique
  commit whose only file is byte-identical on HEAD (`git diff --quiet HEAD <branch> -- <file>` → same).
- **Disposition:** FIX-NOW (coordinator, after the branch ships so the reports are on `main`):
  `git worktree remove .claude/worktrees/agent-a6e5728e0204c312c` and
  `git worktree remove .claude/worktrees/agent-a82a7019cd7d3bac4` (clean, so no `--force`). Until then, keep one
  Owed line in the handoff.

### S2-F9 — LOW (IN-FLIGHT) — Landing places the running `/session-handoff` must refresh

- `.agent/plans/session-2026-09-23d.md:14` says HEAD is `b7c59920` (now `48a1ee12`), and `:17` says the
  attestation is stale (`5ab1a140` vs `dc4b9265`). It is now current: both are `4a077b45`.
- `MEMORY.md:18` says "START HERE: /to-tickets #1351 (Fable)", which is done. The next step is Current Phase item 2
  (or item 0, per S2-F5).
- Goal-history 033 says "`/to-tickets` on #1351 not started", and its workflow names "#1351 T1..T10". The
  published breakdown is 18 tickets (D1-D9, K1-K9), and T10 is "not tickets". The 18-ticket publication is a
  milestone, so `goal-history.md` should get an appended iteration (034) rather than an edit.
- `task_plan.md:712` "N F11: comment the operator `/hooks` trust step on #1334 and #1336" is done (both comments
  exist) and should be marked ✅.
- Any FIX-NOW plan edit from S1-S4 makes attestation `4a077b45` stale. Per `SKILL.md:326-329`, the attest prompt
  must come last, after S1-S4 and any follow-up lanes have settled.

### S2-F10 — LOW — The plan-doctor ruling line is out of date

- **Claim:** `task_plan.md:692` still says "answered by research, not separately ruled". Ray has since approved the
  breakdown that contains #1356 (D5, FAIL-only `pwf-hooks` doctor check) (L2996 "Publish as drafted"), and #1351's
  out-of-scope list excludes both hooks.
- **Disposition:** PLAN (wording). Replace "not separately ruled" with "ratified by Ray's approval of #1351's
  breakdown on 2026-09-23 (#1356 = D5)".

## 4. Incidental (outside S2's scope; for S3/S4)

- `.agents/skills/session-handoff/SKILL.md:147` (the generated codex-side mirror) reads "for a **Codex**-authored
  diff, `fable-orchestrator:codex-reviewer`". The source `.claude/…:147` says "Claude-authored". The mirror
  generator's Claude→Codex substitution flipped a model-family rule. On the codex side it now tells a reviewer to
  use the same family for a codex diff, which contradicts the table's own "a model family that did NOT write the
  diff". Introduced by `5e258baf`. Suggested fix: phrase the source cell without a vendor noun the generator
  rewrites (e.g. "a Claude-authored diff → `fable-orchestrator:codex-reviewer`; a codex-authored diff → an Opus
  `cold-reviewer`"), or exempt that cell from the substitution. Then regenerate the mirror and re-check parity.

## 5. Questions for Ray (for the coordinator's AskUserQuestion)

- **Q1 (S2-F4): when are the codex step-2a remainder tickets implemented?** Recommended: before #1351's tickets.
  PRO: matches "asap" and "codex is updated first"; the work is host-only with no base rebuild. CON: delays #1351
  T1 by the length of that small ticket set. Evidence: `task_plan.md:684-689,721,724`; L2157; L2360 Q4.
- **Q2 (S2-F5): ship `docs/session-2026-09-23d-handoff` now, before any #1351 dispatch?** Recommended: yes, via
  `mise run ship`. PRO: the 18 tickets' anchors and the evidence for #1351 and #910 become reachable from `main`.
  CON: an outward action that needs your go. Evidence: `.agent/plans/session-2026-09-23d.md:14`; `git ls-remote`
  shows nothing on the remote.
- **Q3 (S2-F6): review the two upstream-ask drafts now or later?** Recommended: later, as an owed item. PRO: they
  block nothing (the draft says "Neither blocks anything above"). CON: one more owed line. Evidence:
  `pwf-migration-tickets-draft-2026-09-23.md` § "Not tickets: upstream asks".

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): issues #1352-#1360 (bodies, labels, native
  `blocked_by`), #1351 (corrections comment), #910, #1334, #1336 (comments), #1247 (labels, comment, 34
  sub-issues), label searches (`needs-triage`, `ready-for-agent`), issue search (`coreutils`); `git ls-remote` for
  the handoff branch; commits `5e258baf..48a1ee12`.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): issues #802-#810 (bodies, labels,
  native `blocked_by`); issue search (`coreutils`, control `pwf`).
