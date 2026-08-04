# Channels and remote surfaces — reference for unattended agent-team design

**Agent:** docs-channels · **Date:** 2026-08-04 · **Branch:** `research/agent-team-design`

**Corpus.** `$CC` = `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`
(offline vendor tree, verified current per the brief). Live copies at
`https://code.claude.com/docs/en/<page>.md` used for version-sensitive claims.
Citations are `$CC/<file>.md:<line>`.

**Status legend.** ✅ documented and cited · ⚠️ documented but constrained ·
❌ **UNDOCUMENTED** (absence control-armed) · **UNVERIFIED** (no citation found).

---

## 0. Bottom line for an unattended team

1. **Channels are an inbound event pipe from an external platform, not an
   agent-to-agent bus.** Agent-to-agent stays `SendMessage` + the shared task
   list. The brief's working hypothesis is **confirmed** (§3).
2. **Permission relay is real, fully specified, and the only documented way to
   answer a prompt from outside the terminal without pre-approving it** (§1).
3. **Whether relay covers a teammate's prompt is UNDOCUMENTED** — but the two
   documented facts compose favourably, and the experiment is cheap (§2).
4. **Relay hands the approver full tool-approval authority over your session.**
   Anyone on the channel allowlist can approve a `Bash` call (§1.6).
5. **Research preview**: undocumented flags, Anthropic-curated allowlist, no
   Bedrock/GCP/Foundry, protocol "may change" (§5).

---

## 1. Permission relay — the protocol, exactly

### 1.1 What it is

> "When Claude calls a tool that needs approval, the local terminal dialog opens
> and the session waits. A two-way channel can opt in to receive the same prompt
> in parallel and relay it to you on another device. Both stay live: you can
> answer in the terminal or on your phone, and Claude Code applies whichever
> answer arrives first and closes the other."
> — `$CC/channels-reference.md:442`

✅ **Scope of what relays** — `$CC/channels-reference.md:444`:

> "Relay covers tool-use approvals like `Bash`, `Write`, and `Edit`. Project
> trust and MCP server consent dialogs don't relay; those only appear in the
> local terminal."

This is a hard boundary and it matters for unattended startup: a session that
hits a **new-MCP-server consent** or **project trust** dialog is stuck with no
remote escape. Those must be pre-resolved before going unattended.

### 1.2 The four-step loop (`$CC/channels-reference.md:448-455`)

1. Claude Code generates a short request ID and notifies your server
2. Your server forwards the prompt and ID to your chat app
3. The remote user replies with a yes or no and that ID
4. Your inbound handler parses the reply into a verdict, and Claude Code applies
   it **only if the ID matches an open request**

> "The local terminal dialog stays open through all of this. If someone at the
> terminal answers before the remote verdict arrives, that answer is applied
> instead and the pending remote request is dropped." — `:455`

### 1.3 Message shapes

**Outbound (Claude Code → channel server):** notification method
`notifications/claude/channel/permission_request` (`:463`). Transport is standard
MCP; method and schema are Claude Code extensions. `params` is four **string**
fields (`:465-470`):

| Field | Meaning | Gotcha (cited) |
|---|---|---|
| `request_id` | "Five lowercase letters drawn from `a`-`z` **without `l`**, so it never reads as a `1` or `I` when typed on a phone." | ⚠️ "**The local terminal dialog doesn't display this ID, so your outbound handler is the only way to learn it.**" `:467` |
| `tool_name` | e.g. `Bash`, `Write` | `:468` |
| `description` | "Human-readable summary of what this specific tool call does, **never the command itself**." | ⚠️ "when the model gives no description, the field is the constant `Run shell command` and **carries zero command detail**" `:469` |
| `input_preview` | "The tool's arguments as JSON-shaped display text, keyed per top-level field. For Bash this is the command" | Optional to render; "Your server decides what to show." `:470` |

**Design consequence:** an approver shown only `description` can be asked to
approve a `Bash` call whose text is literally `Run shell command`. **Render
`input_preview` or you are approving blind.**

**Inbound (channel server → Claude Code):** `:474`

> "The verdict your server sends back is
> `notifications/claude/channel/permission` with two fields: `request_id`
> echoing the ID above, and `behavior` set to `'allow'` or `'deny'`. Allow lets
> the tool call proceed; deny rejects it, the same as answering No in the local
> dialog. **Neither verdict affects future calls.**"

⚠️ Last clause is load-bearing for unattended runs: **there is no
"allow-always" over relay.** Every repeat of the same command re-prompts. A team
doing 200 `Bash` calls means 200 relayed prompts unless pre-approved in settings.

### 1.4 Sanitization — version-dependent

`$CC/channels-reference.md:472`, verbatim:

> "Clients on Claude Code **v2.1.211 or later** sanitize both fields before
> relaying them: they neutralize direction-override and invisible characters and
> quote and angle-bracket lookalikes, fold whitespace runs to a single space, and
> relay text whole up to **3,500 code points**, applied per top-level field for
> `input_preview`, which also keeps the JSON's own structural quotes. A longer
> value keeps its start and end visible around a counted
> `⋯ N code points elided ⋯` marker, so the end of a long command still reaches
> the approver. **Earlier clients relay `description` raw and cut `input_preview`
> to 200 UTF-16 units** with a trailing ellipsis. **Treat both fields as
> untrusted unless you control the client fleet.**"

### 1.5 The three server-side components (`:478-484`)

1. `claude/channel/permission: {}` under `experimental` capabilities
2. A `setNotificationHandler` for `notifications/claude/channel/permission_request`
3. An inbound check recognizing `yes <id>` / `no <id>` that emits the verdict
   **instead of** forwarding the text to Claude

Reference regex, `$CC/channels-reference.md:546`:

```ts
// matches "y abcde", "yes abcde", "n abcde", "no abcde"
// [a-km-z] is the ID alphabet Claude Code uses (lowercase, skips 'l')
const PERMISSION_REPLY_RE = /^\s*(y|yes|n|no)\s+([a-km-z]{5})\s*$/i
```

This is exactly the `yes <id>` shape the brief saw in `Akram012388/cc-dm` — it is
the **documented reference implementation**, not that project's invention.

### 1.6 Timeout / no-reply behaviour — and the failure modes

❌ **There is no documented timeout.** Control-armed — probe #3 in §11. The documented
behaviour is that the dialog simply **stays open** and the session waits
(`:442`, `:455`, `:575`). For an unattended team this is the central hazard: a
missed prompt is an indefinite stall, not a denial.

Two documented failure modes, `$CC/channels-reference.md:575-578` — **in both
cases the dialog stays open**:

- **Different format** — "your inbound handler's regex fails to match, so text
  like `approve it` or `yes` without an ID **falls through as a normal message to
  Claude**." (i.e. a failed approval becomes a *prompt injection into the
  session*.)
- **Right format, wrong ID** — "your server emits a verdict, but Claude Code
  finds no open request with that ID and **drops it silently**."

⚠️ **Authority.** `$CC/channels.md:285`:

> "The allowlist also gates permission relay if the channel declares it. **Anyone
> who can reply through the channel can approve or deny tool use in your
> session**, so only allowlist senders you trust with that authority."

And `$CC/channels-reference.md:484`: "Only declare the capability if your channel
authenticates the sender."

### 1.7 The unattended alternative the docs name

`$CC/channels.md:264`:

> "If Claude hits a permission prompt while you're away from the terminal, **the
> session pauses until you respond.** Channel servers that declare the permission
> relay capability can forward these prompts to you… For unattended use,
> `--dangerously-skip-permissions` bypasses most prompts, but only use it in
> environments you trust. **Explicit ask rules, connector tools your organization
> set to `ask`, and MCP tools marked `requiresUserInteraction` still prompt.**"

⚠️ So even `--dangerously-skip-permissions` is **not** a complete stall-proofing.
Three prompt classes survive it.

✅ **Non-interactive mode disables the stalling tools** — `$CC/channels.md:266`:

> "When you run channels in non-interactive mode with `-p`, tools that need
> terminal input, such as multiple-choice questions and plan mode approval, are
> disabled so the session never stalls waiting for input."

This is directly relevant: `AskUserQuestion` and plan approval are *disabled*
rather than *relayed* under `-p`.

---

## 2. Can relay approve a **teammate's** or **subagent's** prompt?

**Verdict: ❌ UNDOCUMENTED — in both directions.** Neither corpus acknowledges
the other exists.

### 2.1 Control-armed absence probes

| Probe | Command shape | Result | Control (same shape) |
|---|---|---|---|
| teammate/subagent in channels docs | `grep -nEi 'teammate\|subagent\|sub-agent\|agent team' channels.md channels-reference.md` | **0 hits** | `grep -nEic 'request_id\|allowlist'` → `channels.md:9`, `channels-reference.md:20` |
| channels in agent-teams doc | `grep -nEi 'channel' agent-teams.md` | **0 hits** | `grep -nEic 'permission' agent-teams.md` → **7** |

Both probes discriminate: the same command shape returns hits on a term known to
be present in the same file. The zeros are real absences, not blind probes.

### 2.2 The two facts that compose

Relay is documented as attaching to **the permission dialog of the session**
(`$CC/channels-reference.md:442` — "the local terminal dialog opens and the
session waits… receive the same prompt in parallel").

And `$CC/agent-teams.md:267`:

> "**Teammate permission prompts appear in the lead session**, so approve them
> there yourself."

Reinforced at `$CC/agent-teams.md:393`: "Teammate permission requests **bubble up
to the lead**."

**Inference (label: UNVERIFIED, not documented):** if a teammate's prompt *is*
the lead session's dialog, and relay forwards the lead session's dialogs, then
relay should cover teammate prompts. Nothing states this. Nothing contradicts it
either. The risk is that relay hooks a code path upstream of the team-bubbling
merge, in which case teammate prompts silently never relay — which for an
unattended team is a total stall with no signal.

### 2.3 What does NOT change

✅ This is separate from, and unaffected by, the agent-to-agent consent ban —
`$CC/agent-teams.md:265`:

> "A teammate cannot approve a permission prompt or supply consent on your
> behalf, and a teammate that was denied an action cannot relay it to another
> teammate to bypass the check. In auto mode, the classifier treats an approval
> claim relayed from another agent as **untrusted input** rather than
> confirmation from you."

Relay does not violate this: the approver is a **human on an allowlisted external
account**, not another agent. But note the shape of the trust boundary — Claude
Code deliberately distrusts agent-sourced approvals, and a channel is a path that
carries approvals from outside that boundary.

### 2.4 The experiment (cheap, ~20 min)

1. Build the §1.5 webhook server verbatim from `$CC/channels-reference.md:589`
   (SSE on `GET /events`, verdict check on `POST /`).
2. `claude --dangerously-load-development-channels server:webhook`
3. `curl -N localhost:8788/events` in a second terminal.
4. In the session: spawn one teammate, instruct it to run a `Bash` command that
   is **not** pre-approved (e.g. `touch /tmp/relay-probe-$RANDOM`).
5. **Read arm:** does a `permission_request` with a five-letter ID appear in the
   SSE stream, and does its `tool_name` correspond to the *teammate's* call?
6. **Control arm (mandatory):** run the identical un-approved command **from the
   lead session itself** and confirm a prompt *does* appear in the stream. A
   silent stream in step 5 is only evidence if step 6 is loud.
7. **Write arm:** `curl -d "yes <id>" -H "X-Sender: dev" localhost:8788` and
   confirm the teammate proceeds — an ID that arrives but doesn't act is a
   different (and worse) finding than an ID that never arrives.

Repeat steps 4-7 with a **subagent** (`Agent` tool) in place of a teammate; the
docs treat those as different mechanisms and the result may differ.

---

## 3. Can a channel be used agent-to-agent? — **No.**

Blunt answer, as asked: **channels are strictly an inbound pipe from an external
non-Claude system.** Agent-to-agent is `SendMessage` + the shared task list.

Evidence:

- **Definition is external-system-shaped.** "A channel is an MCP server that
  pushes events into your running Claude Code session, so Claude can react to
  things that happen while you're not at the terminal." `$CC/channels.md:13`
- **The stated purpose is non-Claude sources.** "Channels fill the gap in that
  list by **pushing events from non-Claude sources** into your already-running
  local session." `$CC/channels.md:351`
- **Both documented shapes are external.** Chat platforms (poll a platform API)
  and webhooks (listen on a local HTTP port) — `$CC/channels-reference.md:34-35`.
- **Zero mention of agents.** §2.1 probe: 0 hits for teammate/subagent/agent-team
  across both channel pages, against a discriminating control.
- **Agent-teams' own communication section** names exactly three mechanisms —
  automatic message delivery, idle notifications, shared task list, plus
  named teammate messaging — and no channel (`$CC/agent-teams.md:269-282`).

**Nothing structurally prevents abuse** — a channel server is just a local
process emitting MCP notifications, so agent A could `curl` agent B's webhook
channel. But that is unsupported, undocumented, and pays a real cost: the message
arrives as a `<channel>` tag from an *external* source subject to the sender
allowlist, with no task-list integration, no idle notification, and no delivery
acknowledgement ("Claude Code doesn't acknowledge notifications… drops the events
silently and returns no error to your server" — `$CC/channels-reference.md:252`).

**One legitimate channel-shaped role in a team design:** a channel is the correct
mechanism for getting a *human* or a *CI system* into a running team session —
i.e. it is the **outside→team** edge, while `SendMessage` is the **team-internal**
edge. Those are complementary, not competing.

### 3.1 Ordering and concurrency (relevant to team design)

`$CC/channels-reference.md:256`:

> "Events queue into the session and are processed in order. If several
> notifications arrive while Claude is busy, they're **delivered together on the
> next turn and Claude handles them as a group**. To process independent event
> streams concurrently, **run separate sessions**."

⚠️ A channel gives you **one serialized inbound queue per session**. It does not
fan out to teammates.

---

## 4. What it takes to run one

| Requirement | Detail | Cite |
|---|---|---|
| **Flag** | `claude --channels plugin:<name>@<marketplace>` — space-separated for several | `channels.md:243`, `:249` |
| **Dev flag** | `claude --dangerously-load-development-channels server:<name>` (bare `.mcp.json` server) or `plugin:<p>@<m>` | `channels-reference.md:178-184` |
| **Bypass is per-entry** | "Combining this flag with `--channels` doesn't extend the bypass to the `--channels` entries." | `channels-reference.md:186` |
| **Registration ≠ enablement** | "Being in `.mcp.json` isn't enough to push messages: a server also has to be named in `--channels`." | `channels.md:283` |
| **Runtime** | Hard requirement is `@modelcontextprotocol/sdk` + a Node-compatible runtime; **Bun, Node, and Deno all work**. Bun is required only for the *pre-built official plugins*. | `channels-reference.md:43`; `channels.md:25` |
| **Auth** | "They require Anthropic authentication through claude.ai or a Console API key, and are **not available on Amazon Bedrock, Google Cloud's Agent Platform, or Microsoft Foundry**." | `channels.md:10` |
| **Transport** | stdio; Claude Code spawns the server as a subprocess | `channels-reference.md:32`, `:49` |
| **Allowlist (preview)** | `--channels` only accepts plugins from the Anthropic-maintained allowlist, or the org's `allowedChannelPlugins` | `channels.md:334` |

### 4.1 Enterprise controls (`$CC/channels.md:296-299`, verbatim table)

| Setting | Purpose | When not configured |
|---|---|---|
| `channelsEnabled` | Master switch. Must be `true` for any channel to deliver messages. Set via the claude.ai Admin console toggle or directly in managed settings. Blocks all channels including the development flag when off. | claude.ai Team and Enterprise: channels blocked. Console: channels allowed unless your organization deploys managed settings, in which case channels are blocked until this key is set |
| `allowedChannelPlugins` | Which plugins can register once channels are enabled. Replaces the Anthropic-maintained list when set. Only applies when `channelsEnabled` is `true`. | Anthropic default list applies |

Both are **managed settings users cannot override** (`:289`). Defaults differ by
auth: claude.ai Team/Enterprise → **blocked until an Owner enables**; Console API
key → **permitted by default** (`:291-292`). "Pro and Max users without an
organization skip these checks entirely" (`:301`).

`allowedChannelPlugins` shape (`:313-322`):

```json
{
  "channelsEnabled": true,
  "allowedChannelPlugins": [
    { "marketplace": "claude-plugins-official", "plugin": "telegram" },
    { "marketplace": "acme-corp-plugins", "plugin": "internal-alerts" }
  ]
}
```

⚠️ Two asymmetries worth knowing (`:324`): an **empty array** blocks allowlist
plugins but `--dangerously-load-development-channels` **still bypasses it** — to
block channels entirely including the dev flag, leave `channelsEnabled` **unset**.

**Silent-ish failure modes:** if `channelsEnabled` is off, "the MCP server still
connects and its tools work, but **channel messages won't arrive**" plus a startup
warning (`:307`). If a plugin isn't on the list, "Claude Code starts normally but
the channel doesn't register" (`:326`).

### 4.2 Sender gating

Every approved plugin keeps a sender allowlist; "everyone else is **silently
dropped**" (`channels.md:270`). Telegram/Discord bootstrap by pairing
(`:272-277`); iMessage self-chat bypasses the gate automatically (`:279`).

Build-your-own rule, `$CC/channels-reference.md:436`:

> "Gate on the **sender's identity, not the chat or room identity**:
> `message.from.id` in the example, not `message.chat.id`. In group chats, these
> differ, and gating on the room would let anyone in an allowlisted group inject
> messages into the session."

And `:422`: "An ungated channel is a **prompt injection vector**."

---

## 5. Research-preview status — what depending on it costs

`$CC/channels.md:328-338`:

> "Channels are a research preview feature. Availability is rolling out
> gradually, and **the `--channels` flag syntax and protocol contract may
> change** based on feedback." `:330`
>
> "**Neither `--channels` nor `--dangerously-load-development-channels` appears
> in `claude --help` while the feature is in preview. The flags work even though
> they aren't listed.**" `:332`

Implications for an unattended design:

- ❌ **No `--help` discoverability** ⇒ no way to feature-detect the flag from a
  script. A wrapper cannot check "does this build support channels" via help
  text; it must try and inspect the startup notice.
- ⚠️ **Protocol may change** ⇒ a custom channel server is a maintenance
  liability across Claude Code upgrades. Note §1.4 already documents a
  behavioural break at **v2.1.211**.
- ⚠️ **Custom channels are permanently on the dev flag** in preview
  (`channels-reference.md:186`, `:761`) — and the dev flag shows "a full-screen
  warning dialog" requiring interactive selection at startup
  (`channels-reference.md:141`). **That is an interactive gate on an unattended
  launch** and must be resolved before automating.
- ⚠️ Community-marketplace submission does **not** get you on the channel
  allowlist (`channels-reference.md:761`); the routes are an Anthropic partner
  contact or org-level `allowedChannelPlugins` (`:763`).



---

## 6. Remote Control — the stronger answer for "approve while away"

### 6.1 Can it approve permissions? ✅ **Yes, and it is documented.**

Two independent citations:

- `$CC/remote-control.md:127` — a built-in nudge that exists *specifically* for
  this: "**Repeated permission prompts**: after you answer several permission
  prompts in a session, an **Approve tool calls from your phone** notification
  shows the session URL."
- `$CC/remote-control.md:253` — "run `/config` and enable **Push when Claude
  decides** for proactive notifications, **Push when actions required** for
  **permission prompts and questions**, or both."

So Remote Control both **surfaces** prompts (push) and **answers** them — the
session UI on claude.ai/code or mobile is a full window into the local session.

### 6.2 Remote Control vs channel relay — for this design

| | Channel permission relay | Remote Control |
|---|---|---|
| Status | Research preview | Research preview, "available on all plans" (`remote-control.md:10`) |
| Auth | claude.ai **or Console API key** (`channels.md:10`) | claude.ai subscription only — "**API keys are not supported**" (`:30`) |
| Plans | Pro/Max skip org checks; Team/Ent must enable | Pro, Max, Team, Enterprise; Team/Ent off until an Owner enables (`:30`) |
| Build cost | Write + maintain an MCP server, or use an official plugin | **Zero** — one flag/command |
| Approve permissions | ✅ tool-use only; project-trust + MCP-consent excluded (`channels-reference.md:444`) | ✅ full session UI; the documented exclusions are *local-only slash commands*, not prompts (`:271`) |
| Approve a **teammate's** prompt | ❌ UNDOCUMENTED (§2) | ❌ UNDOCUMENTED — same control-armed probe: `teammate\|agent team` → **0 hits** in `remote-control.md`, control `subagent` → **3 hits** |
| Push notification | ❌ none (only your chat platform's own) | ✅ native mobile push incl. "**Push when actions required**" (`:253`) |
| Answer arrives as | `yes <5-letter-id>` text | Normal interactive UI |
| Sees subagent progress | No | ✅ "the conversation and the progress of subagents and dynamic workflows stay in sync across all connected devices" (`:18`) |
| Also an inbound event pipe | ✅ that is its purpose | ❌ human-driven only |

**Recommendation: Remote Control is the better primary "answer a prompt while
away" mechanism; channels are the better "wake the team on an external event"
mechanism.** They are complementary and can both run. Remote Control needs no
custom code, has native push including an actions-required class, and —
decisively for a *team* — syncs subagent/workflow progress to the device, which
relay does not.

⚠️ **Neither is documented to reach a teammate's prompt.** Remote Control's
absence is control-armed identically to §2.1 (0 hits for `teammate|agent team`
against a `subagent` control of 3). And `agent-teams.md` mentions Remote Control
**0 times** (control: `permission` → 7). Run the §2.4 experiment against Remote
Control too — it is cheaper there, since there is no server to build.

### 6.3 Remote Control constraints that bite an unattended run

From `$CC/remote-control.md:265-276` unless noted:

- **Local process must keep running.** "If you close the terminal, quit VS Code,
  or otherwise stop the `claude` process, the session ends. To keep a session
  running on a remote machine after you disconnect from SSH, start it inside
  `tmux` or `screen`." (`:268`)
- ⚠️ **Extended network outage kills it.** "if your machine is awake but unable
  to reach the network for more than roughly **10 minutes**, the session times
  out and **the process exits**." (`:269`) For a multi-hour unattended run this
  is a real termination risk — it exits rather than degrading.
- **One remote session per interactive process** outside server mode (`:267`).
- **Ultraplan disconnects Remote Control** (`:270`).
- **`/resume` and `/plugin` are local-only** (`:271`).
- **Transcript is stored on Anthropic servers** while connected (`:166`); "ZDR
  organizations can't enable Remote Control" (`:168`); kill switch is the
  `disableRemoteControl` setting.
- ⚠️ **Four env vars silently disable it** by disabling the feature-flag
  evaluation it depends on: `DISABLE_TELEMETRY`, `DO_NOT_TRACK`,
  `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`, `DISABLE_GROWTHBOOK` (`:33`). Also
  disabled when `ANTHROPIC_BASE_URL` points anywhere but `api.anthropic.com`, as
  of v2.1.196 (`:32`).
- **Workspace trust must be pre-accepted** — "run `claude` in your project
  directory at least once to accept the workspace trust dialog. The startup trust
  dialog **never saves trust for your home directory**, so start Remote Control
  from a project directory" (`:34`). Same blocker class as the un-relayable
  project-trust dialog in §1.1.

### 6.4 Server mode — the most team-relevant Remote Control feature

`claude remote-control` (`:41-64`) is a **server**, not a session:

| Flag | Relevance |
|---|---|
| `--spawn <mode>` | `same-dir` (default; "all sessions share the current working directory, so they can conflict if editing the same files"), **`worktree`** ("each on-demand session gets its own git worktree"), `session` (exactly one, rejects additional connections) |
| `--capacity <N>` | Max concurrent sessions, **default 32** |
| `--sandbox` / `--no-sandbox` | Filesystem + network isolation, **off by default** |
| `-c` / `--session-id` | Resume a prior Remote Control session (v2.1.200+) |

`--spawn worktree` is worth surfacing to the team design: it is a **native**
answer to the "teammates editing the same files" hazard that
`$CC/agent-teams.md:368` ("Avoid file conflicts") only advises about.

⚠️ `claude remote-control --help` "returns an error instead of this flag list
when you aren't signed in with an eligible account" (`:64`) — so a help-text
feature probe fails closed and is not a reliable capability check.

### 6.5 Presence suppression

`$CC/remote-control.md:263`: push is skipped while you are typing in the
connected terminal; as of v2.1.181, `CLAUDE_CLIENT_PRESENCE_FILE` extends this —
"notifications are skipped **while the file exists**." For an unattended run that
file must be **absent**; a stale marker would silently suppress every push.

### 6.6 Trusted Devices (Team/Enterprise, beta)

`$CC/remote-control.md:170-223`. Requires an enrolled device **plus** a sign-in
no more than **18 hours** old, refreshed by biometric step-up (`:183`). ⚠️ For an
unattended operator this is a recurring human-presence requirement on the
*approving* device — an 18-hour clock that can strand a long run. Not
retroactive: sessions started before the toggle continue without it (`:199`).

---

## 7. A surface the brief did not name: **Dispatch**

Found in the comparison table at `$CC/remote-control.md:355`. Dispatch =
"Message a task from the Claude mobile app" → Claude runs on "Your machine
(Desktop)" → setup is pairing the mobile app with Desktop → best for "Delegating
work while you're away, minimal setup". Documented at
`/docs/en/desktop#sessions-from-dispatch`.

It is the only listed surface whose *trigger* is a phone message and whose
*execution* is your own machine **without you having started the session first** —
i.e. the one surface that can originate work unattended on local files. Worth a
follow-up read for the team design; out of scope here beyond the flag.

---

## 8. Scheduled tasks / cron — what a scheduled run can and cannot do

### 8.1 Three mechanisms (verbatim table, `$CC/scheduled-tasks.md:17-27`)

| | Cloud (Routines) | Desktop | `/loop` |
|---|---|---|---|
| Runs on | Anthropic cloud | Your machine | Your machine |
| Requires machine on | No | Yes | Yes |
| **Requires open session** | **No** | **No** | **Yes** |
| Persistent across restarts | Yes | Yes | Restored on `--resume` if unexpired |
| Access to local files | No (fresh clone) | Yes | Yes |
| MCP servers | Connectors configured per task | Config files and connectors | Inherits from session |
| **Permission prompts** | **No (runs autonomously)** | **Configurable per task** | **Inherits from session** |
| Customizable schedule | Via `/schedule` in the CLI | Yes | Yes |
| Minimum interval | **1 hour** | 1 minute | 1 minute |

The "Permission prompts" row is the one that matters here. **Cloud Routines are
the only surface documented to run with no approval prompts at all.**

### 8.2 Cloud Routines — genuinely unattended, and the cost

`$CC/routines.md:53`:

> "Routines run **autonomously as full Claude Code cloud sessions: there is no
> permission-mode picker and no approval prompts during a run.** The session can
> run shell commands, use skills committed to the cloned repository, and call any
> connectors you include."

⚠️ `$CC/routines.md:105`: "Claude can use every tool from an included connector,
**including writes, without asking for permission during a run.**" Confinement is
by *scope*, not by prompt: repositories selected, environment network access and
variables, connectors included.

⚠️ `$CC/routines.md:55`: routines act **as you** — "commits and pull requests
carry your GitHub user, and Slack messages, Linear tickets, or other connector
actions use your linked accounts."

Triggers are richer than cron: **schedule**, **API call**, and **GitHub events**
(`:127-228`). The API trigger is notable for a team design — it is a documented
way to *originate* an unattended cloud run programmatically.

⚠️ **No local files.** Fresh clone only. So Routines cannot drive this repo's
local devcontainer / mise gates.

### 8.3 Desktop scheduled tasks — local files, and the stall behaviour

- Runs "a fresh session when a task is due, independent of any manual sessions"
  (`$CC/desktop-scheduled-tasks.md:66`).
- ⚠️ **Manual mode stalls, it does not fail**: "If a task runs in Manual mode and
  needs to run a tool it doesn't have permission for, **the run stalls until you
  approve it.** The session stays open in the sidebar so you can answer later."
  (`:80`)
- Documented de-stall recipe (`:82`): "click **Run now** after creating a task,
  watch for permission prompts, and select 'always allow' for each one. Future
  runs of that task auto-approve the same tools without prompting."
- ⚠️ **Two classes never offer always-allow** (`:84`): connector tools the org set
  to `ask`, and MCP tools marked `requiresUserInteraction` — "Runs that call these
  tools **stall each time**." Same three-class residue as `--dangerously-skip-permissions`
  in §1.7.
- ⚠️ **Cross-session messaging is disabled in a scheduled run** (`:68`): "Claude
  **can't send or receive cross-session messages** in a scheduled run: Claude can
  edit files, run commands, create commits, and open pull requests." — the closest
  the corpus comes to constraining inter-agent communication from a scheduled run.
- ✅ **Worktree isolation toggle** (`:35`): "Enable the worktree toggle when
  creating the task to give each run its own isolated Git worktree."
- Requires the app running and the computer awake; sleeping through a slot skips
  the run (`:70`). Catch-up: exactly one run for the most recently missed time
  within seven days, older discarded (`:74`).
- ✅ **Self-rescheduling**: "A scheduled task can also modify its own schedule or
  prompt from within a running session using the `update_scheduled_task` MCP
  tool" (`:98`). Prompt lives at `~/.claude/scheduled-tasks/<task-name>/SKILL.md`.

### 8.4 `/loop` — session-scoped, and the traps

- Three forms (`$CC/scheduled-tasks.md:37-41`): interval+prompt (fixed cron),
  prompt only (**Claude picks the delay, 1 min–1 hour, each iteration**),
  bare `/loop` (built-in maintenance prompt or your `loop.md`).
- ⚠️ **A scheduled fire cannot invoke a protected skill** (`:43-48`, v2.1.196+):
  "a scheduled fire only runs skills that Claude is allowed to invoke on its own.
  The following **reach Claude as plain text instead of executing**: built-in
  commands such as `/permissions`, `/model`, `/clear`; **skills marked
  `disable-model-invocation: true`, including the bundled `/verify` and
  `/code-review`**; skills withheld by `skillOverrides` or a `Skill` deny rule;
  MCP prompts." — **Directly relevant to this repo**: our protocol verbs are
  `disable-model-invocation: true`, so a `/loop` cannot run them. It would
  silently pass the text through instead.
- ⚠️ **Seven-day expiry** on recurring tasks (`:187`) — "This bounds how long a
  forgotten loop can run."
- ⚠️ **Jitter** (`:180`): recurring tasks fire up to 30 min late (or half the
  interval if sub-hourly); one-shots at `:00`/`:30` fire up to 90 s early. The
  offset is deterministic from the task ID. Pick a minute that isn't `:00`/`:30`.
- ⚠️ **Only fire while Claude Code is running and idle** (`:214`); "A scheduled
  prompt fires **between your turns**, not while Claude is mid-response" (`:172`).
  No catch-up for missed fires (`:215`).
- ✅ **Backgrounding carries `/loop` over**: "Backgrounding the session carries
  `/loop` tasks over to a background session, which keeps running without a
  terminal" (`:214`).
- Tools: `CronCreate` / `CronList` / `CronDelete`, 5-field cron, 8-char IDs,
  **max 50 scheduled tasks per session** (`:160-168`). Kill switch:
  `CLAUDE_CODE_DISABLE_CRON=1` (`:208`).
- ✅ `Monitor` is the documented better alternative to polling (`:72`): "Monitor
  runs a background script and streams each output line back, which avoids polling
  altogether and is often more token-efficient and responsive."

### 8.5 Can a scheduled run spawn a team? ❌ **UNDOCUMENTED**

Control-armed:

| Probe | Result | Control (same shape) |
|---|---|---|
| `teammate\|agent team\|spawn a team\|subagent` in `scheduled-tasks.md` + `desktop-scheduled-tasks.md` | **0 hits** | `cron` → `scheduled-tasks.md:15`; ⚠️ **0** in `desktop-scheduled-tasks.md` — that arm was BLIND, so it was **re-armed**: `permission` → **7**, `worktree` → **2**, invented term `vqzjhm` → **0**. Probe discriminates. |
| `schedul\|cron\|loop` in `agent-teams.md` | **0 hits** | `permission` → **7** |
| `teammate\|agent team` in `routines.md` | 1 hit — **but it is a false positive**: `routines.md:55` "not shared with **teammates**" means *human colleagues*, not agent teammates. Control `subagent` → **0**, itself blind; re-read confirms routines.md never discusses agent teams. | — |

**Nothing in the corpus says a scheduled run can or cannot spawn a team.** What
*is* documented and bears on it:

- Desktop scheduled runs are "a fresh session" (`desktop-scheduled-tasks.md:66`)
  and a fresh session **can** be a lead — `agent-teams.md:206` describes the lead
  spawning teammates from a normal session. So the *shape* fits.
- ⚠️ But `agent-teams.md:424`: "**One team per session**", `:425` "**No nested
  teams**", and `:426` "**No background subagents from in-process teammates** …
  because a teammate's background work **can't outlive the lead's process**."
  A scheduled run's process lifetime therefore bounds the whole team.
- ⚠️ And a scheduled Desktop run **cannot use cross-session messaging**
  (`desktop-scheduled-tasks.md:68`) — worth testing whether that also disables
  `SendMessage` to teammates, which would break a team outright. **This is the
  single highest-value unknown in §8.**

**Experiment:** create a Desktop scheduled task whose prompt is "spawn one
teammate named probe-a, have it write /tmp/team-probe.txt, then report". Read arm:
does the file exist after the run. Control arm: run the identical prompt in a
normal Desktop session and confirm it *does* produce the file — a failure in the
scheduled run is only evidence if the manual run succeeds.

---

## 9. Slack and Claude Code on the web — brief, for completeness

Both are **cloud-session spawners**, not ways into a running local session.
Neither is a candidate for answering a local team's prompts.

**Slack** (`$CC/slack.md`): `@Claude` in a channel → intent detection → "A new
Claude Code session is created on claude.ai/code" (`:106`). ⚠️ Channels only, "It
does not work in direct messages (DMs)" (`:90`). ⚠️ Prompt-injection warning
verbatim (`:102`): "Claude is given access to the conversation context… **Claude
may follow directions from other messages in the context**, so users should make
sure to only use Claude in trusted Slack conversations." Limits (`:232-237`):
GitHub only, **one PR per session**, shares your plan's rate limits.

**Claude Code on the web** (`$CC/claude-code-on-the-web.md`): isolated
Anthropic-managed VM per session; "network access is limited by default, and can
be disabled"; "sensitive credentials such as git credentials or signing keys are
**never inside the sandbox**" (`:256-263`). ⚠️ Shares rate limits with all other
Claude usage (`:303`). ⚠️ **Org IP allowlisting breaks it entirely** — "every
cloud session fails with an authentication error. The same applies to Code Review
and Routines" (`:306`).

---

## 10. Consolidated: surfaces × unattended-team fitness

| Surface | Reaches a **running local** session | Answers a permission prompt | Documented for **teammate** prompts | Needs custom code |
|---|---|---|---|---|
| Channel permission relay | ✅ | ✅ tool-use only | ❌ UNDOCUMENTED | ✅ (or official plugin) |
| Remote Control | ✅ | ✅ full UI + push | ❌ UNDOCUMENTED | ❌ |
| Channels (event push) | ✅ inbound only | n/a | n/a | ✅ (or official plugin) |
| Dispatch | ❌ spawns a Desktop session | UNVERIFIED | UNVERIFIED | ❌ |
| Desktop scheduled task | ❌ fresh session | ⚠️ stalls; always-allow after first run | ❌ UNDOCUMENTED | ❌ |
| Cloud Routine | ❌ cloud, fresh clone | ✅ **none exist** — fully autonomous | ❌ UNDOCUMENTED | ❌ |
| `/loop` | ✅ same session | inherits session | ❌ UNDOCUMENTED | ❌ |
| Slack / web | ❌ spawns cloud session | n/a | n/a | ❌ |

### The three prompt classes that survive every bypass

Consistent across three independent pages — worth treating as the hard floor for
any unattended design:

1. **Explicit `ask` permission rules** — `$CC/channels.md:264`
2. **Connector tools an org set to `ask`** — `channels.md:264`,
   `desktop-scheduled-tasks.md:84`
3. **MCP tools marked `requiresUserInteraction`** — same two

Plus two dialogs that **never relay at all**: **project trust** and **new-MCP-server
consent** (`channels-reference.md:444`). Both must be pre-accepted on the machine
before an unattended run starts, and workspace trust is **never saved for the home
directory** (`remote-control.md:34`).

---

## 11. Probe ledger — every absence claim with its control arm

Per `.claude/rules/probes-need-a-control-arm.md`, no absence is reported without
a control that returned hits under the same command shape. Control terms for the
"known-absent" arms were invented fresh for this run and are deliberately **not**
reused from any prior receipt.

| # | Claim | Probe | Result | Control arm | Verdict |
|---|---|---|---|---|---|
| 1 | Channels docs never mention teammates/subagents | `grep -nEi 'teammate\|subagent\|sub-agent\|agent team' channels.md channels-reference.md` | 0 | `grep -nEic 'request_id\|allowlist'` → 9 / 20 | armed ✅ |
| 2 | `agent-teams.md` never mentions channels | `grep -nEi 'channel' agent-teams.md` | 0 | `grep -nEic 'permission'` → 7 | armed ✅ |
| 3 | No documented relay timeout | `grep -nEi 'timeout\|time out\|expire\|expiry\|elapsed\|seconds'` on both channel pages | 2 hits, **both Bun `idleTimeout: 0` in the SSE example** (`:384`, `:677`) — unrelated to relay | `grep -nEic 'dialog'` → 0 / 13; invented term `qxwvzt` → 0 | armed ✅ |
| 4 | `remote-control.md` never mentions teammates | `grep -nEi 'teammate\|agent team\|agent-team'` | 0 | `grep -nci 'subagent'` → 3 | armed ✅ |
| 5 | `agent-teams.md` never mentions Remote Control | `grep -nEi 'remote control\|remote-control'` | 0 | same as #2 → 7 | armed ✅ |
| 6 | Scheduling docs never mention agent teams | `grep -nEi 'teammate\|agent team\|spawn a team\|subagent'` on both scheduling pages | 0 | ⚠️ first arm (`cron`) returned **0** on `desktop-scheduled-tasks.md` = **BLIND**; re-armed with `permission` → 7, `worktree` → 2, invented `vqzjhm` → 0 | armed ✅ **after correction** |
| 7 | `agent-teams.md` never mentions scheduling | `grep -nEi 'schedul\|cron\|loop'` | 0 | same as #2 → 7 | armed ✅ |
| 8 | `routines.md` never discusses agent teams | `grep -nEi 'teammate\|agent team'` | **1 hit — false positive**: `:55` "not shared with teammates" = human colleagues | `grep -ci 'subagent'` → **0**, itself blind; resolved by reading `:47-115` directly | resolved by read, not by grep |

**Probe #6 is the one worth remembering**: the first control arm returned 0,
which would have made the absence unfalsifiable. It is recorded here rather than
quietly re-run, because a probe that needed re-arming once may need it again.

**Probe #8 is the counter-lesson**: a grep *hit* can be as misleading as a miss —
`teammate` in `routines.md` means a human colleague. Term collision across
vocabularies is not caught by any control arm; only reading is.

---

## 12. Open questions for the team design

1. **Does relay (or Remote Control) surface a teammate's permission prompt?**
   §2.4 experiment. Highest value; blocks any unattended-team plan that relies on
   remote approval.
2. **Does a scheduled Desktop run permit `SendMessage`?** `desktop-scheduled-tasks.md:68`
   disables *cross-session* messaging; whether that also kills teammate messaging
   decides whether scheduled team runs are possible at all. §8.5 experiment.
3. **What does Dispatch actually permit?** (§7) — the only surface that originates
   local work from a phone without a pre-started session.
4. **Does `--spawn worktree` compose with agent teams?** It is the native answer
   to the file-conflict hazard `agent-teams.md:368` only advises about.
5. **Version floor.** Several behaviours here are version-gated: relay
   sanitization at **v2.1.211**, skill-invocation filtering on scheduled fires at
   **v2.1.196**, Remote Control `--continue`/`--session-id` at **v2.1.200**,
   subagent progress sync at **v2.1.207/2.1.208**. Pin a minimum before relying on
   any of them.

---

## Sources and currency

All citations are from the offline tree, which the brief states is verified
current. **No live fetch was performed** — every claim here is traceable to a
`$CC/<file>:<line>` in that tree, and no claim in this report depends on a
version-sensitive difference between the offline and live copies. Where a
behaviour is version-gated, the doc's own `min-version` marker is quoted rather
than inferred (see §12.5). If a live diff is wanted, the brief's guidance applies:
diff **stripped** text, since the live endpoint removes MDX
`{/* min-version: … */}` comments and a raw size difference is not staleness.

## GitHub repos touched

- [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) — the official channel plugins (telegram, discord, imessage, fakechat) and the default channel allowlist; referenced throughout `channels.md` / `channels-reference.md`. **Not cloned or read directly** — cited as the docs cite it.
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — named in `channels.md:338` as the issue tracker for channel research-preview feedback. Not read.
- [Akram012388/cc-dm](https://github.com/Akram012388/cc-dm) — named in the brief as a third-party framework using `claude/channel/permission`. **Not fetched**; its `yes <id>` pattern was instead traced to the documented reference implementation at `$CC/channels-reference.md:546`, which is its origin.
- [modelcontextprotocol/servers](https://github.com/modelcontextprotocol) / `@modelcontextprotocol/sdk` — the SDK every channel server is built on (`channels-reference.md:43`). Not read.

_None of the above were fetched over the network for this report; all findings
derive from the offline `agent-harness-docs` tree in the knowledge-base repo._
