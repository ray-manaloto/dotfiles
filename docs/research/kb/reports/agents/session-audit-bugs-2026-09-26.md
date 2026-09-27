<!-- verbatim -o output of `codex exec -s read-only --ignore-rules review --base 12a34e88` on docs/session-2026-09-26-handoff (Brief O), session dotfiles-20260926.000 -->

The new fetcher leaves gaps in process cleanup and wall-clock timeout enforcement. Runtime validation was blocked by mise and uv writes prohibited by the read-only sandbox.

Full review comments:

- [P2] Forward termination signals to detached source processes — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/research_fanout.py:340-345
  If the CLI receives SIGTERM or SIGHUP, `start_new_session=True` prevents its source processes from receiving the caller's process-group signal. Only KeyboardInterrupt triggers cancellation, so the parent exits while gh, ctx7, firecrawl, or last30days continues running without its timeout supervisor. Install CLI-level termination handlers that perform bounded group cleanup before exiting, preserving the repository's [hard-bound requirement](.claude/rules/long-running-command-hangs.md#L3-L5).

- [P2] Enforce the deadline while opening the HTTP response — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/research_fanout.py:422-424
  If a server or proxy trickles response-header bytes, `urlopen` can remain blocked beyond `--timeout`: its socket timeout limits inactivity, not total elapsed time. The bounded body reader starts only after headers finish, and executor shutdown waits for this worker, delaying every source's persisted result. Apply the wall-clock deadline to opening the response as well as reading its body, consistent with the [hard-bound requirement](.claude/rules/long-running-command-hangs.md#L3-L5). Both HTTP endpoints have this gap.

- [P2] Kill surviving group members after the leader exits — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/research_fanout.py:294-298
  When a timed-out tool has an in-group descendant that ignores SIGTERM and redirects stdout/stderr, terminating the leader lets `communicate()` succeed immediately. This early return then skips SIGKILL even though the descendant remains alive, so the source reports `timed out` while its work continues. Complete group termination independently of leader exit and pipe completion, preserving the [hard-bound requirement](.claude/rules/long-running-command-hangs.md#L3-L5).