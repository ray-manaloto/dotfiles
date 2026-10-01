# Cold review — `836983e3` (feat/research-enforcement) vs base `a8233f81`

- Subject: `git diff a8233f81..836983e3` (one commit, 14 files, +1239/-54).
- Base `a8233f81` == `origin/main` at review time; HEAD == `836983e3`. Every `file:line` below cites
  the `836983e3` blob.
- Reviewer: cold-reviewer (Opus). Memory consulted: `saved_workflow_js_review.md`,
  `fetcher_fanout_review_patterns.md`, `mutation_harness.md`.
- Status: COMPLETE.

## Method and controls

1. **Scenario driver over the real blobs.** I ran `git show 836983e3:` and `git show a8233f81:` of
   `.claude/workflows/research-sweep-run.js` through one fixture. My own `agent()` records
   label, model, effort and prompt. `parallel()` maps a throwing thunk to `null`, which is the
   documented runtime. `agent()` itself resolves to `null` on failure (`$CC/workflows.md:309`), so the
   two new `Promise.all` joins (`:285`, `:360`) cannot reject on agent failure.
   - Control row C0: the healthy fixture returns `complete` with 0 gaps.
   - The BASE blob through the same fixture is the regression control for S2.
2. **Mutation table.** I ran 18 one-line mutations over a `git archive 836983e3 .claude tests python`
   copy, with `PYTHONPATH` shadowing. Each mutation asserts its anchor has `count == 1`, runs
   `pytest tests/test_workflows_js.py tests/test_research_fanout.py -k "research_sweep or list_sources"`,
   and restores the file.
   - Pristine control: 26 passed (green).
   - Expected-red control (status drops `mandatory-gap`): red.
   - The full two files on the pristine copy: **104 passed**, rc=0.
3. **Live probes** (`gh api`, authenticated):

   | Query | Result |
   |---|---|
   | `repo:jdx/mise filename:README.md` | 19, rc=0 (control) |
   | `repo:virajp/mise filename:README.md` | **0, rc=0** |
   | `repo:django/django filename:README.md` | 3 |

   `virajp/mise` is a 0-star fork of `jdx/mise`. The contents API shows its `README.md` is 8569 bytes,
   so the file exists.
4. **betterleaks arm.** `betterleaks dir --redact --no-banner -c .gitleaks.toml <scratch>` ran over a
   mirror-shaped dir holding a fabricated high-entropy credential-shaped string. It returned
   `rc=1, leaks found: 1`. A clean dir returned `rc=0`.
   - My first fixture was low-entropy (`Ab3` repeated) and returned rc=0. That was a weak probe, not
     a blind gate; it is recorded here so it is not mistaken for evidence.
   - The fixture was deleted afterwards. No credential-shaped literal appears in this report.
5. **Static contract grep.** `grep research-sweep-run|research_fanout|research-fanout` in
   `python/verification/suites.toml` and `hk.pkl` returned 0. The control `PLANNING_DISABLED=1`
   returned 9, so the grep can hit and the 0 is real: **pytest is the only gate on this behaviour.**

### Scenario table

| Scenario | HEAD status / gaps | BASE |
|---|---|---|
| C0 healthy | `complete`, 0 gaps | — |
| S1 planner null, no links, deps OK | `links-only` (0 links). stageGaps: `planner returned null — no fan-out ran`. The synth prompt says "say the evidence base is only the caller links". Triage read `/d/deps:example/repo/0/manifest.json`. | — |
| S2 planner runs all lack a manifest (rc=1), deps OK, no links | **`complete`, 0 gaps** | `no-manifests` |
| S2 + one link | **`complete`, 0 gaps** | `links-only`, stageGaps `fan-out produced no manifests` |
| S3 `relatedRepos:[other/tool]`; `deps:example/repo` returns 2 runs, both QUESTION terms (cross-direction query skipped) | `complete` | — |
| S4 planner codeSearch = `foo OR bar language:toml` count 0 plus known-absent 0; no planner must-hit | `complete` (the README control carries must-hit) | — |
| S5 `repo:""`, `relatedRepos:[other/tool]` | `complete`, 0 gaps | — |
| S6 no repo, no related | `mandatory-gap` | — |
| S7 planner known-absent `{count:-1, rc:1, rateLimited:true}` | `mandatory-gap`; the gap text `no fresh known-absent control returned 0` has no RATE-LIMITED wording | — |
| S8 deps control `{count:0, rc:0, rateLimited:true}` | the gap says RATE-LIMITED, but the `codeSearch` row carries `count: 0` | — |
| S9 planner null + deps null + one link | `links-only` (mandatoryGaps has 2 entries) | — |
| S11 link `https://ex.test/it's;touch${IFS}/tmp/pwn;'` | mirror command `firecrawl scrape 'https://ex.test/it's;touch${IFS}/tmp/pwn;'' …` (the quote breaks and `;touch` becomes a separate command) | — |
| S12 reportPath `/r/docs/research/runs/x/docs/rep.md` | mirror dir `/r/docs/research/runs/x/docs/research/kb/raw/rep/links` | — |

### Mutation table (survivor = the tests stay green)

| Row | Mutation | Result |
|---|---|---|
| PRISTINE | none | green, 26 passed (control) |
| CTRL | status drops `mandatoryGaps.length ? 'mandatory-gap' :` | RED (control) |
| M1 | delete `if (got.runs.length < want) …` (`:301`) | **survived** |
| M2 | `answered = c => c.rc === 0` (drop `!c.rateLimited`, `:315`) | **survived** |
| M3 | delete the README-index-not-written gap (`:373`) | **survived** |
| M4 | delete `code search: planner returned null` gap (`:329`) | **survived** |
| M5 | synth: drop "the Answer must say the sweep is INCOMPLETE" (`:449`) | **survived** |
| M6 | reconcile: drop the MANDATORY GAPS line (`:545`) | **survived** |
| M7 | reader: mirror counts as OK without `bytes > 0` (`:407`) | **survived** |
| M8 | deps: drop `--out …/deps/<repo>/<k>` (`:270`) | **survived** |
| M10 | workflow zeroes a rate-limited count | RED |
| M11 | workflow drops `rateLimited` | RED |
| M12 | planner rows: `rateLimited` not normalised | RED |
| M13 | py `_presence`: drop the gh check | RED |
| M14 | deps: drop the REPO-side cross-direction queries | RED |
| M15 | planner prompt: drop the known-absent role instruction | **survived** |
| M16 | synth: drop "write RATE-LIMITED, never 0" | RED |
| M17 | README control of 0 is not a gap (`> 0` → `>= 0`) | RED |
| M18 | mirrorGaps keyed on `rc !== 0` instead of `reason` | survived (cosmetic) |

## Findings

| # | Sev | Claim | file:line | Evidence |
|---|-----|-------|-----------|----------|
| F1 | MEDIUM | **Regression:** a planner whose whole fan-out produced no manifest now reads `complete` with no gap. Dependency manifests satisfy `!manifests.length`, and `plan.runs` never reaches synthesis. | `.claude/workflows/research-sweep-run.js:338-343` | S2: BASE gives `no-manifests` (no links) or `links-only` + `fan-out produced no manifests`; HEAD gives `complete`, 0 gaps. `:339` concatenates `depManifests`, and no line reads `plan.runs[].rc`. A realistic trigger is a planner `--sources` typo: `research-fanout` exits rc=2 before `_persist` (`research_fanout.py:1537`), so no manifest is written. Because the prompt now steers the planner to the non-GitHub sources (`:251`), this silently drops exa/context7/firecrawl entirely. |
| F2 | MEDIUM | With a null planner, the stage-gap text and the synth instruction are now false, and the status reads `links-only` with zero links. | `:343`, `:463`, `:564-565` | S1. The stage gap says "no fan-out ran" and synth is told "say the evidence base is only the caller links", while triage read the dependency manifests. The log line `:344` was updated ("caller links and mandatory stages"); the stageGap string, the FAILED STAGES clause and SKILL.md's `links-only` description ("only caller links were read", `.claude/skills/research-sweep/SKILL.md:138`) were not. `test_research_sweep_caller_links_survive_a_null_plan` **pins** the false string (`stageGaps == ["planner returned null — no fan-out ran"]`) in the same test that asserts the deps manifest reached triage. |
| F3 | MEDIUM | The README must-hit premise "every repo has a README, so 0 means the search itself is broken" is false. An unindexed fork returns `count=0 rc=0`, which raises a mandatory gap blamed on "gh auth, rate-limit or search problem". Any sweep whose `repo`/`relatedRepos` names such a fork can never be `complete`. | `.claude/workflows/research-sweep-run.js:101-102`, `:320-321` | Live: `repo:virajp/mise filename:README.md` gives 0, rc=0, although the contents API shows `README.md` at 8569 bytes. The control `repo:jdx/mise filename:README.md` gives 19. The gap text (`:321`) sends the operator to debug auth. |
| F4 | MEDIUM | A control in a different shape can satisfy the must-hit requirement. A 0-count planner query whose own shape was never armed (e.g. invalid `OR` syntax, or an org-wide query) reads `complete`. The gap text claims a must-hit shows the search "discriminates". | `:333`, `:327-328` | S4 gives `complete`. The README control (`repo:<r> filename:README.md`) only proves the endpoint answers for one repo. The known-absent returns 0 for any broken shape too, so neither control discriminates the planner's query. This contradicts the new rule item 2 (`.claude/rules/research-doc-sources.md:13`) and `probes-need-a-control-arm.md` rule 1 ("run the same probe"). `test_research_sweep_empty_code_search_still_records_the_query` pins a 0-count query as `complete`, and nothing marks such a row unarmed for synthesis. |
| F5 | MEDIUM | The mirror stage writes arbitrary third-party pages, untracked and not gitignored, into `docs/research/kb/`. `betterleaks_verbatim_trees` scans that tree **by directory on disk**, in `allSteps` and therefore in both `pre-commit` and `check`. One mirrored docs page with a credential-shaped example blocks `mise run lint` and every commit in the checkout until the mirror is deleted, and the spec forbids an allowlist edit. | `.claude/workflows/research-sweep-run.js:99`, `:280`; `hk.pkl:348-349`, `:34` | Measured: a mirror-shaped dir with a fabricated high-entropy key gives rc=1, `leaks found: 1`; the clean control gives rc=0. `git check-ignore` on `docs/research/kb/raw/x/links/1.md` gives rc=1 (not ignored), so every sweep's mirrors also sit in `git status` (`do-not.md` #5). **Q-SCOPE:** the destination was ruled (`docs/specs/research-enforcement-2026-09-30.md` §2), so route this as a decision or ticket for Ray, not an in-diff change. |
| F6 | MEDIUM | The only guard that a dependency agent actually ran its commands is the count comparison `runs.length < want`, and **no test exercises it** (M1 survives). Even when present, it checks the count, not the content: an agent that swaps the cross-direction name query for question terms reads `complete`. | `:301` | M1 stays green (26/26). S3 gives `complete`. With M1 applied, an agent returning `{runs: [], control: …}` adds no dependency gap. The implement report's M7 relies on this line ("defence in depth") without a test for it. The "both directions" claim (`:54`, SKILL.md `:53`) therefore has no pinned enforcement. |
| F7 | LOW | Further load-bearing lines are unpinned: M2 (`!c.rateLimited` in `answered`), M3 (README-index gap), M5/M6 (the only lines that make the REPORT TEXT say INCOMPLETE), M7 (`bytes > 0`), M8 and M15. M8 matters because every related repo's dep query is the same `nameOf(REPO)` (`:92`): without `--out`, the concurrent runs share `.agent/kb/raw/research-fanout/<slug(query)>`, and `_persist` unlinks each other's files (`research_fanout.py:1338-1343`, `:1539-1541`). | `:315`, `:373`, `:449`, `:545`, `:407`, `:270` | Mutation table rows M2-M8 and M15 all survive. |
| F8 | LOW | The caller URL is interpolated inside single quotes in a shell command that a haiku general-purpose agent is told to "Run exactly". An apostrophe, which is legal and common in Wikipedia URLs, breaks the command. A crafted link injects a command. | `:280` | S11. |
| F9 | LOW | Rate-limit handling is labels only. `rateLimited` is the agent's self-report. The planner prompt equates every 403 with a rate limit, although SAML and permission errors are also 403, and it omits 429, which GitHub documents alongside 403. A rate-limited planner known-absent gets non-RATE-LIMITED gap text (S7). A `rateLimited` row can carry `count: 0` (S8). The gap still fires because `answered` requires `rc === 0`, so only the wording misleads. The stage also now runs at least 3 planner code searches plus one per dependency repo **concurrently** against the 10/min code-search bucket (UNVERIFIED; no 403 was forced live, matching the implement report's own admission). | `:254-255`, `:275`, `:315-316`, `:334` | S7, S8. |
| F10 | LOW | Q-CLAIM: several prose clauses have no enforcing line (details in the Q-CLAIM table below). | SKILL.md `:61-64`, `:53`, `:138`; rule `:9`; workflow `:61`, `:298`, `:308`, `:329`, `:347` | S5 and S9; the Q-CLAIM table below. |
| F11 | LOW | `ROOT` uses `lastIndexOf('/docs/')`, so a reportPath under a nested `docs/` mirrors into the wrong tree. | `:95-97` | S12. |
| F12 | LOW | Process: the round-2 behaviour (README control, notes, `rateLimited`) never ran live. The live arm the commit message cites ran the pre-round-2 shape and returned `mandatory-gap`, so `.claude/rules/real-integration-evidence.md` is unmet for what actually shipped. | commit `836983e3` body; `docs/research/kb/reports/agents/implement-research-enforcement-2026-09-30.md:141-182` | The implement report says "I did not force a live 403", and its round-2 checks are dry-run only. |

### Python side (`research_fanout.py`)

The `_presence` change (`:1256-1267`) is correct, and its test has teeth.

- M13 (dropping the gh check) goes red. The PATH="" arm is real because `shutil.which` returns None
  on an empty PATH.
- `_parse_sources` still omits github sources by default when no `--repo` is given. That is
  consistent with "usable once you pass `--repo`".
- `search/issues` has no `is:issue` qualifier (`:594`), so "issues/PRs" in the rule is honoured.
- `_persist` unlinks every owned file before writing (`:1338-1343`), so reusing the
  `REPORT_SLUG`-keyed `--out` dirs cannot ingest stale per-source JSON.
- rc semantics: rc=0 iff any source is `ok`/`empty_verified` (`:1570-1571`), and an empty github
  result carries a repo control. So `rc !== 0` in a dependency run really means "all three sources
  failed", which justifies classing it as a mandatory gap.

### Tests that pass for the wrong reason

- The tests do have teeth where it matters most. M10, M11, M12, M14, M16 and M17 all go red, and
  `test_research_sweep_rate_limit_is_never_a_zero`'s `row["count"] != 0` assertion catches the workflow
  zeroing a count (M10). It is **not** tautological on that axis. It cannot see an agent that
  self-reports `count: 0` with `rateLimited: true` (S8), because the workflow passes that through
  unchanged.
- `test_research_sweep_caller_links_survive_a_null_plan` asserts a false string (F2).
- `test_research_sweep_empty_code_search_still_records_the_query` pins the unarmed-shape `complete`
  (F4).
- No test exercises `runs.length < want` (F6) or any of the F7 lines.

### Q-CLAIM — clauses of the operator-facing strings this diff adds

| Clause | Enforcing line | Outcome |
|---|---|---|
| `dependency-repo stage: no args.repo or args.relatedRepos …` | `:293` `!DEP_REPOS.length` | fine |
| `… agent returned null — nothing ran` | **none** | A null can come mid-run (`$CC/workflows.md:309`, stop or API error), after commands ran. Narrow it to "reported nothing". |
| `… ${n} of ${want} run(s) reported` | `:301` | enforced, unpinned (F6) |
| `mirror stage for … agent returned null — never fetched` | **none** | same as "nothing ran" |
| `code search: planner returned null — no code search ran` | **none** | same |
| `workflow must-hit control … — a gh auth, rate-limit or search problem` | `:321` | **false for an unindexed fork** (F3) |
| `was RATE-LIMITED (HTTP 403), not 0` | the agent's self-reported `rateLimited` | label only (F9) |
| `… so the search is not shown to discriminate` (and its converse) | `:333` | a README hit does not show the planner query discriminates (F4) |
| `no fresh known-absent control returned 0` — "fresh" | **none** | The workflow cannot check freshness; the clause is a prompt request only. |
| log `… ${mandatoryGaps.length} mandatory gap(s)` | `:347` | **stale**: logged before the README-index gap is appended at `:373` |
| `FAILED STAGES … say the evidence base is only the caller links` | **none** | false with deps manifests (F2) |
| `planner returned null — no fan-out ran` | **none** | false: the deps fan-out ran (F2) |
| comment `:61` "skipping it cannot read as `complete`" | `:331-334` over **self-reported** rows | Holds only against honest omission; a fabricated row satisfies it. |
| status comment / SKILL `mandatory-gap` = "a mandatory stage did not run" | `:565` | Also fires when a stage RAN and failed (rc=1, README 0, 403). Narrow to "did not run or did not succeed". |
| SKILL "A stage that did not run returns status `mandatory-gap`" | `:564-565` | **false** under precedence: S9 gives `links-only`, and `partial-verify` also outranks. |
| SKILL "Omitting `repo` is itself a mandatory gap" | `:293` checks `DEP_REPOS`, not `REPO` | **false** with `relatedRepos` (S5 gives `complete`) |
| rule header "enforced by the `research-sweep-run` workflow" covering item 1 "Never guess … native tools first" | **none** | Item 1 has no enforcing line, and items 2-4 bind only inside the opt-in workflow (the SKILL's no-Workflow path is prose). |
| rule item 2 "with a must-hit … control" | `:333` | any-shape must-hit (F4) |

### Q-FRESH

1. **Mirror self-report → reader prompt** (`:298-308` → `:405-408`). The workflow cannot read files,
   so `bytes` is never re-validated before the reader is told "mirror: path, N bytes". This is
   acceptable given the runtime.
2. **`mandatoryGaps` → status.** Status at `:564` reads the final array. The log at `:347` reads it
   before `:373` appends (stale count, see Q-CLAIM).
3. **The planner prompt assumes the concurrent deps stage covers GitHub** (`:251`). If deps then
   fails, the planner never added github runs. The failure is still a mandatory gap, so it is
   visible. No defect.

### Q-SCOPE

- F5: Ray ruled the destination, so this is a ticket or decision, not a change request.
- F12: process.
- Everything else is in scope for this commit.

## Verdict

**SHIP-WITH-FIXES.** 0 HIGH, 6 MEDIUM, 6 LOW.

Required before ship:

1. **F1.** Restore a planner-specific "fan-out produced no manifests" stage gap, keyed on the
   planner's manifests and not the dependency manifests. Surface `plan.runs` rc≠0 to synthesis.
2. **F2.** Make the null-planner stage-gap text and the FAILED STAGES clause true (dependency
   manifests exist). Fix the SKILL.md `links-only` description and the pinning test.
3. **F3.** Stop blaming auth for an unindexed repo: check `fork`/indexability, or word the gap
   honestly.
4. **F6/F7.** Add tests for `runs.length < want` and for the M2/M3/M5/M6/M8 lines.

Decide or ticket F4 (the must-hit shape) and F5 (the mirror destination vs. the betterleaks
verbatim-tree scan) with Ray. The LOWs can ride along.

The Python change, the mirror parity (`.agents` differs from `.claude` only on the sanctioned Codex
line) and the goal-history append (pure append, all nine fields) are clean.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — README must-hit control arm (`search/code`, 19 hits).
- [virajp/mise](https://github.com/virajp/mise) — a low-star fork: README control returns 0 although `README.md` exists (contents API).
- [django/django](https://github.com/django/django) — README.md vs README.rst control probe (3 / 3).
