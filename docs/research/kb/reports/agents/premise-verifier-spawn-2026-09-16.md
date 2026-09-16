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

---

# Delta pass on spec v2 (same agent, SendMessage continuation, 2026-09-16 07:39Z)

> PERSISTED VERBATIM at receipt. Recovered from the subagent transcript because the mailbox delivery truncated the report again.

# Premise verification v2 — delta pass

Repo at `3e1119b`. `git diff --stat bce4ffd..HEAD` over `sdlc_team.py`, `lane_result.py`, both test files, `schemas/`, `hk.pkl`, `suites.toml` and `mise.toml` is **empty**, so every unchanged v1 verdict carries at `3e1119b` without re-reading.

## [v2] row verdicts

| [v2] item | Verdict | Evidence |
|---|---|---|
| §3 `collect_spawn_report` last-anchor | **CONFIRMED on real data** | Anchors found at `output.md:9` and `:125`; binding `:125` parses exactly `sdlc-python-specialist`, `sdlc-config-specialist`, `sdlc-documentation-specialist` and stops at the terminator |
| §3 `payload.session_id` ban | **CONFIRMED** | 449 of 495 children have `session_id == parent_thread_id`; the row's figure is exact |
| §3 node-name fallback chain | **REFUTED at the middle link** | See below |
| §3 roster grammar | **CONFIRMED** | 29 of 29 `name` fields in `.codex/agents/*.toml` match `^[a-z0-9][a-z0-9_-]{0,63}$`, including all six sdlc specialists |
| §3 receipt canonicalization (M5) | **CONFIRMED** | `merge_sources` keys on `name` at `lane_result.py:439` |
| §3/§4 skipped-file counting, `available=True` | **CONFIRMED** | Exactly 1 unparsable file, zero bytes |
| §4 `:111` prompt assertion | **CONFIRMED** | `tests/test_sdlc_team.py:111`; block is `:105-115` |
| §4 base64 payload note | **CONFIRMED** | `sdlc_team.py:286` encodes, `:291` decodes; `os` at `:11` |
| §4 old-settlement decode | **CONFIRMED** | Seven-field bytes decode; control arm, missing `run_id` raises |
| §5 arms 7-10 | **Sound**, one caveat | Arm 7 now has real backing. Arm 9 is the only realistic no-role case, not an edge |
| §7 rows 148-156, 172, 174 (line corrections) | **CONFIRMED** | All five corrections applied correctly; `_SECTION_LINE` is `:87-91`, `_AGENT_LINE` `:92-97` |
| §7 row 157 (`test_lane_result.py:61`) | **CONFIRMED** | `test_self_report_collects_the_first_selected_block_with_roles`, fixture anchors on `The dispatcher selected:` |
| §7 row 158 (prose at `output.md:9`) | **CONFIRMED verbatim** | Re-ran live: `available=True`, one item, name `P1 — `4d91064`'s workflow policy loses setup/run ordering.` |
| §7 row 163 (`session_id` addition), 164 (line 2), 169 (`timestamp` key) | **CONFIRMED** | Direct reads |
| §7 row 165 (corpus) | **CONFIRMED, all five figures exact** | 3,236 / 495 / 326 / 169 / 449, `subagent` for all 495 |
| §7 rows 166, 171, 173 | **CONFIRMED** | Zero-byte file path exact |

## The `sub-agent` discrepancy: neither of us read the wrong field

The single `thread_source == "sub-agent"` record has `parent_thread_id` null, so it is **not** one of the 495 children. Your count is correct as stated. My v1 line was under-qualified, not wrong-fielded. Non-child `thread_source` values are `None` (1,848), `user` (656), `subagent` (184), `automation` (43), `agent_created_thread` (8), `sub-agent` (1). The v2 row needs no change.

## New missing premises

**N1 — the fallback chain's middle link is dead, and the last link is unmatchable.** Of the 326 children with no top-level `agent_role`, **zero** carry `payload.source.subagent.thread_spawn.agent_role`. That link can never fire. Meanwhile 80 of the 326 **do** carry `agent_path`, and 244 of the 326 have `originator == "codex_exec"` — the same originator as our own sdlc children — so this is not a foreign-tool shape. Those 80 fall straight through to a uuid name that no claimed roster token can match, forcing `failed`. The spec assigns `agent_path` to `role` but never admits it as an identity, even though the path-first claimed shape carries exactly that path as its `name`. Recommend adding `agent_path` as the second identity before the uuid, or stating explicitly that an `agent_role`-less child is always a failure.

**N2 — `- None.` parses as a claimed item.** `_AGENT_LINE` matches it with name `None.`, which fails the roster grammar and yields `claimed item 'None.' names no roster specialist`. The fail direction is right but the message is misleading for a run that legitimately spawned nothing. Worth pinning in a test.

**N3 — `payload.source` type varies by record class.** It is a dict on all 495 children but the bare string `"exec"` on parent records, so an unguarded nested dig raises `AttributeError` (mine did on the first scan). Safe only because `parent_thread_id` filters parents first. Make that ordering explicit or type-guard the dig.

## Answers to the two direct questions

**Terminator: yes, cleanly.** `- No other specialists were spawned.` is not an `_AGENT_LINE` item, in both the bulleted (`2c97f4bc:140`) and bare (`4e6f6a4d:131`) forms, with and without the trailing period. Control arm: the real item shape on the same regex does match. The last-anchor parse therefore terminates correctly on both real files.

**Grammar: yes, all 29.** Every `name` in `.codex/agents/*.toml` is kebab-case under 64 characters and passes. Note the filenames carry a `codex-` prefix the `name` fields do not, which the grammar is indifferent to.

Findings appended (never overwritten) to `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/findings.md`. Nothing edited.


---

# Delta pass on spec v3 (same agent, 2026-09-16 07:44Z)

> PERSISTED VERBATIM at receipt (mailbox delivery was complete this time; transcript copy identical).

# Premise verification v3 — delta pass

Repo at `f7f019e`; `git diff` over `python/src`, `tests`, `schemas`, `hk.pkl`, `python/verification`, `mise.toml`, `.codex` against `3e1119b` is empty, so v1/v2 verdicts carry.

**All 13 [v3] marks CONFIRMED.** Every corpus figure re-derived independently and matched exactly.

| [v3] item | Verdict | Evidence |
|---|---|---|
| Observed identity set = {agent_role, agent_path}, nested link dropped | **CONFIRMED** | role-less 326, nested-role 0, with-path 80, neither 246 |
| Type-guard counts | **CONFIRMED** | parents 2,429 str / 311 dict source (2,740 total); children dict on all 495; `source.subagent` str 239 / dict 256 |
| Identity grammar, dual roster-or-path | **CONFIRMED on real data** | Both real reports resolve every item to exactly {agent path, roster name}; `no thread with id` filtered out |
| `- None.` / `- none` not a claim | **CONFIRMED** | `- none` → `none`, `- None.` → `None.`, `- None` → `None`; terminator lines still no-match in both bulleted and bare forms |
| 29/29 roster grammar row | **CONFIRMED** | Re-read with tomllib |
| Arms 9, 11, 12, 13 | **Sound** | Arm 13's fixture shapes are all real: parent `"source": "exec"` string, child `source.subagent` string, child `source.subagent` dict |
| Rows 176-179 | **CONFIRMED verbatim** | All five figure groups exact |

## Path grammar: admits repo paths, but cannot produce a false match

Your suspicion is half right. `^/[A-Za-z0-9_./-]{1,200}$` **does** admit an absolute repo path such as `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/sdlc_team.py`, and also `/etc/passwd`. It rejects the more common citation forms: relative paths (`python/src/...`, `.claude/rules/do-not.md`), `path:line` anchors, and anything with a space or semicolon.

A false **positive** match is still not reachable. Matching is set intersection on exact strings, and every observed identity is either a roster name or a codex-internal `/root/<name>` path. A repo path under `/Users/` can never string-equal `/root/...`. So the widening is cosmetic noise in the identity set, not a correctness hole.

## New missing premise: `agent_role` is not unique among siblings

**13 of 330 parent groups on this host have duplicate `agent_role` among their children** — `explorer` sixteen times under one parent, `default` fourteen times under another, `default` seven times under a third. By contrast **`agent_path` is never duplicated**: zero of 330 groups. I also checked the cross case, a role-less child sharing its path with a roled sibling, and found zero.

This breaks the v3 cardinality clause. "Every claimed item matches exactly one observed child" fails the moment a dispatcher legitimately spawns the same specialist twice, because one claimed roster token intersects both children. The result is `failed` on a correct run, which is the exact false-negative class v2 was rewritten to remove. The duplicated roles I measured belong to other agent sets rather than the sdlc roster, so this is a latent hazard rather than a live one, but nothing in the roster or the prompt forbids two spawns of one specialist.

The fix is cheap and already available: the new pinned prompt format emits both tokens per item, and path is the unique discriminator. Either match on the path when both sides carry one, falling back to role only when no path exists, or state explicitly that a duplicate-role spawn is a declared failure with its own error line.

Findings appended to `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/findings.md`. Nothing edited.

---

# Pass on spec v4 (same agent, 2026-09-16 07:46Z)

> PERSISTED VERBATIM at receipt. Architect decision on its greedy-pairing counterexample: spec v5 fails a multi-identity claimed item closed as AMBIGUOUS rather than adding an augmenting-path matcher — a strict tightening resting on no new factual premise, so no fifth pass.

# Premise verification v4

Repo at `ca6cd57`; source still unchanged, so all prior verdicts carry.

| [v4] mark | Verdict | Evidence |
|---|---|---|
| Line 104, pairing clause replacing set-intersection | **CONFIRMED** | Rests on the three measured facts, all re-derived: 13/330 groups repeat a role, 0/330 repeat a path, 0 cross-case |
| Line 150, arm 14 | **Sound** | All three sub-cases are reachable under the measured structure; the "claimed as ONE item" case correctly yields one unpaired child |
| Line 180, sibling-uniqueness row | **CONFIRMED, including the parenthetical** | Parent `019feca1` carries exactly `explorer` ×16, `default` ×14, `worker` ×5, plus `adversarial-critic` ×1 |
| Revision header line 6 | **CONFIRMED** | Marks are consistently attributed by introducing revision |

## Your question: greedy can fail, but only on a shape the pinned format forbids

**Refuted as stated, with a concrete configuration** — though the counterexample needs one claimed item to carry **two identities of the same kind**, which neither real report produces.

Counterexample. Children: A with `agent_path == /root/p1`, B with `agent_path == /root/p2`, B role-less. Claimed item 1 backticks both paths, so its path identities are `{/root/p1, /root/p2}`; claimed item 2 names only `/root/p2`. Greedy walks item 1 first and takes the first unmatched child whose path is in that set. If B precedes A in child iteration order, item 1 consumes B, item 2 then finds no unmatched child with path `/root/p2`, and the run settles `failed`. A valid one-to-one assignment exists: item 1 to A, item 2 to B. The same shape works with roles: item 1 with identities `{R1, R2}` and item 2 with only `{R2}`.

Your reasoning holds for the single-identity case, which is what the evidence shows. Across both real reports every one of the seven claimed items resolved to exactly one path plus exactly one role, and the v4 pinned format emits exactly one of each. When each item has at most one path identity, path uniqueness on both sides makes the path phase a bijection on its domain, and the role phase then only ever chooses among interchangeable same-role children, so greedy is optimal. The failure requires prose drift that adds a second path or a second roster name to one item, which the model has already demonstrated it will do with prose tokens like `no thread with id`.

Cheapest hardening, pick one: treat a claimed item with more than one path identity as ambiguous and fail it by name, or run one augmenting-path pass instead of plain greedy. With at most six specialists the augmenting pass is a few lines and removes the class outright rather than the instance.

Findings appended to `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/findings.md`. Nothing edited.

---

# Pass on the v6 RESPEC (after the cold review of 22bee5a; same agent, 2026-09-16 08:53Z)

> PERSISTED VERBATIM at receipt. Architect decisions: (1) identity model widened — a roster-grammar token may match `agent_role` OR the basename of `agent_path`, since real dispatchers write `- `<role>` as `<spawn name>`` and `- `<role>` (`<spawn name>`)`; ambiguity is reserved for two PATH identities; (2) F9 compares `st_mtime` to `datetime.fromisoformat(started_at).timestamp()` and an empty `started_at` fails closed; (3) the terminator regex is widened to `^(no\s+other|none\b|nothing\s+else)`.

# Premise verification — v6 respec on 22bee5a

All 19 PREMISES rows **CONFIRMED** against the committed implementation; every cited line is exact. Spot corrections: none.

| Row | Cite | Verdict |
|---|---|---|
| 69 | `lane_result.py:228-230` break, `_AGENT_LINE` `:97-102` | CONFIRMED |
| 70 | `7912a742/output.md:24-30` | CONFIRMED: anchor `:24`, roster `:26-28`, `json_probe` `:29`, terminator `:30` |
| 71 | `sdlc_team.py:302` harvests all backticked tokens, `:346-349` rejects >1 | CONFIRMED |
| 72 | `:399` appends the **child's** name | CONFIRMED (the F3 defect) |
| 73 | `:354-367` path then role, no cross-check | CONFIRMED |
| 74 | `:437-438` rewrites role only when the claim name is a path | CONFIRMED |
| 75 | no read of `payload.source` | CONFIRMED **with a control arm**: 0 hits for `"source"` in either module, while `agent_role` returns 2 |
| 76 | `lane_result.py:335-337`, `sdlc_team.py:472-474` | CONFIRMED |
| 77 | `:186-191` requires `lines[0].startswith` | CONFIRMED |
| 78 | `_utc_now` `:194-196`, `started_at` `:146` | CONFIRMED |
| 79-81 | corpus rows | CONFIRMED (carried from passes v2/v3, figures unchanged) |
| 82 | all 21 codex.log banners at line 1 | **CONFIRMED and strengthened** — I checked all 21, not two; zero exceptions |
| 83-87 | P/E/A rows | Sound; A row's fail direction is correct |

## Q1 — terminator rule holds on real data, with one near-miss worth knowing

Three distinct real phrasings exist across the 21 runs: `No other specialists were spawned.`, `No other specialists or subagents were spawned.`, and `No others were spawned.` (run `3cac53d7`). All three are caught, the third **only** because "no others" happens to contain "no other" as a prefix. No legitimate claim line starts with those words, so there is no false termination. The rule is correct, but it is one rewording away from missing (`None others were spawned`, `Nothing else was spawned`). Matching `^no\s+other` or `^(no other|none|nothing else)` would cost nothing.

## New missing premise — F1+F2 make three real runs ambiguous, not one

Simulating the v6 rules over every real `output.md`, ambiguous claims appear in **3 of 21 runs**, not just the `json_probe` case the spec plans for in arm 16:

- **`b941647c`, five claims**, shape `` - `sdlc-python-specialist` as `round3_python` ``. The bare tail `round3_python` passes the **roster** grammar, so the claim carries two roster identities and `_claim_problem` rejects it. All five are correct spawns, and the child's path would be `/root/round3_python`, the same token with the prefix stripped.
- **`smoke-real`, one claim**, via `` (`config_smoke_review`) ``.
- **`7912a742`, one claim** — the case arm 16 already covers.

So the spec's own F1 objective, that a real dispatcher output must not fail for the wrong reason, is not met for `b941647c`. Two cheap fixes: prefer a candidate that matches an observed identity before declaring ambiguity, or treat a second roster-grammar token as a weak identity used only when the first fails.

## Q2 — the mtime trap is real, and the dangerous form is silent

`_utc_now()` emits an aware ISO string with `+00:00`; `st_mtime` is a POSIX epoch float. The correct comparison is `mtime >= datetime.fromisoformat(started_at).timestamp()`, measured False for the April zero-byte file and True for a file written now, so it discriminates.

Two wrong forms, one loud and one silent:

- Aware parsed `started_at` against a naive `datetime.fromtimestamp(mtime)` raises `TypeError`. Loud, so a test catches it.
- Naive-LOCAL `datetime.fromtimestamp(mtime)` against a naive-stripped UTC `started_at` returns **False for a file written during the run**. Measured: local `03:53:30` against UTC `08:53:30`. This host is UTC-5, so the F9 failure arm would be dead for every run shorter than five hours, which is all of them. That is the "check that can only pass" shape.

Two smaller notes on F9. The zero-byte file's mtime is `2026-04-16T21:14 UTC` while its filename reads `16-14-05` local, the same local/UTC split the spec already documents elsewhere, so the old-file arm is naturally armed. And `collect_session_files` defaults `started_at=""` to "treat every skipped file as old", which is fail-open; `_SupervisorPayload.started_at` has no default so the supervisor path always supplies it, but the standalone CLI path does not. Worth one sentence in the spec.

Findings appended to `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/findings.md`. Nothing edited.


## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under change (sdlc_team.py, lane_result.py, tests).
- [openai/codex](https://github.com/openai/codex) — rollout record shape and `CODEX_HOME` semantics, read from the offline codex docs corpus, not fetched live.
