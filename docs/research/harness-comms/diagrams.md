---
okf_version: "0.2"
type: "report"
title: "Diagrams"
description: "Components and their dependencies, and sequence diagrams for each Claude <-> Codex proposal, in Mermaid."
---

# Diagrams

## Components and dependencies

```mermaid
flowchart LR
  subgraph Claude["Claude Code 2.1.319 (one process per tab)"]
    CS[Claude session] --> SM[SendMessage / ListAgents]
    CS --> INB[inbox socket<br/>cc-socks/&lt;pid&gt;.sock]
    CS --> REG[registry<br/>~/.claude/sessions/&lt;pid&gt;.json]
    INB --> POL[crossSessionInbound<br/>accept / hold / refuse]
    INB --> IDLE[notify_when_idle store<br/>peer_idle_notice]
    SM --> IDX[candidate index]
    IDX --> REG
    IDX --> RC[Remote Control / cloud rows]
    SM -->|uds: or name, local| INB2[peer inbox socket]
    SM -->|cloud / RC| API[HTTPS POST<br/>/v1/sessions/&lt;id&gt;/events<br/>or /v1/code/sessions/&lt;id&gt;/events]
    CS --> TR[transcript .jsonl]
  end
  subgraph Codex["Codex 0.167.0"]
    D[shared app-server daemon<br/>app-server-control.sock] --> TH[threads + subscriber sets]
    TH --> TU[turns: start / steer / interrupt / completed]
    TH --> Q[thread/queue/*]
    TU --> HK[hooks.json: Stop, …<br/>not a done path]
    TU --> RO[rollout .jsonl<br/>task_complete or turn_aborted]
    TUI[codex TUI / --remote] --> D
    CQ[codex queue] --> Q
    TU --> MA[multi_agent subagents<br/>in-process only]
  end
  A[Proposal A client<br/>run by Claude] -->|JSON-RPC over WS on unix socket| D
  DC[Proposal D client<br/>run by Codex] -->|JSON line frames| INB
  DC --> REG
  W[Proposal E watcher<br/>app-server client] -->|thread/resume, turn/completed| D
  W --> DC
```

## Claude -> Claude: SendMessage with notify_when_idle (C2)

```mermaid
sequenceDiagram
  participant S as Claude sender tab
  participant R as receiver inbox socket
  participant C as receiver Claude
  S->>S: resolve name (candidate index)
  S->>R: user frame (priority next) + notify_when_idle
  S-->>S: tool result: "in that session's inbox, not yet read"
  R->>R: crossSessionInbound: accept
  R->>C: enqueue, dequeue when current turn ends
  C->>C: turn runs, replies
  C->>R: idle (nothing queued, 750 ms debounce)
  R->>S: peer_idle_notice state idle, detail «last reply» (registered sender only)
  S->>S: injected [Cross-session idle notice] wakes a new turn
```

## Codex <-> Codex: two clients on one thread (P1)

```mermaid
sequenceDiagram
  participant T as codex TUI (visible)
  participant D as app-server daemon
  participant K as second client
  T->>D: initialize, thread/start
  K->>D: initialize, thread/resume (subscribe + in-flight snapshot)
  K->>D: turn/start (clientUserMessageId)
  D-->>K: item/started userMessage (clientId = clientUserMessageId, gives the turn id)
  D-->>T: item/*, hook/* notifications
  D-->>K: item/*, hook/* notifications
  K->>D: turn/steer (expectedTurnId)
  D-->>T: turn/completed {turn.id, status, items}
  D-->>K: turn/completed {turn.id, status, items}
  Note over D,K: items is empty on failed or interrupted turns
```

## Proposal A: Claude asks a visible Codex reviewer

```mermaid
sequenceDiagram
  participant CL as Claude session
  participant A as client (python, run by Claude)
  participant D as Codex app-server daemon
  participant T as reviewer TUI (visible)
  CL->>A: run client --thread reviewer --message ...
  A->>D: initialize (experimentalApi, no requiredHumanApproval)
  Note over A,D: allowlist only: no approval, sandbox, permissions, config or model fields
  A->>D: thread/resume {threadId} (subscribe)
  Note over A,D: reserved thread: a busy turn/start would steer the owner's turn
  A->>D: turn/start {threadId, input, clientUserMessageId}
  D-->>A: item/started userMessage clientId match: record turn id
  D-->>T: turn shows live in the tab
  D-->>A: turn/completed {turn.id, status, items}
  alt status completed, itemsView summary, items non-empty
    A-->>CL: final answer from items
  else completed, items empty (itemsView notLoaded)
    A-->>CL: completed, no answer
  else failed or interrupted (items empty)
    A-->>CL: failed + codexErrorInfo, or interrupted, no answer
  end
  Note over A,D: never interrupts, after a disconnect reads the turn back with thread/read
```

## Approval fan-out on a joined thread

```mermaid
sequenceDiagram
  participant X as Codex turn
  participant D as Codex app-server daemon
  participant A as client (python, run by Claude)
  participant T as reviewer TUI (visible)
  participant O as owner
  X->>D: needs approval (command / file change / permissions)
  D-->>A: item/.../requestApproval (all subscribers)
  D-->>T: item/.../requestApproval
  Note over A: logs method + id, never replies (an error reply = deny)
  T->>O: prompt
  O->>T: accept or decline
  T->>D: response (first answer wins)
  D-->>A: serverRequest/resolved
  D->>X: decision
  Note over D,T: humanCommand approvals go only to T (requiredHumanApproval), with no eligible T the request is denied, not stored
```

## Proposals D + E: Codex reports to Claude (gated by the delivery contract)

```mermaid
sequenceDiagram
  participant D as Codex app-server daemon
  participant W as turn/completed watcher (E)
  participant P as client (python, D)
  participant R as Claude inbox socket
  participant CL as Claude session
  W->>D: initialize, thread/resume {threadId} (allowlist only)
  D-->>W: turn/completed {turn.id, status, items}
  W->>W: once per turn id (dedup), after reconnect catch up with thread/read
  W->>P: run client --to-pid N --nonce K --status S
  P->>P: read ~/.claude/sessions/N.json: pid alive, procStart matches, socket connects
  P->>R: user frame (priority next, session_id, nonce K, ask for REPLY-END K) + notify_when_idle (fresh reply address)
  R->>CL: enqueue, runs as a turn
  R-->>P: peer_idle_notice, or nothing (best-effort)
  P->>P: read transcript: user entry with K, then assistant entry ending REPLY-END K
  P->>P: outcome: answered / interrupted / held / refused / exited / unknown
  Note over P,R: idle is not done, it also fires after Esc. Socket path, never a name. Claude checks session_id only if sent
```

## Dead-tab fallthrough

```mermaid
sequenceDiagram
  participant S as Claude sender
  participant I as candidate index
  participant L as local row (closed tab)
  participant RC as Remote Control row
  S->>I: SendMessage to "c2-recv"
  I->>L: socket connect (250 ms) fails: row dropped
  I->>RC: only match: exactUnique
  alt notify_when_idle true
    RC-->>S: refused: NOT delivered
  else plain send
    RC-->>S: HTTPS POST .../events, HTTP 2xx is the only receipt (not run)
    Note over RC,S: no idle notice, no consumption receipt, one-way warning only if no live Remote Control or no reply address
  end
```
