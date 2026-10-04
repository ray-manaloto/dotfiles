# Spec — coordinator write guard: only gitignored paths in the main checkout

Follow-up to `docs/specs/coordinator-bgisolation-2026-10-03.md`. Requested by Ray on 2026-10-03, via a relayed side-agent note: "Consider limiting coordinators to the task plan and `.agent/plans` files, which git ignores, and keeping every other edit in worktrees". The request was "/codex-sdlc-team skill team to research and fix".

## 1. Objective

Coordinators are now launched with `worktree.bgIsolation: "none"`, so they can write the main checkout directly. The main checkout is also where `mise run ship` and `land` run, and it often has another lane's PR branch checked out (2026-10-03: `fix/L0-handoff-findings-urgent`). A coordinator Edit/Write to a TRACKED (non-ignored) file there would leak into that PR, or leave the tree dirty and fail a ship.

Add a PreToolUse write guard that DENIES Edit, Write and NotebookEdit from a **coordinator session** when the target is inside the **main checkout** and is **not git-ignored**. It ALLOWS:

- git-ignored paths in the main checkout: `task_plan.md`, `findings.md`, `progress.md`, `.agent/**`;
- paths inside any linked worktree, for example `.claude/worktrees/<name>/…`;
- paths outside any repository;
- every call from a non-coordinator session (lanes, Ray's interactive sessions).

The deny reason must name the fix: "EnterWorktree name=<branch-slug>, then edit the worktree copy".

## 2. Files

- NEW `python/src/dotfiles_setup/coordinator_write_guard.py`
- `python/src/dotfiles_setup/hook_guard.py`: wire it into `decide_payload` (~:1076-1097) and pass `session_id` through from the root payload in `pretooluse_main` (~:1104-1109).
- `python/src/dotfiles_setup/hook_dispatch.py:55`: pass `session_id` through the same way.
- NEW `tests/test_coordinator_write_guard.py`
- `.claude/skills/coordinator-handoff/SKILL.md` and its mirror `.agents/skills/coordinator-handoff/SKILL.md`: regenerate the mirror with `mise run skills-mirror`, never by hand. Add one sentence: the guard confines coordinator writes in the main checkout to ignored paths.
- `docs/specs/coordinator-bgisolation-2026-10-03.md`: add a line pointing at this spec.

## 3. Interfaces

```python
# coordinator_write_guard.py
def handles(tool_name: str) -> bool: ...  # Edit / Write / NotebookEdit
def decide(tool_input: dict[str, object], session_id: str | None,
           *, jobs_dir: Path | None = None) -> str | None: ...  # deny reason or None
```

- `decide_payload(tool_name, tool_input, session_id: str | None = None)`. The new parameter is keyword-compatible, and existing callers and tests stay valid.
- Order inside the file-tool branch (Revision 3, after the #1638 review): `coordinator_write_guard.decide(...) or branch_guard.decide(...) or script_guard.decide(...)` — coordinator first, because branch_guard's remedy (`git checkout -b`) would switch the shared main checkout's branch. The identity lookup sits inside the guard's `try`, so a malformed job record allows and the later guards still run.
- Coordinator identity: `coordinator_handoff.is_coordinator(session_common.session_name(session_id, jobs_dir or session_common.default_jobs_dir()))`. If that would create an import cycle, import `COORDINATOR_NAME_RE` or move `is_coordinator` to `session_common`; say which in the report.
- "Main checkout" means the target's repository top-level, with `git rev-parse --git-dir` equal to `--git-common-dir` (resolved). Equivalently, the target is NOT in a linked worktree. Reuse `branch_guard` helpers (`_probe_dir`, `_git_capture`, `is_ignored`) where you can, rather than duplicating them.
- The target path comes from `tool_input["file_path"]` or `["notebook_path"]`, the same as `branch_guard._target`.

## 4. Constraints and invariants

- **Fail OPEN on every unresolvable step:** no session id, unreadable job record, git failure. This matches `branch_guard`. Ray's interactive sessions have no job record and must never be blocked. Name this residual risk in a module docstring: a coordinator whose job record cannot be read is not confined.
- Cost per call: one jobs-record JSON read, plus at most TWO git invocations. Short-circuit on a non-coordinator BEFORE any git call.
  - Call 1 is a combined `rev-parse` for topology.
  - Call 2 is `git check-ignore -q -- <path>`. It runs only when the target is in the main checkout.
  - Revision 2, after licensed dissent from run 98cb69e7: `check-ignore` cannot be combined with `rev-parse` (rc 129).
  - Read `check-ignore` as THREE states. rc 0 means ignored, so allow. rc 1 means not ignored, so DENY. Any other rc, OSError or timeout means fail OPEN, so allow.
  - Do NOT reuse `branch_guard.is_ignored` for this decision. It maps errors to False ("not ignored"), which in this guard would turn a git error into a deny.
- No inline lint suppressions. Zero-bash logic.
- Do not change `branch_guard` behaviour or its tests.
- Do not change `.claude/settings.json`; the hook is already wired via `scripts/pretooluse-guard.sh`, matcher `…|Edit|Write|NotebookEdit|…`.
- Measured fact that bounds identity (cold-reviewer memory, 2026-10-03): an Agent-tool subagent's calls carry the PARENT session's id. A coordinator's subagents are therefore confined too. That is intended.
- COMMIT: caller.

## 5. Verification

Real git repos in tmp_path: a main checkout, a linked worktree made with `git worktree add`, and a `.gitignore` containing `/task_plan.md` and `.agent/`. Fake job records go in a tmp jobs dir, `<id8>/state.json` with `{"sessionId": …, "name": …}`.

- Coordinator plus tracked main-checkout file → DENY.
- Coordinator plus `task_plan.md` → allow.
- Coordinator plus `.agent/plans/x.md` → allow.
- Coordinator plus a linked-worktree file → allow.
- Coordinator plus an outside-repo path → allow.
- Coordinator plus a tracked main file when `check-ignore` errors (rc 128, simulated through the git runner seam) → allow, fail open.
- Lane name (`dotfiles-…L1-docs-rules`) plus tracked main file → allow.
- No record or no session id → allow.
- `decide_payload("Write", …, session_id=coord)` → deny, end to end.
- Mutation arm: delete the `decide_payload` wiring line and confirm the end-to-end test fails.
- Run `uv run --project python pytest tests/test_coordinator_write_guard.py tests/test_branch_guard.py tests/test_script_guard.py tests/test_ask_quality.py -q` and get rc 0.
- Run `mise run lint-docs` and get rc 0.

## 6. Commit

`caller`.

## 7. PREMISES

| # | Kind | Claim | Source |
|---|---|---|---|
| P1 | I | `decide_payload(tool_name, tool_input)` dispatches file tools to `branch_guard.decide(...) or script_guard.decide(...)` | `python/src/dotfiles_setup/hook_guard.py:1076-1097` |
| P2 | I | `parse_payload` returns `(tool_name, tool_input, root_payload)`, and `pretooluse_main` discards the root | `hook_guard.py:1039`, `:1108-1109` |
| P3 | I | `hook_dispatch` calls `hook_guard.decide_payload(tool_name, tool_input)` | `python/src/dotfiles_setup/hook_dispatch.py:55` |
| P4 | I | `session_name(session_id, jobs_dir)` returns the job's name or None; `job_record` trusts only an exact `sessionId` match | `python/src/dotfiles_setup/session_common.py:71-85` |
| P5 | L | `COORDINATOR_NAME_RE = ^dotfiles-.+\.coordinator$`; `is_coordinator(name)` | at authoring: `python/src/dotfiles_setup/coordinator_handoff.py:74`, `:200-202`; since #1633 both live in `session_common.py` |
| P6 | I | `branch_guard` helpers `_probe_dir`, `_git_capture`, `is_ignored(path, root)`, `_target`; it fails open | `python/src/dotfiles_setup/branch_guard.py:82-170`, `:274-293` |
| P7 | L | Hook stdin carries `"session_id"` at the root of the payload | `knowledge-base/sources/agent-harness-docs/docs/claude-code/hooks.md:780` |
| P8 | L | `/task_plan.md` is gitignored | `.gitignore:144` |
