# Cold review — `ed8e1a96...315640ba` (fix/coordinator-bgisolation-none, post-rebase)

- Base: `ed8e1a96cb54d938365ab27c872313cdb5307ed1` (= origin/main at review start)
- Head: `315640ba6df9b7c99abe38dcda21cf0ee3c74010`
- Commits: `10697c44`, `9af89e68`, `80b41204`, `315640ba`
- Reviewer: cold-reviewer (Opus), diff-only, started 2026-10-04 11:06 local
- Round type: OPEN HUNTING (no enumerated domain in the caller's brief) — per `adversarial-review`
  this round cannot end the loop by any outcome; it promotes to one bounded round.
- Memory: consulted the worktree-local index and the main-checkout cold-reviewer index
  (`write_guard_topology_review.md`, `harness_identity_facts.md`, `review_method.md`, `mutation_harness.md`).

## Status

COMPLETE.

## Verdict: SHIP

The conflict resolution is correct at both focus sites:

- `session_common.py` resolved to main's version as it stood. Its `COORDINATOR_NAME_RE` and `is_coordinator`
  match the branch's dropped hunk byte for byte in semantics.
- `coordinator_handoff.py` carries only the settings constant, the module import and one leftover alias (R2).
  Nothing of main's was lost: the base is the merge-base, and the three-dot and two-dot stats match.

The guard reorder runs the coordinator guard before `branch_guard` and `script_guard`. It does not change the deny
set: the `or` chain still reaches `branch_guard` whenever the coordinator guard returns None. A test now pins the
order (mutant M2 is killed; it survived as M9 last round).

The targeted pytest passed: 260 tests, rc=0. Every finding is LOW or INFO:

- R3-R6 are already ticketed in #1638.
- R1, R2, R7 and R8 are small, in scope, and worth fixing here, but none is a ship blocker. R1's three-line fix is
  proven: candidate C1 keeps the suite at baseline and turns the RecursionError arm from "raises" into "DENY".

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| R1 | LOW | The reorder makes an exception in the coordinator guard's identity lookup pre-empt BOTH later guards. `session_name(...)`/`default_jobs_dir()` run outside the `try`, and `read_json` catches only `OSError, ValueError`, so a deeply nested job record raises `RecursionError` out of `decide_payload`; the hook then fails open and `branch_guard`'s deny is lost. Under the old order `branch_guard` denied first. The module docstring says "Every unresolvable step fails OPEN" — it does, but for all three guards, not just itself. Reachability is low (the harness writes the record). Fix: move the identity lookup into the existing `try` (`RecursionError` is a `RuntimeError`, already caught). | `python/src/dotfiles_setup/coordinator_write_guard.py:64-69`; `python/src/dotfiles_setup/hook_guard.py:1099-1103`; `python/src/dotfiles_setup/session_common.py:64-69` | `/tmp/cr1658/recursion.py`: same tracked file on `main`, `session_id=None` → DENY (control), `session_id=<coordinator-shaped id>` → `RecursionError`. Candidate-fix column C1 in the mutation table. Extends prior F9 (INFO under the old order). |
| R2 | LOW | Conflict-resolution artifact: `COORDINATOR_NAME_RE = session_common.COORDINATOR_NAME_RE` re-adds to `coordinator_handoff` the symbol main's L0 commit `2bd5f9ed` deliberately MOVED out ("move to session_common to avoid a circular import"). It has no production consumer; its only reader is a new test assertion that checks alias identity, which can only pass. | `python/src/dotfiles_setup/coordinator_handoff.py:45`, `:77`; `tests/test_coordinator_write_guard.py:79-85` | `git grep COORDINATOR_NAME_RE 315640ba` → definitions/uses only in `session_common.py:41,96`, tests `test_coordinator_handoff.py:766,799` (via `sc.`) and `test_coordinator_write_guard.py:85` (the alias). `git show 2bd5f9ed -- coordinator_handoff.py` removes the regex and the function. Range-diff: the branch's original commit carried both aliases; the resolution dropped `is_coordinator = …` but kept this one. Fix: drop the alias, the now-unused `session_common` module import at `:45`, and the `coordinator_handoff.*` assertions in the test. |
| R3 | LOW | Carried F3, reshaped by the reorder: a coordinator write to a tracked file in a SIBLING repo's primary checkout is denied with "EnterWorktree name=<branch-slug>", which cannot apply (EnterWorktree targets worktrees of the session's own repository). When that repo is on `main`, the coordinator reason now pre-empts `branch_guard`'s applicable `git checkout -b` remedy. Unfixed: `_main_root` still never compares against the project root `hook_dispatch` holds. | `python/src/dotfiles_setup/coordinator_write_guard.py:36-47`; `python/src/dotfiles_setup/hook_dispatch.py:50-60` | Arms A2 (sibling on `main`, coordinator → coordinator reason), A2c (no session → branch_guard reason), A2f (sibling on feature branch → still DENY). EnterWorktree scope: `$CC/agent-sdk__typescript.md:2940` ("must be a registered worktree of the current repository or … of a repository nested inside it"). |
| R4 | LOW | Carried F4: `git-dir == common-dir` also holds for a nested repo, so a nested clone under ignored `.agent/` is DENIED although `.agent/**` is meant to be writable. | `python/src/dotfiles_setup/coordinator_write_guard.py:46-47` | Arm A3 → DENY; control A3c `.agent/plans/x.md` → ALLOW. Code unchanged since `7168105b` (`git diff 7168105b 315640ba -- coordinator_write_guard.py` touches only the reason string). |
| R5 | LOW | Carried F5: writes inside `.git/` fail open (`--show-toplevel` exits 128 there), so `.git/info/exclude` is writable and can turn a new path from DENY to ALLOW. | `python/src/dotfiles_setup/coordinator_write_guard.py:40-42` | Arm A4 → ALLOW. |
| R6 | LOW | Carried F6: a case-folded DIRECTORY component (APFS) fails open, because `resolve()` keeps the caller's case and `is_relative_to(root)` is false. | `python/src/dotfiles_setup/coordinator_write_guard.py:47` | Arm A5 (file exists) → ALLOW; control A5c canonical case → DENY. |
| R7 | LOW | Q-CLAIM: "Never switch the main checkout's branch" (SKILL) and "Do NOT switch the main checkout's branch." (deny reason) are unconditional and have no enforcing line (Bash `git switch` is not guarded). They contradict the main-checkout ship procedure that `pr._ship_preflight` itself prints (`git switch {branch}` and `mise run ship` in the main checkout) and that the same SKILL tells the coordinator to perform ("Before any main-checkout ship…"). The intended rule is narrower: do not switch it to make an edit. | `.claude/skills/coordinator-handoff/SKILL.md:77-78` (+ mirror `.agents/…:77-78`); `python/src/dotfiles_setup/coordinator_write_guard.py:82` | `python/src/dotfiles_setup/pr.py:621-627`; `.claude/skills/coordinator-handoff/SKILL.md:55-60`; the guard spec's own premise that the main checkout "often has another lane's PR branch checked out" (`docs/specs/coordinator-main-checkout-guard-2026-10-03.md:7`). |
| R8 | LOW | Spec drift after the F1 fix: the guard spec still mandates `branch_guard.decide(...) or coordinator_write_guard.decide(...) or script_guard.decide(...)` and cites `coordinator_handoff.py:74`/`:200-202` for symbols that now live in `session_common.py:41`/`:94-96`; the bgisolation spec still prescribes "must still branch before editing tracked files (do-not #9, branch_guard)", the guidance F1 found harmful and SKILL.md has dropped. Specs here are revised in place (the guard spec's own "Revision 2" line). | `docs/specs/coordinator-main-checkout-guard-2026-10-03.md:37`, `:86`; `docs/specs/coordinator-bgisolation-2026-10-03.md:20` | Implementation `python/src/dotfiles_setup/hook_guard.py:1099-1103`; pin `tests/test_coordinator_write_guard.py:313-328`; revision precedent `docs/specs/coordinator-main-checkout-guard-2026-10-03.md:48`. |
| R9 | INFO | The two new reason clauses ("Do NOT switch the main checkout's branch.", "ExitWorktree (keep) before the next planning-file edit.") are pinned by no test. Deleting either leaves the suite at baseline. Only `"checkout -b" not in` and the EnterWorktree clause are asserted. | `python/src/dotfiles_setup/coordinator_write_guard.py:82`, `:84`; `tests/test_coordinator_write_guard.py:309`, `:324-325` | Mutants M5 and M6 in the table below SURVIVED (2 failed = the harness baseline). |
| R10 | INFO | No `suites.toml`/`hk.pkl` contract names `coordinator_write_guard`. The two edited tokens were loosened to prefixes, and each still binds exactly one site, but neither binds the guard order or the `session_id=` forwarding. pytest does bind both (M2, M7, M8 killed). | `python/verification/suites.toml:1361`, `:2601` | `"branch_guard.decide(tool_input)"` occurs once (`hook_guard.py:1101`); `'reason = hook_guard.decide_payload('` occurs once (`hook_dispatch.py:56`). |
| R11 | INFO | Remote `main` has moved past the reviewed base: `ed8e1a96..ee3b29da` adds 2 commits (#1662, #1663). They touch `install_doctor.py`, `lane_result.py`, `sdlc_team.py`, their tests and `docs/research/kb/**`, with no file overlap with this range. So no new conflict, but the ship gates will validate a merge result this review did not see. | — | `git fetch --dry-run origin main` → `ed8e1a96..ee3b29da`; `gh api repos/ray-manaloto/dotfiles/compare/ed8e1a96...ee3b29da` file list. |
| R12 | INFO | UNVERIFIED, carried: (a) `claude --bg --settings` honouring the nested `worktree.bgIsolation` object (spec P7; no live launch from this lane); (b) prior F8: after `/clear` the hook `session_id` likely stops matching the job record, which leaves the coordinator unconfined. (b) is already in #1638. | `python/src/dotfiles_setup/coordinator_handoff.py:110-113`; `python/src/dotfiles_setup/coordinator_write_guard.py:64-68` | `docs/specs/coordinator-bgisolation-2026-10-03.md:59` (P7 marked UNVERIFIED); `gh issue view 1638` (F8 listed). |

## Q-FRESH / Q-SCOPE / Q-CLAIM

- **Q-FRESH.** The only decision→action pair is the PreToolUse verdict → the harness write. Identity (job record),
  topology (`rev-parse`) and ignore state (`check-ignore`) are re-read on every call; nothing is cached across calls.
  `CROSS_SESSION_SETTINGS` is a module constant consumed at launch time — no staleness. No finding.
- **Q-SCOPE.** R1, R2, R7 and R8 are in scope: they are produced by this range's conflict resolution or its fix
  commits (`80b41204`, `315640ba`). R3-R6 are the prior round's F3-F6, already ticketed in **#1638** (OPEN,
  "coordinator_write_guard: topology precision follow-ups (F3-F6 …, F8 /clear identity)"); recommend appending R3's
  new shape (coordinator reason now pre-empts `branch_guard`'s applicable remedy in a sibling repo on `main`) and R1
  to #1638 if R1 is not fixed here.
- **Q-CLAIM** — every operator-facing string this range adds or changes:

  | String / clause | Enforcing line | Outcome |
  |---|---|---|
  | reason "Coordinator Edit/Write/NotebookEdit" | `coordinator_write_guard.py:19`, `:62-68` | holds (prior F7 fixed) |
  | reason "in the main checkout" | `:46-47` | any repo's primary checkout and nested repos → R3, R4 |
  | reason "is limited to git-ignored paths" | `:74-76` | `.git/` interior → R5; case-folded dir → R6 |
  | reason "{path} is not ignored" | `:75` (rc 1 only) | holds |
  | reason "Do NOT switch the main checkout's branch." | none | R7 |
  | reason "EnterWorktree name=<branch-slug>, then edit the worktree copy" | none (advice) | inapplicable for sibling/nested repos → R3, R4 |
  | reason "ExitWorktree (keep) before the next planning-file edit" | doc-backed: `$CC/worktrees.md:81-89`; `ExitWorktreeInput.action: "keep"` at `$CC/agent-sdk__typescript.md:2947-2950` | holds (prior F2 fixed) |
  | SKILL "launches with `worktree.bgIsolation: "none"`" | `coordinator_handoff.py:110-113`, `:730-732` | holds in argv; CLI honouring a nested `worktree` object via `--settings` is UNVERIFIED (spec P7; no live launch here) |
  | SKILL "so it can edit the git-ignored main-checkout planning files … directly" | `$CC/settings-reference.md:4965-4972` + guard `:74-76` | holds, except nested repo under `.agent/` (R4) |
  | SKILL "denies its Edit/Write/NotebookEdit on any other main-checkout path" | `:74-76` | over-claims by R5, R6 |
  | SKILL "Bash writes are not covered, so make none" | `_TOOLS` `:19` | accurate |
  | SKILL "Never switch the main checkout's branch" | none | R7 |
  | hook_guard comment "Coordinator confinement first … Then branch protection, then script policy." | `hook_guard.py:1099-1103`; pinned by `tests/test_coordinator_write_guard.py:313-328` | holds |
  | module docstring "Every unresolvable step fails OPEN … Git errors likewise allow the write." | `:69-78` | the identity lookup is outside the `try` → R1 |
  | `launch_argv` docstring "accept cross-session inbound and edit the working copy" | `coordinator_handoff.py:110-113` | holds (P7 caveat above) |
  | test docstring "Both public consumers recognize exactly the established name grammar." | `tests/test_coordinator_write_guard.py:79-85` | the `coordinator_handoff.*` half compares an object with itself → R2 |

## Evidence log

- Worktree HEAD == `315640ba` and `git status --short` shows only this report untracked, so working-tree runs
  exercise the reviewed ref. Line numbers below are from `git show 315640ba:<path>`.
- `git range-diff 186233e4..7168105b ed8e1a96..315640ba` (pre-rebase series vs post-rebase series): commit 1
  differs only in context (main's L0 #1633 had already moved `SHIP_QUEUE`/`HANDOFF_INBOX`). Commit 2's resolution
  DROPPED the branch's own `session_common.py` hunk (main's 2bd5f9ed added the byte-identical
  `COORDINATOR_NAME_RE` regex and `is_coordinator` body — `git diff 186233e4 ed8e1a96 -- session_common.py`) and
  dropped the `is_coordinator = session_common.is_coordinator` alias (coordinator_handoff now imports it from
  `session_common` at `:55`), but KEPT `COORDINATOR_NAME_RE = session_common.COORDINATOR_NAME_RE`
  (`coordinator_handoff.py:77`). Commits 3-4 are new (guard reorder + reason text + test; stale-comment fix).
- `session_common.py` is NOT in `ed8e1a96...315640ba` at all: the conflict resolved to main's version wholesale.
  Semantics match the branch's original (`^dotfiles-.+\.coordinator$`, `name is not None and fullmatch`).
- Targeted pytest: `uv run --project python pytest tests/test_coordinator_write_guard.py tests/test_coordinator_handoff.py -q`
  → `260 passed in 34.17s`, rc=0.
- `.agents` mirror of coordinator-handoff SKILL.md differs from `.claude` only on the two expected path rewrites
  (lines 10, 37).
- No `"worktree"` key in project settings (`grep -c` → 0; control `"permissions"` → 1), user settings (0; control 1),
  or the main checkout's `settings.local.json` (0), so the `--settings` object cannot be shadowed by a file key.
- suites.toml token edits: `'reason = hook_guard.decide_payload('` occurs once (`hook_dispatch.py:56`);
  `"branch_guard.decide(tool_input)"` occurs once (`hook_guard.py:1101`). Both still bind one site; neither binds
  the guard ORDER or the `session_id=` forwarding (pytest does — see mutation table).
- Probe `/tmp/cr1658/probe.py` (real git, `GIT_CONFIG_GLOBAL=/dev/null`, module import verified to resolve to this
  worktree's `python/src`):

  | Arm | Verdict |
  |---|---|
  | A1 coordinator, tracked, main checkout on `main` | DENY (coordinator reason) |
  | A1c control: no session id, same file | DENY (branch_guard reason) |
  | A1i coordinator, ignored `task_plan.md`, on `main` | ALLOW |
  | A1n coordinator, new file in new dir, on `main` | DENY (coordinator reason) |
  | A2 coordinator, tracked file in a SIBLING repo's primary checkout on `main` | DENY (coordinator reason: EnterWorktree) |
  | A2c control: no session id, same sibling file | DENY (branch_guard reason) |
  | A2f coordinator, sibling repo on a feature branch | DENY (coordinator reason) |
  | A3 coordinator, nested repo under ignored `.agent/` | DENY |
  | A3c control: `.agent/plans/x.md` | ALLOW |
  | A4 coordinator, `.git/info/exclude` | ALLOW |
  | A5 coordinator, case-folded directory component (file exists) | ALLOW |
  | A5c control: canonical case | DENY |
  | A6 coordinator, linked worktree tracked file | ALLOW |

- Probe `/tmp/cr1658/recursion.py`: a job record of 200000 nested `[` under a coordinator-shaped session id, main
  checkout on `main`, tracked file. `decide_payload(..., session_id=None)` → DENY (control: branch_guard fires);
  `decide_payload(..., session_id=<id>)` → raises `RecursionError` (not caught by `read_json`'s
  `except OSError, ValueError`, and the identity lookup sits outside the guard's `try`).
- Mutation table: `/tmp/cr1658/mut.sh`. It extracts `git archive 315640ba python/src tests scripts` and shadows the
  package with `PYTHONPATH`. Each run covers `tests/test_coordinator_write_guard.py` and
  `tests/test_coordinator_handoff.py`, with `-k "not wrapper"` deselecting 10 shell-wrapper rows. Every mutation
  asserts it was applied exactly once.
- The baseline is 2 failures, named by `/tmp/cr1658/m0.sh` with `-rf`:
  `test_r14_unattended_docs_require_an_early_docs_branch_pr` and
  `test_s5_skill_and_task_contracts_point_to_current_authority`. Both are doc-contract tests that read
  `.claude/`/`docs/` files the archive does not contain. That makes them a harness artifact, and they are blind in
  every row. "Killed" means more than 2 failures.

  | Row | Mutation | Result |
  |---|---|---|
  | M0 | pristine control | 2 failed / 248 passed (baseline) |
  | M1 | drop `coordinator_handoff.COORDINATOR_NAME_RE` re-export | 7 failed — killed only by the 5 params of `test_shared_identity_preserves_handoff_api` (R2: nothing else reads it) |
  | M2 | restore `branch_guard`-first order | 3 failed — killed (order now pinned; last round's M9 survived) |
  | M3 | settings without the `worktree` key | 4 failed — killed |
  | M4 | `bgIsolation: "worktree"` | 4 failed — killed |
  | M5 | drop the "ExitWorktree (keep)…" reason clause | 2 failed — SURVIVED (R9) |
  | M6 | drop the "Do NOT switch the main checkout's branch." clause | 2 failed — SURVIVED (R9) |
  | M7 | `hook_dispatch` forwards `session_id=None` | 3 failed — killed |
  | M8 | `pretooluse_main` forwards `session_id=None` | 3 failed — killed |
  | C1 | candidate fix for R1: identity lookup moved inside the `try` | 2 failed (baseline): the fix is suite-neutral |

- C1 closes R1 (`/tmp/cr1658/c1check.sh`). The copy had C1 applied, and the import was verified to resolve to
  `/tmp/cr1658/mut0/python/src`. The RecursionError arm returned `session_id=None → DENY` and
  `session_id=<coordinator id> → DENY`, where the unfixed code raised.
- Gitignore status in this worktree, with `check-ignore -v`, tested 6 paths:
  - `.claude/agent-memory-local/…` → `.gitignore:109`
  - `task_plan.md` → `:144`
  - `findings.md` → `:145`
  - `progress.md` → `:146`
  - `.agent/plans/x.md` → `:125`
  - `docs/research/kb/reports/agents/x.md` → no match. This is the control arm, and it shows the probe
    discriminates.
- `ruff check` + `ruff format --check` on the 6 changed Python files: "All checks passed!", "6 files already
  formatted", both rc=0.
- Scratch: `/tmp/cr1658/` (probe scripts, archive copies, logs) was deleted at the end of the review.

## Stop condition (adversarial-review)

This round is OPEN HUNTING: the caller's brief named no domain with a cardinality, so the round cannot end the loop
by any outcome. It promotes to one bounded round. The proposed domain, after R1/R2/R7/R8 are dispositioned, has
120 cells:

- **identity** (4): coordinator, lane, absent, unreadable or raising.
- **location** (10): main tracked, main ignored, main new-in-new-dir, linked, outside, sibling primary,
  nested-under-ignored, submodule-in-linked, `.git/` interior, case-folded.
- **main-checkout branch** (3): default, feature, detached.

Add the enumeration question: "which input does `decide_payload` read that this table does not vary?" The candidate
answer is the exception axis R1 exposed. R3-R6 are ticketed in #1638, so a bounded round should verify them as
ticketed, not re-raise them.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the reviewed range, issue #1638, and the
  `compare/ed8e1a96...ee3b29da` API call.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the offline Claude Code docs
  (`sources/agent-harness-docs/docs/claude-code/`), for the hook payload fields, `ExitWorktree` input, worktree
  isolation checks and `bgIsolation`.
