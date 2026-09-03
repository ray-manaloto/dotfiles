# Brief — adversarial critique of the handoff/resume "zero disagreements" claim

**Lane:** `codex-adversarial-critic` · **Dispatched:** 2026-09-03 (session `dotfiles-20260903.003`)
**Commissioned by the operator:** *"have a codex lane review the previous session — we shouldn't
have disagreements anymore so the work we did to ensure a clean handoff still has issues"*

## The observation that prompted this

`/session-resume` this session reported exactly one DISAGREEMENT against
`.agent/plans/session-2026-09-03-d.md`: the handoff listed **PR #968 as "OPEN, auto-merge
armed"**; it was in fact **MERGED** (squash `e152e29`).

**Measured chronology (all UTC, this session, `gh pr view 968 --json createdAt,mergedAt`):**

| event | timestamp |
|---|---|
| #968 created | `2026-09-03T22:27:59Z` |
| handoff file written (mtime) | `2026-09-03T22:28:22Z` |
| #968 merged by armed auto-merge | `2026-09-03T22:31:01Z` |

So the handoff was **CORRECT at write time** and went stale **2m39s later**, by the
deliberate action of the auto-merge it had itself armed.

## The proposal to attack

> **P1.** This disagreement class is *wrong-by-construction*, not a care failure: any PR with
> auto-merge armed at handoff time will merge shortly after the handoff is written, so a
> handoff that records it as OPEN is guaranteed to be stale on resume. No amount of diligence
> at write time closes it.
>
> **P2.** Therefore `/session-handoff` should record such PRs with their *expected* terminal
> state (e.g. "OPEN, auto-merge armed → EXPECT MERGED by resume"), and `/session-resume`
> should classify the OPEN→MERGED transition of an armed PR as **expected drift**, not as a
> DISAGREEMENT.

## The question you must settle

**Would P2, if it had been in place yesterday, have caught its own motivating defect — and
does it introduce a worse one?** Specifically:

1. Is P1 actually true, or is there a write-time action (e.g. handoff waits on the arm, or
   records the merge queue state) that closes the gap without the reclassification?
2. Does P2 create a **blind spot**? An armed PR that is *not* merged by resume time — because
   CI went red, because branch protection blocked it, because auto-merge was disarmed — is a
   REAL disagreement. Under P2 does it still surface, or does "expected drift" swallow it?
   This is the `probes-need-a-control-arm.md` failure shape: a classifier that can only
   report "fine".
3. Are there **other** guaranteed-stale classes in the handoff that this session's resume did
   NOT flag, only because it happened not to look? Bot-advanced `main` (Renovate + the refresh
   bot run on GitHub's schedule) is explicitly named in the handoff as expected. What else?
4. Is "zero disagreements" the right success criterion at all, or does it push toward a resume
   that under-reports? Argue the opposing design if you believe it.

## Ground truth you may rely on (verify anything you use)

- The handoff under review: `.agent/plans/session-2026-09-03-d.md`
- The two skills: `.claude/skills/session-handoff/SKILL.md`, `.claude/skills/session-resume/SKILL.md`
- The checker: `mise run handoff-check` (returned **rc=0** on this handoff — every citation
  resolved, and it still did not catch the #968 staleness; that gap is itself evidence)
- The state snapshot: `mise run session-state`
- Relevant rules: `.claude/rules/probes-need-a-control-arm.md`,
  `.claude/rules/verify-before-advancing.md`
- Memory: `feedback_amend_after_ship_races_automerge` (the sibling auto-merge race)

## PREMISES

| # | Premise | Status |
|---|---|---|
| 1 | #968 merged at `2026-09-03T22:31:01Z` via armed auto-merge | CONFIRMED — `gh pr view 968` this session |
| 2 | The handoff file was last written at `2026-09-03T22:28:22Z` | CONFIRMED — `stat` mtime, this session |
| 3 | mtime is a sound proxy for "when the handoff's PR-state section was authored" | **ASSUMED** — verify; the file may have been edited after the section was written |
| 4 | `handoff-check` returned rc=0 on this handoff | CONFIRMED — run this session |
| 5 | `handoff-check` validates citations (paths, line ranges, task names), not live PR state | ASSUMED from the skill text — verify against the implementation |
| 6 | #968's auto-merge was armed by `mise run ship`, not by hand | ASSUMED — verify |

## Output contract

- Write your report **incrementally** to
  `docs/research/kb/reports/agents/2026-09-03-handoff-staleness-critic.md` — start the file
  early and update it as you go, do NOT hold it in memory until the end.
- Overturn P1 and/or P2 **by name** if the evidence overturns them. A verdict of
  "the proposal is sound" is acceptable only with the control arm that would have shown it unsound.
- Every claim carries a `file:line` anchor or the command that produced it.
- End with `## GitHub repos touched`.
- **SendMessage your summary LAST**, before going idle — a final text that is never sent is lost.
