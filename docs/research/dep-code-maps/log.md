# Directory Update Log

## 2026-11-06
* **Addition**: [§4.12-§4.13](rust-call-graphs.md). cbm's `run`, `tasks` and `bootstrap` gaps are
  traced to the 256-name cap, the dropped self-edge and grouped `use` imports. Charon, CGA and rustc's
  MIR check SCIP's call edges: 93-99% exact, and SCIP+either adds nothing real to any blast.
* **Correction**: rust-analyzer gives every `#[async_trait]` method the whole block as its range. The
  prototypes now take the tree-sitter function bounds, which changes the SCIP blast for bootstrap,
  upgrade, install and tool (marked † in the tables) and codanna's scores (§4.10).
* **Decisions**: Q20-Q30 (inactive-code edges flagged per host build, cleanup, three tickets, the
  glossary terms, the next steps), in [design](design.md).
* **Filed**: dotfiles #510, #511, #512; upstream DeusData/codebase-memory-mcp #2922-#2926.

## 2026-11-05
* **Creation**: bundle cut from the working notes after five grilling rounds and the owner's
  confirmation of design items 1-7. Covers cbm 0.12.1, rust-analyzer SCIP, REAgraph and graphify
  0.9.102/0.9.103, scip-clang 0.4.1, codanna 0.17.1 and CLion 2026.3 read offline.
* **Addition**: scip-clang pilot on cbm's own C sources and codanna pilot scored against SCIP.
* **Rejected**: cbm `compare_graphs` for version diffs, graphify/REAgraph and codanna as blast
  engines, JetBrains indexes and Qodana SARIF as maps, mise dotfiles' private repo as map storage.
* **Addition**: §4.10 explains codanna's 0 `install` blast from its v0.17.1 source and a probe
  crate: annotation-only `let` types, macro bodies, `&Arc<T>` parameters and `..Default::default()`
  leave the receiver untyped or mistyped, and the resolver drops those calls.
* **Addition**: §4.11 explains cbm's miss at src/cli/install.rs:720 from its v0.12.1 source, the
  mise graph and a probe crate. Edges start only from syntactic call sites, and inside a macro
  cbm injects synthetic sites only for built-in expression macros, so no call inside a `macro_rules!` macro
  gets an edge. §4.10's "the macro miss is codanna's own" is corrected.
* **Correction**: results and pilots no longer say cbm drops method calls on local variables. The
  traced miss is the macro one (§4.11); the `run`, `tasks` and `bootstrap` gaps are open. The probe
  crates and helper scripts are saved under `prototype/`.
* **Deferred**: `depmaps lint-diff` (SARIF findings diff), the upstream cbm issue, blast-depth
  calibration.
