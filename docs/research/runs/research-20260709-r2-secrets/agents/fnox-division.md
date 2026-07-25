# Run E / Angle 3 — fnox + mise-env-fnox as the in-container layer (issue #83)

Date: 2026-07-09. Analyst scope: concretely evaluate the migration proposed in
`.devcontainer/AGENTS.md:54-55` ("Future: migrate to mise-env-fnox with doppler
provider inside the container for runtime secret resolution (#83)") — fnox's
provider model and 2026 production-readiness, how mise-env-fnox wires into mise
env resolution, caching/latency, offline/unreachable failure modes, the
devcontainer delta, and which consumers fnox covers that the current host-side
Doppler download cannot.

Method note: per `research-doc-sources.md`, the local mintlify cache
(`docs/research/mintlify-cache/jdx/{fnox,mise-env-fnox,mise}/`) was grepped
first; all load-bearing cache claims were then cross-checked against live
GitHub source (`jdx/fnox`, `jdx/mise-env-fnox`, `jdx/mise`) and current release
pages. Repo baseline: `docs/research/runs/research-20260709-r2-inventory/report.md`.

---

## Findings

### F1. The headline: the plugin's own author advises against mise-env-fnox

Two independent primary sources, both current:

1. The mise-env-fnox docs open with a warning block: *"The author of this
   plugin is uncertain whether it's a good idea. fnox was built as a separate
   CLI for a reason. Evaluate whether this integration fits your workflow
   before adopting it in production."*
   (`docs/research/mintlify-cache/jdx/mise-env-fnox/llms-full.txt:307-309`).
   The GitHub README is blunter: *"I am not sure this plugin is a good idea.
   fnox was built as a separate CLI for a reason. I would probably advise
   avoiding this."* (https://github.com/jdx/mise-env-fnox, fetched 2026-07-09).
2. jdx's fnox announcement (jdx/mise discussion #6779, **2025-10-26**) states
   the architectural reason directly: *mise's frequent environment reloads make
   remote secret calls impractical* — performance and security concerns are
   exactly why fnox was shipped as a separate CLI rather than a mise feature
   (https://github.com/jdx/mise/discussions/6779, fetched 2026-07-09). The
   current mise docs still say *"There is no direct integration between fnox
   and mise — you configure fnox independently"*
   (`docs/research/mintlify-cache/jdx/mise/llms-full.txt:3147`).

Plugin maturity corroborates: **7 commits total, 15 stars, zero releases, 100%
Lua** (github.com/jdx/mise-env-fnox, fetched 2026-07-09). Issue #83 in this
repo already quotes the author caveat in its "Docs reviewed" section
(https://github.com/ray-manaloto/dotfiles/issues/83, created 2026-04-10).

**Consequence:** adopting mise-env-fnox as *the* devcontainer secrets path
would contradict this repo's own `tool-currency-and-native-first.md` /
`use-tool-builtins.md` posture — it is not the tool author's recommended
pattern; it is an experiment he publicly discourages.

### F2. Issue #83 is mis-summarized in `.devcontainer/AGENTS.md` — it is about OAuth tokens, and it already concludes fnox is the wrong tool for them

The actual issue #83 ("Research: devcontainer OAuth token injection for AI
CLIs", 2026-04-10) is about Claude Code / Codex / Gemini **OAuth session
tokens** (`.claude.json` `oauthAccount`, `auth.json`, `oauth_creds.json`), not
about the static-secret pipeline. Its own conclusion: *"Doppler/fnox (designed
for static API keys) is **not the right tool** for OAuth tokens that are
managed/refreshed by each CLI's own login flow"*; the likely solution is
CLI-native login in-container, selective auth-file mounts, or a hybrid
(https://github.com/ray-manaloto/dotfiles/issues/83). The "migrate to
mise-env-fnox with doppler provider" sentence exists only in
`.devcontainer/AGENTS.md:54-55` as a "Future:" note citing #83 — the issue
itself never proposes that migration as a decided direction. **The migration
premise this angle was asked to evaluate is weaker in the primary source than
in the inventory summary.**

### F3. fnox provider model — breadth is real, but the doppler provider shells out to the Doppler CLI

Provider surface (2026-07-09): `1password`, `age`, `aws`, `aws-kms`, `aws-ps`,
`azure-kms`, `azure-sm`, `gcp`, `gcp-kms`, `fido2`, `bitwarden`,
`bitwarden-sm`, `doppler`, `infisical`, `keepass`, `keychain`,
`password-store`, `passwordstate`, `plain`, `proton-pass`, `vault`, `yubikey`
(`docs/research/mintlify-cache/jdx/fnox/llms-full.txt:4952`), plus `foks`
added since the cache snapshot (jdx/fnox `docs/index.md`, live 2026-07-09).

Production-grade assessment for the four candidates named in the brief:

| Provider | Mechanism | Auth for headless use | Verdict |
|---|---|---|---|
| `doppler` | **shells out to the `doppler` CLI binary** — `Command::new("doppler")`, single: `doppler secrets get NAME --plain`, bulk: `doppler secrets get N1 N2 --json` (jdx/fnox `crates/fnox-core/src/providers/doppler.rs`, main, fetched 2026-07-09) | `token` field → `FNOX_DOPPLER_TOKEN` → `DOPPLER_TOKEN` → interactive login (cache llms-full.txt:4528-4533) | Works, but is a thin wrapper: **requires the Doppler CLI installed** (cache :4463) and inherits its network dependency on api.doppler.com |
| `1password` | via `op` CLI; service-account token (`OP_SERVICE_ACCOUNT_TOKEN`) explicitly recommended over personal tokens (cache :4062, :4157-4165) | service account | production-grade pattern, needs `op` in image + paid-ish 1P setup |
| `infisical` | via Infisical CLI; `INFISICAL_TOKEN` service token (cache :4367-4425) | service token | works; another CLI in the image + another service |
| `bitwarden` / `bitwarden-sm` | via `bw` (session tokens **expire**, re-unlock required — cache :4269-4271) / `bws` access token (cache :4274-4364) | `bw`: poor for headless; `bws`: fine | `bitwarden-sm` OK; `bitwarden` PM unsuitable for automation |
| `age` (contrast) | **in-process encryption, ciphertext committed in fnox.toml; zero network, zero extra CLI**; key via `FNOX_AGE_KEY` env or `key_file` (can be an SSH key, `~/.ssh/id_ed25519`) (cache :424-437, :5851-5879) | one env var | the only fully offline, dependency-free provider — and the one fnox's own CI/CD guide builds on (cache :24-30, :46-62) |

fnox itself: announced **2025-10-26** at "1.0"; now **v1.30.0 released
2026-07-09** (github.com/jdx/fnox/releases) — ~30 minor releases in ~8.5
months. Active and fast-moving, but young; jdx acknowledged in #6779 the
initial implementation was LLM-generated. The repo already ships it unused at
`.devcontainer/mise-runtime.toml:41` (`"fnox" = "latest"`).

### F4. How mise-env-fnox wires in, and its caching/latency reality

Mechanics (cache `jdx/mise-env-fnox/llms-full.txt:127-225`): mise calls the
plugin's `MiseEnv` Lua hook on every environment activation → plugin runs
`fnox config-files`, then `fnox export --format json [--profile P]` → each
key in the JSON `secrets` map becomes an env var; `fnox.toml` is registered as
a watch file; `redact: true` hides values in mise output. Config is one line:
`[plugins] fnox-env = "https://github.com/jdx/mise-env-fnox"` +
`[env] _.fnox-env = { tools = true, profile = "..." }` (`tools = true`
required when fnox is mise-installed — llms-full.txt:247-249).

**Latency:** uncached, EVERY shell activation / `mise x` / task run pays a
`fnox export` subprocess, which for the doppler provider pays a further
`doppler secrets get … --json` CLI spawn + HTTPS round-trip to api.doppler.com.
Two mitigations exist, both with sharp edges:

- **mise env caching** (`MISE_ENV_CACHE=1`, opt-in): real and shipped in mise
  core — `settings.toml` defines `env_cache` (Bool), cache encrypted on disk
  with a session-scoped `__MISE_ENV_CACHE_KEY` minted at `mise activate`
  (jdx/mise `src/toolset/env_cache.rs`, `src/cli/activate.rs`, e2e
  `test_env_cache`; fetched 2026-07-09). Invalidation is **fnox.toml-mtime
  based only** — *"If you rotate a secret upstream, the old cached value will
  continue to be used until the cache is invalidated"* (mise-env-fnox cache
  llms-full.txt:111-120). So the "fresh secrets" argument for in-container
  resolution largely evaporates the moment you enable the cache you need for
  acceptable latency.
- **fnox daemon** (fnox ≥1.27.0, 2026): opt-in `[daemon] enabled = true` /
  `FNOX_DAEMON`, per-user Unix socket, **memory-only** cache with
  `idle_timeout` (e.g. `"8h"`), per-secret/provider `daemon_cache = false`
  opt-out, peer-uid verification, `fnox daemon clear`
  (https://fnox.jdx.dev/guide/daemon.html, fetched 2026-07-09). Helps repeated
  `fnox exec/get`; postdates the local mintlify cache (refresh candidate).

### F5. Failure modes: mise-env-fnox fails OPEN, and can cache the failure

Documented behavior (cache llms-full.txt:212-221): if `fnox config-files` or
`fnox export` fails — offline, provider unreachable, bad token — the plugin
*"prints a warning prefixed with `[fnox]` but does not abort the environment
load … the affected secrets are simply omitted"*, returning
`{cacheable = true, watch_files = config_files, env = {}}`. Two consequences:

1. **Silent empty environment.** A container without network (or with an
   expired `DOPPLER_TOKEN`) gets shells with NO canary vars and only a stdout
   warning. Today's enforcement (smoke tier-2 canaries expecting ≥3 of
   DOPPLER_*/EXA_API_KEY/… at `scripts/devcontainer-smoke.sh:91-104`;
   `mise.toml:519-540` verify-secrets S1) checks container-level env injected
   at create; under mise-env-fnox the vars exist only inside mise-activated
   shells, so the whole contract layer (`build.doppler-secrets-wired`,
   suites.toml:443-452) would need redesign, and a fail-open empty env is
   exactly the false-green shape `verify-before-advancing.md` exists to
   prevent.
2. **The failure is marked `cacheable = true`** — with `MISE_ENV_CACHE=1`, a
   transient outage can pin an EMPTY secret set until `fnox.toml` changes.
   fnox's own strictness knob (`FNOX_IF_MISSING=error`, default `warn`; cache
   llms-full.txt:5883-5911) governs missing *secrets*, but the plugin's
   pcall-wrapper converts even hard fnox errors into warn-and-continue.

Contrast with the current baseline's failure mode: host-side
`doppler secrets download` runs in `initializeCommand` — if Doppler is
unreachable at `mise run up`, the failure is loud, host-side, and BEFORE the
container exists; once created, the container's secrets are stable env vars
with zero runtime network dependency (`devcontainer.json:198`, `:84-88`;
`.devcontainer/AGENTS.md` §Secrets Injection). Doppler's CLI additionally
keeps an encrypted fallback file for `doppler run`-style access (sibling
report `doppler-platform.md` F1) — but that applies to the host download path
too.

### F6. The devcontainer delta for the #83 migration would be large, for negative freshness benefit

To move resolution in-container with fnox+doppler you would need ALL of:

1. `doppler` CLI in the image (available via mise registry short-name
   `doppler` → `github:DopplerHQ/cli` backend — https://mise.jdx.dev/registry.html,
   fetched 2026-07-09) — a new runtime-tier tool, ~weekly-release churn.
2. A committed `fnox.toml` (providers + secret name references).
3. `[plugins] fnox-env` + `[env] _.fnox-env` in a mise config the container
   sees — but the repo root `mise.toml` is shared host↔container, so the
   directive would also fire on the Mac host and in GHA/web unless gated
   behind `MISE_ENV` blocks (mise-env-fnox supports `[env.<name>]` scoping,
   cache llms-full.txt:12-24).
4. A `DOPPLER_TOKEN` service token **inside** the container — i.e. the
   host-side delivery path (env-file or equivalent) must survive anyway to
   bootstrap the one secret that unlocks the rest. Read-only project+config
   scoped service tokens are the right primitive (50 free — sibling
   `doppler-platform.md` F1).
5. Rework of the three-layer enforcement (contract, smoke canaries,
   verify-secrets S1) from "container env" to "mise-activated shell env".

Net: strictly more moving parts, a new in-container network dependency, a
token at rest in the container (today NO Doppler credential enters the
container — `.devcontainer/AGENTS.md:47-48`), and — per F4 — no real
freshness gain once caching is enabled. **Keep the host-side
initializeCommand download as the devcontainer path; do not migrate it.**

### F7. Where fnox genuinely adds coverage Doppler-host-side cannot reach

The division of labor that DOES make sense keeps Doppler as the platform of
record and uses fnox as a *delivery adapter* only where the host-side download
cannot run:

| Consumer | Can host-side Doppler download reach it? | fnox option | Assessment |
|---|---|---|---|
| Devcontainer | **Yes (today, working, enforced)** | unnecessary | no change (F6) |
| GHA workflows | No (no Mac host) — but Doppler has native paths (secrets-fetch-action v2.0.0 2026-03-19, GitHub sync; sibling `doppler-platform.md` F2) | `jdx/mise-action` + `FNOX_AGE_KEY` GH secret + `fnox exec` (fnox's own CI/CD guide pattern, cache llms-full.txt:32-66) with `FNOX_IF_MISSING=error` | Doppler-native sync is lower-cost for CI; fnox+age viable if avoiding a Doppler↔GitHub coupling |
| Claude-web sessions | No — and `api.doppler.com` is **blocked under the default Trusted egress policy**; needs a Custom allowlist entry (Run A report §3, `docs/research/runs/research-20260709-r2-web-env/report.md:180,193-198`) | **fnox binary installs via mise from GitHub releases (allowlisted); with the `age` provider it needs ZERO network at resolve time — only `FNOX_AGE_KEY` as a web-environment env var** | this is fnox's unique win: committed age-encrypted ciphertext + one env-var key delivers EXA/BRAVE/AI keys to web sessions under plain Trusted policy, no Custom allowlist, no Doppler reachability. Caveat: web env vars are visible to environment editors (no secrets store yet, anthropics/claude-code#32733; Run A §Open-questions 3) |
| Self-hosted updater runner | No Mac host | either `DOPPLER_TOKEN` + doppler CLI, or fnox+age with the key in the runner's secret store | both work; fnox+age keeps it offline-tolerant |

The dual-write cost (secret lives in Doppler AND as age ciphertext in
fnox.toml for the web path) is the price of the offline property; for the
current tiny research-key set (EXA/BRAVE/GEMINI…) it is a few
`fnox set` invocations, and rotation is an explicit re-encrypt — visible in
git history (auditable), but manual.

### F8. Tool-currency note on the shipped-but-unused fnox

`"fnox" = "latest"` has sat unused in `.devcontainer/mise-runtime.toml:41`
since it landed. Under `tool-currency-and-native-first.md` rule 3, an unused
tool should either gain its justifying consumer (the F7 web/CI age path) or be
retired in the same change that decides against it. fnox's release velocity
(1.27→1.30 within weeks, incl. a daemon and paranoid-env mode) also argues for
the runtime tier's lockfile discipline over `latest`-at-build-time drift —
which the tier already provides via `mise-runtime.lock`.

---

## Recommendation for the domain synthesis (this angle's vote)

1. **Reject the mise-env-fnox migration as written** in
   `.devcontainer/AGENTS.md:54-55`: author-discouraged plugin (F1), fail-open
   + cacheable-failure semantics (F5), large enforcement rework for negative
   freshness benefit (F4/F6). Amend the AGENTS.md "Future:" note — it also
   misattributes the plan to issue #83, which actually concludes fnox is wrong
   for its (OAuth) problem (F2).
2. **Keep the host-side Doppler download as the sole devcontainer secrets
   path** — it is the strongest security posture available (no Doppler
   credential in the container at all) and is triply enforced today.
3. **Adopt fnox narrowly as the web-session (and optionally CI) delivery
   adapter with the `age` provider** — committed ciphertext + `FNOX_AGE_KEY`
   env var; zero network, zero allowlist changes, `FNOX_IF_MISSING=error` in
   any gate that consumes it. Use `fnox exec -- <cmd>` (the author-endorsed
   separate-CLI pattern), NOT shell-activation injection.
4. If fnox gains no consumer, retire it from mise-runtime.toml instead of
   carrying it (F8).

## Uncertainties / gaps

- **fnox daemon and v1.28-1.30 features postdate the local mintlify cache**;
  daemon offline behavior is undocumented (fetched page silent on it). Cache
  refresh for `jdx/fnox` recommended.
- **mise-env-fnox option names**: the cached options page's ParamField names
  render empty in llms-full.txt (types/description only); names
  (`tools`/`profile`/`fnox_bin`) were inferred from the examples and the
  how-it-works Lua — confirm against plugin source before any adoption.
- **`MISE_ENV_CACHE` + plugin empty-failure caching** (F5.2) is derived from
  the documented `cacheable = true` return on error + mise's cache mechanics;
  not empirically probed end-to-end.
- **Whether fnox's doppler provider could bypass the CLI in future** (native
  API client) — currently CLI-shell-out per source; a future release could
  change the image dependency calculus.
- **`FNOX_AGE_KEY` handling in Claude-web**: env-var visibility caveat is
  documented (Run A), but whether the setup-script snapshot captures env vars
  (it should not — it snapshots the filesystem) was not probed.
- The fnox docs' "Supported providers for remote storage" list
  (cache llms-full.txt:452) omits `doppler`/`infisical` while the provider
  pages document them — docs internal inconsistency; treated the provider
  pages + source as authoritative.

---

## Addendum — second independent verification pass (2026-07-09, remote session)

A separate analyst re-ran this angle from scratch (cache-first, then live
fetches). All load-bearing claims above were independently RE-CONFIRMED:
the doppler provider shell-out (`Command::new("doppler")`, `doppler secrets
get NAME --plain` / batch `--json`, token order `FNOX_DOPPLER_TOKEN` →
`DOPPLER_TOKEN`, no provider-level caching) re-read from
`crates/fnox-core/src/providers/doppler.rs` on main; fnox v1.30.0 release
date re-confirmed as 2026-07-09 (repo page cross-check after a WebFetch
summarizer initially misreported the year as 2024); mise-env-fnox repo
state re-confirmed (15 stars / 7 commits / no releases / Lua / README
"I would probably advise avoiding this"); mise-env-fnox fail-open
`{cacheable = true, env = {}}` on error re-read from the cached
how-it-works page (`jdx/mise-env-fnox/llms-full.txt:212-221`); the
`MISE_ENV_CACHE` mtime-only invalidation warning re-read at
`llms-full.txt:111-120`. New evidence found in this pass:

### A1. fnox's OFFICIAL docs now explicitly deprecate the mise-env-fnox path (stronger than the README caveat)

The live fnox Mise Integration guide
(https://fnox.jdx.dev/guide/mise-integration.html, fetched 2026-07-09)
states verbatim: **"We do not recommend using fnox through the
jdx/mise-env-fnox env plugin. It is an incomplete experiment and does not
track every fnox feature."** Its ranked recommendations: (1) shell
integration `eval "$(fnox activate bash)"`, (2) **`fnox exec` inside mise
tasks** (`[tasks.dev] run = "fnox exec -- npm run dev"`), (3) the plugin,
last and discouraged. This upgrades F1 from "author is uncertain" to
"vendor documentation recommends against" — the strongest possible basis
for rejecting the #83-referenced migration as written. (This page
postdates the local mintlify cache; add it to the refresh queue.)

### A2. The doppler subcommand fnox invokes has NO offline fallback

Doppler's encrypted fallback snapshots are automatic **only for
`doppler run`** ("When using the `doppler run` command, the CLI
automatically creates a fallback file…"); `doppler secrets download` can
*write* one with `--passphrase`; **no fallback behavior is documented for
`doppler secrets get`** — the exact subcommand fnox shells out to
(https://docs.doppler.com/docs/automatic-fallbacks, fetched 2026-07-09).
So an in-container fnox+doppler path is strictly *worse* offline than
today's frozen host-side env-file, unless paired with an `age` fallback
provider or periodic `fnox sync` (remote→age, "useful for working
offline", cache `jdx/fnox/llms-full.txt:5167`). This sharpens F5/F6.

### A3. fnox daemon specifics (fills the F4 daemon gap)

https://fnox.jdx.dev/guide/daemon.html (fetched 2026-07-09): opt-in
`[daemon] enabled = true` + `idle_timeout = "8h"` or `FNOX_DAEMON=on`;
memory-only per-user cache over a Unix domain socket ("does not listen on
TCP"), peer-uid validation; serves `exec/get/export/list --values/check/
tui/mcp`; invalidated on config/profile/provider-reference/env change,
`fnox daemon clear|stop`, or idle timeout; per-secret/provider
`daemon_cache = false`. With the sanctioned `fnox exec`-in-tasks pattern,
the daemon (not mise env-cache) is the right latency mitigation — only the
first access per idle window pays the provider round-trip.

### A4. fnox MCP mode exists but collides with a project invariant

`fnox mcp` is a session-scoped stdio secret broker for AI agents (cache
`jdx/fnox/llms-full.txt:856-989`, `:5297-5303`) — conceptually attractive
for keeping ANTHROPIC/EXA/BRAVE keys out of agent env vars, but native
registration is machine-blocked by the `no_mcp_registration` hk step;
only `mcp2cli` process-spawn invocation would be permissible. Note for
the domain synthesis, not a recommendation.

### A5. Image pin detail

`.devcontainer/mise-runtime.lock:171-173` currently locks fnox **1.29.0**
(`backend = "github:jdx/fnox"`); latest is 1.30.0 (released today) — the
existing lock-refresh automation will pick it up; no action needed beyond
F8's use-it-or-retire-it decision.

### A6. mise's native secrets features are the third option nobody asked about

mise core natively supports SOPS-encrypted env files (experimental) and
direct inline age encryption in `mise.toml`
(cache `jdx/mise/llms-full.txt:2935-3010`,
https://www.mintlify.com/jdx/mise/environments/secrets) — for a
web-session/CI research-key use case this could deliver the F7 "age" win
with zero new tools (no fnox at all). Trade-off: no provider model, no
Doppler bridge, SOPS marked experimental. The domain synthesis should
weigh mise-native-age vs fnox-age for recommendation #3.

The addendum author endorses this report's four recommendations unchanged,
with #1 strengthened by A1 and #2 strengthened by A2.

## GitHub repos touched

- [jdx/fnox](https://github.com/jdx/fnox) — provider model, doppler.rs source (CLI shell-out; re-verified in addendum), releases (v1.30.0 2026-07-09), daemon + mise-integration live docs, CI/CD guide (via local mintlify cache + live fetches)
- [jdx/mise-env-fnox](https://github.com/jdx/mise-env-fnox) — plugin mechanics, caching, fail-open error handling, author warning, repo maturity (cache + live)
- [jdx/mise](https://github.com/jdx/mise) — MISE_ENV_CACHE/env_cache source, secrets docs ("no direct integration"), registry (doppler short-name), discussion #6779 (fnox announcement/positioning)
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issue #83 full text; baseline files (.devcontainer/AGENTS.md, mise-runtime.toml, devcontainer.json refs via inventory)
- [DopplerHQ/cli](https://github.com/DopplerHQ/cli) — mise registry backend target for the doppler CLI; docs.doppler.com CLI guide + automatic-fallbacks page read in addendum pass (fallback scope, service tokens)
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — web-session egress facts reused from Run A report (#32733 secrets-store gap)
- [aquaproj/aqua-registry](https://github.com/aquaproj/aqua-registry) — searched for a doppler package (no hits via code search; superseded by mise registry evidence)
