---
okf_version: "0.2"
type: "report"
title: "Pilot: mise v2026.11.1 to v2026.11.2 with cbm and SCIP"
description: "Store layout, offline navigation, blast radius per mise subcommand with cbm and SCIP, and the dotfiles-history size limit."
timestamp: "2026-11-05T23:00:00Z"
status: "draft"
stale_after: "2026-12-05T00:00:00Z"
tags: [dep-maps, mise, scip, blast-radius]
package: "mise"
version: "2026.11.2"
sources:
  - id: mise1
    resource: "https://github.com/jdx/mise/tree/v2026.11.1"
    title: "mise at the pilot's old tag"
  - id: mise2
    resource: "https://github.com/jdx/mise/tree/v2026.11.2"
    title: "mise at the pilot's new tag"
  - id: cbm
    resource: "https://github.com/DeusData/codebase-memory-mcp/tree/v0.12.1"
    title: "Graph store, export and compare_graphs source at the pinned tag"
  - id: ra
    resource: "https://github.com/rust-lang/rust-analyzer/releases/tag/2026-11-02"
    title: "rust-analyzer release used for SCIP"
  - id: scip
    resource: "https://github.com/scip-code/scip/releases/tag/v0.10.0"
    title: "SCIP CLI used for print and convert"
---

# Pilot: mise v2026.11.1 to v2026.11.2 with cbm and SCIP

Section numbers (§1-§5, Q1-Q19) follow the working notes this bundle was cut from; the [index](index.md) maps them to pages. Prototype scripts named `prototype/*.py` are throwaway and live outside the repo in `~/.local/state/dotfiles/dep-code-maps/prototype/`.

## 4.1 Store (current layout, all outside the repo)
```
~/.local/share/dep-maps/mise/v2026.11.1/src/                         detached worktree at the tag
~/.local/share/dep-maps/mise/v2026.11.1/src/.codebase-memory/graph.db.zst + artifact.json
~/.local/share/dep-maps/mise/v2026.11.2/src/  (same)
~/.cache/codebase-memory-mcp/mise-v2026.11.{1,2}.db                  live DBs (cbm projects)
```
The worktrees are registered in `~/dev/github/jdx/mise/.git/worktrees`. Remove them with
`git -C ~/dev/github/jdx/mise worktree remove …`.

## 4.2 Navigation offline
See §1.3. Any agent with the cbm MCP can pass `project: "mise-v2026.11.2"` and then read source
from `~/.local/share/dep-maps/mise/v2026.11.2/src/<file_path>:<line>`.

## 4.3 Blast radius against this repo's mise usage (prototype `prototype/blast.py`)
Our usage surface: the subcommands called in tracked files, by count: run 109, install 21, exec 14,
lock 13, upgrade 12, use 10, config 10, bootstrap 10, tasks 6, doctor 6, outdated 5, trust 4,
dot 4, tool 3, … For each touched or added symbol, the prototype walks inbound `CALLS` edges up to
depth 4 and keeps those reached from `src/cli/<cmd>.rs`:

| subcommand | changed symbols reached | examples |
|---|---|---|
| run | 24 | `cli/mod.rs::run_at_child_args`, `cli/run.rs::get_affected_task_list`, `parallelize_tasks` |
| tasks | 15 | `tasks/info.rs::display_json`, `tasks/ls.rs::display_json` |
| upgrade | 14 | `backend/mod.rs::install_version`, `tool_update.rs::global_scope_command` |
| lock | 13 | `lock.rs::bind_requests` (signature), `backend/npm.rs::validate_aube_lock` |
| exec | 12 | `shims.rs::err_no_version_set`, `shims.rs::offered_bins` |
| bootstrap | 12 | `bootstrap.rs::run_phases`, `simulate_dotfiles_dry_run` |
| use | 10 | `packslip.rs::auto_sync_skills` |
| dotfiles (`mise dot`) | 6 | `dotfiles/apply.rs::apply_config_entries` |
| install | 5 | `packslip.rs::auto_sync_skills_into` |
| tool | 0 | — |

Limits to fix before relying on it:
- **Name-resolved call noise:** `task/mod.rs::default` "reaches" config, doctor, where, current and
  others. cbm resolves `default()` calls by name. Drop trait-method names (`default`, `clone`,
  `fmt`, …) or use SCIP edges.
- **Surface outside Rust symbols:** settings keys, the config schema and env vars. `docs/settings.toml`
  is a symlink that cbm skipped (`not_indexed_files`). The diff should also compare `settings.toml`
  and `schema/*.json` between tags, plus the release notes.
- The usage surface came from a grep. The real tool should parse our mise TOML `run` lines and Python
  `subprocess` argv lists through the AST (tree-sitter / ast-grep), per AGENTS.md.

## 4.4 SCIP side by side with cbm (prototype `prototype/scipblast.py`)
SCIP run: `rust-analyzer scip .` in the v2026.11.2 worktree took **258 s** and wrote
`index.scip` at **112 MB**, covering 1,018 documents, 1,115,388 occurrences and 514 `src/` files.
`scip expt-convert` wrote a **61 MB** SQLite with the tables documents, chunks, global_symbols
(48,734), mentions and defn_enclosing_ranges.

| | cbm 0.12.1 | SCIP (rust-analyzer) |
|---|---|---|
| time to index mise | ~20 s | 258 s (needs a full cargo metadata and type check) |
| size | 240 MB live DB, 30.6 MB `graph.db.zst` | 112 MB `.scip`, plus 61 MB if converted to SQLite |
| languages | 60+, one binary, no build | one indexer per language, each needs that project's build to work |
| agent tooling | MCP tools today (search_graph, trace_path, get_code_snippet) | none installed. `scip print --json` + jq, or our own code |
| symbol identity | `<project>.<path>.<name>`, resolved by name | type-qualified, e.g. `lib/task/impl#[Task][Default]default().` |
| callers of `Lock::bind_requests` | `bind_and_write_target` (correct) | lock.rs:1301 and :1308, both in `bind_and_write_target` (correct, line-exact) |
| callers of `Task::default()` | 155 edges in 24 files, **10 files wrong** (e.g. `cli/lock.rs`) | 234 refs in 20 files; cbm missed 6 of them (e.g. `task/task_executor.rs`) |
| call inside `measure!` | **missed**: `ts.install_all_versions_with_progress(` at `src/cli/install.rs:720` has no edge. It sits inside `measure!`, and cbm makes no edge for any call inside a `macro_rules!` macro ([other-engines §4.11](other-engines.md)) | found |
| SQLite export detail | n/a | `chunks` only records line ranges of about 100 lines; the occurrence blob is zstd-compressed protobuf. Exact lines come from `scip print --json` (5 s) |

Blast radius, same hunks and depth 4, both engines:

| subcommand | cbm | SCIP | why they differ |
|---|---|---|---|
| run | 24 | 34 | SCIP follows calls cbm misses (not traced) |
| tasks | 15 | 23 | same |
| bootstrap | 12 | 26 | SCIP reaches `packslip::*` and `TaskFetcher::*` through `Run::run` and the install path |
| upgrade | 14 | 11 | cbm `default()` noise |
| lock | 13 | 13 | — |
| exec | 12 | **2** | cbm noise: name-resolved `default()` |
| use | 10 | 8 | noise |
| install | 5 | 8 | calls inside `measure!` (other-engines §4.11) |
| dotfiles | 6 | 4 | noise |
| tool | 0 | 1 | — |

**What this means:** cbm's call edges are wrong in **both** directions: it adds false edges for
common names and drops calls it can't see. The one miss traced (`install`, :720) is a call inside
a `macro_rules!` macro, which cbm never links (other-engines §4.11). A plain method call on a local
links in the §4.11 probe, so "local variables" is not the cause. The `run`, `tasks` and `bootstrap`
gaps are not traced; their cause is unknown. For "what upgrade change can reach my
command" SCIP is the source to trust; cbm stays the agents' browsing tool (search, outline,
snippets) and handles languages SCIP has no indexer for. Not explained yet: SCIP counts
references, not only calls (a function passed as a value counts as well). I spot-checked one
path (`auto_sync_skills`); the rest of the deltas were not checked line by line.

## 4.5 Can generated maps ride on mise dotfiles' private repo? (Q6)
No, not as they are. mise's dotfiles history leaves out regular files over **16 MiB**
(`crates/mise-system/src/history/shadow.rs:25` `MAX_FILE_BYTES: u64 = 16 * 1024 * 1024`,
enforced at `tracked.rs:1217`). There are also limits of 100,000 files and 1 GiB per snapshot
(`shadow.rs:27-29`), and journal blobs are capped at 8 MiB (`journal.rs:23`). The cbm artifact is
30.6 MB and the SCIP index 112 MB, so both would be dropped. The small hand-written registry
(`deps.json`) fits easily.
