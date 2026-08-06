---
name: adversarial-review
description: "Write and bound an adversarial review round — the brief, the stop condition, and the escape hatch. Use when commissioning a cold or adversarial review of a diff, branch or PR; when writing the brief for a review agent (codex-reviewer, grok-reviewer, a Claude critic); when a review has returned DO NOT SHIP and you are about to run another round; or when deciding whether a review loop should end. A review's productivity is a property of its BRIEF, not of its reviewer — an unbounded \"what is broken?\" brief cannot terminate, and permission to stop is not a stop condition."
user-invocable: true
---

# Adversarial Review: Bound the Brief, Not the Reviewer

Measured on #601 (`docs/research/kb/reports/session-20260806-review-loop-reflection.md`):
**the same reviewer, same corpus, same model produced six inconclusive rounds
and then one decisive one.** The only variable that changed was the shape of the
question. Rounds 1-3 produced three commits and **zero production change**.

> **A review's productivity is a property of its BRIEF, not of its reviewer.**
> Judge a brief on that property *before* you run it, not on its findings after.

## The load-bearing property: a FINITE CO-DOMAIN

A brief is bounded when its answer set is **enumerable** — you can list, in
advance, the things a complete answer consists of.

| | Shape | Termination |
|---|---|---|
| **v1-v6** | a **SEARCH** question over an open domain — *"what is broken?"* | Never reached, only **conceded**. "No answer" means *keep looking*, so a reviewer with any diligence returns something. |
| **v7** | a **VERIFICATION** question over a finite enumerated domain — 3 questions over 32 cells / 4 axes / 2 meta-tests | **Answering them IS completion.** |

Two consequences, both visible in that record:

1. **v7 found an axis because one question asked about the *enumeration*, not
   about the program.** In six rounds nobody was ever asked whether the search
   space was the right space. Always include one question aimed at the
   enumeration itself.
2. ⚠️ **Naming an axis does not prevent pinning it.** `tempo` *was* named — in
   the 32-cell table's own comment, with a written rationale for excluding it,
   wrong in three places at once. The saving throw was a reviewer's judgement,
   **not a gate**. Do not claim a bounded brief is a guarantee; it is a much
   better bet.

## ⚠️ Permission to stop is not a stop condition

The sentence **"a clean SHIP with zero findings is acceptable" appears verbatim
in briefs v3, v4, v5 AND v6.** Three of those four still returned DO NOT SHIP.

This is the trap a well-meaning brief author falls into: reassurance is not
structure. A reviewer asked an open question will keep looking however warmly it
has been excused from doing so. **Delete the reassurance and add the enumeration
plus the stop condition below.** If you find yourself writing a sentence that
gives the reviewer *permission* to return nothing, that sentence is a signal the
brief has no bound — go fix the bound.

## The round ladder

- **Round 1 — open hunting is legitimate.** You do not yet know the defect
  classes. Run an unbounded cold review, plus the three questions below.
- **Round 2+ — MUST be bounded.** By round 2 the defect classes are known, so
  the brief states an enumerable domain: the cells, the axes, the call sites,
  the strings — and asks the reviewer to *verify* them, not to hunt.
- **A round that re-asks round 1's question is a round you already ran.** Four
  of #601's seven rounds asked the wrong question about **code that had not
  moved** — commits 2-5 never touched the function three findings were in.
- **Never run a round against code that has not moved.** This is the safest
  suppression available, because it can never hide a defect in a change: if
  nothing changed, a re-run of the same question returns the same answer. Prefer
  it over any round cap. If code has not moved and you still want another round,
  what you actually need is a **different question** — go bound the brief.

## The stop condition

> **A BOUNDED round returning SHIP with 0 HIGH and 0 MEDIUM ends the loop.
> LOWs become tickets.**
>
> **A SHIP from an OPEN-HUNTING round does not end the loop** — it promotes to
> a bounded round.

State it in the brief, verbatim, every round.

⚠️ **The "bounded" qualifier is load-bearing, and dropping it inverts the
rule.** Replayed against the #601 verdict table
(`601-codex-review-rounds.md:13-19`), the unqualified form ends the loop at v2 —
which was an *open-hunting* SHIP with 2 LOW. Rounds v4-v7 then never run, and
**five HIGHs and two MEDIUMs ship**, including two the post-mortem says would
"ship under any severity rule". That is the same failure the reflection's own
verdict names: *"every stopping rule the team proposed, replayed against this
record, ships defects."*

The qualifier is what makes it not one of them, and it is not an ad-hoc patch —
it is the finite-co-domain property again:

- SHIP from an **unbounded** round means *"I did not find anything"* —
  termination **conceded**, which is precisely what an open question can only
  ever produce.
- SHIP from a **bounded** round means *"the enumerated domain is verified"* —
  a real completion signal, because the domain was finite and it was answered.

Under the qualified form, v2's SHIP promotes to a bounded round 3, which asks
the enumeration question — the question that eventually found the missing axis
at v7.

It is deliberately **not** a round cap. A cap set low enough to have helped #601
also cuts rounds 4-7, each of which found something real.

## Three questions an enumeration CANNOT replace

Include all three in every open-hunting brief. **None was present in any of
v1-v6**, and each of them independently kills a finding that cost a full round.

- **Q-FRESH** — *"for every decision→action pair, is the decision re-validated
  against freshly-read inputs immediately before the action?"*
  An enumeration is **blind to temporal defects**: a classify→execute race is
  not a cell in any state table, and no state table would ever have found it.
  Kills #601's round-4 HIGH at round 1.

- **Q-SCOPE** — *"is this defect in scope for this ticket, or a sibling?"*
  Round 5's finding was real and out of scope; it cost a whole round of
  attention to scope out, and became issue #604. Asking up front routes it in
  one line.

- **Q-CLAIM** — *"enumerate every clause of every operator-facing string this
  diff adds or changes — log lines, status messages, CLI reasons, `Action.reason`
  — and for each clause name the `file:line` that enforces it. A clause with no
  enforcing line is deleted or narrowed."*
  Worked case, all in **one string** written at commit 1
  (`e9da8cb`, `dag_tick.py` `_needs_human_reason()`):

  | Clause | Enforcing line | Outcome |
  |---|---|---|
  | `escalated — state=blocked with a needs payload` | the classifier's conjunction | fine |
  | `never auto-respawned at any age` | **none** — the harness runs a second supervisor this module cannot close | HIGH, round 2 |
  | `(project + label dag:needs-human)` | **none** — nothing in this process writes the label | HIGH, round 2 |
  | its own replacement, `never respawned BY THIS TICK` | **none** — `execute_respawn` did not re-check | HIGH, round 4 |

  Three findings, two rounds, one string, one minute of checking. A claim with
  no enforcing call site is the repo's **third** recorded instance of this
  failure class.

## The escape hatch — a ticket, not another commit

**Out-of-scope findings route to a ticket.** This was the mechanical break in
the fix→next-defect cycle: it is what round 7 did and rounds 1-6 did not.

The cycle it breaks is real but narrower than it looks — of #601's 7 HIGHs only
**one** was loop-manufactured. The rest of the damage came from *reacting* to
in-scope-looking findings with another commit, which re-opened the review
surface each time. Write the ticket, cite it in the reason string, move on.

## Templates

### Brief — round 1 (open hunting)

```markdown
## Subject
<commit range / branch / PR>. Read the code; do not read the ticket.

## Question (open — this is round 1)
What in this diff is wrong?

## Required, in addition — answer each explicitly
- Q-FRESH: for every decision→action pair, is the decision re-validated
  against freshly-read inputs immediately before the action?
- Q-SCOPE: for each finding, is it in scope for <ticket>, or a sibling?
- Q-CLAIM: enumerate every clause of every operator-facing string this diff
  adds or changes, and name the file:line enforcing each. Clauses with no
  enforcing line are findings.

## Stop condition
This round is OPEN HUNTING, so a SHIP here does not end the loop — it promotes
to exactly ONE bounded round (round 2 below). LOWs become tickets; do not
withhold SHIP for a LOW.

## Escape hatch
An out-of-scope defect is reported as a TICKET recommendation, never as a
change request against this diff.

## Output
severity · one-line claim · file:line. Every claim cited, or labelled
unverified.
```

### Brief — round 2+ (bounded)

```markdown
## Subject
<commit range>. Read the code; do not read the ticket.

## The domain — this is the whole answer set
<the enumeration: N cells over M axes, or the K call sites, or the J strings>

## Questions — answering these three IS completion
1. Does the implementation agree with the enumeration at every one of the
   <N> cells? Name any disagreement by cell.
2. **Is the enumeration itself the right space?** Name any axis the subject
   reads that the enumeration does not vary. (Derive the axes mechanically:
   the union of the function's parameters and every subject field read by any
   predicate it calls.)
3. Do the meta-tests actually constrain the mapping, or would they pass
   against a table with the wrong values?

## Stop condition
This round is BOUNDED, so 0 HIGH and 0 MEDIUM ⇒ SHIP, and the loop ends.
LOWs become tickets.

## Escape hatch
Out-of-scope defects → ticket recommendation, not a change request.
```

### Stop-condition block (paste into any brief)

```markdown
## Stop condition
SHIP with 0 HIGH and 0 MEDIUM ends the loop IF this round is bounded (its
domain is enumerated above). If this round is open hunting, a SHIP promotes to
one bounded round rather than ending the loop. LOW findings become tickets and
do not withhold SHIP. Do NOT return DO NOT SHIP for a defect that is out of
scope for this ticket — recommend a ticket instead.
```

## Judging a brief before you run it

Five checks, in order. Any "no" means fix the brief, not the reviewer.

1. **Can you list what a complete answer consists of?** If not, the brief has
   no co-domain and cannot terminate.
2. **Is there a question aimed at the enumeration itself**, not only at the
   program? Without it the search space is never audited.
3. **Are Q-FRESH, Q-SCOPE and Q-CLAIM present?** An enumeration cannot reach
   any of the three.
4. **Is the stop condition a predicate on the OUTPUT** (0 HIGH / 0 MEDIUM), or
   merely permission? Permission is not a stop condition.
5. **Does the stop condition say whether THIS round is bounded?** An unqualified
   stop condition on an open-hunting round ships defects — see the ⚠️ above.

## When NOT to use this

- **A first review of a small, mechanical diff** — a cold review with no brief
  structure is fine, and the loop will not run twice.
- **A gate failure with a named cause** (lint, a failing test, CI) — that is
  triage, not adversarial review.
- **Design review before code exists** — use `fable-advisor` / a plan critique;
  there is no diff to enumerate over.

## See also

- `.claude/agents/adversarial-critic.md` — attacks a *proposal* (would this gate
  have caught its own motivating defect?), where this skill bounds a review of
  *code*.
- `docs/research/kb/reports/session-20260806-review-loop-reflection.md` — the
  full #601 measurement this skill is derived from, including the DROPPED table.
- `tests/AGENTS.md` § "What a good test is here" — the mutation-signature
  anti-pattern, the test-side half of the same failure.
- `.claude/rules/probes-need-a-control-arm.md` — arm both directions; a review
  that can only return findings is the loop-level instance of the same error.
- `.claude/rules/agent-report-persistence.md` — persist every review report
  verbatim, at receipt, and persist the **brief** alongside it.
