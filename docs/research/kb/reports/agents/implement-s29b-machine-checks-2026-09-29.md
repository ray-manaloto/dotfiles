# Implement S29b — three machine checks (Claude fallback implementer lane)

> Location note: the brief asked for this report at
> `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/implement-s29b-machine-checks-2026-09-29.md`
> (MAIN checkout). Worktree isolation REFUSED that write (both Bash heredoc and the Write tool:
> "Edit the worktree copy of this file instead of the shared-checkout path"). It is written here, in
> the session scratchpad, for the coordinator to copy verbatim to the tracked path.

Spec: `/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/5545fa41-d28d-447c-98b6-1f0effb90ff8/scratchpad/spec-s29b-machine-checks.md`
Worktree: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/agent-a746d61bca3db94b9`
Branch: `feat/s29b-machine-checks` (from `origin/main` @ `948ec2e9`)

Status: DONE — committed `87f905ec`; lint/verify/lint-docs rc=0; pytest rc=0 under a mise ceiling
(plain rc=1 from one location-sensitive test, control-armed as pre-existing — see Gates)

## Premises

| # | Premise | Verdict | Evidence |
|---|---|---|---|
| P1 | `Rule(name, pattern, message, since)`; `_RULES` tuple at `hook_guard.py:417` | CONFIRMED (field is named `reason`, not `message`; plus optional `quoted_blind`) | `hook_guard.py:48-88`, `:417` |
| P2 | `_CMD`, `_WRAPPER`, `_RUNNER` exist and anchor command position | CONFIRMED | `hook_guard.py:117` (`_WRAPPER`), `:121` (`_CMD`), `:392` (`_RUNNER`) |
| P3 | newest date constant `_V10 = "2026-09-28"`; `_V11` free | CONFIRMED | `hook_guard.py:163`; no `_V11` anywhere |
| P4 | `bounded_wait.wait` checks `request.file.exists()` with no type check | CONFIRMED (line 89, not ~95) | `bounded_wait.py:88-89` |
| P5 | `mise run plugin-remove` / `plugin-inventory` exist | CONFIRMED | `mise.toml:1684-1690`; `main.py:1716-1728` (positional `plugin`, `--apply`, `--json`) |
| P6 | `tests/test_hook_guard.py` has parametrized deny/allow pattern | CONFIRMED | `tests/test_hook_guard.py:20-69` (deny), `:72-143` (allow), `:1108-1173` (per-rule name+since pattern) |

No premise refuted in a way that makes the spec contradictory.

Extra probe (not a spec premise): `claude plugin --help` / `claude plugin uninstall --help` /
`claude plugin marketplace --help` list the aliases `plugin|plugins`, `uninstall|remove`,
`marketplace remove|rm`. The C1 pattern covers exactly those (plus `plugins`). `plugin rm` is NOT a
real alias (the audit's F2 proposal listed it) and is not matched.

## Files changed (6, all in the spec's list)

- `python/src/dotfiles_setup/hook_guard.py` — `_V11 = "2026-09-29"`; fragments `_MISE_EXEC`,
  `_LINT_RUNNER`, `_LINT_TOOL`, `_CLAUDE_BIN`, `_RAW_PLUGIN_REMOVAL`; Rule `"lint tool piped to head/tail"`
  (placed right after the `_V3` gate-pipe rule, `_GATE` untouched) and Rule `"raw plugin removal"` (last
  in `_RULES`). No other rule's `since` touched. C1 also excludes a `--help`/`-h` in the same segment
  (the audit's L193 `uninstall --help` shape) and accepts a `mise exec … --` prefix.
- `python/src/dotfiles_setup/bounded_wait.py` — precondition after the exactly-one check: existing
  `--file` that is neither `is_file()` nor `is_dir()` → logged error, rc 2.
- `tests/test_hook_guard.py` — C1: 12 deny + 16 allow; C2: 8 deny (incl. both 2026-09-29b commands
  verbatim) + 9 allow. Each deny asserts rule name + `since == "2026-09-29"`.
- `tests/test_bounded_wait.py` — `/dev/null` → 2 (+ log text), FIFO → 2, existing regular file → 0,
  existing directory → 0. "Non-existent path that appears later → 0" is the pre-existing
  `test_file_created_during_an_injected_sleep_succeeds`.
- `.claude/rules/mise-tasks-only.md` — two table rows (C2, C1). 115 → 117 lines, 8852 → 9392 bytes
  (budget 200 lines / 24000 bytes).
- `.claude/rules/long-running-command-hangs.md` — rule 3 names the new rule; rule 2 names the rc=2
  refusal. Growth offset: 110 → 110 lines, 5875 → 5996 bytes.

## Tests

- Targeted (`tests/test_hook_guard.py tests/test_bounded_wait.py`): 350 passed, rc=0
  (log `scratchpad/t1.log`). New tests: 49 hook_guard parametrized cases + 4 bounded_wait.

## Arm the positive (mutation → restore)

Restore point: all six files `git add`ed first; each mutated file also copied to scratchpad
`*.good` and copied back; `git diff --stat` empty after each restore.

| # | Mutation (realistic: delete the wiring) | Result | rc | Log |
|---|---|---|---|---|
| 1 | delete the `Rule("raw plugin removal", …)` entry (`grep -c` → 0) | 12 failed (every deny case), 16 passed (allow arms) | 1 | `scratchpad/mut1.log` |
| 2 | delete the C3 precondition block in `wait()` (`grep -c is_file` → 0) | 2 failed (`/dev/null`, FIFO), 9 passed | 1 | `scratchpad/mut2.log` |
| 3 (extra) | delete the `Rule("lint tool piped to head/tail", …)` entry | 8 failed (every deny case), 9 passed | 1 | `scratchpad/mut3.log` |

## Real integration arm (the wired wrapper, not `decide()`)

`CLAUDE_PROJECT_DIR=<worktree> bash scripts/pretooluse-guard.sh < payload.json`:

- `C=~/.local/bin/claude; $C plugin uninstall chrome-devtools-mcp@chrome-devtools-plugins -s user --json`
  (the 2026-09-29b command) → `permissionDecision: "deny"` with the plugin-remove redirect.
- `mise exec ruff -- ruff format --check scripts/update_claude.py 2>&1|tail -2` (the 2026-09-29b command)
  → `permissionDecision: "deny"` with the ruff/ty redirect.
- Control: `claude plugin list --json` → empty stdout, rc=0 (allow).

`mise run hook-selfcheck` does NOT exist as a task; its CLI equivalent
`uv run --project python dotfiles-setup hook selfcheck` → all 7 checks PASS, rc=0
(`scratchpad/selfcheck.log`).

## Gates (each via `mise run gate -- run <name>`)

| Gate | rc | Result | Log |
|---|---|---|---|
| lint | 0 | passed, 68 steps ✔ incl. `ruff`, `ruff_format`, `py_ty`, `no_lint_skip`, `md_size_budget`, `agnix`, `contract_token_uniqueness` (31s) | `<wt>/.agent/gate-results/lint.log`; `scratchpad/gate-lint.log` |
| pytest (plain) | **1** | `1 failed, 3529 passed` then stopped (`-x`) on `tests/test_session_review.py::test_mise_requirement_task_exposes_required_root_and_configurable_limit` — ENVIRONMENTAL, see below | `scratchpad/gate-pytest.log` |
| pytest (full suite, no `-x`, plain env) | 1 | `1 failed, 4105 passed, 2 skipped` — the same single test, nothing else | `scratchpad/pytest-full.log` |
| pytest (`MISE_CEILING_PATHS=<…>/.claude/worktrees`) | **0** | `4106 passed, 2 skipped, 11 deselected` | `<wt>/.agent/gate-results/pytest.log`; `scratchpad/gate-pytest-ceiling.log` |
| verify | 0 | `166 passed, 0 failed, 4 skipped` | `<wt>/.agent/gate-results/verify.log`; `scratchpad/gate-verify.log` |
| lint-docs | 0 | `agnix . --strict` → "No issues found" (checked the log: agnix really ran) | `<wt>/.agent/gate-results/lint-docs.log`; `scratchpad/gate-lintdocs.log` |

### The one pytest failure is the worktree's LOCATION, not this diff

- Mechanism: this worktree is nested INSIDE the main checkout
  (`dotfiles/.claude/worktrees/agent-…`), so mise also loads the parent
  `~/dev/github/ray-manaloto/dotfiles/mise.toml` (proved by `mise --cd <wt> config ls` with the worktree's
  `mise.toml` ignored: the parent file is still listed). The test ignores only `REPO_ROOT/mise.toml`
  and asserts `session-requirements` then becomes unresolvable (`assert ignored.returncode != 0`); the
  parent checkout still defines it → `assert 0 != 0`.
- Control arm 1 (diff absent): stashed my 6 files (tag `s29b-control-arm-7f3k2q`, SHA `79e3afe7…`), tree ==
  `origin/main`; the same test failed identically (`assert 0 != 0`, rc=1, `scratchpad/control-main.log`).
  Restored with `git stash apply --index <sha>`, `cmp` identical, entry dropped by SHA.
- Control arm 2 (location removed): with `MISE_CEILING_PATHS` at the worktrees dir the test passes (rc=0,
  `scratchpad/ceiling-single.log`), and the whole gate passes (row above).
- Not fixed: the test and mise config are outside the spec's file list. Expect the plain gate to pass in
  a non-nested clone and in CI. Possible follow-up: this test is location-sensitive for every
  `.claude/worktrees/` agent (it could set `MISE_CEILING_PATHS` itself).

## Commit

- SHA **`87f905ec`** on `feat/s29b-machine-checks` (parent `948ec2e9` = origin/main). The commit's
  pre-commit hook ran (`check_conventional_commit` ✔), rc=0. 6 files, +261/−10.
- Not pushed, not shipped (per the brief).

## Left undone / notes for the coordinator

1. This report could not be written to the MAIN checkout path: worktree isolation refused it. Copy this
   file verbatim to `docs/research/kb/reports/agents/implement-s29b-machine-checks-2026-09-29.md`.
2. The pytest gate is rc=1 in THIS nested worktree for the environmental reason above; rc=0 under the
   ceiling. Re-run the plain `mise run gate -- run pytest` from the branch in a non-nested checkout
   before shipping.
3. The audit's F2 follow-up is NOT addressed here (out of scope): `marketplace remove` may leave
   `marketplaces/<name>..clone` behind; check `plugin_remove.py`'s post-conditions.
4. Design choices beyond the letter of the spec, each tested: C1 also matches `claude plugins …` (a real
   alias) and a `mise exec … --` prefix, and ALLOWS `--help`/`-h` in the segment (the audit's L193 shape);
   C2 matches only `check`/`format` (so `ruff --version | head` stays allowed). `plugin rm` (listed in
   the audit's proposal) is not a real CLI alias and is not matched.
5. `_V11 = "2026-09-29"` — per `mise-tasks-only.md` § Extending, `since` should be the day it lands on
   main. If this merges on a later date, bump `_V11` and the two test assertions before it lands.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the implementation, tests and rules
  docs (local worktree only; nothing pushed).
