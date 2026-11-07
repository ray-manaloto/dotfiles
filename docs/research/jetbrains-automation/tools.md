---
okf_version: "0.2"
type: "report"
title: "Tools: from spike probes to jbax and jbctl"
description: "The spike's probes and scripts, the tracked tools that replace them (swift/ jbax, python/jbctl), and how --ide picks the IDE through Toolbox."
resource: "swift/ and python/jbctl/"
version: "2026-11-05"
timestamp: "2026-11-05T23:00:00Z"
status: "draft"
stale_after: "2026-12-05T00:00:00Z"
tags: [tools, swift, python, jbctl, jbax, rea, agent-desktop]
---

# Tools

## Tracked (issue #502)

| tool | does | background? |
|---|---|---|
| `swift/` **jbax** | Swift CLI for background AX on JBR/Swing: `windows` (kind frame/settings/popup/other, minimized, modal; no titles), `focus-owner`, `combo`, `select` (guarded AXSelected commit, row 0 only), `press`, `popup list/select`. JSON out; exit codes 0 ok, 1 not found, 2 guard refused, 3 verify failed, 4 not reachable in background, 5 AX error | yes |
| `python/jbctl` | recipe runner and CLI: `--ide` resolution through Toolbox, Settings open (station socket)/goto/press, router-direct, the DIRECT check (MCP tools/list), rea maps and the rea helper patch, and `status`/`start`/`stop`/`restart` of Toolbox IDEs (ADR 0002) | yes (the menu-bar opener needs `JETBRAINS_FOREGROUND=1`; `start` and `restart` bring the IDE forward) |

## Which IDE: `--ide`, resolved through Toolbox

Every IDE command takes `--ide <name>`, the install's Toolbox shell-script name. The same rule covers every
IntelliJ-based product Toolbox installs (`clion`, `pycharm`, `webstorm`, `rustrover`...). `jbctl resolve --ide <name>`
prints the result. The resolver refuses when anything is missing or ambiguous, and never falls back to the first
JetBrains app it sees.

1. **Install.** Toolbox has no command line and no query API for its installs. The `jetbrains-toolbox` binary
   has no flags and passes its arguments to the running Toolbox. Its MCP server is a hub for MCP servers the
   user adds; it has no tools for IDEs. Its station socket (`jb.station.<user>.sock`) serves registered IDEs
   (enterprise auth, tool install, logs, popups). What it publishes is `state.json`: `toolId`, `productCode`
   (null for non-IDE tools such as Fleet, dotTrace and Junie CLI), `buildNumber`, `channelId`,
   `installLocation`. The script name is not in it. It sits in the install's channel file at
   `channels/<channelId>.json`, as `tool.extensions[type=shell].name`. With three CLion installs these were
   `clion`, `clion1` and `clion2`; `baseName` and `tool.intelliJProperties.shellScriptName` were `clion` for
   all three, so neither of those picks an install. All of this is undocumented and was read as Toolbox 3.9.1
   writes it.
2. **App.** The app is `installLocation`. Its `Contents/Resources/product-info.json` must match
   Toolbox's `productCode` and `buildNumber`, because Toolbox's record can lag the app.
3. **pid.** Each IDE's station plugin binds `jb.station.ij.<pid>.sock` in the per-user temp dir
   (`confstr(_CS_DARWIN_USER_TEMP_DIR)`). The pid is the station whose process runs from inside the app. That
   check excludes helper processes and sockets left behind by IDEs that have ended.
4. **MCP endpoint.** jbctl follows the MCP plugin's own order (`McpServerSettings*`, `McpServerService`, read
   with `javap` from CLion 263.7307.209):
   1. `-Didea.mcp.server.force.port`. JVM options are read in the launcher's order (XPlatLauncher `default.rs`),
      later ones winning, each line trimmed:
      - the app's `Contents/bin/<launcher>.vmoptions`;
      - one user file: Toolbox's `<app>.vmoptions` beside the bundle (e.g. `~/Applications/CLion.app.vmoptions`),
        else `<default config>/<launcher>.vmoptions`;
      - `product-info.json` `additionalJvmArguments`.

      Not modelled: `<PRODUCT>_VM_OPTIONS` and `IJ_JAVA_OPTIONS`. They come from the running IDE's environment,
      which jbctl cannot see.
   2. Else `mcpServerPort` in `<config>/options/mcpServer.xml`. `<config>` is `-Didea.config.path` when set, read
      as PathManager reads it (quotes stripped, a leading `~/` is home, normalized; a relative path is refused).
      Otherwise it is the channel's `defaultConfigDirectories["idea.config.path"]`. The plugin writes this setting
      only when the port is not the default, including when the default was busy at start and
      `findFirstFreePort` took the next one.
   3. Else 64342 plus the offset for `-Didea.platform.prefix`: idea 0, CLion 20, DataGrip 60, GoLand 80,
      PhpStorm 100, Python 120, Rider 140, Ruby 160, RustRover 180, WebStorm 200. A prefix the plugin does not
      list gets 0.

   Each IDE's private, authorized server is at the default plus 100. So CLion's private port, 64462, is
   PyCharm's default: here PyCharm took 64463 and saved it. jbctl then checks that the pid listens on the
   port and that the port answers MCP `initialize`, and refuses otherwise. Nothing reports the port at run
   time: neither the MCP server, the station socket nor Toolbox does. One hazard: the three CLion installs
   share one config dir (`CLion2026.3`). A second CLion running at the same time would take 64363 and save it
   for all three.

`//jbctl:coverage <ide>` and `//swift:coverage <ide>` take the same name; the Swift live test gets the pid as
`JBAX_PID` from `jbctl resolve`. Offline tests drive the whole chain against a stand-in Toolbox and stand-in IDE
processes started from a stand-in `.app`.

## Spike probes (replaced)

| spike tool | replaced by |
|---|---|
| `selpoke`, `set-direct-bg` | `jbax select` |
| `popupitems` | `jbax popup` |
| `axpressbtn` | `jbax press --window frame` |
| `comboattrs` | `jbax combo` |
| `focusowner` | `jbax focus-owner` |
| `open-settings.sh`, `check-direct.sh`, `mcpcount.sh`, `rea-patch.sh` | jbctl subcommands (zero bash) |
| `pidclick` | dropped: an inactive CLion ignores pid-posted clicks |
| `axwatch`, `inputtap` | recording only; not tracked |
