# Run A — Claude Code web/cloud execution environment: domain report

Date: 2026-07-09. Synthesis of 5 angle reports
(`.omc/research/research-20260709-r2-web-env/agents/{official-docs,tool-compat,network-allowlist,caching-lifecycle,roadmap-signals}.md`),
grounded on `.omc/research/research-20260709-r2-inventory/report.md`. All
load-bearing claims below passed 3/3 adversarial verification against the
live primary source (https://code.claude.com/docs/en/claude-code-on-the-web,
fetched 2026-07-09).

---

## Executive summary — RECOMMENDATION

**Ray's ideal — ONE image usable in web sessions + CI + devcontainer — is
impossible today, on two independent grounds:** (1) "Replacing the base
image with your own Docker image is not yet supported" (official docs,
verbatim, 2026-07-09); (2) even the sanctioned docker-compose sidecar path
cannot carry the ~38 GB `ghcr.io/ray-manaloto/dotfiles-devcontainer:dev`
image, because web sessions have a ~30 GB disk ceiling. There is no
announced roadmap for custom base images — the only forward signal is the
word "yet".

**Adopt the fallback topology now** (two artifacts from a common source of
truth), specifically:

1. **Keep the GHA-built devcontainer image** exactly as-is for
   devcontainer + CI (no change).
2. **Add a "web layer" — NOT an image**: a per-cloud-environment **setup
   script** (root, Ubuntu 24.04, ≤5-minute budget, filesystem-snapshot
   cached ~7 days) that installs mise (direct GitHub-release binary — the
   `mise.run` installer host is blocked under Trusted), then
   `mise trust && mise install` the pinned shared toolchain (hk 1.50.0,
   pkl 0.31.1, python 3.14.6, uv 0.11.27 all resolve to allowlisted
   GitHub/PyPI/npm hosts under the DEFAULT Trusted policy — no Custom
   policy needed), plus `uv sync --project python`; **and** a repo
   **SessionStart hook** gated on `CLAUDE_CODE_REMOTE=true` that re-runs
   idempotently every session/resume, persisting PATH via
   `$CLAUDE_ENV_FILE`. This is the platform's de-facto "custom image"
   mechanism, and it directly fixes the current web-session brick: the
   PreToolUse hook guard (`uv run --project python dotfiles-setup hook
   pretooluse`, `.claude/settings.json:9-20`) fails to start because the
   Anthropic image has no Python ≥3.14 (`python/pyproject.toml:5`), and a
   hook that fails to start blocks every Bash call (fail-closed —
   observed, not documented).
3. **Set `GITHUB_TOKEN` as an environment variable** in the cloud
   environment config — mise's GitHub-backed version resolution hits the
   anonymous 60/hr API rate limit on shared egress IPs without it
   (anthropics/claude-code#52963). Note the docs' caveat: env vars are
   visible to anyone who can edit the environment (no secrets store yet).
4. **Do not plan a convergence date.** Single-image convergence is gated
   on an unannounced capability; Anthropic's shipped BYO-image answer
   (Managed Agents self-hosted sandboxes, 2026-05-19) moves execution to
   customer infrastructure — a different product, not a web-session
   feature.

The common source of truth between the two artifacts already exists:
`.config/mise/conf.d/shared.toml` (the 20 exact-pinned host↔image tools) —
the web setup script should install from it (plus the hk-step host tools),
not from a third hand-maintained list.

---

## 1. Exact current capability set of web session environments

All from https://code.claude.com/docs/en/claude-code-on-the-web (fetched
2026-07-09) unless noted; verification: CONFIRMED 3/3.

- **Base image / owner**: each session runs "in a fresh Anthropic-managed
  VM with your repository cloned". Setup scripts "run as root on Ubuntu
  24.04". No image name/tag/digest/Dockerfile is published; exact tool
  versions are only discoverable in-session via the cloud-only
  `check-tools` command. Architecture is x86_64 — corroborated by
  anthropics/claude-code#55000 (2026-04-30, "Ubuntu 24.04 LTS x86_64") and
  empirically in this session's container (4× Intel Xeon, AVX-512;
  `agents/caching-lifecycle.md` §5). The repo's AMD64-only constraint (R3)
  is therefore *compatible*; size is the blocker, not arch.
- **Resources**: "approximate resource ceilings that may change over
  time: 4 vCPUs, 16 GB of RAM, 30 GB of disk". Empirical probe of this
  session: 4 vCPU and 16 GB match; the virtual block device is 256 GiB
  thin-provisioned, i.e. 30 GB is a policy quota, not the device size —
  do not design against the undocumented headroom.
- **Pre-installed**: Python 3.x with pip/poetry/**uv**/black/mypy/pytest/
  ruff; Node 20-22 (nvm); GCC/Clang/cmake/ninja/conan; **docker, dockerd,
  docker compose**; PostgreSQL 16, Redis 7; git/jq/yq/ripgrep/tmux. **NOT
  pre-installed: mise, hk, pkl, gh, Python ≥3.14** (docs table + observed
  in the remote container,
  `.omc/research/research-20260709-r2-inventory/report.md:120-124`).
- **Session lifetime**: sessions keep running after the tab closes;
  "Cloud sessions stop after a period of inactivity and the underlying
  environment is reclaimed" — the inactivity window is NOT quantified
  anywhere. Reopening provisions a fresh environment with conversation
  history restored; uncommitted working-tree state is gone.
- **Kernel/isolation** (empirical, this session): custom Anthropic
  sandbox kernel 6.18.5, hypervisor flag, virtio disks — a microVM guest,
  with the harness mounted read-only at `/opt/claude-code`.
- **Product constraints**: research preview (Pro/Max/Team/Enterprise
  premium); no Manual/Bypass permission modes; ZDR orgs excluded; usage
  draws shared rate limits (no separate compute charge); GitHub only
  (GitLab/Bitbucket via one-way ≤100MB bundle); git push restricted to the
  current working branch via the GitHub proxy.

## 2. Can mise / hk / pkl / uv / python 3.14 install and run? YES — and the fix for this repo's web brick

Verification: CONFIRMED 3/3 (both the toolchain-installability claim and
the fix-shape claim).

**Why the repo fails today** (bootstrap ordering, not incompatibility):
`.claude/settings.json:9-20` wires a PreToolUse hook on every Bash call to
`uv run --project python dotfiles-setup hook pretooluse` (20 s timeout);
`python/pyproject.toml:5` requires Python ≥3.14; the cloud image has no
Python ≥3.14 and no mise, so the guard cannot start and the harness fails
closed — every Bash call is blocked (observed in this very session;
hooks docs specify exit-2 blocking for PreToolUse but say nothing about a
hook that fails to *start* — the fail-closed behavior is observed, not
documented).

**All five components install under the DEFAULT Trusted policy** via the
GitHub-releases path (per `.config/mise/conf.d/shared.toml` pins):

| Component | Path | Allowlisted? |
|---|---|---|
| mise | direct binary: `github.com/jdx/mise/releases/download/v<V>/mise-v<V>-linux-x64` | Yes |
| hk 1.50.0 | `mise install` → aqua:jdx/hk GitHub releases (aqua registry compiled into mise binary — no extra fetch) | Yes |
| pkl 0.31.1 | mise → aqua:apple/pkl releases (pklr is embedded in hk ≥1.49) | Yes |
| python 3.14.6 | mise core python or `uv python install 3.14` → astral-sh/python-build-standalone GitHub releases | Yes |
| uv 0.11.27 | pre-installed (unknown version); exact pin via mise → astral-sh/uv releases | Yes |

**The fix shape** (documented mechanism; draft script in
`agents/tool-compat.md` F5):

- **Environment setup script** (web UI, per environment): install mise
  from GitHub releases → `mise trust && mise install` (scoped set — see
  below) → `uv sync --project python`. Runs once, snapshot-cached ~7
  days. Non-zero exit blocks session start; keep <5 min (parallelize with
  `&`/`wait`; move overflow to a background SessionStart hook).
- **Repo SessionStart hook** (`.claude/settings.json`, matcher
  `startup|resume`): gate on `[ "${CLAUDE_CODE_REMOTE:-}" = "true" ]`,
  fast idempotent re-check (`mise install` no-ops warm), append PATH
  (`~/.local/bin` + mise shims) to `$CLAUDE_ENV_FILE`. SessionStart runs
  every session including resume, has a 600 s default timeout, is NOT
  gated by the PreToolUse Bash guard, and its failures are non-blocking.
  This is an established pattern — 53 public repos pair
  `CLAUDE_CODE_REMOTE` with `mise install`; Anthropic ships a first-party
  `session-start-hook` skill prescribing exactly this workflow.
- **Scope trim**: the full root `mise.toml` (~40 tools incl. `npm:renovate`
  ~354 MB, aws/azure CLIs, colima/lima) will blow the 5-minute budget and
  adds nothing to web sessions. Install the shared.toml 20 + the hk-step
  host tools (editorconfig-checker, agnix, zizmor, markdownlint-cli2,
  rumdl, biome, ast-grep, npm:renovate only if `renovate-config-validator`
  must run). A `MISE_ENV=web` overlay or curated `mise install a b c…`
  list are the two clean shapes.
- The gates themselves are web-compatible: `mise run lint` (700 s outer
  bound, no PTY), `uv run --project python pytest`, and
  `dotfiles-setup verify run` need only the venv + installed tools; hk's
  pklr backend needs no network at lint time.

## 3. Network policies vs mise backends

Verification: CONFIRMED 3/3 for the backend/allowlist mapping. Four levels
per environment: **None / Trusted (default) / Full / Custom** (own list, `*.`
wildcards, optional union with defaults). All egress passes an HTTP(S)
security proxy; blocked hosts fail `403` + `x-deny-reason:
host_not_allowed` (routines.md). Git-to-GitHub uses a SEPARATE dedicated
proxy independent of the access level (works even under None; push
restricted to the current branch; tokens never enter the container). MCP
connector traffic bypasses the allowlist via Anthropic's servers.

Backend matrix under **Trusted** (angle 3, `agents/network-allowlist.md` F3):

| Backend / source | Verdict |
|---|---|
| npm (`registry.npmjs.org`) | Works |
| pipx / PyPI / uv (`pypi.org`, `files.pythonhosted.org`) | Works |
| conda/rattler (`conda.anaconda.org`, `repo.anaconda.com`) | Works (docs-supported; not live-probed end-to-end) |
| aqua / github / ubi backends (GitHub release-asset hosts) | Works |
| cargo (`crates.io` + static/index) | Works |
| mise core python / `uv python install` (python-build-standalone releases) | Works — the correct Python 3.14 path |
| **mise.run / mise.jdx.dev installer** | **Blocked** — absent from allowlist; use the direct GitHub-release binary URL (or `MISE_INSTALL_FROM_GITHUB=1` + Custom `mise.run`) |
| **astral.sh installer** | **Blocked** (403 confirmed, #52963) — moot, uv pre-installed |
| **api.doppler.com / cli.doppler.com** | **Blocked** — Custom entry or env-var secrets instead |
| apt main archive | Works (`apt install gh` is the docs' own example); **PPAs blocked** (`ppa.launchpadcontent.net` not allowlisted, #71629 — incl. the image's own pre-enabled deadsnakes PPA, so `apt install python3.14` is NOT a viable fix path) |
| **ghcr.io pulls** | **Docs-allowlisted but fails mid-pull in practice**: manifests OK, layer blobs come from `pkg-containers.githubusercontent.com`, which is NOT allowlisted (#71629, open) — needs a Custom entry. Docker Hub has the analogous blob-CDN gap (#69174) |

Two systemic caveats: (a) **docs↔enforced-list drift is a known issue
class** (#71629, #66567) — treat the published list as indicative, probe
`$HTTPS_PROXY/__agentproxy/status` in a live session before locking a
Custom allowlist; (b) **GitHub anonymous API rate limits** (60/hr on
shared egress IPs) make `GITHUB_TOKEN` effectively required for reliable
`mise install` even though the hosts are allowlisted (#52963). The proxy
is TLS-aware; mise/uv (rustls) demonstrably work through it (mise ≥
2025.7.2 honors custom CAs); Bun is the documented incompatible example.

Recommended policy for this repo: **Trusted is sufficient for the lint/
pytest/verify gates.** Go Custom (+"include defaults") only if you need:
`api.doppler.com` (+`cli.doppler.com`/`packages.doppler.com`),
`pkg-containers.githubusercontent.com` (any ghcr pull), or
`ppa.launchpadcontent.net`. Note: changing allowed hosts invalidates the
environment cache and re-runs the setup script.

## 4. Caching and persistence between sessions

Verification: CONFIRMED 3/3. Three distinct lifetimes:

1. **VM + working tree**: per session; fresh clone every session;
   reclaimed after unquantified inactivity; uncommitted edits and
   mid-session installs are lost ("installs don't carry over").
2. **Environment cache snapshot**: after the setup script's first
   successful run, "Anthropic snapshots the filesystem" — installed
   toolchains AND pulled docker images persist ("dependencies, tools, and
   Docker images already on disk"). Rebuilt when the setup script or
   allowed hosts change, or after ~7 days. Captures files, not running
   processes. SessionStart-hook-installed files are also captured (per
   Anthropic's own session-start-hook skill), though the hook re-runs
   every start/resume. This snapshot is the platform's de-facto "custom
   image".
3. **Conversation history**: retained by claude.ai across reclaim.

Durable state must therefore live in the repo, a pushed branch, or the
setup-script snapshot (a ~7-day accelerator, not permanent storage).

## 5. Docker inside web sessions — and the 38 GB question

Verification: CONFIRMED 3/3. `docker`, `dockerd`, `docker compose` are
pre-installed — a real daemon inside the per-session microVM (not sibling
containers to a host, not classic DinD). The docs explicitly sanction
"run your image as a container alongside Claude with `docker compose`" as
the substitute for custom base images, and pulled images are
snapshot-cached. Working Docker landed ~May 2026 (April-era failure
reports #53430 predate it; #29515 requested it and was closed by its
author after the community vfs-storage-driver workaround, with zero
Anthropic comment).

**The heavy devcontainer image cannot ride this path**: ~38 GB
(mise.toml:230, build-publish.yml:631, AGENTS.md) > the ~30 GB disk
ceiling — before the repo clone, base toolchain, and pull-time
extraction scratch. Additionally, under plain Trusted the pull would 403
on GHCR layer blobs (§3), and a large pull collides with the ~5-minute
setup-script cache budget. A dramatically slimmed image (realistically
≤ ~15-20 GB uncompressed; e.g., the runtime tier only —
`.devcontainer/mise-runtime.toml` is the natural fork seam) could ride
the sidecar path with a Custom allowlist entry, amortized to one pull per
~7 days via the snapshot. But for this repo's web use case (lint + pytest
+ verify), the setup-script layer makes the sidecar unnecessary.

## 6. Custom base image support: state and roadmap

Verification: CONFIRMED 3/3. **Not supported, not announced.** The docs'
verbatim, sole statement: "Replacing the base image with your own Docker
image is not yet supported. Use a setup script to install what you need
on top of the provided image, or run your image as a container alongside
Claude with `docker compose`." The word "yet" is the only forward signal;
the CHANGELOG has no base-image entries; no issue-tracker feature request
for replaceable web base images exists (#29515 was Docker-in-web, shipped);
no maintainer statements found.

The strongest architectural signal is from an adjacent product: **Claude
Managed Agents self-hosted sandboxes** (public beta 2026-05-19) deliver
BYO base image by moving execution to customer-controlled infrastructure
(Cloudflare/Daytona/Modal/Vercel/…), while Anthropic-managed sandboxes on
that surface remain a fixed image too (Ubuntu 22.04, 8 GB/10 GB). Pattern:
**Anthropic-managed sandbox ⇒ fixed Anthropic image; custom image ⇒ your
infrastructure.** For Claude Code specifically, the only "own hardware"
escape hatch is Remote Control. Corroborating evidence that the web base
is Anthropic-owned and drifts under users: #75652 (retired PPA in the base
image breaks setup scripts), #53608 (sandbox/Docker parity gap), #57687
(no Git LFS through the GitHub proxy).

**Planning consequence**: treat one-image convergence as gated on an
unannounced capability with no date. The two-artifact topology should be
designed to converge cheaply (both artifacts consuming
`shared.toml`/`mise.lock` pins), not to be temporary.

---

## Refuted / unverified claims

**Refuted: none.** All 10 load-bearing claims submitted to adversarial
verification returned CONFIRMED (3/3 upheld each). No claim from the angle
reports was refuted.

**Unverified / caveated items** (do not treat as established fact):

- **Fail-closed on hook-start failure** (the mechanism bricking Bash
  today) is *observed* in this session and consistent across probes, but
  the hooks docs specify only exit-code semantics — the behavior for a
  hook whose command cannot start is undocumented. The uv-exit-2 → deny
  mapping is inference.
- **"Docs-allowlisted" ≠ runtime guarantee**: the enforced proxy list
  drifts from the published one in both directions (#71629, #66567,
  #10307). GHCR/Docker-Hub blob CDNs are the proven gaps; conda/rattler
  end-to-end success in a live web session is docs-supported but not
  empirically re-verified.
- **Inactivity window before reclaim**: unquantified in docs; the ~7-day
  session-TTL figure comes from a single April-2026 community issue
  (#50197) and behavior has since changed.
- **Environment-cache size limit**: whether a multi-GB docker layer
  actually survives snapshotting is not documented.
- **30 GB disk enforcement mechanism**: quota vs monitoring-based
  termination unknown (device is 256 GiB thin-provisioned).
- **Setup-script cwd** (repo cloned and current at script time?) is
  implied but not explicit; if not, `mise trust && mise install` must
  stay in the SessionStart hook.
- **Async SessionStart** (`{"async": true, ...}` stdout JSON): used by
  Anthropic's own skill and community repos, but the hooks doc documents
  async for command hooks generally — verify live before relying on it.
- **aqua verification endpoints** (sigstore/rekor hosts, not allowlisted):
  whether mise's aqua cosign/SLSA verification dials them at install time
  is unprobed.
- **#29515's "kernel 4.4.0"** probe is stale (this session observes 6.18.5).
- This research container is a Cowork/research flavor of the sandbox, not
  a claude.ai/code web session proper; the substrate facts (OS, CPU, RAM,
  proxy shape) match, but minor differences are possible.

## Open questions for Ray (with recommended answers)

1. **Adopt the two-artifact topology now, or wait for custom base
   images?** → **Adopt now.** No roadmap exists; the setup-script +
   SessionStart-hook layer is small, converges naturally later (both
   artifacts read `shared.toml` pins), and unblocks web sessions this
   week.
2. **Which network policy for the environment?** → **Trusted (default)**
   for the lint/pytest/verify use case — zero Custom entries needed. Move
   to Custom+defaults only when adding Doppler
   (`api.doppler.com`) or any ghcr pull
   (`pkg-containers.githubusercontent.com`).
3. **How to handle secrets (Doppler) in web sessions?** → For now, don't:
   the gates don't need Doppler (it's devcontainer-only,
   `devcontainer.json:198`). If web sessions later need secrets, put a
   least-privilege `DOPPLER_TOKEN` (or the individual values) in the
   environment env vars, accepting the documented visibility caveat — a
   dedicated secrets store "is not yet available" (#32733 tracks it).
4. **Scope of the web toolchain install?** → shared.toml 20 + hk-step
   host tools via a `MISE_ENV=web` overlay (or curated install list). Do
   NOT `mise install` the full root toolset (renovate/aws/azure/colima
   blow the 5-minute cache budget for zero web value).
5. **Set `GITHUB_TOKEN` in the environment config?** → **Yes, read-only
   PAT, treat as required** — anonymous GitHub API rate limiting is the
   dominant real-world mise-in-web failure mode (#52963 + community
   corpus), and env-var visibility is acceptable for a read-only token.
6. **Should the guard fail open in web sessions?** → Worth considering as
   a belt-and-braces change: have the PreToolUse wiring (or the guard
   itself) no-op when its interpreter is unavailable, so a cold cache
   never bricks Bash. The setup script makes this rare, but the
   fail-closed behavior is undocumented and could change under you either
   way.
7. **Slimmed sidecar image (runtime tier) for web?** → **Defer.** Nothing
   in the web use case needs it yet; revisit if web sessions ever need
   the C++/p2996 toolchain, and only with the blob-CDN Custom entry and
   a ≤15-20 GB target.
8. **First live-session probe list** (one session, ~15 min): run
   `check-tools`; run the setup script; `mise run lint` + pytest +
   `dotfiles-setup verify run`; `$HTTPS_PROXY/__agentproxy/status` after
   `mise install`; confirm snapshot warm-start on a second session.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — official docs (code.claude.com), CHANGELOG, issues #29515, #41741, #50197/#50177, #52963, #53430, #53608, #54054, #55000, #57687, #58543, #66567, #69174, #71629, #75652, #10018, #32733, #47006, #52252, #10307
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — repo baseline facts (settings.json, mise tiers, pyproject, image size) read from the working tree
- [jdx/mise](https://github.com/jdx/mise) — install methods, backends, aqua registry, token precedence, custom-CA fix (discussions #5313, PR #5459), mise.run installer script
- [jdx/hk](https://github.com/jdx/hk) — install methods, mise integration (local mintlify cache)
- [apple/pkl](https://github.com/apple/pkl) — pkl release-binary source
- [astral-sh/python-build-standalone](https://github.com/astral-sh/python-build-standalone) — CPython 3.14 binary source for mise/uv
- [aquaproj/aqua-registry](https://github.com/aquaproj/aqua-registry) — registry compiled into mise (metadata source)
- [DopplerHQ/cli](https://github.com/DopplerHQ/cli) — CLI install + API hostnames (via docs.doppler.com)
- [jonpulsifer/infra](https://github.com/jonpulsifer/infra) — exemplar session-start.sh (curated install, CLAUDE_ENV_FILE)
- [datenknoten/freundebuch](https://github.com/datenknoten/freundebuch) — GITHUB_TOKEN-for-mise hook pattern
- [joeblew999/vm-uncloud](https://github.com/joeblew999/vm-uncloud) — anonymous GH API 403 during mise install in web sessions
- [hco/dependency-dir-analyzer](https://github.com/hco/dependency-dir-analyzer) — CLAUDE.md web-session mise hook pattern
- [wado-lang/wado](https://github.com/wado-lang/wado) — .claude/hooks/mise-setup.sh exemplar
- [entireio/cli](https://github.com/entireio/cli) — .claude/scripts/remote-setup.sh exemplar
- [StoDevX/AAO-React-Native](https://github.com/StoDevX/AAO-React-Native) — inline settings.json SessionStart mise command
- [richardthe3rd/cambridge-beer-festival-app](https://github.com/richardthe3rd/cambridge-beer-festival-app) — async SessionStart hook exemplar
