# github-watch design research (2026-09-30)

Lane: general-purpose research + spec revision (Claude Opus). Worktree
`dotfiles.worktrees/agy-native-20260930`, branch `feat/native-cli-installers-workflow`.
Written incrementally; sections are appended as each probe lands.

Inputs read this session: `docs/specs/research-watch-2026-09-30.md` (rev 1 draft),
`docs/research/kb/reports/agents/github-api-vs-cli-vs-sdk-2026-09-30.md` (the githubkit recommendation).

## Progress log

- 00: report created; spec rev 1 and the SDK report read.
- 01 (A, offline docs): githubkit latest = **0.16.1** (PyPI JSON `info.version`, uploaded 2026-08-14; bogus pkg → 404
  control). Mirror written to `docs/research/kb/raw/githubkit-docs-0.16.1/` — `site/` (18 pages, firecrawl CLI 1.25.0
  `scrape -f markdown --only-main-content`, all rc=0 after firecrawl's own 12 req/min rate limit forced retries) and
  `source/` (18 upstream `docs/**/*.md` at tag `v0.16.1` via `gh api` raw). Site has no `llms.txt` (404, root 200).
  Site == v0.16.1: 0 `docs/` commits since the tag; control window from 2026-01-01 returns 5. Token-shape scan: 0.
  **Probe defect caught:** the first drift probe used `compare v0.16.1...master` which truncates at 300 files — its
  "0 docs files" was a bound, replaced by the path-scoped commits query.
- 02 (B2, pydantic): **githubkit imports pydantic at module import** — `githubkit/compat.py:4`
  `from pydantic import VERSION`; also `typing.py:15`, `utils.py:6` (clone of tag v0.16.1, commit `d043cb66`). So it
  cannot run without pydantic installed. BUT validation is **lazy and opt-in per call**: `Response.parsed_data`
  (`response.py:96-102`) is the only place a response is validated (`type_validate_json` → pydantic `TypeAdapter`);
  `Response.json()` (`:93-94`) is plain `httpx.Response.json()` and `.content` (`:85-87`) is raw bytes. `_check`
  (`core.py` ~419-446) constructs `Response(response, model)` without parsing. `request`/`arequest` default
  `response_model=UNSET` → `Response[Any]`. Request-body validation is a separate knob, `rest_api_validate_body`
  (docs `configuration.md`, "rest_api_validate_body"), irrelevant to GETs.
- 03 (B2, the real conflict size): **pydantic is ALREADY in this repo's resolved tree transitively and cannot leave it
  via #683 alone.** `uv tree --invert --package pydantic --frozen` (python/, this session): pydantic 2.13.4 ←
  anthropic 1.6.0 (← kb-setup, graphifyy[all]), mcp 2.0.0 (← graphifyy[all]), mcp-types, openai 3.0.0 (← skillopt ←
  kb-setup; graphifyy[all]), pydantic-settings, and dotfiles-setup directly. #683 (OPEN) acceptance says "Both previous
  dependencies are gone from the dependency tree" — that criterion is already unattainable while graphifyy[all] and
  kb-setup stay. githubkit therefore adds **no new package** to the resolved set on the pydantic axis; the conflict is
  about FIRST-PARTY code touching pydantic, which is what the msgspec/codec policy (#675 CLOSED, #669) governs.
  First-party pydantic importers today: only `python/src/dotfiles_setup/config.py`.
- 04 (B3, cache + ETag, LIVE, scratch venv githubkit 0.16.1 / hishel 1.4.0 / httpx 0.28.1, `GITHUB_TOKEN` presence
  only):
  - **A (http_cache=False, manual `If-None-Match`):** real ETag → **304**, body 0 bytes, `x-ratelimit-remaining`
    4636 → 4636 (free). Control: bogus ETag → 200, remaining 4636 → 4635. So manual ETag through
    `arequest(..., headers={"If-None-Match": etag})` works and a 304 is NOT an error (`_check_is_error` =
    `httpx.Response.is_error`, 4xx/5xx only).
  - **B (default http_cache=True, in-memory):** repeat in the same client → caller sees **200** (not 304) with
    `raw_response.extensions` `hishel_from_cache=True, hishel_revalidated=True`; remaining unchanged. githubkit forces
    revalidation by sending `Cache-Control: no-cache` on every request (`core.py` `_get_client_defaults`, comment
    "tell hishel to always revalidate the request"). Default storage is **in-process sqlite `:memory:`**
    (`githubkit/hishel.py:55-126`, `cache/mem_cache.py:68-77`) — nothing persists across runs.
  - **Cross-process:** a 12-line `MemCacheStrategy` subclass returning `AsyncSqliteStorage(database_path=...)`
    persisted it: run2 `from_cache=True revalidated=True`, remaining unchanged; fresh-db control decremented.
    hishel auto-creates the parent dir with a `.gitignore` of `*` (`hishel/_utils.py:110-119`); default path is
    `.cache/hishel` relative to CWD.
  - **SECURITY FINDING: the hishel sqlite file stores the Authorization token in plaintext** — byte-count of the
    live token in the db = 1 (value never printed), `authorization` header name ×2; control term `yanyongyu` present.
    Probe db deleted immediately. ⇒ a persistent hishel cache is a credential file at rest (and would be uploaded if
    ever put in `actions/cache`). Recommendation: **`http_cache=False`; persist ETags in the tracked watch state**
    (ETags are not secrets) and send `If-None-Match` explicitly.
  - **C:** `search/code` returns **no ETag**, `x-ratelimit-resource=code_search`, remaining 9 (limit 10) — confirms
    the SDK report's n=1 finding by a second route (githubkit instead of gh).
- 05 (B4, ty version): ty is pinned in ONE place — `python/uv.lock:2543-2544` `ty 0.0.76` (dev group, unpinned
  spec `"ty"` at `python/pyproject.toml` `[dependency-groups] dev`). It is NOT in `mise.toml`, `shared.toml` or
  `mise-system.toml` (grep of all four; control: `mise.toml:1651` comment `lint-delta -- --tool ty` hits). Latest =
  **0.0.84** (PyPI upload 2026-09-24; GitHub `astral-sh/ty` releases/latest `0.0.84`; `mise latest ty` 0.0.84).
  Running: `uv run --project python ty --version` → `ty 0.0.76 (1940c8a75 2026-08-31)`. The bare `ty` on PATH is a
  mise shim that errors `No version is set for shim: ty` (stale installs 0.0.23/0.0.32/0.0.74) — so any LSP config
  whose `command` is bare `ty` fails on this host.
- 06 (B4, Claude Code LSP): LSP servers are **plugin-only** — `.lsp.json` in a plugin root or `lspServers` inline in
  `plugin.json` (`$CC/plugins-reference.md:199-277`); `command` must be on PATH; placeholders
  `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`, `${CLAUDE_PROJECT_DIR}` resolve in `command/args/env/workspaceFolder`
  (`:696-713`). No settings-level LSP key (grep settings-reference/settings/env-vars for `lsp`: only permission
  and safe-mode mentions). The LSP tool is inactive until such a plugin is enabled (`$CC/tools-reference.md:305-319`);
  cloud sessions never start plugin LSPs (`$CC/discover-plugins.md:54`). Enabling an LSP plugin changes the tool
  list (prompt-cache note, `$CC/prompt-caching.md:135-137`). Official marketplace lists only `pyright-lsp` for Python
  (`$CC/discover-plugins.md:67`).
  - **Two ty LSP plugins already exist in marketplaces this machine has cloned:**
    1. `astral@astral-sh` (Astral's own, `astral-sh/claude-code-plugins`, upstream pushed 2026-02-27) — its
       `plugin.json` inlines `lspServers.ty = {command: "uvx", args: ["ty@latest", "server"]}` plus three skills
       (ruff, ty, uv). **Disabled in `.claude/settings.json`** by `c1a58bb1` (#812, 2026-08-29) for skill-listing cost
       (zero Skill invocations measured) — that commit's reasoning never mentions its LSP server. `ty@latest` is
       UNPINNED (would run 0.0.84 while the gate runs 0.0.76) and needs network on every start.
    2. `ty@claude-code-lsps` (Piebald-AI, added 2026-04-30 #70) — `.lsp.json` `{command: "ty", args: ["server"]}`;
       bare `ty` = the broken mise shim above. Not enabled (not in `enabledPlugins`).
  - `.claude/settings.json:176-177` disable `pyright-lsp@claude-plugins-official` and `pyright@claude-code-lsps`
    (since `fc8af71c`, #34, 2026-04-05).
  - **Recommendation:** a repo-owned LSP-only plugin (no skills ⇒ no listing cost) with
    `command: "uv", args: ["run", "--project", "${CLAUDE_PROJECT_DIR}/python", "ty", "server"]` so the LSP runs the
    SAME uv.lock ty as the lint gate. Not verified live this session (needs a plugin install + session restart).
- 07 (B4, codex LSP): **codex has no LSP client.** Offline codex docs (126 files): 0 hits for
  `lsp|language server|language_server` (control `mcp_servers` hits 3 files). Vendored `schemas/codex-config.json`
  (0.154.0) and the LIVE `https://learn.chatgpt.com/docs/config-schema.json` (HTTP 200 today): 0 LSP keys, control
  `mcp_servers` 2 each. Last 30 `openai/codex` release bodies: 0 LSP mentions (control: MCP in 3). Open requests:
  openai/codex#8745 "LSP integration (auto-detect + auto-install)" (68 comments, updated today), #31504; #25459 and
  #14799 closed as duplicate; PR #9426 closed unmerged. Host codex 0.159.2. ⇒ codex uses ty via the CLI gate
  (`uv run --project python ty check`), which it already runs; an MCP-to-LSP bridge would be lane-2 MCP for our
  own problem (`research-doc-sources.md`), so not recommended.
- 08 (B1, async API): githubkit is **anyio-native** — `core.py:674` `await anyio.sleep(...)` in the async retry loop,
  `throttling.py:8,42,53` `anyio.Semaphore`; `anyio>=3.6.1,<5` is a hard requirement (PyPI requires_dist). Best
  practice from its docs (mirror `source/`):
  - one client per run: `async with GitHub(auth, ...) as gh:` — "strongly recommend using the context manager … Repeatedly
    creating new HTTP clients may lead to memory leaks" (`usage/getting-started/reusing-client.md`, upstream #285);
    re-entering the same instance raises `RuntimeError`.
  - `async_*` generated methods (`github.rest.repos.async_get`) or `await gh.arequest(method, url, ...)` for raw calls
    (`usage/rest-api.md` "call the API directly"); `async for x in gh.rest.paginate(gh.rest.X.async_Y, ...,
    map_func=...)` — **the paginator validates via `parsed_data` unless `map_func` is given**
    (`githubkit/paginator.py:107-109,126-128`), so a no-pydantic caller passes `map_func=lambda r: r.json()[...]`.
  - `LocalThrottler(n)` is a **concurrency** cap, not a rate limit; code search's 10/min must be paced by us.
  - Auth in Actions: `ActionAuthStrategy()` reads `GITHUB_TOKEN` (`authentication.md:241-262`); a plain token string =
    `TokenAuthStrategy`. For the App token (Q9 ruled) pass the minted token string via env.
- 09 (B1, pytest async): **Recommend anyio's built-in pytest plugin, not pytest-asyncio.** anyio docs: "This plugin is
  part of the AnyIO distribution, so nothing extra needs to be installed" (`anyio/docs/testing.rst:4-6` @4.15.1);
  PyPI `pytest-anyio` 0.0.0 says "The pytest anyio plugin is built into anyio. You don't need this package."
  githubkit's own suite uses `@pytest.mark.anyio` + a conftest `anyio_backend` → `"asyncio"` (tests/conftest.py:6-8,
  tests/test_rest/test_call.py:55…), and its unit-test docs use the same marker. anyio is already in `python/uv.lock`
  (4.14.2, transitive) — so zero new packages; declare `anyio>=4.15.1` explicitly in the dev group. Latest: anyio
  **4.15.1** (2026-09-05); pytest-asyncio **1.4.0** (2026-05-26) for comparison; pytest 9.1.1. The repo has NO async
  code or tests today (grep `async def|asyncio` in `tests/` and `python/src`: 0 files).
  - **LIVE proof (scratch venv, githubkit 0.16.1 + anyio 4.15.1 + pytest 9.1.1, no pytest-asyncio):** 2 passed —
    an ETag round trip via `httpx.MockTransport` (200 → 304) and a guard fixture that monkeypatches
    `Response.parsed_data` to raise; its control test proves the guard fires. **Control arm:** `-p no:anyio` → both
    fail "async def functions are not natively supported", rc=1. Raw artifacts: `.agent/kb/raw/github-watch-2026-09-30/`.
  - Coexistence note: anyio's `anyio_mode="auto"` conflicts with pytest-asyncio's auto mode
    (`testing.rst:29-32`); with pytest-asyncio absent, use the explicit marker anyway (githubkit precedent).
- 10 (B5, currency): three layers already cover a FIRST-LEVEL Python dep; the deep one cannot host githubkit as-is.
  - **Dependabot** is the repo's only Python updater (`.github/dependabot.yml:1-6,16-40`: pip ecosystem, `/python`,
    daily cron America/Chicago, one grouped `python-deps` PR, 7-day cooldown). Renovate's `enabledManagers` has no
    pep621/pip manager (`renovate.json`). A githubkit bump therefore arrives as a Dependabot PR.
  - **`mise run dependency-currency`** reports first-level Python pins that are behind (`uv pip list --outdated`
    against the project interpreter; `python/src/dotfiles_setup/dependency_currency.py:1-30`, `mise.toml:1705-1708`).
    githubkit becomes first-level on adoption, so it is covered with no config.
  - **`currency.toml` deep tracking (`mise run tool-currency`) has an engine gap for binaryless libraries.** The
    engine's python-package resolution demands `<python_project_dir>/.venv/bin/<binary>` (`kb_setup/currency/
    sync.py` `_check_python_resolution`, ~L1041-1049; `binary` defaults to the tool name). **LIVE probe** calling the
    engine directly: `githubkit` → `drift: …/python/.venv/bin/githubkit is missing; run \`mise deps\``; control
    `graphifyy`/`graphify` → `ok: locked uv environment runs 0.9.65`. `source_only` is not an escape hatch — it
    requires a `manifest` (`config.py:517-521`). ⇒ adding `[tool.githubkit]` today yields a PERMANENT red.
    Fix belongs in the shared engine (knowledge-base `kb_setup.currency`): read a library's version from
    `uv.lock`/dist-info when it has no binary. Tracked as an open question.
  - **The watch loop can own githubkit's release-note review itself**: a `[[release]]` watch on
    `yanyongyu/githubkit` (ETag-polled, 304 free, measured §04) surfaces each new release body in the digest; the
    skill's judgment step classifies it and registers every ADOPTED feature as a `[[watch]]` entry with
    `origin = "githubkit@<ver>:<feature>"` in a reviewed diff (the loop the SDK report proposed,
    `github-api-vs-cli-vs-sdk-2026-09-30.md:281-292`).
  - **githubkit-schemas is a second moving part**: githubkit 0.16.1 requires `githubkit-schemas>=26.5.7` (unbounded,
    PyPI requires_dist); a fresh resolve today pulled `githubkit-schemas 26.9.29` + `githubkit-schemas-2026-03-10
    26.9.29`. Schema packages release far more often than githubkit; uv.lock pins them, Dependabot bumps them.
- 11 (seed watches, LIVE `gh api -X GET search/code`, per_page=1, total_count, 2026-09-30):
  | total | query |
  |---|---|
  | 444 | `"from githubkit import GitHub" language:Python` (proposed must-hit control for the githubkit ids) |
  | 141 | `githubkit filename:pyproject.toml` |
  | 206 | `arequest githubkit language:Python` |
  | 24 | `"http_cache=False" githubkit` |
  | 11 | `ActionAuthStrategy language:Python` |
  | 7 | `"pytest.mark.anyio" githubkit` |
  | 6 | `RetryRateLimit githubkit language:Python` |
  | 2 | `githubkit msgspec filename:pyproject.toml` → Crimone/Scoparia, wyf7685/Bot7685 (both `pyproject.toml`) |
  Absent control: a fresh `secrets.token_hex`-derived term (not recorded) `language:Python` → total 0. The next two
  searches returned **HTTP 403 "API rate limit exceeded"** — the 10/min code_search bucket is per USER and shared
  with every concurrent lane; this is a rate limit, NOT zero results, and those two lists are unmeasured.
  Counts are unconfirmed hits (no content re-grep), n=1 each.
- 12: betterleaks over the new mirror (`betterleaks dir --redact --no-banner -c .gitleaks.toml
  docs/research/kb/raw/githubkit-docs-0.16.1`) → "no leaks found", rc=0 (scanner's fail arm is the inherited
  measurement in `suites.toml:2136`, not re-run here).
- 13: new packages githubkit would add to `python/uv.lock` (scratch resolve vs the lock): githubkit,
  githubkit-schemas, githubkit-schemas-2026-03-10 (27 MB installed), hishel, anysqlite, msgpack. Already present:
  httpx 0.28.1, anyio 4.14.2, typing-extensions, pydantic 2.13.4.

## Recommendations (synthesis)

1. **Async + tests.** `github_watch.py` runs one `async with GitHub(token, http_cache=False, auto_retry=<chain>) as gh`
   per invocation under `anyio.run`; code-search calls are sequential through our own ≥6 s pacer (githubkit's
   `LocalThrottler` caps concurrency, not rate); release polls may fan out in an `anyio` task group behind a
   `CapacityLimiter`. Tests use **anyio's built-in pytest plugin** (`@pytest.mark.anyio` + `anyio_backend` →
   `"asyncio"` in `tests/conftest.py`) and `httpx.MockTransport` via `GitHub(async_transport=...)` — the pattern
   githubkit's own docs and suite use. Add `anyio>=4.15.1` to the dev group. Do not add pytest-asyncio.
2. **pydantic vs msgspec — adopt githubkit as a transport only; never let first-party code touch its pydantic models.**
   - Call `gh.arequest(...)` (or `async_*` methods) and decode `resp.content` with `dotfiles_setup.codec.decode(...,
     <msgspec.Struct>)`. Never read `Response.parsed_data`; always pass `map_func` to `paginate`; never call
     `githubkit.webhooks.parse*`. `rest_api_validate_body=False` (GETs only anyway).
   - Machine teeth: (a) a test fixture that monkeypatches `Response.parsed_data` to raise, applied to every
     github_watch test (armed live above); (b) ruff TID251 `banned-api` entries for `githubkit.webhooks` and the
     `githubkit_schemas` model modules, with the control that `githubkit.GitHub` still imports.
   - pydantic is NOT removed from the tree by avoiding githubkit: anthropic, mcp, mcp-types and openai (via
     graphifyy[all] and kb-setup) already require it. #683's "gone from the dependency tree" criterion is unattainable
     today regardless; it should be re-scoped to "gone from first-party code". githubkit adds zero new pydantic
     exposure to the resolved set, and the msgspec partial Struct is also the fix for githubkit's own recurring
     model-drift failure (#293, `ValidationError` on a missing search field).
3. **Cache + ETag.** `http_cache=False`. Persist each release watch's `etag` in its tracked jsonl state and send
   `If-None-Match`; a 304 is free and not an error (measured). Do NOT persist hishel's sqlite cache: it stores the
   Authorization token in plaintext (measured). If a disk cache is ever wanted, it is `.agent/cache/githubkit/` via a
   `BaseCacheStrategy` subclass, and it is a credential file — keep it out of `actions/cache`.
   Auto-retry: `RetryChainDecision(RetryRateLimit(max_retry=N), RetryServerError())` — default max_retry=1 honours
   `retry-after` / `x-ratelimit-reset` once; a 403 that exhausts retries raises `PrimaryRateLimitExceeded` /
   `SecondaryRateLimitExceeded`, which github_watch maps to status `error: rate limited`, never "zero hits".
4. **ty.** Bump the uv.lock ty 0.0.76 → 0.0.84 (separate chore; `mise run lint-delta` first). For Claude Code, a
   repo-owned LSP-only plugin whose server is `uv run --project ${CLAUDE_PROJECT_DIR}/python ty server` (same ty as
   the gate); neither existing ty plugin is safe as-is (astral: unpinned `uvx ty@latest`; Piebald: bare `ty` = broken
   mise shim). For codex: no LSP client exists (0.159.2; #8745 open) — ty stays a CLI gate there.
5. **Currency.** githubkit rides Dependabot (bump PRs) and `dependency-currency` (first-level behind) with no config.
   Deep tracking in `currency.toml` needs a shared-engine change first (binaryless python library → permanent drift
   today, measured). Meanwhile the watch registry tracks `yanyongyu/githubkit` releases itself and registers adopted
   features as `origin = "githubkit@<ver>:<feature>"` watches.

## Gaps

- Whether an App **installation** token can call `search/code` across public repos was not measured (docs body is
  silent on token types; spec §5 live arm).
- The ty LSP plugin shape was not run live (needs plugin install + restart).
- Two seed searches were rate-limited (403) and are unmeasured; all seed counts are unconfirmed and n=1.
- githubkit's GraphQL path (discussions) was not probed.

## GitHub repos touched

- [yanyongyu/githubkit](https://github.com/yanyongyu/githubkit) — docs mirror at v0.16.1; source (core, response, retry, cache, hishel, paginator, compat); tests/conftest; releases; docs commit history
- [agronholm/anyio](https://github.com/agronholm/anyio) — `docs/testing.rst`, `docs/versionhistory.rst` at 4.15.1
- [pytest-dev/pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio) — `docs/concepts.rst` at v1.4.0 (modes)
- [astral-sh/ty](https://github.com/astral-sh/ty) — releases (latest 0.0.84)
- [astral-sh/claude-code-plugins](https://github.com/astral-sh/claude-code-plugins) — `astral` plugin.json `lspServers.ty`
- [Piebald-AI/claude-code-lsps](https://github.com/Piebald-AI/claude-code-lsps) — `ty/.lsp.json`, `ty/plugin.json`, commit history
- [openai/codex](https://github.com/openai/codex) — LSP issues #8745 #31504 #25459 #14799, PR #9426; last 30 release bodies
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issues #683, #675; code-search control
- GitHub code search (public index) — the eight seed queries in §11

## Addendum (cross-check against the coordinator's findings.md)

- A **third** ty LSP candidate exists: `aggregated-research@ray-manaloto` ships `.lsp.json`
  `{ty: {command: "${CLAUDE_PLUGIN_ROOT}/bin/ty", args: ["server"]}}`; `bin/ty` is a shell wrapper →
  `bin/mise-env exec -- ty`, and the plugin's own `mise.toml:4` pins **ty 0.0.74** — a third ty version (gate 0.0.76,
  latest 0.0.84). It also carries skills + hooks (listing cost) and is not enabled in this repo's settings. It is the
  precedent for `${CLAUDE_PLUGIN_ROOT}`-relative LSP commands, but its ty pin diverges from the gate. The recommendation
  stands: an LSP-only plugin running `uv run --project ${CLAUDE_PROJECT_DIR}/python ty server` (no wrapper script,
  no second pin). The coordinator has a separate LSP sweep running
  (`claude-codex-ty-lsp-2026-09-30.md`); this report's §05-07 is an independent route to the same facts.

## Spec revision

- 14: `docs/specs/research-watch-2026-09-30.md` rewritten as **DRAFT rev 2 — `github-watch`** (path kept). Seven-part
  shape kept; 42 PREMISES rows + A1/A2, all read/measured this session except row 35 (rev-1 seed strings, marked
  inherited) and parts of row 36 (marked inherited). Q5 resolved (installed graphify 0.9.65 `cli.py:1472` has
  `--outcome`). New/re-opened questions: Q7b, Q12-Q16. No gate was run: docs/specs is outside hk's scope and nothing
  was implemented.
- 15: rev 1 was never committed (untracked); its 14-id seed table and controls were carried into rev 2 byte-for-byte (diff against the rev-1 read = identical), so the overwrite lost no seed data.
