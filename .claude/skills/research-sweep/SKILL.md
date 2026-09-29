---
name: research-sweep
description: "Fan one research question out to many sources at once — GitHub issues, PRs, discussions and releases, exa, context7, firecrawl, last30days — then synthesize a cited report with every empty result control-armed. Use when an answer needs evidence from more than one source: whether an upstream bug is fixed or released, what a tool's recent release notes change, whether a tool now does something natively, how other projects solved a problem, or what people are saying about a tool."
---

# Research sweep

One question, many sources, one cited report. The **fan-out** is mechanical and
runs with no model at all (`mise run research-fanout`); only reading the best
hits and **synthesis** spend model tokens, and only synthesis spends frontier
ones. That split is the point of this skill: an agent that fetches by hand pays
reasoning prices for network I/O.

## Relation to knowledge-base

knowledge-base's `aggregated-research` / `kb_setup.research` (knowledge-base#509)
overlaps this. Ray ruled on 2026-09-26 (session `dotfiles-20260926.000`) that
dotfiles builds and uses `research-sweep` + `research-fanout` independently; in
this repo use this skill and do not import `kb_setup.research`
(`docs/specs/research-fanout.md` §4).

## Pick your path

- **The Workflow tool is available AND the user asked for a sweep (or approved
  one you proposed)** → run the saved workflow and stop here. It fans out to
  about 5-7 agents including one Opus/high synthesis, so a single-source
  question belongs on the in-lane steps instead. The workflow owns the per-node
  model and effort routing (the reasoning is commented at the top of
  `.claude/workflows/research-sweep-run.js` — that file is the single source of
  truth).

  ```text
  Workflow({ name: "research-sweep-run", args: {
    question: "<the question>", repo: "<owner/repo, optional>",
    reportPath: "<abs>/docs/research/kb/reports/agents/<question-slug>-<YYYY-MM-DD>.md",
    advisor: false } })
  ```

  `question` and an ABSOLUTE `reportPath` are required (the workflow throws
  otherwise). `advisor: true` adds a `codex-sol-advisor` second opinion, spent
  on codex tokens. Optional: `readMax` (URLs deep-read, default 6) and
  `verifyMax` (claims refuted, default 5).

- **No Workflow tool** (a codex lane, a headless run), or no sweep was asked
  for → run the in-lane steps below yourself. The fetch step needs network and `mise`;
  a codex lane under `--sandbox read-only` cannot run it — run the fan-out in a
  full-access lane, or hand the lane an existing output directory.

## In-lane steps

0. **Local corpora first** (`.claude/rules/research-doc-sources.md`). For how a
   harness behaves (Claude Code, codex, cursor), grep
   `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/<tool>/`;
   for a library listed in `docs/research/mintlify-catalog.md`, grep
   `docs/research/mintlify-cache/`. Fan out only for what those do not answer.
1. **Fan out.** `mise run research-fanout -- --list-sources` shows which sources
   are usable here. Then run 1-3 query variants — short search terms, not
   sentences — scoped with `--repo` whenever the question is about one project:

   ```bash
   mise run research-fanout -- "<terms>" --repo <owner/repo> --sources <list>
   ```

   Choose sources by the question's shape: behaviour of a tool or library →
   `github-*`, `firecrawl-developer`, `context7`; recent sentiment →
   `last30days`, `exa`; general web → `exa`, `firecrawl-search`. `last30days`
   runs ONLY when named in `--sources` (it is not in the default set) and may
   use its own LLM planner when its host keeps an LLM key in `pass`, so name it
   only for sentiment questions. Done when every run's manifest path and real
   exit code are written into the report's Evidence section (and appended to
   `findings.md` when the planning files are enabled).
2. **Triage.** Read each manifest and its `<source>.json` files. Dedup by URL,
   rank primary sources (source code, merged PRs, maintainer answers, release
   notes) above secondary ones, and pick at most six URLs to deep-read.
   A source with status `empty_unverified` or `error` is a **gap**, never
   "nothing found" — carry it to the report.
3. **Deep-read.** GitHub threads through `gh api` (issue + comments, PR body,
   discussions via `gh api graphql`); other pages through
   `firecrawl scrape <url> --format markdown`. For a question about what code
   *does*, shallow-clone the repo at its latest release tag
   (`gh api repos/<r>/releases/latest --jq .tag_name`) into `$TMPDIR` — never
   inside this repo — read the source, delete the clone, then check whether the
   default branch changed that code since the tag: a merged fix that is not yet
   released is the most common surprise. Done when every chosen URL has yielded
   quoted claims or a recorded reason it could not be read.
4. **Synthesize** the report at
   `docs/research/kb/reports/agents/<question-slug>-<YYYY-MM-DD>.md` (a slug of
   the QUESTION, not of a query variant: lowercase, hyphens, ≤60 chars): Answer;
   Evidence (claim | URL or file:line | verbatim quote); Conflicts resolved
   (source code and merged PRs beat issue threads, newer beats older — say which
   you trusted); Gaps; Recommendation; `## GitHub repos touched`.
5. **Refute** the claims the Answer depends on (at most five): re-open each
   primary source and try to break the claim; every negative needs a control
   arm (`.claude/rules/probes-need-a-control-arm.md`). Mark a claim you could not
   re-confirm as unverified in the report. Done when each load-bearing claim is
   confirmed, refuted, or explicitly unverified.

## Traps

- `gh search issues --repo` returns issues only; the fan-out uses
  `gh api /search/issues`, which returns issues AND pull requests.
- A workflow run's `subagents/workflows/<wf>/journal.jsonl` has no model field; the model each node ran on is
  `message.model` in that directory's `agent-*.jsonl`.
- The firecrawl developer index can lag GitHub by at least hours (one
  measurement: jdx/mise#13674, merged and missing from it on 2026-09-26), so
  `github-issues` can find what it misses.
- `last30days` took about 100 seconds in one run (2026-09-26, invoked WITH
  `--plan`); the fetcher's own invocation is unmeasured and capped at 180 s. It
  is noisy for questions about a repository's behaviour.
- A docs site can answer HTTP 404 with a full HTML body — judge fetches by status,
  never by size.
- Print credential presence, never values (`.claude/rules/secrets-out-of-the-shell-env.md`).
