# Host-load implementation receipt — 2026-10-02

Lane `dotfiles-20261002.host-load`, branch `fix/host-load`. Implements all five
recommendations of `host-load-review-2026-10-02.md` (Ray's ruling, 2026-10-02),
plus the xdist knob. Every number below was measured in this lane unless marked.

## What changed

| # | Recommendation | Implementation |
|---|---|---|
| 1 | command-audit off SessionEnd | Removed from `.claude/settings.json` AND `.codex/hooks.json` (codex sessions ran it too). On demand: `mise run command-audit -- --output .agent/command-audit.md`. A second concurrent run exits at once on `host_lock.COMMAND_AUDIT`. |
| 2 | Host-wide heavy-gate lock | `python/src/dotfiles_setup/host_lock.py` (fcntl, `$XDG_STATE_HOME/dotfiles/heavy-gate.lock`). Taken by `gate run lint/pytest/verify`, ship's gates **and push**, and `mise run test-hook-isolated` (the pre-push step) via `dotfiles-setup heavy-gate run`. Re-entrant for descendants (ship -> push -> pre-push). KB side drafted: `docs/handoffs/kb-host-load-followup-2026-10-02.md`. |
| 3 | xdist | `pytest-xdist` added; `pytest.ini` `-n auto --dist loadgroup`; `tests/conftest.py` answers `-n auto` with 4 unless `PYTEST_XDIST_AUTO_NUM_WORKERS` (xdist's own variable, the ONE knob) is set; raise it per clone in `mise.local.toml`. |
| 4 | One suite per ship | `pr.pre_push_runs_suite` (git's own `git hook list pre-push` via `hk_hooks`, and no hk skip env/git config) drops ship's pytest gate; a failing pre-push suite fails `git push`, ship returns before the PR / auto-merge. |
| 5 | Per-tool-call hook cost | One PreToolUse entry (`Bash|AskUserQuestion|Edit|Write|NotebookEdit|Grep|Read|Glob`) -> `/bin/bash scripts/pretooluse-guard.sh` -> `<venv>/bin/python -m dotfiles_setup.hook_dispatch` (guard + graphify nudge, one process; `uv run` fallback; fail-open recorded). `scripts/graphify-hook-guard.sh` deleted. Nudge code moved to the light `graphify_hook` module. |

## Measurements and arms

- **Hook cost** (load ~13, 9 runs, no-op Bash): old guard + graphify hooks
  1191 ms summed process time (they ran in parallel, wall ≈ 640 ms); merged via
  PATH `bash` 321 ms; merged via `/bin/bash` + builtin `read` **149 ms**.
- **Shims:** `bash`, `cat`, `mkdir`, `date`, `dirname`, `git` resolve to mise
  shims on this host (817 shims). `bash -c true` via PATH 210 ms vs `/bin/bash`
  3 ms (7 runs, median). Imports: `dotfiles_setup.main` 0.31 s,
  `dotfiles_setup.graphify` 215 ms, `hook_dispatch` ≈ 55 ms incl. interpreter.
- **Lock arms** (manual, then `tests/test_host_lock.py`): B waits "held by pid A"
  and runs after release; `kill -9` holder -> immediate acquire; busy + 1 s bound
  -> rc 124; child with holder export rc 0 vs the same child with it stripped
  rc 124.
- **command-audit:** busy lock -> rc 0 in 0.63 s, "skipped — … held by pid …";
  free -> scans and writes.
- **Wiring:** `hook selfcheck` rc 0; control arms: a PATH-`bash` command and a
  matcher without `Glob` each fail `check_settings_wiring`.
- **Contracts:** `verify run` 171 passed / 0 failed; new
  `workflow.heavy-gate-lock` goes red when ship's `pre_push_runs_suite` call site
  is replaced by `False` (mutation arm).
- **Suite serial vs parallel:** PENDING the host SLOT.

## Not done here (user-level, Ray's call)

Claude's own `git` calls, the guard's Edit/Write branch check (`git` from
Python), and every other bare tool name go through mise shims (1.88 s vs 0.13 s
for `git --version` under load, review §1c; 210 ms vs 3 ms for `bash` here).
Recommendation: in the user-level shell init, put mise's activated install
paths ahead of `~/.local/share/mise/shims` for interactive shells (i.e. `mise
activate` rather than shims-on-PATH), or prepend `/usr/bin:/bin` for Claude Code
sessions. Not applied: it is a user-level file.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — hooks, `host_lock`, `pr.py`, `gate_result.py`, pytest config
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `mise.toml [tasks.test]`, `kb_setup/gates.py` (read for the follow-up draft)
- [pytest-dev/pytest-xdist](https://github.com/pytest-dev/pytest-xdist) — installed 3.8.0 `plugin.py`/`newhooks.py`
- [jdx/hk](https://github.com/jdx/hk) — skip env/config names (mintlify cache)
