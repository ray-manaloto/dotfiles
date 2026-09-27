# Cold review — hk v2.3 migration (`origin/main...HEAD`)

- Base: `453aa39bd18d9333fb0756051705a974085e1f86` (origin/main == merge-base)
- Head: `70b70c6d7d49ce36cb1e9542b340aa3ae6c6ff42` (branch `chore/hk-v2.3-migration`)
- Commits: `5a3077c2` (hk 2.3.0 + editorconfig-checker 4.0.2 migration), `70b70c6d` (tests git-isolation, AGENTS.md fmt rule)
- Scope: `git diff origin/main...HEAD -- . ':(exclude)docs/research/**' ':(exclude)*.lock' ':(exclude)docs/hk-builtins-audit.md'` — 15 files, +223/-60
- Reviewer: cold-reviewer (Opus), diff-only, no intent supplied. Memory consulted: `repo_gate_locations`, `gha_gate_review_patterns`, `mutation_harness`, `contract_token_and_mirror_replay`.
- Status: IN PROGRESS

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| F2 | MEDIUM | `test_global_git_config_isolated_from_machine_hooks` cannot detect removal of the fixture it is named for: its "isolated" arm passes with the fixture deleted (host has no `hook.*` in `~/.gitconfig`), and would also pass on a host WITH `hk install --global`, because the v2 hook runs `--from-hook`, which "gracefully exit[s] 0 when no hk.pkl is present" (`hk.usage.kdl:42`) — the throwaway repo has none. Only the control arm (explicit contaminated config) is exercised. | `tests/test_workflow_claude_code.py:535-541` | E3 |
| F3 | MEDIUM | Dropping `hk install --mise` from the postinstall silently removes the pre-commit/pre-push layers from every NEW clone and web/sandbox setup; the replacement (`hk install --global --mise`, git ≥2.54) lives only in a one-line `mise.toml` comment. Nothing gates hook presence (0 hits for `hook.hk-`/`core.hooksPath` checks in `python/src`, `doctor.toml`, `scripts/`), while `.claude/rules/do-not.md` #9 still counts "hk's `no_commit_to_branch` in the pre-commit hook" as one of four enforced layers. Existing clones are unaffected (this clone's `.git/config` still carries `hook.hk-pre-commit/commit-msg/pre-push`). | `mise.toml:177-178` | E4 |
| F4 | LOW | Stale claims left in the SAME module whose docstring was rewritten: `autofix` is described as "the postinstall SUCCEEDS and the git hooks ARE written" (`:333-335`) and "hk present, postinstall successful, hooks written" (`:810-811`); both are false once the postinstall stops installing hooks. Also `docs/adr/0001-hk-hooks-do-not-run-in-ci.md:7-8,26` (spec allowed leaving it) and `docs/adr/README.md:29`. | `python/src/dotfiles_setup/workflow_hooks.py:333` | `sed -n 320,350p` / `800,820p` of the module |
| F1 | HIGH | The new autouse `isolated_git_config` fixture replaces the global gitconfig for EVERY test, which strips the #1183 `safe.directory` stanza (`home/dot_gitconfig.tmpl:25-26`, rendered into `~/.gitconfig`). Smoke Tier 2 runs `pytest tests/ -x -q` inside the devcontainer (`scripts/devcontainer-smoke.sh:53`), and 17 test files run git-backed subprocesses with `cwd=REPO_ROOT`; under the documented virtiofs uid-0 flicker those tests now fail with `dubious ownership` — #1183 re-opened for the in-container pytest leg. | `tests/conftest.py:36-39` | E1 (two-arm git probe) + E2 (two-arm pytest probe) |

## Evidence log

### E1 — the fixture's environment strips `safe.directory` (raw git, 3 arms)

`GIT_TEST_ASSUME_DIFFERENT_OWNER=1` arms the ownership check with no root (memory `chezmoi_template_and_git_ownership_review`).
`container.gitconfig` = the fixture's `[user]` block PLUS `[safe] directory = <repo>` (what `home/dot_gitconfig.tmpl:25-26` renders in the container);
`fixture.gitconfig` = byte-for-byte the fixture's content (`tests/conftest.py:37`).

| Arm | Env | `git -C <repo> ls-files scripts` |
|---|---|---|
| 0 (control: probe works) | fixture cfg, no ownership arm | rc=0, 10 lines |
| 1 (container today) | ownership arm + container-like global | rc=0, 10 lines |
| 2 (container under this diff) | ownership arm + fixture cfg + `GIT_CONFIG_NOSYSTEM=1` | **rc=128** `fatal: detected dubious ownership in repository` |

### E2 — a real test goes red only because of the fixture (pytest, 2 arms)

`GIT_TEST_ASSUME_DIFFERENT_OWNER=1 GIT_CONFIG_GLOBAL=<container.gitconfig> uv run --project python pytest tests/test_bash_budget.py::test_cli_wires_end_to_end`

| Arm | Result |
|---|---|
| HEAD conftest (fixture active) | **1 failed**, rc=1 — `CalledProcessError: ['git', '-C', '<repo>', 'ls-files', '--', 'scripts/*.sh', ...] returned non-zero exit status 128` |
| `--noconftest` (fixture absent, same outer env) | 1 passed, rc=0 |

Only variable: the fixture. The in-container run itself was NOT executed (UNVERIFIED on the live container); the flicker's
existence and frequency are inherited from `.claude/rules/persistence-gate-retry.md` § "The dubious-ownership defect (#1183)".
Heuristic census of real-repo git consumers: `grep -lE '"git".*(REPO|ROOT)|cwd=(REPO|ROOT|_REPO)' tests/*.py` → 17 files.
Fix direction (not applied): write `[safe]\n\tdirectory = <repo root>` (or the protected-config equivalent) into the fixture's file.

### E3 — mutation: delete the fixture, rerun the isolation test

| Arm | Result |
|---|---|
| HEAD (`tests/conftest.py` fixture active) | 1 passed |
| `--noconftest` (fixture absent) | **1 passed** — the test does not constrain the fixture |

Host precondition read, not assumed: `git config --global --get-regexp '^hook\.'` → rc=1 (no entries).
Contrast (the author's other new test DOES bite): deleting `Flag(("--junit-xml",), takes_value=True),` from a
`git archive 70b70c6d` copy (PYTHONPATH-shadowed) → `2 failed` (`test_junit_xml_value_does_not_hide_the_hook` and
`test_pinned_flag_tables_match_the_documented_help[HK_RUN_FLAGS]`), so that docstring's mutation claim reproduces.

### E4 — hook installation after the diff

- `git config --local --get-regexp '^hook\.'` in this clone → `hook.hk-{pre-commit,commit-msg,pre-push}.command = test "${HK:-1}" = "0" || mise x -- hk run <hook> --from-hook`
  (written by the OLD postinstall; they keep working under 2.3.0 — `--from-hook` exists at `hk.usage.kdl:42`).
- hk 2.3.0 `install` long help (`hk.usage.kdl:274-311`): `--global` "Requires Git 2.54 or newer"; host git 2.54.0, CI runner `/usr/bin/git` 2.55.0
  (lint job 108546542527 log). The devcontainer's git (`conda:git = "latest"`, `.devcontainer/mise-system.toml:91`) was NOT measured.
- `HK_SKIP_HOOKS` is still honoured in v2 (`docs/environment_variables.md@v2.3.0`: "`HK_SKIP_HOOKS` is also accepted"), so the
  kept defense-in-depth is live, not decorative.

### E5 — hk 2.3.0 flag tables (Q: did the transcription miss a value-taking flag?)

Every value-taking flag in `~/.local/share/mise/installs/hk/2.3.0/.mise-packslip/assets/hk.usage.kdl` (hook-options `:8-77`, globals `:78-111`):
run — `-e`, `-g`, `-S`, `-W`(optional), `--files0-from`, `--format`, `--from-ref`, `--junit-xml`, `--sarif`, `--skip-step`, `--stash`, `--to-ref`;
global — `--cd`, `--format`, `-j`, `-p`, `--hkrc`(hidden). All 12 + 5 are present in `HK_RUN_FLAGS`/`HK_GLOBAL_FLAGS`. No finding.
Note: `--hkrc` is hidden, so the comment "Transcribed from hk 2.3.0 `hk --help`" is slightly inaccurate (it came from the usage spec); cosmetic.

### E6 — v2 migration guide checked against the repo (`jdx/hk docs/migration-v2.md@v2.3.0`)

Removed inputs grepped in the repo (excluding `docs/research/**`): `hkrc` / `hk.local.pkl` / `~/.config/hk` / `UserConfig` / `Types.Regex` /
`Config.Regex` / `defaults {` → only the new `--hkrc` flag-table rows; `git ls-files home | grep -i hk` → 0. `hk-image.pkl` (never evaluated
by host lint) validated separately at 2.3.0 in a scratch repo: rc=0 "is valid"; control arm (every `Builtins.x` → removed
`Builtins.check_byte_order_marker`) → rc=1. The global `exclude` still removes the verbatim trees: `hk check --all --plan --json`
→ `trailing_whitespace` fileCount 675 of 1705 tracked (kb 846 + runs 92 + specs 35 excluded).
Staging: guide says "`hk fix` and every other hook leave changes unstaged"; `docs/hooks.md@v2.3.0:26` says `hk fix` selects
"staged, unstaged, and untracked" — so the AGENTS.md rewrite (drop "git add BEFORE", add "git add AFTER") matches upstream. No finding.

### E0 — gate runs on HEAD (worktree == HEAD, clean)

- `mise run lint` with the session's ambient env → **rc=1**: `HK_PKL_BACKEND no longer selects an evaluator in hk v2`. The variable is
  set in this Claude session's inherited process env only — `grep -c HK_PKL_BACKEND` is 0 in `~/.config/mise/config.toml`,
  `~/.zshrc`, `~/.zprofile`, `~/.claude/settings.json`, and `mise env | grep -c` is 0. So a fresh shell does not carry it.
- `env -u HK_PKL_BACKEND mise run lint` → **rc=0**; `editorconfig-checker` (675 files), `pin_parity`, `hk_audit`,
  `workflow_claude_code`, `workflow_hk_skip_hooks` all `✔`.

## Q-FRESH / Q-SCOPE / Q-CLAIM

## GitHub repos touched
