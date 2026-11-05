# Directory Update Log

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
* **Deferred**: `depmaps lint-diff` (SARIF findings diff), the upstream cbm issue, blast-depth
  calibration.
