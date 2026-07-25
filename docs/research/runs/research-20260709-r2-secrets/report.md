# Run E — Secrets into devcontainer/CI/web: Doppler vs fnox vs alternatives, incl. the SSH/R2 model

Date: 2026-07-09 (research) / 2026-07-10 (synthesis, re-run with genuine adversarial verdicts — the earlier 0-vote "all REFUTED" run was a credit-failure artifact and is superseded by this one). Synthesis of five angle reports (`docs/research/runs/research-20260709-r2-secrets/agents/{full-secret-map,doppler-platform,fnox-division,alternatives,ssh-r2-model}.md`), a 3-vote adversarial verification pass over the 10 most load-bearing claims, cross-referenced with Run A (`docs/research/runs/research-20260709-r2-web-env/report.md`) and grounded in `docs/research/runs/research-20260709-r2-inventory/report.md`.

---

## Executive summary — RECOMMENDATION

**Keep the current two-island architecture's devcontainer half exactly as-is, harden its two real bugs, give the unused fnox pin one narrow job (or retire it), leave CI untouched, and keep Docker-Desktop SSH agent-forwarding as R2 while adding git-over-HTTPS as an additive second lane. Reject issue #83's in-container "migrate to mise-env-fnox with doppler provider" as currently written — it is not what issue #83 actually proposes, fnox's own vendor docs now say "we do not recommend" that plugin, and it trades a today-zero in-container Doppler credential for an at-rest one with no freshness gain.**

### Target architecture, by consumer

| Consumer | Manager | Delivery | Change from today |
|---|---|---|---|
| Devcontainer | Doppler (system of record) | host `initializeCommand` → `doppler secrets download` → `doppler.env` → `runArgs --env-file` (create-time) | **No architecture change.** Fix download self-clobbering + canary-gate weakness (see migration deltas). |
| GHA CI (build/smoke/promote/cleanup) | GitHub-native secrets | ephemeral per-run `GITHUB_TOKEN`; `REFRESH_APP_ID`/`REFRESH_APP_PRIVATE_KEY` → short-lived App installation token | **No change.** If CI ever needs a Doppler-managed key (EXA/BRAVE/ANTHROPIC for a research job), prefer Doppler's GitHub sync integration over `DopplerHQ/secrets-fetch-action`. |
| fnox (web sessions, optionally CI) | fnox `age` provider, narrow adapter role | committed age-encrypted ciphertext in `fnox.toml`, decrypted with one `FNOX_AGE_KEY` env var, resolved via `fnox exec -- <cmd>` | **New, narrow build** — the only path that works under Claude-web's default Trusted egress policy (Doppler's `api.doppler.com` is blocked there). If not built soon, retire the unused `"fnox" = "latest"` pin. |
| Claude-web | none today | nothing — no gate needs secrets | **No change today.** If a future web workflow needs API keys, use the fnox-age adapter above, not Doppler directly. |
| Self-hosted updater runner (hypothetical) | GitHub App installation token (git) + fnox-age or a dedicated Doppler service token (secrets), if/when it exists | n/a — no runner exists yet | **No change** — design the provisioning path when the runner is actually built. |
| SSH/R2 (devcontainer outbound) | Docker Desktop magic-socket agent forwarding (unchanged) + git-over-HTTPS as additive lane | `/run/host-services/ssh-auth.sock` bind-mount; App installation tokens for the HTTPS lane | **Keep (a); add (e) additively.** Do not deliver a static deploy key. |

### What NOT to change

- **Do not move the devcontainer off host-side Doppler download.** It is the only point in the whole stack where zero Doppler credential ever enters the container — a stronger security posture than any in-container alternative evaluated.
- **Do not adopt the mise-env-fnox plugin** for anything. fnox's own live docs state verbatim: *"We do not recommend using fnox through the jdx/mise-env-fnox env plugin. It is an incomplete experiment and does not track every fnox feature."* (fnox-division.md F1, A1).
- **Do not switch the secrets-manager platform.** 1Password service accounts are structurally worse for this footprint (1,000 req/24h account-wide cap on Individual/Families, no vault access without restructuring, no offline fallback). Infisical is a credible fallback, not a reason to migrate today (zero current pain, real migration cost). Teller is dormant. Keep all three off the roadmap unless Doppler's free tier materially shrinks.
- **Do not deliver SSH keys via any secrets manager (Doppler or fnox) into the devcontainer.** A delivered deploy key is a non-expiring, at-rest credential; GitHub's own docs recommend Apps instead of deploy keys for exactly this reason.
- **Do not adopt SSH certificates for R2.** Eliminated on capability, not taste — GitHub only honors SSH-CA-signed certs for GitHub Enterprise Cloud/GHES orgs; `ray-manaloto/dotfiles` is a personal repo and github.com will not accept a cert-based identity for it, full stop.
- **Do not architect around Doppler's rotation/dynamic-secrets/service-accounts/OIDC features** — all are Team/Enterprise-gated and none is load-bearing for this repo's threat model on the free plan.
- **Do not keep GitHub Environments/Actions secrets as anything other than what they already are** — they're used correctly today (least-privilege ephemeral token + App installation token) and cannot serve any non-CI consumer.
- **Do not pre-emptively rewrite R2's durable AGENTS.md criteria** based on this research alone — promoting the HTTPS lane into the durable-criteria table requires Ray's explicit sign-off per the durable-criteria governance rule; this report recommends, it does not authorize.

---

## 1. Full secret-set coverage across all consumers — where the gaps are

Nine secret classes exist today (`agents/full-secret-map.md` F1, independently file:line re-verified in the adversarial pass):

| Class | What | Store | Delivery | Consumers |
|---|---|---|---|---|
| S1 | Doppler API keys: `EXA_API_KEY`, `BRAVE_API_KEY`, `GEMINI_API_KEY`, `GITHUB_TOKEN` (PAT-in-Doppler) | Doppler project `dotfiles`/config `dev` | host `initializeCommand` → `doppler secrets download --format docker` → `~/.local/state/dotfiles/doppler.env` → `runArgs --env-file` (`.devcontainer/devcontainer.json:198`, `:84-90`) | Devcontainer only |
| S2 | Doppler host-CLI auth (personal `doppler login` token) | Doppler account / host machine | implicit, assumed-authenticated host CLI (`scripts/devcontainer-smoke.sh:96`) | Devcontainer bootstrap (host side) |
| S3 | CI ephemeral `GITHUB_TOKEN` | GitHub Actions, auto-minted per run | `secrets.GITHUB_TOKEN`, `persist-credentials: false` everywhere | GHA build/smoke/promote/cleanup |
| S4 | Build-time bake secret | pass-through of S3 | `docker-bake.hcl:66-68` `id=github_token,env=GITHUB_TOKEN` | BuildKit build stage |
| S5 | GitHub App creds for refresh auto-merge | GitHub repo Actions secrets (`REFRESH_APP_ID`/`REFRESH_APP_PRIVATE_KEY`) | `actions/create-github-app-token` (`refresh.yml:66-71`), contract `ci.refresh-uses-app-token` (`suites.toml:625-637`) | `refresh.yml` only |
| S6 | SSH (R1 inbound / R2 outbound) | R2: no client key material at rest (DD magic socket); R1: public keys only via `ssh-add -L` | `devcontainer.json:96,189,200,207`; `docker.py:51-91` | Devcontainer only, Docker-Desktop-dependent |
| S7 | AI-CLI OAuth tokens (Claude Code, Codex, Gemini) | each CLI's own login flow, persisted in the named home volume | no declarative delivery path (PR #80 removed the earlier bind mounts) | Devcontainer, ad hoc |
| S8 | fnox | binary shipped, unconfigured, zero call sites | `.devcontainer/mise-runtime.toml:41` | none today |
| S9 | Leak prevention (not a secret) | gitleaks + repo allowlist | `hk-common.pkl:65-67`, `mise.toml:75-79` | pre-commit |

**Notably absent by design**: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, a service-token-class `DOPPLER_TOKEN`, any 1Password/Infisical/Vault/sops reference anywhere in the repo. The AI CLIs are OAuth-subscription authenticated, not API-key authenticated (issue #83) — intentional, not a gap.

### The core finding — CONFIRMED 3/3 (unanimous, four independently re-derived checks incl. a live 2026-07-10 fetch of the Claude Code web docs)

**The architecture is two disjoint secret islands.** Doppler serves exactly one consumer (the devcontainer). GitHub-native secrets serve exactly one platform (GHA). Claude-web and any hypothetical self-hosted updater runner sit on **neither island, with no provisioning path today**. The web docs state verbatim: *"A dedicated secrets store is not yet available… visible to anyone who can edit that environment"* (verified live, code.claude.com/docs/en/claude-code-on-the-web, fetched 2026-07-10). The only crossover between islands is the *name* `GITHUB_TOKEN` — two unrelated tokens (a long-lived PAT in Doppler vs. an ephemeral per-run GHA token), not a shared secret.

### Delivery-path weak points inside the devcontainer island — CONFIRMED 3/3

1. **Create-time snapshot, not runtime resolution.** `--env-file` is read only at `docker create` (Docker's own reference docs confirm no live-reload mechanism); rotating a Doppler key requires a full container recreate. `devcontainer.json:198` re-downloads `doppler.env` on every `mise run up`, but that only reaches a freshly created container — a reused one keeps its env from creation time.
2. **The canary threshold is exploitable, not just weak.** `verify-secrets` S1 (`mise.toml:518-541`) checks only that the env file exists, is non-empty, and contains the two metadata keys `DOPPLER_PROJECT`/`DOPPLER_CONFIG`. Smoke tier-2 (`scripts/devcontainer-smoke.sh:91-104`) passes at ≥3 of 7 canary keys — and 3 of the 7 (`DOPPLER_PROJECT`/`CONFIG`/`ENVIRONMENT`) are Doppler-injected metadata present on *every* download regardless of real secret content. **A download containing zero real secrets passes both gates.** This is confirmed by two independent verifiers, including corroboration that `DOPPLER_PROJECT`/`CONFIG`/`ENVIRONMENT` are Doppler-reserved variables auto-injected on every `doppler run`/`download` call.
3. **The doppler CLI is the single most security-critical host binary yet the only secrets-critical tool managed outside mise** — CONFIRMED 3/3. No entry in `mise.toml`, `shared.toml`, `mise-system.toml`, or `mise-runtime.toml` (confirmed by a full re-grep of every `[tools]` table); personal-login-token authenticated; invisible to the repo's lockfile/tool-currency machinery. `.devcontainer/AGENTS.md:47` itself states "No doppler CLI, fnox, or service token needed inside the container" — confirming doppler runs purely host-side, outside every manifest. A mise registry short-name (`doppler` → `github:DopplerHQ/cli`) exists, so bringing it under mise management is low-risk and independent of every other decision in this report.
4. **The self-clobbering download** (a bug, not architecture): `doppler secrets download … > doppler.env` truncates the last-good file *before* the network call runs. If `api.doppler.com` is unreachable, the `[ -s ]` guard fails and the last good snapshot was already destroyed. Fix is mechanical: download to a temp file, `mv` on success.
5. **Rotation topology is at least three manual surfaces, not two** — this is a **REFUTED** correction to a claim in the underlying research artifact; see the Refutations section below.

Bottom line on coverage: the two consumers the current architecture serves are served well (mod the two bugs above); the two consumers it doesn't serve (Claude-web, hypothetical updater runner) have **zero provisioning path**, and closing that gap is the primary architectural decision this research resolves (§2.3).

---

## 2. Doppler vs fnox division of labor — issue #83

### 2.1 Issue #83 is mischaracterized in `.devcontainer/AGENTS.md` — CONFIRMED 3/3

Issue #83's actual title is **"Research: devcontainer OAuth token injection for AI CLIs"** (opened 2026-04-10, still open — verified via a live GitHub API fetch, not just the repo's summary of it). Its own body states verbatim: *"Doppler/fnox (designed for static API keys) is not the right tool for OAuth tokens that are managed/refreshed by each CLI's own login flow."* It quotes the mise-env-fnox author's own caveat, independently confirmed against the live README: *"fnox was built as a separate CLI for a reason. I would probably advise avoiding this."*

The `.devcontainer/AGENTS.md:54-55` "Future:" note — *"migrate to mise-env-fnox with doppler provider inside the container for runtime secret resolution (#83)"* — describes the opposite of what #83 concludes. **Static-secret delivery architecture (this report) and OAuth token injection (#83's actual, still-open, still-hard problem) must be treated as separate problems.** Correct the AGENTS.md note in the same change that closes out this research (see migration deltas).

### 2.2 Technically feasible, vendor-discouraged — CONFIRMED 3/3

fnox does support Doppler as a provider (`crates/fnox-core/src/providers/doppler.rs` on `jdx/fnox` main, current at v1.30.0 as of 2026-07-09), so an in-container mise-env-fnox+doppler wiring is technically possible. But feasibility and advisability diverge sharply:

- **The vendor's own current docs recommend against it, not just the plugin author.** The live fnox Mise Integration guide (fnox.jdx.dev/guide/mise-integration.html, fetched 2026-07-09) states: *"We do not recommend using fnox through the jdx/mise-env-fnox env plugin. It is an incomplete experiment and does not track every fnox feature."* Ranked alternatives: (1) shell integration, (2) `fnox exec` inside mise tasks, (3) the plugin, last and discouraged.
- **mise-env-fnox fails OPEN on error and caches the failure.** Offline/unreachable/bad-token conditions print a `[fnox]` warning but load an *empty* environment rather than aborting, and mark that empty result `cacheable = true` — so with `MISE_ENV_CACHE=1` a transient outage can pin a silently empty secret set. This is precisely the false-green shape `.claude/rules/verify-before-advancing.md` exists to prevent.
- **No real freshness win.** mise's env-cache invalidation is `fnox.toml`-mtime-based only, not tied to upstream secret rotation — so the "fresh secrets" argument for in-container resolution mostly evaporates once you enable the caching needed for acceptable latency (every uncached shell activation pays a `fnox export` → `doppler secrets get` subprocess + network round-trip).
- **Strictly worse offline than today.** Doppler's automatic encrypted fallback file is documented only for `doppler run`; the `doppler secrets get` subcommand fnox's provider shells out to has **no documented offline fallback** — worse than today's frozen host-side env file, which needs no runtime network at all once created.
- **A real security regression vector.** Today, zero Doppler credential ever enters the container. In-container resolution requires a `DOPPLER_TOKEN` service token at rest inside the container to bootstrap everything else.

**Net verdict: reject the in-container mise-env-fnox+doppler migration as currently sketched. Keep host-side Doppler download as the sole devcontainer secrets path.**

### 2.3 Where fnox genuinely earns its place — the web/CI age-provider adapter

The one place fnox adds coverage the host-side Doppler download structurally cannot reach is **Claude-web**, because `api.doppler.com` sits outside the default Trusted allowlist (Run A, CONFIRMED 3/3) and reaching it there requires a Custom allowlist entry plus a stored `DOPPLER_TOKEN` sitting as a plaintext web-environment env var. fnox's `age` provider is categorically different from every other provider it ships: **zero network at resolve time** — ciphertext committed inline in a `fnox.toml`, decrypted locally with a key from `FNOX_AGE_KEY` (which can even be an existing SSH key). This is the **only candidate that works under Claude-web's default Trusted policy with no Custom allowlist change at all.**

This is a genuine complementary division of labor, not competition: Doppler stays the platform of record (dashboard, versioning, `doppler set`); fnox-age is a narrow, offline-tolerant export format for the handful of low-blast-radius keys (EXA/BRAVE research keys) a web session or offline laptop needs. Use `fnox exec -- <cmd>` (the vendor-endorsed pattern), **not** shell-activation injection via mise-env-fnox. Cost: a dual-write (secret lives in Doppler *and* as age ciphertext in git) — acceptable for the current tiny key set, auditable via git history, rotation is an explicit re-encrypt.

**If this adapter role is not built in the near term, retire the unused `"fnox" = "latest"` pin from `.devcontainer/mise-runtime.toml:41`** per `.claude/rules/tool-currency-and-native-first.md` rule 3 — a tool with zero call sites and zero committed config is dead weight, not optionality.

(Note, not a recommendation: fnox also ships an MCP stdio-broker mode conceptually attractive for keeping API keys out of agent env vars, but native registration would be blocked by this repo's `no_mcp_registration` hk step; only a process-spawn invocation via `mcp2cli` would be permissible. Not pursued here.)

---

## 3. Independent alternatives on 2026 merits

Full comparison in `agents/alternatives.md` F8:

| Option | Verdict | Why |
|---|---|---|
| **1Password service accounts + `op`** | Not worth switching | Individual/Families plan caps at **1,000 requests/24h per account** — a per-shell resolution pattern would burn that fast, 429-ing the whole account for up to 24h; service accounts can never access the built-in Personal vault (requires restructuring secrets into dedicated vaults); no documented offline fallback for `op run` (worse than Doppler); no programmatic token list/revoke, only web-UI cleanup. |
| **1Password SSH agent** | Optional host-side hardening only, doesn't move R2 | Rides the exact same DD magic-socket mechanism the repo already uses — just relocates where the private key rests on the host (1P vault vs `~/.ssh`). Doesn't unblock Colima, doesn't help web sessions, adds unofficial container-forwarding glue (recurring "connection refused"/"permission denied" community reports). |
| **Infisical (cloud/self-host)** | Fallback, not now | Credible OSS like-for-like replacement (MIT, 27k★, free for 5 identities; self-host is genuinely unlimited but a real 24/7 Postgres+Redis operational tax). Two features genuinely ahead of the current Doppler wiring: OIDC machine identities for GHA (zero stored CI token) and a self-host exit ramp if Doppler's free tier ever shrinks. Zero current pain, real migration cost — hold as the designated fallback. fnox already has an Infisical provider, so a later migration wouldn't orphan the fnox layer. |
| **sops/age (git-committed, incl. mise's native support)** | Adopt — as the fnox-age variant | The only alternative that fills a real gap: zero network at resolve time, the only option that works in Claude-web under the default Trusted policy, no service dependency, no rate limits. mise's native SOPS/age support is real but explicitly marked experimental and age-only; fnox's age provider covers the same niche with a maintained, non-experimental surface and one config file instead of two — prefer fnox-age (§2.3) over raw sops. |
| **teller** | Dormant, do not adopt | Last real release 2024-05-20 (a single 4-commit burst on 2026-01-27 is the only activity since); fnox now covers its niche with active, real maintenance. |
| **GitHub Environments / Actions secrets** | Keep exactly as-is | Write-only after creation, not passed to fork-triggered workflows/Dependabot, environment gating available. Already used correctly today. Cannot serve devcontainer, laptop, or web — a delivery endpoint, not a manager. |
| **Doppler-compatible OSS beyond Infisical** (Phase, Keyshade, Bitwarden Secrets Manager) | None worth a look | No differentiator over Infisical for this footprint; Bitwarden Secrets Manager reachable later via fnox's own provider if ever needed. |

**Doppler GitHub-App sync vs `DopplerHQ/secrets-fetch-action` for CI** — CONFIRMED 2/3 on mechanism (see Refutations for the disputed detail): the sync integration pushes a config's secrets one-way into native GitHub Actions/Codespaces/Dependabot secrets with **zero Doppler tokens and zero `api.doppler.com` calls at job time** (free tier: 5 config syncs). This is the lower-operational-cost path versus the fetch-action if/when CI ever needs a Doppler-managed key (e.g., a future EXA/BRAVE/ANTHROPIC research-job key) — GitHub's own masking, no new secret to manage in workflows.

---

## 4. SSH/R2 model — agent-forwarding vs delivered keys vs hybrids

Five options evaluated (`agents/ssh-r2-model.md`, gate-rewrite matrix F6):

- **(a) Status quo — DD magic-socket agent forwarding. RECOMMENDED, keep.** Private key material never enters the container — the strongest at-rest property of any option; the container only ever sees signing *requests*, never key bytes. Trade-off: the live socket is a signing oracle — any process running as the socket owner can request signatures for every identity loaded in the Mac's agent, for any host, while the container runs (classic ssh-agent-hijacking risk class; the canonical real-world exemplar is the Matrix.org 2019 breach, where a compromised Jenkins box trapped forwarded agents and propagated production keys). The exposure is **transient** — it ends when the container stops, nothing is exfiltratable for later use. Both operational frictions are already durably solved or tracked: root:root socket reversion on DD restart is fixed via the double chown in both `postCreateCommand` and `postStartCommand` (`devcontainer.json:200,207`); the Docker-Desktop-only dependency is tracked in issue #78.
- **(b) Secrets-manager-delivered deploy key. REJECTED.** The key would be at rest inside the container (env var / tmpfs / the persistent home volume). GitHub deploy keys never expire and have no programmatic rotation — GitHub's own docs recommend GitHub Apps instead precisely because of the standing-write-credential risk (Read the Docs disabled write-access deploy keys platform-wide in 2025 for the same reason). Real delivery friction too: Docker's env-file format has no multiline support (a PEM key needs bespoke base64 wrap/unwrap machinery), and fnox's age provider doesn't support passphrase-protected SSH keys, so the delivered key would be unencrypted at rest either way.
- **(c) 1Password SSH agent. REJECTED for this decision.** Genuine security win (per-signature biometric prompts) exists only in the DD-forwarding sub-shape, which is *unofficial* (1Password's own forwarding docs cover `ssh -A` to remote hosts, not Docker/devcontainers) and relies on community glue. Adds a paid product with zero existing repo footprint to solve a problem (a) already solves; doesn't unblock Colima, doesn't help web sessions.
- **(d) Short-lived SSH certificates. ELIMINATED on capability, not preference.** GitHub only honors SSH-CA-signed certificates for organizations on GitHub Enterprise Cloud/GHES. `ray-manaloto/dotfiles` is a personal github.com repo — github.com will not accept a step-ca/Vault-issued certificate for it, regardless of the CA's quality. Moot immediately.
- **(e) Git-over-HTTPS with GitHub App installation tokens. RECOMMENDED as an additive second lane.** GitHub App installation tokens expire in ≤1 hour, are scoped to the app's repo/permission grant, and are already ~90% wired: CI already uses App tokens (`refresh.yml`); Claude-web sessions already use Anthropic's own GitHub proxy where SSH is neither needed nor useful; the devcontainer already has `gh` in the runtime tier plus a Doppler-delivered `GITHUB_TOKEN`. This — not a delivered deploy key — is what actually unblocks Colima (issue #78's worst case) and any future headless/self-hosted runner, with zero new secret infrastructure. Friction: `ssh -T git@github.com` as a smoke assertion would need an HTTPS-equivalent check (`gh auth status` / `git ls-remote`), and interactive `git@github.com:` remotes need a `url.insteadOf` rewrite or the gh credential helper.

**Gate impact**: R1 inbound (`mise run verify-ssh-inbound`, `mise.toml:490-516`) is unaffected by every option — it's a separate sshd feature with host-delivered `authorized_keys`, no dependency on the R2 agent socket. Promoting option (e) into R2's durable AGENTS.md criteria requires Ray's explicit approval per the durable-criteria governance rule — this report recommends it, it does not authorize it.

**A correction to the domain framing, not a change in decision**: "DD's `ssh-auth.sock` forwarding has no Colima equivalent" is **REFUTED** (see below) — Colima has a native `--ssh-agent`/`forwardAgent` mechanism targeting the same socket path; it's buggy (issues #942, #1330), not absent. This softens the urgency of a runtime-portability redesign but doesn't change the recommendation: run issue #78's own probe sequence before any migration decision, and prefer (e) over (b) if the probe fails.

---

## Migration deltas from the current baseline

1. **`.devcontainer/devcontainer.json` `initializeCommand` (~line 198)**: change the `doppler secrets download … > doppler.env` redirect to a download-to-temp-file-then-`mv` pattern, so a network failure never destroys the last-good snapshot before failing loud.
2. **`scripts/devcontainer-smoke.sh` tier-2 (~lines 91-104) and/or `mise.toml` `verify-secrets` S1 (~518-541)**: tighten the canary gate to require at least one *non-metadata* canary key present (e.g., `GITHUB_TOKEN`), not just ≥3 of 7 where 3 are always-present Doppler metadata — closing the "zero-real-secret download passes both gates" hole.
3. **`.devcontainer/AGENTS.md:54-55`**: replace the "Future: migrate to mise-env-fnox with doppler provider…" note with two corrected notes — (a) issue #83 is about OAuth token injection for AI CLIs and remains genuinely open/unsolved (do not conflate with static-secret delivery); (b) a new note describing fnox's narrow role as the web/CI `age`-provider adapter (§2.3), not an in-container Doppler replacement.
4. **`.devcontainer/mise-runtime.toml:41`**: either (a) build the fnox-age adapter — commit a `fnox.toml` with age-encrypted values for the low-blast-radius research keys, wire `fnox exec` into the web/CI consumer that needs them — or (b) retire the unused `"fnox" = "latest"` pin if no near-term consumer materializes.
5. **`mise.toml` `[tools]` (host tier) or `.config/mise/conf.d/shared.toml`**: add `doppler` as a managed mise tool (registry short-name `doppler` → `github:DopplerHQ/cli`) instead of an out-of-band personal-token host install, closing the "single most security-critical unmanaged tool" gap. Independent of every other decision above — low risk, do any time.
6. **(Requires Ray's explicit sign-off, per the durable-criteria rule)** Add `gh auth setup-git` as an additive HTTPS git lane in a lifecycle hook or opt-in mise task; if promoted into the gate, add an `gh auth status`/`git ls-remote` smoke assertion alongside (not replacing) the existing SSH tier-3 block; extend R2's durable-criteria table in root `AGENTS.md` with an explicit "or HTTPS-token path" clause only once approved.
7. **Repo docs (wherever the "two manual rotation points" framing lives)**: correct to "at least three manual rotation surfaces" — Doppler dashboard (EXA/BRAVE/GEMINI + PAT), GitHub repo Actions secrets (App creds), and host-side re-authentication (the `doppler login` personal CLI token and macOS SSH-agent identities) — per the REFUTED verdict below.
8. **Repo docs describing R2/Colima**: correct "Docker-Desktop-only, no Colima equivalent" to "Colima has a native but buggy `--ssh-agent` equivalent (abiosoft/colima#942, #1330) targeting the same socket path" — matches issue #78's own framing, which should be the canonical wording going forward.
9. **No repo diff, but a housekeeping action**: audit the scope/type of the `GITHUB_TOKEN` PAT stored in Doppler (classic vs fine-grained, permission set) before any migration work touches the S1 delivery path — this was never derivable from the repo alone (full-secret-map.md U2).
10. **Defer, do not build now**: per-consumer Doppler configs (`dotfiles/ci`, `dotfiles/web`) and service tokens — only worth doing once CI or web sessions have an actual Doppler-managed secret to deliver; building the partition ahead of a real consumer is premature.

---

## Refuted / unverified claims

### REFUTED (1/3 upheld) — "Rotation today collapses to exactly two manual points… everything else is ephemeral auto-minted"

The two named points (Doppler dashboard; GitHub repo Actions secrets for the App) check out at the file level, but the *completeness* assertion is contradicted by the same source document's own rotation table, which lists a third, non-collapsed surface: host-side SSH-agent identities and the Doppler personal CLI token (`doppler login`), both requiring manual macOS-keychain/re-auth — not ephemeral, not auto-minted. **Correct framing: rotation today has at least three manual surfaces**, not two.

### REFUTED (0/3 upheld) — "The DD `ssh-auth.sock` forwarding path has no Colima equivalent, so R2 hard-locks the repo to Docker Desktop"

Colima has a documented, native `--ssh-agent`/`forwardAgent` mechanism (`cmd/start.go`, colima.run/docs/configuration) that targets the identical `/run/host-services/ssh-auth.sock` convention inside the VM. The cited issues (abiosoft/colima#942, #1330) are bugs against an *existing* feature, not evidence of absence. **Correct framing: Colima has a buggy/unreliable equivalent, not no equivalent.** Issue #78 already frames this correctly (VM→container leg unprobed, not impossible); repo docs using the flatter "hard-locked" language should be corrected to match #78 (migration delta #8 above).

### CONFIRMED with a caveat (2/3) — "Zero key material anywhere in the stack" (SSH/R2)

The R2 client-side property — no private SSH key ever crosses into the container — is solid and independently corroborated (Docker's own `--ssh` docs, the `ssh-agent(1)` protocol, `docker.py:51-91`'s `ssh-add -L` public-keys-only usage). But the literal, unqualified claim is false: the R1 sshd feature (`ghcr.io/devcontainers/features/sshd:1`, `devcontainer.json:192`) auto-generates its own SSH **host** keypair inside the container via apt's `openssh-server` postinst — genuine private key material, just outside the R2 threat model and not manually rotated. **Use "R2 outbound has zero SSH client key material at rest," not "the container has zero SSH key material of any kind."**

### CONFIRMED but internally inconsistent on one date (2/3) — Doppler GitHub-sync vs `secrets-fetch-action` currency

Sync mechanics and free-tier limits (5 config syncs, one-way push, zero runtime token/API dependency) are independently confirmed by all three verifiers. One verifier dated `DopplerHQ/secrets-fetch-action` v2.0.0 to **2026-03-19** (~4 months old, actively maintained), contradicting the other two's **2025-03-19** (~16 months old, slow-moving) — same release, disputed year. **Do not cite a specific staleness figure for the fetch-action without re-checking the release page at decision time.** The directional recommendation (prefer GitHub sync over the fetch-action for this repo's CI needs) is unaffected either way, since it rests on operational-cost mechanics (zero stored token, zero runtime call), not on the action being abandoned.

### All other claims submitted to adversarial verification are CONFIRMED (3/3) without caveat

Two disjoint secret islands with Claude-web/updater-runner unprovisioned; create-time-only Doppler delivery with an exploitable weak canary gate; issue #83 is genuinely about OAuth injection, not static-key migration, and the repo's own AGENTS.md mischaracterizes it; the doppler CLI is unmanaged by mise while fnox ships unused; free-tier Doppler auth is service-token-only (no OIDC/service accounts, both Team/Enterprise-gated); fnox has a working Doppler provider making the in-container wiring technically feasible (even though it's inadvisable per §2.2).

---

## Open questions for Ray (with recommended answers)

1. **Fix the two devcontainer-Doppler bugs now?** → **Yes** — both are small, mechanical, and close a real "false-green secrets" hole (migration deltas #1-2).
2. **Build the fnox-age web/CI adapter, or retire fnox?** → **Build it**, narrowly scoped to `fnox exec` + committed age ciphertext, only if a near-term web or CI consumer for research keys is expected. If not within the next month or two, retire the unused pin — dead weight compounds tool-currency debt.
3. **Correct `.devcontainer/AGENTS.md:54-55`'s "Future:" note?** → **Yes, same change** as whichever of #2's two paths is chosen.
4. **Promote git-over-HTTPS (option e) into R2's durable criteria?** → **Recommend formalizing** as an explicit additive fallback clause — but this needs your sign-off before it's touched, per the durable-criteria rule.
5. **Run issue #78's Colima probe before any SSH portability decision?** → **Yes, first.** Colima's native forwarding may preserve model (a) off Docker Desktop entirely; don't default to a deploy-key redesign just because Colima's forwarding has open bugs.
6. **Bring the doppler CLI under mise management?** → **Yes**, low-risk, independent of every other decision here — do it any time.
7. **Audit the `GITHUB_TOKEN` PAT stored in Doppler (scope/type)?** → **Yes, before any work that touches the S1 delivery path** — its scope isn't derivable from the repo and gates what a migration can safely assume.
8. **Correct the "two manual rotation points" and "Colima hard-lock" framing wherever they're documented?** → **Yes** — both are now REFUTED as stated (see above); leaving the overclaim in place will mislead the next person who reads it.

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — all repo baseline evidence (devcontainer.json, mise.toml/shared.toml/mise-system.toml/mise-runtime.toml, workflows, docker-bake.hcl, smoke script, suites.toml, docker.py, AGENTS.md) across all five angles plus issues #78, #80, #83, #116 fetched via API.
- [jdx/fnox](https://github.com/jdx/fnox) — provider model (doppler/1password/infisical/bitwarden/age), `doppler.rs` source, releases (v1.27→v1.30.0), daemon + Mise Integration guide (live vendor recommendation against mise-env-fnox), CI/CD guide.
- [jdx/mise-env-fnox](https://github.com/jdx/mise-env-fnox) — plugin mechanics, caching/fail-open error handling, author warning, repo maturity (7 commits/15 stars/zero releases).
- [jdx/mise](https://github.com/jdx/mise) — `MISE_ENV_CACHE`/`env_cache` source, native sops/age secrets support, registry doppler short-name, fnox-positioning discussion #6779.
- [jdx/hk](https://github.com/jdx/hk) — install/mise-integration reference (Run A cross-reference).
- [DopplerHQ/cli](https://github.com/DopplerHQ/cli) — CLI auth model, service tokens, automatic-fallback scope (`doppler run` only, not `doppler secrets get`), release currency.
- [DopplerHQ/secrets-fetch-action](https://github.com/DopplerHQ/secrets-fetch-action) — official GHA fetch-action inputs/OIDC support; release-date discrepancy flagged in Refutations.
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — web-session secrets/egress facts (no dedicated secrets store; `api.doppler.com` absent from Trusted allowlist), issues #29910/#32733/#71629 (Run A cross-reference).
- [abiosoft/colima](https://github.com/abiosoft/colima) — issues #942/#1330: native `--ssh-agent` forwarding exists but is buggy (refutes the "no equivalent" framing).
- [docker/for-mac](https://github.com/docker/for-mac) — issue #4242: DD magic socket forwards only the launchd agent, not a custom `SSH_AUTH_SOCK`.
- [github/docs](https://github.com/github/docs) — deploy-key, GitHub App installation-token, and SSH-CA (GHEC-only) documentation.
- [cli/cli](https://github.com/cli/cli) — `gh auth setup-git` manual and credential-helper behavior for the HTTPS R2 lane.
- [1Password/load-secrets-action](https://github.com/1Password/load-secrets-action) — SSH-key formatting for `op read`.
- [1Password/onepassword-sdk-python](https://github.com/1Password/onepassword-sdk-python) — issue #221: no programmatic service-account lifecycle management.
- [1Password/onepassword-sdk-js](https://github.com/1Password/onepassword-sdk-js) — issue #180: rate-limit introspection gap.
- [rancher-sandbox/rancher-desktop](https://github.com/rancher-sandbox/rancher-desktop) — discussion #1842: VM→container agent-socket mount recipe, adjacent evidence for the Colima probe.
- [lima-vm/lima](https://github.com/lima-vm/lima) — `forwardAgent` mechanics underlying Colima's implementation.
- [matrix-org/matrix.org](https://github.com/matrix-org/matrix.org) — 2019 SSH-agent-hijacking postmortem, cited as the blast-radius exemplar for R2 option (a)'s signing-oracle risk.
- [readthedocs/readthedocs.org](https://github.com/readthedocs/readthedocs.org) — rationale for deprecating write-access deploy keys platform-wide, supporting the rejection of R2 option (b).
- [Infisical/infisical](https://github.com/Infisical/infisical) — OSS Doppler-alternative platform, pricing/self-host model.
- [Infisical/cli](https://github.com/Infisical/cli) — offline-mode feature-request gap (#216).
- [Infisical/secrets-action](https://github.com/Infisical/secrets-action) — OIDC machine-identity GHA auth.
- [tellerops/teller](https://github.com/tellerops/teller) — maintenance-state check confirming dormancy.
- [aquaproj/aqua-registry](https://github.com/aquaproj/aqua-registry) — mise's compiled-in registry, tool-install-path evidence.
