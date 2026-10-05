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

## Result

F1, F2, F3, F4, F6 and F10 are fixed; F7 and F11 are explicitly accepted below.
The original contract above is preserved. All authorized final Python checks
passed. HOST SLOT forbids the usual lint, lint-docs, verify, full-suite and
Docker gates for this round; none is credited as passed.

F1 now resolves git from `os.defpath` with a PATH fallback, failing clearly
only when both lookups fail. Its fixture regression uses isolated lookup state
to represent the image's PATH-only git installation.

The retry rule now distinguishes completed non-timeout diagnostics from partial
timeout output (F2), records the 90%-of-timeout elapsed classification and its
remaining ambiguity (F3), describes script argv positions rather than arbitrary
cmdline mentions (F4), and records bounded probe/reap errors without the inline
program (F6). Static inspection of the final Python diff agrees with those
four rule changes. F4 tests cover direct script and `bash`/`sh` invocations,
with seven unrelated cmdline-mention forms as refusal controls. F6 tests cover
raw, repr and JSON program echoes, long errors and TimeoutExpired argv omission
through the public verification interface.

F3 early rc 124/137 still performs marker-scoped reap for cleanup safety; only
the elapsed-qualified path claims an in-container timeout. F10 is fixed:
completed failures with empty output say `smoke failed (no output)`; timeout
paths retain `no partial output`.

F7 is accepted: acquiring the heavy slot before resolving container and source
identity preserves the required freshness of those inputs. It can delay a
no-container result, and a slot timeout reports only the failed smoke Check.
Changing that behavior requires a broader decision about identity freshness
and check visibility, beyond this round's small fixes.

F11 is accepted: the existing `:g` duration formatting is harmless at realistic
timeouts. Replacing it with fixed decimal precision can round an allowed tiny
positive timeout to zero; handling every finite positive value accurately is
more than the spec's one-line fix allowance. Scientific notation and six
significant digits remain a known formatting limitation.

Intermediate Python verification: the first combined ruff check/format-check
command exited 1 with line-length and return-count findings. The specialist
corrected those findings; the subsequent ruff format and ruff check commands
each exited 0. Final authoritative commands and results are recorded below.

Python self-review also found an F6 sanitization-order edge: stripping stderr
before replacing the raw inline program can remove its terminal newline and
prevent an exact replacement. The first required HOST SLOT wait exited 0,
then `uv run --project python pytest tests/test_container.py -x -q -n 0`
exited 1 (57 passed, 1 failed in 160.75 seconds): the raw-probe F6 assertion
exposed that ordering defect. The specialist corrected the production sequence
to redact the original stderr before stripping and bounding it. Test refinements
pin elapsed 2.699/2.7 seconds at `<T>=3` for both rc 124/137 and isolate
failed-reap error arms so cleanup state is retained. Post-fix ruff format and
ruff check each exited 0; the final suite passed after these corrections.

F1 realistic fail arm: installing the defpath-only git lookup mutation exited
0; the second required HOST SLOT wait exited 0. The exact targeted pytest
command above exited 1 (1 failed, 9 passed in 11.84 seconds), at
`test_smoke_fixture_uses_path_when_defpath_has_no_git`'s clear missing-git
fixture assertion. Restoring the intended fallback exited 0. The mutation
demonstrates that the new fixture regression test catches the original defect.

F2 realistic fail arm: installing the stderr-drop mutation exited 0; the third
required HOST SLOT wait exited 0. The same exact targeted pytest command
exited 1 (1 failed, 10 passed in 3.97 seconds), at
`test_completed_failure_reports_stderr_only_cause`: stdout progress survived,
but the expected mise Rust-panic stderr cause was absent. Restoring combined
output exited 0. Both required mutations are restored in the final tested files.

Final authorized Python checks:

| Command | rc | Evidence |
|---|---|---|
| `uv run --project python pytest tests/test_container.py -x -q -n 0` | 0 | 72 passed in 89.45 seconds (0:01:29) |
| `uv run --project python ty check --project python python/src tests plugins` | 0 | Required project-wide type check passed |
| `mise exec -- ruff check python/src/dotfiles_setup/container.py tests/test_container.py` | 0 | Changed Python files passed |
| `mise exec -- ruff format --check python/src/dotfiles_setup/container.py tests/test_container.py` | 0 | Both files formatted |

All four pytest invocations were preceded by
`mise run bounded-wait -- --deadline 14400 --cmd '! pgrep -f devcontainer-smoke.sh'`,
each with rc 0. The fourth wait immediately preceded the final successful run.
The Python specialist's owned-file `git diff --check` also exited 0.

F5 (orphaned-pytest pre-flight), F8 (cleanup on interruption), F9 (real
in-container signals), and the earlier lifecycle-reuse/other-smoke-slot tickets
remain outside this round. No real-container or real-signal validation is
claimed. COMMIT remains caller-owned; no commit or push is performed by these
specialists.

Documentation static check: `git diff --check --
.claude/rules/persistence-gate-retry.md
docs/specs/land-smoke-timeout-round3-2026-10-04.md` exited 0 on the final
rule and Result changes. `mise run lint-docs` was **NOT RUN** because the hard
HOST SLOT constraint prohibits lint in this round; documentation lint remains
unverified.
