# Spec — research-enforcement round 3 (cold-review fixes)

Branch `feat/research-enforcement` in the MAIN checkout `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`,
HEAD `836983e3`. Source of findings: `docs/research/kb/reports/agents/cold-review-research-enforcement-2026-09-30.md`
(read it in full first — scenario IDs S1..S12 and mutation IDs M1..M18 below refer to it).

## 1. Objective

Close cold-review findings F1, F2, F3, F6, F7 and the cheap LOWs F8, F10 in ONE new commit on top of `836983e3`.
F4, F5, F9, F11, F12 are OUT of scope (F4/F5 are being ticketed; F12 is a live run the architect does after you).

### F1 — planner fan-out failure must not read `complete`
- Compute `planManifests` (planner runs with a manifest) separately from `depManifests`.
- When `plan !== null && !planManifests.length`, push the stage gap
  `planner fan-out produced no manifests (<q1> rc=<n>, …) — exa/context7/firecrawl/github evidence from the planner is missing`
  regardless of whether dependency manifests exist (base behaviour restored; S2 must no longer be `complete`).
- Planner runs with `rc !== 0` or no manifest (even when other planner runs succeeded) go into a NEW non-mandatory
  array `fanoutGaps` (strings naming query + rc), passed to synthesis as `FANOUT GAPS` (each a Gap) and returned in the
  result object. Partial planner failure alone does NOT change status.
- Keep the early returns: `plan-null` only when planner null AND no links AND no dep manifests; `no-manifests` only when
  NO manifests at all (planner + deps) and no links.

### F2 — make the null-planner / failed-fan-out text true
- Stage gap for a null planner: `planner returned null — no planner fan-out ran (dependency-repo manifests, if any, were still read)`.
- The synth `FAILED STAGES` clause: replace "say the evidence base is only the caller links" with
  "say the evidence base is the caller links plus the mandatory-stage (dependency-repo) manifests".
- `.claude/skills/research-sweep/SKILL.md` status list: `links-only` = "planner/fan-out/triage failed; the evidence base
  is the caller links plus the mandatory-stage manifests" (matches the existing code comment above `status`).
- Fix `test_research_sweep_caller_links_survive_a_null_plan` to assert the new, true string.

### F3 — split "is search working" from "is this repo indexed" (Ray ruling 2026-09-30)
- New constant `SEARCH_HEALTH_CONTROL = 'repo:cli/cli filename:README.md'` (measured 9 hits on 2026-09-30).
- Each deps agent additionally runs `gh api repos/<r> --jq .full_name` and returns `exists {rc, fullName}`.
  The FIRST deps agent only (index 0) also runs the health control and returns `health {count, rc, rateLimited}`.
  Extend the `DEPS` schema accordingly (`exists` required; `health` optional).
- Health row: `{query: SEARCH_HEALTH_CONTROL, role: 'must-hit', source: 'workflow', …}` added to `codeSearch`.
  Health not answered or count 0 → mandatory gap `code search: search-health control "<q>" <outcome> — gh auth, rate-limit or search is broken`.
- Per repo: `exists.rc !== 0` → mandatory gap `dependency repo <r> not found via the repos API (rc=<n>)`.
  README control answered with count 0 AND repo exists → a `codeSearchNotes` entry
  `"<q>" returned 0 although <r> exists — GitHub code search does not index it (e.g. a low-star fork); not a gap`.
  README 0 with repo NOT existing → covered by the exists gap (do not double-report as an auth problem).
  README rate-limited / rc≠0 → mandatory gap worded with `outcome()` (no "auth" blame unless health also failed).
- The must-hit requirement (`ok(codeSearch, 'must-hit', n => n > 0)`) is satisfied by any answered must-hit row incl.
  the health row — unchanged semantics; F4 (shape-matching) is ticketed, do NOT attempt it.
- Update the comment at the old README_CONTROL ("every repo has a README, so 0 means the search itself is broken") —
  it is false; replace with the two-question rationale.

### F6 — enforce WHICH dependency queries ran, not just how many
- Keep `got.runs.length < want`. Add: for every k where `depQueries(r)[k] !== null`, require
  `got.runs[k] && got.runs[k].query === depQueries(r)[k]`; otherwise mandatory gap
  `dependency-repo stage for <r>: cross-direction query "<expected>" not run (got "<actual|missing>")`.

### F7 — pin the unpinned lines with tests (each test must FAIL when its line is mutated as in the review's M-row)
M1 (`runs.length < want`), the new F6 content check, M2 (`!c.rateLimited` in `answered`), M3 (README-index-not-written gap),
M5 (synth "the Answer must say the sweep is INCOMPLETE"), M6 (reconcile MANDATORY GAPS line), M7 (`bytes > 0` in the
reader's mirror-ok test), M8 (`--out …/deps/<repo>/<k>` in the dep command). Plus tests for F1 (S2 and S2+link not
`complete`, stage gap present), F3 (fork note not gap; health 0 = gap; repo 404 = gap), F8.

### F8 — shell-safe link interpolation
- In `mirrorPrompt`, single-quote-escape the URL (`'` → `'\''`) before interpolation. Test with
  `https://ex.test/it's;touch${IFS}/tmp/pwn;'` asserting the rendered command keeps the whole URL as one quoted word.

### F10 — prose that overclaims (no behaviour change)
- "agent returned null — nothing ran" / "never fetched" / "no code search ran" → "agent reported nothing (null)".
- SKILL.md "A stage that did not run returns status `mandatory-gap`" → "A mandatory stage that did not run or did not
  succeed adds to `mandatoryGaps`; status is `mandatory-gap` unless a higher-precedence degraded status applies".
- SKILL.md "Omitting `repo` is itself a mandatory gap" → "Omitting both `repo` and `relatedRepos` is a mandatory gap".
- `.claude/rules/research-doc-sources.md` "Always" header: say items 2-4 are enforced by the workflow; item 1 is a rule.
- Move the `Mandatory: … mandatory gap(s)` log line so it runs after the README-index gap can be appended.
- `docs/specs/research-fanout.md:67`: `--list-sources` prints `present` / `needs --repo` / `absent`.

## 2. Files (exclusive allowlist — touch nothing else)
- `.claude/workflows/research-sweep-run.js`
- `tests/test_workflows_js.py`
- `.claude/skills/research-sweep/SKILL.md` and its generated mirror `.agents/skills/research-sweep/SKILL.md`
  (regenerate with `mise run skills-mirror`, never hand-edit the mirror)
- `.claude/rules/research-doc-sources.md`
- `docs/specs/research-fanout.md`
- `docs/research/kb/reports/agents/implement-research-enforcement-2026-09-30.md` — APPEND a "## Round 3" section only.
NOT: `task_plan.md`, `docs/agents/goal-history.md`, `hk.pkl`, `.gitleaks.toml`, `python/`.

## 3. Interfaces
- Workflow args unchanged. Result object gains `fanoutGaps` (array of strings). `DEPS` schema gains required
  `exists {rc:int, fullName:string}` and optional `health {count:int, rc:int, rateLimited:bool}`.
- Status taxonomy unchanged.

## 4. Constraints
- Zero-skip: no suppressions, no `--no-verify`. hk pre-commit must pass on its own.
- `.claude/rules/md-size-budgets.md`: rule files ≤200 lines (eager), SKILL ≤500.
- `.claude/rules/research-doc-sources.md` is rule-synced with knowledge-base: after editing it run
  `KB_REPO_PATH=~/dev/github/ray-manaloto/knowledge-base mise run rule-sync`; if it reports drift because KB has the
  old text, STOP and report — do not edit the KB repo.
- Mutation testing: do it IN PLACE on the checkout (edit → run → `git diff` empty after restore), NOT via `git archive`
  (memory: `git archive` mutation testing is void on this repo's gates). `git add` your work before mutating so
  `git checkout --` cannot lose it.
- Do not run the live Workflow; the architect does that.
- Never `| tail` a gate; capture rc to a file.

## 5. Verification (report each command, its rc, and the summary line)
- `mise run gate -- run lint` → 0
- `mise run gate -- run pytest` → 0
- `mise run gate -- run verify` → 0 (expect ≥166 passed, 0 failed)
- `mise run gate -- run lint-docs` → 0
- `mise run skills-mirror -- --check` → 0
- `KB_REPO_PATH=~/dev/github/ray-manaloto/knowledge-base mise run rule-sync` → 0
- Mutation table: re-run M1, M2, M3, M5, M6, M7, M8 + the new F6/F3/F8 lines — each must now go RED; pristine GREEN.
- Scenario re-run: S1, S2, S2+link, S3, S11 statuses/gaps after the fix (use pytest fixtures; no live calls).

## 6. Commit
One commit, conventional message `fix(research): close cold-review findings in research-sweep-run (round 3)`, body listing
F1/F2/F3/F6/F7/F8/F10 and "F4/F5 ticketed; F12 live arm pending". End with:
```
Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Pya9WGydcD4EJHLg9goLPL
```
Stage files explicitly by path (never `git add .`). Do NOT push, do NOT ship.

## 7. PREMISES (verified by the architect 2026-09-30, re-check any you rely on)
| # | Premise | Evidence |
|---|---|---|
| P1 | `manifests` concatenates planner and dep manifests, so dep manifests mask a planner failure | `research-sweep-run.js` (836983e3) `const manifests = (plan === null ? [] : plan.runs…).concat(depManifests)` + `if (plan === null || !manifests.length)` |
| P2 | `status` gives `links-only` whenever `stageGaps` is non-empty and reconcile/verify are clean | status expression at the end of the workflow |
| P3 | `repo:cli/cli filename:README.md` returns >0 | live `gh api -X GET search/code` → 9 (2026-09-30) |
| P4 | repos API distinguishes exists vs not | `gh api repos/virajp/mise` rc=0 fork=true stars=0; `gh api repos/no-such-owner-qq9/nope` → HTTP 404 rc=1 |
| P5 | `depQueries(r)` entries are `null` (question terms) or a name (cross-direction) | `const depQueries = r => (r === REPO ? [null, …RELATED…map(nameOf)] : [REPO ? nameOf(REPO) : null])` |
| P6 | Tests drive the real workflow blob through a JS harness in `tests/test_workflows_js.py` | existing `test_research_sweep_*` (lines ~560-1270) |
| P7 | `.agents/skills` is a generated mirror checked by hk `skills_mirror_parity` | `mise.toml [tasks.skills-mirror]`, `hk.pkl:719` |

Write your report incrementally to `docs/research/kb/reports/agents/implement-research-enforcement-2026-09-30.md`
(Round 3 section). If any premise is REFUTED or the spec contradicts the code, STOP and report instead of guessing.
