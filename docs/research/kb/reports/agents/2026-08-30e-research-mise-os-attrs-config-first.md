# Research: mise OS/platform tool attributes — can config + mise commands replace the Python mirror?

Question (operator, verbatim): *"did we research how to make use of mise os specific
tool attributes to remove code and try to be config first?"*

Status: COMPLETE.

## Executive summary

**The research was not done before, and the answer is yes — substantially.**

1. mise's `os` attribute is a real, documented, arch-aware tool-scoping
   mechanism (`os = ["linux/arm64"]`), available since **2026.4.12** for the
   compound OS/arch form; we pin **2026.8.14**, so nothing is blocked on a
   release.
2. **`mise ls --current --json` reports the post-`os=`-filter truth**, keyed by
   backend-prefixed tool name and carrying `requested_version` — exactly the
   shape the smoke's expected set is in. Proven by a live, control-armed probe
   on the real 2026.8.14 binary (5 included / 4 excluded across four axes).
3. **The smoke script already calls `mise ls --json` in-container**
   (`image.py:446`), and that call is **already os-filtered** — I probed the
   exact jq pattern it uses. Only the *expected* side of its diff is predicted
   on the macOS host. Both sides can come from that one JSON document, which
   removes the prediction entirely, along with the `arch` parameter and the
   normalisation tables.
4. ⚠️ **I found a live defect while doing this:** `image.py` asserts that
   `os = "linux"` as a bare string is *"rejected by mise as a type error"* and
   raises `TypeError` on it. **mise accepts it** (`parse_string_or_array`) —
   confirmed both in source and by live probe. That is the #845 defect class,
   still present.
5. Limits are real but narrow: the **backend registry** can exclude a tool with
   nothing in the TOML saying so (so no host parser can ever be correct);
   `mise ls` only speaks for the platform it runs on; and `[bootstrap.packages]`
   is a separate domain with *inverted* empty-list semantics.

## 0. Sources and their currency (control arms first)

### Primary source A — mise SOURCE, offline

`~/dev/github/ray-manaloto/knowledge-base/sources/mise/` — full `jdx/mise` clone,
including `docs/` (the docs site is built from this tree, so `docs/*.md` IS
`mise.jdx.dev`).

⚠️ **CURRENCY DRIFT FOUND (cross-check, two routes disagreed).**

| Route | Value |
|---|---|
| `sources/mise.manifest` `ref =` / `commit =` | `v2026.8.14` / `2a3ea199…` |
| Actual working tree `git log -1` | `c2a0cb9d…` — *"chore: release 2026.8.10 (#12187)"*, 2026-08-20 |
| Actual working tree `Cargo.toml:15` | `version = "2026.8.10"` |

So the on-disk corpus is **2026.8.10**, four patch releases behind the
**2026.8.14** this repo actually runs (host `mise --version` → `2026.8.14
macos-arm64 (2026-08-26)`; image pins `ARG MISE_VERSION=2026.8.14`,
`.devcontainer/Dockerfile:115`). The manifest's own invariant comment says the
pin MUST track the version we run — it does; the *clone* does not.

**Consequence for this report:** every source claim below is verified against
2026.8.10 and MUST be re-checked against 2026.8.14 before being load-bearing.
I re-verify the load-bearing ones against the live v2026.8.14 tag (see §later).
This drift is itself a finding worth reporting to the KB repo.

### Repo's pinned mise version

- Host + image: **2026.8.14** (`.devcontainer/Dockerfile:115` `ARG MISE_VERSION=2026.8.14`;
  `mise --version` → `2026.8.14 macos-arm64 (2026-08-26)`).

---

## Q1. What `os` on a `[tools]` entry actually supports

### The docs (primary, authoritative)

`docs/dev-tools/index.md:198-246` — section **"OS-Specific Tools"** (this file
renders as <https://mise.jdx.dev/dev-tools/#os-specific-tools>). Verbatim
content:

- Syntax: `ripgrep = { version = "latest", os = ["linux", "macos"] }` — the
  table form of a `[tools]` entry, `os` an array.
- OS identifiers: `"linux"` (all Linux distros), `"macos"` (`"darwin"` accepted
  as an alias), `"windows"` (`"win"` accepted as an alias). (`:220-224`)
- **OS/arch combinations** exist (`:226-244`): `hk = { version = "latest",
  os = ["linux", "macos/arm64"] }`, `mytool = { version = "latest",
  os = ["linux/x64"] }`.
- Arch identifiers: `"arm64"` (or `"aarch64"`), `"x64"` (or `"x86_64"` or
  `"amd64"`). (`:238-241`)
- Semantics, verbatim (`:243`): *"When an entry contains `/`, both the OS and
  architecture must match. When an entry is just an OS name, it matches any
  architecture on that OS."*
- Skip behaviour, verbatim (`:245`): *"If a tool specifies an `os` restriction
  and the current operating system is not in the list, mise will skip
  installing and using that tool."*

### The source (mise 2026.8.10, `src/toolset/tool_request.rs:467-484`)

```rust
pub fn is_os_supported(&self) -> bool {
    if let Some(os_list) = self.os() {
        let current_os = &crate::cli::version::OS;
        let current_arch = &crate::cli::version::ARCH;
        let matched = os_list.iter().any(|entry| {
            if let Some((os, arch)) = entry.split_once('/') {
                normalize_os(os) == current_os.as_str()
                    && normalize_arch(arch) == current_arch.as_str()
            } else {
                normalize_os(entry) == current_os.as_str()
            }
        });
        if !matched { return false; }
    }
    self.ba().is_os_supported()      // <- BACKEND-level restriction, second gate
}
```

Normalizers, `tool_request.rs:663-679`:

```rust
fn normalize_os(os: &str) -> &str {
    match os { "darwin" | "macos" => "macos", "windows" | "win" => "windows", other => other }
}
fn normalize_arch(arch: &str) -> &str {
    match arch { "x86_64" | "amd64" | "x64" => "x64", "aarch64" | "arm64" => "arm64", other => other }
}
```

Unit tests at `tool_request.rs:1050-1069` confirm each mapping, and confirm
unknown tokens pass through unchanged (`normalize_os("freebsd") == "freebsd"`,
`normalize_arch("riscv64") == "riscv64"`).

**Answers to the sub-questions:**

| Sub-question | Answer | Citation |
|---|---|---|
| Legal OS values | `linux`, `macos`/`darwin`, `windows`/`win` — and **any other string passes through unchanged** and is compared against `std::env::consts::OS`, so `freebsd` works too | `tool_request.rs:663-670`, test `:1057` |
| OS-only or OS+arch | **Both.** `"linux"` = OS-only; `"linux/arm64"` = OS+arch, both halves must match | `tool_request.rs:471-477`; docs `:243` |
| Legal arch values | `arm64`/`aarch64` → `arm64`; `x64`/`x86_64`/`amd64` → `x64`; anything else passes through unchanged | `tool_request.rs:672-679` |
| Case sensitivity | **CASE-SENSITIVE.** `normalize_os`/`normalize_arch` are exact `match` arms with an `other => other` fallthrough; no `to_lowercase`, no `trim`. `"Linux"` falls through unchanged and `"Linux" != "linux"` → no match | `tool_request.rs:663-679` |
| What happens when excluded | **Skipped silently.** Not an error. `is_os_supported()` is called as a *filter* at every consumer | see call sites below |

### "Skipped silently" — the call sites that make it so

Every consumer treats a false result as a `continue`/`filter`, never an error:

- `src/toolset/tool_request_set.rs:52` — `if tr.is_os_supported() && !tr.is_install_satisfied(…)` → excluded from the missing/install list.
- `src/toolset/tool_version_list.rs:70,74` — `.filter(|tv| tv.request.is_os_supported())`.
- `src/toolset/mod.rs:164` — `list_missing_plugins` filters on it.
- `src/toolset/helpers.rs:63` — `if !tr.is_os_supported() { continue; }`, with the comment *"Skip requests not applicable to this OS, matching doctor's analyze_system_deps and bootstrap's collect_plugin_deps."*
- `src/toolset/mod.rs:665` — `is_disabled()` returns true when `!ba.is_os_supported()`.

So an excluded tool is **not installed, not listed as missing, and not an
error**. That is precisely the behaviour `.devcontainer/mise-system.toml`'s
`conda:gxx` relies on.

---

## ⚠️ TWO DEFECTS IN THIS REPO'S MIRROR, found by reading the source

### DEFECT 1 — `os = "linux"` (bare string) is VALID in mise; `image.py` raises `TypeError`

`python/src/dotfiles_setup/image.py:194-198` docstring asserts:

> *"An `os` value that isn't a list (e.g. the bare string `os = "linux"`, **which
> mise itself rejects as a type error**) raises `TypeError` …"*

**That claim is false.** mise's option parser routes `os` through
`parse_string_or_array`, which explicitly accepts a bare string:

`src/toolset/tool_version_options.rs:336-341`
```rust
fn insert_core_option(&mut self, key: &str, value: &toml::Value) -> Result<bool, String> {
    match key {
        "os" => { self.os = Some(parse_string_or_array(value, "os")?); Ok(true) }
```
`src/toolset/tool_version_options.rs:494-508`
```rust
fn parse_string_or_array(value: &toml::Value, key: &str) -> Result<Vec<String>, String> {
    match value {
        toml::Value::String(s) => Ok(vec![s.clone()]),          // <-- bare string OK
        toml::Value::Array(values) => …,
        _ => Err(format!("{key} must be a string or array")),
    }
}
```

So `"conda:gxx" = { version = "…", os = "linux/arm64" }` is a config **mise
installs correctly** and **`image.py` crashes on** (`TypeError`). Same defect
class as #845: the host-side mirror predicting mise's behaviour and getting it
wrong, producing a red gate on a correct image.

Control arm for this claim: the same `parse_string_or_array` function is used
for `depends` (`tool_version_options.rs:342`), and `depends = "foo"` as a bare
string is likewise accepted — so the function is genuinely the shared
string-or-array parser, not a special case I misread.

### DEFECT 2 (minor, and this one the repo got RIGHT for tools) — empty-list asymmetry

For **tools**, an empty `os = []` matches nothing: `os_list.iter().any(…)` over
an empty vec is `false` → `matched == false` → skipped
(`tool_request.rs:470-479`). `image.py`'s docstring says exactly this and is
**correct**.

But for **`[bootstrap.packages]`** the rule is INVERTED — empty means
*supported*:

`src/system/mod.rs:174-179`
```rust
fn is_os_supported(&self) -> bool {
    let Self::Options(options) = self else { return true; };
    options.os.is_empty() || options.os.iter().any(|entry| package_os_matches(entry))
}
```

Anyone generalising `image.py`'s tool rule to the apt section would get it
backwards. Not currently a live bug (no `os` on any `[bootstrap.packages]`
entry today), but a trap for the redesign.

---

## Q2. Sibling attributes that do related work

### EXISTS — `os` on `[bootstrap.packages]` too

`docs/bootstrap/packages/index.md:35`:
```toml
"brew-cask:font-jetbrains-mono" = { os = ["linux", "macos"] }
```
Parsed by `deserialize_package_os` (`src/system/mod.rs:186-200`) which, like the
tools path, accepts `OneOrMany` — a bare string **or** an array. Filtering by
`package_os_matches` (`src/system/mod.rs:174-179`), empty-means-supported as
noted above.

This matters directly: `.devcontainer/mise-system.toml`'s `[bootstrap.packages]`
holds 66 apt pins, none arch-scoped today. If an arch-asymmetric apt package
ever appears, `os` is the declarative answer there too.

### EXISTS — `enable_tools` / `disable_tools` settings

`src/toolset/mod.rs:661-668`:
```rust
fn is_disabled(&self, ba: &BackendArg) -> bool {
    let settings = Settings::get();
    !ba.is_os_supported()
        || !tool_enabled(settings.enable_tools().as_ref(), &settings.disable_tools(), &ba.short.to_string())
}
```
A second, settings-level way to exclude a tool — but keyed by tool NAME, not by
platform, so it cannot express "arm64 only" on its own.

### EXISTS — Tera templating in `[tools]` VERSION values, with `arch()` / `os()`

`docs/templates.md:9-14` — templates are available in *"Most `mise.toml`
configuration values"*, with the explicit caveat *"The `mise.toml` file itself
is not templated and must be valid toml"*. The doc's own example templates a
`[tools]` value (`:25-30`):

```toml
[tools]
terraform = "{{ env.TERRAFORM_VERSION }}"
```

Available functions include `arch() -> String` — *"such as `x64` or `arm64`"*
(`docs/templates.md:282`) — and `os()` (`:509`).

**Probed live (mise 2026.8.14, macos/arm64):**

```toml
[tools]
"npm:uuid" = "{% if arch() == 'arm64' %}9.0.0{% else %}8.0.0{% endif %}"
```
→ `npm:uuid  requested=9.0.0`

So a **per-architecture VERSION** is expressible declaratively, today.

### ⚠️ …but `os` ARRAY ELEMENTS are NOT templated (control-armed negative)

```toml
[tools]
"npm:ms"    = { version = "2.1.3", os = ["macos"] }        # CONTROL: literal
"npm:uuid"  = { version = "9.0.0", os = ["{{ os() }}"] }   # test
"npm:chalk" = { version = "5.3.0", os = ["{{os()}}"] }     # test, no spaces
```
→ `mise ls --current -J` returns **`npm:ms` only.**

**Control arm:** the literal-`os` entry DID come back, so the probe can return
entries — the absence of the two templated ones is a real negative, not a blind
probe. The template text is compared verbatim against `std::env::consts::OS`
and never matches.

(Not that templating `os` would be useful — `os = ["{{ os() }}"]` is a tautology
— but it bounds what "config-first" can mean: you cannot compute an `os`
restriction, only state it literally.)

### EXISTS — backend-level platform restriction (the one no config can see)

`is_os_supported()` on a tool request falls through to
`self.ba().is_os_supported()` (`tool_request.rs:483`), i.e.
`src/cli/args/backend_arg.rs:703-710`:
```rust
pub fn is_os_supported(&self) -> bool {
    if self.uses_plugin() { return true; }
    if let Some(rt) = REGISTRY.get(self.short.as_str()) { return rt.is_supported_os(); }
    true
}
```
So the **registry** can declare a tool unsupported on a platform independently
of anything written in the config. `image.py`'s docstring already flags this
correctly as un-mirrorable. It is the strongest single argument against any
host-side prediction: *the config does not contain the answer.*

---

## Q3 + Q4. THE CRUX — `mise ls --current --json` reports the post-filter truth

### The live probe (this is the load-bearing evidence)

Run against the **host's real mise 2026.8.14** (`macos-arm64`), in an isolated
directory with the global config neutralised
(`MISE_GLOBAL_CONFIG_FILE=<empty file>`).

Probe config (`scratchpad/probe/mise.toml`) — nine entries chosen so the probe
**must** discriminate on four independent axes:

```toml
[tools]
"npm:cowsay"   = { version = "1.6.0", os = ["linux"] }                     # OS mismatch
"npm:left-pad" = { version = "1.3.0", os = ["macos"] }                     # OS match
"npm:is-odd"   = { version = "3.0.1", os = ["macos/arm64"] }               # OS+arch match
"npm:is-even"  = { version = "1.0.0", os = ["macos/x64"] }                 # arch mismatch
"npm:rimraf"   = { version = "5.0.0", os = "macos" }                       # BARE STRING
"npm:chalk"    = { version = "5.3.0", os = [] }                            # empty list
"npm:uuid"     = "9.0.0"                                                   # no os key
"npm:dedent"   = { version = "1.5.0", os = ["Linux"] }                     # wrong CASE
"npm:ms"       = { version = "2.1.3", os = ["linux/arm64", "macos/arm64"] } # multi-entry
```

Command and result:

```
$ cd probe && mise trust ./mise.toml
$ MISE_GLOBAL_CONFIG_FILE=./empty-global.toml mise ls --current -J
rc=0        (no error, no warning on stderr)
keys: npm:is-odd  npm:left-pad  npm:ms  npm:rimraf  npm:uuid
```

**Both arms fire — 5 included, 4 excluded — so the probe discriminates.**

| Entry | `os` | Expected | `mise ls --current -J` | |
|---|---|---|---|---|
| `npm:left-pad` | `["macos"]` | included | **included** | ✓ |
| `npm:is-odd` | `["macos/arm64"]` | included | **included** | ✓ |
| `npm:ms` | `["linux/arm64","macos/arm64"]` | included | **included** | ✓ |
| `npm:uuid` | *(none)* | included | **included** | ✓ |
| `npm:rimraf` | `"macos"` **bare string** | ??? | **included** | ⚠️ see below |
| `npm:cowsay` | `["linux"]` | excluded | **excluded** | ✓ |
| `npm:is-even` | `["macos/x64"]` | excluded | **excluded** | ✓ |
| `npm:chalk` | `[]` | excluded | **excluded** | ✓ |
| `npm:dedent` | `["Linux"]` | excluded | **excluded** | ✓ |

Four independent facts confirmed live, not inferred:

1. **`os=` filtering is applied by `mise ls --current`** — the command reports
   the resolved set, so nothing needs to predict it.
2. **Exclusion is silent** — `rc=0`, empty stderr. Not an error, not a warning.
3. **Case sensitivity is real** — `["Linux"]` was excluded.
4. **`os = "macos"` as a BARE STRING is accepted and honoured** — this is
   **DEFECT 1 above, confirmed by live execution**, not just by reading the
   parser. `image.py` would raise `TypeError` on this exact config.

Also confirmed: `--current` lists config-declared tools **whether or not they
are installed** (every entry above came back with `"installed": false`), so the
command answers "what does this config declare *here*", which is exactly the
smoke test's question.

### ⚠️ TRAP — `mise config ls` is UNFILTERED; only `mise ls --current` is filtered

Same probe, same directory, same binary:

```
$ mise config ls -J
[ { "path": ".../probe/mise.toml",
    "tools": ["npm:cowsay","npm:left-pad","npm:is-odd","npm:is-even",
              "npm:rimraf","npm:chalk","npm:uuid","npm:dedent","npm:ms"] }, … ]
```

**All NINE** — including every entry `os=` excludes (`cowsay`/linux,
`is-even`/wrong arch, `chalk`/empty list, `dedent`/wrong case).
`mise config ls` reports the **raw declaration**; `mise ls --current` reports
the **resolved set**. Reaching for `config ls` to build an expected set would
silently reintroduce the exact #845 defect — a set naming a tool the image
correctly does not have.

Likewise `mise ls -J` **without** `--current` returned the whole host's
installed tools (`actionlint`, `age`, `aqua:…` — nothing to do with the probe
config). `--current` is load-bearing, not cosmetic.

| Command | os-filtered? | Scope |
|---|---|---|
| `mise ls --current -J` | **YES** | active config only ✅ |
| `mise ls --current --missing -J` | **YES** | active config, not-installed ✅ |
| `mise config ls -J` | **NO** | raw per-file declarations ❌ |
| `mise ls -J` | n/a | everything mise knows about, incl. global ❌ |

### The JSON shape

```json
{
  "npm:is-odd": [
    {
      "version": "3.0.1",
      "requested_version": "3.0.1",
      "install_path": "/Users/…/installs/npm-is-odd/3.0.1",
      "source": { "type": "mise.toml", "path": "/…/probe/mise.toml" },
      "installed": false,
      "active": false
    }
  ]
}
```

Note what this hands you, free:

- **the key carries the backend prefix verbatim** (`npm:is-odd`, `conda:gxx`) —
  `parse_declared_tools`' docstring already states this is what makes the
  comparison exact, and it is the same key space;
- **`requested_version`** — the declared string (`"latest"` stays `"latest"`);
- **`version`** — the resolved concrete version;
- **`installed`** / **`active`** — booleans;
- **`source.path`** — which config file contributed the entry, so the base /
  shared / runtime tiers are distinguishable in one call.

### The exact command for Q4

```bash
mise ls --current --json
```

…run **inside the container** (and, for the runtime tier, under the same
`MISE_ENV=runtime` the image bakes). That single invocation returns the
post-`os=`-filter, post-merge, per-tier tool set with requested versions —
which is precisely what `resolve_declared_tools(arch=…)` + `parse_declared_tools`
reconstruct today by re-implementing mise's platform logic on the macOS host.

Flags worth knowing for shaping it:
- `--current` — only what the active config declares (`docs/cli/ls.md:26`).
- `--installed` / `-i` — only what is actually installed (`ls.md:32`).
- `--missing` / `-m` — declared but not installed (`ls.md:44`).
- `--all-sources` — every tracked config source (`ls.md:47`).
- `--json` / `-J` (`ls.md:38`); `--no-header` for the human form.

**`--missing` is the sharper tool for the smoke's real question.** The smoke
asserts "the image contains what the config declares". Rather than building an
expected set at all, ask mise for the *discrepancy* directly: an empty
`mise ls --current --missing --json` in the container IS that assertion, already
os-filtered, with no expected-set construction anywhere.

---

## Q4 verdict — can config + mise replace the Python?

**Yes for the platform-prediction half, which is the half that produced the
defects. Not entirely for the rest.**

### What can be deleted outright

Everything in `image.py` that re-implements mise's platform semantics on the
host:

- `_normalize_tool_os` (`image.py:129-143`)
- `_normalize_tool_arch` (`image.py:146-170`)
- `_tool_os_supported` (`image.py:173-224`)
- the `arch` parameter threaded through `parse_declared_tools`
  (`image.py:227-249`) and `resolve_declared_tools` (`image.py:252+`) purely to
  feed that filter

…because a single in-container `mise ls --current --json` reports the answer
those functions try to predict. This is the exact "five places predicted what
mise would do" problem #845 exists to stop, and it is the operator's instinct in
U46 being correct.

The `os = ["linux/arm64"]` scoping on `conda:gxx`
(`.devcontainer/mise-system.toml:68`) **stays** — it is the config-first
declaration doing real work. What goes is the host-side mirror of it.

### ⭐ THE DECISIVE FINDING — the smoke script ALREADY asks mise, in-container

`python/src/dotfiles_setup/image.py:445-459` (`_TIER1_MISE_LS_TOOLSET`) already
runs this **inside the image**:

```bash
installed_tool_requests=$(mise ls --json \
  | jq -r --arg cfg "$MISE_CFG" --arg shared "$MISE_SHARED_CFG" \
       --arg runtime "$MISE_RUNTIME_CFG" '
  to_entries[] | .key as $k | .value[]
  | select((.source.path == $cfg or .source.path == $shared
            or .source.path == $runtime) and .installed == true)
  | "\($k)\t\(.requested_version)"' | LC_ALL=C sort -u)
if ! diff <(printf '%s\n' "$EXPECTED_TOOL_REQUESTS") \
          <(printf '%s\n' "$installed_tool_requests"); then …
```

So **one side of the diff already comes from mise**. Only
`$EXPECTED_TOOL_REQUESTS` — injected from the macOS host by
`parse_declared_tools(arch=…)` — is predicted. That asymmetry is the whole bug
class.

**And I probed that mise's side of it is already os-filtered.** Same probe
config, same `mise ls --json`-plus-`source.path` filter the smoke uses:

```
$ mise ls --json | jq -r --arg cfg "$CFG" 'to_entries[] | .key as $k | .value[]
    | select(.source.path == $cfg) | "\($k)\t\(.requested_version)\tinstalled=\(.installed)"'
npm:is-odd    3.0.1   installed=false
npm:left-pad  1.3.0   installed=false
npm:ms        2.1.3   installed=false
npm:rimraf    5.0.0   installed=false
npm:uuid      9.0.0   installed=false
```

**Five, not nine** — `cowsay`/`is-even`/`chalk`/`dedent` are gone. The very call
the smoke already makes returns the os-filtered declared set, keyed exactly as
`parse_declared_tools` keys it (backend prefix verbatim), carrying
`requested_version` exactly as the diff compares it.

**Therefore the expected set does not need to be computed at all.** Both sides
of the existing diff can be derived from the *same single JSON document*:

- **declared** = entries whose `source.path` is one of the three config files
  (mise has already applied `os=`),
- **installed** = that same subset filtered by `.installed == true`.

Diff those two. The assertion is unchanged and still bidirectional
(declared-not-installed *and* installed-not-declared/version-drift), but there
is no host-side prediction, no `arch` parameter, and no normalisation table
anywhere. The three-tier merge is also already handled — the existing jq names
all three config paths in one call.

A further simplification, if the bidirectional property can be relaxed:
`mise ls --current --missing --json` filtered to those three paths must be
**empty**. Probed above; it is os-filtered too.

### What still needs code, and precisely why

1. **Something must invoke mise in the container and diff two sets.** That is a
   subprocess call plus a set comparison — small, and it contains no platform
   logic. It cannot be pure config: TOML cannot run a command.
2. **The tier split.** The image merges three files across two `MISE_ENV`
   values (base+shared at default, runtime under `MISE_ENV=runtime`, per
   `.devcontainer/AGENTS.md`). One `mise ls` call sees one env; covering both
   tiers is two calls whose results are unioned. Still no platform logic —
   `source.path` in the JSON even labels which file each entry came from.
3. **Non-mise content.** `[bootstrap.packages]` (66 apt pins) is *not* in
   `mise ls` output at all — it has its own command,
   `mise bootstrap packages status --json` (already used as the build-time gate,
   `.devcontainer/mise-system.toml:115-117`). Two commands, two domains.

So the honest shape is: **the expected set stops being computed and starts being
*asked for*.** The remaining Python is a thin invoke-and-compare wrapper with no
knowledge of architectures, OS names, or normalisation tables.

---

## Q5. What CANNOT be expressed in config (state plainly — do not over-promise)

1. **The backend's own platform restriction is invisible to the config.**
   `is_os_supported()` falls through to `self.ba().is_os_supported()`
   (`tool_request.rs:483` → `backend_arg.rs:703-710`), which consults the
   **registry** (`rt.is_supported_os()`). A tool can be excluded on a platform
   with *nothing in the TOML saying so*. No host-side parser can ever be
   correct here — which is an argument *for* asking mise, not an argument
   against config-first.

2. **`os` alone cannot express a conditional VERSION** — it gates whether an
   entry applies, full stop. But a **Tera template on the version value CAN**
   (`"{% if arch() == 'arm64' %}16.2.0{% else %}15.0{% endif %}"`, probed
   working above). Two ways to say it; `os` with two disjoint entries is the
   more legible, and keeps the version a plain string a lockfile and Renovate
   can see. A templated version is opaque to both — worth weighing before
   reaching for it.

2b. **You cannot conditionally include or exclude a KEY.** *"The `mise.toml`
   file itself is not templated and must be valid toml"* (`docs/templates.md:11`)
   — templates render VALUES only. `os` is the sole mechanism for
   entry-level presence, and its array elements are not themselves templatable
   (control-armed above).

3. **`os` cannot express "install X *instead of* Y".** The arm64-gets-`conda:gxx`
   / amd64-gets-`gcc-latest` asymmetry is expressible only as two independently
   scoped entries — and `gcc-latest` is not a mise tool at all (it is a deb
   fetched in the Dockerfile, per `platform_target.GCC_LATEST_ARCHES`), so that
   half of the asymmetry lives outside mise's reach entirely and stays in code.

4. **No conditional/templated config.** mise merges config files; it does not
   evaluate conditionals inside `[tools]`. The available mechanisms are
   file merging (`conf.d/*.toml`), `MISE_ENV` profiles (`config.<env>.toml`) and
   per-entry `os` — there is no `if arch == …` construct.

5. **`mise ls` reports the platform it RUNS ON.** It cannot answer "what would
   this config resolve to on the *other* architecture" — that is what
   `lockfile_platforms` + `mise.lock` are for. So a **host-side** check of arm64
   expectations remains impossible by construction; the check must run in the
   container (which the operator explicitly said is fine and preferred).

6. **`[bootstrap.packages]` is a separate domain** with inverted empty-list
   semantics (§Defect 2). Config-first there means `mise bootstrap packages
   status --json`, not `mise ls`.

---

## Version currency — when each feature landed vs. what we pin

Per `CHANGELOG.md` in the mise tree:

| Feature | Landed in | PR | CHANGELOG line |
|---|---|---|---|
| `os` field on `[tools]` (OS-only) | **2025.8.8** | [#5947](https://github.com/jdx/mise/pull/5947) | `:9036`, under heading `:9032` |
| `os/arch` compound syntax | **2026.4.12** | [#9088](https://github.com/jdx/mise/pull/9088) | `:4492`, under heading `:4485` |

This repo pins **2026.8.14** (`.devcontainer/Dockerfile:115`), which is well
past both. **Nothing here is a "wait for a release" item — both features are
available in the version we already run.**

### Closing the KB-clone drift (§0)

The offline clone is 2026.8.10; we run 2026.8.14. I re-checked the delta live:

```
$ gh api repos/jdx/mise/compare/v2026.8.10...v2026.8.14 --jq '.files[].filename' \
    | grep -E "tool_request|tool_version_options|toolset|backend_arg|system/mod|cli/ls"
docs/cli/ls.md
docs/cli/ls-remote.md
```

300 files changed across the four releases; **not one of the source files this
report's claims rest on** (`src/toolset/tool_request.rs`,
`src/toolset/tool_version_options.rs`, `src/cli/args/backend_arg.rs`,
`src/system/mod.rs`, `src/cli/ls.rs`) appears. The only matches are two
generated CLI doc pages.

**Control arm:** that grep returned two non-empty results, so it is not a blind
probe — the absence of the source files is a real negative, not a broken
pattern.

And independently: the live probe in Q3 ran on the **actual 2026.8.14 binary**,
so the behavioural claims do not depend on the 8.10 source read at all. The
source read explains *why*; the probe proves *that*.



---

## What I verified about this repo (vs. what the brief told me)

The brief states five places predicted mise's behaviour. What I independently
confirmed by grep:

- The platform-prediction logic is **centralised in `image.py`**:
  `_normalize_tool_os` (`:129`), `_normalize_tool_arch` (`:146`),
  `_tool_os_supported` (`:173`), filtered in `parse_declared_tools` (`:248`).
- The `arch` parameter is threaded to **7 call sites**: `image.py:265, 269, 275`
  (the three config tiers), `:1085`, `:2059`, `:2143`, `:2173`.
- Consumed by the smoke-script generator at `image.py:441` as
  `$EXPECTED_TOOL_REQUESTS`, diffed at `:453`.
- Tests: `tests/test_image_smoke.py` is the only test file referencing them.

So the deletion surface is one module's worth of helpers plus a parameter
threaded through seven sites — not five scattered mirrors. (I did not attempt to
locate the historical five; the brief's framing may predate the consolidation.)

## Probe artifacts (reproducible)

- `scratchpad/probe/mise.toml` — the 9-entry discrimination matrix, `probe/ls.json`
  its output.
- `scratchpad/probe2/mise.toml` — the templating probes and their control arm.

Reproduce with:
```bash
cd <probe dir> && mise trust ./mise.toml
MISE_GLOBAL_CONFIG_FILE=./empty-global.toml mise ls --current -J | jq -r 'keys[]'
```
(The `MISE_GLOBAL_CONFIG_FILE` neutralisation is required — without it the
user-global config's ~100 tools drown the result. `mise trust` is required or
mise exits 1 without listing anything.)

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — primary source and docs for the `os`
  tool attribute, `is_os_supported`, `parse_string_or_array`, `mise ls`,
  templating, and the CHANGELOG version history; offline clone at
  `knowledge-base/sources/mise/`, plus live `gh api` calls for the
  v2026.8.10…v2026.8.14 delta.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo
  under study: `.devcontainer/mise-system.toml`, `python/src/dotfiles_setup/image.py`,
  `python/src/dotfiles_setup/platform_target.py`.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) —
  offline source corpus; `sources/mise.manifest` is where the version-pin drift
  was found.
- [RobertDeRose](https://github.com/jdx/mise/pull/9088) / mise PR #9088 — the
  os/arch compound-syntax feature; mise PR #5947 — the original `os` field docs.
