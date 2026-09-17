# codex SDLC team — Phase 7 /verify follow-up mini run (2026-09-17), verbatim

Brief: `mise run sdlc-team` implement mode, run `phase7-verify-followup-20260917`, 2400 s, 7-path allowlist, `COMMIT: caller`; spec appended. Output copied verbatim at receipt.

---

Phase 7 is partially implemented. Six allowlisted files changed; nothing was staged or committed.

Implemented:

- Audit-only bounded deadline classification via [`is_audit_wait_loop()`](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/hook_guard.py:262), while the guard still allows bounded polls.
- `session-orphans` now uses that predicate and documents the harness-wrapper limitation in [session_orphans.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/session_orphans.py:4).
- Positive, negative, and guard-control tests.
- Append-only goal-history iteration 018 in [goal-history.md](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/agents/goal-history.md:978).
- Refreshed [plan-pointer.json](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/agents/plan-pointer.json:1).

The verify skill was not added under licensed dissent. The spec requires a mise-based `renovate-validate` recipe while forbidding nonexistent mise tasks. `mise task info renovate-validate` returned rc `1`, `Task not found`. Completing W2 requires either adding that task or authorizing the existing Python CLI command.

Verification:

- Focused pytest: rc `0`, 278 passed.
- `handoff-check`: rc `0`.
- `mise run verify`: rc `0`, 159 passed, 4 skipped.
- `mise run lint-docs`: rc `0`.
- `mise run lint`: rc `1`, sandbox blocked its log before hk ran.
- Full pytest: 770 passed, then an unrelated sandbox failure because `ps` is denied. A focused rerun reproduced it; neither failing file was modified.
- Final `git diff --check`: rc `0`.
- Graphify was unavailable because its graph is six commits stale; source fallback followed repository policy.

`★ Insight ─────────────────────────────────────`
- Separating audit classification from guard enforcement preserves the security boundary while allowing orphan cleanup to recognize bounded deadline loops.
- The added test arms pin both sides: reverting the audit predicate loses bounded-loop classification, while guard tests ensure the same command remains allowed.
`─────────────────────────────────────────────────`

Specialists spawned:

- `sdlc-python-specialist` — `/root/phase7_python`
- `sdlc-documentation-specialist` — `/root/phase7_docs`
- `sdlc-config-specialist` — `/root/phase7_config`

No others were spawned.


---

## Appendix — the spec (verbatim)

# Spec — Phase 7 /verify follow-up (mini implement run, 2026-09-17)

Repo `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`, branch `fix/session-orphans-bounded-loops` (already checked out, off `main` = `0865524`, the merged Phase 7 squash). Mode **IMPLEMENT**, `COMMIT: caller`, do not stage.
Ruling (Ray, 2026-09-17): the codex SDLC team closes the `/verify` FAIL of PR #1163 as a mini run. Inputs: `docs/research/kb/reports/agents/cold-review-phase7-r2-2026-09-16.md` (M8), the verify report in this session (summarised in §2).

## 1. Objective
`mise run session-orphans` must implement the ruling its own docstring and the handoff skill state: "every session-local wait loop is an orphan, including a loop whose condition carries a deadline". Today the prescribed bounded poll is classified OTHER (blocked, never reaped) because `session_orphans.build_plan` reuses the guard's `is_wait_loop`, which round 3 deliberately made return False for arithmetic comparisons (correct for the GUARD, wrong for the AUDIT). Failure prevented: a bounded in-turn poll left alive at handoff is reported as an unknown OTHER and survives `--kill`.

## 2. Measured at the surface (architect, 2026-09-17, checkout `0865524`)
- `sh -c 'deadline=$((SECONDS+600)); while [ $SECONDS -lt $deadline ]; do sleep 5; done' &` then `mise run session-orphans` → `WAIT-LOOP: 0`, the loop listed as `BLOCK OTHER 40816 … sh -c deadline=…`.
- `hook_guard.is_wait_loop(masked)` → False for that string; True for `until [ -f /tmp/nope ]; do sleep 5; done` and `while true; do sleep 30; done` (control arms).
- A harness-launched background wait shows in `ps` only as `/bin/zsh -c source …/shell-snapshots/snapshot-zsh-….sh 2>/dev/null || true` with a `/bin/sleep N` child (the command is fed on stdin) — the 2026-09-15 orphan's exact shape. Out of scope here (issue #1171 territory) but the docstring must say it.

## 3. Workstreams
W1 (python) `python/src/dotfiles_setup/session_orphans.py` `build_plan` (`:79-80`): classify a descendant shell as WAIT-LOOP when its masked command contains a loop whose BODY sleeps and whose CONDITION is EITHER a wait-family predicate (`hook_guard._is_wait_condition`) OR a deadline comparison (`SECONDS`, `$deadline`/`$DEADLINE`/`$end`/`$END`, or a `date +%s` comparison — the same tokens `hook_guard._CONDITION_BOUND` (`hook_guard.py:178`) recognises). Add a public predicate in `hook_guard` (e.g. `is_audit_wait_loop(masked)`) that the guard's DENY rule does NOT use, so guard behaviour is unchanged (a counter loop `while [ $i -lt 40 ]` stays non-wait everywhere; a `while read` stays non-wait). `format_plan` keeps the `bounded`/`unbounded` label. Tests (`tests/test_session_orphans.py`, `tests/test_hook_guard.py`): the bounded `SECONDS` poll row → WAIT-LOOP labelled `bounded`; `until [ -f x ]` → WAIT-LOOP `unbounded`; counter loop and `while read` rows → OTHER; and a guard arm pinning that the bounded poll is still ALLOWED by the PreToolUse rule.
W1b (python docs) the module docstring gains the harness-launch limitation in one sentence (only argv-visible loops are classifiable; a `zsh -c source …snapshot…` wrapper is OTHER and is left to #1171).
W2 (docs) `.claude/skills/verify/SKILL.md` (NEW, ≤ 80 lines): the runtime-verification recipe that worked for this repo — the mise tasks as the CLI surface (`handoff-check` with a fixture, `bounded-wait` three arms, `session-orphans` dry run with a spawned bounded `sh -c` loop + `--kill --allow`, `session-agentsview-pass` two arms, `session-review --requirements-only --source-repo-root <tmp>` refusal, `renovate-validate` under `env -i` with `~/.local/bin` + shims on PATH), the guard through `printf '{json}' | bash scripts/pretooluse-guard.sh`, and the gotchas (zsh does not word-split `$var`; the `gh pr checks --watch` guard; the harness wraps background commands in `zsh -c source snapshot`). Frontmatter `name: verify`, `description:` one sentence; no `mise run` name that does not exist (`doc_refs`).
W3 (docs) `docs/agents/goal-history.md`: APPEND iteration `dotfiles-goal-20260917-018` (never edit prior bytes). Fields exactly: `Iteration ID`, `Prior goal digest` (= 017's current digest `sha256:92307e302d1678fbf6ef3e50a4f6081eedcfe8fe7f18a745671f22b5b83badac`), `Current goal digest` (sha256 of the current goal text you write, computed, prefixed `sha256:`), `Changed requirement` (Phase 7 landed as #1163 → `0865524`: plan-only task authority, orphan/bounded-wait guard, AgentsView census, self-describing session-review; the `/verify` pass found one docs-vs-code mismatch (bounded loops not classified) closed by this iteration; the goal now = the nine filed follow-ups #1165–#1173 with #1171 (harness-children allowlist) and #1157 (session-review non-record residual) first), `Reason` (Ray, 2026-09-16/17: one PR, codex SDLC team does the work, continuity = tracked plan digest pointer only; `/verify` after the PR), `Evidence` (PR #1163, `docs/research/kb/reports/agents/*2026-09-16.md`, the verify report), `Affected tickets` (#1157, #1155, #1165–#1173), `Disposition` (accepted), `Topology and ownership` (one writer: the Claude architect session; implementation lanes = codex SDLC team; cold review = Opus), then the current goal text and a Mermaid `flowchart LR` of the workflow (land → verify → this fix → #1171/#1157 → next).
W4 (config) refresh `docs/agents/plan-pointer.json` with `mise run plan-pointer` (writes the tracked file; the plan on disk is the authority) — commit is the caller's.

## 4. Constraints
Round-1/2/3 constraints of the Phase 7 specs bind (no `noqa`, budgets, `doc_refs`, `contract_token_uniqueness`: any NEW `hook_guard` predicate name must not collide with a contract token; do not add another `_inert_masked(command)` call site). Do not touch `.claude/settings.json`, `task_plan.md`, `findings.md`, `progress.md`. Append-only on `docs/agents/goal-history.md` — the `workflow.goal-history` validator (`mise run session-review` / `mise run verify`) fails closed on any rewrite.

## 5. Verification (config specialist; real rc; `SANDBOX:` when blocked — the architect re-runs)
```
uv run --project python pytest tests/test_session_orphans.py tests/test_hook_guard.py tests/test_plan_pointer.py -x -q
uv run --project python dotfiles-setup handoff-check            # rc=0 now that the pointer is refreshed
mise run verify                                                   # incl. workflow.goal-history on the appended 018
mise run lint
uv run --project python pytest tests/ -x -q
```
Fail arms: revert the classifier change → the bounded-row test fails; append 018 with a rewritten 017 byte → verify's goal-history contract fails; guard arm: the bounded poll must remain ALLOWED.

## 6. Commit
COMMIT: caller.

## 7. PREMISES (fresh this session)
- L `session_orphans.build_plan` classifies with `hook_guard.is_wait_loop(hook_guard.mask_shell_syntax(process.command))` — `session_orphans.py:79-80`; docstring `:4-6` states the bounded ruling.
- L `hook_guard._is_wait_condition` returns False for `_BRACKET_OR_ARITHMETIC_WAIT`/`_TEST_WAIT`/`_READ_WAIT` — `hook_guard.py:188-198`; `_CONDITION_BOUND` at `:178`; `is_wait_loop`/`is_unbounded_wait_loop` at `:234/:239`; `mask_shell_syntax` at `:229`.
- L measured predicate results and the `ps` shapes — §2.
- L goal-history 017 layout and digest — `docs/agents/goal-history.md:911-914`; file is 976 lines.
- L `docs/agents/plan-pointer.json` is stale vs this clone's `task_plan.md` (`handoff-check` → `stale_plan_pointer`, measured 2026-09-17).
- A `.claude/skills/verify/SKILL.md` has no listing-budget conflict (skill class ≤ 500 lines / 32,000 B; doctor `listing-budget` is a SEPARATE host check — keep the description under 200 chars).
