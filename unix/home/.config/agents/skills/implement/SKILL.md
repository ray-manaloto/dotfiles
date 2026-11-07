---
name: implement
description: "Build one ticket in this worktree, pinned to its existing plan by PLAN_ID; stage the changes and hand back without committing."
disable-model-invocation: false
---

You are a **worker**. You build one ticket in your own git worktree, in your own plan, and hand the staged
changes back. The workflow is `~/.config/agents/workflow/index.md`.

## Before you start

Check these in order. If one fails, stop: tell the owner which one and show the command's output. Write nothing.

1. **A worktree.** `git rev-parse --path-format=absolute --git-dir --git-common-dir` must print two different
   paths. The same path means the main checkout: the coordinator gives each worker its own worktree.
2. **A plan.** `PLAN_ID` must be set and `workflowtools tickets --plan` must print a `plan` line. That command
   fails when `PLAN_ID` is unset, on no roadmap line, or has no `task_plan.md` in the plans folder.
3. **The ticket.** The `issue` in that line is your ticket. If the owner named a different one, stop. Fetch it
   with `gh issue view` and state its title.

## Steps

1. Read your plan's `task_plan.md`, `findings.md` and `progress.md` (the `path` in the `plan` line). Update only
   those files. Never write the roadmap (`task_plan.md` in the main checkout) or another worker's plan.
2. Call the Skill tool with "tdd" where possible, at the ticket's agreed seams.
3. Run typechecking regularly, single test files regularly, and the repository's check command (`## Workflow
   facts` in `AGENTS.md`) once at the end.
4. Call the Skill tool with "code-review" to review the work. Fix what it finds that the diff confirms.
5. Stage everything with `git add`. Write the proposed commit message to a file outside the repository.
6. Stop and report: the staged files, the message file, the check result and anything left open. You do not
   commit, push or write to GitHub; the commit goes through the reviewer pane
   (`~/.config/agents/workflow/ship.md`).

## Departures from upstream

Adapted from mattpocock-skills 1.3.2 `implement` (MIT, see `../LICENSE`).

- One ticket per worker, in its own worktree; upstream takes a spec or a set of tickets in any checkout.
- Pinned to an existing plan by `PLAN_ID`, resolved by `workflowtools tickets --plan`; the worker never creates
  a plan.
- Never writes the roadmap; the coordinator is its only writer.
- Never commits: it stages and hands back. Upstream commits to the current branch.
- Model-invocable (`disable-model-invocation: false`); upstream is user-only.
- Stops when a prerequisite is missing: no worktree, no `PLAN_ID`, no plan.
