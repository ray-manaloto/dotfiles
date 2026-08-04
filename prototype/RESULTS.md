# Prototype results — the four claims, measured 2026-08-04

Harness: `prototype/secrets_claims_probe.py` (throwaway).
Run: `uv run --project python python prototype/secrets_claims_probe.py [4|1|2|3|all]`.

No secret value was printed at any point. Value-bearing stdout was counted, never rendered.
Every subprocess ran under a hard Python timeout — `timeout`/`gtimeout` are not installed here.

**Verdicts: claim 1 CONFIRMED · claim 2 CONFIRMED (and it corrects a claim I made earlier) ·
claim 3 DEFECT CONFIRMED · claim 4 blocks the fnox-less path.**

---

## Claim 4 — fnox-full vs fnox-less (decides D5)

### 4a. Shell-population cost

| Path | Time | Bytes |
|---|---|---|
| `fnox export -f shell` (daemon allowed) | 0.276s | 3115 |
| `fnox export -f shell --no-daemon` | 0.178s | 3115 |
| `doppler secrets download --no-file --format env` — **no explicit scope** | **rc=1** | *"Unable to fetch secrets from the Doppler API"* |
| + `--project dotfiles --config dev_personal --fallback <f>` | 0.392s | 2872 |
| + `--offline` (fallback only) | **0.142s** | 2872 |

Doppler's offline path is the fastest measured option. But a **bare** `doppler secrets download`
fails: the Doppler CLI's own `.doppler.yaml` (under its config dir) scopes only `/` and carries no
project/config — those live in fnox's provider block instead. A fnox-less design must add
`doppler setup` scoping as well.

### 4b. The `DOPPLER_TOKEN` keychain ACL — this is what blocks the fnox-less path

| Arm | Result |
|---|---|
| `security find-generic-password` (no `-w`, metadata) | **rc=0, 0.015s** — item exists, probe works |
| same, bogus service | **rc=44, 0.018s** — failure returns FAST, not by hanging |
| **`security find-generic-password -w`** (ACL read) | **TIMEOUT at 8.005s**, twice |
| `fnox list --no-daemon` (fnox reads the same item) | **rc=0, 0.021s** |

**fnox is on the `mde-fnox` ACL; `/usr/bin/security` is not.** A non-GUI process asking for the
value blocks forever on a password dialog nobody can answer. Any fnox-less design must first
solve bootstrap-credential retrieval.

⚠️ **This arm is now disabled by default** (`PROTO_RUN_ACL_ARM=1` to re-enable). It popped a real
GUI dialog both times. **Never answer that dialog with "Always Allow"** — it would add
`/usr/bin/security` to the ACL permanently and destroy the condition being measured.

✅ **Python's `subprocess` timeout genuinely killed the blocked process** — `ps` showed no
survivors afterwards, load 8.38. This is why the harness is Python and not shell: the 2026-08-02
incident left 190 stuck processes precisely because nothing could kill them.

---

## Claim 1 — `mise bootstrap dotfiles`: CONFIRMED

`mode = "symlink-each"` applies, and `status --json --missing` exits 1 in **every** bad state:

| State | rc | Expected |
|---|---|---|
| all applied (control) | **0** | 0 ✅ |
| target MISSING | **1** | 1 ✅ |
| target DIFFERS | **1** | 1 ✅ |
| source FILE gone, target symlink DANGLING | **1** | 1 ✅ |
| source DIRECTORY gone | **1** | 1 ✅ |

**Schema, from the live schema** (`raw.githubusercontent.com/jdx/mise/main/schema/mise.json`,
http 200 — the docs cache is stale and misses `[dotfiles]`): the table is **keyed by TARGET
path**, value is a source string or `{ source, mode, exclude, block, template, … }`, and
`symlink-each` is a **directory → directory** mode.

⚠️ **I nearly published a false defect here.** An early fixture removed source *and* target
together and `--missing` returned rc=0; I was one step from reporting "source-gone doesn't fire".
It was correct — nothing was out of desired state. Arming *both* readings of "source gone"
(dangling symlink, and whole directory removed) showed rc=1 for each.

---

## Claim 2 — `-P <profile> --no-defaults`: CONFIRMED, and it corrects an earlier claim

Fixture mirrors the live config (a **copy** of the real 50-secret config — never modified) with a
genuinely declared profile added.

| Arm | total secrets | of which profile-only |
|---|---|---|
| control: no profile | **50** | 0 |
| `-P shell` | **52** | 2 |
| **`-P shell --no-defaults`** | **2** | **2** |
| `-P bogus --no-defaults` | **0** | 0 |

⚠️ **CORRECTION.** Earlier this session I reported "fnox has no subtraction primitive". That was
measured on a fixture with **no declared profile** — and zero `[profiles.*]` exist on this host,
so the only observable outcome was the degenerate 0. Against a real profile the mechanism works:
**`-P <declared profile> --no-defaults` restricts to exactly that profile's secrets.**

The accurate statement is narrower: fnox *has* a subtraction primitive, but it is **profile-
selected, not directory-selected** — a profile is chosen by flag or `FNOX_PROFILE`, never by cwd.
So it still cannot express "this directory sees fewer secrets" on its own, which is what D1 was
actually about. D1 stands; the reason I gave for it was too strong.

---

## Claim 3 — the cleartext-write defect: CONFIRMED

Three arms, isolated `FNOX_CONFIG_DIR`, a fake marker string, asserted by substring (the file is
never printed):

| Provider | rc | entry written | **cleartext in config** |
|---|---|---|---|
| `age` (encrypting writer) — **control** | 0 | yes | **NO** (ciphertext) ✅ |
| `plain` (cleartext store) | 0 | yes | yes — correct by definition |
| **`doppler`** (has **no `put_secret`**) | **0** | yes | **YES — DEFECT** |

The `age` control proves the probe can observe the non-leaking case, so the doppler result is
real. `fnox set --provider <doppler>` returns **rc=0**, writes the entry, and stores the
**plaintext value in the config file** rather than writing through (which it cannot) or refusing.

⚠️ **My first run used `plain` as the "writer" control, which is itself a cleartext store — so
both arms leaked and the probe discriminated nothing.** A control arm has to be able to produce
the *other* answer.

**Worth reporting upstream** — note `jdx/fnox` has GitHub Issues **disabled**, so it needs a PR or
a discussion, not an issue.

---

## What this changes

- **D5 (fnox stays?)** — the fnox-less path is not blocked on speed (Doppler offline is *faster*),
  it is blocked on **bootstrap-credential retrieval** and on **Doppler scoping**. Both are
  solvable; neither is free. This is now a real decision rather than a documentation argument.
- **D1** stands, with a corrected justification (see claim 2).
- **Claim 3** is an upstream defect and an argument for the CLI owning writes rather than passing
  `--provider` through to `fnox set`.

---

## Claim 5 — keychain ACL: one-time, and automatable AT CREATION only

Throwaway items (`proto-acl-<pid>-*`), all deleted afterwards; the live `mde-fnox` item was
never touched (verified intact after cleanup).

| Item created with | read `-w` by `/usr/bin/security` |
|---|---|
| no ACL flags (creator **is** `security`) | **rc=0, 0.017s — no prompt** |
| `-T /usr/bin/security` | **rc=0, 0.018s — no prompt** |
| `-A` (any app) | **rc=0, 0.019s — no prompt** |
| **`-T <fnox binary>` only** | **TIMEOUT 8.003s — prompted** ← discriminating negative arm |
| `set-generic-password-partition-list` (no `-k`) | **TIMEOUT — wants the login password** |

**Answers: yes, one-time; yes, automatable — but only at CREATION time.** Create the item with
the right `-T` list, or simply let the reading tool create it (row 1: the creator is implicitly
trusted), and it never prompts again with no password required. **Amending an existing item's ACL
is NOT automatable** — `set-generic-password-partition-list` prompts for the login keychain
password, and the `-k` flag that skips it is deprecated and puts the password in argv.

⇒ The fnox-less migration is **delete-and-recreate** with the new reader trusted, not an ACL
amendment.

⇒ **Design win.** `-T` binds a binary PATH. fnox's is version-pinned
(`installs/fnox/1.32.0/fnox`, five versions since April) so its ACL breaks on every upgrade.
**`/usr/bin/security` is an OS-stable path.** A CLI that reads the bootstrap token by shelling
out to `/usr/bin/security`, against an item created with `-T /usr/bin/security`, has an ACL that
never breaks on a tool upgrade — strictly more durable than today.

⚠️ **Process note: this arm popped a real GUI dialog, after I had written "negative arm cited,
not re-run" in the probe's own header and then included it anyway.** The header and the code
disagreed. Second unwanted dialog of the session.

## Claim 6 — doppler per-directory scoping: CONFIRMED

Isolated `--config-dir`; no `doppler login` performed, so auth had to come from `DOPPLER_TOKEN`
in the environment.

| Arm | rc | bytes |
|---|---|---|
| control: download BEFORE setup, inside the dir | **1** | 0 |
| `doppler setup --scope <inside> --project … --config … --no-interactive` | **0** | — |
| **download, NO flags, from INSIDE the scope** | **0** | **2872** ✅ |
| control: download, NO flags, from OUTSIDE the scope | **1** | 0 ✅ |

Scoping works, is genuinely directory-bound, resolves project/config with no flags, and
authenticates from the environment token alone.

**`doppler setup` does NOT persist the token.** Measured by key presence and length, never value:
`token` key present = False, length 0 — while `DOPPLER_TOKEN` *was* set in the calling process,
so it could have. Only `enclave.project` / `enclave.config` are written.

⚠️ **Fixture trap worth keeping: `/var` vs `/private/var`.** The first run failed with *"You must
specify a project"* and looked like a doppler limitation. macOS `/var` is a symlink to
`/private/var`, so a scope registered under the unresolved path never matches the cwd doppler
sees. `Path.resolve()` fixed it. A working feature looked broken.

---

## D5 — both blockers are now resolved

| Blocker | Status |
|---|---|
| bootstrap-credential retrieval without fnox | **SOLVED** — create-time `-T /usr/bin/security`, one-time, no password, OS-stable path |
| `doppler setup` scoping | **SOLVED** — directory-bound, env-token auth, no token persisted |

Neither is free, but both are one-time scripted steps. D5 is now a genuine decision rather than
an unknown: fnox-less is **faster** (0.142s offline vs 0.276s), **fewer moving parts**, and costs
a delete-and-recreate of one keychain item plus a `doppler setup` per project.

What is LOST by dropping fnox: 23 providers collapse to one backend; the `sync`-to-age local
cache is replaced by Doppler's own `--fallback`; and `[profiles.*]` subtraction (claim 2) goes
away — though zero profiles are declared on this host today.
