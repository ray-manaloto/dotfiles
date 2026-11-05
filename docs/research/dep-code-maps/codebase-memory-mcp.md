---
okf_version: "0.2"
type: "report"
title: "codebase-memory-mcp as a per-version map store"
description: "How cbm 0.12.1 stores, exports and reloads one graph per dependency version, and why its compare_graphs cannot diff two versions."
timestamp: "2026-11-05T23:00:00Z"
status: "draft"
stale_after: "2026-12-05T00:00:00Z"
tags: [dep-maps, codebase-memory-mcp, diff]
package: "github:DeusData/codebase-memory-mcp"
version: "0.12.1"
sources:
  - id: cbm
    resource: "https://github.com/DeusData/codebase-memory-mcp/tree/v0.12.1"
    title: "Graph store, export and compare_graphs source at the pinned tag"
  - id: mise1
    resource: "https://github.com/jdx/mise/tree/v2026.11.1"
    title: "mise at the pilot's old tag"
  - id: mise2
    resource: "https://github.com/jdx/mise/tree/v2026.11.2"
    title: "mise at the pilot's new tag"
---

# codebase-memory-mcp as a per-version map store

Section numbers (§1-§5, Q1-Q19) follow the working notes this bundle was cut from; the [index](index.md) maps them to pages. Prototype scripts named `prototype/*.py` are throwaway and live outside the repo in `~/.local/state/dotfiles/dep-code-maps/prototype/`.

## 1.1 Where the graph lives and what format it is
- One SQLite DB per project: `<cache>/<project>.db`, where `project_db_path` builds
  `"%s/%s.db"` from the cache dir (`src/mcp/mcp.c:2252-2261`). The cache dir is
  `${CBM_CACHE_DIR:-$HOME/.cache/codebase-memory-mcp}` (`src/cli/cli.c:185`).
- Tables include `nodes(project,label,name,qualified_name,file_path,start_line,end_line,properties)`
  and `edges(source_id,target_id,type,properties)` (seen with `.schema` on the pilot DB). Function
  and Method `properties` carry `signature`, `return_type`, `param_names`, `param_types`,
  `docstring`, `complexity`, `lines` and `fp`.
- Pilot sizes: 239 MB live DB per mise version; 30.6 MB compressed artifact; 86 MB source worktree.

## 1.2 Indexing one checkout at a tag
- `index_repository` takes `repo_path`, a `name` override and `persistence`
  (`src/mcp/mcp.c:534-552`). Real run:
  `codebase-memory-mcp cli index_repository '{"repo_path":".../mise/v2026.11.2/src","name":"mise-v2026.11.2","mode":"full","persistence":true}'`
  → `status: indexed`, 70,227 nodes, 334,066 edges, in 19.3 s.
- The checkout is a detached `git worktree` of `~/dev/github/jdx/mise` at the tag. cbm records a
  `__branch__.detached` node and the commit.

## 1.3 Export, copy and offline load
- `persistence:true` writes `<repo>/.codebase-memory/graph.db.zst` plus `artifact.json`
  (`src/pipeline/artifact.h:1-35`). The pilot's `artifact.json` holds `commit 43ee02c5…`,
  `schema_version 2` and `reconcile_basis git-clean-head`.
- Re-import happens only inside `index_repository` when no local DB exists (`try_artifact_bootstrap`,
  `src/mcp/mcp.c:10747-10775`). It requires the artifact to sit in the checkout's
  `.codebase-memory/`. The best-quality export drops the SQL indexes, and import rebuilds them
  (`artifact.h:24-28,54-56`), so `zstd -d` alone gives a slow DB. Import refuses a
  `schema_version` newer than the binary supports (`artifact.h:14-19`), so a cbm upgrade can force
  a remap.
- Read-only queries: the query tools open with `cbm_store_open_path_query`, which does not create
  the DB (`src/mcp/mcp.c:3292`). Navigation needs no network. Demo:
  - `search_graph {"project":"mise-v2026.11.2","name_pattern":"bind_requests"}` →
    `src/cli/lock.rs 1823-1886`
  - `trace_path ... direction inbound depth 3` → `bind_and_write_target ← generate_target ← lock_target`

## 1.4 Diffing two versions: the two caveats (confirmed)
- **Name prefix.** Node identity is `(qualified_name, label, file_path)` (`src/store/store.c:1860-1870`).
  The cursor reads raw `qualified_name` with no prefix stripping (`src/store/store.c:2001-2008`).
  Qualified names start with the project name (`mise-v2026.11.2.src.cli.lock.Lock.bind_requests`).
  Real run of `compare_graphs` with base `mise-v2026.11.1` and target `mise-v2026.11.2`: **69,948
  added and 69,687 removed**, i.e. every node. Indexing both versions under the *same* name is
  impossible, because a name maps to one DB file.
- **Changed bodies.** Identity has no body, signature or line fields, so a function that keeps its
  name never shows up. Our prefix-stripped prototype (`prototype/depdiff.py`) compares
  `signature`/`return_type` and `fp`:
  - totals for `src/`: 227 added, **5 signature changes**, 50 body changes. Example: `Lock::bind_requests`
    gained a `run: &LockRun<'_>` parameter, which `compare_graphs` does not report.
  - `fp` is a K=64 MinHash over **AST node-type trigrams** (`src/simhash/minhash.h:1-13`). It is
    skipped below 30 leaf tokens (`minhash.h:27-30`). So it misses identifier-only edits. Four
    git-changed files had no hit: `which.rs` (added `.await`), `tasks/info.rs`,
    `task_results_display.rs`, and `dotfiles/mod.rs` (a `use` list).
  - **Fix (verified):** map `git diff -U0 v1 v2` hunks on the new side to the innermost
    Function/Method whose `start_line..end_line` contains them (`prototype/hunks.py`): 206 hunks
    → **110 touched functions** in 36 files. That includes all four misses. 32 hunks fall outside
    any function (imports, struct fields, consts, docs). Those are caught by the added/removed/field
    diff or reported per file.
- `detect_changes` maps a *working-tree/Git* diff of one indexed project to impact
  (`src/mcp/mcp.c:803`). It is the right tool for "what does this diff touch in one repo". It is
  not a two-version comparison.
