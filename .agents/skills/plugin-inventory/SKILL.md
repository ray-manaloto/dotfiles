---
name: plugin-inventory
description: Inventory one exact Codex or codex plugin selector across native CLI state, settings, caches, worktrees, and live repository references. Use before removing a plugin, when a plugin appears absent but may leave state behind, or when auditing plugin counts. This skill is read-only; run it before deciding what removal work is needed.
---

# Plugin inventory

Run the checked read-only inventory for an exact `name@marketplace` selector:

```bash
mise run plugin-inventory -- <name@marketplace>
```

Use `--json` when another tool will consume the typed report.

## Read the result

- `locations` names user-level settings, registries, caches, marketplaces and
  hook-trust keys. An `unreadable` location means the probe could not answer;
  treat it as an error, not absence.
- `claude_cli` and `codex_cli` are exact native-CLI matches. Codex matching uses
  both selector halves, so a longer plugin name cannot satisfy the requested one.
- `project_settings` are mutable repository settings. `worktree_settings` and
  `stale_worktrees` are report-only because other worktrees belong to other
  branches.
- `references` excludes historical documentation paths. Judge every remaining
  hit in context and re-derive any nearby count before editing it.
- `errors` means the inventory is incomplete. Resolve every error before
  concluding the plugin is absent.

The implementation contract is
`docs/specs/plugin-remove-pipeline.md`; the command performs no mutation.
