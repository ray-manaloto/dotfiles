# Review spec: does `mise run ship`'s host pytest step run every test?

Requested by Ray via lane saved-searches-1502, 2026-10-03 ~23:50 CDT. REVIEW mode: research and
propose; do NOT edit any tracked file, commit, push, or open PRs.

## Objective

Find the root cause (file:line) of why `mise run ship`'s host-side pytest step passed at a commit
where full-suite tests fail on the Mac host, and propose options with PRO/CON and citations, ending
with ONE recommendation for Ray to rule on.

## Evidence (inherited — re-derive what you rely on)

- 1502's first main-checkout ship (head 74c62091) failed ONLY at gate `sync-full` (in-container smoke
  pytest) on `tests/test_codec.py::test_no_module_outside_the_codec_calls_msgspec_directly`. The
  host pytest step "didn't catch it": `/Users/rmanaloto/.claude/jobs/328111a4/tmp/ship-1502.log`
  lines ~1822-1838 (read the whole host-pytest section of that log, not just those lines).
- Same test run directly on the Mac host at the same commit FAILS (rc=1): in the saved-searches-1502
  worktree (find it with `git worktree list`), `.agent/kb/raw/saved-searches-1502/codec-test.log`.
- At that commit, 3 real-generator tests in `tests/test_codegen_check.py` also failed on host; fixed
  in b0774dc1.

## Hypotheses to confirm or refute (cite code for each verdict)

1. host step runs a subset (changed-file selection, markers, `-k`, testmon-style selection);
2. `-x` / xdist interaction reports a different rc;
3. the wrong rc is read (pipe, wrapper, background notification);
4. cwd/project makes these tests deselected or uncollected (e.g. `--project python` rootdir/testpaths);
5. anything else (e.g. ship's pytest is the pre-push hook's selection, or a gate is skipped by cache).

Starting points: `mise.toml` `[tasks.ship]` (and `gate`, `test`), `python/src/dotfiles_setup/` (ship,
gate, pytest runners, pre-push), `python/pyproject.toml` pytest addopts/markers, `hk.pkl` pre-push
steps, `tests/conftest.py`.

## Options to evaluate (at minimum)

- always run the full suite on ship;
- add a selection-coverage check (e.g. assert selected == collected, or log deselected count);
- make the in-container smoke authoritative / move it earlier;
- any native pytest/hk feature that already solves this (`.claude/rules/use-tool-builtins.md`).

Each option: PRO, CON, cost (wall time on this Mac), citations (file:line, URLs).

## Constraints

- HOST SLOT: another heavy run owns the host. Do NOT run the full pytest suite, `mise run lint`,
  `mise run verify`, `ship`, `land`, or any container op. Single-test `uv run --project python pytest
  <one nodeid>` and `--collect-only` runs are allowed.
- No `gh pr create/merge`, no pushes, no file writes outside your output.
- Never print environment dumps or credential values.

## Verification / output

Final output: root cause with file:line and the probe that proves it (with its control arm, per
`.claude/rules/probes-need-a-control-arm.md`), hypothesis verdict table, options table, ONE
recommendation, and a `## GitHub repos touched` section.

## COMMIT

caller (none in review mode).
