# Saved searches: finding NEWER examples past the top-N — research (2026-10-03)

Lane: read-only researcher. Status: COMPLETE. 5 of the 6 allowed `search/code` calls used.

## Problem (as read from code)

- `_direct` (`python/src/dotfiles_setup/saved_searches.py:474-526`) issues ONE `search/code` call with `per_page=limit`
  (default 10, file max 100) and keeps `items[:limit]`. No `page` parameter, no pagination.
- `_urls` (`:540-545`) canonicalises `/blob/<sha>/` to `/blob/HEAD/`, so the diff key is repo+path.
- `_report` (`:846-901`) diffs `set(run.urls)` vs previous; when `count > len(urls)` it only appends `(top N of M)`.
- `_PacedRunner` (`:450-463`) sleeps `_CODE_PACE = 6.5` s before every `search/code` call after the first.

## Findings with citations

Primary docs fetched as markdown via `https://docs.github.com/api/article/body?pathname=<path>` (control: a bogus
pathname `/en/rest/search/zzqq-nope` → 404 while the real page → 200, so the fetch discriminates).

### GitHub REST `GET /search/code` (legacy engine)

- **1,000-result cap**: "the GitHub REST API provides **up to 1,000 results for each search**" — REST search
  overview, `/en/rest/search/search` § About search.
- **`per_page` max 100, default 30; `page` default 1** — same page, § Search code → Parameters.
- **Pagination**: via the `link` header (`rel="next"/"prev"/"first"/"last"`), omitted when one page fits —
  `/en/rest/using-the-rest-api/using-pagination-in-the-rest-api` § Using link headers. Measured live (below).
  `gh api --paginate [--slurp]` follows `rel="next"` natively (`gh api --help`), but issues pages back-to-back with no
  pacing.
- **Rate limit**: "The Search code endpoint requires you to authenticate and limits you to 10 requests per minute";
  other search endpoints 30/min — § Rate limit. Measured response headers: `x-ratelimit-limit: 10`,
  `x-ratelimit-resource: code_search`.
- **`incomplete_results`**: set `true` when a query hits the search timeout; "Reaching a timeout does not necessarily
  mean that search results are incomplete" — § Timeouts and incomplete results.
- **Ordering**: "Unless another sort option is provided ... results are sorted by best match in descending order"
  — § Ranking search results. **`sort` for code is "closing down" and "Can only be `indexed`"**; `order` likewise
  closing down — § Search code → Parameters. Measured: `sort=indexed&order=desc` is accepted (200) and **ignored**
  (identical best-match order). The docs make NO stability promise across pages or runs; measured stable for
  back-to-back calls only.
- **Coverage limits**: default branch only; files < 384 KB; at least one search term — § Search code
  considerations. Forks are indexed only when they have more stars than the parent and a post-create push, and need
  `fork:true`/`fork:only` — `/en/search-github/searching-on-github/searching-code` (legacy) § Considerations.
- **Other cost driver**: `_confirmed` re-fetches every kept item for `grep`/`path_grep` watches via `gh api <url>`
  (core rate limit 5000/h, not `code_search`) — collecting all 141 items would mean 141 raw fetches for the
  `iwyu-dockerfile-cmake-prefix` watch, which carries `grep = 'include-what-you-use'`.

### Qualifiers usable for sharding (legacy syntax — the only one the REST API takes)

From `/en/search-github/searching-on-github/searching-code` ("Searching code (legacy) … you should only need to use
for the REST API endpoint for searching code"): `in:file|path`, `user:`, `org:`, `repo:`, `path:` (incl. `path:/`),
`language:`, `size:` (with `>`, `<`, `n..m` ranges, e.g. `size:>10000`), `filename:`, `extension:`, `fork:`.
**No `pushed:`/`created:`/date qualifier**: `grep -c -E "pushed:|created:"` on that page = **0**, while the control
`grep -c "size:"` on the same page = **3**, so the grep discriminates. `size:` ranges are the only qualifier that
partitions an arbitrary result set into disjoint, exhaustive shards (every file has exactly one size); `language:` and
`path:` partitions are neither exhaustive nor guaranteed disjoint.

### Alternatives

- **New code search (regex, `symbol:`, boolean)**: documented at
  `/en/search-github/github-code-search/understanding-github-code-search-syntax`; the legacy page states the legacy
  syntax is only needed "if you are using the code search API" — i.e. the new engine has **no public REST/GraphQL
  endpoint**; the REST endpoint is the legacy engine.
- **GraphQL `search`**: `SearchType` enum, introspected live: `ISSUE, ISSUE_ADVANCED, ISSUE_SEMANTIC, ISSUE_HYBRID,
  REPOSITORY, USER, DISCUSSION` — **no CODE** (control: `__type(name:"ZzqqNoSuchType")` → `null`, so introspection
  discriminates).
- **grep.app**: `https://grep.app/api/search?...` → **HTTP 429 with a "Vercel Security Checkpoint" HTML page** for both
  a real and a known-absent query — scripted access is bot-walled; not a usable automated source today.
- **Sourcegraph public** `/.api/search/stream` (anonymous, SSE): works (control `repo:^github\.com/cli/cli$
  file:README.md` → 1 match). `include-what-you-use file:Dockerfile count:all` → **167 matches in only 25 repos** vs
  GitHub's 221 files; the two-term AND query → 0. Coverage of sourcegraph.com is a curated subset, so it can be a
  supplementary second source at best, never the authority for "new to the index". It does offer exhaustive
  (`count:all`) results with no 1000-cap, and `type:diff`/`type:commit` with `after:` dates — but only on repos it
  indexes.

## Measurements

All on 2026-10-03, authenticated `gh api -i -X GET search/code`, query
`include-what-you-use CMAKE_PREFIX_PATH filename:Dockerfile`, `per_page=100`. Raw responses kept in the scratch dir
`/tmp/ssr/p{1a,2a,1b,2b,1sort}.raw` (not tracked). **5 search/code calls used of the 6 allowed.**

| call | page | total_count | items | incomplete | x-ratelimit-limit / remaining (resource) | wall |
|---|---|---|---|---|---|---|
| 1a | 1 | **125** | 100 | false | 10 / 9 (`code_search`) | 2.4 s |
| 2a | 2 | **141** | 41 | false | 10 / 8 | 2.4 s |
| 1b | 1 | 141 | 100 | false | 10 / 7 | 0.5 s |
| 2b | 2 | 141 | 41 | false | 10 / 6 | 0.4 s |
| 1sort | 1, `sort=indexed&order=desc` | 141 | 100 | false | — | — |

Four paged calls with a 6.5 s gap between them: **25.2 s wall** in total (each call 0.4-2.4 s; the repeat calls were
~5x faster, consistent with a server-side result cache).

Findings:

1. **Top-10 (and top-20, and all of page 1) were identical in order between two calls 7 s apart.** Page 2 was also
   identical. So immediate re-calls are stable; churn, if any, is a between-runs (index update) effect, not per-call
   noise. This measurement cannot speak to week-to-week rank churn (the bound is "when it ran").
2. **Pages do not overlap**: page1 ∩ page2 = 0 in both runs; page1 ∪ page2 = **141 unique repo+path keys**, identical
   set across runs (a−b = b−a = 0). 133 distinct repos.
3. **`total_count` is not stable even within seconds**: the first call said 125 (matching the 2026-10-03 baseline),
   every later call said 141, and pages 1+2 actually delivered 141 items. So `total_count` is an estimate; the count
   column `125 → 141` would read as "16 new examples" when the index set did not change between my calls. The real
   measure of size is the number of distinct keys actually collected.
4. **`Link` header pagination works**: page 1 carried `rel="next"` and `rel="last"` = page 2; page 2 carried
   `rel="prev"`/`rel="first"`/`rel="last"`, no `next` — a reliable stop signal.
5. **Reachability**: 141 ≤ 1000, so the full set is collectable in `ceil(141/100) = 2` calls.
6. **`sort=indexed&order=desc` is silently ignored**: rc 0, HTTP 200, same 141 total, and the top 100 came back in
   exactly the best-match order (ranks 0..9 → 0..9). There is no usable recency sort on code search.
7. The rate-limit resource is `code_search` with limit **10** per window, separate from `search` (30) — so the paced
   6.5 s gap (≈9.2/min) is right for code search.

Baseline-URL check: the three baseline URLs of `iwyu-dockerfile-cmake-prefix` (magma, cmake_template, ogdf) are ranks
0, 1, 2 — the baseline only ever saw the head of a 141-item set.

## Examples found

Repo search via `gh search repos` (control arm: `gitleaks` → 8 hits while the fresh absent term
`zzqv8k1 nonexistentmonitorterm` → 0, and the multi-word phrases like "github code search monitor" also → 0, so the
multi-word zeros are the search's AND semantics, not a broken probe; the tools below were then found by name). Source
read through `gh api repos/<o>/<r>/contents/<path>` (no search/code calls spent).

| tool | how it watches code search | top-N / ranking handling | evidence |
|---|---|---|---|
| [FeeiCN/GSIL](https://github.com/FeeiCN/GSIL) (★2.1k, leak monitor) | PyGithub `search_code(keyword, sort="indexed", order="desc")`, cron | Fixed window `default_pages = 4` × `per_page = 50` (= top 200); dedupe by blob `sha` in a persisted hash list ("Processed, skip!") | `gsil/engine.py:35,43,91-95,174,198-202` |
| [hisxo/gitGraber](https://github.com/hisxo/gitGraber) (★2.4k) | `search/code?q=…&sort=indexed&o=desc`, one page, loop | Relies on `sort=indexed` to surface new files at the top; appends seen raw URLs to `rawGitUrls*.txt` | `config.py:3,5`; `gitGraber.py:26-40,311-330` |
| [VKSRC/Github-Monitor](https://github.com/VKSRC/Github-Monitor) (★1.75k) | `search_code(keyword, sort='indexed', order='desc')` every `task.interval` min | `total = min(totalCount, 1000)` ("github api supports at most 1000 records"), pages = min(ceil(total/50), task.pages); dedupe by `sha` in DB | `server/.../monitor/processors.py:28,66-68,79-88,157-158,225` |
| [Macr0phag3/GithubMonitor](https://github.com/Macr0phag3/GithubMonitor) (★317) | `sort="indexed"`, pages 0..33 × 30 ("corresponds to github's 1000-result limit") | Pages to the cap; random 20-60 s sleep on rate-limit; records url+sha per item | `spider.py:96-103,121-123,175-190,256` |
| [4x99/code6](https://github.com/4x99/code6) (★1.2k, PHP) | `api('search')->setPage($page)->code($keyword, 'indexed')` | Pages while `next` link exists, up to per-job `scan_page`; dedupe key `md5(owner/repo/blob/path)` | `app/Console/Commands/JobRunCommand.php:93-100,146-150,231-254` |
| Sourcegraph Code Monitoring (product, not a repo) | Trigger "When new search results are detected"; query must be `type:commit` or `type:diff`; runs over every new commit | Sidesteps ranking entirely: it diffs commits, not a ranked file list — but only over repos Sourcegraph indexes | [docs](https://sourcegraph.com/docs/code-monitoring) |

Pattern across all five GitHub tools: **(1) persist a seen-set keyed by file identity, (2) page deeper than the head
(200 → the full 1000), (3) lean on `sort=indexed`.** Point 3 no longer works: the parameter is "closing down" and was
measured ignored today — so those tools now see best-match order, and only the ones that page to the cap (VKSRC,
Macr0phag3, code6 with a large `scan_page`) still catch a new file ranked low. None of them shard past 1000. None treats
GONE as a signal (they only alert on NEW), which is consistent with ranking/index churn making GONE noisy.

## Recommendation

**Adopt a per-watch `collect = "all"` mode (opt-in, code watches with `role = "query"` only), with a hard
"uncollectable" status above 1000 and NO default sharding; keep `top` as the default; NEW is the signal, GONE is
reported only for complete-vs-complete runs.** Do not raise the global default `limit` — it does not fix the defect
(any N < total still diffs a rank window) and multiplies `_confirmed` fetches for every watch.

Why this shape: the measured set was stable, non-overlapping and fully reachable (141 keys in 2 calls, 7 s apart), so
"diff the full repo+path set" is sound for any total ≤ 1000. There is no date sort or date qualifier to target "newer"
directly, and the new engine has no API, so exhaustive collection is the only way "NEW" can mean "new to the index".
Every surveyed monitor that still works today does exactly this (page to the cap, dedupe by file identity).

### Concrete changes

1. **Schema/model** — `schemas/saved-search-file.schema.json` Watch: add `"collect": {"enum": ["top", "all"]}`
   (default `top`); regenerate `python/src/dotfiles_setup/generated/saved_search_file.py` with the repo's codegen
   task. Validation in `_validate_watch` (`saved_searches.py:117`): `collect = "all"` only on `kind = "code"` and role
   `query`; ignore/forbid `limit` with it.
   `schemas/saved-search-snapshot.schema.json` WatchRun: add `collected: int` (distinct keys actually gathered) and
   `complete: bool`; add RerunStatus `uncollectable` (or reuse `incomplete` with a reason — a new value is clearer and
   must also be excluded from `_COMPARABLE`).
2. **`_direct` (`:474-526`)** — take a `page` argument and pass `-f page=<n>`; for `collect="all"` use `per_page=100`.
   Return items untruncated for all-mode (today `items[:limit]`).
3. **New `_collect_all(query, watch, boundaries, timeout) -> _Answer`** called from `_run_code` (`:690`, in place of
   `_direct` for all-mode watches): page 1..10 at per_page 100; stop when a page returns < 100 items (the measured
   terminal: page 2 had 41 and no `rel="next"`), or after page `ceil(min(total,1000)/100)`; dedupe by
   `(repository.full_name, path)`; if any page is rate-limited/incomplete/error, the whole answer takes that status
   (never a partial set — a partial set would report false GONE). If the first page's `total_count > 1000`, return
   status `uncollectable` with reason `"total N > 1000: shard with size:/path:/language: or narrow the query"` without
   paging (saves 9 calls) — sharding stays a manual edit to the saved file (split the watch into `size:` ranges),
   because no qualifier partitions automatically and a wrong shard silently drops files.
   Pagination needs no header parsing: `_GhResponse` (`research_fanout.py:1659-1686`) does not expose headers today,
   and the short-page rule is sufficient; `_PacedRunner` already paces every `search/code` argv, so pages are paced
   for free (keep `_CODE_PACE = 6.5`; `gh api --paginate` was rejected because it does not pace and would burst 10
   calls into a 10/min bucket).
4. **Count measure** — store `count = collected` (distinct keys) for all-mode, keep `total_count` as advisory. Measured:
   `total_count` said 125 then 141 for the same set within 7 s, so a `125 → 141` count delta is not evidence of 16 new
   examples.
5. **`_confirmed` (`:548-581`)** — with all-mode it would refetch every item each run (141 + 81 + 3 + 12 = 237 core
   API raw fetches for the IWYU file vs 55 today). Cache confirmations per `(repo, path, item.sha)` in the snapshot, and
   fetch only keys that are new or whose blob `sha` changed. (`item.sha` is the blob sha; the URL is canonicalised to
   HEAD by `_canonical`, so the sha must be stored separately — add `shas: dict[url, sha]` or a parallel list to
   WatchRun.)
6. **`_report` (`:846-901`)** — for all-mode rows print `collected N (complete)` instead of `(top N of M)`; compute
   GONE only when both runs are `complete`; mark NEW in a top-mode row as `NEW (rank window)` so the two meanings never
   share a column silently. `uncollectable` renders `n/a` like other non-comparable statuses.
7. **IWYU file** — set `collect = "all"` on `iwyu-dockerfile-cmake-prefix` (141), `iwyu-yml-cmake-prefix` (81),
   `iwyu-clang-23-branch` (3), `iwyu-clang-p2996` (12). Leave `iwyu-dockerfile-musthit` (221) as a top-mode must-hit:
   a control only needs count > 0.

### Cost estimate (calls are `search/code`, 6.5 s apart ⇒ ≈9.2/min, under 10/min)

| file | code calls today (approx.) | added by all-mode | notes |
|---|---|---|---|
| `.agent/kb/raw/saved-searches-1502/iwyu.toml` | health 1 + known-absent 3 shapes + 3 `control_hit` + 5 queries = **12 (~72 s)** | **+1** (cmake-prefix: 2 pages; others ≤ 100 fit one page) | +182 core raw fetches on the first all-mode run, then only new/changed keys |
| `docs/research/saved-searches/orchestration-2026-10-02.toml` | 14 code watches each with `control_hit`+`control_absent` + health + shapes ≈ **45-50 (~5 min)** | Σ over opted-in watches of `ceil(min(N,1000)/100) − 1`; worst case +9 per watch (~+58 s each) | totals unknown — no baseline counts recorded; measure with one top-mode rerun before opting in |
| `llvm-major-detection-sweep-2026-10-02.toml` | 14 code watches (1 must-hit, 9 query, 1 health, 3 readme) | same formula over the 9 query watches | totals unknown (baseline `count` absent) |
| `model-registry-research-2026-10-02.toml` | 7 code watches (3 query) | same formula over the 3 queries | all are `repo:`-scoped, so totals are likely small (≤ 100 ⇒ +0) — unverified |

Because the cost is per-watch and only paid when `total > 100`, opt-in keeps the three tracked files at today's cost
until a curator flips a specific watch.

### Tests (each with a fail arm), in `tests/test_saved_searches.py` using the existing fake runner

1. `test_collect_all_pages_until_short_page` — fake returns 100 then 41 items; assert exactly 2 `search/code` calls
   with `page=1`/`page=2`, `per_page=100`, and 141 urls. Fail arm: remove the `page` loop → 100 urls, test fails.
2. `test_collect_all_new_item_ranked_past_top_n_is_new` — previous snapshot holds 141 keys; the new run puts a new key
   at rank 120. Assert it appears in NEW and nothing in GONE. Fail arm: run the same fixture with `collect="top"` /
   `limit=10` → the item is absent from NEW (that is the defect being fixed).
3. `test_collect_all_rank_shuffle_reports_nothing` — same 141 keys in a reversed order → NEW and GONE empty. Fail arm:
   top-mode with limit 10 on the same fixture reports 10 NEW and 10 GONE.
4. `test_collect_all_over_1000_is_uncollectable` — first page `total_count = 1500` → status `uncollectable`, exactly 1
   call, rc 1, row not diffed. Fail arm: delete the guard → 10 calls and a partial 1000-set marked ok.
5. `test_collect_all_partial_failure_never_reports_gone` — page 2 returns 403 → status `rate-limited`, GONE `n/a`.
   Fail arm: accept partial pages → 41 previous keys show as GONE.
6. `test_collect_all_pages_are_paced` — fake `ProbeTiming` records sleeps; assert a 6.5 s sleep between page 1 and 2.
   Fail arm: route pages through the unpaced runner → zero sleeps recorded.
7. `test_confirmed_skips_unchanged_sha` — two runs, same keys and blob shas → zero raw fetches on run 2; one changed
   sha → one fetch. Fail arm: drop the cache → 141 fetches.
8. `test_collect_all_rejected_on_non_code_or_must_hit` — `load()` raises `SavedSearchError` for `collect="all"` on an
   issues watch or a `must-hit`. Fail arm: remove the validation → loads.

Plus one real-integration arm (per `real-integration-evidence.md`): `mise run research-saved-search -- rerun` on the
IWYU file twice in a row with `collect="all"` must show NEW = GONE = ∅ and `collected 141`-ish for cmake-prefix.

### Open questions this research could not answer

- Week-scale rank churn and index churn magnitude: my calls were 7 s apart ("the condition has passed" bound) — two
  runs a week apart are needed.
- Whether `total_count` drift (125 → 141) reflects a lagging estimate or real index growth between calls 1 and 2;
  the collected set was identical in both runs, so for diffing it does not matter.
- Sourcegraph as a second source: coverage measured at 25 repos vs GitHub's 221 files for the same term; not
  recommended beyond an optional extra column.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — `saved_searches.py`, spec, schemas, saved-search files read
- [FeeiCN/GSIL](https://github.com/FeeiCN/GSIL) — code-search leak monitor; paging window + sha dedupe
- [hisxo/gitGraber](https://github.com/hisxo/gitGraber) — `sort=indexed` single-page monitor + seen-URL file
- [VKSRC/Github-Monitor](https://github.com/VKSRC/Github-Monitor) — `min(totalCount,1000)` paging + sha dedupe
- [Macr0phag3/GithubMonitor](https://github.com/Macr0phag3/GithubMonitor) — pages 0..33 to the 1000 cap
- [4x99/code6](https://github.com/4x99/code6) — `next`-link paging with `scan_page` cap; md5(repo/blob/path) dedupe
- [eth0izzle/shhgit](https://github.com/eth0izzle/shhgit) — surfaced by repo search only; not read (event-stream based, not code search)
- [magma/magma](https://github.com/magma/magma), [cpp-best-practices/cmake_template](https://github.com/cpp-best-practices/cmake_template), [ogdf/ogdf](https://github.com/ogdf/ogdf) — appear as ranks 0-2 of the measured IWYU result set (not read)
- [cli/cli](https://github.com/cli/cli) — Sourcegraph control-arm query target; `gh api --paginate/--slurp` help read locally

