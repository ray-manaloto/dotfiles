# Secrets: Doppler, fnox, macOS Keychain, and environment variables

What is **actually wired on this Mac for `ray-manaloto/dotfiles`**, the agent
contract in the form this repo enforces, and the recipes for adding and
diagnosing a credential.

**Rewritten 2026-08-03.** Every count and claim below was re-measured on this
host that day against fnox **1.32.0**, with a control arm on each probe and no
value printed. The exec-era version of this file — the mode it taught, its
opt-in list, and the Context7 incident — moved verbatim to
`docs/rules-evidence/secrets-out-of-the-shell-env.md` § "Moved here 2026-08-03".

> Placed at `docs/` and **not** `docs/agents/` deliberately: agnix applies a
> frontmatter rule to `**/agents/*.md`, and this is a prose guide, not an agent
> definition.

## Read this first: all 50 credentials are in every shell, on purpose

```toml
env = true   # ~/.config/fnox/config.toml, line 2 — global
```

**Ray reversed the exec-only posture on 2026-08-02, deliberately.** The stated
requirement was *"in sync and available to all terminals and ai/llm agents"*. So:

- every one of the **50** declared credentials is exported into every
  interactive shell, and inherited by every child — Claude Code, its subagents,
  every MCP server they spawn, every `mise run` task;
- all 50 additionally carry an inline `env = true` (belt and braces — an inline
  per-secret `env` **overrides** the global, so this survives a global flip);
- **`fnox exec` is no longer a confinement boundary.** The parent shell already
  has everything.

**Do not "fix" this back.** It is a decision, not drift. What it costs is stated
plainly in `.claude/rules/secrets-out-of-the-shell-env.md`: the `__MISE_DIFF`
exposure is accepted rather than mitigated, and the confinement work in #432 and
#441 is scoped to a hazard the host no longer avoids.

What still binds, and binds *harder* at 50 credentials than it did at 4:

| Still true | Layer |
|---|---|
| Never commit an environment dump | `no_env_dump` hk step |
| Never print a credential **value**, only presence | `secret_value_substitution` guard rule + the contract below |
| Never mark a non-secret as a secret | reviewed `doctor.toml` diff |
| A clean scanner means "ask what it can see" | judgment; no gate |

## The four layers

| layer | role | what it holds here |
|---|---|---|
| **Doppler** | shared authority — the value of record | project `dotfiles`; configs **`dev_personal`** (49 secrets) and **`dev`** (43) |
| **fnox** | declaration + resolution + optional encrypted cache | `~/.config/fnox/config.toml`; providers `keychain`, `age`, `doppler_dotfiles_dev_personal` |
| **macOS Keychain** | machine-local bootstrap vault | service **`mde-fnox`**, holding **two** accounts: `DOPPLER_TOKEN` (the credential that unlocks everything else) and `DOPPLER_RO_TOKEN` (#487's scoped read-only token, deliberately kept out of the shell) |
| **environment** | process delivery | injected by shell activation (all 50) or `fnox exec`; never the source of truth |

The chain: **Keychain → `DOPPLER_TOKEN` → Doppler → fnox declaration → process env.**

### The live shape, parsed rather than grepped

Measured 2026-08-03 with `tomllib` against `~/.config/fnox/config.toml`, keys
and field-presence only:

| | count |
|---|---:|
| secrets declared | **50** |
| carrying inline `env = true` | **50** |
| provider `doppler_dotfiles_dev_personal` | 49 |
| provider `keychain` (`DOPPLER_TOKEN`) | 1 |
| `sync = { provider = "age" }` blocks | **49** |
| occurrences of `env = "exec"` | **0** |

**50 secrets carry 49 sync blocks, and that is correct.** `AGE_PRIVATE_KEY` is
the one without: it is the key that decrypts the age cache, so it cannot be
cached in it. Do not "fix" 49 → 50 anywhere sync counts appear.

`fnox check` reports `50 secret(s)`, `3 provider(s)`, healthy; `fnox profiles`
shows a single `default` profile.

> 🔬 **Parse the format; do not pattern-match it.** Three greps written for this
> rewrite returned confident zeros — `env = true }` matched 1 of 50 (field order),
> `^[A-Z_]* = {` matched 0 (spacing), and `grep -c 'env = true'` counts the
> header comment. `tomllib` answered all three in one pass. The same trap ate a
> `^env = true$` regex during the 2026-08-03 audit (defeated by a trailing
> comment) and nearly produced "there is no global env setting".

### The `env` mode — the tool's behaviour, unchanged

| `env` | interactive shell / `fnox export` | `fnox exec` | `fnox get` |
|---|:-:|:-:|:-:|
| **`true` (fnox default, and ours)** | **yes** | yes | yes |
| `"exec"` | no | yes | yes |
| `false` | no | no | yes |

A per-secret `env` **overrides** the global. That is why flipping the global
alone changes nothing here — all 50 inline values would still win.

## Two Doppler configs, two lanes — `dev` is not a mistake

This is the correction the previous version of this file most needed. It called
writing to `dev` "the single easiest mistake to make". It is not; `dev` is a
real lane with its own consumer.

| config | real secrets | who reads it |
|---|---:|---|
| **`dev_personal`** | **49** | fnox on this host — every declaration maps to `providers.doppler_dotfiles_dev_personal` |
| **`dev`** | **43** | the devcontainer: `.devcontainer/devcontainer.json:198` downloads `${DOPPLER_CONFIG:-dev}`, pinned to `dev` by `mise.toml:251,277,771` |

(Both report 3 more names than that — Doppler auto-injects `DOPPLER_PROJECT`,
`DOPPLER_CONFIG`, `DOPPLER_ENVIRONMENT`.)

Measured 2026-08-03: **`dev` ⊂ `dev_personal`** exactly — 0 names in `dev` are
absent from `dev_personal`, and `dev_personal` carries 6 extra. Its 49 match
fnox's 49 doppler-backed declarations one for one.

So the operative rule is narrower than "never use `dev`":

- **A host credential written to `dev` never reaches fnox** — declare it in
  `dev_personal`. This still fails silently.
- **A credential the devcontainer needs must be in `dev`**, or `mise run up`
  ships without it.

⚠️ **Latent and unfixed — the *scoping mismatch*, not the token.** #487 is
**CLOSED/COMPLETED** (2026-08-02): the scoped read-only token
`dotfiles-fnox-ro-20260802` exists, in keychain `mde-fnox` under account
`DOPPLER_RO_TOKEN`. What is unfixed is that it is scoped to **`dev_personal`**
while the devcontainer downloads **`dev`**. Repointing `DOPPLER_TOKEN` at it
would break `mise run up`, and the `build.doppler-secrets-wired` contract stays
green straight through — its `per_path_tokens` assert an `--env-file`, the
`doppler.env` path, and `&& doppler secrets download --format docker`, and
**name no config at all** (`python/verification/suites.toml:507-511`). Decide
the scoping before swapping the token.

## The config is generated, and the generator is one command away

`~/.config/fnox/config.toml` opens with *"Managed by `mde-py secrets
bootstrap-config`. Do not edit by hand."* Everything below was re-measured
2026-08-03, and it corrects the reassuring version this file used to carry.

**`which mde-py` returns rc=1 — and that means nothing.** (Control: `which fnox`
rc=0.) `mde-secret-add` is a **live shell function in every interactive shell**,
from `~/.zshrc.d/50-mde-secrets.zsh` (control: a bogus name → "not found"). It
calls `$MDE_PROJECT_DIR/.venv/bin/mde-py`, which is present and executable. The
documented happy path is one command away right now.

**That venv is an editable install** — `mde.pth` points at
`…/macos-development-environment/src` — so *which code runs depends on which
branch that sibling repo has checked out*. There is no pinned copy.

**The fix is checked out, and that is not the same as shipped.** Commit
`691e866` (2026-08-01, *"stop rewriting the fnox config — reconcile through fnox
instead"*) adds and drops declarations by invoking the `fnox` binary, writing the
file directly only when it does not exist — so it **cannot** drop the `env` mode
or a per-secret opt-in. As of 2026-08-03 it lives on the local branch
`fix/bootstrap-config-reroute-through-fnox` only: **not** an ancestor of
`origin/main` (rc=1, control on an `origin/main` commit rc=0), **no PR open**,
and issue
**[macos-development-environment#82](https://github.com/ray-manaloto/macos-development-environment/issues/82)**
still **OPEN**. `src/mde/secrets/manage.py` does not exist on `origin/main` at
all (`git cat-file -e` rc=128; control on `sync.py` rc=0).

⚠️ **So the template-rewrite hazard is currently held off by a checked-out
branch, not by a fix anyone has landed.** Verified two ways on 2026-08-03: that
repo's `HEAD` is `691e866` with `manage.py` clean (control — the probe *can* see
dirt: `.claude/settings.json` shows ` M`), and importing the module through the
venv the wrapper actually calls resolves to that working tree and finds
`_reconcile_declarations` (control: a bogus attribute → `False`), a symbol that
exists only in the fix.

**A `git checkout main` in that sibling repo silently restores the old
behaviour, and nothing in this repo detects it.**

### What still happens on every add/remove, fix or no fix

`add_secret` / `update_secret` (a literal alias) / `remove_secret` each call
`bootstrap_config()` and then run a **full** `_run_fnox_sync_age()` —
`fnox sync --provider age --global --force` — so **all 49 sync ciphertexts are
regenerated** whichever branch is checked out.

On `origin/main`'s version, `bootstrap_config()` additionally rebuilds the file
from a template emitting `provider` + `value` only, preserving just
`DOPPLER_TOKEN`. That is the wipe class of #82, and it is what returns on a
branch switch. What it would cost now:

⚠️ **The mode hazard inverted on 2026-08-02 and the rest did not.** fnox's
default `env` is `true`, so a regeneration now lands on the *desired* mode — the
wipe class that ate `env = "exec"` and its four opt-ins is **benign for the
mode**. What stays fragile:

- **any declaration** the template does not know about — including
  `AGE_PRIVATE_KEY`, which is doppler-primary with no sync block;
- **all 49 `sync` ciphertexts**, silently replaced — this one happens on every
  branch;
- the inline per-secret `env = true` on all 50 — cosmetic while the global says
  `true`, load-bearing the moment it does not.

**fnox is exonerated** — an authorized write probe rewrote all 49 values on both
its scoped and bulk paths and preserved the mode and every opt-in. The defect is
mde's, not fnox's. Full probe table and the wipe timeline:
`docs/rules-evidence/secrets-out-of-the-shell-env.md`.

The durable layer is not this document and not a hand edit: it is
`mise run doctor`'s `fnox-baseline` check, which re-reads the artifact every
session against `doctor.toml` (`[fnox] env = true` plus the full 50-name
`env_true` set, `AGE_PRIVATE_KEY` included). **Adding or removing a secret means
changing `doctor.toml` in the same reviewed diff**, or the next session reports
drift and someone "fixes" it back.

## Agent operating contract

Hard limits, not preferences. These survive the posture reversal unchanged —
with 50 credentials reachable instead of 4, the blast radius of breaking one is
12.5× larger, not smaller.

**An agent MAY**: resolve tool versions/paths · run `fnox config-files`,
`fnox doctor`, `fnox check` · list names only (`doppler secrets --only-names`,
`fnox list` **without** `--values`) · parse the config for **keys and field
presence** · run dry-run sync/removal · ask a human to type a value into a
hidden prompt · invoke a narrow consumer and report a non-secret result · report
key name, scope, operation, timestamp, outcome.

**An agent MUST NOT**:

- ask for a secret to be pasted into chat;
- put a secret in a command argument, file, patch, fixture, or tool input;
- run `doppler secrets get` / `download`, `fnox get`, `fnox export`, or
  `fnox list --values`;
- **run `printenv` / `env` / `set` or shell tracing inside a secret-injected
  process** — this repo violated exactly that on 2026-07-20 by suggesting
  `fnox exec -- env | grep NVIDIA_API_KEY`; the compliant form is below;
- **emit a credential value to its own stdout** — see the trap below; this is
  the surface no gate covered, and it cost four rotations on 2026-08-02;
- use `security … -w` / `-g` to display a Keychain value;
- read `~/.doppler`, the login Keychain DB, an age private key, or a `.env` for
  plaintext — and never read `~/.config/fnox/config.toml` for its **values**;
- add `--yes`/`--force` to a deletion without explicit authorization;
- treat a successful write as a completed rotation.

**Human-only**: creating accounts · passwords/MFA/OAuth consent · viewing a
provider's one-time credential · **typing the value into the hidden prompt** ·
approving paid/production scope · confirming destructive deletion.

Even *names* disclose architecture — summarize counts in public logs, not
inventories.

## Verify presence, never value

```sh
zsh -c '[[ -v KEY_NAME ]] || exit 20; print "credential is present"'
```

Under `env = true` a plain shell is enough; `fnox exec --` is no longer needed
to see a credential, and wrapping a probe in it no longer caps what can leak.

⚠️ **The safe form is only safe alone.**

| expression (with `FOO=visible-safe-value`) | output |
|---|---|
| `${FOO:+SET}` | `SET` |
| `[ -n "$FOO" ] && echo SET \|\| echo ABSENT` | `SET` |
| **`${FOO:+SET}${FOO:-ABSENT}`** | **`SETvisible-safe-value`** |
| the same, on an **unset** variable | `ABSENT` |

`:-` and `:=` are **value-emitting** substitutions. The combined form opens with
the recommended construct, so it reads as compliant, and on an unset variable it
looks perfect — which is why an unset-only control arm certifies nothing. **Arm
a presence probe on a variable that IS set, with a value you can afford to see.**
A live Doppler token reached a transcript this way on 2026-08-02, by an agent
citing the rule it was breaking. Now denied by `hook_guard`'s
`secret_value_substitution`; every other value-emitting shape is still on you.

Presence is not correctness. Correctness needs a narrow provider health check
whose response contains no secret — an identity endpoint returning an account
id, or a minimal request returning an expected status.

Never record token prefixes/suffixes, hashes of low-entropy secrets, auth
headers, raw env dumps, or the contents of a secret-bearing config.

## Add a secret

1. Confirm key name, **which config** (`dev_personal` for the host,
   `dev` if the devcontainer needs it, both if both), consumer, scope, rotation
   expectation, and that no existing credential can be reused.
2. Human creates/reveals the credential at the provider.
3. Interactive setter — **no value argument**, so nothing enters argv or history:

   ```sh
   doppler secrets set 'KEY_NAME' \
     --project dotfiles --config dev_personal --silent
   ```

4. Human types the value into the hidden prompt.
5. Confirm it appears in a **names-only** listing:

   ```sh
   doppler secrets --project dotfiles --config dev_personal --only-names | grep KEY_NAME
   ```

6. Declare it in fnox (`fnox edit`) — the declaration holds the **name**, never
   the value:

   ```toml
   KEY_NAME = { provider = "doppler_dotfiles_dev_personal", value = "KEY_NAME", env = true }
   ```

7. Optional offline cache: `fnox sync --global -p age KEY_NAME`.
   ⚠️ **`--global` is not optional.** Without it fnox targets a `fnox.toml` in
   the current directory, not the config the declaration lives in — the dry-run
   output says `to provider age (global):` only with `-g`, and mde's own code
   uses `fnox sync --provider age --global --force`. (One route plus
   corroboration; never observed as a write, since settling it would require a
   real sync.)
8. **Add the name to `doctor.toml`'s `[fnox] env_true` list in the same reviewed
   diff.** Under `env = true` this is the reviewed decision — the new credential
   lands in every terminal and every agent by default, and the doctor's baseline
   is what makes that a decision rather than a drift.
9. Run a narrow consumer health check; report only the non-secret result.

**Never**: `doppler secrets set KEY 'value'` (argv/history) or
`echo 'value' | doppler secrets set KEY` (plaintext through the tool call).

⚠️ **`mde-secret-add KEY` does steps 3-7 in one command and is the sanctioned
mde interface — and it churns all 49 sync ciphertexts every time.** It does not
rewrite the whole config *while* the sibling repo stays on the #82 fix branch;
on `origin/main` it does. See "The config is generated" above before reaching
for it, and it still does not touch `doctor.toml` for you.

## Diagnose "the variable isn't set" — in this order

Each step is contract-compliant (no value read or printed) and each
**discriminates**, so a pass genuinely rules that layer out.

```sh
# 1. Which config files are actually in play?  fnox merges the user root into
#    EVERY invocation, even with an explicit -c.  Expect this one line.
fnox config-files

# 2. Is the secret DECLARED?  names only, never --values.
fnox list | grep KEY_NAME

# 3. Is it in the plain interactive shell?  Under env = true it must be.
zsh -c '[[ -v KEY_NAME ]] && print present || print ABSENT'

# 4. Does it resolve to a process at all?
fnox exec -- zsh -c '[[ -v KEY_NAME ]] && print present || print ABSENT'

# 5. Is the offline age copy stale vs Doppler?  dry-run reveals no values.
fnox sync --dry-run -p age KEY_NAME
#   "Would sync 1 secrets … KEY_NAME (from doppler_…)"  -> a copy would change
#   "No secrets to sync"                                -> nothing to do / unknown key
```

**Reading the result:**

| step 3 (shell) | step 4 (`fnox exec`) | meaning |
|---|---|---|
| present | present | **healthy** — the expected state for all 50 |
| **ABSENT** | present | ⚠️ **A REAL FAULT.** Under `env = true` nothing should be exec-only. Do not dismiss it. |
| ABSENT | ABSENT | declaration or provider problem — suspect order below |

⚠️ **`fnox check` is not step 1, because for a *lost declaration* it can only
pass.** Measured 2026-08-03 on a throwaway fixture, both arms:

| fixture | `fnox check` |
|---|---|
| two probe keys **declared** | rc=0 · `Found 52 secret(s)` · ✓ healthy |
| one declaration **deleted** | rc=0 · `Found 51 secret(s)` · ✓ healthy |

Identical verdict either way. `check` validates what is *declared*, and
`if_missing` lives on the declaration line — so a line that vanished is not
"missing", it is unknown. The only signal is the **count**, and `check` compares
it against nothing. `doctor.toml`'s 50-name baseline is the layer that can see
this.

**Bare `fnox check` is weaker still — it also passes for a declared secret that
does not resolve.** Measured on a fixture declaring a keychain item that does not
exist:

| invocation | result |
|---|---|
| `fnox check -c <fixture>` | rc=0 · ✓ **healthy** |
| `fnox check -c <fixture> -a` | rc=0 · ✓ OK **with warnings** · names the secret |
| `fnox check -c <fixture> --if-missing error` | **rc=1** · `Found 1 error(s)` · names the secret |

So `--if-missing error` is the arm that can fail; use it when you want `check` to
mean anything. Neither form sees a **deleted** declaration.

**Suspect order when a variable is missing:**

1. ⚠️ **A hung `doppler` CLI.** fnox's doppler provider **shells out** to it
   (tell: `Doppler: command failed`), so any *uncached* doppler-primary secret —
   `AGE_PRIVATE_KEY`, which cannot have an age cache — resolves through a child
   `doppler` process. A keychain **authorization dialog** blocks that child
   forever from a non-GUI process, and nothing can answer the dialog.
   **Resolved on this host**: the `doppler-cli` and `gh:github.com` keychain
   entries were deleted and both tools fall through to their ENV token. Verified
   2026-08-03 — `doppler configs` returns rc=0 in under 25s from a background
   process, where it previously hung indefinitely.
   ⚠️ A hang is **not** evidence of a locked keychain.
   `security show-keychain-info` prompts unconditionally, so *its* hang proves
   nothing; believing it cost ~2 hours on 2026-08-02. fnox reads a keychain
   secret in 0.03s, which a locked keychain cannot do.
2. **A stale `MISE_ENV_CACHE` entry.** It can serve a dead name in **one
   directory** long after the config is byte-identically restored, and `grep`
   cannot see it — the cache is encrypted. Clear
   `~/.local/state/mise/env-cache`.
3. **The declaration itself** — steps 1-2 above, then `doctor.toml`.

**Always control-arm the negative.** An ABSENT result is worthless until the
same command shape returns present for something you *know* is set:

```sh
zsh -c '[[ -v HOME ]] && print "control ok: [[ -v ]] works"'
```

A 2026-07-29 session reported a variable "set, 43 chars" and later "unset" from
two probes in the same session. The control arm is what settled it.

⚠️ **`env | grep` is forbidden inside a secret-injected process.** Use
`[[ -v VAR ]]`, which reveals presence without the value.

## Evidence record

```text
Operation: add | update | rotate | delete | sync
Key: <authorized name>
Authority: Doppler dotfiles/dev_personal | Doppler dotfiles/dev | Keychain mde-fnox/<account>
Consumer: <program>
Value observed by agent: no
Name/presence check: pass | fail
Consumer health check: <safe result>
doctor.toml env_true updated: yes | n/a
Timestamp: <ISO-8601>
```

## Incidents

Two are kept here because they teach the contract. The posture-era incidents —
the Context7 anonymous tier, the config wipe and its attribution — moved to
`docs/rules-evidence/secrets-out-of-the-shell-env.md`.

### 2026-07-29 — contract breaches by an agent, recorded, not excused

While diagnosing a missing credential, the agent violated the contract three
ways:

1. **Ran `fnox get` and `doppler secrets get`** — both explicitly on the MUST
   NOT list — to sha256-compare the two values. Output was truncated to 12 hex
   chars, never the value, but the commands themselves are forbidden.
2. **Interpolated a live key into `curl -H "Authorization: $K"`** — a secret in
   a command argument, which the contract forbids because argv is observable.
3. Reached for `env | grep` on secret names.

None of it reached a tracked file or the transcript, and the endpoint was the
credential's legitimate vendor. It was still avoidable: **`fnox sync --dry-run
-p age` answers the staleness question without reading any value**, and
`[[ -v ]]` answers presence. Both are in the MAY list.

### 2026-08-02 — a presence probe printed a live token

`${DOPPLER_TOKEN:+PRESENT}${DOPPLER_TOKEN:-ABSENT}` printed `PRESENT` followed
by the live token, which had to be rotated. It was written by an agent holding
and citing the rule against it. See "Verify presence, never value" for why it
passed review, and why its control arm certified nothing.

## Gotchas

- **A silently-empty credential is still the default failure mode.** The
  exec-only *mechanism* is gone, but `${VAR:-}` interpolation in an MCP/plugin
  config yields an empty string for any credential that is absent, misnamed, or
  unset. The server starts, reports healthy, and degrades to an anonymous tier.
  **Check the consumer's authenticated identity, never its connection status.**
- **A running process keeps its env snapshot.** After a rotation, restart
  consumers — a green write proves nothing about live processes.
- **`fnox sync` caches**; a Doppler change does not propagate to the encrypted
  cache until you re-sync.
- **`-c` ADDS a config, it does not isolate one.** fnox merges
  `~/.config/fnox/config.toml` into every invocation — measured 2026-08-03,
  `fnox -c <scratchpad>/fnox.toml config-files` run from `/tmp` lists **both**
  files, and `check` counted 51 = the 50 user-root secrets plus 1 fixture key.
  `fnox config-files` is the arm that shows what is really loaded. A test that
  forgets this reaches live user state — that is how a mutation test wiped this
  host's config on 2026-08-01.
- **Shell startup got slower** — 50 credentials resolve on activation instead of
  4. ⚠️ The often-quoted "≈1.7s → ≈2.7s" is an **inherited figure this rewrite
  could not reproduce**: three consecutive `zsh -ic true` runs measured
  **0.99s / 1.33s / 3.12s** (control `zsh -f`, no rc: 0.058s, so the probe
  discriminates). The same-input variance is **larger than the claimed 1s
  delta**, so treat the number as unverified — the direction is real, the
  magnitude is not established, and the *before* can no longer be measured
  without reverting the config.
- **mise masks digits in `mise run` output** when a redacted value is short and
  all-digit — `[redacted][redacted]3` for 113. Read numbers from a recorded
  `rc=` or a non-`mise` invocation.
- **Unexplored fnox surface**, still worth a look: `fnox scan` (repo secret
  scan; 0 wiring here, against a control of 14 for `gitleaks` under the same
  command shape, `git grep -nI <term> -- '*.pkl'`), `fnox mcp`
  (secret-gated agent access without handing over the value), `fnox proxy`
  (destination-scoped credential brokering), and `fnox profiles` / `--profile`
  (the per-profile overlay #441 wanted, present in 1.32.0).

## See also

- `.claude/rules/secrets-out-of-the-shell-env.md` — the posture, the reversal,
  and the gates.
- `docs/rules-evidence/secrets-out-of-the-shell-env.md` — measurements, the wipe
  timeline, and this file's exec-era sections verbatim.
- `.claude/CLAUDE.md` § "Project doctor" — `doctor.toml` and the
  SessionStart check.
- `.claude/rules/do-not.md` — project invariants (#10 forbids a committed
  environment dump).
- `hk.pkl` (`betterleaks:272`, `no_env_dump:259`) and `hk-common.pkl`
  (`gitleaks:98`, `detect_private_key:74`) — the scanner steps. `hk.pkl` imports
  and spreads the common ones, so all four *run* from the project config; only
  two are *defined* there.

⚠️ **The upstream guide this file once adapted is gone.** It was cited as
`~/dev/honeymoon-period/docs/agents/doppler-fnox-keychain-environment-guide.md`
(813 lines, read 2026-07-20). That path does not exist as of 2026-08-03, nothing
matching `doppler-fnox-keychain*` exists anywhere under `~/dev` (control: the
same `find` locates `AGENTS.md`), and it is not in that repo's git history. This
file is now the only copy of what it taught.
