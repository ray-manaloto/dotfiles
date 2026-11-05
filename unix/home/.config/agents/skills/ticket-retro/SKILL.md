---
name: ticket-retro
description: "Conduct a retrospective on a finished ticket or spec and record what it taught in the ticket plan. Started by the owner only."
disable-model-invocation: true
---

The owner has asked for a **retrospective** on a finished ticket or spec. You are suggesting improvements to the
coding agent's **environment** to improve future runs. You propose changes and record the ones the owner keeps in
the ticket plan; you change nothing else yourself.

## Before you start

Stop and tell the owner what is missing, without reading the sources or writing anything, when:

- `workflowtools` is not on PATH (it is installed by `mise run //repo:tools-install` from a dotfiles checkout);
- `PLAN_ID` is not set, or `workflowtools tickets --plan` exits non-zero: print its finding;
- the ticket or spec the owner named is not a GitHub issue of this repository (`gh issue view <N>` fails);
- the plan is for another issue: the `issue` and the repository in `url` of the `PlanResolved` line that
  `workflowtools tickets --plan` prints differ from the number and repository of the issue the owner named. Print
  both and stop.

## Steps

1. Call the Skill tool with `writing-for-agents` for the writing style guide.

2. Read the primary sources for the ticket or spec the owner names: its issue, its plan's `task_plan.md`,
   `findings.md` and `progress.md` (the folder `workflowtools tickets --plan` prints), its pull requests and their
   review comments, and the session logs on this machine. If the owner names no session, default to the current one.

3. Look for candidates for improvement in these categories.

- **Navigation**: how easy was it for the agent to find the right files? Are there hidden dependencies between files? Would a **navigation pointer** make it easier? _Use when_ the session took a long time to find a piece of information.
- **Automated checks**: are there automated checks that could catch errors the agent made? Linting, typing, tests, filesystem linters? Read the repo's own check command first (its `package.json`/build-tool `lint`/`check` scripts, its CI workflow), so a check that already exists but sits unwired or silently broken is the finding, not a reinvention. A repo with no **guardrail** (no pre-commit hook and no CI job running its lint/typecheck/test command) is itself a finding: an un-linted repo is a standing missed opportunity, not a neutral default. _Use when_ the agent made a mistake an automated check could have caught, or the repo has no guardrail at all.
- **Coding standards**: should the **reviewer agent** be given a new rule to enforce? Should an existing rule be removed or clarified? Classify the violation first: a **mechanical** one (a fixed syntactic pattern, a banned API, an import shape, a file-location rule) gets a deterministic check, full stop: a custom rule in the repo's own linter, a new pre-commit hook, or a new CI job, whichever the repo's language and existing guardrail make cheapest. Default to building the check over writing the rule. Reserve `CODING_STANDARDS.md` for genuine **judgement calls** (cross-file consistency, "matches the surrounding style," anything no guardrail could ever substitute for). _Use when_ the reviewer agent failed to catch a mistake.
- **Global AGENTS.md**: are there any steering instructions that should be moved to coding standards (or automated checks) instead? _Use when_ the AGENTS.md file is particularly large - in the repo OR the user's global scope.
- **Tool economy**: did the agent make expensive tool calls that could be streamlined? Is there any custom tooling (CLI's, MCP's) that is particularly token-inefficient? _Use when_ the agent made an expensive tool call.
- **No-ops**: look for instructions in steering files that don't modify the agent's behavior. _Use when_ the steering files are large and unwieldy.
- **Information access**: look for opportunities to increase the agent's access to information. Teeing dev server logs, readonly access to third-party services. _Use when_ a crucial piece of information was not available to the agent.

4. Present these candidates to the owner, in order of severity.

5. Record the ones the owner keeps under a `## Retro <YYYY-MM-DD>` heading at the end of the plan's `findings.md`,
   one bullet each: the category, what happened, and the proposed change. Add one line to `progress.md`:
   `ticket-retro: <n> lessons recorded`. Write nothing else.

## Departures from upstream

- The output goes to the ticket plan, not to the conversation only.
- Only the owner starts it (`disable-model-invocation: true`, and `allow_implicit_invocation: false` for Codex).
- A change it proposes is made later as a normal pull request, through the usual pane approval. ticket-retro itself
  edits no file outside the plan's `findings.md` and `progress.md`, makes no commit, and opens no issue or pull
  request.
- Nothing it writes is published without the home-path scan, the reviewer's leak check and approval on the exact
  bytes (workflow.md rule 12).
- Tickets and specs are GitHub issues. The plan is found by `workflowtools tickets --plan`, and must be the plan of
  the issue the owner named.

## Reference

### Implementation vs Review

Remember that all work goes through two stages: implementation and review. The implementation agent has the most **context pressure**. They are responsible for exploration, writing code, and debugging failures.

The review agent has the least context pressure - it receives a diff, so no exploration needed. It often does not need to write code or debug.

This means that the review agent should be responsible for imposing coding standards, not the implementation agent.

### Files

You have access to several files in the repo:

- `CLAUDE.md`/`AGENTS.md`: these files are pushed to the context window of any agent working in this repo. They should be used incredibly sparingly, usually only for **navigation pointers** to other files.
- `CODING_STANDARDS.md`: this file is read during review, not implementation. Add **navigation pointers** to docs folders if the standards file gets more than 1,000 lines long.
- Docs: use docs as references files, pointed to by other files. Look for existing docs before writing new ones.
- Skills: use skills for docs (since their description goes into the agent's context window), or for user-invoked commands. Follow the advice in the `writing-for-agents` skill.
