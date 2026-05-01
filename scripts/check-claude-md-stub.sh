#!/usr/bin/env bash
# check-claude-md-stub.sh — enforce the CLAUDE.md import-stub invariant.
#
# Invoked by hk.pkl:claude_md_import_stub on pre-commit.
#
# Every tracked CLAUDE.md (excluding .claude/**) MUST consist solely of:
#   - exactly one `@AGENTS.md` import line
#   - optional blank lines
#   - optional HTML comments (single- or multi-line)
#
# Rationale: CLAUDE.md is the Claude Code memory file; AGENTS.md is the
# agent-agnostic equivalent shared with Codex/Gemini. Keeping CLAUDE.md
# as a thin `@AGENTS.md` import avoids drift between the two.
#
# .claude/** is exempt — that scope is Claude-specific (e.g.,
# .claude/CLAUDE.md holds OMC orchestration that other agents don't load).
set -euo pipefail

rc=0
while IFS= read -r f; do
  awk '
    BEGIN { in_comment = 0; content = "" }
    {
      line = $0
      while (1) {
        if (in_comment) {
          i = index(line, "-->")
          if (i > 0) { line = substr(line, i + 3); in_comment = 0 }
          else { line = ""; break }
        } else {
          i = index(line, "<!--")
          if (i > 0) {
            before = substr(line, 1, i - 1)
            rest   = substr(line, i + 4)
            j = index(rest, "-->")
            if (j > 0) { line = before substr(rest, j + 3) }
            else       { line = before; in_comment = 1 }
          } else { break }
        }
      }
      sub(/^[ \t]+/, "", line); sub(/[ \t]+$/, "", line)
      if (line != "") content = content line "\n"
    }
    END {
      if (content != "@AGENTS.md\n") {
        printf "%s: not a thin @AGENTS.md import stub\n", FILENAME > "/dev/stderr"
        printf "  allowed: @AGENTS.md import + blank lines + HTML comments only\n" > "/dev/stderr"
        printf "  actual non-comment content:\n" > "/dev/stderr"
        n = split(content, lines, "\n")
        for (k = 1; k <= n; k++) if (lines[k] != "") printf "    %s\n", lines[k] > "/dev/stderr"
        exit 1
      }
    }
  ' "$f" || rc=1
done < <(git ls-files | grep -E '(^|/)CLAUDE\.md$' | grep -v '^\.claude/' || true)

exit "$rc"
