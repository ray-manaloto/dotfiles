---
okf_version: "0.2"
type: "process"
title: "Cross-review"
description: "Who reviews what, in which tab, and how review findings are handled."
timestamp: "2026-11-04T00:00:00Z"
status: "current"
tags: [workflow, review, codex]
---

# Cross-review

Claude writes the change; Codex reviews it, so the reviewer is a different model family and never
sees the author's transcript.

## The reviewer pane

One reviewer tab per worktree: `codex-hc -a never -s read-only`, opened as a herdr-app tab in that worktree.
Pin its session once with the repository's pane-pin command. Resume it only read-only
(`codex resume <id> -a never -s read-only`). Its last final answer must end `PANE-APPROVE <fingerprint>`;
that line, read from the session log by the repository's approval check, is the only approval.
Never read an approval from the screen. No hc template is needed: the pane is an ordinary tab.

## Three review kinds

| Kind | When | In the tab | Effort |
|------|------|------------|--------|
| Uncommitted changes | Before each commit | `/review` -> Review uncommitted changes | medium |
| Base branch | Before the pull request | `/review` -> Custom review instructions: the acceptance criteria and `git diff origin/<default>...HEAD` | high |
| Document | Specs, ticket bodies, pull-request text | A typed brief in a read-only tab | high |

Set the effort in the tab's argv (`-c model_reasoning_effort=...`); the session default may differ.

A document review brief names the file's absolute path and that it is read-only, then asks by
document type: a spec for gaps, untestable criteria, missing seams and contradictions with the
glossary and ADRs; ticket bodies for vertical slices, written seams and criteria that can fail;
pull-request text for accuracy against the diff and a merge danger rated too safe. Every document
review of public text, and every comment before it is posted, includes the leak check: private
content in the exact bytes blocks approval.

## Handling findings

1. Check each finding's file and line against the diff before acting on it.
2. Tag it Important (fix), Nit (note) or Pre-existing (not caused by this change; ticket it if real).
   Drop style-only findings. Report at most five Nits a round and count the rest.
3. P0-P2 are fixed or ticketed; P3 may be noted and skipped. Answer every finding in the ticket plan
   with a fix or a reason.
4. Call a second, different-family validator only for a P0-P2 finding the author disputes with
   evidence.
5. When a finding is one case of a class, fix the class.
6. Re-review only the fix. Three rounds per review kind, then park the ticket and tell the owner.
7. Findings never approve or block by themselves; the pane's approval does. Protected paths and CI
   workflow files always need the owner.

A supplementary fresh-context review subagent inside a session is allowed as an extra pass. It
never replaces the reviews above and counts against the ticket's review budget.
