# Brief — lane L0 "urgent-code" (Ray ruling 2026-10-03 ~14:50: 5 file-keyed groups; urgent now, no reorder)

Coordinator: newest dotfiles coordinator by ListAgents recency (now `dotfiles-20261003T140808.926861000-05.coordinator`).
Report BY NAME; keep your state in `<your worktree>/.agent/kb/raw/lanes/L0.md`. NEVER Bash-write the main checkout
(Ray ruling b). You are launched inside your worktree — do NOT call EnterWorktree.

Source of truth: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/coord-docs-20261003e/docs/research/kb/reports/agents/apply-998ab91b-findings-proposals-2026-10-03.md`
(Q2 L0, Q3 rows RO-F1, DE-F1, DE-F4, PC-F3) and the audit reports on branch docs/lane-completion-protocol
(worktree `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/lane-completion-20261002`,
`docs/research/kb/reports/agents/session-audit-*-2026-10-03f.md`) for each finding's exact FIX-NOW text.

## Scope (files ONLY these; collide with nothing in flight)
1. FIRST: `mise run handoff-inbox -- append` (and a read/list verb if cheap): python module + mise task, reusing
   `HANDOFF_INBOX` at `python/src/dotfiles_setup/coordinator_handoff.py:108`; tests. Purpose: lanes/watchers write the
   main-checkout fallback inbox WITHOUT a Bash bypass (ruling b). Must work from any worktree (resolve the main checkout
   via `git rev-parse --git-common-dir`). Do NOT touch `main.py` if lock-format's uncommitted edit there can be avoided —
   if CLI registration requires main.py, keep the hunk minimal and report it.
2. RO-F1: `python/src/dotfiles_setup/command_audit.py:337` classifies every failed command as guard-denied (bypass alarm
   blind). Fix + test with both arms (a real `Error: Exit code` failure is NOT counted as a guard deny; a real deny is).
3. DE-F1: `python/src/dotfiles_setup/agentsview_pass.py:160,310` uses `repo_root.name` as `--project`; use `--session`
   (verified to work) or the correct project id. Test.
4. DE-F4: `python/src/dotfiles_setup/session_orphans.py:83` per DE audit. Test.

## Process
Seven-part spec first (spec-scribe or yourself) → premise-verifier → implementation (codex-sol-implementer per the
codex-sdlc-team skill, or inline if small) → re-verify every claim yourself → Opus cold review → gates via
`mise run gate -- run lint|verify|pytest`. **HOST SLOT:** before pytest/verify/push, ask the coordinator for the slot and
wait for "SLOT L0 GRANTED". Commit on branch `fix/L0-handoff-findings-urgent`; tell the coordinator the head; the
coordinator ships (one shipper).
