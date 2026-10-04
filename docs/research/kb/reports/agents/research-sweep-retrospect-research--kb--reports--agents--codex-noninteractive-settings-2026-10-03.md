# Research-sweep retrospect — research--kb--reports--agents--codex-noninteractive-settings-2026-10-03 (PROPOSAL ONLY)

Run status: `mandatory-gap` (statuses: mandatory-gap). Report: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/codex-noninteractive-research/docs/research/kb/reports/agents/codex-noninteractive-settings-2026-10-03.md`.

> Nothing here has been applied. Tuning the workflow, its fetcher, rules or settings happens only through a
> spec + PR (#1502); this file is the input to that, written by a read-only agent.

## What was hard or missing

- Mandatory gap: dependency-repo stage for openai/codex failed on github-releases (exited 1, HTTP/2 stream CANCEL). The 0.153-0.160 changelog was never read, so flag removals (--full-auto) and new features stayed unconfirmed.
- Mandatory gap: the anthropics/claude-code dependency probe emitted no PROBE-JSON line, so the probe did not run or its output was not copied. The Claude side of the unified schema rests on docs only.
- Mirror gaps: 7 learn.chatgpt.com pages (config-basic, config-advanced, config-reference, environment-variables, config-sample, agents-md, rules) failed with Firecrawl rate limits (about 11-17 req/min, retry 15-23s). The bursts were not paced or retried, so 'every config key / env var' was never enumerated.
- Mirror gap: https://learn.chatgpt.com/docs/config-file returned HTTP 404. It is probably an index or redirect URL, and no fallback or canonical-URL discovery was tried.
- Unverified-empty: github-releases returned status error with 0 items for two stages (codex-exec-output-schema and deps/openai--codex/2). The failure was transient and was not retried or distinguished from a genuinely empty result.
- No live capture was made for codex exec --json, claude -p, or agy. The unified-schema mappings (num_turns, model, duration, agy exit-0 on soft-deny) are speculative, and the schema was never validated.
- The saved GitHub searches were authored but not executed. Only 4 of about 25 have counts, and the controls, total_count and incomplete_results are unrecorded, so the controls could not discriminate.
- The side-agent stash note (uncommitted .codex/config.toml edit near line 266) was not reconciled. The cited knowledge-base/.codex/config.toml:267-268 may come from a different branch state than the one probed.
- The --strict-config effect on both repos' configs, hook behavior under exec, and the post-tag main commits were all unprobed. The recommended flag set is therefore unproven.

## Proposals

| target | change | why |
|---|---|---|
| python/src/dotfiles_setup/research_fanout.py (github-releases fetcher) | Retry on transient transport errors (stream CANCEL, 5xx, rate limit) with backoff, and fall back from the failing call to `gh api repos/X/releases --paginate`. Classify the outcome as error vs verified-empty. Make the error status name the retry count. | A single stream CANCEL produced a mandatory gap and two unverifiedEmpty entries. |
| research-sweep-run.js mirror stage | Throttle Firecrawl mirroring to the plan limit (concurrency 1-2, or a token bucket), and honour the 'retry after Ns' hint with a bounded retry. Treat a 404 on an index URL as a trigger to discover the canonical URL via sitemap or links. | 7 pages were lost to rate limiting and one to a 404, leaving the 'every key / env var' claim unsupported. |
| research-sweep-run.js dependency-repo stage | Emit the PROBE-JSON line from the stage's own script and write the file directly, instead of relying on the agent to copy the line. Fail loudly with the probe command's stderr if it is missing, and add a per-dep retry. | The anthropics/claude-code probe line was never recorded, which created a mandatory gap. |
| research-sweep-run.js and skill: live-capture stage | For CLI-output questions, add an optional stage that runs one cheap invocation per CLI (codex exec --json, claude -p --output-format json, agy -p) and saves the raw output as evidence. Require schema proposals to be validated against the captured files, and list the validator command. | The unified schema was derived from docs only and never checked against real output. |
| research-sweep-run.js saved-search stage | Require each saved gh api query to be executed once, and record total_count, incomplete_results and the control-arm count in a results table. Fail the gate when a query returns 0 or its control cannot discriminate. | Only 4 of about 25 queries had counts, so the controls were unverified. |
| skill/rules: preflight | Add a preflight that runs `git stash list` and `git status` on the cited repos and records the branch and HEAD under which config lines were cited. Reconcile any side-agent stash notes before citing file:line. | The stash note was left unreconciled with the report's line cites. |
| research-sweep-run.js critic stage | Convert each criticGaps.nextProbe into an executable follow-up stage that is budgeted and bounded to one round (strict-config probe, hook-trust marker test, release-notes read). Run those that are safe and read-only. | The critic found 15 gaps whose probes were cheap and left undone. |
