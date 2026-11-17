---
okf_version: "0.2"
type: "process"
title: "Cross-review"
description: "Optional Codex reviews: when a lead asks for one, in which tab, and how its findings are handled."
timestamp: "2026-11-17T00:00:00Z"
status: "current"
tags: [workflow, review, codex]
---

# Cross-review

Optional: a lead may ask Codex to review a change by choice, so the reviewer is a different model family
and never sees the author's transcript.

No review is required for commits or pull requests (owner ruling, 2026-11-17), and nothing waits on
one: no approval line, pin or fingerprint. The repository's own checks still run (in dotfiles, hk with
betterleaks and private-paths), and the author keeps public text free of private project content,
claude.ai session links and home paths.

## The reviewer tab

A review runs in a herdr-app tab in the change's worktree: `codex-hc -a never -s read-only`, at Codex's
default model and effort (the tab's argv sets neither). Resume it only read-only
(`codex resume <id> -a never -s read-only`).

Send the brief with `hc send <terminal> "<text>"`, then wait with `hc wait <terminal>`, or use
`hc send --wait`. Never sleep and grep `hc read`: while the pane works, `hc read` shows only its screen,
so a loop can miss the answer. A wait that ends with reason `message` or `timeout` is a check-in:
handle it and wait again. Once the pane stops, read its findings or question with
`hc read --lines 100 <terminal>`, and reply to a question.

A brief that limits the pane names what stays allowed: "Do not contact <service>; read-only local
shell commands are allowed". Never write "do not call any tool": a reviewer reads that as a ban on the
shell it needs, and it stops to ask.

## Review kinds

| Kind | In the tab |
|------|------------|
| Branch | `/review` -> Custom review instructions: the acceptance criteria, `git diff origin/<default>...HEAD`, and the title and body file |
| Document | A typed brief naming the file's absolute path and that it is read-only |

A document review asks by document type: a spec for gaps, untestable criteria, missing seams and
contradictions with the glossary and ADRs; ticket bodies for vertical slices, written seams and
criteria that can fail; pull-request text for accuracy against the diff. A review over about 1,000
changed lines fans out.

## Handling findings

1. Check each finding's file and line against the diff before acting on it.
2. Tag it Important (fix), Nit (note) or Pre-existing (not caused by this change; ticket it if real).
   Drop style-only findings. Report at most five Nits a round and count the rest.
3. P0-P2 are fixed or ticketed; P3 may be noted and skipped.
4. When a finding is one case of a class, fix the class.
5. Re-review only the fix, if at all. Protected paths and CI workflow files always need the owner.
