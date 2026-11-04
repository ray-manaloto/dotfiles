---
okf_version: "0.2"
type: "concept"
title: "codebase-memory-mcp tools, hooks and agents"
description: "What CBM 0.12.1 gives Claude Code and Codex: a tree-sitter code graph with an in-binary type resolver, 13 read-only tools (blast radius via detect_changes and trace_path), per-client hooks, and three agent tiers."
package: "github:DeusData/codebase-memory-mcp"
version: "0.12.1"
timestamp: "2026-11-03T23:50:00Z"
status: "draft"
tags: [codebase-memory-mcp, mcp, tree-sitter, hooks, agents, blast-radius]
sources:
  - id: cbm-readme
    resource: "https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/README.md"
  - id: cbm-mcp
    resource: "https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/src/mcp/mcp.c"
    title: "Tool profiles (analysis = 13 tools, scout = 8)"
---

# codebase-memory-mcp tools, hooks and agents

## The graph

- Parsing: tree-sitter, 162 grammars compiled into the binary. One index per project under the account cache.
- "Hybrid LSP" in CBM is an in-binary type resolver used to attribute calls; it is not a language server and does
  not replace one. Native LSP in Claude Code is a separate question (see the LSP bundle).
- Graph: nodes such as Project, Folder, File, Module, Class, Function, Method, Variable, Route, Resource; edges such
  as CALLS, IMPORTS, DEFINES, INHERITS, IMPLEMENTS, HTTP_CALLS, TESTS, SPAWNS, FILE_CHANGES_WITH.
- Known C/C++ gaps: calls attributed to the Module node (#220); qualified-name `trace_path` lookups (#1365).

## Tools

13 read-only tools (the `analysis` profile): search_graph, query_graph (Cypher), trace_path, get_code_snippet,
get_file_outline, get_graph_schema, compare_graphs, get_architecture, search_code, list_projects, index_status,
check_index_coverage, detect_changes. Four more mutate state: index_repository, delete_project, manage_adr,
ingest_traces. The `scout` profile has 8.

Blast radius: `detect_changes` maps a Git diff against a base (default `origin/main`) to changed symbols and their
inbound callers; `trace_path` walks callers and callees to a depth. No precision or recall study of
`detect_changes` exists.

## Hooks

| Client | Events | Effect |
|---|---|---|
| Claude Code | SessionStart (startup, resume, clear, compact), SubagentStart | adds `[codebase-memory]` session context: project, index status, the agent tiers |
| Claude Code | PreToolUse `Grep\|Glob\|Bash` | adds graph symbols that match the search; never blocks |
| Claude Code | PostToolUse `Read` | coverage feedback for partially indexed files |
| Codex | SessionStart, SubagentStart | dynamic graph context; no search augmentation |

Each hook runs `codebase-memory-mcp hook-augment` with a 5 s registration timeout and a 2 s internal deadline. Hooks
only connect to a running daemon and never start one; an MCP session starts it. Measured: ~205 ms per call with a
daemon, ~465 ms and no output without one. Every call hashes the ~330 MB executable (#2683, #2834).

## Agents

Three tiers for each client: `codebase-memory-scout` (Tier 1, quick, provisional), `codebase-memory` (Tier 2,
verification, falls back to reading and grep) and `codebase-memory-auditor` (Tier 3, full graph verification). Their
tool lists exclude the mutating tools. The Codex role files name the launcher and their tool profile.

## Daemon

One per runtime namespace, shared by every client in it; the default setup (no `CBM_RUNTIME_DIR`) has one per
account. Every process in a namespace must be the same build with the same cache root.
The default is session-managed: it starts with the first session and stops after the last. `daemon start` keeps one
running; `daemon stop` refuses while sessions use it.
