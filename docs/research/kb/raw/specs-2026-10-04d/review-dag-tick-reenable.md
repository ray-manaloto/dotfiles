# SDLC review request: re-enable the dag-tick LaunchAgent after #1644?

Mode: REVIEW. Do not write to any repository file; write only your output file.
Do NOT run `launchctl`, `claude respawn`, `claude stop`, `claude rm`, or any heavy
gate (pytest suite, `mise run lint`, `verify-local`) — read-only probes only
(`launchctl list`, `launchctl print-disabled`, reading files).

## Context (measured by the session-autostart lane, 2026-10-04)

- #1644 (155bca21, "never stop a DONE session; it may be an idle coordinator") is on main.
- `dev.mise.dotfiles-dag-tick` is NOT loaded (`launchctl list` count 0) and is
  `launchctl disable`d (`print-disabled gui/<uid>` → disabled), which persists across
  logins. Whether `mise bootstrap launchd-agents apply` overrides `disabled` is unverified.
- The plist is still at `~/Library/LaunchAgents/dev.mise.dotfiles-dag-tick.plist`.
- Last log lines (pre-unload) still classified sessions (WEDGED 8d6e7252, NEEDS_HUMAN ×2).
- Consequence: nothing respawns a crashed (DEAD) lane or coordinator now.
- Evidence: `docs/research/kb/reports/agents/session-autostart-2026-10-03.md` on branch
  `feat/session-autostart-recipe` (f9b56da5) — read with `git show f9b56da5:<path>`.

## Scope to read

The dag-tick implementation in `python/src/dotfiles_setup/` (grep `dag_tick`/`dag-tick`),
its tests, the LaunchAgent definition (mise bootstrap config / plist template), and the
coordinator-handoff flow (`python/src/dotfiles_setup/coordinator_handoff.py`).

## Questions

1. Is the post-#1644 tick safe to re-enable? Enumerate every action class it can still
   take (DEAD → `claude respawn`, which was measured to return IDLE; log-only classes)
   and whether any can stop, kill, or mutate a live coordinator, lane, or checkout.
2. Should DEAD recovery use `claude --resume <sid> --bg "<prompt>"` instead of
   `claude respawn`, so a recovered coordinator actually takes a turn? Cite `$CC/` docs
   (`~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`).
3. It runs from the main checkout, so it executes whatever branch is checked out there.
   Does it guard against running a non-`main` tick? Should it?
4. Does `mise bootstrap launchd-agents apply` (or the repo's equivalent) clear a
   `launchctl disable`? Recommend the exact re-enable procedure (host action, for Ray)
   or a reason to keep it off.

## Output

Findings table (severity | claim | file:line | evidence), ranked proposals with PRO/CON,
a single recommended option. End with `## GitHub repos touched`.
