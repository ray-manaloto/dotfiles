---
okf_version: "0.2"
type: "report"
title: "Critique"
description: "What the evidence does not cover, and which claims are weakest."
---

# Critique

Written by the session that did the research; not an independent review. The weakest points, in order:

1. **Proposals A, C and E were never run end to end, and their correlation is designed, not tested.** P1 ran the
   app-server client against a TUI, but not as a tool called from a Claude session, and not headless. A matches its
   input by `clientUserMessageId`, D binds by `session_id` and a nonce (a loose join on the transcript), and E, a
   `turn/completed` watcher that posts to Claude, posts only on a terminal turn. None of these has run.
2. **`codex queue` is source-only**, and so is the "no dispatch after an interrupt" rule that would make B stall.
3. **Approval fan-out** ran live only with reviewer `user`, and `humanCommand` was not run live; the rest is
   source-only ([Approval fan-out](approval-fanout.md#not-established)). The safety of proposals A and C rests on the
   client never replying.
4. **Claude citations point at a derived file.** `L<n>` only means something with the same extractor and split rule;
   the anchors are what survive. The extractor is not in this repo yet.
5. **Remote Control receiving side is unknown.** The binary shows the POST, not what the server does with it.
6. **Negative claims** ("nothing external posts into the Codex subagent mailbox", "no positive delivered receipt for an ordinary accepted message"; a released hold does send a `delivered` receipt, JS:L373001,L373011)
   rest on method-list and code-path reads, not exhaustive search.
7. **No auth on either socket** beyond same-user file modes: any process running as this user can post to a Claude
   tab or drive a Codex thread. Fine for one owner on one Mac; not a boundary.
8. **Round 1 found 27 errors in a bundle the author thought was checked.** Most were overreach from one code path.
   Round 2 (rev 4) raised 22 more, all corrected ([Update log](log.md)); later claims carry the same risk until reviewed.
9. External projects named in earlier notes (AgEnD, AX, a2a-bridge, mngr) were not re-checked against 0.167.0.
