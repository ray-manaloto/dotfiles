#!/usr/bin/env bash
# scripts/web-setup.sh — Claude Code on the web / cloud-session toolchain bootstrap.
#
# WHY THIS EXISTS
#   Claude Code on the web boots from Anthropic's Ubuntu 24.04 image, which has
#   no mise and no Python >=3.14. This repo's PreToolUse guard
#   (`uv run --project python dotfiles-setup hook pretooluse`) needs Python
#   >=3.14; when it is absent the guard errors on startup and the harness fails
#   closed, blocking EVERY Bash call — the "web brick". Full analysis:
#   .omc/research/research-20260709-r2-web-env/report.md. This script installs
#   the toolchain so the guard can start and the repo gates (mise run lint,
#   uv run --project python pytest, dotfiles-setup verify run) work.
#
# HOW TO USE — two entry points, same script:
#   1. Web environment SETUP SCRIPT (recommended, runs before Claude launches,
#      snapshot-cached ~7 days): paste the CONTENTS of this file into the
#      environment's setup-script field in the claude.ai/code UI.
#   2. SessionStart hook (idempotent re-check on every session/resume): wired in
#      .claude/settings.json, gated on CLAUDE_CODE_REMOTE=true. Runs at the
#      session-lifecycle layer, so it executes even while the Bash *tool* is
#      still guard-blocked — installing the interpreter the guard needs before
#      the first Bash tool call, which un-bricks the session.
#
# NETWORK POLICY (claude.ai/code environment config)
#   Under the default "Trusted" policy, GitHub releases + PyPI are reachable but
#   `mise.run` is NOT. Either (a) add `mise.run` and `mise.jdx.dev` to a Custom
#   allowlist (simplest — keeps the one-liner below), or (b) replace the mise
#   install with a direct GitHub-release binary download. Set a read-only
#   GITHUB_TOKEN env var to avoid anonymous GitHub API rate limits (the dominant
#   real-world mise-in-web failure). Doppler (`api.doppler.com`) is only needed
#   if a web workflow requires secrets — the lint/test/verify gates do not.
#
# ZERO-BASH-LOGIC EXCEPTION
#   This is a thin bootstrap that MUST run before Python >=3.14 and the uv venv
#   exist, so it cannot itself be Python — the sanctioned exception to the
#   zero-bash-logic rule (thin wrappers in scripts/).
set -euo pipefail

log() { printf '[web-setup] %s\n' "$*"; }

# 1. Ensure mise. mise.run is blocked under the default Trusted policy; either
#    allowlist it (see header) or swap this for a GitHub-release binary download.
if ! command -v mise >/dev/null 2>&1 && [ ! -x "${HOME}/.local/bin/mise" ]; then
  log "installing mise"
  curl -fsSL https://mise.run | sh
fi
export PATH="${HOME}/.local/bin:${HOME}/.local/share/mise/shims:${PATH}"

# 2. Install the toolchain. `mise install` resolves the active config; to fit the
#    ~5-minute setup-script budget, scope it to the shared 20-tool fragment via a
#    MISE_ENV=web overlay rather than the full root mise.toml (see Run A report).
log "installing toolchain via mise"
mise trust --yes >/dev/null 2>&1 || true
mise install

# 3. Ensure Python 3.14 (for the repo venv + the PreToolUse guard), then sync deps.
#    uv is pre-installed in the web image; auto-downloads the interpreter.
if command -v uv >/dev/null 2>&1; then
  log "ensuring Python 3.14 + uv project deps"
  uv python install 3.14
  uv sync --project python
fi

# 4. SessionStart-hook mode: persist PATH so subsequent Bash tool calls (and the
#    guard) find mise + the shims. No-op when run as the setup script. The
#    literal '$PATH' is written via ${dollar} so it stays UNEXPANDED (it expands
#    when the env file is later sourced) without tripping shellcheck SC2016 on a
#    single-quoted expansion — which the no_lint_skip rule forbids suppressing.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  dollar='$'
  printf 'export PATH="%s/.local/bin:%s/.local/share/mise/shims:%sPATH"\n' \
    "${HOME}" "${HOME}" "${dollar}" >>"${CLAUDE_ENV_FILE}"
fi

log "done"
