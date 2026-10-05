# Coordinator-creation requirements — APPROVED by Ray 2026-10-02b (+ all-session addendum)

Sources: outgoing coordinator transcript 98eb9783 (/handoff instruction + answers); coordinator-auto-handoff grilling rounds 1-3 (79921362); staged spec docs/specs/coordinator-auto-handoff-2026-10-02.md. Compiled by review fork c059.

## Trigger + enforcement
1. Auto-handoff at 30% context USED via a function hook on `session.measure` that AUTO-SUBMITS `/coordinator-handoff` (not a nudge); active only in coordinator sessions (by name).
2. Re-fire every +5% over threshold if the handoff fails; 30% and 5% configurable.
3. Status-line state every turn (`handoff 23%/30%` / `fired` / `ERROR`) so a silently failed hook can't read as "below threshold".
4. Prove the real submit path with a probe arg before relying on it.
5. Skill -> mise task -> python ("update the skills so the steps are automated").
6. #823 75% hard deny = separate follow-up.

## Old coordinator
7. Run `/session-handoff` fully unattended; ambiguities/review findings become OWED/OPEN items in the handoff instead of asking. "Make sure all issues are fixed and applied and not lost."
8. Commit handoff to tracked `docs/handoffs/session-….md` on a docs branch; push with ssh keepalive; keep `.agent/plans/main-checkout-ship-queue.md` current; ship that docs branch as a PR early.
9. Launch successor: `claude --bg -n <name> --settings '{"crossSessionInbound":"accept","worktree":{"bgIsolation":"none"}}'` from the dotfiles MAIN checkout (first `git worktree list` entry), never a worktree.
10. Successor name: `dotfiles-<yyyyMMdd'T'HHmmss.SSSSSSSSSX>.coordinator`, America/Chicago, 9-digit ns, e.g. `dotfiles-20261002T163103.123456789-05.coordinator`.
11. At successor launch, census every heavy run it owns (ship/land/sync/verify-local/bounded-wait/kb-ship/kb-land: pid, argv, log) into the brief.
12. Brief carries old name, old session id, old transcript path, handoff path, ship-queue path. Old coordinator then idles, starts nothing new.

## Successor
13. Spawn a review subagent: old transcript vs handoff; fix lost/incorrect/vague items in handoff AND task_plan.md.
14. Announce new coordinator name to every lane in ListAgents.
15. Per recorded heavy run: wait for it or explicitly adopt its result.
16. Retire old via `coordinator-handoff retire` — refuses (rc 1, names pid/argv/log) while any recorded run is alive and not adopted, or harness inFlight tasks exist; else `claude stop <old id>`. Never a bare `claude stop` on a coordinator.
17. Resume the ship queue keeping host SLOT discipline (one heavy test/gate run host-wide) and one-shipper-per-repo.
18. Identify "newest coordinator" by ListAgents recency / notify message, NOT lexical name sort (old `20261002b` sorts after new `20261002T…`).
19. Before any `claude stop`, live-probe what it does to bg children; ticket a ship/land detach only if they die.

## Brief must carry
20. Autonomy: coordinate autonomously, ask Ray ONLY for human-intervention items (agent-denied actions, credential rotation). Supersedes "ask Ray before each GitHub write".
21. AskUserQuestion format: recommended first, PRO/CON, citation, notes, "Other", final open "anything else" question.
22. Lanes report to coordinator BY NAME; fallback `.agent/plans/handoff-inbox/<lane>.md`; successor reads that dir at start.

## ADDENDUM (Ray, 2026-10-02b) — ALL sessions, both repos
23. Every Claude session in dotfiles AND knowledge-base (not only coordinators) gets a Claude mod FUNCTION HOOK that on each NEW session:
    a. runs `/reload-skills` and `/reload-plugins --force`;
    b. renames the session to `<project>-<yyyyMMdd'T'HHmmss.SSSSSSSSSX>.<feature>` (America/Chicago, 9-digit ns); <project> = `kb` (knowledge-base) | `dotfiles`; <feature> = the task the session is working on.
    KB half needs a KB lane.

## Gaps observed in the 2026-10-02b takeover
- (10) named `dotfiles-20261002b.coordinator` — ISO ruling never reached coordinator/task_plan/brief.
- (13) old coordinator ran the review itself.
- (16) old coordinator ended with no retire check; Lane G ship survived on a polite message.
- (11/12/20) brief lacked transcript path, heavy-run census, autonomy rule (said "ask Ray each GitHub write").
- (1-6) trigger unbuilt.
- (8) docs/handoff-2026-10-02 has no PR.
