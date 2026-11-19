---
okf_version: "0.2"
type: "report"
title: "Other indexers surveyed"
description: "SCIP, scip-clang, clangd-indexer, Kythe, Glean, LSIF, stack-graphs and the tree-sitter MCP tools, with real working configs and fit."
timestamp: "2026-11-05T23:00:00Z"
status: "draft"
stale_after: "2026-12-05T00:00:00Z"
tags: [dep-maps, scip, indexers, survey]
sources:
  - id: ra
    resource: "https://github.com/rust-lang/rust-analyzer/releases/tag/2026-11-02"
    title: "rust-analyzer release used for SCIP"
  - id: ra-include
    resource: "https://github.com/rust-lang/rust-analyzer/issues/23604"
    title: "include! files are not indexed"
  - id: scip
    resource: "https://github.com/scip-code/scip/releases/tag/v0.10.0"
    title: "SCIP CLI used for print and convert"
  - id: warnalyzer
    resource: "https://github.com/est31/warnalyzer"
    title: "Working config: rust-analyzer scip"
  - id: mozsearch
    resource: "https://github.com/mozsearch/mozsearch-mozilla"
    title: "Working config: rust-analyzer scip for Glean"
  - id: opencodehub
    resource: "https://github.com/laithalsaadoon/opencodehub"
    title: "ADR 0005: SCIP replaces LSP"
  - id: glean
    resource: "https://github.com/facebookincubator/Glean"
    title: "Glean rust-scip indexer"
  - id: kythe
    resource: "https://github.com/kythe/kythe"
    title: "Kythe"
  - id: stack-graphs
    resource: "https://github.com/github/stack-graphs"
    title: "stack-graphs (archived)"
  - id: scip-clang
    resource: "https://github.com/sourcegraph/scip-clang/tree/v0.4.1"
    title: "scip-clang source at the pinned tag"
  - id: codanna
    resource: "https://github.com/bartolli/codanna/tree/v0.17.1"
    title: "codanna source at the pinned tag"
---

# Other indexers surveyed

Section numbers (§1-§5, Q1-Q30) follow the working notes this bundle was cut from; the [index](index.md) maps them to pages. Prototype scripts named `prototype/*.py` are throwaway and live outside the repo in `~/.local/state/dotfiles/dep-code-maps/prototype/`.

| Tool | What it stores | Real working config |
|---|---|---|
| SCIP via `rust-analyzer scip` | precise defs/refs, one protobuf per repo | est31/warnalyzer `run.sh:27` `rust-analyzer scip . --output target/index.scip`; mozsearch/mozsearch-mozilla `glean/build:10-12` `rust-analyzer scip .` then `mv index.scip $OBJDIR/rust.scip` |
| SCIP ingestion into a graph | SCIP replaces LSP as the source of edges | theagenticguy/opencodehub (now laithalsaadoon/opencodehub) `docs/adr/0005-scip-replaces-lsp.md:25-28` ("Each indexer runs once per repo and emits a single `.scip` protobuf file. No daemon") |
| Glean (Meta) | SCIP → Glean facts | facebookincubator/Glean `glean/lang/rust-scip/Glean/Indexer/RustScip.hs:30-33` |
| ast-grep, tree-sitter, graphify, ctags | installed locally; structural search or tags. graphify links some calls across files by name and path, but no type resolution (§4.8) | complements, not a replacement |

- The rustup proxy has no rust-analyzer component, so the pilot ran it without installing anything:
  `mise x aqua:rust-lang/rust-analyzer@2026-11-02` (0.3.3105) and `github:scip-code/scip@0.10.0`.
  Results are in §4.4. Known gap: files pulled in through `include!` are not indexed
  (rust-lang/rust-analyzer#23604).

**Survey of other indexers (2026-11-05; repos and latest releases checked, source read only where cited):**

| Tool | Kind | Status | Fit |
|---|---|---|---|
| scip-clang (Sourcegraph) | compiler-grade, C/C++, writes `.scip` | v0.4.1, 2026-10-22 | Piloted (§4.9). Needs `compile_commands.json`. |
| clangd-indexer (LLVM) | compiler-grade, C/C++ | ships with LLVM | Static index for `clangd -index-file`; clangd-private format, needs our own reader. Second choice. |
| Kythe (Google) | compiler-grade, many languages | v0.0.76, 2026-07 | Heavy, own graph store. Too much for one machine. |
| Glean (Meta) | fact store, imports SCIP | active, no releases | Built to run as a server. Same verdict. |
| LSIF | SCIP's predecessor | replaced by SCIP | Skip. Not re-checked this session. |
| stack-graphs (GitHub) | name resolution | archived, last release 2024-12 | Skip. |
| codanna | tree-sitter heuristics + embeddings, MCP | v0.17.1, 2026-10-11 | Piloted (§4.10). |
| tokensave | tree-sitter, MCP | v7.16.0, 2026-10-22 | README only, not run. |
| narsil-mcp | tree-sitter, call graph, taint | v1.7.2, 2026-10-07 | README only, not run. |
| codeseek | call graph + hybrid search | v0.1.31, 2026-07 | README only, not run. |
| probe | code search, no graph | v0.6.0-rc344 | Not a map. |
| Charon (AeneasVerif) | rustc driver, writes ULLBC JSON | 0.1.311 (2bceb7c), on nightly-2026-09-17 | Piloted ([§4.13](rust-call-graphs.md)). Compiler-resolved calls for sync code; async bodies come out as `Error`. |
| CGA (OpenDevicePartnership/cga) | rustc driver, monomorphized call graph | 2fc6310, 2026-10-20, on nightly-2026-10-18 | Piloted ([§4.13](rust-call-graphs.md)). Needs a one-character build.rs fix on macOS. Reads async fns but not `#[async_trait]` (`dyn Future`) bodies. |

The tree-sitter tools compete with cbm, not with SCIP.
