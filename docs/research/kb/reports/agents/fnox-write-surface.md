# fnox write / CRUD surface — research report

**Agent:** fnox-write-surface · **Date:** 2026-08-03 · **fnox version probed:** 1.32.0 (local, mise-managed)
**Status:** COMPLETE

Primary sources only: the `jdx/fnox` repo (`docs/`, `src/`, `CHANGELOG.md`) and the local 1.32.0 binary's `--help`.
`fnox get` was never run.

---

## Q1 — Which providers accept writes?

**Answer: read-only is the MINORITY, not the rule — but the split is not the one the
docs' categories suggest.** 17 of 23 documented providers accept `fnox set`. Infisical is
**one of 5 read-only providers** (1password, bitwarden *personal*, doppler, infisical,
proton-pass), plus azure-ac which is read-only by explicit declaration. **All five
read-only ones are the "password manager / CLI-shell-out" class** — fnox drives their
vendor CLI for reads only.

### The mechanism (source of truth)

Write support is decided entirely by `Provider::capabilities()`
(`crates/fnox-core/src/providers/mod.rs:229-233`), whose **default is
`vec![ProviderCapability::RemoteRead]`** — i.e. read-only. Three capability values exist
(`mod.rs:45-52`):

| Capability | Meaning for a write | Where the value lands |
|---|---|---|
| `Encryption` | `provider.encrypt(value)` | **ciphertext in the fnox config file** |
| `RemoteStorage` | `provider.put_secret(key, value)` | **value in the remote**; only a key/reference in the config |
| `RemoteRead` (default) | ⚠️ **no error** — see Q2 defect | **plaintext in the config file** |

Default `put_secret` (`mod.rs:210-227`) errors for a `RemoteRead` provider — but
`set.rs` never calls it for one (see Q2).

### The table

Derived by reading each provider's `capabilities()` impl. A file with **no**
`capabilities()` impl inherits the read-only default.

| Provider | `capabilities()` | `fnox set` writes? | Where the secret goes | Source |
|---|---|---|---|---|
| age | `Encryption` | ✅ yes | ciphertext into fnox.toml | `providers/age.rs:141` |
| aws-kms | `Encryption` | ✅ yes | ciphertext into fnox.toml | `providers/aws_kms.rs:211` |
| azure-kms | `Encryption` | ✅ yes | ciphertext into fnox.toml | `providers/azure_kms.rs:144` |
| gcp-kms | `Encryption` | ✅ yes | ciphertext into fnox.toml | `providers/gcp_kms.rs:121` |
| fido2 | `Encryption` | ✅ yes | ciphertext into fnox.toml | `providers/fido2.rs:142` |
| yubikey | `Encryption` | ✅ yes | ciphertext into fnox.toml | `providers/yubikey.rs:76` |
| plain | `Encryption` | ✅ yes (no-op "encrypt") | plaintext into fnox.toml | `providers/plain.rs:28` |
| aws-ps | `RemoteStorage` | ✅ yes | AWS SSM Parameter Store | `aws_ps.rs:326`, `put_secret` `:405` |
| aws-sm | `RemoteStorage` | ✅ yes | AWS Secrets Manager | `aws_sm.rs:258`, `put_secret` `:460` |
| azure-sm | `RemoteStorage` | ✅ yes | Azure Key Vault | `azure_sm.rs:156`, `put_secret` `:204` |
| gcp-sm | `RemoteStorage` | ✅ yes | GCP Secret Manager | `gcp_sm.rs:232`, `put_secret` `:300` |
| bitwarden-sm | `RemoteStorage` | ✅ yes | Bitwarden Secrets Manager | `bitwarden_sm.rs:176`, `put_secret` `:232` |
| foks | `RemoteStorage` | ✅ yes | FOKS KV | `foks.rs:360`, `put_secret` `:371` |
| vault | `RemoteStorage` | ✅ yes | HashiCorp Vault | `vault.rs:174`, `put_secret` `:231` |
| keychain | `RemoteStorage` | ✅ yes | OS keychain | `keychain.rs:100`, `put_secret` `:188` |
| keepass | `RemoteStorage` | ✅ yes | .kdbx database | `keepass.rs:354`, `put_secret` `:395` |
| password-store | `RemoteStorage` | ✅ yes | GPG pass store | `password_store.rs:122`, `put_secret` `:135` |
| **azure-ac** | `RemoteRead` (explicit) | ❌ **no** | — write via `az appconfig kv set` | `azure_ac.rs:179`; doc `docs/providers/azure-ac.md:82` |
| **1password** | *(no impl → default RemoteRead)* | ❌ **no** | — write via `op` CLI | `onepassword.rs` (0 `ProviderCapability` mentions) |
| **bitwarden** (personal) | *(no impl → default)* | ❌ **no** | — write via `bw` CLI | `bitwarden.rs` (0 mentions) |
| **doppler** | *(no impl → default)* | ❌ **no** | — write via `doppler secrets set` | `doppler.rs` (0 mentions) |
| **infisical** | *(no impl → default)* | ❌ **no** | — write via `infisical secrets set` | `infisical.rs` (0 mentions); doc `docs/providers/infisical.md:31,146` |
| **proton-pass** | *(no impl → default)* | ❌ **no** | — read-only, no write path at all | `proton_pass.rs` (0 mentions); doc `docs/providers/proton-pass.md:109-125` |

`passwordstate.rs` exists in source (`RemoteRead`, `passwordstate.rs:270`) but has **no
`docs/providers/*.md` page**, so it is outside the 23 asked about. `yubikey_usb.rs`,
`hw_encrypt.rs`, `aws_shared.rs`, `resolved.rs`, `resolver.rs`, `secret_ref.rs` are
helper modules, not providers.

**Control arm for the "no impl = read-only" claim:** `grep -l "fn capabilities" *.rs`
returned 20 files (including `age.rs` → `Encryption`, so the pattern discriminates);
`grep -L` returned the 11 without. For the 5 read-only providers named above I then ran a
*second, wider* probe — `grep -c ProviderCapability <file>` — which returned **0** for
each, so they cannot be declaring a capability by any other spelling.

**Corroborating doc arm:** in the docs for every read-only provider, the only `fnox set`
occurrences are `fnox set <PROVIDER>_TOKEN … --provider age` — i.e. storing that
provider's *own auth token* encrypted, never writing a secret *through* it
(`1password.md:15,85,248`; `doppler.md:195`; `infisical.md:22,107,315,390`;
`bitwarden.md:18,91,308`). `proton-pass.md:119` lists "`fnox set` to create or update
Proton Pass items" under **Not supported**.

## Q2 — `fnox set` semantics

**Both, depending on provider class — and it *always* writes the config file.**
`src/commands/set.rs:118-196` resolves the provider, reads `capabilities()`, then:

- `Encryption` → `provider.encrypt(value)` and the **ciphertext is stored in the config
  TOML** (`set.rs:146-160`, `:233-235`). Nothing leaves the machine except a KMS call.
- `RemoteStorage` → `provider.put_secret(key_name, value)` writes to the **remote**, and
  the returned key/reference is stored in the config (`set.rs:161-179`, `:230-232`).
- Everything else (i.e. `RemoteRead`) → `(None, None)` at `set.rs:180-183`.

The config write itself is `config.save_secret_to_source(...)` at `set.rs:322-328`.

### ⚠️ DEFECT: `fnox set` through a read-only provider silently writes PLAINTEXT

`set.rs:236-243`:

```rust
} else if provider_name_to_use.is_some() {
    // Provider specified or default provider available (but not an encryption/remote provider)
    secret_config.set_value(Some(value.clone()));
```

So `fnox set FOO bar --provider infisical` (or `1password`/`doppler`/`bitwarden`/
`proton-pass`/`azure-ac`) does **not** error, does **not** reach the provider, and writes
the **cleartext value into `fnox.toml`**. The `put_secret` default that *would* have
errored (`mod.rs:222-226`) is never called on this path. `--dry-run` shows the value
truncated to 50 chars (`set.rs:301-309`), so a dry run does reveal it, but nothing warns.
Marked **UNVERIFIED-BY-EXECUTION**: read from source only; not executed, because doing so
would write a value into a live config.

### Value input: argv, stdin, or hidden prompt

`set.rs:70-92`. `value` is an **optional positional** (`set.rs:20`). Precedence:

1. argv if given;
2. **stdin when not a TTY** — `echo "x" | fnox set KEY` (`set.rs:76-83`, trimmed);
3. otherwise an **interactive hidden prompt** — `demand::Input::new(...).password(true)`
   (`set.rs:85-91`).

The help text itself warns: *"Passing secrets as arguments exposes them in shell history
and `ps` output. For sensitive values, prefer stdin or the interactive prompt."*
(`set.rs:18-19`, and identically in local `fnox set --help` at 1.32.0). **A CLI wrapping
fnox should pipe on stdin, never argv.**

Other flags (from `set.rs:22-53`, matching local 1.32.0 `--help`): `-d/--description`,
`-g/--global` (writes `~/.config/fnox/config.toml`), `-k/--key-name`, `-n/--dry-run`,
`-p/--provider`, `--base64-encode`, `--default`, `--if-missing`. Global-level
`--write-profile` selects the target profile and is **required when multiple profiles are
active** (`fnox --help`, and `Config::resolve_write_profile` at `set.rs:58`).

## Q3 — Delete

**`fnox remove` exists (aliases `rm`, `delete`) and removes the DECLARATION ONLY. It
never touches the remote.** Verified in local 1.32.0 `fnox remove --help` and in
`src/commands/remove.rs`.

- Signature: `fnox remove [-g|--global] [-n|--dry-run] <KEY>`, plus the global
  `--write-profile` (`remove.rs:6-19`).
- The whole implementation is: resolve the target config path, load **that file only**
  (not the merged config, `remove.rs:54`), confirm the key exists in the write profile
  (`remove.rs:58-77`), then `Config::remove_secret_from_source(...)` — a `toml_edit` AST
  delete + rewrite (`remove.rs:96-97`, impl at `crates/fnox-core/src/config.rs:1171`).
- **No provider is ever instantiated.** There is no `get_provider_resolved` call in
  `remove.rs`, and the `Provider` trait has **no delete method at all**: `grep -rn
  'fn delete_secret|fn remove_secret|fn delete\b' crates/fnox-core/src/providers/` →
  **0 hits**. *Control arm:* the same grep shape for `fn put_secret` over the same
  directory returns **11 files**, so the probe discriminates.

**Consequence for a CLI using fnox as its single entrypoint:** `fnox rm` orphans the
remote value. Deleting from AWS SM / keychain / Vault / Doppler still requires that
provider's own CLI or API. This is a genuine hole in the CRUD surface — fnox is
**CRU**, not CRUD, with respect to remotes.

## Q4 — Write safety (#438): locking + atomicity

**Still true at v1.32.0: config writes are neither locked nor atomic.** The prior
session's finding stands; nothing has changed.

Every config mutation ends in a bare truncating `std::fs::write` of the whole rendered
document — `crates/fnox-core/src/config.rs:1011` (save), **`:1157`
(`save_secret_to_source`, used by `fnox set`)**, **`:1209`
(`remove_secret_from_source`, used by `fnox rm`)**, **`:1289`
(`save_secrets_to_source`, used by `fnox sync`)**.

- **No temp-file-then-rename.** `tempfile` is a dependency
  (`crates/fnox-core/Cargo.toml:59`) but is not used on any config write path; there is
  no `NamedTempFile`/`persist`/`rename` in `config.rs`.
- **No file locking.** The workspace *does* pull `xx = { version = "2", features =
  ["fslock"] }` (`Cargo.toml:106`), but the only two uses in the entire tree are
  `crates/fnox-core/src/lease.rs:45` and `:99` — the **ephemeral-lease store**, not the
  config. *Control arm:* the same `grep -rn` shape for `fs::write` over `src/ crates/`
  returns **38 hits**, so the 2-hit result for lock terms is a real negative, not a dead
  probe.
- **The pattern is read-modify-write.** `save_secret_to_source` reads the file
  (`config.rs:1099-1114`), edits the `toml_edit` AST, writes the whole thing back
  (`:1157`). Two concurrent `fnox set` calls therefore **lose one update**; a crash or a
  full disk mid-write leaves a **truncated config**, and since a file may hold age
  ciphertexts that exist nowhere else, that is data loss, not just inconvenience.

**Has anything changed recently? No.** *Control-armed negative:*
- `CHANGELOG.md` grep for `lock|atomic|concurren|race|corrupt|clobber` returns **~30
  hits, all of them Renovate "lock file maintenance" / `aube-lock.yaml` / `mise.lock` /
  a proton-pass "unlock session" UX message** — none about config writes. Control: the
  same file has **215** hits for `### `/`fnox set`, so the grep works.
- `git log --oneline -15 -- crates/fnox-core/src/config.rs` shows the last 15 touches;
  none is a locking/atomicity fix (nearest are `6702e0f fix(config): preserve secret
  table formatting (#467)` and `debd3cc fix(config): load global config for explicit
  --config paths (#651)`).
- **The repo has GitHub Issues DISABLED** — `gh api repos/jdx/fnox --jq .has_issues` →
  `false`, so every number is a PR and "search the issue tracker" is not available.
  *This is exactly the control-arm case:* `gh search issues --repo jdx/fnox "sync"`
  returned `[]`, which reads as "no such discussion" but actually means "no such
  tracker". PR-title searches for `atomic` and `race` return **0** against a control of
  **551 total PRs** and 17/39/27/12 body-level hits for atomic/concurrent/race/corrupt —
  so the zero is real, not a broken query.

**Implication:** a wrapper CLI that may run concurrently (a hook, a devcontainer
bootstrap, two shells) must serialise its own `fnox set`/`rm`/`sync` calls. fnox will not
do it. (This is the same class of hazard as dotfiles #438.)

## Q5 — `fnox sync`

**`sync` is a native fnox command, and it is manual-trigger only.**
`fnox sync [FLAGS] [KEYS]…` — "Sync secrets from remote providers to a local encryption
provider" (`docs/cli/sync.md`, `src/commands/sync.rs:12`).

### What it does

1. Picks a **target provider** that must have the `Encryption` capability — otherwise it
   errors `SyncTargetProviderUnsupported` (`sync.rs:104-109`). That is why age is the
   target in Ray's config.
2. Selects every secret that (a) has a `provider`, (b) whose provider is **not already
   the target**, and (c) passes the `KEYS` / `--source` / `--filter` filters
   (`sync.rs:128-159`).
3. Resolves each one **raw from its original provider**, deliberately bypassing the
   cached sync value and any `json_path` post-processing (`sync.rs:222-231`).
4. `target_provider.encrypt(plaintext)` each value and stores it as a per-secret
   `sync = { provider = "age", value = "<ciphertext>" }` block (`sync.rs:276-282`,
   `SyncConfig`).
5. `Config::save_secrets_to_source(...)` writes the file (`sync.rs:301`).

### Answers to the specific sub-questions

- **Is it a fnox feature?** Yes, entirely. The 49 age `sync` ciphertexts in Ray's config
  are fnox's own format.
- **What triggers it?** **Only an explicit `fnox sync` invocation.** `SyncCommand` is
  referenced in exactly two places, both plumbing: `src/commands/mod.rs:179` (enum
  variant) and `:234` (dispatch). Nothing in `activate`, `hook_env`, `exec`, or the
  daemon calls it. *Control arm:* the same grep found the `set`/`remove` dispatch lines
  the same way, so the search shape is sound. It also **prompts for confirmation unless
  `--force`** (`sync.rs:196-220`).
- **Does adding/removing one secret rewrite all 49?** **`fnox set` / `fnox rm`: NO.**
  Both `save_secret_to_source` (`config.rs:1141-1154`) and `save_secrets_to_source`
  (`config.rs:1269-1286`) edit **only the named keys** in the `toml_edit` AST and leave
  every other entry — including its `sync` ciphertext — byte-identical; comments and
  formatting are preserved by design.
  **A bare `fnox sync`: YES.** With no `KEYS`, no `--source` and no `--filter`, step 2
  selects *every* eligible secret and step 4 re-encrypts *every* one; age encryption is
  non-deterministic, so all 49 ciphertexts change even when no plaintext did.

  **So the observed churn is the CALLING TOOL's fault, and it is avoidable**: `fnox sync
  <KEY>` (positional) or `--filter '^KEY$'` scopes the re-encryption to one secret. A
  wrapper CLI should always pass the key.

## Q6 — List without values

**`fnox list` (aliases `ls`, `secrets`) is names-only BY DEFAULT — but it CAN print
values, via `-V/--values`.** The premise "confirm it cannot print values" is **false**;
this is a correction, not a confirmation.

From local 1.32.0 `fnox list --help`:

```
  -V, --values                         Show secret values (if available)
  -f, --full                           Show full provider keys without truncation
  -s, --sources                        Show source file paths where secrets are defined
```

Source: `src/commands/list.rs:23-25` declares the flag; `:120-121` only resolves values
`if self.values`; `:143-144` / `:137-138` pick the value-printing renderers. Without the
flag, `:159-169` prints the key plus a *provider reference* and a category string
(`"stored value"` / `"default value"`) — never the plaintext. Note `-f/--full` widens the
**provider key/reference**, not the value; for a `plain`-provider secret the "reference"
IS the value, so `--full` is not unconditionally safe either.

**For a wrapper CLI:** `fnox list` with no flags is the safe enumeration call, and
`-V/--values` must be treated as dangerous exactly like `fnox get`. This repo's
`hook_guard` currently has no rule for `fnox list --values` / `fnox list -V`
(UNVERIFIED — not checked against `hook_guard.py` in this run; flagged for follow-up).

## Bonus — the rest of the write surface (relevant to "single entrypoint")

Enumerated from local 1.32.0 `fnox --help` and per-command `--help`:

| Command | Writes what |
|---|---|
| `set` / `s` | secret declaration + (encrypt or remote put) — Q2 |
| `remove` / `rm` / `delete` | declaration only — Q3 |
| `sync` | `sync = {…}` ciphertext blocks — Q5 |
| `import` / `im` | bulk-import secrets from a format; **requires `--provider`** |
| `reencrypt` | re-encrypt `[KEYS]…` with the current provider config (scopeable) |
| `edit` | opens the config in `$EDITOR` — arbitrary hand edits |
| `init` / `i` | creates a new config file |
| `provider` | ⚠️ **at 1.32.0 there is NO `provider add` / `provider remove`** — both are `unrecognized subcommand`, even though the global `--write-profile` help text lists "provider add/remove" as write commands. Either unreleased or the help text is stale. |
| `lease` | ephemeral credential leases — the **only** path with real file locking (`lease.rs:45,99`) |
| `tui` | interactive dashboard "for managing secrets" (write-capable; not audited here) |

## Bottom line for "can a CLI use fnox as its single entrypoint?"

- **Create/update: mostly yes** — 17 of 23 providers, including every KMS, every cloud
  secrets manager, keychain, KeePass, pass and Vault.
- **Delete: no** — fnox can only delete the declaration; remote deletion always needs the
  provider's CLI.
- **The five password-manager providers (1password, bitwarden, doppler, infisical,
  proton-pass) are read-through-only**, and — the sharp edge — `fnox set --provider
  <one of those>` **does not error, it writes plaintext into the config**
  (`set.rs:236-243`). A wrapper must refuse that combination itself.
- **Concurrency is the wrapper's problem**: no lock, no atomic rename, read-modify-write.
- **Never put the value on argv**; pipe it on stdin (`set.rs:76-83`).

## Method / provenance

- fnox source read from a shallow clone of `jdx/fnox` at `292c788` (tip of `main`,
  one commit past tag `v1.32.0`; `v1.32.1` was still an open release PR #673). All
  `file:line` citations are against that tree.
- Local binary probed: `fnox 1.32.0` (mise install). Only `--help` subcommands were run.
  **`fnox get` was never invoked and no secret value was printed.**
- `https://fnox.jdx.dev` was not fetched — `docs/` in the repo is the source the site is
  generated from, and `docs/cli/*.md` is marked `@generated by usage-cli from usage spec`.

### UNVERIFIED items

| Claim | Why unverified | What was tried |
|---|---|---|
| `fnox set --provider <read-only>` writes plaintext | read from source only; executing it would write a real value into a config | `set.rs:180-183` + `:236-243` read directly; not run |
| Whether this repo's `hook_guard` blocks `fnox list -V` | out of scope of this brief | not probed |
| `fnox tui` write behaviour | not audited | `fnox --help` only |
| Whether `provider add/remove` exists unreleased | `--write-profile` help names them; 1.32.0 rejects them | `fnox provider add --help` → `unrecognized subcommand` |

## GitHub repos touched

- [jdx/fnox](https://github.com/jdx/fnox) — primary source under study: `src/commands/{set,remove,sync,list}.rs`, `crates/fnox-core/src/{config.rs,lease.rs,providers/*}`, `docs/providers/*.md`, `docs/cli/sync.md`, `CHANGELOG.md`, `Cargo.toml`, PR list via `gh api`
