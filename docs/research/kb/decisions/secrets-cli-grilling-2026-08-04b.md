# Grilling outcome — the secrets CLI, 2026-08-04

Output of `/mattpocock-skills:grilling` against the direction set in
`docs/specs/secrets-takeover.md` (STATUS 3) and the 2026-08-04 handoff. Six decisions taken,
each grounded in a measurement made during the session rather than in the inherited record.

**This is a planning artifact.** No code ships from it.

---

## 0. The requirement, in Ray's words

> "Dev projects on the mac having a universal way to crud api keys secrets."

That replaces "takeover" as the north star. Reconcile, scoping and CRUD ownership are all in
service of it, not ends in themselves.

---

## 1. Decisions

| # | Decision | Status |
|---|---|---|
| D1 | **Scoping = additive declaration + reconcile.** A project declares what it additionally needs; the CLI checks the declaration against reality. Scoping buys **zero confinement** — accepted, because confinement is already dead as a goal. | Settled |
| D2 | ~~Declarations use fnox's native hierarchy~~ → **VOIDED BY D5.** The mechanism it chose (committed `fnox.toml` + gitignored `fnox.local.toml`) leaves with fnox. Its *intent* survives — a project records what it needs and reconcile reports drift — and its new home is `doppler setup --scope` plus whatever the CLI declares. **Re-decide in `/to-spec`.** | **Superseded** |
| D3 | **Storage is the status quo.** Keychain holds exactly `DOPPLER_TOKEN`; Doppler CLI owns CRUD; the other 49 stay Doppler-sourced. | Settled |
| D4 | **The highest-value verbs are rotate / classify / retire**, not create. See § 3. | Settled |
| D5 | ~~"fnox stays" is PROVISIONAL~~ → **RESOLVED 2026-08-04: DROP FNOX.** The stack becomes **Doppler + macOS keychain**. See § 6. | **Settled** |
| D6 | **Language deferred** — and largely pre-decided. Rust's only genuine win is typed in-process `fnox-core`, which is **read-only**; D5 removed fnox, so that argument is now moot entirely. | Open, near-zero variance |

## 2. Measurements that drove them

All control-armed. Full working: `.agent/notepad.md`; agent reports under
`docs/research/kb/reports/agents/`.

### fnox has no subtraction primitive (⇒ D1) — ⚠️ CORRECTED, see § 6

> **This heading is wrong and is kept for the record.** `/prototype` claim 2 measured the opposite
> against a fixture with a **real declared profile**: `-P shell --no-defaults` yields exactly the
> profile's 2 secrets out of 52. The six arms below were run with **no profile declared** — and
> zero `[profiles.*]` exist on this host — so the only outcome they could show was the degenerate
> 0. fnox **has** a subtraction primitive; it is **profile-selected, not directory-selected**,
> which is what D1 was actually about. D1 stands; this reason was too strong.

Throwaway project dir + `fnox list --sources`, six arms:

| Arm | from global config | from project file |
|---|---|---|
| bare (control) | 50 | 1 |
| `--no-defaults` | 50 | 1 |
| `-c ./fnox.toml` | 50 | 1 |
| `-P bogus` (fail-open, rc=0) | 50 | 1 |
| `-P bogus --no-defaults` | 0 | 0 |
| `FNOX_CONFIG_DIR=<empty>` | 0 | 1 |

A project dir sees **51**. `--no-defaults` governs profile-vs-top-level merge, **not** the global
config. Confirmed independently by fnox's own docs: *"Global config is always loaded, even when
`root = true` … or `-c/--config` points at an explicit file"* (`guide/hierarchical-config.md:167`).

### Overriding is designed, silent, and undiagnosable (⇒ D2)

A project declaration **replaces** the global entry of the same name: 49 global + 1 local on
collision vs 50 + 1 on the control, `rc=0`, **stderr 0 bytes**. There is no override-warning
setting anywhere (`warn` → 5 hits in the config reference, all five `if_missing`; control
`provider` → 73). Introspection is after-the-fact only: `fnox config-files`, `fnox list --sources`.

This supersedes codex adversarial review finding **H1** (2026-04-08, quoted in
`../macos-development-environment/fnox.toml`), which read designed behaviour as a defect. H1 is
right about the mechanics and wrong about the verdict; its residual concern — a *committed* file
silently repointing a *personal* global token — is answered by fnox's own committed/local split.

### `fnox sync -p keychain` cannot be built (⇒ D3)

`sync` re-encrypts with a **local encryption provider** and writes a `sync` field into the TOML
(`config.rs:263`), not into a keystore. Targets must declare `ProviderCapability::Encryption` —
exactly `age`, `yubikey`, `fido2`, `aws_kms`, `azure_kms`, `gcp_kms`, `plain`. Keychain declares
only `RemoteStorage` (`keychain.rs:100-102`) and has no `encrypt()` override, so it falls to the
trait default `Err("This provider does not support encryption")` (`mod.rs:195-200`; control:
`age.rs:145` does declare it).

Doppler cannot do it either, and structurally: `keychain` → **0** hits across
`docs.doppler.com/llms.txt` (control `sync` → 24) and **0** across the whole CLI help tree
(control `secrets` → 3). Its two sync families are *server-side push to a cloud endpoint* and
*pull-based DIY syncs "with the Doppler CLI"* — neither can address a laptop keystore.

Writing all 50 to the keychain **is** possible (`keychain.rs:188` `put_secret`) and was rejected
on cost: 50 keychain reads per shell prompt and 50 ACL grants to re-apply on every fnox bump
(`installs/fnox/latest` is a symlink → `./1.32.0`; five versions on disk since April), guarding the
failure that produced **190 stuck processes** on 2026-08-02 — while buying ~no secrecy, because
all 50 are already in every process by design under `env = true`.

### fnox's unique feature is inert on this Mac (⇒ D5)

Doppler CLI v3.76.1 natively provides CRUD, `--scope <dir>` per-directory config, an encrypted
offline cache (`--fallback`, `--offline`, `--passphrase` — a functional equivalent of
`fnox sync -p age`), child injection (`doppler run`), and shell-eval-able env
(`secrets download --no-file --format env`).

The one thing it lacks is an automatic chpwd/precmd hook. But **zero** project `fnox.toml` files
exist in `dotfiles` or `knowledge-base`, the only one (mde's) declares no secrets, and
`~/.doppler/.doppler.yaml` holds exactly **one** scope — `/`. No directory on this machine
resolves a different secret set.

Stated fairly, fnox *is* buying one real thing: `DOPPLER_TOKEN` sits in a keychain item with the
fnox binary on its ACL, and the native `doppler login` item is the one that hung forever from
background processes and was deleted on 2026-08-02. Any fnox-less design must re-solve that.

### Rust buys read-only access (⇒ D6)

`fnox-core` has **no `[lib]` section** ⇒ default `rlib` ⇒ Rust-only. `crate-type`, `cdylib`,
`staticlib`, `no_mangle`, `wasm-bindgen`, `napi`, `uniffi`, `neon`, `cbindgen`, `pyo3` → **0 each**
(control: `clap` 56, `async_trait` 68, `rmcp` 13). The 26 `extern "C"` are inbound libusb types.

The public `Fnox` API is `discover / open / with_profile(s) / with_no_defaults / profile / config /
get / list` — **no `set`**, by design; writes live in the binary's unpublished `commands` module.
`fnox mcp` offers strictly fewer verbs than shelling out (stdio, tools-only, exactly `get_secret`
and `exec`). Meanwhile `usage` — the jdx CLI generator — works for a **non-Rust** CLI, yielding
completions for 5 shells, markdown docs, man pages, JSON and typed SDKs from hand-written KDL.

## 3. Why rotate / classify / retire beat create (⇒ D4)

From the consumption sweep (28 repos enumerated, 162 `.mcp.json`, `~/.claude.json`, `~/.config/`):

**CONSUMED 25 · AMBIENT 4 · ALIAS 4 · ORPHAN 17.**

- **Rotate** — one GitHub PAT lives under **four names**, and they are not aliases: mise documents
  a *precedence chain* (`MISE_GITHUB_TOKEN` → `GITHUB_API_TOKEN` → `GITHUB_TOKEN`), plus
  `GITHUB_MCP_PAT`. Rotating it today is four coordinated edits. There is **no documented rotate
  procedure at all**, and a running fnox daemon serves the rotated-away value until idle timeout.
- **Classify** — **19 of 50 are not secrets** (regions, buckets, endpoints, protocols, usernames,
  handles, client IDs, booleans). `.claude/rules/secrets-out-of-the-shell-env.md` rule 3 forbids
  this: value-based redaction means a short or empty "secret" corrupts every log the tool writes.
- **Retire** — **17 orphans, 14 of them one dead project**: an S3-backed
  Grafana/Loki/Mimir/Tempo/OpenLIT stack plus a NextAuth app. The surviving observability compose
  uses local storage and reads only `GRAFANA_PASSWORD`. There is **no documented delete procedure**
  either, and fnox is **CRU** — the `Provider` trait has no delete method at all.

By contrast **create** is a documented 9-step runbook across four systems
(`docs/secrets-doppler-fnox-keychain.md:347-397`), of which `mde-secret-add` already automates
steps 3–7 — everything except `doctor.toml`.

### One design already refuted before being built

Only **1 of 50** secrets is interpolated into an MCP config; the other 49 arrive by **environment
inheritance**. So a reconcile code-scan that greps for `${VAR}` would report **~49 false orphans**.
The project-scope↔code seam needs a different mechanism than the spec assumed.

## 4. What `/prototype` must settle

1. `mise bootstrap dotfiles` — `symlink-each` against a fixture; does `status --json --missing`
   really exit 1 on missing / differs / source-gone?
2. `eval "$(fnox export -f shell -P shell --no-defaults)"` against a **real** declared profile —
   zero `[profiles.*]` exist today, so one must be declared first.
3. The cleartext-write defect — `fnox set … --provider doppler` in a throwaway `FNOX_CONFIG_DIR`,
   both arms.
4. **fnox-full vs fnox-less** — time `eval "$(doppler secrets download --no-file --format env
   --fallback <enc>)"` cold and warm against the current fnox path, and confirm the
   `DOPPLER_TOKEN` keychain-ACL story survives without fnox. **This decides D5, and D6 follows.**

All four are safe with `FNOX_CONFIG_DIR` isolation and fake secrets. **Never print a value** —
compare `value == name`.

## 5. Probe corrections made during this session

Recorded because each is a reusable trap, not to flagellate.

- **A path-spelling bound produced a false negative.** The `-c ./fnox.toml` arm first read
  `local=0` because the grep searched `q1-scope/fnox.toml` while fnox printed
  `q1-scope/./fnox.toml` — the flag's `./` is embedded verbatim in the source column.
- **A probe aimed at a directory with no source in it.** The first keychain-`encrypt()` check ran
  against a scratch dir containing no fnox tree; its `age.rs` **control arm returned empty**, which
  is the only reason it was caught. Re-run against the real clone: same verdict, right reason.
- Agents caught three of their own: a lockfile `awk … {print; exit}` reporting the first of several
  majors; `gh repo list --limit 200` returning exactly 200 against a true **623**; and a crates.io
  sweep printing empty for all 9 crates due to a broken parser, with no control arm passed.
- The consumption agent **refuted the belief it was handed** — "`MISE_GITHUB_TOKEN` and
  `GITHUB_API_TOKEN` are aliases of `GITHUB_TOKEN`" is wrong as stated; they are three distinct
  variables in a documented precedence chain.

## GitHub repos touched

- [jdx/fnox](https://github.com/jdx/fnox) — provider traits, `library.rs`, `mcp_server.rs`, config model, docs
- [jdx/mise](https://github.com/jdx/mise) — GitHub-token precedence chain; crate stack comparison
- [jdx/hk](https://github.com/jdx/hk) — crate stack comparison
- [jdx/usage](https://github.com/jdx/usage) — CLI spec generator; non-Rust viability
- [jdx/xx](https://github.com/jdx/xx) — jdx-owned utility crate in the shared stack
- [DopplerHQ/cli](https://github.com/DopplerHQ/cli) — `run` / `secrets download` / `configure` surfaces (v3.76.1)

---

# 6. `/prototype` outcome — D5 RESOLVED: drop fnox (2026-08-04)

Full harness, every arm and every control: branch **`prototype/secrets-cli-claims`**
(`fce4a80`, `6a27014`, `719c175`), file `prototype/RESULTS.md`. Kept off this branch on purpose —
throwaway code as a primary source, per the prototype skill's capture step.

**Ray's decision: the stack becomes Doppler + macOS keychain.** This reverses the 2026-08-04
"fnox stays" ruling, on measurement rather than argument.

## What was measured

| Question | Result |
|---|---|
| Does every terminal still get the secrets fnox-less? | **Yes — 49 of 50 in a clean shell, 0.117s offline.** Controls: empty env → 0, token-only → 1 |
| The 50th? | `DOPPLER_TOKEN` itself — the bootstrap, from the keychain, not from Doppler |
| Cost shape | fnox `hook-env` ~0.009s on **every prompt**; fnox-less ~0.117s **once per shell** |
| Is the keychain ACL a one-time approval? | **Yes, and automatable — at CREATION only.** Creator is implicitly trusted; `-T /usr/bin/security` and `-A` both read with no prompt; an item trusting only the fnox binary **TIMEOUTs at 8s** behind a GUI dialog |
| Can an existing ACL be amended non-interactively? | **No.** `set-generic-password-partition-list` prompts for the login keychain password; `-k` is deprecated and leaks it into argv ⇒ migrate by **delete-and-recreate** |
| Per-project scoping without fnox? | **Yes.** `doppler setup --scope` is genuinely directory-bound — succeeds inside, fails outside, fails before setup |
| Does `doppler setup` persist the token? | **No.** Key absent, length 0, while `DOPPLER_TOKEN` *was* set in the caller — so it could have |

## Why this beats the incumbent, per axis

- **Durability.** `-T` binds a binary PATH. fnox's is version-pinned (`installs/fnox/1.32.0/fnox`,
  five versions since April) so its ACL breaks on every upgrade. **`/usr/bin/security` is
  OS-stable** — an ACL granted to it never breaks.
- **Scoping.** `doppler setup --scope` is directory-bound. fnox's `[profiles.*]` subtraction is
  real (measured: `-P shell --no-defaults` → exactly 2 of 52) but **profile-selected, not
  directory-selected**, and **zero profiles are declared** on this host.
- **Simplicity.** Four moving parts (Doppler + fnox + age + keychain) become two. The CLI's write
  path drops from **4 systems to 2**, which was most of its complexity.
- **Churn.** The 49-ciphertext re-encrypt on every add/remove disappears with the age cache;
  Doppler's `--fallback` is per-fetch.

## What is given up, stated plainly

22 unused providers; the age `sync` cache (replaced by Doppler `--fallback`); and profile
subtraction. The CLI, not fnox, now owns local-cache correctness.

## Carried forward as work

- **The migration is delete-and-recreate** of the `mde-fnox` `DOPPLER_TOKEN` keychain item with
  `-T /usr/bin/security`, plus a `doppler setup --scope` per project. Both scripted, no password
  prompts. ⚠️ Register scopes with **resolved** paths — macOS `/var` is a symlink to
  `/private/var`, and an unresolved scope silently never matches.
- **Upstream defect to report** (claim 3): `fnox set --provider <doppler>` returns rc=0 and writes
  the **plaintext value** into the config rather than writing through or refusing. Control arm
  `age` writes ciphertext. `jdx/fnox` has Issues disabled ⇒ PR or discussion.
- **D1's stated reason was too strong** — fnox *does* have a subtraction primitive; it is
  profile-selected, not directory-selected. The decision stands, the justification is corrected.
- **`mise bootstrap dotfiles` is confirmed usable** (claim 1): `symlink-each` applies and
  `status --json --missing` exits 1 on missing, differs, dangling-symlink and source-dir-gone.

## Probe discipline — five broken probes, all caught by their own controls

Recorded because the hit rate is the point: a fixture that can only produce one answer is the
default failure mode, not an unusual one.

1. A grep bounded by **path spelling** (`q1-scope/fnox.toml` vs the printed `q1-scope/./fnox.toml`).
2. A probe aimed at a **directory containing no source** — caught only because its control arm
   returned empty.
3. A `[dotfiles]` fixture whose keys mise rejected, leaving "no dotfiles configured" ⇒ **every arm
   returned rc=0**; and a later one that removed source *and* target, which nearly shipped as a
   mise defect that was not one.
4. A claim-3 control (`plain`) that is **itself a cleartext store**, so both arms leaked and the
   probe discriminated nothing.
5. `zsh -f` **inherits the environment**, so a do-nothing control reported **47 of 50 set**; and a
   `doppler secrets --only-names` parse reported 0 names while a download in the same run returned
   49. Both discarded rather than published.
