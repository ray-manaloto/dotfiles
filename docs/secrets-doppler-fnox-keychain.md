# Secrets: Doppler, fnox, macOS Keychain, and environment variables

Adapted for **this repo** from
`~/dev/honeymoon-period/docs/agents/doppler-fnox-keychain-environment-guide.md`
(813 lines, read 2026-07-20). That guide is the conceptual source of truth; this
one records **what is actually wired on this Mac for `ray-manaloto/dotfiles`**,
the deltas, and the agent contract in the form this repo enforces.

> Placed at `docs/` and **not** `docs/agents/` deliberately: agnix applies a
> frontmatter rule to `**/agents/*.md`, and this is a prose guide, not an agent
> definition.

Eventual intent (Ray, 2026-07-20): migrate this into a **skill** that handles the
integration, and have this dotfiles repo manage the macOS environment. Neither
is done. Treat this file as the interim contract.

## The four layers

| layer | role | what it holds here |
|---|---|---|
| **Doppler** | shared authority — the value of record | project `dotfiles`, config **`dev_personal`** (49 secrets as of 2026-07-29) |
| **fnox** | declaration + resolution + optional encrypted cache | `~/.config/fnox/config.toml`; providers `keychain`, `age`, `doppler_dotfiles_dev_personal` |
| **macOS Keychain** | machine-local bootstrap vault | service **`mde-fnox`**, holds `DOPPLER_TOKEN` — the credential that unlocks everything else |
| **environment** | temporary process delivery | injected by `fnox exec` or shell activation; never the source of truth |

The chain: **Keychain → `DOPPLER_TOKEN` → Doppler → fnox declaration → process env.**

### The `env` mode — the gate on the last layer (added 2026-07-29)

A secret being *declared and resolvable* does **not** mean it reaches the shell.
Since 2026-07-27 this config is globally:

```toml
env = "exec"   # secrets stay OUT of the interactive shell
```

| `env` | interactive shell / `fnox export` | `fnox exec` | `fnox get` |
|---|:-:|:-:|:-:|
| `true` (fnox default) | yes | yes | yes |
| **`"exec"` (ours)** | **no** | yes | yes |
| `false` | no | no | yes |

Only secrets carrying an explicit per-secret `env = true` are exported. **Three
are** — `EXA_API_KEY`, `GITHUB_TOKEN`, `MISE_GITHUB_TOKEN` — chosen because their
consumers can *only* read the environment (an `.mcp.json` `${VAR}` interpolation
at MCP-server spawn; `gh` and `mise` reading their tokens).

**This is the single most likely cause of "the variable isn't set".** It is not a
sync failure. See the diagnosis recipe below before suspecting Doppler.

⚠️ **Any consumer that reads a credential from the environment needs either
`fnox exec --` or an explicit `env = true`.** A new one added without either gets
an **empty string**, not an error — see "Incidents".

## Deltas from the honeymoon-period guide (this repo)

1. **`dev_personal` is the config fnox reads — not `dev`.** Every declaration
   maps to `providers.doppler_dotfiles_dev_personal` (`project = "dotfiles"`,
   `config = "dev_personal"`). A secret written to `dev` lands in Doppler and
   **never reaches the environment**. This is the single easiest mistake to make
   and it fails silently.
2. **The config's stated owner is gone — and re-running it would be
   DESTRUCTIVE.** `~/.config/fnox/config.toml` opens with *"Managed by `mde-py
   secrets bootstrap-config`. Do not edit by hand."* but **`mde-py` is not on
   PATH** (re-verified 2026-07-29). `fnox edit` is the only route, so
   hand-editing is sanctioned.

   ⚠️ **The generator still exists in source and would wipe the config's most
   important fields.** `mde/secrets/manage.py` → `bootstrap_config()` rebuilds the
   file from a template whose per-secret line is:

   ```python
   lines.append(f'{key} = {{ provider = "{provider_name}", value = "{key}" }}')  # :318
   ```

   `provider` and `value` only — the function contains **zero** references to
   `env`, and preserves only `DOPPLER_TOKEN`. Measured against the live config:

   | field | present now | generator emits |
   |---|---:|---:|
   | global `env = "exec"` | 1 | **0** |
   | per-secret `env = true` | 3 | **0** |
   | `sync = { provider = "age", … }` | **49** | **0** |

   So a single `bootstrap-config` run silently reverts every secret to
   shell-exported — undoing the whole reason `env = "exec"` was adopted — and
   drops every offline age-encrypted copy. **Do not run it** until the generator
   preserves those fields. Tracked for the sibling repo in
   knowledge-base issue **#74**.
3. **fnox is already shell-activated** on this machine (3 `FNOX_*` vars present,
   `DOPPLER_TOKEN` resolving from Keychain). No bootstrap needed.
4. **An `age` provider is configured** (`recipients = ["age16djrq…"]`), so the
   encrypted-cache path in the source guide is available via `fnox sync`.

## Agent operating contract

Adopted from the source guide. These are hard limits, not preferences.

**An agent MAY**: resolve tool versions/paths · run `fnox config-files`,
`fnox doctor`, `fnox check` · list names only (`doppler secrets --only-names`,
`fnox list` **without** `--values`) · run dry-run sync/removal · ask a human to
type a value into a hidden prompt · invoke a narrow consumer and report a
non-secret result · report key name, scope, operation, timestamp, outcome.

**An agent MUST NOT**:
- ask for a secret to be pasted into chat;
- put a secret in a command argument, file, patch, fixture, or tool input;
- run `doppler secrets get` / `download`, `fnox get`, `fnox export`, or
  `fnox list --values`;
- **run `printenv` / `env` / `set` or shell tracing inside a secret-injected
  process** — this repo violated exactly that on 2026-07-20 by suggesting
  `fnox exec -- env | grep NVIDIA_API_KEY`; see "Verify presence" below for the
  compliant form;
- use `security … -w` / `-g` to display a Keychain value;
- read `~/.doppler`, `~/.config/fnox/config.toml`, the login Keychain DB, an age
  private key, or a `.env` for plaintext;
- add `--yes`/`--force` to a deletion without explicit authorization;
- treat a successful write as a completed rotation.

**Human-only**: creating accounts · passwords/MFA/OAuth consent · viewing a
provider's one-time credential · **typing the value into the hidden prompt** ·
approving paid/production scope · confirming destructive deletion.

Even *names* disclose architecture — summarize counts in public logs, not
inventories.

## Add a secret (the procedure this repo uses)

1. Confirm key name, config (**`dev_personal`**), consumer, scope, rotation
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
   KEY_NAME = { provider = "doppler_dotfiles_dev_personal", value = "KEY_NAME" }
   ```

7. Optional offline cache: `fnox sync KEY_NAME`.
8. Run a narrow consumer health check; report only the non-secret result.

**Never**: `doppler secrets set KEY 'value'` (argv/history) or
`echo 'value' | doppler secrets set KEY` (plaintext through the tool call).

## Verify presence, never value

```sh
fnox exec -- zsh -c '[[ -v KEY_NAME ]] || exit 20; print "credential is present"'
```

Presence is not correctness. Correctness needs a narrow provider health check
whose response contains no secret (an identity endpoint returning an account id,
or a minimal request returning an expected status).

Never record token prefixes/suffixes, hashes of low-entropy secrets, auth
headers, raw env dumps, or the contents of a secret-bearing config.

## Diagnose "the variable isn't set" — in this order

Work down the layers. Each step is contract-compliant (no value is read or
printed), and each **discriminates**, so a pass genuinely rules that layer out.

```sh
# 1. Is fnox itself healthy?  Expect: "Configuration is healthy" + counts.
fnox check

# 2. Is the secret DECLARED?  names only, never --values.
fnox list | grep KEY_NAME

# 3. Does it resolve to a process?  (present here + absent in step 4 == env="exec")
fnox exec -- zsh -c '[[ -v KEY_NAME ]] && print present || print ABSENT'

# 4. Is it in the plain interactive shell?
zsh -c '[[ -v KEY_NAME ]] && print present || print ABSENT'

# 5. Is the offline age copy stale vs Doppler?  dry-run reveals no values.
fnox sync --dry-run -p age KEY_NAME
#   "Would sync 1 secrets … KEY_NAME (from doppler_…)"  -> a copy would change
#   "No secrets to sync"                                -> nothing to do / unknown key
```

**Reading the result:**

| step 3 | step 4 | meaning |
|---|---|---|
| present | **ABSENT** | **`env = "exec"` working as designed.** Consumer must use `fnox exec --`, or the secret needs `env = true`. *Not a bug.* |
| ABSENT | ABSENT | declaration or provider problem — go back to steps 1–2 |
| present | present | it has `env = true`; if a consumer still sees nothing, the consumer is the fault |

**Always control-arm the negative.** A `0`/ABSENT result is worthless until the
same command shape returns present for something you *know* is set:

```sh
zsh -c '[[ -v HOME ]] && print "control ok: [[ -v ]] works"'
```

A 2026-07-29 session reported a variable "set, 43 chars" and later "unset" from
two different probes in the same session. The control arm is what settled it.

⚠️ **`env | grep` is forbidden inside a secret-injected process** (see the
contract above). Use `[[ -v VAR ]]`, which reveals presence without the value.

## Evidence record

```text
Operation: add | update | rotate | delete | sync
Key: <authorized name>
Authority: Doppler dotfiles/dev_personal | Keychain mde-fnox/<account>
Consumer: <program>
Value observed by agent: no
Name/presence check: pass | fail
Consumer health check: <safe result>
Timestamp: <ISO-8601>
```

## Incidents

### 2026-07-29 — Context7 MCP ran anonymous for days; nothing noticed

The Upstash context7 plugin interpolates `"Authorization": "${CONTEXT7_API_KEY:-}"`.
That secret is exec-only, so the header resolved to **empty** and the server used
the anonymous tier — while reporting `✓ connected` the whole time.

What made it invisible:

- **`${VAR:-}` substitutes an empty string instead of failing.** Silent by
  construction.
- **Doppler → fnox was perfectly healthy**, so every instinct to blame "the sync"
  was wrong. `fnox check` green; the value matched Doppler exactly.
- **The opt-in list was drawn before the consumer existed.** The three `env = true`
  entries were chosen 2026-07-27 for the three consumers that existed then; the
  plugin arrived 2026-07-29 and nothing re-checked the list.

Generalisation: **a new env-var consumer is a new opt-in decision, and nothing
enforces it.** Tracked as dotfiles issue **#418** (project-doctor SessionStart
check: every `${VAR}` interpolated by an MCP/plugin config must be `env = true`).

### Contract breaches by an agent in that same session — recorded, not excused

While diagnosing the above, the agent violated the operating contract three ways:

1. **Ran `fnox get` and `doppler secrets get`** — both explicitly on the MUST NOT
   list — to sha256-compare the two values. Output was truncated to 12 hex chars,
   never the value, but the commands themselves are forbidden.
2. **Interpolated a live key into `curl -H "Authorization: $K"`** — a secret in a
   command argument, which the contract forbids because argv is observable.
3. Reached for `env | grep` on secret names (permitted here only because the
   variables in question were *absent*; the compliant form is `[[ -v VAR ]]`).

None of it reached a tracked file or the transcript, and the endpoint was the
credential's legitimate vendor. It was still avoidable: **`fnox sync --dry-run -p age`
answers the staleness question without reading any value**, and `[[ -v ]]` answers
presence. Both are in the MAY list. The compliant recipe is now written above so
the next session reaches for it first.

## Gotchas

- **A silently-empty credential is the default failure mode.** `${VAR:-}` and
  `${VAR}` interpolation in MCP/plugin configs yield an empty string when the var
  is exec-only. The server starts, reports healthy, and degrades to an anonymous
  or unauthenticated tier. Check the *consumer's* authenticated identity, never
  its connection status.
- **A running process keeps its env snapshot.** After a rotation, restart
  consumers — a green write proves nothing about live processes.
- **`fnox sync` caches**; a Doppler change does not propagate to the encrypted
  cache until you re-sync.
- **`fnox scan`** searches the repo for potential secrets — complements the
  `gitleaks` step already in `hk.pkl`; currently unused here.
- **`fnox mcp`** starts an MCP server for *secret-gated AI agent access* — the
  supported way to give an agent gated use of a credential without handing it
  the value or a shell. Relevant to the planned research agent; unexplored.

## See also

- `~/dev/honeymoon-period/docs/agents/doppler-fnox-keychain-environment-guide.md`
  — the full 813-line conceptual guide this adapts.
- `.claude/rules/do-not.md` — project invariants.
- `hk.pkl` — the `gitleaks` and `detect_private_key` steps.
