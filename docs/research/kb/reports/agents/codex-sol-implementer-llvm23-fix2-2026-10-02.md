# LLVM fix round 2 rev 2 — lane report

Commit: `682d626d2d5d79aa5c1641889227d80482d25d05` (`fix(llvm): hold IWYU to the pinned major and report daily currency`).
Branch: `feat/llvm-23-detect-bump`. Exactly one commit relative to dispatch HEAD `ff72cf5c`; clean worktree; never pushed. Normal pre-commit and commit-msg hooks passed on the successful retry. Attribution trailers match the dispatch exactly.

## Result

- IWYU pin is live-derived `0.26`, held to apt LLVM 22. Per-version newest-build checks preserve F10 tie handling, skip single-architecture versions, and retain compatibility when later majors arrive.
- Offline parity separately validates the exact plain pin and the lock version plus both published Linux libllvm dependencies. Variants are ignored. Existing real lock is clean and unchanged.
- Explicit `--major` plans do not fetch Anaconda or plan the IWYU rewrite. Detected bumps rewrite the pin exactly once, report it, validate everything except the stale lock immediately after writing, and print the required lock-image next step. Full parity stays red until the lock is regenerated.
- Markdown reports retain the detection exit codes and held prefix. The daily llvm-currency job upserts or closes the exact-title standing report using native gh argv operations through mise. GH_TOKEN is scoped to the three steps that need it; REPO is job env. Existing refresh jobs are byte-identical.
- Exactly nine authorized paths changed. No lock, apt pin/path, Dockerfile, bake, Renovate or host-lock edit. No full pytest, mise run lint, mise run verify, verify-apt-pins, lock-image, Docker, push, hook bypass or HK_SKIP variable.

## Verification

Final targeted pytest: **217 passed**, EXIT=0, across only tests/test_llvm_major.py, tests/test_standing_issue.py and tests/test_workflow_hooks.py. Changed-file Ruff, format check and ty: EXIT=0 each. actionlint, authenticated online zizmor, pin-actions and token-audit: EXIT=0 each. Native hooks additionally passed ghalint_workflow, LLVM parity, hk_audit and their normal checks; no audit regeneration was needed.

Live read-only pin: iwyu_pin_for(22) = 0.26; iwyu_versions_for(23) = []; EXIT=0. Final llvm-parity EXIT=0. Final llvm-detect --markdown EXIT=4, pinned 22, newest GA 23, target 22, held on 23, IWYU ready false. The mise task labels a nonzero detector result as ERROR, while rc 4 is the specified held status.

The original newest-only iwyu_ready implementation was restored temporarily from dispatch HEAD for the requested mutation. test_iwyu_readiness_survives_later_major failed on its readiness assertion: EXIT=2 under xdist -x. The mutation driver EXIT=0 verifies the expected failure and restores the source byte-for-byte. The final targeted suite passed afterward. Coordinator synthetic 0.27/libllvm23 and 0.28/libllvm24 controls, each-platform lock drift, older missing-arm64 versions, malformed pins, rewrite counts, close-no-match, exact-title selection and parser dispatch are covered.

GitHub write operations and the daily job have offline runner/static evidence; this lane did not modify a live issue or launch a workflow.

## Research provenance and primary checks

Applied skill: [research-sweep](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002/.agents/skills/research-sweep/SKILL.md), in-lane path. No subagents, connector apps or MCP routes ran. The Last30Days installed plugin was accessed through its Python CLI; no Exa/Firecrawl connector plugin was invoked. Actual research routes: native fnox codex_research profile, mise research-fanout, gh REST issues/releases and GraphQL Discussions, gh code search, Exa HTTP API, Context7 ctx7 library/docs CLI, Firecrawl developer HTTP API and search CLI, Last30Days Python CLI with explicit web/GitHub plan and Exa backend. curl provided the live Anaconda and LLVM detector network probes. Verification used uv, pytest, Ruff, ty, actionlint, zizmor, pinact and the native git/hk hooks.

[Final manifest](/Users/rmanaloto/.codex/research-coverage/01a0ffe8-8d30-7e22-af52-f0611def70de/01a0ffe8-9209-7e60-be34-de3cd54db1b9/manifest.json): strict-five passed, research retry EXIT=0; independent request/raw/hash validation EXIT=0. Initial full receipt is preserved at `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/llvm23-20261002/.agent/kb/raw/llvm23-fix2-research-first-attempt/`.

| Source | Final status | Items |
|---|---|---|
| github-issues | ok | 10 |
| github-discussions | ok | 1 |
| github-releases | ok | 1 |
| exa | ok | 10 |
| context7 | ok | 2 |
| firecrawl-developer | ok | 10 |
| firecrawl-search | ok | 10 |
| last30days | ok | 2 |

Primary verification: live [conda-forge metadata](https://api.anaconda.org/package/conda-forge/include-what-you-use/files) supports the derived pin; the [feedstock recipe](https://github.com/conda-forge/include-what-you-use-feedstock/blob/main/recipe/meta.yaml) independently names IWYU 0.26 with LLVM 22. Official [gh issue list](https://cli.github.com/manual/gh_issue_list), [edit](https://cli.github.com/manual/gh_issue_edit), and [close](https://cli.github.com/manual/gh_issue_close) docs confirm the native interfaces. Explicit Context7 docs for /websites/cli_github_manual corroborate them. [ghalint policy 006](https://github.com/suzuki-shunsuke/ghalint/blob/main/docs/policies/006.md) requires step-scoped secrets. Material behavior claims were checked against these primary routes, current code and saved primary fixtures.

GitHub code query libllvm in the conda feedstock returned 0, with EXIT=0; this was not promoted to a dependency-absence claim. Same-source cli/cli README must-hit returned 9 and known-absent returned 0, both EXIT=0. The actual feedstock recipe was fetched separately and directly verified.

## Failures, limitations and deviations

- Initial research EXIT=1: RESEARCH INCOMPLETE: github-discussions empty_unverified, exact blocker `canary returned 0 items`; Context7 error, exact blocker `exited 1:`. Preserved unchanged. Retry against cli/cli completed every required route and passed strict validation.
- Fanout's Context7 lookup for the short library name cli resolved Supabase CLI. Those snippets were not used as evidence. Explicit GitHub CLI resolution and official manual docs both succeeded, EXIT=0.
- Browser reader failed the Anaconda endpoint with Internal Error. Real curl probes through the project fetcher succeeded and replaced that read route.
- Initial Ruff EXIT=1 (line formatting/imports, later argument count); initial ty EXIT=1 (optional comment in argv). Fixed without inline suppressions. Formatter applications EXIT=0; final checks EXIT=0.
- First native commit EXIT=1: ghalint job_secrets rejected job-scoped GH_TOKEN. No commit was created. Moved the token into detect/upsert/close step env, allowed by the spec and required by the primary policy, reran affected checks, and committed successfully with EXIT=0. No final spec or file-scope deviation.
- Initial standalone zizmor and native hooks emitted the tool's default offline-mode notice. Authenticated online standalone audits completed with no findings, EXIT=0, covering the unavailable online audits. Existing 17 repository suppressions were neither added nor modified.
- Mutation EXIT=2 is the expected deliberate failing control, with source restoration verified. The baseline instruction wording and existing planner assertions were adapted where the new specified semantics change their expected behavior.

## Every EXIT receipt

Each literal EXIT line below is copied from its command log, including unsuccessful attempts and supplementary research/control routes. Logs are also copied under .agent/logs for lane-local retention.

### /tmp/llvm23-fix2-actionlint-final.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-actionlint.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-commit-retry.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-commit.log

```text
EXIT=1
```

### /tmp/llvm23-fix2-context7-docs.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-context7-resolve.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-detect-final.log

```text
EXIT=4
```

### /tmp/llvm23-fix2-detect.log

```text
EXIT=4
```

### /tmp/llvm23-fix2-diff-check-final.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-diff-check.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-format-apply.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-format-apply2.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-format-apply3.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-format-final.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-github-code-absent.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-github-code-must-hit.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-github-code.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-invariants.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-live-iwyu.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-mutation-driver.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-mutation.log

```text
EXIT=2
```

### /tmp/llvm23-fix2-parity-final.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-parity.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-pin-actions-final.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-pin-actions.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-postcommit.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-primary-recipe.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-pytest-final.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-pytest-final2.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-pytest-initial.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-research-retry.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-research-validation.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-research.log

```text
EXIT=1
```

### /tmp/llvm23-fix2-ruff-final.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-ruff-fix.log

```text
EXIT=1
```

### /tmp/llvm23-fix2-ruff-initial.log

```text
EXIT=1
```

### /tmp/llvm23-fix2-ruff-second.log

```text
EXIT=1
```

### /tmp/llvm23-fix2-stage.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-stage2.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-token-audit-final.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-token-audit.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-ty-final.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-ty-initial.log

```text
EXIT=1
```

### /tmp/llvm23-fix2-workflow-preservation.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-zizmor-final.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-zizmor-help.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-zizmor-online.log

```text
EXIT=0
```

### /tmp/llvm23-fix2-zizmor.log

```text
EXIT=0
```
