# Long-Running Commands: Never Run Blind — Bound Every Run

Any command that can block on network, IO, a lock, or a prompt MUST be
run with a hard time bound and an observable log. Never start a
potentially-slow command and then wait on it indefinitely.

## Why this rule exists

Case history: `docs/rules-evidence/long-running-command-hangs.md`.

## Rules

1. **Use `mise run lint`, not raw `hk run check`/`hk run pre-commit`.**
   `mise run lint` runs the **read-only** `hk run check --all` (identical
   to CI — no silent source rewriting; the fix path is `mise run fmt`)
   wrapped in an out-of-process hard timeout, because **hk has none of
   its own**. On expiry it kills hk's whole process group and prints the
   debug-log tail. Default 600s; override with `--timeout <secs>` or
   `DOTFILES_LINT_TIMEOUT=<secs>` (source: `lint.py`, See also).

2. **For any command expected to exceed ~30s, never wait blind.** For a file or
   command condition use `mise run bounded-wait -- --deadline <s> (--file <path> | --cmd '<sh -c>')`.
   Its deadline is mandatory and expiry returns rc=124 with the awaited target;
   a `--file` that already exists as a device, FIFO or socket (`/dev/null`) is
   refused with rc=2, because that wait could only succeed.

   **Mac-side container ops** (`mise run ship`/`land`, `verify-local`,
   `sync`, image pulls): from the main conversation, launch them with the
   harness `run_in_background` and a file-captured rc
   (`… > "$LOG" 2>&1; echo "rc=$?" >> "$LOG"`), then read the `rc=` line
   when the completion notice arrives — the command keeps running after the
   turn ends. A foreground subagent's background commands stop at its final
   response, so a subagent keeps its turn engaged with a bounded poll:
   `deadline=$((SECONDS+540)); while [ $SECONDS -lt $deadline ]; do grep -qs RC "$LOG" && break; sleep 15; done`

   Preserve that `deadline`. The wait-loop guard accepts a bound only when the
   loop condition compares `SECONDS`, `deadline`/`DEADLINE`/`end`, or
   `date +%s`, or when command position wraps the loop with `timeout <n>` or
   `mise run bounded-wait`. ⚠️ On this Mac host `timeout` is an unversioned mise
   shim that exits 1 ("No version is set for shim: timeout"): bound host commands
   with `bounded-wait` or a `SECONDS` deadline; `timeout <n>` only in-container or
   in CI. A comment, `--connect-timeout`, path containing
   `timeout`, or out-of-condition deadline assignment is not a bound. The
   separate `backgrounded mise run` guard still denies `&`-detached or `nohup`
   mise tasks; `&&` and `2>&1` remain allowed.

   **CI/remote waits**: `ship` arms auto-merge (GitHub waits on `ci-gate`),
   and `land` waits on main CI after the merge (see `gh-cli-watch.md`).

   For `mise run lint`, the symlink
   **`~/.local/state/dotfiles/hk-lint-<hash>.log`** names only the most recent
   run; with two live, read the exact path each logs at start. The hk state log
   is different and usually stale. mise → `~/.local/state/mise/mise.log`.
   Count-diff monitor, not a fixed sleep.

3. **Preserve real exit codes — never `cmd 2>&1 | tail -N` to capture.**
   *Machine-enforced since 2026-07-21* — the PreToolUse guard denies a
   pipe-to-`tail`/`head` on a **gate** command (`hook_guard` rule `gate command
   piped to head/tail`), and since 2026-09-29 on a direct `ruff`/`ty` run (`lint
   tool piped to head/tail`). Non-gate diagnostics (`git log | head`) pass. Bash
   returns the *last* pipeline command's exit code (tail's `0`), swallowing the
   upstream failure or kill. Redirect to a file (`cmd > /tmp/out.log 2>&1; echo
   "rc=$?" >> /tmp/out.log`) and read the file + the recorded `rc`.

4. **A stalled process is a hang — kill it, don't keep waiting.** A
   process sitting at 0% CPU with no children for minutes is wedged
   (blocked on a lock, stdin, or a dead socket), not working. Kill it
   (and its process group), then diagnose from the log tail. Re-running
   under a timeout is cheaper than waiting on a corpse.

5. **hk specifics.** hk parallelises via per-file read/write locks
   *within* a run; a crashed/killed run can leave stale state under
   `~/.local/state/hk/`. The pkl-eval cache is content-hashed, so editing
   `hk.pkl` needs no cache clearing.

6. **A scary log line next to a hang is not the hang.** Confirm a suspect by
   removing it and re-probing (the #268 wedge was `depends` + `fail_fast =
   false`, now blocked by `no_hk_depends`; its red herrings are in the evidence
   file). When lint hangs, run `uv run --project python ruff check` directly —
   it takes seconds and separates your own code from hk's scheduling.

7. **Find the wedged step by name.** Grep the lint output for a
   `❯ <step>` with no matching `✔ <step>` — that names it directly,
   without reading the whole debug log.

## Applies to

`hk` (use `mise run lint`), `mise install`, `docker buildx`/`devcontainer
up`, `gh` waits (see `gh-cli-watch.md`), and any other
network- or IO-bound command an agent or human launches in this repo.

## See also

- `python/src/dotfiles_setup/lint.py` — the guarded hk runner.
- `gh-cli-watch.md` — sibling rule: auto-merge and land own CI waits; never sleep-poll.
- `ci-local-parity.md` — every CI lint step has a local hk equivalent.
- Memory: `feedback_long_running_tail_logs`, `feedback_pipe_kills_exit_code`.
- CLAUDE.md → `AGENTS.md` "Validate before committing" — prefer `mise run lint`.
