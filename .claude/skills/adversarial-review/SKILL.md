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
- **Round 2+ — should be bounded.** By round 2 the defect classes are known, so
  the brief states an enumerable domain: the cells, the axes, the call sites,
  the strings — and asks the reviewer to *verify* them, not to hunt.
  ⚠️ **"Should" is a prescription, not a fact.** Whether a round IS bounded is
  decided by the test below, applied to the brief that actually ran — never by
  its round number. Reading the prescription as the precondition is what broke
  the first version of the stop condition.
- **A round that re-asks round 1's question is a round you already ran.** Four
  of #601's seven rounds asked the wrong question about code whose relevant
  function had not moved — commits 2-5 never touched the function three findings
  were in. (State it at *function* level, as here. At diff level it is false:
  `dag_tick.py` moved 60, 37 and 17 lines in those commits.)

## What makes a round BOUNDED — the test, and it is a grep

> **A round is bounded iff its brief states a domain with a CARDINALITY.**
> "32 cells over 4 axes." "These 6 call sites." "Exactly these three questions."
>
> **Numbered questions are not an enumeration**, and **a question with a
> catch-all is not enumerated** — one "anything else you notice" re-opens the
> co-domain and un-bounds the whole brief.

Mechanically discriminated across #601's seven verbatim briefs: a stated
cardinality appears in **v1-v6 zero times, v7 twice** ("32 rows"; "exactly three
questions, nothing else"). The v7 hits are the control arm, so the six zeros are
real negatives.

⚠️ **This narrowing is not theoretical — brief v6 reads bounded at a glance and
is not.** It has *five numbered questions*, which looks like an enumeration; but
question 5 is "anything else `09d2cb9` touched", a catch-all with no co-domain.
Classify v6 as bounded and the loop **ends at v6, shipping the missing `tempo`
axis** — the exact finding this skill exists for.

Where an enumeration is machine-derived (a registry, a schema, a generated
table), prefer that: it makes the cardinality *derivable* rather than
author-asserted, and an author-asserted cardinality is a claim like any other.

## The stop condition

> **A BOUNDED round ends the loop when its enumerated questions have been
> ANSWERED — regardless of what it found.** Its findings are then dispositioned:
> fixed inside this unit of work, or ticketed.
>
> **A further round happens only if the ENUMERATION changed** — not because the
> code changed.
>
> **A round with no enumerated domain cannot end the loop by any outcome**,
> because it has nothing to have answered. It promotes to a bounded round.

State it in the brief, verbatim, every round.

**Why completion and not emptiness.** Two severity-keyed versions of this rule
were written and both ship defects, so the class is the problem, not the
threshold:

- *"SHIP with 0 HIGH and 0 MEDIUM ends the loop"* — ends at **v2** (an
  open-hunting SHIP with 2 LOW). v4-v7 never run: **5 HIGH + 2 MEDIUM ship.**
- *The same, qualified with "bounded"* — under the ladder reading v2 is bounded
  by round number, so it ends at v2 too, identically. Under the fixed-record
  reading it never terminates at all, because **v7 returned 2 MEDIUM** and the
  predicate is unsatisfiable by any round that did real work.

An emptiness test asks the reviewer to prove a negative. A completion test asks
whether a finite question set was answered — which is the finite-co-domain
property above, finally applied to the stop condition instead of contradicting
it. It is the mechanism that actually terminated #601: v7 answered three
questions over 32 cells, returned 2 MEDIUM, and the loop ended.

**Replayed, honestly:**

- v1-v6: terminates **nowhere** — none of them had an enumeration to answer.
- v7: its three questions were answered, so the round ends and the 2 MEDIUMs
  disposition in-unit, exactly as `8706670` did. **But that disposition CHANGED
  THE ENUMERATION** (32 cells → 64; `tempos = [_IDLE, _ACTIVE]`), so the re-open
  clause fires and prescribes a round 8 over the 32 newly-reachable cells. So:
  **it terminates at v8, having verified the enumeration it ended up with** —
  not at v7. That is the rule working. Thirty-two cells nobody had verified now
  existed.

⚠️ **The re-open clause has a structural self-trigger — know it before you use
it.** The bounded template's enumeration question exists precisely to find
enumeration errors, so *whenever that question does its job, the clause fires*
and a successful bounded round always costs one more round by construction.
Scope that extra round to the **delta** (here: the 32 new `tempo="active"`
cells, not all 64). It does not regress infinitely — an enumeration only grows,
and its axis set is bounded above by what the code actually reads, which
`classifier_axes` derives mechanically.

**Two things this rule does NOT do, stated rather than implied:**

1. **It does not help rounds 1-3** — the waste the #601 post-mortem calls the
   real failure. v2 is open, so it promotes; v3 is *also* open, so it promotes
   again, and v3 still runs. The earlier rule's termination at v2 at least
   stopped before v3 — but it did so **correct by accident**, at a price of
   5 HIGH + 2 MEDIUM. Buying v4-v7 back for the cost of v3 is a good trade, and
   it is a trade, not a free win. Nothing here addresses rounds 1-3.
2. **It is not a round cap.** A cap set low enough to have helped #601 also cuts
   rounds 4-7, each of which found something real.

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
  | `never auto-respawned at any age` | **none** — the harness runs a second supervisor this module cannot close | HIGH, round 1 |
  | `(project + label dag:needs-human)` | **none** — nothing in this process writes the label | HIGH, round 1 |
  | its own replacement, `never respawned BY THIS TICK` | **none** — `execute_respawn` did not re-check | HIGH, round 4 |

  Four clauses, one string, one minute of checking. Be precise about what this
  buys: **one finding moves from round 4 to round 1.** The other two were
  already round-1 findings, so Q-CLAIM saves no rounds on them — it makes them
  cheaper to find, not earlier. (Round 2 returned **zero** HIGHs; an earlier
  draft of this table credited two of these to it, which was wrong.) A claim
  with no enforcing call site is the repo's **third** recorded instance of this
  failure class.

  ⚠️ **Why this is a brief question and not an eager rule** — the write-time
  version was proposed and deliberately not adopted (issue #608 §N1), and the
  asymmetry is worth stating because a sibling change in the same batch DID add
  clauses to two eager rules. Those clauses each shipped **with an enforcing
  call site**: `agent-report-persistence.md` rule 5 rides on `session-handoff`'s
  audit step, and the `clarify-before-acting.md` edit was a factual correction
  to a matcher that `hook_selfcheck` asserts. The write-time clause audit has
  **no available enforcing site** — a machine cannot check "does this clause
  have an enforcing `file:line`", which is the whole point of the failure class.
  So it goes where something can actually invoke it: a brief.

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
This round is OPEN HUNTING — it states no domain with a cardinality — so it
CANNOT end the loop by any outcome. It promotes to one bounded round. Report
what you find; do not withhold findings, and do not treat "nothing found" as
completion.

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
This round is BOUNDED — the domain above has a cardinality. **Answering all of
the questions ends the round, regardless of what you find.** Findings are then
dispositioned: fixed in this unit of work, or ticketed. A further round happens
only if dispositioning them CHANGES THE ENUMERATION, and is then scoped to that
delta alone.

## Escape hatch
Out-of-scope defects → ticket recommendation, not a change request.
```

### Stop-condition block (paste into any brief)

```markdown
## Stop condition
This round is BOUNDED / OPEN HUNTING (delete one). A round is bounded only if
the domain above states a CARDINALITY — numbered questions are not an
enumeration, and one catch-all question un-bounds the whole brief.

A BOUNDED round ends when its questions are ANSWERED, whatever it found; a
further round happens only if dispositioning the findings changed the
enumeration, scoped to that delta. An OPEN-HUNTING round cannot end the loop by
any outcome and promotes to one bounded round. Do NOT withhold completion for a
defect that is out of scope for this ticket — recommend a ticket instead.
```

## Judging a brief before you run it

Five checks, in order. Any "no" means fix the brief, not the reviewer.

1. **Can you list what a complete answer consists of?** If not, the brief has
   no co-domain and cannot terminate.
2. **Is there a question aimed at the enumeration itself**, not only at the
   program? Without it the search space is never audited.
3. **Are Q-FRESH, Q-SCOPE and Q-CLAIM present?** An enumeration cannot reach
   any of the three.
4. **Is the stop condition a predicate on COMPLETION** (these questions are
   answered), or on emptiness (nothing was found), or merely permission?
   Emptiness asks the reviewer to prove a negative; permission is not a stop
   condition at all. Both shapes have been tried here and both ship defects.
5. **Does the domain state a CARDINALITY?** If you cannot count the answer set,
   the brief is open hunting however many numbered questions it has.

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
