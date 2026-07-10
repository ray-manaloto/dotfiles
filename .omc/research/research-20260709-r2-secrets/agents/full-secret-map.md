# Run E / Angle 1 — Full secret inventory × consumer matrix (repo-grounded)

Date: 2026-07-09. Researcher: full-secret-map agent (Run E, angle 1 of 5).
Scope: enumerate every secret-shaped thing in ray-manaloto/dotfiles, its
current delivery path, and the consumer coverage matrix; identify gaps and
today's rotation points. Grounding: repo working tree at `main` +
`.omc/research/research-20260709-r2-inventory/report.md` + Run A web-env
reports (`research-20260709-r2-web-env/agents/{official-docs,network-allowlist}.md`).

## Findings

### F1. The complete secret inventory (9 classes)

| # | Secret class | Concrete items | Store of record | Delivery mechanism | Evidence |
|---|---|---|---|---|---|
| S1 | Doppler-managed runtime API keys | `EXA_API_KEY`, `BRAVE_API_KEY`, `GEMINI_API_KEY`, `GITHUB_TOKEN` (a long-lived PAT stored *in Doppler*), + doppler metadata `DOPPLER_PROJECT/CONFIG/ENVIRONMENT` | Doppler project `dotfiles`, config `dev` | host `initializeCommand` → `doppler secrets download --format docker` → `~/.local/state/dotfiles/doppler.env` → `runArgs --env-file` at container **create** | `.devcontainer/devcontainer.json:198`, `:84-90`; canary key list `scripts/devcontainer-smoke.sh:99` |
| S2 | Doppler host-CLI auth | personal CLI token from `doppler login` (scoped under `~/.doppler`) | Doppler account / host machine | implicit — `initializeCommand` assumes an authenticated host CLI; smoke error text says "is doppler authenticated on the host?" | `scripts/devcontainer-smoke.sh:96`; Doppler CLI docs (docs.doppler.com/docs/cli, fetched 2026-07-09): personal CLI token for local dev, service tokens for production |
| S3 | CI ephemeral `GITHUB_TOKEN` | per-job least-privilege tokens | GitHub Actions (auto-minted, per-run) | `secrets.GITHUB_TOKEN` → ghcr login (`build-publish.yml:125,257,388,519,654,742`, `ci.yml:397`, `image-analysis.yml:60`), BuildKit secret file (`build-publish.yml:162-174,297-309,531-548`), lock-refresh composite (`refresh.yml:84` → `GITHUB_TOKEN`/`MISE_GITHUB_TOKEN`, `.github/actions/lock-refresh/action.yml:29-36`), `GH_TOKEN` for gh api (`ghcr-cleanup.yml:54,78`, `refresh.yml:151`, `ci.yml:532`) | file:line as listed; `persist-credentials: false` on every checkout (13+ occurrences) |
| S4 | Build-time github_token bake secret | same token, BuildKit `--mount=type=secret` | n/a (pass-through) | `docker-bake.hcl:66-68` (`id=github_token,env=GITHUB_TOKEN` local default); Dockerfile consumes at `.devcontainer/Dockerfile:173-182` and `:396-404` (exports `GITHUB_TOKEN`+`MISE_GITHUB_TOKEN` for mise rate limits); local benchmark path uses `gh auth token` → tmpfile (`scripts/benchmark-docker.sh:50-54`) | never via ARG/env — invariant in `.github/workflows/AGENTS.md` ("BuildKit secret mount … never via ARG or env") |
| S5 | GitHub App credentials (refresh auto-merge) | `REFRESH_APP_ID` + `REFRESH_APP_PRIVATE_KEY` | GitHub repo **Actions secrets** (NOT Doppler) | `actions/create-github-app-token` mints a short-lived installation token per run (`refresh.yml:66-71`, permissions contents+PRs write); contract `ci.refresh-uses-app-token` pins the wiring (`python/verification/suites.toml:625-637`) | file:line as listed |
| S6 | SSH credentials (R1/R2) | **zero key material in the stack**: R2 = Docker Desktop magic socket `/run/host-services/ssh-auth.sock` bind mount + `SSH_AUTH_SOCK` containerEnv + chown in postCreate AND postStart; R1 = *public* keys only, `ssh-add -L` → `~/.local/state/dotfiles/authorized_keys` (0600) | macOS launchd ssh-agent / Keychain | socket mount `.devcontainer/devcontainer.json:96`, env `:189`, rationale `:37-54`; pubkey staging `python/src/dotfiles_setup/docker.py:51-91`; smoke asserts sock path `scripts/devcontainer-smoke.sh:214-215` | Docker-Desktop-only (issue #78, abiosoft/colima#1330/#942) |
| S7 | AI-CLI OAuth tokens (Claude Code, Codex, Gemini) | `.claude.json` oauthAccount, codex `auth.json`, gemini `oauth_creds.json` | each CLI's own login flow | **no declarative delivery path** — PR #80's `~/.claude`/`~/.codex`/`~/.gemini` bind mounts were removed; de-facto persistence is the single named home volume (`devcontainer.json:97`) after an in-container login | issue #83 (opened 2026-04-10, still open): "Doppler/fnox … is **not the right tool** for OAuth tokens"; CLIs installed in runtime tier `mise-runtime.toml:59-61` |
| S8 | fnox | binary shipped in image runtime tier, **no `fnox.toml`, no provider config, zero call sites** | n/a | none — dead weight pending #83 decision | `.devcontainer/mise-runtime.toml:41`; repo-wide grep: only mintlify-cache + AGENTS.md future-note hits; fnox docs cache confirms a Doppler provider exists (`docs/research/mintlify-cache/jdx/fnox/llms.txt:24`) |
| S9 | Leak-prevention control (not a secret, part of the surface) | gitleaks in hk pre-commit, repo allowlist | n/a | `hk-common.pkl:65-67` + `GITLEAKS_CONFIG` → `.gitleaks.toml` (`mise.toml:75-79`) | file:line as listed |

Notably absent from the entire repo (grep across workflows, mise configs,
home/ templates, .claude/): `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`,
`DOPPLER_TOKEN` (service token), any 1Password/Infisical/Vault/sops
reference, any git credential helper or signing key
(`home/dot_gitconfig` is credential-free). The absence of
ANTHROPIC/OPENAI keys is *by design* — those CLIs are OAuth-subscription
authenticated (issue #83), not API-key authenticated.

### F2. Consumer × secret matrix

Legend: ✅ delivered today · ⚠️ partial/fragile · ❌ needed but absent · — not needed.

| Secret class | Devcontainer | GHA CI (build/smoke/promote) | refresh auto-merge | ghcr-cleanup / image-analysis | Claude-web session | Self-hosted updater runner (hypothetical) |
|---|---|---|---|---|---|---|
| S1 API keys (EXA/BRAVE/GEMINI) | ✅ doppler.env → --env-file | — | — | — | ❌ nothing; `api.doppler.com` not in Trusted allowlist (Run A network-allowlist F3); only path = plain env vars in the environment config, "visible to anyone who can edit that environment" (Run A official-docs:43) | ❌ no provisioning path exists |
| S1 GITHUB_TOKEN (PAT-in-Doppler) | ✅ same path (gh CLI in container, `mise-runtime.toml:38`) | — (uses ephemeral S3 instead) | — | — | ⚠️ web GitHub proxy provides its own scoped credential — "Tokens never enter the container" (Run A official-docs:61); raw-API use would need env-var injection | ❌ |
| S3 ephemeral GITHUB_TOKEN | — | ✅ least-privilege blocks | ✅ (lock-refresh internals) | ✅ (`packages: write` for gated delete) | — | ❌ self-hosted runner would still get it from GitHub, but ghcr pull for a private-ish 38GB image + doppler access are unprovisioned |
| S4 bake secret | — | ✅ file→secret mount | — | — | — | ⚠️ builds are CI-only by policy anyway |
| S5 App private key | — | — | ✅ Actions secret → short-lived installation token | — | — | ❌ (would need the same App or a second one) |
| S6 SSH (R2 outbound) | ✅ DD magic socket (chown-fragile, DD-only) | — (checkout via token) | — | — | ✅ *different mechanism*: web GitHub proxy handles git push/pull; no SSH at all | ❌ headless runner has no macOS agent — the DD model does not transfer |
| S7 OAuth CLI tokens | ⚠️ home-volume persistence after manual in-container login; lost on volume prune | — | — | — | ⚠️ Claude auth is the platform's own; Codex/Gemini CLIs would be unauthenticated | ❌ |

The matrix shows the architecture is **two disjoint islands**: Doppler
serves exactly one consumer (the devcontainer), GitHub-native secrets
serve exactly one platform (GHA). No secret crosses islands except the
GITHUB_TOKEN *name* (two unrelated tokens: a PAT in Doppler vs the
ephemeral per-run token). Claude-web and any future updater runner sit on
neither island.

### F3. Delivery-path mechanics and their weak points (devcontainer island)

1. **Create-time snapshot, not runtime resolution.** `--env-file` applies
   only at `docker create`; a reused container (`mise run up` reuses,
   per `.devcontainer/devcontainer.json:46-50` comment re postCreate) keeps
   the env it was created with. Rotating a key in Doppler therefore
   requires container **recreate**, and nothing detects staleness:
   `verify-secrets` S1 (`mise.toml:518-541`) checks only that the host
   file exists, is non-empty, and contains the two **metadata** keys
   `DOPPLER_PROJECT`/`DOPPLER_CONFIG`.
2. **Weak canary threshold.** Smoke tier-2 passes at ≥3 of 7 canary keys
   (`scripts/devcontainer-smoke.sh:99-101`) — but 3 of the 7 are doppler
   metadata (`DOPPLER_PROJECT/CONFIG/ENVIRONMENT`), so a download
   containing **zero real secrets** still passes both gates.
3. **Plaintext at rest + docker-inspect exposure.** `doppler.env` sits
   unencrypted on the host, and `--env-file` values become part of the
   container config (visible to anything that can `docker inspect`).
   The Doppler CLI docs themselves position service tokens + `doppler run`
   as the production pattern precisely to avoid persisted plaintext
   (docs.doppler.com/docs/service-tokens, fetched 2026-07-09: read-only,
   single-config-scoped, revocable, `--max-age` ephemeral option).
4. **Unmanaged host dependency.** The doppler CLI is the only
   secrets-critical binary NOT in any mise config (grep: no `doppler` in
   `mise.toml [tools]`, `shared.toml`, or the image tiers) — installed
   out-of-band on the Mac, authenticated with a personal CLI token, and
   invisible to the repo's tool-currency/lockfile machinery. This
   violates the repo's own mise-first policy for the single most
   security-sensitive host tool.
5. **Selector plumbing is clean**: `DOPPLER_PROJECT=dotfiles` /
   `DOPPLER_CONFIG=dev` defaults live in `mise.toml:186,212`
   (`[tasks.up]`/`[tasks.dev-rebuild]` env) with a documented
   `mise.local.toml` per-clone override (`.devcontainer/AGENTS.md:50-52`).
   Contract `build.doppler-secrets-wired`
   (`python/verification/suites.toml:443-452`) pins the wiring.

### F4. Rotation topology today — exactly two manual rotation points

| Rotation point | Covers | Procedure today | Blast radius |
|---|---|---|---|
| **Doppler dashboard** (project dotfiles/dev) | EXA, BRAVE, GEMINI keys + the container GITHUB_TOKEN PAT | rotate at issuer → paste into Doppler → `mise run down && mise run up` (recreate) on every clone | container-only; PAT is dual-location (GitHub settings + Doppler) |
| **GitHub repo Actions secrets** | REFRESH_APP_ID / REFRESH_APP_PRIVATE_KEY | regenerate key in App settings → update repo secret | refresh.yml only |
| *(no rotation needed)* | S3/S4 ephemeral GITHUB_TOKEN, App installation tokens | auto per-run | — |
| *(host-side)* | SSH keys (agent), doppler personal CLI token | macOS keychain / `doppler login` re-auth | dev machine only |

The SSH model has **no rotation burden at all** because no key material
exists in the stack — the load-bearing property to preserve or
consciously trade away in any R2 redesign (a deploy-key model would add a
third rotation point AND at-rest key material).

### F5. Claude-web consumer (cross-referenced with Run A)

- The web environment has **no secrets store**: "Both environment
  variables and setup scripts are stored in the environment
  configuration, visible to anyone who can edit that environment"
  (Run A official-docs.md:43, from code.claude.com/docs/en/claude-code-on-the-web.md,
  fetched 2026-07-09).
- Doppler is **unreachable under the default Trusted allowlist**
  (`api.doppler.com` absent); making `doppler secrets download` work in a
  web session requires a Custom allowlist entry (+`cli.doppler.com` or
  `packages.doppler.com` for install) AND a `DOPPLER_TOKEN` service token
  stored as a plain environment-config variable (Run A
  network-allowlist.md F3 Doppler row + F6). fnox would face the identical
  egress constraint since its doppler provider calls the same API.
- GitHub credentials are the one thing the web platform solves natively:
  a dedicated GitHub proxy with a scoped in-sandbox credential; push
  restricted to the working branch (Run A official-docs.md:61). So the
  web consumer needs **only S1-class API keys**, not GitHub or SSH
  credentials.

### F6. Issue #83's actual scope (correction to the domain brief)

The brief characterizes #83 as "migrate to mise-env-fnox with doppler
provider in-container". The AGENTS.md future-note says that
(`.devcontainer/AGENTS.md:54-55`, `devcontainer.json:70-71`), but the
issue itself (fetched via GitHub API today) is titled "Research:
devcontainer **OAuth token injection for AI CLIs**" and its own
conclusion is that Doppler/fnox is the right tool **only for static
secrets** and "not the right tool" for the OAuth token class (Claude
Code oauthAccount, Codex `auth.json`, Gemini `oauth_creds.json`); it
proposes in-container login flows or selective auth-file mounts for
those. Any Run-E recommendation should treat "static-key delivery
refactor" and "OAuth token injection" as **separate problems** — #83 is
primarily the latter. Note also that #83's own docs-reviewed list quotes
the mise-env-fnox author's caveat verbatim: "I am not sure this plugin
is a good idea" (github.com/jdx/mise-env-fnox, cited in the issue body)
— relevant to weighing the brief's proposed mise-env-fnox migration.

*(Verification pass 2026-07-09, second session: every file:line citation
in F1-F5 re-read against the working tree — devcontainer.json:84-90/96/
189/198/200/207, suites.toml:443-453, refresh.yml:59-71, docker-bake.hcl:
66-68, mise-runtime.toml:33/38/41/59-61, smoke:92-104/208-221,
docker.py:51-91, hk-common.pkl:65-67, mise.toml:75-79 — all confirmed;
issue #83 re-fetched via GitHub API and confirmed; absence grep for
ANTHROPIC_API_KEY/OPENAI_API_KEY/DOPPLER_TOKEN outside research artifacts
confirmed; home/ grep for credential/token/helper returned zero hits.
One correction applied: the refresh contract is `ci.refresh-uses-app-token`
at suites.toml:625-637, not `workflow.refresh-app-token`.)*

## Uncertainties / gaps

- **U1 — actual Doppler config contents.** The full key list in project
  `dotfiles`/config `dev` is only observable from the Doppler dashboard
  or an authenticated download; the repo shows just the 7 canary names.
  There may be additional secrets with no repo-visible consumer.
- **U2 — scope of the GITHUB_TOKEN PAT in Doppler.** Classic vs
  fine-grained, and its permission set, are not derivable from the repo;
  it gates in-container `gh` and mise GitHub-API rate limits. Audit
  before any migration.
- **U3 — doppler CLI install/auth state on the Mac** (brew? version?
  keychain vs `~/.doppler` file token) — host-side, unverifiable from
  this container; the CLI-docs fetch did not pin the storage mechanism.
- **U4 — whether `initializeCommand` re-download ever reaches a reused
  container.** The spec runs initializeCommand on every `up`, refreshing
  the host file, but `--env-file` is create-only; the exact reuse
  semantics of `@devcontainers/cli` for `runArgs` changes were not
  probed here (consistent with the AGENTS.md note that postCreate does
  not re-run on reuse).
- **U5 — GEMINI double-coverage.** `GEMINI_API_KEY` arrives via Doppler
  while gemini-cli is also OAuth-capable (#83); which auth path the
  in-container gemini CLI actually uses when both are present was not
  verified.
- **U6 — updater-runner requirements are hypothetical**; the ❌ column
  reflects "no provisioning path exists", not measured failures.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — all repo evidence (devcontainer.json, mise.toml, workflows, Dockerfile, bake, smoke, suites.toml, docker.py) + issues #83, #78 via API.
- [jdx/fnox](https://github.com/jdx/fnox) — local mintlify cache llms.txt for the provider list (Doppler/1Password/Bitwarden/Infisical providers).
- [DopplerHQ/cli](https://github.com/DopplerHQ/cli) — via docs.doppler.com (CLI auth model, service tokens, `--max-age` ephemeral tokens; fetched 2026-07-09).
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — indirectly via Run A reports (web-env secrets/egress facts, issue #71629).
- [abiosoft/colima](https://github.com/abiosoft/colima) — issues #1330/#942 cited for the DD-only SSH socket constraint (via repo docs + issue #78, not re-fetched).
