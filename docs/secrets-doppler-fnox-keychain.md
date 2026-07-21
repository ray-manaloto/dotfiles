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
| **Doppler** | shared authority — the value of record | project `dotfiles`, configs `dev` (46 secrets) and **`dev_personal` (50)** |
| **fnox** | declaration + resolution + optional encrypted cache | `~/.config/fnox/config.toml`; providers `keychain`, `age`, `doppler_dotfiles_dev_personal` |
| **macOS Keychain** | machine-local bootstrap vault | service **`mde-fnox`**, holds `DOPPLER_TOKEN` — the credential that unlocks everything else |
| **environment** | temporary process delivery | injected by `fnox exec` or shell activation; never the source of truth |

The chain: **Keychain → `DOPPLER_TOKEN` → Doppler → fnox declaration → process env.**

## Deltas from the honeymoon-period guide (this repo)

1. **`dev_personal` is the config fnox reads — not `dev`.** Every declaration
   maps to `providers.doppler_dotfiles_dev_personal` (`project = "dotfiles"`,
   `config = "dev_personal"`). A secret written to `dev` lands in Doppler and
   **never reaches the environment**. This is the single easiest mistake to make
   and it fails silently.
2. **The config's stated owner is gone.** `~/.config/fnox/config.toml` opens with
   *"Managed by `mde-py secrets bootstrap-config`. Do not edit by hand."* —
   but **`mde-py` is not on PATH** (verified 2026-07-20). `fnox edit` is the only
   remaining route. The header is stale; treat hand-editing as sanctioned until
   the planned skill replaces it.
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

## Gotchas

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
