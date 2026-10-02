# Session audit — repeat offenders (Brief R) — 2026-10-01c

Audited session: `dotfiles-20261001.000` (`7133045d-9086-4a3f-8fa7-0a4df70f442a`), 2026-10-01T20:38:44Z →
2026-10-02T18:07:47Z. Method: `## Brief R` in `session-handoff-briefs-q-s-2026-09-28.md`. Read-only lane; this file is
its only write. Prior reports cross-referenced: `session-audit-repeat-offenders-2026-09-29b.md` ("09-29b F<n>"),
`-2026-09-29.md` ("09-29 R<n>"), `-2026-09-28.md` ("09-28 R<n>"). Status: COMPLETE (MAIN to L5623; lanes as listed).

## Method and extraction control arm

`/tmp/ro-c/extract.py` pairs every `tool_use` with its `tool_result` across the MAIN `.jsonl` (5625 lines, **558
tool calls**) and the 33 `subagents/*.jsonl` with tool calls (2079 more). Results kept head+tail 1200+1200 chars
(the tail on purpose — 09-29b's lesson). Anchors: `L<n>` = 0-based line of the MAIN `.jsonl`; `<agent>:L<n>` for a
lane. Background-command outputs were read from `tasks/*.output` and the scratchpad logs they redirect to, because
the transcript holds only the notification summary.

## Findings

### F1 — `git push` died rc=141 FOUR times; every wrapper notification read "completed (exit code 0)"; the first was called "transient" and retried unchanged — HIGH (cross-session)

**Occurrences** (all four logs end with `Connection to github.com closed by remote host`):

| # | where | wrapper / notification | real rc (file) |
|---|---|---|---|
| 1 | MAIN L4988 chain `b470k7zxy` → `ship` of `docs/fanout-launch-fixes` | L5190 "completed (exit code 0)" | `scratchpad/ship-docs-fanout-launch-fixes.log:929` `FAIL  ship: git push rc=141` |
| 2 | MAIN L5205 identical re-run `bfdtbpdmw` ("It looks transient", L5206) | L5547 "completed (exit code 0)" | `scratchpad/ship2-docs-fanout-launch-fixes.log:929` `FAIL  ship: git push rc=141` |
| 3 | MAIN L5383 handoff commit+push `bc5slhum4` | L5438 "completed (exit code 0)" | `tasks/bc5slhum4.output:3` `push rc=141` (and `commit rc=1`) |
| 4 | MAIN L5459 handoff re-commit+push `bau4ip6mh` | L5584 "completed (exit code 0)" | `tasks/bau4ip6mh.output:3` `push rc=141` — commit `9d2f202b` never reached GitHub |

Two aggravating shapes in the same window:
- **Read before settled, then claimed done.** L5429 read `bc5slhum4.output` at 17:53:59, *before* the push finished
  (notification 17:54:46) — it saw only `commit rc=1` and never re-read, so `push rc=141` was never seen. L5499 read
  `bau4ip6mh.output` mid-push (`commit rc=0` only). L5493 (17:56:11) briefed the NEW coordinator that the handoff was
  "pushed on branch docs/handoff-2026-10-02", and L5504 told Ray "committed … and the push (pre-push pytest) is
  running" — the push failed at ~18:02 and the session was out of context from L5588.
- **A retry with no change of condition.** #2 is #1 re-run byte-for-byte (L5205 vs L4988 differ only by an added
  `git fetch`), on the same overloaded host — and failed at the same log line 929.

**Root-cause evidence (why it is not transient).** `git push` holds its SSH connection to github.com open while the
`pre-push` hook runs (`hk.pkl:872-893`: `ghcr_publish_prereqs` + the FULL `test-hook-isolated` pytest). `ship` has
already run the same pytest as a gate (`pr.py:581-586` `run_gates` then `git push`), so the pytest runs twice, the
second time with an idle SSH channel. Pre-push pytest in the failing runs took 349-650 s under host load. `ssh -G
github.com` → `serveraliveinterval 0` (keepalives off). Control arm: `closed by remote host` appears in **4 of 4**
rc=141 logs and **0 of 12** other `ship*.log` files from this session (nine reach `ship: OK`/`land: OK`; the others
fail for different reasons, e.g. `ship-ncd2.log:947` `git push rc=1` = non-fast-forward after a rebase) — the probe
discriminates. (Pre-push duration alone does NOT separate them cleanly — `ho-push3` failed at 349 s while some
successful logs show longer pytest runs, though those figures may be land's pytest, not pre-push's; the SSH-idle
mechanism is the likely cause, not a measured threshold.)

**Warnings that failed.** `feedback_background_task_notification_can_lie` (2026-08-30, corrected 2026-09-25: "the
notification reports the LAST command of the wrapper … read the logged `rc=`"); `feedback_read_agent_reports_only_when_settled`
("an incremental report is a MOVING TARGET"); `verify-before-advancing.md` § Evidence discipline ("never a
background-task 'completed' notification's exit code"); `persistence-gate-retry.md` (retry once only after the
signature is classified as environmental — here nobody looked at the signature). Cross-session: 09-29b F4 (an
in-turn poll beside a `completed (exit code 0)` notification); the same memory was written after two 2026-08-30
incidents. HIGH: recurring across sessions, and it left the session's own handoff off GitHub.

**Disposition — MACHINE (two checks + one PLAN row).**

1. *Make the notification true* — `python/src/dotfiles_setup/hook_guard.py`, in `decide_payload` (L1064ff; rules in
   `_RULES` see only the command string, so this one needs the payload): for `tool_name == "Bash"` with
   `tool_input["run_in_background"] is True`, deny when the command contains `$?` inside an `echo`/`printf` and its
   final top-level command is not `exit` — reason: *"A background wrapper's notification reports its LAST command.
   End it with `exit "$rc"` (e.g. `cmd > L 2>&1; rc=$?; echo "rc=$rc" >> L; exit "$rc"`) so 'completed (exit code N)'
   is the gate's rc."* New `Rule`-style `name="background_wrapper_masks_rc"`, `since` = landing date. Test in
   `tests/test_hook_guard.py`: `test_background_wrapper_masking_rc_is_denied` (payload `{"command": "git push > L 2>&1;
   echo \"push rc=$?\"; git log --oneline -1", "run_in_background": true}` → deny) and
   `test_background_wrapper_propagating_rc_is_allowed` (`…; rc=$?; echo "rc=$rc" >> L; exit "$rc"` → allow) plus a
   foreground control (same masking command with `run_in_background` false → allow). Replay: denies L4988, L5205,
   L5383, L5459 verbatim.
2. *Classify the failure in ship* — `python/src/dotfiles_setup/pr.py:588-590`: when `push_rc == 141`, print `FAIL
   ship: git push rc=141 (SIGPIPE — the SSH session was closed while the pre-push hook ran; NOT transient under the
   same load)` and return a distinct rc (e.g. 3). Test in `tests/test_pr.py`: monkeypatch `run_with_fnox` → 141,
   assert the message and rc; control arm rc=1 keeps the generic message.
3. **PLAN** (needs a Ray ruling, recommend option A): `- [ ] S30-push-141: pre-push pytest holds an idle github SSH
   channel for 6-11 min; 4/4 rc=141 pushes on 2026-10-02 logged "Connection to github.com closed by remote host".
   Options: (A, recommended) ship skips the duplicate pre-push pytest it has just run as a gate — via a
   ship-set env the pre-push `test` step honours (NOT `--no-verify`/`HK_SKIP_*`, both guard-denied) and a contract
   that the gate ran on the same HEAD; (B) chezmoi-managed `ServerAliveInterval 30` for Host github.com (user-level
   file, needs Ray); (C) both. Evidence: docs/research/kb/reports/agents/session-audit-repeat-offenders-2026-10-01c.md F1.`

### F2 — post-ship `/code-review` skipped again; the RULED ship gate (2026-09-28) was never built — HIGH (cross-session)

**Occurrences.** MAIN made **0** `Skill` calls of `code-review` / `mattpocock-skills:code-review` across the 11
dotfiles + 3 KB PRs it merged; it launched `cold-reviewer` **6** times (Agent-type count over MAIN). Control arm: the
same Skill scan DOES see `code-review` invocations in lanes (`agent-aaudit-r` L39/L43/L44/L57, `agent-as29-tak`
L537/L599), so a 0 in MAIN is a real absence. The coordinator's "skipped on 7 PRs" figure comes from the
process-compliance lane and is **inherited, not re-derived here**.

**Warning that failed.** `feedback_verify_and_spec_review_before_ship` (2026-09-28: "skipped both on 4 PRs until Ray
asked"; "The durable fix Ray ruled is MACHINE enforcement at `mise run ship`"). `task_plan.md:1257-1271` holds the
ruling and says "NEXT SESSION runs `/grilling` on the ship gate BEFORE any spec" — two sessions later it has not run.
Same class as 09-28 Brief Q.

**Disposition — PLAN (already Ray-ruled; promote it).** Replace the stale row's "NEXT SESSION" with:
`- [ ] S30-ship-review-gate (P0, ruled 2026-09-28, slipped twice; 2026-10-01 shipped 14 PRs with 0 /code-review
calls): /grilling → /to-spec → codex implementer. Gate in python/src/dotfiles_setup/pr.py ship(): refuse to push
unless a review receipt for `git write-tree` of HEAD exists outside the agent-writable path (author-family →
lens: Claude diff → codex review lens, codex diff → Opus cold pass); test tests/test_pr.py::
test_ship_refuses_without_a_review_receipt_for_this_tree + control test_ship_proceeds_with_a_matching_receipt.`

### F3 — `land`/`sync` dirty `mise.lock` with platform checksums; worked around by `git stash` three times, never dropped — MED (cross-session)

**Occurrences.** L4169: `land -- 1526` → `FAIL  land: could not fast-forward local main` with ` M mise.lock`. The
chains at L4988 and L5205 then hard-coded `git stash push -m "mise.lock auto-written during land ($n)" -- mise.lock`
before every `land`. Shared stash stack today (`/usr/bin/git stash list`): `stash@{0}` "mise.lock platform checksums
written by mise during sync after #1093 (2026-10-02)", `stash@{1}` "… during land -- 1526 (2026-10-02)", `stash@{3}`
"mise.lock aws-cli macos-arm64 checksum (written by mise during land -- 1188, 2026-09-17)". None were applied or
dropped. Control: the same listing shows unrelated entries (`stash@{2}`, `{4}`, `{5}`), so the probe sees the stack.
No dedicated ticket: `gh api search/issues q=repo:ray-manaloto/dotfiles+mise.lock+checksum+land` → 4 unrelated hits
(#160, #1093, #421, #755).

**Warning that failed.** The environment's shared-stash warning; `clean-git-state.md`; `feedback_mise_lock_whole_file_is_destructive`
(mise writes the lockfile as a side effect). The workaround became a template instead of a ticket.

**Disposition — MACHINE + PLAN.** In `python/src/dotfiles_setup/pr.py` `land`: snapshot `mise.lock` bytes before
`sync`, and after it either restore them (when the only change is `[tools.*.platforms.*]` checksum additions) or
fail with `FAIL land: mise.lock rewritten by mise during sync — <diff stat>`; never leave the tree dirty. Test
`tests/test_pr.py::test_land_restores_a_checksum_only_mise_lock_rewrite` + control
`test_land_fails_on_a_version_changing_mise_lock_rewrite`. PLAN row: `- [ ] S30-land-mise-lock: land/sync write
platform checksums into mise.lock (3 stashes 2026-09-17..10-02, land rc=1 at L4169); research whether MISE_LOCKED /
lockfile read-only mode prevents it natively first (use-tool-builtins); then the pr.py guard above. Ray: OK to drop
stash@{0},{1},{3}?`

### F4 — KB #748 xdist/load flake blocked kb-ship 9 times this session; open 22 days — MED (cross-session)

**Occurrences** (`agent-akb-flak`): `tests/test_mcp_serve.py::test_probe_catches_a_clean_exit` L797, L801, L990,
L1273, L1277; `test_kb_serve_actually_answers_mcp` L1557, L1741, L1794, L1801 (`FAIL gate test rc=2` → `ship: gates
failed — not pushing`). Both are named in KB #748 (`gh issue view 748`: OPEN since 2026-09-10T09:55:49Z, 7
comments, body lists `test_kb_serve_actually_answers_mcp`, `test_mcp_serve`, `test_codex_lane`). The session fixed a
DIFFERENT flake (`test_guard_codegen.py`, KB #833) and twice took the admin-merge route (#831; KB2 at L5299) instead.

**Warning that failed.** #748 itself; `zero-skip-policy.md` rule 5 (a gate passing on retry is not green).

**Disposition — PLAN** (KB task_plan): `- [ ] KB-748 (P1): test_mcp_serve timing tests fail under xdist + host load
(9 kb-ship refusals 2026-10-01/02). Either mark them xdist_group-serial (pytest-xdist --dist loadgroup) with a
measured timeout margin, or move the live server probe out of the parallel gate into its own serial gate step; arm:
run kb-gates under `stress-ng --cpu N` and require 3/3 green.` Needs no Ray ruling.

### F5 — runaway `tr -dc … </dev/urandom` orphans (2×) pinned the host for 1.5 h; killed by hand-picked PID — MED

**Occurrences.** MAIN L5277: `ps` shows PIDs 31127 and 68453, PPID 1, 91% CPU each, etime 1:36:45 / 1:33:52; load
average 69/80/106. `agent-akb-flak` L1752 traced their stderr to KB session `53f20658` task outputs `bm514shmh` and
`b6kor23fj`; that session's transcript L338 and L387 ran `tok="ghp_$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom |
head -c 36)"` — an unbounded producer behind `head`. `tr` normally dies of SIGPIPE when `head` exits; that it ran
on with PPID 1 suggests SIGPIPE was ignored in the inherited environment (**inferred, not measured**). L5281 killed
both by PID; the `reap` skill ("before hand-rolling a `pkill`, a `ps | grep | awk | xargs kill`") was not used (low
risk here — PIDs were verified first at L5277).

**Warning that failed.** None specific to the `tr </dev/urandom | head` shape (rg over memory + reports: only
unrelated hits); `long-running-command-hangs.md` rule 4 covers the symptom, not the cause. Twice in one lane → a
repeat.

**Disposition — MACHINE.** `python/src/dotfiles_setup/hook_guard.py` new `Rule(name="unbounded_urandom_producer",
since=<landing date>)`, pattern on the masked view: `\btr\b[^|;&]*<\s*/dev/u?random\s*\|` — reason: *"`tr …
</dev/urandom | head` spins forever if SIGPIPE is ignored (two 90%-CPU orphans for 1.5 h, 2026-10-02). Bound the
INPUT: `head -c 64 /dev/urandom | LC_ALL=C tr -dc A-Za-z0-9` or `openssl rand -hex 18`."* Tests in
`tests/test_hook_guard.py`: deny the verbatim L338 command; allow `head -c 64 /dev/urandom | tr -dc A-Za-z0-9`; allow
the quoted mention `echo "tr -dc x </dev/urandom | head"`. Note the guard does not see a KB session's commands
unless KB wires the same hook — add the same rule to KB's guard (rule-sync set).

### F6 — seven background lanes stalled ~11 h 45 m on an `EnterWorktree` trust prompt — MED

**Occurrences.** MAIN L4638 (recorded): "all 7 bg lanes (A,B,C,E,G,KB2,KB3) blocked ~11h45m on the EnterWorktree
'permission-root relocation … outside .claude/worktrees/' prompt"; L4640 diagnosis: each lane called `EnterWorktree`
into `../dotfiles.worktrees/lane-*`. One cause, seven instances, discovered only when Ray asked. Second instance of
the same "a `claude --bg` lane is waiting on input and nobody sees it" class: L5466 → L5474 `Workspace not trusted`
(see F7).

**Warning that failed.** The harness's own `EnterWorktree` description ("Never use this tool unless 'worktree' is
explicitly mentioned"); `feedback_agent_spawn_liveness` ("'Spawned successfully' ≠ running — verify the transcript
exists AND grows").

**Disposition — MACHINE (PLAN row).** The fix that shipped (#1533's skill adds a `CWD:` line and "no EnterWorktree")
is prose. Add a check: `- [ ] S30-lane-liveness: a python `lane_launch` (mise task) that, after each `claude --bg`,
polls `claude agents --json` (bounded, 5 min) and FAILS when a lane's state is waiting-for-input/permission or its
transcript has not grown; the parallel-work-split skill calls the task instead of a raw `claude --bg`. Test with a
fixture `claude agents --json` payload in each state (control: a running lane passes).`

### F7 — a filter hid the failure of the thing being launched: `claude --bg … 2>&1 | grep -o 'backgrounded · …'` — LOW (same class as F1)

L5466 piped two `claude --bg` launches through `grep -o`; the result read `Exit code 1` + `backgrounded · 5361f892`,
so the second launch's error was invisible until the unfiltered retry at L5474 printed `Workspace not trusted. Run
claude in … once and accept the trust prompt`. Warning: `probes-need-a-control-arm.md` rule 3 (display bounds);
`long-running-command-hangs.md` rule 3. Disposition: fold into F6's `lane_launch` task (it captures the full
stdout/stderr and rc per launch); no separate guard (a `| grep -o` on arbitrary commands is too common to deny).

### F8 — own prose tripping `typos` twice in a row on one coined abbreviation; the first fix covered one spelling — LOW (cross-session, CAUGHT by machine)

`scratchpad/ho-commit.log:55-70` already listed BOTH `hel` and `HEL`; the L5437 fix replaced only `\bHEL\b`, so
`ho-commit2.log:56` failed again on `hel` (fixed at L5459). Cross-session: 09-28 R7, 09-29 R5 (own edits failing
typos). The pre-commit `typos` step caught it every time, so the cost is cycles, not escapes — and here the
commands chained `commit; push` with `;`, so a push ran after a failed commit (L5383). Disposition: **needs Ray
ruling that it stays prose** (recommended: yes — the gate works; a further check would duplicate it). Optional
cheap PLAN item: `session-handoff` skill step "run `typos <handoff file>` before committing it".

### Seeds checked and qualified

- **"#1526 land rc=1 twice but handoff says 'All land: OK'"** — refuted as stated. The rc=1s are real (L4169 ff
  failure; L4217 `FAIL verify-local rc=1` on a shared.toml hash mismatch), but
  `handoff-20261002/docs/handoffs/session-2026-10-02.md:16` reads "All `land: OK` except #1526: `land -- 1526` rc=1
  twice". The handoff is accurate (it is, however, the commit that never reached GitHub — F1).
- **kb-land rc=1 on #831 / #832, no tickets** — confirmed: `agent-akb-flak` L1611 (`kb-land 831` "PR #831 is not
  green", admin-merged), L1654/L1656 (`kb-land 832` "merge failed" though merged at 55923b5f). Ticket search
  `repo:ray-manaloto/knowledge-base+kb-land+created:>=2026-10-01` → 2 unrelated (#834, #829); control: the undated
  `kb-land` search returns 108, so the query works. Single occurrence each → not a repeat by Brief R's test; route to
  the dismissed-errors lane. PLAN: `- [ ] KB-land-rc: kb-land reports rc=1 for an already-merged PR (#832) and gives
  no admin-merged path (#831); file a KB issue.`
- **Coordinator context exhaustion** — MAIN crossed 800 k context at L4282 (10:39Z), peaked at 975,956 tokens, and
  started the handoff only at ~17:43Z (L5383); from L5588 every turn is "Prompt is too long", so seven teammate
  messages (L5599-L5623) went unanswered and F1's #4 failure was never seen. Warning: `session-handoff` skill ("on
  your own judgment when context is getting full"). No repo check exists (`rg cache_read_input_tokens|context_window`
  over `python/src` + `.claude/settings.json` → 0; control: the same rg finds `context_window.used_percentage` in
  `$CC/statusline.md`). Cross-session recurrence is **inherited/unverified** here. Disposition — MACHINE (PLAN): `- [ ]
  S30-context-gate: a PreToolUse branch in hook_guard.decide_payload that reads the transcript's last `usage`
  (input+cache tokens) and, above 70 % of the window, denies NEW `Agent`/`claude --bg`/`mise run ship` launches with
  "run /session-handoff first" (allowing reads and the handoff itself); tests with a synthetic transcript at 69 %/71
  %.` Needs Ray ruling (it blocks work) — recommend yes, at 75 %.
- **Hand kill instead of `mise run reap`** (F5) — single, verified PIDs; not escalated.

## Summary

| ID | sev | repeat | disposition |
|---|---|---|---|
| F1 | HIGH | `git push` rc=141 ×4, notifications "exit code 0", read-before-settled, "transient" retry | MACHINE: `decide_payload` background-wrapper rule + `pr.py` rc=141 classification; PLAN (Ray): stop the duplicate pre-push pytest / SSH keepalive |
| F2 | HIGH | `/code-review` skipped (0 calls / 14 PRs) | PLAN: promote the 2026-09-28 RULED ship review gate to P0 |
| F3 | MED | land/sync dirties `mise.lock`; 3 un-dropped stashes since 09-17 | MACHINE in `pr.py` land + PLAN (native lock mode first) |
| F4 | MED | KB #748 flake: 9 kb-ship refusals | PLAN (KB) serialise/relocate the timing tests |
| F5 | MED | `tr </dev/urandom \| head` orphans ×2 | MACHINE: `hook_guard` rule `unbounded_urandom_producer` (+ KB) |
| F6 | MED | 7 lanes stalled on a prompt, unseen 11 h 45 m | MACHINE (PLAN): `lane_launch` liveness task |
| F7 | LOW | `\| grep -o` hid a launch failure | folded into F6 |
| F8 | LOW | typos on own prose, partial-spelling fix | Ray ruling: stays prose (gate catches it) |

Counts: **2 HIGH, 4 MED, 2 LOW** (8 findings) + context-exhaustion PLAN row (needs Ray ruling) + kb-land PLAN row.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issue search for a mise.lock/land ticket; code read (`pr.py`, `hook_guard.py`, `hk.pkl`)
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `gh issue view 748`; kb-land ticket search
