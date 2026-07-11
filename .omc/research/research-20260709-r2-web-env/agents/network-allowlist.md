# Run A / Angle 3 — Network policy vs package backends (Claude Code on the web)

Date: 2026-07-09. Researcher: network-allowlist agent (Run A, angle 3 of 5).
Scope: map the web environment's network access policy options against every
package source this repo's toolchain (mise + hk + pkl + uv + python 3.14 +
doppler + ghcr.io image) needs.

Primary source fetched today (2026-07-09):
<https://code.claude.com/docs/en/claude-code-on-the-web.md> ("the web doc"
below). Section anchors cited are from that page as fetched.

## Findings

### F1. The policy model: four per-environment access levels

The web doc § "Network access" defines exactly four levels, chosen per
environment (an environment bundles network level + env vars + setup script):

| Level | Outbound connections |
|---|---|
| **None** | No outbound network access |
| **Trusted** | Allowlisted domains only: package registries, GitHub, cloud SDKs |
| **Full** | Any domain |
| **Custom** | Your own allowlist, optionally including the defaults |

- Default is **Trusted**.
- **Custom** shows an "Allowed domains" field, one domain per line, `*.`
  wildcard subdomain matching, plus a checkbox "Also include default list of
  common package managers" to union the Trusted defaults with your entries
  (§ "Allow specific domains").
- **GitHub operations use a separate proxy that is independent of this
  setting** (§ "Access levels" note + § "GitHub proxy"): git clone/fetch/push
  and the built-in GitHub tools authenticate through a dedicated proxy with a
  scoped credential; push is restricted to the current working branch. So git
  to github.com works even under **None** — but *raw HTTPS to GitHub REST/
  release assets from arbitrary tools* goes through the normal egress path and
  the allowlist.
- MCP connector traffic is routed through Anthropic's servers and bypasses the
  allowlist entirely (§ "Network access" note).

### F2. Proxy semantics: env-var HTTP(S) egress proxy, CONNECT-level 403 denials

- § "Security proxy": "Environments run behind an HTTP/HTTPS network proxy for
  security and abuse prevention purposes. All outbound internet traffic passes
  through this proxy" — protection, rate limiting, content filtering, and a
  "DNS-level audit trail of requested hostnames".
- The proxy is exposed to processes via the standard `HTTPS_PROXY` env var and
  has a debug endpoint: `curl -sS "$HTTPS_PROXY/__agentproxy/status"` with a
  `recentRelayFailures` list. A policy denial surfaces as
  `connect_rejected: gateway answered 403 to CONNECT (policy denial ...)` —
  i.e., the proxy refuses the CONNECT for a non-allowlisted host. Evidence:
  anthropics/claude-code#71629 (filed 2026-06-26, in-sandbox probe transcript;
  <https://github.com/anthropics/claude-code/issues/71629>). This session's own
  remote container carries the same shape (`HTTPS_PROXY` pre-set, CA bundle at
  `/root/.ccr/ca-bundle.crt`, `__agentproxy/status` endpoint per env notes) —
  first-hand corroboration, flagged as observation not doc.
- **Tool compatibility is not universal**: the web doc explicitly warns "all
  outbound traffic passes through a security proxy. Some package managers
  don't work correctly with this proxy. Bun is a known example" (§ "Install
  dependencies with a SessionStart hook", limitation 3; also footnote ¹ under
  Installed tools). Any tool that ignores `HTTP(S)_PROXY` env vars will fail
  under every level except (possibly) Full.
- Practical consequence for mise: mise is a reqwest/rustls binary and
  historically failed behind TLS-intercepting proxies with
  `invalid peer certificate: UnknownIssuer`; **fixed in mise v2025.7.2
  (2025-07-09, jdx/mise PR #5459)** — mise now picks up custom CAs "assuming
  the required CA is trusted in your system/native cert store"
  (<https://github.com/jdx/mise/discussions/5313>). Setup scripts run as root
  on Ubuntu 24.04 (web doc § "Setup scripts"), so `update-ca-certificates`
  with the proxy CA is available if TLS interception applies to a given path.
  (#71629's evidence shows plain CONNECT tunneling for shell traffic — where
  no custom CA is needed — but this research container also ships a CA
  bundle; see Uncertainties U2.)

### F3. Backend-by-backend matrix under **Trusted** (the default allowlist)

Default allowed domains as published today in the web doc § "Default allowed
domains", mapped to what each mise backend / tool in this repo actually dials.
Repo backend inventory: `mise.toml`, `.config/mise/conf.d/shared.toml`,
`.devcontainer/mise-system.toml` (~35 `conda:` tools),
`.devcontainer/mise-runtime.toml` (npm/pipx/github/conda mix).

| Package source | Hosts it needs | In Trusted defaults? | Verdict under Trusted |
|---|---|---|---|
| **npm backend** (`npm:@devcontainers/cli`, `npm:renovate`, AI CLIs…) | `registry.npmjs.org` | Yes ("JavaScript and Node package managers") | **Works** |
| **pipx backend / PyPI / uv** (`pipx:mcp2cli`, `pipx:check-jsonschema`, all uv installs) | `pypi.org`, `files.pythonhosted.org` | Yes ("Python package managers") | **Works** |
| **conda/rattler backend** (`conda:llvm`, `conda:cmake`, … 35+ tools) | `conda.anaconda.org` (conda-forge channel), `repo.anaconda.com` | Yes ("Development tools and platforms": `repo.anaconda.com`, `conda.anaconda.org`, `anaconda.org`) | **Works** |
| **aqua backend** (`aqua:jackchuka/mdschema`, most bare-name registry tools: hk, pkl, shellcheck, jq…) | Registry metadata: none at runtime — "the aqua registry … is compiled into the mise binary at release" (mise docs, cache `docs/research/mintlify-cache/jdx/mise/llms-full.txt:1838`). Assets: GitHub release downloads → `github.com`, `objects.githubusercontent.com`, `release-assets.githubusercontent.com`, `codeload.github.com` | Yes (all four in "Version control") | **Works** (see U3 on cosign/SLSA verification endpoints) |
| **github backend** (`github:cli/cli`, `github:ast-grep/ast-grep`, `github:mozilla/sccache`, agnix…) | `api.github.com` + release-asset hosts above | Yes | **Works** |
| **gitlab backend** (available, unused by repo today) | `gitlab.com`, `registry.gitlab.com` | Yes (fronts) | Likely works; asset CDN unverified (U4) |
| **mise core python** (`python = "3.14.6"`) & `uv python install` | precompiled builds from `github.com/astral-sh/python-build-standalone/releases/download/...` → GitHub release-asset hosts | Yes | **Works** — this is the correct python-3.14 path (see F5) |
| **mise.run installer** | `mise.run` (script) then, for the current version, the CDN `mise.jdx.dev/v${version}/...`; GitHub releases otherwise. `MISE_INSTALL_FROM_GITHUB=1` forces GitHub releases; `MISE_TARBALL_URL` overrides entirely (read from <https://mise.run> script, 2026-07-09; current v2026.7.4) | **No** — neither `mise.run` nor `mise.jdx.dev` is in the defaults | **Fails as `curl https://mise.run \| sh`.** Fix without Custom policy: download the release tarball from `github.com/jdx/mise/releases/download/...` directly (allowlisted), or run the script with `MISE_INSTALL_FROM_GITHUB=1` after allowlisting only `mise.run`. Cleanest zero-Custom path: plain `curl -L https://github.com/jdx/mise/releases/download/v<ver>/mise-v<ver>-linux-x64 ...` (pattern documented in mise install docs, cache `llms-full.txt:4265`) |
| **Doppler** (secrets: `doppler secrets download` per `.devcontainer/devcontainer.json:198`) | API `api.doppler.com`; CLI install `cli.doppler.com/install.sh` or apt repo `packages.doppler.com` (docs.doppler.com/docs/cli + /docs/api, fetched 2026-07-09) | **No** — no doppler host in the defaults | **Fails.** Requires **Custom** with `api.doppler.com` (+ `cli.doppler.com`/`packages.doppler.com` for install), or inject secrets as environment variables in the environment config instead (web doc: "A dedicated secrets store is not yet available … add them as environment variables with that visibility in mind") |
| **ghcr.io image pulls** (e.g. `ghcr.io/ray-manaloto/dotfiles-devcontainer:dev`) | Manifest: `ghcr.io` — allowlisted. **Layer blobs: `pkg-containers.githubusercontent.com` — NOT allowlisted** (the defaults include `pkg-npm.githubusercontent.com` but not `pkg-containers`) | Partially | **Fails mid-pull under Trusted**: "docker pull ghcr.io/… — manifest OK, layer 403 … Get https://pkg-containers.githubusercontent.com/ghcr1/blobs/sha256:… Forbidden" — verified in-sandbox, anthropics/claude-code#71629 (open, 2026-06-26; still absent from the docs' default list as fetched today). Fix: **Custom** + `pkg-containers.githubusercontent.com` |
| **Docker Hub pulls** | `registry-1.docker.io`/`auth.docker.io` allowlisted; blob CDN `production.cloudfront.docker.com` NOT (defaults list the wrong `production.cloudflare.docker.com`) | Partially | Small images may still work per-cache; blob CDN 403 tracked as anthropics/claude-code#69174 (cross-ref in #71629) |
| **apt / Ubuntu archive** | `archive.ubuntu.com`, `security.ubuntu.com`, `*.ubuntu.com` allowlisted; **PPAs serve from `ppa.launchpadcontent.net` which is NOT allowlisted** (only legacy `ppa.launchpad.net`) | Partially | Main archive works (`apt install gh` is the doc's own example); **any PPA 403s** — incl. the base image's own pre-enabled deadsnakes PPA (#71629 instance 1) |

Under **None**, everything above fails (docs: "Scripts fail to install
packages if your environment uses **None** network access"). Under **Full**,
everything works modulo proxy-compatibility (F2). **Custom + "include
defaults"** is the union — the natural choice for this repo.

### F4. Allowlist-drift is a known, systemic issue class

anthropics/claude-code#71629 ("Trusted egress allowlist is systematically out
of sync with where tooling connects", open, labels `area:claude-code-web`,
`area:networking`) documents the pattern: the allowlist names the human-visible
front while tooling dials a CDN/renamed host — Docker CDN (#69174), .NET
(#11897), Launchpad PPAs, GHCR blobs, ECR Public blobs, `registry.k8s.io`.
Design consequence for this repo: **do not treat the published Trusted list as
a contract**; run a probe (`$HTTPS_PROXY/__agentproxy/status` →
`recentRelayFailures`) in a live session before locking in a Custom allowlist,
and expect to maintain the custom entries as CDNs move.

### F5. Interaction with this repo's known web-session failure (python ≥3.14 / hook guard)

- The obvious repair path "apt install python3.14" is **blocked under
  Trusted**: the sandbox base image (Ubuntu 24.04) ships the deadsnakes PPA
  pre-enabled, but its host `ppa.launchpadcontent.net` 403s (#71629 instance
  1, with `apt-get install -y python3.14` abort transcript).
- The path that DOES work under plain Trusted: **mise or uv installing CPython
  3.14 from astral-sh/python-build-standalone GitHub releases** — all hosts
  allowlisted. So a setup script of the shape
  `curl -L https://github.com/jdx/mise/releases/download/... ; mise install`
  (or `uv python install 3.14`) is network-feasible with zero Custom entries.
- Setup-script/cache coupling (web doc § "Environment caching"): the script
  must finish in ~5 minutes for the snapshot to build; the snapshot persists
  ~7 days; **changing the environment's allowed network hosts invalidates the
  cache and re-runs the setup script** — so allowlist churn has a startup-cost
  side effect.

### F6. Recommended policy shape for ray-manaloto/dotfiles (synthesis)

**Custom, with "Also include default list of common package managers" checked**,
plus these entries (each traced to a concrete need above):

```text
api.doppler.com                          # doppler secrets download (devcontainer parity)
cli.doppler.com                          # doppler CLI install script (or use packages.doppler.com apt repo)
packages.doppler.com                     # doppler apt repo alternative
pkg-containers.githubusercontent.com     # GHCR layer blobs — any ghcr.io pull (#71629)
mise.run                                 # only if using the curl|sh installer (else omit; use GitHub releases)
mise.jdx.dev                             # mise.run script's CDN for current-version binaries (else MISE_INSTALL_FROM_GITHUB=1)
ppa.launchpadcontent.net                 # only if any apt PPA is needed (#71629)
```

Everything else the four mise tiers need (npm, PyPI, conda-forge, GitHub
releases/aqua, gitlab fronts, ubuntu archive) is already in the Trusted
defaults. Note the 38GB `dotfiles-devcontainer:dev` pull is *network*-unblocked
by the `pkg-containers` entry but remains *disk*-blocked: cloud sessions have
~30 GB disk (web doc § "Resource limits") — a cross-angle constraint for
angles 1/5.

## Uncertainties / gaps

- **U1 — mise proxy-env behavior in the sandbox is inferred, not probed.**
  reqwest-based mise is expected to honor `HTTPS_PROXY`; no doc states it and
  no live web-session probe of `mise install` was possible from this session
  (Bash disabled). Needs a one-shot probe in a real web session
  (`mise install` + `__agentproxy/status`).
- **U2 — MITM vs CONNECT-tunnel ambiguity.** #71629 evidence shows plain
  CONNECT tunneling (no CA issue) for the web sandbox, while this research
  container ships a proxy CA bundle (`/root/.ccr/ca-bundle.crt`), suggesting
  at least some Anthropic-managed surfaces TLS-intercept. If the web sandbox
  ever MITMs, mise ≥2025.7.2 + root `update-ca-certificates` covers it; older
  pins would fail with `UnknownIssuer`.
- **U3 — aqua verification endpoints.** mise's aqua backend supports cosign /
  SLSA / minisign / GitHub-attestation verification "implemented in Rust
  without external tools" (cache `llms-full.txt:1840-1846`); whether
  verification dials sigstore infrastructure (`tuf-repo-cdn.sigstore.dev`,
  `rekor.sigstore.dev` — NOT in the Trusted defaults) at install time is
  unverified. If it does, aqua installs could fail or silently skip
  verification under Trusted; probe needed.
- **U4 — gitlab release-asset CDN** hosts behind `gitlab.com` downloads not
  verified (repo currently has no `gitlab:` tools; low priority).
- **U5 — allowlist currency.** The default-domain list was read from the live
  docs today, but #71629 proves docs↔proxy drift both ways; the effective
  policy is only observable from inside a session.
- **U6 — Trusted-list evolution.** #71629 is open with no Anthropic response
  captured; whether `pkg-containers.githubusercontent.com` etc. get added
  upstream (making the Custom entries redundant) should be re-checked before
  finalizing the environment config.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — issues #71629 (+cross-refs #69174, #11897) for in-sandbox egress-proxy/allowlist ground truth.
- [jdx/mise](https://github.com/jdx/mise) — docs (local mintlify cache) for backend endpoints/aqua registry; discussions #5313 + PR #5459 for custom-CA fix; mise.run install script for installer hosts.
- [aquaproj/aqua-registry](https://github.com/aquaproj/aqua-registry) — referenced as the registry compiled into mise (metadata source, not fetched at runtime).
- [astral-sh/python-build-standalone](https://github.com/astral-sh/python-build-standalone) — the GitHub-releases host mise/uv use for CPython downloads (allowlist mapping).
- [DopplerHQ/cli](https://github.com/DopplerHQ/cli) — via docs.doppler.com (CLI install + API hostnames).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — local reads: mise.toml, .config/mise/conf.d/shared.toml, .devcontainer/mise-{system,runtime}.toml, inventory report.
