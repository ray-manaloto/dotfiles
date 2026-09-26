# Session audit — vague or misinterpretable docs/plans (2026-09-25c, Brief P)

Reviewer: read-only session-integrity lane (Brief P, `session-2026-09-25c-agent-briefs.md`). Session under review:
`e0054614-0df9-4dff-9b50-af3b534871e1`. Scope: dotfiles `f7245695..e38ce9cb`, knowledge-base `cb08d898..6957b0ac`,
issue bodies dotfiles #1383/#1384 + OthmanAdi/planning-with-files#296, closing comments dotfiles #1318 + KB #794,
`task_plan.md` § fable-orchestrator removal / § Current Phase / item 23.

Status: COMPLETE — 12 findings (0 HIGH / 6 MEDIUM / 6 LOW). Per the brief this lane wrote only this file (no
`findings.md`/`progress.md` appends); the coordinator persists the condensed record. Transcript "ordinals" are 0-based JSONL line indexes of the main
transcript (`python3 enumerate`); add 1 for `grep -n`/`sed -n` line numbers.

## Findings

### P1 — MEDIUM — task_plan item 23(f) prescribes a wording that did NOT ship, and is not marked DONE

- **Claim:** `task_plan.md:879-881` still reads "(f) F13 — RULED …: reword only — `register.ts:375` "install is BROKEN" →
  "install is not current — repair before continuing"". What shipped in #1382 (`e38ce9cb`) is
  "install **failed a required check** — repair it before continuing"
  (`.claude/skills/claude-doctor/hooks/register.ts:375`). The deviation was deliberate and justified (the `invalid`
  verdict also fires on install-method and clean-marker failures, `claude_doctor.py:517`; transcript ordinal 716
  SendUserMessage and the commit body at ordinal 747), but the plan was never updated. A fresh session or a codex lane
  reading 23(f) sees an OPEN item with a concrete wording that differs from the code, and could "fix" the code back to
  "not current" — which would be wrong for method-mismatch/clean-marker findings.
- **Evidence:** `task_plan.md:879-881`; `register.ts:375`; `git show e38ce9cb` message; transcript ordinals 533 (the
  plan edit that wrote "not current"), 597 (the code edit that wrote "failed a required check").
- **Control arm:** the transcript search for `failed a required check` returned hits at 597/607/642/716/747 and the
  search for `not current — repair` returned hits at 469-533 — both strings are findable, so the ordering (plan
  written first, code diverged later, plan not revisited) is real. `grep -n 'F13' task_plan.md` → only line 879.
- **Disposition: FIX-NOW.** Replace `task_plan.md:879-881` "(f) F13 — RULED (Ray, 2026-09-25): keep `running != latest`
  enforcing; reword only — `register.ts:375` "install is BROKEN" → "install is not current — repair before continuing"
  (+ `.agents/` mirror, `harness.ts:480` regex). Advice: …" with:
  "(f) F13 — DONE 2026-09-25 in dotfiles #1382 (`e38ce9cb`). Ray ruled: keep `running != latest` enforcing, reword only.
  Shipped lead: "install failed a required check — repair it before continuing" — NOT the advisor's "not current",
  because `invalid` also fires on install-method and clean-marker findings (`claude_doctor.py:517`). Do not revert to
  "not current". Advice: `1319-live-arm-claude-advisor-dotfiles-2026-09-25.md`."

### P2 — MEDIUM — the #1319 "Next" step in task_plan and the #1319 receipt list DIFFERENT remaining arms; the done half is not marked done

- **Claim:** Three sources name what is left of #1319, and they disagree:
  - Issue #1319 body ("What to build"): `verify`/`rule-sync`/`plugin-health` green in both repos; live-path grep for
    `fable-orchestrator:` = 0 with a control; one `sdlc-team` dispatch settles `completed`; the four `Agent` spawns;
    one KB tool-review run to its Review phase; AC3: a #1293 map comment.
  - `docs/receipts/1319.md:4-7` (Still OPEN): codex arms, sdlc-team (#1362), KB tool-review, the
    `verify`/`rule-sync`/`plugin-health` + live-path-grep re-runs, the #1293 map comment. Matches the issue.
  - `task_plan.md:948-951` (Current Phase → Next, item 2): "**Now (Claude-only):** spawn `premise-verifier` and
    `claude-advisor` … **After 2026-09-30 …:** run `kb-codex-implementer` once and one `kb-tool-review` …. The
    sdlc-team arm waits on #1362." — it OMITS the `verify`/`rule-sync`/`plugin-health` re-runs, the live-path grep and
    the #1293 comment, ADDS a `kb-codex-implementer` arm that #1319 never asks for, and still presents the Claude-only
    half as "Now" although #1382 did it.
  A fresh session executing task_plan item 2 as written would close #1319 without the grep/verify arms or the map
  comment (AC1/AC3 unmet), or re-spawn the four Agent arms that already have a receipt.
- **Evidence:** `gh issue view 1319 -R ray-manaloto/dotfiles` (body, 0 comments); `docs/receipts/1319.md:3-7`;
  `task_plan.md:948-951`; also `task_plan.md:767` header "ACTIVE, NEXT SESSION: #1319 live arms, V8, F2, claudex-loop
  removal, #794 close" (V8, claudex-loop and #794 are DONE per `:776`, `:780`, `:789`).
- **Control arm:** `grep -n 'kb-codex-implementer' task_plan.md` → hits at 791, 815, 949 (so the term is findable);
  the same term in the #1319 body → 0 (jq over the fetched JSON). `grep -E 'rule-sync|live-path'` over
  `task_plan.md:767-953` → 3 hits (`:791` #1384 axis, `:861` rule-synced files, `:932` KB-main CI note), none of them
  a #1319 arm — so the grep sees the term and the arms are genuinely absent from the plan's next step.
- **Disposition: FIX-NOW.** (a) Replace `task_plan.md:948-951` with:
  "2. #1319 live arms. **DONE 2026-09-25 (#1382, `docs/receipts/1319.md`):** the four Claude-only `Agent` arms.
  **After 2026-09-30 4:05 PM CDT (codex):** one `kb-tool-review` to its Review phase (also the artifact-mode proof and
  KB#793's arm) and, as an extra stopgap check not required by #1319, one `kb-codex-implementer` run. **Also owed, runnable
  now:** re-run `mise run verify`, `mise run rule-sync`, `mise run plugin-health` in both repos and the live-path grep for
  `fable-orchestrator:` (control: `codex-sol-implementer`), each appended to `docs/receipts/1319.md`. **Blocked on #1362:**
  the `sdlc-team` dispatch. **Last:** comment on #1293 that Phase 10 step 0 is complete, then close #1319 and #1310."
  (b) Replace the `:767` header with "## fable-orchestrator removal (2026-09-24) — ACTIVE: #1319 remaining arms (see
  Current Phase item 2), F2 graphify rebuild, V6 KB CLAUDE.md pointer".

### P3 — LOW — `docs/receipts/1319.md` dangling "F13" pointer (committed) — being fixed in the working tree; make it name the file

- **Claim:** committed `docs/receipts/1319.md:16` (`e38ce9cb`) says "see F13 below"; the receipt has no F13. F13 is defined
  in `docs/research/kb/reports/agents/session-audit-dismissed-errors-2026-09-25b.md:222`. The advisor report header
  (`1319-live-arm-claude-advisor-dotfiles-2026-09-25.md:1,5`) also says "the F13 / item 23(f) advice" and "the question
  Ray still owes" (Ray has since ruled). The working tree (uncommitted, this handoff branch) already rewrites line 16 to
  "audit F13 / task_plan 23(f); see Notes" — better, but "audit F13" still does not say WHICH audit (there are F13s in
  several `session-audit-*` files).
- **Evidence:** `git diff e38ce9cb -- docs/receipts/1319.md`; `grep -n F13 session-audit-*2026-09-25b.md` → only
  `session-audit-dismissed-errors-2026-09-25b.md:222,243`.
- **Control arm:** `grep -c F13 docs/receipts/1319.md` → 1 (the pointer itself, no definition), while the same grep over
  the 25b dismissed-errors audit returns its heading.
- **Disposition: FIX-NOW.** Receipt line 16 cell: "returned (KEEP-BROKEN, reword only — `session-audit-dismissed-errors-2026-09-25b.md`
  F13 / task_plan 23(f); see Notes)". Receipt Notes, replace the last bullet with: "The dotfiles advisor answered Ray's
  owed ruling 23(f) (F13 in `session-audit-dismissed-errors-2026-09-25b.md`). Ray ruled 2026-09-25: keep enforcing,
  reword only. Shipped in this PR as "install failed a required check — repair it before continuing" (not the advisor's
  "not current": `invalid` also covers install-method and clean-marker findings)." Advisor report line 5: "It answered
  the question Ray then owed (task_plan.md 23(f); Ray ruled 2026-09-25 — see `docs/receipts/1319.md` Notes)".

### P4 — MEDIUM — KB#794's close hands AC1 to "#750", but the code it cites says that work is "a separate, later ticket" with no number

- **Claim:** The knowledge-base #794 closing comment (2026-09-26T02:25Z) says "AC1 is superseded by #750, not met … Binding
  the variant is #750's job (`review.py:445-447`)". The cited code (`knowledge-base/python/src/kb_setup/review.py:436-446`)
  says the opposite: "**#750 Phase 1** deliberately adds NO third term here … **Phase 2 (gating) is a separate, later
  ticket**". #750's body never mentions a Phase 2 at all. So AC1 of #794 was transferred to a ticket that, per the code
  and #750 itself, does not own it — the same "later ticket with no number" defect class that V8 just fixed for
  `kb-codex-implementer`. A future session closing #750 on its Phase 1 scope would silently drop #794's AC1.
  Secondary: `cli.py:834` and `review.py:442` now call `cold:codex-astra` "the default … since #794", while #794 was
  closed WITHOUT building a code default ("No code default lane") — a reader can take "since #794" to mean #794 added one.
- **Evidence:** `gh issue view 794 -R ray-manaloto/knowledge-base` (closing comment); `review.py:436-446`;
  `cli.py:831-835`; `gh issue view 750 -R ray-manaloto/knowledge-base` body.
- **Control arm:** `jq -r .body kb-750.json | grep -ci phase` → 0, while `grep -ci receipt` on the same body → 6 (the
  probe reads the body). #750's comments do mention "if Phase 2 gates" (1 hit), so Phase 2 exists as a concept, not as
  an owned scope. GitHub search `repo:ray-manaloto/knowledge-base "Phase 2" 750` → only #750 itself; no separate ticket.
- **Disposition: PLAN** (needs Ray: is #750 Phase 2 in #750's scope or a new ticket?). task_plan text, under
  § fable-orchestrator removal, after the KB#794 bullet: "- **KB#794 AC1 owner (OPEN, needs Ray):** the #794 close says
  AC1 (variant bound at the review seam) is #750's job, but `kb_setup/review.py:445` calls #750 Phase 2 'a separate,
  later ticket' and #750's body has no Phase 2. Ask: extend #750's scope to Phase 2 (edit its body + the
  `review.py:445` comment to say 'Phase 2 of #750'), or file the Phase 2 ticket and put its number in `review.py:445`
  and a follow-up comment on KB#794. Also reword `cli.py:834`/`review.py:442` 'the default since #794' → 'the
  skill-level default (kb-review SKILL.md; no code default, #794)'." No /grilling needed — one AskUserQuestion.

### P5 — MEDIUM — V6 reads as done in the Current Phase list, but the KB CLAUDE.md rewrite it rules is not done and has no step

- **Claim:** `task_plan.md:946-947` (Next, item 1): "DONE 2026-09-25b — rulings recorded …: V6 subsumed, KB#794 close,
  `kb-tool-review` artifact mode kept, claudex-loop removed fully". "V6 subsumed" is a RULING whose action —
  `task_plan.md:774-775` "Rewrite KB `.claude/CLAUDE.md`'s 'escalate to Fable/Opus only when a problem needs reasoning
  codex cannot close' as a pointer to dotfiles `.claude/token-routing.md` trigger 2" — has not been done:
  `knowledge-base/.claude/CLAUDE.md:33` still carries the original sentence. The action is not in the Next list, the
  2026-09-24/25 remainder, or any issue. KB#815 (this session's KB PR) touched the neighbouring stopgap but not this.
  Note also item 7 of the remainder (`task_plan.md:814`) targets `.claude/CLAUDE.md:40-42` in KB for grok/fable text —
  V6's line 33 is adjacent and the two edits should go in one KB PR, but neither mentions the other.
- **Evidence:** `task_plan.md:774-775,946-947,814-817`; `knowledge-base/.claude/CLAUDE.md:33`;
  `git -C knowledge-base log -1 -- .claude/CLAUDE.md` → `d229399f` (#812, ponytail), predates the ruling's action.
  Trigger 2 exists: `.claude/token-routing.md:17` ("the same problem resisted two attempts after a codex verdict").
- **Control arm:** the grep for `escalate to Fable` in KB `.claude/CLAUDE.md` returned line 33 (the probe finds the
  string); `grep -in trigger .claude/token-routing.md` returned 0, which is why I read the list — the triggers are a
  numbered list without the word "trigger", so "trigger 2" in the plan is correct but not greppable (see rewrite).
- **Disposition: FIX-NOW** (plan text). Replace `task_plan.md:774-775` with: "- **V6 → SUBSUMED by trigger 2 (RULED
  2026-09-25b; edit OWED).** In knowledge-base `.claude/CLAUDE.md:33`, replace '…escalate to Fable/Opus only when a
  problem needs reasoning codex cannot close.' with a pointer: 'escalate to `claude-advisor` only under dotfiles
  `.claude/token-routing.md` § Escalation, item 2 (the same problem resisted two attempts after a codex verdict)'; no
  fourth trigger. Ship in the same KB PR as remainder item 7 (F1, `.claude/CLAUDE.md:40-42`)." And in `:946-947` change
  "V6 subsumed" → "V6 ruled subsumed (KB edit still owed, see § fable-orchestrator removal)".

### P6 — MEDIUM — #1383's "Blocked by" names an unnumbered "that ticket" and misses #1295, the open decision on the SAME module

- **Claim:** dotfiles #1383 § Blocked by: "Coordinate with the Phase 11 codex-invocation class fix ('ONE codex entry
  point'). If that ticket already owns the move, close this as a duplicate of it." There is no such ticket: the class
  fix is still `/to-spec` → `/to-tickets` pending (`task_plan.md:916`). A fresh session cannot evaluate "if that ticket
  already owns the move". Meanwhile dotfiles **#1295** (OPEN, "Place the codex entry-point rework in the Phase 10
  order") is the open decision about reworking `sdlc_team.py` itself (RESEARCH mode, typed `role`, role-derived model,
  claudex features) — the very module #1383 proposes to move into `kb_setup`. #1383 does not mention it, so the move
  could be scheduled before/independently of the rework and port a module that is about to be redesigned (the ticket's
  own principle: "Port a working entry point, not a broken one").
- **Evidence:** #1383 body (fetched 2026-09-25); `task_plan.md:916`; `gh issue view 1295` (OPEN, body cites
  `codex-entrypoint-design-2026-09-22.md`); GitHub search `repo:ray-manaloto/dotfiles is:open "codex entry point"` → 6
  hits incl. #1295 and #1383 — no class-fix ticket.
- **Control arm:** the same search returned #1383 itself and #1293/#1310 (known-present), so the absence of a
  class-fix ticket is a real absence, not a blind query.
- **Disposition: FIX-NOW** (issue body edit, anchor-asserted). Replace #1383's second "Blocked by" bullet with:
  "- The Phase 11 codex-invocation class fix (`task_plan.md` § Current Phase, Phase 11 item 3) has **no ticket yet**
  (2026-09-25). When its `/to-tickets` runs, decide there whether it absorbs this move; until then this ticket stands.
  - #1295 (OPEN) — decides where the `sdlc_team.py` rework (typed `role`, RESEARCH mode, role-derived model) lands.
  Move the module AFTER that rework is placed, or move-then-rework in one ticket; do not port a module that #1295 is
  about to redesign."

### P7 — LOW — #1383 and #1384 are filed but scheduled nowhere; the plan says only "filed"

- **Claim:** `task_plan.md:789` ("V8: DONE 2026-09-25 — filed #1383 (a) + #1384 (b)") is the only mention of either
  ticket in the plan. Neither appears in the Current Phase order, the 2026-09-24/25 remainder, or Phase 11. #1384 is
  "Blocked by: None", so a fresh session reading "V8 DONE" may either ignore it indefinitely or start it out of order.
  #1384's "What to build" also opens with "Agree on the shared region (the routing table, spec contract, review tiers,
  advisor escalation)" — a design decision across two rule-synced repos with no stated decider; `task_plan.md:859-861`
  (eager-rules trim) says the SAME class of change ("touches rule-synced files in both repos") "Needs `/grilling` →
  `/to-spec`".
- **Evidence:** `grep -n 1383 task_plan.md` → only `:789` (same for 1384); #1384 body.
- **Control arm:** `grep -n 1362 task_plan.md` finds several scheduled references (e.g. `:940`, `:951`), so the grep
  finds scheduled tickets when they exist.
- **Disposition: PLAN.** Append to § "2026-09-24/25 session remainder": "24. V8 follow-ups (filed 2026-09-25, not yet
  ordered): #1383 (sdlc_team → `kb_setup`) — blocked on #1362 and on #1295's placement; order it with Phase 11's codex
  class fix. #1384 (rule-sync doctrine content-hash axis) — Ray decides the shared region first via `/grilling` (which
  sections are shared, which repo is canonical) → `/to-spec`; it touches rule-synced skills in both repos, so bundle it
  with item 18's rule trim rather than shipping separately." Also add to #1384 § Blocked by: "Needs a `/grilling` ruling
  (Ray) on the shared region's contents and canonical repo."

### P8 — LOW — #1318 is closed, but the plan still lists "close #1318" as owed, and the close leaves a library gap ownerless

- **Claim:** (a) `task_plan.md:784-786` "Tracker hygiene: … Still owed: close #1318 citing the doctor `removed-plugins`
  7→0 arm after the claudex-loop removal" — #1318 was closed 2026-09-26T02:17:56Z (2026-09-25 CDT); the same section's
  `:780` says "#1318 CLOSED", so the section contradicts itself. (b) The #1318 closing comment does not map its
  acceptance criteria: AC1 ("doctor check fails BEFORE and passes AFTER, both runs recorded") is answered only by
  reference to "the 2026-09-24 7→0 arm", and AC3 ("No other project's codex lane was running when the codex-side config
  was edited (checked, not assumed)") is not mentioned — the claudex-loop `--apply` edited `~/.codex/config.toml` again
  (transcript ordinal 897 copies it, then applies) with no lane check in the transcript between the approval
  (ordinal 893) and the apply. All three checkboxes stay unticked on a closed issue. (c) The comment says the empty
  `~/.codex/plugins/cache/claudex-loop` "was left behind by the library and removed by hand (rmdir)" — a
  `plugin-remove` defect (`remove-orphan-cache` reported "removed 0", `findings.md:2111`) with no issue, no task_plan
  line, and no owner. `findings.md` is gitignored, so this is the only durable record and it is in a closed issue.
- **Evidence:** `task_plan.md:780,784-786`; `gh issue view 1318 --json comments`; transcript ordinals 893, 897, 940
  (`rmdir`), 953 (`findings.md` append).
- **Control arm:** transcript scan of every assistant `tool_use` for `pgrep|ps -|codex exec|lane` found `ps -Ao` probes
  only at ordinals 1115/1153/1190 (the later "something is stuck" diagnosis) — so the scan sees process probes when
  they exist, and none precede ordinal 897. `grep -n -i 'orphan-cache\|cache parent' task_plan.md` → 0, while the
  same grep over `findings.md` → 1 (`:2111`). GitHub search `repo:ray-manaloto/dotfiles remove-orphan-cache` → 12
  fuzzy hits, none a plugin-remove orphan-cache ticket (control: `plugin-remove` → 97).
- **Disposition: FIX-NOW + PLAN.** (a) Replace `task_plan.md:784-786` with: "- **Tracker hygiene:** #1311-#1317 CLOSED
  2026-09-25b citing dotfiles#1363. #1318 CLOSED 2026-09-25 (claudex-loop removal). Keep #1310 open until #1319
  closes." (b) Add a comment to #1318: "AC mapping: AC1 — doctor `removed-plugins` 7→0 recorded 2026-09-24
  (`fable-orchestrator-removal-session-2026-09-24.md`), re-confirmed 0 on 2026-09-25 after claudex-loop. AC2 —
  `plugin-health` rc=0. AC3 — the claudex-loop `--apply` was not preceded by an explicit other-project lane check;
  codex was at its usage limit account-wide until 2026-09-30, so no codex lane could run (state that as the basis, not
  as a check)." — or, if Ray wants AC3 held strictly, reopen until a lane check is recorded. (c) File the orphan-cache
  gap (via `issue-filer`): "plugin-remove: `remove-orphan-cache` leaves an empty codex marketplace parent
  (`~/.codex/plugins/cache/<marketplace>/`) and reports 'removed 0'; `plugin-inventory` cannot see it" and add it as
  remainder item 4b next to #1372 (same module).

### P9 — LOW — F2 says "after the branches land" (which branches?) and the section's bare IDs are ambiguous across audits

- **Claim:** `task_plan.md:792` "**F2:** after the branches land, run `mise run graphify-rebuild` and require
  `mise run graphify-health` rc=0 (2026-09-25: rc=3, built `9c624360`)". The branches are the 2026-09-24
  `chore/remove-fable-orchestrator` pair, which landed as dotfiles#1363 / knowledge-base#811 — so F2 is runnable NOW,
  but a fresh reader cannot tell that and may wait. The section intro (`:771`) says only "PLAN items from the §1c
  audits", and at least two 2026-09-24 audits have an F2 (`session-audit-dismissed-errors-2026-09-24.md:17` — the
  graph; `session-audit-missing-requests-2026-09-24.md:37` — step 5 results). V4/V6/V8 likewise come from
  `session-audit-vagueness-2026-09-24.md` without saying so.
- **Evidence:** `task_plan.md:771,789,792`; the two F2 headings above.
- **Control arm:** `grep -n 'F2' session-audit-*2026-09-24*.md` returned both headings (so the ambiguity is measured,
  not assumed); `graphify-rebuild` appears in `session-audit-dismissed-errors-2026-09-24.md`, identifying the right F2.
- **Disposition: FIX-NOW.** Replace `:792` with: "- **F2** (`session-audit-dismissed-errors-2026-09-24.md` F2): the
  removal branches have landed (dotfiles#1363, knowledge-base#811), so run `mise run graphify-rebuild` now and require
  `mise run graphify-health` rc=0 (last measured 2026-09-25: rc=3, built `9c624360`)." And `:771` → "PLAN items from
  the §1c audits (V* = `session-audit-vagueness-2026-09-24.md`, F2 = `session-audit-dismissed-errors-2026-09-24.md`):".

### P10 — MEDIUM — remainder item 10 says claudex-loop "satisfies this", but claudex-loop was a CODEX plugin and item 10's D2 half is the CLAUDE user-scope case

- **Claim:** `task_plan.md:825-827` "10. (F5) `plugin-remove --apply` has never run against a real plugin; do one
  supervised real removal of a disposable plugin (and the user-scope marketplace case D2) with the dry-run plan reviewed
  first. (claudex-loop satisfies this; see the fable section.)" D2 is "`--scope user` runs when `~/.claude/settings.json`
  declares the marketplace" (`opus-fallback-implementer-plugin-remove-r3-2026-09-25.md:127`) — a Claude-side,
  user-scope path. claudex-loop was a codex plugin (transcript ordinal 891: "claudex-loop is a codex plugin …, not a
  Claude one"; its 4 steps were cache backup, native codex plugin + marketplace removal, orphan cache). So the real
  `--apply` covered the codex path only; D2 has still never run live. The parenthetical reads as "item 10 done", and
  item 10 is not marked either way.
- **Evidence:** `task_plan.md:780-783,825-827`; the r3 report `:127`; #1318 closing comment (step list).
- **Control arm:** the #1318 close comment lists its 4 steps and none is a Claude `--scope user` step; the r3 report's
  D2 line names `~/.claude/settings.json`, so the distinction is in the sources, not inferred.
- **Disposition: FIX-NOW.** Replace `task_plan.md:825-827` with: "10. (F5) `plugin-remove --apply`: the CODEX path
  ran live on 2026-09-25 (claudex-loop, rc=0, inventory 3→0; #1318 close comment). Still owed: one supervised real
  removal on the CLAUDE side that exercises D2 (`--scope user`, marketplace declared in `~/.claude/settings.json`), dry
  run reviewed first. Needs a disposable Claude plugin — ask Ray which."

### P11 — LOW — the #1319 live-arm reports carry raw extraction markers and omit the premises they verify

- **Claim:** (a) `1319-live-arm-knowledge-base-2026-09-25.md:21,40,48,50` use separators from the extraction script:
  "===== agent-a8d386ef8146c95f4.jsonl None", "=====RESULT 6", "=====RESULT 3". "None" reads like a failed field
  (it is Python's repr of a missing value), and "RESULT 6/3" are undefined (they are the parent `result` records'
  `num_turns`). Lines 56-57 are empty lines before the prompt fence. (b) `1319-live-arm-premise-verifier-dotfiles-2026-09-25.md`
  records the verdicts for P1-P4 but not the premise TEXT (the KB report quotes its whole prompt, § Prompt); a reader
  cannot see what P2 ("matches the tool set this lane was actually given") or P4 asserted, or that P3's control was
  `zq-absent-arm-4417`, without opening the transcript. (c) The advisor report's "Could not verify" probe
  (`1319-live-arm-claude-advisor-dotfiles-2026-09-25.md:22`) elides the URL (`…/v2.1.282/…`), so it is not runnable,
  and no plan line owns it. These markers are coordinator-authored scaffolding, not verbatim agent text, so they can
  be edited without violating `agent-report-persistence.md` rule 4.
- **Evidence:** the three report files at the cited lines; transcript ordinal 440 (the `kb-arms-extract` python that
  printed `'=====', ids[tool_use_id]` — `None` is a failed id→type lookup — and the `result` records' `num_turns`), and
  ordinal 471 (the `printf` that assembled the report from that extract).
- **Control arm:** N/A (textual). The "None"/"RESULT n" origin was confirmed from the extract command at ordinal 440.
- **Disposition: FIX-NOW.** (a) Replace line 21 with "### premise-verifier — final assistant text of
  `agent-a8d386ef8146c95f4.jsonl`", line 40 with "### claude-advisor — final assistant text of
  `agent-ad9f39535ec66de0f.jsonl`", line 48 with "### Headless parent — first `result` record (num_turns=6; NOT
  evidence)", line 50 with "### Headless parent — second `result` record (num_turns=3; NOT evidence)"; drop the blank
  lines 56-57. (b) Add to the dotfiles premise-verifier report a "## Premises sent (verbatim)" section copied from the
  Agent call's `prompt` in the main transcript. (c) Under the advisor report's verbatim block add a coordinator note:
  "Not pursued: Ray's 2026-09-25 ruling keeps `running != latest` enforcing regardless of whether 2.1.282→2.1.283
  changed `claude-code.d.ts`, so the probe does not bear on any open decision."

### P12 — LOW — OthmanAdi/planning-with-files#296 offers a PR on Ray's behalf, with no follow-up owner

- **Claim:** #296 ends "Offer: Happy to send a PR: the flag, a test for each arm …, plus the doc line. Tell me if
  you'd prefer a different shape." The plan records only "DONE 2026-09-25 (… filed OthmanAdi/planning-with-files#296)"
  (`task_plan.md:737,944`). If the maintainer accepts the offer, nothing in the plan says who writes the PR, when, or
  where the local workaround ("clear `.active_plan`, attest, restore", racy per the issue) is documented meanwhile —
  and it bears directly on Phase 11's first priority (#1351, pwf current-workflow migration), where the root roadmap
  and a slug plan will coexist.
- **Evidence:** #296 body; `grep -n 296 task_plan.md` → `:737`, `:944` (both "DONE … filed") plus `:1230` (an unrelated
  `hooks.md:296` line anchor).
- **Control arm:** the same grep found both known DONE lines, so a follow-up line would have been found if present.
- **Disposition: PLAN.** Add under Phase 11's pwf migration addendum: "- Upstream ask OthmanAdi/planning-with-files#296
  (`attest-plan.sh --target root|<plan-id>`), filed 2026-09-25 with an offer to send the PR. Owner: the #1351 migration
  lane. Check #296 at the start of #1351 work; if accepted, send the PR (the four arms listed in #296) before relying on
  root-roadmap re-attestation; until then, re-attest the root plan only with no slug plan selected, and record that
  constraint in the #1351 spec."

## Summary

| # | Sev | Surface | One line | Disposition |
|---|---|---|---|---|
| P1 | MED | `task_plan.md:879-881` | 23(f) prescribes "not current"; "failed a required check" shipped; not marked DONE | FIX-NOW |
| P2 | MED | `task_plan.md:767,948-951` vs #1319 / receipt | plan's #1319 next step drops verify/rule-sync/plugin-health/grep/#1293 arms, adds an unrequired arm, keeps done half as "Now" | FIX-NOW |
| P3 | LOW | `docs/receipts/1319.md:16`, advisor report | dangling "F13" (working tree half-fixed); name the audit file; record shipped wording | FIX-NOW |
| P4 | MED | KB#794 close ↔ `review.py:445` ↔ #750 | AC1 handed to #750, code says "separate, later ticket" (no number) | PLAN (one AskUserQuestion) |
| P5 | MED | `task_plan.md:774-775,946-947` | "V6 subsumed" reads DONE; KB `.claude/CLAUDE.md:33` edit still owed, unscheduled | FIX-NOW |
| P6 | MED | #1383 Blocked by | "that ticket" has no number; misses #1295 (same module) | FIX-NOW (issue edit) |
| P7 | LOW | #1383/#1384 in plan | filed but unordered; #1384 region decision has no decider | PLAN (#1384 needs /grilling → /to-spec) |
| P8 | LOW | `task_plan.md:784-786`, #1318 close | "close #1318" still owed though closed; ACs unmapped (AC3 unchecked); orphan-cache gap ownerless | FIX-NOW + PLAN (file issue) |
| P9 | LOW | `task_plan.md:771,792` | "after the branches land" (landed); bare F2/V* IDs ambiguous across audits | FIX-NOW |
| P10 | MED | `task_plan.md:825-827` | "claudex-loop satisfies this" — codex path only; Claude D2 `--scope user` never run live | FIX-NOW |
| P11 | LOW | three `1319-live-arm-*` reports | extraction markers ("None", "RESULT 6"), missing premise text, elided probe URL | FIX-NOW |
| P12 | LOW | pwf#296 | PR offered upstream; no owner/follow-up in plan; bears on #1351 | PLAN |

Worst: **P2** — a fresh session executing `task_plan.md` Current Phase item 2 as written would either re-run the four
Claude arms or close #1319 without its grep/verify arms and the #1293 comment, i.e. with AC1/AC3 unmet. P4 is the
subtlest: a closed issue's AC transferred to a ticket whose own code comment disowns it.

Clean (checked, no finding): the `register.ts` lead change itself and its four harness regex updates (both mirrors
updated; `claude_doctor.py:509-518` confirms `invalid` covers method/clean-marker findings and the finding text
carries the repair command `claude install latest`); knowledge-base `cb08d898..6957b0ac` (two identical stopgap
pointer edits, accurate: #1383 is open and names the retirement); #1384's line anchors (`SKILL.md:138`,
orchestrator-routing 150 lines, `rule-sync.toml:51-56`) all verified; #1383's audit anchor
`session-audit-vagueness-2026-09-24.md:32` verified; pwf#296's `v3.20.8` exists in the local plugin cache.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — diff `f7245695..e38ce9cb`; issues #1318 (close comment), #1319, #1383, #1384, #1295, #1362 refs; search API probes
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — diff `cb08d898..6957b0ac`; issues #794 (close comment), #750; `review.py`, `cli.py`, `.claude/CLAUDE.md`, kb-review/orchestrator-routing skills read
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — issue #296 body
