# #601 — loop forensics: the causal chain across 7 adversarial review rounds

Forensics on a closed record. No new defects hunted, no fixes proposed.

**Corpus:** `docs/research/kb/reports/agents/601-codex-review-rounds.md` (7
reports + 7 briefs, verbatim); the 9 commits on `fix/601-dag-tick-needs-human`;
`python/src/dotfiles_setup/dag_tick.py`; `tests/test_dag_tick.py`;
`gh issue view 601`.

---

## 1. The 9 commits

| # | SHA | Subject | Round it answers | Changed |
|---|---|---|---|---|
| 1 | `e9da8cb` | classify `blocked ∧ needs≠∅` as NEEDS_HUMAN, never respawn | — (the fix) | prod + tests |
| 2 | `42e7c9c` | carry the stall fact into the NEEDS_HUMAN note | in-house 2-axis review | prod + tests |
| 3 | `cf6e97d` | scope the NEEDS_HUMAN log line to what this module does | v1 | **prose only** |
| 4 | `b9214ad` | arm the honesty check with the review's own counterexample | v2 | **tests + prose** |
| 5 | `397675b` | pin the reason by golden equality, not substrings | v3 | **tests only** |
| 6 | `8c87eec` | re-check escalation at execution, not only at classification | v4 | prod + tests |
| 7 | `09d2cb9` | a queued human reply is not an escalation — deliver it | v5 | prod + tests |
| 8 | `796777a` | surface a queued reply on a LIVE node instead of going silent | v6 | prod + tests |
| 9 | `eda53d6` | enumerate the classification truth table instead of patching cells | v6→v7 pivot | **tests only** |

**Three of nine commits (3, 4, 5) changed no production behaviour at all.** They
consumed rounds 1–3 and answered findings that two of those rounds themselves
graded `SHIP`.

---

## 2. The full finding ledger — 15 findings, with causation

Legend for **Origin**: `PRE` = predates the branch · `C<n>` = introduced by
commit *n* of this session · `C1-contract` = the defect exists only because
commit 1 made a promise the old code never made.

| # | Rd | Sev | Defect (one line) | Origin | Class | Reachable before the fix that exposed it? |
|---|---|---|---|---|---|---|
| F1 | v1 | HIGH | Reason string says `project + label dag:needs-human`; neither action is performed. Projection unowned. | **C1** | operator text (+ spec scope) | Yes — round 0. Auditable against the code the moment C1 was written. |
| F2 | v1 | HIGH | "never auto-respawned" claims a guarantee only the harness supervisor could make. | **C1** | operator text | Yes — round 0. |
| F3 | v1 | LOW | `per_path_tokens` is unanchored substring membership; commented-out wiring stays green. | **PRE** (engine-wide, all 115 contracts) | contract engine | Yes. Never fixed; accepted. |
| F4 | v2 | LOW | New comment says #575 deferred the projection **OWNER**; #575 in fact **assigns** it to the scheduler. | **C3** (the fix for F1) | doc accuracy | No — the wrong sentence did not exist before C3. |
| F5 | v2 | LOW | Wording test not semantically control-armed; loose fragment `is NOT done here` unbound to its subject. | **C3** (the test added by the fix for F1) | test strength | No — the test did not exist before C3. |
| F6 | v3 | LOW | Honesty predicate still bypassable: a trailing self-contradicting sentence nothing constrains. | **C4** (the fix for F5) | test strength | **Yes, in class.** Not a new hole — the same hole. "A substring guard cannot judge meaning" was fully knowable at F5. |
| F7 | v4 | **HIGH** | `never respawned BY THIS TICK` is FALSE: `execute_respawn` re-read only roster/pid, never `state.json`/`needs`; a node planned DEAD→RESPAWN that escalated in between was respawned. | **C1-contract** (code path is `PRE`/#578; the *promise* is C1's) | **production** | **Yes — from round 1.** Commits 2–5 never touched `execute_respawn`. Nothing but the brief changed. |
| F8 | v5 | **HIGH** | `blocked+needs+queuedPrompt` → NEEDS_HUMAN forever: the human already answered and the answer is never delivered. | **C1** | **production** | **Yes — from round 1.** `is_needs_human` ignored `queued_prompt` from the first line it was written. |
| F9 | v5 | **HIGH** | Race narrowed, not closed: order was state re-check → roster read → `Popen`; a node can escalate during the roster read (`race2`). | **C6** (the fix for F7) | **production** | No — genuinely created by C6's check placement. |
| F10 | v5 | **HIGH** | `execute_stop` has the analogous stale-state defect: a reply arriving between classify and execute makes the node non-terminal, `claude stop` fires anyway. | **PRE** (#578) | **production** | Yes — from round 1. Out of scope; filed **#604**. Surfaced only because the v5 brief explicitly commissioned it as the implementer's own hunch. |
| F11 | v5 | LOW | `test_execute_respawn_skips_when_pid_alive_now` silently disarmed — the new unreadable-state SKIP short-circuits it before the pid check. | **C6** (the fix for F7) | test strength | No — created by C6. A *pre-existing* test was disarmed by a new guard. |
| F12 | v6 | **HIGH** | `blocked+needs+queued+pid_alive=True` falls through every branch to ALIVE: no action, no note. Less visible than before #601 existed. | **C7** (the fix for F8) | **production** | **No — genuinely created by C7.** The only finding in the whole record that a prior enumeration could not have named without the fix. |
| F13 | v6 | LOW | Reordering traded TOCTOU: pid check now behind the state read; another actor can revive the node during that I/O (`race3`). | **C7** (the fix for F9) | **production** | No — created by C7's reorder. |
| F14 | v7 | MED | `tempo` is a **fifth** class-changing axis, pinned away by the truth table (`is_terminal` consumes it). | **C9** (the table) / underlying fact `PRE` | test strength / enumeration | Yes in fact, no in artifact — the table didn't exist before C9. |
| F15 | v7 | MED | Meta-tests don't hold the expected column honest: coverage ignores it; reachability checks only its value *set*. A table with 27 arbitrary ALIVE rows passes both. | **C9** | test strength | No — created by C9. |

### Tallies

| Cut | Count |
|---|---|
| Total findings | **15** |
| HIGH | **7** (F1, F2, F7, F8, F9, F10, F12) |
| Introduced by a fix for an earlier round **in this session** | **9 / 15** (F4, F5, F6, F9, F11, F12, F13, F14, F15) — **60%** |
| Introduced by the original fix commit `e9da8cb` | **4** (F1, F2, F7, F8) — including **2 of the 3 real behavioural HIGHs** |
| Genuinely pre-existing on `origin/main` | **2** (F3 engine LOW, F10 `execute_stop`) |
| **HIGHs that were reachable from round 1 and found later only because the BRIEF changed** | **F7, F8, F10 — 3 of 7** |
| **HIGHs genuinely created by a fix, unfindable earlier** | **F9, F12 — 2 of 7** |

### By class

| Class | Findings | Rounds spent |
|---|---|---|
| Production behaviour | F7, F8, F9, F10, F12, F13 — **6** | v4, v5, v6 |
| Test strength | F5, F6, F11, F14, F15 — **5** | v2, v3, v5, v7 |
| Operator-facing text | F1, F2 — **2** | v1 |
| Documentation accuracy | F4 — **1** | v2 |
| Contract engine (pre-existing, accepted) | F3 — **1** | v1 |

---

## 3. The two sub-loops

The record is not one loop. It is two, with different mechanics, and **both
terminated by the same move** — replacing a point-fix with a structure that has
a completion criterion.

### Loop A — the prose/guard loop (rounds 1→3, commits 3–5)

```
C1 writes a reason string with two unenforced claims
  → v1: F1, F2 (HIGH, text)
  → C3 rewrites the string + adds a guard test
      → v2: F4 (the new sentence is wrong), F5 (the new guard is loose)
      → C4 tightens the guard to contiguous clauses
          → v3: F6 (append one more sentence; guard defeated again)
          → C5 ABANDONS substrings for GOLDEN EQUALITY  ← loop ends
```

Three rounds, three commits, **zero production change**. The loop was
unwinnable by construction and the v3 reviewer said so in as many words: the
check is *"an exact-template guard, not a semantic classifier"*. Each tightening
bought one counterexample's worth of ground against an adversary who can always
append a sentence. It ended when the guard's *shape* changed to one with a
completion criterion ("any textual change fails").

**Rounds 2 and 3 both returned `SHIP`.** Commits 4 and 5 were written against a
SHIP verdict with 0 HIGH and 0 MEDIUM.

### Loop B — the state-space loop (rounds 4→6, commits 6–8)

```
v4 asks a NEW question ("is the string TRUE?") → F7 (HIGH, real bug)
  → C6 adds an execute-time escalation re-check
      → v5: F9 (residual race from C6's ordering), F11 (C6 disarmed a test),
             F8 (HIGH, latent since C1 — brief asked the inverse question),
             F10 (HIGH, pre-existing → #604)
      → C7 adds `queued_prompt` to is_needs_human + reorders the checks
          → v6: F12 (HIGH — the queued+ALIVE cell C7 opened),
                 F13 (LOW — the PID TOCTOU C7's reorder opened)
          → C8 fixes both, and the F13 fix is STRUCTURAL:
             "both reads first, both decisions after" — not another swap
  → C9 ENUMERATES the 4-axis cross product (32 rows)  ← loop ends
```

Each fix opened a cell; the next round walked into it. It ended when the
implementer stopped patching cells and enumerated the space.

---

## 4. The single sharpest datum: `queued_prompt` was on the table at commit 1

`Node.queued_prompt` and `is_terminal(state, tempo, *, queued_prompt)` exist on
**`origin/main`** — `dag_tick.py:195` and `:262` of the pre-branch file. They
predate #601 entirely.

Commit 1 wrote:

```python
def is_needs_human(state: str | None, needs: str | None) -> bool:
```

— a sibling predicate over the same `Node`, **omitting an axis its own sibling
two functions above already consumed.** The census path at
`e9da8cb:dag_tick.py:772` was already populating `queued_prompt=bool(data.get("queuedPrompt"))`.

That omission is F8 (HIGH, v5) and, transitively, F12 (HIGH, v6) — the fix for
F8 is what opened F12's cell. **Two of the three real behavioural HIGHs, and
two full rounds, trace to one missing parameter that was visible in the
adjacent function signature at the moment the first line of the fix was
written.**

No judgement was required to catch it. A mechanical rule — *the axes of a
classifier are the union of `classify()`'s parameters and every field the
predicates it calls read* — names `state`, `tempo`, `needs`, `queued_prompt`,
`pid_alive`, `state_age_s` from signatures alone. That rule, applied at commit
1, produces the exact table that shipped as commit 9, **and** it names `tempo`
— which is F14, the finding round 7 still had to report against the table.

---

## 5. Brief v1–v6 vs brief v7 — quantified

|  | v1–v6 | v7 |
|---|---|---|
| Rounds | 6 | 1 |
| Findings | 13 | 2 |
| HIGH | 7 | **0** |
| Convergence | HIGH-per-round `2 · 0 · 0 · 1 · 3 · 1` — never reached and held zero | terminated |
| Shape of what was found | **cells** (one reachable combination at a time) | **an axis** (`tempo` — the whole missing dimension) |
| Brief framing | "find what is WRONG" + an *open* attack list ("Do not limit yourself to this list") | 3 numbered questions, "nothing else" |
| Completion criterion | none | explicit: *"If (1) no cell is wrong, (2) four axes complete, (3) meta-tests hold, then SHIP and ZERO findings"* |
| Explicit exclusions | none | 5 (`v1–v6` re-reports, `execute_stop`, sandbox limits, style/wording, manufactured findings) |
| Brief size | v1 = 122 lines / 885 words | v7 = 89 lines / 676 words |

**The difference is not length, and not reviewer quality.** Same reviewer
(`codex-cli 0.146.0`), same model, same `--sandbox read-only`, same
`model_reasoning_effort=high`, same repository. v7 is only 24% shorter than v1.
What changed is that v7 is **closed** — "complete" is a defensible answer.

The mechanism, stated plainly: under an unbounded "find what is broken" brief,
a reviewer's cheapest defensible output is *one more finding*, and the cheapest
finding available is always another cell or another string. Nothing in the
brief rewards reasoning about the *space*, and "I found nothing" reads as a
failed review — briefs v3–v6 each said in prose that a clean SHIP was
acceptable, and **it did not work**: v3 said SHIP and the loop ran four more
rounds anyway. Prose permission is not a stop condition. A stop condition is a
sentence that names the specific answers which end the round.

---

## 6. What the record shows about *when* the diagnosis was available

Brief v7's preamble contains the correct diagnosis, verbatim:

> Every HIGH was **the same shape**: a reachable combination of
> `state × needs × queuedPrompt × pid_alive` that nobody had enumerated. […]
> The briefs asked "what is broken", which has no completion criterion.

**That diagnosis was derivable one round earlier.** Brief v6 already states
*"v5's HIGH 1 was introduced by the fix for v4's HIGH"* and asks *"what did
`09d2cb9` break?"* — which is the **cell-level** version of the question. Round
6 duly returned the next cell (F12). The step from *"what did this fix break"*
to *"what is the space of things a fix can break"* is one inference, and it took
one more round than the evidence on the page required.

Cost of that one-round delay: round 6, commit 8, and one HIGH finding.

---

## 7. Synthesis — the smallest mechanical change that collapses 7 rounds into ≤2

Ranked by rounds saved per unit of effort. All five are mechanical; none is
"be more careful".

### R1 — Derive the axis list from the classifier's own signatures, and enumerate the cross product, **before writing the fix**. (saves ~3 rounds)

The rule, applied literally: *list `classify()`'s parameters, plus every `Node`
field read by any predicate `classify()` calls. That is the axis set. Cross it.
Fill each cell by hand from intended semantics. Then write the fix.*

- Names `queued_prompt` at commit 1 → **F8 dies** → **F12 never exists** (it is
  only reachable because F8's fix opened it) → **rounds 5 and 6 collapse.**
- Names `tempo` → **F14 dies** at round 7.
- Cost: ~30 lines of table. It shipped anyway, as commit 9, **8 commits late.**
- The table's own meta-tests (F15's subject) are the second-order version of the
  same rule: compute coverage from the axis lists rather than hardcoding it, so
  adding an axis fails loudly.

### R2 — Audit every clause of an operator-facing string against an enforcing `file:line` at write time. (saves ~2 rounds)

For each clause of a reason/log string, name the line of code that makes it
true. A clause with no enforcing line is deleted or narrowed **before commit**.

- **F1, F2 die** (claims about actions no code performs) → round 1's HIGHs go.
- **F7 dies** — `never respawned BY THIS TICK` has no enforcing line in
  `execute_respawn`, which re-read only the roster. That is a one-minute check
  that took until round 4 to run, and only because brief v4 invented the
  question: *"Every round so far has attacked whether the CHECK constrains the
  string. Nobody has yet audited whether the string itself is TRUE."*
- Loop A never starts: F4, F5, F6 are all downstream of C3, which exists only to
  repair F1/F2.

### R3 — A `SHIP` verdict with 0 HIGH / 0 MEDIUM ends the loop. LOW findings become a ticket, not a commit. (saves ~2 rounds)

Rounds 2 and 3 returned `SHIP`. Commits 4 and 5 were written against them and
produced **zero production change**; commit 4 produced F6, another LOW, which
bought round 3.

Honest counterpoint, stated rather than smoothed: commit 5 (golden equality) is
what made brief v4's "is the string TRUE?" question natural. But the question
was the *implementer's reframing*, not the commit's — it could have been asked
of the identical string at round 2. The round was bought by the reframing, not
by the commit.

### R4 — Every fix to a predicate ships with the enumeration of the cells it makes newly reachable. (saves 1 round)

Adding `not queued_prompt` to `is_needs_human` changes exactly two cells:
`blocked+needs+queued+dead` and `blocked+needs+queued+alive`. Commit 7 tested
only the first. The v6 report says so directly: *"The new tests prove only
dead-PID delivery — `test_dag_tick.py:375` explicitly supplies
`pid_alive=False`, and the end-to-end fixture uses an empty roster."*

One test row, one HIGH round (F12) saved. Same rule catches **F11**: a new guard
placed ahead of an existing one silently disarms the test behind it — enumerate
what the guard now short-circuits.

### R5 — Bound every review brief: N questions, an explicit stop condition naming the answers that end the round, an explicit do-not list. (saves the tail)

This is v7's shape and it is the one intervention with a measured before/after
inside this very record: 6 unbounded rounds found cells and never converged;
1 bounded round found the axis and terminated. Note it is **not** achieved by
adding "a clean SHIP is acceptable" to the prose — v3, v4, v5 and v6 all said
that, and all four kept going.

### The collapsed counterfactual

With **R1 + R2** alone applied at commit 1:

- F1, F2, F7, F8, F12, F14 never occur.
- The execute-time re-check ships in commit 1 (R2 forces it: the promise needs
  an enforcing line), so F9/F13 — the ordering races — surface in **one** round
  against the initial commit, where the structural answer commit 8 eventually
  found ("both reads first, both decisions after") is available immediately
  rather than after two swaps.
- Remaining for round 1: F9/F13 as one ordering finding, F3 (pre-existing engine
  LOW, accepted), F10 (pre-existing → #604), F15 (meta-test strength).
- **Round 2 confirms.** Two rounds, 2–3 commits.

---

## 8. Unvarnished summary

1. **Nine of fifteen findings (60%) would not exist without a previous round's
   fix.** The loop was largely self-fed.
2. **But that is not the main cost.** Only **2 of 7 HIGHs** (F9, F12) were
   genuinely un-findable earlier. **3 of 7** (F7, F8, F10) were reachable from
   round 1 and were found later *purely because the brief finally asked the
   right question*. The dominant failure is not that fixes caused bugs — it is
   that four rounds of briefs asked the wrong question about a program that had
   not changed in the relevant place.
3. **Rounds 1–3 spent three commits and produced no production change**, on two
   `SHIP` verdicts.
4. **The one missing parameter that cost two HIGHs and two rounds was visible in
   the adjacent function's signature on `origin/main` before the branch
   existed.**
5. **Both loops terminated identically**: by replacing a point-fix with a
   structure that has a completion criterion (golden equality; exhaustive
   enumeration). Neither terminated by being more careful with the next patch.
6. **The diagnosis that produced brief v7 was on the page at brief v6.** One
   round, one commit, one HIGH were spent re-deriving it.

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under forensics; issue #601 read via `gh`, and #556 / #590 / #602 / #604 referenced from the corpus.
