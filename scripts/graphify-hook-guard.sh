#!/usr/bin/env bash
# scripts/graphify-hook-guard.sh — thin fail-open exec wrapper for the
# graphify PreToolUse nudge. All logic (resolving graphify, execing
# `graphify hook-guard`, rewriting its bare-binary nudge text to this
# repo's mise tasks) is Python: dotfiles-setup graphify hook-guard ->
# python/src/dotfiles_setup/graphify.py::hook_guard_main/rewrite_hook_nudge
# (zero-bash-logic). This script only fails open (exit 0, no nudge) when
# uv is missing — fresh clone / CI before bootstrap — same rationale as
# scripts/pretooluse-guard.sh: a crashed guard must not brick every call.
#
# `uv run --project python` resolves this repo's pinned graphify 0.9.42
# (python/pyproject.toml) — NOT the user-global PATH shim (currently
# 0.9.53, ~/.config/mise/config.toml — see graphify-first.md).
#
# Advisory, soft mode. graphify's strict mode (GRAPHIFY_HOOK_STRICT /
# _TTL, graphify/cli.py) is an env-var override, not a code change — set
# it in .claude/settings.json's env block if ever needed, don't build
# machinery for it. GRAPHIFY_BIN is NOT a binary override (vendor skill
# doc only, never runtime code) — `uv run` resolution stays necessary.
#
# $1 is the hook kind: `search` (Bash|Grep matcher) or `read` (Read|Glob).
set -uo pipefail

kind="${1:-search}"

if command -v uv >/dev/null 2>&1; then
  uv run --project python dotfiles-setup graphify hook-guard "$kind" 2>/dev/null || true
fi
# Absent uv (fresh clone / CI): fall through and exit 0 — allow, no nudge.
exit 0
