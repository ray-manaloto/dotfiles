# Run A / Angle 4 — Session caching, persistence, and sibling containers (Claude Code on the web)

Researcher: caching-lifecycle agent, 2026-07-09.
Scope: what persists between web sessions (repo clone, tools, caches), container
reclaim policy, and docker/docker-compose availability inside web sessions
(sibling containers / DinD) — including whether the ~38GB
`ghcr.io/ray-manaloto/dotfiles-devcontainer:dev` image could be pulled inside one.

Primary source throughout: https://code.claude.com/docs/en/claude-code-on-the-web
(fetched as `.md` 2026-07-09; quotes below are verbatim from that fetch unless
otherwise cited). A second evidence stream is **empirical probing of THIS very
session's container**, which runs in the Anthropic cloud sandbox (`/proc`,
`/etc/os-release`, filesystem reads — Bash was unavailable, so all probes are
Read/Glob-based).

---

## Findings

### 1. Lifecycle model: fresh isolated VM per session; per-environment filesystem snapshot

- "Each session runs in a fresh Anthropic-managed VM with your repository
  cloned." and "Cloud sessions start from a fresh clone of your repository."
  (docs, § The cloud environment). So the **repo clone is always fresh per
  session** — clone-freshness is not a persistence concern; installed tools and
  caches are.
- Isolation: "each session runs in an isolated, Anthropic-managed VM" (docs,
  § Security and isolation; same claim on
  https://code.claude.com/docs/en/sandbox-environments.md — "Full operating
  system, hosted by Anthropic").
- **Empirical (this session's container, 2026-07-09):**
  - `/etc/os-release`: `Ubuntu 24.04.4 LTS (Noble Numbat)` — matches docs
    ("Scripts run as root on Ubuntu 24.04").
  - `/proc/version`: `Linux version 6.18.5 (builder@sandboxing) (gcc (GCC)
    15.2.0 ...)` — a **custom Anthropic-built sandbox kernel**, and
    `/proc/cpuinfo` shows the `hypervisor` flag with virtio block devices
    (`vda..vde` in `/proc/partitions`) — i.e., a microVM-style guest, not a
    plain container.
  - `/proc/mounts`: root ext4 on `/dev/vda`; **read-only** mounts
    `/opt/claude-code` (`vdb`), `/opt/env-runner` (`vdc`), and squashfs
    `/mnt/skills/{public,examples}` — the harness and env-runner are injected
    outside the writable root.

### 2. What persists between sessions: the "environment cache" (filesystem snapshot)

Docs § Environment caching, verbatim:

> "The setup script runs the first time you start a session in an environment.
> After it completes, Anthropic snapshots the filesystem and reuses that
> snapshot as the starting point for later sessions. New sessions start with
> your dependencies, tools, and Docker images already on disk, and the setup
> script step is skipped."

Key rules extracted:

- **Persists:** anything the setup script writes to disk — installed packages,
  toolchains, **pulled Docker images** ("The pulled images are saved in the
  cached environment, so each new session has them on disk").
- **Does NOT persist:** running processes/containers ("The cache captures
  files, not running processes. Anything the setup script writes to disk
  carries over. Services or containers it starts don't"), and **mid-session
  installs** ("You can also ask Claude to install packages mid-session, but
  those installs don't carry over to other sessions").
- **Cache invalidation / rebuild triggers:** "The setup script runs again to
  rebuild the cache when you change the environment's setup script or allowed
  network hosts, and when the cache reaches its expiry after roughly **seven
  days**. Resuming an existing session never re-runs the setup script."
- **Cache-build time budget:** "Keep the script's total runtime under roughly
  **five minutes** so the environment cache can build." — a setup script that
  overruns forfeits caching; long downloads should move to a background
  SessionStart hook.
- The cache is fully managed: "You don't need to enable caching or manage
  snapshots yourself."
- **SessionStart-hook output is also captured by the snapshot.** Anthropic's
  built-in web-onboarding skill (read locally at
  `/root/.claude/skills/session-start-hook/SKILL.md:77`) states: "The container
  state gets cached after the hook completes, prefer dependency install methods
  that take advantage of that (i.e. prefer npm install over npm ci)". Hooks
  still *re-run* on every start/resume (docs: they "run each time a session
  starts or resumes, unlike setup scripts") — so hooks must be idempotent and
  fast-on-warm, but their installed files warm the next session.

Implication for this repo: a setup script (or idempotent SessionStart hook)
that installs python 3.14 + uv + mise + hk + pkl runs its full cost **once per
environment per ~7 days** (or per script/network-config edit), not per session.

### 3. Session/environment reclaim policy

- Docs § Troubleshooting → Environment expired, verbatim: "Cloud sessions stop
  after a period of inactivity and the underlying environment is reclaimed.
  From a local terminal, this surfaces as `Could not resume session ... its
  environment has expired. Creating a fresh session instead.` On the web, the
  session is marked expired in the session list." Recovery: "Reopen the session
  from claude.ai/code to provision a fresh environment with your conversation
  history restored."
- The inactivity window is **not documented numerically**. Community evidence:
  anthropics/claude-code#50197 ("Add expiration warnings before cloud session
  termination", opened 2026-04-17, closed as duplicate of #50177) reports
  "Cloud sessions ... currently terminate silently at their TTL with no advance
  warning" and cites a **~7-day session TTL**; at that time expired sessions
  "disappear[ed] entirely" with "all uncommitted session context ...
  unrecoverable" (https://github.com/anthropics/claude-code/issues/50197).
  Current docs (July 2026) describe the softer behavior (history restored,
  fresh environment) — the April behavior appears to have been improved, but
  **uncommitted working-tree state in a reclaimed VM is still gone**; only
  conversation history survives reclaim.
- Net model: three distinct lifetimes — (a) VM/working tree: per session,
  reclaimed on inactivity; (b) environment cache snapshot: ~7 days or until
  config change; (c) conversation history: retained by claude.ai across
  reclaim.

### 4. Docker inside web sessions: real dockerd in the VM; sibling containers are the officially recommended pattern

- Docs § Installed tools lists **"Docker | docker, dockerd, docker compose"**
  as pre-installed. § Run tests...: "Docker is available for running
  containerized services. Ask Claude to run `docker compose up` to start your
  project's services. Network access to pull images follows your environment's
  access level, and the Trusted defaults include Docker Hub and other common
  registries." The Trusted allowlist explicitly includes **`ghcr.io`**,
  `registry-1.docker.io`, `gcr.io`/`*.gcr.io`, `mcr.microsoft.com`,
  `public.ecr.aws` (docs § Default allowed domains) — so pulling this repo's
  GHCR image is *network-permitted* under default Trusted access.
- Large images: "If your images are large or slow to pull, add `docker compose
  pull` or `docker compose build` to your setup script. The pulled images are
  saved in the cached environment, so each new session has them on disk. The
  cache stores files only, not running processes, so Claude still starts the
  containers each session."
- **The sibling-container pattern is official guidance**, verbatim (docs,
  § Install dependencies with a SessionStart hook): "Replacing the base image
  with your own Docker image is **not yet supported**. Use a setup script to
  install what you need on top of the provided image, **or run your image as a
  container alongside Claude with `docker compose`**."
- This is dockerd running inside the per-session VM (docker-in-VM, not
  docker-socket-to-host and not classic DinD-in-container) — consistent with
  the microVM evidence in Finding 1.
- **Empirical (this session):** `/usr/bin/docker`, `/usr/bin/dockerd`,
  `/usr/bin/docker-proxy` all present (Glob); **no `/var/run/docker.sock`**
  exists — the daemon is not running by default and must be started per
  session (consistent with "cache stores files only, not running processes").
  Note: this particular research-container flavor may not have dockerd
  startable; not verified live because Bash is blocked in this session.
- **History / trust-weighting:** Docker support is recent.
  anthropics/claude-code#29515 ("[FEATURE] Docker support in Claude Code web
  environment", opened 2026-02-28, labels `area:claude-code-web`,
  `area:sandbox`, still open) requested it;
  anthropics/claude-code#53430 ("[BUG] Docker daemon not started on web
  environment", opened 2026-04-26, closed as not planned) reported docker CLI
  v29.3.1 present but dockerd unstartable (no root/privileges; attempts
  crashed the environment). The current docs page (updated ~2026-05-21 per
  search-result metadata, re-fetched live 2026-07-09) documents dockerd +
  compose as first-class with image caching — i.e., **working Docker landed
  roughly May 2026**, and April-era failure reports predate the current
  capability.

### 5. Resource ceilings vs. the ~38GB dotfiles-devcontainer image

- Docs § Resource limits: "approximate resource ceilings that may change over
  time: **4 vCPUs, 16 GB of RAM, 30 GB of disk**. Tasks requiring significantly
  more ... may fail or be terminated."
- **Empirical (this session):** `/proc/cpuinfo` = 4 × Intel Xeon @2.10GHz
  (**x86_64**, AVX-512/AMX flags — Sapphire-Rapids-class); `/proc/meminfo`
  MemTotal = 16,461,176 kB ≈ 16 GB — both match the docs. `/proc/partitions`
  shows `/dev/vda` (root) = 268,435,456 KiB-blocks = **256 GiB virtual disk**,
  i.e., the 30 GB figure is a policy/quota ceiling on a thin-provisioned
  device, not the device size. Do not design against the undocumented
  headroom: the docs reserve the right to terminate workloads exceeding the
  stated ceilings.
- **Consequence:** pulling `ghcr.io/ray-manaloto/dotfiles-devcontainer:dev`
  (~38 GB; repo baseline `.omc/research/research-20260709-r2-inventory/
  report.md:70-96` and AGENTS.md "verify-container-latest" notes) **exceeds the
  documented 30 GB disk ceiling on its own**, before the repo clone, base
  toolchain, and build scratch space. Even though ghcr.io is allowlisted and
  docker image caching exists, the current image cannot be the
  sibling-container payload as-is. A slimmed image (roughly ≤ ~15-20 GB
  uncompressed, leaving headroom for the OS image, repo, and caches) would fit
  the documented envelope and would be **snapshot-cached across sessions**,
  amortizing the pull to once per ~7 days per environment.
- Arch note: the web VM is x86_64 (empirical), so the repo's AMD64-only image
  constraint (R3) is *compatible* — size, not architecture, is the blocker.

### 6. Practical persistence matrix for this repo

| Item | Persists across sessions? | Mechanism / source |
|---|---|---|
| Repo working tree / uncommitted edits | **No** — fresh clone per session; lost on reclaim | docs § cloud environment; § Environment expired |
| Conversation history | Yes (survives reclaim; reopen provisions fresh env) | docs § Environment expired |
| Setup-script-installed tools (apt, mise, uv, python) | Yes, via env cache snapshot (~7d, invalidated by script/network edits) | docs § Environment caching |
| SessionStart-hook-installed files | Yes (snapshot captures them); hook itself re-runs every start/resume | skill `/root/.claude/skills/session-start-hook/SKILL.md:77`; docs § Setup scripts vs SessionStart hooks |
| Docker images pulled in setup script | Yes ("saved in the cached environment") | docs § Run tests, start services |
| Mid-session installs (asked of Claude) | **No** | docs § Run tests, start services |
| Running services / containers | **No** — files only, restart each session | docs § Environment caching |
| Env vars | Yes, stored in environment config (visible to env editors; no secrets store yet) | docs § What's available |

---

## Uncertainties / gaps

1. **Inactivity window before VM reclaim is undocumented** — community evidence
   says ~7-day session TTL (#50197/#50177, April 2026), but the current
   inactivity threshold and whether it changed since is unverified.
2. **Environment-cache size limit is unstated.** Whether the snapshot itself
   is capped below the 30 GB disk ceiling (e.g., whether a 20 GB docker image
   layer survives snapshotting) is not documented; only "large or slow to
   pull" images are described as cacheable.
3. **30 GB disk enforcement mechanism unknown.** The empirical block device is
   256 GiB; whether a quota hard-fails writes at ~30 GB, or enforcement is
   monitoring-based termination, is unverified (this session could not run
   `df`/`dd` probes — Bash blocked).
4. **dockerd functionality was not live-verified** in this session (binaries
   present, no socket; Bash blocked). Docs + May-2026 update strongly indicate
   it works in standard web sessions, but a smoke test (`docker compose up` of
   a small image, then confirm the image survives into a second session) is
   the required next probe.
5. **Whether the environment snapshot is shared by concurrently running
   parallel sessions** of the same environment (docs say "later sessions"
   start from it; concurrent-start semantics unstated).
6. **#53430 closure reason** ("closed as not planned") is ambiguous — likely
   mooted by the May 2026 docker rollout, but no official comment confirms.
7. This session's container flavor (research/Cowork execution) may differ in
   minor ways from a standard claude.ai/code web session (e.g., the read-only
   `/opt/env-runner` mount, agent HTTPS proxy with custom CA at
   `/root/.ccr/ca-bundle.crt`); the CPU/RAM/OS/kernel/docker-binary facts are
   still the same Anthropic sandbox substrate.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — issues #29515, #53430, #50197 (docker in web env, daemon startup, session TTL) and CHANGELOG.md scan for cloud-session entries.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — repo baseline facts (image size ~38GB, AMD64 constraint) from the working tree and `.omc/research/research-20260709-r2-inventory/report.md`.
