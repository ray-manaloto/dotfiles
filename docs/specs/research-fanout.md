# Spec (rev 5, 2026-09-26: premise rounds + review rounds 1-2 applied; round 3 authorized by Ray) — `research-fanout`: a no-LLM, multi-source research fetcher for Claude AND codex

Status: RATIFIED by Ray 2026-09-26 (AskUserQuestion, session `dotfiles-20260926.000`): the "hybrid" architecture —
a Python fetch layer + mise task usable by both harnesses, a saved Claude workflow over it with per-node model/effort,
and a mirrored skill. Ray was shown that knowledge-base#509 `aggregated-research` / `kb_setup.research` overlaps and
chose a NEW dotfiles module anyway (re-ruled the same day). This spec covers ONLY the fetch layer + mise task; the
workflow and skill are authored separately by the architect.

Evidence: `docs/research/kb/reports/agents/mise-warn-multisource-2026-09-26.md` (per-source scorecard: invocations,
latency, codex reachability) and `docs/research/kb/reports/agents/research-skill-inventory-2026-09-26.md`.

## 1. Objective

One command fans a research question out to many sources concurrently, with **no LLM in the loop**, and writes one
raw JSON file per source plus a manifest. It replaces an agent spending Opus tokens on fetching. Every empty result
carries a **control arm** (a canary query against the same source) so "0 results" is distinguishable from "source
broken" (`.claude/rules/probes-need-a-control-arm.md`). Both harnesses call it: Claude through the workflow,
codex directly.

## 2. Files

Create:
- `python/src/dotfiles_setup/research_fanout.py` — the library + `main(argv, repo_root) -> int`.
- `tests/test_research_fanout.py`.

Modify:
- `mise.toml` — add `[tasks.research-fanout]`, a thin caller invoking the module DIRECTLY (precedent
  `[tasks.session-review-gate]`, `mise.toml:1619-1621`): `run = 'uv run --project python python -m dotfiles_setup.research_fanout'`,
  with a one-line description and a `# Thin caller; python/src/dotfiles_setup/research_fanout.py.` comment.
  **Do NOT register a `dotfiles-setup` subcommand:** `main.py` parses with `parse_args` (`main.py:3112`), and a
  pass-through whose first token is a flag (`--list-sources`) is rejected — `plan_attest.py:95-110` documents why that
  case needed a special separator. `python -m` bypasses the parent parser entirely (rev 2, premise-verifier finding).
  The module ends with `if __name__ == "__main__": raise SystemExit(main(sys.argv[1:], _repo_root()))` where
  `_repo_root()` reads `MISE_PROJECT_ROOT` and falls back to `Path.cwd()` (precedent `session_gate.py:272`; the task's
  default `dir` is `{{ config_root }}`, `schemas/mise.json:3415`).

Touch nothing else. No new `.sh` file (`bash_logic_budget`). No new Python dependency: HTTP via `urllib.request`
(stdlib); subprocesses via `subprocess.run` with an explicit `timeout`.

## 3. Interfaces

CLI (`mise run research-fanout -- …`):

```
research-fanout QUERY [--repo OWNER/REPO] [--sources S1,S2,...] [--out DIR] [--limit N] [--timeout SECS] [--list-sources]
```

- `QUERY` (required unless `--list-sources`): the research question / search terms.
- `--repo`: scopes the GitHub sources and the firecrawl developer index. Without it, GitHub sources return
  `skipped` with reason `needs --repo`.
- `--sources`: comma list; default = every source whose prerequisites are present. Unknown name → exit 2.
- `--out`: default `<repo_root>/.agent/kb/raw/research-fanout/<slug>/`, slug = lowercase alnum-and-hyphen of QUERY,
  ≤60 chars.
- `--limit`: max items per source (default 10). `--timeout`: per-source wall clock; when given it applies to EVERY
  source; when omitted, 60 s per source and 180 s for last30days.
- `--list-sources`: print one line per source: name, transport, prerequisite, present/absent (presence only — never a
  value). Exit 0.

Sources (name → transport; all reachable from a plain shell):

| name | transport | prerequisite |
|---|---|---|
| `github-issues` | `gh api '/search/issues?q=repo:<repo>+<query>&per_page=<limit>'` (issues AND PRs; NOT `gh search issues`) | `gh` on PATH, `--repo` |
| `github-discussions` | `gh api graphql` — `search(type: DISCUSSION, query: "repo:<repo> <query>")` | `gh`, `--repo` |
| `github-releases` | `gh api 'repos/<repo>/releases?per_page=100'`; items = the releases whose tag/name/body contain EVERY query term as a whole word (§8.9 terms; ALL-terms per §9.9), at most `--limit` | `gh`, `--repo` |
| `exa` | `POST https://api.exa.ai/search`, header `x-api-key` from `EXA_API_KEY`, JSON `{"query", "numResults"}` | `EXA_API_KEY` set |
| `context7` | `ctx7 library <name>` where name = the `--repo` NAME part when given, else the query (text: a numbered list of library IDs), then `ctx7 docs <first-id> <query>` (text: `### ` sections, each carrying a `Source:` URL). Items = one per `### ` section of the docs output (title = heading, url = its `Source:` URL, snippet = the section text); only the FIRST library ID is queried | `ctx7` on PATH |
| `firecrawl-developer` | `GET https://api.firecrawl.dev/v2/search/developer?query=…&k=…` (+`repos=<repo>` when given; the count param is `k` — `limit` is a 400, measured 2026-09-26); send `Authorization: Bearer $FIRECRAWL_API_KEY` only if set (the endpoint is keyless) | none |
| `firecrawl-search` | `firecrawl search <query> --sources web --json --limit <limit>` (the CLI default `web,alexandria` returns the Alexandria tool catalog; results are under `data.web`) | `firecrawl` on PATH |
| `last30days` | **OPT-IN ONLY** (never in the default set; runs only when named in `--sources`). `python3 <script> "<query>" --emit=json` (+`--github-repo=<repo>` when given); script = env `LAST30DAYS_SCRIPT`, else the highest-version match (compare versions NUMERICALLY, not as strings) of `~/.claude/plugins/cache/last30days-skill/last30days/*/skills/last30days/scripts/last30days.py`, else the same under `~/.codex/plugins/cache/`. Parse its JSON; unparsable → `error` | script found |

Result shapes (frozen dataclasses, serialised with `dataclasses.asdict`):

```python
class Status(Enum): OK, EMPTY_VERIFIED, EMPTY_UNVERIFIED, ERROR, SKIPPED   # values: lowercase names

@dataclass(frozen=True)
class Item: title: str; url: str; snippet: str; date: str | None      # snippet ≤ 500 chars

@dataclass(frozen=True)
class Control: query: str; count: int | None                            # None = the canary itself errored

@dataclass(frozen=True)
class SourceResult:
    source: str; status: Status; items: tuple[Item, ...]; elapsed_s: float
    reason: str | None          # why ERROR / SKIPPED / EMPTY_UNVERIFIED — never contains a credential value
    control: Control | None     # set iff the primary query returned 0 items
    raw_file: str | None        # path of <source>.raw (the untrimmed response), when one exists
```

- Control arm: when a source returns 0 items, run its canary once (github-issues/-discussions: the repo's NAME part, e.g.
  `mise` for `jdx/mise`, on the same repo; github-releases: none needed — an empty release list for an existing repo is
  `empty_verified` only if `gh api repos/<repo>` returns 200; exa/firecrawl-*/context7: `python`; last30days: none → `EMPTY_UNVERIFIED` with reason `no canary`).
  canary count > 0 → `EMPTY_VERIFIED`; canary 0 or error → `EMPTY_UNVERIFIED`. The firecrawl-developer canary keeps the
  `repos=` filter when `--repo` was given (and then uses the repo's name as its query), so the canary tests the same
  scoped index the primary query hit.
- Output: `<out>/<source>.json` (the SourceResult), `<out>/<source>.raw` (the untrimmed response bytes as received —
  JSON for the HTTP/`gh` sources, text for `ctx7`; no extension claim about the format),
  `<out>/manifest.json` = `{"query", "repo", "sources": [SourceResult...], "out_dir"}`.
- stdout: the manifest path, then one line per source: `<source>  <status>  <n> items  <elapsed>s  [<reason>]`.
- Exit: 0 if ≥1 source is `ok` or `empty_verified`; 1 if every requested source is error/skipped/empty_unverified;
  2 for usage errors.
- Library entry: `def fan_out(request: FanoutRequest, *, runner: Runner = default_runner, http: Http = default_http) -> list[SourceResult]`
  where `FanoutRequest` is a frozen dataclass `(query: str, repo: str | None, sources: tuple[str, ...], limit: int,
  timeout: float | None)` — bundled because ruff `select=["ALL"]` keeps PLR0913's default max of 5 args
  (`pyproject.toml:63-86`) and inline suppressions are banned (precedent: `WaitRequest`, `bounded_wait.py:27`, used at `main.py:2844`).
  `runner`/`http` are injectable seams (Protocols) so tests never touch the network.
  **The `Http` seam takes an `Endpoint` enum, never a URL** — `Endpoint.EXA_SEARCH`, `Endpoint.FIRECRAWL_DEVELOPER` —
  plus query params / JSON body, headers and timeout, and returns `(status: int, body: bytes)`. `default_http` maps each
  member to its own `urllib.request.Request(...)` call site whose URL is a literal or f-string beginning `https://`
  (`f"https://api.firecrawl.dev/v2/search/developer?{urlencode(params)}"`), so ruff S310 sees a literal at every
  `urlopen` site (rev 3: a URL-taking seam would put a variable at the call site and trip §4's STOP).
  `def main(argv: list[str], repo_root: Path, *, runner: Runner = default_runner, http: Http = default_http) -> int`
  — the same seams, so the exit-code tests run through `main` with fakes (never by patching this module,
  `tests/AGENTS.md:94`). Sources run concurrently (`concurrent.futures.ThreadPoolExecutor`).

## 4. Constraints and invariants

- **URLs are literals.** Every `urllib.request` URL is a literal or f-string beginning with `https://` (ruff S310
  audits dynamic URLs; there is no repo precedent for `urllib` — `gcc_sha.py:129` shells out to `curl`). If ruff still
  flags S310, STOP and report (dissent) — no suppression, no per-file ignore.
- **Credentials never reach output.** No credential value in stdout, stderr, any written file, or `reason`. Pass keys
  only in HTTP headers / the child env. Subprocess envs: `child_env.clean_env(keep=frozenset({...}))`
  (`child_env.py:77`) keeping ONLY the names that child needs (`gh`: `GITHUB_TOKEN`, `GH_TOKEN`; `firecrawl`:
  `FIRECRAWL_API_KEY`; `ctx7`: `CONTEXT7_API_KEY`; last30days: `GITHUB_TOKEN` (the only name it reads, plugin
  `lib/github.py:53`; without it it falls back to `gh auth token`, `:59`, the keychain route
  `secrets-out-of-the-shell-env.md` warns about), `SCRAPECREATORS_API_KEY`,
  `EXA_API_KEY`, `PARALLEL_API_KEY`, `BRAVE_API_KEY` — and deliberately NOT the LLM-provider keys (`XAI_API_KEY`,
  `PERPLEXITY_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`), which switch on its
  internal planner/reranker (`providers.py:271-279`, `planner.py:375-377` in the plugin). Its child env ALSO sets
  `LAST30DAYS_CONFIG_DIR=""` (disables `~/.config/last30days/.env`, plugin `lib/env.py:31-35`) and
  `LAST30DAYS_SKIP_KEYCHAIN=1` (disables its macOS Keychain lookup of 23 keys incl. `XAI_API_KEY`/`OPENAI_API_KEY`,
  `env.py:60`, `:346-419`). KNOWN LIMIT, state it in the module docstring: its `pass` password-store source
  (`env.py:422-458`) has no documented off-switch, so an LLM key stored there can still enable its planner — that is
  why last30days is opt-in and why §1's "no LLM" holds only for the default source set.
  A test must assert a sentinel secret value never appears in any written file or captured output.
- A 0-result is never reported as `ok`. A timeout, non-2xx, non-zero rc, or unparsable JSON is `ERROR` with a reason,
  never `EMPTY_*` (`probes-need-a-control-arm.md` rule 4).
- Every subprocess and HTTP call has an explicit timeout. No shelling out through `sh -c`; argv lists only.
- The module must not import from `kb_setup` (Ray's ruling: independent module).
- Follow repo Python standards: `ruff` + `ty` clean, Google docstrings, no inline suppressions (`no_lint_skip`),
  module docstring explaining the WHY (see `session_state.py:1-13` for tone).
- Do not run `mise run research-fanout` against live sources from tests. Live runs are the architect's verification.
- Do not touch `.claude/`, `.agents/`, `.github/`, `docs/`, or any file not listed in §2.

## 5. Verification

```bash
uv run --project python pytest tests/test_research_fanout.py -q     # rc=0
uv run --project python ruff check python/src/dotfiles_setup/research_fanout.py tests/test_research_fanout.py
uv run --project python ty check python/src/dotfiles_setup/research_fanout.py
mise run research-fanout -- --list-sources                           # rc=0, one line per source
mise run lint                                                        # rc=0
```

Tests (fake `runner`/`http`) must include, each with its fail arm noted in a comment:
- empty primary + non-empty canary → `empty_verified`; empty primary + empty canary → `empty_unverified`;
- non-2xx / timeout / bad JSON / rc≠0 → `error`, never `empty_*`;
- missing prerequisite → `skipped` with reason; `github-*` without `--repo` → `skipped`;
- the secret-sentinel test (set `EXA_API_KEY=SENTINEL-…` in the fake env; assert it appears in the outgoing header
  and NOWHERE in written files / stdout / reasons);
- exit-code table (0 / 1 / 2);
- unknown `--sources` name → exit 2;
- concurrency: two sources whose fakes each sleep T finish in < 2T.

- `main([...], repo_root, runner=fake, http=fake)` with `--list-sources` returns 0 and names every source;
- last30days is absent from the default source set and present only when named.

The architect then runs the live integration arm (`mise run research-fanout -- "tracked configs" --repo jdx/mise`) and
its control (`--sources exa` with `EXA_API_KEY` unset → `skipped`), per `.claude/rules/real-integration-evidence.md`.

## 6. Commit

`caller`. Leave changes uncommitted; report changed paths and each §5 command's real exit code.

## 7. PREMISES

| # | Kind | Claim | Source (read this session) |
|---|---|---|---|
| 1 | P | `python -m` task precedent (bypasses `main.py`'s `parse_args`, `:3112`); repo root via `MISE_PROJECT_ROOT` | `mise.toml:1619-1621`, `session_gate.py:272` |
| 2 | P | Module `main(args, repo_root) -> int` precedent | `python/src/dotfiles_setup/session_state.py:290` |
| 3 | P | Thin mise task precedent | `mise.toml:996-999` |
| 4 | I | `clean_env(base=None, *, keep: frozenset[str]) -> dict[str, str]` | `python/src/dotfiles_setup/child_env.py:77-92` |
| 5 | L | Python floor `>=3.14` | `python/pyproject.toml:5` |
| 6 | L | CLIs present: `firecrawl` 1.24.6, `ctx7` 0.5.12, `gh` 2.101.0 (user-global only) | `mise.toml:139`, `mise.toml:66`, `~/.config/mise/config.toml:131` |
| 7 | L | last30days script paths (3.21.1/3.24.0/3.25.0 Claude cache; 3.25.0 codex cache) | `ls` this session |
| 8 | E | exa `POST /search` with `x-api-key` → 200; no key → 402 | inventory report §1 (live probe, control armed) |
| 9 | E | firecrawl `GET /v2/search/developer` keyless → 200; bogus path → 404 | inventory report §1 |
| 10 | E | `gh api /search/issues` returns issues+PRs; `gh search issues --repo` issues only | inventory report §4 |
| 11 | L | last30days `--emit` choices include `json`; `--plan` skips its internal LLM planner | plugin `last30days.py:658`, `:805` |
| 12 | A | GraphQL `search(type: DISCUSSION)` accepts `repo:` qualifiers — the multisource lane used it (control 0 vs 63); re-probe if it fails | multisource report scorecard |
| 13 | L | `ctx7 library` prints a numbered ID list; `ctx7 docs` prints `### ` sections each with a `Source:` URL | `.agent/kb/raw/mise-warn-src-ctx7.md:1-105` (premise-verifier) |

## 8. Review round 1 — corrections (rev 4, 2026-09-26)

Sources: codex review lens `docs/research/kb/reports/agents/codex-review-50ba9eec-2026-09-26.md` (C4, C5) and Opus cold
review `docs/research/kb/reports/agents/cold-review-50ba9eec-2026-09-26.md` (F1–F14). Every item is a confirmed finding
against commit `50ba9eec`; the caller already fixed the firecrawl `k`/`--sources web` defects (the §3 table is updated
below) and the workflow findings. Each fix ships WITH a test whose fail arm is stated in a comment. Dissent on any item
you find false against the code.

Same ALLOWLIST as before: `python/src/dotfiles_setup/research_fanout.py`, `tests/test_research_fanout.py`
(`mise.toml` needs no change). `COMMIT: caller`.

1. **Transport failures never abort the run (C4, F1, F12).** At the transport boundary (primary AND canary calls)
   catch `http.client.HTTPException` (incl. `IncompleteRead`), `ValueError`, `OSError`, `TimeoutError` →
   per-source `ERROR`. A socket timeout reports `timed out`, not `request failed`. One broken source must still leave
   every other source's result AND the manifest on disk. GraphQL: "response contained errors" only when an `errors`
   key exists; a non-object reply says `unexpected response shape`.
2. **No credential value in any exception text (F2).** Header values are validated before use; an invalid value
   (CR/LF, non-latin-1) yields `ERROR` reason `invalid credential header for <NAME>` — the NAME, never the value.
   Test: a CRLF sentinel in `EXA_API_KEY` appears in NO output stream, file, or reason.
3. **Deadline covers the whole response (C5).** Read the body in chunks, calling `deadline.remaining()` between
   chunks, with a hard cap of 8 MiB (`ERROR` `response too large`). A slow trickle past the deadline → `timed out`.
4. **Process-group kill on timeout (F10).** `default_runner` spawns with `start_new_session=True` and on timeout
   SIGTERMs then SIGKILLs the process GROUP — precedent `bounded_wait.py:44-60`.
5. **Diagnosable subprocess errors (F11).** A non-zero exit's reason is `exited N: <last 300 chars of stderr>` with
   every credential value present in the child env replaced by `[REDACTED]` before truncation.
6. **Web URLs for GitHub items (F3).** Prefer `html_url` over `url` in `_record_item`. Fixtures use the REAL REST
   search item shape (both `url` = api link and `html_url` = web link present).
7. **context7 resolves the right library (F4).** `ctx7 library <name>` uses the repo's NAME part when `--repo` is
   given (`mise` for `jdx/mise`), else the query; `ctx7 docs <id> <query>` still uses the query.
8. **No stale files in a reused out dir (F5).** Before writing, delete from the out dir exactly these names if
   present: `manifest.json` and `<source>.json` / `<source>.raw` for EVERY known source (not only the requested
   ones). Nothing else is deleted.
9. **Releases filtered by the query (F6).** Fetch up to 100 recent releases; keep those whose tag, name or body
   contains a query TERM as a whole word, case-insensitive, where terms are the query's words of ≥3 characters minus
   the stopwords `the and for with from this that are was not you`. Emit at most `--limit` matches. None →
   the repo-exists canary decides `empty_verified` / `empty_unverified` (as before).
10. **Credential scrubbing is tested for EVERY child (F7).** For `gh`, `firecrawl`, `ctx7`, `last30days`: assert a
    non-kept credential sentinel (e.g. `AWS_SECRET_ACCESS_KEY`) is absent from the env the runner received, and each
    kept name is present.
11. **Hermetic tests (F8, F9).** The last30days default-set test sets `HOME` to `tmp_path` and `LAST30DAYS_SCRIPT` to
    a fake so it fails on a clean runner if the opt-in rule breaks. Add a test for each path F9 names: exit 1 when all
    results are `empty_unverified`; GitHub query construction (`repo:<r>+<q>`); the `gh` presence check; the shared
    deadline; the releases repo-exists check; `per_page`; slug truncation to 60; GraphQL `errors`; the mention flag.

Out of scope (ticket, not this change): `LAST30DAYS_TRUST_PROJECT_CONFIG` passes the scrub — drop it from last30days'
child env in THIS change only if it is a one-line removal; otherwise leave it and say so.

§5 verification is unchanged; run all of it and report real exit codes.

## 9. Review round 2 — corrections (rev 5, 2026-09-26; a THIRD round, authorized by Ray via AskUserQuestion)

Sources: `docs/research/kb/reports/agents/cold-review-0a908d9e-round2-2026-09-26.md` (N1–N6, C2/F4/F6 PARTIAL) and
`docs/research/kb/reports/agents/codex-review-0a908d9e-round2-2026-09-26.md` (unbounded drain, Ctrl-C). Scope is
LIMITED to `default_runner`, `_read_http_body`, the context7 canary, the releases filter, the stderr tail, and the
tests below — do not refactor anything else. Same ALLOWLIST (`research_fanout.py`, `tests/test_research_fanout.py`),
`COMMIT: caller`. Every item ships with a test whose fail arm is stated in a comment; where the defect only shows with
a REAL process or socket (items 1, 4), the test MUST use a real one (a local `socketserver` / a real child process),
because the round-2 review showed the fake `Popen`/response cannot produce these cases.

1. **Bounded cleanup after the group kill (N1, codex P2-1).** After SIGKILL of the group, drain with a bounded wait
   (≤ 2 s); if a descendant outside the group still holds the pipes, close them and return. The source reports
   `timed out`. Budget: the runner returns within `timeout + 3 s` even when a detached descendant keeps stdout open.
2. **`killpg` failures are tolerated (N2).** Suppress `ProcessLookupError` and `PermissionError` around each
   `killpg`; the child is always reaped; the reason stays `timed out`.
3. **Ctrl-C reaches the children (codex P2-2).** Track live child processes; on `KeyboardInterrupt` in the fan-out,
   kill every live child GROUP (same TERM→KILL sequence, bounded) before the executor shuts down, then exit 130
   from `main`. Test the cancellation path by raising `KeyboardInterrupt` while a real child is running.
4. **The deadline bounds the whole body read (C2).** Total wall clock for one HTTP source ≤ `timeout + 1 s` even for a
   body trickled one byte at a time. Prefer public APIs; if the only route needs a private attribute, dissent rather
   than use it.
5. **Short bodies are errors (N3).** When `Content-Length` is present and fewer bytes arrive → `ERROR`
   `incomplete response`, never `invalid JSON`.
6. **The context7 canary tests context7, not the repo's library (N4).** The canary runs `ctx7 library python` then
   `ctx7 docs <id> python`, independent of `--repo`, and records exactly the query it ran.
7. **Missing tests (N5).** Add a failing-arm test for: firecrawl credential-header validation; the ≥3-letter term
   rule; both context7 error sites; the firecrawl branch of the body reader.
8. **One line per source on stdout (N6).** Collapse newlines in the stderr tail (`\n` → ` | `) before it enters a
   reason.
9. **Releases need ALL terms (F6; Ray ruling 2026-09-26: "All terms must match").** A release is kept only when every
   term appears as a whole word. `"is python fixed"` against a repo whose releases never say "python" → empty.
10. F4 without `--repo` stays as specified (query → `ctx7 library`); no change.

§5 verification unchanged; report real exit codes and per-item done / dissent.
