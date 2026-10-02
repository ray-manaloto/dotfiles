# Herdr official documentation — offline mirror (2026-10-02)

Agent-optimized offline copy of Herdr's **official** documentation, pinned to the
stable release **v0.9.3** (published 2026-09-29). Herdr is "the runtime your coding
agents live on" — a terminal workspace manager that runs coding-agent CLIs
(Claude Code, codex, agy, …) in panes and exposes them through a CLI/socket API.

- Repo: <https://github.com/herdrdev/herdr> (default branch `master`, discussions on)
- Docs: <https://herdr.dev/docs/> · agent index: <https://herdr.dev/llms.txt>
- Installed here: `herdr` 0.9.3 via user-global mise (`~/.config/mise/config.toml`),
  registry `aqua:herdrdev/herdr`; the running server measured 0.9.1 (`herdr status`).

## How this was fetched

The site's own `llms.txt` says its links "return raw source files from the exact
documented revision" — `raw.githubusercontent.com/herdrdev/herdr/v0.9.3/docs/next/website/...`.
Those raw `.mdx` files are the agent-optimized form, so they were fetched with `curl`
(per `.claude/rules/research-doc-sources.md` step 1/2: llms.txt then per-page source).
`fetch.tsv` records status, bytes, file and URL for each.

- **Control arm**: a bogus raw path (`.../docs/zz-nope-q7.mdx`) returned **404** while every
  listed page returned **200**, so the fetch discriminates. Note `herdr.dev/<bogus>` returns
  **200** (SPA shell) — never judge the human site by status.
- **firecrawl cross-check**: `mise exec -- firecrawl scrape https://herdr.dev/docs/agent-automation/
  --format markdown --only-main-content` rc=0 → `firecrawl/agent-automation.md` (12.7 KB);
  content matches `pages/agent-automation.mdx`.

## Files

| File | What |
|---|---|
| `llms.txt` | Official agent index (22 pages + config reference + bundles) |
| `llms-full.txt` | Complete docs bundle (329 KB) |
| `pages/llms-small.txt` | Abridged bundle (310 KB) |
| `pages/agent-guide.md` | Agent guide (help a human set up/troubleshoot) |
| `pages/config-reference.json` | Every `config.toml` key (filter with `jq`, see `llms.txt`) |
| `urls.txt`, `fetch.tsv` | Re-run inputs and per-file fetch result |
| `firecrawl/agent-automation.md` | Human-site scrape used as a cross-check |

### Pages (raw `.mdx`, v0.9.3)

| File | Title | Description |
|---|---|---|
| [`add-herdr-support.mdx`](pages/add-herdr-support.mdx) | Add Herdr support to your agent | Report your coding agent's state and resume command to Herdr from your own code, without adding native support to Herdr. |
| [`agent-automation.mdx`](pages/agent-automation.mdx) | Agent automation | Use Herdr's layout, pane, and agent primitives to coordinate coding agents from scripts or other agents. |
| [`agent-skill.mdx`](pages/agent-skill.mdx) | Agent skill file | Install Herdr instructions for Claude Code or another coding agent. |
| [`agents.mdx`](pages/agents.mdx) | Agents | See which coding agents work with Herdr, either supported by Herdr or supporting Herdr themselves, and how agent state works. |
| [`cli-reference.mdx`](pages/cli-reference.mdx) | CLI reference | Herdr commands for sessions, workspaces, tabs, panes, notifications, agents, waits, integrations, and status. |
| [`concepts.mdx`](pages/concepts.mdx) | Concepts | Understand Herdr workspaces, tabs, panes, agents, sessions, and modes. |
| [`configuration.mdx`](pages/configuration.mdx) | Configuration | Configure Herdr keybindings, themes, sidebar behavior, notifications, and advanced options. |
| [`connecting-machines.mdx`](pages/connecting-machines.mdx) | Connecting machines | Work across Local and saved SSH machines in one Herdr window, with shared agent navigation and independent reconnects. |
| [`how-to-work.mdx`](pages/how-to-work.mdx) | How to work with Herdr | Run Herdr locally, inside SSH, or through remote attach. |
| [`index.mdx`](pages/index.mdx) | Herdr documentation | Terminal workspace manager for AI coding agents. |
| [`install.mdx`](pages/install.mdx) | Install Herdr | Install, update, and verify Herdr on Linux, macOS, and Windows. |
| [`integrations.mdx`](pages/integrations.mdx) | Integrations | Install Herdr integrations for Pi, OMP, Claude Code, Codex, GitHub Copilot CLI, Devin CLI, Droid, Kimi Code CLI, OpenCode, Kilo Code CLI, Hermes Agent, Qoder CLI, Qwen Code, Letta Code, Cursor Agent CLI, MastraCode, Antigravity CLI, and Grok CLI. |
| [`keyboard.mdx`](pages/keyboard.mdx) | Keyboard | What the prefix is, which bindings to learn first, and how to go prefix-free. |
| [`marketplace.mdx`](pages/marketplace.mdx) | Marketplace | Discover community Herdr plugins on GitHub, and get your own plugin listed. |
| [`persistence-remote.mdx`](pages/persistence-remote.mdx) | Persistence and remote access | Detach from Herdr, reattach later, use named sessions, and connect over SSH. |
| [`plugins.mdx`](pages/plugins.mdx) | Plugins | Author local Herdr plugins with manifest actions, event hooks, and panes. |
| [`quick-start.mdx`](pages/quick-start.mdx) | Quick start | Create your first Herdr workspace and run agents in persistent terminal panes. |
| [`session-state.mdx`](pages/session-state.mdx) | Session state and restore | Understand what Herdr keeps live, restores after restart, replays from history, resumes through agent integrations, and hands off during updates. |
| [`socket-api.mdx`](pages/socket-api.mdx) | Socket API | Control a running Herdr server from scripts, tools, and coding agents. |
| [`troubleshooting.mdx`](pages/troubleshooting.mdx) | Troubleshooting | Diagnose common installation, terminal input, session, keybinding, and remote access problems. |
| [`windows-beta.mdx`](pages/windows-beta.mdx) | Windows support | Native Windows support, workflows, and known limitations. |

## Start here for orchestration questions

1. `pages/agent-automation.mdx` — layout/pane/agent primitives, `agent start|prompt --wait|read`, lifecycle states.
2. `pages/socket-api.mdx` — the API under the CLI (events, subscriptions).
3. `pages/session-state.mdx` — what survives a server restart; native agent resume via integrations.
4. `pages/integrations.mdx` § Claude Code — `herdr integration install claude` writes `~/.claude/hooks/herdr-agent-state.sh` + user `settings.json`.

## Refresh

```bash
curl -fsSL https://herdr.dev/llms.txt   # read "Current stable release", then re-fetch urls.txt at that tag
```

## GitHub repos touched

- [herdrdev/herdr](https://github.com/herdrdev/herdr) — official docs source at tag v0.9.3
