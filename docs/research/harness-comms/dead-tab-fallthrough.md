---
okf_version: "0.2"
type: "report"
title: "Dead-tab name fallthrough to Remote Control"
description: "Why a message to a closed Claude tab's name can reach its cloud copy, and how to address tabs so it cannot."
---

# Dead-tab name fallthrough to Remote Control

**Risk:** when a Claude tab dies, SendMessage to its name can reach that session's Remote Control (cloud) copy
instead of failing. A message sent there gets no idle notice (`notify_when_idle` is refused) and no consumption receipt, so a crashed tab could swallow messages
without anyone knowing.

## What was seen (C2, VERIFIED-LIVE)

The C2 run closed the receiving tab `c2-recv`, then sent to the name again with `notify_when_idle`. The name resolved
to the tab's Remote Control copy (the first send's result had already said it was "also connected via Remote
Control"). The send was refused only because Remote Control targets don't support `notify_when_idle`: "Your message
was NOT delivered". A plain send was not tried.

## Why it happens (VERIFIED-SOURCE, `cli-2.1.319.split.js`)

1. SendMessage builds one candidate index: main, in-process teammates and subagents, local registry rows, cloud
   sessions, Remote Control rows (L38100-38142).
2. A cloud or Remote Control row whose id equals a **live** local row's `bridgeSessionId` is left out of the
   candidates and its name is recorded as claimed locally (L38114-38125). L470194-470200 only marks mirrored metadata. So while the tab lives, its name means the local socket.
3. There is no "prefer local" rule. A name pinned earlier in the conversation wins first (L470119-470120). Otherwise one matching candidate resolves directly with `exactUnique` only when it is a session, cloud or bridge row, no cloud, bridge or local list was unavailable, the bridge lookup has settled, its identity is not claimed locally, it is not an agent pin and its name is not derived (L470122). Anything else, including two candidates, gives the `[ref]` ambiguity error (L471407-471429). The fallthrough was demonstrated only in C2.
4. A local row is listed only if its socket connects within 250 ms and its pid is neither gone nor recycled
   (L128419-128485). After a close the `exited` notice came 0.5 s later and the local row was gone (C2; cleanup time not measured), so the Remote Control row becomes the only
   match and wins.
5. A plain send to it is an HTTPS POST to `/v1/sessions/<id>/events`, or `/v1/code/sessions/<id>/events` with the
   default-on flag `tengu_ccr_v2_send_events_cli` (L76225-76227, L356870-356871, L109186). It returns only an HTTP
   status, and 200/201/204 counts as success (L356864-356885). The warning "one-way" always applies to a cloud target;
   for a Remote Control target it applies only when this side has no live Remote Control or no reply address
   (L471216-471218, L471577-471578), and it is about replies, not delivery. Nothing in the binary wakes or resumes a closed local process; what the server
   does with it is unknown.

## Who is affected

| Sender | Addressing | Can fall through? |
|---|---|---|
| Claude tab, SendMessage by name | name | yes, once the local tab is gone |
| Claude tab, SendMessage with `to:"uds:/…/<pid>.sock"` | socket path | no: a dead socket fails with the stale-socket text "the peer process may have restarted, so this socket path is stale" (L471375-471376, L128303). No cloud fallback. "That session may have just exited" is the name-send text (L471557) |
| Codex or any script writing to the inbox socket (C1) | socket path | no: ENOENT or ECONNREFUSED |
| Codex app-server client | thread id on a local socket | no Remote Control involvement |

## Mitigations

1. **Address by socket, not by name** for anything automated: `uds:<messagingSocketPath>` read from the
   registry record at send time. A dead tab then fails loudly. The tool's prompt steers models toward names
   (L470979), so a skill or wrapper has to supply the address.
2. **Always set `notify_when_idle`** on Claude-to-Claude sends: it turns a fallthrough into a hard refusal (seen in C2).
3. **Check liveness before sending**: registry file present, pid alive, socket connects.
4. **Unique per-run names** for test tabs, so an old name can't collide with a live one.

## Live run to settle it (specified, not run)

From a test sender tab, send without `notify_when_idle` to the name of a closed test tab that has a Remote Control
copy. Record the tool result, any later `[Cross-session delivery notice]` or idle notice, any process or transcript
that shows the message, and whether claude.ai/code shows it. Then send to `uds:<the dead socket>` and expect "gone".
