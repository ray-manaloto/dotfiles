# Spec (DRAFT rev 2, 2026-09-30, not ratified) — `github-watch`: one registry (`watches.toml`) for topic watches and dependency-feature watches, a githubkit async engine, dated snapshots, a tracked diff, ETag release polling and a scheduled job

Status: **DRAFT rev 2, awaiting architect ratification.** Rev 1 (the `research-watch` draft by the spec-scribe
lane, no Bash) proposed `research-queries.toml` plus a `gh`-subprocess `github-code` source inside
`research_fanout.py`. Rev 2 applies Ray's 2026-09-30 ruling **"Revise: githubkit + one registry for both"** and the
six research points below. A general-purpose lane with Bash wrote rev 2. It ran live probes in scratch venvs and
made no repository change other than this file, the docs mirror, and its report. Evidence:
`docs/research/kb/reports/agents/github-watch-design-2026-09-30.md` (cited below as **R§nn**). The file path is
kept on purpose. Only the title changes.

Roles: "architect" is the Claude session that ratifies this spec. "Implementer" is the
`codex-{sol,astra}-implementer` lane chosen by the routing doctrine. "Caller" is the architect acting in its
commit role.

## Ratified architect notes (verbatim, load-bearing)

Rev 1 notes, unchanged:

> implement items 1-6 of the Recommendation in
> docs/research/kb/reports/agents/github-search-automation-2026-09-30.md:
> 1. A tracked `research-queries.toml` registry at the repo root: stable ids, question, repo, sources, `code = [...]`
>    with one legacy query per alternative, cadence, tags. Seed it with today's conf.d queries from
>    docs/research/kb/reports/agents/mise-confd-github-examples-2026-09-30.md and the native-installer queries from
>    native-installers-github-examples-2026-09-30.md. Each needs a must-hit control query and a known-absent control
>    query.
> 2. A `github-code` source in `python/src/dotfiles_setup/research_fanout.py`:
>    - `gh api -X GET search/code`, own ≤10/min pacing, 403 = rate limit and never zero;
>    - re-fetch each hit and grep it for a per-query pattern;
>    - a control arm.
> 3. Dated snapshots for registry runs; ad-hoc runs keep today's overwrite.
> 4. A `research_watch` module and `mise run research-watch [-- <id>]`:
>    - tracked `docs/research/kb/watch/<id>.jsonl` keyed on canonical URL;
>    - diff vs the previous snapshot: added / changed / dropped-from-top-N;
>    - deleted only after a direct 404/410.
> 5. A scheduled GHA job modelled on refresh.yml's standing-issue upsert.
> 6. A committed markdown digest per run, plus graphify `save-result --outcome` recording, via the repo's graphify
>    mise tasks only.
>
> Also a skill (.claude/skills/research-watch/SKILL.md) wrapping the task, and the research-sweep skill updated to
> use the registry.

Rev 2 rulings (Ray, 2026-09-30, intent as relayed by the coordinator):

> **Revise: githubkit + one registry for both.** One `watches.toml` holding topic watches and dependency-feature
> watches; `python/src/dotfiles_setup/github_watch.py` on githubkit's ASYNC API; a mise task and a skill (skill →
> task → python); dated snapshots and a tracked diff; ETag release polling; the refresh.yml schedule, using the
> existing GitHub App token (**Q9 ruled**); seed watches for real-world githubkit usage. Keep the drafter's
> accepted answers Q1-Q8, Q10, Q11.
>
> Research points: (A) mirror githubkit's docs offline at its latest version; (B1) githubkit async best practice and
> pytest async (pytest-asyncio vs anyio); (B2) githubkit's optional pydantic validation vs this repo's move to
> msgspec (#683, #675); (B3) the Hishel HTTP cache and auto-retry; (B4) latest ty and a ty LSP for Claude Code and
> codex; (B5) automating githubkit currency, with each adopted feature registered as a watch.

### What rev 2 changes from rev 1

| Rev 1 | Rev 2 | Why |
|---|---|---|
| `research-queries.toml` | `watches.toml`, holding `kind = "code"`, `"issues"` and `"releases"` entries with an `origin` field | "one registry for both" |
| `research_watch.py`, with transport through `research_fanout`'s `gh` subprocess | `github_watch.py`, with its own githubkit async client | "githubkit … ASYNC API" |
| A `github-code` source in `research_fanout.py`, plus changes to its tests | **Dropped from this change (Q12)**. `research_fanout.py` is not touched. | One code-search implementation, not two (gh and githubkit) |
| `mise run research-watch`, skill `research-watch` | `mise run github-watch`, skill `github-watch` | The rename follows the module |
| New `.github/workflows/research-watch.yml` (Q7) | New `.github/workflows/github-watch.yml` on refresh.yml's schedule and App token (**Q7b conflict, below**) | Q7 accepted and Q9 ruled |
| Deletion/fetch through `gh api` stderr parsing (A1) | Deletion through githubkit's `RequestFailed.response.status_code` | Typed status. A1 is retired. |
| Q5 (does graphify 0.9.65 have `--outcome`?) | **Resolved: yes.** Installed `graphify/cli.py:1472` declares it, and `--nodes` defaults to `[]` (`:1471`) | A read this session (PREMISES 33) |
| — | ETag release polling, the pydantic boundary, anyio tests, and cache/credential rules | B1-B5 |

## 1. Objective

Every GitHub search or release feed we care about becomes a **named, reviewed, re-runnable watch** in one
registry, `watches.toml`. There are two kinds of origin, and they share one engine:

- **Topic watches** (`origin = "topic:<slug>"`) track how real repositories solve a problem. The rev-1 seeds, conf.d
  layout and native installers, carry over unchanged.
- **Dependency-feature watches** (`origin = "dep:<package>@<version>[:<feature>]"`) cover our dependencies. A
  `releases` watch polls a dependency's releases with an ETag, so an unchanged feed costs a free `304`. Each feature
  we **adopt** from its release notes is registered as a `code` watch that finds real-world usage of that feature.
  githubkit is the first such dependency.

A scheduled job re-runs due watches. It records what changed since the last committed run (added, changed,
dropped-from-top-N, deleted after a direct 404/410) as tracked jsonl plus a committed markdown digest and a standing
issue. The chain is skill → mise task → Python (`mise-tasks-only.md`, `zero-bash-logic.md`). The engine uses
githubkit **only as a transport**. Every model is a msgspec `Struct` decoded through `dotfiles_setup.codec`, and no
first-party code touches githubkit's pydantic models (§3.2, §4).

Out of scope, never done by this change:

- the `research-fanout` `github-code` source (Q12);
- moving `research-sweep-run.js` off its out-of-band code search (Q6, still a follow-up);
- GraphQL discussions watches;
- a deep `currency.toml` entry for githubkit (Q14, which is blocked on the shared engine);
- the ty bump and the ty LSP plugin (Q15, Q16);
- any change to the strict-five research policy.

## 2. Files

Create:

- `watches.toml` (repo root, a sibling of `currency.toml` and `rule-sync.toml`). This is the registry, seeded per §3.1.
- `python/src/dotfiles_setup/github_watch.py`. It contains the registry loader and validator, the async engine, the
  pacer, canonicalization, the diff, the 404/410 deletion probe, the jsonl and digest writers, and
  `main(argv, repo_root, *, client_factory=None, clock=None, sleep=None) -> int`. It ends with the
  `if __name__ == "__main__": raise SystemExit(main(sys.argv[1:], _repo_root()))` shape that
  `research_fanout.py` uses (`python -m` task form, PREMISES 26).
- `tests/test_github_watch.py`.
- `.claude/skills/github-watch/SKILL.md`. This is the wrapper skill (§3.6).
- `.github/workflows/github-watch.yml`. This is the scheduled job (§3.7; Q7 accepted, Q7b open).
- `docs/research/kb/watch/` is created by the first real run and never hand-written. It holds `<id>.jsonl`,
  `runs.jsonl`, and `digests/<stamp>.md`.

Modify:

- `python/pyproject.toml`:
  - `dependencies` gains `"githubkit>=0.16.1"`, with a comment naming the transport-only rule (§4).
  - `[dependency-groups] dev` gains `"anyio>=4.15.1"`, because the tests use anyio's built-in pytest plugin (§3.8).
  - `[tool.ruff.lint.flake8-tidy-imports.banned-api]` gains `"githubkit.webhooks"` and
    `"githubkit_schemas"`. Their messages say "githubkit is transport-only here; decode with dotfiles_setup.codec
    (#675)".
  - Do **not** add `githubkit[auth-app]`: the App token is minted by the workflow action, not by Python.
- `python/uv.lock`: regenerated by `uv lock` after the pyproject edit. The expected new packages are githubkit,
  githubkit-schemas, githubkit-schemas-2026-03-10, hishel, anysqlite and msgpack (R§13).
- `tests/conftest.py`: add a session-wide `anyio_backend` fixture returning `"asyncio"`, following githubkit's own
  `tests/conftest.py:6-8`.
- `python/src/dotfiles_setup/graphify.py` and `python/src/dotfiles_setup/main.py`: add `save-result` as rev 1
  §3.5 specified. `build_save_result_args(...)` and `save_result(...)` go beside the other argv builders and run
  through `_run` (`graphify.py:531`). The `save-result` subparser and its dispatch go in `main.py`.
- `mise.toml`: add two thin tasks.
  - `[tasks.github-watch]`, which runs
    `run = 'uv run --project python python -m dotfiles_setup.github_watch'`.
  - `[tasks.graphify-save-result]`, which runs
    `run = 'uv run --project python dotfiles-setup graphify save-result'`, next to the `graphify-*` tasks
    (`mise.toml:799-866`).
- `python/verification/suites.toml`: add `workflow.github-watch-wiring`, a `require_tokens` contract binding skill ↔
  task ↔ module ↔ test ↔ workflow, modelled on `workflow.tool-currency-wiring`. Choose its tokens with
  `mise run token-check` so that each one binds a single site.
- `python/AGENTS.md`: the "Dependencies" line gains one clause, "`githubkit` (GitHub transport only: never
  `parsed_data`; decode with `codec`)". Stay inside `md_size_budget`.
- `.claude/skills/research-sweep/SKILL.md`: make it registry-first (§3.6).
- Generated, never hand-edited: `.agents/skills/github-watch/SKILL.md` and `.agents/skills/research-sweep/SKILL.md`,
  both produced by `mise run skills-mirror` (`mise.toml:1359-1362`).

Touch nothing else. In particular:

- `python/src/dotfiles_setup/research_fanout.py` and `tests/test_research_fanout.py` stay **untouched** (Q12).
- No new `.sh` (`bash_logic_budget`).
- No `scripts/codex-research-gate.py` edit.
- No edit under `docs/research/kb/reports/**` or `docs/research/kb/raw/**` (verbatim records).
- No `.claude/workflows/` edit (Q6).
- No `.claude/settings.json` edit and no plugin enablement (Q16).
- No `currency.toml` edit (Q14).

## 3. Interfaces

### 3.1 `watches.toml` schema

```toml
schema_version = 1

# One [[watch]] per stable id. Renaming a watch keeps its id, so its history survives.
[[watch]]
id       = "claude-native-installer"     # ^[a-z0-9][a-z0-9-]{0,59}$, unique, never reused
kind     = "code"                        # "code" | "issues" | "releases"
origin   = "topic:agent-cli-installers"  # "topic:<slug>" | "dep:<pkg>@<ver>" | "dep:<pkg>@<ver>:<feature>"
question = "How do real repos install Claude Code via the native installer?"   # human prose (Q11)
cadence  = "weekly"                      # "daily" | "weekly" (Q8)
tags     = ["agent-cli", "installer"]
limit    = 10                            # optional, default 10, 1..100 (per_page)

# kind = "code" — rev 1's fields, with `code` renamed to `queries`
queries  = ['"claude.ai/install.sh" filename:mise.toml', '"claude.ai/install.sh" filename:Dockerfile']
grep      = 'claude\.ai/install\.sh'     # content regex a re-fetched hit must match (Q2)
path_grep = ''                           # optional path regex; at least one of grep/path_grep non-empty
control_hit           = '"[tools]" filename:mise.toml'   # must return ≥1 CONFIRMED hit, every run
control_hit_grep      = '^\[tools\]'
control_hit_path_grep = ''
control_absent        = '"{nonce}" filename:mise.toml'   # MUST contain {nonce}; must return total_count == 0 (Q1)

# kind = "issues" — REST search/issues `q` strings (Q3: the short-terms field non-code kinds need)
# queries = ['repo:yanyongyu/githubkit is:issue "rate limit"']
# control_hit / control_absent as above; grep/path_grep not used (title+state are the record)

# kind = "releases" — ETag-polled; no queries, no grep
# repo = "yanyongyu/githubkit"
# include_prereleases = false            # optional
# allow_empty = false                    # a 200 with zero releases is invalid-control unless true
```

- Carried from rev 1: **Q1** (the absent control is a `{nonce}` template, rendered fresh from
  `secrets.token_hex(8)` on every run and never written back), **Q2** (one `grep`/`path_grep` pair per id), **Q3**
  (non-code kinds carry their own short query strings), **Q8** (weekly seeds) and **Q11** (paraphrased `question`
  prose, verbatim queries).
- `origin` is validated by shape. A `dep:` origin names a package that must appear in `python/pyproject.toml`
  `dependencies`, or in a `[[watch]] kind = "releases"` entry, so an adopted-feature watch cannot outlive the
  dependency unnoticed.
- `releases` controls: a `304` or a `200` carrying ≥1 release is the positive answer. A `200` with zero releases is
  `invalid-control` unless `allow_empty = true`. A `404` on the repo is `error`, never "no releases".

Loader validation happens before any network call. A failure exits with rc 2 and names the id and field:

- unknown keys, a duplicate id or a malformed id;
- an unknown `kind`, or fields that are illegal for that kind;
- `kind = "code"`/`"issues"` without non-empty `queries`, or `kind = "releases"` without `repo`;
- a code query containing ` OR `, `(`, `)` or `**` (the legacy engine, PREMISES 36);
- `control_absent` without `{nonce}`;
- a code watch with neither `grep` nor `path_grep`;
- a regex that does not compile;
- `limit` out of range;
- a malformed `origin`, or a `dep:` package that nothing declares;
- `schema_version` other than 1.

**Seed set.** The seeds are the 14 rev-1 topic ids, unchanged, plus 7 githubkit dependency ids.

1. **The 14 rev-1 topic ids** carry over verbatim: same ids, same query strings (the rev-1 `code` field is now
   `queries`), same grep/path_grep, same controls. Each gets `kind = "code"`. The four conf.d ids (the first four
   rows, whose lines cite the confd report) get `origin = "topic:mise-confd"`. The other ten, whose lines cite the
   native-installers report (including `mise-disable-tools`), get `origin = "topic:agent-cli-installers"`. The table below is copied **byte-for-byte from rev 1 §3.1**. Rev 1 was
   never committed, so this copy is its only record. Line references point into the two seed reports
   (`confd` = `mise-confd-github-examples-2026-09-30.md`, `native` = `native-installers-github-examples-2026-09-30.md`;
   PREMISES 35).

| id | `code` alternatives (source line) | `grep` / `path_grep` |
|---|---|---|
| `mise-confd-layout` | `path:.config/mise/conf.d` (confd `:24`), `path:dot_config/mise/conf.d` (`:38`) | path_grep `mise/conf\.d/` |
| `mise-confd-tasks` | `path:.config/mise/conf.d tasks` (`:52`) | path_grep `mise/conf\.d/`; grep `^\s*\[tasks` |
| `mise-confd-symlink` | `"mise/conf.d" ln` (`:66`), `"mise/conf.d" symlink` (`:80`) | grep `mise/conf\.d` |
| `mise-global-config-tasks` | `path:.config/mise filename:config.toml tasks` (`:94`), `path:dot_config/mise filename:config.toml tasks` (`:108`) | grep `^\s*\[tasks` |
| `mise-disable-tools` | `"disable_tools" filename:mise.toml` (native `:47`), `"disable_tools" path:.config/mise` (`:73`), `"disable_tools" language:TOML` (`:101`) | grep `disable_tools` |
| `disable-tools-agent-clis` | `"disable_tools" "codex" language:TOML` (`:1010`), `"disable_tools" "claude" language:TOML` (`:1045`) | grep `disable_tools.*(codex\|claude)` |
| `agent-cli-task-names` | `"update:codex"` (`:130`), `"update:claude"` (`:165`), `"install:agy"` (`:203`), `"install:claude"` (`:233`), `"install:codex"` (`:261`) | grep `(update\|install):(codex\|claude\|agy)` |
| `claude-native-installer` | `"claude.ai/install.sh"` + `filename:mise.toml` (`:293`), `filename:Dockerfile` (`:320`), `filename:devcontainer.json` (`:346`), `path:.chezmoiscripts` (`:372`), `dotfiles` (`:398`), `"postCreateCommand"` (`:730`) | grep `claude\.ai/install\.sh` |
| `claude-code-npm-and-feature` | `"npm:@anthropic-ai/claude-code" filename:mise.toml` (`:425`), `"@anthropic-ai/claude-code" filename:Dockerfile` (`:452`), `"ghcr.io/anthropics/devcontainer-features/claude-code" filename:devcontainer.json` (`:479`) | grep `anthropic-ai/claude-code\|devcontainer-features/claude-code` |
| `codex-install-paths` | `"npm:@openai/codex" filename:mise.toml` (`:505`), `"github:openai/codex" filename:mise.toml` (`:531`), `"@openai/codex" filename:Dockerfile` (`:539`), `"@openai/codex" filename:devcontainer.json` (`:565`), `"openai/codex/releases" filename:Dockerfile` (`:591`) | grep `openai/codex` |
| `codex-native-installer` | `"chatgpt.com/codex/install.sh"` + `filename:mise.toml` (`:771`), `filename:Dockerfile` (`:788`), `filename:devcontainer.json` (`:814`), `path:.chezmoiscripts` (`:840`), bare (`:861`) | grep `chatgpt\.com/codex/install\.sh` |
| `agy-install-paths` | `"antigravity-cli" filename:mise.toml` (`:619`), `"antigravity" filename:Dockerfile` (`:648`), `"agy" filename:mise.toml` (`:693`) | grep `antigravity\|\bagy\b` |
| `agy-native-installer` | `"antigravity.google/cli/install.sh"` + `filename:mise.toml` (`:892`, 0 hits today, kept on purpose to catch the first appearance), `filename:Dockerfile` (`:898`), `filename:devcontainer.json` (`:926`), `path:.chezmoiscripts` (`:952`), bare (`:970`) | grep `antigravity\.google/cli/install\.sh` |
| `agent-cli-self-update-tasks` | `"claude update" filename:mise.toml` (`:759`), `"codex update" filename:mise.toml` (`:998`), `"agy update" filename:mise.toml` (`:1004`) | grep `(claude\|codex\|agy) update` |

   Rev-1 controls, unchanged:

   - The conf.d ids use the must-hit `path:.config/mise filename:config.toml` (confd `:7`), with
     `control_hit_grep = ''` and `control_hit_path_grep = '\.config/mise/config\.toml$'`. The absent control is
     `"{nonce}" path:.config/mise`.
   - The native ids use the must-hit `"[tools]" filename:mise.toml` (native `:15`) and the absent control
     `"{nonce}" filename:mise.toml`.

   The implementer must re-read each cited seed-report line and confirm that the string matches before copying it.
   These strings were inherited, not re-read this session.
2. **The 7 githubkit ids.**
   - Controls for the code ids: must-hit `"from githubkit import GitHub" language:Python` (444 hits on 2026-09-30,
     R§11) with `control_hit_grep = 'from githubkit import'`, and absent `"{nonce}" language:Python`.
   - Hit counts are unconfirmed, n=1, 2026-09-30.

| id | kind | origin | queries (hits) | grep |
|---|---|---|---|---|
| `githubkit-releases` | releases | `dep:githubkit@0.16.1` | `repo = "yanyongyu/githubkit"` | — |
| `githubkit-async-usage` | code | `dep:githubkit@0.16.1:async-api` | `arequest githubkit language:Python` (206) | `\barequest\(\|async with GitHub\(` |
| `githubkit-action-auth` | code | `dep:githubkit@0.16.1:ActionAuthStrategy` | `ActionAuthStrategy language:Python` (11) | `ActionAuthStrategy` |
| `githubkit-retry-config` | code | `dep:githubkit@0.16.1:auto-retry` | `RetryRateLimit githubkit language:Python` (6) | `RetryRateLimit\|RetryChainDecision\|auto_retry\s*=` |
| `githubkit-http-cache-off` | code | `dep:githubkit@0.16.1:http_cache` | `"http_cache=False" githubkit` (24) | `http_cache\s*=\s*False` |
| `githubkit-anyio-tests` | code | `dep:githubkit@0.16.1:anyio-testing` | `"pytest.mark.anyio" githubkit` (7) | `pytest\.mark\.anyio` |
| `githubkit-with-msgspec` | code | `dep:githubkit@0.16.1:msgspec-decode` | `githubkit msgspec filename:pyproject.toml` (2: Crimone/Scoparia, wyf7685/Bot7685) | `githubkit` (content) and path_grep `pyproject\.toml$` |

(`\|` in the table is markdown escaping. In the TOML the character is a plain `|`.)

About 54 code alternatives plus shared controls come to roughly 9-10 minutes of paced `search/code` per full run, so
the cadence stays weekly (Q8).

### 3.2 `github_watch.py`: the async engine

- **Client.** There is one client per invocation:
  `async with client_factory(token) as gh:`. The default factory builds
  `GitHub(token, http_cache=False, auto_retry=RetryChainDecision(RetryRateLimit(max_retry=2), RetryServerError(max_retry=3)), rest_api_validate_body=False, timeout=httpx.Timeout(10.0, read=30.0), user_agent="dotfiles-github-watch")`.
  - The entrypoint is `anyio.run(_amain, ...)`. githubkit is anyio-native (`core.py:674` `anyio.sleep`,
    `throttling.py` `anyio.Semaphore`).
  - Tests inject a factory that passes `async_transport=httpx.MockTransport(handler)`.
  - The docs strongly recommend the context manager, because repeated clients leak memory (PREMISES 1).
- **Token.** Read `GITHUB_TOKEN`, then `GH_TOKEN`, from the environment. If neither is set, exit with rc 2 and the
  message `no GitHub token in GITHUB_TOKEN/GH_TOKEN (presence checked; value never read into output)`. Never shell
  out to `gh auth token` or `fnox get` (`secrets-out-of-the-shell-env.md`, keychain hang). Never print, log or write
  the token.
- **Calls.** Use `await gh.arequest(method, url, params=..., headers=...)` only.
  - Decode `resp.content` with `codec.decode(resp.content, <Struct>)` into private msgspec Structs that declare only
    the fields we read. msgspec ignores unknown fields, so upstream schema growth cannot break a run. This is the
    failure githubkit's own pydantic models hit in #293.
  - **Never** touch `Response.parsed_data`, `gh.rest.paginate` without `map_func`, or any `githubkit.webhooks` /
    `githubkit_schemas` symbol (§4).
- **`kind = "code"`.**
  1. The search call is `GET /search/code` with `params={"q": q, "per_page": limit}`, paced (below).
  2. For each item, re-fetch the file at its indexed ref: `GET item.url` with `Accept: application/vnd.github.raw`
     (core bucket, not paced).
  3. An item is **confirmed** when every given pattern matches: `path_grep` against `repository.full_name + "/" +
     path`, and `grep` (multiline) against the decoded bytes. A re-fetch failure is unconfirmed, never confirmed.
  4. The result records `total_count`, `incomplete_results` and `truncated = incomplete_results or total_count >
     1000`. The REST search cap is 1,000 per query (PREMISES 36).
- **`kind = "issues"`.** `GET /search/issues`, paced at ≥2.0 s (the search bucket is 30/min). Items are keyed by
  `html_url` and carry `state`, `merged` (from `pull_request.merged_at`) and `updated_at`.
- **`kind = "releases"`.** `GET /repos/{o}/{r}/releases?per_page={limit}` with `If-None-Match: <etag>` taken from
  the newest `ok` `runs.jsonl` row for the id.
  - A `304` means unchanged: githubkit returns it as a normal `Response`, because `_check` raises only when
    `is_error` (`core.py:414-445`). A `304` is free against the primary limit (measured, R§04 A).
  - A `200` gives the new ETag plus items `{tag, html_url, published_at, prerelease}`.
  - Search endpoints return no ETag (measured, R§04 C), so ETags apply to `releases` only.
- **Pacing.** A process-wide async `_Pacer` (an `anyio.Lock` plus injectable `clock`/`sleep`) enforces at least
  6.0 s between the starts of consecutive `search/code` requests, and at least 2.0 s for `search/issues`. It covers
  primary queries and controls alike.
  - githubkit's `LocalThrottler(100)` caps **concurrency**, not rate (`throttling.py`), so it is not a substitute.
  - Code and issue searches run sequentially. Release polls may run concurrently in an `anyio` task group behind a
    `CapacityLimiter(4)`.
- **Rate limits (never zero).**
  - `PrimaryRateLimitExceeded`/`SecondaryRateLimitExceeded` after retries, and a `RequestFailed` with status 403 or
    429, make the id `error` with a reason starting `rate limited:`.
  - A 403 can never yield an empty result.
  - The code_search bucket is **per user or installation and shared** with every concurrent lane (a 403 was
    measured mid-session, R§11).
- **Snapshots (Q4 carried).** Raw response bytes are written to
  `.agent/kb/raw/github-watch/<id>/<YYYYMMDDTHHMMSSZ>/<part>.json` with `mkdir(exist_ok=False)`, so a snapshot is
  never overwritten.
  - `<part>` is `q<n>` per query, `fetch-<sha12>` per re-fetch, `control-hit`, `control-absent` or `releases`.
  - Response headers are **not** stored, because a request's `Authorization` header must never reach disk (§4).
  - In CI the stamp directory is uploaded as an Actions artifact (§3.7).
  - "The previous snapshot" for the diff is the committed `<id>.jsonl` (Q4).

### 3.3 Canonical URL, normalized line, diff

These follow rev 1 §3.4, with these changes:

- **Canonical URL.** Lowercase the scheme and host, drop the query, fragment and trailing `/`, and replace the
  `<ref>` of `github.com/<o>/<r>/blob/<ref>/<path>` with `HEAD`.
- **Normalized line**, sorted by key, `codec.encode` with sorted keys: `{"key", "url", "kind", "alternative",
  "rank", "title_sha256" (16 hex), "state", "merged", "updated_at", "tag", "blob_sha", "published_at",
  "first_seen", "last_changed", "status"}`.
  - `status` is one of `present`, `dropped` or `deleted`.
  - There is no `last_seen`, no snippet and no release body.
  - An unchanged item's line is byte-identical from run to run.
- **Diff states.**
  - **added**: the key is new, or it comes back from `dropped`/`deleted`.
  - **changed**: any of `state`, `merged`, `tag`, `blob_sha`, `updated_at`, `published_at` or `title_sha256`
    differs.
  - **dropped-from-top-N**: previously `present`, absent now.
  - **deleted**: a dropped item whose direct GET returns 404 or 410, read as
    `RequestFailed.response.status_code`.
    - Code uses `GET /repos/<o>/<r>/contents/<path>`.
    - An issue or PR uses `GET /repos/<o>/<r>/issues/<n>`.
    - A release uses `GET /repos/<o>/<r>/releases/tags/<tag>`.
    - Any other status or exception leaves the item `dropped`. Non-GitHub URLs are never probed.
- **A broken control never rewrites the index.** If `control_hit` returns 0 confirmed hits, `control_absent` returns
  `total_count > 0`, or any query is `error`, the id's `<id>.jsonl` is left byte-identical and nothing is marked
  dropped or deleted.

### 3.4 CLI and outputs

```
github-watch [ID ...] [--registry PATH] [--all] [--list] [--kind code|issues|releases]
```

- The bare command runs every due id. `-- <id> [...]` runs the named ids regardless of cadence. `--all` runs
  everything. `--kind` filters. `--list` prints `id  kind  cadence  last-run  origin` and exits 0.
- An id is due when its newest `status == "ok"` row in `runs.jsonl` is older than 1 day (`daily`) or 7 days
  (`weekly`), or when it has no such row.
- Outputs are written only after every selected id has run:
  - `docs/research/kb/watch/<id>.jsonl`, for ok ids only. Every line is re-parsed after writing.
  - An appended `runs.jsonl` row per id: `{stamp, id, kind, status, added, changed, dropped, deleted, truncated,
    etag, controls:{hit_confirmed, absent_total}, snapshot_dir, digest}`.
  - `docs/research/kb/watch/digests/<stamp>.md`. It opens with a status table, then lists
    `[title](url)` lines per id. New releases appear as `[tag](html_url)` under a **"Release notes to review"**
    heading, which carries the `dep:` origin.
- stdout is the digest path, then one line per id: `<id>  <status>  +A ~C -D xX`.
- Exit codes: 0 when every selected id is ok; 1 on any `invalid-control`/`error` or a write failure; 2 on a usage
  error, a registry error, an unknown id or a missing token; 130 on Ctrl-C.

### 3.5 `graphify save-result` task

Unchanged from rev 1. `mise run graphify-save-result -- --question Q --answer A --outcome
{useful,dead_end,corrected} [--correction TEXT] [--nodes N ...]` builds `graphify save-result --question Q
--answer A --type query --outcome O [...]` and runs it through `graphify._run`.

- It is host-only, and it is never called from CI or from `github_watch`.
- The installed 0.9.65 accepts `--outcome`, and `--nodes` is optional (PREMISES 33).

### 3.6 Skills

- **`.claude/skills/github-watch/SKILL.md` (new).** Its description names the triggers: "re-run a tracked GitHub
  search", "what's new since last time", "a dependency released", "add/tune a watch". The body covers:
  1. `mise run github-watch -- --list`, and running by id or `--kind`.
  2. Reading the digest, never the raw tree.
  3. Adding or tuning an entry: keep the id; one legacy query per alternative; set both controls; follow the
     `{nonce}` rule.
  4. **The dependency release loop**, a judgment step owned by the skill, never by code:
     - a new release in the digest → read its notes (`gh release view <tag> -R <repo>`);
     - classify each item as fix or feature, and as applies to us or not;
     - for every feature we **adopt**, add a `kind = "code"` watch with `origin = "dep:<pkg>@<ver>:<feature>"` in a
       reviewed diff, bump the `releases` watch's `origin` version, and record retirements
       (`tool-currency-and-native-first.md`).
  5. `mise run graphify-save-result -- --question "github-watch:<id>" --answer "<digest>: <one line>" --outcome
     useful|dead_end` (host only).
  6. Traps:
     - a 403 is a rate limit, and the bucket is shared across lanes;
     - `invalid-control` means "probe broken", not "no change";
     - `dropped` is not `deleted`;
     - a `304` is "unchanged", not "empty";
     - never read `parsed_data`.
- **`.claude/skills/research-sweep/SKILL.md` (modify).** In step 1, before writing fresh code-search queries, check
  `watches.toml` for an id that covers the question and run `mise run github-watch -- <id>`. A code-search query
  worth re-running gets a `watches.toml` entry in the same change. The GitHub code-search trap now points at
  `github-watch` instead of a hand-run `gh api` recipe, keeping its syntax and rate-limit facts. Stay inside
  `md_size_budget`.

### 3.7 `.github/workflows/github-watch.yml`

This follows **Q7 accepted (its own file)** with **refresh.yml's schedule and App token (Q9 ruled)**. The conflict
between the two readings is Q7b.

- **Triggers.** `schedule: - cron: "0 0 * * *"` with `timezone: "America/Chicago"` (refresh.yml:42-44), plus
  `workflow_dispatch`. There is no `pull_request` trigger. The daily cron is safe with weekly seeds because the
  task's cadence filter picks what is due.
- **Permissions.** The workflow-level default is `{}`. The job has `contents: read` and `issues: write`.
- **Job env.** `HK_SKIP_HOOKS: pre-commit,pre-push` (ADR-0001; `workflow_hooks.py`).
- **Steps.**
  1. Mint the App token with `actions/create-github-app-token`, using the **same SHA pin and secrets** as
     refresh.yml:92-98 (`REFRESH_APP_ID`, `REFRESH_APP_PRIVATE_KEY`), with `permission-contents: write` and
     `permission-pull-requests: write`.
  2. Checkout with `persist-credentials: false`.
  3. `setup-mise` with `install_args: "python uv"`.
  4. `mise run --skip-tools github-watch` with `GITHUB_TOKEN: ${{ steps.app-token.outputs.token }}` (Q9). Record the
     task rc in a step output. Do not use `continue-on-error`.
  5. `actions/upload-artifact` of `.agent/kb/raw/github-watch/` (`if: always()`), mirroring the `tool-currency`
     report artifact (refresh.yml:224-230). The snapshots hold response bodies only, never headers (§3.2).
  6. `open-refresh-pr` with `paths: docs/research/kb/watch/`, `branch: chore/github-watch`,
     `labels: needs-triage`, `summary-heading: GitHub watch` and `auto-merge: "true"` (Q2b accepted). Its inputs
     are listed at `action.yml:11-39`.
  7. Upsert the standing issue `GitHub watch report` with the newest digest as its body, using exact-title matching.
     Close the issue when every id is ok with zero changes. This follows the refresh.yml:161-223 semantics, with
     `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` as there.
  8. `exit` with the recorded rc.
- Every action is SHA-pinned exactly as in refresh.yml.

### 3.8 Adjacent decisions this spec carries (research points B1-B5)

- **B1, async and tests.** Use anyio's built-in pytest plugin: `@pytest.mark.anyio`, or a module-level
  `pytestmark`, plus the conftest `anyio_backend` → `"asyncio"`. Do **not** add pytest-asyncio. Mock through
  `GitHub(async_transport=httpx.MockTransport(...))` via `client_factory`.
  - This is githubkit's own pattern (its `tests/conftest.py:6-8` and the unit-test docs).
  - It was proven live in a scratch venv: 2 passed, and the `-p no:anyio` control failed rc=1 (R§09).
  - Latest versions: anyio 4.15.1 and pytest 9.1.1. pytest-asyncio 1.4.0 is noted only as the rejected
    alternative.
- **B2, pydantic.** githubkit imports pydantic at module import, so it cannot run without it. Its validation is
  lazy and opt-in: `parsed_data` validates, while `content` and `json()` are raw. The recommendation is to adopt it
  as a transport and never validate through it. The full reasoning is in the "Recommendation" section of the final
  report and R§02-03.
- **B3, cache.** Set `http_cache=False` and poll ETags explicitly. Hishel's persisted sqlite stores the
  Authorization token in plaintext (measured, R§04). A disk cache is therefore banned in this change (§4).
- **B4, ty.** The gate's ty is `python/uv.lock` 0.0.76, and the latest is 0.0.84. ty LSP for Claude Code and codex
  is Q15/Q16 and is not part of this diff.
- **B5, currency.** githubkit rides Dependabot (bump PRs) and `mise run dependency-currency` (first-level behind)
  with no configuration. Its release-note review runs through the `githubkit-releases` watch and the §3.6 loop. A
  deep `currency.toml` entry is Q14.

## 4. Constraints and invariants

- **Strict-five is untouched.** `research_fanout.py` is not edited at all. `validate_strict_five`
  (`research_fanout.py:1468`) and its consumer `scripts/codex-research-gate.py:17-19,101` therefore cannot drift.
- **pydantic boundary (B2).** First-party code never reads `githubkit.Response.parsed_data`, never calls
  `gh.rest.paginate` without `map_func`, and never imports `githubkit.webhooks` or `githubkit_schemas` (ruff TID251,
  §2). Every model is a msgspec `Struct` decoded through `dotfiles_setup.codec` (the #675 policy,
  `python/AGENTS.md:85-103`).
  - **Machine teeth.** An autouse fixture in `test_github_watch.py` monkeypatches `Response.parsed_data` to raise.
    Every engine test runs under it. One test asserts that the fixture fires when `parsed_data` is touched: the
    control arm, run live in R§09.
- **No persistent HTTP cache (B3).** `http_cache=False` is a constructor argument that a test asserts on the default
  factory. No hishel storage path, no `.cache/hishel/`, and no `actions/cache` of any githubkit or hishel state.
  - Reason: hishel's sqlite persists request headers, including `Authorization` (R§04).
  - If a disk cache is ever wanted, it is a follow-up. It must live under `.agent/cache/githubkit/` and be treated
    as a credential file.
- **A 403/429/rate limit is ERROR, never EMPTY.** A test drives a MockTransport 403 carrying
  `x-ratelimit-remaining: 0` and asserts `error` with a `rate limited:` reason, rc=1, and an untouched jsonl.
- **A broken control never rewrites the index.** The rev-1 test stands: flip must-hit to 0 confirmed, then assert
  the file is byte-identical and rc=1.
- **Deleted requires a direct 404/410.** 403, 5xx and timeouts yield `dropped`. Both arms are tested.
- **A 304 is unchanged, never empty.** A releases test replays 200 (ETag e1) then 304 (If-None-Match e1). It asserts
  zero added, zero changed, a byte-identical jsonl, and that the second request carried the header.
- **Stable bytes.** Running the same fake twice gives byte-identical jsonl, and `last_changed` does not move.
- **The known-absent control is fresh on every run.** Two invocations render different nonces, and no rendered
  nonce is written anywhere tracked. A hand-written absent term in tests is built by string concatenation.
- **No third-party text in tracked files beyond titles, tags and URLs.** `docs/research/kb/` is secret-scanned by
  path (`suites.toml:2135-2154`) and excluded from hk builtins (`hk-common.pkl:52`), so `github_watch` validates
  what it writes.
- **Pacing is enforced in code.** No more than 10 `search/code` starts in any 60 s window, including controls,
  tested with the injected clock. githubkit's throttler does not count.
- **Credentials.** The token comes from env only. No token value appears in any written file, stdout, snapshot or
  reason. Extend the repo's sentinel-token test pattern to `github_watch`: put a sentinel in `GITHUB_TOKEN`, run a
  full fake cycle, and grep every output for it.
- **No live network in tests.** Use the `client_factory` + `MockTransport`, `clock` and `sleep` seams only.
- **Graphify only through the mise task**, host-only, never from CI or `github_watch`.
- **Repo Python standards.** `ruff` + `ty` clean at the locked versions, Google docstrings, no inline suppressions,
  and a module docstring that says WHY githubkit is transport-only. Do not import `kb_setup`.
- **Lane allowlist.** Exactly the files in §2. The lane must not touch `research_fanout.py`,
  `docs/research/kb/{reports,raw}/**`, `.agents/**` (regenerated by the task only), `scripts/`,
  `.claude/workflows/`, `.claude/settings.json` or `currency.toml`.

## 5. Verification

Implementer (every command reports its real rc from a file-captured log, never a piped tail):

```bash
uv run --project python pytest tests/test_github_watch.py -q
uv run --project python pytest tests/ -x -q
mise run gate -- run lint
mise run gate -- run verify
mise run gate -- run lint-docs          # new/changed SKILL.md, python/AGENTS.md
mise run gate -- run pin-actions        # new workflow
mise run skills-mirror -- --check        # after `mise run skills-mirror`
mise run token-check -- python/verification/suites.toml "<each new token>"
mise run github-watch -- --list          # rc=0; 21 seed ids
```

Required tests, each with its fail arm stated in a comment:

- the registry validator (every §3.1 rule, one negative fixture each, including `dep:` origin resolution);
- code confirm, unconfirm and re-fetch error;
- the 403 rate-limit case;
- pacer spacing (code 6 s, issues 2 s);
- the ETag 200 → 304 cycle;
- releases `allow_empty`;
- canonicalization of two blob refs to one key;
- diff added, changed, dropped and deleted (404 and 410) plus 403 → dropped;
- broken-control no-rewrite;
- byte-stable lines;
- nonce freshness;
- cadence due and not-due;
- exit codes 0/1/2 (including the missing token → 2);
- the `parsed_data` guard and its firing control;
- `http_cache=False` on the default factory;
- the sentinel-token sweep;
- `graphify save-result` argv (with and without `--correction`).

Architect's live arms, per `real-integration-evidence.md`:

1. **Positive:** `mise run github-watch -- mise-disable-tools` gives rc=0, a digest with `hit_confirmed ≥ 1` and
   `absent_total == 0`, and a new jsonl.
2. **Negative (must fail):** run a scratch registry copy with a corrupted `control_hit` via `--registry <copy>`.
   It gives rc=1 and `invalid-control`, and the arm-1 jsonl stays byte-identical.
3. **Stable bytes:** re-run arm 1 immediately. Expect zero added, zero changed and an empty `git diff`.
4. **ETag:** `mise run github-watch -- githubkit-releases` twice. The second `runs.jsonl` row reads status `ok` with
   0 added. Cross-check the free 304 with a one-shot
   `gh api -i -H "If-None-Match: <etag>" repos/yanyongyu/githubkit/releases?per_page=10`, which returns `304`; a bogus
   ETag is the control.
5. `mise run graphify-save-result -- --question "github-watch:mise-disable-tools" --answer "<digest>: arm" --outcome useful`
   gives rc=0, and `graphify-out/memory/` now exists.
6. After merge: `mise run gha-dispatch -- github-watch.yml`, then a one-shot `gh run view <id> --json conclusion`.
   Its digest proves the **App installation token** can call `search/code` against public repos (PREMISES A1). A red
   `invalid-control` on every code id means A1 is refuted and Q9 needs a different token.

## 6. Commit

`caller`. Leave the tree uncommitted, and report the changed paths plus the real exit code of every §5 implementer
command. The caller runs the §5 live arms and ships through `mise run ship` on a dedicated branch cut from `main`,
for example `feat/github-watch` (**Q10 accepted**). The spec, the githubkit docs mirror and the design report move to
that branch with it.

## 7. PREMISES

Kinds: P = precedent, I = interface, L = local fact, E = evidence record, A = assumption (unverified, reason
stated). Every row was read or measured **this session** (2026-09-30, rev-2 lane) unless marked inherited.
Repository paths are in the worktree `dotfiles.worktrees/agy-native-20260930`. githubkit source paths are the tag
`v0.16.1` (commit `d043cb66`), cloned to the scratchpad. `$CC` is
`knowledge-base/sources/agent-harness-docs/docs/claude-code`.

| # | Kind | Claim | Source |
|---|---|---|---|
| 1 | P | Use one `async with GitHub(...)` per workload; repeated clients leak memory; re-entry raises `RuntimeError` | `docs/research/kb/raw/githubkit-docs-0.16.1/source/usage/getting-started/reusing-client.md` |
| 2 | I | Validation is lazy: only `parsed_data` validates; `content`/`json()` are raw | githubkit `response.py:85-102` |
| 3 | I | githubkit imports pydantic at module import | githubkit `compat.py:4`, `typing.py:15`, `utils.py:6` |
| 4 | I | `paginate` validates through `parsed_data` unless `map_func` is given | githubkit `paginator.py:107-109`, `:126-128` |
| 5 | I | A 304 is not an error: `_check` raises `RequestFailed` only when `is_error`; the client sends `Cache-Control: no-cache` | githubkit `core.py:414-445`, `:260` |
| 6 | I | Retry defaults: rate limit once (`retry_after`), 5xx three times with quadratic backoff; async sleep is `anyio.sleep` | githubkit `retry.py:9-31`, `:34-60`, `:80`; `core.py:674` |
| 7 | I | Config knobs `http_cache`, `cache_strategy` (default `MemCacheStrategy`), `throttler`, `auto_retry`, `rest_api_validate_body`, `async_transport` | mirror `source/usage/getting-started/configuration.md` |
| 8 | I | The default hishel storage is in-process sqlite `:memory:` | githubkit `hishel.py:55-126`, `cache/mem_cache.py:68-77` |
| 9 | L | Manual `If-None-Match` → 304 with rate-limit remaining unchanged; bogus-ETag control 200 costs 1; same-client hishel revalidation shows 200 + `hishel_from_cache`; `search/code` has no ETag | R§04 (live; raw `.agent/kb/raw/github-watch-2026-09-30/p1.out`) |
| 10 | L | A persisted hishel sqlite held the live token (count 1, value never printed); hishel auto-creates `.cache/hishel` with a `*` gitignore | R§04 (live, db deleted); hishel 1.4.0 `_utils.py:110-119` |
| 11 | I | `ActionAuthStrategy` reads `GITHUB_TOKEN`; a plain string is a token | mirror `source/usage/getting-started/authentication.md:241-262` |
| 12 | P | anyio's pytest plugin ships in anyio; the marker coexists; `anyio_mode=auto` conflicts with pytest-asyncio auto | `anyio/docs/testing.rst:4-6`, `:29-35`, `:62-72` @4.15.1 (raw copy `.agent/kb/raw/github-watch-2026-09-30/anyio-testing.rst`) |
| 13 | P | githubkit's own suite uses `@pytest.mark.anyio` + `anyio_backend` → `"asyncio"` | githubkit `tests/conftest.py:6-8`, `tests/test_rest/test_call.py:55` |
| 14 | L | Live: 2 passed with anyio only; `-p no:anyio` → 2 failed, rc=1 | R§09 |
| 15 | L | No async code or tests exist in the repo today | grep `async def\|asyncio` over `tests/`, `python/src` → 0 files |
| 16 | L | pydantic 2.13.4 is already required by anthropic, mcp, mcp-types, openai (via graphifyy[all], kb-setup) and pydantic-settings | `uv tree --invert --package pydantic --frozen` (R§03) |
| 17 | L | `config.py` is the only first-party pydantic importer | grep `import pydantic\|from pydantic` over `python/src` |
| 18 | P | The codec / TID251 policy and its ban list | `python/AGENTS.md:85-103`; `python/pyproject.toml:94-136` |
| 19 | L | Project deps (msgspec, pydantic) and the dev group | `python/pyproject.toml:6-42`, `:186-195` |
| 20 | L | ty is pinned only in `python/uv.lock:2543-2544` (0.0.76); latest is 0.0.84 (PyPI, GitHub); the bare `ty` shim is unset | R§05 |
| 21 | L | New packages githubkit brings: githubkit, githubkit-schemas(+2026-03-10), hishel, anysqlite, msgpack; httpx/anyio already locked | R§13; `python/uv.lock` grep |
| 22 | P | Thin `tool-currency` task over the shared engine | `mise.toml:661-668` |
| 23 | L | The currency engine reports DRIFT for a binaryless python library (`.venv/bin/githubkit is missing`); the graphify control is ok | R§10 (live engine call); `kb_setup/currency/sync.py` `_check_python_resolution`; `config.py:517-521` (`source_only` needs a manifest) |
| 24 | P | The `python_package` deep-tracking precedent | `currency.toml:41-59` (`[tool.graphify]`) |
| 25 | P | Dependabot is the only Python updater; daily grouped PR; 7-day cooldown | `.github/dependabot.yml:1-6`, `:16-40`; `renovate.json` `enabledManagers` has no pip/pep621 |
| 26 | P | The `python -m` thin-task form | `mise.toml:868-871` |
| 27 | I | The strict-five validator and its codex-gate consumer | `research_fanout.py:1468`; `scripts/codex-research-gate.py:17-19`, `:101` |
| 28 | P | refresh.yml schedule, App-token mint, standing-issue upsert, artifact upload | `.github/workflows/refresh.yml:42-44`, `:84-98`, `:161-230` |
| 29 | P | `open-refresh-pr` inputs | `.github/actions/open-refresh-pr/action.yml:11-39` |
| 30 | P | Every committing job sets `HK_SKIP_HOOKS` | `python/src/dotfiles_setup/workflow_hooks.py:1-26` |
| 31 | L | `.agent/` is gitignored | `.gitignore:124` |
| 32 | L | `docs/research/kb` is secret-scanned by path and excluded from hk builtins | `python/verification/suites.toml:2135-2154`; `hk-common.pkl:52` |
| 33 | I | graphify tasks; vendor `save-result` form; installed 0.9.65 has `--outcome` (and `--nodes` defaults `[]`) | `mise.toml:799-866`; `.claude/skills/graphify/references/query.md:171`, `:176`; `python/.venv/.../graphify/cli.py:1461-1475`; `python/uv.lock` graphifyy 0.9.65 |
| 34 | P | The skills mirror is generated by a task | `mise.toml:1359-1362` |
| 35 | E | Rev-1 seed queries and controls (the 14 topic ids) | **inherited** from rev 1 §3.1 and its PREMISES 29-30 (`mise-confd-github-examples-2026-09-30.md`, `native-installers-github-examples-2026-09-30.md`); not re-read this session |
| 36 | L | Code search: 10/min (`x-ratelimit-resource: code_search`), legacy engine (no OR/regex), 1,000-result cap, default branch only | docs.github.com REST search body line 18 (fetched this session); live header R§04 C; cap/legacy **inherited** from `github-api-vs-cli-vs-sdk-2026-09-30.md:19-30` |
| 37 | E | githubkit seed hit counts; a fresh-nonce absent control returned 0; the shared bucket then returned 403 | R§11 |
| 38 | E | githubkit docs mirror at 0.16.1 (site = tag; 18 pages ×2) | `docs/research/kb/raw/githubkit-docs-0.16.1/README.md` |
| 39 | L | `ray-manaloto/dotfiles` is public and code-search indexed: `research_fanout repo:ray-manaloto/dotfiles` → 19 | R§04 C (live) |
| 40 | I | Claude Code LSP servers come only from plugins; placeholders resolve in `command/args` | `$CC/plugins-reference.md:199-277`, `:696-713` |
| 41 | L | Settings disable pyright-lsp, pyright and astral (astral ships a `uvx ty@latest server` LSP) | `.claude/settings.json:176-177`, `:183`; R§06 |
| 42 | L | codex has no LSP client (0 docs/schema/release hits; controls hit) | R§07 |
| A1 | A | The `REFRESH_APP_ID` App's **installation** token can call `search/code` over public repos. Neither the docs body nor any probe settles it; §5 arm 6 proves or refutes it | none |
| A2 | A | githubkit's `RetryRateLimit(max_retry=2)` + our pacer keeps a full weekly run (~54 code calls) inside the bucket without a hard failure; not run at full size | none |

## Open questions for the architect (STOP: ratify or amend before dispatch)

Each question has a recommendation. PRO/CON are given in prose because this lane cannot call `AskUserQuestion`.

**Carried and accepted (no action):**

- Q1, Q2, Q2b, Q3, Q4, Q6, Q8, Q10, Q11: rev-1 recommendations, accepted by Ray.
- Q5: moot, because 0.9.65 has `--outcome` (PREMISES 33). The separate graphify bump PR stands; it is on
  `chore/currency-20260930`.
- Q7: its own workflow file.
- Q9: ruled, use the existing App token.

**New or re-opened:**

- **Q7b: "refresh.yml schedule" vs Q7-accepted "its own file".** These conflict if "refresh.yml schedule" means
  *a job inside refresh.yml*. *Recommended: own file (`github-watch.yml`) copying refresh.yml's cron/timezone and App
  token step.*
  - PRO: honours Q7's failure isolation, and keeps github-watch off refresh.yml's `pull_request` trigger. The
    refresh.yml header warns "Do not re-wire a second scheduled writer here" (`refresh.yml:24`), though that warning
    is about snapshot refresh.
  - CON: if Ray meant a job inside refresh.yml, this is one more workflow to pin.
  - Citation: `refresh.yml:20-24`, `:42-44`.
- **Q12: drop rev-1 item 2 (the `github-code` source in `research_fanout.py`).** *Recommended: drop.* github_watch
  owns code search through githubkit, while `research-fanout` keeps `gh` for ad-hoc issue, PR and release lookups.
  - PRO: one code-search implementation; strict-five is untouchable by construction.
  - CON: an ad-hoc `mise run research-fanout --sources github-code` no longer exists. Ad-hoc code search goes through
    a registry entry or `gh search code`.
  - Citation: rev-1 §3.2; `github-api-vs-cli-vs-sdk-2026-09-30.md:236-250`.
- **Q13: the pydantic/msgspec policy for githubkit.** *Recommended: adopt githubkit as transport-only.* That means
  `arequest` + `codec.decode` into msgspec Structs, TID251 bans on `githubkit.webhooks`/`githubkit_schemas`, and an
  autouse test guard on `parsed_data`. Separately, re-scope #683's "both previous dependencies gone from the
  dependency tree" to "gone from first-party code": pydantic is already transitive via anthropic, mcp and openai
  (PREMISES 16).
  - PRO: zero new pydantic exposure, and drift-tolerant decoding (the githubkit #293 failure class).
  - CON: githubkit's typed `rest.*` models go unused, so field access is only as typed as our Structs.
  - Citation: #683, #675, PREMISES 2-4, 16.
- **Q14: githubkit in `currency.toml`.** *Recommended: not in this change.* File a knowledge-base issue so the shared
  `kb_setup.currency` engine can resolve a binaryless python library from `uv.lock`/dist-info. Until then, rely on
  Dependabot, `dependency-currency` and the `githubkit-releases` watch.
  - PRO: avoids a permanent red that trains people to ignore the report.
  - CON: githubkit gets no six-step deep review until the engine lands.
  - Citation: PREMISES 23-25.
- **Q15: bump ty 0.0.76 → 0.0.84.** *Recommended: a separate `chore` PR after `mise run lint-delta -- --tool ty`,
  before this implementation*, so that new diagnostics cannot be confused with github_watch's own.
  - PRO: a clean attribution of any new diagnostics.
  - CON: one more PR first.
  - Citation: PREMISES 20; the `lint-delta` skill.
- **Q16: a ty LSP for Claude Code.** *Recommended: a repo-owned LSP-only plugin*, with no skills and therefore no
  listing cost, in the `ray-manaloto` marketplace. Its `.lsp.json` is `{"ty": {"command": "uv", "args": ["run",
  "--project", "${CLAUDE_PROJECT_DIR}/python", "ty", "server"], "extensionToLanguage": {".py": "python", ".pyi":
  "python"}}}`, so the LSP runs the gate's locked ty. Codex gets no LSP: it has no client (openai/codex#8745 is
  open), so ty stays its CLI gate.
  - PRO: one ty version everywhere, and none of the three existing plugins' drift. astral runs `uvx ty@latest`
    (unpinned). Piebald's bare `ty` is the broken mise shim. `aggregated-research` pins ty 0.0.74 and carries
    skills.
  - CON: a plugin to maintain, the LSP tool changes the tool list (a prompt-cache effect), and it is unverified live.
  - Citation: PREMISES 40-42; R§06-07 and the Addendum.
