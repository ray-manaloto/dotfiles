# Session audit 2026-09-27 — dismissed errors and repeated mistakes (Brief M)

Brief: `docs/research/kb/reports/agents/session-2026-09-27-agent-briefs.md` § Brief M.
Session: `1f389314-77c7-44e8-85de-4f23b3f73c0a` (dotfiles-20260926.001). Status: COMPLETE (audit lane
a7a0106471bf3d03a, 2026-09-27). This lane is read-only except for this file. `findings.md` and `progress.md` were NOT
written; the coordinator persists them.

## Summary — 9 dismissed or unrecorded findings

| # | Sev | Finding | Kind | Disposition |
|---|---|---|---|---|
| F1 | HIGH | `bounded-wait … state = MERGED` cannot fail fast. Two waits burned about 3 h 50 min each after CI had already gone red. | repeat ×2, unrecorded | FIX-NOW: file the issue. PLAN: `/to-spec` → `/to-tickets` |
| F2 | HIGH | `ship` skips `verify-apt-pins` when a diff touches only locks or `shared.toml`. #962 named this gap on 2026-09-03 and was closed without fixing it. It recurred on #1398 and #1400. | repeat of a closed issue | FIX-NOW: widen the trigger (exact diff below) |
| F3 | MED | Every per-turn pwf plan injection is spilled past the 10,000-char hook cap. The model sees a 2 KB preview of the stale 2026-09-14 Goal and never sees Current Phase. | measured now; earlier marked UNVERIFIED | FIX-NOW: comment on #1360. PLAN line |
| F4 | MED | A main-session `cd` moved into knowledge-base 7 times, and the KB plan was injected. task_plan item 27(b) said "File NOW" on 2026-09-26, but no issue exists. | repeat; recorded remedy not done | FIX-NOW: file the issue |
| F5 | MED | Two zsh traps fired 9 times across 3 transcripts: `=`-expansion 5× and NOMATCH 4×. #1388 is still unbuilt, and NOMATCH is recorded in memory only. | repeat | FIX-NOW: comment on #1388. PLAN: `/grilling` (native `setopt` option) |
| F6 | LOW | Cold-reviewer a2b1898d stopped at `maxTurns: 60` and was never resumed. Its report still says "IN PROGRESS", and the branch shipped on the partial review. | unrecorded | FIX-NOW: annotate the report. PLAN line |
| F7 | LOW | Two CLIs blocked on inherited stdin: `hk run pre-push --plan` hung until killed, and `claude -p` stalled 3 s. Both were fixed ad hoc with `< /dev/null`. | repeat ×2, unrecorded | PLAN: one line on #1405 and item 13 |
| F8 | LOW | The KB review record was trimmed to get past gitleaks. The full 305 KB transcript now exists only in the session scratchpad. This is the KB#506 class, and the recurrence is unnoted. | recurrence of a recorded class | FIX-NOW: comment on KB#506 |
| F9 | LOW | Renovate has never opened a PR for the stale `curl` or `libsqlite3-dev` apt pins, so pin decay went undetected until a cold build. | unrecorded; cause UNVERIFIED | PLAN: investigate (paired with F2) |

## Method

- **Main transcript:** 4,763 JSONL lines and 547 tool calls, scanned with a Python extractor. The extractor flagged
  every `is_error` result, every result line matching
  `rc=[1-9]|exit code [1-9]|ERROR|error|WARN|DRIFT|denied|FAIL|fatal|Traceback|not found|timed out|blocked|refused|failed`,
  every hook attachment, every `<task-notification>`, and every `system` notice. `L<n>` = the JSONL line of the
  `tool_use` record.
- **Subagents:** the same extractor ran over the 5 prior subagents: ab04f1eb (research), af59a211 (codex-sol
  implementer), a4d92c52 (codex-astra implementer), aae1f4e2 (premise-verifier) and a2b1898d (cold-reviewer). The 4
  concurrent audit lanes M/N/O/P were excluded as live.
- **Session cwd:** tracked through every record's `cwd` field. Each pwf injection was classified by `Plan-SHA256` and by
  whether it was spilled.
- **Background commands:** every background command was mapped to the log its `echo "rc=$?" >> LOG` wrote. The log's
  real rc was read, not the notification's.
- **Cross-checks for each candidate:**
  - `task_plan.md`, at the line numbers of this audit (the coordinator edits it live, so numbers can shift by about 2);
  - `findings.md`;
  - the memory dir;
  - `gh api /search/issues` on both repos;
  - `gh issue view` on the named issues.
- **Graphify** was not used. The transcripts are outside the repo corpus, so the graph cannot answer this brief.
- **Control arms for the "unrecorded" verdicts:**
  - The issue search returns known-present #1388 for `expansion separators`, and returns #1190/#1163 for
    `bounded-wait`.
  - A body scan of #1351–#1360 returns `attestation`=3 in #1352 and `plan`=8 in #1360, and 0 cap terms.
  - The PR search for `gnupg` finds #969, and the same search for `curl` or `libsqlite3` finds 0.
  - The memory grep for `no matches found` hits 2 files.

## Findings

### F1 — HIGH — `bounded-wait` on `state = MERGED` cannot see a failed check; ~7 h 40 min burned, twice

**Claim.** The canonical merge wait, `mise run bounded-wait -- --deadline N --cmd 'test "$(gh pr view <n> --json state
--jq .state)" = MERGED'`, has no failure predicate. `WaitRequest` (`python/src/dotfiles_setup/bounded_wait.py:27-33`)
holds exactly one success condition. A PR whose required check fails stays OPEN/BLOCKED, so the wait runs to the full
deadline.

**Evidence.** Wait start and end are the tool_use and notification timestamps. Failure time is `gh pr checks
--json completedAt`.

| PR | Wait start | First failed check | Wait end | Dead time |
|---|---|---|---|---|
| #1398 | L3412 08:11:49Z | `lint` 08:13:27Z | L3434 12:11:52Z, rc=124 | about 3 h 58 min |
| #1400 | L3842 12:41:34Z | `base-prep` 12:52:30Z | L4340 16:41:42Z, rc=124 | about 3 h 49 min |

On the third wait, the coordinator hand-rolled a partial predicate:

- L4505 is `wait-baseprep`, a `gh pr checks … select(base-prep) pending` count.
- L4499 says "This time I'll also check the build's progress partway through".

The lesson was learned inside the session but not recorded. `.claude/rules/gh-cli-watch.md:32-33` and
`.claude/rules/mise-tasks-only.md:24` both prescribe the fail-blind pattern.

**Control.**
- `gh pr checks --help` does offer a native `--fail-fast` (line 18 of its help), but it is guard-denied with `--watch`
  (`do-not.md` #6).
- `grep -n 'bounded-wait' task_plan.md findings.md` finds only M-1, which is about `--file-contains`, and item 29(c)
  (`kb-land`).
- The issue search for `bounded-wait` returns #1190/#1163/#1180, none about fail-fast.

**Disposition.**
- **FIX-NOW:** file a dotfiles issue titled "bounded-wait merge wait cannot fail fast: a red required check burns the
  whole deadline (2× ~3h50m on 2026-09-27)". The body is the table above plus `bounded_wait.py:27-33`.
- **PLAN**, for task_plan.md under the 2026-09-26/27 owed list:
  `(S27-5) Merge waits must end on a red required check. Pick ONE mechanism: (a) \`bounded-wait --abort-cmd '<pred>'\`
  (rc=1 when the predicate holds), (b) a typed \`mise run pr-await -- <n>\` returning MERGED | CHECK_FAILED | TIMEOUT
  from \`gh pr checks --json bucket\`, (c) allow \`gh pr checks <n> --watch --fail-fast --required\` under an outer
  deadline, re-checked against the API \`conclusion\`. Then update gh-cli-watch.md:32 and mise-tasks-only.md:24 in the
  same PR. Needs \`/to-spec\` → \`/to-tickets\` (one design choice, no grilling).`

### F2 — HIGH — `ship` skips `verify-apt-pins` for lock-only and `shared.toml` diffs; named in #962 and still open in code

**Claim.**
- `changes_apt_pin_inputs` (`python/src/dotfiles_setup/pr.py:283-289`) matches only `_APT_PIN_PATTERNS` =
  `mise-system.toml` and `Dockerfile` (`:175-178`).
- `BASE_INPUT_PATTERNS` (`:132-142`) additionally holds `mise-system.lock`, `mise-runtime.{toml,lock}`, `shared.toml`,
  `hk-*.pkl` and `docker-bake.hcl`.
- Any of those triggers a cold base build, and a cold base build re-resolves every apt pin, which decay as Ubuntu
  supersedes them.

**Evidence.**
- #1398 and #1400 both touched only `shared.toml` plus `mise-{system,runtime}.lock` (`gh pr view --json files`).
- #1400's base-prep failed on all three arches, per L4366:
  - `E: Version '8.18.0-1ubuntu2.5' for 'curl' was not found`;
  - the same error for `libsqlite3-dev 3.46.1-9ubuntu0.2`.
- The local probe reproduced it in 60 s: L4373, `verify-apt-pins` rc=1.
- **#962**, closed and filed 2026-09-03, states verbatim: "`ship` only runs this gate when a diff touches
  `mise-system.toml` or the Dockerfile, so branches that change only the *locks* pass locally and still trigger a base
  rebuild." It was closed by the pin bump (#969) alone, and `pr.py` was not changed. `git log -3 -- pr.py` shows no
  trigger change since then.

**Control.** `verify-apt-pins` passed after the bump (L4429, "PASS: all 66 pinned packages", with the named pins
failing first). The g8 ship log shows the gate ran once `mise-system.toml` changed.

**Disposition.** FIX-NOW, a small, reversible code change with a test:
- In `pr.py`, replace the `_APT_PIN_PATTERNS` tuple with `_APT_PIN_PATTERNS = BASE_INPUT_PATTERNS`.
- Update the `:164-174` comment: "every base input triggers a cold rebuild that re-resolves every pin, and pins decay
  with time, not only with diffs".
- Add a `tests/test_pr.py` case: a diff of only `.config/mise/conf.d/shared.toml` → `verify-apt-pins` is in
  `select_gates`.
- Fail arm: revert the tuple → the new test fails.

### F3 — MED — pwf per-turn plan injection never reaches the model past a 2 KB preview

**Claim.** Claude Code caps each hook output value at 10,000 characters. It spills longer output to a file and gives
the model a preview plus a path (`$CC/hooks.md:941`, `:1023`).

**Evidence.**
- In this session, 42 of 65 planning-with-files injections were `Output too large (19.4KB|19.9KB)` spills. The other
  23 were 16 `PLAN TAMPERED` notices and 7 inline.
- The preview shows only the first 2 KB: "# Task Plan: quantified dependency + graph currency (supersedes the
  2026-09-09 program)", which is the 2026-09-14 Phase 1 text.
- The payload's `## Current Phase` sits at line 179 of the spilled file, for example
  `tool-results/hook-046fba2a-…-additionalContext.txt`, with `bytes=19297 truncated=true`.
- So the active phase was never injected. The plan was re-read by hand (L288, L294) instead.

**Prior record.** `docs/research/kb/reports/agents/context-injection-hooks-2026-09-23.md:155-159` says the tail "likely
reaches the model only as a file path. UNVERIFIED which side of the cap the current plan lands on." This session
verifies it.

**Control.**
- The body scan of #1351–#1360 finds 0 hits for `10,000|10000|preview|spill|additionalContextLimit`.
- The control terms `attestation`=3 (#1352) and `plan`=8 (#1360) prove the scan reads the bodies.

**Disposition.**
- **FIX-NOW:** comment on #1360 (D9, plan migration) with the 42/65 measurement. Add the acceptance criterion: "the
  injected plan block is ≤ 10,000 chars, and `## Current Phase` falls inside the first 2 KB of what the model receives".
- **PLAN**, for task_plan.md:
  `(S27-6) pwf injection exceeds Claude's 10,000-char hook cap on every turn (42/65 spilled 2026-09-27); the model sees
  only the stale Goal. Fix inside #1360/D9 (archive the program plan so the injected block fits) — no new ticket.`

### F4 — MED — main-session `cd` into knowledge-base, 7×; the recorded "File NOW" was not done

**Claim and evidence.**
- The session cwd moved into knowledge-base at records L105, L330, L440, L483, L508, L542 and L812. The commands were
  L104, L314, L329, L439, L482, L507, L541 and L811, each a bare `cd …/knowledge-base &&` or `cd ../knowledge-base &&`.
- At L586, pwf injected the **knowledge-base** plan (`Plan-SHA256 965e724c`, "the 2026-09-12 session-review round")
  into a dotfiles turn.
- `task_plan.md:918-923` (item 27(b), from 2026-09-26) reads: "File NOW, not only list … a guard on a main-session `cd`
  into another repo."

**Control.**
- The issue searches `cd knowledge-base guard` and `cwd another repo` return no such issue, although they do return
  #1397/#916/#1020.
- The known-present #1388 is found by the same route.
- The `cd $K` inside background commands (L1161, L1276) did NOT move the session cwd, as the harness notice says.

**Disposition.** FIX-NOW: file a dotfiles issue titled "hook_guard: deny a main-session `cd <sibling repo>` (use `git -C`,
or a subshell `( cd … )`); 7× on 2026-09-27, 6× on 2026-09-26, pwf injected the KB plan". The acceptance arms are:
- `cd ../knowledge-base && ls` → deny;
- `(cd ../knowledge-base && ls)` → allow;
- `git -C ../knowledge-base log` → allow.

### F5 — MED — zsh `=`-expansion and NOMATCH: 9 aborted commands across 3 transcripts

**Evidence.** Counted as `(eval):1:` messages, each stored twice in the JSONL, so the counts are halved:

| Trap | Main transcript | Research lane ab04f1eb | Cold-reviewer a2b1898d |
|---|---|---|---|
| `=`-expansion | L289 (`==== not found`) and L559 (`=== not found`) | L48 (`==== not found`) | 2× (`= not found`, including L167) |
| NOMATCH | L127 and L1938 | 1× | 1× (L71) |

- This audit lane also hit `=`-expansion once. That makes 5 `=`-expansion hits in all, alongside the 4 NOMATCH aborts
  above.
- The L1938 NOMATCH was consequential. It aborted the `grep -ln HK_PKL_BACKEND …` probe for the variable's origin, so
  that probe returned nothing. The conclusion survived only because a second route, the login-shell probe, answered.

**Record.**
- #1388 (`=`-expansion guard) has been OPEN and unbuilt since 2026-09-25c.
- NOMATCH is recorded only in memory (`project_session_2026-08-08.md:94`, `project_session_2026-09-14-d.md:104`), with
  no guard and no ticket.

**Disposition.**
- **FIX-NOW:** comment on #1388 with these counts, and widen its scope to NOMATCH.
- **PLAN** (`/grilling`, one question for Ray, since it touches user-level shell config):
  `(S27-7) zsh traps (=-expansion, NOMATCH) aborted 9 commands on 2026-09-27. Native option: \`setopt NO_EQUALS
  NO_NOMATCH\` in the shell the Bash tool snapshots (user-level zsh config) removes both classes with zero guard code;
  alternative: build #1388 and add a NOMATCH rule. Ray rules which.`

### F6 — LOW — a truncated cold review shipped as if complete; its report still says IN PROGRESS

**Evidence.**
- L2932: `Agent "Cold review hk v2 migration range" stopped at its 60-turn limit (partial result; SendMessage to task-id
  to continue)`, where `.claude/agents/cold-reviewer.md:7` sets `maxTurns: 60`.
- The coordinator relayed 4 findings (L2947) and asked F3 (L2949), but never sent it a `SendMessage`. The transcript
  mentions the ID at L2910/L2930/L2932 plus the handoff census only.
- `cold-review-hk-v2-migration-2026-09-27.md:8` still reads `Status: IN PROGRESS`.
- The unreviewed remainder went into #1403. Brief O's squash review (`cold-review-1403-squash-2026-09-27.md`)
  compensates after the fact.

**Control.** A grep of `task_plan.md`/`findings.md` for `turn limit|60-turn` returns 0 hits. No prior dismissed-errors
report records a cold-reviewer turn-limit stop.

**Disposition.**
- **FIX-NOW:** append a decision annotation to that report. Do not edit the verbatim body. Text: `> Annotation
  2026-09-27 (audit): the lane stopped at maxTurns 60 and was not resumed; findings F1-F4 are partial. Superseded for
  the landed diff by cold-review-1403-squash-2026-09-27.md.`
- **PLAN:** add one line to the `codex-sdlc-team` skill's review-tier section: "a reviewer notification that says
  'stopped at its N-turn limit' is a partial review. Resume it with SendMessage before shipping, or record the gap."

### F7 — LOW — headless CLIs blocking on inherited stdin

**Evidence.**
- Research lane L353: `hk run pre-push --all --plan` hung. It was auto-backgrounded at 120 s, then stopped with
  `TaskStop` and a hand-rolled `pkill -f` (L361, L363, not `mise run reap`), and re-run with `< /dev/null` (L363).
- Main L1166: `claude -p` printed "Warning: no stdin data received in 3s". It was re-run with `< /dev/null` at L1276.
- Neither `task_plan.md` nor #1405 names stdin. #1405 covers the background-wait ceiling only.

**Disposition.** PLAN: add `< /dev/null` to the #1405 `kb-workflow-run` argv spec. Add one sentence to item 13 / #1056:
"headless CLIs inherit the Bash tool's stdin; `hk run <hook> --plan` for pre-push/commit-msg blocks forever on it."
No separate ticket.

### F8 — LOW — a verbatim KB review record was trimmed to pass gitleaks (KB#506 class, recurrence unnoted)

**Evidence.**
- kb-ship #1 was refused on a dirty tree. The two untracked cclint report directories were stashed (L4119).
- kb-ship #2 failed `gitleaks` on `.agent/kb/review/reports/review-<sha>-cold.md`. The codex lane's 305 KB transcript
  quoted test-fixture tokens (L4151-L4157).
- The coordinator overwrote that report with only the lane's final verdict (L4177). The full copy now lives only in
  `…/scratchpad/kbhk/review-<sha>-cold.full.md`, a session-temporary path.

**Record.** KB#506 is open, and its 2026-08-25 comment documents exactly this file shape (`review-9b8c5e9b456f-cold.md`).
This recurrence and the trim are not noted there.

**Disposition.** FIX-NOW: comment on KB#506. Name the recurrence and the fact that the fix rewrote a review record. Ask
that the KB review writer store transcripts outside the `gitleaks dir .` scan, or redact fixture tokens at write time.

### F9 — LOW — Renovate never opened a PR for the decayed apt pins (cause UNVERIFIED)

**Evidence.**
- `renovate.json:65` and `:191-196` declare a `deb`-datasource regex manager for every `[bootstrap.packages]` pin.
- Both `curl` and `libsqlite3-dev` went two Ubuntu revisions stale, and no PR ever proposed them.
- The previous decay, gnupg in #962, was also fixed by hand in #969.

**Control.** `gh pr list --state all --search 'curl in:title'` and `'libsqlite3 in:title'` both return 0. The same
search for `gnupg` returns #969.

**Disposition.** PLAN, paired with F2:
`(S27-8) Renovate's deb manager (renovate.json:191-196) produced no PR for curl 2.5→2.7 or libsqlite3-dev 0.2→0.3 before
they broke the cold build; run \`mise run renovate-dryrun\` and read what it extracts for those two deps.` No grilling.

## Recorded, fixed or handled — NOT findings (listed for completeness)

| Event | Where | Disposition |
|---|---|---|
| SessionStart `[currency]`: graphify has no exact pin; doppler last checked 2026-08-12; graphify upstream never recorded | JSONL L10 | RECORDED task_plan.md:719-722 cluster, item 26 (startup noise → one `/grilling`) |
| DRIFT listing-budget: `antigravity-delegate` is 1789 > 1536 | L10 | RECORDED task_plan.md:719 (M-3) |
| DRIFT graphify PATH 0.9.69 != locked 0.9.65 | L10 | RECORDED S27-2 (task_plan.md:998), #1397 item 5, #1344 |
| Notice `aggregated-research: hooks.json: unknown key "$comment" ignored` | L12 | RECORDED task_plan.md:897 (e) F11 |
| 9 notifications said "completed (exit code 0)" over a real non-zero rc: ship4 L1848 rc=1; cr-attest L1614 (timeout shim); wait1398 rc=124; wait1400 rc=124; kb-ship L4084 and L4120 rc=1; kb-land 823 rc=1; gate matrix L2828 (pytest rc=1); KB gates L3984 | notifications L1862, L1624, L3434, L4340, L4105, L4143, L4233, L2848 | HANDLED: each one was read from the log `rc=`. Class RECORDED #1056 §3 and task_plan.md:1150/1948/1956 |
| `timeout` shim: L1614 in dotfiles → `mise ERROR No version is set for shim: timeout` (L1621). L1161 and L1276 resolved because they ran under `cd $K` (KB pins coreutils) | L1614/L1629 | RECORDED #1056 §2, S27-2, #1397 item 4, #1405, item 13 (task_plan.md:856) |
| Stale `HK_PKL_BACKEND=pkl` plus global hk hooks → `tests/test_branch_guard.py` failed 3× (L1865, L1900), and `Error: Failed to load configuration` (L1908) | ship4 | FIXED: conftest `isolated_git_config` (#1403); `unset HK_PKL_BACKEND`. RECORDED #1397 item 3, S27-2 |
| `PLAN TAMPERED — injection blocked` on 16 prompts (L953 to about L1804) after `task_plan.md` edits | UserPromptSubmit | FIXED #1395 (attestation made agent-runnable, Ray) |
| Graph `stale` rc=3 (L513), later rc=3 again in both codex lanes (graph built at `9f5bd67a`) | graphify-health | FIXED L518 rebuild; class RECORDED (rebuild-on-currency, #1344) |
| AskUserQuestion quality deny, no citation (L1314) | hook | HANDLED: the guard worked and the re-ask passed |
| Guard deny: gate piped to `tail` (L2713) | hook | HANDLED: the guard worked and the command was re-issued with file rc |
| Deny of `sh …/set-active-plan.sh` (L1534) | permissions | INTENDED arm (control for #1395) |
| `fmt` rc=1 on `doc_refs` (L1539) | own edit | FIXED L1562 (fmt rc=0) |
| pytest 1 failed: `test_graphify_skill` saw an extra `gitconfig` in `tmp_path` (L2850) | own fixture | FIXED L2867 (sibling path); full 3,945 pass (L2894) |
| ruff rc=1 at L2726, L2982, L3008, L3144, L3317 and L3640; `test_doctor` wiring (L3160); `test_lock_shared` ×2 (L3707) | own edits | FIXED in-session, each re-run green before commit |
| #1398 CI `No lockfile URL found for hk@2.3.0 on platform linux-x64 (--locked)` | CI lint | FIXED (lock-shared versioned name plus `lock_integrity` blind spot) in #1403. Root cause (mise 2026.9.8 bare-name lock writes nothing) RECORDED findings.md:2172 |
| Image/CI mise 2026.9.8 vs host 2026.9.14/9.15 (`mise WARN mise version … available`, L3498/L3512) | skew | RECORDED item 29(b) (task_plan.md:927-929), N-F3 |
| `mise WARN … lockfile format version 0; run mise lock --upgrade` (L3491, L3539, L3574) | locks | RECORDED #1058 |
| Container `xh@latest is not in the lockfile` WARN (L3546) | probe artifact | NOT A DEFECT: the probe ran `mise install --locked` in a temp dir, which also reads the chezmoi user-global `xh = "latest"` (`home/dot_config/mise/config.toml.tmpl:51`) |
| `lock-shared` ERROR rc=1 (L3598) | lock-fix | FIXED in #1403 |
| kb-ship `test_guard_codegen` `Rc.NOT_RUN 127` (L4151) | KB#816 | RECORDED KB#816, which has a 2026-09-27 impact comment; restored with `kb-codegen-check` |
| kb-land 823 rc=1: `Verify signed exact-head live evidence`, `couldn't find remote ref refs/heads/graphify-live-evidence` | KB CI | RECORDED KB#824, S27-1 |
| codex lanes: `hook: SessionStart Failed`, 1 of 7 SessionStart hooks in every codex run (11+ logs since 2026-09-16) | codex | RECORDED #884 C-4 (open since 2026-08-31, origin still unidentified; the staleness is worth a nudge) |
| codex: exa OAuth `invalid_grant: Refresh token has been revoked`; `clamping SessionEnd hook timeout to 3s`; `Under-development features enabled: chronicle` | every codex run | RECORDED task_plan item 5 (re-auth), KB#642, deliberate user config |
| codex-sol resume lane: `ERROR: Selected model is at capacity` (lane rc=1) | af59a211 L101 | HANDLED: rerouted to codex-astra (a4d92c52) per the fallback chain |
| codex review lenses ran `-s read-only` and could not run tests (uv cache), 3× (L1676, L3279, L3799) | review | HANDLED: the coordinator ran the tests. RECORDED memory `project_session_2026-09-16d` |
| codex-sol wrapper wrote an unbounded `until … sleep` loop and was guard-denied (af59a211 L52) | wrapper | HANDLED: the guard worked; the wrapper doc prescribes the bounded form (`codex-sol-implementer.md:213-214`) |
| KB codex lane: `Command blocked by PreToolUse hook: Do not hand-chain the gates` (L983) | KB guard | HANDLED: the KB guard worked on a codex lane |
| premise-verifier Glob `Ripgrep search timed out after 20 seconds` ×2 (aae1f4e2 L177, L207) | verifier | HANDLED: it narrowed the path and reported UNVERIFIABLE, not "absent" |
| Research-lane `hk` plans for pre-push/commit-msg rc=1/2 | research | RECORDED in the research report ("need hook args — not compared") |
| `git add task_plan.md` refused because the file is ignored (L683) and `dangling-grep rc=1` (L811) | probes | EXPECTED (task_plan is gitignored; grep no-match was the pass arm) |

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): issues #1397, #1056, #1388, #1405, #1344, #962,
  #884 and #1351–#1360; PRs #1398, #1400, #947 and #969; the issue and PR searches; `pr.py`, `bounded_wait.py`,
  `renovate.json`, rules and task_plan.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): issues #506 and #816, the issue search,
  and `hk.pkl` on `origin/main`.
- [cli/cli](https://github.com/cli/cli): `gh pr checks --help` (local binary), for `--fail-fast`/`--required`.
