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
   debug log. **EXCEPTION — Mac-side container ops: background-and-idle gets
   them REAPED.** `mise run ship`/`land`, `verify-local`, `sync`, and image
   pulls are killed if the turn goes idle waiting on them, so "background it"
   — the default advice above — is precisely wrong here and cost a killed
   20-minute image pull (2026-07-16). Measured both ways: a foreground 10-min
   bound also killed a `ship` mid-`shellcheck` (rc=143). What works is
   **in-turn polling** — background the command, then keep the turn engaged
   reading its log until it finishes:

   ```bash
   deadline=$((SECONDS+540))
   while [ $SECONDS -lt $deadline ]; do grep -q RC "$LOG" && break; sleep 15; done
   ```

   **Backgrounding stays correct for CI/remote waits** (`gh pr checks --watch`,
   `gh run watch`) — those run on GitHub's infrastructure, not this Mac, and
   nothing local reaps them. The hazard is specifically local, long, Mac-side
   work. See `feedback_long_mac_ops_keep_turn_engaged`, which this rule used to
   contradict outright. For a `mise run lint` run the log is
   **`~/.local/state/dotfiles/hk-lint.log`** — the per-run `HK_LOG_FILE`
   the wrapper sets (`lint.py` `DEFAULT_LOG_FILE`). Read THAT one:
   `~/.local/state/hk/hk.log` is a *different* file written by other hk
   entrypoints (e.g. the pre-push hook) and is typically stale, which
   makes a live hang look idle (misread 2026-07-14). mise →
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
   `~/.local/state/hk/`. (The old "clear ~/Library/Caches/hk/configs/
   after editing hk.pkl" guidance is retired — the cache is
   content-hashed since hk 1.47; see `ci-local-parity.md` rule 5.)

6. **The ruff-error wedge is FIXED (#268) — and its published diagnosis
   was wrong.** A ruff violation now fails `mise run lint` with `rc=1`
   and a `✗ ruff` summary. Root cause was **`depends` + `fail_fast =
   false`**, not ruff: hk never releases a dependent whose dependency
   FAILED, so `ruff_format` (which we had given `depends = List("ruff")`)
   sat at `waiting for ruff` forever. Fixed by ordering with `exclusive
   = true` instead; `hk.pkl`'s `no_hk_depends` step now blocks `depends`
   from coming back. Reproduced on hk 1.50.0 AND 1.51.0 — **not** fixed
   by a bump.

   **Two red herrings this rule itself repeated for two days, both worth
   remembering:**
   - *"The `ruff` step has `fix=true`."* It does not. `fix` on a builtin
     Step is a **command string**; the boolean lives on the **hook**
     (`hk.pkl` `["pre-commit"] { fix = true }`). Same key name, two
     meanings, opposite levels.
   - *"`failed to get write locks …` is the wedge."* It is a **DEBUG-level,
     non-fatal** retry line from whole-repo hygiene steps contending over
     the first file alphabetically; it appears on runs that finish fine.
     The wedge is one line lower: `waiting for <dep>`. **A scary log line
     adjacent to a hang is not the hang** — confirm a suspect by removing
     it and re-probing, which is what finally isolated `depends`.

   The durable habit survives: **when lint hangs, run `uv run --project
   python ruff check` DIRECTLY** — seconds, and it never lies about your
   own code.

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
