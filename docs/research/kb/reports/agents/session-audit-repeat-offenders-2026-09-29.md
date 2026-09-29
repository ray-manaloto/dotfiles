# Session audit — repeat offenders (Brief R), 2026-09-29

Session: `dcb0b106-0da4-46a8-9ce7-2e41e8ce5b9e` (dotfiles). Method: `session-handoff-briefs-q-s-2026-09-28.md` § Brief R
(method only). Lane: read-only except this file. Status: COMPLETE (transcript state to ~16:00Z 2026-09-29; the
session was still running).

## Summary

| ID | sev | repeat | count | warning that failed | disposition (file) |
|---|---|---|---|---|---|
| R1 | MED | zsh unmatched-glob abort | 16 (+6 concurrent audit lanes) | 09-28 R3; PLAN S28b-3 RULED not run; #1388 open | MACHINE: `hook_guard` `zsh_unquoted_glob_arg` (`--include=*`, `gh api …?`) — 12/16, 0 FP; path globs stay with S28b-3 |
| R2 | MED | codex lens on a stale HEAD | 2 (`6b8832c7` L1723; `a8e8e8d9` L2303 — NOT `613d822a`) | none specific; coordinator's own L1760 admission | MACHINE: `mise run codex-lens -- <sha>` (`codex_lens.py`) refuses sha≠HEAD or dirty index/tree + `hook_guard` redirect; PLAN: Phase 11 one-launcher |
| R3 | HIGH | `grep '^rc=' LOG && git commit` hid lint rc=1 | 4 uses, 1 false "all pass" (L2303) | control-arm rule; verify-before-advancing; `feedback_pipe_kills_exit_code` | MACHINE: `hook_guard` `rc_grep_gates_commit` + `gate run --all` in `gate_result.py` (the typed `mise run gate` exists, unreferenced by any skill/rule) |
| R4 | LOW | scribe/reviewer hit `maxTurns` | 3 | `project_session_2026-09-28b.md:24` | RAY RULING: raise caps (cold-reviewer 100, spec-scribe 80) vs a `PostToolUse`/`Agent` resume nudge |
| R5 | LOW-MED | own edits fail ruff/E501/typos | 4 full gate cycles (+4 in-call) — `unparseable` verbatim again | 09-28 R7 (same word); PLAN S28b-4 "R7 RULED: accept" | RAY RE-RULING: `mise run lint -- --changed` fast pre-gate (`lint.py:66` hard-wires `--all`) |
| R6 | MED | stash+checkout left the fix only in a stash; 12 hand-rolled mutation arms | 1 near-loss; 12 arms (same as 09-28) | `feedback_git_checkout_is_not_undo`; 09-28 R4; PLAN S28b-4 not built | MACHINE: `mise run mutation-arm` (`mutation_arm.py`) + `hook_guard` stash/checkout redirect |
| R7 | — | review rounds past the 2-round cap | 2 (#1437, #1450) | — | NONE: both surfaced to Ray via AskUserQuestion at the cap (L1077, L3998) — compliant |

Not recurring this session (control-armed, see end): `echo ====` (7 guard denies, 0 escapes), bare `timeout` (2
deliberate probes), multi-path `$VAR`, write on `main`, tracked-report clobber.

Build order by value/cost: R3 (HIGH, one regex + a flag on an existing module), R1 (one regex, closes #1388's
glob half for 12/16), R6 and R2 (each a task + redirect; both re-derived by hand 12× this session), then the rulings
R4/R5.

## Findings

### Method and extraction control arm

Scratchpad extractor (`scratchpad/ro/extract.py`) pairs every `tool_use` with its `tool_result` across the MAIN
transcript and all 30 `subagents/**/*.jsonl` (incl. this lane, `a1498848`) → **1152 tool calls** (MAIN 473).
Anchors are `<src> L<line>` (the `tool_use` line) with UTC time. Positive control: the scan for `no matches found`
finds the known 2026-09-28 occurrence text when a lane *reads* the prior report (a1498848 L31, a4645f6a L53) — those
text hits are excluded below; only `(eval):N: no matches found:` lines produced by a command's own execution count.

### R1 — zsh unmatched glob aborts the command — REPEAT, **16 occurrences in 10 transcripts** (+6 in concurrent audit lanes), despite a RULED plan row

Severity: MEDIUM (every occurrence visible; cost = one wasted call + a lost-evidence window each; none produced a
wrong conclusion that I could find, but 2 lost a probe's output inside a longer chain).

| # | anchor | UTC | glob word | shape |
|---|---|---|---|---|
| 1 | MAIN L297 | 02:39 | `~/.claude/plugins/cache/*fable*` | path glob (the probe was a deletion's control arm) |
| 2 | a61a79bc L93 | 07:07 | `--include=*.js` | grep option |
| 3 | a61a79bc L157 | 07:09 | `--include=*.py` | grep option |
| 4 | a3884b3d L23 | 07:50 | `--include=*.py` | grep option |
| 5 | abe12c28 (cold-reviewer) L35 | 05:53 | `…/cold-review-07221b46*` | path glob (existence check) |
| 6 | abe12c28 L238 | 06:00 | `~/.config/mise/conf.d/*.toml` | path glob; `2>/dev/null` did not help |
| 7 | a66d4fad L154 | 11:10 | `--include=*.md` (line 40 of a heredoc-append command) | grep option |
| 8 | a472b5fc L167 | 11:26 | `repos/jdx/mise-action/contents/action.yml?ref=9149ea85…` | **`?` in a `gh api` URL query** (new shape) |
| 9 | a472b5fc L176 | 11:27 | `--include=*.yml` | grep option |
| 10 | ac1415a8 (cold-reviewer) L72 | 13:37 | `--include=*.js` | grep option |
| 11 | ac1415a8 L110 | 13:38 | `repos/jdx/renovate-config/commits?per_page=3` | **`?` in a `gh api` URL** |
| 12 | af96115c L47 | 14:00 | `--include=*.js` | grep option |
| 13 | MAIN L4221 | 15:50 | `docs/research/kb/reports/agents/session-audit-*2026-09-29*` | path glob (handoff's own "does a report exist" probe) |
| 14 | a746b3d4 (`/code-review`) L27 | 03:10 | `--include=*` | grep option |
| 15 | a746b3d4 L34 | 03:11 | `--include=*.sh` | grep option |
| 16 | a0397791 (mattpocock Standards) L41 | 07:51 | `--include=*.json` | grep option |

**RECOUNT (this lane's own bound, found and fixed):** the first pass truncated each tool result at 4000 chars, and
the `no matches found` line sits at the END of a long output, so rows 14-16 were invisible to it
(`probes-need-a-control-arm.md` rule 3 — "YOUR OWN PARSER"). The replay of the proposed regex (below) hit those three
as "matches without a nomatch", which exposed the truncation; a full-length re-extraction (1476 calls by then, the
session still running) confirmed all three carry `(eval):1: no matches found:`. So the coordinator-era count is
**16 in 10 transcripts**. Concurrent §1c audit lanes (launched 15:51, running beside this one) added **6 more** —
a0ac3629 L45 (`.devcontainer/*.sh`), a43aba43 L119 (`--include=*.py`), a6a6422e L206 (`--include=*.py`), ac877cb0 L46
(`2026-09-2[89]`), L76 (`…/cli*.py`), L216 (`--include=*.sh` ×2) — **22 total**. Excluded as text reads, not
executions: a1498848 (this lane) L31/L58/L111/L225, a4645f6a L53, af36a7a9 L46.

Shape split (coordinator era, 16): `--include=*…` 10, `gh api …?query` 2, path glob that legitimately matches nothing 4.

Warnings that failed: 2026-09-28 repeat-offenders report **R3** (5 occurrences, same shapes); `task_plan.md:1055-1059`
**S28b-3 — RULED** ("probe `CLAUDE_CODE_SHELL=bash` … → adopt or fall back to guard rules"), not executed this session;
`task_plan.md:1194-1197` records "unmatched-glob half NOT built (no static signal)"; issue **#1388 still OPEN** for the
glob half; `memory/project_session_2026-08-08.md:94`, `project_session_2026-09-14-d.md:103-104`. The `=` half's guard
(`zsh_equals_separator`, `hook_guard.py:733`) fired **7 times** this session (MAIN L122, a0ac3629 L31, a2d1db9b L56,
a472b5fc L139, a61a79bc L150, a66d4fad L129, ac1415a8 L43) — each a clean one-call deny, confirming a guard is the
mechanism that works and memory/plan text is not.

Control arm: `grep -n -i "include_glob\|nomatch\|no matches" python/src/dotfiles_setup/hook_guard.py` → 0 hits, while the
control token `zsh_equals_separator` → 1 hit in the same file: no glob rule exists (the probe can see rules).

Disposition — PROPOSED MACHINE CHECK (independent of S28b-3's shell probe, because "no static signal" is wrong for
12 of 16): `hook_guard` rule **`zsh_unquoted_glob_arg`** in `python/src/dotfiles_setup/hook_guard.py`, with allow/deny
cases in `tests/test_hook_guard.py` and a `since` date per `mise-tasks-only.md` § Extending. Deny, after
`_inert_masked` quoting, any unquoted argument word that (a) starts with `--include=`/`--exclude=`/`--glob=`/`-g` and
contains `*`/`?`/`[` — in zsh it can only match a file literally named `--include=…`, so it is ALWAYS a nomatch abort
(occurrences 2-4, 7, 9, 10, 12, 14-16); or (b) contains `?` after a `/`-bearing word in a `gh api` argument
(`gh api repos/…?per_page=3`, occurrences 8, 11). Redirect text: "zsh aborts on an unmatched glob — quote it:
`--include='*.py'`, `gh api 'repos/o/r/commits?per_page=3'`". Replay (scratchpad regex, quotes/heredocs masked, over
the 1152-call extraction): clause (a) → exactly the 10 `--include` rows, clause (b) → exactly rows 8 and 11; **12 of
16, zero false positives** (every hit carries a real nomatch abort). The 4 path-glob cases
(1, 5, 6, 13) have no static signal — they stay with S28b-3 (`CLAUDE_CODE_SHELL` probe) or a `cwd`-relative
`glob.glob` check (2026-09-28 R3 option 2). PLAN: split S28b-3 so the static rule ships now and #1388 closes on it.

### R2 — codex review lens pinned to a STALE HEAD — TWICE (both via `SHA=$(git rev-parse HEAD)` after an unsettled commit)

Severity: MEDIUM (a review round spent on the wrong commit each time; occurrence 2 also produced a user-facing
"all five pass" claim that was false — see R3).

| # | anchor | UTC | what happened |
|---|---|---|---|
| 1 | MAIN L1717 → L1723 | 06:19:36 → 06:19:40 | the commit of `10e5e806` was launched in the BACKGROUND (L1717; its pre-commit hook runs hk, so it takes minutes); 4 s later L1723 ran `sleep 2; SHA=$(git rev-parse --short HEAD); … codex exec … review --commit $SHA` → reviewed `6b8832c7` (the previous, already-reviewed commit). Found at L1746 (`codex-lens-10e5e806.log: No such file`), admitted at L1760 ("read HEAD before the new commit had landed"), re-launched pinned at L1758 |
| 2 | MAIN L2303 → L2344 | 08:10:34 → 08:17:00 | `grep '^rc=' gates2.log && git commit …; echo "commit rc=$?"; SHA=$(git rev-parse --short HEAD); … review --commit $SHA` — lint was rc=1, the pre-commit hook REFUSED the commit (`commit rc=1`), and the `;` chain went on to review the unchanged HEAD `a8e8e8d9` (already reviewed at L2104-era). Admitted at L2361 |

Correction to the brief's candidate: the second occurrence is **`a8e8e8d9` (MAIN L2303)**, not `613d822a`. The
`613d822a` lens (L2979) was explicitly pinned and ran on the right commit; `613d822a`'s commit (L2967) returned rc=0.
Control arm: a regex scan over all 1152 calls for `stale (head|sha)|previous commit|re-reviewed|commit rc=[1-9]`
returns exactly L1760, L2344, L2361 (+ one unrelated Read) — the scan can see the known occurrence 1, so the absence
of a `613d822a` refusal is real.

Warnings that failed: none specific existed before occurrence 1; after it, the coordinator's own L1760 message named
the cause, and 2 h later the same shape recurred (dynamic `rev-parse` after a `;`-chained commit). General warnings in
play: `verify-before-advancing.md` ("read the real rc"), `feedback_ship_gates_before_push_automerge_race.md` (a race on
an unsettled commit). The canonical lens command lives only as prose in `.claude/skills/codex-sdlc-team/SKILL.md:187`;
this session hand-typed it **12 times** (MAIN L715, L876, L970, L1081, L1584, L1723, L1758, L1851, L2303, L2428,
L2979, + persistence boilerplate each time), which is the `mise-tasks-only.md` "recurs → earns a task" trigger.

Disposition — PROPOSED MACHINE CHECK: a `mise run codex-lens -- <sha>` task backed by
`python/src/dotfiles_setup/codex_lens.py` (+ `tests/test_codex_lens.py`) that REFUSES (rc≠0, before spawning codex)
when (a) `<sha>` is not `HEAD`, or (b) the index or tracked worktree differs from `HEAD`
(`git diff --cached --quiet && git diff --quiet` fails) — both occurrences had the staged fix still uncommitted at
launch — then runs the SKILL.md:187 argv, and writes the verbatim report to
`docs/research/kb/reports/agents/codex-review-lens-<sha>-<date>.md` (refusing to overwrite). Pair with a
`hook_guard` redirect in `python/src/dotfiles_setup/hook_guard.py` (deny a raw `codex exec … review --commit` outside
the task; test pair in `tests/test_hook_guard.py`). Replay: occurrence 1's index held the staged `10e5e806` content
while the background commit's hook ran; occurrence 2's index held the refused commit's content — clause (b) refuses
both; L1851/L2428-style launches after a settled commit pass. PLAN: fold into the Phase 11 "one launcher" class fix
named in `.claude/rules/ai-cli-invocation.md` ("The class fix that replaces all three with one launcher").

### R3 — `grep '^rc=' LOG && git commit` — a probe that can only pass; used 5× (4 `&&`-gated), hid `lint rc=1` once

Severity: HIGH (a false "all five gates pass" report to the user at MAIN ~L2303-2344; only the pre-commit hook —
a later layer — stopped the commit).

| # | anchor | UTC | log content | outcome |
|---|---|---|---|---|
| 1 | MAIN L1578 | 06:11 | all `rc=0` | commit `6b8832c7` (correct by luck) |
| 2 | MAIN L1851 | 06:32 | (background) | commit + lens |
| 3 | MAIN L2104 | 07:49 | all `rc=0` | commit `a8e8e8d9` |
| 4 | **MAIN L2303** | **08:10** | **`rc=1 [mise run lint]`** | grep matched (it matches `rc=1` as happily as `rc=0`), `&&` fired, hook refused commit; lens re-reviewed `a8e8e8d9` (R2 #2); L2361: "I read the rc lines through a `grep … &&` chain and reported 'all five pass' without checking each value" |
| (5) | MAIN L965 | 03:30 | earlier variant: `grep '^rc='` then an unconditional commit | all rc=0 |

After L2361 the coordinator switched to an explicit `nonzero: N` count (L3158 shows `nonzero: 0`) — a behavioural fix,
not a mechanical one; nothing prevents the next session re-deriving the `grep && commit` shape.
Warnings that failed: `.claude/rules/probes-need-a-control-arm.md` title rule ("A check that can only pass is not a
check") and rule 2; `.claude/rules/verify-before-advancing.md` § Evidence discipline ("Read a file-based rc … never a
piped/notified exit code"); memory `feedback_pipe_kills_exit_code`. All three are eager/indexed.
Also: the session hand-rolled the gate loop (`for g in "mise run lint" …; do sh -c "$g"; echo "rc=$? [$g]"; done`)
at least 8 times (MAIN L2392, L2876, L2947, L3871, L3947, L4036, + the logs behind L1578/L2104/L2303), while
`mise run gate -- run <lint|pytest|verify|lint-docs|pin-actions>` already exists (`python/src/dotfiles_setup/gate_result.py:58-63`,
status-derived exit code `:65-70`, typed result under `.agent/gate-results/`). Control arm: `grep -rn "mise run gate\b"
.claude/skills .claude/rules .claude/agents` → 0 hits (while the same grep for `mise run lint` hits many): **no skill or
rule points at the task**, so the hand-rolled loop is the path of least resistance.

Disposition — PROPOSED MACHINE CHECK: (1) `hook_guard` rule `rc_grep_gates_commit` in
`python/src/dotfiles_setup/hook_guard.py` (+ `tests/test_hook_guard.py`): deny a command where `grep` of a `rc=`
pattern WITHOUT a nonzero-discriminating form (`'^rc=[1-9]'`, `-v 'rc=0'`) is joined by `&&` to `git commit` —
redirect: "`grep '^rc='` matches `rc=1` too; chain `mise run gate -- run lint && mise run gate -- run pytest && …`".
Replay (scratchpad regex on raw commands): matches L1578, L1851, L2104, L2303 plus ONE false positive, MAIN L2477 —
the `progress.md` heredoc that records this very LESSON as text; the real rule must run after `_inert_masked`
(which neuters heredoc bodies, `mise-tasks-only.md` § Extending), and its test pair should include that quoted
mention as the must-pass case. Note the coordinator's own disposition for this was a `progress.md` LESSON line
(L2477) — a note, which is exactly the disposition Brief R rejects for a repeat. (2) Add
`gate run --all` (every `GATE_COMMANDS` entry, exit = worst status) to `gate_result.py` so the one-line replacement
exists, and name it in `.claude/skills/pr-workflow/SKILL.md` and `verify-before-advancing.md`'s matrix (a doc edit
that rides with the machine check, not in place of it).

### R4 — spec-scribe / cold-reviewer hit their `maxTurns` cap mid-work — 3× this session, after a memory named it

Severity: LOW (each cost one `SendMessage` resume and 2-10 min; incremental report persistence meant nothing was lost).

| # | agent (type, cap) | anchor of resume | assistant msgs total | what was partial |
|---|---|---|---|---|
| 1 | a4645f6a (spec-scribe, `maxTurns: 40`, `.claude/agents/spec-scribe.md:7`) | MAIN L336 02:44 "You hit the turn limit … the spec file has 53 lines so far" | 50 | S28b-0 spec half-drafted (a 45-file audit sweep) |
| 2 | abe12c28 (cold-reviewer, `maxTurns: 60`, `.claude/agents/cold-reviewer.md:7`) | MAIN L1488 06:02 "You hit the turn limit with F1-F2 recorded" | 67 | review of `07221b46` (45 files, +667/-74) |
| 3 | ac1415a8 (cold-reviewer, 60, codex FALLBACK — codex usage-limited) | MAIN L3457 13:51 "You hit the turn limit mid-evidence (E4 table)" | 63 | B′ review, Findings table empty |

Controls: the other spec-scribe (aaf1cc96, 21 assistant msgs) and cold-reviewers (a2d1db9b 41, a0ac3629 18) finished
under cap and received no resume `SendMessage` (the full list of MAIN `SendMessage` calls = exactly L336, L1488,
L3457), so the scan discriminates. Prior warning: `memory/project_session_2026-09-28b.md:24` ("Opus cold-reviewer hit
its 60-turn cap once; resuming it … found a MEDIUM") — it records the event and the recovery, not a prevention.

Disposition — **Ray ruling** (no pure machine check can predict a review's size; the cap is a deliberate runaway bound):
(a, recommended) raise `maxTurns` to 100 for `cold-reviewer` and 80 for `spec-scribe` in
`.claude/agents/{cold-reviewer,spec-scribe}.md` — 3 of 6 runs this session exceeded the current caps, all on large
diffs/sweeps; or (b) keep the caps and add a mechanical resume prompt: extend the existing `PostToolUse`/`Agent` hook
(`agent-report-persistence.md` § Native carriage) so an Agent completion whose report file lacks a `Status: COMPLETE`
line injects "resume this agent by SendMessage, pinned to the same SHA" — test row in `tests/test_hook_selfcheck.py`.
Either way a PLAN row, not memory.

### R5 — own edits failing ruff/E501/typos — 4 full gate cycles lost + 4 cheap in-call catches; `unparseable` recurred VERBATIM from 2026-09-28

Severity: LOW-MEDIUM (no wrong result shipped — gates caught every one; cost ≈ one ~6-min full gate cycle each, pytest
alone is 4038 tests / 5 min 14 s per MAIN L965).

Reached the FULL gate (expensive):

| # | anchor | UTC | failure | file |
|---|---|---|---|---|
| 1 | MAIN L658/L671 | 03:09 | ruff 1 error (fixable) | `handoff_check.py` / tests |
| 2 | MAIN L2344/L2363 | 08:17 | `E501 Line too long (111 > 88)` — also the rc hidden by R3 | S28b-1 python |
| 3 | MAIN L2899/L2909 | 11:38 | `E501 (90 > 88)` | `schema_vendor.py:272` |
| 4 | MAIN L3638/L3643 | 14:06 | `typos` — **`unparseable`**, fixed by `sed 's/unparseable/unparsable/'` at L3654 | `tests/test_renovate_ignored_authors.py`, `tests/TEST-INDEX.md` |

Caught cheaply by the coordinator's own inline `ruff check` in the same call (the working habit): L2922 (the E501 fix
itself introduced two new E501s, 92 and 89), L3018 (`S105` on `token == "--"`), L3116 (2 errors), L3276
(`RUF002` prime `′`, `D403`). Excluded as not own-prose: L2790 (`contract_token_uniqueness` / `renovate_config_validate`
— real gate logic), L3319 (`taplo`; see the known transient at `task_plan.md:1044`).

Warning that failed: 2026-09-28 repeat-offenders **R7** — the SAME word: "`typos` on 'unparseable' in
`sync.py`/`tests/test_sync.py`" — and its PLAN disposition `task_plan.md` S28b-4 "R7 RULED: accept (gates catch it)";
`memory/feedback_typos_diff_hides_ambiguous.md`. The ruling's premise held (gates caught all four), but it assumed one
cycle per session; this session paid four.
Why the 09-28 proposal would not have helped: R7 proposed a `PostToolUse` nudge on `Edit|Write`, but occurrences 2-4
were written through `python3 - <<'EOF' … p.write_text(…)` or `sed -i` inside **Bash**, which an `Edit|Write`
matcher never sees. Control: of this session's MAIN source edits, the `python3 - <<'EOF'` + `sub()` helper shape
appears in ≥12 calls (L604, L617, L1535, L2922, L3018, L3031, L3105, L3295, L3541, L3615, …).

Disposition — **Ray re-ruling request** (a repeat after an "accept" ruling): (a, recommended) a fast pre-gate —
`mise run lint -- --changed` in `python/src/dotfiles_setup/lint.py` (today `HK_COMMAND` is hard-wired to
`hk run check --all`, `lint.py:66`) that runs hk's own changed-file selection instead of `--all`, and make it the
first step of `mise run gate` (see R3) so a typo costs seconds, not a pytest run; test in `tests/test_lint.py`. Or (b)
keep the ruling and record the measured cost (4 cycles ≈ 25 min) in it.

### R6 — the `git stash` dance that left the fix only in a stash — once, inside a 12× hand-rolled mutation-arm pattern the prior audit already asked to replace

Severity: MEDIUM (near-loss of an uncommitted fix; recovered one call later).

| anchor | UTC | what happened |
|---|---|---|
| MAIN L2733 | 11:29:58 | mutation arm for `tests/test_workflow_skip_tools.py`: `git add refresh.yml test…; git stash push -q -- .github/workflows/refresh.yml 2>/dev/null; git show main:… > refresh.yml; pytest → rc=1 (arm OK); git checkout -q -- refresh.yml` — after `stash push` the index held HEAD's version, so `checkout --` restored **HEAD, not the fix**: `grep -c 'skip-tools' refresh.yml` → **0**. The #963 fix now existed only as `stash@{0}`, above an unrelated 12-day-old `stash@{1}` ("On main: mise.lock aws-cli …") — a bare `git stash pop` on a different day, or `drop`, would pick the wrong one |
| MAIN L2747 | 11:30:09 | `git stash pop -q stash@{0}` → `skip-tools` count 5; the fix came back UNSTAGED (` M refresh.yml`; pop without `--index` drops the staging) |

The same session hand-rolled backup → mutate → test → restore **12 times** with three different restore mechanisms
(`cp …bak` at MAIN L570, L688, L787, L931, L1035, L2275, L3533; in-memory python at L2386, L3129, L3288, L3610;
`git stash`+`checkout` at L2733) — the identical count to 2026-09-28's R4 ("hand-rolled … 12 times").
Warnings that failed: `memory/feedback_git_checkout_is_not_undo.md` ("For a tracked file it restores to the STAGED
version … prefer an inverse edit"); 2026-09-28 repeat-offenders **R4** and its PLAN row `task_plan.md` **S28b-4**
("R4 `mise run mutation-arm` helper (backup/mutate/assert-applied/test/restore — hand-written 12× this session)") —
ruled, not built. Control arm: `mise tasks | grep -i mutat` → only `session-review-mutation-*` sentinels, no
`mutation-arm`; the same listing shows `gate` (1 hit), so the probe can see tasks.

Disposition — PROPOSED MACHINE CHECK (execute S28b-4's R4 row; it is now a two-session repeat): `mise run
mutation-arm -- --file F --old O --new N -- <test argv>` backed by `python/src/dotfiles_setup/mutation_arm.py`
(+ `tests/test_mutation_arm.py`): in-memory byte backup, `assert count(old)==1`, apply, run the argv with a
file-captured rc, restore from the in-memory bytes (never `git checkout`/`stash`), verify the restore byte-for-byte,
exit non-zero if the mutation did not apply, the test PASSED, or the restore differs. Plus a `hook_guard` rule
`hand_rolled_mutation_restore` (`python/src/dotfiles_setup/hook_guard.py` + `tests/test_hook_guard.py`): deny a
command that contains both `git stash push … -- <path>` and `git checkout … -- <same path>` (the L2733 shape), with
the redirect to `mise run mutation-arm`. Replay: the stash+checkout clause matches L2733 only among 1152 calls.

### R7 — review rounds past the two-round cap — reached TWICE, surfaced to Ray both times: NOT a violation

`.claude/skills/codex-sdlc-team/SKILL.md:197`: "Stop after two respec rounds on one diff and surface the residue to Ray."

| PR | rounds (fix commits answering a review of the same diff) | at the cap | anchor |
|---|---|---|---|
| #1437 | 3: `fd5d422b`, `b0fc2268`, `f697ff89` (each lens found a narrower defect in the same attestation parser) | AskUserQuestion MAIN L1077 03:42 "The doctrine caps at two respec rounds. How do we close?" → Ray: "One last lens, then ship"; lens on `f697ff89` clean | L1077, L1082 |
| #1450 | `d92c1318` → `bef133bc` → `01be828f` (three `/code-review` rounds on the push-retry race) | AskUserQuestion MAIN L3998 15:11 "hit the two-round review cap" → Ray: "Re-run repair on the tip" | L3996, L3998 |
| #1439 / #1447 | 2 each (`6b8832c7`+`9b945687`; `19a565ef`+`4c685c39`) | at, not past | — |
| #1441 / #1445 | 1 each | — | — |

Control: PR commit lists from `gh pr view <n> --json commits` for all six PRs; a transcript regex for
`two|third … rounds|round cap` finds exactly L1050, L1077, L1082, L3996, L3998 (+ the skill text at L216). The cap
worked as written: both times the coordinator stopped and asked. Disposition: **none required**. Observation for the
PLAN (not a repeat finding): both over-cap loops were one input domain probed piecewise (whitespace bytes; git push
race states) — the `adversarial-review` skill's bounded-round enumeration (`SKILL.md` § Three questions, Q-FRESH) is
the lever, and it was not used for either loop's brief (the lenses were the fixed codex command and bundled
`/code-review`, which take no brief).

### Candidates checked and NOT repeated this session (control-armed)

- **zsh `echo ====`** — 7 attempts, all DENIED by `zsh_equals_separator` (list under R1). Closed by machine; #1388
  stays open only for the glob half (R1).
- **bare `timeout N`** (2026-09-28 R9) — 2 uses (a46a0ce8 L32, abe12c28 L65), both DELIBERATE probes of the diff's
  "`timeout` is not usable here" claim, each with `which -a timeout` beside it. Not mistakes.
- **multi-path `$VAR` word-split** (2026-09-28 R2) — scan for `NAME="a b"` + `No such file`, and for `no tests ran`/rc=4:
  0 real hits (the only matches are lanes *reading* the 09-28 report). Control: the same scan finds that report text.
- **write on `main`** — 0 `branch_guard` denials of Edit/Write; the only Edit/Write error in 1152 calls is an
  `old_string` miss (abe12c28 L336).
- **tracked report clobbered** (2026-09-28 R10) — every `Write … updated successfully` under `reports/agents/` was a
  lane updating a report it had itself created earlier in the session (a2d1db9b L235, a95c1f22 L56, abe12c28 L326,
  af776bda L62); the date+letter names (`-2026-09-28c`) held.
- Self-disclosure: this lane's own first R4 append died with `(eval):37: parse error` (an unquoted `<<EOF` second
  heredoc containing backticks in the same command, a1498848 L128); nothing was written, verified with
  `grep -c "### R4"` → 0, then re-appended. One occurrence, no warning covers it; not a repeat.


## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — `gh pr view` commit lists for #1437, #1439,
  #1441, #1445, #1447, #1450 (round counts), `gh issue list` for #1388 state.

Otherwise local only: the session transcript `dcb0b106-….jsonl` + its 30 `subagents/` transcripts, `task_plan.md`,
`progress.md`, the auto-memory dir, `.claude/{skills,rules,agents}`, and `python/src/dotfiles_setup/{hook_guard,gate_result,lint}.py`.
