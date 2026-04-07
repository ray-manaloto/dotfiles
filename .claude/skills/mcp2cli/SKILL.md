---
name: mcp2cli
description: Invoke MCP servers as one-shot CLI commands (no native registration, no schema injection into Claude's context). Use whenever a research or tool-use task wants an MCP server's capabilities without paying the per-conversation context tax of `claude mcp add`.
---

# mcp2cli — MCP servers as CLI, no context tax

`mcp2cli` runs an MCP server as a subprocess, calls a single tool, prints
the result, and exits. Unlike `claude mcp add`, nothing is registered with
Claude Code, so **no tool schemas land in Claude's system prompt**. This
is the only sanctioned way to reach MCP servers from this repo.

> See `feedback_no_mcp_registration.md` and
> `.claude/rules/research-doc-sources.md` for the full rationale.

## When to use this skill

Use `mcp2cli` when any of these are true:

- You need a capability an MCP server exposes (GitHub API, Docker, a
  mintlify per-repo search, etc.) and you would otherwise be tempted to
  `claude mcp add` it.
- You want to call an MCP tool from a Bash one-liner (script, hk step,
  mise task, ad-hoc research).
- You want fuzzy search across a doc site's mintlify-hosted content
  without pulling HTML by hand.

Do **not** use it for:

- Plain web fetches of `llms.txt` or per-page `.md` — use `curl` directly,
  it is strictly cheaper. See the preference chain in
  `.claude/rules/research-doc-sources.md`.
- Registering MCP servers — that is precisely what this skill exists to
  avoid.

## Invocation patterns

### Globally-wired shorthands (from `~/CLAUDE.md`)

```bash
mcp2cli @github <tool> [args...]      # GitHub operations
mcp2cli @docker <tool> [args...]      # Docker operations
```

The `@<name>` form resolves through the user-global `mcp2cli` config.
Shorthands are the preferred call shape when one exists — they hide the
transport URL and any auth plumbing.

### Direct MCP URL (no config entry required)

```bash
mcp2cli --mcp <server-url> <tool> --param value [--param value ...]
```

Use the `--mcp <url>` flag, followed by the tool subcommand and its
own args. The tool subcommand must be spelled in **hyphenated form**
(argparse normalizes `_→-` at the CLI layer — see "Tool-name
normalization" below).

Example — query Mintlify's own platform docs (the only mintlify MCP
server reliably reachable without credentials):

```bash
# List tools exposed by the server
mcp2cli --mcp https://mintlify.com/docs/mcp --list

# Fuzzy search Mintlify's platform docs
mcp2cli --head 5 --mcp https://mintlify.com/docs/mcp \
        search-mintlify --query "llms.txt standard"

# Fetch a specific page
mcp2cli --mcp https://mintlify.com/docs/mcp \
        get-page-mintlify --page "ai/model-context-protocol"
```

> ⚠️ **Do not use `mcp2cli` against per-repo mintlify URLs** like
> `https://mintlify.com/<owner>/<repo>/mcp`. Those are GET-only
> preview descriptors, not live MCP servers. POST returns 404. See
> `.claude/skills/mintlify/SKILL.md` for the real per-repo access
> path (`curl llms.txt` + `curl <page>.md`) and
> `docs/research/mintlify-catalog-validation-log.md` for the probe
> evidence.

### Output controls (pre-subcommand globals)

```bash
mcp2cli --jq '.items[].name' --mcp <url> <tool> ...   # jq filter on JSON output
mcp2cli --head 20            --mcp <url> <tool> ...   # truncate to first N lines
mcp2cli --pretty             --mcp <url> <tool> ...   # pretty-print JSON
mcp2cli --toon               --mcp <url> <tool> ...   # "toon" compact single-line mode
```

**Flag order matters:** `--jq`, `--head`, `--pretty`, `--toon` are
**pre-subcommand globals** and must appear BEFORE `--mcp <url>` and
the tool subcommand. Placing them after the subcommand yields
`mcp2cli: error: unrecognized arguments: --head N`.

Prefer `--jq` + `--head` early — most MCP tool responses are far
larger than the actual answer, and raw output wastes conversation
context.

### Tool-name normalization (`_ → -`)

MCP servers commonly advertise tool names with underscores (e.g.,
`search_mintlify`, `get_page_mise`), but `mcp2cli` normalizes them
to hyphens at its argparse layer because argparse subcommand choices
reject `_`. Invocation must use the hyphen form; `mcp2cli` translates
back to the wire format for you:

```bash
# WRONG — fails with "invalid choice: 'search_mintlify'"
mcp2cli --mcp <url> search_mintlify --query "..."

# RIGHT
mcp2cli --mcp <url> search-mintlify --query "..."
```

This is purely a `mcp2cli` UX artifact, not a choice by the target
MCP server.

### Auth model

`mcp2cli` reuses the server's auth. Typical options, picked per server:

- **API key / token via env var** — export before invocation
  (`GITHUB_TOKEN=... mcp2cli @github ...`).
- **OAuth** — handled by the server's own flow; `mcp2cli` passes through.
- **File-based config** — per-server credentials file pointed at via
  `--config` or the `@shorthand` entry.
- **None** — public MCP endpoints (e.g. per-repo mintlify search) need
  no auth.

When adding a new shorthand, prefer env-var or keychain-backed auth over
checking secrets into the repo.

## Why `mcp2cli` over `claude mcp add`

Registered MCP servers inject every tool's JSON schema into Claude's
system prompt for **every turn of every conversation, forever**, even
conversations that never touch the tool. For a server exposing 10 tools
with moderate schemas, that is easily several thousand tokens of
permanent context tax per conversation.

`mcp2cli` spawns the server as a subprocess for a single tool call. The
schemas never touch Claude's context, the process exits when done, and
Claude sees only the tool's textual output (which you can further
trim with `--jq`/`--head`).

Rule of thumb: **if you are about to `claude mcp add`, you almost
certainly want `mcp2cli` instead.** The exceptions require explicit user
approval and a written justification in `feedback_no_mcp_registration.md`.

## Repo wiring

- Pinned in `mise.toml` as `"pipx:mcp2cli" = "2.6.0"` — available on any
  machine after `mise install`.
- Global shorthands live in `~/.config/mcp2cli/` (user scope).
- The preference chain (`curl llms.txt → curl .md → mcp2cli → context7-cli
  → raw HTML curl`) is codified in `.claude/rules/research-doc-sources.md`.
- The ban on `claude mcp add` is enforced locally by the `no_mcp_registration`
  step in `hk.pkl` and documented in the memory rule
  `feedback_no_mcp_registration.md`.

## See also

- `.claude/skills/mintlify/SKILL.md` — the mintlify URL surface and the
  per-repo search tool names.
- `.claude/rules/research-doc-sources.md` — the full preference chain.
- `docs/research/mintlify-catalog.md` — list of mintlify-covered repos
  with their probed HTTP status.
- `feedback_no_mcp_registration.md` (auto-memory) — the constraint and
  its context-cost reasoning.
- Upstream project: <https://github.com/knowsuchagency/mcp2cli>
