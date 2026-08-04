# Bitwarden Secrets Manager — primary-source evaluation as a secrets backend

**Date:** 2026-08-03
**Source discipline:** PRIMARY ONLY — `bitwarden.com/help/**`, `bitwarden.com/pricing/**`,
`github.com/bitwarden/{server,clients,sdk-sm}`, `bws` docs and `--help`.
Third-party comparison blogs / news write-ups are BANNED for this sweep; any fact
that exists only there is marked `UNVERIFIED (secondary-only)`.

**Status:** COMPLETE.

## Verdict at a glance

| Q | Answer |
|---|---|
| 1 Free tier | 2 users / 3 projects / 3 machine accounts / unlimited secrets. SM has its own free subscription. 3 primary pages agree on numbers; they **contradict each other on self-hosting**. |
| 2 Licensing | SM **server** = AGPL 3.0 (FOSS). **`bws` CLI + `bitwarden-sm` SDK = proprietary** Bitwarden SDK EULA. Self-host = Enterprise licence file. |
| 3 Machine accounts | **Scoped per PROJECT** (not per secret), read or read/write. A strict subset is achievable at project granularity. |
| 4 `bws run` | **EXISTS** — env injection, plus `--no-inherit-env` and `--project-id`. Not retrieval-only. |
| 5 Offline | **No offline mode, no secret cache.** State file caches auth tokens only. Unreachable service → nonzero exit, no secrets. |
| 6 Agent surface | **`bitwarden/agent-access` (Apache-2.0, `aac` CLI)** + `bitwarden/mcp-server` (GPL-3.0). Both target the **password manager**, not SM. No Claude Code plugin. |
| 7 **Fail-open?** | **REFUSES** on bad project id, bad/expired token. ⚠️ One rc=0 defect: token with no org → exit 0, command never runs, no secrets emitted. |

**Headline for the decision at hand:** on the one property the replacement CLI
was specified to add — converting fnox's silent scope-widening fail-open into a
refusal — `bws` already refuses, structurally (Q7). The costs are that the
client is **not FOSS**, there is **no offline operation**, and the agent-scoping
story you'd actually want (`agent-access`) is on the **other** Bitwarden product
and in **early preview**.

## Q1 Free tier, exactly

Source: <https://bitwarden.com/products/secrets-manager/> (pricing block on the
product page).

| Tier | Users | Projects | Machine accounts | Secrets |
|---|---|---|---|---|
| **Free** | "Up to 2 users" | "Up to 3 projects" | "Up to 3 machine accounts" | unlimited |
| Teams ($6/user/mo) | unlimited | unlimited | "Up to 20 machine accounts, $1 per additional machine account" | unlimited |
| Enterprise ($12/user/mo) | unlimited | unlimited | "Up to 50 machine accounts, $1 per additional machine account" | unlimited |

Annual rates, USD, excl. tax.

⚠️ `https://bitwarden.com/help/about-secrets-manager/` returns **HTTP 404** — the
help-doc counterpart had to be located elsewhere.

### Cross-check against the help docs — numbers AGREE

<https://bitwarden.com/help/secrets-manager-plans/>:

| | Free | Teams | Enterprise |
|---|---|---|---|
| Users | "Up to 2 users" | "Unlimited users" | "Unlimited users" |
| Projects | "Up to 3 projects" | "Unlimited projects" | "Unlimited projects" |
| Machine accounts | "Up to 3 machine accounts" | "Up to 20 … extra accounts billed per account" | "Up to 50 … extra accounts billed per account" |
| Secrets | "Unlimited secret storage" | unlimited | unlimited |

<https://bitwarden.com/help/secrets-manager-faqs/> states it in one sentence:

> "Bitwarden Secrets Manager offers a free subscription with unlimited secret
> storage and **up to 2 users, 3 projects, and 3 machine accounts**."

**Three independent primary pages agree on the numbers** (product pricing block,
plans help page, FAQ). No disagreement on limits.

### Is Secrets Manager included in the free plan?

**Yes — it is its own free subscription, not a Password Manager add-on you must
pay for.** `secrets-manager-quick-start` confirms the free path exists at signup:
*"If you are on the Free plan, select **Submit**. If you are on an upgraded plan,
enter the desired number of **Subscription seats**…"* SM is subscribed to
separately from Password Manager but has its own free tier.

### ⚠️ The help docs DO disagree — on self-hosting

- `secrets-manager-plans/`: **"Coming Soon: Self-host option"**, listed against
  all three tiers — i.e. not available anywhere.
- `secrets-manager-faqs/`: **"Enterprise organizations can self-host Bitwarden
  Secrets Manager alongside their existing self-hosted installations."**
  Requires *"minimum server version 2023.10.0 and a new license file from your
  cloud organization."*

These cannot both be current. The FAQ is the more specific and more plausible
(it cites a concrete minimum server version, 2023.10.0, which is ~3 years old);
the plans page's "Coming Soon" reads as stale marketing copy. **Treat
self-hosting as Enterprise-gated and requiring a cloud-issued licence file**, and
treat the plans page as out of date — but this is a documented contradiction in
Bitwarden's own help corpus, not a settled fact.

### Free-tier fit for the use case at hand

3 machine accounts × 3 projects is the entire scoping budget on free. Since
machine-account scope is per-project (Q3), the free plan permits **at most 3
disjoint blast radii**. Adequate for a single developer host with, say,
`agent` / `devcontainer` / `ci` splits; nothing beyond that without paying $6/user/mo.

## Q2 Licensing

Bitwarden's licensing really is mixed. Read from the LICENSE files themselves,
not from summaries.

### Server (`bitwarden/server`) — Secrets Manager code is **AGPL 3.0**

`LICENSE.txt` (verbatim):

> Source code in this repository is covered by one of two licenses: (i) the GNU
> Affero General Public License (AGPL) v3.0 (ii) the Bitwarden License v1.0. The
> default license throughout the repository is AGPL v3.0 unless the header
> specifies another license. **Bitwarden Licensed code is found only in the
> /bitwarden_license directory.**

`bitwarden_license/README.md`: *"All source code under this directory is licensed
under the Bitwarden License Agreement."*

`bitwarden_license/src` contains exactly: `Commercial.Core`,
`Commercial.Infrastructure.EntityFramework`, `Scim`, `Services`, `Sso`.
**No `SecretsManager` directory.** The Secrets Manager server code lives at
`src/Core/SecretsManager` and `src/Api/SecretsManager` — *outside*
`bitwarden_license/`, therefore **AGPL 3.0**. (Verified by listing both trees via
`gh api repos/bitwarden/server/contents/...`.)

`LICENSE_FAQ.md` adds that the Bitwarden License is *"source available"*:
*"provides users access to product source code for non-production purposes such
as development and testing, but requires a paid subscription for production use"*,
and states plainly *"The Bitwarden License does not qualify as an open source
license under the OSI definition."* It also notes the Api module includes
`Commercial.Core` by default, disable-able with
`` /p:DefineConstants="OSS" ``.

### `bws` CLI + SDK (`bitwarden/sdk-sm`) — **NOT open source**

- GitHub license metadata for `bitwarden/sdk-sm`: `spdx_id: NOASSERTION`.
- `sdk-sm/LICENSE` is the **"BITWARDEN SOFTWARE DEVELOPMENT KIT LICENSE
  AGREEMENT, Version 1, 17 March 2023"** — a bespoke proprietary EULA. It
  restricts use to a *"Compatible Application"*, defined as software that
  *"connects to and interoperates with a current version of the Bitwarden server
  products distributed by the Company"* and complies with Bitwarden's acceptable
  use policy. **This is the licensing controversy referenced in the brief**: the
  SDK is source-available under a bespoke agreement, not GPL/AGPL, and the
  Compatible-Application clause is what makes it unusable for a
  non-Bitwarden-server client.
- `crates/bws/Cargo.toml` sets `license-file.workspace = true`; the workspace
  `Cargo.toml` sets `license-file = "LICENSE"` — i.e. **the `bws` binary itself
  ships under that same SDK EULA**, not GPL. `bws` version in-tree: **2.1.0**.

### `bitwarden/sdk-internal` — dual GPL-3.0 **OR** SDK License v2.0

Materially relevant, and easy to miss: `sdk-sm`'s workspace now pulls
`bitwarden-core`, `bitwarden-crypto`, `bitwarden-sm`, `bitwarden-cli`,
`bitwarden-auth` as **git dependencies on `bitwarden/sdk-internal`** (pinned rev
`15ab4caf17fc7b9f1c80a1141d4341dd80432562`). That repo's `LICENSE` says:

> Source code in this repository is covered by one of two licenses: (i) the GNU
> General Public License (GPL) v3.0 (ii) the BITWARDEN SOFTWARE DEVELOPMENT KIT
> LICENSE v2.0. The default license throughout the repository is **your choice of
> GPL v3.0 OR BITWARDEN SOFTWARE DEVELOPMENT KIT LICENSE** unless the header
> specifies another license. Anything contained within a directory named
> bitwarden_license is covered solely by the BITWARDEN SOFTWARE DEVELOPMENT KIT
> LICENSE.

So the **general SDK crates were relicensed to a GPL-3.0 dual option** in
`sdk-internal` (v2 of the SDK licence), while the `sdk-sm` repo wrapper —
including the `bws` crate — still carries the **v1 EULA with no GPL option**.
Anyone reasoning about "the SDK licensing controversy" from 2023-era material is
reading a state that has partially moved.

⚠️ **BUT — the Secrets Manager crate is carved back out.** `sdk-internal`'s
LICENSE says *"Anything contained within a directory named bitwarden_license is
covered solely by the BITWARDEN SOFTWARE DEVELOPMENT KIT LICENSE."* And
`bitwarden-sm` — the crate that actually implements every SM operation
(`list_by_project`, `get_by_ids`, `sync`) — lives at
**`bitwarden_license/bitwarden-sm/`**, alongside `bitwarden-commercial-vault`
and `bitwarden-pam`. `crates/` holds the GPL-dual-licensed general crates
(`bitwarden-core`, `bitwarden-crypto`, `bitwarden-cli`, `bitwarden-auth`, …).

**Net: the entire Secrets Manager client stack is proprietary.** The GPL dual
option covers the generic plumbing; every SM-specific line is SDK-License-only.
Verified by `ls bitwarden_license/` on a shallow clone of `bitwarden/sdk-internal`
(control: `crates/` listing returns 30+ non-SM crates, so the probe distinguishes
the two trees).

### Clients (`bitwarden/clients`)

`spdx_id: NOASSERTION`; per `LICENSE_FAQ.md`, *"The core password management code
for individual password vaults, including Desktop, Web, Browser, Mobile, and CLI
versions, is available under the GPL 3.0 license."* Not the Secrets Manager
surface — the SM CLI is `bws`, in `sdk-sm`.

### Summary — what is and is not FOSS

| Component | License | FOSS? |
|---|---|---|
| Secrets Manager **server** code (`src/{Core,Api}/SecretsManager`) | AGPL 3.0 | **YES** |
| `bitwarden_license/**` (SSO, SCIM, Commercial.Core) | Bitwarden License v1.0 | NO — source-available, production use needs a paid subscription |
| **`bws` CLI** (`sdk-sm/crates/bws`) | Bitwarden SDK License Agreement v1 | **NO** — bespoke EULA, Compatible-Application restriction |
| `sdk-sm` Rust/py/wasm SDK wrappers | Bitwarden SDK License v1 | NO |
| `sdk-internal` crates (incl. `bitwarden-sm`) | GPL-3.0 **OR** SDK License v2.0 | **YES, at your choice** |
| Password-manager clients | GPL 3.0 | YES |

**Self-hosting Secrets Manager gated to enterprise? YES — by *licence file*, not
by source licence.** The distinction matters and is easy to garble:

- The SM **server source** is AGPL 3.0 and sits outside `bitwarden_license/`, so
  it is *not* source-gated the way SSO and SCIM are. You may legally build and
  run it.
- But `secrets-manager-faqs` states *"Enterprise organizations can self-host
  Bitwarden Secrets Manager alongside their existing self-hosted installations,"*
  requiring *"a new license file from your cloud organization"* — i.e. the
  **feature is unlocked at runtime by an Enterprise-tier licence**, and
  `secrets-manager-plans` still says "Coming Soon: Self-host option" (see Q1 for
  the contradiction).
- And the **client is proprietary regardless**: `bws` and `bitwarden-sm` are
  SDK-License-only, so even a fully self-hosted AGPL server is talked to by a
  non-FOSS CLI whose EULA restricts use to a "Compatible Application"
  interoperating with *"Bitwarden server products distributed by the Company."*

**Net for a FOSS-preference evaluation: Secrets Manager is not a FOSS-viable
stack.** The server half is AGPL; the half you actually run on your laptop is
not, and there is no open-source `bws` alternative in Bitwarden's own repos. The
one Apache-2.0 component in this sweep (`agent-access`, Q6) is on the password
manager, not SM.

## Q3 Machine accounts — scoping

Source: <https://bitwarden.com/help/machine-accounts/>

- Definition (verbatim): *"Machine accounts represent non-human machine users,
  like applications or deployment pipelines, that require programmatic access to
  a discrete set of secrets."*
- **Scope unit = PROJECT, not secret.** Configuration asks you to *"type or
  select the name of the project(s) that this machine account should be able to
  access."*
- Two permission levels per assigned project:
  - *"Can read"* — retrieve secrets from assigned projects.
  - *"Can read, write"* — retrieve/edit secrets in assigned projects, create new
    secrets in assigned projects, or create new projects.
- Access token grants *"programmatic access to, and the ability to decrypt,
  edit, and create secrets"* for that machine account.
- The help docs do **not** document per-secret scoping — only whole projects.

**Answer to "can it be scoped to a strict subset?": YES, at project
granularity.** A machine account holding one project's grant structurally cannot
decrypt secrets in other projects. Sub-project (per-secret) scoping is
`UNVERIFIED` / apparently unsupported — tried the machine-accounts help page,
which enumerates only project selection.

⚠️ Free-tier interaction: 3 projects max means at most 3 disjoint blast radii
before you must pay.

## Q4 `bws` injection semantics

Source: <https://bitwarden.com/help/secrets-manager-cli/>

**`bws run` EXISTS.** Verbatim: *"The `run` command runs commands with secrets
injected as environment variables, enabling you to easily adapt existing
development projects and scripts to use secure secrets management."*

Documented forms:

```
bws run -- 'npm run start'
bws run --project-id <PROJECT_ID> -- <command>
bws run --shell fish -- <command>
bws run --no-inherit-env -- <command>
bws run --uuids-as-keynames -- <command>
```

So `bws` is **not** retrieval-only: it has the `infisical run` / `sops exec-env`
shape, plus `--no-inherit-env` (drop the parent environment — a real
confinement knob that fnox's `env = true` posture does not offer) and
`--project-id` to bound which secrets are injected. No shell-interpolation
wrapper is required, so the transcript-leak shape (`echo "$SECRET"`) is
avoidable by construction.

Retrieval commands also exist: `bws secret {create,delete,edit,get,list}`,
`bws project {create,delete,edit,get,list}`, `bws config {server-base,state-dir,--profile,--config-file}`.

## Q5 Offline behaviour

**There is no offline mode and no secret cache.** The only on-disk persistence is
the **state file**, and it caches *authentication tokens*, not secret values.

Source: <https://bitwarden.com/help/secrets-manager-cli/> (state-files section),
verbatim:

> "State files are fully encrypted files that store authentication tokens and
> additional relevant data."
> "State files can reduce rate limiting while authenticating, using stored tokens
> for authentication."
> "The state directory default location is `~/.config/bws/state`."
> "If your workflow uses many separate sessions (where each use of an access token
> to authenticate constitutes a 'session') to make requests from the same IP
> address in a short span of time, you may encounter rate limits."

Opt-out: set `state_opt_out` to `true`/`1` in `~/.config/bws/config`; set the
directory with `bws config state-dir /absolute/path` (absolute path required).

Source-side confirmation (`sdk-sm` @ HEAD): `crates/bws/src/state.rs` only
computes a path (`~/.config/bws/state/<access_token_id>`) and `create_dir_all`s
it; `crates/bws/src/config.rs` has exactly two state keys — `state_dir` and
`state_opt_out`. A grep of `crates/bws/src/{cli,config}.rs` for
`state|cache|offline` returns **only** those two keys — no cache TTL, no offline
flag, no stale-read path.

**When the service is unreachable:** the `reqwest` transport error becomes
`Err` at `bitwarden-api-base`, propagates through `?`, and `bws` exits nonzero
with **no secrets**. Consistent with Q7 — it refuses rather than degrading. Note
`main.rs:87-102` treats a *state-file* failure as recoverable (prints
`"Warning: … Attempting to continue without using state"` and continues with
`state_file = None`), which affects auth caching only, never secret retrieval.

**Operational consequence:** every `bws run` is a live network round-trip. A
laptop offline, or Bitwarden's service down, means the wrapped command does not
run. That is the safe direction, but it is a hard availability dependency that
fnox's local-file/keychain reads do not have.

## Q6 Agent / plugin surface

**Answer: YES — and this is the most under-appreciated finding of the sweep.**
Bitwarden ships *two* separate agent-facing products, neither of which is
Secrets Manager.

### Control arm (run first, per `probes-need-a-control-arm.md`)

Method: `gh search repos --owner=bitwarden --limit 100 --json name,description`,
then substring-filter the combined name+description.

| Arm | Term | Result |
|---|---|---|
| Target | `mcp` / `agent` / `claude` / `model context` | **3 matches** — `mcp-server`, `agent-access`, `key-connector` |
| **Control** | `sdk` (known present — `sdk-sm` was already read this session) | **14 matches** — `sdk-sm`, `sdk-internal`, `sdk-go`, `sdk-swift`, `agent-access`, 9 × `passwordless-*` |

64 repos enumerated total. The control returns a large non-zero set by the same
method, so the probe discriminates — the target result is a real positive, not a
blind search. (No absence is being claimed here anyway; both arms found things.)

### 1. `bitwarden/agent-access` — **Apache-2.0**, `aac` CLI

<https://github.com/bitwarden/agent-access> · created 2025-12-19 · 121 stars ·
license `Apache-2.0` (the **only genuinely OSI-open** component in this whole
sweep).

README verbatim:

> "Agent Access allows users to provide credentials from their password manager to
> remote systems, **without exposing their entire vault**. Agent Access creates an
> end-to-end encrypted tunnel between a remote system and a credential provider."
>
> "Agent Access is an open protocol, CLI tool, and SDK that can be implemented
> directly into agents or custom software. While Agent Access has been built and
> developed by the team at Bitwarden, **it is open for any credential provider**…"

And, directly on point for the transcript-leak concern:

> ⚠️ "This project is in an **early preview stage**. APIs and protocols are subject
> to change. We do not recommend inputting sensitive credentials directly into LLMs
> or AI agents (any unknown software, really).
>
> For LLM's specifically, where possible **use environment injection (e.g. `aac
> run`) to pass secrets to processes without exposing them in recorded context**."

Shape: `aac listen` on the human's machine (holds the vault, interactive
`/unlock`, mints a **pairing token**) ↔ `aac connect` / `aac run` on the remote
/ agent side. Per-request, per-domain credential release —
`aac connect --domain github.com --provider bitwarden --output json`. Crates:
`ap-cli`, `ap-client`, `ap-relay`, `ap-relay-protocol`, `ap-noise` (Noise-protocol
tunnel), `ap-uniffi`. Protocol spec in-repo at `protocol-v0.md`.

Bindings/examples shipped: Python (UniFFI), JS/WASM, Swift (UniFFI), Rust
listener + remote, shell, **GitHub Action**, and **`examples/skills/`** — an
agent *skill* directory. The README documents installing it as an **OpenClaw
skill**:

```shell
curl -fsSL "https://raw.githubusercontent.com/bitwarden/agent-access/main/examples/skills/agent-access/SKILL.md" \
  -o ~/.openclaw/skills/agent-access/SKILL.md --create-dirs
```

⚠️ **No Claude Code plugin is documented** — the shipped skill targets OpenClaw's
`~/.openclaw/skills/` path. The `SKILL.md` format is portable, but a Claude Code
integration is not something Bitwarden ships or documents. `UNVERIFIED` whether
the skill works unmodified under `.claude/skills/`; not tested.

⚠️ **Agent Access reads the PASSWORD MANAGER vault (`bw` CLI), not Secrets
Manager.** `--provider bitwarden` is the `bw` CLI provider; `--provider example`
is a built-in demo. No `bws` / Secrets Manager provider is documented in the
README. So it is **not** an agent front-end for the SM backend this report is
evaluating — it is a parallel product on the other vault.

### 2. `bitwarden/mcp-server` — **GPL-3.0**

<https://github.com/bitwarden/mcp-server> · created 2025-05-23 · 217 stars ·
`@bitwarden/mcp-server` on npm. Two interfaces: **vault management via the `bw`
CLI**, and **organization administration via the Bitwarden Public API**
(collections, members, groups, policies, audit logs, subscriptions).

Its own README carries a blunt warning worth quoting in full before anyone
considers it:

> "When you grant an AI assistant access to this server, you are providing the
> ability to: Read vault items including passwords, secure notes, and sensitive
> data … **Expose credentials and vault contents through AI responses**"
>
> "Never: Deploy this server to cloud hosting … Grant access to untrusted AI
> clients or services"

Configuration is documented for **Claude Desktop** ("Option 1 … Recommended") —
Claude *Desktop*, not Claude Code.

⚠️ **The MCP server's feature list contains no Secrets Manager tools.** Every
listed capability is password-manager vault or org-admin. So there is no MCP
path to SM secrets.

⚠️ Note also that this server is the **opposite** of the scoping property the user
wants: it hands an assistant the whole vault, by design.

### Agent-scoped identity primitives beyond machine accounts

- **Machine accounts** (Q3) — project-scoped, for SM.
- **Agent Access pairing tokens** — per-session, per-domain, human-in-the-loop
  release, on the password-manager vault. Genuinely a *different and stronger*
  primitive (the agent never holds a long-lived credential), but on the wrong
  product for an SM-backed design, and **early preview** by Bitwarden's own label.
- `bitwarden/key-connector` — despite "agent" in its description ("An agent that
  stores and provides cryptographic keys to Bitwarden clients"), this is
  self-hosted key custody for SSO, not an AI-agent primitive. Not relevant.

## Q7 DECISIVE — fail-open vs refusal

Method: shallow-cloned `bitwarden/sdk-sm` (bws 2.1.0) and `bitwarden/sdk-internal`
and read the actual call chain. `bws` is not installed on this host
(`which bws` → not found), so this is **source-verified, not runtime-probed**.

### Verdict per input

| Bad input | Behaviour | Confidence |
|---|---|---|
| **Nonexistent / unauthorized project id** (`--project-id`) | **REFUSES** — nonzero exit, no secrets emitted | source-verified |
| **Invalid / unparseable access token** | **REFUSES** — nonzero exit | source-verified |
| **Expired / rejected access token** | **REFUSES** — nonzero exit | source-verified |
| **Valid token not associated with an organization** | ⚠️ **rc=0, command never runs** — a distinct rc-lying defect, but **no secrets emitted** | source-verified |

### The chain (project-id path)

`crates/bws/src/command/run.rs:62-74`:

```rust
let res = if let Some(project_id) = project_id {
    client.secrets()
        .list_by_project(&SecretIdentifiersByProjectRequest { project_id }).await?
} else {
    client.secrets()
        .list(&SecretIdentifiersRequest { organization_id: organization_id.into() }).await?
};
```

**There is no fallback branch.** If `--project-id` is supplied, the org-wide
`list` is never reached. This is the structural difference from fnox: a bad scope
argument cannot silently widen to "everything", because the widened call is in the
*other* arm of the `if`.

Error propagation, bottom-up:

1. `crates/bitwarden-api-base/src/request.rs:57-69` — the shared response
   processor returns `Err(ResponseContent { status, message })` for **any**
   `status.is_client_error() || status.is_server_error()`. 4xx/5xx are errors,
   not empty successes.
2. `bitwarden_license/bitwarden-sm/src/secrets/list.rs` —
   `list_secrets_by_project` calls `get_secrets_by_project(input.project_id)`
   with `?`; no `unwrap_or_default`, no empty-vec fallback.
3. `run.rs` — `.await?` propagates to `main`.
4. `crates/bws/src/main.rs:23` — `async fn main() -> Result<()>`; an `Err` from
   `process_commands()` is printed by `color_eyre` and Rust exits **nonzero**.

So a 403/404 on an unknown or unpermitted project produces a nonzero exit with
**zero secrets in the child environment**. **REFUSES.**

### Access token handling

`main.rs:63-67`:

```rust
let access_token = match cli.access_token {
    Some(key) => key,
    None => bail!("Missing access token"),
};
let access_token_obj: AccessToken = access_token.parse()?;
```

Absent token → `bail!` (nonzero). Malformed token → `parse()?` (nonzero).
`main.rs:107-113` — `login_access_token(...).await?` — a rejected/expired token
errors out of the login call before any secret is fetched. **REFUSES.**

### ⚠️ The one rc=0 defect found — `main.rs:115-121`

```rust
let organization_id = match client.get_access_token_organization() {
    Some(id) => id.into(),
    None => {
        error!("Access token isn't associated to an organization.");
        return Ok(());
    }
};
```

A token that authenticates but carries no organization claim causes `bws` to log
to stderr and **return `Ok(())` → exit code 0**, *before* the command dispatch.
For `bws run -- ./deploy.sh`, that means **the wrapped command never executes and
`bws` reports success**. A CI step would go green having done nothing.

Classify precisely: this is **not** a secrets fail-open (nothing is decrypted or
emitted, so it cannot leak), but it **is** an rc-lies-about-outcome path, and it
is exactly the shape a refusal-enforcing wrapper must still guard. Any adoption
should treat "token has no org" as a case to detect explicitly rather than trust
`bws`'s exit code for.

### Two things NOT verified

- **Does the server return 404/403 or an empty 200** for a project id the machine
  account cannot see? The client refuses on 4xx, but an empty-200 would instead
  produce "runs the child with zero secrets, propagating the child's exit code"
  — still no leak, still no widening, but not a hard refusal. `UNVERIFIED`: not
  runtime-probed (no `bws`, no Bitwarden org on this host) and the controller
  authorization path in `bitwarden/server` was not read to completion.
- **No runtime probe was run at all.** Every verdict above is read from source at
  the pinned revisions (`sdk-sm` @ HEAD, `sdk-internal` @ rev
  `15ab4caf17fc7b9f1c80a1141d4341dd80432562` as pinned by `sdk-sm`'s workspace).

### Contrast with fnox 1.32.0

fnox `exec -P <nonexistent>` returns all 49 secrets at rc=0 with no stderr — the
scope argument is silently discarded and the call widens to everything. `bws run
--project-id <nonexistent>` cannot do that: the widening call lives in a branch
the code does not take, and a 4xx becomes a nonzero exit. **On the specific
property the replacement CLI was specified to add, `bws` already has it.**

## Open gaps / UNVERIFIED

Listed so nobody mistakes an unasked question for a negative answer.

1. **No runtime probe of `bws` was performed.** `which bws` → not found on this
   host, and there is no Bitwarden org/token here. Every Q7 verdict is
   **source-verified at a pinned revision**, not observed. Before adopting, run
   the real arms: `bws run --project-id 00000000-0000-0000-0000-000000000000 --
   env` and an expired-token arm, and read `echo "rc=$?"` from a file (never a
   piped tail).
2. **Server-side response for an unauthorized project id** — 403/404 vs empty
   200 — not read to completion in `bitwarden/server`'s SM controllers. The
   client refuses on 4xx; an empty 200 would instead run the child with zero
   secrets. Neither leaks, but only the first is a hard refusal.
3. **Self-hosting availability is genuinely contradictory** between
   `secrets-manager-plans` ("Coming Soon") and `secrets-manager-faqs`
   ("Enterprise organizations can self-host"). Not resolvable from the help
   corpus alone.
4. **`bws --help` was not captured firsthand** (binary not installed); the flag
   and subcommand list is from the CLI help page plus `crates/bws/src/cli.rs`.
   The two agree on `--project-id`, `--no-inherit-env`, `--shell`,
   `--uuids-as-keynames`, `state_dir`, `state_opt_out`.
5. **Whether `agent-access`'s `SKILL.md` loads under Claude Code** (vs its
   documented `~/.openclaw/skills/` target) is untested.
6. **`bitwarden/agent-access` has no documented Secrets Manager provider** —
   only `--provider bitwarden` (the `bw` CLI) and `--provider example`. Whether
   a `bws` provider is planned was not researched.

**Banned-source discipline:** no third-party comparison blog, news write-up, or
aggregator was consulted for any claim above. Every fact carries a
`bitwarden.com/*` URL, a `github.com/bitwarden/*` URL, or a file:line from a
shallow clone of a Bitwarden repo. No claim in this report is marked
`UNVERIFIED (secondary-only)` because none was sourced that way — gaps were left
as gaps instead.

**Revisions pinned:** `bitwarden/sdk-sm` @ HEAD of `main` (bws 2.1.0);
`bitwarden/sdk-internal` @ `15ab4caf17fc7b9f1c80a1141d4341dd80432562` (the rev
`sdk-sm`'s workspace `Cargo.toml` pins); `bitwarden/server` read via
`gh api .../contents` at `main`. Sweep date 2026-08-03.

## GitHub repos touched

- [bitwarden/server](https://github.com/bitwarden/server) — `LICENSE.txt`, `LICENSE_FAQ.md`, `bitwarden_license/README.md`, and directory listings of `src/` and `bitwarden_license/src/` to prove Secrets Manager code is AGPL and outside the commercial tree.
- [bitwarden/sdk-sm](https://github.com/bitwarden/sdk-sm) — `LICENSE` (SDK EULA v1), workspace + `crates/bws/Cargo.toml` for the `bws` licence, and `crates/bws/src/{main,state,config,cli}.rs` and `src/command/run.rs` for the Q4/Q5/Q7 semantics.
- [bitwarden/sdk-internal](https://github.com/bitwarden/sdk-internal) — `LICENSE` (GPL-3.0 OR SDK v2), `bitwarden_license/bitwarden-sm/**` (the SM crate is carved back out as proprietary), and `crates/bitwarden-api-base/src/request.rs` for the 4xx/5xx → `Err` rule that decides Q7.
- [bitwarden/clients](https://github.com/bitwarden/clients) — licence metadata only; confirmed the SM CLI is not here (it is `bws` in `sdk-sm`).
- [bitwarden/agent-access](https://github.com/bitwarden/agent-access) — README, repo metadata (Apache-2.0), `crates/` and `examples/` listings; the Q6 agent-scoped credential protocol and `aac run` env injection.
- [bitwarden/mcp-server](https://github.com/bitwarden/mcp-server) — README and repo metadata (GPL-3.0); Bitwarden's MCP surface and its explicit whole-vault-exposure warning.
- [bitwarden/key-connector](https://github.com/bitwarden/key-connector) — description only, via the org repo enumeration; checked and ruled out as an AI-agent primitive.
