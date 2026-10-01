# Cold review (round 3) — `955be9e6` vs parent `836983e3` (feat/research-enforcement)

- Subject: `git diff 836983e3..955be9e6` (one commit, 7 files, +587/-79).
- Branch HEAD at review time: `b5c089d8` (a docs-only commit on top of the subject). Every `file:line`
  below cites the `955be9e6` blob.
- Prior review: `docs/research/kb/reports/agents/cold-review-research-enforcement-2026-09-30.md`
  (F1-F12). This commit claims F1, F2, F3, F6, F7, F8, F10 closed.
- Reviewer: cold-reviewer (Opus). Memory consulted: `saved_workflow_js_review.md`, `mutation_harness.md`.
- Status: COMPLETE. Auto memory was enabled and consulted; the scratch worktree was removed after use.

## Method and controls

1. **Scenario driver over the real blobs.** `git show 955be9e6:` and `git show 836983e3:` of
   `.claude/workflows/research-sweep-run.js` run through one fixture (`scratchpad/h/drive3.py`). My
   `agent()` records label, model, effort and prompt; `parallel()` maps a throwing thunk to `null`. The
   default dependency responder returns the new `exists`/`health` fields, which the parent ignores, so
   one fixture drives both blobs.
   - Control C0: the healthy fixture returns `complete` with 0 gaps on BOTH blobs.
2. **Mutation table** run IN PLACE on a scratch `git worktree add --detach <scratchpad>/wt 955be9e6`
   (not `git archive`). Each mutation asserts an exact anchor count, runs the whole
   `tests/test_workflows_js.py` from the worktree (`REPO_ROOT` resolves to the worktree via `__file__`),
   and restores the file with `git -C wt checkout --`. Pristine worktree: **45 passed, rc=0**.

### Replay of the claimed fixes (both blobs, same fixture)

| Prior finding | Scenario | `836983e3` (parent) | `955be9e6` (subject) | Closed? |
|---|---|---|---|---|
| F1 | planner runs all `rc=1`, no manifest; deps OK; no links | `complete`, 0 gaps | `links-only`; stageGap `planner fan-out produced no manifests (q rc=1) …`; `fanoutGaps` names the run | yes |
| F1 | same + one link | `complete`, 0 gaps | `links-only`, same gaps | yes |
| F2 | planner `null`, no links, deps OK | stageGap `no fan-out ran`; synth told "only the caller links" | stageGap `no planner fan-out ran (dependency-repo manifests, if any, were still read)`; synth told "caller links plus the mandatory-stage (dependency-repo) manifests" | yes for this scenario (but see R5, scenario N1) |
| F3 | README control `0 rc=0`, repo exists, health OK | `mandatory-gap`, blamed on gh auth | `complete`; a note says the repo is not indexed | yes for the auth blame (but see R1-R4, scenarios N2/N3/N4/N6) |
| F6 | related repo; both deps agents swap the cross-direction name for question terms | `complete` | `mandatory-gap`, both swaps named | yes |
| F8 | link `https://ex.test/it's;touch${IFS}/tmp/pwn;'` | `… scrape 'https://ex.test/it's;touch${IFS}/tmp/pwn;'' …` (the quote breaks out) | `… scrape 'https://ex.test/it'\''s;touch${IFS}/tmp/pwn;'\''' …` (one word) | yes for the mirror command (but see R7, scenario N12) |

### Live probes (authenticated `gh`, 2026-09-30)

| Probe | Result |
|---|---|
| `search/code q='repo:cli/cli filename:README.md'` (the new health control) | `9`, rc=0 — matches the comment at `:108` |
| `search/code q='repo:jdx/mise filename:README.md'` (control) | `19`, rc=0 |
| `search/code q='repo:jdx/rtx filename:README.md'` (`jdx/rtx` was renamed to `jdx/mise`) | **`0`, rc=0** |
| `gh api repos/jdx/rtx --jq .full_name` | **`jdx/mise`**, rc=0 (the API follows the rename) |
| `gh api repos/jdx/zz-no-such-repo-q7 --jq .full_name` (control) | HTTP 404, rc=1 |
| `search/issues q='repo:jdx/rtx hook'` vs `repo:jdx/mise hook` | HTTP 422, rc=1 vs `3514`, rc=0 |
| `mise run research-fanout -- "hook" --repo jdx/rtx --sources github-issues,github-discussions,github-releases` | **rc=0**: issues `error` (422), discussions `empty_unverified`, releases `ok` 10 items |
| `search/code q='repo:sphinx-doc/sphinx filename:README.md'` (8045 stars, not a fork, root `README.rst`) | **`0`, rc=0** |
| `search/code q='repo:sphinx-doc/sphinx filename:README.rst'` (control: the repo IS indexed) | `3`, rc=0 |
| `search/code q='repo:pypa/pip filename:README.md'` (root `README.rst`) | `1`, rc=0 |

### New-behaviour scenarios (subject blob; parent where it discriminates)

| # | Scenario | `955be9e6` | `836983e3` |
|---|---|---|---|
| N1 | `triage: null`, one link | `links-only`; stageGap `triage returned null — no fan-out hit was read`; synth told "say the evidence base is the caller links **plus the mandatory-stage (dependency-repo) manifests**" | same status; synth told "only the caller links" |
| N1c | planner `null`, one link, `repo: ''` (no dependency stage at all) | synth told "plus the mandatory-stage (dependency-repo) manifests"; there are none | — |
| N2 | README `0 rc=0` AND health `0 rc=0` | gap "search-health … — gh auth, rate-limit or search is broken" **and** note "… GitHub code search does not index it …; not a gap" in the same run | — |
| N3 | repo unindexed (README 0), planner query `repo:example/repo someSymbol` = 0, known-absent 0, **no planner must-hit** | **`complete`**, 0 gaps; the only must-hit >0 is `repo:cli/cli filename:README.md` | `mandatory-gap` (README gap + `no must-hit control returned a hit`) |
| N4 | `deps:example/repo` null; `deps:other/tool` README 0 | note asserts `other/tool` is not indexed; health never ran | — |
| N5 | `exists: {rc:1}` (e.g. a 403), README count 7 | one gap `dependency repo example/repo not found via the repos API (rc=1)`; the README result is not evaluated | — |
| N6 | `repo: 'jdx/rtx'`, `exists: {rc:0, fullName:'jdx/mise'}`, README 0 (the live values above) | **`complete`**; note says `jdx/rtx` is not indexed; `fullName` never read | `mandatory-gap` |
| N7 | `deps:example/repo` fills BOTH slots with the cross-direction name `tool` (question terms never searched) | `complete` | — |
| N8 | `deps:other/tool` reports query `"repo"` (with its quotes) | `mandatory-gap`: `cross-direction query "repo" not run (got ""repo"")` | — |
| N9 | one planner run rc=0 with no manifest beside a good run | `complete`; `fanoutGaps` names it | — |
| N10 | planner `runs: []` | `links-only`, stageGap `… (no runs) …` | — |
| N11 | `health` returned by the 2nd agent only | gap `… was not run …` (correct) | — |
| N12 | `relatedRepos: ["o'x/t$(id)"]` | dep prompt renders `-f q='repo:o'x/t$(id) filename:README.md'`, `gh api repos/o'x/t$(id)`, `--repo o'x/t$(id)` | — |
| N13 | README index `written:false` | `Mandatory:` log now counts it (1 gap) — the F10 log fix holds | — |

## Findings

| # | Sev | Claim | file:line | Evidence |
|---|-----|-------|-----------|----------|
| R1 | MEDIUM | **Regression:** the search-health row is pushed into `codeSearch` with `role: 'must-hit'`, so on every sweep where health passes it satisfies the must-hit check by construction, and `:368` can no longer fire without another gap already present. A sweep about an unindexed repo with no planner must-hit and an all-zero planner query now reads `complete`; the parent read `mandatory-gap`. | `.claude/workflows/research-sweep-run.js:340`, `:359`, `:368` | N3: subject `complete`, the only must-hit >0 being `repo:cli/cli filename:README.md`; parent `mandatory-gap` with 2 gaps. One of those two (the README gap) was removed on purpose by F3. The other, `no must-hit control returned a hit`, is what the health row suppresses: with candidate R1-C (health row role `health`) N3 returns to `mandatory-gap` on that gap alone. By enumeration, `:368` needs no answered must-hit >0. Health OK satisfies it. Health failed already pushes `:345`. Health absent already pushes `:312` (no deps), `:317` (deps[0] null) or `:346` (not run). `test_research_sweep_other_missing_stages_are_mandatory_gaps` case 2 has to zero `health` to reach `:368` at all. **Q-SCOPE:** this is the #1471 (F4) class, which Ray ruled ticket-not-block. The new aspect is that the must-hit requirement is now identical to the health requirement on every run. The in-diff fix is one token: give the health row its own role, or exclude it at `:368`. Otherwise add this delta to #1471. |
| R2 | MEDIUM | **A renamed repo now reads `complete` with a false note.** `exists.fullName` is collected but never compared with `r`. The repos API follows the rename (rc=0), code search returns `0 rc=0` for the old name, and the note says the repo "is not indexed … not a gap". The parent read `mandatory-gap`. | `:183`, `:292-293`, `:353-355` | Live: `repos/jdx/rtx` gives `jdx/mise` rc=0; `repo:jdx/rtx filename:README.md` gives 0 rc=0; `research-fanout --repo jdx/rtx` gives rc=0 (releases follow the redirect, issues 422, discussions empty_unverified), so `:325` raises no dep gap. N6 fixture with those values gives `complete`. Every test's `DEPS_OK` returns `fullName: 'stub/repo'` for `example/repo`, a "rename" in every fixture, and all 45 pass. That proves the field is never read. Fix: compare `fullName` case-insensitively with `r`, and on a mismatch raise a gap that names the canonical repo. |
| R3 | LOW | The note's causal clause "GitHub code search does not index it (e.g. a low-star fork)" has no enforcing line. A `README.md` 0 also means "no README.md" (an indexed repo with `README.rst`) or "renamed" (R2). The comment "README_CONTROL asks 'is THIS repo indexed?'" overclaims the same way. | `:355`, `:108-110`; SKILL `.claude/skills/research-sweep/SKILL.md:62-64` | Live: `sphinx-doc/sphinx` gives `filename:README.md` 0 but `filename:README.rst` 3 (indexed, 8045 stars, not a fork). Status is unaffected because it is a note, but the report text states a false cause. `test_research_sweep_readme_zero_for_an_existing_repo_is_a_note` pins the causal string verbatim. |
| R4 | LOW | The README note is emitted whatever the health outcome. With health `0` the run carries both "search is broken" and "this repo is not indexed". With the first deps agent null, the note asserts non-indexing while health never ran. | `:342-346`, `:355` | N2, N4. The implement report's decision 1 relies on the null gap "covering" the missing health check, but the note text is still emitted. A `healthRow && !healthFailed` guard on `:355` is the candidate fix (mutation F3j below). |
| R5 | LOW | The FAILED STAGES instruction is one fixed string for three different stage failures, so the F2 fix is the mirror image of F2. It is now false for triage-null: the synth is told the evidence base includes dependency manifests "still read", although no fan-out hit was read, and it omits the planner manifests that do exist. It is also false for a repo-less sweep, which has no dependency manifests. The planner stage gap's "were still read" is likewise false once triage then fails, and "no planner fan-out ran" kept the mid-run-null overclaim that F10 removed from the sibling strings. | `:504`, `:383`; SKILL `.claude/skills/research-sweep/SKILL.md:144-145` (`links-only` "… triage failed; the evidence base is the caller links plus the mandatory-stage manifests") | N1, N1c. Mutation F2a (restoring the old clause) is red only through the S2 test, which runs a planner failure. Neither triage-null test asserts the clause. The candidate fix R5-C is red only through that same S2 test, which pins the clause verbatim. |
| R6 | LOW | Any `exists.rc !== 0` is reported as "not found via the repos API", including a 403 (core rate limit, SAML SSO) or a gh auth error. The `else if` chain then skips the README control's result. | `:353-354` | N5: README count 7 (indexed), still a single "not found" gap. Status is correct (`mandatory-gap`); the wording sends the operator to look for a typo. |
| R7 | LOW | The F8 class is not closed. `repo`/`relatedRepos` values go into four shell commands per dependency agent, unquoted or inside bare single quotes (`--repo ${r}`, `-f q='repo:${r} …'`, `gh api repos/${r}`, `--out …/${r.replace('/', '--')}`), with no `owner/repo` shape check. `REPORT_SLUG` is likewise unquoted in `--out`. | `:78`, `:81`, `:284`, `:287`, `:293` | N12 renders `-f q='repo:o'x/t$(id) filename:README.md'`. The values are caller-supplied, hence LOW. One validation line beside the `reportPath` check (`:77`) closes the class. |
| R8 | LOW | The F6 content check is one-directional. An agent that fills the question-terms slot with the cross-direction name reads `complete`, so REPO's tracker is never searched for the QUESTION. An agent that echoes the query with its quotes raises a false mandatory gap (the safe direction). | `:322-324` | N7 gives `complete`; N8 gives `mandatory-gap` `(got ""repo"")`. |
| R9 | LOW (ticket) | Pre-existing, surfaced by R2's live arm: `research-fanout` rc=0 means ANY source succeeded, so a dependency run whose `github-issues` errored and whose discussions were `empty_unverified` counts as a successful mandatory stage on releases alone. | `:325` (unchanged here); `python/src/dotfiles_setup/research_fanout.py` rc rule | Live `--repo jdx/rtx` gives rc=0 with issues `error`. **Q-SCOPE:** not this diff (Python untouched; `:325` predates it), so recommend a ticket. Triage still lists `error`/`empty_unverified` sources as gaps. |

| R10 | LOW | Unpinned lines that the fix commit added: the `!r.manifest` arm of the `fanoutGaps` filter (a planner run with rc=0 and no manifest), `shq()` on the mirror PATHS (only the URL is pinned), the moved `Mandatory:` log, `fanoutGaps` on the `no-manifests` return, and the `(no runs)` stage-gap text. Separately, `test_research_sweep_null_planner_without_links_reads_dependency_manifests` asserts no triage prompt, so its name claims more than it checks. | `:377`, `:299-300`, `:413`, `:381`, `:384`; `tests/test_workflows_js.py` (the S1 test) | Mutations F1c, F8c, F10, N2 and N1 all stay green. T1 (triage reads only `planManifests`) is red, but only through the older `caller_links_survive_a_null_plan`, not the S1 test. |

### Mutation table (in place on the `955be9e6` worktree; whole `tests/test_workflows_js.py`)

Every anchor asserted `count == 1` (2 for F3a) before writing. The worktree was clean after every
restore (`git -C wt status --short` printed nothing, rc=0).

| Row | Mutation | Result | Failing tests |
|---|---|---|---|
| PRISTINE / PRISTINE2 | none | green | — (45 passed) |
| CTRL | status drops `mandatory-gap` | **RED** | 5 tests |
| M1 | delete `runs.length < want` | RED | cross_direction…, other_missing_stages |
| M2 | `answered` drops `!rateLimited` | RED | other_missing_stages |
| M3 | delete README-index gap | RED | other_missing_stages |
| M5 | synth drops "must say … INCOMPLETE" | RED | missing_dependency_stage |
| M6 | reconcile drops MANDATORY GAPS line | RED | missing_dependency_stage |
| M7 | reader mirror OK without `bytes > 0` | RED | empty_mirror… |
| M8 | dep command drops `--out` | RED | dependency_stage_runs_per_repo… |
| F1a | stage gap keyed on combined manifests | RED | planner_fanout_without_manifests ×2 |
| F1b | `fanoutGaps` drops the `rc !== 0` arm | RED | partial_planner_failure… |
| F1c | `fanoutGaps` drops the `!r.manifest` arm | **survived** | — (R10) |
| F1d | FANOUT GAPS line not sent to synth | RED | 3 tests |
| F2a | old FAILED STAGES clause | RED | planner_fanout_without_manifests ×2 (only) |
| F2b | old null-planner stage-gap text | RED | caller_links_survive_a_null_plan, null_planner_without_links… |
| F3a | health asked of every deps agent | RED | search_health_is_asked_once… |
| F3b | drop the health-failed gap | RED | search_health_is_asked_once… |
| F3c | drop the health-not-run gap | RED | other_missing_stages |
| F3d | drop the exists gap | RED | missing_dependency_repo_is_one_gap |
| F3e | README 0 becomes a gap again | RED | readme_zero_for_an_existing_repo_is_a_note |
| F3f / F3g | auth blame always / never | RED / RED | rate_limit_is_never_a_zero / blames_auth…only_when_health_failed |
| F3h | health row left out of `codeSearch` | RED | search_health_is_asked_once… |
| F3i | health threshold `>= 0` | RED | search_health_is_asked_once… |
| F3j | **candidate fix for R4**: note only when health ran and passed | **survived** | — (R4's behaviour is unpinned in both directions) |
| F3k | delete `:368` (no-must-hit gap) | RED | other_missing_stages, only via case 2, which must zero `health` to reach the line (R1) |
| F3l | README checked even when `exists` failed | RED | missing_dependency_repo_is_one_gap |
| F3m | health read from the LAST agent | RED | 2 tests |
| F6a | drop the cross-direction content check | RED | cross_direction… |
| F6b | content check order-insensitive (`some`) | survived | acceptable semantics, not a finding |
| F8a / F8b | URL back in bare quotes / `shq` without `/g` | RED / RED | link_is_one_shell_word |
| F8c | mirror dir unquoted | **survived** | — (R10) |
| F10 | `Mandatory:` log removed | **survived** | — (R10; observational, acknowledged by the implement report) |
| N1 / N2 | `(no runs)` text emptied / `fanoutGaps` dropped from `no-manifests` | survived / survived | — (R10, cosmetic) |
| T1 | triage reads `planManifests` only | RED | caller_links_survive_a_null_plan only (R10) |
| R1-C | **candidate fix for R1**: health row gets role `health` | **survived** | — the tests pin neither direction; the fix costs no test edit |
| R2-C | **candidate fix for R2**: `fullName` ≠ `r` is a gap | RED | **16 tests**, because every `DEPS_OK` fixture reports `fullName: 'stub/repo'` for `example/repo`; the fixture world is a rename and reads `complete` (R2) |
| R5-C | **candidate fix for R5**: clause becomes "say which evidence was read" | RED | planner_fanout_without_manifests ×2 (pins the clause verbatim) |

**F7's claim holds.** M1, M2, M3, M5, M6, M7 and M8 and every claimed F1/F3/F6/F8 line go red. The
survivors are lines the commit did not claim (R10), or candidate fixes for this round's findings.

### Tests that pass for the wrong reason

- `test_research_sweep_other_missing_stages_are_mandatory_gaps` case 2 pins `:368`, but only by also
  zeroing `health`, so the pinned line never fires alone (R1).
- `test_research_sweep_readme_zero_for_an_existing_repo_is_a_note` pins the causal text "does not index
  it (e.g. a low-star fork)", which is false for a rename (R2) and for a `README.rst` repo (R3). It
  repeats round 2's F2 test shape: a test pinning a false string.
- Every `DEPS_OK` fixture returns `exists.fullName: 'stub/repo'` for `example/repo`. The suite is green
  only because `fullName` is never read (R2-C: 16 red).

### Q-CLAIM — clauses of the operator-facing strings this diff adds or changes

| Clause | Enforcing line | Outcome |
|---|---|---|
| `search-health control … ${outcome} — gh auth, rate-limit or search is broken` | `:344` (answered && count > 0) | fine |
| `… was not run, so whether code search answers is unverified` | `:346` | fine |
| `dependency repo ${r} not found via the repos API (rc=…)` — "not found" | `:353` is `rc !== 0` only | **overclaims** for a 403 or auth failure (R6) |
| `README control … ${outcome}` + conditional auth blame | `:354` | fine |
| note `… returned 0 although ${r} exists` — "exists" | `:353` `exists.rc === 0` | true only under SOME name: a renamed repo "exists" as another repo (R2) |
| note `— GitHub code search does not index it (e.g. a low-star fork)` | **none** | false for a rename (R2), a `README.rst` repo (R3), a health failure, or a never-run health check (R4) |
| note `; not a gap` | `:355` routes it to notes | a deliberate choice; with R2 it hides a real misconfiguration |
| `planner fan-out produced no manifests (…) — … evidence from the planner is missing` | `:384` | fine |
| `planner returned null — no planner fan-out ran` | **none** | a null can arrive mid-run (`$CC/workflows.md:309`, cited by round 2). F10 narrowed this for its siblings but not here (R5) |
| `… (dependency-repo manifests, if any, were still read)` | **none** | false when triage then fails (R5) |
| `FANOUT GAPS (each is a Gap: a planner fan-out run that failed or wrote no manifest)` | `:377` | fine (the `!manifest` arm is unpinned, R10) |
| `FAILED STAGES (… say the evidence base is the caller links plus the mandatory-stage (dependency-repo) manifests)` | **none** | false for triage-null and for a repo-less sweep (R5) |
| `cross-direction query "${q}" not run (got …)` — "not run" | `:323` self-reported string equality | a quoted echo reads as "not run" (R8) |
| `agent reported nothing (null)` | `:316`, `:331`, `:364` | fine |
| comment `:60-61` "skipping it cannot read as `complete`" (the planner's must-hit) | `:368` | **false**: the health row satisfies the must-hit (R1, N3) |
| comment `:108` "README_CONTROL asks 'is THIS repo indexed?'" | **none** | it asks whether a `README.md` is indexed (R3) |
| SKILL `:57-58` "at least one planner query plus a must-hit and a fresh known-absent control" | `:367-369` | the must-hit need not be the planner's, and the health row always supplies it (R1) |
| SKILL `:62-64` "a 0 for a repo that exists is only a note, since code search skips some repos" | `:355` | the "since" is one of three causes (R2, R3) |
| SKILL `:144-145` `links-only` "… the evidence base is the caller links plus the mandatory-stage manifests" | **none** | false for triage-null (R5) |
| rule header "items 2-4 enforced by the `research-sweep-run` workflow" | the workflow, when it runs | item 2's must-hit is satisfied by the health row (R1). Items 2-4 still bind only inside the opt-in workflow, which round 2's Q-CLAIM already noted; F10 is only **partly** closed here |

### Q-FRESH

1. **Health (agent 0, at its own moment) → the README note for agents 1..n.** The note is emitted
   without consulting health at all (R4). Re-validating against fresh inputs would mean gating `:355` on
   `healthRow && !healthFailed`.
2. **`exists` → README interpretation.** The same agent runs both in sequence, so they are fresh with
   respect to each other. But `exists` validates the NAME only through `rc`, never through `fullName` (R2).
3. Mirror `bytes` is still self-reported (unchanged from round 2; acceptable given the runtime).

### Q-SCOPE

- R1: the #1471 (F4) class, which Ray ruled ticket-not-block. Either apply the one-token fix here (R1-C
  costs no test edit) or add the N3 delta to #1471.
- R9: pre-existing Python rc semantics; recommend a new ticket.
- R2-R8 and R10: introduced or left open by this commit's own fixes; in scope.

### Stop condition (per the adversarial-review skill)

The brief's enumerated part, the seven claimed fixes, is **answered**. F1, F2 (for its scenario), F3
(the auth blame), F6, F7, F8 (the mirror command) and F10 (the log and the null wording) are closed.
F10's rule-header clause is only partly closed. The new-defect hunt was open, and it found R1-R10. Any
further round should be scoped to the delta of the R1/R2 fixes: the health row's role, and the `fullName`
comparison with its fixture update. It should not re-open the whole workflow.

## Verdict

**SHIP-WITH-FIXES.** 0 HIGH, 2 MEDIUM (R1, R2), 8 LOW (R3-R10).

Every claimed fix closes its original scenario, and the claimed mutations all go red. The required fixes:

1. **R2:** compare `exists.fullName` with `r` (case-insensitively) and raise a gap that names the
   canonical repo. Update `DEPS_OK` to echo the real repo name; 16 tests depend on it.
2. **R1:** give the health row its own role, so it cannot satisfy `:368` (no test edit needed). Or, if
   Ray prefers the ticket route, record the N3 delta on #1471.

The LOWs can ride along. R4 is a one-condition guard; R5 needs per-stage clause text plus an update to
the S2 test's pin; R7 is one validation line. Ticket R9.

## GitHub repos touched

- [cli/cli](https://github.com/cli/cli) — the new search-health control (`filename:README.md`, 9 hits).
- [jdx/mise](https://github.com/jdx/mise) — README control arm (19) and canonical-name arm for the rename probe.
- [jdx/rtx](https://github.com/jdx/rtx) — renamed repo: repos API follows to `jdx/mise`, code search returns 0, issue search returns 422.
- [sphinx-doc/sphinx](https://github.com/sphinx-doc/sphinx) — an indexed repo whose root README is `README.rst`: `filename:README.md` 0, `filename:README.rst` 3.
- [pypa/pip](https://github.com/pypa/pip) — `README.rst` root but `filename:README.md` 1 (a nested README.md), the contrast case.
