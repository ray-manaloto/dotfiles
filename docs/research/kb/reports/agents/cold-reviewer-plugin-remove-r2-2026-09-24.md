# Cold review ROUND 2 (verification) — d1fe8efc..48732d05

- Reviewer: cold-reviewer (Claude Opus), author family: codex
- Subject: `48732d05e7184816fbab5446d27a45dbcef3777a` (branch head), base `d1fe8efc73be862493468691d909ae2c38835bb9`.
  The fix commit under verification is `9c624360..48732d05`.
- Scope: everything except `docs/research/**` and `docs/specs/**`. The spec was not read.
- Round-1 report: `docs/research/kb/reports/agents/cold-reviewer-plugin-remove-2026-09-24.md` (22 findings).
- Memory: consulted `.claude/agent-memory-local/cold-reviewer/` (auto memory enabled).
- Status: COMPLETE. All 22 round-1 findings have a disposition, and the new-defect list is final.
- Tally: **13 FIXED, 8 PARTIAL, 1 NOT FIXED (ticketed #1370)**. New defects: **3 HIGH, 1 MEDIUM, 5 LOW**.
- Verdict: DO NOT SHIP `--apply`.
  - N2: every live plan that removes a Claude marketplace fails after the native CLI has already mutated state, then restores the JSON files over that mutation. Affected live plans: antigravity, exa, firecrawl, planning-with-files.
  - N8: the new dependency blocker never fires on the documented manifest format. The live `exa@exa` and `firecrawl@firecrawl` plans show 0 blockers, yet `aggregated-research@ray-manaloto` depends on both.
  - N1: a one-character selector typo (`honcho@`) still deletes a sibling's cache.

## Disposition convention

**Disposition** describes behaviour at `48732d05`. Each finding is read in the code, and exercised live, in a scratch home, or by a mutation wherever that was possible.

- **FIXED** requires two things: the behaviour is fixed, AND at least one test fails when the fix is reverted.
- **PARTIAL** covers either of two cases: the behaviour is only partly fixed, or a load-bearing part of the fix has no test that fails without it.
- **NOT FIXED** means the defect is still present.

**Guard** names the mutation (listed in F6) and the test(s) it turned red. Every mutation ran on a `git archive 48732d05` copy with `PYTHONPATH` shadowing the package.
- Harness control: M0 (`plugin_name` returns its input unchanged) turned 15 tests red, so the copy is the code under test.
- Baseline: M00 has 3 environment failures in `test_doctor.py`. They come from repository files that were not archived and are subtracted from every row.

## Dispositions

| # | R1 sev | Disposition | Fix file:line | Guard: test that fails without it | Evidence |
|---|---|---|---|---|---|
| 1 | HIGH | PARTIAL | reader: `plugin_state.py:179-183`, `:290-304` (cache = `installPath.parent`), `:190-233` (per-marketplace orphan scan); removal: `plugin_remove.py:332-367` | Removal half: M1d turns 2 tests red (`test_cache_removal_refuses_a_freshly_malformed_registry`, `test_symlinked_cache_is_dereferenced_but_only_the_link_is_deleted`). **Reader half: none.** M1c reverts both reader changes to `cache/<name>` and produces 0 new failures, because the fixture's `cache` kind is also satisfied by the codex cache | Live dry-run: antigravity now has `cache/antigravity-for-claude-code/antigravity`, honcho has `cache/honcho/honcho` (F7). The same layout comes back through an empty selector half (N1) |
| 2 | HIGH | FIXED (for well-formed selectors; see N1) | sibling notes `plugin_remove.py:208-230`; fresh re-check before the native call `:1288-1300`; exact recorded path set `:332-367`, `:838-850` | M2a → `test_plan_keeps_a_marketplace_with_siblings_and_names_them`; M2b → `test_apply_refuses_marketplace_removal_while_target_is_still_installed` | Live `honcho@honcho`: `marketplace kept: still used by honcho-dev@honcho`, orphan target `cache/honcho/honcho` only (F7) |
| 3 | HIGH | FIXED | `plugin_state.py:476-492` (every codex plugin entry, `enabled=` detail), `:494-526` (hooks, marketplace and cache no longer exempt); doctor-only policy `removed_plugins.py:43-67`, documented `doctor.toml:288-289` | M3a → `test_disabled_codex_plugin_still_reports_all_inventory_state` (+2); M3b → `test_a_codex_plugin_marked_disabled_is_not_a_finding`, `test_hook_trust_of_a_disabled_codex_plugin_is_not_a_finding` | Live: antigravity plan has `remove-codex-hook-trust`; claudex-loop plan has codex plugin + marketplace + cache; live doctor shows 0 findings, as `doctor.toml` now states (F7, F8) |
| 4 | MEDIUM | FIXED | `plugin_state.py:77-78` (marketplace half, falling back to the name) | M4 → `test_fixture_home_yields_every_location_kind_and_scope`, `test_disabled_codex_plugin_still_reports_all_inventory_state` | Live: antigravity plan removes marketplace `antigravity-for-claude-code` on both harnesses (F7) |
| 5 | MEDIUM | PARTIAL | `tests/test_plugin_state.py:20-22`, `:51-129` (`alpha@market` + `other-market`); `tests/test_plugin_inventory.py:189-297` | n/a (fixture finding) | Four fixtures still use name == marketplace, or no marketplace level: `tests/test_plugin_remove.py:23` (26 uses of `example-plugin@example-plugin`), `:180`, `:190`, `tests/test_removed_plugins.py:167`. The tests at `:180`/`:190` use a BARE selector with `cache/example-plugin`, so they certify the `cache / "" / name` join that N1 exploits. The fixture set still cannot tell the reader's cache layout apart (M1c: 0 failures) |
| 6 | HIGH | FIXED | `plugin_remove.py:359-366` (exact `cache/<mk>/<name>` on both harnesses) | M6 → `test_cache_backup_is_exact_manifested_and_requires_uninstall` (+4) | Live `exa@exa`: targets `~/.claude/plugins/cache/exa/exa` and `~/.codex/plugins/cache/exa/exa` only; `claude-plugins-official/exa` is untouched (F7) |
| 7 | HIGH | FIXED | timestamped exclusive backup `plugin_remove.py:463-473`; backup failure returns before any write `:1165-1168`; rollback writes the in-memory `original` `:1106-1117` | M7 (backup failure restores the newest `*.bak`) → `test_failed_hook_backup_never_restores_a_stale_backup` | code read + guard |
| 8 | HIGH | PARTIAL | `_installed_steps` `plugin_remove.py:126-181` (user, project and local scopes; unsupported scope and unusable projectPath become blockers) | M8 → `test_plan_covers_user_project_and_local_entries`, `test_plan_blocks_missing_project_path_and_dependencies_and_data_collision` | Installs are now planned: live exa and firecrawl include `uninstall-user-scope` (F7). Still unconsumed: an `enabledPlugins` key with no install record, in user or project settings, and a codex `[plugins."x"]` entry the codex CLI does not list. Each yields `['add-to-watchlist']` with 0 blockers (F9), and `claude_cli` rows are still never read by `plan()`. The uninstall registry post-condition has no test (N5) |
| 9 | MEDIUM | FIXED | `_stat_location` uses `lstat` `plugin_state.py:116-139`; scandir errors `:199-218`, `:339-358`, `:406-424`; `plugin_remove.py:116-123`, `:319-329` | M9 → `test_permission_denied_cache_is_unreadable_not_absent` | Scratch run with `cache/mk` at mode 000: full and bare selector → `unreadable PermissionError`; `_removal_sources` raises; control (unlocked) → `cache` (F10) |
| 10 | MEDIUM | FIXED | `--keep-data` on every uninstall `plugin_remove.py:148-149`, `:175-176`, `:762`; data dir goes into the manifested archive before deletion `:365-366`, `:392-415`; marketplace removal only when it has no siblings | M10a → `test_project_uninstall_removes_surviving_key_and_added_local_override`; M10b → `test_persistent_data_is_backed_up_before_it_is_removed` | The archive, now the only copy of plugin data, still lives in `.agent/state/` (see 18) |
| 11 | MEDIUM | FIXED | `_matches_settings` reads `extraKnownMarketplaces` `plugin_inventory.py:539-554`; install records of every scope become `installed` locations `plugin_state.py:276-289` | M11 → `test_inventory_reads_marketplace_declarations_and_planning_evidence` | Live `honcho@honcho`: `uninstall-project-scope …/macos-development-environment` (F7). Consuming a declaration fails at apply (N2) |
| 12 | MEDIUM | FIXED (for well-formed selectors; see N1) | registry re-read before deletion `plugin_remove.py:878-882`; deletes only the recorded set `:838-850` | M12 → `test_cache_backup_is_exact_manifested_and_requires_uninstall` | `honcho@` keys the re-check on a selector that is never installed (N1) |
| 13 | MEDIUM (UNVERIFIED) | FIXED in code; the vendor behaviour is still UNVERIFIED | `_prepare_uninstall` snapshots `settings.json` + `settings.local.json` `plugin_remove.py:725-738`; goal state per file `:563-678`; registry post-condition `:789-792` | M13 → `test_project_uninstall_removes_surviving_key_and_added_local_override` (the fake CLI writes `false` into `settings.local.json`) | Both CLI behaviours are now handled. Which file the real `claude plugin uninstall --scope project` writes is still unmeasured. The registry post-condition has no test (N5) |
| 14 | LOW | PARTIAL | comment- and quote-aware `_array_span` `plugin_remove.py:1175-1214`; name verification `:1255-1259` | M14b → `test_watchlist_multiline_comment_cannot_hide_a_false_success`. **The verification clause itself is unguarded**: M14a deletes `name not in names` and produces 0 failures | This fix introduced N6 (inline comments deleted) |
| 15 | LOW | PARTIAL | `git grep -I -z` + byte decode `plugin_inventory.py:468-523`; `UnicodeDecodeError` caught at `plugin_state.py:90`, `:464` and `plugin_inventory.py:212`, `:281`, `:532`, `:542` | M15a → `test_live_references_uses_binary_exclusion_and_replacement_decode`. **Decode half unguarded**: M15b drops `UnicodeDecodeError` from `_load_json` and produces 0 failures | Scratch: registry with an `0xff` byte → `unreadable UnicodeDecodeError`; codex config with `0xff` → `unreadable` (F10). The new byte-parse loop is quadratic (N9) |
| 16 | LOW | FIXED | `plugin_remove.py:1424` | M16 → `test_dry_run_with_a_blocker_exits_one` | code read + guard |
| 17 | LOW | PARTIAL | line editor for header, inline, subtable and root-dotted forms `plugin_remove.py:1021-1103`; post-condition re-read `:1120-1139` | M17a → `test_hook_trust_handles_inline_and_subtable_forms` (+1). **Post-condition unguarded**: M17b deletes it and produces 0 failures, because the multi-line test rolls back through the TOML parse error instead | A form tomllib parses but the line editor does not model, `[hooks]` + `state."k" = {…}`, still returns **rc=0 `no matching hook-trust entries`** while `locate()` reports the trust. The `count == 0` short-circuit at `:1163-1164` runs before the post-condition. This is the round-1 symptom; latent here, where the live config is 47/47 header form (F10) |
| 18 | LOW | PARTIAL | path set recorded in `_BackupRecord` `plugin_remove.py:70-76`, `:414`; removal deletes that set `:838-850`, `:884`; archive timestamped, keyed by selector, created with exclusive `x:gz` `:96-100`, `:403` | **None**: M18 (removal recomputes `_removal_sources`) produces 0 failures | The archive still lives under `.agent/` (`.gitignore:124`), which `git clean -xdf` sweeps. It now holds the only copy of plugin data |
| 19 | LOW | FIXED | `doctor.py:1351-1360` (`removed plugin could not check:`) | M19 → `test_the_doctor_labels_unreadable_state_as_could_not_check` | code read + guard |
| 20 | LOW | PARTIAL | every write goes through `_atomic_write` (mkstemp + fsync + replace) `plugin_remove.py:448-460`. `grep write_text\|write_bytes` over `plugin_remove.py` finds 0 hits, and the fallback writes now sit inside `try` | **None**: M20 (plain `write_bytes`) produces 0 failures | This fix introduced N7 (mode 0600, symlink replaced) |
| 21 | LOW | FIXED | `plugin_inventory.py:97`, `plugin_remove.py:421` (`mise exec --`) | M21a → `test_apply_stops_at_the_first_failing_step` (+1); M21b → 5 tests | code read + guard |
| 22 | LOW | NOT FIXED (ticketed **#1370**, open) | none in this diff | n/a | `.agents/skills/plugin-removal/SKILL.md:3` and `.agents/skills/plugin-inventory/SKILL.md:3` still say "Codex or codex"; `diff` against `.claude/skills/*` differs only at line 3. Ticketed as round 1's Q-SCOPE recommended |

## New defects introduced by the fixes

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| N1 | HIGH | Selector validation is only `"@" in plugin`, so `honcho@` and `@honcho` are accepted. `_removal_sources` then joins `cache / "" / name` (or `cache / mk / ""`), which is the MARKETPLACE directory. `_selector_installed` checks the key `honcho@`, which is never installed. The live dry-run of `honcho@` returns rc=0 with 0 blockers and shows `remove-orphan-cache: …/cache/honcho/honcho, …/data/honcho-honcho`. `--apply` would instead rmtree `~/.claude/plugins/cache/honcho`, taking the installed `honcho-dev` with it, and leave the displayed data directory in place. So the plan's displayed target is not the path that apply deletes, and the round-1 class (items 1 and 2) survives through an empty selector half | `python/src/dotfiles_setup/plugin_inventory.py:616`; `python/src/dotfiles_setup/plugin_remove.py:332-367`, `:819-835` | F1, F2 |
| N2 | HIGH | `remove-claude-marketplace` cannot succeed on a real registry. `_remove_json_key_line` matches only a one-line value containing no comma (`[^,\n]+`), but every real `known_marketplaces.json` entry, and every real `extraKnownMarketplaces` entry, is a multi-field object: 0 of the 12 live declarations checked can be edited. By the time the goal check fails, the native `claude plugin marketplace remove` has already run, which per the vendor removes the shared state and cache. `_restore_snapshots` then writes back `known_marketplaces.json`, `installed_plugins.json` and every settings file, and the step returns rc=1. The registry is left declaring a marketplace whose `installLocation` is gone, and apply stops before the codex, hook-trust, cache and watchlist steps. The step is present in the live plans for antigravity, exa, firecrawl and planning-with-files. No test exercises this step's success path. This contradicts the skill's claim that the apply path "preserves minimal settings diffs" | `python/src/dotfiles_setup/plugin_remove.py:507-534`, `:583-605`, `:901-927` | F3, F4 |
| N8 | HIGH | The dependent-plugin blocker never fires on the documented manifest format. `dependencies` is an array of bare-name strings or `{name, version, marketplace}` objects (`$CC/plugin-dependencies.md:25-47`). `_manifest_dependencies` drops objects, keeps bare names, and then compares them with the full selector (`selector in dependencies`). The test fixture uses an invented dict keyed by selectors. Live: `aggregated-research@ray-manaloto` declares `exa@exa`, `firecrawl@firecrawl`, `context7@context7-marketplace` and `last30days@last30days-skill` as object dependencies, and `_installed_metadata` returns `dependent_plugins=()` for all four. The live `exa@exa` and `firecrawl@firecrawl` dry-runs show 0 blockers, and plan to uninstall both and remove their marketplaces. The commit message's "a dependent plugin is a blocker" has no enforcing line for real manifests. The vendor's own `plugin disable` refuses this case (`$CC/plugins-reference.md:1122`) | `python/src/dotfiles_setup/plugin_inventory.py:205-226`, `:249-272`; `tests/test_plugin_inventory.py:206-210` | F5, F7 |
| N3 | MEDIUM | Every edit leaves a `<file>.<stamp>.bak` beside the file, nothing cleans them up, and none is gitignored anywhere. `settings.local.json.<stamp>.bak` is a verbatim copy of a gitignored personal-settings file, placed as an **un-ignored** file in another repository's `.claude/`. `doctor.toml.<stamp>.bak` lands in the dotfiles root. Live: dotfiles, knowledge-base and macos-development-environment all have `settings.local.json`; `git check-ignore` matches the original and does NOT match the `.bak` in all three | `python/src/dotfiles_setup/plugin_remove.py:463-473`, `:476-491`, `:725-735`, `:892-898`, `:1260` | F11 |
| N4 | LOW | Bare-name data matching is a hyphen-prefix match, and the doctor watchlist uses bare names. Live: `clangd` reports `data/clangd-lsp-claude-plugins-official` (the `clangd-lsp` plugin) and reports `clangd-claude-code-lsps` twice; `gopls` does the same. A watched name that is the hyphen-prefix of another plugin therefore produces a doctor finding that points the operator at a different plugin's data | `python/src/dotfiles_setup/plugin_state.py:338-360` | F12 |
| N5 | LOW | `uninstall_project_scope` passes `home=project`, so its registry snapshot and its "installed scope survived uninstall" post-condition both read `<project>/.claude/plugins/installed_plugins.json`, which never exists. All four uninstall tests go through this wrapper. As a result nothing tests the post-condition: MSA deletes it and produces 0 failures | `python/src/dotfiles_setup/plugin_remove.py:796-798`, `:789-792`; `tests/test_plugin_remove.py:105`, `:141`, `:433`, `:458` | F6 |
| N6 | LOW | `add_to_watchlist` replaces the whole `names` array with `json.dumps(...)`. That collapses a multi-line array and deletes its inline provenance comments in the tracked `doctor.toml`. The comment-bracket test asserts only that the name is present | `python/src/dotfiles_setup/plugin_remove.py:1232-1233`; `tests/test_plugin_remove.py:643-658` | F10 |
| N7 | LOW | `_atomic_write` writes through `mkstemp` (mode 0600) and then `replace()`. Every edited file therefore becomes 0600, and a symlinked config would be replaced by a regular file. Measured: `doctor.toml` went from 0644 to 0600. The live `known_marketplaces.json`, `installed_plugins.json` and project `settings*.json` are 0644, and none of them is a symlink, so the symlink half is latent | `python/src/dotfiles_setup/plugin_remove.py:448-460` | F10, F11 |
| N9 | LOW | The new `-z` byte parse in `live_references` re-slices the remaining payload once per record, which makes it O(n²): 10k, 20k and 40k records took 0.28s, 1.23s and 5.23s. `PROBE_TIMEOUT` bounds only the `git grep` subprocess. With `@honcho` (empty needle; 218,035 matching lines in dotfiles alone) the dry-run printed nothing for more than 15 minutes and was killed. It is reachable only with a malformed or very short name | `python/src/dotfiles_setup/plugin_inventory.py:504-523` | F13 |

## Enumeration check (is the round-1 domain the right space?)

Round 1 proposed a round-2 domain: {harness} × {location kind} × {selector shape: name == mk, name != mk, same name in two mks} × {codex enabled} × {install scope}. This round shows the domain is missing two axes:

- **Selector shape needs an "empty half" cell** (`name@`, `@mk`). That is where N1 and N9 live, and no validation rejects it.
- **Manifest dependency format** (bare string, `{name, marketplace}` object) is an input `plan()` reads that no axis varies. That is where N8 lives.

A further round, if any, should be scoped to those two new cells, plus N2's declaration-shape cell (single-line vs multi-field object).

## Q-CLAIM spot check on strings this fix added

| Clause | Enforcing line | Holds? |
|---|---|---|
| skill: "Confirm every … exact cache/data target" | plan targets come from `locate()`; apply deletes `_removal_sources()` | **no** for empty-half selectors (N1) |
| skill: "preserves minimal settings diffs" | `_remove_json_key_line` `plugin_remove.py:507-534` | **no** for marketplace declarations (N2) |
| skill-inventory: "They guard cascading marketplace removal and lossy data-directory names" | siblings: yes (`:208-230`, `:1288-1300`); dependencies: `plugin_inventory.py:205-272` | **partly**: the dependency guard is inert (N8) |
| commit: "a dependent plugin is a blocker, never an empty plan" | `plugin_remove.py:255-258` fed by `plugin_inventory.py:249-272` | **no** (N8) |
| doctor.toml: disabled codex plugin "is exempt; inventory still reports all of its residual state" | `removed_plugins.py:43-67`; `plugin_state.py:476-526` | yes |
| `removed plugin could not check:` | `doctor.py:1353-1354` | yes |
| "no matching hook-trust entries" (rc=0) | `plugin_remove.py:1163-1164` (edit count, not the parsed state) | **no** (item 17 residual) |
| "watchlist updated and verified" | `plugin_remove.py:1255-1259` | yes (unguarded, M14a) |

## Evidence log

### F1 — live dry-run of an empty-half selector (no `--apply`)

```
=== honcho@   rc=0
steps: 3
- backup-cache: …/.agent/state/plugin-removal-honcho-.<stamp>.tar.gz
- remove-orphan-cache: ~/.claude/plugins/cache/honcho/honcho, ~/.claude/plugins/data/honcho-honcho
- add-to-watchlist: honcho
blockers: 0
_removal_sources('honcho@', ~)       -> [('claude-cache', '~/.claude/plugins/cache/honcho')]
_removal_sources('@honcho', ~)       -> [('claude-cache', '~/.claude/plugins/cache/honcho')]
_removal_sources('honcho@honcho', ~) -> [cache/honcho/honcho, data/honcho-honcho]   # control arm
ls ~/.claude/plugins/cache/honcho/   -> honcho  honcho-dev
```

### F2 — scratch-home replay of backup + removal for `honcho@` (reviewed module, scratch `$HOME`)

```
backup 0 backed up 1 path(s) with manifest
remove 0 removed 1 backed-up path(s)
cache/honcho exists: False | data/honcho-honcho exists: True
registry still lists: ['honcho@honcho', 'honcho-dev@honcho']
```

Both installed plugins lost their caches, and the path the plan displayed (`data/honcho-honcho`)
survived. `locate(['honcho@'])` also reports `data/honcho-honcho` twice (the installed loop and
the bare-name scan both add it).

### F3 — `_minimal_goal_bytes` on the REAL declaration files, in memory (no writes)

```
~/.claude/plugins/known_marketplaces.json (41 keys, 331 lines):
  antigravity-for-claude-code / exa / firecrawl / planning-with-files / honcho: value_type=dict -> minimal_ok=False
dotfiles/.claude/settings.json extraKnownMarketplaces: antigravity-for-claude-code / planning-with-files / exa -> minimal_ok=False
knowledge-base/.claude/settings.json extraKnownMarketplaces: antigravity-for-claude-code / planning-with-files / exa / firecrawl -> minimal_ok=False
control: dotfiles/.claude/settings.json enabledPlugins antigravity@… / exa@exa (bool values) -> minimal_ok=True
```

### F4 — scratch replay of `_remove_claude_marketplace_step` with a CLI stub

The stub does what the vendor documents: it drops the key and the shared clone.

```
A dict value, pretty-printed (real shape) | rc 1 | known_marketplaces.json minimal edit does not match the goal state
   known still declares mk: True | its installLocation exists: False
B single-line value containing commas     | rc 1 | known_marketplaces.json has no unique line for mk
   known still declares mk: True | its installLocation exists: False
C positive arm: comma-free single-line    | rc 0 | removed marketplace and verified declarations
```

Arm C proves the harness can succeed, so A and B are real negatives. Vendor text: without
`--scope`, the declaration is removed from every editable scope, and only a scoped removal
preserves "the shared state, cache, and installed plugin data"
(`$CC/plugin-marketplaces.md:1304-1320`). `grep` of `tests/test_plugin_remove.py` finds only the
refusal test for this step (`:690-735`); there is no success-path test.

### F5 — live manifest census and dependency-blocker replay (read-only)

```
manifests read: 165
('aggregated-research@ray-manaloto', 'list', [{'name': 'firecrawl', 'marketplace': 'firecrawl'},
  {'name': 'exa', 'marketplace': 'exa'}, {'name': 'context7', 'marketplace': 'context7-marketplace'},
  {'name': 'last30days', 'marketplace': 'last30days-skill'}])
auto-installed registry keys: ['last30days@last30days-skill', 'context7@context7-marketplace', 'exa@exa', 'firecrawl@firecrawl']
target firecrawl@firecrawl: dependent_plugins=()  (expected aggregated-research@ray-manaloto)
target exa@exa:             dependent_plugins=()
target context7@context7-marketplace: dependent_plugins=()
target last30days@last30days-skill:   dependent_plugins=()
```

Fixture used by the only dependency test: `{"dependencies": {"a-b@c": "1.0.0"}}`
(`tests/test_plugin_inventory.py:206-210`). That is a dict keyed by selectors; the documented format is
an array of `"name"` strings or `{name, version, marketplace}` objects.

### F6 — mutation arms (`git archive 48732d05` + `PYTHONPATH`, 163 tests, baseline 3 env failures subtracted)

| id | mutation | new failures |
|---|---|---|
| M00 | none | 0 |
| M0 | control: `plugin_name` returns its input | 15 |
| M1a | reader: no `installPath` cache | **0** |
| M1b | reader: orphan scan uses `cache/<name>` | **0** |
| M1c | M1a + M1b | **0** |
| M1d | removal source uses `cache/<name>` | 2 |
| M2a | no sibling list | 1 |
| M2b | no fresh marketplace guard | 1 |
| M3a | state reader drops disabled codex plugins | 3 |
| M3b | doctor drops the disable exemption | 2 |
| M4 | marketplaces matched by bare name | 2 |
| M6 | codex cache scanned across every marketplace | 5 |
| M7 | backup failure restores the newest `*.bak` | 1 |
| M8 | no uninstall steps | 2 |
| M9 | `_stat_location` OSError → absent | 1 |
| M10a | no `--keep-data` | 1 |
| M10b | data not in the backup | 1 |
| M11 | settings ignore marketplace declarations | 1 |
| M12 | no installed re-check before deletion | 1 |
| M13 | no `settings.local.json` goal | 1 |
| M14a | no name-landed verification | **0** |
| M14b | comment-blind array scan | 1 |
| M15a | no `git grep -I` | 1 |
| M15b | `_load_json` lets `UnicodeDecodeError` escape | **0** |
| M16 | dry run always rc=0 | 1 |
| M17a | inline hook form not handled | 2 |
| M17b | no hook post-condition | **0** |
| M18 | removal recomputes the path set | **0** |
| M19 | doctor single prefix | 1 |
| M20 | non-atomic write | **0** |
| M21a | bare CLI in remove | 2 |
| M21b | bare CLI in inventory | 5 |
| MSA | uninstall registry post-condition deleted | **0** |
| MSR | dependency blocker deleted | 1 (the dict-format fixture) |

### F7 — live dry-runs at 48732d05 (`dotfiles-setup plugin-remove <sel>`, no `--apply`), all rc=0, blockers 0

```
honcho@honcho: backup-cache; uninstall-project-scope …/macos-development-environment;
  remove-orphan-cache ~/.claude/plugins/cache/honcho/honcho, ~/.claude/plugins/data/honcho-honcho; add-to-watchlist
  notes: marketplace kept: still used by honcho-dev@honcho
claudex-loop@claudex-loop: backup-cache; remove-codex-plugin; remove-codex-marketplace claudex-loop;
  remove-orphan-cache ~/.codex/plugins/cache/claudex-loop/claudex-loop
antigravity@antigravity-for-claude-code: backup-cache; uninstall-project-scope ×2 (knowledge-base, dotfiles);
  remove-claude-marketplace; remove-codex-plugin; remove-codex-marketplace; remove-codex-hook-trust;
  remove-orphan-cache (claude cache/antigravity-for-claude-code/antigravity, data, codex cache); add-to-watchlist
exa@exa: backup-cache; uninstall-project-scope dotfiles; uninstall-user-scope; uninstall-project-scope knowledge-base;
  remove-claude-marketplace exa; remove-codex-plugin; remove-codex-marketplace;
  remove-orphan-cache ~/.claude/plugins/cache/exa/exa, ~/.codex/plugins/cache/exa/exa; add-to-watchlist
firecrawl@firecrawl: backup-cache; uninstall-user-scope; uninstall-project-scope knowledge-base;
  remove-claude-marketplace firecrawl; remove-orphan-cache ~/.claude/plugins/cache/firecrawl/firecrawl; add-to-watchlist
planning-with-files@planning-with-files: 9 steps incl. remove-claude-marketplace and remove-codex-hook-trust
```

Round-1 controls reproduced: the honcho marketplace is kept, codex `claude-plugins-official/exa` is
not targeted, and the disabled antigravity plugin's hook trust is planned.

### F8 — live doctor

`doctor.check_removed_plugins(doctor.collect(repo))` → `[]`. claudex-loop is exempt by the
now-documented policy at `doctor.toml:288-289`, and ponytail is absent.

### F9 — synthetic plans (reviewed `plan()`, scratch `doctor.toml`)

```
A user settings enable, no install record      -> ['add-to-watchlist'] blockers 0
B project settings enable, no install record   -> ['add-to-watchlist'] blockers 0
C control: user install record                 -> ['uninstall-user-scope', 'add-to-watchlist']
D codex config entry, CLI says not installed   -> ['add-to-watchlist'] blockers 0
```

### F10 — scratch probes (reviewed module, scratch homes)

```
R1-9 locked cache/mk, full selector: [('unreadable', 'PermissionError')]
R1-9 locked cache/mk, bare name    : [('unreadable', 'PermissionError')]
R1-9 _removal_sources              : raised 'cannot inspect removal source …/cache/mk/alpha: PermissionError'
R1-9 control unlocked              : [('cache', '')]
R1-15 registry 0xff: [('unreadable', 'UnicodeDecodeError')]
R1-15 codex 0xff   : [('unreadable', 'UnicodeDecodeError')]
R1-17 [hooks] + state."k" form: 0 no matching hook-trust entries | config unchanged: True | locate still finds: ['codex-hook-trust']
R1-14 add_to_watchlist: 0 watchlist updated and verified
   before: ['[removed_plugins]', 'names = [', '  "ponytail",  # removed in [#1363]', '  "claudex-loop",  # disabled, see #1310', ']']
   after : ['[removed_plugins]', 'names = ["ponytail", "claudex-loop", "alpha"]']
   .bak left beside doctor.toml: ['doctor…bak'] | mode: 0o600
```

### F11 — ignore status and file modes (read-only)

```
dotfiles / knowledge-base / macos-development-environment:
  .claude/settings.json.<stamp>.bak        -> NOT IGNORED
  .claude/settings.local.json.<stamp>.bak  -> NOT IGNORED
  .claude/settings.local.json              -> ignored (.gitignore:37 / ~/.gitignore_global:37 / .gitignore:59)   # control
dotfiles doctor.toml.<stamp>.bak           -> NOT IGNORED;  .agent/state/x -> ignored (.gitignore:124)
settings.local.json exists in all three (175 / 540 / 2103 bytes)
modes: installed_plugins.json 0644, known_marketplaces.json 0644, ~/.claude/settings.json 0600, ~/.codex/config.toml 0600; no symlinks
```

### F12 — bare-name data prefix (read-only, live home)

```
clangd                  -> data/clangd-claude-code-lsps (key clangd@claude-code-lsps),
                           data/clangd-lsp-claude-plugins-official (key clangd), data/clangd-claude-code-lsps (key clangd)
clangd@claude-code-lsps -> data/clangd-claude-code-lsps only          # control
gopls                   -> gopls-claude-code-lsps ×2, gopls-lsp-claude-plugins-official
```

### F13 — quadratic parse

```
live_references parse, synthetic payload: 10000 rec 0.28s | 20000 rec 1.23s | 40000 rec 5.23s
git grep -F -c "" in dotfiles (historical pathspecs excluded): 218035 lines; 79 depth-2 repos under ~/dev/github
`plugin-remove @honcho` dry-run: no output after 15m13s; killed (rc=143)
```

### Gates run at 48732d05

- `uv run --project python pytest tests/test_plugin_state.py tests/test_plugin_inventory.py tests/test_plugin_remove.py tests/test_removed_plugins.py tests/test_doctor.py -q` → `163 passed` rc=0.
- All mutations used the archive harness; the harness control (M0) goes red, so the copy is the code under test.
- `mise run lint`, `dotfiles-setup verify run` and the `.agents` mirror check were NOT re-run in this round, because the brief bounds it to dispositions and new defects. Item 22's mirror text was read directly.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): the reviewed range, its tests, live dry-runs, the mutation harness, and issue search (#1370)
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): the offline Claude Code docs corpus (`plugin-marketplaces.md`, `plugins-reference.md`, `plugin-dependencies.md`), and its `.claude/settings.json` shape (read-only)
- [ray-manaloto/macos-development-environment](https://github.com/ray-manaloto/macos-development-environment): gitignore status and existence of its `.claude/settings.local.json` (read-only)
