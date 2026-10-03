# Errata + successor log — handoff 2026-10-03g (27e2bf5c → 28f1a8f7)

Successor: `dotfiles-20261003T144132.124570000-05.coordinator` (session 28f1a8f7). `session-2026-10-03g.md` shipped
as PR #1620 before these corrections existed and its branch is closed (auto-merge armed), so corrections live here.
Evidence: `docs/research/kb/reports/agents/handoff-review-27e2bf5c-2026-10-03g.md` (transcript line refs).

## Corrections to session-2026-10-03g.md (and its coordinator log + task_plan delta)

| Handoff says | Correct | Ref |
|---|---|---|
| Ruling (b) ~14:35; Q1–Q5 ~14:50; D1–D4 ~14:55; plan-write verbs ~15:00 | 14:26 (a+b, via watcher 998ab91b); 14:33 (Q answers; "proceed" 14:34); 14:36 (D1–D4 + "write the spec"); 14:38 (verbs) | review item 1 |
| #1606 cold review RUNNING | Returned **SHIP** @0125fc4d: F1–F6 fixed, F7 partial; LOWs R2-1..R2-4; I3: branch touches `suites.toml` ⇒ ship from MAIN checkout; T1 (`.claude/worktrees/` ignored only via `.git/info/exclude`) needs its own ticket | `docs/research/kb/reports/agents/cold-review-1606-0125fc4d.md` |
| Durability-proposals subagent RUNNING; re-run if lost | Delivered; verbatim at `docs/research/kb/reports/agents/durability-proposals-27e2bf5c-2026-10-03.md`. Do not re-run | review item 4 |
| Queued "Durability" question (ship each, this branch first) | Superseded by proposals Q1–Q4; Ray ruled A on all four (below) | review item 5 |
| Ruled order step 1 "ship THIS branch" | Shipped as **#1620** (auto-merge armed); owed: `mise run land -- 1620` | review items 6, 14 |
| "Main checkout on `main`" | Main checkout is on `docs/handoff-2026-10-03g`; switch back to main after #1620 lands | review item 7 |
| L1 "HOLDS SLOT watch-push" | Held nothing at handoff; successor granted both; Part A b487c3ad lint 0 / verify 0 (170 passed); Part B 8484e5ec lint 0 / verify 0 (171 passed) | review item 10; L1 messages |
| L0 state unstated | No commit (branch at 984d3571); uncommitted WIP incl. new `handoff_inbox.py`; Ray's plan-apply ruling relayed, no ack seen | review item 11 |
| L0/L1 START briefs | Point at removed `.claude/worktrees/coord-docs-20261003e/.agent/plans/…`; tracked copies at `docs/handoffs/briefs/` (in #1620) | review item 8 |
| Delta "PLAN rows from Q3" | Q3 (fix vs PLAN vs issue) was never put to Ray — coordinator default, UNRATIFIED | review item 13 |
| Rulings list | Missing: 14:19 "have a subagent review and fix" (stale branches held unpushed work); 14:37:50 "have the coordinator have a subagent review and provide cited and researched proposals" | review item 12 |

## Rulings received by 28f1a8f7 (Ray, 2026-10-03 ~14:50 CDT, AskUserQuestion)

- Durability Q1 = A: each unit ships as its own docs PR (coordinator+03g = #1620; lane-completion after gates; research+spec after premise-verifier).
- Q2 = A: #1606 next after #1620, then #1614.
- Q3 = A: `coordinator-handoff launch` lists unpushed branches + local `.agent/` drafts as owed ships (no refuse, no auto-push); fold into the #1617 spec under D3 (fix spec `:88`).
- Q4 = A: after #1620 merges, edit #1616/#1618/#1619 once (merged commit + correct branch).
- Upstream worktree-guard issue: file only AFTER due diligence (read-only lane launched).
- "Anything else": no — resume the queue.

## Successor actions

- 27e2bf5c retired through the gate: `coordinator-handoff retire … --adopted 26479` rc=0 (pid 26479 = the handoff-g ship, rc=0, PR #1620).
- Old jobs dir + cold-review report + cold-reviewer local memory backed up to `.agent/state/retired-jobs/27e2bf5c/` (main checkout, gitignored).
- premise-verifier launched on `docs/specs/session-handoff-automation.md` @5c3c155d (P2/P6/P8/P9 first).
- Watcher `dotfiles-20261003.watch`: its watch-push (0ac9bacd) is superseded by the lane-completion docs PR (b487c3ad).
