# fw-gamma — Claude Code multi-agent framework survey (batch gamma)

**Agent:** fw-gamma · **Measured:** 2026-08-04 · **Branch:** `research/agent-team-design`

Repos under review:

1. [vildanbina/claude-relay](https://github.com/vildanbina/claude-relay)
2. [liatrio-labs/claude-code-gauntlet](https://github.com/liatrio-labs/claude-code-gauntlet)
3. [romiluz13/cc10x](https://github.com/romiluz13/cc10x)
4. [Akram012388/cc-dm](https://github.com/Akram012388/cc-dm)

Evidence rule in force: every claim carries a `path:line` or URL; uncited claims are labelled **UNVERIFIED**. Absence claims carry a control arm.

## Maturity snapshot (measured 2026-08-04 via `gh api repos/<o>/<r>`)

| Repo | Stars | Forks | Open issues | Created | Last push | License | Size (KB) |
|---|---|---|---|---|---|---|---|
| vildanbina/claude-relay | 61 | 12 | 0 | 2026-04-21 | 2026-08-03 | MIT | 162 |
| liatrio-labs/claude-code-gauntlet | 11 | 2 | 46 | 2026-03-24 | 2026-08-04 | Apache-2.0 | 3291 |
| romiluz13/cc10x | 161 | 25 | 0 | 2025-10-22 | 2026-08-03 | MIT | 8933 |
| Akram012388/cc-dm | 22 | 9 | 0 | 2026-03-21 | 2026-03-28 | MIT | 149 |

---

## 1. vildanbina/claude-relay

**HEAD measured:** `4a4844f28d53d12a45ceeeae949af1f4bc97a2dd`, 2026-08-03 21:52 +0200 (`git log -1`, shallow clone).

### What it actually is

A **Claude Code plugin that ships one MCP server** (TypeScript/Bun, ~30 source modules + a per-module test file each). Not a subagent pack, not a prompt pack, not a CLI wrapper.

- `.claude-plugin/plugin.json:287-292` — the plugin's *entire* payload is `"mcpServers": {"relay": {"command": "bun", "args": ["run", "${CLAUDE_PLUGIN_ROOT}/src/main.ts"]}}`.
- `.claude/commands/relay-rename.md` + `commands/relay-rename.md` (222 B each, duplicated) — one slash command, `/relay-rename`.
- `src/hub/` (5 modules) — the daemon: `registry.ts`, `pending-asks.ts`, `socket-recovery.ts`, `handlers.ts`, `index.ts`.
- `src/channel/` (13 modules) — the per-session MCP server: `hub-connection.ts`, `bootstrap.ts`, `daemon-spawn.ts`, `register.ts`, `tools.ts`, `tool-schemas.ts`, `routing.ts`, `notifications.ts`, `mcp-server.ts`, `pending-broadcasts.ts`, `parent-watch.ts`, `session-watcher.ts`, `reconnect.ts`.
- `src/protocol.ts` — a Zod discriminated union over the whole wire protocol; `src/framing.ts` — line-delimited JSON over a Unix socket.

**Architecture** (`docs/architecture.md:183-191`): three process kinds — N Claude Code sessions, N channel MCP servers (one per session), and **exactly one detached hub daemon per machine** at `$CLAUDE_PLUGIN_DATA/hub.sock`. First channel to start spawns the hub `detached: true` and unreffed; the hub self-exits 5 min after the last peer disconnects.

### Multi-agent roles

**There are no named agent roles.** Relay is role-agnostic transport. Its "roles" are protocol positions, not personas — `UBIQUITOUS_LANGUAGE.md:319-327` enumerates them verbatim:

> **Host** — the channel that spawned the hub daemon in the current lifecycle. Informational only; all peers act as clients at the protocol layer.
> **Client** — any channel connected to an existing hub.
> **Asker / Caller** — the peer that sent an ask.
> **Target** — the peer an ask is addressed to.

Mapped to the orchestrator/planner/researcher/executor/qa/... taxonomy: **none of them.** It is a message bus that any of those roles could sit on top of. Peer identity is a *directory basename*, not a role — `src/identity.ts:5` `defaultName(cwd)` slugifies the cwd basename; collisions get `-2`, `-3` suffixes (`register.ts` `registerWithRetries`).

Control arm for "no agent definitions": `ls agents .claude/agents` → both `No such file or directory`; `grep -rniE "maxTurns|permissionMode|disallowedTools|subagent"` over all `.ts`/`.md`/`.json` → **0 hits**, against a control grep for `relay_broadcast` over the same corpus → **21 hits**. The probe discriminates.

### Per-agent configuration

**No Claude Code subagent frontmatter at all** — there are no subagents. The knobs that exist are process-level:

| Knob | Where | Effect |
|---|---|---|
| `CLAUDE_RELAY_PRESET_NAME` | env, read at `src/identity.ts:44-45` | Pre-registers a spawned session under a deterministic peer name. **Explicitly for orchestrators**: `README.md:66-74` — *"Useful when a parent process pty-spawns many sessions and needs each to land under a known name."* Validated `[A-Za-z0-9._-]+`, max 64 chars; invalid values ignored. |
| `--dangerously-load-development-channels plugin:relay@claude-relay` | CLI launch flag | **Mandatory.** `README.md:32-38` — the `notifications/claude/channel` capability is "a Claude Code capability still in research preview"; the `dangerously-` prefix is required until Anthropic allowlists the plugin. |
| `requestTimeoutMs` / `broadcastTimeoutMs` | `StartChannelOptions`, `src/channel/index.ts` | Per-channel timeouts; not exposed as user config. |
| hub ask timeout | `handlers.ts` `handleAsk`, `msg.timeout_ms ?? ctx.defaultAskTimeoutMs` | 120 s default, server-side (`docs/architecture.md:263`). |

The one genuinely interesting configuration surface is the **MCP server `instructions` string** — `src/channel/index.ts:24-32`, seven sentences injected into every session that loads the plugin. Verbatim highlights:

> "If an incoming `<channel>` message is present, you MUST reply via relay_reply(ask_id, text) BEFORE handling any other user work. The peer session is blocked waiting on your reply. **Exception: if the pending user work is destructive or irreversible, complete or confirm that first, then reply.**"

> "your first user-visible output that turn must quote the peer's full body verbatim in a fenced markdown block... **The Claude Code TUI truncates tool-result panels, so plain assistant text is the only place the user actually sees the message.** Quote first, then act."

> "If a relay_ask fails (peer_not_found, peer_gone, timeout), surface the failure to the user and let them decide. **Never broadcast as a fallback**: relay_broadcast hits every session on the machine, including ones on unrelated projects, and is almost always the wrong recovery."

### Parallelism / DAG

**None modelled.** There is no DAG, no dependency graph, no scheduler. Parallelism is whatever the human already had — N sessions the user launched independently. The only fan-out primitive is `relay_broadcast`, and it is a flat star: `src/hub/handlers.ts:174-208` loops `for (const name of ctx.registry.names())`, creates a pending ask per peer keyed `${broadcast_id}:${name}`, and returns `{broadcast_id, peer_count}` synchronously; individual replies stream back as separate notifications tagged with the `broadcast_id`.

**What it routes and how (the brief's specific question):** it routes *natural-language questions between whole Claude Code sessions on one machine*, over a Unix socket, addressed by peer name.

- Transport: line-delimited JSON, Zod-validated discriminated union (`src/protocol.ts`).
- Client→hub verbs: `register`, `rename`, `list_peers`, `ask`, `reply`, `broadcast`.
- Hub→client verbs: `ack`, `err`, `peers`, `incoming_ask`, `incoming_reply`, `broadcast_ack`.
- Delivery into the receiving Claude: an MCP notification `notifications/claude/channel` (`src/channel/notifications.ts:3`) with `{content, meta}`; Claude Code renders it as `<channel source="relay" from="..." ask_id="...">body</channel>` at the **next turn boundary** (`docs/architecture.md:244-246`).
- Correlation: `ask_id` (UUID, `tools.ts` `relayAsk`) plus an optional `thread_id` the hub auto-generates; broadcasts reuse `broadcast_id` as `thread_id` so the whole fan-out shares one thread (`UBIQUITOUS_LANGUAGE.md:317`).
- Authorization: **the hub verifies the replier is the ask's target** — `handlers.ts` `handleReply` rejects with `unknown_ask` when `peeked.target !== replier`. That is the only access control in the system.

`relay_ask` is **non-blocking** — it returns `{ok, ask_id}` immediately and the reply arrives later as a notification (`docs/architecture.md:265`, a documented reversal of an earlier blocking design that "lost a race with its own client-side timeout").

### Self-improvement

**Absent.** No memory field, no cross-session learning, no persistence of any kind. `README.md:124-128` "Out of scope" states it outright: *"No persistence — peer state lives in the hub process only"*, *"Single user per machine; no auth or access control"*, *"Same-host only; no cross-machine relaying"*. `docs/architecture.md:261` — *"In-memory only... A peer that disconnects is gone."*

### Cross-vendor

**No.** The brief flagged this as a "prime suspect" — it is not one. Absence probe: `grep -rniE "codex|gemini|openai|grok|opencode|litellm"` across all `*.ts`/`*.md`/`*.json` (excluding `bun.lock`) → **0 hits**. Control arm on the same corpus and command shape: `relay_broadcast` → **21 hits**. Relay routes only between Claude Code sessions; the transport is Claude Code's own `notifications/claude/channel` capability, which no other vendor's CLI implements.

### Maturity (measured 2026-08-04)

61 stars, 12 forks, **0 open issues**, MIT, created 2026-04-21, last push 2026-08-03. Effectively **single-author**: `vildanbina` 20 commits vs `Jeff-Lebowski` 1 (`gh api repos/.../contributors`). Releases v0.1.1 → v0.1.5, cadence roughly monthly with a 2.5-month gap (v0.1.4 2026-05-19 → v0.1.5 2026-08-03). 74 tests, ~1.5 s (`docs/architecture.md:271`); CI in `.github/workflows/ci.yml`; husky pre-commit runs `bun run check` (typecheck + eslint + prettier + tests). **Still gated on a research-preview Claude Code capability** — the `--dangerously-load-development-channels` flag is a hard prerequisite, which is the single biggest adoption risk.

### WORTH STEALING

1. **`CLAUDE_RELAY_PRESET_NAME` — deterministic peer naming for orchestrator-spawned sessions.** A parent that pty-spawns N children can pre-assign each an addressable name instead of racing on directory basenames (`src/identity.ts:44-45`, `README.md:66-74`).
2. **The "quote the peer's body verbatim before acting" instruction.** `src/channel/index.ts:26` — a mechanism-level fix for a *harness* limitation (TUI truncates tool-result panels), enforced by prompt rather than hoped for. Directly applicable to our subagent-report problem: the same reasoning says a delegate's findings must land in assistant text or a file, never only in a tool result.
3. **"Never broadcast as a fallback" — an explicit anti-recovery rule in the tool description itself.** `src/channel/tool-schemas.ts:628` puts it in the *schema*, not just the system prompt, so it rides with the tool wherever it is loaded. We have the same shape of problem (an agent reaching for a wide, expensive verb after a narrow one errors).
4. **Hub-side replier authorization.** `src/hub/handlers.ts` `handleReply` refuses a reply whose sender is not the recorded `target`, returning `unknown_ask` — a two-line check that makes cross-talk impossible. Cheap and worth copying into any homegrown message table.
5. **`parent-watch.ts` — exit on stdin EOF plus a parent-pid liveness poll.** `docs/architecture.md:191`: "Claude Code sends no shutdown signal, and the MCP stdio transport ignores stdin EOF, so a channel would otherwise outlive its session forever." Versions before 0.1.5 leaked one process per session exit (`README.md:104`). Any long-lived process we spawn from a session needs exactly this.

### DEFICIENT

- **Not a multi-agent framework.** Zero roles, zero orchestration, zero DAG. For the agent-team design question it contributes a *transport idea*, not an architecture.
- **Research-preview dependency.** Requires `--dangerously-load-development-channels` on every participating session; the author himself says the flag stays "until Anthropic promotes the channels capability to general availability" (`README.md:38`). Adopting it means a launch-flag change on every session and a bet on an unshipped capability.
- **Fights this repo's conventions.** (a) It is an MCP registration for something we would build ourselves — `.claude/rules/research-doc-sources.md` § "MCP: two lanes" puts that squarely in lane 2 (avoid). (b) It spawns a **detached daemon** that survives sessions, which is exactly the shape `long-running-command-hangs.md` and the `mise run` backgrounding guard exist to police. (c) No persistence means nothing survives a `/clear`, colliding with `agent-report-persistence.md`.
- **Broadcast is machine-wide and unscoped.** `handleBroadcast` iterates every registered peer with no project/branch filter — the author mitigates by *telling Claude not to*, which is prompt-level enforcement of a thing the protocol could enforce.
- **No auth, single user, same host** (`README.md:126-128`) — stated scope, but it means any process that can open the socket can impersonate a peer at registration time.

---

## 2. Akram012388/cc-dm

**HEAD measured:** `3327e5cb926455625565b4bd1877853c48c4c858`, 2026-03-28 16:14 +0400. Plugin version `1.3.1` (`.claude-plugin/plugin.json:443`); the GitHub Releases API tops out at v1.3.0 but the `v1.3.1` **git tag exists** (`gh api repos/.../tags`) — the release was tagged without a Release object.

### What it actually is

A **Claude Code plugin: one MCP server + three skills + one hook**, TypeScript/Bun, zero deps beyond `@modelcontextprotocol/sdk`. Same problem space as claude-relay, opposite transport (**shared SQLite file + 500 ms poll**, vs a socket daemon).

Actual files (`CLAUDE.md:292-310` is the author's own inventory, verified against the tree):

- `.claude-plugin/plugin.json` — manifest with inline `mcpServers` (`bun run --cwd ${CLAUDE_PLUGIN_ROOT} --silent start`).
- `.claude-plugin/hooks/hooks.json` — **a single `PreCompact` hook** (see WORTH STEALING #1).
- `skills/cc-dm/SKILL.md` (5.2 KB), `skills/register/SKILL.md` (3.2 KB), `skills/install-stream/SKILL.md` (2.4 KB).
- `src/bus.ts` (SQLite WAL, `sessions` + `messages` tables), `src/tools.ts` (4 tool handlers), `src/server.ts` (17 KB — MCP entry, capabilities, permission relay, poll loop, shutdown), `src/heartbeat.ts`, `src/permission.ts`, `src/sanitize.ts`.
- `tests/` — 6 files, 140 tests (`CLAUDE.md:306`).
- `install.sh` (curl|bash), `AUDIT.md` (8 KB — a self-audit against the official docs), `CHANGELOG.md` (10 KB), `CLAUDE.md` (11.5 KB).

**No `agents/` directory, no commands directory.** Control arm: `ls -d agents .claude/agents commands` → all three `No such file or directory`, while `ls skills/` returns three dirs.

**Topology** (`README.md:17-25`): every session's MCP server opens `~/.cc-dm/bus.db`; a sender writes a row; every other server polls every 500 ms, delivers matching rows as `<channel>` events, then deletes the row. *"No daemon, no ports, no network. Just a shared file and a poll loop."*

### Multi-agent roles

**Roles are a first-class, user-supplied string — not a fixed set.** `CC_DM_SESSION_ROLE` defaults to `worker` (`CLAUDE.md:329`). The documented examples, enumerated verbatim:

- `README.md:123` — *"`CC_DM_SESSION_ROLE` — your role (e.g. `orchestrator`, `worker`, `reviewer`)"*
- `skills/register/SKILL.md:641` — *"What role should this session have?" (e.g., orchestrator, worker, reviewer, specialist)*
- `README.md:196` — `CC_DM_BROADCAST_ALLOWED_ROLES=orchestrator,architect`
- `README.md:10` — the motivating scenario: *"a planner, a backend worker, a test runner"*

Map to the taxonomy: **orchestrator** (`orchestrator`, also the permission `approver`), **planner** (`planner` in every example), **executor** (`worker`, the default), **qa** (`reviewer`, `tests`), **architect** (`architect`, only in the broadcast-allowlist example). Absent: researcher, adversarial-review, self-optimizer, documentation, suggestions.

Critically: **the role is a label the bus enforces authorization on, not a behaviour spec.** There is no prompt, no model, no toolset attached to a role. Two sessions with `role=reviewer` differ only in what they're allowed to broadcast.

### Per-agent configuration

**Zero Claude Code subagent frontmatter fields.** Control arm: `grep -rniE "maxTurns|permissionMode|disallowedTools|isolation:|background:|subagent"` over all `.ts`/`.md`/`.json` → **0 hits**; control on the same corpus and command shape, `role` → 25+ hits (rows printed above), so the probe reads the corpus. There is also **no `model` token anywhere** in `*.md`/`*.json` (excluding `bun.lock`, `modelcontextprotocol`).

Configuration is **entirely environment variables read once at server startup** — `src/server.ts:39-65`:

| Env var | Read at | Effect |
|---|---|---|
| `CC_DM_SESSION_NAME` | `server.ts` | Display name; sanitized (lowercase/trim/spaces→hyphens); globally unique — `handleRegister` rejects a name held by another session ID (`src/tools.ts:799-803`) |
| `CC_DM_SESSION_ROLE` | `server.ts` | Role label, default `worker` |
| `CC_DM_SESSION_PROJECT` | `server.ts` | Project tag → **outbound scoping**; a tagged session can only DM/broadcast to same-tag sessions; an untagged session reaches everyone (`CLAUDE.md:333`) |
| `CC_DM_PERMISSION_RELAY=1` | `src/server.ts:39` | Declares `claude/channel/permission` capability (`server.ts:125-128`) |
| `CC_DM_PERMISSION_APPROVER` | `src/server.ts:40` | Name of the session that approves; unset → broadcast to project, first response wins |
| `CC_DM_BROADCAST_ALLOWED_ROLES` | `src/server.ts:42-47` | Comma-separated roles permitted to broadcast; enforced at `src/tools.ts:199` |
| `CC_DM_DM_ALLOWLIST` | `src/server.ts:49-54` | Sessions this session may DM; enforced `src/tools.ts:139` |
| `CC_DM_DM_BLOCKLIST` | `src/server.ts:56-61` | Inverse; **mutually exclusive with allowlist — both set is a fatal `process.exit(1)` at `src/server.ts:63-65`** |

All access control is **sender-side only** and stated as such: `README.md:214` — *"It restricts what THIS session can send, not what it can receive. A session blocked by your allowlist can still DM you."*

Per-message config (not per-agent): `priority` ∈ {urgent, normal, low}, `message_type` ∈ {task, question, status, review}, `thread_id` (≤64 chars) — delivered as `<channel>` attributes and explicitly *"purely informational — they don't change delivery behavior"* (`README.md:161`).

### Parallelism / DAG

**No DAG, no scheduler, no dependency modelling.** Parallelism is N human-launched terminals. Fan-out is `broadcast`, and its implementation carries a hard-won correctness note (`CLAUDE.md:325`):

> "Broadcast writes **one row per recipient** with their specific session ID as `to_session`. Do not use `to_session='all'` — this causes a race condition across concurrent poll loops where whichever session polls first deletes the message, preventing other sessions from seeing it."

**What it routes and how (the brief's specific question):**

- **Substrate:** a single SQLite WAL file `~/.cc-dm/bus.db`, two tables (`sessions`, `messages`). Inspectable by hand (`README.md:236-241`).
- **Delivery:** each server `setInterval(500ms)` (`src/server.ts:322-326`) → `readPendingMessages` → `server.notification()` → `deleteDeliveredMessage`. Per-message try/catch so one failure doesn't block the batch (`CLAUDE.md:323`).
- **Addressing:** by display name, filtered by project tag on the *sender* side; a message row is simply never written for an out-of-scope recipient (`CLAUDE.md:333`).
- **Liveness:** 30 s heartbeat; 60 s no-heartbeat → session row deleted; **undelivered messages expire after 15 s** (`README.md:128`). That 15 s TTL is aggressive — a session mid-tool-call for 20 s misses the message entirely, and the skill tells Claude so (`skills/cc-dm/SKILL.md:590` "Messages expire after 15 seconds — if the sender sent the message more than 15s ago, it's gone").
- **Meta-spoofing defence:** in the poll loop, stored meta is spread **before** hardcoded routing fields so `from_session`/`to_session`/`message_id`/`sent_at` always win (`CLAUDE.md:341`). Meta keys validated against `/^[a-zA-Z0-9_]+$/` because the channels protocol *silently drops* hyphenated keys (`AUDIT.md:402`).
- **The genuinely novel route — permission relay.** `CLAUDE.md:343`: with `CC_DM_PERMISSION_RELAY=1` the server registers a handler for inbound `notifications/claude/channel/permission_request`, stores it in an in-memory `pendingPermissions: Map`, and **relays the approval request as a DM to another session**. The approver replies in natural language `yes <id>` / `no <id>`; the poll loop matches every inbound message against `VERDICT_RE = /^\s*(y|yes|n|no)\s+([a-km-z]{5})\s*$/i` (`src/permission.ts:3`) *before* regular delivery, and on a hit emits `notifications/claude/channel/permission` instead of a chat notification. 5-minute pending expiry. **So cc-dm routes two distinct things: chat messages, and tool-permission decisions.**

### Self-improvement

**None.** No cross-session learning, no `memory` field, no accumulated state beyond a session roster that self-deletes after 60 s of silence.

What it *does* have is **identity durability across compaction**, which is adjacent but not learning — two layers (`CLAUDE.md:337`): (1) every tool response is wrapped by `withIdentity()` (`src/tools.ts:66-73`) injecting `_identity: {name, role, project}` plus a `_note` string; (2) the `PreCompact` hook echoes an identity-recovery instruction.

### Cross-vendor

**No.** Absence probe: `grep -rniE "codex|gemini|openai|grok|opencode"` over all `*.ts`/`*.md`/`*.json`/`*.sh` (minus `bun.lock`) → **0 hits**; control arm on the same corpus, `broadcast` in `*.ts` → **29 hits**. Everything is Claude-Code-to-Claude-Code over the Channels protocol.

### Maturity (measured 2026-08-04)

22 stars, 9 forks, **0 open issues**, MIT. Created 2026-03-21; **last push 2026-03-28** — i.e. **~4 months stale**, by far the least maintained of the four. Effectively single-author: `Akram012388` 78 commits, `claude` 4. Eight releases in seven days (v0.1.0 → v1.3.1, 2026-03-21 → 2026-03-27) and then nothing. 140 tests. Requires Claude Code ≥ 2.1.80, **claude.ai login (not API-key auth)**, Bun, macOS-primary (`README.md:27-32`). Same research-preview gate as relay: `--dangerously-load-development-channels`, and the README's suggested alias also passes **`--dangerously-skip-permissions`** (`README.md:68`).

### WORTH STEALING

1. **A `PreCompact` hook that re-injects identity the model is about to lose.** `.claude-plugin/hooks/hooks.json:462-472` — a plain `echo` of an instruction ("call the `who` tool to recover your display name... Do NOT re-register"). This is the cheapest possible answer to "context compaction destroyed a fact the agent needs", and it generalises far past messaging.
2. **`withIdentity()` — stamp durable context onto every tool response.** `src/tools.ts:66-73` returns `{...result, _identity, _note}` so the *first* tool call after any context loss re-establishes state. A self-healing channel that costs nothing when unused.
3. **Permission relay: remote approval of another session's tool calls.** `src/server.ts:412-436` + `src/permission.ts:3` — an orchestrator session approves a worker's `Bash` call by replying `yes abcde`. This is the only mechanism in all four repos that gives one agent *runtime authority over another's* permission decisions, and it uses a documented Claude Code capability (`claude/channel/permission`) rather than a hack.
4. **Heartbeat ghost self-heal via `RETURNING id`.** `CLAUDE.md:339` — `updateHeartbeat()` returns rows-affected (bun:sqlite has no `db.changes`); 0 rows means another session's cleanup deleted you, so re-register — *and first check whether your name was stolen during the ghost window*, falling back to the session ID. A textbook "detect that the world deleted you" loop.
5. **Fan-out writes one row per recipient, never a wildcard.** `CLAUDE.md:325` — the wildcard row is a delete-race across concurrent consumers. Any homegrown work queue we build has exactly this bug latent in it.
6. **`AUDIT.md` — a self-audit artifact checked into the repo, citing the official docs it was audited against.** Includes items the author later marked `~~RESOLVED in 36b2af9~~` inline (`AUDIT.md:424`). Cheap, greppable provenance; close cousin of our `docs/rules-evidence/` pattern.

### DEFICIENT

- **Roles are labels, not behaviour.** Nothing attaches a model, prompt, toolset or permission mode to `role=reviewer`. For an agent-team design this is a naming convention with an ACL bolted on — it does not answer "how is a reviewer agent different from a worker agent".
- **Stale.** No commit since 2026-03-28 while the Channels protocol it depends on is explicitly "research preview... **Breaking changes possible** as the Channels protocol matures toward GA" (`README.md:265`). Four months of protocol drift, unmaintained.
- **500 ms poll × N sessions against one SQLite file, forever.** The author's own audit flags the missing index (`AUDIT.md:420`) and unbounded message-table growth (`AUDIT.md:422`) as open suggestions.
- **15 s message TTL is a silent data-loss window.** A recipient busy in a long tool call simply never sees the message; the mitigation is documentation telling Claude it happened.
- **Sender-side-only access control is not access control.** `README.md:214` concedes a blocked peer can still DM you. And the permission relay *bypasses* it: *"The permission relay's internal `handleDm`/`handleBroadcast` calls use default params, bypassing access control — the relay is a system-level mechanism"* (`CLAUDE.md:343`). So the one path carrying tool-authorization decisions is the one path with no allowlist.
- **Fights this repo hard.** The documented launch alias is `claude --dangerously-skip-permissions --dangerously-load-development-channels ...` (`README.md:68`) — permanently disabling the permission prompts our entire PreToolUse guard architecture (`mise-tasks-only.md`, `branch_guard`, `ask_quality`) depends on. Deterministic `deny` decisions still apply in bypass mode, but the whole approval surface goes. Plus: `install.sh` is a `curl | bash` that (per the author's own audit, `AUDIT.md:416`) writes to `~/.claude.json` — a **user-level file mutation**, which `feedback_no_user_level_file_updates` forbids outright.
- **Lane-2 MCP registration** under `research-doc-sources.md` — a server we'd register to solve our own coordination problem.

---

## 3. liatrio-labs/claude-code-gauntlet

**HEAD measured:** `097400423f4eb368fc2fc77e65e1607f865f7859`, 2026-08-04 19:48 UTC, `chore(release): 3.3.12 [skip ci]`. **This is the most sophisticated of the four by a wide margin** and the only one with a measured benchmark.

### What it actually is

A **Claude Code plugin: 12 subagent definitions + 2 skills + a JS workflow bundle + 14 Python orchestration scripts + a full benchmark harness.** No MCP server at all — `.claude-plugin/plugin.json` declares only metadata (name, version, description, author, keywords); components are discovered by convention.

- `agents/` — **12 agent `.md` files** (2.3 KB–23 KB each) plus `AGENTS.md` / `CLAUDE.md` guides.
- `skills/code-gauntlet/SKILL.md` (508 lines) + **15 reference files totalling 207 KB** (`phase2-triage.md` alone is 42.6 KB); `skills/build-review-md/`.
- `workflows/pipeline.js` (a build artifact — *"GENERATED by workflows/build.js — do not edit by hand"*, `workflows/pipeline.js:3`), assembled from `workflows/src/{stages,registry,filterFindings,mergeFindings,applyChallenges,applyValidations,findingDedup,args,pipeline_entry}.js`, with **22 test files**.
- `scripts/` — 14 Python scripts, the heavy ones being `filter_findings.py` (59 KB), `verify_findings.py` (57 KB), `await_workflow.py` (44 KB), `post_review.py` (42 KB), `assemble_artifacts.py` (32 KB).
- `bench/` — a benchmark harness with a **vendored** copy of `withmartian/code-review-benchmark`, 50 golden PRs across keycloak/grafana/sentry/cal.com/discourse, an LLM judge, an adjudicator, `baselines.json`, `report.py` (86 KB) and 16 test files.

### Multi-agent roles

Enumerated verbatim from `agents/*.md` frontmatter `description` fields:

**Seven discovery agents** (the "gauntlet"):

| Agent | Description (verbatim) | Taxonomy |
|---|---|---|
| `bug-detector` | "Detects correctness bugs, logic errors, edge cases, API misuse, and error handling issues in code changes" | qa / adversarial-review |
| `security-reviewer` | "Reviews code changes for security vulnerabilities, focusing on OWASP top 10, auth issues, data exposure, and cryptographic problems" | adversarial-review |
| `cross-file-impact` | "Analyzes how changes in one file affect consumers across the codebase, catching cross-file breakage from signature changes, interface violations, and broken references" | researcher |
| `test-analyzer` | "Analyzes test coverage quality and identifies critical gaps in the test suite relative to code changes" | qa |
| `conventions-and-intent` | "Verifies code changes comply with project conventions, match documented intent, and maintain comment accuracy" | qa / documentation |
| `type-design-analyzer` | "Analyzes type design for encapsulation quality, invariant expression, enforcement, and usefulness" | qa |
| `code-simplifier` | "Simplifies complex code for clarity and maintainability while preserving functionality" | suggestions |

**Five stage agents:**

| Agent | Description (verbatim) | Taxonomy |
|---|---|---|
| `change-summarizer` | "Produces a concise semantic summary of PR/MR changes for shared context across all review agents" | planner / context-builder |
| `validator` | "Validates review findings by attempting to disprove them — assesses whether each finding is real, reachable, and correctly described" | adversarial-review |
| `challenger` | "**Blindly** challenges a single review finding — attempts to disprove the claim using only the finding title, description, and file:line location, reading the code itself (no original reasoning or evidence)" | adversarial-review |
| `report-writer` | "Renders the code-gauntlet report markdown... Reasoning only — no disk writes." | documentation |
| `artifact-writer` | "Persists code-gauntlet artifacts... Mechanical — writes exactly what it is given." | executor |
| `executor` | "Runs a single pinned command and returns its output... No interpretation." | executor |

Unmapped in the taxonomy: **orchestrator** — the orchestrator is the *skill file itself* (Phases 1–2, 8) plus the workflow script (Phases 3–7). There is no orchestrator agent. **self-optimizer** — see Self-improvement: it exists, but as a human-run benchmark, not an agent.

Note the deliberate **role separation of reasoning from writing**: `report-writer` has `tools: Read` only and is explicitly "no disk writes"; `artifact-writer` has `Write, Read` and is "mechanical — writes exactly what it is given". The stated reason (`skills/code-gauntlet/SKILL.md`, context-file section): *"CLAUDE.md's 'Artifact persistence' section records the artifact-writer's transcription of a multi-KB payload diverging from its input on 3 of 3 measured runs."*

### Per-agent configuration

**The richest of the four — and it uses the real Claude Code subagent frontmatter fields.** Every `agents/*.md` carries `name`, `description`, `tools`, `effort`, `model`, `color`:

| Agent | `tools` | `effort` | `model` | `color` |
|---|---|---|---|---|
| bug-detector | Read, Grep, Glob, LSP | high | sonnet | red |
| security-reviewer | Read, Grep, Glob, LSP | high | **opus** | red |
| cross-file-impact | Read, Grep, Glob, LSP | high | sonnet | orange |
| test-analyzer | Read, Grep, Glob, LSP | high | sonnet | cyan |
| conventions-and-intent | Read, Grep, Glob, LSP | high | sonnet | blue |
| type-design-analyzer | Read, Grep, Glob, LSP | high | sonnet | magenta |
| code-simplifier | Read, Grep, Glob, LSP | high | sonnet | blue |
| challenger | Read, Grep, Glob, LSP | high | sonnet | orange |
| validator | Read, Grep, Glob, LSP | **medium** | sonnet | yellow |
| change-summarizer | Read | medium | sonnet | blue |
| report-writer | Read | medium | sonnet | blue |
| artifact-writer | **Write, Read** | **low** | sonnet | gray |
| executor | **Bash, Read** | low | sonnet | gray |

**Not used:** `maxTurns`, `disallowedTools`, `permissionMode`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `isolation`, `initialPrompt`. (Control arm: `grep` for `effort:` over `agents/` → 13 hits, so the probe reads frontmatter; the same grep for `maxTurns|permissionMode|memory:` → 0.)

A harness fact captured **as an inline frontmatter comment** at `agents/change-summarizer.md`:

```yaml
tools: Read  # works from prompt context only; one read-only tool satisfies the harness (zero-tool agents are refused as of Claude Code 2.1.211)
```

**The model policy is defended in code, not just frontmatter** — `workflows/src/registry.js:120-137`:

- `STAGE_DEFAULTS` restates each stage agent's `model:` frontmatter explicitly *"so a dispatch pins a full model ID instead of inheriting the session variant"*.
- `MODEL_IDS = { sonnet: 'claude-sonnet-5', opus: 'claude-opus-4-8', haiku: 'claude-haiku-4-5-20251001' }` (`registry.js:136`) — with the measured reason: *"Aliases like 'sonnet' resolve against the SESSION's model variant at dispatch time — a child session pinned to 'sonnet[1m]' cascades the [1m] variant into every agent whose policy says 'sonnet' (**measured: cache reads 15.6M→28.7M, zero plain-sonnet rows**)."*
- `CLAUDE_CODE_SUBAGENT_MODEL` is captured in Phase 2 and **warned about**, because *"it silently overrides the entire per-stage model policy, and the workflow cannot read `process.env`"*.
- Only one model tier ships: `policy.tier="optimized"` — *"the single benchmarked configuration (discovery on Sonnet with security-reviewer on Opus)"*. A REVIEW.md asking for anything else **self-heals to `optimized` with a loud warning** rather than failing.

Per-project configuration lives in a repo-root **`REVIEW.md`** (`skills/code-gauntlet/references/review-md-spec.md`, 21.5 KB) carrying `confidence_threshold`, `severity_threshold`, an `ignore` list and exclusion patterns. Defaults: non-security confidence **55**, security **70**.

### Parallelism / DAG

**The only one of the four that uses the native `Workflow` tool, and it is a hard requirement.** `skills/code-gauntlet/SKILL.md` Phase 1:

> "Before anything else, confirm the **`Workflow` tool is present in this session's available tools**. v3 orchestration is a single `Workflow` invocation; **there is no in-session fallback.**" → prints `code-gauntlet v3 requires Claude Code >= 2.1.154 with dynamic workflows` and STOPs.

The DAG is an **8-stage pipeline** declared in `workflows/pipeline.js:1`: `['summarize', 'discover', 'merge', 'verify', 'validate', 'filter', 'challenge', 'report']`. The workflow script runs in a **sandbox with no disk, no shell, and no `process.env`** — everything arrives through an args object ("the args waist") and everything produced is persisted by a writer agent.

Fan-out uses the injected runtime globals `agent()` and `parallel()`:

- **Discover** — `workflows/src/stages.js:365-378`: one `parallel()` call fanning out to every active agent; `parallel()` takes zero-arg thunks each calling `agent(prompt, opts)`, **preserves input order**, and **resolves a failed member to `null` in place** so a gap is attributable to a named agent rather than silently dropped.
- **Summarize** — small PRs get one `agent()` call; PRs > 500 changed lines are bucketed by `limits.summarizeBucketSize` through `parallel()`, then merged by a single `agent()` (`stages.js:186-223`).
- **Verify** — deliberately **sequential, not parallel** (`stages.js:576`): slice-at-a-time executor dispatch with a receipt/nonce check and at most one retry.
- **Validate** — batched through `parallel()`, positionally aligned (`stages.js:1301-1308`).
- **Challenge** — `parallel()` with **one challenger per finding** (`stages.js:1476`).
- **Report** — chunked, dispatched per chunk through `parallel()`, concatenated in index order (`stages.js:1605-1610`).

Dependencies are modelled as **stage ordering in a script**, not as a declarative graph — but they are real, and the sequencing is justified per-stage. There is also **checkpoint resume**: `stages.js:2925` — `checkpoints[name] !== undefined ? checkpoints[name] : await thunk()`, backed by `references/crash-recovery.md`.

Scope gating is opt-out and centralised: `registry.js:13-26` — `conditionalFlag: null` means UNGATEABLE (the two core dimensions `bug` and `security` always run); the other seven share a single `deep` flag, so a light-scope run stamps `{ deep: false }` and drops to two discovery agents. *"Adding a dimension = one entry here + one agent .md"* (`registry.js:1`).

### Self-improvement

**Real, measured, and human-triggered — not an agent loop.** `bench/` runs the skill headlessly against golden PRs and scores it against pinned LLM judges.

- `bench/baselines.json` pins `judge_pin: claude-opus-4-5-20251101`, `adjudicator_pin` (same), `scorer_sha`, and published anchor numbers: Claude Code CLI `precision 0.348 / recall 0.409`, with measured rows (`claude`: recall 0.339, noise_rate 0.481, precision_strict 0.392).
- `bench/MEASUREMENT.md` defines a **four-tier ratcheted ladder** with per-tier dollar costs: always-on suites → functional smoke (`--tier smoke`, 2–3 PRs, ~$21–32) → paired mini-subset (6 PRs, ~$78–85/leg) → full-15/holdout (~$190–230, "sealed"). *"It exists to give every change to the skill a repeatable, quantified answer to 'did this help or hurt,' instead of vibes"* (`bench/README.md:6-8`).
- The improvements it produced are **cited inline in the code**: `registry.js:8-11` — *"Hill-climb iter 5 uses it for two discovery-breadth sweeps grounded in the subset diagnosis (~21 never-discovered goldens)"*, feeding `SECURITY_SWEEP_PROMPT_EXTRA` and `TYPO_NAMING_SWEEP_PROMPT_EXTRA` (verbatim prompt strings appended to specific agents' prompts).
- `bench/profile_run.py` (47 KB) turns a recorded workflow run into a stage/critical-path/cost profile (`bench/PROFILING.md`).

There is **no cross-session `memory`**, no runtime learning. The loop is: measure → change a prompt → measure again → cite the iteration in a comment.

### Cross-vendor

**No for review work; yes, narrowly, for scoring.** Absence probe over `*.md`/`*.js`/`*.py`/`*.json` (excluding golden fixtures, CHANGELOG, `report.html`, `uv.lock`) for `codex|gemini|openai|grok|opencode`: **0 hits for `codex` as a CLI lane** — the only `Codex` hits are `tests/test_agent_instruction_layout.py:3,12` describing *why AGENTS.md is canonical* ("the file Codex and Cursor read natively"; "Codex truncates its concatenated instructions at 32 KiB with no notice"). Control arm: `challenger` over the same corpus → **96 hits**.

Every `openai` hit is the **vendored benchmark scorer**, and it talks to *Anthropic's* OpenAI-compatible endpoint: `bench/adjudicator/adjudicate.py:9` — *"via the Anthropic OpenAI-compatible chat-completions endpoint (spec H5)"*; `bench/vendor/VENDORED.md:121-124` documents `MARTIAN_BASE_URL` / `MARTIAN_MODEL` (upstream default `openai/gpt-4o-mini`) as the vendored harness's knobs. **No review work is offloaded to another vendor's model to save tokens.**

### Maturity (measured 2026-08-04)

11 stars, 2 forks, **46 open issues**, Apache-2.0, org-owned (`liatrio-labs`). Created 2026-03-24; last push **2026-08-04 19:48**, hours before measurement. Release cadence is extreme: **v3.3.8 → v3.3.12 in 24 hours** (2026-08-03 19:23 → 2026-08-04 19:48), semantic-release automated (`.releaserc.toml`, `[skip ci]` commits). Contributor concentration is high — `leehopper` 259 commits vs `sighup` 5, `rudi193-cmd` 1, `cursor[bot]` 1 — but it is an **organisation** repo with `CONTRIBUTING.md` (13 KB), `SECURITY.md`, `CODE_OF_CONDUCT.md`, `PRIVACY.md`, a 98 KB CHANGELOG, pre-commit config, markdownlint, and cspell. Renamed from `deep-review`. Requires **Claude Code ≥ 2.1.154**.

### WORTH STEALING

1. **Structural blindness by allowlist, not delete-list.** `workflows/src/stages.js:1412-1420` — `blindChallengeFields()` returns exactly `{title, description, file, line_start, line_end}`, and the comment states why: *"an allowlist, not a delete-list — means no confirming context... can ever reach the challenger, and stays impossible even if new reasoning-bearing fields are added to findings later."* Unit-tested both ways. This is the correct shape for any "cold review" lane, including our `codex-reviewer` / `grok-reviewer` doctrine.
2. **Pin FULL model IDs, never aliases, when dispatching subagents.** `registry.js:130-137` — an alias resolves against the *session's* model variant at dispatch, so a `sonnet[1m]` orchestrator cascades `[1m]` into every child. **Measured: cache reads 15.6M → 28.7M, zero plain-sonnet rows.** Directly relevant to us — this session is `claude-opus-5[1m]`.
3. **Measure the artifact in the same command that writes it, and pass the measurement to the reader.** SKILL.md's `contextLines`/`contextChars` stamp exists because *"A `Read` of a file this size returns only part of it and emits **no truncation notice**"*. The incident (issue #48) is stated with numbers: *"all 7 discovery agents' first `Read` of a 95,057-byte / 2,028-line context file returned 58,145 chars ending at line 1083, with no truncation notice in any of the 7 tool results. Six agents inferred the cutoff and paginated on; `security-reviewer` did not, and reviewed roughly the first half of the diff while returning `complete: true`."* This is a live hazard for **every** agent-report and context-file handoff we do.
4. **Never resolve `plugin_root` by searching the filesystem.** SKILL.md Phase 1: a recorded 2026-07-30 run used `find / -type d -name code-gauntlet`, picked **3.2.3 out of a four-version plugin cache** while 3.3.1 was installed, and reviewed with stale scripts. *"The path you were loaded from is the only correct answer; a `find` hit is a coin flip between every version ever installed."*
5. **A benchmark ladder with pre-registered tiers and dollar costs, and improvements cited back into the code.** `bench/MEASUREMENT.md` + `registry.js:8` ("Hill-climb iter 5... grounded in the subset diagnosis (~21 never-discovered goldens)"). This is the answer to "did that prompt change help" that our own rules keep asking for and cannot currently answer.
6. **Separate the reasoner from the writer.** `report-writer` (`tools: Read`, no disk) vs `artifact-writer` (`tools: Write, Read`, mechanical) — because *"the artifact-writer's transcription of a multi-KB payload diverg[ed] from its input on 3 of 3 measured runs"*. A model asked to both compose and transcribe will corrupt the transcription.
7. **Deliberate verbatim duplication of critical instructions, with an explicit anti-refactor note.** SKILL.md repeats the shell-hygiene warning in Phase 1 and Phase 2 and says so: *"A future refactor that collapses this into a single cross-reference reintroduces the exact failure it fixes."* Same doctrine in `agents/AGENTS.md` ("Do not refactor them into a shared read").
8. **Fail loud on an unguarded handoff read.** SKILL.md: `open(path).read()` on the project-rules file must be unconditional — *"A missing rules file means the collection step never ran; the write must fail loudly rather than produce a context file whose empty rules section is indistinguishable from a repo with no convention files."* That is precisely `probes-need-a-control-arm.md` rule 4 ("a redirect/timeout/parse-error is not a 'no'"), independently derived.
9. **Hunk-state diff counting instead of `git apply --numstat`.** SKILL.md Composite B: `git apply` refuses valid patches and exits non-zero with **empty stdout**, which piped to `awk` prints a false `0` — and a bare `+`/`-` prefix test miscounts content lines beginning `--`/`++`. Verified against `git diff --numstat` on a nine-case corpus. A concrete instance of our `feedback_pipe_kills_exit_code`.

### DEFICIENT

- **Single-purpose.** It reviews diffs. It is not a general agent-team framework — no planner→executor flow, no build/ship lane. For designing a general team it contributes *mechanisms*, not a topology.
- **Hard dependency on the `Workflow` tool** (Claude Code ≥ 2.1.154) with an explicit no-fallback stop. Any adoption is a bet on that tool's stability, and `Workflow` is not in this session's tool list by default.
- **Enormous instruction surface: 207 KB of skill references, one file at 42.6 KB.** That collides head-on with our `md_size_budget` gate and the whole `md-size-budgets.md` doctrine. It is also self-referentially risky — the project's own issue #48 is *"the model didn't finish reading a 95 KB file"*, and their answer was more prose about how to read it.
- **46 open issues**, and load-bearing behaviour deferred to them: alternate model tiers are "roadmap work (issue #17)", a `requiredExtra` schema mechanism is "tracked separately; do not fake it". Fields *"went years declared by no schema and silently dropped at the StructuredOutput boundary"* (`registry.js:33-37`).
- **Expensive.** `bench/README.md`: *"a full-skill code-gauntlet pass costs roughly **$8/PR**"*, scoring a run ~$2, `--tier subset` (15 PRs) ~$190–230. The skill itself says *"Cost and time concerns do not justify skipping any phase."*
- **Would fight this repo's conventions in specific places:** it writes to `.code-gauntlet/` and appends to `.git/info/exclude` (we standardise artifacts under `.agent/` and `docs/research/`, `agent-artifact-conventions.md`); it wants an `AskUserQuestion` gate that our `ask_quality` hook would judge on its own terms (recommendation + PRO/CON + citation); and the review-output path duplicates `/code-review` and `ultrareview`, which are already user-invoked here.
- **Effectively one author** despite the org badge (259 of 266 commits), on a 24-hour release cadence — high churn, low review depth per release.

---

## 4. romiluz13/cc10x

**HEAD measured:** `65a1b4261bb7ff6379ce76930f47bf9236048d97`, 2026-08-03 20:42 +0300, `feat(guide): v12.8.0 — cc10x-guide skill + documentation overhaul`.

### What it actually is

A **Claude Code plugin (marketplace-shaped repo) with 11 subagents, 21 skills, 10 wired hook events, and 10 Python hook/guard scripts.** Everything lives under `plugins/cc10x/`; the repo root is a marketplace (`.claude-plugin/marketplace.json`) plus docs and three standalone HTML explorers.

- `plugins/cc10x/agents/` — **11** `.md` agent definitions (5.1 KB–25.4 KB).
- `plugins/cc10x/skills/` — **21** skill directories: `agent-common`, `architecture`, `building`, `cc10x-guide`, `cc10x-router`, `code-review`, `codebase-design`, `codebase-hygiene`, `debugging`, `diff-driven-docs`, `domain-modeling`, `exploration`, `frontend`, `mcp-cli`, `memory-and-handoff`, `plan-review-gate`, `planning`, `research`, `resolving-merge-conflicts`, `update`, `verification`.
- `plugins/cc10x/hooks/hooks.json` + `pre-commit`; `plugins/cc10x/config/hook-mode.json`.
- `plugins/cc10x/scripts/` — 10 Python files (guards + event logger + state persist + 2 test files).
- `plugins/cc10x/tools/` — 11 Python tools incl. `worldclass_benchmark.py`, `harness_audit.py`, `latency_audit.py`, `live_harness_runner.py`, `workflow_replay_check.py`, `prompt_clause_assertions.py`.
- Root: `CHANGELOG.md` (**218 KB**), `README.md` (43 KB), `keynote.html`, `cc10x-explorer.html`, `cc10x-architecture-explorer.html`.

⚠️ **The repo description undercounts itself.** It advertises *"1 router · 9 agents · 16 skills · 4 workflows"*; measured on HEAD: `ls agents/*.md` → **11**, `ls -d skills/*/` → **21**, and the router table declares **7** workflows. Treat the marketing numbers as stale.

### Multi-agent roles

Verbatim from `plugins/cc10x/agents/*.md` frontmatter, with the router's workflow assignment:

| Agent | `description` (verbatim, trimmed) | Taxonomy |
|---|---|---|
| `planner` | "Create a saved execution plan or decision RFC when implementation work needs an agreement-first artifact before execution." | **planner** |
| `plan-gap-reviewer` | "Fresh read-only review of a saved plan when the router needs an **anti-anchoring** codebase check before plan finalization." | **adversarial-review** |
| `component-builder` | "Execute the current approved build phase with TDD when implementation work is ready to be carried out." | **executor** |
| `code-reviewer` | "**Adversarial** multi-dimensional code review — security, performance, correctness, spec compliance, maintainability. Report issues with confidence ≥80..." | **adversarial-review / qa** |
| `failure-hunter` | "Find silent failures in code — empty catches, log-only error handlers, discarded errors... **Zero tolerance for error handling that hides bugs.** Runs in parallel with code-reviewer during BUILD workflows." | **adversarial-review** |
| `integration-verifier` | "Verify built or fixed work end-to-end before any pass, completion, or workflow-advance claim, and classify proof work for latency telemetry." | **qa** |
| `bug-investigator` | "Investigate bugs, failing tests, and broken behavior when root cause must be proven before code is changed." | **researcher / executor** |
| `researcher` | "Execute web and GitHub research using Bright Data MCP, Octocode MCP, and WebSearch/WebFetch. Persist findings to dated files, return structured research contracts." | **researcher** |
| `doc-syncer` | "Sync documentation to reflect the current diff — updates business, technical, and audit doc layers." | **documentation** |
| `architecture-scanner` | "Scan the codebase for deepening opportunities — shallow modules, pass-throughs, semantic duplicates. Read-only. Produces a visual HTML report." | **self-optimizer (codebase)** |
| `triage-agent` | "Triage incoming issues and PRs — categorize, verify, check redundancy and prior rejection, write agent-ready briefs. Read-only." | **suggestions** |

**Orchestrator** is the `cc10x-router` skill (730 lines), explicitly *"THE ONLY ENTRY POINT FOR CC10X"* and *"Runtime contract only"*. It is a skill, not an agent — same choice gauntlet made.

Full coverage of the requested taxonomy — **the only one of the four that hits every slot** except a cross-session self-optimizer (see below).

### Per-agent configuration

Frontmatter fields actually used: `name`, `description`, `model`, `color`, `effort`, `tools`, **`skills`**.

| Agent | `model` | `effort` | `tools` | `skills` |
|---|---|---|---|---|
| planner | inherit | high | Read, Edit, Write, Bash, Grep, Glob, Skill, LSP, WebFetch, TaskUpdate | agent-common, planning, architecture, codebase-design, domain-modeling |
| plan-gap-reviewer | inherit | high | **Read, Grep, Glob, LSP** (no Skill) | **none — deliberate** |
| component-builder | inherit | **medium** | Read, Edit, Write, Bash, Grep, Glob, Skill, LSP, WebFetch, TaskUpdate | agent-common, building, verification, codebase-design, domain-modeling |
| code-reviewer | inherit | high | Read, Bash, Grep, Glob, Skill, LSP, WebFetch | agent-common, code-review, verification, codebase-hygiene, codebase-design |
| failure-hunter | inherit | high | Read, Bash, Grep, Glob, Skill, LSP, WebFetch | agent-common, code-review |
| integration-verifier | inherit | high | Read, Bash, Grep, Glob, Skill, LSP, WebFetch | agent-common, verification |
| bug-investigator | inherit | high | Read, Edit, Write, Bash, Grep, Glob, Skill, LSP, WebFetch, TaskUpdate | agent-common, debugging, building, verification, codebase-design |
| researcher | inherit | medium | Read, Write, Edit, Bash, WebFetch, WebSearch, TaskUpdate | agent-common, mcp-cli |
| doc-syncer | **haiku** | medium | Read, Edit, Write, Bash, Grep, Glob, TaskUpdate, Skill | agent-common, diff-driven-docs, verification, domain-modeling |
| architecture-scanner | inherit | high | Read, Bash, Grep, Glob, Skill, LSP, Write | agent-common, codebase-hygiene, codebase-design |
| triage-agent | inherit | medium | Read, Bash, Grep, Glob, Skill, LSP, WebFetch, Write | agent-common, codebase-hygiene, domain-modeling |

**Three things worth naming:**

1. **`skills:` in agent frontmatter** — the only repo of the four that uses it. Each agent declares a scoped skill set (`cc10x:agent-common` is shared by all except `plan-gap-reviewer`). This is composition, not copy-paste: `code-review` is loaded by both `code-reviewer` and `failure-hunter`, who differ only in posture.
2. **`model: inherit` everywhere except `doc-syncer: haiku`** — the opposite of gauntlet's pinned-full-IDs doctrine. `inherit` is exactly the cascade gauntlet measured at 15.6M→28.7M cache reads. Only the cheapest agent is pinned down.
3. **`plan-gap-reviewer` is configured by SUBTRACTION** — no `skills:`, no `Skill` tool, and its body says so (`agents/plan-gap-reviewer.md`): *"This is the anti-anchoring design: no memory, no preamble, no prior context... Do NOT load `.cc10x/*.md`. Do NOT infer authority from prior planner confidence, history, or planner-authored repo summaries."*

**Not used:** `maxTurns`, `disallowedTools`, `permissionMode`, `mcpServers`, `hooks`, `memory`, `background`, `isolation`, `initialPrompt`.

Session-level config lives in `.cc10x/activeContext.md` `## Session Settings`: `AUTO_PROCEED: true` sets `JUST_GO=true`, which *"auto-default[s] AskUserQuestion gates to the recommended option EXCEPT: REVERT, failure-stop gates, destructive finishing options... and plans with unresolved Open Decisions"* (`skills/cc10x-router/SKILL.md:84-90`). Hook strictness is a three-key dial in `config/hook-mode.json`: `{"artifactIntegrity": "block", "memoryWrites": "audit", "taskMetadata": "audit"}`.

### Parallelism / DAG

**A router table, not a workflow engine.** No `Workflow` tool, no tmux, no homegrown scheduler — dispatch is the plain Agent/Task tool, and parallelism is *"invoke them in the same message."*

The DAG is the router's routing table (`skills/cc10x-router/SKILL.md:22-30`), verbatim:

| Priority | Signal | Workflow | Chain |
|---|---|---|---|
| 1 | ERROR | DEBUG | `bug-investigator -> code-reviewer -> integration-verifier` |
| 2 | PLAN | PLAN | `exploration -> planner -> bounded fresh review loop` |
| 3 | REVIEW | REVIEW | `code-reviewer` |
| 4 | ORIENT | ORIENT | advisory orientation (no agents) |
| 5 | TRIAGE | TRIAGE | `triage-agent → optional exploration → agent-ready brief` |
| 6 | CODEBASE-HEALTH | CODEBASE-HEALTH | `architecture-scanner → HTML report → human picks → exploration (grilling) → feeds PLAN` |
| 7 | DEFAULT | BUILD | `component-builder → [code-reviewer ‖ failure-hunter] → integration-verifier` |

Dependencies are modelled **explicitly enough to be useful and no further**: the only parallel step is `[code-reviewer ‖ failure-hunter]`, gated by a stated invariant (`SKILL.md:713`):

> "Only parallelize agents whose file-write surfaces do not overlap. Reviewer and hunter are read-only and safe to parallelize. **Two write agents on overlapping files must be serialized.** [EASY TO MISS: Each parallel agent must have a distinct phase value and unique task description. **Identical prompts cause agents to duplicate work or silently clobber each other's output.**]"

And it has a **documented degradation path** (`SKILL.md:556`): if parallel invocation fails (API error, rate limit, agent not found) → fall back to sequential, *"Do NOT substitute the hunter with a different agent... Do NOT skip the hunter... Never block a workflow because parallelism is unavailable. Log `event=parallel_fallback` in the workflow event log."*

There is a **complexity gradient** (`SKILL.md:39`): trivial scope (1–2 files, single change, one testable outcome, no cross-module wiring) collapses to `builder → verifier → memory`; anything else runs the full chain; the builder **escalates trivial → full on any scope increase**.

Durable orchestration state: `.cc10x/workflows/{workflow_uuid}.json` plus a companion `{uuid}.events.jsonl`, with router-owned gates `plan_trust_gate`, `phase_exit_gate`, `failure_stop_gate`, `memory_sync_gate`, `skill_precedence_gate` (`SKILL.md:106-110`).

**Hook enforcement is the real differentiator — 10 events wired** (`hooks/hooks.json`): `PreToolUse` (Edit|Write → protected-write guard; Bash → git guard), `PostToolUse` (Edit|Write → workflow artifact audit), `SessionStart` (startup|resume|compact → resume context), `TaskCompleted` (task metadata guard), `PreCompact` (state snapshot), `PostCompact` (event capture), `SubagentStop` (subagent contract audit), `Stop` (state persistence), `StopFailure` (async failure logging), `InstructionsLoaded` (async instruction audit).

### Self-improvement

**The most developed of the four at the *session* level, and still not cross-session learning of the kind our `memory` field would give.** Three layers:

1. **Persistent memory** — `skills/memory-and-handoff/SKILL.md`: `.cc10x/activeContext.md` (focus, decisions, learnings, blockers), `.cc10x/patterns.md` (*"reusable project standards, gotchas, conventions, skill hints"*), `.cc10x/progress.md` (workflow, tasks, verification evidence). Stated philosophy: *"Memory is an index, not a transcript. Distill decisions, learnings, references, and verification evidence into durable, reusable notes."* The router **auto-heals** these files — inserts missing required sections before `## Last Updated`, then *"After every `Edit(...)`, immediately `Read(...)` and verify the new section exists."* This survives compaction via the `PreCompact`/`PostCompact`/`SessionStart` hook trio. It is **reinvented, not the native `memory` field.**
2. **Self-audit tooling** — `tools/harness_audit.py`, `latency_audit.py`, `workflow_replay_check.py`, `prompt_clause_assertions.py`, `doc_consistency_check.py`, `live_harness_runner.py`.
3. **`tools/worldclass_benchmark.py`** — compares cc10x against `anthropics/skills` (`skills/skill-creator`) and its own `v7.7.0` tag, writing to `docs/benchmarks/`. This is a **self-comparison / size-and-structure benchmark**, not an outcome benchmark against golden data — materially weaker evidence than gauntlet's judged golden-PR harness.

`architecture-scanner` is a self-optimizer aimed at the *user's* codebase, not at cc10x's own prompts.

### Cross-vendor

**No.** Absence probe over all `*.md`/`*.py`/`*.json` in `plugins/cc10x/` for `codex|gemini|openai|grok|opencode|antigravity` → **0 hits**. Control arm, same corpus and command shape: `code-reviewer` in `*.md` → **42 hits**. Nothing is routed to another vendor's CLI to offload tokens.

It **does** use third-party MCP servers, but for research reach, not model offload — `agents/researcher.md:3`: *"Execute web and GitHub research using Bright Data MCP, Octocode MCP, and WebSearch/WebFetch."* With an explicit backend-degradation ladder (`researcher.md:122`): `BACKEND_MODE: "brightdata+websearch" | "octocode" | "octocode+web" | "websearch+webfetch" | "websearch-only" | "webfetch-only" | "none"`, plus `SOURCES_ATTEMPTED` / `SOURCES_USED` reported separately. Both MCPs are optional and user-configured.

### Maturity (measured 2026-08-04)

**161 stars, 25 forks, 0 open issues**, MIT — the most popular of the four. Oldest too: created **2025-10-22**, last push 2026-08-03. Single-author-dominant but with a real tail: `romiluz13` **473** commits, then `ChenReuven` 3, `IdoGil-boop`/`RoiSukenik`/`yuval-raz-notch`/`yuvalraz`/`amit221`/`th3nate` 1 each. Releases: v9.1.1 (2026-03-07) → v10.1.17 (2026-04-04) → v11.0.0 (2026-06-17) → v11.1.0 (2026-06-20) → **v12.8.0 (2026-08-03)** — major versions roughly every 6–10 weeks, and a 218 KB CHANGELOG. Zero open issues on a 161-star repo is either excellent hygiene or aggressive closing; **UNVERIFIED which**.

### WORTH STEALING

1. **The "keyword NOMINATES, primary deliverable DECIDES" routing rule.** `skills/cc10x-router/SKILL.md:20` — *"A keyword hit only NOMINATES a row; the request's primary deliverable DECIDES the route (e.g. 'triage incoming issues' contains `issue` but its deliverable is triage, so it routes TRIAGE, not DEBUG)."* Ties break by priority number. This is the cleanest solution I've seen to skill-description trigger collisions, which we have several of.
2. **`skills:` in agent frontmatter as composition.** `code-reviewer` and `failure-hunter` share `cc10x:code-review` and differ only in adversarial posture — one skill, two stances, no duplicated prose. Directly applicable to our `codex-reviewer`/`grok-reviewer` pair.
3. **Anti-anchoring by subtraction, enforced in the tool grant.** `plan-gap-reviewer` gets `Read, Grep, Glob, LSP` and **no `Skill` tool and no `skills:` list**, plus a body rule *"Do NOT load `.cc10x/*.md`. Do NOT infer authority from prior planner confidence."* Making blindness a *capability* fact rather than a prompt request is the same insight as gauntlet's allowlist, reached from the other direction.
4. **Test Honesty Gates — greps that catch tests which "pass while proving nothing."** `agents/integration-verifier.md:67-95`, six named false-GREEN classes each with a runnable grep: asserting the mock (`getByTestId\(['\"][^'\"]*-mock`), schema-incomplete mocks (`as\s+(any|unknown|Partial<)`), DB-bypass verification (`\.(find|findOne|collection|query|raw)\(|readFileSync`), test-only methods in production classes, mocking-without-understanding (`mock this to be safe|better mock it|just mock`), arbitrary sleeps (`setTimeout\(|sleep\(|await delay\(`). Plus a **test-tampering** gate marked CRITICAL: `git diff HEAD -- '*.test.*' '*.spec.*' | grep -E '\.skip|\.only|expect\(\)\.not\b|\.toBe\(true\)$'`. This is `feedback_test_right_answer_wrong_reason` rendered as executable checks — the single most portable thing in all four repos.
5. **Forbidden-language list before a PASS claim.** `agents/integration-verifier.md`: *"'should pass', 'looks good', 'seems fine', 'builder reported success', 'the tests cover this' (without showing which test), 'no regressions detected' (without listing what was tested)."* An enforceable phrasing of our `verify-before-advancing.md` evidence discipline.
6. **Parallel-dispatch invariant + named degradation event.** `SKILL.md:713` (never parallelize overlapping write surfaces; distinct phase value and unique task description per agent, or they clobber) and `SKILL.md:556` (fall back to sequential, **never substitute or skip an agent**, log `event=parallel_fallback`). We have hit exactly the "agents silently clobber each other" failure.
7. **Ten hook events with a three-key strictness dial.** `hooks/hooks.json` + `config/hook-mode.json` — `block` vs `audit` per concern, so a guard can be introduced in audit mode and promoted. Notably it wires `SubagentStop` to a *contract audit*, which is the mechanism our repeatedly-failing "subagent must deliver before idle" rule actually needs.
8. **`## Session Settings` / `AUTO_PROCEED` with a carved-out exception list.** An autonomy dial that explicitly cannot auto-answer REVERT, failure-stop gates, destructive finishing options, or plans with unresolved Open Decisions — and logs every auto-choice into `## Decisions`.

### DEFICIENT

- **`model: inherit` on 10 of 11 agents is the exact hazard gauntlet measured.** A session on `claude-opus-5[1m]` (this one) would cascade the `[1m]` variant into every subagent. Where gauntlet pins full model IDs with a cache-read measurement behind it, cc10x pins nothing and calls it flexibility.
- **Self-benchmarking is self-referential.** `worldclass_benchmark.py` compares cc10x to `anthropics/skills` and to its own `v7.7.0` tag. There is no golden dataset and no independent judge — so "zero quality regression" in the plugin description is **UNVERIFIED** in the sense that matters. Contrast gauntlet's judged 50-PR harness with pinned judge SHAs.
- **Stale self-description.** "9 agents · 16 skills · 4 workflows" vs measured 11 / 21 / 7. Minor on its own; it means the README is not a reliable map of the plugin.
- **Enormous surface with a 218 KB changelog and a 730-line router skill** that the model must hold while routing, plus mandatory reference reads (*"Treat it as load-bearing orchestration law, not optional background"*). Same `md_size_budget` collision as gauntlet.
- **Would fight this repo directly.** It installs its own `PreToolUse` guards on `Edit|Write` and `Bash`, competing with our `hook_guard`/`branch_guard`/`ask_quality` chain — two independent guards on the same matchers, with our own `hook selfcheck` asserting the wiring. It writes durable state to `.cc10x/` in the repo, against `agent-artifact-conventions.md` (`.agent/` local, `docs/` tracked). It ships its own `pre-commit` hook alongside our hk chain. And `JUST_GO` auto-answering `AskUserQuestion` is the inverse of `clarify-before-acting.md`, whose gate exists precisely because that standard drifted three times.
- **Router is the sole entry point** — an all-or-nothing adoption. You cannot take the Test Honesty Gates by installing the plugin; you take the router too.
- **Optional MCP dependencies** (Bright Data, Octocode) are lane-1 under `research-doc-sources.md` (a third-party skill requires them, so allowed), but they are extra registration and auth surface for capability we largely have.

---

## Cross-cutting synthesis

**Two pairs, not four peers.** `claude-relay` and `cc-dm` solve the same problem (session↔session messaging) with opposite transports — a detached socket daemon vs a polled SQLite file — and neither is a multi-agent *framework*: zero roles between them, no orchestration, no DAG. `claude-code-gauntlet` and `cc10x` are the real frameworks, and they disagree instructively:

| | gauntlet | cc10x |
|---|---|---|
| Orchestrator | a skill + the native **`Workflow` tool** (hard requirement, no fallback) | a **730-line router skill**, plain Agent dispatch |
| Model policy | **pinned full IDs**, measured cache-read justification | `model: inherit` on 10/11 agents |
| Parallelism | `parallel()` thunks, order-preserving, `null`-on-failure | "invoke in the same message", documented sequential fallback |
| Blindness | allowlist of 5 fields into the challenger | subtraction — no `Skill` tool, no `skills:`, no memory reads |
| Evidence | 50 golden PRs, pinned LLM judge, $/tier ladder | self-comparison vs `anthropics/skills` and its own old tag |
| Memory | none (checkpoints only) | reinvented `.cc10x/` triad + compaction hooks |
| Hooks | none | **10 events**, `block`/`audit` dial |
| Scope | code review only | build / debug / plan / review / orient / triage / health |

**Nobody does cross-vendor.** All four are Claude-Code-only. The brief's suspicion about `claude-relay` is **refuted** (0 hits, control 21). Gauntlet's only non-Anthropic surface is a vendored benchmark scorer pointed at Anthropic's OpenAI-compatible endpoint. If we want a codex/gemini offload lane, none of these four is prior art — our own `fable-orchestrator` + `antigravity` setup is ahead of all of them on that axis.

**Nobody uses the native `memory` field.** cc10x reinvents it in markdown files with compaction hooks; the other three have no cross-session learning at all.

**The three highest-value transplants, ranked:**

1. **cc10x's Test Honesty Gates** (`agents/integration-verifier.md:67-95`) — six runnable greps plus a CRITICAL test-tampering check. Portable today, zero adoption cost, and it operationalises a rule we already hold but cannot enforce.
2. **gauntlet's full-model-ID pinning and its measurement** (`workflows/src/registry.js:130-137`) — a concrete, measured cost we are currently exposed to on a `[1m]` session.
3. **gauntlet's "measure the file as you write it, pass the measurement to the reader"** (issue #48: 7 agents, a 95 KB context file, silent truncation at 58,145 chars, one agent returned `complete: true` on half a diff) — this is a live hazard in our own agent-report handoffs.

Runner-up: **cc-dm's `PreCompact` identity re-injection** and **`withIdentity()`** — the cheapest known defence against context loss destroying a fact the agent needs.

## GitHub repos touched

- [vildanbina/claude-relay](https://github.com/vildanbina/claude-relay) — primary subject 1; cloned at `4a4844f`, read README, `docs/architecture.md`, `UBIQUITOUS_LANGUAGE.md`, and 8 `src/` modules.
- [Akram012388/cc-dm](https://github.com/Akram012388/cc-dm) — primary subject 2; cloned at `3327e5c`, read README, CLAUDE.md, AUDIT.md, 3 skills, `src/tools.ts`, `src/permission.ts`, `src/server.ts`, hooks.json.
- [liatrio-labs/claude-code-gauntlet](https://github.com/liatrio-labs/claude-code-gauntlet) — primary subject 3; cloned at `0974004` (v3.3.12), read all 12 agent frontmatters, `skills/code-gauntlet/SKILL.md`, `workflows/src/{registry,stages,pipeline}.js`, `bench/{README,MEASUREMENT,baselines.json,vendor/VENDORED}`.
- [romiluz13/cc10x](https://github.com/romiluz13/cc10x) — primary subject 4; cloned at `65a1b42` (v12.8.0), read all 11 agent frontmatters, `skills/cc10x-router/SKILL.md`, `hooks/hooks.json`, `config/hook-mode.json`, `skills/memory-and-handoff/SKILL.md`, `tools/worldclass_benchmark.py`.
- [withmartian/code-review-benchmark](https://github.com/withmartian/code-review-benchmark) — vendored (MIT) inside gauntlet's `bench/vendor/`; source of the golden PR corpus and the dedup/judge scorer.
- [Akram012388/cc-dm-stream](https://github.com/Akram012388/cc-dm-stream) — cc-dm's companion TUI bus viewer; referenced by `skills/install-stream/SKILL.md`, not independently inspected.
- [anthropics/skills](https://github.com/anthropics/skills) — the comparison target hardcoded in cc10x's `tools/worldclass_benchmark.py` (`skills/skill-creator`); referenced only, not fetched.

