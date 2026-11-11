---
okf_version: "0.2"
type: "report"
title: "Claude <-> Codex: proposals"
description: "The options in each direction, visible tab and headless, with evidence, gaps and the recommended pair."
---

# Claude <-> Codex: proposals

Neither harness speaks the other's protocol. Each one exposes a local socket the other side can use with a small
client:
- Codex's app-server: JSON-RPC over WebSocket framing on a unix socket.
- Claude's inbox socket: newline-delimited JSON.

Same-user file permissions are the only gate on either socket. Sequences are in [Diagrams](diagrams.md).

## Claude -> Codex (Claude asks, Codex answers)

| # | Proposal | How | Evidence | Gaps |
|---|---|---|---|---|
| A | **App-server client on the shared daemon** (recommended, gated on t10, t11, t13 and t15 passing) | Claude runs a small client. It connects to the control socket, `initialize`s, `thread/resume`s the reviewer's thread to subscribe, `turn/start`s with a fresh `clientUserMessageId`, records the turn id of the `item/started` whose `userMessage` item has that `clientId`, and waits for `turn/completed` with that turn id. The reviewer stays visible, because its TUI is a client of the same daemon. Only the methods and fields in the [allowlist](approval-fanout.md#strict-allowlist-for-the-proposed-client-a-and-c) are sent. The client never interrupts. | P1 5/5; [Codex <-> Codex](codex-codex.md) subscribers and turns | **Steering:** `turn/start` on a busy thread steers the owner's turn and returns that turn's id (protocol/src/turn_input.rs:255-262; turn_processor.rs:717-725, 755-767). The response is the same whether it started a turn or steered one (turn_processor.rs:717-767), so the client cannot tell afterwards. A runs only on a thread reserved for it, or when the owner allowed steering. A reviewer the owner also types into is not reserved. An idle check before sending still leaves a race (t11). **Approvals:** with reviewer `user` the client receives the reviewer's approval requests and must never reply; with `auto_review` the auto-reviewer decides and the client sees only notices; with policy `never` no request is raised and the auto-reviewer is not asked, so on a danger-full-access worker only forced `rm` (also behind `sudo`, `env` or `trap`) is blocked and every other command runs unchecked ([Approval fan-out](approval-fanout.md#who-answers-the-threads-policy-and-reviewer), d8). **Answer:** `items` holds an answer only when status is `completed`, `itemsView` is summary and `items` is non-empty. Failed and interrupted turns have `items: []`, and a `completed` turn with no agent message has `items: []` with `itemsView: notLoaded` (bespoke_event_handling.rs:1402-1405, 1583-1585, 1618-1626). **Lost notice:** after a disconnect the client reads the turn back with `thread/read` or `thread/turns/list` (t15). **Resume side effects:** it overwrites the session's client name (thread_processor.rs:4822-4827) and can fire a queued item on an idle thread (thread_lifecycle.rs:1283-1290). |
| B | **`codex queue` one-liner** | `codex queue --thread <name> --message … [--remote …]`. The answer comes from a separate wait path: the rollout's terminal event (`task_complete` or `turn_aborted`), or a `turn/completed` watcher. | source only | not run. A queued item does not dispatch after an interrupt (`ThreadIdleCause::Interrupted`, ext/queue/src/service.rs:549-553). |
| C | **Headless thread on the daemon** (dropped for workers by d8: workers on on-request need a visible TUI for person-only prompts; gated on t13 and t14 if reused) | The same client as A, with `thread/start` (empty params) and no TUI attached. | source; P1 shows the turn lives in the app-server | No live run without a TUI. The approval policy comes from the owner's config. An ordinary approval waits and is replayed to a TUI that attaches later. A `humanCommand` approval with no eligible TUI is never stored: it ends as a denial and the item fails (outgoing_message.rs:425-427, 449-467; bespoke_event_handling.rs:2142-2147). So if the config can raise human checkpoints, an eligible TUI must already be attached (d4). |
| - | `codex exec` / `codex mcp-server` | Rejected. `codex exec` breaks the owner rule against it for agent steps, and `mcp-server` does not exist in 0.167.0. | - | - |

## Codex -> Claude (Codex asks or reports, Claude answers)

| # | Proposal | How | Evidence | Gaps |
|---|---|---|---|---|
| D | **Direct inbox-socket client** (recommended, gated on the delivery contract below and t12 passing) | Codex runs a small client. It reads `~/.claude/sessions/<pid>.json` and writes a `type:"user"` frame (`priority:"next"`, or `"now"` to steer) plus `notify_when_idle` to `messagingSocketPath`. The text asks Claude to end its reply with a marker line holding a per-message nonce. The client waits for `peer_idle_notice` and then reads the Claude transcript for an assistant entry with that marker. It addresses a socket, so it cannot fall through to the cloud. | C1 (see below) | **Observed in C1:** the refusals C1 saw were for malformed frames (C1 results.md:16, 29-31). After a partial reply and Esc, the idle notice still said `idle` (C1 results.md:18, 22-26). **From source, not run:** policy receipts go to any vetted reply socket and need no registry membership (JS:L372946-372954, L395322-395327, L128363-128405). Notices are best-effort: correlations are evicted, unmatched receipts are dropped, send failures are only logged, and idle subscriptions expire (L128334-128349, L395038-395041, L395327, L394658-394689). No notice proves nothing. There is no auth off Windows. Identity is not bound by Claude: an omitted `session_id` is accepted (L395003-395004), and no send path checks the registry pid or start time (L471549, L471369). A second subscription from the same reply address and verified pid replaces the first (L394624-394625). |
| E | **`turn/completed` watcher posts to Claude** (replaces the Stop hook, gated on t16 passing) | A separate app-server client subscribes to the reviewer's thread with `thread/resume {threadId}` and the A allowlist. On each `turn/completed` for a turn it was asked to report, it runs D's client once with the status and the answer. | source; D | not run. **Resume is not attach-only:** it overwrites the session's client name and version with the watcher's `clientInfo` (thread_processor.rs:4822-4827), and on an idle thread it fires the idle lifecycle, which can dispatch a queued item (thread_lifecycle.rs:1283-1290; ext/queue/src/service.rs:549-565). It also replays pending approvals, which the watcher must never answer. **Catch-up:** keep the last seen turn id; after a reconnect read newer turns with `thread/turns/list` (common.rs:891) and post once for each terminal one. A turn left `inProgress` is read back as `interrupted` when the thread is not active (thread_lifecycle.rs:1443-1457), so a stale turn and a real interrupt look the same. **Why not a Stop hook:** all Stop handlers run before the outcome is combined, and one handler that blocks makes the same turn continue (hooks/src/events/stop.rs:201-234, 299-339; core/src/session/turn.rs:750-786). A hook cannot see whether another handler blocks, so it can post an answer that is not final, and post it more than once. The Stop hook is not a done path. |
| F | Channels | An MCP server pushes `notifications/claude/channel` into the Claude session. | source only | Needs `--dangerously-load-development-channels` or an allowlist, so it is rejected as a default. |

## D and E delivery contract

D and E are usable only when they also do the following:
1. **Bind the target.** Read the registry record and check that the pid is alive, its start time matches the record,
   and the socket connects. A raw client maps the record's `sessionId` (JS:L128442) to the frame's `session_id`
   (L395003), so a reused socket path for another session drops the frame. Stock `SendMessage` has no such field
   (L471074), so this needs the raw client.
2. **Correlate by an explicit final-reply marker.** Put a nonce in the text, and ask Claude to end its reply with the
   line `REPLY-END <nonce>`. Dequeue records carry no content (L151308, L151491, L151515-151521), so adjacency in the
   transcript cannot identify the reply. Find the `user` entry whose `message.content` holds the nonce (inside the
   `<cross-session-message …>` wrapper, L32043), then the next `assistant` entry that ends with the marker. A turn
   with tool calls writes several assistant entries, and only the last holds the marker. Use a fresh reply address
   for each wait, so no other wait replaces the subscription.
3. **Bound every wait.** End with one of these outcomes: `answered` (marker found), `interrupted` (a
   `[Request interrupted by user]` user entry follows, L32174, as in C1 results.md:18), `held`, `refused`, `exited`,
   `unknown` (timeout, no notice, or idle with no marker and no interrupt entry). An idle notice means "read the
   transcript", never "done": it also fires after Esc. The marker depends on the model obeying the request, so a
   missing marker is `unknown`, not `failed`. Never treat partial output as an answer.
4. **E posts once per terminal turn.** Post on `turn/completed` for the correlated turn: `completed` with an answer,
   `completed` with no answer, `failed` or `interrupted`. Deduplicate on turn id, so a reconnect and `thread/read`
   catch-up does not post twice. The rollout's `task_complete` / `turn_aborted` is the fallback when no watcher was
   connected.

## Recommended pair

A and D, with a correlated `turn/completed` as the done signal, and E's watcher when Codex must report unasked.
- **Claude to a visible Codex reviewer:** the app-server client on the shared daemon (A), on a reserved thread, with
  the allowlist. The reply is in `turn/completed` after the status and items checks.
- **Codex to Claude:** an inbox-socket client by socket path (D), never by name
  ([Dead-tab fallthrough](dead-tab-fallthrough.md)), with the delivery contract and the final-reply marker.
- **Approvals:** the A client never answers a server request, never interrupts and never sends a field outside the
  allowlist. It reports the requests it saw ([Approval fan-out](approval-fanout.md)).
- **Implementation:** both clients are small stdlib Python, which fits this repo's zero-bash rule as a package under
  `python/`.
- **Order:** nothing is built until its gate tests pass, not just run: A on t10, t11, t13 and t15; C (not used for workers) on t13 and t14;
  D on t12; E's watcher on t16.
