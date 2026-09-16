# cold-reviewer — commit 22bee5a (spawn reconciliation), 2026-09-16

> PERSISTED VERBATIM at receipt (agent-report-persistence.md rule 1). Agent: `cold-reviewer` run as an Opus subagent (Claude = third model family vs the codex implementer), diff-only by ref, no intent framing. The on-disk incremental report was 32 lines; the full final message below was recovered from the subagent transcript. Coordinator refutation pass and dispositions follow the report.

Report written to `/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/68a8b3b8-90eb-4d81-ab35-ceabe415ec3b/scratchpad/cold-review-22bee5a.md`. Findings below.

## Refs

- Reviewed: `22bee5a3c45b82fdf9113bb6dfc5fa0ea71aa3c6`
- Parent: `36ac565d62ffd5f4a8f50e90a96df0e3cf0e4b7c`
- 9 files, +1276 / −59. Baseline at this ref: 47 tests pass, rc=0.

Graphify was stale (graph at `63a76ec0`, HEAD 20 commits ahead), so I read source. Mutation harness control arm: deleting the demotion line at `python/src/dotfiles_setup/sdlc_team.py:857` from a `git archive` copy turns **6 tests red**, so green results from that harness are real.

## Findings, most severe first

**1. HIGH — one grammar-rejected list item silently truncates the claim list, so a correct run settles `failed`.** `python/src/dotfiles_setup/lane_result.py:228-230` breaks out of the claim loop on the first item `_AGENT_LINE` (`lane_result.py:97`) does not match. Run 7912a742's own `output.md` contains exactly such an item:

```
- `sdlc-config-specialist`
- `json_probe` (`default`) — nested JSONL observability probe
- `sdlc-python-specialist`
```

The parenthetical defeats the optional role group, so parsing stops after item 1. Replayed against three matching children: 1 claim parsed, `consistent=False`, errors `observed child 'json_probe' was not claimed` and `observed child 'sdlc-python-specialist' was not claimed`. Control arm with the odd item removed: `consistent=True`. The errors accuse the children of being unclaimed when the dispatcher did claim them.

**2. HIGH — one extra backticked roster-shaped word in a claim's narrative makes the claim "ambiguous" and fails a correct run.** `_claimed_identity` harvests every backticked token from the item tail (`sdlc_team.py:314`) and `_claim_problem` rejects more than one role or path (`sdlc_team.py:346-349`). Probed:

```
- `sdlc-python-specialist` — `/root/python_review`; spawned after `explorer` finished
```

gives `claimed item 'sdlc-python-specialist' carries more than one path or role identity` plus a second error blaming the child. Control arm without the trailing clause: `consistent=True`. Run 2c97f4bc already appends backticked prose in that position and survived only because its token (`no thread with id`) contained spaces.

**3. MEDIUM — `specialists_claimed` is overwritten with the observed name on every match, so a `completed` settlement holds no dispatcher-originated text.** `sdlc_team.py:399` appends `children[child_index].node.name` rather than the claim. Probe: a report claiming only `` `/root/python_review` `` produces `specialists_claimed == ('sdlc-python-specialist',)`, a string absent from the report, and `sorted(claimed) == observed` holds by construction on every passing run. The skill docs at `.claude/skills/codex-sdlc-team/SKILL.md:96` say settlement "records the dispatcher's claimed specialists separately from child sessions observed"; for the runs that pass, the two rosters are one source.

**4. MEDIUM — path-first pairing falls back to role, so a fabricated path and a scrambled role/path association both settle `completed`.** `_matching_child` tries path (`sdlc_team.py:361`) then role (`sdlc_team.py:364`) with no cross-check. Probed: a claim citing `/root/never_existed` with role `sdlc-python-specialist`, against a child whose real path is `/root/python_review`, yields `consistent=True` with zero errors. Two claims with their roles and paths swapped also yield `consistent=True`. The commit message rests path-first pairing on `agent_path` never repeating; I reproduced that statistic (330 parent groups, 13 with duplicate roles, 0 with duplicate paths), but a wrong path is never reported.

**5. MEDIUM — a direct child with neither `agent_role` nor `agent_path` is unpairable by construction and forces `failed`.** `collect_session_files` reads only those two fields plus `id` (`lane_result.py:326-334`), and `_unmatched_child_errors` (`sdlc_team.py:403-418`) then reports it. Measured on `~/.codex/sessions` (3236 files, 495 children):

| child identity shape | count |
|---|---|
| agent_role + agent_path | 166 |
| agent_path only | 80 |
| agent_role only | 3 |
| neither | 246 |

On codex 0.154.0, the version in the live banner, 15 of 53 children have neither, and all 15 carry `source = {"subagent": "review"}`. None has landed under an SDLC dispatcher parent yet, so this is latent rather than observed. `test_identityless_child_fails_with_its_uuid_and_missing_fields` (`tests/test_sdlc_team.py:774`) pins the failure, so the behavior is intended; the corpus is what makes it load-bearing.

**6. MEDIUM — a role-only claim cannot pair with a path-only child.** Probed: claim `` `sdlc-python-specialist` ``, child with `agent_path` only, gives `claimed … has no observed child session` plus `observed child '/root/python_review' … was not claimed`. Control arm with a role+path child: `consistent=True`. 80 of 495 real children are path-only, and run 7912a742's real output emits role-only claims.

**7. MEDIUM — the newly pinned prompt format makes every consistent run emit a spurious `conflicting role` disagreement in its receipt.** `build_prompt` now pins ``- `<agent_role>` — `<agent_path>` `` (`sdlc_team.py:289`), but `_canonical_self_report` strips backticks only when the claim leads with a path (`sdlc_team.py:437-438`). For the pinned order the claim role stays `` `/root/python_review` `` while the observed role is `/root/python_review`, so `merge_sources` reports `agent 'sdlc-python-specialist' has conflicting role: self_report='`/root/python_review`', observed='/root/python_review'`. Settlement status is unaffected. It is untested: `test_real_shape_uses_closing_spawn_list_and_three_matching_children` (`tests/test_sdlc_team.py:690`) uses the pinned shape but discards `_receipt`.

**8. MEDIUM — the commit message's `source.subagent` type-guarding describes code that does not exist, and the test that names it passes without it.** The message says "every nested read is type-guarded because `payload.source` is a string on most parent records and `source.subagent` a string on 239 of 495 children". Grep across both changed modules returns only two comment hits; no code reads `payload["source"]`. `test_session_file_collector_reads_first_records_and_guards_payload_shapes` (`tests/test_lane_result.py:170`) supplies four `source` variants and `tests/test_sdlc_team.py:63` supplies `{"subagent": "type-guard-control"}`. Deleting all four `source` keys in an archive copy leaves **47 passed, rc=0**, while the harness control arm goes red. This is also the direct cause of finding 5.

**9. MEDIUM — an unreadable rollout is a non-causal note, so a dropped child fails the run.** `collect_session_files` sets `error` while leaving `available=True` (`lane_result.py:336-342`), and `reconcile_spawns` only inspects `observed.available`. A child whose rollout is unreadable at settlement is silently dropped and then reported as "has no observed child session". A 0-byte rollout demonstrably exists in the corpus (`~/.codex/sessions/2026/04/16/rollout-2026-04-16T16-14-05-019d9824-….jsonl`), which is why every one of the 21 replays prints `skipped 1 unreadable rollout file(s)`.

**10. LOW — no legitimately zero-specialist run can settle `completed`.** `_is_none_claim` (`sdlc_team.py:294`) drops `- None.`, but zero children then triggers `zero specialists observed under …` (`sdlc_team.py:491-495`), and any child present triggers an unclaimed-child error. The `None` handling only changes the error text.

**11. LOW — the banner parse requires the banner at byte 0 of the merged stdout+stderr log.** `lane_result.py:186-191`. All 21 real logs parse, and their stderr-style lines start at line 34 or later, so this is brittleness rather than a live defect. Control arm: prepending one line returns `None`, which demotes the run to `failed`.

**12. LOW — `_ROSTER_IDENTITY` is lowercase-only** (`sdlc_team.py:185`), so a capitalized role claim fails as "names no roster specialist or agent path". All 21 observed roles are lowercase.

**13. INFO — nothing outside pytest gates this.** Grep of `python/verification/suites.toml` and `hk.pkl` for `sdlc_team`, `reconcile_spawns`, `specialists_claimed`, `Specialists spawned`, `collect_session_files`, `parse_parent_thread_id` returns 0 hits, with `PLANNING_DISABLED=1` returning 7 as the control. `["test"]` is still pre-push only (`hk.pkl:844`) and absent from `allSteps` (`hk.pkl:34`), so `mise run lint` does not exercise any of it.

**14. INFO — the unparenthesized multi-except is correct here.** `except OSError, UnicodeError, json.JSONDecodeError:` (`lane_result.py:284`) and `except OSError, UnicodeError:` (`sdlc_team.py:770`) are PEP 758 and the project requires Python >= 3.14. Verified on the 3.14.0 runtime with both arms: a `UnicodeDecodeError` is caught by the two-type form, and a `JSONDecodeError` correctly escapes it.

## What the diff gets right

The negative arm works end to end. Replaying the new code over all 21 historical runs marks the fabricated run 2c97f4bc `failed` with `zero specialists observed`, and marks 4 genuine runs consistent. The `LAST anchor` choice is load-bearing and correct: run 4e6f6a4d quotes the phrase in prose at line 9 and the real list at line 125. Old seven-field settlements still decode, the schema additions match the struct, and `.agents/skills` mirror parity is clean (`dotfiles-setup skills-mirror --check`, rc=0).

## Coordinator refutation pass (2026-09-16 ~08:50Z)

Read against the diff, most severe first. CONFIRMED = fix in the respec round; ACCEPTED = intended fail-closed behaviour, to be documented; REFUTED = not a defect.

1. CONFIRMED — `collect_spawn_report` breaks on the first non-matching list item; list-marker lines must instead become unparseable claims so errors name the item, not the children.
2. CONFIRMED (spec defect, mine) — identity harvesting from EVERY backticked token makes narrative fail a correct run; v6 takes the item name plus the FIRST backticked token of the role text only.
3. CONFIRMED (spec defect, mine) — `specialists_claimed` must carry the dispatcher's own identity, never the observed name.
4. CONFIRMED — a claim that carries a path must match a child by that path; a path matching no child is an error; role fallback only for path-less claims.
5. CONFIRMED as a refinement — children with `source.subagent == "review"` (codex-internal review threads) are non-roster and are excluded from pairing but listed; a child with neither role nor path AND no review marker still fails closed.
6. REFUTED as a defect — a role-only claim and a path-only child share no field to pair on; the pinned format carries the path. Documented limitation.
7. CONFIRMED — canonicalize the matched claim's role to the child's agent_path in every order.
8. CONFIRMED — the 22bee5a message describes source type-guards the code does not have; v6 implements the read (for 5) with a real fail arm, and the respec commit corrects the record.
9. CONFIRMED as a refinement — unreadable rollouts NEWER than the run's start are causal (fail closed); older ones stay a receipt note.
10. ACCEPTED — a team run that spawned nothing is a failure by design.
11. CONFIRMED (minor) — locate the banner within the first 50 lines instead of requiring byte 0.
12. ACCEPTED — roster names are lowercase by the 29/29 measurement.
13-14. INFO, no action.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under review.
