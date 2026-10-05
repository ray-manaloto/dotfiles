# SPEC: land/sync smoke timeout — review and fix (Ray, 2026-10-04: "/codex-sdlc-team to review and fix")

Mode: implement. First REVIEW the failure class below (confirm or refute every premise against the code), then FIX it.
If a premise is refuted, stop and report it rather than guess.

## 1. Objective

`mise run land -- 1662` (2026-10-04) failed with rc=1 because the in-container smoke timed out. The run itself was
healthy. Make a smoke timeout a typed, diagnosable failure. Stop it from re-running a ~14-30 min suite that already
passed in the same run. Stop it from losing to concurrent host load.

Evidence: log `/Users/rmanaloto/.claude/jobs/bcc4b879/tmp/land-1662.log` (read only), and the verbatim audit
`docs/research/kb/reports/agents/handoff-audit-2026-10-04h.md` on branch `docs/handoff-2026-10-04i` (LOST #1). The facts
from that log:

- Tiers 1-3 passed once at 17:27:37Z ("devcontainer smoke: tiers 1-3 OK"; pytest `5023 passed, 4 skipped in 823.64s`).
- Then `verify-latest` ran `scripts/devcontainer-smoke.sh` AGAIN and it raised an uncaught
  `subprocess.TimeoutExpired ... timed out after 1800.0 seconds`. The call path is
  `pr.py:1059 land_main → sync.py:906 sync_main → sync.py:841 _verify → container.py:184 verify_latest →
  container.py:109 _run_smoke → container.py:64 _run`.
- The traceback reached the top-level "Unexpected command failure" handler in `main.py`.
- At the same time, a `mise run ship` on the host was running its pre-push full pytest under
  `heavy-gate run --label pre-push`. The in-container smoke takes no host heavy slot (cf. `host_lock.py:30-32`: container
  heavy work is outside the lock).

## 2. Files (allowlist)

`python/src/dotfiles_setup/container.py`, `python/src/dotfiles_setup/sync.py`, `python/src/dotfiles_setup/pr.py` (only if
needed), `python/src/dotfiles_setup/host_lock.py` or the heavy-gate module (only if needed), `scripts/devcontainer-smoke.sh`
(comment fix only: the stale "uv pytest 190/190" note), `tests/test_container.py` / `tests/test_sync.py` / the relevant
existing test files, `python/verification/suites.toml` (only if a contract pins changed text), and
`.claude/rules/persistence-gate-retry.md` (update the "land-smoke transient" section to match the new behaviour, within its
size budget). Nothing else.

## 3. Interfaces / required behaviour

1. **Typed timeout.** `_run_smoke` must catch `subprocess.TimeoutExpired` and return `(False, detail)`. The detail names
   the timeout, its seconds, and the tail of the partial output, so `verify_latest` reports a failed `smoke-tiers-1-3`
   Check and `land`/`sync` exit through their normal nonzero path, with no traceback. The "stale base? dev-rebuild" hint
   must NOT be appended to a timeout: per `.claude/rules/persistence-gate-retry.md` that hint is the expensive wrong move.
2. **No duplicate smoke in one run.** First find where the FIRST smoke in the 1662 run came from: the devcontainer
   lifecycle, or `sync`'s converge step. If the same run has already passed tiers 1-3 against the same container ID and
   the same workspace HEAD, `_verify` must reuse that result rather than run the suite again. Record the reuse in the
   Check detail. If you cannot establish a reliable same-run proof from code you own, do NOT implement reuse; report why
   instead.
3. **Host-load coordination.** The in-container smoke runs the full pytest on the same CPU as the host gates. Either:
   - take the existing host heavy slot (the same lock `heavy-gate run` uses) around the `docker exec` smoke, bounded and
     with the slot's normal timeout semantics; or
   - if that would deadlock with a caller that already holds the slot (check `pr.py:671-707` and the land path), say so
     and choose the safe alternative.

   Do not raise `_SMOKE_TIMEOUT_S` as the fix. You may make it configurable via an env var with the current default.

## 4. Constraints

- Zero-bash-logic: logic goes in Python. `devcontainer-smoke.sh` may only get its comment fixed; its line count must not
  grow (`bash_budget.py`).
- `tests/AGENTS.md`: no mocks of our own modules or internal collaborators. Fake only at the system boundary
  (`docker`/`gh`/`mise` executables on PATH, a temp HOME), as `tests/test_sync.py` does for `docker`.
- No inline suppressions. No `2>/dev/null`.
- Do not run `mise run land`, `sync`, `dev-rebuild`, `up`, or any real container op. A land loop owns the devcontainer.
- Do not push, ship, or commit (`COMMIT: caller`). Leave the diff uncommitted.
- One heavy gate host-wide: run gates through `mise run gate -- run <name>`, which takes the slot.

## 5. Verification

- New tests:
  - a fake `docker` that sleeps past a tiny configured timeout produces a failed Check and a nonzero sync status, not an
    exception;
  - the reuse path (if implemented) skips the second `docker exec` only when container ID and HEAD both match, and runs
    it when either differs;
  - the slot is taken and released around the smoke (if implemented).
- Fail arms: revert each change and confirm its test fails.
- Gates: `mise run gate -- run pytest`, `mise run gate -- run lint`, `mise run gate -- run verify`, plus
  `mise run gate -- run lint-docs` if the rule file changed. Report each rc.

## 6. Commit

`COMMIT: caller`. Branch `fix/land-smoke-timeout` (base origin/main 25bceb1e). Suggested subject:
`fix(land): a smoke timeout is a typed failure, not a traceback; no duplicate smoke per run`.

## 7. PREMISES (verify each; mark CONFIRMED/REFUTED with file:line)

| # | Premise | Citation |
|---|---|---|
| P1 | `_SMOKE_TIMEOUT_S = 1800.0` and `_run` passes it to `subprocess.run` without catching `TimeoutExpired` | `container.py:49`, `:61-66`, `:108-118` |
| P2 | `verify_latest` appends the "stale base? `mise run dev-rebuild`" hint to every smoke failure | `container.py:183-195` |
| P3 | `sync._verify` calls `verify_latest(workspace, run_smoke=True)` unconditionally | `sync.py:828-841` |
| P4 | `land_main` calls `sync_main` after the merge | `pr.py:1059` |
| P5 | The smoke's tier 2 runs the FULL pytest suite | `scripts/devcontainer-smoke.sh:52-53` |
| P6 | Container heavy work is outside the host lock | `host_lock.py:30-32` |
| P7 | The FIRST smoke in the 1662 log came from a lifecycle hook or converge step in the same `land` invocation | land-1662.log ~lines 660-5830 — VERIFY |
