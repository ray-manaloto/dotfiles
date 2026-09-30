# GitHub search automation: storage, re-runs, and change tracking (2026-09-30)

User question (verbatim): *"are we storing this github searches so we can automate them and tune/refactor
them and get updates to find newer examples?"*

Synthesis node of `/research-sweep-run`. Inputs: 7 research-fanout manifests (listed under Provenance), the
triage hit list, the planner's code-search hits, and the direct probes this node ran on 2026-09-30.
Every probe below says which control arm it ran.

## Answer

**Partly. We store the raw results of each search, but we cannot yet automate, tune, or diff them over time.**

1. **What is stored today (shipped code).** `mise run research-fanout` writes one JSON file per source, the
   raw response bytes (with a sha256), and a `manifest.json` (`query`, `repo`, `generated_at`, `sources[]`). The
   default location is `.agent/kb/raw/research-fanout/<slug(query)>/`
   (`python/src/dotfiles_setup/research_fanout.py:1526-1528`).
2. **Three reasons it cannot track change over time:**
   - **Each re-run erases the previous snapshot.** `_persist` unlinks `manifest.json` and every
     `<source>.json`/`.raw` in the directory before it writes (`research_fanout.py:1326-1331`). The directory is
     keyed on the query slug, not a date, so running the same query again replaces the last result. Nothing
     keeps the history, so there is nothing to diff.
   - **The results are machine-local.** `.agent/` is gitignored (`.gitignore:124`, checked with
     `git check-ignore -v`). The snapshots don't survive a clone, and graphify never indexes them: 0 of 1,673
     graphify manifest entries are under `.agent/`, against 2 entries for `research_fanout.py` as the control.
   - **No query registry exists.** The queries live only in the planner's prompt output for each
     `research-sweep-run` workflow run. GitHub **code** search is not a research-fanout source: the workflow
     tells the planner to run `gh api -X GET search/code` itself (`.claude/workflows/research-sweep-run.js:195-199`)
     and hands `codeSearch` to the synthesis prompt and the workflow's return value
     (`research-sweep-run.js:212,219,298,400`). The workflow itself writes no file for it. *Qualification
     (verification, UPHELD misleading):* code-search queries and hit counts do persist indirectly, as prose in
     the tracked, graphify-indexed synthesis reports under `docs/research/kb/reports/agents/` (this report's
     E16/E17 are an example). What does not exist is a machine-readable, re-runnable query set.
3. **Best transport (recommended):** keep `gh api` (REST `/search/issues` and `/search/code`, GraphQL for
   Discussions) as the primary path. It is already a dependency, already authenticated, and already
   control-armed in research-fanout. Keep the firecrawl developer index as a complementary cross-repo source.
   Adopt an SDK (githubkit is the Python candidate) only if we need typed models or built-in throttling, and I
   did not verify that it provides them (see Gaps).
4. **Graphify helps with *retention and orientation*, not with *diffing*.** Its shipped work memory
   (`save-result --outcome useful|dead_end|corrected` plus `graphify reflect` → `LESSONS.md`) can record which
   queries paid off and which were dead ends. The graph already indexes the tracked reports under
   `docs/research/kb/reports/agents/` (864 manifest entries). Graphify is not a result store or a change
   detector. The dated snapshot and diff layer has to be ours.

## Evidence

Tags: **SHIPS** = in merged code or a release; **PROPOSES** = an open issue or unmerged PR; **3RD** = a third
party describing someone else's project; **MEASURED** = a probe this node ran today.

| # | Claim | Kind | Source | Quote / measurement |
|---|---|---|---|---|
| E1 | research-fanout persists per-source JSON + raw bytes + manifest | SHIPS | `python/src/dotfiles_setup/research_fanout.py:1317-1363` | `_write_json(out_dir / f"{result.source}.json", asdict(result))` … `"generated_at": datetime.now(UTC).isoformat()` |
| E2 | Re-running a query deletes the previous snapshot | SHIPS | `research_fanout.py:1326-1331` | `for name in owned_names: (out_dir / name).unlink(missing_ok=True)` |
| E3 | Default output is keyed on the query slug, not a timestamp | SHIPS | `research_fanout.py:1526-1528` | `repo_root / ".agent/kb/raw/research-fanout" / _slug(args.query)` |
| E4 | `.agent/` is gitignored | MEASURED | `.gitignore:124` | `git check-ignore -v` → `.gitignore:124:.agent/` |
| E5 | Fanout sources are issues/PRs, discussions, and releases. Code search is not one of them | SHIPS | `research_fanout.py:62-65,594,615` | `endpoint = f"/search/issues?q=repo:{repo}+{encoded}&per_page={request.limit}"` |
| E6 | Code search runs out of band in the workflow planner and is not written to disk as a structured artifact by the workflow (qualified: the synthesis node records queries and hits as prose in tracked reports) | SHIPS | `.claude/workflows/research-sweep-run.js:195-199,400` | `'GITHUB CODE SEARCH … gh api -X GET search/code -f q=…'`; `return { … plan, … }` |
| E7 | Spec: SHIPPED in #1391, stdlib only, injectable `Runner`/`Http` seams, empty results control-armed | SHIPS (spec of merged code) | `docs/specs/research-fanout.md` | "Status: SHIPPED in #1391 (squash `e5ac3324`, 2026-09-26)" |
| E8 | Rate-limit buckets: code_search 10, search 30, core 5000, graphql 5000 | MEASURED | `gh api rate_limit` | `{"code_search":10,"core":5000,"graphql":5000,"search":30}` |
| E9 | `gh search code` uses GitHub's *legacy* code-search engine | SHIPS (gh help text) + 3RD confirmation | `gh search code --help` line 6; https://github.com/cli/cli/issues/8522 (closed, completed) | "these search results are powered by what is now a legacy GitHub code search engine"; issue: "this search engine does not have API endpoints and thus we are using the legacy code search" |
| E10 | Asking for 1,000 code results trips a 403 | PROPOSES (open bug) | https://github.com/cli/cli/issues/10426 (open) | `"limit": 10, "used": 10, "remaining": 0` |
| E11 | gh reuses a cached introspection response that carries stale rate-limit headers | PROPOSES (open bug) | https://github.com/cli/cli/issues/12812 (open) | "cached **response** carries `X-Ratelimit-Remaining: 0`" |
| E12 | `gh skill search`, built on code search, is rate-limited into unusability | PROPOSES (open bug) | https://github.com/cli/cli/issues/13293 (open) | "the rate limit is hit almost immediately when using `gh skill`" |
| E13 | gh OAuth tokens get the 5,000-point/hour GraphQL limit; the issue asks GitHub to raise it | PROPOSES | https://github.com/cli/cli/issues/13433 (open) | "count against the standard authenticated-user GraphQL primary rate limit of **5,000 points per hour**" |
| E14 | Advanced issue-search support in gh | PROPOSES → **closed not_planned** | https://github.com/cli/cli/issues/10577 | state `closed`, `state_reason: not_planned` (measured) |
| E15 | gh does not auto-throttle the way octokit's plugins do | PROPOSES (a question in an issue) | https://github.com/cli/cli/issues/3292 | "does the CLI do something similar?" |
| E16 | Code search works through `gh api` and discriminates hits from misses | MEASURED | `gh api -X GET search/code` | `filename:research_fanout.py repo:ray-manaloto/dotfiles` → 2; a fresh bogus filename → 0 |
| E17 | PyGithub exposes `search_code` | MEASURED (code search) | `github/MainClass.py` in PyGithub/PyGithub | `"def search_code" repo:PyGithub/PyGithub` → 1 hit, `github/MainClass.py` |
| E18 | githubkit exposes the `/search/code` REST endpoint in its generated schemas, sync and async | MEASURED (code search) | `packages/githubkit-schemas-*/…/rest/search.py` | `"/search/code"` → 4 hits; `"async_code"` → 8 hits. (A first probe bounded to `path:githubkit/versions` returned 0; the path was wrong, not the feature missing) |
| E19 | Latest releases as of 2026-09-30 | MEASURED | `gh api repos/<r>/releases/latest` | cli/cli v2.102.0 (2026-09-30); githubkit v0.16.1 (2026-08-14); PyGithub v2.10.0 (2026-08-20); octokit.js v5.0.5 (2025-10-31); firecrawl/firecrawl v2.11.0 (2026-06-19); firecrawl/cli v1.25.1 (2026-09-30); Graphify-Labs/graphify v0.9.73 (2026-09-30). Control: a bogus repo → 404 |
| E20 | Firecrawl search and scrape surfaces can discover and run Alexandria providers | SHIPS (merged PR) | https://github.com/firecrawl/firecrawl/pull/4621 (merged 2026-09-12) | title "feat(api): provider discovery through Search and billed execution…"; `merged=true` |
| E21 | Exchange/alexandria provider discovery, retrieval, and billing | PROPOSES (open PR) | https://github.com/firecrawl/firecrawl/pull/4582 (open, unmerged) | "`alexandria` and legacy `exchange-providers` sources return ranked provider contracts" |
| E22 | Firecrawl search groups results by source and slices each group to `limit` independently | PROPOSES (open PR) | https://github.com/firecrawl/firecrawl/pull/4109 (open, unmerged) | "each group is sliced to the request's `limit` independently" |
| E23 | `x-firecrawl-session-id` correlation header | PROPOSES (open PR) | https://github.com/firecrawl/firecrawl/pull/3590 (open, unmerged) | "Adds session ID tracking across API endpoints" |
| E24 | Our firecrawl transports: the developer index is keyless and takes `k`; `firecrawl search` defaults to `web,alexandria` | SHIPS (our spec + a 2026-09-26 measurement) | `docs/specs/research-fanout.md` (sources table) | "the count param is `k` — `limit` is a 400"; "the CLI default `web,alexandria` returns the Alexandria tool catalog" |
| E25 | Graphify work memory: `save-result --outcome`, `graphify reflect` → `LESSONS.md` | SHIPS (CHANGELOG #1441, #1502, #114) | Graphify-Labs/graphify `CHANGELOG.md` lines 965, 1023, 1027-1028, 2014-2015; `.claude/skills/graphify/references/query.md:171-186` | "`graphify save-result` gains optional `--outcome useful\|dead_end\|corrected` and `--correction TEXT`" |
| E26 | Our work memory is empty: 0 session memories, and `graphify-out/memory/` does not exist | MEASURED | `graphify-out/reflections/LESSONS.md` | "0 useful · 0 dead ends · 0 corrected · 0 unmarked" |
| E27 | The graph already indexes the tracked agent reports and does not index `.agent/` | MEASURED | `graphify-out/manifest.json` | `docs/research/kb/reports/agents/` 864 entries; `.agent/` 0 entries (control: `research_fanout.py` 2 entries) |
| E28 | Graphify memory-note ignore rules (#3639), learning sidecar on query (#3043), memory budget (#3031), NeuG backend | PROPOSES (open PRs, absent from CHANGELOG) | https://github.com/Graphify-Labs/graphify/pull/3639, /pull/3043, /pull/3031 | all `open merged=false`. CHANGELOG grep for `#3639 #3637 #3043 #3011 #3031 #2267 #2272 NeuG` → 0 hits. Control: `#3957` → found, line 15 |
| E29 | Pinned graphify is 0.9.65. Latest release is 0.9.73 | MEASURED | `python/uv.lock:596-597` vs E19 | `name = "graphifyy"` / `version = "0.9.65"` |

## Conflicts resolved

1. **"Results are dated snapshots that let runs be compared" (a claim from an earlier lane) versus the code.**
   I trusted the **code**. The spec's manifest does carry `generated_at`, but `_persist` deletes the previous
   files and the directory is keyed on the query slug (E2, E3). One timestamped snapshot per query, overwritten
   on each run, is not a history. The earlier claim described what the manifest *could* support, not what ships.
2. **The planner's "graphify supports incremental update via NeuG MERGE, ignore rules for memory, and learning
   overlays on query" versus the merge state.** I trusted **merge state + CHANGELOG**. PRs #3639, #3043, and #3031
   are open and unmerged, and none of their numbers appears in the CHANGELOG (E28; the grep was armed with a
   known entry). Those are proposals. The *shipped* memory surface is `save-result` + `reflect` (E25). I kept the
   repo's standing caveat that `merged=false` does not always mean "didn't ship". The CHANGELOG check is the
   second route that settles it here.
3. **"Firecrawl supports Alexandria provider tools" came from open PR #4582. Merged PR #4621 says the same
   thing.** I trusted **#4621 (merged 2026-09-12)** as the shipping evidence. #4582's billing and
   extended-catalog details stay a proposal. Neither PR concerns *GitHub* search. Alexandria is a
   provider/tool catalog, which is why research-fanout pins `--sources web` (E24).
4. **"Firecrawl v2.11.0 is latest" versus the v2.12.0 drafted in PR 3974.** The `releases/latest` of
   firecrawl/firecrawl is v2.11.0 (2026-06-19). The CLI we actually pin is a separate repo, firecrawl/cli:
   v1.25.1 was released today, and the repo moved to v1.25.0 in `a5a9f786`. I report both and treat v2.12.0 as
   unreleased.
5. **"Graphify latest is v0.8.50" (triage) versus "v0.9.48" (PR text).** Both were stale. `releases/latest` is
   **v0.9.73** (2026-09-30). The fanout releases lane returned 3 items, which looks like a page or ordering
   limit, not the true latest. Pin currency belongs to `mise run graphify-upgrade`.
6. **Advanced issue search (#10577).** The claim read "becoming default September 4th 2025". The issue is now
   **closed as not_planned**. I trusted the current issue state. Whatever GitHub changed server-side, the gh CLI
   issue is not an open roadmap item.

## Verification

Five load-bearing claims went through an independent refuter (5 verdicts) and an adjudicator (Opus). The
critic and adjudicator both ran; none of the stages failed. No claim was refuted outright.

| # | Claim | Status | Evidence / adjudication |
|---|---|---|---|
| V1 | Re-running a query deletes the previous snapshot (`_persist` unlinks, slug-keyed dir), so no history to diff | **Confirmed** (refuter flagged it misleading; adjudicator overturned) | The refuter's omission is the `--out` flag. It does not change the conclusion: the only caller, `research-sweep-run.js:186`, never passes `--out`, and a reused `--out` dir is wiped the same way. A hand-picked dated `--out` is an unwired workaround, not retained history. Code confirmed at HEAD `a5a9f786` (introduced in #1391, `e5ac3324`, so deliberate). Control arm: same greps found the unlink loop, `_slug` and `--out`. |
| V2 | Snapshots live under gitignored `.agent/`, machine-local, not in the graphify corpus | **Confirmed** (adjudicator overturned the misleading flag) | `.gitignore:124` matched; manifest 1,673 keys, 0 start with `.agent/` (48 `.agent` substring hits are all `.agents/`). The alleged omissions (tracked spec, no scheduler) are already stated in Answer and Recommendation. |
| V3 | No tracked query registry; code search is not a fanout source; the workflow passes results only to the synthesis prompt and return value, never writing them to disk | **UPHELD as misleading** | Core is true (`_SOURCE_NAMES` has no code search; no registry file; `codeSearch` is in memory at `research-sweep-run.js:212`). **Omission:** "never writing them to disk" is too strong. Synthesis (lines 284-298) writes a report to `A.reportPath` using the hits; those reports are tracked under `docs/research/kb/reports/agents/` and graphify-indexed (10+ tracked reports mention `search/code`; this report's E16/E17 record exact queries and counts). Qualified in Answer point 2 and E6. Control arm: grep of this report hit E16/E17 lines; registry-term grep found only one unrelated cached file. Caveat: one `git log -S"github-code"` probe tested a single token spelling. |
| V4 | Buckets code_search 10/min, search 30, core 5000, graphql 5000; `gh search code` uses the legacy engine | **Confirmed** (adjudicator overturned the misleading flag) | Refuter re-measured 10/30/5000/5000 with shared ~60s reset for code_search and search. Help text line 6 says "legacy". The refuter wrongly said #8522 does not cover the legacy engine: a maintainer comment there says the new engine has no API endpoints so gh uses legacy (quoted in E9). Real residual caveat, already in Gaps: #8522 is closed and the fix was not read. Also relevant: legacy gh code search can silently drop matches beyond six per file (#8522 report), so automated results may be undercounted. |
| V5 | Graphify work memory (`save-result --outcome`, `reflect` to `LESSONS.md`) can retain which queries paid off; not a result store or diff engine; #3639, #3043, #3031 open/unmerged/absent from CHANGELOG; pin 0.9.65, latest v0.9.73 | **Confirmed** (adjudicator overturned the misleading flag) | PR states, CHANGELOG (0 hits for the three numbers, 3 for the known `#1441`) and `python/uv.lock:596-597` all check out. "Not a result store" means graphify does not store or diff GitHub search results; `save-result` does persist graphify's own Q&A under `graphify-out/memory/`. Minor, in the Conflicts section's grouping only: the `.graphify_learning.json` sidecar shipped in 0.9.3 (CHANGELOG line 948), #3031 is an unrelated RAM budget, #3639 concerns ignore rules. Latest v0.9.73 is inherited from the refuter's probe, not re-derived by the adjudicator. |
| V6 | All other table entries (E1-E5, E7-E29) | **Unverified** in this pass | Not individually re-probed by the verification stage; they rest on the synthesis node's own probes and sources. |

**How the conclusion changes.** The headline stands: raw results are stored, but nothing can be automated,
tuned or diffed over time. The only correction is scope. Code-search queries and hits are *not* lost: they
persist as prose in tracked reports, which is enough to re-find the examples by reading, but not to re-run,
tune or diff them. The missing piece is a machine-readable, re-runnable query registry and dated snapshots,
which is exactly what the Recommendation proposes. Nothing in the Recommendation depended on the claim that
code-search results never reach disk.

- **SDK throttling and retry behaviour is unverified.** Whether githubkit v0.16.1 or PyGithub v2.10.0
  automatically honour `Retry-After` / `X-RateLimit-Reset` for the search buckets was not read from source or
  docs. The octokit throttling claim (E15) is a user's question inside an issue, not documentation. No manifest
  covered these SDKs' docs or releases.
- **The official GitHub REST search docs were not fetched.** The 10/min code-search bucket is *measured* (E8).
  The documented query limits (the 1,000-result cap, the query-length cap, the lack of OR/parentheses in legacy
  code search) come from the workflow prompt's own notes (`research-sweep-run.js:196-198`), which is an
  in-repo claim, and were not re-verified against docs.github.com.
- **Completeness of `/search/code` compared with the web UI's new engine.** #8522 was closed "completed", but I
  did not read what the fix was. The gh help text still says "legacy" (E9). Whether a REST endpoint for the new
  engine exists now is unknown.
- **Firecrawl developer-index semantics.** Beyond our own transport notes (E24), no primary docs cover the
  index's coverage, freshness, ranking stability, or stable result identifiers. Those determine whether its
  results can be diffed run over run.
- **Other Claude or codex plugins with GitHub search.** The planner fetched nothing about them. Skills
  available in this session that touch GitHub content: `firecrawl:firecrawl-developer-index`, `exa:search`, and
  `last30days` (lists GitHub). None was evaluated for persistence or diffing.
- **Prior art for a tracked query registry plus snapshot diff.** No manifest searched for it.
- **The graphify releases lane.** It returned 3 releases while the latest is v0.9.73. Why it truncated
  (a sort order or page issue in `github-releases`) is unexplained, and it may be a research-fanout defect.
- **The planner's code-search hits were not independently re-fetched.** One of them,
  `githubkit search code language:python` → 262, is recorded with no top URLs. I re-probed the SDK surfaces
  myself instead (E17, E18).
- **Empty but control-armed results (they did answer "none").** These cover the queried terms, not the
  topics: `github-code-search-rate-limit` discussions and releases; `cli-github-search-firecrawl` and
  `cli-graphify` issues. The `cli-*` manifests pointed at `cli/cli` for non-gh topics, so they are noise, not
  coverage.

### Critic gaps (appended)

- **SDK throttle/retry behaviour never read** (githubkit v0.16.1, PyGithub v2.10.0; octokit throttling is only a
  question in cli/cli#3292). Next probe: read githubkit throttle/retry source and docs, PyGithub `GithubRetry`,
  and octokit plugin-throttling; confirm `Retry-After` / `X-RateLimit-Reset` handling on search and code_search.
- **Official GitHub REST search docs not fetched.** The 1,000-result cap, query-length and operator limits, and
  no-OR/parentheses for legacy code search rest on the workflow prompt's notes (`research-sweep-run.js:196-198`).
  Next probe: fetch docs.github.com search pages and run measured 1001+ page and OR probes with control arms.
- **REST endpoint for the new code-search engine, and the fix that closed cli/cli#8522, not read.** Next probe:
  read #8522 and its linked PR, check the GitHub changelog, and diff hit counts of `gh api search/code` against
  the web UI.
- **Firecrawl developer-index semantics** (coverage, freshness, ranking stability, stable IDs) rest on our own
  transport notes; alexandria/developer-index compared by PR titles only. Next probe: run the same query twice,
  24h apart, and diff URLs and ordering; check for stable IDs or `updated_at`.
- **Other plugins/skills with GitHub search not evaluated** (exa:search, last30days GitHub source, `gh skill
  search`, the GitHub MCP server); marketplaces not searched. Next probe: capability matrix with a control arm.
- **No prior-art search for a registry-plus-diff tool or GitHub-native watchers** (saved searches, Atom feeds,
  watch-releases, notifications). Decide build-versus-adopt before writing `research-watch`.
- **Graphify claims not run.** `save-result`/`reflect` were read from the CHANGELOG, not executed, and our memory
  is empty (E26); token savings of a committed digest were not measured; the 0.9.65 to 0.9.73 CHANGELOG was not
  read for memory or ignore-rule changes.
- **Graphify releases lane returned 3 items while latest is v0.9.73**; cause (sort, page size, or fanout defect)
  unexplained and could truncate "new release" detection in a watch feature. Next probe: compare
  `releases?per_page=30` with the `github-releases` endpoint and limit.
- **Planner code-search hits not re-fetched** (`githubkit search code language:python` returned 262 with no top
  URLs), and the registry design is untested against real 403/429 secondary-rate-limit behaviour or 10/min
  pacing; only one `rate_limit` snapshot exists. Next probe: 15-query burst recording 403/429 and `Retry-After`.

## Recommendation

Build it downward (skill → mise task → python), reusing research-fanout instead of starting a parallel tool
(per `use-tool-builtins.md` and `mise-tasks-only.md`).

1. **Tracked query registry: `research-queries.toml` at the repo root**, a sibling of `currency.toml` and
   `rule-sync.toml`. One `[[query]]` per stable `id`, with `question`, `repo`, `sources`, `limit`, an optional
   `code = ["filename:… repo:…", …]` (one legacy query per alternative, since there is no OR), `cadence`, and
   `tags`. Tuning a query then means editing a line in review. A renamed query keeps its `id`, so its history
   survives the rename.
2. **Add `github-code` as a research-fanout source.** Use `gh api -X GET search/code`, give it its own
   ≤10/min pacing, and treat a 403 as a rate limit, never as zero results. Control arm: the repo's own
   `filename:` canary. This brings code search inside the same persistence, sha256, and control-arm contract
   as every other source (fixes E6).
3. **Dated snapshots instead of overwrites.** Keep the raw bytes gitignored at
   `.agent/kb/raw/research-fanout/<id>/<UTC-stamp>/`: they are large, and `.agent/` keeps secret-scan exposure
   low. Remove the unlink-then-write overwrite (E2) only on that registry path, so ad-hoc runs keep today's
   behaviour.
4. **Tracked, normalized index plus diff.** Write one line per item to
   `docs/research/kb/watch/<id>.jsonl`, keyed on the canonical URL, with state/merged/updated_at/tag/title-hash.
   A `research-watch` module diffs the latest snapshot against the previous one and reports **added**,
   **changed** (state, merged, new release, or updated_at moved), and **dropped from the top-N**.
   Classify an item as **deleted** only after a direct `GET` returns 404/410. Falling out of a ranked,
   limit-bounded search result is not deletion (`probes-need-a-control-arm.md` rule 3: a bound turns
   "absent" into "unreachable").
5. **Scheduling reuses the existing pattern.** A scheduled GHA job runs `mise run research-watch` and upserts a
   standing issue, as `refresh.yml` does for `tool-currency`. This uses the platform's native scheduling and
   issue upsert and adds no poller.
6. **Graphify gets the digest and the outcomes, not the raw JSON.** Commit a short markdown digest per watch
   run under `docs/research/kb/`. That tree is already in the graph corpus (E27), so
   `mise run graphify-query` can answer "what did the X watch find" without loading snapshots into context.
   After each synthesis, record `save-result --outcome useful|dead_end` for the registry query. `LESSONS.md`
   then tells the next agent which queries to reuse and which to skip (E25, E26). Do not graphify the raw
   `.raw`/`.json`: it would flood the graph with noise nodes. Bump graphify 0.9.65 → 0.9.73 through
   `mise run graphify-upgrade` first (E29).
7. **Transport choice.** Keep `gh api`. Revisit githubkit only if item 2's pacing or GraphQL pagination grows
   past a thin wrapper, and resolve the SDK throttling gap before relying on it. Keep the firecrawl developer
   index as a recall-widening, keyless cross-repo source. Keep `--sources web` so the Alexandria catalog stays
   out of GitHub research.

## Provenance

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| triage | Explore | sonnet | low |
| read:1/2 | Explore | haiku | (default) |
| read:2/2 | Explore | haiku | (default) |
| synthesize | general-purpose | opus | high |
| refute:1/5 | general-purpose | sonnet | medium |
| refute:2/5 | general-purpose | sonnet | medium |
| refute:3/5 | general-purpose | sonnet | medium |
| refute:4/5 | general-purpose | sonnet | medium |
| refute:5/5 | general-purpose | sonnet | medium |
| critic | Explore | sonnet | medium |
| adjudicate | general-purpose | opus | high |
| reconcile | general-purpose | sonnet | medium |

No stage failed (failed stages: none).

Manifests read (all `.agent/kb/raw/research-fanout/<dir>/manifest.json`, generated 2026-09-30 15:03 local):
`github-code-search-rate-limit` (cli/cli: issues ok 10, discussions empty_verified, releases empty_verified,
firecrawl-developer ok 10); `firecrawl-github-search-cli` (firecrawl/firecrawl: issues 10, releases 4,
firecrawl-developer 10); `cli-github-search-firecrawl` (cli/cli: issues empty_verified, firecrawl-developer 10);
`graphify-memory-cli` (Graphify-Labs/graphify: issues 10, releases 3, firecrawl-developer 1); `cli-graphify`
(cli/cli: issues empty_verified, firecrawl-developer 10); `dotfiles-research-search-cli` (ray-manaloto/dotfiles:
issues 10, firecrawl-developer 1); `cli-dotfiles` (cli/cli: issues 10, firecrawl-developer 10). None had
`empty_unverified` or `error` sources. No failed reads.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): research_fanout.py, the sweep workflow, the spec, .gitignore, graphify-out state
- [cli/cli](https://github.com/cli/cli): code-search rate limits, legacy engine, cached rate-limit headers, advanced issue search, latest release
- [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl): Alexandria provider PRs (#4621 merged, #4582 open), grouped search results, session header, latest release
- [firecrawl/cli](https://github.com/firecrawl/cli): latest CLI release v1.25.1
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify): work-memory CHANGELOG entries, open memory/NeuG PRs, latest release v0.9.73
- [PyGithub/PyGithub](https://github.com/PyGithub/PyGithub): `search_code` surface, latest release
- [yanyongyu/githubkit](https://github.com/yanyongyu/githubkit): `/search/code` in generated schemas, latest release
- [octokit/octokit.js](https://github.com/octokit/octokit.js): latest release; throttling mention (weak, unverified)
