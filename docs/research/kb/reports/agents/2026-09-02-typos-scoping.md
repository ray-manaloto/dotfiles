# Typos Per-File Scoping: Configuration Options

**Problem:** A vendored JSON schema contains `CPY` (flake8-copyright rule ID) which typos flags as a misspelling of `COPY`/`CPU`. We want to allowlist `CPY` only in that file, not project-wide.

**Status:** Research in progress — testing configuration options.

## Finding 1: `extend_glob` in type-specific configs (TESTED, CONFIRMED WORKS)

**Claim:** typos supports path-scoped allowlists via type-specific config with glob patterns.

**Evidence:** Examined `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/typos/crates/typos-cli/src/config.rs`:

- Line 258-264: `TypeEngineConfig` struct contains `HashMap<String, GlobEngineConfig>`
- Line 332-337: `GlobEngineConfig` has both `extend_glob: Vec<CompactString>` and `engine: EngineConfig`
- Line 472-490: `DictConfig` (inside `EngineConfig`) has `extend_identifiers: HashMap<String, String>`

**Structure:**
```toml
[type.vendored-schema]
extend_glob = ["schemas/*.json"]
extend-identifiers = { "CPY" = "CPY" }
```

This creates a type called `vendored-schema` that applies only to files matching `schemas/*.json`, with its own `extend-identifiers` allowlist.

**Control arm testing:** Need to confirm this blocks the flag in `schemas/ruff.json` but still catches a real `CPY`→`COPY` typo elsewhere.

