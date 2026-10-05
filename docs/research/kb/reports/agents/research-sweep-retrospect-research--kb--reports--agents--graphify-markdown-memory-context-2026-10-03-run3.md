# Research-sweep retrospect — research--kb--reports--agents--graphify-markdown-memory-context-2026-10-03-run3 (PROPOSAL ONLY)

Run status: `complete` (statuses: complete). Report: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-03o/docs/research/kb/reports/agents/graphify-markdown-memory-context-2026-10-03-run3.md`.

> Nothing here has been applied. Tuning the workflow, its fetcher, rules or settings happens only through a
> spec + PR (#1502); this file is the input to that, written by a read-only agent.

## What was hard or missing

- Mirror stage failed for all three seed PRs (#2875, #3348, #1064): firecrawl returned 'Insufficient credits'. The cited PR quotes exist only as live gh reads and cannot be re-audited offline (mirrorGaps; critic gap 'Offline mirrors missing').
- Third-party usage (ai-brain-starter SKILL.md, Agent Memory Atlas graphify page, DeepWiki Work Memory page) was never read, so the 'how people use it' half of the question was answered only from graphify's own features.
- github-discussions lane was empty_verified: control returned 10 hits for 'graphify' but no hit for the memory query. PR thread bodies were not searched for frontmatter/body, so real-world memory-dir usage reports are unknown (absence not proven).
- Code search 'filename:serve.py frontmatter' returned 0. It was armed as a gap, not proof of absence, and the serve.py score must-hit returned 2, so serve.py is indexed. The claim that query ignores frontmatter rests on code reading, not a positive negative-control.
- LLM semantic mode (the only mode likely to index prose) was never run. 'Lossy summary' and 'rationale is searched' are inferred from code reading.
- Version 0.9.74, named in the question, was never executed. The claim rests on a compare diff plus 0.9.73 behaviour, which can miss indirect extractor or graph-build changes.
- Upstream issues #295, #613 and #131 (frontmatter ask / ground truth / cache) were not read, so whether a frontmatter-search request or fix already exists is unknown.
- Query paths other than the keyword scorer (MCP serve tools, explain/path, embedding or --semantic flags) were not checked, so 'query does not search frontmatter' covers only the scorer.
- No Tier 0 vs Tier 1 comparison on the real memory dir. The Tier 0 recommendation rests on a 2-file synthetic fixture, not real size, link density or wikilink use.

## Proposals

| target | change | why |
|---|---|---|
| python/src/dotfiles_setup/research_fanout.py (mirror step) | When firecrawl returns an insufficient-credits error, fall back to saving 'gh api' JSON (PR/issue body and comments) or raw.githubusercontent content into the raw dir. For github.com URLs make gh the primary mirror and firecrawl the fallback. Classify the credits error as a distinct 'quota' status, not a generic not-mirrored line. | Seed-lead PRs were cited from live reads only and could not be re-audited. gh needs no firecrawl credits. |
| .claude/workflows/research-sweep-run.js (mirrorGaps handling) | Treat a mirror gap on a seed lead as a stage gap that marks the run degraded, or blocks completion, unless an offline copy exists. Add a preflight firecrawl credit check that warns before fan-out. | Run reported status 'complete' with empty mandatoryGaps although all three mandatory seed leads were unmirrored. |
| .claude/workflows/research-sweep-run.js (seed/lead reading stage) | Add a mandatory 'third-party usage' lane that reads every URL named in the question or lead list (gh raw or WebFetch) and tags each claim as documented-by-others or shipped. Fail the run if a named URL was not read. | Third-party usage pages were never read, so half of the question went unanswered. |
| .claude/workflows/research-sweep-run.js (discussions and issues lanes) | Make the discussions lane also search issues and PR comments for the topic terms (auto-memory, MEMORY.md, frontmatter). Read the cited upstream issues by number (#295, #613, #131). Pair the empty-result control with a positive control that has a known on-topic hit. | The discussions control proved only that the lane works for the word 'graphify', not that the memory query was searchable. Linked issues were skipped. |
| research-sweep skill / rules (empirical-behaviour questions) | For 'does tool X index Y' questions, require an executable fixture lane, run against both the named versions (0.9.73 and 0.9.74) via uvx --from pkg==ver, in each mode (keyword and LLM semantic). It should record hit/miss plus token cost, and also cover alternate query paths (MCP, explain, embeddings). Skip it only when no key is available, and in that case record the gap explicitly. | The answer to 'which mode indexes prose' and the 0.9.74 behaviour were inferred, not measured. |
| research-sweep skill (decision-feeding runs) | Require a small real-data comparison, for example a copy of the real memory dir, 5 recall questions, hit rate and token cost per tier. Alternatively require the report to label the recommendation 'provisional: synthetic fixture only'. | The Tier 0 vs Tier 1 decision was argued from a 2-file synthetic fixture. |
