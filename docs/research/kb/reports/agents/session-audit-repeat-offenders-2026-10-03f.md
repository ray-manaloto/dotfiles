# Session audit — repeat offenders (Brief R) — 2026-10-03f

Session `998ab91b-50a0-4bd2-917b-aa8e5825b915` ("dotfiles-20261002.watch"). Method: `## Brief R` in
`session-handoff-briefs-q-s-2026-09-28.md` (method only), common contract in
`/Users/rmanaloto/.claude/jobs/998ab91b/tmp/audit-brief-common.md`. Lane: read-only except this file. Status: COMPLETE.

Anchors are `L<n>` = line of the MAIN transcript
`~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles-worktrees-lane-completion-20261002/998ab91b-….jsonl`
(5,225 lines, 341 Bash calls), UTC. Extractors (scratch, untracked): `/tmp/ro-998r/{x,win,all,race,deny,g,payload}.py`.

## Summary

| ID | sev | repeat | count | warning that failed | disposition |
|---|---|---|---|---|---|
| F1 | **HIGH** | zsh `echo ======` ran despite a live guard rule — AND the bypass detector reports it as "guard denied (working)" | 1 run (L350); detector misclassifies **every** non-zero-exit bypass | memory `feedback_zsh_equals_expansion`; `hook_guard` rule `zsh_equals_separator` (#1421); `command-audit` bypass alarm | FIX-NOW: `command_audit._executed_ids` + test; PLAN: find why the guard did not fire |
| F2 | MED | user/coordinator told a write landed in the SAME tool batch as the write | **7** batches (L2750, L2838, L2901, L2934, L3849, L4241, L4331); the first write FAILED (L2751) | `verify-before-advancing.md` ("verified done"); `notepad-enforcement.md` rule 4 ("never pretend a denied write succeeded") | PLAN: inbox write owned by the tick script; announcements filled from its output |
| F3 | MED | worktree-isolation refusals after the watcher `EnterWorktree`'d mid-session; refused Write then bypassed via Bash | **7** in MAIN (L403, L435, L439, L948, L2751, L2757, L4442) + **7** in THIS lane | none in repo for the cause; CC changelog 2.1.273 says the heredoc/`$VAR` false refusals were fixed — still refusing on 2.1.288 | PLAN (watcher brief) + RAY RULING (upstream regression; Bash bypass of a Write refusal) |
| F4 | MED | research sweep run from a stale worktree 25 s after reading the newer workflow on `origin/main` | 1 (L4551, after L4529) | `verify-before-advancing.md` § "Validate against the latest branch code"; the session itself reported #1581 merged at L2620 | MACHINE: workflow preflight compares its own blob to `origin/main` → status `stale-workflow` |
| F5 | MED | coordinator died with no successor | 2 (L911-L937 19:21Z 10-02; L2750 03:32Z 10-03 → ~13 h outage) | #1583 auto-handoff (never loaded, L4199); dag-tick root cause known (`task_plan.md:2511`) | PLAN: ship `060de30b` (dag-tick STOP removal is NOT on main) + test; supervisor row exists (`task_plan.md:2536`) |
| F6 | MED | a lane launched outside its worktree hit the EnterWorktree permission prompt | 1 in session (1502 lane, L2645) after 7 that morning | `.claude/skills/parallel-work-split/SKILL.md:114,141` | PLAN exists (#1606, `task_plan.md:2535`) — widen its guard to LANES, add a test |
| F7 | LOW | session ids printed bare beside lane names, read by the coordinator as head SHAs | 1 (L2143 → L2152) | none | PLAN: label contract in #1551's summarizer (`session=` / `head=`) + test |
| — | — | pushed SHA claimed before `ls-remote` | **0** — did not recur | — | control below |

Counts: **1 HIGH, 5 MEDIUM, 1 LOW** (7 findings) + 1 candidate refuted.

## Findings

### F1 — HIGH — the zsh `=` separator ran past a live guard rule, and `command-audit` reports it as a successful denial

**Claim.** At L350 (17:45:08Z 10-02) the session ran
`T=…/tmp; cat $T/1502.md; echo ======; grep -n '^#' …`. Result L351: `Exit code 1 … (eval):1: ===== not found` — it ran,
and everything after the separator in that chain was lost (this exact cost is what #1388 / #1421 closed).

**Warnings that failed:** memory `feedback_zsh_equals_expansion` (MEMORY.md:122); `hook_guard` rule
`zsh_equals_separator` (`python/src/dotfiles_setup/hook_guard.py:791`, `_V10` = 2026-09-28); the 09-28/09-29 repeat-offender
reports, which named this class as closed by the guard.

**Evidence the guard SHOULD have denied it:**
- `hook_guard.match(<L350 command>)` → `zsh_equals_separator` at HEAD 0ac9bacd (`/tmp/ro-998r/g.py`).
- The real wrapper, `CLAUDE_PROJECT_DIR=<this worktree> bash scripts/pretooluse-guard.sh < payload` → rc=0 with
  `"permissionDecision": "deny"`.
- The session's project tree at the time was `fanout-fixes-20261002` on `docs/fanout-launch-fixes` (`faad62f8`); that
  branch carries both the hook registration (`.claude/settings.json`, 1 hit) and the rule (`hook_guard.py`, 1 hit).
- No fail-open was recorded: `~/.local/state/dotfiles/guard-fail-open.log` has 12 entries on 10-02/03, none near 17:45Z,
  none from this session's directories. The tool call took 6 s end-to-end (L350 17:45:08 → L351 17:45:14), so it was
  not a 20 s hook timeout. Why the guard allowed it is **unexplained** — the condition has passed (the fanout-fixes
  worktree is deleted), so this lane cannot reproduce it.

**The load-bearing new defect — the detector built to catch exactly this reports it as "working":**
`mise run command-audit` over this session (`dotfiles-setup command-audit --limit 5 --output /tmp/ro-998r/audit.md`, rc=0):
`0 bypass, 8 guard-denied`, and the "guard denials" table lists the L350 command under `zsh_equals_separator`.
Cause, `python/src/dotfiles_setup/command_audit.py:337`:

```python
if not (isinstance(result, dict) and "stdout" in result):
    continue
```

An executed command that exits non-zero is stored as a **string** `toolUseResult` beginning `Error: Exit code N\n<stdout>`
(L351: type `string`, `"Error: Exit code 1\nOPEN\n…"`; L2155: `"Error: Exit code 128\nfatal: …"`), so it is counted as
"not executed" → `blocked`. A real guard denial is `Error: PreToolUse:Bash hook error: <reason>` (21 such strings across
the 80 newest dotfiles transcripts, `/tmp/ro-998r/deny.py`); executed-non-zero strings: 72 in the same set. The 07-14
probe in the docstring sampled no non-zero executions, and the test fixture (`tests/test_command_audit.py:89-105`
`_result`) models only `dict` (ran) vs `"Error: Use \`mise run ship\` — …"` (refused).

The `zsh_equals_separator` class **always** exits 1, so every evasion of that rule is structurally invisible to the
bypass alarm — a probe that can only say "working" (`probes-need-a-control-arm.md` rule 2).

**Control arm.** Both shapes observed on disk: string-executed (L351, L2155) vs string-denied
("PreToolUse:Bash hook error", 21 hits); dict-executed (L2159 `object`). The guard itself discriminates: the L350
command → deny; `ls; echo '===='` → no match.

**Disposition: FIX-NOW** (spec for a lane; this lane is read-only):
- `python/src/dotfiles_setup/command_audit.py` `_executed_ids`: also add the id when
  `isinstance(result, str) and result.startswith("Error: Exit code ")`.
- `tests/test_command_audit.py`: new arm `_result(uid, executed="nonzero")` producing
  `"Error: Exit code 1\n(eval):1: ===== not found"`; assert `classify(...) == "bypass"` for an `echo ======` command dated
  after `_V10`; keep the existing refused-string arm asserting `blocked`. Fail arm: revert the one-line change → the new
  test must fail.
- **PLAN** (task_plan.md text): `- (S1003f-1) Guard did not deny L350 \`echo ======\` in session 998ab91b (17:45Z 10-02,
  project dir fanout-fixes-20261002, no fail-open logged, 6 s round trip). After the command_audit fix, re-run
  \`mise run command-audit -- --limit 80\` and triage every newly surfaced bypass; if more than this one appear, the
  wrapper needs a per-invocation heartbeat so "never ran" is distinguishable from "allowed".`

### F2 — MED — "I wrote it" sent in the same batch as the write; 7 times, the first one failed

**Claim.** The watcher announced an inbox append to Ray (SendUserMessage) in the same parallel tool batch as the append
itself, before its result existed. Detector `/tmp/ro-998r/race.py` (a Send* tool_use issued while a Bash/Write/Edit
tool_use has no result yet):

| batch | write | announce | write result |
|---|---|---|---|
| 1 | L2749 `cat >> …/handoff-inbox/watch.md <<EOF … echo rc=$?` | L2750 "I wrote this tick's alert to `.agent/plans/handoff-inbox/watch.md`" | **L2751 REFUSED** (worktree isolation); L2752 "Message delivered" |
| 2 | L2837 | L2838 "I've appended a reminder" | L2839 rc=0 |
| 3 | L2900 | L2901 | L2902 rc=0 |
| 4 | L2933 | L2934 | L2935 rc=0 |
| 5 | L3848 | L3849 | L3850 rc=0 |
| 6 | L4240 | L4241 "I logged both to the handoff inbox" | L4242 rc=0 |
| 7 | L4330 | L4331 | L4332 rc=0 |

The session noticed the first failure (L2778: "The first write failed, but the second went through, so my earlier message
saying it was written is now accurate") and then repeated the pattern six more times. Batches 2-7 were true by luck.

**Warnings that failed:** `verify-before-advancing.md` ("Done means verified done … not an assumed outcome");
`notepad-enforcement.md` rule 4; memory `feedback_background_task_notification_can_lie`.

**Control arm.** The detector does not fire on correctly ordered claims: L4693 ("push in progress", the push L4692
pending) is flagged but its text does not claim completion, and L848/L852 ("report is PUSHED") come after the L845
`ls-remote` result and are not flagged. 11 hits total, 7 are announcements of a pending write; the other 4 (L4199,
L4693, L4843, L4844) carry no completion claim about the pending call.

**Mechanical check feasibility.** A PreToolUse hook on `SendUserMessage` cannot see sibling calls in the same batch, so
no hook can enforce ordering. The feasible machine fix is to remove the separate claim:

**Disposition: PLAN** (task_plan.md text): `- (S1003f-2) Watcher/summarizer inbox writes: the tick (successor
\`.agent/state/watch/tick.py\`, and #1551's summarizer module) performs the handoff-inbox append itself and prints
\`INBOX path=<p> lines=<n> rc=<rc>\`; alerts quote that line verbatim and are sent only in a LATER turn than the tick.
Test in the #1551 module: an unwritable inbox path yields rc!=0 and no "appended" text in the rendered alert.`

### F3 — MED — 14 worktree-isolation refusals: the watcher entered a branch worktree while its job writes the shared checkout

**Claim.** At L396 the watcher called `EnterWorktree` into `lane-completion-20261002` to write its research report. From
then on every operation touching the shared checkout or another worktree is refused by the harness: L403 (`grep` of
KB docs via `$D`), L435/L439 (`claude logs` loops), L948 (`git rev-parse` of lane branches), **L2751** (inbox append,
see F2), **L2757** (Write tool: "Edit the worktree copy of this file instead of the shared-checkout path"), L4442 (`cp` to
the inbox). This lane, a subagent of the same session, was refused **7** more times on commands that never touch git:
`ls $(dirname $T)`, two python heredocs, a `for n in …; sed -n ${n}p` loop, `cd <main> && git log` (correct refusal),
`grep -rn … $CC/`, a `jq` loop over transcripts.

**Two sub-findings.**
1. **Upstream regression candidate.** CC changelog (`knowledge-base/sources/agent-harness-docs/docs/claude-code/changelog.md:741`,
   2.1.273): "Fixed worktree-isolated sessions refusing Bash loops, `$VAR` reads, `"$(…)"` and heredocs that never touch git
   as 'too complex to verify'". Installed `claude --version` = 2.1.288; the same shapes are refused here.
2. **The session bypassed the refusals instead of fixing the cause.** After L2757 refused the Write tool, L2774 wrote the
   same file with `cat … >> <shared checkout>/.agent/plans/handoff-inbox/watch.md; echo "rc=$?"` (allowed); after L4442
   refused `cp …; echo rc=$?`, L4446 re-ran the bare `cp` (allowed). The discriminant in both pairs is the unquoted
   `echo rc=$?` tail (L2774's quoted `"rc=$?"` passed; L623's unquoted one passed because it targeted the worktree) — the
   "unquoted rc=$? guard refusals" in the candidate list are this class, not `hook_guard`. Dropping the rc capture to get
   past it (L4446) also dropped the file-captured rc evidence.

**Warnings that failed:** none in the repo name the cause. `parallel-work-split/SKILL.md:141` tells LANES not to
EnterWorktree; nothing tells a watcher/coordinator whose duties write `.agent/plans/handoff-inbox/` in the main checkout.
The successor watcher was launched correctly from the main checkout (`agent-arun-the-same-…jsonl` command 4:
`cd …/dotfiles && claude --bg -n dotfiles-20261003.watch …`).

**Control arm.** A correct refusal is in the same set (`cd <main checkout> && git log` → refused naming the shared
checkout), and a same-shape command inside the worktree passed (L623, L4684 `git add` in the worktree).

**Disposition:**
- **PLAN** (task_plan.md text): `- (S1003f-3) Watcher/coordinator rule: a session whose duties write the shared checkout
  (handoff-inbox, task_plan.md, lane census) never calls EnterWorktree; branch work it owns goes to a \`git worktree add\`
  tree driven by \`git -C <tree>\` from the main checkout, or to a lane. Add to the watcher brief
  (\`.agent/state/watch/WATCHER.md\`) and to \`parallel-work-split/SKILL.md\` next to line 141; #1606's guard denies
  EnterWorktree in a session named \`*.watch\`/\`*.coordinator\`.`
- **RAY RULING:** (a) file the 2.1.288 refusals of git-free heredoc/`$VAR`/loop commands upstream as a regression of the
  2.1.273 fix (repro: this lane's `ls $(dirname $T)` and `grep -rn x "$CC/"` in an EnterWorktree'd session); (b) whether
  re-issuing a harness-refused shared-checkout write through a narrower Bash spelling (L2774, L4446) is acceptable or must
  be denied — no hook can see a harness refusal, so this needs a ruling, not a check.

### F4 — MED — the second research sweep ran a pre-#1581 workflow 25 s after reading the post-#1581 one

**Claim.** L4529 (16:41:00Z 10-03): `git show origin/main:.claude/workflows/research-sweep-run.js > …/rsr-main.js` and
grepped its phases. L4551 (16:41:24Z): `Workflow research-sweep-run` launched — loaded from the session's worktree, whose
copy is `3a861923` (2026-10-01) while `origin/main` has `9307dcb9` (#1581, merged 2026-10-03T02:52:57Z); worktree
merge-base `aeeb9164`. The report's "Retrospect is missing" claim was stale (side-agent note L4720; addendum commit
`0ac9bacd`).

**Warnings that failed:** `verify-before-advancing.md` § "Validate against the latest branch code"; the session itself
had reported "lane C has merged (#1581)" at L2620 (02:56Z) — 14 h before the sweep.

**Control arm.** The first sweep (L481, 17:47Z 10-02) ran from the same worktree but before #1581 existed, so it is not
an occurrence. `git log -1 HEAD -- <workflow>` = `3a861923` vs `origin/main` = `9307dcb9` discriminates.

**Disposition: MACHINE** (PLAN row for a lane): `- (S1003f-4) research-sweep-run preflight: before phase 1 run
\`git rev-parse HEAD:.claude/workflows/research-sweep-run.js origin/main:.claude/workflows/research-sweep-run.js\` (after a
bounded \`git fetch\`); when the blobs differ and HEAD's is an ancestor-side version, add \`stale-workflow\` to
\`statuses\` (never \`complete\`) and print both blob ids. Test in \`tests/test_workflows_js.py\`: a fixture repo whose
origin/main copy differs → status contains \`stale-workflow\`; identical → absent.`

### F5 — MED — coordinators died twice with no successor

| # | anchor | what |
|---|---|---|
| 1 | L911-L937 (19:21Z 10-02) | `dotfiles-20261002.coordinator` vanished; lane A blocked with nobody to hand to; watcher re-routed to `dotfiles-20261001.000` |
| 2 | L2750 (03:32Z 10-03) → L4331 (16:14Z) | `dotfiles-20261002b.coordinator` (7541ae79) `done`/unreachable; 30-min inbox re-alerts until Ray's morning; ~13 h with nothing shipped (L3723 "stalled since about 22:30") |

**Root causes already recorded:** `task_plan.md:2511` — our `dag-tick` LaunchAgent ran `claude stop` on DONE nodes with a
live pid (an idle coordinator reads as done); 7541ae79 also died at context limit and never loaded #1583's hook
(L4199: restarted 44 s before the plugin reached the checkout).

**New datum — the code fix is not on main.** `task_plan.md:2511` says "code fix (A) DONE = log-only with the STOP
removed", but `origin/main:python/src/dotfiles_setup/dag_tick.py:1384` still runs `[ctx.claude_bin, "stop", node_id]`
(last change #647). The fix is `060de30b` ("never stop a DONE session; it may be an idle coordinator") on the unmerged
branch `feat/session-autostart-no-prompts`. The only live mitigation is `launchctl disable` (`task_plan.md:2517`), a
host state no gate checks.

**Control arm.** `git branch -a --contains 060de30b` → only `feat/session-autostart-no-prompts`; the same grep on
`origin/main` finds the stop call, so the probe sees both states.

**Disposition: PLAN** (task_plan.md text): `- (S1003f-5) Ship 060de30b (feat/session-autostart-no-prompts) BEFORE any
re-enable of dev.mise.dotfiles-dag-tick; its test must assert dag_tick never invokes \`claude stop\` for a DONE node
(fail arm: restore :1384). Add a doctor check that reports dag-tick loaded while origin/main dag_tick.py still contains
the stop call. The supervisor row (task_plan.md:2536) stays the long-term fix; the watcher's coordinator auto-launch
(scratch tick.py, now .agent/state/watch/tick.py) moves into #1551's module with a test.`

### F6 — MED — EnterWorktree permission prompt recurred for a lane

**Claim.** L2645/L2646 (03:01Z 10-03): `saved-searches-1502` (8d6e7252) parked on the EnterWorktree root-relocation prompt;
it stayed blocked until the morning (still listed at L3892, 13:31Z). L2651: "the same worktree-entry prompt that parked
7 lanes this morning."

**Warning that failed:** `.claude/skills/parallel-work-split/SKILL.md:114` and `:141` ("CWD: you were launched inside
your worktree. Do NOT … call EnterWorktree"). Prose in a brief cannot stop a launcher that starts the lane elsewhere.

**Disposition: PLAN exists** — #1606 "coordinator EnterWorktree outside .claude/worktrees/ prompts" (OPEN), ruled
`task_plan.md:2535` option (a) `.claude/worktrees/` + guard. Gap: the title scopes it to the coordinator. Add to #1606:
`guard covers every \`*.lane-*\`/feature lane launch, not only coordinators; test: a launch command whose cwd is outside
the lane's worktree is denied`.

### F7 — LOW — session ids read as SHAs

**Claim.** L2143 reported "devcontainer-cap (9652109a) and host-load (53b8d22d)"; L2152 the coordinator read them as
head SHAs and asked for a probe fix. L2158 `git for-each-ref` (control: `docs/lane-completion-protocol 1dcf0d4b`, a
known pushed SHA) and L2170 relabelled `session=` / `head=` in the scratch tick.

**Disposition: PLAN** (task_plan.md text): `- (S1003f-7) #1551 summarizer output contract: every hex id is labelled
(\`session=\`, \`head=\`, \`pr=#\`); a test renders a row and asserts no bare 8-hex token appears.` (Single occurrence;
no prior warning; low cost.)

## Candidate refuted — pushed SHA claimed before `ls-remote`

Not found. Every "pushed" claim follows an `ls-remote` result: L845 (`push_rc=0` + `1dcf0d4b…`) precedes L848/L852/L864;
L4812 (`push_rc=1`, origin still `1dcf0d4b`) precedes L4843 "push FAILED … origin is still at 1dcf0d4b"; L4693/L4707 say
"push in progress"; 0ac9bacd was always "local"/"held" (L4866, L4987, L5032). Control: the same grep
(`ls-remote|git push` USE lines + `pushed|on origin|landed` claims) finds all four pushes (L722, L771, L818, L4692) and
their checks, so it sees the shape when present.

## Lane self-observation

This lane repeated memory `feedback_zsh_no_word_splitting` once (`for r in "2837 2845" …; set -- $r` — zsh passed one
word; rc=1, no data lost) and was itself refused 7 times by the F3 isolation class.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — PR #1581 merge time, issue #1606 state, `origin/main` blobs of `command_audit.py`, `dag_tick.py`, `research-sweep-run.js`, `tests/test_command_audit.py`
