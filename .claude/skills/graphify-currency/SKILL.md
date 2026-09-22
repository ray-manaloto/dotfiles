---
name: graphify-currency
description: Keep Graphify's uv lock, managed skill surfaces, version stamps, PATH binary, and project graph current through the four sanctioned mise tasks. Use for Graphify upgrades, currency drift, or stale graphs; never invoke the vendor installer.
user-invocable: true
---

# Graphify currency

Use the smallest task that matches the state you need to change:

| Task | Use it when | Writes |
|---|---|---|
| `mise run graphify-check` | Diagnose currency or skill drift and print graph health. The doctor calls the offline form of the same checker. | Nothing. Returns 1 on any unverifiable or drifted currency surface; graph health is an informational line with its own typed status. |
| `mise run graphify-update` | Move the uv lock to `mise latest pipx:graphifyy`, or repair managed skill bytes/stamps when the lock is already current. | On a version move: one tracked release receipt per tag, `python/uv.lock`, and the project environment. Always repairs the managed `--platform claude`/`--platform codex` skill surfaces and all three stamps when needed. |
| `mise run graphify-rebuild` | Re-extract the repository graph after source changes. | `graphify-out/` only; success additionally requires `graphify-health: fresh`. |
| `mise run graphify-upgrade` | Perform a complete operator upgrade. | Runs update, then rebuild, sequentially. The first nonzero return code stops the composite. |

The task layer is intentionally thin. Currency mechanics live in
`python/src/dotfiles_setup/graphify_currency.py`; graph extraction and health
live in `python/src/dotfiles_setup/graphify.py`. Mise `depends` is not an
ordering mechanism because dependencies may run in parallel.

## Release-review receipt

Graphify is pre-1.0 and has shipped silent data-loss defects. Before a version
move, `graphify-update` fetches every GitHub release in `(locked, latest]`
and writes one tracked `docs/receipts/graphify/<version>.md` per release. Each
file records the tag, `publishedAt`, verbatim body, and the command that wrote
it. The task prints every receipt path before native
`uv lock --project python --upgrade-package graphifyy` and
`uv sync --project python` run. A missing latest version or failed release
fetch stops before lock mutation.

The offline checker requires a receipt for the exact locked version. This is
the CI backstop for a Renovate lockfile-maintenance re-resolution: a lock move
without a new tracked receipt fails with `receipt-missing` even when the new
lock equals latest.

When locked equals latest, update prints `already current`, skips the receipt
and uv commands, and still refreshes skills/stamps. That path repairs a stale
stamp without inventing a dependency change.

## Managed skill boundary

The package bundles selected by `--platform claude` and `--platform codex` are
reviewed vendor bytes.
After `uv sync`, an internal `graphify refresh-skills` CLI runs in a fresh
`uv run --project python` process, then a second fresh process runs
`graphify check --offline`. This prevents cached placement metadata from the
old package being combined with the newly installed package bytes. The refresh
copies the bundles and their packaged references, then stamps them. The
`agents` surface is stamp-only: its `DELIBERATE STUB` stays byte-identical
and no `references/` directory is created.

A differing destination `SKILL.md` is copied to
`.agent/graphify/backups/<platform>-SKILL.md.<timestamp>` before replacement,
and the task prints that path. No `SKILL.md.bak` is left beside a managed
surface. The only manual decision is whether the retained local delta mattered;
a current surface performs no writes and creates no backup.

## Why the native project installer is excluded

Do not use `graphify install --project` for this repository. The 2026-09-22
probe showed that `--platform claude` also writes root `CLAUDE.md` and
`.claude/settings.json` hooks, while `--platform codex` also writes root
`AGENTS.md` and `.codex/hooks.json`. Those are broader configuration
mutations than skill currency.

Only `graphify install --project --platform agents` is skill-only. The separate
`graphify agents install` subcommand also writes root `AGENTS.md`. This
repository deliberately uses the smaller `.agents/skills/graphify/SKILL.md`
redirect stub, so either vendor bundle would overwrite the enforcement surface.

Antigravity's project installer is also excluded: it targets the same
`.agents/skills/graphify/**` tree, adds a graphify.md file to each of the `.agents`
rules and workflows directories, and its vendor rules prescribe bare Graphify
commands. It makes no `$HOME` writes with `--project`, but still collides with
this repository's deliberate stub and mise-only command policy.

## Zero-token boundary

These four tasks use deterministic package metadata, GitHub release data,
native uv operations, filesystem comparison/copy, AST extraction, and graph
health. An AST test scans the repository-owned subprocess surface and permits
only `mise`, `gh`, `uv`, the ambient version probe, and the exact rebuild argv.
Keep model-backed labeling outside this workflow: never run
`graphify label` or `--dedup-llm` as part of currency or rebuild work.
The installed package's `graphify.llm` module around line 3512 can silently
escalate to the `claude-cli` backend
when no API-key backend is available, so an apparently unconfigured label
operation can still spend agent tokens.

The PATH probe is the binary an agent shell resolves, read from
`DOTFILES_AMBIENT_PATH`: the SessionStart hook captures it for the doctor, and
the `graphify-check` task captures the PATH `mise run` resolves (mise's repaired
PATH, which still points at the user-global pin — the drift this axis exists
for; a stale shell activation is the doctor's path-drift check). It prints the resolved path and
runs that exact file with the same PATH. This is deliberately different from
the project venv's Graphify used by `uv run --project python`.

The rebuild subprocess removes every known LLM-provider credential/backend
selector and forces the project venv to the front of PATH. Installed Graphify
0.9.65 ignores `--no-label` on `update`, so no such flag is passed. Residual:
PATH must remain available for Graphify/git, and a future vendor update could
still discover the keyless `claude` CLI fallback. The environment scrub reduces
provider reachability; the AST argv gate is the repository-owned hard boundary.

`graphify check-update` is deliberately not wired. It only inspects a
`needs_update` sentinel produced by the banned watch/LLM path and always exits
0, so it is not a currency or health gate.

## Stable operator output

- `mise run graphify-check`: `graphifyy locked <v>, latest <v>`,
  `graphify path-binary: <resolved-path> (version=<v>)`,
  `graphify currency current`, and `graphify-health: <status> ...`; rc 0 means
  currency is current, while any `graphify drift [...]` line means rc 1.
- `uv run --project python dotfiles-setup graphify check --offline`: latest is
  `SKIPPED (offline)`; it emits no network or graph-health probe and returns 0
  only when every local axis passes.
- `mise run graphify-update`: either `already current` or one
  `release notes -> docs/receipts/graphify/<v>.md` line per release, followed
  by `graphifyy lock updated ...`, refresh/current output, and the offline
  check's `graphify currency current`; rc 0 only after the fresh-process check.
- `mise run graphify-rebuild`: rebuild output followed by
  `graphify-health: fresh ...`; rc 0 only for fresh health.
- `mise run graphify-upgrade`: the update lines followed by rebuild/fresh-health
  lines; the first nonzero rc stops the sequence.

## Completion criteria

- `mise run graphify-check` returns 0 and prints the ambient resolved path.
- `docs/receipts/graphify/<locked>.md` exists and is tracked.
- The three `.graphify_version` files equal the installed/locked version.
- The `claude` and `codex` bundle bytes equal the installed package.
- The `agents` stub still contains `DELIBERATE STUB` and has no references.
- The health line printed by `graphify-check` is read separately from its
  currency rc; after a requested rebuild it reports `fresh`.
