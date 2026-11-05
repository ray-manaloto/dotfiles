---
okf_version: "0.2"
type: "report"
title: "JetBrains CLion indexes and SARIF"
description: "CLion 2026.3 read offline: which engine indexes C++, where its caches live, and why neither they nor Qodana SARIF give a pinned, portable map."
timestamp: "2026-11-05T23:00:00Z"
status: "draft"
stale_after: "2026-12-05T00:00:00Z"
tags: [dep-maps, clion, jetbrains, sarif]
sources:
  - id: clion
    resource: "https://www.jetbrains.com/clion/"
    title: "CLion (2026.3 read offline from the installed app)"
  - id: sarif
    resource: "https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html"
    title: "SARIF 2.1.0 specification"
---

# JetBrains CLion indexes and SARIF

Section numbers (§1-§5, Q1-Q19) follow the working notes this bundle was cut from; the [index](index.md) maps them to pages. Prototype scripts named `prototype/*.py` are throwaway and live outside the repo in `~/.local/state/dotfiles/dep-code-maps/prototype/`.

- `WellKnownCommand` in `lib/intellij.platform.core.jar` names `dump-shared-index`, but no bundled
  plugin registers it as an `appStarter`. The registered starters are: buildEventsScheme,
  dataSources, diff, dumpActions, dumpArtifacts, dumpLaunchParameters, duplocate, format, full-line,
  ideScript, inspect, inspections, installPlugins, keymap, listBundledPlugins, **mcpServer**, merge,
  **warmup** and others (from every `META-INF/*.xml` in `lib/` and `plugins/*/lib`). The
  shared-index generator plugin is not bundled; the platform only has
  `JsonSharedIndexDiagnosticEvent` classes (`intellij.platform.lang.impl.jar`).
- `warmup` builds the IDE's own indexes in its system dir. They are an internal binary format
  (stub/PSI persistent maps) that nothing outside the IDE reads. The only agent route is the live
  IDE MCP, which is off-limits while private projects are open, and it is not version-pinned.
- CLion's clangd (`plugins/cidr-clangd`) plus a compile database is the reusable piece for C++
  (AGENTS.md already names it). Its background index is per-machine, not a portable artifact.
- **Which engine indexes C++ (2026-11-05):** CLion 2026.3 (build 263.7307.209) ships two.
  - **CLion Nova** is the one in use here (`clion.use.radler` is `true` in the IDE's
    `options/other.xml`). It is the ReSharper C++ engine from Rider, run as a separate .NET backend
    (`plugins/clion-radler`, 1.2 GB, 922 DLLs) with its own C++ front end, not Clang. Caches:
    `~/Library/Caches/JetBrains/CLion2026.3/resharper-host`. `bin/idea.properties:175` sets
    `clion.nova.migrate.users=true`.
  - **CLion Classic** (shipped, not in use) is the Java engine with a bundled clangd
    (`plugins/cidr-clangd`). A module `intellij.cidr.clangd.novaBridge` exists
    (`product-info.json:5011`); its purpose is not verified.
  - Both share the platform's file-based and stub indexes (`…/Caches/JetBrains/CLion2026.3/index`),
    which `clion warmup` builds headless.
  - All three are internal, per-machine, unpinned binary formats. Nova's cache layout is not
    documented and its .NET code was not read.
  - The only headless Nova route is Qodana for C/C++ (`product-info.json:866` launch entry). Qodana
    writes SARIF: findings (rule, message, severity, location, optional codeFlow), no symbols or
    references, so it can't answer "who calls X". SARIF could feed an optional findings diff
    (`depmaps lint-diff`, see Open), from tools that mise can pin.
- **Conclusion:** JetBrains is not a source of stored, pinned maps. Keep using it interactively only.
