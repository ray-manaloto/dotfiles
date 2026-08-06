# Rule-coverage audit — #601 session (7 review rounds, 9 commits) — 2026-08-06

Agent: `rule-coverage`. Question: **for each failure, was there already a rule
that should have caught it — and if so, why didn't it fire?**

Headline: **4 of 5 failures were covered by a rule that was eager, loaded, and
correct.** One rule is actively misleading in a way that contributed to three
of them. The corpus does not need a 24th rule for four of the five; it needs
one small new rule and two gates.

## Ground truth measured (not asserted)

| Fact | Measurement |
|---|---|
| Rules in `.claude/rules/` | `ls .claude/rules/*.md \| wc -l` → **23** |
| Case histories in `docs/rules-evidence/` | `ls docs/rules-evidence/*.md \| wc -l` → **17** |
| Commits on branch | `git log --oneline origin/main..fix/601-dag-tick-needs-human` → **9** |
| `paths:`-scoped rules | **2 of 23** — `ci-local-parity.md`, `md-size-budgets.md`. The other 21 have no frontmatter ⇒ **eager, loaded at launch** |
| `tests/AGENTS.md` load class | `nested` (per `md-size-budgets.md` table) — loaded when Claude reads files in `tests/`. The session touched `tests/test_dag_tick.py` in **7 of 9 commits** ⇒ loaded |
| Gates green on every one of the 9 commits | each commit body: `lint rc=0 · lint-docs rc=0 · pytest 1369→1420 passed · verify 115 passed/0 failed` |

**Scoping probe, control-armed.** `for f in .claude/rules/*.md; do head -8 "$f"; done`
returned YAML frontmatter for exactly 2 files and prose-first for 21. The probe is
not blind to frontmatter (it found 2), so "21 eager" is a real positive, not an
unreachable one.

---

## The coverage table

| # | Failure | Existing rule that covers it | Loaded? | Why it did not fire | Fix class |
|---|---|---|---|---|---|
| 1 | Honesty predicate applied only to the real string, never a wrong one (v2 LOW) | `probes-need-a-control-arm.md` R1/R2 · `tests/AGENTS.md` § "a probe with no control arm" | **YES** (eager + nested) | Nothing fires at *test-authoring* time. The author restated the rule's own metaphor **verbatim** two commits later — it was known, not absent | **EXISTING RULE IS FINE, HUMAN ERROR** → the only useful response is a gate |
| 2 | Queued-reply fix tested only on `pid_alive=False` (v6 HIGH) | `probes-need-a-control-arm.md` **R8** (arm the fixture) + R3 (bounds) | **YES** (eager) | R8's canonical case is a *rigged* fixture; this was a **pinned axis in an otherwise-real fixture**. And R2's mutation standard was fully satisfied — see §M1 | **RULE IS WRONG OR MISLEADING** (§M1) |
| 3 | "tempo/age pinned … keeps WEDGED out of the picture" — false in comment, commit body, contract, and the test's own axis list (v7 MEDIUM) | `probes-need-a-control-arm.md` R8 + R3 · memory `feedback_enumerate_dont_assert_the_list` | Rule **YES**; the memory is **recall-gated, not eager** | The exhaustiveness meta-test is computed **from the hand-written axis list**, so it can only confirm the author's own axis choice — a meta-probe with one face | **EXISTING RULE NEEDS TEETH** (§T2) |
| 4 | Log line asserting two actions the code does not perform (v1, 2×HIGH) | `secrets-out-of-the-shell-env.md` gates **2** and **4** · `.claude/agents/staleness-auditor.md` shape #3 | **YES** (eager) — and the rule records this exact defect **twice** | Both records are **archaeology about two specific artifacts**, never a directive. Grep proves no rule states it as a rule (§N1) | **NEW RULE NEEDED** (one paragraph) |
| 5 | Each fix created the next round's HIGH — 3 rounds running (v4→v5→v6) | `verify-before-advancing.md` · `zero-skip-policy.md` | **YES** (eager) | Both were **fully satisfied** on all 9 commits. They gate *the checks*, not *the reachable-state delta a fix opens*. No rule asks "what did this fix make reachable?" | **NEW RULE NEEDED** (§N2) — or accept it and fix the *brief*, see §V7 |

---

## §M1 — RULE IS MISLEADING: `probes-need-a-control-arm.md` R2 taught the exact discipline that produced failures 2 and 5

This is the finding I would act on first.

**Verbatim, `.claude/rules/probes-need-a-control-arm.md` R2:**

> 2. **Arm the positive.** Before reporting "the gate works", reintroduce the bug
>    and confirm it **fails**. A gate verified only on clean code is decoration.
>
>    **Reintroduce the bug REALISTICALLY** … it must be a break that could
>    **really happen** — usually deleting the wiring line that calls a function,
>    not renaming the function.

**The session followed this exactly, every round, and said so:**

| Commit | Verbatim mutation receipt |
|---|---|
| `8c87eec` | "Both arms bound, mutation-verified: deleting the re-check fails the race arm **and ONLY the race arm**" |
| `09d2cb9` | "Mutation-verified: dropping the `queued_prompt` term fails 5 tests including the end-to-end delivery arm." |
| `796777a` | "Mutation-verified: deleting the REPLY_QUEUED wiring fails the visibility arm and the note arm, **and nothing else**." |

Each of those three mutation-verified fixes **was the direct cause of the next
round's HIGH**. Codex v5 on `8c87eec`; v6 on `09d2cb9`; v7's axis finding on the
table that replaced `796777a`'s cell-patching. So the rule's own gold standard for
"the gate works" was met at 100% and had **zero** predictive power on the defect
that actually shipped.

**The falsifier, and why it lands.** For R2 to be adequate here, "deleting the fix
fails the test" would have to imply "the fix covers the state space". It does not,
and it cannot: deletion-mutation is a proof about the *test↔fix* pair. It says
nothing about cells neither the test nor the fix ever visits. Every one of the
three HIGH findings was exactly such a cell — `eda53d6`'s own commit body names
the shape: *"a reachable combination nobody had enumerated … each was made
reachable by the previous round's fix."*

**The misleading part is sharper than an omission.** The phrases "and ONLY the
race arm" and "and nothing else" are written in those commits as **evidence of
quality** — a tight fix that doesn't over-reach. R2's framing ("a mutation must
actually *destroy* what the check looks for") encourages reading narrow mutation
impact as good. It is in fact the **signature of the failure mode**: when
deleting the fix breaks only the arm you just wrote, the test space and the fix
space are the same size, which is precisely the condition under which an
unenumerated neighbouring cell exists.

**Second route, independent of my reading of the rule.** `docs/rules-evidence/probes-need-a-control-arm.md:46-68`
expands R2 with two worked cases — both are about a mutation being *too weak to
destroy the token* (`_REMOVED` suffix surviving as a substring; a token surviving
in a comment). Neither case is about a mutation being *complete but irrelevant*.
So the evidence file confirms the rule's scope is "make the mutation bite", with
no coverage of "the mutation bit, and proved nothing about neighbours". The gap
is in the rule, not in my reading of it.

**Proposed replacement text** (caller applies; I do not edit the audited file).
Append to R2, after "an unrealistic mutation can only ever accuse the wrong party":

> **A mutation proves the TEST covers the FIX. It says nothing about what the fix
> left uncovered.** Deleting a fix and watching one arm fail is necessary and
> weak — and "…and ONLY that arm" is not a quality signal, it is the signature of
> a fix and a test that are the same size. When the fix adds a *condition* to a
> predicate, the mutation to run second is not deleting the condition: it is
> **flipping every other axis that predicate reads** and asking which cells you
> have never asserted. #601 shipped three mutation-verified fixes in a row, each
> of which made the next round's HIGH reachable
> (`docs/research/kb/reports/agents/601-codex-review-rounds.md`).

---

## §N1 — NEW RULE NEEDED: prose must not assert an action the code does not perform (third occurrence)

The v1 HIGH:

> `"…never auto-respawned at any age (project + label dag:needs-human)"`
>
> — *"'project + label' named an action no code here performs. #602 owns the
> projection; nothing in this process writes the label or the comment."* (`cf6e97d`)

**This repo has recorded the identical defect class twice already, in an eager
rule.** `.claude/rules/secrets-out-of-the-shell-env.md`:

- gate 2 — *"`docs/hk-builtins-audit.md` listed it as a 'second scanner alongside
  gitleaks' … and it was never wired — 0 occurrences in any `.pkl`, against a
  control of 1 for `Builtins.gitleaks`. **A doc asserting a security scanner runs
  when it does not is worse than not claiming it.**"*
- gate 4 — *"`clean_env()` has ZERO production call sites … yet this file claimed
  it as a gate — **the defect it convicts betterleaks of, two entries above.**"*

The corpus already noticed it was recurring, inside the same file, and still did
not promote it to a directive.

**Probe that no rule states it, control-armed:**

```
$ grep -rniE "claims? an action|does not perform|asserts? a (gate|control|action)|worse than no doc|worse than not claiming" .claude/rules/
.claude/rules/secrets-out-of-the-shell-env.md:107: asserting a security scanner runs when it does not is worse than not claiming
```
Control arm (known-present term): `grep -rl "control arm" .claude/rules/ | wc -l` → **4**.
Known-absent arm (invented fresh for this run, never published before): `grep -rl "quorbaxil" .claude/rules/ | wc -l` → **0**.
So the probe both finds and fails to find — the single hit is real.

**One hit, and it is a sentence about betterleaks.** The principle is stated
nowhere as a rule, and #601 is its third instance — this time in an operator-facing
*runtime string* rather than a doc, which is the more dangerous surface (a doc is
read once; a log line is read during an incident).

**Proposed new rule** — `.claude/rules/claims-must-name-a-call-site.md`, eager,
short (this is a behaviour-triggered rule, so per `md-size-budgets.md` § "the
trigger test" it cannot be `paths:`-scoped):

> Any sentence a human will read as a statement about system behaviour — a log
> line, a docstring, a rule, a receipt, a contract description — must name an
> action **this** code performs, or scope itself explicitly to what it does not.
> Before writing "X is done", grep for X's call site; if there is none, write "X
> is NOT done here — <owner>". Three recorded instances: betterleaks documented
> as wired with 0 occurrences; `clean_env()` claimed as a gate with 0 call sites
> (both `secrets-out-of-the-shell-env.md`); `dag_tick`'s NEEDS_HUMAN line claiming
> `project + label` that no code emits (#601 v1 HIGH). Evidence:
> `docs/rules-evidence/claims-must-name-a-call-site.md`.

This is the one place I recommend *adding* prose, because the alternative is a
fourth instance. It is also gateable — see §T1.

---

## §T1/§T2 — where teeth are feasible, and what they'd cost

The doctrine (`mise-tasks-only.md`): *"markdown alone is 'relying on the LLM',
never the only layer."* Two of these are mechanisable with machinery this repo
already runs.

**§T1 — a claim/call-site gate.** `contract_token_uniqueness` (hk step, `hk.pkl:306`)
already binds a contract's `per_path_tokens` to real source and it **worked during
#601**: `09d2cb9`'s body records *"`contract_token_uniqueness` caught two token
problems in this change (a stale 0× match after the signature change, and an
ambiguous 2× `and not queued_prompt`)"*. That is a live proof the mechanism has
teeth. The extension: for any string literal emitted to an operator that contains
an imperative verb naming a repo concept (`label`, `project`, `respawn`, `stop`),
require a bound call site or an explicit negation. Cost: real false-positive risk;
this is the weakest of my three recommendations and I flag it **SUSPECT** — I have
one route (reading `verify.py`'s handler names via the contract), not two.

**§T2 — a truth-table axis gate, which the session half-built.** `eda53d6`'s
`test_classify_truth_table_is_exhaustive` computes coverage **from a hand-written
axis list** (`tests/test_dag_tick.py:667`: `states = [_TERMINAL, "blocked", _OTHER, None]`).
That meta-test can only ever confirm the author's own axis choice — which is why
it passed while `tempo`, a real fifth axis, sat pinned. The teeth: derive the axis
set from the **classifier's own reads** (the parameters `classify`/`is_terminal`
actually consume) rather than from a literal list, so adding a read to the
predicate fails the meta-test. That converts failure 3 from prose into a gate, and
it is the shape memory `feedback_enumerate_dont_assert_the_list` already prescribes
— *"an alternation of what you expect hid 18 of 29 hook events; match the SHAPE"*.

⚠️ That memory is **recall-gated, not eager**. It states the exact lesson of
failure 3 and there is no mechanism that pushed it into this session. A rule-coverage
audit that only reads `.claude/rules/` would have scored failure 3 as "new lesson";
it is not — it is a lesson the project already holds in a layer that does not load.

---

## §N2 — failure 5: the rules were satisfied, and the branch was still DO-NOT-SHIP four times

`verify-before-advancing.md` says *"'Done' means verified done — the checks
actually ran and actually passed"*. On this branch the checks ran and passed
**nine times**, and rounds v1/v4/v5/v6 all returned DO NOT SHIP, three of them on
HIGH behavioural defects. The rule was never violated. It is simply measuring a
different thing than the one that was wrong.

This is the honest reading, and I want to be explicit that it is **not** a
criticism of that rule: a check-based gate cannot detect a state nobody enumerated.
The missing question is one line and belongs next to it:

> **When a fix responds to a review finding, name what the fix made REACHABLE
> before running the gates.** A fix that adds a term to a predicate moves nodes
> across a boundary; the cells on the new side of that boundary have never been
> asserted by anything. #601: `8c87eec` → v5 HIGH, `09d2cb9` → v6 HIGH,
> `796777a` → v7's axis finding. Three rounds, one shape.

---

## §V7 — the datum that argues against writing any of this as prose

The corpus's own summary line (`601-codex-review-rounds.md:21-24`):

> ⚠️ **v7 used a deliberately different brief shape** — three bounded questions
> with an explicit stop condition, instead of open-ended "find what is broken".
> It found an *axis* rather than another *cell*, in one pass.

Rounds v1–v6 were open-ended and found six cells across six passes. v7 was bounded
and found the axis in one. **That is a change to the review brief, not to the rule
corpus** — and on this evidence it outperformed six rounds of a correct, loaded,
eager rule set. I flag it because my own deliverable is a list of prose changes,
and the strongest single result in this corpus says prose was not the lever.

My recommendation, ranked: (1) fix the R2 framing in §M1 — it is actively
misleading and cost three rounds; (2) build §T2's gate; (3) add §N1's rule, the
only genuinely new one, because it is on its third instance; (4) do **not** add
prose for failures 1 or 5 beyond the one line in §N2 — a rule quoted verbatim by
the person who violated it is not a rule problem.

---

## Re-verified before reporting

Re-read at write-up time, after the analysis was drafted:

- `.claude/rules/probes-need-a-control-arm.md` (as injected eagerly into this
  session's context) and `docs/rules-evidence/probes-need-a-control-arm.md:40-167`
  — R2 and R8 text unchanged from first read; the evidence file's R2 section
  confirms both worked cases are "mutation too weak", neither is "mutation
  complete but irrelevant".
- `tests/test_dag_tick.py:565-694` — the `_CLASSIFY_TABLE` comment, the pinned
  `tempo="idle"`, and both meta-tests. Unchanged.
- `git log origin/main..fix/601-dag-tick-needs-human` — still 9 commits, HEAD
  `eda53d6`. Nothing moved under me.
- `.claude/rules/` file count re-run at write-up: still 23.

**Nothing had moved.** One caveat I will not paper over: this session has five
other agents active, and `docs/research/kb/reports/agents/601-codex-review-rounds.md`
is a shared artifact. I re-read its header table but not all 1,176 lines a second
time; if another agent edited its body mid-run, my §V7 quote is the part I
re-verified and the round-by-round detail is the part I did not.

## Verdict summary

| Verdict | Count | Which |
|---|---|---|
| RULE IS WRONG OR MISLEADING | 1 | `probes-need-a-control-arm.md` R2 (§M1) — contributed to failures 2 and 5 |
| NEW RULE NEEDED | 2 | §N1 claims/call-site (3rd instance) · §N2 reachability-delta (1 line) |
| EXISTING RULE NEEDS TEETH | 2 | §T1 (SUSPECT — one route only) · §T2 (axis derivation) |
| EXISTING RULE IS FINE, HUMAN ERROR | 1 | failure 1 — rule quoted verbatim by the author two commits later |

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the audited
  repo: `.claude/rules/`, `docs/rules-evidence/`, `tests/`, and the nine commits
  on `fix/601-dag-tick-needs-human`.
