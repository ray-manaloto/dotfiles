---
okf_version: "0.2"
type: "reference"
title: "GitHub issues, PRs and discussions on LSP plugins"
description: "Every relevant issue and PR found by 20 saved searches across anthropics/claude-code, anthropics/claude-plugins-official, anthropics/claude-plugins-community and Piebald-AI/claude-code-lsps, as of 2026-11-03."
timestamp: "2026-11-03T21:00:00Z"
status: "draft"
stale_after: "2026-12-03T00:00:00Z"
tags: [claude-code, plugins, lsp, github, issues]
sources:
  - id: saved-searches
    resource: "repo:docs/research/lsp/data/saved-searches.json"
    title: "The 20 searches and their hit counts"
---

# GitHub issues, PRs and discussions on LSP plugins

The search definitions are in `data/saved-searches.json`; the hit lists are in `data/search-hits/`.

## Read in full

| Item | State | What it says |
|---|---|---|
| [claude-plugins-official#379](https://github.com/anthropics/claude-plugins-official/issues/379) | open | Every official LSP folder lacks `.lsp.json`; still broken on 2.1.288 |
| [claude-plugins-official#378](https://github.com/anthropics/claude-plugins-official/pull/378) | closed 2026-02-11, unmerged | The fix (adds `.lsp.json` to each folder), closed by the contributor policy. A comment links a self-hosted fixed fork, `itsjoshpark/claude-plugins` (not inspected) |
| [claude-plugins-official#5667](https://github.com/anthropics/claude-plugins-official/issues/5667) | open | rust-analyzer-lsp and clangd-lsp ship without `plugin.json` |
| [claude-code#99117](https://github.com/anthropics/claude-code/issues/99117) | open (bug, has repro) | The Desktop `--plugin-dir` copy of a `strict: false` LSP plugin drops `lspServers` → 0 servers |
| [claude-code#102145](https://github.com/anthropics/claude-code/issues/102145) | open (bug, has repro) | Desktop SSH sessions sync pyright-lsp and typescript-lsp without `lspServers` |
| [claude-code#93474](https://github.com/anthropics/claude-code/issues/93474) | open (labelled duplicate) | Install writes a `plugin.json` without `lspServers`; workaround: a hand-written `.lsp.json`, wiped on update |
| [claude-code#78604](https://github.com/anthropics/claude-code/issues/78604) | open (reproduced by Anthropic 2026-08-21) | A stale `plugin.json` shadows the entry's `lspServers`; `plugin update` cannot repair it |
| [claude-code#94762](https://github.com/anthropics/claude-code/issues/94762) | open (regression) | Same class of failure for inline `skills` |
| [claude-code#90114](https://github.com/anthropics/claude-code/issues/90114) | closed by stale bot 2026-11-03, not planned | clangd-lsp never registers an LSP tool |
| [claude-code#53399](https://github.com/anthropics/claude-code/issues/53399) | closed by stale bot | A plugin-root `.lsp.json` works; inline `lspServers` alone is ignored (third-party marketplace) |
| [claude-code#15148](https://github.com/anthropics/claude-code/issues/15148) | open since 2025-12-23 | The original "lspServers not processed from marketplace.json" |

## Triaged by title

anthropics/claude-code, Directory-related:
- #100608: `strictKnownMarketplaces` drops `{"source":"pluginDirectory"}`, so the Directory cannot be allowlisted.
- #104457: a Desktop Directory install has no working path.

anthropics/claude-code, LSP in plugins:
- #15168: "No LSP server available".
- #101008: the recommendation offers the official plugin when another plugin already covers the extension.
- #104477: plugin servers have no idle timeout.
- #101351: clangd `--background-index` runs per session with unbounded memory.
- #106465: servers bypass `CLAUDE_CODE_SHELL_PREFIX`.
- #84125 and #80733: the LSP tool is pruned from subagents.
- #91916: gopls is installed but its `lspServers` wiring is missing.
- #84857: clangd is missing `lspServers` (closed).
- #75612 and #73961: a server on the user's PATH is refused as "not found or in an unsafe location".
- #64422: an extension conflict resolves silently (closed).

anthropics/claude-code, `ENABLE_LSP_TOOL`: 46 hits. Some are open, but they mention the variable only in passing
(#15148, #80733, #84125). The issues whose subject is the variable are closed (#17468, #53837). No hit reports it as
a requirement in 2.1.317. The 2.1.317 binary still lists the variable in its environment-variable registry (offset
≈7247940 in `strings -n 6`); whether it still gates the LSP tool was not traced.

anthropics/claude-plugins-official, per-plugin:
- #444: php-lsp ships with no configuration.
- #441: lua-lsp ships with no configuration.
- #2284: add `.hh` to clangd-lsp.
- #2432: let clangd-lsp set the clangd path.
- #1836: pyright-lsp `workspaceFolder`.

anthropics/claude-plugins-community: no LSP packaging issue. The hits are bump PRs for third-party LSP plugins (#3019
zig-lsp, #2572 docvet-lsp, #2686 karellen-lsp-mcp).

Piebald-AI/claude-code-lsps:
- #7–#19 (2025-12): "missing lspServers config in marketplace.json", fixed by 2026-01-30.
- #39: a temporary patch for the 2.0.76 LSP bug.
- No issue discusses the Directory.

## Gaps

- **GitHub Discussions.** `gh search issues` covers issues and PRs only, and no discussion surfaced in either
  Anthropic repository.
- **Respelled queries.** Three queries were respelled after an invalid or empty first run; each row in
  `data/saved-searches.json` carries a `note`.
