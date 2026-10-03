# Brief — lane L1 "docs-rules" + the de9575bd report fixes (Ray ruling 2026-10-03 ~14:50)

Coordinator: newest dotfiles coordinator by ListAgents recency (now `dotfiles-20261003T140808.926861000-05.coordinator`).
Report BY NAME; keep your state in `<worktree>/.agent/kb/raw/lanes/L1.md`. NEVER Bash-write the main checkout (Ray
ruling b). You are launched inside your worktree — do NOT call EnterWorktree.

Source of truth: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/coord-docs-20261003e/docs/research/kb/reports/agents/apply-998ab91b-findings-proposals-2026-10-03.md`
(Q1-A, Q2 L1, Q3 rows) plus each audit's exact FIX-NOW text in
`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/lane-completion-20261002/docs/research/kb/reports/agents/session-audit-*-2026-10-03f.md`.

## Part A — finish de9575bd (Ray: fix reports, then ship)
Work in `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/lane-completion-20261002` (branch
docs/lane-completion-protocol @ de9575bd; it is a docs-only branch). Apply: V3 (copy
`~/.claude/jobs/998ab91b/tmp/skill-hunk.md` onto the branch as `docs/research/kb/raw/parallel-work-split-hunk-2026-10-02.md`
or the path V3 names — do this FIRST, before 998ab91b's job dir is cleaned), V5–V9, V12, V13, PC-F7, PC-F5 (verify the
inventory is verbatim). Commit. Then ask for "SLOT watch-push GRANTED", run `mise run gate -- run lint` and
`mise run gate -- run verify`, and report the head — the coordinator ships it.

## Part B — docs/rules (branch `docs/L1-handoff-findings-rules`, a NEW worktree from origin/main)
Rules: `agent-artifact-conventions.md` (R3, ruling (b) "never Bash-bypass a refused main-checkout write; use
`mise run handoff-inbox`", the quoted `"rc=$?"` workaround, watchers/coordinators never EnterWorktree);
`long-running-command-hangs.md` (R7); `research-repo-enumeration.md` + `agent-report-persistence.md` (PC-F7: allow a
trailing `## Addendum`); `.claude/skills/session-handoff/SKILL.md` (R4, R8, DE-F1 §1b line). Memory
`feedback_no_compact.md` (R11) is user-scope: draft the text in your report, the coordinator writes it.
Respect `md_size_budget`; run `mise run lint-docs`. Gates need "SLOT L1 GRANTED". Report the head; coordinator ships.

Do NOT touch parallel-work-split, coordinator-handoff, hook_guard.py (L2, after #1606) or research-sweep (L3, after 1502).
