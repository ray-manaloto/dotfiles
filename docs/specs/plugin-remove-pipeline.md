# Spec: plugin-removal pipeline (skill → task → python) + restored removed-plugins watch

Status: ratified by Ray 2026-09-24 (session dotfiles-20260924.000). Implementer:
`codex-sol-implementer`, effort `xhigh`. COMMIT: caller.

## 1. Objective

Removing a Claude Code / codex plugin must follow ONE reusable, checked procedure
instead of being improvised. The fable-orchestrator removal (2026-09-22/24) left a
complete runbook only as prose
(`docs/research/kb/reports/agents/fable-orchestrator-removal-session-2026-09-24.md`
§ "Step 0" and § "User-global and codex scope"). Two days later the ponytail
removal ignored it and missed: the live-reference/count audit (two cold-review
rounds each caught a stale plugin count), the cache backup, the native
`codex plugin list`, the git-worktree check, and a guard against reappearance
(the `removed-plugins` doctor check had just been deleted in #1368).

Deliver, per Ray's protocol (wrapper skill → smaller modular skills → mise tasks
→ python library functions; **no scripts**, no bash logic):

1. A python library that INVENTORIES every place a plugin lives and REMOVES it
   through native CLIs, dry-run by default.
2. Thin CLI subcommands and mise tasks over it.
3. Skills: one small read-only skill and one wrapper skill that composes it with
   the existing `plugin-health` skill.
4. The `removed-plugins` doctor check restored (it was deleted in #1368), watching
   `["ponytail", "claudex-loop"]`. **The string `fable-orchestrator` must not
   appear in any code, config, test, skill, agent or rule file this change
   creates or modifies** (Ray's ruling, #1368). Specs and reports are historical
   docs and exempt — but a skill must NOT cite the fable runbook's path (its
   filename contains the string); describe it as "the 2026-09-24 plugin-removal
   session report" and cite this spec instead.

## 2. Files

Create:
- `python/src/dotfiles_setup/plugin_state.py` — readers (where a plugin lives).
- `python/src/dotfiles_setup/plugin_inventory.py` — inventory = state + native CLI
  listings + worktrees + live repo references.
- `python/src/dotfiles_setup/plugin_remove.py` — plan + apply steps + wrapper.
- `python/src/dotfiles_setup/removed_plugins.py` — RESTORED from
  `git show 1c4977eb:python/src/dotfiles_setup/removed_plugins.py`, then refactored
  to delegate its readers to `plugin_state` (keep `find_reappearances` signature).
- `tests/test_plugin_state.py`, `tests/test_plugin_inventory.py`,
  `tests/test_plugin_remove.py`, `tests/test_removed_plugins.py` (restore from
  `1c4977eb`, replace every `fable-orchestrator` fixture with `example-plugin`).
- `.claude/skills/plugin-inventory/SKILL.md` (small, read-only).
- `.claude/skills/plugin-removal/SKILL.md` (wrapper).

Modify:
- `python/src/dotfiles_setup/doctor.py` — restore `check_removed_plugins`,
  `_REMOVED_PLUGINS_UNWATCHED`, the `removed_plugins` import and the
  `("removed-plugins", check_removed_plugins)` CHECKS row exactly as at `1c4977eb`
  (see `git show 1c4977eb:python/src/dotfiles_setup/doctor.py`), fable-free.
- `doctor.toml` — restore a `[removed_plugins]` block (comment fable-free),
  `names = ["ponytail", "claudex-loop"]`.
- `tests/test_doctor.py` — `len(doctor.CHECKS) == 14` plus its comment line.
- `tests/TEST-INDEX.md` — rows for the four test files.
- `python/src/dotfiles_setup/main.py` — subcommands `plugin-inventory` and
  `plugin-remove` next to `_add_plugin_health_subcommands` (main.py:1710) and the
  dispatch table (main.py:2876).
- `mise.toml` — tasks `plugin-inventory` and `plugin-remove` next to
  `[tasks.plugin-health]` (mise.toml:1676), same `uv run --project python
  dotfiles-setup …` shape.
- `.claude/skills/plugin-health/SKILL.md` — one "See also" line to `plugin-removal`.
- `.agents/skills/**` — regenerate with `uv run --project python dotfiles-setup
  skills-mirror` (never hand-edit).
- `python/verification/suites.toml` — one `require_tokens` contract
  `workflow.plugin-removal-wiring` binding skill → task → CLI → module (choose
  tokens with `mise run token-check`; each must bind exactly one site).

## 3. Interfaces

```python
# plugin_state.py — pure readers, no mutation, report KEYS never values
@dataclass(frozen=True)
class PluginLocation:
    harness: Literal["claude", "codex"]
    kind: Literal["enabled", "declared-marketplace", "installed", "known-marketplace",
                  "cache", "codex-plugin", "codex-marketplace", "codex-hook-trust",
                  "unreadable"]
    where: str          # display label, e.g. "~/.claude/plugins/installed_plugins.json"
    key: str            # the plugin/marketplace/hook key found
    detail: str = ""    # e.g. projectPath/scope for an install; reason for unreadable

def plugin_name(key: str) -> str                       # "a@b" -> "a"
def settings_locations(names, sources: Mapping[str, Mapping[str, object]]) -> list[PluginLocation]
def claude_state_locations(names, home: Path) -> list[PluginLocation]
def codex_config_locations(names, home: Path) -> list[PluginLocation]   # disabled plugin ≠ finding, as at 1c4977eb
def locate(names, *, home: Path, settings_sources) -> list[PluginLocation]  # wrapper = the three above

# removed_plugins.py — find_reappearances(names, *, home, settings_sources) -> list[str]
#   unchanged signature and message wording as at 1c4977eb, built by formatting locate().

# plugin_inventory.py
@dataclass(frozen=True)
class RepoReference:  repo: Path; path: str; line: int; text: str
@dataclass(frozen=True)
class PluginInventory:
    plugin: str                          # "name@marketplace"
    locations: tuple[PluginLocation, ...]
    claude_cli: tuple[str, ...]          # rows of `claude plugin list` naming it
    codex_cli: tuple[str, ...]           # rows of `codex plugin list` naming it
    project_settings: tuple[Path, ...]   # every <repo>/.claude/settings*.json enabling it
    worktree_settings: tuple[Path, ...]  # same, but inside a git worktree (report only)
    stale_worktrees: tuple[Path, ...]    # prunable worktrees whose dir is gone (report only)
    references: tuple[RepoReference, ...]
    errors: tuple[str, ...]              # a probe that could not answer — never silent

def discover_repos(root: Path) -> list[Path]           # git repos at root/<owner>/<repo> (depth 2, default root ~/dev/github), plus each repo's `git worktree list --porcelain` entries; dedupe by realpath
# A worktree whose directory no longer exists (git marks it `prunable`) is NOT an
# error: it goes to PluginInventory.stale_worktrees (report only) and never
# raises the rc.
def claude_cli_rows(name: str, *, timeout: int) -> tuple[list[str], str | None]
def codex_cli_rows(name: str, *, timeout: int) -> tuple[list[str], str | None]   # `codex plugin list --json` -> {installed:[…], available:[…]}; match an `installed[]` entry whose (`name`, `marketplaceName`) equal the selector's two halves AND `installed is True` (measured 2026-09-24: pluginId == f"{name}@{marketplaceName}" on all 86 entries — assert that too and report a mismatch as a probe error). Never a substring match.
def live_references(repo: Path, name: str) -> list[RepoReference]               # `git grep -n -F`, HISTORICAL_PATHSPECS excluded
def inventory(plugin: str, *, home: Path, root: Path) -> PluginInventory         # wrapper

HISTORICAL_PATHSPECS: tuple[str, ...]  # ':!docs/research' ':!docs/agents/goal-history.md' ':!docs/receipts' ':!docs/specs' ':!docs/direction' ':!docs/artifacts' ':!docs/rules-evidence'

# plugin_remove.py
@dataclass(frozen=True)
class RemovalStep: name: str; argv_or_action: str; target: str
@dataclass(frozen=True)
class RemovalPlan: plugin: str; steps: tuple[RemovalStep, ...]; blockers: tuple[str, ...]
@dataclass(frozen=True)
class StepResult: step: RemovalStep; rc: int; detail: str

def plan(inv: PluginInventory, *, repo_root: Path) -> RemovalPlan
def backup_cache(name: str, *, home: Path, dest: Path) -> StepResult          # tar.gz via tarfile module into <repo_root>/.agent/state/
def uninstall_project_scope(plugin: str, project: Path) -> StepResult         # see minimal-diff rule below
def remove_local_override(plugin: str, project: Path) -> StepResult           # settings.local.json key delete (gitignored file)
def remove_claude_marketplace(marketplace: str) -> StepResult                 # `claude plugin marketplace remove`
def remove_orphan_cache(name: str, *, home: Path) -> StepResult               # only AFTER backup_cache succeeded
def remove_codex_plugin(plugin: str) -> StepResult                            # `codex plugin remove` — only if codex_cli shows it installed
def remove_codex_marketplace(marketplace: str) -> StepResult
def remove_codex_hook_trust(plugin: str, *, home: Path) -> StepResult         # backup config.toml, delete the [hooks.state."<plugin>:…"] tables AND path-keyed [hooks.state."<abs path>"] tables whose path is under the plugin's codex cache dir (~/.codex/plugins/cache/<marketplace>/<name>/), by text; re-parse with tomllib; restore backup on parse failure. Keys only, never values.
def add_to_watchlist(name: str, *, repo_root: Path) -> StepResult             # append to doctor.toml [removed_plugins].names, text edit, re-parse
def apply(plan: RemovalPlan, *, home: Path, repo_root: Path) -> list[StepResult]   # stops at the first rc != 0
def plugin_inventory_main(argv: Sequence[str]) -> int                         # `plugin-inventory <name@mkt> [--json]`; rc 0 found-or-absent, 2 on probe errors
def plugin_remove_main(argv: Sequence[str]) -> int                            # `plugin-remove <name@mkt> [--apply] [--json]`; default prints the plan and exits 0
# main.py uses strict parse_args (main.py:3085): declare the positional plugin and
# the --apply/--json flags on each subparser and rebuild argv in the dispatch
# lambda, following the `instructions-report` precedent (main.py:2929-2937).
```

Output goes through `dotfiles_setup.codec.encode` (handles dataclasses and Path,
codec.py:212,345), exactly as `plugin_health` emits its report (plugin_health.py:378-403);
stdlib `json` only PARSES external payloads (CLI output, settings files), as
plugin_health.py:180-193 does. Direct msgspec encode/decode is banned (TID251).

## 4. Constraints and invariants

- **Dry run by default.** `plugin-remove` without `--apply` mutates nothing and
  prints the plan. `--apply` is the only mutating path.
- **Native first** (`use-tool-builtins.md`): `claude plugin uninstall --scope
  project --json` (run with `cwd=project`), `claude plugin marketplace remove`,
  `codex plugin remove <p@m>`, `codex plugin marketplace remove <m>`. Custom code
  only for what has no command: cache backup/removal, codex hook-trust tables,
  local-override keys, the watchlist.
- **Minimal settings diff.** `claude plugin uninstall` re-serializes the whole
  project `settings.json` (measured 2026-09-24 in knowledge-base: 12+/13− for one
  key). So `uninstall_project_scope` must: read the file text; run the CLI; parse
  the CLI's result; write back the ORIGINAL text with only the
  `"<plugin>": true|false,` line removed (fix a dangling comma if it was last);
  then assert `json.loads(new) == json.loads(cli_result)` and fail the step (and
  restore the CLI result) if they differ. The CLI still updates
  `installed_plugins.json`.
- **Never read or print values** from `~/.codex/config.toml` or `~/.claude.json`
  (`secrets-out-of-the-shell-env.md` rule 8): keys and line numbers only.
  `~/.claude.json` usage counters are NOT touched (harness-owned, rewritten live).
- **Every probe is bounded**: `subprocess.run(..., timeout=…)`, never an
  unbounded filesystem walk. Do NOT recurse `~/.codex` (it contains sockets:
  `ipc/ipc.sock`, `app-server-daemon/app-server-updater.sock`; a `grep -r` over
  it wedged 3.5 h on 2026-09-24). Read only the named files.
- **A probe that cannot answer is an error, never "absent"** (the `_Unreadable`
  pattern at 1c4977eb:removed_plugins.py:33-58; `probes-need-a-control-arm.md`).
- The restored doctor check returns `[]` when `setup.home is None` (as at 1c4977eb).
- **Worktrees are reported, never mutated** — they are other branches; they
  inherit the removal on rebase (fable runbook, "Other projects" row).
- **Cross-repo**: `plan()` covers every discovered repo's project settings, but
  commits/ships are the caller's (the skill), never the library's.
- **`codex_cli_rows` matches the exact selector.** A substring match reported
  `engineering-suite-ponytail@openai-curated-remote` as ponytail on 2026-09-24.
- No `fable-orchestrator` string in any created/modified code, config, test, skill, agent or rule file (specs/reports exempt; grep must return 0).
- No new `.sh` files (`bash_logic_budget` allowlist). No inline lint suppressions.
- Skills: `plugin-inventory` = when/what/how to read the output; `plugin-removal`
  = the wrapper: (1) run `plugin-inventory`; (2) for every `references` hit decide
  by judgment — live instruction/config → remove, historical → keep; re-derive any
  count near a hit (the two misses of 2026-09-24); (3) `mise run plugin-remove --
  <p@m>` dry run, then `-- --apply`; (4) verify with `mise run plugin-health` and
  `mise run doctor`; (5) one branch + PR per repo touched (`ship`/`land`,
  `kb-review` → `kb-ship`/`kb-land` in knowledge-base). Frontmatter `description`
  under ~500 chars, no incident tail.

## 5. Verification

```bash
uv run --project python pytest tests/test_plugin_state.py tests/test_plugin_inventory.py tests/test_plugin_remove.py tests/test_removed_plugins.py tests/test_doctor.py -q
uv run --project python pytest tests/ -q
uv run --project python dotfiles-setup verify run
mise run lint
mise run plugin-inventory -- ponytail@ponytail          # real, read-only: expect 0 locations, 10 worktree_settings, 3 stale_worktrees (KB), rc 0
mise run plugin-remove -- ponytail@ponytail             # real dry run: empty plan (already removed), rc 0
mise run plugin-inventory -- planning-with-files@planning-with-files  # POSITIVE arm: codex_cli and claude_cli both non-empty (it is installed on both harnesses)
mise run doctor                                          # removed-plugins: no finding
{ git diff --name-only origin/main; git ls-files -o --exclude-standard; } | grep -vE '^docs/(specs|research)/' | xargs grep -l fable-orchestrator ; echo "expect no file names above"
# control arm for that grep: printf 'fable-orchestrator\n' > .agent/state/arm.txt; echo .agent/state/arm.txt | xargs grep -l fable-orchestrator   # must print the path; then delete it
```

Tests must include FAIL arms: a fixture home where the plugin IS installed/enabled
/cached/codex-trusted yields each `PluginLocation` kind; an unreadable
`installed_plugins.json` yields an `unreadable` location (not absence); the
minimal-diff check fails when the CLI result differs semantically; `apply` stops
at the first failing step; `remove_orphan_cache` refuses without a backup;
`codex_cli_rows` does not match a superstring name. Subprocesses are faked in unit
tests; the real read-only commands above are the integration evidence
(`real-integration-evidence.md`).

## 6. Commit

`caller` — leave changes staged/unstaged in the working tree; do not commit.

## 7. PREMISES

| # | Kind | Claim | Source |
|---|---|---|---|
| P1 | L | Old module readers: `_plugin_name`, `_Unreadable`, `_load_json`, `_unchecked`, `_settings_findings`, `_claude_state_findings`, `_codex_findings`, `find_reappearances` | `git show 1c4977eb:python/src/dotfiles_setup/removed_plugins.py` lines 28-191 |
| P2 | L | Old doctor check + CHECKS row `("removed-plugins", check_removed_plugins)`; Setup has `settings` (243), `local_settings` (244), `user_settings` (250), `home: Path \| None` (253); `collect` loads all three settings (423-431) | `1c4977eb:python/src/dotfiles_setup/doctor.py:1326-1378`; current `doctor.py:243-253,423-431` |
| P3 | L | `plugin_health` runs `claude plugin list` with `PLUGIN_LIST_TIMEOUT = 10` via `subprocess.run(..., timeout=)` | `python/src/dotfiles_setup/plugin_health.py:39,128-160` |
| P4 | I | Subcommand registration + dispatch pattern | `main.py:1710-1720`, `main.py:2876-2880` |
| P5 | I | Task shape `run = 'uv run --project python dotfiles-setup plugin-health'` | `mise.toml:1676-1678` |
| P6 | I | `claude plugin uninstall <p> --scope project --json` → `{"outcome":"ok",…}` rc 0, cwd-scoped | measured 2026-09-24 in both repos |
| P7 | I | `codex plugin remove <PLUGIN[@MARKETPLACE]>`; `codex plugin marketplace remove <NAME>` | `codex plugin remove --help`, codex 0.156.1 |
| P8 | L | CLI uninstall re-serialized KB settings.json (12+/13−) for a one-key removal | this session, knowledge-base `git diff` before restore |
| P9 | L | `~/.codex` holds sockets `ipc/ipc.sock`, `app-server-daemon/app-server-updater.sock` | `find ~/.codex -maxdepth 3 -type s`, 2026-09-24 |
| P10 | L | 10 worktrees of dotfiles/KB still enable ponytail | `git worktree list --porcelain` + grep, 2026-09-24 |
| P11 | L | `codex plugin list` row `engineering-suite-ponytail@openai-curated-remote not installed` | 2026-09-24 |
| P12 | L | msgspec direct encode/decode is banned; use `dotfiles_setup.codec` | `python/pyproject.toml:123-139` |
| P13 | L | `git worktree list --porcelain` is the worktree source of truth (no filesystem walk); worktrees live outside any tree walk (`~/.codex/worktrees`, scratchpad dirs) and 3 KB ones are prunable | `.git/worktrees/*/gitdir` (5 dotfiles, 9 KB; 3 KB gitdirs point at a deleted /private/tmp dir) |
| P14 | L | `codex plugin list --json` (host codex 0.156.1) returns `{installed, available}`; each installed entry has `pluginId`, `name`, `marketplaceName`, `installed`, `enabled`; `pluginId == name@marketplaceName` on all 86 | measured 2026-09-24, rc 0 |
| P15 | L | `~/.codex/config.toml` has hook-trust tables keyed both `"name@mkt:…"` and by absolute path | premise-verifier header count, 2026-09-24 |
