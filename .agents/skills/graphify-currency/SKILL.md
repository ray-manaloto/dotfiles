---
name: graphify-currency
description: Keep Graphify's uv lock, managed skill surfaces, version stamps, PATH binary, and project graph current through the four sanctioned mise tasks. Use for Graphify upgrades, currency drift, or stale graphs; never invoke the vendor installer.
user-invocable: true
---

# Graphify currency

Use the smallest task that matches the state you need to change:

| Task | Use it when | Writes |
|---|---|---|
| `mise run graphify-check` | Diagnose currency or skill drift. The doctor calls the same checker. | Nothing. Returns 1 on any unverifiable or drifted surface. |
| `mise run graphify-update` | Move the uv lock to `mise latest pipx:graphifyy`, or repair managed skill bytes/stamps when the lock is already current. | On a version move: the release-note receipt, `python/uv.lock`, and the project environment. Always repairs the managed `--platform claude`/`--platform codex` skill surfaces and all three stamps when needed. |
| `mise run graphify-rebuild` | Re-extract the repository graph after source changes. | `graphify-out/` only; success additionally requires `graphify-health: fresh`. |
| `mise run graphify-upgrade` | Perform a complete operator upgrade. | Runs update, then rebuild, sequentially. The first nonzero return code stops the composite. |

The task layer is intentionally thin. Currency mechanics live in
`python/src/dotfiles_setup/graphify_currency.py`; graph extraction and health
live in `python/src/dotfiles_setup/graphify.py`. Mise `depends` is not an
ordering mechanism because dependencies may run in parallel.

## Release-review receipt

Graphify is pre-1.0 and has shipped silent data-loss defects. Before a version
move, `graphify-update` fetches every GitHub release in `(locked, latest]`
and writes
`.agent/graphify/release-notes-<latest>.md`. The directory is gitignored.
The task prints the receipt path and release count before native
`uv lock --project python --upgrade-package graphifyy` and
`uv sync --project python` run. A missing latest version or failed release
fetch stops before lock mutation.

When locked equals latest, update prints `already current`, skips the receipt
and uv commands, and still refreshes skills/stamps. That path repairs a stale
stamp without inventing a dependency change.

## Managed skill boundary

The package bundles selected by `--platform claude` and `--platform codex` are
reviewed vendor bytes.
`graphify_skill.refresh_skills` copies those bundles and their packaged
references, then stamps them with the installed distribution version. The
`agents` surface is stamp-only: its `DELIBERATE STUB` stays byte-identical
and no `references/` directory is created.

A differing destination `SKILL.md` is copied to `SKILL.md.bak` before
replacement. After a reviewed update, inspect the backup to understand the
discarded local delta, then remove it if it should not be committed. A current
surface performs no writes and creates no backup.

## Why the native project installer is excluded

Do not use `graphify install --project` for this repository. The 2026-09-22
probe showed that `--platform claude` also writes root `CLAUDE.md` and
`.claude/settings.json` hooks, while `--platform codex` also writes root
`AGENTS.md` and `.codex/hooks.json`. Those are broader configuration
mutations than skill currency.

The vendor `agents` platform is skill-only, but this repository deliberately
uses the smaller `.agents/skills/graphify/SKILL.md` redirect stub. Installing
the vendor bundle there would overwrite the enforcement surface rather than
repair it. The sanctioned `graphify-update` path therefore manages full bytes
for `claude`/`codex` and only the version stamp for `agents`.

## Zero-token boundary

These four tasks use deterministic package metadata, GitHub release data,
native uv operations, filesystem comparison/copy, AST extraction, and graph
health. Keep model-backed labeling outside this workflow: never run
`graphify label` or `--dedup-llm` as part of currency or rebuild work.
The installed package's `graphify.llm` module around line 3512 can silently
escalate to the `claude-cli` backend
when no API-key backend is available, so an apparently unconfigured label
operation can still spend agent tokens.

The only deliberate PATH probe is `graphify --version` inside
`graphify-check`; rebuild resolves the project-locked executable through
`uv run --project python`.

## Completion criteria

- `mise run graphify-check` returns 0.
- The three `.graphify_version` files equal the installed/locked version.
- The `claude` and `codex` bundle bytes equal the installed package.
- The `agents` stub still contains `DELIBERATE STUB` and has no references.
- After a requested rebuild, `mise run graphify-health` reports `fresh`.
