---
type: Reference
title: "CLion MCP server"
description: "How Claude Code reaches CLion's MCP server, how the clion-debugger skill is installed, what to redo when the IDE changes, and the rejected options."
resource: "docs/research/clion-mcp.md"
tags: [clion, mcp, claude-code, skills, jetbrains]
generated: { by: process:claude-code-session, at: "2026-11-03T15:45:00-06:00" }
status: stable
stale_after: "2027-05-03T00:00:00+00:00"
---

# CLion MCP server

## The connection

- Claude Code reaches CLion through one user-scope entry, `mcpServers.clion` in `~/.claude.json`:
  `{"type": "http", "url": "http://127.0.0.1:64362/stream"}`. Add it with
  `claude mcp add -s user -t http clion http://127.0.0.1:64362/stream`.
- The port is picked per machine in CLion (Settings | Tools | MCP Server), so the entry stays at user
  scope. Never put it in a project `.mcp.json`.
- The server runs in router-only mode (Settings | Tools | MCP Server | Exposed Tools). Claude Code
  then sees a single tool, `mcp__clion__execute_tool`, and every CLion tool is called through it.
  The `clion-debugger` skill expects this mode.
- No configuration this repo applies (chezmoi or mise templates, tasks, zsh files) names a CLion
  version, install path or port; only this note and AGENTS.md do. The only CLion-related setting is
  the JetBrains Toolbox scripts folder on `PATH` (`unix/home/.config/zsh/path.zsh`), and it has no
  version in it.

## Switching IDE versions

On 2026-11-03, CLion 2026.3 RC (build CL-263.7307.108, installed by Toolbox as
`~/Applications/CLion 2026.3 Release Candidate.app`) replaced CLion 2026.2.4.1 as the IDE that
serves this endpoint. The RC imported the 2026.2 settings, so it listens on the same port and the
`~/.claude.json` entry did not change. The RC adds MCP tools that load CMake projects: `load_cmake`
and the CMake profile and toolchain tools.

Only one IDE can hold the port. To check which one does:
`lsof -nP -iTCP:64362 -sTCP:LISTEN`, then `ps -p <pid> -o command=`.

A Claude Code session started while the old IDE was serving keeps its dead connection. `/mcp`
shows `clion (ECONNREFUSED)` until you reconnect `clion` from `/mcp`, or restart the session.
Sessions started after the switch connect on their own.

## The clion-debugger skill

- What it is: JetBrains' agentic-debugging skill
  (<https://www.jetbrains.com/help/clion/agentic-debugging.html>). It teaches an agent to drive
  CLion's debugger through `execute_tool`, using `xdebug_*` tools and run configurations, with
  logpoints first. On native backends (GDB, LLDB) it uses suspending breakpoints instead.
- Where it comes from: it is bundled with CLion. The searches on 2026-11-03 (below) found no other
  JetBrains distribution of it. In the 2026.3 RC it is
  `bundledSkills/clion-debugger/` (`SKILL.md`, `metadata.json` version 1.3.2, `reference/`) inside
  `Contents/plugins/air-plugin/lib/modules/intellij.aiagentextensions.contrib.ide.clion.jar`
  in the app. In 2026.2.4.1 the AI Assistant plugin (`air-plugin`) was a separate install, under
  `~/Library/Application Support/JetBrains/CLion2026.2/plugins/`, and its jar of the same name
  carries an older copy, version 1.1.4.
- Install (user scope): in CLion, Settings | Tools | AI Assistant | Skills, find `clion-debugger`
  under Bundled skills, open its menu and pick Claude Agent (Global). That writes
  `~/.claude/skills/clion-debugger/`. Codex has a matching "Codex (Global)" choice. Without the
  IDE: unzip `bundledSkills/clion-debugger/*` from the jar into an empty folder, then copy its
  `bundledSkills/clion-debugger/` folder to `~/.claude/skills/clion-debugger/` (the archive keeps
  the `bundledSkills/` prefix).
- After each CLion update, redo the export so the copy matches the IDE's tools. Compare the
  `version` in `~/.claude/skills/clion-debugger/metadata.json` with the jar's.

## Rejected options and failed searches

- **A Claude Code plugin or marketplace entry**: none found on 2026-11-03. A GitHub search of the
  JetBrains organization for marketplace repos found only `JetBrains/phpstorm-claude-marketplace`,
  which covers PHP. GitHub code searches for `clion-debugger` and `name: clion-debugger` found no
  JetBrains source for the skill. These searches cover GitHub only, so they do not rule out a
  distribution elsewhere.
- **`JetBrains/skills`**: it has `debugging-code`, a JetBrains debugger skill with the same
  `execute_tool` and `xdebug_*` design. But that one is written for Rider (.NET, Unity, Unreal), not
  CLion, and the repo has no license.
- **Committing the skill folder here**: rejected. The files are JetBrains' proprietary content in a
  public repo, and a copy would go stale with every CLion update.
- **A mise task that unzips the skill from the installed CLion**: deferred. Toolbox keeps several
  CLion apps side by side, so the task would have to pick one. The IDE's own export does the same
  job in one click.
