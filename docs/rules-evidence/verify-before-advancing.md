# Evidence — `verify-before-advancing`

Archaeology and provenance behind `.claude/rules/verify-before-advancing.md`.
Extracted from the rule so the eager copy carries the directive and this file
carries the case history. Read it when you want to know *why* a line in that
rule is worded the way it is, or before changing one.

## Why the rule exists

The expensive failure mode is declaring a step complete on an *assumption*:
"the warm path will skip the build", "that's a trivial edit", "lint should be
fine". The assumption is sometimes wrong, and the gap surfaces a task later,
when unwinding it is costly. The rule makes verification a hard gate between
units of work rather than an optional courtesy. It is the operational teeth
behind `zero-skip-policy.md`.

## This file is where the ≤12,000-char misattribution was born

*(2026-07-15 archaeology.)*

The rule's conditional matrix once asserted a "≤200-line / ≤12,000-char limit"
for a gate that enforced **only** lines.

The number is REAL — it is **Windsurf's** `AGENTS.md` limit (agnix AGM-003) —
but it arrived here without its source, was later machine-enforced to match this
prose, and was captioned "per Claude Code memory docs", which never stated it.

**A true fact that travels without its source becomes indistinguishable from an
invented one**, and gets applied to files its real owner never governed.

Cite a figure only where you can name the vendor; when code and a doc disagree,
re-read the source before making either match the other. See
`.claude/rules/md-size-budgets.md`, which now owns the budgets and their
provenance in full.

## The other half is SCOPE: a fact needs its CONDITION, not just its source

Provenance alone is not enough. Each fact below is genuine and correctly
sourced, and each was still wrong where it was used — because it travelled
without its "true when". This is *harder* to catch than invention: the citation
checks out, so the claim survives review.

| fact | true when | was applied to | what it cost |
|---|---|---|---|
| 12,000-char limit | Windsurf / agnix AGM-003 | all Claude markdown | a gate enforcing a limit its real owner never set |
| renovate "extracts NOTHING" under an unsupported node | some older renovate | 43.265.1, which extracts fine | a hunt for a data-loss bug that does not exist |
| 2–2.5h cold build | the p2996 cache **misses** | any `mise-system.toml` touch | a ~4x over-warning; measured ~37 min |

A stated condition is also what makes a fact **falsifiable later**: "2.5h when
p2996 misses" tells the next reader what to check, while a bare "2.5h" can only
be believed or doubted.

So when you carry a number, carry its condition — and when you meet one, ask
"what has to be true for this to hold, and is it true HERE?"

## Why this lives in one place

Deliberately folded into the rule's evidence file rather than given its own
eager rule: one idea, one place. Making it a separate rule would add a fourth
eager file restating what `md-size-budgets.md` and this rule already carry.

## GitHub repos touched

- _None._ — this is internal repo archaeology; the Windsurf figure is cited from
  <https://docs.windsurf.com/windsurf/cascade/memories>, a vendor docs site
  rather than a GitHub repo.
