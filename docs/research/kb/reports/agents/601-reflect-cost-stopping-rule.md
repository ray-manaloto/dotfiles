# #601 — when should a review loop STOP?

**Agent:** cost-analyst · **Date:** 2026-08-06 · Corpus:
`docs/research/kb/reports/agents/601-codex-review-rounds.md` (7 reports + 7
briefs, verbatim) and `git log d070cb5..HEAD`.

Every number below states how it was obtained. Nothing is inherited.

---

## 0. Two premises in my brief are wrong. Correcting them first, because the
## whole cost calculation hangs off them.

### 0.1 It was not a "~40-line correctness fix"

Re-derived (`git diff --stat d070cb5..HEAD`):

| Surface | Lines |
|---|---|
| `python/src/dotfiles_setup/dag_tick.py` (**production**) | **+416 / −35** |
| `tests/test_dag_tick.py` | +1049 net |
| `python/verification/suites.toml` | 4 |
| `tests/AGENTS.md`, `tests/TEST-INDEX.md` | 3 |
| **Total** | **1465 / 42** |

The **first** commit alone (`e9da8cb`) was 164 production lines + 318 test
lines. There was never a 40-line version to over-review.

**Why this matters:** a 7-round loop on 40 lines is malpractice. A 7-round loop
on a 451-line rewrite of the decision core of an unattended watchdog is a
defensible-but-unmanaged process. Calibrating a stopping rule against the wrong
denominator would produce a rule that stops far too early.

### 0.2 Stopping at round 3 would have shipped **2** HIGH defects, not 3

Probed directly at `b9214ad` (the tree v3 pronounced SHIP), with control arms:

| Defect | Present at `b9214ad`? | Probe |
|---|---|---|
| Queued-reply deadlock (v5 HIGH#1) | **YES** | `is_needs_human(state, needs)` — no `queued_prompt` parameter. **Control arm:** the same grep at HEAD returns `is_needs_human(state, needs, *, queued_prompt: bool)`, so the probe discriminates. |
| classify→execute race (v4 HIGH) | **YES** | `load_state_json\|node_from_state` occurs **2×** at `b9214ad` vs **6×** at `8c87eec` (v4's fix). The execution-time re-read did not exist. |
| Live-PID queued reply (v6 HIGH) | **NO** | `git blame` attributes the defective line (`dag_tick.py:419` at `09d2cb9`) to **`09d2cb9` itself** — the fix for v5. It could not have shipped at `b9214ad` because it did not exist yet. |

So the honest indictment of a "stop when severity drops" rule is that it ships
**two** genuine HIGH defects. The third was manufactured by the loop.

---

## 1. What each round COST and what it BOUGHT

### 1.1 Wall clock — bounded, not point-estimated

From `git log --format='%h|%aI|%s'` (author dates, `-05:00`):

| # | SHA | Time | Δ prev | Prod Δ | Reviewed by |
|---|---|---|---|---|---|
| 1 | `e9da8cb` | 01:47:35 | — | 164 | (v1 reviewed the tree at #2) |
| 2 | `42e7c9c` | 01:58:05 | 10m30s | 66 | **v1** |
| 3 | `cf6e97d` | 02:14:34 | 16m29s | 39 | **v2** |
| 4 | `b9214ad` | 02:26:48 | 12m14s | 17 | **v3** |
| 5 | `397675b` | 02:39:36 | 12m48s | **0 (test-only)** | **v4** |
| 6 | `8c87eec` | 02:59:28 | 19m52s | 66 | **v5** |
| 7 | `09d2cb9` | 10:13:11 | **7h13m43s** | 86 | **v6** |
| 8 | `796777a` | 12:55:10 | 2h41m59s | 107 | — |
| 9 | `eda53d6` | 13:04:26 | 9m16s | 0 (test-only) | **v7** |

**Span:** 11h 16m 51s. ⚠️ **The span is not the work.** The 7h13m and 2h42m gaps
almost certainly contain sleep and unrelated work. **Contiguous working time is
bounded below by the sum of the seven sub-20-minute gaps: 1h 21m 09s.** Anything
between ~1.4h and 11.3h is consistent with the artifacts. I report the interval,
not a figure.

**What I cannot measure at all:** token spend per round, codex latency, human
reading time, brief-authoring time, whether other work interleaved. Any
cost-per-round claim beyond commit cadence would be invented.

### 1.2 The value ledger

| Round | Findings | What it actually bought | Class |
|---|---|---|---|
| v1 | 2 HIGH · 1 LOW | Honest log wording; the missing-projection gap → **#602**. **No production behaviour changed.** | claims/scope |
| v2 | 2 LOW | Doc accuracy; a stored test counterexample | prose/test |
| v3 | 1 LOW | Golden-equality test hardening | test |
| v4 | 1 HIGH | **Real pre-existing race** (classify→execute) | production |
| v5 | 3 HIGH · 1 LOW | 1 real pre-existing (queued deadlock) · 1 **residual of v4's own fix** · 1 out-of-scope → **#604** | mixed |
| v6 | 1 HIGH · 1 LOW | **Self-inflicted by v5's fix** (blame-confirmed) | self-inflicted |
| v7 | 2 MEDIUM | Missing 5th axis (`tempo`); meta-tests don't hold the table honest. **Unresolved on the branch.** | coverage |

**Yield accounting for the five HIGH findings in rounds 4–6:**

- **2 genuine pre-existing in-scope defects** (v4 race, v5 queued deadlock)
- **1 genuine pre-existing out-of-scope defect** → #604 (real value, wrong ticket)
- **1 residual** — v4's fix narrowed but did not close its own finding
- **1 self-inflicted** — v6's HIGH was authored by v5's fix

**40% of the HIGH yield of rounds 4–6 was the loop cleaning up after itself.**
The loop was not waste, but it was not 5-defects-worth of value either.

---

## 2. Does severity-trend work as a signal? **No — and not for the reason it looks.**

The obvious reading is "severity is noisy, LOW→LOW→HIGH happens." That reading
is too kind. Severity trend failed here for a structural reason:

> **Severity measures the ROUND, not the ARTIFACT.** Rounds 2 and 3 scored LOW
> because they were reviewing 39- and 17-line wording deltas that the *previous
> round's own findings* had directed them at. The two HIGH defects were sitting
> untouched in the original 164-line commit the entire time.

Look at the Prod Δ column: v2 reviewed a 39-line delta, v3 a 17-line delta, v4 a
**zero-line** (test-only) delta. A reviewer given "find what is broken" against a
tiny prose delta will report prose findings. The severity dropped because the
**question** got smaller, not because the **program** got safer.

This generalises into a disqualifying property:

> **Any stopping rule that reads the severity of the last N rounds is reading a
> function of the briefs, not of the code.** The implementer authored those
> briefs. The rule is therefore gameable by the party it is meant to constrain —
> unintentionally here, but gameable all the same.

**What does work is coverage, not quiescence.** Round 7 is the proof. Its brief
asked three closed questions about an *enumeration* rather than "what is
broken", and it found a genuine gap (the `tempo` axis) **in one pass** — after
six rounds of open hunting had walked cell-by-cell through the same state space.

The v7 brief diagnosed this itself, verbatim:

> *"Every HIGH was **the same shape**: a reachable combination of
> `state × needs × queuedPrompt × pid_alive` that nobody had enumerated. Round 5
> found `blocked+needs+queued+dead`. Round 6 found the same with `alive`. Each
> fix made a new cell reachable, and the next round walked into it."*

`blocked+needs+queued+dead` and `blocked+needs+queued+alive` are **two rows of a
32-row table**. Enumerating the table finds both at once. Hunting finds them one
per round, with a regression between.

---

## 3. The stopping rule: **ENUMERATE-THEN-CLOSE**

Decidable from artifacts a script reads. No judgement calls.

### Phase gates

```
PHASE 1 — OPEN HUNTING.  Hard cap: 2 rounds.
   Brief asks "what is broken". Findings are expected.
   Phase-1 briefs MUST additionally ask the two questions that
   open hunting reliably misses (see 3.3).

GATE G — ENUMERATION GATE.  Machine-checkable. Blocks phase 2.
   The change must ship an explicit enumeration artifact:
     (a) a parametrized table over the NAMED decision axes of the
         code under review;
     (b) row count == product of declared axis cardinalities;
     (c) a meta-test asserting (b);
     (d) a meta-test asserting every reachable output class appears.
   Not satisfied -> the next unit of work is BUILDING THE TABLE,
   not another review round.

PHASE 2 — BOUNDED CLOSE-OUT.  Hard cap: 2 rounds.
   Brief asks exactly three closed questions:
     Q1 is any expected cell WRONG?
     Q2 are the axes COMPLETE — is there a fifth?
     Q3 do the meta-tests actually hold the table honest?
   Brief carries an EXPLICIT stop condition and an explicit
   "do not manufacture a finding" instruction.

TERMINATE when:  Q1=no cell wrong AND Q2=axes complete AND Q3=holds
                 -> SHIP, zero findings.
            OR:  phase-2 round cap reached -> SHIP, remaining
                 findings become TICKETS, not commits on this branch.
```

### 3.1 Every predicate is script-computable

| Predicate | Computed from |
|---|---|
| round count per phase | count of review artifacts |
| Gate G (a)–(d) | AST of the test file: a table literal, `len(TABLE) == len(A)*len(B)*…` assertion, a class-coverage assertion |
| phase-2 brief is bounded | brief contains an explicit stop condition section (grep) |
| Q1/Q2/Q3 answers | the reviewer's mandated output format is three labelled verdicts |
| "findings become tickets" | `gh issue create`, not a commit |

### 3.2 Replayed against the actual 7-round record

| Rule round | Maps to | Outcome |
|---|---|---|
| P1-R1 | v1 | 2 HIGH · 1 LOW → wording fixed, #602 filed |
| P1-R2 | v2 | 2 LOW → fixed |
| **GATE G** | — | **FAILS** — no truth table exists. Next work = build `_CLASSIFY_TABLE`. |
| — | (`eda53d6`, pulled forward) | The 32-row table over `state × needs × queuedPrompt × pid_alive` |
| P2-R1 | v7's brief, run here | **Finds the `tempo` axis + weak meta-tests** (v7's actual result, one pass) |
| P2-R2 | — | Table extended with `tempo`; re-asked; converges or the remainder becomes tickets |

**4 rounds instead of 7.**

**Does it find the same defects?** The two self-inflicted-cycle defects, yes,
mechanically — `blocked+needs+queued+{dead,alive}` are literally two rows of the
table Gate G forces. And they are found **without the intervening regression**,
because the table is derived from the axes rather than from the last fix.

### 3.3 Where the enumeration gate is BLIND — stated plainly

**v4's HIGH (the classify→execute race) is NOT a cell in any state table.** It
is a *temporal* defect: a decision computed at T1 is executed at T2 without
re-reading its inputs. No cross-product of state fields contains it. Gate G
would have missed it entirely.

That class needs its own phase-1 question, and it is a question, not a table:

> **Q-FRESH (mandatory in every phase-1 brief):** *For every
> decision→action pair, is the decision re-validated against freshly-read
> inputs immediately before the action? Name every pair where it is not.*

The same brief must carry:

> **Q-SCOPE:** *Which findings belong to a different ticket? Name them and
> stop.* (v5 HIGH#3 → #604 took a full round of attention to be scoped out.)

Both are one line each and cost nothing. Neither was in briefs v1–v6.

---

## 4. The non-convergence detector: **REGRESSION-ECHO**

> **Fire when a HIGH or MEDIUM finding cites at least one PRODUCTION line
> authored by the immediately-preceding fix commit.**
>
> `git blame -L <n>,<n> <reviewed-tree> -- <cited-prod-file>` → does the SHA
> equal the previous round's fix?

Cheap, exact, needs only the review report's `file:line` citations and git.

### Measured across every round with a HIGH/MEDIUM finding

| Round | Prev fix | Prod cites blaming to it | Fires? | Ground truth |
|---|---|---|---|---|
| v4 | `397675b` (test-only) | **0/3** | no | Pre-existing race — correct not to fire |
| v5 | `8c87eec` | **2/9** (`:687`, `:951`) | **YES** | HIGH#2 is explicitly "narrowed, not closed" — v4's fix |
| v6 | `09d2cb9` | **2/6** (`:419`, `:998`) | **YES** | HIGH cites `09d2cb9` by name as the cause |
| v7 | `796777a` | **0/2** | no | Found an original-design axis gap — correct not to fire |

**Both arms fire. The probe discriminates.** It returns YES exactly on v5 and
v6 — the two rounds the v7 brief independently identified as non-convergent —
and NO on v4 and v7, the two rounds that found genuine pre-existing problems.

**The production/test distinction is load-bearing, and I got it wrong on the
first pass.** A naive "blames to prev commit" count over *all* files ranks **v7
highest (3/3)** — and v7 is the round that converged. Its citations are all
*test* lines the previous commit added, which is what reviewing a new test
artifact looks like. Restricting to production lines is what makes the detector
work.

**Escalation:** REGRESSION-ECHO firing **twice consecutively** (v5 then v6) is
the stop signal. It means the loop is chasing its own tail, and the correct
response is not another round — it is **Gate G**: stop fixing cells, enumerate
the space.

**Honest limits.** Four rounds is a small sample; two fires and two non-fires is
suggestive, not established. `git blame` attributes the *last touch*, so a
cosmetic reformat by the previous fix would false-positive; pairing it with
severity ≥ MEDIUM suppresses most of that. It cannot see a defect the previous
fix *enabled* without touching the defective line.

---

## 5. The asymmetry that should change the DEFAULT

Verified, not assumed — `python/src/dotfiles_setup/dag_tick.py:1` and
`docs/receipts/578.md:5`:

- a `dev.mise.dotfiles-dag-tick` LaunchAgent fires `mise run dag-tick` with
  **`start_interval = 60`**;
- each tick issues **`claude respawn`** and **`claude stop`** against live
  workers;
- **no human is present**, and healthy ticks print nothing.

So this change is *unattended* × *irreversible action* × *silent*. A defect here
destroys work at 1440 opportunities per day with nobody watching. That is the
opposite end of the spectrum from a doc typo, and the review budget should say
so **by construction rather than by the reviewer's mood**.

### Machine-readable blast-radius tiers

| Tier | Predicate (script-computable) | Phase 1 | Gate G | Phase 2 |
|---|---|---|---|---|
| **T3 unattended-destructive** | diff touches a module reachable from a scheduled entrypoint (launchd/cron/CI cron) **AND** the diff touches a function that spawns/stops/deletes | 2 rounds, min 1 | **MANDATORY** | 1–2 rounds |
| **T2 unattended-benign** | scheduled-reachable, read-only actions | 1 round | mandatory if the change adds a decision axis | 1 round |
| **T1 interactive code** | not scheduled-reachable | 1 round | optional | 0 |
| **T0 prose/docs** | diff touches only `*.md` | 0 rounds | n/a | 0 |

`dag_tick.py` is **T3** on both clauses. Under this table #601 gets the full
4-round treatment automatically — nobody has to argue for it, and nobody has to
argue it down at round 3 either.

**The default this replaces:** "review until the reviewer says SHIP." That
default produced a SHIP verdict at round 2 on code carrying two HIGH defects.

---

## 6. False-negative cost — what this rule ships that it should not

Stated honestly, because a stopping rule that never ships anything wrong does
not stop.

1. **Anything outside the declared axes.** Gate G checks that the table is
   *complete with respect to the axes the author declared*, not that the axes
   are right. Q2 asks a reviewer to find a missing axis — and on this corpus
   that worked (v7 found `tempo`) — but it is one reviewer's judgement inside an
   otherwise mechanical rule. **This is the rule's single biggest hole.**
2. **Temporal and concurrency defects**, unless Q-FRESH catches them. Gate G is
   structurally blind here (§3.3). #601's v4 HIGH is a worked example of exactly
   what slips.
3. **Defects introduced by the phase-2 fixes themselves.** Fixing the `tempo`
   gap could open a new cell; with a hard cap of 2 phase-2 rounds, a second
   REGRESSION-ECHO fire ships rather than loops. That is deliberate — the
   alternative is #601's 7 rounds — but it is a real exposure.
4. **Everything at T0/T1.** A one-round budget on interactive code will miss
   things a three-round budget would find. That is the trade being bought.
5. **Cross-module interactions.** The rule reasons about the module under
   review. v5's `execute_stop` finding (→#604) was only found because a reviewer
   wandered out of scope; Q-SCOPE would file it, but nothing *guarantees* it is
   noticed.

**What it does not ship:** the two HIGH defects that a severity-trend rule ships
at round 3, because Gate G forces the enumeration that contains both.

---

## 7. Answers to the five sub-questions, compactly

1. **What would a correct rule have done?** ENUMERATE-THEN-CLOSE stops at **4
   rounds** (2 hunt + gate + 1–2 bounded). It does not stop at 3 — Gate G blocks
   the exit until the truth table exists, and the table contains both defects a
   round-3 stop would ship.
2. **Does severity-trend work?** No. It measures the brief, not the program, and
   the implementer writes the briefs. Use **coverage** (Gate G) plus
   **REGRESSION-ECHO**.
3. **Cost vs. buy?** 9 commits, ≥1h21m contiguous / ≤11h17m span, 1465 lines. It
   bought 2 genuine in-scope HIGH fixes + 1 out-of-scope ticket (#604) + 1
   deferred gap (#602); **40% of the rounds-4–6 HIGH yield was self-cleanup**.
   Tokens and reviewer latency are unmeasurable from the artifacts.
4. **Asymmetry?** Yes — §5. Scheduled-reachable × destructive-action is
   computable from the diff and should set the budget before anyone reviews.
5. **Cheapest non-convergence detector?** REGRESSION-ECHO (§4): `git blame` the
   production lines a HIGH/MEDIUM finding cites against the previous fix's SHA.
   Two consecutive fires ⇒ stop hunting, enumerate.

---

## 8. The one-line version

> **A review loop terminates on COVERAGE, not on quiescence.** Stop when the
> input space is enumerated and the enumeration is checked — not when the
> reviewer runs out of things to say. And when a round's findings blame to the
> previous round's fix twice running, stop reviewing and start enumerating.

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo
  under analysis: `git log`/`blame`/`show` over `d070cb5..HEAD`, the #601 review
  corpus, receipts 565/573/575/578, and issue refs #590/#602/#604.
