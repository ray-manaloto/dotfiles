# llvm23 lane hook errors — diagnosis (Explore lane of coordinator 27e2bf5c, 2026-10-03, verbatim)

Both warnings share one cause: the lane runs the new hooks against an OLD copy of the Python CLI. Neither is a real handoff or rename problem.

**Where things are**
- Lane: session 6fae0fec-3da8-48e2-838d-cc9aafce9a0b, worktree /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002, branch feat/llvm-23-detect-bump at 87599224.
- Job record ~/.claude/jobs/6fae0fec/state.json: cwd is the main checkout, name ...llvm-23-bump, created 01:44Z.
- Lane branched from main at 46d87389 (01:49Z), before #1583 (4e2c9395, 03:53Z), which added both hooks and their Python subcommands.
- Hooks come from the main checkout's .claude/skills (its own worktree has neither skill dir), but its worktree Python is pre-#1583.
- Control arm: grep `coordinator-handoff|session-start` in the lane's python/src/dotfiles_setup/main.py finds no subcommand registration; same grep on main finds main.py:45-48, 173-176, 1787-1790.

**1. `session-start ERROR: pending rename failed: pending recovery failed after 3 attempts; reload to retry`**
- Emitted by .claude/skills/session-start/hooks/register.ts — outer prefix :296 (prompt.submit catch), inner text :213.
- Trigger: each prompt, recoverPending runs `uv run --project python dotfiles-setup session-start pending` in CLAUDE_PROJECT_DIR, falling back to session root (:106-108). Non-zero exit three times (:198-199), then gives up (:194-195, :212-213). Test-covered at tests/fixtures/session_start_hook/harness.ts:534.
- Pending-rename state: no file for 6fae0fec (not in dotfiles/.agent/state/session-start/; lane worktree has no .agent/state/session-start/). Nothing lost.
- Effect: only the automatic /rename is skipped; session already has a valid name. No lane action.

**2. `coordinator-handoff: handoff ERROR: decide rc 2`**
- Emitted at .claude/skills/coordinator-handoff/hooks/register.ts:136, shown by fail() at :62-63 (`decide rc` also appears in session-start/hooks/register.ts:124).
- `decide` never exits 2 for a role refusal: Python main returns 0 with JSON for every decision incl. not-coordinator (python/src/dotfiles_setup/coordinator_handoff.py:1274-1287). Its only rc 2 path is worktree-unavailable (:1265-1271). The "2 = refused (invalid role/id ...)" help at :723 and :1093 belongs to launch/retire.
- Most likely cause (inferred, not run): argparse rejects the unknown `coordinator-handoff` choice in the pre-#1583 CLI → usage exit 2. Not executed because `uv run` would sync the lane's venv.
- Not the #1583 role-check gap: the role check is never reached. Fail-closed; cannot fire a handoff (:242-244 returns before any command.run).
- With current Python, decide would return not-coordinator (name check :197-199, :345-348).

**Is a reload safe? Yes, but pointless.** /reload-plugins and /reload-skills only re-register hooks; next measurement re-runs the old CLI → rc 2 again. Auto-submit only when Python returns fire:true (register.ts:257, :283).

**Fix:** rebase/merge main (needs #1583, 4e2c9395) into feat/llvm-23-detect-bump, or ignore until the lane's PR lands. Lane must not run /coordinator-handoff itself.

## Coordinator note
Class defect: hooks resolve from the MAIN checkout's .claude/skills while their Python CLI resolves from the lane's (stale) worktree — hook/CLI version skew for every lane branched before a hook change. Forwarded to the handoff-automation research lane.

## GitHub repos touched

_None._
