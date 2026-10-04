# Spec: land smoke round 3 — fix cold-review findings on 9241c174 (2026-10-04)

Source: Opus cold review `docs/research/kb/reports/agents/cold-review-land-smoke-r2-9241c174.md` (DO NOT SHIP).
F1 CONFIRMED by coordinator probe 2026-10-04 16:45: in container 0eed9addeee6 `test -x /usr/bin/git` → 1 while the
control `test -x /usr/bin/env` → 0; `command -v git` = `/usr/local/share/mise/shims/git`.

## 1. Objective
Fix F1 (HIGH) and F2 (MEDIUM); fix or explicitly accept in the spec's Result section F3, F4, F6, F7, F10, F11.

## 2. Files (allowlist)
`python/src/dotfiles_setup/container.py`, `tests/test_container.py`, `.claude/rules/persistence-gate-retry.md`,
this spec (append `## Result`).

## 3. Interfaces
- F1: `smoke_system` fixture (`tests/test_container.py:217-219`) must not require `/usr/bin/git`; resolve git with
  `shutil.which("git", path=os.defpath) or shutil.which("git")`, and fail with a clear message only if neither exists.
- F2: `_smoke_output` keeps the previous behaviour on the non-timeout path (combined stdout+stderr tail, so a stderr-only
  cause such as a mise Rust panic stays visible); the FAIL-line preference may stay.
- F3: classify inner rc 124/137 as "in-container timeout" only when elapsed ≥ 0.9 × timeout; otherwise report the rc.
- F4: pre-flight matches a process whose argv[0] or argv[1] basename is `devcontainer-smoke.sh` (or `bash`/`sh` running
  it), not any cmdline containing the string.
- F6: bound probe/reap error text to 500 chars and never include the inline program.
- F7/F10/F11: fix if one-line; else accept with reason.

## 4. Constraints
No new shell scripts; no inline suppressions. HOST SLOT (hard): before EVERY pytest run,
`mise run bounded-wait -- --deadline 14400 --cmd '! pgrep -f devcontainer-smoke.sh'`; run ONLY
`uv run --project python pytest tests/test_container.py -x -q -n 0`; never full suite, lint, verify or docker.
Run `uv run --project python ty check --project python python/src tests plugins` and ruff on changed files (rc 0).
COMMIT: caller.

## 5. Verification
Targeted pytest rc 0; ty + ruff rc 0. New test for F1: fixture works when `os.defpath` has no git (monkeypatch
`shutil.which` / PATH) — mutation: revert to the defpath-only lookup → that test fails. F2 test: non-timeout failure
with cause only on stderr → detail contains the stderr text; mutation: drop stderr → fails. Report every arm's rc.

## 6. Commit
`fix(container): land smoke round 3 — cold-review F1/F2 (+F3/F4/F6)`.

## 7. PREMISES
- P1 `smoke_system` fixture git lookup at `tests/test_container.py:217-219` uses `os.defpath` only.
- P2 `_smoke_output` at `container.py:~222-235` prefers stdout and drops stderr when stdout is non-empty.
- P3 the image ships git only via `conda:git` (`.devcontainer/mise-system.toml:91`), confirmed by the probe above.
- Tickets (not this round): F5 orphaned-pytest pre-flight, F8 cleanup on interrupt, F9 real in-container signal test,
  plus run-9bdd F4 lifecycle smoke reuse, F6 slot coverage for other smoke paths.
