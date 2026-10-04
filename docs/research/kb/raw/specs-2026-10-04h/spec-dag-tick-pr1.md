# Spec DRAFT: dag-tick safety, PR 1 of 2 ((a) + (b) + (d) + U6)

**Status:** REVISED DRAFT, written by spec-scribe on 2026-10-04 (04h). It applies the
premise-verifier report `docs/research/kb/reports/agents/premise-verifier-dag-tick-pr1.md` (04h
worktree) to the 04d draft
`handoff-2026-10-04e/docs/research/kb/raw/specs-2026-10-04d/spec-dag-tick-pr1.md`. It is extracted
from the ratified parent spec `docs/research/kb/raw/specs-2026-10-04d/spec-dag-tick-safety.md`
(§R rulings: U1 = R1 plus `[bootstrap.repos]` for PR 2; U2 = A; U3 to U7 = the recommended
options). **Nothing has been dispatched.** Decisions **D1 to D6** need the architect's nod.
**D3 conflicts with ratified wording, and D6 (new) edits a verification contract token**, so
the spec must not be dispatched until both are settled.

**Scope:** proposal 1 items (a), (b) and (d), plus the U6 text correction.
**Provenance (c) is excluded**; it is PR 2 and a separate spec.

**Source of truth for every citation:** the 04h worktree
`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-04h`, a
checkout of `13af2848`. In the main checkout, `refs/heads/main` and `refs/remotes/origin/main`
both read `13af28480ae4…` (P1). Every `file:line` below was re-read there in this run. This lane
has no shell (Read/Grep/Glob/Write only): there was no `git show` and nothing was executed, so
every claim about runtime behaviour is marked A.

**Memory:** the spec-scribe local memory directory was empty at start, so no prior convention
was applied.

**Ratified decision (Ray, 2026-10-04; verbatim from parent §1, the load-bearing part):**
keep the dag-tick LaunchAgent DISABLED and fix (a) "re-check terminal/retired status
right before a DEAD respawn", (b) "--dry-run must not consume codex verdicts",
(d) "timeouts on census/preflight subprocesses and the reaper flock". "Do not change
respawn → resume."

## Revision log (04h)

Letters (a)-(g) are the report's "Exact corrections". MISSING-n and An/Pn are its MISSING list
and rows. **N-n are new findings from this run.**

| # | Correction | Kind | Where applied |
|---|---|---|---|
| (a) | Base `36ab6bba` → `13af2848`; branch from current origin/main. P46 re-confirmed and repointed: the aba49c5d review is **now tracked at the base** (worktree index probe, P46), so no copy was needed and none was written | blocking | header, §6, P1, P46 |
| (b) | §2 now allows a reviewed edit of `python/verification/suites.toml` `workflow.codex-verdict-contract` (`:2628`): `per_path_tokens` (`:2638`) gets the bounded-acquire line in place of `fcntl.flock(handle.fileno(), fcntl.LOCK_EX)`, plus a `ReapOutcome.LOCK_BUSY: Edge.NONE` token, plus (D3-A) the seams form of the gate line; the description's "all ten reap outcomes" (`:2630`) becomes "eleven". D3 stays explicit | blocking | §2, §3 (d) "Contract tokens", constraint 9 |
| (c) | Constraint 9 extended to `workflow.codex-verdict-contract`, listing every token the implementation must keep byte-identical in `codex_verdict.py` and `dag_tick.py` | blocking | constraint 9 |
| (d) | V-b1 control uses a recording `Popen` stub (precedent `tests/test_dag_tick.py:2447-2451`), because the fixture node is DEAD and a normal tick plans RESPAWN | blocking | §5 V-b1 control |
| (e) | V-a2 gains the "coordinator name + invalid/missing sessionId → SKIP 'no valid sessionId'" positive; its revert check counts **six** positives | blocking | §5 V-a2 table and revert check |
| (f) | Constraint 13 gains two residuals: the A4/U1 deploy-clone state-dir mismatch (a PR-2 requirement) and the mid-launch `launch_pending`-without-`started` window | blocking | constraint 13 |
| (g) | U6 list adds the stale docstrings at `dag_tick.py:102`, `:1171`, `:1193`, `:1203`; constraint 14 adds the `session_common` imports | blocking | §3 U6, constraint 14 |
| N1 | **NEW, blocking.** The verifier's correction (c) says "remain present". The real gate is stricter: hk `contract_token_uniqueness` (`hk.pkl:388-395`, run by `mise run lint` via `["check"]` `:848-850`) requires **every `per_path_tokens` entry to match its file exactly once** (`token_audit.py:351-354`, `:358-367`, `:389-407`). Neither `dag_tick.py` nor `codex_verdict.py` has an allowlist entry. A `preview()` that repeats the liveness-gate lines, or a dry-run `preview(...)` call that repeats `expected_owner=classified.node_id,` / `max_rework=ctx.max_rework,`, would fail `mise run lint` | blocking (new) | constraint 9 ("exactly once"), §3 (b) shared gate, new **D6**, §5 V-b revert check |
| N2 | **NEW.** More stale text than (g) names: the `execute_respawn` docstring `:1222-1234` ("Deliberately PID-liveness only"), the comment `:1236-1239` ("BOTH reads first, THEN both decisions"), the whole module bullet `:102-115`, and the `dag-tick-wiring` description prose (`suites.toml:1963`: "covers BOTH axes, and BOTH reads happen first") | non-blocking (applied) | §3 U6, D5 |
| N3 | **NEW.** `session_common.main_checkout` passes no git-context scrub (`session_common.py:186-192`), so an inherited `GIT_DIR` would make V-a3's "not-a-repo" resolve to a real repo. V-a3 deletes the git-context variables with `monkeypatch.delenv`. The production analogue is a residual (`session_common.py` is outside the allowlist) | non-blocking (applied) | §5 V-a3, constraint 13 |
| N4 | **NEW.** V-b3's detail-parity check is valid only for details that contain no `run_dir` path. Every outcome in its parametrize list has a path-free detail today (`codex_verdict.py:476-497`, `:512-534`, `:551-575`) | non-blocking (applied) | §5 V-b3 |
| N5 | **NEW.** A closer precedent for V-d3's in-process holder: `tests/test_codex_lane.py:530-535` holds the real `.reap.lock` with `fcntl.flock(..., LOCK_EX)` against a second thread | informational | §5 V-d notes, P44 |
| MISSING-6 | The unlocked handoff read is safe: `write_state` is atomic tmp+replace, and `_read_launch_state` reads the receipt first and writes nothing | residual (stated) | §3 (a) |
| MISSING-8 | The `exec` in the V-d1 fake is kept for "no orphaned `sleep`", not for timing | residual (applied) | §5 V-d notes |
| MISSING-9 | The 8-character node id trap is restated | residual | §5 V-a2 |
| MISSING-10 | `tests/AGENTS.md:113` names `git` and `sh`/`bash` but not `sleep`; `exec sleep` fakes have precedent | residual | constraint 11 |
| A1-A4 | Accepted on the record; A4 is linked to (f) | residual | §7 A-rows |

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
- the producer-side blocking flock in `codex_lane` (`codex_lane.py:314-315`; its contention test
  `tests/test_codex_lane.py:504-540` stays as is);
- review arm 5 (ownership/continuation, a pre-activation gate);
- any change to `coordinator_handoff.py` or `session_common.py`.

## 2. Files

This is the allowlist. The implementer edits only these files.

| File | Change |
|---|---|
| `python/src/dotfiles_setup/dag_tick.py` | (a) superseded/terminal refusals in `execute_respawn`, with a read/decide split; (b) `reap_codex_lanes` routes to `preview` under `ctx.dry_run` (shape per **D6**), and `LOCK_BUSY` always prints; (d) `TickContext` timeout fields (+ D1/D4 fields), `timeout=` on both `subprocess.run` calls, and distinct timeout warnings; U6 text (incl. N2) |
| `python/src/dotfiles_setup/codex_verdict.py` | (b) pure decision step plus an effects step, `preview()`, and **one** shared liveness-gate helper (N1); (d) bounded lock acquire, `REAP_LOCK_TIMEOUT_S`, `ReapOutcome.LOCK_BUSY` + `OUTCOME_EDGES` row; the D3 signature shape |
| `tests/test_dag_tick.py` | V-a, V-b (end-to-end), V-d arms; `_ctx` gains the new fields only if they are made required (they should not be; see §3d) |
| `tests/test_codex_verdict.py` | V-b `preview()` parity and byte arms; V-d lock arms; the two `is_settled=` call sites at `:499` and `:517` if D3-A is ratified |
| `python/verification/suites.toml` | **(b), required, reviewed:** `workflow.codex-verdict-contract` `per_path_tokens` (`:2638`) and its description's outcome count (`:2630`), exactly as listed in §3 (d) "Contract tokens"; **D6:** the one `dag_tick.py` token named there. *(D5, optional:)* `workflow.dag-tick-wiring` **description prose only** (`:1963`). No other `per_path_tokens` entry changes |
| `python/src/dotfiles_setup/main.py` *(D5, optional)* | `--dry-run` help text only (`main.py:1917-1921`), so it says verdicts are previewed, not consumed |

**Forbidden:**

- `coordinator_handoff.py` (U2 = A is read-only) and `session_common.py` (imported, not edited);
- `mise.toml`;
- any `scripts/*.sh` or `.devcontainer/scripts/*.sh`;
- `tests/test_codex_lane.py` and `tests/test_codex_lane_e2e.py`. They construct
  `TickContext` with the current 10 keyword arguments (`test_codex_lane.py:951-964`,
  `test_codex_lane_e2e.py:214-227`), so new fields **must have defaults**;
- `python/src/dotfiles_setup/classifier_tables.py` and `python/src/dotfiles_setup/token_audit.py`
  (no `AMBIGUITY_ALLOWED` entry may be added to dodge N1);
- the installed plist.

## 3. Interfaces

### (a) `dag_tick.execute_respawn`: fresh terminal and superseded refusals

The signature is unchanged (`node_id, ctx, *, is_alive=None, proc_start=None`). The
invariant stays as it is at `dag_tick.py:1203-1213` and `:1236-1239`: **all reads first,
then all decisions, then `Popen`.** No I/O may sit between the last guard and `Popen`.

**Reads**, all up front:

- `load_state_json(ctx.jobs_dir, node_id)` (`dag_tick.py:951-971`);
- `read_roster(ctx.daemon_dir)`;
- **NEW: the handoff read.** From the fresh state data take
  - `sessionId`. It is valid when `session_common.valid_session_id` passes and
    `sessionId[:SHORT_ID_LEN] == node_id` (`session_common.py:31`, `:38`, `:59-61`, `:72-74`);
  - `name` (`session_common.py:87-96`).

  If `ctx.handoff_state_dir` is not None and `sessionId` is valid, read the launch
  state at `ctx.handoff_state_dir / f"{sessionId}.json"` with
  `coordinator_handoff._read_launch_state` (D2). The result is "launched" when
  `"launch" in state` or `_started_pending(state) is not None`. That is the exact
  predicate `retire` uses (`coordinator_handoff.py:1099-1104`) and the one `launch`
  refuses on (`:846-847`). `StateUnreadableError` (an `OSError`, `session_common.py:55-56`)
  or any other `OSError` means "unreadable".

  ⚠️ **File existence is NOT the signal.** `decide()` writes `<sessionId>.json` on
  *every* coordinator call (`last_seen`; `coordinator_handoff.py:338`, `:351-355`). A
  coordinator that merely crossed the measurement threshold has the file and no
  launch.

  **Why reading without `state_lock` is safe (MISSING-6).** `write_state` is atomic
  (tmp + `replace`, `session_common.py:119-127`), so a reader sees an old or a new file and
  never a torn one. `_read_launch_state` reads the started receipt **before** the state
  (`coordinator_handoff.py:263-279`), so a finalisation that races the read is still seen as
  launched. It writes nothing; it only reads and logs a warning. The tick must not take
  `state_lock`: that would make a handoff transaction block the watchdog.

**Decisions**, in this order. Each refusal returns its SKIP line:

1. `fresh_data is None` → the existing SKIP, unchanged (`dag_tick.py:1242-1246`).
2. **NEW:** `is_terminal(fresh.state, fresh.tempo, queued_prompt=fresh.queued_prompt)` →
   `f"dag-tick: SKIP respawn {node_id} — terminal since classification (state={fresh.state}, tempo={fresh.tempo})"`.
3. The existing `is_needs_human` check. **Keep the line
   `if is_needs_human(fresh.state, fresh.needs, queued_prompt=fresh.queued_prompt):`
   byte-identical and present exactly once** (a `per_path_tokens` token, `suites.toml:1974`;
   N1).
4. **NEW, superseded:**
   - launched → `"dag-tick: SKIP respawn <id> — superseded: coordinator-handoff launch recorded for <sessionId>"`;
   - unreadable → `"… — superseded check failed: <reason>; not respawning on doubt"`;
   - `ctx.handoff_state_dir is None` **and** `is_coordinator(name)` → SKIP "handoff state
     dir unresolved";
   - invalid or missing `sessionId` **and** `is_coordinator(name)` → SKIP "no valid sessionId".

   Non-coordinator nodes with an unresolved state dir or an invalid `sessionId` proceed.
   This is ratified as the U2 detail: fail closed for coordinator-named nodes, open
   otherwise. `launch` refuses non-coordinators (`coordinator_handoff.py:804-810`), so a
   genuine record only exists for coordinators. The record is still checked for every
   node whose `sessionId` is valid.
5. The existing pid-alive SKIP, unchanged.
6. `Popen`. Its argv, env strip, `cwd=Path.home()` and `start_new_session` are all unchanged
   (`dag_tick.py:1255-1266`).

**Shape:** ruff runs `select = ["ALL"]` with default ceilings (`pyproject.toml:71-94`; no
`[tool.ruff.lint.pylint]` override; `max-complexity = 10` at `:152-153`). The current
function already has 5 returns (`dag_tick.py:1243`, `:1249`, `:1254`, `:1266`, `:1271`); adding
2 inline breaks the return ceiling (A2). Split it into a read step and a **pure** decision helper
that returns `str | None` (the SKIP line or None). **Do not** introduce a function whose return
annotation is an enum defined in `dag_tick.py`. `classifier_tables.classifier_shaped` flags any
such function as an unregistered classifier (`classifier_tables.py:1025-1065`, `:1221-1260`),
and the registry file is forbidden here.

**D1, where the state dir is resolved (scribe default):** add
`handoff_state_dir: Path | None = None` to `TickContext`. `build_tick_context`
resolves it **once per tick** as
`session_common.main_checkout(Path(cwd)) / coordinator_handoff.STATE_SUBDIR`. Any
`SessionError` becomes `None`. `main_checkout` already carries a 30 s timeout
(`session_common.py:32`, `:183-203`) and raises `SessionError` on every failure.

Why the context and not `execute_respawn`: tests monkeypatch `dag_tick.subprocess.Popen`,
which breaks any real `subprocess.run` inside the patched scope
(`tests/test_dag_tick.py:1993-1997`). Resolving in the context keeps `execute_respawn` free of
subprocess calls, and lets tests inject a `tmp_path` state dir. Only two tests call
`build_tick_context` (`tests/test_dag_tick.py:2305`, `:2322`), and neither patches
`subprocess.run`.

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
- The liveness gate (`lane_is_settled`, read-only, `codex_verdict.py:336-370`) runs
  first, exactly as in `reap`.
- The docstring must say: unlocked reads can race a real reaper, and the output means
  "would".

**Implementation:** today, `_read_payload` consumes on failure (`codex_verdict.py:518-534`)
and `_reap_locked` consumes and marks (`:546-556`, `:564-565`). Split both into:

- **one pure decision step** that returns the `ReapResult` plus its effects (consume?
  lane record to mark reaped?);
- **one effects step**, which keeps using `_consume` (so
  `source.replace(run_dir / PROCESSED_FILENAME)` stays a single line, `:396`) and `_mark_reaped`.

`reap()` = gate → bounded lock → decide → apply effects. `preview()` = gate → decide.
There must be **no second copy** of the CAS (`_cas_check`, `:449-498`) or the payload
logic. **The liveness gate lives in exactly one private helper that both `reap` and
`preview` call (N1).** That helper holds the single `gate = …` assignment and the single
`if not gate(run_dir):` line (today `:425-426`), because each of those is a contract token that
must match `codex_verdict.py` exactly once. Keep `def _read_payload(` and `def _cas_check(` as
names. Keep each helper under ruff's return and argument ceilings by splitting, the way
`_cas_check` was split (`:457-460`).

**Effect parity with today**, which must be preserved exactly:

| Outcome | Consume (rename) | Mark `reaped` |
|---|---|---|
| CAS refusals (OWNER/STATUS_MISMATCH, ALREADY_PROCESSED) | no | no |
| LANE_UNREADABLE | yes | no |
| FILE_MISSING | no (nothing to rename) | no |
| PARSE_FAILED | yes | no |
| APPROVED / REVISE / REJECTED | yes | yes |

**`dag_tick.reap_codex_lanes`** (`dag_tick.py:1303-1348`): when `ctx.dry_run` is set,
call `preview` and emit
`f"dag-tick: [dry-run] would CODEX-REAP {id} [{outcome}] edge={edge} — {detail}"`. Real
reaps keep the existing line, including the "edge is DECIDED here, not applied" suffix
(`:1342-1347`). That suffix is a token (`suites.toml:2638`) and must appear **once**, so the
dry-run line must not carry it. The `Edge.NONE`-is-quiet-unless-verbose filter (`:1340-1341`)
applies to both paths, **except `LOCK_BUSY`, which always prints** (U4). **How the two calls
share one argument list is D6**, because of N1.

### (d) Timeouts

**Module constants** (the U3 values, ratified):

```python
GATE_TIMEOUT_S = 10.0        # dag_tick
CENSUS_TIMEOUT_S = 20.0      # dag_tick
REAP_LOCK_TIMEOUT_S = 5.0    # codex_verdict
```

**`TickContext` additions** (a frozen `@dataclass` with 10 fields today,
`dag_tick.py:360-382`). Each new field has a default, so the forbidden test files keep
constructing it:

```python
gate_timeout_s: float = GATE_TIMEOUT_S
census_timeout_s: float = CENSUS_TIMEOUT_S
reap_lock_timeout_s: float = REAP_LOCK_TIMEOUT_S   # D4
handoff_state_dir: Path | None = None              # D1
```

`build_tick_context` (`dag_tick.py:1372-1392`) fills all four explicitly.

**`gate_preflight`** (`dag_tick.py:994-1021`) passes `timeout=ctx.gate_timeout_s`.
`subprocess.TimeoutExpired` is a `SubprocessError`, **not** an `OSError` (stdlib
`subprocess.py:129`, `:169`), so the existing `except OSError` (`:1014`) does not catch it.
Add a separate clause:

```python
logger.warning("dag-tick: gate preflight timed out after %gs", ctx.gate_timeout_s)
return "unknown"
```

`"unknown"` then proceeds, as it does today (`:1423-1428`).

**`read_census`** (`dag_tick.py:1024-1068`) passes `timeout=ctx.census_timeout_s`. On
`TimeoutExpired` it logs
`logger.warning("dag-tick: census timed out after %gs", ctx.census_timeout_s)` and
returns `[]`. That warning is distinct from the four existing ones (`:1044-1066`).

**`codex_verdict.reap`** acquires `.reap.lock` with `LOCK_EX | LOCK_NB` plus a
monotonic deadline and short sleeps. This is the `session_common.state_lock` pattern
(`session_common.py:130-152`), including the `errno in {EACCES, EAGAIN}` discrimination
and re-raising any other `OSError`.

- The lock file stays exactly `run_dir / LOCK_FILENAME`, opened with `"a"`, because
  `codex_lane` locks the same file (`codex_lane.py:310-315`).
- On expiry it returns
  `ReapResult(ReapOutcome.LOCK_BUSY, Edge.NONE, f".reap.lock held for {t:g}s — not read; retried next tick")`
  and consumes nothing.
- New enum member: `LOCK_BUSY = "lock_busy"`, under the "no-ops" group
  (`codex_verdict.py:143-147`).
- New row: `ReapOutcome.LOCK_BUSY: Edge.NONE,` in `OUTCOME_EDGES` (`:159-170`).

**Contract tokens: the reviewed `suites.toml` edit (correction (b), with N1).** In
`workflow.codex-verdict-contract` `per_path_tokens` (`suites.toml:2638`), the
`python/src/dotfiles_setup/codex_verdict.py` list changes exactly so:

| Old token | New token(s) | Why |
|---|---|---|
| `'fcntl.flock(handle.fileno(), fcntl.LOCK_EX)'` | the implemented bounded-acquire line, byte-exact (e.g. `'fcntl.flock(handle.fileno(), fcntl.LOCK_EX \| fcntl.LOCK_NB)'`) **and** `'ReapOutcome.LOCK_BUSY: Edge.NONE'` | the old token ends `LOCK_EX)`, so a `LOCK_EX \| LOCK_NB` acquire no longer contains it, and a comment-only stand-in would be a dodge |
| `'gate = lane_is_settled if is_settled is None else is_settled'` | **D3-A only:** the seams-form gate line, byte-exact as implemented in the single gate helper | D3-A removes the `is_settled` parameter. Under D3-B/C this token stays byte-identical |

The description (`:2630`) changes "all ten reap outcomes" to "all eleven reap outcomes". Every
other token in that suite stays byte-identical (constraint 9). The implementer makes this edit,
and the coordinator's review checks the new tokens against the implemented lines (§5 "Gates").

**D3, a ratified-wording conflict (blocks dispatch).** The ratified text says
"`codex_verdict.reap` gains a keyword `lock_timeout_s`". `reap` already has 5
parameters (`codex_verdict.py:399-406`), so a sixth breaks ruff's argument ceiling.
The repo treats that ceiling as binding and bundles parameters into a dataclass to
satisfy it (`classifier_tables.py:581-588`; `tests/test_dag_tick.py:2629-2631`).

- **D3-A (recommended):** add
  `@dataclass(frozen=True) class ReapSeams: is_settled: Callable[[Path], bool] | None = None; lock_timeout_s: float = REAP_LOCK_TIMEOUT_S`.
  Replace `is_settled=` with `seams: ReapSeams | None = None` on both `reap` and
  `preview`; `preview` ignores `lock_timeout_s`. Update the only two `is_settled=`
  call sites (`tests/test_codex_verdict.py:499`, `:517`; none in `python/src`).
  - PRO: 5 parameters each; the lock timeout stays injectable.
  - CON: deviates from the ratified spelling, edits two existing tests, and replaces one more
    contract token.
- **D3-B:** the literal ratified signature (6 parameters) plus a reviewed ruff
  `max-args` change.
  - PRO: matches the wording.
  - CON: a lint-config relaxation needs Ray's explicit approval (zero-skip policy);
    not recommended.
- **D3-C:** no parameter; `reap` reads `REAP_LOCK_TIMEOUT_S`.
  - PRO: no signature change.
  - CON: lock arms cost 5 s of wall clock each; `TickContext` cannot inject.
    Tests must not monkeypatch our own module (`tests/AGENTS.md:90-93`).

`reap_codex_lanes` passes `seams=ReapSeams(lock_timeout_s=ctx.reap_lock_timeout_s)`
under D3-A.

### U6: corrected text

The vendor doc says: "`claude respawn <id>`: Restart a session, running or stopped"
(`knowledge-base/sources/agent-harness-docs/docs/claude-code/agent-view.md:695`).

- **`dag_tick.py:508-512`** (`is_reply_queued` docstring): replace "and `claude respawn`
  refuses an already-running session anyway — so a respawn here would be a no-op
  reported as a recovery". New meaning: `claude respawn` restarts a running session
  too, so a respawn here would restart a live worker out from under its own work.
  Making the shape visible remains the fix.
- **`dag_tick.py:678-681`** (`_reply_queued_reason` docstring): the same correction.
- **`dag_tick.py:683-690`** (`_reply_queued_reason()` return). The proposed exact text
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
- **`dag_tick.py:1267-1270`** (comment above the RESPAWN return): "requested" stays.
  Remove the "CLI has its own already-running refusal" justification and replace it
  with: the child is never read back, and the fresh re-checks narrow the window but do
  not close it.
- **(g) `dag_tick.py:102-115`** (module bullet "The respawn precondition is PID-liveness only,
  never `tempo`/in-flight"; N2 widens the line to the whole bullet): the precondition is now
  "fresh state readable, not terminal, not escalated, not superseded, pid not alive". The
  "never skip on `tempo == "active"` alone" half stays true, because `is_terminal` treats
  `tempo == "active"` as non-terminal (`dag_tick.py:395`), so a crash mid-activity still
  respawns. Keep that half and its 565 B6 evidence.
- **(g) `dag_tick.py:1171`** (summary line "after a fresh ESCALATION and PID re-check"): name
  all four re-checks (terminal, escalation, superseded, PID).
- **(g) `dag_tick.py:1193`** ("covers BOTH axes it must"): there are now four decision axes
  from three reads.
- **(g) `dag_tick.py:1203`** ("BOTH reads happen first, THEN both decisions"): three reads
  (state, roster, handoff record), then all decisions. The DISTANCE argument is unchanged.
- **(N2) `dag_tick.py:1222-1234`** ("Deliberately PID-liveness only — no `tempo`/in-flight
  check"): same correction as `:102-115`.
- **(N2) `dag_tick.py:1236-1239`** (the inline comment "BOTH reads first, THEN both
  decisions"): three reads first, then every decision.
- **D5 (optional):** the same corrections in the `suites.toml:1963` description prose (it
  repeats "the CLI refuses an already-running session" and "The fresh re-check covers BOTH axes,
  and BOTH reads happen first with both decisions after"), and the `main.py:1920` `--dry-run`
  help. Suggested help text: "Print the planned actions and Codex reap previews, then exit
  without spawning anything or consuming a verdict".

**Do not touch** `_needs_human_reason()` (`dag_tick.py:616-651`). It is golden-pinned
and reproduced verbatim by `dag_project` (`:654-669`).

## 4. Constraints and invariants

1. **LaunchAgent stays disabled.** Never run `mise bootstrap`, `mise bootstrap macos
   launchd-agents apply`, `launchctl enable/bootstrap/load`, or any live
   `claude respawn/stop/rm`. Tests use fakes or `tmp_path` executables only. **State
   this in the lane brief:** hook_guard cannot see codex lane commands.
2. **Respawn stays respawn.** No `--resume`, no prompt injection, no new verb.
3. **#1644 holds.** `ActionKind` stays exactly `{RESPAWN, LOG}` (`dag_tick.py:295-299`);
   there is no `execute_stop`; DONE plans nothing (`:710-713`). The forbid tokens must
   stay absent: `'"stop", node_id]'`, `"ActionKind.STOP"`, `'STOP = "stop"'`
   (`suites.toml:1983`).
4. **Fail toward not respawning.** Every new unanswerable read (unreadable record,
   unresolved state dir for a coordinator, invalid `sessionId` for a coordinator)
   yields SKIP. A timeout yields "unknown"/`[]`/`LOCK_BUSY`, never RESPAWN.
5. **Reads → decisions → spawn** in `execute_respawn`, with no I/O after the last guard.
6. **One predicate source.** Terminal = `is_terminal`, escalation = `is_needs_human`,
   both fed by `node_from_state` (`dag_tick.py:931-948`). Launched =
   `coordinator_handoff._read_launch_state` + `_started_pending` (D2). There is no
   parallel "terminal-ish" or "launched-ish" check.
7. **Dry-run is byte-preserving for every Codex lane.** That covers verdict, processed
   file, `lane.json`, `exit.marker`, and the presence or absence of `.reap.lock`. The
   tick's own lock file and stdout are allowed.
8. **`OUTCOME_EDGES` stays exhaustive.** `test_every_reap_outcome_has_a_defined_edge`
   (`tests/test_codex_verdict.py:553-560`) must cover `LOCK_BUSY`.
   `test_the_escalating_outcomes_are_exactly_the_inverted_set` (`:563-578`) must stay
   green unchanged; `LOCK_BUSY` → `NONE` keeps that set intact.
9. **Contract tokens: each one present, and present EXACTLY ONCE (c, N1).** `mise run verify`
   checks presence (`require_tokens`). `mise run lint`'s `contract_token_uniqueness` checks that
   each `per_path_tokens` entry matches its file exactly once (`hk.pkl:388-395`, `:848-850`;
   `token_audit.py:351-354`, `:389-407`). No allowlist entry covers `dag_tick.py` or
   `codex_verdict.py`. This binds three suites:
   - `workflow.dag-tick-wiring` (`suites.toml:1974`) and `workflow.dag-projection-wiring`
     (`:1999`), on `dag_tick.py`. Unchanged. The fragile one is
     `if is_needs_human(fresh.state, fresh.needs, queued_prompt=fresh.queued_prompt):`. Keep the
     variable name `fresh`, and keep the line once even after the read/decide split. New text
     must not add a second `TERMINAL_STATES:` (today only `:180`).
   - `workflow.codex-verdict-contract` (`suites.toml:2638`), on `codex_verdict.py`. Byte-identical
     and once: `def reap(`, `def _cas_check(`, `def _read_payload(`, `def lane_is_settled(`,
     `if not gate(run_dir):`, `source.replace(run_dir / PROCESSED_FILENAME)`,
     `OUTCOME_EDGES: dict[ReapOutcome, Edge] = {`, the three `…: Edge.NEEDS_HUMAN` rows,
     `_EXIT_LINE_PREFIX in (run_dir / LANE_LOG_FILENAME).read_text()`, `wrote empty content to`,
     and the schema/parse tokens. Changed, only as listed in §3 (d) "Contract tokens".
   - The same suite, on `dag_tick.py`. Byte-identical and once: `def reap_codex_lanes(`,
     `def read_rework_count(`, `reap_lines = reap_codex_lanes(result.classified, ctx)`,
     `CODEX_LANE_DIRNAME = "codex-lane"`, `DEFAULT_MAX_REWORK = 2`,
     `expected_owner=classified.node_id,`, `max_rework=ctx.max_rework,`,
     `DECIDED here, not applied`. `result = codex_verdict.reap(` is kept or replaced only per
     **D6**.
   - Test-file tokens in that suite (`tests/test_codex_verdict.py`, `tests/test_dag_tick.py`) are
     function names. New tests must not reuse them.
10. **No module-defined-enum return types on new functions** (classifier_axes
    `unlisted`). `ReapOutcome` and `Edge` are already enums in `codex_verdict`. The new
    decision helper must return `ReapResult` (a dataclass) or a tuple, never a bare
    `ReapOutcome`/`Edge`, and the effects flag must not be a new enum it returns.
11. **Tests mock only system boundaries.** Use the injected `is_alive`/`proc_start`
    seams, `TickContext` fields and `ReapSeams`. Never monkeypatch our own module
    functions or constants (`tests/AGENTS.md:90-93`). Environment variables are a boundary
    (V-a3's `delenv`). Real processes in tests may use only base-OS tools. `tests/AGENTS.md:113`
    names `git` and `sh`/`bash`; it does not name `sleep` (MISSING-10), but `exec sleep` fakes
    already have precedent (`tests/test_sync.py:493`, `tests/test_bounded_wait.py:183`).
12. **No inline suppressions.** Respect ruff's argument, return and complexity
    ceilings by splitting functions.
13. **Residuals.** These are not fixed here; record them in the PR body:
    - a read-to-spawn window remains (`dag_tick.py:1215-1220`);
    - a coordinator-handoff run with a non-default `--state-dir`
      (`coordinator_handoff.py:1251-1256`) is invisible to (a);
    - the worst-case tick can exceed the 60 s interval: 10 + 20 + N×5 s, plus up to
      30 s for `main_checkout`. The tick lock turns overlap into a silent skip
      (`dag_tick.py:242-244`, `:974-991`);
    - **(f) A4 / U1 deploy-clone mismatch (PR-2 requirement).** The ratified PR-2 plist runs a
      pinned `[bootstrap.repos]` deploy clone (`spec-dag-tick-safety.md:410`). `git worktree list`
      in a separate clone returns that clone, so `handoff_state_dir` would resolve to the deploy
      clone's `.agent/state/coordinator-handoff`. The record would read "absent" and a
      superseded coordinator would respawn, failing open. Harmless in PR 1 while the
      LaunchAgent stays disabled (`mise.toml:1565` still names the main checkout). **PR 2 must
      resolve the handoff state dir against the dotfiles main checkout explicitly**, not from
      the tick's cwd;
    - **(f) mid-launch window.** While `claude --bg` runs, the state holds a plain
      `launch_pending` (`{"name", "at"}`, no `started`, `coordinator_handoff.py:923`) for up to
      `LAUNCH_TIMEOUT_S` = 60 s (`:87`, `:936-942`). That does not count as "launched", so a
      respawn in that window is possible. It is the same predicate `retire` uses
      (`:1104`), so it is accepted;
    - **N3: unscrubbed git context in `main_checkout`.** `session_common.main_checkout` runs
      `git -C <cwd> worktree list` without dropping `GIT_DIR`/`GIT_WORK_TREE`
      (`session_common.py:186-192`), so an inherited git context retargets it. The launchd
      environment carries none. Fixing it means editing `session_common.py`, which is outside
      this allowlist.
14. **D2 import:** `from dotfiles_setup.coordinator_handoff import STATE_SUBDIR, _read_launch_state, _started_pending`,
    **plus (g)** `from dotfiles_setup.session_common import SHORT_ID_LEN, SessionError, is_coordinator, main_checkout, valid_session_id`.
    - Use the `from`-import form. Attribute access `coordinator_handoff._x` would trip
      SLF001; `pyproject.toml:96-112` has no per-file ignore for `dag_tick.py`.
    - Precedent for a cross-module private `from`-import that passes lint today:
      `coordinator_handoff.py:67`.
    - No cycle: coordinator_handoff imports only `handoff_inbox`, `reap`,
      `session_common` and `session_orphans` (`:45-67`). Their closure adds `hook_guard`,
      `ask_quality`, `branch_guard`, `script_guard`, `heredoc` and `bash_budget`
      (`session_orphans.py:24`, `hook_guard.py:47-48`, `script_guard.py:43`). Across
      `python/src`, `dag_tick` is imported only by `codex_lane.py:82`, `dag_project.py:72` and
      `main.py:50`, none of which is in that closure.

## 5. Verification

Every new test needs a positive arm, a control arm, and a **must-fail-on-revert**
check. To run that check: `git add` first, then delete **only** the added guard line(s)
(a realistic regression, not a rename), run the named test, confirm it FAILS, and
restore with `git checkout -- <file>` from the staged copy. Report each
revert-then-fail rc.

### V-a: terminal / superseded re-check (`tests/test_dag_tick.py`)

The pattern to copy is the snapshot → mutate → execute race pair at
`tests/test_dag_tick.py:2173-2247`. Inject `Popen` via
`monkeypatch.setattr(dag_tick.subprocess, "Popen", …)` as those tests do.

**Fixture trap (MISSING-9):** V-a2 needs an **8-character** node id, because
`sessionId[:SHORT_ID_LEN]` must equal it and `_SESSION_ID_RE` needs at least 8 characters
(`session_common.py:31`, `:38`). The existing 6-character ids (`"abc123"`,
`tests/test_dag_tick.py:2279`) cannot be reused.

| Arm | Fixture | Must hold |
|---|---|---|
| V-a1 positive (parametrize `done`/`failed`/`stopped`) | `{"state":"blocked","tempo":"idle"}`, roster empty → classify DEAD → plan RESPAWN; then rewrite to `{state:<s>, tempo:"idle"}` | `execute_respawn` returns SKIP containing "terminal since classification"; a `Popen` stub that raises is never called |
| V-a1 control: still DEAD | rewrite to `{"state":"blocked","tempo":"blocked"}` | `Popen` is called once with `["claude","respawn",id]` |
| V-a1 control: not-terminal axes | `stopped` + `tempo:"active"`; `stopped` + `queuedPrompt:"x"` | both still respawn, so the guard is `is_terminal`, not "any stopped" |
| V-a2 positive: launch | state.json carries `name:"dotfiles-x.coordinator"`, `sessionId:<8-char node id + suffix>`; `ctx.handoff_state_dir=tmp_path/"ho"` holds `<sessionId>.json` = `{"launch":{"successor":"s","at":"t"}}` | SKIP "superseded" |
| V-a2 positive: started-pending | `<sessionId>.json` = `{"launch_pending":{"started":true,"name":"s"}}` | SKIP "superseded" |
| V-a2 positive: receipt only | only `<sessionId>.started.json` = `{"started":true,"census":[]}` | SKIP "superseded" |
| V-a2 positive: unreadable | `<sessionId>.json` = `"{not json"`, no receipt | SKIP "superseded check failed" |
| V-a2 positive: unresolved dir | coordinator-named node, `handoff_state_dir=None` | SKIP "handoff state dir unresolved" |
| **V-a2 positive: invalid sessionId (e)** | coordinator-named node, valid `handoff_state_dir`; parametrize `sessionId` as (i) absent, (ii) `"x"` (fails `valid_session_id`), (iii) a valid id whose first 8 characters ≠ the node id | SKIP "no valid sessionId", for every cell |
| V-a2 **control: decide-only file** | `<sessionId>.json` = `{"last_seen":{"at":"t","percent":31}}` (the shape `decide` writes, `coordinator_handoff.py:353-355`) | **respawns**, which proves the signal is a launch record, not file existence |
| V-a2 control: absent | no file | respawns |
| V-a2 control: non-coordinator, unresolved dir | no `name`, `handoff_state_dir=None` | respawns (fail-open side of the U2 detail) |
| V-a2 control: non-coordinator, invalid sessionId | no `name`, `sessionId:"x"` | respawns (fail-open side, for the arm (e) adds) |
| V-a3 build-context | **first** `monkeypatch.delenv(v, raising=False)` for each of `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_COMMON_DIR`, `GIT_OBJECT_DIRECTORY`, `GIT_ALTERNATE_OBJECT_DIRECTORIES` (N3; the names `child_env.GIT_CONTEXT_NAMES` lists, `child_env.py:36-45`); then `build_tick_context(_tick_args(cwd=str(tmp_path/"not-a-repo")))` | `handoff_state_dir is None`; `gate_timeout_s == 10.0`, `census_timeout_s == 20.0`, `reap_lock_timeout_s == 5.0`. Extends the tests at `:2296-2324` |

- **Revert check V-a1:** delete the terminal guard → the three V-a1 positives fail and
  the controls stay green.
- **Revert check V-a2:** delete the superseded guard → the **six** V-a2 positive rows fail
  (launch, started-pending, receipt only, unreadable, unresolved dir, invalid sessionId), and
  the controls stay green.
- **Regression:** the existing `test_execute_tick_never_stops_a_done_node_with_live_pid`
  (`:2544-2582`) and the escalation race pair (`:2173-2247`) stay green unchanged.

### V-b: dry-run preserves lane bytes; normal run consumes

**End-to-end** (`tests/test_dag_tick.py`): extend the shape of
`test_execute_tick_dry_run_reports_without_spawning` (`:2418-2435`), which today creates
no lane (review `:63`). Add `_codex_lane(ctx, "dead1", verdict="approve")` (helper at
`:2619-2650`). Before and after `execute_tick` with `dry_run=True`, record the sorted
`os.listdir(run_dir)` and the sha256 of every file.

| Arm | Must hold |
|---|---|
| V-b1 positive | listing and hashes are identical; `.reap.lock` is absent; stdout contains `[dry-run] would CODEX-REAP dead1 [approved] edge=advance` |
| V-b1 control **(d)** | same fixture with `dry_run=False`, **and a recording `Popen` stub** in place of the raising one, shaped like `_fake_popen` at `tests/test_dag_tick.py:2447-2451`: the fixture node is DEAD (empty roster, `:2422-2423`), so a normal tick plans and executes RESPAWN, and the raising `_fail_popen` (`:2426-2431`) would fail the arm for the wrong reason. Assert `verdict.processed.json` exists, `verdict.json` is gone, `json.loads(lane.json)["status"] == "reaped"`, and the stub recorded `["claude","respawn","dead1"]`. (The alternative, making the node ALIVE via a roster entry, also works but changes two variables at once) |
| V-b2 (parametrize the failure lanes) | `verdict="{not json"` (PARSE_FAILED), no `lane.json` (LANE_UNREADABLE), no verdict (FILE_MISSING): dry-run → bytes and listing identical with no `.reap.lock`; normal run (with the same recording stub) → the PARSE_FAILED and LANE_UNREADABLE lanes are renamed, and FILE_MISSING creates `.reap.lock`. Each normal arm proves its dry-run arm could have failed |

**Unit** (`tests/test_codex_verdict.py`):

| Arm | Must hold |
|---|---|
| V-b3 parity (parametrize every reachable outcome: approve, revise under/at bound, reject, file_missing, parse_failed, empty file, lane_unreadable, owner_mismatch, status_mismatch, already_processed, not_settled via injected gate) | build two identical lanes A and B; `preview(A)` equals `reap(B)` on outcome, edge, detail and verdict; A is byte-identical afterwards and has no `.reap.lock`. (N4) Every listed outcome's detail is path-free today (`codex_verdict.py:476-497`, `:512-534`, `:551-575`); if one ever embeds `run_dir`, compare it with the path normalised |
| V-b3 control | `reap(A)` afterwards does mutate A wherever the effect-parity table (§3b) says it should |

- **Revert check V-b1/V-b2 (shape per D6):** make the dry-run routing a no-op. Under D6-A,
  replace the selection with `reaper = codex_verdict.reap` → V-b1 and V-b2 dry-run arms fail.
  (Under D6-B, delete the dry-run branch.)
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
| V-d4 control | an `OWNER_MISMATCH` lane, non-verbose | still prints nothing (the existing quiet rule, `:2711-2720`) |

- **Revert check V-d1:** remove both `timeout=` keyword arguments → the elapsed
  assertion fails (about 20 s).
- **Revert check V-d3:** restore the blocking `LOCK_EX` acquire. The call then blocks
  until the holder releases, so run that check with the holder in a `threading.Timer`
  that releases after 3 s and assert elapsed < 2 s → it fails.
- **Keep `exec` in the V-d1 fake, for cleanliness, not timing (MISSING-8).** On POSIX,
  `run()` kills the direct child and then only `wait()`s it; it does not `communicate()` again
  (stdlib `subprocess.py:554-570`). A fake without `exec` still returns promptly, but it leaves
  the `sleep` grandchild orphaned. `exec` makes `sleep` the direct child, so the kill reaps it.
  The V-d1 revert timing is unaffected either way.
- V-d3's in-process holder relies on two `open()` descriptions conflicting under
  `flock`. `test_lock_contention_second_acquire_fails` already exercises that mechanism
  (`tests/test_dag_tick.py:1226-1234`), and so does, more closely, the producer's contention test
  on the real `.reap.lock` (`tests/test_codex_lane.py:530-535`, N5).

### Gates

Run each through `mise run gate -- run <name>`. Its rc is the gate's result, and the
typed result lands in `.agent/gate-results/`.

- `lint`, `pytest`, `verify`: always. `verify` binds token **presence** in the suites.toml
  contracts; `lint` binds token **uniqueness** through `contract_token_uniqueness` (constraint 9,
  N1). Before running them, the coordinator also runs `uv run --project python dotfiles-setup
  token-audit` once on its own, so a uniqueness failure is read as that, not as a lint mystery.
- `lint-docs`: not applicable (no `.claude/**/*.md` or `AGENTS.md` change).
- `pin-actions`: not applicable.

**Evidence to return:**

- each gate's rc from `.agent/gate-results/`;
- each revert-then-fail rc (V-a1, V-a2, V-b1/2, V-b3, V-d1, V-d3);
- `git diff --stat` showing only §2 paths;
- the `suites.toml` diff, so review can check each new token against the line it binds.

## 6. Commit

- **Branch:** `fix/dag-tick-safety-pr1`, created from origin/main at `13af2848` or later,
  **before the first edit** (do-not.md #9).
- **COMMIT: caller.** The implementer leaves the work **uncommitted** on the branch
  and returns the evidence. The caller reviews, commits and ships via `mise run ship`
  only.
- **Message:** `fix(dag-tick): refuse respawn of terminal/superseded nodes, read-only dry-run reaping, bounded waits`.
- **Body:**
  - cite proposal 1 of `docs/research/kb/reports/agents/sdlc-team-review-dag-tick-aba49c5d.md`.
    It is tracked at the base (P46), so link it;
  - state that the LaunchAgent stays disabled, respawn is unchanged, and (c) is PR 2;
  - list the residuals from constraint 13, including the PR-2 requirement in (f);
  - name the `workflow.codex-verdict-contract` token edits (and the D6 edit), with the reason
    for each.
- End the commit with the session attribution trailer.

## 7. PREMISES

V = read by this lane during this run, at the cited line, in the 04h worktree at `13af2848`
unless another path is given. A = assumption, with the reason given. `.git/…` = the main
checkout's git dir.

| # | Premise | Cite | V/A |
|---|---|---|---|
| P1 | Main checkout HEAD is `main`; `refs/heads/main` = `refs/remotes/origin/main` = `13af28480ae4…`; the origin/main reflog records `ee3b29da → 13af2848` as a fast-forward fetch; the 04h worktree is at `13af2848` | `.git/HEAD:1`; `.git/refs/heads/main:1`; `.git/refs/remotes/origin/main:1`; `.git/logs/refs/remotes/origin/main:213-214`; `.git/worktrees/handoff-2026-10-04h/logs/HEAD:1-2` | V |
| P2 | `execute_respawn` reads state, then roster, then decides: unreadable → `is_needs_human` → pid-alive → `Popen`; there is no terminal or superseded check; exactly 5 returns | `python/src/dotfiles_setup/dag_tick.py:1240-1271` (returns `:1243`, `:1249`, `:1254`, `:1266`, `:1271`) | V |
| P3 | The reads-then-decisions ordering is a documented invariant | `dag_tick.py:1203-1213`, `:1236-1239` | V |
| P4 | `classify` returns DONE for a terminal node first; terminal = state ∈ {done, failed, stopped} ∧ tempo ≠ active ∧ no queued prompt | `dag_tick.py:558-559`, `:180`, `:385-395` | V |
| P5 | `node_from_state` is the shared builder for the census path and the fresh re-check | `dag_tick.py:931-948` | V |
| P6 | The false "CLI refuses an already-running session" claim appears in docstrings, the reason string and a comment | `dag_tick.py:508-512`, `:678-681`, `:686-689`, `:1267-1270` | V |
| P7 | Vendor doc: `claude respawn <id>` restarts a session "running or stopped" | `knowledge-base/sources/agent-harness-docs/docs/claude-code/agent-view.md:695` | V |
| P8 | `stopped` includes a `claude stop` or an outside kill | `agent-view.md:116` | V |
| P9 | Dry-run is honoured only in `_execute_or_preview`; `reap_codex_lanes` calls `codex_verdict.reap` unconditionally from `execute_tick` | `dag_tick.py:1289-1293`, `:1334-1339`, `:1436` | V |
| P10 | `reap` creates `.reap.lock` and blocks on `flock(LOCK_EX)` | `codex_verdict.py:434-446` (`:440`) | V |
| P11 | Consume = rename `verdict.json` → `verdict.processed.json`; mark = rewrite `lane.json` status `reaped` | `codex_verdict.py:386-396`, `:592-602` | V |
| P12 | LANE_UNREADABLE and PARSE_FAILED consume; FILE_MISSING returns without rename; success consumes and marks | `codex_verdict.py:546-556`, `:518-534`, `:510-517`, `:564-565` | V |
| P13 | `ReapOutcome` members (10) and the exhaustive `OUTCOME_EDGES` | `codex_verdict.py:127-147`, `:159-170` | V |
| P14 | `_cas_check` order is owner → idempotency → status, and it was split for ruff's return ceiling | `codex_verdict.py:449-498`, `:457-460` | V |
| P15 | `codex_lane` locks the same `.reap.lock` with a blocking flock and `"a"` mode | `codex_lane.py:310-315` | V |
| P16 | Gate and census `subprocess.run` calls have no `timeout=`; gate catches only `OSError`; the `ps` read has a 1 s timeout as precedent | `dag_tick.py:1006-1020`, `:1036-1049`, `:254-258`, `:847-857` | V |
| P17 | Gate "unknown" proceeds with a warning | `dag_tick.py:1423-1428` | V |
| P18 | `TimeoutExpired` subclasses `SubprocessError`, not `OSError`; on timeout, POSIX `run()` kills and then only `wait()`s the direct child | `~/.local/share/uv/python/cpython-3.14-macos-aarch64-none/lib/python3.14/subprocess.py:129`, `:169`, `:554-570` (the venv's base interpreter per the **main checkout's** `python/.venv/pyvenv.cfg:1`; the 04h worktree has no `.venv`) | V |
| P19 | A bounded flock pattern exists (`LOCK_NB`, monotonic deadline, EACCES/EAGAIN) | `session_common.py:130-152` | V |
| P20 | `main_checkout` has a 30 s timeout and raises `SessionError` on every failure; it passes no `env=` | `session_common.py:32`, `:183-203` (`:186-192`) | V |
| P21 | Job state.json is at `jobs/<sid[:8]>/state.json` and is trusted only when it carries the full `sessionId`; `name` is read from it; coordinator name regex | `session_common.py:72-96`, `:41` (`SHORT_ID_LEN` `:31`, `_SESSION_ID_RE` `:38`) | V |
| P22 | `read_state`: missing → `{}`, corrupt → `StateUnreadableError` (an `OSError`) | `session_common.py:55-56`, `:104-116` | V |
| P23 | Handoff state lives at `<main_checkout>/.agent/state/coordinator-handoff/<sessionId>.json`; the started receipt is `<sessionId>.started.json` | `coordinator_handoff.py:108`, `:258-260`, `:841-842`, `:1266-1267` | V |
| P24 | "Launched" = `"launch" in state` or a `launch_pending` with `started: True`, after receipt recovery via `_read_launch_state`; `retire` and `launch` use exactly this | `coordinator_handoff.py:251-279`, `:846-847`, `:1099-1104` | V |
| P25 | `decide()` writes `<sessionId>.json` (`last_seen`) on every coordinator call, so file existence ≠ launch; non-coordinators return earlier | `coordinator_handoff.py:338`, `:340-349`, `:351-355` | V |
| P26 | `launch` writes the started receipt, then promotes `launch_pending` to `launch` | `coordinator_handoff.py:952-996` | V |
| P27 | `retire` stops via `claude stop` after its blockers; it writes no retirement marker | `coordinator_handoff.py:1148-1170` | V |
| P28 | `launch` refuses a non-coordinator session | `coordinator_handoff.py:804-810` (message at `:806`) | V |
| P29 | No import cycle; a precedent of a cross-module private `from`-import | `coordinator_handoff.py:45-67`; `session_orphans.py:24`; `hook_guard.py:47-48`; `script_guard.py:43`; Grep `import.*dag_tick\|dag_tick import` over `python/src` → only `codex_lane.py:82`, `dag_project.py:72`, `main.py:50` | V |
| P30 | Nothing pins the full `_reply_queued_reason()` text. Tests assert only the substring "reply queued but undelivered" and the note prefix; suites tokens and `dag_project` do not include it | `tests/test_dag_tick.py:474`, `:1772-1774`; `suites.toml:1974`, `:1999`; Grep `reply_queued_reason` (docs/ excluded) → only `dag_tick.py:672`, `:723`, `:1143` | V |
| P31 | `_needs_human_reason` is golden-pinned and reproduced by `dag_project` | `dag_tick.py:616-669` | V |
| P32 | suites `dag-tick-wiring` tokens include the exact `is_needs_human(fresh.…)` line; its description repeats the false claim and the "BOTH axes / BOTH reads" text; forbid tokens ban the STOP shapes | `suites.toml:1974`, `:1963`, `:1983` | V |
| P33 | ruff `select = ["ALL"]`, no pylint ceiling override, mccabe 10; no SLF001 per-file ignore for `dag_tick.py` | `python/pyproject.toml:71-94`, `:96-112`, `:152-153` | V |
| P34 | The repo treats the argument ceiling as binding, including keyword-only parameters, and bundles to satisfy it | `tests/test_dag_tick.py:2619-2631` (5 params incl. 3 kw-only, "stays under ruff's argument ceiling"); `classifier_tables.py:581-588` | V |
| P35 | `classifier_shaped` flags any function returning an enum defined in its own module that has no REGISTRY entry | `classifier_tables.py:1025-1065`, `:1221-1260` | V |
| P36 | `TickContext` is a frozen dataclass constructed in 3 test files with exactly the current 10 keyword arguments | `dag_tick.py:360-382`; `tests/test_dag_tick.py:111-130`; `tests/test_codex_lane.py:951-964`; `tests/test_codex_lane_e2e.py:214-227` | V |
| P37 | Existing fake `run`/`Popen` stubs accept `**_kwargs`, so a new `timeout=` keyword does not break them | `tests/test_dag_tick.py:2408-2415`, `:2562-2569` | V |
| P38 | Patching `dag_tick.subprocess.Popen` breaks a real `subprocess.run` in the same test | `tests/test_dag_tick.py:1993-1997` | V |
| P39 | The existing dry-run tick test creates no Codex lane; its node is DEAD and its `Popen` stub raises | `tests/test_dag_tick.py:2418-2435` (`:2422-2423`, `:2426-2431`) | V |
| P40 | The never-stop test pins the `ActionKind` set and the absence of `execute_stop`, and asserts no non-census `subprocess.run` call | `tests/test_dag_tick.py:2544-2582` (`:2578`) | V |
| P41 | The escalation race pair (snapshot → mutate → execute, plus control) exists to copy | `tests/test_dag_tick.py:2173-2247` | V |
| P42 | Only two call sites pass `is_settled=` | `tests/test_codex_verdict.py:499`, `:517` (Grep `is_settled=` over `tests/` → those two; over `python/src` → 0) | V |
| P43 | The exhaustiveness and inverted-set tests exist | `tests/test_codex_verdict.py:553-578` | V |
| P44 | In-process double flock on separate `open()`s conflicts (the tests assert it) | `tests/test_dag_tick.py:1226-1234`; `tests/test_codex_lane.py:530-535` | V (test bodies read; that they pass is inherited from CI, not run here) |
| P45 | `--dry-run` help promises "without spawning anything"; the task comment calls it a "read-only preview" | `main.py:1917-1921`; `mise.toml:721` | V |
| P46 | Review proposal 1 wording; HIGH findings for the retire race, the respawn-refusal contradiction, and dry-run consumption; MEDIUM for hangs; the control arms. **Tracked at the base:** the worktree index contains its path (the control: the untracked `premise-verifier-jobdir-part2.md` and an invented name give 0). Its text matches the handoff-2026-10-04d copy line for line (both read in full, 127 lines). Not re-copied | `docs/research/kb/reports/agents/sdlc-team-review-dag-tick-aba49c5d.md:7`, `:8`, `:10`, `:14`, `:49`, `:55-63`; `.git/worktrees/handoff-2026-10-04h/index` Grep → 1 | V |
| P47 | Ratified rulings: U1 (PR 2: `[bootstrap.repos]` deploy clone), U2 = A, U3 to U7 = recommended | `docs/research/kb/raw/specs-2026-10-04d/spec-dag-tick-safety.md:408-413` (tracked at the base, index Grep → 1; identical lines in the handoff-2026-10-04d copy) | V |
| P48 | **N1:** `contract_token_uniqueness` runs `dotfiles-setup token-audit` in every `check` run; the audit counts each `per_path_tokens` entry with `str.count` and fails anything ≠ 1 that is not allowlisted; no allowlist entry names `dag_tick.py` or `codex_verdict.py` (control: the same Grep shape over python paths finds 3 entries) | `hk.pkl:388-395`, `:848-850`; `python/src/dotfiles_setup/token_audit.py:335-367`, `:389-407`, `:87` | V |
| P49 | `workflow.codex-verdict-contract` binds the LOCK_EX acquire, the `is_settled` gate line, `if not gate(run_dir):`, `def _read_payload(`, `def _cas_check(`, the rename, and in `dag_tick.py` the reap call and its keyword lines; its description says "all ten reap outcomes" | `suites.toml:2628`, `:2630`, `:2638` | V |
| P50 | Today the gate lines exist once, inside `reap` | `codex_verdict.py:425-426` | V |
| P51 | A recording `Popen` stub precedent for a DEAD node under a normal tick | `tests/test_dag_tick.py:2438-2451` | V |
| P52 | Only two tests call `build_tick_context`, and neither patches `subprocess.run` | Grep `run_tick\(\|build_tick_context\(` over tests/ → `tests/test_dag_tick.py:2305`, `:2322`; `:2296-2324` read | V |
| P53 | `child_env.GIT_CONTEXT_NAMES` lists the six git-routing variables | `python/src/dotfiles_setup/child_env.py:36-45` | V |
| P54 | `launch_pending` without `started` is the reservation during `claude --bg`, bounded by `LAUNCH_TIMEOUT_S` = 60 | `coordinator_handoff.py:923`, `:87`, `:936-942` | V |
| P55 | The plist's working directory is the main checkout today | `mise.toml:1561`, `:1565` | V |
| A1 | After `claude stop`, the harness persists `state:"stopped"` with a non-active tempo promptly, so the terminal re-check catches the retire race | `agent-view.md:116` documents the state, not the tempo or its timing; inherited from review `:7` ("latest stopped/idle state"). Not settleable from code | A |
| A2 | ruff's default return ceiling is 6, so 7 returns in `execute_respawn` would fail | `schemas/ruff.json:3001-3004` names `max-returns`/PLR0911 with no default; the codebase splits for "ruff's return-count ceiling" (`codex_verdict.py:229-231`, `:457-460`) without stating the number. Nothing contradicts 6 | A |
| A3 | `subprocess.run(timeout=)` with `capture_output=True` raises promptly even if the fake writes nothing | stdlib source read (P18); runtime not executed | A (checkable) |
| A4 | The handoff state dir resolved from `ctx.cwd` matches the one `coordinator_handoff` uses (`main_checkout(Path.cwd())`, `coordinator_handoff.py:1266-1267`) | Holds for PR 1: `mise.toml:1565` sets the main checkout as the working dir, and `:722` passes no `--cwd`. **It breaks under the ratified PR-2 deploy clone; see constraint 13 (f)** | A (checkable) |

---

## Pending architect decisions (stop here for ratification)

- **D3 (blocks dispatch: conflicts with ratified wording).** The ratified
  `reap(..., lock_timeout_s=)` makes 6 parameters, which breaks ruff's argument
  ceiling (P34). Recommended: **D3-A**, a `ReapSeams` bundle replacing `is_settled=`
  on `reap` and `preview`. B and C are in §3d. D3-A also replaces one more contract token
  (§3 (d) "Contract tokens").
- **D6 (NEW; blocks dispatch: edits a contract token).** How `reap_codex_lanes` routes
  dry-run to `preview` without repeating the keyword lines that must match `dag_tick.py`
  exactly once (N1, P48-P49).
  - **D6-A (recommended):** select the callable once, then call it once:
    `reaper = codex_verdict.preview if ctx.dry_run else codex_verdict.reap`, then
    `result = reaper(` with the existing keyword lines unchanged. A reviewed token edit in
    `workflow.codex-verdict-contract` replaces `'result = codex_verdict.reap('` with
    `'reaper = codex_verdict.preview if ctx.dry_run else codex_verdict.reap'` and
    `'result = reaper('`. PRO: one call site. `expected_owner=classified.node_id,` and
    `max_rework=ctx.max_rework,` stay byte-identical and unique, and the new token binds the
    dry-run routing itself, so deleting it fails `verify`. CON: one more contract-token edit,
    and the old token's literal spelling goes away.
  - **D6-B:** keep `result = codex_verdict.reap(` in an `else` branch, and give the dry-run
    branch a `preview` call whose arguments are spelled differently (e.g. a local
    `owner = classified.node_id`). PRO: no token edit. CON: the contract then binds only the
    real-reap call. A differently spelled argument list exists only to dodge the uniqueness
    gate, which the report calls out as a "comment-only dodge" in spirit. Not recommended.
- **D1.** Resolve `handoff_state_dir` once per tick in `build_tick_context` and inject
  it as a `TickContext` field. Recommended: yes.
  - PRO: no subprocess inside `execute_respawn` (P38); tests inject `tmp_path`. Only two
    tests reach `build_tick_context`, and neither patches `subprocess.run` (P52).
  - CON: one git call per tick, even on lock contention.
  - Alternative: resolve after acquiring the lock inside `execute_tick` via
    `dataclasses.replace`. That puts a `git` call inside every existing tick test's patched
    `subprocess.run`. `_fake_run_for_one_dead_node` raises on unexpected argv
    (`tests/test_dag_tick.py:2408-2415`), and the never-stop test asserts no non-census call
    (`:2578`). Both would break.
- **D2.** Import `coordinator_handoff._read_launch_state` / `_started_pending` /
  `STATE_SUBDIR` rather than re-deriving the "launched" predicate. Recommended: import.
  - PRO: one predicate source (constraint 6); identical to `retire`.
  - CON: a cross-module private import (precedent `coordinator_handoff.py:67`); `dag_tick`
    now transitively imports `reap`, `hook_guard` and its closure (constraint 14).
  - Alternative: a 3-line duplicate with a cross-reference comment and fixtures pinned
    to the P26 shapes.
- **D4.** Add `TickContext.reap_lock_timeout_s`. Without it, V-d4 waits the full 5 s.
  Recommended: add.
- **D5.** Include the optional `suites.toml:1963` description and `main.py:1920` help-text
  corrections (now including the N2 "BOTH axes / BOTH reads" prose). Recommended: include.
  Each repeats a claim that PR 1 makes false, or one it makes true only now. Description
  prose and help text are not tokens.

### Residuals accepted on the record (from the report)

- A1, ASSUMED: the stopped-state timing cannot be settled from code.
- A2, ASSUMED: ruff's default return ceiling of 6 is unread, but every codebase precedent is
  consistent with it.
- A3, ASSUMED (checkable): source-confirmed; no runtime run.
- A4, ASSUMED (checkable): holds for PR 1 while the LaunchAgent is disabled; it becomes the PR-2
  hazard in constraint 13 (f).
- MISSING-6, MISSING-8, MISSING-9 and MISSING-10: informational, each stated where it applies
  (Revision log).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): local reads only (04h worktree at `13af2848`: `dag_tick`, `codex_verdict`, `coordinator_handoff`, `codex_lane`, `session_common`, `child_env`, `classifier_tables`, `token_audit`, `hook_guard`, `main`, `pyproject.toml`, `suites.toml`, `hk.pkl`, `mise.toml`, `schemas/ruff.json`, tests, `tests/AGENTS.md`; main-checkout git refs, reflogs and the worktree index; the handoff-2026-10-04d copies of the aba49c5d review and the parent spec)
- [mrkhachaturov/agent-harness-docs](https://github.com/mrkhachaturov/agent-harness-docs): offline mirror `agent-view.md` read for respawn and stop semantics

---

## Architect ratification (coordinator 5a11da, 2026-10-04 ~12:40 CDT)

D1–D6: the recommended (or scribe-default) option of each is RATIFIED. Explicitly: **D3-A** (`ReapSeams` dataclass; the
reviewed `per_path_tokens` replacement listed in §3 (d) is authorised; D3-B is rejected because it relaxes a lint ceiling,
which needs Ray's approval under the zero-skip policy); **D6** recommended shape (choose the reaper callable once, one
reviewed `dag_tick.py` token edit as listed). d921a3f6 (#1662) is an ancestor of the base: `git merge-base --is-ancestor
d921a3f6 13af2848` rc=0, control (reverse) rc=1. Next: premise re-verification of this revision, then dispatch.

## Base pin + re-verification corrections (coordinator 5a11da, 2026-10-04, from premise-verifier-recheck-2026-10-04h.md)

- **Base: cut from origin/main `ad4dbc62`** (13af2848 + #1667 docs, #1665 saved-searches, #1658 bgisolation). This supersedes every "13af2848 or later". `git diff --stat 13af2848 ad4dbc62` over this spec's §2 paths touches only `python/verification/suites.toml` (+16 lines: a new `workflow.research-saved-search-wiring` suite inserted at :1501, plus token edits in two unrelated suites) and `coordinator_handoff.py` (`CROSS_SESSION_SETTINGS`, :106-112; launch_argv docstring). So every `suites.toml` anchor after :1500 shifts **+16** (e.g. :2630→:2646, :2638→:2654, :2619→:2635, :1963→:1979, :1974→:1990). Re-read anchors at ad4dbc62 before editing; the token text itself is unchanged.
- The "04h worktree has no `.venv`" parentheticals are stale (it now has one); cosmetic.
- **Constraint 9 addendum (blocking item 1 of the re-check):** `workflow.classifier-axis-enforcement` (suites.toml :2635 at ad4dbc62) and `workflow.dag-tick-wiring` (:1990) bind TEST-file tokens. Keep `tests/test_dag_tick.py:37` (`from dotfiles_setup import classifier_tables, codex_verdict, dag_tick`) and `tests/test_codex_verdict.py:24` (`from dotfiles_setup import classifier_tables`) byte-identical; add any new `dotfiles_setup` import on a SEPARATE `from dotfiles_setup import …` line; spell V-a3's six git-context names as literals; do not reuse or redefine any bound test name or `_AXIS_VALUES`. Also keep `'is not Edge.ADVANCE'`, `'def edge_for('`, `'def demands_rework('`, `'def parse_verdict('` exactly once in codex_verdict.py.
- Non-blocking: `codex_lane.py:6` "maps ten outcomes" prose is stale after LOCK_BUSY (outside allowlist) — name it in the PR body for a follow-up.
