---
okf_version: "0.2"
type: "report"
title: "Codex <-> Codex (Codex CLI 0.167.0)"
description: "The app-server, shared daemon and --remote, thread subscribers, turn start, steer, interrupt and completion, codex queue, hooks, multi-agent tools, exec and rollouts."
---

# Codex <-> Codex (Codex CLI 0.167.0)

Paths are `codex-rs/<path>:<line>` at tag `rust-v0.167.0`. VS = VERIFIED-SOURCE, VL = VERIFIED-LIVE (P1 run).

## The pieces

Everything goes through the **app-server**: a JSON-RPC server that owns threads and turns. The TUI, `codex exec`,
`codex queue` and any outside client are all app-server clients. Two Codex sessions "talk" by being clients of the
same app-server, or by one Codex's subagent tools inside one process.

### Transports and connection

| Claim | Where | Tag |
|---|---|---|
| `codex app-server --listen stdio:// \| unix:// \| unix://PATH \| ws://IP:PORT \| off`, default stdio. | app-server-transport/src/transport/mod.rs:84-159 | VS |
| The shared daemon's control socket is `$CODEX_HOME/app-server-control/app-server-control.sock`; it speaks WebSocket framing over the unix socket. Socket mode 0600, no token: file permissions are the only gate. The server creates a missing parent directory with mode 0700, but an existing advertised parent is kept: it must be a directory owned by the user or root and not group/world-writable (unless sticky), else startup fails. The advertised path is an alias; the physical socket sits in a separate protected directory (0700) via `protected_socket_path`. Observed default dir mode 0700. | transport/mod.rs:56-77, unix_socket.rs:34, 79-110, 148-249; uds/src/daemon_directory.rs:21-31 | VS, VL (dir mode) |
| A `ws://` listener rejects an Origin header and needs `--ws-auth` (capability token or signed bearer) when not on loopback. | websocket.rs:99-107, 160-185; websocket-auth/src/lib.rs:33-36 | VS |
| `initialize` once per connection; `capabilities.experimentalApi` unlocks experimental methods for that connection only. | initialize_processor.rs:68-147; message_processor.rs:1003-1030 | VS, VL |
| `codex app-server generate-json-schema \| generate-ts --out DIR [--experimental]` writes the exact protocol of the installed version. | cli/src/main.rs:640-646, 1474-1489 | VS |

### Shared daemon and `--remote`

| Claim | Where | Tag |
|---|---|---|
| `codex app-server daemon {bootstrap, start, restart, update, stop, version, enable/disable-remote-control}`. | cli/src/main.rs:652-700 | VS |
| The TUI attaches to the shared daemon by default. Exclusions: `--no-daemon`, `--oss`, workload identity, `CODEX_EXEC_SERVER_URL`, `--profile`, a custom config loader, `--strict-config`, `--dangerously-bypass-hook-trust`, and command-line config overrides other than boolean `features`/`--enable`/`--disable` entries and the boolean `suppress_unstable_features_warning` / `tui.fullscreen_transcript` keys, or a `tui` table whose only key is a Boolean `fullscreen_transcript` (`-c 'tui={fullscreen_transcript=true}'`); those do not exclude. `--remote ws://\|unix://…` attaches to a given server; `--no-daemon` with `--remote` is an error. | tui/src/daemon_startup.rs:61-124; cli/src/main.rs:960-980, 2486 | VS |
| A turn lives in the app-server: closing the TUI tab mid-turn did not stop it. | - | VL (P1 kill3) |

### Threads: subscribers and fan-out

| Claim | Where | Tag |
|---|---|---|
| Each thread keeps a set of subscribed connections; notifications go to every subscriber, minus a per-connection filter: a notification marked experimental is skipped for a connection without `experimentalApi`, and any method in the connection's `optOutNotificationMethods` is skipped. A client that needs lifecycle events (`turn/completed`, `thread/status/changed`, `item/*`) must not opt them out. | app-server/src/thread_state.rs:359-363, 715-731; outgoing_message.rs:869-905; app-server/src/transport.rs:105-126 | VS, VL |
| `thread/start` subscribes its creator. `thread/resume` on a running thread subscribes the caller, returns the in-flight turn, and replays pending approvals. | request_processors/thread_lifecycle.rs:1034-1058, 1166-1190, 1283-1287 | VS, VL (resume) |
| Approval requests (command, file change, permissions, user input, MCP elicitation) go to all subscribers; the first answer from an eligible connection wins, and an error reply counts as one (deny, empty grant or decline). Only `humanCommand` approvals are kept to connections that declared `requiredHumanApproval`; with none, they are not stored and end as a denial. Details: [Approval fan-out](approval-fanout.md). | outgoing_message.rs:388-523, 563-686, 1029-1032; bespoke_event_handling.rs:2134-2148 | VL for ordinary command approvals with reviewer `user` (t10); VS (not run) for the rest, including `humanCommand` |

### Turns

| Claim | Where | Tag |
|---|---|---|
| `turn/start` with `clientUserMessageId` (echoed as `item.clientId`); on a busy thread it steers instead of starting. Per-turn overrides such as model persist on the thread. | request_processors/turn_processor.rs:546-768 | VS, VL |
| `turn/steer` needs `expectedTurnId`; a mismatch or an ended turn is an error ("no active turn to steer"). | turn_processor.rs:1077-1220 | VS, VL (P1 steer) |
| `turn/interrupt` at turn_processor.rs:1470-1532; Esc in the TUI gives status `interrupted`. An empty `turnId` is a startup interrupt: it skips the active-turn checks and submits `Op::Interrupt` (:1475-1482, 1508-1512); a non-empty one is rejected when it differs from the active turn or the turn already ended (:1482-1497). No caller ownership check: the proposed client does not use it (approval-fanout.md). | turn_processor.rs:1470-1532 | VS, VL |
| `turn/completed` status completed / interrupted / failed; `items[0]` is the final-answer agentMessage only when `itemsView` is "summary". `items` is empty with `itemsView` "notLoaded" when no last agent message exists: always for `interrupted` and `failed`, and for a `completed` turn without one. Check status, `itemsView`, array length and item type first. A failed turn carries `error.codexErrorInfo` (e.g. modelNotFound). | bespoke_event_handling.rs:1385-1423 (empty items 1402-1405), 1583-1586 (failed: no message), 1618-1626 (interrupted: none); v2/thread_data.rs:439-447 | VS, VL |

### Queue: `codex queue` and `thread/queue/*`

| Claim | Where | Tag |
|---|---|---|
| `codex queue --thread <uuid\|name> --message TEXT [--resume] [--remote ADDR]` sends the experimental `thread/queue/add`; it refuses `--no-daemon`. | cli/src/main.rs:207; cli/src/queue_cmd.rs:18-39; tui/src/session_queue_commands.rs:33-95 | VS |
| Enqueue on an idle loaded thread starts a turn, except when the thread's last idle cause was an interrupt. On an unloaded thread the item waits; `--resume` loads it. | ext/queue/src/service.rs:265-279, 472-483, 549-566 | VS (not run) |

### Hooks

| Claim | Where | Tag |
|---|---|---|
| `hook/started` / `hook/completed` notifications reach app-server clients. | bespoke_event_handling.rs:1172-1187 | VS, VL |
| 14 hook events; the Stop hook input includes `last_assistant_message` and `transcript_path` and can block completion. `hooks.json` per config folder; feature Stable, on. | protocol/src/protocol.rs:1786-1801; hooks/src/events/stop.rs:23-37 | VS |

### Inside one Codex: subagents

| Claim | Where | Tag |
|---|---|---|
| `multi_agent` (Stable, on): spawn_agent, send_input, resume_agent, wait_agent, close_agent. `multi_agent_v2` (Stable, off): adds send_message, followup_task, list_agents, interrupt_agent. | features/src/lib.rs:1593-1603; core/src/tools/handlers/multi_agents_spec.rs | VS |
| A watcher routes a child's final status to its parent. No app-server method posts into this mailbox (method-list check). | core/src/agent/control.rs:444-520 | VS (negative by list) |
| The agent message board and `wake_on_agent_messages` are under development, off, and provisioned by a research host. | features/src/lib.rs:1635-1645; features/src/feature_configs.rs:11-15 | VS |

### Not a live path

- `codex mcp-server` does not exist in 0.167.0: the only `mcp` subcommand manages external servers. cli/src/main.rs:136-215.
- `codex exec` runs its own in-process app-server, not the shared one, and has no `--remote`. exec/src/lib.rs:737-761.
- Rollouts `$CODEX_HOME/sessions/YYYY/MM/DD/rollout-<ts>-<id>.jsonl` record a turn end as one of two events:
  `"type":"task_complete"` inside the line's `payload` (a line is `{"timestamp":…,"type":"event_msg","payload":{"type":…}}`,
  seen in a local rollout; the `payload.type` tag is the `EventMsg` tag) (Rust `TurnComplete`: `turn_id`, `last_agent_message`, `error`) for a turn that ran to an
  end, or `"type":"turn_aborted"` (Rust `TurnAborted`: `turn_id`, `reason`, no `last_agent_message`) when the turn
  was aborted, for example interrupted. Both are persisted. The `EventMsg` enum is internally tagged with
  `rename_all = "snake_case"` (protocol.rs:1515), so `TurnAborted` serializes as `turn_aborted` (variant at :1699, no
  rename); `TurnComplete` carries an explicit `rename = "task_complete"` with alias `turn_complete` (:1577). The
  `reason` values are `interrupted`, `replaced`, `review_ended`, `budget_limited` (:4551-4558).
  Match the serialized names.
  core/src/tasks/mod.rs:871-903; rollout/src/policy.rs:137-140; rollout/src/recorder.rs:1770-1790;
  protocol/src/protocol.rs:1515, 1577, 1699, 2383-2395, 4526-4558.

## Unexplained

- Approval fan-out ran live only with reviewer `user` (t10 passed, see [Approval fan-out](approval-fanout.md#not-established));
  `requiredHumanApproval` and `humanCommand` were not run live; `codex queue` was not run live.
- Daemon thread recovery and the cloud remote-control path are not mapped; stdio-to-uds framing was inferred.
