> **PARTIAL — stopped by coordinator 97ffeddb (2026-10-03).** Ray ruled on #1614 (P1+P4, interim P2) from `review-1614-worktree-ship-blocker-2026-10-03.md` before this review finished. Kept verbatim as written up to the stop.

# #1614 worktree ship route — cited proposals (2026-10-03)

Status: IN PROGRESS (written incrementally). Read-only review; no source edited, no worktree moved.

Inputs: issue #1614 body (fetched `gh issue view 1614 -R ray-manaloto/dotfiles --json ...`, 0 comments);
prior research `docs/research/kb/reports/agents/mise-claude-worktrees-research-2026-10-03.md` (203 lines,
treated as INHERITED until re-derived below).

## Live probes (mise 2026.10.1, this host, 2026-10-03)

P1 leak control — `mise config ls` from `.claude/worktrees/coord-97ffeddb` lists main's
`~/dev/github/ray-manaloto/dotfiles/{mise.toml,mise.local.toml,.config/mise/conf.d/shared.toml}` in addition
to the worktree's own. With `MISE_CEILING_PATHS=<main>/.claude/worktrees` only the worktree's files are
listed. Main checkout: `mise config ls` identical with and without a ceiling above it.

P2 the failing test, same worktree, single node id, both arms:
- no env: `1 failed` (`assert 0 != 0` at the `ignored` arm), logged rc=2 (/tmp/p1614a.log)
- `MISE_CEILING_PATHS=<main>/.claude/worktrees`: `1 passed`, rc=0 (/tmp/p1614b.log)

P3 KEY FIXTURE (scratch `/tmp/fx1614.*`, canonical `/private/tmp` paths; first run used `/tmp/...` in
MISE_CEILING_PATHS, which macOS canonicalises to `/private/tmp`, so the env arm falsely "leaked" — a
fixture artifact, re-run with `pwd -P`). main/mise.toml, main/.claude/worktrees/wt/mise.toml and hostile/mise.toml
each define task `probe`; `.miserc.toml` with the #1614 one-liner in main and wt. Query:
`mise --cd wt tasks info --json probe` with `MISE_IGNORED_CONFIG_PATHS=wt/mise.toml` (the test's shape).

| Arm | cwd | ceiling source | Resolved |
|---|---|---|---|
| A | wt | wt `.miserc.toml` | NOT FOUND (fix works) |
| E (control) | wt | none (wt miserc removed) | main/mise.toml (leak) |
| G | wt/sub | wt `.miserc.toml` | NOT FOUND |
| **B** | **hostile** (the test's cwd) | wt `.miserc.toml` | **main/mise.toml — LEAK** |
| C | hostile | `MISE_CEILING_PATHS` env | NOT FOUND |
| D | hostile, no ignore | wt miserc | wt/mise.toml (sanity: `--cd` works) |

=> **The `.miserc.toml` line alone does NOT make `tests/test_session_review.py:1106` pass.** The test runs
mise with `cwd=hostile_root` (a tmp dir) and `--cd REPO_ROOT` (tests/test_session_review.py:1088-1102);
miserc is discovered from the INVOCATION cwd (prior report, arm O/P: src/cli/mod.rs:868 vs :913,
miserc.rs:60-65), so the worktree's miserc is never read. Arm B reproduces exactly that. #1614's
acceptance bullet 3 therefore needs a second, test-side change (Proposal 1b below).
