# Cold review — saved searches (#1502), uncommitted worktree diff

- Reviewer: `cold-reviewer` (Claude Opus 5.5), 2026-10-03 12:35 local
- Worktree: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/saved-searches-1502`
- Subject: the uncommitted working tree on top of HEAD `785c3708`, the stated base.
  `origin/main` has since moved to `713994ba`, two commits ahead: #1589 (report
  promotion) and #1590 (lima bump). `git diff origin/main` would therefore also show
  those two commits REVERSED. This review uses `git diff HEAD` (merge-base `785c3708`)
  plus every untracked file, excluding `.agent/`.
- Memory: `.claude/agent-memory-local/cold-reviewer/` was empty at start (first run).
- Constraints honoured: I ran no pytest, bun, lint or verify. I ran static reads,
  ruff and ty, plus four read-only checks: `codegen-check`, `skills-mirror --check`,
  `saved_searches status`, and a token-pattern scan. All used `uv run --no-sync`, so
  the venv was not modified.
- Round shape: OPEN HUNTING (round 1). The brief states no domain with a
  cardinality, so this round cannot end the loop. It promotes to one bounded round.

## Status

COMPLETE. Verdict: **SHIP-WITH-FIXES** (0 HIGH, 3 MEDIUM, 10 LOW).

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| 1 | MEDIUM | A failed or unarmed rerun reports EVERY previous URL as `GONE`. `_urls` returns `[]` for error, rate-limited and incomplete answers (items `()`) and for an unarmed 0. `_report` then computes `GONE = old_urls - set(run.urls)` with no status guard. A failure, or a 0 that lacks both arms, therefore reads as "vanished" in the drift column, and the count cell prints `N → -1` / `N → 0`. No test runs a non-ok rerun against a baseline that has URLs. | `python/src/dotfiles_setup/saved_searches.py:846-847` | Failure answers carry `items=()` at `:489`, `:492`, `:494-496`, `:505-507`. The unarmed-0 path is `:677-682`, and `_run_other` gives an unarmed 0 at `:737-741`. Every GONE test (`tests/test_saved_searches.py:681-732`, `:735-772`) uses `ok` reruns. |
| 2 | MEDIUM | The diff's "previous" is chosen per FILE, not per watch. After `rerun --id X` (a documented option), the next full rerun takes that partial snapshot as Previous. Every other watch then prints `first run → N` with ALL its URLs `NEW`. The same happens to watches a later `record` added with a baseline: once any snapshot exists, the TOML baseline is never consulted again. A false "new examples" signal is exactly what the feature exists to produce correctly. `status` likewise marks a whole file fresh from a one-watch snapshot. This follows spec §4.4 literally, so the spec carries the defect. | `python/src/dotfiles_setup/saved_searches.py:781-786`, `:793-802`, `:826-830`, `:938-939` | `_previous` returns only the newest snapshot's `(id, query)` rows. `before is None` gives `old_urls = set()` (`:828`), so NEW is every URL (`:846`) and the label is "first run" (`:830`). |
| 3 | MEDIUM | Test gap on fail-closed RECORDING: `_probe_record`'s failure predicate has no test. That predicate is `rc == 0`, `count >= 0`, `not rate_limited` and `not incomplete_results`; failing it should give status `error`. The only probe fixture has five all-good rows. Mutating `good = True` survives the suite, so a rate-limited or incomplete code row recorded as an `ok` baseline would go unnoticed. | `python/src/dotfiles_setup/saved_searches.py:278-284`; `tests/fixtures/saved_searches/probe.json:6-12` | `grep -n 'rate_limited\|incomplete_results\|"rc"' tests/test_saved_searches.py` finds only the runner stub (`:93`) and an unrelated parametrize name (`:434`). Control arm: the same grep shape finds `fanout-items.json` 3×. |
| 4 | LOW | Q-FRESH: Save passes `--probe-manifest` for `PLAN_PROBE` and every dependency probe UNCONDITIONALLY. It does so even when this run's probe line was rejected (`planProbe`/`depProbes[i] === null`), and those paths are fixed per slug. A PREVIOUS run's probe is then recorded under THIS run's `--question`/`--origin`, possibly one from a run that had `saveSearches: false`. Planner manifests are taken without `rc === 0`, and the planner's default out dir `.agent/kb/raw/research-fanout/<slug(query)>` is shared by EVERY sweep. A failed planner run can therefore pull another sweep's searches into this file. LOW rather than MEDIUM because each `[[result]]` keeps its manifest's own `generated_at`, so no observation is mis-dated. Still, the SKILL's "fresh … code probes" is unenforced. Spec §4.5 (line 234) mandates the unconditional form, and the harness test pins it (`tests/test_workflows_js.py`, `values("--probe-manifest") == [...]`). | `.claude/workflows/research-sweep-run.js:328`, `:333`; `python/src/dotfiles_setup/saved_searches.py:371-379` | Fan-out manifests ARE filtered by `fresh === true` (`:327`) for this exact reason (spec §4.5: "a stale manifest is a PREVIOUS run's results"). Default out dir: `research_fanout.py:2158-2160`. The triage half (`:624`) is pre-existing, so ticket that part. |
| 5 | LOW | A failed fan-out stores and reports `count = 0`, not −1. `_fanout_record` writes `count=len(items)` whatever the row status (error/skipped/empty_unverified), and `_run_other` does the same with `count = len(result.items)`. Spec §4.2 says −1 means "no count … never treat it as 0", yet it also defines fan-out count as items returned, so the spec is internally inconsistent. | `python/src/dotfiles_setup/saved_searches.py:257`, `:722` | `_FANOUT_STATUS` maps ERROR/SKIPPED → `error` (`:76-82`), but the count is not tied to it. |
| 6 | LOW | The status-change annotation compares two vocabularies. The recorder stores research-fanout's `empty_verified`/`empty_unverified`; reruns emit `empty-verified`/`empty-unarmed`. An unchanged watch therefore prints `empty-verified (was empty_verified)`. This bites real data: the two tracked generated files hold 17 + 6 underscore-form statuses. | `python/src/dotfiles_setup/saved_searches.py:256`, `:836-837` | `Status.EMPTY_VERIFIED = "empty_verified"` (`research_fanout.py:98`); `RerunStatus.empty_verified = "empty-verified"` (`generated/saved_search_snapshot.py:20`). Counted with `grep -o '^status = "[^"]*"'` on both TOMLs. |
| 7 | LOW | `_atomic_write` writes via `NamedTemporaryFile` (mkstemp, mode 0600). Every generated tracked TOML, `--report` file and snapshot lands as `-rw-------`, and re-recording a file that was 0644 downgrades it. | `python/src/dotfiles_setup/saved_searches.py:195-198` | `stat`: both generated TOMLs are `-rw-------`, while the curated `orchestration-2026-10-02.toml` and the spec are `-rw-r--r--` (the control arm). Git does not track 0600 vs 0644, so there is no diff noise; this is a local readability nit. |
| 8 | LOW | Q-CLAIM: `written` does not mean "this run's searches were saved". If the generated file exists and every manifest is missing or stale, `_record` rewrites it from the previous watches and returns `written: true` with `added == updated == 0`. The workflow then reports `written` and logs nothing, so the "not saved" log at `:357` never fires for a run that saved nothing. | `python/src/dotfiles_setup/saved_searches.py:393-407`; `.claude/workflows/research-sweep-run.js:346-357` | `watches.update(incoming)` with an empty `incoming` still reaches `_atomic_write` (`:406`). |
| 9 | LOW | `missing` conflates three cases: an absent file, a malformed file, and a GitHub fan-out manifest without `repo`. The last raises TypeError at `:245-247`, so an existing, readable manifest is reported as "missing". | `python/src/dotfiles_setup/saved_searches.py:320-321`, `:245-247` | A single broad `except` returns `None`, and `None` becomes `missing`. |
| 10 | LOW | A must-hit control that returned 0 is labelled `empty-verified` when a same-shape sibling must-hit hit. `_zero_armed` is applied to every role, not only `query`. rc stays 0, which matches the workflow's "a missed must-hit is a note, not a gap", but the snapshot calls a failed positive control verified absence. | `python/src/dotfiles_setup/saved_searches.py:677-682`, `:626` | `hits` is fed by must-hit rows (`:668-671`); `negatives` is keyed by query shapes (`:648-652`). |
| 11 | LOW | The rerun report header prints the absolute resolved file path (`# Saved searches: /Users/...`), and `--report` may target a tracked path. The spec forbids a home path in a tracked file for `origin` (§4.5), but the report header is unguarded. | `python/src/dotfiles_setup/saved_searches.py:816`, `:897` | `snapshot.file = str(file)`, where `file = _resolve(...)` (`:872`). The live `status` run printed `/Users/rmanaloto/...` paths too (stdout only). |
| 12 | LOW | The contract `workflow.research-saved-search-wiring` binds python DEFINITIONS (`def record_main(` …), not the `main()` dispatch call sites. Unwiring `record_main` from `main` would keep the contract green (pytest would still catch it). | `python/verification/suites.toml:1484-1498` | Every token occurs exactly once (counted with `text.count`; control `shq(` = 17). Call sites are `saved_searches.py:1000`, `:1002`, `:1003`. |
| 13 | LOW | Q-CLAIM: the meta phase detail says the output always goes to `docs/research/saved-searches/<slug>.toml`. Without a resolvable ROOT it goes to `<report>.searches.toml` beside the report instead. | `.claude/workflows/research-sweep-run.js:14`, `:315-316` | `SAVED_PATH` ternary. |

## Not findings (checked, clean)

- **Shell quoting.** Every value interpolated into the Save command is `shq()`-quoted:
  `SAVED_PATH`, `A.question`, `ORIGIN`, every manifest path, every probe path
  (`research-sweep-run.js:331-333`). `shq` is the established `'…'\''…'` form (`:175`).
  The harness proves round-trip through `shlex` with `Ray's query: $value \`literal\``
  and paths containing `'` (`test_research_sweep_save_origin_and_shell_quoting`). The
  #1582 fix single-quotes the dependency query via `shq(q)` and tells the planner the
  same (`:424-425`, `:451-452`). One residual: a question containing a NEWLINE spreads
  the command over several prompt lines. That is shell-valid inside single quotes but
  harder for a haiku to copy, and the harness's `_command` would fail on it. UNVERIFIED
  whether any caller passes multi-line questions.
- **PreToolUse guard interaction.** Guard rules anchor on `_CMD = (?:^|[;&|\n]\s*)`
  (`hook_guard.py:123`), and `_inert_masked` neuters separators inside quoted spans
  (`:936-961`). So a question that mentions `gh pr merge` inside `--question '…'` should
  not match. This is reasoned, not executed: UNVERIFIED.
- **Tokens never printed.** `saved_searches.py` never writes gh stderr or the env.
  `_gh_env()` only passes the env to the child (`research_fanout.py:544-545`). Snapshot,
  receipt and report carry queries, URLs and counts only. A scan of all 20 untracked
  files for `ghp_/gho_/github_pat_/sk-/AKIA/dp.st.` patterns found 0 matches; the
  control arm (a synthetic `ghp_` + 30 chars) matched 1.
- **Known-absent never saved.** `CodeRole` lacks `known-absent`
  (`generated/saved_search_file.py:24-30`), so `_probe_record` skips such rows (`:272`)
  and `--code-search known-absent=` is rc 2 (`:382-383`). The two generated TOMLs hold
  0 `known-absent` and 0 `zz<hex>` nonces; the control `schema_version` matched 1.
- **Rerun 0-handling (both arms).** Code: health > 0, plus a same-shape must-hit > 0,
  plus a fresh per-shape known-absent == 0 (`:615-630`, `:675-682`). Any failed control
  sets rc 1 (`:696-701`). Draft issues/discussions need `control_hit` AND
  `control_absent` (`:591-592`, `:609-612`). Fan-out with repo defers to fan_out's own
  control (`:717-728`). A failed or limited direct call is −1, never 0 (`:488-507`).
- **Curated files never clobbered.** The header check comes before any load or write
  (`:359-363`). The live `status` run loaded the curated orchestration file (rc 0,
  three `_controls-*` warnings as specified).
- **Contract tokens.** All 10 `per_path_tokens` occur exactly once.
- **Lint and codegen gates.** `ruff check` rc 0 and `ruff format --check` rc 0 on the
  three python files. `ty check` rc 0. Control arm: ruff rc 1 (F401) and ty rc 1
  (invalid-assignment) on a deliberately bad temp file. `dotfiles-setup codegen-check`
  rc 0 and `skills-mirror --check` rc 0; neither was mutation-armed, because arming them
  needs a source edit, which this lane may not make.
- **Mirror divergence** `.agents` vs `.claude` SKILL ("Codex" vs "Claude Code", one
  line). This is PRE-EXISTING at HEAD (`git show HEAD:` of both files differ the same
  way), and `skills-mirror --check` is rc 0.
- **Test FAIL arms spot-checked** (by reading, not mutation):
  `test_record_never_saves_known_absent`, `test_record_merge_and_curated_refusal`,
  `test_code_zero_requires_both_shape_controls`, `test_failed_code_search_never_becomes_zero`,
  `test_health_zero_invalidates_all_code`, `test_pacing_covers_every_code_call`,
  `test_status_ages_baseline_by_cadence` (strict `>` boundary at exactly 7 d), and the
  six-way JS receipt parametrize. Each asserts the behaviour its docstring names. The
  exception is the gap in finding 3.

## Required answers

- **Q-FRESH.** There are two decision→action pairs.
  - The JS Save decision (`saveSearches !== false`) leads to the command; no input can
    go stale between the two. But the INPUTS to that command are not re-validated for
    this run (finding 4).
  - In python `_record`, the `path.exists()` + header check leads to `_atomic_write`.
    There is no lock, so two concurrent records of one slug lose an update. This is
    LOW and not tabled: concurrent sweeps on one report slug already clobber each
    other's mirrors.
  - `rerun` reads the TOML once and never writes it, so it has no TOCTOU.
- **Q-SCOPE.** Every finding is in scope for #1502, with one exception. Finding 4's
  "planner manifest with rc ≠ 0 / shared default out dir" also affects the PRE-EXISTING
  triage input (`research-sweep-run.js:624`). Ticket that half as a sibling. Findings 2
  and 5 are spec defects (§4.4, §4.2): amend the spec in this unit.
- **Q-CLAIM.** I enumerated every new operator-facing string: the JS meta detail, the
  Save prompt, the Save log line, the two #1582 prompt sentences, the SKILL paragraphs,
  the python receipt reasons, the run reasons, the report header/labels, the status
  labels and `GENERATED_HEADER`. The clauses with no enforcing line are:
  - "fresh … code probes" (finding 4);
  - `written` read as "saved" (finding 8);
  - "first run" for a watch that was run before (finding 2);
  - "→ docs/research/saved-searches/<slug>.toml" unconditionally (finding 13).

  `GENERATED_HEADER`'s "edits are overwritten on the next record" OVER-states the risk:
  watches whose id is not re-recorded keep their hand edits, though comments are lost
  to `tomli_w`. That over-statement errs on the safe side, so it is not tabled.

## Recommended fixes (in-unit)

1. `_report`: diff NEW/GONE only when the run is `ok`/`empty-verified` and so is the
   previous run. Otherwise print `n/a (<status>)`. Add a test: a rate-limited rerun
   against a baseline with URLs gives an empty GONE. (Finding 1.)
2. `_previous`: resolve "previous" per `(id, query)` by walking snapshots newest to
   oldest, then fall back to that watch's TOML baseline. Amend spec §4.4. Add a test:
   `--id A`, then a full rerun, gives no `first run` for B. (Finding 2.)
3. Add a probe fixture row each for rc 1/count −1, `rate_limited`, and
   `incomplete_results` with count 0. Assert `status == "error"` and the count is
   preserved. (Finding 3.)
4. Pass `--probe-manifest` only for probes whose `readProbe` was accepted, and drop
   planner runs with `rc !== 0`. Alternatively, keep the current behaviour and soften
   the SKILL to "dated" rather than "fresh". (Finding 4.)
5. Low-cost: map recorded fan-out statuses through `_FANOUT_STATUS` before comparing
   (finding 6). `chmod 0o644` after the temp write (finding 7). Surface
   `added + updated == 0` as its own Save status (finding 8).

## GitHub repos touched

_None._ (This was a local diff review; the only external reference was a
re-read of `research_fanout.py` in this repo.)

## Disposition (coordinator annotation, 2026-10-03; the report above is verbatim)

- **Fixed in this change:**
  - M1: `_report` diffs NEW/GONE only for two answered runs, otherwise n/a. Test: `test_unanswered_rerun_never_reports_gone`.
  - M2: `_previous` picks the previous run per `(id, query)`, newest snapshot first, else the TOML baseline. Test: `test_previous_is_chosen_per_watch`.
  - M3, F5: a failed probe or fan-out row is `error` with count -1. Test: `test_record_classifies_failed_rows`.
  - F6: the recorder now uses the rerun status vocabulary, and older baselines are read through `_status_word`.
  - F7: files are written 0644. F8: a no-op record is not written and the run returns rc 1. Both are asserted in `test_record_merge_and_curated_refusal`.
  - F4: Save passes only accepted probes and only rc-0 planner manifests.
  - F13: the Save phase text is corrected.
- **Deferred to #1602:** F9 (the `missing` taxonomy), F10 (a must-hit 0 labelled empty-verified), F11 (the absolute path in the report header), F12 (the contract binds `def` lines, not dispatch). F2's status freshness also stays per-file.
- **Separate pre-existing ticket candidate:** planner runs with rc != 0 and the shared default output dir (`research-sweep-run.js`, the triage input).
