# Brief — ticket-cut-advisor (#916 ticket cut), 2026-09-02d

Persisted per `.claude/rules/agent-report-persistence.md` rule 5 (a
findings-bearing lane maps BOTH brief and report). Report:
`2026-09-02-ticket-cut-advisor.md`.

**Lane:** `fable-orchestrator:fable-advisor` — the Claude-backed original.
`.claude/CLAUDE.md` substitutes `codex-advisor` while Claude tokens are
constrained; the operator named "@fable-adviser" a second time after being told
of the substitution, which was read as reaffirmation. The override was stated to
them, not made silently.

## The question put to it

How to cut the approved spec (**issue #916**) into tickets under a hard
parallelism + context-budget constraint.

## The operator constraints that drove it (verbatim)

> "we want to be able to quickly iterate on each one with parallel codex lanes
> that dont interfere w each other and the main context stays roughly at the 20%
> mark of context and the claude agents and the codex lanes and the codex agents
> in those codex lanes stay around 20% of each model's limit — note: gpt-5.6-sol
> model really only has about 200K context"

Decomposed for the lane: (1) concurrent tickets must be **file-disjoint**, and
blocking edges do NOT deliver that — two tickets sharing a blocker run
concurrently and can collide (`feedback_lane_done_does_not_release_the_checkout`:
a second writer on a live checkout made a file revert 4x); (2) each lane fits
**~40K tokens** covering ticket text + files read + diff written; (3) the
orchestrator and Claude subagents each stay ~20% of their own limits.

## What was demanded back

1. A concrete re-cut, each ticket with blocking edges **and the file/directory
   territory it owns exclusively** — ownership being the thing that makes lanes safe.
2. A verdict on the ~78-module one-commit migration: executable by one lane at
   40K, or a constraint conflict the operator must see?
3. Sizing — which tickets cannot fit, and how to split them.
4. The frontier shape: how many lanes can genuinely run at once per stage. "If
   the answer is *mostly one*, the parallelism the operator wants is not
   available from this spec and I need to tell them."
5. Any failure mode in my cut I had not named.

I supplied my own 14-ticket cut and **named the defect I suspected** (3/4/5 and
9/10 colliding), asking it to confirm or refute.

## Outcome

Collision CONFIRMED and wider than I named. It also refuted the "~78 modules"
figure I had published in #916 (measured ~30), and dissolved a constraint
conflict I had already escalated to the operator — the repo squash-merges, so N
file-disjoint lanes still yield one commit. **Both corrections were
independently re-verified by me before I acted on them**, including the
squash-merge claim, because I had told the operator the opposite minutes earlier.

⭐ Reusable brief moves: naming my own suspected defect and asking for
confirm-or-refute; demanding the frontier number with an explicit invitation to
answer "mostly one"; and the standing "say plainly if a premise of mine is wrong
— that is more valuable than agreement", which produced the highest-value half of
both advisor returns this session.
