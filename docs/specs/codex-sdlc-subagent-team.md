# Codex SDLC subagent team — settled design

**Status:** design settled by operator grilling 2026-09-14. NOT implemented.
**Research:** `docs/research/kb/reports/agents/adv-sdlc-team-2026-09-14.md`
**Primary source:** `$KB/agent-harness-docs/docs/codex/agent-configuration__subagents.md`
where `$KB=~/dev/github/ray-manaloto/knowledge-base/sources`. Codex CLI **0.154.0**.

## Why this file exists

The decisions below were reached by grilling and would otherwise survive only in a
gitignored handoff. This session's own coverage audit found that its rank-1 action
had no durable record at all (now #1116), so a settled-but-unrecorded design is the
failure mode most worth preventing here.

## Verified mechanism — cite these, do not re-derive

| # | Fact | Evidence |
|---|---|---|
| 1 | Custom agents are standalone TOML under `.codex/agents/` (project) or `~/.codex/agents/` (personal) | `subagents.md:234` |
| 2 | Required fields: `name`, `description`, `developer_instructions` | `subagents.md:276` schema table |
| 3 | Agent files may also carry `model`, `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`, `skills.config` | `subagents.md:284` |
| 4 | `name` is the identity; filename is convention only | `subagents.md:286-288` |
| 5 | Built-ins `default`, `worker`, `explorer`; a custom agent with a built-in's name WINS | `subagents.md` §Global settings notes |
| 6 | `[agents]` globals: `enabled` (default true), `max_concurrent_threads_per_session` (legacy alias `max_threads`), `default_subagent_model`, `default_subagent_reasoning_effort`, `interrupt_message` (default true) | `subagents.md:258` table |
| 7 | Delegation is PROMPT-TRIGGERED. Codex itself spawns, routes, waits, and closes threads | `subagents.md:87-88`, §Orchestration |
| 8 | `multi_agent` is `stable true` by codex's OWN default, not set in our config | `codex features list`; control: 140 features, `code_mode` -> 6 |
| 9 | **Headless `codex exec` DOES spawn subagents** — measured, not assumed | see §Verification below |

### ⚠️ Precedence is NOT uniform — this was corrected during design

Verbatim, `subagents.md:248-254`:

> "If a custom agent file sets `model` or `model_reasoning_effort`, the value in the
> file takes precedence. **Otherwise**, Codex resolves each setting independently: an
> explicit spawn value, then the corresponding `[agents]` default, then the parent's
> value. … Other session settings, such as `sandbox_mode`, `mcp_servers`, and
> `skills.config`, **inherit from the parent when the custom agent file omits them**."

So: the agent file pre-empts only for `model`/`model_reasoning_effort`. **`mcp_servers`
inherits the parent's full set unless declared.** A coordinator's earlier claim that
the agent file wins universally was wrong.

### ⚠️ Model names — one proposed name does not exist

Real names, from the docs: `gpt-5.1-codex-max`, `gpt-5.2`, `gpt-5.3-codex`,
`gpt-5.3-codex-spark`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.5`, `gpt-5.6`,
`gpt-5.6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra`.

The advisor's roster proposed **`gpt-5.3-spark`** for two agents. That is not a model;
the real name is **`gpt-5.3-codex-spark`**. Both would have failed on first spawn.

## Settled decisions

### D1 — Roster shape: artifact-keyed, gate-owned, phase-instructed

One agent per ARTIFACT, because `description` is what codex routes on and artifacts
are naturally disjoint where phases are not (`design` and `implement` overlap, and
description collision is the documented wrong-agent routing risk). Each agent OWNS a repo
gate, so its success signal is that gate's real rc. PHASE is expressed inside
`developer_instructions`, where it cannot cause wrong-agent routing.

Artifact axes present in this repo: `python/`, `*.pkl` + `hk.pkl`, `.github/`,
`.devcontainer/` + image, `docs/` + `.claude/rules/`, `tests/`.

### D2 — A dispatcher agent adjusts the team per task

Beyond the fixed base roster, a dispatcher agent selects and ADJUSTS the team for the
task at hand, and may add further subagents when required. This is additive to D1, not
a replacement.

⚠️ Tension to resolve at implementation time: the advisor recommended `AGENTS.md`
instruction blocks over a dispatcher, on the grounds that codex already routes by
description — and `.claude/rules/use-tool-builtins.md` requires written justification
before duplicating a native mechanism. The operator chose the dispatcher anyway, for
the dynamic add/adjust capability descriptions alone cannot provide. Record that
justification in the implementing PR.

### D3 — `mcp_servers` declared explicitly on EVERY agent

Because of the inherit-on-omit rule above, omitting the key silently grants the
parent's entire tool surface, which makes "specialist" fiction. Every agent file
declares its own.

### D4 — The five research plugins are ALREADY native, installed and enabled

Measured via `codex plugin list` across **18** configured marketplaces:

| plugin | status | source |
|---|---|---|
| `context7@context7-marketplace` | installed, enabled 1.0.1 | own marketplace |
| `exa@claude-plugins-official` | installed, enabled 3.4.1 | `exa-labs/exa-mcp-server.git` |
| `firecrawl@claude-plugins-official` | installed, enabled 1.0.9 | `firecrawl/firecrawl-claude-plugin.git` |
| `last30days@last30days-skill` | installed, enabled 3.24.0 | `mvanhorn/last30days-skill.git` |
| `openaiDeveloperDocs` | enabled (remote MCP) | `developers.openai.com/mcp` |

**Nothing needs adding.** An earlier claim that `firecrawl` and `last30days` were
absent came from two bounded probes: searching `codex mcp list` (servers, not plugins)
and truncating `codex plugin list` after the first two of 18 marketplaces.

### D5 — Schema: generate version-exact, ship as a skill, gate in doctor

`codex app-server generate-json-schema --out ./schemas` emits a bundle specific to the
exact codex version run (`app-server.md:112-116`) — preferred over the "latest" URL at
`config-file__config-reference.md:1603`, which can describe settings 0.154.0 lacks.
This also satisfies the requirement for a searchable inventory of every setting and
environment variable.

Currency is layered (operator chose all three, plus a fourth):
1. `currency.toml` + the shared engine (`mise run tool-currency`, `tool-currency-check`)
2. a `doctor.toml` assertion that the schema matches the installed codex version
3. Renovate carrying the codex pin bump
4. **a Claude function hook** that flags a stale/outdated dependency version

⚠️ **Trap:** a `# :schema` directive written WITH A SPACE is INERT (measured, session
2026-09-10c). Get the directive form right and pin it with a fail-arm test.

### D6 — Self-optimizing/self-healing/self-learning is OUT OF SCOPE here

Codex "Memories" is a ChatGPT-account feature for carrying context between chats, not
per-agent performance learning (`app__settings.md:108-111`, `chrome-extension.md:155`).
No native mechanism was found. Scoped out deliberately as its own design.

## Verification already performed

Headless spawn, on the path our lanes actually use:

```
printf '%s\n' "<spawn-two-subagents prompt>" | codex exec --ephemeral -s read-only -o <out> -
rc=0
```

Its report: *"I actually spawned two subagents in parallel and waited for both. I did
not perform the checks myself. The initial spawn attempt failed, so I retried it
successfully before spawning the second agent."*

Control-armed: both returned values correct (`.claude/agents/` -> 23 files; README
first line `# Reproducible Dotfiles (AMD64)`), and 7 spawn/subagent mentions in the run
log. **Design input:** spawn is not perfectly reliable — the first attempt failed and
codex self-retried. Any orchestration must tolerate that.

## Not yet decided

- The concrete agent names, descriptions, and `developer_instructions` per artifact.
- Which of the five plugins each role declares.
- Whether the dispatcher is an agent file, a skill, or an `AGENTS.md` block.
- Whether `CLAUDE_CODE_VERSION` (currently `2.1.270` in `mise.toml [env]`) should track
  the native install, now at 2.1.271.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the subject.
- [exa-labs/exa-mcp-server](https://github.com/exa-labs/exa-mcp-server) — source of the enabled `exa` codex plugin.
- [firecrawl/firecrawl-claude-plugin](https://github.com/firecrawl/firecrawl-claude-plugin) — source of the enabled `firecrawl` codex plugin.
- [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) — source of the enabled `last30days` codex plugin.
