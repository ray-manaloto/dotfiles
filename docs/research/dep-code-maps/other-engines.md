---
okf_version: "0.2"
type: "report"
title: "Other engines piloted: REAgraph, graphify, scip-clang, codanna"
description: "REAgraph and graphify as a blast engine, why graphify misses Rust calls, scip-clang on cbm C sources, and codanna scored against SCIP."
timestamp: "2026-11-05T23:00:00Z"
status: "draft"
stale_after: "2026-12-05T00:00:00Z"
tags: [dep-maps, graphify, reagraph, scip-clang, codanna]
sources:
  - id: reagraph
    resource: "https://github.com/Graphify-Labs/REAgraph/tree/83b3c41"
    title: "REAgraph source at the commit read"
  - id: rea
    resource: "https://github.com/morluto/rea"
    title: "rea"
  - id: agent-desktop
    resource: "https://github.com/vercel-labs/agent-desktop/tree/v1.2.0"
    title: "agent-desktop at the pinned tag"
  - id: graphify
    resource: "https://github.com/Graphify-Labs/graphify/tree/v0.9.103"
    title: "graphify source at the latest release"
  - id: scip-clang
    resource: "https://github.com/sourcegraph/scip-clang/tree/v0.4.1"
    title: "scip-clang source at the pinned tag"
  - id: codanna
    resource: "https://github.com/bartolli/codanna/tree/v0.17.1"
    title: "codanna source at the pinned tag"
  - id: cbm
    resource: "https://github.com/DeusData/codebase-memory-mcp/tree/v0.12.1"
    title: "Graph store, export and compare_graphs source at the pinned tag"
---

# Other engines piloted: REAgraph, graphify, scip-clang, codanna

Section numbers (§1-§5, Q1-Q19) follow the working notes this bundle was cut from; the [index](index.md) maps them to pages. Prototype scripts named `prototype/*.py` are throwaway and live outside the repo in `~/.local/state/dotfiles/dep-code-maps/prototype/`.

## 4.6 Compared: REAgraph, rea, agent-desktop

**REAgraph** (Graphify-Labs/REAgraph 83b3c41, v0.1.0-2, Python), a structural diff and memory
layer over REA output:
- It fixes the same class of bug as cbm's compare_graphs prefix problem. Its diff.py header
  (lines 1-19) says a diff by byte offset gives "0 unchanged" (REA #4520).
- Identity is the node id plus the edge key (source, target, relation), never a file location.
  REA ids embed a per-build hash, so across builds it matches on `signature=`: kind, a
  range-normalized label (`normalize_label` strips `@line:col` spans) and the source file, with a
  stable ordinal to break ties.
- align.py matches stripped nodes by relation-typed Weisfeiler-Lehman colour (confidence 0.70,
  line 58) and falls back to seed propagation (lines 17-46).
- memory.py stores plain JSON graphs (load/save/merge, edge_key at line 51). cache.py is a
  content-addressed store (canonical JSON + sha256).
- **Fit:** it confirms the depdiff.py design: strip the location or prefix from identity, then
  match by signature. Its WL alignment is a pattern for renames and moves, which neither cbm nor
  depdiff handles. It's not needed for source deps, where SCIP symbols are already build-stable.
  Worth citing in the upstream cbm issue as prior art.

**rea** (morluto/rea 0beedcd71, rea-agents 6.8.0, TypeScript MCP), reverse engineering of
binaries and bundles:
- Android (jadx: src/android/JadxSession.ts), Apple Mach-O (src/artifacts/apple/*), Electron/JS,
  .NET, EVM, pcap, plus ghidra/hopper/ida/frida bridges.
- Desktop: an X11 observer (src/desktop/X11WindowObserver.ts) and a macOS AX bridge (bridge/native/ReaNativeUI.swift, actions limited to AXPress, AXIncrement/AXDecrement and AXValue at :111-115).
- **Fit:** it's a sensor for deps with no source. Not needed here: mise, cbm, agent-desktop and
  the JBR all have source at the pinned tag. A JVM-only dep (a CLion plugin jar) would need jadx;
  rea wraps it only for APK/DEX. Not a dep-maps engine.

**agent-desktop** v1.2.0 (vercel-labs/agent-desktop 2b0a7334): mapped as cbm project
`agent-desktop-v1.2.0` (48,047 nodes, 245,117 edges, persistence artifact written). It is a
deps.json candidate (global config pins 1.2.0). The CLion use case is in
local working notes. Reading agent-desktop together with the JBR at CLion's runtime tag
explained the CLion failures from file:line. That was the dep-maps workflow working on a real
problem.

## 4.7 REAgraph as a third blast-radius engine (prototype `prototype/rgblast.py`)

REAgraph has no impact walk of its own. It gives a structural diff (`reagraph diff`,
diff.py:153-200), and `query` hands off to graphify (cli.py:315-320). So the pipeline is:
graphify 0.9.102 `update` on each tag's worktree, then `reagraph.diff.diff` (stdlib, run from
source with `-I`, nothing installed), then a reverse walk over `calls` edges, depth 4.

**Cost:** about 48 s per tag for graphify (57,749 nodes, 126,010 links, a 57 MB graph.json). The
diff plus walk takes 1.4 s.

**Identity is right by construction:** graphify ids are path-based with no tag or project prefix
(`src_cli_lock_lock_bind_requests`). So an id-keyed diff gives 54,349 unchanged, 2,639 added,
2,415 removed and 761 rewired nodes: no prefix churn, unlike cbm compare_graphs. Much of the
added/removed set is docs/changelog nodes with positional ids. Restricted to Rust under
`src/`: 294 seeds.

**What it can't see:** body-only changes. "Rewired" means an incident edge changed. Nodes carry
only a start line (`source_location: L1823`), no end line and no signature, so hunk mapping has
to use the nearest preceding function (`hunks` mode, 114 seeds versus SCIP's 111).

| subcommand | cbm | SCIP | REAgraph diff seeds | git hunks → graphify |
|---|---|---|---|---|
| run | 24 | 34 | 45 | 9 |
| tasks | 15 | 23 | 6 | 7 |
| bootstrap | 12 | 26 | 14 | 4 |
| upgrade | 14 | 11 | 19 | 13 |
| lock | 13 | 13 | 19 | 11 |
| exec | 12 | 2 | 5 | 4 |
| use | 10 | 8 | 11 | 7 |
| install | 5 | 8 | 1 | 0 |
| dotfiles | 6 | 4 | 13 | 3 |
| tool | 0 | 1 | 0 | 0 |

**Why it under-reaches:** graphify's Rust call graph is mostly within a file. Of 34,680 Rust
`calls` edges, 28,285 (82%) join two nodes in the same file; only 6,395 cross files, and 3,534
of those are INFERRED.
- `Task::default` has 2 callers, both tests in task/mod.rs. SCIP has 234 references, cbm 155.
- The `ts.install_all_versions_with_progress(` call at src/cli/install.rs:720 has no edge. The
  only caller is in-file (`install_all_versions`). That is the same miss cbm has, and why
  `install` scores 0 or 1.
- Precise when it does link: `bind_requests` ← `bind_and_write_target` matches SCIP exactly.

**Verdict:** for Rust blast radius it ranks below cbm and well below SCIP. The REAgraph diff
counts are higher only because each new or rewired node is a seed: it counts differently, it
doesn't cover more. Worth keeping:
- graphify's stable path ids, which give a prefix-free diff (prior art for the upstream issue);
- REAgraph's WL alignment, for renames and moves;
- `reagraph attest` (source↔binary).

The proposal is unchanged (cbm in the hook, SCIP in the update flow). REAgraph/graphify isn't
added as an engine.

## 4.8 Why graphify's Rust call graph falls short of cbm and SCIP (source at the latest release)

**Source:** Graphify-Labs/graphify, cloned to ~/dev/github/Graphify-Labs/graphify. Worktrees:
- `~/.local/share/dep-maps/graphify/v0.9.102/src` (installed; `diff -rq` against the installed
  site-packages differs only in extractors/MIGRATION.md);
- `.../v0.9.103/src` (latest on PyPI, 2026-11-05). The repo's `v1.0.0` tag is from 2026-04-05,
  so it isn't the latest.

**Which release is latest (decide by date, not by version number):** graphify's tags do not sort
by version. `v1.0.0` (2026-04-05, commit 0a31c086) is an old tag, and the project has since gone
back to 0.9.x. To pick the latest, use release dates:
- `gh release list -R Graphify-Labs/graphify` marks v0.9.103 (2026-11-05T16:35Z) **Latest**.
  v1.0.0 is a GitHub release too, but it was published on 2026-04-05.
- v1.0.0 is not an ancestor of v0.9.103 (`git merge-base --is-ancestor`), so it sits on a side
  line.
- PyPI `graphifyy` has no 1.0.0 at all. Its newest upload is 0.9.103 (2026-11-05), the version
  `mise latest` reports.
- Rule for the update flow: take the latest from the GitHub releases page by `publishedAt`, or
  from PyPI upload time, never from a semver sort of the git tags.

**Every graphify number in §4.7 and §4.8, by version:**
| measurement | version |
|---|---|
| §4.7 mise v2026.11.1 and v2026.11.2 graphs, REAgraph diff, blast-radius table | 0.9.102 (installed pin) |
| §4.8 call-form table (125,767 call sites, tree-sitter count via `gfyclass.py`) | 0.9.102 rules |
| §4.8 file:line citations | 0.9.102 |
| cbm map `graphify-v0.9.103` | 0.9.103 source |
| re-check below | 0.9.103 |

**Re-check on 0.9.103 (2026-11-05):** I mapped mise v2026.11.2 again with the installed
graphify 0.9.103 into `~/.local/share/dep-maps/mise/v2026.11.2-gfy0.9.103/`. Its graph.json
records `graphify_version: "0.9.103"`.
- An earlier run of the 0.9.103 source on the 0.9.102 install recorded "0.9.102", because the
  field comes from the installed package's metadata. That run is kept in the scratchpad.
- 0.9.102 gave 57,749 nodes and 126,010 links; 0.9.103 gives 57,678 and 125,997.
- Both give 34,645 Rust→Rust `calls` edges, of which 28,285 (81.6%) are same-file.
- The Rust call-edge sets are identical: the symmetric difference is 0.
- From 0.9.102 to 0.9.103 nothing changed under `graphify/languages/`, `symbol_resolution.py`
  or `scip_ingest.py`. The `extract.py` and `extractors/resolution.py` changes cover JS, C#,
  ObjC/C++ headers and Python names (#4989, #4994), plus a rule that drops name-only calls to
  source-less stubs.
- So the §4.8 verdict holds at the latest release.
- §4.7 re-run on 0.9.103: I mapped v2026.11.1 with the installed 0.9.103 too
  (`v2026.11.1-gfy0.9.103/`) and ran `prototype/rgblast.py` on the pair. Both seed modes match the
  0.9.102 table exactly: diff mode has 294 seeds and hunks mode 114, with the same count for every
  subcommand.
- `rgblast.py` now strips a leading `<tag dir>/src/` from `source_file`. graphify writes paths
  relative to the cwd it ran in, so the 0.9.102 maps (run from the parent folder) have that prefix
  and the 0.9.103 maps (given an absolute path) don't. Before this fix, the 0.9.103 run showed 0
  for every subcommand. That came from the path mismatch, not from graphify.

v0.9.102→v0.9.103 doesn't touch extractors/rust.py or symbol_resolution.py, and none of its
extract.py hunks mention Rust. So the mise graph built with 0.9.102 stands for the latest.

**Map:** cbm project `graphify-v0.9.103`: 19,480 nodes, 75,763 edges, 5 s, persistence artifact
12.2 MB.

graphify parses each file with tree-sitter (extractors/rust.py `extract_rust`, 277-1120) and has
no type information. It keeps a call only if it is sure of the target, so these rules drop most
cross-file calls:

1. **Method calls on anything but `self` never cross files.**
   - rust.py:993-1000 marks `x.m()` as a member call. Cross-file it is queued as a raw call
     (1083-1095).
   - The shared cross-file pass then skips every member call (extract.py:11692-11695), to avoid
     binding `obj.log()` to any `log` in the corpus.
   - The only recovery is `_resolve_rust_self_member_calls` (extract.py:7927-8077), which handles
     only `self.m()`, where the receiver type is known from syntax.
   - That is the `ts.install_all_versions_with_progress(` miss at src/cli/install.rs:720.
2. **`Type::f()` never crosses files.**
   - rust.py:1001-1013 resolves `Type::f()` only against impls in the same file (1019-1030).
   - Across files, `rust_scoped_call_survivors` (symbol_resolution.py:348-412) returns `[]` when
     the last qualifier segment is UpperCamelCase: "an UpperCamelCase segment is a type ... keeps
     its pre-existing skipped behavior". That is why `Task::default` has 2 callers.
3. **Common names are dropped outright.**
   - `_RUST_TRAIT_METHOD_BLOCKLIST` (rust.py:189-195) has 43 names: new, default, get, run,
     build, lock, install-adjacent verbs and others. A call to one of them is never queued
     cross-file (rust.py:1083).
4. **Trait dispatch and inferred calls are invisible.**
   - `..Default::default()`, `T::from`, `?` conversions, operator traits and generic bounds need
     type inference. Only rust-analyzer (SCIP) has it.
   - Macro arguments are scanned only for 27 expression macros (rust.py:207-213).
5. **Only free functions resolve across files**, and only `mod::f()` whose qualifier matches the
   file path (symbol_resolution.py:348-412), plus bare `f()` through the name tie-breakers.
6. **No end line or signature on nodes** (`source_location: "L1823"` only). A diff can't tell a
   body change apart from no change, and hunks map only to "nearest preceding function".
7. **SCIP ingest exists but can't help.** scip_ingest.py:1-30 says "Not wired to the CLI in
   this phase". It reads a "simplified" shape with occurrences on each symbol, not on each
   document as in real SCIP. A real `rust-analyzer scip` index puts its references on the
   documents, so it would give no call edges.

**Measured on mise v2026.11.2** (`prototype/gfyclass.py` reuses graphify's own blocklist
and tree-sitter-rust from the installed venv):

| call form | sites | share | graphify across files |
|---|---|---|---|
| `x.m()`, receiver not `self` | 41,590 | 33.1% | dropped (rule 1) |
| `x.m()` blocklisted name | 35,702 | 28.4% | dropped (rule 3) |
| bare `f()` | 21,059 | 16.7% | name match |
| `Type::f()` | 14,514 | 11.5% | dropped (rule 2) |
| `mod::f()` | 8,801 | 7.0% | path-matched |
| `self.m()` | 3,185 | 2.5% | self pass |
| other | 916 | 0.7% | — |

So about 73% of mise's 125,767 call sites can bind only to a target in the same file (rules
1-3). That matches the 82% same-file share of graphify's edges.

**What each tool does instead:**
- **cbm** resolves member and type calls by name across files. It finds them (155 for
  `Task::default`) but over-counts on common names, the opposite failure.
- **SCIP** uses rust-analyzer's type inference: 234 references, exact.

graphify picked precision over recall on purpose (#908, #543/#1219). For blast radius, a missed
edge hides a real impact, so recall matters more there. graphify is the wrong engine for Rust
deps, though its path-based ids remain the prior art for a prefix-free diff.

## 4.9 scip-clang 0.4.1 on cbm v0.12.1, scored against cbm (prototype `prototype/cscore.py`)

Goal: does C have a SCIP-grade engine, so cbm could get a blast radius too (Q17 said no)?
- **Compile database:** cbm builds with one Makefile. I added `-MJ` through a Python wrapper
  (`mjcc.py`, `CC="env MJ_TOOL=clang python3 -I mjcc.py"`, `make -B`): 171 fragments. Makefile.cbm
  builds `PROD_SRCS` (257 files) in one compile+link command without `-c`, so I synthesized those
  257 entries from its flags (`-Werror` dropped, `-c <file> -o /dev/null` added): 428 entries.
- **Compiler:** Homebrew LLVM clang 23.1.4 from the global mise config's `CC`/`CXX`
  (config.toml:96-98, DL-766); not a mise pin. scip-clang embeds LLVM 21.1.8
  (`_LLVM_COMMIT` 2078da43 at fetch_deps.bzl:7) and runs the compdb compiler only for
  `-print-resource-dir` (indexer/CompilationDatabase.cc:127-134), so builtin headers come from clang 23.
- **Full compdb:** 428 TUs, 604 s, 3.3 GB index, 1 TU timeout (`grammar_lean.c`). The vendored
  tree-sitter grammars dominate. Deleted.
- **Own sources only** (`own_compdb.json`, grammars and vendored code left out): 259 TUs, **2.0 s**,
  **46 MB**, 0 errors, 516 documents, 1,124,567 occurrences.
- scip-clang 0.4.1 writes **no `enclosing_range`** on definitions, so callers are attributed with
  cbm's function line ranges on both sides; the score isolates call-target resolution.

| | count |
|---|---|
| cbm CALLS (both sides index the file) | 39,403 |
| scip-clang reference edges | 33,722 |
| agree | 30,991 |
| **cbm recall / precision** | **0.919 / 0.787** |

- 6,296 of the 8,412 cbm-only edges go to cbm's libc wrappers in
  `src/foundation/mem_override_libc.c`; scip-clang resolves those calls to the system headers. Without
  them cbm's precision is ~0.936. Other cbm-only callees include duplicate static names bound to the
  wrong copy (`heap_strdup` 119).
- scip-only callees: `cbm_ts_child_by_field_name` 522, `cbm_arena_alloc` 386, `cbm_log` 265,
  `cbm_arena_sprintf` 212, `cbm_arena_strdup` 168. **Why cbm misses these is unexplained** (macro
  wrappers are a lead, not checked).
- Probes agree exactly: `graph_node_compare` 2/2, `graph_prepare_node_cursor` 1/1, `cbm_store_open` 1/1.
- **Verdict:** for C, cbm's edges are much closer to a compiler's than they are for Rust. scip-clang is
  fast on own sources, but needs a compile database that cbm's build doesn't emit. Q17 (no cbm blast)
  stands; scip-clang is the engine if that changes.

## 4.10 codanna 0.17.1 on mise v2026.11.2, scored against SCIP (prototype `prototype/codannascore.py`)

- Run with `mise x github:bartolli/codanna@0.17.1`, no config change. It registers projects in
  `~/.codanna/projects.json`.
- Semantic embeddings are **on by default**: `impl Default for SemanticSearchConfig` sets
  `enabled: true` (src/config/mod.rs:375-378; the serde default is false at :199-200), and the generated
  settings.toml had `enabled = true` (line 232). I set it false before indexing; no model was downloaded.
- Indexed `src/` in **12.6 s**: 20,422 symbols, 40,100 relationships (Calls 21,882, Uses 13,439,
  Defines 4,687, Implements 92), 19 MB. `codanna dump` writes JSON Lines (src/dump.rs:94-127).
- Mapping: 12,653 of 12,876 codanna functions map to SCIP symbols by file, start line (+3) and name;
  324 calls touch unmapped functions.

| | count |
|---|---|
| SCIP src/ functions / reference edges | 12,651 / 26,750 |
| agree | 16,576 |
| **codanna precision / recall** | **0.920 / 0.620** |

Probes: `Task::default` callers codanna 34 vs SCIP 160 (all 34 agree); `bind_requests` 1/1;
`install_all_versions_with_progress` 1 of 2.

Blast at depth 4, same 110 touched functions:

| subcommand | cbm | SCIP | codanna |
|---|---|---|---|
| run | 24 | 34 | 15 |
| tasks | 15 | 23 | 10 |
| bootstrap | 12 | 26 | 6 |
| upgrade | 14 | 11 | 11 |
| lock | 13 | 13 | 10 |
| exec | 12 | 2 | 6 |
| use | 10 | 8 | 8 |
| install | 5 | 8 | **0** |
| dotfiles | 6 | 4 | 4 |
| tool | 0 | 1 | 0 |

- **Verdict:** codanna is more precise than cbm on Rust but misses 38% of SCIP's edges, so it doesn't
  replace SCIP for blast radius. **Why `install` is 0 is unexplained.** The 8% of codanna edges not in
  SCIP were not spot-checked.
