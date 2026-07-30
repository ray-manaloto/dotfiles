# Concurrency, locking and cross-store atomicity in fnox / Doppler — sweep for #433

**Status:** COMPLETE
**Date:** 2026-07-30
**Ticket:** [ray-manaloto/dotfiles#433](https://github.com/ray-manaloto/dotfiles/issues/433)

## Method and control arms

Search probe used throughout (the `gh search issues --state all` form is broken and
was NOT used):

```bash
gh api -X GET search/issues -f q='repo:<owner>/<repo> <term>' --jq '.total_count'
```

Control arm for the fnox corpus, run with the identical command shape:

| query | total_count | meaning |
|---|---:|---|
| `repo:jdx/fnox secret` | **233** | probe can see the corpus |
| `repo:jdx/fnox zzqqxxww` | **0** | probe can return a true zero |

The pair discriminates, so a zero from this probe is a finding rather than a blind spot.

Source verification is against a fresh `--depth 1` clone of `jdx/fnox` `main`
(not inherited from the prior sweep).

Clone pinned at `34f0ded6a265445ad7589f8463e5248a57fcf635` (2026-07-29, *"feat(azure-ac): add
Azure App Configuration provider (#659)"*) — one day old at time of sweep.

---

## Q1 — Does fnox have ANY write locking?

**Answer: YES, but not where it matters.** The inherited claim was half wrong in a way
that matters, and half right.

### Correction: fnox DOES depend on a file-locking crate

The prior measurement said *"no locking crate in `fnox-core` deps"*. **That is false on
current `main`:**

```toml
# Cargo.toml:106 (workspace deps)
xx = { version = "2", features = ["fslock"] }
```
```toml
# crates/fnox-core/Cargo.toml:67
xx = { workspace = true }
```

`xx` is jdx's own utility crate and the `fslock` feature is enabled explicitly — an
advisory-file-lock dependency, present in `fnox-core`.
Source: [Cargo.toml](https://github.com/jdx/fnox/blob/main/Cargo.toml#L106),
[crates/fnox-core/Cargo.toml](https://github.com/jdx/fnox/blob/main/crates/fnox-core/Cargo.toml#L67).

### But the lock protects the LEASE LEDGER only — never the config

Every use of that lock is in one file, `crates/fnox-core/src/lease.rs`:

```rust
// lease.rs:44-46
pub struct LedgerLockGuard {
    _lock: xx::fslock::LockFile,
}

// lease.rs:92-103
/// Locks a separate `.lock` sentinel file rather than the data file itself,
/// because `save()` uses atomic rename which replaces the data file's inode.
/// Locking the data file directly would break mutual exclusion: after rename,
/// new processes would lock the new inode while the old process holds the old one.
pub fn lock(project_dir: &Path) -> Result<LedgerLockGuard> {
    let ledger_path = Self::ledger_path(project_dir);
    let lock_path = ledger_path.with_extension("lock");
    let lock = xx::fslock::FSLock::new(&lock_path).lock()
        .map_err(|e| FnoxError::Config(format!("Failed to acquire ledger lock: {e}")))?;
    Ok(LedgerLockGuard { _lock: lock })
}
```

This is *competent* concurrency engineering — a sentinel-file lock chosen deliberately
because the data file is replaced by rename, plus an atomic `write-tmp → fs::rename`
save with `0o600` mode (`lease.rs:153-181`). Whoever wrote it understood the problem.

It has exactly **two callers**, both on the read/exec path, neither on the config path:

- `src/commands/exec.rs:115` — `let _lock = LeaseLedger::lock(&project_dir)?;`
- `src/commands/get.rs:147` — same

Source: [lease.rs](https://github.com/jdx/fnox/blob/main/crates/fnox-core/src/lease.rs).

### The config write path has NO lock and is NOT atomic — confirmed on current main

`Config::save_secret_to_source` — the function `fnox set` calls — is a textbook
unguarded read-modify-write:

```rust
// config.rs:1087-1164  (called from src/commands/set.rs:323)
pub fn save_secret_to_source(&self, secret_name: &str, …) -> Result<()> {
    let mut doc = if target_file.exists() {
        let content = fs::read_to_string(&target_file)…;   // READ   (config.rs:1101)
        content.parse::<DocumentMut>()…                     // MODIFY
    } else { DocumentMut::new() };
    …
    fs::write(&target_file, doc.to_string())…              // WRITE  (config.rs:1157)
}
```

No lock acquisition anywhere in the function, and `fs::write` truncates the real file
in place — there is no temp-file-plus-rename, unlike `lease.rs`. All four config write
sites share this shape:

| site | function | caller |
|---|---|---|
| `config.rs:1011` | `Config::save` | whole-config rewrite |
| `config.rs:1157` | `save_secret_to_source` | `src/commands/set.rs:323` |
| `config.rs:1209` | `remove_secret_from_source` | `src/commands/remove.rs:97` |
| `config.rs:1289` | `save_secrets_to_source` | `sync.rs:301`, `import.rs:258`, `reencrypt.rs:316` |

**So the operative conclusion of the prior sweep survives — `fnox set` is an unlocked,
non-atomic read-modify-write — but its stated reason ("no locking crate") was wrong.
fnox has the locking primitive in-tree and simply does not apply it to the config
file.** That distinction matters for us: the upstream fix is a small one (wrap the
config write in the same `LedgerLockGuard` pattern), not an architectural change.

---

## Q3a — Is fnox's Doppler provider read-only? **VERIFIED YES**

`crates/fnox-core/src/providers/doppler.rs` (464 lines) implements exactly three trait
methods:

- `get_secret` (line 111)
- `get_secrets_batch` (line 118)
- `test_connection` (line 188)

It does **not** override `capabilities()`, so it inherits the trait default:

```rust
// providers/mod.rs:229-232
fn capabilities(&self) -> Vec<ProviderCapability> {
    // Default: read-only remote provider (like 1Password, Bitwarden)
    vec![ProviderCapability::RemoteRead]
}
```

And it does not override `put_secret`, so a write attempt lands in the default's
read-only branch:

```rust
// providers/mod.rs:209-226
async fn put_secret(&self, _key: &str, value: &str) -> Result<String> {
    let capabilities = self.capabilities();
    if capabilities.contains(&ProviderCapability::Encryption) { … }
    else if capabilities.contains(&ProviderCapability::RemoteStorage) { … }
    else {
        Err(FnoxError::Provider("This provider does not support storing secrets".into()))
    }
}
```

The chain is fully verified from source: **fnox can never write to Doppler.** Doppler is
a one-way upstream; every fnox write lands in the local TOML.
Source: [doppler.rs](https://github.com/jdx/fnox/blob/main/crates/fnox-core/src/providers/doppler.rs),
[providers/mod.rs](https://github.com/jdx/fnox/blob/main/crates/fnox-core/src/providers/mod.rs#L170).

Corroborated by the PR that added it,
[jdx/fnox#376](https://github.com/jdx/fnox/pull/376) *"feat(provider): add Doppler
secrets manager provider"*, whose entire described surface is
`doppler secrets get <name> --plain` and `--json` for batch — no write verb is
mentioned anywhere in the PR. Read-only was the design, not an oversight.

---

## Q1b — Does the fnox daemon serialise writes? **NO — it has no write path at all**

fnox ships an opt-in per-user daemon over a Unix socket
([jdx/fnox#550](https://github.com/jdx/fnox/pull/550), *"feat(daemon): add per-user
secret resolver daemon"*). It does hold an in-process mutex:

```rust
// src/daemon.rs:542
let request_lock = std::sync::Arc::new(Mutex::new(()));
```
…taken in `process_request` at `daemon.rs:764, 769, 773, 796`.

But the wire protocol admits **no write operation whatsoever**:

```rust
// src/daemon.rs:94-100
enum Request {
    ResolveBatch(ResolveBatchRequest),
    ResolveOne(ResolveOneRequest),
    Status,
    Clear,
    Shutdown,
}
```

It is a *resolver cache* — read, status, cache-clear, shutdown. `fnox set` does not
route through it. **The daemon therefore cannot serialise config writes, and its mutex
is irrelevant to this question.**
Source: [src/daemon.rs](https://github.com/jdx/fnox/blob/main/src/daemon.rs).

---

## Q5 — jdx/fnox discussion #463: a FALSE POSITIVE

The ticket flagged
[jdx/fnox#463](https://github.com/jdx/fnox/discussions/463) as *"surfaced under the
concurrency angle and never read"*. **It has now been read, and it is not about
concurrency.**

Title: *"bug(keepass): database corruption and interop failure between fnox and
KeePassXC"* (category *Troubleshooting and Bugs*, 2026-05-04, fnox 1.23.1, **zero
comments — no maintainer response**).

It is a **serialization-format** bug: `keepass-rs` writes KDBX XML that KeePassXC's
strict parser rejects (`Invalid number value`), and cannot save into a KeePassXC-created
KDBXv4 database (`Unsupported database version`). The words that made it match a
concurrency query are *"corruption"* and *KeePass/unlock*, not any concurrent-write
semantics. Single-writer, sequential, still broken.

**This is worth stating plainly: it is an instance of the same defect class the ticket
exists to correct.** The earlier sweep's term-matching surfaced it as concurrency
evidence; reading it shows it is not. Filtering by reading rather than counting was
load-bearing here.

---

## Q2 — What happens on concurrent writes?

**Answer: a silent lost update. There is no versioning, no etag, no optimistic
concurrency, and no conflict detection anywhere in the fnox write path.**

Derived from the code above, not from a doc claim. Two `fnox set` processes (or an agent
and a human) targeting the same `fnox.toml`:

1. both `fs::read_to_string` the same bytes (`config.rs:1101`);
2. both parse to independent `DocumentMut` trees and each applies **its own** edit;
3. both `fs::write` the whole document (`config.rs:1157`) — last writer wins, and the
   first writer's secret is gone with no error on either side.

Because `fs::write` truncates in place rather than renaming, there is a second, worse
window: a **reader concurrent with a writer can observe a truncated or half-written
TOML file**. `lease.rs` explicitly defends against this for the ledger; the config path
does not.

Searches for any upstream discussion of this, all with the verified control arm:

| query | count | assessment after reading |
|---|---:|---|
| `repo:jdx/fnox "atomic write"` | 5 | none about the config write path |
| `repo:jdx/fnox fslock` | 2 | both are the lease system (#318) and #548 `scan` |
| `repo:jdx/fnox "file lock"` | 111 | ~all Renovate *"chore(deps): lock file maintenance"* noise |
| `repo:jdx/fnox concurrent` | 38 | provider batch **fetch** concurrency (#180, #495, #308), CI test serialisation (#242) — read-side only |
| `repo:jdx/fnox race` | 27 | CI test flakiness and signal handling; no config-write race |
| `repo:jdx/fnox corrupt` | 12 | #463 KeePass serialisation (above); nothing on config |

**No upstream issue, PR, or discussion in `jdx/fnox` raises concurrent config writes.**
Given the control arm (`secret` → 233, `zzqqxxww` → 0), this is a real negative: nobody
has reported it, so there is no upstream fix in flight.

### The comparison that makes this an omission rather than a design choice

The same author's `jdx/mise` **does** lock, using the same `fslock` primitive:

```rust
// mise/src/lock_file.rs:33-45
pub fn lock(self) -> Result<fslock::LockFile> {
    …
    let mut lock = fslock::LockFile::open(&self.path)?;
    if !lock.try_lock()? {
        if let Some(f) = self.on_locked { f(&self.path) }   // "waiting for lock on …"
        lock.lock()?;
    }
    Ok(lock)
}
```
Applied at `mise/src/lockfile.rs:1524, 1752, 2416` (lockfile writes), `shims.rs:200`,
and `config/env_directive/venv.rs:194`.
Source: [mise/src/lock_file.rs](https://github.com/jdx/mise/blob/main/src/lock_file.rs).

So jdx locks mise's lockfile, and locks fnox's lease ledger, but not fnox's config.
**The pattern, the crate and the author are all already present — only the application
to `config.rs` is missing.** That is an upstream gap worth filing, not a wontfix.

---

## Q4 — Doppler's side: etags, conditional writes, config locking

### No etags / conditional writes on the secrets API — VERIFIED NEGATIVE with control arm

Fetched <https://docs.doppler.com/reference/config-secret-update> (HTTP 200, 467 KB):

| term | occurrences |
|---|---:|
| `etag` | **0** |
| `if-match` | **0** |
| `concurren` | **0** |
| `secret` (control) | **249** |

The control confirms the document was fetched and is greppable, so the three zeros are
real. **Doppler's secret-update endpoint documents no entity tag, no conditional write,
no version precondition.** Writes are unconditional last-writer-wins.

⚠️ *Scope caveat:* this is the rendered docs page. I did not obtain a machine-readable
OpenAPI spec, so I cannot rule out an **undocumented** header. Treat this as "not
offered as a supported feature", which is the operative fact for a design decision.

### Doppler's "locks" are deletion guardrails, NOT concurrency control

[DopplerHQ/terraform-provider-doppler#24](https://github.com/DopplerHQ/terraform-provider-doppler/issues/24)
*"Feature: Lock on secrets"* — flagged by the earlier sweep under a concurrency angle.
**Read in full, it is not concurrency.** It asks for Doppler's UI lock to be exposed in
Terraform so that *"removing/changing a resource doesn't cause accidental removal"* —
an anti-footgun flag requiring a two-step apply to delete.

Two decisive comments:

- Reporter `@a-nldisr` (2023-04-06) corrects his own request: *"Locks are not present on
  secrets directly, they need to be done on **branch configs**."*
- Doppler's `@nmanoogian` (2023-04-06): *"Even using locks at the config level, you
  would still be able to remove the config by unlocking it first."* — i.e. an advisory
  guardrail any writer can lift, not mutual exclusion. He closes with *"I'll pass this
  along to our product team"*.

**Still OPEN, filed 2022-09-08, last activity 2023-04-06 — no implementation in ~3
years.** So `configs_lock`/`configs_unlock` (config-level, not secret-level) is a
delete-protection toggle; it gives no atomicity and no conflict detection.

### Doppler's CLI *does* write its local config atomically — and beat fnox to it

```go
// DopplerHQ/cli pkg/utils/io.go:38-56
func WriteFile(filename string, data []byte, perm os.FileMode) error {
	temp := fmt.Sprintf("%s.%s", filename, RandomBase64String(8))
	// write to a unique temp file first before performing an atomic move to the actual
	// file name; this prevents a race condition between multiple CLIs reading/writing
	// the same file
	if err := ioutil.WriteFile(temp, data, os.FileMode(perm)); err != nil { return err }
	if err := os.Rename(temp, filename); err != nil { … }
	return nil
}
```
Used for `UserConfigFile` at `pkg/configuration/config.go:422`.
Source: [DopplerHQ/cli](https://github.com/DopplerHQ/cli/blob/master/pkg/utils/io.go).

Note what this does and does not buy: temp+rename removes **torn reads**, but with no
lock it does **not** remove **lost updates** — the same read-modify-write race remains.
Doppler CLI has solved half the problem; fnox's config path has solved neither half.

Doppler also hit — and fixed — a TOCTOU race of exactly the fnox shape:
[DopplerHQ/cli#493](https://github.com/DopplerHQ/cli/issues/493) *"[BUG] Race condition
when running doppler concurrently on CI"* (2025-06-21) — a check-then-`os.Mkdir` on
`~/.doppler`, reproducible with `$DP me & $DP me`. Fixed by the **merged**
[#495](https://github.com/DopplerHQ/cli/pull/495) *"Fix race condition in concurrent
creation of config and fallback dirs"*. Relevant as precedent: this class of bug is real
in practice, gets reported, and gets fixed — it is not theoretical.

### `repo:DopplerHQ/mcp-server` — the zero is real

All four terms return 0. The repository is small and new; the zero reflects an absent
discussion rather than a broken probe (same command shape that returned 233 for
`repo:jdx/fnox secret`).

---

## Q3b — Any documented pattern for keeping Doppler and a local store consistent?

**No. Nothing in either project documents a two-store consistency pattern, and given
Q3a the question is partly moot in fnox's architecture.**

Because fnox's Doppler provider is strictly `RemoteRead`, there is no fnox-initiated
write to Doppler that could diverge — Doppler is authoritative-upstream and fnox holds a
*reference* (`value = "DATABASE_URL"`), resolved at read time, not a copy. For
provider-referenced secrets there is **no cross-store write atomicity problem to
solve**, because there is only ever one writer per store.

The exposure is different and narrower than "cross-store atomicity":

1. **The local `fnox.toml` is the only thing fnox writes**, and that write is unlocked
   and non-atomic (Q1/Q2). This is a *single*-store integrity problem.
2. **`fnox sync` writes many secrets at once** (`src/commands/sync.rs:301` →
   `save_secrets_to_source`), so a sync racing any other writer loses the largest amount
   of work — and this is exactly the path implicated in the `mde-py` config-wipe
   incident already documented in `.claude/rules/secrets-out-of-the-shell-env.md`.
3. Writes to Doppler happen **out of band** (Doppler UI, `doppler secrets set`, the
   Doppler MCP). fnox never observes them and has no cache-invalidation contract beyond
   the daemon's manual `Clear`.

### Adjacent prior art (Q6) — both apply, in different ways

**GCP Secret Manager ETags — directly applicable, and the shape Doppler lacks.**
<https://cloud.google.com/secret-manager/docs/etags> (fetched, HTTP 200):

> *"Secret Manager supports using entity tags (ETags) for optimistic concurrency
> control… If an ETag is provided and matches the current resource ETag, the request
> succeeds; otherwise, it fails with a `FAILED_PRECONDITION` error and an HTTP status
> code 400. If an ETag isn't provided, the request proceeds without checking the
> currently stored ETag value."*

Supported on `projects.secrets.patch`, `.delete`, and `versions.enable/disable/destroy`.
Note the default: **absent an ETag the write is unconditional** — precisely Doppler's
only mode. This is the canonical design for our Critical #2 and it is worth citing when
filing upstream.

**HashiCorp Vault Secrets Sync — applicable as an architectural counter-example.**
Vault's sync feature makes Vault the single writer and pushes one-way into
destinations, deliberately avoiding bidirectional reconciliation. That is the same
shape fnox's read-only Doppler provider already has, and it is the shape to preserve:
*one writer per store, never two.* (Vault docs: <https://developer.hashicorp.com/vault/docs/sync>
— see caveat in "What I could not determine".)

**chezmoi — gets locking for free by not using a flat file.** chezmoi's persistent state
is bbolt, which takes an `flock(2)` on open:

```go
// chezmoi internal/chezmoi/boltpersistentstate.go:233-236
switch db, err := bbolt.Open(b.path.String(), 0o600, &b.options); {
case errors.Is(err, syscall.EINVAL):
    // Assume that any EINVAL error is because flock(2) failed.
    return fmt.Errorf("open %s: failed to acquire lock: %w", b.path, err)
```
Its only *concurrency* issue found in the tracker is
[twpayne/chezmoi#2001](https://github.com/twpayne/chezmoi/issues/2001) *"fix: Fix
concurrent map writes on sourcestate.ignoredRelPaths"* — an in-process Go map race, not
a multi-process file race. chezmoi's source-state files are user-authored and it does
not arbitrate concurrent external edits to them either.

The Vault wording, verified from the fetched page rather than paraphrased:

> *"Vault can maintain a **one-way sync** for KVv2 secrets into various destinations…
> Vault remains the system of records but can cache a subset of secrets on various
> external systems acting as trusted last-mile delivery systems."*

(Vault Enterprise / HCP Dedicated only, so it is a design reference for us, not a tool
we can adopt.)

### fnox's own docs say nothing about config-write concurrency

Grep of the in-repo `docs/` tree for `concurren|race condition|simultaneous|locking|
atomic` (excluding lockfile noise) returns only:

- `docs/providers/keepass.md:137` — *"**Atomic writes:** Uses temporary files with
  sync-to-disk before rename to prevent data loss"*
- `docs/providers/keepass.md:230, 262` — same claim restated
- two unrelated `WORKER_CONCURRENCY` examples and a GPG-agent unlock note

Control arm: `docs/` plainly contains `secret` (`docs/index.md` et al.), so the grep can
see the corpus. **fnox documents atomic writes for the KeePass provider's database and
for nothing else — there is no documented guidance, guarantee, or warning about
concurrent `fnox set`.** (Mildly ironic given #463 reports that same KeePass database
corrupting, for unrelated format reasons.)

---

## Verdict on Criticals #2 and #3

### Critical #2 (concurrent writes / lost updates) — **OURS TO DESIGN. Not solved, not discussed, not in flight upstream.**

- fnox's config write is an unlocked, non-atomic read-modify-write on current `main`
  (verified from source, `config.rs:1101` → `1157`).
- No issue, PR, or discussion in `jdx/fnox` raises it — against a control arm proving
  the probe can see 233 `secret` hits and return a true 0.
- Doppler's API offers no etag or conditional write (0/0/0 against a 249-hit control).
- Doppler's "locks" are a config-level delete guardrail, open and unimplemented since
  2022.

**But the cost of fixing it is far lower than "design from scratch" implies, and the
inherited framing obscured that.** fnox already vendors `xx`'s `fslock` and already
contains a *correct, commented* implementation of exactly the needed pattern in
`lease.rs` — sentinel `.lock` file plus temp-write-and-rename. The upstream fix is to
apply `LedgerLockGuard`'s pattern to `Config::save_secret_to_source` and its three
siblings. That is a small, well-precedented PR (mise does the same thing in
`lock_file.rs`), and it is worth **filing upstream** rather than only working around
locally. A local mitigation (serialise our own writers; never run `mde-secret-add`
concurrently with a `fnox sync`) is still needed meanwhile, because we cannot make
third-party writers take a lock fnox does not take.

### Critical #3 (cross-store atomicity) — **LARGELY DISSOLVED, and it should be kept that way.**

The premise is weaker than assumed once the read-only finding is verified from source.
fnox **cannot** write to Doppler (`RemoteRead` default → `put_secret` errors), so there
is no two-phase write to make atomic: each store has exactly one writer, and the local
config holds a *reference*, not a copy, resolved at read time. This is the same
one-way-sync discipline Vault deliberately adopts.

So Critical #3 is not "design a distributed transaction". It is two much smaller things:

1. **Preserve the single-writer property.** Any future move to write *into* Doppler —
   e.g. adopting the Doppler MCP's write tools, which the takeover spec (#430) was
   considering for its privilege boundary — is what would *create* a cross-store
   atomicity problem that does not exist today. That is a decision to take knowingly.
2. **Fix the single-store integrity problem**, which is Critical #2. Every concrete
   data-loss event we have actually observed — including the documented `mde-py`
   `bootstrap_config()` wipe — is a local-file write problem, not a cross-store one.

**Contradiction with the ticket's framing worth flagging:** the two upstream artifacts
the ticket named as promising leads (`jdx/fnox` discussion #463, and
`terraform-provider-doppler#24`) both turned out, on reading, to be **false positives**
of the same term-matching that produced the original "not found". #463 is a KDBX
serialisation bug; #24 is delete protection. The genuinely load-bearing evidence came
from reading source (`lease.rs`, `config.rs`, `providers/mod.rs`, mise's
`lock_file.rs`, Doppler's `io.go`), not from the trackers.

---

## What rests on what

| Claim | Basis |
|---|---|
| fnox depends on `xx`/`fslock`; lock used only in `lease.rs`; 2 callers | **Verified from source** @ `34f0ded` |
| `fnox set` → unlocked, non-atomic `fs::write` | **Verified from source**, `set.rs:323` → `config.rs:1087-1164` |
| fnox Doppler provider is read-only | **Verified from source** (3 methods; inherits `RemoteRead` + erroring `put_secret`) |
| fnox daemon has no write request type | **Verified from source**, `daemon.rs:94-100` |
| mise locks its lockfile writes with the same crate | **Verified from source** |
| Doppler CLI writes its local config atomically (no lock) | **Verified from source**, `pkg/utils/io.go:38-56` |
| Doppler API has no documented etag/conditional write | **Verified by fetch + control arm** (0/0/0 vs 249) — docs page only, not an OpenAPI spec |
| Doppler "locks" are delete guardrails | **Maintainer statement** in an issue (`@nmanoogian`, Doppler) — not source |
| Vault sync is one-way, Vault as system of record | **Official docs**, fetched and quoted |
| GCP Secret Manager ETag semantics | **Official docs**, fetched and quoted |
| No upstream discussion of fnox config-write races | **Negative from a control-armed probe** — see caveat below |

### What I could not determine

- **Whether Doppler's API has an *undocumented* conditional-write header.** I read the
  rendered docs page, not a machine-readable OpenAPI spec. The zero means "not offered
  as a supported feature", which is what a design decision needs, but it is not proof of
  absence at the wire level.
- **Whether any fnox concurrency discussion exists outside the issue/PR/discussion
  corpus** — GitHub's search API does not index Discord, and jdx runs an active Discord.
  A negative from this probe is a negative about the *trackers*, not about the project's
  whole conversation.
- **Whether GitHub code search would surface additional `fslock` call sites** beyond the
  shallow clone — a `--depth 1` clone of `main` is the shipped source, so this is a
  low risk, but no branch or fork was examined.
- **Doppler's server-side write semantics** (whether the backend serialises same-secret
  writes internally). Not observable from the CLI, the docs, or the public trackers; it
  would need a live concurrent-write experiment against a real Doppler config.

---

## GitHub repos touched

- [jdx/fnox](https://github.com/jdx/fnox) — primary subject; read `config.rs`, `lease.rs`, `providers/mod.rs`, `providers/doppler.rs`, `src/daemon.rs`, `src/commands/*`, `Cargo.toml`, `docs/`; swept issues/PRs/discussions incl. #318, #376, #463, #548, #550.
- [jdx/mise](https://github.com/jdx/mise) — read `src/lock_file.rs` and `src/lockfile.rs` as same-author prior art proving the locking pattern exists and is applied elsewhere.
- [DopplerHQ/cli](https://github.com/DopplerHQ/cli) — read `pkg/utils/io.go` (atomic temp+rename) and `pkg/configuration/config.go`; read issue #493 and merged PR #495 (real concurrency race, fixed).
- [DopplerHQ/terraform-provider-doppler](https://github.com/DopplerHQ/terraform-provider-doppler) — issue #24 and its comments established that Doppler "locks" are config-level delete protection, per a Doppler maintainer.
- [DopplerHQ/mcp-server](https://github.com/DopplerHQ/mcp-server) — swept for all four terms; genuine zero across the board.
- [twpayne/chezmoi](https://github.com/twpayne/chezmoi) — read `internal/chezmoi/boltpersistentstate.go` (bbolt/`flock(2)`) and issue #2001 as a contrasting persistence design.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the commissioning repo; ticket #433, and cross-referenced `.claude/rules/secrets-out-of-the-shell-env.md`.

Non-GitHub sources consulted: <https://docs.doppler.com/reference/config-secret-update>,
<https://cloud.google.com/secret-manager/docs/etags>,
<https://developer.hashicorp.com/vault/docs/sync>.

