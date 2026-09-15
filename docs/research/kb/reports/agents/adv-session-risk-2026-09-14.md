# Structural risk review — session 2026-09-14e at commitment boundary

**Role:** codex-astra-advisor (structural risk, probes with control arms)  
**Scope:** what the session record loses or misleads about, before `/clear`  
**Status:** COMPLETE

---

## VERDICT: Ship the record; fix THREE claims before the next session starts

The session's HANDOFF is **substantially correct and honest**, but three internal misstatements will mislead the next session into false confidence about specific repairs. All three sit in tracked files that can be corrected before `/clear`. The `/goal` replacement text is sound and should be pasted.

**CRITICAL UNRECORDED RISK:** Cold review found a NEW regression (R4, MED severity) in the shipped fix `adbc5ac` that permanently blocks a failed codex lane's retry. The next session will encounter this if any codex lane fails mid-run. The risk is NOT recorded in the lane definitions themselves.

---

## Highest-risk misalignment: The single thing a fresh session could get catastrophically wrong

**If a codex lane fails mid-run before shipping its result (common in xhigh reasoning), the same `CODEX_LANE_ID` is refused forever.** Cold review found this at R4 (cold-1113-r2-2026-09-14.md:21-34):

```
A lane that dies before codex writes leaves a zero-byte $OUT behind — and the 
claim is the only thing that refuses. [R4 ARM 1 shows the 0-byte file; ARM 2 shows 
permanent refusal]
```

**Why this matters:** The session shipped `adbc5ac` which FIXES F1 (concurrent race) via `( set -C; : > "$OUT" )` — that atomicity is PROVEN and real. But it introduces R4: **the 0-byte `$OUT` is PERMANENT**, not recoverable. Cold review's control arm (the pre-fix guard) allowed retry; the fix does not.

**The commit message for `adbc5ac` does NOT mention this.** It says "the 0-byte file is a load-bearing new risk [that is] clean" (cold-1113-r2:line 26). That is false on the retry axis — the "clean" claim covers only the `codex exec -o` behavior (R3), not the lane's own recovery path (R4).

**Recorded where?** Only in cold-1113-r2-2026-09-14.md (§ R4, lines 21-34). NOT in:
- `.claude/agents/codex-sol-advisor.md` (the code itself)
- `suites.toml` or `hk.pkl` (no contract guards R4)
- The commit message for `adbc5ac`
- The session handoff (not mentioned)

**Control arm, proof R4 is real:** The pre-fix `test ! -e "$OUT"` guard allowed `retry under the same CODEX_LANE_ID` to succeed (rc=0 on the retry in cold-1113-r2:line 32 ARM 2). The post-fix `set -C` prevents that retry. Both measured in live shells.

**Mitigation for next session:** If a lane fails mid-run, do NOT retry under the same `CODEX_LANE_ID`. Rotate to a fresh id (the default `$$-$(date +%s)` form, line 90 of the lane comments, already does this). Or delete the 0-byte `$OUT` before retry.

---

## Three misstatements in tracked files — all fixable before `/clear`

### 1. Commit `571560e` message claims the guard works concurrently (FALSE)

**Location:** git log of commit `571560e`, or GitHub #1113 body  
**Claim:** "A `test ! -e "$OUT"` guard at claim time refuses concurrent peers"  
**Reality:** Cold review F1 (cold-1112-2026-09-14.md:29-40) measured concurrency directly:
```
lane A wrote prompt-A
lane B wrote prompt-B [same LANE_ID]
--- files produced --- p-X.md v-X.md
[one prompt file; lane B shipped lane A's payload]
```
**The guard DOES fire in sequential case (confirmed), but NOT in concurrent (both lanes find `$OUT` absent, both write).**

**Evidence from control arm:** Sequential re-run with same id -> refuses at rc=1 ✓. But the concurrent case shows no refusal. The commit message generalises sequential behavior to the concurrent window.

**Who should fix:** A single-line correction to the commit message is not possible (it is merged); annotate in a follow-up issue or next session's note.

### 2. Commit `adbc5ac` message claims traversal escape (MEASURED FALSE and retracted)

**Location:** git log of commit `adbc5ac`, or GitHub #1113 body  
**Claim:** (in the F3 bullet) "traversal escape via `CODEX_LANE_ID=../../../tmp/x`"  
**Reality:** Cold review F2 correction (cold-1112-2026-09-14.md:36-38 + cold-1113-r2 R5) measured:
```
CODEX_LANE_ID=../../../tmp/x
→ writes inside .agent/kb/raw/ (the prompt file)
→ the ../ path component tries to escape but the write fails (no parent created)
→ control: benign1 writes inside — so the write is failing on the directory traversal, not succeeding
```
**Traversal does NOT escape; it fails. The empty-prompt risk (F2's ACTUAL issue) is from the `/` character, not traversal.**

The handoff acknowledges this at line 119-125: "its recorded RATIONALE (traversal) is wrong — corrected in #1114's comment." So #1114 exists as a follow-up.

**Who should fix:** #1114 (follow-up issue) should clarify the real mechanism (invalid path prefix from `/`, not traversal). Verify before closing.

### 3. Handoff summary of goal defects CONTRADICTS goal-review report structure

**Location:** Session handoff lines 326-342 (four defects named) vs adv-goal-review-2026-09-14.md  
**Claim:** "Four defects found in the `/goal`, each by a probe"  
**Reality:** Goal-review PASS 1 found THREE CONFLICTS (Q2, lines 34-38 of goal-review):
```
1. Clause 4 contradicts clauses 3 & 5 (stop for operator vs land PRs)
2. Clause 2/3 conflict (dryrun evidence only, no actual grouped PR)
3. Clause 5 conflict (PR state requirement vs superseded closed PRs)
```
Goal-review PASS 2 (implied via the replacement text at line 68-70) addressed these conflicts in a narrowed scope. The handoff then lists PROBE findings (bad line ref, missing pin site, unreachable unset arm, incomplete lock spec) that ARE in goal-review.

**The mismatch:** The handoff calls these "four defects found in the `/goal`" (implying fresh discovery), but they are actually **corrections applied to the replacement text** that goal-review generated. The handoff's own statement "Four defects found in the `/goal`, each by a probe" is technically true (they WERE probed), but it elides the fact that goal-review's first pass found conflicts and the second pass validated the probes against the replacement text, not the original.

**Control arm:** Compare handoff lines 326-342 (four defects) to goal-review lines 29-50 (Q1–Q4 answers, which address the same clauses). The probes match; the framing does not. Goal-review also lists the replacement text (lines 68-70) which INCORPORATES the fixes; the handoff lists them as separate findings.

**Who should fix:** A clarifying note in `.agent/plans/session-2026-09-14-e.md` at line 324 (before "Four defects") stating "two-pass goal review: PASS 1 found conflicts (scope narrowed); PASS 2 validated probes against replacement text." The replacement text in adv-goal-review-2026-09-14.md is CORRECT and should be pasted as-is.

---

## What survives the `/clear` correctly

- ✅ **All reports are on disk**, tracked, dated 2026-09-14
- ✅ **The `/goal` replacement text is in adv-goal-review-2026-09-14.md:68-70**, ready to paste
- ✅ **All 30 tracked reports exist** (verified with `find`)
- ✅ **Issue #1114 filed** (follow-up to #1113 on the rationale mismatch)
- ✅ **Memory survives** at `~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/memory/`
- ✅ **Merged PRs are in git history** (#1094, #1109, #1113)

---

## What is load-bearing and NOT recorded

| Risk | Where | Consequence | Next action |
|---|---|---|---|
| **R4: Dead lane → stuck lane** | cold-1113-r2-2026-09-14.md:21-34 only | A codex lane that fails mid-run permanently refuses retry under the same `CODEX_LANE_ID` | If codex lane fails mid-run, rotate `CODEX_LANE_ID` or delete the 0-byte output file before retry. Add to codex lane docs. |
| **F2 mech (rationale)** | cold-1112-2026-09-14.md + #1114 follow-up | Commit message says "traversal" but measured cause is `/` in path prefix | Verify #1114 clarifies; do not re-litigate the fix (it works) |
| **Clause 3/4 fixes in adv-goal-review** | adv-goal-review-2026-09-14.md:73-77 | The narrowed scope and clause edits must be understood as applying TOGETHER | Paste the replacement text verbatim from goal-review:68-70 |

---

## Prioritization check: Is the handoff's lead item correct?

**Handoff leads with:** "THE CLAUDE PIN — a live defect, decision SETTLED, implementation OWED" (line 20)  
**Question:** Is this RANK 1 for the next session?

**Answer:** No, it is a daily-driver problem, not a session blocker.

**Evidence:**
- The operator is running `~/.local/share/mise/installs/github-anthropics-claude-code/2.1.270/claude` (via mise pin)
- Native installer placed `~/.local/bin/claude` @ 2.1.271
- Measured 2.1.271 has no breaking changes (hook feedback, Bash, MCP, subagent tooling)
- **The fix is simple: run native 2.1.271 instead of the pinned 2.1.270** (the operator can do this immediately)

**What the next session should do:** This is a FOLLOW-UP, not RANK 1 blocker. The `/goal` work (hk currency) is ranked first. The claude pin is a separate track: "Review 2.1.271 release notes next session, then decide on mis → native transition." (handoff line 79)

**Rank 1 should be:** Paste the replacement `/goal` text and start the hk currency work. The claude binary can be updated in parallel or deferred to a second session.

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — session records, reports, commit messages, goal artifact, PRs #1113–#1114
- [jdx/hk](https://github.com/jdx/hk) — hk 2.0 validation in goal-review report

