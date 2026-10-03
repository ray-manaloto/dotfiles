# codex review lens (gpt-6-astra, xhigh) — coordinator-auto-handoff 21e46a08

Command: `mise exec -- codex exec -s read-only --ignore-rules review --commit 21e46a08 -c sandbox_mode="read-only" -m gpt-6-astra -c review_model="gpt-6-astra" -c model_reasoning_effort="xhigh"`, rc=0, codex 0.160.0.

## Report (verbatim)


codex
Successful handoffs can launch duplicate successors, and cross-worktree retirement cannot locate its state. Deferred naming also mishandles the current runtime API and rename failures. Both Bun harnesses passed; Python validation was blocked by the read-only sandbox.

Full review comments:

- [P1] Stop retrying after a successor launches successfully — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/coordinator-auto-handoff-20261002/python/src/dotfiles_setup/coordinator_handoff.py:252-259
  If a successful handoff grows context from 30% to at least 35%, the measurement after that turn fires another handoff: `_judge` checks only `last_fired`, ignoring the successor already launched. The skill can then spawn a second coordinator and overwrite the first launch's census. Persist successful launch completion and suppress subsequent handoffs for that old session, retaining stepped retries only when the handoff fails.

- [P2] Share launch state with the main-checkout successor — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/coordinator-auto-handoff-20261002/python/src/dotfiles_setup/coordinator_handoff.py:837-840
  When the old coordinator runs in a linked worktree, this default stores its launch record and census there. However, `launch` starts the successor in the main checkout, and its brief's retirement command omits `--state-dir`. Retirement therefore reads a different directory and returns rc 2, leaving the old coordinator running. Resolve a shared state location or pass the exact state directory to the successor; machine-local artifacts are not inherited across worktrees ([artifact-isolation rule](.claude/rules/agent-artifact-conventions.md#L62-L65)).

- [P2] Extract text from the current completion result — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/coordinator-auto-handoff-20261002/.claude/skills/session-start/hooks/register.ts:144-146
  Claude Code 2.1.288, the runtime targeted by this change, returns a `ModelCompleteResult` object containing `isAnswered`, `text`, and `usage`, not a string. Passing it to `toSlug` throws, so even successful completions silently produce the fallback `.session` name. Check `isAnswered` and use `reply.text`. The string-only harness masks this incompatibility; validate the real integration as required by the [integration-evidence rule](.claude/rules/real-integration-evidence.md#L6-L11).

- [P2] Record deferred naming only after rename succeeds — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/coordinator-auto-handoff-20261002/.claude/skills/session-start/hooks/register.ts:149-155
  If `/rename` rejects, `queue` reports the rejection but immediately returns, so this path still records `renamed` and overwrites the error status with `session-start ok (renamed)`. Subsequent reloads then discard the pending prefix even though the session was never renamed. A rejection control reproduces both the false success status and persisted completion. Record completion and display success only after the command resolves successfully.
Successful handoffs can launch duplicate successors, and cross-worktree retirement cannot locate its state. Deferred naming also mishandles the current runtime API and rename failures. Both Bun harnesses passed; Python validation was blocked by the read-only sandbox.

Full review comments:

- [P1] Stop retrying after a successor launches successfully — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/coordinator-auto-handoff-20261002/python/src/dotfiles_setup/coordinator_handoff.py:252-259
  If a successful handoff grows context from 30% to at least 35%, the measurement after that turn fires another handoff: `_judge` checks only `last_fired`, ignoring the successor already launched. The skill can then spawn a second coordinator and overwrite the first launch's census. Persist successful launch completion and suppress subsequent handoffs for that old session, retaining stepped retries only when the handoff fails.

- [P2] Share launch state with the main-checkout successor — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/coordinator-auto-handoff-20261002/python/src/dotfiles_setup/coordinator_handoff.py:837-840
  When the old coordinator runs in a linked worktree, this default stores its launch record and census there. However, `launch` starts the successor in the main checkout, and its brief's retirement command omits `--state-dir`. Retirement therefore reads a different directory and returns rc 2, leaving the old coordinator running. Resolve a shared state location or pass the exact state directory to the successor; machine-local artifacts are not inherited across worktrees ([artifact-isolation rule](.claude/rules/agent-artifact-conventions.md#L62-L65)).

- [P2] Extract text from the current completion result — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/coordinator-auto-handoff-20261002/.claude/skills/session-start/hooks/register.ts:144-146
  Claude Code 2.1.288, the runtime targeted by this change, returns a `ModelCompleteResult` object containing `isAnswered`, `text`, and `usage`, not a string. Passing it to `toSlug` throws, so even successful completions silently produce the fallback `.session` name. Check `isAnswered` and use `reply.text`. The string-only harness masks this incompatibility; validate the real integration as required by the [integration-evidence rule](.claude/rules/real-integration-evidence.md#L6-L11).

- [P2] Record deferred naming only after rename succeeds — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/coordinator-auto-handoff-20261002/.claude/skills/session-start/hooks/register.ts:149-155
  If `/rename` rejects, `queue` reports the rejection but immediately returns, so this path still records `renamed` and overwrites the error status with `session-start ok (renamed)`. Subsequent reloads then discard the pending prefix even though the session was never renamed. A rejection control reproduces both the false success status and persisted completion. Record completion and display success only after the command resolves successfully.
rc=0

## GitHub repos touched

_None._
