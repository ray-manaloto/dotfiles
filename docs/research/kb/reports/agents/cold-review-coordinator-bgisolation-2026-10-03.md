# Cold review — 186233e4..7168105b (coordinator bgIsolation + main-checkout write guard)

- Reviewer: cold-reviewer (Claude Opus), diff-only, by ref. Round 1 (open hunting).
- Range: `186233e4612566554f2b82a15228a57a4f7f7eec..7168105b486f12165ce812a337bd6250cadc5530`
  (commits `abc117c6`, `7168105b`). Worktree HEAD == `7168105b`; `git status` shows no modification to any
  reviewed file (only two untracked reports), so working-tree runs exercise the reviewed code. All line
  numbers below are from `git show 7168105b:<path>`.
- Memory: this worktree's `.claude/agent-memory-local/cold-reviewer/` was EMPTY (memory: local is per-checkout).
  I read the main checkout's cold-reviewer memory instead (`harness_identity_facts.md`, `review_method.md`,
  `mutation_harness.md`, `contract_token_and_mirror_replay.md`, `reference_dotfiles_gate_internals.md`).
- Status: COMPLETE.

## Verdict: SHIP-WITH-FIXES

The guard's core decision is correct on every cell the spec enumerates, and the tests genuinely constrain it
(mutation table: 7 of 9 mutants killed; the 2 survivors are an equivalent check and an unpinned order). The
launcher change is correct and narrowly scoped. Two MEDIUM findings are guidance/ordering defects that steer a
coordinator into the exact harms the pair exists to prevent (F1: branching the shared main checkout; F2:
re-entering the worktree isolation that blocks planning-file edits). Both are small fixes inside this unit of work.

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| F1 | MEDIUM | On a main checkout sitting on `main` (its state right now), a coordinator's tracked write gets `branch_guard`'s remedy `git checkout -b <type>/<slug>` FIRST. Following it switches the SHARED main checkout's branch (what guard spec §1 protects: ship/land run there), and the retried edit is then denied by the coordinator guard anyway. abc117c6's SKILL.md sentence "must still branch before editing tracked files (do-not #9, branch_guard)" actively prescribes that branch switch, and 7168105b left it beside the contradicting new sentence. | `python/src/dotfiles_setup/hook_guard.py:1099-1103`; `python/src/dotfiles_setup/branch_guard.py:68-79`; `.claude/skills/coordinator-handoff/SKILL.md:74-78` (+ mirror `.agents/skills/coordinator-handoff/SKILL.md:74-78`) | Arm `/tmp/cr-bgiso/order.py` (real git, `decide_payload("Write", tracked, session_id=<coordinator>)`): on `main` → "You are on the default branch (main)… `git checkout -b <type>/<slug>`… Then re-run this edit"; after `git checkout -b feat/x` → "Coordinator writes in the main checkout are limited to git-ignored paths…". Live main checkout `rev-parse --abbrev-ref HEAD` → `main`. Order is mandated by `docs/specs/coordinator-main-checkout-guard-2026-10-03.md:37`, so the defect is spec-level. No test pins either order (mutant M9 survived). Fix: for a coordinator session, decide the coordinator guard before `branch_guard` (or have `branch_guard`'s reason defer to it), and rewrite SKILL.md:74-76. |
| F2 | MEDIUM | The deny remedy "EnterWorktree name=<branch-slug>, then edit the worktree copy" leads back into the motivating failure: once a session has entered a worktree, Claude Code blocks Edit/Write/NotebookEdit on ANY main-checkout path (task_plan.md included), and `bgIsolation` documents only the pre-EnterWorktree block. Neither the reason nor SKILL.md says to `ExitWorktree` before the next planning-file edit. | `python/src/dotfiles_setup/coordinator_write_guard.py:79-83`; `.claude/skills/coordinator-handoff/SKILL.md:77-78` | `$CC/worktrees.md:81-89` ("While a session is isolated in a worktree … The same rules apply whether … Claude entered a worktree with `EnterWorktree`"; "File edits: … blocks an `Edit`, `Write`, or `NotebookEdit` that targets a path in the main checkout"); `$CC/settings-reference.md:4965-4972` (`"worktree"` blocks "until the session calls EnterWorktree"; `"none"` is silent about after). The bgisolation spec measured that in-worktree refusal itself (`docs/specs/coordinator-bgisolation-2026-10-03.md:9`). Runtime behaviour of `"none"` AFTER EnterWorktree: UNVERIFIED (doc-derived; I cannot call EnterWorktree from this lane). |
| F3 | LOW | "Main checkout" is ANY repository's primary worktree, not this project's: a coordinator write to a tracked file in a sibling repo (the knowledge-base clone, an additional working directory) is DENIED with a remedy (`EnterWorktree`, which creates worktrees of the session's own repo) that cannot apply. Pre-change bg isolation skipped such writes ("The write is outside the working directory"), so this is a new restriction beyond spec §1's stated objective. `hook_dispatch` already holds `project_root` but does not pass it. | `python/src/dotfiles_setup/coordinator_write_guard.py:36-47`; `python/src/dotfiles_setup/hook_dispatch.py:55-60` | Arm A4: second repo on `main`, coordinator id → DENY, reason "…EnterWorktree name=<branch-slug>…". Live: `rev-parse --show-toplevel` in `~/dev/github/ray-manaloto/knowledge-base` → itself (a primary checkout); `~/.claude`, `~/.config/mise`, `~/.config`, `$HOME` → "not a git repository" (so auto-memory writes are unaffected). Doc: `$CC/agent-view.md:497`. The spec's generic definition: `docs/specs/coordinator-main-checkout-guard-2026-10-03.md:39`. |
| F4 | LOW | `git-dir == common-dir` also holds for a nested repo and for a submodule, so both are misclassified as "main checkout": a nested clone under ignored `.agent/` is DENIED although spec §1 lists `.agent/**` as allowed, and a submodule inside a LINKED worktree is DENIED although linked worktrees are allowed. | `python/src/dotfiles_setup/coordinator_write_guard.py:46-47` | Arm A3: `.agent/clone/` repo, outer `check-ignore` rc 0, guard → DENY (control `.agent/plans/x.md` → ALLOW). Arm A5: submodule in `.claude/worktrees/lane/sub` → rev-parse git-dir == common-dir == `.git/worktrees/lane/modules/sub` → DENY (control linked file → ALLOW). Real-world: no `.gitmodules` at 7168105b; one nested repo exists under the main checkout (`.agent/state/hk-v2-migration-pytest/…/repo/.git`, test residue). Fix: ask `check-ignore` of the OUTER repo first, or compare the root to `session_common.main_checkout(project_root)`. |
| F5 | LOW | Writes inside `.git/` fail OPEN (rev-parse `--show-toplevel` exits 128 there), so a coordinator can append to `.git/info/exclude` and thereby turn any NEW tracked-to-be path from DENY into ALLOW. Deliberate-bypass shape only. | `python/src/dotfiles_setup/coordinator_write_guard.py:40-42` | Arm A2: `.git/info/exclude` → ALLOW, `.git/hooks/pre-commit` → ALLOW; `new.md` DENY → append `new.md` to `.git/info/exclude` → ALLOW. |
| F6 | LOW | A path whose DIRECTORY components differ in case from the on-disk spelling (APFS is case-insensitive) is ALLOWED: `resolve()` keeps the caller's case while git reports the canonical toplevel, so `is_relative_to(root)` is false and the guard fails open. Same class already present in `branch_guard`. | `python/src/dotfiles_setup/coordinator_write_guard.py:47`; `python/src/dotfiles_setup/branch_guard.py:164` | Arm A1: `…/arms/MAIN/tracked.md` (exists: True) → ALLOW; control `…/arms/main/tracked.md` → DENY; A1b case-folded basename → DENY (git index lookup is case-insensitive). |
| F7 | LOW | Q-CLAIM: "Coordinator writes in the main checkout are limited to git-ignored paths" (deny reason, SKILL.md:77, commit message) has no enforcing line for Bash: `sed -i`, heredocs and `git checkout` in the main checkout are untouched. Not a regression — `bgIsolation: "worktree"` also blocked only Edit/Write before EnterWorktree — but the sentence over-claims. | `python/src/dotfiles_setup/coordinator_write_guard.py:19`, `:79-83`; `.claude/skills/coordinator-handoff/SKILL.md:77` | `_TOOLS = {"Edit","Write","NotebookEdit"}`; `$CC/settings-reference.md:4965-4972`. Narrow the sentence to "Edit/Write/NotebookEdit". |
| F8 | LOW | After `/clear` the hook's `session_id` changes, while the job record stays keyed by the launch id's directory, so the identity lookup most likely misses and a /cleared coordinator is unconfined (fail open). | `python/src/dotfiles_setup/coordinator_write_guard.py:64-68`; `python/src/dotfiles_setup/session_common.py:72-91` | `$CC/env-vars.md:352` (hook `session_id` "is updated on `/clear`"); `$CC/glossary.md:271` ("Running `/clear` starts a new session"). Whether the harness re-keys `~/.claude/jobs/<id8>/` on /clear: UNVERIFIED — 58/58 live records have `dir == sessionId[:8]`, which cannot discriminate. The module docstring names only "job record cannot be read". |
| F9 | INFO | The fail-open docstring is not total: `session_common.default_jobs_dir()` (`Path.home()`, can raise `RuntimeError`) runs before the `try`, and an exception there also skips `script_guard` in the same `or` chain. | `python/src/dotfiles_setup/coordinator_write_guard.py:64-69`; `python/src/dotfiles_setup/hook_guard.py:1099-1103` | Code read; needs an unresolvable HOME, so practically unreachable. |
| F10 | INFO | No `suites.toml`/`hk.pkl` contract names the new module; the wiring is bound by pytest only (adequate: deleting it fails 5 tests), while the edited `workflow.*branch*` token `"branch_guard.decide(tool_input)"` no longer binds the `policy_reason =` assignment. | `python/verification/suites.toml:2592` | `grep -c coordinator_write_guard` suites.toml → 0, hk.pkl → 0 (control `branch_guard` in suites.toml → 6). Mutant M1 → 5 failed. |

## Q-FRESH / Q-SCOPE / Q-CLAIM

- **Q-FRESH:** the one decision→action pair is hook verdict → harness write. Identity, topology and ignore state are
  all re-read on every call; nothing is cached. The residual window (a file force-added between `check-ignore` and
  the write) is negligible. No finding.
- **Q-SCOPE:** F1, F2, F7 are in scope (strings and order this diff adds). F3-F6 are in scope for the guard but
  could be ticketed as a "topology precision" follow-up. F8 is a sibling of the coordinator-handoff identity
  design (same lookup in `coordinator_handoff`), ticket-worthy. F9/F10 informational.
- **Q-CLAIM** (every operator-facing string the diff adds):

  | String / clause | Enforcing line | Outcome |
  |---|---|---|
  | reason: "Coordinator writes" | `coordinator_write_guard.py:67` (+ `:19` tools) | Edit/Write/NotebookEdit only → F7 |
  | reason: "in the main checkout" | `:46-47` | any repo's primary checkout, nested repos, submodules → F3, F4 |
  | reason: "are limited to git-ignored paths" | `:74-76` | `.git/**` fail-open → F5; case-fold → F6 |
  | reason: "{path} is not ignored" | `:75` (rc 1) | holds (force-added tracked file → DENY, arm A8) |
  | reason: "EnterWorktree name=<branch-slug>, then edit the worktree copy" | none | wrong for foreign/nested repos (F3, F4); incomplete without ExitWorktree (F2) |
  | SKILL.md:74-76 "must still branch before editing tracked files (do-not #9, branch_guard)" | `branch_guard` | stale and harmful after 7168105b → F1 |
  | SKILL.md:77-78 "confines main-checkout writes to gitignored paths; enter a linked worktree…" | as reason | F2, F7 |
  | `launch_argv` docstring "accept cross-session inbound and edit the working copy" | `coordinator_handoff.py:110-113` | holds; nested `--settings` object UNVERIFIED live (spec P7). `--settings` keys override same keys (`$CC/cli-reference.md:127`); no `worktree` key in project or user settings to shadow (`grep -c '"worktree"'` → 0 and 0; controls `"matcher"` 4, `"permissions"` 1) |
  | module docstring "Every unresolvable step fails OPEN" | `:69-78` | F9 |
  | commit msg "allows ignored paths (task_plan.md, .agent/**)" | `:74-76` | nested repo under `.agent/` → F4 |

## Launcher change (abc117c6) — verified correct

- `CROSS_SESSION_SETTINGS` is built with `json.dumps(..., separators=(",", ":"))`
  (`python/src/dotfiles_setup/coordinator_handoff.py:110-113`); the only code consumer is `launch_argv`
  (`:730-732`), used at `:914`. `parallel-work-split` lane launches still pass `{"crossSessionInbound":"accept"}`
  only (`.claude/skills/parallel-work-split/SKILL.md:106`), so lanes keep isolation as the spec requires.
- The new test parses the emitted argv JSON and asserts both keys (`tests/test_coordinator_handoff.py:524-539`).
- Specs updated consistently (`docs/specs/coordinator-auto-handoff-2026-10-02.md:136`, requirements `:16`).

## Arms run (scratch: /tmp/cr-bgiso, deleted at end)

- `uv run --project python pytest tests/test_coordinator_write_guard.py tests/test_coordinator_handoff.py tests/test_branch_guard.py -q` → 293 passed, rc=0.
- `/tmp/cr-bgiso/probe.py` (real git, `GIT_CONFIG_GLOBAL=/dev/null`): controls tracked→DENY, task_plan→ALLOW;
  A1 case-folded dir component→ALLOW; A1b case-folded basename→DENY; A2 `.git/info/exclude`→ALLOW,
  `.git/hooks/pre-commit`→ALLOW, `new.md` DENY→ALLOW after appending it to `.git/info/exclude`; A3 nested repo
  under ignored `.agent/`→DENY (outer `check-ignore` rc 0), control `.agent/plans/x.md`→ALLOW; A4 foreign repo→DENY;
  A5 submodule inside a linked worktree→DENY, control linked file→ALLOW; A6 tracked symlink→ignored target→ALLOW
  (resolved target is ignored; no such tracked symlink exists in the repo — the one tracked symlink points at a
  tracked file); A7 `<linked>/../../../tracked.md`→DENY; A8 force-added ignored path→DENY.
- `/tmp/cr-bgiso/order.py`: F1.
- `/tmp/cr-bgiso/realworld.sh`: one nested `.git` under the main checkout outside worktrees, control 13 under
  `.claude/worktrees`; no `.gitmodules`; one tracked symlink.
- `/tmp/cr-bgiso/jobs.py` (counts only): 58 job records, all `dir == sessionId[:8]`; `name` present in 57; 18
  coordinator-named.
- Mutation table (`git archive 7168105b python/src tests scripts` + `PYTHONPATH`, import verified to resolve to the
  copy; `-k "not wrapper"` deselects the 3 shell-wrapper rows):

  | Mutant | Result |
  |---|---|
  | M0 pristine control | 59 passed (control) |
  | M1 delete `decide_payload` wiring line | 5 failed (spec's mutation arm reproduced) |
  | M2 `hook_dispatch` forwards no session_id | 1 failed |
  | M3 `pretooluse_main` forwards no session_id | 1 failed |
  | M4 drop `git_dir == common_dir` | 2 failed |
  | M5 check-ignore errors deny (not tri-state) | 2 failed |
  | M6 identity check removed | 12 failed |
  | M7 git-never-ran denies | 2 failed |
  | M8 drop topology `rc != 0` check | SURVIVED — equivalent today (non-zero rev-parse prints no 3-line stdout; the fact-count check catches it) |
  | M9 coordinator guard moved after `script_guard` | SURVIVED — no test pins guard order (relevant to the F1 fix) |
- Strict `per_path_tokens` replay over suites.toml: 1414 tokens, 0 missing (supporting only; no planted control).
- `.agents` mirror of coordinator-handoff SKILL.md differs from `.claude` only in the two expected path rewrites.

## Stop condition (adversarial-review)

This round is OPEN HUNTING — no domain with a cardinality was stated — so it cannot end the loop by any outcome.
Proposed bounded round 2 domain (after F1/F2 dispositions): identity {coordinator, lane, absent, unreadable} ×
location {main tracked, main ignored, main new-in-new-dir, linked, outside, foreign primary, nested-under-ignored,
submodule-in-linked, `.git/` interior, case-folded} × main-checkout branch {default, feature} = 80 cells, plus the
enumeration question "which axis does `decide_payload` read that this table does not vary?"

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the reviewed range.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline Claude Code docs (`sources/agent-harness-docs/docs/claude-code/`) and as the live foreign-primary-checkout example for F3.
