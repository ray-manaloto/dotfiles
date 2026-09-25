# Opus fallback implementer — plugin-remove r3 (2026-09-25)

- Lane: Claude Opus fallback implementer (codex lane unavailable until 2026-09-30).
- Spec: `docs/specs/plugin-remove-pipeline-r3.md` (+ base and r2 specs); review
  `docs/research/kb/reports/agents/cold-reviewer-plugin-remove-r2-2026-09-24.md`.
- Base: `48732d05` on `feat/plugin-remove-pipeline`. No commit (caller commits).
- Status: COMPLETE. All N1-N9 and the 8 PARTIAL rows closed; every closure has a test that goes red when the fix is reverted (scratch-copy mutation run: 33 fix-reverting mutations all red, plus the M0 control arm red; baseline and restored copies green). No commit.

## Live read-only facts gathered before coding

- `claude plugin marketplace remove --help` (2.1.282): `--scope <scope>` "Remove the marketplace
  declaration from a specific settings scope: user, project, or local. Omit to remove it from every scope."
- Live declarations (keys only): `exa` is declared in dotfiles + knowledge-base project
  `settings.json` and registered in `known_marketplaces.json` (fields `installLocation, lastUpdated,
  source`); it is NOT in `~/.claude/settings.json` `extraKnownMarketplaces` (that holds
  gary-sonyak, i-have-adhd, planning-with-files, ray-manaloto, typesafe-ai). No project has a
  `settings.local.json` declaration.
- `aggregated-research@ray-manaloto` plugin.json: 4 object deps `{name, marketplace}` (T2 confirmed);
  its marketplace entry (`~/.claude/plugins/marketplaces/ray-manaloto/.claude-plugin/marketplace.json`)
  declares no dependencies; 0 live marketplace entries declare dependencies.
- Registry: `aggregated-research@ray-manaloto` has user + project entries; `exa@exa` has project x2 + user(`auto: true`).

## Progress log
- plugin_state: added `parse_selector` (N1) and public `data_id`; bare-name data scan now checks only
  exact ids `data_id(name@m)` for marketplaces the harness records mention (N4), dedup by id.
- plugin_inventory: `inventory` calls `parse_selector` first; dependencies resolved per
  `$CC/plugin-dependencies.md:40-46` from plugin.json AND the marketplace entry, bare or object items,
  default = declaring plugin's marketplace (N8); `enabled_dependents` from `claude plugin list`;
  `enabling_settings` (row 8); `git grep -z` parsed with one split (N9). `claude_ids` became a
  dict id->enabled so the `workflow.plugin-removal-wiring` token line is unchanged.
- plugin_remove rewritten around the two file classes (harness-owned: backed up, never restored,
  verified by re-read; repo/user settings: whole-member-span minimal diff, restored from memory).
  Per-scope `claude plugin marketplace remove <m> --scope project|local|user` (N2), containment at
  plan time + re-check before each delete + in `_removal_sources` (N1), `dereference=False` + link
  target in manifest, backups mirrored under `.agent/state/plugin-remove/<stamp>/` created 0600 (N3),
  `uninstall_project_scope(..., home=)` post-condition on the real home (N5), array-text insert for
  the watchlist + exact-list verification (N6/row 14), mode/symlink-preserving atomic write (N7),
  row 8 steps `remove-settings-key` / `remove-codex-config-plugin`, generic TOML entry editor that
  resolves `[hooks]` + `state."k"` and fails when entries remain (row 17).
- Tests rewritten on `alpha@market` fixtures with an autouse fixture that points HOME/cwd at tmp.
  NOTE: before that fixture existed, one run of the OLD tests against the new defaults READ (never
  wrote) the real `~/.claude/plugins/installed_plugins.json` into `.agent/state/plugin-remove/`
  backups; those copies were deleted (`rm -rf .agent/state/plugin-remove`) and no real file was modified.
- Targeted suites: 212 passed; ruff/ty clean on all touched files.
- Live dry run of `exa@exa` (after the first parser) returned a NEW blocker `git grep returned malformed
  output for ~/dev/github/fanvanzh/3dtiles`: `geoids/geoids/egm96-5.pgm` passes `git grep -I` (the
  binary heuristic reads only the first 8000 bytes) and its matched "lines" contain NUL bytes
  (captured: 16 NULs over 7 records; line 2 of the output has 3 NULs). "Split on NUL once" is
  therefore unsound on real data. Replaced with a single forward cursor scan (NUL, NUL, LF from the
  cursor) — still one pass / linear. Captured bytes parse to 7 records. See Deviation D1.

## Files changed

- `python/src/dotfiles_setup/plugin_state.py` — `parse_selector`, public `data_id`, exact-id data scan.
- `python/src/dotfiles_setup/plugin_inventory.py` — selector validation, dependency resolution,
  `enabled_dependents` / `enabling_settings`, linear `git grep -z` parser.
- `python/src/dotfiles_setup/plugin_remove.py` — rewritten (file classes, containment, per-scope
  marketplace removal, mirrored backups, atomic write, row-8 steps, TOML entry editor, watchlist insert).
- `tests/test_plugin_state.py`, `tests/test_plugin_inventory.py`, `tests/test_plugin_remove.py`,
  `tests/test_removed_plugins.py`, `tests/TEST-INDEX.md`.
- No new modules, no `.sh`, no inline suppressions, `.gitignore` untouched (`.agent/` already ignored).
  Staged with `git add` (explicit paths) for the lint gate; NOT committed.

## Dispositions (test that goes red when the fix is reverted)

Mutation harness: `.agent/logs/plugin-remove-r3/mutate.py`, results `mutation-results.json` /
`mutation-summary.txt`. Scratch copy = `git archive HEAD` + the 7 changed files, `PYTHONPATH`
shadowing the package. Control arm M0 (`plugin_name` returns its input) -> 13 red, so the copy is the
code under test. M00 baseline 103 passed, M99 restored 103 passed.

| Finding | Fix | Mutation (revert) | Red test(s) |
|---|---|---|---|
| N1 selector | `parse_selector` in state; called by `inventory`, `plan`, `plugin_remove_main` (exit 2), `_removal_sources`, codex CLI probe | N1a `"@" in` only | `test_parse_selector_rejects_every_malformed_shape[*]` (8), `test_plan_rejects_a_malformed_selector_before_building_a_path[*]`, `test_plugin_remove_main_exits_two_on_an_empty_selector_half`, `test_inventory_rejects_a_malformed_selector_before_any_probe[*]` (17 total) |
| N1 containment (plan) | escape = blocker | N1b | `test_plan_blocks_a_removal_target_outside_the_plugin_roots` |
| N1 containment (sources) | `_removal_sources` raises on escape | N1d | `test_backup_refuses_a_registry_install_path_outside_the_plugin_root` |
| N1 TOCTOU | re-check per path immediately before delete | N1c | `test_removal_rechecks_containment_immediately_before_delete` |
| symlinks | `dereference=False`, link target in manifest | N1e | `test_symlinked_cache_is_archived_as_a_link_and_only_the_link_is_deleted` |
| N2 per-scope CLI | `--scope project/local` (cwd=project) + `--scope user` (cwd=repo_root) | N2a drop `--scope` | `test_marketplace_removal_calls_each_declared_scope_and_keeps_minimal_diffs`, `test_marketplace_removal_never_restores_the_harness_registry`, `test_end_to_end_apply_removes_the_last_plugin_and_its_marketplace` |
| N2 harness never restored | known/installed backed up only | N2b restore harness | `test_marketplace_removal_never_restores_the_harness_registry` |
| N2 whole-span minimal diff | brace-matched, string-aware member span | N2c old single-line remover | 5 incl. the N2 success test and the last-plugin e2e |
| N3 backups | `<repo>/.agent/state/plugin-remove/<stamp>/<mirrored path>`, created 0600 | N3 beside the file | `test_backups_land_under_agent_state_never_beside_the_file` (+5) |
| N4 exact data id | bare name -> `data_id(name@m)` for recorded marketplaces only | N4 prefix match | `test_bare_name_data_matches_exact_ids_never_a_prefix`, `test_a_surviving_data_directory_is_a_finding` |
| N4 collision blocker | (kept) `data_collisions` -> blocker | — | `test_plan_blocks_missing_project_path_and_dependencies_and_data_collision` |
| N5 real-home registry | `uninstall_project_scope(..., home=)` defaults to `Path.home()` | N5a home=project; N5b no post-condition | `test_uninstall_post_condition_reads_the_real_home_registry`; + `test_user_uninstall_post_condition_fails_when_the_registry_keeps_the_scope` (direct, via `apply`) |
| N6 watchlist layout | insert into array text, keep comments | N6 json.dumps whole array | `test_watchlist_insert_keeps_comments_and_layout` |
| N7 mode | chmod temp to original mode | N7a | `test_settings_edit_preserves_mode_bits` |
| N7 symlink | edit the resolved file, keep link | N7b | `test_settings_edit_keeps_a_symlinked_file_a_link` |
| N8 object/bare items | documented resolution | N8b drop objects | `test_the_live_dependency_shape_blocks_removal_even_when_disabled` (+2) |
| N8 declarer's marketplace | never "any" | N8a name-only | `test_dependency_names_resolve_in_the_declaring_marketplace` |
| N8 marketplace entry | read `<installLocation>/.claude-plugin/marketplace.json` | N8c | `test_dependency_names_resolve_in_the_declaring_marketplace` |
| N8 installed-but-disabled blocks | all installed dependents block; text says enabled/not | N8d only enabled block | `test_the_live_dependency_shape_blocks_removal_even_when_disabled`, `test_plan_blocks_missing_project_path_and_dependencies_and_data_collision` |
| N9 linear | single cursor pass | N9 old quadratic; N9b split-once | `test_parse_is_linear_for_a_large_grep_payload` (60k records < 3s; mutant 6.06s run); `test_grep_parse_tolerates_nul_in_text_and_rejects_truncation` |
| Row 1 reader half | (existing fix) now guarded | R1 install-path; R1 orphan scan | `test_claude_cache_comes_from_the_install_path_and_marketplace_half` (decoy `cache/alpha`) |
| Row 5 fixtures | every `example-plugin@example-plugin` / bare-name cache fixture replaced (`alpha@market`, `example-plugin@other-market`, `cache/other-market/...`); grep of the four files for `example-plugin@example-plugin` -> 0 (control: `alpha@market` -> 6 in one file) | n/a | fixture finding |
| Row 8 enabled key w/o install | `remove-settings-key` step | R8a | `test_plan_removes_an_enabled_key_that_has_no_install_record` |
| Row 8 codex plugin CLI doesn't list | `remove-codex-config-plugin` text edit | R8b | `test_plan_removes_a_codex_config_plugin_the_cli_does_not_list` (+ apply test `test_codex_config_plugin_table_is_removed_by_text_edit`) |
| Row 14 verification clause | name present AND list == existing + [name] | R14 | `test_watchlist_verification_rejects_an_edit_of_a_decoy_array` |
| Row 15 decode half | (existing) now guarded | R15 | `test_an_undecodable_registry_is_unreadable_not_a_crash` |
| Row 17 post-condition | re-parse; rollback if entries remain | R17a | `test_hook_trust_post_condition_catches_a_form_the_editor_leaves_behind` |
| Row 17 count==0 | now rc 1 when entries remain | R17b | `test_hook_trust_that_no_line_matches_is_a_failure_not_success` |
| Row 17 `[hooks]`+`state."k"` | full key path = header + dotted key | R17c | `test_hook_trust_handles_inline_and_subtable_forms` (hooks-table-dotted) |
| Row 18 recorded set | delete only `_BackupRecord.sources` | R18 recompute | `test_removal_deletes_only_the_backed_up_set` (+1) |
| Row 20 atomic write | temp + fsync + replace | R20 plain `write_bytes` | `test_a_crash_before_the_new_bytes_are_durable_leaves_the_original` |
| §5 e2e | scratch-home `--apply`, realistic 2-plugin marketplace | — | `test_end_to_end_apply_removes_one_plugin_and_leaves_its_sibling_identical` (sibling cache, data, registry entry byte-identical) and `..._removes_the_last_plugin_and_its_marketplace` |

## §5 commands — real exit codes (logs in `.agent/logs/plugin-remove-r3/`, rc appended by `echo "rc=$?"`)

| # | Command | rc | Result |
|---|---|---|---|
| 1 | `uv run --project python pytest tests/test_plugin_state.py tests/test_plugin_inventory.py tests/test_plugin_remove.py tests/test_removed_plugins.py tests/test_doctor.py -q` | 0 | 212 passed |
| 2 | `uv run --project python pytest tests/ -q` | 0 | 3874 passed, 11 deselected (4m51s) |
| 3 | `uv run --project python dotfiles-setup verify run` | 0 | 165 passed, 0 failed, 4 skipped (the 4 human-only `policy.*`); `workflow.plugin-removal-wiring` PASSED |
| 4 | `mise run lint` | 0 | all steps green incl. ruff, ruff_format, py_ty, no_lint_skip, bash_logic_budget, contract_token_uniqueness |
| 5 | `dotfiles-setup plugin-remove 'honcho@'` | 2 | argparse error naming the selector rule (expected 2) |
| 6 | `dotfiles-setup plugin-remove exa@exa --json` | 1 | one blocker: `installed plugin depends on target: aggregated-research@ray-manaloto (installed but enabled nowhere; re-enabling it would break)`; 9 planned steps incl. `remove-claude-marketplace` with context [dotfiles, knowledge-base] (expected 1) |
| 7 | `dotfiles-setup plugin-remove honcho@honcho --json` | 0 | 0 blockers; note `marketplace kept: still used by honcho-dev@honcho`; targets `cache/honcho/honcho`, `data/honcho-honcho` only (expected 0) |
| 8 | `dotfiles-setup plugin-inventory ponytail@ponytail` | 0 | locations 0, worktree_settings 10, stale_worktrees 3, errors 0 (expected 0) |
| 9 | `mise run doctor` | 0 | no removed-plugins finding; 5 UNRELATED host drifts reported (listing-budget antigravity agent 1789>1536, path-drift BLIND, graphify path-binary 0.9.68 != locked 0.9.65, claude-doctor BLIND, codex-schema 0.154.0 vs 0.157.0) — none touch this diff, left for the caller |

No command above passed `--apply`; no dry run created `.agent/state/plugin-remove/` (checked: absent).

## Deviations and open items (need caller ratification)

- **D1 (N9 method).** The spec says "split on NUL once"; live data refutes its premise (NUL inside
  matched text, `fanvanzh/3dtiles` `.pgm`). Implemented a single-pass cursor scan instead; linear time
  is kept, and mutation N9b (split-once) goes red on `test_grep_parse_tolerates_nul_in_text...`.
- **D2 (N2 user scope).** `--scope user` runs when `~/.claude/settings.json` declares the marketplace,
  OR when `known_marketplaces.json` still lists it after the project/local calls (the docs say
  marketplace state is stored once per user there). What the real CLI does for `--scope user` when
  the marketplace is only in `known_marketplaces.json` is UNVERIFIED (measuring it needs a live
  mutation, which is prohibited). If it refuses, the step fails with the CLI's rc and nothing
  harness-owned is restored. Live `exa`: declared only in dotfiles + knowledge-base project settings.
- **D3 (class split applied everywhere).** Besides the marketplace step, `installed_plugins.json`
  (uninstall) and `~/.codex/config.toml` (codex native remove) are no longer restored after a CLI
  call either. They are backed up only. Our OWN text edits of `config.toml` (hook trust, stray
  plugin) still roll back from memory, because no CLI touched the file.
- **D4 (N4 trade-off).** A bare watched name now finds a data dir only for marketplaces still named
  in harness records (registry keys, `known_marketplaces.json`, claude/codex cache dirs). An orphaned
  data dir whose marketplace appears in none of them is no longer reported by the doctor.
- **D5 (interfaces).** Keyword-only additions: `plan(..., home=None)`,
  `uninstall_project_scope(..., home=None, repo_root=None)`, `repo_root=None` on
  `remove_local_override` / `remove_claude_marketplace` / `remove_codex_plugin` /
  `remove_codex_marketplace` / `remove_codex_hook_trust`, `add_to_watchlist(..., backup_root=None)`.
  New `remove_settings_key`, `remove_codex_config_plugin`, `PluginInventory.enabled_dependents` /
  `.enabling_settings`, `plugin_state.parse_selector` / `.data_id`. Without `repo_root`, backups go
  to `Path.cwd()/.agent/state/plugin-remove/`. The `workflow.plugin-removal-wiring` token lines were
  kept byte-identical (`plan(inv, repo_root=repo_root)` relies on `home` defaulting to `Path.home()`).
- **D6 (hook-trust editor limit).** A hook key containing `#` or `=` is not resolved by the line
  editor. It fails closed (the post-condition rolls back with rc 1), and a test pins that behavior.
  It does not report success.
- **Incident (read-only).** Before the autouse HOME/cwd fixture existed, one run of the OLD tests
  against the new defaults READ the real `~/.claude/plugins/installed_plugins.json` and copied it into
  gitignored `.agent/state/plugin-remove/` backups. Those copies were deleted. No real file was
  written, because the subprocess was faked and the settings paths were `tmp_path`.
- Not in scope: row 22 (#1370, `.agents` mirror wording); the skills' prose was not touched (spec §2).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the implementation, tests, gates and live dry runs
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline Claude Code docs (`plugin-marketplaces.md`, `plugin-dependencies.md`, `plugins-reference.md`) and its `.claude/settings*.json` keys (read-only)
- [ray-manaloto/macos-development-environment](https://github.com/ray-manaloto/macos-development-environment) — its `.claude/settings*.json` keys, read-only via the honcho dry run
- fanvanzh/3dtiles (local clone under `~/dev/github`) — the `git grep -z` output with NUL inside matched text that refuted "split on NUL once" (read-only)
