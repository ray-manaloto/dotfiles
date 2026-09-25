# Session-integrity audit (vagueness / contradictions) — 2026-09-25

Brief P (reused), read-only. Scope: `git diff 1c4977eb..HEAD` excluding
docs/research, python, tests (PRs #1368, #1373, handoff branch), task_plan.md
sections "2026-09-25 step 0", "2026-09-24/25 session remainder",
"fable-orchestrator removal (2026-09-24)", docs/specs/plugin-remove-pipeline*.md,
.claude/skills/plugin-{inventory,removal}/SKILL.md.

Status: COMPLETE — 21 findings: 17 FIX-NOW (3 of them LOW), 3 PLAN (F1, F14, F20), and F12 split FIX-NOW (doc) / PLAN (code).

## Summary

| # | Class | Where | One line |
|---|---|---|---|
| F1 | PLAN (#1370) | `.agents/skills/plugin-{inventory,removal}/SKILL.md:3` | mirror says "Codex or codex plugin" |
| F2 | FIX-NOW | `docs/agents/goal-history.md` | no iteration since 034; three accepted order/topology changes unrecorded |
| F3 | FIX-NOW | `task_plan.md:71,815` | two ACTIVE phases; `## Next Step` is the 2026-09-15 order |
| F4 | FIX-NOW | `task_plan.md` § Current Phase | item 0 done-but-open; "unshipped" vs "landed"; list numbered 1,3,4 |
| F5 | FIX-NOW | `task_plan.md` fable section | V4 superseded by C5 but still listed; stale graph SHA; false pointer sentence |
| F6 | FIX-NOW | plugin-removal skill step 4 | `mise run doctor` always rc=0 — use `-- --strict` |
| F7 | FIX-NOW | plugin-removal skill step 3 | `--apply` writes tracked `doctor.toml`/settings — branch first |
| F8 | FIX-NOW | plugin-removal skill step 2 | would delete the watchlist line and test fixtures |
| F9 | FIX-NOW | plugin-removal skill step 3 | "apply that same plan" — apply re-plans; blocked apply rc=2 |
| F10 | FIX-NOW | plugin-removal skill step 5 | `mise run kb-review` does not exist (it is a skill) |
| F11 | FIX-NOW | skills + specs | skills cite only the base spec; r2 "LAST round"; r3 implementer line wrong |
| F12 | FIX-NOW / PLAN | mise-tasks-only.md:24, mise.toml:971, hook_guard.py:504-507,568-570 | "ship watches to green" vs gh-cli-watch "ship arms and returns" |
| F13 | FIX-NOW | do-not.md #6 | frames `gh run watch` as usable; it is guard-denied |
| F14 | PLAN | this session's context | subagents received PRE-#1368 rule text; /clear is load-bearing |
| F15 | FIX-NOW | task_plan.md step 0 item 2 | "neither repo imports an Anthropic SDK" is false (KB model_limits.py) |
| F16 | FIX-NOW | task_plan.md step 0 item 1 | no output file / disposition vocabulary for `/doctor` |
| F17 | FIX-NOW | rules-evidence/long-running-command-hangs.md:113 | cites renumbered ci-local-parity rule 5 |
| F18 | FIX-NOW (LOW) | .claude/CLAUDE.md:4-5 | 12,000-char cap cited without owner/headroom |
| F19 | FIX-NOW (LOW) | task_plan.md remainder item 5 | quota-reset time has no timezone |
| F20 | PLAN | prompt-audit-2026-09-24.md:86 | "grok text load-bearing" — #1368 changed the eval |
| F21 | FIX-NOW (LOW) | plugin-inventory skill | "historical paths"/scan root undefined |

Verified-and-fine (no finding): `/claude-api` subcommand list (matches
`$CC/commands.md:66`); remainder item 6 worktree counts (10 = 5+5, 3 stale KB;
control-armed); `.github/workflows/AGENTS.md`, `verify-before-advancing.md`,
`long-running-command-hangs.md` and `pr-workflow` now agree on auto-merge +
`land` + `bounded-wait`; `land --resume` still accepted (`pr.py:880-891`);
`FALLBACK_TOKENS` phrase present in `.claude/CLAUDE.md`; fable-orchestrator's
absence from the watchlist is Ray's ruling (`plugin-remove-pipeline.md:26-31`),
not drift. Deleted skills leave refs only in historical specs/evidence and
`skills_mirror.py` comments.

## Findings


Graph note: `mise run graphify-health` -> rc=3 `stale` (built 9c624360, HEAD
c4806bf4, 23 corpus files changed). Graph unavailable; every finding below is
from source.

### F1 [PLAN — already tracked as #1370] Codex-facing mirrors of both new skills say "Codex or codex plugin"

- `.agents/skills/plugin-inventory/SKILL.md:3` — "Inventory one exact Codex or codex plugin selector"
- `.agents/skills/plugin-removal/SKILL.md:3` — "Remove a Codex or codex plugin"
- Cause: `skills_mirror.RULES` rewrites `("Claude Code", "Codex")`
  (`python/src/dotfiles_setup/skills_mirror.py:124`); the new skills name BOTH
  harnesses in one sentence, the exact case `PER_FILE` exists for
  (`skills_mirror.py:52-58`, session-review precedent "Codex and Codex").
- Effect: a codex lane reading its mirror is told the skill handles only codex
  plugins, while the body (`claude_cli`, `claude plugin`) handles Claude Code too.
- Control: `diff` of the two trees shows ONLY line 3 differs, so the rest of the
  mirror is faithful.
- Rewrite: add to `PER_FILE` in `skills_mirror.py`:
  ```python
  # Both skills cover BOTH harnesses' plugins; RULES' ("Claude Code","Codex")
  # collapses the pair to "Codex or codex".
  "plugin-inventory": (("exact Codex or codex plugin", "exact Claude Code or codex plugin"),),
  "plugin-removal": (("Remove a Codex or codex plugin", "Remove a Claude Code or codex plugin"),),
  ```
  then `mise run skills-mirror` and confirm `mise run skills-mirror -- --check` rc=0.
- Status: #1370 (OPEN) asks for the CLASS fix (skip phrases that already name
  both harnesses + a test forbidding "Codex or codex"/"Codex and Codex" in
  `.agents/skills/**`). The PER_FILE entries above are the interim instance fix
  if the class fix is not scheduled before the next codex lane reads these skills.

### F2 [FIX-NOW] goal-history has no iteration for the 2026-09-24 removal or the 2026-09-25 order ruling

- `origin/main:docs/agents/goal-history.md` ends at `dotfiles-goal-20260924-034`,
  whose Current goal still says "Run Phase 11 ... first ... Then resume Phase 10
  ... step 0 (fable-orchestrator removal)", mermaid starting `S["ship this branch"]`.
- Since then, three accepted order/topology changes: the 2026-09-24 SUPERSEDED
  ruling (fable removal NOW — `task_plan.md` § Current Phase), the plugin-removal
  pipeline landing (#1373), and the 2026-09-25 ruling "this FIRST, then the
  fable-orchestrator remainder, then the 2026-09-24/25 session remainder, then
  Phase 11" (`task_plan.md` § 2026-09-25 step 0).
- The handoff branch (`git status`: plan-pointer.json + agent-briefs report)
  touches no goal-history. `.claude/rules/goal-history.md`: "After an accepted
  goal change, orchestration-topology change, major milestone, landing, or
  handoff, append one iteration ... before advancing."
- Rewrite: append `dotfiles-goal-20260925-035` on this branch. `Changed
  requirement:` "Order: 2026-09-25 step 0 (/doctor, one /claude-api subcommand)
  -> fable-orchestrator remainder -> 2026-09-24/25 session remainder -> Phase 11
  -> Phase 10. Landed: dotfiles#1363, #1368, #1373; knowledge-base#811, #812."
  Mermaid: `S0["step 0: /doctor + /claude-api"] --> F["fable remainder"] -->
  R["session remainder"] --> P11["Phase 11"] --> P10["Phase 10"]`. Check no
  other session already wrote 035 first.

### F3 [FIX-NOW] task_plan.md has TWO "ACTIVE" phases and a ten-day-stale "## Next Step"

- `task_plan.md:800` "## 2026-09-25 step 0 — ACTIVE, NEXT SESSION" (matches
  `docs/agents/plan-pointer.json` `active_phase`) vs `task_plan.md:815`
  "Phase 11 — ACTIVE." under `## Current Phase`, while `task_plan.md:509` says
  Phase 11 is "QUEUED behind the 2026-09-24 fable-orchestrator removal section".
- `task_plan.md:71` `## Next Step` still prescribes the 2026-09-15 triage order
  ("Phase A — land PR #1128 ... Do not start Phase B before this is complete").
  A fresh session reading top-down meets this first.
- Rewrite line 815: `Phase 11 — QUEUED (4th in the 2026-09-25 order: step 0 ->
  fable-orchestrator remainder -> 2026-09-24/25 session remainder -> Phase 11).
  Its internal order when it resumes (Ray, 2026-09-23 rounds 6-7 and 2026-09-24
  delta rulings):`
- Rewrite `## Next Step` body: `See "## 2026-09-25 step 0" (ACTIVE). The
  2026-09-15 Phase A-G order is ARCHIVED (superseded by Phases 9-11 and the
  2026-09-24/25 sections); issue-triage-2026-09-15.md stays the per-issue
  disposition authority.` Move Phases A-G under `## ARCHIVE`.

### F4 [FIX-NOW] Current Phase item 0 and the fable "Status" block are stale

- § Current Phase item 0: "Ship `docs/session-2026-09-23d-handoff` ... BEFORE
  dispatching any #1351 ticket." Probe: iteration 034 (that branch's content) is
  on `origin/main`. `git log origin/main..docs/session-2026-09-23d-handoff`
  still lists 11 commits — squash-merge makes them unreachable, so ancestry is
  the wrong test (`graphify-first.md`). Control: 032/033 present on both refs.
- Same block: "DONE and committed, **unshipped**" three lines above "both removal
  branches landed as knowledge-base#811 and dotfiles#1363".
- "Next, in order" is numbered 1, 3, 4 — item 2 missing; a reader cannot tell a
  deletion from a skipped renumber.
- Rewrites: item 0 -> `0. DONE: the docs/session-2026-09-23d-handoff content is
  on main (goal-history 034 present).`; "DONE and committed, **unshipped**:" ->
  `DONE, committed and LANDED (dotfiles#1363, knowledge-base#811):`; renumber
  to 1, 2, 3.

### F5 [FIX-NOW] fable section: V4 contradicts remainder item 1; F2 cites a stale SHA; pointer sentence false

- Fable section lists "**V4:** retire 'while Claude tokens are constrained' ...
  Edit the sol files" as open work, while § 2026-09-24/25 session remainder
  item 1 says "Audit C5 SUPERSEDES the fable section's V4". Executing in the
  ruled order does V4 alone first, then C5 again.
- "F2: ... The dotfiles graph has been stale since `3db81d8e`." Probe:
  `mise run graphify-health` rc=3 "graph built at 9c624360" (HEAD c4806bf4) —
  rebuilt since, stale again for another reason.
- "This heading carries the `plan-pointer` token until #1354 (D3)." Probe:
  working-tree plan-pointer `active_phase` = "2026-09-25 step 0 — ACTIVE, ...".
- Rewrites:
  - V4 -> `- **V4:** SUPERSEDED by session-remainder item 1 (audit C5); do it
    there, once.`
  - F2 -> `- **F2:** after the branches land, run \`mise run graphify-rebuild\`
    and require \`mise run graphify-health\` rc=0 (2026-09-25: rc=3, built
    9c624360, 23 corpus files changed).`
  - Pointer sentence -> `The plan-pointer moved to "## 2026-09-25 step 0" on
    2026-09-25; this section is QUEUED second.`

### F6 [FIX-NOW] plugin-removal skill: its "verify" step uses a doctor call that can only pass

- `.claude/skills/plugin-removal/SKILL.md` step 4: "verify both guards:
  `mise run plugin-health` / `mise run doctor`".
- `mise.toml` `[tasks.doctor]` comment: "ALWAYS exits 0 (findings included) ...
  `-- --strict` exits 1 for use as a gate"; `doctor.py:1473`
  `return 1 if (drifted and strict) else 0`. So rc can never report a
  re-appeared plugin — a probe with no failing arm
  (`probes-need-a-control-arm.md` rule 2).
- Rewrite step 4:
  ```bash
  mise run plugin-health            # rc is the verdict
  mise run doctor -- --strict       # rc=1 on ANY drift, incl. removed-plugins
  ```
  "Both must exit 0. `mise run doctor` without `--strict` always exits 0 and
  proves nothing."

### F7 [FIX-NOW] plugin-removal skill does not say `--apply` edits a TRACKED file (doctor.toml), so it must run on a branch

- `plugin_remove.plan()` always appends `add-to-watchlist` ("doctor.toml text
  edit", `plugin_remove.py:522-526`) unless the name is already watched;
  `add_to_watchlist` writes `<cwd>/doctor.toml` (`plugin_remove.py:1802-1830`).
  Settings-key steps also rewrite `<project>/.claude/settings*.json`.
- The skill orders "Apply repository edits on branches" (step 2, about
  references) and puts ship in step 5, but never says the `--apply` in step 3
  itself produces a dotfiles diff. `branch_guard` only intercepts
  Edit/Write/NotebookEdit (`do-not.md` #9), so a python write on `main` is not
  caught until pre-commit.
- Rewrite step 3's apply paragraph: "Create the dotfiles branch (and a branch in
  every repository whose project settings the plan names) BEFORE `--apply`: it
  appends the bare plugin name to `doctor.toml` `[removed_plugins].names` and
  minimally edits project `settings*.json`, all tracked. Backups land in
  `.agent/state/plugin-remove/<UTC stamp>/`."

### F8 [FIX-NOW] plugin-removal skill step 2 would have an agent delete the watchlist entry and test fixtures

- Step 2: "Remove live instruction or configuration references, keep historical
  records". Probe: `mise run plugin-inventory -- ponytail@ponytail --json`
  rc=0, 31 `references`; the first is `doctor.toml:291 names = ["ponytail",
  "claudex-loop"]` and 27 more are `tests/test_plugin_{inventory,remove}.py`
  fixtures. Both are "configuration"/code references that MUST stay — the
  watchlist line is the reappearance guard the removal itself adds.
- Control arm: same command on `code-review@claude-plugins-official` (enabled)
  -> 6 locations, 1 claude_cli, 2 project_settings, so the probe discriminates.
- Rewrite step 2 first sentence: "Review every `references` hit. Remove live
  instructions that tell a reader to USE the plugin, and live configuration that
  enables it. KEEP: the `doctor.toml` `[removed_plugins]` entry (the guard),
  test fixtures, and historical records (specs, reports, receipts)."

### F9 [FIX-NOW] plugin-removal skill says "apply that same plan" — apply re-derives it

- `plugin_remove_main` (`plugin_remove.py:1993-2023`) re-runs `inventory()` and
  `plan()` on every invocation; `--apply` never reads a saved plan and prints
  only per-step results, not the plan it executed.
- Blocked apply returns rc=2 (`apply()`, `plugin_remove.py:1953-1955`); the
  skill documents only "A blocked dry run exits 1".
- Rewrite: "After explicit approval, run the dry run again immediately before
  `--apply` and change nothing in between: `--apply` re-inventories and
  re-plans, so a state change between the two runs executes a plan you did not
  review. A blocked `--apply` exits 2 without mutating; any failed step stops
  the run with that step's rc."

### F10 [FIX-NOW] plugin-removal skill names a nonexistent task `mise run kb-review`

- Skill step 5: "In knowledge-base run `mise run kb-review` before
  `mise run kb-ship`". Probe: `mise tasks ls` in knowledge-base lists
  `kb-land`, `kb-review-receipt`, `kb-ship` (control arm — the sibling tasks
  resolve) and no `kb-review`; `kb-review` is a SKILL
  (`knowledge-base/.claude/skills/kb-review`), whose last step is
  `mise run kb-review-receipt`, which `kb-ship` requires.
- Same wording originates in the base spec (`plugin-remove-pipeline.md:192-193`
  "`kb-review` → `kb-ship`/`kb-land`").
- Rewrite: "In knowledge-base invoke the `kb-review` skill (it ends with
  `mise run kb-review-receipt`, which `kb-ship` checks), then `mise run kb-ship`,
  and `mise run kb-land -- PR_NUMBER` after merge."

### F11 [FIX-NOW] the skills cite only the base spec, whose mechanics r2/r3 overrode; r2 claims to be the last round

- Both skills: "The mechanics are defined by / The implementation contract is
  `docs/specs/plugin-remove-pipeline.md`". The base spec has no forward pointer
  to r2/r3 (grep for `r2|r3|superseded` in it: 0 hits) and still says
  `plugin_remove_main ... default prints the plan and exits 0` (`:141`) — code
  exits 1 on blockers (r2); the base prescribes `mise run doctor` (see F6) and
  `kb-review` (F10).
- `plugin-remove-pipeline-r2.md:7-8`: "This is the LAST respec round on this
  diff." — r3 exists ("Ray-approved extra round").
- `plugin-remove-pipeline-r3.md:8`: "Implementer `codex-sol-implementer`" — the
  #1373 commit body says r3 was "Implemented by an Opus FALLBACK lane (codex
  unavailable: usage limit until 2026-09-30)".
- Rewrites:
  - Both skills: "The contract is `docs/specs/plugin-remove-pipeline.md` as
    amended by `-r2.md` and `-r3.md` (later files win); the code in
    `python/src/dotfiles_setup/plugin_remove.py` is authoritative where they differ."
  - Base spec, under the Status line: `Amended by plugin-remove-pipeline-r2.md
    and -r3.md (later wins). Shipped as #1373.`
  - r2 line 7-8: `This was planned as the last respec round; Ray approved one
    more (r3, 2026-09-25).`
  - r3 line 8: append `Executed by an Opus fallback lane (codex usage limit);
    deviations D1, D2 ratified — see the #1373 commit body.`

### F12 [FIX-NOW doc / PLAN code] "ship watches checks to green" survives in 4 places #1368 did not update

- #1368 rewrote `.claude/rules/gh-cli-watch.md:3-5`: "`mise run ship` arms GitHub
  auto-merge and returns ... a returned `ship` is NOT green CI". Code agrees:
  `python/src/dotfiles_setup/pr.py:24-31` ("native auto-merge, no polling ...
  and returns").
- Still asserting the opposite:
  1. `.claude/rules/mise-tasks-only.md:24` — "`mise run ship`/`land` already watch".
  2. `mise.toml:971` `[tasks.ship] description = "Gate matrix → push → open/update
     PR → watch checks to verified green"` (shown by `mise tasks ls`).
  3. `hook_guard.py:504-507` deny text for `gh pr create`: "... then watches
     checks to bucket-verified green".
  4. `hook_guard.py:568-570` deny text for `gh pr checks --watch`: "`mise run
     ship` already watches PR checks to bucket-verified green".
  Items 3-4 are the text a model reads AT the moment it is redirected — the
  exact point the contradiction does most harm.
- Rewrites:
  1. (FIX-NOW) mise-tasks-only row: `| \`gh pr checks … --watch\` (hand-rolled CI
     wait) | \`mise run ship\` arms auto-merge and returns; wait for the merge
     with \`mise run bounded-wait -- --deadline <s> --cmd 'test "$(gh pr view <n>
     --json state --jq .state)" = MERGED'\`, then \`mise run land -- <n>\`;
     one-shot read: \`gh pr checks <n> --json name,bucket\` |`
  2. (PLAN, python/mise.toml) task description: `"Gate matrix → push →
     open/update PR → arm auto-merge (returns; GitHub merges on green ci-gate)"`.
  3-4. (PLAN) replace "then watches checks to bucket-verified green" with
     "then arms GitHub auto-merge and returns" and "`mise run ship` already
     watches PR checks" with "`mise run ship` arms auto-merge; wait with
     `mise run bounded-wait`, then `mise run land`". Needs the guard-message
     tests updated in the same change.

### F13 [FIX-NOW] do-not.md #6 still frames `gh run watch` as usable-but-untrusted

- `.claude/rules/do-not.md:27` "**Do NOT trust `gh run watch --exit-status`.**
  Verify with `gh pr checks <n> --json` or `gh run list --json`." — but the
  guard now DENIES `gh run watch` outright (`hook_guard.py:557-558`) and
  gh-cli-watch.md says so. A reader infers "run it, then cross-check".
- Rewrite: `6. **Do NOT run \`gh run watch\` or \`gh pr checks --watch\`** —
  guard-denied; \`--exit-status\` has reported 0 prematurely. Read state
  one-shot: \`gh run view <id> --json conclusion\` / \`gh pr checks <n> --json
  name,bucket\`.`

### F14 [PLAN] this session's own loaded rules are the PRE-#1368 text

- The rule text injected into this subagent's context (from the coordinator
  session) is the pre-#1368 version: gh-cli-watch "Always use `--watch`"
  with `gh pr checks 123 --watch` patterns; verify-before-advancing
  "`gh pr checks <n> --watch` until terminal"; `.claude/CLAUDE.md` "There is
  no `grok` here". On disk (HEAD c4806bf4) all three were rewritten.
  So every subagent this session spawns still receives instructions the repo
  retired — and two of them (the `--watch` patterns) are now guard-DENIED.
- Consequence for the handoff: the `/clear` is load-bearing, not cosmetic.
- Rewrite (add to the § 2026-09-25 step 0 preamble in task_plan.md):
  `Start with /clear, not /resume: the 2026-09-24/25 session's eager rules
  were loaded before #1368 landed and are stale in its context.`

### F15 [FIX-NOW] step 0's load-bearing premise "neither repo imports an Anthropic SDK" is FALSE

- `task_plan.md` § 2026-09-25 step 0, item 2: "Measured input (2026-09-25):
  neither repo imports an Anthropic SDK; ... knowledge-base pins model ids in
  `python/src/kb_setup/graphify_native_extract.py`, `.../model_limits.py` and
  `mise.toml`."
- Probe: `knowledge-base/python/src/kb_setup/model_limits.py:85`
  `from anthropic import Anthropic` and `:351` `import anthropic` (function-local
  imports), and `knowledge-base/pyproject.toml:31` `"anthropic>=1.0.0"` with the
  comment "a dependency we import must be one we name".
- Probe discipline note: my first route (`git grep -E "^\s*(import anthropic|from
  anthropic)"`) returned 0 in both repos — `\s` is not ERE, so it could only
  match column-0 imports. A second route (`git grep -nw anthropic -- '*.py'`)
  found both. The plan's "measured" 0 was very likely the same blind probe.
  Dotfiles: 0 on both routes (control: `import json|subprocess` counts > 0).
- Why it matters: the `$CC/commands.md:66` `/claude-api` row says `upgrade`
  moves "the Python `anthropic` package from 0.x to 1.x" and `cost-optimize`
  profiles API spend — both are live options for KB, and the skill "activates
  automatically when your code imports `anthropic`". The recommendation Ray is
  owed is built on the false negative.
- Rewrite: "Measured input (2026-09-25, re-probed): dotfiles imports no Anthropic
  SDK and pins no Claude model id in code. knowledge-base DOES import the
  `anthropic` SDK (`python/src/kb_setup/model_limits.py:85,351`, dependency
  `anthropic>=1.0.0` at `pyproject.toml:31`, used for `GET /v1/models`) and pins
  model ids in `graphify_native_extract.py`, `model_limits.py` and `mise.toml`.
  `prompt-audit` already ran on dotfiles (#1368); knowledge-base's prompt surface
  and its SDK usage are both unaudited."

### F16 [FIX-NOW] step 0 item 1 has no output location and no definition of "disposition"

- "Run Claude Code's built-in `/doctor` ... and disposition every finding." No
  file receives the dispositions, no disposition vocabulary, and no rule for a
  finding that needs a code change (branch? ticket?). Session-handoff will have
  nothing to audit.
- Rewrite: "1. Run the built-in `/doctor` (not `mise run doctor`). Record every
  finding verbatim in `docs/research/kb/reports/agents/claude-doctor-2026-09-25.md`
  with one disposition each: FIXED (commit SHA on a branch), FILED (issue #),
  ACCEPTED (reason + who ruled), or NOT-OURS (user-global/harness; cite the file).
  A fix to a tracked file goes on a branch and ships via `mise run ship`."

### F17 [FIX-NOW] docs/rules-evidence/long-running-command-hangs.md cites a renumbered rule

- #1368 deleted `ci-local-parity.md` "Rule 5: Clear hk cache" (whose body said
  "Kept as a numbered rule so references to 'rule 5' stay valid") and renumbered
  Rule 6 to Rule 5 (`ci-local-parity.md:53` "## Rule 5: Test new hk steps locally").
- `docs/rules-evidence/long-running-command-hangs.md:113`: "the cache has been
  content-hashed since hk 1.47 (`ci-local-parity.md` rule 5)" — now points at
  the unrelated "Test new hk steps" rule. Control: other numbered refs
  (`ci-local-parity.md` rule 3 in `context7-cli/SKILL.md:10`, rule 2 in
  `mise.toml:137`) still resolve to the right rules.
- Rewrite: "the cache has been content-hashed since hk 1.47 (formerly
  `ci-local-parity.md` rule 5, retired in #1368)."

### F18 [FIX-NOW, LOW] .claude/CLAUDE.md says AGENTS.md "sits at" the 12,000-char cap without the cap's owner

- `.claude/CLAUDE.md:4-5` "`AGENTS.md` sits at agnix AGM-003's 12,000-char cap".
  Probe: 11,517 characters (11,605 bytes), 191 lines — 483 characters of headroom.
  `md-size-budgets.md:46-52,81` says that ceiling is Windsurf's, enforced by
  agnix — the exact provenance-loss this repo's rules warn about
  (`verify-before-advancing.md` "Carry a number with its CONDITION").
- Rewrite: "`AGENTS.md` is within ~500 characters of the 12,000-character ceiling
  agnix AGM-003 enforces (Windsurf's per-file limit; see
  `.claude/rules/md-size-budgets.md`), so anything Claude-specific ..."

### F19 [FIX-NOW, LOW] session-remainder item 5 names a clock time with no timezone

- "After the codex quota resets (2026-09-30 16:05)". A codex/remote lane or a
  fresh session cannot tell local from UTC.
- Rewrite: "(2026-09-30 16:05 <ZONE>, as printed by the codex usage-limit
  message)". The zone is not recorded anywhere I could find; the coordinator
  must fill it from the original message rather than guess.
- Item 6 verified: `mise run plugin-inventory -- ponytail@ponytail --json` rc=0 ->
  0 locations, 10 `worktree_settings` (5 dotfiles incl. one under
  `~/.codex/worktrees`, 5 knowledge-base), 3 `stale_worktrees` (all KB, under
  `/private/tmp/.../scratchpad/`), 0 errors. Control arm: an enabled plugin gave
  6 locations. The plan's "10 (5 dotfiles, 5 KB)" and "3 prunable KB" hold.

### F20 [PLAN] prompt-audit summary says the grok text is load-bearing; #1368 removed it and changed the eval

- `docs/research/kb/reports/prompt-audit-2026-09-24.md:86`: "**F-A3 is withdrawn.**
  The grok text is load-bearing: eval `tier1.lanes-declared-or-degraded` requires
  `.claude/CLAUDE.md` to declare grok 'NOT installed'."
- Same PR (#1368, `d1fe8efc`) then removed the grok section from
  `.claude/CLAUDE.md` (now "### Lane routing — codex and Claude only") AND changed
  `eval_cases.py:42-49` to `DECLARED_LANES = ("codex", "agy")`,
  `FALLBACK_TOKENS = ("terminal fallback is Claude Opus",)`. The task_plan
  session-remainder section cites this report as evidence, so a reader applying
  "report A" findings will skip F-A3 for a reason that no longer exists (and may
  try to restore grok text).
- Rewrite: do not edit the synthesis body (records stay verbatim); append
  `> **2026-09-25 correction:** F-A3 was applied after all — #1368 retired grok
  from DECLARED_LANES and re-keyed FALLBACK_TOKENS to "terminal fallback is Claude
  Opus" (eval_cases.py:42-49). The withdrawal note above is historical.`

### F21 [FIX-NOW, LOW] plugin-inventory skill: "historical documentation paths" and "live repository" are undefined

- Skill: "`references` excludes historical documentation paths." The actual set
  is `plugin_inventory.HISTORICAL_PATHSPECS` (`plugin_inventory.py:28-36`):
  docs/research, docs/agents/goal-history.md, docs/receipts, docs/specs,
  docs/direction, docs/artifacts, docs/rules-evidence. A reader cannot tell
  whether e.g. `docs/handoffs/` or `.agent/` hits are "live".
- The repo set scanned is derived from `root=~/dev/github` (hard-coded in
  `plugin_remove_main`, `plugin_remove.py:2008`), not from the current repo —
  the skill never says references span every clone under that root.
- Rewrite: "`references` are `git grep` hits in every repository under
  `~/dev/github`, excluding `HISTORICAL_PATHSPECS` in
  `python/src/dotfiles_setup/plugin_inventory.py` (docs/research, docs/specs,
  docs/receipts, docs/rules-evidence, docs/direction, docs/artifacts, and
  goal-history). Everything else — including tests and `doctor.toml` — is
  reported and must be judged (see plugin-removal step 2)."

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — audited diff, task_plan, specs, skills, rules, python sources; read issue #1370.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `mise tasks ls` (kb-review), `pyproject.toml`, `kb_setup/model_limits.py`, offline `$CC/commands.md`.
