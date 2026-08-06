# #601 — process design: the fixes, ready to apply

**Agent:** process-designer · **Status:** DRAFT, written incrementally per
`.claude/rules/agent-report-persistence.md` §1b · **Date:** 2026-08-06

Corpus read in full: `docs/research/kb/reports/agents/601-codex-review-rounds.md`
(all 7 reports **and** all 7 briefs, 1179 lines), the 9 commits on
`fix/601-dag-tick-needs-human`, sibling drafts as they landed.

---

## Finding 0 — what EXACTLY made v7 different (the primary datum)

I compared briefs v1–v6 against v7 clause by clause. Five of the six differences
are cosmetic; **one is the mechanism**.

### The differences that are NOT the cause

| Candidate explanation | Refuted by |
|---|---|
| "v7 said a zero-finding SHIP was acceptable" | So did **v3, v4, v5 and v6** — verbatim: *"A clean SHIP with zero findings is acceptable and useful. Do not manufacture findings."* Four rounds carried that sentence and three of them still returned DO NOT SHIP. **Permission to stop is not a stop condition.** |
| "v7 was shorter / more focused" | v6 was equally specific (5 numbered attacks, each naming a mechanism). Specificity of *attacks* did not converge it. |
| "v7 named the loop's failure mode" | Necessary framing, but v6 also named it (*"v5's HIGH 1 was introduced by the fix for v4's HIGH — so hunt what `09d2cb9` broke"*) and still produced a cell-level HIGH. |
| "v7 forbade re-reporting old findings" | v2–v6 all did (*"do not restate their findings"*). |

### The difference that IS the cause

**v1–v6 asked a SEARCH question over an open domain. v7 asked a VERIFICATION
question over a finite enumerated domain.**

- Search: *"find what is wrong"* — co-domain is the set of all defects, which is
  unbounded and unenumerable. There is no answer that means *done*. The only
  terminating answer available to the reviewer was "I failed to find anything",
  which an adversarial reviewer is explicitly instructed not to produce.
- Verification: *"here are 32 cells, 4 axes and 2 meta-tests — are the cells
  right, are the axes complete, do the meta-tests hold"*. Each question has a
  finite domain and a definite answer. Answering all three IS completion.

Two consequences follow directly, and both are visible in the v7 report:

1. **It found an AXIS, not a CELL.** Q2 (*"are the four axes the right axes — is
   there a fifth?"*) is a question **about the enumeration**, not about the
   program. v1–v6 could only ever find cells, because every question they asked
   was about a behaviour, and a behaviour is a cell. Nobody was asked whether
   the space being searched was the right space. `tempo` had been sitting there
   for six rounds; it was found in one pass the moment someone asked.
2. **The escape hatch routed OUT of the loop.** v7's last paragraph: anything
   genuinely HIGH but outside the three questions *"will become a ticket rather
   than another commit on this branch."* This is the mechanical break in the
   fix→new-defect cycle: a finding no longer implies a commit, so a finding
   cannot manufacture the next round's defect.

**The reusable rule, stated once:** an adversarial review converges when the
artifact under review is an *enumeration* and the brief asks whether the
enumeration is (a) correct in its cells, (b) complete in its axes, (c) honestly
checked. It does not converge when the artifact is a *diff* and the brief asks
what is wrong with it.

_(Prescriptions below.)_
