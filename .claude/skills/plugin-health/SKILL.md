---
name: plugin-health
description: Check that every plugin declared in settings is actually installed and enabled for THIS project, via `mise run plugin-health`. Use when a skill or slash command you expected is missing, after enabling or disabling a plugin, when a SessionStart report mentions plugin drift, or before shipping a change to `.claude/settings.json`. Reach for it INSTEAD of reading `claude plugin list` by eye — the payload spans other projects and repeats ids, so eyeballing it is how a plugin stays silently disabled.
---

# plugin-health

Reconciles what `.claude/settings.json` **declares** against what
`claude plugin list --json` **actually reports**, and returns a typed exit code.

## Why this exists

`enabled_plugin_ids` in `doctor.py` reads the declaration. Nothing read the
other side, so on 2026-09-13 `firecrawl@firecrawl` had no `enabledPlugins`
entry at all while `context7` and `exa` sat at `false`, and no gate said a word.
Five requested skills were simply absent for a whole session.

## Use it

```bash
mise run plugin-health          # rc IS the verdict; JSON report on stdout
mise run plugin-health-e2e      # cross-session check against a fresh `claude`
```

Exit codes (`PluginHealthCode`, generated into `.claude/types/plugin-health.d.ts`
so the SessionStart hook cannot drift from Python):

| rc | meaning |
|---|---|
| 0 | OK |
| 1 | DRIFT — one of the three findings below is non-empty |
| 2 | `claude` not executable |
| 3 | CLI ran and failed (rc is the contract; stderr is display-only) |
| 4 | payload would not decode |
| 5 | settings unreadable |
| 6/7/8 | e2e timeout / validate failed / session failed |

## Reading the report

Three **observable** findings, never an inferred verdict:

- `declared_not_installed` — settings enable it, no CLI row exists anywhere.
- `declared_disabled_here` — settings enable it, this project's row says off.
- `installed_not_declared` — enabled for this project, absent from settings
  (it arrived outside a reviewed diff).

⚠️ **Silence on a declared id with no project-scoped row is deliberate.**
Measured: `firecrawl@firecrawl` is enabled in this project's settings and has
NO dotfiles-scoped row — only a `user` row and another project's. An earlier
design inferred "not effective here" from that and would have reported a false
DRIFT whenever the user row read `false`. We do not know the mechanism, so the
correct output for that state is nothing.

## Traps

- The payload is **not uniform**: 8 distinct key shapes, `projectPath` absent
  from 55 of 271 rows, `scope` has three values (`project`/`user`/`local`), and
  35 ids repeat — one 8 times. Never assume one row per id.
- Findings name plugin **ids only**. `installPath`/`projectPath`/`notes` carry
  the operator's home directory, and SessionStart context is transcript-persisted.
- `claude mcp list` and `claude doctor` **both exit 0 regardless of health** —
  measured, with `exa` pending approval and disconnected. Never gate on their rc.
  `claude plugin validate` DOES discriminate (bad dir rc=1, good rc=0).

## See also

- `.claude/rules/probes-need-a-control-arm.md` — why the doctor entry runs the
  real check instead of returning `[]`.
- `python/src/dotfiles_setup/plugin_health.py` — the library.
