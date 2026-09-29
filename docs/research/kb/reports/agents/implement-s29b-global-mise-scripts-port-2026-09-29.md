# Implementer report — S29b-P port user-global mise scripts (2026-09-29)

Lane: Claude fallback implementer (codex usage-limited). Spec:
`scratchpad/s29b-global-mise-scripts-port.md`.

Worktree: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/agent-a5777caf9c7dcecd2`
Branch: `feat/s29b-global-mise-scripts` from `origin/main` @ `948ec2e9`.

## Premises

| # | Premise | Verdict | Evidence |
|---|---|---|---|
| P1 | Both scripts exist and are stdlib-only | CONFIRMED | Read in full: `update_claude.py` imports concurrent.futures, json, os, shutil, subprocess, sys, time, pathlib; `mise_update_guard.py` imports argparse, os, shutil, subprocess, sys, time, dataclasses, datetime, pathlib. No third-party imports. |
| P2 | main.py uses argparse subparsers + name→lambda dispatch | CONFIRMED | `setup_parser()` `subparsers = parser.add_subparsers(dest="command")` (main.py:2065); `bounded-wait` parser main.py:1583-1591; dispatch dict `_build_command_handlers` with `"bounded-wait": lambda: sys.exit(...)` main.py:2834. |
| P3 | No existing `update_claude` / `mise_update_guard` module | CONFIRMED | `ls python/src/dotfiles_setup/ \| grep -Ei 'update\|guard'` → only branch_guard/hook_guard/script_guard (control arm: the grep DID match `*_guard.py`, so it discriminates). |
| P4 | pyproject exposes `dotfiles-setup` console script | CONFIRMED | `python/pyproject.toml:45` `dotfiles-setup = "dotfiles_setup.main:main"`. |

## Progress

- premises verified; branch created.
- modules + main.py registration written; ruff check/format rc=0, ty (whole tree as hk runs it) rc=0.
- tests written: 34 passed (tests/test_update_claude.py + tests/test_mise_update_guard.py).

## Files changed

- NEW `python/src/dotfiles_setup/update_claude.py` — faithful port; docstrings + measured-evidence comments kept verbatim. Adjustments only for lint/typing: `print` -> `_say`/`_warn` (`sys.stdout/err.write` + flush; ruff T201); `SUMMARY_PATH` constant -> `summary_path()` read at call time; `_json_result`'s in-loop try/except factored to `_parse_update_line` (PERF203/PLW2901); `main` split into `_update_plugins`/`_summary`/`_report` (C901 max 10). Injected seams: `runner` (argv, timeout)->(rc, out, err) threaded through every function with default `_run_split`; `main(*, runner, which, summary)`. `classify_json`, `_json_result`, `targets`, `UPDATABLE_SCOPES` stay module-level. Summary JSON keys/order and stdout lines unchanged.
- NEW `python/src/dotfiles_setup/mise_update_guard.py` — faithful port; docstring kept. `LOG_PATH` constant -> `log_path()` (same `MISE_UPDATE_LOG` override, same default `~/.config/mise/update-runs.log`, same line format); `datetime.now(timezone.utc)` -> `datetime.now(UTC)` (identical isoformat `+00:00`); LIVE/UNKNOWN refusal body moved to `_refuse` (same messages, same log notes, rc 2). Injectable `GuardEnv` (cache_roots, which, capture, alive, run_task); `main(task, *, check_only=False, env=DEFAULT_ENV)`.
- `python/src/dotfiles_setup/main.py` — imports; `_add_update_subcommands` (called after `_add_pin_parity_subcommand`); dispatch entries `update-claude` / `mise-update-guard` (positional `task`, `--check-only`, same help strings as the script's argparse).
- NEW `tests/test_update_claude.py`, `tests/test_mise_update_guard.py`.
- `tests/TEST-INDEX.md` — two rows (not in the spec's file list; added because the index lists every test file).

## Arm the positive (mutation) — both restored from the staged copy via `git checkout --`

| Mutation | Result |
|---|---|
| `classify_json`: `return "failed" if res.get("refreshFailed") else "current"` -> `return "current"` | `test_classify_json[up_to_date-refreshFailed-is-failed]` FAILED (`'current' == 'failed'`) |
| guard `main`: `if state in {"LIVE", "UNKNOWN"}:` -> `if state == "UNKNOWN":` (drops the LIVE refusal) | `test_live_holder_refuses_with_2_without_running_the_task` FAILED |
| combined run | rc=1, `2 failed, 32 passed`; after restore both original lines grep-count 1 |

## Real smoke (read-only)

| Command | rc |
|---|---|
| `uv run --project python dotfiles-setup mise-update-guard --help` | 0 (usage `[-h] [--check-only] task`) |
| `uv run --project python dotfiles-setup update-claude --help` | 0 |
| failure arm: `dotfiles-setup mise-update-guard` (no task) | 2 (argparse "required: task") |
| real host: `MISE_UPDATE_LOG=<scratchpad> dotfiles-setup mise-update-guard update:all --check-only` | 0, `[guard] state=CLEAR - check-only, nothing cleared, task not run` |
| cross-check: ORIGINAL `~/.config/mise/scripts/mise_update_guard.py update:all --check-only` (same env) | 0, byte-identical line |
| failure arm: `env PATH=/usr/bin:/bin uv run ... dotfiles-setup update-claude` | 127, `claude is not on PATH` (control: `command -v claude` -> `~/.local/bin/claude` under the normal PATH) |

NOT run: a real full `update-claude` (it would update the CLI, every marketplace and every plugin — host-mutating) and a real non-check-only guard run (it would `mise run update:*`). Both are UNVERIFIED end to end; the coordinator's call-site switch is the first real run.

## Gates (all via `mise run gate -- run <name>`, rc captured to file)

| Gate | rc | Result | Log |
|---|---|---|---|
| lint (1st) | 1 | typos: `unparseable` -> `unparsable` (docstring + the `plugin list` error message) | scratchpad/gate-lint.log (overwritten) |
| lint (after fix) | 0 | passed, 19.3s | scratchpad/gate-lint.log; `<worktree>/.agent/gate-results/lint.log` |
| pytest (plain) | 1 | `1 failed, 3486 passed` — ONLY `test_session_review.py::test_mise_requirement_task_exposes_required_root_and_configurable_limit` (`assert ignored.returncode != 0` at :1106: the parent checkout's mise config is discovered above the nested worktree — the location reason the spec anticipated) | scratchpad/gate-pytest.log |
| pytest (`MISE_CEILING_PATHS=/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees`) | 0 | `4089 passed, 2 skipped, 11 deselected in 297.58s` | scratchpad/gate-pytest2.log, scratchpad/gate-pytest2-full.log |
| verify | 0 | `166 passed, 0 failed, 4 skipped` (the 4 are the human-only `policy.*` suites) | scratchpad/gate-verify.log; `<worktree>/.agent/gate-results/verify.log` |
| pre-commit hook (hk, on `git commit`) | 0 | every step ✔ incl. ruff, ruff_format, py_ty, no_lint_skip, typos, agnix, md_size_budget, token-audit | commit output |

## Commit

- SHA `ef172a80` on `feat/s29b-global-mise-scripts` (parent `948ec2e9` = origin/main at fetch), 6 files, +1548.
- Worktree: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/agent-a5777caf9c7dcecd2`. Not pushed, not shipped.

## Deviations / left undone

- `tests/TEST-INDEX.md` got two rows (outside the spec's file list).
- The ported `mise-update-guard --help` shows only the argparse help strings, not the script's full-docstring `description=` (the flag/positional surface and exit codes are identical; the docstring lives in the module).
- One user-visible string changed: `unparseable` -> `unparsable` (typos gate; no suppression).
- Unverified end to end (host-mutating, deliberately not run): a real `update-claude` run and a real non-`--check-only` guard run. The first real run will be the coordinator's call-site switch in `~/.config/mise` (untouched here).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the port, tests and gates (branch `feat/s29b-global-mise-scripts`).
