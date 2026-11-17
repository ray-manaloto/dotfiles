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
   same tests afterwards. It never runs after the pull request's approval: an edit voids it.
3. **Verify.** `/verify` over the working changes, the branch diff and the untracked files. It must
   end PASS, or SKIP for documentation only. FAIL and BLOCKED stop the ticket.
4. **Stage.** The coordinator or owner stages everything.
5. **Language gate.** Where the repository has one (for example a Python reviewer that must end
   `VERDICT: PASS`), run it on the staged content in its own tab.
6. **Commit.** Write the message to a file and run `git commit -F <message file>`. Commits need no
   reviewer approval: the pull request's one review covers every commit in it.

The worker stops at step 1-3 with its changes in the worktree and a proposed message file. Staging
and the commit belong to the coordinator or the owner.

## The pull request

1. `/pr` writes the title and body to a file: summary, evidence (how it was tested), merge danger
   (one-way or two-way door, and how to undo it) and blast radius.
2. Run the home-path scan on the title and body. A clean scan is not a leak check.
3. One review in the reviewer tab: the whole branch diff against the base (every commit in it), the
   ticket's acceptance criteria, and the title and body, with the reviewer's leak check over all of
   it. Fix or ticket each finding (see [cross-review](cross-review.md)).
4. The reviewer pane approves the pull-request fingerprint of the head and the exact title and body.
   Nothing is pushed before this. Then push the branch, and only then does the repository's create
   command open the pull request. Edits and comments go through the same approval, and a new commit
   voids it.
5. The lead merges its own pull request (owner ruling, 2026-11-15) once local `hk check --all` passes on
   the exact head and the reviewer approved that head and the pull request's text. Hosted checks from
   free apps are advisory, and no paid CI is added. The merge is `gh pr merge N --merge
   --match-head-commit <sha> --author-email 1428022+sortakool@users.noreply.github.com`, so the merge
   commit carries the account's noreply address, not a personal email. A repository can check these
   gates in one task: dotfiles has `mise run //repo:pr-merge`.

## Close-out

After the merge: close the issue with an approved comment, tick the roadmap line, remove the
worktree, and recompute the frontier (a GitHub blocked-by link only drops when its blocker closes).

A spec may let its tickets close earlier, on a shared branch, so the frontier can move before the
one pull request merges. Then a ticket closes only after the reviewer approved the shared branch's
diff at its head, and only then were its commits pushed to the shared branch on the remote and seen
there; nothing is pushed before that approval. The approved comment names each commit and says it is
not merged yet. Those commits are never rewritten: later changes are new commits, and the pull
request merges with a merge commit, never squashed or rebased. On an early close, tick the roadmap
line and recompute the frontier, but keep the worktree until the merge. The spec stays open until
the merge. If the branch or pull request is abandoned, or later work undoes a ticket, reopen the
ticket and recompute the frontier.
