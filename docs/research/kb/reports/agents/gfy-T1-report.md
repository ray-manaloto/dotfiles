# gfy-T1 report — graphify 0.9.73 -> 0.9.76 pin move (dotfiles)

Lane gfy-T1, worktree `.claude/worktrees/gfy-t1`, branch `chore/graphify-0976-pin`, base `cd66147e`.
Spec: `docs/specs/graphify-0976-plan-2026-10-04.md` (graphify-plan worktree) §1, §3 T1, §7.

Note: `EnterWorktree(path=...)` refused ("git could not be run to resolve it"), but the harness switched
the primary working directory to the worktree anyway; `git rev-parse --git-dir` there = `.git/worktrees/gfy-t1`.

## Log

### Step 1 — `mise run graphify-update` → rc=0 (log `.agent/logs/gfy-t1-update.log`)
- `graphifyy locked 0.9.73, latest 0.9.76`; receipts written: `docs/receipts/graphify/0.9.74.md`, `0.9.75.md`, `0.9.76.md`.
- `graphifyy lock updated to 0.9.76; environment synced`. `python/uv.lock` diff: the graphifyy row only (version + sdist/wheel hashes, 3+/3-).
- Skills "refreshed" for `.claude/`, `.codex/`, `.agents/`: SKILL.md bytes UNCHANGED (vendor skill identical 0.9.73→0.9.76); only the three `.graphify_version` stamps moved 0.9.73→0.9.76.
- Post-update offline check: path-binary `~/.local/share/mise/installs/pipx-graphifyy/0.9.76/bin/graphify` (0.9.76), `graphify currency current`.

### Release notes vs `python/src/dotfiles_setup/graphify*.py`
Our modules call the vendor CLI only as `graphify update <target>` (`graphify.py:859`, AST rebuild) plus `hook-guard` (nudge rewrite in `graphify_hook.py`). Grep for `extract`/`path`/`cluster-only`/`merge-graphs`/`dedup`/`stat-index`/`GRAPHIFY_OUT`/`skills/graphify` in those modules: 0 hits (control arm: the same pattern hit `"update"` at `graphify.py:859`).
- 0.9.76 #4062: graphify no longer indexes its own installed skill folders / whole-written rule+hook files → manifest shrinks; `graphify-health` freshness is manifest-based, so the rebuild (G step) re-baselines it. Watch item for the health step.
- 0.9.75 #4042: hook-guard reminder names the effective graph path when `GRAPHIFY_OUT` is customised. Our `_general_nudge` keys on `additionalContext.startswith("MANDATORY:")`, not on the path text; we do not set `GRAPHIFY_OUT`. Covered by pytest (G step).
- 0.9.75 #4014 (`extract` refuses dedup-shrink without `--allow-dedup-shrink`), #4005 (AST cache stat index per root), #4010 (cluster-only/label parallel edges): not invoked by our code.
- 0.9.76 #3919 (`hook install` refuses out-of-repo `core.hooksPath`): irrelevant — `do-not.md` #8 forbids `graphify hook install`.
- 0.9.74/0.9.76 extractor changes (Python external-module `calls` edges #4043, etc.) change graph CONTENT only.

### Step 2 — `mise run graphify-check` → rc=0 (log `.agent/logs/gfy-t1-check.log`)
- `graphifyy locked 0.9.76, latest 0.9.76`; path-binary 0.9.76; `graphify currency current`.
- `graphify-health: missing (runtime=0.9.76)` — this worktree has no `graphify-out/graph.json` yet (gitignored, P3); the rebuild is the slot-gated step.
