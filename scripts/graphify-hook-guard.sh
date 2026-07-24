#!/usr/bin/env bash
# scripts/graphify-hook-guard.sh — resilient wrapper around graphify's PreToolUse
# nudge hooks (`graphify hook-guard search|read`).
#
# graphify's own installer embeds a user-specific ABSOLUTE path
# (`/Users/<you>/.local/share/mise/installs/pipx-graphifyy/<ver>/bin/graphify`)
# into .claude/settings.json — wrong for a committed, multi-clone repo, and it
# pins a version that breaks on the next graphify bump. This wrapper resolves
# graphify at runtime via mise (host-pinned in mise.toml) and FAILS OPEN (exit 0
# = allow the tool call, no nudge) when graphify is absent — so a fresh clone,
# or CI, before graphify is installed is not disrupted by a `command not found`
# hook error. Same belt-and-braces shape as scripts/pretooluse-guard.sh.
#
# The nudge is advisory (soft mode, no --strict): it prints a "query the graph
# first" reminder that Claude Code surfaces as context; it never blocks a call.
#
# $1 is the hook kind: `search` (Bash|Grep matcher) or `read` (Read|Glob).
set -uo pipefail

kind="${1:-search}"

# MISE FIRST. Reversed until 2026-07-23, making the claim above false: a stale
# 0.9.23 install dir sat ahead of the shims under a 0.9.25 pin.
if command -v mise >/dev/null 2>&1; then
  mise exec -- graphify hook-guard "$kind" 2>/dev/null || true
elif command -v graphify >/dev/null 2>&1; then
  graphify hook-guard "$kind" 2>/dev/null || true
fi
# Absent graphify (fresh clone / CI): fall through and exit 0 — allow, no nudge.
exit 0
