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
