# Cold review — df481e1f (vs parent 589dc90e)

- Subject: `df481e1ff304aff21177894c51617e506eacb8e7` "fix(coordinator-handoff): review round-1 corrections R1-R14"
- Base: `589dc90e1a519e6cfed4002067d75950d9efc5f3` (= `df481e1f^`, checked with `git rev-parse`)
- Diff: 19 files, +1708 / -351 (`git diff 589dc90e df481e1f`)
- Author family: codex (gpt-5.6-sol). Reviewer: Claude Opus (cold, diff-only)
- Constraints: read-only. I ran no tests, bun, tsc, lint or gate (the caller's host slot discipline). Runtime claims come from reading the source plus three cheap read-only probes (`lsof`/`ps` of my own Bash-tool shells), and are labelled UNVERIFIED where execution would be needed.
- Memory: `.claude/agent-memory-local/cold-reviewer/` was empty at start, so there were no prior patterns.
- Brief shape: a round-1 open hunt (adversarial-review skill). It cannot end the loop by outcome; Q-FRESH, Q-SCOPE and Q-CLAIM are answered below.

## Status

COMPLETE — 18 findings: 3 HIGH, 1 MEDIUM, 14 LOW.

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| 1 | HIGH | PROBE mode now re-fires `/coordinator-handoff --probe` after every turn that ends at or above the limit, and the loop sustains itself. PROBE passes `--no-commit`, so no level is ever recorded. Each probe reply is a turn, that turn triggers the next `session.measure`, and the next measurement fires again. At 589dc90e the probe consumed the level, so it fired once per step. | `.claude/skills/coordinator-handoff/hooks/register.ts:196-199,209,233`; `python/src/dotfiles_setup/coordinator_handoff.py:225-235` | `noCommit = probe \|\| dryRun` (register.ts:198). `_judge` skips the `last_fired` write when `no_commit` (py:232-234), so `threshold` stays at `limit` and every measurement ≥ limit returns `fire:true`. The non-dry-run path then calls `$.command.run({command, args:"--probe"})` (register.ts:233). `session.measure` fires "After each turn" (KB `claude-code-docs/plugins__mods__reference.md:111`). The harness PROBE arm measures only once (`tests/fixtures/coordinator_handoff_hook/harness.ts:300-309`), so this loop has no arm. Runtime loop is UNVERIFIED (I did not execute it); the code path is read directly. |
| 2 | HIGH | A failed successor start disables the handoff permanently, with no successor and no recovery verb. `launch` writes the terminal `launch` record before `claude --bg` and never rolls it back, whether `claude --bg` exits nonzero or is missing (FileNotFoundError, caught, rc 2). After that, `decide` answers `already-launched` forever, `launch` refuses, and `release` refuses. The status line then reads "handoff already launched" although nothing launched. This contradicts spec R1: "Stepped re-fire stays only for a handoff that never launched." | `coordinator_handoff.py:689-698` (record, then `runner(argv)`); `:649-651` (OSError → rc 2 after the write); `:223-224`; `:310`; `:632-642`; `register.ts:154-155`; `.claude/skills/coordinator-handoff/SKILL.md:60-62` | `write_state(path, state)  # state before signal` precedes `runner(argv, cwd=checkout, check=False)` with no rc check or rollback. `_judge` returns `already-launched` on `"launch" in state`. `release` acts only `if "launch" not in state`. The SKILL treats rc 2 as a "refusal" and says to "stop". The spec R1 text is at `docs/specs/coordinator-auto-handoff-2026-10-02.md` §9 R1. Before this commit, `decide` ignored `launch`, so a failed start re-fired at the next step. `test_r1_*` (`tests/test_coordinator_handoff.py:774`) arms only a successful launch. |
| 3 | HIGH | R9 records the wrong log for every heavy run launched through the Bash tool. It records Claude Code's task `.output` file instead of the run's `$LOG`. The outermost heavy match is the tool's own zsh wrapper, because its argv contains the whole command, and that zsh's fd 1 is the harness `.output` regular file, so `stdout_log(outer)` wins. For the canonical `mise run X > "$LOG" 2>&1; echo "rc=$?" >> "$LOG"`, the rc line is never in that file. The brief nevertheless tells the successor to `bounded-wait` on "its resolved log's rc line", and the path is not marked `unexpanded:`, so it looks trustworthy. The code follows spec R9 literally, which means the spec's premise is wrong. | `coordinator_handoff.py:426-436` (outer fd 1 first, first-descendant fallback only when that is not a regular file); `:370-390`; `:512-515` (brief); test codifying it: `tests/test_coordinator_handoff.py:1066-1088` (owner=300 is the zsh) | PROBED with both arms. In a background Bash task, `sleep 3 > /tmp/…child.log &` gave **child** fd1 = `/tmp/cold-review-child-df481e1f.log` and **parent zsh** fd1 = `/private/tmp/claude-501/<proj>/<session>/tasks/bz20xhv5a.output`. In a foreground Bash call, the zsh's fd1 was also a `tasks/<id>.output` regular file. Non-tty `ps -eo pid=,args=` shows that zsh's full 987-char argv including the user command tail, and `reap.PS_COMMAND` (`reap.py:70`) is that same non-tty form, so `HEAVY_COMMAND_RE` matches the wrapper and the wrapper is the outermost match. Retire's liveness gate (pid+argv) is unaffected; only the successor's wait/adopt instructions point at the wrong file. |
| 4 | MEDIUM | The R4 role cache is permanent for the module's lifetime. One `not-coordinator` answer disables the handoff for that session until a plugin reload. That answer can come from a transient job-record read (the record is missing, partially written, or has a mismatched id; every doubt maps to `None` → not a coordinator) or from a session renamed to `…coordinator` after its first measurement. 589dc90e re-read the name on every measurement above the limit, so it recovered by itself. The only visible signal is the status text `handoff n/a (not coordinator)`, which an unattended coordinator never surfaces. | `register.ts:186-189,204`; `session_common.py:54-76` | `roles.set(sessionId,"not")` happens on the first `not-coordinator` and is never cleared. `read_json` maps OSError/ValueError to `None` and `session_name` maps that to `None`. The live job records (`~/.claude/jobs/*/state.json`, read with jq, counts only) carry a changing `inFlight` block, so the harness rewrites them during a session. Whether those writes are atomic is UNVERIFIED. The behaviour is prescribed by spec R4 ("NO process ever again"), so the fix is a respec, for example not caching a `not` whose cause was a missing or unreadable record. |
| 5 | LOW | Every session in every worktree now spawns one `uv run … decide` on its first measurement, even at 1%. Each one writes `<id>.json` and `<id>.json.lock` into the main checkout's `.agent/state/coordinator-handoff/`, for lanes and non-coordinators too. Nothing prunes them. At 589dc90e, sessions below the limit ran no process. | `register.ts:186-199`; `coordinator_handoff.py:272-281`; `session_common.py:115-117` | `decide` takes the lock and writes `last_seen` before `_judge` decides `not-coordinator`. `state_lock` creates the `.lock` file. |
| 6 | LOW | DRY_RUN now toasts and logs on every turn at or above the limit, not once per step. It uses the non-consuming preview and the raw `$.ui.toast`, not `toastOnce`. | `register.ts:216-221` | Same `noCommit` mechanism as #1, but with no `command.run`, so there is no loop: noise only. |
| 7 | LOW | `launch` holds the state flock across `claude --bg`, which has no timeout. A hung start holds the lock until the Bash tool kills the process, and any `decide` for that session times out to `state-locked` in the meantime. | `coordinator_handoff.py:630-648,697-698` | `runner(argv, cwd=checkout, check=False)` runs inside `with state_lock(path)` with no `timeout=`. |
| 8 | LOW | A non-UTF-8 handoff file escapes R6's code contract and returns traceback rc 1. `handoff.read_text` raises UnicodeDecodeError (a ValueError), which neither `_gather` nor `launch` catches. | `coordinator_handoff.py:574-581,649` | Both except lists cover CoordinatorHandoffError, ReapError, OSError and TimeoutExpired only. |
| 9 | LOW | The SKILL §2 census list is stale. It names 7 tasks; R8's regex covers 15 (it is missing dev-rebuild, up, persistence, gate, lock-image, lock-shared, verify-container-latest and automerge). | `.claude/skills/coordinator-handoff/SKILL.md:55-56` (same text in `.agents/…:55-56`) | Compare `HEAVY_COMMAND_RE`, `coordinator_handoff.py:105-113`. |
| 10 | LOW | Spec §3c lists git failure under `census-unavailable`, but the code logs it as a generic "launch refused" with a traceback, because `main_checkout` runs before and outside `_gather`. | `docs/specs/coordinator-auto-handoff-2026-10-02.md:178-179`; `coordinator_handoff.py:624-627,649-651` | The rc (2) is right; only the operator-facing reason text differs. |
| 11 | LOW | `release` logs "invalid-percent" when it rejects an invalid **level**. | `coordinator_handoff.py:301-304` | Message literal. |
| 12 | LOW | When only inFlight blocks, which R7 now includes for *unknown*, retire's summary says "wait for each run or pass --adopted PID". `--adopted` cannot clear an inFlight block; only `--accept-inflight` can. | `coordinator_handoff.py:820-827` | The summary string is unconditional; the inFlight line before it does name `--accept-inflight`. |
| 13 | LOW (UNVERIFIED) | R12 records `renamed` and shows `ok (renamed)` when `$.command.run({command:"rename"})` *resolves*. Resolution returns the command's output text, not a success flag, so a built-in `/rename` that prints a refusal would still be recorded as renamed. | `.claude/skills/session-start/hooks/register.ts:147-154`; `.claude/types/claude-code.d.ts:1528-1545` (`CommandRunResult = {text?, context?, ref?}`) | Whether `/rename` rejects or resolves on refusal is not documented in the vendored types or the KB mods docs I grepped. |
| 14 | LOW | `recoverPending` adds the session to `pendingChecked` *before* the python call. One failed or timed-out `pending` call therefore loses a persisted pending rename for the rest of the module's life. | `.claude/skills/session-start/hooks/register.ts:190-194` | When the call throws, a later `prompt.submit` returns early at :191. |
| 15 | LOW | Redirect-fallback log paths are recorded relative to the old process's cwd, but they go to a successor that runs from the main checkout. | `coordinator_handoff.py:362-367,436` | `_log_path` returns the raw target, e.g. `logs/ship.log` (test `:342-348`). In practice #3 makes this fallback rare. |
| 16 | LOW | Test cost: the four R5 arms each wait the full 10 s lock bound (about 40 s) because no caller injects `timeout_s`. | `session_common.py:110-113`; `tests/test_coordinator_handoff.py:880,898`; `tests/test_session_start.py:384` | `state_lock(path)` is called with its default everywhere (`coordinator_handoff.py:275,308,630`; `session_start.py:275,306,326`). |
| 17 | LOW (sibling) | The `.agents` mirror rewrites "nearest Claude ancestor's argv" as "nearest Codex ancestor's argv", which is false for this code: `_session_root` matches `claude`. | `.agents/skills/session-start/SKILL.md:48` | Compared with `.claude/skills/session-start/SKILL.md:48` and `session_orphans.py:27`. This is a mirror-generator transform, so it is a ticket for `skills-mirror`, not a change to this diff. |
| 18 | LOW (out of diff) | The mise task description still lists `decide \| name \| launch \| retire` and omits the new `release`. | `mise.toml:1673` | `mise.toml` is not in this diff, so this is a ticket. |

## Q-FRESH — each decision→action pair

- **decide (py)**: the state read, `_judge` and the write all happen under one flock (`coordinator_handoff.py:275-281`). The job-record name is read before the lock, but we do not own that record. Fresh.
- **hook role → skip decide**: the cached role is never re-validated (register.ts:186-195). This is by design under spec R4, and finding #4 is the consequence.
- **hook fire → command.run → skill → launch**: `launch` re-reads state under the lock and refuses an existing launch (py:630-642). Fresh. It does not re-validate that a *queued* second fire is still wanted, but the refusal covers that case.
- **launch census → record → `claude --bg`**: all under one lock. Fresh. The rc of the start is never used to correct the record (#2).
- **retire snapshot → blockers → `claude stop`**: the process snapshot is taken at the start of `_retire_main` (py:952), and inFlight is read immediately before the stop (py:820). Recorded runs can only die, so an older snapshot errs only toward blocking. Acceptable. No lock is held, and nothing writes state after launch.
- **release**: compares `last_fired == level` under the lock (py:308-316). Fresh.
- **session-start decide / renamed / pending**: classify and write under the lock (session_start.py:275-283, 306-314, 326-327). Fresh.
- **session-start rename → `renamed`**: gated on `command.run` resolving, not on a verified name (#13).

## Q-SCOPE

- In scope (the R-item each defeats or regresses): #1 (R3), #2 (R1/R6), #3 (R9; needs a respec, since the code matches R9's text), #4 (R4; needs a respec), #5 (R4), #6 (R3), #7 (R5), #8 (R6), #9 (R8 docs), #10 (R14 docs), #11, #12 (R7), #13 and #14 (R12), #15 (R9), #16 (R5 tests).
- Sibling, so recommend a ticket: #17 (`skills-mirror` generator rewrites "Claude" to "Codex" in prose about process names), #18 (`mise.toml` task description).

## Q-CLAIM — operator-facing strings added or changed, with what enforces each

| String / clause | Enforcing line | Verdict |
|---|---|---|
| `handoff already launched` | `coordinator_handoff.py:223-224` | Enforced, but also shown after a FAILED start (#2): the wording claims a launch that may not exist. |
| `handoff ERROR: …; release rc N` / `release failed to run` | `register.ts:173-179` | Enforced. |
| SKILL: "An existing launch record prevents every subsequent fire and second launch" | `py:223-224,632-642` | Enforced. |
| SKILL: "The first measurement caches the role; lanes make no further Python calls" | `register.ts:186-189,204` | Enforced for the module's lifetime. Note the commit body says "lanes run no process", but each session runs one (#5). |
| SKILL: "DRY_RUN/PROBE pass `--no-commit`" | `register.ts:198,124` | Enforced. The consequence is #1 and #6. |
| SKILL: "failed delivery releases the consumed level" | `register.ts:225,233-240` | Enforced for list, not-listed, reject and throw. A failed `claude --bg` is not "delivery" and is not released (#2). |
| SKILL §2: census "(ship, land, sync, verify-local, bounded-wait, kb-ship, kb-land)" | `py:105-113` | Stale (#9). |
| SKILL §2: "rc 2 means refused (… already launched …): record that in the handoff and stop" | `py:610-651` | rc 2 is also returned AFTER a launch record was written (claude missing). In that case it is not a refusal (#2). |
| Brief: "pass this exact --state-dir to retire" | `py:483,518` (`shlex.quote`) | Enforced. |
| Brief: "blocks (rc 1) while … live and unadopted, or … in flight or unknown" | `py:808-827,741-768` | Enforced. |
| Brief: codes 2 and 3 | `py:783-806,837-850,952-955` | Enforced. |
| Brief: "wait for it (`bounded-wait` on its resolved log's rc line)" | `py:426-436` | NOT enforced: the "resolved log" is the harness `.output` (#3). |
| Brief: "A log marked `unexpanded:` is unresolved redirect text" | `py:367` | Enforced. The converse does not hold: an unmarked path can still be wrong (#3). |
| Log: `release: invalid-session-id or invalid-percent` | `py:302-304` | Mislabelled (#11). |
| Log: `retire: refusing to stop … wait for each run or pass --adopted PID` | `py:822-826` | Misleading when inFlight alone blocks (#12). |
| Log: `launch: census-unavailable: …` | `py:666` | Enforced for `_gather` failures only. Git failure is logged differently (#10). |
| session-start: `session-start pending rename` / `name unknown` / `ok (renamed)` | `register.ts:232,254,153` | Enforced. `ok (renamed)` is gated on resolution, not a verified rename (#13). |
| session-start SKILL: "Queue a known `/rename` BEFORE `/reload-skills`" | `register.ts:215-219` with `confirmRename`'s synchronous first `command.run` call | Enforced. |
| session-start SKILL: "Missing spare records fail closed" | `session_start.py:142-174` | Enforced. Live job records all carry `nameSource:"user"` for `-n` names (26/26 probed, values only), so the predicate matches the real data. |
| session-start SKILL: "vendor types need a … refresh from 2.1.277 to … 2.1.288" | `register.ts:140-145` | The documented `{isAnswered,text}` shape matches the KB doc `plugins__mods__api.md:85-93`. Fine. |
| Spec §3c retire codes 0/1/2/3 | `py:771-850,949-964` | Enforced, except #8 (an uncaught ValueError gives 1). |

## Control arms run

- fd-1 probe: child redirect vs parent zsh in one background Bash task. Child = the redirect file, parent = the harness `.output`, so the probe discriminates.
- `ps` width probe: the self pid line was 987 chars and contained a marker from the end of the command, so the args are not truncated in non-tty `ps`.
- Job-record `nameSource` survey: 26 records, all `user`. The `auto` value is attested in `docs/research/kb/reports/agents/wf-dag-recovery.md:703`. Probe output was counts and name prefixes only; no values were printed.

## GitHub repos touched

_None._ Only local files were read: the repo at df481e1f, the vendored `.claude/types/claude-code.d.ts`, and the offline knowledge-base mirror `knowledge-base/sources/media/claude-code-docs/plugins__mods__{api,reference}.md`.
