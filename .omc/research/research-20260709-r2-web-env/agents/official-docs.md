# Run A / Angle 1 — Official docs full review: Claude Code on the web / cloud execution environment

Agent: official-docs (research analyst). Date: 2026-07-09.
Sources: the full `code.claude.com/docs` cloud page set, fetched as `.md` per the mintlify per-page rule. Primary pages:

- https://code.claude.com/docs/en/claude-code-on-the-web (main reference; fetched in full, ~57KB)
- https://code.claude.com/docs/en/web-quickstart
- https://code.claude.com/docs/en/hooks (SessionStart section)
- https://code.claude.com/docs/en/routines
- https://code.claude.com/docs/en/sessions
- https://code.claude.com/docs/en/env-vars
- https://code.claude.com/docs/llms.txt (index; confirmed the sibling-page set: web-quickstart, ultraplan, sessions, remote-control, routines, scheduled-tasks, channels, sandbox-environments, devcontainer, network-config, env-vars, settings)

All quotes below are verbatim from those pages as of 2026-07-09.

---

## Findings

### 1. Product status and eligibility

- "Claude Code on the web is in research preview for Pro, Max, and Team users, and for Enterprise users with premium seats or Chat + Claude Code seats." (claude-code-on-the-web)
- "Organizations with Zero Data Retention enabled can't use `/web-setup` or other cloud session features."
- "There is no separate compute charge for the cloud VM" — usage draws down the account's shared rate limits.
- Web sessions offer only "Accept edits, Plan, Auto" permission modes; "Cloud sessions don't offer Manual or Bypass permissions." (web-quickstart comparison table + Start-a-task step 2)

### 2. The environment: base image, ownership, resources

- **Per-session fresh VM, Anthropic-owned base**: "Each session runs in a fresh Anthropic-managed VM with your repository cloned." The OS is Ubuntu 24.04 and setup scripts run as root: "Scripts run as root on Ubuntu 24.04, so `apt install` and most language package managers work." (claude-code-on-the-web §Setup scripts)
- **Custom base image is explicitly NOT supported (the single most load-bearing doc quote for the one-image goal)**: "Replacing the base image with your own Docker image is not yet supported. Use a setup script to install what you need on top of the provided image, or run your image as a container alongside Claude with `docker compose`." (claude-code-on-the-web, end of §Setup scripts / SessionStart hooks section). The "not **yet**" is the only roadmap signal in the docs.
- **Resource limits** (§Resource limits): "Cloud sessions run with approximate resource ceilings that may change over time: 4 vCPUs / 16 GB of RAM / 30 GB of disk. Tasks requiring significantly more memory ... may fail or be terminated. For workloads beyond these limits, use Remote Control to run Claude Code on your own hardware."
  - Direct consequence for this repo: the ~38GB `ghcr.io/ray-manaloto/dotfiles-devcontainer:dev` image **cannot fit on the documented 30GB disk**, even though Docker + ghcr.io access are both available (see §5, §6).
- **Pre-installed toolchain** (§Installed tools): "Python 3.x with pip, poetry, **uv**, black, mypy, pytest, ruff"; Node 20/21/22 via nvm (npm, yarn, pnpm, bun¹); Ruby 3.1–3.3; PHP 8.4; OpenJDK 21; Go latest; Rust; "**C/C++**: GCC, Clang, cmake, ninja, conan"; "**Docker**: docker, dockerd, docker compose"; PostgreSQL 16, Redis 7.0; git, jq, yq, ripgrep, tmux, vim, nano. "¹ Bun is installed but has known proxy compatibility issues for package fetching."
  - "For exact versions, ask Claude to run `check-tools` in a cloud session. This command only exists in cloud sessions." — the only documented way to enumerate exact versions; no image tag/digest is published.
  - `gh` is NOT pre-installed: "The `gh` CLI isn't pre-installed." Documented fix: `apt update && apt install -y gh` in the setup script + a `GH_TOKEN` env var. mise, hk, pkl are (unsurprisingly) not in the pre-installed list either — they must come from a setup script or SessionStart hook.

### 3. What carries over into a cloud session (config surface)

From the availability table (§What's available in cloud sessions):

- **Yes (part of the clone)**: repo `CLAUDE.md`, repo `.claude/settings.json` hooks, repo `.mcp.json`, repo `.claude/rules/`, `.claude/skills|agents|commands/`, plugins declared in repo `.claude/settings.json` (installed at session start; needs network to the marketplace), org server-managed settings (fetched from Anthropic servers).
- **No**: user `~/.claude/CLAUDE.md`, user-level skills/agents/commands, user-scoped `enabledPlugins`, MCP servers registered via the Claude CLI's user-scoped `mcp add` subcommand ("Those write to your local user config, not the repo. Declare the server in `.mcp.json` instead" — literal command elided here for the repo's no_mcp_registration guard), static API tokens/credentials, interactive auth (AWS SSO).
- **Secrets**: "A dedicated secrets store is not yet available. Both environment variables and setup scripts are stored in the environment configuration, visible to anyone who can edit that environment." (relevant to the Doppler question: a `DOPPLER_TOKEN` would have to live as a plain environment variable in the environment config.)
- Environment variables use `.env` format, one `KEY=value` per line, "Don't wrap values in quotes, since quotes are stored as part of the value."
- Environments are managed in the web UI; `/remote-env` in the CLI only *selects* the default environment.

### 4. Setup scripts vs SessionStart hooks (the two customization hooks)

- **Setup script** (per cloud environment, configured in the web UI): "A setup script is a Bash script that runs when a new cloud session starts, before Claude Code launches." Runs as root. "If the script exits non-zero, the session fails to start." "Keep the script's total runtime under roughly five minutes so the environment cache can build."
- **Environment caching** (§Environment caching): "The setup script runs the first time you start a session in an environment. After it completes, Anthropic snapshots the filesystem and reuses that snapshot as the starting point for later sessions. New sessions start with your dependencies, tools, and Docker images already on disk, and the setup script step is skipped." — "The cache captures files, not running processes." — "The setup script runs again to rebuild the cache when you change the environment's setup script or allowed network hosts, and when the cache reaches its expiry after roughly seven days. Resuming an existing session never re-runs the setup script."
  - So a mise/hk/pkl/uv toolchain installed by a setup script is effectively "baked" into a 7-day filesystem snapshot — the closest thing to a custom image the platform currently offers.
- **SessionStart hooks** (repo `.claude/settings.json`, run in cloud AND local): "Runs ... After Claude Code launches, on every session including resumed." Detection: "The `CLAUDE_CODE_REMOTE` environment variable is set to `true` in cloud sessions, so you can use it to skip local execution." Persist env for later Bash commands by appending `export` lines to `$CLAUDE_ENV_FILE` (hooks.md: "Any variables written to this file will be available in all subsequent Bash commands"). Default SessionStart timeout: 600s (hooks.md).
- Documented limitations of SessionStart hooks in the cloud (verbatim list): "No cloud-only scoping" / "Requires network access ... If your environment uses **None** network access, these hooks fail" / "Proxy compatibility: all outbound traffic passes through a security proxy. Some package managers don't work correctly with this proxy. Bun is a known example." / "Adds startup latency: hooks run each time a session starts or resumes, unlike setup scripts which benefit from environment caching."
- Hook failure semantics (hooks.md): SessionStart exit code 2 is NON-blocking — "the exit code 2 stderr renders in the transcript as a `<hook name> hook error` notice ... Claude doesn't see it, and the session or subagent proceeds." **PreToolUse exit code 2 BLOCKS the tool call** ("Blocks the tool call"). This is the documented mechanism behind this repo's current web-session failure: `.claude/settings.json` wires every Bash call through `uv run --project python dotfiles-setup hook pretooluse`; with no Python ≥3.14 present the guard cannot run and every Bash call is blocked (observed fail-closed in the current session; see Uncertainties for the exit-code nuance).
- Quickstart troubleshooting adds the operational pattern: for >5-minute installs, "Move the largest downloads out of the setup script and into a SessionStart hook that launches them in the background", run independent installs "in parallel with `&` and a final `wait`", debug with `set -x`, soften non-critical steps with `|| true`.

### 5. Network access model

- Four levels per environment (§Access levels): **None** ("No outbound network access"), **Trusted** (default; "Allowlisted domains only: package registries, GitHub, cloud SDKs"), **Full** ("Any domain"), **Custom** ("Your own allowlist, optionally including the defaults" — one domain per line, `*.` wildcards, checkbox "Also include default list of common package managers").
- **Security proxy** (§Security proxy): "Environments run behind an HTTP/HTTPS network proxy for security and abuse prevention purposes. All outbound internet traffic passes through this proxy" (malicious-request protection, rate limiting, content filtering, "A DNS-level audit trail of requested hostnames"). Blocked hosts fail with "`403` and `x-deny-reason: host_not_allowed`" (routines.md §Environments and network access).
- **GitHub proxy** is separate and independent of the access level (§GitHub proxy): "all GitHub operations go through a dedicated proxy service ... the git client uses a scoped credential inside the sandbox, which the proxy verifies and translates to your actual GitHub authentication token"; it "Restricts git push operations to the current working branch for safety". Tokens never enter the container.
- MCP connector traffic "is routed through Anthropic's servers, so the connectors you enable ... work without adding their hosts to Allowed domains."
- **Trusted default allowlist — repo-relevant mapping** (full list captured from §Default allowed domains):
  - PRESENT: `github.com`, `api.github.com`, `codeload.github.com`, `raw.githubusercontent.com`, `objects.githubusercontent.com`, `release-assets.githubusercontent.com` → **GitHub-release-based mise backends (aqua, ubi, github releases) and pkl/hk release downloads are reachable**; `registry.npmjs.org` (npm backend); `pypi.org` + `files.pythonhosted.org` (pipx/uv/pip); `crates.io` + `static.crates.io` (cargo); `repo.anaconda.com` + `conda.anaconda.org` (conda/rattler backend); `ghcr.io`, `registry-1.docker.io`, `gcr.io`, `*.gcr.io`, `mcr.microsoft.com`, `public.ecr.aws` (container pulls incl. this repo's ghcr image); `archive.ubuntu.com`/`security.ubuntu.com`/`ppa.launchpad.net` (apt); `proxy.golang.org`, `rustup.rs`, `dl.k8s.io`, `releases.hashicorp.com`, `*.nixos.org`, `json.schemastore.org`, `*.modelcontextprotocol.io`, `*.amazonaws.com`, `*.googleapis.com`, sentry/datadog/statsig/honeycomb.
  - ABSENT (needs Custom allowlist or an alternate install path): `mise.run` / `mise.jdx.dev` (the curl installer + mise docs), `astral.sh` (uv installer — moot, uv is pre-installed), `api.doppler.com` / `cli.doppler.com` (Doppler API + CLI install), `hk.jdx.dev` / `pkl-lang.org` (docs only), any private registries.
- Setup scripts / SessionStart installs "fail to install packages if your environment uses **None** network access."

### 6. Docker inside web sessions

- Docker is a first-class documented capability: "**Docker**: docker, dockerd, docker compose" are installed (§Installed tools), i.e. a real daemon *inside* the VM (root), not a sibling-container arrangement — no privileged-mode caveats are documented.
- "Docker is available for running containerized services. Ask Claude to run `docker compose up` to start your project's services. Network access to pull images follows your environment's access level, and the Trusted defaults include Docker Hub and other common registries." (§Run tests, start services, and add packages)
- "If your images are large or slow to pull, add `docker compose pull` or `docker compose build` to your setup script. The pulled images are saved in the cached environment, so each new session has them on disk. The cache stores files only, not running processes."
- The docs even name running your own image as the sanctioned substitute for custom base images: "run your image as a container alongside Claude with `docker compose`."
- Constraint for this repo: pulling the ~38GB devcontainer image collides with BOTH the ~5-minute setup-script budget ("Heavy steps such as pulling large Docker images ... often push the total over the limit" — web-quickstart troubleshooting) AND the ~30GB disk ceiling. A dramatically slimmed image (or the runtime tier only) would be required.

### 7. Session lifecycle, persistence, reclaim

- Sessions run detached: "Closing the tab or navigating away doesn't stop the session. It continues running in the background until Claude finishes the current task, then idles." (web-quickstart troubleshooting)
- Reclaim: "Cloud sessions stop after a period of inactivity and the underlying environment is reclaimed. From a local terminal, this surfaces as `Could not resume session ... its environment has expired. Creating a fresh session instead.` ... Reopen the session from claude.ai/code to provision a fresh environment with your conversation history restored." (§Troubleshooting — Environment expired). The inactivity period is NOT quantified anywhere in the docs.
- What survives a reclaim: conversation history (restored) + the environment cache snapshot (setup-script output, ≤ ~7 days). Mid-session ad-hoc installs do not persist: "You can also ask Claude to install packages mid-session, but those installs don't carry over to other sessions."
- Cloud-supported context commands: `/compact` yes, `/context` yes, `/clear` no ("Start a new session from the sidebar instead"). Auto-compaction tunable via `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` env var in the environment config. Agent teams opt-in via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
- Session traceability: `CLAUDE_CODE_REMOTE_SESSION_ID` env var (cse_ → session_ prefix conversion documented); since v2.1.179 web commits get a `Claude-Session: <url>` trailer; `attribution.sessionUrl: false` (v2.1.182+) disables it.

### 8. GitHub integration model

- Two auth paths: the **Claude GitHub App** (browser onboarding; required for Auto-fix PR webhooks) or **`/web-setup`** (syncs the local `gh` CLI token to the Claude account; creates a default environment with "Trusted network access and no setup script").
- Scope warning: "a cloud session can access any repository the connecting GitHub account can see, not just the repositories the Claude GitHub App is installed on. App installation ... is not a session-level access control."
- Built-in GitHub tools (read issues, list PRs, fetch diffs, post comments) go through the GitHub proxy — no `gh` needed for those.
- Session start flow (web-quickstart §How sessions run): 1. clone + setup script → 2. configure network → 3. work → 4. push branch. "The session doesn't close when the branch is pushed."
- `claude --cloud` from the terminal creates a cloud session cloning "your current directory's GitHub remote at your current branch" (push first); `--teleport`/`/teleport` pulls a cloud session down (requires clean git state, same repo, branch pushed, same claude.ai account). Non-GitHub repos can be sent as a ≤100MB git bundle but "can't push results back to the remote".
- Routines (schedule/API/GitHub-event triggers) run as "full Claude Code cloud sessions: there is no permission-mode picker and no approval prompts during a run", inherit a cloud environment's network policy, default to `claude/`-prefixed branch pushes only, and have a per-account daily run cap.

### 9. Documented restriction set (consolidated)

1. Base image fixed, Anthropic-managed ("Replacing the base image with your own Docker image is not yet supported").
2. ~4 vCPU / 16GB RAM / 30GB disk, "approximate ... may change over time".
3. Setup script ≈5-minute budget; non-zero exit blocks session start.
4. Environment cache ≈7-day expiry; invalidated by setup-script or allowed-host edits.
5. All outbound traffic through the security proxy; some package managers break (bun named); blocked hosts → 403 `x-deny-reason: host_not_allowed`.
6. Git push restricted to the current working branch (GitHub proxy); routines restricted to `claude/*` branches unless "Allow unrestricted branch pushes".
7. No user-level config carryover (~/.claude/*); repo-committed config only + server-managed settings.
8. No secrets store; environment env vars visible to environment editors.
9. No Manual/Bypass permission modes; `/clear` unavailable; terminal-only commands unavailable.
10. GitHub required for clone/PR (GHES supported on Team/Enterprise; GitLab/Bitbucket only via one-way bundle).
11. Shared rate limits; org IP-allowlisting breaks cloud sessions entirely.
12. Sessions expire on inactivity (unquantified); mid-session installs don't persist.
13. ZDR organizations excluded from all cloud-session features.

### 10. What this means for a "web-compatible" setup for THIS repo (doc-grounded)

- **uv is pre-installed** and `pypi.org`/`files.pythonhosted.org`/GitHub releases are on the Trusted allowlist, so `uv python install 3.14` (python-build-standalone from GitHub releases) + `uv sync --project python` is reachable under default Trusted network — no Custom policy required. This directly addresses the current failure (hook guard needs Python ≥3.14).
- **mise cannot use `curl https://mise.run`** under Trusted (`mise.run` absent from the allowlist); it CAN be installed from GitHub releases (`github.com` + `release-assets.githubusercontent.com` present), or via a Custom policy adding `mise.run`/`mise.jdx.dev`. Once mise runs, its aqua/ubi/github/npm/pipx/cargo/conda backends all resolve against Trusted-allowlisted hosts.
- **Doppler is unreachable under Trusted** (`api.doppler.com` absent) → Custom allowlist entry or env-var-based secrets (with the documented visibility caveat).
- The sanctioned "image-like" mechanism is **setup script + 7-day filesystem snapshot**, and optionally the heavy image **as a docker-compose sidecar** — but the 38GB image exceeds the 30GB disk, so only a slimmed variant could ride that path.
- SessionStart hook with `CLAUDE_CODE_REMOTE=true` gating + `$CLAUDE_ENV_FILE` exports (PATH to mise shims, MISE_* vars) is the documented per-repo mechanism that runs on every session including resume — the right place for `mise install` fast-path checks, while the environment setup script does the one-time heavy install.

## Uncertainties / gaps

- **Base image identity**: docs never publish an image name, tag, digest, or Dockerfile; only "Ubuntu 24.04" and the category-level tool table. Exact versions only discoverable in-session via `check-tools`. CPU architecture is not documented (x86_64 implied by the toolchain, unverified).
- **PreToolUse hook that fails to START** (command not found / interpreter missing, as in this repo's `uv run ... hook pretooluse` with no Python 3.14): the docs specify exit-code-2 blocking semantics, but not the behavior for a hook whose command errors out entirely. Observed behavior in the current remote session is fail-closed (every Bash call blocked); the docs neither confirm nor deny this.
- **Inactivity window before environment reclaim** is not quantified ("a period of inactivity").
- **Filesystem state on resume-after-reclaim**: docs promise "conversation history restored" on a fresh environment; they do not state whether uncommitted working-tree changes are preserved (the fresh-clone + cache-snapshot model implies they are lost, but this is inference).
- **Proxy env vars inside the session** (`HTTP_PROXY`/`HTTPS_PROXY` names, CA bundle path) are not documented on the env-vars page; the security proxy is described only behaviorally. (Empirically, this session has a pre-configured `HTTPS_PROXY` + CA bundle, but that is observation, not documentation.)
- **Disk quota semantics**: whether the 30GB is total disk, free space after the base image, or per-workspace is not specified; whether docker image layers count against it is implied (cached images "on disk") but not spelled out.
- **Roadmap for custom base images**: the docs' only signal is the word "yet". Community/issue-tracker signals (e.g. anthropics/claude-code#29515) are covered by a sibling angle, not verified here.
- The `sandbox-environments` and `devcontainer` pages listed in llms.txt concern local-CLI sandboxing/devcontainers, not the web product; they were not fetched in depth for this angle.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — its official product documentation (code.claude.com/docs) is the sole source set for this angle; repo source/issues not read here.
