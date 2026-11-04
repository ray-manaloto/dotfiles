---
okf_version: "0.2"
type: "report"
title: "Verification of the codebase-memory-mcp install"
description: "Every check run on 2026-11-03 against the live install, with results: file diffs, hooks with and without a daemon, the 12 read-only tools, and headless Claude and Codex sessions running the agents."
package: "github:DeusData/codebase-memory-mcp"
version: "0.12.1"
timestamp: "2026-11-03T23:50:00Z"
status: "draft"
stale_after: "2026-12-03T00:00:00Z"
tags: [codebase-memory-mcp, verification, claude-code, codex]
sources:
  - id: task
    resource: "repo:python/cbm"
---

# Verification of the codebase-memory-mcp install

Runs on 2026-11-03 (Claude Code 2.1.317) and 2026-11-04 (Claude Code 2.1.318, Codex 0.166.0); CBM 0.12.1, mise 2026.11.0.

| Check | Result |
|---|---|
| Package tests (`mise run //cbm:check`: ruff, ty, codegen drift, pytest with a stand-in CBM binary in a temporary HOME) | 52 pass at 100% line and branch coverage: installer failure, start error, Ctrl-C and SIGTERM restore the launcher; a foreign launcher, bad `CBM_CLIENTS` (a repeated client named as the reason, order kept), moved config folders and bad usage are refused; each weakened config fails its own check, and so does an MCP server with another version, a missing read-only tool or non-JSON output |
| Installer exit, binary bytes | rc 0; binary sha256 unchanged (`a36cfa1f…`) |
| Strict file diff against a backup (32 checks) | 31 pass. The FAIL: `enabledPlugins` gained one plugin that another session installed between the backup and the install; kept as a FAIL with that explanation |
| Codex `hooks.state` | gained trust entries for exactly the two CBM hooks (Codex `/hooks` trust) |
| `mise run //cbm:verify` on the live install | 18/18 (2026-11-04), including the live MCP check: initialize and tools/list over stdio through the launcher answered 0.12.1 with 17 tools |
| `mise run //cbm:install` on the live install (the real installer, rerun on 2026-11-04) | rc 0; installer "configuring agents only"; `config set` and all 18 checks pass; launcher restored; no new conflict-log lines; `~/.zshrc` unchanged and no `~/.local/bin` copy, though the installer prints its generic "source ~/.zshrc" line |
| Installer twice in a throwaway HOME (rehearsal) | the second run rewrote the same config files and the file checks passed both times. Both runs still exited 1: `config set` failed because the scratch cache root met the live daemon (`cache_root` conflict). Not an end-to-end idempotence result |
| Index dotfiles main | 2183 nodes, 6754 edges, `status: ready`, 1.5 s |
| 12 read-only tools through `cli`, each with an expected result | 12/12: list_projects, index_status, check_index_coverage, search_graph, get_file_outline, get_code_snippet, trace_path, detect_changes, get_architecture, get_graph_schema, query_graph, search_code (~460 ms each, mostly process start) |
| Hooks, 5 runs each, daemon running | 6/6: SessionStart and SubagentStart return `[codebase-memory]` context; PreToolUse Grep, Bash and Glob return matching graph symbols; a Grep for a missing symbol returns nothing; ~205 ms median |
| Hooks with no daemon (first run, before any session) | rc 0, no context, ~465 ms; hooks never start a daemon (they are connect-only) |
| Headless Claude session in dotfiles | MCP `codebase-memory-mcp` connected; agents codebase-memory, -scout, -auditor and the `codebase-memory` skill listed; the SessionStart hook injected its context; `list_projects` and `index_status` answered |
| The three Claude agents | each ran and called CBM tools (search_graph, trace_path, check_index_coverage); all found the same definition |
| Headless Codex session in dotfiles | `list_projects` and `index_status` answered; the `[codebase-memory]` context line was present; the scout agent answered |
| Daemon conflicts log | no new lines (5 old `cache_root` lines from the retired 0.11.0 setup) |
| Fresh sessions after the switch (2026-11-04) | `claude mcp get codebase-memory-mcp`: user scope, Connected, from the retired repository's checkout and a dotfiles worktree. Headless Claude in each: the server connected (MCP log: 0.12.1) and `list_projects` answered. Headless Codex (`codex exec`, read-only) in each: `list_projects` answered |
| Claude hooks in a fresh session (`--include-hook-events`, indexed dotfiles checkout) | SessionStart: rc 0, "graph project … is indexed" context; PreToolUse Grep: rc 0, "5 graph symbol(s) match" context; PostToolUse Read: rc 0, no context. In an unindexed checkout every hook returns rc 0 and `{}` |
| Hook run time, warm daemon | 5 PreToolUse Grep runs: 0.20-0.21 s each, all with context |

## Found during verification

- A project-scope `.mcp.json` or `.codex/config.toml` entry with the same server name overrides the user-scope
  entry. The retired repository's entries did, and a review session there saw the old 0.11.0 server with 0
  projects. Those entries were removed.
- Running Codex sessions picked up the new server through the launcher before any restart.

## Open

- Recovery after a stdio MCP server exits mid-session (for example after a forced upgrade). One data point: a
  Claude Code 2.1.317 session whose retired 0.11.0 server was killed later listed it as failed to connect, with no
  reconnect attempt in its MCP log, and it never loaded the user-scope entry added after it started. New sessions
  connect. Claude Code offers `/mcp reconnect <server>|all`; Codex is untested.
- Hook deadline: `hook-augment` gives up after 2000 ms by default (`CBM_HOOK_DEADLINE_MS`, 50-10000) and exits 0
  with no context, logging `deadline_exceeded` to `~/.cache/codebase-memory-mcp/logs/hook-augment-timeouts.log`
  (src/cli/hook_augment.c:65-90). That log holds 54 lines without timestamps; the newest was written during the
  2026-11-04 installer rerun. How often hooks time out in normal use is unmeasured; measure it with the hook A/B.
- The hook token A/B test (hooks on vs off on the same questions; cutoffs 20% tokens or 300 ms median) is
  deferred; CBM has no switch to turn its hooks off for one run.
