# Run A, angle 2 — Toolchain compatibility (mise / hk / pkl / uv / python 3.14) in Claude Code web sessions

Date: 2026-07-09. Researcher: tool-compat agent (remote container; Bash unavailable — all
probes via WebFetch/WebSearch/GitHub MCP/local cache greps).

Primary sources: `https://code.claude.com/docs/en/claude-code-on-the-web` (fetched
2026-07-09, current), `https://code.claude.com/docs/en/hooks` (fetched 2026-07-09),
anthropics/claude-code issues, GitHub code-search corpus, local mintlify cache
(`docs/research/mintlify-cache/jdx/{mise,hk}/`).

---

## Findings

### F1. The cloud environment: Ubuntu 24.04, root setup scripts, uv preinstalled — mise/hk/pkl are NOT

- "Scripts run as root on Ubuntu 24.04" — setup-script section of
  [claude-code-on-the-web](https://code.claude.com/docs/en/claude-code-on-the-web).
  Base arch is x86_64 (confirmed independently by
  [anthropics/claude-code#55000](https://github.com/anthropics/claude-code/issues/55000),
  2026-04-30: "Claude Code web sandbox, Ubuntu 24.04 LTS x86_64").
- Installed-tools table (same page): **Python** "Python 3.x with pip, poetry, **uv**,
  black, mypy, pytest, ruff"; Node 20/21/22 via nvm; GCC/Clang/cmake/ninja/conan;
  **docker, dockerd, docker compose**; git/jq/yq/ripgrep/tmux. **mise, hk, pkl are not
  in the image.** Exact versions: "ask Claude to run `check-tools` in a cloud session".
- Resource ceilings: "4 vCPUs, 16 GB of RAM, 30 GB of disk" (may change over time).
- **Custom base image is explicitly not supported yet**: "Replacing the base image with
  your own Docker image is not yet supported. Use a setup script to install what you
  need on top of the provided image, or run your image as a container alongside Claude
  with `docker compose`." → for this angle, the toolchain must be layered on Anthropic's
  image via setup script / SessionStart hook.
- **Environment caching**: after the setup script completes once, "Anthropic snapshots
  the filesystem and reuses that snapshot as the starting point for later sessions...
  the setup script step is skipped"; cache rebuilds on script/allowlist change or after
  "roughly seven days". Keep setup script "under roughly five minutes so the environment
  cache can build". Cache stores files, not processes.

### F2. All five toolchain components are installable under the default **Trusted** network policy — via the GitHub-releases path

Trusted allowlist (same docs page) includes `github.com`, `api.github.com`,
`codeload.github.com`, `objects.githubusercontent.com`,
`release-assets.githubusercontent.com`, `raw.githubusercontent.com`, `pypi.org`,
`files.pythonhosted.org`, `registry.npmjs.org`, `ghcr.io`, `repo.anaconda.com`,
`conda.anaconda.org`, `*.amazonaws.com`, `download.docker.com`, `archive.ubuntu.com`.

Per component (repo pins from `.config/mise/conf.d/shared.toml:20-40`):

| Component | Pin | Install path in web session | Allowlisted? |
|---|---|---|---|
| **mise** | (installer) | `curl -L https://github.com/jdx/mise/releases/download/v<V>/mise-v<V>-linux-x64` (documented GitHub-releases method, mise cache `llms-full.txt:4262-4267`) | Yes (github.com + release assets) |
| **hk** | 1.50.0 | via `mise install` — registry backend resolves to jdx/hk GitHub releases; "recommended way to install hk is with mise" (hk cache `llms-full.txt:3689-3708`); aqua registry metadata is **compiled into the mise binary** (mise cache `llms-full.txt:1838`), no extra fetch | Yes |
| **pkl** | 0.31.1 | via mise → apple/pkl GitHub release binaries. pklr needs no install — embedded in hk since 1.49 (`mise.toml:69-72`, AGENTS.md "Split hk Architecture") | Yes |
| **python** | 3.14.6 | mise core python: "By default, mise will download precompiled binaries for python" from `astral-sh/python-build-standalone` ([mise.jdx.dev/lang/python](https://mise.jdx.dev/lang/python.html)) = GitHub releases. Alternative: preinstalled `uv python install 3.14` (same host) | Yes |
| **uv** | 0.11.27 | **preinstalled** in the cloud image (version unknown/older); exact pin via mise → astral-sh/uv GitHub releases | Yes |

Backends for the rest of the lint toolset: `pipx:*` → pypi.org (allowed), `npm:*` →
registry.npmjs.org (allowed), `aqua:`/`github:`/core → GitHub releases (allowed),
aws-cli → `*.amazonaws.com` (allowed), docker-cli → download.docker.com (allowed).

**Domains that are NOT allowlisted under Trusted (avoid or add via Custom):**

- `mise.run` and `mise.jdx.dev` — the canonical `curl https://mise.run | sh` installer
  is NOT on the documented allowlist, and the install script downloads the *current*
  version from `https://mise.jdx.dev/v${version}/...` (verified by fetching
  https://mise.run on 2026-07-09; only non-current versions come from GitHub releases).
  → In a web session, install mise by direct GitHub-release URL, or add
  `mise.run` + `mise.jdx.dev` to a Custom allowlist.
- `astral.sh` — confirmed blocked: "`curl -LsSf https://astral.sh/uv/install.sh | sh`
  → `curl: (22) The requested URL returned error: 403` — astral.sh is not on the
  default sandbox network allowlist"
  ([anthropics/claude-code#52963](https://github.com/anthropics/claude-code/issues/52963),
  2026-04-24). Not needed here (uv preinstalled + mise-pinned), but it calibrates the
  expectation: any non-listed domain 403s under Trusted.
- Doppler API — not allowlisted; irrelevant to the lint/pytest gates (Doppler is
  devcontainer-only per `.devcontainer/devcontainer.json:198`).

### F3. The mise-in-web-session SessionStart hook is an established real-world pattern (53 code hits)

GitHub code search `"CLAUDE_CODE_REMOTE" "mise install"` → **53 files**
(2026-07-09). The canonical shape across the corpus:

1. `.claude/hooks/session-start.sh`, gated `if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then exit 0; fi`
2. install mise if absent, then `mise trust && mise install`
3. persist PATH (`~/.local/bin` + `~/.local/share/mise/shims`) via `$CLAUDE_ENV_FILE`

Exemplars (all fetched/inspected 2026-07-09):

- [jonpulsifer/infra](https://github.com/jonpulsifer/infra) `.claude/hooks/session-start.sh` —
  installs mise (via mise.run — implies a widened network policy), installs a **curated
  subset** of tools ("The heavier CLIs ... are intentionally skipped", AGENTS.md), and
  appends to `$CLAUDE_ENV_FILE`:
  `PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:$PATH"`, `MISE_YES=1`,
  `MISE_TASK_RUN_AUTO_INSTALL=0`.
- [datenknoten/freundebuch](https://github.com/datenknoten/freundebuch) and
  [joeblew999/vm-uncloud](https://github.com/joeblew999/vm-uncloud)
  `.claude/hooks/session-start.sh` — both document the dominant failure mode: mise's
  `github:`/`aqua:` version lookups "hit GitHub's ANONYMOUS API rate limit (HTTP 403)
  without a token — the exact failure seen in web sessions"; fix is a `GITHUB_TOKEN`
  env secret in the environment config.
- [hco/dependency-dir-analyzer](https://github.com/hco/dependency-dir-analyzer)
  CLAUDE.md — "installs mise if absent, runs `mise install`, and puts the toolchain on
  PATH so tests and linters work immediately. It is a no-op locally."
- [wado-lang/wado](https://github.com/wado-lang/wado) `.claude/hooks/mise-setup.sh`,
  [entireio/cli](https://github.com/entireio/cli) `.claude/scripts/remote-setup.sh`,
  [StoDevX/AAO-React-Native](https://github.com/StoDevX/AAO-React-Native) (inline
  settings.json command `mise trust && mise settings experimental=true && mise install`),
  [richardthe3rd/cambridge-beer-festival-app](https://github.com/richardthe3rd/cambridge-beer-festival-app)
  (async hook emitting `{"async": true, "asyncTimeout": ...}`).

**Failure modes observed in the wild:**

- **GitHub API anonymous rate limit** (60 req/hr/IP; egress IPs shared across users).
  Officially confirmed by
  [anthropics/claude-code#52963](https://github.com/anthropics/claude-code/issues/52963)
  (setup script `uv self update` failed 5× consecutively; closed `not_planned`; the
  working fix from its workaround table: "Set `GITHUB_TOKEN` in Custom Environment
  variables — Works — the rate limit jumps from 60/hr to 5,000/hr"). mise's token
  precedence: `MISE_GITHUB_TOKEN` > `GITHUB_TOKEN` (mise cache `llms-full.txt:3998-4026`).
- **TLS-inspecting egress proxy**: all outbound HTTPS passes a MITM proxy
  (`O=Anthropic; CN=sandbox-egress-production TLS Inspection CA`,
  [#55000](https://github.com/anthropics/claude-code/issues/55000)). Clients with
  unusual TLS stacks are refused (Erlang `:httpc` → 502 on every host; Bun has
  documented "proxy compatibility issues" in the official docs). **mise and uv
  (rustls-based) demonstrably work through it** — the 53-repo corpus and #52963's
  successful `GITHUB_TOKEN` path are the evidence; no report of a mise/uv TLS failure
  in web sessions was found.

### F4. Why THIS repo currently fails in web sessions — bootstrap ordering, not incompatibility

- `.claude/settings.json:8-20` wires a **PreToolUse hook on every Bash call**:
  `uv run --project python dotfiles-setup hook pretooluse` with `"timeout": 20`.
- `python/pyproject.toml:5`: `requires-python = ">=3.14"`; the cloud image ships
  generic "Python 3.x" and no mise, so on the first Bash call uv must download
  CPython 3.14 (~tens of MB from python-build-standalone), create the venv, and
  install pydantic + the package — far beyond the 20 s hook timeout even when the
  network path works.
- Observed behavior in the current remote execution container: "Bash entirely blocked:
  the PreToolUse hook ... cannot start — no Python ≥3.14 in the container — and the
  harness fails closed"
  (`docs/research/runs/research-20260709-r2-inventory/report.md:118-124`). Mechanism
  (inferred, consistent with uv semantics): uv exits with its **own-error code 2** when
  it cannot provision the interpreter, and PreToolUse **exit 2 = deny the tool call**,
  so every Bash invocation is denied.
- Nothing in the `mise run lint` / `uv run pytest` toolchain is unreachable under
  Trusted (F2) — the failure is purely that the guard's interpreter isn't provisioned
  before the first Bash call.

### F5. The fix: pre-warm via SessionStart hook (repo) + environment setup script (cloud env)

Mechanics (from [hooks docs](https://code.claude.com/docs/en/hooks) and the web docs):

- **Setup script** (cloud environment config): runs as root before Claude Code
  launches; result is snapshot-cached (~7 days); keep <5 min; needs Trusted+ network.
- **SessionStart hook** (repo `.claude/settings.json`): runs after Claude Code
  launches, on every startup/resume; **default timeout 600 s** (vs PreToolUse's
  configured 20 s); can persist env via `$CLAUDE_ENV_FILE` ("Any variables written to
  this file will be available in all subsequent Bash commands"); `CLAUDE_CODE_REMOTE`
  is `"true"` only in cloud sessions. SessionStart hooks are executed directly by the
  harness — they are **not gated by the PreToolUse Bash guard** (PreToolUse matches
  tool calls only), so the hook can run even while Bash is "blocked".
- Anthropic ships a first-party **startup-hook skill** (present in this remote
  container at `/root/.claude/skills/session-start-hook/SKILL.md`, name
  `startup-hook-skill`) prescribing exactly this workflow: analyze manifests → write
  `.claude/hooks/session-start.sh` → register in settings → validate lint + one test →
  commit. It documents async mode (`echo '{"async": true, "asyncTimeout": 300000}'`
  on stdout) and notes "The container state gets cached after the hook completes".

**Minimal setup that makes `mise run lint`, `uv run --project python pytest`, and
`dotfiles-setup verify run` work** (draft; MISE_V = current mise version):

```bash
#!/bin/bash
# .claude/hooks/session-start.sh — web-only toolchain bootstrap
set -euo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0

export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:$PATH"
mkdir -p "$HOME/.local/bin"

# 1. mise — direct GitHub-release download (mise.run/mise.jdx.dev are NOT on the
#    Trusted allowlist; github.com + release assets are).
if ! command -v mise >/dev/null 2>&1; then
  curl -fsSL "https://github.com/jdx/mise/releases/download/v${MISE_V}/mise-v${MISE_V}-linux-x64" \
    -o "$HOME/.local/bin/mise" && chmod +x "$HOME/.local/bin/mise"
fi

# 2. Pinned toolchain: shared.toml (hk 1.50.0, pkl 0.31.1, python 3.14.6,
#    uv 0.11.27, all linters) + root mise.toml host tools. Needs GITHUB_TOKEN
#    env var in the cloud environment config to avoid anonymous API 403s.
mise trust && mise install || {
  echo "warn: mise install incomplete — likely api.github.com anonymous rate" >&2
  echo "limit; set GITHUB_TOKEN in the environment variables and retry." >&2
}

# 3. Pre-warm the venv so the 20s PreToolUse hook guard succeeds on first call.
uv sync --project python

# 4. Persist PATH for all subsequent Bash commands.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo 'export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:$PATH"' >> "$CLAUDE_ENV_FILE"
fi
exit 0
```

Registered in `.claude/settings.json` under `hooks.SessionStart` with matcher
`startup|resume` (per the [official example](https://code.claude.com/docs/en/claude-code-on-the-web#install-dependencies-with-a-sessionstart-hook)).
Additionally put the same body (minus the `CLAUDE_CODE_REMOTE` gate and
`CLAUDE_ENV_FILE` write) in the **environment setup script** so the ~7-day filesystem
snapshot carries the installed toolchain and per-session hook runs become no-op-fast.
Set `GITHUB_TOKEN` (read-only PAT) in the environment variables — with the caveat from
the web docs that environment config values are "visible to anyone who can edit that
environment".

### F6. Sizing and scope caveats for this repo's toolset

- The **full** root `mise.toml` is ~40 host tools including `npm:renovate` (~354 MB,
  `mise.toml:16`), `aws-cli`, `azure-cli`, `colima`, `lima`, `opencode` — a complete
  `mise install` will likely exceed the 5-minute setup-script cache window without
  parallelization, and adds no value to web sessions. The lint gate strictly needs the
  20 shared.toml tools plus the hk-step host tools (editorconfig-checker, agnix,
  zizmor, markdownlint-cli2, rumdl, biome, npm:renovate for
  `renovate-config-validator`, ast-grep). A web-scoped trim (e.g. `mise.web.toml` via
  `MISE_ENV=web`, or a curated `mise install tool1 tool2 ...` list à la
  jonpulsifer/infra) is the pragmatic option; the snapshot cache makes even the full
  set tolerable if installed via setup script rather than per-session hook.
- `mise.toml [hooks] postinstall = "mise reshim && hk install --mise"`
  (`mise.toml:62-66`) runs automatically after install — installs git hooks into the
  clone; harmless and desirable in web sessions.
- `mise run lint` (`mise.toml:121-139`) wraps hk in a 700 s outer bound — compatible
  with web-session Bash (no PTY/daemon requirements). hk 1.50's pklr backend needs no
  network at lint time.
- The pytest gate (`uv run --project python pytest tests/ -x -q`) and
  `dotfiles-setup verify run` need only the uv venv (pypi-only deps: pydantic,
  pydantic-settings, pytest, ruff, ty — all allowlisted).

---

## Uncertainties / gaps

1. **mise.run / mise.jdx.dev under Trusted**: inferred blocked (absent from the
   documented allowlist; astral.sh precedent 403s per #52963) but not directly probed.
   The GitHub-release install path sidesteps the question.
2. **Does the setup script run with the repo already cloned / cwd inside it?** The docs
   imply yes (the `docker compose pull` guidance assumes project files), but it is not
   explicit. If not, `mise trust && mise install` must stay in the SessionStart hook
   (which definitively runs in the repo).
3. **Exact preinstalled uv/python versions** in the current cloud image — only "Python
   3.x" + "uv" documented; run `check-tools` in a live session to pin down.
4. **PreToolUse fail-closed mechanism**: the uv-exit-2 → deny mapping is inferred; the
   observed all-Bash-blocked state is documented
   (inventory report :118-124) but the exact exit-code path is unverified.
5. **Async SessionStart hooks**: the hooks-doc fetch said async is documented "for
   command hooks in general, not specifically enabled for SessionStart", while
   Anthropic's own startup-hook skill and community repos emit
   `{"async": true, "asyncTimeout": ...}` from SessionStart successfully. Treat the
   stdout-JSON async protocol as supported but verify in a live session before relying
   on it (sync-first is the skill's own recommendation anyway).
6. **Every root-toolset backend within the allowlist**: verified by domain class
   (npm/pypi/github/aws/docker) not per-tool URL; a stray tool with a bespoke download
   host (e.g. a vendor CDN) could 403 — surface via the hook's warn path, then add the
   domain to a Custom allowlist.
7. **Rate-limit exposure even with lockfiles**: `mise.lock` pins versions, but backend
   metadata/asset resolution can still touch `api.github.com`; with shared egress IPs,
   `GITHUB_TOKEN` should be treated as required, not optional, for reliable
   `mise install` in web sessions (corpus + #52963).
8. Bash is broken in this research container, so none of the above was live-probed
   here; the load-bearing claims rest on official docs (fetched today), the
   anthropics/claude-code issue tracker, and the 53-repo community corpus.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — issues #52963 (setup-script rate limit, astral.sh 403, GITHUB_TOKEN fix) and #55000 (Ubuntu 24.04 x86_64, TLS-inspection egress proxy)
- [jdx/mise](https://github.com/jdx/mise) — install methods, GitHub-token precedence, aqua-registry-compiled-in, python precompiled source (local mintlify cache + mise.jdx.dev + mise.run installer script)
- [jdx/hk](https://github.com/jdx/hk) — install methods, mise integration (local mintlify cache)
- [astral-sh/python-build-standalone](https://github.com/astral-sh/python-build-standalone) — python 3.14 binary source referenced by mise docs
- [apple/pkl](https://github.com/apple/pkl) — pkl release-binary source (backend class)
- [jonpulsifer/infra](https://github.com/jonpulsifer/infra) — exemplar session-start.sh (curated install, CLAUDE_ENV_FILE persistence)
- [datenknoten/freundebuch](https://github.com/datenknoten/freundebuch) — GITHUB_TOKEN-for-mise hook comments
- [joeblew999/vm-uncloud](https://github.com/joeblew999/vm-uncloud) — hook documenting anonymous GH API 403 during mise install in web sessions
- [hco/dependency-dir-analyzer](https://github.com/hco/dependency-dir-analyzer) — CLAUDE.md web-session mise hook pattern
- [wado-lang/wado](https://github.com/wado-lang/wado) — .claude/hooks/mise-setup.sh
- [entireio/cli](https://github.com/entireio/cli) — .claude/scripts/remote-setup.sh
- [StoDevX/AAO-React-Native](https://github.com/StoDevX/AAO-React-Native) — inline settings.json SessionStart mise command
- [richardthe3rd/cambridge-beer-festival-app](https://github.com/richardthe3rd/cambridge-beer-festival-app) — async SessionStart hook exemplar
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — repo baseline facts (settings.json, mise.toml, shared.toml, pyproject.toml) read from the working tree
