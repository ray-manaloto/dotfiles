---
name: mcp2cli
description: Invoke MCP servers as one-shot CLI commands, with nothing registered in Codex. Use whenever this repo's own research or tool-use work wants an MCP server's capabilities without registering it via `codex mcp add`.
---

# mcp2cli — MCP servers as CLI, no context tax

`mcp2cli` runs an MCP server as a subprocess, calls a single tool, prints
the result, and exits. Unlike `codex mcp add`, nothing is registered with
Codex. This is the **preferred** way for this repo's own work to reach
an MCP server; native registration is allowed when a third-party plugin
requires it.

> See `feedback_no_mcp_registration.md` and
> `.claude/rules/research-doc-sources.md` for the full rationale.

## When to use this skill

Use `mcp2cli` when any of these are true:

- You need a capability an MCP server exposes (GitHub API, a live
  customer-domain docs MCP, etc.) and you would otherwise be tempted to
  `codex mcp add` it.
- You want to call an MCP tool from a Bash one-liner (script, hk step,
  mise task, ad-hoc research).

Do **not** use it for:

- Plain web fetches of `llms.txt` or per-page `.md` — use `curl` directly,
  it is strictly cheaper. See the preference chain in
  `.claude/rules/research-doc-sources.md`.
- Registering MCP servers — that is precisely what this skill exists to
  avoid.

## Invocation patterns

### Shorthands

```bash
mcp2cli @github <tool> [args...]      # GitHub operations
```

The `@<name>` form resolves through the user-global `mcp2cli` config
(`~/.config/mcp2cli/`); only shorthands defined there exist.
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
> `.agents/skills/mintlify/SKILL.md` for the real per-repo access
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
- **None** — public MCP endpoints (e.g. Mintlify's own
  `https://mintlify.com/docs/mcp`) need no auth.

When adding a new shorthand, prefer env-var or keychain-backed auth over
checking secrets into the repo.

## Why `mcp2cli` over `codex mcp add`

Not context cost: Codex presents registered MCP tools deferred (names
only, schemas loaded on demand). The reason is simplicity — a registration
adds a long-lived server process, a version to pin, an auth path and a failure
mode for the doctor to police, while `mcp2cli` spawns the server for one call
and exits, and its output can be trimmed with `--jq`/`--head`.

Rule of thumb: **for this repo's own calls, prefer `mcp2cli`**. Register
natively when a third-party plugin or tool requires it for its features —
see `.claude/rules/research-doc-sources.md` § "MCP: two lanes".

## Repo wiring

- Pinned in `mise.toml` (`pipx:mcp2cli`) — available on any machine after
  `mise install`.
- Global shorthands live in `~/.config/mcp2cli/` (user scope).
- Where `mcp2cli` sits relative to curl, ctx7 and native registration is
  codified in `.claude/rules/research-doc-sources.md`.
- `mcp2cli` is the preferred path; native `codex mcp add` is allowed when a
  plugin requires it (the `no_mcp_registration` hk hard-ban was removed
  2026-07-19). Rationale in `feedback_no_mcp_registration.md`.

## See also

- `.agents/skills/mintlify/SKILL.md` — the mintlify URL surface
  (`curl llms.txt` + `.md`, not MCP).
- `.claude/rules/research-doc-sources.md` — the full preference chain.
- `docs/research/mintlify-catalog.md` — list of mintlify-covered repos
  with their probed HTTP status.
- `feedback_no_mcp_registration.md` (auto-memory) — when native
  registration is and is not appropriate.
- Upstream project: <https://github.com/knowsuchagency/mcp2cli>
