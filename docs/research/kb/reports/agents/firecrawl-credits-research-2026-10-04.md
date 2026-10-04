# Firecrawl credit pre-flight research — 2026-10-04

Status: two requested artifacts prepared and targeted saved-search checks pass;
research coverage remains incomplete as detailed below. No implementation,
commits, or heavy gates.

RESEARCH INCOMPLETE: the mandated strict-five run exited 1 because
`firecrawl-search` returned `exited 1: Error: Request failed with status code 402 |`.
The credit pre-flight would have identified this exhausted account before search.

## Native capability

The real credential-scoped command succeeded with an exhausted, negative balance.
This proves that querying credit usage remains possible for this exhausted account;
it does not alone prove a universal billing contract.

```text
fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults --no-daemon --non-interactive exec -- mise exec -- firecrawl credit-usage --json
exit code: 0
{"success":true,"data":{"remainingCredits":-194,"planCredits":1000,"billingPeriodStart":"2026-09-11T17:36:55.821Z","billingPeriodEnd":"2026-10-11T17:36:55.821Z"}}
```

### CLI, API, plugin skill, and MCP

All live research commands used native `fnox` with profile `codex_research`.
The Python specialist independently ran the installed command surface:

| Command under `fnox … exec -- mise exec --` | rc | Observed result |
| --- | ---: | --- |
| `firecrawl --version` | 0 | `1.25.3` |
| `firecrawl --help` | 0 | `status`, `--status`, `credit-usage`, `credits` |
| `firecrawl credit-usage --help` | 0 | `credit-usage\|credits`, `--json` |
| `firecrawl status` | 0 | Authenticated via `FIRECRAWL_API_KEY`; concurrency `0/2`; credits `-194 / 1,000 (-19% left this cycle)` |

Installed 1.25.3 code at
`~/.local/share/mise/installs/npm-firecrawl-cli/1.25.3/node_modules/firecrawl-cli/dist/commands/credit-usage.js:59–82`
uses authenticated `GET https://api.firecrawl.dev/v2/team/credit-usage` and
projects the four returned fields. Its lines 134–149 exit 1 on failure and emit
the JSON success wrapper. `status.js:72–108,221–238` also fetches queue status,
catches failures, and may return with rc=0 without usable credits.

Offline sources were inspected first: `knowledge-base/sources/firecrawl-cli`,
commit `86aaf06cb139029ff5ad2a249670f42b01d40b13`, package **1.23.3**, resolves
the canonical upstream to `firecrawl/cli`. This older source is not presented as
the installed 1.25.3 implementation. The [offline pinned command source](https://github.com/firecrawl/cli/blob/86aaf06cb139029ff5ad2a249670f42b01d40b13/src/commands/credit-usage.ts)
matches the live endpoint and response shape.

The [primary API route](https://github.com/firecrawl/firecrawl/blob/4244638a7041bae8b99bdd42e3c44520f9e62da1/apps/api/src/routes/v2.ts)
registers the credit GET with account authentication and no credit-check middleware.
The [controller](https://github.com/firecrawl/firecrawl/blob/4244638a7041bae8b99bdd42e3c44520f9e62da1/apps/api/src/controllers/v2/credit-usage.ts)
calls `getTeamBalance` and returns the four fields; missing balance returns 404.
The [balance helper](https://github.com/firecrawl/firecrawl/blob/4244638a7041bae8b99bdd42e3c44520f9e62da1/apps/api/src/services/autumn/usage.ts)
reads billing balances and subscriptions, with a customer get-or-create fallback;
this inspected path contains no debit call. **Inference: the balance lookup itself
does not consume scrape/search credits in this implementation.** The successful
−194 lookup and unchanged status balance support that inference. No explicit
hosted pricing guarantee for this GET was found, so “always free” is not claimed.

Installed Firecrawl skills were read at
`~/.claude/plugins/cache/firecrawl/firecrawl/1.1.0/skills/firecrawl/SKILL.md` and
`~/.codex/plugins/cache/claude-plugins-official/firecrawl/1.0.9/skills/firecrawl/SKILL.md`.
Both already prescribe `firecrawl --status` as a prerequisite and document
`firecrawl credit-usage` plus JSON output. The corresponding [pinned upstream
skill](https://github.com/firecrawl/cli/blob/86aaf06cb139029ff5ad2a249670f42b01d40b13/skills/firecrawl/SKILL.md)
is a CLI workflow, not a separate billing service. No plugin installation or
settings changes were needed.

The upstream MCP server **does have** `firecrawl_credit_usage`. At commit
`af5c378915280a87628a07cbc1b6041e7e8694cb`, its [usage tool source](https://github.com/firecrawl/firecrawl-mcp-server/blob/af5c378915280a87628a07cbc1b6041e7e8694cb/src/usage.ts)
registers a read-only tool with optional `view: current|historical` and `byApiKey`.
`{ "view": "current" }` calls the same `/v2/team/credit-usage` endpoint and
returns the balance fields; historical mode uses the `/historical` endpoint.
`byApiKey=true` selects historical mode and can include API-key identifiers, so
it was not invoked. The [server README](https://github.com/firecrawl/firecrawl-mcp-server/blob/af5c378915280a87628a07cbc1b6041e7e8694cb/README.md#16-credit-usage-tool)
requires an authenticated account; keyless and search-only profiles expose
different tool sets. Session tool discovery exposed no Firecrawl MCP tool.
This is primary-source verification, **not a claimed live MCP execution**.
Its current-view adapter defaults a missing balance to zero; for pre-flight use,
prefer raw CLI JSON with explicit field validation so unknown does not become
exhausted through normalization.

## Pre-flight proposal

The current `python/src/dotfiles_setup/research_fanout.py:981` Firecrawl search
prerequisite checks only `shutil.which("firecrawl")`. `_presence` at line 1288
maps a missing reason to `present`, and `_list_sources` at lines 1296–1301 prints
it. A real `--list-sources --repo firecrawl/cli` still reported `present` after
the live balance was measured at −194.

Propose one bounded credit snapshot, shared explicitly between the list path and
runtime `_source_result` before `_primary_attempt` at line 1104. Keep the cheap
PATH prerequisites pure; inject the snapshot rather than accidentally making
multiple network requests from a predicate. Prefer `firecrawl credit-usage
--json` over `status`: the former projects machine-readable fields and exits 1
on failures; status additionally fetches concurrency and may catch errors while
exiting 0.

- Require rc=0, `success=true`, and a finite numeric `remainingCredits`.
- `remainingCredits <= 0` identifies exhausted **team** credits. Initially report
  this as an actionable advisory snapshot. Only after authoritative mapping to
  the search allowance is verified should confirmed exhausted search credits
  become `absent: no credits (remaining=-194)` in the list and an explicit
  blocked/skipped source result at runtime. Strict-five must still fail; a
  skipped required source is not successful coverage.
- Propose a tunable 10-second ceiling, bounded by the remaining source deadline.
  Retain the existing credential-cleaning path at line 823. Never log keys.
- Separate 401/403 authentication errors from timeout, 429, 5xx, invalid JSON,
  and unknown balance. None of these establish zero credits.
- Positive credits are only a snapshot: compare against an operation budget,
  including the potential empty-result control at lines 1039–1077. Preserve
  request-time 402 handling because concurrent spending makes the check non-atomic.
- Team balance is not the entire eligibility contract. The inspected API search
  route checks `SEARCH_CREDITS_FEATURE_ID`, whereas the balance helper reads
  `CREDITS_FEATURE_ID`; [PR #4412](https://github.com/firecrawl/firecrawl/pull/4412)
  also proves per-key limits can cause 402 with a positive team balance. Before
  implementing hard exclusion for all accounts, verify the search allowance and
  PAYG semantics. The observed −194 account plus live search 402 is conclusive
  for this run; the proposed predicate is not a universal entitlement oracle.
  Under licensed dissent, the unconditional hard-skip portion is stopped at
  proposal stage until this mapping is established; no implementation is authorized
  by this report.
- Record observation time, endpoint, rc and safe fields; refresh per invocation
  rather than adding a cross-run cache.

**PRO:** actionable early failure, avoids doomed searches and control calls,
uses an existing supported command. **CON:** another authenticated request,
latency and account rate limits; no reservation or guarantee of later success.
This is a proposal only. No implementation or new tests were written.

## Prior art

Queries below use `repo:<repo>` plus the displayed terms. Issues include PRs.
The direct `gh api /search/issues` calls returned rc=0 with
`incomplete_results=false`; discussion counts are returned nodes up to limit 20,
not total-match counts. All zeros were accompanied by controls in the saved rerun.

| Repo | Query | Hits | Control arm |
| --- | --- | ---: | --- |
| `firecrawl/firecrawl` | `credits` | 333 | Issue positive 4; fresh absent 0 |
| `firecrawl/firecrawl` | `"credit" "balance"` | 53 | Issue positive 4; fresh absent 0 |
| `firecrawl/firecrawl` | `"credit-usage"` | 131 | Issue positive 4; fresh absent 0 |
| `firecrawl/firecrawl` | `402` | 49 | Issue positive 4; fresh absent 0 |
| `firecrawl/firecrawl` | `preflight` / `"pre-flight"` | 17 / 14 | Issue positive 4; fresh absent 0 |
| `firecrawl/cli` | `credits` | 25 | Issue positive 1; fresh absent 0 |
| `firecrawl/cli` | `"credit" "balance"` | 1 | Issue positive 1; fresh absent 0 |
| `firecrawl/cli` | `"credit-usage"` | 12 | Issue positive 1; fresh absent 0 |
| `firecrawl/cli` | `402` | 1 | Issue positive 1; fresh absent 0 |
| `firecrawl/cli` | `preflight` / `"pre-flight"` | 0 / 0 | Issue positive 1; fresh absent 0 |
| `firecrawl/firecrawl` | discussions: `credit` / `"credit-usage"` / `402` | 5 / 1 / 1 | CostGoat positive 1; fresh absent 0 |
| `firecrawl/firecrawl` | discussions: `preflight` / `"pre-flight"` | 0 / 0 | CostGoat positive 1; fresh absent 0 |
| `firecrawl/cli` | discussions: `credit` / `402` | 0 / 0 | Main-repo CostGoat 1; fresh CLI absent 0; forum disabled |

Positive issue controls are `repo:firecrawl/firecrawl "per-key spend limit"`
and `repo:firecrawl/cli "omit inferred credit usage"`. The discussion positive
is `repo:firecrawl/firecrawl CostGoat`; negative queries use a fresh `{nonce}`.
`gh api repos/firecrawl/cli` reports `has_discussions=false`, so the cross-repo
positive validates GraphQL search access, not the completeness of an active CLI
discussion forum. The corresponding GitHub-only fanout discussion arm was
`empty_unverified` with `canary returned 0 items`, despite aggregate rc=0.

Verified relevant prior art:

- [CLI PR #236](https://github.com/firecrawl/cli/pull/236), merged 2026-09-16:
  avoids misleading inferred usage when remaining credits exceed plan allowance;
  machine-readable balance fields remain available.
- [CLI PR #242](https://github.com/firecrawl/cli/pull/242), merged 2026-09-17:
  adds the `credits` and `status` aliases.
- [API PR #4412](https://github.com/firecrawl/firecrawl/pull/4412), merged
  2026-08-26: per-key spending limits return 402, including v1/v2 search, even
  when the team still has credit.
- [CLI issue #115](https://github.com/firecrawl/cli/issues/115), open at review:
  reports a budget-cap failure with a large team balance. Its pasted shell
  exit-code evidence is not an independently verified CLI result.
- [Discussion #4528](https://github.com/firecrawl/firecrawl/discussions/4528)
  describes CostGoat balance monitoring; [discussion #4135](https://github.com/firecrawl/firecrawl/discussions/4135)
  asks about per-agent spending controls. No third-party monitor was installed.

Both required GitHub-only `research-fanout` subset runs completed rc=0. Main
repo returned issues 15, discussions 5 and releases 10; CLI returned issues 15
and releases 2, with the disabled-discussion limitation above. Own-repository
search `repo:ray-manaloto/dotfiles firecrawl` returned 39 complete hits, including
issues #1514, #1577 and #1572. The controlled GitHub code probe returned HTTP 200:
must-hit README 2, fresh known-absent 0, and `credit-usage` 12.

## Saved search

Created `docs/research/saved-searches/firecrawl-credits-2026-10-04.toml` with
schema version 1, four watches, 19 queries, eight controls, weekly cadence and
limit 20. Tune query terms, cadence and limit in place; `issues` includes PRs,
and adding `is:issue` or `is:pr` narrows it. The CLI discussion watch explicitly
records that discussions are disabled and can detect future enablement.

| Public-interface validation | rc | Result |
| --- | ---: | --- |
| `mise run research-saved-search -- status <file>` | 0 | Four watches; initially STALE before first snapshot |
| `fnox … exec -- mise run research-saved-search -- rerun <file>` | 0 | 13 ok, 6 empty-verified; all eight controls pass |
| `mise run research-saved-search -- status <file>` after rerun | 0 | Four watches; fresh; snapshot `2026-10-04T21:33:15.870550+00:00` |

Snapshot: `.agent/kb/raw/saved-searches/firecrawl-credits-2026-10-04/20261004T213315Z.json`.
The first attempted cadence was `monthly`, inherited from the schema example;
the current loader rejected it with rc=2. It was corrected to supported `weekly`
before the successful runs. This is an observed example/loader mismatch, not
permission to weaken validation or edit the existing example.

## Recommendation

Use the native JSON credit-usage command as the proposed pre-flight: it already
answers the account-status question while exhausted. Keep the API and MCP tool
as equivalent native alternatives; no custom balance service is justified.
Validate endpoint-specific allowance semantics before turning the team snapshot
into a universal hard skip, and preserve explicit failed-route accounting in
strict-five receipts. The tunable saved search is ready for future checks.
Implementation and any commit remain with the caller.

## Sources

The Python specialist ran `mise run graphify-health`: rc=3, graph missing.
Source inspection is the fallback; no graph rebuild was attempted.

### Five-source receipt

The required native `fnox` profile wrapped `mise -C
/Users/rmanaloto/.codex/tools/dotfiles-research-gate run research-fanout` with
`--strict-five`, request ID `01a108cb-a357-7fd0-b81d-01d2db9a1703`, an explicit
two-subquery Last30Days plan, and the mandated external receipt directory.
The run's manifest is
`/Users/rmanaloto/.codex/research-coverage/01a108cb-8164-7b90-9ed3-2dae35a11875/01a108cb-a357-7fd0-b81d-01d2db9a1703/manifest.json`.

| Source | Status | Items | Qualification |
| --- | --- | ---: | --- |
| GitHub issues | ok | 1 | Issue number 402 was unrelated to credit exhaustion; excluded |
| GitHub discussions | empty_verified | 0 | Positive control returned 10 |
| GitHub releases | empty_verified | 0 | Positive control returned 1 |
| Exa | ok | 10 | Unsolicited retired-site result excluded and never followed |
| Context7 | ok | 5 | Primary upstream docs selected for verification |
| Firecrawl developer | ok | 8 | Developer index works despite search exhaustion |
| Firecrawl search | error | 0 | HTTP 402; not a valid zero-result search |
| Last30Days | ok | 4 | Includes unrelated Descript result, excluded from conclusions |

The aggregate verdict was `strict-five fail [firecrawl-search did not complete]`.
Last30Days diagnostic ran through native `fnox`, rc=0; its third-party `jieba`
dependency emitted a Python invalid-escape `SyntaxWarning`, recorded here rather
than suppressed. Raw nested source outcomes were `grounding=ok`, `reddit=ok`,
`github=no-results`, `hackernews=no-results`, `youtube=no-results`; these do not
establish successful coverage for every platform listed in the original plan.
Only primary source checks above support final capability claims.
The primary [API error reference](https://github.com/firecrawl/firecrawl-docs/blob/main/api-reference/errors.mdx)
was also fetched directly: 402 insufficient credits is not retryable; rate-limit
429 calls for backoff. These are different failure classes.

### Tools used and failed routes

- Actually executed: native `fnox`, `mise`, `uv`/Python, `research-fanout`,
  `research-saved-search`, `gh api` REST and GraphQL, Firecrawl CLI (credit,
  status, help, search, developer), `curl`, `ctx7` through the Context7 arm,
  Exa API through fanout, Last30Days engine through fanout and `--diagnose`.
- Skills read and applied: installed Firecrawl CLI skill for native surfaces;
  Last30Days 3.26.0 skill for explicit query planning and outcome interpretation.
  No connector app, Firecrawl MCP tool, plugin installation, or UI automation ran.
- Required failure: Firecrawl search HTTP 402. Developer search still succeeded;
  success of that sibling route does not repair the failed required search arm.
- Recovered routes: an unquoted GitHub tree URL was rejected locally by zsh
  (rc=1); the quoted URL succeeded. An initial guessed `controllers/v2/team.ts`
  fetch returned HTTP 404 (curl rc=56); tree discovery found `credit-usage.ts`.
  The installed CLI discovery initially assumed a nonexistent `lib/node_modules`
  layout (rg rc=2), then resolved the actual binary symlink. Config research's
  initial code-probe role argument was rejected (rc=2), then corrected to `query`.
  Local record search encountered missing `task_plan.md` (rg rc=2), not a
  verified empty record corpus.
- The mandatory failed Firecrawl route is retained as the mirror/coverage gap;
  no additional doomed paid scrapes were run for every primary URL. Primary
  upstream source bytes were fetched with bounded `curl` into isolated raw
  evidence. Retired-site results returned unsolicited by Exa were excluded.
- Targeted validation only. No lint/hk/verify/full-test gates or code changes.
  The documentation specialist's normal `lint-docs` gate was not run under the
  task's explicit no-heavy-gates constraint; no gate pass is claimed.
- Lightweight report checks exited 0: all seven required sections present,
  balanced fenced blocks and no trailing whitespace. All eight manifest raw-file
  SHA256 values matched the recorded hashes. `git diff --check` exited 0, but
  the report is untracked, so the explicit file-content checks carry that evidence.

Tracked-file baseline before this task contained two unrelated untracked reports:
`cold-review-af0739cb-2026-10-04.md` and `vendored-skills-review-2026-10-04.md`.
They are outside this task's ownership and remain untouched. Other agents later
modified additional pre-existing tracked paths; this task's writes remain confined
to its two authorized deliverables and isolated raw evidence. This report is the
incremental findings record under the user's explicit two-file allowlist.

## GitHub repos touched

- `firecrawl/cli` — offline source, installed CLI provenance, live metadata,
  issues/PRs/releases, disabled discussions and code controls.
- `firecrawl/firecrawl` — primary API source, issues/PRs/discussions/releases.
- `firecrawl/firecrawl-mcp-server` — pinned README and tool implementation.
- `firecrawl/firecrawl-docs` — Context7 excerpts and primary error reference.
- `ray-manaloto/dotfiles` — existing issue history and local fanout/saved-search
  interfaces. No upstream issue, PR, comment or discussion was posted.
