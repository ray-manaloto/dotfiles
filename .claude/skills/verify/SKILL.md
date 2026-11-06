---
name: verify
description: Verify a dotfiles change by running the real thing it touches. Zsh startup files, the starship config, the shell tasks and the shell tests are verified by the shell tests, which start real zsh in a scratch HOME and type keys into it through tmux. Use for /verify, and before committing a change with a runtime surface.
---

# Verify a dotfiles change

The shell tests are this repo's runtime surface for the shell. They do not mock zsh: each one
starts `/bin/zsh` with the tracked startup files in a temporary HOME, or drives a real zsh in a
tmux terminal and reads the screen. Running them is verifying the shell, not re-running CI.

Run everything through mise tasks, which run uv underneath. Never run bare `python`, `pytest` or
`uv`, and never write a shell script to drive a check.

## 1. Find the change

```
git fetch origin main
git status --short
git diff HEAD --stat
git diff origin/main... --stat
```

State how many commits the range has. The diff is the ground truth; a description is a claim
about it.

## 2. Pick the surface

| The change touches | Run, from the repo root |
|---|---|
| `unix/home/.zshenv`, `.zprofile`, `.zshrc`, `.zshrc.d/`, `.config/zsh/`, or a new `.zprofile.d/` | `mise run //python:test` |
| `unix/home/.config/starship.toml` | `mise run //python:test` |
| anything else under `python/`: `src/`, `tests/`, `pyproject.toml`, `uv.lock`, `mise.toml` | `mise run //python:test` |
| `shell:apply`, `shell:rollback` or `shell_backup_paths` in `mise.toml`, `python/repo/src/repotools/shell.py` | `mise run //python:test` |
| `python/toolchains/p2996/` | `mise run //p2996:check` |
| `python/repo/` | `mise run //repo:check` |
| `typescript/` | `mise run //typescript:test` |
| `cpp/` | `mise run //cpp:test` |
| any other task: `tasks/privacy/`, `tasks/review/`, `hk.pkl`, a task in a `mise.toml` | that task itself, through `mise run`, on an input that reaches the change |

A change to the shell tests is verified here: they are the instrument, and a broken instrument
passes broken shells. Run the row for every path the diff touches. Docs alone (`*.md`, comments)
have no runtime surface: report SKIP with that reason.

`//python:test` runs every file in `python/tests`: the startup tests (`test_shell_startup.py`),
the shell tasks (`test_shell_apply.py`) and the keys typed into zsh (`test_shell_interactive.py`).
The interactive tests need `tmux` and `starship` on PATH, as the global mise config installs them.

## 3. Run and capture

Run the task and keep its output. unittest ends with `OK`, or `FAILED (failures=N, errors=M)`
and the task exits non-zero. Quote the summary and the name and first lines of every failure.

The task is the shell probe: the startup tests copy the tracked files into a temporary HOME and
start zsh the four ways a shell starts (login and not, interactive and not), and the interactive
tests type into it. Don't hand-run zsh in `tasks/scratch/env.sh`: it gives an empty HOME without
the tracked files, so its output says nothing about them. Never touch the live `~/.zshrc` or the
other live startup files.

## 4. Report

- **PASS**: every task the diff calls for ended `OK` or exit 0.
- **FAIL**: any task failed. Quote the failing test names and their messages.
- **BLOCKED**: a task could not start (mise, tmux or starship missing). Say exactly where it stopped.
- **SKIP**: docs only.

List each task run with its result line, then anything you noticed while running it.
