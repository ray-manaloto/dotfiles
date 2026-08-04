# SOPS + age as a secrets backend — primary-source research

**Agent:** secrets-backend-sops-age
**Date:** 2026-08-03
**Source rules:** primary only — `github.com/getsops/sops`, `github.com/FiloSottile/age`,
official SOPS docs site, `age` spec/man pages, local `--help` output.
Third-party tutorials/comparisons are BANNED; any fact available only there is
marked `UNVERIFIED (secondary-only)`.

## Local versions probed

| Tool | Version | Path |
|---|---|---|
| `sops` | 3.13.3 | `~/.local/share/mise/installs/aqua-getsops-sops/latest/sops` |
| `age` | v1.3.1 | `~/.local/share/mise/installs/aqua-filo-sottile-age/latest/age/age` |
| `age-keygen` | (same install) | `.../age/age-keygen` |

Offline KB corpus (`knowledge-base/sources/`) has **no** sops or age tree —
control arm: the same `ls | grep` for `agent-harness-docs` returns 2, so the
probe discriminates. All repo facts below are fetched from GitHub.

---

Repos cloned (shallow) for file:line citation:

- `getsops/sops` @ `382c478` (2026-08-03)
- `FiloSottile/age` @ `706dfc1` (2026-03-20)

---

## Q3 — `sops exec-env` semantics (READ FROM SOURCE)

**Yes, it execs a child process with the decrypted values in its environment.**
It does NOT "tear them down on exit" in any active sense — there is nothing to
tear down, because the values were never placed in the *caller's* environment.

Call chain: `cmd/sops/main.go:186` (`exec-env` command) →
`decryptTree(opts)` at `main.go:249` → the decrypted tree's top-level branch is
flattened into `KEY=VALUE` strings at `main.go:254-274` → passed as
`ExecOpts.Env` to `exec.ExecWithEnv` at `main.go:276-284`.

Inside `ExecWithEnv`
(`cmd/sops/subcommand/exec/exec.go:130-182`):

- `exec.go:143-146` — if `--pristine` is NOT set, `env = os.Environ()` (the
  parent env is forwarded); with `--pristine`, `env` starts empty so **only**
  the decrypted values are present.
- `exec.go:147-156` — the plaintext is split on newlines; blank lines and lines
  starting with `#` are skipped; each remaining line is appended as an env
  entry. (For `exec-env` the plaintext is `[]byte{}` — `main.go:278` — and the
  real values arrive via `opts.Env`, appended at `exec.go:159`.)
- `exec.go:170-181` — default path: `cmd := BuildCommand(opts.Command)`;
  `cmd.Env = env`; stdio wired to the parent; `cmd.Run()`. `BuildCommand` is
  `exec.Command("/bin/sh", "-c", command)` (`exec_unix.go:19-21`).
- `exec.go:161-168` — with `--same-process`, it calls `ExecSyscall`, i.e.
  `syscall.Exec("/bin/sh", ["-c", command], env)` (`exec_unix.go:15-17`). The
  comment at `exec.go:166` states *"the call does NOT return, unless an error
  happens"* — the sops process is **replaced**, so there is no parent left to
  clean up.

**Teardown is process lifetime, not cleanup code.** The env lives in the child
(or the replaced process). When it exits, the environment dies with it. Nothing
in `ExecWithEnv` scrubs or zeroes anything. Any blog claiming an explicit
"tear-down" step is describing process semantics, not sops code.

**Caveat worth knowing:** the values pass through `/bin/sh -c`, so the command
string is shell-interpreted, and the child's env is visible to anything that can
read `/proc/<pid>/environ` (Linux) or is a descendant of it.

### `exec-file` — yes, documented, and materially different

`cmd/sops/main.go:292-381`. Usage string: *"execute a command with the decrypted
contents as a temporary file"* (`main.go:293`).

| | `exec-env` | `exec-file` |
|---|---|---|
| Delivery | env vars on the child | a temp **file**, path substituted for `{}` in the command (`exec.go:115`) |
| Backing store | process env | a **FIFO by default** (`main.go:372` passes `Fifo: !--no-fifo`); `--no-fifo` uses a regular file |
| Perms | n/a | `0600` — regular file chmod at `exec.go:53`, FIFO `syscall.Mkfifo(tmpfn, 0600)` at `exec_unix.go:37` |
| Cleanup | none needed | **explicit**: temp dir created at `exec.go:71` with `defer os.RemoveAll(dir)` at `exec.go:75` |
| Shape | flat `KEY=VALUE` only; complex values REJECTED (`main.go:256-258`) | whole decrypted document in any supported output format |

So `exec-file` is the one with real teardown (`defer os.RemoveAll`), and the
FIFO default means the plaintext never has to touch disk at all. Windows has no
FIFOs — sops warns and downgrades (`exec.go:66-69`).

`exec-env` also **refuses** several shapes rather than silently mangling them:
complex/nested values (`main.go:256-258`), non-string keys (`main.go:262-265`),
and keys containing `=` (`main.go:266-268`) each return a nonzero exit.

---

## Q7 — fail-open vs refusal: **IT REFUSES.** (LIVE PROBE, both arms)

### Why it structurally cannot fail open

`cmd/sops/main.go:249-252`:

```go
tree, err := decryptTree(opts)
if err != nil {
    return toExitError(err)
}
```

The decrypt happens **before** `exec.ExecWithEnv` is reached (`main.go:276`).
Any decrypt failure returns early — the child process is never constructed.
There is no partial-population path: `env` is built from an already-successful
`decryptTree` in one loop (`main.go:254-274`), and every anomaly inside that
loop is `return`, not `continue`.

### Live probe

Fixture: throwaway age identities A (held) and B (**private key deleted** after
encrypting, so it is genuinely unheld), a fake dotenv (`FIXTURE_VAR`,
`OTHER_VAR` — no real secrets), in a scratch dir. Never touched
`~/.config/fnox/config.toml`. Child probe prints **presence flags only**
(`printenv VAR >/dev/null; echo rc=$?`), never a value.
Script: `scratchpad/sopsfix/probe.sh`, child: `scratchpad/sopsfix/child.sh`.

Confounder control: no `~/.config/sops/age/keys.txt` on this host; `SOPS_AGE_KEY`
unset; ambient `SOPS_AGE_KEY_FILE` **overridden per-arm** — ARM4's error text
names the override path, proving the override took effect.

| Arm | Case | EXIT | Child ran? | stderr (first line) |
|---|---|---|---|---|
| **1** | **known-good, recipient held** | **0** | **YES** (`CHILD_RAN=yes`, both vars `rc=0`) | _(empty)_ |
| 2 | nonexistent file | **2** | no | `Error reading file: open does-not-exist.env: no such file or directory` |
| 3 | recipient NOT held | **128** | no | `Failed to get the data key required to decrypt the SOPS file.` → `Group 0: FAILED` |
| 4 | identity file missing | **128** | no | same, plus `failed to open SOPS_AGE_KEY_FILE file: ... no such file or directory` |
| 5 | file is not sops-encrypted | **1** | no | `sops metadata not found` |
| 6 | `--pristine`, recipient held | **0** | YES | _(empty)_ |

**The probe discriminates** — ARM 1 and ARM 6 succeed with the child running and
both variables present; ARMs 2-5 every one exits nonzero and `CHILD_RAN=yes`
never appears on stdout. So "no values" is a *refusal*, not a silent pass.

**Verdict: `sops exec-env` REFUSES.** Nonzero exit, no child process, no partial
environment. Distinct exit codes per class (2 = file read, 1 = not a sops file,
128 = no master key). ARM 3's message is explicit and would be hard to miss in a
log: `at least one key has to be successful, but none were`.

This is the opposite of the classic fail-open hazard, and it is the strongest
single point in SOPS's favour for this evaluation.

**Known caveat (primary source):** getsops/sops issue
[#840](https://github.com/getsops/sops/issues/840) — *"exec-env/exec-file signal
handling might be broken"* (OPEN). Refusal is sound; signal propagation to the
child is not fully settled.

---

## Q1 — Disaster recovery: age supports the mechanisms, but **documents no DR story**

### What age DOES support (all cited, all decisive for DR)

**Multiple recipients — YES, first-class.** `age-src/README.md:208-215`:

> ### Multiple recipients
> Files can be encrypted to multiple recipients by repeating `-r/--recipient`.
> **Every recipient will be able to decrypt the file.**

Usage line `README.md:174`: `age [--encrypt] (-r RECIPIENT | -R PATH)...` — the
`...` is repetition. Flag help `README.md:184-185`: `-r, --recipient RECIPIENT
… Can be repeated.` / `-R, --recipients-file PATH … Can be repeated.`

Recipient **files** (`README.md:217-228`) let you keep the recipient set as a
checked-in, commented list — one per line, `#` comments allowed. This is exactly
the "primary key + YubiKey + offline paper key + second machine" shape, and it
is a **file you can version-control**.

**Passphrase mode — YES.** `README.md:254-264`:

> Files can be encrypted with a passphrase by using `-p/--passphrase`. By
> default age will automatically generate a secure passphrase. Passphrase
> protected files are automatically detected at decrypt time.

**Passphrase-protected identity files — YES, and this is the DR primitive.**
`README.md:266-278`: `age-keygen | age -p > key.age`; an identity file passed to
`-i` that is itself a passphrase-encrypted age file *"will be automatically
decrypted"* (`README.md:268`). The README's own stated use case is precisely
off-machine storage — `README.md:280`:

> Passphrase-protected identity files are not necessary for most use cases,
> where access to the encrypted identity file implies access to the whole
> system. **However, they can be useful if the identity file is stored
> remotely.**

That sentence is the closest thing in the entire age corpus to DR guidance, and
it is one line long.

**YubiKey — supported, via a THIRD-PARTY plugin.** `README.md:30`:
> 🔑 Hardware PIV tokens such as YubiKeys are supported through the
> [age-plugin-yubikey](https://github.com/str4d/age-plugin-yubikey) plugin.

Note it is `str4d/age-plugin-yubikey`, not a FiloSottile repo — so it is out of
the primary-source boundary for its own behaviour. Also `README.md:301` warns
*"SSH keys held on YubiKeys can't be used to decrypt files"* — the SSH-key
convenience path and the YubiKey path are **not** the same thing.

**Also usable as recovery recipients:** SSH public keys (`README.md:282-289`,
`ssh-rsa` / `ssh-ed25519`; `ssh-agent` NOT supported) and post-quantum hybrid
keys (`README.md:232-252`, age ≥ v1.3.0; recipients ~2000 chars).

### What age does NOT do — control-armed absence

**There is no documented backup / disaster-recovery guidance in age.**

- ABSENCE ARM: `grep -rniE "back ?up|backups|recover|disaster|lost (key|device)|key loss"` over
  `age-src/README.md` + `age-src/doc/` (all 12 man-page files) → **0 hits, rc=1**.
- CONTROL ARM, same corpus, same method: `grep -rncE "passphrase"` → README **10**,
  `age.1` **17**, `age.1.ronn` **21**, `age-plugin-batchpass.1` **14**. The probe
  discriminates; the zero is real.
- `age-keygen(1)` (`doc/age-keygen.1.ronn`, read in full) says nothing about
  backing up the identity. Its only protective note is on `-o/--output`: *"If
  OUTPUT already exists, it is not overwritten."*

**So the answer to "what do the age docs themselves recommend" is: nothing.**
age ships the *primitives* for a robust DR posture (multiple recipients,
passphrase-wrapped identities) and leaves the *policy* entirely to the operator.
Any "recommended age backup procedure" you have read is
`UNVERIFIED (secondary-only)` — it is not in the primary corpus.

### The one hard constraint that shapes any DR design

Recipients are fixed **at encrypt time**. `README.md:210` — every recipient *"will
be able to decrypt the file"*, but there is no notion of adding a recipient to an
existing age file without re-encrypting it. Consequence: **the recovery key must
exist BEFORE the first secret is encrypted, or every file must be rewritten to
add it.** For SOPS this is softened — see Q4, where `updatekeys` rewraps the data
key without touching the values.

---

## Q2 — Does "encrypted secrets in a private git repo" satisfy cloud durability? **Partially — and the gap is total, not marginal.**

### What is actually stored in the repo

Structure of a real sops+age dotenv file (throwaway fixture, ciphertext
truncated):

```
FIXTURE_VAR=ENC[AES256_GCM,data:waLXDvGQ…]
OTHER_VAR=ENC[AES256_GCM,data:EKafvf0S…]
sops_age__list_0__map_enc=-----BEGIN AGE ENCRYPTED FILE-----\nYWdlLWVuY3J5…
sops_age__list_0__map_recipient=age1xs9hmgql5e5zg9ur2gesvp4t0e67vnmqw60t4e93jkla4wc9m3jsl6xsk6
sops_lastmodified=2026-08-04T01:30:40Z
sops_mac=ENC[AES256_GCM,data:5G4CxQBL…]
sops_unencrypted_suffix=_unencrypted
sops_version=3.13.3
```

**Stored:** the encrypted values; the age-wrapped **data key** (`_map_enc`); the
**recipient public key in cleartext**; a MAC; version and mtime metadata. Note
the **variable NAMES are cleartext** — a git clone leaks your key *inventory*
even though it leaks no values.

**NOT stored:** the age **private key** (`AGE-SECRET-KEY-1…`). By construction —
that is the whole point.

### Therefore, precisely:

A `git clone` on a new Mac recovers **100% of the ciphertext and 0% of the
ability to read it.** It is a perfect backup of a locked box and no backup at
all of the key. Restated as durability: the repo gives you *availability* of the
encrypted payload from anywhere, and gives you **nothing** toward *recoverability*.

**The requirement "secrets must survive the Mac being lost or destroyed" is
therefore NOT satisfied by the git repo alone.** If the age identity exists only
on that Mac, losing the Mac loses every secret permanently, with the useless
ciphertext preserved in perfect fidelity forever. Git durability is orthogonal to
the failure mode being guarded against.

**What closes the gap** (and it is the operator's job — Q1 shows age documents
none of it): the identity must independently survive, via at least one of —

1. a **second recipient** whose key lives elsewhere (`README.md:208-215`) —
   YubiKey (`README.md:30`), a second machine, or an offline key;
2. a **passphrase-wrapped identity file** stored remotely — the README's own
   stated use case (`README.md:266-280`); this one CAN go in the repo, because
   what is committed is then an age-encrypted blob whose only secret is a
   passphrase in your head or a password manager;
3. an out-of-band copy (printed, hardware, another vault).

Option 2 is the only one that makes "private git repo" genuinely sufficient on
its own — and it must be set up **before** encryption begins (Q1's fixed-recipient
constraint), or every file has to be rewritten. **`age -p` on the identity is the
single decision that turns this option from "loses everything" into "survives".**

---

## Q4 — Rotation and re-encryption cost: TWO different operations, very different costs

SOPS uses envelope encryption: a per-file **data key** encrypts the values; the
**master keys** (here, age recipients) each wrap a copy of that data key. Rotating
the age key and rotating the data key are separate things.

### `sops updatekeys <file…>` — the cheap one (this is what you want)

`cmd/sops/main.go:725-772` → `cmd/sops/subcommand/updatekeys/updatekeys.go`.

What it does (`updatekeys.go:101-110`):

```go
key, err := tree.Metadata.GetDataKeyWithKeyServices(...)   // decrypt data key with a key you still hold
tree.Metadata.KeyGroups = conf.KeyGroups                    // adopt the .sops.yaml recipient set
errs := tree.Metadata.UpdateMasterKeysWithKeyServices(key, ...)  // REWRAP the SAME data key
```

**It re-wraps the data key; it does NOT re-encrypt the values.** The `ENC[…]`
payloads are untouched — only the `sops_age_*` wrapping entries and the metadata
change. Cost is O(recipients), not O(secrets).

Operational shape:

- **Per FILE, not per value** — `UpdateKeys` rejects a directory outright
  (`updatekeys.go:36-38`, `"can't operate on a directory"`), but the CLI accepts
  **multiple file arguments** and loops (`main.go:753`, `for _, path := range c.Args()`).
  So ~50 values in **one** dotenv file = one invocation. 50 separate files = 50
  files on the command line (`sops updatekeys $(git ls-files 'secrets/*.env')`).
- **Driven by `.sops.yaml`**, not by flags — it reads the creation rule and syncs
  the file to it (`updatekeys.go:54-60`). **Hard-fails** if no creation rule
  matches: `"The config file %s does not contain any creation rule"`. So rotation
  is: edit the recipient list in `.sops.yaml` once → run `updatekeys` over the files.
- **Interactive by default** — it prints a diff (`updatekeys.go:83-85`) and
  prompts `Is this okay? (y/n):` (`updatekeys.go:87-100`). Pass `-y/--yes` for
  non-interactive (`main.go:729-732`).
- **Idempotent** — no-ops with `"File %s already up to date"` when nothing
  changed (`updatekeys.go:79-82`).
- **Requires you still hold a current key** (`updatekeys.go:101`). You cannot
  `updatekeys` your way out of having lost every identity — which is Q1/Q2 again.

### `sops --rotate` / `sops rotate` — the expensive one

`cmd/sops/rotate.go:26`. It decrypts the whole tree (`rotate.go:43-52`), then:

```go
// Create a new data key
dataKey, errs := tree.GenerateDataKeyWithKeyServices(opts.KeyServices)   // rotate.go:70
// Reencrypt the file with the new key
err = common.EncryptTree(...)                                            // rotate.go:77
```

**Full re-encrypt of every value** with a brand-new data key. Also supports
`--add-{age,kms,pgp,…}` / `--rm-{…}` to edit the master-key set inline
(`rotate.go:54-67`; `main.go:150-151` documents the flags against `--rotate` *or*
`updatekeys`).

### Summary

| | `updatekeys` | `--rotate` |
|---|---|---|
| Data key | reused | **new** |
| Values re-encrypted | **no** | yes, all |
| Granularity | per file (multi-arg) | per file |
| Driven by | `.sops.yaml` | CLI flags |
| Use for | **age key rotation / adding a recovery recipient** | data-key compromise |

**Answer to "what does rotating the age key across ~50 values require":** edit
`.sops.yaml`, then `sops updatekeys -y <files>`. Not a full re-encrypt, and if
the 50 values live in one file it is a single invocation. This is materially
cheaper than the fnox situation described in the brief, where each add/remove
churns all 49 `sync` ciphertexts.

---

## Q5 — Interactive-shell injection: **no such thing exists.** (control-armed)

**There is no SOPS-native equivalent of `fnox activate`.** `exec-env` is strictly
per-command: it builds a child process (or `syscall.Exec`-replaces itself) and
the environment exists only for that command's lifetime — see Q3,
`exec.go:170-181` / `exec.go:161-168`. There is no chpwd hook, no precmd hook, no
`eval "$(sops …)"` shell-init form, no daemon, no directory-scoped activation.

Control-armed:

- ABSENCE ARM: `grep -rniE "chpwd|precmd|shell hook|shellhook|direnv"` over
  `sops-src` (`*.go`, `*.md`, `*.rst`) → **0 files, rc=1**.
- CONTROL ARM, same corpus, same method: `grep -rn "exec-env"` → **2 files**
  (`CHANGELOG.md`, `cmd/sops/main.go`). The probe discriminates.

The CLI surface confirms it — `sops --help` exposes `exec-env` and `exec-file`
as the only injection verbs (`main.go:186`, `main.go:292`); there is no
`activate`, `shellenv`, or `hook` command.

**Implication for this evaluation:** replacing `fnox activate` with SOPS means
giving up ambient secrets in interactive shells. Every consumer becomes
`sops exec-env secrets.env '<cmd>'`. Whether that is a cost or a *feature*
depends entirely on the posture chosen in
`.claude/rules/secrets-out-of-the-shell-env.md` — under the 2026-08-02 reversal
(`env = true`, all 50 in every shell by decision), SOPS **cannot reproduce the
current behaviour**. Under the prior exec-only posture it would have been a
near-drop-in. This is the sharpest functional mismatch between SOPS and the
requirement as it stands today.

The nearest hand-rolled approximation would be wrapping a login shell:
`sops exec-env secrets.env "$SHELL"`. That is one shell for the whole session
with a fixed snapshot — not per-directory reactivation, and not something either
project documents. Marked `UNVERIFIED` as a *recommendation*; the mechanism
(`exec-env` runs any command, including a shell, via `/bin/sh -c` —
`exec_unix.go:19-21`) is verified.

---

## Q6 — Agent / plugin surface: **nothing, in either project.** (control-armed)

Neither `getsops/sops` nor `FiloSottile/age` ships or documents a Claude Code
plugin, an MCP server, or any agent-scoped access primitive.

**Source-tree arm:**

- ABSENCE ARM: `grep -rniE "model context protocol|\bMCP\b|claude|anthropic|\.mcp\.json|agent-scoped"`
  over BOTH `sops-src` and `age-src` (`*.go`, `*.md`, `*.rst`, `*.json`, `*.yaml`)
  → **0 files, rc=1**.
- CONTROL ARM, same method: `grep -rniE "plugin"` over `age-src` → **8+ files**
  (`age.go`, `README.md`, `parse.go`, `cmd/age-plugin-batchpass/plugin-batchpass.go`,
  `cmd/age/age.go`, `plugin/example_test.go`, …). The probe discriminates.

**Issue-tracker arm** (a second route, per the cross-check habit):

- `gh search issues --repo getsops/sops "MCP OR claude OR anthropic"` → `[]`
- `gh search issues --repo FiloSottile/age "MCP OR claude OR anthropic"` → `[]`
- CONTROL ARM: `gh search issues --repo getsops/sops "exec-env"` → **5 issues**
  (#1469, #1127, #840, #872, #1096). The search API works; the zero is real.

**What age DOES have that is adjacent but is not this:** a documented **plugin
protocol** for *key backends* (`age-src/plugin/`, `README.md:30`,
`README.md:248-252`, and the in-tree `age-plugin-batchpass`). That is an
extensibility point for hardware tokens and alternative KDFs — it is not an
agent, an MCP server, or a permission boundary for a subprocess.

**Assessment for this repo's context:** both tools are plain CLIs. Any
agent-scoped access is something we would build (and per
`.claude/rules/research-doc-sources.md` § "MCP: two lanes", that puts us in lane
2 — CLI/API first, never a registered MCP server). The *upside* is that SOPS's
per-command model (Q5) plus its hard refusal semantics (Q7) compose well with a
`PreToolUse`-style guard: a subprocess either gets exactly the file it was
pointed at, or it gets a nonzero exit and nothing.

---

## Bottom line against the stated requirement

**"Secrets must survive the Mac being lost or destroyed":**

- SOPS+age is **free and open source** — verified by reading both LICENSE files,
  not from memory: sops is **MPL-2.0** (`sops-src/LICENSE:1`, *"Mozilla Public
  License Version 2.0"*); age is **BSD-3-Clause** (`age-src/LICENSE:9-17`, three
  clauses incl. the no-endorsement clause). Requirement met.
- The git repo alone **does not** meet the survival requirement (Q2). The
  ciphertext survives; the key does not.
- age **has** every primitive needed to fix that — multiple recipients,
  `age -p`-wrapped identity files — but **documents no DR procedure at all**
  (Q1, control-armed). The policy is 100% ours to design and write down.
- Because this repo **already** has `[providers.age]` + 49 age ciphertexts, the
  decisive question is not "adopt age?" but **"does a second, off-Mac recipient
  exist for those 49?"** If it does not, the current setup has the identical gap,
  and the fix (a passphrase-wrapped identity copy, or a second recipient) is
  worth doing regardless of whether SOPS is ever adopted.
- SOPS's strongest differentiator here is **Q7: it refuses.** Nonzero exit, no
  child, no partial env, distinct exit codes.
- SOPS's sharpest mismatch is **Q5: no interactive-shell activation**, which
  directly contradicts the current `env = true` posture.

---

## GitHub repos touched

- [getsops/sops](https://github.com/getsops/sops) — read `cmd/sops/main.go`,
  `cmd/sops/rotate.go`, `cmd/sops/subcommand/exec/*.go`,
  `cmd/sops/subcommand/updatekeys/updatekeys.go`, `LICENSE`, `CHANGELOG.md` at
  `382c478` for Q3/Q4/Q5/Q7; searched its issue tracker for Q6.
- [FiloSottile/age](https://github.com/FiloSottile/age) — read `README.md`,
  `doc/age-keygen.1.ronn`, `doc/` man pages, `plugin/`, `LICENSE` at `706dfc1`
  for Q1/Q2/Q6; searched its issue tracker for Q6.
- [str4d/age-plugin-yubikey](https://github.com/str4d/age-plugin-yubikey) —
  referenced only as the YubiKey path named by age's README:30; **not read**, and
  outside the primary-source boundary, so no claim here rests on it.

