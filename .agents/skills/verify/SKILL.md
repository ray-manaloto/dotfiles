---
name: verify
description: Runtime-verify a dotfiles change at its real surfaces — the mise tasks, the PreToolUse guard's hook entrypoint, the AgentsView daemon — without re-running CI. Use after a merge or before a ship when the change touches session tooling, the guard, or the devcontainer gates.
---

# Verify — drive the surfaces, capture what they print

The surface of almost every change here is a `mise run <task>` (a thin
caller of `dotfiles-setup`), the PreToolUse guard, or the devcontainer.
Tests and `ty` are CI's evidence; this skill is about observation. Every
probe writes to a file and reads the recorded `rc` — never a piped tail.

## Recipe that worked (2026-09-17, Phase 7)

| surface | drive it | expect |
|---|---|---|
| guard | `printf '%s' '{"tool_name":"Bash","tool_input":{"command":"<CMD>"}}' \| bash scripts/pretooluse-guard.sh` | a deny prints JSON with `"permissionDecision": "deny"`; an allow prints nothing (rc=0 either way) |
| handoff-check | `mise run handoff-check -- <fixture.md>` with a fixture carrying `## Next task`, and one with `NEXT:` inside a fence | `forbidden_task_carrier` for the first; none for the fenced one; `stale_plan_pointer` whenever the plan was edited after the pointer |
| bounded-wait | `mise run bounded-wait -- --file x` (no deadline) · `-- --deadline 3 --interval 1 --cmd 'sleep 47 \| cat'` then `pgrep -f 'sleep 47'` · `-- --deadline 10 --file <path touched 2 s later>` | rc=2 usage · rc=124 `DEADLINE EXPIRED`, 0 survivors · rc=0 `satisfied file` |
| session-orphans | in **bash** (zsh does not word-split `$var`): spawn `sh -c 'deadline=$((SECONDS+600)); while [ $SECONDS -lt $deadline ]; do sleep 5; done' &`, then `mise run session-orphans`, then `mise run session-orphans -- --kill --allow <each OTHER pid>` | the loop as `WAIT-LOOP bounded …`; harness children (MCP servers, `caffeinate`) as `BLOCK OTHER`; after `--kill` the loop pid is gone |
| AgentsView census | `mise run session-agentsview-pass -- --limit 2` · `-- --skill /nonexistent/SKILL.md` | two `AGENTSVIEW PASS` blocks · `UNVERIFIABLE`, rc=2, no `Traceback` |
| session-review isolation | `mise run session-review -- --requirements-only --source-repo-root <tmp git repo>` (no `--output`) | rc=2 `explicit --output is required`; `.agent/session-review.md` sha unchanged |
| session-review report | `mise run session-review` | rc=1 while codex turns are open; the `VERDICT:` block sits after the automation lanes (line ~56), not line 1 |
| renovate validator | `env -i HOME=$HOME PATH=$HOME/.local/bin:$HOME/.local/share/mise/shims:/usr/bin:/bin uv run --project python dotfiles-setup renovate-validate` | rc=0 `RE2 engine confirmed live` — `~/.local/bin` (the `mise` binary) MUST be on that PATH |

## Gotchas

- The guard denies a hand-rolled `gh pr checks --watch`; wait on a merge with
  `mise run bounded-wait -- --cmd 'test "$(gh pr view N --json state --jq .state)" = MERGED'`.
- Anything this harness runs in the background appears in `ps` only as
  `/bin/zsh -c source …/shell-snapshots/snapshot-zsh-….sh`; only an argv-visible
  `sh -c '<loop>'` is classifiable by `session-orphans` (#1171).
- `kill(pid, 0)` succeeds on a zombie; read `ps -o stat=` before calling a
  survivor real.
- `mise ls` can list a version whose install dir has no `bin/`; `mise install -f
  <tool@ver>` repairs it.
- The harness's "completed (exit code 0)" summary lies; read the `rc=` you wrote.
