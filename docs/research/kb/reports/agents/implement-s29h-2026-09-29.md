# implement-s29h — S29-H implementation report (Opus fallback for codex-sol-implementer), 2026-09-29

Spec: `docs/specs/s29h-machine-checked-handoff.md`. Branch `feat/s29h-machine-checked-handoff`. Nothing is committed (COMMIT: caller).

## Status

COMPLETE: all three gates are GREEN on the final tree (lint 0, pytest 0, verify 0), and all five live arms and four mutation arms behave as specified.

Two gates were first red on `classifier_axes`. Team-lead then extended the allowlist to exactly two edits (see "Allowlist extension" below), and after those edits every gate is green.

## Allowlist extension (approved by team-lead), with before/after

- `python/src/dotfiles_setup/classifier_tables.py`: added the REGISTRY entry `"dotfiles_setup.pr_facts:classify_check"` (module_path pr_facts.py, function classify_check, subject None/None, axes `{"check"}`, table `tests/test_pr_facts.py:_CLASSIFY_CHECK_TABLE`, table_excluded_classes empty, and an S29-H reason). Nothing else in the file changed.
- `tests/test_classifier_tables.py`: added `"pr_facts.py:classify_check"` to `prior_classifiers` (:867). Nothing else in the file changed.
- `uv run --project python dotfiles-setup classifier-axes`: **before rc=1** (`classifier-axes unlisted: python/src/dotfiles_setup/pr_facts.py:classify_check …`), **after rc=0** (`classifier-axes OK: 9 registered classifier(s) whose declared axes match the code, and no unregistered classifier-shaped function`).
- Control arm, in-process with nothing written: repointing the entry's `table_symbol` to `_NO_SUCH_TABLE` → `['table_missing']`. The pre-edit state is the deletion arm, which gave rc=1.

## Final gates (after the extension)

| gate | command | rc | evidence |
|---|---|---|---|
| lint | `mise run gate -- run lint` | **0** | `.agent/gate-results/lint.log`, failures [] |
| pytest | `mise run gate -- run pytest` | **0** | `.agent/gate-results/pytest.log`, `4232 passed, 11 deselected in 294.50s` |
| verify | `mise run gate -- run verify` | **0** | `166 passed, 0 failed, 4 skipped` |

I re-ran arm 1 on the final tree: rc=1, with the same two `task_plan.md:1108`/`:1162` findings and nothing else.

### Re-run requested by team-lead (third run, same tree plus report edits)

- `git diff --stat` still shows both approved edits (classifier_tables.py +15, test_classifier_tables.py +1). `classifier-axes` rc=0.
- lint **rc=0**, verify **rc=0** (166/0/4).
- The first pytest re-run gave **rc=1**, `1 failed, 3630 passed`:
  `test_session_review.py::test_default_cli_includes_automation_and_dual_provider_requirements` failed with `.agent/test-default-session-review.md` `is_file() False`. I **voided** that run for a two-writer collision. Another `mise run gate -- run pytest` (pid 9366, not mine) was live in the same checkout, writing the same fixed `.agent/` output path and `.agent/gate-results/pytest.log`. Three pieces of evidence:
  - The test passed alone (rc=0).
  - `session_review*.py`/`session_ledger*.py` import none of handoff_check/session_state/pr_facts/classifier_tables (grep rc=1; control: the same file shows 13 `import` lines).
  - `docs/agents/goal-history.md` became modified by another writer during the run.
- I waited for pid 9366 to exit (bounded) and confirmed no pytest process was running. The pytest gate then gave **rc=0**, `4232 passed, 11 deselected in 305.23s`, and still no concurrent pytest afterward.

## Changed paths (all inside the allowlist)

- `python/src/dotfiles_setup/pr_facts.py` (new): `GH_TIMEOUT=120`, `run_gh` (moved verbatim from `session_state._gh`), `CheckBucket` (StrEnum, values pass/fail/pending), `classify_check`, `CheckCounts` (+`total` property), `count_checks`, `ItemKind`, `PrFacts`, `fetch_facts` (issues endpoint first, then `gh pr view` for a PR).
- `python/src/dotfiles_setup/handoff_check.py`: new `_visible_lines` helper, which `_task_carrier_findings` (UNCLOSED_FENCE behaviour unchanged) and extraction both use. Also new: `active_section`, `ClaimWord`, `Claim`, `extract_claims`, `claim_holds`, `check_with_claims`, two new `Verdict` members, a per-number cache and a total deadline. `check()` delegates. The OK line appends `; N PR claim(s) match GitHub`. `main` passes the display source and the count.
- `python/src/dotfiles_setup/session_state.py`: `_gh`/`_GH_TIMEOUT` deleted, and every gh call now goes through `pr_facts.run_gh`. `_checks_summary` now goes through `count_checks`. New: `PrSummary`, four new `Snapshot` fields, `default_since`, `parse_since`, the open and merged-since queries (`--limit 100`), claim-grammar rendering, and `--since` (rc=2 when unparsable).
- `python/src/dotfiles_setup/main.py`: the session-state `--since` argument and the dispatch passthrough only.
- `mise.toml`: the two `description` strings only.
- `tests/test_pr_facts.py` (new; includes the `_CLASSIFY_CHECK_TABLE` truth table), `tests/test_handoff_check.py`, `tests/test_session_state.py` (6 `_gh` patches converted to a dispatching `pr_facts.run_gh` fake).
- Append-only: `progress.md`, `findings.md`.

## Gates (FIRST run, before the allowlist extension; kept for the record)

| gate | command | rc | log |
|---|---|---|---|
| lint | `mise run gate -- run lint` | **1** | `.agent/gate-results/lint.log` — `✗ classifier_axes`: `classifier-axes unlisted: python/src/dotfiles_setup/pr_facts.py:classify_check — classify_check() returns an enum defined in python/src/dotfiles_setup/pr_facts.py — it is a classifier, and it has no REGISTRY entry …` (the only failing step) |
| pytest | `mise run gate -- run pytest` | **1** | `.agent/gate-results/pytest.log` — `-x` stopped at `test_classifier_tables.py::test_the_real_registry_is_clean` (1 failed, 212 passed) |
| pytest (full, no -x, clean re-run after mutations restored) | `uv run --project python pytest tests/ -q` | **1** | `/tmp/claude-501/pytest-full2.log` — `3 failed, 4229 passed, 11 deselected`. All 3 are in `test_classifier_tables.py` (`test_the_real_registry_is_clean`, `test_classifier_shaped_finds_the_three_real_classifiers`, `test_classifier_axes_main_both_directions`), and each cites `pr_facts.py:classify_check` |
| verify | `mise run gate -- run verify` | **0** | `.agent/gate-results/verify.log` — `166 passed, 0 failed, 4 skipped` |

The first full pytest run overlapped the mutation windows, so I discarded it as VOID and re-ran clean after `cmp` confirmed both sources were restored.

Targeted: `ruff check` + `ruff format --check` + `ty check` on the new and changed source are clean. No inline suppressions.

## Real-integration arms (§5), live GitHub

1. `mise run handoff-check -- .agent/plans/session-2026-09-29b.md` → **rc=1**, exactly two findings and no other claim finding:
   ```
   - pr_claim_mismatch: `#1449 auto-merge (task_plan.md:1108)` — GitHub reports PR #1449 state=OPEN auto-merge=yes checks fail:2 pending:0 pass:12
   - pr_claim_mismatch: `#1449 auto-merge (task_plan.md:1162)` — GitHub reports PR #1449 state=OPEN auto-merge=yes checks fail:2 pending:0 pass:12
   ```
   task_plan.md was not edited.
2. Scratch copy + `- #1454 research-sweep tuning (auto-merge armed)` → **rc=1**, 3 findings, including
   `pr_claim_mismatch: #1454 auto-merge armed (…/handoff-arm2.md:63) — GitHub reports PR #1454 state=MERGED auto-merge=yes checks fail:0 pending:0 pass:15`.
3. The same copy under `GH_HOST=bogus.invalid` → **rc=1**, 9 × `pr_claim_unverifiable` (one per number: #1456, #1452, #1454, #1449, #1450, #1441, #963, #1063, #1445), for example
   `#1454 — GitHub lookup failed (gh api exited 1: unable to expand placeholder in path: none of the git remotes configured for this repository correspond to the GH_HOST environment variable. …) — 5 claim(s) unchecked; a failed lookup is never a pass`. No token was printed.
4. `mise run session-state` → **rc=0**. It prints `- **open PRs** (7):`, including `  - #1449 OPEN, auto-merge armed, RED (fail:2 pending:0 pass:12) — \`Update image-build inputs\` (@app/renovate)`, and `- **merged since** 2026-09-29T22:26:03Z (.agent/plans/session-2026-09-29b.md mtime): none`. The handoff mtime is 17:26:03-0500 = 22:26:03Z ✓. That output was pasted into a scratch handoff copy and handoff-check run on it: rc=1 with ONLY the two arm-1 plan findings, so the pasted rows added none. In-process on the State section alone: 20 claims extracted, 0 findings from them, and `claims_checked` = 34 counting the active plan.
   - Note: default `since` is the mtime of the handoff's LAST write, 22:26:03Z. That is later than #1456's merge (22:09:36Z), so "merged since" is empty by default. This is the effect the premise report named, now observed.
5. `mise run session-state -- --since 2026-09-29T00:00:00Z` → 20 merged, including #1454 (21:52:30Z) and #1456 (22:09:36Z). `--since 2026-09-29T22:00:00Z` → exactly #1456 and #1455, **not #1454**. **A1 CONFIRMED: GitHub honours the time part.** Control: `--since bogus` → rc=2, `session-state: --since needs an ISO-8601 timestamp, got 'bogus'`.

P16 CONFIRMED live: `gh pr list --json` returns `author.login` (bots render as `app/renovate` and `app/dotfiles-refresh-bot-org`), `autoMergeRequest`, `statusCheckRollup` and `mergedAt`.

## Control arms (mutations; each restored by byte copy, `cmp` identical)

| # | mutation (one semantic line) | live arm | unit tests |
|---|---|---|---|
| M1 | bare `auto-merge` drops `and checks.failing == 0` | arm 1 goes rc=1 → **rc=0** (motivating defect returns) | 2 failed |
| M2 | `armed` drops `facts.state == "OPEN" and` | arm 2's #1454 finding **disappears** (3 → 2) | 4 failed |
| M3 | a failed lookup emits no finding | arm 3 goes rc=1 → **rc=0 "OK"** | 2 failed |
| M4 | `_summaries` returns `()` on gh rc≠0 | `GH_HOST=bogus` session-state renders `open PRs: none`. Restored control renders `UNVERIFIABLE` | 1 failed |

## Dissent / deviations

1. **RESOLVED (allowlist extended by team-lead): `classifier_axes`.** Originally blocking, because it needed files outside the allowlist. Spec §3 makes `classify_check` return an enum, which makes it a classifier by the repo's gate, and the spec's Files list omits the two files that gate requires:
   - `python/src/dotfiles_setup/classifier_tables.py` REGISTRY entry. This was verified in-process with no file written: `find_violations` went from 1 `unlisted` to `[]`.
     ```python
     "dotfiles_setup.pr_facts:classify_check": ClassifierSpec(
         module_path="python/src/dotfiles_setup/pr_facts.py",
         function="classify_check",
         subject_param=None,
         subject_type=None,
         axes=frozenset({"check"}),
         table_path="tests/test_pr_facts.py",
         table_symbol="_CLASSIFY_CHECK_TABLE",
         table_excluded_classes=frozenset(),
         reason="S29-H: check buckets drive the RED/green/auto-merge claim verdicts; ...",
     ),
     ```
   - `tests/test_classifier_tables.py:862-867`: `prior_classifiers` (or its own set) must gain `"pr_facts.py:classify_check"`.
   I escalated this to team-lead via SendMessage, recommending the allowlist be extended to exactly these two edits. Team-lead APPROVED it, and both edits are applied exactly as proposed (see "Allowlist extension" at the top); nothing else changed in either file. The truth table `_CLASSIFY_CHECK_TABLE` in `tests/test_pr_facts.py` reaches every bucket.
2. `check_with_claims` has no `deadline_s` parameter (the spec signature has one). Six arguments trip ruff `PLR0913 (6 > 5)`, and suppressions are banned, so the budget is the module constant `CLAIMS_DEADLINE_S`, read at call time. Tests monkeypatch it. The behaviour is otherwise as specified.
3. `CheckBucket` is a `StrEnum` with `auto()`, so the values are still `"pass"/"fail"/"pending"`. A literal `PASS = "pass"` trips ruff `S105` (hardcoded password).
4. Unverifiable-by-deadline detail is exactly `claim-check deadline (300 s) expired before lookup`. The lookup-failure form adds the claim count.
5. Residuals, not fixed: `_path_findings` still scans raw text including code spans, so a PR title containing `foo.py:12` pasted from session-state would be path-checked. This is pre-existing behaviour. I also fixed one of my own test fixtures: `green-ish` legitimately matches `\bgreen\b` under the spec's rule.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — live PR/issue facts for arms 1-5 (read-only `gh api`/`gh pr view`/`gh pr list`)
