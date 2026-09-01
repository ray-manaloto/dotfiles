# Long-Running Commands: Never Run Blind — Bound Every Run

Any command that can block on network, IO, a lock, or a prompt MUST be
run with a hard time bound and an observable log. Never start a
potentially-slow command and then wait on it indefinitely.

## Why this rule exists

Session 2026-06-29: a `hk run pre-commit --all` invocation hung at **0%
CPU with no child processes for ~7 hours** — hk has no native timeout,
so nothing aborted it. It had been launched as `hk ... 2>&1 | tail -40`,
so when it was finally killed **the pipeline reported exit 0** (tail's),
masking the fact that the gate never passed. Two traps in one incident;
both are now operative rules below, and both are guard-enforced.

Case history — the backgrounding reversal, which log file to read, and
the ruff wedge's two published red herrings:
`docs/rules-evidence/long-running-command-hangs.md`.

## Rules

1. **Use `mise run lint`, not raw `hk run check`/`hk run pre-commit`.**
   `mise run lint` runs the **read-only** `hk run check --all` (identical
   to CI — no silent source rewriting; the fix path is `mise run fmt`)
   wrapped in an out-of-process hard timeout, because **hk has none of
   its own**. On expiry it kills hk's whole process group and prints the
   debug-log tail. Default 600s; override with `--timeout <secs>` or
   `DOTFILES_LINT_TIMEOUT=<secs>`. Source:
   `python/src/dotfiles_setup/lint.py`.

2. **For any command expected to exceed ~30s, never wait blind.** Either
   bound it with a timeout, or run it in the background and monitor its
   debug log. **EXCEPTION — Mac-side container ops: background-and-idle gets
   them REAPED.** `mise run ship`/`land`, `verify-local`, `sync`, and image
   pulls are killed if the turn goes idle waiting on them, so "background it"
   is precisely wrong here (measured both ways — a foreground 10-min bound
   also killed a `ship` at rc=143). What works is **in-turn polling** —
   background the command, then keep the turn engaged reading its log:

   ```bash
   deadline=$((SECONDS+540))
   while [ $SECONDS -lt $deadline ]; do grep -q RC "$LOG" && break; sleep 15; done
   ```

   *Machine-enforced since 2026-07-21* — the PreToolUse guard denies a
   `&`-detached `mise run` (`hook_guard` rule `backgrounded mise run`), the
   sibling of the existing `nohup mise run` rule. `&&` and a `2>&1` fd-dup are
   not background operators and stay allowed.

   **Backgrounding stays correct for CI/remote waits** (`gh pr checks --watch`,
   `gh run watch`) — those run on GitHub's infrastructure and nothing local
   reaps them. The hazard is specifically local, long, Mac-side work.

   For `mise run lint` the log is the symlink
   **`~/.local/state/dotfiles/hk-lint-<hash>.log`** (per-workspace). Read
   THAT one — `~/.local/state/hk/hk.log` is a *different*, usually stale
   file, and reading it made a live hang look idle. mise →
   `~/.local/state/mise/mise.log`. Use a count-diff monitor loop, not a
   fixed sleep.

3. **Preserve real exit codes — never `cmd 2>&1 | tail -N` to capture.**
   *Machine-enforced since 2026-07-21* — the PreToolUse guard denies a
   pipe-to-`tail`/`head` on a **gate** command (`hook_guard` rule `gate command
   piped to head/tail`). Non-gate diagnostics (`git log | head`) are untouched.
   Bash returns the *last* pipeline command's exit code (tail's `0`),
   silently swallowing the upstream failure or kill. Redirect to a file
   (`cmd > /tmp/out.log 2>&1; echo "rc=$?" >> /tmp/out.log`) and read the
   file + the recorded `rc`. Trust file content, not a piped tail.

4. **A stalled process is a hang — kill it, don't keep waiting.** A
   process sitting at 0% CPU with no children for minutes is wedged
   (blocked on a lock, stdin, or a dead socket), not working. Kill it
   (and its process group), then diagnose from the log tail. Re-running
   under a timeout is cheaper than waiting on a corpse.

5. **hk specifics.** hk parallelises via per-file read/write locks
   *within* a run; a crashed/killed run can leave stale state under
   `~/.local/state/hk/`. (The old "clear the pkl config cache" guidance is
   retired — content-hashed since hk 1.47; `ci-local-parity.md` rule 5.)

6. **The ruff-error wedge is FIXED (#268), and it was never ruff.** Root
   cause was **`depends` + `fail_fast = false`** — hk never releases a
   dependent whose dependency FAILED, so `ruff_format` sat at `waiting
   for ruff` forever. `hk.pkl`'s `no_hk_depends` step blocks `depends`
   from coming back.

   Generalisation, learned by publishing the wrong diagnosis twice:
   **a scary log line adjacent to a hang is not the hang** (`failed to
   get write locks …` is a benign DEBUG retry; the wedge was one line
   lower). Confirm a suspect by removing it and re-probing. Both red
   herrings: `docs/rules-evidence/long-running-command-hangs.md`.

   Durable habit: **when lint hangs, run `uv run --project python ruff
   check` DIRECTLY** — seconds, and it never lies about your own code.

7. **Find the wedged step by name.** Grep the lint output for a
   `❯ <step>` with no matching `✔ <step>` — that names it directly,
   without reading the whole debug log.

## Applies to

`hk` (use `mise run lint`), `mise install`, `docker buildx`/`devcontainer
up`, `gh` waits (use `--watch`, see `gh-cli-watch.md`), and any other
network- or IO-bound command an agent or human launches in this repo.

## See also

- `python/src/dotfiles_setup/lint.py` — the guarded hk runner.
- `gh-cli-watch.md` — sibling rule: use `--watch`, never sleep-poll.
- `ci-local-parity.md` — hk pkl-cache clearing after `hk.pkl` edits.
- Memory: `feedback_long_running_tail_logs`, `feedback_pipe_kills_exit_code`.
- CLAUDE.md → `AGENTS.md` "Validate before committing" — prefer
  `mise run lint` for the lint gate.
