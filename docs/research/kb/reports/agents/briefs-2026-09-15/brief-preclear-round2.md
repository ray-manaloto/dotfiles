# Spec — pre-`/clear` audit, ROUND 2 (verification pass)

## Objective

Round 1 (`7ff5aaf3…`, rc=0) returned **BLOCK `/clear`** with 11 required items,
persisted verbatim at
`docs/research/kb/reports/agents/final-preclear-audit-2026-09-15.md`.

The coordinator has since (a) obtained operator rulings on the four undecidable
items and (b) rewritten the durable record. **This round is the control arm:
determine whether the corrections actually discharged each item, and find what
round 1 missed.**

⚠️ **A clean verdict is a legitimate outcome.** Do not manufacture findings to
justify the round. Equally, do not accept a correction because it LOOKS
addressed — check the file.

## The record under audit

    .agent/plans/session-2026-09-15.md   <- the handoff the next session reads
    task_plan.md
    findings.md

All three are gitignored by design. Round 1 flagged that; it is not a defect to
re-report.

## Part A — verify round 1's 11 required items, one at a time

For each, return **DISCHARGED / PARTIAL / NOT DONE / WRONGLY DONE**, with the
`file:line` you read.

1. Local HEAD `97dcb1b`, cached upstream `4f176e1`, and the branch/cherry-pick
   recovery action recorded.
2. Q18 explicitly settled.
3. Q2/Q10 and Q12 supersession state marked.
4. A report-precedence map exists.
5. Marker state corrected to "target 2.1.273; repository still 2.1.272".
6. Ownership/provenance defined for `.claude/types/claude-code-mcp.d.ts`.
7. Target-version input, source/URL consistency, rationale preservation, and
   missing-manifest fail-closed contracts specified.
8. Refresh staging derived from every `[[schema]].file`.
9. Cache-independent lifecycle smoke, change routing, persisted-home migration,
   and separate bare/lifecycle contracts specified.
10. Q14's query-only-oracle explanation completed.
11. Runs `2dab7794…`, `54914e99…`, `7ff5aaf3…` and the `smoke-real` control
    recorded.

⚠️ **Items 2, 3 and the Q18/Q10 direction were decided by the OPERATOR, and the
rulings went AGAINST round 1's suggested wording.** Round 1 proposed wording
that assumed Q18 would be overturned and that exact-pin would be superseded. The
operator ruled the opposite: **Q18 STANDS (bake into the image)** and **exact
pin STANDS, at the latest stable release**, plus a new gate asserting
installed == pinned. Q12 IS reopened. Judge whether the record states the
OPERATOR'S rulings correctly and unambiguously — **not** whether it matches
round 1's proposed text. Round 1's wording has no authority.

## Part B — hunt what round 1 missed

Round 1 audited contradictions, false current-state claims, and omissions. Look
for classes it did NOT cover:

- **Is the record ACTIONABLE by a fresh session?** Take the single most
  important next task and ask: could someone who has read only these three
  files start it without asking a question? Name every gap that forces a
  question.
- **Newly introduced contradictions.** The corrections are new text. Does any
  of it contradict something else in the same file, or in the tracked reports?
- **Corrections that overshot.** Did any "fix" delete or weaken a true claim, or
  restate an inherited number as if it were measured?
- **Orphaned cross-references.** Does every `file:line` in the corrected text
  still resolve? Round 1 found `refresh.yml:512` had drifted to `:541`.
- **Anything in `docs/research/kb/reports/agents/` from 2026-09-15 whose
  RECOMMENDATION now conflicts with a ruling, and is not covered by the
  precedence map.**

## Part C — the DAG

The coordinator recorded a reconstructed DAG plus four named defects in our own
code (`sdlc_team.py:59,463`; `lane_result.py:367`; `lane_result.py:87`; the
impossible "all specialists in parallel" roster requirement).

Verify the DAG matches the settlement files on disk, and say whether the four
defects are stated precisely enough to be fixed. Add any fifth.

## Constraints

- Read-only. Run no gates, write no report file, modify nothing.
- Every negative finding needs a control arm; invent the known-absent token
  fresh.
- Cite `file:line`. An uncited claim is labelled unverified or dropped.
- Do NOT re-litigate operator rulings. A ruling you believe is wrong is
  reported as a RISK with its evidence, not as a required change.

## Deliverable

1. Part A table: 11 rows, verdict + evidence.
2. Part B findings, most severe first.
3. Part C verdict.
4. **One line: PROCEED TO `/clear` or BLOCK, and if BLOCK, the shortest list
   that unblocks it.**

## PREMISES (verify before relying on them)

| # | Premise | Where |
|---|---|---|
| P1 | Round 1's report is on disk and is what I summarised | `docs/research/kb/reports/agents/final-preclear-audit-2026-09-15.md` |
| P2 | HEAD is `97dcb1b`, upstream `4f176e1`, 1 ahead | `git rev-list --left-right --count @{u}...HEAD` |
| P3 | `schemas/sources.toml` still records 2.1.272 | `schemas/sources.toml:51-52` |
| P4 | PR #1128 is OPEN/BLOCKED with `lint` + `ci-gate` failing | `gh pr view 1128` |
