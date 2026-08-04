# fnox export / exec / activate surface + refusal semantics

**Agent:** fnox-export-exec · **Date:** 2026-08-03 · **Local version:** fnox 1.32.0
**Status:** COMPLETE.

## TL;DR for the entrypoint decision

1. **Profile selection is unverifiable at the call site.** An unknown or invalid
   `-P` silently yields the top-level secret set at rc=0 — **always**, not only
   when no profiles are declared (source + live positive control, Q4a). No
   strictness flag covers it; `--if-missing error` and `fnox check` both return
   0 on a typo'd profile. **A caller must validate against `fnox profiles`.**
2. **Default resolution policy is fail-open** (`if_missing = "warn"`): an
   unreachable provider or a deleted remote value ⇒ warning, rc=0, variable
   unset. Set `--if-missing error` (or top-level `if_missing = "error"`) or the
   entrypoint cannot tell "resolved" from "skipped".
3. **`fnox export -f env|shell|json|yaml|toml` is the machine-readable surface**
   (`--all` needed for `env=false`/`"exec"` secrets). There is **no `fnox env`**.
4. **mise integration exists but upstream says don't use it** — the recommended
   channels are shell inheritance via `activate`, or `fnox exec` inside a task.
   No `_.file` output is documented.
5. **No redaction on `exec`/`export` output** — redaction is MCP-, proxy-,
   `ci-redact`- and `scan`-scoped only. No mise-style `--redacted`.
6. **The daemon cache does not invalidate on remote rotation** — only on config/
   env change, `daemon clear`/`stop`, or idle timeout (default example: 8h).


Primary sources: `github.com/jdx/fnox` (source + `docs/` + CHANGELOG), local
`fnox <cmd> --help` (authoritative for 1.32.0), `https://fnox.jdx.dev/**`.

⚠️ No `fnox get` was ever run. No secret value printed. The user's real
`~/.config/fnox/config.toml` was not modified.

---

## Q1. The export surface

**There is no `fnox env` subcommand.** `fnox env --help` → `error: unrecognized
subcommand 'env'`, rc=2 (local 1.32.0). The four surfaces are:

| Command | What it does |
|---|---|
| `fnox activate [SHELL]` | *Prints* shell activation code (bash/zsh/fish/nu/pwsh) to stdout; you `eval` it. Does not itself load secrets. |
| `fnox exec [-- CMD]` | Resolves secrets, injects as env vars, spawns CMD. `--replace` execs in fnox's own PID (signals, no leases, drops ambient `FNOX_AGE_KEY`/`FNOX_AGE_KEY_FILE`). |
| `fnox export -f <fmt>` | **The machine-readable surface.** `--format env\|shell\|json\|yaml\|toml`, `-o FILE`, `--header`, `--all`, `-n/--dry-run`. |
| `fnox proxy {rules,run}` | Destination-scoped credential brokering (Q3). |
| `fnox hook-env` | Internal command the activate hooks call; `-s/--shell`. |

`export` **is** a dotenv/JSON emitter: `-f env` gives `KEY=value`, `-f shell`
gives `export KEY=value`, plus `json`/`yaml`/`toml` — any of which another tool
can consume. ⚠️ `--all` is needed to include `env = false` / `env = "exec"`
secrets, which are **excluded by default** (`fnox export --help`, 1.32.0).

### What `activate` installs

Source: `src/shell/zsh.rs:7-72`. `fnox activate zsh` emits, to stdout:

1. `export FNOX_SHELL=zsh`
2. A **`fnox()` shell function** wrapping the real binary. It exists so that
   `fnox deactivate` and `fnox shell` are `eval`'d rather than run in a child
   (`zsh.rs:26-28`); every other subcommand is exec'd plainly. ✅ Verified live
   on this host — `type fnox` returns exactly this function, so activation is
   in effect in this shell.
3. `_fnox_hook()` → `eval "$(<exe> hook-env -s zsh)"`, wrapped in
   `trap -- '' SIGINT` / `trap - SIGINT` (`zsh.rs:41-47`).
4. Registration of `_fnox_hook` into **both** `precmd_functions` **and**
   `chpwd_functions` (`zsh.rs:50-69`), each guarded against double-insert.

⚠️ **`precmd` means the hook runs before EVERY PROMPT, not only on `cd`.** This
is the mechanism behind the already-recorded incident that a hung `doppler` CLI
wedges every shell prompt (`secrets-out-of-the-shell-env.md`): `hook-env` is on
the interactive critical path, and `--if-missing`/provider latency is paid there.
`--no-hook-env` suppresses items 3-4 (leaving only the wrapper) — it is
documented "for testing".

`deactivate` emits the inverse: it filters `_fnox_hook` out of both arrays
(`zsh.rs:76-80`).

## Q2. How mise would consume fnox

⚠️ **Correction to the brief's premise.** fnox's side documents a *real* mise
env plugin — it is not "no integration", it is an integration fnox tells you not
to use. `docs/guide/mise-integration.md:7-11`:

> ::: warning Experimental plugin
> We do not recommend using fnox through the
> [`jdx/mise-env-fnox`](https://github.com/jdx/mise-env-fnox) env plugin. It is
> an incomplete experiment and does not track every fnox feature.

The plugin wires in as `[env] _.fnox-env = { tools = true, profile = "..." }`
(`mise-integration.md:61-63`), i.e. a mise **env plugin**, *not* `_.file`. It
requires `tools = true` so it runs after mise puts the fnox binary on PATH
(`:65-68`). Its own feature table concedes "Full fnox feature support: **No**"
(`:183`).

**The recommended channels are exactly two** (`mise-integration.md:3-5`, `:185`):

1. **Shell integration** — `eval "$(fnox activate bash)"`; mise picks the vars up
   as ordinary inherited shell vars. This is the shell-inheritance channel.
2. **`fnox exec` inside a mise task** — `run = "fnox exec -- npm run dev"`
   (`:36-41`). fnox keeps resolution, "so options such as `env = false`,
   `as_file`, leases, profiles ... all work the same" (`:43-45`).

There is **no `_.file`-compatible output documented for mise**. `fnox export -f
env` produces a dotenv file that mise's `[env] _.file` could read, but nothing in
fnox's docs proposes that pairing, and it would write plaintext secrets to disk.

**Control arm (required by `probes-need-a-control-arm.md`):** the same grep
method that returned the `_.file` absence returns hits for a term known present.

```
$ grep -rn '_\.file' docs/ src/ crates/     → 0 hits
$ grep -rln 'mise'    docs/ src/ crates/    → 15 files   (control: discriminates)
$ grep -rn '_\.fnox-env' docs/              → 7 hits     (control: the plugin form IS found)
```

So the `_.file` zero is a real negative, not a blind probe.

## Q3. `fnox proxy`

Source: `docs/guide/proxy.md`, `src/proxy.rs`. Two subcommands: `proxy rules`
(show effective rules, **without resolving secrets** — `proxy.md:37-41`) and
`proxy run -- CMD`.

**Design intent** (`proxy.md:3-8`): the child gets *placeholders*, never real
values; fnox substitutes the real credential only into approved HTTPS requests.
Aimed explicitly at "AI agents and other untrusted or highly automated programs".

`[[proxy.rules]]` fields (`proxy.md:25-31`): `secret`, `domain`, `header`,
`methods`, `paths` (glob), optional `placeholder` (else a unique per-session one
is generated — useful when an SDK validates credential format, `:34-35`).
Rules "refer to secrets in the active profile" (`:12`) — so **Q4(a)'s silent
profile fallback applies to the proxy's rule resolution too.**

**Runtime sequence** (`proxy.md:51-63`), verbatim shape:

1. Resolve secrets referenced by proxy rules + the provider auth secrets they
   depend on.
2. Start a **loopback-only HTTPS (CONNECT) proxy with an ephemeral CA**.
3. Pass placeholders + standard proxy/CA env vars to the child.
4. Verify upstream TLS, substitute a placeholder **only** when domain, method,
   path **and** header all match.
5. Replace reflected secret values in response headers/bodies with placeholders
   (`src/proxy.rs:875-884` `redact_values`/`redact_string`/`redact_bytes`).
6. Stop the proxy and delete the public CA file on child exit.

CA private key and real values stay in fnox process memory (`:65`).

**Egress modes** (`:67-80`): `egress = "strict"` is the **default** — destinations
with no rule are **rejected**. `"permissive"` tunnels unmatched destinations
without inspection or injection. Strict is recommended for agents.

⚠️ **Documented limits** (`:82-93`) that decide whether this is usable as an
entrypoint: header-only substitution; `http://` rejected; matched destinations
must be **HTTPS on port 443**; HTTP/1.1 only; **chunked request bodies rejected**
(`Content-Length` required); 10 MiB request/response cap; **domains are exact —
no wildcards**; client must honor standard proxy/CA env vars.

⚠️ **Stated non-guarantee** (`:101-105`): "The proxy is **not yet an
operating-system sandbox**. A determined process running as the same user may
bypass proxy environment variables, read accessible fnox configuration or
provider state, or **invoke fnox directly**." Upstream's own advice is to run
untrusted agents in a container/VM. Under this repo's `env = true` posture the
parent shell already holds all 50 credentials, so the proxy confines nothing it
inherits — it is only meaningful for a child launched from a *clean* env.

Auditing (`audit = true`) logs method, domain, path and injected secret **names**
through fnox tracing, and "never logs request headers, bodies, or secret values"
(`:107-108`).

**UNVERIFIED:** no live request was made through the proxy in this run either —
I did not start `proxy run`, since doing so would resolve real credentials into
a live broker on this host. The above is design-from-source/docs, as briefed.

## Q4. Refusal semantics per command

### (a) Unknown profile → SILENTLY IGNORED, ALWAYS. Root cause found.

The prior session's measurement (`fnox exec -P <nonexistent>` → 50 secrets,
rc=0, zero stderr) is **fully explained by source, and the answer is the worse
of the two options the brief posed: the profile flag is ignored ALWAYS, not
merely when no profiles are declared.**

`crates/fnox-core/src/config.rs:1440-1444` — the entire profile overlay:

```rust
for profile in profiles.iter().filter(|p| *p != "default") {
    if let Some(profile_config) = self.profiles.get(profile) {
        secrets.extend(profile_config.secrets.clone());
    }
}
```

`self.profiles.get(profile)` returns `None` for an unknown name, the `if let`
does not fire, and **there is no `else` branch** — no error, no warning, no
counter. The loop is unconditional over whatever names were passed; whether or
not *other* profiles are declared is never consulted. The base map was already
set at `:1434-1438` to `self.secrets.clone()` (the top-level secrets), because
`no_defaults` is false by default. Hence: full top-level set, zero overlay, rc=0.

This is **structural, not a config artifact of this host.** A typo'd `-P`
(`prodution`, `dev_personal` vs `dev-personal`) silently yields the top-level
secret set on every command that takes `-P`.

Two further silent degradations on the same path:

- **Invalid profile names are dropped, then the list falls back to `default`.**
  `normalize_profiles` (`config.rs:1335-1347`) filters on
  `env::is_valid_profile_name` and then: `if profiles.is_empty() { vec!["default"] }`.
  So `-P 'bad/name'` → the name is discarded → active profile becomes `default`.
  No diagnostic.
- **`--no-defaults` changes the failure shape, not the refusal.** With
  `no_defaults` + a non-default profile, the base map starts empty
  (`:1434-1438`), so an unknown profile yields **zero** secrets — still rc=0,
  still silent. Safer (no wrong secrets) but equally unannounced.

**No command validates profile existence anywhere in the codebase.** There is no
`UnknownProfile` variant in `crates/fnox-core/src/error.rs` (its profile-related
errors at `:123-235` are all *secret*- or *provider*-not-found-**in**-a-profile,
which presuppose the profile). Control-armed grep:

```
$ grep -rn "Unknown profile|profile not found|UnknownProfile" src/ crates/   → 0 relevant hits
$ grep -rn "Multiple profiles are active" src/ crates/                       → 1  (control: config.rs:1377, discriminates)
```

The only profile-shaped refusal in the whole tree is the **write** path:
`resolve_write_profile` (`config.rs:1363-1381`) errors on an invalid
`--write-profile` name or on multiple active profiles without one. Read paths
(`exec`, `export`, `activate`/`hook-env`, `proxy`) have no equivalent.

⇒ **For a fnox-only entrypoint this is the primary unsafe-failure surface:
profile selection is unverifiable at the call site.** The only way to detect a
typo'd profile is to compare the resolved *name set* against an expectation
(`fnox list -P <p>` names, or `fnox profiles` for what is declared) — fnox will
never tell you.

### (b) Unreachable provider / (c) declared secret whose remote value is missing

Governed by **`if_missing`, whose default is `warn` — i.e. continue, rc=0.**
`docs/guide/missing-secrets.md:6-9`:

> - **`error`** - Fail the command if a secret cannot be resolved (strictest)
> - **`warn`** - Print a warning and continue (default)
> - **`ignore`** - Silently skip missing secrets

Precedence, highest first (`missing-secrets.md:11-20`): CLI `--if-missing` →
`FNOX_IF_MISSING` → per-secret `if_missing` → top-level config `if_missing` →
`FNOX_IF_MISSING_DEFAULT` → built-in `warn`.

⚠️ **The default is fail-open for every read command.** A provider that is down,
or a secret deleted upstream, produces a stderr warning and a **successful exit
with that variable absent** — the consumer then sees an unset var, which is the
"anonymous tier" trap already recorded in `secrets-out-of-the-shell-env.md`
rule 5. A fnox-only entrypoint that does not pass `--if-missing error` (or set
`if_missing = "error"` top-level) cannot distinguish "resolved" from "skipped".

`--if-missing` is a **global** flag present on `exec`, `export`, `activate`,
`hook-env`, `ci-redact` and `proxy` alike (verified in each `--help`, 1.32.0),
so the strict mode is available uniformly.

**An unreachable provider is governed by the same chain, not by a separate
error path.** `handle_provider_error` (`secret_resolver.rs:348-379`) takes the
resolved `IfMissing` and returns `Some(err)` only for `Error`; `Warn` logs and
returns `None`, `Ignore` returns `None` silently. It is called on the provider
failure paths at `:1119` and `:1157`. So "provider down" and "secret absent"
collapse into one policy — **default `warn` ⇒ continue, rc=0, variable unset.**

### Live probe (fixture-armed, control-armed) — 1.32.0 on this host

Isolated fixture in a scratchpad dir, `provider = "plain"`. ⚠️ **First fixture
was rigged** — I declared `provider = "plain"` without a `[providers.plain]`
block, so both canaries silently vanished and every arm returned the same 50
names. Rebuilt with the provider declared. (The failed fixture was itself an
unplanned live demo of (b): *"Provider 'plain' not configured in profile
'default'"* → **WARN, rc=0**.) `fnox config-files` confirms both the fixture and
the user's global `~/.config/fnox/config.toml` load — hence the +50 baseline.
Only NAMES and counts were ever printed; no value, no `fnox get`.

**Arm A — profile handling.** The fixture declares a real profile (`real`), so
it *can* distinguish "flag ignored always" from "flag ignored when no profiles
exist":

| Invocation | rc | names | canaries |
|---|---|---|---|
| `export` (baseline) | 0 | 51 | `TOPLEVEL_CANARY` |
| `export -P real` **← positive control** | 0 | **52** | `TOPLEVEL_CANARY REAL_CANARY` |
| `export -P nope` | **0** | 51 | `TOPLEVEL_CANARY` only |
| `export -P real,nope` | 0 | 52 | both (unknown name in a stack is dropped) |
| `export -P nope --no-defaults` | **0** | **0** | none |
| `export -P 'bad/name'` | **0** | 51 | falls back to `default` |

The positive control proves `-P` works when the profile exists ⇒ the `-P nope`
result is a real silent fallback, not a dead flag.
**⇒ The profile flag is ignored ALWAYS, exactly as the source predicts — not
merely when no profiles are declared.** Source and probe agree.

**Arm B — `if_missing`, both directions:**

| Invocation | rc | names | stderr lines |
|---|---|---|---|
| `export` (default) | 0 | 51 | 2 |
| `export --if-missing warn` | 0 | 51 | 2 (identical to default ⇒ default *is* `warn`) |
| `export --if-missing ignore` | 0 | 51 | **0** |
| `export --if-missing error` | **1** | 0 | 12 |
| `exec --if-missing error -- true` | **1** | — | — |
| `exec -- true` (default) | **0** | — | — |

Both directions fire ⇒ the probe discriminates.

### ⚠️ The composite finding: strict mode does NOT cover the profile gap

| Invocation | rc |
|---|---|
| `export -P real --if-missing error` | 0 (52 names) |
| **`export -P nope --if-missing error`** | **0** (51 names) |
| `check -P real` | 0 |
| **`check -P nope`** | **0** |

**`--if-missing error` cannot catch a typo'd profile, and neither can `fnox
check`.** The mechanism is exactly the source: an unknown profile's secrets are
never *added* to the map, so there is nothing "missing" for the policy to judge —
the two failure modes are orthogonal, and fnox ships a lever for only one.

**The only detector is `fnox profiles`**, which enumerates declared profiles with
counts (`default (51 secrets)` / `real (52 secrets)` in the fixture). A
fnox-only entrypoint must validate its profile name against that list itself —
**this is the one guard rail a caller has to build, because fnox has none.**

## Q5. Redaction — **there is NO `--redacted` equivalent to mise's**

Redaction in fnox 1.32.0 exists in exactly **four** places, none of which covers
`exec`/`export`/`get` output:

| Site | Scope |
|---|---|
| `src/mcp_server.rs:510-543` | `fnox mcp`'s `exec` tool: replaces secret values with `[REDACTED]` in the child's stdout/stderr before returning to the agent. Aho-Corasick, longest-match-wins, skips empty/short values, and **refuses to return output at all if the filter fails to build** (`:537`). Default **on** (`config.rs:489-491`, `redact_output.unwrap_or(true)`). |
| `src/proxy.rs:875-884` | Proxy step 5: replaces *reflected* secret values in upstream response headers/bodies with placeholders. |
| `src/commands/ci_redact.rs` | `fnox ci-redact` — emits **GitHub Actions `::add-mask::`** directives so the CI runner masks values in logs. Errors on a secret containing newlines, which "cannot be fully redacted in CI logs" (`:35`). |
| `src/commands/scan.rs:76,294` | `fnox scan`'s findings carry a `redacted` rendering of each match. |

**Control-armed grep** (my first attempt used a broken control that also returned
0; redone):

```
$ grep -rni "redacted" src/ crates/ docs/   → 19 hits, exhaustively the four sites above
$ grep -rn  "if_missing" src/ crates/       → 111   (control: discriminates)
$ grep -rn  "no_daemon"  src/ crates/       →   4   (control: discriminates)
```

⇒ `fnox exec -- printenv` and `fnox export` **print values in full, by design** —
`export` is a value-emitting command. The `redact_output` config key is a field of
**`McpConfig`** (`config.rs:350-353`), not a global. **`fnox ci-redact` is the only
lever for log safety outside MCP, and it delegates masking to the CI runner.**
Note `ci-redact` is **not listed in `fnox --help`** (hidden), but is live and has
`--help` (verified locally) and is listed among daemon-backed read commands
(`docs/guide/daemon.md:50`).

## Q6. Caching

Two distinct caches, plus a third that is not fnox's.

**1. The per-user daemon (`docs/guide/daemon.md`) — opt-in, memory-only.**
"fnox does not use it unless you enable it in config or set `FNOX_DAEMON=on`"
(`:5`). Enabled via `[daemon] enabled = true`, `idle_timeout` (`:11-15`).

- Applies to read commands: `exec`, `get`, `hook-env`, `export`, `list --values`,
  `check`, `tui`, `mcp`, `ci-redact` (`:40-50`). Mutating/admin commands
  (`sync`, `reencrypt`, `edit`, `set`, `remove`, `provider`, `lease create`)
  always resolve directly (`:52`).
- **"The daemon cache is memory-only. Secret values are not written to disk by
  the daemon."** (`:56`)
- **Invalidation** (`:58-63`) — discarded when: `fnox daemon clear`;
  `fnox daemon stop`; idle-timeout exit; or **"Config files, profile settings,
  provider references, post-processing options, or relevant `FNOX_*` and provider
  environment variables change"**.

⚠️ **The rotation hazard is real and is the gap in that list.** Invalidation keys
on *fnox-side inputs* — config, profile, provider refs, env. **A value rotated
at the remote provider changes none of those**, so a running daemon keeps serving
the rotated-away credential until `daemon clear`/`stop` or the idle timeout
expires. `idle_timeout = "8h"` in upstream's own example (`:14`) is therefore the
worst-case staleness window. Mitigations upstream provides: `daemon_cache = false`
per-secret (`:71-76`) or per-provider (`:78-85`), and `--no-daemon` per
invocation. `fnox check` deliberately **does not reuse cached values** — "It still
contacts providers so it can validate the current state" (`:65`), which makes
`check` the correct post-rotation probe.
Per-invocation opt-out: `fnox --no-daemon get X` (`:29`); session:
`FNOX_DAEMON=off` (`:35`).

**2. `fnox sync` — an encrypted local cache that DOES survive restarts.**
`daemon.md:97-101` contrasts them: use the daemon for fast in-session reads;
use sync "when you want an encrypted local cache that survives restarts and can
work offline". A synced value is a **materialised copy** and is stale until
re-synced — after a rotation, `fnox sync` must be re-run. (This is the mechanism
behind the already-known "every add/remove churns all 49 `sync` ciphertexts".)

**3. `MISE_ENV_CACHE`** is mise's, not fnox's — it caches whatever the env plugin
produced (`mise-integration.md:160-172`), invalidated by `mise cache clear` or
`mise exec --fresh-env` (`:209-219`). Already recorded on this host as able to
"serve a dead name in ONE directory long after the config is restored".

**Security note:** daemon transport is a **Unix domain socket, never TCP**, in a
user-owned runtime dir with strict permissions, with bidirectional peer-ownership
verification (`daemon.md:89-95`). Unsupported platforms return a clear error.

## Provenance / upstream status

**A profile also selects a config FILENAME**, a second channel for the same
silent failure: `find_local_config(dir, profiles)` (`config.rs:67`) and
CHANGELOG `#64` ("add support for `fnox.$FNOX_PROFILE.toml` config files") +
`#87` ("respect `--profile`/`-P` CLI flag when loading config files"). An unknown
profile simply means `fnox.<name>.toml` does not exist and nothing extra loads —
again with no diagnostic.

**The fallback is intentional design, not a bug**: CHANGELOG `#21` "add top-level
secret inheritance for profiles". The *inheritance* is deliberate; the silent
acceptance of an **undeclared** profile name is the emergent gap.

**Upstream has no issue tracking this** — `gh search issues --repo jdx/fnox
"profile" --state open` → `[]`, and `"unknown profile"` (all states) → `[]`.
⚠️ Weak evidence: those searches returned empty for *every* query shape I tried,
so I cannot distinguish "no such issue" from "search not indexing this repo".
Treat as **UNVERIFIED**; the source reading and the live probe are the load-
bearing evidence, not the issue search.

**Version alignment:** the cloned tree's `Cargo.toml` is `version = "1.32.0"`,
byte-matching the installed binary, so source claims apply to this host's fnox.

## Not covered / UNVERIFIED

- No live HTTPS request was made through `fnox proxy run` (would resolve real
  credentials into a live broker on this host). Q3 is design-from-source.
- `--replace` exec semantics (PID/signal behaviour, lease interaction) read from
  `--help` only, not exercised.
- Multi-profile overlay *precedence* was confirmed for name-dropping only; I did
  not test conflicting values across a profile stack (would require printing
  values).
- Daemon behaviour is documented-only: the daemon is opt-in and was **not**
  enabled on this host, so no cache-staleness measurement was taken.

## GitHub repos touched

- [jdx/fnox](https://github.com/jdx/fnox) — primary source (`crates/fnox-core/src/config.rs`, `secret_resolver.rs`, `error.rs`, `src/shell/zsh.rs`, `src/proxy.rs`, `src/mcp_server.rs`, `src/commands/`), `docs/guide/*`, `CHANGELOG.md`, issue search
- [jdx/mise-env-fnox](https://github.com/jdx/mise-env-fnox) — the experimental mise env plugin fnox's docs explicitly recommend against (referenced, not cloned)
- [jdx/mise](https://github.com/jdx/mise) — the consuming side of Q2 (referenced via fnox's docs only)
