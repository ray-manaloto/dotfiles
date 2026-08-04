# fnox-core: binding surface for a NON-Rust consumer

**Agent:** jdx-fnox-core-bindings
**Date:** 2026-08-04
**Status:** COMPLETE
**Corpus:** shallow clone of `jdx/fnox` @ `292c788` (2026-08-02, "ci: build perf binaries on bamboo (#674)"), workspace version **1.32.0**

## Question list

1. Any binding protocol out of `fnox-core` a non-Rust caller could use?
2. `fnox mcp` — usable programmatic surface?
3. `fnox-core` public API surface, precisely.
4. Stability / semver / lockstep with the binary.

---

## Q1 — Binding protocol out of `fnox-core`: **NONE**

### Crate type

`crates/fnox-core/Cargo.toml` has **no `[lib]` section at all** (verified: file is 94 lines,
`[package]` / `[dependencies]` / target-cfg deps / `[build-dependencies]` / `[dev-dependencies]` only).
No `[lib]` ⇒ default `crate-type = ["rlib"]` ⇒ **Rust-only, statically linked at Rust compile time.**
There is no `.so`/`.dylib`/`.a` artifact for a non-Rust caller to link or `dlopen`.

### Grep sweep (repo root, `--include='*.rs' --include='*.toml'`, `Cargo.lock` excluded)

| Term | Hits |
|---|---|
| `crate-type` | **0** |
| `cdylib` | **0** |
| `staticlib` | **0** |
| `no_mangle` | **0** |
| `wasm-bindgen` / `wasm_bindgen` | **0** / **0** |
| `napi` | **0** |
| `uniffi` | **0** |
| `neon` | **0** |
| `cbindgen` | **0** |
| `interoptopus` | **0** |
| `pyo3` | **0** |
| `extern "C"` | 26 — **inbound only, see below** |
| `ffi` | 62 |

**Control arm** (same command shape, terms known present): `clap` → 56, `async_trait` → 68,
`libloading` → 5, `rmcp` → 13. The probe discriminates; the zeros are real.

### The 26 `extern "C"` are fnox CONSUMING C, not exposing it

Every one is in `crates/fnox-core/src/providers/yubikey_usb.rs:91-208` — function-pointer *types*
for `libusb` symbols resolved at runtime through `libloading::Library::new` (`yubikey_usb.rs:131`,
`:147-208`, e.g. `.get::<unsafe extern "C" fn(...)>(b"libusb_init\0")`). The file's own doc comment
(`yubikey_usb.rs:4`) says it "loads libusb at runtime via `libloading`". Direction is **inbound**:
fnox is the C *caller*, never the C *callee*. `libloading` appears at exactly 5 sites, all this file
plus the two Cargo.toml declarations — there is no plugin-loading system.

**Conclusion Q1a: there is no FFI, no dynamic library, no WASM, no language binding of any kind
out of `fnox-core`. A non-Rust program cannot link it. Full stop.**

---

## Q3 (partial) — the `Fnox` convenience API is READ-ONLY

`crates/fnox-core/src/library.rs`. Public surface of the `Fnox` struct:

| Item | Signature | Notes |
|---|---|---|
| `CONFIG_FILENAME` | `pub const &str = "fnox.toml"` | `library.rs:40` |
| `Fnox::discover()` | `-> Result<Self>` | `library.rs:75` — upward walk + parent/local/global merge (`Config::load_smart`) |
| `Fnox::open(path)` | `-> Result<Self>` | `library.rs:100` — **strictly one file**, no merge, no discovery |
| `.with_profile(s)` / `.with_profiles(iter)` | builder | `library.rs:127`, `:132` |
| `.with_no_defaults(bool)` | builder | `library.rs:140` |
| `.profile()` | `-> &str` | `library.rs:146` |
| `.config()` | `-> &Config` | `library.rs:153` — escape hatch to the lower-level surface |
| `.get(key)` | `async -> Result<Option<String>>` | `library.rs:167` — resolves a VALUE |
| `.list()` | `-> Result<Vec<String>>` | `library.rs:202` — **declared** names, sync, no I/O |

**No `set`.** The module doc says so explicitly (`library.rs:10-16`): the API was designed in
response to [jdx/fnox discussions/441], "First cut covers `get` and `list`. `set` is left to a
follow-up because the orchestration in `commands::set::SetCommand::run` … is substantial enough to
warrant its own design pass." So the library API is read-only *by design*. Writes live in the
**binary's** `commands` module, which is not published as a library. (Note: the `Provider` **trait**
is *not* read-only — it has `encrypt` and `put_secret`. See the Q3 correction below.)

`Fnox` is `Clone` + `Debug`, `Config` behind `Arc` (`library.rs:46-52`), test at `:417` asserts clone
shares the Arc.

### `fnox-core/src/lib.rs` module visibility (`lib.rs:11-32`)

`pub`: `auth_prompt, config, config_path, env, error, http, lease, lease_backends, library,
providers, secret_resolver, settings, source_registry, spanned, suggest, temp_file_secrets`.
`pub(crate)` (NOT downstream-reachable): **`credential_command`**, **`keyring_store`**.
Re-exports: `pub use error::{FnoxError, Result}; pub use library::Fnox;`.

---

## Q1b — The daemon: a real wire protocol, but PRIVATE and versioned-against-you

`src/daemon.rs` (1,650 lines) — note it lives in the **binary** crate `src/`, **not** in
`crates/fnox-core/`. So it is not part of the published library at all.

**Transport:** newline-delimited **JSON over a Unix domain socket**. `tokio::net::UnixListener`
(`daemon.rs:16`), `serde_json::to_string` + `read_line` (`daemon.rs:673`, `:691`, `:720`, `:734`).
Docs confirm: "Unix-first and uses a Unix domain socket. It does not listen on TCP"
(`docs/guide/daemon.md` § Security Model).

**Message types — all PRIVATE (no `pub`):**

```rust
// daemon.rs:93-137
#[derive(Serialize, Deserialize)] #[serde(tag = "type", rename_all = "snake_case")]
enum Request { ResolveBatch(..), ResolveOne(..), Status, Clear, Shutdown }

// daemon.rs:138-151
#[derive(Serialize, Deserialize)] #[serde(tag = "status", rename_all = "snake_case")]
enum Response {
    Resolved { values: IndexMap<String, Option<String>> },   // ← raw VALUES
    Status { pid: u32, cached_entries: usize },
    Ok,
    Error { message: String },
}
```

**The wire format is explicitly declared unstable, and the design actively LOCKS OUT
third-party clients.** `daemon.rs:1044-1048`:

```rust
/// Wire-protocol version tag included in the socket path hash.
/// Incrementing this ensures new clients don't connect to stale daemons
/// running an incompatible wire format.
const WIRE_VERSION: u8 = 2;
```

The socket *path* is `runtime_dir()/<blake3(WIRE_VERSION ‖ profiles ‖ no_defaults ‖ if_missing ‖
age_key_file)[..16]>-fnoxd.sock` (`daemon.rs:1048-1068`), with `runtime_dir()` = `$XDG_RUNTIME_DIR/fnox`
or `$TMPDIR/fnox-<uid>/fnox`, with a `/tmp/fnox-<uid>/<hash8>/fnox` fallback when the path would
exceed the ~100-byte `sun_path` limit (`daemon.rs:1069-1089`). A third-party client would have to
reimplement that whole hash to even *find* the socket, and the version byte guarantees a silent
disconnect on any bump. There is **no negotiation and no compatibility window** — the only nod to
compat is a single `#[serde(rename = "include_env_false")]` kept for a renamed field
(`daemon.rs:118-120`).

**Zero documentation of the protocol.** `docs/guide/daemon.md` (saved verbatim to
`.agent/kb/raw/fnox-docs-guide-daemon.md`) documents `[daemon] enabled/idle_timeout`, the
`fnox daemon start|status|clear|stop` verbs, cache behavior, `daemon_cache = false`, and the
security model. It documents **no message shape, no socket path, no field names.** Nothing in
`docs/` describes the JSON schema.

Also: the daemon is **opt-in** (`docs/guide/daemon.md`: "fnox does not use it unless you enable it
in config or set `FNOX_DAEMON=on`") and Unix-only, and it verifies the peer's uid both directions.

**Verdict:** speaking the daemon protocol from Python is *technically possible* and *categorically
unwise* — it is a private, unversioned-except-to-break-you, undocumented internal IPC that requires
the user to have opted the daemon in. It is not a binding surface.

---

## Q2 — `fnox mcp`: a REAL, documented programmatic surface (the only one)

Sources: `docs/guide/mcp.md` (verbatim → `.agent/kb/raw/fnox-docs-guide-mcp.md`),
`src/commands/mcp.rs` (84 lines), `src/mcp_server.rs` (689 lines).

**Transport: stdio only.** `src/commands/mcp.rs:73` — `server.serve(rmcp::transport::io::stdio())`.
Built on `rmcp` v2 (the official Rust MCP SDK) with features `["server", "transport-io", "macros"]`
(`Cargo.toml:77`). Control arm on capabilities: `enable_tools` → 1 hit, `enable_resources` → **0**,
`enable_prompts` → **0**, `enable_logging` → **0** (`src/mcp_server.rs:568`
`ServerCapabilities::builder().enable_tools().build()`). **No resources, no prompts — tools only.**
No HTTP/SSE transport anywhere.

**Exactly two tools** (`#[tool]` attribute count in `src/mcp_server.rs` = 2, at `:209` and `:292`):

| Tool | Line | Returns |
|---|---|---|
| `get_secret` | `mcp_server.rs:209` | **the raw secret VALUE** as a text ContentBlock |
| `exec` | `mcp_server.rs:292` | subprocess stdout/stderr (captured, ≤1 MiB) |

`get_secret` returns `CallToolResult::success(vec![ContentBlock::text(value.clone())])`
(`mcp_server.rs:246-248`, `:268`) — the plaintext value, unredacted.

**What `redact_output` actually gates — narrower than it sounds.** It is read at **exactly one
site**: `src/mcp_server.rs:463`, `if self.mcp_config.redact_output() { … }`, inside the **`exec`**
tool's output handling. Default `true` (`crates/fnox-core/src/config.rs:489-490`). It literal-string-
replaces resolved secret values in the subprocess's stdout/stderr with `[REDACTED]`. It does
**not** touch `get_secret`, and the docs say so: "Redaction performs literal string matching and does
not detect base64-encoded or otherwise transformed values" (`docs/guide/mcp.md:100`). The intended
lockdown posture is `tools = ["exec"]` + redaction on, which removes the value-returning path
entirely.

**Other config knobs** (`[mcp]` in `fnox.toml`): `tools = ["get_secret", "exec"]` (default both;
disabled tools are **not advertised in `tools/list`** — `mcp_server.rs:574` `list_tools` +
`:593` `get_tool`), `secrets = [...]` allowlist (`commands/mcp.rs:66` `mcp_config.filter_secrets`),
`exec_timeout_secs` (must be ≥ 1, `commands/mcp.rs:59-64`), `redact_output`.

**Read-only?** With respect to fnox's own state, **yes** — there is no `set_secret`, `remove`,
`sync`, or `provider` tool. Control arm: the `#[tool]` grep returns exactly the two above; a
write tool would have to carry that attribute. But `exec` runs **arbitrary commands with secrets
injected**, so the *process* is not sandboxed — it just cannot mutate fnox config through MCP.
(You could of course have `exec` shell out to `fnox set`. That is the agent choosing to, not a
surface fnox exposes.)

**Behavioral notes that matter to a downstream driver:**
- Non-interactive is forced (`commands/mcp.rs:18` `env::set_non_interactive(true)`) — provider
  prompts would corrupt the JSON-RPC stream. So any provider needing a TTY prompt **fails** here.
- First tool call batch-resolves every `env = true` / `env = "exec"` secret
  (`mcp_server.rs:94` `ensure_resolved`), amortizing yubikey/SSO. `env = false` resolves on demand.
- `as_file = true` secrets are **rejected** by `get_secret` (`mcp_server.rs:222-231`) — exec only.
- Cache is process-memory, cleared on EOF/disconnect.
- It can sit on top of the daemon (`Purpose::Mcp` at `daemon.rs:73`).

**Viability as a Python-facing surface:** yes, mechanically. It is a standard stdio MCP server, so
`mcp` (the Python SDK) `stdio_client` drives it in a few lines, and it is the one surface with a
public spec and user-facing documentation. But note what it costs versus shelling out to the CLI:
you still spawn the `fnox` binary as a subprocess (`command: "fnox", args: ["mcp"]`), you now carry
an MCP client dependency and a JSON-RPC handshake, and you get **strictly fewer verbs** —
`get_secret` and `exec` only, i.e. no `set`, `list`, `sync`, `check`, `provider`, `edit`, `import`.
Shelling out to `fnox` gives you the whole CLI for the same process spawn.

---

## Q3 (rest) — the `Provider` trait, and whether a downstream can implement one

`crates/fnox-core/src/providers/mod.rs` (487 lines).

**The trait IS `pub` and IS implementable by a downstream crate** (`providers/mod.rs:169-170`):

```rust
#[async_trait]
pub trait Provider: Send + Sync {
    async fn get_secret(&self, value: &str) -> Result<String>;                       // :172 required
    async fn get_secrets_batch(&self, ..) -> HashMap<String, Result<String>>;        // :185 defaulted
    async fn encrypt(&self, _value: &str) -> Result<String>;                          // :195 defaulted → Err
    async fn put_secret(&self, _key: &str, value: &str) -> Result<String>;            // :208 defaulted
    fn capabilities(&self) -> Vec<ProviderCapability>;                                // :227 defaulted
    async fn test_connection(&self) -> Result<()>;                                    // :233 defaulted
}
```

Not sealed, not `#[non_exhaustive]` (control: `non_exhaustive` → **0** hits across `crates/` + `src/`).
Only `get_secret` is required.

⚠️ **CORRECTION to a premise in the brief.** The brief said "fnox is CRU, not CRUD — the `Provider`
trait has no delete method." The *delete* half is right; the implication that the trait is read-only
is not. `Provider` has **`encrypt`** (`:195`) and **`put_secret`** (`:208`) — real write methods
("Store a secret and return the value to save in config"). What is missing is a **delete/remove**
method: the CLI's `fnox remove` (alias `delete`) removes the *declaration from the TOML*, never the
value from the backing store. So: trait = C/R/U, no D. Separately, the **`Fnox` convenience API**
(Q3 above) really is read-only — no `set` at all.

**But a downstream `Provider` impl cannot be REGISTERED.** There is no plugin/registry hook:

| Hook | Hits (`crates/` + `src/`, `*.rs`) |
|---|---|
| `register_provider` | **0** |
| `add_provider` | **0** |
| `inventory` (typed distributed slice) | **0** |
| `linkme` | **0** |
| `non_exhaustive` | **0** |
| *control* `Box<dyn Provider>` | 4 |

Providers are **code-generated at build time** from **24 in-tree TOML files** in
`crates/fnox-core/providers/*.toml` (`1password.toml`, `age.toml`, `aws-kms.toml`, … `yubikey.toml`)
by `crates/fnox-core/build.rs` → `build/generate_providers.rs`, emitted into `$OUT_DIR` and
`include!`-ed at `providers/mod.rs:134-162`. The generated `ProviderConfig` / `ResolvedProviderConfig`
enums and `get_provider_from_resolved` (`providers/mod.rs:165-167`) are closed sets. A downstream
`impl Provider` compiles and can be called by hand, but nothing in config parsing or secret
resolution will ever route to it — adding a provider means a PR to fnox.

*(This is Rust-internal detail; it changes nothing for a non-Rust caller, who cannot reach the trait
at all.)*

---

## Q4 — Stability: lockstepped to the binary, no promise, undocumented, 3 months old

**Lockstep: CONFIRMED.** `crates/fnox-core/Cargo.toml:3` is `version.workspace = true`, and the root
`Cargo.toml:6` sets `version = "1.32.0"` for the whole workspace; the binary depends on it as
`fnox-core = { path = "crates/fnox-core", version = "1.32.0" }` (`Cargo.toml:124`) — an **exact
pinned version**, re-written every release. crates.io bears it out:

| | fnox (binary) | fnox-core |
|---|---|---|
| First published | 0.1.0, 2025-10-20 | **1.23.1, 2026-05-02** |
| Versions published | 21 | 12 |
| Latest | 1.32.0 (2026-08-01) | 1.32.0 (2026-08-01) |
| Downloads (all-time) | — | **968** |

Every fnox-core release is a same-numbered fnox release. (Two gaps: `1.25.0` was never published to
either; `1.28.0` shipped as fnox-core but **not** as the fnox binary crate — publish hiccups, nothing
semantic.) **fnox-core bumps its minor on every single fnox release** — 12 releases in 3 months,
roughly one per week. That is exactly the "different proposition" the brief warned about: the version
number carries no information about API change, because it is the binary's release cadence.

**No stability promise exists.** Grep over `README.md`, `docs/**.md`, `AGENTS.md`, `CONTRIBUTING.md`:
`semver` → **0**, `semantic version` → **0**, `stability` → **0**, `stable API` → **0**,
`breaking change` → **0**, `BREAKING` → **0**. Control arm, same files, same command shape:
`provider` → **339**, `secret` → **511**, `daemon` → **55**. The probe sees; there is genuinely
nothing to find. The 1,272-line `CHANGELOG.md` (git-cliff generated from conventional commits, per
`cliff.toml`) contains **zero** "breaking" entries — breaking changes are not labelled at all.

**The library is invisible in the project's own documentation.** `fnox-core` / `fnox_core` appears
**0 times** across `README.md`, the whole `docs/` site, `AGENTS.md` and `CONTRIBUTING.md` (same
control arm as above). The only mention anywhere is one CHANGELOG line under **1.23.1**
(`CHANGELOG.md:373`): "extract providers and core types into fnox-core crate … [#458]". There is no
"using fnox as a library" guide, no example, no stability statement.

**It is new, and it has had one contributor-driven PR in its life.** The `Fnox` API landed in
**v1.23.0, 2026-04-26** as `feat(library): top-level Fnox::discover() / get / list convenience API`
by **@bglusman** (their first contribution) — `CHANGELOG.md:406`, PR
[#442](https://github.com/jdx/fnox/pull/442), from discussion
[#441](https://github.com/jdx/fnox/discussions/441). The crate split (#458) followed a week later.
A `gh pr list -R jdx/fnox --state all --search "library API"` sweep (control arm: the same query
shape with `"fnox-core"` returns 5 unrelated but real PRs, so the search works) finds **no
subsequent PR adding `set`** or otherwise extending the library API. The `set` follow-up promised in
`library.rs:13-16` has not landed as of 1.32.0.

**docs.rs IS built and browsable:** `https://docs.rs/fnox-core/latest/fnox_core/` → **HTTP 200**,
`<title>fnox_core - Rust</title>`, zero build-failure markers. Control arm: a bogus crate path →
**404**, so the 200 is real.

---

## Bonus: the machine-readable surfaces that DO exist (both probed live on 1.32.0)

These are not "bindings", but they are the closest thing to a contract a Python CLI could lean on,
and neither was in the brief's question list:

1. **`fnox usage`** — emits the complete `usage` (jdx's CLI spec DSL) KDL description of the entire
   CLI: 275 lines, version-stamped `version "1.32.0"`, every command/flag/arg with help text.
   Probed: `/Users/rmanaloto/.local/share/mise/installs/fnox/latest/fnox usage` → rc=0, 275 lines,
   byte-comparable to the checked-in `fnox.usage.kdl`. It is **regenerated every release**
   (`mise.toml:92` `fnox usage > fnox.usage.kdl`; `mise-tasks/release-plz:58` lists it as a release
   artifact) and also published as **JSON**: `mise.toml:95` `usage g json -f fnox.usage.kdl >
   docs/cli/commands.json` → a 60 KB JSON tree shipped in the repo and on the docs site. A Python
   wrapper can generate/validate its own argument surface from this and detect CLI drift
   mechanically.
2. **`fnox schema`** — a hidden subcommand (`src/commands/schema.rs`; NOT in `fnox --help`) printing
   a **JSON Schema draft 2020-12** for `fnox.toml` (schemars-derived). Probed: rc=0, emits
   `{"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Config", …}`. Also shipped
   as `docs/public/schema.json` (42 KB).
3. **`fnox export --format json|yaml|toml|env|shell`** — structured output of resolved secrets.
   ⚠️ This emits **VALUES**; `--all` widens it to `env = false` / `env = "exec"` secrets. Useful as
   a batch-read path, dangerous as a debugging habit.
4. `fnox list` has **no** `--json`; `-V/--values` prints values (do not run it here).

---

## Bottom line

| Surface | Exists? | Usable from Python? | Documented / stable? |
|---|---|---|---|
| `fnox-core` as a linkable library | rlib only, **no** cdylib/staticlib | **No** — Rust-to-Rust only | docs.rs yes; project docs **0 mentions** |
| C FFI / WASM / PyO3 / napi / uniffi | **No** (all 0 hits, control-armed) | No | — |
| Daemon Unix-socket JSON protocol | Yes | Technically; **don't** | Private types, `WIRE_VERSION` lockout, **0** protocol docs, opt-in only |
| `fnox mcp` (stdio MCP, `rmcp` v2) | **Yes** | **Yes** | Documented (`docs/guide/mcp.md`); 2 tools only |
| CLI + `usage` KDL/JSON spec + `schema` JSON Schema | **Yes** | **Yes** | Documented, regenerated every release |

**For a new secrets CLI written in a non-Rust language, there is exactly one sane integration path:
shell out to the `fnox` binary**, and use `fnox usage` / `docs/cli/commands.json` and `fnox schema`
as the machine-readable contracts to code against. The MCP server is a real, documented, standards-
based alternative but is strictly narrower (`get_secret` + `exec`, no `set`/`list`/`sync`/`check`)
and costs the same process spawn plus a JSON-RPC client dependency. `fnox-core` is irrelevant to
anything that is not Rust — and even for a Rust consumer it is a 3-month-old, weekly-minor-bumping,
un-promised, project-docs-invisible API with 968 lifetime downloads.

**If the new CLI were written in Rust**, `fnox-core` becomes real but still buys less than it looks:
`Fnox::discover/open/with_profile(s)/with_no_defaults/get/list` is read-only, and every write verb
(`set`, `remove`, `sync`, `reencrypt`, `import`, `provider add`) lives in the binary's unpublished
`commands` module. You would be linking a library to do the half you could already do, and shelling
out for the other half.

## GitHub repos touched

- [jdx/fnox](https://github.com/jdx/fnox) — primary subject; shallow-cloned at `292c788` and grepped; docs, CHANGELOG, Cargo manifests, daemon/MCP/provider source, PR + discussion refs
- [jdx/usage](https://github.com/jdx/usage) — the CLI spec/generator behind `fnox.usage.kdl`, `usage g markdown`, `usage g json` (referenced via `mise.toml:92-95`, `usage-lib = "4"` at `Cargo.toml:103`); not itself read
- [modelcontextprotocol/rust-sdk](https://github.com/modelcontextprotocol/rust-sdk) — the `rmcp` v2 crate fnox's MCP server is built on (`Cargo.toml:77`, `src/commands/mcp.rs:8,73`); identified as the dependency, source not read


## GitHub repos touched

- [jdx/fnox](https://github.com/jdx/fnox) — primary subject; shallow clone grepped at `292c788`
