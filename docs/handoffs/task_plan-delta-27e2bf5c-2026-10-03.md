# task_plan.md delta — coordinator 27e2bf5c, 2026-10-03 (pending a sanctioned write route, Ray ruling b)

`task_plan.md` is gitignored in the main checkout; this isolated coordinator cannot Edit it and may not Bash-write it.
Apply via `mise run handoff-inbox` / plan verb once lane L0 ships it, then `mise run plan-attest`.

1. :2511 — replace "code fix (A) DONE" with "code fix (A) DONE on feat/session-autostart-no-prompts (060de30b), NOT on
   main — origin/main dag_tick.py:1384 still runs `claude stop`; ships at slot 3 (autostart)".
2. :2547 — #1606 codex fix lane: "DONE 14:09, rc 0; coordinator re-verified; committed 0125fc4d; gates lint/verify/
   lint-docs rc=0, pytest only the #1614 worktree failure; Opus cold review running".
3. Add under the current section — Ray rulings 2026-10-03:
   - 14:1x: stale branches removed after log check (7 archived to local tags archive/2026-10-03/*; native-service
     locked/kept); watcher lane after the item-9 probe; resume queue.
   - ~14:35 (via 998ab91b): (a) worktree-guard false refusals → local workaround + upstream issue after due diligence;
     (b) NEVER Bash-bypass a refused main-checkout write; route via mise tasks.
   - ~14:50: apply 998ab91b findings — Q1 fix reports on de9575bd then ship; Q2 five file-keyed groups (L0 urgent code,
     L1 docs/rules, L2 after #1606, L3 after 1502, L4 coordinator-direct); Q4 urgent now, no reorder; Q5 typed findings
     + `mise run handoff-apply` ledger. Report:
     docs/research/kb/reports/agents/apply-998ab91b-findings-proposals-2026-10-03.md.
   - ~14:55 handoff automation: D1 S1 ($.plugin.root CLI resolution, "n/a (CLI skew)"); D2 role registry, lanes 40%
     CONFIGURABLE (default 40), coordinator 30%; D3 own branch + issues + SendMessage digest; D4 message + rebase at next
     boundary. Spec drafting on research/session-handoff-automation.
4. New rows: L0 (fix/L0-handoff-findings-urgent, lane dotfiles-20261003T143441.L0-urgent-code), L1
   (docs/L1-handoff-findings-rules + de9575bd fixes, lane dotfiles-20261003T143441.L1-docs-rules), L2 after #1606, L3
   after 1502, handoff-automation spec → implementation after #1606; PLAN rows from Q3 (VG-V6 autoCompact question to
   Ray, DE-F6 sweep re-run with OpenHands/ruflo, PC-F4 coordinator-alive check, PC-F6 draft-spec promote/discard, MR-F3
   watcher brief, S1003f-1 re-triage after L0).
