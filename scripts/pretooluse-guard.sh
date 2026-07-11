#!/usr/bin/env bash
# scripts/pretooluse-guard.sh — resilient wrapper around the mise-tasks-only
# PreToolUse guard (belt-and-braces for the web-setup.sh SessionStart bootstrap).
#
# Runs the real guard when its interpreter (Python >=3.14 via uv) is present;
# FAILS OPEN (exit 0 = allow the Bash call) only when that interpreter is
# ABSENT — so a cold Claude-web session, before web-setup.sh has installed the
# toolchain, is not bricked by every Bash call being denied.
#
# This aligns actual behavior with the documented intent in
# .claude/rules/mise-tasks-only.md: "The hook fails OPEN on its own errors (a
# crashed guard must not brick every Bash call)." Enforcement is UNCHANGED
# everywhere the toolchain is present (devcontainer, CI, a bootstrapped web
# session), where the real guard runs exactly as before. The only environments
# that now fail open are precisely the ones where the guard could not run at all
# — a strict improvement over fail-closed, never a bypass where enforcement was
# previously effective.
set -uo pipefail

if ! command -v uv >/dev/null 2>&1 || ! uv python find '>=3.14' >/dev/null 2>&1; then
  # The interpreter the guard needs is unavailable — allow, do not brick.
  exit 0
fi

exec uv run --project python dotfiles-setup hook pretooluse
