# Session audit — vague or misinterpretable docs/plans (Brief P, session 2026-09-25b)

Reviewer: read-only Brief P lane. Session under review: `1df2b6a7-b103-4a4c-84cf-57d8842b7af2`.
Status: COMPLETE — 16 findings (P1-P16).


## Findings

### Scope actually read (probe log)

- dotfiles `git diff --stat 3397f521..origin/main`: `.claude/types/README.md`, `.claude/types/claude-code.d.ts` (generated, skipped),
  `docs/research/kb/reports/agents/claude-doctor-2026-09-25.md`, `schemas/sources.toml`, `mise.toml`/`mise.lock` (renovate bump only).
- knowledge-base `git diff d229399f..cb08d898`: `python/src/kb_setup/model_limits.py` (+5-line comment), `docs/model-limits/snapshot.json`,
  `mise.toml` (antigravity-cli 1.2.2→1.2.11), `mise.lock`.
- #283 comment 5840614053 (`gh api`, created 2026-09-25T22:36:54Z).
- `task_plan.md` § "fable-orchestrator removal", § "2026-09-24/25 session remainder", § "2026-09-25 step 0", § Current Phase, § Next Step.
  ⚠️ **The coordinator edited `task_plan.md` while this audit ran** (sha `47c824f0…` at 19:0x → `46a48482…`, mtime 19:18) and
  modified `claude-doctor-2026-09-25.md` + `docs/agents/goal-history.md` in the working tree of branch `docs/session-2026-09-25b-handoff`.
  Findings below are graded against the CURRENT working tree (19:18 state); ones the coordinator already fixed are marked.
- Transcript `1df2b6a7….jsonl` (1,482 lines): Edit/Write targets enumerated with `jq` (control: it lists README.md and model_limits.py,
  so the probe sees edits); every AskUserQuestion + answer extracted.

### P1 — HIGH — `task_plan.md` still says Phase 10 step 0 both "runs NOW" and "resumes after Phase 11", and the tracker agrees with neither

- **Claim.** § Current Phase carries two contradictory statements about the same unit of work, three lines apart, and a third in
  Phase 11's header. The work itself was largely DONE on 2026-09-24, yet every ticket of it is still OPEN, so a fresh session
  reading `gh issue list` would re-implement landed work, and one reading `task_plan.md:886` would wait until after Phase 11.
- **Evidence.** `task_plan.md:886` "Phase 10 step 0 (spec dotfiles#1310, KB#793 first) resumes after Phase 11." vs
  `task_plan.md:891` "Phase 10 step 0 (#1310: #1311-#1319, KB #793-#797) runs NOW, ahead of Phase 11." vs `task_plan.md:514`
  (Phase 11) "Runs BEFORE Phase 10 step 0 `/implement`". goal-history iteration 036 "Current goal" (working tree) says
  "…then Phase 11 in its ruled order, then Phase 10" — which reads as the whole Phase 10 including step 0.
  Tracker: `gh issue view` → #1310, #1311, #1312, #1313, #1314, #1315, #1316, #1317, #1318, #1319 all **OPEN**, although
  PR #1363 (MERGED 2026-09-24T10:08:33Z) lists "#1311-#1315", "(#1316)", "(#1317)" in its body (no `Closes` keyword), and
  `task_plan.md:900` says "#1318 is DONE on this Mac". `claude-advisor` and `premise-verifier` (#1314's deliverable) are live agent types.
- **Control arm.** `gh issue view 1053 --json state` → `CLOSED`, so the state probe can return the other answer.
- **Disposition: FIX-NOW** (coordinator; `task_plan.md` is coordinator-only). Exact rewrite of `task_plan.md:886`:
  > Phase 10 step 0 (#1310) EXECUTED EARLY on 2026-09-24 (see the "SUPERSEDED 2026-09-24" paragraph below): #1311-#1317 landed
  > in dotfiles#1363, #1318 done on this Mac; only #1319 (live arms) remains and is carried by § "fable-orchestrator removal".
  > The REST of Phase 10 resumes after Phase 11.

  and `task_plan.md:514` "Runs BEFORE Phase 10 step 0 `/implement`" → "Runs BEFORE the rest of Phase 10 (its step 0 ran early,
  2026-09-24)". Plus **PLAN** (GitHub mutation, needs Ray's go or an `issue-filer` run with `FILE ISSUES: yes`): add to the fable
  section "- **Tracker hygiene:** close #1311-#1317 with a comment citing dotfiles#1363 (`15662741`…), close #1318 citing the
  doctor `removed-plugins` 7→0 arm after the claudex-loop removal; keep #1310 open until #1319 closes." No /grilling needed.

### P2 — MEDIUM — the fable section contradicts itself: header says ACTIVE, first sentence says QUEUED second; V6 is both ruled and open

- **Claim.** The coordinator's 19:18 edit updated the header and added a Rulings block but left the stale lines under it.
- **Evidence.** `task_plan.md:767` header "— ACTIVE, NEXT SESSION" vs `task_plan.md:769` "The plan-pointer moved to "## 2026-09-25
  step 0" on 2026-09-25; this section is QUEUED second." Rulings block: "**V6 → SUBSUMED by trigger 2.**" vs `task_plan.md:783`
  "**Ruling for Ray (V6):** is the KB lane-preference line's … a fourth `claude-advisor` trigger, or is it subsumed by trigger 2?"
  And `task_plan.md:907` (Current Phase "Next, in order" 1) "Ray answers the report's REMAINING open questions: KB#794 CLI-default;
  `kb-tool-review` artifact mode; remove vs disable claudex-loop." — all three were answered by the 2026-09-25b rulings.
  `docs/agents/plan-pointer.json` still reads `"active_phase":"2026-09-25 step 0 — ACTIVE, NEXT SESSION…"`, `plan_sha256` `47c824f0…`
  (current file `46a48482…`).
- **Control arm.** The same `grep -n` located the new "Rulings (Ray, 2026-09-25b" block, so the probe sees both old and new text.
- **Disposition: FIX-NOW.** Replace `:769` with: "Step 0 landed 2026-09-25 (#1378, KB#814); this section is ACTIVE. Order: the
  'Next, in order' list under § Current Phase." Delete the `:783-785` "Ruling for Ray (V6)" bullet (the Rulings block now carries
  V6). Replace `:907-908` item 1 with: "1. DONE 2026-09-25b — rulings recorded in § fable-orchestrator removal: V6 subsumed, KB#794
  close, `kb-tool-review` artifact mode kept, claudex-loop removed fully." Then re-record `plan-pointer.json` (the handoff's
  pointer step) and remind Ray: `! mise run plan-attest`.

### P3 — MEDIUM — "#1319 live arms" next step does not say which arms are blocked on codex until 2026-09-30

- **Claim.** `task_plan.md:909-911` orders "spawn `premise-verifier` and `claude-advisor` in both repos, run `kb-codex-implementer`
  once, run `kb-tool-review` to its Review phase" as one step. The new ruling says the `kb-tool-review` run "Needs codex — usage
  limit until 2026-09-30"; `kb-codex-implementer` is a codex lane by name, so it is blocked too. A fresh session will either
  stall the whole item or burn a turn discovering the block.
- **Evidence.** `task_plan.md:777-779` ("Needs codex — usage limit until 2026-09-30"); handoff `.agent/plans/session-2026-09-25.md`
  "Codex: usage limit until 2026-09-30 4:05 PM CDT".
- **Control arm.** N/A (textual); the codex block is recorded in two independent places above.
- **Disposition: FIX-NOW.** Rewrite item 2 as: "2. #1319 live arms. **Now (Claude-only):** spawn `premise-verifier` and
  `claude-advisor` once in each repo and record rc + transcript path. **After 2026-09-30 4:05 PM CDT (codex):** run
  `kb-codex-implementer` once and one `kb-tool-review` to its Review phase (doubles as the artifact-mode proof and KB#793's arm).
  The sdlc-team arm waits on #1362."

### P4 — MEDIUM — the claudex-loop ruling hands a raw removal command that bypasses the dry-run-first skill it names

- **Claim.** `task_plan.md:780` "**claudex-loop → REMOVE fully:** `mise exec -- codex plugin remove claudex-loop@claudex-loop` plus
  its marketplace, then `mise run doctor` and `plugin-inventory` … (use the `plugin-removal` skill)". The skill's contract is
  "dry-run-first" (`.claude/skills/plugin-removal/SKILL.md:3`) with `mise run plugin-remove -- <sel> --apply` as the mutating step
  (`:47`); a reader who executes the first backticked command skips the inventory and plan. It also misses that this is the
  real-plugin `--apply` that remainder item 10 (`task_plan.md` "(F5) `plugin-remove --apply` has never run against a real plugin")
  asks for — two items, one action. The selector `claudex-loop@claudex-loop` is unverified in the plan (not probed here:
  reading `~/.codex/config.toml` is barred by secrets rule 8).
- **Control arm.** `grep -n 'dry-run\|--apply'` on the SKILL returned the lines cited; the same grep for `codex plugin remove`
  returned 0 there, i.e. the skill does not prescribe the raw form.
- **Disposition: FIX-NOW.** Rewrite `:780-781` as: "**claudex-loop → REMOVE fully** via the `plugin-removal` skill: `mise run
  plugin-inventory -- <selector>` (confirm the exact `name@marketplace` first), `mise run plugin-remove -- <selector>` (dry run;
  review the plan), then `… --apply`; confirm with `mise run doctor` + a second `plugin-inventory` showing zero residue. This is
  also remainder item 10's first supervised real `--apply`." In remainder item 10 append "(claudex-loop satisfies this; see the
  fable section)".

### P5 — MEDIUM — remainder items cite audit findings by bare F-number, and this session's "-25b" audits reuse the same numbers

- **Claim.** `task_plan.md:827` "(vagueness F12, code half)", `:830` "(dismissed F1)", `:833` "(dismissed F2)", `:836` "(dismissed F4 +
  F5 + F6 …)", `:841` "(dismissed, repeats)" name no file. Item 7 (`:809-812`) and item 3 (`:800-802`) DO name theirs
  (`session-audit-missing-requests-2026-09-25.md` F1; `session-audit-dismissed-errors-2026-09-25.md` F3). This session now writes
  `session-audit-{dismissed-errors,missing-requests,vagueness}-2026-09-25b.md` (see `git status`), each with its own F1…/P1…
  numbering, so "dismissed F1" has two candidate referents from the next session on.
- **Evidence.** `git status --short` lists the four `-2026-09-25b.md` audit files untracked beside the `-2026-09-25.md` set.
- **Control arm.** The same grep found item 3's fully-qualified citation, so the probe distinguishes qualified from bare.
- **Disposition: FIX-NOW.** Qualify each: `:827` "(`session-audit-vagueness-2026-09-25.md` F12, code half)"; `:830`
  "(`session-audit-dismissed-errors-2026-09-25.md` F1)"; `:833` "(… F2)"; `:836` "(… F4 + F5 + F6, orchestration contract)";
  `:841` "(`session-audit-dismissed-errors-2026-09-25.md`, repeats)". Brief text for future sessions: "cite a finding as
  `<report filename> <ID>`, never a bare ID".

### P6 — MEDIUM — item 11 points at an unnamed gitignored file with undefined Q-IDs; Q6 has no action and is really a Ray ruling

- **Claim.** `task_plan.md:824-826` "(F7) Carried from the 2026-09-24 ship session, tracked only in a gitignored file: Q6 `eval --live`
  has no live case left; Q7 …; Q8 …". The file is not named, and Q6 states a fact, not a step. The source file frames Q6 as a
  three-way question for Ray, and dotfiles #1311 "Retire the eval --live plugin doctor" (OPEN) is the ticket that already owns it.
- **Evidence.** `.agent/plans/ship-session-results-2026-09-24.md:47` "Q6 (Greptile #2 on KB#811): `kb-setup eval --live` still
  accepted but no live case exists … Retire `--live`, make it say "0 live cases", or add a repo-owned live lane probe?";
  `:48` Q7 (unique `laneRoot` per run + explicit `method.txt`); `:31` Q8 (6 CodeRabbit comments on KB#811). `gh issue view 1311`
  → OPEN "Retire the eval --live plugin doctor".
- **Control arm.** `grep -ln laneRoot .agent/plans/*.md` returned exactly one file (so the source is unique, not a guess).
- **Disposition: FIX-NOW.** Rewrite item 11: "11. (`session-audit-…-2026-09-25.md` F7) From
  `.agent/plans/ship-session-results-2026-09-24.md` (gitignored, this Mac only): **Q6 — ruling for Ray:** `kb-setup eval --live`
  has no live case since KB#811; retire the flag, make it print "0 live cases", or add a repo-owned live probe (ticket: dotfiles #1311
  / KB counterpart). **Q7:** `kb-tool-review.js` — allocate a per-run `laneRoot` and require an explicit `method.txt`
  (fold into the #1319 `kb-tool-review` live run). **Q8:** disposition knowledge-base #811's 6 CodeRabbit comments (reply per comment).
  **Trusted configs:** remove the 3 pytest-path entries from mise's trusted-configs list." Promote the Q-section of that file into
  a tracked report if it is to outlive this Mac (`agent-artifact-conventions.md` "Promote anything a rule … will cite").

### P7 — MEDIUM — item 15(b)'s "write the report via a Bash heredoc" fallback, as worded, also routes around `branch_guard`

- **Claim.** `task_plan.md:838-839` proposes adding to the SubagentStart contract and `agent-report-persistence.md` rule 2: "if Write
  is refused ('Subagents should return findings as text'), write the report via a Bash heredoc". A delegate that reads it as
  "Write refused → heredoc" will also apply it to a `branch_guard` deny on `main`, which `do-not.md` #9 says is deliberate ("The
  gate is on the *write*, not the commit"). The instruction as drafted conflicts with a rule unless it is scoped to the one refusal text.
- **Evidence.** `task_plan.md:838`; `.claude/rules/do-not.md` #9 (PreToolUse `branch_guard` denying Edit/Write on the default branch).
- **Control arm.** N/A (textual). Note: this lane's own Write succeeded because the checkout is on `docs/session-2026-09-25b-handoff`
  (`git branch --show-current`), not `main`, so it did not exercise the guard.
- **Disposition: PLAN** (text change to an eager rule + selfcheck tokens; no /grilling). Exact wording for the eventual edit:
  "If the Write TOOL itself is refused with 'Subagents should return findings as text', write the report with a Bash heredoc to
  the SAME path. Never use a heredoc to get past any other deny — a `branch_guard` or permission-rule deny means stop and report."

### P8 — MEDIUM — the claude-code pin has no documented bump path: `sources.toml` forbids the only edit that bumps it, and the README says the refresh task can do it

- **Claim.** For `claude-code`, `schemas/sources.toml`'s `version` field IS the pin (no mise `[tools]` entry), and
  `schema-vendor-refresh` only re-downloads AT that version — it never bumps it. Yet `schemas/sources.toml:4-7` says "Never
  hand-edit the `version`/`source`/`sha256` fields; run `mise run schema-vendor-refresh`", and `.claude/types/README.md`
  (Metadata ⚠️ paragraph) says "edit the two together (or let `mise run schema-vendor-refresh` do it)". This session bumped it
  the only way that works — hand-edit `version` + `source`, then refresh — which the header forbids. The 37-line claude-code comment
  block that likely explained this was deleted by the refresh bot's #1364 and is still gone (`task_plan.md` remainder item 17).
- **Evidence.** `python/src/dotfiles_setup/schema_vendor.py:111-120` (`_PIN_RESOLVERS` has no `claude-code`),
  `:191-193` and `:407-411` ("the vendored `version` in sources.toml IS the pin"); `:249-254` (URL built from that version).
  Doctor report row 16: "`version` + `source` tag bumped, … `mise run schema-vendor-refresh` rc=0". `grep -c '^#'` on
  `schemas/sources.toml` = 14 both at `3397f521` and now (the block was not restored).
- **Control arm.** `_PIN_RESOLVERS` DOES carry `typos`, `ruff`, `mise`, `codex`, so the probe would have shown a claude-code resolver
  had one existed.
- **Disposition: FIX-NOW** (tracked docs, one small dotfiles PR). README ⚠️ paragraph → "⚠️ **This line is a PIN, not prose.**
  `pin-parity.toml`'s `claude-code` entry requires it to equal `schemas/sources.toml`'s `version`. To bump: hand-edit BOTH to the new
  version (`sources.toml` `version`; `source` is rebuilt from it), then `mise run schema-vendor-refresh`, which re-downloads at that
  tag and rewrites `sha256`. The refresh task never bumps claude-code on its own — for this tool `sources.toml` is the pin."
  `sources.toml:4-7` → "Never hand-edit the `source`/`sha256` fields, nor `version` for a tool with a resolver in
  `schema_vendor._PIN_RESOLVERS`; `claude-code` has none, so its `version` IS its pin — edit it, then run `mise run
  schema-vendor-refresh`." (Put the explanation in the header, which the bot's rewrite preserves; item 17 shows it drops per-row comments.)

### P9 — MEDIUM — the #283 comment (and doctor row 11) names the wrong cross-repo constraint for the proposed trim

- **Claim.** The comment says "Any edit to `.claude/CLAUDE.md` is rule-synced byte-for-byte with knowledge-base, so a trim PR needs the
  KB half too." But the trim it proposes is to `.claude/rules/*.md`, and what actually binds those is `rule-sync.toml`'s `rules`
  list, matched **by stem** (presence, not bytes). Trim class 2 proposes turning `persistence-gate-retry.md` and
  `local-devcontainer-first.md` into skills — both stems are in that list, so deleting either rule fails `mise run rule-sync`
  (hard-fail in CI) unless `rule-sync.toml` is narrowed in the same program; `codex-sdlc-team.md` is NOT in the list, so it is
  dotfiles-only. And `rule-sync.toml`'s `lines` gate matches ONE line of `.claude/CLAUDE.md` "exactly modulo whitespace", not the
  file byte-for-byte. A reader planning the trim from the comment will look in the wrong place and be surprised by a red gate.
- **Evidence.** #283 comment 5840614053 (last paragraph); doctor report row 11 "Not edited in place: `.claude/CLAUDE.md` is rule-synced
  byte-for-byte with knowledge-base"; `rule-sync.toml` `rules = [...]` includes `"local-devcontainer-first"`,
  `"persistence-gate-retry"`, omits `codex-sdlc-team`; `rule-sync.toml` `lines` comment "matched exactly modulo whitespace".
  Also the comment's rule count checks out: 27 rule files, `paths:` in the first 5 lines only for `ci-local-parity.md` and
  `md-size-budgets.md` → 25 eager (re-derived here).
- **Control arm.** The stem list contains `zero-bash-logic` (a rule known to exist in both repos) and does NOT contain
  `codex-sdlc-team` — so the list discriminates.
- **Disposition: FIX-NOW** for the doctor report row 11 wording; **PLAN** for #283 (a GitHub comment is outward-facing — Ray's go or
  `issue-filer` with `FILE ISSUES: yes`). Exact follow-up comment for #283:
  > Correction to the comment above: the cross-repo constraint on this trim is `rule-sync.toml`'s `rules` list (matched by stem), not
  > `.claude/CLAUDE.md`. `persistence-gate-retry` and `local-devcontainer-first` are in that list, so moving either to a skill must
  > first remove it from knowledge-base and narrow `rule-sync.toml` (reverse of the widening order in its header), or `mise run
  > rule-sync` goes red. `codex-sdlc-team` is dotfiles-only. Only the one trigger line of `.claude/CLAUDE.md` is synced, modulo whitespace.

  Doctor row 11 → "Not edited in place: a trim changes the eager-rule set that `rule-sync.toml`'s `rules` list binds across both
  repos (by stem), and rules are `md_size_budget`-gated."

### P10 — LOW-MEDIUM — doctor report leaves four open ends with no owner and no plan line; one already has an issue

- **Claim.** Rows end in "not established" / "remains open" with nothing that carries them: row 5 "What created them is not
  established" (10 `source-command-memory-index-curation-skill-*` symlinks, 2026-09-11); row 12 "the graphify guard is ours, and no
  issue was searched for its latency, so that remains open"; row 14 antigravity-delegate description 1,789 > 1,536 chars, NOT-OURS
  with no upstream report; row 19 `.git/index.lock` "Origin not established". None appears in `task_plan.md`.
- **Evidence.** `grep -n 'graphify-hook-guard\|index.lock\|source-command-memory\|antigravity-delegate' task_plan.md` → one hit only,
  `:712` (an older M-3 note on the antigravity-delegate description, so row 14 IS carried; the other three are not). Issue search:
  **#536 "Hook latency: PreToolUse guards cost ~393ms median on every read; 17 timeouts in 3 days" (OPEN)** — its table's first row is
  `graphify-hook-guard.sh` PreToolUse. So row 12's "remains open" is wrong: the issue exists.
- **Control arm.** The same `task_plan.md` grep hit `:712`, so a zero for the other three terms is an absence, not a blind probe;
  `gh api /search/issues` returned #536 for the guard name.
- **Disposition: FIX-NOW** (doctor report). Row 12 disposition → "… the graphify guard is ours: re-measurement belongs on **#536**
  (post the 58-runs-over-2s figure there)." Row 5 → append "Origin open: PLAN item below." Row 19 → append "Origin open; recurrence
  → Brief M lead (see `session-audit-dismissed-errors-2026-09-25b.md`)." **PLAN** (append to the 2026-09-24/25 remainder):
  "18. (`session-audit-vagueness-2026-09-25b.md` P10) Doctor loose ends: (a) find what created the 10
  `~/.claude/skills/source-command-memory-index-curation-skill-*` symlinks on 2026-09-11 (they point into `~/.agents/skills/`) before
  they are recreated; (b) post the 2026-09-25 guard-latency numbers on #536." No /grilling.

### P11 — LOW — doctor rows 6-7 attribute ACCEPTED rulings to a gate that never asked about them

- **Claim.** Rows 6 (herdr) and 7 (25 unused project skills) say "**ACCEPTED** (Claude, at Ray's "clean up everything" gate)". The
  gate's question named only three actions — "removes the stale mise claude installs …, turns off 10 junk skills, and files one
  issue" — so Ray ruled on rows 1, 5, 11, not 6-7. The step-0 contract asks "ACCEPTED (reason + who ruled)"; the text reads as if Ray ruled.
- **Evidence.** Transcript AskUserQuestion "Apply the doctor cleanup? It removes the stale mise claude installs (the shim first on your
  PATH), turns off 10 junk skills, and files one issue…", options "Clean up everything (Recommended) | Let me pick | No, keep everything".
- **Control arm.** The same extraction shows the other step-0 questions verbatim, so herdr/project-skill text would have appeared if asked.
- **Disposition: FIX-NOW.** Rows 6-7 → "**ACCEPTED** (Claude's call, not put to Ray; the cleanup gate covered rows 1, 5, 11 only): …".
  Also note in row 11 that Ray approved "files one issue" and the outcome was a comment on the existing #283 (the step-0 DONE block
  already says so; the report should too).

### P12 — LOW — doctor report cites a branch commit and a gitignored plan as its anchors

- **Claim.** Row 16 "**FIXED** on branch `docs/claude-doctor-2026-09-25` `1b6cae72`" — this repo squash-merges, so once that branch is
  deleted the SHA is unreachable; the landed commit is `f68f943d` (#1378). The title "(task_plan.md § "2026-09-25 step 0", item 1)"
  cites a gitignored file no other clone can open.
- **Evidence.** `git branch -a --contains 1b6cae72` → only `docs/claude-doctor-2026-09-25` + its remote (still alive today).
  `agent-artifact-conventions.md`: "A citation that only one machine can open is not durable evidence."
- **Control arm.** `git cat-file -t 1b6cae72` → `commit` (resolves today, so the claim is about durability, not a typo).
- **Disposition: FIX-NOW.** Row 16 → "**FIXED** in dotfiles #1378 (squash `f68f943d`; branch commit `1b6cae72`)". Title →
  "# Built-in `/doctor` — 2026-09-25 (session-plan step 0, item 1; goal-history iteration `dotfiles-goal-20260925-036`)".

### P13 — LOW — the doctor addendum doesn't warn that row 5's backup predates the tier_pro keys

- **Claim.** Row 5's undo points at `~/.claude/settings.json.bak-doctor-2026-09-25`; the addendum then adds two keys to the same file
  AFTER that backup. Restoring the backup to undo row 5 would silently revert the Gemini 3.8 change too. Also: after the change the
  label `--tier pro` runs Gemini 3.8 **Flash** — anyone reading "pro tier" in older reports/briefs (e.g. Brief O's
  "`agy-delegate --tier pro`") will assume a Pro model.
- **Evidence.** Doctor report row 5 (backup path) and addendum bullet 1 (keys added "after the report shipped"); transcript L1256
  "`pro`: now Gemini 3.8 Flash (High), was 3.1 Pro (High)".
- **Control arm.** N/A (ordering of two recorded actions).
- **Disposition: FIX-NOW.** Append to addendum bullet 1: "Row 5's backup predates these keys — undo row 5 by deleting its 10
  `skillOverrides` keys, never by restoring the backup. From here on `--tier pro` is a label, not a model class: it runs 3.8 Flash (High)."

### P14 — LOW — KB `model_limits.py` comment says `claude-opus-5` "is still served" with no date or source, while the session found the docs dropped it

- **Claim.** `knowledge-base/python/src/kb_setup/model_limits.py:281-285`: "`claude-opus-5` stays listed because it is still served and
  remains graphify's claude-cli default". The same session found "The docs no longer list `claude-opus-5` or `claude-fable-5`"
  (AskUserQuestion, transcript) and only the credentialed Models API run resolved it. "Still served" is true as of one measurement
  and will silently go stale; the retirement consequence (graphify's `DEFAULT_MODEL = "claude-opus-5"`,
  `graphify_native_extract.py:268`, keeps extracting on a model absent from the docs) is not recorded anywhere as a trigger.
  "No caller's model changed" also misnames the list (it is the ids the registry asks about, not callers).
- **Evidence.** Snapshot `docs/model-limits/snapshot.json`: `"observed_at": "2026-09-25"`, `"source": "models-api"`, contains
  `"claude-opus-5"` (line 18). Ray's scope ruling: "Registry only: add opus-5-5 (Recommended)"; the declined option was "Registry +
  extraction default".
- **Control arm.** `grep -n '"claude-opus-5"'` on the snapshot → line 18 (present), while the ruling transcript shows the docs-sourced
  run resolved only 4 of 6 ids — two routes, two answers, both recorded.
- **Disposition: FIX-NOW** (KB, next KB branch; via `kb-review` → `kb-ship`). Rewrite the comment:
  "# Successor to `claude-opus-5`, added 2026-09-25 via `/claude-api migrate`, scoped (Ray) to this registry list only — no
  # model a caller USES changed. `claude-opus-5` stays listed: the Models API still returned it on 2026-09-25
  # (docs/model-limits/snapshot.json, source=models-api) although the public models page no longer lists it, and it is still
  # graphify's claude-cli default (`graphify_native_extract.DEFAULT_MODEL`). When the API stops returning it, move that default first."
  Optional **PLAN** (KB task plan, no /grilling): "When `kb-model-limits` stops resolving `claude-opus-5`, migrate
  `graphify_native_extract.DEFAULT_MODEL` (re-extract required: Opus 5.5 effort defaults differ)."

### P15 — LOW — KB `mise.toml` self-update note says "before this bump" about a bump two bumps ago

- **Claim.** `knowledge-base/mise.toml:235` "⚠️ `agy` also SELF-UPDATES IN PLACE: before this bump the binary inside the `1.1.5`
  install dir reported 1.1.10." sits directly above `antigravity-cli = "1.2.11"`; "this bump" now reads as the 1.2.2→1.2.11 bump.
  The recurrence (1.2.2 dir reported 1.2.11 on 2026-09-25) and its operational consequence — `kb-review-receipt` REFUSES until the
  pin is bumped (`review.py` `_reviewer_pin_gap`), and the fix is a pin bump, not a reinstall — are not written next to the pin.
- **Evidence.** KB `mise.toml` lines around `antigravity-cli`; `python/src/kb_setup/review.py:318-341` ("ASK THE BINARY … REFUSE,
  not warn"); transcript AskUserQuestion "Even the pinned `antigravity-cli/1.2.2/agy` reports 1.2.11 … Bump KB pin to 1.2.11 here".
- **Control arm.** N/A (textual).
- **Disposition: FIX-NOW** (KB, bundle with P14). Replace the sentence with: "⚠️ `agy` SELF-UPDATES IN PLACE: the `1.1.5` dir once
  reported 1.1.10, and on 2026-09-25 the `1.2.2` dir reported 1.2.11. `kb-review-receipt` then REFUSES (`review.py`
  `_reviewer_pin_gap`); the fix is `mise use antigravity-cli@<what agy --version prints>` + a scoped re-lock, matching dotfiles."

### P16 — LOW (pre-existing) — § Next Step says the Phase A-G list is ARCHIVED, then says "Execute in this operator-ratified order"

- **Claim.** `task_plan.md:73-74` "The 2026-09-15 Phase A-G order below is ARCHIVED" and `:82` "Execute in this operator-ratified
  order:" followed by `### Phase A — land PR #1128`. A codex lane or fresh session that jumps to `### Phase A` (it is the first `###`
  after `## Next Step`) will read an imperative. Not introduced this session, but it sits in the section this session edited.
- **Evidence.** `task_plan.md:73`, `:82`, `:84`.
- **Control arm.** N/A.
- **Disposition: FIX-NOW.** `:82` → "ARCHIVED — the order ratified on 2026-09-15, kept for its decisions; do NOT execute from here:".

## Already fixed by the coordinator during this audit (not findings)

- Step 0 header/“ACTIVE” wording: now "DONE 2026-09-25" (`task_plan.md:848`, `:73`, `:876`) with a DONE block citing #1378/`f68f943d`
  and KB#814/`cb08d898` — the brief's example stale statement is resolved in the working tree (plan-pointer.json still stale: P2).
- Doctor report missing the Gemini 3.8 / `tier_pro` change: an "Addendum — after the report shipped" now records both keys and the
  KB antigravity-cli bump (residual gap: P13).
- goal-history iteration `dotfiles-goal-20260925-036` added for the milestone.

## Summary of dispositions

| # | Sev | Disposition | Where |
|---|---|---|---|
| P1 | HIGH | FIX-NOW text + PLAN (close #1311-#1318) | task_plan :886, :514; GitHub |
| P2 | MED | FIX-NOW | task_plan :769, :783-785, :907; plan-pointer.json |
| P3 | MED | FIX-NOW | task_plan :909-911 |
| P4 | MED | FIX-NOW | task_plan :780, remainder item 10 |
| P5 | MED | FIX-NOW | task_plan :827-841 |
| P6 | MED | FIX-NOW | task_plan :824-826 |
| P7 | MED | PLAN | task_plan :838 (future rule text) |
| P8 | MED | FIX-NOW | `.claude/types/README.md`, `schemas/sources.toml:4-7` |
| P9 | MED | FIX-NOW (report) + PLAN (#283 comment) | doctor row 11; #283 |
| P10 | LOW-MED | FIX-NOW + PLAN item 18 | doctor rows 5/12/19; task_plan |
| P11 | LOW | FIX-NOW | doctor rows 6-7, 11 |
| P12 | LOW | FIX-NOW | doctor row 16, title |
| P13 | LOW | FIX-NOW | doctor addendum |
| P14 | LOW | FIX-NOW (KB) + optional PLAN | KB model_limits.py:281-285 |
| P15 | LOW | FIX-NOW (KB) | KB mise.toml |
| P16 | LOW | FIX-NOW | task_plan :82 |

None needs /grilling → /to-spec → /to-tickets; P1's issue closures and P9's #283 comment are GitHub mutations needing Ray's go.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issue states #1053 (control), #1310-#1319, #1362, #283; PR #1363 body; #283 comment 5840614053; issue search (#536 found).
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — local git diff `d229399f..cb08d898`; issue #793 state.
