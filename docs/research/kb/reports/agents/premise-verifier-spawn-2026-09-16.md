# premise-verifier — spec-sdlc-spawn-reconciliation (2026-09-16)

> PERSISTED VERBATIM at receipt (agent-report-persistence.md rule 1). Agent: `fable-orchestrator:premise-verifier` (Claude, read-only), named `premise-verifier-spawn`, session dotfiles-20260916.000. Brief: verify the PREMISES block of the scratchpad spec `spec-sdlc-spawn-reconciliation.md` (6c P0 — settlement reconciles the codex SDLC team's spawn self-report against descendant rollout files) and hunt unstated premises. Recovered from the subagent transcript because the mailbox delivery truncated the report.

Verification complete. Report follows.

---

# Premise verification — `spec-sdlc-spawn-reconciliation.md`

Repo at `bce4ffd`, branch `fix/sdlc-team-settlement-verifies-spawn`, tree clean. Graphify reported `stale` (built `63a76ec0`, 14 commits behind HEAD), so every read fell back to source per `graphify-first.md`.

**Headline: no cited row is refuted, but two unstated premises are refuted by live data, and either one breaks the change on real runs.**

## 1. Per-row verdicts (spec order, §7)

| # | Row | Verdict | Evidence / correction |
|---|---|---|---|
| 1 | `SdlcTeamSettlement` 7 fields | **CONFIRMED, line fix** | `sdlc_team.py:103-112`, not `:103-111` — `errors` is at `:112` |
| 2 | `_SupervisorPayload` 11 fields | **CONFIRMED** | `sdlc_team.py:115-128`, exact |
| 3 | `_write_lane_receipts` hard-codes OBSERVED unavailable | **CONFIRMED, line fix** | `:483-524`; the OBSERVED stub is `:497-501`, not `:496-501` |
| 4 | `_supervise` status from rc alone, log `"wb"` | **CONFIRMED, line fix** | function is `:527-582` not `:527-583`; status `:549-553` and log `:537` both exact |
| 5 | argv has no `--ephemeral`, no `--json` | **CONFIRMED** | `sdlc_team.py:371-383`, exact; removal rationale comment at `:365-370` |
| 6 | `build_prompt` carries the retry clause | **CONFIRMED** | `:238-240` retry clause, `:243-244` the spawned-list instruction |
| 7 | `AgentSource` / `AgentNode` / `CollectorOutcome` | **CONFIRMED, line fix** | `lane_result.py:41-56` and `:70-76` (spec said `:41-57, 70-75`) |
| 8 | `collect_self_report` shape | **CONFIRMED** | `:125-172` and regexes `:87-97`, both exact |
| 9 | `merge_sources` message forms | **CONFIRMED** | `:425-478`; unavailable at `:434`, missing-from at `:462-463` |
| 10 | `collect_observed` pinned to agentsview 0.42.0, CLI-only | **CONFIRMED** | path `:80-84`, function `:250-299`, sole call site `:630` |
| 11 | HOOK always unavailable for codex runs | **CONFIRMED** | `tests/test_lane_result.py:215` is that test, assertion at `:224`. DATA arm run live: `hook_events_path` resolves to `.agent/lane-results/<run>.hooks.jsonl`, absent for run `2c97f4bc` |
| 12 | codex banner layout | **CONFIRMED** | `.agent/sdlc-runs/4e6f6a4d.../codex.log` lines 1, 2, 10, 11, 12 exactly as stated |
| 13 | child rollout first-line shape | **CONFIRMED, addition** | `~/.codex/sessions/2026/09/16/rollout-...-01a0a8db-de4d-...jsonl:1`. Parent arm confirmed: `parent_thread_id` null, `source: "exec"`, no `agent_role`. **Addition:** the payload also carries `session_id` and `forked_from_id`, and `session_id` holds the **parent's** uuid on a child record — keying on it would silently mis-identify every child |
| 14 | child has a second `session_meta` at ordinal 1 | **CONFIRMED, provenance upgraded** | Cited from a codex.log transcript scrape; I read the three child files directly, all three have `session_meta` at ordinal 1 |
| 15 | real self-report shapes | **CONFIRMED** | role-first `4e6f6a4d.../output.md:125-131`; path-first `2c97f4bc.../output.md:134-140`. Both exact |
| 16 | `CODEX_HOME` defaults to `~/.codex`, roots sessions | **CONFIRMED** | `config-file__environment-variables.md:17` and `config-file__config-advanced.md:71`, both exact |
| 17 | filename local vs timestamp UTC | **CONFIRMED, key fix** | Same file, line 1. The key is `timestamp`, not `"ts"` — `"2026-09-16T06:16:17.947Z"` against filename `01-16-17` |
| 18 | supervisor test expects COMPLETED for a zero-child claim | **CONFIRMED** | `tests/test_sdlc_team.py:299-347`, exact. Its fake `Popen` is `lambda *_a, **_kw: child` and discards the stdout handle, so §4's banner-writing constraint is a real required change |
| 19 | committed-schema parity test; no mise task regenerates it | **CONFIRMED, line fix** | parametrize `:454-461`, function `:462-470` (spec said `:450-470`). `mise.toml:280` is the only `sdlc` task |
| 20-24 | E rows (provenance of the 5 emitted values) | **CONFIRMED** | Each source read directly; see §2 for the one that is worse than the row admits |
| 25 | A — banner format stable, fails closed if not | **ASSUMED, reasonable** | Observed on the pinned 0.154.0; no doc describes the exec banner. Fail direction is safe |

## 2. MISSING premises

**M1 — `collect_self_report` does not parse the spawned list on a real run. This is the one that breaks the change.** The parser takes the **first** line matching `_SECTION_LINE` anywhere in the document (`lane_result.py:138-141`). In run `4e6f6a4d`, `output.md:9` is prose quoting the literal string `Specialists spawned:` inside a file reference, so the parser anchors there and never reaches the real list at `:125-131`. Measured live through the real function:

| Run | Parsed claim | Observed children |
|---|---|---|
| `4e6f6a4d` | 1 item, `P1 — `4d91064`'s workflow policy loses setup/run ordering.` | 3, correct roster names |
| `2c97f4bc` | 4 path-first items | 0 |

The `2c97f4bc` motivating case in §1 is fully confirmed: claimed four, spawned zero. But `4e6f6a4d` would settle **failed** under the new rule despite spawning correctly. The spec's §5 positive arm uses a synthetic output with no preceding prose, so it passes while the real positive case fails. That is the fixture-rigging shape in `probes-need-a-control-arm.md` rule 8. Either anchor on the **last** matching section, require a list within N lines, or state explicitly that a false FAILED is acceptable.

**M2 — a test asserts on the exact prompt clause the spec deletes.** `tests/test_sdlc_team.py:111` asserts `"retry once without conversation history" in prompt`. §4 says prompt tests assert "elsewhere" and to run them; it never says one binds the deleted text. `:105-115` is the full prompt-assertion block and must be updated in the same change.

**M3 — one rollout file is zero bytes, so the collector's error text is never empty.** Of 3,236 files (the spec's count is exact), `2026/04/16/rollout-2026-04-16T16-14-05-019d9824-...jsonl` is 0 bytes and fails to parse. §4 requires parse failures to be counted in the error text. The spec never says error text must not imply `available=False`; if the implementer couples them, every run on this host fails closed permanently.

**M4 — `agent_role` is absent on two-thirds of subagent children.** Across the corpus, 326 records have `parent_thread_id` set and `thread_source == "subagent"` but **no** `agent_role`; only 169 carry one. `thread_source` also appears once as `"sub-agent"` with a hyphen. §3 defines node name as `payload.agent_role` with no fallback, so such a child yields an empty name and a spurious "observed child was not claimed" error.

**M5 — `merge_sources` keys on name, so path-first self-reports never merge.** OBSERVED nodes will be named by `agent_role` while path-first SELF_REPORT items are named by path. The receipt will list both as separate agents with a name-mismatch disagreement even when reconciliation succeeds. §4 only immunises the fail-closed rule against the HOOK disagreement.

**M6 — the identity set is unbounded over model prose.** §3 admits every backticked token in the role text. Real role text is `` `sdlc-config-specialist`; initial spawn failed with `no thread with id` ``, so tokens like `no thread with id` enter the set. Harmless today, but nothing bounds it.

**M7 — `_SupervisorPayload` crosses a process boundary as base64 argv** (`sdlc_team.py:284`, `:289-291`). Adding `sessions_root` grows that argument. Not a size risk, but the round-trip is real and the spec does not mention it. `os` is already imported at `:11`.

Three checks the spec asked about came back clean:

- **(c) Old settlements decode.** Seven-field bytes decode into the current struct; control arm, a missing required `run_id` raises `ValidationError`, so the decoder discriminates. The 20 real `settlement.json` files read by `read_status` (`sdlc_team.py:467`) stay readable. The two fixtures at `:207-231` and `:283-297` construct the struct in Python rather than embedding old JSON, so they re-encode with the new defaults.
- **(d) Indent is derivable, with a control arm.** `json.dumps(schema, indent=2) + "\n"` reproduces the committed file byte-for-byte; `indent=4` does not. The parity test compares parsed objects, so indent is not what binds it.
- **(e) No gate greps the changed files.** Zero hits for `sdlc_team` or `lane_result` in `python/verification/suites.toml` or `hk.pkl`; the lone `ephemeral` hit at `hk.pkl:671` is an unrelated comment. `md-budget` is rc=0 and the eager budget is 200 lines / 24,000 bytes, against 77 lines / 3,905 bytes for `.claude/rules/codex-sdlc-team.md`.

## 3. Provenance flags

- **Row 14** cited `codex.log:10065-10066`, a transcript scrape of the model's own tool output, not the file. The fact is true. I replaced it with direct reads of all three child files.
- **Row 11** is labelled `P` and pairs a test name with a "DATA match" assertion. Both halves now have direct evidence, so it reads as CONFIRMED rather than pattern-matched.
- No row cites a handoff or session report.

Files read live outside the repo: `/Users/rmanaloto/.codex/sessions/2026/09/16/rollout-2026-09-16T01-14-43-01a0a8da-6d39-74e3-a8fc-fe66f5505378.jsonl`, `...01-16-17-01a0a8db-de4d-7c93-a96f-8d001939aecd.jsonl`, `...01-16-24-01a0a8db-fbb1-7db3-8384-978b2e8cd6a1.jsonl`, `...01-16-34-01a0a8dc-1ee0-7e10-912c-70a417e45218.jsonl`, and `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/codex/config-file__environment-variables.md`.

Findings were appended (never overwritten) to `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/findings.md` and `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/progress.md`. Nothing else was edited.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under change (sdlc_team.py, lane_result.py, tests).
- [openai/codex](https://github.com/openai/codex) — rollout record shape and `CODEX_HOME` semantics, read from the offline codex docs corpus, not fetched live.
