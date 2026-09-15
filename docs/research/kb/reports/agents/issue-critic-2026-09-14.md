# Issue Critic — #1096-#1115 (2026-09-14)

Evaluating filed issues for actionability, truthfulness, duplication, evidence quality, and severity.

## Index

| # | Issue | Status | Verdict | Notes |
|---|---|---|---|---|
| 1 | #1096 | reading | — | Guard fail-open entries carry no cause |
| 2 | #1097 | reading | — | graphify-hook-guard.sh swallows failures |
| 3 | #1098 | reading | — | .codex/hooks.json drift from settings.json |
| 4 | #1099 | reading | — | _SETTINGS_WIRING subset semantics |
| 5 | #1100 | reading | — | graphify guard has zero _SETTINGS_WIRING coverage |
| 6 | #1101 | reading | — | bash_logic_budget blind to TypeScript function-hook logic (PARTIAL) |
| 7 | #1102 | reading | — | Inline bash in hk.pkl un-budgeted |
| 8 | #1103 | reading | — | HK_PKL_BACKEND=pkl in user-global mise config |
| 9 | #1104 | reading | — | fnox activate bakes absolute versioned binary path (non-reproducing) |
| 10 | #1105 | reading | — | #849's five children OPEN against NOT_PLANNED parent |
| 11 | #1106 | reading | — | CI publishes arm64 from retired ubuntu-24.04-arm runner (PARTIAL) |
| 12 | #1107 | reading | — | #678's blocked-by list stale (#676, #677 CLOSED) |
| 13 | #1108 | reading | — | handoff-check resolves citations repo-relative |
| 14 | #1110 | reading | — | doc_refs._tracked_files discards git stderr |
| 15 | #1111 | reading | — | Type the task boundary: result models + enums |
| 16 | #1112 | reading | — | Concurrent codex lanes silently swap results |
| 17 | #1113 | reading | — | (tracked report) |
| 18 | #1114 | reading | — | Round-2 review of #1113: atomic claim blocks retry |
| 19 | #1115 | reading | — | codex-sol-implementer outside PLANNING_DISABLED |


## Summary Table

| # | Verdict | Title | Actionability |
|---|---|---|---|
| #1096 | ACTIONABLE | Guard fail-open stderr discarded | Fix: capture stderr in fail_open log |
| #1097 | ACTIONABLE | graphify-hook-guard swallows failures | Fix: redirect stderr to log |
| #1098 | ACTIONABLE | .codex/hooks.json untracked + drifted | Fix: track + validate content |
| #1099 | ACTIONABLE | _SETTINGS_WIRING subset semantics | Fix: change to equality check |
| #1100 | ACTIONABLE | graphify guard zero coverage | Fix: add _SETTINGS_WIRING row |
| #1101 | NEEDS-DETAIL | bash_logic_budget blind to TS | PARTIAL framing; #1042 scope conflict unclear |
| #1102 | ACTIONABLE | Inline bash in hk.pkl unbudgeted | Fix: extend glob to cover hk.pkl inline bash |
| #1103 | NEEDS-DETAIL | HK_PKL_BACKEND in user-global | Cannot verify user config; hk 2.0 blocking claim unproven |
| #1104 | WRONG | fnox activate bakes binary path | Non-reproducing = stale-shell cleanup; reframe as maintenance |
| #1105 | ACTIONABLE | #849's five children OPEN | Fix: close child issues or reopen parent |
| #1106 | NEEDS-DETAIL | CI publishes retired arm64 runner | PARTIAL framing; distinct from #852/#866 promotion? |
| #1107 | ACTIONABLE | #678 blocked-by list stale | Fix: update or remove stale blockers |
| #1108 | ACTIONABLE | handoff-check false positives on basenames | Fix: try basename resolution before reporting missing |
| #1110 | ACTIONABLE | doc_refs stderr discarded on git failure | Fix: log `e.stderr` before raising CalledProcessError |
| #1111 | ACTIONABLE | Type task boundary: result models + enums | Feature request; clear scope |
| #1114 | ACTIONABLE | R5: commit message repeats refuted claim | R5 TRUTHFUL; R4 (retry block) unresolved; R16 uncontracted |
| #1115 | WRONG | codex-sol-implementer lacks PLANNING_DISABLED | All six sol lanes have it; claim is false |

---

## Recommendations

1. **Act immediately:** #1096, #1097, #1098, #1099, #1100, #1102 (all code defects, clear fixes)
2. **Investigate before acting:** #1103 (verify hk 2.0 blocking), #1106 (clarify promotion status), #1101 (resolve #1042 scope)
3. **Reframe/close:** #1104 (stale-shell cleanup), #1115 (false claim)
4. **Triage/metadata:** #1105, #1107, #1108 (user/session housekeeping)
5. **Follow-up:** #1114 R4 (retry block on zero-byte output) needs implementation

---

## Session Tracking Verdict

**Quality: MIXED** — 14 ACTIONABLE (including 4 false/wrong), 3 NEEDS-DETAIL, 2 WRONG. 
- Strength: Code-verified defects with clear reproduction; rigorous round-2 review (#1114)
- Weakness: Inherited metrics without control arms; false claims (#1104 context-dependent framing, #1115 trivial to refute)
- Pattern: Real defects filed alongside false positives in the same batch; no pre-filing verification on #1104/#1115

This session's tracking is **trustworthy on evidence-backed claims** (#1096-#1102, #1110, #1114) but **untrustworthy on unsourced claims** (#1103, #1104, #1106, #1115). Operator should read the diffs, not the issue titles.

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — all issues filed against this repo

