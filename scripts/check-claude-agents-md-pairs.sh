#!/usr/bin/env bash
# check-claude-agents-md-pairs.sh — enforce the CLAUDE.md/AGENTS.md
# pair invariant.
#
# Invoked by hk.pkl:claude_agents_md_pairs on pre-commit.
#
# Every tracked CLAUDE.md (excluding .claude/**) MUST have a sibling
# AGENTS.md in the same directory, and vice versa.
#
# Rationale: CLAUDE.md is a thin `@AGENTS.md` import for Claude Code;
# AGENTS.md is the agent-agnostic equivalent shared with Codex/Gemini.
# A CLAUDE.md without a sibling AGENTS.md would import a non-existent
# file; an AGENTS.md without a sibling CLAUDE.md would mean Claude
# doesn't load that scope's project instructions.
#
# .claude/** is exempt — that scope is Claude-specific (no AGENTS.md
# counterpart).
set -euo pipefail

rc=0
check_pair() {
  local path="$1" sibling_name="$2"
  local dir
  dir="$(dirname "$path")"
  local sibling
  if [[ "$dir" == "." ]]; then
    sibling="$sibling_name"
  else
    sibling="$dir/$sibling_name"
  fi
  if ! git ls-files --error-unmatch "$sibling" >/dev/null 2>&1; then
    echo "$path: missing sibling $sibling" >&2
    rc=1
  fi
}

while IFS= read -r f; do
  check_pair "$f" "AGENTS.md"
done < <(git ls-files | grep -E '(^|/)CLAUDE\.md$' | grep -v '^\.claude/' || true)

while IFS= read -r f; do
  check_pair "$f" "CLAUDE.md"
done < <(git ls-files | grep -E '(^|/)AGENTS\.md$' | grep -v '^\.claude/' || true)

exit "$rc"
