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
2. Steps 1-3 share one attended session; every later step gets a fresh session. An optional
   Codex review runs in its own tab, never in the author's session. One ticket per worker, one
   git worktree per worker.
3. State lives in GitHub: issues, labels, assignees and blocked-by links. The roadmap and the ticket
   plans mirror it and hold working notes.
4. A review finding is a hypothesis to check against the diff. No review is required (owner ruling,
   2026-11-17); a lead may ask Codex for one by choice (see [cross-review](cross-review.md)).
5. Every loop has a cap. No review runs "until clean": three rounds per review kind, then park.
6. A mechanical mistake that recurs becomes a deterministic check; judgement calls stay in the
   repository's coding standards.
7. Workers never write to GitHub and never commit. They leave their changes in the worktree, write
   the proposed commit message to a file and stop.
8. Spend is tracked across a ticket, not only per loop. While a person is watching, money limits are
   advisory; an external spend limit is set and verified before anything runs unattended.
9. Text is checked for private content before it is published, not after. The home-path scan
   finds only the home-path strings it is configured with; a clean scan says nothing else about the
   content. The author reads the exact bytes for private content before publishing them.
10. A lead merges its own pull request with its repository's merge command (owner ruling,
    2026-11-15); the owner merges anything else.
11. Each agent step starts in a herdr-app tab: Codex as `codex-hc`, Claude through its launcher,
    both opened with `herdr-app do tab.new` and driven with `hc send`, `hc keys` and `hc read`.
    Inside that session, subagents and subagent teams are allowed (built-in `/simplify`, a
    fresh-context review subagent). Never start an agent step with `claude -p`, `codex exec`, the
    non-interactive `codex review` or `hc run`. A task (not an agent step) may make one one-shot
    model call when it sets a spend cap, restricts the model's tools and has a fallback for when the
    call fails (owner ruling, 2026-11-17). If `herdr-app ls` fails, stop and ask the owner. Close a
    tab when its step is done.
12. Every public write (docs, a commit, a spec, a ticket, pull-request text, an edit or a comment)
    is sent only after the home-path scan and the author's own read of the exact bytes for private
    content, plus the owner's OK where a step asks for it. The order is push, open the pull
    request, merge.
13. A step is done on an observed result: the verify output, a passing test run, a finding checked
    against the diff. A read that failed is reported as unreadable, never as "nothing found".

## The chain

Before the first ticket in a repository, `/work` runs setup once: `setup-matt-pocock-skills`, then a
`## Workflow facts` section (see [skills](skills.md)).

| # | Step | Who starts it | Produces | Person's gate | Review |
|---|------|---------------|----------|---------------|--------|
| 1 | `/grill-with-docs` | The owner, in a fresh session | Shared understanding, glossary terms, ADRs | Confirms the summary | None required |
| 2 | `/to-spec` | The owner, same session | One spec issue | Signs off the spec | Optional document review of the local file before it is published |
| 3 | `/to-tickets` | The owner, same session | Vertical-slice ticket issues, blockers first, each with seams and criteria that can fail | Approves the breakdown | Optional document review of the ticket bodies |
| 4 | `/implement owner/repo#N` | The owner or coordinator, one worker tab per ticket | Changes in the worker's worktree, tests first at the agreed seams | None: commits need no approval | None required |
| 5 | Branch review (optional) | A Codex tab, when the lead asks for one | Findings against the acceptance criteria | None: findings are hypotheses | Optional: the base-branch diff with the criteria supplied |
| 6 | `/pr` | The worker writes the body to a file | Title and body: summary, evidence, merge danger, blast radius | None | Home-path scan and the author's read of the diff and the text for private content |
| 7 | Close-out | The coordinator, after the lead merges (or earlier on a shared branch, see [ship](ship.md)) | Issue closed, roadmap line ticked; worktree removed only after the merge | The merge, or a spec's early-close rule in [ship](ship.md) | None |
| 8 | `/ticket-retro` | The owner | Lessons for the ticket plan; changes as normal pull requests | Approves any change | As any pull request |

`/implement-spec` runs step 4 for every open ticket of a spec, frontier first. Off the chain:
`triage` is for issues other people filed; `diagnosing-bugs` replaces step 1 for a bug;
`wayfinder` comes before step 2 when the work spans many sessions.

## Plans

The roadmap lives in the main checkout; ticket plans live in a sibling `<repo>.plans/` folder,
outside every checkout. The coordinator creates each plan and is the only one who writes the
roadmap. A worker starts with `PLAN_ID` set to its plan and never re-creates it.
