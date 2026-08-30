#!/usr/bin/env bash
# scripts/graphify-hook-guard.sh — resilient wrapper around graphify's PreToolUse
# nudge hooks (`graphify hook-guard search|read`).
#
# graphify's own installer embeds a user-specific ABSOLUTE path
# (`/Users/<you>/.local/share/mise/installs/pipx-graphifyy/<ver>/bin/graphify`)
# into .claude/settings.json — wrong for a committed, multi-clone repo, and it
# pins a version that breaks on the next graphify bump. This wrapper resolves
# graphify via `uv run --project python` — the SAME repo-pinned 0.9.42 that
# `mise run graphify-query`/`graphify-health`/`graphify-update` use, NOT the
# user-global mise pin (currently 0.9.53, ~/.config/mise/config.toml, outside
# this repo — see graphify-first.md) — and FAILS OPEN (exit 0 = allow the tool
# call, no nudge) when graphify/uv is absent, so a fresh clone or CI is not
# disrupted by a `command not found` hook error.
#
# The nudge is advisory (soft mode, no --strict): it prints a "query the graph
# first" reminder that Claude Code surfaces as context; it never blocks a call.
# graphify's own copy names the bare binary — sed rewrites that to the mise
# task so the nudge agrees with graphify-first.md instead of instructing the
# one invocation the rule forbids.
#
# $1 is the hook kind: `search` (Bash|Grep matcher) or `read` (Read|Glob).
set -uo pipefail

kind="${1:-search}"

if command -v uv >/dev/null 2>&1; then
  # shellcheck disable=SC2016 # single-quoted on purpose: these backticks are
  # literal markdown in the JSON we're rewriting, not shell substitution —
  # double-quoting would make bash actually EXECUTE them as command subs.
  uv run --project python graphify hook-guard "$kind" 2>/dev/null |
    sed -e 's/`graphify query/`mise run graphify-query --/g' \
        -e 's/`graphify update`/`mise run graphify-update`/g' || true
fi
# Absent graphify/uv (fresh clone / CI): fall through and exit 0 — allow, no nudge.
exit 0
