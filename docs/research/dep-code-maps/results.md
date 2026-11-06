---
okf_version: "0.2"
type: "report"
title: "Dependency code maps: results"
description: "What was measured across cbm, SCIP, scip-clang, codanna, graphify and JetBrains, and what it means for the design."
timestamp: "2026-11-06T12:00:00Z"
status: "draft"
stale_after: "2026-12-05T00:00:00Z"
tags: [dep-maps, codebase-memory-mcp, scip, summary]
package: "github:DeusData/codebase-memory-mcp"
version: "0.12.1"
sources:
  - id: cbm
    resource: "https://github.com/DeusData/codebase-memory-mcp/tree/v0.12.1"
    title: "Graph store, export and compare_graphs source at the pinned tag"
  - id: mise2
    resource: "https://github.com/jdx/mise/tree/v2026.11.2"
    title: "mise at the pilot's new tag"
  - id: ra
    resource: "https://github.com/rust-lang/rust-analyzer/releases/tag/2026-11-02"
    title: "rust-analyzer release used for SCIP"
  - id: scip-clang
    resource: "https://github.com/sourcegraph/scip-clang/tree/v0.4.1"
    title: "scip-clang source at the pinned tag"
  - id: codanna
    resource: "https://github.com/bartolli/codanna/tree/v0.17.1"
    title: "codanna source at the pinned tag"
  - id: graphify
    resource: "https://github.com/Graphify-Labs/graphify/tree/v0.9.103"
    title: "graphify source at the latest release"
---

# Dependency code maps: results

Section numbers (§1-§5, Q1-Q30) follow the working notes this bundle was cut from; the [index](index.md) maps them to pages. Prototype scripts named `prototype/*.py` are throwaway and live outside the repo in `~/.local/state/dotfiles/dep-code-maps/prototype/`.

- **Yes, this works with cbm today.** Indexing one mise tag takes ~20 s and gives 70k nodes and
  334k edges. The result is one SQLite file per version, which agents query offline through the
  existing cbm MCP tools under a project name such as `mise-v2026.11.2`.
- **Don't build on cbm's built-in version diff.** Both caveats from the side-agent note are
  **confirmed by real runs** (details in §1.4):
  1. `compare_graphs` reports *everything* as changed between two versions (69,948 added /
     69,687 removed), because every node name starts with the project name.
  2. It matches nodes only by (name, kind, file), so it never reports a changed body or signature.
     The stored `fp` body fingerprint catches some body changes but not all.
- **A ~100-line diff of our own fixes both.** It strips the project prefix, compares signatures, and
  maps exact `git diff` hunks onto function line ranges. Then it walks inbound CALLS edges up to
  the mise subcommands this repo uses, which gives a per-subcommand blast radius (§4.3).
- **JetBrains has no offline-queryable index export** in CLion 2026.3 (§2). Its maps are reachable
  only through a running IDE.
- **SCIP** (`rust-analyzer scip`) was run on mise and compared with cbm (§4.4). cbm's call edges
  are wrong in both directions: it adds false callers for common names (`default()`) and drops
  every call inside a `macro_rules!` macro (§4.11), such as mise's `measure!`. The `run`, `tasks` and `bootstrap` gaps come from a 256-name cap on
  the name lookup, a dropped self-edge and grouped `use` imports ([§4.12](rust-call-graphs.md)). So SCIP is the one to trust for blast radius, while cbm stays
  the browsing tool for agents and covers the other languages. The SCIP run took 258 s and wrote
  112 MB.
- **REAgraph + graphify** was run as a third blast-radius engine (§4.7). Its diff is prefix-free
  (stable path ids), but graphify's Rust call graph is 82% same-file, so it under-reaches. It
  finds 2 callers of `Task::default` where SCIP finds 234, and misses `install`. It isn't added
  as an engine; its WL rename/move alignment is noted as prior art. rea is a binary-RE sensor
  that this pipeline doesn't need (§4.6). §4.8 explains the miss from graphify's source: it drops
  `x.m()` and `Type::f()` across files, which is 73% of mise's call sites.
- **mise dotfiles' private repo can't carry the maps**: its history skips files over 16 MiB
  (§4.5), and the cbm artifact is 30.6 MB.
- **scip-clang on cbm's own C** (§4.9): 2 s, 46 MB. cbm's C call edges score recall 0.919 and
  precision 0.787 against it (~0.936 without cbm's libc wrappers), far closer than on Rust.
- **codanna on mise** (§4.10): 12.6 s, precision 0.981 but recall 0.648 against SCIP (after the
  range fix below); it doesn't
  replace SCIP for blast radius. Its `install` blast is 0 because it drops all three call sites
  where SCIP's chains enter src/cli/install.rs: a receiver typed only by annotation, a call inside `measure!`, and an
  `&Arc<Config>` parameter it types as `Arc`. Its resolver drops untyped receivers rather than guess.
- **cbm on Rust macros** (§4.11): cbm makes an edge only where its syntactic extractor finds a call
  site, and inside a macro it adds sites only for built-in macros such as `println!`. So no call in
  a `macro_rules!` body is linked, which is why the `install_all_versions_with_progress` call at
  src/cli/install.rs:720 is missing. Confirmed on the mise graph and a probe crate.
- **SCIP checked against the compiler** ([§4.13](rust-call-graphs.md)). Charon and CGA, both rustc
  drivers, agree with SCIP's call edges at 0.988/0.985 and 0.928/0.925 precision/recall, and rustc's
  MIR confirms 1,684 of the 1,703 edges out of `#[async_trait]` methods. Neither tool adds anything real
  to any command's blast. The fault that moved the blast counts was in our reading of SCIP:
  rust-analyzer gives `#[async_trait]` methods the whole block as their range, which the prototypes
  now fix with tree-sitter bounds. SCIP's one real flaw found: three nested test fns share one symbol,
  and their 3 edges are in test code that no check builds.
- **cfg:** SCIP keeps path edges from `#[cfg]`-off code. Blast keeps them and flags them as not in this
  host's build (Q20, Q24).
- **Design confirmed (Q19)** on 2026-11-05; the build is tickets #510, #511 and #512 (Q23).
