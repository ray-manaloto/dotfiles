# Run D / Angle 3 — fnox + mise-env-fnox release mining (secrets angle)

Date: 2026-07-09. Analyst: research subagent (remote container; Bash disabled — cache-grep + WebFetch only).
Window mined: 2026-01 → 2026-07. Grounding: `docs/research/runs/research-20260709-r2-inventory/report.md`.

## Findings

### 1. fnox is mature, fast-moving, and already in the image — locked at 1.29.0, unused

- Release cadence (from `CHANGELOG.md` on `jdx/fnox@main`, fetched 2026-07-09): **11 minor releases in ~3 months** —
  1.20.0 (2026-04-04), 1.21.0 (04-21), 1.22.0/1.23.0 (04-26), 1.23.1 (05-02), 1.24.0 (05-06), 1.24.1 (05-13), 1.25.0 (05-14), 1.25.1 (05-17), 1.26.0 (06-12), 1.27.0 (06-17), 1.27.1 (06-18), 1.28.0 (06-24), 1.29.0 (07-01), **1.30.0 (2026-07-09, today)**.
  Source: <https://raw.githubusercontent.com/jdx/fnox/main/CHANGELOG.md>.
- Repo health (github.com/jdx/fnox, fetched 2026-07-09): **1.9k stars**, Rust, active. No explicit breaking changes flagged in the 1.20→1.30 window (the last CLI-breaking change noted in the changelog is ancient: v1.2.2 `-p`→`-P` profile flag).
- The image already ships fnox in the runtime tier: `.devcontainer/mise-runtime.toml:41` (`"fnox" = "latest"`), locked at **1.29.0** (`.devcontainer/mise-runtime.lock:171-178`, `github:jdx/fnox` backend, linux-x64 sha256). So the binary is one lock-refresh away from current at all times — it is wired but **unused** (no `fnox.toml` anywhere in the repo).

### 2. Provider list: Doppler support landed v1.20.0 (2026-04-04) — and it shells out to the doppler CLI

- Full provider list (fnox config reference, local cache `docs/research/mintlify-cache/jdx/fnox/llms-full.txt:4952`): `1password`, `age`, `aws`, `aws-kms`, `aws-ps`, `azure-kms`, `azure-sm`, `gcp`, `gcp-kms`, `fido2`, `bitwarden`, `bitwarden-sm`, `doppler`, `infisical`, `keepass`, `keychain`, `password-store`, `passwordstate`, `plain`, `proton-pass`, `vault`, `yubikey`. So yes: **Doppler, 1Password, Infisical** are all supported.
- Doppler provider added in **v1.20.0, 2026-04-04** (CHANGELOG: "add Doppler secrets manager provider", PR jdx/fnox#376); no doppler-specific fixes since — stable since landing.
- **Mechanics (verified in source, `crates/fnox-core/src/providers/doppler.rs` @ main):** the provider is a **doppler-CLI wrapper**, not an HTTP client — `Command::new("doppler")`, single fetch via `doppler secrets get <NAME> --plain`, **batch fetch** via `doppler secrets get N1 N2 … --json` (parses the `computed` field). Token resolution: provider `token` field → `FNOX_DOPPLER_TOKEN` → `DOPPLER_TOKEN` (passed as env to the subprocess) → interactive `doppler login` session. Docs confirm the CLI prerequisite (cache `llms-full.txt:4460-4533`).
- Consequence for this repo: an in-container fnox+doppler path **requires the doppler CLI inside the image**. That is cheap — the mise registry carries `doppler` via `github:DopplerHQ/cli` (<https://mise.jdx.dev/registry.html>) — one line in `mise-runtime.toml`. But it does NOT eliminate the bootstrap credential: the container still needs a `DOPPLER_TOKEN` service token injected from somewhere (host env / a one-line env-file), because interactive `doppler login` sessions live on the Mac host.

### 3. mise-env-fnox is NOT ripe: dormant, unreleased, and the author advises against it

- Mechanics (local cache `docs/research/mintlify-cache/jdx/mise-env-fnox/llms-full.txt`, all 6 pages): a **Lua mise env plugin**. Declared via `[plugins] fnox-env = "https://github.com/jdx/mise-env-fnox"` + `[env] _.fnox-env = { tools = true, profile = "…", fnox_bin = "…" }`. On every mise activation it runs `fnox config-files` then `fnox export --format json` (optionally `--profile`), exports the `secrets` map as env vars, registers `fnox.toml` as a watch file, returns `redact: true` and `cacheable: true`. `tools = true` is **required when fnox is mise-installed** (this repo's case).
- Caching: opt-in via `MISE_ENV_CACHE=1`; secrets cached **encrypted on disk**, invalidated only on `fnox.toml` change — **documented staleness trap**: an upstream Doppler rotation keeps serving the old cached value until `fnox.toml` is touched (cache `llms-full.txt:111-120`). Errors fail open: a failed `fnox export` prints `[fnox] warning:` and activation continues with the secrets silently missing.
- Maturity signals (github.com/jdx/mise-env-fnox, fetched 2026-07-09): **15 stars, 7 total commits, zero releases, last commit 2026-03-09** (born 2026-01-19 — a 7-week active life, dormant 4 months). The docs and README carry an explicit author warning: *"The author of this plugin is uncertain whether it's a good idea. fnox was built as a separate CLI for a reason… I would probably advise avoiding this."* (cache `llms-full.txt:307-309`; README).
- Open issues directly on this repo's adoption path: **#3 "race condition when fnox is managed by mise as a tool"** (2026-01-28 — exactly this repo's setup, fnox is mise-managed), #1 "Unable to load plugin due to missing hook" (2026-01-28), #8 lazy loading (2026-03-02), #11 `auth_command` support (2026-03-17), #13 "Reflect plugin status in fnox documentation" (2026-05-08 — i.e. the deprecation-ish warning isn't even propagated yet). None fixed since March.
- The cached mise docs themselves say: *"There is no direct integration between fnox and mise — you configure fnox independently"* and position fnox as env vars mise "picks up like any other" (`docs/research/mintlify-cache/jdx/mise/llms-full.txt:3143-3149`). The plugin is the only bridge, and it is the piece with the warning label.

### 4. Native fnox alternatives to the plugin (all shipped/stable in the window)

If the goal of issue #83's static-secrets half is "resolve secrets in-container at runtime instead of freezing them at `initializeCommand` time", fnox offers three plugin-free mechanisms:

1. **Shell integration** — `eval "$(fnox activate bash)"` in the chezmoi-managed `.bashrc`/`.zshrc` (`home/dot_config/…` templates). Per-prompt hook loads/unloads secrets on cd into a `fnox.toml` dir, respects `FNOX_PROFILE`, hierarchical config merge (cache `llms-full.txt:1574-1693`). This is fnox's own first-class equivalent of what mise-env-fnox does.
2. **`fnox exec -- <cmd>`** — per-invocation injection, with `FNOX_IF_MISSING=error` strict mode; the CI/CD guide shows the same pattern for GHA via `jdx/mise-action` (cache `llms-full.txt:2-84`) — relevant to Run E for CI too.
3. **`fnox mcp` — session-scoped secret broker for AI agents** (cache `llms-full.txt:859-984`): stdio MCP server; secrets resolved on first access, cached **in process memory only**, cleared on disconnect; `[mcp] secrets = [...]` allowlist; `tools = ["exec"]` exec-only isolation. **v1.30.0 (2026-07-09) extends this** with an `env = "exec"` secret state that keeps secrets out of interactive shells entirely while still injecting into `fnox exec` subprocesses — release notes explicitly call out "preventing exposure to inherited processes like AI coding agents" (<https://github.com/jdx/fnox/releases>, v1.30.0). Given this container's runtime tier ships claude-code/codex/gemini-cli (`mise-runtime.toml:57-61`) and today's `--env-file` approach broadcasts *every* Doppler secret to *every* process including the AI CLIs, this is arguably the highest-value fnox feature for this repo — a blast-radius reduction, not just plumbing swap. (NOTE: repo rule `no_mcp_registration` forbids registering MCP servers via the Claude CLI's `mcp add` subcommand; an fnox MCP adoption would need the `mcp2cli` process-spawn pattern or an explicit exception per `research-doc-sources.md` — flag for Run E.)

### 5. What the migration would actually change (adoption sketch for issue #83, static-secrets half)

Current live path (inventory report + read directly): `devcontainer.json:198` `initializeCommand` runs host-side `doppler secrets download --format docker` → `~/.local/state/dotfiles/doppler.env` → `runArgs --env-file` (`devcontainer.json:87-88`) → plaintext env in every container process. Enforced by contract `build.doppler-secrets-wired` (`python/verification/suites.toml:443-452`), smoke tier-2 canaries (`scripts/devcontainer-smoke.sh:91-104`), `mise verify-secrets` (`mise.toml:519-540`).

In-container fnox+doppler would change:

| Surface | Change |
|---|---|
| `.devcontainer/mise-runtime.toml` | add `doppler = "latest"` (registry backend `github:DopplerHQ/cli`) — fnox's doppler provider shells out to it |
| new `fnox.toml` (repo root) | `[providers] doppler = { type = "doppler", project = "dotfiles", config = "dev" }` + `[secrets] EXA_API_KEY = { provider = "doppler", value = "EXA_API_KEY" }` … per canary |
| `devcontainer.json:198` | `initializeCommand` shrinks from full-secrets download to a **single-token handoff**: write only `DOPPLER_TOKEN=<service token>` to the env-file (bootstrap credential cannot be eliminated — `doppler login` sessions are host-side) |
| activation | chezmoi shell template `eval "$(fnox activate bash)"` (preferred) or per-task `fnox exec`; `[env] _.fnox-env` plugin route NOT recommended (finding 3) |
| contracts/smoke | rewrite `build.doppler-secrets-wired` + tier-2 canaries + `verify-secrets` S1 to assert fnox resolution instead of env-file presence |

Gains: secrets no longer plaintext-at-rest on the host state dir; rotation visible without container recreate; per-profile switching (`FNOX_PROFILE`) maps to `DOPPLER_CONFIG` overrides; optional MCP/exec-only scoping for AI CLIs. Costs: doppler CLI in image; network dependency at shell activation (batch `doppler secrets get … --json` per resolution unless cached); token still injected from host; three enforcement surfaces to rewrite.

### 6. Ripeness verdict

- **mise-env-fnox migration as written in `.devcontainer/AGENTS.md` ("Future: migrate to mise-env-fnox… #83"): NOT ripe.** The plugin is dormant, unreleased, has an unfixed race with mise-managed fnox (its issue #3 = this repo's exact configuration), and its own author advises avoiding it. Issue #83's body already records this caveat — and #83 is actually primarily about **OAuth tokens for AI CLIs**, which it correctly concludes Doppler/fnox is *not* the tool for; only its static-secrets half maps to fnox at all.
- **fnox-in-container (plugin-free) is ripe on the tool side, not the integration side**: fnox itself is healthy (1.9k stars, weekly releases, doppler provider stable since 2026-04-04, binary already locked in the image at 1.29.0). What's missing is repo work (fnox.toml, token handoff, contract rewrites), not upstream features. Recommend: **watch** mise-env-fnox; **adopt-candidate** fnox shell-integration or MCP/exec-only mode, prioritized by the AI-CLI blast-radius argument rather than by retiring the (working, small) initializeCommand download.

## Retire/adopt/watch table (feed for Run E and the domain rollup)

| Feature | Version / date | What it touches in-repo | Risk | Verdict / sketch |
|---|---|---|---|---|
| fnox doppler provider | v1.20.0, 2026-04-04 | `devcontainer.json:198` initializeCommand download + `--env-file` (`:87-88`) | Med — needs doppler CLI in image + host token handoff; 3 contracts to rewrite | **Adopt-candidate**: fnox.toml + doppler tool in runtime tier + token-only env-file |
| fnox `mcp` broker + v1.30.0 `env="exec"` state | MCP guide (cached); 1.30.0, 2026-07-09 | AI CLIs (`mise-runtime.toml:57-61`) currently inherit all secrets via env-file | Med — interacts with `no_mcp_registration` rule; needs mcp2cli-style spawn or approved exception | **Adopt-candidate (highest value)**: scope secrets away from claude-code/codex/gemini |
| mise-env-fnox plugin | unreleased; last commit 2026-03-09 | would replace the same initializeCommand path | High — author warning, race with mise-managed fnox (its #3), fail-open errors, cache-staleness on rotation | **Watch** — revisit if it gets a release + #3 fix; update `.devcontainer/AGENTS.md` future-note to reflect this |
| fnox in CI (`fnox exec` + mise-action) | CI/CD guide (cached) | GHA secrets blocks (Run E scope) | Low | **Watch** — no current pain; note for Run E |
| fnox leases (ephemeral cloud creds) | v1.16.0-1.17.0 window | nothing today (no AWS/GCP creds in repo) | — | **Ignore** for now |

## Uncertainties / gaps

- **fnox open-issue volume**: the github.com issues page failed to render through the proxy ("error while loading"); star/release cadence and PR count (2 open) retrieved, issue count not. Low confidence only on that one signal.
- **WebFetch summarizer misdated v1.30.0 as "July 9, 2024"** on the releases page; the CHANGELOG fetch confirms **2026-07-09**. Changelog treated as truth per repo rule.
- **Latency of in-container resolution**: the doppler provider batch call is one `doppler secrets get … --json` subprocess + network round-trip per resolution; per-prompt shell-integration cost inside the container is unmeasured. Mitigable (mise-env-fnox's `MISE_ENV_CACHE`, or resolve-once-per-login), but unprobed.
- **mise-env-fnox functional status on current mise**: its issue #1 (plugin hook fails to load) and the "minimum runtime version 0.3.0" (plugin-runtime versioning, not mise's own version — docs wording ambiguous, cache `llms-full.txt:335`) are unverified against mise 2026.x; no probe possible in this session (Bash disabled).
- **Cache currency**: the local fnox mintlify cache includes leases + MCP + doppler (≥1.16.0 era) but predates today's 1.30.0 `env = "exec"` secret state — that feature is sourced from the release notes only.
- Whether Doppler service-token scoping (read-only, single-config tokens) meets the repo's threat model is Run E's question, not assessed here.

## GitHub repos touched

- [jdx/fnox](https://github.com/jdx/fnox) — CHANGELOG, releases page, repo metadata, doppler provider source (`crates/fnox-core/src/providers/doppler.rs`)
- [jdx/mise-env-fnox](https://github.com/jdx/mise-env-fnox) — README/repo metadata, commit history, open issues; docs via local mintlify cache
- [jdx/mise](https://github.com/jdx/mise) — secrets docs page + registry (doppler entry) via local cache + mise.jdx.dev/registry.html
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — devcontainer.json, mise-runtime.toml/.lock, .devcontainer/AGENTS.md, issue #83
