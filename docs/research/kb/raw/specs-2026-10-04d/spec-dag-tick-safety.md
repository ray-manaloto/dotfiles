# Spec DRAFT — dag-tick safety fixes (proposal 1; the LaunchAgent stays disabled)

**Status:** DRAFT written by spec-scribe on 2026-10-04. **Not ratified.** Sections
marked **UNRESOLVED (U#)** need a decision from the architect or Ray before anyone
dispatches work. Nothing has been dispatched.

**Ratified decision (Ray, 2026-10-04, relayed by the architect; keep this wording):**
keep the dag-tick LaunchAgent DISABLED and fix the defects in proposal 1 of
`docs/research/kb/reports/agents/sdlc-team-review-dag-tick-aba49c5d.md`:
(a) re-check terminal/retired status right before a DEAD respawn (dag_tick.py:1240
race vs coordinator_handoff retire); (b) --dry-run must not consume codex verdicts
(codex_verdict reaper); (c) launch provenance — refuse running from a non-main /
dirty / unapproved checkout BEFORE mutable project code or mise auto-install runs;
(d) timeouts on census/preflight subprocesses and the reaper flock.
Do not change respawn → resume.

Proposal 1 as the review words it (review `:49`): *"Keep disabled; correct
recovery-state checks, launch provenance and dry-run consumption, then validate
isolated recovery controls."*

**How the code was read (provenance caveat).** This lane had no shell, so it could
not run `git show origin/main:<path>`. Code was read from the
`.claude/worktrees/handoff-2026-10-04d` checkout: branch `docs/handoff-2026-10-04d`
at `e4532785`, while `refs/remotes/origin/main` is `36ab6bba`. The lane could not
prove that the python, test and `mise.toml` files are byte-identical to origin/main.
As a cross-check, every line the review cites matches the content it describes at
that exact line: dag_tick 295/508/711/1008/1037/1240/1334; codex_verdict 396/440;
coordinator_handoff 698/823/1154; mise.toml 132/721/1565. **The implementer must
re-read from origin/main before editing** (PREMISES row A1).

**Memory:** the spec-scribe local memory directory was empty when the lane started.
Auto memory is enabled, so the lane consulted it, but there were no prior conventions
to apply.

---

## 1. Objective

Make the dag-tick watchdog safe to re-enable *later*, without re-enabling it now
and without changing what recovery does (`claude respawn` stays the only recovery
verb; no switch to `--resume`). Four defects get fixed:

- **(a) Retired-session race.** `execute_respawn` re-reads state immediately before
  `Popen`, but only re-checks escalation and pid liveness. It must also refuse a node
  that has become **terminal** (`done`/`failed`/`stopped` with no active tempo and no
  queued prompt) or **retired/superseded** since classification. The harness's own
  docs say `claude respawn` restarts a session *"running or stopped"*, so the CLI
  will not refuse on our behalf.
- **(b) Dry-run consumes verdicts.** Under `--dry-run`, `reap_codex_lanes` must
  **preview** each lane's edge without creating `.reap.lock`, renaming
  `verdict.json`, or rewriting `lane.json`. Normal runs keep consuming exactly as
  they do today.
- **(c) Launch provenance.** A scheduled tick must refuse to act unless it is running
  approved code: on the default branch, clean, at an approved revision. The refusal
  must happen **before** mutable project code or mise tool auto-install can run.
  This is a structural change to how launchd invokes the tick, and its shape is
  **U1** below.
- **(d) Bounded waits.** The gate-preflight and census subprocesses get hard
  timeouts. The reaper's blocking `flock` becomes a bounded acquire. Each expiry
  degrades to "do nothing for this item this tick", logged distinctly, and never to a
  respawn.

**Non-goals (deliberate):**

- Re-enabling, bootstrapping, or editing the *installed* plist.
- `respawn` → `resume`.
- Automated stall recovery (#590).
- Awaiting or reaping detached respawn children (review `:14`, last sentence). That
  needs a separate decision; see U7.
- The producer-side blocking flock in `codex_lane` (codex_lane.py:314-315).
- Review control arm 5, "recovery preserves ownership and verifies useful
  continuation". It needs live harness sessions and stays a pre-activation gate for a
  future re-enable decision. This spec does not claim to satisfy it.

## 2. Files

Allowlist. The implementer edits only these. Anything else is out of scope.

| File | Change |
|---|---|
| `python/src/dotfiles_setup/dag_tick.py` | (a) terminal + superseded re-check in `execute_respawn`; (b) dry-run routes the reaper to preview; (d) `subprocess.run` timeouts plus `TickContext` timeout fields; corrected docstrings that claim the CLI refuses a running session (see U6) |
| `python/src/dotfiles_setup/codex_verdict.py` | (b) a side-effect-free `preview()` that shares decision logic with `reap()`; (d) bounded lock acquire plus a new `ReapOutcome` member mapped in `OUTCOME_EDGES` |
| `python/src/dotfiles_setup/dag_tick_launch.py` *(new; only if U1 = option R1)* | Stdlib-only provenance guard plus launcher. Verifies, then imports and runs the tick |
| `python/src/dotfiles_setup/main.py` | Register any new CLI flags or subcommand (approve verb, timeouts) next to `_add_dag_tick_subcommand` (main.py:1898) |
| `mise.toml` | Declaration only, and inert, because nothing applies it: the `[bootstrap.macos.launchd.agents.dotfiles-dag-tick]` program/args/env per U1, plus a human-run approve task if U1 needs one. **Never apply it.** |
| `tests/test_dag_tick.py` | Arms for (a), (b) end-to-end and (d) |
| `tests/test_codex_verdict.py` | `preview()` byte-preservation arms; bounded-lock arms; exhaustiveness of the new outcome |
| `tests/test_dag_tick_launch.py` *(new; only if R1)* | Real-git provenance arms in `tmp_path` |
| `tests/TEST-INDEX.md` | Index row for any new test file |

**Forbidden:** any `scripts/*.sh` or `.devcontainer/scripts/*.sh` (zero-bash-logic;
the `bash_logic_budget` allowlist must not change); `coordinator_handoff.py` unless
U2 = option C; the installed `~/Library/LaunchAgents/*.plist`.

## 3. Interfaces

### (a) `dag_tick.execute_respawn` — added fresh-state refusals

The signature is unchanged. Ordering is unchanged too: **all reads first, then all
decisions, then the spawn** (the existing invariant at dag_tick.py:1203-1213). The
new reads join the existing state and roster reads up front. Decision order after the
reads:

1. state.json unreadable → existing SKIP (unchanged).
2. **NEW:** `is_terminal(fresh.state, fresh.tempo, queued_prompt=fresh.queued_prompt)`
   → `"dag-tick: SKIP respawn <id> — terminal since classification (state=<s>, tempo=<t>)"`.
3. Existing `is_needs_human` → existing SKIP (unchanged text).
4. **NEW (per U2):** superseded/retired → `"dag-tick: SKIP respawn <id> — superseded: <reason>"`.
5. Existing pid-alive → existing SKIP.
6. `Popen` (argv, env strip, cwd and detachment all unchanged).

Rule: steps 2 and 3 use **the same predicates `classify()` uses**, built through
`node_from_state`. That way the snapshot and the fresh read cannot disagree about what
one file says, which is the #601 v4 lesson recorded at dag_tick.py:931-938.

The default for U2 is option A. Read the full `sessionId` from the fresh state.json,
then check for a coordinator-handoff launch record. Both the `launch` key and the
started-pending receipt count. The record lives at
`<main_checkout(ctx.cwd)>/.agent/state/coordinator-handoff/<sessionId>.json`. If the
record exists, refuse. If the record is unreadable, refuse; never respawn on doubt. If
the file is absent, proceed. Resolve `main_checkout` **once per tick**, not once per
node. It already carries a 30 s timeout (session_common.py:32, :191). A failure to
resolve it fails closed for coordinator-named nodes and open for everything else
(U2 detail).

### (b) `codex_verdict.preview`

```python
def preview(
    run_dir: Path,
    *,
    expected_owner: str,
    rework_count: int,
    max_rework: int,
    is_settled: Callable[[Path], bool] | None = None,
) -> ReapResult: ...
```

Contract:

- `preview()` returns the `ReapResult` that `reap()` *would* return for the current
  bytes.
- It creates, renames, writes and locks **nothing**. No `mkdir`, no `.reap.lock`
  open, no `_consume`, no `_mark_reaped`.
- Implement it by splitting today's `_reap_locked` and `_read_payload` into a pure
  decision step plus an effects step. The decision step returns the result and whether
  to consume and mark. `reap()` takes the lock, decides and applies the effects;
  `preview()` only decides.
- There must be **no second copy** of the CAS or payload logic.
- Unlocked reads in `preview` can race a real reaper. That is acceptable because the
  output says "would"; say so in the docstring.

`dag_tick.reap_codex_lanes` calls `preview` when `ctx.dry_run` is set and `reap`
otherwise. A dry-run line reads
`dag-tick: [dry-run] would CODEX-REAP <id> [<outcome>] edge=<edge> — <detail>`. The
existing "DECIDED here, not applied" suffix stays on real reaps.

### (c) Provenance (shape depends on **U1**)

The default for U1 is **R1**. The interface is shown so the architect can judge it.

- **Approved deployment checkout:** a detached `git worktree` at an approved SHA,
  located outside the main checkout. The path is an open detail; one candidate is
  `~/.local/state/dotfiles/dag-tick-approved`. Its venv is created at approval time.
- **Human verb:** `mise run dag-tick-approve -- <sha>`. It is a thin task that calls
  python, in line with zero-bash-logic. It refuses unless `<sha>` is an ancestor of a
  freshly fetched `origin/main`. It then moves the deployment worktree to `<sha>`,
  runs a frozen `uv sync` there, and writes the approval record outside every
  checkout, for example `~/.local/state/dotfiles/dag-tick-approved.json` holding
  `{sha, approved_at}`.
- **Launchd invocation:** the plist runs `<deploy>/python/.venv/bin/python -I -m
  dotfiles_setup.dag_tick_launch --cwd <main checkout abs path>`. No `mise run` and
  no `uv run`, so no mise auto-install and no uv sync at tick time.
- **`dag_tick_launch` (stdlib-only imports until verification passes):**

```python
@dataclass(frozen=True)
class Provenance:
    ok: bool
    reason: str          # one line, always logged
    head: str | None
    branch: str | None   # "HEAD" when detached

def check_provenance(
    checkout: Path,
    approved_sha: str | None,
    *,
    runner: Runner | None = None,   # injected; real git by default
    timeout_s: float = GIT_TIMEOUT_S,
) -> Provenance: ...

def main(argv: Sequence[str] | None = None) -> int: ...  # rc 0 always (launchd)
```

Refuse when any of these holds:

- no approval record exists;
- HEAD ≠ approved SHA;
- the approved SHA is not an ancestor of the local `origin/main` ref;
- tracked files are dirty (U5 decides whether untracked files count);
- a git call times out or fails.

On refusal, log the reason and return 0 **without importing `dotfiles_setup.main`
or `dag_tick`**. Only after `ok` does it import `dag_tick` and call `run_tick`.

`mise run dag-tick` (manual, from the main checkout) must also apply
`check_provenance` to the main checkout **when not `--dry-run`**. U5 decides whether
dry-run is exempt.

### (d) Timeouts

- `TickContext` gains `gate_timeout_s: float` and `census_timeout_s: float`. The
  defaults are module constants (values: **U3**); `build_tick_context` fills them.
  Tests inject small values.
- `gate_preflight` passes `timeout=ctx.gate_timeout_s`. `subprocess.TimeoutExpired`
  → warning `"dag-tick: gate preflight timed out after Ns"` → `"unknown"`. This
  matches the existing fail-open path (dag_tick.py:1423-1428).
- `read_census` passes `timeout=ctx.census_timeout_s`. `TimeoutExpired` → one
  distinct warning `"dag-tick: census timed out after Ns"` → `[]`.
- `codex_verdict.reap` gains a keyword `lock_timeout_s: float = REAP_LOCK_TIMEOUT_S`.
  It acquires the lock with `LOCK_NB` plus a monotonic deadline, the same pattern as
  `session_common.state_lock` (session_common.py:131-145). The lock file stays
  exactly `run_dir/.reap.lock` because `codex_lane` locks the same file. On expiry it
  returns a new `ReapOutcome.LOCK_BUSY` mapped to `Edge.NONE` and consumes nothing.
  `reap_codex_lanes` prints `LOCK_BUSY` **even without `--verbose`**, so a stuck lock
  is never silent (U4).

## 4. Constraints and invariants

1. **The LaunchAgent stays disabled.** Never run `mise bootstrap`, `mise bootstrap
   macos launchd-agents apply`, `launchctl enable/bootstrap/load`, or any live
   `claude respawn/stop/rm`. `mise.toml` edits are declarations only.
2. **Respawn stays respawn.** No `--resume`, no prompt injection, no new recovery verb.
3. **#1644 holds.** `ActionKind` stays exactly `{RESPAWN, LOG}`, there is no
   `execute_stop`, and DONE plans no action (dag_tick.py:295-299, :711-713;
   tests/test_dag_tick.py:2544-2582).
4. **Fail toward not respawning.** Every new read or decision that cannot be
   answered (timeout, unreadable record, git failure) yields SKIP or LOG, never
   RESPAWN. This mirrors the existing rules at dag_tick.py:93-101 and :1194-1201.
5. **Reads before decisions before spawn** in `execute_respawn`. No I/O may sit
   between the last guard and `Popen` (dag_tick.py:1203-1213).
6. **One predicate source.** `classify` and `execute_respawn` share
   `is_terminal`/`is_needs_human`/`node_from_state`. Do not add a parallel
   "terminal-ish" check.
7. **Dry-run is byte-preserving for every Codex lane.** The verdict, the processed
   file, `lane.json`, and the presence or absence of `.reap.lock` are identical before
   and after. The tick's own lock file and stdout logging are allowed, as in the
   review's "every tick" row at `:31`.
8. **`OUTCOME_EDGES` stays exhaustive** (codex_verdict.py:150-170). The new outcome
   gets a row and the exhaustiveness test covers it.
9. **Zero-bash-logic and mise-tasks-only.** Any new verb is a mise task wrapping
   python. No shell scripts.
10. **Tests mock only system boundaries.** Use the injected runner/`is_alive`
    seams; never monkeypatch our own module functions (tests/AGENTS.md § Mocking).
    Provenance arms use **real git** in `tmp_path` (real-integration-evidence).
11. **Operator-facing strings.** `_needs_human_reason()` is golden-pinned and
    reproduced verbatim by `dag_project` (dag_tick.py:654-669). **Do not change it.**
    New SKIP strings must state only what the code does.
12. No inline suppressions. Follow ruff's return-count and argument ceilings by
    splitting functions, the way the current `_cas_check` split does
    (codex_verdict.py:457-460).
13. **The guard must run before mutable code** (U1). Whatever option is ratified,
    show which bytes execute before the check. With `mise run`, mise reads the
    checkout's `mise.toml` and may auto-install before any python runs (mise.toml:132,
    :722).

## 5. Verification

The review's isolated control arms come first. Each arm pairs a positive with the
negative it must discriminate (probes-need-a-control-arm). Every new test must fail
when its fix is reverted: revert only the added lines, with `git add` before
mutating.

| # | Arm (review `:57-61`) | Positive / must-hold | Control / must-fail-on-revert |
|---|---|---|---|
| V1 | DONE with a live PID remains untouched | Existing `test_execute_tick_never_stops_a_done_node_with_live_pid` stays green | Temporarily restore the pre-#1644 stop branch from `git log -S execute_stop` history in a scratch commit → the test **fails**; drop the scratch commit |
| V2 | DEAD snapshot then terminal state → no respawn | New: classify `{"state":"blocked","tempo":"idle"}` → DEAD → plan RESPAWN; rewrite to `{"state":"stopped","tempo":"idle"}` → `execute_respawn` SKIPs with "terminal since classification" and `Popen` fails if called. Parametrize over `done`/`failed`/`stopped` | Still-DEAD rewrite → `Popen` called once (mirrors tests/test_dag_tick.py:2223-2247). `stopped` with `tempo:"active"` or a `queuedPrompt` → still respawns, so the predicate is not "any stopped" |
| V3 | DEAD snapshot then retired/superseded → no respawn (U2-A) | State dir has a launch record for the node's `sessionId` → SKIP "superseded" | No record → respawn; unreadable record → SKIP; started-pending receipt → SKIP |
| V4 | Dry-run preserves verdict and lane bytes; normal run consumes | `execute_tick` with `dry_run=True` plus a settled `approve` lane (`_codex_lane`, tests/test_dag_tick.py:2619): sha256 of each file and the sorted dir listing are identical before and after, with no `.reap.lock` created; stdout has `[dry-run] would CODEX-REAP` | Same fixture with `dry_run=False` → `verdict.processed.json` exists, `verdict.json` is gone, `lane.json` status is `reaped`. Revert the dry-run routing → the dry-run arm fails. Repeat for a `file_missing`/`parse_failed` lane, where today's consume-on-failure paths also mutate |
| V5 | Unapproved branch/revision/dirty → refused; approved → succeeds | Real `git init` repos in `tmp_path` with a fake `origin/main` ref: detached HEAD at the approved SHA, clean → `ok`, and the tick entry is reached (assert via the injected tick callable) | Each refusal is a separate arm: wrong branch, HEAD ≠ approved, approved SHA not an ancestor of `origin/main`, one modified tracked file, missing approval record, git timeout (a runner that raises `TimeoutExpired`). Each asserts the tick entry was **not** reached and `dag_tick` was **not imported** (check `sys.modules` in a subprocess `python -I -c`) |
| V6 | Census/preflight timeouts | Real-process arm: a `tmp_path` executable `#!/bin/sh` + `exec sleep 30` as `claude_bin`, `gate_timeout_s=census_timeout_s=0.2` → `execute_tick` returns 0 in under ~2 s, logs both timeout warnings, and calls no `Popen` | Healthy fake → no timeout warning. Remove the `timeout=` kwarg → the real-process arm exceeds a pytest-side bound (use `pytest`'s own timeout or a `SECONDS` budget in the test) |
| V7 | Reaper flock bounded | The test holds `.reap.lock` via its own `open`+`flock`; `reap(..., lock_timeout_s=0.2)` → `LOCK_BUSY`, `Edge.NONE`, bytes unchanged; `reap_codex_lanes` prints it without verbose | Release the lock → the same call reaps normally. `OUTCOME_EDGES` exhaustiveness test includes `LOCK_BUSY` |
| V8 | Review arm 5 (ownership/continuation) | **NOT RUN, out of scope.** Recorded as a pre-activation gate for any future re-enable | — |

Gates. Each runs through `mise run gate -- run <name>`, and its rc is the gate's
result:

- `lint`, `pytest`, `verify`: always.
- `lint-docs`: only if a `.claude/**/*.md` or `AGENTS.md` changes, which is not
  expected.
- `pin-actions`: not applicable.

Also check that `bash_logic_budget` is unchanged and that `mise run lint` passes the
`mise.toml` edit.

**Evidence to return:** each gate's rc from `.agent/gate-results/`; the V1/V4/V5
revert-then-fail outputs; and `git diff --stat` limited to the §2 allowlist.

## 6. Commit

Recommend **two PRs**. U1 blocks only the second.

1. `fix(dag-tick): refuse respawn of terminal/superseded nodes, read-only dry-run reaping, bounded waits`
   — covers (a), (b) and (d), with V1–V4, V6 and V7. Body: cite the review
   path and proposal 1; state that the LaunchAgent stays disabled and respawn is
   unchanged.
2. `feat(dag-tick): launch provenance guard before project code runs`
   — covers (c), with V5. It starts only after U1/U5 are ratified. Body: the trust-root
   rationale, and why `mise run` cannot be the guard (constraint 13), per
   use-tool-builtins' "justify custom code" requirement.

Process:

- Branch from origin/main before the first edit.
- Ship through `mise run ship` only. `land` is post-merge.
- The implementer lane must not run any command listed in constraint 1. State that
  explicitly in the lane brief, because hook_guard cannot see codex lane commands.
- End each commit with the session's attribution trailer.

## 7. PREMISES

V = verified by this lane reading the cited line during this run. A = assumption or
inherited, with the reason given.

| # | Premise | Cite | V/A |
|---|---|---|---|
| P1 | `execute_respawn` re-reads state and roster, then checks only unreadable state, `is_needs_human` and pid liveness before `Popen`; there is no terminal check | `python/src/dotfiles_setup/dag_tick.py:1240-1264` | V |
| P2 | `classify` returns DONE for a terminal node before any other branch | `dag_tick.py:558-559` | V |
| P3 | Terminal = state in {done, failed, stopped} ∧ tempo ≠ active ∧ no queued prompt | `dag_tick.py:180`, `:385-395` | V |
| P4 | The module claims the CLI refuses respawning a running session | `dag_tick.py:508-511`, `:686-688`, `:1267-1270` | V (that the claim exists) |
| P5 | Vendor docs: `claude respawn <id>` restarts a session "running or stopped" | `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/agent-view.md:695` | V |
| P6 | `stopped` also covers a process ended from outside Claude Code, so the new terminal re-check only matches what classification already suppresses | `agent-view.md:116`; `dag_tick.py:558-559` | V |
| P7 | `retire` writes no retirement marker; after its blockers it calls `claude stop` directly | `python/src/dotfiles_setup/coordinator_handoff.py:1081-1154`, `:1157-1170` | V |
| P8 | A launch writes a `launch` record (or a started-pending receipt) into `<state_dir>/<old_session_id>.json`, where `state_dir = main_checkout/.agent/state/coordinator-handoff` | `coordinator_handoff.py:108`, `:841-847`, `:1266-1267` | V |
| P9 | A job's state.json lives at `jobs/<short id>/state.json` and carries the full `sessionId`; the roster is keyed by short id | `python/src/dotfiles_setup/session_common.py:72-84`; `dag_tick.py:794-799` | V |
| P10 | `main_checkout` already has a 30 s timeout | `session_common.py:32`, `:183-192` | V |
| P11 | Dry-run is honored only inside `_execute_or_preview`; `reap_codex_lanes` runs unconditionally and calls `codex_verdict.reap` with no dry-run flag | `dag_tick.py:1288-1293`, `:1330-1339`, `:1436` | V |
| P12 | `reap` creates `.reap.lock` and blocks on `flock(LOCK_EX)`; it consumes by rename and rewrites `lane.json` to `reaped` | `python/src/dotfiles_setup/codex_verdict.py:434-440`, `:394-396`, `:599-600` | V |
| P13 | Failure paths also consume (lane unreadable, unreadable or invalid verdict) | `codex_verdict.py:546-550`, `:518-529` | V |
| P14 | `OUTCOME_EDGES` is declared exhaustive over `ReapOutcome` | `codex_verdict.py:127-170` | V |
| P15 | `codex_lane` takes the same `.reap.lock` with a blocking flock | `python/src/dotfiles_setup/codex_lane.py:310-315` | V |
| P16 | The gate preflight and census `subprocess.run` calls have no `timeout=`; the `ps` read has one (1 s) as precedent | `dag_tick.py:1008-1013`, `:1037-1042`, `:258`, `:854` | V |
| P17 | A bounded flock pattern (LOCK_NB + monotonic deadline) already exists | `session_common.py:131-145` | V |
| P18 | The `--dry-run` help promises "exit without spawning anything", and the task comment calls it "read-only" | `python/src/dotfiles_setup/main.py:1917-1921`; `mise.toml:721` | V |
| P19 | `mise.toml` sets `auto_install = true`; the dag-tick task runs `uv run --project python dotfiles-setup dag-tick` | `mise.toml:132`, `:722` | V |
| P20 | The declared LaunchAgent runs `~/.local/bin/mise run dag-tick` with working dir = main checkout and a literal PATH env; applying it is human-only | `mise.toml:1538-1549`, `:1561-1576` | V |
| P21 | `task.run_auto_install` defaults to true and is disabled by `--skip-tools` / `MISE_TASK_RUN_AUTO_INSTALL=0` | `docs/research/kb/reports/agents/diagnose-963-lock-perturbation-2026-09-29.md:65-66`, `:143`; `docs/research/kb/raw/mise-dotfiles-2026-09-29/mise-docs/cli_run.md:121` | V (read via grep lines; a prior session's measurement, not re-probed) |
| P22 | `main.py` imports `dag_tick` at module top, so any in-CLI guard runs after the whole import graph | `main.py:50`, `:3117` | V |
| P23 | The existing dry-run test creates no Codex lane | `tests/test_dag_tick.py:2418-2435` | V |
| P24 | The never-stop test pins `ActionKind` without STOP and the absence of `execute_stop` | `tests/test_dag_tick.py:2544-2582` | V |
| P25 | The race-test pattern (snapshot → mutate → execute, plus a control arm) exists to copy | `tests/test_dag_tick.py:2173-2247` | V |
| P26 | Tests build `TickContext` through `_ctx(tmp_path, **overrides)` | `tests/test_dag_tick.py:111-130` | V |
| P27 | Proposal 1 wording and the five control arms | `docs/research/kb/reports/agents/sdlc-team-review-dag-tick-aba49c5d.md:49`, `:55-63` | V |
| A1 | The files read here equal origin/main `36ab6bba` | The lane had no shell, so it could not run `git show origin/main:`; read worktree `handoff-2026-10-04d` at `e4532785`. Every review-cited line matched (cross-check only) | A |
| A2 | `subprocess.run(timeout=…)` kills and reaps the child on expiry | Stdlib behavior; docs not read this run | A |
| A3 | `uv run` syncs the project environment before running unless frozen/no-sync, so it is itself a mutation at tick time | Not read this run; drives the R1 "no `uv run` at tick time" choice | A |
| A4 | `claude stop` leaves tempo non-active, so the stopped node satisfies `is_terminal` (the review's "stopped/idle" replay) | agent-view.md:116 documents the state, not the tempo; inherited from review `:7` | A |
| A5 | Two `flock`s on separate `open()` descriptions in one process conflict on macOS, which makes V7's in-process holder valid | Implied by the existing `test_lock_contention_second_acquire_fails` (`tests/test_dag_tick.py:1226`, name only, body not read) | A |

---

## UNRESOLVED — needs ratification before dispatch

- **U1: provenance trust root (blocks PR 2).** Any code path that starts with
  `mise run` from the main checkout executes mutable `mise.toml` and possibly
  auto-installs before python runs (P19–P22). So:
  - **R1 (recommended): an approved detached worktree, launched without mise or uv**
    (§3c). PRO: the guard runs before any `dotfiles_setup.main` import; no
    auto-install at tick time; per-invocation branch/dirty/SHA checks still apply,
    matching the ratified wording. CON: new approve verb, worktree and venv to
    maintain; a third worktree appears in `git worktree list`; the guard's own bytes
    are in that worktree, so self-tamper is a stated residual.
  - **R2: `uv tool install` of `dotfiles-setup` at an approved SHA.** The plist runs
    the installed binary. PRO: strongest isolation, an immutable wheel, a native tool
    feature. CON: "dirty/non-main checkout" becomes vacuous per invocation; uv tool
    install of a subdirectory package with git deps is unprobed here.
  - **R3: keep `mise run dag-tick`, add `MISE_TASK_RUN_AUTO_INSTALL=0` and an
    in-CLI guard.** PRO: small. CON: **does not satisfy (c).** A branch switch replaces
    the guard itself and `mise.toml` (the review's pre-#1644 scenario, `:9`).
- **U2: retired signal for (a).**
  - **A (recommended):** terminal re-check plus "a coordinator-handoff launch record
    or started receipt exists" → SKIP (read-only; no coordinator_handoff change).
    CON: couples dag_tick to the handoff state path and needs a `main_checkout` call.
  - **B:** terminal re-check only (minimal). Leaves the window between retire's
    decision and the harness writing `stopped`.
  - **C:** retire writes a `retiring` marker under `state_lock` before `_stop`.
    Edits coordinator_handoff; largely redundant with A.
  - Sub-question for A: fail closed or open when `main_checkout` cannot resolve.
- **U3: timeout values.** Proposed gate 10 s, census 20 s, reap lock 5 s, git
  provenance 10 s each. The tick interval is 60 s (mise.toml:1564).
- **U4: `LOCK_BUSY` edge.** Proposed `Edge.NONE` plus always-printed (retry next
  tick). The alternative `NEEDS_HUMAN` escalates on contention, which is likely noisy.
- **U5: provenance details.** Does "dirty" include untracked non-ignored files? Is
  manual `mise run dag-tick -- --dry-run` exempt from the guard? Proposed: tracked
  only; dry-run exempt once (b) makes it read-only.
- **U6: correct the false "CLI refuses an already-running session" text** (P4 vs
  P5) in docstrings and comments. Should `_reply_queued_reason()` (operator-facing,
  :686-688) change too? Proposed: fix docstrings/comments in PR 1; change the reason
  string only if no golden pin or `dag_project` consumer binds it (not checked here).
- **U7: detached respawn children** outliving the tick lock (review `:14`). Out of
  scope as drafted. Confirm, or add to PR 1.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — local source read (dag_tick, codex_verdict, coordinator_handoff, codex_lane, session_common, branch_guard, main, mise.toml, tests)
- [mrkhachaturov/agent-harness-docs](https://github.com/mrkhachaturov/agent-harness-docs) — offline mirror `agent-view.md` read for respawn/stop semantics

## §R Rulings (Ray, 2026-10-04 ~09:00 CDT, via coordinator 5a5787)

- **U1:** R1 plus `[bootstrap.repos]`. The plist runs the pinned deploy checkout's venv python directly, with no mise or uv at tick time. The deploy checkout is a native mise `[bootstrap.repos]` clone at a full SHA, not `git worktree add --detach`. Set `process_type = "Background"`, and put `MISE_AUTO_INSTALL=0`, `UV_FROZEN=1` and `UV_NO_SYNC=1` in the plist `environment`. A python `dag-tick-approve -- <sha>` verb still performs the ancestry check against origin/main and runs `uv sync --frozen`. Evidence: `docs/research/kb/reports/agents/research-mise-launchd-worktree.md`.
- **U2:** terminal re-check plus coordinator-handoff launch/started record (recommended option).
- **U3–U7:** the spec's recommended options.
- **Next:** re-derive the PREMISES from origin/main (row A1), run premise-verifier, then dispatch PR 1 ((a), (b), (d)) and PR 2 ((c)) as separate specs.
