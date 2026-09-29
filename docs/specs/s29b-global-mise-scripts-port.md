> **SUPERSEDED (call site, 2026-09-29b):** the `uv run --project <repo>/python dotfiles-setup …` call site below was
> overturned by `cold-review-ef172a80-2026-09-29.md` (HIGH) and Ray's runtime-source-selector ruling — see
> `docs/specs/mise-native-dotfiles-plan.md` §4.7. The module port itself (`ef172a80`, branch
> `feat/s29b-global-mise-scripts`) is HELD, unshipped.

# Spec S29b-P — port the user-global mise scripts into `dotfiles_setup`

Ruled by Ray 2026-09-29b: "migrate the python scripts in ~/.config/mise/scripts/ to this project's python library so
... we have all the python code in one place"; call site = `uv run --project <repo>/python dotfiles-setup …`
(AskUserQuestion, recommended option). Precursor to S29-M (mise-native dotfiles), which will later own where the
global config lives.

## 1. Objective

Move the two user-global scripts into this repo's package, behaviour-preserving, as typed modules with CLI
subcommands and tests:

- `~/.config/mise/scripts/update_claude.py` (the 2026-09-29b version — `--json` classification, synced-scope skip,
  prelude/refresh failure → rc 1) → `python/src/dotfiles_setup/update_claude.py`, CLI `dotfiles-setup update-claude`.
- `~/.config/mise/scripts/mise_update_guard.py` (lock-holder guard + audit log for `update:*` tasks, knowledge-base
  #418) → `python/src/dotfiles_setup/mise_update_guard.py`, CLI `dotfiles-setup mise-update-guard <task> [--check-only]`
  with the SAME argv semantics it has today (read its argparse).

Read both source files in full first; they are outside the repo and NOT in git, so copy their logic, docstrings and
measured-evidence comments faithfully (they are load-bearing history), adjusting only for repo lint/typing.

## 2. Files

- NEW `python/src/dotfiles_setup/update_claude.py`, `python/src/dotfiles_setup/mise_update_guard.py`.
- `python/src/dotfiles_setup/main.py` — register the two subcommands following the existing `bounded-wait` /
  `plugin-remove` pattern (parser registration ~`main.py:1584`, dispatch ~`main.py:2834`).
- NEW `tests/test_update_claude.py`, `tests/test_mise_update_guard.py`.
- Do NOT edit anything under `~/.config/mise` — the coordinator switches the call sites after this merges.

## 3. Interfaces

- `update-claude`: no required args; env `CLAUDE_UPDATE_JOBS`, `CLAUDE_UPDATE_JSON` as today; exit 0 / 1 / 127 as
  today. Keep `classify_json`, `_json_result`, `targets`, `UPDATABLE_SCOPES` as module-level functions/constants.
- `mise-update-guard`: identical positional/flag surface and exit codes to the script; the audit log path and format
  unchanged (`~/.config/mise/update-runs.log`) so existing history stays continuous.

## 4. Constraints

- Zero inline suppressions; ruff + ty clean under repo config; no `shell=True`.
- Tests must not run the real `claude`/`mise`/`lsof` binaries: inject runners (the repo's pattern — see
  `bounded_wait.wait(..., command_runner=...)`) or monkeypatch. Include the 11 `classify_json` cases from the
  coordinator's session (up_to_date, updated, both "refreshed" versionless shapes, `abc→abc` = updated,
  `1.0→unknown` = updated, skipped, up_to_date+refreshFailed = failed, updated+refreshFailed = updated,
  outcome failed, unknown outcome = failed) and exit-code tests for: prelude failure → 1, plugin failure → 1,
  refresh_failed → 1, clean → 0, synced scope skipped and listed in `skipped_scope`.
- Guard tests: live holder → 2 without running the task; stale holder → marker cleared and task run; none → task run;
  audit line appended.
- Work on branch `feat/s29b-global-mise-scripts` from `origin/main` in your worktree. Do not push or ship.

## 5. Verification

`mise run gate -- run lint`, `pytest`, `verify` → rc 0 (note: a nested worktree can fail
`test_session_review.py::test_mise_requirement_task_exposes_required_root_and_configurable_limit` for a location
reason; if so, re-run with `MISE_CEILING_PATHS=<main checkout>/.claude/worktrees` and say so). Arm the positive:
break `classify_json`'s refreshFailed branch and the guard's live-holder refusal → the tests must fail; restore.
Real smoke (read-only): `uv run --project python dotfiles-setup mise-update-guard --help` and
`uv run --project python dotfiles-setup update-claude --help` rc 0.

## 6. Commit

One commit: `feat(update): port user-global update_claude + mise_update_guard into dotfiles_setup`, body citing this
spec, trailers:

```
Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_017U4bhJeNiL2W3F3LNaB3Gz
```

## 7. PREMISES

- P1 Both scripts exist at the stated paths and are self-contained (stdlib only). Verify imports.
- P2 `main.py` registers subcommands via argparse subparsers plus a name→lambda dispatch dict.
- P3 No existing module is named `update_claude` or `mise_update_guard` in `dotfiles_setup`.
- P4 `pyproject.toml` exposes the `dotfiles-setup` console script.
