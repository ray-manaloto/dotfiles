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
| `unix/home/.zshenv`, `unix/home/.config/zsh/` (`.zprofile`, `.zshrc`, `.zshrc.d/`, `path.zsh`), or a new `.zprofile.d/` | `mise run //python:test` |
| `unix/home/.config/starship.toml` | `mise run //python:test` |
| anything else under `python/`: `src/`, `tests/`, `pyproject.toml`, `uv.lock`, `mise.toml` | `mise run //python:test` |
| `shell:apply`, `shell:rollback` or `shell_backup_paths` in `mise.toml`, `python/repo/src/repotools/shell.py` | `mise run //python:test` |
| `python/toolchains/p2996/` | `mise run //p2996:check` |
| `python/repo/` | `mise run //repo:check` |
| `typescript/` | `mise run //typescript:test` |
| `cpp/` | `mise run //cpp:test` |
| `python/jbctl/`, `swift/` (jbctl, jbax) | drive the CLIs against a running JetBrains IDE, headless only: `python/jbctl/.venv/bin/jbctl resolve --ide clion`, `python/jbctl/.venv/bin/jbctl check-direct --ide clion`, `python/jbctl/.venv/bin/jbctl settings-open --ide clion --page "Exposed Tools"` then `python/jbctl/.venv/bin/jbctl settings-press --ide clion --label Cancel` (`settings-open` refuses while a Settings window is already open, and `settings-press`/`settings-goto` refuse a window `settings-open` did not open: it may hold the owner's unapplied edits, so ask them to close it rather than pressing anything), and `~/.local/bin/jbax windows <pid>` (`mise run //swift:install` first). `python/jbctl/.venv/bin/jbctl status` is read-only and always safe. `start`, `stop` and `restart` quit or bring forward a real IDE: run them only as `mise run //jbctl:lifecycle <spare ide>` (e.g. rustrover, never the IDE the owner works in), with the owner's go, after the owner has added `~/.local/state/jbctl/lifecycle-projects` to that IDE's Trusted Locations. `start` and `restart` refuse without `--foreground`, and `stop --check`/`restart --check` run every guard but send nothing: both are safe to check headless with `JETBRAINS_FOREGROUND` cleared (`env -u JETBRAINS_FOREGROUND`), since an inherited `JETBRAINS_FOREGROUND=1` lets start and restart act. A change to `jbax select` or `router-direct` needs a headless run of that command too: `python/jbctl/.venv/bin/jbctl router-direct --ide clion` applies DIRECT with OK, so run it only with the owner's go. Log `lsappinfo front` while driving: the front app must not change. Never set `JETBRAINS_FOREGROUND=1` or pass `--foreground` without the owner's go for that exact run |
| `python/home/src/hometools/herdr.py`, `unix/home/.config/mise/tasks/herdr/`, `unix/home/.local/bin/hc-safe`, or herdr-core and Herdr.app on this Mac | `mise run //home:herdr-unit`, then the **Herdr core** section below |
| any other task: `tasks/privacy/`, `tasks/review/`, `hk.pkl`, a task in a `mise.toml` | that task itself, through `mise run`, on an input that reaches the change |

A change to the shell tests is verified here: they are the instrument, and a broken instrument
passes broken shells. Run the row for every path the diff touches. Docs alone (`*.md`, comments)
have no runtime surface: report SKIP with that reason.

`//python:test` runs every file in `python/tests`: the startup tests (`test_shell_startup.py`),
the shell tasks (`test_shell_apply.py`) and the keys typed into zsh (`test_shell_interactive.py`).
The interactive tests need `tmux` and `starship` on PATH, as the global mise config installs them.

## Herdr core

The doctor reads herdr-core from outside and never runs `hc` (docs/agents/herdr-core.md):

```
mise run herdr:doctor
```

It prints one JSON line and exits 0 when every check passes, 1 when one fails and 3 when one is
`unknown` and none failed. Quote the `checks` object and every failing or unknown ID with the
`observation` fields that explain it. For a doctor change not yet applied, run the checkout's own
task as `//home:integration` does: a copy of `~/.config/mise` whose `tasks` links to this checkout,
passed as `MISE_CONFIG_DIR`.

The doctor can't see two checks from outside: V6, the environment the core's terminals inherit
(`cutover.py receipt v6`), and V8, a Dock launch reaching the core (`cutover.py receipt v8`, the
owner's attestation). Both are cutover gate checks. They come from the cutover script in
`~/.local/state/dotfiles/herdr-update-socket/<drain folder>/cutover.py`, as do the checks that need
a live agent (V9, V12, V13) and V14, which is reported and never decides done. The script talks to
the core only through `hc-safe <core pid> <socket> -- <hc args>`. When that folder is absent,
report V6, V8, V9, V12, V13 and V14 each as SKIP: cutover only. Never run bare `hc`, `herdr-core` or `herdr-app`, never `hc send`
to a shell, and never open Herdr.app from an agent shell: each can start a second core, or give the
window this session's environment. `hc-safe` exit 82 is BLOCKED (a sandbox that can't nest, as in
a Codex `-s read-only` shell), never a pass and never a reason to retry another way.

## 3. Run and capture

Run the task and keep its output. unittest ends with `OK`, or `FAILED (failures=N, errors=M)`
and the task exits non-zero. Quote the summary and the name and first lines of every failure.

The task is the shell probe: the startup tests copy the tracked files into a temporary HOME and
start zsh the four ways a shell starts (login and not, interactive and not), and the interactive
tests type into it. Don't hand-run zsh in `mise run scratch:env`: it gives an empty HOME without
the tracked files, so its output says nothing about them. Never touch the live `~/.zshenv`, `~/.config/zsh` or the
other live startup files.

## 4. Report

- **PASS**: every task the diff calls for ended `OK` or exit 0.
- **FAIL**: any task failed. Quote the failing test names and their messages.
- **BLOCKED**: a task could not start (mise, tmux or starship missing). Say exactly where it stopped.
- **SKIP**: docs only.

List each task run with its result line, then anything you noticed while running it.
