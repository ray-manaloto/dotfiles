---
name: codex-schema
description: Generate and check the codex app-server JSON schema for the EXACT installed codex version, via `mise run codex-schema-generate` and the doctor `codex-schema` check. Use when codex is upgraded, when doctor reports the schema stale or missing, when authoring a `.codex/agents/*.toml` and you need the real key names, or when you need to search every setting and environment variable codex accepts. Reach for it BEFORE hand-writing an agent config — codex DROPS an invalid agent file silently, with no error.
user-invocable: true
---

# codex-schema — Codex app-server JSON schema management

Manages the codex configuration schema, which documents all settings and environment variables supported by the installed codex version. The schema is generated from the exact pinned codex version to ensure local searchability.

## Generate schema

```bash
mise run codex-schema-generate
```

Generates the JSON schema bundle from the installed codex version into `schemas/`. The schema includes:

- Complete app-server configuration reference
- All supported settings and their types
- Environment variable documentation
- MCP server and plugin configuration

## Check schema currency

```bash
mise run codex-schema-check
```

Verifies that the generated schema exists and is valid. Part of the verification contract (`mise run verify`).

## Validating an agent file before codex drops it

Codex silently ignores an invalid `.codex/agents/*.toml`. Every agent file
starts with `#:schema ../../schemas/codex-agent.json`; keep that directive,
run `mise run lint` (its `taplo` step checks TOML), and confirm the agent
actually loads — the codex-sdlc-team settlement records which specialists
were observed.

## What the schema covers

`schemas/codex_app_server_protocol*.schemas.json` is generated for the codex
version pinned in `.config/mise/conf.d/shared.toml` (the generator writes a
version stamp beside it; both are gitignored, machine-local outputs); grep it for any setting, type or
environment variable. The host may run a newer native codex than that pin
(`mise.toml` `disable_tools`), so check `mise exec -- codex --version` when a
setting seems missing.

Both tasks are thin wrappers around `python/src/dotfiles_setup/codex_schema.py`.
