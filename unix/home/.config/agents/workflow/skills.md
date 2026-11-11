---
okf_version: "0.2"
type: "reference"
title: "Skills the workflow uses"
description: "The six workflow skills, and every mattpocock-skills skill with who may start it, pinned to the plugin commit installed at user scope."
package: "github:mattpocock/skills"
version: "1.3.2"
upstream_commit: "4ae2317ddb22b046e26455e4f9c9b3aaaf62212d"
timestamp: "2026-11-04T00:00:00Z"
status: "current"
tags: [workflow, skills, mattpocock-skills]
---

# Skills the workflow uses

## The six workflow skills

They live at user scope only (`~/.claude/skills/` and `~/.agents/skills/`), linked from
`~/.config/agents/skills/`. A repository keeps no project-scope copy: Claude Code and Codex both
load two skills that share a name, and Codex then ignores a bare mention of either.

| Skill | Started by | What it does |
|---|---|---|
| `work` | the owner or an agent | Picks the next ready ticket and drives it to a pull request; sets a repository up first when it has no Workflow facts. |
| `to-spec` | the owner or an agent | Turns a settled conversation into a spec issue. |
| `to-tickets` | the owner or an agent | Splits a spec issue into ticket issues, each with one task-plan line. |
| `implement` | the owner or an agent | Builds one ticket in its own worktree and plan. |
| `implement-spec` | the owner or an agent | Builds every open ticket of a spec, frontier first. |
| `ticket-retro` | the owner or an agent | Records what a finished ticket or spec taught, in the ticket plan. |

`to-spec`, `to-tickets`, `implement` and `implement-spec` are adapted from the mattpocock-skills
skills of the same name, and `ticket-retro` from its `retro` (MIT; the license sits beside the
skills). `work` is this workflow's own. Each of the six sets `disable-model-invocation: false` in
its SKILL.md and `allow_implicit_invocation: true` in its `agents/openai.yaml`, so an agent may
start it as well as the owner.

## mattpocock-skills, as installed

The `upstream_commit` above is the user-scope install's commit. `workflowtools skill-table` fails
when the install moves: re-read the changed SKILL.md files, update this table and the adapted
skills, then move the pin. `user-only` means the SKILL.md sets `disable-model-invocation: true`, so
only the owner can start it.

| Skill | Who starts it |
|---|---|
| `ask-matt` | user-only |
| `code-review` | model |
| `codebase-design` | model |
| `diagnosing-bugs` | model |
| `domain-modeling` | model |
| `grill-me` | user-only |
| `grill-with-docs` | user-only |
| `grilling` | model |
| `handoff` | user-only |
| `implement` | user-only |
| `implement-spec` | user-only |
| `improve-codebase-architecture` | user-only |
| `pr` | model |
| `prototype` | model |
| `research` | model |
| `retro` | user-only |
| `setup-matt-pocock-skills` | user-only |
| `tdd` | model |
| `teach` | user-only |
| `to-questionnaire` | user-only |
| `to-spec` | user-only |
| `to-tickets` | user-only |
| `triage` | user-only |
| `wait-what` | user-only |
| `wayfinder` | user-only |
| `wizard` | model |
| `writing-for-agents` | model |
