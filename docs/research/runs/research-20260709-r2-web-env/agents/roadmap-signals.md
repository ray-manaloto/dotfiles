# Run A / Angle #5 — Custom base image support for Claude Code web/cloud sessions: state + roadmap signals

Date: 2026-07-09. Researcher: roadmap-signals agent (Run A, angle 5 of 5).
All web sources fetched 2026-07-09; publication dates noted per source.

## Findings

### 1. Shipped today: the web-session base image is Anthropic-managed and NOT replaceable — stated explicitly in the official docs

The canonical docs page (https://code.claude.com/docs/en/claude-code-on-the-web,
fetched 2026-07-09) says, verbatim, in the "Install dependencies with a
SessionStart hook" section:

> "Replacing the base image with your own Docker image is **not yet
> supported**. Use a setup script to install what you need on top of the
> [provided image], or run your image as a container alongside Claude with
> `docker compose`."

This is the single authoritative statement of current state. Supporting
facts from the same page:

- Each session runs "in a fresh Anthropic-managed VM with your repository
  cloned"; setup scripts "run as root on **Ubuntu 24.04**".
- Resource ceilings ("may change over time"): **4 vCPUs, 16 GB RAM, 30 GB
  disk**.
- The only sanctioned customization layers are: (a) the **environment setup
  script** (cloud-environment-scoped, runs before Claude Code launches,
  should finish in ~5 minutes so the cache snapshot can build), (b)
  **SessionStart hooks** from the repo's `.claude/settings.json` (run every
  session, cloud + local, gate on `CLAUDE_CODE_REMOTE=true`), (c)
  **environment variables** (.env format; no secrets store yet), and (d)
  the **network access level** (None / Trusted / Full / Custom allowlist).
- **Environment caching**: after the setup script's first run "Anthropic
  snapshots the filesystem and reuses that snapshot"; cache rebuilds when
  the setup script or allowed hosts change, or after roughly **7 days**.
- A `check-tools` command "only exists in cloud sessions" and reports exact
  pre-installed versions.

### 2. Shipped today: Docker/dockerd/docker compose run INSIDE web sessions — the sanctioned "custom image" path is a sibling container, not a replaced base

The same docs page lists **docker, dockerd, docker compose** as
pre-installed, and says: "Docker is available for running containerized
services... If your images are large or slow to pull, add `docker compose
pull` or `docker compose build` to your setup script. The pulled images are
saved in the cached environment." The Trusted network default allowlists
the container registries needed for pulls, including **ghcr.io**,
registry-1.docker.io/auth/index, gcr.io/\*.gcr.io, mcr.microsoft.com, and
public.ecr.aws (docs, "Default allowed domains" → Container registries).

Repo-specific consequence: the sibling-container path is how ANY custom
image gets into a web session today — but this repo's
`ghcr.io/ray-manaloto/dotfiles-devcontainer:dev` image is **~38 GB**
(AGENTS.md; `.claude/rules/verify-before-advancing.md`), which exceeds the
**30 GB session disk ceiling**, so pulling the heavy devcontainer image
inside a web session is infeasible regardless of allowlist. A thin image
would fit; the fat one cannot.

### 3. Issue #29515 was about Docker-in-web, not base-image replacement — and it resolved via shipping + community workaround, with zero Anthropic comment

anthropics/claude-code#29515 "[FEATURE] Docker support in Claude Code web
environment" (https://github.com/anthropics/claude-code/issues/29515):

- Opened 2026-02-28 by @juanluiscr27; labels `area:claude-code-web`,
  `area:sandbox`, `enhancement`, `platform:web`; 18 👍 reactions, 5 comments.
- At filing time "Docker is not available as an executable tool" in web
  sessions; user @ja-ka posted (2026-03-10) a working workaround: a
  `session-start.sh` starting dockerd with the **vfs storage driver** inside
  the sandbox (noting sessions ran on "Linux kernel 4.4.0" per his probe).
- **Closed by the author on 2026-03-29** after confirming "I have tested for
  a few weeks and it works"; auto-locked 2026-04-07. **No Anthropic staff
  response appears anywhere in the thread** (api.github.com issue + comments
  JSON, fetched 2026-07-09).
- Docker is now officially pre-installed (finding 2), so the capability the
  issue asked for is shipped, but the issue itself is NOT evidence of any
  base-image roadmap.

### 4. No official plan or timeline exists for custom base images in Claude Code on the web — the only forward signal is the word "yet"

Evidence of absence, all checked 2026-07-09:

- **Docs**: "not yet supported" (finding 1) is the only forward-looking
  phrase; no "coming soon"/"planned" statement anywhere on the page.
- **CHANGELOG** (raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md):
  no entry mentioning base image, custom image, or environment-image
  replacement (scan of recent 2.1.x entries; cloud-related entries are
  session-plumbing: v2.1.154 remote env vars, v2.1.179 session trailers,
  v2.1.195 provisioning checklist, v2.1.199 teleport).
- **Issue tracker**: GitHub search `repo:anthropics/claude-code "base
  image" in:title` returns 8 issues, none a feature request for
  replaceable web base images. The top-reacted open `area:claude-code-web`
  enhancements are instead: **#32733** secure secrets injection
  (2026-03-10), **#10018** start from non-default branch (2025-10-21),
  **#58543** per-repository default cloud environment (2026-05-13),
  **#54054** Azure DevOps support (2026-04-27).
- **Launch blog** (https://claude.com/blog/claude-code-on-the-web,
  2025-10-20): sandbox isolation + custom network config only; no image
  customization mention.
- Web searches for maintainer statements ("working on custom images" etc.)
  found none; third-party mentions of "customise sandbox images" all trace
  to the Managed Agents / Cloudflare path (finding 5), not Claude Code web.

Classification: **custom base images for Claude Code web = not shipped, not
officially announced; any timeline is community speculation.**

### 5. The strongest roadmap signal is architectural, from an adjacent product: Claude Managed Agents shipped BYO-image via SELF-HOSTED sandboxes (public beta, 2026-05-19)

Anthropic's answer to "I need my own image" shipped on the **API platform**,
not on Claude Code web:

- Announcement "New in Claude Managed Agents: self-hosted sandboxes and MCP
  tunnels" (https://claude.com/blog/claude-managed-agents-updates,
  **2026-05-19**): "the agent loop ... stays on Anthropic's infrastructure"
  while tool execution moves to infrastructure you control; "you control
  the compute: resource sizing and **the runtime image** are set on your
  side."
- Docs (https://platform.claude.com/docs/en/managed-agents/self-hosted-sandboxes,
  beta header `managed-agents-2026-04-01`): an "environment worker" polls a
  work queue; the sandbox-per-session pattern is literally a Dockerfile
  starting `FROM your-base-image` with the `ant` CLI as entrypoint — full
  BYO base image. Managed providers: **Cloudflare, Daytona, Modal, Vercel**,
  plus platform guides for AWS Lambda MicroVMs, Blaxel, E2B, GKE Agent
  Sandbox, Namespace, Superserve, and a custom worker API for air-gapped
  infra. Cloudflare coverage (itbrief.co.uk, 2026-05-21) confirms users can
  "customise sandbox images."
- Meanwhile the Managed Agents **Anthropic-managed** cloud sandboxes
  (https://platform.claude.com/docs/en/managed-agents/cloud-sandboxes-reference)
  are ALSO a fixed image — Ubuntu **22.04**, x86_64, up to 8 GB RAM / 10 GB
  disk, network disabled by default — with no custom-image option.

Pattern across both products: **Anthropic-managed sandbox ⇒ fixed
Anthropic image; custom image ⇒ execution moves to customer-controlled
infrastructure.** This is the best available signal for how (and where)
BYO-image is likely to land: via self-hosted execution surfaces, not via
uploading images into Anthropic's consumer web sandbox. Claude Code on the
web has no self-hosted-execution option today; the closest escape hatch the
docs give is Remote Control ("For workloads beyond these limits, use Remote
Control to run Claude Code on your own hardware").

### 6. Corroborating operational evidence that the web base image is Anthropic-owned and mutable under users

- **#75652** (opened 2026-07-08, open): "Code on the web: `apt-get update`
  in setup scripts fails with exit 100 — base image ships the retired
  ondrej/php PPA" — Anthropic's image contents drift and can break user
  setup scripts; users cannot pin or fork the image.
- **#53608** (2026-04-26, open): "[BUG] [P0] Claude Code Web sandbox
  produces Docker-incompatible projects" — the sandbox "is not equivalent
  to the final Dockerized environment", the parity gap a custom image
  would close.
- **#57687** (2026-05-09, open): Git LFS unsupported through the GitHub
  proxy — another fixed-infrastructure constraint users route around.
- Cowork (a distinct local-VM sandbox product) issues **#52252** /
  **#47006** show the same fixed-Anthropic-base-image pattern on that
  surface too (base image too large for allocated disk; ~3.2 GB waste).

### Implications for the domain recommendation (this repo)

1. **A single "one image everywhere" is impossible today**: web sessions
   cannot boot ray-manaloto/dotfiles-devcontainer, period (finding 1), and
   the 38 GB image cannot even ride along as a sibling container inside the
   30 GB session disk (finding 2).
2. The web-compatible unit for this repo is therefore a **setup script +
   SessionStart hook layer** (install python 3.14/uv/mise/hk/pkl on top of
   Anthropic's Ubuntu 24.04 image; snapshot-cached ~7 days), i.e. the
   two-artifact fallback topology, with convergence gated on an
   **unannounced** capability — do not plan a date for it.
3. If true image parity becomes a hard requirement, the only shipped
   Anthropic path is Managed Agents self-hosted sandboxes (API platform,
   different product/pricing/auth), or Remote Control on own hardware —
   both outside the claude.ai/code web-session UX.

## Uncertainties / gaps

- **CHANGELOG scan coverage**: the CHANGELOG is very large; the fetch-model
  scan covered recent 2.1.x entries. Older entries (e.g., when Docker first
  appeared in the web image, likely ~Mar–Apr 2026 between #29515's filing
  and the current docs) were not pinpointed to a version.
- **No access to Anthropic-internal roadmaps**: absence of a public plan is
  not proof none exists; the "not yet supported" phrasing implies intent
  without commitment.
- **#29515 kernel claim** ("Linux kernel 4.4.0") is a single community
  probe from 2026-03-10 and may be stale (gVisor-style kernels often report
  fixed versions); treat as indicative, not current fact.
- The docs page was fetched live; per-section last-updated dates are not
  exposed, so I cannot date exactly when the "not yet supported" sentence
  and the Docker pre-install landed.
- Whether Claude Code web sessions share literal infrastructure with
  Managed Agents cloud sandboxes is unconfirmed; their published specs
  differ (Ubuntu 24.04 / 4 vCPU / 16 GB / 30 GB vs Ubuntu 22.04 / 8 GB /
  10 GB), suggesting related-but-distinct fleets.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — issues #29515 (+comments/events JSON), #75652, #53608, #57687, #52252, #47006, #32733, #10018, #58543, #54054; issue searches; CHANGELOG.md; its docs at code.claude.com.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — grounding inventory (`docs/research/runs/research-20260709-r2-inventory/report.md`) and image-size facts from AGENTS.md/rules.
