# Cold review — `50ba9eec` (research-fanout)

- **Subject:** `50ba9eec8c47b24e6da740403880eb8d35038c53` (branch `feat/research-fanout`), parent `12a34e88`.
- **Focus:** `python/src/dotfiles_setup/research_fanout.py`, `tests/test_research_fanout.py` (codex-authored).
- **Reviewer:** cold-reviewer (Opus), diff-only, round 1 (OPEN HUNTING — no enumerated domain; cannot end the loop by outcome).
- **Memory:** consulted `.claude/agent-memory-local/cold-reviewer/` (mutation harness, PATH probe blindness, subprocess review, stream-split/oracle review).
- **Status:** COMPLETE. 14 findings: 0 HIGH, 6 MEDIUM (F1-F5, F7), 8 LOW (F6, F8-F14). Every MEDIUM carries a live or mutation arm.
- **Verdict:** FIX BEFORE RELYING ON IT. F1+F2 share one root: the `except` at `:883-892` is narrower than what `urllib`/`http.client` raise, and F2 makes it a credential leak. F3 is a one-line precedence swap plus a fixture that includes `url`. F5 is a stale-directory cleanup. F7 is three missing env assertions. F4 is a spec defect: pass a library name (the repo's name part when `--repo` is set), or skip context7 without one.
- **Stop condition:** this was an OPEN-HUNTING round (no enumerated domain), so it cannot end the loop by any outcome. A bounded round 2 would verify the fixes for F1-F14 — that list is its enumeration — plus the Q-FRESH table's five pairs.
- **Tree state:** `HEAD == 50ba9eec` and the working tree was clean at start (`git diff --stat 50ba9eec HEAD` was empty). Every probe ran against a `git archive 50ba9eec` copy in the scratchpad, and this reviewer edited nothing tracked. ⚠️ By the end, ANOTHER writer had modified `.claude/workflows/research-sweep.js` in the working tree (+37/-10, reader identity and source-dive agentType; the triage prompt lines F3/F5 cite were untouched). Every JS citation here is to the `50ba9eec` blob.

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| F1 | MEDIUM | `http.client.HTTPException` subclasses (`IncompleteRead`, `BadStatusLine`, …) and any `ValueError` escape `_source_result`, re-raise through `future.result()`, and abort the WHOLE fan-out: no manifest, no per-source files, every other source's completed result discarded, rc=1 (indistinguishable from "all sources failed"). | `python/src/dotfiles_setup/research_fanout.py:883-892` (only `TimeoutError`/`TimeoutExpired`/`OSError` caught), `:924` (`future.result()` re-raises) | E1 |
| F2 | MEDIUM | Same escape path prints a credential VALUE to stderr: an `EXA_API_KEY`/`FIRECRAWL_API_KEY` containing CR/LF makes `http.client.putheader` raise `ValueError('Invalid header value %r')` with the key's repr, uncaught, as a traceback — violating the spec's "No credential value in stdout, stderr" (§4). No test covers a non-HTTP-status failure from the real `default_http`. | `research_fanout.py:524-527`, `:547-549` (header built from raw env), `:236-248` (`default_http`, no header validation) | E2 |
| F3 | MEDIUM | `github-issues` items carry the REST **API** URL (`https://api.github.com/repos/o/r/issues/N`), not the web URL: `_record_item` prefers `url` over `html_url`, and GitHub search items carry both. The test fixture omits `url`, so it passes while live is wrong. Consumer impact: the workflow's triage "dedup by URL" cannot merge a github-issues hit with the same issue from `firecrawl-developer` (which returns `https://github.com/...`), and the report cites API URLs. | `research_fanout.py:279`; fixture `tests/test_research_fanout.py:252-255`; consumer `.claude/workflows/research-sweep.js:128` | E3 |
| F4 | MEDIUM | `context7` resolves the library from the WHOLE research query and ignores `--repo`: `ctx7 library <name>` takes a library NAME, so `"tracked configs" --repo jdx/mise` queries `/rust-cli/config-rs` (a Rust crate) and reports `ok` with irrelevant items. The commit's "7/7 sources ok" live arm counts this as a pass; status `ok` never measures relevance. Spec-faithful (spec row `context7`), so the defect is in the spec too. | `research_fanout.py:635` (`["ctx7","library", query]`), `:639` (first ID taken) | E4 |
| F5 | MEDIUM | Output dir is reused without clearing: a later run whose query slugs to the same dir (same question next session, or two variants differing only in case/punctuation, or sharing a 60-char prefix) leaves the earlier run's `<source>.json`/`.raw` beside the new manifest, and overwrites the earlier manifest. Both consumers read files BESIDE the manifest, not the manifest's own list — so stale results from another query/run are ingested as current evidence. | `research_fanout.py:1014-1043` (`_persist`: `mkdir(exist_ok=True)`, no cleanup), `:995-997` (`_slug`); consumers `.claude/workflows/research-sweep.js:127`, `.claude/skills/research-sweep/SKILL.md:45` | E5 |
| F6 | LOW | `github-releases` returns the latest `limit` releases UNFILTERED (status `ok` whenever the repo has any release), and its only relevance signal — "release body mentions a query term" — is an any-substring test over `[a-z0-9]+` tokens, so a query containing a common word is `yes` for every release. Measured on jdx/mise's last 10: `"is python fixed"` 10/10, `"qzxvkw to"` 10/10; control `"qzxvkw"` 0/10. | `research_fanout.py:449`, `:459`, `:465` | E6 |
| F7 | MEDIUM | The spec's central security invariant — each child env is `clean_env` keeping ONLY the names that child needs — is tested for `last30days` alone. Replacing the `gh`, `firecrawl` and `ctx7` child envs with the full `os.environ` leaves all 27 tests green, so a regression that hands every shell credential to three external CLIs is invisible. | `research_fanout.py:362-363`, `:585`, `:634`; only env assertion `tests/test_research_fanout.py:419-422` | E7 (M4, M5, M6 green; M13 red) |
| F8 | LOW | `test_default_sources_exclude_last30days` only has a fail arm on a host whose REAL `$HOME` has the last30days plugin cached: it never isolates `HOME`, and on this host the mutation goes red only because `_last30days_script()` finds `~/.claude/plugins/cache/…/3.25.0` and the fake runner's `AssertionError` escapes (F1's path). With `HOME` pointed at an empty dir (any CI runner or devcontainer), putting last30days into the default set passes 27/27. | `tests/test_research_fanout.py:579-611` (no `HOME` monkeypatch); `research_fanout.py:664-677` | E7 (M14) |
| F9 | LOW | Further untested branches, each mutated to green: exit code counting `empty_unverified` as success (spec §3's rc=1 leg); the GitHub issues/discussions canary query (replaced with a junk term); the `gh` presence prerequisite; the canary sharing the primary's deadline; the releases canary's error path; `per_page`; slug truncation; GraphQL `errors` handling; the release mention predicate. | `research_fanout.py:1089`, `:781-782`, `:726-727`, `:864-869`, `:485-486`, `:382`, `:997`, `:417`, `:459` | E7 (M7-M12, M15, M17, M18) |
| F10 | LOW | A runner timeout kills only the direct child: `subprocess.run(timeout=)` leaves grandchildren running (measured: a pipeline's `sleep` survived). `last30days` (180 s default, its own thread pool and subprocesses) and the node CLIs are the realistic carriers. The repo already has the fix pattern (`start_new_session=True` + `os.killpg`). | `research_fanout.py:213-223`; precedent `python/src/dotfiles_setup/bounded_wait.py:48-59` | E8 |
| F11 | LOW | Child stderr is captured and then thrown away: an `error` reads only `exited N`, and `<source>.raw` holds stdout alone, so a failing `ctx7`/`firecrawl`/`python3` leaves the operator with nothing to diagnose. | `research_fanout.py:352-355`, `:636-649` | code read |
| F12 | LOW | Two `reason` strings claim more than their branch enforces: `GraphQL response contained errors` also fires for a non-dict payload that has no `errors` key; and a CONNECT timeout surfaces as `request failed`, not `timed out`, because urllib wraps it in `URLError` (an `OSError`, not a `TimeoutError`). | `research_fanout.py:417-418`; `:883-890` | E9 |
| F13 | LOW | The ratified spec drifted from the code in the same commit: spec §3 still sends `limit` to the developer index and omits `--sources web` from firecrawl-search — both are the live-arm fixes the code comments describe. | `docs/specs/research-fanout.md:68-69` vs `research_fanout.py:542-544`, `:575-578` | code read |
| F14 | LOW | Commit-message overclaims: "every empty result is control-armed with a canary query" (last30days has none — the module docstring and spec are correct); "Live arm: 7/7 sources ok" (as F4/F6 show, `ok` does not measure relevance for context7 or releases). | commit `50ba9eec` message; `research_fanout.py:803`, `:876` | E4, E6 |

## Q-FRESH / Q-SCOPE / Q-CLAIM

### Q-FRESH — decision→action pairs, re-validated immediately before the action?

| Decision | Action | Re-validated? |
|---|---|---|
| default-source filter `_parse_sources` (`:952-959`) | fetch | YES — `_source_result` re-runs `_prerequisite_reason` (`:832`) |
| `_last30days_script()` found (`:734`) | `python3 <script>` | YES — re-resolved, `script disappeared` branch (`:704-706`) |
| `shutil.which(tool)` (`:726-732`) | `runner([tool,…])` | Implicitly — exec re-resolves; a vanished tool → `FileNotFoundError` → `request failed` |
| primary deadline | canary call | YES — `deadline.remaining()` before each call (`:352`, `:501`, `:635`, `:643`) |
| **output dir state** | `_persist` writes | **NO** — existing `<source>.json`/`.raw` are never cleared → F5 |

### Q-SCOPE
All of F1–F14 are in scope for `50ba9eec`: the module, tests, spec and both consumers all land in this commit. **Ticket, not a change request:** `last30days`' per-project `.claude/last30days.env` is loaded when `LAST30DAYS_TRUST_PROJECT_CONFIG` is truthy in the process env (vendor `lib/env.py:209-215`), and that name is not credential-shaped, so `clean_env` passes it through. It is moot today: the variable is unset here and no `last30days.env` exists at the repo root, its parent or `~/.claude`. Also ticket-level: every `last30days` claim is verified against vendor **3.25.0** only, and the module picks the highest cached version with no version bound.

### Q-CLAIM — every operator-facing clause this diff adds

| Clause | Enforcing line | Verdict |
|---|---|---|
| `needs --repo` / `needs gh` / `needs EXA_API_KEY` / `needs ctx7` / `needs firecrawl` / `needs last30days script` | `:723-735` | enforced (`needs gh` untested, F9) |
| `exited N` | `:354-355`, `:637-638`, `:648-649` | enforced; stderr dropped (F11) |
| `invalid JSON` | `:356-359`, `:505-508` | enforced |
| `GraphQL response contained errors` | `:417-418` | **over-claims** for a non-dict payload (F12) |
| `unexpected JSON shape` | `:447-448`, `:485-486` | enforced |
| `HTTP <status>` | `:503-504` | enforced |
| `timed out` | `:883-885` | enforced for read timeouts; connect timeouts land in `request failed` (F12) |
| `request failed` | `:888-890` | enforced |
| `script disappeared` | `:704-706` | enforced |
| `no canary` / `canary failed` / `canary returned 0 items` | `:802-803`, `:817-820`, `:875-881` | enforced |
| `release body mentions a query term: yes/no` | `:459`, `:465` | substring-of-any-token; true but uninformative (F6) |
| `--list-sources` `present/absent` | `:975-977` | enforced; values never printed (tested `:549-576`) |
| usage errors (`QUERY is required…`, `--limit…`, `--timeout…`, `--sources must…`, `unknown source(s)…`) | `:960-967`, `:984-992` | enforced |
| `could not write output (<ExcType>)` | `:1083-1087` | enforced; type name only |
| docstring: "Empty answers carry a same-source control so absence is never confused with a broken transport" | `:863-881` | true for every source except `last30days`, which is disclosed |
| docstring: "strips LLM-provider variables, disables its dotenv file, and disables macOS Keychain lookup" | `:681-694` | TRUE against vendor 3.25.0 (`lib/env.py:30-41` empty string = clean mode; `:362` `_truthy("1")`); project-env route → ticket (Q-SCOPE) |
| spec §4 "Credentials never reach output … stderr" | none for non-OSError exceptions | **violated** by the traceback path (F2) |

## Evidence log

### E1 — exception escape (control-armed)
Scratchpad probe `exc_probe.py` against `git archive 50ba9eec` (`sys.path.insert` of the archived `python/src`), fake `http` raising each exception for sources `("exa","firecrawl-developer")`:

```
IncompleteRead -> ESCAPED fan_out: IncompleteRead
BadStatusLine -> ESCAPED fan_out: BadStatusLine
RemoteDisconnected(control) -> [('exa', 'error', 'request failed'), ('firecrawl-developer', 'error', 'request failed')]
URLError(control) -> [('exa', 'error', 'request failed'), ('firecrawl-developer', 'error', 'request failed')]
```
The two OSError-derived controls are handled, so the probe discriminates. `http.client.HTTPException` derives from `Exception`, not `OSError`; `IncompleteRead` is the realistic one (server closes mid-body during `response.read()`, `research_fanout.py:246`/`:260`).

### E2 — credential value in a traceback (offline; the ValueError fires in `putheader` before any connect)
```
EXA_API_KEY=$'SENTINEL-not-a-real-key\r\nX-Injected: 1' PYTHONPATH=<archive>/python/src \
  uv run --project python python -m dotfiles_setup.research_fanout "topic" --sources exa,github-issues --repo jdx/mise --out <scratch>/out_hdr
-> stderr line 83: ValueError: Invalid header value b'<SENTINEL>\r\nX-Injected: 1'   (sentinel count in log: 1)
-> rc=1; <scratch>/out_hdr does not exist (the github-issues result, fetched live and concurrently, is lost)
```
(Sentinel redacted here; it was a fabricated value, not a credential.) Trigger realism: a secret stored with a trailing newline in Doppler/fnox. Low probability, but it is exactly the output channel the module's contract (§4) forbids.

### E3 — API vs web URL (live, `gh` only)
```
gh api '/search/issues?q=repo:jdx/mise+tracked+configs&per_page=2' --jq '.items[] | {url, html_url, title}'
{"html_url":"https://github.com/jdx/mise/pull/13602",...,"url":"https://api.github.com/repos/jdx/mise/issues/13602"}
```
And through the reviewed module itself (`live_issues.py`, default runner, real `gh`):
```
github-issues ok None [('https://api.github.com/repos/jdx/mise/issues/13602', ...), ...]
github-discussions ok None [('https://github.com/jdx/mise/discussions/13600', ...), ...]   <- control: GraphQL `url` IS the web URL
github-releases ok None [('https://github.com/jdx/mise/releases/tag/v2026.9.14', ...), ...] <- control: reads html_url explicitly (:454)
```

### E4 — context7 library resolution (live, `ctx7` 0.5.12 = the mise pin, `which -a` first hit)
`ctx7 library --help` → `Usage: ctx7 library [options] <name> [query]` (`name: Library name to search for`).
```
ctx7 library "tracked configs"          -> 1. Title: Config / Context7-compatible library ID: /rust-cli/config-rs   (rc=0)
ctx7 library mise "tracked configs"     -> 1. Title: Mise   / Context7-compatible library ID: /jdx/mise           (rc=0)  <- control
```
The module's argv is the first form. The second form is what the rule `research-doc-sources.md` step 3 documents (`ctx7 library <name> [query]`). `ctx7` also offers `--json`, which the module does not use (it regex-parses human text, `:592-598`).

### E5 — stale per-source files (offline, fakes, archived module)
`stale_probe.py`: run 1 `main(["Tracked configs","--sources","exa,firecrawl-developer"])`, run 2 `main(["tracked-configs!","--sources","firecrawl-developer"])`, same `repo_root`, default `--out`:
```
dir files: ['exa.json', 'exa.raw', 'firecrawl-developer.json', 'firecrawl-developer.raw', 'manifest.json']
manifest query: tracked-configs! sources: ['firecrawl-developer']
```
`exa.json` belongs to run 1 and a different query; the manifest no longer mentions it; the workflow's triage prompt says "Read these research-fanout manifests and every <source>.json beside them".

### E6 — release mention flag (live `gh api 'repos/jdx/mise/releases?per_page=10'`, module's own predicate re-implemented verbatim)
```
'tracked configs': mentions=yes on 6/10
'qzxvkw to': mentions=yes on 10/10
'qzxvkw jq': mentions=yes on 2/10
'qzxvkw': mentions=yes on 0/10      <- known-absent control (fresh string)
'is python fixed': mentions=yes on 10/10
```

### E7 — mutation sweep (archived `50ba9eec` tree copied per mutation, `PYTHONPATH=<copy>/python/src`, `python/.venv/bin/python -m pytest <copy>/tests/test_research_fanout.py -x`; each mutation asserted to apply exactly once)
Baseline at the ref: `27 passed`, `ruff` and `ty` clean.
```
M0 control: canary count>0 -> is not None: rc=1 1 failed      <- harness live
M1 firecrawl-dev k->limit: rc=1 1 failed                       <- live-shape test has teeth
M2 drop --sources web: rc=1 1 failed                           <- live-shape test has teeth
M3 url/html_url precedence swap: rc=0 27 passed                <- F3
M4 gh env unscrubbed: rc=0 27 passed                           <- F7
M5 firecrawl env unscrubbed: rc=0 27 passed                    <- F7
M6 ctx7 env unscrubbed: rc=0 27 passed                         <- F7
M7 rc=0 on empty_unverified: rc=0 27 passed                    <- F9
M8 gh-issues canary = junk term: rc=0 27 passed                <- F9
M9 drop gh which() prerequisite: rc=0 27 passed                <- F9
M10 discussions ignore GraphQL errors: rc=0 27 passed          <- F9
M11 release mention always yes: rc=0 27 passed                 <- F9
M12 canary gets fresh full deadline: rc=0 27 passed            <- F9
M13 last30days LLM keys kept: rc=1 1 failed                    <- the one env test that exists
M14 last30days in defaults: rc=1 (real HOME) || HOME=empty: rc=0 27 passed   <- F8
M15 slug no truncation: rc=0 27 passed                         <- F9
M16 exa key from wrong var: rc=1 1 failed
M17 github-issues per_page dropped: rc=0 27 passed             <- F9
M18 releases canary skipped (count=1 always): rc=0 27 passed   <- F9
```
M14 on the real HOME fails with `AssertionError: unexpected subprocess call: ['python3', '/Users/…/.claude/plugins/cache/last30days-skill/last30days/3.25.0/…/last30days.py', 'topic', '--emit=json']`, raised by the fake runner inside a worker thread, not by the test's manifest assertion.

### E8 — grandchild survives a runner timeout (control-armed)
`orphan_probe.py`: a self-started `sleep 9673` (control), then `default_runner(["sh","-c","sleep 9671 | cat; sleep 9672"], timeout=1.0)`:
```
TimeoutExpired raised
survivors: /bin/sleep 9673 (control)   /bin/sleep 9671 (orphaned grandchild)
```
Both were killed by PID afterwards; `pgrep` then returned none.

### E9 — urllib connect-timeout type
`urllib.request.urlopen("http://10.255.255.1/", timeout=1)` → `URLError`, `isinstance(OSError)=True`, `isinstance(TimeoutError)=False`, `.reason` is a `TimeoutError`. So `_source_result`'s `except TimeoutError` (`:883`) never sees it and the `OSError` branch reports `request failed`.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — live `gh api` probes of `/search/issues` (`url` vs `html_url`), `releases?per_page=10` (mention predicate), GraphQL discussions via the module; `ctx7 library mise` control.
- [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) — slug confirmed from the plugin's own metadata (12 references in `.claude-plugin/`/`README.md`); vendor script read from the local plugin cache `~/.claude/plugins/cache/last30days-skill/last30days/3.25.0/skills/last30days/scripts/lib/env.py` (`:30-41`, `:124-127`, `:209-215`, `:362`, `:461-476`, `:495-552`).
- context7 (`ctx7` 0.5.12 CLI, `/rust-cli/config-rs` and `/jdx/mise` resolutions) — a service, not a repo read.
