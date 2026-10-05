PREMISE REPORT: docs/specs/handoff-capsule-pr1.md, including the Architect ratification section

(Persisted verbatim by coordinator f5b237 from the premise-verifier hand-back; the lane had no write tool. The harness
neutralised control tags in the original as `<\`.)

I could not write the report file. This lane has only Read, Grep and Glob, so nothing was written to `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-04i/docs/research/kb/reports/agents/premise-verifier-handoff-capsule-pr1.md`. You will need to save this report there yourself, verbatim.

**How I read the code.**
- **Code base.** I read `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/land-smoke-timeout` (written LST below). The spec cites nothing in container.py, sync.py or their tests, so the in-flight codex lane cannot affect any row.
- **89f6ce99.** I read it from `.claude/worktrees/handoff-pr1` (written HPR1 below). `.git/worktrees/handoff-pr1/HEAD` is `refs/heads/feat/handoff-automation-pr1` = 89f6ce99, and the last entry in `logs/HEAD` is the 89f6ce99 commit.
- **Base of 89f6ce99.** The branch was created from b9a027f6 (`logs/refs/heads/feat/handoff-automation-pr1:1`). That is before #1658/ad4dbc62 (`logs/refs/remotes/origin/main:203,216`).
- **Limit.** With no Bash I cannot diff, so I cannot tell what the branch changed from what it simply lacks because its base is older. I compared text side by side, and I could not check whether that worktree has uncommitted edits.

ROWS: 49 checked — 40 CONFIRMED (0 provenance corrected) / 4 REFUTED / 0 UNVERIFIABLE / 5 ASSUMED (2 checkable)

L1 — CONFIRMED — LST coordinator_handoff.py:109-112 is `json.dumps({"crossSessionInbound":"accept","worktree":{"bgIsolation":"none"}}, separators=(",",":"))`. The value is a compact JSON **string**. ⚠ 89f6ce99 risk: HPR1 coordinator_handoff.py:109 is `CROSS_SESSION_SETTINGS = '{"crossSessionInbound":"accept"}'`, which is the pre-#1658 base. Re-verify L1 after the merge; a conflict resolved toward the branch side would silently revert #1658.
L2 — CONFIRMED — :780-784 `_gather` calls `handoff.read_text` once; :894-912 builds the brief from that text. 89f6ce99 moves these lines down about 2 (HPR1 :779-783 and :893-911 sit on an older base). Content is identical.
L3 — CONFIRMED — `_QUEUED_HEADING_RE.search` returns the first match only (:134-137, :440-448). The section ends at `^##\s`.
L4 — CONFIRMED — :664-666 holds the fallback text and :698-699 the render. A non-empty body such as `_None._ (…)` is passed through verbatim (launch.log:32).
L5 — CONFIRMED — :454-460 `HeavyRun(pid, argv, log_path)`.
L6 — CONFIRMED — :918-927 records at/successor/handoff/cwd and `state["census"]`.
L7 — CONFIRMED — the :824-832 docstring defines rc 0/2/3/4.
L8 — CONFIRMED — :690-691 says LANES report BY NAME; :705-706 is step 2, SendMessage to every lane. HPR1 :689-705 is the same text.
L9 — CONFIRMED — requirements.md :16 (req 9, bgIsolation none), :22 (req 13), :23 (req 14), :31-33 (reqs 20-22). Audit :112 bounded its search to `.claude/skills/coordinator-handoff/`.
I1 — CONFIRMED — handoff_check.py:637-644 `check_with_claims(repo_root, text, *, show=show_attestation, facts=None, source="handoff")`.
I2 — CONFIRMED — :4-12, including "A GitHub lookup that fails is a finding, never a pass."
I3 — CONFIRMED — :394 ``(?i)\blanded\b`` → LANDED; :494 `LANDED: facts.state == "MERGED"`. Note `_NEGATED_CLAIM` (:67-71) masks "not/never landed".
I4 — CONFIRMED — session_state.py:378-385 is the signature. :396-408 returns `open_prs`/`merged_prs=None` when `with_pr=False`. :254-258 maps a gh failure to None. :427-428 sets the truncation flags.
I5 — CONFIRMED — :170 `--format=%H%x00%s`.
I6 — CONFIRMED — :557-602 handles only `--no-pr`, `--since` and `--for`, and prints Markdown.
I7 — CONFIRMED — handoff_inbox.py:149-151 is the record format; :230-259 is `_replace_atomically` under `state_lock`.
I8 — CONFIRMED — sdlc_team.py:101-122.
I9 — CONFIRMED — :1019-1023 sets COMPLETED iff rc 0; :1036-1037 downgrades to FAILED when reconciliation is not consistent.
I10 — CONFIRMED — :183, :224, :252, :908-929. Caveat: output.md is only the default path; `request.output_file` can override it (:224).
I11 — CONFIRMED — gate_result.py:43-52, :83-86, :127-133, :164.
I12 — CONFIRMED — session_common.py:43-44 and :77-84 (an exact `sessionId` match is required).
I13 — CONFIRMED — reap.py:70 is `ps -eo pid=,ppid=,etime=,stat=,args=`; :96-103 is `Process`.
I14 — CONFIRMED — main.py:1609-1654 and :2936-2955. In HPR1 every `def` line and these anchors sit at identical lines, so 89f6ce99 does not move them.
I15 — CONFIRMED — mise.toml :1027-1030, :1037-1040, :1369-1372, :1394-1397, :1700-1705.
I16 — CONFIRMED — pyproject.toml:229-266 and :268-284.
P1 — CONFIRMED — session_common.py:119-127 `write_state` (tmp then replace); :130-152 `state_lock`, 10 s default (:33).
P2 — CONFIRMED — session_state.py:14-16.
P3 — CONFIRMED — suites.toml:1517-1537 and :1804-1826.
P4 — CONFIRMED — tests/AGENTS.md:90-100.
P5 — CONFIRMED — SKILL.md:40-43 and :64-76; the mirror `.agents/skills/coordinator-handoff/SKILL.md` exists. ⚠ 89f6ce99 also edits this skill: HPR1 SKILL.md:18-19 adds probe-TTL text that main lacks. Lines shift by about +2, so :40-43→42-45, :64-76→66-78, and the "do not touch" :57-60→59-62.
P6 — CONFIRMED — Grep of `handoff_check|session_state|coordinator_handoff` (and the dashed forms) in suites.toml returned 0. Control arm: the same file contains `workflow.bash-logic-enforcement` (:1518).
E1 — CONFIRMED — the settlement has `"status":"completed","codex_returncode":0,"finished_at":"2026-10-04T17:56:04.881620+00:00"` (the spec abbreviates the timestamp). output.md:1 begins `**DO NOT SHIP`.
E2 — CONFIRMED — `completed`, `17:44:13.560448+00:00`; output.md:1 is "Blocked before implementation."
E3 — CONFIRMED — :3 "All required gates passed:" and :12 "Nine mutation controls failed as expected." The note that a "fail" lexicon would misfire is irrelevant: the specified lexicon has no fail term (see MISSING-7).
E4 — REFUTED — The 04h handoff:17 reads "3. Lane G relayed (AskUserQuestion, 2026-10-04): …", which is a third outside-section match the row omits. Grep on that file for ``(?i)\bqueued question|AskUserQuestion`` returns :17, :58, :75 and :88. Also, the :77 body is `_None._ (Review a3d6e816's recommendation will produce questions for Ray once it settles.)`, not bare `_None._`.
E5 — CONFIRMED — launch.log:7 shows argv `--settings {"crossSessionInbound":"accept"}`; :31-32 shows the propagated `_None._ (…)`.
E6 — CONFIRMED — 598fd7e2/state.json:58-64 has respawnFlags without bgIsolation, and :71/:73/:78 hold name, sessionId and createdAt. e67105a8:19-25 has bgIsolation `none`. Its createdAt is at :45, outside the cited :19-28.
E7 — CONFIRMED — main-checkout-ship-queue.md:498 contains "#1647 landed (rc 0)".
E8 — CONFIRMED — land-1662.log:5919 `raise TimeoutExpired(`, :5922 the message, :5934 `rc=1`.
E9 — CONFIRMED — the prefixes are at transcript lines :17, :27, :315, :358, :585 and :980. The "8 hits / 4 files" count is a grep artifact: each subagent file holds one real tool_use (for example agent-afe482f8f0481c9c4.jsonl:299, an assistant record) plus one attachment mention at :23. That is 4 handbacks, not 8.
E10 — CONFIRMED — inbox autostart.md:2 is `## 2026-10-04T17:06:32Z — …`; session_common.py:155-157 `now_iso()` returns Chicago time.
E11 — REFUTED — The row says the capsule contains "no env values". `HeavyRunRecord.argv` comes from `reap.Process.command`, which for every harness Bash run starts with the wrapper prelude: launch.log:19-22 shows `source …snapshot… && export CODEX_COMPANION_SESSION_ID='…'\012export CODEX_COMPANION_TRANSCRIPT_PATH='…'\012export CLAUDE_PLUGIN_DATA='…'`. Truncating to the first 512 characters keeps that prelude and cuts off the real command (`eval '…mise run land…'`, near the end).
A1 — ASSUMED — I cannot run git. The ratification records `git diff --stat 25bceb1e f4b39b8b -- python/` as empty with rc 0, but that is the architect's report, not a file:line. Everything I read in LST python agrees with post-#1658 main.
A2 — REFUTED — The sub-claim "observed in 2 of 59 records" is false: Grep `"respawnFlags"` over `~/.claude/jobs/*/state.json` returns 78 of 78 files. The core assumption (undocumented key; the check fails closed when it is absent) still stands. Correct the text; this does not block on its own.
A3 — REFUTED — The row says "an unknown prefix fails closed to `human`", but deliveries also arrive as non-`user` records, which rule 3 never reads. In bcc4b879 there are 20 `"type":"queued_command"` attachments, for example :65 `"prompt":"<\cross-session-message from=…`, :500 `<\agent-message from="a46b…">[Subagent hand-back]…` and :370 `<\task-notification>`. Twelve of them are cross-session messages. All of them are silently dropped, not routed to `human`.
A4 — ASSUMED (checkable) — The ratification settles it. Read: HPR1 changes coordinator_handoff.py (`_launch_in_progress(state, warnings)` → `_pending_in_progress(state, key, warnings)` at HPR1:228-250 and :860, timestamped `probe_pending` at :305, probe help text at :1195-1199). It also changes `.claude/skills/coordinator-handoff/SKILL.md` (:18-19), which the ratification omits. main.py anchors do not move.
A5 — ASSUMED — The first-paragraph heuristic. It is safe in that it can only downgrade.
A6 — ASSUMED (checkable) — Re-read at LST: L2/L5/L8/I1/I4/I11/P1 hold.
A7 — ASSUMED — Savings are unmeasured.

**Ratification rows.**
- "A1 CONFIRMED (git diff empty)" is unverifiable by this lane; there was no Bash.
- "89f6ce99 touches coordinator_handoff.py and main.py" is CONFIRMED for coordinator_handoff.py. It is incomplete: the branch also touches the coordinator-handoff SKILL.md (and presumably its `.agents` mirror). For main.py I could only show its anchors do not move.
- "Re-read the anchors after merge": after 89f6ce99 the coordinator_handoff anchors shift about +2 from roughly line 231 onward (L2-L8, census :588-627, transcript_path :432-437, BriefContext/_launch_locked, which OC-2 edits). Content does not change: HPR1 :647-725 brief and :883-927 `_launch_locked` are identical text. This is an estimate, because 89f6ce99's base is older than 25bceb1e.

MISSING:
1. **The transcript walk misses non-`user` deliveries** (load-bearing). Read: bcc4b879 :65, :166-220, :370, :500, :893, :964, all `attachment`/`queued_command`. List-content user text (:746) is also dropped as if it were a tool result. Rule 3 and AT7 must also classify `attachment.type == "queued_command"` prompts. An unrecognised record type must become an obligation, not be skipped.
2. **The AT4 control arm cannot pass as written** (load-bearing). Read: handoff :17 `AskUserQuestion` stays outside the section after :88 is moved and :58 removed, so `question_outside_queue` still fires. Remove or handle :17 in the control, or narrow the matcher.
3. **`body_is_none` is undefined** (load-bearing for AT4). Read: :77 is `_None._ (Review …)`. Define it, for example "the body starts with `_None._`".
4. **There is no pid source for unsettled runs** (load-bearing for rule 9, AT1 and RUNNING). Read: `read_status` needs a caller-supplied `pid` (sdlc_team.py:908-929); the run dir holds only prompt.md, output.md, codex.log and settlement.json (:223-225, :252). Without a pid every unsettled run reads ABANDONED. State where the pid comes from (for example the dispatch JSON, or a codex.log/prompt mtime heuristic marked UNKNOWN).
5. **The inbox record grammar and naive stamps are unspecified** (load-bearing). Read: the inbox holds `## 2026-10-03 — …` (dotfiles-20261002.audit-000.md:1), which parses to a naive datetime and raises TypeError when compared with an aware `since`. It also holds `## LANE WATCH 2026-10-02 …` (watch.md, 27 headings) and section headings like `## 1. Run …`. Define what counts as a record (` — ` required?), how naive or date-only stamps are treated, and whether all 48 legacy headings become perpetual pending obligations.
6. **Collect under the launch lock** (load-bearing for OC-2). Read: OC-2 puts collect inside `_launch_locked`, which runs under `state_lock` (:847). `gather` makes three gh calls at `GH_TIMEOUT=120` each (pr_facts.py:27; session_state.py:413-415), up to 360 s. Meanwhile `decide` gets `state-locked` after 10 s. The spec must bound launch-time collect (for example `with_pr=False` or a deadline), or collect before taking the lock.
7. **The AT2 "whole-file lexicon" mutation cannot fail the listed fixtures** (load-bearing for the mutation evidence). Read: Grep `DO NOT SHIP|^\W*blocked` over the 671241e5 and eb6af51c outputs matches only 671241e5:1; eb6af51c has neither term. Add a constructed fixture with the term after paragraph 1.
8. **`check_with_claims` side effects are not in the rc contract** (load-bearing). Read: handoff_check.py:238-256 runs `mise tasks ls` and raises RuntimeError on failure. :117-134 runs the pwf plugin through `show_attestation`, and `show` is not injectable through the spec's `check()`. :204-235 resolves paths against `repo_root`. Worst case is about 540 s (:72-74). Say how RuntimeError maps (rc 2? a finding?) and inject `show`.
9. **`gather` failure modes are unhandled** (needs a ruling). Read: session_state.py:122-134 raises RuntimeError on git failure, which collect's rc 2 list does not cover. Snapshot carries no error text, so "`available=false` with the error" has no source. `gather` reads `utc_now()` itself (:391), so `CollectDeps.now` cannot pin it.
10. **The default `since` uses only `.agent/plans/session-*.md`** — handoff_check.py:189-194. Tracked handoffs live in `docs/handoffs/`. State which handoff sets the window.
11. **Generated structs are not frozen** — generated/saved_search_file.py:11 `class Struct(_Struct, forbid_unknown_fields=True)`. The spec's "All structs are frozen" is false for the current codegen config. Non-blocking; drop the word or add the config deliberately.
12. **argv sanitisation** — this is E11. Specify taking the eval payload (the `rpartition("eval '")` pattern at coordinator_handoff.py:466) or redacting `export X=…` before the 512-character cap.
13. **finished_at format** — settlements use `2026-10-04T17:56:04.881620+00:00`, while `since` uses `…Z` (session_state.py:40). Require a datetime comparison. Non-blocking.
14. **Ship-queue LANDED grammar is inconsistent** — :501 `land 1656 rc 0` and :494 `land -- 1647` have no `#N … landed`, so they produce `land:N` obligations that never clear. This fails closed. Non-blocking; document it.
15. **`CollectDeps` has no `self_pid`** — `census(self_pid=…)` requires one (coordinator_handoff.py:591). Non-blocking.
16. **CLI dispatch shape** — the main.py dispatch must rebuild argv for the nested collect/check verbs, the way session-state does (main.py:2936-2949). Non-blocking.
17. **Possible overflow on day one** — I did not count sdlc-run dirs across worktrees: Glob over `.claude/worktrees/*/.agent/sdlc-runs/*` timed out. If unsettled or legacy runs exceed 64, every check fails with `overflow`. The architect should count before dispatch.
18. **Merge-order collision** — 89f6ce99 and this PR both edit coordinator_handoff.py and the SKILL.md, and probably tests/test_coordinator_handoff.py. After the merge, re-verify L1 against the merged main, not the 89f6ce99 tree (which lacks bgIsolation).

VERDICT: correct the spec first. What blocks: the transcript walk misses `queued_command` deliveries (A3, MISSING-1); E4 is incomplete, which breaks AT4's control arm (MISSING-2/3); RUNNING is underivable without a pid (MISSING-4); the inbox stamp grammar and naive-datetime TypeError (MISSING-5); unbounded gh calls inside the launch lock under OC-2 (MISSING-6); and argv carrying the env prelude (E11). Re-read the anchors after 89f6ce99 merges, adding SKILL.md to that list.
