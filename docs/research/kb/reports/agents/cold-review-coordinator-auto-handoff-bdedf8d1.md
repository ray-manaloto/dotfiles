# Cold review — coordinator auto-handoff, commit bdedf8d1

- Subject: `bdedf8d14e14d2ddce167ab09ff5a1a0bd6be273` ("fix(coordinator-handoff): review round-2 corrections S1-S5")
- Base: `823284723154197449c04ab084d1245edc997d89` (its first parent)
- Diff: `git diff 82328472 bdedf8d1` — 18 files, +1377/-166
- Author family: codex (gpt-5.6-sol); reviewer: Claude Opus (cold, diff-only)
- Constraints honoured: no tests, bun, tsc, lint or gate executed; read-only probes only, each with a control arm.
- Memory: consulted `.claude/agent-memory-local/cold-reviewer/` (2 entries from the df481e1f review).
- Status: COMPLETE (2026-10-02). 1 HIGH, 3 MEDIUM, 6 LOW (2 of them partly UNVERIFIED).

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| F1 | HIGH | A persistent start failure (rc 3) re-fires the handoff skill on EVERY following turn: rollback restores `previous_fired`, so the threshold drops back to the level that was just fired, and the next `session.measure` fires again at once. Nothing bounds it (no attempt counter or backoff). Each pass re-runs unattended `/session-handoff` and ships a docs PR, until the context overflows. | `python/src/dotfiles_setup/coordinator_handoff.py:905` (via `:342-351`); trigger `.claude/skills/coordinator-handoff/hooks/register.ts:200-210`; doc `.claude/skills/coordinator-handoff/SKILL.md:68-69` | E1, E2 |
| F2 | MEDIUM | The wrapper-redirect fallback returns `/dev/null` for every Bash-tool heavy run whose inner fd 1 is not a regular file (pipe, tty, lsof failure or timeout). The real harness wrapper has `} >/dev/null 2>&1 \|\| true && eval '<cmd>'` BEFORE the user's command, and `_REDIRECT_RE.search` takes the FIRST match. The R9 `unexpanded:` label therefore never appears in production, and the brief tells the successor to bounded-wait on `/dev/null`. The test fixtures use a bare `zsh -c mise run ship > "$LOG"` with no prelude, so this cannot surface in tests. A second trigger: a non-shell heavy argv that `shlex.split` rejects (a lone apostrophe) yields `process is None`, which reaches the same fallback. | `python/src/dotfiles_setup/coordinator_handoff.py:516` (`_log_path` at `:419-424`; shlex at `:468-471`); fixtures `tests/test_coordinator_handoff.py:1122`, `:1376` | E3, E4 |
| F3 | MEDIUM | rc 3 and "start failed" are reported even when `claude --bg` SUCCEEDED, if finalisation then fails: a lock timeout or any `OSError` at `:907-911`, or "pending claim changed" at `:892-900`. On that path `launch` is never recorded, `launch_pending` is left in place and the level is not restored. That contradicts SKILL.md's rc-3 promise ("pending state is removed and the real firing level restored"). The running successor's `retire` then refuses with rc 2 because there is no launch record, and the brief forbids a bare `claude stop`. After the 15-minute TTL, the next step re-fires and launches a SECOND successor. | `python/src/dotfiles_setup/coordinator_handoff.py:887-912`; claim at `.claude/skills/coordinator-handoff/SKILL.md:68-69`; retire gate at `coordinator_handoff.py:1008-1020` | E5 |
| F4 | MEDIUM | PROBE consumes `probe_fired` at decide time and never releases it on failed delivery: `releaseFailure` returns early when `noCommit`. After a failed probe (skill not listed, or `command.run` rejected), every later turn overwrites the ERROR status with `handoff probe done`. The probe exists only to prove that the `command.run` path reached the skill (SKILL.md §0), so this is a check that reports success after it failed. No harness arm covers a failed probe delivery. | `.claude/skills/coordinator-handoff/hooks/register.ts:170`, `:159-160`; `python/src/dotfiles_setup/coordinator_handoff.py:259-264` | E6 |
| F5 | LOW (UNVERIFIED) | When the 60 s timeout kills `claude --bg` after it has already dispatched to the per-user supervisor, rollback runs. With F1's immediate re-fire, that starts a second successor. The docs say the supervisor outlives the dispatching shell, and a cold start may print `Starting background service…` first. Whether dispatch can precede a >60 s CLI exit was not measured. | `python/src/dotfiles_setup/coordinator_handoff.py:871-886`, `:84` | E7 |
| F6 | LOW | Q-CLAIM: the operator label `census-unavailable` is emitted for causes that have nothing to do with the census: a state-lock timeout (`StateLockedError` subclasses `OSError`), corrupt or unwritable state, and a `git worktree` failure in `main()`. The test `test_s5_git_failure_uses_census_unavailable` enshrines the mislabel. | `python/src/dotfiles_setup/coordinator_handoff.py:806-807`, `:1158-1161`; `session_common.py:45` | E8 |
| F7 | LOW | The residual of the round-1 permanent-cache class: a `not-coordinator` answer at or above the limit is cached for the module's lifetime. That includes the first measurement after a hot reload, when context is already high. A transient job-record read miss (`read_json` → `None` on `ValueError`) then disables the trigger for good. The new arm "a first miss already at the limit is final" enshrines this. Whether job-record reads can transiently miss is UNVERIFIED. | `.claude/skills/coordinator-handoff/hooks/register.ts:215-217`; `tests/fixtures/coordinator_handoff_hook/harness.ts` (S4 "first miss … is final" block); `session_common.py:54-59` | E9 |
| F8 | LOW | Q-CLAIM: SKILL.md says "A pending start blocks another for 15 minutes", but a `launch_pending` whose age cannot be computed (non-dict, missing or naive `at`) blocks `decide` and `launch` FOREVER. It fails closed with no TTL escape, only a warning. Only this module writes the field, so it is reachable only through a bad edit or partial corruption. | `python/src/dotfiles_setup/coordinator_handoff.py:215-219`; `.claude/skills/coordinator-handoff/SKILL.md:66-67` | code read |
| F9 | LOW | A failed `pending` read is now retried on EVERY prompt with no cap. With a persistently corrupt session-start state file (`pending` → `state-write-failed`), each `prompt.submit` awaits a fresh `uv run … session-start pending` and sets ERROR. The parent commit made one attempt per module lifetime. | `.claude/skills/session-start/hooks/register.ts:190-205`, `:280`; `python/src/dotfiles_setup/session_start.py:355-356` | code read |
| F10 | LOW | The `launch` docstring is garbled ("…executes nothing. Otherwise the\n rc 3: start failed …"). Its rc-3 contract omits the started-but-unrecorded path (F3) and rc 2 for launch-in-progress. | `python/src/dotfiles_setup/coordinator_handoff.py:767-774` | code read |

## Evidence log

- **E1 — rc 3 restores the fired level, so the next measure re-fires immediately.**
  `_start_successor` calls `_rollback_fire(state, level)` on every non-zero, missing-binary or timeout start
  (`coordinator_handoff.py:902-905`). `_rollback_fire` sets `last_fired = previous_fired` or deletes it
  (`:346-350`), so `next_level` (`:199-201`) returns the threshold that was just crossed. The current percent is
  still at or above it, so `_judge` fires (`:268-275`). The subject's own test asserts the immediate re-fire:
  `assert _decide(tmp_path, 45).fire` straight after the rc-3 launch (`tests/test_coordinator_handoff.py:1274`).
  The hook submits again on any fire (`register.ts:236-249`); the role cache short-circuits only below the
  limit (`:200`). The docs say only "so the hook can retry" for rc 3, with no stop instruction. rc 2, by
  contrast, says "record that in the handoff and stop" (`SKILL.md:63-69`).
  Grep for `attempt|retries|retry|backoff|launch_failed|failures` in the subject module: rc=1, 0 hits. Control:
  `launch_pending` gives 8 hits in the same file with the same command, so the probe discriminates.
- **E2 — what one loop pass costs.** SKILL.md §1 (`:32-49`) runs `/session-handoff` in full and ships
  `docs/handoffs/session-<date><letter>.md` as a PR with `mise run ship`. §2 then launches. The parent commit's
  behaviour was the opposite failure: a permanent disable, because `launch` was recorded before the signal.
  This commit swaps that for an unbounded immediate retry. A bounded alternative: keep `last_fired` (retry at
  the next step, at most `(100 - limit) / step` passes) or add an attempt cap.
- **E3 — real wrapper argv vs the fallback regex.** Probe: `ps -o args= -p $$` for this reviewer's own Bash-tool
  shell (1657 chars), with `_REDIRECT_RE` exec'd verbatim from the subject file. Three matches came back. The
  first is `/dev/null` at offset 637, in `{ \builtin unalias -- 'unsetenv'; … } >/dev/null 2>&1 || true && eval '`.
  The user command starts at offset 671. Control arm: the same regex on `zsh -c mise run ship > /tmp/x.log 2>&1`
  returns `['/tmp/x.log']`.
  `_run_log` uses `_log_path(owner.command) or _log_path(by_pid[pid].command)` (`:516`). `owner` is the inner
  heavy command, whose argv carries no redirect, so the outer wrapper's FIRST redirect wins. That is
  `/dev/null`: absolute, so it is returned unchanged (`:517-522`). Re-derived inherited facts, each with a
  control arm: the wrapper's fd 1 = `…/tasks/bvxtf1n5r.output`, and a child started with `> "$LOG"` has fd 1 =
  `$LOG`. `ps` renders newlines in the wrapper as `\012`.
- **E4 — shlex arms.** `shlex.split` on the real 1657-char wrapper → OK, argv0 `/bin/zsh`. Control (balanced
  quotes) → OK. `mise run bounded-wait -- --cmd test -f /tmp/Ray's.log` → `ValueError: No closing quotation`.
  The `except ValueError: argv = []` at `:470-471` then skips that process as if it were a shell.
- **E5 — the start succeeded but finalisation failed.** `started` is computed before the second lock
  (`:871-886`). Both early exits, `return 3` at `:900` and at `:911`, skip `state["launch"] = record`
  (`:903`) and leave `launch_pending`. `retire` requires `state["launch"]["successor"]` (`:1008-1020`), so it
  returns 2. `_launch_in_progress` turns stale after `LAUNCH_PENDING_TTL_S = 900` (`:85`, `:220-223`). `decide`
  then fires at `last_fired + step`, because `last_fired` was never rolled back, and `launch` proceeds past the
  stale claim (`:798-805`). The log strings at `:898` and `:909` both say "start failed" whatever `started`
  was.
- **E6 — a probe that can only report done.** `_judge` sets `probe_fired = True` on the fire (`:263-264`).
  register.ts runs `mode = "probe"` → `noCommit = true` (`:208-209`). On "skill not listed" or a rejected
  `command.run`, `releaseFailure(…, noCommit, …)` returns before calling `release` (`:170`), and `release`
  touches only real levels anyway (`:342-351`). The next turn → `probe-done` → `belowStatus` → `handoff probe
  done` (`:159-160`). The harness covers only the success path ("s1-probe-three-measurements-one-command").
- **E7 — `--bg` semantics (KB step 00).** `agent-view.md:430-470`: `--bg` prints `backgrounded · <id>` after
  dispatch and may first print `Starting background service…`. `network-config.md:164`: "A per-user supervisor
  process starts on demand, outlives your shell". `changelog.md:2722`: "`claude --bg` occasionally failing with
  'socket missing' when the background daemon was cold-starting on a loaded machine". `changelog.md:3051`
  mentions a `--bg` rejection gate named "non-TTY". Whether that gate refuses a non-TTY `mise run` launch is
  UNVERIFIED; if it does, F1 is deterministic rather than conditional.
- **E8 — label scope.** `launch`'s `except CoordinatorHandoffError, OSError, subprocess.TimeoutExpired` wraps
  `main_checkout`, `state_lock` (raising `StateLockedError(OSError)`), `read_state` (raising `OSError` on corrupt
  JSON) and `write_state` inside `_launch_locked`. All of them log "census-unavailable". In `main()`, a
  `main_checkout` failure is also called "census-unavailable" for `launch`.
- **E9 — role cache.** `roles.set(sessionId, percent < limit ? "not-below-limit" : "not")` (`:217`). `"not"` is
  checked first on every measure and never cleared (`:191-194`). The module's Maps reset only on reload.
  `session_name` returns `None` on any `read_json` failure (`session_common.py:54-59`, `:77-81`).
- **Mirror check (not a finding).** `.claude/skills/{coordinator-handoff,session-start}/SKILL.md` and
  `.agents/skills/…` differ only by the generator's `.claude/skills/` → `.agents/skills/` rewrite, at the parent
  and at the subject alike. The session-start change from "Claude ancestor" to "harness process" removes the
  false "Codex ancestor" claim the rewrite produced in the Codex mirror at the parent.
- **Hook-harness arm counts reconcile.** Coordinator 30 → 34 (four new blocks). Session-start 24 → 28 (a
  four-case loop).
- **UNVERIFIED (no finding filed): `/rename` → job record.** `mark_renamed` now needs the bg job record's
  `name` to equal the new name (`session_start.py:324-332`). `changelog.md:944` ("`/rename` silently confirming
  when the session registry could not be updated") and `:2114` (bg `/rename` reverted on restart) suggest
  `/rename` does update the registry. The timing relative to `command.run` resolving was not measured. Host
  probe: 26 job records, all `nameSource: user`, 0 carrying the stamped convention. The regex control on a
  literal stamped name gave `true`, so the probe discriminates, but there was nothing to measure. If the update
  is asynchronous, the first confirmation races and fails once, then self-heals at the next prompt. If it never
  lands, bg naming never confirms and `/rename` is re-queued on every prompt.

## Required questions

- **Q-FRESH.** Every lock-protected decision→action pair re-reads state immediately before acting:
  - Finalisation re-reads and checks the pending identity (`:889-900`).
  - Rollback re-checks `_last_fired(state) == level` (`:344`).
  - `release` re-checks `launch_pending` (`:372`).
  - `launch` re-checks `launch` and `launch_pending` under the lock (`:786-804`).
  - `mark_renamed` reads the job record inside the state lock (`:317-332`).

  Two pairs are not re-validated. One is the TS role cache (F7): a cached "not" is reused without asking again.
  The other is the census→start gap, where a heavy run started after the census but before `claude --bg` goes
  unrecorded. That gap is narrow and older than this diff. `retire`'s unlocked state read is outside this diff.
- **Q-SCOPE.** F1, F3 and F5 come from the S2 start/rollback change. F2 comes from S3 log resolution, F4 from
  S1 probe semantics, F7 from S4, and F9 from S5. All are in scope for this round. F6, F8 and F10 are
  label/doc nits on lines this diff added.
- **Q-CLAIM.** Operator-facing strings added or changed by this diff, with the enforcing line or a finding:
  - **Enforced:**
    - Stale and unknown-age `launch_pending` warnings (`:217-223`).
    - `launch-in-progress` and `probe-done` reasons (`:259-262`).
    - Release `invalid-session-id` and `invalid-level` (`:362-367`).
    - "relative log … unresolved" (`:524-530`).
    - Brief "no rc file — wait on pid exit" (`:601-605`; `stdout_log` `:447-448`).
    - "start failed: claude --bg rc %d" (`:879-883`).
    - Retire remedies, each conditional on its blocker (`:1036-1043`).
    - CLI help for `--probe` and `--dry-run` (`:263-266`).
    - mise description "release" (`release_parser`).
    - TS "handoff launch in progress".
    - The "DRY_RUN wins" and "exactly one re-check" comments.
    - session-start "job name mismatch or unreadable; naming stays pending" (`:326-332`).
    - session-start "Failed pending reads are retried".
    - SKILL.md "Lanes write no handoff state" (`decide` returns before the lock, `:309-318`).
  - **Unenforced:**
    - "start failed: pending claim changed" and "start failed: cannot finalise state" when `started` is true
      (F3).
    - SKILL.md rc 3: "pending state is removed and the real firing level restored" (F3).
    - SKILL.md rc 3: "so the hook can retry" (true, but unbounded: F1).
    - TS "handoff probe done" after a failed delivery (F4).
    - "census-unavailable" for non-census causes (F6).
    - SKILL.md "blocks another for 15 minutes" for unreadable ages (F8).
    - The `_run_log` comment "the outer shell can carry redirect syntax": it does, but the harness's own
      `>/dev/null` comes first (F2).

## Verdict

DO NOT SHIP as-is. F1 turns any persistent start failure into a self-sustaining loop: handoff, then docs PR,
then failed launch, on every turn. F3 can leave a running successor with no launch record. Fixing both is
local to `_start_successor`:
- Keep the fired level on rc 3, so the retry waits for the next step and passes are bounded at
  `(100 - limit) / step`. An attempt cap would also work.
- Report "started but unrecorded" distinctly from "not started".

F2 needs the redirect fallback to ignore the harness prelude. The narrow options are: take the redirect that
follows the last `eval '`; or drop the wrapper fallback when the outermost process is a harness wrapper; or
emit `unexpanded:`/none rather than a device path. Its fixtures should carry the real prelude.

Reviewer constraint honoured: nothing executed beyond read-only `git`, `ps`, `lsof`, `jq`, `grep`, and python
regex/shlex evaluation over captured strings, each with a control arm. No test, gate, bun, tsc or lint was run.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the reviewed diff `82328472..bdedf8d1` and its consumers (local worktree)
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline Claude Code docs (`sources/agent-harness-docs/docs/claude-code/{agent-view,network-config,changelog,errors}.md`) for `--bg` and `/rename` semantics
