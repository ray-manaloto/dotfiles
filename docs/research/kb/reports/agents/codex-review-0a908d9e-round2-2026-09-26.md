<!-- verbatim -o output of `codex exec -s read-only --ignore-rules review --commit 0a908d9e`, session dotfiles-20260926.000 -->

The subprocess rewrite introduces timeout-cleanup and cancellation regressions. Python validation was blocked by read-only uv cache restrictions; git diff --check passed.

Full review comments:

- [P2] Bound the final pipe drain after killing the process group — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/research_fanout.py:258-261
  If a CLI spawns a descendant that starts its own session while retaining stdout or stderr, that descendant survives both group signals and keeps the pipes open. The final unbounded `communicate()` then blocks past `--timeout`, preventing the entire fanout from writing its manifest. Previously, POSIX `subprocess.run(timeout=...)` killed and waited for the direct child without draining those pipes. Bound the cleanup and close the pipes when necessary, preserving the hard-time-bound requirement in [long-running-command-hangs.md](.claude/rules/long-running-command-hangs.md#L3-L5).

- [P2] Forward cancellation to the detached subprocess groups — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/research_fanout.py:249-252
  When a user presses Ctrl-C during a CLI fetch, the new session prevents that child from receiving the terminal's SIGINT. Meanwhile, `_fan_out_with_raw()` waits for its workers during `ThreadPoolExecutor` shutdown, and group cleanup only runs on `TimeoutExpired`. Consequently, cancellation now leaves fetchers running until their normal deadline—potentially 180 seconds for last30days—instead of interrupting them with the parent. Add cancellation handling that terminates active child groups before waiting for executor shutdown.