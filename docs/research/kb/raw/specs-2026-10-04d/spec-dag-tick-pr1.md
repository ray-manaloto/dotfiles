# Spec DRAFT: dag-tick safety, PR 1 of 2 ((a) + (b) + (d) + U6)

**Status:** DRAFT, written by spec-scribe on 2026-10-04. It is extracted from the
ratified parent spec `docs/research/kb/raw/specs-2026-10-04d/spec-dag-tick-safety.md`
(§R rulings: U2 = A; U3 to U7 = the recommended options). **Nothing has been
dispatched.** Five items marked **D1 to D5** need the architect's nod. **D3 conflicts
with ratified wording**, so the spec must not be dispatched until D3 is settled.

**Scope:** proposal 1 items (a), (b) and (d), plus the U6 text correction.
**Provenance (c) is excluded**; it is PR 2 and a separate spec.

**Source of truth for every citation:** the main checkout
`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`. Its `.git/HEAD` is
`ref: refs/heads/main` and `refs/heads/main` = `36ab6bba9a5297497610f08c114bad7f94fe5558`,
which is the origin/main tip named in the parent spec (both read this run). Every
`file:line` below was read in that checkout during this run. This closes parent
row A1. The lane had no shell: there was no `git show` and nothing was executed, so
every claim about runtime behaviour is marked A.

The one exception to that path is the review
`docs/research/kb/reports/agents/sdlc-team-review-dag-tick-aba49c5d.md`. It is not
on main yet; it exists only in the `handoff-2026-10-04d` worktree, and it was read
there.

**Memory:** the spec-scribe local memory directory was empty at start. Auto memory
is enabled, so it was consulted, but it held no prior conventions.

**Ratified decision (Ray, 2026-10-04; verbatim from parent §1, the load-bearing part):**
keep the dag-tick LaunchAgent DISABLED and fix (a) "re-check terminal/retired status
right before a DEAD respawn", (b) "--dry-run must not consume codex verdicts",
(d) "timeouts on census/preflight subprocesses and the reaper flock". "Do not change
respawn → resume."

---

## 1. Objective

Make three defects in `dag_tick` / `codex_verdict` impossible. The LaunchAgent stays
disabled, and `claude respawn` stays the only recovery verb.

- **(a)** `execute_respawn` must refuse a node that, on its fresh pre-`Popen` read,
  meets either condition:
  - it is **terminal** by the same `is_terminal` predicate `classify` uses; or
  - it has been **superseded**: a coordinator-handoff `launch` record, or a started
    receipt, exists for its full `sessionId`.

  A fresh DEAD-and-not-superseded node must still respawn.
- **(b)** `--dry-run` must leave every Codex lane byte-identical. That covers no
  `.reap.lock` creation, no `verdict.json` → `verdict.processed.json` rename, and no
  `lane.json` rewrite. Dry-run instead prints what the reaper *would* decide, via a
  side-effect-free `codex_verdict.preview()` that shares `reap()`'s decision logic.
  A normal run consumes exactly as today.
- **(d)** The gate-preflight and census `subprocess.run` calls get hard timeouts. The
  reaper's blocking `flock` becomes a bounded acquire that returns a new
  `ReapOutcome.LOCK_BUSY` (mapped to `Edge.NONE`, always printed). Every expiry
  degrades to "nothing for this item this tick", logged distinctly, and never to a
  respawn.
- **U6** Correct the false claim that "the CLI refuses an already-running session".
  The vendor doc says `claude respawn` restarts a session "running or stopped". The fix
  touches docstrings and comments, and also `_reply_queued_reason()`, because nothing
  pins that full string (see P30).

**Non-goals:**

- (c) provenance;
- re-enabling, bootstrapping or editing the installed plist;
- `respawn` → `resume`;
- #590 stall recovery;
- detached respawn children (U7, out of scope as ratified);
- the producer-side blocking flock in `codex_lane` (codex_lane.py:314-315);
- review arm 5 (ownership/continuation, a pre-activation gate);
- any change to `coordinator_handoff.py`.

## 2. Files

This is the allowlist. The implementer edits only these files.

| File | Change |
|---|---|
| `python/src/dotfiles_setup/dag_tick.py` | (a) superseded/terminal refusals in `execute_respawn`, with a read/decide split; (b) `reap_codex_lanes` routes to `preview` under `ctx.dry_run`, and `LOCK_BUSY` always prints; (d) `TickContext` timeout fields (+ D1/D4 fields), `timeout=` on both `subprocess.run` calls, and distinct timeout warnings; U6 text |
| `python/src/dotfiles_setup/codex_verdict.py` | (b) pure decision step plus an effects step, `preview()`; (d) bounded lock acquire, `REAP_LOCK_TIMEOUT_S`, `ReapOutcome.LOCK_BUSY` + `OUTCOME_EDGES` row; the D3 signature shape |
| `tests/test_dag_tick.py` | V-a, V-b (end-to-end), V-d arms; `_ctx` gains the new fields only if they are made required (they should not be; see §3d) |
| `tests/test_codex_verdict.py` | V-b `preview()` parity and byte arms; V-d lock arms; the two `is_settled=` call sites at :499 and :517 if D3-A is ratified |
| `python/src/dotfiles_setup/main.py` *(D5, optional)* | `--dry-run` help text only (main.py:1917-1921) so it states that verdicts are previewed, not consumed |
| `python/verification/suites.toml` *(D5, optional)* | `workflow.dag-tick-wiring` **description prose only** (suites.toml:1963), to correct the same false claim. Do not change any `per_path_tokens` entry |

**Forbidden:**

- `coordinator_handoff.py` (U2 = A is read-only);
- `mise.toml`;
- any `scripts/*.sh` or `.devcontainer/scripts/*.sh`;
- `tests/test_codex_lane.py` and `tests/test_codex_lane_e2e.py`. They construct
  `TickContext` with the current 10 keyword arguments (test_codex_lane.py:951-964,
  test_codex_lane_e2e.py:214-227), so new fields **must have defaults**;
- `python/src/dotfiles_setup/classifier_tables.py`;
- the installed plist.

## 3. Interfaces

### (a) `dag_tick.execute_respawn`: fresh terminal and superseded refusals

The signature is unchanged (`node_id, ctx, *, is_alive=None, proc_start=None`). The
invariant stays as it is at dag_tick.py:1203-1213 and :1236-1239: **all reads first,
then all decisions, then `Popen`.** No I/O may sit between the last guard and `Popen`.

**Reads**, all up front:

- `load_state_json(ctx.jobs_dir, node_id)`;
- `read_roster(ctx.daemon_dir)`;
- **NEW: the handoff read.** From the fresh state data take
  - `sessionId`. It is valid when `session_common.valid_session_id` passes and
    `sessionId[:8] == node_id` (session_common.py:31, :59-61, :72-74);
  - `name` (session_common.py:87-96).

  If `ctx.handoff_state_dir` is not None and `sessionId` is valid, read the launch
  state at `ctx.handoff_state_dir / f"{sessionId}.json"` with
  `coordinator_handoff._read_launch_state` (D2). The result is "launched" when
  `"launch" in state` or `_started_pending(state) is not None`. That is the exact
  predicate `retire` uses (coordinator_handoff.py:1099-1104) and the one `launch`
  refuses on (:846-847). `StateUnreadableError` or any other `OSError` means
  "unreadable".

  ⚠️ **File existence is NOT the signal.** `decide()` writes `<sessionId>.json` on
  *every* coordinator call (`last_seen`; coordinator_handoff.py:338, :351-355). A
  coordinator that merely crossed the measurement threshold has the file and no
  launch.

**Decisions**, in this order. Each refusal returns its SKIP line:

1. `fresh_data is None` → the existing SKIP, unchanged (dag_tick.py:1242-1246).
2. **NEW:** `is_terminal(fresh.state, fresh.tempo, queued_prompt=fresh.queued_prompt)` →
   `f"dag-tick: SKIP respawn {node_id} — terminal since classification (state={fresh.state}, tempo={fresh.tempo})"`.
3. The existing `is_needs_human` check. **Keep the line
   `if is_needs_human(fresh.state, fresh.needs, queued_prompt=fresh.queued_prompt):`
   byte-identical.** It is a `per_path_tokens` token (suites.toml:1974).
4. **NEW, superseded:**
   - launched → `"dag-tick: SKIP respawn <id> — superseded: coordinator-handoff launch recorded for <sessionId>"`;
   - unreadable → `"… — superseded check failed: <reason>; not respawning on doubt"`;
   - `ctx.handoff_state_dir is None` **and** `is_coordinator(name)` → SKIP "handoff state
     dir unresolved";
   - invalid or missing `sessionId` **and** `is_coordinator(name)` → SKIP "no valid sessionId".

   Non-coordinator nodes with an unresolved state dir or an invalid `sessionId` proceed.
   This is ratified as the U2 detail: fail closed for coordinator-named nodes, open
   otherwise. `launch` refuses non-coordinators (coordinator_handoff.py:806), so a
   genuine record only exists for coordinators. The record is still checked for every
   node whose `sessionId` is valid.
5. The existing pid-alive SKIP, unchanged.
6. `Popen`. Its argv, env strip, `cwd=Path.home()` and `start_new_session` are all unchanged.

**Shape:** ruff runs `select = ["ALL"]` with default ceilings (pyproject.toml:72; no
`[tool.ruff.lint.pylint]` override; `max-complexity = 10` at :152-153). The current
function already has 5 returns; adding 2 inline breaks the return ceiling. Split it
into a read step and a **pure** decision helper that returns `str | None` (the SKIP
line or None). **Do not** introduce a function whose return annotation is an enum
defined in `dag_tick.py`. `classifier_tables.classifier_shaped` flags any such
function as an unregistered classifier (classifier_tables.py:1025-1055, :1221-1259),
and the registry file is forbidden here.

**D1, where the state dir is resolved (scribe default):** add
`handoff_state_dir: Path | None = None` to `TickContext`. `build_tick_context`
resolves it **once per tick** as
`session_common.main_checkout(Path(cwd)) / coordinator_handoff.STATE_SUBDIR`. Any
`SessionError` becomes `None`. `main_checkout` already carries a 30 s timeout
(session_common.py:32, :183-203) and raises `SessionError` on every failure.

Why the context and not `execute_respawn`: tests monkeypatch
`dag_tick.subprocess.Popen`, which breaks any real `subprocess.run` inside the patched
scope (tests/test_dag_tick.py:1994-1996). Resolving in the context keeps
`execute_respawn` free of subprocess calls, and lets tests inject a `tmp_path` state
dir.

### (b) `codex_verdict.preview` and the decision/effects split

```python
def preview(
    run_dir: Path,
    *,
    expected_owner: str,
    rework_count: int,
    max_rework: int,
    seams: ReapSeams | None = None,   # D3-A; ratified text had `is_settled=`
) -> ReapResult: ...
```

**Contract:**

- `preview()` returns the `ReapResult` (outcome, edge, detail, verdict) that `reap()`
  would return **for the current bytes**.
- It creates, renames, writes and locks **nothing**: no `mkdir`, no `.reap.lock`
  open, no `_consume`, no `_mark_reaped`.
- The liveness gate (`lane_is_settled`, read-only, codex_verdict.py:336-370) runs
  first, exactly as in `reap`.
- The docstring must say: unlocked reads can race a real reaper, and the output means
  "would".

**Implementation:** today, `_read_payload` consumes on failure (codex_verdict.py:518-534)
and `_reap_locked` consumes and marks (:546-556, :564-565). Split both into:

- **one pure decision step** that returns the `ReapResult` plus its effects (consume?
  lane record to mark reaped?);
- **one effects step.**

`reap()` = gate → bounded lock → decide → apply effects. `preview()` = gate → decide.
There must be **no second copy** of the CAS (`_cas_check`, :449-498) or the payload
logic. Keep each helper under ruff's return and argument ceilings by splitting, the
way `_cas_check` was split (:457-460).

**Effect parity with today**, which must be preserved exactly:

| Outcome | Consume (rename) | Mark `reaped` |
|---|---|---|
| CAS refusals (OWNER/STATUS_MISMATCH, ALREADY_PROCESSED) | no | no |
| LANE_UNREADABLE | yes | no |
| FILE_MISSING | no (nothing to rename) | no |
| PARSE_FAILED | yes | no |
| APPROVED / REVISE / REJECTED | yes | yes |

**`dag_tick.reap_codex_lanes`** (dag_tick.py:1303-1348): when `ctx.dry_run` is set,
call `preview` and emit
`f"dag-tick: [dry-run] would CODEX-REAP {id} [{outcome}] edge={edge} — {detail}"`. Real
reaps keep the existing line, including the "edge is DECIDED here, not applied" suffix
(:1342-1347). The `Edge.NONE`-is-quiet-unless-verbose filter (:1340-1341) applies to
both paths, **except `LOCK_BUSY`, which always prints** (U4).

### (d) Timeouts

**Module constants** (the U3 values, ratified):

```python
GATE_TIMEOUT_S = 10.0        # dag_tick
CENSUS_TIMEOUT_S = 20.0      # dag_tick
REAP_LOCK_TIMEOUT_S = 5.0    # codex_verdict
```

**`TickContext` additions.** Each new field has a default, so the forbidden test files
keep constructing it:

```python
gate_timeout_s: float = GATE_TIMEOUT_S
census_timeout_s: float = CENSUS_TIMEOUT_S
reap_lock_timeout_s: float = REAP_LOCK_TIMEOUT_S   # D4
handoff_state_dir: Path | None = None              # D1
```

`build_tick_context` fills all four explicitly.

**`gate_preflight`** (dag_tick.py:994-1021) passes `timeout=ctx.gate_timeout_s`.
`subprocess.TimeoutExpired` is a `SubprocessError`, **not** an `OSError` (stdlib
subprocess.py:129, :169), so the existing `except OSError` (:1014) does not catch it.
Add a separate clause:

```python
logger.warning("dag-tick: gate preflight timed out after %gs", ctx.gate_timeout_s)
return "unknown"
```

`"unknown"` then proceeds, as it does today (:1423-1428).

**`read_census`** (dag_tick.py:1024-1068) passes `timeout=ctx.census_timeout_s`. On
`TimeoutExpired` it logs
`logger.warning("dag-tick: census timed out after %gs", ctx.census_timeout_s)` and
returns `[]`. That warning is distinct from the four existing ones.

**`codex_verdict.reap`** acquires `.reap.lock` with `LOCK_EX | LOCK_NB` plus a
monotonic deadline and short sleeps. This is the `session_common.state_lock` pattern
(session_common.py:130-152), including the `errno in {EACCES, EAGAIN}` discrimination
and re-raising any other `OSError`.

- The lock file stays exactly `run_dir / LOCK_FILENAME`, opened with `"a"`, because
  `codex_lane` locks the same file (codex_lane.py:310-315).
- On expiry it returns
  `ReapResult(ReapOutcome.LOCK_BUSY, Edge.NONE, f".reap.lock held for {t:g}s — not read; retried next tick")`
  and consumes nothing.
- New enum member: `LOCK_BUSY = "lock_busy"`, under the "no-ops" group
  (codex_verdict.py:143-147).
- New row: `OUTCOME_EDGES[ReapOutcome.LOCK_BUSY] = Edge.NONE` (:159-170).

**D3, a ratified-wording conflict (blocks dispatch).** The ratified text says
"`codex_verdict.reap` gains a keyword `lock_timeout_s`". `reap` already has 5
parameters (codex_verdict.py:399-406), so a sixth breaks ruff's argument ceiling.
The repo treats that ceiling as binding and bundles parameters into a dataclass to
satisfy it (classifier_tables.py:581-588; tests/test_dag_tick.py:2629-2631).

- **D3-A (recommended):** add
  `@dataclass(frozen=True) class ReapSeams: is_settled: Callable[[Path], bool] | None = None; lock_timeout_s: float = REAP_LOCK_TIMEOUT_S`.
  Replace `is_settled=` with `seams: ReapSeams | None = None` on both `reap` and
  `preview`; `preview` ignores `lock_timeout_s`. Update the only two `is_settled=`
  call sites (tests/test_codex_verdict.py:499, :517).
  - PRO: 5 parameters each; the lock timeout stays injectable.
  - CON: deviates from the ratified spelling, and edits two existing tests.
- **D3-B:** the literal ratified signature (6 parameters) plus a reviewed ruff
  `max-args` change.
  - PRO: matches the wording.
  - CON: a lint-config relaxation needs Ray's explicit approval (zero-skip policy);
    not recommended.
- **D3-C:** no parameter; `reap` reads `REAP_LOCK_TIMEOUT_S`.
  - PRO: no signature change.
  - CON: lock arms cost 5 s of wall clock each; `TickContext` cannot inject.
    Tests must not monkeypatch our own module (tests/AGENTS.md § Mocking).

`reap_codex_lanes` passes `seams=ReapSeams(lock_timeout_s=ctx.reap_lock_timeout_s)`
under D3-A.

### U6: corrected text

The vendor doc says: "`claude respawn <id>`: Restart a session, running or stopped"
(`knowledge-base/sources/agent-harness-docs/docs/claude-code/agent-view.md:695`).

- **dag_tick.py:508-512** (`is_reply_queued` docstring): replace "and `claude respawn`
  refuses an already-running session anyway — so a respawn here would be a no-op
  reported as a recovery". New meaning: `claude respawn` restarts a running session
  too, so a respawn here would restart a live worker out from under its own work.
  Making the shape visible remains the fix.
- **dag_tick.py:678-681** (`_reply_queued_reason` docstring): the same correction.
- **dag_tick.py:683-690** (`_reply_queued_reason()` return). The proposed exact text
  keeps the prefix that a test pins (P30):

  ```text
  reply queued but undelivered — state=blocked with a needs payload AND a queuedPrompt
  while the process is still alive, so a human already answered and the answer is
  waiting on a restart this module must not perform (it respawns only a confirmed-dead
  process; `claude respawn` would restart a live session out from under its own work);
  log-only, and no automated recovery exists for this shape
  ```

  The real return value is that single string, built by Python implicit concatenation
  as today.
- **dag_tick.py:1267-1270** (comment above the RESPAWN return): "requested" stays.
  Remove the "CLI has its own already-running refusal" justification and replace it
  with: the child is never read back, and the fresh re-checks narrow the window but do
  not close it.
- **D5 (optional):** the same correction in the suites.toml:1963 description prose,
  and main.py:1920 `--dry-run` help. Suggested help text: "Print the planned actions
  and Codex reap previews, then exit without spawning anything or consuming a
  verdict".

**Do not touch** `_needs_human_reason()` (dag_tick.py:616-651). It is golden-pinned
and reproduced verbatim by `dag_project` (:654-669).

## 4. Constraints and invariants

1. **LaunchAgent stays disabled.** Never run `mise bootstrap`, `mise bootstrap macos
   launchd-agents apply`, `launchctl enable/bootstrap/load`, or any live
   `claude respawn/stop/rm`. Tests use fakes or `tmp_path` executables only. **State
   this in the lane brief:** hook_guard cannot see codex lane commands.
2. **Respawn stays respawn.** No `--resume`, no prompt injection, no new verb.
3. **#1644 holds.** `ActionKind` stays exactly `{RESPAWN, LOG}` (dag_tick.py:295-299);
   there is no `execute_stop`; DONE plans nothing (:710-713). The forbid tokens must
   stay absent: `'"stop", node_id]'`, `"ActionKind.STOP"`, `'STOP = "stop"'`
   (suites.toml:1983).
4. **Fail toward not respawning.** Every new unanswerable read (unreadable record,
   unresolved state dir for a coordinator, invalid `sessionId` for a coordinator)
   yields SKIP. A timeout yields "unknown"/`[]`/`LOCK_BUSY`, never RESPAWN.
5. **Reads → decisions → spawn** in `execute_respawn`, with no I/O after the last guard.
6. **One predicate source.** Terminal = `is_terminal`, escalation = `is_needs_human`,
   both fed by `node_from_state` (dag_tick.py:931-948). Launched =
   `coordinator_handoff._read_launch_state` + `_started_pending` (D2). There is no
   parallel "terminal-ish" or "launched-ish" check.
7. **Dry-run is byte-preserving for every Codex lane.** That covers verdict, processed
   file, `lane.json`, `exit.marker`, and the presence or absence of `.reap.lock`. The
   tick's own lock file and stdout are allowed.
8. **`OUTCOME_EDGES` stays exhaustive.** `test_every_reap_outcome_has_a_defined_edge`
   (tests/test_codex_verdict.py:553-560) must cover `LOCK_BUSY`.
   `test_the_escalating_outcomes_are_exactly_the_inverted_set` (:563-578) must stay
   green unchanged; `LOCK_BUSY` → `NONE` keeps that set intact.
9. **`per_path_tokens` for `workflow.dag-tick-wiring` and
   `workflow.dag-projection-wiring` must all remain present** in `dag_tick.py`
   (suites.toml:1974, :1999). The fragile one is the `is_needs_human(fresh.…)` line;
   keep the variable name `fresh`.
10. **No module-defined-enum return types on new functions** (classifier_axes
    `unlisted`). `ReapOutcome` is already an enum in `codex_verdict`. The new
    decision helper must return `ReapResult` (a dataclass) or a tuple, never a bare
    `ReapOutcome`.
11. **Tests mock only system boundaries.** Use the injected `is_alive`/`proc_start`
    seams, `TickContext` fields and `ReapSeams`. Never monkeypatch our own module
    functions or constants (tests/AGENTS.md § Mocking). Real processes in tests may use
    only base-OS tools (`sh`, `sleep`) (tests/AGENTS.md "Working in this directory").
12. **No inline suppressions.** Respect ruff's argument, return and complexity
    ceilings by splitting functions.
13. **Residuals.** These are not fixed here; record them in the PR body:
    - a read-to-spawn window remains (dag_tick.py:1215-1220);
    - a coordinator-handoff run with a non-default `--state-dir`
      (coordinator_handoff.py:1255) is invisible to (a);
    - the worst-case tick can exceed the 60 s interval: 10 + 20 + N×5 s, plus up to
      30 s for `main_checkout`. The tick lock turns overlap into a silent skip
      (dag_tick.py:242-244).
14. **D2 import:** `from dotfiles_setup.coordinator_handoff import STATE_SUBDIR, _read_launch_state, _started_pending`.
    - Use the `from`-import form. Attribute access `coordinator_handoff._x` would trip
      SLF001.
    - Precedent for a cross-module private `from`-import that passes lint today:
      coordinator_handoff.py:67.
    - No cycle: coordinator_handoff imports only `handoff_inbox`, `reap`,
      `session_common` and `session_orphans` (:45-67); none of those import `dag_tick`.

## 5. Verification

Every new test needs a positive arm, a control arm, and a **must-fail-on-revert**
check. To run that check: `git add` first, then delete **only** the added guard line(s)
(a realistic regression, not a rename), run the named test, confirm it FAILS, and
restore with `git checkout -- <file>` from the staged copy. Report each
revert-then-fail rc.

### V-a: terminal / superseded re-check (`tests/test_dag_tick.py`)

The pattern to copy is the snapshot → mutate → execute race pair at
tests/test_dag_tick.py:2173-2247. Inject `Popen` via `monkeypatch.setattr(dag_tick.subprocess, "Popen", …)`
as those tests do.

| Arm | Fixture | Must hold |
|---|---|---|
| V-a1 positive (parametrize `done`/`failed`/`stopped`) | `{"state":"blocked","tempo":"idle"}`, roster empty → classify DEAD → plan RESPAWN; then rewrite to `{state:<s>, tempo:"idle"}` | `execute_respawn` returns SKIP containing "terminal since classification"; a `Popen` stub that raises is never called |
| V-a1 control: still DEAD | rewrite to `{"state":"blocked","tempo":"blocked"}` | `Popen` is called once with `["claude","respawn",id]` |
| V-a1 control: not-terminal axes | `stopped` + `tempo:"active"`; `stopped` + `queuedPrompt:"x"` | both still respawn, so the guard is `is_terminal`, not "any stopped" |
| V-a2 positive | state.json carries `name:"dotfiles-x.coordinator"`, `sessionId:<8-char node id + suffix>`; `ctx.handoff_state_dir=tmp_path/"ho"` holds `<sessionId>.json` = `{"launch":{"successor":"s","at":"t"}}` | SKIP "superseded" |
| V-a2 positive: started-pending | `<sessionId>.json` = `{"launch_pending":{"started":true,"name":"s"}}` | SKIP "superseded" |
| V-a2 positive: receipt only | only `<sessionId>.started.json` = `{"started":true,"census":[]}` | SKIP "superseded" |
| V-a2 positive: unreadable | `<sessionId>.json` = `"{not json"`, no receipt | SKIP "superseded check failed" |
| V-a2 positive: unresolved dir | coordinator-named node, `handoff_state_dir=None` | SKIP "handoff state dir unresolved" |
| V-a2 **control: decide-only file** | `<sessionId>.json` = `{"last_seen":{"at":"t","percent":31}}` (the shape `decide` writes, coordinator_handoff.py:353-355) | **respawns**, which proves the signal is a launch record, not file existence |
| V-a2 control: absent | no file | respawns |
| V-a2 control: non-coordinator, unresolved dir | no `name`, `handoff_state_dir=None` | respawns (fail-open side of the U2 detail) |
| V-a3 build-context | `build_tick_context(_tick_args(cwd=str(tmp_path/"not-a-repo")))` | `handoff_state_dir is None`; `gate_timeout_s == 10.0`, `census_timeout_s == 20.0`, `reap_lock_timeout_s == 5.0`. Extends the tests at :2296-2324 |

- **Revert check V-a1:** delete the terminal guard → the three V-a1 positives fail and
  the controls stay green.
- **Revert check V-a2:** delete the superseded guard → the five V-a2 positives fail and
  the controls stay green.
- **Regression:** the existing `test_execute_tick_never_stops_a_done_node_with_live_pid`
  (:2544-2582) and the escalation race pair (:2173-2247) stay green unchanged.

### V-b: dry-run preserves lane bytes; normal run consumes

**End-to-end** (`tests/test_dag_tick.py`): extend the shape of
`test_execute_tick_dry_run_reports_without_spawning` (:2418-2435), which today creates
no lane (review :63). Add `_codex_lane(ctx, "dead1", verdict="approve")` (helper at
:2619-2650). Before and after `execute_tick` with `dry_run=True`, record the sorted
`os.listdir(run_dir)` and the sha256 of every file.

| Arm | Must hold |
|---|---|
| V-b1 positive | listing and hashes are identical; `.reap.lock` is absent; stdout contains `[dry-run] would CODEX-REAP dead1 [approved] edge=advance` |
| V-b1 control | same fixture with `dry_run=False` → `verdict.processed.json` exists, `verdict.json` is gone, `json.loads(lane.json)["status"] == "reaped"` |
| V-b2 (parametrize the failure lanes) | `verdict="{not json"` (PARSE_FAILED), no `lane.json` (LANE_UNREADABLE), no verdict (FILE_MISSING): dry-run → bytes and listing identical with no `.reap.lock`; normal run → the PARSE_FAILED and LANE_UNREADABLE lanes are renamed, and FILE_MISSING creates `.reap.lock`. Each normal arm proves its dry-run arm could have failed |

**Unit** (`tests/test_codex_verdict.py`):

| Arm | Must hold |
|---|---|
| V-b3 parity (parametrize every reachable outcome: approve, revise under/at bound, reject, file_missing, parse_failed, empty file, lane_unreadable, owner_mismatch, status_mismatch, already_processed, not_settled via injected gate) | build two identical lanes A and B; `preview(A)` equals `reap(B)` on outcome, edge, detail and verdict; A is byte-identical afterwards and has no `.reap.lock` |
| V-b3 control | `reap(A)` afterwards does mutate A wherever the effect-parity table (§3b) says it should |

- **Revert check V-b1/V-b2:** make `reap_codex_lanes` call `reap` unconditionally
  (delete the dry-run branch) → V-b1 and V-b2 dry-run arms fail.
- **Revert check V-b3:** make `preview` delegate to `reap` → the byte assertions fail.

### V-d: bounded waits

| Arm | Fixture | Must hold |
|---|---|---|
| V-d1 positive, real process (`tests/test_dag_tick.py`) | `tmp_path/"claude"` = `#!/bin/sh\nexec sleep 10\n`, chmod 0o755; `_ctx(..., claude_bin=str(that), gate_timeout_s=0.2, census_timeout_s=0.2)`; **no** monkeypatching of `subprocess` | `execute_tick(ctx) == 0`; elapsed (`time.monotonic()`) < 5 s; caplog has both "gate preflight timed out after" and "census timed out after"; stdout has no `RESPAWN` |
| V-d1 control: healthy fake | script prints `No job matching 'x'.` to stderr and exits 1 for `logs`, prints `[]` and exits 0 for `agents` | neither timeout warning appears; the gate reads "on" |
| V-d2 unit | monkeypatch `dag_tick.subprocess.run` (a system boundary) to raise `subprocess.TimeoutExpired(cmd, 0.2)` | `gate_preflight` → `"unknown"`; `read_census` → `[]`, each with its distinct warning |
| V-d3 positive (`tests/test_codex_verdict.py`) | settled approve lane; the test opens `run_dir/".reap.lock"` with `"a"` and holds `fcntl.flock(fd, LOCK_EX)`; call `reap(..., seams=ReapSeams(lock_timeout_s=0.2))` | outcome `LOCK_BUSY`, edge `NONE`; elapsed ≥ 0.2 s and < 2 s; verdict, lane and listing are byte-identical |
| V-d3 control | release the lock, then make the same call | `APPROVED`, consumed |
| V-d4 tick (`tests/test_dag_tick.py`) | same held lock; `_ctx(..., verbose=False, reap_lock_timeout_s=0.2)`; `reap_codex_lanes` | exactly one line containing `[lock_busy] edge=none`, printed without verbose |
| V-d4 control | an `OWNER_MISMATCH` lane, non-verbose | still prints nothing (the existing quiet rule, :2711-2720) |

- **Revert check V-d1:** remove both `timeout=` keyword arguments → the elapsed
  assertion fails (about 20 s).
- **Revert check V-d3:** restore the blocking `LOCK_EX` acquire. The call then blocks
  until the holder releases, so run that check with the holder in a `threading.Timer`
  that releases after 3 s and assert elapsed < 2 s → it fails.
- `exec` in the fake is load-bearing. `subprocess.run` kills and waits only the direct
  child (stdlib subprocess.py:554-570).
- V-d3's in-process holder relies on two `open()` descriptions conflicting under
  `flock`. That is the same mechanism `test_lock_contention_second_acquire_fails`
  already exercises (tests/test_dag_tick.py:1226-1234).

### Gates

Run each through `mise run gate -- run <name>`. Its rc is the gate's result, and the
typed result lands in `.agent/gate-results/`.

- `lint`, `pytest`, `verify`: always. `verify` binds the suites.toml tokens (constraint 9).
- `lint-docs`: not applicable (no `.claude/**/*.md` or `AGENTS.md` change).
- `pin-actions`: not applicable.

**Evidence to return:**

- each gate's rc from `.agent/gate-results/`;
- each revert-then-fail rc (V-a1, V-a2, V-b1/2, V-b3, V-d1, V-d3);
- `git diff --stat` showing only §2 paths.

## 6. Commit

- **Branch:** `fix/dag-tick-safety-pr1`, created from origin/main `36ab6bba` **before the
  first edit** (do-not.md #9).
- **COMMIT: caller.** The implementer leaves the work **uncommitted** on the branch
  and returns the evidence. The caller reviews, commits and ships via `mise run ship`
  only.
- **Message:** `fix(dag-tick): refuse respawn of terminal/superseded nodes, read-only dry-run reaping, bounded waits`.
- **Body:**
  - cite proposal 1 of `docs/research/kb/reports/agents/sdlc-team-review-dag-tick-aba49c5d.md`.
    It is on the handoff branch; if that has not merged first, quote the proposal line
    instead of linking;
  - state that the LaunchAgent stays disabled, respawn is unchanged, and (c) is PR 2;
  - list the residuals from constraint 13.
- End the commit with the session attribution trailer.

## 7. PREMISES

V = read by this lane during this run, at the cited line, in the main checkout at
`36ab6bba` unless another path is given. A = assumption, with the reason given.

| # | Premise | Cite | V/A |
|---|---|---|---|
| P1 | Main checkout HEAD is `main` at `36ab6bba…` | `.git/HEAD:1`; `.git/refs/heads/main:1` | V |
| P2 | `execute_respawn` reads state, then roster, then decides: unreadable → `is_needs_human` → pid-alive → `Popen`; there is no terminal or superseded check | `python/src/dotfiles_setup/dag_tick.py:1240-1271` | V |
| P3 | The reads-then-decisions ordering is a documented invariant | `dag_tick.py:1203-1213`, `:1236-1239` | V |
| P4 | `classify` returns DONE for a terminal node first; terminal = state ∈ {done, failed, stopped} ∧ tempo ≠ active ∧ no queued prompt | `dag_tick.py:558-559`, `:180`, `:385-395` | V |
| P5 | `node_from_state` is the shared builder for the census path and the fresh re-check | `dag_tick.py:931-948` | V |
| P6 | The false "CLI refuses an already-running session" claim appears in docstrings, the reason string and a comment | `dag_tick.py:508-512`, `:678-681`, `:686-689`, `:1267-1270` | V |
| P7 | Vendor doc: `claude respawn <id>` restarts a session "running or stopped" | `knowledge-base/sources/agent-harness-docs/docs/claude-code/agent-view.md:695` | V |
| P8 | `stopped` includes a `claude stop` or an outside kill | `agent-view.md:116` | V |
| P9 | Dry-run is honoured only in `_execute_or_preview`; `reap_codex_lanes` calls `codex_verdict.reap` unconditionally from `execute_tick` | `dag_tick.py:1289-1293`, `:1334-1339`, `:1436` | V |
| P10 | `reap` creates `.reap.lock` and blocks on `flock(LOCK_EX)` | `codex_verdict.py:434-446` | V |
| P11 | Consume = rename `verdict.json` → `verdict.processed.json`; mark = rewrite `lane.json` status `reaped` | `codex_verdict.py:386-396`, `:592-602` | V |
| P12 | LANE_UNREADABLE and PARSE_FAILED consume; FILE_MISSING returns without rename; success consumes and marks | `codex_verdict.py:546-556`, `:518-534`, `:510-517`, `:564-565` | V |
| P13 | `ReapOutcome` members and the exhaustive `OUTCOME_EDGES` | `codex_verdict.py:127-147`, `:159-170` | V |
| P14 | `_cas_check` order is owner → idempotency → status, and it was split for ruff's return ceiling | `codex_verdict.py:449-498`, `:457-460` | V |
| P15 | `codex_lane` locks the same `.reap.lock` with a blocking flock and `"a"` mode | `codex_lane.py:310-315` | V |
| P16 | Gate and census `subprocess.run` calls have no `timeout=`; gate catches only `OSError`; the `ps` read has a 1 s timeout as precedent | `dag_tick.py:1006-1020`, `:1036-1049`, `:254-258`, `:847-857` | V |
| P17 | Gate "unknown" proceeds with a warning | `dag_tick.py:1423-1428` | V |
| P18 | `TimeoutExpired` subclasses `SubprocessError`, not `OSError`; `run()` kills and waits the direct child on timeout | `~/.local/share/uv/python/cpython-3.14-macos-aarch64-none/lib/python3.14/subprocess.py:129`, `:169`, `:554-570` (the venv's base interpreter per `python/.venv/pyvenv.cfg:1`) | V |
| P19 | A bounded flock pattern exists (`LOCK_NB`, monotonic deadline, EACCES/EAGAIN) | `session_common.py:130-152` | V |
| P20 | `main_checkout` has a 30 s timeout and raises `SessionError` on every failure | `session_common.py:32`, `:183-203` | V |
| P21 | Job state.json is at `jobs/<sid[:8]>/state.json`, carries the full `sessionId` and `name`; coordinator name regex | `session_common.py:72-96`, `:41` | V |
| P22 | `read_state`: missing → `{}`, corrupt → `StateUnreadableError` (an `OSError`) | `session_common.py:51-56`, `:104-116` | V |
| P23 | Handoff state lives at `<main_checkout>/.agent/state/coordinator-handoff/<sessionId>.json`; the started receipt is `<sessionId>.started.json` | `coordinator_handoff.py:108`, `:258-260`, `:841-842`, `:1266-1267` | V |
| P24 | "Launched" = `"launch" in state` or a `launch_pending` with `started: True`, after receipt recovery via `_read_launch_state`; `retire` and `launch` use exactly this | `coordinator_handoff.py:251-279`, `:846-847`, `:1099-1104` | V |
| P25 | `decide()` writes `<sessionId>.json` (`last_seen`) on every coordinator call, so file existence ≠ launch | `coordinator_handoff.py:338`, `:351-355` | V |
| P26 | `launch` writes the started receipt, then promotes `launch_pending` to `launch` | `coordinator_handoff.py:952-996` | V |
| P27 | `retire` stops via `claude stop` after its blockers; it writes no retirement marker | `coordinator_handoff.py:1148-1170` | V |
| P28 | `launch` refuses a non-coordinator session | `coordinator_handoff.py:806` (grep hit: "is not a coordinator") | V |
| P29 | coordinator_handoff imports no `dag_tick`-dependent module; precedent of a cross-module private `from`-import | `coordinator_handoff.py:45-67`; `handoff_inbox.py:58`; `session_orphans.py:24`. A src-wide grep shows `dag_tick` is imported only by `dag_project.py:72`, `main.py:50` and `codex_lane.py:82`, and `codex_lane`/`dag_project` only by `main.py:35`, `:49` | V |
| P30 | Nothing pins the full `_reply_queued_reason()` text. Tests assert only the substring "reply queued but undelivered" and the note prefix; suites tokens and `dag_project` do not include it | `tests/test_dag_tick.py:474`, `:1772-1774`; `suites.toml:1974`, `:1999`; grep of `reply_queued_reason` across the repo (`docs/` excluded) hit only `dag_tick.py` | V |
| P31 | `_needs_human_reason` is golden-pinned and reproduced by `dag_project` | `dag_tick.py:616-669` | V |
| P32 | suites `dag-tick-wiring` tokens include the exact `is_needs_human(fresh.…)` line; its description repeats the false claim; forbid tokens ban the STOP shapes | `suites.toml:1974`, `:1963`, `:1983` | V |
| P33 | ruff `select = ["ALL"]`, no pylint ceiling override, mccabe 10 | `python/pyproject.toml:71-94`, `:152-153` | V |
| P34 | The repo treats the argument ceiling as binding, including keyword-only parameters, and bundles to satisfy it | `tests/test_dag_tick.py:2619-2631` (5 params incl. 3 kw-only, "stays under ruff's argument ceiling"); `classifier_tables.py:581-588` | V |
| P35 | `classifier_shaped` flags any function returning an enum defined in its own module that has no REGISTRY entry | `classifier_tables.py:1025-1055`, `:1221-1259` | V |
| P36 | `TickContext` is constructed in 3 test files with exactly the current 10 keyword arguments | `tests/test_dag_tick.py:111-130`; `tests/test_codex_lane.py:951-964`; `tests/test_codex_lane_e2e.py:214-227` | V |
| P37 | Existing fake `run`/`Popen` stubs accept `**_kwargs`, so a new `timeout=` keyword does not break them | `tests/test_dag_tick.py:2408-2415`, `:2562-2569` | V |
| P38 | Patching `dag_tick.subprocess.Popen` breaks a real `subprocess.run` in the same test | `tests/test_dag_tick.py:1994-1996` | V |
| P39 | The existing dry-run tick test creates no Codex lane | `tests/test_dag_tick.py:2418-2435` | V |
| P40 | The never-stop test pins the `ActionKind` set and the absence of `execute_stop` | `tests/test_dag_tick.py:2544-2582` | V |
| P41 | The escalation race pair (snapshot → mutate → execute, plus control) exists to copy | `tests/test_dag_tick.py:2173-2247` | V |
| P42 | Only two call sites pass `is_settled=` | `tests/test_codex_verdict.py:499`, `:517` (repo grep of `is_settled=` in `python/src` + `tests`) | V |
| P43 | The exhaustiveness and inverted-set tests exist | `tests/test_codex_verdict.py:553-578` | V |
| P44 | In-process double flock on separate `open()`s conflicts (the test asserts it) | `tests/test_dag_tick.py:1226-1234` | V (test body read; that it passes is inherited from CI, not run here) |
| P45 | `--dry-run` help promises "without spawning anything"; the task comment calls it a "read-only preview" | `main.py:1917-1921`; `mise.toml:721` | V |
| P46 | Review proposal 1 wording; HIGH findings for the retire race, the respawn-refusal contradiction, and dry-run consumption; MEDIUM for hangs; the control arms | `.claude/worktrees/handoff-2026-10-04d/docs/research/kb/reports/agents/sdlc-team-review-dag-tick-aba49c5d.md:7`, `:8`, `:10`, `:14`, `:49`, `:55-63` | V (worktree copy; not on main) |
| P47 | Ratified rulings U2 = A, U3 to U7 = recommended | `.claude/worktrees/handoff-2026-10-04d/docs/research/kb/raw/specs-2026-10-04d/spec-dag-tick-safety.md:408-413` | V |
| A1 | After `claude stop`, the harness persists `state:"stopped"` with a non-active tempo promptly, so the terminal re-check catches the retire race | `agent-view.md:116` documents the state, not the tempo or its timing; inherited from review `:7` ("latest stopped/idle state") | A |
| A2 | ruff's default return ceiling is 6, so 7 returns in `execute_respawn` would fail | ruff docs not read this run; the codebase splits for "ruff's return-count ceiling" (`codex_verdict.py:229-231`, `:457-460`) without stating the number | A |
| A3 | `subprocess.run(timeout=)` with `capture_output=True` raises promptly even if the fake writes nothing | stdlib source read (P18); runtime not executed | A |
| A4 | The handoff state dir resolved from `ctx.cwd` matches the one `coordinator_handoff` uses (`main_checkout(Path.cwd())`) | Holds when the tick's cwd is in the dotfiles repo; the LaunchAgent sets the main checkout as working dir (parent P20, not re-read this run) | A |

---

## Pending architect decisions (stop here for ratification)

- **D3 (blocks dispatch: conflicts with ratified wording).** The ratified
  `reap(..., lock_timeout_s=)` makes 6 parameters, which breaks ruff's argument
  ceiling (P34). Recommended: **D3-A**, a `ReapSeams` bundle replacing `is_settled=`
  on `reap` and `preview`. B and C are in §3d.
- **D1.** Resolve `handoff_state_dir` once per tick in `build_tick_context` and inject
  it as a `TickContext` field. Recommended: yes.
  - PRO: no subprocess inside `execute_respawn` (P38); tests inject `tmp_path`.
  - CON: one git call per tick, even on lock contention.
  - Alternative: resolve after acquiring the lock inside `execute_tick` via
    `dataclasses.replace`.
- **D2.** Import `coordinator_handoff._read_launch_state` / `_started_pending` /
  `STATE_SUBDIR` rather than re-deriving the "launched" predicate. Recommended: import.
  - PRO: one predicate source (constraint 6); identical to `retire`.
  - CON: a cross-module private import (precedent coordinator_handoff.py:67); `dag_tick`
    now transitively imports `reap`/`hook_guard`.
  - Alternative: a 3-line duplicate with a cross-reference comment and fixtures pinned
    to the P26 shapes.
- **D4.** Add `TickContext.reap_lock_timeout_s`. Without it, V-d4 waits the full 5 s.
  Recommended: add.
- **D5.** Include the optional suites.toml:1963 description and main.py:1920 help-text
  corrections. Recommended: include. Both repeat claims PR 1 makes false or true.
  Description prose and help text are not tokens.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): local main checkout read (`dag_tick`, `codex_verdict`, `coordinator_handoff`, `codex_lane`, `session_common`, `classifier_tables`, `main`, `pyproject.toml`, `suites.toml`, `mise.toml`, tests)
- [mrkhachaturov/agent-harness-docs](https://github.com/mrkhachaturov/agent-harness-docs): offline mirror `agent-view.md` read for respawn and stop semantics
