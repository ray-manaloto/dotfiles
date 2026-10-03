# Research-sweep retrospect — research--kb--reports--agents--session-close-background-work-handover-2026-10-03 (PROPOSAL ONLY)

Run status: `complete` (statuses: complete). Report: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/coord-97ffeddb/docs/research/kb/reports/agents/session-close-background-work-handover-2026-10-03.md`.

> Nothing here has been applied. Tuning the workflow, its fetcher, rules or settings happens only through a
> spec + PR (#1502); this file is the input to that, written by a read-only agent.

## What was hard or missing

- Primary question unanswered: whether a RUNNING background Agent subagent survives `claude stop` (critic G1). Only indirect evidence (#92716, #98170, #98241); the sole local datum (38ae1474) had already delivered its report, so it cannot discriminate.
- Offline vendor docs ($CC) stop at changelog 2.1.273 while the host runs 2.1.288. No manifest covers the stop/--bg/SendMessage/SubagentStop/SessionEnd docs pages. Notes for v2.1.274-288 came from a raw fan-out file, not the primary releases or changelog.
- Six github-discussions rows came back empty_unverified (background-tasks-session-exit-drain, claude-stop-background-subagent, anthropics--claude-code/1-4). anthropics/claude-code has discussions disabled, so these rows were structurally unsearchable and added no signal. The run rated this 'not a gap', but the control could not discriminate.
- Code-search was thin. 'SessionEnd background task drain repo:anthropics/claude-code' returned 1 hit. The 3 hits for 'claude stop background subagent' were never examined. Neither result is verified exhaustive.
- Other-orchestrator coverage is missing. claude-squad, ruflo, Podiom, session-peer and postbag were read only as announcement text, not source or docs. No manifest covers a succession/lease/drain workflow. Generic analogues (Temporal leases, LangGraph checkpoints, OpenHands, Agent SDK resume) were not swept.
- Issue status was never confirmed for #98170, #98241, #96849, #92716, #85066 and #86443 (open/closed, maintainer replies, linked PRs). 'Fixed in 2.1.288' rests on release notes alone.
- Native mechanisms were not tested, only read about: SendMessage by agentId across sessions, `--resume --fork-session`, teams, `claude attach`/`logs`, and SubagentStop/SessionEnd payload fields. A SubagentStop hook that persists the report is the cheapest native form of option A, and it was left unevaluated.
- Repo-side claims are unarmed. The census inFlight 'no agent kind observed' claim was not checked against coordinator_handoff.py :1056-1095 or its tests. The detached-codex contract (sdlc-team pid, settlement files) was asserted without file:line citations.
- The proposed saved searches were never executed, so their must-hit and known-absent arming and hit counts are unknown. Whether gh `search/issues` handles OR and quoted terms, and PR search, was not validated.

## Proposals

| target | change | why |
|---|---|---|
| research-sweep-run.js: github-discussions stage | Before querying a repo's discussions, check `repos/<r>` `has_discussions`. If false, emit status `not_applicable` and skip the row instead of `empty_unverified`. Where discussions are enabled, run a must-hit control query. Fall back to GraphQL `search(type:DISCUSSION)`. | Six structurally empty rows were counted as unverified and could never be armed. |
| research_fanout.py / manifests: vendor-docs source | Add a manifest entry that live-fetches the code.claude.com docs pages (agent-view, hooks, cross-session-messaging, headless) and `gh api repos/anthropics/claude-code/releases`. Add a version-skew check that fails the mandatory-source gate when the local docs changelog version is older than `claude --version`. Also capture `claude --help` and `claude stop --help` output. | The docs mirror lagged the host by 15 releases, and the key stop semantics were never re-read. |
| research-sweep-run.js: issue-evidence stage | For every issue cited in the report, auto-fetch state, closedAt, the last N comments and timeline cross-references. Make the report template require a status column and reject a 'fixed in X' claim that has no linked PR or release. | Status and maintainer responses for six issues were unconfirmed. |
| research-sweep-run.js: code-search stage | After a code-search row returns 3 or fewer hits, fetch and summarize each hit automatically. Mark the row 'examined' only when every hit has been read. | Three hits were left unread and one query returned a single hit. |
| research_fanout.py: peer-project source type | Add a 'peer-orchestrator' lane that clones or reads the README and source tree of named repos (claude-squad, ruflo, OpenHands, LangGraph). It greps for orphan, handoff, resume, lease, heartbeat and takeover in code and issues, and records file:line hits. Keep announcement-only hits out of the evidence class. | Succession and lease workflows were judged from announcement text only. |
| research-sweep skill: empirical-probe stage | Add an optional sandboxed probe step for behavioral questions. Run a two-arm test (stop vs control) and log agent jsonl mtimes. Also capture SubagentStop/SessionEnd hook stdin payloads and test a SubagentStop-persist hook. The step needs a human-approved write scope. | The central question can only be settled empirically, and the sweep is read-only by design. |
| research-sweep-run.js: saved-search stage | Execute every proposed saved search through `gh api search/issues`, with a must-hit control and a fresh absent-token control. Record the hit counts in the report. Add `is:pr` variants, and test OR and quoted-term behavior once per run. | The saved searches were proposed unexecuted, so they are untuned and unarmed. |
| research-sweep skill: repo-claim verification | Require every claim about the repo (census kinds, retire blocking, sdlc-team detach contract) to carry a file:line citation and a read of the relevant tests. A claim without a citation is demoted to 'asserted'. | The inFlight and codex-lane claims were asserted without being read. |
