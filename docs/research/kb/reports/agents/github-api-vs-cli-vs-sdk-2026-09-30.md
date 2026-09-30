# GitHub research automation: gh CLI vs REST/GraphQL vs SDK (2026-09-30)

Synthesis node of a research-fanout DAG. Inputs: the claims JSON, the triage hit list, the
code-search results and the 13 fanout manifests under `.agent/kb/raw/research-fanout/`. The
synthesizer re-ran the load-bearing claims itself, against `gh` 2.101.0 on the host, three
docs.github.com article bodies, and the githubkit and go-github source at their latest release tags.
Every claim tagged **[re-probed]** was re-derived in this node. Claims without that tag are
**inherited** from the read lanes and are not re-measured.

## Answer

**Use a hybrid. Keep `gh` for one-off human and agent lookups. Build the scheduled watch loop in
Python on top of the REST and GraphQL APIs, with githubkit as the client. Do not prefer PyGithub (it
is unmaintained-leaning and its GraphQL support is thin, but it is NOT REST-only; see Verification). Do not
treat any SDK as a way around the search limits: those limits are server-side, and no client can lift
them.**

1. **The hard limits are in the API, not the client.**
   - REST search returns at most 1,000 results per query. It also searches at most 4,000 matching
     repositories. **[re-probed]**
   - `/search/code` is limited to 10 requests per minute. The live response header reads
     `X-Ratelimit-Resource: code_search`, limit 10. **[re-probed]**
   - Code search covers only the default branch and files under 384 KB. **[re-probed]**
   - A timed-out query returns partial results with `incomplete_results: true`. **[re-probed]**
   - The gh CLI's own help text says the API serves a **legacy** code search engine: "new features
     like regex search are not yet available via the GitHub API". **[re-probed]**

   So no SDK exposes the new code search engine. The REST docs page itself does not use the word
   "legacy". That statement is gh's claim, and GitHub ships it.
2. **What `gh` does not expose, measured against gh 2.101.0.** The latest release is v2.102.0,
   published 2026-09-30; these probes did not re-run against it.
   - **Conditional requests are manual only.** `gh api -H 'If-None-Match: <etag>'` gets
     `304 Not Modified`, and gh then **exits rc=1**. A bogus ETag gets `200` (the control arm). So a
     caller must parse the status line, not the exit code. **[re-probed]**
   - `--cache` is a TTL response cache (`"3600s"`), not ETag revalidation. **[re-probed]**
   - There is no automatic secondary-rate-limit retry. cli/cli#3292 ("Does the CLI honor response
     headers for throttling and ratelimits?") is still **open**. **[re-probed state]**
   - `gh search code` has no discussions search. `gh search` offers only
     code/commits/issues/prs/repos. **[re-probed]**

   `gh` *does* expose several things one inherited claim denied:
   - `gh discussion` exists (preview) with create/list/view/comment/edit.
   - `gh search issues --search-type {lexical|semantic|hybrid}` exists.
   - The `--search` flag accepts advanced issue syntax. **[re-probed]**
3. **SDKs: what they ship and what they lack.**
   - **githubkit v0.16.1** (third-party, Python) covers REST and GraphQL. **[re-probed from source at
     v0.16.1]**
     - Auto-retry is on by default: `auto_retry=True` → `RETRY_DEFAULT` = rate-limit retry plus
       server-error retry.
     - It raises typed `PrimaryRateLimitExceeded` / `SecondaryRateLimitExceeded` exceptions carrying
       `retry_after`. The rate-limit retry defaults to `max_retry=1`, modelled on octokit.js.
     - It has a `LocalThrottler(100)` concurrency cap, a `Paginator`, and a hishel-backed HTTP cache.
   - **go-github v92.0.0** is REST only. It exposes typed `AbuseRateLimitError` (secondary limit)
     handling. It delegates ETag caching to a caching `http.Transport` (inherited from the README).
     It **defaults** to API version 2022-11-28 and allows up to 2026-03-10. **[re-probed from
     source]**
   - **githubv4** is Go GraphQL only, with manual pagination and no rate-limit section (inherited).
   - **octokit.js v5.0.5** is official. It bundles REST, GraphQL, throttling (primary and secondary,
     retry once) and pagination. Its README never mentions ETags (inherited absence). It is
     JavaScript, not this repo's Python stack.
   - **PyGithub v2.10.0** has mainly REST coverage, and its README says it is "actively seeking
     maintainers". An earlier draft called it "REST only"; that was **struck** (REFUTED in
     Verification): `Requester.graphql_query` and related methods exist in source. Its GraphQL
     coverage is thinner than githubkit's typed GraphQL support. Do not prefer it, for maintainer risk
     and thinner GraphQL coverage, not for lacking GraphQL.
4. **The loop** (see Recommendation) runs in this order:
   1. The `research-sweep` skill.
   2. `mise run github-watch` (new).
   3. `python/src/dotfiles_setup/github_watch.py` (new), which uses githubkit and reads a
      declarative `watches.toml`.
   4. It runs on demand and on the existing `refresh.yml` schedule.

   For dependency currency, a new release is detected by an **ETag-conditional** releases poll.
   ETags work on `releases`; search endpoints return none, measured below. Release notes are then
   reviewed, and a human-approved diff registers each adopted feature as a watch query.

## Evidence

| Claim | URL or file:line | Quote |
|---|---|---|
| The official list is octokit.js/.rb/.net plus Terraform only **[re-probed]** | https://docs.github.com/en/rest/using-the-rest-api/libraries-for-the-rest-api?apiVersion=2026-03-10 (article body lines 17-20) | "JavaScript: octokit.js … Ruby: octokit.rb … .NET: octokit.net … Terraform: terraform-provider-github" |
| Third-party libraries are not maintained by GitHub | same page | "These third-party libraries are not maintained by GitHub." |
| PyGithub and githubkit are listed third-party (Python); go-github is third-party (Go); githubv4 is absent **[re-probed: lines 44, 88, 93; grep `githubv4` = 0, control `githubkit` hit]** | same page | "go-github: google/go-github" / "PyGithub: PyGithub/PyGithub" / "githubkit: yanyongyu/githubkit" |
| The API code search is the legacy engine; regex is not in the API **[re-probed]** | `gh search code --help` (gh 2.101.0), lines 6-8 | "these search results are powered by what is now a legacy GitHub code search engine … new features like regex search are not yet available via the GitHub API." |
| 1,000-result cap **[re-probed]** | https://docs.github.com/en/rest/search/search (body line 7) | "the GitHub REST API provides **up to 1,000 results for each search**." |
| 4,000-repository scope cap **[re-probed; not in any inherited claim]** | same page, "Search scope limits" | "The REST API will find up to 4,000 repositories that match your filters and return results from those repositories." |
| Code search is limited to 10/min, the default branch, and files under 384 KB **[re-probed]** | same page, lines 18, 188-192 | "Only the default branch is considered … Only files smaller than 384 KB are searchable … limits you to 10 requests per minute." |
| Live code-search budget header **[re-probed]** | `gh api -i 'search/code?q=research_fanout+repo:ray-manaloto/dotfiles'` | `X-Ratelimit-Limit: 10` / `X-Ratelimit-Resource: code_search` |
| Timeouts produce `incomplete_results` **[re-probed]** | same page, line 70 | "the response has the `incomplete_results` property set to `true`." |
| Text-match fragments via media type **[re-probed]** | same page, lines 87-92 | "specify the `text-match` media type in your `Accept` header … application/vnd.github.text-match+json" |
| REST issue search supports `advanced_search` and `search_type` (semantic/hybrid, 10/min) **[re-probed]** | same page, lines 723-735 | "Semantic and hybrid search require authentication and are rate limited to 10 requests per minute." |
| ETag conditional GETs: a 304 does not count against the primary limit **[re-probed]** | https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api (line 56) | "Making a conditional request does not count against your primary rate limit if a `304` response is returned" |
| Search endpoints return no ETag; releases and repos do **[re-probed, n=1 each, control-armed]** | `gh api -i` ETag header count | `repos/ray-manaloto/dotfiles: 1`, `repos/cli/cli/releases: 1`, `search/issues?…: 0` |
| gh passes a manual If-None-Match; 304 exits rc=1 **[re-probed]** | `gh api -i -H "If-None-Match: $etag" repos/cli/cli/releases?per_page=1` | `rc=1` / `HTTP/2.0 304 Not Modified`; bogus-etag control → `HTTP/2.0 200 OK` |
| gh `--cache` is a TTL cache **[re-probed]** | `gh api --help` line 65 | "--cache duration  Cache the response, e.g. \"3600s\", \"60m\", \"1h\"" |
| gh `--paginate`/`--slurp` for REST and GraphQL **[re-probed]** | `gh api --help` lines 51-55 | "For GraphQL requests, this requires that the original query accepts an `$endCursor: String` variable" |
| Secondary limits **[re-probed]** | https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api (lines 66-67, 113) | "No more than 900 points per minute are allowed for REST API endpoints, and no more than 2,000 points per minute … for the GraphQL API"; "If the `retry-after` response header is present, you should not retry your request until after that many seconds" |
| `gh discussion` exists (preview) **[re-probed; refutes an inherited claim]** | `gh help` line 10; `gh discussion --help` | "discussion:    Work with GitHub Discussions (preview)"; control `gh qzvbogus` → "unknown command" |
| gh search has no discussions category **[re-probed]** | `gh search --help` lines 32-36 | "code … commits … issues … prs … repos" |
| gh issue search supports semantic/hybrid **[re-probed]** | `gh search issues --help` line 56 | "--search-type string  Type of issue search to perform: {lexical\|semantic\|hybrid}" |
| gh has no auto throttling (open question upstream) **[re-probed state]** | https://github.com/cli/cli/issues/3292 | state `open`: "Does the CLI honor response headers for throttling and ratelimits?" |
| `gh search code --limit 1000` still hits 403 secondary limits **[state re-probed: open]** | https://github.com/cli/cli/issues/10426 | "When running a `gh search code` query with a limit of 1000, I get a 403 rate limit" |
| Code search suffers rate-limit starvation in gh's own features | https://github.com/cli/cli/issues/13293 | "the rate limit is hit almost immediately when using `gh skill`" |
| githubkit default retry covers the rate limit **[re-probed, v0.16.1]** | yanyongyu/githubkit `githubkit/retry.py:80`, `config.py:98-103` | `RETRY_DEFAULT = RetryChainDecision(RETRY_RATE_LIMIT, RETRY_SERVER_ERROR)`; `if auto_retry is True: return RETRY_DEFAULT` |
| githubkit types the primary and secondary limits separately **[re-probed]** | `githubkit/exception.py:74-93` | `class PrimaryRateLimitExceeded(RateLimitExceeded)` / `class SecondaryRateLimitExceeded(RateLimitExceeded)` |
| githubkit retries once, modelled on octokit.js **[re-probed]** | `githubkit/retry.py:14-19` | "def __init__(self, max_retry: int = 1) … # retry once for rate limit exceeded … octokit.js" |
| githubkit throttler default is 100 concurrent **[re-probed]** | `githubkit/config.py:95` | `return throttler or LocalThrottler(100)` |
| githubkit README features **[re-probed]** | https://github.com/yanyongyu/githubkit README lines 57-61 | "Calling REST API and GraphQL easily … Built-in pagination support … Built-in http cache (powered by Hishel …) and auto retry" |
| githubkit search-model validation bug (fixed) **[state re-probed: closed 2026-04-13]** | https://github.com/yanyongyu/githubkit/issues/293 | "Repo search results missing `has_downloads` field … ValidationError" |
| PyGithub is short of maintainers (README L68). **"REST-only" REFUTED**: the README says only "a Python library to access the GitHub REST API" (silence, not absence); `github/Requester.py` defines `graphql_query` (L733) and POSTs to a `graphql_url` | https://github.com/pygithub/pygithub | "We're actively seeking maintainers that will triage issues and pull requests and cut releases." |
| go-github is REST-only; recommends githubv4 for GraphQL (inherited) | https://github.com/google/go-github | "If you're interested in using the GraphQL API v4 … the recommended library is shurcooL/githubv4" |
| go-github secondary-limit error type (inherited) | same | "check if the error is an `AbuseRateLimitError`" |
| go-github delegates ETags to the transport (inherited) | same | "`go-github` does not handle conditional requests directly, but is instead designed to work with a caching `http.Transport`." |
| go-github API version: default 2022-11-28, max 2026-03-10 **[re-probed, v92.0.0]** | google/go-github `github/github.go:43-44, 572-574` | `apiVersionDefault: api20221128, apiVersionMin: api20221128, apiVersionMax: api20260310` |
| githubv4 is GraphQL codegen with manual auth (inherited) | https://github.com/shurcooL/githubv4 | "Support all of GitHub GraphQL API v4 via code generation from schema." / "does not directly handle authentication" |
| octokit org metadata (inherited) | https://github.com/octokit | "Official clients for the GitHub API" |
| octokit.js throttling covers both limits (inherited) | https://github.com/octokit/octokit.js | "requests are retried once and warnings are logged in case of hitting a rate or secondary rate limit." |
| octokit.js README has no ETag mention (inherited ABSENCE, control-armed by the read lane) | same | grep `etag\|conditional` matched only "conditional exports" |
| GitHub's generated SDKs exist but are not on the libraries page **[re-probed]** | https://github.com/octokit/go-sdk (pushed 2026-05-08, tag v0.0.30), https://github.com/octokit/dotnet-sdk (pushed 2025-03-15); blog https://github.blog/news-insights/product-news/our-move-to-generated-sdks/ (inherited) | "A generated Go SDK from GitHub's OpenAPI specification. Built on Kiota" |
| Latest versions **[re-probed 2026-09-30]** | `gh api repos/<r>/releases/latest` | githubkit v0.16.1 (2026-08-14); PyGithub v2.10.0 (2026-08-20); go-github v92.0.0 (2026-09-14); octokit.js v5.0.5 (2025-10-31); cli/cli v2.102.0 (2026-09-30); plugin-throttling.js v11.0.5 (2026-08-01); go-sdk and githubv4 have no GitHub releases (404) |
| GraphQL `ISSUE_ADVANCED` search type (inherited, changelog) | https://github.blog/changelog/2025-03-06-github-issues-projects-api-support-for-issues-advanced-search-and-more/ | "use the ISSUE_ADVANCED type to perform searches with the AND and OR keywords and nested searches" |
| Discussions and projects are GraphQL-only (inherited) | https://docs.github.com/en/rest/about-the-rest-api/comparing-githubs-rest-api-and-graphql-api | "Some GitHub data and operations are only accessible through the GraphQL API (such as discussions, projects…)" |
| The repo's fanout already uses gh subprocesses **[re-probed]** | `python/src/dotfiles_setup/research_fanout.py:79-81, 594-596` | `"github-issues": ("gh api REST", …)`; `endpoint = f"/search/issues?q=repo:{repo}+{encoded}&per_page={request.limit}"` |
| githubkit and PyGithub are not current dependencies **[re-probed]** | `python/uv.lock` | `grep -ci '^name = "(githubkit\|pygithub)"'` = 0; control `httpx` = 1 |

## Conflicts resolved

1. **"gh has no `gh discussion` subcommand"** (claims JSON, cited to an issues-search URL) vs the
   binary. **Trusted the binary.** gh 2.101.0 lists `discussion` (preview) with
   create/list/view/comment/edit. A bogus subcommand prints "unknown command", so the probe
   discriminates. Both exit rc=0, so it was the text that discriminated, not the rc. The
   narrower true claim is that there is no **`gh search discussions`**.
2. **go-github API version.** The README table ends at `92.0.0 | 2022-11-28`, which suggested it
   cannot speak 2026-03-10. The v92.0.0 source sets default 2022-11-28 and max 2026-03-10.
   **Source wins.** 2026-03-10 behavior is opt-in, not the default.
3. **"docs list go-sdk / generated Go SDKs as official"** (claim 38) vs the fetched libraries page,
   which lists octokit.js/.rb/.net plus Terraform only. **Trusted the page for "official list"**. The
   generated SDKs exist as octokit-org repos and a blog announcement: GitHub ships them, but the
   libraries page does not list them. These are two distinct claims.
4. **"gh api supports conditional requests"** (claim 40). **Partly true.** A manual
   `-H If-None-Match` works, but the 304 exits rc=1. `--cache` is TTL-only. There is no automatic
   ETag handling. Measured.
5. **cli/cli#11029 was inverted in the claims JSON.** Its own quote says `--extension` works in the
   CLI and fails with `--web`. The claim said the reverse. **Trusted the quote.** The issue is closed
   (completed, 2025-07-17).
6. **"The 1,000 cap is a gh limitation"** (cli/cli#9734, closed completed 2024-10-14) vs the REST
   docs. The cap is **server-side** per query, so no gh pagination change or SDK can exceed it. The
   only way past it is query partitioning, which is a design proposal and not measured.
7. **"The REST code search API returns only the first match, with up to five fragments"** (claim
   36). The quote is **not present** in the current REST search page: grep for
   `five fragments|first match` returned 0, while the control `text-match` hit. The claim is treated
   as unverified or outdated. What the current page says is that fragments carry offsets
   (line 87). cli/cli#8522 (the six-match truncation) is closed as completed (2024-01-08); how it was
   fixed was not read.
8. **Query limits (256 chars, five boolean operators)** come from the **GHES 3.13** troubleshooting
   page, an older product version. They are not verified for github.com today. Treat them as a gap.
9. **"GraphQL does not support ETags; cache results yourself keyed by the query hash"** (claim 55).
   The quoted wording was **not verified** on the cited page. Treat it as unverified. The design
   below does not depend on it.
10. **"GitHub recommends SDKs over direct API calls for pagination and rate limits"** (claim 51). The
    quote attached to it only says GitHub maintains libraries. **Unsupported. Dropped.**
11. **Third-party blogs** (medium.com, fixdevs.com, computingforgeeks.com) are third-party claims
    about GitHub. They were kept out of the Answer and out of the load-bearing claims.

## Gaps

These are unknowns, not "nothing found".

- **Fanout targeting defect.** The `githubkit`, `octokit-js`, `go-github`, `githubv4`, `pygithub`
  and `dotfiles` fanouts queried **repo cli/cli**, so their issue, discussion and release lanes
  returned cli/cli noise, not SDK-repo data (triage `unverifiedEmpty`). SDK-repo issue coverage is
  therefore limited to the `cli-*` fanouts, which did target the SDK repos.
- The fanout had **no hit on the GitHub REST code-search docs, octokit plugin-throttling, or ETag
  behavior**. This node filled the docs part by fetching docs.github.com directly. **plugin-throttling
  source and octokit.js ETag behavior in source were not read.** The octokit.js ETag absence rests on
  the README only.
- `code-search-api/context7` returned r-lib/cli (R) noise. Its content for this question is unknown.
- The planner code-search query `is:issue repo:cli/cli "search/code"` returned 0 because the
  qualifier is invalid for code search. **The internals of gh's `search code` are not
  characterized**, apart from one hit on `search.go`.
- The `empty_verified` lanes (control-armed empties) were cli-pygithub, cli-githubkit, cli-go-github,
  cli-githubv4 and cli-octokit-js releases, githubkit issues and discussions, octokit-js discussions,
  and cli-dotfiles releases. These are real empties for those queries only.
- **Not read:**
  - whether githubkit's hishel cache revalidates with ETags or only by TTL;
  - whether githubkit's retry honors `retry-after` for secondary limits beyond one retry;
  - octokit.rb and octokit.net;
  - octokit/go-sdk rate-limit behavior;
  - GraphQL `search(type: DISCUSSION)` availability (the discussions-search route is proposed, not
    verified);
  - Projects v2 advanced-search API support.
- **Query-partitioning to beat the 1,000 cap** (sharding by `language:`, `path:`, `filename:`,
  `user:`/`org:`, or `size:`) is proposed and not measured. Whether the legacy engine honors each
  qualifier was not probed.
- The ETag-absence-on-search measurement is n=1 per endpoint (code search was not header-counted for
  ETags separately; issues search was). The noise floor is unknown.
- The gh probes ran on 2.101.0. **v2.102.0 (released today) was not probed.**
- **Failed reads:** none were reported by the harness.
- **Critic gaps (verification step):**
  - gh v2.102.0 (2026-09-30) not probed; all gh claims rest on 2.101.0. Next: re-run
    `gh api -i -H If-None-Match`, `gh api --help`, `gh search --help`, `gh discussion --help` on
    2.102.0 and read its release notes.
  - The new (non-legacy) code search engine's API exposure rests on gh help text only; GitHub docs and
    changelog were not checked for a newer code-search API or regex support. Next: grep the REST
    code-search and search-syntax docs and github.blog/changelog; introspect GraphQL `search(type:)`.
  - githubkit hishel cache (ETag revalidation vs TTL only) and retry-after handling beyond
    `max_retry=1` are unread. Next: read githubkit cache and retry tests at v0.16.1; run a live
    conditional GET through githubkit and count 304s.
  - GraphQL `search(type: DISCUSSION)`, `ISSUE_ADVANCED`, and "GraphQL has no ETag" are unverified;
    the discussions lane depends on them. Next: run them via `gh api graphql` and inspect headers.
  - Query-partitioning to beat the 1,000 cap is proposed, not measured; whether the legacy engine
    honors `language:`, `path:`, `filename:`, `size:`, `user:`, `org:` sharding is unknown, as are
    current github.com 256-character and boolean limits (source is GHES 3.13). Next: run sharded
    queries, compare the union to `total_count`, check `incomplete_results`.
  - octokit.js ETag/throttling rests on the README only; plugin-throttling.js source, octokit.rb,
    octokit.net and octokit/go-sdk were not read. Next: read plugin-throttling.js v11.0.5 and grep
    for `if-none-match`/`etag`.
  - ETag absence on search is n=1 and code search was not header-counted. Next: 5 runs each of
    search/code, search/issues, search/repositories counting ETag and Last-Modified, with a repos
    control.
  - Text-match: the "first match, up to five fragments" wording is absent from the current page, and
    the fix for cli/cli#8522 is unread. Next: run the text-match Accept header on `search/code` and
    inspect `text_matches`.
  - Nothing shows `github-watch`, `watches.toml` or `github_watch.py` fit repo conventions;
    `dependency_currency.py`, `currency.toml` and `refresh.yml` were cited but not read here, and
    release-note fix-vs-feature classification has no measured example. Next: read those files and
    prototype one release poll end to end through the 304 path.
  - SDK-repo issue health (maintainer activity, known rate-limit bugs) is absent because of the
    fanout targeting defect. Next: re-run fanouts against yanyongyu/githubkit, PyGithub/PyGithub and
    octokit/octokit.js for "rate limit", "secondary", "etag", "search".
  - The Terraform provider README and Projects v2 search/filter support were not read.

## Recommendation

**Client choice.**

- Keep `gh` for ad-hoc lookups and for the existing `research-fanout` lanes. They already shell out
  to `gh api` (`research_fanout.py:79-81`).
- Adopt **githubkit** for a new scheduled watch engine. It is the only Python client in scope that
  covers REST and GraphQL and ships default rate-limit retry, typed secondary-limit exceptions, a
  concurrency throttler, a paginator and an HTTP cache. It tracks the OpenAPI schema.
- Its risks:
  - It is third-party and pre-1.0 (v0.16.1).
  - Its schema validation has broken on search payloads before (#293, now fixed). Read raw JSON for
    search and don't rely on `parsed_data`.
  - It is a new dependency, so the tool-currency rule applies. Add it to `currency.toml`.
- Do not prefer PyGithub: the README appeals for maintainers and its GraphQL coverage (a
  `Requester.graphql_query` path exists) is thinner than githubkit's. The earlier "REST only"
  rationale was refuted and is struck.
- Octokit.js is the official reference design but the wrong language for `python/`.
- Auth: read a token from the environment (`GH_TOKEN`/`GITHUB_TOKEN`; CI provides one). **Do not**
  call `gh auth token` or `fnox get` from a scheduled path (the keychain hang risk in
  `secrets-out-of-the-shell-env.md`), and print presence only.

**The loop.** It follows skill → mise task → Python, with zero bash logic.

1. **Research.** The `research-sweep` skill (judgment) runs `mise run research-fanout` to collect
   evidence, then synthesizes, as it does today.
2. **Keyword searches.** A new `watches.toml` declares each standing query as a reviewed diff. Each
   entry has `id`, `kind ∈ {code, issues, discussions(graphql), releases}`, `q`, `origin` (a topic,
   or `dep@version:feature`), `added`, and optional `shards` for partitioning.
3. **Merge and refine.** `github_watch.py` runs each query:
   - It sends `Accept: application/vnd.github.text-match+json` to get fragments.
   - It dedupes by `(repo, path, sha)` for code and by `node_id` for issues.
   - It records `incomplete_results` and `total_count > 1000` as **truncated**, never as complete.
   - It proposes a refined filter (added qualifiers or shards) as a diff for human review. It does
     not auto-edit.
4. **Budget.** Run code queries sequentially at 10 per minute or fewer, honor `retry-after`, and back
   off exponentially per the rate-limit doc. A run with N code queries takes at least N/10 minutes;
   the task should print that estimate up front.
5. **Detect new examples.** Diff against a seen-set state file. Put it in `.agent/state/` for local
   runs; in CI, persist it as the issue body or an artifact, as `refresh.yml` already does for the
   currency report. Emit only new hits.
6. **Surfaces.**
   - `mise run github-watch` for on demand.
   - A job in the existing daily `refresh.yml` for the schedule, which upserts one standing issue.
   - A `verify` contract that asserts the skill↔task↔module↔test chain, like
     `workflow.tool-currency-wiring`.

**Dependency currency, the same loop.**

- For each deep-tracked tool in `currency.toml` with a `github =` key, poll
  `repos/<r>/releases?per_page=N` with **`If-None-Match`**. This was measured to return an ETag, and a
  304 is free against the primary limit.
- On change, fetch the release body. Classify each item as fix or feature, and as applicable to us or
  not, as a *judgment* step in the skill. Only a human decides adoption and retirement
  (`tool-currency-and-native-first.md`).
- Register each adopted feature as a `watches.toml` entry with `origin = "<tool>@<ver>:<feature>"`,
  in a reviewed diff. Later runs then surface real-world adopters via code search.
- Latest versions only: the release poll reads `releases/latest` plus newer tags, never backfills old
  majors.

## Verification

Verification ran (critic and adjudicator both ran; no stage failed). Load-bearing claims:

| Claim | Status | Evidence and qualification |
|---|---|---|
| API code search is the legacy engine (no regex); REST search capped at 1,000 results and 4,000 repos; code search 10/min | **Confirmed** | gh help text, REST docs lines 7, 18, 63, 192, live `code_search` limit 10. Qualify: "legacy" and "regex not yet available" come from gh CLI help, not the REST docs; point-in-time (2026-09); "no client or SDK" is slightly stronger than the source wording. Control arm: plain-term query returned 5 hits vs 0 for the regex query. |
| gh has no automatic ETag handling or secondary-rate-limit retry; manual If-None-Match gives 304 and rc=1; `--cache` is TTL-only; #3292 open | **Confirmed** (a "misleading" flag was **overturned by the adjudicator**) | Real ETag 304/rc=1, bogus 200/rc=0; no `If-None-Match` handling in cli/cli source. `gh skills search` and the attachments upload read Retry-After only to print a message; they do not retry, so the claim stands. Open issues #13158 and #13357 request ETag/TTL caching upstream. gh version is stated (2.101.0). |
| Search endpoints return no ETag; repos and releases do; 304 is free against the primary limit | **Confirmed** (a "misleading" flag was **overturned by the adjudicator**) | Adjudicator re-probe: releases 1 ETag, search/issues and search/repositories 0. Qualify: search has its own rate-limit bucket (30/min; code search 10/min); "most endpoints" is docs wording so the search exception is empirical, n=1; the docs anchor is line 78 of the source, not line 56; the free 304 requires an authenticated request. |
| githubkit v0.16.1: REST and GraphQL, default auto-retry, typed exceptions, `LocalThrottler(100)`, paginator, hishel cache | **Confirmed** (a "misleading" flag was **overturned by the adjudicator**) | `retry.py` L14-20, `config.py` L95/98-102/125, `exception.py` L74-93, README L57-61. The 5xx retry (up to 3 times, quadratic backoff) is already stated in the report. Paginator, GraphQL and cache modules confirmed from the README feature list only. |
| Official libraries list names only octokit.js/.rb/.net and Terraform; PyGithub, githubkit, go-github third-party; PyGithub asks for maintainers | **Confirmed** for the list, the third-party split and the maintainer appeal | Docs page and PyGithub README L68. |
| PyGithub is REST-only | **REFUTED (UPHELD), struck** | README says only "a Python library to access the GitHub REST API" (silence, not absence). `github/Requester.py` (main) defines `graphql_query` (L733), `graphql_query_class`, `graphql_node`, `graphql_node_class` and POSTs to a `graphql_url`. The grep control arm: 40 hits for "graphql" vs 0 for a fresh invented token. **Qualify (UPHELD misleading):** other Python clients exist (gidgethub, ghapi, github3.py), so the third-party list is larger than the report implies. |
| `gh discussion` exists (preview); `gh search` has no discussions category | **Confirmed** | `gh discussion --help` lists create/list/comment/edit/view; `gh search discussions` returns unknown command; #8867 open. |

Unverified: everything tagged inherited that the verifiers did not touch (go-github README claims,
githubv4, octokit.js README claims, GraphQL ETag, discussions search).

**How the conclusion changes.** The hybrid recommendation (gh for ad-hoc, githubkit for the scheduled
loop) stands. One rationale changes: PyGithub is no longer rejected for being "REST only". It is
disfavored for maintainer risk and thinner GraphQL coverage. The limits section is confirmed, with the
qualifiers above (gh-help-sourced "legacy", search's separate rate-limit bucket).

## Provenance

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| triage | Explore | sonnet | low |
| read-link:1 | Explore | sonnet | low |
| read-link:2 | Explore | sonnet | low |
| read:1/3 | Explore | haiku | (default) |
| read:2/3 | Explore | haiku | (default) |
| read:3/3 | Explore | haiku | (default) |
| synthesize | general-purpose | opus | high |
| refute:1/6 | general-purpose | sonnet | medium |
| refute:2/6 | general-purpose | sonnet | medium |
| refute:3/6 | general-purpose | sonnet | medium |
| refute:4/6 | general-purpose | sonnet | medium |
| refute:5/6 | general-purpose | sonnet | medium |
| refute:6/6 | general-purpose | sonnet | medium |
| critic | Explore | sonnet | medium |
| adjudicate | general-purpose | opus | high |
| reconcile (this node) | general-purpose | sonnet | medium |

Caller links, all cited: the libraries page (fetched and re-probed), pygithub/pygithub (inherited
README claims plus a releases re-probe), google/go-github (inherited README plus a source re-probe at
v92.0.0), shurcooL/githubv4 (inherited README plus a releases re-probe), and github.com/octokit
(inherited org metadata plus go-sdk/dotnet-sdk/octokit.js re-probes).

## GitHub repos touched

- [cli/cli](https://github.com/cli/cli) — gh 2.101.0 help probes; issue states for #3292, #9734, #10426, #8522 and #11029; latest release
- [yanyongyu/githubkit](https://github.com/yanyongyu/githubkit) — README plus `retry.py`, `exception.py`, `config.py`, `throttling.py` and `paginator.py` at v0.16.1; issue #293
- [PyGithub/PyGithub](https://github.com/PyGithub/PyGithub) — README (inherited); latest release
- [google/go-github](https://github.com/google/go-github) — README (inherited); `github/github.go` API-version constants at v92.0.0
- [shurcooL/githubv4](https://github.com/shurcooL/githubv4) — README (inherited); release check (none)
- [octokit/octokit.js](https://github.com/octokit/octokit.js) — README (inherited); latest release
- [octokit/plugin-throttling.js](https://github.com/octokit/plugin-throttling.js) — latest release only
- [octokit/go-sdk](https://github.com/octokit/go-sdk) — repo metadata and tags
- [octokit/dotnet-sdk](https://github.com/octokit/dotnet-sdk) — repo metadata
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — `research_fanout.py`, `dependency_currency.py`, `currency.toml`, `python/uv.lock`; a live code-search header probe
- [integrations/terraform-provider-github](https://github.com/integrations/terraform-provider-github) — named on the official libraries page (not read)
