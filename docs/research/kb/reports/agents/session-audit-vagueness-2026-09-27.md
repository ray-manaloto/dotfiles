# Session audit — vague or misinterpretable docs/plans (Brief P, 2026-09-27)

Session `1f389314-77c7-44e8-85de-4f23b3f73c0a`. Brief:
`docs/research/kb/reports/agents/session-2026-09-27-agent-briefs.md` § Brief P.
Read-only lane except this file. Status: COMPLETE (written incrementally; `findings.md`/`progress.md` not touched —
the brief restricts writes to this file, so the coordinator persists the condensed entries).

## Scope enumerated

`git log 8bffc0ef..origin/main` (origin/main = `3fb2d6d8`): session PRs #1393 `9f5bd67a`,
#1394 `463bb27b`, #1395 `ba8ae96e`, #1396 `453aa39b`, #1403 `42a699c8`. Renovate #1399/#1401/#1402/#1404
are out of scope (mise.toml pin bumps only). Verbatim agent reports under
`docs/research/kb/reports/agents/` are records (agent-artifact-conventions rule 8: "Do not normalize
records") and are read only as evidence, not flagged for rewrite.

## Findings

> **Line numbers.** The coordinator edited `task_plan.md` while this audit ran (S27-5..7 appeared at 14:16). Every
> `task_plan.md` line cited below is from the snapshot read at that time; apply each rewrite by its QUOTED anchor, not
> by number. Proposed new owed items use the next free numbers, S27-8 and S27-9.

### P-A1 — HIGH — open ticket #1352 (D1) contradicts the shipped #1395 on the set-active-plan deny, and nothing links them

**Claim.** #1395 (`ba8ae96e`) executed most of pwf-migration ticket #1352 ("D1: Retire the operator-only attestation
posture") early, but #1352 is still OPEN, carries no comment naming #1395, and its spec now CONTRADICTS what shipped:
#1352 "What to build" retires "the eleven deny entries (six naming the attest and **selector** scripts …)" and its
added check must "fail on any entry matching the attest script, **the selector script**, the wrapper task/CLI or the
**initializer**". #1395 deliberately KEPT `Bash(*set-active-plan.sh)` (the selector) and added
`workflow.plan-switch-denied` (suites.toml) + `check_plan_switch_deny` asserting it stays. A codex lane implementing
#1352 as written would delete the deny #1395's contract requires, fail `verify`, and have two authorities that
disagree. `task_plan.md:1011-1012` still schedules "#1351's tickets (frontier #1352 …)" with no note that D1 is
mostly done.

**Second defect.** #1352's corrected acceptance grep (comment 2026-09-24) now FAILS on main because #1395 kept the
retirement history in prose: `git grep -niE 'operator[- ]only|human boundary' origin/main -- .claude AGENTS.md mise.toml
python/src python/verification ':!.claude/agent-memory*'` → 2 hits (`python/src/dotfiles_setup/plan_attest.py:6`,
`python/verification/suites.toml:1833`), rc=0. Control arm: `agent-runnable` over the same pathspec → 5 hits, so the
probe reads those trees.

**Owner ambiguity.** Keeping set-active-plan denied was the AGENT's call, not Ray's: transcript ordinal 1388 offered
"Fully open, all routes … Remove every attest deny"; 1389 Ray chose it; 1659 the agent reports "That's a separate risk
from approving a plan, so I left it closed." Yet `task_plan.md:988-989` reads "#1395 (attestation agent-runnable, Ray:
"fully open, all routes"; set-active-plan stays denied)", which attributes both halves to Ray.

**Disposition: FIX-NOW (comment) + PLAN (ruling).**
- Comment on #1352 (exact text):
  > #1395 (`ba8ae96e`, 2026-09-26) shipped most of this ticket early: all nine attest/wrapper/CLI deny rules are gone,
  > `workflow.plan-attest-agent-runnable` (forbid_tokens `attest-plan`, `plan-attest` over `.claude/settings.json`)
  > replaces the operator-only contract, and the prose in `.claude/CLAUDE.md`, `mise-tasks-only.md`, `mise.toml`, the
  > CLI help and `plan_attest.py` is rewritten. **It diverges from this ticket in one place:** the selector
  > (`set-active-plan.sh`) deny is KEPT and asserted by `workflow.plan-switch-denied` + `hook_selfcheck.check_plan_switch_deny`.
  > That was an agent judgment, not a Ray ruling — pending ruling below. Remaining here: (1) Ray's ruling on the
  > selector deny; (2) the initializer (`init-session`) spelling; (3) the required CLAUDE.md sentence "an attested plan
  > no longer means Ray approved it"; (4) the live MATCH/mismatch doctor arms. The acceptance grep must exclude history
  > sentences: `git grep -niE 'operator[- ]only|human boundary' -- .claude AGENTS.md mise.toml python/src python/verification ':!.claude/agent-memory*' | grep -v -E 'plan_attest.py:6:|suites.toml:18[0-9][0-9]:'`
  > — or reword those two lines to "was restricted to the operator".
- `task_plan.md:988-989` → replace `set-active-plan stays denied)` with
  `set-active-plan deliberately left denied by the agent — NOT a Ray ruling; contradicts #1352's spec, ruling owed)`.
- PLAN line (add under Current Phase "Owed", S27 list):
  `- (S27-8) Ray to rule: keep the set-active-plan (selector) deny (#1395 as shipped, workflow.plan-switch-denied) or
  retire it (#1352 as specced). Then comment the ruling on #1352 and narrow #1352 to its unshipped remainder. No
  /grilling needed — one AskUserQuestion.`

### P-A2 — MEDIUM — three live texts still name Ray/the operator as the attester after #1395

**Claim.** #1395 rewrote the five sites #1352 named, but three other live texts still assign attestation to Ray:
- `docs/specs/phase9-lane-dag.md:16` — mermaid node `RAY["Ray<br/>rulings, user-level changes,<br/>plan-attest"]`;
- `docs/specs/phase9-lane-dag.md:81` — roster row `| Operator | Ray | — | — | user-level skills, codex plugin enablement, \`plan-attest\` |`;
- `task_plan.md:1780-1781` — "⚠️ `task_plan.md` reads TAMPERED to planning-with-files; re-attest is operator-only: `! mise run plan-attest`."
- `task_plan.md:402` — "**Coordinator** = the process behind Ray's plan attestation" (a definition now resting on a retired premise).

A fresh session reading Phase 6 or the Phase 9 roster will print a `!` prompt for Ray instead of running the task.
**Evidence/control.** `git grep -n 'plan-attest' origin/main -- docs/specs/phase9-lane-dag.md` → lines 16, 81;
`grep -n 'operator-only' task_plan.md` → 1781 (control: the same grep finds the retired-D4 history at 622/636, so it
reads the file). #1352's corrected grep scopes `.claude AGENTS.md mise.toml python/…` and never covers `docs/specs/`
or `task_plan.md` — that is why these survived.

**Disposition: FIX-NOW.**
- `docs/specs/phase9-lane-dag.md:16` → `RAY["Ray<br/>rulings, user-level changes"]:::ray`
- `docs/specs/phase9-lane-dag.md:81` → `| Operator | Ray | — | — | user-level skills, codex plugin enablement (plan attestation is agent-runnable since #1395) |`
- `task_plan.md:1780-1781` → `coordinator-only, no exception). ⚠️ After editing \`task_plan.md\`, re-attest with \`mise run plan-attest\` (agent-runnable since #1395, 2026-09-26).`
- `task_plan.md:402` → `- **Coordinator** = the one session that writes \`task_plan.md\` and runs \`mise run plan-attest\` after its edits; codex only when`
  (rest of the line unchanged).

### P-B1 — MEDIUM — the new `AGENTS.md` fmt rule is ambiguous about WHICH "fix" and whether to stage first

**Claim.** `AGENTS.md:152-153` now reads "hk 2 `fix` does NOT stage its fixes (measured 2026-09-27): `git add` AFTER
`mise run fmt`." Two misreadings are open to a fresh session or codex lane:
1. "hk 2 `fix`" names neither the command nor the hook. hk.pkl has a `fix` hook AND `fix = true` on `pre-commit`;
   the research the rule came from says only `pre-commit` still auto-stages under v2
   (`hk-v2-migration-research-2026-09-27.md:26,408`). A reader can conclude the pre-commit hook's fixes are left
   unstaged too, which is false.
2. "`git add` AFTER" silently drops the old "BEFORE" half without saying whether it is still needed. Measured now
   (throwaway `git clone --shared` in the scratchpad, `GIT_CONFIG_GLOBAL` emptied, hk 2.3.0):
   `hk fix --plan --json` → `trailing_whitespace included 2` for {1 modified tracked + 1 untracked} with NOTHING
   staged, the same 2 with the untracked file staged, the same 2 with everything staged; control arm, clean tree →
   `skipped 0`. So under hk 2.3.0 staging before `fmt` does not change the file set — the rule should SAY that, since
   the KB-cached upstream doc (`knowledge-base/sources/hk/docs/cli/fix.md`: "`--all` — Run on all files instead of
   just staged files") says the opposite and a lane that reads it will stage first "to be safe" or skip untracked files.

**Disposition: FIX-NOW** (net +~110 chars; AGENTS.md is 11,586 B, ceiling 12,000):
replace `AGENTS.md:152-153` with
```
  guard redirects raw hk); `mise run fmt` (`hk fix`) to auto-fix. It fixes
  modified AND untracked files, staged or not, but leaves the fixes UNSTAGED
  (hk 2.3, measured 2026-09-27; only the pre-commit hook auto-stages):
  review, then `git add` AFTER `mise run fmt`.
```

### P-B2 — MEDIUM — `clean-git-state.md` rule 3 is false under hk 2.3 (surfaced by this session's migration)

**Claim.** `.claude/rules/clean-git-state.md:24` — "New files must be `git add`-ed before hk runs, or hk won't check
them". Measured in the same throwaway clone: `hk check --all --plan --json` (what `mise run lint` runs) →
`trailing_whitespace` fileCount 678 on a clean tree, 679 after adding one UNTRACKED file (control: removing it → 678).
hk 2.3.0 `--all` help: "Select all tracked and eligible untracked files". So hk DOES check unstaged new files; the
real divergence runs the other way — an untracked scratch file is linted locally but absent in CI. The #1403 spec
(§2) rewrote only AGENTS.md and never swept this sibling rule, which carries the same premise.

**Disposition: FIX-NOW** — replace `clean-git-state.md:24` with:
`3. hk 2.3 checks untracked files too (\`--all\` selects "tracked and eligible untracked", measured 2026-09-27), so an
untracked file you do NOT mean to commit is linted locally but absent in CI — stage exactly what you intend to
commit and delete or ignore the rest before \`mise run lint\``.
Run `mise run lint-docs` (eager rule, `md_size_budget`).

### P-C1 — MEDIUM — "once per machine" never says whether the devcontainer is a machine; in-container commits now run NO hk hooks

**Claim.** #1403 moved hook installation from mise's postinstall to an operator step described as "once per machine
from this checkout" (`mise.toml:177`, `doctor.toml:293-300`, `do-not.md:63-65` "present only once
`hk install --global --mise` has run for this machine", `hk_hooks.py:5-7`, `doctor.py:1366-1367`). The devcontainer
has its own `~/.gitconfig` (chezmoi `home/dot_gitconfig.tmpl`), and neither it nor `.devcontainer/**` installs a hook:
`git grep -n -i -E 'hk install|hook\.hk|\[hook' origin/main -- home/ .devcontainer/` → only an unrelated comment
(`mise-system.toml:412`); control arm, the same pattern shape finds `[safe]` at `home/dot_gitconfig.tmpl:25`, so the
grep reads that template. The host-side `hk uninstall` (issue #1397 status comment) removed the LOCAL `.git/config`
hooks from the bind-mounted checkout, which the container used to share. So inside the container — the repo's
declared real dev env (`AGENTS.md` R1-R3) — `no_commit_to_branch` and the commit-msg check no longer fire, and no
text says whether that is intended. A reader of do-not.md #9 cannot tell whether "this machine" includes the container.

**Disposition: PLAN** (a behaviour decision, not a wording fix) — add to `task_plan.md` Current Phase "Owed":
`- (S27-9) Devcontainer hk hooks after #1403: the container's chezmoi ~/.gitconfig has no hook.hk-* and the shared
checkout's local hooks were uninstalled, so in-container commits run no hk hooks. Decide: (a) chezmoi renders the
three hook.hk-* entries (hk 2.3 global form) into dot_gitconfig.tmpl, or (b) state in do-not.md #9 that the pre-commit
layer is host-only and the ruleset + CI are the in-container layers. Needs one AskUserQuestion; if (a), /to-spec
(image-adjacent: verify-container-latest + a live \`git hook list pre-commit\` arm in the container).`
Interim FIX-NOW wording for `do-not.md:63-65`: `hk's \`no_commit_to_branch\` in the **pre-commit** hook (on the Mac
host only once \`hk install --global --mise\` has run from this checkout — the doctor's \`hk-hooks\` check reports when
it has not; the devcontainer currently installs no hk hooks, S27-9)`.

### P-C2 — LOW — ADR-0001's Context still says the postinstall installs hooks on every `mise install`

**Claim.** `docs/adr/0001-hk-hooks-do-not-run-in-ci.md:7-9`: "`mise.toml`'s `[hooks] postinstall = "mise reshim && hk
install --mise"` runs on **every** `mise install` — including on GitHub Actions runners. `hk install` writes three git
hooks". False since #1403 (`mise.toml:178` `postinstall = "mise reshim"`). The ADR is still the live authority cited by
`mise-tasks-only.md` (the `HK_SKIP_HOOKS=` row) and `hk.pkl:405-415`. The #1403 spec §2 permitted "an optional one-line
dated note" and none was added (`git log -2 -- docs/adr/0001-*` → last touched #402).

**Disposition: FIX-NOW** — insert after the Status line:
`> **2026-09-27 (#1403):** the postinstall below no longer runs \`hk install\` (upstream removed that recipe,
> jdx/hk#1376); a runner gets hk hooks only if some other setup installs them. The decision stands as defence in depth
> and \`workflow_hk_skip_hooks\` still gates it.`

### P-C3 — MEDIUM — #1397 body is stale and its status comment claims a pin that knowledge-base main does not have

**Claim.** (a) #1397's BODY still leads item 1 with "A. Roll back" and cites "The dotfiles postinstall `mise.toml:180`
(`hk install --mise`)" and "Both repos still pin **1.57.0**"; the 05:49Z comment reverses the recommendation and the
19:03Z comment marks item 1 done, but a reader of the body alone (the usual `gh issue view` skim, and every
`/to-spec` lane that quotes a body) gets the pre-research framing. (b) The 19:03Z status comment says "Item 2 —
resolved by alignment: both repos now pin hk 2.3.0 (dotfiles #1403; knowledge-base #823, still blocked …)". On
knowledge-base `origin/main`: `mise.toml:46 hk = "1.57.0"` and `hk.pkl:1` `v1.57.0/hk@1.57.0` (control arm: the same
`git grep` on dotfiles main finds 2.3.0). The user-global 2.3.0 and KB's 1.57.0 still coexist. (c) Items 3-5 have no
owner and no closure test: item 3 "restart long-lived terminals" (operator, no check), item 5 offers two actions with
no ruling, and `task_plan.md:996-997` (S27-2) copies them as "Owed" without either.

**Disposition: FIX-NOW** (issue edits; `-R ray-manaloto/dotfiles`; assert the anchor count first, per memory
`feedback_issue_body_edit_needs_anchor_assert`):
- Prepend to the #1397 body: `> **Status 2026-09-27:** item 1 DONE (global install kept and reinstalled from dotfiles,
  see the 19:03Z comment; option A below is superseded by the 05:49Z correction). Item 2 is HALF done: dotfiles pins
  2.3.0 (#1403); knowledge-base main still pins 1.57.0 until knowledge-base#823 lands (blocked on knowledge-base#824).
  Open: items 3-5.`
- ~~Correction comment for item 2~~ — **already posted by the coordinator at 19:16:47Z while this audit ran** ("Item 2
  is not resolved yet … Item 2 closes when #823 lands"). Independently confirmed here: hk 1.57.0 accepts the global
  hook's hidden `--from-hook` (`hk run pre-commit --from-hook --plan` in the KB checkout → rc 0; control without the
  flag → rc 0; `--help` hides it in BOTH 1.57.0 and 2.3.0, so help text is not the arm). BUT `task_plan.md` S27-2 still
  ends "Items 1-2 DONE (status comment on #1397)", contradicting that correction — fixed by the S27-2 rewrite below
  ("Items 1-2 DONE except KB's pin (#823)").
- `task_plan.md:996-997` S27-2 → `(S27-2) #1397 items 3-5 — owner Ray (user-level, never agent-applied per
  feedback_no_user_level_file_updates): 3 restart shells carrying stale HK_PKL_BACKEND (done when a fresh session's
  \`[ -n "$HK_PKL_BACKEND" ] && echo SET || echo ABSENT\` → ABSENT); 4 the version-less global \`timeout\` shim (#1056,
  pick pin-coreutils vs reshim); 5 graphify PATH drift 0.9.69 vs lock 0.9.65 (pick: lower the user-global pin, or
  \`mise run graphify-upgrade\` to raise the lock). Items 1-2 DONE except KB's pin (#823).`

### P-D1 — LOW — `docs/specs/hk-v2-migration-dotfiles.md` reads as still pending, with pre-change anchors and an UNVERIFIED premise

**Claim.** The spec's Status line says only "RATIFIED 2026-09-27"; nothing records that it LANDED as #1403
(`42a699c8`) or that the landed change went beyond its §2 allowlist (new `hk_hooks.py` + doctor `hk-hooks` check,
`lock_integrity.platformless_asset_entries`, `lock_shared` `tool@version`, two apt pins, `tests/test_git_config_isolation.py`
— all in the squash, `git show --stat 42a699c8`). Its line anchors (`mise.toml:180`, `AGENTS.md:151-154`,
`refresh.yml:77,289`) are pre-change and several no longer match (`mise.toml` postinstall is now `:178`; refresh.yml's
second site is `:285`). `P16 | A | … UNVERIFIED` still stands although verification step 1 ran. §4 "the global
reinstall is an operator step after merge" names no owner and no record — it was done (#1397 19:03Z comment). A lane
told "implement docs/specs/hk-v2-migration-dotfiles.md" (the KB twin, #823, is still open) could re-run it.

**Disposition: FIX-NOW** — replace the spec's Status paragraph's first sentence with:
`Status: LANDED 2026-09-27 as #1403 (squash \`42a699c8\`; land rc=0 incl. verify-local). Line anchors below are
against the pre-change tree \`8bffc0ef\`. The landed diff also carries review fixes outside §2 (hk-hooks doctor check,
lock_integrity platform-less check, lock_shared \`tool@version\`, curl/libsqlite3-dev apt pins). The operator step in
§4 (global reinstall from this checkout) was done 2026-09-27 (#1397 status comment). Ratification: …` (keep the rest);
and change P16's Kind from `A` to `E` with Source `verified: step 1 (hk-v2 implementer reports)`.

### P-E1 — MEDIUM — `task_plan.md` Current Phase item 2 contradicts itself and its section heading is stale

**Claim.**
- `task_plan.md:1044-1046`: "the `kb-tool-review` arm is MET … receipt row owed on the next dotfiles PR". #1396
  (`453aa39b`) landed that row (`docs/receipts/1319.md`, "knowledge-base `kb-tool-review` to its Review phase
  (2026-09-26)"), so "owed" is stale.
- `task_plan.md:1049-1051`, in the SAME item, still lists as remaining "one `kb-tool-review` to its Review phase (also
  the artifact-mode proof and KB#793's arm)" — the arm the preceding sentence calls MET. A fresh session reading
  top-down gets both "done" and "do it".
- `task_plan.md:1049` "remainder item 5" is ambiguous: two sections are called "remainder" (§ "fable-orchestrator
  removal" is "the fable-orchestrator remainder" at :1004; § "2026-09-24/25 session remainder" at :812). It means the
  latter's item 5 (:828, codex MCP re-auth).
- `task_plan.md:773` heading: "ACTIVE, NEXT SESSION: #1319 remaining arms (see Current Phase item 2), F2 graphify
  rebuild, V6 KB CLAUDE.md pointer" — F2 is "DONE 2026-09-26" (:803) and V6 "DONE 2026-09-26 in knowledge-base#820" (:781).
- `task_plan.md:1041-1042` "**DONE 2026-09-25 …** the four Claude-only `Agent` arms. **Also owed, runnable now:** re-run
  `mise run verify` …" — done in #1394 (the :1044 sentence says so) but not marked.

**Disposition: FIX-NOW** (coordinator applies; `task_plan.md` is coordinator-only, then `mise run plan-attest`):
- `:773` heading → `## fable-orchestrator removal (2026-09-24) — ACTIVE: #1319 remaining arms only (Current Phase item 2); F2 and V6 DONE`
- Replace `:1041-1051` (item 2) with:
```
2. #1319 live arms. DONE: the four Claude-only `Agent` arms (2026-09-25, #1382); the verify/rule-sync/plugin-health
   re-runs + live-path greps (2026-09-26, #1394); the `kb-tool-review` Review-phase arm, also KB#793's arm and the
   artifact-mode proof (headless run `wf_9a05aaf2-5f5`, receipt row landed in #1396). Codex is available (probe PONG
   2026-09-26); its `exa`/`graphify` MCP OAuth re-auth is § "2026-09-24/25 session remainder" item 5. Attestation is
   agent-runnable since #1395. REMAINING, in order: (a) optional `kb-codex-implementer` stopgap run; (b) the
   `sdlc-team` dispatch — BLOCKED on #1362; (c) comment on #1293 that Phase 10 step 0 is complete; (d) close #1319
   and #1310.
```

### P-E2 — LOW — the `timeout`-shim item is owed twice in `task_plan.md` with no cross-reference

**Claim.** `task_plan.md:856-858` (remainder item 13: "`/grilling`: pin coreutils in dotfiles too, or remove the
global shim. Class tracked in #1056") and `task_plan.md:996-997` (S27-2: "#1397 items 3-5: … the version-less global
`timeout` shim (#1056)") are the same decision in two places with different framings (a /grilling in one, an operator
item in the other). Two owners can act on it independently.

**Disposition: FIX-NOW** — append to remainder item 13: `Same decision as #1397 item 4 / S27-2; resolve once, mark both.`
and in S27-2 item 4 write `(= remainder item 13)`.

### P-F1 — LOW — `typos.toml` states two contradictory SHA policies and a wrong range

**Claim.** #1393 added `[default] extend-ignore-re = ["\\b[0-9a-f]{7,40}\\b"]` whose comment says "Short hex SHAs in prose
(7-24 chars)" and "full 32/40-char hashes already pass" — the regex covers 7-40, so the comment's range is wrong. The
same file still opens with "Allowlist the exact hash identifier so genuine typos elsewhere are still caught"
(`typos.toml:2-5`) and keeps the `f6ba0ae` entry whose comment argues "One SHA, one line, no collateral" /
"rather than allowing bare `ba`" (`:17-23`) — the policy the new regex replaced. A reader adding the next SHA cannot tell
which policy governs. Measured: a file containing `f6ba0ae` and `ba41c3748e298012`, checked with a config holding ONLY
the regex → `typos` rc 0; control, an empty config → rc 2 with `ba` flagged twice. So both per-SHA entries are now
redundant.

**Disposition: FIX-NOW** — in `typos.toml`: change the header (`:2-5`) to `# typos config (#154). Hex digests and
commit SHAs (7-40 lowercase hex chars) are ignored by the [default] regex below; do not add per-SHA entries.`; change
"(7-24 chars)" to "(7-40 chars)" and drop "full 32/40-char hashes already pass"; delete the `ba41c3748e298012` and
`f6ba0ae` entries with their comments (arm: `mise run lint` typos step stays rc 0; mutation arm: delete the regex →
typos fails on `f6ba0ae` in `docs/agents/goal-history.md`).

### P-E3 — LOW — Current Phase "Owed" list is out of order and the fable section still lists a done ruling as open

**Claim.** (a) The S27 list reads S27-1, -2, -3, **-5, -6, -7, -4** (snapshot 14:16), so "the next item" is ambiguous to a
reader walking it top-down; S27-4 is also already filed (#1405) and needs no action beyond tracking. (b) § fable-orchestrator
removal, ruling "`kb-tool-review` artifact mode → KEEP, and prove it with one live `kb-tool-review` run reaching its Review
phase (doubles as the #1319 / KB#793 live arm). Needs codex — available again since 2026-09-26" carries no DONE marker
although the run happened (`wf_9a05aaf2-5f5`, #1396 receipt row). (c) S27-6 ("Add `hk install --global --mise` to the
root `AGENTS.md` Quick Start") covers the host only — see P-C1/S27-9 for the container half.

**Disposition: FIX-NOW** — reorder S27-4 to sit between S27-3 and S27-5 and append ` — FILED, no action here` to it;
prefix the fable ruling with `**DONE 2026-09-26** (\`wf_9a05aaf2-5f5\`, receipt row #1396) — ` ; append to S27-6
` Host only; the devcontainer half is S27-9.`

### P-G1 — MEDIUM — knowledge-base #823 says "once per machine — same as dotfiles" but not FROM WHICH checkout; running it from knowledge-base drops dotfiles' pre-push

**Claim.** KB PR #823 (head `d92e1b3c`) `mise.toml` `[hooks]` comment: "The setup is `hk install --global --mise`, once per
machine — same as ray-manaloto/dotfiles." hk 2's global install fixes the event set from the CWD config at install time
(dotfiles `doctor.toml:293-300`: "the global event set is the cwd config's hooks, so pre-push is included only then").
KB's `hk.pkl` (PR head) defines `pre-commit` (:602) and `commit-msg` (:609) and NO `pre-push`; dotfiles' defines
`pre-push` (:858). So an operator or agent following the KB comment from the KB checkout rewrites `~/.gitconfig` to
two events and silently removes dotfiles' `pre-push` (`ghcr_publish_prereqs`, `test`). That is exactly the state #1397
item 1 found ("The event set is pre-commit and commit-msg only, so it was installed from a repo whose `hk.pkl` has no
pre-push"). dotfiles' doctor `hk-hooks` would catch it only at the next dotfiles SessionStart.

**Disposition: FIX-NOW** on the #823 branch before it lands (kb-review receipt required) — replace the comment's last
sentence with: `The setup is \`hk install --global --mise\`, run ONCE per machine FROM THE ray-manaloto/dotfiles
CHECKOUT (its hk.pkl has the superset of events incl. pre-push; running it here would drop dotfiles' pre-push). Do not
run it from this repo.` Mirror the same "from the dotfiles checkout, never from another repo" sentence into dotfiles
`mise.toml:177` (it already says "from this checkout", which is correct only when read inside dotfiles) — no change
needed there beyond P-C1.

### P-G2 — LOW — knowledge-base #823's gitleaks rationale now argues against the code it sits above

**Claim.** KB #823 `hk.pkl`: the kept rationale says "amending `Builtins.gitleaks` inherits a disk-writing test that a
`--staged` command cannot satisfy" and "UPSTREAM NOW SHIPS THIS. `Builtins.gitleaks_staged` landed in hk v1.57.0";
the new code 20 lines below is `local gitleaksStaged: Step = (Builtins.gitleaks) { scan = "staged" }` — an amendment
of `Builtins.gitleaks`, because v2.0.0 removed `gitleaks_staged`. Likewise "`hk test` goes 46 -> **51** … Any comment
in this file quoting 46 is stale" now sits beside "Under hk 2.3.0 … `hk test` is **53**", making 51 the stale number by
the file's own rule. A reader cannot tell which paragraph is current.

**Disposition: FIX-NOW** on the #823 branch — prefix the "UPSTREAM NOW SHIPS THIS" paragraph with
`HISTORY (hk 1.57): ` and append to it `Under hk 2.x the variant is gone; the staged form is the base builtin's
\`scan = "staged"\` option, whose own tests pass (see below), so the "amending Builtins.gitleaks" objection in
correction 1 applies to the v1 disk-scanning shape only.`; change "Any comment in this file quoting 46 is stale." to
"Current count: 53 under hk 2.3.0 (below); 46 and 51 are history."

### P-G3 — MEDIUM — knowledge-base `.claude/CLAUDE.md` now says "only under … item 2" while the next bullet up lists three triggers

**Claim.** KB #820 (`c7c121cc`) rewrote the lane-preference bullet to "escalate to `claude-advisor` only under dotfiles
`.claude/token-routing.md` § Escalation, item 2 (the same problem resisted two attempts after a codex verdict)" (KB
`.claude/CLAUDE.md:33`; same sentence in KB `.claude/agents/kb-codex-advisor.md:15-16`). The bullet directly above
(`:32`) lists THREE `claude-advisor` triggers ("the codex advisor failed or returned empty, the problem resisted two
attempts after a codex verdict, or Ray names it"), and the cited source has three (dotfiles `.claude/token-routing.md:16-18`).
"only under item 2" read literally forbids items 1 and 3. The V6 ruling (`task_plan.md` § fable-orchestrator removal,
"V6 → SUBSUMED by trigger 2 … no fourth trigger") meant "the codex-cannot-close case IS trigger 2", not "trigger 2
only". Also a cross-repo pointer: a KB-only clone cannot open the cited file.

**Disposition: FIX-NOW** (next KB PR, kb-review receipt) — in both KB files replace "only under dotfiles
`.claude/token-routing.md` § Escalation, item 2 (the same problem resisted two attempts after a codex verdict)" with
"only under one of the three escalation triggers listed in the advisor bullet above (the same list as dotfiles
`.claude/token-routing.md` § Escalation); \"a problem codex cannot close\" is trigger 2 — the same problem resisted two
attempts after a codex verdict". (In `kb-codex-advisor.md` say "listed in `.claude/CLAUDE.md`" instead of "above".)

### P-A3 — LOW — the new session-handoff attest step has an undefined trigger and no branch for a busy session; a rule row has a sentence-case slip

**Claim.** `.claude/skills/session-handoff/SKILL.md:292-294` (and its `.agents/` mirror): "If the plan changed, run
`mise run plan-attest` yourself … and only after `mise run session-orphans` shows no live wait loops or lanes …".
(a) "the plan changed" has no reference point (since session start? since the last attest?) and no probe, although
the read-only probe exists (`mise run plan-attest -- --show`). (b) It says what to do when `session-orphans` is clean,
not what to do when it is not (wait? cancel? hand off unattested?). (c) `.claude/rules/mise-tasks-only.md:31` ends
"… the bare form WRITES. the plugin's set-active-plan script stays denied" — lower-case sentence start from a scripted
replace (transcript ordinal 1561).

**Disposition: FIX-NOW** — replace the SKILL.md sentence (edit `.claude/`, then `mise run skills-mirror`
regenerates the `.agents/` copy) with: `If \`mise run plan-attest -- --show\` reports that \`task_plan.md\` no longer matches its
attestation, run \`mise run plan-attest\` yourself before printing that line — but only once \`mise run session-orphans\`
shows no live wait loops or lanes and no background agent, codex lane or harness task is still running. If any is
still running, wait for it or stop it first; never attest bytes a live writer can still change. Any later plan edit
makes the attestation stale again.`; in `mise-tasks-only.md:31` capitalise "The plugin's set-active-plan script stays
denied".

### P-A4 — note for the coordinator's uncommitted goal-history iteration 039

`docs/agents/goal-history.md` iteration `dotfiles-goal-20260927-039` (uncommitted in the working tree at audit time)
repeats P-A1's misattribution: "Rulings (Ray, AskUserQuestion): plan attestation made agent-runnable, 'Fully open, all
routes' (set-active-plan stays denied)". The parenthetical was the agent's call (transcript ordinals 1388-1389, 1659).
Because the iteration is not yet committed, the append-only rule does not yet bind it. **FIX-NOW (before commit):**
change it to `… 'Fully open, all routes'; the agent kept set-active-plan denied on its own judgment — ruling owed, S27-8`.
Its goal text also names "S27-1..7"; if S27-8/-9 are added, update it to "S27-1..9".

## Summary

| ID | Sev | Surface | Disposition |
|---|---|---|---|
| P-A1 | HIGH | #1352 (D1) vs shipped #1395 on the set-active-plan deny; #1352's acceptance grep now fails; misattributed ruling in `task_plan.md` | FIX-NOW comment + text; PLAN S27-8 (one AskUserQuestion) |
| P-A2 | MED | `docs/specs/phase9-lane-dag.md:16,81`, `task_plan.md` Phase 6 + Coordinator definition still say operator attests | FIX-NOW |
| P-A3 | LOW | session-handoff attest step: undefined trigger, no busy-session branch; rule-row typo | FIX-NOW |
| P-A4 | — | uncommitted goal-history 039 repeats P-A1's misattribution | FIX-NOW before commit |
| P-B1 | MED | `AGENTS.md` fmt rule: which "fix", and whether to stage first (measured: hk 2.3 selects modified+untracked regardless) | FIX-NOW |
| P-B2 | MED | `clean-git-state.md:24` "hk won't check unstaged new files" — false under hk 2.3 (678→679) | FIX-NOW |
| P-C1 | MED | "once per machine" vs the devcontainer: in-container commits run no hk hooks | PLAN S27-9 + interim do-not.md wording |
| P-C2 | LOW | ADR-0001 Context still says postinstall installs hooks | FIX-NOW (dated note) |
| P-C3 | MED | #1397 body stale; S27-2 "Items 1-2 DONE" contradicts the 19:16Z correction; items 3-5 unowned | FIX-NOW |
| P-D1 | LOW | hk v2 spec reads as pending; pre-change anchors; P16 still UNVERIFIED | FIX-NOW |
| P-E1 | MED | `task_plan.md` Current Phase item 2 says both "MET" and "do it"; stale fable heading; ambiguous "remainder item 5" | FIX-NOW |
| P-E2 | LOW | `timeout` shim owed twice | FIX-NOW |
| P-E3 | LOW | S27 list out of order; done fable ruling unmarked; S27-6 host-only | FIX-NOW |
| P-F1 | LOW | `typos.toml` two SHA policies, wrong 7-24 range; per-SHA entries redundant (measured) | FIX-NOW |
| P-G1 | MED | KB #823 "once per machine" omits "from the dotfiles checkout" (KB has no pre-push) | FIX-NOW on #823 branch |
| P-G2 | LOW | KB #823 gitleaks rationale contradicts the v2 code; stale test count | FIX-NOW on #823 branch |
| P-G3 | MED | KB CLAUDE.md "only under … item 2" vs three triggers one bullet up | FIX-NOW next KB PR |

**Read and found clean (no finding):** `.claude/CLAUDE.md` saved-workflows line (#1393); `docs/specs/research-fanout.md`
status/roles/§8-§9 history labels (#1393); `research-sweep` SKILL.md (#1393); `docs/receipts/1319.md` rows (#1394,
#1396); `doctor.toml [hk_hooks]`; `hk.pkl` postinstall/ADR comment (:405-415); `refresh.yml`/`gcc-sha-repair.yml`
postinstall comments; `renovate.json` group description; KB#824 body (options + ruling explicit, owner Ray);
`plan_attest.py`/`suites.toml` history prose (accurate as history; only P-A1's grep collision). Verbatim agent reports
were not audited for rewrite (records).

**Probes run (each with its arm):** attestation-text grep (control `agent-runnable` 5 hits); #1352 acceptance grep
on main (2 hits); KB attestation grep (0; control `kb-land` 3 hits); `hk fix --plan` in a throwaway clone (2/2/2 vs
clean 0); `hk check --all --plan` 678 vs 679; typos regex-only rc 0 vs empty config rc 2; hk 1.57 `--from-hook` in KB
rc 0 (control without flag rc 0); container hook grep (control `[safe]` found); KB vs dotfiles hk.pkl event sets.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — session PRs #1393-#1396, #1403 diffs; issues #1351-#1360, #1397, #1405
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — PR #820 (`c7c121cc`) and PR #823 (head `d92e1b3c`) diffs; issue #824; offline `sources/hk` docs
- [jdx/hk](https://github.com/jdx/hk) — `docs/cli/fix.md` via the knowledge-base offline source mirror (default file-selection wording), plus the installed 2.3.0/1.57.0 binaries' `--help`
