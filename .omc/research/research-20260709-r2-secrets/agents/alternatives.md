# Run E — Angle #4: Independent alternatives on 2026 merits

Agent: alternatives. Date: 2026-07-09. Grounding:
`.omc/research/research-20260709-r2-inventory/report.md` (baseline: Doppler
host-side download → `--env-file` is the live devcontainer path,
`devcontainer.json:198`; fnox ships unused in the image runtime tier,
`.devcontainer/mise-runtime.toml:41`; CI = least-privilege GITHUB_TOKEN +
REFRESH_APP app token). Cross-referenced Run A
(`.omc/research/research-20260709-r2-web-env/report.md`) for the web-session
allowlist model.

Scope: evaluate 1Password service accounts + op CLI/inject/run (+ 1Password
SSH agent), Infisical (cloud + self-host), sops/age with git-committed
encrypted files (incl. mise's documented sops support), teller, GitHub
Environments secrets, and doppler-compatible OSS — each on setup cost,
rotation, offline behavior, devcontainer/GHA/web fit, and lock-in, with a
switch/no-switch verdict.

---

## Findings

### F1. 1Password service accounts + op CLI — capable but structurally wrong for this footprint

**Mechanics.** Service accounts give non-interactive `op` CLI auth via
`OP_SERVICE_ACCOUNT_TOKEN`; up to 100 service accounts per account; you scope
each to specific vaults ([overview](https://www.1password.dev/service-accounts/),
fetched 2026-07-09). `op run`/`op inject` resolve `op://vault/item/field`
references into env vars or templated files — same shape as
`doppler run`/`doppler secrets download`. The official GHA integration
(load-secrets-action) authenticates with the same token and masks values in
logs ([1password.dev/ci-cd/github-actions.md](https://www.1password.dev/ci-cd/github-actions.md)).

**Plan availability and the rate-limit wall.** Service accounts exist on ALL
plans including Individual — but the
[rate-limits page](https://developer.1password.com/docs/service-accounts/rate-limits/)
(fetched 2026-07-09, redirects to 1password.dev) gives Individual/Families a
**combined 1,000 requests/24h cap PER 1PASSWORD ACCOUNT** (hourly: 1,000
read / 100 write per token; Business gets 50,000/day). A `mise`-integrated
per-shell or per-task resolution pattern (the shape issue #83 proposes for
fnox+doppler) would burn that daily budget fast; exceeding it 429s the
*whole account's* automation for up to 24h. Doppler has no comparable
account-wide daily cap on the workloads this repo runs.

**Vault restriction.** By policy a service account can NEVER be granted the
built-in Personal/Private/Employee vaults — you must restructure secrets into
dedicated custom vaults ([community answer](https://www.1password.community/discussions/developers/service-account-access/96808/replies/96809),
[get-started](https://developer.1password.com/docs/service-accounts/get-started/)).
So "I already keep my API keys in my 1Password personal vault" does not
translate into automation access without a migration inside 1Password itself.

**Rotation/lifecycle.** Token expiry is set at creation (`op service-account
create --expires-in 24h` supports short-lived ephemeral accounts), but there
is **no programmatic list/delete/revoke** — cleanup is web-UI-only
([1Password/onepassword-sdk-python#221](https://github.com/1Password/onepassword-sdk-python/issues/221)).

**Offline.** Service-account `op` calls are online per request; unlike
Doppler's CLI there is no documented encrypted fallback-file mechanism for
`op run` (Doppler: automatic AES-256-GCM fallback snapshots,
`--fallback`/`--fallback-only`, auto-used after ~50-60s network timeout —
[docs.doppler.com/docs/automatic-fallbacks](https://docs.doppler.com/docs/automatic-fallbacks)).
Offline behavior is therefore *worse* than the incumbent.

**Web-session fit.** 1Password endpoints (`my.1password.com` etc.) are not in
the Claude-web Trusted allowlist any more than `api.doppler.com` is (Run A
§3: Doppler explicitly blocked; the allowlist covers package registries +
GitHub) — a Custom allowlist entry would be needed. No advantage over Doppler
there. (Inference for the 1P hostnames — see Uncertainties U2.)

**Verdict: NOT worth switching** as the secrets manager. On a solo
Individual-plan footprint it is strictly worse than Doppler on rate limits,
offline behavior, and rotation automation, and requires vault restructuring.
Price is fine ($3.99/mo Individual, 2026 — [cybernews pricing roundup](https://cybernews.com/best-password-managers/1password-review/1password-pricing/))
but price is not the constraint.

### F2. 1Password SSH agent — interesting, but does NOT fix the R2 portability problem

The 1P SSH agent holds keys end-to-end-encrypted (keys never leave the app),
answers via `~/.1password/agent.sock` (`IdentityAgent` in `~/.ssh/config`),
with biometric approval per use
([ssh/overview](https://www.1password.dev/ssh/overview.md),
[ssh/agent/advanced](https://www.1password.dev/ssh/agent/advanced.md)). For
*container* use it rides the exact same Docker Desktop magic socket the repo
already uses: DD synthesizes `/run/host-services/ssh-auth.sock` from the
host's `SSH_AUTH_SOCK`, so pointing host `SSH_AUTH_SOCK` at the 1P agent
socket forwards 1P-held keys into the container with zero devcontainer.json
change ([Server Side Up walkthrough](https://serversideup.net/blog/how-to-get-ssh-to-work-with-1password-docker-desktop-macos-within-a-container/),
[1Password community thread 142569](https://www.1password.community/discussions/developers/how-to-forward-1password-ssh-agent-to-docker-container-macos/142569)).
Known friction: DD is launchd-managed and doesn't inherit shell env, so the
global `SSH_AUTH_SOCK` must be set via the 1P-documented plist, and some
setups need a group-container symlink workaround; permission-denied reports
exist ([community thread 143271](https://www.1password.community/discussions/developers/error-connecting-to-agent-permission-denied-when-forwarding-1password-ssh-agent-/143271)).

Crucially: it is **still agent forwarding over the DD magic socket** — it
inherits the same Docker-Desktop-only limitation (Colima gap, issue #78) and
the same root:root chown fragility the baseline already handles
(`devcontainer.json:200,207`). It changes *where the private key rests on the
host* (1P vault vs `~/.ssh`), not the container delivery mechanism. It also
does not help web sessions (no host agent there at all).

**Verdict: optional host-side hardening, not an R2 architecture change.**
Adopt only if Ray independently wants 1Password for host key custody +
biometric-gated key use; it neither unblocks Colima nor web sidecars, so it
is orthogonal to the decision this run must make.

### F3. Infisical — the credible like-for-like Doppler replacement; hold as fallback, don't switch

Open-source (MIT core, 27k+ stars), cloud + self-host, dashboard/CLI/SDKs/
K8s operator; free tier: $0 for up to **5 identities** (humans + machines
count identically), Pro $18/identity/mo
([infisical.com/pricing](https://infisical.com/pricing),
[Infisical/infisical](https://github.com/Infisical/infisical), 2026 pages).
Self-hosting the Community Edition is genuinely free/unlimited but means
running Postgres + Redis + the app 24/7 — a real operational tax for a solo
developer whose alternative is a managed free tier.

Two features genuinely ahead of the repo's current Doppler wiring:

- **OIDC machine identities for GHA**: the official
  [Infisical/secrets-action](https://github.com/Infisical/secrets-action)
  authenticates workflows with GitHub's short-lived OIDC token instead of a
  stored long-lived service token — zero static secret stored in GitHub at
  all ([docs](https://infisical.com/docs/integrations/cicd/githubactions)).
- Self-host exit ramp: if Doppler's free tier ever shrinks, Infisical is the
  strongest landing zone
  ([Infisical's own Doppler-alternatives page, 2026](https://infisical.com/blog/doppler-alternatives);
  [openalternative.co roundup](https://openalternative.co/alternatives/doppler)).

Offline: the CLI caches/falls back, but an explicit offline/prefer-offline
mode is an OPEN feature request
([Infisical/cli#216](https://github.com/Infisical/cli/issues/216),
[Infisical/infisical#2496](https://github.com/Infisical/infisical/issues/2496)) —
weaker than Doppler's documented fallback files. Web sessions:
`app.infisical.com` (or a self-host origin) would need a Custom allowlist
entry, same class as Doppler (Run A §3). fnox has a first-class Infisical
provider (fnox docs cache,
`docs/research/mintlify-cache/jdx/fnox/llms.txt:24`), so a later migration
would not orphan the issue-#83 fnox layer.

**Verdict: NOT worth switching now — zero current pain, real migration cost —
but it is the designated fallback**, and its OIDC GHA pattern is the feature
to envy (worth checking in angle #2 whether Doppler has an equivalent before
adding any new long-lived CI service token).

### F4. sops/age (git-committed encrypted files) — the one alternative that fills a real gap; mise support is native but experimental

mise reads sops-encrypted `.env.json`/`.env.yaml`/`.env.toml` via
`[env] _.file`, decrypting automatically — **age-only backend**, marked
**experimental** — with key lookup via
`MISE_SOPS_AGE_KEY(_FILE)` → `SOPS_AGE_KEY(_FILE)` → `~/.config/mise/age.txt`,
and redaction support (`_.file = { path = ".env.json", redact = true }`,
`mise env --redacted`). Source: local cache,
`docs/research/mintlify-cache/jdx/mise/llms-full.txt:2956-3044`. The same
docs page positions fnox as the "recommended for team environments" superset
(`llms-full.txt:2951-2953`).

Properties no service-backed manager can match:

- **Zero network at resolve time** → perfect offline behavior, and the ONLY
  candidate that works in Claude-web sessions under the default Trusted
  policy with no Custom allowlist entry (Run A §3: `api.doppler.com`
  blocked; decryption is local; only the age private key must arrive, e.g.
  as a cloud-environment env var — with Run A's documented visibility
  caveat).
- **No service dependency, no rate limits, no vendor lock-in** (ciphertext in
  git; age is a stable standalone format).
- CI story is standard: age private key as a single GHA/CI secret, everything
  else in the repo — the fnox docs prescribe exactly this pattern (cache,
  `jdx/fnox/llms-full.txt:24`).

Costs: **rotation is manual re-encryption + commit** (rotating the age key
means re-encrypting everything); **no audit trail or central dashboard** (git
history is the audit); **secret-zero moves** from "Doppler login" to "age key
distribution"; mise's implementation is explicitly experimental.

Important interaction (Run D / issue #83): the repo already ships fnox in the
image (`mise-runtime.toml:41`), and **fnox's age provider covers this same
git-native niche with a maintained, non-experimental surface** — encrypted
values inline in a committed `fnox.toml`, accepting **native age keys or
existing SSH keys as identities** (fnox docs cache, `jdx/fnox/llms.txt:15`,
`llms-full.txt:429-437`). If issue #83's mise-env-fnox migration proceeds,
prefer **fnox-age over raw sops** for the git-committed tier — one config
surface (fnox.toml: doppler-provider refs for platform-managed secrets +
age-encrypted values for the offline/web tier) instead of two.

**Verdict: worth adopting — as a COMPLEMENT for the offline/web-session
tier, not a Doppler replacement.** Concretely: the handful of
low-blast-radius keys a web session or offline laptop needs (e.g. EXA/BRAVE
research keys) age-encrypted in git; Doppler remains system of record for
everything else.

### F5. teller — dormant; do not adopt

tellerops/teller (Rust rewrite, 3.2k stars): **last release v2.0.7 on
2024-05-20**; a single burst of 4 commits on 2026-01-27 is the only activity
since May 2024; 48 open issues
([repo](https://github.com/tellerops/teller),
[commits/master](https://github.com/tellerops/teller/commits/master), both
fetched 2026-07-09). Its niche (one declarative mapping of many providers →
env) is exactly what fnox — already in the image, actively developed in the
jdx ecosystem, with doppler/1password/infisical/bitwarden/age providers —
now covers with real maintenance. **Verdict: not worth adopting.**

### F6. GitHub Environments / Actions secrets — keep exactly as-is, CI-only by design

Write-only after creation (no read-back via UI/API), not passed to
fork-triggered workflows or Dependabot events, ~48KB practical size limit;
environment secrets add reviewer/branch-protection gating
([GitHub docs](https://docs.github.com/en/actions/how-tos/security-for-github-actions/security-guides/using-secrets-in-github-actions)).
They cannot serve the devcontainer, a laptop, or web sessions — they are a
delivery endpoint, not a manager. The repo already uses this layer correctly
(least-privilege GITHUB_TOKEN, REFRESH_APP app token — inventory report
:38-41). The only credible upgrade in this layer is *removing* stored tokens
via OIDC federation to whatever manager wins (F3). **Verdict: keep; no
change.**

### F7. Doppler-compatible OSS beyond Infisical — nothing worth a look yet

2026 roundups list Infisical, Phase, Keyshade, Bitwarden (Secrets Manager) as
the open Doppler alternatives
([openalternative.co](https://openalternative.co/alternatives/doppler)).
Phase (cloud + self-host) and Keyshade are young with no differentiator over
Infisical for this footprint; Bitwarden Secrets Manager is reachable later
through fnox's provider anyway (fnox docs cache, `jdx/fnox/llms.txt:24`).
**Verdict: none worth adopting; Infisical is the representative of this
class.**

### F8. Comparison matrix (solo dev, this repo's consumers)

| Option | Setup cost | Rotation | Offline | Devcontainer | GHA | Claude-web | Lock-in | Verdict |
|---|---|---|---|---|---|---|---|---|
| **Doppler (incumbent)** | sunk | dashboard + versioning | encrypted fallback files (auto) | live, contract-enforced | token or action | blocked w/o Custom allowlist | moderate (export = one CLI call) | **keep as system of record** |
| 1Password svc accts | med (vault restructure) | expiry-at-create; no programmatic revoke | none documented for `op run` | works (op or fnox provider) | official action | blocked (inference) | moderate | **not worth switching** (1k/day acct cap on Individual) |
| 1P SSH agent | low-med (plist/symlink friction) | n/a (key custody) | n/a | same DD magic socket as today | n/a | no help | low | **optional; doesn't move R2** |
| Infisical | med (cloud) / high (self-host) | dashboard + versioning | cache; explicit offline mode still an open FR | CLI or fnox provider | **OIDC action (no stored token)** | blocked w/o Custom | low (MIT, self-host exit) | **fallback, not now** |
| sops/age via mise | low (key + encrypt) | manual re-encrypt + commit | **perfect (no network)** | works (mise built-in, experimental) | age key as 1 CI secret | **only option under default Trusted** | none | **adopt for offline/web tier — prefer fnox-age variant** |
| teller | — | — | — | — | — | — | — | **dormant; skip** |
| GH Environments | sunk | manual re-set | n/a | unusable | native | n/a | n/a | **keep, CI-only** |

---

## Uncertainties / gaps

- **U1 — 1P Individual-plan service-account daily cap**: the 1,000/24h
  account-wide figure comes from the official rate-limits page (fetched via
  redirect to 1password.dev, 2026-07-09) plus a corroborating community
  thread; whether background retries by `op run` count multiplicatively was
  not probed.
- **U2 — Web allowlist status of 1Password/Infisical hosts** is *inference*
  from Run A's allowlist model (package registries + GitHub; Doppler
  explicitly blocked). Not empirically probed for `my.1password.com` /
  `app.infisical.com`. Probe `$HTTPS_PROXY/__agentproxy/status` in a live
  session before relying on it.
- **U3 — mise sops is experimental** (the docs' own warning) and age-only;
  the fnox-age recommendation assumes Run D's fnox mining confirms fnox-age
  is production-ready at the pinned fnox version — verify there.
- **U4 — teller's Jan-2026 commit burst** content was not inspected; if it
  signals a maintainer handover the dormancy verdict could soften (unlikely
  to change the outcome given the fnox overlap).
- **U5 — Doppler OIDC**: whether Doppler now offers GHA OIDC federation
  (matching Infisical's stored-token-free CI auth) was not researched here —
  belongs to angle #2's Doppler-platform inventory.
- **U6 — 1P SSH agent through Colima** was not directly probed; the verdict
  rests on it using the same DD magic-socket forwarding path (well-sourced),
  hence inheriting issue #78's gap.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — baseline facts, mintlify cache (mise secrets page, fnox providers), Run A report
- [tellerops/teller](https://github.com/tellerops/teller) — maintenance-state check (releases page, commits/master)
- [Infisical/infisical](https://github.com/Infisical/infisical) — OSS platform, pricing/self-host model, offline FR #2496
- [Infisical/cli](https://github.com/Infisical/cli) — offline-mode feature request #216
- [Infisical/secrets-action](https://github.com/Infisical/secrets-action) — GHA OIDC machine-identity auth
- [1Password/onepassword-sdk-python](https://github.com/1Password/onepassword-sdk-python) — issue #221: no programmatic service-account lifecycle
- [1Password/onepassword-sdk-js](https://github.com/1Password/onepassword-sdk-js) — issue #180: rate-limit introspection gap (search context)
- [jdx/mise](https://github.com/jdx/mise) — sops/age support (via local mintlify cache)
- [jdx/fnox](https://github.com/jdx/fnox) — provider matrix: age (SSH-key identities), 1password, doppler, infisical, bitwarden (via local mintlify cache)
- [DopplerHQ/cli](https://github.com/DopplerHQ/cli) — fallback-file behavior (via docs.doppler.com)
