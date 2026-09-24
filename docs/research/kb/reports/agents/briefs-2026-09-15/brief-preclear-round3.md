# Spec — pre-`/clear` audit, ROUND 3 (frozen-input verification)

## Why this round exists

Round 2 (`24fdd932…`, rc=0) returned **BLOCK**, and its own CRITICAL finding was
that **the audit inputs changed while its five specialists were reading them** —
the handoff moved through at least seven versions, 41,978 → 58,862 bytes. Its
Part A verdicts are therefore snapshot findings against bytes that no longer
exist, not a certification.

**The inputs are now FROZEN.** The coordinator has stopped editing them.

## ⚠️ VERIFY THE FREEZE FIRST — this is a required step, not a courtesy

Before reading anything for content, confirm you are auditing the frozen bytes:

```bash
shasum -a 256 task_plan.md findings.md .agent/plans/session-2026-09-15.md .claude/types/README.md
```

Expected, exactly:

    3c75844823169c52a1f73ff545a9f3de0b6b8a30b09edf75dd566a95b6dafd7f  task_plan.md
    ff85b87145c8096c25ce84b9e54315466c3a3cc3b6612c6cac6b6aca783e53f2  findings.md
    098cb91b77ca98c4f93e25547573d509b37bfd5711282fd09a98c35d8222ef49  .agent/plans/session-2026-09-15.md
    02647d4e7b6779b6f5c42e7d531343d4a3515e93d581f025dcbf2573b4515c95  .claude/types/README.md

**If any hash differs, STOP and report the mismatch as your first finding.** Do
not audit content against a spec whose baseline has already drifted — that is
the exact defect this round exists to avoid repeating. Re-verify the hashes once
more at the END of your review and report if they moved.

## Part A — did round 2's findings actually get fixed?

Round 2's report is at
`docs/research/kb/reports/agents/` (round 1) and
`.agent/sdlc-runs/24fdd932fe414da08f2b4c285b39ebfb/output.md` (round 2, read
this one). For each item below return **FIXED / PARTIAL / NOT FIXED / WRONGLY
FIXED**, with the `file:line` you read.

1. **A3 / B2 — duplicate Q12.** Round 2 found "reopened; do not move" and the
   superseded "moves out of `shared.toml`" both live in the authority table.
2. **A4 / B5 — precedence map.** Round 2: `session-audit-2026-09-15.md` left
   unqualified despite a superseded `latest` recommendation, and
   `claude-version-drift-disposition.md` called aligned despite contradicting
   the exact-pin ruling.
3. **A6 / B3 — MCP declaration ownership.** ⚠️ **Round 2's framing was WRONG and
   you must not repeat it.** This was NOT an open question: it was settled
   2026-09-12 and is implemented at `fnhook_gates.py:469-480`
   (`drift_comparable_files` EXCLUDES `claude-code-mcp.d.ts` because it is
   per-session in its entirety). Only the README was false. **Verify the README
   fix is correct and complete, and that nothing else in the repo still claims
   that file is vendored.**
4. **A7 / B4 — missing-manifest fail-closed contract.** Round 2: diagnosed but
   no required fail arm. Check a contract now exists AND requires inverting the
   positive test at `tests/test_fnhook_gates.py:457` that currently blesses the
   permissive behaviour at `fnhook_gates.py:530`.
5. **B6 — the "parked work is gone" claim.** Round 2 refuted it. Check the
   retraction is honest and the artifacts are preserved at
   `docs/research/kb/raw/parked-claude-install-2026-09-15/`.
6. **B7 — stale cross-references.** Round 2 named `task_plan.md` still citing
   Q18b as open and `refresh.yml:512`, plus `devcontainer.json:119` used for
   the home-volume mount when `:119` is `remoteUser` and the mount is `:129`.
   **Sweep for ANY remaining instance of all three across all three files.**
7. **Part C — DAG defect precision.** Round 2 corrected `sdlc_team.py:463`→`477`
   and `lane_result.py:87`→`92`, said defects 2 and 3 were not precise enough to
   implement, and added a fifth (receipt publication fails open,
   `sdlc_team.py:529`). Check all five are now stated precisely enough that an
   implementer needs no further questions.

## Part B — is the record ACTIONABLE, and what is still wrong?

1. **The first task.** Ruling Q24 makes it Phase 5b/5c (agentsview). Could a
   session that has read ONLY these three files begin it without asking a
   question? Name every gap that forces one.
2. **New contradictions.** The corrections are new text. Does any of it
   contradict something else in the same file or another?
3. **Overshoot.** Did any correction delete or weaken a TRUE claim, or restate
   an inherited number as if it were measured?
4. **Cross-reference resolution.** Spot-check `file:line` citations added in
   this round of corrections. Report every one that does not resolve.
5. **The ruling table Q2–Q25.** Is every ruling stated once, unambiguously, with
   no two rulings sharing a number and no superseded ruling still readable as
   current?

## Constraints

- Read-only. Run no gates, write no report file, modify nothing.
- Every negative finding needs a control arm. **Invent the known-absent token
  FRESH** — do not reuse `R2CTRL_*` or any token from a previous round's report,
  because those strings are now IN the corpus.
- Cite `file:line`. An uncited claim is labelled unverified or dropped.
- Do not re-litigate operator rulings. A ruling you believe is wrong is a RISK
  with evidence, not a required change.
- ⚠️ **Do not treat a document's claim as the state of the world.** Round 2's
  one wrong finding came from reading a false README as authoritative instead of
  checking the code. Where a document and the code disagree, the code wins and
  the disagreement is the finding.

## Deliverable

1. Freeze verification: hashes matched, or which differed.
2. Part A: 7 rows, verdict + evidence.
3. Part B findings, most severe first.
4. **One line: PROCEED TO `/clear` or BLOCK. If BLOCK, the shortest list that
   unblocks it.**

## PREMISES (verify before relying on them)

| # | Premise | Where |
|---|---|---|
| P1 | The four files match the hashes above | `shasum -a 256` |
| P2 | Round 2's report is readable | `.agent/sdlc-runs/24fdd932fe414da08f2b4c285b39ebfb/output.md` |
| P3 | `drift_comparable_files` excludes the MCP declaration | `python/src/dotfiles_setup/fnhook_gates.py:469-480` |
| P4 | The parked patch is preserved in-repo | `docs/research/kb/raw/parked-claude-install-2026-09-15/` |
