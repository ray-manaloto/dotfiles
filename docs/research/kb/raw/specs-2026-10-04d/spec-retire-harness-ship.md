# SPEC — retire refuses live `harness-output:` runs; the successor settles the whole ship wrapper

Status: DRAFT by spec-scribe, 2026-10-04. Not ratified as a spec, not dispatched. The
proposals it implements were ratified; the open choices in §8 still need the architect.
Ratified scope: Ray 2026-10-04, proposals **1** and **3** of
`docs/research/kb/reports/agents/sdlc-team-review-retire-vs-harness-ship-0ca4b234.md:59-88`.
Proposal 2 (clean, default-branch checkout gate) is **out of scope**.

Memory: the spec-scribe local memory directory was empty, so there was nothing to apply. I
wrote no memory update because the caller said "Write nothing inside any repo checkout", and
`.claude/agent-memory-local/` sits inside the worktree.

**Provenance caveat (read before dispatch).** This lane has no shell, so I could not run
`git show origin/main:<path>`. Every `file:line` below comes from the **working tree of
`.claude/worktrees/handoff-2026-10-04c`**:

- Its HEAD is `a39cbc3e`, one commit on `abf75906` with the subject `docs(handoff): session
  2026-10-04c …` (`.git/worktrees/handoff-2026-10-04c/logs/HEAD:5`).
- `refs/remotes/origin/main` = `abf75906` (`.git/refs/remotes/origin/main:1`).
- The handoff doc also carries edits newer than that commit (§ "Successor review and
  corrections", `docs/handoffs/session-2026-10-04c.md:120`), so the tree is not pristine.

Before dispatch, the coordinator must confirm that this prints nothing:
`git diff --stat origin/main -- python/src/dotfiles_setup/coordinator_handoff.py tests/test_coordinator_handoff.py .claude/skills/coordinator-handoff/SKILL.md .agents/skills/coordinator-handoff/SKILL.md docs/specs/coordinator-auto-handoff-2026-10-02.md`.
If it prints anything, re-anchor every row of §7.

---

## 1. Objective

**Ratified wording (load-bearing, verbatim from the coordinator's brief of Ray's ruling):**

> **P1:** a matching live `harness-output:` census entry is NON-ADOPTABLE. `retire` must
> refuse it with zero stop calls under every override combination (`--adopted`,
> `--accept-inflight`, tasks=0). Ordinary detached-run adoption and completed wrappers with
> cleared counters still pass. Include a case where the inner ship exited but the outer
> wrapper is alive. The protected-adoption assertions must FAIL against today's predicate.
>
> **P3:** the generated successor brief (`coordinator_handoff.py` ~:704-718) and
> `.claude/skills/coordinator-handoff/SKILL.md` must require waiting for the whole user ship
> wrapper; then verify the ship outcome, the branch restoration and the push/PR result;
> distinguish completed-result adoption from active-process adoption; and note that with
> `mise run ship; git switch main`, a successful restore can mask ship failure as the final
> status. Brief assertions must fail if those requirements are removed.

**What this prevents.** Today a successor can stop the old coordinator while that
coordinator's harness task is still running Ray's ship:

- **The route.** It passes `--adopted <pid>` plus either `--accept-inflight` or a zero
  `inFlight.tasks`. Adoption alone removes a run from `blocking`
  (`coordinator_handoff.py:1120-1124`), and the counter gate is independent of it
  (`:1061-1078`). Today's test asserts exactly that pass (`tests/test_coordinator_handoff.py:640-647`).
- **The live case.** The recorded census has the ship as a `harness-output:` wrapper (pid
  30424, `.agent/state/coordinator-handoff/1debf341-07f6-423c-a932-1dd292874f66.json:13-16`).
  Its argv chains `mise run ship; git switch main`.
- **The settlement gap.** The current brief tells the successor to "adopt its result
  explicitly" (`coordinator_handoff.py:704-710`). It never asks for the ship outcome or the
  branch restoration to be checked. And the wrapper's final status is that of `git switch`,
  not of the ship.

**Outcome.**

1. `retire` returns BLOCKED with zero `claude stop` calls while any matching live
   `harness-output:` run exists, whatever flags and counters are given.
2. The brief and the skill tell the successor to wait for the whole wrapper, then verify
   three things from evidence: the ship outcome, the branch restoration and the PR state.

## 2. Files

Implementation worktree: `<main>/.claude/worktrees/retire-harness-ship`. Branch: see §8 Q3.
Never the main checkout. Allowlist (modify only these):

| Path | Change |
|---|---|
| `python/src/dotfiles_setup/coordinator_handoff.py` | prefix constant; `_adoptable`; retire predicate, logs and remedies; retire docstring; brief run-line suffix; brief steps 3 and 4 |
| `tests/test_coordinator_handoff.py` | new arms in §5.1; edit no existing expected value except where §4 names it |
| `.claude/skills/coordinator-handoff/SKILL.md` | settlement paragraph (§3.4) |
| `.agents/skills/coordinator-handoff/SKILL.md` | **generated** only, by `mise run skills-mirror` (bare form writes, `mise.toml:1389-1392`). Never hand-edit it |
| `docs/specs/coordinator-auto-handoff-2026-10-02.md` | the §3.5 edits: three in-place edits and a new §12 |

**Not to touch:**

- `docs/specs/coordinator-auto-handoff-2026-10-02-requirements.md`. It is tracked verbatim (spec `:45-47`).
- Any `docs/handoffs/*`.
- The real state dir `.agent/state/coordinator-handoff/`.
- `.claude/settings.json`.

## 3. Interfaces

### 3.1 Constant and predicate (`coordinator_handoff.py`)

```python
HARNESS_OUTPUT_PREFIX = "harness-output:"   # module constant, beside the other constants

def _adoptable(run: HeavyRun) -> bool:
    """A live harness-output run is never adoptable (P1, Ray 2026-10-04).

    Its stdout is a harness task file, so nothing durable records its rc; and the recorded
    pid is the user's whole wrapper (e.g. `mise run ship; git switch main`), whose exit is
    the only settlement signal.
    """
    return not (run.log_path or "").startswith(HARNESS_OUTPUT_PREFIX)
```

- `stdout_log` (`:499`) and `successor_brief` (`:654`) use `HARNESS_OUTPUT_PREFIX`
  instead of the literal. No other literal changes.
- `_recorded_runs` (`:1034-1048`) is unchanged. The prefix is read from the census
  `log_path` that launch recorded. It is not re-probed at retire.

### 3.2 `retire` (`:1081-1154`)

Signature, `RetireRequest`, `RetireDeps`, CLI flags (`:1229-1239`) and rc codes are all
unchanged. The predicate becomes:

```python
blocking = tuple(
    run for run in runs
    if commands.get(run.pid) == run.argv
    and (run.pid not in request.adopted or not _adoptable(run))
)
```

- A blocking run that is non-adoptable and in `request.adopted` logs one ERROR line, of the
  form `coordinator-handoff retire: adopted pid %d ignored — harness-output run is not
  adoptable; wait for the wrapper pid to exit`. The pid is the argument. Do not spell the
  flag as `--adopted` in that line (see §5.1 T5).
- Remedies (`:1135-1141`):
  - Keep `"wait for each run or pass --adopted PID"`, but only when at least one blocking
    run is adoptable.
  - Add `"wait for each harness-output wrapper pid to exit (not adoptable)"` when at least
    one blocking run is non-adoptable.
- The rc for this block is **1** (BLOCKED); see §8 Q1. The decision is still made before
  dry-run and before `_stop` (`:1148-1154`), so zero stop calls holds by construction.
- Update the docstring (`:1082-1090`) to state the third blocker: a matching live
  harness-output run blocks even when adopted, and no flag overrides it.
- `_in_flight_blocks` (`:1061-1078`) is unchanged.

### 3.3 Brief (`successor_brief`, `:645-723`)

**Run-line suffix (`:650-656`).** Keep `" — no rc file — wait on pid exit"` for both
`None` and harness-output. Append `" (not adoptable)"` for harness-output only. The
existing asserts at `tests/…:1367` and `:1675` must stay green.

**Step 3 (`:704-710`).** Replace it with text carrying **every** token in the table below,
byte-exact (tests bind to them):

| Req | Required token(s) in the brief |
|---|---|
| R1 whole wrapper | `wait for the WHOLE wrapper pid to exit, not just the inner` |
| R2 three checks | `verify the ship outcome`, `the branch restoration`, `the push/PR result` |
| R2 evidence | `ship: OK — PR #` (`pr.py:764`) and `gh pr view` |
| R3 two adoptions | `COMPLETED-RESULT adoption`, `ACTIVE-PROCESS adoption` |
| R4 masking | `` `mise run ship; git switch main` `` and `a successful restore can mask a failed ship` |
| R5 P1 mirror | `` `harness-output:` `` + `NOT adoptable` |

Suggested wording. The implementer may reflow the lines but must keep the tokens verbatim.
No token may span a newline in the **generated** brief. Mind the `\` continuations in the
f-string: a token broken across a real newline fails T6.

```text
3. Settle each recorded heavy run before retire. There are two kinds of adoption:
   - COMPLETED-RESULT adoption: the run has exited; read its result and own the
     outcome. No flag is needed — an exited pid never blocks retire.
   - ACTIVE-PROCESS adoption (`--adopted PID`): the run is still alive and you take
     over waiting on its rc log after retire. Only a run with a resolved rc log
     qualifies.
   A log with an rc line: `mise run bounded-wait` on that rc line. A log marked
   `unexpanded:` is unresolved redirect text: find its real path first; never wait
   on a literal `$LOG` or an absent log.
   A log marked `harness-output:` has no rc file and is NOT adoptable while live —
   retire refuses it under every override. wait for the WHOLE wrapper pid to exit, not just the inner
   `mise run ship`; then verify the ship outcome (its output carries
   `ship: OK — PR #<n> open`), the branch restoration (the main checkout is back on
   the branch the wrapper restores), and the push/PR result (`gh pr view <branch>
   --json number,state,autoMergeRequest`), from evidence, never from the task's
   exit status: with `mise run ship; git switch main` the final status is the
   `git switch`'s, so a successful restore can mask a failed ship.
   With no log, wait on pid exit, then verify the same way when it was a ship.
```

(The lowercase `wait` that opens the R1 sentence is deliberate. It makes the R1 token an
exact substring.)

**Step 4 (`:711-720`).** Change "It blocks (rc 1) while a recorded run is live and
unadopted" to cover the new blocker. It should read: live and unadopted; or a live
`harness-output:` run, which no flag overrides; or harness tasks in flight or unknown
(`--accept-inflight` overrides only that). The rc legend is unchanged.

### 3.4 Skill (`.claude/skills/coordinator-handoff/SKILL.md`)

Extend the paragraph at `:100-102`, or add one under §3 (`:104-109`). It must carry these
tokens:

- `NOT adoptable`
- `wait for the WHOLE wrapper pid to exit`
- `verify the ship outcome`
- `the branch restoration`
- `the push/PR result`
- `COMPLETED-RESULT adoption`
- `ACTIVE-PROCESS adoption`
- `` `mise run ship; git switch main` ``
- `a successful restore can mask a failed ship`

**Do not write the word `Claude`.** The mirror rewrites `Claude` → `Codex`
(`skills_mirror.py:122-136`); write "the harness", or lowercase `claude stop`, which is not
rewritten. Then run `mise run skills-mirror` (bare).

### 3.5 Spec doc (`docs/specs/coordinator-auto-handoff-2026-10-02.md`)

1. In §3c (`:190-194`), extend the rc 1 definition with the live `harness-output:` blocker,
   which no flag overrides.
2. In §3e (`:262-266`), replace "or adopt its result explicitly" with the two adoption kinds
   and the whole-wrapper wait plus the three checks.
3. In §5.4 (`:309-312`, retire arms), add: "a live `harness-output:` run blocks even with
   `--adopted` + `--accept-inflight` + tasks=0".
4. Append `## 12. Retire vs harness ship — P1 + P3 (Ray, 2026-10-04)` **before**
   `## GitHub repos touched` (`:543`). It quotes §1's ratified block, cites the report path,
   and lists the §8 rulings once they are made.

## 4. Constraints and invariants

- **Ratified scope only.** Add no new override flag and no Git-state check (P2 is
  rejected/deferred). The only way past the new blocker is the wrapper exiting.
- **Unchanged behaviour (regression arms in §5.1):**
  - Ordinary adoption still works for a `log_path` that is a real file, `unexpanded:`, or
    `None`. Examples are `tests/…:621-652`, and the census row for pid 19009, a redirect
    log (`…1debf341….json:3-7`).
  - PID reuse never blocks (`tests/…:656-660`).
  - Blocking on in-flight tasks alone is unchanged (`tests/…:663-693`, `:1469-1480`).
- **Known residuals.** List these in the commit body and in spec §12 rather than fixing them:
  - A task whose stdout was redirected stays adoptable. The heuristic is stdout provenance
    only (report `:65-66`).
  - Changes of argv or identity, and observation races, remain (report `:52-57`).
- **No new expected values for old tests.** The single exception is
  `test_retire_blocks_on_a_live_recorded_run_until_it_exits`, which stays as it is: its log
  is a real redirect, so its adoption arm (`:640-647`) must still return 0.
- **Tests go through the public surface only:** `ch.retire` with `RetireDeps` injection,
  `ch.launch(dry_run=True)` for the brief, and `ch.main` with `--dry-run` for the CLI.
  - The process table and `lsof` are the only injected boundaries (`tests/AGENTS.md`
    § Mocking).
  - A CLI arm must always pass `--dry-run`. `_retire_main` takes a real `reap.snapshot()`
    and has no runner seam (`:1319-1334`), so a wrong pass without `--dry-run` would call
    the real `claude stop`.
- **Implementer lane, codex (`codex-sol-implementer`, effort `xhigh`).** The PreToolUse
  guard does not see a codex lane, so these prohibitions bind by this spec alone:
  - It runs **no** pytest, lint, verify, lint-docs, `claude`, `gh`, `kill`, `git push`,
    `mise run ship`, or anything under the main checkout.
  - It may run `uv run --project python ruff format`/`ruff check` on the files it touched,
    and `mise run skills-mirror` (bare).
  - It must not read, signal or probe pid 30424, or any process it did not start in a test.
  - It must not edit outside the §2 allowlist.
- **Gates.** The coordinator runs them under the host slot, in order. Each rc is
  file-captured or comes from `mise run gate` (§5).
- **Safety gate.** This touches a process-lifecycle safety gate, so per `codex-sdlc-team`
  § The spec contract, run `premise-verifier` over §7 before dispatch.
- **Zero inline suppressions; zero bash logic.** Tests shell out only to `/bin/sh` and
  `sleep`, as the existing real-process arm does (`tests/…:626-629`).

## 5. Verification

### 5.1 New test arms (in `tests/test_coordinator_handoff.py`)

Use the existing helpers:

- `_record_launch` (`:570-583`)
- `_retire` (`:586-600`)
- `_job` (`:45-62`)
- `_proc` (`:334-335`)
- `_Recorder`, which records every non-git, non-lsof call (`:436-456`)
- `_wait_for` (`:603-610`)
- `_deps` (`:459-477`)

**T1 — `test_p1_live_harness_output_wrapper_is_never_adoptable`**

- **Parametrize** over three axes, 2×2×3 = 12 cells, and two shapes, 24 cases in all:
  - `adopted` ∈ {∅, {300}}
  - `accept_inflight` ∈ {False, True}
  - `in_flight` ∈ {`{"tasks": 0}`, `{"tasks": 2}`, `"garbage"`}
  - shape `inner-alive`: `_proc(300,100,W)` + `_proc(301,300,"mise run ship")`
  - shape `inner-exited`: `_proc(300,100,W)` only, so the outer wrapper is alive while
    the inner ship has exited
- `W = "/bin/zsh -c mise run ship; git switch main"`. The census row is
  `HeavyRun(300, W, "harness-output:/tmp/x/tasks/b.output")`.
- Call it with `RetireRequest(SESSION, adopted=…, accept_inflight=…, dry_run=False)` and
  `runner=_Recorder(0)`.
- **Expect** rc **1** and `runner.calls == []`. When `adopted` is non-empty, `"not adoptable"`
  must appear in caplog.
- **Against today's predicate**, the cells with `adopted={300}` and (`tasks=0`, or
  `accept_inflight=True`) return 0 with one stop call. That is 4 cells per shape, 8 in all.
  These are the protected-adoption assertions that must FAIL on `abf75906`.

**T2 — `test_p1_real_wrapper_blocks_until_it_exits` (a real process)**

1. Start `subprocess.Popen(["/bin/sh","-c",": mise run ship; sleep 30"], start_new_session=True)`.
   The no-op `: mise run ship` has already "finished", so the live process is the wrapper alone.
2. Wait until its pid is in `reap.snapshot()`. Record
   `HeavyRun(pid, <that snapshot row's command>, f"harness-output:{tmp_path}/tasks/b.output")`.
3. With `_job(in_flight={"tasks": 0})`, `adopted={pid}`, `accept_inflight=True`,
   `dry_run=False` and `_Recorder(0)`, expect rc 1 and zero calls.
4. Run the same request through the CLI: `ch.main` with `retire --old-session SESSION
   --adopted <pid> --accept-inflight --dry-run --jobs-dir … --state-dir …`. Expect rc 1.
5. In `finally`, call `os.killpg` and then `wait`.
6. Wait until the pid has gone. Then call `_retire` with no flags, tasks 0, `dry_run=False`
   and `_Recorder(0)`. Expect rc 0 and exactly one call, `["claude","stop",SESSION[:8]]`.
   This proves that a completed wrapper with cleared counters passes.

**T3 — `test_p1_ordinary_adoption_still_passes`**

- Parametrize the live run's `log_path` over `"/logs/ship.log"`, `"unexpanded:$LOG"` and `None`.
- The process table is a matching `_proc`, the census adopts the run, tasks are 0,
  `dry_run=False`, and the runner is `_Recorder(0)`.
- Expect rc 0 and one stop call. **Control arm:** the same run without `adopted` returns
  rc 1 with zero calls.

**T4 — `test_p1_completed_harness_wrapper_with_cleared_counters_passes`**

- The census holds a harness-output run, its pid is absent from the table, and tasks are 0.
  Expect rc 0 with one stop call.
- **Control arm:** the same with `{"tasks": 2}` and no accept returns rc 1 with zero calls.

**T5 — `test_p1_refusal_names_waiting_not_adoption`**

- Only a non-adoptable run blocks, and it is adopted.
- Expect `"not adoptable"` in caplog and `"pass --adopted PID"` absent from caplog.
- Mirror shape: `:1469-1480`.

**T6 — `test_p3_brief_requires_whole_wrapper_settlement`**

- Generate the brief through `ch.launch(handoff, SESSION, dry_run=True, deps=…)` and read it
  as `argv[6]` of the printed JSON. This is the same route as `:493-506`.
- Pass a runner whose `lsof` returns a `tasks/*.output` path for the heavy pid, the shape
  of `:1344-1346`, so the census row is `harness-output:`.
- **Parametrize over every token in §3.3's table**, one case per token, so a removed
  requirement fails its own named case.
- Also assert that the run line carries `(not adoptable)`.

**T7 — `test_p3_skill_carries_settlement_contract`**

- Parametrize over the §3.4 tokens against `.claude/skills/coordinator-handoff/SKILL.md`,
  in the shape of `:1483-1498`.
- Assert `"Claude"` not in the new paragraph. Locate the paragraph by its first token and
  read up to the next blank line.

### 5.2 Mutation (FAIL) arms. The coordinator runs them after `git add` of the lane's diff

Stage first: `git checkout -- <file>` restores from the index, so staging is what makes
the undo safe.

| Arm | Mutation | Must fail |
|---|---|---|
| M1 | Restore the exact prior predicate `commands.get(run.pid) == run.argv and run.pid not in request.adopted`. Take it from `git show origin/main:python/src/dotfiles_setup/coordinator_handoff.py`, `:1123` | The 8 T1 cells named above, plus T2 step 3. T3 and T4 stay green |
| M2 | Delete the R1 sentence from the brief | That T6 case only |
| M3 | Delete the R4 masking clause from the brief | That T6 case only |
| M4 | Delete the R3 two-adoption bullets from the brief | Those T6 cases |
| M5 | Delete the settlement paragraph from SKILL.md | T7 |

After each arm, run `git checkout -- <file>`, then rerun T1 to T7 green.

### 5.3 Gate bundle (coordinator, host slot, each rc read from the artifact)

1. `uv run --project python pytest tests/test_coordinator_handoff.py -x -q > $LOG 2>&1; echo "rc=$?" >> $LOG`
2. The M1 to M5 arms (§5.2).
3. Then each of:
   - `mise run gate -- run lint` (includes `skills_mirror_parity`, `hk.pkl:733-735`)
   - `mise run gate -- run pytest`
   - `mise run gate -- run verify`
   - `mise run gate -- run lint-docs`
4. Cold review by ref. The diff is codex-authored, so the reviewer is Opus `cold-reviewer`.

## 6. Commit

One commit. Owner: see §8 Q2 (recommended: `caller`).

Subject: `fix(coordinator-handoff): live harness-output runs are never adoptable; successor
settles the whole ship wrapper`.

The body:

- cites the report path and Ray's 2026-10-04 ratification of P1 and P3;
- lists the §4 known residuals;
- states that P2 is not implemented.

It ends with the session's attribution trailers. No push and no ship from the lane; the
coordinator ships.

## 7. PREMISES

Every row was read by me in this run, in the handoff-2026-10-04c worktree unless the path
says otherwise. Paths are relative to that worktree. See the provenance caveat at the top:
these rows are worktree reads, **not** `git show origin/main` reads.

| # | Kind | Premise | Citation |
|---|---|---|---|
| 1 | L | origin/main = `abf75906c52b…` | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.git/refs/remotes/origin/main:1` |
| 2 | L | The worktree HEAD is a single `docs(handoff)` commit `a39cbc3e` on `abf75906` | `…/.git/worktrees/handoff-2026-10-04c/logs/HEAD:1,5` |
| 3 | L | Ratified proposals P1 and P3, their files and their tests | `docs/research/kb/reports/agents/sdlc-team-review-retire-vs-harness-ship-0ca4b234.md:61-88` |
| 4 | L | Prefix literal `f"harness-output:{path}"`, set when fd 1 is a `tasks/*.output` file | `python/src/dotfiles_setup/coordinator_handoff.py:495-500` |
| 5 | I | `census` records only the OUTERMOST heavy pid of a chain | `coordinator_handoff.py:585-624` |
| 6 | L | The brief suffix treats `None` and harness-output alike: "no rc file — wait on pid exit" | `coordinator_handoff.py:650-656` |
| 7 | L | Current step 3 says "adopt its result explicitly"; harness-output says "wait on pid exit" | `coordinator_handoff.py:704-710` |
| 8 | L | Current step 4 blocker sentence and rc legend | `coordinator_handoff.py:711-720` |
| 9 | I | Today's predicate is `commands.get(run.pid) == run.argv and run.pid not in request.adopted` | `coordinator_handoff.py:1119-1124` |
| 10 | I | The in-flight gate is independent; accept overrides positive or unknown counts | `coordinator_handoff.py:1061-1078` |
| 11 | L | Remedy text `"wait for each run or pass --adopted PID"` | `coordinator_handoff.py:1137` |
| 12 | I | Blocking returns 1 before dry-run and `_stop`; `_stop` calls `["claude","stop",short_id]` | `coordinator_handoff.py:1134-1170` |
| 13 | I | The CLI retire path takes a real `reap.snapshot()` and has no runner seam | `coordinator_handoff.py:1319-1334` |
| 14 | I | `--adopted` is `type=int, nargs="*"` | `coordinator_handoff.py:1233` |
| 15 | I | `launch(dry_run=True)` writes the argv JSON and the brief, then records nothing | `coordinator_handoff.py:897-914` |
| 16 | P | Today's test asserts that adoption passes (rc 0) for a live run | `tests/test_coordinator_handoff.py:640-647` |
| 17 | P | Existing asserts on `"no rc file — wait on pid exit"` | `tests/test_coordinator_handoff.py:1367`, `:1675` |
| 18 | P | The in-flight-only block must not name `--adopted` | `tests/test_coordinator_handoff.py:1469-1480` |
| 19 | P | `_Recorder` records `claude` calls and fakes `lsof` as rc 1 | `tests/test_coordinator_handoff.py:436-456` |
| 20 | P | A brief via launch dry-run is read as `argv[6]` | `tests/test_coordinator_handoff.py:493-506` |
| 21 | P | A harness-output census arm uses an injected `lsof` | `tests/test_coordinator_handoff.py:1338-1367` |
| 22 | P | A CLI retire arm uses `ch.main` with `--dry-run` | `tests/test_coordinator_handoff.py:846-857` |
| 23 | P | A skill-content assert precedent | `tests/test_coordinator_handoff.py:1483-1498` |
| 24 | L | The live census row is pid 30424 with a `harness-output:` log; its argv ends `mise run ship; git switch main` | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/state/coordinator-handoff/1debf341-07f6-423c-a932-1dd292874f66.json:13-16` |
| 25 | L | Ordinary waits are recorded with real redirect logs (pid 19009) | same file `:3-7` |
| 26 | L | The ship success line `ship: OK — PR #{number} open, local gates green, AUTO-MERGE enabled.` | `python/src/dotfiles_setup/pr.py:764` |
| 27 | L | The skill already says "Harness logs marked `harness-output:` have no rc file; wait on pid exit." | `.claude/skills/coordinator-handoff/SKILL.md:100` |
| 28 | L | The mirror copy exists with the same line | `.agents/skills/coordinator-handoff/SKILL.md:100` (Grep hit) |
| 29 | L | The mirror rewrites `Claude` → `Codex` | `python/src/dotfiles_setup/skills_mirror.py:122-136` |
| 30 | L | `skills_mirror_parity` runs in lint; the `skills-mirror` bare form writes | `hk.pkl:733-735`; `mise.toml:1389-1392` |
| 31 | L | The auto-handoff spec describes adoption at §3c, §3e and §5.4, and ends with `## GitHub repos touched` | `docs/specs/coordinator-auto-handoff-2026-10-02.md:190-194, 262-266, 309-312, 543` |
| 32 | L | The requirements doc is tracked verbatim, so it is not edited | `docs/specs/coordinator-auto-handoff-2026-10-02.md:45-47` |
| 33 | A | **The worktree files equal their `origin/main` blobs.** UNVERIFIED: this lane has no shell, so it cannot run `git show`/`git diff`. The top-of-file command settles it | — |
| 34 | A | **The in-flight ship branch `fix/coordinator-bgisolation-none` also edits `coordinator_handoff.py`.** Its commit `abc117c6` is titled "launch successors with worktree.bgIsolation none". That would move the line anchors around `launch_argv` (`:726-728`) and maybe the launch tests. This comes from the session's git-status snapshot, not from a file I read. UNVERIFIED | — |
| 35 | A | **The user `!` task's process is the recorded wrapper pid**, and it outlives `claude stop`. The report marks the `!` case "unproven" (`…0ca4b234.md:19`, `:46`). P1 does not depend on it: it blocks while the pid is live, however long that is | — |

## 8. Open choices for the architect (stop for ratification)

**Q1 — rc for a non-adoptable block.**

- **Recommended: 1 (BLOCKED).** The blocker is live work, and the remedy is to wait.
  - PRO: it matches the existing rc 1 meaning (spec `:190-194`), and no consumer changes.
  - CON: an `--adopted` the operator passed on purpose is silently downgraded. The ERROR
    line is the only signal.
- **Alternative: 2 (refused).**
  - PRO: it is loud.
  - CON: rc 2 means invalid input or state (`coordinator_handoff.py:1088-1089`); a valid
    pid is neither.

**Q2 — commit owner.**

- **Recommended: `caller`.** The coordinator commits after §5.2/§5.3.
  - PRO: the mutation arms need the diff staged, not committed.
  - CON: one more coordinator step.
- **Alternative: `lane`.**
  - PRO: the default.
  - CON: the mutation arms then have to be run against a commit.

**Q3 — branch and base.**

- **Recommended:** branch `fix/retire-harness-ship`, cut **after** the bgisolation PR
  merges, from the new origin/main, then re-anchor §7.
  - PRO: no conflict in `coordinator_handoff.py`.
  - CON: it waits on pid 30424's ship.
- **Alternative:** cut from `abf75906` now.
  - CON: a likely conflict (§7 row 34).

**Q4 — whether the brief says what to do when the ship or the restore failed.**

- **Recommended:** add "report it to Ray; do not switch the branch yourself".
  - PRO: it matches the successor-review correction F1 (`docs/handoffs/session-2026-10-04c.md:126-130`).
  - CON: that text is a successor correction, not a Ray ratification, and it narrows the
    AUTONOMY rule (`coordinator_handoff.py:680-682`).
- **Alternative:** leave the remedy to the successor's judgement.

## §8 RULINGS (coordinator e67105a8, 2026-10-04)

- **Q1:** rc 1 (BLOCKED) when `--adopted` names a live `harness-output:` run.
- **Q2:** commit mode `caller`.
- **Q3:** branch `fix/retire-harness-ship`, cut from origin/main AFTER the bgisolation PR merges.
- **Q4:** "report it to Ray; do not switch the branch yourself".
- **Row 34 CONFIRMED (blocking for the line numbers):** `git diff --stat origin/main fix/coordinator-bgisolation-none` touches every file this spec edits, except the `.agents` mirror: `coordinator_handoff.py` (+/-40), `tests/test_coordinator_handoff.py` (+24), the `.claude` skill (+7) and the auto-handoff spec (2). After bgisolation merges, re-derive EVERY file:line in this spec against the new origin/main, then run premise-verifier, and only then dispatch.
- **Row 33:** settled by the same re-derivation.
