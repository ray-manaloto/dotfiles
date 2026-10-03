# Branch archive review — 2026-10-03

Source log: /Users/rmanaloto/.claude/jobs/27e2bf5c/tmp/branch-archive.log (7 OK, 1 FAIL)
Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles. All tags are lightweight, local-only, `archive/2026-10-03/*`.

| branch | tag | sha | unpushed commits preserved | WIP files preserved | worktree removed |
|---|---|---|---|---|---|
| codex/graphify-0-9-67 | archive/2026-10-03/codex-graphify-0-9-67 | b7747f85 | y (parent eb9a8c16; 0 branch commits ahead of origin/main, +1 WIP commit) | y — 14 files incl. docs/specs/graphify-project-sync.md + both 2026-09-23 graphify-sync reports | y |
| codex/agentsview-managed-service | archive/2026-10-03/codex-agentsview-managed-service | 835eae79 | y (parent e0f58cea; 0 ahead + WIP) | y — 10 files incl. agentsview.py, test_agentsview.py, docs/specs/agentsview-managed-service.md, .config/mise/agentsview/{agentsview,global-fragment,tasks}.toml | y |
| fix/agent-shell-mise-hookenv | archive/2026-10-03/fix-agent-shell-mise-hookenv | 68eb20e4 | y (parent f08cd0a9; 0 ahead + WIP) | y — 12 files incl. agent_shell_env.py, test_agent_shell_env.py | y |
| codex/worktree-orchestration-20260929 | archive/2026-10-03/codex-worktree-orchestration-20260929 | a530e488 | y (1, expected 1) | n/a (clean; tag = branch tip) | y |
| codex/dotfiles-project-sync-readiness | archive/2026-10-03/codex-dotfiles-project-sync-readiness | 7a636974 | y (2, expected 2) | n/a (clean) | y |
| docs/session-audit-2026-09-30 | archive/2026-10-03/docs-session-audit-2026-09-30 | ce3ab0b5 | y (2, expected 2; also on origin at same sha) | n/a (clean) | y |
| feat/native-cli-installers-workflow | archive/2026-10-03/feat-native-cli-installers-workflow | 102ee0c5 | y (2, expected 2; also on origin at same sha) | n/a (clean) | y |
| codex/agentsview-native-service (FAIL) | archive/2026-10-03/codex-agentsview-native-service (left by archive step) | 5ec8ac8d | y (branch tip 36537951 = origin; 1 ahead of main + WIP) | y — WIP commit holds the 6 paths; worktree also restored | **n — kept (locked), by design** |

## Checks
- Ahead counts: `git rev-list --count origin/main..<tag>`, which matches the expected 1/2/2/2. Each WIP tag sits one commit above its parent branch tip.
- WIP: `git diff --name-status <tag>^ <tag>` plus targeted `ls-tree -r --name-only`. Negative control: an invented absent path printed nothing. Positive control: `ls-tree origin/main -- AGENTS.md` returned it.
- Local branches for all 7 are GONE. The 5 without a remote copy now exist **only** as these local tags. A tag deleted before it is pushed means that work is lost.
- `git worktree prune --dry-run -v`: no output, rc=0. No leftover dirs for the 7 (a grep control matched the kept native-service dir).

## FAIL fix — codex/agentsview-native-service
- The worktree is still present and LOCKED ("Live AgentsView global mise tasks reference this worktree; migrate references before removal"). Branch local = origin = 36537951.
- Before the fix, the index held 6 staged entries (left by the coordinator's `git add -A`). Ran `git -C <wt> reset -q`, rc=0. Status is now exactly:
  ` M .config/mise/agentsview-native/tasks.toml`, ` M docs/specs/agentsview-native-follow-ons.md`, ` M mise.lock`, ` M mise.toml`,
  `?? .config/mise/agentsview-native/embedding-action-manifest.json`, `?? .config/mise/agentsview-native/embedding-policy.toml`.
- The worktree content equals the tag: tracked diff vs the tag shows no tracked files, and both untracked files are byte-identical to the tag's copies.
- **Anything wrong:** the log says FAIL, but the archive step still created tag `archive/2026-10-03/codex-agentsview-native-service` → 5ec8ac8d. The tag is harmless (a redundant WIP backup) and was left in place, because deleting tags is not allowed. The log does not mention it.

## Restore
`git worktree add <dir> -b <branch> <tag>`. For WIP tags, then run `git reset HEAD^` (mixed) to turn the WIP commit back into uncommitted changes.
