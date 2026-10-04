# Research-sweep retrospect — research--kb--reports--agents--session-handoff-automation-sweep-2026-10-03 (PROPOSAL ONLY)

Run status: `complete` (statuses: complete). Report: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-automation-research/docs/research/kb/reports/agents/session-handoff-automation-sweep-2026-10-03.md`.

> Nothing here has been applied. Tuning the workflow, its fetcher, rules or settings happens only through a
> spec + PR (#1502); this file is the input to that, written by a read-only agent.

## What was hard or missing

- Merge-queue/auto-merge for agent-written docs and propagation of main to live sessions/worktrees were covered by no source (only issue 77869 touches it). Two of the question's core halves are unevidenced, and the report still recommends 'research merge queue first'.
- github-discussions canaries returned 0 items for anthropics/claude-code (2 sets) and claude-agent-sdk-python, so the empties are unverified. The repos API says discussions are disabled there, so the canary was the wrong control and could not discriminate.
- context7 exited 1 and firecrawl-search returned HTTP 402 on the second query (claude-bg-session-continuation-worktree-auto-merge). These two sources were lost with no retry or fallback, yet status stayed complete with empty mandatoryGaps and no failedReads.
- Code-search rows 'PreCompact handoff' and 'autocompact threshold' returned count 0 while armed, but were not verified against ground truth. Absence of results is not evidence of absence.
- Deep-read was capped at 6 picks. Third-party handoff tools (autosessionclaude, ddaanet/handoff, Continuous-Claude-v3, claudikins) and docs for agent teams, routines, Stop hook and SDK resume were never read, so they are cited by title only.
- The load-bearing trigger session.measure and the propagation claims (watchPaths/FileChanged, reloadSkills) rest on offline docs only. No runtime probe of --bg behavior was attempted, because the sweep is read-only fetch with no experiment stage.
- No offline mirror of cited URLs was made under docs/research/kb/raw/, so the report's links are not archived.
- github-releases returned empty_verified, so the 2.1.286 idle-compaction and CLAUDE_AUTOCOMPACT_PCT_OVERRIDE semantics were not checked from release notes.

## Proposals

| target | change | why |
|---|---|---|
| .claude/workflows/research-sweep-run.js | Add a coverage-check stage. It decomposes the QUESTION into sub-questions (e.g. auto-merge/merge queue, propagation, native triggers) and requires at least one source with hits per sub-question. A sub-question with none becomes a mandatoryGap, and the status is downgraded from complete. | The merge-queue and propagation gaps were only 'not covered' notes, and the run still reported complete. |
| python/src/dotfiles_setup/research_fanout.py | Make the discussions canary conditional. Query repos API has_discussions first, and if it is false emit 'not_applicable' instead of empty_unverified. Where it is true, use a positive-control repo through gh api graphql. | The canary returned 0 on repos with discussions disabled, which is noise rather than a control, and it left three unverified-empty entries. |
| python/src/dotfiles_setup/research_fanout.py | Treat a source error (context7 rc 1, firecrawl 402) as a fanoutGap. Add one retry, then a fallback source (exa or WebFetch). Also add a quota preflight that fails early on 402. | Two sources died silently on the second query and the run was still marked complete. |
| .claude/workflows/research-sweep-run.js | Raise or make configurable the deep-read cap of 6. Reserve picks so every third-party tool named in the report gets its canonical README read. Add a rule that a tool cited by title only is flagged unverified. | Prior art was cited without reading it. |
| python/src/dotfiles_setup/research_fanout.py | Add a mirror step that saves every cited URL under docs/research/kb/raw/, and report mirrorGaps when a cited URL is missing. | The no-offline-mirror breach left the cited links unarchived. |
| research-sweep skill | Add a rule that any claim about runtime behavior (hooks firing in --bg, FileChanged, session.measure) is labeled 'docs-only, untested' unless a probe was run. Spawn a separate write-capable probe lane for those claims. | The load-bearing claims were not tested and the sweep cannot run experiments. |
| .claude/workflows/research-sweep-run.js | Add a code-search control that pairs each armed query with a known-positive query on the same repo. Require the positive control to return hits before a zero count counts as verified-empty. | The zero-count code-search rows could not discriminate between 'absent' and 'broken'. |
