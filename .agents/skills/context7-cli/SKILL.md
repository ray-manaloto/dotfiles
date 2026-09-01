---
name: context7-cli
description: Use when the user mentions "ctx7" or "context7", needs current docs for any library, wants to install/search/generate skills, or needs to set up Context7 for their AI coding agent. Fetches library documentation, manages AI coding skills, and configures Context7 MCP.
---

# ctx7 CLI

The Context7 CLI fetches up-to-date library documentation and sets up Context7 MCP for your editor. It also still carries **deprecated** skill-management commands (see the caveat below).

**In this repo `ctx7` is mise-pinned — do NOT `npm install -g` or `npx` it.** The pin is `"npm:ctx7"` in `mise.toml`; `.Codex/rules/ci-local-parity.md` rule 3 bans `npx` because it bypasses mise and can resolve a different version than CI. Just call the binary:

```bash
ctx7 library <name> [query]     # resolve a name -> Context7 library ID
ctx7 docs <libraryId> <query>   # fetch the docs
```

To move the version, bump the `mise.toml` pin (Renovate does this) — not `@latest`.

> ⚠️ **The `ctx7 skills …` commands are DEPRECATED.** They are hidden from
> `--help` but still execute, printing *"Skill commands are deprecated and will
> stop working in the next major release."* (verified on the pinned 0.5.5, rc=0).
> Treat the sections below that use them as historical; do not build on them.
> Note their absence from `--help` is NOT proof they are gone — they run.

## What this skill covers

- **[Documentation](references/docs.md)** — Fetch current docs for any library. Use when writing code, verifying API signatures, or when training data may be outdated.
- **[Skills management](references/skills.md)** — Install, search, suggest, list, remove, and generate AI coding skills.
- **[Setup](references/setup.md)** — Configure Context7 MCP for Codex / Cursor / OpenCode.

## Quick Reference

```bash
# Documentation
ctx7 library <name> <query>           # Step 1: resolve library ID
ctx7 docs <libraryId> <query>         # Step 2: fetch docs

# Skills
ctx7 skills install /owner/repo       # Install from a repo (interactive)
ctx7 skills install /owner/repo name  # Install a specific skill
ctx7 skills search <keywords>         # Search the registry
ctx7 skills suggest                   # Auto-suggest based on project deps
ctx7 skills list                      # List installed skills
ctx7 skills remove <name>             # Uninstall a skill
ctx7 skills generate                  # Generate a custom skill with AI (requires login)

# Setup
ctx7 setup                            # Configure Context7 MCP (interactive)
ctx7 login                            # Log in for higher rate limits + skill generation
ctx7 whoami                           # Check current login status
```

## Authentication

```bash
ctx7 login               # Opens browser for OAuth
ctx7 login --no-browser  # Prints URL instead of opening browser
ctx7 logout              # Clear stored tokens
ctx7 whoami              # Show current login status (name + email)
```

Most commands work without login. Exceptions: `skills generate` always requires it; `ctx7 setup` requires it unless `--api-key` or `--oauth` is passed. Login also unlocks higher rate limits on docs commands.

Set an API key via environment variable to skip interactive login entirely:

```bash
export CONTEXT7_API_KEY=your_key
```

## Common Mistakes

- Library IDs require a `/` prefix — `/facebook/react` not `facebook/react`
- Always run `ctx7 library` first — `ctx7 docs react "hooks"` will fail without a valid ID
- Repository format for skills is `/owner/repo` — e.g., `ctx7 skills install /anthropics/skills`
- `skills generate` requires login — run `ctx7 login` first
