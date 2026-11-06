---
okf_version: "0.2"
type: "report"
title: "Rust call graphs: cbm's gaps, and SCIP checked against Charon, CGA and rustc MIR"
description: "Why cbm's run, tasks and bootstrap blasts fall short of SCIP's, the SCIP range fix for #[async_trait], and how exact SCIP's call edges are against compiler-resolved calls."
timestamp: "2026-11-06T12:00:00Z"
status: "draft"
stale_after: "2026-12-06T00:00:00Z"
tags: [dep-maps, codebase-memory-mcp, scip, rust, charon, cga, mir]
package: "github:DeusData/codebase-memory-mcp"
version: "0.12.1"
sources:
  - id: cbm
    resource: "https://github.com/DeusData/codebase-memory-mcp/tree/v0.12.1"
    title: "Registry, import and call-pass source at the pinned tag"
  - id: mise2
    resource: "https://github.com/jdx/mise/tree/v2026.11.2"
    title: "mise at the pilot's new tag"
  - id: ra
    resource: "https://github.com/rust-lang/rust-analyzer/releases/tag/2026-11-02"
    title: "rust-analyzer release used for SCIP"
  - id: charon
    resource: "https://github.com/AeneasVerif/charon"
    title: "Charon 0.1.311 (2bceb7c)"
  - id: cga
    resource: "https://github.com/OpenDevicePartnership/cga"
    title: "CGA at 2fc6310"
---

# Rust call graphs: cbm's gaps, and SCIP checked against Charon, CGA and rustc MIR

Section numbers (§1-§5, Q1-Q30) follow the working notes this bundle was cut from; the [index](index.md) maps them to pages. Prototype scripts named `prototype/*.py` are throwaway and live outside the repo in `~/.local/state/dotfiles/dep-code-maps/prototype/`.

## 4.12 Why cbm's run, tasks and bootstrap blasts fall short of SCIP's (prototype `prototype/gapclass.py`)

`gapclass.py` maps cbm's functions into SCIP's symbols (file + name + start line; all 111 touched
functions map) and walks both engines over the same touched set at depth 4. It reproduces [§4.4](pilots.md):
cbm reaches run 23, tasks 16, bootstrap 12 ([§4.4](pilots.md): 24, 15, 12). For each (touched function, command)
pair that SCIP reaches and cbm doesn't (47 pairs across run, tasks, bootstrap, install and lock; 45 before the §4.13 range fix), it
follows SCIP's shortest path and classifies the first edge cbm lacks by parsing its call site with
cbm's vendored Rust grammar. Only 10 distinct edges cause all 47:

| pairs | missing edge | site | cause |
|---|---|---|---|
| 10 | `Bootstrap::run_task` → `Run::run` | bootstrap.rs:3162, `Run { … }.run().await` | name cap on `run` |
| 10 | `Run::run_task_sched` → `TaskExecutor::run_task_sched` | run.rs:1969, `self.executor.as_ref().expect(…).run_task_sched(ctx)` | name fallback lands on the caller itself, then the self-edge is dropped |
| 10 | `Bootstrap::run_phases` → `Upgrade::run` | bootstrap.rs:2668, `Upgrade::new_bare(…).run().await?` | name cap on `run` |
| 8 | `Commands::run` → `Run::run` | tasks/mod.rs:72, `Self::Run(cmd) => (*cmd).run().await` | name cap on `run` (self-edge below the cap) |
| 4 | `install_missing_runtimes` → `install_all_versions_with_progress` | install.rs:720 | inside `measure!` ([§4.11](other-engines.md)) |
| 3 | `prepare_tasks` (or `run_tasks`), `setup_executor`, `setup_output_and_validate` → `…::new` | run.rs:1789 (or :1007, the same `TaskFetcher::new` call), :1894, :1808 | name cap on `new` (261 entries, see below) |
| 2 | `drop_what_needs_trust` → `aube_graph_names_only_registry`; `new_for_inspection` → `TaskFetcher::for_inspection` | lockfile.rs:5463, task/deps.rs:164 | the function is passed as a value, not called; SCIP counts the reference |

**Cause 1, the name cap.** When the Rust LSP can't type a receiver, the call falls back to the
registry's name lookup. That lookup returns nothing for a name with more than 256 definitions
(`REG_MAX_CANDIDATES`, src/pipeline/registry.c:22; the bail-out at :1760 in `resolve_name_lookup`).
The comment at :15-21 explains it: the kernel's `list_head` has 7,188 candidates, a pick among them
is noise, and scoring them cost ~900 s. mise's graph has **322** Function/Method nodes named `run`
and 256 named `new`. The cap is checked before the qualified-tail match (`qualified_suffix_match`,
strategy 3.5 at :1709), so a fully written path such as `other::Other::new()` loses its edge too.

**Cause 2, the self-edge.** Below the cap, an untyped `x.run_task_sched()` inside a method also
named `run_task_sched` is scored by import distance (`best_by_import_distance`, registry.c:1729-1741, or :1479-1520 when the file has imports),
which picks the caller's own definition. The call pass drops an edge whose target is its source
(src/pipeline/pass_parallel.c:3514). With a differently named caller, the same call gets a
**wrong** edge instead (to the caller's class, not `TaskExecutor`), so this is the same failure
that makes [§4.4](pilots.md)'s false `default()` edges.

**Confirmed with a probe** (`prototype/probes/cbm-chain-probe`, cbm 0.12.1, mode full, then
deleted):
- with few `run`s: `Commands::run` → `(*cmd).run()` and `Sched::run_task_sched` →
  `executor…run_task_sched()` get no edge. The same bodies in `dispatch` and `sched_other` get one,
  to the wrong target (`Commands.run`, `Sched.run_task_sched`, by `suffix_match`). A cross-file,
  async `Upgrade::new_bare(…).run().await?` links by `suffix_match`.
- after adding 300 structs each with `run` and `new`: the `suffix_match` edges to `run`
  (cross-file `Upgrade::run`, `dispatch`) and the `qualified_suffix` edge for `other::Other::new()`
  disappear. LSP-typed edges (`lsp_method_dispatch`, `lsp_direct`) stay.

**Not explained:**
- In the probe the LSP types `run::Run { n: 2 }.run().await` (`lsp_method_dispatch`); in mise it
  doesn't type `Run { … }.run()` at bootstrap.rs:3162. The cap only matters because the LSP missed
  first; why it missed is not traced.
- Why the LSP doesn't type the three `::new` calls in the first place.

**Why `import_map` misses `OutputHandler::new` (traced, probe-confirmed):** a grouped `use` is a
single import whose key is the literal brace text.
- `parse_rust_imports` (`internal/cbm/extract_imports.c:1099-1127`) emits one import per
  `use_declaration`, with `module_path` set to the whole text after `use` and
  `local_name = path_last(full)`. `path_last` (`:99-113`) cuts after the last `/ . : \`, so
  `use crate::task::task_output_handler::{OutputHandler, SummaryOutcome};` (run.rs:27) gets the
  local name `{OutputHandler, SummaryOutcome}`.
- The IMPORTS edge stores that string as `local_name` (`src/pipeline/pass_parallel.c:1862-1866`).
  The index has it: run.rs's edge is `{OutputHandler, SummaryOutcome}` → `…task_output_handler.OutputHandler`.
  The target is the first name only.
- The call-time import map is built from those edges, so its key is the same `local_name`
  (`src/pipeline/pass_lsp_cross.c:1007`, read at `:1054-1066`).
- `registry_resolve_chain` splits `OutputHandler::new` at the first `::`, giving prefix
  `OutputHandler` and suffix `new` (`src/pipeline/registry.c:1785-1807`). `resolve_import_map`
  (`:1350`) then looks for the key `OutputHandler` by exact match (`:1360-1368`), finds nothing
  and returns empty (`:1370-1371`). The `import_map_suffix` fallback (`:1408-1432`) is never
  reached.
- `same_module` (`:1815`) misses, since `new` isn't in `cli.run`. The name lookup (`:1819`) hits
  the 261-entry cap.

Probe `prototype/probes/cbm-import-probe`, with cbm 0.12.1 in mode `full`:
- `h.rs` defines `Handler::new`. `a.rs` has `use crate::h::{Handler, Other};` and `b.rs` has
  `use crate::h::Handler;`, and both call `Handler::new()`. `many.rs` adds 300 more `new`s.

| caller | IMPORTS `local_name` | 300 extra `new`s | without them |
|---|---|---|---|
| `b.rs single` | `Handler` | edge, `import_map` | edge, `import_map` |
| `a.rs grouped` | `{Handler, Other}` | **no edge** | edge, `unique_name` |

So a grouped import never works as an import-map key. Calls through it rely on the LSP or the
name lookup, and above the cap there is nothing left. In mise, **1,912 of the 5,172** Rust IMPORTS
edges have a `{…}` local name. Upstream main 612eee25 has the same parser
(`extract_imports.c:1900`, the body is identical) and the same lookup (`registry.c:1859`, called at `:2319`).

The same edges also show a second, separate fault: a single-name import can point at the wrong
node. For example, `Arc` → `mise-system…history.sync.run.sync` and `Mutex` → the same function.
It is traced in the next block.

This could be a fourth upstream issue: split a `use_list` into one import per member (including
`self` and `as` aliases), each with its own local name and its full path.

**Why std and external-crate imports link to same-named mise nodes (traced; fifth issue
candidate).** All citations are `src/pipeline/pass_pkgmap.c` at v0.12.1:
- `cbm_pipeline_resolve_import_node` (`:2736`) sends every non-PHP import to
  `resolve_import_strategies` (`:2779`, defined at `:2300`). Strategy 1 resolves the module path,
  1b tries a sibling file, and 2 uses the namespace map. None of them finds `std::sync` in mise,
  so it falls through.
- Strategy 3 is the symbol-name fallback (`:2428-2532`). Its candidates are the imported symbol,
  then the path's segments walked from the end, deduped, at most 8 (`:2467-2469`). For each one,
  `cbm_gbuf_find_by_name` takes any targetable node of that simple name in another file, and the
  lexicographically smallest QN wins (loop from `:2501`, `return best` at `:2531-2532`).
- The only gate is `cbm_import_symbol_fallback_allowed` (`:1818-1820`: `return lang != CBM_LANG_GO;`).
  The only check for an external module is Python's #2127 (`py_external`, `:2496-2500`): an import
  from outside the project may only match a node that spells its chain. Nothing checks a Rust
  path's root: `std`, `core`, `alloc` and crates.io crates all go through.
- So for `use std::sync::Arc`, no node is named `Arc`; the next segment `sync` matches mise's
  `sync` function. For `use std::iter::once`, the walk goes `once`, then `iter`, which matches
  `InstallDependencyDeclarations.iter`.
- The import map is built from these IMPORTS edges (`pass_lsp_cross.c:1007`, read at `:1054-1066`),
  so a call to the imported name inherits the wrong target as an `import_map` CALLS edge.
- Upstream main 612eee25 still has it: the gate at `:1818`, Strategy 3 at `:2512`, `py_external` at
  `:2582`, `cbm_pipeline_resolve_import_node` at `:2833`.

How much it hits mise v2026.11.2:
- Imports, from the top-level `use` declarations matched to their IMPORTS edges. A path root
  counts as local when it is `crate`, `self`, `super`, a workspace crate, or a `mod` declared in
  the same file (`mod tool_versions;` then `use tool_versions::ToolVersions`). A `pub(crate) use`
  prefix is stripped before reading the root.
  - 1,135 have a std/core/alloc root and an in-repo target.
  - 907 have another crate's root and an in-repo target. Of these, 900 are roots declared as
    dependencies in a mise `Cargo.toml`, and no workspace crate is renamed as a path dependency.
    The other 7 (`expr`, `packages`, `usage`, and 2 with an empty root) aren't counted.
  - That leaves **2,035 of 5,172 (39%) certainly wrong**: an import from std or a crates.io crate
    can't resolve to mise's code.
  - The first count, 2,230 (43%), also took same-file `mod`s and `pub(crate) use` lines for
    external crates. A side agent flagged it.
  - A further 1,152 in-repo imports have a target that looks off. Re-exports make some of those
    right, so they aren't counted.
- Calls: of the **835** Rust `import_map` CALLS edges, I matched each callee's first segment to the
  `use` in the caller's file. **55 (6.6%) are wrong**: 28 go through a std `use` and 27 through a
  `use` of a crates.io dependency (`serde_json` 15, `console` 6, `shell_escape` 3, `glob`, `log`,
  `eyre`).
  - Same-file `mod`s count as local, which removed 10 false hits such as
    `use tool_versions::ToolVersions`.
  - The 5 through `packages` aren't counted. `crates/mise-system/src/lib.rs:86` has
    `pub use mise_system_packages as packages;`, a workspace crate under an alias, and their
    target `AppSpec.parse` is correct.
  - The first report said 70, then 60.
  Examples:

| caller | call | through | cbm's target |
|---|---|---|---|
| `src/watch_files.rs`, `src/task/task_list.rs` | `once` | `use std::iter::once` | `InstallDependencyDeclarations.iter` (19 edges in all) |
| `crates/mise-system/src/history/watch/runtime.rs` | `json` | `use serde_json::json` | `mise-util…http.Client.json` (15) |
| `src/cli/doctor/mod.rs` | `split_paths` | `use std::env::split_paths` | `benchmarks/perf-fixture/mise.env` (7) |
| `src/cli/tasks/deps.rs` | `style` | `use console::style` | `docs/vitepress/showreel-capture/frames.Encoder.style` (6) |

  55 is a lower bound for wrong `import_map` calls. The other 780 go through mise's own paths and
  weren't checked further. Counts come from two throwaway
  scripts outside the repo.
- Blast effect: a wrong edge adds a false caller (`once` callers show up in the blast of
  `InstallDependencyDeclarations::iter`). It doesn't hide a real one, because std and external
  callees aren't in the graph anyway. So this inflates blast and never shrinks it.

Proposal (fifth upstream issue candidate): skip the symbol-name fallback, like the Python #2127
guard does, for a Rust import whose first segment isn't `crate`, `self`, `super`, `$crate`, a `mod`
of the importing crate or a workspace crate. Alternatively, never fall back past the imported
symbol to a module segment such as `sync` or `iter`.

**Registry bucket sizes, dumped (the three `::new` misses do hit the cap).** Which nodes go in:
- Every definition whose label passes `cbm_label_is_registry_symbol` (`internal/cbm/helpers.c:196`)
  is registered (`pass_parallel.c:1784`, `pass_definitions.c:445`). The labels are Function,
  Method, the type-like labels, Variable, Constant, Field, Table, View and Model.
- The key is the QN's last segment (`registry.c:1250-1253`, `simple_name` at `:115`). The lookup
  is case-sensitive, so `whip.ts`'s `NEW` goes in a separate bucket.
- The bucket isn't split by language. Modules and Folders don't go in.

Counted from the index's distinct QNs with those labels:

| bucket | entries | made of |
|---|---|---|
| `new` | **261** | 256 Method, 4 Variable (`new=` in the e2e shell tests `e2e/backend/test_pipx_uv_global_upgrade:79`, `e2e/cli/test_install_layout_{legacy,migrate,migrate_aube_slow}`), 1 Field (`DirenvDiff.new`, src/direnv.rs:20) |
| `run` | **357** | Method, Function, Field, Variable |
| `default` | 61 | Method, Field, Variable, Class |

So `new` is over the cap only because of the 4 shell variables and 1 Rust field; with Rust methods
alone it would be exactly 256 and pass. The index agrees. No edge into any `new` or `run` target
comes from the name-lookup strategies (`qualified_suffix`, `unique_name`, `suffix_match`). Their
edges are all `lsp_*`, `import_map` or `same_module`, the strategies that run before the cap. By
contrast, `default`, under the cap, gets 135 `qualified_suffix` and 869 `suffix_match` edges.
`setup_output_and_validate` (run.rs:1798-1850) has edges at lines 1812-1846 and none at 1808.

**What it means for blast:** cbm's misses on mise are not random. 38 of 47 come from the four
`run`-family edges, all at the entry of a subcommand. Any project with a common method name over
256 definitions loses every untyped call to it, and the probe shows the qualified path doesn't
save it. SCIP stays the blast engine (Q9); this is a third upstream issue candidate (the cap should
come after `qualified_suffix_match`).

## 4.13 Charon and CGA against SCIP on mise v2026.11.2 (prototype `prototype/cgscore.py`)

Both tools run inside rustc, so their call targets are compiler-resolved. That makes them the
closest thing to ground truth for SCIP's call edges. Their outputs are streamed with ijson
(`charonstream.py`, `charonedges.py`, `cgaedges.py`). `json.load` on Charon's 3-4 GB ULLBC peaked at
52 GB; the stream peaks at 12 MB.

**SCIP range bug (fixed in every prototype: cgscore.py, scipblast.py, and, behind `SCIP_FIX_GRAMMAR`,
gapclass.py, codannascore.py and installpath.py).**
- rust-analyzer gives every method of an `#[async_trait]` trait or impl the whole block as its
  `enclosing_range`. `Backend#description()` and 89 other `Backend` methods all cover
  src/backend/mod.rs:3113-6795, and the impl blocks in aqua.rs, npm.rs, github.rs, vfox.rs, rust.rs,
  node.rs and others do the same.
- 381 defs share a range like this.
- Folding by smallest enclosing range sent every reference and every hunk inside those blocks to
  whichever def came first.
- Fix: a def whose range is shared gets the bounds of the tree-sitter `function_item` (or
  `function_signature_item`) that holds its name. No def is left out.
- The SCIP blast changed (marked † in the three SCIP blast tables above). The release changes
  `Backend::install_version`. Before the fix that change was credited to `description`, so
  bootstrap, upgrade and install missed it and `tool` got a false hit. Now: bootstrap 27, upgrade 12,
  install 9, tool 0.
- A first, wrong fix dropped the shared-range defs from the scores. That made the scores silent
  about backend code. It was replaced by the fix above.
- Rerun 2026-11-06 with the fix, before and after outputs diffed (`SCIP_FIX_GRAMMAR=<cbm's Rust grammar>`):
  - gapclass.py (§4.12): bootstrap 26→27, upgrade 11→12 and install 8→9, the same `install_version` gain. 45 → 47 pairs, still 10 edges.
  - codannascore.py ([§4.10](other-engines.md)): codanna precision 0.920→0.981, recall 0.620→0.648; its blast is unchanged.
  - installpath.py ([§4.11](other-engines.md)): the `Task::default` chain into install.rs is unchanged.

**Scoring rule.**
- Both sides are folded onto SCIP function defs.
- Only callers the tool actually read count. For Charon that means `Unstructured` bodies; `Error`
  (async) and `Opaque` bodies are listed as `skipped`. For CGA it means nodes with at least one
  outgoing use, including an async fn's coroutine node.
- A CGA node whose `def_span` is over 30 lines (a long async fn's coroutine, or an `#[async_trait]`
  method) is placed by name: the smallest SCIP def with that method name that overlaps the span.
  That places 3,171 such nodes; 121 find no def.
- The "exact" tier is direct calls: Charon `Fun`/`Trait`, CGA `Called`. CGA's `VTableCalled`,
  `FnPtrCast` and closure-callee edges are "possible" links and are counted apart.

**Charon** (lib and bin targets merged; 6,381 sync functions read):

| | SCIP | Charon | both | precision | recall |
|---|---|---|---|---|---|
| edges | 8,383 | 8,406 | 8,283 | **0.988** | **0.985** |

- SCIP-only, 100 edges:
  - 94 are functions passed as values (83 arguments, 10 field initializers, 1 macro token tree).
    Those are real uses, not calls.
  - 6 are plain calls, all inside `#[cfg(windows)]` blocks, which Charon (built for macOS) never
    compiles. 5 are from `is_mise_shim_in` (src/shims.rs:865-907: `is_dedicated_shims_dir`,
    `is_generated_windows_file_shim_contents`, `files_identical`, `find_mise_shim_bin`,
    `has_mise_native_shim_fingerprint`). One is `get_cmd_program_and_args -> inline_args_style`
    (src/task/task_executor.rs:1845). (An earlier draft named `run_tasks -> finish` and
    `discover_with_context -> discover`; those came from the range bug, and the fixed run doesn't have them.)
    Listed with `DUMP_CALLS=1` on cgscore.py, from a Charon rebuild (0.1.311, nightly-2026-09-17) whose
    streamed output is byte-identical to the first run's.
  - Why SCIP has them, read from rust-analyzer b98172d80f (the version in the index metadata):
    - Body lowering drops a cfg'd-out expression: `maybe_collect_expr` returns `None` when
      `check_cfg` fails (crates/hir-def/src/expr_store/lower.rs:1417-1420). So the block has no
      expression ids and no type inference.
    - The SCIP indexer still classifies every token in the file
      (crates/ide/src/static_index.rs:180-183, then `get_definitions` at :148-153).
    - A path still resolves through the scope resolver with no body
      (`resolve_hir_path_`, crates/hir/src/source_analyzer.rs:1423). A method call needs the
      expression id first (`resolve_method_call`, :650), which is missing.
    - The index matches this: in the `#[cfg(windows)]` block SCIP has `is_dedicated_shims_dir`,
      `files_identical` and `Result::Ok` but no `path.is_file()`. The `#[cfg(not(windows))]` twin
      at :909-917 has `is_file()` and `not()`.
    - So inactive code gives SCIP free-function and path edges, but no method edges.
- Charon-only, 123 edges: implicit calls SCIP has no syntax for (deref, hash, macro expansions).
- Async: 2,018 bodies under src/ are `Error`, and Charon has no coroutine translation. None of
  the 381 `#[async_trait]` methods is read, so the range fix changed no Charon number.
- Blast: SCIP+Charon = SCIP for all 10 commands.

**CGA** (3,849 functions read):

| tier | SCIP | CGA | both | precision | recall |
|---|---|---|---|---|---|
| exact, all sites | 8,059 | 8,087 | 7,480 | **0.928** | 0.925 |
| sync sites only | 5,221 | | 4,920 | 0.942 | |

- CGA does read plain async fns. Before name placement their coroutine nodes were dropped as wide
  spans, which made CGA look blind to async code (precision 0.766). Only 278 of the 579 SCIP-only
  edges are now in async bodies.
- SCIP-only, 579 edges:
  - 451 are calls, and 124 are values.
  - One pattern behind some of the calls: a closure argument. `run_phases -> write_and_reload_with`
    (src/cli/bootstrap.rs:2492) shows up reversed on CGA's side as `write_and_reload_with ->
    run_phases` [Closure], because the closure's def_span sits inside `run_phases`.
- What CGA can't read is `#[async_trait]` code: 2 of the 381 methods.
  - `#[async_trait]` returns `Pin<Box<dyn Future>>`.
  - CGA widens a `dyn` call through `tcx.trait_impls_of` and drops generic impls
    (`cga_analysis/src/callgraph/dyn_object.rs:35-37`).
  - A coroutine's `Future` impl is builtin, not an impl item, so it is never walked.
  - mise has 67 `#[async_trait]`, 161 `Box::pin` and 6 `BoxFuture`.
- CGA-only, 950 edges: `VTableCalled` 301; `Called` 607 (implicit calls, `self.ba()` inside
  `Backend` default methods resolved to the impls); `Closure` 39; `FnPtrCast` 3.

Blast per command (SCIP / CGA exact / SCIP+exact / SCIP+all):

| cmd | SCIP | CGA exact | SCIP+exact | SCIP+all |
|---|---|---|---|---|
| run | 34 | 23 | 34 | 34 |
| tasks | 23 | 6 | 23 | 23 |
| bootstrap | 27 | 24 | 27 | 27 |
| upgrade | 12 | 10 | 12 | 12 |
| lock | 13 | 5 | 13 | 13 |
| exec | 2 | 1 | 2 | 2 |
| use | 8 | 0 | 8 | 8 |
| install | 9 | 8 | 9 | 9 |
| dotfiles | 4 | 2 | 4 | **14** |
| tool | 0 | 0 | 0 | 0 |

- The only addition, `dotfiles` 4 -> 14, runs through the reversed closure edge above
  (src/cli/dotfiles/apply.rs:249). It's a mapping artifact, not a missed call.
- CGA run: 98m43s, 2.5 GB peak, 2.6 GB JSON, 1,277,872 nodes.

**Not checked by Charon or CGA: the backends' `#[async_trait]` methods. rustc's MIR checks them.**
SCIP has 1,703 edges out of 294 of them (`Backend::install_version`, `list_remote_versions`, and
each backend's impl). Charon refuses coroutines and CGA never roots them, so neither read any. The
precision numbers above are for code outside them.

rustc's own MIR covers them (2026-11-06, `prototype/mirscore.py`):
- Run: `cargo +nightly-2026-09-17 rustc --locked --lib -- -Zunpretty=mir -Zmir-include-spans=on
  -Zinline-mir=no` (4m01s into a fresh target dir, 740 MB), then the same with `--bin mise` (1m49s,
  499 MB). The scorer reads both dumps; no `src/` file has SCIP defs in both crates. It holds every body,
  generic trait defaults included, and each `Box::pin(async move {..})` becomes a
  `<method>::{closure#0}` body. A body folds onto the SCIP def holding its return-place span.
- Match: a SCIP edge is exact when a MIR call, or a fn item passed as a value (a `// + const_`
  line), sits in the same caller with a span holding SCIP's site, and its callee path names that def.
  That means the same name; for an impl method, the same type (and trait); for a trait declaration,
  the same trait, as `<X as T>`, `dyn T` or `Self`; for a free fn, the same module or a bare path.
  MIR prints trimmed paths, so the module and type are matched by last segment only.
- Result: **1,684 of 1,703 exact (98.9%)**.
  - 16 have callers rustc never built. Each one is inside a `#[cfg(test)]` module, checked from the
    tree-sitter tree: secrets/broker.rs (8), backend/packslip.rs (6), task/task_cache_store.rs (2).
  - 3 have no MIR call: `if cfg!(windows)` (backend/mod.rs:6277, plugins/core/node.rs:766) and
    `cfg!(target_os = "linux")` (plugins/core/swift.rs:425) branches, folded away on the macOS host.
    They are real calls, not SCIP errors.
  - None point at a different def.
  - The 12 `src/cli/mcp.rs` edges are all exact with the bin dump. That needed two scorer fixes:
    - rmcp's `#[tool(..)]` attribute macro rewrites each tool method into `Box::pin(async {..})`,
      and the async block gets the attribute's span (`src/cli/mcp.rs:244:5: 246:7`). That span is
      outside tree-sitter's `function_item`, so a refined def's range now takes in the attribute
      items just above it.
    - `walk`, a fn nested inside `list_commands` (mcp.rs:251), is `cli/mcp/walk()` in SCIP but
      `..::list_commands::{closure#0}::walk` in MIR. A free fn now also matches a MIR path that is
      nested in a body.
- The other way: 5 MIR call sites in those bodies name a mise fn with no SCIP edge. None is a real
  miss: `tokio::time::timeout` and `PathBuf::from` only share a mise fn's name. The 2
  `should_display_hint` sites are inside the `hint!` macro, whose spans point at its definition
  (src/hint.rs:22).
- Control, every other caller: 15,704 of 25,567 exact (`score13.txt`). 9,836 have callers rustc never built: 9,671
  are under `#[cfg(test)]` or a `#[test]` fn (neither dump uses `--test`), 127 under another `#[cfg(..)]`
  item, and 38 other (not looked at). 3 more test edges call a shared SCIP symbol (below).
  Of the 15,728 with a body, 22 have no MIR call and 2 match only elsewhere in the caller (the 2 not
  looked at one by one). None points at a different def.
- The 23 control edges that first had no MIR call or fn value of that name (`prototype/mir/nomir.json`;
  the 22 left are in `nomir13.json`). None is a SCIP bug; each target is the one-definition fn of that
  name in the same module or imported:
  - 1 scorer bug, fixed: `crate::shell::fish_escape(..)` (src/cli/exec.rs:536) calls a re-export,
    `pub use fish::escape as fish_escape;` (src/shell/mod.rs:18). rustc prints the visible name
    `fish_escape`; SCIP names the def `lib/shell/fish/escape()`. The scorer now reads mise's
    `pub use X as Y;` lines (`fish_escape`, `request_exit`) and maps Y back to X: exact +1, nothing
    else moves (`score11.txt` vs `score13.txt`).
  - 15 inside a `cfg!(windows)` branch, which is the constant `false` on macOS. `-Zunpretty=mir` prints
    `optimized_mir` (rustc-src rustc_middle/src/mir/pretty.rs:350), where that branch is already gone:
    `keep_required_extensions` comes down to `_0 = move _4; return`. rust-analyzer lowers `cfg!(..)` to a bool literal
    (crates/hir-def/src/expr_store/lower.rs:1936, check_cfg_pred at :3346) but keeps the `if` and both
    branches in the body and infers them, so SCIP's edge is right and this check cannot see it. Sites: static_helpers.rs:1670, 1710; mise_bins.rs:20; npm.rs:602, 827,
    843; config/mod.rs:6793; install_layout/resolver.rs:105, 1518; toolset_install.rs:1191;
    install_state.rs:392; shims.rs:525, 735, 1157, 2009.
  - 7 inside a `#[cfg(..)]` block that is off on macOS: task_executor.rs:1845 (`#[cfg(windows)]`),
    task_cache_audit.rs:116 (`#[cfg(target_os = "linux")]`), and shims.rs:872, 891, 895, 896, 906 (the
    `#[cfg(windows)]` block at 866-907). rustc never builds them. rust-analyzer drops cfg-off
    expressions and statements from the body (lower.rs:1418, :2728), so a path there has no expr_id;
    source_analyzer.rs resolve_path (:1158) then falls back to a scope-only name lookup (:1423-1432),
    with the scope of the nearest enclosing expression that is in the body (scope_for, :1756-1773).
    That is how SCIP gets these edges. They name the right fn, but they are edges of a Windows or Linux
    build, not this host's. A blast map for one host cfg would want them flagged or dropped.
- The 46 control edges that first came out "different def" were all scorer bugs; SCIP named the same
  fn every time (`prototype/mir/otherdef.json`, rescored in `score10.txt` and `score11.txt`):
  - 13: the scorer cut a SCIP symbol at its first space, but a descriptor in backticks can hold one
    (`` impl#[`BTreeMap<String, T>`][`GetMatchingExt<T>`]get_matching ``, `` `dyn ConfigFile + 'static` ``,
    `` `From<IndexMap<String, toml::Value>>` ``). 9 of these are `get_matching`.
  - 20: a turbofish of `impl Trait` arguments (`env_value::<impl Fn(&str) → Option<String>>`) was read
    as an impl block. 9 are in src/task/workspace/git.rs.
  - 11: a fn nested in a fn or method (`bytes` is also in the 20). rustc names it after the outer fn
    (`hash_canonical_toml::bytes`, `<X as T>::render_templates::render_value`), SCIP after the module
    (`lib/lockfile/bytes()`). The scorer now accepts the outer fn name when the SCIP def lies inside a
    def of that name.
  - 3 naming differences: `mise::register_util_hooks` from the bin for SCIP's `lib/register_util_hooks()`;
    a `&T` self type; and SCIP printing `eyre::Report` as its re-export `eyre::Error`
    (eyre-0.6.14/src/lib.rs:388; the impl is `for eyre::Report`, src/backend/static_helpers.rs:292).
  - Checked: the fixed rule accepts 13 hand cases and rejects 8 (wrong type, wrong module, wrong outer
    fn, another error type). Edge by edge against the old rule, the only moves are these 46 into exact
    and the 3 shared-symbol edges below; no async_trait edge moves, and the reverse pass is unchanged.
  - One real SCIP flaw turned up nearby, outside the 46: because nested fns are named after their module,
    three test fns' own `parse_script_from_str` (src/task/task_script_parser.rs:2400, 2465, 2543) share one
    symbol, `lib/task/task_script_parser/tests/parse_script_from_str()`. It is the only fn symbol in mise with
    more than one definition site. Its 3 edges come from test code, which neither dump builds, so no
    edge here was scored on it. `mirscore.py` now puts any edge whose caller or callee symbol has more
    than one definition in its own tier ("SCIP symbol has several definitions") and never counts it exact
    (`score11.txt`: exact counts unchanged).
- Limits: same-name targets are told apart only by type, trait or module last segment, and a call
  through `<X as T>` matches either T's declaration or X's impl. One host cfg (macOS, default
  features); lib and `mise` bin targets, no `--test` build.
- Two parser bugs were found and fixed before these numbers. A destination that is a coroutine field
  (`(((*_56) as variant#4).3: T) = f(..)`) was read as part of the callee, and a `->` inside generic
  arguments closed an angle bracket. The first pass reported 242 "other def" edges, which were these
  bugs.

**Verdict.**
- Where a compiler-grade tool can check them, SCIP's call edges are 93-99% exact. Its extra edges
  are mostly value uses, which blast wants anyway.
- SCIP+Charon and SCIP+CGA add nothing real to any command's blast.
- The fold bug was in our reading of SCIP, not in its edges. Fixing it changed four commands.
- The `#[async_trait]` bodies are checked too: rustc's MIR confirms 98.9% of SCIP's 1,703 edges by
  exact site and target. The other 19 are test or other-OS code, and SCIP misses none.
- Not worth a store slot: Charon needs a pinned nightly and 7 GB of JSON per version; CGA takes
  100 minutes.

**Caveats.**
- cfg-gated code: Charon and CGA saw one cfg, the macOS host's default features. SCIP (rust-analyzer)
  still indexes inactive code, but only for names that resolve by path, never method calls (see the 6
  calls above). So its Windows/Linux-only edges are partial.
- CGA's macOS build fails with `ld: unknown options: -rpath=…`. Apple ld wants `-rpath,<dir>`, so
  build.rs's `-Wl,-rpath={sysroot}/lib` breaks. A one-character fix (`=` -> `,`) works. This is a
  draft-only upstream issue candidate.
