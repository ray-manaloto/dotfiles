# Session-integrity (vagueness) audit — 2026-09-28

Brief P (reused from `docs/research/kb/reports/agents/session-2026-09-23d-agent-briefs.md:298`).
Scope: this session's commits `6c9576f0` (#1412) and `bed7cbb2` (#1417), plus `task_plan.md` and docs describing sdlc-team's codex launch.
Lane: read-only except this report. Status: COMPLETE (20 findings: 6 FIX-NOW, 14 PLAN).

## Findings

### F1 — `docs/receipts/1319.md:8` and `:15` are future-tense and now stale (STALE) — FIX-NOW

- `:8` "The #1293 map comment and the #1319/#1310 closes follow the land."
- `:15` "**Resolved:** arms complete 2026-09-27 (closes on land of the #1362 PR)" — also leaves "the #1362 PR" unnamed (it is #1412).
- Probe: `gh issue view 1319 --json state,closedAt` → `CLOSED 2026-09-28T05:22:54Z`; #1310 → `CLOSED 2026-09-28T05:30:50Z`; #1293 comments after 2026-09-27 → one, `2026-09-28T05:30:51Z` "**Phase 10 step 0 is complete** …". Control arm: the same query on #1383 → `OPEN`, and on #1293 → `OPEN`, so the probe discriminates open from closed.
- `git log -- docs/receipts/1319.md` → last touched by `6c9576f0` (#1412); `bed7cbb2` (#1417, which did the closes) did not update it.
- Rewrite `:8` last sentence → "The #1293 map comment was posted and #1319/#1310 were closed on 2026-09-28, after #1412 landed."
- Rewrite `:15` → "**Resolved:** 2026-09-28 — all arms complete 2026-09-27; #1319 closed after #1412 (the #1362 fix) landed."

### F2 — `task_plan.md:1047` Active order still marks the fable remainder ACTIVE (CONTRADICTION) — PLAN

- Text: "**Active order (Ray, 2026-09-25):** § "2026-09-25 step 0" (DONE 2026-09-25) → the fable-orchestrator remainder (ACTIVE) → § "2026-09-24/25 session remainder" → Phase 11."
- Contradicts `task_plan.md:775` (heading "… — DONE 2026-09-28"), `:814` (remainder heading "ACTIVE, NEXT SESSION (fable remainder DONE 2026-09-28)"), `:1084` (item 2 "DONE 2026-09-28") and `docs/agents/plan-pointer.json` `active_phase` = "2026-09-24/25 session remainder — ACTIVE …". A fresh session reading Current Phase top-down meets `:1047` before `:1084` and has two ACTIVE phases.
- Control: `grep -n "fable-orchestrator remainder (ACTIVE)" task_plan.md` → exactly 1 hit (`:1047`); `grep -n "fable remainder DONE 2026-09-28"` → 1 hit (`:814`), so both spellings are live and the probe distinguishes them.
- PLAN (exact task_plan text, replace `:1047` line start): `**Active order (Ray, 2026-09-25):** § "2026-09-25 step 0" (DONE 2026-09-25) → the fable-orchestrator remainder (DONE 2026-09-28) → § "2026-09-24/25 session remainder" (ACTIVE) → Phase 11.`

### F3 — `task_plan.md:1057-1059` "only #1319 (live arms) remains" (STALE) — PLAN

- Text: "Phase 10 step 0 (#1310) EXECUTED EARLY on 2026-09-24 …: #1311-#1317 landed in dotfiles#1363, #1318 done on this Mac; only #1319 (live arms) remains, carried by § "fable-orchestrator removal". The REST of Phase 10 resumes after Phase 11."
- Probe: #1319 `CLOSED 2026-09-28T05:22:54Z`, #1310 `CLOSED 2026-09-28T05:30:50Z` (control #1383 → OPEN).
- PLAN rewrite: `Phase 10 step 0 (#1310) EXECUTED EARLY on 2026-09-24 and CLOSED 2026-09-28: #1311-#1317 landed in dotfiles#1363, #1318 done on this Mac, #1319's live arms completed in #1412; KB #793-#797 closed. The REST of Phase 10 resumes after Phase 11.`

### F4 — `task_plan.md:777` "ACTIVE since 2026-09-25b" under a DONE heading (CONTRADICTION) — PLAN

- `:775` heading says "DONE 2026-09-28"; the first body line `:777` says "ACTIVE since 2026-09-25b (step 0 DONE). The order is the "Status" block …".
- PLAN rewrite `:777` first sentence: `Was ACTIVE 2026-09-25b → 2026-09-28 (step 0 DONE); now DONE, kept as the record of its rulings.`
- Same section, `:799` "Keep #1310 open until #1319 closes." → `#1310 closed 2026-09-28, after #1319.` (condition satisfied; as written it reads like a standing instruction.)

### F5 — `task_plan.md:514` Phase 11 heading still "QUEUED behind the fable-orchestrator remainder" (STALE) — PLAN

- Text: "## Phase 11 — QUEUED behind the fable-orchestrator remainder and the 2026-09-24/25 session remainder (step 0 DONE 2026-09-25) …".
- The parenthetical "(step 0 DONE 2026-09-25)" is also ambiguous: it is the § "2026-09-25 step 0" (/doctor + /claude-api), NOT Phase 10 step 0 (#1310, done 2026-09-28). Two different "step 0"s share a name inside one heading.
- PLAN rewrite: `## Phase 11 — QUEUED behind the 2026-09-24/25 session remainder (the fable-orchestrator remainder DONE 2026-09-28; the "2026-09-25 step 0" /doctor + /claude-api section DONE 2026-09-25) (ruled by Ray 2026-09-23 / 2026-09-25): …` (rest unchanged).
- Also `:495` Phase 10 Order item "0. fable-orchestrator removal (addendum above) — before anything that triggers codex work or agents." → prefix `DONE 2026-09-28 (#1310 closed): `.

### F6 — `task_plan.md:910` item 25 "#1383 … blocked on #1362" (STALE blocker) — PLAN

- Probe: #1362 `CLOSED 2026-09-28T04:59:29Z` (control #1383 → OPEN).
- PLAN rewrite: `25. V8 follow-ups (filed 2026-09-25, not yet ordered): #1383 (sdlc_team → `kb_setup`) — #1362 fixed in #1412 (2026-09-28); still blocked on #1295's placement; order it with Phase 11's codex class fix. …` (rest unchanged).
- Note for the #1383 implementer: the moved entry point must carry `_codex_launcher` (`mise exec -- codex exec`, `absolute()` not `resolve()`) and the `LANE_ENV_OVERRIDES` env merge, or #1362 regresses in `kb_setup`. Suggest appending that sentence to item 25.

### F7 — `task_plan.md:752-762` Brief U "OPEN DECISION for Ray" + "BUG to file first" (STALE, pre-session but #1362-bearing) — PLAN

- Text still reads "**OPEN DECISION for Ray (AskUserQuestion first thing):** A (recommended) … B …" and "a **BUG to file first**: `sdlc_team.py:724,781` resolves codex via `Path(shutil.which("codex")).resolve()` …".
- Resolved: `task_plan.md:1062` ("This resolves Brief U's open A/B decision as **B, and more**"), `:1076` ("Filed dotfiles#1362"), #1362 closed by #1412. The cited lines `sdlc_team.py:724,781` no longer hold that code: `grep -n 'which(\|resolve()' python/src/dotfiles_setup/sdlc_team.py` → `which("codex")` now appears only at `:695` (docstring) and `:705` (presence check), and the launcher returns `Path(mise).absolute()` (`:710`); the remaining `resolve()` hits (`:209,218,268,272,648,819,895,1065,1085`) resolve repo/spec paths, not the codex binary. Control: the same grep finds `which("mise")` at `:702`.
- A fresh session obeying "AskUserQuestion first thing" would re-ask a settled question.
- PLAN: prefix the bullet at `:752` with `RESOLVED 2026-09-24 (B, see "SUPERSEDED 2026-09-24" under Current Phase); the BUG was filed as #1362 and fixed in #1412 (2026-09-28). Kept as the record:` and change "OPEN DECISION for Ray (AskUserQuestion first thing)" → "Decision (was open)".

### F8 — `task_plan.md:848-850` item 11 Q7 "fold into the #1319 `kb-tool-review` live run" (DEAD instruction) — PLAN

- That live run already happened (`wf_9a05aaf2-5f5`, 2026-09-26, receipt `docs/receipts/1319.md:31`), so "fold into" has no future vehicle.
- Probe (knowledge-base origin/main): `git grep -n -E "laneRoot|method\.txt" origin/main -- .claude/workflows/kb-tool-review.js` → `laneRoot` at `:57-60` (per-run override exists, `cfg.laneRoot`, introduced by `330b03e6`/#811); `git grep -n -F "method.txt"` over `.claude/workflows/` → 0 hits, rc=1. Control: the same `git grep` shape finds `laneRoot` (3 lines) and `agentType` (4), so the 0 for `method.txt` is real.
- PLAN rewrite of the Q7 clause: `**Q7:** `kb-tool-review.js` per-run `laneRoot` — DONE in KB#811 (`cfg.laneRoot`, `kb-tool-review.js:57-60`). Still owed: an explicit `method.txt` per lane (0 hits on KB origin/main 2026-09-28) — ship in the next KB PR touching kb-tool-review.js, or drop with Ray's ruling.`

### F9 — `python/src/dotfiles_setup/sdlc_team.py:698-700` `_codex_launcher` docstring misstates HOW codex is resolved (IMPRECISE) — FIX-NOW (next sdlc_team touch)

- Docstring: "`mise exec -- codex exec`, which resolves the host's native codex from the current config rather than whatever the supervisor's inherited PATH happens to list first."
- Probe (2026-09-28, dotfiles root): `mise which codex` → rc=1 "codex is a mise bin however it is not currently active" (the config does NOT provide codex; `mise.toml:169` `disable_tools = ["npm:@openai/codex"]`). Control: `mise which hk` → rc=0, `…/installs/hk/2.3.0/.mise-bins/hk`, so the probe can report an active tool. `mise exec -- sh -c 'command -v codex'` → still the shim `~/.local/share/mise/shims/codex`, and `codex --version` → `codex-cli 0.158.0`, identical to `~/.local/bin/codex --version` → `0.158.0`. So under `mise exec` the shim falls through to the native binary found on the INHERITED PATH; the config's role is only to disable the npm pin.
- What the fix actually guarantees is narrower and still correct: argv[0] is the `mise` binary invoked AS `mise exec -- codex`, never `mise` invoked with codex's flags.
- Exact rewrite of `:698-700`: "``.claude/rules/ai-cli-invocation.md`` mandates ``mise exec -- codex exec``: mise applies the workdir's config (which disables the npm codex pin, ``mise.toml`` ``disable_tools``), and the codex shim then falls through to the host's native install on PATH. The ``--`` keeps mise from reading codex's flags as its own."
- Side note, not a defect: codex auto-updated 0.157.1 (receipt/report, 2026-09-27) → 0.158.0 (now). The receipt row records 0.157.1 as the version AT the arm, which is correct as a dated record.

### F10 — `.claude/skills/codex-sdlc-team/SKILL.md:73` (+ mirror `.agents/skills/codex-sdlc-team/SKILL.md:73`) `cli_missing` wording now wrong (STALE) — FIX-NOW

- Text: "- `cli_missing` — Codex was unavailable and no lane launched."
- Since #1412, `dispatch()` returns CLI_MISSING when EITHER `mise` or `codex` is absent (`sdlc_team.py:705` `if mise is None or shutil.which("codex") is None`), and the error reads "`mise` and `codex` must both be on PATH to launch codex". A reader diagnosing `cli_missing` on a host with codex present would look in the wrong place.
- Control: `grep -rn "cli_missing\|CLI_MISSING" docs/specs .claude/rules .claude/skills .agents` → exactly these two lines, so no other doc describes the status.
- Exact rewrite (both files; the mirror is generated — run `mise run skills-mirror` after editing the source rather than hand-editing `.agents/`): "- `cli_missing` — `mise` or `codex` was not on PATH (the launcher is `mise exec -- codex exec`), and no lane launched."

### F11 — `.claude/rules/ai-cli-invocation.md:10-12, :38, :43` do not say which launchers now follow the canonical form (INCOMPLETE; rule-synced) — PLAN

- `:7` mandates "Invoke every AI CLI through `mise exec --`". `:38` names only one deviation: "Still in code, tracked by the Phase 11 codex class fix: `codex_lane.py` passes it [--ephemeral]." `:43` "Until the class fix, the 12 codex wrappers still carry their own (sonnet, background launch, `$LOG.rc` completion file)".
- Measured 2026-09-28: 12 wrappers (`ls .claude/agents/codex-*.md | wc -l` → 12) and all 12 contain `mise exec -- codex` (`grep -l` → 12, `grep -L` → none); `sdlc_team.py` now launches `mise exec -- codex exec` (#1412). `codex_lane.py:112` `CODEX_BIN = "codex"` and `:379-382` argv `[CODEX_BIN, "exec", "--ephemeral", …]` — so `codex_lane.py` is now the ONLY one of the three launchers not under `mise exec --`, a second deviation the rule does not record. Control: the same `grep -n -- "--ephemeral"` finds `codex_lane.py:382`, confirming the rule's one stated deviation is still true.
- Also `codex_lane.py:457-459` error text "it is pinned host-only in mise.toml" is stale: `mise.toml:169` `disable_tools = ["npm:@openai/codex"]` — codex is NOT pinned on the host (see F9 probe `mise which codex` rc=1).
- PLAN (rule-synced: `rule-sync.toml:59` lists `ai-cli-invocation`, so the same bytes must land in knowledge-base in the paired PR): replace `:38` last sentence with `Still in code, tracked by the Phase 11 codex class fix: `codex_lane.py` passes it, and is also the one launcher still running a bare `codex` instead of `mise exec -- codex` (`sdlc-team` moved in #1412; the 12 wrappers in 86324c6a).` Fold the `codex_lane.py:457-459` message fix into the same class-fix ticket. Exact task_plan line, under Phase 11 item 3 (codex-invocation class fix): `   Scope includes: `codex_lane.py` bare `CODEX_BIN` + `--ephemeral` → `mise exec -- codex exec` (audit 2026-09-28 F11); its "pinned host-only in mise.toml" error text is stale (disable_tools).`

### F12 — `.claude/rules/ai-cli-invocation.md:46` "the host now runs native 0.156.x" (STALE version) — PLAN (rule-synced)

- Probe: `~/.local/bin/codex --version` → `codex-cli 0.158.0`; `mise exec -- codex --version` → `0.158.0` (2026-09-28). Receipt row (2026-09-27) recorded `v0.157.1`, so it auto-updated twice in three days; any fixed minor in the rule will rot.
- Rewrite heading: `## Codex facts (probed at 0.152.1; the host runs the self-updating native install — re-probe with `mise exec -- codex --version` before relying)`. Ship with F11 in the rule-sync pair.

### F13 — code-review report claims `codex_pid` is now the mise pid (UNVERIFIED claim in a verbatim report) — FIX-NOW (coordinator annotation, not an edit of the verbatim text)

- `docs/research/kb/reports/agents/code-review-1362-2026-09-27.md:11`: "`codex_pid` is only recorded in the settlement … so it now being the mise pid is harmless."
- Probe: `subprocess.Popen([mise, "exec", "--", "sh", "-c", "echo $$"])` → Popen pid 41197, child `$$` 41197 (SAME) — `mise exec` replaces its own process image. Control: `sh -c "sh -c 'echo $$'; true"` → 41360 vs 41361 (DIFFERENT), so the probe can detect a fork. The shim hop (`codex` shim → native) was not separately measured.
- The SKILL (`.claude/skills/codex-sdlc-team/SKILL.md:92` "Codex child `codex_pid`") therefore stays accurate; the report's parenthetical is the inaccurate side. Append under the report (per `agent-report-persistence.md` rule 4, annotate, do not trim): `> Coordinator annotation 2026-09-28: measured, `mise exec` execs in place (Popen pid == child $$; forked control differs), so `codex_pid` is the pid the exec chain hands to codex, not a lingering mise parent. The shim hop was not separately measured.`

### F14 — `docs/receipts/1319.md:64` + `session-audit-missing-requests-2026-09-25.md:186-187`: fable-removal backups were to be deleted "until #1319 closes" — trigger MET, no owner, no plan line (UNOWNED NEXT STEP) — PLAN

- Condition: #1319 CLOSED 2026-09-28T05:22:54Z.
- Presence (sizes only, never content — `secrets-out-of-the-shell-env.md` rule 8): `ls -la` → `.agent/state/fable-orchestrator-1.21.0-cache-backup-2026-09-24.tgz` 416702 B; `~/.codex/config.toml.pre-fable-removal-2026-09-24` 24990 B, mode 0600. Both still present.
- Tracking: `grep -c -i backup task_plan.md` → 0. Control: `grep -c -i attestation task_plan.md` → 12, so the grep reads the file. Only `.agent/plans/session-2026-09-24.md` (gitignored handoff) mentions them.
- Owner split: the `.agent/state/` tarball is repo-local (agent may delete); `~/.codex/…` is user-level — Ray only (`feedback_no_user_level_file_updates`), and it may hold MCP credentials, so it is the more important deletion.
- PLAN, exact task_plan line (append to § 2026-09-24/25 session remainder as item 30): `30. (audit 2026-09-28 F14) #1319 closed 2026-09-28, so the fable-removal backups are due for deletion: agent deletes `.agent/state/fable-orchestrator-1.21.0-cache-backup-2026-09-24.tgz`; Ray (user-level, never agent-applied) deletes `~/.codex/config.toml.pre-fable-removal-2026-09-24` (0600, may hold MCP config). Done when `ls` of both → "No such file".`

### F15 — `docs/agents/goal-history.md:1791` "The main-holding worktree's HEAD is detached." (UNDEFINED TERM, unstated owner) — PLAN

- The phrase occurs once in the repo (`git grep -n -i "main-holding"` → only `goal-history.md:1791`; control: the same `git grep` for `kb-codex-implementer` finds many files). It names no path and no reason.
- Measured: `git worktree list` → `…/dotfiles.worktrees/research-five-source-gate 2d763acb (detached HEAD)`; its reflog `HEAD@{0}: checkout: moving from main to HEAD`. That worktree belongs to ANOTHER agent's work (#1409 / #1415, branch family `codex/agent-team-research-skill`), so the ruling mutated a second writer's checkout — the kind of cross-writer handoff `.claude/rules/goal-history.md` says to record ("Record every ownership handoff").
- `task_plan.md` does not mention it: `grep -n "research-five-source-gate\|1409" task_plan.md` → nothing; control `grep -c -i attestation task_plan.md` → 12.
- goal-history is append-only, so no rewrite of `:1791`. PLAN: the next iteration (041) carries, under **Topology and ownership**: `The worktree `dotfiles.worktrees/research-five-source-gate` (owner: the #1409/#1415 research-skill session) had `main` checked out; Ray ruled (2026-09-27, /grilling) to detach its HEAD at `2d763acb` so the primary checkout could take `main` for `land`. Its owner re-attaches with `git -C <path> switch <branch>`; no commits were lost (HEAD unchanged).` And one task_plan line under Current Phase owed items: `- (S28-1) `dotfiles.worktrees/research-five-source-gate` is on a detached HEAD at `2d763acb` by Ray's 2026-09-27 ruling (goal-history 040); tell its owning session before it resumes.`

### F16 — goal text "including items 24-26" while items 27-29 exist (AMBIGUOUS SCOPE) — PLAN

- `docs/agents/goal-history.md:1811` (040) and `:1769` (039): "Finish the 2026-09-24/25 session remainder in task_plan.md (including items 24-26 and filed #1386/#1387/#1388) …". `task_plan.md` § remainder runs to item 29 (items 27/28/29 at `:918`/`:924`/`:927`, all from 2026-09-26 audits — `grep -n "^2[4-9]\. " task_plan.md`; control: the same grep finds 24/25/26 at `:903`/`:910`/`:914`). Singling out 24-26 invites the reading that 27-29 are out of scope, although they predate 039.
- Append-only: fix in iteration 041's goal text: `Finish the 2026-09-24/25 session remainder in task_plan.md (every open item, 1-29 plus any appended, and filed #1386/#1387/#1388) and the 2026-09-27 owed items S27-1..17 …` (rest unchanged).

### F17 — `kb-1310-children-verification-2026-09-28.md:3` and `:70` read "all four issues state=OPEN … 0 comments" with no closing annotation (POINT-IN-TIME, now false) — FIX-NOW (coordinator annotation)

- Probe: KB #793/#795/#796/#797 → `CLOSED` 2026-09-28T05:30:11Z / 05:30:48Z / 05:30:12Z / 05:30:14Z, `comments=1` each. Control: KB#823 → `OPEN`, KB#824 → `OPEN comments=0`, so the query reports open and zero-comment states when true.
- The report also says "Proposed close comment" four times, but never records which text was actually posted (KB#795 in particular had an "Alternative: leave it open").
- Per `agent-report-persistence.md` rule 4, do not edit the verbatim body; append: `## Coordinator disposition (2026-09-28)` / `- KB#793, #796, #797 closed 05:30Z with the proposed comments; KB#795 closed 05:30:48Z as delivered-with-waiver (Ray, 2026-09-28), not left for #1383. Each issue now has 1 comment. The report's "state=OPEN"/"0 comments" lines are as of its fetch, before the closes.` (Adjust "with the proposed comments" if the posted text differed — `gh issue view <n> -R ray-manaloto/knowledge-base --comments` decides.)

### F18 — `cold-lens-1362-2026-09-27.md:11` "on 78bb5e07 (same tree as 3340a939 pre-rebase)" (FALSE + ambiguous) — FIX-NOW (coordinator-authored note, editable)

- Probe: `git rev-parse 78bb5e07^{tree}` → `fd4e9eb7…`; `3340a939^{tree}` → `90a59832…` — different trees. `78bb5e07`'s parent is `2d763acb` (#1409); `3340a939`'s is `d453020f` (#1411), and `2d763acb` is an ancestor of `d453020f` (`merge-base --is-ancestor` rc=0; reverse rc=1). `git diff --stat 78bb5e07 3340a939 -- python tests` → 6 files outside the #1362 diff (`lock_integrity.py`, `lock_shared.py`, `pr.py`, `test_hk_hooks.py`, `test_pr.py`, `test_workflow_hooks.py`). Control: `git diff --stat 2d763acb 78bb5e07 -- python tests` → 2 files (only the #1362 change), so the diff probe isolates the change.
- "pre-rebase" can attach to either SHA. 78bb5e07 is the pre-rebase commit; 3340a939 is the rebase.
- Exact rewrite: `The lens could not run tests (read-only sandbox blocks uv cache). The coordinator ran them on 78bb5e07 — the same #1362 change BEFORE the rebase, on base 2d763acb (#1409): full suite 3,982 passed / 0 failed. 3340a939 is that change rebased onto d453020f (#1411); its tree differs in 6 python/tests files outside this diff, so the post-rebase suite evidence is `mise run ship`'s gate run for #1412 [cite its log rc, or state "not recorded"].`

### F19 — SKILL cold-lens command vs the command actually run: `< /dev/null` (DOC/PRACTICE DIVERGENCE, unmeasured) — PLAN

- `.claude/skills/codex-sdlc-team/SKILL.md:185`: `mise exec -- codex exec -s read-only --ignore-rules review --commit <SHA> -c 'sandbox_mode="read-only"'` — no stdin redirect. The run recorded in `cold-lens-1362-2026-09-27.md:3` appended `< /dev/null`. `.claude/rules/ai-cli-invocation.md` ("With no prompt, or with `-`, instructions come from stdin") plus S27-16 (`task_plan.md` "Stdin hangs: … `claude -p` waited on inherited stdin") make an inherited-stdin wait plausible for `exec review` from a non-TTY harness shell, but no arm has been run for `exec review` specifically — this audit did not run one (it would launch a codex review).
- PLAN, extend S27-16's exact text: `- (S27-16) Stdin hangs: `hk run pre-push --plan` and `claude -p` waited on inherited stdin; add `< /dev/null` to #1405's spec and one sentence to remainder item 13 / #1056 (dismissed-errors F7). Also measure `codex exec review` with and without `< /dev/null` from a non-TTY shell (audit 2026-09-28 F19); if the no-redirect arm waits, add `< /dev/null` to `.claude/skills/codex-sdlc-team/SKILL.md:185`.`
- Related, still accurate: "pending #1297's write-canary" — #1297 `OPEN`; "`exec review` ignores it (#1296)" — #1296 `CLOSED` (a mapping issue; its closure does not change the fact).

### F20 — Are the S27-1..17 owed items before Phase 11 or not? (CONTRADICTION between plan and goal) — PLAN

- `task_plan.md:989` labels the 2026-09-26/27 session "OUTSIDE the active order; the active order is UNCHANGED", and `:1089` reads "3. NEXT (ACTIVE): the 2026-09-24/25 session remainder, then Phase 11 as ordered above." — S27-1..17 are not in the ordered path.
- The accepted goal (`docs/agents/goal-history.md:1811`, iteration 040, and 039 at `:1769`) says "Finish the 2026-09-24/25 session remainder … and the 2026-09-27 owed items S27-1..17 …. Then Phase 11". Two authorities disagree on whether S27 items gate Phase 11, and the goal names `task_plan.md` "the sole task authority".
- Control: `grep -n "S27-1\.\.17" task_plan.md` → 0 lines in `task_plan.md` (the range spelling lives only in goal-history); the S27 entries themselves exist (`grep -c "^- (S27-" task_plan.md` → 17).
- PLAN, exact rewrite of `:1089`: `3. NEXT (ACTIVE): the 2026-09-24/25 session remainder and the owed items S27-1..17 (goal-history 039/040; the "OUTSIDE the active order" label on `:989` describes that session's shipped work, not these owed items), then Phase 11 as ordered above.` If Ray intends S27 items to float, the NEXT goal iteration must drop them from the goal instead — one AskUserQuestion decides.

## Checked and clean (with the arm that could have failed)

- `docs/agents/plan-pointer.json` `plan_sha256` `7551fd7b…` == `shasum -a 256 task_plan.md` == `mise run plan-attest -- --show` SHA (rc=0); `active_phase` string == the `task_plan.md:814` heading text. A pointer written before a later plan edit would have differed.
- `task_plan.md:73` pointer line, `:775` heading, `:814` heading, `:1084-1088` item 2: mutually consistent (DONE / ACTIVE agree). Only `:514`, `:777`, `:799`, `:910`, `:1047`, `:1057-1059` lag (F2-F6).
- `docs/receipts/1319.md` row anchors cited by the KB verification report (`:23,24,26,30,31,33`) point at the rows they describe (checked line by line: `:31` kb-tool-review, `:33` kb-codex-implementer).
- `_supervise` env comment (`sdlc_team.py:990-992`) matches code (`:996` `env={**os.environ, **codex_lane.LANE_ENV_OVERRIDES}`) and `codex_lane.py:135` `LANE_ENV_OVERRIDES = {"PLANNING_DISABLED": "1"}`; test `:584` seeds `PLANNING_DISABLED=0`. Its "every other codex lane" claim holds: `grep -l "PLANNING_DISABLED=1" .claude/agents/codex-*.md` → 12 of 12 (`grep -L` → none, rc=1).
- `_codex_launcher` inline comments (`:703-709`) match code; the shim-layout claim in `tests/test_sdlc_team.py:385-386` is real on this Mac: `~/.local/share/mise/shims/codex -> ~/.local/bin/mise` (control: `shims/hk` points at the same binary).
- `.claude/rules/codex-sdlc-team.md` and `docs/specs/codex-sdlc-subagent-team.md` say nothing about HOW codex is resolved (no `which`/`resolve`/`mise exec` statement to go stale; `grep -n -i "which\|resolve\|mise exec"` hits only unrelated prose and struck-through historical `codex exec --ephemeral` blocks). No doc outside reports/tests/code still says sdlc-team resolves `which("codex")` (`git grep -n 'which("codex")'` → only `sdlc_team.py:695` docstring and `:705` presence check; control `which("mise")` → `:702`).
- No non-report doc claims #1362/#1319/#1310 are open except `docs/receipts/1319.md:8,15` (F1) and the task_plan lines in F3/F6/F7. `docs/receipts/1319.md:64` ("#1319 OPEN; sdlc-team arm waits on #1362") is inside the receipt's "Sources — what I actually opened" table, i.e. a dated record of what that source said — correct as written; its unowned consequence is F14.

## Disposition summary

| # | File:line | Class | Disposition |
|---|---|---|---|
| F1 | `docs/receipts/1319.md:8,15` | stale future tense | FIX-NOW |
| F2 | `task_plan.md:1047` | contradiction (two ACTIVE) | PLAN |
| F3 | `task_plan.md:1057-1059` | stale | PLAN |
| F4 | `task_plan.md:777,799` | contradiction / satisfied condition | PLAN |
| F5 | `task_plan.md:514,495` | stale + two "step 0"s | PLAN |
| F6 | `task_plan.md:910` | stale blocker | PLAN |
| F7 | `task_plan.md:752-762` | resolved decision still OPEN | PLAN |
| F8 | `task_plan.md:848-850` | dead instruction | PLAN |
| F9 | `sdlc_team.py:698-700` | imprecise docstring | FIX-NOW |
| F10 | `SKILL.md:73` (+ `.agents` mirror) | stale status meaning | FIX-NOW |
| F11 | `ai-cli-invocation.md:38` (+ `codex_lane.py:457-459`) | incomplete deviation list | PLAN (rule-synced) |
| F12 | `ai-cli-invocation.md:46` | stale version | PLAN (rule-synced) |
| F13 | `code-review-1362-2026-09-27.md:11` | unverified claim | FIX-NOW (annotation) |
| F14 | backups (receipt `:64`) | unowned due step | PLAN |
| F15 | `goal-history.md:1791` | undefined term, cross-writer side effect | PLAN (iteration 041) |
| F16 | `goal-history.md:1811` | ambiguous scope | PLAN (iteration 041) |
| F17 | `kb-1310-children-verification-2026-09-28.md:3,70` | point-in-time, no disposition | FIX-NOW (annotation) |
| F18 | `cold-lens-1362-2026-09-27.md:11` | false "same tree" | FIX-NOW |
| F19 | `SKILL.md:185` vs practice | divergence, unmeasured | PLAN |
| F20 | `task_plan.md:1089` vs goal 040 | contradiction | PLAN |

FIX-NOW count: F1, F9, F10, F13, F17, F18 = 7 files in dotfiles (F10 is two: the source plus its `mise run skills-mirror` output); none rule-synced. F11/F12 need the knowledge-base pair PR.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issues #1293, #1296, #1297, #1310, #1319, #1362, #1383, #1405, #1056 (state/comment reads); commits `6c9576f0`, `bed7cbb2`, `78bb5e07`, `3340a939`, `2d763acb`, `d453020f`
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — issues #793-#797, #823, #824 (state/comment counts); `origin/main:.claude/workflows/kb-tool-review.js` (laneRoot/method.txt probe)
