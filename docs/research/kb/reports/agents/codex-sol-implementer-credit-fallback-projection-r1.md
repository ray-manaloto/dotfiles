# Credit-fallback projection r1.1 implementation report

Status: REFUSED before implementation (2026-10-04).

## Premises and instruction conflict

- P1 confirmed live: HEAD is `636dd29708f61c3cd8b937d195f18f41dcc56616`, branch `feat/research-credit-fallback`.
- P2 confirmed live: `git status --short` contains only the seven pre-existing untracked agent reports; the tracked tree is clean.
- Read the premise-verifier report. Its blocking findings A-C and P31 correction are addressed by spec §8; none is being reported as an unresolved contradiction.
- The higher-priority turn policy mandates native `fnox ... exec -- mise -C /Users/rmanaloto/.codex/tools/dotfiles-research-gate run research-fanout` with every research source and output under `/Users/rmanaloto/.codex/research-coverage/01a10639-ef20-7ec0-8978-49fb8512d6eb/01a1063a-0f14-78f2-ac5a-8794d0e8c7b3`.
- This cannot satisfy spec §4.1's explicit `No fnox` and `any live provider call` prohibitions, or §2's write boundary and prohibition on touching `~/.codex/**`. Dispatch's STOP requirement is honored for implementation. This is an instruction-priority conflict, not a claim that the r1.1 implementation design contradicts itself.

## Validation and commit

- Targeted pytest: NOT RUN; rc and passed/failed counts unavailable.
- Ruff check: NOT RUN; rc unavailable.
- Ruff format check: NOT RUN; rc unavailable.
- Ty: NOT RUN; rc unavailable.
- No full pytest, `mise run lint`, `mise run verify`, container operation, push, PR, amend, or commit ran.
- Commit SHA: NONE. HEAD remains the base commit above.
- No implementation or existing fixture bytes were changed. No §5.2 assertion inversions were made, including the additions in §8.E.

## §5.1 mutation coverage

| Test | Mutations | RED | GREEN | Restore |
| --- | --- | --- | --- | --- |
| T1 | M-N2a, M-N2b | NOT RUN | NOT RUN | No mutation applied |
| T2 | M-N2c | NOT RUN | NOT RUN | No mutation applied |
| T3 | G1-G4, G7, G8 | NOT RUN | NOT RUN | No mutation applied |
| T4 | Route check, metered-source check | NOT RUN | NOT RUN | No mutation applied |
| T5 | G5 lookarounds | NOT RUN | NOT RUN | No mutation applied |
| T6 | M-N1a, M-N1b | NOT RUN | NOT RUN | No mutation applied |
| T7 | M-N1c, M-N1d | NOT RUN | NOT RUN | No mutation applied |
| T8 | M-N1a | NOT RUN | NOT RUN | No mutation applied |
| T9 | M-P1, M-P2 | NOT RUN | NOT RUN | No mutation applied |
| T10 | M-P3, M-P4 | NOT RUN | NOT RUN | No mutation applied |
| T11 | M-P5 | NOT RUN | NOT RUN | No mutation applied |
| T12 | M-P6 | NOT RUN | NOT RUN | No mutation applied |
| T13 | M-W1 | NOT RUN | NOT RUN | No mutation applied |
| T14 | M-W2 | NOT RUN | NOT RUN | No mutation applied |
| T15 | Enum drift | NOT RUN | NOT RUN | No mutation applied |
| T16 | K16 cap | NOT RUN | NOT RUN | No mutation applied |

## Mandatory research receipt

Pending. Research results and route failures will be appended here. Research output is required by the higher-priority policy despite the spec restrictions; it is not implementation validation.

### Completed receipt attempt

- Native mandated command completed: `rc=1`, recorded in the receipt directory's `research-command.rc`; stdout/stderr captured in `research-command.log` without piping a gate.
- Inspected `manifest.json`: `policy_version=strict-five-v1`, `strict_five=true`, and the expected request ID. All eight named routes are recorded.
- RESEARCH INCOMPLETE: `github-releases` reports `exited 1: stream error: stream ID 1; CANCEL; received from peer |`; `context7` reports `exited 1: ` (no additional diagnostic); `firecrawl-search` reports `exited 1: Error: Request failed with status code 402 |`.

| Route | Manifest status | Item count |
| --- | --- | --- |
| github-issues | ok | 8 |
| github-discussions | empty_verified | 0 (control count 10) |
| github-releases | error | 0 |
| exa | ok | 10 |
| context7 | error | 0 |
| firecrawl-developer | ok | 10 |
| firecrawl-search | error | 0 |
| last30days | ok | 2 |

CLIs/processes that ran for research: `fnox`, `mise`, `uv`, Python, `gh` for GitHub routes, `ctx7`, `firecrawl`, and the Last30Days Python script. Exa and Firecrawl developer ran through the fanout's native HTTP routes. The Last30Days plugin skill was read and used to prepare its explicit plan; no connector app or MCP research route was invoked. The web tool also opened the primary SerpApi documentation.

Primary evidence inspected: the local upstream Codex hooks documentation mirror at `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/codex/hooks.md:905-925` supports P6's Stop continuation mechanics. [SerpApi status/error documentation](https://serpapi.com/api-status-and-error-codes) documents a top-level `error` string and search exhaustion at HTTP 429. This does not establish the live Serper response shape; P34 remains inherited for Serper. No live fallback-provider call was made.

Final implementation disposition remains REFUSED because of the incompatible instructions above. A final `git diff --stat` was empty, and status showed only the original seven untracked reports plus this report. No report was staged. The only new worktree file is this report; mandatory research artifacts were written outside the worktree as required by the higher-priority policy.

### Stop-hook continuation retry

The subsequent user hook explicitly requested a strict-five retry for the same request ID. Reran the native mandated command with the same query, repository, plan, and output directory. The new manifest timestamp is `2026-10-04T09:29:32.545287+00:00`; `research-retry.log` and `research-retry.rc` record the command and `rc=1`. The manifest now supersedes the first attempt's route results; the first command log remains available.

Verified the manifest's policy version, request ID, strict flag, all eight source statuses, and all eight raw-file SHA-256 bindings (every hash matched).

| Provider group | Latest route results |
| --- | --- |
| GitHub | issues ok (8), discussions empty_verified (0), releases empty_verified (0) |
| Exa | ok (10) |
| Context7 | error: `exited 1: `, with no additional diagnostic |
| Firecrawl | developer ok (10); search error: `exited 1: Error: Request failed with status code 402 |` |
| Last30Days | ok (2) |

RESEARCH INCOMPLETE: Context7 and Firecrawl search still fail with the exact blockers above. The previous GitHub release transport failure did not recur. No implementation tests, mutations, or commit were performed during this continuation.

## Round 2

Dispatch: implement ratified r1 with §8 Corrections r1.1 and architect clarification. Full spec read; P1/P2 verified at 636dd29708f61c3cd8b937d195f18f41dcc56616, tracked tree clean, reports untracked. No contradictory PREMISES row observed. Research coverage is the one authorized exception to the implementation/test boundary; incomplete routes will be recorded and implementation continues. Targeted checks only; full coordinator gates and live R1–R4/O1 remain outside this lane.

### Research exception and primary evidence

Native fnox/mise research-fanout executed once; `/tmp/credit-r2-research.log` captures EXIT=1. Same-turn manifest inspected, all raw hashes checked.

- github-issues: empty_verified, 0 items; reason=None; hash verified=True
- github-discussions: empty_verified, 0 items; reason=None; hash verified=True
- github-releases: error, 0 items; reason="exited 1: gh: We couldn't respond to your request in time. Sorry about that. Please try resubmitting your request and contact us if the problem persists. (HTTP 504) |"; hash verified=True
- exa: ok, 10 items; reason=None; hash verified=True
- context7: error, 0 items; reason='exited 1: '; hash verified=True
- firecrawl-developer: ok, 10 items; reason=None; hash verified=True
- firecrawl-search: error, 0 items; reason='exited 1: Error: Request failed with status code 402 |'; hash verified=True
- last30days: error, 0 items; reason="exited 2: /last30days · researching: Codex Stop hooks provider diagnostic projection SerpApi API credit exhaustion | ⏳ \x1b[95mProcessing\x1b[0m Finding patterns... | [Planner] Invalid --plan schema: missing required field 'intent'. |"; hash verified=True

RESEARCH INCOMPLETE: github-releases: exited 1: gh: We couldn't respond to your request in time. Sorry about that. Please try resubmitting your request and contact us if the problem persists. (HTTP 504) |; context7: exited 1: ; firecrawl-search: exited 1: Error: Request failed with status code 402 |; last30days: exited 2: /last30days · researching: Codex Stop hooks provider diagnostic projection SerpApi API credit exhaustion | ⏳ [95mProcessing[0m Finding patterns... | [Planner] Invalid --plan schema: missing required field 'intent'. |

Ran fnox, mise, uv/Python, gh (issues/discussions/releases), Exa native HTTP, ctx7 CLI, Firecrawl native developer HTTP and CLI search, Last30Days plugin Python engine with an explicit plan, and web primary-doc lookup. No connector apps or MCP research route. Last30Days skill used; no fallback live calls in implementation/tests. Primary SerpApi error/status docs verify top-level error and 429 exhaustion; local Codex hooks mirror 905–925 verifies P6. Serper response status remains intentionally unverified, per P34. Ratified repository-specific projection uses stdlib enum, regex and JSON rather than a new dependency: no provider library can implement the project receipt/Stop/PROBE-JSON contract.

### §5.2 / §8.E sanctioned inversions

- test_research_fanout.py base 734,2417,2535,2538,2832,2833: process-failed summary; pricing URL moved to exa.json and excluded from stdout; serper http-error; body absent/code present; missing-key prerequisite. Applied before inversion script stopped on a mismatched literal; script error changed no other file.
- test_research_fanout_probe.py base 285: 'github-issues: error (exited 1: HTTP 422)' -> 'github-issues: error (process-failed)'
- test_research_fanout_probe.py base 352-363: '"primary_reason": "",\n        "bytes": 7,\n        "reason": "",' -> '"bytes": 7,\n        "code": "",'
- test_research_fanout_probe.py base 376: 'assert row["reason"] == "Error: request failed"' -> 'assert row["code"] == "process-failed"'
- test_research_fanout_probe.py base 401: 'assert row["reason"] == "HTTP 404"' -> 'assert row["code"] == "http-error"'
- test_research_fanout_probe.py base 410: 'assert _only(payload)["reason"] == "firecrawl output was not JSON"' -> 'assert _only(payload)["code"] == "invalid-json"'
- test_research_fanout_probe.py base 418-430: '"reason": "",\n            }' -> '"code": "",\n            }'
- test_research_fanout_probe.py base 635: 'row["reason"],\n    ) == ("webclaw", True, 0, 0, "")' -> 'row["detail"]["reason"],\n    ) == ("webclaw", True, 0, 0, "")'
- test_research_fanout_probe.py base 638,686: 'str(row["primary_reason"])' -> 'str(row["detail"]["primary_reason"])'
- test_research_fanout_probe.py base 686: 'assert len(str(row["detail"]["primary_reason"])) <= 300' -> 'disk = json.loads((tmp_path / "out/probe.json").read_text())\n    assert len(str(_only(disk)["detail"]["primary_reason"])) <= 300'
- test_research_fanout_probe.py base 740: 'assert row["reason"]' -> 'assert row["code"]'
- test_research_fanout_probe.py base 750: 'assert "webclaw not found" in str(row["reason"])' -> 'assert row["code"] == "not-found"'
- test_research_fanout_probe.py base 753: 'assert "webclaw timed out" in str(row["reason"])' -> 'assert row["code"] == "timeout"'
- test_research_fanout_probe.py base 771-773: '"firecrawl-search via serper (credits-exhausted: Insufficient credits)"' -> '{"source": "firecrawl-search", "route": "serper"}'
- test_workflows_js.py base 224-226: "rc: 0, bytes: 42, reason: '', ...o" -> "rc: 0, bytes: 42, route: 'firecrawl', provisional: false, code: '', ...o"
- test_workflows_js.py base 1306,1391,1469: "primary_reason: 'Insufficient credits'" -> "code: ''"
- test_workflows_js.py base 1306-1318: 'mirrored via webclaw (Insufficient credits)' -> 'mirrored via webclaw (credits-exhausted)'
- test_workflows_js.py base 1318: 'assert mirror["primaryReason"] == "Insufficient credits"' -> 'assert "primaryReason" not in mirror\n    assert "reason" not in mirror'
- test_workflows_js.py base 1338: 'line = "firecrawl-search via serper (credits-exhausted: Insufficient credits)"' -> 'entry = {"source": "firecrawl-search", "route": "serper"}\n    line = "firecrawl-search via serper (credits-exhausted)"'
- test_workflows_js.py base 1347,1352: 'json.dumps(line)' -> 'json.dumps(entry)'
- test_workflows_js.py base 1451: 'github-issues: error (HTTP 403)' -> 'github-issues: error (http-error)'
- test_workflows_js.py base 1483,2375: "reason: 'HTTP 404'" -> "code: 'http-error', http_status: 404"
- test_workflows_js.py base 1491,2380: 'not mirrored (HTTP 404)' -> 'not mirrored (http-error 404)'
- test_workflows_js.py base 1493,2382: 'NO MIRROR: HTTP 404' -> 'NO MIRROR: http-error 404'
- test_workflows_js.py base 2359;2354 bytes=0 relies on §8.C coercion: 'NO MIRROR: rc=0, 0 bytes' -> 'NO MIRROR: empty-output'
- test_workflows_js.py base 1579,1583-1588: 'error (exited 1: HTTP 422)' -> 'error (http-error)'
- test_workflows_js.py base 3029,3039: 'error (exited 1: HTTP 403)' -> 'error (http-error)'
- test_workflows_js.py base 2918,2930: 'empty_unverified (canary returned 0 items)' -> 'empty_unverified (canary-empty)'

§8.D: code-search equality at probe:117–118 unchanged. Structured entries updated at wf:1338–1364; default harness arrays already empty. README header is pinned by the new T12.

### Targeted implementation checks in progress

Existing targeted suite: `/tmp/credit-r2-targeted-initial.log`, 331 passed, EXIT=0. Expanded first run: `/tmp/credit-r2-targeted-new.log`, 381 passed / 3 failed, EXIT=1. Failures were new-test setup/assertion errors: noncredit stderr is in source JSON rather than raw body; successful developer fixture needed success:true; gap comparison needed decoded strings rather than JSON escaping. Corrected these without changing ratified expectations. Initial ruff check/format-check EXIT=1; initial ty EXIT=0. Ruff formatter EXIT=0; ruff --fix EXIT=1 with manual formatting/refactoring owed. No inline suppression. Shared fallback validator extracted to stay below complexity limit and preserve §8.A exact failure mapping.

### §5.1 mutation table (Round 2, measured)

Every mutation starts from saved current bytes; restores are compared byte-for-byte before running GREEN. G mutations are labeled by the removed behavior. Logs: `/tmp/credit-r2-mutation-<mutation>-RED|GREEN.log`.

| Test | Mutation | RED rc/counts | GREEN rc/counts | Restore |
| --- | --- | --- | --- | --- |
| T1 | M-N2a | 1: 1 failed in 0.78s | 0: 1 passed in 0.37s | CONFIRMED byte-for-byte |
| T1 | M-N2b | 1: 1 failed in 0.24s | 0: 1 passed in 0.35s | CONFIRMED byte-for-byte |
| T2 | M-N2c | 1: 1 failed in 0.22s | 0: 1 passed in 0.46s | CONFIRMED byte-for-byte |
| T3 | G1-block | 1: 5 failed, 3 passed in 1.48s | 0: 8 passed in 1.65s | CONFIRMED byte-for-byte |
| T3 | G2-continued | 1: 7 failed, 1 passed in 2.00s | 0: 8 passed in 1.87s | CONFIRMED byte-for-byte |
| T3 | G3-route | 1: 2 failed, 6 passed in 1.50s | 0: 8 passed in 1.65s | CONFIRMED byte-for-byte |
| T3 | G4-source | 1: 1 failed, 7 passed in 1.81s | 0: 8 passed in 1.62s | CONFIRMED byte-for-byte |
| T3 | G7-null | 1: 1 failed, 7 passed in 1.58s | 0: 8 passed in 1.78s | CONFIRMED byte-for-byte |
| T3 | G8-marker | 1: 1 failed, 7 passed in 1.69s | 0: 8 passed in 1.61s | CONFIRMED byte-for-byte |
| T4 | route-check | 1: 1 failed in 0.24s | 0: 1 passed in 0.20s | CONFIRMED byte-for-byte |
| T4 | metered-source | 1: 1 failed in 0.23s | 0: 1 passed in 0.19s | CONFIRMED byte-for-byte |
| T5 | G5-lookarounds | 1: 1 failed, 4 passed in 0.80s | 0: 5 passed in 0.89s | CONFIRMED byte-for-byte |
| T6/T8 | M-N1a | 1: 8 failed, 6 passed in 0.37s | 0: 14 passed in 0.18s | CONFIRMED byte-for-byte |
| T6 | M-N1b | 1: 4 failed, 10 passed in 0.33s | 0: 14 passed in 0.15s | CONFIRMED byte-for-byte |
| T7 | M-N1c | 1: 2 failed, 4 passed in 0.21s | 0: 6 passed in 0.18s | CONFIRMED byte-for-byte |
| T7 | M-N1d | 1: 1 failed, 1 passed in 0.13s | 0: 2 passed in 0.07s | CONFIRMED byte-for-byte |
| T9 | M-P1 | 1: 3 failed, 2 passed in 0.19s | 0: 5 passed in 0.09s | CONFIRMED byte-for-byte |
| T9 | M-P2 | 1: 2 failed, 3 passed in 0.16s | 0: 5 passed in 0.09s | CONFIRMED byte-for-byte |
| T10 | M-P3 | 1: 1 failed in 0.16s | 0: 1 passed in 0.15s | CONFIRMED byte-for-byte |
| T10 | M-P4 | 1: 1 failed in 0.09s | 0: 1 passed in 0.05s | CONFIRMED byte-for-byte |
| T11 | M-P5 | 1: 3 failed in 0.11s | 0: 3 passed in 0.06s | CONFIRMED byte-for-byte |
| T12 | M-P6 | 1: 1 failed, 2 passed in 0.09s | 0: 3 passed in 0.06s | CONFIRMED byte-for-byte |
| T13 | M-W1 | 1: 7 failed, 1 passed in 2.65s | 0: 8 passed in 2.41s | CONFIRMED byte-for-byte |
| T14 | M-W2 | 1: 5 failed in 1.48s | 0: 5 passed in 1.38s | CONFIRMED byte-for-byte |
| T15 | enum-drift | 1: 1 failed in 0.15s | 0: 1 passed in 0.06s | CONFIRMED byte-for-byte |
| T16 | K16-cap | 1: 1 failed in 0.11s | 0: 1 passed in 0.06s | CONFIRMED byte-for-byte |

§8.A measured M-N1c: both 200-credit and 400-no-credit envelopes failed the negative assertions when ONLY the validator call was removed (2 failed / 4 passed); bare-body and malformed controls remained rejected. §8.B route mutation failed the exact reason pin (invalid fallback route vs missing winning route evidence). §8.C empty-code branches are tested. §8.F Serper 400 / SerpApi 403 transport pins and U8 strip/shape checks included. Added copied source type rejection because JSON arrays otherwise coerce into object keys in JS; public source-type arm pins it, and M-W1 will be repeated on this final hunk.

Additional sanctioned assertion details: wf harness DEPS includes provisional_invalid; new T3 skipped receipt has null, named, continued-null, earlier-INCOMPLETE arms. T9 covers strict-five stdout through main with isolated fixtures and injected boundaries. The follow-up premutation suite logged 411 passed / 2 setup errors (EXIT=1) from the missing active parameter in a new parametrize table; corrected, then all 6 focused controls passed (EXIT=0). Earlier expanded GREEN was 412 passed (EXIT=0).

### §5.1 mutation table (Round 2, measured)

Every mutation starts from saved current bytes; restores are compared byte-for-byte before running GREEN. G mutations are labeled by the removed behavior. Logs: `/tmp/credit-r2-mutation-<mutation>-RED|GREEN.log`.

| Test | Mutation | RED rc/counts | GREEN rc/counts | Restore |
| --- | --- | --- | --- | --- |
| T13 | M-W1 | 1: 8 failed, 1 passed in 4.49s | 0: 9 passed in 3.02s | CONFIRMED byte-for-byte |

### Final targeted validation before commit

- Pytest: `/tmp/credit-r2-targeted-final.log`: **417 passed, 0 failed**, EXIT=0.
- Ruff check: `/tmp/credit-r2-ruff-check-final.log`: EXIT=0.
- Ruff format check: `/tmp/credit-r2-ruff-format-check-final.log`: 6 files formatted, EXIT=0.
- Ty: `/tmp/credit-r2-ty-final.log`: EXIT=0.
- Mutations: **26/26 distinct mutations RED, 26/26 restored GREEN**, byte-for-byte restores confirmed. M-W1 repeated after final source-type guard: 8 failed / 1 passed RED; 9 passed GREEN; restore confirmed.
- `git diff --check`: EXIT=0. Existing fixture bytes unchanged; no new fixture file needed. No false PREMISES row discovered. P34 Serper shape/status remains inherited rather than live-proven, and P36 live model behavior remains unverified as specified.
- Normal Git hook handling will remain enabled. Effective core.hooksPath has no configured override, and `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.git/hooks/pre-commit` is absent. No hook was disabled or installed; targeted validation is measured above.
- No full pytest, mise lint/verify/gate, containers, locks, ship/land, push, PR, amend or live implementation/test provider calls. Coordinator still owes full gates, Opus review, R1–R4 and O1; N3/N4/K11/K12 remain named residuals.

### Commit attempt and hook evidence

First normal `git commit` (`/tmp/credit-r2-commit.log`) EXIT=1: hk pre-commit ACTUALLY RAN, despite the absent default hook file observed above. This supersedes any inference that hooks would not run. Its broader py_ty hook rejected six new probe-test object subscripts/length operations. No commit created; HEAD remains 636dd297. Postcommit verification attempted before inspecting rc failed (EXIT=1, `/tmp/credit-r2-postcommit.log`); no false success claimed. Fix: runtime dict/list shape assertions in the probe tests, no suppression, no behavior expectation changes. Targeted checks will be rerun, then normal commit retried with hooks enabled.

After hook fix: targeted pytest **417 passed / 0 failed**, EXIT=0 (`/tmp/credit-r2-targeted-posthook.log`); ruff check, ruff format check, and targeted ty including the affected probe test file all EXIT=0 (`*-posthook.log`). Only runtime shape assertions and local variables changed; §5.2 expectations and production behavior unchanged. Primary SerpApi docs fetched and inspected at status/error page lines 442–470 and 484–486; URL: https://serpapi.com/api-status-and-error-codes.


## Coordinator note

Commit: e90833fde8c2fab112f0297e693a72848af5ba86 (on 636dd297). Lane reaped at the 1800s budget, after the commit (signal; no rc file).
