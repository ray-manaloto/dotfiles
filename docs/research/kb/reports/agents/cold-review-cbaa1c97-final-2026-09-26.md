# Cold review — FINAL bounded round — `cbaa1c97` (research-fanout review-2 fixes)

- **Subject:** `cbaa1c9713b63c61e83e10d68f9477b2a3386137`, parent `0a908d9e`.
- **Reviewer:** cold-reviewer (Opus), diff-only, round 3, BOUNDED.
- **Domain (9 items):** spec `docs/specs/research-fanout.md` §9 items N1 (§9.1), N2 (§9.2), Ctrl-C (§9.3), C2 (§9.4),
  N3 (§9.5), N4 (§9.6), N5 (§9.7), N6 (§9.8), F6 all-terms (§9.9). Sources:
  `cold-review-0a908d9e-round2-2026-09-26.md` and `codex-review-0a908d9e-round2-2026-09-26.md`.
  Plus: new HIGH/MEDIUM defects in lines this commit touched only.
- **Stop condition:** BOUNDED. Answering the 9 verdicts plus the touched-lines question ends the round.
- **Memory:** consulted `.claude/agent-memory-local/cold-reviewer/` (`fetcher_fanout_review_patterns.md`,
  `mutation_harness.md`).
- **Graph:** not used. The subject is one pinned diff, and the hook reports `graph.json` possibly STALE for this file.
- **Status:** COMPLETE.
- **Score:** **9/9 FIXED**, 0 PARTIAL, 0 NOT FIXED. **0 new HIGH/MEDIUM defects in touched lines.** Three LOW
  observations sit below the bar and are listed for disposition only. One Q-SCOPE ticket recommendation covers a
  sibling class that round 1 (`0a908d9e`) introduced, not this commit.
- **Verdict:** SHIP for the §9 domain. Every fix was verified with a real child process, a real socket, a live CLI or
  live upstream data, each against the parent `0a908d9e` as the control arm. The stop condition is met: all 9 questions
  are answered, and nothing found changes the enumeration.

## Verdicts (domain: 9)

| # | Verdict | Claim | file:line | Probe |
|---|---|---|---|---|
| N1 (§9.1) | FIXED | After the group SIGKILL, the drain is `communicate(timeout=2.0)`. On expiry the pipes are closed and the direct child is killed and reaped with a bounded `wait`. A detached descendant that holds stdout no longer extends the runner past `timeout + 3 s`. | `research_fanout.py:290-308`, `:336-362` | R1 (real processes, budget 1.0 s). **Linux:** the setsid arm took **3.23 s** and the SIGTERM-ignoring+setsid arm **3.21 s**; the parent `0a908d9e` took 6.03 s and 6.04 s. **macOS:** fix 3.21 s / 3.21 s, parent TERM-ignoring arm 6.06 s. Control (grandchild stays in the group): 1.01 s on both refs and both OSes. The direct child is `gone` (reaped) in every fix arm. The escaped grandchild survives, which is by design: it left the group. |
| N2 (§9.2) | FIXED | `_signal_process_group` suppresses `ProcessLookupError` and `PermissionError` for both group signals. The macOS zombie-only-group EPERM no longer escapes, the child is reaped, and the source reports `timed out`. | `:276-280` | R1 macOS setsid arm: fix raised `TimeoutExpired` (child `gone`), and `fan_out` gave `error/timed out` in 3.21 s. Control, parent `0a908d9e`: `PermissionError`, and `fan_out` gave `error/request failed`. |
| Ctrl-C (§9.3) | FIXED | Live children are tracked. On `KeyboardInterrupt` in `future.result()`, `_cancel_live_processes` sets a cancel event and SIGTERMs every live group. Each worker's `_communicate_until` polls the event every 0.1 s and runs the bounded TERM→KILL cleanup. `main` returns 130. | `:311-333`, `:343-360`, `:1177-1196`, `:1357-1360` | R2 (real CLI process, real children, SIGINT delivered to the CLI's process group as a terminal does, `--timeout 8`). **Fix:** `last30days` alone: rc=**130**, SIGINT→exit **0.07 s**. `last30days,context7`: rc=130 in 0.05 s. Both direct children AND their in-group grandchildren (`sleep 4101`, `sleep 4102`) are `gone`. **Parent `0a908d9e`:** 7.63 s / 7.61 s, rc=-2, stderr ends `KeyboardInterrupt`. Observation, not a §9.3 defect: an in-flight **HTTP** source still holds the exit until its deadline (fix 7.51 s, rc=130; parent 7.50 s, `KeyboardInterrupt` escaped). The item is scoped to child GROUPS, and the behaviour is unchanged from the parent. |
| C2 (§9.4) | FIXED | The body read runs in a daemon thread; the caller waits on a queue with `timeout=deadline.remaining()` and raises `TimeoutError` on expiry. A 1-byte trickle is bounded by the deadline. Public APIs only (`queue`, `threading`, `response.read/close/headers`), no private attribute. | `:365-401` | R3 (real `127.0.0.1` socket, 1 byte per 0.2 s, budget 1.0 s). **Fix:** exa CL drip **1.01 s**, chunked drip 1.00 s; firecrawl CL 1.00 s, chunked 1.01 s; HTTP 500 drip (the `HTTPError` path) 1.01 s. All `error/timed out`. **Parent:** 13.66 s / 13.86 s / 13.66 s / 13.88 s / 13.65 s. Controls: fast gives `ok` (1 item) and stall gives 1.00 s on both refs. CLI-level (R3b, `python -m`, urlopen redirected via `sitecustomize`): fix wall **1.10 s**, rc=1, both sources `[timed out]`; parent 13.83 s. So the leaked daemon reader threads do not hold the process open. |
| N3 (§9.5) | FIXED | When `Content-Length` is present and fewer bytes arrive, the result is `_IncompleteResponseError` → `incomplete response`. | `:369-386`, `:1135-1139` | R3 truncated-CL (body is valid JSON, declared +10 bytes): fix gives `error/incomplete response` for **both** exa and firecrawl-developer. Parent: `ok` with 1 item, so the short body was silently accepted. Control: truncated-chunked gives `request failed` on both refs (the C1 path, unchanged). |
| N4 (§9.6) | FIXED | The context7 canary runs with `replace(request, repo=None)`, so it resolves `ctx7 library python` → `ctx7 docs <id> python` whatever `--repo` is. It records `control.query='python'`, which is exactly the query it ran. | `:1049-1058`; `_control_query` `:1024-1025` | R4, LIVE `ctx7` 0.5.12 through the real `_empty_control` + `default_runner` (recording runner). **Fix**, for `repo=jdx/mise`, an unindexed `repo=wqzkvxnotarepo/zqvkwx`, and `repo=None`: all three ran `['ctx7','library','python'] ['ctx7','docs','/python/cpython','python']`, giving `control=(query='python', count=5)`. **Parent:** `jdx/mise` ran `library mise` → `docs /jdx/mise python`; the unindexed repo ran `library zqvkwx` → `count=None`, `err=exited 1:`. So the canary had failed on a repo name context7 does not index. |
| N5 (§9.7) | FIXED | All four named gaps now have a failing-arm test. | tests: `test_invalid_credential_header_never_leaks_value[header_case1-*]`, `test_github_releases_ignore_terms_shorter_than_three_letters`, `test_context7_reports_both_subprocess_error_sites[library\|docs]`, `test_default_http_deadline_covers_real_streaming_body[firecrawl-developer]` | R5 mutation sweep (21 rows, each `count(old)==1`, each under the real HOME AND `HOME=<empty>`; both columns agree on every row). N5a firecrawl header bypass RED (2). N5b `>=3` removed RED. N5c ctx7 `library` site bare RED. N5d ctx7 `docs` site bare RED. C2b firecrawl branch bare `response.read()` RED. Harness control M0 (the `incomplete response` string changed) RED. |
| N6 (§9.8) | FIXED | CRLF and bare CR are normalised to `\n`, then `\n` becomes ` \| `, after credential redaction and before the 300-char tail. A failing child's multi-line stderr stays on one stdout row. | `:556-561` | R6, real child (a `last30days` script writing `\r\n`, a bare `\r`, `\n`, VT, FF and U+2028 to stderr, then exiting 3) through `python -m`. **Fix:** 2 `\n`-delimited stdout lines. **Parent:** 4. Mutation N6a (collapse removed) RED. Residual, LOW and outside the `\n` spec: VT, FF and U+2028 pass through, so Python `str.splitlines()` still sees 5 lines (parent 8). Mutation N6b (CR normalisation removed) stays GREEN, because the test has no `\r`. |
| F6 all-terms (§9.9) | FIXED | A release is kept only when every retained term (length ≥3, not a stopword) appears as a whole word in the tag, name or body. An all-stopword query keeps nothing. | `:659-679`, `:696-698` | R7, live `gh api 'repos/jdx/mise/releases?per_page=100'` (rc=0, 100 releases) through the module's own `_github_releases`. **Fix:** `"is python fixed"` **33/100**, which equals an independent recount of releases containing BOTH `python` and `fixed` (33; first `v2026.9.10`). `"wqkzvx fixed"` **0/100** (parent **98/100**). `"tracked configs"` 7/100 (parent 29). `"fixed"` 98/100 on both. Fresh absent `"zqwvkx"` 0/0. Mutation F6a (all→any) RED (2 tests). F6b (the `not terms` guard removed) stays GREEN: an untested clause whose code is correct. mise releases DO say "python", so the spec's hypothetical "→ empty" is correctly non-empty here. |

## New HIGH/MEDIUM defects in touched lines

**None.** Candidates examined in touched lines, each probed:

- the leaked daemon reader and closer threads after a body timeout (R3b: the CLI still exits in 1.10 s);
- `outcomes.get(timeout=deadline.remaining())` raising before `get` when the deadline is already spent (an unclosed
  response only; no wrong status);
- the `AttributeError` that `_read_http_body` re-raises and `_source_result` does not catch. It is unreachable from urllib's own
  raise sites, which always pass real `hdrs`; and `HTTPError.__init__` substitutes `BytesIO` for a missing `fp`
  (`urllib/error.py:45-47`);
- `_cancel_live_processes` signalling a pgid whose leader was just reaped (ESRCH is suppressed; a PID-reuse window of
  microseconds);
- a second Ctrl-C during executor shutdown (workers have already observed the event within 0.1 s).

None reaches MEDIUM.

### Below the bar (LOW), for disposition only, not findings of this round

| # | Severity | Claim | file:line | Probe |
|---|---|---|---|---|
| L1 | LOW | `_read_http_body` compares the body with the raw `Content-Length` header even on a `Transfer-Encoding: chunked` response, where `http.client` ignores CL by design (`http/client.py:367-380`, "RFC 2616, S4.4, #3 says we ignore this if tr_enc is chunked"). A TE+CL response is now `incomplete response`. | `:369-386` | R8 real socket, valid chunked body plus `Content-Length: <encoded length>`: fix `error/incomplete response`, parent `ok` with 1 item (the first run used a broken chunk encoder and is VOID; this is the corrected re-run). Why only LOW: RFC 9112 §6.1 says a sender MUST NOT send both, and live `curl --http1.1` against `api.firecrawl.dev` (400) and `api.exa.ai` (402) shows plain `Content-Length` framing with no TE. |
| L2 | LOW | Test gaps on correct code. The cancel-event poll (CC-b) is load-bearing only for a SIGTERM-ignoring child, and no test covers it. The same holds for the final kill+wait reap (N1c), CR normalisation (N6b), the `not terms` guard (F6b) and the cancel-event `clear()` (CC-d). | `:315-316`, `:306-308`, `:559`, `:675`, `:1196` | R5: all five mutations GREEN under both HOMEs. R2c real arm for CC-b: with the poll removed, a SIGTERM-ignoring child holds Ctrl-C for **7.86 s**; with the fix, **0.26 s**. (The first mutant run was VOID: a zsh `no matches found` broke the `&&` chain, so the CLI imported the installed, unmutated module. The re-run verified `m.__file__` and the mutated source first.) |
| L3 | LOW | VT, FF and U+2028 in a child's stderr still pass through to the summary row. The `\n` requirement of §9.8 holds. | `:559-560` | R6: `str.splitlines()` sees 5 lines (parent 8); `\n`-delimited lines: 2 (parent 4). |

### Q-SCOPE — ticket recommendation (sibling of §9.3; introduced by `0a908d9e`, not by this commit)

SIGTERM or SIGHUP to the CLI orphans every live source child. Since round 1's `start_new_session=True`
(`research_fanout.py:345`, unchanged here), children never receive a group-directed signal, and §9.3 intercepts only
`KeyboardInterrupt`. R9, real CLI, `killpg(cli, SIGTERM)` with `last30days` running: on **fix** and on **parent**
`0a908d9e`, the CLI dies at once (rc=-15) and the `last30days` child plus its in-group grandchild stay **ALIVE**. They
would run to their own end: 180 s by default for last30days, holding API quota. Control, `50ba9eec` (before
`start_new_session`): the grandchild is `gone` and the child is exiting. Recommend a ticket: install a SIGTERM/SIGHUP
handler that raises into the same `_cancel_live_processes` path, or document the limit. Not a change request against
`cbaa1c97`.

## Evidence log

All probes ran against `git archive cbaa1c97` (`python/src` + `tests/test_research_fanout.py`) and `git archive 0a908d9e`
in the session scratchpad (`r3/ref`, `r3/parent`). Each in-process probe asserts `module.__file__` is inside its
copy. `git diff --quiet cbaa1c97 -- python/ tests/` held, and `git status` showed only this report.

### R0 — baseline

`PYTHONPATH=r3/ref/python/src python/.venv/bin/python -m pytest tests/test_research_fanout.py` gave **62 passed**
under the real `HOME` (rc=0) and under `HOME=<empty dir>` (rc=0). The commit's own gate numbers (lint rc=0, pytest
3940 passed, verify 165/0/4) are INHERITED and were not re-run in this bounded round.

### R1 — `default_runner`, real processes (`r3/runner_probe3.py`; budget 1.0 s; grandchild = `python -c time.sleep(6)`)

```
macOS    fix    control-grandchild-in-group   1.01s TimeoutExpired  child=gone grandchild=gone
macOS    fix    setsid-grandchild-holds-pipe  3.21s TimeoutExpired  child=gone grandchild=Ss (left the group, by design)
macOS    fix    TERM-ignored+setsid           3.21s TimeoutExpired  child=gone grandchild=Ss
macOS    fix    fan_out last30days setsid     3.21s error/timed out
macOS    parent control-grandchild-in-group   1.01s TimeoutExpired
macOS    parent setsid-grandchild-holds-pipe  1.21s PermissionError                 <- N2 control
macOS    parent TERM-ignored+setsid           6.06s TimeoutExpired                  <- N1 control
macOS    parent fan_out last30days setsid     1.21s error/request failed            <- N2 control
Linux    fix    control / setsid / TERM-ign   1.01s / 3.23s / 3.21s, fan_out 3.22s error/timed out
Linux    parent control / setsid / TERM-ign   1.01s / 6.03s / 6.04s, fan_out 6.03s error/timed out   <- N1 control
```

Linux: `docker run --rm --network none python:3.14-slim-bookworm` (3.14.7), module mounted `:ro`, process state from
`/proc/<pid>/stat` (the image has no `ps`).

### R2 — Ctrl-C, real CLI (`r3/ctrlc_probe.py`)

`python -m dotfiles_setup.research_fanout topic --sources <s> --timeout 8` was launched in its own session; SIGINT was
sent with `killpg`, as a TTY does. `last30days` is a real script that spawns an in-group `sleep 4101`; `ctx7` is a real
shell script that spawns `sleep 4102`.

```
fix    last30days           SIGINT->exit 0.07s rc=130  l30=gone l30g=gone
fix    last30days,context7  SIGINT->exit 0.05s rc=130  l30/l30g/ctx/ctxg all gone
parent last30days           SIGINT->exit 7.63s rc=-2   stderr ends KeyboardInterrupt
parent last30days,context7  SIGINT->exit 7.61s rc=-2
fix    SIGTERM-ignoring last30days       0.26s rc=130  all gone          (r2b)
CC-b mutant (poll removed), same arm     7.86s rc=130                    (r2c, m.__file__ verified)
fix    exa stalled over a real socket    7.51s rc=130 (HTTP is not a child group; unchanged from parent 7.50s)
```

### R3 — HTTP over a real `127.0.0.1` socket (`r3/http_probe3.py`; the server drains the request, then `SHUT_WR`)

```
                      budget  fix                              parent
exa fast              1.0     0.02s ok (1)                     0.01s ok (1)
exa stall             1.0     1.00s timed out                  1.00s timed out
exa drip 1B/0.2s CL   1.0     1.01s timed out                  13.66s timed out
exa drip chunked      1.0     1.00s timed out                  13.86s timed out
fc  fast/stall        1.0     0.00s ok / 1.00s timed out       same
fc  drip CL/chunked   1.0     1.00s / 1.01s timed out          13.66s / 13.88s
exa truncated-CL      2.0     incomplete response              ok (1)   <- short body silently accepted
fc  truncated-CL      2.0     incomplete response              ok (1)
exa truncated-chunked 2.0     request failed                   request failed
exa HTTP 500 drip     1.0     1.01s timed out                  13.65s timed out
```

R3b is the CLI (`python -m`, urlopen redirected by a `sitecustomize` on `PYTHONPATH`, `--sources
exa,firecrawl-developer --timeout 1`, 1-byte drip). The fix gave rc=1 in 1.10 s wall with two `[timed out]` rows; the
parent took 13.83 s.

### R4 — context7 canary, LIVE `ctx7` 0.5.12 (`r3/n4_probe.py`) — see the N4 row

### R5 — mutation sweep (`r3/mutate3.py`, 21 rows; `count(old)==1` asserted; real HOME + empty HOME agree on every row)

```
M0 CONTROL incomplete reason string        RED   test_default_http_rejects_short_content_length
N1a unbounded drain after SIGKILL          RED   bounds_drain_when_detached..., tolerates_killpg... (32 s run)
N1b pipe close removed                     GREEN (bound still holds via kill+wait; not load-bearing)
N1c final kill+wait (reap) removed         GREEN (L2)
N2a PermissionError not suppressed         RED
CC-a cancel call removed                   RED   test_main_ctrl_c_terminates_real_child_and_returns_130
CC-b cancel-event poll removed             GREEN (L2; real arm 7.86 s vs 0.26 s)
CC-c main re-raises Ctrl-C                 RED   (session aborted after 19 passed)
CC-d cancel event never cleared            GREEN (L2; one-shot CLI, no later fan-out)
C2a caller waits for the whole body        RED   x2 (exa, firecrawl-developer)
C2b firecrawl branch bare read             RED
N3a short-body check removed               RED
N4a canary reuses repo library             RED
N5a firecrawl header validation bypass     RED   x2
N5b min term length removed                RED
N5c ctx7 library error bare                RED
N5d ctx7 docs error bare                   RED
N6a newline collapse removed               RED
N6b CR normalisation removed               GREEN (L2)
F6a all-terms -> any-term                  RED   x2
F6b empty-terms guard removed              GREEN (L2)
```

### R6 — N6, real child stderr (`r3/n6_l30.py`) — see the N6 row

### R7 — F6, live `jdx/mise` releases (`r3/f6_probe.py`) — see the F6 row

```
query               fix     parent
'is python fixed'   33/100  98/100    (independent recount of python AND fixed: 33)
'tracked configs'    7/100  29/100
'fixed'             98/100  98/100
'python'            33/100  33/100
'wqkzvx fixed'       0/100  98/100
'zqwvkx'             0/100   0/100    (fresh known-absent control)
'is it the'          0/100   0/100    (no retained terms)
```

### R8 — TE+CL framing (`r3/tecl.py`) and live framing headers — see L1

### R9 — SIGTERM to the CLI group (`r3/sig_probe.py`) — see Q-SCOPE

A post-run census (`ps -axo pid=,command=` for `sleep 410[12]` / `time.sleep(6|30|40)`) returned rc=1, meaning no
survivors. Control: the same `ps` matched my own command line containing the literal (count 2).

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — live `gh api 'repos/jdx/mise/releases?per_page=100'` replayed through the
  all-terms release filter (R7).
- [python/cpython](https://github.com/python/cpython) — installed `http/client.py` / `urllib/error.py` semantics
  (`read(amt)` on a CL body, chunked-ignores-CL, `HTTPError` hdrs/fp), read locally, not fetched.

