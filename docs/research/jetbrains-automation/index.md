---
okf_version: "0.2"
---

# Driving JetBrains IDEs from code: CLion 2026.3 on macOS (2026-11-05)

How far CLion can be read and driven through macOS accessibility (agent-desktop, rea, small Swift
probes), with CLion kept behind other apps. The worked example is changing Settings › AI › MCP Server
› Exposed Tools › "Enable router-only mode for:" from "All agents" (VIA_ROUTER) to "ACP agents only"
(DIRECT).

The live runs were on CLion 2026.3 (JBR 25.0.4.1+1-b635.79, pid 37856), agent-desktop 1.2.0
(envelope 2.6), rea-agents 6.8.0 (patched locally) and macOS 27.2. Source reading:
JetBrainsRuntime jbr-release-25.0.4.1b635.79 and intellij-community ebd238636, done by a second
session (dotfiles-c6).

* [Results](results.md) - what changed DIRECT, every route tried, and how it was verified. Start here.
* [Headed vs headless](headed-vs-headless.md) - why keys and focus need an active app, and what runs in the background.
* [Background dropdown commit](background-combo-commit.md) - AXSelected on the popup child → `setSelectedIndex(0)`, the row-0 limit and its guard.
* [Opening and navigating Settings](settings-open-and-navigation.md) - menu AXPress dropped while inactive, the gear popup, the URL scheme, search-field navigation, the breadcrumb.
* [Recordings and evidence](recordings-and-evidence.md) - the owner's hand runs, AX notification timelines, input event sources.
* [rea on CLion](rea.md) - the install, the three local patches, what rea sees and can do, and its limits.
* [Tools](tools.md) - every script, probe and the `jbctl` library, with what each one does.
* [Plan](plan.md) - map once, execute many: the zero-token automation plan.
* [CLion MCP server](clion-mcp.md) - the user-scope `clion` entry, its default port, router mode, ECONNREFUSED after a switch, and the bundled clion-debugger skill.
* [Terms](terms.md) - headless run, debug route, station route, Toolbox script name.
* [Update log](log.md) - what was added, rejected and failed.

Privacy rule for this bundle: no window titles or project names from CLion appear here. The spike's raw
recordings and rea maps stayed in its local, untracked working folder.
