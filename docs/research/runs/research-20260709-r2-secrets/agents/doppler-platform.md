# Run E / Angle 2 — Doppler platform capabilities, 2026 state

Date: 2026-07-09. Analyst scope: Doppler's current platform surface relevant to
ray-manaloto/dotfiles (service tokens vs service accounts, CLI auth models, GHA
action + GitHub sync, webhooks, versioning/rollback, rotated/dynamic secrets,
solo-dev pricing limits, api.doppler.com endpoints for web-session allowlisting),
plus a gap assessment against the repo's current wiring.

Sources: docs.doppler.com (not in the local mintlify cache — inventory report
line 107 confirms; all fetched live 2026-07-09), doppler.com/pricing, GitHub
(DopplerHQ/cli, DopplerHQ/secrets-fetch-action). Repo baseline:
`docs/research/runs/research-20260709-r2-inventory/report.md` and files cited below.

**Verification pass (2026-07-09, second analyst sweep):** every load-bearing
claim below was re-probed against the live primary source
(docs.doppler.com/{docs/service-tokens,docs/service-account-identities,
docs/webhooks,docs/github-actions,docs/versioning,docs/secrets-rotation,
reference/api}.md, doppler.com/pricing, both GitHub release pages). Result:
F1/F3/F4/F5 confirmed verbatim; **two corrections applied inline** —
(a) `secrets-fetch-action` v2.0.0 is dated **2025-03-19, not 2026-03-19**
(F2), and (b) Developer-tier API rate limits ARE documented (resolves the
former U1; folded into F5). One strengthening fact added to F6 (CLI 3.76.0
fallback-file improvements).

## Findings

### F1. Token/auth model taxonomy (the decision-relevant part)

Doppler has five relevant auth primitives (all accepted as bearer tokens against
the same API — https://docs.doppler.com/reference/api, fetched 2026-07-09):

| Primitive | Scope | Write? | Plan | Fit for this repo |
|---|---|---|---|---|
| **CLI token** (`doppler login`) | user, whole workplace | yes | all; **5/user on free tier** | current host-Mac auth for `initializeCommand` |
| **Personal token** | user | yes | all | avoid in automation |
| **Service token** | ONE project+config, read-only by default; optional write at creation; **ephemeral variant with `--max-age`** (e.g. `--max-age 1m`) | opt-in | all; **50 on free tier** | the right primitive for CI / web sessions / any headless consumer |
| **Service account** (API tokens 0..n) | workplace-level, multi-project, role+per-project permissions; default zero access | configurable | **Team/Enterprise only** | not available on free plan |
| **Service account identity (OIDC)** | short-lived token exchanged for a CI OIDC token (`doppler oidc login` / `POST /v3/auth/oidc`); GitHub Actions, Kubernetes, any OIDC provider | n/a | **Team/Enterprise only** | the no-static-secret CI path — plan-gated |

Sources: https://docs.doppler.com/docs/service-tokens,
https://docs.doppler.com/docs/service-accounts,
https://docs.doppler.com/docs/service-account-identities (all fetched
2026-07-09). Token precedence in the CLI: `--token` flag >
`DOPPLER_TOKEN` env var > directory-scoped config (`doppler setup`, incl.
`doppler.yaml` for monorepos) > interactive login session
(https://docs.doppler.com/docs/cli). Service-token revocation is immediate and
irreversible, but the CLI keeps serving from an encrypted fallback file if one
exists (service-tokens doc).

**Consequence for the domain recommendation:** on the free Developer plan the
only non-interactive auth primitive is the project+config-scoped read-only
service token (50 available — plenty). GitHub-OIDC-to-Doppler exists and is the
best-practice CI path, but it is Team-gated ($21/user/mo), so free-tier CI and
Claude-web sessions must carry a `DOPPLER_TOKEN` service token as a stored
secret (GitHub Actions secret / web environment env var respectively). The
ephemeral `--max-age` option mitigates blast radius where a token can be minted
just-in-time.

### F2. GitHub Actions: two official delivery paths, both current in 2026

1. **Pull at job time — `DopplerHQ/secrets-fetch-action`**: v2.0.0 released
   **2025-03-19** (Node 24 upgrade; 9 releases total, v1.3.1 2024-12-03;
   https://github.com/DopplerHQ/secrets-fetch-action/releases, re-verified
   2026-07-09 — the action's last release is ~16 months old, i.e. stable but
   slow-moving, not "current-2026"). Inputs: `doppler-token`, `doppler-project`/`doppler-config`
   (required for service-account auth), `auth-method: oidc` +
   `doppler-identity-id` (OIDC, Team plan), `inject-env-vars` (env vars instead
   of step outputs). Automatically masks secret values in logs except
   DOPPLER_PROJECT/ENVIRONMENT/CONFIG metadata and "unmasked"-visibility
   secrets.
2. **Push ahead of time — GitHub sync integration**: the Doppler GitHub App
   continuously one-way-syncs a config's secrets into GitHub **repository,
   environment, or organization** Actions secrets (also Codespaces and
   Dependabot); creates three `DOPPLER_*` bookkeeping secrets; "unmasked"
   secrets can sync as GitHub **variables** instead
   (https://docs.doppler.com/docs/github-actions and
   https://docs.doppler.com/docs/enclave-github-actions, fetched 2026-07-09).
   Counts against the plan's "config syncs" quota — **5 on the free tier** (F5).
   No plan gating on the integration itself is documented.

The sync path needs **zero Doppler tokens in CI** (secrets arrive as native
GitHub secrets with GitHub's own masking) and zero api.doppler.com calls at job
time; the fetch-action path keeps Doppler authoritative at run time but puts a
`DOPPLER_TOKEN` in GitHub secrets (or requires Team-plan OIDC). For this repo's
tiny CI secret set (GitHub App creds are GitHub-native already; a future
EXA/BRAVE/ANTHROPIC key for CI research jobs would be the first real consumer),
the **sync integration is the lower-operational-cost path** on the free plan.

### F3. Webhooks can close the "secret changed → rebuild" loop

Doppler webhooks fire on `config.secrets.update` per enabled config, POST a
JSON payload including a `diff` (added/removed/updated secret names — names,
not values), support a **custom payload**, and optional HMAC-SHA256 signing via
`X-Doppler-Signature`. The docs explicitly point at GitHub's
`workflow_dispatch` API as a supported target, i.e. a Doppler secrets change
can directly trigger a GHA workflow (https://docs.doppler.com/docs/webhooks,
fetched 2026-07-09). Free tier includes **5 webhooks** (F5).

Fit here: a webhook → `workflow_dispatch` (or `repository_dispatch`) on
`ci.yml` would re-publish `:dev` when the `dotfiles/dev` config changes —
relevant because the devcontainer only re-reads secrets at container creation
(`--env-file` is create-time-only), so a rotation today silently requires a
manual `mise run up`. Note: syncing to GitHub secrets (F2 path 2) does NOT
trigger workflows by itself — GitHub secret updates are not workflow events —
so the webhook is the only change-driven trigger primitive. Caveat: the
webhook's custom-payload + auth-header shape must carry a GitHub PAT/App token
to call the GitHub API; that's a second secret to manage, or point the webhook
at an intermediary.

### F4. Versioning/rollback is strong and un-gated; rotation/dynamic are gated

- **Versioning**: every config action is recorded git-log-style; "every version
  of a secret is retained for the lifetime of that secret (i.e., until it's
  deleted)"; rollback is per-operation via a "Rollback Changes" button in the
  dashboard log viewer (https://docs.doppler.com/docs/versioning, fetched
  2026-07-09). No plan gating documented on secret-version retention itself —
  but see the 3-day **activity log** retention on free tier (F5) and U2.
- **Rotated secrets**: Team+ ("Automatic secret rotation" listed under Team on
  the pricing page). Mechanism: each rotated secret holds **two credential
  instances, one active**; halfway through each interval they swap, the
  incoming one being freshly rotated in the target service; consumers that
  fetch at least every 2×N days always hold a valid credential
  (https://docs.doppler.com/docs/secrets-rotation +
  https://www.doppler.com/blog/doppler-secrets-rotation-core-logic). Supported
  targets are per-integration pages (SendGrid, Azure Service Principal, AWS
  Lambda proxied rotation, databases, …) — the rotation doc itself only
  defines the generic issuer/updater methods; the docs.doppler.com llms.txt
  index and a targeted search (2026-07-09) surface **no "rotate an arbitrary
  SSH keypair" or GitHub-deploy-key integration**, so a Doppler-rotated
  deploy key is not an off-the-shelf feature at any tier.
- **Dynamic secrets** (AWS IAM / Azure SP): **Enterprise only** (pricing page).

**Consequence for the R2/SSH decision:** Doppler cannot, on any plan Ray would
plausibly buy, automatically rotate a GitHub deploy key. A
secrets-manager-delivered SSH key would be static-at-rest with manual rotation.
That materially weakens the "move R2 to Doppler-delivered deploy keys" option
versus keeping DD agent-forwarding (key never at rest in container, zero
rotation burden).

### F5. Free (Developer) tier limits — the solo-dev budget envelope

From https://www.doppler.com/pricing (fetched 2026-07-09): free for 3 users
($8/mo per extra); **10 projects, 4 environments, 10 configs/env; 3 days
activity log retention; 5 config syncs; 5 webhooks; 50 service tokens; 5 CLI
tokens per user**; basic alerting (Email/Slack/Teams/Discord). Team =
$21/user/mo: 90d logs, 100 syncs, 50 webhooks, 500 service tokens, service
accounts, automatic rotation, trusted IPs, SAML. Enterprise adds dynamic
secrets, EKM, custom rate limits. API rate limits by plan (all documented at
https://docs.doppler.com/reference/api.md, re-verified 2026-07-09):
**Developer 240 reads/min, 120 secret-reads/min, 60 writes/min**; Team 480/240/120;
Enterprise 480/480/240 — the free tier's 120 secret-reads/min is orders of
magnitude above this repo's call volume (a handful of reads per `mise run up`
/ CI job).

The repo's entire current + projected surface (1 project `dotfiles`, configs
`dev`/`dev_personal`, ≤3 service tokens for CI + web + a possible self-hosted
updater, 1-2 syncs, 1 webhook) fits inside the free tier with wide margin. The
only free-tier feature gaps that matter here: no OIDC (F1), no rotation (F4),
3-day activity log (U2).

### F6. Endpoints & offline behavior — web-session and airplane cases

- **Runtime endpoint is exactly one host**: `https://api.doppler.com` (API base
  `https://api.doppler.com/v3`), overridable via `DOPPLER_API_HOST`. Install
  paths: `cli.doppler.com` (install.sh) or `packages.doppler.com` (apt/gpg —
  also mirrored in the fnox docs cache,
  `docs/research/mintlify-cache/jdx/fnox/llms-full.txt:4474-4479`). Dashboard
  `dashboard.doppler.com` is browser-only. This matches Run A's allowlist
  recommendation verbatim
  (`docs/research/runs/research-20260709-r2-web-env/agents/network-allowlist.md:138-140`):
  Claude-web needs a Custom allowlist with `api.doppler.com` (+ an install
  host, or bake the CLI into the image — note **fnox is already in the image
  runtime tier**, `.devcontainer/mise-runtime.toml:41`, and speaks to Doppler
  via its own client with `DOPPLER_TOKEN`, which would avoid the CLI-install
  hosts entirely; cross-ref Run D). The CLI is Go; api.doppler.com behind the
  web env's HTTPS proxy should work via standard Go proxy env handling, but
  this is unprobed (U3).
- **Offline**: `doppler run` writes an encrypted snapshot (PBKDF2 +
  AES-256-GCM) to `$HOME/.doppler/fallback` and automatically falls back to it
  after a ~50-60s unreachability timeout; `--fallback-only` forces offline
  mode; decryption is bound to the generating token unless `--passphrase` is
  used (https://docs.doppler.com/docs/automatic-fallbacks, via search
  2026-07-09). **The repo's `--no-file` + shell redirect opts out of all of
  this** — see F7.
- CLI currency: v3.76.0 (2026-04-22), v3.75.3 (2026-02-17), v3.75.2
  (2026-01-27) — actively maintained
  (https://github.com/DopplerHQ/cli/releases, re-verified 2026-07-09).
  Notably, **3.76.0 added "support fallback files and caching when mounting
  to any file format"** plus curl timeout/retry flags in the install script —
  the fallback machinery (F7 item 1) is under active investment, reinforcing
  that the repo's `--no-file` opt-out is swimming against the tool's grain.
  Attribution caveat: `DOPPLER_API_HOST` is a CLI-level override (CLI docs /
  release notes), not mentioned on the API reference page itself as fetched.

### F7. Gap assessment — what the repo is NOT using that it should

Current wiring (verified): host-side `doppler secrets download --format docker
--no-file … > ~/.local/state/dotfiles/doppler.env` in `initializeCommand`
(`.devcontainer/devcontainer.json:198`), authenticated by Ray's interactive
`doppler login` CLI token; `runArgs --env-file` (`devcontainer.json:84-90`);
no Doppler anywhere in CI.

1. **Offline fragility + self-clobbering download (fix regardless of any
   migration).** The `> doppler.env` redirect truncates the previous good env
   file *before* `doppler` runs; if api.doppler.com is unreachable the `[ -s ]`
   guard fails and `mise run up` is dead — AND the last good snapshot was just
   destroyed. Doppler's native answer (fallback files, F6) is explicitly
   disabled by `--no-file`. Minimal fix: download to a temp file and `mv` on
   success (keeps last-good on failure); fuller fix: `doppler secrets download`
   without `--no-file` for an encrypted at-rest snapshot, or accept last-good
   with a staleness warning.
2. **No service token anywhere.** Fine for the Mac host (interactive login is
   the intended dev-machine mode), but any new headless consumer — GHA research
   jobs, a self-hosted updater runner, Claude-web sessions — should get its own
   **read-only service token scoped to `dotfiles/dev`** (or a dedicated
   `ci`/`web` config so revocation/blast-radius is per-consumer). 50 free-tier
   tokens make per-consumer tokens costless. Web caveat from Run A: the web
   env has no secret store, so `DOPPLER_TOKEN` sits as a plaintext env var in
   the environment config
   (`docs/research/runs/research-20260709-r2-web-env/agents/official-docs.md:43`) —
   scoped read-only + instant revocability is exactly the mitigation profile
   for that.
3. **No GitHub sync integration.** If/when CI jobs need AI/research keys
   (EXA/BRAVE/ANTHROPIC), sync `dotfiles/ci` → GitHub repo secrets (free: 5
   syncs) instead of introducing DOPPLER_TOKEN + fetch-action into workflows —
   fewer moving parts, native masking, no api.doppler.com dependency in CI.
   Keep the fetch-action in the back pocket for when run-time freshness
   matters; upgrade to OIDC only if a Team plan ever happens for other reasons.
4. **No webhook.** One free webhook → `workflow_dispatch` would make secret
   changes propagate to the published image / running consumers instead of
   waiting for the next manual `mise run up` (F3). Low priority until a secret
   actually rotates more than ~never, but it is the platform's answer to the
   "env-file is create-time-only" staleness inherent in the current design.
5. **Environments under-used but adequate.** `dotfiles/dev` + `dev_personal`
   is well within 4 envs × 10 configs; a `ci` (and possibly `web`) config to
   partition consumer blast-radius costs nothing and enables per-consumer
   sync/webhook/token scoping. Branch configs are the idiomatic Doppler way to
   do this.
6. **What NOT to adopt:** rotated secrets, dynamic secrets, service accounts,
   OIDC — all plan-gated (Team/Enterprise) and none load-bearing for this
   repo's threat model today. Do not architect around them on a free plan.

### F8. Doppler-side verdict on issue #83 (in-container fnox+doppler)

From this angle's evidence only (Run D owns the fnox side): the migration does
not add Doppler capability — the same project/config data arrives either way —
but it *changes the auth requirement*: in-container resolution needs a
credential inside the container (fnox's Doppler provider resolves
`token` → `FNOX_DOPPLER_TOKEN` → `DOPPLER_TOKEN` → interactive session, per the
cached fnox docs, `docs/research/mintlify-cache/jdx/fnox/llms-full.txt:4526-4533`),
whereas today the container holds only the *values*, never a Doppler
credential. That is a real security regression vector unless the in-container
token is a read-only service token — and it adds api.doppler.com as a runtime
dependency inside every consumer environment (incl. web allowlisting). The
host-side download keeping credentials out of the container is a defensible
architecture to keep; #83's payoff must come from fnox-side benefits (lazy
resolution, per-directory scoping, non-devcontainer consumers), not Doppler-side
ones.

## Uncertainties / gaps

- **U1 — RESOLVED (2026-07-09 verification pass)**: Developer-tier API rate
  limits are documented — 240 reads/min, 120 secret-reads/min, 60 writes/min
  (https://docs.doppler.com/reference/api.md). No longer a gap.
- **U2 — Rollback window vs 3-day activity log on free tier**: the versioning
  doc says secret versions persist for the secret's lifetime, while the
  pricing page caps *activity log* retention at 3 days (Developer). Whether
  the dashboard rollback UI (driven from config logs) can reach back past 3
  days on the free plan is untested. Assume rollback beyond 3 days may be
  unavailable on free.
- **U3 — Doppler CLI behind the Claude-web HTTPS proxy**: expected to work
  (Go net/http honors HTTPS_PROXY; `DOPPLER_API_HOST` exists as an escape
  hatch) but not probed in a live web session. Same caveat as Run A's U1 for
  mise. A one-shot probe (`DOPPLER_TOKEN=… doppler secrets --only-names`)
  in a real web session with `api.doppler.com` allowlisted settles it.
- **U4 — The three `DOPPLER_*` bookkeeping secrets** created by the GitHub
  sync are not named in the docs page as fetched; names unknown (cosmetic).
- **U5 — Ephemeral service-token minting** requires an authenticated caller
  (dashboard/CLI/API) at mint time; for fully unattended consumers the
  practical shape is still a long-lived read-only token. The `--max-age`
  option is most useful for human-initiated short sessions.
- **U6 — Webhook plan gating**: the webhooks doc states no tier restriction;
  the pricing page lists "5 webhooks" under Developer, which I read as
  free-tier-included with a count cap. Not double-confirmed against a
  second source.

## GitHub repos touched

- [DopplerHQ/cli](https://github.com/DopplerHQ/cli) — CLI releases/currency, install hosts, fallback behavior.
- [DopplerHQ/secrets-fetch-action](https://github.com/DopplerHQ/secrets-fetch-action) — official GHA action inputs, v2.0.0 (2026-03-19), OIDC support.
- [jdx/fnox](https://github.com/jdx/fnox) — via local mintlify cache only: Doppler provider config + token precedence (llms-full.txt:4455-4545).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — baseline wiring read from working tree (devcontainer.json:84-90,198; mise.toml:186,212,519-540; suites.toml:443-452; scripts/devcontainer-smoke.sh:91-104; mise-runtime.toml:41).
