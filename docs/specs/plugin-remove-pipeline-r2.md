# Spec addendum r2: plugin-removal pipeline — correction round 1 of 2

Base spec: `docs/specs/plugin-remove-pipeline.md` (still authoritative where not
overridden here). Base commit under correction: `9c624360`. Review:
`docs/research/kb/reports/agents/cold-reviewer-plugin-remove-2026-09-24.md`
(6 HIGH / 7 MEDIUM / 9 LOW; architect re-verified H1, H2 and H6 live).
Implementer: `codex-sol-implementer`, `xhigh`. COMMIT: caller. Planned as the last respec round;
Ray approved one more (r3, 2026-09-25).

## 1. Objective

`--apply` must remove exactly the named `plugin@marketplace` — nothing else — at
every scope it is installed, with every destructive step backed up, and must
never report success for work it did not do. Fix every HIGH and MEDIUM finding
and the LOW items listed in §4.

## 2. Files

Same set as the base spec §2 (`plugin_state.py`, `plugin_inventory.py`,
`plugin_remove.py`, `removed_plugins.py`, `doctor.py`, `doctor.toml`, the four test
files, the two skills + mirrors). No new modules.

## 3. Interfaces (changes only)

- The selector is ALWAYS split into `(plugin, marketplace)`; every lookup keys on
  the half it concerns. `plugin_name()` stays; add `marketplace_name(key)`.
- `PluginLocation` gains `marketplace: str` and `scope: str = ""`
  (`user`/`project`/`local`/`""`), and `kind` gains `"data"`.
- `RemovalPlan` gains `notes: tuple[str, ...]` (e.g. "marketplace kept: still
  used by honcho-dev@honcho").
- `plugin_remove_main` exits **1** on a dry run whose plan has blockers (0 when
  clean).

## 4. Constraints and invariants (the corrections)

**Paths come from the harness's own records, never from a guessed layout.**
- Claude: the cache path is each `installed_plugins.json` entry's `installPath`
  (measured: `cache/<marketplace>/<plugin>/<version>`). The removable cache unit
  is `~/.claude/plugins/cache/<marketplace>/<plugin>/` (all versions). The
  `<marketplace>/` directory is removed only when it is empty afterwards AND the
  marketplace itself is being removed.
- Claude data: `~/.claude/plugins/data/<plugin>-<marketplace>/` (measured:
  `antigravity-antigravity-for-claude-code`). Back it up in the same archive as the
  cache BEFORE any uninstall; the CLI deletes it unless `--keep-data` is passed.
- Codex cache: `~/.codex/plugins/cache/<marketplace>/<plugin>/` — never a bare
  `<plugin>` match across marketplaces (review H4: `exa@exa` vs
  `claude-plugins-official/exa`).

**Every install scope is planned** (review H6; measured 213 project / 53 user / 2
local entries). For each `installed_plugins.json` entry of the selector:
`user` → `claude plugin uninstall <sel> --scope user --json`; `project` → the
same with `--scope project`, `cwd=projectPath`; `local` → `--scope local`,
`cwd=projectPath`. An installed scope the plan cannot handle is a BLOCKER, never
an empty plan.

**Marketplace removal is guarded** (review H2). Plan `remove-claude-marketplace`
/ `remove-codex-marketplace` only if NO other installed plugin (any scope, per
`installed_plugins.json`, `claude plugin list`, `codex plugin list --json`) comes
from that marketplace; otherwise skip it and add a `notes` entry naming the
siblings. Marketplace matching uses the selector's marketplace half (review M1).

**Reading is separate from policy** (review H3). `plugin_state` reports every
location of a codex plugin — hook trust, marketplace, cache, enabled flag —
regardless of `enabled`. Only the doctor's reappearance POLICY
(`removed_plugins.find_reappearances`) keeps the ruled exemption: a codex plugin
explicitly `enabled = false` is a deliberate disable (claudex-loop) and yields no
finding. State that exemption in the `doctor.toml` comment.

**Minimal settings diff handles both files** (review M-unverified;
`$CC/changelog.md:4754` says `/plugin uninstall` may write
`settings.local.json`). Snapshot BOTH `<project>/.claude/settings.json` and
`settings.local.json` before the CLI call; apply the minimal-line restore to
whichever file(s) the CLI changed; the json-equivalence check applies per file.

**Rollback from memory, never from disk** (review H5). Every file edit keeps the
original bytes in memory, restores from them on failure, and writes via a temp
file in the same directory + `os.replace`. Backups are timestamped
(`<name>.<UTC stamp>.bak`), never overwritten, and a backup that cannot be
written aborts the step BEFORE any edit.

**Unreadable is an error, not absence** (review M3, Python 3.14): use
`os.stat`/`os.scandir` inside `try` and map `PermissionError`/`OSError` to an
`unreadable` location; never `Path.exists()` on a path whose parent may be
unreadable.

**Inventory completeness** (review M5): other repos' settings are read for
`extraKnownMarketplaces` as well as `enabledPlugins`.

**Cache removal requires the uninstall** (review M6): `remove-orphan-cache` runs
only after the plugin is absent from `installed_plugins.json` (re-read) and a
backup exists.

**LOW fixes to include:** watchlist edit verified by re-parsing `doctor.toml` and
checking the name is in `[removed_plugins].names`; `git grep -I` and decode with
`errors="replace"`; doctor labels unreadable lines "could not check", not
"reappeared"; invoke `claude`/`codex` through `mise exec --` (ai-cli-invocation
rule); the backup archive carries a manifest of the paths it saved and a
timestamped name; hook-trust editing handles dotted, quoted and sub-table forms or
fails the step (never reports success while trust remains).

**Tests must construct the shapes that hid these bugs** (review M2): plugin ≠
marketplace (`alpha@market`), a sibling plugin in the same marketplace
(`beta@market`), a same-named plugin in another marketplace, a disabled codex
plugin with hook trust + cache, user and local scope installs, a permission-denied
directory, a CLI that writes `settings.local.json`, a failed backup write. Each
fix gets a FAIL arm (revert the fix → its test goes red).

Out of scope (ticketed separately): the `.agents/` mirror turning "Claude Code or
codex" into "Codex or codex".

## 4a. Corrections from the r2 premise check

**Goal state, not a CLI assumption** (R8 refuted as a guarantee). After every
project/local uninstall, the plugin key must be ABSENT from both
`<project>/.claude/settings.json` and `settings.local.json`. Measured 2026-09-24:
`claude plugin uninstall --scope project` DELETED the key from `settings.json` in
both repos. The changelog (`$CC/changelog.md:4754`) says `/plugin uninstall` may
instead ADD a `false` override to `settings.local.json`. Handle both: after the
CLI, compute the goal state from the snapshots — delete the key's line from
`settings.json` if it survived (minimal-line edit) and delete any override the
CLI added to `settings.local.json`; verify the post-condition by re-parsing both.

**Marketplaces from the harness's ids.** `claude plugin list --json` returns a
list of rows `{id, scope, projectPath, enabled, installPath, …}` where `id` is
`<plugin>@<marketplace>` (measured, 271 rows). The sibling guard reads marketplace
membership from those ids, `installed_plugins.json` keys and codex
`installed[].marketplaceName`.

**Iterate entries, not keys:** 214 keys carry 268 entries; entries may lack
`gitCommitSha` and may carry `auto` (an auto-installed dependency).

**Dependencies.** If any other installed plugin declares the target in its
`.claude-plugin/plugin.json` `dependencies`, that is a BLOCKER (the harness
refuses the disable, `$CC/plugin-dependencies.md:177,190`). Report the target's
own `auto`-installed dependencies in `notes`; do not remove them.

**Marketplace removal cascades** (`$CC/plugin-marketplaces.md:1320-1323`): it is
planned only after every plugin from it is uninstalled (sibling guard), and it may
edit `extraKnownMarketplaces` in project settings — snapshot and apply the same
minimal-diff/goal-state rule to those files.

**Data dir id**: `data/<id>` where `<id>` = the selector with every character
outside `[a-zA-Z0-9_-]` replaced by `-` (`$CC/plugins-reference.md:744`). The
mapping is lossy (`a-b@c` and `a@b-c` collide): if another installed selector maps
to the same id, the data step is a BLOCKER.

**Missing projectPath**: a `project`/`local` entry whose `projectPath` no longer
exists is a BLOCKER (the CLI needs it as cwd).

**Symlinked cache entries** (link mode, `$CC/plugins-reference.md:798`): back up
with dereferenced content and record the link target in the manifest; never
delete a link target outside `~/.claude/plugins/cache`.

## 5. Verification

```bash
uv run --project python pytest tests/test_plugin_state.py tests/test_plugin_inventory.py tests/test_plugin_remove.py tests/test_removed_plugins.py tests/test_doctor.py -q
uv run --project python pytest tests/ -q
uv run --project python dotfiles-setup verify run
mise run lint
mise run plugin-remove -- honcho@honcho            # DRY RUN: no marketplace removal, notes name honcho-dev; cache target .../cache/honcho/honcho/ only
mise run plugin-remove -- exa@exa                  # DRY RUN: codex cache target never claude-plugins-official/exa
mise run plugin-remove -- planning-with-files@planning-with-files   # DRY RUN: user/project/local uninstall steps match installed_plugins.json scopes
mise run plugin-inventory -- antigravity@antigravity-for-claude-code  # codex hook-trust locations reported (4)
mise run plugin-inventory -- ponytail@ponytail     # unchanged: 0 locations, rc 0
mise run doctor                                    # no removed-plugins finding (claudex-loop disabled = exempt)
```
Never `--apply` against the real machine.

## 6. Commit

`caller`.

## 7. PREMISES

| # | Kind | Claim | Source |
|---|---|---|---|
| R1 | L | `installed_plugins.json` = `{version: 2, plugins}`; 214 keys / 268 entries; entry keys `installPath, installedAt, lastUpdated, projectPath, scope, version` + optional `gitCommitSha` (255/268) and `auto` (4 user entries); scopes project 213 / user 53 / local 2 | measured 2026-09-24; premise-verifier r2 |
| R2 | L | `installPath` = `cache/<marketplace>/<plugin>/<version>` (e.g. `cache/claude-code-workflows/agent-teams/1.0.3`) | measured 2026-09-24 |
| R3 | L | data dirs named `<plugin>-<marketplace>` (e.g. `antigravity-antigravity-for-claude-code`) | `ls ~/.claude/plugins/data` 2026-09-24 |
| R4 | L | codex cache `~/.codex/plugins/cache/<marketplace>/<plugin>/…` | `ls ~/.codex/plugins/cache` 2026-09-24 |
| R5 | L | 9c624360 dry run `honcho@honcho`: steps remove-claude-marketplace honcho + remove-orphan-cache honcho, 0 blockers; `cache/honcho/` holds `honcho` and `honcho-dev` | measured 2026-09-24 |
| R6 | L | cache lookup `cache / name` | `plugin_state.py:107-131` @9c624360 |
| R7 | I | `claude plugin uninstall … --scope user|project|local`, `--keep-data` | `claude plugin uninstall --help` (2.1.281) |
| R8 | L+A | measured: CLI project-scope uninstall deleted the key from `settings.json` (both repos, 2026-09-24); documented: `/plugin uninstall` may add a `false` override in `settings.local.json` — §4a handles both via the goal state | this session; `$CC/changelog.md:4754` |
| R9 | L | `claude plugin list --json` = list of rows `{enabled, id, installPath, installedAt, lastUpdated, projectPath, scope, version}`, `id` = `plugin@marketplace`, 271 rows | measured 2026-09-24, rc 0 |
