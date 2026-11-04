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
   same tests afterwards. It never runs after an approval: an edit voids the approval.
3. **Verify.** `/verify` over the working changes, the branch diff and the untracked files. It must
   end PASS, or SKIP for documentation only. FAIL and BLOCKED stop the ticket.
4. **Stage.** The coordinator or owner stages everything.
5. **Language gate.** Where the repository has one (for example a Python reviewer that must end
   `VERDICT: PASS`), run it on the staged content in its own tab.
6. **Review.** The reviewer tab runs an uncommitted-changes review. Fix or ticket each finding (see
   [cross-review](cross-review.md)); a fix that changes the index repeats steps 4 and 5.
7. **Approve and commit.** Write the message to a file, compute the commit fingerprint with the
   repository's command, and ask the reviewer pane. On `PANE-APPROVE <fingerprint>`, run
   `git commit -F <message file>`. A changed index, a changed message or any later answer from the
   reviewer voids the approval.

The worker stops at step 1-3 with its changes in the worktree and a proposed message file. Staging,
the approval and the commit belong to the coordinator or the owner.

## The pull request

1. Base-branch review in the reviewer tab, with the ticket's acceptance criteria supplied.
2. `/pr` writes the title and body to a file: summary, evidence (how it was tested), merge danger
   (one-way or two-way door, and how to undo it) and blast radius.
3. Scan the title and body for private content, then a document review in a read-only tab.
4. The reviewer pane approves the pull-request fingerprint of the exact title and body; only then
   does the repository's create command open it. Edits and comments go through the same approval.
5. Watch the checks. The owner merges on GitHub.

## Close-out

After the merge: close the issue with an approved comment, tick the roadmap line, remove the
worktree, and recompute the frontier (a GitHub blocked-by link only drops when its blocker closes).
