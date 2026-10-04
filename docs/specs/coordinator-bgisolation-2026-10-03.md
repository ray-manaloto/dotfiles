# Spec — coordinator sessions edit main-checkout planning files (bgIsolation none, coordinator-only)

Requested by Ray, 2026-10-03 ~20:20 CDT: "/codex-sdlc-team skill team to work on this", about a side-agent note. The note said a background coordinator cannot update `task_plan.md` or the ship queue.

## 1. Objective

A coordinator started by `mise run coordinator-handoff -- launch` must be able to Edit and Write the gitignored main-checkout planning files: root `task_plan.md`, `findings.md`, `progress.md`, and `.agent/plans/**`.

The failure this prevents: Claude Code's background-session isolation refuses those writes. The message is "This background session hasn't isolated its changes yet… Call EnterWorktree first", or, from inside a worktree, "Edit the worktree copy of this file instead of the shared-checkout path". Gitignored files have no worktree copy, so `task_plan.md` drifts at every handoff. This was measured on coordinator c1a35607, 2026-10-03, with three refusals, including one from a subagent.

Lanes (non-coordinator `--bg` sessions) MUST keep worktree isolation.

Follow-up: [coordinator main-checkout write guard](coordinator-main-checkout-guard-2026-10-03.md) confines coordinator writes there to gitignored paths.

## 2. Files

- `python/src/dotfiles_setup/coordinator_handoff.py`: the launch `--settings` JSON.
- `tests/test_coordinator_handoff.py`: the argv assertion at ~:503. Add one test that the settings JSON parses and carries both keys.
- `docs/specs/coordinator-auto-handoff-2026-10-02.md` (:136) and `docs/specs/coordinator-auto-handoff-2026-10-02-requirements.md` (:16): update the documented argv.
- `.claude/skills/coordinator-handoff/SKILL.md`: one sentence in §2 saying the successor launches with `worktree.bgIsolation: "none"`, so it may edit main-checkout planning files directly. Tracked edits go through `EnterWorktree`, never a branch switch of the shared main checkout (superseded wording "must still branch before editing tracked files" — see the main-checkout guard spec, Revision 3).

Nothing else. In particular, do NOT add `worktree.bgIsolation` to `.claude/settings.json` or `.claude/settings.local.json`. That would remove isolation from every lane.

## 3. Interfaces

- Keep the constant name `CROSS_SESSION_SETTINGS`, or rename it to `COORDINATOR_SETTINGS`. If you rename it, update every reference.
- Its value must be compact JSON, equal to `json.dumps({"crossSessionInbound": "accept", "worktree": {"bgIsolation": "none"}}, separators=(",", ":"))`. Build it with `json.dumps` rather than a hand-written string.
- The launch argv shape is unchanged: `["claude","--bg","-n",name,"--settings",<json>,brief]`.

## 4. Constraints and invariants

- No inline lint suppressions (no_lint_skip). Zero-bash logic.
- No change to lane launch paths: `parallel-work-split` and any `claude --bg` launch outside `coordinator_handoff.launch`.
- Do not run `claude --bg` or any real launch. Tests use the existing dry-run and deps seams.
- COMMIT: caller. Do not commit or push.
- Do not edit files outside the list in section 2.

## 5. Verification

- `uv run --project python pytest tests/test_coordinator_handoff.py -q`: rc 0.
- Mutation arm: delete the `"worktree"` key and confirm the new test fails, then restore it.
- `mise run lint-docs`: rc 0, because SKILL.md changes.
- The caller runs `mise run lint`, the full pytest and `mise run verify`.

## 6. Commit

`caller`.

## 7. PREMISES

| # | Kind | Claim | Source |
|---|---|---|---|
| P1 | L | `CROSS_SESSION_SETTINGS = '{"crossSessionInbound":"accept"}'` | `python/src/dotfiles_setup/coordinator_handoff.py:109` |
| P2 | I | The launch argv is `["claude","--bg","-n",name,"--settings",CROSS_SESSION_SETTINGS,brief]` | `python/src/dotfiles_setup/coordinator_handoff.py:733` |
| P3 | L | The test asserts argv[5] == `'{"crossSessionInbound":"accept"}'` | `tests/test_coordinator_handoff.py:503` |
| P4 | L | "With `\"none\"`, background jobs edit the working copy directly." The setting's only values are `"worktree"` and `"none"`; it has no per-path form | `knowledge-base/sources/agent-harness-docs/docs/claude-code/settings-reference.md:4965-4981` |
| P5 | L | Isolation is skipped only for a linked worktree, a non-git dir, or "The write is outside the working directory" | `…/claude-code/agent-view.md:494-497` |
| P6 | L | `worktree.bgIsolation` was added in v2.1.143. The host runs 2.1.289 | `…/claude-code/agent-view.md:998`; `claude --version` → 2.1.289 |
| P7 | A | `--settings` JSON accepts the nested `worktree` object, the same as file settings ("Scope: Any file") | `…/settings-reference.md:4890`. UNVERIFIED for the CLI flag. The caller verifies it live after merge with the next real launch |
| P8 | L | Planning files are gitignored (`/task_plan.md` at `.gitignore:144`), so they have no worktree copy | `.gitignore:144` |
