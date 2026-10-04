# Cold review: fix/dag-tick-safety-pr1 @ 4c76cc6a (base ad4dbc62)

Reviewer: cold-reviewer (Opus), reviewing the diff by ref. Round 1, OPEN HUNTING per the
adversarial-review skill, with Q-FRESH, Q-SCOPE and Q-CLAIM answered below. A round with no
enumerated domain cannot end the loop, so this round promotes to one bounded round.
Memory: the local cold-reviewer memory dir was empty at start, so no prior patterns were applied.

**Subject:** `ad4dbc62..4c76cc6a`, one commit `4c76cc6a`
`fix(dag-tick): fresh respawn guards, read-only dry-run previews, bounded waits (PR1)`.
6 files, +692/-179: `codex_verdict.py`, `dag_tick.py`, `main.py`, `suites.toml`, and two test files.

**Status: COMPLETE. Verdict: SHIP.** There is no HIGH. Disposition the one MEDIUM (F1)
before PR 2 activates the LaunchAgent, either by fixing it here or by filing a ticket.

## Findings

| # | Sev | Claim | file:line | Evidence |
|---|---|---|---|---|
| F1 | MEDIUM | `--dry-run` prints `would respawn <id>` for a DEAD coordinator that a real tick always SKIPs (superseded, `handoff state dir unresolved`, `no valid sessionId`). The new refusal axes live only in `execute_respawn`, not in `classify`/`plan`, so the dry-run line now diverges every time, not just during the race window. The diff also re-advertises dry-run as the preview (help text) | `python/src/dotfiles_setup/dag_tick.py:1313-1317` (dry-run branch) vs `:1271-1280`, `:1243-1244` | Probe `/tmp/cold-review-dryrun-probe.py`. Arm `superseded`: `dry: would respawn race1234` vs `real: SKIP respawn race1234 — superseded: …`, Popen calls `[]`. Control arm (no launch record): `real: RESPAWN race1234`, Popen called once. So the probe discriminates. Fix: run the read-only read+decide half (`_respawn_refusal` is already pure) in dry-run and print `would SKIP …`/`would respawn …`, or ticket it |
| F2 | LOW | Stale cross-reference: `_cas_check` says it was "Split out of :func:`_reap_locked`", but this diff renamed that function to `_decide_reap` | `python/src/dotfiles_setup/codex_verdict.py:531` | `grep -rn _reap_locked python/src` → this single hit. The definition is gone (`_decide_reap` at `:606`) |
| F3 | LOW | The `reap_codex_lanes` docstring still says "A `NONE` edge … is reported only under `--verbose`", but `LOCK_BUSY` (edge NONE) now always prints. The docstring also says nothing about dry-run routing to `preview` | `python/src/dotfiles_setup/dag_tick.py:1349-1351` vs `:1366-1371`, `:1358` | Code read. The V-d4 test (`tests/test_dag_tick.py`, `test_tick_busy_lock_is_loud_but_owner_mismatch_is_quiet`) asserts the always-print behaviour that the docstring denies |
| F4 | LOW | The edited `workflow.dag-tick-wiring` description is only half-updated: "reading both up front leaves neither guard with I/O between it and `Popen`" (there are three reads now). The same description still documents "`execute_stop` now carries the SAME re-check (#604)", a function #1644 removed (pre-existing, sibling) | `python/verification/suites.toml:1979` | Read in the diff (`description` line). `grep -n "def execute_stop" dag_tick.py` → 0 hits. Control: `def execute_respawn` → 1 |
| F5 | LOW (pre-existing, sibling, Q-FRESH) | `reap()` evaluates the liveness gate BEFORE taking `.reap.lock` and does not re-check it under the lock. If a producer relaunch (`codex_lane.prepare_lane` clears EXIT/log/verdict/processed under the same lock) lands between gate and lock, the reap reads a fresh in_progress lane with no verdict, gets FILE_MISSING, and escalates `needs_human` for a round that just started. This diff restructured `reap` but kept the ordering | `python/src/dotfiles_setup/codex_verdict.py:466-487`; producer `codex_lane.py:310-322` | Code read. UNVERIFIED at runtime (no interleaving test). Ticket recommendation, not a change request |
| F6 | LOW (pre-existing, sibling) | FILE_MISSING neither consumes nor marks the lane, so a settled lane with no verdict re-escalates `needs_human` on every tick. That is the "warning storm" the `_consume` docstring says the inversion avoids. Parity with the old code is preserved, as specified | `python/src/dotfiles_setup/codex_verdict.py:630-633`, `:410-417` | Code read, and the old `_reap_locked` returned `failure` without mark. The downstream impact (projector dedupe in `dag_project`) is UNVERIFIED. Ticket recommendation |
| F7 | LOW (nit) | The reason `no valid sessionId` also fires for a syntactically valid sessionId whose 8-char prefix does not match the node id. That is a mismatch, not an invalid id | `python/src/dotfiles_setup/dag_tick.py:1195-1206` | Test cell `mismatched_id` (`tests/test_dag_tick.py`, `test_fresh_handoff_race`) asserts this exact text |
| F8 | LOW | Flake risk: the V-d1 healthy-control arm keeps `gate_timeout_s=0.2`/`census_timeout_s=0.2` while fork+exec'ing a real `/bin/sh` fake. On a loaded host (the "busy slot" condition) startup can exceed 200 ms, and the arm then fails on `"timed out after" not in caplog.text` | `tests/test_dag_tick.py:262`, `:275-277` | Reasoning only (UNVERIFIED). It passed here: 342 passed in 2.54s. Widening the control arm's timeouts (e.g. 5s) keeps it discriminating |
| F9 | LOW (nit) | The help text "then exit without spawning anything" is literally false: a dry run spawns `claude logs`, `claude agents`, `ps`, and now `git worktree list` (`build_tick_context`). The wording predates this diff, but the diff edited this sentence | `python/src/dotfiles_setup/main.py:1920-1921`; `dag_tick.py:1417-1421` | Code read |
| F10 | LOW (doc) | `execute_respawn`'s ~60-line ordering rationale was replaced by "documented in #601's v4-v6 review", which is no resolvable path. The full rationale now lives only in the suites.toml description | `python/src/dotfiles_setup/dag_tick.py:1262-1263` | Diff read (removed lines 180-244 of the diff hunk) |
| F11 | INFO (out of allowlist, already known) | `codex_lane.py:6` "maps ten outcomes" is stale now that `LOCK_BUSY` exists. The spec addendum already names it for the PR body | `python/src/dotfiles_setup/codex_lane.py:6` | grep hit |
| U1 | UNVERIFIED | Whether `claude logs <bogus>` and `claude agents --json --all` finish under the ratified 10 s / 20 s on this host under load. If the census routinely times out, the watchdog does nothing, though it logs this distinctly | `dag_tick.py:235-236` | Not measured: no live runs allowed |

## Verified (positive evidence)

- Targeted tests: `uv run --project python pytest tests/test_dag_tick.py tests/test_codex_verdict.py -x -q` → **342 passed, rc=0** (`/tmp/cold-review-dagtick-pytest.log`).
- The committed diff is identical to the diff the lane gated. `diff` of `.agent/logs/dag-tick-pr1-final.diff` vs `git diff ad4dbc62..4c76cc6a`, with `index` lines removed, gave rc=0. Lane receipts: lint rc=0, pytest rc=0, verify rc=0 (175 passed) in `.agent/logs/dag-tick-pr1-final-gates.json`.
- Token uniqueness, counted independently with `str.count` over `per_path_tokens` of the 5 dag/codex suites: every token =1 except `mise.toml 'program = "~/.local/bin/mise"'`=2. That file is unchanged and the token predates this diff. Control: `def reap(`=1, fresh-invented absent string=0.
- Mutation receipts are genuine. The six arms in `.agent/logs/dag-tick-pr1-mutations.jsonl` all have rc=1. The V-a1 deletion fails exactly the 3 terminal cells (controls pass). V-a2 fails exactly the 8 refusal cells (4 controls pass). V-b3 fails 11/12 (`not_settled` correctly unaffected). V-d1 took ~22s without `timeout=`.
- U6 correction grounded: `knowledge-base/sources/agent-harness-docs/docs/claude-code/agent-view.md:695` says "Restart a session, running or stopped".
- `_read_launch_state` writes nothing and only raises `StateUnreadableError` (an `OSError`), which `_handoff_refusal` catches (`coordinator_handoff.py:266-282`, `session_common.py:104-116`). `launch` writes the receipt and state via atomic `write_state` (`coordinator_handoff.py:965-999`) and never deletes the receipt, so an unlocked reader cannot see a "neither" window after a successful start.
- Effect parity of the decide/apply split matches the old code for every outcome (`codex_verdict.py:614-646` vs the removed `_reap_locked`/`_read_payload` consume calls).
- `build_tick_context` (`dag_tick.py:1408-1437`) is the only production `TickContext` constructor. `main_checkout` raises only `SessionError` (`session_common.py:183-203`).
- `is_terminal` and `is_needs_human` are disjoint (state set vs `blocked`), so the new terminal check cannot shadow the escalation reason.

## Q-FRESH (each decision→action pair)

1. `execute_respawn`: the reads are state (t0), roster, handoff record, pid+`ps`. Then a pure `_respawn_refusal`, then `Popen`. Nothing does I/O between the decision and `Popen` (`strip_respawn_env` reads only `os.environ`). The terminal and escalation decisions rest on the t0 read, which is the oldest. The window is narrowed, not closed, and the docstring says so. **OK.**
2. `reap()`: the CAS and payload are decided under the lock from fresh reads, and the effects are applied under the same lock. The liveness gate is NOT re-validated under the lock (**F5**, pre-existing).
3. `preview()`: no action, so N/A. Its docstring states the unlocked "would" semantics.
4. Dry-run `_execute_or_preview`: the "would respawn" decision is never validated against the fresh refusal reads (**F1**).
5. `build_tick_context`: resolves the handoff dir once per tick, before the tick lock. It is a path, not volatile state. **OK.**

## Q-SCOPE

- In scope: F1 (a consequence of (a) adding refusal axes, set against (b)'s dry-run-as-preview purpose), F2, F3, F7, F8, F9, F10, and F4's first half.
- Sibling, so ticket it: F4's `execute_stop` paragraph, F5, F6, F11.

## Q-CLAIM (operator-facing strings added or changed)

| String / clause | Enforcing line | Verdict |
|---|---|---|
| `gate preflight timed out after %gs` | `dag_tick.py:1023` `timeout=` + `:1025` except | OK |
| `census timed out after %gs` | `:1059` + `:1061` | OK |
| `SKIP … terminal since classification (state, tempo)` | `:1233` `is_terminal`, and the classifier uses the same `node_from_state` (`:1128`), so the snapshot was non-terminal | OK |
| `SKIP … superseded: coordinator-handoff launch recorded for <sid>` | `:1213` (`"launch" in state or _started_pending`) | OK |
| `SKIP … superseded check failed: <exc>; not respawning on doubt` | `:1210` | OK |
| `SKIP … handoff state dir unresolved` | `:1201-1203` | OK |
| `SKIP … no valid sessionId` | `:1195-1206`: also fires on a prefix mismatch | narrow (F7) |
| `[dry-run] would CODEX-REAP … [outcome] edge=…` | `:1358` routes to the effect-free `preview`. A real reap may instead return LOCK_BUSY, a caveat documented at `codex_verdict.py:500-501` | OK |
| `[dry-run] would respawn <id> — not terminal and the process is not alive` (unchanged string, changed truth) | only `plan()` `:745-751`. The new refusals are absent | **F1** |
| `_reply_queued_reason`: "`claude respawn` would restart a live session out from under its own work" | vendor doc `agent-view.md:695` | OK |
| `.reap.lock held for Xs — not read; retried next tick` | `codex_verdict.py:473-479`: nothing consumed, and `reap_codex_lanes` runs every tick | OK (true only while ticks run) |
| `--dry-run` help: "without spawning anything" | none: it spawns subprocesses | F9 |
| `--dry-run` help: "or consuming a verdict" | `dag_tick.py:1358` | OK |
| module bullet "Respawn requires fresh readable state, no terminal…, no superseding handoff launch, and a process confirmed dead" | `:1228-1246` | OK |

## Notes

- This review did not run `mise run lint`, `verify` or the full pytest, per the caller's restriction. It relies on the lane receipts, cross-checked by the independent token count above.
- No source, config or test file was edited. The only writes were this report, `/tmp` probe and log files, and the reviewer's local memory.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): diff, consumers (`coordinator_handoff`, `session_common`, `codex_lane`), suites.toml, lane receipts.
- [mrkhachaturov/agent-harness-docs](https://github.com/mrkhachaturov/agent-harness-docs): offline mirror `agent-view.md:695` for `claude respawn` semantics.
