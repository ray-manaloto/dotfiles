# Cold review round 2 — `0a908d9e` (research-fanout fix round)

- **Subject:** `0a908d9eb1ff417e3dc101a23bf624046690e000`, parent `50ba9eec8c47b24e6da740403880eb8d35038c53`.
- **Reviewer:** cold-reviewer (Opus), diff-only, round 2, BOUNDED.
- **Domain (14 items):** F1-F12 from `cold-review-50ba9eec-2026-09-26.md`, plus C1 (codex: `IncompleteRead` escape) and C2
  (codex: the deadline must cover the whole response) from `codex-review-50ba9eec-2026-09-26.md`. The brief also asks
  whether any fix introduced a new defect in the lines it touched. That is scoped to touched lines; it is not an open hunt.
- **Stop condition:** BOUNDED. Answering the 14 verdicts and the touched-lines question ends the round, whatever the
  findings are. A further round is warranted only if dispositioning N1-N6 changes the enumeration. It would then be
  scoped to `default_runner` and `_read_http_body` alone.
- **Memory:** consulted `.claude/agent-memory-local/cold-reviewer/` (`fetcher_fanout_review_patterns.md`, the mutation
  harness notes, and the note that a `ps` census counts its own command line).
- **Graph:** not used. The PreToolUse hook reported `graph.json` STALE for this file, and the subject is one pinned diff.
- **Status:** COMPLETE.
- **Score:** 10 FIXED, 3 PARTIAL (F4, F6, C2), 0 NOT FIXED. 6 new rows in touched lines: 1 MEDIUM (N1) and 5 LOW.
- **Verdict:** the round-1 defects are closed except F6 and C2, where the fix follows the spec but misses the real
  behaviour, and F4, whose no-`--repo` residual the spec sanctions. **N1 is a regression introduced by the F10 fix.** The
  parent runner returned in 1.01 s; this one blocks until an escaped descendant exits. Fix N1 before relying on the
  timeout. N2-N6 are small.

## Verdicts (domain: 14)

| # | Verdict | Claim | file:line | Probe |
|---|---|---|---|---|
| F1 | FIXED | `HTTPException` and `ValueError` become a per-source `error` at both the primary and canary boundaries. The manifest and every other source's result persist. | `research_fanout.py:1017-1021`, `:931-937` | R1 F1a/F1b RED; R2: a truncated chunked body over a real socket gives `request failed`, and the manifest is written |
| F2 | FIXED | A CR/LF or non-latin-1 credential yields `invalid credential header for <NAME>`, validated before any connect. No value appears in stdout, stderr or any file. | `:440-447`, `:630-632`, `:655-657`, `:1002-1006` | R3: CLI run with sentinels in `EXA_API_KEY` and in `FIRECRAWL_API_KEY`: **0 hits** in stdout, stderr and every out file. Control: the reason string is present in both manifests (1 hit each). Round-1 E2 control on the parent: 1 hit. R1 F2a/b/c RED |
| F3 | FIXED | `_record_item` prefers `html_url`. The fixture now carries both `url` (the API link) and `html_url`. | `:335`; `tests/test_research_fanout.py:514-523` | R1 F3 (swap back) RED |
| F4 | PARTIAL | With `--repo` the library is the repo's name part (`mise`). Without `--repo` it is still `ctx7 library <whole query>`, the round-1 mechanism. Spec §8 item 7 sanctions that residual, and a test pins it. | `:743`; test pin `tests/…:816` | R1 F4 RED; R6 argv trace for `repo=None`: `['ctx7','library','tracked configs']` |
| F5 | FIXED | Before writing, the out dir is cleared of `manifest.json` and every known `<source>.json`/`.raw`. Unrelated files are kept. | `:1156-1160` | R1 F5 RED (the test also asserts `operator-notes.txt` survives) |
| F6 | PARTIAL | Whole-word matching, a minimum term length of 3 and the stopwords closed the short-word cases. The predicate still matches ANY term, and generic English stopwords do not cover changelog vocabulary. On the round-1 evidence query the filter still keeps nearly everything. | `:535-564`, `:568-573` | R4, live `jdx/mise` (100 releases): `"is python fixed"` kept **98/100** (round 1: 10/10); `"qzxvkw use"` 71/100; `"qzxvkw to"` 0/100 (fixed); fresh control `"wqkzvx"` 0/100 |
| F7 | FIXED | Credential scrubbing is asserted for the `gh`, `firecrawl`, `ctx7` and `last30days` child envs, with a non-kept sentinel. | `tests/…:907-983`, `:986-1040` | R1 M4/M5/M6/M13 all RED |
| F8 | FIXED | The default-set test sets `HOME` and `LAST30DAYS_SCRIPT`, so its fail arm no longer depends on the author's plugin cache. | `tests/…:1330-1366` | R1 M14 RED under the real HOME AND `HOME=<empty>` (round 1: green under the empty HOME) |
| F9 | FIXED | All 9 named branches now carry a test. | tests named in R1 | R1 M7, M8, M9, M10, M11, M12, M15, M17, M18: all RED |
| F10 | FIXED (the stated shape) | New session plus process-GROUP SIGTERM, then SIGKILL. A pipeline grandchild dies within the budget. **The fix introduced N1 and N2.** | `:240-263` | R5 (macOS, real processes): `sh -c "sleep 9681 \| cat; sleep 9682"`, budget 1.0 s, elapsed 1.01 s, both sleeps dead; the unrelated `sleep 9683` control survived. R1 F10a/b RED |
| F11 | FIXED | The error reads `exited N: <last 300 chars of stderr>`, with each child-env credential value `[REDACTED]` before truncation. | `:411`, `:422-437`, `:751`, `:762` | R1 F11a/b RED. `is_credential` is True for all 8 kept names (control: PATH and HOME are False) |
| F12 | FIXED | A non-object GraphQL reply reads `unexpected response shape`, and `errors` fires only when the key exists. A `URLError` wrapping a timeout reports `timed out`. | `:501-504`, `:1017-1037` | R1 F12a/b RED; R7 real transport: connect to `10.255.255.1` gives `timed out` in 1.01 s; control `127.0.0.1:1` (refused) gives `request failed` |
| C1 | FIXED | Same boundary as F1. ⚠️ `IncompleteRead` is now unreachable for content-length responses; see N3. | `:1017-1021` | R2: parent-code `response.read()` raises `IncompleteRead` on the truncated body; the fix gives a per-source error |
| C2 | PARTIAL | The deadline is checked only BETWEEN `response.read(65536)` calls. `http.client`'s `read(amt)` uses a BufferedReader that loops until `amt` bytes or EOF (`http/client.py:479`), so one call can run for up to 64 KiB × the per-recv timeout. The spec §8 item 3 wording ("between chunks") has the same gap. The test double returns one chunk per call whatever `amt` is, so it cannot produce this outcome. | `:266-278`; fixture `tests/…:89-108` | R2, real local socket: a 53-byte body dripped at 0.2 s/byte with a 1.0 s budget ran **10.57 s**, then `timed out`. Controls: `fast` 0.01 s `ok`; `stall` 1.00 s `timed out` |

## New defects in touched lines

| # | Severity | Claim | file:line | Probe |
|---|---|---|---|---|
| N1 | MEDIUM | **Regression from the F10 fix.** After SIGKILL, `process.communicate()` has no timeout. A descendant that left the group (setsid or daemonised) and still holds stdout/stderr blocks the runner until it exits. That worker blocks the whole fan-out, so the timeout is no longer a hard bound. The parent's `subprocess.run` called `kill()` and then `wait()`, never reading the pipes, and returned on time. The new test's fake `Popen` returns on its third `communicate`, so it cannot produce the hang. | `research_fanout.py:261`; fake `tests/…:462-472` | R5b, ephemeral `python:3.14-slim-bookworm` (Linux), budget 1.0 s. Fix: **6.04 s** (bounded only by the descendant's `sleep 6`) on the setsid arm and on the SIGTERM-ignoring arm. Control (grandchild stays in the group): 1.02 s. Same arms on the parent `50ba9eec`: **1.01 s** on all three |
| N2 | LOW | `suppress(ProcessLookupError)` does not cover macOS, where `killpg` on a group holding only a zombie raises `PermissionError` (EPERM). It escapes `default_runner` as an `OSError`, the source reports `request failed` instead of `timed out`, and the child is never reaped. The trigger is the same as N1. | `:259-260` | R5 macOS arm: traceback ends `os.killpg(process.pid, signal.SIGKILL)` → `PermissionError: [Errno 1] Operation not permitted` |
| N3 | LOW | For a content-length body, `read(amt)` returns short data and then `b""`; it does not raise `IncompleteRead` (`http/client.py:480-483`: "Ideally, we would raise IncompleteRead…"). So a truncated body is accepted as complete, persisted as `.raw`, and reported as `invalid JSON`, which blames the content for a transport truncation. | `:271-274` | R2: the truncated content-length body gives `('error','invalid JSON')`. Controls: the parent read raises `IncompleteRead`; the truncated chunked body gives `request failed` |
| N4 | LOW | With `--repo`, the context7 canary runs `ctx7 library <repo-name>` and then `docs <id> python`, but records `control.query='python'`. It also shares the primary's library resolution, so a repo name that context7 does not index cannot be verified by the canary. | `:743` × `:899-900` | R6 argv trace: `['ctx7','library','mise']`, `['ctx7','docs','/jdx/mise','python']`, with `control.query='python'` |
| N5 | LOW | Four fixed clauses have no test (each mutated to green). They are the `FIRECRAWL_API_KEY` header validation (live-verified by R3), the `>=3` term-length clause (load-bearing: whole-word `to` matches **96/100** live mise releases, control 0), the two ctx7 `_subprocess_error` sites, and the firecrawl branch of `_read_http_body`. | `:655-657`, `:538`, `:751`, `:762`, `:316-318` | R1 F2d, F6d, F11c, F11d, C2c: all `50 passed` |
| N6 | LOW | The stderr tail keeps internal newlines, so the one-line-per-source stdout summary breaks. A failing Python child (a traceback) turned 2 lines into 4. The consumers take the manifest path from line 1, so there is no functional break found. | `:437` × `:1186-1193` | R8: stdout had 4 lines, expected 2 |

Outside the touched lines, not a finding: spec §3's `github-releases` row (`per_page=<limit>`) and `context7` row
(`ctx7 library <query>`) were not updated; only §8 records the change. That is the F13 class, which is outside this
round's domain.

## Evidence log

### R0 — tree state and baseline

`HEAD == 0a908d9e`. `git status --short` showed only this report untracked, and `git diff --quiet 0a908d9e -- python/`
held. The probes ran against `git archive 0a908d9e`, copied to the scratchpad (`r2/ref`: `python/src` + `tests`); each
probe asserts `module.__file__` is inside the copy. Baseline:
`PYTHONPATH=<ref>/python/src python/.venv/bin/python -m pytest tests/test_research_fanout.py` gave `50 passed` under
the real `HOME` and under `HOME=<empty dir>`. Python 3.14.0 (macOS); 3.14.7 (Linux container).

### R1 — mutation sweep (40 applied, each asserted `count(old)==1`, each run under the real `HOME` and under `HOME=<empty>`)

The harness is `r2/mutate2.py`: a per-mutation `copytree`, the venv python, and `PYTHONPATH` pointing at the copy. The
two HOME columns agreed on every row.

```
M0 CONTROL canary count>0 -> is not None ........ RED (2 failed)   <- harness imports the COPY
F1a source except narrowed to OSError ............ RED  test_transport_failure_isolated_and_manifest_persisted
F1b canary except narrowed ....................... RED  test_canary_transport_failure_does_not_escape[x2]
F2a CRLF check removed ........................... RED  test_invalid_credential_header_never_leaks_value[CRLF]
F2b latin-1 check removed ........................ RED  test_invalid_credential_header_never_leaks_value[snowman]
F2c exa call site bypass ......................... RED  (both params)
F2d firecrawl call site bypass ................... GREEN 50 passed          <- untested call site (N5)
F3  url/html_url precedence swap back ............ RED  test_subprocess_sources_normalize_items[case0]
F4  context7 library from query .................. RED  test_context7_uses_repo_name_for_library_resolution
F5  unlink loop removed .......................... RED  test_reused_output_directory_clears_only_owned_files
F6a whole-word -> substring ...................... RED  test_github_releases_filter_whole_words_and_stopwords
F6b release filter removed ....................... RED  (2)
F6c stopwords removed ............................ RED
F6d min term length (>=3) removed ................ GREEN 50 passed          <- untested clause (N5)
F7  gh / firecrawl / ctx7 / last30days env unscrubbed  RED x4
F7  LAST30DAYS_TRUST_PROJECT_CONFIG pop removed .. RED
F8  last30days in defaults ....................... RED under BOTH HOMEs (round 1: green under empty HOME)
F9  M7 M8 M9 M10 M11 M12 M15 M17 M18 ............. RED x9 (each by a named test)
F10a start_new_session=False ..................... RED  test_default_runner_terminates_process_group_on_timeout
F10b SIGTERM via process.terminate() ............. RED
F11a stderr tail dropped / F11b redaction removed  RED x2  test_nonzero_subprocess_is_error
F11c ctx7 `library` error back to bare `exited N`  GREEN 50 passed          <- untested (N5)
F11d ctx7 `docs` error back to bare `exited N` ... GREEN 50 passed          <- untested (N5)
F12a URLError(TimeoutError) not classified ....... RED  test_wrapped_socket_timeout_reports_timed_out
F12b GraphQL shape branches merged ............... RED
C2a body deadline checks removed ................. RED  test_default_http_deadline_covers_streaming_body
C2b exa branch uses bare response.read() ......... RED (2)
C2c firecrawl branch uses bare response.read() ... GREEN 50 passed          <- untested branch (N5)
C2d 8 MiB cap removed ............................ RED
```

### R2 — `default_http` over a real local socket (`r2/http_probe2.py`)

`urllib.request.urlopen` is redirected to a `127.0.0.1` server. The server drains the request, then half-closes with
`SHUT_WR`. The first version skipped the drain, so the truncated arm returned `ConnectionResetError` and measured
nothing; that run is discarded. The response keeps real `http.client` semantics.

```
fast               budget=1.0s elapsed= 0.01s -> ('ok', None, 1)
stall              budget=1.0s elapsed= 1.00s -> ('error', 'timed out', 0)
drip               budget=1.0s elapsed=10.57s -> ('error', 'timed out', 0)          <- C2 PARTIAL
truncated-cl       budget=2.0s elapsed= 0.00s -> ('error', 'invalid JSON', 0)       <- N3
truncated-chunked  budget=2.0s elapsed= 0.00s -> ('error', 'request failed', 0)     <- C1 fixed path
truncated-cl  reader=parent-read (50ba9eec transport: one response.read()) -> RAISED IncompleteRead  <- control
```

`http/client.py` (3.14.0) lines 475-488 show the `read(amt)` branch: `self.fp.read(amt)` (a BufferedReader, which
loops until `amt` bytes or EOF), and no `IncompleteRead` on a short content-length body.

### R3 — credential header through the module CLI (offline: validation fires before any connect)

`EXA_API_KEY=<sentinel>$'\r\nX-Injected: 1' uv run --project python python -m dotfiles_setup.research_fanout "topic" --sources exa`,
and the same with `FIRECRAWL_API_KEY` and `--sources firecrawl-developer`. Both exited rc=1 with 0 bytes on stderr.
Sentinel counts: `hdr_*.out` 0, `hdr_*.err` 0, and 0 in every file under both out dirs. Control: both manifests carry
`invalid credential header for EXA_API_KEY` / `…FIRECRAWL_API_KEY`, which proves the sentinel reached the module. The
sentinels were fabricated values. Not run through `mise run` on purpose: mise re-injects the user's env and could
replace the sentinel with a real key.

### R4 — release filter against live `gh api 'repos/jdx/mise/releases?per_page=100'` (rc=0, 100 releases)

This runs the module's own `_github_releases` with a runner that returns those bytes, `limit=100`:

```
'tracked configs'    kept= 29/100
'is python fixed'    kept= 98/100      <- round-1 evidence query; still ~all
'fixed'              kept= 98/100
'qzxvkw to'          kept=  0/100      <- fixed (length floor + whole word)
'qzxvkw use'         kept= 71/100      <- 3-letter common word
'wqkzvx'             kept=  0/100      <- fresh known-absent control
```

Min-length clause (N5): with a whole-word match, `to` alone matches 96/100 releases; fresh control `zqxwvk` matches 0.

### R5 — `default_runner` with real processes

macOS (`r2/runner_probe.py`):

```
F10 pipeline grandchild (same group)      budget=1.0s elapsed=1.01s -> TimeoutExpired; 9681/9682 gone, control 9683 alive
N1 control: grandchild in group           budget=1.0s elapsed=1.00s -> TimeoutExpired; no survivors
N1 arm: setsid grandchild holds stdout    -> PermissionError: [Errno 1] Operation not permitted  (os.killpg …SIGKILL, :260)   <- N2
```

(The survivors list also matched my own zsh command line, which contains the literal `sleep 9681`. That row is the
probe, not a survivor. I killed the control `sleep 9683` by PID afterwards. The escaped `sleep 8` had already exited, so `kill` reported "no such
process". A follow-up `ps -axo pid=,command= | grep -E '/bin/sleep (968[0-9]|8)$'` returned rc=1, meaning no match.)

R5b, Linux (`docker run --rm --network none python:3.14-slim-bookworm`, module mounted read-only):

```
                                         fix 0a908d9e     parent 50ba9eec
control: grandchild stays in group       1.02s            1.01s
arm: setsid grandchild holds stdout      6.04s            1.01s     <- N1
arm: SIGTERM-ignoring child + setsid     6.04s            1.01s     <- N1
```

### R6 — context7 argv trace (scripted runner; primary docs empty, canary docs non-empty)

```
repo=jdx/mise: ['ctx7','library','mise'] ['ctx7','docs','/jdx/mise','tracked configs'] ['ctx7','library','mise'] ['ctx7','docs','/jdx/mise','python']  control.query='python'
repo=None:     ['ctx7','library','tracked configs'] … ['ctx7','library','python'] ['ctx7','docs','/jdx/mise','python']
```

### R7 — connect timeout vs refused (real transport, `fan_out(..., http=default_http)`)

`10.255.255.1` gave `error / timed out` in 1.01 s. `127.0.0.1:1` gave `error / request failed` in 0.00 s.

### R8 — multi-line stderr in the summary

A scripted `firecrawl` child exited 1 with a 3-line traceback on stderr. `main` then wrote 4 stdout lines instead of 2:
the path, then a source row split across three lines.

## Q-SCOPE

Every N-row is in scope: each sits in a line this commit added. F4's residual and F6's ANY-term predicate are
spec-faithful (spec §8 items 7 and 9). The disposition there is a spec decision, which is a ticket or a spec revision,
not a code defect against the spec. C2's between-chunks wording is also in spec §8 item 3.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — live `gh api 'repos/jdx/mise/releases?per_page=100'` replayed through the
  release filter (R4).
- [python/cpython](https://github.com/python/cpython) — the installed 3.14.0 `http/client.py` `read(amt)` branch
  (lines 463-501), read locally from the uv-managed interpreter, not fetched.
