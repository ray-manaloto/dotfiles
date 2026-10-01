# Implementer report — research enforcement (2026-09-30)

Lane: Opus fallback for codex-sol-implementer (codex usage-limited until 2026-10-03).
Spec: `docs/specs/research-enforcement-2026-09-30.md`. Worktree branch `feat/research-enforcement`. No commit.

## Status

DONE except §4 live arm 2 (a real Workflow run), which this lane cannot execute — see Dissent 1.

## Research before editing

- Workflow runtime (`$CC/workflows.md:307,324,355`): a workflow body has only `agent()`, `pipeline()`,
  `parallel()`, `phase()`, `log()`, `args` — "No direct filesystem or shell access from the workflow itself".
  So the mirror, dependency and code-search stages must each be executed by an agent; the workflow can only
  dispatch deterministically and validate the returned rows.
- `firecrawl` probe: `which -a firecrawl` first hit is
  `~/.local/share/mise/installs/npm-firecrawl-cli/1.24.6/bin/firecrawl` (stale); `mise exec -- firecrawl --version`
  prints `1.25.1` (P5 said 1.25.0 — the mise pin has moved since; the premise's point, PATH is stale, holds).
  `mise exec -- firecrawl scrape --help` confirms `-f/--format`, `--only-main-content`, `-o/--output <path>`.
- `research_fanout._prerequisite_reason` (`:967-985`) checks `request.repo is None` BEFORE `shutil.which("gh")`, and
  `_list_sources` (`:1256-1263`) maps every non-None reason to `absent` — P1 CONFIRMED.

## Implementation (all §2 files; nothing outside the allowlist except this report)

- `research_fanout.py`: new `_presence()` — `present` / `needs --repo` (reason is `needs --repo` AND
  `shutil.which("gh")` finds gh) / `absent`. `_prerequisite_reason` is untouched, so fan-out skip reasons do not move
  (`test_missing_prerequisite_and_repo_are_skipped` still expects `needs --repo`).
- `research-sweep-run.js`:
  - Plan phase now dispatches three things concurrently: the planner, one `deps:<repo>` agent per repo in
    `[repo, ...relatedRepos]` (sonnet/low), one `mirror:<n>/<N>` agent per caller link (haiku, general-purpose —
    Explore may not create files). The dependency commands are built by the WORKFLOW (not the planner): repo gets
    question-terms + each related project's NAME; each related repo gets the main repo's NAME. Each writes to a
    deterministic `--out .agent/kb/raw/research-fanout/<report-slug>/deps/<owner--repo>/<k>` so two runs of the same
    query cannot overwrite each other's manifest (default out dir is `.../<query-slug>`).
  - Mirror agent runs `mkdir -p <dir> && mise exec -- firecrawl scrape '<url>' --format markdown --only-main-content -o <dir>/<n>.md`
    from the repo root; `<dir>` = `<root>/docs/research/kb/raw/<report-slug>/links`. `<root>` = `args.repoRoot` or the
    prefix of `reportPath` before `/docs/`; missing both with links → throws.
  - `mirror-index` agent (haiku) writes `links/README.md` from rows the WORKFLOW builds (so a null mirror agent still
    gets a row), concurrently with triage.
  - PLAN schema: `codeSearch` now required, rows carry `role` ∈ {query, must-hit, known-absent}. Planner prompt makes
    code search mandatory on every run (was "config-pattern questions only").
  - `mandatoryGaps`: no repo at all; deps agent null; deps reported fewer runs than commands; a deps run with rc≠0
    or no manifest; mirror agent null; README not written; no code-search `query` row with rc 0; no `must-hit` with
    rc 0 & count>0; no `known-absent` with rc 0 & count 0; planner null.
  - `mirrorGaps` (named, NOT mandatory): firecrawl rc≠0 or 0 bytes — the stage ran, the world said no; the link is
    read live and marked NO MIRROR.
  - Link readers are told to read the mirror file; READ_RULES now say `mise exec -- firecrawl scrape … --only-main-content`.
  - Synthesis must carry three Evidence tables (Code search, Dependency-repo fan-out, Offline mirrors) with a row per
    input even at count 0; mandatory gaps flow to Gaps and the Answer must say INCOMPLETE; reconcile gets them too.
  - Status precedence: verify-null > reconcile-null > partial-verify > links-only > **mandatory-gap** > complete.
    links-only outranks mandatory-gap because it is the worse condition (a null planner implies a code-search gap too).
  - Behaviour change: with a null planner, the dependency-stage manifests are still triaged (previously triage was
    skipped); `plan-null` is now returned only when there are also no links AND no dependency manifests.
- Tests: routing pin gained `deps`/`mirror`/`mirror-index`; shared JS helpers `CODE_SEARCH_OK` / `DEPS_OK(prompt)`
  (one run per `mise run research-fanout` command the prompt names). New: per-link mirror, unfetchable link = named
  gap, deps per repo both directions, empty code search recorded, deps stubbed null → `mandatory-gap` (the §4.2 control),
  six other gap shapes. `test_research_sweep_caller_links_survive_a_null_plan` updated for the triage behaviour change.
- Rule: "Always" block (11 lines incl. heading) in `research-doc-sources.md`. `python/AGENTS.md`: scope note.
  SKILL.md: mandatory stages, `needs --repo`, `mise exec -- firecrawl`, `mandatory-gap`; `mise run skills-mirror` rc=0
  (`WROTE: research-sweep`).

## Gates (all run on the staged tree; `git diff` empty, i.e. worktree == index)

| gate | rc | evidence |
|---|---|---|
| `mise run gate -- run lint` | 0 | first run rc=1 (ruff D403/S108/PLR0913/E501, ruff_format, agnix `Unclosed XML tag '<url>'` from a code span broken across lines in SKILL.md); all fixed, re-run rc=0 |
| `mise run gate -- run pytest` | 0 | `4364 passed, 2 skipped, 11 deselected in 381.10s` |
| `mise run gate -- run verify` | 0 | `166 passed, 0 failed, 4 skipped` |
| `mise run gate -- run lint-docs` | 0 | `agnix . --strict` → `No issues found` |
| `mise run rule-sync` | 0 | bare run SKIPped (worktree has no sibling `knowledge-base`); re-run with `KB_REPO_PATH=~/dev/github/ray-manaloto/knowledge-base` → `OK rule-sync: … 22 rule(s) … hold` |
| `mise run skills-mirror` | 0 | `WROTE: research-sweep` |

## Mutation arms (each realistic regression applied to the good file, targeted tests run, restored by `cp` + `cmp`)

| # | mutation | result |
|---|---|---|
| M1 | `research_fanout.py` replaced by HEAD's (every unmet prereq → `absent`) | rc=1, 1 failed (the new list-sources test) |
| M2 | status line drops `mandatoryGaps.length ? 'mandatory-gap' :` | rc=1, 2 failed |
| M3 | mirror command uses bare `firecrawl` instead of `mise exec -- firecrawl` | rc=1, 1 failed |
| M4 | known-absent control check line deleted | rc=1, 1 failed |
| M5 | zero-count code-search rows filtered out | rc=1, 1 failed |
| M6 | dependency queries one-direction only (related names dropped) | rc=1, 1 failed |
| M7 | null dependency agent treated as `{runs: []}` | rc=1, 1 failed — NOTE the run still reads `mandatory-gap` via the "0 of 1 run(s)" check; the test fails on the exact gap text. Defence in depth, not a gap. |
| M8 | link readers no longer told about the mirror | rc=1, 2 failed |

After restore: both test files 101 passed; `cmp` clean for both source files.

## Live arms

**Arm 1 — `--list-sources`** (all rc=0):
- `mise run research-fanout -- --list-sources` → github-issues/discussions/releases `needs --repo`.
- control: `… --list-sources --repo cli/cli` → all three `present`.
- control: `env PATH=/usr/bin:/bin python/.venv/bin/python -m dotfiles_setup.research_fanout --list-sources` → all
  three `absent` (and `command -v gh` under that PATH → not found, so the arm really removed gh; the direct venv python is
  used because `mise run` re-injects gh — it is a mise tool).
- bug reproduction: HEAD's module (`git show HEAD:…`) with gh ON PATH and no `--repo` → all three `absent`.

**Arm 2 — real Workflow sweep: NOT RUN (UNVERIFIED).** See Dissent 1. What I could run for real is each command the
new mandatory-stage agents are told to execute, with control arms (outputs in the session scratchpad, not the repo):
- mirror: `mise exec -- firecrawl scrape 'https://mise.jdx.dev/tasks/' --format markdown --only-main-content -o …/1.md`
  → rc=0, 5311 bytes of main-content markdown. Control: `https://nonexistent-host-qx7v.invalid/` → rc=1, no file,
  `Error: DNS resolution failed…` (the agent's `reason`).
- dependency: `mise run research-fanout -- "task dependencies" --repo jdx/mise --sources github-issues,github-discussions,github-releases --out …/deps/jdx--mise/1`
  → rc=0, manifest path printed first, all three `ok 10 items`.
- code search: `repo:jdx/mise filename:mise.toml depends` → rc=0 count=2 (query); `repo:jdx/mise filename:Cargo.toml`
  → rc=0 count=13 (must-hit); `repo:jdx/mise vwqpzkoltrb` (fresh token) → rc=0 count=0 (known-absent). So the probe
  discriminates.
The §4.2 dry-run control (dependency stage stubbed null → `mandatory-gap`) is
`test_research_sweep_missing_dependency_stage_is_a_mandatory_gap`, passing, with M2/M7 as its fail arms.

## Dissent / decisions for the architect

1. **Live arm 2 cannot run from this lane.** This lane has no `Workflow` tool (ToolSearch finds none), and the
   `research-sweep-run` skill resolves `.claude/workflows/` from the session's project root — the MAIN checkout, whose
   file is the OLD workflow. Running it would spend tokens certifying the wrong code. It must be run from a session
   rooted in this worktree (or after merge), e.g. `Workflow({ name: "research-sweep-run", args: { question: "does mise
   support task dependencies natively", repo: "jdx/mise", links: ["https://mise.jdx.dev/tasks/"], readMax: 2,
   verifyMax: 1, reportPath: "<worktree>/docs/research/kb/reports/agents/<slug>-2026-09-30.md" } })`, then check
   `docs/research/kb/raw/<slug>/links/README.md` exists, `dependencyRuns` non-empty, `codeSearch` has all three roles,
   status `complete`.
2. **Choices beyond the spec's letter (ratify or revert):** (a) no `repo`/`relatedRepos` at all is itself a
   `mandatory-gap` (Ray: "always … dependency repo issues"); (b) a dependency run with rc≠0 is a mandatory gap (all
   three github sources failed = the evidence the rule demands is missing), while an unfetchable caller link is only a
   named `mirrorGap` (the stage ran; the world said no) and is read live; (c) `links-only` outranks `mandatory-gap`;
   (d) with a null planner, dependency-stage manifests are still triaged, and `plan-null` now requires no links AND no
   dependency manifests; (e) the README lives at `links/README.md`; (f) `repoRoot` or a `…/docs/…` reportPath is
   required when links are given.
3. **Cost:** each run adds one sonnet/low agent per repo, one haiku agent per link, and one haiku index agent (all
   general-purpose, so each pays the CLAUDE.md payload). A 1-repo, 1-link run adds 3 agents.
4. **Stale prose outside the allowlist:** `docs/specs/research-fanout.md:67` still says `--list-sources` prints
   "present/absent". Not edited (§2 is exclusive).
5. P5 inherited "1.25.0"; the pinned `mise exec -- firecrawl --version` measured today is `1.25.1` (`mise.toml:139`).
6. I `git add`-ed the untracked spec file along with my changes so lint saw the CI tree. Nothing committed;
   `docs/agents/goal-history.md` and `task_plan.md` untouched.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — live arm: dependency-stage fan-out and code-search control queries.
- [cli/cli](https://github.com/cli/cli) — `--list-sources --repo cli/cli` control arm (no network call).

## Round 2 — deterministic must-hit (team-lead, after live run wf_b74e66f5-ca3)

The architect ran live arm 2: every mandatory stage executed. Status was `mandatory-gap` only because the planner's
guessed must-hit (`filename:skills.rs repo:jdx/mise`) returned 0.

**Change (`research-sweep-run.js`):**
- Each `deps:<repo>` agent now also runs one workflow-built control and returns it as `control {count, rc, rateLimited}`
  (`DEPS.required` now includes `control`):
  `gh api -X GET search/code -f q='repo:<r> filename:README.md' --jq .total_count`
- The workflow builds the row from its own query string, so the agent can't reword the query:
  `{query: README_CONTROL(r), role: 'must-hit', source: 'workflow', …}`. Planner rows are tagged `source: 'planner'`.
- The code-search must-hit requirement is met by ANY must-hit (planner or workflow) with rc 0, not rate-limited, and
  count > 0. The query and known-absent requirements still come from the planner's rows.
- A planner must-hit that misses goes to `codeSearchNotes`, which is returned and sent to synthesis as
  `CODE SEARCH NOTES`, rendered as a note under the Code search table. It is not a gap.
- A README control that fails is a gap: count 0, rc≠0, or rate-limited all add
  `code search: workflow must-hit control "<q>" … — a gh auth, rate-limit or search problem`, even when a planner
  must-hit hit.
- 403 handling: planner and agent are told to record a 403 as `rateLimited=true, count=-1`, never 0. The gap text says
  `was RATE-LIMITED (HTTP 403), not 0`, and synthesis must write `RATE-LIMITED`, never 0, for such a row.
- SKILL.md documents the control; the `.agents` mirror was regenerated (`skills-mirror` rc=0).

**Tests** (`tests/test_workflows_js.py`, now 35):
- `DEPS_OK` returns a control with count 7.
- `…planner_must_hit_miss_is_a_note_not_a_gap`: the live failure shape now reads `complete`, with exactly one note and
  the README row present.
- `…readme_control_zero_is_a_gap`: gives `mandatory-gap` even beside a planner hit.
- `…rate_limit_is_never_a_zero`: the row carries `rateLimited: true`, count ≠ 0, and the gap names RATE-LIMITED.
- The existing "no must-hit" gap case now also zeroes the README control. The empty-code-search row equality gained
  `source` and `rateLimited`.

**Mutation checks** (each restored by `cp` + `cmp`; afterwards 35 passed):

| # | mutation | result |
|---|---|---|
| M9 | README control dropped from `codeSearch` (the pre-fix shape) | 1 failed |
| M10 | README control of 0 not a gap | 1 failed |
| M11 | `rateLimited` dropped from the workflow row | 1 failed |
| M12 | only planner rows may satisfy must-hit | 1 failed |

**Live control query:** `repo:jdx/mise filename:README.md` → rc=0 count=19; `repo:jdx/packslip filename:README.md` →
rc=0 count=5 (the two repos from the live run). I did not force a live 403; that path is covered only by dry-run tests.

**Gates (round 2, my files staged):**

| gate | rc | evidence |
|---|---|---|
| `mise run gate -- run lint` | 0 | |
| `mise run gate -- run pytest` | 0 | 4367 passed, 2 skipped, 11 deselected |
| `mise run gate -- run verify` | 0 | 166 passed, 0 failed, 4 skipped |
| `mise run gate -- run lint-docs` | 0 | No issues found |
| `mise run rule-sync` | 0 | with `KB_REPO_PATH` set: `OK … 22 rule(s) … hold` |

I did not stage or touch your `docs/agents/goal-history.md` edit or the untracked `arm-enforced-sweep-2026-09-30`
artifacts. Nothing is committed.

## Round 3 — cold-review fixes (F1, F2, F3, F6, F7, F8, F10)

Spec: `scratchpad/spec-n0-round3.md`. Findings source:
`docs/research/kb/reports/agents/cold-review-research-enforcement-2026-09-30.md` (read, not modified).
Status: IN PROGRESS.

**Premise re-check (2026-09-30):**

| # | probe | result |
|---|---|---|
| P1 | `research-sweep-run.js:339` | `manifests = (plan…).concat(depManifests)` — confirmed |
| P2 | `:564-566` | `stageGaps.length ? 'links-only'` before `mandatoryGaps` — confirmed |
| P3 | `gh api -X GET search/code -f q='repo:cli/cli filename:README.md' --jq .total_count` | `9`, rc=0 — confirmed |
| P4 | `gh api repos/virajp/mise --jq .full_name` / `repos/no-such-owner-qq7x/nope` | `virajp/mise` rc=0 / HTTP 404 rc=1 — confirmed, discriminates |
| P5 | `:92` `depQueries` | `[null, …names]` / `[nameOf(REPO)]` — confirmed |
| P6 | `tests/test_workflows_js.py:533-1284` | bun harness over the real blob — confirmed |
| P7 | `.agents/skills/research-sweep/SKILL.md` differs from `.claude/` only on the Codex line | confirmed (`diff`) |

**Implementation (round 3):**

- F1 — `planManifests` split from `depManifests`; a planner with no manifest pushes stage gap
  `planner fan-out produced no manifests (<q> rc=<n>, …) — exa/context7/firecrawl/github evidence from the planner is missing`;
  every planner run with `rc !== 0` or no manifest goes into the new `fanoutGaps` (synth `FANOUT GAPS`; returned on
  the final, `no-manifests`, `triage-null` and `synth-null` results). Early returns unchanged.
- F2 — null-planner stage gap and the synth FAILED STAGES clause reworded per spec; SKILL `links-only` fixed;
  `…caller_links_survive_a_null_plan` now pins the true string.
- F3 — `SEARCH_HEALTH_CONTROL` (deps agent 0 only) + per-repo `gh api repos/<r> --jq .full_name` (`exists`, required
  in `DEPS`; `health` optional). README 0 for an existing repo → `codeSearchNotes`; repo 404 → one mandatory gap;
  README rate-limited/rc≠0 → gap via `outcome()`, auth blame appended only when health also failed.
- F6 — per-k cross-direction query content check beside the count check.
- F8 — `shq()` single-quote escaping for the URL **and** the mirror paths (same interpolation class).
- F10 — "agent reported nothing (null)" wording; SKILL/rule/spec prose; the `Mandatory:` log moved after the
  README-index gap; header + status comments narrowed to "did not run or did not succeed".
- Tests: `DEPS_OK` now echoes the cross-direction name, `exists`, and `health` only when its prompt asks;
  `_mandatory_run` gained `plan`, `plan_runs`, `mirror_index` stubs and records the reconcile prompt.
  First run: 34 research_sweep tests passed; ruff format/check clean.

**Mutation table (round 3)** — in place on the checkout (files staged first); driver
`scratchpad/mutate.py` asserts each anchor's count, writes the mutation, runs
`uv run --project python pytest tests/test_workflows_js.py -q -k "research_sweep or every_saved"`, rewrites the
original bytes, and checks `git diff --quiet` on the workflow (rc=0 after every row, i.e. worktree == index):

| mutation | result | summary | failing tests | restore |
|---|---|---|---|---|
| PRISTINE | GREEN (rc=0) | 35 passed, 10 deselected in 7.57s |  | diff-after-restore rc=0 |
| CTRL status drops mandatory-gap | RED (rc=1) | 5 failed, 30 passed, 10 deselected in 6.70s | test_research_sweep_cross_direction_query_must_be_the_one_that_ran, test_research_sweep_missing_dependency_repo_is_one_gap, test_research_sweep_missing_dependency_stage_is_a_mandatory_gap, test_research_sweep_other_missing_stages_are_mandatory_gaps, test_research_sweep_search_health_is_asked_once_and_its_zero_is_a_gap | diff-after-restore rc=0 |
| M1 delete runs.length < want | RED (rc=1) | 2 failed, 33 passed, 10 deselected in 7.22s | test_research_sweep_cross_direction_query_must_be_the_one_that_ran, test_research_sweep_other_missing_stages_are_mandatory_gaps | diff-after-restore rc=0 |
| F6 delete cross-direction content check | RED (rc=1) | 1 failed, 34 passed, 10 deselected in 7.68s | test_research_sweep_cross_direction_query_must_be_the_one_that_ran | diff-after-restore rc=0 |
| M2 answered drops !rateLimited | RED (rc=1) | 1 failed, 34 passed, 10 deselected in 7.39s | test_research_sweep_other_missing_stages_are_mandatory_gaps | diff-after-restore rc=0 |
| M3 delete README-index gap | RED (rc=1) | 1 failed, 34 passed, 10 deselected in 7.74s | test_research_sweep_other_missing_stages_are_mandatory_gaps | diff-after-restore rc=0 |
| M5 synth drops INCOMPLETE | RED (rc=1) | 1 failed, 34 passed, 10 deselected in 7.95s | test_research_sweep_missing_dependency_stage_is_a_mandatory_gap | diff-after-restore rc=0 |
| M6 reconcile drops MANDATORY GAPS line | RED (rc=1) | 1 failed, 34 passed, 10 deselected in 7.93s | test_research_sweep_missing_dependency_stage_is_a_mandatory_gap | diff-after-restore rc=0 |
| M7 reader mirror ok without bytes>0 | RED (rc=1) | 1 failed, 34 passed, 10 deselected in 7.92s | test_research_sweep_empty_mirror_is_not_read_as_a_mirror | diff-after-restore rc=0 |
| M8 dep command drops --out | RED (rc=1) | 1 failed, 34 passed, 10 deselected in 8.06s | test_research_sweep_dependency_stage_runs_per_repo_both_directions | diff-after-restore rc=0 |
| F1 stage gap keyed on combined manifests | RED (rc=1) | 2 failed, 33 passed, 10 deselected in 8.02s | test_research_sweep_planner_fanout_without_manifests_is_not_complete[no-link], test_research_sweep_planner_fanout_without_manifests_is_not_complete[one-link] | diff-after-restore rc=0 |
| F1 fanoutGaps not passed to synthesis | RED (rc=1) | 3 failed, 32 passed, 10 deselected in 8.00s | test_research_sweep_partial_planner_failure_is_a_gap_not_a_status, test_research_sweep_planner_fanout_without_manifests_is_not_complete[no-link], test_research_sweep_planner_fanout_without_manifests_is_not_complete[one-link] | diff-after-restore rc=0 |
| F2 old null-planner stage-gap text | RED (rc=1) | 2 failed, 33 passed, 10 deselected in 8.01s | test_research_sweep_caller_links_survive_a_null_plan, test_research_sweep_null_planner_without_links_reads_dependency_manifests | diff-after-restore rc=0 |
| F2 old FAILED STAGES clause | RED (rc=1) | 2 failed, 33 passed, 10 deselected in 7.99s | test_research_sweep_planner_fanout_without_manifests_is_not_complete[no-link], test_research_sweep_planner_fanout_without_manifests_is_not_complete[one-link] | diff-after-restore rc=0 |
| F3 health control ignored | RED (rc=1) | 2 failed, 33 passed, 10 deselected in 8.05s | test_research_sweep_blames_auth_for_a_readme_failure_only_when_health_failed, test_research_sweep_search_health_is_asked_once_and_its_zero_is_a_gap | diff-after-restore rc=0 |
| F3 health asked of every deps agent | RED (rc=1) | 1 failed, 34 passed, 10 deselected in 8.09s | test_research_sweep_search_health_is_asked_once_and_its_zero_is_a_gap | diff-after-restore rc=0 |
| F3 health not-run gap deleted | RED (rc=1) | 1 failed, 34 passed, 10 deselected in 7.70s | test_research_sweep_other_missing_stages_are_mandatory_gaps | diff-after-restore rc=0 |
| F3 exists check deleted | RED (rc=1) | 1 failed, 34 passed, 10 deselected in 7.99s | test_research_sweep_missing_dependency_repo_is_one_gap | diff-after-restore rc=0 |
| F3 README 0 of existing repo is a gap again | RED (rc=1) | 1 failed, 34 passed, 10 deselected in 8.06s | test_research_sweep_readme_zero_for_an_existing_repo_is_a_note | diff-after-restore rc=0 |
| F3 README failure always blames auth | RED (rc=1) | 1 failed, 34 passed, 10 deselected in 7.91s | test_research_sweep_rate_limit_is_never_a_zero | diff-after-restore rc=0 |
| F3 README failure never blames auth | RED (rc=1) | 1 failed, 34 passed, 10 deselected in 7.96s | test_research_sweep_blames_auth_for_a_readme_failure_only_when_health_failed | diff-after-restore rc=0 |
| F8 URL back in bare quotes | RED (rc=1) | 1 failed, 34 passed, 10 deselected in 8.04s | test_research_sweep_link_is_one_shell_word | diff-after-restore rc=0 |
| F10 old deps-null wording | RED (rc=1) | 1 failed, 34 passed, 10 deselected in 8.06s | test_research_sweep_missing_dependency_stage_is_a_mandatory_gap | diff-after-restore rc=0 |

**Scenario re-run (fixtures, no live calls; `scratchpad/scen.py` over `_mandatory_run`):**

| scenario | status | gaps |
|---|---|---|
| C0 healthy | `complete` | none |
| S1 planner null, no links, deps OK | `links-only` | stage: `planner returned null — no planner fan-out ran (dependency-repo manifests, if any, were still read)`; mandatory: `code search: planner agent reported nothing (null)` |
| S2 planner runs rc=1 no manifest, no links | `links-only` (was `complete`) | stage: `planner fan-out produced no manifests (q rc=1) — …`; fanout: `planner fan-out "q" rc=1, no manifest` |
| S2 + one link | `links-only` (was `complete`) | same as S2 |
| S3 relatedRepos, cross-direction swapped | `mandatory-gap` (was `complete`) | `…example/repo: cross-direction query "tool" not run (got "terms1")`, `…other/tool: cross-direction query "repo" not run (got "terms0")` |
| S11 apostrophe link | `complete` | command renders `scrape 'https://ex.test/it'\''s;touch${IFS}/tmp/pwn;'\'''`; `shlex.split` yields the URL as ONE word |

**Gates (round 3, all on the staged tree):**

| command | rc | summary |
|---|---|---|
| `mise run gate -- run lint` | 0 | `status: passed` (17 s) |
| `mise run gate -- run pytest` | 0 | 4379 passed, 11 deselected |
| `mise run gate -- run verify` | 0 | 166 passed, 0 failed, 4 skipped |
| `mise run gate -- run lint-docs` | 0 | No issues found |
| `mise run skills-mirror -- --check` | 0 | `.agents/skills matches the generator` |
| `KB_REPO_PATH=~/dev/github/ray-manaloto/knowledge-base mise run rule-sync` | 0 | `OK … 22 rule(s) … hold` (presence-gated; the KB copy's content already differed before this round) |

**Decisions / dissent (round 3):**

1. *Health control not reported.* The spec says "Health not answered or count 0 → gap … gh auth, rate-limit or
   search is broken". I applied that wording when the health control ran and failed. When the first dependency
   agent ran but returned no `health` field (it is optional in the schema), the gap says
   `… was not run, so whether code search answers is unverified`, with no auth blame. When that agent returned
   null, no health gap is added, because the existing `agent reported nothing (null)` gap already covers it.
2. *README control on a repo that does not exist.* Only the `not found via the repos API` gap is raised, even when
   the README control was rate-limited or rc≠0. A code search against a missing repo fails (HTTP 422), so that
   failure is explained by the missing repo.
3. *`shq()` also quotes the mirror paths*, not just the URL. They share the same interpolation, and a report
   slug can contain `'`. For ordinary inputs the rendered command is byte-identical, which the existing
   `-o '<raw>/<n>.md'` test pins.
4. *Not in the spec, but kept honest.* The header comment line "A run missing any of the three returns status
   `mandatory-gap`" and the status comment had the same overclaim that F10 fixes in SKILL.md. Both now say
   "did not run or did not succeed", with the precedence caveat.
5. *Not done:* F4, F5, F9, F11, F12 (out of scope per spec). The `Mandatory:` log move has no test; it is
   observational only.

Status: COMPLETE (commit below).
