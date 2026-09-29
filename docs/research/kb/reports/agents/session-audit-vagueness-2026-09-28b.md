# Session audit — Brief P: vague or misinterpretable docs/plans (2026-09-28, second session)

Session: cc5eebbf-2629-4ae9-a9ee-f6d38df8c8c0. Range: `fdd9ef53..HEAD` (`3ba79a67`).
Lane: Opus `general-purpose`, read-only except this report. Status: IN PROGRESS (appended incrementally).

Incident at start (self-reported): this lane's first `Write` targeted the brief's filename
`session-audit-vagueness-2026-09-28.md`, which is an already-committed report from the EARLIER 2026-09-28 session
(#1419), and overwrote it (-180/+3). Coordinator is restoring it from HEAD; this report moved to the `-28b` path.
That collision is itself finding V1 below.

## Findings

### V1 (HIGH) — `session-audit-<kind>-<date>` filename template collides across two sessions on one day
- Evidence: `.claude/skills/session-handoff/SKILL.md` §1c ("persisting its report under
  `docs/research/kb/reports/agents/session-audit-<kind>-<date>.md`"); same template in
  `docs/research/kb/reports/agents/session-handoff-briefs-q-s-2026-09-28.md:4`. `ls` shows
  `session-audit-{bugs,dismissed-errors,missing-requests,vagueness}-2026-09-28.md` already committed by the earlier
  session (#1419; bugs report scope is #1412 `6c9576f0`), so this session's lanes following the template overwrite
  them. It happened (this lane, -180/+3). Prior days already needed ad-hoc `b`/`c` suffixes (`-2026-09-25b`, `-25c`).
- Rewrite (both files): "persisting its report under
  `docs/research/kb/reports/agents/session-audit-<kind>-<date>[-letter].md` — use the same letter suffix as this
  session's handoff (`.agent/plans/session-<date>[-letter].md`); if the un-suffixed path already exists in git, you
  MUST suffix. Create the file with a new path only — never `Write` over an existing report."
- Disposition: FIX-NOW (doc) + PLAN (machine check: `handoff-check` or a `hook_guard`/`branch_guard` arm that denies
  `Write` to an existing tracked `docs/research/kb/reports/agents/*.md`, since those are verbatim records).

### V2 (HIGH) — "Briefs Q-S" collides with existing Briefs Q, R, S1-S4 in the file §1c tells you to read alongside
- Evidence: `.claude/skills/session-handoff/SKILL.md` §1c now says 'Briefs M-P in `…/session-2026-09-23d-agent-briefs.md`
  and "Briefs Q-S" in `…/session-handoff-briefs-q-s-2026-09-28.md`'. The 23d file ALREADY has `## Session-integrity
  review (Ray, 2026-09-23): Briefs M-Q` (:266), `### Brief Q — native codex installer` (:306), `## Brief R — Fable
  drafts /to-tickets` (:316), `## Briefs S1-S4 — … DELTA run` (:332). A lane told "reuse Brief Q/R/S" can pick the
  installer/to-tickets/delta brief. This lane's own dispatch was labelled "Brief P" and resolved correctly only because
  P is unique.
- Rewrite (§1c, both `.claude/` and `.agents/` copies): 'Their briefs: "Brief M"-"Brief P" under `### Brief M`..`### Brief
  P` in `…/session-2026-09-23d-agent-briefs.md` (that file's Brief Q, R and S1-S4 are UNRELATED — do not use them), and
  the three briefs named "process compliance", "repeat offenders", "retrieval misses" in
  `…/session-handoff-briefs-q-s-2026-09-28.md`. Address a brief by its review name (the table's first column), not its
  letter.' And in the q-s file retitle headings to `## Brief Q (process compliance)` etc. plus one line: "Not the
  Briefs Q/R/S of `session-2026-09-23d-agent-briefs.md`."
- Disposition: FIX-NOW.

### V3 (HIGH) — "reuse them" hands a fresh lane briefs with another session's hardcoded ids, bases and report paths
- Evidence: 23d `:266-305` hardcode session `a6750a24-…`, branch `docs/session-2026-09-23d-handoff`, base `219e83cc`,
  "Phase 11 addendum", and report paths ending `-2026-09-23.md`; §1c says only "reuse them". Brief O is literally
  "Diff by REF: base `219e83cc`". A literal reuse audits the wrong session or overwrites a 09-23 report (see V1).
- Rewrite (append to the §1c "reuse them" sentence): "Reuse their METHOD only. Substitute, in every brief: this
  session's id and transcript path, this session's commit range (see the bugs row), today's date plus the handoff's
  letter suffix in the report path, and this session's plan sections. Never reuse a brief's SHA, session id or
  report path."
- Disposition: FIX-NOW.

### V4 (HIGH) — §1c "bugs" row scope ("branch diff, base = merge-base with main") excludes everything this session already merged
- Evidence: this session merged #1421/#1423/#1426/#1427/#1429/#1433 to main; the current branch
  `docs/p2996-ref-currency-review` has merge-base `6e690e0b` = `origin/main`, so "branch diff by ref" is one docs
  commit (`3ba79a67`). The committed `session-audit-bugs-2026-09-28.md` is the EARLIER session's (#1412 `6c9576f0`),
  confirming the row is interpreted per-session in practice, not per-branch.
- Rewrite (bugs row, Question column): "cold review of every commit this session authored, by ref: each squash SHA
  that landed on `main` this session plus the handoff branch's diff against its merge-base. Skip a squash SHA only when
  the process-compliance review shows it already got the cross-family lens on that exact SHA."
- Disposition: FIX-NOW.

### V5 (MEDIUM) — §1c says "seven read-only reviews" but two rows instruct the reviewer to write
- Evidence: §1c header "run seven read-only reviews"; retrieval-misses row: "name the file that should carry it and add
  it there"; Q-S Brief S says "the exact line to add" (propose) — the row and its brief disagree about who edits.
  Every lane is "Opus `general-purpose`" (write-capable), so a lane following the row edits skills/rules in the
  coordinator's checkout mid-audit (the one-writer rule, `.claude/rules/goal-history.md`).
- Rewrite (retrieval-misses row): "…name the ONE file that should carry it and give the exact line to add; the
  coordinator applies it as a FIX-NOW." Same rewrite shape for repeat offenders: "propose the MACHINE check (file +
  rule/test text) …".
- Disposition: FIX-NOW.

### V6 (HIGH) — three sections of `task_plan.md` each claim to be "next session"; the Active order names none of the 2026-09-28 work
- Evidence (task_plan.md, read 2026-09-28): `:1002` p2996 ORDER "then the fix PR, next session after handoff; then the
  ship-gate `/grilling`"; `:1011-1012` "NEXT SESSION runs `/grilling` on the ship gate BEFORE any spec"; `:1186-1188`
  "3. NEXT (ACTIVE): the 2026-09-24/25 session remainder AND the owed items S27-1..17 + S28-0..4 … then Phase 11";
  `:1141` Active order = step 0 → fable remainder → remainder → Phase 11 (no p2996, no ship gate). A fresh session
  cannot tell whether p2996 / ship-gate preempt remainder items 3-31 and S27/S28.
- Rewrite (coordinator-only file; proposed text for `:1186`): "3. NEXT (ACTIVE), in this order (Ray, 2026-09-28):
  (a) the clang-p2996 fix PR (§ Current Phase '2026-09-28 clang-p2996 currency'); (b) the ship-gate `/grilling`
  (§ '2026-09-28 rulings — post-change review/verify enforcement'); (c) the 2026-09-24/25 session remainder and the
  owed items S27-1..17 + S28-0..4; then Phase 11 as ordered above." If Ray did not rule (a)/(b) ahead of (c), ask
  one AskUserQuestion instead of guessing.
- Disposition: FIX-NOW (plan text; ask Ray if the order is not already ruled).

### V7 (MEDIUM) — S27-14 still says "ask it FIRST next session" after it was ruled, built and merged
- Evidence: `task_plan.md:1108-1112` — "RULED 2026-09-28 … Branch `fix/1388-zsh-equals-guard` …" then "RECURRED 5× …
  ask it FIRST next session." #1421 (`e502c47b`, "fix/1388 zsh equals guard") is on main; the guard is live (this
  lane's own `echo ====` was denied with `zsh_equals_separator`'s text, 2026-09-28).
- Rewrite: "(S27-14) ✅ DONE 2026-09-28 — #1421 (`e502c47b`): `hook_guard` rule `zsh_equals_separator` (since
  2026-09-28); unmatched-glob half NOT built (no static signal). Ray ruled guard over `setopt`. Close #1388 if still
  open."
- Disposition: FIX-NOW.

### V8 (MEDIUM) — "Also now" items of the 2026-09-28 ship-gate block carry no done/owed marks although most shipped
- Evidence: `task_plan.md:1004-1010` lists: the owed mattpocock review of #1426, refresh `.claude/skills/verify`,
  record the lesson in memory, add self-improvement checks to `/session-handoff`. Shipped: mattpocock reports
  `mattpocock-review-{spec,standards}-1426-2026-09-28.md`; #1433 (`6e690e0b`) added the verify recipe rows and §1c
  rows Q-S. Memory lesson: UNVERIFIED by this lane (MEMORY.md's newest 2026-09-28 entry is the EARLIER session's).
- Rewrite (append after `:1010`): "Status 2026-09-28: mattpocock review of #1426 DONE (reports above); verify skill
  refresh DONE (#1433); `/session-handoff` §1c process-compliance/repeat-offender/retrieval-miss rows DONE (#1433);
  memory lesson <DONE: `<file>` | OWED>."
- Disposition: FIX-NOW.

### V9 (MEDIUM) — p2996 ORDER's "research FIRST … whether mise now has a NATIVE way to track a git ref" is neither done nor owed
- Evidence: `task_plan.md:1000-1002` "RESEARCH FIRST … why did it break (done above; also check whether the Renovate app /
  Dependabot runs are failing), and whether mise now has a NATIVE way to track a git ref". `(done above)` scopes only
  "why did it break". `grep -n -i mise sdlc-team-p2996-ref-currency-2026-09-28.md` → only run metadata and hk/lock
  lines (`:3,:72,:73,:117,:148…`), no mise-native analysis (control: the same grep finds `Dependabot` at `:137`, which
  the review DID cover). A fresh session may skip the mise research or redo the Dependabot one.
- Rewrite: "- OWED before the fix PR (Ray's research-first order): (i) mise-native git-ref tracking — read mise
  release notes since 2026.9.x for a git-ref/commit-pin tool backend and say adopt/reject with the reason; (ii)
  Renovate app run health for this repo (Dependency Dashboard / job logs). DONE: why it broke (ROOT CAUSE above);
  Dependabot has no generic extractor (review `:137`)."
- Disposition: FIX-NOW (plan text).

### V10 (MEDIUM) — p2996 SCOPE is internally ambiguous ("ONE source of truth" vs "pin-parity + both-site tests") and leaves the direction open
- Evidence: `task_plan.md:~997-999` "ONE source of truth for the hash … e.g. drop the Dockerfile ARG default so bake
  is the only literal, or the reverse — plus pin-parity/hk coverage and both-site tests." With one literal there is no
  second site for pin-parity to compare; "or the reverse" is an unmade design decision handed to an implementer.
  Also unlisted in SCOPE but stale: `.github/workflows/AGENTS.md:18` ("`CLANG_P2996_REF`: Renovate git-refs" — Renovate
  never updated the bake site), `.devcontainer/Dockerfile:421` ("Reconciled to match docker-bake.hcl's
  CLANG_P2996_REF default" — it is `f349a2d`, bake is `7220baf`), and the stale scheduling descriptions in
  `p2996_refresh.py`/`mise.toml` the review names (`:117`).
- Rewrite: "- SCOPE: exactly ONE 40-hex literal for CLANG_P2996_REF. Direction is decided in the spec (recommend the
  bake `variable` default, since bake passes `args.CLANG_P2996_REF` at `docker-bake.hcl:139,:239`; the Dockerfile keeps
  `ARG CLANG_P2996_REF` with NO default and fails the build when empty). Tests: (1) the Dockerfile carries no 40-hex
  literal for it (fail arm: re-add #904's default); (2) the Renovate regex extracts the surviving literal (fixture,
  both arms). pin-parity only if a second literal survives. Same PR corrects `.github/workflows/AGENTS.md:18`,
  `.devcontainer/Dockerfile:421`, and the `p2996_refresh.py`/`mise.toml` descriptions."
- Disposition: PLAN (the direction is a spec decision; ask Ray only if he wants the reverse).

### V11 (MEDIUM) — `docs/specs/p2996-ref-currency-review.md` has no status and keeps a premise the review refuted
- Evidence: the spec opens "Mode: **review**" with no executed marker; the review ran (`sdlc-team` run
  `fef427ec…`, report `sdlc-team-p2996-ref-currency-2026-09-28.md`). §4: "A p2996 bump triggers a base-image rebuild
  (~2.5 h cold in CI)"; the review's licensed dissent (`:141-144`) says it invalidates the compiler/final tiers, not the
  base tier (`p2996_hash.py:7`, `build-publish.yml:267`; repo estimate 80-120 min cold). A fresh session re-reading
  the spec could re-dispatch it or carry the wrong cost into the policy decision.
- Rewrite (insert after the title): "**Status: EXECUTED 2026-09-28** — `mise run sdlc-team` run
  `fef427ecb37740aebdd76ff528dd1713`, report `docs/research/kb/reports/agents/sdlc-team-p2996-ref-currency-2026-09-28.md`;
  Ray's rulings in `task_plan.md` § Current Phase '2026-09-28 clang-p2996 currency'. Do not re-dispatch." And amend
  §4's bullet: "~~base-image rebuild (~2.5 h)~~ — REFUTED by the review: a compiler bump invalidates the compiler and
  final-image tiers only (`p2996_hash.py:7`); repo estimate 80-120 min cold, 15-30 min warm ccache (unmeasured)."
- Disposition: FIX-NOW.

### V12 (MEDIUM) — Phase C's 2026-09-28 rulings, DONE line and the only #1432 pointer sit under "ARCHIVED — do NOT execute from here"
- Evidence: `task_plan.md:82` "ARCHIVED — the order ratified on 2026-09-15 … do NOT execute from here:" precedes `###
  Phase C` (`:97`), whose `:99-106` carry this session's rulings, "✅ DONE 2026-09-28 — #1429", and "Open: #1432". `grep
  -n 1432 task_plan.md` → only `:106` (control: the same grep finds `1429` at `:104`). #1432 is OPEN (gh, 2026-09-28).
  The DONE line also does not settle Phase C's own list: item 5 "Add/use public `verify-ssh-outbound`" — `mise tasks
  ls` has `verify-arch`/`verify-ssh-inbound` but no `verify-ssh-outbound` (control arm: the same grep found the two);
  the ruling "stop the two idle research-five-source worktree containers" has no done mark (`docker ps` now shows
  only the two `…-273897ea-{amd64,arm64}-…` containers, so it looks done).
- Rewrite: in the ACTIVE section's owed list add "- (S28-5) #1432 (post-land `sync --check` OUTDATED on both arches;
  verify skill gotcha carries the discriminator). Phase C remainder: item 5 `verify-ssh-outbound` task (not built),
  items 4/6 two-profile runs (#669)." And in Phase C `:104` append "Idle research-five-source containers: stopped
  (2026-09-28, `docker ps` shows only the two arch containers). Items 4-6 NOT done — see S28-5."
- Disposition: FIX-NOW.

### V13 (MEDIUM) — the new R3 rows name `MISE_ENV=arm64` but not the gitignored profile it depends on; CONTEXT.md's R1 port is stale
- Evidence: `AGENTS.md:166` "`aarch64`/`arm64` via `MISE_ENV=arm64`"; `CONTEXT.md:38` "under `MISE_ENV=arm64`";
  `.claude/skills/verify/SKILL.md` dual-arch row "per arch (`MISE_ENV=arm64` for arm64)". `DOTFILES_PLATFORM` defaults
  to `linux/amd64/v2` (`mise.toml:203`) and no tracked `mise.arm64.toml` exists (`ls mise.arm64*` → only the gitignored
  `mise.arm64.local.toml`, `.gitignore:34`), so on a fresh clone `MISE_ENV=arm64 mise run verify-arch` targets AMD64.
  `.devcontainer/AGENTS.md:97` does state the prerequisite. Also `CONTEXT.md:38` "Never the host's by passthrough"
  reads as forbidding arm64 on this arm64 Mac. And `CONTEXT.md:36` (the adjacent row) still says `-p 4444`, while
  `AGENTS.md:164` and #677 derive the port (`$(mise run ssh-port)`).
- Rewrite: `CONTEXT.md:36` → "`ssh ${USER}@localhost -p $(mise run ssh-port)` opens a shell, no password (port derived
  per workspace+arch, #677)." `CONTEXT.md:38` → "The container reports the architecture requested by
  `DOTFILES_PLATFORM`: `x86_64`/`amd64` by default; `aarch64`/`arm64` under `MISE_ENV=arm64` with the gitignored
  `mise.arm64.local.toml` profile from `mise.local.toml.example`. It must come from the request, never from host
  passthrough (on this arm64 Mac, arm64 equals the host only because it was requested)." `AGENTS.md:166`: append
  "+ profile (`.devcontainer/AGENTS.md`)" within the char budget. Verify skill dual-arch row: "per arch (`MISE_ENV=arm64`
  plus `mise.arm64.local.toml`, see `mise.local.toml.example`)".
- Disposition: FIX-NOW.

### V14 (MEDIUM) — two PLAN rows from 2026-09-28 have no issue, owner or position; Standards 8 still unresolved in the agent descriptions
- Evidence: `task_plan.md:1017-1020` "PLAN (mattpocock Standards 4 …) single-source them … Also Standards 8:
  `codex-sol-advisor` 'The default advisor lane' vs `token-routing.md` 'Neither is a default' — reword." and
  `:1021-1025` "PLAN (repeat-offender class …) Machine check wanted" — neither names an issue, a ticket, or where in
  the Active order it runs. Live: `.claude/agents/codex-{sol,astra}-advisor.md:4` and `.codex/agents/codex-{sol,astra}-
  advisor.toml` all say "The default advisor lane"; `.claude/CLAUDE.md:70` and `.claude/token-routing.md:28` say
  "Neither is a default". A router reading two agents that each claim "the default" has no tiebreak.
- Rewrite: (a) FIX-NOW, sol files then `mise run codex-lane-mirror`: description tail → "A standing advisor lane on
  codex gpt-5.6-sol (its astra twin is equivalent; neither is the default between them); claude-advisor is
  escalation-only." Same meaning in the TOML sentence shape; body `:15` "You are the default advisor lane" → "You are
  a standing advisor lane". (b) PLAN: file one issue for Standards 4 + the md↔toml shared-prose parity gate
  (`issue-filer`), and place it as "(S28-6) … — with Phase 11's codex class fix" so it has a slot.
- Disposition: FIX-NOW (a) + PLAN (b).

### V15 (MEDIUM) — 12 agent prompts say "There is no `timeout` binary here", but `timeout` resolves to a mise shim that fails
- Evidence: `grep -n 'no \`timeout\`'` → `.claude/agents/{adversarial-critic:156,staleness-auditor:130,
  claude-code-expert:300,codex-sol-adversarial-critic:275,codex-sol-staleness-auditor:250,codex-sol-claude-code-expert:280}`
  + astra twins + 3 gitignored `.codex/agents` exports. `which -a timeout` → `~/.local/share/mise/shims/timeout`
  (rc=0); `timeout 1 true` → rc=1 "mise ERROR No version is set for shim: timeout". An agent that checks `which timeout`
  sees the prompt contradicted and may trust the shim (task_plan item 13: it broke 6+3 calls).
- Rewrite (sol + Claude originals, then mirror): "- **`timeout` is not usable here.** On this Mac it resolves to a
  version-less mise shim that exits 1 (`No version is set for shim`; #1056). Bound a slow command with `python3` and
  …" (keep the rest of the bullet). Fold into V14(b)'s single-source refactor if that lands first.
- Disposition: FIX-NOW (or PLAN inside V14(b); one of the two, not neither).

### V16 (LOW) — verify-skill recipe rows: PRs called "sessions", a volatile byte count, an undefined `<fresh>`, an unstated session-id reuse
- Evidence: `.claude/skills/verify/SKILL.md` "## Recipe additions (2026-09-28, sessions #1421/#1423/#1427/#1429)" —
  those are PR numbers. Graphify row: "first call ~314 bytes" (changes with any wording edit); `"session_id":"<fresh>"`
  is undefined; the stale-file `read` arm does not say whether it reuses that session id, which is exactly what #1427's
  dedup fix is about (plan item 2: "dedup swallowing stale/deny").
- Rewrite: heading → "## Recipe additions (2026-09-28, PRs #1421/#1423/#1427/#1429)". Graphify row: "`session_id` = a
  new UUID (`uuidgen`) not used before in this repo … first call prints the factual nudge (no `MANDATORY`); repeat
  prints nothing; then, with the SAME `session_id`, `… graphify-hook-guard.sh read` with a `Read` payload whose
  `tool_input.file_path` is listed by `git diff --name-only <built_at_commit>..HEAD` → the stale notice still prints
  (dedup must not swallow it)."
- Disposition: FIX-NOW (both `.claude/` and `.agents/` copies).

### V17 (LOW) — `docs/specs/prompt-audit-C-apply.md` §5 verification cannot be re-run as written; the "planned separately" item has no pointer
- Evidence: §5 "each must print 0 for `.claude/agents` and `.codex/agents`: `grep -rlF 'All 50'` …". Re-run
  2026-09-28: `grep -rlF 'All 50' .claude/agents .codex/agents` → 3 files, `masks digits` → 3, `78-85` → 1,
  `2026-08-03 run` → 2, `read line 8 of` → `.codex/agents/graphify-operator.toml` — all gitignored Codex-app exports
  (cold review F1, #1425 OPEN). Control: `grep -rlF 'Never print a credential value' .codex/agents` finds the same 3
  exports, so the probe reaches them. The Amendments end "Open: the six-copy duplication … planned separately" with
  no pointer.
- Rewrite: §5: "`git grep -lF '<phrase>' -- .claude/agents .codex/agents` (TRACKED files; the gitignored Codex-app
  exports are #1425 and still hit)". Amendments last sentence: "… planned separately: `task_plan.md` § Current Phase
  'PLAN (mattpocock Standards 4, #1426)'."
- Disposition: FIX-NOW.

### V18 (LOW) — the active section's heading carries a relative "NEXT SESSION" that the plan pointer freezes
- Evidence: `task_plan.md:826` "## 2026-09-24/25 session remainder — ACTIVE, NEXT SESSION (fable remainder DONE
  2026-09-28) …"; `docs/agents/plan-pointer.json` `active_phase` copies it verbatim. Written 2026-09-25, it has been
  "next session" for four sessions; `:73` repeats "(ACTIVE, NEXT SESSION)".
- Rewrite: "## 2026-09-24/25 session remainder — ACTIVE since 2026-09-25 (fable remainder DONE 2026-09-28), before
  Phase 11 (Ray, 2026-09-25)"; same at `:73`; then `mise run plan-pointer` (and `plan-attest` per §6).
- Disposition: FIX-NOW (only with the handoff's plan-pointer/attest refresh; otherwise PLAN).

### V19 (LOW) — codex version facts disagree across the operator prompt and the rule it cites
- Evidence: `.claude/agents/codex-sol-operator.md:136-138` "`--full-auto` **did not exist** when probed at codex
  0.152.1 and 0.158.0 (…; see `.claude/rules/ai-cli-invocation.md`)"; the rule `:46` says "probed at 0.152.1; the host
  now runs native 0.156.x" and records no 0.158.0 probe (`grep 0.158` in the rule and its evidence file → 0; control
  `0.156` → hit). The citation does not support the 0.158.0 half.
- Rewrite: add the 0.158.0 `--full-auto` arm to `docs/rules-evidence/ai-cli-invocation.md` with its date, and fix the
  rule's heading per plan Phase 11 item 3 (F12): "Codex facts (probed at 0.152.1 and 0.158.0; the native install
  self-updates — re-probe before relying)". Rule-synced: paired KB PR.
- Disposition: PLAN (already Phase 11 item 3; add "and record the 0.158.0 arm" to that item).

### V20 (LOW) — `codex-sol-implementer.md` keeps one unsourced figure the #1426 standards review asked to drop
- Evidence: `:30` "tens of minutes; 50 minutes has been observed." (no run, date or report). The spec's Amendments say
  the mattpocock review required "no dated story or unsourced 'measured' claim in `codex-sol-implementer`". The other
  dated claims there (`:48` #1026, `:163` 2026-09-23, `:167` 2026-09-16) carry a source.
- Rewrite: "Codex at `xhigh` on a real spec takes tens of minutes." (sol, then mirror).
- Disposition: FIX-NOW (with V14a's mirror run) or PLAN with V14(b).

### V21 (MEDIUM) — `devcontainer-workflow` skill still says the local `:dev` holds ONE platform, contradicting the example #1429 rewrote
- Evidence: `mise.local.toml.example:45-47` (changed this session) "The local :dev tag keeps every platform `mise run
  sync` has refreshed onto it (a union) … sync treats a missing platform as stale"; `python/src/dotfiles_setup/sync.py:
  155-162` (the #1429 fix: a tag lacking this arch is stale; "platform UNION keeps the other architecture's layers").
  But `.claude/skills/devcontainer-workflow/SKILL.md:57-60` (and `.agents/` mirror) still says "One wart survives: the
  local `:dev` tag holds ONE platform, so right after the other arch's `up`, `mise run verify-local` fails at
  `verify-image` … until `mise run sync` in that arch's env re-points the tag". `git grep -i 'holds one platform\|one
  platform at a time'` → only these two skill copies (control: `git grep -i union` finds the example and sync.py).
  §2 doc-sync of #1429 missed the skill a devcontainer session loads first.
- Rewrite (both copies, `:57-60`): "The local `:dev` tag keeps every platform `mise run sync` has refreshed onto it (a
  union, #1429). Run `mise run sync` once in an arch's env before that arch's first `verify-local`: sync treats a tag
  that lacks this arch's platform as stale and refreshes it without dropping the other arch's layers."
- Disposition: FIX-NOW.

### V22 (LOW) — Briefs Q-S omit the common contract the M-P briefs carry (finding shape, disposition, repos-touched)
- Evidence: `session-2026-09-23d-agent-briefs.md:280-282` (common to M-P): "Every finding: severity, claim, evidence
  (transcript ordinal or file:line), control arm, and a disposition: FIX-NOW (exact change) or PLAN (exact task_plan
  text …). End with `## GitHub repos touched`." `session-handoff-briefs-q-s-2026-09-28.md` has no such paragraph; only
  Brief R mentions a Ray ruling. A lane handed Brief Q alone has no disposition or control-arm requirement, although
  §1c requires a disposition for "every finding".
- Rewrite (insert after the q-s file's intro paragraph): "Common to Q-S (same as M-P): every finding carries severity,
  claim, evidence (transcript ordinal or file:line), a control arm, and a disposition — FIX-NOW (exact change) or PLAN
  (exact `task_plan.md` text, noting `/grilling` → `/to-spec` → `/to-tickets` when a design decision is open). Read-only
  except your report; create it at a NEW path (see §1c naming). End with `## GitHub repos touched`."
- Disposition: FIX-NOW.

## Checked and clean (control arms)

- `.claude/skills/verify/SKILL.md` hook-selfcheck row "(it is NOT a mise task; `ship` runs this exact argv)": confirmed at
  `python/src/dotfiles_setup/pr.py:340-341` (`"hook-selfcheck", ("uv","run","--project","python","dotfiles-setup","hook","selfcheck")`).
- `graphify-operator.md` new instruction (the `- <N> nodes · …` line under `## Summary`): `GRAPH_REPORT.md:8` is `## Summary`,
  `:9` is `- 29969 nodes · 45857 edges · 1781 communities (1484 shown, 297 thin omitted)` — the prompt's "total, not shown" rule
  matches the real format.
- task_plan SCOPE "close #1063 so Renovate recreates it": suspected wrong, REFUTED — #1063's body says "👻 **Immortal**: This PR
  will be recreated if closed unmerged."
- Mirrors: `diff .claude/skills/verify/SKILL.md .agents/skills/verify/SKILL.md` rc=0; session-handoff mirror differs only in
  the intended `.claude`→`.agents` path/CLAUDE.md-layer lines.
- `mise.local.toml.example` new union text agrees with `sync.py:155-162` (the #1429 fix).
- `codex-sol-{staleness-auditor,adversarial-critic,claude-code-expert}.toml` descriptions: "a standing … lane" (the Standards 6
  "a audit lane" grammar error is fixed).

## Incidents observed by this lane (for the dismissed-errors / repeat-offenders lanes)

1. This lane's first `Write` overwrote the committed `session-audit-vagueness-2026-09-28.md` (earlier session, #1419) —
   V1's root cause; coordinator restoring from HEAD.
2. This lane ran an unquoted `echo ====` separator; the #1421 `zsh_equals_separator` guard denied it before execution (the
   machine check worked; memory `feedback_zsh_equals_expansion` alone would not have).

## Summary

| # | Sev | Where | Disposition |
|---|---|---|---|
| V1 | HIGH | §1c + q-s briefs: report filename collides same-day | FIX-NOW + PLAN (guard) |
| V2 | HIGH | §1c: "Briefs Q-S" letters collide with 23d Q/R/S1-S4 | FIX-NOW |
| V3 | HIGH | §1c "reuse them": hardcoded session ids/SHAs/paths | FIX-NOW |
| V4 | HIGH | §1c bugs row: branch-diff scope misses merged session PRs | FIX-NOW |
| V5 | MED | §1c "read-only" vs "add it there" | FIX-NOW |
| V6 | HIGH | task_plan: three "next session" claimants, Active order silent | FIX-NOW (ask Ray if unruled) |
| V7 | MED | task_plan S27-14 stale ("ask it FIRST") | FIX-NOW |
| V8 | MED | task_plan ship-gate "Also now" items unmarked | FIX-NOW |
| V9 | MED | task_plan p2996 mise-native research neither done nor owed | FIX-NOW |
| V10 | MED | task_plan p2996 SCOPE one-literal vs parity; stale docs unlisted | PLAN |
| V11 | MED | p2996 spec: no status; refuted cost premise | FIX-NOW |
| V12 | MED | task_plan Phase C live items under ARCHIVED; #1432 orphaned | FIX-NOW |
| V13 | MED | AGENTS/CONTEXT R3 omit arm64 profile; CONTEXT R1 port 4444 | FIX-NOW |
| V14 | MED | advisor "default" ×2; two PLAN rows unowned | FIX-NOW + PLAN |
| V15 | MED | 12 agent prompts: "no `timeout` binary" vs failing shim | FIX-NOW or PLAN(V14b) |
| V16 | LOW | verify skill recipe wording (PRs, bytes, `<fresh>`, session id) | FIX-NOW |
| V17 | LOW | prompt-audit-C spec §5 not re-runnable; no pointer | FIX-NOW |
| V18 | LOW | active heading "NEXT SESSION" frozen into plan-pointer | FIX-NOW w/ pointer refresh |
| V19 | LOW | operator 0.158.0 claim unsupported by cited rule | PLAN (Phase 11 item 3) |
| V20 | LOW | implementer "50 minutes observed" unsourced | FIX-NOW or PLAN(V14b) |
| V21 | MED | devcontainer-workflow skill "holds ONE platform" vs #1429 union | FIX-NOW |
| V22 | LOW | q-s briefs lack common finding/disposition contract | FIX-NOW |

Status: COMPLETE.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — read PR #1063 body (Renovate "Immortal" semantics) and
  issue states #1432, #1425, #1388 via `gh`; all other evidence from the local checkout.
