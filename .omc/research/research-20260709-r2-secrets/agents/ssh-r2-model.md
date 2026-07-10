# Run E / Angle 5 — SSH/R2 model: agent-forwarding vs delivered keys vs hybrids

Date: 2026-07-09. Analyst angle #5 of the Run E secrets domain
(`research-20260709-r2-secrets`). Grounding:
`.omc/research/research-20260709-r2-inventory/report.md`; Run A web-env
report Read in full (`.omc/research/research-20260709-r2-web-env/report.md`).
All repo facts re-read from the working tree at file:line.

## Baseline (verified from the tree)

- R2 outbound = Docker Desktop magic socket: bind-mount
  `/run/host-services/ssh-auth.sock` (`.devcontainer/devcontainer.json:96`),
  `SSH_AUTH_SOCK` containerEnv (`devcontainer.json:189`), `sudo chown` in
  BOTH `postCreateCommand` (`devcontainer.json:200`) and
  `postStartCommand` (`devcontainer.json:207`) because the socket reverts
  to root:root on DD restart (comment block `devcontainer.json:201-206`).
- The gate: smoke tier-3 SSH block (`scripts/devcontainer-smoke.sh:208-234`)
  asserts (1) `SSH_AUTH_SOCK == /run/host-services/ssh-auth.sock`, (2) the
  path is a socket, (3) `ssh-add -L` lists ≥1 identity, (4)
  `ssh -o BatchMode=yes -T git@github.com` reaches "successfully
  authenticated". R2 is a **durable success criterion** in root `AGENTS.md`
  ("do NOT silently drop"); any mechanism change is a criteria rewrite, not
  a refactor.
- R1 inbound is fully independent: `mise.toml [tasks.verify-ssh-inbound]`
  (`mise.toml:490-516`) tests host→container sshd
  (`ghcr.io/devcontainers/features/sshd:1`, `devcontainer.json:192`,
  `appPort` 4444→2222) with `authorized_keys` copied from the host-state
  bind mount (`devcontainer.json:200`). **No R2 option below touches R1** —
  the inbound path uses its own key file, not the agent socket.
- `GITHUB_TOKEN` is already delivered into the container via the Doppler
  `--env-file` path — it is one of the tier-2 smoke canary keys
  (`scripts/devcontainer-smoke.sh:99`). This matters for option (e).
- Issue #78 (open, 2026-04-09) already scopes the Colima question and — 
  important — includes an **untested probe sequence** for replicating
  forwarding on Colima (Lima `ssh.forwardAgent` host→VM, then volume-mount
  the VM's `$SSH_AUTH_SOCK` into the container). The issue's own framing:
  deploy keys are NOT the presumed answer; the VM→container leg is simply
  unprobed (https://github.com/ray-manaloto/dotfiles/issues/78).
- Issue #83 is about **OAuth token injection for AI CLIs**, and explicitly
  concludes Doppler/fnox is for *static* secrets — it does not propose
  moving SSH into a secrets manager
  (https://github.com/ray-manaloto/dotfiles/issues/83).

---

## Findings

### F1 — Option (a) status quo: DD magic socket agent forwarding

**Mechanism & support status.** `/run/host-services/ssh-auth.sock` is an
officially documented Docker Desktop feature (bind-mount + `SSH_AUTH_SOCK`
env), documented on Docker's networking how-tos page
(https://docs.docker.com/desktop/features/networking/networking-how-tos/),
shipped since Docker Desktop 2.2.0.0 (2020). It synthesizes an in-VM
socket proxied to the **macOS default launchd ssh-agent** — it does NOT
honor a custom host `$SSH_AUTH_SOCK` (gpg-agent, YubiKey agents):
docker/for-mac#4242 (closed stale, never fixed;
https://github.com/docker/for-mac/issues/4242).

**Attack surface / blast radius on container compromise.** The private key
material never enters the container — the strongest at-rest property of
any option. But the live socket is a **signing oracle**: any process in
the container running as the socket owner (which postCreate/postStart
chown to `${USER}`) can request signatures for **every identity loaded in
the Mac's agent**, for **any host** those keys authenticate to — not just
github.com, and not just this repo. This is classic ssh-agent hijacking
(ATT&CK-catalogued; e.g.
https://www.clockwork.com/insights/ssh-agent-hijacking/,
https://smallstep.com/blog/ssh-agent-explained/). The canonical real-world
blast radius is the Matrix.org 2019 breach: an attacker on a compromised
Jenkins box trapped forwarded agents and propagated root keys across
production
(https://matrix.org/blog/2019/05/08/post-mortem-and-remediations-for-apr-11-security-incident/).
Mitigations that keep the model: load only the GitHub key into the agent;
`ssh-add -c` per-use confirmation (macOS UI prompt). The exposure is
**transient** — it ends when the container stops or DD closes the tunnel;
nothing is exfiltratable for later use.

**Operational friction.** (i) root:root reversion on DD restart — already
solved durably via the double chown (`devcontainer.json:200,207`); (ii)
Docker-Desktop-only: Colima has no magic-socket equivalent
(abiosoft/colima#1330 — open since May 2025, `--ssh-agent` sets the env
var but the socket path doesn't exist:
https://github.com/abiosoft/colima/issues/1330; #942 — VZ/virtiofs
forwarding breaks across `colima stop/start` with containers running:
https://github.com/abiosoft/colima/issues/942); (iii) does not exist at
all in Claude-web sessions (no host Mac). Note the Colima gap may be
**closable without changing model**: the Lima/Rancher-Desktop community
recipe is exactly issue #78's probe — enable `forwardAgent`, then
volume-mount the VM's `$SSH_AUTH_SOCK` into the container (works on
Rancher Desktop per
https://github.com/rancher-sandbox/rancher-desktop/discussions/1842); the
friction vs DD is the *dynamic* in-VM socket path and the stop/start
staleness of #942.

### F2 — Option (b) secrets-manager-delivered deploy key

**Mechanism.** Generate a dedicated keypair; register the public half as a
GitHub **deploy key** on `ray-manaloto/dotfiles`; deliver the private half
via Doppler (or fnox) into the container; run an in-container agent or
`IdentityFile`.

**Scoping & lifecycle facts** (GitHub docs,
https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys):
deploy keys grant access to a **single repository**, read-only by default
(write is opt-in), are typically passphrase-less, and **never expire** —
GitHub's own docs recommend GitHub Apps instead for fine-grained,
expiring access. Read the Docs is disabling write-access deploy keys
platform-wide in 2025 precisely because of the standing-write-credential
risk (https://about.readthedocs.com/blog/2025/07/ssh-keys-with-write-access/).
A single deploy key also cannot be attached to multiple repos
(https://github.com/orgs/community/discussions/67734), so multi-repo work
multiplies keys.

**Attack surface / blast radius.** The key is **at rest inside the
container** (env var, tmpfs, or the persistent home volume — the v6 home
volume survives stop/up, so a key written there persists). On container
compromise the attacker **exfiltrates a durable credential** usable
offline from anywhere until manually rotated — strictly worse than the
transient signing oracle of (a), though the *scope* is narrower (one repo
vs every identity/host). With write access it's a standing push credential
to the repo that CI auto-publishes images from — a supply-chain pivot.

**Delivery friction specific to this repo.** The live Doppler path is
`--format docker` → `runArgs --env-file` (`devcontainer.json:87-88,198`);
Docker's env-file format has no multiline-value support, so a PEM key
must be base64-wrapped and decoded by a lifecycle hook — new bespoke
machinery. Alternative: fnox's age provider can encrypt the key into
`fnox.toml` in-repo and decrypt with an age/SSH key (fnox docs, local
cache `docs/research/mintlify-cache/jdx/fnox/llms-full.txt:1925-2058`) —
but that only relocates the "what decrypts it in the container" problem,
and fnox-age explicitly does **not** support passphrase-protected SSH
keys (`llms-full.txt:2051`), forcing the delivered key to be unencrypted
at rest. Rotation is entirely manual (no expiry, no platform reminder).

**Gates rewritten**: the whole smoke tier-3 SSH block (socket-path and
`ssh-add -L` asserts die; `ssh -T` stays), mounts:96, containerEnv:189,
both chowns, plus new key-provisioning + rotation contracts. R1 untouched.

### F3 — Option (c) 1Password SSH agent

Two sub-shapes. (c1) *Forward the host 1Password agent through DD*: DD's
magic socket forwards only the default launchd agent, not a custom
`SSH_AUTH_SOCK` (docker/for-mac#4242), so 1Password-through-DD relies on
community glue (symlinks/socat; e.g.
https://serversideup.net/blog/how-to-get-ssh-to-work-with-1password-docker-desktop-macos-within-a-container/;
recurring "connection refused"/"permission denied" threads on
1password.community for Docker/devcontainer forwarding, e.g.
https://www.1password.community/discussions/developers/connection-refused-when-accessing-1password-ssh-agent-within-devcontainer/164126).
1Password's official forwarding doc covers `ssh -A` to remote *hosts*
only — Docker/devcontainers are not addressed
(https://www.1password.dev/ssh/agent/forwarding/). (c2) *In-container `op`
+ service account*: a service account token (`OP_SERVICE_ACCOUNT_TOKEN`)
in the container can `op read "op://vault/item/private key?ssh-format=openssh"`
(https://developer.1password.com/docs/cli/reference/commands/read/) —
but that reduces to option (b) (key materializes in the container) with
an extra SaaS dependency.

**Fit.** The genuine security win of the 1Password agent — per-signature
biometric authorization prompts — only exists in shape (c1), which is the
unsupported one. The repo has **zero existing 1Password footprint**
(inventory report: "No 1Password/Vault/Infisical anywhere"), so this adds
a paid product + unofficial glue to solve a problem (a) already solves.

### F4 — Option (d) short-lived SSH certificates: not overkill — **impossible** for this target

GitHub only accepts SSH-CA-signed certificates for **organizations on
GitHub Enterprise Cloud** (or GHES): "To use SSH certificate authorities,
your organization must use GitHub Enterprise Cloud", and certs
authenticate only against that org's repos
(https://docs.github.com/en/enterprise-cloud@latest/organizations/managing-git-access-to-your-organizations-repositories/about-ssh-certificate-authorities).
`ray-manaloto/dotfiles` is a personal github.com repo — github.com will
simply not honor a step-ca/Vault-issued cert for it. The step-ca/Vault
machinery is therefore moot regardless of its (real) operational weight
for a solo developer. Option (d) is eliminated on capability, not taste.

### F5 — Option (e) sidestep SSH: git-over-HTTPS with expiring tokens

**Mechanism.** GitHub App **installation access tokens** work as the HTTP
password for git (`git clone https://x-access-token:TOKEN@github.com/...`),
require only the app's `contents` permission, can be scoped to selected
repos with fine-grained permissions, and **expire after 1 hour**
(https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation).
This is the exact model the repo's CI already uses (`refresh.yml` App
token; inventory report lines 38-41). For interactive/container use, `gh
auth setup-git` installs gh as git's credential helper and honors
`GH_TOKEN`/`GITHUB_TOKEN` env (https://cli.github.com/manual/gh_auth_setup-git)
— and `gh` is already baked into the image runtime tier
(`.devcontainer/mise-runtime.toml`, inventory line 85) and `GITHUB_TOKEN`
already arrives via the Doppler env-file (smoke canary,
`devcontainer-smoke.sh:99`). GitHub itself recommends Apps over deploy
keys for exactly this use
(https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys).
Implementation note: newly minted installation tokens are moving to a
stateless `ghs_APPID_JWT` format (staged rollout from 2026-04-27), so any
glue must not assume the legacy 40-char token length
(https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app).

**Attack surface / blast radius.** A leaked installation token dies in ≤1h
and is scoped to the app's repo/permission grant; a leaked fine-grained
PAT is scoped + expiring by policy. Both beat (b) decisively at rest. The
tradeoff vs (a): a token IS exfiltratable for its lifetime, whereas (a)
exposes no reusable credential at all — but (a)'s oracle spans every
agent identity while live.

**Where (e) is already the only answer.** (i) **Claude-web sessions**: the
Run A report (verified 3/3) establishes git-to-GitHub in web sessions
flows through a dedicated GitHub proxy where "tokens never enter the
container" and push is restricted to the current branch
(`.omc/research/research-20260709-r2-web-env/report.md:165-166`) — SSH is
neither needed nor useful there; R2 does not extend to web. (ii) **A
self-hosted updater runner / any headless automation**: App installation
tokens (already minted by `refresh.yml`) are the GitHub-recommended
pattern; no agent socket exists to forward. (iii) **Colima fallback**: if
issue #78's probe fails, `gh auth setup-git` + the Doppler-delivered
`GITHUB_TOKEN` gives working `git push` with **zero new secret
infrastructure** — the pieces are already in the container today.

**Friction.** Remote URLs: interactive clones use `git@github.com:` —
either a `url.insteadOf` rewrite or the gh credential helper handles it;
`ssh -T git@github.com` as a *smoke assertion* would need an HTTPS
equivalent (`gh auth status` / `git ls-remote`). Token lifetime: the
Doppler-stored `GITHUB_TOKEN` is a PAT (rotation discipline required —
but it is already in the threat model today, delivered into every
container).

### F6 — Gate/invariant rewrite matrix (what each option costs in this repo)

| Option | devcontainer.json | smoke tier-3 (`devcontainer-smoke.sh:208-234`) | Durable criteria (`AGENTS.md` R-table) | New machinery |
|---|---|---|---|---|
| (a) keep | none | none | none | none |
| (b) deploy key | drop `mounts:96`, `containerEnv:189`, chown at `:200`/`:207` | rewrite: drop socket/`ssh-add -L` asserts, keep `ssh -T`; add key-presence check | R2 mechanism text + `.devcontainer/AGENTS.md` §SSH | base64 key delivery through env-file (no multiline) or fnox-age; rotation contract; key-hygiene check on home volume |
| (c) 1Password | same as (b) or new socket glue | rewrite socket-path assert to 1P socket | R2 mechanism text | 1P subscription + service account + unofficial container glue |
| (d) SSH certs | n/a | n/a | n/a | impossible on personal github.com (GHEC-only) |
| (e) HTTPS lane (additive) | none removed | ADD an HTTPS auth assert (`gh auth status`) alongside — or as fallback tier for — the SSH block | R2 gains an "or HTTPS-token path" clause **only with explicit approval** (durable-criteria rule) | one lifecycle line (`gh auth setup-git`) + optional `url.insteadOf` |

**R1 (`verify-ssh-inbound`, `mise.toml:490-516`) is unaffected by every
option** — it exercises the sshd feature + host-delivered
`authorized_keys`, no dependency on the outbound agent socket. S1
(`verify-secrets`, `mise.toml:518-541`) is likewise untouched unless (b)
rides the Doppler env-file, in which case its canary set grows.

---

## Recommendation: KEEP (a) as the devcontainer's R2; ADD (e) as the portable lane; do NOT adopt (b)/(c)/(d)

1. **Keep DD agent forwarding for the interactive Mac devcontainer.** It
   is the only option where key material never exists in the container;
   its two known weaknesses are already durably mitigated in-tree (double
   chown) or accepted and tracked (DD-only, #78). The signing-oracle risk
   is real but bounded (transient, no exfiltratable artifact) and can be
   cheaply narrowed: keep only the GitHub key in the Mac agent, consider
   `ssh-add -c`. Rewriting a verified, contract-gated invariant to trade
   a transient oracle for an at-rest credential (b) is a security
   downgrade for this threat model.
2. **Adopt git-over-HTTPS tokens (e) as the second lane for every
   non-DD consumer** — it is already 90% wired: CI uses App tokens today;
   web sessions use Anthropic's git proxy and need nothing; the container
   already has `gh` + Doppler-delivered `GITHUB_TOKEN`. The delta is one
   documented fallback (`gh auth setup-git` in a lifecycle hook or an
   opt-in mise task) and, if promoted into the gate, a smoke assert.
   This — not deploy keys — is what unblocks Colima (#78 worst case) and
   any future self-hosted runner.
3. **Do not deliver raw SSH keys via Doppler/fnox (b)**: non-expiring
   credential at rest on a persistent volume, manual rotation, multiline
   env-file friction, and GitHub's own guidance says use Apps instead.
   Revisit only if some consumer strictly requires SSH *protocol* (none
   identified does).
4. **Reject (c)** (no existing 1Password footprint; container forwarding
   unofficial; DD socket won't carry a custom agent — #4242) and **(d)**
   (GHEC-only; impossible for a personal repo).
5. **Before ever migrating runtimes, run issue #78's probe as written** —
   the Lima `forwardAgent` + VM-socket volume-mount recipe (proven on
   Rancher Desktop) may preserve model (a) off Docker Desktop entirely,
   with (e) as the safety net. Do not pre-emptively rewrite R2.

## Uncertainties / gaps

- **Colima VM→container socket mount viability** (issue #78 steps 4-5) is
  unprobed in this repo; Rancher Desktop evidence is adjacent-but-not-
  identical (different VM plumbing; colima#942 shows stop/start
  staleness). Empirical probe required before any runtime decision.
- **Whether DD's magic socket will ever honor a non-launchd host agent**:
  #4242 closed stale; treat "launchd agent only" as current behavior, not
  a guarantee either way.
- **macOS launchd agent + `ssh-add -c` interplay**: per-use confirmation
  prompts through the DD proxy path were not live-verified; if prompts
  don't surface, the mitigation is weaker than stated.
- **`gh auth setup-git` inside this container** is asserted from gh docs +
  presence of `gh` in the runtime tier; not live-probed in-container with
  the Doppler-delivered token (the token's scopes on Ray's PAT are
  unknown to this analyst).
- **Durable-criteria governance**: adding an HTTPS clause to R2 requires
  explicit user approval per root `AGENTS.md` ("durable, do NOT silently
  drop") — this report recommends, it cannot approve.
- Publication-date caveat: several agent-hijacking references are older
  than 12 months (Matrix 2019 postmortem, Clockwork, smallstep); they are
  cited for mechanism, which is unchanged, not for currency.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — baseline wiring, issues #78/#83 read via API
- [abiosoft/colima](https://github.com/abiosoft/colima) — issues #1330, #942 (agent-forwarding gaps)
- [docker/for-mac](https://github.com/docker/for-mac) — issue #4242 (magic socket ignores custom SSH_AUTH_SOCK)
- [github/docs](https://github.com/github/docs) — deploy-key, GitHub App installation-token, and SSH-CA documentation (docs.github.com)
- [cli/cli](https://github.com/cli/cli) — `gh auth setup-git` manual + credential-helper issues #3796/#10922
- [jdx/fnox](https://github.com/jdx/fnox) — age/SSH-key provider capabilities (local mintlify cache)
- [1Password/load-secrets-action](https://github.com/1Password/load-secrets-action) — SSH-key formatting issue #59 (op read ssh-format)
- [rancher-sandbox/rancher-desktop](https://github.com/rancher-sandbox/rancher-desktop) — discussion #1842 (VM→container agent socket mount recipe)
- [lima-vm/lima](https://github.com/lima-vm/lima) — forwardAgent behavior, issue #626 / discussion #649
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — web-session git proxy facts via Run A report
- [matrix-org/matrix.org](https://github.com/matrix-org/matrix.org) — 2019 agent-hijack postmortem (blast-radius exemplar)
- [readthedocs/readthedocs.org](https://github.com/readthedocs/readthedocs.org) — write-deploy-key deprecation rationale
