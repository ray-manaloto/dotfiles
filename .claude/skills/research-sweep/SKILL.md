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
  about 11-17 agents (one Opus/high synthesis, plus an Opus/high adjudicator
  only when a claim is flagged), so a single-source
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
  on codex tokens. Optional: `readMax` (triaged URLs deep-read, default 6),
  `verifyMax` (claims refuted, default 5), `links` (URLs the user named —
  ALWAYS read, on sonnet, outside the triage cap) and `relatedRepos` (other
  projects the question is about — searched in BOTH directions, since a
  relationship searched from one side only is a gap). Pass every link the user
  gives in `links`; a user link left to triage can be ranked away. The run
  returns `routing` (node → agent type/model/effort), which the report's
  Provenance section carries — cite it when asked which agents researched what.

  **Three mandatory stages** (Ray, 2026-09-30) run whatever the planner chooses:
  **dependencies** (`github-issues,github-discussions,github-releases` for
  `repo` and every `relatedRepos` entry, both directions, one agent per repo;
  EACH of the three must answer `ok`/`empty_verified`, read from the run's
  manifest — the fan-out's own rc is 0 when any one source answered, #1473 —
  except a tracker the repos API reports DISABLED (`has_discussions` false, or
  `has_issues` AND `has_pull_requests` false — the issues search also returns
  PRs), which is a note, not a gap (Ray, 2026-10-02);
  pass `runId` to stamp each fan-out with `--request-id` so only THIS run's
  manifests count, else freshness is a 1-hour age window),
  **mirror** (every link saved by the mirror probe using pinned firecrawl, or
  webclaw when firecrawl answers credit exhaustion, into
  `docs/research/kb/raw/<report-slug>/links/<n>.md` plus a `README.md` index;
  readers read the mirror) and **code search** (at least one planner query that
  is evidence, a fresh known-absent control, and a must-hit >0 from the planner
  or a README control). **Every mandatory number is computed by a probe, not
  interpreted by an agent** (#1514): each stage runs one workflow-built
  `mise run research-fanout -- --probe-out <path> ...` command (`--code-search
  ROLE=Q`, `--repo-check R`, `--fanout-manifest M --require ...`, `--mirror-url
  U --mirror-path F`, `--mirror-index DIR --mirror-count N`), which runs gh and
  firecrawl itself (with webclaw fallback for credit exhaustion) and writes
  real exit codes and HTTP statuses to that manifest (a page answering
  HTTP >= 400 is a failure and is not saved, except a credit-exhausted route
  may be substituted by a validated webclaw response:
  firecrawl exits 0 with a full 404 body; a stale manifest or mirror probe from
  an earlier sweep is a gap, never evidence); the agent copies the final
  `PROBE-JSON` line, and the workflow accepts it only when it names the exact
  path it asked for. That echo catches a miscopied line, not a fabricated one:
  the workflow has no filesystem, so the manifests on disk are the evidence a
  reader re-checks. A planner query
  that returns 0 is evidence only beside a planner must-hit >0 with the SAME
  qualifier set; otherwise it is an unarmed gap (`codeSearchGaps`, #1471). The workflow adds its own controls for two separate questions:
  *does code search answer at all?* — one search-health control
  (`repo:cli/cli filename:README.md`, role `health` — workflow-only: the
  planner's roles are `query`/`must-hit`/`known-absent`, and a planner row tagged
  `health` is INERT — recorded, counted for nothing), whose 0 or
  failure is a gap — and, per dependency repo, *does it
  exist under this name?* (`gh api -i repos/<r>`: a 404 is "not found", a
  403/429/other is "could not check", and a rename such as `jdx/rtx` →
  `jdx/mise` is a gap naming the canonical repo) and *is a README.md of it
  indexed?* (`repo:<r> filename:README.md`; a 0 for a repo that exists under
  its own name is only a note, and only when health passed — either the repo is
  not indexed, e.g. a low-star fork, or it has no README.md, e.g. README.rst).
  `repo`, `relatedRepos` and the report file name are shape-checked
  (`[A-Za-z0-9_.-]`; a repo segment of only dots, such as `../..`, is refused)
  because they reach shell commands and API paths. A planner's guessed
  must-hit of 0 is a note; a 403 is recorded as rate-limited, never as 0. A
  dependency agent must run the cross-direction NAME in its slot and question
  terms (never a repo name) in the other. A mandatory stage that did not run or
  did not succeed adds to `mandatoryGaps`; `statuses` lists every degraded
  state that applies and `status` is its head, so a mandatory gap is never
  hidden (#1513). A planner fan-out run that failed
  is listed in `fanoutGaps`; a link that will not fetch is a named gap
  (`mirrorGaps`) and is read live. A successful webclaw mirror records
  `route: "webclaw"`, `provisional: true`, webclaw's rc (0), and an empty
  reason; its README records that rc and route. `provisionalRoutes` names
  provisional mirrors and routes from planner and dependency manifests.
  Omitting both `repo` and `relatedRepos` is a
  mandatory gap. `repoRoot` (absolute) is required with `links` when
  `reportPath` is not under `<repo>/docs/`. The report slug is the path below
  `docs/` with `/` → `--` (so two `runs/<run>/report.md` never share a mirror
  directory; outside `docs/` it is the file name); a `.`/`..` path segment or a
  dot-only slug is refused.

  **Retrospect** (#1502) ends every run, early exits included: a READ-ONLY
  Explore agent records what was hard and proposes tuning, and a haiku writer
  saves it to `docs/research/kb/reports/agents/research-sweep-retrospect-<slug>.md`
  (beside the report when no repo root is known) — a proposal file only,
  never applied (tuning happens through a spec + PR). It never changes
  `status`; `retrospect.status` is `written`, `retrospect-null`, `write-null`,
  `write-failed`, `write-mismatch` (the writer REPORTED another path: the phase
  failed; a writer that writes elsewhere but reports the right path cannot be
  detected from the workflow) or `skipped` (`retrospect: false`).

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
   are usable here (`needs --repo` means usable once you pass `--repo` — never
   drop a github source for it). Always run `--sources
   github-issues,github-discussions,github-releases` against every dependency
   repo, save every link you were given with the mirror probe
   `mise run research-fanout -- --probe-out <p> --mirror-url <u> --mirror-path <f>`,
   and run a GitHub code search with its two controls (the mandatory stages
   above). Then run 1-3 query variants — short search terms, not
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
   `mise exec -- firecrawl scrape <url> --format markdown` (a bare `firecrawl`
   can resolve a stale PATH copy). For a question about what code
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

- **Absence claims are the easiest to get wrong.** "X does not use Y" must be
  confirmed by a second, independent route with a control term, and kept apart
  from "X's docs propose Y" and "a third party documents Y for X" (2026-09-29b:
  a one-route probe produced a true-but-misleading Omarchy headline). The
  workflow marks these `absence` and briefs their refuter to confirm them by a
  second route of a different kind; every refuter also judges
  misleading-by-omission, and a flagged claim is adjudicated one tier up.
  Status precedence: `verify-null`, `reconcile-null`, `mandatory-gap` (a
  mandatory stage did not run or did not succeed), `partial-verify` (some
  refuters null), then `links-only` / `stage-gap` (planner/fan-out/triage
  failed, with / without caller links; `stageGaps` names which, and the report
  states what was actually READ — caller links read, hits triaged from the
  planner or dependency-repo manifests, deep-read URLs, answered code-search
  rows), then `provisional` (a credit-exhausted provider was skipped or
  substituted); early exits `plan-null`, `no-manifests`, `triage-null`,
  `synth-null` stay degraded without adding `provisional`.
  `statuses` carries every one that applies. Anything but `complete` is degraded; even
  `complete` verifies only the first `verifyMax` load-bearing claims and
  says so in the report's Verification section.
- **Credit exhaustion stays visible.** A metered provider's HTTP 402, quota
  429 or "Insufficient credits" is `skipped: credits-exhausted`, or Firecrawl
  search is substituted by Serper (`SERPER_API_KEY`), then SerpApi
  (`SERP_API_KEY`); the mirror probe can substitute webclaw for scrape.
  These receipts pass **provisional**, and the report must name every entry
  in `provisionalRoutes`. Auth failures, 5xx, timeouts, malformed JSON, plain
  rate limits and GitHub errors remain failures and do not trigger fallback.
  Bare `firecrawl scrape`, including the deep-read step, has no fallback.
- **GitHub code search** (mandatory on every sweep): in-lane, `gh api -X GET
  search/code -f q='QUERY'` — no parentheses/`**`, 10 requests/min (a 403/429
  is a rate limit, not zero; the probe waits out a reset under 60 s once), and
  the tokenizer drops punctuation, so re-fetch and grep each hit. `foo OR bar`
  answered HTTP 200 with hits on 2026-10-02, so do not rely on the old "OR is a
  422" rule either way. Arm every zero with a same-shape query that must hit
  (recipe: the 2026-09-29b lane G GitHub-examples report).

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
