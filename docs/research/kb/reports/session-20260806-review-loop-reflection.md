# Why #601 took 7 review rounds — and what to actually change

**Session 2026-08-06 · self-reflection pass · 6 agents · PRESCRIPTIVE**

Corpus: `agents/601-codex-review-rounds.md` (7 reports + 7 briefs, verbatim).
Agent reports: `agents/601-reflect-{loop-forensics,rule-coverage,cost-stopping-rule,harness-feasibility,process-design,adversarial-critique}.md`.

---

## VERDICT — the framing was wrong, and the fix list is mostly not what it looked like

**#601 is a STARTING problem, not a stopping problem.** Every stopping rule the
team proposed, replayed against this record, **ships defects**. The interventions
that work force the enumeration *at commit 1* — and both were filed EVENTUAL.

Three corrections to what this session believed while it was happening:

| Believed during the session | Measured afterwards |
|---|---|
| "a ~40-line correctness fix" | **1,465 insertions, 451 production.** The FIRST commit was 164 production lines. There was never a small version to over-review. |
| "7 wasted rounds" | **3 wasted + 4 proportionate.** Rounds 4–7 each found something real against a 451-line rewrite of an unattended watchdog. Rounds 1–3 produced 3 commits and **zero production change**. |
| "3 HIGHs, each caused by the previous fix" | **2 were pre-existing** and ship under any severity rule. Only the third was loop-manufactured (`git blame` puts it in `09d2cb9`, the fix for v5). |

**The waste is rounds 1–3, and not one of the five reports proposed a fix aimed
at it.** Those rounds chased a *string* — three commits against two `SHIP`
verdicts, no production change.

### The single sharpest datum in the whole corpus

`Node.queued_prompt` and `is_terminal(state, tempo, *, queued_prompt)` exist on
**`origin/main`**, before this branch was cut (`dag_tick.py:195`, `:262`). The
census path already populated `queued_prompt=bool(data.get("queuedPrompt"))`.

Commit 1 then wrote `def is_needs_human(state, needs)` — **a sibling predicate
over the same `Node`, omitting an axis its own sibling two functions above
already consumed.**

That one missing parameter is F8 (HIGH, round 5) and transitively F12 (HIGH,
round 6, only reachable because F8's fix opened it). **Two of the three real
behavioural HIGHs, and two entire rounds, from one omission visible in the
adjacent function signature.**

### And the dominant failure is not the self-feeding cycle

Of the 7 HIGHs: **2** were genuinely un-findable earlier, **2** were in commit
1's log string and auditable the minute it was written, and **3 were reachable
from round 1** — surfacing later *purely because the brief finally asked the
right question*. Commits 2–5 never touched `execute_respawn`.

> **The dominant failure is four rounds of briefs asking the wrong question
> about code that had not moved.**

**Both sub-loops terminated by STRUCTURE, never by care** — loop A when
substring guards were abandoned for golden equality, loop B when cell-patching
was abandoned for the enumeration. Neither ended with a more careful patch.

---

## The mechanism — why v7 converged and v1–v6 did not

Four obvious explanations were refuted before the real one:

> **"a clean SHIP with zero findings is acceptable" appears verbatim in briefs
> v3, v4, v5 AND v6.** Four rounds carried it; three still returned DO NOT SHIP.
> **Permission to stop is not a stop condition.**

The actual difference is the **shape of the question**:

- **v1–v6 asked a SEARCH question over an open domain** — "what is broken?"
  No answer means *keep looking*. Termination is never reached, only conceded.
- **v7 asked a VERIFICATION question over a finite enumerated domain** —
  3 questions over 32 cells / 4 axes / 2 meta-tests. **Answering them IS
  completion.**

Two consequences, both visible in the record:

1. v7 found an **axis** because Q2 asked about the *enumeration*, not the
   program. In six rounds nobody was ever asked whether the search space was
   the right space.
2. v7's escape hatch routed out-of-scope findings to **a ticket, not another
   commit** — the mechanical break in the fix→next-defect cycle.

⚠️ **But naming an axis does not prevent pinning it.** `tempo` WAS named — in
the 32-cell table's own comment (*"tempo is pinned 'idle'. Stated so its absence
reads as deliberate"*). The author wrote a rationale for excluding it and was
wrong in three places at once. The saving throw was Q2 — a reviewer's judgement,
**not a gate**. Any proposal claiming a gate would have caught it is overclaiming.

---

## APPLY NEXT SESSION (post-critique — nothing survives unchanged)

### A1 · `tests/AGENTS.md` — the coverage lesson, ≤4 sentences
Beside the two existing anti-patterns. Content: *testing both arms of the
condition you changed is not coverage; enumerate every axis the condition
INTERACTS with.* Plus: **never edit an expected value to make a test pass** —
that converts an independent expectation into a transcription of behaviour.
**Why here:** `nested` load class, edited in 7 of 9 commits so it was loaded for
nearly the whole loop, **zero eager cost**. Measured headroom: 4,888 B under the
12,000 AGM-003 cap.

### A2 · Promote **§T2 + Fix 7** from EVENTUAL — the only pairing with a positive control arm
- **§T2** — derive a classifier's axes from *its own reads*, with this literal
  definition (loop-forensics R1, and the precision matters — it is
  signature-derivable with **zero judgement**):

  > **The axes are the union of `classify()`'s parameters and every `Node` field
  > read by any predicate it calls.**

  Applied at commit 1 this names `queued_prompt` (F8 dies, F12 never exists,
  rounds 5 and 6 collapse) and names `tempo` (F14 dies at round 7). It shipped
  anyway as commit 9 — **eight commits late**. Cost: ~30 lines.
- **Fix 7** — a `classifier_tables.py` registry + cardinality gate, modelled on
  `bash_budget.py`: forces the table to EXIST at commit 1, which catches
  `queued_prompt`.

Neither alone suffices; **together they are the only mechanism in all five
reports that catches both defects.** Fix 7 was deprioritised as "guarding one
call site" — that call site produced every HIGH in this record.

### A2b · Two brief questions an enumeration CANNOT replace
**Gate G is blind to temporal defects** — round 4's classify→execute race is not
a cell in any state table, and no enumeration would have found it. Two one-line
additions to every open-hunting brief, neither present in v1–v6:

- **Q-FRESH** — *"for every decision→action pair, is the decision re-validated
  against freshly-read inputs immediately before the action?"* Kills F7 at
  round 1.
- **Q-SCOPE** — *"is this defect in scope for this ticket, or a sibling?"*
  Round 5's `execute_stop` finding (→#604) cost a round of attention to scope out.

### A2c · Operator-string clause audit (loop-forensics R2)
**Every clause of an operator-facing string is audited against an enforcing
`file:line` at write time; a clause with no enforcing line is deleted or
narrowed before commit.** Kills F1, F2 **and F7** — `never respawned BY THIS
TICK` had no enforcing line in `execute_respawn`, which is precisely why it was
false. A one-minute check that waited until round 4. **Loop A never starts.**

### A3 · loop-forensics **R3** — the cheapest fix, and the only one aimed at the real waste
**A review round returning SHIP with 0 HIGH and 0 MEDIUM ends the loop; LOWs
become tickets.** Applied to this record it ends the loop after v2 — killing
exactly rounds 1–3, the wasted ones — and does not touch rounds 4–7, which
were proportionate. It was absent from the IMPORTANT list.

### A4 · `.claude/skills/adversarial-review/SKILL.md` (new) — a skill, not a rule
The round ladder (round 1 open hunting is legitimate; round 2+ bounded), the
three questions stated generically, the stop-condition and escape-hatch
templates, and — load-bearing — **the finite-co-domain property**: a bounded
brief asks questions whose answer set is enumerable, not "what is broken".
Behaviour-triggered but niche ⇒ a skill (`md-size-budgets.md`). **Zero eager cost.**

### A5 · `agent-report-persistence.md` rule 5 — amend scope by ONE WORD
Add **"briefs"**. All 7 briefs existed only in the ephemeral scratchpad; the
rule already makes `/clear-prep` audit artifact coverage. This is a one-word
amendment, not a 30-line skill step.

### A6 · `hook_guard.py:30` — a 2-word docstring fix, and a live defect
It says the matcher is `Bash|AskUserQuestion`. Measured from `.claude/settings.json`
it is **`Bash|AskUserQuestion|Edit|Write|NotebookEdit`**. The module enforcing
this repo's redirect rules misdescribes its own trigger surface — in the file
you would read to decide whether a new rule can see `Write`.

### A7 · `command_audit.py` — subagent transcripts are invisible to it
`project_transcripts()` globs `*.jsonl` **non-recursively** and never descends
into `<session>/subagents/`. Every teammate transcript is on disk at
`~/.claude/projects/<encoded-cwd>/<session-id>/subagents/agent-a<name>-<16hex>.jsonl`.
**The existing self-learning loop sees zero subagent activity today.**

---

## FILE AS ISSUES (eventual)

1. **`reflect` DAG node type** on map #556 — tier 2 (below).
2. **`mise run review-brief`** renderer — makes the good brief the *default path*
   instead of policing the bad one.
3. **`.claude/agents/rule-coverage-auditor.md`** — SUSPECT, file rather than
   build: rule-coverage's own §V7 undercuts it (*"prose was not the lever"*).
4. The `probes-need-a-control-arm.md` §N1/§N2 additions (claims-need-a-call-site;
   reachability-delta) — small, but they are prose, and prose was not the lever.

---

## DROPPED, with the reason (do not resurrect without reading this)

| Proposal | Why dropped |
|---|---|
| **Fix 1b** — hook rule denying a round-≥2 brief with no `## Stop condition` | Fires on **0 of 7** real briefs (they lived in the scratchpad; the gate keys on a convention the fix is itself introducing). Worse: its content predicate **PASSES v4/v5/v6** — the three rounds that produced 5 HIGHs — and denies only v2/v3, the cheap ones. It greps for *permission to stop* 80 lines after proving permission is not a stop condition. |
| **"4 rounds instead of 7"** headline | Gate G **passes** the 32-cell table with `tempo` absent (32 == 4×2×2×2). The replay's saving throw is a reviewer's judgement, not the gate. Keep the phase structure; delete the number. |
| **REGRESSION-ECHO + Trigger A** | Both first fire at round 6; the phase-1 cap fires at round 2 and dominates. Inert by construction. |
| **"R2 is WRONG OR MISLEADING"** | **Misapplied, not wrong.** The phrases it was convicted with are not in R2 (`grep` → 0; control → 1, so the probe reads) — they are from the implementer's own commit bodies. Rewording a correct eager rule is the exact scar `verify-before-advancing.md` carries. **⚠️ The LABEL is dropped; the insight underneath it is NOT — see below.** |
| **REGRESSION-ECHO detector** (fire when a finding blames to the previous fix) | Both arms fire correctly (v5, v6 — exactly the two non-convergent rounds), but it **first has data at round 6**, while the phase-1 round cap fires at round 2 and dominates every branch. Inert by construction alongside a cap. ⚠️ Its load-bearing detail is worth keeping if it is ever revived: **restrict to PRODUCTION line cites** — counting all cited files ranks v7 *highest*, and v7 is the round that converged. |

---

## Tier 1 — `/clear-prep` integration

⚠️ **It CANNOT be a `SessionEnd` hook.** Re-derived from `$CC/hooks.md`:
`SessionEnd` supports only `command`/`http`/`mcp_tool` — **not `agent`**
(`:2999-3015`); hooks share a **1.5 s** budget raised only by settings-file
timeouts, hard ceiling **60 s** (`:2857`); and it has **no decision control**
(`:2855`). A `type:"agent"` hook spawns **ONE** subagent, ≤50 turns, returning
only `{ok, reason}` — a gate, not a producer — and is marked EXPERIMENTAL.

**So tier 1 is a step in the `/clear-prep` SKILL**, which runs inside the live
session: no time budget, the real `Agent` tool, and access to both transcript
layers. Strictly better than any hook trigger.

**The step does NOT run the reflection inline.** It measures the loop, folds
briefs+reports verbatim into the tracked bundle, and **files a `dag:reflect`
ticket when a trigger fires**.

## Tier 2 — the `reflect` DAG node type (#556)

- **Inputs:** review artifacts, the branch diff, `<session>/subagents/*.jsonl`.
- **Trigger:** ≥2 review rounds on one unit of work, OR a round finding a defect
  introduced by the previous round's fix.
- **Terminal reasons** (#575's taxonomy): `Succeeded` · `Failed` · `NeedsHuman`
  (a finding needing a human ruling) · `Stalled` · `CanceledByReconciliation`.
- **Best native trigger:** `TaskCompleted` — fires when an agent marks a task
  complete, carries `task_id`/`teammate_name`, exit 2 blocks completion.
  ⚠️ **No matchers** — scoping must live in the hook body.
- Teammates keep all `Task*`/`Cron*` tools, which is what makes tier 2 viable.

## Which roles earn a durable definition — **2 of 6, not 6 of 6**

| Role | Verdict |
|---|---|
| `claude-code-expert` | **Already exists.** Produced the decisive constraint. Add nothing. |
| `rule-coverage` | **Earns one** — distinct from `staleness-auditor` ("is this prose true" vs "did this rule FIRE, and if not why"). ⚠️ Filed as an issue, not built: its own §V7 says prose was not the lever. |
| `adversarial-critic` | **Earns one.** It overturned the majority of the team's proposals; without it this document would have prescribed a gate that fires on none of its own motivating cases. `model: opus`, `effort: high`. |
| loop-forensics · cost-analyst · process-designer | **No** — the first is a section of the reflect node's work, the second's discipline is already an eager rule, the third *is* the reflect node. |

---

## ⚠️ The mutation-testing signature that meant the OPPOSITE of what I thought

Dropping the "R2 is wrong" *label* does not drop this, and it is the most
counter-intuitive thing in the corpus. Every fix this session was
mutation-verified, and I wrote the result up as **quality evidence**:

- `8c87eec` — *"deleting the re-check fails the race arm **and ONLY the race arm**"*
- `796777a` — *"deleting the REPLY_QUEUED wiring fails the visibility arm … **and nothing else**"*

All three such fixes **directly caused the next round's HIGH.** R2's mutation
standard was met 100%, with **zero predictive power**.

> **"Deleting the fix breaks only the arm you just wrote" is the SIGNATURE OF
> THE FAILURE, not evidence of quality.** It means test space and fix space are
> the same size — which is exactly the condition under which an unenumerated
> neighbouring cell exists.

The rule is correct and silent on this; the evidence file's two expansions are
both *"mutation too weak to bite"*, never *"mutation complete but irrelevant"*.
**Put this in `tests/AGENTS.md` with A1 — do not reword the eager rule.**

## The other measured facts worth not re-deriving

- **21 of 23 rules are eager**, and **every gate was green on all 9 commits**
  (lint 0 · pytest 1369→1453 · verify 115/0) while 4 of 7 rounds returned DO NOT
  SHIP. The gates and the rules were not the missing layer.
- **Cost: contiguous work ≥1h21m, span ≤11h17m** (two long gaps are almost
  certainly sleep). Reported as an interval, not a point estimate. Tokens,
  reviewer latency and reading time are **not measurable** from artifacts.
- **The v7 diagnosis was legible in brief v6**, which already asked *"what did
  `09d2cb9` break?"* — the **cell-level** question. Round 6 duly returned the
  next cell. The step to *"what is the SPACE of things a fix can break"* is one
  inference, and it cost a round and a HIGH.
- Failure class 4 (a claim with no enforcing call site) is on its **third**
  recorded instance — `secrets-out-of-the-shell-env.md` documents it twice and
  still did not promote it to a directive.

## The single most reusable finding

**A review's productivity is a property of its BRIEF, not of its reviewer.**
The same reviewer, same corpus, same model produced six inconclusive rounds and
then one decisive round — the only variable that changed was whether the question
had a finite co-domain. Any future adversarial pass should be judged on that
property before it is run, not on its findings after.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under reflection; #601, #602, #604 and map #556.
