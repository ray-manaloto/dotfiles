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
# `--project "$CLAUDE_PROJECT_DIR/python"` resolves this repo's pinned
# graphify, NOT the user-global PATH shim (aligned 2026-08-31, not kept in
# sync — see graphify-first.md) — ANCHORED, not relative: a bare
# `--project python` fails rc=2 off the repo root (a subagent, a worktree).
#
# Advisory, soft mode. Strict mode (GRAPHIFY_HOOK_STRICT/_TTL,
# graphify/cli.py) is an env var, not a code change — set it in
# .claude/settings.json's env block if ever needed. GRAPHIFY_BIN is NOT a
# binary override (vendor skill doc only, never runtime code).
#
# $1 is the hook kind: `search` (Bash|Grep matcher) or `read` (Read|Glob).
set -uo pipefail

kind="${1:-search}"
project_dir="${CLAUDE_PROJECT_DIR:-.}/python"

if command -v uv >/dev/null 2>&1; then
  uv run --project "$project_dir" dotfiles-setup graphify hook-guard "$kind" 2>/dev/null || true
fi
# Absent uv (fresh clone / CI): fall through and exit 0 — allow, no nudge.
exit 0
