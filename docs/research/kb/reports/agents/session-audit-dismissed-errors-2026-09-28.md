# Session audit — dismissed errors and repeated mistakes (Brief M), 2026-09-28

Session `52723a40-6c46-475a-9854-b0b3ef2cf856` ("dotfiles-20260927.000"). Read-only review; this file is the only write.
Scope: main transcript + 4 subagent transcripts. Only DISMISSED or plan-recorded-only items are listed as findings.

Status: COMPLETE (written incrementally; final 2026-09-28).

## Summary

| # | Sev | Class | One line | Disposition |
|---|---|---|---|---|
| F0 | HIGH | unrecorded, contradicts plan | #1412 added the sdlc_team `PLANNING_DISABLED` scrub that round 5 (`task_plan.md:652`), `:420`, `:664` and open #1357 forbid; grilling Q3 didn't name the conflict | FIX-NOW: AskUserQuestion naming the conflict → revert + #1357 contract, or re-rule |
| F1 | MED | dismissed | `session-agentsview-pass` step-3c printed 0 for 4 real Bash report writes; called "clean" | PLAN (S28-1), one ticket |
| F2 | MED | mis-recorded, repeated | "harness notification lied" written again (progress.md, new memory) against its memory's 09-25 correction; the cause was a batched wrapper ending in `| tail` | FIX-NOW memory/progress wording; PLAN (S28-2) `mise run gates` |
| F3 | MED | recorded (M-1), recurred | invented `bounded-wait --file-contains`, rc hidden behind `>/dev/null ||`, call auto-backgrounded | PLAN: unfold M-1 from the class-fix spec; 1 /grilling Q |
| F4 | MED | recorded (#1388, S27-14), recurred ×5 | zsh `====` aborted 5 commands (main ×2, Audits N/P/M) + 1 NOMATCH | PLAN: ask S27-14 first next session |
| F5 | LOW | recorded (item 13, S27-2.4, #1056), recurred ×3 | version-less `timeout` shim broke 3 subagent calls, incl. the bundled /code-review fork | PLAN: raise priority; host fix only |
| F6 | LOW | recorded (M-3, S27-2.5), stale numbers | doctor DRIFT/currency lines; graphify user pin now 0.9.70 and rising | PLAN: refresh S27-2.5 text |
| F7 | LOW | recorded (23(e)) | aggregated-research `$comment` notice | PLAN: tick only |
| F8 | LOW | dismissed (class recorded S1-3) | graphify never consulted; graph stale now (69 files) | FIX-NOW: handoff trap or rebuild |
| F9 | LOW | stale plan item | `env -u HK_PKL_BACKEND` ritual ×8; S27-2 item 3's probe is now ABSENT | FIX-NOW: mark DONE (Claude env) |
| F10 | LOW | unrecorded, repeated ×2 | brief-mode turn ended without SendUserMessage | memory line |
| F11 | LOW | unrecorded residue | `research-five-source-gate` worktree left detached | PLAN: fold into S27-5 |
| F12 | LOW | recorded (S27-13), grown | pwf injection 25.4 KB → 2 KB preview ×15; Stop nag ×12 | PLAN: append measurement |

Write scope: this lane wrote ONLY this file. The brief's "edit nothing else" overrides the SubagentStart contract's
`findings.md`/`progress.md` appends, so the coordinator should append the condensed lines.

## Method

- Extracted every tool_use/tool_result, user message and system/attachment row from the main transcript
  (`52723a40-….jsonl`, 1,486 compact rows by the end of the audit) and from the four other subagent transcripts
  (`agent-a7541bcdccffc815f` KB verification, `agent-af3d1a5f11e86c6f1` /code-review fork, `agent-a1789afcceb3a6ef3` Audit N,
  `agent-af721ac0b54f84fe9` Audit P; this lane is `agent-a7cf8d62e060c4d0b`). "Ordinal" below = JSONL line number in the
  transcript named.
- Grepped for `is_error`, `rc=[1-9]`, `Exit code`, `WARN`, `DRIFT`, `denied`, `ERROR`, `FAIL`, `not found`, then read
  every main-transcript row in order (not only the grep hits).
- For each item, looked up its disposition in `task_plan.md`, `findings.md`, `progress.md`, the new session memory
  `project_session_2026-09-28.md`, and git (`6c9576f0`, `bed7cbb2`).
- No `permission denied` / hook-deny rows occurred in any transcript (grep `denied` → 0 in main; control: the same grep
  shape finds `denied` in `.claude/rules/do-not.md`).

## Fixed or correctly dispositioned (NOT findings — listed for coverage)

| Item | Where | Disposition |
|---|---|---|
| `fatal: 'main' is already used by worktree` on `git checkout main` | main ord 157 | Branched from `origin/main` (ord 165); later Ray ruled detach (ord 422). Residue is F11. |
| ty `invalid-argument-type` ×5 (`_SupervisorFixture(**fixture)` with a new list field) → fmt rc=1, lint rc=1 | main ord 549/574 | FIXED ord 579 (capture moved to a `_run_supervisor` parameter); fmt/lint rc=0 ord 595; in `78bb5e07`→`3340a939`→`6c9576f0`. |
| sdlc-team lane P2 (relative `which("mise")`) and P3 (CLI_MISSING wording) | main ord 789 | FIXED ord 809, each fail-armed (ord 816: 4 arms rc=1); in `65e70f73`→`6c9576f0`; report `1319-live-arm-sdlc-team-1362-review-2026-09-27.md`. Private-helper test concern declined with reason in that report. |
| Codex cold lens "runtime validation unverified" (read-only sandbox blocks uv cache) ×2 | main ord 762, 1353 | Accepted by design (cold lens is read-only); coordinator's own pytest 3,984 passed (ord 883). |
| `/code-review` fork: "ReportFindings tool isn't in my tool list" | sub af3d1a5f ord 60 | Not a defect: `$CC/code-review.md:329` — ReportFindings is used only when a host app requests a findings list; text output is the documented CLI path. Report persisted verbatim (`code-review-1362-2026-09-27.md`). |
| `git grep -E '#79[3567]\b'` returned nothing on a known-present term | sub a7541bcd ord 43-50 | Caught by the agent's own control arm (`\b` form rc=1, plain form rc=0) and recorded as a "Probe note" in the tracked `kb-1310-children-verification-2026-09-28.md`. |
| rule-sync "advisory divergence (blocks nothing)" | sub a7541bcd ord 176 | Advisory by design; rc=0. |
| Test fail-arms rc=1 (ord 260, 494, 511, 595, 816) | main | Intentional control arms; each restored and re-passed. |
| `mise which codex` rc=1 "codex is a mise bin however it is not currently active" | Audit P `af721ac0` ord ~111-120 | Audit P's own probe finding (the host resolves native codex through PATH, since root `mise.toml` disables the npm pin); Audit P reports it, so it is not duplicated here. |
| `/code-review` and the codex cold lens both missed the 2 defects the live sdlc-team lane found | main ord 729, 762 vs 789 | Recorded as a lesson in memory `project_session_2026-09-28.md` and the lane report; not an error. |

## Findings

### F1 — MEDIUM — `session-agentsview-pass` step-3c census is blind to Bash report writes; its 0 was reported as "clean" (DISMISSED)

- **Claim.** The handoff census printed `step-3c writes : 0 under docs/research/kb/reports/agents/` for the main
  session (main ord 1230), and the coordinator told Ray "The session census is clean" (ord 1257). By then the session
  had already written four reports into that directory through Bash: a `{ …; } > $R/1319-live-arm-…md` redirect with
  `R=docs/research/kb/reports/agents` (ord 821, also `cold-lens-1362…`, `code-review-1362…`) and a
  `cp $S/kb-1310-children-verification-2026-09-28.md docs/research/kb/reports/agents/…` (ord 1077).
- **Evidence.** `python/src/dotfiles_setup/agentsview_pass.py:27-30` — `_BASH_REPORT_WRITE` only matches a `>`/`>>`
  or `tee` target containing the literal prefix. A `$VAR/` redirect target and `cp`/`mv`/`install` never match.
  Non-Bash writes count only for `Write|Edit|MultiEdit|NotebookEdit` (`:225-227`); the session used none of them for
  reports before ord 1230.
- **Control arm.** The positive exists: `git show --name-only 6c9576f0 bed7cbb2 | grep reports/agents` lists all four
  files (`1319-live-arm-sdlc-team-1362-review-2026-09-27.md`, `code-review-1362-…`, `cold-lens-1362-…`,
  `kb-1310-children-verification-2026-09-28.md`). The census ran after they were written and printed 0, so it can't see
  them. This is the "0-result probe with no control arm" class (`.claude/rules/probes-need-a-control-arm.md` rule 3).
- **Disposition: PLAN** (one small ticket; no /grilling). Proposed task_plan line, next to S27-10:
  > (S28-1) `agentsview_pass` step-3c census misses Bash report writes whose target is a `$VAR/…` path or a
  > `cp`/`mv`/`install` destination (2026-09-28: printed 0 for 4 real writes, and the handoff called it "clean"). Fix: count
  > from `git diff --name-only <first-session-commit>^..HEAD -- docs/research/kb/reports/agents/` plus untracked files
  > there, instead of parsing argv. Tool-agnostic, and it can't be evaded by spelling. Arms: this session → ≥4; a session
  > with no report writes → 0; `R=…; echo x > $R/a.md` → 1. File via `issue-filer`.

### F2 — MEDIUM — The "harness notification lied" misattribution was written down again, contradicting its own memory's correction (REPEATED; mis-recorded)

- **Claim.** Ord 516 batched `fmt; lint; pytest; verify; grep … | tail -2` into one backgrounded command. Its
  notification (ord 549, `[exited with code 0]`) truthfully reported the wrapper's LAST command, while the log held
  `fmt rc=1` / `lint rc=1`. The session then recorded this as the harness lying, in `progress.md` (appended at ord 1131:
  "Harness notification said exit 0 over fmt rc=1 / lint rc=1 once more") and in the new memory
  `project_session_2026-09-28.md` ("Harness background notification again reported "exit code 0" over real fmt/lint
  rc=1"). The linked memory `feedback_background_task_notification_can_lie.md` has carried a **Correction
  (2026-09-25)** since 2026-09-25: "The notification reports the LAST command of the wrapper, not the gate … the premise
  'the harness lies' does not [stand]". The session read the log correctly (ord 564-574), so no bad state shipped. The
  defect is the record: it teaches the next session the wrong cause, and the same batching shape was used again at ord
  855 and 1131.
- **Control arm.** Ord 516's command text ends `grep -E "passed|failed" $S/verify.log | tail -2`, so rc 0 is what that
  pipeline returns. The gate rcs sit on their own `echo "… rc=$?"` lines, and fmt/lint read 1 there.
- **Disposition: FIX-NOW** (coordinator; this lane is read-only):
  1. In memory `project_session_2026-09-28.md`, replace the bullet with: "The backgrounded 4-gate wrapper exited 0
     because its last command was `grep … | tail`; the real `fmt rc=1` / `lint rc=1` were on their own lines in the log.
     End a batched gate wrapper with an aggregate rc, or read each `rc=` line
     ([[feedback_background_task_notification_can_lie]] 2026-09-25 correction)."
  2. `progress.md` is append-only: append a correction line rather than editing the old one ("2026-09-28 correction:
     the exit 0 was the wrapper's last command (`tail`), not a harness fault").
- **Also PLAN** (no /grilling):
  > (S28-2) Stop hand-batching gates. Expose `pr.run_gates`/`gate_matrix` (`python/src/dotfiles_setup/pr.py:371`, the
  > matrix `ship` already runs) as `mise run gates`, returning the OR of the gate rcs, and point the SKILL/rule examples
  > at it. Until then, end any batched gate wrapper with `exit $((fmt|lint|pytest|verify))`.

### F3 — MEDIUM — Invented `bounded-wait --file-contains` again, rc hidden, and the call auto-backgrounded (RECORDED since 2026-09-23 as M-1; guard still unbuilt)

- **Claim.** Main ord 621:
  `mise run bounded-wait -- --deadline 3000 --file-contains 'rc=' --file … > /dev/null 2>&1 || mise run bounded-wait -- --deadline 3000 --cmd 'grep -q "^rc=" …' >/dev/null 2>&1; echo "wait rc=$?"`.
  `--file-contains` doesn't exist, and `bounded_wait.py:82` requires exactly one of `--file`/`--cmd`. The usage error
  was sent to `/dev/null` and absorbed by `||`. The Bash call carried no `timeout` parameter, so it hit the 600 s tool
  cap and was moved to the background (ord 622), and its `wait rc` line was never read. The land result was read from
  the log instead (ord 644), so the outcome was sound.
- **Recorded.** `task_plan.md:717-718` (M-1: "never `--file-contains`; never hide its rc") and `:726` (M-1 → a guard
  rule inside the codex class-fix spec). Five days later it recurred verbatim, because a rule folded into a large spec
  has not shipped.
- **Control arm.** `grep -n "file-contains" task_plan.md` → 2 hits (717, 726). The same grep on transcript ord 621 → 1
  hit, so the recurrence is real and the earlier record exists.
- **Disposition: PLAN** (one /grilling question, then /to-tickets). Append to M-1:
  > M-1 RECURRED 2026-09-28 (session 52723a40 ord 621; usage error sent to /dev/null behind `||`). Unfold it from the
  > codex class-fix spec and ship it alone. /grilling one question: (a) make the need real — add
  > `bounded-wait --file <p> --contains <s>`, since both sessions reached for exactly that; or (b) a `hook_guard` deny for
  > `bounded-wait … --file-contains` plus any `bounded-wait … >/dev/null 2>&1 ||`. Recommend (a)+(b-second-half).
  > Arms: the invented form denied or working; `--file x` allowed.

### F4 — MEDIUM — zsh `=`-expansion separators aborted 5 commands this session, including in this audit lane (RECORDED: #1388 and S27-14; still unbuilt)

- **Claim / evidence.** An unquoted `echo ====…` word is an `=cmd` lookup in zsh, and it aborts the rest of the
  command:
  - main ord 80: `echo ======` → `(eval):1: =====` not found; tool rc=1 over `session-state rc=0` / `handoff-check rc=0`.
  - main ord 564→567: `echo ====LINT` → rc=1. The lint-log grep after it **never ran**, so that call printed only
    fmt.log hits, and the lint failure was only seen at ord 571.
  - Audit N (`agent-a1789afcceb3a6ef3`) ord 34→35: `echo ====` → `(eval):1: === not found`.
  - Audit P (`agent-af721ac0b54f84fe9`) ord 30→32: `… && echo ==== && cat -n docs/receipts/1319.md` → rc=1.
  - This lane (Audit M): `echo ======P` → `(eval):1: =====P not found`. The brief warned about it explicitly, and the
    trap fired anyway.

  Also 1× zsh NOMATCH: Audit N ord 171→172, `ls .agent/plans/session-2026-09-28*` → `no matches found` (same S27-14
  cluster).
- **Recorded.** `task_plan.md:729-733` (#1388, the guard rule; "bit 3 sessions") and `:1036-1037` (S27-14: Ray to choose
  `setopt NO_EQUALS NO_NOMATCH` vs the #1388 guard). Memory `feedback_zsh_equals_expansion.md` exists. It doesn't
  help: 3 of the 5 hits were in subagents, which don't load memory, and 1 was in a lane whose brief said "Quote shell
  separators".
- **Control arm.** Each hit's output contains `(eval):1: =… not found` and the tool result is `Exit code 1`. A quoted
  `echo '===='` in the same lanes succeeds (e.g. this lane's later `echo '--- P'` ran).
- **Disposition: PLAN** (the one /grilling question is already specified as S27-14). Append to S27-14:
  > RECURRED 5× on 2026-09-28 (main ×2, Audit N, Audit P, Audit M; 3 in subagents that memory can't reach, 1 despite an
  > explicit brief warning). Brief text and memory are proven insufficient. Ask the S27-14 question FIRST next session;
  > either answer closes it: user-level `setopt NO_EQUALS NO_NOMATCH` (Ray-applied) or #1388's guard.

### F5 — LOW — The version-less global `timeout` shim broke 3 subagent calls (RECORDED: item 13 / S27-2 item 4 / #1056)

- **Evidence.** `mise ERROR No version is set for shim: timeout` at: the `/code-review` fork (`agent-af3d1a5f11e86c6f1`
  ord 51, `timeout 60 mise exec -- codex --version`); the KB verification agent (`agent-a7541bcdccffc815f` ord 171,
  `timeout 300 mise -C … run rule-sync`; it attributed the rc=1 correctly, citing memory, at ord 174); Audit N (`agent-a1789afcceb3a6ef3` ord 119-120, `timeout 60 agentsview --help`). Each lane
  recovered by dropping `timeout`.
- **Recorded.** `task_plan.md:856-858` (item 13, `/grilling`: pin coreutils in dotfiles or remove the global shim; #1056)
  and `:1000` (S27-2 item 4, owner Ray, user-level).
- **Control arm.** The same lanes' un-wrapped reruns succeeded (af3d1a5f ord 55-56 `codex-cli 0.157.1`; a7541bcd ord
  175-176 rule-sync rc=0), so the shim, not the tool, failed.
- **Disposition: PLAN.** Append to item 13:
  > RECURRED 3× on 2026-09-28, all in subagents. One was the bundled `/code-review` fork, whose prompt we don't author, so
  > no brief line or memory can prevent it. Only the host fix (pin or remove the shim) closes it; raise priority.

### F0 — HIGH — #1412 shipped the `PLANNING_DISABLED` scrub on sdlc_team that Ray's round-5 ruling and open ticket #1357 forbid; the grilling question never named the conflict (UNRECORDED; contradicts the plan)

- **Claim.** The session framed "`sdlc_team.py` never sets `PLANNING_DISABLED=1`" as a **new finding** (main ord 324 in
  `findings.md`, ord 329 to Ray). It asked Q3 "Fix it in this PR? (Recommended)" at ord 351, citing only
  `codex_lane.py:135`. Ray accepted the recommendation (ord 352), and #1412 (`6c9576f0`) now passes
  `env={**os.environ, **codex_lane.LANE_ENV_OVERRIDES}` on the supervisor's codex `Popen`, with a fail-armed test that
  pins the scrub in place. That is the opposite of the standing design:
  - `task_plan.md:420`: "⚠️ SUPERSEDED 2026-09-23 by #1351 …: … do NOT scrub `sdlc_team` with `PLANNING_DISABLED`".
  - `task_plan.md:652`: "Rulings round 5 (Ray, 2026-09-23): sdlc_team lanes SEE the plan (no `PLANNING_DISABLED` scrub)".
  - `task_plan.md:664`: Phase 10 step 5's "`PLANNING_DISABLED=1` for sdlc_team" is SUPERSEDED.
  - #1351's corrections comment: "Worker lanes / sdlc_team = `mise run sdlc-team` … These lanes see the plan."
  - Design of record `docs/research/kb/reports/agents/pwf-migration-fable-round3-2026-09-23.md:43-46`: lanes "already
    see the plan … it needs a guard so it is not 'fixed' back". It specifies a `regex_forbid` contract "no
    `PLANNING_DISABLED` in `sdlc_team.py`".
  - Open ticket **#1357** "pwf migration D6: worker lanes see the plan; pre-dispatch refusal matrix; scrub forbidden by
    contract".

  The guard the design called for didn't exist yet, so nothing stopped the regression. The motivation the session gave,
  the 2026-09-22c "wrong plan" incident, is the case #1357's pre-dispatch attestation check was designed to handle
  (refuse on MISSING/MISMATCH). The scrub was not the chosen remedy.
- **Also propagated.** Memory `project_session_2026-09-28.md` now teaches "⭐ sdlc-team lanes were the only codex lanes
  WITHOUT `PLANNING_DISABLED=1` … Fixed in #1412". The #1319 receipt/commit bodies and `findings.md` (ord 324/400)
  describe it the same way.
- **Control arm.** `grep -n 'no \`PLANNING_DISABLED\` scrub' task_plan.md` → `:652`. The main transcript contains no
  mention of `scrub`, `round 5`, `#1357` or `SEE the plan` (grep → 0 relevant hits; the same grep finds the unrelated
  "SUPERSEDED 2026-09-24" at extract row 88, so it can match). Q3's `description` cites only `codex_lane.py:135` and
  `sdlc_team.py`.
- **Why it slipped.** The grilling checked the code (the class audit, ord 293-311) but not the plan's rulings on the same
  symbol. The pwf injection doesn't carry `:420`/`:652` at all (F12). The plan ranges the session did read by `sed`
  (`775-860`, `960-1000`, `1080-1095` at ord 105/119/139) don't include `:420` or `:652`.
  memory `feedback_clarify_before_acting` requires: "A user ruling conflicting with a protocol ⇒ re-ask NAMING the
  conflict".
- **Disposition: FIX-NOW decision, then PLAN.** One AskUserQuestion to Ray that NAMES the conflict (cite
  `task_plan.md:420/652/664`, #1357, round-3 design `:43-46`):
  - (a) *(Recommended)* Revert only the env override + its test in a small PR. Keep the `mise exec` launcher fix. Land
    #1357's `regex_forbid` contract with it or right after, so the scrub cannot return. Correct the memory bullet
    and append a correction to `findings.md`.
  - (b) Ray re-rules that sdlc_team lanes stay scrubbed until #1357. Then amend `task_plan.md:420/652/664`, comment on
    #1351/#1357 that the scrub exists (#1412) and D6 must remove it, and update the round-3 design pointer.

  Proposed task_plan line (either branch):
  > (S28-0) CONFLICT: #1412 (`6c9576f0`) added `PLANNING_DISABLED=1` to the sdlc_team supervisor Popen, contrary to
  > round 5 (`:652`), `:420`, `:664` and open #1357 (D6 "scrub forbidden by contract"). Ray to rule (revert + land #1357's
  > contract, or re-rule). The grilling Q3 on 2026-09-27 did not cite the ruling. No /to-spec needed: #1357 already
  > specifies the contract.

### F6 — LOW — SessionStart doctor DRIFT and [currency] lines: all RECORDED, but two plan numbers are stale and the graphify drift keeps moving

- **Evidence.** Main ord 7 (SessionStart hook stdout):
  `DRIFT doctor[listing-budget]: agent 'antigravity-delegate' … 1789-char description over the HARD 1536 cap`;
  `DRIFT doctor[graphify-skill-surface]: path-binary …/pipx-graphifyy/0.9.70/bin/graphify reports 0.9.70 != locked 0.9.65`;
  `[currency] graphify: pin — pyproject.toml has no exact pin for 'graphifyy'`; `doppler: last upstream check was 2026-08-12`;
  `graphify: no upstream version has ever been recorded`. None was touched this session.
- **Recorded.** `task_plan.md:719-722` (M-3: antigravity 1,789 > 1,536, `graphifyy` exact pin, doppler stale, graphify
  upstream never recorded; "graphify PATH drift … (0.9.68 vs 0.9.65 on 2026-09-25) = #1344"). `:1001-1002` (S27-2 item 5:
  "0.9.69 vs lock 0.9.65 (pick: lower the user-global pin, or `mise run graphify-upgrade`)"). `:916-917` (startup-noise
  cluster: one `/grilling` round "at the start of the next session that touches `doctor.toml`; until then these lines
  are known noise").
- **What is new.** The user-global pin went 0.9.68 (09-25) → 0.9.69 (09-27) → **0.9.70** (today;
  `~/.config/mise/config.toml:195` `"pipx:graphifyy" = { version = "0.9.70", …, minimum_release_age = "0s" }`). Something
  or someone bumps the user-global pin forward, so "lower the user-global pin" is overtaken every few days, while the
  repo lock stays at 0.9.65 (`graphify-health` today: `runtime=0.9.65`).
- **Control arm.** `mise ls pipx:graphifyy` shows 0.9.63, 0.9.69 (pruned in 14h) and 0.9.70 (config), so the drift
  direction is observed, not inferred.
- **Disposition: PLAN** (text refresh; the /grilling is already scheduled). Edit S27-2 item 5 to read "0.9.70 (2026-09-28;
  the user-global pin is being bumped: 0.9.68→0.9.69→0.9.70 in 3 days) vs lock 0.9.65. Lowering the user pin will not
  stick; decide `graphify-upgrade` (raise the lock) or find what bumps `~/.config/mise/config.toml:195`." Update M-3's
  "0.9.68" to point at S27-2 item 5 instead of carrying its own number.

### F7 — LOW — `aggregated-research: hooks.json: unknown key "$comment" ignored` at startup (RECORDED 23(e))

- **Evidence.** Main ord 9 (system notice at session start).
- **Recorded.** `task_plan.md:897-898` (item 23(e) F11: "restore the aggregated-research `$comment` hooks.json fix dropped
  when M-13 was copied to this plan"). Part of the startup-noise cluster (`:916`).
- **Disposition: PLAN**, nothing new: it recurs every session until 23(e) is done. No change beyond a "seen again
  2026-09-28" tick.

### F8 — LOW — graphify never consulted; the graph is stale now (DISMISSED this session; the resume half is RECORDED as S1-3)

- **Evidence.** The PreToolUse:Read hook said "graphify-out/graph.json exists but may be STALE" (main attachment line
  77), and the PreToolUse:Bash "MANDATORY: … run `mise run graphify-query`" hook fired on ~40 Bash calls. The session ran
  **0** `graphify-health`/`graphify-query`/`graphify-check` calls, yet did a source class audit by raw grep (ord 293-319).
  `.claude/rules/graphify-first.md` asks for `mise run graphify-health` first. Probed now: `mise run graphify-health` →
  rc=3 `stale (runtime=0.9.65) graph built at 9f5bd67a but .agents/skills/codex-team-research/SKILL.md changed since
  (HEAD bed7cbb2, 69 corpus file(s))`.
- **Control arm.** The transcript grep `graphify-(query|health|check)` → 0. The same file grepped for `graphify` → 2 hits,
  so the probe can match. `graphify-health` itself returns a classified state (not "missing"), so the check works.
- **Recorded.** Partially: `task_plan.md:735-736` S1-3 ("`session-state` live probes gain `graphify-health`; resume
  prints `stale` …", folds into #1340). Nothing records that the graph is stale at `bed7cbb2`.
- **Disposition: FIX-NOW** (coordinator, at handoff): record "graph stale at bed7cbb2 (69 files); run `mise run
  graphify-rebuild` before the next graph-dependent query" in the handoff's traps, or run the rebuild. No new PLAN line;
  S1-3 covers the class.

### F9 — LOW — `env -u HK_PKL_BACKEND` ritual on 8 mise calls, while S27-2 item 3's done-criterion is already met (STALE plan item)

- **Evidence.** Main ord 516, 592, 615, 855, 900, 933, 1144, 1173 prefix `env -u HK_PKL_BACKEND` on
  `mise run fmt|lint|land|ship`. `task_plan.md:999-1000` (S27-2 item 3) says this item is done "when a fresh session's
  `[ -n "$HK_PKL_BACKEND" ] && echo SET || echo ABSENT` → ABSENT". The session never ran that probe.
- **Probe (this lane, same Claude Code process env as the main session).** `[ -n "$HK_PKL_BACKEND" ]` → **ABSENT**.
  Control: `[ -n "$HOME" ]` → SET. Caveat: this covers the Claude Code environment only. Ray's other open terminals are
  not probed.
- **Disposition: FIX-NOW.** Mark S27-2 item 3 "DONE 2026-09-28 for the Claude Code env (probe ABSENT, control HOME=SET,
  session 52723a40); Ray to confirm his interactive terminals", and drop the `env -u` prefix from session practice. It
  was also a no-op by construction for any mise-injected copy (memory `feedback_mise_reinjects_user_global_env`).

### F10 — LOW — Brief-mode reply missed twice: the turn ended with plain text instead of SendUserMessage (UNRECORDED, repeated)

- **Evidence.** Main ord 735 and ord 1362: the harness re-prompted "You ended the turn without calling SendUserMessage".
  Both times the preceding turn ended with an `ASST` status line after background work was launched (ord 734, 1361).
- **Control arm.** `grep -c "without calling SendUserMessage"` over the main extract → 2. The same extract contains 20
  delivered `SendUserMessage` calls (e.g. ord 739, 1366), so the grep sees the surrounding turns and only 2 were missed.
- **Disposition: PLAN-lite** (no ticket): one line in the session memory's lessons ("brief mode: every turn that
  launches or collects background work ends with SendUserMessage, not a status line; missed 2× on 2026-09-28"). Harness
  behaviour, so there is nothing to build in the repo.

### F11 — LOW — Another agent's worktree left detached (UNRECORDED residue)

- **Evidence.** Main ord 524 ran `git -C …/dotfiles.worktrees/research-five-source-gate checkout -q --detach` (Ray-ruled,
  ord 422) to free `main` for `land`. Now: `## HEAD (no branch)` at `2d763acb` (`git worktree list` → `(detached HEAD)`).
  Its branch `codex/research-five-source-gate` shipped as #1409 (MERGED).
- **Recorded?** Only as a generic how-to in memory `project_session_2026-09-28.md` ("`git -C <wt> checkout --detach` …
  frees it"). `task_plan.md`, `findings.md` and `progress.md` have 0 hits for `research-five-source-gate`. Nothing says
  the worktree is still parked, or who removes it.
- **Control arm.** `grep -c research-five-source-gate task_plan.md findings.md progress.md` → 0/0/0. The same grep for
  `detach` in findings.md → 2, so the files are searchable.
- **Disposition: PLAN** (fold into S27-5, the stale-worktree item):
  > S27-5 add: `dotfiles.worktrees/research-five-source-gate` is detached at `2d763acb` since 2026-09-27 (freed `main` for
  > `land -- 1411`); its work shipped as #1409. Owner Ray: `git worktree remove` it, or reattach. The next `land` will
  > hit the same block from any worktree holding `main`.

### F12 — LOW — pwf plan injection is now 25.3-25.4 KB and arrives as a 2 KB preview on every prompt; the Stop hook nags 12× (RECORDED S27-13; the measurement has grown)

- **Evidence.** 15 UserPromptSubmit/SessionStart `hook_additional_context` rows, each "Output too large (25.4KB). Full
  output saved to … Preview (first 2KB)" (main attachment lines 8, 45, 290, …, 1196). The Stop hook "[planning-with-files]
  Task in progress (2/19 phases complete). Update progress.md before stopping" fired 12× (lines 283 … 1182).
  `progress.md` was appended once, at ord 1131.
- **Recorded.** `task_plan.md:1034-1035` (S27-13: "exceeds the 10,000-char hook cap (42/65 injections were 19.4-19.9 KB;
  Current Phase never reached the model) — fix inside #1360/D9").
- **Why it matters here.** F0's ruling text (`task_plan.md:420`, `:652`) is not in the injection at all: 0 hits for
  `PLANNING_DISABLED|round 5` in the full 26,186-byte injection file (`tool-results/hook-5c1c20eb-…-additionalContext.txt`)
  and 0 in its 2 KB preview. Control: the preview contains `planning-with-files` twice, so the grep reads it. It was
  also outside every range the session read by hand, so no route carried the ruling to the model. Shrinking the
  injection (S27-13) alone won't fix this; a rule-bearing plan needs the ruling next to the code it governs (#1357's
  contract).
- **Control arm.** All 15 sizes were parsed from the attachment text (`re 'Output too large \(([\d.]+KB)\)'`), with no
  inline (un-persisted) injection among them. The regex does match: 15 of 15.
- **Disposition: PLAN.** Append to S27-13: "2026-09-28: 25.3-25.4 KB ×15, persisted with a 2 KB preview; the Stop-hook
  'x/19 phases' nag fired 12× on a plan whose phases are mostly archived. Both fold into #1360/D9."


## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): read `task_plan.md`, `agentsview_pass.py`,
  `bounded_wait.py`, `pr.py`, `mise.toml`, reports; `gh issue view 1351` comments; `gh pr view 1409`; issue search for
  `PLANNING_DISABLED` / "see the plan" (#1357, #1115).
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): read the offline Claude Code docs
  (`sources/agent-harness-docs/docs/claude-code/code-review.md:329`, `tools-reference.md:46`) for ReportFindings.
