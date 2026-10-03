#!/usr/bin/env bash
# scripts/pretooluse-guard.sh — the ONE per-tool-call PreToolUse hook: the
# mise-tasks-only/ask-quality/branch guard AND graphify's nudge, in a single
# Python process (python/src/dotfiles_setup/hook_dispatch.py). Fail-open shim.
#
# Fast path: the venv's own interpreter, no `uv` resolution per call (two uv
# chains per Bash call were ~1.2 s of process starts, host-load review
# 2026-10-02). `uv run` is the fallback, which also re-syncs a stale venv.
# FAILS OPEN (exit 0 = allow) when neither can run, so a cold Claude-web
# session before web-setup.sh is not bricked by every call being denied.
#
# EVERY PATH IS ANCHORED TO $CLAUDE_PROJECT_DIR, NOT THE CWD (#343): hooks run
# in the session's cwd, and a relative path silently resolved a sibling repo.
# AND EVERY FAIL-OPEN IS COUNTED: one nobody records is indistinguishable from
# enforcement. See .claude/rules/mise-tasks-only.md and issue #343.
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-}"
[ -n "$ROOT" ] || ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="${DOTFILES_GUARD_FAILOPEN_LOG:-$HOME/.local/state/dotfiles/guard-fail-open.log}"
VENV="${UV_PROJECT_ENVIRONMENT:-$ROOT/python/.venv}"

# Record, then allow — the exit 0 stands whether or not the line was written.
fail_open() {
  mkdir -p -- "$(dirname -- "$LOG")" 2>/dev/null &&
    printf '%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$PWD" >>"$LOG" 2>/dev/null
  exit 0
}

# Builtin read, not $(cat): on this Mac `cat` is a mise shim (~200 ms a call).
# `python -P`: never put the session's cwd on sys.path (a stray json.py there
# would run on every call and fail the guard open).
IFS= read -r -d '' payload || true
if [ -x "$VENV/bin/python" ] &&
  out="$(printf '%s' "$payload" | "$VENV/bin/python" -P -m dotfiles_setup.hook_dispatch "$ROOT")"; then
  printf '%s' "$out"
  exit 0
fi
{ command -v uv && uv python find '>=3.14'; } >/dev/null 2>&1 || fail_open "interpreter-absent"
out="$(printf '%s' "$payload" | uv run --project "$ROOT/python" python -P -m dotfiles_setup.hook_dispatch "$ROOT")" ||
  fail_open "guard-error-rc=$?"
printf '%s' "$out"
