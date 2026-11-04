---
okf_version: "0.2"
type: "process"
title: "The agent workflow"
description: "The rules and the eight steps that take an idea to a merged pull request."
timestamp: "2026-11-04T00:00:00Z"
status: "current"
tags: [workflow]
---

# The agent workflow

## Rules

1. People do the thinking steps: grilling, spec sign-off, ticket approval and the merge. Agents do
   the mechanical steps: implementing, reviewing and drafting pull request text.
2. Steps 1-3 share one attended session; every later step gets a fresh session. Reviews run in
   the worktree's pinned reviewer pane, never in the author's session. One ticket per worker, one
   git worktree per worker.
3. State lives in GitHub: issues, labels, assignees and blocked-by links. The roadmap and the ticket
   plans mirror it and hold working notes.
4. A review finding is a hypothesis to check against the diff, never an approval. The only approval
   is the reviewer pane's `PANE-APPROVE <fingerprint>` (see [cross-review](cross-review.md)).
5. Every loop has a cap. No review runs "until clean": three rounds per review kind, then park.
6. A mechanical mistake that recurs becomes a deterministic check; judgement calls stay in the
   repository's coding standards.
7. Workers never write to GitHub and never commit. They leave their changes in the worktree, write
   the proposed commit message to a file and stop.
8. Spend is tracked across a ticket, not only per loop. While a person is watching, money limits are
   advisory; an external spend limit is set and verified before anything runs unattended.
9. Text is scanned for private content before it is published, not after.
10. Merges stay human. No agent merges a pull request.
11. Each step starts in a herdr-app tab: Codex as `codex-hc`, Claude through its launcher, both
    opened with `herdr-app do tab.new` and driven with `hc send`, `hc keys` and `hc read`. Inside
    that session, subagents and subagent teams are allowed (built-in `/simplify`, a fresh-context
    review subagent). Never start a step with `claude -p`, `codex exec`, the non-interactive
    `codex review` or `hc run`. If `herdr-app ls` fails, stop and ask the owner. Close a tab when
    its step is done.
12. Every public write (an issue, a pull request, an edit or a comment) is sent only after a private
    content scan and an approval on the exact bytes. Without approval the item stays local.
13. A step is done on an observed result: the verify output, a passing test run, a finding checked
    against the diff. A read that failed is reported as unreadable, never as "nothing found".

## The chain

Before the first ticket in a repository, `/work` runs setup once: `setup-matt-pocock-skills`, then a
`## Workflow facts` section and the approval hook (see [skills](skills.md)).

| # | Step | Who starts it | Produces | Person's gate | Review |
|---|------|---------------|----------|---------------|--------|
| 1 | `/grill-with-docs` | The owner, in a fresh session | Shared understanding, glossary terms, ADRs | Confirms the summary | Uncommitted-changes review if files changed |
| 2 | `/to-spec` | The owner, same session | One spec issue | Signs off the spec | Document review of the local file before it is published |
| 3 | `/to-tickets` | The owner, same session | Vertical-slice ticket issues, blockers first, each with seams and criteria that can fail | Approves the breakdown | Optional document review of the ticket bodies |
| 4 | `/implement owner/repo#N` | The owner or coordinator, one worker tab per ticket | Changes in the worker's worktree, tests first at the agreed seams | Reviewer pane approves each commit | Uncommitted-changes review before each commit |
| 5 | Branch review | The reviewer tab, after the ticket's commits | Findings against the acceptance criteria | None: findings are hypotheses | Base-branch review with the criteria supplied |
| 6 | `/pr` | The worker writes the body to a file | Title and body: summary, evidence, merge danger, blast radius | Reviewer pane approves the exact bytes | Private-content scan, then a document review |
| 7 | Close-out | The coordinator, after the owner merges | Issue closed, roadmap line ticked, worktree removed | The merge itself | None |
| 8 | `/retro` | The owner | Lessons for the ticket plan; changes as normal pull requests | Approves any change | As any pull request |

`/implement-spec` runs step 4 for every open ticket of a spec, frontier first. Off the chain:
`triage` is for issues other people filed; `diagnosing-bugs` replaces step 1 for a bug;
`wayfinder` comes before step 2 when the work spans many sessions.

## Plans

The roadmap lives in the main checkout; ticket plans live in a sibling `<repo>.plans/` folder,
outside every checkout. The coordinator creates each plan and is the only one who writes the
roadmap. A worker starts with `PLAN_ID` set to its plan and never re-creates it.
