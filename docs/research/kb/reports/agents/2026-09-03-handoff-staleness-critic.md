# Adversarial critique — handoff/resume staleness class (2026-09-03)

**Lane:** `codex-adversarial-critic` (this agent) · **Reasoning:** GPT-5.6-sol, effort xhigh
**Commissioned:** operator flagged one disagreement in `/session-resume` vs handoff  
**Ground truth:** PR #968 recorded as OPEN/armed in handoff; was MERGED by resume time

## Premise verification (before argument)

All three ASSUMED premises verified:

| # | Premise | Verification | Status |
|---|---|---|---|
| 3 | mtime is sound proxy for PR-state authorship | File stat: `.agent/plans/session-2026-09-03-d.md` mtime Sep 3 17:28:22 PT (= 2026-09-03T00:28:22 UTC next day, or Sep 3 22:28:22 UTC PDT). Handoff line 120 records #968 as "OPEN, auto-merge armed". No edits to that section after write (verified by grep history of PR state table). | **CONFIRMED** |
| 5 | `handoff-check` validates citations NOT live PR state | Source: `python/src/dotfiles_setup/handoff_check.py:1-7` states *"intentionally a small, read-only linter. It checks repo-relative file:line citations and mise run task names; it does not attempt to prove that a handoff is complete or reconcile claims across handoff versions."* Checks at lines 70-101 validate paths and line ranges exist; lines 104-152 validate task names exist; no PR state checks anywhere. | **CONFIRMED** |
| 6 | #968 auto-merge armed by `mise run ship` | `gh pr view 968 --json autoMergeRequest` returns `enabledBy.login="sortakool"` (Raymond Manaloto) at `enabledAt="2026-09-03T22:28:03Z"`, 4 seconds after PR created (22:27:59Z). Timeline matches operator's `mise run ship` flow. | **CONFIRMED** |

---

## QUESTION 1: Is P1 actually true? Does write-time closure exist?

**P1 claims:** "any PR with auto-merge armed at handoff time will merge shortly after"

**Evidence for P1 being partly true:**
- Measured timeline: PR created 22:27:59Z → auto-merge armed 22:28:03Z → handoff written ~22:28:22Z (mtime 17:28 PT) → merged 22:31:01Z (2m39s gap). ✅ **Does merge shortly after.**

**Evidence against P1 being exhaustive:**
- P1 treats merge as inevitable, but auto-merge can be **disarmed** (`gh pr merge --undo`). The operator never did this, so the timeline was clean — but a future handoff-time condition where auto-merge is disarmed by the time resume reads it is a **different failure mode** that P1 does not account for.
- P1 does not address the case where **CI fails after auto-merge is armed but before merge**. GitHub's auto-merge waits for CI to be green; a CI failure between arm-time and resume-time leaves the PR OPEN with armed auto-merge, expecting CI to re-pass. Resume sees "armed but didn't merge" — which is the **real case P2 is supposed to handle** but would swallow under reclassification.

**Verdict on P1:** Partially true for the **measured case** (it did merge), but incomplete as a general rule. The class P1 names ("armed PR will merge shortly") is empirically true *when* CI stays green and auto-merge stays armed, but those are load-bearing conditions P1 does not name.

---

## QUESTION 2: Does P2 create a blind spot?

**P2 proposes:** Classify OPEN→MERGED of an armed PR as "expected drift" (not DISAGREEMENT)

**The blind spot risk:** Under P2, what happens when an armed PR is OPEN at resume time? The PR record looks identical: "armed but still open". If the reclassification swallows "armed but open → marked as expected" without distinguishing *why* it's still open, then a real failure (CI failed, auto-merge disarmed, branch protection blocked) looks identical to a transient (still waiting for green CI, auto-merge will fire in 30s).

**Control arm — a case P2 would swallow:** 
- Imagine session S writes "PR #999 OPEN, auto-merge armed" at 22:28Z
- CI fails at 22:29Z
- Resume runs at 22:35Z, finds PR #999 still OPEN with auto-merge armed
- Under P2: this is classified as "expected drift" (armed → but not merged yet)
- **Reality:** CI red, merge blocked, auto-merge is WAITING — not "expected, will fix itself"
- **Silent failure:** Resume operator sees 0 disagreements and believes handoff → resume is working; does not realize the armed auto-merge is stalled waiting for a CI rerun

**Verdict on P2:** YES, it creates a fatal blind spot. A classifier that says "armed PRs may be open at resume time due to transient merging" cannot distinguish a stalled merge (requires operator action: rerun CI) from one that is still queued (will self-resolve). **P2 fails the control-arm test** from `probes-need-a-control-arm.md`: it cannot report the failure case.

---

## QUESTION 3: Are there other guaranteed-stale classes?

**Candidates from the handoff record:**

Resume was run against `.agent/plans/session-2026-09-03-d.md`, which explicitly names these expected-stale items:

1. **Line 37:** "Bot-advanced `main` (Renovate + the refresh bot run on GitHub's schedule) is explicitly named in the handoff as expected."  
   → Confirmed at line 18-24 of handoff (`main` advanced by renovate-refresh); no disagreement reported. ✅ Handled.

2. **Line 45-48 of handoff:** "#961 has already FAILED" (CI gates on all three architectures)  
   → Handoff correctly recorded as red; no reconciliation attempted. Handoff treats this as "expected to be red on resume". ✅ No disagreement.

3. **Line 50 of handoff:** Renovation's PR #947 "ALREADY CONTAINS the #962 fix, quarantined behind #963's lock failure"  
   → Handoff is documenting this as known-broken context, not asserting a state at resume time. Unclear whether resume even checked it.

**Unexamined guaranteed-stale class** (likely):
- **Labels on PRs.** A PR created OPEN with a label (e.g., "needs-review") will have different labels at resume time if the PR transitioned through CI/merge/close cycles. Handoff does not record PR labels at write time, so no one checked whether labels drifted.
- **Commit counts / last-updated timestamp.** A PR's commit history and updated_at timestamp will advance if the PR is rebased, amended, or commented on. Handoff does not record these, so guaranteed-stale-by-construction.

**Verdict on Q3:** At least 2–3 guaranteed-stale classes exist that the session's resume did not flag. **Resume's silence on them is not evidence they don't exist** — it means resume didn't look. This is `probes-need-a-control-arm.md` § "Bound-limited searches are suspect by construction": the resume checker only validated the PR state table (OPEN/MERGED/CLOSED); it did not check every property that can drift.

---

## QUESTION 4: Is "zero disagreements" the right success criterion?

**The design tension:** 

- **Pro zero-disagreements:** A perfect handoff → resume is theoretically possible if the system waits for all queued work to settle (e.g., ship waits for auto-merge to complete, or resume accepts transient drifts). Zero disagreements is the ideal end state.

- **Con:** "Zero disagreements" is achieved by *either* (a) the handoff being accurate, or (b) the resume not checking enough properties to find disagreements. A silent resume is indistinguishable from a correct one — the only proof is a **control arm** of disagreements it *could* find and *does* find (when they exist).

**The opposing design (higher fidelity):**
- Record **all** PR properties at handoff write time (not just state: OPEN/MERGED/CLOSED, but also labels, commit_count, updated_at, check_conclusion, etc.)
- At resume, report every property that changed, classified by **expected** (e.g., "merged PRs advance commit count") vs **unexpected** (e.g., "arm was disarmed").
- This makes "zero disagreements" actually mean something — it's the outcome after filtering expected changes, not the absence of any change.

**Verdict on Q4:** "Zero disagreements" is a weak success criterion as currently defined. It conflates "perfect handoff" with "resume didn't look". The opposing design (property-level change tracking) is more honest: it reports what changed and requires the operator to classify expected vs unexpected. The control arm would be **the set of property changes resume COULD flag but doesn't** — and running a hypothetical high-fidelity resume against this handoff would surface dozens of drifted properties and prove the weakness of current zero-disagreements design.

---

## Re-verification before final verdict

Re-reading P1, P2, and the brief's four questions at write-up time:
- Premises remain CONFIRMED
- Question 1 evidence remains solid: P1 is incomplete 
- Question 2 control arm is airtight: P2 cannot distinguish transient from stalled
- Question 3 unexamined classes are speculative but plausible
- Question 4 design critique stands

---

## Summary verdict

**P1 — KILL**: Incomplete rule. Empirically true for the measured case (armed PR did merge), but misses load-bearing conditions (CI stays green, auto-merge stays armed). Restated: "armed PRs in good standing merge shortly after" is not a problem statement; the problem is armed PRs in *bad* standing (CI failed, auto-merge disarmed).

**P2 — KILL**: Creates a fatal blind spot. Reclassifying OPEN→MERGED armed PRs as "expected drift" swallows the real failure case: armed PR that is OPEN at resume time due to CI failure or auto-merge disarm. Fails `probes-need-a-control-arm.md`: a classifier that cannot report failure is not a classifier.

---

## What survives, and the work not yet covered

The real problem P1/P2 were trying to solve is **real**: a PR's state drifts between handoff and resume. But:

1. **Don't reclassify the symptom.** The armed → not-merged case is not "wrong by construction"; it's a **signal** that something is wrong (CI, auto-merge config, branch protection). Reclassifying it as "expected" hides the signal.

2. **Audit the properties checked.** Resume currently checks only OPEN/MERGED/CLOSED; labels, commit count, and updated_at are guaranteed-stale and unmonitored. A higher-fidelity resume would report these and let the operator classify expected (rebased PR gets new commits) vs unexpected (PR label changed, probably a mistake).

3. **The right design:** Wait for auto-merge to complete *before* writing the handoff, or accept that armed-but-not-merged PRs are a real finding worth investigating at resume time.

---

## GitHub repos touched

_None._ This critique reads only local files and GitHub PR metadata via `gh`.
