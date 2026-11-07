---
name: to-tickets
description: "Use when the owner says /to-tickets or asks to split a spec issue into tickets: tracer-bullet GitHub issues, blockers first, each published only after the home-path scan, the reviewer's leak check and the owner's approval of its exact text, then given its plan and roadmap line."
disable-model-invocation: false
---

# To Tickets

Break a spec issue into a set of **tickets**: tracer-bullet vertical slices, each declaring the tickets that
**block** it. It is step 3 of the agent workflow (`~/.config/agents/workflow/workflow.md`).

## Departures from upstream

Adapted from mattpocock-skills 1.3.2 `to-tickets` (MIT, `../LICENSE`).

- Tickets are GitHub issues, sub-issues of the spec, with native blocked-by links. There is no local-files form.
- Each ticket is published only after the home-path scan, the reviewer's leak check and the owner's approval of
  its exact text. Until then it stays a local file.
- The coordinator creates each ticket's plan in the sibling plans folder and is the only writer of the roadmap in
  the main checkout.
- A new project runs `setup-matt-pocock-skills` first.
- It calls `workflowtools tickets`, never a repository path.

## Before you start

Stop, publishing nothing, and tell the owner why, when any of these fails:

- The root `AGENTS.md` or `CLAUDE.md` has an `## Agent skills` section naming GitHub Issues as the tracker. If it
  has none, ask the owner to run `/setup-matt-pocock-skills`. If it names another tracker, say this skill only
  publishes GitHub issues.
- `workflowtools` and `repotools` are on `PATH` (`command -v`). If not, ask the owner to run
  `mise run //repo:tools-install` from dotfiles.
- The spec is a GitHub issue and `workflowtools tickets --spec <N> --require-github` exits 0. If not, show its
  output: the spec needs its roadmap section first (`/to-spec`, step 4).

## Process

### 1. Gather context

Work from whatever is already in the conversation context. Read the spec issue's full body and comments.

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code. Ticket titles and descriptions should use the project's domain glossary vocabulary, and respect ADRs in the area you're touching.

Look for opportunities to prefactor the code to make the implementation easier. "Make the change easy, then make the easy change."

### 3. Draft vertical slices

Break the work into **tracer bullet** tickets.

<vertical-slice-rules>

- Each slice cuts a narrow but COMPLETE path through every layer (schema, API, UI, tests): vertical, NOT a horizontal slice of one layer
- A completed slice is demoable or verifiable on its own
- Each slice is sized to fit in a single fresh context window
- Any prefactoring should be done first

</vertical-slice-rules>

Give each ticket its **blocking edges**: the other tickets that must complete before it can start. A ticket with no blockers can start immediately. Name the seams it is tested at, and acceptance criteria that can fail.

**Wide refactors are the exception to vertical slicing.** A **wide refactor** is one mechanical change (rename a column, retype a shared symbol) whose **blast radius** fans across the whole codebase, so a single edit breaks thousands of call sites at once and no vertical slice can land green. Don't force it into a tracer bullet; sequence it as **expand–contract**. First expand: add the new form beside the old so nothing breaks. Then migrate the call sites over in batches sized by blast radius (per package, per directory), each batch its own ticket blocked by the expand, keeping CI green batch to batch because the old form still exists. Finally contract: delete the old form once no caller remains, in a ticket blocked by every migrate batch. When even the batches can't stay green alone, keep the sequence but let them share an integration branch that all block a final integrate-and-verify ticket; green is promised only there.

### 4. Quiz the owner

Present the proposed breakdown as a numbered list. For each ticket, show:

- **Title**: short descriptive name
- **Blocked by**: which other tickets (if any) must complete first
- **What it delivers**: the end-to-end behaviour this ticket makes work

Ask the owner:

- Does the granularity feel right? (too coarse / too fine)
- Are the blocking edges correct: does each ticket only depend on tickets that genuinely gate it?
- Should any tickets be merged or split further?

Iterate until the owner approves the breakdown.

### 5. Publish the tickets

Write each ticket body, using the template below, to its own file outside every checkout, and its exact title to
a `.title` file beside it. Steps 1-4 cover both files of every ticket. Then, for all of them:

1. **Home-path scan.** `repotools privacy-scan --patterns="$HOME" --files="<ticket file> <title file>"` must exit 0.
   A clean scan only means no home path; it is not the leak check.
2. **Leak check.** Ask the reviewer pane (`~/.config/agents/workflow/cross-review.md`) for a document review of the
   files that includes the leak check. Fix what it finds and repeat from the scan.
3. **Approval.** Show the owner each exact title and body with `git hash-object <title file> <ticket file>`, and ask for
   approval of that text. Without an explicit yes, stop: the tickets stay local.
4. **Publish** in dependency order, blockers first, so each blocked-by can name a real issue number. Before each
   one, check that `git hash-object <title file> <ticket file>` still prints the approved hashes; if not, start again at the scan.
   ```
   gh issue create --title "<the title file's text>" --body-file <ticket file> --label ready-for-agent \
     --parent <spec number> --blocked-by <issue numbers, comma-separated; omit when none>
   ```

Do NOT close or modify the spec issue.

### 6. Plans and roadmap

Only the coordinator does this step: this session, unless the owner names another one (then send it the new issue
numbers and stop).

1. For each new ticket, create its plan folder `<main checkout>.plans/.planning/<YYYY-MM-DD>-<slug>/` (the main
   checkout is the first line of `git worktree list`; `PWF_PLAN_ROOT`, when set, replaces `<main checkout>.plans`).
   Its `task_plan.md` starts `# Task Plan: #<number> <title>` and its `## Goal` is the line
   `Implement <issue URL>`. Never re-create a plan that exists.
2. Replace the spec's section of the roadmap with the output of `workflowtools tickets --rebuild --spec <N>`: one
   line per ticket, with its issue link, `PLAN_ID` and blockers.
3. `workflowtools tickets --spec <N> --require-github --listing frontier` must exit 0. Show the owner the frontier.

<issue-template>

## Parent

#<spec number>

## What to build

The end-to-end behaviour this ticket makes work, from the user's perspective, not layer-by-layer implementation.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2

</issue-template>

Blockers are native blocked-by links, so the body has no "Blocked by" section.

Avoid specific file paths or code snippets: they go stale fast. Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it and note briefly that it came from a prototype. Trim to the decision-rich parts, not a working demo, just the important bits.
