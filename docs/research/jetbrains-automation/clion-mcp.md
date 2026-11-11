---
okf_version: "0.2"
type: "reference"
title: "CLion MCP server: the connection and the clion-debugger skill"
description: "How Claude Code reaches CLion's MCP server, which IDE holds the port, why sessions show ECONNREFUSED, where the clion-debugger skill comes from, and the options that were rejected."
resource: "~/.claude.json mcpServers.clion and CLion's bundled clion-debugger skill"
version: "2026-11-07"
timestamp: "2026-11-08T02:30:00Z"
status: "draft"
stale_after: "2027-05-07T00:00:00Z"
tags: [clion, mcp, claude-code, skills, jetbrains]
---

# CLion MCP server

First written on 2026-11-03 (CLion 2026.3 RC, on the unmerged `feat/clion-ctl` branch). Ported here and
rechecked headless on 2026-11-07, from config files, app bundles, the plugin's bytecode and `lsof`, with no
request to the IDE. Every CLion install was then 2026.3, build CL-263.7307.209.

## The connection

- Claude Code reaches CLion through one user-scope entry, `mcpServers.clion` in `~/.claude.json`:
  `{"type": "http", "url": "http://127.0.0.1:64362/stream"}`. No project carries a `clion` entry. Add it with
  `claude mcp add -s user -t http clion http://127.0.0.1:64362/stream`.
- 64362 is CLion's default port, not one chosen per machine: the MCP plugin's base port 64342 plus CLion's
  offset of 20 (`McpServerSettingsKt.getPortOffset`; jbctl follows the same order, see [Tools](tools.md)). A
  port changed in Settings › AI › MCP Server would be saved in `options/mcpServer.xml`. On 2026-11-07,
  CLion 2026.3's file held only `enableMcpServer` and `consent`, so the default applies.
- Keep the entry at user scope, never in a project `.mcp.json`: the port belongs to this machine's IDE, not
  to a repo.
- No configuration this repo applies names a CLion version, install path or port. The only CLion-related
  setting is the Toolbox scripts folder on `PATH` (`unix/home/.config/zsh/path.zsh`). jbctl computes ports
  from the platform prefix instead of storing them.

## Router mode

- Settings › AI › MCP Server › Exposed Tools › "Enable router-only mode for:" decides what Claude Code
  sees (details in [Results](results.md)). With "All agents" (VIA_ROUTER) it sees one tool,
  `mcp__clion__execute_tool`, and every CLion tool is called through it. With "ACP agents only" (DIRECT,
  the default) it saw 88 tools on 2026-11-05.
- On 2026-11-07, CLion 2026.3's config had no `options/mcpToolFilter.xml`, so it is in DIRECT, the default.
  The older `CLion2026.2` config still says VIA_ROUTER.
- The clion-debugger skill (1.3.2) is written for the router. Its `allowed-tools` is `execute_tool`, and it
  says "Do not call the underlying handles directly". So the skill depends on `execute_tool` being listed.
- **DIRECT keeps `execute_tool` for external clients such as Claude Code** (its listing was seen live on
  2026-11-07, below). Why, from the bytecode:
  `McpServerService.getMcpToolsFiltered` builds each session's list and passes it through `withRouterTool`. That
  adds the router tool back in every mode unless the session opts out with
  `McpSessionOptions.withUnusedRouterToolOmitted()`. An opted-out session keeps it only in
  DIRECT_WITH_ROUTER_ENABLED, when router-only tools exist. The only callers of the opt-out are in the AI-agents
  plugin's ACP module (`air-plugin/lib/modules/intellij.air.backend.acp.mcp.jar`:
  `createAirIdeMcpSessionOptions`, `createAirHookMcpSessionOptions`), for the MCP sessions of agents CLion
  starts itself. An external client such as Claude Code gets the defaults instead:
  `McpServerService.getSessionOptions` builds fresh options (RESPECT_GLOBAL_SETTINGS) when none are registered
  for the session, and those do not opt out. So in DIRECT, Claude Code should get every tool directly **and**
  `execute_tool`. In VIA_ROUTER it got `execute_tool` alone (measured on 2026-11-05).
- **Listed live on 2026-11-07 (00:30 UTC on 2026-11-08), #563.** Measured: one `initialize` and `tools/list` on
  `http://127.0.0.1:64362/stream` from a small script on jbctl's MCP client, which sends only those two requests
  and `notifications/initialized`. The server answered as "CLion MCP Server" 2026.3 (protocol 2025-06-18) and
  listed 88 tools on one page. `execute_tool` ("Universal tool executor that can invoke specific IDE MCP tool
  dynamically") was one of them, and so were all 17 tools the clion-debugger skill's `reference/tools/`
  documents. Context, read from local files rather than the response: the port was held by `clion` (CLion
  2026.3, CL-263.7307.209), whose config had no `options/mcpToolFilter.xml`, so DIRECT. The script is a client
  like Claude Code that registers no session options, which is the case the bytecode reading covers; Claude
  Code itself was not the client. This shows the tools are advertised, not that they work: no tool was called,
  so whether `execute_tool` dispatches to them in DIRECT is untested.
- **To check it again:** `jbctl check-direct --ide clion` sends only `initialize` and `tools/list`, reading
  every page. It prints `{"tools": 88, "direct": true, "router": true}`, where `router` says whether
  `execute_tool` is listed. When the listing succeeds, it exits 1 only if the server is not in DIRECT; DIRECT
  without the router still exits 0, and `router: false` then means the clion-debugger skill cannot run. A
  listing that fails (no answer, no tool list, a bad or repeated cursor) exits 1 with a Failure line instead.

## Which IDE serves the port

- The three CLion installs share the default port, and only one process can hold it. To see which one does:
  `lsof -nP -iTCP:64362 -sTCP:LISTEN`, then `ps -p <pid> -o command=`. `jbctl status` reports MCP per IDE.
- Claude Code retries a remote server's first connection after a transient error. It reconnects one that drops
  mid-session up to five times, with backoff starting at one second, and then marks it failed with "open /mcp
  to reconnect" (Claude Code's MCP docs, Automatic reconnection). So when nothing listens on 64362, `clion`
  ends up failed: CLion is not running, or a switch to another install outlasts the retries. Once a CLion
  serves the port again, reconnect `clion` from `/mcp`, or start a new session.
- Seen: on 2026-11-03, sessions started before the RC took over showed `clion (ECONNREFUSED)` in `/mcp` until
  reconnected. On 2026-11-07 no CLion was running and nothing listened on 64362, and a running session's MCP
  list showed `clion` as failed with ECONNREFUSED.
- On 2026-11-03, the 2026.3 RC (CL-263.7307.108) imported the 2026.2 settings and served the same endpoint,
  so `~/.claude.json` did not change. It added MCP tools that load CMake projects (`load_cmake`, and the
  CMake profile and toolchain tools). The 2026.3 listing of 2026-11-07 still has them: `load_cmake`,
  `check_toolchain`, and the tools that create, update, delete, enable or disable CMake profiles and toolchains.

## The clion-debugger skill

- What it is: JetBrains' agentic-debugging skill
  (<https://www.jetbrains.com/help/clion/agentic-debugging.html>). It drives CLion's debugger through
  `execute_tool`, using `xdebug_*` tools and run configurations, logpoints first. On native backends (GDB,
  LLDB) it uses suspending breakpoints instead.
- Where it comes from: it ships with CLion. In 2026.3 it is `bundledSkills/clion-debugger/` (`SKILL.md`,
  `metadata.json`, `reference/`) inside
  `Contents/plugins/air-plugin/lib/modules/intellij.aiagentextensions.contrib.ide.clion.jar`. On 2026-11-07
  all three installs carried version 1.3.2. In 2026.2.4.1 the AI Assistant plugin (`air-plugin`) was a
  separate install under the config's `plugins/` folder, and its jar of the same name carried 1.1.4.
- Install (user scope), without the IDE: `mise run //jbctl:skills -- --ide clion --skill clion-debugger`
  (`jbctl skills`). It reads the install's jars on disk and contacts no IDE, so CLion may be stopped. It writes
  one copy to `~/.agents/skills/clion-debugger/`, which Codex reads, and links
  `~/.claude/skills/clion-debugger` to it, as `skills add -g` lays out the other skills. It keeps a
  `.jbctl-skill.json` marker in the copy, and leaves alone a copy someone changed or one it did not write.
  `--check` reports what a run would do and writes nothing. See the terms "Bundled skill" and "Skill copy" in
  [[terms]].
- Install from the IDE instead: Settings › AI › Skills (where 2026.3 registers the page). Find
  `clion-debugger` under Bundled skills, open its menu and pick Claude Agent (Global), or "Codex (Global)".
  The steps after the page are from the 2026-11-03 RC and were not rerun. The export writes
  `~/.claude/skills/clion-debugger/`.
- After each CLion update, run `jbctl skills` again: it updates a copy nobody changed to what the install
  ships. On 2026-11-07 the installed copy was 1.3.2, matched the jar byte for byte, and carried the marker
  (`.dotfiles-clion-skills.json`) of the earlier copy task. `jbctl skills --check --ide clion --skill
  clion-debugger` reported `copied` for Codex and `adopted` for Claude: the first run moves that copy under
  jbctl's marker and replaces the Claude folder with the link.

## Rejected options and failed searches (2026-11-03)

- **A Claude Code plugin or marketplace entry**: none found. A GitHub search of the JetBrains organization
  for marketplace repos found only `JetBrains/phpstorm-claude-marketplace`, which covers PHP. GitHub code
  searches for `clion-debugger` and `name: clion-debugger` found no JetBrains source for the skill. These
  searches cover GitHub only, so they do not rule out a distribution elsewhere.
- **`JetBrains/skills`**: it has `debugging-code`, a JetBrains debugger skill with the same `execute_tool`
  and `xdebug_*` design. But that one is written for Rider (.NET, Unity, Unreal), not CLion, and the repo
  has no license.
- **Committing the skill folder here**: rejected. The files are JetBrains' proprietary content in a public
  repo, and a copy would go stale with every CLion update.
- **A task that copies the skill from the installed CLion**: built as `jbctl skills` (2026-11-07), not as
  the mise file task on `feat/clion-ctl` (33eec5c), which predates this repo's rule that Python lives in
  packages under `python/`. Toolbox keeps several CLion apps side by side, so it takes the install by
  `--ide`, not by which one serves the MCP port.
