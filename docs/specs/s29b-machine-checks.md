# Spec S29b — three machine checks for 2026-09-29b repeat offenders

Ruled by Ray 2026-09-29 (AskUserQuestion: "Build them in this session"). Source findings:
`docs/research/kb/reports/agents/session-audit-repeat-offenders-2026-09-29b.md` F2, F3, F4 and
`session-audit-dismissed-errors-2026-09-29b.md` F-1 (M-1 in `task_plan.md`, third recurrence).

## 1. Objective

Add three deterministic checks so these mistakes cannot recur silently:

- **C1 `raw plugin removal`** — `hook_guard` denies a Bash command that runs `claude plugin uninstall|remove` or
  `claude plugin marketplace remove|rm` directly (including via a variable/absolute path to the binary, e.g.
  `$C plugin uninstall`, `~/.local/bin/claude plugin marketplace remove x`). Redirect text: use
  `mise run plugin-inventory -- <selector>` then `mise run plugin-remove -- <selector>` (the `plugin-removal`
  skill), which dry-runs, backs up, and writes the doctor `[removed_plugins]` guard.
- **C2 `lint tool piped to head/tail`** — a NEW `Rule` entry (own `since`), sibling of
  "gate command piped to head/tail" (`python/src/dotfiles_setup/hook_guard.py:622-634`), covering
  `ruff check|format` and `ty check` (bare, via `uv run [--project python]`, or `mise exec [<tool>] --`) piped to
  `tail`/`head`. Do NOT widen `_GATE` (a widened pattern needs its own date — `.claude/rules/mise-tasks-only.md`
  § "`since` dates COVERAGE").
- **C3 bounded-wait refuses a device/non-regular `--file` target** — `bounded_wait.wait` returns 2 with a logged
  error when `request.file` is an existing path that is not a regular file or directory (e.g. `/dev/null`, a FIFO,
  a socket): such a target is satisfied instantly, so the wait can only succeed. A path that does not exist yet
  stays valid (that is the normal case).

## 2. Files

- `python/src/dotfiles_setup/hook_guard.py` — two new `Rule` entries + a new `_V11 = "2026-09-29"` constant.
- `python/src/dotfiles_setup/bounded_wait.py` — the C3 precondition in `wait()`.
- `tests/test_hook_guard.py`, `tests/test_bounded_wait.py` — tests (see §5).
- `.claude/rules/mise-tasks-only.md` — two new rows in "The canonical task map" table (C1, C2), same change
  (the rule's § Extending requires it).
- `.claude/rules/long-running-command-hangs.md` — one sentence under rule 3 noting ruff/ty are now guarded; one
  under rule 2 noting a device-node `--file` is refused. Keep within `md_size_budget` (offset any growth).

## 3. Interfaces

No new CLI surface. `bounded_wait.wait()` keeps its signature; new rc=2 path. Rule names exactly
`"raw plugin removal"` and `"lint tool piped to head/tail"`.

## 4. Constraints

- Match patterns against real shell syntax and rely on `_inert_masked` for quoting — no quote-awareness in the
  rule (`mise-tasks-only.md` § Extending). A quoted mention (`echo "claude plugin uninstall x"`,
  `rg 'ruff check' | head`) must ALLOW; the real invocation must DENY.
- C1 must NOT deny `claude plugin list|update|install|marketplace list|marketplace update|details|validate`, nor
  `mise run plugin-remove`, nor `python … plugin_remove` internals (those are subprocess calls, not Bash).
- C2 must NOT deny `ruff check x > /tmp/o.log 2>&1; echo rc=$?` or `rg ruff | head`.
- No inline suppressions (`no_lint_skip`). Python 3.14; match surrounding idiom and comment density.
- Do not touch any other rule's `since`.
- Work only in your worktree/branch `feat/s29b-machine-checks`; do not push, do not ship.

## 5. Verification (report real exit codes)

- Tests: for C1 ≥6 deny cases (bare `claude`, `$C`, absolute path, `uninstall`, `remove` alias, `marketplace rm`)
  and ≥6 allow cases (list/update/install/marketplace update, quoted mention, `mise run plugin-remove -- x`);
  for C2 ≥4 deny (`ruff check . | tail`, `uv run --project python ruff format --check f.py 2>&1 | tail -3`,
  `mise exec ruff -- ruff check f | head`, `ty check | tail`) and ≥3 allow; for C3: `/dev/null` → 2,
  a non-existent path that appears later → 0, a regular existing file → 0, a directory → 0.
- ARM THE POSITIVE (`.claude/rules/probes-need-a-control-arm.md` rule 2): after green, delete the C1 rule entry
  → its deny tests must FAIL; restore; same for C3's precondition. Record both rc values. Restore from
  `git stash`/`git show`, and `git add` before mutating (a `git checkout --` restores the STAGED version).
- Gates, each via `mise run gate -- run <name>`: `lint`, `pytest`, `verify`, `lint-docs`. All rc=0.
- `mise run hook-selfcheck` if that task exists (it drives the wired guard end-to-end).

## 6. Commit

One commit on `feat/s29b-machine-checks`: `feat(guard): deny raw plugin removal + lint-tool pipes; bounded-wait
refuses device targets` with body citing the audit reports and trailers:

```
Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_017U4bhJeNiL2W3F3LNaB3Gz
```

Print the commit SHA the commit command returns.

## 7. PREMISES (verify each; report CONFIRMED/REFUTED with file:line)

- P1 `Rule(name, pattern, message, since)` is the rule shape and `_RULES` is the tuple (`hook_guard.py:417`).
- P2 `_CMD`, `_WRAPPER`, `_RUNNER` exist and anchor command position.
- P3 The newest date constant is `_V10 = "2026-09-28"` (`hook_guard.py:163`), so `_V11` is free.
- P4 `bounded_wait.wait` checks `request.file.exists()` (`bounded_wait.py:~95`) with no type check.
- P5 `mise run plugin-remove` and `mise run plugin-inventory` exist (`mise.toml`, `main.py:1723`).
- P6 `tests/test_hook_guard.py` has a parametrized deny/allow pattern to extend.
