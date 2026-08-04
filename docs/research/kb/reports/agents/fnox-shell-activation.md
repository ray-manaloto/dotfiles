# fnox shell-activation surface — scoping and cost

**Agent:** fnox-shell-activation research
**Date:** 2026-08-03
**fnox version under test:** 1.32.0 (`/Users/rmanaloto/.local/share/mise/installs/fnox/latest/fnox`)
**Status:** COMPLETE

Goal: determine what replaces `~/.zshrc.d/50-mde-secrets.zsh` (`fnox activate zsh`)
with something this repo owns — scoped if possible, cheap if possible.

---

## Q1 — Can `fnox activate` be scoped?

**NO. `fnox activate` CANNOT be scoped by flag. The flags are accepted and
silently discarded.** This is the single most important finding in this task,
and it is the opposite of the hoped-for answer.

### Root cause (source)

`ActivateCommand` has **exactly two fields** — `shell` and `no_hook_env`:

```rust
// src/commands/activate.rs:5-17
pub struct ActivateCommand {
    /// Shell to generate activation code for (bash, zsh, fish, nu, pwsh)
    #[arg(value_name = "SHELL")]
    pub shell: Option<String>,

    /// Don't automatically invoke hook-env (for testing)
    #[arg(long)]
    pub no_hook_env: bool,
}
```
<https://github.com/jdx/fnox/blob/main/src/commands/activate.rs>

`-P/--profile`, `--no-defaults`, `-c/--config`, `--if-missing`, `--no-daemon`
are **global** clap flags (they appear on every subcommand's `--help`,
including `activate`), but `ActivateCommand` never reads them. It builds
`ActivateOptions { exe, no_hook_env }` — and `ActivateOptions` (`src/shell/mod.rs:29-35`)
carries **only those two fields**. There is nowhere for a profile to go.

The generated zsh hook is a hardcoded format string with no flag interpolation:

```rust
// src/shell/zsh.rs:41-48
_fnox_hook() {{
  trap -- '' SIGINT
  eval "$({exe} hook-env -s zsh)"
  trap - SIGINT
}}
```
<https://github.com/jdx/fnox/blob/main/src/shell/zsh.rs>

`{exe}` is the only substitution. So every per-prompt invocation is bare
`fnox hook-env -s zsh` — default profile, defaults merged, config discovered
by upward search from `$PWD`.

### Empirical confirmation — both arms

fnox 1.32.0, local binary:

| Arm | Command | `hook-env` line emitted |
|---|---|---|
| A (baseline) | `fnox activate zsh` | `eval "$(… fnox hook-env -s zsh)"` |
| B (scoped attempt) | `fnox activate zsh -P shell --no-defaults` | `eval "$(… fnox hook-env -s zsh)"` |
| C (config attempt) | `fnox activate zsh -c /nonexistent/x.toml` | `eval "$(… fnox hook-env -s zsh)"` |

`diff <(arm A) <(arm B)` → **IDENTICAL** (rc=0, zero lines of diff). Arm C is
identical too, and note it does **not error** on a nonexistent config path —
another fail-open.

**CONTROL ARM (this is the important part):** the same `diff` harness against
`fnox activate zsh --no-hook-env` produces a **16-line diff** (the whole
`_fnox_hook` / `precmd_functions` / `chpwd_functions` block is removed). So the
probe *can* detect a difference in activation output — the `IDENTICAL` for
`-P … --no-defaults` is a real negative, not a blind harness.

### The consequence for the replacement file

`fnox activate zsh -P <anything>` is **not a scoping mechanism** — it is
`fnox activate zsh` with extra words. Combined with the already-established
fail-open on an unknown profile, a replacement file written as
`eval "$(fnox activate zsh -P agent --no-defaults)"` would look scoped in
review, pass any "does it run" check, and yield **all 50 secrets**. That is a
silently-wrong config, which is worse than the current file.

### What DOES scope a shell activation

The only lever that reaches the per-prompt `hook-env` is the **environment**,
because the hook inherits it:

- **`FNOX_PROFILE`** — read as the profile default (it is the documented
  fallback in the global `-P` help text: *"default: default, or FNOX_PROFILE
  env var"*), and the docs confirm the hook picks up a change on the next
  prompt: *"fnox detects the change on the next prompt automatically"*
  (`docs/guide/shell-integration.md` § Using Profiles).
  So `export FNOX_PROFILE=agent` **before** the `eval` does scope the hook.
- **`--no-defaults` has NO environment equivalent** — see the flag table in
  Q1b below. This is the gap: you can select a profile shell-wide, but you
  **cannot suppress the top-level secret merge** shell-wide.

Net: a shell-wide *scoped* activation is only **half** achievable. Selecting a
profile: yes, via `FNOX_PROFILE`. Excluding the 50 top-level secrets: **no**,
not through `activate`. To get `--no-defaults` you must be on an `exec`/`get`/
`export` code path, which is the `fnox exec` model, not the shell-activation
model.

### Q1b — which global flags have an env fallback

From `fnox <cmd> --help` (1.32.0), only two globals declare an `[env: …]`
binding:

- `--non-interactive` → `[env: FNOX_NON_INTERACTIVE=]`
- (`--profile` documents `FNOX_PROFILE` in prose, not as a clap `[env:]` tag)

`--no-defaults`, `--no-daemon`, `--if-missing` and `--config` show **no**
`[env:]` tag. `FNOX_CONFIG_DIR` and `FNOX_SHELL_OUTPUT` exist but are separate
knobs, not `--no-defaults`. Marked **UNVERIFIED-NEGATIVE** for
`--no-defaults`: absence of an `[env:]` tag in `--help` is strong but not
proof; a `std::env::var` read elsewhere in the source would not show up there.
Control arm run: the same `--help` scan **does** surface
`FNOX_NON_INTERACTIVE`, so the scan can find an env binding when one exists.

## Q2 — What does `hook-env` do per prompt?

**On an unchanged prompt it short-circuits BEFORE touching any provider.** The
steady-state per-prompt cost is one process spawn plus a handful of `stat()`
calls. It does **not** re-resolve secrets, so a hung provider CLI does **not**
wedge every prompt — but it *does* wedge every `cd` and every new shell (see
"Where the wedge actually is" below).

### The early-exit is the first thing that runs

`HookEnvCommand::run` (`src/commands/hook_env.rs`) does, in order:

1. `Settings::try_get()` — output mode.
2. `shell::get_shell(...)`.
3. **`if hook_env::should_exit_early() { return Ok(()) }`** — returns with
   **no output at all**.
4. Only past that point: `hook_env::find_config()`, then
   `load_secrets_from_config(cli)` → `daemon::resolve_batch(…, Purpose::HookEnv, …)`,
   which is what actually contacts providers.

<https://github.com/jdx/fnox/blob/main/src/commands/hook_env.rs>

So provider resolution is strictly downstream of the early-exit gate.

### What `should_exit_early()` actually costs

```rust
// src/hook_env.rs — should_exit_early()
if has_directory_changed()   { return false }  // env::current_dir() vs PREV_SESSION.dir
if has_config_been_modified(){ return false }  // stat sweep, see below
if has_fnox_env_vars_changed(){ return false } // hash of all FNOX_* vars
true
```
<https://github.com/jdx/fnox/blob/main/src/hook_env.rs>

The three checks, by cost:

| Check | Work done |
|---|---|
| `has_directory_changed` | one `getcwd`, compare to `PREV_SESSION.dir` |
| `has_config_been_modified` | `collect_config_files(cwd)`: **walks cwd up to `/`, and at every level `stat()`s every name in `all_config_filenames(profile)`** (`fnox.toml`, `.fnox.toml`, `fnox.<profile>.toml`, `fnox.local.toml`, …). Then **also `stat()`s the global config** `Config::global_config_path()`. Hashes (path, mtime) pairs with `DefaultHasher`. |
| `has_fnox_env_vars_changed` | iterate `std::env::vars()`, collect `FNOX_*` into a `BTreeMap`, hash |

Plus, lazily on first access, `PREV_SESSION` decodes `__FNOX_SESSION`:
**base64 → miniz inflate → msgpack deserialize** (`src/hook_env.rs`, `decode_session`).

Two consequences worth naming:

- The stat sweep is **O(directory depth × config filename count)** and it runs
  on **every prompt**. In a deep tree that is tens of syscalls per prompt.
  Cheap, but not free, and it grows with `cd` depth.
- **`collect_config_files` stats the GLOBAL config on every prompt.** This is
  the source-level confirmation of the previously-recorded behaviour that fnox
  pulls `~/.config/fnox/config.toml` into every invocation: the global config's
  mtime is part of the change-detection hash, so touching it invalidates every
  shell's session on the next prompt.

### `__FNOX_SESSION` — a second `__MISE_DIFF`-shaped blob, but NOT secret-bearing

`hook_env_output` always appends `__FNOX_SESSION` (`src/shell/mod.rs`,
`hook_env_output`). It is base64(deflate(msgpack(`HookEnvSession`))).

**It does not contain secret values.** The struct stores
`secret_hashes: IndexMap<String, String>` — BLAKE3 **keyed** hashes, with a
per-session random `hash_key`, domain-separated by the secret name
(`hash_secret_with_key`). The doc comment states the intent: *"Hashed with the
session's hash_key to prevent offline dictionary attacks"*.

It **does** contain, in cleartext-after-decode: **every secret NAME**, the cwd,
the config path, and temp-file paths for `as_file` secrets. So it is a
**name-disclosure** blob, not a value-disclosure blob — materially different
from `__MISE_DIFF`, which carries values. A committed `env` dump would leak all
50 credential *names* and the local paths, not the credentials. Worth knowing
for this repo's `no_env_dump` scanner: `__FNOX_SESSION` deserves the same
"don't commit it" treatment, but it is not a rotation event if it leaks.

### Where the wedge actually is

The early exit fails — and a full 50-secret provider resolution runs — in
exactly three situations:

1. **Directory changed.** The hook is registered in `chpwd_functions` *and*
   `precmd_functions`, so **every `cd` triggers a full re-resolve.**
2. **Any config file in the hierarchy, or the global config, changed mtime.**
3. **Any `FNOX_*` env var changed** (including `FNOX_PROFILE`).

Plus an unlisted fourth, which is the expensive one in practice:

4. **Every brand-new shell.** A fresh login shell has no `__FNOX_SESSION`, so
   `PREV_SESSION` is `Default` with `dir: None`; `has_directory_changed()`
   compares `None != Some(cwd)` → **true** → full resolve. So **every new
   terminal, and every shell that does not inherit the parent's
   `__FNOX_SESSION`, pays a complete resolution of all 50 secrets.**

This reconciles the "hung `doppler` hangs every shell prompt" observation with
the early-exit: the hang is not on the *steady-state* prompt, it is on
**shell startup and on every `cd`** — which, in interactive use, is
indistinguishable from "every prompt". The fix framing therefore is not "make
the prompt hook cheaper" (it already is); it is "stop the *startup* and *cd*
paths from contacting a provider at all".

### The per-secret confinement lever that survives

`load_secrets_from_config` filters the resolved set before emitting it:

```rust
// src/commands/hook_env.rs — load_secrets_from_config
// Skip secrets unless their env mode allows shell injection —
// env=false and env="exec" secrets must never appear in shell
// integration output.
if let Some(secret_config) = profile_secrets.get(&key)
    && !secret_config.env_mode().in_shell()
{
    continue;
}
```

So **per-secret `env` mode is the only working scoping mechanism for shell
activation.** It is enforced in the hook-env code path itself, not merely by
convention. Under the current `env = true`-for-all-50 posture this filter
passes everything; it is the lever that would narrow the shell set if that were
ever wanted, and it works *without* any profile plumbing.

## Q3 — Cheaper / non-hook activation mode

### What `--no-hook-env` actually does

It removes the **entire** hook block. Measured diff (`fnox activate zsh` vs
`fnox activate zsh --no-hook-env`, fnox 1.32.0): 16 lines removed — the
`_fnox_hook` function, the `precmd_functions` registration, and the
`chpwd_functions` registration. What survives is only:

```zsh
export FNOX_SHELL=zsh
fnox() { … }        # the wrapper that eval's `deactivate`/`shell`
```

So `--no-hook-env` is **not** a cheaper way to load secrets — it loads **zero**
secrets. It gives you the `fnox` wrapper function and nothing else. The
`(for testing)` in its help text is accurate.

(Aside, low-stakes: the emitted wrapper special-cases `deactivate|shell`, but
`fnox shell` is **not a subcommand in 1.32.0** — `fnox shell --help` →
`error: unrecognized subcommand 'shell'`. Dead branch in the generated code.)

### There IS a once-per-shell mode, and it is the answer to this whole task

`fnox export --format shell` emits exactly the same `export …` lines the hook
emits, and — unlike `activate` — it is a **normal subcommand that honours the
global flags**. Confirmed in the isolated fixture:

| Arm | `fnox export -f shell …` | Output |
|---|---|---|
| default | (no flags) | `FIXTURE_TOP_A`, `FIXTURE_TOP_B` |
| profile | `-P scoped` | `FIXTURE_TOP_A`, `FIXTURE_TOP_B`, `FIXTURE_SCOPED_ONLY` (inheritance) |
| **scoped** | `-P scoped --no-defaults` | **`FIXTURE_SCOPED_ONLY` only** |
| bogus, fail-OPEN | `-P bogus` | `FIXTURE_TOP_A`, `FIXTURE_TOP_B`, rc=0 |
| bogus, fail-CLOSED | `-P bogus --no-defaults` | **nothing**, rc=0 |

Both arms discriminate: the scoped arm drops the two top-level secrets that the
unscoped arm emits, and the bogus arm reproduces the known fail-open.

Two correctness properties I verified rather than assumed, because the whole
recommendation rests on them:

1. **It respects per-secret `env` mode.** A fixture with
   `FX_ENVFALSE = { …, env = false }` and `FX_ENVEXEC = { …, env = "exec" }`
   emitted **neither** through `export -f shell`. Control arm: `FX_PLAIN` and
   `FX_SPACES` in the same file **did** appear, so the probe can see secrets —
   the two omissions are real filtering, not a blind probe. This matters
   because it means `export -f shell` is **not** a confinement regression
   versus `activate`.
2. **It quotes safely.** `FX_SPACES = "has spaces and 'quote' and $DOLLAR"`
   round-tripped through `eval "$(fnox export -f shell)"` **byte-identical**
   (`posix_quote` / `shlex::try_quote`, `src/shell/mod.rs`). Output was
   `export FX_SPACES="has spaces and 'quote' and "'$DOLLAR'` — correct
   concatenated quoting.

**So the once-per-shell, scoped, fail-closed activation is:**

```zsh
eval "$(fnox export --format shell --profile <name> --no-defaults)"
```

No hook. No `precmd_functions`. No `chpwd_functions`. One provider resolution
per shell instead of one per shell **plus one per `cd`**.

What you give up versus `activate`: automatic load/unload as you `cd` between
projects, and pickup of a project-local `fnox.toml`. For a machine whose
credential set is a single global config — which is this host's situation —
that is a feature, not a loss.

## Q4 — Does the daemon make activation cheap?

**It makes the expensive path cheaper; it does nothing for the steady-state
prompt, because that path already does no work.**

- The daemon is **opt-in**: *"The daemon is opt-in. fnox does not use it unless
  you enable it in config or set `FNOX_DAEMON=on`."*
  (`docs/guide/daemon.md`)
- `hook-env` **is** on the daemon-backed list, alongside `exec`, `get`,
  `export`, `list --values`, `check`, `tui`, `mcp`, `ci-redact`
  (`docs/guide/daemon.md` § What Uses It).
- Source confirms the wiring: `load_secrets_from_config` calls
  `crate::daemon::resolve_batch(cli, &config, profile_name, &profile_secrets,
  crate::daemon::Purpose::HookEnv, false)` (`src/commands/hook_env.rs`).

**But `resolve_batch` is only reached after `should_exit_early()` returns
false.** On an unchanged prompt the daemon is never contacted either — there is
no socket round-trip, because there is no resolution at all. So:

| Path | Daemon OFF | Daemon ON |
|---|---|---|
| unchanged prompt | early exit, no resolution | early exit, no resolution (**identical**) |
| `cd` / new shell / config change | full provider resolution (50 secrets, spawns `doppler` etc.) | Unix-socket round-trip to memory cache |

So the daemon's value is precisely on the **shell-startup and `cd`** paths —
which, per Q2, are the paths that actually hurt. Enabling it would convert a
provider round-trip into a same-user Unix-socket read for every new shell after
the first.

Caveats that bear on whether it is the right lever here:

- Cache is **memory-only**, discarded on `daemon clear`/`stop`, idle timeout,
  or *"Config files, profile settings, provider references, post-processing
  options, or relevant `FNOX_*` and provider environment variables change"*
  (`docs/guide/daemon.md` § Cache Behavior). Invalidation keys on fnox-side
  inputs only — it will not notice a rotation performed out-of-band.
- Per-secret / per-provider opt-out exists: `daemon_cache = false`.
- **It does not remove the first resolution.** The very first shell after boot
  still pays the full provider cost, and that is still where a hung `doppler`
  wedges. The daemon narrows the window; it does not close it.

**Measured cost of the warm path** (isolated fixture, fnox 1.32.0, this Mac):

| Measurement | avg over 30 runs |
|---|---|
| `fnox hook-env -s zsh`, warm (early exit, 0 bytes output) | **11.78 ms** |
| same, from a directory 12 levels deeper | **11.65 ms** |
| `fnox --version` (bare process-spawn floor) | **9.57 ms** |

Reading: the early-exit *logic* costs roughly **2 ms**; the other ~9.6 ms is
just starting a Rust binary. The `collect_config_files` stat sweep is
**below the noise floor** — 12 extra directory levels changed nothing
(11.78 vs 11.65 ms is within run-to-run variance, i.e. **not a difference**).

⚠️ **Fixture limitation, stated rather than glossed:** this fixture uses
`default = "…"` values with **no provider**, so it **cannot** measure the cold
path's real cost. Cold measured 12.3 ms here only because there was nothing to
fetch. The real cold path on this host resolves 50 secrets through Doppler /
keychain / age and is orders of magnitude slower. I deliberately did **not**
run a real cold `hook-env` against the live config: it would print 50 secret
values, and it is the exact shape known to hang on a keychain-backed provider.
The real cold cost is therefore **UNVERIFIED** here.

## Q5 — Ordering with mise

**No documented guidance, no known-conflict report — and that absence is
control-armed and structural.** But there is a real structural interaction that
falls out of the source, and this repo has already been bitten by it.

### The absence, and the control arms

- **fnox's docs say nothing about ordering.** `docs/guide/mise-integration.md`
  mentions mise 39 times and never discusses rc-file ordering with
  `mise activate`. Control arm: that same file **does** state a hard ordering-ish
  requirement for the plugin (*"`tools = true` is required so the plugin can
  access the mise-managed fnox binary. Without it, the plugin runs before mise
  tools are added to PATH"*), so the document is fully capable of expressing an
  ordering constraint. It expresses one for the plugin and none for `activate`.
- **`jdx/fnox` has issues DISABLED** (`gh api repos/jdx/fnox` →
  `"has_issues": false`). My first probe, `gh search issues --repo jdx/fnox`,
  returned `[]` — and the control arm exposed it as **blind**: searching
  `daemon`, a term fnox certainly discusses, also returned `[]`. Reported
  absence from an issue search would have been a false negative.
- **Discussions are enabled** (`"has_discussions": true`) and *do*
  discriminate: `daemon` → **5** hits. Against that working probe,
  `precmd` → **0**, `activate order` → **0**, `zshrc order mise` → **0**,
  `FNOX_SHELL conflict` → **0**. So the absence of ordering discussion is a
  **real** negative.
- The nearest real report is discussion
  [#300](https://github.com/jdx/fnox/discussions/300) — *"mise integration not
  working with mise activated and fnox not installed"* — but that is about the
  **`mise-env-fnox` plugin** racing tool installation (`sh: fnox: not found`),
  not about `mise activate` vs `fnox activate` hook ordering.

### The structural interaction (derived from source, not docs)

Both tools prepend into `precmd_functions`. fnox:

```zsh
# src/shell/zsh.rs
precmd_functions=( _fnox_hook ${precmd_functions[@]} )
chpwd_functions=( _fnox_hook ${chpwd_functions[@]} )
```

Because it **prepends**, whichever tool is `eval`'d **last** ends up **first**
in the array and therefore **runs first** each prompt. Ordering in the rc file
is thus load-bearing, and inverted from the intuitive reading.

Three consequences worth acting on:

1. **fnox's resolution order consults the environment.** *"When fnox resolves a
   secret, it checks in this order: 1. Encrypted value … 2. Provider reference
   … **3. Environment variable (if already set in shell)** … 4. Default value.
   First match wins!"* (`docs/guide/how-it-works.md`). So if mise's hook has
   already put a same-named variable into the environment, fnox can resolve to
   **mise's** value. Name collisions between `mise.toml [env]` and fnox secrets
   are silently resolved by whoever ran first.
2. **mise snapshots the environment fnox creates.** This is the already-recorded
   incident behind `.claude/rules/secrets-out-of-the-shell-env.md`: fnox's
   exports were captured into **`__MISE_DIFF`** (zlib+base64), a form no secret
   scanner reads. That capture is an ordering artifact — it happens because
   fnox's exports land inside the window mise is diffing. Any replacement file
   inherits this hazard **unless it stops exporting into the login shell**.
3. **Both are active on this host simultaneously** (`MISE_SHELL` and
   `FNOX_SHELL` both set), so this is live configuration, not a hypothetical.

**Recommendation:** if the replacement keeps a shell-wide load at all, do the
fnox load **once, early, and without a hook** (Q3's `export -f shell` form).
That sidesteps the `precmd` ordering question entirely — there is no fnox
prompt hook to order against mise's.

## Q6 — Recommended production setup per fnox's own docs

fnox's docs offer **three** supported shapes and rank them only indirectly.
Quoting:

- **Shell integration** — `docs/guide/shell-integration.md`:
  > "fnox can automatically load secrets when you `cd` into directories with a
  > `fnox.toml` file." … "Add this to your shell profile: … `eval "$(fnox
  > activate zsh)"`"

- **`fnox exec` for anything task-launched** — `docs/guide/mise-integration.md`:
  > "The recommended setup is to install the fnox CLI with mise, then use fnox
  > directly through shell integration, `fnox exec`, or mise tasks."

  and, explicitly for mise tasks:
  > "For commands launched through mise, run them through `fnox exec`: … This
  > keeps secret resolution inside fnox, so options such as `env = false`,
  > `as_file`, leases, profiles, and provider-specific behavior all work the
  > same as they do outside mise."

- **The env plugin is explicitly NOT recommended** — same file, a `::: warning`
  block:
  > "**Experimental plugin.** We do not recommend using fnox through the
  > [`jdx/mise-env-fnox`](https://github.com/jdx/mise-env-fnox) env plugin. It
  > is an incomplete experiment and does not track every fnox feature."

  and: "For new setups, prefer shell integration or `fnox exec`."

So the docs' answer is **"shell integration *or* `fnox exec`"** — presented as
co-equal, with the mise env plugin ruled out. There is **no** doc statement
preferring global activation over per-project, and **no** doc recommending
`activate` for a machine with a single global credential set. The `cd`-driven
auto-load that `activate` sells is aimed at **per-project `fnox.toml` files**,
which is not this host's shape.

### The fourth shape the docs describe, aimed exactly at this problem

`docs/guide/proxy.md` — the **credential proxy** — is worth flagging because it
targets the precise hazard of "50 credentials inherited by every agent":

> "The fnox credential proxy lets a command use API credentials without
> receiving their real values. The child process receives placeholders, and
> fnox substitutes the real values only in approved HTTPS requests. **This is
> useful for AI agents** and other untrusted or highly automated programs that
> need to call external APIs."

with first-class examples `fnox proxy run -- codex` and
`fnox proxy run -- claude`, `egress = "strict"` by default, and
`"The CA private key and real secret values remain in fnox process memory."`

This is **out of scope** for "what replaces the rc file" and is **not** a
recommendation here — the current host posture (`env = true` for all 50) is a
deliberate user decision. Recorded only because it is fnox's own answer to the
agent-inheritance problem, and it was not on the table when that decision was
made.

---

## Summary — what the replacement file should be

| Option | Scoped? | Per-prompt cost | Provider hit | Verdict |
|---|---|---|---|---|
| `eval "$(fnox activate zsh)"` (status quo) | **No** | ~11.8 ms spawn | every `cd` + every new shell | current pain |
| `eval "$(fnox activate zsh -P p --no-defaults)"` | **No — flags silently dropped** | same | same | **never write this**; looks scoped, is not |
| `export FNOX_PROFILE=p; eval "$(fnox activate zsh)"` | profile only, **no** `--no-defaults` | same | same | half-scoped, fail-open on typo'd profile |
| **`eval "$(fnox export -f shell -P p --no-defaults)"`** | **Yes, fail-closed** | **none** | **once per shell** | **best fit** |
| `fnox exec -- <cmd>` in tasks | Yes | none | per invocation | docs-endorsed for task-launched work |

The one thing that must not survive review: `fnox activate` with scoping flags
on it. It parses, exits 0, and yields the full 50.

---

## Verification notes

- All local probes ran against fnox **1.32.0** at
  `/Users/rmanaloto/.local/share/mise/installs/fnox/latest/fnox`.
- All secret-bearing probes ran in an **isolated fixture** under the session
  scratchpad with `FNOX_CONFIG_DIR` pointed at an empty directory and
  `FNOX_PROFILE`/`__FNOX_SESSION` unset via `env -u`. Fixture values are
  `aaa`/`bbb`/`ccc`/`plain` — no real credential was read, printed, or resolved.
- The user's real `~/.config/fnox/config.toml` was **not** modified or read.
- `fnox get` and `fnox list -V` were **never** invoked.
- **UNVERIFIED:** the real cold-path cost against the live 50-secret config
  (deliberately not measured — it prints values and is the known keychain-hang
  shape). Also **UNVERIFIED-NEGATIVE:** that no `FNOX_NO_DEFAULTS` env var
  exists anywhere in the source; the `--help` scan that found
  `FNOX_NON_INTERACTIVE` (control) showed no `[env:]` tag for `--no-defaults`,
  which is strong but not a source-level proof.
- Source read from `main`, not the `v1.32.0` tag. The `--help` output of the
  installed 1.32.0 binary matches the `main` source structure on every point
  relied upon here (two-field `ActivateCommand`, bare `hook-env -s zsh` in the
  emitted hook), so the drift risk is low but non-zero.

---

## GitHub repos touched

- [jdx/fnox](https://github.com/jdx/fnox) — primary source of every claim here:
  `src/commands/activate.rs`, `src/commands/hook_env.rs`, `src/hook_env.rs`,
  `src/shell/zsh.rs`, `src/shell/mod.rs`, `CHANGELOG.md`, and
  `docs/guide/{shell-integration,mise-integration,daemon,profiles,how-it-works,proxy,real-world-example}.md`,
  `docs/cli/activate.md`. Repo metadata probed via `gh api` (issues disabled,
  discussions enabled); discussion [#300](https://github.com/jdx/fnox/discussions/300) read.
- [jdx/mise-env-fnox](https://github.com/jdx/mise-env-fnox) — referenced only;
  fnox's own docs carry an explicit "we do not recommend" warning against it.
  Not cloned or read.
- [jdx/mise](https://github.com/jdx/mise) — named as the co-resident shell-hook
  installer in Q5; no mise source was read for this report (the `precmd`
  prepend interaction is derived from fnox's `src/shell/zsh.rs` plus this
  repo's own `.claude/rules/secrets-out-of-the-shell-env.md`).
