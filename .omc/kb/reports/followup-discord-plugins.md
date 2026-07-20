# Follow-up: Discord Plugins for Mining the graphify Server

**Question.** Which Claude Code Discord plugin (if any) can *read/search* the
graphify project's Discord server (human invite `https://discord.com/invite/598Ad9zQZ`)
for discussion of backends / cost / multi-model / ingestion — and what is the
concrete, honest path to do it?

**Bottom line up front.**

- The **official Anthropic Discord plugin is a two-way *messaging channel*, not a
  history miner.** It can `fetch_messages` (≤100, oldest-first, one channel at a
  time) but Discord's search API "isn't exposed to bots", so it cannot do the
  keyword/topic mining the task needs. It is built to talk to *you*, not to crawl
  a server. (Source: official README, below.)
- The tool actually fit for mining is a **community plugin — `lycfyi/community-agent-plugin`** — which syncs a server's channel history to local Markdown and gives `discord-read` / `discord-chat-summary` keyword + date search over it.
- **The real blocker is access, not tooling.** A *human invite link is not
  programmatic read access.* To mine graphify you need either (a) a **bot** added
  to the graphify server — which requires a graphify **admin** to authorize the
  OAuth invite (Ray only holds a member invite, so he cannot do this himself), or
  (b) a **user token** for Ray's own logged-in account after he joins — which
  works without admin but is a **Discord-ToS gray area / self-bot** that risks
  account termination.

---

## 1. Official Anthropic Discord plugin

Repo: `anthropics/claude-plugins-official/external_plugins/discord`. Files:
`.claude-plugin/plugin.json`, `.mcp.json`, `server.ts` (~33 KB), `package.json`,
`bun.lock`, `ACCESS.md`, `skills/`.

**What it is.** A *channel* — a messaging bridge so you can talk to a running
Claude Code session from Discord (announced with Claude Code Channels, Mar 20
2026). `plugin.json` describes it as "Discord channel for Claude Code — messaging
bridge with built-in access control." Keywords: `discord, messaging, channel, mcp`.

**Is it MCP?** Yes. `.mcp.json` declares one stdio server:
```
command: "bun"
args: ["run","--cwd","${CLAUDE_PLUGIN_ROOT}","--shell=bun","--silent","start"]
```
i.e. it runs `server.ts` (discord.js + MCP SDK) over stdio.

**Can it read history? Barely.** Its five tools are `reply`, `react`,
`edit_message`, `fetch_messages`, `download_attachment`. `fetch_messages` pulls
"recent history from a channel (oldest-first). Capped at 100 per call." The README
is explicit about the limit that kills mining:

> "Discord's search API isn't exposed to bots, so this is the only lookback."

So there is no server-wide search, no topic query — just sequential 100-message
pages from one channel the bot can see. Everything else (`reply`, `react`,
`edit_message`) is **post/interact**, not read.

**What it requires.**
- A **Discord bot token** (`/discord:configure <TOKEN>`).
- **MESSAGE CONTENT intent** — "without this the bot receives messages with empty
  content." (So for mining, empty message bodies unless enabled.)
- OAuth bot permissions: View Channels, Send Messages, Send Messages in Threads,
  Read Message History, Attach Files, Add Reactions.
- **The bot must share the server** — "Discord won't let you DM a bot unless you
  share a server with it"; the bot is added via the generated OAuth invite URL.

**Install.**
```
/plugin install discord@claude-plugins-official
/reload-plugins
/discord:configure <TOKEN>
# restart:
claude --channels plugin:discord@claude-plugins-official
/discord:access pair <code>
```
Requires Claude Code ≥ v2.1.80, Bun runtime, Pro/Max. (code.claude.com/docs/en/channels.)

**Verdict for mining graphify:** *Wrong tool.* It is designed for you to receive
and answer messages, not to crawl and search someone else's server. The 100-msg,
no-search cap makes topic mining impractical.

---

## 2. Community plugins — read/mining capability

| Plugin | Read server history? | What it actually is | Creds |
|---|---|---|---|
| **`lycfyi/community-agent-plugin`** | **YES — the one built for this** | Syncs Discord (+Telegram) channel history to local Markdown; `discord-read` / `discord-chat-summary` do keyword + date-range search + AI summary | **Bot token** (bot-connector, ToS-OK, needs SERVER MEMBERS INTENT + bot added to server) **or user token** (user-connector, "gray area") |
| `AxiumFoundry/claude-discord-threads-plugin` | Limited (same as official) | A **derivative/fork of the official channel** — identical tool set (`fetch_messages` ≤100 oldest-first, no search API), adds private-thread support | Bot token, MESSAGE CONTENT intent, server membership, MCP (Bun + discord.js). Maintenance status not stated in README |
| `yusufkaraaslan/Skill_Seekers` | Only from **exports** | "Data layer for AI" — ingests a *pre-exported* Slack/Discord dump (`--chat-export-path`) into skills; ships a 40-tool MCP. No live Discord API, no bot | None (you supply the export file) |
| `ndjordjevic/pinrag` | Only from **exports** | RAG/MCP server; accepts "Discord export (.txt)" (e.g. DiscordChatExporter output) as an input format. No live access | None (static exports) |
| `getsocialclaw.com` (SocialClaw) | **NO** | Social *publishing* layer for agents (MCP + skill); lists Discord as a post target only ("upload media, schedule posts, publish") | Workspace API key; post-only |
| `docs.keeperhub.com` plugin | **NO** | Automation-workflow plugin; Discord is a *notification action* (post-only) | KeeperHub account / `kh` CLI |
| `AxiumFoundry` (above) | see row | — | — |
| `CloudPlayPlus/cloudplayplus-cc-plugin` | **NO Discord** | A Claude Code *channel* for a local Flutter app (same `reply/fetch_messages` channel API, but the peer is CloudPlayPlus, not Discord) | Local MCP endpoint |
| `QuantumInkDev/claude-discord-status` | **NO** | Discord **Rich Presence** — shows your Claude activity as a status. IPC via Application ID; "zero message history or server inspection capabilities" | Discord Application ID only; post/status-only |

**Also surfaced (not in the task list but relevant):**
- `zebbern/claude-code-discord` — a self-hosted **bot that runs Claude Code from
  Discord commands** (execute code, threads, MCP mgmt). It is a control surface,
  not a history miner. Bot token + Application ID; MESSAGE CONTENT intent only if
  channel-monitoring is used.
- `Tyrrrz/DiscordChatExporter` — the canonical **standalone exporter**; produces
  the `.txt`/HTML/JSON dumps that Skill_Seekers and PinRAG consume. Its own docs
  warn that automating a **user account violates Discord ToS**.

**Only `lycfyi/community-agent-plugin` mines an *existing* server's history**
through Claude Code end-to-end (sync → local files → search/summarize). The
export-based tools (Skill_Seekers, PinRAG) can also mine, but only *after* you
obtain a dump by other means (e.g. DiscordChatExporter). Everything else is
post-only, status-only, or a live two-way channel with no real search.

### How the winning path stores/searches (lycfyi)

Sync writes `data/{server_id}-{slug}/{channel}/messages.md`; `discord-read` is "a
command-line utility for reading and searching locally synced Discord messages"
(read all / last-N, keyword search, date-range, select by server ID),
`discord-chat-summary` adds AI summarization. Sync is incremental by default
(`--full` to re-pull). Install:
```
/plugin marketplace add https://github.com/lycfyi/community-agent-plugin
# then install discord-init + a connector + discord-read (+ discord-chat-summary)
```

Two connectors, with the trade-off the README states verbatim:

| | Bot Connector | User Connector |
|---|---|---|
| Member sync | Fast, complete | Cached only |
| Message sync | Yes | Yes |
| DM access | No | Yes |
| Rich profiles | No | Yes |
| **ToS compliant** | **Yes** | **Gray area** |

Bot connector needs **SERVER MEMBERS INTENT** and **the bot added to the target
server**. User connector uses "your personal account" — no admin needed — and
carries the README's own warning:

> "Using a user token may violate Discord's Terms of Service. This tool is
> intended for personal archival and analysis only. Use at your own risk."

---

## 3. Practical recommendation for graphify

**Goal:** search graphify's Discord for backends / cost / multi-model / ingestion.

**Recommended tool:** `lycfyi/community-agent-plugin` (`discord-init` +
connector + `discord-read`/`discord-chat-summary`). It is the only option that
turns an existing server's history into searchable local data inside Claude Code.
Not the official plugin (no search, 100-msg cap) and not the export tools (they
need a dump you don't yet have).

**Access is the hard part — a human invite link ≠ programmatic read.** Ray must
first *join* graphify with `https://discord.com/invite/598Ad9zQZ`. Then one of:

- **Option A — bot connector (ToS-clean but needs an admin).** Register a Discord
  application, enable SERVER MEMBERS INTENT (+ MESSAGE CONTENT intent for message
  bodies), and add the bot to the graphify server via its OAuth invite. **This
  requires "Manage Server" / admin on graphify — Ray only holds a member invite,
  so a graphify maintainer must authorize the bot.** Not automatable by Ray alone.
  *Recommended if a graphify admin will add the bot* — it is the only clean path.

- **Option B — user connector (works solo, but ToS gray area).** Use Ray's own
  logged-in-account **user token** after joining. No admin, no bot approval — it
  reads exactly what Ray can already see in the UI. **But this is a "self-bot":
  the plugin's own README and DiscordChatExporter both warn it may violate Discord
  ToS and risks account termination.** Only defensible framing is personal,
  read-only archival of a server Ray is a legitimate member of, at his own risk.

- **Option C — one-shot export (no plugin persistence).** Join, run
  **DiscordChatExporter** against the channels Ray can see, then feed the dump to
  `Skill_Seekers` or `PinRAG`. Same user-token ToS caveat as B for the export
  step; decouples mining from any live connection afterward.

**What cannot be automated / honest blockers:**
1. **Membership is a prerequisite** — no tool reads a server Ray hasn't joined.
2. **Bot path needs a graphify admin.** Ray's invite link authorizes *him* to
   join, not a bot; adding a bot is a privileged server action he cannot perform.
3. **MESSAGE CONTENT is a privileged intent.** Without it, bot-fetched messages
   have empty bodies — useless for topic mining. (Below the 100-server threshold
   it's toggle-only; still a required, deliberate step.)
4. **User tokens are ToS gray-area self-botting** — the only solo path, and it
   carries real account-ban risk; not something to run silently.
5. **No server-side search via bots at all** — even with access, the official/bot
   API has no search; mining means *syncing then searching locally*, which is
   exactly why lycfyi (local-file search) beats the official channel.

**Suggested concrete sequence (if a graphify admin is reachable → Option A):**
join server → ask a graphify maintainer to add your bot (SERVER MEMBERS + MESSAGE
CONTENT intents) → `/plugin marketplace add https://github.com/lycfyi/community-agent-plugin`
→ `discord-init` → `discord-bot-connector:discord-sync --full` over the relevant
channels → `discord-read` / `discord-chat-summary` with keywords
`backend`, `cost`, `multi-model`, `ingestion`. If no admin is reachable, Option B
(user connector) is the only solo route and must be an explicit, risk-accepted
decision by Ray — not a default.

---

## 4. Last-month trends (2026-06 / 07) on Claude Code ↔ Discord

- **Channels is now core, not preview.** Claude Code Channels (Telegram + Discord,
  launched Mar 20 2026; iMessage a week later) has settled into the official
  plugin ecosystem. VentureBeat framed it as "an OpenClaw killer." Discord is
  consistently positioned as the channel to pick *when you want message history,
  guild channels, or team collaboration* (vs Telegram) — but "history" here means
  the channel conversation with your agent, not server mining.
- **July 2026 Anthropic release notes** emphasize a "stability and safety update":
  tighter permission checks, safer Bash/PowerShell handling, background-session
  cleanup, and "better remote and **plugin** reliability" — i.e. hardening the
  channel/plugin surface rather than adding read/mining features.
- **A cottage industry of third-party "Discord read/search/sync" skills** has
  appeared on skill marketplaces (mcpmarket.com, lobehub.com, claudeskills.club) —
  `discord-sync`, `discord-read`, `discord-message-reader`, `discord-chat-summary`,
  etc. Almost all follow the same architecture as lycfyi: **sync history to local
  files first, then search offline.** This is the emergent pattern for "mine a
  Discord server," precisely because the bot API exposes no search.
- Guides proliferated (claudefa.st, DataCamp, TowardsAI, DanubeData VPS setup)
  but they cover *setting up the channel*, not history mining — reinforcing that
  Anthropic's own tooling remains conversation-bridge-first.

---

## GitHub repos touched

- [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) — official Discord channel plugin README, `plugin.json`, `.mcp.json`, file tree.
- [lycfyi/community-agent-plugin](https://github.com/lycfyi/community-agent-plugin) — the recommended history-mining plugin (sync + read/summarize); connector trade-off + ToS warnings.
- [AxiumFoundry/claude-discord-threads-plugin](https://github.com/AxiumFoundry/claude-discord-threads-plugin) — official-derivative channel plugin with threads; same fetch limits.
- [yusufkaraaslan/Skill_Seekers](https://github.com/yusufkaraaslan/Skill_Seekers) — export-ingesting data-layer/MCP; no live Discord.
- [ndjordjevic/pinrag](https://github.com/ndjordjevic/pinrag) — RAG/MCP consuming Discord `.txt` exports; no live access.
- [QuantumInkDev/claude-discord-status](https://github.com/QuantumInkDev/claude-discord-status) — Rich Presence status only; no read.
- [CloudPlayPlus/cloudplayplus-cc-plugin](https://github.com/CloudPlayPlus/cloudplayplus-cc-plugin) — Flutter-app channel; not Discord.
- [zebbern/claude-code-discord](https://github.com/zebbern/claude-code-discord) — bot to run Claude Code from Discord; control surface, not miner.
- [Tyrrrz/DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter) — canonical standalone exporter feeding the export-based tools; user-token ToS warning.

Non-repo sources: getsocialclaw.com (post-only), docs.keeperhub.com (post-only),
mcpmarket.com / lobehub.com / claudeskills.club (skill marketplaces),
code.claude.com/docs/en/channels, claudefa.st, DataCamp, TowardsAI, DanubeData,
VentureBeat, releasebot.io (Anthropic July 2026 notes).
