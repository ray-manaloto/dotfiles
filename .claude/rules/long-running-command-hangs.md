# Long-Running Commands: Never Run Blind — Bound Every Run

Any command that can block on network, IO, a lock, or a prompt MUST be
run with a hard time bound and an observable log. Never start a
potentially-slow command and then wait on it indefinitely.

## Why this rule exists

Session 2026-06-29: a `hk run pre-commit --all --stash none` invocation
hung at **0% CPU with no child processes for ~7 hours** before it was
noticed. hk has no native timeout, so nothing aborted it. Worse, the run
had been launched as `hk ... 2>&1 | tail -40`, so when it was finally
killed the pipeline reported **exit 0** (tail's exit code) — masking the
fact that the gate never actually passed. Two traps in one incident:
unbounded wait + pipe-masked exit code.

## Rules

1. **Use `mise run lint`, not raw `hk run pre-commit`.** `mise run lint`
   wraps hk in an out-of-process hard timeout (hk has none of its own —
   verified against hk 1.46 and the live v1.48 docs: no `--timeout` flag,
   no `timeout` step key, no `HK_*` timeout env var). On expiry it kills
   hk's whole process group and prints the tail of the debug log. Default
   600s; override with `--timeout <secs>` or
   `DOTFILES_LINT_TIMEOUT=<secs> mise run lint`. Source:
   `python/src/dotfiles_setup/lint.py`.

2. **For any command expected to exceed ~30s, never wait blind.** Either
   bound it with a timeout, or run it in the background and monitor its
   debug log: hk → `~/.local/state/hk/hk.log` (or the per-run
   `HK_LOG_FILE` that `mise run lint` sets), mise →
   `~/.local/state/mise/mise.log` (`MISE_LOG_FILE`, debug level set in
   `mise.toml [env]`). Use a count-diff monitor loop, not a fixed sleep.

3. **Preserve real exit codes — never `cmd 2>&1 | tail -N` to capture.**
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
   `~/.local/state/hk/`. After editing `hk.pkl`, clear the pkl config
   cache (`rm -rf ~/Library/Caches/hk/configs/`) — see `ci-local-parity.md`.

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
