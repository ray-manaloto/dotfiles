<!-- verbatim SubagentHandback of agent a473b047719b4263a (premise-verifier, session c769e1a1), extracted from its subagent JSONL 2026-10-04 by coordinator 5a11da -->

PREMISE REPORT: spec-dag-tick-pr1.md, checked against the main checkout
(This lane is read-only, so nothing was persisted. The coordinator should save this report verbatim.)

Baseline: `.git/HEAD` is `ref: refs/heads/main`. Both `refs/heads/main` and `refs/remotes/origin/main` are `ee3b29da24a4e64f30f0576353cee0331c7c75b5`. I had no shell, so I could not run `git log` to list what #1662, #1663 and #1664 changed. Instead I re-read every cited file:line at ee3b29da.

**Anchor rot: none found.** Every dag_tick, codex_verdict, coordinator_handoff, session_common, codex_lane, classifier_tables, suites.toml, main.py, pyproject, mise.toml and test anchor still points at the content the spec describes. The only stale fact is the base SHA (P1).

ROWS: 51 checked — 44 CONFIRMED (0 provenance corrected) / 1 REFUTED / 0 UNVERIFIABLE / 4 ASSUMED (2 checkable). The remaining 2 (P44, P46) are confirmed with a caveat, noted on their rows.

- **P1 — REFUTED.** `refs/heads/main:1` = `ee3b29da…`, not `36ab6bba…`. §6 "created from origin/main `36ab6bba`" is stale.
- **P2 — CONFIRMED.** dag_tick.py:1240-1271: state read, roster read, unreadable SKIP, `is_needs_human` SKIP, pid SKIP, Popen. There is no terminal or superseded check. There are exactly 5 `return`s (1243, 1249, 1254, 1266, 1271).
- **P3 — CONFIRMED.** dag_tick.py:1203-1213, :1236-1239.
- **P4 — CONFIRMED.** :180 TERMINAL_STATES; :385-395 `is_terminal`; :558-559 DONE comes first.
- **P5 — CONFIRMED.** :931-948.
- **P6 — CONFIRMED.** :508-512, :678-681, :687-688 (inside the :683-690 return), :1267-1270.
- **P7 — CONFIRMED.** agent-view.md:695: "Restart a session, running or stopped".
- **P8 — CONFIRMED.** agent-view.md:116. This is a UI state; how it maps to state.json is A1.
- **P9 — CONFIRMED.** :1289-1293, :1334-1339, :1436.
- **P10 — CONFIRMED.** codex_verdict.py:434-446, including the blocking `fcntl.flock(handle.fileno(), fcntl.LOCK_EX)` at :440.
- **P11 — CONFIRMED.** :386-396, :592-602.
- **P12 — CONFIRMED.** :546-556, :518-534, :510-517, :564-565.
- **P13 — CONFIRMED.** :127-147 (10 members), :159-170.
- **P14 — CONFIRMED.** :449-498; the split rationale is at :457-460.
- **P15 — CONFIRMED.** codex_lane.py:310-315.
- **P16 — CONFIRMED.** :1008-1013 and :1037-1042 have no `timeout=`. :1014 is `except OSError` only. The precedents are at :258 and :854.
- **P17 — CONFIRMED.** :1423-1428.
- **P18 — CONFIRMED.** stdlib subprocess.py:129, :169. At :554-570 the POSIX path calls `kill()` and then only `wait()`. It does not call communicate a second time. See MISSING-8.
- **P19 — CONFIRMED.** session_common.py:130-152.
- **P20 — CONFIRMED.** :32, :183-203. TimeoutExpired becomes SessionError at :193-195.
- **P21 — CONFIRMED.** :72-74, :87-91, :41. This holds as reader code; that the harness writes `sessionId` and `name` is inferred from `job_record`.
- **P22 — CONFIRMED.** :55-56, :104-116.
- **P23 — CONFIRMED.** coordinator_handoff.py:108, :258-260, :841-842, :1266-1267.
- **P24 — CONFIRMED.** :251-279, :846-847, :1099-1104. The receipt-only and corrupt-state paths behave as V-a2 assumes.
- **P25 — CONFIRMED.** :338, :351-355. This is on every coordinator call only; non-coordinators return at :340-349.
- **P26 — CONFIRMED.** :952-996.
- **P27 — CONFIRMED.** :1148-1170.
- **P28 — CONFIRMED.** :804-810.
- **P29 — CONFIRMED.** coordinator_handoff.py:45-67. reap.py, handoff_inbox.py and session_orphans.py import no dag_tick, and neither do hook_guard, script_guard or bash_budget. Across src, dag_tick is imported only at main.py:50, dag_project.py:72 and codex_lane.py:82.
- **P30 — CONFIRMED.** The repo-wide grep hits only test_dag_tick.py:474 (substring), suites.toml:1963 (prose) and dag_tick.py.
- **P31 — CONFIRMED.** :616-669.
- **P32 — CONFIRMED.** suites.toml:1963, :1974, :1983.
- **P33 — CONFIRMED.** pyproject.toml:71-94, :152-153. There is no `[tool.ruff.lint.pylint]` and no preview.
- **P34 — CONFIRMED.** test_dag_tick.py:2619-2631 and classifier_tables.py:581-588.
- **P35 — CONFIRMED.** classifier_tables.py:1025-1065, :1221-1260.
- **P36 — CONFIRMED.** test_dag_tick.py:111-130, test_codex_lane.py:951-964, test_codex_lane_e2e.py:214-227.
- **P37 — CONFIRMED.** :2408, :2562.
- **P38 — CONFIRMED.** :1993-1997.
- **P39 — CONFIRMED.** :2418-2435.
- **P40 — CONFIRMED.** :2544-2582.
- **P41 — CONFIRMED.** :2173-2247.
- **P42 — CONFIRMED.** A grep of `is_settled=` across tests/ and python/src hits only test_codex_verdict.py:499 and :517.
- **P43 — CONFIRMED.** test_codex_verdict.py:553-578.
- **P44 — CONFIRMED** (body read, not run). :1226-1234.
- **P45 — CONFIRMED.** main.py:1917-1921, mise.toml:721.
- **P46 — CONFIRMED.** I read the handoff-2026-10-04d worktree copy at :7, :8, :10, :14, :49, :55-63. **It is still not on main**: `docs/research/kb/reports/agents/sdlc-team-review-dag-tick-aba49c5d.md` does not exist in the main checkout.
- **P47 — CONFIRMED.** handoff-2026-10-04d spec-dag-tick-safety.md:408-412.
- **A1 — ASSUMED.** Not settleable from code. agent-view.md:116 lists "process ended from outside" as Stopped as well.
- **A2 — ASSUMED.** schemas/ruff.json:3001 names `max-returns`/PLR0911 but gives no default. Nothing contradicts 6.
- **A3 — ASSUMED (checkable).** stdlib :554-570 shows the timeout raised from `communicate(timeout=)`, then `kill` and `wait`, so it is prompt by source. It was not executed.
- **A4 — ASSUMED (checkable).** mise.toml:1565 has `working_directory = "~/dev/github/ray-manaloto/dotfiles"`, and :722 passes no `--cwd`, so `ctx.cwd` = the main checkout today. See MISSING-3 for why this breaks under the PR-2 ruling.

MISSING:
1. **BLOCKING. `workflow.codex-verdict-contract` per_path_tokens break under (d) and D3-A** (suites.toml:2638). The spec checks only dag-tick-wiring and projection tokens (constraint 9), and §2 forbids "any per_path_tokens entry" change. But codex_verdict.py must keep:
   - `'fcntl.flock(handle.fileno(), fcntl.LOCK_EX)'`. A `LOCK_EX | fcntl.LOCK_NB` acquire no longer contains this substring, because the token ends in `LOCK_EX)`.
   - `'gate = lane_is_settled if is_settled is None else is_settled'`. D3-A removes the `is_settled` parameter, so this line disappears.
   - `'def _read_payload('` and `'def _cas_check('`. The decide/effects split must keep both names.
   - `'source.replace(run_dir / PROCESSED_FILENAME)'`.

   In dag_tick.py, the dry-run branch must not respell `'result = codex_verdict.reap('`, `'expected_owner=classified.node_id,'` or `'max_rework=ctx.max_rework,'`. As written, `mise run gate -- run verify` fails. The description at :2630 also says "all ten reap outcomes", which becomes eleven.
2. **V-b1 control arm cannot pass as written.** In the existing fixture, dead1 is DEAD (blocked/idle, empty roster, test_dag_tick.py:2422-2423). With `dry_run=False`, `execute_tick` plans RESPAWN, and the test's `_fail_popen` (:2426-2431) raises. The control needs a recording Popen stub, or an ALIVE node.
3. **A4 is invalidated by the ratified U1 (PR 2).** The plist moves to a pinned `[bootstrap.repos]` deploy clone (spec-dag-tick-safety.md:410). A separate clone's `git worktree list` returns that clone, not the main checkout. `handoff_state_dir` would then point at the deploy clone's `.agent/state/coordinator-handoff`, so the record is "absent" and the node respawns, which fails open. This is non-blocking for PR 1 because the LaunchAgent stays disabled, but it must be a constraint-13 residual and a PR-2 requirement.
4. **Mid-launch window.** A plain `launch_pending` without `started` (coordinator_handoff.py:923; this is the reservation while `claude --bg` runs, up to `LAUNCH_TIMEOUT_S` = 60 s, :87) does not count as "launched". A respawn in that window is possible. This is the same predicate `retire` uses, so it is non-blocking. Record it as a residual.
5. **No test arm for the "coordinator + invalid/missing sessionId → SKIP" decision.** §3a item 4, bullet 4 has no V-a2 row. The revert check counts 5 positives and none covers it.
6. **Unlocked handoff read is safe, but the spec does not say so.** `write_state` is atomic tmp+replace (session_common.py:119-127), and `_read_launch_state` reads the receipt before the state, so a concurrent finalisation is still seen as launched. `_read_launch_state` writes nothing; it only reads and logs a warning. Worth stating, because the spec calls it without `state_lock`.
7. **Docstrings that go stale and are not in the U6 list:**
   - execute_respawn :1171 ("fresh ESCALATION and PID re-check"), :1193 ("covers BOTH axes") and :1203 ("BOTH reads … both decisions"): there are now three reads.
   - The module docstring at :102 ("precondition is PID-liveness only").
   - The new code also needs `session_common.is_coordinator`, `valid_session_id`, `main_checkout` and `SessionError` in dag_tick; constraint 14 lists only the coordinator_handoff import.
8. **§5 "`exec` in the fake is load-bearing" overstates the reason.** On POSIX, `run()` waits only on the direct child after the kill (subprocess.py:567-569). It does not communicate again, so a fake without `exec` still returns promptly and just orphans the `sleep`. Keep `exec`, but justify it as "no orphan". The V-d1 revert timing is unaffected. Non-blocking.
9. **Fixture detail.** V-a2 needs an 8-character node id (`_SESSION_ID_RE` at session_common.py:38, plus the `[:8]` check). Existing fixtures use 6-character ids such as "abc123", so V-a2 cannot reuse them. The spec says this; noting it as a trap.
10. **Citation nit.** The tests/AGENTS.md:113 allowlist is `git`, `sh`/`bash`, `mise`, `uv` and shared.toml tools. It does not name `sleep`, which constraint 11 implies. Non-blocking.

VERDICT: correct the spec first. MISSING-1 makes the verify gate fail as specced, and P1/§6 names a stale base.

Exact corrections:
- **(a) §6 and P1.** Replace `36ab6bba` with `ee3b29da` and branch from current origin/main. Re-confirm P46: the review is still only in the handoff-2026-10-04d worktree.
- **(b) §2.** Add `python/verification/suites.toml` → `workflow.codex-verdict-contract` per_path_tokens as an allowed, reviewed edit:
  - replace `'fcntl.flock(handle.fileno(), fcntl.LOCK_EX)'` with the new bounded-acquire line (for example `fcntl.LOCK_EX | fcntl.LOCK_NB`) plus a `ReapOutcome.LOCK_BUSY: Edge.NONE` token;
  - under D3-A, replace the `gate = lane_is_settled if is_settled is None else is_settled` token with its seams equivalent;
  - update the "ten reap outcomes" prose.

  Keep the D3 decision explicit. Alternatively, keep the §2 ban and pin the exact source strings the implementation must keep. That route is not possible for the LOCK_EX token without a comment-only dodge.
- **(c) Constraint 9.** Extend it to `workflow.codex-verdict-contract` (suites.toml:2638). The implementer must keep `def _read_payload(`, `def _cas_check(` and `source.replace(run_dir / PROCESSED_FILENAME)` in codex_verdict.py, and `result = codex_verdict.reap(`, `expected_owner=classified.node_id,` and `max_rework=ctx.max_rework,` byte-identical in dag_tick.py.
- **(d) V-b1 control.** Use a recording Popen stub, or say the node is made ALIVE.
- **(e) V-a2.** Add the "coordinator name + invalid sessionId → SKIP 'no valid sessionId'" positive and count six positives in its revert check.
- **(f) Constraint 13.** Add two residuals: the A4/U1 deploy-clone state-dir mismatch, which PR 2 must resolve, and the mid-launch `launch_pending`-not-started window.
- **(g) U6 list and constraint 14.** Add the stale docstrings at dag_tick.py:102, :1171, :1193 and :1203, and add the `session_common` imports.

Non-blocking residuals to accept on the record:
- A1, ASSUMED: the stopped-state timing cannot be settled from code.
- A2, ASSUMED: ruff's default return ceiling of 6 is unread, but every codebase precedent is consistent with it.
- A3, ASSUMED (checkable): source-confirmed; no runtime run.
- A4, ASSUMED (checkable): it holds for PR 1 while the LaunchAgent is disabled; it becomes the PR-2 hazard in MISSING-3.
- MISSING-6, MISSING-8, MISSING-9 and MISSING-10: informational.

Files read (all absolute):
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/{dag_tick,codex_verdict,coordinator_handoff,session_common,codex_lane,classifier_tables,main}.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/verification/suites.toml
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/pyproject.toml
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/{test_dag_tick,test_codex_verdict,test_codex_lane,test_codex_lane_e2e}.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/AGENTS.md
- /Users/rmanaloto/.local/share/uv/python/cpython-3.14-macos-aarch64-none/lib/python3.14/subprocess.py
- /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/agent-view.md
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-04d/docs/research/kb/reports/agents/sdlc-team-review-dag-tick-aba49c5d.md
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-04{d,e}/docs/research/kb/raw/specs-2026-10-04d/spec-dag-tick-safety.md

## GitHub repos touched
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): local main checkout at ee3b29da, source, tests and contracts
- [mrkhachaturov/agent-harness-docs](https://github.com/mrkhachaturov/agent-harness-docs): offline agent-view.md, read for respawn/stop semantics
