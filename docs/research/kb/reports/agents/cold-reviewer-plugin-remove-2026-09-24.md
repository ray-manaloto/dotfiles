# Cold review — 9c624360 (range d1fe8efc..9c624360)

- Reviewer: cold-reviewer (Claude Opus), author family: codex
- Subject: `9c624360aba9b5cfd345423e11d0365c8ce5d6f2` against parent `d1fe8efc73be862493468691d909ae2c38835bb9`
- Scope: everything except `docs/research/**`, `docs/specs/**`
- Focus: error / empty / timeout / unreadable branches in `plugin_state.py`,
  `plugin_inventory.py`, `plugin_remove.py`, `removed_plugins.py`, doctor wiring.
- Memory: consulted `.claude/agent-memory-local/cold-reviewer/` (auto memory enabled).
- Status: COMPLETE — 22 findings: 6 HIGH, 7 MEDIUM (1 UNVERIFIED), 9 LOW
- Verdict: DO NOT SHIP `--apply` as-is. Findings 1, 2, 6 and 7 destroy state the operator did not name; 3, 4 and 8 make the plan (and the skill's step-4 re-inventory) report clean while state remains.

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| 1 | HIGH | Claude cache is probed at `~/.claude/plugins/cache/<plugin>`, but the real layout is `cache/<marketplace>/<plugin>/<version>`: a real cache is missed (antigravity), and a MARKETPLACE dir whose name equals the plugin name is treated as the plugin's cache | `python/src/dotfiles_setup/plugin_state.py:107-131`; `python/src/dotfiles_setup/plugin_remove.py:162-164` | E1, E2 |
| 2 | HIGH | `--apply` for `honcho@honcho` (live dry-run, blockers 0) backs up then `rmtree`s `~/.claude/plugins/cache/honcho`, which is the marketplace dir that also holds the installed sibling `honcho-dev@honcho`, and removes marketplace `honcho` with no check that no other installed plugin comes from it | `python/src/dotfiles_setup/plugin_remove.py:115-128`, `:150`, `:387-393` | E2, E3 |
| 3 | HIGH | A codex `enabled = false` entry hides that plugin's hook-trust, marketplace and cache from `locate()`; the removal inventory inherits this, so the live `antigravity@antigravity-for-claude-code` plan omits its 4 trusted hooks, and the watched `claudex-loop` (disabled, marketplace registered, cache present) yields 0 doctor findings | `python/src/dotfiles_setup/plugin_state.py:264-286`; `python/src/dotfiles_setup/plugin_inventory.py:363-367` | E3, E4 |
| 4 | MEDIUM | Marketplace locations are matched against the set of BARE PLUGIN NAMES, so a marketplace whose name differs from the plugin's (`antigravity-for-claude-code`) is never found by inventory, never removed by the plan, and never flagged by the doctor; the skill's step-4 re-inventory is blind in the same place | `python/src/dotfiles_setup/plugin_state.py:99`, `:172`, `:284`; `python/src/dotfiles_setup/plugin_remove.py:115-120` | E3, E4 |
| 5 | MEDIUM | Every test fixture uses `example-plugin@example-plugin` (name == marketplace) and builds `cache/<name>` with no marketplace level, the one configuration in which findings 1, 2 and 4 cannot show (probes rule 8: the fixture admits only one answer) | `tests/test_plugin_state.py:19-20`, `:41`; `tests/test_plugin_remove.py:22`, `:175-176`; `tests/test_removed_plugins.py:167` | E5 |
| 6 | HIGH | `remove-orphan-cache` deletes by BARE name across every codex marketplace, so removing `exa@exa` also deletes `~/.codex/plugins/cache/claude-plugins-official/exa` (a different selector) and `firecrawl@*` deletes the whole `~/.claude/plugins/cache/firecrawl` marketplace dir — the "exact selector" the skills promise is not what the mutation uses | `python/src/dotfiles_setup/plugin_remove.py:160-172`, `:387-393` | E6 |
| 7 | HIGH | `remove_codex_hook_trust` rolls back from the ON-DISK backup file, not the in-memory original: when a backup from an earlier run exists (every success leaves one) and the new backup write fails, it overwrites the untouched `~/.codex/config.toml` with the stale backup and reports `rolled back` | `python/src/dotfiles_setup/plugin_remove.py:457`, `:467-480` | E7 (arm A vs B) |
| 8 | HIGH | The plan never consumes `claude_cli` rows or user/local-scope `enabled`/`installed` locations: a user-scope install (53 such installs on this host) yields an EMPTY plan with 0 blockers, so `--apply` exits 0 having run nothing | `python/src/dotfiles_setup/plugin_remove.py:103-157`; `python/src/dotfiles_setup/plugin_inventory.py:374` | E8 |
| 9 | MEDIUM | `Path.exists()` never raises on Python 3.14 (it returns False on `PermissionError`), so the `except OSError` → `unreadable` branches are dead and a locked cache dir reports ABSENT, contrary to the module's own unreadable-is-not-absence contract | `python/src/dotfiles_setup/plugin_state.py:110-122`, `:180`, `:198-210`; `python/src/dotfiles_setup/plugin_remove.py:163`, `:166-171` | E9 |
| 10 | MEDIUM | Removal deletes the plugin's persistent data with no backup: `claude plugin uninstall` deletes `${CLAUDE_PLUGIN_DATA}` by default and `marketplace remove` uninstalls every plugin from that marketplace, while the pipeline backs up only the re-downloadable cache and never passes `--keep-data` | `python/src/dotfiles_setup/plugin_remove.py:109-112`, `:316`, `:379` | E10 |
| 11 | MEDIUM | Inventory reads other repositories' settings ONLY for `enabledPlugins`, so a project-scope `extraKnownMarketplaces` declaration (live: `macos-development-environment` declares `honcho`) and a project install record whose settings do not enable the plugin are never reported or planned | `python/src/dotfiles_setup/plugin_inventory.py:294-302`, `:316-338` | E3, E11 |
| 12 | MEDIUM | `remove-orphan-cache` asserts orphanhood it never checks: it runs whenever a cache location exists, after steps that may not have uninstalled the plugin (8) or that uninstall a sibling (2), so the cache of a still-installed plugin is deleted | `python/src/dotfiles_setup/plugin_remove.py:149-150`, `:382-396` | E3, E8 |
| 13 | MEDIUM (UNVERIFIED) | `uninstall_project_scope` assumes `claude plugin uninstall --scope project` rewrites `.claude/settings.json`; the vendor changelog says `/plugin uninstall` writes a `false` into `settings.local.json` instead. If the CLI shares that path, `cli_text == original`, the step returns rc=1 and apply halts at the first project after the CLI has already mutated state. The test's fake CLI models only the settings.json behaviour | `python/src/dotfiles_setup/plugin_remove.py:301-329`; `tests/test_plugin_remove.py:93-96` | E12 |
| 14 | LOW | `add_to_watchlist` checks only that the edit still PARSES, not that the name landed: a `]` inside a comment in a multi-line `names` array puts the insertion inside the comment and returns rc=0 `watchlist updated` with the name absent | `python/src/dotfiles_setup/plugin_remove.py:503-520` | E13 |
| 15 | LOW | A tracked binary file matching the name (`Binary file X matches`) or non-UTF-8 input raises `ValueError`/`UnicodeDecodeError`, which the CLIs' `except ValueError` turns into a misleading argparse USAGE error; the whole inventory and plan abort (fails closed, no mutation). The doctor contains the same decode crash as `check crashed` | `python/src/dotfiles_setup/plugin_inventory.py:275-277`, `:433-434`; `python/src/dotfiles_setup/plugin_remove.py:587-588`; `python/src/dotfiles_setup/plugin_state.py:57`, `:242` | E13 |
| 16 | LOW | The dry-run exit code ignores plan blockers: with `doctor.toml` unreadable the plan prints `blockers: 1` and exits 0 | `python/src/dotfiles_setup/plugin_remove.py:594` | E13 |
| 17 | LOW | The hook-trust text editor recognises only `[hooks.state."<key>"]` headers and never re-reads its post-condition: an inline entry under `[hooks.state]` returns rc=0 `no matching hook-trust tables` while inventory still finds the trust, and a `."<key>".sub` subtable survives the drop (live config is 47/47 header form, so latent) | `python/src/dotfiles_setup/plugin_remove.py:26`, `:437-450`, `:464-466` | E7 (arms C, D) |
| 18 | LOW | Q-FRESH: the backup records `(home, name)`, not the path set, and removal recomputes `_cache_paths`, so a path that appears after the backup is deleted unbacked; the archive is keyed by bare name, overwritten each run, and lives in `.agent/state/` which `git clean -xdf` sweeps | `python/src/dotfiles_setup/plugin_remove.py:60-61`, `:178-188`, `:385-387` | code read |
| 19 | LOW | Q-CLAIM: the doctor prefixes every line with `removed plugin reappeared:` including `unreadable` lines, which state the opposite (the probe could not answer) | `python/src/dotfiles_setup/doctor.py:1352`; `python/src/dotfiles_setup/removed_plugins.py:18-19` | code read |
| 20 | LOW | Every mutation writes with a non-atomic `write_text` (truncate then write), and the fallback writes at `:289` and `:294` sit outside any `try`, so an `OSError` there escapes `apply()` mid-plan | `python/src/dotfiles_setup/plugin_remove.py:289`, `:292-294`, `:345`, `:468-469`, `:473`, `:517` | code read |
| 21 | LOW | `claude`/`codex` are invoked bare from `PATH`, not through `mise exec --` as `.claude/rules/ai-cli-invocation.md` requires for every AI CLI call | `python/src/dotfiles_setup/plugin_inventory.py:98`, `:118`; `python/src/dotfiles_setup/plugin_remove.py:316`, `:379`, `:402`, `:412` | E14 |
| 22 | LOW | The generated `.agents` mirrors of both new skills now read "Remove a Codex or codex plugin" / "Inventory one exact Codex or codex plugin selector": the mirror generator's substitution erases the Claude half of the scope; `skills-mirror --check` is green because it checks parity, not meaning | `.agents/skills/plugin-removal/SKILL.md:3`; `.agents/skills/plugin-inventory/SKILL.md:3` | E15 |

## Required questions

### Q-FRESH — is each decision re-validated against fresh inputs right before its action?

| Decision -> action | Re-validated? | Where |
|---|---|---|
| inventory -> `plan()` -> `apply()` | Same process, no re-inventory; acceptable only because every step re-reads its own file | `plugin_remove.py:585-595` |
| "marketplace == plugin name" -> `marketplace remove` | **Never validated** that no other installed plugin comes from it | `plugin_remove.py:115-128` (finding 2) |
| backup path set -> removal path set | **No** — removal recomputes `_cache_paths`; the guard is `(home, name)` | `plugin_remove.py:185-188`, `:385-387` (finding 18) |
| settings read -> CLI -> minimal write | Yes: the CLI result is re-read and compared semantically before the minimal write | `plugin_remove.py:309-329` |
| config.toml read -> edited write | No lock against a concurrent codex writer (lost update); rollback source is the disk, not memory | `plugin_remove.py:459-470` (finding 7) |
| watchlist plan -> `add_to_watchlist` | Yes: re-reads `doctor.toml` and re-checks "already watched" | `plugin_remove.py:488-497` |
| hook trust found by `locate()` -> text removal | No post-condition re-read | `plugin_remove.py:464-466` (finding 17) |

### Q-SCOPE

All 22 findings are in the new modules, their tests, or the generated mirrors of the
new skills, so all are in scope for this commit. Two are better as tickets than as
edits to this diff: 21 (bare `claude`/`codex`, which the rule itself defers to the
"Phase 11 codex class fix") and 22 (the mirror generator's `Claude Code` -> `Codex`
substitution, a generator defect that this diff only exposes).

### Q-CLAIM — operator-facing clauses and the line that enforces each

| Clause | Enforcing line | Holds? |
|---|---|---|
| doctor.toml: reports a watched name that becomes "installed" | Claude `plugin_state.py:143-163`; a codex plugin with `enabled = false` is dropped at `:264-266` | partly (3) |
| … "enabled" | `plugin_state.py:87-93`, `:268` | yes |
| … "registered as a marketplace" | `plugin_state.py:99`, `:172`, `:284` match only when marketplace == plugin name, and not for disabled codex plugins | **no** (3, 4) |
| … "cached" | `plugin_state.py:111` probes the wrong layout; `:286` exempts disabled codex plugins | **no** (1, 3) |
| … "hook-trusted" | `plugin_state.py:276` exempts disabled | partly (3) |
| doctor finding "removed plugin reappeared:" | `doctor.py:1352` — also printed for `unreadable` lines | **no** (19) |
| skill: "an `unreadable` location means the probe could not answer" | JSON/TOML readers and `iterdir`; not `exists()` | partly (9) |
| skill: "Codex matching uses both selector halves" | `plugin_inventory.py:137-141` for CLI rows; not for caches `plugin_remove.py:171` | partly (6) |
| skill: "keeps worktrees report-only" | `plan()` never reads `worktree_settings` | yes |
| skill step 4: re-inventory shows "every location … absent" | the same `locate()` with blind spots 1, 3, 4 and 9 | **no** |
| `remove-orphan-cache` ("orphan") | none | **no** (12) |
| "refusing cache removal without a prior backup" | `plugin_remove.py:385` — keyed on `(home, name)`, not paths | partly (18) |
| "hook-trust edit rolled back" | `plugin_remove.py:473` restores the disk backup | **no** (7) |
| "no matching hook-trust tables" (rc=0) | header regex `:26` only | partly (17) |
| "watchlist updated" | `tomllib.loads(changed)` — syntax only | **no** (14) |
| "removed one settings key; CLI state retained" | `plugin_remove.py:288-292` | yes |
| "Plan … mutate only with --apply" / "dry-run unless --apply" | `plugin_remove.py:589-594`; `plan()` writes nothing | yes |
| "Read-only inventory" | no write call in `plugin_inventory.py` / `plugin_state.py` | yes |
| suites.toml: "Every token … binds exactly one site" | replay: each token occurs once | yes |

### Doctor wiring

The wiring is sound: `check_removed_plugins` is registered (`doctor.py:1372`,
`tests/test_doctor.py` count 13 -> 14), `run_checks` contains any crash as a finding,
`collect()` always sets `home`, so the `setup.home is None` return is reachable
only from synthetic `Setup`s, and an unreadable `doctor.toml` degrades to the
`_REMOVED_PLUGINS_UNWATCHED` finding rather than silence. The defects are all in
what `locate()` can see (1, 3, 4, 9) and in the prefix wording (19).

## Stop condition

This round was OPEN HUNTING: the brief stated no domain with a cardinality, so it
cannot end the review loop whatever it found. Suggested bounded round-2 domain,
derived from the axes `locate()` and `plan()` actually read:
{harness: claude, codex} × {location kind: 8 + unreadable} × {selector shape:
name == marketplace, name != marketplace, same name in two marketplaces} ×
{codex `enabled`: true, false, absent} × {install scope: user, project, local}.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the reviewed commit, its tests, gates and live dry-runs
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline Claude Code docs corpus (`sources/agent-harness-docs/docs/claude-code`) for `plugin uninstall` / `marketplace remove` semantics

## Evidence log


### E1 — the real Claude cache layout (read-only `ls`, 2026-09-24)

`ls ~/.claude/plugins/cache/` lists MARKETPLACE names (`honcho`, `docker`,
`openai-codex`, `antigravity-for-claude-code`, …); each contains plugin dirs:
`honcho/: honcho honcho-dev`, `docker/: beta-mcp-skills mcp-toolkit`,
`antigravity-for-claude-code/: antigravity`. Codex's cache is also
`<marketplace>/<plugin>/<version>` (`~/.codex/plugins/cache/antigravity-for-claude-code/antigravity/0.28.0`).
The code joins `cache / name` for Claude (plugin_state.py:111, plugin_remove.py:162)
but `cache / <mk> / name` for codex (plugin_state.py:197, plugin_remove.py:171) —
the two harnesses are handled asymmetrically.

### E2 — `locate()` against the live home (read-only)

```
['antigravity'] [('claude','installed',...,'antigravity@antigravity-for-claude-code')]
    # no claude cache although ~/.claude/plugins/cache/antigravity-for-claude-code/antigravity exists
['honcho'] [('claude','installed',...,'honcho@honcho'), ('claude','known-marketplace',...,'honcho'),
            ('claude','cache','~/.claude/plugins/cache/honcho','honcho')]
    # 'cache' is the MARKETPLACE dir that also holds honcho-dev
['claudex-loop'] []
```

Control arm: `['planning-with-files']` returned 14 locations across all 8 kinds, so
the probe discriminates.

### E3 — live dry-runs of the reviewed CLI (`dotfiles-setup plugin-remove <sel>`, no `--apply`)

```
=== honcho@honcho            steps: 4  blockers: 0  rc=0
- backup-cache: .../.agent/state/plugin-cache-honcho.tar.gz
- remove-claude-marketplace: honcho
- remove-orphan-cache: honcho
- add-to-watchlist: honcho
=== claudex-loop@claudex-loop steps: 1 blockers: 0 rc=0
- remove-codex-plugin: claudex-loop@claudex-loop
=== antigravity@antigravity-for-claude-code steps: 4 blockers: 0 rc=0
- uninstall-project-scope: .../dotfiles
- uninstall-project-scope: .../knowledge-base
- remove-codex-plugin: antigravity@antigravity-for-claude-code
- add-to-watchlist: antigravity
```

`installed_plugins.json` holds both `honcho@honcho` and `honcho-dev@honcho`
(project scope). No `honcho` plan step uninstalls the `honcho@honcho` install record.

### E4 — codex config shape (keys and `enabled` only; no values printed)

```
plugin antigravity@antigravity-for-claude-code enabled= False
plugin claudex-loop@claudex-loop enabled= False
marketplaces: [..., 'antigravity-for-claude-code', ..., 'claudex-loop', ...]
hook antigravity@antigravity-for-claude-code:hooks/hooks.json:session_start:0:0  (4 such)
```

`doctor.check_removed_plugins(doctor.collect(repo))` on this machine returned
**0 findings** although `claudex-loop` (in `doctor.toml [removed_plugins].names`)
has a codex plugin entry, a registered marketplace and
`~/.codex/plugins/cache/claudex-loop/claudex-loop`. The `doctor.toml` comment says
the doctor "reports any watched name that becomes installed, enabled, registered
as a marketplace, cached or hook-trusted again". The disabled exemption is
deliberate for the doctor (`tests/test_plugin_state.py:88`,
`tests/test_removed_plugins.py:93`, `:173`) but nothing states it in the
operator-facing comment, and the removal inventory reuses the same `locate()`.

### E5 — fixtures

`_NAME = "example-plugin"`, `_PLUGIN = "example-plugin@example-plugin"` in every
new test module; `(claude / "cache" / _NAME).mkdir` and
`tmp_path / ".claude" / "plugins" / "cache" / "example-plugin"`.

### E6 — `_cache_paths` on the live home (read-only call)

```
exa ['~/.claude/plugins/cache/exa', '~/.codex/plugins/cache/exa/exa',
     '~/.codex/plugins/cache/claude-plugins-official/exa']
mattpocock-skills ['~/.codex/plugins/cache/mattpocock/mattpocock-skills',
                   '~/.codex/plugins/cache/claude-plugins-official/mattpocock-skills']
firecrawl ['~/.claude/plugins/cache/firecrawl',
           '~/.codex/plugins/cache/claude-plugins-official/firecrawl']
honcho ['~/.claude/plugins/cache/honcho']
```

`remove_orphan_cache` recomputes this list at action time and `rmtree`s each
(plugin_remove.py:387-393). `.claude/skills/plugin-inventory/SKILL.md` says
"Codex matching uses both selector halves"; that is true of `codex_cli_rows`
(plugin_inventory.py:137-141) and false of the cache mutation.

### E7 — hook-trust rollback (scratch `$HOME`, reviewed module imported directly)

```
A rc 1 | hook-trust edit rolled back: PermissionError
A config now: 'model = "STALE-FROM-AN-EARLIER-RUN"\n'      # current config destroyed
B rc 0 | removed 1 hook-trust table(s) | backup left behind: True   # control arm
```

Arm A: config held current content + two hook tables; a `.plugin-remove.bak`
from "an earlier run" was present and mode 0444. `backup.write_text` raised,
the `except` restored `backup.read_text()` over a config that had NOT been
edited. Arm B (no stale backup) succeeds and leaves the backup behind, which is
what arms the next run. On ENOSPC the same branch truncates both files, since
every write here is a non-atomic `write_text`.

### E8 — plan for a user-scope install (synthetic inventory)

```
P6 steps: [] blockers: ()
```

Inventory with a user `enabled` location, a user `installed` location and a
`claude_cli` row `scope=user enabled=True`. Live scope census of
`installed_plugins.json`: `{'project': 213, 'user': 53, 'local': 2}`.
Live `plugin-inventory honcho@honcho --json`: `claude_cli ['honcho@honcho
scope=project enabled=False']`, `project_settings []` — the CLI row is reported
and then dropped by `plan()`. `git grep claude_cli` over both modules: only the
dataclass field, the assignment and the print count.

### E9 — unreadable dirs (scratch home, Python 3.14.0)

```
P1 claude cache locked: []                                   # 0o000 parent -> "absent"
P1 control (unlocked): [PluginLocation(... kind='cache' ...)]
P1 codex cache_root locked: [PluginLocation(... kind='unreadable' ... 'PermissionError')]  # iterdir DOES raise
P1 codex mk-dir locked: []                                   # exists() swallowed it
```

The codex-root arm proves the harness can produce `unreadable`; the two `[]`
results are therefore the dead branches, not a broken probe.
`plugin_remove._cache_paths` also returns a partial list on `iterdir` OSError
(`:169-170`) and the backup/removal proceed on it with rc=0.

### E10 — vendor semantics (`$CC` = knowledge-base `agent-harness-docs/docs/claude-code`)

- `$CC/plugin-marketplaces.md:1304-1320`: "Removing a marketplace from its last
  remaining scope also uninstalls any plugins you installed from it"; without
  `--scope` "the declaration is removed from every editable scope".
- `$CC/plugins-reference.md:1046-1067`: "By default, uninstalling from the last
  remaining scope also deletes the plugin's `${CLAUDE_PLUGIN_DATA}` directory.
  Use `--keep-data` to preserve it".
- `$CC/discover-plugins.md:456-460`: "Removing a marketplace will uninstall any
  plugins you installed from it."

### E11 — the honcho project declaration

`~/dev/github/ray-manaloto/macos-development-environment/.claude/settings.json`:
`enabledPlugins` has no honcho key; `extraKnownMarketplaces` declares `honcho`;
`installed_plugins.json` records `honcho@honcho` and `honcho-dev@honcho` at
project scope for that path. `_enabled_in_settings` reads only `enabledPlugins`.

### E12 — why 13 is UNVERIFIED

`$CC/changelog.md:4754`: "Improved `/plugin uninstall` to disable project-scoped
plugins in `.claude/settings.local.json` instead of modifying
`.claude/settings.json`". The installed CLI (`claude 2.1.282`,
`claude plugin uninstall --help`) documents `--scope`, `--json` and `--keep-data`
but not which file a project uninstall writes. Settling it needs a real
project-scope install in a scratch project, which mutates
`~/.claude/plugins/installed_plugins.json` — outside what a cold reviewer may
write. The fixture at `tests/test_plugin_remove.py:93-96` rewrites settings.json,
so the other behaviour has no test.

### E13 — scratch probes of the reviewed module

```
P3a rc 0 | watchlist updated | names now: ['ponytail', 'claudex-loop']      # "newplug" absent
P3b rc 0 | watchlist updated | names now: ['ponytail', 'claudex-loop', 'newplug']  # control: shipped one-line shape
P4 raised ValueError not enough values to unpack (expected 3, got 1)         # tracked binary matching the name
P4 control: [RepoReference(... path='note.md', line=1 ...)]                  # same repo, text only
U1 raised UnicodeDecodeError        # installed_plugins.json with a 0xff byte
U1 control ['unreadable']           # a JSON syntax error IS contained
U2 raised UnicodeDecodeError        # ~/.codex/config.toml with a 0xff byte
B1 dry-run rc 0 | printed: plugin: foo@mk / steps: 0 / blockers: 1 / - doctor.toml is unreadable (FileNotFoundError)
```

P3a fixture: `names = [\n  "ponytail",  # removed in [#1363]\n  "claudex-loop",\n]`.
A live scan of every `~/dev/github/*/*` repo for `Binary file` lines on
`git grep -n -F -- codex` found none, so 15 is latent on this host.

### E14 — CLI resolution

`which -a codex` -> `~/.local/bin/codex` (twice) then the mise shim; both
subcommands used by the code exist in `codex-cli 0.156.1`
(`plugin remove`, `plugin marketplace remove`) and `claude 2.1.282`
(`plugin uninstall --json`, `plugin marketplace remove`).

### E15 — mirror check

`dotfiles-setup skills-mirror --check` -> `skills-mirror OK` rc=0, while
`diff .claude/skills/plugin-removal/SKILL.md .agents/skills/plugin-removal/SKILL.md`
shows only line 3: `Claude Code or codex` -> `Codex or codex`.

### Gates run at 9c624360

- `uv run --project python pytest tests/test_plugin_state.py tests/test_plugin_inventory.py tests/test_plugin_remove.py tests/test_removed_plugins.py tests/test_doctor.py -q` -> `142 passed` rc=0.
- Strict `per_path_tokens` replay over the whole `suites.toml`: 1,357 tokens, 0 missing; every `workflow.plugin-removal-wiring` token occurs exactly once in its file.
- The suites contract binds wiring strings only; no contract binds any error branch reviewed here.
