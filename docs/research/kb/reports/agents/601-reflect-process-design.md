# #601 — process design: the fixes, ready to apply

**Agent:** process-designer · **Status:** COMPLETE · **Date:** 2026-08-06

Corpus read in full: `docs/research/kb/reports/agents/601-codex-review-rounds.md`
(all 7 reports **and** all 7 briefs, 1179 lines), the 9 commits on
`fix/601-dag-tick-needs-human`, the current `tests/test_dag_tick.py`
`_CLASSIFY_TABLE` region, `.claude/skills/clear-prep/SKILL.md`,
`.claude/agents/*.md` (3), `docs/receipts/575.md`, `hk.pkl` step shapes, and the
four sibling drafts as they landed.

Every fix below states **the file**, **the change**, **the evidence**, and
**whether it adds prose or teeth**.

---

## Finding 0 — what EXACTLY made v7 different (the primary datum)

I compared briefs v1–v6 against v7 clause by clause. Five of the six candidate
differences are cosmetic; **one is the mechanism**.

### The differences that are NOT the cause

| Candidate explanation | Refuted by |
|---|---|
| "v7 said a zero-finding SHIP was acceptable" | So did **v3, v4, v5 and v6**, verbatim: *"A clean SHIP with zero findings is acceptable and useful. Do not manufacture findings."* Four rounds carried that sentence; three of them still returned DO NOT SHIP. **Permission to stop is not a stop condition.** |
| "v7 was shorter / more focused" | v6 was equally specific — five numbered attacks, each naming a concrete mechanism. Specificity of *attacks* did not converge it. |
| "v7 named the loop's failure mode" | Necessary framing, but v6 named it too (*"v5's HIGH 1 was introduced by the fix for v4's HIGH — so hunt what `09d2cb9` broke"*) and still produced a cell-level HIGH. |
| "v7 forbade re-reporting old findings" | v2–v6 all did (*"do not restate their findings"*). |
| "v7 gave an out-of-scope escape hatch" | Contributory, not sufficient — see below; it breaks the *cycle*, not the *search*. |

### The difference that IS the cause

**v1–v6 asked a SEARCH question over an open domain. v7 asked a VERIFICATION
question over a finite enumerated domain.**

- *Search* — "find what is wrong". The co-domain is the set of all defects:
  unbounded, unenumerable. **No answer means done.** The only terminating answer
  available was "I failed to find anything", which an adversarial reviewer is
  explicitly instructed not to produce.
- *Verification* — "here are 32 cells, 4 axes and 2 meta-tests; are the cells
  right, are the axes complete, do the meta-tests hold". Each question has a
  finite domain and a definite answer. **Answering all three IS completion.**

Two consequences follow directly, both visible in the v7 report:

1. **It found an AXIS, not a CELL.** Q2 — *"are the four axes the right axes — is
   there a fifth?"* — is a question **about the enumeration**, not about the
   program. v1–v6 could only ever find cells, because every question they asked
   was about a behaviour, and a behaviour is a cell. Nobody was ever asked
   whether the space being searched was the right space. `tempo` sat there for
   six rounds and fell out in one pass the moment someone asked.
2. **The escape hatch routed OUT of the loop.** v7's closing paragraph: anything
   genuinely HIGH but outside the three questions *"will become a ticket rather
   than another commit on this branch."* That is the mechanical break in the
   fix→new-defect cycle — a finding no longer implies a commit, so a finding
   cannot manufacture the next round's defect.

**The reusable law, stated once:** an adversarial review converges when the
artifact under review is an **enumeration** and the brief asks whether it is
(a) correct in its cells, (b) complete in its axes, (c) honestly checked. It does
not converge when the artifact is a **diff** and the brief asks what is wrong.

---

## IMPORTANT — apply next session

### Fix 1 — the review-brief contract → a SKILL plus one guard rule

**Form: a skill, not a rule.** `md-size-budgets.md` § "Scoping: the trigger test"
is explicit — *"Behaviour-triggered but niche → a skill, not a rule."* Writing an
adversarial review brief happens once or twice per ticket. A 24th eager rule
would spend launch bytes in every session for something used occasionally, and
unscoped rules are already ~88% of the eager corpus. A skill also *carries a
method* (template + worked example + a ladder), which rule files deliberately do
not.

#### 1a. NEW FILE — `.claude/skills/adversarial-review/SKILL.md`

Budget class `skill`: 500 lines / 32,000 B. Frontmatter `name:
adversarial-review`, `description:` naming the triggers ("adversarial review",
"codex review round", "review brief", "the review loop is not converging").
Do **not** set `disable-model-invocation` — unlike the protocol verbs, this is
something the model should reach for on its own.

Body, in this order:

1. **The round ladder** — the operative content.

   | Round | Brief shape | Terminates? |
   |---|---|---|
   | **v1** | Open hunt. *"Find what is wrong."* Legitimate and necessary — it discovers the defect **shape**. | No, by design |
   | **v2..vN** | **Bounded disposition.** A `vN-1 → vN` disposition table (`CLOSED`/`PARTIALLY CLOSED`/`OPEN`), plus "what did THIS commit break". Must carry a stop condition. | Only if nothing new is reachable |
   | **STOP** | **Trigger: two rounds find the same defect SHAPE.** Stop writing fix commits. Build the enumeration. | — |
   | **v-final** | **The three-question verification brief** over the enumeration. | **Yes** |

2. **The three questions, stated generically** (they are not truth-table-specific
   — they apply to any enumeration: a state table, a permission matrix, a rule
   list, a taxonomy):

   - **Q1 — CELLS.** Is any expected value wrong? Not "does the code produce it",
     but "is that the right decision", judged against the ground-truth
     documents. Answer per-cell only where you disagree.
   - **Q2 — AXES.** Are these the right axes — is there another input that
     changes an outcome? *"If the axes are complete, say so explicitly; that is
     the answer that ends this."*
   - **Q3 — META.** Do the tests guarding the enumeration actually constrain it,
     or can a degenerate/wrong enumeration still pass them?

3. **The mandatory stop condition, verbatim template:**

   > If your answer to (1) is "no cell is wrong", to (2) is "the axes are
   > complete", and to (3) is "the meta-tests hold", then the correct verdict is
   > SHIP and the correct finding count is ZERO. Say that plainly.

4. **The mandatory escape hatch, verbatim template:**

   > If you find something genuinely outside these questions that is HIGH
   > severity, report it — but say explicitly that it is out of scope, and it
   > will become **a ticket rather than another commit on this branch**.

5. **The `## Do NOT` block** — negative scope removing every re-litigation
   surface: prior findings, out-of-scope tickets, sandbox limits, style/wording,
   manufactured findings.

6. **Carry-overs from v1–v6 that DID work and must be kept** (evidence: every
   round produced `file:line`-anchored, `UNVERIFIED`-marked findings, and no
   round wasted a finding on sandbox limits after v2 named them):
   - "MANDATORY: code introspection is not optional" + open every changed file in
     full;
   - `file:line` for every claim, or it is not a finding;
   - explicit `UNVERIFIED` marking;
   - a receipts list split source-verified vs reasoned-alone;
   - a **"Sandbox limits — do NOT report these as findings"** section listing the
     implementer's gate results **as CLAIMS**.

7. **Brief path convention** — `.agent/reviews/<ticket>/brief-v<N>.md`, reports
   alongside as `report-v<N>.md`. Gitignored (so `branch_guard` allows it), and
   folded into the tracked bundle at clear-prep (Fix 4).

   **Evidence this matters:** all seven #601 briefs lived only in the ephemeral
   session scratchpad and were persisted by hand at clear-prep. The bundle's own
   header says it: *"one `/clear` from being lost"*. The briefs turned out to be
   the more valuable half of the corpus.

#### 1b. TEETH — `python/src/dotfiles_setup/hook_guard.py`, new PreToolUse rule `review_brief_stop_condition`

Markdown alone is "relying on the LLM, never the only layer"
(`.claude/rules/mise-tasks-only.md`), and the evidence here is damning: **6 of 7
briefs, written by an agent that had every rule in context, lacked a stop
condition.** That is the decay pattern the doctrine predicts, measured.

- **Matcher:** `Write`/`Edit` where `file_path` matches `.agent/reviews/*/brief-v*.md`.
- **Condition:** if the parsed `N` in `brief-v<N>` is **≥ 2** and the content
  lacks a `## Stop condition` heading (or lacks the literal `ZERO`/`zero`
  finding-count sentence), **deny** with a reason naming the
  `adversarial-review` skill. `N == 1` is exempt — round 1 is legitimately an
  open hunt.
- **Why Write and not the `codex exec` Bash call:** the guard sees the full
  content in the tool input, so no file-reading or command-line parsing is
  needed. A `cat X | codex exec -` rule would have to resolve `X` and would be
  fragile.
- **Performance note — real, from this repo's own history:** `branch_guard`
  already costs ~340 ms per edit (memory `project_session_2026-08-03-f`, flagged
  as a follow-up). This rule MUST short-circuit on a cheap
  `.agent/reviews/` path-prefix test before any content inspection, so it costs
  ~0 on the 99.99% of writes that are not briefs.
- **Test:** `tests/test_hook_guard.py` — both arms. A `brief-v2.md` with a stop
  condition passes; the same file with the section deleted denies. Per
  `probes-need-a-control-arm.md` R2, mutate by **deleting the heading**, which is
  what the real regression looks like — not by renaming it.
- **Contract:** add the wiring assertion to `workflow.mise-tasks-enforcement`'s
  sibling pattern in `python/verification/suites.toml`.

**Adds: teeth (a machine gate) + a skill. Adds NO eager prose.**

#### 1c. One-row prose addition — `.claude/rules/agent-artifact-conventions.md`

Add to the "Local, gitignored" table:

| `.agent/reviews/<ticket>/` | Review briefs + reports, per round (`brief-v<N>.md` / `report-v<N>.md`) |

Required because that rule forbids ad-hoc directories, and the guard in 1b keys
off this path. **This is the only eager-prose byte any IMPORTANT fix spends: one
table row.**

---

### Fix 2 — enumerate-before-patching: the trigger, made concrete

Three HIGHs (v4, v5, v6) were the identical shape: *a reachable combination of
`state × needs × queuedPrompt × pid_alive` that nobody had enumerated.* The v7
brief says so in its own words. The eventual fix (`eda53d6`) was an exhaustive
table — which, at the time of writing, has grown to **64 rows across five axes**
(`tests/test_dag_tick.py:595`), the fifth axis being v7's finding.

**Two triggers. The first is for humans and applies immediately; the second is a
machine gate and is EVENTUAL (Fix 7).**

#### Trigger A (IMPORTANT, human-checkable) — the same-shape rule

> **When two review rounds find defects of the same shape, stop writing fix
> commits. Build the enumeration, then review the enumeration.**

"Same shape" is concrete: the two findings differ only in the *value* of one
input, not in the mechanism. v5 found `blocked+needs+queued+dead`; v6 found the
same with `alive`. That is one axis value apart. By the end of round 5 the shape
was visible; rounds 6 and 7 were both spent inside it.

**Where it lives:** step 1 of the `adversarial-review` skill's ladder (Fix 1a),
and it is the same trigger `/clear-prep` measures (Fix 4). **No new rule file.**

#### The authoring-time question, for the change that starts it

> A change that adds or reorders a branch in a function mapping **≥3 independent
> inputs** onto a **closed set of outcomes** must ship the exhaustive table
> **with the first commit**, not the ninth.

`dag_tick.classify` reads five (`state`, `needs`, `queuedPrompt`, `pid_alive`,
`tempo`) and returns a six-member enum. It qualified from commit 1. The table
arrived at commit 9.

**Where it lives:** `tests/AGENTS.md` § "What a good test is here", as a third
bullet next to the two existing anti-patterns — because it is the same class of
silent false negative, and that file is `nested` load class, loaded whenever
Claude reads anything under `tests/`. **The #601 session edited
`tests/test_dag_tick.py` in 7 of its 9 commits**, so that file was loaded for
almost the whole loop. It is the highest-hit-rate placement available that costs
zero eager bytes.

**Adds: prose — but placed where it demonstrably loads, and it is one bullet in
a `nested`-class file, not an eager rule.** Teeth follow in Fix 7.

---

### Fix 3 — the fix-creates-the-next-defect cycle (rounds 4→5→6)

**The honest answer: this needs no new mechanism, because Fix 2 IS the
mechanism — applied at t=0 instead of t=9.**

Trace it. Once `_CLASSIFY_TABLE` exists, a fix that moves a cell **fails a test
at commit time**:

| Fix | Cell it moved | Would the table have caught it? |
|---|---|---|
| `8c87eec` (v4's fix — add the escalation SKIP path) | made `blocked+needs+queued+dead` reachable-and-deadlocked | **Yes** — a row's expected value no longer matches |
| `09d2cb9` (v5's fix — add `queued_prompt` to `is_needs_human`) | `blocked+needs+queued+alive`: NEEDS_HUMAN → ALIVE (silent) | **Yes** — one row flips |

Both would have been a failing parametrized row seconds after the edit, instead
of a full codex round each. Rounds 6 and 7 would not have existed.

**So the distinct contribution of this fix is not a mechanism — it is the
READING DISCIPLINE that keeps the mechanism from being defeated**, and that
discipline has exactly one failure mode:

> When the enumeration test fails after a fix, **the failing cells ARE the blast
> radius.** Each one is either (a) intended by this fix and named in the commit
> message, or (b) the next defect. **Never edit the expected value to make the
> test pass.** That converts an independent hand-derived expectation into a
> transcription of behaviour — the tautological-test anti-pattern
> `tests/AGENTS.md` already names, and the one way this whole mechanism can be
> silently disarmed.

**Where it lives:** the same `tests/AGENTS.md` bullet as Fix 2 — one paragraph.

**Adds: prose only, and I am labelling it as such.** I looked for teeth and did
not find honest ones: a gate that inspected whether a diff's expected-column
changes were "named in the commit message" would be a natural-language judgement
in a hook, which is exactly the over-reach `mise-tasks-only.md` warns keeps
patterns narrow. The mechanical half is already carried by the enumeration test
itself; this paragraph is the part no gate can hold.

---

### Fix 4 — `/clear-prep` integration (tier 1)

**Constraint, from harness-expert's findings — this is why the design is what it
is.** A SessionEnd hook **cannot** run a reflection team: the budget is 60 s
(`$CC/hooks.md`), SessionEnd "can't block session termination", `async` is
command-hook-only, and in `-p` mode async hooks are **killed at teardown**. A
native `type: "agent"` hook spawns **one** subagent, returns `{ok, reason}` only,
and is marked experimental. The only surviving route is a fully detached
process — which is not a place to run a 6-agent reflection either.

**Therefore the reflection step belongs inside `/clear-prep` itself** — a
user-invoked skill running in a live session with full team capability. That is
the tier-1 answer.

#### 4a. `.claude/skills/clear-prep/SKILL.md` — NEW step 3d

Insert **after 3c** (research artifacts) and **before step 4** (validate/commit),
so anything it writes lands in the same doc commit.

```markdown
### d. Review-loop audit — always cheap; reflection is a TICKET, not a step

**Always (seconds, no agents):**

1. **Fold this session's review rounds into the tracked bundle.** For each
   ticket reviewed, concatenate `.agent/reviews/<ticket>/brief-v*.md` and
   `report-v*.md` — **briefs included, verbatim** — into
   `docs/research/kb/reports/agents/<ticket>-review-rounds.md`. The briefs are
   evidence, not scaffolding: the #601 reflection's single most important datum
   was the v1→v7 brief evolution, and all seven briefs existed only in the
   ephemeral scratchpad until they were rescued by hand.
2. **Measure the loop and record it in the handoff:**

   ```bash
   git log --oneline origin/main..HEAD | wc -l        # commits
   ls .agent/reviews/*/brief-v*.md 2>/dev/null | wc -l  # rounds
   ```

**Escalate ONLY if a trigger fires** — any of:

- **≥3 review rounds** on one ticket;
- **≥2 rounds finding the same defect shape** (differing in one input value,
  not in mechanism);
- **≥5 commits** on the branch whose subjects are `fix:`/`test:` written in
  response to a review.

Then **file it, do not run it**: `gh issue create` with the metrics, the bundle
path, and the `dag:reflect` label, and put it in the handoff's next-task. A
reflection is a ticket's worth of work with its own branch and receipt
(#601's was six agents); clear-prep is the moment you have the least context
and are about to destroy it. Running it here is the wrong trade.
```

#### 4b. Two lines in clear-prep's final checklist

```markdown
- [ ] Review briefs AND reports folded verbatim into `docs/research/kb/reports/agents/<ticket>-review-rounds.md`.
- [ ] Loop metrics recorded in the handoff; if a trigger fired, the `dag:reflect` ticket is filed and named as next-task.
```

**Enforced by:** the existing clear-prep checklist discipline (the skill is
`disable-model-invocation: true`, so it only ever runs when the user invokes it,
top-to-bottom). **Adds: prose in a `skill`-class file (500-line budget, current
file is 247).** The teeth for the *brief* half are Fix 1b; the fold step's own
teeth are that `agent-report-persistence.md` already requires verbatim
persistence — this step names briefs as in-scope, closing a gap the rule left
open by only naming *reports*.

---

### Fix 5 — the `reflect` DAG node type (tier 2, map #556)

Specified against `docs/receipts/575.md`'s taxonomy — **no new terminal reasons
are invented**; all five map onto the existing set.

**Kind:** `reflect`. Sits on the run axis as an ordinary node; its verdict axis
is separate, per #575's split.

#### Inputs

| Input | Required | Notes |
|---|---|---|
| `ticket` | yes | the ticket whose implementation loop is under study |
| `rounds_artifact` | **yes** | path to the tracked verbatim bundle (`docs/research/kb/reports/agents/<ticket>-review-rounds.md`), **briefs included**. Absent ⇒ fail fast — a reflection over summaries reproduces exactly the loss `agent-report-persistence.md` exists to prevent |
| `commit_range` | yes | `origin/main..<branch>` |
| `trigger_metrics` | yes | rounds, HIGH count per round, same-shape count — the numbers that opened the node, so the receipt can be judged against its own premise |

#### Outputs

| Output | Notes |
|---|---|
| `docs/receipts/<ticket>-reflect.md` | same shape as `575.md`: verdict paragraph, tables, `## Sources — what I actually opened` |
| N child tickets | each carrying a **fix class**: `teeth` (a machine gate), `prose` (a doc edit, with its load class named), or `deferred` |
| verdict | `approve` / `revise` / `reject`, routing per #575 |

#### Terminal reasons (mapped onto #575's five)

| Reason | Condition |
|---|---|
| `Succeeded` | receipt written **and** every finding carries a fix class **and** every `teeth` finding has a filed ticket |
| `Failed` | the corpus artifact is missing or unreadable, or the spawned agents produced no persisted reports. Retries to #573's cap 3 with its backoff — this failure is usually transient (an artifact still being written) |
| `NeedsHuman` | the recommendation would **add prose to an eager rule**, **change a rule's directive**, or **add a hook**. All three change agent behaviour repo-wide and `md_size_budget` is a shared budget, so none is an autonomous decision. **Never auto-retried**, per #575 |
| `Stalled` | inferred; **no action until #590**, per #575 |
| `CanceledByReconciliation` | the ticket under reflection was closed or reverted before the node ran. Consumes **no attempt** |

#### Escalation path

`NeedsHuman` uses #575's two-tier projection unchanged: the node writes
`state=blocked` + a `needs` payload to `~/.claude/jobs/<id>/state.json`; the
scheduler projects `dag:needs-human` + an append-only tracker comment, one
direction only. **#575's evidence gate binds here specifically:** *"a blocker is
valid only if it names what was exhausted"* — so a reflect node's `needs` MUST
carry the fix-class analysis, e.g. *"this failure needs teeth; I could find no
machine gate; alternatives tried: X (rejected because …), Y (rejected
because …)"*. An evidence-free "needs a rule" escalation is rejected at
projection time.

Downstream, `dag_tick` classifies it `NEEDS_HUMAN` and never respawns — which is
#601's own fix, so the reflect node inherits the correctness this whole loop
bought.

#### Stopping predicate

> A reflect node is **done** when every finding carries a fix class **and the set
> of fix classes is closed** — no finding is left as "needs more investigation".

This is Finding 0's law applied to the reflection itself: the artifact under
review is the *findings × fix-classes* matrix, so the node inherits the v7 stop
condition rather than inventing one. A finding that resists classification is not
a reason for another round; it is a `deferred` child ticket.

`max_rework` **2** applies (#573): a reflect receipt rejected twice goes
`dag:needs-human`.

⚠️ **Reconcile with cost-analyst.** I derived this predicate independently; their
`601-reflect-cost-stopping-rule.md` was still mid-draft (measurements 1–2 only)
when I wrote it. Their numbers already refute the task brief's own "~40-line fix"
premise — **1,465 insertions**, 451 in production — so any cost-based stopping
rule must be calibrated against that denominator, not the wrong one. If their
predicate differs from mine, theirs is the measured one and wins.

**Adds: teeth (a node type with a machine-checked terminal predicate).** EVENTUAL
— file as a sub-issue of map #556.

---

### Fix 6 — which of this run's 6 roles earn a durable `.claude/agents/*.md`

Judged by output produced, **not by symmetry**. Two of six.

| Role | Verdict | Evidence |
|---|---|---|
| **harness-expert** | **Already exists — keep, add nothing.** `.claude/agents/claude-code-expert.md` (`model: opus`) | It produced the single decisive constraint of this whole design — SessionEnd cannot host a reflection team — with verbatim `$CC/hooks.md` citations, **and** flagged that its own ledger is pinned at 2.1.222 while the binary is 2.1.223. Version-drift self-reporting is precisely what that definition is for. |
| **rule-coverage** | **EARNS a new definition** — `.claude/agents/rule-coverage-auditor.md`, `model: opus`, high effort | Highest-density output in the run: a 5-row coverage table with a **control-armed** scoping probe (23 files swept, 2 scoped / 21 prose-first — so the probe discriminates), plus a `fix class` column that directly drove Fixes 1–3. **It is a distinct capability from `staleness-auditor`**: staleness-auditor asks *"is this prose still true"*; rule-coverage asks *"did this rule FIRE, and if not, why not"* — a counterfactual about instruction-loading, not a truth check. `model: opus` because it must hold 23 rule files plus the corpus and reason counterfactually; its sibling `staleness-auditor` is already opus. |
| **loop-forensics** | **Does not earn one** | At the time of writing its output is a 9-row commit table reconstructible from one `git log --oneline`. Its value is entirely downstream of a corpus the caller already holds. It is a *section of the reflect node's own work*, not a reusable agent. (Judged on a draft — revisit if its causal chain lands with independent content.) |
| **cost-analyst** | **Does not earn one** | It made one genuinely valuable move — refuting the task brief's own "~40-line fix" premise by re-derivation, and **refusing** to report a single wall-clock figure because git cannot discriminate idle from work. But that is `probes-need-a-control-arm.md` **R6** (*an inherited number is not a measurement*), which this repo already carries as an eager rule binding every agent. It earns a **line in the reflect node's brief**, not a definition. |
| **process-designer** | **Does not earn one** | This output *is* the reflect node's core deliverable. Encoding it as a separate agent would duplicate Fix 5. |
| **main / lead** | n/a | orchestration |

#### The `rule-coverage-auditor` definition — required contents

Model `opus`, `disallowedTools: Edit, NotebookEdit` (it audits; it must not fix —
same posture as its two siblings). It **must** carry, in the definition itself
and not in the per-task brief:

- **incremental persistence** — write the report file early and update it as
  findings land;
- **`SendMessage` before going idle.**

**Evidence this placement is the one that works:** `agent-report-persistence.md`
§1b records that on 2026-08-03 the requirement went into *none* of four briefs,
two agents died leaving nothing, and only `staleness-auditor` — which carries it
in its **definition** — complied. In **this** run all four sibling agents had
readable incremental drafts on disk when I read them at the ~30-minute mark. The
mechanism held. Put it in the definition.

**Adds: a new agent definition file.** Note `.claude/agents/*.md` is
**unbudgeted** by `md_size_budget` (memory `project_session_2026-08-05e`), so
this costs no gate headroom — but it is loaded when the agent runs, so keep it at
`staleness-auditor`'s ~169-line scale, not `claude-code-expert`'s 342.

---

## EVENTUAL — file as issues

### Fix 7 — the classifier-enumeration gate (the teeth behind Fix 2)

**New file** `python/src/dotfiles_setup/classifier_tables.py` + CLI subcommand
`classifier-tables` + hk step, **modelled exactly on `bash_budget.py`** — which
`.claude/rules/zero-bash-logic.md` documents as this repo's canonical
"allowlist gates NEW, budget flags GROWTH" shape:

1. **REGISTRY gates NEW.** Every function under `python/src/dotfiles_setup/**`
   whose return annotation is a repo-defined `Enum` must have a registry entry
   naming (a) its decision axes and (b) the test-module constant enumerating
   them. A new classifier with no entry **fails** — the answer is to write the
   table, or add an entry with a one-line justification (a reviewable diff).
2. **CARDINALITY flags GROWTH.** For each entry, assert
   `len(TABLE) == prod(len(axis) for axis in axes)`. Adding an axis value without
   re-enumerating **fails**. A stale entry (registered classifier no longer
   present) also fails, so the map cannot rot.

`hk.pkl`:

```pkl
["classifier_truth_table"] {
  glob = List("python/src/dotfiles_setup/*.py", "tests/test_*.py")
  check = "uv run --project python dotfiles-setup classifier-tables"
}
```

Plus `tests/test_classifier_tables.py` (both arms) and a
`workflow.classifier-enumeration` contract in `python/verification/suites.toml`
asserting the chain (hk step ↔ CLI ↔ module ↔ tests ↔ the skill), mirroring
`workflow.bash-logic-enforcement`.

**Do NOT implement this as a `per_path_tokens` contract instead.** Two reasons,
both from this corpus: a token cannot compute a cardinality product, and codex's
**v1 LOW** established that `per_path_tokens` is unanchored substring membership
which a commented-out line satisfies. Wrong tool.

**Honest caveat, stated because it changes the priority:** the repo has exactly
**one** qualifying classifier today (`dag_tick.classify`). A gate guarding one
call site is thin. It is filed as EVENTUAL rather than IMPORTANT for that reason
— but it should be built *before* map #556's remaining nodes land, because
#575's own taxonomy (terminal reasons, per-reason retry policy, verdict routing)
is three more classifiers waiting to be written. The gate is cheap now and
retrofitted expensively later.

### Fix 8 — the `reflect` node type (Fix 5) as a sub-issue of map #556

Spec is complete above; it needs the scheduler-side plumbing that #602 (tracker
projection) and the existing `dag_tick` classes already imply.

### Fix 9 — `mise run review-brief -- <ticket> <round>`

A renderer (`python/src/dotfiles_setup/review_brief.py`) emitting the scaffold
from Fix 1a into `.agent/reviews/<ticket>/brief-v<N>.md`, pre-filled with the
disposition table skeleton and the round-appropriate stop condition. Turns Fix
1b's guard from "deny a bad brief" into "the good brief is the path of least
resistance" — `mise-tasks-only.md`'s preferred shape (a task wrapping a python
library). Low value until briefs are routine; file it, do not build it yet.

---

## Summary — prose vs teeth, per fix

| # | Fix | File | Prose or teeth | Tier |
|---|---|---|---|---|
| 1a | `adversarial-review` skill | `.claude/skills/adversarial-review/SKILL.md` (NEW) | skill (on-demand, 0 eager bytes) | **IMPORTANT** |
| 1b | Brief stop-condition guard | `hook_guard.py` + `tests/test_hook_guard.py` | **TEETH** | **IMPORTANT** |
| 1c | `.agent/reviews/` path row | `.claude/rules/agent-artifact-conventions.md` | prose — **one table row**, the only eager bytes spent | **IMPORTANT** |
| 2 | Enumerate-first, same-shape trigger | `tests/AGENTS.md` (+ skill ladder) | prose, `nested` class — loaded in 7 of the 9 commits | **IMPORTANT** |
| 3 | Blast-radius reading discipline | `tests/AGENTS.md`, same bullet | **prose only — labelled; no honest gate exists** | **IMPORTANT** |
| 4 | clear-prep step 3d + 2 checklist lines | `.claude/skills/clear-prep/SKILL.md` | prose in a `skill`-class file (247/500 lines used) | **IMPORTANT** |
| 6 | `rule-coverage-auditor` | `.claude/agents/rule-coverage-auditor.md` (NEW) | agent definition (unbudgeted) | **IMPORTANT** |
| 7 | Classifier-enumeration gate | `classifier_tables.py` + `hk.pkl` + suites.toml | **TEETH** | EVENTUAL |
| 5/8 | `reflect` DAG node type | map #556 sub-issue | **TEETH** (terminal predicate) | EVENTUAL |
| 9 | `mise run review-brief` | `review_brief.py` + `mise.toml` | teeth-adjacent (path of least resistance) | EVENTUAL |

**Net eager-context cost of the entire IMPORTANT set: one table row** in
`agent-artifact-conventions.md`. No new `.claude/rules/*.md` file is proposed,
and no existing rule is reworded.

---

## Budget feasibility — measured, not assumed

Fixes 2 and 3 both land in `tests/AGENTS.md`, which carries the **hard** agnix
AGM-003 12,000-char cap (Windsurf's rule) *and* the `nested` class budget
(400 lines / 32,000 B). Measured 2026-08-06:

| File | Now | Binding cap | Headroom | Proposed addition |
|---|---|---|---|---|
| `tests/AGENTS.md` | **4,888 B** | AGM-003 **12,000** | **7,112 B** | ~800 B (one bullet + one paragraph) |
| `.claude/skills/clear-prep/SKILL.md` | 247 lines | `skill` **500** | 253 lines | ~30 lines |
| `.claude/rules/agent-artifact-conventions.md` | — | `rule_unscoped` 200 / 24,000 | — | **one table row** |

All three fit with room. `.claude/agents/*.md` is unbudgeted. **No offsetting
trim is required for any IMPORTANT fix** — which is the point of routing
everything except one table row away from eager rules.

## What I could not settle

- **Fix 1b's exact deny predicate** was not probed against the live guard. The
  mechanism (PreToolUse `Write` matcher, deterministic deny, reason shown to
  Claude) is established by `$CC/hooks.md:1544` and by `branch_guard` already
  doing this for `Write`/`Edit` — but I did not execute a `.agent/reviews/`
  denial. **UNVERIFIED**; arm both directions when implementing.
- **The `reflect` node's stopping predicate** is mine, derived from Finding 0,
  not cost-analyst's measured one. Reconcile before building.
- **loop-forensics' agent verdict** is judged on a draft containing only a commit
  table. If its causal chain lands with independent content, revisit Fix 6.
- I did **not** re-derive the sibling agents' measurements (23 rules, 1,465
  insertions, the 60 s SessionEnd budget). They are **inherited and labelled** as
  such per `probes-need-a-control-arm.md` R6 — each sibling states its own
  method.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under study; #601, #602, #604, #573/#575/#578 receipts and map #556 read from the working tree.
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — hook semantics (SessionEnd budget, `type: "agent"` hooks, PreToolUse deny) via the knowledge-base's offline `$CC` doc tree, cited through harness-expert's report rather than fetched directly.
