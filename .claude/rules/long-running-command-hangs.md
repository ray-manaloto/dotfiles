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

Case history — the backgrounding reversal, log selection, and the ruff wedge's
red herrings — lives in `docs/rules-evidence/long-running-command-hangs.md`.

## Rules

1. **Use `mise run lint`, not raw `hk run check`/`hk run pre-commit`.**
   `mise run lint` runs the **read-only** `hk run check --all` (identical
   to CI — no silent source rewriting; the fix path is `mise run fmt`)
   wrapped in an out-of-process hard timeout, because **hk has none of
   its own**. On expiry it kills hk's whole process group and prints the
   debug-log tail. Default 600s; override with `--timeout <secs>` or
   `DOTFILES_LINT_TIMEOUT=<secs>`. Source:
   `python/src/dotfiles_setup/lint.py`.

2. **For any command expected to exceed ~30s, never wait blind.** For a file or
   command condition, use the sanctioned helper:
   `mise run bounded-wait -- --deadline <s> (--file <path> | --cmd '<sh -c>')`.
   Its deadline is mandatory and expiry returns rc=124 with the awaited target.

   **Mac-side container ops** (`mise run ship`/`land`, `verify-local`,
   `sync`, image pulls): from the main conversation, launch them with the
   harness `run_in_background` and a file-captured rc
   (`… > "$LOG" 2>&1; echo "rc=$?" >> "$LOG"`), then read the `rc=` line
   when the completion notice arrives — the command keeps running after the
   turn ends. A foreground subagent's background commands stop at its final
   response, so a subagent keeps its turn engaged with a bounded poll:

   ```bash
   deadline=$((SECONDS+540))
   while [ $SECONDS -lt $deadline ]; do grep -q RC "$LOG" && break; sleep 15; done
   ```

   Preserve that `deadline`. The wait-loop guard accepts a bound only when the
   loop condition compares `SECONDS`, `deadline`/`DEADLINE`/`end`, or
   `date +%s`, or when command position wraps the loop with `timeout <n>` or
   `mise run bounded-wait`. A comment, `--connect-timeout`, path containing
   `timeout`, or out-of-condition deadline assignment is not a bound. The
   separate `backgrounded mise run` guard still denies `&`-detached or `nohup`
   mise tasks; `&&` and `2>&1` remain allowed.

   **CI/remote waits** are owned by `mise run ship`/`land`, which watch
   GitHub-side checks themselves (see `gh-cli-watch.md`).

   For `mise run lint`, the symlink
   **`~/.local/state/dotfiles/hk-lint-<hash>.log`** names only the most recent
   run; with two live, read the exact path each logs at start. The hk state log
   is different and usually stale. mise → `~/.local/state/mise/mise.log`.
   Count-diff monitor, not a fixed sleep.

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
- `gh-cli-watch.md` — sibling rule: ship/land own CI waits; never sleep-poll.
- `ci-local-parity.md` — every CI lint step has a local hk equivalent.
- Memory: `feedback_long_running_tail_logs`, `feedback_pipe_kills_exit_code`.
- CLAUDE.md → `AGENTS.md` "Validate before committing" — prefer `mise run lint`.
