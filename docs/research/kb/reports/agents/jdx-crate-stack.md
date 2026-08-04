# jdx shared Rust crate stack — mise / hk / fnox

**Status:** COMPLETE
**Question:** how cheap is it to build a new CLI on the same foundation jdx uses?
**Method:** `git clone --depth 1` of `jdx/{mise,hk,fnox,usage,xx}` into the session
scratchpad; manifests + `Cargo.lock` + `.github/workflows/` + `mise.toml` read from disk;
crates.io API for publish status; `gh repo list jdx` for the starter-template search.
Raw manifests are copied verbatim to `.agent/kb/raw/jdx-<repo>-cargo-toml.md`.

## Headline

There **is no jdx CLI starter template**, but there is a very consistent *house style*, and
about **70% of a new CLI's scaffolding is copy-paste from any one of these three repos**.
The jdx-owned crates you actually get for free are `xx`, `usage-lib`, `demand`, `clx`,
`clap_usage` and `clap-sort` — all published on crates.io, all current, but only `xx` and
`usage-lib` are documented for downstream use. Distribution is **not** cargo-dist; it is a
hand-rolled but near-identical `release.yml` + `release-plz` + a `mise-tasks/release-plz`
shell script that is ~95% byte-identical between hk and fnox.

## Clone provenance

| repo | HEAD | commit date |
|---|---|---|
| jdx/mise | `72379d0c459808f980a037065ac9c39a60032280` | 2026-08-04T06:40:11Z |
| jdx/hk | `fc81820fb21f72497b28d4fd1315a64244076aad` | 2026-08-01T20:55:05-05:00 |
| jdx/fnox | `292c7880d095d63de7c994a18752851064cdb78d` | 2026-08-02T02:42:28Z |
| jdx/usage | `6cbc9317b9e7f7b96394e2a974a3b14d1bea4f8c` | 2026-08-01T22:10:39-05:00 |
| jdx/xx | `0d481453629ffb39fa1fc0128fb385df6a699e55` | 2026-08-04T06:36:42Z |

Declared versions: mise **2026.8.1** (`jdx-mise/Cargo.toml:13`), hk **1.54.0**
(`jdx-hk/Cargo.toml:23`), fnox **1.32.0** (`jdx-fnox/Cargo.toml:6`), xx **2.6.1**
(`jdx-xx/Cargo.toml:3`). Each matches its crates.io `max_version` exactly (below), so the
clones are at released state, not ahead of it.

> ⚠️ **Probe corrections made during this run — three, all caught by a control arm.**
> 1. A first pass read lock versions with `awk … {print; exit}`, returning the **first**
>    entry per name. Lockfiles carry multiple majors, so it reported `indexmap 1.9.3` while
>    every manifest declares `indexmap = "2"`. The manifest/lock disagreement caught it.
> 2. `gh repo list jdx --limit 200` returned **exactly 200** — my own bound, not a total.
>    `gh api users/jdx --jq .public_repos` says **623**. The "no template" claim below is
>    re-derived from the full 623.
> 3. The first crates.io sweep printed **empty for all 9 crates** — a broken python
>    one-liner, not an absent registry. No control arm had passed, so the zero was not an
>    answer. Re-run below with a working parser.

## 1. Crate table — the load-bearing categories

Versions are resolved from each repo's own `Cargo.lock` (**all** versions present per name).
"transitive" = in the lock but not declared in that repo's manifest.

| Category | Crate | mise | hk | fnox | What it does | jdx's? |
|---|---|---|---|---|---|---|
| **CLI parsing** | `clap` | 4.6.5 | 4.6.4 | 4.6.4 | arg parser — **derive in all three** | no |
| | └ features | `env`,`derive`,`string` | `derive` | `derive`,`env` | note: **no `cargo` feature anywhere** | |
| | `usage-lib` | 4.1.0 (`clap`,`docs`) | 4.0.0 (via `clap_usage`) | 4.0.0 (`clap`) | CLI spec → completions + docs | **yes** |
| | `clap_usage` | 4.0.0 | 4.0.0 | — | clap→usage-spec bridge | **yes** |
| | `clap-sort` (dev) | 1 | 1 | 1 | test-only: subcommands must be sorted | **yes** |
| **Errors** | `miette` | 7.6.0 (`fancy`) | 7.6.0 (transitive) | 7.6.0 (`fancy`) | diagnostic-rich errors | no |
| | `eyre` | 0.6.12 | 0.6.12 | — | error context | no |
| | `color-eyre` | 0.6.5 | — | — | pretty eyre reports | no |
| | `thiserror` | 1.0.69, 2.0.19 | 2.0.19 | 1.0.69, 2.0.19 | derived error enums | no |
| | `anyhow` | 1.0.104 | — | 1.0.104 | boxed errors | no |
| **Async** | `tokio` | 1.53.1 (`full`) | 1.53.1 (`process`,`rt-multi-thread`,`signal`,`sync`) | 1.53.1 (`full`) | **all three are async** | no |
| | `async-trait` | 0.1 | — | 0.1 | | no |
| **Config** | `serde` (derive) | 1.0.229 | 1.0.229 | 1.0.229 | | no |
| | `toml` | 0.5.11, 0.8.23, 1.1.4 | 1.1.3 | 0.5.11 (transitive) | TOML parse | no |
| | `toml_edit` | 0.22.27, 0.25.13 | — | 0.25.13 (`serde`) | format-preserving TOML | no |
| | `serde_json` / `serde_yaml` | ✓ / ✓ | ✓ / ✓ | ✓ / ✓ | | no |
| | `indexmap` (`serde`) | 2.14.0 | 2.14.0 | 2.14.0 | order-preserving maps | no |
| | `pklr` | — | 1 | — | **hk only** — Apple Pkl eval | **yes** |
| | `schemars` | — | — | 1 | JSON-schema generation | no |
| | **no `figment`, no `kdl`, no `config`** in any of the three | | | | | |
| **HTTP** | `reqwest` | 0.13.4 | 0.13.4 (transitive) | 0.13.4 (+0.12.28) | **not `ureq`** | no |
| **Logging** | `tracing` | 0.1.44 | 0.1.44 | 0.1.44 | | no |
| | `tracing-subscriber` | 0.3.23 | 0.3.23 (`env-filter`,`json`,`fmt`) | 0.3.23 (`env-filter`) | | no |
| | `log` | 0.4 | 0.4 | (transitive) | legacy facade, still declared in mise+hk | no |
| **TUI / progress** | `console` | 0.16.4 | 0.16.4 | 0.16.4 | terminal styling | no |
| | `clx` | 3.0.2 | 3.0.2 | — | jdx's progress/output layer | **yes** |
| | `indicatif` | 0.18.6 (transitive) | 0.18.6 (via `ensembler`) | — | progress bars — **never a direct dep** | no |
| | `demand` | 2.0.5 | 2.0.5 | 2.0.5 | **prompts/selects, all three** | **yes** |
| | `tabled` (`ansi`) | 0.21.0 | — | 0.21.0 | tables | no |
| | `ratatui` | — | — | 0.30.2 | full TUI — **fnox only** | no |
| | `crossterm` | 0.29.0 (transitive) | — | 0.29.0 (`event-stream`) | terminal events | no |
| **Templating** | `tera` | 1.20.1 + 2.1.0 | 2.1.0 | 2.1.0 | mise keeps v1 aliased as `tera1` | no |
| **Utility** | `xx` | 2.6.1 (`glob`) | 2.6.1 (`hash`) | 2.6.1 (`fslock`) | **jdx std-lib extension, all three** | **yes** |
| | `strum` (derive) | 0.27.2, 0.28.0 | 0.27.2, 0.28.0 | 0.28.0 | enum↔string | no |
| | `globset` / `ignore` | 0.4.19 / 0.4.31 | same | same | **identical pair in all three** | no |
| | `tempfile` | 3.27.0 | 3.27.0 | 3.27.0 | | no |
| | `which` | 8.0.5 | — | 8.0.5 | binary lookup | no |
| | `regex` / `chrono` | 1 / 0.4 | 1 / 0.4 | 1 / 0.4 | | no |
| | `expr-lang` | 1.1.1 | 1.1.1 (`serde`) | — | expression language | **yes** |
| | `ensembler` | — | 1.1.3 | — | command runner + progress | **yes** |
| **Testing** | `bats` (shell) | — | **150 files** | **72 files** | ⚠️ **the primary CLI test harness** | n/a |
| | `insta` | 1.48.0 (`filters`,`json`) — **80 `.snap`** | — | — | snapshot tests, **mise only** | no |
| | custom `e2e/` | 24 files | — | — | mise's own e2e runner | n/a |
| | `test-log` / `pretty_assertions` / `mockito` / `ctor` | ✓ | — | — | mise only | no |
| | `assert_cmd`, `rstest`, `trycmd`, `predicates` | **0** | **0** | **0** | control arm: `tempfile` → 1/1/1 | — |

### The intersection: direct deps common to ALL THREE

| Crate | mise | hk | fnox | Note |
|---|---|---|---|---|
| `clap` (derive) | 4.6.5 | 4.6.4 | 4.6.4 | |
| `usage-lib` | 4.1.0 | 4.0.0 (via `clap_usage`) | 4.0.0 | **jdx** |
| `xx` | 2.6.1 | 2.6.1 | 2.6.1 | **jdx**, one feature each |
| `demand` | 2.0.5 | 2.0.5 | 2.0.5 | **jdx** |
| `clap-sort` (dev) | 1 | 1 | 1 | **jdx** — the only dev-dep shared by all three |
| `tokio` | 1.53.1 | 1.53.1 | 1.53.1 | |
| `serde` + `serde_json` + `serde_yaml` | 1.0.229 | 1.0.229 | 1.0.229 | |
| `miette` | 7.6.0 | 7.6.0 | 7.6.0 | |
| `thiserror` | 2.0.19 | 2.0.19 | 2.0.19 | |
| `tracing` + `tracing-subscriber` | 0.1.44 / 0.3.23 | same | same | |
| `console` | 0.16.4 | 0.16.4 | 0.16.4 | |
| `reqwest` | 0.13.4 | 0.13.4 | 0.13.4 | rustls in fnox; mise defaults native-tls |
| `indexmap` (`serde`) | 2.14.0 | 2.14.0 | 2.14.0 | |
| `globset` + `ignore` | 0.4.19 / 0.4.31 | same | same | |
| `tera` | 2.1.0 | 2.1.0 | 2.1.0 | |
| `strum` (derive), `regex`, `chrono`, `tempfile` | ✓ | ✓ | ✓ | |
| edition **2024** + `resolver = "3"` | ✓ | ✓ | ✓ | |

**Errors are the one category that is NOT uniform.** mise = `eyre` + `color-eyre` +
`miette`; hk = `eyre` + `thiserror`; fnox = `miette(fancy)` + `anyhow` + `thiserror`.
`miette` appears in all three only because **`xx` itself depends on `miette 7`
unconditionally** (`jdx-xx/Cargo.toml:25`) — every `xx` consumer inherits it. So there is no
single house error story; if you copy one, copy fnox's (`miette` fancy for user-facing
diagnostics + `thiserror` for library errors + `anyhow` at the edges).

**Everything is async on tokio** — even hk, a git-hook runner, pulls
`process`/`rt-multi-thread`/`signal`/`sync`. Nothing here is a blocking CLI.

## 2. jdx's OWN crates — published, and how reusable

All queried live against `https://crates.io/api/v1/crates/<name>`:

| Crate | crates.io max | total dl | recent dl | documented for downstream? |
|---|---|---|---|---|
| `xx` | **2.6.1** | 338,149 | 102,180 | **yes** — `docs.rs/xx`, rustdoc with runnable examples |
| `usage-lib` | **4.1.0** | 381,404 | 112,590 | **yes** — `usage.jdx.dev` |
| `demand` | **2.0.5** | 417,659 | 147,639 | no `documentation` field set |
| `expr-lang` | **1.1.1** | 178,030 | 48,479 | `docs.rs/expr-lang` |
| `clx` | **3.0.2** | 134,507 | 80,408 | none — effectively internal |
| `clap_usage` | **4.0.0** | 73,918 | 48,294 | points at `usage.jdx.dev`; thin |
| `clap-sort` | **1.0.3** | 67,192 | 30,377 | `docs.rs/clap-sort`; trivial |
| `ensembler` | **1.1.3** | 23,420 | 6,179 | `docs.rs/ensembler`; thin, hk-only |
| `pklr` | **1.3.0** | 12,341 | 7,995 | none |
| `usage` (the CLI binary) | 1.4.0 | 8,749 | 313 | — (note: **binary is 1.x while the lib is 4.x**) |

Download counts are heavily inflated by mise/hk/fnox's own CI, so treat them as
"published and maintained", not "third-party adoption".

### `xx` — the full surface (this is the reusable one)

`jdx-xx/src/`: `archive.rs` · `cache.rs` · `context.rs` · `env.rs` · `error.rs` ·
`file.rs` · `fslock.rs` · `git.rs` · `hash.rs` · `home.rs` · `http.rs` · `platform.rs` ·
`process.rs` · `rand/` · `regex.rs` · `suggest.rs` · `test.rs` — **9,769 LOC / 21 files**.

Beyond `xx::fslock` (fnox's `lease.rs`), you get:

- **file ops** — `file::read_to_string`, `file::write` (auto-creates parent dirs),
  `file::mkdirp`, all with better error messages (`jdx-xx/src/lib.rs:44-57`)
- **process** — `process::sh("…")`, `process::cmd("git", &["status"]).read()` builder
  (`jdx-xx/src/lib.rs:60-71`), backed by `duct`
- **git** — `git::Git`, `git::CloneOptions` high-level repo management
- **hashing** — sha2 by default; `hash_blake3` / `hash_md5` / `hash_sha1` opt-in
- **archives** — tar.gz / tar.bz2 / tar.xz / zip, **both directions** (10 granular features)
- **http** — a `reqwest` wrapper (gzip + json + urlencoded)
- **glob** (`globwalk`), **cache**, **env**, **platform detection**, **did-you-mean
  suggestions** (`strsim`), **test helpers**

Feature flags: `archive`, `cache`, `fslock`, `glob`, `hash`, `hash_blake3`, `hash_md5`,
`hash_sha1`, `http`, `native-tls` / `rustls` / `rustls-native-roots`
(`jdx-xx/Cargo.toml:48-70`). Always-on core: `rand`, `log`, `miette`, `regex`, `strsim`,
`thiserror`, plus (non-wasm) `duct`, `filetime`, `homedir`. **It builds for wasm**
(`getrandom` wasm_js target block, `jdx-xx/Cargo.toml:45-46`). MSRV **1.88**, edition 2024.

`xx`'s own dev-deps show the house library-test style, which differs from the CLI style:
`insta`, `pretty_assertions`, `test-log`, `wiremock`, `tempfile` (`jdx-xx/Cargo.toml:72-81`).

## 3. Project shape

| | mise | hk | fnox | usage | xx |
|---|---|---|---|---|---|
| shape | **workspace**, 5 members + root | **single crate** | **workspace**, 2 members | **workspace**, 3 members | **single crate** |
| members | `vfox`, `aqua-registry`, `mise-interactive-config`, `mise-shim`, `mise-sigstore` | — | `.` + `crates/fnox-core` | `cli`, `clap_usage`, `lib` | — |
| edition | 2024 | 2024 | 2024 | — | 2024 |
| resolver | 3 | 3 | 3 | — | — |
| MSRV | **1.91** | **1.88.0** | **1.91.1** | — | **1.88** |
| `.rs` files | 496 | 101 | 116 | 82 | 21 |
| total `.rs` LOC | 240,573 | 22,678 | 37,995 | 24,721 | 9,769 |
| root `src/` LOC | 220,645 | 21,607 | 36,755 | 20,553 | 9,769 |
| build script | `build.rs` (`built`, `phf_codegen`, `cfg_aliases`) | `build/mod.rs` (`codegen` crate) | in `fnox-core` (`proc-macro2`+`quote`) | — | none |
| extra bins | `mise-shim` (workspace member) | `generate-docs` (`bin/generate_docs.rs`) | — | `usage` | lib only |
| shell tests | — (`e2e/`, 24 files) | 150 `.bats` | 72 `.bats` | — | — |

mise workspace member LOC: `vfox` 6,688 · `mise-interactive-config` 5,655 ·
`aqua-registry` 4,449 · `mise-sigstore` 2,194 · `mise-shim` 73.

**fnox's split is the shape to copy for a new CLI.** `fnox-core` holds providers, config and
secret resolution; the root `fnox` binary holds commands, MCP server, TUI, hook-env and
shell integration, and re-declares only what the *binary* needs — the manifest says so
explicitly at `jdx-fnox/Cargo.toml:126-128`. All versions live in `[workspace.dependencies]`
(`jdx-fnox/Cargo.toml:17-106`) and members write `{ workspace = true }`.

**MSRV is a deliberate, documented decision, not drift.** fnox pins 1.91.1 with a comment
telling you not to raise it for a dependency bump — *"pin the dependency to an
MSRV-compatible version instead"* (`jdx-fnox/Cargo.toml:11-15`), because distro/nixpkgs
packagers build from source with an older shared rustc.

`tokei` is **not installed on this host** — LOC is `find … -name '*.rs' | xargs wc -l`
excluding `target/` and `vendor/`, so it includes tests and comments.

## 4. Release / distribution tooling

**Not cargo-dist.** Control-armed: `grep -ril 'cargo-dist\|cargo dist'` finds **zero** hits
in hk/fnox/usage/xx; mise's two hits are `registry/cargo-dist.toml` (mise's *registry entry*
for cargo-dist as a tool it can install) and its vendored aqua registry — not its own use.
No `dist-workspace.toml` / `dist.toml` anywhere. Control: `grep -ril release` over
`.github/` returns 16/4/6/3/1 files, so the probe can see.

**The jdx-standard answer, in four layers:**

1. **Version + changelog + tag** — `release-plz` (mise, hk, fnox, usage) driven by a
   `release-plz.yml` workflow that does nothing but `mise run release-plz`
   (`jdx-hk/.github/workflows/release-plz.yml:38`). The actual logic is a **shell script at
   `mise-tasks/release-plz`** (hk 65 lines, fnox 68 lines). `xx` is the odd one out — it
   uses `release-please` instead. Changelog generation is `git cliff`.
2. **Binary build** — `taiki-e/upload-rust-binary-action` in a target matrix, with
   `build-tool: cargo` for macOS/Windows and `build-tool: cross` for Linux
   (`jdx-fnox/.github/workflows/release.yml:26-63`). Run with `dry-run: true` so it *builds
   and packages* but doesn't upload; the artifacts are collected and a separate
   `create-release` job runs `gh release create`. macOS binaries are **codesigned** via
   `apple-actions/import-codesign-certs` + `codesign: "Developer ID Application: Jeffrey
   Dickey (4993Y37DX6)"`. Targets: aarch64/x86_64 × {apple-darwin, linux-gnu, linux-musl,
   pc-windows-msvc} = 8 for fnox, 7 for hk.
3. **crates.io** — plain `cargo publish` from a workflow job
   (`jdx-hk/.github/workflows/release.yml:224`), or from the release-plz script for
   workspaces (`cargo publish -p fnox-core` then `-p fnox`, because the binary path-depends
   on core at an exact version).
4. **Release notes** — `communique generate "$TAG" --github-release` (another jdx tool; uses
   `ANTHROPIC_API_KEY`) plus a hardcoded sponsor blurb appended with `gh release edit`.

**mise alone is bespoke and much larger** (434-line `release.yml` vs fnox's 173) because it
fans out to every packaging channel: `rpm`, `deb`, plus separate workflows for
`copr-publish`, `ppa-publish`, `snapcraft-publish`, `winget`, `npm-publish`, `docker`,
`release-alpine`. **A new CLI does not inherit any of that** — hk and fnox ship
tarballs + crates.io only, and are installed via mise/`ubi` from GitHub releases.

**The workflow set is a template.** hk, fnox and usage all carry the same nine files with
near-identical sizes: `aube-lock` (20/20/20 lines), `auto-merge-release` (74/74/74),
`pr-closer` (17/21/21), `perf-pr` (205/208/205), `perf` (90/95/90), `docs` (72/62/62),
`zizmor` (21/25/21), `release-plz`, `release`. The `mise-tasks/release-plz` scripts diff to
**~12 lines** between hk and fnox, and every difference is workspace-vs-single-crate publish
or a `|| true`. That is copy-paste, not a shared action or reusable workflow.

Other house conventions visible in the workflows: every action is **SHA-pinned with a
version comment**, `permissions: {}` at workflow level with per-job grants,
`persist-credentials: false`, a `zizmor` (GHA security lint) workflow, `jdx/mise-action` +
`mise trust --all` as the universal setup step, a **per-repo PAT** (`HK_GH_TOKEN`,
`FNOX_GH_TOKEN`) rather than `GITHUB_TOKEN`, and an `auto-merge-release` cron that will not
merge a release younger than 7 days. hk additionally does **PGO + BOLT** optimized builds
with dedicated `[profile.serious]` / `[profile.serious-pgo]` profiles
(`jdx-hk/Cargo.toml:88-99`).

### The dev-loop task vocabulary (the real scaffolding)

Every repo has a `mise.toml` with the same task names: `build`, `test`, `lint`, `lint-fix`,
`ci`, `render` (regenerate docs/completions/schemas), `perf`, `perf:record`, `release-plz`.
hk puts them in `mise-tasks/` as files (18 of them); fnox and usage put most inline in
`mise.toml` and keep only `release-plz` as a file. fnox's `test` is
`depends = ["test:cargo", "test:bats"]` and runs bats under `fnox exec --` with
`--jobs 16` and tranche-splitting for CI (`jdx-fnox/mise.toml:30-56`).

## 5. Is there a "jdx CLI starter"? — **No.**

Control-armed search over **all 623** of jdx's public repos (`gh api users/jdx --jq
.public_repos` = 623; `gh repo list jdx --limit 700` returned 623 rows — the earlier
`--limit 200` was my own bound and was discarded):

- `isTemplate == true`: **3 repos**, all mise-plugin templates —
  `mise-tool-plugin-template`, `mise-backend-plugin-template`, `mise-env-sample`. **None is
  a Rust CLI starter.**
- Regex over name+description for
  `template|starter|scaffold|boilerplate|cookiecutter|skeleton|generator|create-|toolkit`:
  **7 hits**, all accounted for — the three mise-plugin templates, `mise-env-plugin-template`,
  `angular-boilerplate` ("example angular app"), `heroku-plugin-readme-generator`,
  `smithy-typescript` (a fork). **Control arm: `mise` in name → 14 repos**, so the search sees.
- `create-my-cli` looked promising and is **empty** — created 2018-01-09, no README, no
  primary language, 0 stars, last pushed 2024. A dead stub from jdx's oclif (Node) era.
- `gabarit` (French for "template") is **not one either** — `gh repo view` description:
  *"⚠️ SUPER WIP, ignore — toolbelt experiment for coding agents"*, created 2026-07-16.
- `jdx/usage` docs (`jdx-usage/docs/`) contain **no "build a CLI like mise" guide** — the
  tree is `cli/`, `spec/`, `contributing.md`, `index.md`. Grepping for
  `scaffold|starter|template|getting started|new project` hits only vitepress theme files
  and the spec reference. Control arm: `completions` → 14 files, so the corpus is greppable.

**So the honest answer:** the jdx foundation is a *convention*, distributed by copy-paste.
There is no `cargo generate jdx/cli-template`. To stand up a new CLI in this style you would
fork the manifest + `.github/workflows/` + `mise.toml` + `mise-tasks/release-plz` from
**fnox** (the smallest complete workspace example) and delete what you don't need.

### Cost estimate for a new jdx-style CLI

| You get for free | You must copy/write |
|---|---|
| `xx` (file/process/git/hash/archive/http/lock) — 9,769 LOC you don't write | `Cargo.toml` dep block (~40 lines, transcribe from fnox) |
| `usage-lib` + `clap_usage` — completions + docs generation from your clap tree | 9 GHA workflows (~700 lines total, near-verbatim from fnox) |
| `demand` — prompts/selects | `mise-tasks/release-plz` (~68 lines) |
| `clx` — progress/output | `mise.toml` task set (~120 lines) |
| `clap-sort` — the sorted-subcommand test | The bats harness + `test/*.bats` |
| `release-plz` + `git cliff` + `taiki-e/upload-rust-binary-action` (all third-party) | Codesigning secrets / Apple Developer ID (if you want signed macOS builds) |

Realistically: **a day of scaffolding**, and the dependency list is the cheap part. The
expensive, non-obvious parts are the release pipeline (~700 lines of workflow you inherit by
copying, not by importing) and the bats test harness.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — manifest, lockfile, workspace shape, 7-channel release pipeline
- [jdx/hk](https://github.com/jdx/hk) — manifest, lockfile, single-crate shape, PGO+BOLT profiles, release-plz task
- [jdx/fnox](https://github.com/jdx/fnox) — workspace manifest, fnox-core split, MSRV policy, bats harness, release.yml
- [jdx/usage](https://github.com/jdx/usage) — jdx-owned CLI spec crate; docs tree searched for a starter guide
- [jdx/xx](https://github.com/jdx/xx) — jdx-owned utility crate; full module + feature surface
- [jdx/gabarit](https://github.com/jdx/gabarit) — probed as a possible template ("gabarit" = FR "template"); it is not
- [jdx/create-my-cli](https://github.com/jdx/create-my-cli) — probed as a possible starter; empty 2018 stub
- [taiki-e/upload-rust-binary-action](https://github.com/taiki-e/upload-rust-binary-action) — the binary-release action all three use
- [release-plz/release-plz](https://github.com/release-plz/release-plz) — version/changelog/publish automation
