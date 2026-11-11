---
okf_version: "0.2"
type: "report"
title: "Claude <-> Claude (Claude Code 2.1.319)"
description: "The inbox socket, registry, delivery policy, SendMessage, idle notices, ListAgents, teammates, --bg, Channels and Remote Control."
---

# Claude <-> Claude (Claude Code 2.1.319)

`L<n>` is a line of `cli-2.1.319.split.js` (see [Method](method.md)); the quoted anchor finds it again after a rebuild.
VS = VERIFIED-SOURCE, VL = VERIFIED-LIVE (run named).

## The pieces

Each interactive session that has messaging enabled and starts it successfully runs an **inbox socket** and writes a
**registry record**. Restricted sessions, sessions with the messaging gate off and remote thin clients skip the
startup (L393918-393922, VS). Senders find a session through the
registry and write newline-delimited JSON frames to its socket. Everything else (SendMessage, ListAgents, idle
notices, delivery notices) is built on those two.

### Inbox socket (L394844-395345, anchor `cc-socks`)

| Claim | Where | Tag |
|---|---|---|
| Path `<XDG_RUNTIME_DIR or CLAUDE_CODE_TMPDIR or /tmp>/cc-socks/<pid>.sock` (here `~/.local/run/cc-socks/`); directory 0700, socket 0600. | L395118-395123, L395315 | VS, VL (C1) |
| One JSON object per line. The receiver appends each chunk to a string buffer and drops the connection when that buffer is longer than `sLn=1048576` characters, before it splits complete lines. So it is a limit on the accumulated string, not an exact per-line wire-byte limit. A connection that sends no complete line in 30 s is closed. | L395100-395105, L128269 `sLn=1048576`, L394844 `SVr=30000` | VS |
| An `{"type":"auth","token"}` first line is optional off Windows: a missing or wrong token leaves the connection unauthenticated, not closed. Peer identity is the kernel's peer pid (`getPeerPid`), not the token. | L37989, L128254-128262, L395081-395116 | VS, VL (C1) |
| A frame whose `session_id` is present and not this session's is dropped with no reply; so are empty content and unknown types. A frame with no `session_id` passes the check, so a sender that omits the field is not bound to one session. | L395003-395004 | VS, VL (C1) |
| `type:"user"` frame: `message.content`, `uuid`, `msg_id`, `priority` now/next/later (default next), `from` (a `uds:` reply address). Enqueued as a prompt with origin `{kind:"peer", from, verifiedPeerPid, msg_id}`. | L395005-395020 | VS, VL (C1) |
| `priority:"now"` bypasses the serial queue and steers: the in-flight request is aborted and re-run with both messages. | L395076-395078 | VS, VL (C1 steer) |
| Sender guard: rate limit and dedup are keyed by sender. The queue limit is not: `maxQueuedPeerMessages` defaults to 50 and a flag may set it from 10 to 5000, and the count is every queued peer-origin message in this receiver, from any sender. Over it, the message is dropped with `queue-full`. | L128233-128236, L151409-151420 | VS |

### Registry (L51024-51075 writer, L128427-128447 reader)

| Claim | Where | Tag |
|---|---|---|
| `~/.claude/sessions/<pid>.json`: pid, sessionId, cwd, name, kind (interactive/bg/daemon), messagingSocketPath, status busy/idle/waiting/shell, bridgeSessionId (its Remote Control copy). | L51030-51070, L128432-128447 | VS, VL (C2) |
| A 0600 key file `<pid>.<sha256 of socket path>.key` holds the peer token. | L37988-38007 | VS |
| Record, key and socket are removed on exit; dead rows are swept. After a tab close the process, registry record, key file and socket were gone (C1; cleanup time not measured). In C2 the `exited` notice came 0.5 s after the close and process, registry and socket were gone; C2 did not check the key file. | L51025, L128456 | VS, VL (C1, C2 kill) |

### Delivery policy (`crossSessionInbound`, L372860-373016)

| Claim | Where | Tag |
|---|---|---|
| accept / hold / refuse; a repo setting can only tighten. | L372860-372904 | VS |
| Order: an explicit `crossSessionInbound` setting decides first (accept, hold or refuse); only then a `selfSent` message is accepted, and only then the mode checks run. Mode checks hold when the sender's permission mode class (prompting vs bypass) differs, when it asserts none to a bypass receiver, or when the mode is unknown. | L372917-372927 | VS |
| Only a `mode-mismatch` or `no-mode-asserted` hold, in a session with a dialog handler, opens a timed approval dialog. The timeout is configurable (`CLAUDE_CODE_USER_DIALOG_TIMEOUT_MS` / `dialogExpiry`; default 5 min), and it is postponable: when the timer fires and `Vf()` holds or the peer dialog is not the visible one, it re-arms instead of expiring. So 5 min is not an upper bound on the hold. `dialogExpiry:"never"` means no timer. Other holds (explicit setting, unknown mode, bypass default) open no such dialog. | L530257-530268, L73698-73705 | VS |
| In the plain accept path the sender gets no positive receipt: only enqueue/dequeue in the receiver transcript. The sender may learn of other outcomes as a `[Cross-session delivery notice]` turn: held, denied, expired, refused, dropped (with reason). This channel is best-effort: the sender keeps at most 200 outstanding sends and evicts the oldest (`we=200`), a receipt with no matching send is discarded, and a receipt the receiver cannot send is only logged. So the absence of a notice proves neither acceptance nor continued queueing; callers need a bounded wait that ends as unknown. | L128334-128349, L395036-395041, L395322-395327, L521657-521674, L395322-395343 | VS, VL (C2 finding 2) |
| A held message that is later released sends the sender a `delivered` receipt, rendered "approved and released to that session (final delivery is up to their queue)". This covers approval and automatic policy release. It means release to the queue, not that the receiver consumed it. | L373001, L373011, L521655-521666 | VS |

### Idle notices (`notify_when_idle`, L394585-394835)

| Claim | Where | Tag |
|---|---|---|
| A sender subscribes with `{action:"notify_when_idle", from, msg_id}`; the receiver may answer once with `{action:"peer_idle_notice", state: idle/exited/unavailable, detail?}`. | L394585 | VS, VL (C1, C2) |
| One subscription per (reply address, verified peer pid): a second replaces the first. Replacement needs a verified pid (`r!==void 0`); entries with no pid are counted in a separate class. 12 h expiry, 32 global cap, 4 per pid, 750 ms idle debounce. The notice is best-effort: a subscription can be revoked before it fires if the receiver's inbound policy becomes `refuse`, can expire unfired, and a notice send that fails twice is only logged. | L394585, L394617-394634, L394658-394689 | VS, VL (C1 replace) |
| Fires only when nothing is queued or held. It does not preempt: a message sent mid-turn waits, and the tool text says it drains at the receiver's next tool round (L470995), so same-turn consumption is possible when a tool round occurs. C2 saw it run as its own turn after the current one, but that run had no intervening tool round (C2 `results.md:19`), so that observation is scoped to C2. | L394635-394681, L470995 | VS, VL (C2 steer, scoped) |
| `detail` = the receiver's last reply: the parsed status detail if there is one (it takes precedence, and can come from a later `result:` line), else the first non-blank line; cleaned, cut to 100 characters, sent only when the reply address is the inbox registered to the subscriber's own pid. An unregistered poster (C1) gets no detail. | L394654-394705, L137081-137090 | VS, VL (C1, C2) |
| Esc = idle with no detail; a closed tab = `exited` within 0.5 s. | L394733-394767 | VL (C2) |

### SendMessage and ListAgents

| Claim | Where | Tag |
|---|---|---|
| SendMessage takes `to`, `summary`, `message`, `notify_when_idle`; no priority field, and the client hardcodes `priority:"next"`, so it can never steer. It has no `session_id` field either: the `uds:` path builds its frame without one (the frame the client builds has msg id, type, message, priority, from, no `session_id`), so stock SendMessage addresses a socket and does not bind the recipient session. The registry field is `sessionId` (L128442) and the wire field is `session_id` (L395003); only a raw wrapper that maps the first to the second and rejects a missing id binds the session. | L471074, L471369, L128328, L128094, L128442, L395003 | VS, VL (C2 steer) |
| The receiver sees `<cross-session-message from= from-name= from-mode=>`; transcript shows queue-operation enqueue/dequeue. | L32043 | VS, VL (C2) |
| Names resolve through one candidate index: main, teammates, subagents, local registry rows, cloud sessions, Remote Control rows. See [Dead-tab fallthrough](dead-tab-fallthrough.md). | L470042, L38100-38142 | VS |
| `to` may also be `uds:<path>` (or a bare `*.sock` path), `bridge:<id>`, `name [ref]`. | L32043, L471364-471376 | VS |
| Remote Control and cloud targets get an HTTPS POST to `<BASE_API_URL>/v1/sessions/<id>/events`, or `/v1/code/sessions/<id>/events` when the flag `tengu_ccr_v2_send_events_cli` is on (default on). `notify_when_idle` is refused for them. HTTP 200/201/204 is the only receipt. | L76225-76227, L356870-356871, L109186, L471559-471578 | VS, VL (C2 error) |
| "One-way" differs by target. A cloud target always gets the warning that it cannot message back. A Remote Control target gets it only when this side has no live Remote Control or no reply address. The warning is about replies, not about delivery. | L471216-471218, L471577-471578 | VS |
| An earlier GET of `/v1/code/sessions/<id>` (no `/events`) is an optional read in the same function; it is not the POST. | L356870 | VS |
| ListAgents rows come from the same index, labelled on this machine / Remote Control / cloud. | L38154, L470143-470164 | VS |

### Other paths

- **Teammates and subagents** (in one process): a mailbox, "queued your message for its next turn"; a subagent's
  SendMessage to `main` enqueues on the parent. L471143-471163, L471477-471481. VS.
- **`claude --bg`** sessions (kind `bg`) with `claude agents --json` for status; a SendMessage reply lands on the
  Stop hook. L22879, L22904. VS for existence, VL as recorded in the options map (B26).
- **Channels** (`notifications/claude/channel` from an MCP server into a running session): gated on a server
  capability, org policy, `--channels`, and an allowlist unless `--dangerously-load-development-channels`. L290935-290971.
  VS, not run.

## Unexplained

- What the server does with a plain message to a closed tab's Remote Control copy.
- A live mode-mismatch hold and its dialog timeout; the 100-character detail cut on a long reply.
- ListAgents row rendering, `claude agents --json` and `--bg` internals, hop-chain bookkeeping: not read in full.
