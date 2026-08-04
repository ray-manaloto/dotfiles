# Can mise own shell activation for secrets?

**Agent:** mise-shell-activation · **Date:** 2026-08-03 · **Status:** COMPLETE

Question: can `mise` replace `~/.zshrc.d/50-mde-secrets.zsh`'s `fnox activate zsh`,
which is what puts 50 credentials into every shell?

Primary sources: local mise doc cache
(`docs/research/mintlify-cache/jdx/mise/llms-full.txt`, 5434 lines, fetched
2026-07-02), local `mise` 2026.8.1 binary + `--help`/`settings`, and
`github.com/jdx/mise` / `github.com/jdx/mise-env-fnox`.

---

## Q1 — What does `mise activate` install in the shell?

**Method:** ran `mise activate zsh` locally (mise 2026.8.1 macos-arm64, 2026-08-03)
and read the emitted script verbatim. This is the authoritative answer — it is the
exact text `.zshrc` evals.

**Hooks installed — precmd + chpwd, the same two fnox uses:**

```zsh
add-zsh-hook precmd _mise_hook_precmd
add-zsh-hook chpwd _mise_hook_chpwd
```

Both funnel into one function that re-evals mise's env delta:

```zsh
_mise_hook() {
  eval "$(/Users/rmanaloto/.local/bin/mise hook-env -s zsh "$@")";
}
_mise_hook_chpwd() { export __MISE_ZSH_CHPWD_RAN=1; _mise_hook --reason chpwd; }
```

`preexec` is **not** used. Control arm: the emitted script contains
`add-zsh-hook precmd` and `add-zsh-hook chpwd` but zero occurrences of
`preexec` — and the same grep does find `precmd`, so the probe discriminates.

**It installs four things beyond the hooks:**

1. A **`mise` shell function** wrapping the binary, so `mise deactivate` /
   `mise shell` can `eval` their output into the live shell.
2. A **`command_not_found_handler`** that offers to install a missing tool
   (chains to any pre-existing handler, saved as `_command_not_found_handler`).
3. An **undo preamble**. Before installing anything, the script emits `unset`
   for every variable mise currently has in its `__MISE_DIFF`. On this host that
   preamble literally begins `unset AUTH_TOKEN` / `unset AWS_ACCESS_KEY_ID` /
   `unset DOPPLER_TOKEN`. ⚠️ **This does not mean mise sources the secrets** —
   Q2 shows it does not. It means mise's diff has *absorbed* the
   fnox-exported credentials from the ambient shell, so `mise activate` (and
   `mise deactivate`) will happily `unset` all 50. Worth knowing before touching
   the activation order in `.zshrc`.
4. A **precmd fast-path** (`__MISE_ZSH_PRECMD_RUN`, `__MISE_ZSH_ACTIVATE_PATH`,
   `__MISE_ZSH_ACTIVATE_ENV`) that skips the first post-activation `hook-env`
   when `PATH` and the `MISE_*` state are unchanged, and skips `precmd` entirely
   when `chpwd` already ran for the same prompt.

**Versus fnox.** Structurally identical: fnox registers `_fnox_hook` into
`precmd_functions` + `chpwd_functions`; mise registers `_mise_hook_precmd` +
`_mise_hook_chpwd` via `add-zsh-hook`. Both therefore run **before every
prompt**. mise's is the more defensive of the two — it has the dedup fast-path
above, which fnox's does not (fnox's hook has no equivalent short-circuit).
So replacing fnox's hook with mise's does **not** add a per-prompt hook; the
mise hook is already installed and already running.

> Incidental find worth flagging to the caller: mise's `_mise_hook_env_state`
> carries a comment that referencing `${parameters}` "autoloads the
> zsh/parameter module via dlopen, which can deadlock under Rosetta in login
> shells (https://github.com/jdx/mise/discussions/11187)". Relevant to this
> repo's Rosetta/amd64 posture.

## Q2 — Can mise provide env GLOBALLY? **YES — and it already does.**

This is the crux, and the answer is stronger than expected: **the global
`~/.config/mise/config.toml` `[env]` applies in every directory, including
outside any project**, and on this host mise is *already* emitting all 50
credentials everywhere.

**Method:** `mise env -C <dir> --json | jq -r 'keys[]'` — keys only, never
values (per `secrets-out-of-the-shell-env.md` rule 7). `-C/--cd` is a real
`mise env` flag (`mise env --help`).

| Directory | Keys returned | `DOPPLER_TOKEN`/`AWS_SECRET_ACCESS_KEY`/`AGE_PRIVATE_KEY` present? |
|---|---|---|
| `/tmp` (outside every repo) | **75** | **3 / 3 — yes** |
| `$HOME` | **75** | yes |
| `~/dev/.../dotfiles` (repo) | **79** | yes |

**Control arm:** the probe is not stuck returning one answer — it returns 79 in
the repo and 75 outside it, and the 4-key delta is exactly the repo-scoped vars
(`GITLEAKS_CONFIG`, `HK_MISE`, `HK_LOG_FILE_LEVEL`, … sourced from
`dotfiles/mise.toml` per `--json-extended`). So it genuinely distinguishes
global from directory-scoped.

### ⚠️ CORRECTION — the 50 secrets above were INHERITED, not mise-produced

The table above surprised me (why would mise hold `DOPPLER_TOKEN`?), so I
cross-checked by a second route before reporting it — and the surprise was my
probe. `mise env` **echoes back variables already present in the ambient
environment**, and this agent's shell inherits all 50 credentials from
`fnox activate zsh`. `--json-extended` was already hinting at it: every secret
had source `?` (no config file), while every real mise var named a file.

**Re-run under a sanitized environment** (`env -i` with only `HOME`/`PATH`):

```
env -i HOME=$HOME PATH=/usr/bin:/bin:/usr/sbin:/sbin:/Users/rmanaloto/.local/bin \
  /Users/rmanaloto/.local/bin/mise env -C /tmp --json | jq -r 'keys[]'
```

| Arm | Grep | Result |
|---|---|---|
| **CONTROL** — vars we *know* the global config sets (`HK_PKL_BACKEND`, `CPPFLAGS`, `GIT_TERMINAL_PROMPT`) | `grep -c` | **3 / 3 present** |
| **TEST** — secrets (`DOPPLER_TOKEN`, `AWS_SECRET_ACCESS_KEY`, `AGE_PRIVATE_KEY`, `GITHUB_TOKEN`) | `grep -c` | **0 / 4 — absent** |

The control arm proves the probe can see mise's global env; the test arm is
therefore a real negative. **First attempt at this control was itself broken** —
I used `command -v mise`, which resolves to the *shell function* `mise` installed
by `mise activate`, not a path, so both arms returned 0. A control arm returning
0 means the probe is broken, not the world; re-ran against
`/Users/rmanaloto/.local/bin/mise` directly.

### The corrected answer

**YES, mise has a genuine global env source — but it is not currently carrying
the secrets.**

- `~/.config/mise/config.toml` `[env]` **does apply in every directory**,
  including `/tmp` and `$HOME`, with no project config anywhere near. Confirmed:
  **26 keys** survive the sanitized run at `/tmp`, all attributable to the global
  config (`CC`, `CXX`, `CPPFLAGS`, `LDFLAGS`, `GOROOT`, `CARGO_HOME`,
  `RUSTUP_HOME`, `PKG_CONFIG_PATH`, `CONDA_SUBDIR`, `GIT_TERMINAL_PROMPT`,
  `HK_MISE`, `HK_PKL_BACKEND`, the eleven `MDE_DIR_*`/`MDE_*` vars,
  `NOTEBOOKLM_HOME`, `PATH`).
- Directory-scoping applies to a **project** `mise.toml`, not to the global one.
  The cache calls the global config's env "global" and mise's config resolution
  is hierarchical: global config first, then each config file from root down to
  cwd.
- The current `~/.config/mise/config.toml` `[env]` block holds only
  `HK_PKL_BACKEND` and `HK_MISE`; the other global vars come from elsewhere in
  that same file. **No secret mechanism is wired into it today.**

So the premise "shell-wide availability requires a global env source" is
satisfied — `~/.config/mise/config.toml` **is** that global source, it is proven
to reach every directory, and it is the correct place to hang a secrets
mechanism. Whether a mechanism exists that can *fill* it from fnox is Q3/Q5.

> Also worth flagging for the mde retirement: the eleven `MDE_*` variables are
> set by `~/.config/mise/config.toml`, not by mde's zsh files — so they survive
> the repo's deletion, and are a separate cleanup item.

## Q3 — Every `[env]` mechanism; which can pull from a COMMAND?

**Method — enumerated, not asserted.** The doc cache is a 2026-07-02 snapshot and
a shape-match over it (`grep -oE '_\.[a-zA-Z][a-zA-Z0-9_-]*'`) finds only three
(`_.source` 8, `_.file` 7, `_.path` 6) — it misses `_.python`. So I pulled the
**live JSON schema** from the repo instead:

```
curl https://raw.githubusercontent.com/jdx/mise/main/schema/mise.json   # http=200, 152170 bytes
jq '.["$defs"].env' mise-schema.json
```

### `[env]._` modules — the complete list from the schema

| Directive | What it takes | Can it run a COMMAND? |
|---|---|---|
| `_.file` | "environment file to load (**dotenv, json, yaml, or toml**)"; string, or array, or `{path, redact, tools, required}` | **No — file only.** (sops-encrypted files are auto-decrypted; age backend only) |
| `_.path` / `_.paths` | `PATH` entries to add; string/array/object, supports `tools = true` | No |
| `_.source` | "**bash script to load**"; string, or array, or `{path, redact, …}` | **YES — this is the only command escape hatch.** |
| `_.python` | `{ venv = <path> \| {path, create, python, python_create_args, uv_create_args} }` | No |
| *(anything else)* | `_` is `additionalProperties: true` in the schema — which is what lets an **env plugin** add its own key, e.g. `_.fnox-env` | Yes, via plugin (see Q5) |

### Per-variable forms (also from the schema)

`{value}`, `{default}`, `{required}` (bool or help-string), `{age = {value, format}}`
(**experimental** — inline age-encrypted value), each combinable with
`tools = true` and `redact = true`. Plus Tera templates (`{{config_root}}`,
`{{env.VAR}}`, `{{tools.node.version}}`) and `env_shell_expand` (`$VAR`,
`${VAR:-default}`) — **both interpolate, neither shells out.**

Multiple directives of the same kind need `[[env]]` (array of tables), because
TOML forbids duplicate keys.

### So: `_.source` is the mechanism, and it works

Verified end-to-end that `_.source` executes and its exports reach `mise env`:

```toml
[[env]]
_.source = "ctl.sh"     # ctl.sh: export ZZQ_CTL_ARM=1
```

→ `ZZQ_CTL_ARM` present in `mise env --json` under a sanitized `env -i`.
**Control arm 1/1 in all four runs.** The cache warns the sourced file must be a
**bash** script — "the shebang is ignored, mise always sources the file using
`source ./script.sh` in bash."

`fnox export` fits it exactly: `fnox export --format shell` emits
`export KEY=value` lines (`fnox export --help`, fnox 1.32.0), so
`eval "$(fnox export --format shell)"` in a sourced script is the composition.
Measured: **52 lines** from `fnox export --format shell` in a normal shell, run
from an unrelated directory — fnox finds `~/.config/fnox/config.toml` regardless
of cwd (`fnox config-files` → that one path), so it is already global.

### 🚨 HAZARD, measured: `_.source` + a mise-shimmed binary = infinite recursion

Calling **`fnox`** (unqualified) from an `_.source` script while the mise shims
dir is on `PATH` **fork-bombs**. The shim re-enters mise → mise resolves `[env]`
→ runs `_.source` → calls the `fnox` shim → … Measured on this host:

- `ps aux | grep -c '[f]nox'` → **3011 processes**, 1-min load **17.9 → 28.4**
- the `mise env` call never returned (killed at 120s)

**This is the same failure the global config already documents** —
`~/.config/mise/config.toml` carries a comment that enabling `mise-env-fnox` on
2026-04-09 spawned "runaway `fnox config-files` subprocesses (10+ concurrent at
100% CPU each, shell hangs during login-shell sourcing)", tracked as
`macos-development-environment#75`. My reproduction says the root cause is
**shim re-entry**, not the plugin per se.

**Control arm for that diagnosis:** the identical config with the *absolute*
binary path
(`/Users/rmanaloto/.local/share/mise/installs/fnox/latest/fnox export …`)
returned **rc=0 immediately, 0 runaway processes**, control arm still 1/1. So the
recursion is caused by the shim indirection and is avoided by an absolute path
(or by the plugin's documented `tools = true`).

### ⚠️ UNVERIFIED — end-to-end secret *delivery* through `_.source`

I could **not** prove the secrets themselves arrive, and the reason is my
harness, not mise. Across three fixtures the TEST arm stayed 0/5 while the
CONTROL arm stayed 1/1, with fnox's own stderr giving the cause:

```
WARN fnox_core::secret_resolver: Error resolving secret 'GEMINI_API_KEY':
     Age identity file not found: /Users/rmanaloto/.config/fnox/age.txt
```

`AGE_PRIVATE_KEY` is **ABSENT** from this agent's environment (probed with
`printenv`, presence only) and `~/.config/fnox/age.txt` **does not exist**, so
every age-encrypted secret fails to resolve in any subprocess. `DOPPLER_TOKEN`,
`EXA_API_KEY`, `GITHUB_TOKEN` *are* set, i.e. fnox decrypted fine at login —
the bootstrap key just is not itself exported.

**Fixture iterations, each an armed correction of the last** (rule 8 — ask
whether the setup admits the other answer):

| # | Fixture | Why it could only fail |
|---|---|---|
| 1 | `env -i`, no shims | `fnox: command not found` |
| 2 | shims on PATH | fork bomb, 3011 procs |
| 3 | absolute fnox path | no `AGE_PRIVATE_KEY` → age decryption fails |
| 4 | + real `doppler` dir on PATH, `DOPPLER_TOKEN` passed | same — fnox still fell back to the missing age.txt |

What this **does** establish: `_.source` runs, fnox is invoked, and fnox in a
normal shell yields 52 export lines. What remains unproven is only the join,
and it is blocked by an agent-shell artifact. Re-run in Ray's real interactive
shell to close it.

## Q4 — Redaction and per-prompt cost

### Redaction — exists, but does **not** reduce exposure here

mise supports `redact = true` per variable, on `_.file` and on `_.source`, plus
a glob list (`redactions = ["SECRET_*", "*_TOKEN", "PASSWORD"]`), and
`mise env --redacted` / `--redacted --values` to inspect. Age-decrypted values
are "always marked as redacted".

**The load-bearing caveat, verbatim from the cache:** *"Redactions work by
intercepting **task output** line-by-line, so they require a non-`raw` output
mode. Tasks with `raw = true` bypass this interception."*

So redaction hides values in **mise's own task logs**. It does nothing about the
variable being present in the environment of every child process — which is the
entire exposure `secrets-out-of-the-shell-env.md` documents. **Adopting mise
would not shrink the blast radius**; the 50 credentials remain inherited by every
child either way, and `__MISE_DIFF` would still carry them in the
scanner-invisible zlib+base64 form.

One additional silent-failure hazard, verbatim: for direct age encryption, *"If
no identities are found or decryption fails, **mise returns the encrypted value
as-is**."* — a consumer would receive ciphertext rather than an error.

### Cost — mise's hook is already running; caching is on by default

- The `precmd` hook is **already installed** on this host (Q1), so moving
  secrets to mise adds **no new per-prompt hook**. It would let
  `50-mde-secrets.zsh`'s `_fnox_hook` be *removed*, i.e. one fewer per-prompt
  hook, not one more.
- mise's `_mise_hook_precmd` has a dedup fast-path (skips when `chpwd` already
  ran this prompt, and skips the first one when `PATH` + `MISE_*` are unchanged).
- **`MISE_ENV_CACHE` is real and already enabled.** From `mise settings --all`
  on this host:

  | Setting | Value |
  |---|---|
  | `env_cache` | `true` |
  | `env_cache_ttl` | `"1h"` |

  Note `mise settings` (without `--all`) does **not** print them — only
  `--all` does; a probe using the short form would wrongly report them absent.
  These are absent from the 2026-07-02 doc cache entirely (grep for
  `MISE_ENV_CACHE|env_cache` → 0 hits, while `_.source` → 8, so the probe
  discriminates); the schema lists both under settings.

  This means an `_.source` shelling out to fnox is **not** paid every prompt —
  it is cached for an hour. It also means **decrypted secrets are cached to
  disk**. `mise-env-fnox`'s README describes this as "cached encrypted on disk"
  and "scoped to your shell session"; ⚠️ that README also says caching is opt-in
  via `MISE_ENV_CACHE=1`, which **contradicts** the measured default of
  `env_cache = true` — treat the README as stale and the live setting as
  authoritative.

## Q5 — `jdx/mise-env-fnox`

**What it is.** A vfox-style Lua env plugin, read in full at
`~/.local/share/mise/plugins/fnox-env/hooks/mise_env.lua` (already cloned on this
host). `PLUGIN:MiseEnv(ctx)` does exactly this:

1. `fnox config-files` → list of config files (empty ⇒ return no env);
2. `fnox export --format json` (`+ --profile <p>` if `profile` is set);
3. `json.decode` → `data.secrets` → emit as env vars;
4. returns `{cacheable = true, watch_files = config_files, redact = true}`.

So it is a **thin wrapper around the same two fnox CLI calls** I tested by hand
in Q3 — it does not embed fnox, and it does not remove the fnox dependency.

**Wiring required** (README): the plugin must be *both* registered and invoked —
```toml
[plugins]
fnox-env = "https://github.com/jdx/mise-env-fnox"
[env]
_.fnox-env = { tools = true }        # options: tools, profile, fnox_bin
```
On this host it is registered in `~/.config/mise/config.toml` **but `_.fnox-env`
is absent from `[env]`**, so it is genuinely inert — matching the "intentionally
disabled" comment there. `tools = true` is *required* when fnox is mise-managed
(it is here) — that is the plugin's answer to the shim-recursion hazard I
measured in Q3.

**What upstream says — verbatim from the plugin's own README:**

> [!CAUTION]
> I am not sure this plugin is a good idea. fnox was built as a separate CLI for
> a reason. I would probably advise avoiding this.

And mise's own docs, cache line **3147**: *"There is **no direct integration**
between fnox and mise — you configure fnox independently, and it sets
environment variables that mise picks up like any other variables in your
shell."* (line 3145 notes fnox is "a separate project by the same author".)

**Maintenance status** (`gh api`, 2026-08-03):

| Fact | Value |
|---|---|
| Last commit (default branch) | **`4c9ca02`, 2026-03-09** — "Update README.md" |
| Last *code* commit | `e8304bf`, **2026-02-21** — redact=true by default |
| Releases | **0** |
| Open issues | **7** |
| Stars | 16 |
| Archived | no |

So: ~5 months since the last commit, ~5.5 months since the last code change,
never released, 7 open issues, and the author advising against it. The
local clone is at upstream HEAD (`4c9ca02` both sides) — not stale, just
dormant.

**Why upstream discourages it** is stated as a design position, not a bug list
("fnox was built as a separate CLI for a reason"). The concrete costs visible
from the source: it forks fnox twice per uncached env resolution, it can only
surface fnox failures as `print()` warnings while returning an **empty env**
(a silent-degradation path — secrets vanish rather than erroring), and it
inherits the shim-recursion hazard unless `tools = true` is set. This repo has
already been burned by it once (`macos-development-environment#75`, 2026-04-09).

## Q6 — Verdict

**mise can take over the shell-activation *role*, but it cannot replace fnox,
and adopting it buys less than it looks like it does.**

Component by component:

| Capability `50-mde-secrets.zsh` provides | Can mise do it? | Evidence |
|---|---|---|
| A hook that refreshes env before every prompt | **Yes — already installed.** `mise activate zsh` registers `precmd` + `chpwd`, same two hooks fnox uses | Q1 |
| Env in **every** shell regardless of directory | **Yes.** `~/.config/mise/config.toml` `[env]` applies globally — 26 keys survive at `/tmp` under a sanitized env, control arm 3/3 | Q2 |
| Pull values from the fnox CLI | **Yes, via `_.source`** (the only command-capable directive) — or the discouraged `_.fnox-env` plugin | Q3, Q5 |
| **Replace fnox itself** (Doppler sync, keychain, age, profiles, 50 declarations) | **No.** Both native paths (sops `_.file`, inline `age`) are **experimental**, file/inline-only, and would mean re-homing all 50 secrets out of fnox+Doppler | Q3, cache §Secrets |

### The honest answer to the three options posed

**It is option 1 — mise *can* provide shell-wide 50-secret availability — but
only by continuing to call fnox.** It is a re-housing of the activation line,
not a retirement of the dependency. Concretely, `50-mde-secrets.zsh` can be
replaced by adding to `~/.config/mise/config.toml`:

```toml
[env]
_.source = "~/.config/mise/fnox-env.sh"
# fnox-env.sh:  eval "$(/abs/path/to/fnox export --format shell)"
```

…with **the absolute fnox path, never the bare name** (Q3's fork bomb).

**What it genuinely gains:** the mde repo's zsh file goes away; one per-prompt
hook is removed rather than added (mise's is already there); resolution becomes
cached (`env_cache_ttl = 1h`) instead of running fnox's hook every prompt.

**What it does not gain, and should be said plainly:**

- **fnox remains a hard dependency** — the mde retirement does not remove it.
- **No security improvement.** mise's redaction only covers mise's own task
  output; all 50 credentials still land in every child process, and
  `__MISE_DIFF` still carries them in the scanner-invisible form.
- **New failure modes**: shim recursion (measured: 3011 processes), secrets
  cached to disk for an hour, and a `_.source` script whose failure is a silent
  empty env rather than an error.
- **Neither native secret path is production-ready** — both are flagged
  experimental by mise, and direct age returns **ciphertext as-is** on
  decryption failure.

**Recommendation.** If the only requirement is "delete
`~/.zshrc.d/50-mde-secrets.zsh`", the lowest-risk move is not mise at all — it is
to move the existing `fnox activate zsh` line into a chezmoi-managed
`~/.zshrc.d/` file in *this* repo. That is a one-line relocation of a mechanism
that is known to work, versus mise's route which adds an `_.source` shell-out,
a disk cache, and a fork-bomb footgun to achieve the same end state.
The `mise-env-fnox` plugin should stay disabled: unreleased, 5 months dormant,
7 open issues, already broke this host once, and its own author advises against it.

**Do not** treat "mise natively decrypts sops / has built-in age" as a path to
retiring fnox — those replace the *storage*, not the *sync*, and both are
experimental.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — live `schema/mise.json` (authoritative
  `[env]._` enumeration), cached docs `llms-full.txt`, and the local 2026.8.1
  binary's `activate`/`env`/`settings` output.
- [jdx/mise-env-fnox](https://github.com/jdx/mise-env-fnox) — plugin source
  (`hooks/mise_env.lua`, `metadata.lua`, README CAUTION), commit history and
  repo metadata via `gh api`.
- [jdx/fnox](https://github.com/jdx/fnox) — `fnox export`/`config-files` CLI
  surface probed locally at v1.32.0; referenced by mise's secrets docs.
- [ray-manaloto/macos-development-environment](https://github.com/ray-manaloto/macos-development-environment)
  — issue #75, the prior runaway-`fnox config-files` incident cited in
  `~/.config/mise/config.toml`, independently reproduced here.
- [getsops/sops](https://github.com/getsops/sops) · [FiloSottile/age](https://github.com/FiloSottile/age)
  — named as mise's native secret backends (both experimental in mise).

