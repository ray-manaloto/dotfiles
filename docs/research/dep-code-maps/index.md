---
okf_version: "0.2"
---

# Dependency code maps (2026-11-05)

Research into version-pinned, offline code maps of the tools this repo depends on, so an agent can
browse a dependency at the exact pinned version and see which upgrade changes can reach the commands
we use. Piloted on mise v2026.11.1 → v2026.11.2 and codebase-memory-mcp v0.12.1. The design was
confirmed by the owner on 2026-11-05; nothing is built yet.

* [Results](results.md) - the summary of every measurement and what it means.
* [Design](design.md) - the confirmed design (items 1-7), decisions Q1-Q19 and open questions (§5).
* [codebase-memory-mcp](codebase-memory-mcp.md) - per-version graphs, export and reload, and why `compare_graphs` can't diff versions (§1).
* [JetBrains](jetbrains.md) - CLion's C++ engines and caches, Qodana and SARIF (§2).
* [Other indexers](other-tools.md) - SCIP and the survey of other indexers (§3).
* [Pilot: mise with cbm and SCIP](pilots.md) - store layout, navigation, blast radius per subcommand, size limits (§4.1-§4.5).
* [Other engines](other-engines.md) - REAgraph, graphify, scip-clang on cbm's C, codanna against SCIP, and cbm's Rust macro miss (§4.6-§4.11).

Working notes, prototypes and generated maps stay outside the repo: `~/.local/state/dotfiles/dep-code-maps/`
and `~/.local/share/dep-maps/`. The upstream codebase-memory-mcp issue about `compare_graphs` is drafted
there and not filed.
