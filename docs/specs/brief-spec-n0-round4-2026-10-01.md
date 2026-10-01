# Spec delta — research-enforcement round 4 (round-3 cold-review fixes)

Same branch/checkout/allowlist/constraints/verification/commit rules as `spec-n0-round3.md` (re-read its §2, §4, §5).
HEAD is now `b5c089d8` (my docs commit on top of your `955be9e6`). Findings source:
`docs/research/kb/reports/agents/cold-review-research-enforcement-round3-2026-09-30.md` (untracked; read, never modify
or commit). Commit message: `fix(research): close round-3 review findings in research-sweep-run (round 4)`.

## Objective — fix the CLASS, not just the instance

### R1 (MEDIUM) — the health row must not satisfy the must-hit requirement
Give the search-health row its own role `health` (add to `CODE_ROLES`). It is a gap when not answered >0 (unchanged),
but `ok(codeSearch, 'must-hit', …)` must be satisfied only by a planner must-hit or a per-repo README row that hit.
Test: unindexed repo + no planner must-hit + health OK → `mandatory-gap` (the review's failing scenario).
Synthesis "Code search" table keeps listing the health row (role `health`).

### R2 (MEDIUM) — a redirected/renamed repo is not the repo you asked for
Compare `exists.fullName` to `r` case-insensitively. Mismatch → mandatory gap
`dependency repo <r> redirects to <fullName> — re-run with repo/relatedRepos set to <fullName>` and do NOT emit the
"not indexed" note for it. Fix every fixture that carries a mismatched `fullName` so the healthy baseline is honest.
Live premise (architect, 2026-10-01): `gh api repos/jdx/rtx --jq .full_name` → `jdx/mise` rc=0; `repo:jdx/rtx
filename:README.md` → 0 rc=0.

### R3/R4/R6 — the README note and the exists check must say only what they know
- R6: the deps agent returns `exists.status` = the HTTP status (200 / 404 / 403 / other; `gh api -i` or parse the
  `gh: … (HTTP NNN)` line). Only 404 → "not found". 403/other → mandatory gap `could not check <r> via the repos API
  (HTTP <n>${rate-limit wording when 403/429})`. Treat 429 like 403 (rate limit).
- R4: emit the README note only when health answered >0. If health failed/unrun, the README-0 row gets no note (the
  health gap already says search is unverified).
- R3: note wording → `"<q>" returned 0 although <r> exists — either code search does not index it (e.g. a low-star
  fork) or it has no README.md (e.g. README.rst); not a gap`. Update the pinning test and SKILL.md text.
  Live premise: `repo:sphinx-doc/sphinx filename:README.rst` → 3.

### R5 — FAILED STAGES text per stage
Build the synthesis FAILED STAGES clause from WHICH stage failed (planner null / planner no manifests / triage null),
each naming its own evidence consequence; no fixed sentence. Align SKILL.md `links-only` text.

### R7 — close the injection CLASS for every interpolated arg (F8 was one instance)
- Validate `repo` and every `relatedRepos` entry against `^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$` at arg parse; throw on
  mismatch (same style as the existing `reportPath` / `repoRoot` throws).
- Validate `REPORT_SLUG` against `^[A-Za-z0-9_.-]+$`; throw on mismatch.
- Then sweep EVERY shell command string the workflow builds (plan, deps, mirror, index, any other) and confirm each
  interpolated value is either shape-validated or quoted with the shared escape helper. List each site + its guard in
  your report. Tests: a `repo` with `;` / `'` / space throws; a slug with `'` throws.

### R8 — F6 in both directions
For the question-terms slot (`depQueries(r)[k] === null`), the returned query must NOT equal any related repo's name
(nor REPO's name). Normalise returned queries by trimming surrounding quotes before comparison (no false gap for an
echoed `"name"`). Tests for both.

### R10 — pin the five untested lines
`!r.manifest` arm of `fanoutGaps`; mirror-path quoting; the moved Mandatory log line (after README-index gap);
`fanoutGaps` on the `no-manifests` return; the "no runs" text. Rename/strengthen the S1 test so its name matches what it
asserts.

### OUT of scope
R9 (pre-existing: dep run counts as OK when only releases worked) — architect is ticketing it. F4/F5/F9/F11/F12.

## Verification
As round 3 §5, plus: in-place mutation of each R1/R2/R3/R4/R6/R7/R8/R10 line → RED, pristine GREEN, `git diff` empty
after each restore. Append a `## Round 4` section to the implement report incrementally.
