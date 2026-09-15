---
name: codex-schema
description: Generate and check the codex app-server JSON schema for the EXACT installed codex version, via `mise run codex-schema-generate` and the doctor `codex-schema` check. Use when codex is upgraded, when doctor reports the schema stale or missing, when authoring a `.codex/agents/*.toml` and you need the real key names, or when you need to search every setting and environment variable codex accepts. Reach for it BEFORE hand-writing an agent config — codex DROPS an invalid agent file silently, with no error, which is how six specialist agents sat on disk and none of them loaded.
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

## Why this matters

Without a local schema:

- **No offline search** — settings and env vars are only documented in the web
- **Version drift** — using the "latest" schema can describe settings the pinned codex lacks
- **Incomplete information** — the live docs may lag code changes

With a versioned schema:

- **Offline access** — grep any setting name, type, or description
- **Version-exact** — schema matches 0.154.0, the exact installed version
- **Searchable** — every doc in `schemas/v2/` is a JSON file ready to grep

## Integration

The skill wraps these mise tasks:

- `mise run codex-schema-generate` — creates or refreshes the schema
- `mise run codex-schema-check` — validates for verification contracts

Both are thin wrappers around `python/src/dotfiles_setup/codex_schema.py`.
