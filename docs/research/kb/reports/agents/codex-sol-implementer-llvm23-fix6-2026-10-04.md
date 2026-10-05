# LLVM freeze gate fix round 6 delivery report

Commit: `37390929952e52c0cdcd2d6384b2250d3adc0cdc` on `feat/llvm-23-detect-bump`. One new commit; clean tracked tree; no push.

Only tracked changes: `python/src/dotfiles_setup/llvm_major.py`, `tests/test_llvm_major.py`. All protected config bytes unchanged.

F1: apt must have built current head; tag+1 with an older tag build stays held. F2: freshly parsed build identity must equal detection evidence before a bump plan. F3: Freeze records the build-match result and the summary reads it. F4: original IWYU explanation and codename diagnostics restored. F5: all five fail-loud guard groups tested. F6: status line plus two headers, LF and CRLF. F8: Packages.gz count diagnostic, suite publication/Release Date wording, held-run docstring. F7: no action, as ruled.

Final targeted pytest: 228 passed, EXIT=0. Ruff, format check, ty, llvm-parity: EXIT=0 each. All 44 distinct sharp mutations killed with EXIT=1 using only `uv run --project python pytest tests/test_llvm_major.py -x -q -n 0`.

## Live freeze evidence

| Major | Head | Tag / commit | Ahead | Apt build | Release Date UTC | Frozen |
| --- | --- | --- | --- | --- | --- | --- |
| 22 | ca7933e47d3a3451d81e72ac174dcb5aa28b59d1 | llvmorg-22.1.8 / ca7933e47d3a3451d81e72ac174dcb5aa28b59d1 | 0 | ca7933e47d3a | 2026-07-14T18:49:42+00:00 | True |
| 23 | 21ef2ddb806006eba611b8a769ae72e5f86f9418 | llvmorg-23.1.2 / 85ac560262434c9ccfc0c183ec22d4138ed647fb | 27 | 67f4a076a097 | 2026-09-22T11:37:22+00:00 | False |

Live detector EXIT=4; direct freeze22 EXIT=0.

23 GA+served, held: IWYU, freeze; IWYU: conda-forge include-what-you-use has no version whose newest builds on both Linux architectures target libllvm23; freeze: release/23.x 27 ahead of llvmorg-23.1.2; apt build 67f4a076a097 ≠ head; suite published 2026-09-22 (Release Date)

## Research routes

RESEARCH INCOMPLETE: GitHub discussions canary returned 0 items; Firecrawl search exited 1 with HTTP 402. Strict-five EXIT=1. Manifest identity, source set and all raw evidence digests verified, EXIT=0.

| Source | Status | Exact blocker |
| --- | --- | --- |
| github-issues | empty_verified |  |
| github-discussions | empty_unverified | canary returned 0 items |
| github-releases | empty_verified |  |
| exa | ok |  |
| context7 | ok |  |
| firecrawl-developer | ok |  |
| firecrawl-search | error | exited 1: Error: Request failed with status code 402 / |
| last30days | ok |  |

[Same-turn manifest](/Users/rmanaloto/.codex/research-coverage/01a108b7-b9e3-7561-9a09-eccb5e046912/01a108b7-d837-7361-ae77-080d0bd2d81e/manifest.json).

Actually ran: native fnox profile codex_research, mise research-fanout, uv/Python, gh REST/GraphQL issues/discussions/releases, Exa HTTPS API, ctx7 CLI, Firecrawl developer HTTPS index, firecrawl CLI, installed Last30Days plugin Python script with explicit GitHub/grounding plan, curl live fetches, Ruff, ty, git and native hk hooks. No connector app, MCP research route, skill invocation or delegated agent was used.

Primary verification: [gh api manual](https://cli.github.com/manual/gh_api) confirms --include emits status and headers; real gh invocation EXIT=0. Also read [apt.llvm.org](https://apt.llvm.org/), [LLVM release instructions](https://llvm.org/docs/HowToReleaseLLVM.html), and [GitHub commits REST docs](https://docs.github.com/en/rest/commits/commits#compare-two-commits). Supplemental LLVM Discourse announcement web fetch returned Internal Error and supplied no final claim.

## Deviations and recovered attempts

No spec/code dissent or implementation deviation. No pins, paths, Dockerfile, Renovate, workflows, lockfiles or mise-system.toml changed. No push, hook bypass, suppressions, forbidden test command, lint, verify, image gate, or main-checkout operation.

Initial Ruff and format checks found issues; all corrected manually. Mutation-driver first attempt stopped before experiments on an ambiguous count-guard anchor. Second attempt stopped after a no-effect tag-site selector (fixture 22.1.0 versus assumed 22.1.8); its EXIT=0 is preserved. Resumed only unfinished experiments, yielding all 44 intended failures. First commit EXIT=1 because gitleaks falsely flagged ordinary prose in this session's gitignored findings.md; reworded the note without suppressions and retried the native hook. Credential values were never printed. Gitignored findings/state/report artifacts and requested temporary logs were written in addition to the two tracked files; required research receipt went to the developer-specified output directory.

## Every captured EXIT receipt

Expected mutation EXIT=1 means the corresponding test rejected the regression. Initial failures and no-effect probe remain visible below.

| Receipt | EXIT |
| --- | --- |
| [llvm-fix6-research-retry.log](/tmp/llvm-fix6-research-retry.log) | 1 |
| [llvm-fix6-research-manifest-retry.log](/tmp/llvm-fix6-research-manifest-retry.log) | 0 |
| [llvm-fix6-postcommit-audit.log](/tmp/llvm-fix6-postcommit-audit.log) | 0 |
| [llvm-fix6-commit-second.log](/tmp/llvm-fix6-commit-second.log) | 0 |
| [llvm-fix6-commit.log](/tmp/llvm-fix6-commit.log) | 1 |
| [llvm-fix6-format-final.log](/tmp/llvm-fix6-format-final.log) | 0 |
| [llvm-fix6-format-initial.log](/tmp/llvm-fix6-format-initial.log) | 1 |
| [llvm-fix6-format-second.log](/tmp/llvm-fix6-format-second.log) | 1 |
| [llvm-fix6-gh-headers.log](/tmp/llvm-fix6-gh-headers.log) | 0 |
| [llvm-fix6-hook-diagnosis.log](/tmp/llvm-fix6-hook-diagnosis.log) | 0 |
| [llvm-fix6-live-detect.log](/tmp/llvm-fix6-live-detect.log) | 4 |
| [llvm-fix6-live-freeze22.log](/tmp/llvm-fix6-live-freeze22.log) | 0 |
| [llvm-fix6-mutation-f1-head-build-at-tag-plus-one.log](/tmp/llvm-fix6-mutation-f1-head-build-at-tag-plus-one.log) | 1 |
| [llvm-fix6-mutation-f1-tag-build-at-tag-plus-one.log](/tmp/llvm-fix6-mutation-f1-tag-build-at-tag-plus-one.log) | 1 |
| [llvm-fix6-mutation-f2-bump-rebuild-no-write.log](/tmp/llvm-fix6-mutation-f2-bump-rebuild-no-write.log) | 1 |
| [llvm-fix6-mutation-f2-fresh-build-0.log](/tmp/llvm-fix6-mutation-f2-fresh-build-0.log) | 1 |
| [llvm-fix6-mutation-f2-fresh-build-1.log](/tmp/llvm-fix6-mutation-f2-fresh-build-1.log) | 1 |
| [llvm-fix6-mutation-f2-fresh-build-2.log](/tmp/llvm-fix6-mutation-f2-fresh-build-2.log) | 1 |
| [llvm-fix6-mutation-f2-fresh-build-3.log](/tmp/llvm-fix6-mutation-f2-fresh-build-3.log) | 1 |
| [llvm-fix6-mutation-f3-summary-head-match-ahead-two.log](/tmp/llvm-fix6-mutation-f3-summary-head-match-ahead-two.log) | 1 |
| [llvm-fix6-mutation-f3-summary-head-match-frozen.log](/tmp/llvm-fix6-mutation-f3-summary-head-match-frozen.log) | 1 |
| [llvm-fix6-mutation-f3-summary-head-match-young.log](/tmp/llvm-fix6-mutation-f3-summary-head-match-young.log) | 1 |
| [llvm-fix6-mutation-f3-summary-recorded-false.log](/tmp/llvm-fix6-mutation-f3-summary-recorded-false.log) | 1 |
| [llvm-fix6-mutation-f3-summary-recorded-true.log](/tmp/llvm-fix6-mutation-f3-summary-recorded-true.log) | 1 |
| [llvm-fix6-mutation-f3-summary-tag-mismatch.log](/tmp/llvm-fix6-mutation-f3-summary-tag-mismatch.log) | 1 |
| [llvm-fix6-mutation-f4-fallback-codename.log](/tmp/llvm-fix6-mutation-f4-fallback-codename.log) | 1 |
| [llvm-fix6-mutation-f4-iwyu-explanation-frozen-False.log](/tmp/llvm-fix6-mutation-f4-iwyu-explanation-frozen-False.log) | 1 |
| [llvm-fix6-mutation-f4-iwyu-explanation-frozen-True.log](/tmp/llvm-fix6-mutation-f4-iwyu-explanation-frozen-True.log) | 1 |
| [llvm-fix6-mutation-f4-no-suite-codename.log](/tmp/llvm-fix6-mutation-f4-no-suite-codename.log) | 1 |
| [llvm-fix6-mutation-f5-ahead-0.log](/tmp/llvm-fix6-mutation-f5-ahead-0.log) | 1 |
| [llvm-fix6-mutation-f5-ahead-1.log](/tmp/llvm-fix6-mutation-f5-ahead-1.log) | 1 |
| [llvm-fix6-mutation-f5-ahead-2.log](/tmp/llvm-fix6-mutation-f5-ahead-2.log) | 1 |
| [llvm-fix6-mutation-f5-ahead-3.log](/tmp/llvm-fix6-mutation-f5-ahead-3.log) | 1 |
| [llvm-fix6-mutation-f5-ahead-4.log](/tmp/llvm-fix6-mutation-f5-ahead-4.log) | 1 |
| [llvm-fix6-mutation-f5-clang-count-0.log](/tmp/llvm-fix6-mutation-f5-clang-count-0.log) | 1 |
| [llvm-fix6-mutation-f5-clang-count-2.log](/tmp/llvm-fix6-mutation-f5-clang-count-2.log) | 1 |
| [llvm-fix6-mutation-f5-missing-major-ga.log](/tmp/llvm-fix6-mutation-f5-missing-major-ga.log) | 1 |
| [llvm-fix6-mutation-f5-naive-clock.log](/tmp/llvm-fix6-mutation-f5-naive-clock.log) | 1 |
| [llvm-fix6-mutation-f5-sha-branches-0.log](/tmp/llvm-fix6-mutation-f5-sha-branches-0.log) | 1 |
| [llvm-fix6-mutation-f5-sha-branches-1.log](/tmp/llvm-fix6-mutation-f5-sha-branches-1.log) | 1 |
| [llvm-fix6-mutation-f5-sha-branches-2.log](/tmp/llvm-fix6-mutation-f5-sha-branches-2.log) | 1 |
| [llvm-fix6-mutation-f5-sha-branches-3.log](/tmp/llvm-fix6-mutation-f5-sha-branches-3.log) | 1 |
| [llvm-fix6-mutation-f5-sha-branches-4.log](/tmp/llvm-fix6-mutation-f5-sha-branches-4.log) | 1 |
| [llvm-fix6-mutation-f5-sha-commits-0-attempt2.log](/tmp/llvm-fix6-mutation-f5-sha-commits-0-attempt2.log) | 1 |
| [llvm-fix6-mutation-f5-sha-commits-0.log](/tmp/llvm-fix6-mutation-f5-sha-commits-0.log) | 0 |
| [llvm-fix6-mutation-f5-sha-commits-1.log](/tmp/llvm-fix6-mutation-f5-sha-commits-1.log) | 1 |
| [llvm-fix6-mutation-f5-sha-commits-2.log](/tmp/llvm-fix6-mutation-f5-sha-commits-2.log) | 1 |
| [llvm-fix6-mutation-f5-sha-commits-3.log](/tmp/llvm-fix6-mutation-f5-sha-commits-3.log) | 1 |
| [llvm-fix6-mutation-f5-sha-commits-4.log](/tmp/llvm-fix6-mutation-f5-sha-commits-4.log) | 1 |
| [llvm-fix6-mutation-f6-crlf-status-201.log](/tmp/llvm-fix6-mutation-f6-crlf-status-201.log) | 1 |
| [llvm-fix6-mutation-f6-crlf-status-301.log](/tmp/llvm-fix6-mutation-f6-crlf-status-301.log) | 1 |
| [llvm-fix6-mutation-f6-crlf-status-500.log](/tmp/llvm-fix6-mutation-f6-crlf-status-500.log) | 1 |
| [llvm-fix6-mutation-f6-first-newline-crlf-direct.log](/tmp/llvm-fix6-mutation-f6-first-newline-crlf-direct.log) | 1 |
| [llvm-fix6-mutation-f6-first-newline-crlf.log](/tmp/llvm-fix6-mutation-f6-first-newline-crlf.log) | 1 |
| [llvm-fix6-mutation-f6-first-newline-lf.log](/tmp/llvm-fix6-mutation-f6-first-newline-lf.log) | 1 |
| [llvm-fix6-mutation-f8-clang-count-source.log](/tmp/llvm-fix6-mutation-f8-clang-count-source.log) | 1 |
| [llvm-fix6-mutation-f8-release-date-label.log](/tmp/llvm-fix6-mutation-f8-release-date-label.log) | 1 |
| [llvm-fix6-mutations-driver-final.log](/tmp/llvm-fix6-mutations-driver-final.log) | 0 |
| [llvm-fix6-mutations-driver-second.log](/tmp/llvm-fix6-mutations-driver-second.log) | 1 |
| [llvm-fix6-mutations-driver-third.log](/tmp/llvm-fix6-mutations-driver-third.log) | 0 |
| [llvm-fix6-mutations-driver.log](/tmp/llvm-fix6-mutations-driver.log) | 1 |
| [llvm-fix6-parity-final.log](/tmp/llvm-fix6-parity-final.log) | 0 |
| [llvm-fix6-pytest-final.log](/tmp/llvm-fix6-pytest-final.log) | 0 |
| [llvm-fix6-pytest-initial.log](/tmp/llvm-fix6-pytest-initial.log) | 0 |
| [llvm-fix6-research-manifest.log](/tmp/llvm-fix6-research-manifest.log) | 0 |
| [llvm-fix6-research.log](/tmp/llvm-fix6-research.log) | 1 |
| [llvm-fix6-ruff-final.log](/tmp/llvm-fix6-ruff-final.log) | 0 |
| [llvm-fix6-ruff-initial.log](/tmp/llvm-fix6-ruff-initial.log) | 1 |
| [llvm-fix6-ruff-second.log](/tmp/llvm-fix6-ruff-second.log) | 0 |
| [llvm-fix6-stage.log](/tmp/llvm-fix6-stage.log) | 0 |
| [llvm-fix6-ty-final.log](/tmp/llvm-fix6-ty-final.log) | 0 |
| [llvm-fix6-ty-initial.log](/tmp/llvm-fix6-ty-initial.log) | 0 |

## Every mutation arm

| Mutation | EXIT | Observed failing test |
| --- | --- | --- |
| [f1-tag-build-at-tag-plus-one](/tmp/llvm-fix6-mutation-f1-tag-build-at-tag-plus-one.log) | 1 | tests/test_llvm_major.py::test_freeze_independent_conditions[1-ca7933e47d3a-age3-False] |
| [f1-head-build-at-tag-plus-one](/tmp/llvm-fix6-mutation-f1-head-build-at-tag-plus-one.log) | 1 | tests/test_llvm_major.py::test_freeze_independent_conditions[1-85ac56026243-age2-True] |
| [f3-summary-tag-mismatch](/tmp/llvm-fix6-mutation-f3-summary-tag-mismatch.log) | 1 | tests/test_llvm_major.py::test_freeze_summary_build_relation[1-ca7933e47d3a-14-\u2260-False] |
| [f3-summary-head-match-frozen](/tmp/llvm-fix6-mutation-f3-summary-head-match-frozen.log) | 1 | tests/test_llvm_major.py::test_freeze_summary_build_relation[1-85ac56026243-14-matches-True] |
| [f3-summary-head-match-ahead-two](/tmp/llvm-fix6-mutation-f3-summary-head-match-ahead-two.log) | 1 | tests/test_llvm_major.py::test_freeze_summary_build_relation[2-85ac56026243-14-matches-False] |
| [f3-summary-head-match-young](/tmp/llvm-fix6-mutation-f3-summary-head-match-young.log) | 1 | tests/test_llvm_major.py::test_freeze_summary_build_relation[1-85ac56026243-13-matches-False] |
| [f3-summary-recorded-false](/tmp/llvm-fix6-mutation-f3-summary-recorded-false.log) | 1 | tests/test_llvm_major.py::test_freeze_summary_uses_recorded_build_match[False] |
| [f3-summary-recorded-true](/tmp/llvm-fix6-mutation-f3-summary-recorded-true.log) | 1 | tests/test_llvm_major.py::test_freeze_summary_uses_recorded_build_match[True] |
| [f5-sha-branches-0](/tmp/llvm-fix6-mutation-f5-sha-branches-0.log) | 1 | tests/test_llvm_major.py::test_freeze_rejects_invalid_commit_sha[ca7933e47d3a-branches] |
| [f5-sha-branches-1](/tmp/llvm-fix6-mutation-f5-sha-branches-1.log) | 1 | tests/test_llvm_major.py::test_freeze_rejects_invalid_commit_sha[gggggggggggggggggggggggggggggggggggggggg-branches] |
| [f5-sha-branches-2](/tmp/llvm-fix6-mutation-f5-sha-branches-2.log) | 1 | tests/test_llvm_major.py::test_freeze_rejects_invalid_commit_sha[aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-branches] |
| [f5-sha-branches-3](/tmp/llvm-fix6-mutation-f5-sha-branches-3.log) | 1 | tests/test_llvm_major.py::test_freeze_rejects_invalid_commit_sha[aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-branches] |
| [f5-sha-branches-4](/tmp/llvm-fix6-mutation-f5-sha-branches-4.log) | 1 | tests/test_llvm_major.py::test_freeze_rejects_invalid_commit_sha[None-branches] |
| [f5-sha-commits-0](/tmp/llvm-fix6-mutation-f5-sha-commits-0.log) | 0 | No effect: incorrect fixture tag selector; corrected in attempt2 |
| [f5-sha-commits-0](/tmp/llvm-fix6-mutation-f5-sha-commits-0-attempt2.log) | 1 | tests/test_llvm_major.py::test_freeze_rejects_invalid_commit_sha[ca7933e47d3a-commits] |
| [f5-sha-commits-1](/tmp/llvm-fix6-mutation-f5-sha-commits-1.log) | 1 | tests/test_llvm_major.py::test_freeze_rejects_invalid_commit_sha[gggggggggggggggggggggggggggggggggggggggg-commits] |
| [f5-sha-commits-2](/tmp/llvm-fix6-mutation-f5-sha-commits-2.log) | 1 | tests/test_llvm_major.py::test_freeze_rejects_invalid_commit_sha[aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-commits] |
| [f5-sha-commits-3](/tmp/llvm-fix6-mutation-f5-sha-commits-3.log) | 1 | tests/test_llvm_major.py::test_freeze_rejects_invalid_commit_sha[aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-commits] |
| [f5-sha-commits-4](/tmp/llvm-fix6-mutation-f5-sha-commits-4.log) | 1 | tests/test_llvm_major.py::test_freeze_rejects_invalid_commit_sha[None-commits] |
| [f5-naive-clock](/tmp/llvm-fix6-mutation-f5-naive-clock.log) | 1 | tests/test_llvm_major.py::test_freeze_rejects_naive_clock - TypeError:... |
| [f5-missing-major-ga](/tmp/llvm-fix6-mutation-f5-missing-major-ga.log) | 1 | tests/test_llvm_major.py::test_freeze_rejects_missing_major_ga - Asser... |
| [f5-ahead-0](/tmp/llvm-fix6-mutation-f5-ahead-0.log) | 1 | tests/test_llvm_major.py::test_freeze_rejects_invalid_ahead_by[-1] - F... |
| [f5-ahead-1](/tmp/llvm-fix6-mutation-f5-ahead-1.log) | 1 | tests/test_llvm_major.py::test_freeze_rejects_invalid_ahead_by[1] - Ty... |
| [f5-ahead-2](/tmp/llvm-fix6-mutation-f5-ahead-2.log) | 1 | tests/test_llvm_major.py::test_freeze_rejects_invalid_ahead_by[1.0] - ... |
| [f5-ahead-3](/tmp/llvm-fix6-mutation-f5-ahead-3.log) | 1 | tests/test_llvm_major.py::test_freeze_rejects_invalid_ahead_by[True] |
| [f5-ahead-4](/tmp/llvm-fix6-mutation-f5-ahead-4.log) | 1 | tests/test_llvm_major.py::test_freeze_rejects_invalid_ahead_by[None] |
| [f5-clang-count-0](/tmp/llvm-fix6-mutation-f5-clang-count-0.log) | 1 | tests/test_llvm_major.py::test_freeze_rejects_clang_count[0] - IndexEr... |
| [f5-clang-count-2](/tmp/llvm-fix6-mutation-f5-clang-count-2.log) | 1 | tests/test_llvm_major.py::test_freeze_rejects_clang_count[2] - Failed:... |
| [f4-no-suite-codename](/tmp/llvm-fix6-mutation-f4-no-suite-codename.log) | 1 | tests/test_llvm_major.py::test_detect_no_suite_names_codename - Assert... |
| [f4-fallback-codename](/tmp/llvm-fix6-mutation-f4-fallback-codename.log) | 1 | tests/test_llvm_major.py::test_detect_fallback_names_codename - Assert... |
| [f4-iwyu-explanation-frozen-False](/tmp/llvm-fix6-mutation-f4-iwyu-explanation-frozen-False.log) | 1 | tests/test_llvm_major.py::test_detect_requires_both_gates[22-False-22-IWYU, freeze] |
| [f4-iwyu-explanation-frozen-True](/tmp/llvm-fix6-mutation-f4-iwyu-explanation-frozen-True.log) | 1 | tests/test_llvm_major.py::test_detect_requires_both_gates[22-True-22-IWYU] |
| [f6-first-newline-crlf](/tmp/llvm-fix6-mutation-f6-first-newline-crlf.log) | 1 | tests/test_llvm_major.py::test_freeze_github_http_failures[commits] - ... |
| [f6-first-newline-lf](/tmp/llvm-fix6-mutation-f6-first-newline-lf.log) | 1 | tests/test_llvm_major.py::test_freeze_gh_requires_http_200[\n-200] - j... |
| [f8-clang-count-source](/tmp/llvm-fix6-mutation-f8-clang-count-source.log) | 1 | tests/test_llvm_major.py::test_freeze_rejects_clang_count[0] - Asserti... |
| [f8-release-date-label](/tmp/llvm-fix6-mutation-f8-release-date-label.log) | 1 | tests/test_llvm_major.py::test_freeze_summary_build_relation[1-ca7933e47d3a-14-\u2260-False] |
| [f2-fresh-build-0](/tmp/llvm-fix6-mutation-f2-fresh-build-0.log) | 1 | tests/test_llvm_major.py::test_plan_rechecks_detected_apt_build[1:23.1.0~++20260804082631+ca7933e47d3a-1~exp1~20260804082728.35-False] |
| [f2-fresh-build-1](/tmp/llvm-fix6-mutation-f2-fresh-build-1.log) | 1 | tests/test_llvm_major.py::test_plan_rechecks_detected_apt_build[1:23.1.0~++20260804082631+21ef2ddb8060-1~exp1~20260804082728.35-True] |
| [f2-fresh-build-2](/tmp/llvm-fix6-mutation-f2-fresh-build-2.log) | 1 | tests/test_llvm_major.py::test_plan_rechecks_detected_apt_build[1:23.1.0-True] |
| [f2-fresh-build-3](/tmp/llvm-fix6-mutation-f2-fresh-build-3.log) | 1 | tests/test_llvm_major.py::test_plan_rechecks_detected_apt_build[1:23.1.0~++20260804082631+21ef2ddb8060-1~exp1~20260804082728.35ca7933e47d3a-True] |
| [f2-bump-rebuild-no-write](/tmp/llvm-fix6-mutation-f2-bump-rebuild-no-write.log) | 1 | tests/test_llvm_major.py::test_detected_bump_refuses_apt_rebuild - Ass... |
| [f6-first-newline-crlf-direct](/tmp/llvm-fix6-mutation-f6-first-newline-crlf-direct.log) | 1 | tests/test_llvm_major.py::test_freeze_gh_requires_http_200[\r\n-200] |
| [f6-crlf-status-201](/tmp/llvm-fix6-mutation-f6-crlf-status-201.log) | 1 | tests/test_llvm_major.py::test_freeze_gh_requires_http_200[\r\n-201] |
| [f6-crlf-status-301](/tmp/llvm-fix6-mutation-f6-crlf-status-301.log) | 1 | tests/test_llvm_major.py::test_freeze_gh_requires_http_200[\r\n-301] |
| [f6-crlf-status-500](/tmp/llvm-fix6-mutation-f6-crlf-status-500.log) | 1 | tests/test_llvm_major.py::test_freeze_gh_requires_http_200[\r\n-500] |

Exact commit trailers:

```text
Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01CuaT9nm8J1GXkfM1xfWXd8
```

## Stop-hook research retry

Re-ran the mandated strict-five command under native fnox for the same request and output directory. EXIT=1. Verified the replacement manifest's request identity, complete source set and all raw evidence digests: EXIT=0.

RESEARCH INCOMPLETE: github-discussions remains empty_unverified with exact blocker `canary returned 0 items`; firecrawl-search remains error with exact blocker `exited 1: Error: Request failed with status code 402 |`.

Latest counts: GitHub issues/releases empty_verified; Exa ok 10; Context7 ok 5; Firecrawl developer ok 10; Last30Days ok 4. All five provider groups attempted. The report now inventories 72 EXIT receipts. Commit 37390929952e52c0cdcd2d6384b2250d3adc0cdc and clean tracked tree verified unchanged; no new tests, commits or push.
