# fnox SDK / config-model research

**Question:** can our secrets CLI be a thin wrapper over fnox, or must it reimplement?
**Date:** 2026-08-03 · **Local version:** fnox 1.32.0 · **Method:** primary sources only
(`gh api` on `jdx/fnox`, repo `docs/`, `fnox --help` on the installed 1.32.0, crates.io).

Status: **COMPLETE.** All six questions answered from primary sources.

> **Provenance note.** The source read is the `jdx/fnox` tarball of `main` whose
> `Cargo.toml` reads `version = "1.32.0"` — i.e. it *is* the installed version, so no
> main-vs-release drift. Line numbers are that tree. Live probes ran against the
> installed `fnox 1.32.0`. **No `fnox get` was ever run and no secret value was printed;**
> live probes report line counts or fixture-only fake names.

## Bottom line

| | verdict |
|---|---|
| SDK | **Exists** (`fnox-core`, published) but **Rust-only — no Python bindings**, so unusable for us |
| JSON | **No general `--json`.** 4 commands only; every introspection command is human-formatted |
| Wrapper viability | **Thin wrapper = shell out + screen-scrape.** Possible, but the contract is weak |
| Biggest hazard | **Unknown profile fails OPEN** — all 50 secrets, rc=0, zero stderr |
| Scoping | **Achievable**, but only as `-P <name> --no-defaults` on every invocation |

## Q1 — Is there an SDK (library crate)?

**YES — a real, published, documented-as-such library crate: `fnox-core`.
But it is Rust-only, and our CLI is Python, so it is unreachable for us.**

Evidence:

- `Cargo.toml` (root) is a **workspace**: `members = [".", "crates/fnox-core"]`,
  `resolver = "3"`. The root `fnox` package declares `[[bin]] name = "fnox"` **and**
  depends on `fnox-core = { path = "crates/fnox-core", version = "1.32.0" }` — the
  `version =` key is what makes it publishable.
  <https://github.com/jdx/fnox/blob/main/Cargo.toml>
- `crates/fnox-core/Cargo.toml` → `description = "Provider library and core types for fnox"`.
- `crates/fnox-core/src/lib.rs` doc comment, verbatim:
  > "Core library for fnox: provider implementations, config types, secret resolution.
  > This crate is the reusable engine underneath the `fnox` binary. It contains the
  > `Provider` trait, every provider implementation, the config data types, the secret
  > resolver, the lease backends, and the `Fnox` convenience API **for downstream
  > consumers**."
- Public modules: `auth_prompt, config, config_path, env, error, http, lease,
  lease_backends, library, providers, secret_resolver, settings, source_registry,
  spanned, suggest, temp_file_secrets`; re-exports `FnoxError, Result, Fnox`.
- The root `fnox` crate ALSO has `src/lib.rs`, which re-exports fnox-core "so existing
  `fnox::providers`, `fnox::config`, etc. paths continue to work **for downstream
  consumers**", plus CLI-only modules (`commands, daemon, hook_env, mcp_server, proxy,
  shell, tui`). So both crates are lib+consumable.

**Published on crates.io — both crates, at 1.32.0.** The crates.io JSON API returned an
access-policy error for every name including the control (`serde`), so that probe was
broken, not the world; I switched to the sparse index:

| crate | `index.crates.io` | versions | latest |
|---|---|---|---|
| `fnox` | HTTP 200 | 21 | 1.32.0 (unyanked) |
| `fnox-core` | HTTP 200 | 12 | 1.32.0 (unyanked) |
| `serde` (control, present) | HTTP 200 | 316 | — |
| `zzqwvbnmnonexist` (control, absent) | **HTTP 404** | — | — |

Both arms fire, so the 200s are real.

### The `Fnox` client API (`crates/fnox-core/src/library.rs`, 430 lines)

> "Convenience client over `Config` — load once, query many. Cheap to clone (Config is
> held behind an `Arc`); hold across `.await` freely." (`library.rs:42-45`)

| item | line | note |
|---|---|---|
| `Fnox::discover()` | `library.rs:75` | upward search, same as the binary |
| `Fnox::open(path)` | `library.rs:100` | explicit config path |
| `.with_profile(p)` | `library.rs:127` | builder |
| `.with_profiles(iter)` | `library.rs:132` | **multiple** active profiles |
| `.with_no_defaults(bool)` | `library.rs:140` | mirrors `--no-defaults` |
| `.profile()` / `.config()` | `library.rs:146` / `153` | accessors |
| `async .get(key) -> Result<Option<String>>` | `library.rs:167` | |
| `.list() -> Result<Vec<String>>` | `library.rs:202` | |

`library.rs:38` also re-exports the discovered filename "so callers can probe with the
same name fnox itself uses".

### ⚠️ The decision-relevant caveat

**There are no Python bindings.** `gh api search/code repo:jdx/fnox pyo3` → **0**;
control arm `clap` on the same query shape → **45**, so the probe discriminates. No
`maturin`, no `cdylib`, no FFI crate in the workspace member list.

So for a **Python** wrapper the SDK is not usable without writing our own PyO3 binding
and shipping a compiled wheel per platform. **Practically: we shell out and parse
output** — which makes Q2 the load-bearing question, not Q1.

## Q2 — Machine-readable output

**There is NO general `--json`. Structured output exists on exactly four commands, and
none of them is an introspection command a wrapper would want.** Everything a wrapper
needs to *read* (`list`, `check`, `profiles`, `config-files`, `doctor`, `provider list`)
is human-formatted only — rendered via the `tabled` crate (`Cargo.toml` dep).

Method: `fnox <cmd> --help` on the installed 1.32.0 for each command, cross-checked
against `fnox.usage.kdl` in the 1.32.0 source tarball (the tarball's
`Cargo.toml` reads `version = "1.32.0"`, i.e. it *is* the installed version, not `main`
drift).

### The complete structured-output surface

| command | flag | values | note |
|---|---|---|---|
| `export` | `-f/--format env\|shell\|json\|yaml\|toml` | `usage.kdl:63` | **emits secret VALUES** |
| `import` | `--format env\|json\|yaml\|toml` | `usage.kdl:100` | *input* parsing, not output |
| `lease create` | `-f/--format shell\|json\|env` | `usage.kdl:118` | `src/commands/lease.rs:326-346` |
| `scan` | `--format human\|json` | `usage.kdl:203` | `src/commands/scan.rs:167,402` |
| `schema` *(hidden)* | — | `src/commands/schema.rs` | JSON Schema of the config |

Control arm for the negative: grepping `fnox.usage.kdl` for `json` returns those **4**
hits against a total of **71** `flag ` lines — so the file is being read and the token
is found where it exists. `fnox list --help` etc. were read in full, not grepped.

### `fnox schema` — the one genuinely useful machine contract (undocumented)

`src/commands/schema.rs` is `#[command(hide = true)]`, so it does **not** appear in
`fnox --help`, but it is wired (`src/commands/mod.rs:32,168-170,200`) and it runs:

```
$ fnox schema | head -3
{ "$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Config", ...
$ fnox schema | wc -c
47739
```

It is `schemars::schema_for!(Config)` — a 47 KB JSON Schema of the **config file
format**. Useful for validating/generating a `fnox.toml`; it says nothing about
*runtime* state. Being `hide = true` it carries no stability promise.

### What screen-scraping actually looks like

```
$ fnox config-files
~/.config/fnox/config.toml          # one path per line — parseable, but no contract

$ fnox profiles
Available profiles:
  default (50 secrets)              # prose + parenthesised count
```

`fnox list` is a `tabled` table with truncation by default (`-f/--full` to disable,
`-s/--sources` to add source paths, `-V/--values` to add values). Parsing it is a
column-width-dependent screen-scrape.

**Consequence for the wrapper decision:** a Python wrapper gets one clean contract
(`fnox schema`, hidden), one value-bearing structured dump (`export --format json`,
which defeats the point of not handling values), and otherwise **regex over
human-formatted tables**. That is the fragility to price in — not the absence of an SDK.

## Q3 — Config discovery and precedence

**The prior measurement is CONFIRMED against 1.32.0 source, and it is stronger than
"`-c` adds a config": the global config is layered under *everything*, and even
`root = true` does not switch it off.** Source comment, verbatim
(`crates/fnox-core/src/config.rs:640-644`, doc comment on `load_explicit`):

> "Unlike `Self::load_with_recursion` this does not search parent directories, but the
> file's own imports and the global config are still layered underneath it — **the
> global config is the base for every project, and `root = true` doesn't disable it
> either.**"

### The two load strategies (`config.rs:621-639`, `load_smart`)

`uses_config_discovery(path)` (`config.rs:44-48`) decides. It returns true **only for a
bare default filename**; the doc comment (`config.rs:38-43`) is explicit:

> "Only the bare default filenames do; anything else (**including `./fnox.toml` or an
> absolute path to a `fnox.toml`**) is treated as an explicit path and loads just that
> file, its imports, and the global config."

So `-c fnox.toml` recurses, but `-c ./fnox.toml` does **not** — a real footgun for a
wrapper that normalises paths.

| strategy | trigger | behaviour |
|---|---|---|
| `load_with_recursion` (`:710`) | bare default filename | walk **up from cwd**, merging every dir's config files; global as base at fs root |
| `load_explicit` (`:646`) | any other `-c` value | that file + its `import`s + **the global config** |

### Precedence, lowest → highest

1. **`FNOX_CONFIG_DIR/config.toml`** — the global/user config (`config.rs:813-814`,
   `global_config_path()`). `FNOX_CONFIG_DIR` defaults to `$XDG_CONFIG_HOME/fnox`, else
   `~/.config/fnox` on unix (`crates/fnox-core/src/env.rs:44-55`).
2. **Parent-directory configs**, farthest ancestor first (`load_recursive`, `:735-793`).
3. **`import = [...]`** entries of a given file — loaded *before* and overridden by the
   file that imports them (`:773-777`).
4. **The nearest/most-local config file.**

Within a single directory, `all_config_filenames()` gives the order
(`config.rs:20-36`), "first = lowest priority, last = highest":

`fnox.toml` → `.fnox.toml` → `fnox.<profile>.toml` → `.fnox.<profile>.toml` →
`fnox.local.toml` → `.fnox.local.toml`

### The single exception

`load_explicit` returns early **only** when the explicit path *is itself* the global
config path (`config.rs:659-663`) — otherwise the global is always merged in.

`root = true` stops the *upward walk* but still loads the global underneath
(`config.rs:757-770`).

**Verified live:** `fnox config-files` run from this repo prints exactly
`~/.config/fnox/config.toml` — one file, the global, with no project config present.

### Consequence for a per-project wrapper

There is **no supported way to get a clean, project-only view.** Not `-c`, not
`root = true`. The only lever is `FNOX_CONFIG_DIR` — pointing it at an empty/temp dir
makes `load_global()` find nothing (`config.rs:820-829` returns `(Config::new(), false)`
when the path does not exist). That is an env-var override, not a config feature, but it
is the one mechanism that actually isolates.

## Q4 — Profiles

### Declaration and activation

Declared as TOML sections — `[profiles.<name>.secrets]` and
`[profiles.<name>.providers]` (`docs/guide/profiles.md`). Activation, in precedence
order (`Config::get_profiles`, `config.rs:1326-1331`): **CLI `-P/--profile` > `FNOX_PROFILE` env > default**.
`normalize_profiles` (`:1335-1347`) splits on commas, trims, drops names failing
`env::is_valid_profile_name`, and falls back to `["default"]` when the result is empty.

### Composition (#605) — what it means

PR [#605](https://github.com/jdx/fnox/pull/605), *"feat(config): support composing
multiple active profiles"*, **MERGED 2026-07-12** by @gaojunran. From the PR body:

> "Allow activating multiple profiles simultaneously as an ordered overlay stack. Later
> profiles override earlier ones on key conflicts, with top-level config as the base."
>
> ```
> top-level config + profiles.aws + profiles.prod
> ```

Three activation spellings, all equivalent: `-P aws -P prod`, `-P aws,prod`,
`FNOX_PROFILE=aws,prod`. The overlay is a plain ordered `extend` over an `IndexMap`
(`config.rs:1440-1444`), so "compose" means **last-wins key-by-key merge**, not any kind
of intersection or scoping.

Consequences the PR body lists: `--write-profile` becomes **required** when multiple
profiles are active (write target is otherwise the single active profile); the daemon's
socket-path hash and cache key include the full stack; `Fnox` gained `with_profiles()`.

### ⚠️ The unknown-profile fail-open — CONFIRMED, and it has a mitigation

**Root cause, at source.** `Config::get_secrets_with_no_defaults`
(`crates/fnox-core/src/config.rs:1428-1444`):

```rust
let has_non_default = profiles.iter().any(|p| p != "default");
let mut secrets = if !has_non_default || !no_defaults {
    self.secrets.clone()          // <-- ALL top-level secrets
} else {
    IndexMap::new()
};
for profile in profiles.iter().filter(|p| *p != "default") {
    if let Some(profile_config) = self.profiles.get(profile) {   // <-- silent no-match
        secrets.extend(profile_config.secrets.clone());
    }
}
```

`if let Some(...)` with no `else`: an unknown profile name simply **contributes
nothing**, and since `no_defaults` defaults to `false`, the top-level secrets remain.
There is no existence check anywhere on the read path. (The two `profiles.get(profile).is_none()`
sites at `config.rs:1131` and `:1259` are **write** paths that *auto-create* the table —
they are not validation.)

**Live probe, control-armed** (`fnox list`, line counts only — no values printed):

| arm | lines | rc | stderr |
|---|---|---|---|
| `-P default list` (known-good control) | 51 (hdr + 50) | 0 | 0 bytes |
| `-P zqbwmxvv77 list` (unknown) | **51 — identical** | **0** | **0 bytes** |
| `-P zqbwmxvv77 --no-defaults list` | **1 (hdr only, 0 secrets)** | 0 | 0 bytes |

The known-good arm and the unknown arm are indistinguishable → fail-open reproduced. The
third arm shows **`--no-defaults` flips it to fail-CLOSED.** (Control string invented
fresh for this run.)

`fnox -P zqbwmxvv77 profiles` still prints only `default (50 secrets)` — it lists
*declared* profiles and never objects to the bogus active one.

### Is it intentional / documented / tracked?

- **Intentional by construction, yes** — `docs/guide/profiles.md` § "Profile Inheritance"
  documents that "Profiles automatically inherit secrets from the top level" as a
  *feature* to "reduce duplication". An unknown profile inheriting everything is the
  degenerate case of that design.
- **Documented as a hazard: NO.** Nothing in `docs/` warns that a typo'd profile name
  silently yields the full default set.
- **Tracked upstream: cannot be tracked.** ⚠️ **`jdx/fnox` has GitHub Issues DISABLED**
  (`gh issue list -R jdx/fnox` → *"the 'jdx/fnox' repository has disabled issues"*). My
  first issue-search returned 0 results for that reason, **not** because nothing matches
   — a broken probe. They use **Discussions** (124 total). Searching those for `profile`
  returns 4, none about unknown-profile handling:
  #631 `ci-redact does not respect FNOX_PROFILE`, #601 `FR: support composing multiple
  active profiles` (→ #605), #570 `Fall back to default value when provider isn't
  configured for the active profile`, #577 `fnox daemon clear can be misleading with
  profile-scoped daemon caches`.

### `--no-defaults` / `FNOX_NO_DEFAULTS`

Per `fnox --help`: *"Do not merge top-level secrets into the selected profile."* It is a
real setting (`crates/fnox-core/src/settings.rs:47`), bound to env
`FNOX_NO_DEFAULTS` (`crates/fnox-core/settings.toml:57`), documented at
`docs/reference/environment.md:35-40` and `docs/reference/configuration.md:535-538`:

> "With `--no-defaults`, only `[profiles.<name>.secrets]` are used for the selected profile."

**It is a no-op unless a non-default profile is active** (`has_non_default &&
no_defaults`, `config.rs:1433-1438`) — so `--no-defaults` alone, on the default profile,
does nothing at all.

Doc drift noted: `docs/guide/profiles.md` shows `fnox profiles` printing
`default (active)`, but 1.32.0 prints `default (50 secrets)`.

## Q5 — Per-project scoping

**YES — "this project gets these 6 secrets" IS expressible, but only via
`[profiles.<name>.secrets]` + `--no-defaults`, and `--no-defaults` must be passed on
EVERY invocation because it cannot be declared in a config file.**

### The default model is purely ADDITIVE — a project config cannot subtract

`docs/guide/hierarchical-config.md` states the merge order explicitly:

> 1. Loads `~/.config/fnox/config.toml` (global config, if exists)
> 2. Loads `project/fnox.toml` (parent) … 5. `…/fnox.local.toml`
>
> "**Global config provides the base layer available to all projects.**"

So a project-local `fnox.toml` alone can only **add** to (or key-override within) the
global's 50. There is no `exclude`, no allow-list, no `root`-style cut for the global
(Q3: `root = true` explicitly does not disable it).

### The mechanism that DOES scope: profile + `--no-defaults`

Measured in a purpose-built isolated fixture (`FNOX_CONFIG_DIR` pointed at a temp dir
holding 3 fake `GLOBAL_*` secrets; a project `fnox.toml` with 1 top-level `PROJ_TOP` and
`[profiles.proj.secrets]` holding `SCOPED_ONE`/`SCOPED_TWO`; plaintext `default =`
values, no real credentials):

**Isolation control arm:** `fnox config-files` printed exactly the two fixture files and
**not** `~/.config/fnox/config.toml` — so `FNOX_CONFIG_DIR` really does relocate the
global layer, and the fixture is not silently merging the host's 50.

| arm | resulting secret set |
|---|---|
| A — default profile | `GLOBAL_A GLOBAL_B GLOBAL_C PROJ_TOP` |
| B — `-P proj` | `GLOBAL_A GLOBAL_B GLOBAL_C PROJ_TOP SCOPED_ONE SCOPED_TWO` (inheritance) |
| **C — `-P proj --no-defaults`** | **`SCOPED_ONE SCOPED_TWO` — exactly the scoped set** |
| D — `-P typo99` (unknown) | `GLOBAL_A GLOBAL_B GLOBAL_C PROJ_TOP` — identical to A (**fail-open**) |
| E — `-P typo99 --no-defaults` | *(empty)* — fail-closed |

Five arms, five distinct outcomes (D matching A is itself the finding), so the fixture
admits every result and is not rigged toward one answer. Arm C independently reproduces
the Q4 fail-open in a clean environment, away from the host config.

### ⚠️ The catch that decides the design

**`no_defaults` cannot be declared in a `fnox.toml`.** Control arm: enumerating every
`sources.` line in `crates/fnox-core/settings.toml` yields **11 entries across all 7
settings — every one is `sources.cli` or `sources.env`, and there is not a single
`sources.config`.** (Settings: `age_key_file`, `profile`, `no_defaults`,
`shell_integration_output`, `if_missing`, `http_timeout`, `if_missing_default`.)

So scoping is **invocation-time only**. A project cannot declare "I am scoped"; the
caller must supply `-P <name> --no-defaults` (or `FNOX_PROFILE` + `FNOX_NO_DEFAULTS`)
every single time. Miss either half and you silently get all 50 back — arm D is what
that looks like, and it is rc=0 with zero stderr.

For a **wrapper**, that is actually workable: injecting two flags on every `fnox`
call is exactly the kind of thing a wrapper is for. But it means the scoping guarantee
lives entirely in *our* code, not in fnox's config — nothing on disk enforces it, and
anyone invoking `fnox` directly bypasses it completely.

## Q6 — `fnox.<profile>.toml`

**The prior session's conclusion is CONFIRMED on the reachability half, and REFUTED on
the "mutually exclusive with `--no-defaults`" half.**

### It exists, and it is generated purely from the active profile list

`crates/fnox-core/src/config.rs:24-36`:

```rust
pub fn all_config_filenames(profiles: &[String]) -> Vec<String> {
    let mut files = vec![DEFAULT_CONFIG_FILENAME.to_string(), ".fnox.toml".to_string()];
    for p in profiles.iter().filter(|p| *p != "default") {
        files.push(format!("fnox.{p}.toml"));
        files.push(format!(".fnox.{p}.toml"));
    }
    files.push("fnox.local.toml".to_string());
    files.push(".fnox.local.toml".to_string());
    files
}
```

Note the `.filter(|p| *p != "default")` — **`fnox.default.toml` is never loaded.** A
per-profile file only exists for non-default profile names.

### CONFIRMED: it is project-config-only, unreachable for a user-level setup

`all_config_filenames()` is consumed only by the **directory-walking** paths —
`load_recursive` (`config.rs:737`), `find_project_dir` (`config.rs:797`), and
`uses_config_discovery` (`config.rs:45`). Each joins the filename onto a *directory being
walked* (`dir.join(filename)`, `config.rs:745`).

The global config never goes through that function. It is a single hardcoded name:

```rust
pub fn global_config_path() -> PathBuf { env::FNOX_CONFIG_DIR.join("config.toml") }  // config.rs:813-814
```

**Control arm for the absence:** grepping the entire source (`crates/fnox-core/src/` and
`src/`) for the literal `"config.toml"` returns **exactly one hit** — `config.rs:814`.
The same grep shape finds the six project filenames in `all_config_filenames`, so it
discriminates. There is no `~/.config/fnox/config.<profile>.toml`, no
`~/.config/fnox/fnox.<profile>.toml`, and no `.local` variant at user level.

⚠️ **Caveat on "unreachable":** `FNOX_CONFIG_DIR` is a *directory*, and the upward walk
starts at **cwd**, not at the config dir — so pointing `FNOX_CONFIG_DIR` at a directory
does not cause `fnox.<profile>.toml` files inside it to be picked up. The only way to
reach a per-profile file is to have it in cwd or an ancestor of cwd.

### REFUTED: it is NOT mutually exclusive with `--no-defaults`

They operate on **different layers** and compose fine:

- `fnox.<profile>.toml` selects which **files** are read (`all_config_filenames`).
- `--no-defaults` controls whether **top-level secrets are merged into the selected
  profile** (per `fnox --help`) — a within-config merge decision, applied after loading.

Nothing in `all_config_filenames` or `load_recursive` consults a no-defaults flag; see
Q4 for where `no_defaults` is actually read. Marking the prior claim **REFUTED**, though
the practical effect for us is unchanged because the reachability half already rules the
mechanism out for a user-level setup.

## Probes that were broken (recorded so they are not repeated)

1. **crates.io JSON API** (`https://crates.io/api/v1/crates/<name>`) returned an
   *"unable to process your request … API data access policy"* error for **every** name
   including the control `serde`. Not a signal about fnox. **Use
   `https://index.crates.io/<a>/<b>/<name>` instead** — it gave 200/200/200/404 across
   fnox / fnox-core / serde / a nonsense name.
2. **`gh issue list -R jdx/fnox` / `gh search issues`** return nothing because
   **the repo has GitHub Issues DISABLED**, not because nothing matches. Use the
   **Discussions** GraphQL query (124 discussions) for upstream reports.

## GitHub repos touched

- [jdx/fnox](https://github.com/jdx/fnox) — primary subject: `Cargo.toml`,
  `crates/fnox-core/{Cargo.toml,src/lib.rs,src/library.rs,src/config.rs,src/config_path.rs,src/env.rs,src/settings.rs,settings.toml}`,
  `src/{lib.rs,commands/schema.rs,commands/mod.rs,commands/lease.rs,commands/scan.rs}`,
  `fnox.usage.kdl`, `CHANGELOG.md`, `docs/guide/{profiles.md,hierarchical-config.md}`,
  `docs/reference/{configuration.md,environment.md}`, PR #605, Discussions #570/#577/#601/#631
