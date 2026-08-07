# Adversarial critique — #601 reflection fix-list (2026-08-06)

Record replayed against: commits `bd4857c..b6fd9a0` on `fix/601-reflection-fixes`;
`docs/research/kb/reports/session-20260806-review-loop-reflection.md`;
the verdict table at `docs/research/kb/reports/agents/601-codex-review-rounds.md:11-19`
and the verbatim v1 report at `:31-49`;
`dag_tick.py` extracted at `d070cb5` (pre-branch main) and `e9da8cb` (#601 commit 1).

Replay scripts: `scratchpad/replay/probe{1,2,3}.py`; raw output `out{1,2,3}.txt`.

| # | Verdict | Proposal | Fires on its motivating cases? | Shape |
|---|---|---|---|---|
| 1 | **KEEP (enumeration) / KEEP, NARROWED (`illegal_pin`)** | `classifier_tables.py` + `classifier_axes` hk step | enumeration: yes, but one commit earlier and via a different kind than claimed. `illegal_pin`: fails open on **4 of 7** return shapes (control arm A denies) | 5, 6 |
| 2 | **CONVICTED as written** | the "bounded" stop condition | Both readings fail, in opposite directions; its own replay contradicts its own ladder (`:55` vs `:95`) | 3, 5 |
| 3 | **Q-FRESH SURVIVES · Q-SCOPE RIGHT-FOR-WRONG-REASON · Q-CLAIM RIGHT-FOR-WRONG-REASON** | the three brief questions | Q-CLAIM's worked table misattributes 2 of 3 findings to round 2; round 2 had **zero HIGHs** | 5 |
| 4 | **KEEP, NARROWED** | `tests/AGENTS.md` third anti-pattern | It does **not** escape "prose was not the lever"; one third of it is dominated by proposal 1 | 4 |
| 5 | **CONVICTED** | the A2c drop reasoning | The same batch added clauses to **two eager rules** on the grounds that adding a clause to an eager rule does not fire | 3 |

---

## 1 · `classifier_tables.py` + the `classifier_axes` hk step (`b6fd9a0`)

**Restated.** A registry declares, per classifier, the axes its truth table
crosses and the axes it pins; `derive_axes` reads the real axis set out of the
AST; six violation kinds compare declaration against code. Motivating defects:
F8/F12 (`queued_prompt` omitted from `is_needs_human`, rounds 5–6) and F14
(`tempo` pinned on a false premise, round 7).

### 1a · The composite claim is FALSE as stated — but the mechanism is real

Claim under test: *applied at #601's commit 1 it emits `undeclared:
queued_prompt` + `illegal_pin: tempo` + `table_missing` in one run.*

Replay (`probe3.py` → `out3.txt`), four registry-provenance scenarios, verbatim:

```
=== S1 entry BORN at commit 1, author mirrors is_needs_human(state, needs)
   undeclared: the code reads ['pid_alive', 'queued_prompt', 'stall_after_s',
   'state_age_s', 'tempo'] but the registry declares neither a crossed nor a
   pinned axis f
=== S2 entry born at MAIN (gate pre-existing), author ADDS needs at commit 1
   (no violations)
=== S3 the MAIN entry itself, as the gate's adopter would first write it
   (no violations)
=== S4 commit 1 + the round-7 PIN the author actually wrote at commit 8
   illegal_pin: 'tempo' is pinned with the reason 'only matters for WEDGED',
   but the code lets it decide ['DONE'] — classes the table does not declare
   out of scope (i
```

The three violations fire in **three different worlds**, never in one run:

- **`undeclared: queued_prompt` fires only in S1** — the world where the entry is
  born at commit 1. But "applied at commit 1" is only meaningful if the gate
  pre-existed the branch, and in that world (**S2/S3**) the gate is **silent at
  commit 1**. `probe1.py` shows why — at `d070cb5`, *before the branch was cut*:

  ```
  --- MAIN d070cb5 ---
    derived axes : ['pid_alive','queued_prompt','stall_after_s','state','state_age_s','tempo']
    gated_classes: {'pid_alive':['DEAD'], 'queued_prompt':['DONE'], 'stall_after_s':['WEDGED'],
                    'state':['DONE'], 'state_age_s':['WEDGED'], 'tempo':['DONE','WEDGED']}
  ```

  `queued_prompt` was already declared. The axis the proposal claims to name *at
  commit 1* is named **one commit earlier**, by the gate's own adoption.
- **`illegal_pin: tempo` cannot fire at commit 1** — there was no pin and no table
  at commit 1. The `tempo` pin was written at commit 8 (`eda53d6`); S4 confirms it
  fires there, not at commit 1.
- **`table_missing`** is a substring test — `spec.table_symbol not in table_source`
  (`classifier_tables.py:678`). That is the same unanchored-substring shape codex
  filed as v1's LOW against `per_path_tokens` (`601-codex-review-rounds.md:44-46`).
  A comment naming `_CLASSIFY_TABLE` satisfies it.

**This is not a kill — it is shape 6 (misapplied, not wrong) plus shape 5 (the
replay headline overclaims).** The mechanism works; the causal chain is just not
the one advertised. Under S2 it runs: `table_missing` forces the table to exist →
`test_classify_truth_table_axes_match_the_registry` asserts
`frozenset(_AXIS_VALUES) == spec.axes` at **`tests/test_dag_tick.py:824`** →
declaring `needs` at commit 1 forces a `needs` column → the cell
`(blocked, needs≠∅, queued_prompt=True)` is enumerated at commit 1. That cell is F8.

`tests/test_dag_tick.py:824` is the load-bearing line of the entire proposal, and
it is real. **Enumeration half: KEEP.** The correction owed is to prose only:
`classifier_tables.py:26-28` should say the axis is named **when the gate is
adopted**, not "applied at commit 1 that names `queued_prompt`". Naming it earlier
is a better result than the one claimed — which is exactly why the claim should be
fixed rather than defended.

### 1b · `illegal_pin` IS the thing it convicts others of — fails open on 4 of 7 shapes

The module already knows this failure mode, at `classifier_tables.py:344-347`: a
bare-`Enum.MEMBER` requirement made `_gated_classes` return an empty map, "and an
empty map makes every pin vacuously legal: the check would have failed OPEN on the
second classifier registered." It was then fixed **for ternaries**.

The fix does not generalise. `probe2.py` runs one synthetic classifier per return
shape, each pinning `tempo` on round 7's literal false premise, under the shipped
`table_excluded_classes={"WEDGED"}`. Verbatim (`out2.txt`):

```
A_bare_return_CONTROL       axes=['state','tempo']  tempo_gates=['DONE']                -> DENIED (pin refused)
B_ternary_the_patched_shape axes=['state','tempo']  tempo_gates=['DONE','LIVE','tempo'] -> DENIED (pin refused)
C_match_statement           axes=['state','tempo']  tempo_gates=[]                      -> *** PIN ALLOWED ***
D_dict_dispatch             axes=['state','tempo']  tempo_gates=['state','tempo']       -> DENIED (pin refused)
E_name_return               axes=['state','tempo']  tempo_gates=[]                      -> *** PIN ALLOWED ***
F_else_branch_only          axes=['tempo']          tempo_gates=['WEDGED']              -> *** PIN ALLOWED ***
G_method_call_predicate     axes=['state']          tempo_gates=[]                      -> *** PIN ALLOWED ***
```

**Control arm: A — a bare `return K.DONE` under an `if` — DENIES the pin.** The
probe discriminates, so the 4-of-7 fail-open is a result and not a broken harness.

| Shape | Cause | `file:line` |
|---|---|---|
| **C** `match`/`case` | `_gated_classes` walks only `ast.If`. A `match` classifier has zero `If` nodes ⇒ empty map ⇒ **every** pin vacuously legal. | `classifier_tables.py:431-433` |
| **E** `verdict = K.DONE; return verdict` | `_returned_classes` needs an `ast.Attribute` inside the return expression; a bare `Name` yields nothing. | `:354-357` |
| **F** `if …: return WEDGED` / `else: return DONE` | `_returned_classes` reads `branch.body` and never `branch.orelse`. The axis is credited with the `if`-arm class only. | `:348` |
| **G** predicate reached as `self.pred(node)` or via an import | `_follow` and `_axes_in_test` both require `isinstance(call.func, ast.Name)`; an `Attribute` callee is skipped, so the axis is **not derived at all** — `undeclared` is blind too. | `:313`, `:399` |

**F is the kill.** It is not exotic: it is round 7's premise written with an
`else`. An author who writes `if tempo == "active": return WEDGED else: return
DONE` and then declares *"tempo only matters for WEDGED"* gets **PIN ALLOWED** —
from the check whose own docstring at `:421-428` says *"This function checks it:
the pin is legal only when every class the axis can decide is one the table
declares out of scope."* The gate's headline claim survives exactly one syntactic
rearrangement of the code it was derived from.

Two tells that the derivation is textual rather than semantic: B reports
`tempo_gates=['DONE','LIVE','tempo']` and D reports `['state','tempo']` — **axis
names appearing as class names**, because `ast.walk(node.value)` cannot distinguish
`NodeClass.DONE` from `node.tempo`. Both fail *closed* (a wider gated set refuses
more pins), so neither is exploitable today.

**VERDICT 1b: KEEP, NARROWED.** Exact restriction — `_gated_classes` must **fail
closed on a shape it cannot read**: if a classifier contains a `match` statement,
or any `return` whose expression yields no enum member, or any `if` with a
class-returning `orelse`, then `illegal_pin` must treat every axis as gating **all**
classes, so no pin is legal. Anchor: `classifier_tables.py:430`
(`accumulated: dict[str, set[str]] = {}`) — the line where "I could not read this"
currently becomes "nothing gates anything". Until that lands, `:40-51` and
`:421-428` overstate and should say `illegal_pin` is checked only for classifiers
whose class returns are bare `if`-body enum members.

### 1c · Two smaller findings, stated as SUSPECT

- **`find_unlisted` scans 45 modules; the hk step's glob names 5 files**
  (`hk.pkl:270-276`). Under `hk run check --all` — what `mise run lint` runs — the
  step always executes, so the scan is live. Under a plain pre-commit run, a commit
  adding a *new* module with a classifier matches none of the five globs. **SUSPECT**:
  I did not verify hk's per-run glob semantics against the binary, and the `--all`
  path is the gate that matters.
- `graphify` reports a third `classify()` at `command_audit.py:438` that
  `classifier_shaped` does not flag. Consistent with the "2 hits, zero false
  positives" claim only if its return annotation is not a module-local enum. I did
  not confirm which. **SUSPECT.**

---

## 2 · The stop condition in `.claude/skills/adversarial-review/SKILL.md`

**Restated.** *"A BOUNDED round returning SHIP with 0 HIGH and 0 MEDIUM ends the
loop. LOWs become tickets. A SHIP from an OPEN-HUNTING round does not end the loop
— it promotes to a bounded round."* (`SKILL.md:69-73`.) Motivating defect: A3's
unqualified form terminates at v2 and ships five HIGHs.

**Both available replays fail, in opposite directions.**

**Reading 1 — ladder-compliant.** `SKILL.md:55` states *"Round 2+ — MUST be
bounded."* So round 2 is bounded. Round 2's historical verdict
(`601-codex-review-rounds.md:14`) is **SHIP · 2 LOW** = 0 HIGH, 0 MEDIUM. A bounded
SHIP with 0 HIGH and 0 MEDIUM **ends the loop at v2**. What then ships: v4's 1 HIGH
+ v5's 3 HIGH + v6's 1 HIGH + v7's 2 MEDIUM = **5 HIGH and 2 MEDIUM** — byte for
byte the outcome the skill convicts the unqualified form of at `:79-84`. The
qualifier changes nothing on this record.

**Reading 2 — fixed-record, which is what `SKILL.md:95-97` actually does** (it
treats v2 as open-hunting: *"v2's SHIP promotes to a bounded round 3"*). Then:

| Round | Verdict | Under the shipped rule |
|---|---|---|
| v1 | DO NOT SHIP · 2 HIGH | continue |
| v2 | SHIP · 2 LOW | open ⇒ promotes, loop continues |
| v3 | SHIP · 1 LOW | open ⇒ promotes again |
| v4–v6 | DO NOT SHIP · 5 HIGH total | continue |
| v7 | DO NOT SHIP · **2 MEDIUM** | bounded, but MEDIUM ≠ 0 ⇒ **does not end** |

The loop terminates **nowhere in the seven-round record** and demands a round 8.

**These two readings cannot both be the rule, and `SKILL.md:55` and `SKILL.md:95`
assert them respectively.** That is shape 3 (self-refuting): the replay offered as
proof requires round 2 to be open-hunting, 40 lines after the ladder mandates it be
bounded. And the claim at `:96-97` — that a bounded round 3 *"asks the enumeration
question — the question that eventually found the missing axis at v7"* — is a
counterfactual with no record behind it, the same overclaim the post-mortem forbids
at its own line 87 (*"Any proposal claiming a gate would have caught it is
overclaiming"*).

**What fires first — and it also misses.** `SKILL.md:60-65` calls *"Never run a
round against code that has not moved"* **"the safest suppression available…
Prefer it over any round cap."** Replayed on the diff, `dag_tick.py` changed by
**60, 37 and 17** changed lines across the three commits the post-mortem calls
wasted (`42e7c9c`, `cf6e97d`, `b9214ad`), and `42e7c9c` added a whole new
`def is_stalled(`. A diff-based reading fires on **0 of 3** wasted rounds. Only a
behaviour-level reading fires — which is a judgement, not a suppression. The
post-mortem's own "rounds 1–3 produced 3 commits and **zero production change**"
(line 21) is true of *behaviour* and false of *files*; `SKILL.md:59-60` then
converts a function-level observation ("commits 2-5 never touched the function")
into a round-level rule.

**VERDICT: CONVICTED as written.** The finite-co-domain *distinction* underneath —
a SHIP from an unbounded round means "I found nothing", a SHIP from a bounded round
means "the domain is verified" — survives intact and is worth keeping; this is a
conviction of the rule's stated form and stated replay, not of its idea.

Minimum restriction, if it is kept: `SKILL.md:55` ("Round 2+ MUST be bounded") and
`SKILL.md:95-97` (the v2-promotes replay) cannot both stand — strike one. And the
stop condition must say what a bounded round returning **MEDIUM** does, because v7
did exactly that and the rule as written cannot end the loop on its own headline
example.

---

## 3 · Q-FRESH / Q-SCOPE / Q-CLAIM (`SKILL.md:102-134`)

The umbrella claim is at `SKILL.md:105`: *"each of them independently kills a
finding that cost a full round."* Checked one at a time.

### Q-FRESH — **SURVIVES**

*"for every decision→action pair, is the decision re-validated against
freshly-read inputs immediately before the action?"* Claimed to kill the round-4
HIGH at round 1.

Round 4's finding is the classify→execute race (`601-codex-review-rounds.md:16`),
fixed by `8c87eec` *"re-check escalation at execution, not only at classification"*.
That is literally a decision→action pair with no re-validation, and the code was
present at commit 1 — nothing in commits 2–3 created it. The question's answer set
is finite (the decision→action pairs in the diff), so it is a verification question,
not a search question. **It fires, at round 1, on its own motivating case.**

One honest caveat, not a defect in the question: `8c87eec` is one of the three
mutation-verified fixes the batch itself identifies as having *caused the next
round's HIGH* (`tests/AGENTS.md`, and the post-mortem's lines 240–245). Q-FRESH
moves that finding earlier; it does not dissolve the chain that followed it.

### Q-SCOPE — **RIGHT-FOR-WRONG-REASON**

The question is sound. The claim attached to it is not. Round 5 returned **3 HIGH**
(`601-codex-review-rounds.md:17`), of which the `execute_stop` finding became #604.
Round 5 would have run regardless and returned DO NOT SHIP on the other two. So
Q-SCOPE saves **attention within a round**, never a round — which is exactly what
the skill's own body says at `:113-116` (*"it cost a whole round of **attention** to
scope out"*). `SKILL.md:105`'s "kills a finding that cost a full round" is the
overclaim, and it contradicts the paragraph eleven lines below it. Keep the
question; strike Q-SCOPE from the `:105` sentence.

### Q-CLAIM — **RIGHT-FOR-WRONG-REASON**, with a factual error in the worked table

The worked table at `SKILL.md:126-131` attributes two clauses to **"HIGH, round 2"**:

| Clause (per `SKILL.md`) | Claimed | Actual |
|---|---|---|
| `never auto-respawned at any age` | HIGH, round 2 | **HIGH, round 1** — `601-codex-review-rounds.md:37-41` |
| `(project + label dag:needs-human)` | HIGH, round 2 | **HIGH, round 1** — `:31-35`, which quotes `dag_tick.py:491` emitting exactly that string |
| `never respawned BY THIS TICK` | HIGH, round 4 | HIGH, round 4 ✓ |

Round 2 had **no HIGH findings at all**: the verdict table at `:14` reads
`v2 | SHIP | 2 LOW`, and v1's own severity count at `:49` reads
`**HIGH 2 · MEDIUM 0 · LOW 1**`. The attribution is impossible on its face.

The consequence is not cosmetic. Two of the three clauses were **already found in
round 1**, so Q-CLAIM saves **zero rounds** on them; its real value is the third,
moving `never respawned BY THIS TICK` from round 4 to round 1. `SKILL.md:132`'s
*"Three findings, two rounds, one string, one minute of checking"* should read
**one finding moved from round 4 to round 1; the other two were already round-1
findings.** The question survives — Q-CLAIM is the only one of the three aimed at
the failure class the post-mortem calls its third recorded instance — but its
stated payoff is roughly a third of what is claimed.

---

## 4 · `tests/AGENTS.md`'s third anti-pattern (`47eb739`)

**Does it escape "prose was not the lever"? No — and the honest answer is that it
does not need to, but one third of it is dominated.**

It does not escape. The post-mortem's measurement stands unchallenged: **21 of 23
rules were eager and every gate was green on all 9 commits** while 4 of 7 rounds
returned DO NOT SHIP (post-mortem lines 258-260). Nothing in this record shows
instruction prose changing a reviewer's or an implementer's behaviour, and this
addition has no mechanism the other 23 lacked. Any claim that it will fire is a
bet, not a replay.

What it has instead is a **cost argument that actually holds**, and one that was
misreported:

- Placement is `nested`, so it is zero eager cost — correct.
- **The measured headroom in the post-mortem is wrong.** Line 100 says *"Measured
  headroom: 4,888 B under the 12,000 AGM-003 cap."* 4,888 B is the file's **total
  size** at `bd4857c` (`git show bd4857c:tests/AGENTS.md | wc -c` → `4888`), not its
  headroom. True headroom was 12,000 − 4,888 = **7,112 B**. Post-addition the file
  is **6,084 B**, leaving 5,916 B. The gate is not breached and the error is in the
  safe direction — but it is the exact failure `verify-before-advancing.md`'s own
  closing block names: a number carried without its condition.

**What is dominated (shape 4).** The addition restates the axis-derivation
definition — *"the axes are the union of the function's own parameters and every
subject field read by any predicate it calls"* — which proposal 1 now **machine-
enforces** (`classifier_tables.py:23-24`, asserted at `tests/test_dag_tick.py:824`).
It is also in `SKILL.md:192-194`. That is three prose copies of one rule a gate
already owns; the gate fires first on every branch, and three copies is three
places to drift.

**What is NOT dominated, and is the reason to keep it.** Two claims no gate covers:

1. *"deleting the fix breaks ONLY the arm you just wrote" is the SIGNATURE OF THE
   FAILURE, not evidence of quality* — this **inverts an existing belief** rather
   than adding a directive. That is a different kind of prose from the 23 rules the
   record convicts: those competed for compliance, this one reinterprets a signal
   the author was already reading. Whether that difference matters is untested, but
   it is not the same bet.
2. *never edit an expected value to make a test pass* — nothing machine-checks it.

**VERDICT: KEEP, NARROWED.** Exact restriction: delete the axis-derivation
definition (the two sentences from *"which is derivable with no judgement"* through
*"every `Node` field its predicates read"*) and replace with a pointer to
`python/src/dotfiles_setup/classifier_tables.py`, which enforces it. Keep the
mutation-signature paragraph and the never-edit-an-expected-value clause verbatim.
And state plainly in the commit body that this is a bet against a record that says
prose does not fire — an unexamined "it's cheap so it's fine" is the thing the
caller asked me not to accept.

---

## 5 · The A2c decision — the write-time operator-string audit that was dropped

**Restated.** A2c (post-mortem lines 132-138) would audit every clause of an
operator-facing string against an enforcing `file:line` **at write time**. Only its
review-time half shipped, as Q-CLAIM. The stated reason: a further clause in an
eager rule is the exact intervention the record shows does not fire.

**The reasoning is CONVICTED, on the batch's own diff.**

The same five commits added a clause to **two eager rules**:

- `.claude/rules/agent-report-persistence.md` rule 5 — `f775f93` adds
  *"**both its brief and its report**"*.
- `.claude/rules/clarify-before-acting.md` — `8530273` rewrites the matcher clause
  to `Bash|AskUserQuestion|Edit|Write|NotebookEdit`.

Neither file carries `paths:` front-matter (checked: both open directly on their
`# ` heading), so both are `rule_unscoped` — the eager class. **The batch applied
the intervention it declared does not fire, twice, while declining A2c on the
grounds that it does not fire.** No line in the batch says why A5 escapes the
verdict and A2c does not. That is shape 3: the reasoning refutes a decision the
same author made one commit earlier.

Two further problems with the reasoning as stated:

1. **"The only available placement is eager prose" is false.** A2c's review-time
   half shipped into a *skill* (Q-CLAIM). A write-time half has at least the same
   placement available, and this repo already runs a narrower machine analogue of
   exactly this check — `dotfiles-setup token-audit` / `per_path_tokens`, whose
   whole purpose is binding a declared token to the call site that enforces it
   (`python/AGENTS.md` § Verification contracts). Whether that generalises to
   arbitrary operator strings is a real question; "eager prose or nothing" is not.
2. **The reasoning proves too much.** If "another clause in an eager rule does not
   fire" is decisive, it convicts every future amendment to the eager corpus,
   including the two in this batch. A principle that would forbid what you just did
   is not a principle you are applying.

**The cost of being wrong is on the record and rising.** The post-mortem's own line
269-270: failure class 4 (a claim with no enforcing call site) is on its **third**
recorded instance, and `secrets-out-of-the-shell-env.md` "documents it twice and
still did not promote it to a directive." The A2c decision is the **third** time
this class was filed rather than directed, reached by the same reasoning that
produced the first two. That is the strongest available evidence that the reasoning
is the thing generating the recurrence.

**VERDICT: CONVICTED.** Not "build A2c as an eager clause" — that specific placement
may well be wrong. The conviction is of the *justification*: the drop was decided on
a premise the same batch violates twice and that forecloses placements it never
evaluated. Re-decide it on the merits, or state explicitly why the eager-rule
verdict binds A2c and not `agent-report-persistence.md` rule 5.

---

## What survives, and what the survivors do NOT cover

Surviving: the enumeration half of proposal 1 (via `tests/test_dag_tick.py:824`),
Q-FRESH intact, Q-SCOPE and Q-CLAIM as questions, the mutation-signature half of
proposal 4, and the bounded/open *distinction* under proposal 2.

**Residual — motivating defects that no surviving proposal catches:**

1. **F14's shape one refactor away.** With `illegal_pin` failing open on `match`,
   `else`-arm returns, `Name` returns and method-call predicates, round 7's exact
   false premise is re-writable in legal form today. Until 1b's restriction lands,
   the gate's headline defect is uncovered.
2. **A classifier reached through an imported or method predicate is invisible to
   BOTH `undeclared` and `illegal_pin`** (shape G derived `axes=['state']` — it lost
   `tempo` entirely). The proposal's own motivating case only works because
   `is_terminal` happens to be a module-level function.
3. **Rounds 1–3, the waste the post-mortem calls the real failure**, are caught by
   nothing that shipped: the stop condition ends the loop at v2 or never (§2), and
   the no-movement suppression fires on 0 of 3 (§2).
4. **The write-time half of failure class 4** — third recorded instance, still
   unowned (§5).

## Re-verified before reporting

Re-read at write-up time, after all replays: `.claude/skills/adversarial-review/SKILL.md`
(lines 55, 69-73, 95-97, 105, 113-116, 126-134 — unchanged since first read),
`classifier_tables.py:344-357, 421-433, 678`, `tests/AGENTS.md` (re-measured at
6,084 B), and `git diff bd4857c..HEAD -- .claude/rules/` (re-run at write-up; both
eager-rule hunks still present). Nothing had moved under me.

Control arms run: probe2 shape A (a pin the gate MUST refuse) → DENIED, so the
4-of-7 fail-open discriminates. probe3 S1 (a registry the gate MUST reject) →
`undeclared` fires, so the "(no violations)" in S2/S3 is a real negative.

---

# APPENDIX · The proposed REPLACEMENT stop condition (round 2 of this critique)

**Restated.** A bounded round ends the loop when its enumerated questions have been
ANSWERED, regardless of what it found; findings are dispositioned (fixed here or
ticketed); a further round happens only if the ENUMERATION changed, not because the
code changed. A round with no enumerated domain cannot end the loop by any outcome.

**Overall: KEEP, NARROWED.** It is strictly better than the shipped rule — it
terminates nowhere in v1–v6, where the shipped rule terminates at v2 and ships five
HIGHs. Three things must be said out loud before it ships: it does **not** terminate
at v7 (it terminates at v8), its bounded/unbounded test is **one judgement call away
from shipping the tempo axis**, and it does **nothing** for rounds 1–3.

The caller's diagnosis is **confirmed**: the shipped rule reads its own *prescription*
("round 2+ must be bounded") as a *fact about the round that ran*. In the record v2's
brief was open hunting — the prescription was violated, not satisfied. The replacement
correctly keys on a property of the round rather than on its ordinal. That is the
right repair.

## Q1 · Does it terminate at v7? — **REFUTED. It terminates at v8.**

v7's three questions were answered (`601-codex-review-rounds.md:1122-1139`): Q1 "no
cell wrong", Q2 **"the four axes are NOT complete — `tempo` is a fifth"**, Q3 "the
meta-tests are weak". Under the replacement the round therefore ends and the 2 MEDIUMs
are dispositioned in-unit — which is exactly what `8706670` did.

But dispositioning them **changed the enumeration**, verified in that commit's diff:

```
-    assert len(_CLASSIFY_TABLE) == len(expected_cells) == 32
+    assert len(_CLASSIFY_TABLE) == len(expected_cells) == 64
-    # tempo is pinned "idle". Stated so its absence reads as deliberate.
+    tempos = [_IDLE, _ACTIVE]
```

4 axes / 32 cells → 5 axes / 64 cells. The rule's own re-open clause — *"a further
round happens only if the ENUMERATION itself changed"* — therefore **fires**, and
prescribes round 8 over the 32 newly-reachable cells.

**This is not a defect; it is the rule working, and the claim needs restating.** 32
cells that no round has ever verified now exist. A round over them is proportionate,
and it is bounded, so it terminates. Say "it terminates at v8, having verified the
enumeration it ended up with" — not "it terminates at v7".

## Q2 · Does it terminate anywhere in v1–v6? — **NO. Clean pass.**

Mechanically discriminated rather than asserted. Searching each verbatim brief for a
stated cardinality on its answer set (`\d+ (rows|cells|axes|questions)`, or "exactly
N questions"):

```
--- brief v1: 0    --- brief v5: 0
--- brief v2: 0    --- brief v6: 0
--- brief v3: 0    --- brief v7: 2
--- brief v4: 0          :1109  ... × pid_alive, **32 rows** — with `tempo="idle"` ...
                         :1120  ## YOUR TASK — exactly three questions, nothing else
```

**Control arm: the same pattern returns 2 hits on v7**, so the six zeros are real
negatives and not a broken regex. No round in v1–v6 has an enumerated domain; none of
them can end the loop. **Your rule survives its must-not test.**

### The narrowing, and it is not theoretical — v6 is a one-judgement-call near-miss

The rule says "a round with no enumerated domain" and never says how that is
established. **Brief v6 has FIVE numbered questions** (`:1028-1049`) and reads as
bounded at a glance. It is not: its question 5 is *"**Anything else `09d2cb9`
touched.**"* — a catch-all with no co-domain — and its framing at `:1025-1026` is
*"what did `09d2cb9` break?"*, a search question. It states no cardinality.

If v6 were classified bounded, it answered its questions and **the loop ends at v6 —
shipping the missing `tempo` axis**, the single finding this entire skill exists to
have caught. The rule's correctness on this record rests on one classification call
about the most enumeration-looking brief in the corpus.

**Exact restriction:** *a round is BOUNDED only if its brief states a domain with a
CARDINALITY — N cells over M axes, K call sites, J strings. Numbered questions are not
an enumeration; a question with a catch-all is not enumerated.* That test is
mechanically checkable (the grep above is the whole implementation), it discriminates
v6 from v7 correctly, and proposal 1's registry now makes the cardinality **derivable**
for any classifier table rather than asserted by the brief's author.

## Q3 · The "enumeration changed" clause — attacked hardest

**It does NOT re-open indefinitely, and the reason is worth keeping.** An enumeration
changes by gaining axes or cells, and the axis set is bounded above by what
`derive_axes` reads out of the code — 7 axes for `dag_tick.classify` at HEAD
(`probe1.py`). **Proposal 1 mechanically bounds proposal 2's re-open clause.** The
regress is finite and small; two proposals in this batch turn out to need each other.

**But the clause has a structural self-trigger, and you should not ship without
naming it.** The bounded template's question 2 (`SKILL.md:191-194`) exists *precisely*
to find enumeration errors. Any finding it produces changes the enumeration. Therefore:

> **Whenever the enumeration question does its job, the re-open clause fires.**
> A successful bounded round always costs one more round, by construction.

That is a real cost, not a bug — the alternative is shipping an enumeration nobody
verified. The refinement available, if you want it: distinguish *"the enumeration
changed as a result of dispositioning THIS round's findings"* — which mandates exactly
one more bounded round, scoped to the delta (here: the 32 new `tempo="active"` cells,
not all 64) — from *"the enumeration changed independently"* (the code gained an
axis), which is a fresh loop. Without that split the clause is honest but pays full
freight every time.

**One dominance finding falls out of this clause** — see correction C below.

## Q4 · Does it help rounds 1–3? — **NO. Your suspicion is correct; state it.**

The rule says an unbounded round "promotes to a bounded round". Nothing forces the
promotion to actually happen. Replayed: v2 is open → promotes; **v3 is also open**
(cardinality 0, above) → promotes again. v3 still runs. Rounds 1–3 still produce three
commits and no behavioural change.

It is in fact **worse than the shipped rule on this segment**: the shipped rule's
ladder reading terminates at v2, so v3 never runs. Your rule runs v3.

**That is the right trade and should be stated as one:** the shipped rule's early
termination was correct-by-accident and cost five HIGHs and two MEDIUMs. Buying v4–v7
back at the price of v3 is a good deal. But it means the residual stands unchanged —
**nothing in this batch addresses rounds 1–3, the waste the post-mortem calls the real
failure.** Claim the v4–v7 correctness; do not imply coverage of 1–3.

---

# Three small corrections, verified against the record

## A · Q-CLAIM's worked table (`SKILL.md:126-131`) — corrected rows

| Clause | Currently says | Correct | Anchor |
|---|---|---|---|
| `escalated — state=blocked with a needs payload` | fine | fine (unchanged) | — |
| `never auto-respawned at any age` | HIGH, **round 2** | **HIGH, round 1** | `601-codex-review-rounds.md:37-41` |
| `(project + label dag:needs-human)` | HIGH, **round 2** | **HIGH, round 1** | `:31-35`, quoting `dag_tick.py:491` |
| `never respawned BY THIS TICK` | HIGH, round 4 | HIGH, round 4 ✓ | — |

Round 2 had **zero** HIGH findings: `:14` reads `v2 | SHIP | 2 LOW`, and v1's own
severity count at `:49` reads `**HIGH 2 · MEDIUM 0 · LOW 1**`.

**Corrected saving for `SKILL.md:132`** — replace *"Three findings, two rounds, one
string, one minute of checking"* with:

> **One finding moves from round 4 to round 1. The other two clauses were already
> round-1 findings, so Q-CLAIM saves no rounds on them — it makes them cheaper to
> find, not earlier.** One string, one minute of checking.

Q-CLAIM stays: it is still the only one of the three aimed at the failure class the
post-mortem calls its third recorded instance.

## B · `tests/AGENTS.md`'s axis-derivation sentence — **the overlap is NOT total; it stays**

This corrects my §4 restriction. The gate does **not** enforce the definition
unconditionally. `probe2.py` shape G:

```
G_method_call_predicate     axes=['state']   tempo_gates=[]   -> *** PIN ALLOWED ***
```

A predicate reached as `self.pred(node)` or through an import is skipped by both
`_follow` and `_axes_in_test` (`classifier_tables.py:313`, `:399`), so **`tempo` is
not derived at all** — the axis vanishes from the enumeration and `undeclared` never
fires. The gate implements *"every subject field read by any predicate it calls"* only
for **same-module predicates invoked by a bare name**. The prose states it without
that qualifier, so it covers exactly the case the gate is blind to.

**Revised restriction for §4:** keep the sentence; add the qualifier rather than
delete it — *"`dotfiles-setup classifier-axes` derives this automatically for
same-module predicates called by name; you carry it yourself for predicates reached
through an import or a method."* Everything else in my §4 verdict stands: the
mutation-signature paragraph and the never-edit-an-expected-value clause are
uncovered by any gate and are the reason the addition earns its bytes.

## C · "Never run a round against code that has not moved" (`SKILL.md:60-65`) — **DELETE, for dominance, not for firing 0 times**

Firing 0 of 3 is not by itself grounds for deletion — a safe, true rule that happened
not to bite once is worth keeping. The grounds are stronger: **your replacement's
re-open clause dominates it on every branch.**

- The suppression blocks a round when *code* has not moved.
- The replacement blocks a round unless the *enumeration* has changed — which also
  blocks every round where code moved but the enumeration did not, i.e. **all three of
  #601's wasted rounds' successors, and more besides.**

There is no branch on which the suppression changes an outcome the replacement has not
already decided. That is shape 4, inert by construction — the same verdict this
project's own DROPPED table gave REGRESSION-ECHO.

Delete the paragraph. If any of it is kept, the sentence at `:59-60` must go
regardless: it cites *"commits 2-5 never touched the function"* — a function-level
observation — to justify a round-level rule, and at the diff level `dag_tick.py` moved
**60, 37 and 17** changed lines across `42e7c9c`/`cf6e97d`/`b9214ad`, with `42e7c9c`
adding a whole new `def is_stalled(`.

## Re-verified before reporting (round 2)

Re-read at write-up time: brief v6 (`:979-1080`) and brief v7 (`:1084-1174`) in full;
the `8706670` diff; `SKILL.md:60-65`, `:126-134`, `:191-194`. The cardinality scan was
re-run at write-up, not quoted from the first pass. Nothing had moved under me.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under
  critique; issues #601, #604, map #556.
