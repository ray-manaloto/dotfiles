# The eight briefs — #601 post-mortem fix list, 2026-08-06

Persisted per `.claude/rules/agent-report-persistence.md` rule 5, **as amended
by this very batch** (`f775f93`) to cover an agent's brief and not only its
report. #601's seven review briefs lived in an ephemeral scratchpad and are
unrecoverable; the post-mortem's headline finding is that *a review's
productivity is a property of its BRIEF*, so the artifact that decides whether a
round was worth running was exactly the one nothing persisted.

The reports these produced are the sibling files in this directory:
`adversarial-critic-601-fixlist.md`, `staleness-auditor-post-601-batch.md`, and
the per-agent reports under the session scratchpad folded into the receipts.

**Condensation notice, stated rather than implied:** the briefs below are
reproduced in full for their operative content — the task, the constraints, the
acceptance bar and the required arms. The boilerplate preamble repeated verbatim
in each (scratchpad path, "do not write inside the repo", "do not run
`mise run lint`", "write `report.md` incrementally", "SendMessage last") is
stated once here and elided from each brief. Nothing that shaped a finding has
been dropped.

## The shared preamble (in all four builder briefs)

1. **DO NOT WRITE ANYWHERE INSIDE THE REPO.** A `ship` was in flight on the
   parent branch and a PreToolUse guard blocks repo writes. Everything goes to
   `<scratchpad>/team/<agent>/`.
2. **DO NOT run `mise run lint` / `hk`** — hk locks were held by the in-flight
   ship. `ruff check` and `pytest` were permitted (read-only).
3. **Write `report.md` INCREMENTALLY** from the first minutes. *"Agents on this
   project have died at ~40 min and left nothing."*
4. **End with SendMessage to `main`.** *"Your final text goes NOWHERE."*
5. `graphify query` for orientation before broad greps.
6. Deliver `APPLY.md` with a **unique anchor** per edit — *"an edit without a
   unique anchor cannot be applied."*

---

## 1 · `classifier-gate` — build A2 / "Fix 7"

Build `python/src/dotfiles_setup/classifier_tables.py`, **modelled closely on
`bash_budget.py`** (a declarative registry, a pure `find_violations(repo_root)`,
a thin `*_main` CLI entry, and a **stale-entry kind so the map cannot rot**).

Context given: `classify(node, *, pid_alive, state_age_s)` dispatches through
predicates reading fields off a `Node`. #601 burned four rounds on one root
cause twice — commit 1 wrote `is_needs_human(state, needs)` while
`is_terminal(state, tempo, *, queued_prompt)` sat two functions above it already
consuming an axis the new predicate omitted; then round 7 found the same shape
with `tempo`, pinned on a premise asserted in a comment, a commit message AND a
contract, wrong in all three. *"No test could catch it, because the test encoded
the same wrong assumption."*

The definition to implement, verbatim and non-negotiable:

> **The axes are the union of `classify()`'s parameters and every `Node` field
> read by any predicate it calls.**

Required: `derive_axes` via `ast`, following calls transitively; violation kinds
`undeclared` / `phantom` / `stale` at minimum; a CLI subcommand wired the way
`bash-budget` is; an hk step mirroring `bash_logic_budget`; tests in the repo's
style with **no inline suppressions**; `tests/test_dag_tick.py` changed so its
axis lists are **derived from the registry** rather than restated; and a
`suites.toml` contract mirroring `workflow.bash-logic-enforcement`.

**The acceptance bar — stated as a VERIFICATION question with a finite answer
set, not as "build a gate":**

- **Arm A (positive control, the real defect):** against `dag_tick.py` as it was
  at commit 1 — reconstructed with `git show e9da8cb`, not approximated — the
  gate must FAIL and name `queued_prompt`.
- **Arm B:** with `tempo` removed from the declared axes, FAIL naming `tempo`.
- **Arm C (negative control):** against HEAD with a correct registry, PASS.
- **Arm D (realism):** *"the mutation must be a break that could REALLY happen —
  deleting a wiring line or omitting a parameter, not renaming a symbol (a
  rename leaves the original as a substring and makes substring checks
  no-ops)."*

⚠️ Two framing constraints that produced the two best findings:

> *"Do not report a clean single-arm mutation as proof. **"Deleting the fix
> breaks ONLY the arm you just wrote" is the SIGNATURE OF THE FAILURE, not
> evidence of quality** — it means test space and fix space are the same size.
> Report what ELSE your gate would catch, and — honestly — what it would not."*

> *"**A gate that would not have caught its own motivating defect is
> rejected.** Before you finish, replay your gate against BOTH #601 defects and
> say plainly whether it catches each."*

### 1b · Follow-up: the honest-limitations gap and the missing `unlisted` kind

> *"Six arms that all fire correctly is precisely the shape that reads as proof
> and isn't."* Required: what defect class the gate structurally cannot see;
> whether derivation follows calls transitively past one level; behaviour on
> `getattr`, dicts, comprehensions, cross-module helpers; behaviour on a field
> read in a dead branch.

> *"`bash_budget`'s FIRST mechanism is that the allowlist gates NEW files. All
> five of your kinds presuppose an entry exists — so a second classifier added
> tomorrow is invisible, and the registry never grows. Is a sixth kind cleanly
> decidable? **If it is not, say so and do not build it** — a heuristic that
> misfires on ordinary functions is worse than nothing. Either answer is fine; I
> need the reasoning, not a yes."*

### 1c · Follow-up: build `unlisted`, register `branch_guard:classify`

Ray's ruling. The measurement that earned it: 2 hits / 0 false positives across
45 modules. Specific instructions:

- The modelling call on `lines: list[str]` is *"the part I want you to DECIDE and
  DEFEND, not guess"* — if it cannot be modelled as a finite axis, **pin it with
  a written reason and let `illegal_pin` judge the pin**.
- Build the missing truth table; **do not transcribe expected values off a run**.
- ⚠️ *"Its docstring claims one case 'cannot be produced by any real git.' That
  is an unenforced reachability claim — treat it as a claim to be VERIFIED, not
  a premise. If the case turns out reachable, that is a finding and I want it
  flagged loudly."*

### 1d · Follow-up: the two review HIGHs

**HIGH A (cold review):** *"It does not fail silent. It fails LOUD IN THE WRONG
DIRECTION"* — an added `n = node` makes derivation emit a `phantom` telling the
author to delete the still-live declarations. *"A miss is a gap; a confidently
inverted instruction is a trap, and it lands on the fixture that IS the
motivating defect."* Required: propagate subject-hood through aliasing and
enumerate the forms covered and not covered; **`phantom` must be withheld
whenever the walk hit anything it could not resolve** — *"'declared but unread'
is only sound if the walk saw everything."*

**HIGH B (adversarial critic):** `illegal_pin` fails open on 4 of 7 return
shapes. *"F is the kill — `if tempo == "active": return WEDGED else: return
DONE` is round 7's own premise written with an `else`."* Required: **fail
CLOSED** at the point where "I found nothing" currently becomes "nothing gates
anything". Plus a prose correction to a claim that overstated its own replay.

---

## 2 · `live-defects` — A5 / A6 / A7

Three already-diagnosed defects, each with its evidence supplied and each with
an instruction to **verify rather than accept**:

- **A5** — `agent-report-persistence.md` rule 5 audits reports only; amend to
  cover briefs. *"This is a one-word / one-clause amendment, not a new rule
  step — resist expanding it. Check whether `clear-prep/SKILL.md` also needs a
  matching line for the rule to actually bind; a rule whose enforcing step does
  not mention briefs is a claim with no enforcing call site."*
- **A6** — the stale PreToolUse matcher docstring. *"**Verify this yourself
  against `.claude/settings.json` and quote the actual value** — do not take my
  word for it, and if I am wrong, say so."* Plus: find every other occurrence.
- **A7** — the non-recursive transcript glob, with the measured control arm
  (214 vs 2,172) supplied. Required to answer explicitly: does pulling in 10×
  the files silently change what `limit` means; does anything downstream assume
  one file == one session; **are subagent transcripts the same JSONL schema —
  "verify empirically against a real subagent transcript on disk, do not
  assume"**. The test *"must have a control arm: it must FAIL against the old
  non-recursive glob."*

---

## 3 · `review-doctrine` — A1 / A2c / A4 / A4b

The doctrine layer, with the size budgets supplied and one inherited number
corrected in the brief itself (*"the handoff called 4,888 the headroom; it is
the file size"*).

The load-bearing instruction, and the one that produced the session's most
valuable refusal:

> *"You must decide where A2c goes and justify it... The post-mortem separately
> lists two OTHER additions under **FILE AS ISSUES, do not apply** — with the
> reason 'they are prose, and prose was not the lever'. Read that tension
> carefully and tell me honestly whether A2c collides with it. **If you conclude
> A2c should also be filed rather than applied, say so** — I would rather have
> the right answer than the assigned one."*

For A4, the skill: the round ladder, the stop condition, the finite-co-domain
property, *"permission to stop is not a stop condition"* (with the verbatim
evidence that the reassurance appears in briefs v3–v6 and three still returned
DO NOT SHIP), Q-FRESH and Q-SCOPE, the ticket escape hatch, and templates.

For A4b, the agent: *"read `agent-report-persistence.md` rule 1b — the
definition must itself carry the incremental-persistence + deliver-before-idle
requirement, because a rule nothing pushes into the prompt is not a layer."*

---

## 4 · `issue-filer` — the four eventual issues

Read #602/#604 for house style; create four issues; link each as a sub-issue of
map #556 and **prove it with a control arm** (*"confirm a number you did NOT add
is absent from the list, so the probe is shown to discriminate"*).

Issue 3 was briefed to be filed **as SUSPECT, deliberately not built**, carrying
its own undercutting evidence: *"the agent that proposed it undercuts it in its
own §V7 — 'prose was not the lever'"*, plus the measurement that 21 of 23 rules
are eager and every gate was green on all 9 commits while 4 of 7 rounds returned
DO NOT SHIP.

---

## 5 · `cold-review` — round 1, cross-family (codex)

Written from the round-1 template of the skill this batch ships — the first
dogfooding of it.

> **Read the code; do not read the tickets, the commit bodies' claims, or the
> post-mortem before forming your own view. Design context primes happy-path
> confirmation — that is why you are the cold lens.**

Question: *"What in this diff is wrong?"* Plus Q-FRESH, Q-SCOPE and Q-CLAIM,
each required to be answered explicitly even if the answer is "none", with
Q-CLAIM flagged as *"the single highest-yield question against this diff."*

Four risk areas named, with the framing *"not a list of what to confirm — a list
of where I believe the risk is. Look elsewhere too."* Area 1 supplied a defect
already found and fixed during development and instructed: *"assume there are
siblings of that bug and go find them."* Area 3 asked whether deriving test axes
from a registry **makes any assertion tautological**.

Stop condition and escape hatch stated verbatim from the skill.

---

## 6 · `design-critic` — the first invocation of its own definition

> *"You are the first invocation of your own definition — it landed in commit
> `47eb739`. Read `.claude/agents/adversarial-critic.md` and hold yourself to
> it."*

Five proposals, each with the specific thing to test it against, and the
governing question: **would this proposal have caught its own motivating
defect?** Explicitly asked to attack the gate's own `illegal_pin` (*"is it the
thing it convicts others of?"*), to replay the shipped stop condition against
the real verdict table, to check whether each of Q-FRESH/Q-SCOPE/Q-CLAIM would
actually have surfaced its named finding, to judge whether the `tests/AGENTS.md`
prose escapes *"prose was not the lever"*, and to **attack the reasoning used to
DROP A2c**.

Method requirements: replay against the real record not the proposal's
description of it; cite `file:line`; distinguish *"this proposal is wrong"* from
*"this proposal is right but its stated justification is wrong"*; and —

> *"If a proposal survives, say so plainly. **A critic that can only convict is
> a probe with one face.** I would rather have four survivals and one real kill
> than five hedged verdicts."*

### 6b · Follow-up: replay the replacement stop condition

Supplied my diagnosis (the rule conflates a prescription with a fact about the
round that ran) and my proposed replacement (completion by answering, not by
emptiness), then: *"Replay it and tell me if it also ships defects."* Four
numbered questions with the instruction *"**the 'enumeration changed' clause is
the dangerous one** — attack that hardest"*, and *"does it help rounds 1–3? I
suspect not... If that is right, say so plainly and I will state the residual
openly rather than imply coverage."*

---

## 7 · `prose-audit` — staleness after the batch

Five changes of ground truth enumerated, with the constraint that
`docs/research/kb/reports/**` is persisted verbatim output and must be reported
as informational only.

The question flagged as the one most cared about: does any newly-added prose
**contradict existing prose** — specifically whether the new `tests/AGENTS.md`
anti-pattern sits consistently beside `probes-need-a-control-arm.md`, which
prescribes mutation testing. *"I believe they are compatible... but I want that
checked, not assumed, because a reader who takes them as contradictory will
discard one."*

Control-arm requirement: *"before reporting that a stale claim appears nowhere,
run the same grep shape against a term you KNOW is present. **Invent the
known-absent control term fresh; do not reuse one from a prior receipt.**"*
Cleared checks were required to be reported: *"a report listing only hits gives
me no way to tell coverage from luck."*

---

## 8 · `ship-advisor` — the commitment boundary

The situation, round 1's full findings, and the decision:

> *"Is continuing to fix-and-re-review this batch the correct move, or am I now
> reproducing the exact failure the batch exists to prevent?"*

Four considerations supplied with the instruction to say **which risk
dominates**, and one calibration constraint:

> *"I have already been wrong once today in exactly the 'I fixed it, here is the
> clean control arm' shape. Weight my confidence accordingly."*

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under change; #601, #602, #604, #605-#608, map #556.
