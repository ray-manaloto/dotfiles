<!-- verbatim final report of Explore agent aff3e0915e824d27a (coordinator 5a11da), 2026-10-04 -->

# Audit: c769e1a1 transcript vs handoff 04g (and 04f)

This lane was read-only, so I wrote nothing and **the coordinator has to persist this report**. In the evidence below, "L" means a line of the transcript `/Users/rmanaloto/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles--claude-worktrees-handoff-2026-10-04g/c769e1a1-f655-4771-b94f-a07abe6cf541.jsonl`. It now has 832 lines and was still growing after the handoff was written. I also read the job files under `/Users/rmanaloto/.claude/jobs/c769e1a1/tmp/` and checked live `git`/`gh` state.

## 1. LOST (in the transcript, missing from the 04g handoff)

1. **Ray gave a new instruction after the handoff, and nobody acted on it.**
   - L830 (17:07:12Z) is a human turn (`origin.kind: "human"`, `humanTurn: true`). Ray pasted a side agent's note: the coordinator handed off after about 15 minutes because the takeover routine used up most of the 30% budget; handoffs may loop with little progress; consider raising the handoff limit or trimming per-turn injection.
   - He ended it with: **"/codex-sdlc-team skill team to review and fix"**.
   - L829 shows it removed from the queue at 17:07:26Z, right after the ScheduleWakeup stop (L827-828). There is no assistant response after it.
   - The successor owes a `/codex-sdlc-team` review and fix of the handoff-churn problem: `DOTFILES_COORDINATOR_HANDOFF_PCT`, the takeover routine, and the per-turn injected context.
2. **Both premise-verifier verdicts are FIX SPEC FIRST, and neither report is persisted.**
   - aed96876ae537f9a5 (jobdir-part2) reported at L737 (17:02:49Z). That was after the handoff Write at L670 (17:01:01Z).
   - a473b047719b4263a (dag-tick-pr1) reported at L789 (17:05:47Z).
   - The handoff still calls both "RUNNING".
   - The coordinator tried to write the jobdir report to `.agent/plans/handoff-inbox/premise-verify-jobdir-part2-2026-10-04g.md` (L755). The worktree-isolation guard refused it (L756).
   - Relays to the successor:
     - L764: jobdir summary, sent OK.
     - L799: dag-tick summary to `dotfiles-20261004T120251.264509000-05.coordinator`. It **FAILED** (L800: `"success":false`).
     - L818: a retry via `uds:/Users/rmanaloto/.local/run/cc-socks/86974.sock`. It succeeded (L819), but carried only a short pointer, not the text.
   - At L804 the successor said it was "persisting" the jobdir relay.
   - A `find` across the main checkout and all worktrees finds neither `premise-verifier-jobdir-part2*` nor `premise-verifier-dag-tick*`.
   - Intended targets: `docs/research/kb/reports/agents/premise-verifier-jobdir-part2.md` and `docs/research/kb/reports/agents/premise-verifier-dag-tick-pr1.md`. Both verbatim texts are in section 4.
3. **The 04g ship was in flight and had not finished at audit time.**
   - It was started at L726 (17:02:22Z): `mise run ship > /Users/rmanaloto/.claude/jobs/c769e1a1/tmp/ship-04g.log`, with an rc line appended. Census pid **21360**; the `mise run ship` child is pid 21361. See `/Users/rmanaloto/.claude/jobs/c769e1a1/tmp/launch.log`, line 19.
   - Local commit: **bfdc3e53** "docs(handoff): 2026-10-04g auto-handoff at 30% context". It is based on 13af2848 (#1666) and contains the handoff file plus `handoff-audit-2026-10-04f.md`.
   - Live check: the log has no `rc=` yet (still in pre-push pytest), `git ls-remote origin docs/handoff-2026-10-04g` is empty, and no PR exists. The ship processes are still alive.
   - The successor said at L804 that it would retire c769e1a1 "after your ship-04g run settles".
   - The handoff's Owed item 7 says only "see below", and there is no "below".
4. **The successor was launched without bgIsolation:none.** Its argv (launch.log line 7) passes only `--settings {"crossSessionInbound":"accept"}`. So successor 120251 cannot Write `task_plan.md` or `.agent/**` in the main checkout either. G5 implies this, but the handoff does not state it for the successor that actually launched.
5. **Successor identity.** It is `dotfiles-20261004T120251.264509000-05.coordinator`: launch rc 0 at L731/L734, name confirmed at L761, socket `cc-socks/86974.sock` (L804). The handoff does not name it, because it was written before launch.
6. **Lane details dropped from the acks.**
   - **kb-ship** (L184):
     - The KB main checkout is on **26a84f7f**.
     - KB queue after "SLOT kb-ship GO": #13 doc PR → fix 1 (manifest-audit) → the kb-admin-merge lane (**Ray-only**), each minted on current main.
     - The lane says "Dotfiles ccf6234c (codex research) is the coordinator's to ship".
   - **model-registry** (L168):
     - Its worktree is `dotfiles.worktrees/model-registry-20261002`. The branch was 4 behind main and merges cleanly; cold reviews show 0 blocking findings.
     - On GO the lane runs: rebase → static → targeted pytest → lint → pytest → verify → lint-docs → rule-sync.
   - **handoff-automation** (L182): "Keep the worktree." The spec branch is `research/session-handoff-automation`; PR1 is `feat/handoff-automation-pr1`, with cold review SHIP.
   - **Lane G** (L186): it asked explicitly that `land -- 1663` not be dropped, and cited `pr.py:1050`. The handoff covers this.
7. **The handoff omits the session-state facts at L630 (state.txt lines 204-244).**
   - Five Renovate PRs have auto-merge armed but are RED: #1492 (python 3.14.8, fail 4), #1449, #1323, #1221 and #1092 (opencode v2, fail 3).
   - At that snapshot #1665 had fail:0 pending:2 pass:23.
8. **Scratch files the handoff never cites.**
   - `/Users/rmanaloto/.claude/jobs/c769e1a1/tmp/coordinator-notes.md` (L454): it records the `land -- 1647` check and a task_plan stale-items list. Mostly carried over.
   - `/Users/rmanaloto/.claude/jobs/c769e1a1/tmp/c1638.md`: the #1638 comment body.
   - `retire-cd95.log`, `retire-2498.log`, `wait-ship04f.log`.
   - A ScheduleWakeup for 12:28 was set (L503) and later cancelled (L827-828).
9. **#1637 evidence.** At L439 the #1637 issue body cites a "third confirming run 4a282b807b17452a9dc31bc5b2280642" (codex 0.160.0). The settlement.json for 292404a1 shows `"status":"failed"` with the errors "parent thread id not found in codex.log banner" and codex_pid 98560. The handoff cites neither, although they support G1.

## 2. INCORRECT

1. **"#1658 PUSHED at 12:06 CDT"** is wrong. The push task finished at 17:00:32Z (L674), which is about 12:00 CDT. The coordinator verified it at L686 (17:01:10Z): `c3569d61...3a486d10 (forced update)`, rc 0, head 3a486d10, auto-merge true. The SHAs and rc are correct; only the time is wrong.
2. **"It auto-handed off at 30% at about 12:05 CDT"** is slightly off. The skill fired at L578 (16:59:23Z, 11:59 CDT). Launch ran at 17:02:29Z and returned at 17:02:54Z (L731/L734), about 12:03 CDT.
3. **"Two premise-verifier runs were RUNNING at handoff … If c769e1a1 is retired before they report, re-run both."** Both runs finished: L737 and L789. A re-run is wasted work. Use section 4 instead.
4. **"Main checkout: on main @ ee3b29da, clean."** It was true at L215 (16:53). But #1666 merged at 16:55:41Z (state.txt:213), so origin/main is now **13af2848**, which the 04g branch was rebased onto at L653-657. The main checkout is one commit behind and needs `git pull --ff-only` before the next ship or land.
5. **"rebased onto origin/main ee3b29da"** for #1658 is correct (L401-412, at 16:55:01Z, before #1666 merged). The consequence is that #1658's base (ee3b29da) is one commit behind main. Live check: mergeStateStatus is BLOCKED with checks pass 17 / pending 1 / skipping 6. It is probably only waiting on the pending check, but if an up-to-date branch is required, auto-merge stalls.
6. **The G1 timing claim checks out against the transcript.** At L443-444, ed8e1a96 is #1664 and d921a3f6 (#1662) is the next commit. At L262, output.md says "Reviewed the whole PR against `ed8e1a96`".

## 3. VAGUE

1. **Owed item 7**, "Ship this branch … if this session's own ship did not complete; see below": no log path, pid or commit is given, and no "below" exists. It should say: log `/Users/rmanaloto/.claude/jobs/c769e1a1/tmp/ship-04g.log`, pid 21360/21361, commit bfdc3e53, worktree `.claude/worktrees/handoff-2026-10-04g`.
2. **Owed item 4**, "Premise-verify results (or re-run)": it does not say where the results are. They are at transcript L737 and L789, and in the subagent JSONLs. It should list the corrections and the persistence targets (section 4).
3. **Owed item 2**, "Lands … `1666`": it does not say a pull is needed first (main is behind at 13af2848).
4. **"All 16 live bg lanes were told"** gives no list. The 16 recipients are at L115-130:
   - saved-searches-1502
   - kb lane-KB2, lane-KB3
   - coordinator-auto-handoff
   - watch
   - kb-20260910.001
   - lane-G
   - session-autostart
   - llvm-23-bump
   - L1-docs-rules
   - ledger native-codex
   - devcontainer-cap-fix
   - kb-20261002.ship
   - model-registry
   - kb-20261003T102535.932032000-05.ship
   - handoff-automation-research
5. **The Gotcha about `for g in …`** is undercut by the handoff's own claim to rules compliance: L416 ran all four gates in one background loop.
6. **"Ray's L406 ruling"** in Owed item 6 refers to a line in the old transcript 2498695d, not this one. Name the transcript.

## 4. Subagent final reports

The subagents/ directory is `/Users/rmanaloto/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles--claude-worktrees-handoff-2026-10-04g/c769e1a1-f655-4771-b94f-a07abe6cf541/subagents/`. It holds agent-a473b047719b4263a.jsonl (311 lines), agent-aed96876ae537f9a5.jsonl (250 lines), agent-a860558329f4aeab8.jsonl (62 lines; the 04f audit), and their meta.json files.

**The "LAST non-blank assistant text block", taken literally:**
- **aed96876ae537f9a5**: subagent JSONL line 50, "Rows 10-13 hold. Now the dispatch region." Every later turn is tool calls only. The final report is the `SubagentHandback` tool_use at line 249.
- **a473b047719b4263a**: it has **no** assistant text blocks at all. Its final report is the `SubagentHandback` tool_use at line 310.

I compared each SubagentHandback `input.message` with the text delivered in the coordinator transcript (after removing the 2-space harness indent). Both are byte-identical: 12050 and 13475 chars. So the verbatim texts below are both the subagents' final reports and what was delivered.

**a473b047719b4263a did report**, at L789 (17:05:47Z), after the handoff was written. Its task-notification is at L786/L803.

### aed96876ae537f9a5: verbatim (delivered L737; subagent line 249)

```
PREMISE REPORT: spec-jobdir-part2-dispatch-gate.md
(/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-04e/docs/research/kb/raw/specs-2026-10-04d/spec-jobdir-part2-dispatch-gate.md)

This lane is read-only (Read/Grep/Glob only, no shell, no Write), so nothing was written to findings.md. The coordinator needs to persist this report.

Baseline I read: main checkout working tree. `.git/refs/heads/main` and `.git/refs/remotes/origin/main` are both `ee3b29da24a4…`. `.git/logs/refs/remotes/origin/main:213` shows `ed8e1a96 → ee3b29da pull --ff-only`. You said "at or after d921a3f6". That sha appears nowhere in `.git/{FETCH_HEAD,logs/HEAD,packed-refs,refs/**}`; the control is `ee3b29da`, which does hit in those files. So I cannot place d921a3f6 relative to ee3b29da, and every verdict below is against ee3b29da. I assumed the main working tree is clean, because I could not run `git status`.

ROWS: 44 checked — 34 CONFIRMED (0 provenance corrected) / 5 REFUTED / 0 UNVERIFIABLE / 5 ASSUMED (1 checkable)

1 — REFUTED (stale) — `.git/refs/heads/main:1` = `ee3b29da24a4e64f30f0576353cee0331c7c75b5`, not `36ab6bba`.
2 — REFUTED (stale) — `.git/refs/remotes/origin/main:1` = `ee3b29da…`, the same as local main. The "origin ahead of local" premise no longer holds.
3 — CONFIRMED (historical only) — `.git/logs/refs/remotes/origin/main:211` reads `36ab6bba… eba2e4e4… fetch -q origin: fast-forward`. It is superseded by lines `:212-213`, ending at ee3b29da.
4 — CONFIRMED — `.git/logs/refs/heads/fix/codex-banner-ansi:2` reads `4fdbac59 → 2d81c36d commit: fix(sdlc-team): settle codex runs whose exec banner is ANSI-coloured`. The `.git/logs/HEAD:1057-1058` cite is not the place this is recorded; the branch log is.
5 — CONFIRMED, and now on main — `sdlc_team.py:819-822` on main is the comment plus `"--color", "never"`, and `dispatch` is still at `:723`.
6 — ASSUMED — I cannot read the PR number. The code is consistent with the claim: main now carries exactly the BA hunk, and the test `:412-416` asserts `--color never`.
7 — CONFIRMED — main `generate_dispatch_schema` `:1067`, `sdlc_team_main` `:1093`. The BA prediction now describes main.
8 — CONFIRMED — main `tests/test_sdlc_team.py`: `_request` `:171`, `_capture_dispatch` `:185`, sandbox test def `:270`, `--color` asserts `:412-416`, schema test def `:1706`.
9 — ASSUMED (moot) — I could not diff eba2e4e4..ee3b29da. Every cited file was re-read at ee3b29da instead (below), so this row no longer carries weight.
10 — CONFIRMED — `sdlc_team.py:56-62`.
11 — CONFIRMED — `sdlc_team.py:83-98`, the last field is `errors: tuple[str, ...] = ()` at `:98`.
12 — CONFIRMED — `_DispatchState` `:172-180`; `_resolved_dispatch` `:214-253` builds `SdlcTeamDispatch` by keyword (`:237-251`).
13 — CONFIRMED — `build_prompt` `:256-293`; `SPEC FILE:` `:274`; REVIEW clause `:261-267`. The signature is `build_prompt(request, repo_root)` at `:256`.
14 — CONFIRMED — 0 hits for `SPEC_UNCOMMITTED|spec_uncommitted|spec_commit` across python/tests/schemas/.claude/skills/.agents/skills. The control `SPEC_MISSING|spec_missing` gives 7 hits (6 plus the `.agents` mirror). The control anchor `tests/test_sdlc_team.py:1666` is now `:1671`.
15 — CONFIRMED — 0 hits for `\bgit\b|subprocess\.run` in `sdlc_team.py`. The same pattern gives 6 lines in `session_common.py` (`:184,186,187,194,197,202`).
16 — CONFIRMED — `sdlc_team.py:723-777` is exact: INVALID `:727-739`, SPEC_MISSING `:741-753`, CLI_MISSING `:755-767`, paths `:769-777`.
17 — REFUTED (anchor rot from #1662) — argv is now `:811-828` (spec says `:811-824`). The `try` (prompt write `:833`, unlink `:834`, `subprocess.Popen` `:852`) and `except OSError → INVALID_REQUEST carrying argv` are now `:830-878` (spec says `:826-874`). DISPATCHED result `:880+`. The behaviour is as described.
18 — CONFIRMED — `sdlc_team.py:16` `import subprocess`.
19 — CONFIRMED — `tests/test_sdlc_team.py:185-203` (fake records every call and returns `_DetachedProcess`; patches `sdlc_team.subprocess.Popen` and `sdlc_team.shutil.which`). `_DetachedProcess` `:28-31` has no `__enter__`.
20 — CONFIRMED — `:266-286`: the IMPLEMENT cell uses `_request` (an untracked `tmp_path/spec.md`, `:171-182`) and asserts only flag absence (`:285-286`).
21 — REFUTED (anchor rot, +5/+4) — the CLI test is now `tests/test_sdlc_team.py:1651-1673` (spec says `:1646-1668`); `sdlc_team_main` is now `:1093-1110` (spec says `:1089-1106`). Behaviour holds: `:1110` `return 0 if result.status is SdlcStatus.DISPATCHED else 1`.
22 — CONFIRMED — `schemas/sdlc-team-dispatch.json:1-97`, required `:73-76`, enum `:81-86` (4 values, sorted alphabetically).
23 — REFUTED (anchor rot) — the schema-equality test is now `tests/test_sdlc_team.py:1698-1714` (spec says `:1693-1709`); `generate_dispatch_schema` is now `sdlc_team.py:1067-1069` (spec says `:1063-1065`). Semantics hold: parsed-JSON equality at `:1711-1714`; `codec.schema(SdlcTeamDispatch)` at `:1069`.
24 — CONFIRMED — `sdlc_team.py:700-720` (`shutil.which("mise")` `:712`, `which("codex")` `:715`).
25 — CONFIRMED — `…/cpython-3.14-macos-aarch64-none/lib/python3.14/subprocess.py:512` `def run(`, `:554` `with Popen(*popenargs, **kwargs) as process:`. The venv home is that dir (`python/.venv/pyvenv.cfg:1`).
26 — CONFIRMED — `.claude/skills/codex-sdlc-team/SKILL.md:51`.
27 — CONFIRMED — `SKILL.md:72-77`; mirror `.agents/skills/codex-sdlc-team/SKILL.md:75`.
28 — CONFIRMED — `mise.toml:1389-1392`; `hk.pkl:733-734`.
29 — CONFIRMED — `skills_mirror.py:122-125`.
30 — CONFIRMED — `mise.toml:294-296`; `main.py:3056-3058`.
31 — CONFIRMED — `suites.toml:3046-3052` (`regex_forbid`, `PLANNING_DISABLED|LANE_ENV_OVERRIDES`, path `sdlc_team.py`).
32 — CONFIRMED — `tests/conftest.py:27-49`.
33 — CONFIRMED — `session_common.py:32`.
34 — CONFIRMED — `tests/test_worktree_guard.py:19-22` (`timeout=10`), `:30` (`init -b main`), `:35` (`-c commit.gpgsign=false commit`).
35 — CONFIRMED — the only sdlc hit is `tests/test_sdlc_team.py:268`. The other hits are `cv.Edge.REOPEN_IMPLEMENT`, which shows the probe matches.
36 — CONFIRMED — `:326-344`, `:364-367`.
37 — CONFIRMED — `agent-artifact-conventions.md:48`, `:75`.
38 — CONFIRMED — `.gitignore:125` `.agent/`; no `docs/specs` match.
39 — CONFIRMED — `HW/…/spec-jobdir-preservation.md:310-341`.
40 — CONFIRMED — same file `:466-479`, `:492-493`.
41 — CONFIRMED — same file `:600`.
42 — CONFIRMED — same file `:676-679`.
43 — ASSUMED — `--show-toplevel` symlink resolution. §3.2 resolves both sides, so nothing rests on it.
44 — ASSUMED (checkable) — this matches the existing pattern for every `str = ""` field (`schemas/sdlc-team-dispatch.json:33-36`, `:61-64`). The equality test settles it.

MISSING:
- **S5 can launch a real paid codex lane under mutation M8 (load-bearing).** The S5 precedent (`tests/test_sdlc_team.py:1651-1673`) fakes neither `shutil.which` nor `Popen`. It is safe today only because SPEC_MISSING returns before launch (`sdlc_team.py:741-753`). S5's spec exists, so with the gate deleted (M8), dispatch reaches the real `_codex_launcher` (`:712-720`, real `mise` and `codex` on the host) and the real `subprocess.Popen` at `:852`: a detached supervisor running real `codex exec`. The fix is for S5 to patch `sdlc_team.subprocess.Popen` with the F1 git-passthrough raising fake (and optionally `which`), so M8 fails S5 by assertion instead of by spending credits.
- **No git-context scrub on the gate's git calls (recommended correction).** The repo convention is that every production git probe passes `env=child_env.without_git_context()` (`child_env.py:71-74`; used at `pr.py:244,259`, `doctor.py:1524,1656`, `session_state.py:120`, `sync.py:414,436`, `pr_facts.py:53`). The reason is in `tests/test_pr.py:525-528`: "GIT_DIR overrides `git -C`". §3.2 omits it, so an inherited `GIT_DIR`/`GIT_WORK_TREE` from a hook or editor would retarget `rev-parse --show-toplevel` and `HEAD:<rel>` away from the spec's worktree. In tests the pre-push suite already strips these (`mise.toml:310-314`, `process git-isolated`), but plain `mise run test`/`uv run pytest` does not. Add it to §3.2's "every git call" sentence. F1's `_REAL_POPEN(command, **kwargs)` forwards `env=`. S2.9 still works because the scrubbed copy keeps the emptied PATH.
- **The order of setup in S2.9 matters and is not stated.** `_committed_spec` must run before `monkeypatch.setenv("PATH", empty)`, or the fixture's own git calls fail. Also, `git` resolves through a mise shim on this host (`conftest.py:61-64`), and this is irrelevant once PATH is emptied.
- **The skill example request will become a refused shape.** `SKILL.md:37-48` shows `"mode": "implement"` with `"spec_file": "/absolute/path/to/spec.md"`, which the gate now refuses. If U1 is accepted, change the example path to `…/docs/specs/<name>.md` (then the mirror regenerates).
- **Text vs bytes capture is unstated for checks 1, 3 and 5.** §3.2 says only check 4 is bytes. Checks 1 and 5 need `text=True` or an explicit decode before `Path(stdout.strip())` and the returned sha. State it, or the implementer may pass bytes into `Path` (TypeError, which escapes the `OSError`/`TimeoutExpired` catch). `session_common.py:186-192` is the `text=True` precedent.
- **Byte comparison assumes no eol/smudge filters.** There is no `.gitattributes` in the repo (Glob found nothing), so blob bytes equal working-tree bytes today. Non-blocking residual: a future `.gitattributes` eol rule would make check 4 fail closed (safe direction).
- **M9 does not make S2.1 fail.** With `ls-files --error-unmatch` as check 3, an untracked file still fails `ls-files` and returns the same message, so S2.1 stays green. S2.2 and S2.3 fail, because check 4's `cat-file HEAD:<rel>` returns the check-4 message instead of the expected check-3 message. The spec already says "or be explained". Record that S2.1 is expected to survive M9.
- **The other Popen-patching tests are all review mode,** so F1 does not need to touch them (`tests/test_sdlc_team.py:337,367,402,434,466,1614`; only `:268` uses IMPLEMENT). This is an implicit premise of "the only edits to existing tests" in §4, and it holds.

VERDICT: FIX SPEC FIRST. The four corrections below are blocking; the residuals after them are not.
1. **S5 safety (load-bearing):** require S5 to patch `sdlc_team.subprocess.Popen` with the F1 git-passthrough raising fake, so M8 cannot launch a real supervisor or codex.
2. **Rotted anchors (REFUTED rows):**
   - Rows 1-3 and the provenance caveat: local main = origin/main = `ee3b29da`. Drop the "unpulled main" narrative.
   - The #1662 paragraph and U3: #1662 has already merged, so the "+4/+5" caveat is now just fact. Cut from ee3b29da (or later), not "after #1662".
   - Row 17: argv `:811-828`, try/except `:830-878`.
   - Row 21: test `:1651-1673`, `sdlc_team_main` `:1093-1110`.
   - Row 23: test `:1698-1714`, `generate_dispatch_schema` `:1067-1069`.
   - Row 14 control anchor: `:1666` → `:1671`.
   - Rows 7-8: restate as main anchors.
   - Row 9: drop it (re-derived).
3. **Git env scrub:** add `env=child_env.without_git_context()` to the "every git call" sentence in §3.2, citing `pr.py:244` as the precedent.
4. **Capture types:** state that checks 1, 3 and 5 use `text=True` (or decode), and that check 4 alone captures bytes.

Non-blocking residuals:
- Row 6: an unverified PR number, with no effect on code.
- Rows 43-44: settled by the design and by the equality test.
- d921a3f6: its relation to ee3b29da is unverified. Before cutting, the coordinator should run `git merge-base --is-ancestor d921a3f6 ee3b29da` (or diff the §2 files between them).
- `.gitattributes`: none today; a future eol rule fails closed.
- Skill example path: only relevant if U1 is accepted.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): local reads of sdlc_team.py, session_common.py, child_env.py, main.py, skills_mirror.py, tests, conftest, schemas, SKILL.md, suites.toml, mise.toml, hk.pkl, .gitignore, git refs/logs, and the parent spec in the handoff-2026-10-04d worktree.
```

That report's "d921a3f6 relation unverified" residual is already settled by transcript L443-444: d921a3f6 (#1662) is in `git log origin/main` just below ee3b29da, so it is an ancestor.

### a473b047719b4263a: verbatim (delivered L789; subagent line 310)

```
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
```

## Corrections the 04g handoff needs
- Replace "premise-verifiers RUNNING / re-run both" with: **both reported, both FIX SPEC FIRST.** Persist both texts above and fix the specs. The specs are in `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-04e/docs/research/kb/raw/specs-2026-10-04d/`.
- Add: the 04g ship is in flight (log, pids and bfdc3e53 as in section 1, item 3). Wait on its `rc=` before retiring c769e1a1.
- Add: Ray's L830 instruction, "/codex-sdlc-team skill team to review and fix" the handoff-churn issue.
- Fix the push time: 12:00 CDT, not 12:06.
- Fix the main checkout: it is behind origin/main 13af2848, so pull before any land.
- Note that #1658's base is ee3b29da, one behind main.
- Note that successor 120251 also lacks bgIsolation:none.

