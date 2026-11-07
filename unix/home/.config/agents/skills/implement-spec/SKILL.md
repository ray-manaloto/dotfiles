---
name: implement-spec
description: "Build every open ticket of a spec, frontier first: one pinned implement worker per ticket, each in its own worktree and plan; nothing is committed."
disable-model-invocation: false
---

You have a spec whose tickets form a **task graph**: blockers first, so there is always a **frontier** of ready
tickets. You start one **worker** per frontier ticket and collect what each hands back. The workflow is
`~/.config/agents/workflow/index.md`.

## Before you start

Check these in order. If one fails, stop: tell the owner which one and show the command's output. Write nothing.

1. **A worktree.** `git rev-parse --path-format=absolute --git-dir --git-common-dir` must print two different
   paths. The spec is built on an integration branch in its own worktree, never in the main checkout.
2. **A plan.** `PLAN_ID` must be set and `workflowtools tickets --plan` must print a `plan` line. That command
   fails when `PLAN_ID` is unset, on no roadmap line, or has no `task_plan.md` in the plans folder.
3. **The spec.** You are given one spec issue number, `<N>`. `workflowtools tickets --spec <N> --listing frontier`
   must succeed; it lists only that spec's tickets. Read the spec issue and its tickets with `gh issue view`.

## Steps

1. Read your plan's `task_plan.md`, `findings.md` and `progress.md` (the `path` in the `plan` line). Update only
   those files. Never write the roadmap or a worker's plan.
2. For each frontier ticket, ask the coordinator for its worktree on the integration branch and its plan.
   Workers need both before they start; you do not create either.
3. Start each worker as the workflow says: a herdr-app tab in its worktree, with its `PLAN_ID` set, running
   `/implement <owner/repo>#<number>`. Communicate through pointers: the spec, the ticket, the plan folder.
4. When a worker hands back staged changes, its commit goes through that worktree's reviewer pane
   (`~/.config/agents/workflow/ship.md`). You do not commit, merge or write to GitHub.
5. When the coordinator reports the frontier changed, start workers for the new tickets.
6. Stop and report: each ticket, its worktree, what it handed back, and what is still blocked. Close every tab
   you opened.

## Departures from upstream

Adapted from mattpocock-skills 1.3.2 `implement-spec` (MIT, see `../LICENSE`).

- Each ticket is one `implement` worker in its own worktree and plan, started in a herdr-app tab; upstream uses
  background subagents.
- Pinned to an existing plan by `PLAN_ID`; the coordinator creates every plan and worktree.
- Never writes the roadmap; the coordinator is its only writer.
- Never commits or merges: workers stage and hand back, and commits go through the reviewer pane. Upstream
  merges each ticket into the integration branch and opens a pull request.
- Model-invocable (`disable-model-invocation: false`); upstream is user-only.
- Stops when a prerequisite is missing: no worktree, no `PLAN_ID`, no plan.
