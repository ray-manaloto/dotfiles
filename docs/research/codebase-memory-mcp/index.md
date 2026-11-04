---
okf_version: "0.2"
---

# codebase-memory-mcp on this Mac (v0.12.1, 2026-11-03)

How codebase-memory-mcp (CBM) is installed at user scope for Claude Code and Codex, how it was verified, what it
gives (AST graph, type resolution, blast radius, hooks, agents), how to upgrade it, what other projects do, and how
much its token savings can be trusted.

* [Install](install.md) - mise owns the binary; `//cbm:install` runs CBM's installer through a stable launcher; the macOS `--skip-binary` workaround.
* [Verification](verification.md) - every check that was run, with results, and what is still open.
* [Tools, hooks and agents](tools-hooks-agents.md) - the 13 read-only tools, the hook set per client, the three agent tiers, latency.
* [Upgrades](upgrades.md) - the exact pin, why bulk upgrades skip CBM, what the forced drain keeps, and the agreed upgrade automation design (ADR 0001).
* [How other projects set it up](other-projects.md) - multi-harness dotfiles setups, kept and stripped hooks, launch paths.
* [Effectiveness and token cost](effectiveness.md) - the 10x claim has one source; independent tests disagree.

# Data

* `data/saved-searches.json` - 75 GitHub saved searches (34 in the updates set) about CBM setups, releases and issues, in the saved-search row shape plus `endpoint`, `qualifiers`, `why` and hit counts. 73 ran on 2026-11-03; the two watch rows (`upd-releases`, `upd-watch-issues`) are for later runs.
