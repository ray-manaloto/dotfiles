# #1531 — /code-review high

- Target: merge SHA `63c0b6dd7ac4f07eebb590af683f31b574f1503f` (feat/native only doctor check)
- Lens: built-in `/code-review high` (forked, task `a5c4710f2ce3ce8ea`, 13 tool uses, 219s)
- Verdict: **FINDINGS** — 10 (3 MED)

## Verbatim result

No correctness-breaking defects turned up. The check works on the paths it was tested against. The 10 findings below are real weaknesses, ranked by severity: misleading output, gaps that let a non-native copy pass, error handling that hides other results, and maintenance cost. All line numbers refer to the files as they are at `63c0b6dd`. Nothing was verified with a test run (the recipe skips verification), and this lane wrote no files.

```json
[
  {
    "file": "python/src/dotfiles_setup/path_drift.py",
    "line": 451,
    "summary": "foreign_source checks markers in table order across the hit and its resolved target, so 'homebrew' wins over 'node_modules' and 'node_modules' wins over '.bun': the two most common non-native installs get the wrong source name.",
    "failure_scenario": "`bun add -g @openai/codex` creates ~/.bun/bin/codex -> ~/.bun/install/global/node_modules/@openai/codex/bin/codex.js. The resolved parts contain 'node_modules', so the FAIL says it came 'from an npm global install' instead of bun. `npm i -g @openai/codex` under Homebrew node gives /opt/homebrew/bin/codex -> /opt/homebrew/lib/node_modules/..., which is reported as 'from Homebrew', and `brew uninstall codex` then does nothing. The bun test (test_a_bun_global_first_hit_names_bun) uses a regular file rather than the real symlink, so it misses this."
  },
  {
    "file": "python/src/dotfiles_setup/path_drift.py",
    "line": 539,
    "summary": "native_roots calls .resolve() on the declared native location, so when that location is itself a symlink (agy's root is the file ~/.local/bin/agy), the 'native' root becomes whatever the symlink points to. Any non-mise copy linked there passes the positive native check.",
    "failure_scenario": "`ln -sf /opt/homebrew/bin/agy ~/.local/bin/agy`, or an npm/bun global target. native_roots resolves the root to the Homebrew/npm path, and is_native(hit) compares hit.resolve() with that same path and returns True. _from_mise is False, so the check reports zero findings while agy is not the native install. This is exactly the F1 regression the cold review closed. A target inside mise installs is still caught, but only by _from_mise."
  },
  {
    "file": "python/src/dotfiles_setup/doctor.py",
    "line": 1281,
    "summary": "One doctor.toml table with no `native` key makes check_native_only return that single config message immediately, so no binary is checked at all.",
    "failure_scenario": "A reviewed edit leaves [path_drift.native_only.agy] without `native` (a typo such as `natve`). Every session the doctor then shows only 'has no `native` locations'. A real 'codex resolves to mise's copy first' FAIL for codex/claude is never computed. The config error should be one finding alongside the other binaries' results, not a short-circuit."
  },
  {
    "file": "python/src/dotfiles_setup/doctor.py",
    "line": 1291,
    "summary": "doctor.toml replaces DEFAULT_NATIVE_ONLY as a whole rather than merging per binary, so declaring any one table silently removes the checks for the binaries it leaves out.",
    "failure_scenario": "Someone trims doctor.toml to just [path_drift.native_only.claude] (or adds a new zzfoo table and deletes the others). `declared` is non-empty, so `declared or None` passes only that table. agy and codex are no longer checked, and nothing reports that they dropped out. The suites.toml token check catches only the deletion of the three exact headers, not a renamed header or a missing default."
  },
  {
    "file": "python/src/dotfiles_setup/doctor.py",
    "line": 1291,
    "summary": "check_native_only passes setup.home through unchanged, and path_drift.check_native_only falls back to Path.home() when it is None. Setup.home's contract is that None means 'fixtures that never touch user state; checks that need it skip', and check_install_doctor (line 1389) honours that.",
    "failure_scenario": "Any test or caller that builds a Setup without home, on a Darwin host with a captured or inherited PATH, has the check probe the operator's real ~/.local/bin, ~/.codex and ~/.local/share/mise, and spawn a real `mise ls`. Results then depend on the machine, and the 'pure function of Setup' guarantee the docstring states is broken."
  },
  {
    "file": "python/src/dotfiles_setup/path_drift.py",
    "line": 682,
    "summary": "check_native_only runs a second `mise ls --current --json` subprocess (60s timeout) on every doctor run only to learn the installs root, which check_path_drift (line 312) has already fetched in the same run.",
    "failure_scenario": "The SessionStart hook runs CHECKS in order, so path-drift and native-only each spawn `mise ls` over ~148 tools. Every session start pays that subprocess twice, and a hung mise costs up to 120s instead of 60s. A failing mise also produces two separate DRIFT findings for one cause. The listing should be resolved once (on Setup, or passed in as `listing=`)."
  },
  {
    "file": "python/src/dotfiles_setup/path_drift.py",
    "line": 564,
    "summary": "When an install slug is not in the declared specs, uninstall_spec returns the raw slug, and the Fix line then gives an argument `mise uninstall` cannot accept.",
    "failure_scenario": "codex resolves first from ~/.local/share/mise/installs/npm-openai-codex-fork/1/bin/codex. The FAIL advises `mise uninstall --all npm-openai-codex-fork && mise reshim`. mise parses the slug as a registry short name and errors 'not found', so the printed fix fails. test_an_undeclared_slug_is_named_as_itself locks this broken advice in. The safer fallback is the `mise which <binary>` advice that shims already get."
  },
  {
    "file": "python/src/dotfiles_setup/path_drift.py",
    "line": 415,
    "summary": "DEFAULT_NATIVE_ONLY copies the doctor.toml tables by hand, so the same native roots and specs live in two places. The parity test checks only that the default specs are a subset of the TOML specs.",
    "failure_scenario": "Adding a spec (say `aqua:openai/codex-cli`) to the Python default but not to doctor.toml fails the test, while adding it only to doctor.toml passes. A later edit to one copy's `native` root is caught only for exact list equality. The module comment already expects a third copy (the devcontainer's native_clis_container). One source, the TOML loaded with a fallback, would remove the drift surface."
  },
  {
    "file": "python/src/dotfiles_setup/path_drift.py",
    "line": 636,
    "summary": "The 'one PATH reorder from winning' WARN only covers later mise copies. A later Homebrew, npm-global or bun-global copy behind the native one gets no warning, although the same reasoning applies.",
    "failure_scenario": "Native ~/.local/bin/codex is first and /opt/homebrew/bin/codex (an npm global) is later on PATH. The check reports nothing. When a shell profile puts /opt/homebrew/bin ahead of ~/.local/bin, which is common, the non-native copy wins with no prior warning, which is exactly what F1's 'native is positive' stance was meant to prevent."
  },
  {
    "file": "docs/research/kb/reports/agents/cold-review-native-only-doctor-2026-10-01.md",
    "line": 64,
    "summary": "The committed research report does not end with its `## GitHub repos touched` section: a 'Running evidence log' section (line 68 onward) follows it.",
    "failure_scenario": ".claude/rules/research-repo-enumeration.md: 'Every research artifact produced by an agent — deep reviews, … — MUST end with a `## GitHub repos touched` section'. Here the enumeration sits in the middle, so a grep for the trailing index used by the catalog tooling misses or misreads it."
  }
]
```

## Lane triage (second read) — appended after receipt

Re-read at main `785c3708`. `path_drift.py` is unchanged since the merge, and `doctor.py` changed by +15/-6 elsewhere.

| # | Severity | Second read | Disposition |
|---|---|---|---|
| 1 | LOW | CONFIRMED: `_FOREIGN_SOURCES` (`path_drift.py:450-458`) is order-first; `homebrew` precedes `node_modules`, which precedes `.bun`. Wrong source name ⇒ wrong fix advice | folded into F |
| 2 | MED | CONFIRMED: `native_roots` `.resolve()`s the declared root (`path_drift.py:539`); `is_native` compares `hit.resolve()` (`:546`). A symlinked `~/.local/bin/agy` (currently a regular file, 175 MB) pointing at a foreign copy would pass | Issue F |
| 3 | MED | CONFIRMED: `doctor.py:1282-1288` returns early on the first table missing `native`, blinding the other binaries | Issue F |
| 4 | MED | CONFIRMED: `declared or None` (`doctor.py:1292`) means any non-empty table set REPLACES the defaults; an omitted binary drops silently | Issue F |
| 5 | LOW | `home=None` falls back to the real home | folded into F |
| 6 | LOW | duplicate `mise ls` spawn per doctor run | folded into F |
| 7 | LOW | the undeclared-slug fix advice is not a valid `mise uninstall` arg | folded into F |
| 8 | LOW | the two copies of the native table (Python default + doctor.toml) | folded into F |
| 9 | LOW | no WARN for a later non-mise foreign copy | folded into F |
| 10 | NIT | repos-touched section is not last in the cold-review report | none (verbatim record; rule 8 of agent-artifact-conventions forbids normalising it) |

Duplicate search: `native-only doctor` (48 hits; only #1531 relevant, closed) and `path_drift native_only` (0). Neither is a duplicate.

## GitHub repos touched

_None._ (local git objects only)

## Issues filed

- F → [#1599](https://github.com/ray-manaloto/dotfiles/issues/1599)
