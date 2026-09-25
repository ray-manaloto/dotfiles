# Spec addendum r3: plugin-removal pipeline — correction round 2 (Ray-approved extra round)

Base: `docs/specs/plugin-remove-pipeline.md` + `…-r2.md` (authoritative where not
overridden). Code under correction: `48732d05`. Review:
`docs/research/kb/reports/agents/cold-reviewer-plugin-remove-r2-2026-09-24.md`
(22 round-1 dispositions: 13 FIXED / 8 PARTIAL / 1 NOT FIXED→#1370; 9 NEW:
N1-N9). Ray ruled 2026-09-25: one more respec round rather than shipping with
`--apply` gated. Implementer `codex-sol-implementer`, `xhigh`, COMMIT caller.

## 1. Objective

Close N1-N9 and the 8 PARTIALs so `plugin-remove --apply` is safe on the real
registry, each closure proven by a test that FAILS when the fix is reverted.

## 2. Files

`plugin_state.py`, `plugin_inventory.py`, `plugin_remove.py`, their four test
files, `tests/TEST-INDEX.md`, `.gitignore` only if needed for N3 (prefer an
already-ignored dir). No new modules.

## 3. Interfaces (changes)

- `parse_selector(sel: str) -> tuple[str, str]` in `plugin_state`: raises
  `ValueError` unless the selector is exactly `<plugin>@<marketplace>` with BOTH
  halves non-empty and matching `^[A-Za-z0-9][A-Za-z0-9._-]*$`. Every entry point
  (`inventory`, `plan`, `*_main`) calls it first; `*_main` exits 2 with the message.
- `plugin_remove_main` unchanged otherwise (dry run exits 1 on blockers).

## 4. Constraints — the fixes

**N1 (HIGH) selector validation**: `honcho@`, `@honcho`, `a@b@c`, `../x@y`,
`x@y/z` are all rejected before any path is built. Additionally every path the
plan will delete must resolve (`os.path.realpath`) INSIDE
`~/.claude/plugins/cache/<marketplace>/<plugin>` / `~/.codex/plugins/cache/<marketplace>/<plugin>`
/ `~/.claude/plugins/data/<id>` — assert it, and make an escape a blocker.

**N2 (HIGH) marketplace removal on the real registry**: split files into two
classes. (a) HARNESS-OWNED files under `~/.claude/plugins/` and `~/.codex/`
(`installed_plugins.json`, `known_marketplaces.json`, codex state): the native CLI
is authoritative — never minimal-diff or restore them after a successful CLI
call; verify the goal state by re-reading. (b) REPO/USER settings files
(`<project>/.claude/settings*.json`, `~/.claude/settings.json`): the native
`claude plugin marketplace remove <m>` WITHOUT `--scope` edits every editable scope
of the process cwd (`--help`: "Omit to remove it from every scope";
`$CC/plugin-marketplaces.md:1320`). So call it PER DECLARED SCOPE —
`--scope user` (cwd = repo_root), and `--scope project` / `--scope local` with
`cwd=<that project>` for every project whose settings declare the marketplace —
snapshotting each file first. Then apply the goal-state rule to each file the CLI
touched: restore the ORIGINAL text minus the key's WHOLE multi-line object span
(brace-matched on the original text, string-aware) and assert json-equivalence
with the CLI's result. Removing a marketplace from its last scope uninstalls its
plugins (`:1322-1324`) — the sibling guard already prevents that. Fixture shapes
must match reality: settings `extraKnownMarketplaces` entries are
`{"source": {"source": "github", "repo": "o/r"}}` (`.claude/settings.json:204-216`);
the harness-owned `known_marketplaces.json` entries add `installLocation` and
`lastUpdated`. The success-path test uses both, multi-line.

**N8 (HIGH) dependency format** (`$CC/plugin-dependencies.md:9,40-46`):
dependencies are declared in a plugin's `plugin.json` OR in its marketplace
entry (`<marketplace installLocation>/.claude-plugin/marketplace.json`); read both.
Each item is a bare name string or an object `{name, version?, marketplace?}`.
The item's marketplace is `marketplace` if present, ELSE THE DECLARING PLUGIN'S
OWN MARKETPLACE (never "any"). `version` is ignored for matching. An item matches
the target when `(name, resolved marketplace) == (target plugin, target
marketplace)`. A match by any OTHER plugin that is INSTALLED in any scope
(present in `installed_plugins.json`, regardless of its enabled state) is a
blocker; the blocker text names the dependent and whether it is enabled
anywhere. (Measured: `aggregated-research@ray-manaloto` is installed but disabled
by user and local overrides — it still blocks, because re-enabling it would break.) Test with
that exact live shape plus a bare-string item; the live dry run of `exa@exa`
must report the blocker.

**N3 backups location**: all backups go under `<repo_root>/.agent/state/plugin-remove/<UTC stamp>/`
(gitignored), mirroring the source path; never beside the edited file.

**N4 data id**: exact documented id only (`$CC/plugins-reference.md:744`), no
prefix/hyphen matching; because the mapping is lossy (`foo@bar-baz` and
`foo-bar@baz` → `foo-bar-baz`), a collision with any other installed selector is a
BLOCKER for the data step.

**Symlinks / containment**: the containment check applies to the TOP-LEVEL
removal path only (a per-entry realpath check would block every link-mode plugin)
and is re-run immediately before each delete (TOCTOU). Deletion uses
`shutil.rmtree` (measured `avoids_symlink_attacks = True` on the repo Python) and
unlinks a symlinked top-level source instead of traversing it. The backup must NOT
dereference links (`dereference=False`): archive the link itself and record its
target in the manifest — a link target is an external checkout that is never
deleted, so its content needs no backup.

**N5**: the post-uninstall registry check reads the REAL home's
`installed_plugins.json`; test it directly (not only through the wrapper).

**N6 watchlist**: insert the name into the existing `names` array text, keeping
its comments and layout; re-parse to verify.

**N7 file mode/symlinks**: preserve the original mode bits on atomic replace; if
the target is a symlink, edit the resolved file and keep the link.

**N9 parser**: `git grep -z` output parsed in linear time (split on NUL once).

**PARTIALs** (review table rows 1, 5, 8, 14, 15, 17, 18, 20): add the missing
revert-sensitive tests; replace every remaining `example-plugin@example-plugin`
/ bare-name cache fixture with plugin≠marketplace fixtures (row 5); an
`enabledPlugins` key with no install record, or a codex config plugin the CLI does
not list, yields a real removal step (settings goal-state / codex config edit) or
a blocker — never a plan of only `add-to-watchlist` (row 8); the `[hooks]` +
`state."k" = {…}` inline form is removed or the step fails (row 17).

**Process prohibitions** (the Claude guard cannot see a codex lane): do not use
the planning-with-files skill; do not create or modify anything under `.planning/`
or any `task_plan.md`/`findings.md`/`progress.md`; never `--apply` against the real
machine; do not commit; do not touch staged `docs/`.

## 5. Verification

```bash
uv run --project python pytest tests/test_plugin_state.py tests/test_plugin_inventory.py tests/test_plugin_remove.py tests/test_removed_plugins.py tests/test_doctor.py -q
uv run --project python pytest tests/ -q
uv run --project python dotfiles-setup verify run
mise run lint
uv run --project python dotfiles-setup plugin-remove 'honcho@' ; echo "expect rc=2 (rejected)"
uv run --project python dotfiles-setup plugin-remove exa@exa --json ; echo "expect rc=1, blocker naming aggregated-research@ray-manaloto"
uv run --project python dotfiles-setup plugin-remove honcho@honcho --json ; echo "expect rc=0, marketplace kept (honcho-dev)"
uv run --project python dotfiles-setup plugin-inventory ponytail@ponytail ; echo "expect rc=0, 0 locations"
mise run doctor
```
Plus: a scratch-home end-to-end `--apply` test of a realistic multi-plugin
marketplace (fixtures only) that asserts the sibling plugin's cache, data and
registry entries survive byte-identical.

## 6. Commit — `caller`.

## 7. PREMISES

| # | Kind | Claim | Source |
|---|---|---|---|
| T1 | L | inventory selector check is only `"@" in plugin` | `plugin_inventory.py:614-617` @48732d05 |
| T2 | L | `aggregated-research` manifest `dependencies` = `[{"name":"firecrawl","marketplace":"firecrawl"},{"name":"exa","marketplace":"exa"},{"name":"context7","marketplace":"context7-marketplace"},{"name":"last30days","marketplace":"last30days-skill"}]` | `~/.claude/plugins/cache/ray-manaloto/aggregated-research/6b5b092efa6b/.claude-plugin/plugin.json`, read 2026-09-25 |
| T3 | L | `exa@exa` dry run at 48732d05 reports 0 blockers | `.agent/logs/plugin-remove-r2-mine/dry-exa@exa.json` |
| T4 | L | N2: live marketplace entries are multi-line objects; key-line remover handles single-line only | reviewer r2 report N2 (`plugin_remove.py:507-534,583-605,901-927`) |
| T5 | I | dependency items: bare name or `{name, version?, marketplace?}`; `name` resolves in the DECLARING plugin's marketplace unless `marketplace` is given; deps may be declared in plugin.json or the marketplace entry | `$CC/plugin-dependencies.md:9,40-46` (premise-verifier r3 refuted the earlier wording) |
| T7 | I | `claude plugin marketplace remove <name> [--scope user\|project\|local]`; omitting --scope removes from every scope | `claude plugin marketplace remove --help`, 2.1.281, 2026-09-25 |
| T8 | L | `shutil.rmtree.avoids_symlink_attacks` is True on the repo's Python | measured 2026-09-25 |
| T6 | L | `.agent/state/` is gitignored | `.gitignore:41,124` (premise-verifier r1) |
