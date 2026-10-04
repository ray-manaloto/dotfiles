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
- `scripts/devcontainer-smoke.sh` (only if needed; bash budget applies: `python/src/dotfiles_setup/bash_budget.py`)
- `.claude/rules/persistence-gate-retry.md`
- `docs/specs/land-smoke-timeout-round2-2026-10-04.md` (this file; append a "Round 2 result" section only)

Anything else is out of scope. If a fix requires another file, STOP and report it as dissent.

## 3. Interfaces

- `_run_smoke(container_id: str, workspace_dest: str) -> tuple[bool, str]`: keep the signature and the tuple contract.
- New typed failure details, each a stable prefix that tests assert:
  - `smoke already running in <id12> (pids …)`: a smoke or its pytest is already live in the container, so refuse
    instead of starting a second one.
  - `smoke timed out after <T> seconds: …`: existing prefix; it must also report the reap result
    (`reaped N in-container processes` or `ORPHANS REMAIN: pids …`).
- The in-container command must self-terminate before the host timeout. Wrap it in GNU coreutils
  `timeout --kill-after=<k> <T_inner>`, with `T_inner` < host timeout. Verify in the image that `timeout` exists and
  that it signals the whole process group, including xdist workers and `bun` grandchildren. If it does not, use
  `setsid` plus a group kill, and say which in the result.

## 4. Constraints and invariants

- Fix these cold-review findings: **F1** (flaky 0.1 s fixture; generous timeout for non-timeout tests, a ready-file
  handshake plus a timeout of a few seconds for timeout tests; must pass under `-n auto`), **F2** (above), **F3**
  (resolve container id, mount destination and HEAD AFTER acquiring the slot, or re-resolve after), **F5** (time-ordered
  tail, with the first FAIL line preferred), **F7** (narrow the rule wording), **F8** (make the `pass_fds` mutation
  fail a test), and **F9** (rule failure-mode table rows for the new messages, rule file only). For **F4** and **F6**,
  do not implement them: list them as tickets to file in your closing list.
- Pre-flight orphan check: before the exec, probe the container read-only for a running `devcontainer-smoke.sh` or a
  pytest whose parent chain is the smoke. If found, fail with the "already running" detail. Never kill a process you
  did not start, except in the post-timeout reap.
- Post-timeout reap: after a host timeout, re-probe the container. Kill only processes whose command line is the smoke
  script or its descendants. Report survivors in the detail.
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
| P7 | A | GNU `timeout` is in the image and signals its process group by default (no `--foreground`) | ASSUMED — lane must verify in-image (read-only `docker exec … timeout --version` is allowed) |
| P8 | I | main's `_run_smoke` takes no slot (the incident ran main code) | `python/src/dotfiles_setup/container.py:108-127` on main 64c6aae8 |
