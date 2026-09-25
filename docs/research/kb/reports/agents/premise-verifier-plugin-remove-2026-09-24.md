Read-only lane: I had no write tools, so nothing was persisted. Please save this report verbatim. I also couldn't run the graphify mandate (no Bash), so every fact below comes from reading files directly.

```
PREMISE REPORT
ROWS: 13 checked — 5 CONFIRMED (0 provenance corrected) / 0 REFUTED / 7 UNVERIFIABLE / 1 ASSUMED (1 checkable)
```

| Row | Verdict | Evidence |
|---|---|---|
| P1 | UNVERIFIABLE | I can't run git, and the blob isn't on disk. Grepping for `_Unreadable\|find_reappearances` finds only the spec, an unrelated `_UnreadableSourceError` (`rule_registry.py:272`) and one report. |
| P2 | UNVERIFIABLE (historical) / CONFIRMED (current) | Current `doctor.py`: `settings` is at **243** (not 244), `local_settings` 244, `user_settings` 250, `home: Path \| None` 253. CHECKS is at 1327-1341. |
| P3 | CONFIRMED | `plugin_health.py:39` `PLUGIN_LIST_TIMEOUT = 10`; `subprocess.run(..., timeout=timeout)` at 141-148. |
| P4 | CONFIRMED | `main.py:1710-1720` and `2876-2878`. Both are no-argv precedents; see MISSING. |
| P5 | CONFIRMED | `mise.toml:1676-1678`. |
| P6 | UNVERIFIABLE | A measurement. The docs back the shape: `--json` prints one object on the **last line only** (`$CC/plugins-reference.md:1021-1027`), and it can't be combined with `--prune` (1066). |
| P7 | UNVERIFIABLE | I couldn't run `--help`. Docs show `codex plugin remove --json` (`codex/cli__reference.md:239`) and a `marketplace` subcommand (242-246). The exact argv sits in an unrendered ConfigTable. |
| P8 | UNVERIFIABLE | Session measurement. |
| P9 | UNVERIFIABLE | Glob doesn't list sockets. A glob over `~/.codex/{ipc,app-server-daemon}` timed out. The daemon dir listed only pid/lock/log files. |
| P10 | CONFIRMED | 10 files contain `"ponytail@ponytail": true`. dotfiles has 5: `dotfiles.worktrees/agentsview-{managed,native}-service`, `.claude/worktrees/agent-a6e…` and `agent-a82…`, and `~/.codex/worktrees/3f4c/dotfiles`. KB has 5 under `knowledge-base.worktrees/`. |
| P11 | UNVERIFIABLE | Session measurement. |
| P12 | CONFIRMED | `pyproject.toml:123-139` bans; TID251 at 94-97 and 106. |
| P13 | ASSUMED (checkable) | Should be a cited row. `.git/worktrees/*/gitdir` shows worktrees outside any tree walk: `~/.codex/worktrees`, `/private/tmp/...scratchpad`. |

MISSING:
- **The §5 fable grep can't fail for new files.** `git diff --name-only origin/main` leaves out untracked files, and every created file stays untracked because the commit is the caller's. The runbook path (`…/fable-orchestrator-removal-session-2026-09-24.md`) contains the banned string, so a skill that cites it breaks Ray's ruling. Fix both: add `git ls-files -o --exclude-standard` to the grep, and tell the skill not to cite that path.
- **3 KB worktrees are prunable.** Their gitdirs point at missing `/private/tmp/...scratchpad/wt-{lychee,dag-gate,round-close}`. Under the "probe that can't answer = error" rule they would force rc 2, which contradicts §5's "rc 0". The spec has to say whether a missing worktree is skipped or treated as an error.
- **CLI argv.** `main()` uses strict `parse_args` (`main.py:3085`), and the passthrough only applies to plan-attest (`plan_attest.py:104`). The subparsers must declare the positional arg plus `--apply` and `--json`, then rebuild argv. Precedent: `instructions-report` (`main.py:2929-2937`).
- **codec.** `codec.encode` handles dataclasses and `Path` (`codec.py:212,345`). `plugin_health` uses stdlib `json` only to PARSE external payloads (180-193) and outputs through `codec.encode` (378-403). "Stdlib json as plugin_health does" misdescribes that precedent.
- **`codex plugin list --json`** already gives an `installed` array with `pluginId` (`cli__reference.md:235-238`). Exact-selector matching can use that structure instead of parsing text rows.
- **Hook-trust keys.** `~/.codex/config.toml` has 47 `[hooks.state.` headers (counted only, no values read). 22 are `"name@mkt:`-shaped and 25 are keyed by absolute path; none mention ponytail. The spec only covers the first shape.
- **Settings loading.** `collect` loads project, user and `settings.local.json` (`doctor.py:423-431`), and `home` may be `None`, so the restored check has to skip in that case.
- **Other checks that hold:** `.agent/state/` is gitignored (`.gitignore:41,124`). `doctor.toml` has no `[removed_plugins]` block today, and sections are read ad hoc with `_str_keys(baseline.get(...))` (`doctor.py:255-265`). The current `CHECKS` count is 13 (`tests/test_doctor.py:1197`).
- **Undefined `root` for `discover_repos`.** It isn't specified. Nested worktrees under `.claude/worktrees/` would be counted twice unless worktree-list results are deduplicated.

```
VERDICT: correct the spec first — §5's fable grep cannot see untracked created files, and the prunable-worktree policy decides whether the "rc 0" expectation can hold.
```

Non-blocking residuals:
- **P1/P2 historical:** running the restore's `git show` settles them.
- **P6-P9, P11:** the docs corroborate them, and the §5 real runs re-measure them.
- **P13:** the on-disk gitdirs support it.

---

## Revision 2 (changed rows)

No row is refuted. One new item needs fixing before dispatch: the codex match key.

**PREMISE REPORT (revision 2, changed rows only)**
ROWS: 4 checked. 3 CONFIRMED (2 of them provenance corrected), 0 REFUTED, 1 UNVERIFIABLE, 0 ASSUMED.

| Row | Verdict | Evidence |
|---|---|---|
| P2 | CONFIRMED (current part); UNVERIFIABLE (1c4977eb part) | `doctor.py:243,244,250,253` and `collect` at 423-431 all match. |
| P13 | CONFIRMED (provenance corrected) | Kind should be L/A, not P, and the "premise-verifier" source should come out. Checked in `.git/worktrees/*/gitdir`: 5 dotfiles and 9 KB worktrees. The 3 KB ones live under `/private/tmp/claude-501/-Users-…-knowledge-base/`, which doesn't exist, so the "3 stale" claim holds. |
| P14 | UNVERIFIABLE (context) | `codex/cli__reference.md:234-240` says what the row claims. But the docs aren't tied to host codex 0.156.x, and they never say what `pluginId` looks like. |
| P15 | CONFIRMED (provenance corrected) | Recounted the table headers in `~/.codex/config.toml` (headers only, no values read): 22 are `"name@mkt:`-shaped and 25 are absolute paths. |

**The fixes you made:**
- **Fable-string scope and skill citation (§1:27-32):** fine. Stale leftover: §4:185 still says "any created/modified file", which contradicts the exemption for specs and reports.
- **`discover_repos`:** `~/dev/github/<owner>/<repo>` at depth 2 finds dotfiles and KB. The `dotfiles.worktrees/*`, `.claude/worktrees/*` and `~/.codex/worktrees/3f4c` copies are only reachable through the worktree list, so dedupe by realpath is needed and specified.
  - I grepped every depth-2 repo's `.claude/settings*.json` for `ponytail@` and got 0 hits. The control grep for `enabledPlugins` over the same files got 9 hits, so the probe works.
- **`stale_worktrees`:** consistent with §5's "10 worktree_settings, 3 stale".
- **argv precedent:** `main.py:3085` and `2929-2937` match.
- **codec output:** `codec.py:212,345` and `plugin_health.py:180-193,378-403` match.
- **`home` is None:** §4:178 depends on 1c4977eb, so I can't verify it.
- **§5 grep:** now includes untracked files. It still has no control arm; running it once on a scratch file that contains the string would prove it can fail.

MISSING:
- **`pluginId` format is unknown.** The docs list `pluginId`, `name` and `marketplaceName` as separate fields but never say `pluginId == "name@mkt"`. The only support is indirect: the 81 `[plugins."name@mkt"]` tables in `config.toml`.
  - If the assumption is wrong, `codex_cli_rows` always reports "absent". Neither check would catch it: the unit tests use faked output built on the same assumption, and the §5 real run only looks at ponytail, which isn't installed in codex.
  - Fix: match on `name` and `marketplaceName` together, or add a live positive check against a plugin that is installed in codex.
- **Path-keyed hook-trust tables:** all 25 are `/Users/…/.codex/hooks…` project-hook paths, and 0 sit under `plugins/cache`. The cache layout itself is `~/.codex/plugins/cache/<mkt>/<name>/<ver>/` (confirmed). So the new path-keyed deletion never matches anything in current data. That's harmless because it only deletes under the cache dir, but its unit test must build its own fixture.

VERDICT: **correct the spec first.** Pin `codex_cli_rows` to (`name`, `marketplaceName`) or add a live positive check, because as written a wrong `pluginId` guess passes every check and hides every codex install.

Non-blocking leftovers:
- the historical parts of P1/P2 and §4:178 get settled when the restore runs `git show`;
- the wording at §4:185;
- the §5 grep's missing control arm;
- the P14 doc version, which the §5 real run measures.

---

## r2 addendum premise report

PREMISE REPORT (read-only lane: nothing was written, so please persist this verbatim)

ROWS: 8 checked — 6 CONFIRMED (0 provenance corrected) / 1 REFUTED / 0 UNVERIFIABLE / 1 ASSUMED (0 checkable)

Scope: my tools were Read/Grep/Glob only, so no CLI runs (`--help`, dry runs) and no `graphify-query`. I read `installed_plugins.json` with key and scope-enum greps only, never values.

- **R1 — REFUTED (narrow).** The entry key list is incomplete. Top level is `{version: 2, plugins}` and the scope counts are exact (213/53/2, total 268, over 214 keys). But an unlisted entry key `auto` sits on 4 user-scope entries (`installed_plugins.json:1232,2579,2608,2750`). `gitCommitSha` is optional: present in 255 of 268 entries.
- **R2 — CONFIRMED.** All 268 `installPath` values match `.../plugins/cache/<a>/<b>/<c>`, and `plugins-reference.md:800` documents the layout. Grep can't check that each segment equals the key's own halves (no backreferences).
- **R3 — CONFIRMED (docs).** `plugins-reference.md:744`: `data/{id}/` where `{id}` is the plugin id with every character outside `[a-zA-Z0-9_-]` replaced by `-`. I couldn't see the named directory on disk (Glob found no files in it).
- **R4 — CONFIRMED.** On disk: `cache/exa/exa/3.4.1` and `cache/claude-plugins-official/exa/3.4.1`.
- **R5 — CONFIRMED (code path + disk).** `cache/honcho/` holds `honcho/0.3.2` and `honcho-dev/0.2.4`. `honcho` is a key in `known_marketplaces.json`. `plugin_remove.py:109-150` triggers on the marketplace-level directory. I did not re-run the dry run.
- **R6 — CONFIRMED.** `plugin_state.py:111` `present = (cache / name).exists()`.
- **R7 — CONFIRMED against docs.** `plugins-reference.md:1060-1066` lists `--scope user|project|local` and `--keep-data`. `--json` can't be combined with `--prune`. Data is deleted only on uninstall from the last scope (`:1071`).
- **R8 — ASSUMED, load-bearing.** `changelog.md:4754` says `/plugin uninstall` "disable[s] project-scoped plugins in `.claude/settings.local.json` instead of modifying `.claude/settings.json`". That is an *added* `false` override, not a deleted line.
  - `_remove_enabled_line` (`plugin_remove.py:339`) can only delete a line.
  - The doctor reads each settings file separately (`doctor.py:1345-1349`) and flags `on is True` (`plugin_state.py:92`), so a surviving `true` in `settings.json` would count as a reappearance.

MISSING:
1. **Marketplace field in `claude plugin list --json`.** The docs promise a "source marketplace" (`plugins-reference.md:1173,1183`) but name no JSON field. Codex documents `marketplaceName` (`codex/cli__reference.md:234-240`). The architect must measure the Claude field or drop that source; `installed_plugins.json` is the only source known to cover every project.
2. **Marketplace remove cascades.** Without `--scope` it removes the declaration from every editable scope, and removal from the last scope "also uninstalls any plugins you installed from it" (`plugin-marketplaces.md:1320-1323`). It also edits `extraKnownMarketplaces` in project settings, which no minimal-diff step covers.
3. **Local scope records `projectPath`.** Both local entries have `projectPath` right after `scope` (control: the same pattern for user scope gives 0). There is no rule for a `projectPath` directory that no longer exists as a CLI working directory; add one (blocker or skip).
4. **Data dirs can be shared.** The `{id}` mapping is lossy: `a-b@c` and `a@b-c` both map to `a-b-c`, and dots also become `-`. The spec should derive the name with the documented rule and treat a collision as a blocker.
5. **Dependencies (`auto` entries).** Disabling is refused while an enabled plugin depends on it (`plugin-dependencies.md:177,190`), and auto-installed dependencies outlive their parent (`:203`). The plan and tests don't cover either.
6. **Harness cache sweep and symlinked entries.** The harness marks uninstalled version directories orphaned and sweeps them about 14 days later (`plugins-reference.md:802-804`). Link-mode cache entries are symlinks (`:798`), so a tar backup captures the link, not the content.
7. **One key, many entries.** 214 keys carry 268 entries, so the plan must iterate entries, not keys.

VERDICT: correct the spec first. R8's disable-override semantics make the "minimal-line restore" as written unable to handle an added `false` override, and leave the doctor flagging the kept `true` in `settings.json`. MISSING 1 (unknown Claude list field) and 4 (data-dir collision) leave the sibling guard and data backup underspecified. R1 needs a one-line fix (`auto`, optional `gitCommitSha`).

Files read:
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/specs/plugin-remove-pipeline-r2.md`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/plugin_state.py`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/plugin_remove.py`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/doctor.py`
- `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/{plugins-reference,plugin-marketplaces,plugin-dependencies,changelog}.md`
- `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/codex/cli__reference.md`

---

## r3 addendum premise report

**Read-only lane.** I have no write tools, so none of this is persisted. Please save it verbatim to `docs/research/kb/reports/agents/`.

```
PREMISE REPORT
ROWS: 6 checked — 5 CONFIRMED (1 provenance corrected) / 1 REFUTED / 0 UNVERIFIABLE / 0 ASSUMED
T1 — CONFIRMED — plugin_inventory.py:616 `if "@" not in plugin:`; plugin_state.py:53,58 split/partition with no further validation.
T2 — CONFIRMED — plugin.json:7-12, an array of 4 `{name, marketplace}` objects. It is pretty-printed, not compact, but the keys and structure are the same.
T3 — CONFIRMED — dry-exa@exa.json `"blockers":[]`, .rc `rc=0`. The plan includes remove-claude-marketplace.
T4 — CONFIRMED (provenance corrected) — the row's source is the reviewer report. I read the code myself: plugin_remove.py:510 regex `[^,\n]+` matches only the opener line `"exa": {`. The result is invalid JSON, so :603 errors and :923 restores snapshots after a CLI call that succeeded. Live known_marketplaces.json:2-10 entries are 9-line nested objects.
T5 — REFUTED — plugin-dependencies.md:44: `name` "Resolves within the same marketplace as the declaring plugin". An item with no marketplace field does NOT match every marketplace, so N8's "(if marketplace is present)" rule matches too much. :35 also shows a legal `{name, version}` object with no marketplace field.
T6 — CONFIRMED — .gitignore:41 `.agent/state/`, :124 `.agent/`.
MISSING:
- "Enabled" is undefined, and §5 contradicts N8 on the live machine. aggregated-research@ray-manaloto is set to false in ~/.claude/settings.json:37 and KB settings.local.json:19, and true in KB settings.json:213. Local overrides project, so it is disabled everywhere, and the §5 `exa@exa` expectation of rc=1 cannot hold under N8's "installed, enabled" rule. The architect must define which scope counts as enabled, or drop "enabled".
- Dependencies can also be declared in the marketplace entry (plugin-dependencies.md:9), not only in plugin.json. N8 reads only the manifest.
- The native CLI edits files N2 treats as repo/user settings. plugin-marketplaces.md:1320 says that without `--scope`, "the declaration is removed from every editable scope". plugin_remove.py:910 passes no `--scope` and no `cwd`, so the CLI edits the process cwd's tracked `.claude/settings.json` (and local) itself. It does not edit the knowledge-base project's settings. I could not check (it needs a run) whether the CLI rewrites the whole file with its own formatting. The architect must choose between scoped CLI calls per scope and project cwd, or accepting the CLI's rewrite. Separately, removing a marketplace from its last scope uninstalls its plugins (:1322-1324).
- The N2 test fixture uses the wrong shape. Settings `extraKnownMarketplaces` entries contain only `{"source":{…}}` (.claude/settings.json:204-216). `installLocation`/`lastUpdated` is the harness-owned known_marketplaces shape.
- The data directory id can collide between plugins. plugins-reference:744 maps `@` and `.` to `-`, so `foo@bar-baz` and `foo-bar@baz` both become `foo-bar-baz`. The N1 selector regex allows `.`. N4's "exact id" check can therefore delete another plugin's data. The architect should add a collision check against the other installed selectors.
- Realpath check vs link mode:
  - Deletion stays safe. The code (838-850) unlinks a symlinked source and runs rmtree on a real directory. rmtree unlinks inner links without following them, so link-mode entries (plugin-marketplaces.md:634) and symlinked dev-checkout versions (plugins-reference:804) are unlinked, not traversed.
  - A containment check only on the top-level path is sound, including against a symlinked `cache/<m>` parent directory. It must run at delete time: sources are captured at :396 and deleted at :884 (a time-of-check/time-of-use gap).
  - A realpath check applied to every entry would wrongly block every link-mode plugin.
  - The backup sets `archive.dereference = True` (:404), which follows those links and archives external directories of unbounded size.
  - Unverified: whether `shutil.rmtree.avoids_symlink_attacks` is True on this macOS Python.
VERDICT: correct the spec first — T5's matching rule is refuted; "enabled" is undefined and §5's live expectation contradicts it; the native CLI's edits to every settings scope are unstated in N2.
```

Relevant paths:
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/plugin_remove.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/plugin_inventory.py
- /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/plugin-dependencies.md
- /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/plugin-marketplaces.md