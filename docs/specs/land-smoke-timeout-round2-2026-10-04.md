# Land smoke timeout — round 2 (orphan-proof smoke + cold-review fixes)

Branch `fix/land-smoke-timeout` @ c14af317. Round 1 spec: `docs/specs/land-smoke-timeout-2026-10-04.md`.
Round 1 cold review (Opus, verdict DO NOT SHIP):
`docs/research/kb/reports/agents/cold-review-land-smoke-c14af317.md`.

## 1. Objective

Make the land/sync smoke step unable to leave work running in the container, and unable to run two smokes or a
smoke next to another heavy run, with each guarantee enforced by code and a test that has a control arm.

Motivating incident (2026-10-04, Ray had to kill processes by hand):

- `mise run land -- 1666`, on main at 64c6aae8 (main has NO slot around the smoke), ran
  `docker exec … 0eed9addeee6 scripts/devcontainer-smoke.sh`. At the same time `mise run ship` held the heavy-gate slot
  for pre-push pytest (`heavy-gate run --label pre-push`). That made two heavy runs at once.
- The smoke hit `_SMOKE_TIMEOUT_S = 1800.0` and raised `subprocess.TimeoutExpired`
  (log `/Users/rmanaloto/.claude/jobs/a90e493a/tmp/land-1666.log`).
- `subprocess.run` killed only the host `docker` CLI. Inside the container, bash `devcontainer-smoke.sh` (pid 84353),
  `uv run … pytest` (85057) and 4 xdist workers (85091–85103) kept running for more than 38 minutes. They kept
  spawning children (`mise exec -- bun run …`).
- The agent was denied the kill. Ray ran two separate `docker exec … pkill`s: one for the script, then a second one
  because the first left pytest alive.

This is cold-review F2 (moby/moby#9098: killing `docker exec` does not terminate the spawned process).

## 2. Files (allowlist)

- `python/src/dotfiles_setup/container.py`
- `tests/test_container.py`
- `.claude/rules/persistence-gate-retry.md`
- `docs/specs/land-smoke-timeout-round2-2026-10-04.md` (this file; append a "Round 2 result" section only)

`scripts/devcontainer-smoke.sh` is NOT in scope: it has zero bash-budget headroom (166/166, `bash_budget.py:92-97`),
so the wrapper lives in the Python argv (M3). Anything else is out of scope. If a fix requires another file, STOP and report it as dissent.

## 3. Interfaces

- `_run_smoke(container_id: str, workspace_dest: str) -> tuple[bool, str]`: keep the signature and the tuple contract.
- New typed failure details, each a stable prefix that tests assert:
  - `smoke already running in <id12> (pids …)`: a smoke or its pytest is already live in the container, so refuse
    instead of starting a second one.
  - `smoke timed out after <T> seconds: …`: existing prefix; it must also report the reap result
    (`reaped N in-container processes` or `ORPHANS REMAIN: pids …`).
- The in-container command must self-terminate before the host timeout: a coreutils `timeout --kill-after` wrapper
  (exact budget in §3a; §3a overrides this bullet).

## 3a. Design pins (premise-verify round 1, `docs/research/kb/reports/agents/premise-verifier-land-smoke-round2.md`)

- **Slot and identity (M2/F3/F8):** `verify_latest` acquires `host_lock.HEAVY_GATE` ONLY when `run_smoke=True`. Under the
  slot it resolves container id, mount destination and HEAD (re-resolve; do not reuse pre-slot values). It then calls
  `_run_smoke(container_id, workspace_dest, *, lock_fd: int | None = None)`. The new keyword-only parameter is the only
  signature change. `_run_smoke` passes `lock_fd` via `pass_fds`. F8's mutation = drop `pass_fds` in `_run_smoke`; a
  test must observe that the child holds the fd and fail without it. The slot is held through the exec, the probe and
  the reap (M5).
- **Run identity (M4):** each smoke exec carries a fresh marker, `docker exec -e DOTFILES_SMOKE_RUN_ID=<uuid4> …`.
  The pre-flight REFUSES (never kills) when any process in the container runs `devcontainer-smoke.sh`, whatever its
  marker. The reap kills ONLY processes whose `/proc/<pid>/environ` carries THIS run's marker.
- **Probe mechanism (M6):** probe and reap run through `docker exec <id> python3 -c <inline program>`. The program
  reads `/proc/*/cmdline` and `/proc/*/environ`, excludes its own pid and its parent chain, and prints JSON. Verify
  read-only that `python3` is on the image PATH (`docker exec <id> python3 --version`). If it is absent, STOP and
  dissent. No `pgrep -f` (it self-matches).
- **Timeout budget (M7):** with configured `T` (`DOTFILES_SMOKE_TIMEOUT_S`, default 1800):
  - `kill_after = max(1, min(30, 0.1*T))`;
  - `grace = max(2, min(60, 0.1*T))`;
  - inner argv `timeout --kill-after=<kill_after>s <T>s scripts/devcontainer-smoke.sh`;
  - host `subprocess` timeout = `T + kill_after + grace`.

  So the inner wrapper always fires first. Tests use a `T` of a few seconds.
- **Inner timeout exit (M1):** the `docker exec` rc 124 or 137 maps to `smoke timed out after <T> seconds (in-container
  timeout): <tail>` with NO `stale base?` hint. The orphan probe and reap run on this path too. The host
  `TimeoutExpired` path keeps its prefix and also probes and reaps.
- **`timeout` implementation (P7):** Ubuntu 26.04 may ship uutils coreutils. Record `timeout --version` from the image
  (read-only). Prove with a test that the fake honours group kill, and prove in-image only via the read-only version
  probe. If `--kill-after` is unsupported, STOP and dissent.
- **F5 (M9):** keep stdout and stderr separate, and prefer the first FAIL line, then the last 3 stdout lines.

- **Re-verify pins (`docs/research/kb/reports/agents/premise-verifier-land-smoke-round2-reverify.md`):**
  - **N1, group kill:** run ONE harmless in-image arm, read-only in effect:
    `docker exec <id> /usr/bin/python3 -c …` plus `timeout -k1 1 sh -c 'sleep 30 & sleep 30 & wait'`, then a `/proc`
    check that no `sleep 30` survives. Record the result. If children survive, the marker reap is the backstop: say so
    in the result and do NOT claim group kill.
  - **N2:** `verify_latest` catches `host_lock.HostLockTimeoutError` and returns a failed `smoke-tiers-1-3` Check
    carrying `smoke host heavy-slot wait timed out`. `test_container.py:421-426` must stay green.
  - **N3:** the fake `docker` must support a ready-file handshake, emit rc 124/137 for the inner path, and record argv
    so the "delete the wrapper" mutation fails an argv assertion. Host-timeout tests use the smallest `T`.
  - **N4:** the probe and reap use `/usr/bin/python3` (NOT the mise shim; `.devcontainer/mise-system.toml:217-219`).
    Verify that exact path in-image.
  - **N5 (accepted residual):** rc 137 from an OOM/SIGKILL child is reported as a timeout. Distinguish by elapsed
    time ≥ `T` if cheap; otherwise name it in the rule.
  - **N6:** both timeout paths format the configured `T` (not `T+kill_after+grace`). `test_container.py:315`
    (`after 0.1 seconds`) is the anchor.

## 4. Constraints and invariants

- Fix these cold-review findings: **F1** (flaky 0.1 s fixture; generous timeout for non-timeout tests, a ready-file
  handshake plus a timeout of a few seconds for timeout tests; must pass under `-n auto`), **F2** (above), **F3**
  (resolve container id, mount destination and HEAD AFTER acquiring the slot, or re-resolve after), **F5** (time-ordered
  tail, with the first FAIL line preferred), **F7** (narrow the rule wording), **F8** (make the `pass_fds` mutation
  fail a test), and **F9** (rule failure-mode table rows for the new messages, rule file only). For **F4** and **F6**,
  do not implement them: list them as tickets to file in your closing list.
- Pre-flight and reap: exactly as §3a pins them. Pre-flight REFUSES on any `devcontainer-smoke.sh` process. The reap
  kills ONLY processes carrying THIS run's `DOTFILES_SMOKE_RUN_ID`, on both timeout paths (host `TimeoutExpired` and
  inner rc 124/137), and reports survivors. **§3a overrides §3 and §4 wherever they differ.**
- The smoke stays under `host_lock.HEAVY_GATE` (round 1). Do not drop the slot.
- Zero-skip; no inline suppressions; no new `.sh`; no `2>/dev/null` in the Dockerfile; keep the zero-bash-logic budget.
- Do NOT run the full pytest suite, `mise run lint` or `mise run verify`. The caller runs the heavy gates under the
  host slot. You may run `uv run --project python pytest tests/test_container.py -q` (single file) and `ruff`/`ty` on
  the changed modules.
- Do not use the real devcontainer for tests: use the fake-`docker` fixture pattern already in
  `tests/test_container.py` (`smoke_system`).

## 5. Verification

- `uv run --project python pytest tests/test_container.py -q -n auto` is green 3 times in a row. Then `-n 0` once.
- Mutation arms, each run and reported as FAILING the suite:
  - delete the inner `timeout` wrapper;
  - delete the post-timeout reap call;
  - delete the pre-flight orphan probe;
  - drop `pass_fds`.
- `uv run --project python ruff check python/src/dotfiles_setup/container.py tests/test_container.py` rc 0;
  `ty check` on `container.py` rc 0.

## 6. Commit

`caller`. Leave changes uncommitted. Report `git diff --stat`.

## 7. PREMISES

| # | Kind | Claim | Source |
|---|---|---|---|
| P1 | L | `_SMOKE_TIMEOUT_S = 1800.0` | `python/src/dotfiles_setup/container.py:52` (this branch) |
| P2 | I | smoke exec is `_run([... "docker","exec","--workdir",dest,id,"scripts/devcontainer-smoke.sh"], timeout=..., pass_fds=...)` inside `host_lock.held(host_lock.HEAVY_GATE, ...)` | `container.py:126-140` (this branch) |
| P3 | I | `TimeoutExpired` handling builds `smoke timed out after …` from stdout-then-stderr tail | `container.py:141-155` |
| P4 | L | the test fixture sets `DOTFILES_SMOKE_TIMEOUT_S=0.1` | `tests/test_container.py:290` |
| P5 | E | the incident's process tree: bash 84353, uv 85057, 4 xdist workers 85091-85103, live after 38 min | `docker exec 0eed9addeee6 ps` read 2026-10-04 ~15:25 CDT |
| P6 | P | a killed `docker exec` client does not stop the in-container process | moby/moby#9098 (cold review F2) |
| P7 | A | a coreutils `timeout` (GNU or uutils — record which) with `--kill-after` is in the image | ASSUMED — lane verifies read-only (`docker exec … timeout --version`); base `ubuntu:26.04` (`.devcontainer/Dockerfile:14`) |
| P9 | I | re-entrant `held()` in the same pid yields `None` | `host_lock.py:171-179`, `:186-187` (premise-verify M2) |
| P10 | L | `devcontainer-smoke.sh` 166 lines = budget 166 | `bash_budget.py:92-97` (premise-verify M3) |
| P11 | I | the fake `docker` treats every exec as the smoke; `test_smoke_invalid_timeout_uses_bounded_default` asserts `observed == [1800.0]` — retarget it (host timeout is now `T+kill_after+grace`) | `tests/test_container.py:256-276`, `:354-363` |
| P8 | I | main's `_run_smoke` takes no slot (the incident ran main code) | `python/src/dotfiles_setup/container.py:108-127` on main 64c6aae8 |

## Round 2 result

Implemented on `fix/land-smoke-timeout` from HEAD
`17c858a18023e94666913cbc8bca78ee0f77d164`; changes remain uncommitted (caller owns commit).
Section 3a governs the implementation. No claim of shipping or full integration is made.

- Image prerequisites confirmed read-only in running amd64 container
  `0eed9addeee650710c1495e2cd3f1e95882c169a769999546420db8543dc64fa`:
  `/usr/bin/python3 --version` rc 0, Python 3.14.4; `timeout --version` rc 0,
  `timeout (uutils coreutils) 0.8.0`; `timeout --help` rc 0 lists `-k`/`--kill-after`.
  It mounts the main checkout `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`
  at `/workspaces/dotfiles`; it does not mount this implementation worktree.
  One harmless N1 arm used `/usr/bin/python3` and
  `timeout -k1 1 sh -c 'sleep 30 & sleep 30 & wait'`, with a 20-second host bound.
  Docker exec and the observer both returned rc 0; inner timeout returned rc 124
  in 1.224 seconds. The observer saw both `sleep 30` children (PIDs 97867/97868,
  starttime 42966922) before termination. After timeout, survivors were empty;
  marker-scoped cleanup killed no processes and its final survivor list was empty.
  Marker `DOTFILES_N1_PROBE_ID=e824e6e0-0061-4065-91d9-0271ac25c815` isolated the arm.
  The observer required exactly two marked children before termination, inner
  rc 124/137, and no remaining marked live processes; the child-count assertion
  would fail if no child launched. This demonstrates child/group termination
  only for this uutils 0.8.0 harmless shell tree. Arbitrary smoke descendants and
  SIGKILL escalation were not exercised, nor were real smoke, lifecycle actions
  or a container gate.
- `verify_latest(run_smoke=True)` owns the heavy slot and re-resolves container
  id, mount destination and HEAD under it; the no-smoke path avoids the slot.
  `_run_smoke(..., *, lock_fd=None)` passes an available fd into the smoke child.
  Pre-flight refuses any existing smoke, including unreadable process cmdline
  (failed probe, no launch). Each run has a fresh marker, the prescribed inner
  timeout and larger host bound, and both timeout paths probe/reap under the slot.
  Marker cleanup uses a kernel-bound pidfd and fresh marker check before signaling
  to avoid killing an unrelated process if a selected PID was reused.
  Read-only image inspection using exact `/usr/bin/python3` returned Docker/host
  rc 0 and empty stderr: `os.pidfd_open` and `signal.pidfd_send_signal` exist;
  opening and closing the inspector's own pidfd succeeded. No signals were sent
  in that capability probe and no additional N1 arm ran.
- F7/F9 rule updates narrow guarantees to `verify-latest(run_smoke=True)`, add
  failure-table actions for timeout, slot wait, live-smoke refusal, probe failure
  and unresolved orphans, and replace unsafe standalone retry advice with
  exclusion of live smoke/orphans and safe scheduling. Diagnostics describe
  separate stdout/stderr, first FAIL preference, configured T, and marker-only reap.
  The accepted N5 residual is explicit: child OOM/SIGKILL rc 137 is also a timeout.
- File-scoped `agnix --strict` on the rule and this spec returned rc 0 (no issues);
  `git diff --check` on both documentation files returned rc 0. The rule measures
  170 lines and 10,651 bytes, within the unscoped 200-line/24,000-byte budget.
- Final-revision `uv run --project python pytest tests/test_container.py -q -n auto`
  passed three consecutive runs on unchanged code: rc 0, 41 passed in 21.84,
  30.08 and 16.00 seconds. The corresponding `-n 0` run returned rc 0, 41 passed
  in 86.58 seconds. Changed-file ruff and `ty check` on `container.py` returned
  rc 0; Python `git diff --check` returned rc 0. No code edits followed the first
  final parallel run. Fake tests include group-kill grandchildren, marker change
  after pidfd open, unreadable pre-flight cmdline, and reap errors. Teardown checks
  its unique per-test state path in a live process command before signaling.
  Dispatcher inspection confirmed the autouse fixture in `tests/conftest.py`
  isolates `DOTFILES_LOCK_DIR` and clears inherited `DOTFILES_LOCK_HOLDER_*`;
  these targeted tests do not take the coordinator's real host slot.
- Final mutations ran against isolated temporary copies of the final code,
  each through the whole single-file suite with `-n auto` and a 180-second bound.
  Every arm returned rc 1 with ordinary behavior assertion failures; no setup,
  collection, NameError or UnicodeDecodeError failures, and every stderr was empty.
  The mutation driver returned rc 0 with `ALL_FOUR_MUTATIONS_CAUGHT`.
  Receipts are in
  `/var/folders/z4/0p475gq56vvczc3y4qlt60f80000gn/T/land-smoke-final-mutations-be8lno71/<arm>/{stdout,stderr}.log`.

| Final mutation | Real rc | Failed / passed | Seconds |
|---|---|---|---|
| Delete inner timeout wrapper | 1 | 12 / 29 | 18.46 |
| Delete post-timeout reap | 1 | 11 / 30 | 26.75 |
| Delete pre-flight probe | 1 | 4 / 37 | 23.76 |
| Drop `pass_fds` | 1 | 4 / 37 | 62.48 |

- Earlier failures retained for provenance: initial `ruff check --fix` rc 1
  (line length/SIM105), corrected with format rc 0; exploratory serial rc 1,
  five failed/33 passed in 409.34 seconds, and focused inner-timeout rc 1,
  three failed in 9.97 seconds. Strict UTF-8 stderr decoding interrupted cleanup;
  `_run(errors="replace")` corrected that path. The isolated fixture now uses
  base-OS git instead of repeated mise-shim startup. Parent review also prompted
  the pidfd identity protection and fail-closed unreadable-cmdline control.
  An earlier 40-test revision passed three parallel runs (42.69/38.13/47.50
  seconds) and serial (93.80 seconds), all rc 0; its four mutations returned rc 1
  with 12/11/3/4 failures in 90.62/55.21/87.57/90.56 seconds respectively.
  Those earlier results are superseded by the final 41-test evidence above.
- Full pytest, lint, verify, lint-docs and container gates are reserved for the
  coordinator and were not run by this team. No full integration or shipping
  claim is made; all changes remain uncommitted.
- Tickets to file (not implemented or filed here): F4 lifecycle smoke result
  reuse with container-ID/HEAD proof; F6 slot and timeout coverage for lifecycle,
  standalone and full `verify-local` smoke; F9 matching failure tables in the
  out-of-scope `.claude/skills/devcontainer-sync/SKILL.md` and
  `.agents/skills/devcontainer-sync/SKILL.md`.
