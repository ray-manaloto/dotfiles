---
type: Reference
title: "CLion MCP server"
description: "How Claude Code reaches CLion's MCP server, how the clion-debugger skill is installed, how clion-ctl starts and restarts the IDE, what to redo when the IDE changes, and the rejected options."
resource: "docs/research/clion-mcp.md"
tags: [clion, mcp, claude-code, skills, jetbrains, clion-ctl]
generated: { by: process:claude-code-session, at: "2026-11-03T17:30:00-06:00" }
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
- Install (user scope): `mise run clion:skills`, which bootstrap runs after the tools
  (`[bootstrap.hooks.post-tools]` in `unix/home/.config/mise/config.toml`). The task,
  `unix/home/.config/mise/tasks/clion/skills`, copies `bundledSkills/clion-debugger/` from the
  installed CLion's jar to `~/.claude/skills/clion-debugger/`, so no JetBrains file is committed.
  - Source: the skill must match the CLion serving MCP. Skill 1.1.4 (2026.2) calls
    `xdebug_set_breakpoint` where 1.3.2 (2026.3) calls `xdebug_set_breakpoints`, so the newest
    installed copy can be the wrong one. In order:
    - `CLION_SKILL_JAR`, when set, names the jar.
    - With `mcpServers.clion` in `~/.claude.json`: the module jar that the one process listening
      on its loopback port has open (`lsof -iTCP@<host>:<port> -sTCP:LISTEN`, then `lsof -p`),
      wherever it was loaded from. The listener is read again afterwards, and must not have changed.
    - With no such entry: the one installed jar, from a `CLion*.app` in `/Applications` or
      `~/Applications` (`CLION_SKILL_APPS` replaces these) or a
      `~/Library/Application Support/JetBrains/CLion*/plugins/`.
    - Otherwise nothing changes, with exit 0, so bootstrap never fails on it: `no-server` when the
      entry is set but nothing listens, or several CLions are installed and no entry picks one;
      `invalid-config` when `~/.claude.json` or the entry cannot be read. Start CLion and re-run
      `mise run clion:skills`.
  - Ownership: the task writes `.dotfiles-clion-skills.json`, listing every file's sha256, into
    the folder. It replaces the folder only when the files still match that list and the jar's
    copy differs. An unmarked folder byte-identical to the jar's copy is adopted. A changed or
    unmarked folder, or a link, is left alone with status `modified` or `unmanaged`.
  - It prints one JSON event: `installed`, `current`, `adopted`, `modified`, `unmanaged`,
    `no-server`, `invalid-config` or `no-clion` with exit 0, or an `error` on stderr with exit 1
    (a broken jar, bad metadata, a path that leaves the skill folder, a listener with no skill
    module open or several).
- The IDE way: in CLion, Settings | Tools | AI Assistant | Skills, find `clion-debugger` under
  Bundled skills, open its menu and pick Claude Agent (Global). CLion's `InstallSkillAction`
  copies the folder once and reports it already installed when the folder exists, so it never
  updates a copy. A fresh export is adopted by the task on its next run.

## Starting, stopping and restarting the IDE: clion-ctl

`clion-ctl` (`python/clionctl`, installed with `mise run //clionctl:install`) runs on macOS only. It
starts, stops and restarts a JetBrains IDE and lists the running ones. Each command prints JSON
lines: an event on stdout, or a failure with a named `error` on stderr and exit 1.

- `clion-ctl status` lists each running IDE: its pid, its `.app` bundle, its station socket and the
  TCP ports it listens on. The station gives no way to list open projects, so status leaves them out.
- `clion-ctl start --app <path.app> [--project <dir>] [--mcp-port <n>]` runs
  `/usr/bin/open -n <app> --args <dir>`. It waits until a new process of that bundle holds a socket
  and, when `--mcp-port` is given, listens on that port. It refuses an app that already runs (`running`):
  a second launch hands its arguments to the running copy and quits, so no new IDE would come.
- `clion-ctl stop` and `clion-ctl restart` pick one IDE: the only one running, or one chosen with
  `--pid` or `--app`. When several match, they refuse with `ambiguous`.
- **Finding the IDEs:** each IDE's bundled station plugin listens on the Unix socket
  `jb.station.ij.<pid>.sock` in the JVM's temporary folder. On macOS that is the per-user folder
  `confstr(_CS_DARWIN_USER_TEMP_DIR)` returns (`unistd.h`: 65537), whatever `TMPDIR` or
  `XDG_RUNTIME_DIR` say (this Mac's shell sets `XDG_RUNTIME_DIR`). `CLION_CTL_STATION_DIR`
  replaces the folder. The socket file stays after the IDE ends, so a socket counts only while
  its pid is alive and holds that path (`psutil` `net_connections("unix")`).
  `lvillis/za` (`src/command/ide/mod.rs:1974-2059`) reads the same name and checks the pid.
- **Stopping:** `POST /exit` on that socket, plain HTTP with JSON:
  `{"userInitiated": true, "force": false, "restart": <bool>}`, answered `200 {"immediate": false}`.
  The station plugin (`Contents/plugins/station-plugin/lib/station-plugin.jar`,
  `com.intellij.station.core.impl.IdeShutdownHandlerService`, read with `javap`) calls
  `Application.exit(force, exitConfirmed = userInitiated, restart)`. `userInitiated` only skips the
  "exit?" question. With `force: false` the IDE quits as its own menu does, saving projects and asking
  first when a process still runs. An IDE without the endpoint answers 404 with
  `X-Station-Failure: no-endpoint`, reported as `station`.
- **Never killed:** when the IDE still runs at the timeout, the command reports `still-running`:
  the IDE may be asking a question, to be answered in the IDE. It never sends a signal and never
  sets `force`. A restart that ended the old process with no new one reports `not-started`.
- **Restarting:** the IDE restarts through a new process (`Restarter` in `idea.log`), so the pid
  changes; `restarted` reports both. A short restart (the one on 2026-11-03 took seconds) left a
  running Claude Code session connected: its `clion` entry came back on its own. Claude Code
  retries a refused connection in the background with growing waits, so after a long outage a
  session can still show `clion (ECONNREFUSED)`; reconnect it from `/mcp`.
- **Tests:** a stand-in IDE app bundle (`tests/standin.py`) serves the same socket and `/exit`,
  launched by the real `open -n`, so every case runs without starting a real IDE: one that obeys,
  one whose quit waits on a question, one that quits instead of restarting, one with no endpoint,
  and one that hangs up.

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
- **The highest installed version**: the first version of the task took it. It gave the
  2026.3 skill to a session served by 2026.2, whose tools have other names.
- **Mapping the listener to its app folder**: tried, and replaced by reading the jar the process
  has open, which also finds a plugin loaded from a config folder.
- **Failing when CLion is not running**: a Codex peer's first version did. Bootstrap would then
  fail on a Mac where CLion is closed, so the task reports `no-server` and changes nothing.
- **Leaving updates to CLion**: its skills module has a sync to agent homes
  (`AgentHomeSkillsSync`), but it is off unless the JVM property
  `intellij.aiagentextensions.skills.sync.to.agent.homes` is set, and it refuses a non-empty
  `~/.claude/skills` that it has not claimed.
- **Killing an IDE that will not quit, or `force: true`**: rejected for clion-ctl. A blocked quit
  is a question for the user, such as a running process or unsaved work, and a kill loses that work.
- **The Toolbox scripts (`clion`, `clion1`, ...) to pick the IDE**: they are numbered per install,
  not per version, so clion-ctl takes the app path or a pid.
