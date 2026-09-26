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

## Pick your path

- **The Workflow tool is available** → run the saved workflow and stop here.
  It owns the per-node model and effort routing (the reasoning is commented at
  the top of `.claude/workflows/research-sweep.js` — that file is the single
  source of truth).

  ```text
  Workflow({ name: "research-sweep", args: {
    question: "<the question>", repo: "<owner/repo, optional>",
    reportPath: "<abs>/docs/research/kb/reports/agents/<slug>.md",
    advisor: false } })
  ```

- **No Workflow tool** (a codex lane, a headless run) → run the in-lane steps
  below yourself.

## In-lane steps

1. **Fan out.** `mise run research-fanout -- --list-sources` shows which sources
   are usable here. Then run 1-3 query variants — short search terms, not
   sentences — scoped with `--repo` whenever the question is about one project:

   ```bash
   mise run research-fanout -- "<terms>" --repo <owner/repo> --sources <list>
   ```

   Choose sources by the question's shape: behaviour of a tool or library →
   `github-*`, `firecrawl-developer`, `context7`; recent sentiment →
   `last30days`, `exa`; general web → `exa`, `firecrawl-search`.
   Done when every run's manifest path and real exit code are recorded.
2. **Triage.** Read each manifest and its `<source>.json` files. Dedup by URL,
   rank primary sources (source code, merged PRs, maintainer answers, release
   notes) above secondary ones, and pick at most six URLs to deep-read.
   A source with status `empty_unverified` or `error` is a **gap**, never
   "nothing found" — carry it to the report.
3. **Deep-read.** GitHub threads through `gh api` (issue + comments, PR body,
   discussions via `gh api graphql`); other pages through
   `firecrawl scrape <url> --format markdown`. For a question about what code
   *does*, shallow-clone the repo at its latest release tag and read the source,
   then check whether the default branch changed it since — a merged fix that is
   not yet released is the most common surprise. Done when every chosen URL has
   yielded quoted claims or a recorded reason it could not be read.
4. **Synthesize** the report at
   `docs/research/kb/reports/agents/<slug>.md`: Answer; Evidence
   (claim | URL or file:line | verbatim quote); Conflicts resolved (source code
   and merged PRs beat issue threads, newer beats older — say which you
   trusted); Gaps; Recommendation; `## GitHub repos touched`.
5. **Refute** the claims the Answer depends on (at most five): re-open each
   primary source and try to break the claim; every negative needs a control
   arm (`.claude/rules/probes-need-a-control-arm.md`). Mark a claim you could not
   re-confirm as unverified in the report. Done when each load-bearing claim is
   confirmed, refuted, or explicitly unverified.

## Traps

- `gh search issues --repo` returns issues only; the fan-out uses
  `gh api /search/issues`, which returns issues AND pull requests.
- The firecrawl developer index lags GitHub by hours: a PR merged today can be
  missing from it while `github-issues` finds it.
- `last30days` takes about 100 seconds and is noisy for questions about a
  repository's behaviour; spend it on sentiment questions.
- A docs site can answer HTTP 404 with a full HTML body — judge fetches by status,
  never by size.
- Print credential presence, never values (`.claude/rules/secrets-out-of-the-shell-env.md`).
