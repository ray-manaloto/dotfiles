---
okf_version: "0.2"
type: "process"
title: "Shipping a change"
description: "The order of gates from a green test run to a merged pull request."
timestamp: "2026-11-04T00:00:00Z"
status: "current"
tags: [workflow, commit, pull-request]
---

# Shipping a change

## Before each commit, in this order

1. **Tests green.** Run the repository's test task and keep the result.
2. **Simplify.** One pass of built-in `/simplify` in the worker's tab. It may only touch files
   already in the change, and it changes either code or tests in one pass, never both. Re-run the
   same tests afterwards.
3. **Verify.** `/verify` over the working changes, the branch diff and the untracked files. It must
   end PASS, or SKIP for documentation only. FAIL and BLOCKED stop the ticket.
4. **Stage.** The coordinator or owner stages everything.
5. **Commit.** Write the message to a file and run `git commit -F <message file>`. No review is
   required, for a commit or a pull request (owner ruling, 2026-11-17).

The worker stops at steps 1-3 with its changes in the worktree and a proposed message file. Staging
and the commit belong to the coordinator or the owner.

## The pull request

1. `/pr` writes the title and body to a file: summary, evidence (how it was tested), merge danger
   (one-way or two-way door, and how to undo it) and blast radius.
2. Run the home-path scan on the title and body, and read the diff, every commit message and the
   text for private project content, claude.ai session links and home paths. A clean scan is not
   that check.
3. A Codex review is optional: a lead may ask for one by choice (see [cross-review](cross-review.md)).
4. Push the branch, then open the pull request with the repository's create command.
5. The lead merges its own pull request (owner ruling, 2026-11-15) once local hk checks pass on the exact
   head: `hk check --all`, or `hk check --pr` where hk.pkl runs every suite for a shared file (dotfiles). Hosted checks from free apps are advisory, and no paid CI is added. The merge is
   `gh pr merge N --merge --match-head-commit <sha> --author-email 1428022+sortakool@users.noreply.github.com`,
   so the merge commit carries the account's noreply address, not a personal email. A repository can
   check these gates in one task: dotfiles has `mise run //repo:pr-merge`.

## Close-out

After the merge: close the issue with a comment, tick the roadmap line, remove the
worktree, and recompute the frontier (a GitHub blocked-by link only drops when its blocker closes).

After a mise tool bump merges and local `main` fast-forwards, run `mise run roll:all`: sessions opened
earlier keep the old install on their PATH, and its plan lists them as stale. `--apply` stops and
resumes them so they load the new one; it stops other leads' sessions, so only the owner runs it.

A spec may let its tickets close earlier, on a shared branch, so the frontier can move before the
one pull request merges. Then a ticket closes only after its commits were pushed to the shared
branch on the remote and seen there. The closing comment names each commit and says it is
not merged yet. Those commits are never rewritten: later changes are new commits, and the pull
request merges with a merge commit, never squashed or rebased. On an early close, tick the roadmap
line and recompute the frontier, but keep the worktree until the merge. The spec stays open until
the merge. If the branch or pull request is abandoned, or later work undoes a ticket, reopen the
ticket and recompute the frontier.
