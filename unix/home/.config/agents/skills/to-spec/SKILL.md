---
name: to-spec
description: "Use when the owner says /to-spec or asks to turn the current conversation into a spec: synthesize it into one spec issue on GitHub, published only after the home-path scan, the reviewer's leak check and the owner's approval of its exact text."
disable-model-invocation: false
---

This skill takes the current conversation context and codebase understanding and produces a spec. Do NOT interview
the owner; just synthesize what you already know. It is step 2 of the agent workflow
(`~/.config/agents/workflow/workflow.md`).

## Departures from upstream

Adapted from mattpocock-skills 1.3.2 `to-spec` (MIT, `../LICENSE`).

- The spec is published only after the home-path scan, the reviewer's leak check and the owner's approval of its
  exact text. Until then it stays a local file.
- The tracker is GitHub Issues; another tracker stops the skill.
- A new project runs `setup-matt-pocock-skills` first.
- It calls `workflowtools tickets`, never a repository path. The coordinator creates plans and is the only writer
  of the roadmap in the main checkout.

## Before you start

Stop, publishing nothing, and tell the owner why, when any of these fails:

- The root `AGENTS.md` or `CLAUDE.md` has an `## Agent skills` section naming GitHub Issues as the tracker. If it
  has none, ask the owner to run `/setup-matt-pocock-skills`. If it names another tracker, say this skill only
  publishes GitHub issues.
- `workflowtools` and `repotools` are on `PATH` (`command -v`). If not, ask the owner to run
  `mise run //repo:tools-install` from dotfiles.
- `git remote get-url origin` names a GitHub repository.

## Process

1. Explore the repo to understand the current state of the codebase, if you haven't already. Use the project's
   domain glossary vocabulary throughout the spec, and respect any ADRs in the area you're touching.

2. Sketch out the seams at which you're going to test the feature. Existing seams should be preferred to new ones.
   Use the highest seam possible. If new seams are needed, propose them at the highest point you can. The fewer
   seams across the codebase, the better - the ideal number is one.

   Check with the owner that these seams match their expectations.

3. Write the title and the spec, using the template below, to a file outside every checkout. Then:
   1. **Home-path scan.** `repotools privacy-scan --patterns="$HOME" --files=<spec file>` must exit 0. A clean scan
      only means no home path; it is not the leak check.
   2. **Leak check.** Ask the reviewer pane (`~/.config/agents/workflow/cross-review.md`) for a document review of
      the file that includes the leak check. Fix what it finds and repeat from the scan.
   3. **Approval.** Show the owner the exact title and file text with `git hash-object <spec file>`, and ask for
      approval of that text. Without an explicit yes, stop: the spec stays local.
   4. **Publish.** Check that `git hash-object <spec file>` still prints the approved hash; if not, start again at
      the scan. Then run
      `gh issue create --title "<title>" --body-file <spec file> --label ready-for-agent` and show the owner the
      issue URL.

4. **Roadmap.** Only the coordinator writes it: this session, unless the owner names another one (then send it the
   spec's number and stop). Add the output of `workflowtools tickets --rebuild --spec <N>` as the spec's section of
   the roadmap, `task_plan.md` in the main checkout (`git worktree list`, first line). Then
   `workflowtools tickets --spec <N> --require-github` must exit 0; if not, show its output and stop.
   `/to-tickets` comes next, in the same session.

<spec-template>

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A LONG, numbered list of user stories. Each user story should be in the format of:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
</user-story-example>

This list of user stories should be extremely extensive and cover all aspects of the feature.

## Implementation Decisions

A list of implementation decisions that were made. This can include:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do NOT include specific file paths or code snippets. They may end up being outdated very quickly.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it within the relevant decision and note briefly that it came from a prototype. Trim to the decision-rich parts, not a working demo, just the important bits.

## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)

## Out of Scope

A description of the things that are out of scope for this spec.

## Further Notes

Any further notes about the feature.

</spec-template>
