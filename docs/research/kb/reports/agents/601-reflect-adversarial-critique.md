# #601 reflection — adversarial critique of the five reports

**Agent:** adversarial-critic · **Date:** 2026-08-06 · **Status:** COMPLETE

Attacking five reports before their fixes become durable process debt. Every
claim states its probe and its control arm. Nothing is inherited unlabelled.

## Claim index — all 7 briefed claims RULED, none partial

| Claim | Verdict | Probed? | Where |
|---|---|---|---|
| 1 — cost-analyst's "4 rounds not 7" replay | **DROP the headline** — Gate G passes the shipped table with `tempo` absent; loop-forensics R1 refuted by `8706670` | yes — table + commit body | DROP 2 |
| 2 — "round 3 ships 2 HIGH, not 3" | **CONFIRMED**, both probes re-run independently with control arms; the brief's follow-on gloss inverted | yes — 3 git probes | KEEP §0.2 |
| 3 — R2 "WRONG OR MISLEADING" | **RELABEL** — R2 is correct and silent; rule was misapplied. Convicting phrases are not in R2 (0 hits, control-armed) | yes — verbatim read + armed grep | KEEP (corrected label) |
| 4 — Fix 1b brief-guard feasibility AND value | **DROP** — two independent kills (matcher fires 0/7; predicate passes v4/v5/v6) | yes — corpus grep + live matcher read | DROP 1 |
| 5 — two stopping predicates compatible? | **Not incompatible — non-interacting.** Both detectors are inert behind cost-analyst's own caps | yes — round-number trace | DROP 3 + §5 |
| 6 — SessionEnd cannot host the loop | **CONFIRMED verbatim**, re-derived from `$CC/hooks.md` independently of harness-expert | yes — 2 doc sites | KEEP |
| 7 — was the loop actually justified? | **Team is ~40% wrong.** Rounds 4–7 proportionate; rounds 1–3 are the waste, and no proposed fix targets them | yes — per-round production-delta | §7 |

⚠️ **The branch moved under all five reports.** `git log --oneline
origin/main..HEAD` now returns **10** commits, HEAD `8706670`
(*"add tempo as the fifth axis, and constrain the table's mapping"*).
loop-forensics, rule-coverage and cost-analyst all state 9 commits / HEAD
`eda53d6`; rule-coverage's re-verification section explicitly asserts *"still 9
commits, HEAD eda53d6. Nothing moved under me."* That is now false. The 10th
commit is round 7's fix, and — see §1 — **its commit body is the single most
damaging piece of evidence against the two headline proposals.**

---

## DROP LIST — fixes that would NOT have prevented what they claim to prevent

### DROP 1 — process-designer Fix 1b (`review_brief_stop_condition` hook rule). Two independent kills.

**Kill A — the matcher would have fired on ZERO of the seven actual briefs.**

Fix 1b matches `Write`/`Edit` where `file_path` is `.agent/reviews/*/brief-v*.md`.
The #601 briefs never lived there. The corpus records their real paths verbatim,
inside brief v3 itself (`601-codex-review-rounds.md:637-640`):

```
/private/tmp/claude-501/-Users-rmanaloto-…/99d89987-…/scratchpad/codex-review.md
/private/tmp/claude-501/-Users-rmanaloto-…/99d89987-…/scratchpad/codex-review-v2.md
```

process-designer says so itself (Fix 1a §7): *"all seven #601 briefs lived only
in the ephemeral session scratchpad."* The gate is keyed to a path convention
**the fix is simultaneously introducing**, so it can only fire on an author who
has already complied. Contrast the guard's live rules — `ask_quality` fires on
`tool_name == "AskUserQuestion"`; `branch_guard` fires on any `Write`/`Edit` to
a tracked repo path (`hook_guard.py:791-793`). Both are **unavoidable by
construction**. Fix 1b is **avoidable by default**: write the brief to the
scratchpad — which is where this repo's own scratchpad instruction sends
temporary files — and the gate is silent, with no bad intent required.

**Kill B — the content predicate PASSES exactly the briefs that failed.**

Fix 1b denies when a brief *"lacks a `## Stop condition` heading (or lacks the
literal `ZERO`/`zero` finding-count sentence)"*. Measured against the corpus
(`grep -n -i "zero finding\|clean SHIP\|manufacture"`; control arm — the same
grep also returns v7's genuinely different stop condition, so it is not blind to
the shape it hunts):

| Brief | `zero findings` sentence? | Verbatim | Fix 1b verdict |
|---|---|---|---|
| v2 (`:626`) | no | "Do not manufacture findings to justify a second round." | deny |
| v3 (`:666`) | no — "**no** findings" | "a clean SHIP with **no** findings is an acceptable and useful outcome" | deny |
| v4 (`:853`) | **YES** | "A clean SHIP with **zero findings** is an acceptable and useful outcome." | **PASS** |
| v5 (`:972`) | **YES** | "A clean SHIP with **zero findings** is acceptable and useful." | **PASS** |
| v6 (`:1076`) | **YES** | "A clean SHIP with **zero findings** is acceptable and useful — six rounds in…" | **PASS** |

**Rounds 4, 5 and 6 — the three rounds that produced five HIGHs and the entire
self-feeding cycle — all pass.** The gate fires only on v2 and v3, the two
rounds everyone agrees were cheap.

This is not a tuning problem; the report refutes its own predicate 80 lines
earlier. process-designer's Finding 0, verbatim: *"'v7 said a zero-finding SHIP
was acceptable' — refuted by: so did v3, v4, v5 and v6, verbatim. **Permission
to stop is not a stop condition.**"* Fix 1b then greps for permission to stop.

Under the AND reading (heading **and** sentence) it denies v2–v6 — and is
satisfied by pasting `## Stop condition` above the identical sentence that
failed four times. That is the outcome this repo already documents for shape
gates: `clarify-before-acting.md` on its own citation escape — *"Reaching for it
routinely defeats the gate rather than satisfying it."*

**Feasibility is fine — that is not the objection.** `Write`/`Edit` already reach
the guard (live matcher measured: `Bash|AskUserQuestion|Edit|Write|NotebookEdit`)
and `tool_input` carries `content`, so `ask_quality` is a working precedent for
content inspection. The mechanism works; it just cannot see the property that
mattered. v7's convergence came from its questions having a **finite co-domain**
— a semantic property no heading grep detects.

**Verdict: DROP.** If anything survives, it is Fix 9 (`mise run review-brief`),
which makes the good brief the default path rather than policing the bad one.

---

### DROP 2 — cost-analyst's "4 rounds instead of 7" replay. The record refutes the mechanism.

The replay (§3.2) has Gate G fail after round 2, the author build the 32-row
table, and phase-2 round 1 find `tempo`. Two things break it.

**Break A — Gate G cannot detect a missing axis, and the report knows it.**
Gate G's checks are *(b) row count == product of declared axis cardinalities*
and *(c) a meta-test asserting (b)*. Measured against the table that actually
shipped at `eda53d6` (`tests/test_dag_tick.py:660-674`):

```python
states = [_TERMINAL, "blocked", _OTHER, None]
bools  = [False, True]
assert len(_CLASSIFY_TABLE) == len(expected_cells) == 32   # 4 × 2 × 2 × 2
```

**Gate G passes on that table. `tempo` is absent from it.** cost-analyst concedes
this in §6.1 — *"Gate G checks the table is complete with respect to the axes the
author declared… This is the rule's single biggest hole"* — but §3.2's replay
does not carry the concession forward. The replay's saving throw is entirely
**Q2**, a reviewer's judgement, not the gate. So the honest claim is "a bounded
brief finds the axis in one pass" (true, measured) — **not** "Gate G collapses
the loop" (unsupported).

**Break B — naming the axis does not prevent pinning it, and that is exactly
what happened.** loop-forensics R1 claims a signature-derived axis rule *"names
`tempo` → **F14 dies** at round 7."* The record kills this. At `eda53d6` the
author **had already named `tempo`**, in the table's own comment:

```python
# WEDGED is the one class this table cannot reach, by construction —
# tempo is pinned "idle". Stated so its absence reads as deliberate.
```

And the round-7 fix commit `8706670` states why that reasoning was wrong, in the
author's own words:

> **"Q2 — the axis list was incomplete, and my own reasoning was the defect.**
> I asserted in a code comment, a commit message AND the contract that `tempo`
> 'only matters for WEDGED'. False… **No test could have caught it, because the
> test encoded the same wrong assumption.**"

So: the axis was **enumerated, deliberately pinned, and justified in three
places** — and was still wrong. A rule that produces an axis list does not
prevent an author from pinning an axis out of it with a written rationale.
**R1's "names `tempo` → F14 dies" is refuted by the artifact.** Gate G, which is
strictly weaker than R1, is refuted a fortiori.

The same doubt lands on the replay's premise that a round-2 table would have
contained `queued_prompt`. The demonstrated failure mode of this author, at
round 9 with seven rounds of review context, is *axis-omission-with-
justification*. The prior that they would have included it at round 2 is not
supported by the record; it is contradicted by the nearest available instance.

**Verdict: DOWNGRADE, don't drop.** The phase structure is reasonable. Delete
the "4 rounds instead of 7" headline — it is a replay whose mechanism is
disproved on the same branch — and keep the two things that ARE measured:
Q-FRESH/Q-SCOPE (§3.3, one line each, genuinely absent from v1–v6) and the
bounded-brief result.

---

### DROP 3 — REGRESSION-ECHO is inert under cost-analyst's own stopping rule.

REGRESSION-ECHO is the most carefully measured artifact in the whole set (both
arms fire; v5/v6 YES, v4/v7 NO; the production-vs-test distinction is genuinely
load-bearing and the report caught its own first-pass error). It is also **dead
code inside ENUMERATE-THEN-CLOSE**.

Trace it: phase 1 has a **hard cap of 2 rounds**. REGRESSION-ECHO's stated stop
signal is **two consecutive fires**, which on this record first occurs at v5→v6
— round 6. Phase 1 ended at round 2. In phase 2, cost-analyst states the cap
dominates again: *"with a hard cap of 2 phase-2 rounds, a second REGRESSION-ECHO
fire ships rather than loops."* **Every branch is decided by a round cap before
the detector has data.** Adopt the caps and you never need the detector; adopt
the detector and you don't need the caps. Adopting both makes the detector
decoration that still has to be built and maintained.

Same objection retires process-designer's **Trigger A** ("two rounds find the
same defect shape"), which is Trigger-A-shaped duplication of the same signal at
the same round number, minus the git-blame precision.

**Verdict: pick ONE.** If a non-convergence detector is wanted at all, it should
replace the phase-1 cap, not sit behind it.

---

## KEEP LIST — with corrections

### KEEP (corrected label) — rule-coverage §M1. R2 is not wrong. R2 is SILENT.

I read R2 verbatim from `.claude/rules/probes-need-a-control-arm.md`. Its whole
content is: reintroduce the bug and confirm the check fails; the mutation must
*destroy* what the check looks for (not leave it as a substring); the mutation
must be a break that could really happen. **That is a rule about whether a probe
discriminates. It makes no claim about state-space coverage, and never implies
one.**

§M1's charge is that R2's framing *"encourages reading narrow mutation impact as
good."* The phrases it convicts R2 with — *"and ONLY the race arm"*, *"and
nothing else"* — are **not in R2**. Probe: `grep -rn "and ONLY\|only that
arm\|nothing else"` over both the rule and `docs/rules-evidence/
probes-need-a-control-arm.md` → **0 hits in each**. Control arm: `grep -c
"Reintroduce"` → **1** in the rule, so the probe reads the file. Those phrases
come from the **commit bodies**, authored by the implementer. §M1 attributes to
the rule a framing the implementer invented.

**Why the label matters more than the content.** §M1's *proposed text* is good
and true — a mutation proves the test covers the fix and nothing about what the
fix left uncovered. But the verdict "RULE IS WRONG OR MISLEADING" licenses
**rewording an eager rule that is correct**, and this repo has a scar exactly
there: `verify-before-advancing.md` carries a standing warning that it is *"where
the ≤12,000-char misattribution was born: a real figure … travelled here without
its source, was captioned to Anthropic, and was then machine-enforced against
files its real owner never governed."* Editing a correct eager rule to absorb a
lesson from a different domain is how that happens.

**Corrected verdict: EXISTING RULE IS FINE, RULE MISAPPLIED.** The author treated
a necessary condition as sufficient. Put the coverage lesson where it fires — in
`tests/AGENTS.md`, next to the two anti-patterns it belongs beside — and leave
R2 alone.

### KEEP AND PROMOTE — rule-coverage §T2 + process-designer Fix 7. The only pairing that catches its own motivating defect.

Applying my own test to every proposal, exactly two pass, and they are the two
filed lowest.

| Proposal | Would it have caught F8 (`queued_prompt`, commit 1)? | F14 (`tempo`, round 7)? |
|---|---|---|
| Fix 1b brief guard | no | no |
| Gate G (declared axes) | no — passes a table missing the axis | **no** — measured above |
| REGRESSION-ECHO | no (fires at round 6) | no (correctly doesn't fire on v7) |
| loop-forensics R1 (signature-derived axes, human-applied) | maybe | **no** — refuted by `8706670` |
| **§T2** (meta-test derives axes from the classifier's own reads) | no — needs a table to exist first | **YES** — `classify` calls `is_terminal(state, tempo, …)`, so a signature-derived check fails while `tempo` is pinned |
| **Fix 7 REGISTRY** (a new enum-returning classifier with no table entry FAILS) | **YES** — forces the table at commit 1 | — |
| **§T2 + Fix 7 together** | **YES** | **YES** |

Fix 7's registry forces the table to exist; §T2's derivation forces its axes to
match the code. Neither alone is sufficient; together they are the only
mechanism in the five reports that catches both motivating defects.

**Invert the priority.** process-designer files Fix 7 as EVENTUAL on the ground
that *"the repo has exactly one qualifying classifier today. A gate guarding one
call site is thin."* That is the wrong test. The one call site is `dag_tick.
classify` — the decision core of an unattended watchdog firing 1440×/day — and it
is the exact site that produced every HIGH in this record. A gate that would have
prevented the incident under review is not thin; it is the only fix here with a
positive control arm. Note also that §T2's escape hatch (an explicit exemption) is
a **reviewable diff**, which is this repo's established shape (`bash_budget`'s
allowlist). That is honest teeth, not decoration.

### KEEP — harness-expert's SessionEnd constraint. Verified independently, verbatim.

I re-derived both claims from `$CC/hooks.md` directly rather than through the
report:

- **`SessionEnd` is in the "support `command`, `http`, `mcp_tool` but NOT
  `prompt` or `agent`" list** (`$CC/hooks.md:2999-3015`, alongside `PreCompact`,
  `PostCompact`, `SubagentStart`, `StopFailure`, …).
- **`$CC/hooks.md:2855-2857`, verbatim:** *"SessionEnd hooks have no decision
  control. They can't block session termination… default timeout of 1.5 seconds
  … budget is automatically raised to the highest per-hook timeout configured in
  settings files, up to 60 seconds."*

**CONFIRMED.** The load-bearing constraint holds; the design's shape (tier 1
inside `/clear-prep`) is correctly derived. This is the strongest report of the
five and I found nothing to attack in it.

### KEEP — cost-analyst's §0.2 defect count. Both probes re-run independently.

| Defect | Present at `b9214ad`? | My independent probe |
|---|---|---|
| F8 queued-reply deadlock | **YES** | `git show b9214ad:…/dag_tick.py` → `def is_needs_human(state, needs) -> bool` at `:386`. **Control arm:** at HEAD it is `def is_needs_human(state, needs, *, queued_prompt: bool)` at `:387`, so the probe discriminates. |
| F7 classify→execute race | **YES** | `execute_respawn` at `b9214ad:891` guards on `background_pid_alive(node_id, read_roster(...))` only — roster, never `state.json`. |
| F12 live-PID queued reply | **NO** | `git blame -L 410,425 09d2cb9` → the defective line `:419` (`return state == ESCALATED_STATE and needs is not None and not queued_prompt`) blames to **`09d2cb94` itself**. |

**Confirmed: stopping at round 3 ships 2 HIGH, not 3.**

**But the brief's follow-on inference does not hold.** "The third defect was
manufactured by the loop, so an earlier stop prevents it existing — which
changes the calculus in the rule's favour." It does not, because F12 was
**never shippable**: it existed only in the window between commits 7 and 8 and
was fixed inside the same loop that created it. It is pure loop-internal cost on
one side of the ledger and zero on the other. Meanwhile the defect you get
*instead* of F12 by stopping early is **F8 unfixed** — a permanent recovery
deadlock on `blocked+needs+queued+dead`, strictly worse than the narrow
live-PID cell F12 describes. Counting F12 as "a defect early stopping avoids"
double-counts in the stopping rule's favour. cost-analyst got the direction
right; the brief's gloss inverts it.

---

## §7 — THE PREMISE. The team is ~40% wrong, and it matters.

Argued as strongly as the record allows: **"7 rounds" is not one failure. It is
three wasted rounds bolted onto four correct ones**, and the proposed fixes are
aimed at the wrong half.

**The case that rounds 4–7 were proportionate:**

- The denominator is **451 production lines** rewriting the decision core
  (cost-analyst §0.1, re-derived and correct) — not the brief's "~40-line fix".
- The blast radius is `unattended × irreversible × silent`: launchd at
  `start_interval=60`, issuing `claude respawn`/`claude stop` against live
  workers, 1440 opportunities/day, healthy ticks printing nothing.
- **Every one of rounds 4, 5, 6, 7 found something real.** v4 → a genuine
  pre-existing race. v5 → a genuine pre-existing deadlock + a genuine
  out-of-scope defect (→ #604). v6 → a genuine regression, caught before it
  shipped. v7 → an axis error the author had **reasoned about wrongly and
  asserted in three separate places**.
- Two of those (F7, F8) predate the branch's own fixes and would have shipped
  under any severity-based stopping rule.

**The case for waste is confined to rounds 1–3:** three commits (`cf6e97d`,
`b9214ad`, `397675b`), **zero production change**, written against two `SHIP`
verdicts, chasing a string. That is the real indictment, it is ~40 minutes of
commit cadence, and **not one of the five reports proposes a fix aimed at it.**
The applicable fix is loop-forensics' **R3** (a SHIP with 0 HIGH/0 MEDIUM ends
the loop; LOWs become tickets) — the cheapest proposal in the set, and the only
one that targets the part of the record everyone agrees was waste. It is not in
process-designer's IMPORTANT list at all.

**The consequence for the fix set:** the problem #601 exhibits is a **starting**
problem, not a **stopping** problem. Every stopping rule proposed here, applied
to #601, ships defects — cost-analyst proves this for severity-trend and
concedes it for Gate G's blind spots. The only interventions with a positive
control arm against this record are the ones that force the enumeration **at
commit 1**: Fix 7 + §T2. The loop's length was a *symptom*; the missing table
was the disease; and a stopping rule treats the symptom by shipping the disease.

Honest counterweight: **9 of 15 findings (60%) would not exist without a prior
round's fix**, which is real self-feeding cost. But the HIGH cut is **2 of 7**,
and the LOW-heavy remainder (F4, F5, F6, F11, F13, F15) is largely the prose
loop — rounds 1–3 again. The 60% figure makes the loop look more pathological
than the severity-weighted record supports.

---

## What the repo is ALREADY paying for, in a different form

| Proposal | Already carried by | Assessment |
|---|---|---|
| Fix 3 — "never edit the expected value to make the test pass" | `tests/AGENTS.md` § "What a good test is here" → **Tautological**: *"the assertion recomputes the expected value the way the code does, so it passes by construction"* | **Same anti-pattern, verbatim.** A table-shaped worked instance is defensible; a new paragraph restating it is not. Add ≤2 sentences, or cite the existing bullet. |
| cost-analyst §5 blast-radius tiers | `verify-before-advancing.md`: *"Scale the matrix to the blast radius"* + the conditional check matrix | Prose exists; the **machine-computable predicate** (scheduled-reachable ∧ spawns/stops/deletes) is genuinely new and is the valuable half. Keep the predicate, drop the T0–T3 restatement. |
| Fix 4 — clear-prep fold of review artifacts | `agent-report-persistence.md` **rule 5**: *"`/clear-prep` … requires each findings-bearing one to map to an on-disk artifact"* | Rule 5 already owns the audit. The genuinely new content is **one word: briefs**. The rule names *reports* only, and the briefs were the more valuable half of this corpus. Amend rule 5's scope; do not add a 30-line skill step. |
| Fix 1c — `.agent/reviews/` table row | — | Fine, one row — **but it exists only to support the dropped Fix 1b.** Drop with it unless Fix 9 is built. |
| Fix 6 — `rule-coverage-auditor` agent | `staleness-auditor` (*"is this prose still true"*) | process-designer's distinction (truth-check vs *did-it-fire* counterfactual) is real. But rule-coverage's own §V7 undercuts its author's case: *"the strongest single result in this corpus says prose was not the lever."* An agent whose output is prose recommendations, in a run whose lesson is that prose was not the lever, is a weak second definition. **SUSPECT — one route only.** |

---

## Compatibility of the two stopping predicates (brief item 5)

They do not conflict; they **do not interact at all**, which is the problem.

- process-designer's Trigger A (same defect shape twice) and cost-analyst's
  REGRESSION-ECHO (two consecutive blame-hits) both first fire at **round 6** on
  this record.
- cost-analyst's phase-1 hard cap fires at **round 2** and dominates both.
- process-designer's *other* predicate — the reflect node's "done when every
  finding carries a fix class and the set is closed" — is about a different
  artifact entirely (a reflection's own findings matrix), and touches neither.

**Authoritative where they touch:** cost-analyst's, as process-designer conceded
— but the concession is moot, because under cost-analyst's caps neither detector
ever changes an outcome (DROP 3). **The reconciliation is to delete one layer,
not to rank them.**

---

## Bonus defect found while attacking — evidence FOR rule-coverage §N1

§N1 argues that "prose must not assert an action the code does not perform" is
on its third instance and needs a rule. Here is a **fourth, live, in the guard's
own module docstring**:

`python/src/dotfiles_setup/hook_guard.py:30`, verbatim:

> The settings.json matcher is ``Bash|AskUserQuestion``; dispatch is on ``tool_name``.

Measured from `.claude/settings.json`: the live matcher is
**`Bash|AskUserQuestion|Edit|Write|NotebookEdit`**. The docstring predates the
`branch_guard` wiring (#400) and was never updated, so the module that enforces
this repo's redirect rules misdescribes its own trigger surface — in the file a
future author reads to decide whether a new rule can see `Write`. §N1's case
strengthens from three instances to four, and this one is a two-word fix.

**§N1 verdict: KEEP.** It is the only genuinely new rule proposed, it is on its
fourth instance, and it is cheap.

---

## Final disposition

| # | Proposal | Verdict |
|---|---|---|
| Fix 1b | brief stop-condition hook rule | **DROP** — fires on 0/7 real briefs; passes v4/v5/v6 |
| Fix 1c | `.agent/reviews/` row | **DROP** with 1b, unless Fix 9 is built |
| Gate G replay "4 rounds not 7" | cost-analyst §3.2 | **DROP the headline**; keep Q-FRESH + Q-SCOPE |
| REGRESSION-ECHO | cost-analyst §4 | **DROP or replace the caps** — inert behind them |
| Trigger A | process-designer Fix 2 | **DROP** — duplicates REGRESSION-ECHO at the same round |
| §M1 "R2 is WRONG" | rule-coverage | **RELABEL** — R2 is correct and silent; do not reword an eager rule; place the lesson in `tests/AGENTS.md` |
| Fix 3 | blast-radius reading discipline | **TRIM** — `tests/AGENTS.md` already carries the anti-pattern |
| Fix 4 | clear-prep step 3d | **TRIM to one word** — amend `agent-report-persistence.md` rule 5 to name *briefs* |
| Fix 6 | `rule-coverage-auditor` | **SUSPECT** — defer |
| §N1 | claims-must-name-a-call-site | **KEEP** — now 4 instances incl. `hook_guard.py:30` |
| **§T2 + Fix 7** | axis derivation + classifier registry | **KEEP and PROMOTE to IMPORTANT** — the only pairing that catches both motivating defects |
| R3 | SHIP with 0 HIGH/0 MED ends the loop | **KEEP — and it is missing from the IMPORTANT list.** The only fix aimed at rounds 1–3, the only rounds that were unambiguously waste |
| harness-expert's constraints | SessionEnd / tier 1 in `/clear-prep` | **KEEP** — re-verified verbatim |

**Net:** of the IMPORTANT set as proposed, I would apply **one item unchanged**
(nothing), trim three, drop three, and promote two currently filed EVENTUAL.

---

## What I could not settle

- **Whether a round-2 table would have contained `queued_prompt`.** I established
  the author's demonstrated failure mode is axis-omission-with-justification
  (`8706670`, `tempo`), which makes the replay's assumption unsupported — but
  "unsupported" is not "refuted". A second instance would settle it; one exists.
- **§T2's false-positive rate.** Deriving axes from a classifier's transitive
  reads will pull in fields that genuinely do not change the outcome. I did not
  prototype it. The exemption-as-reviewable-diff shape mitigates but does not
  measure this.
- **Whether the 10th commit (`8706670`) changes any sibling report's numbers
  beyond the commit count.** I checked its effect on the axis argument only.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under critique: `git log`/`show`/`blame` over `origin/main..HEAD` (10 commits), `.claude/rules/`, `.claude/settings.json`, `python/src/dotfiles_setup/hook_guard.py`, `tests/AGENTS.md`, `tests/test_dag_tick.py`, and the five sibling reports.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline `agent-harness-docs` corpus (`$CC/hooks.md`), used to re-derive the SessionEnd hook-type exclusion and timeout budget independently of harness-expert's report.
