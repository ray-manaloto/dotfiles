#!/usr/bin/env bash
# scripts/pretooluse-guard.sh — resilient wrapper around the mise-tasks-only
# PreToolUse guard (belt-and-braces for the web-setup.sh SessionStart bootstrap).
#
# Runs the real guard when its interpreter (Python >=3.14 via uv) is present;
# FAILS OPEN (exit 0 = allow the Bash call) when it cannot run — so a cold
# Claude-web session, before web-setup.sh has installed the toolchain, is not
# bricked by every Bash call being denied.
#
# EVERY PATH IS ANCHORED TO THE PROJECT ROOT, NOT THE CWD (#343). Claude Code
# runs hooks "in the current directory", so in a session that also works in a
# sibling repo a relative path resolves against THAT repo. Measured: 125 Bash
# calls this guard denies executed unchecked while the cwd was the
# knowledge-base clone. Anchoring settings.json's script path alone is NOT
# enough — `uv run --project python` is relative too and fails rc=2 off-root,
# so $ROOT is threaded into the exec line as well.
#
# AND EVERY FAIL-OPEN IS COUNTED. A fail-open nobody records is
# indistinguishable from enforcement — which is exactly how this went unseen:
# the guard was documented as covering every Bash call while it silently
# allowed them. See .claude/rules/mise-tasks-only.md and issue #343.
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-}"
[ -n "$ROOT" ] || ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="${DOTFILES_GUARD_FAILOPEN_LOG:-$HOME/.local/state/dotfiles/guard-fail-open.log}"

# Record, then allow. Never let bookkeeping failure turn a fail-open into a
# brick: the exit 0 stands whether or not the line was written.
fail_open() {
  mkdir -p -- "$(dirname -- "$LOG")" 2>/dev/null &&
    printf '%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$PWD" >>"$LOG" 2>/dev/null
  exit 0
}

if ! command -v uv >/dev/null 2>&1 || ! uv python find '>=3.14' >/dev/null 2>&1; then
  fail_open "interpreter-absent"
fi

decision="$(uv run --project "$ROOT/python" dotfiles-setup hook pretooluse)" ||
  fail_open "guard-error-rc=$?"
printf '%s' "$decision"
