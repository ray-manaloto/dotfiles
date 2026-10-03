# Handoff review — 7541ae79 (in progress)

Transcript: ~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/7541ae79-...jsonl (6160 lines; L5600-6160 = 2026-10-03T15:31Z-16:29Z, i.e. the session WAS live 10:31-11:29 CDT and ended with Ray's `/exit` at L6158-6160, 16:29:13Z).

## 1. Rulings by Ray (AskUserQuestion answers, raw Ray messages)
| L | ts (UTC) | Ruling |
|---|---|---|
| 531 | 10-02 21:49 | Owed review batch (task_plan:2488: #1523, /code-review #1503 #1505 #1520 #1531 #1533 #1535, mattpocock #1531/#1532, codex lens 11 SHAs) runs "After MR-A ships" |
| 670 | 21:55 | "why is the session name missing the ISO date timestamp i requested?" |
| 817 | 22:00 | codex use: "we need to wait until the modesl have been updated" |
| 931 | 22:04 | "coordinate all fan out sessions to pause until the knowledge-base and dotfiles repos have the codex model upgrades" |
| 1502 | 22:28 | Pre-confirm admin toggle-merge of KB#841 at head 7e411cee |
| 1675 | 22:38 | "i need you to coordinate all this work and only ask me for anything that needs human intervention" |
| 1757-1811 / 3113-3254 | 22:40, 00:15 | Ray personally toggled enforce_admins and admin-merged KB#841 and KB#849 |
| 2119 | 23:01 | 22-item coordinator-creation list: ADD — for EVERY new claude session (not just coordinator) a claude-mod function hook that (1) runs /reload-skills and /reload-plugins --force, (2) renames the session to `<project>-<yyyyMMdd'T'HHmmss.SSSSSSSSSX>.<feature>` (kb / dotfiles). "Exempt it from pause now" for coordinator-auto-handoff lane |
| 2919 | 23:53 | "ratified" (context: see below) |
| 4113 | 01:43 | #1502 saved searches: "Ship C, then #1502 lane" |
| 4505 | 02:17 | LLVM detection rule approved; when M not served for codename -> "Highest served below M" (NOT the recommended option) |
| 4686 | 02:39 | "Hold bump until IWYU 0.27"; "Coordinator ratifies" spec rev 2 docs/specs/llvm-major-detect-bump.md |
| 6000 | 10-03 15:51 | LLVM pin-churn: Ray: /research-sweep how other projects get prebuilt IWYU matching latest LLVM; does conda publish newer iwyu; GH issues/PRs/discussions; ADD A SAVED GITHUB SEARCH; if no prebuilt -> build from source like p2996; maybe special IWYU build for p2996 llvm — "research and provide cited answer". AND "fix the apt Renovate group now" (own automerging LLVM-deb group, registryUrls follows the major, daily container-free check opening an issue within 24h of a stale pin) |
| 6036 | 15:52 | dag-tick: stopgap "I unload it for you" (Ray does it, not the coordinator); code fix "DONE = log only" |
| 1534/1570 | 22:29/22:33 | Relayed via fork 48df ("when-will-the"): MR-A into BOTH repos ASAP; every fan-out session rebases onto MR-A before ANY codex work; Ray approved admin merge of KB#841 |
| 2919 | 23:53 | "ratified" = MR-B ratification (L2914 coordinator: "MR-B is waiting for your ratification") |
| 5629 | 15:30 | Ray ruling relayed via kb837 lane: auto-deletion of retired docs pages OK (3 misses + >=7d + absent from inventories); appended to task_plan |

Ruling-coverage notes (preliminary):
- L6000 IWYU /research-sweep + "fix apt Renovate group now" — NOT in the stand-in handoff. It IS in task_plan (coordinator appended at L6058) and was routed to llvm-23-bump lane as "fix round 3" + research sweep (L6056). Handoff §2.7 describes llvm-23 only as "waits on lock-format" — WRONG/INCOMPLETE: lane owes fix round 3 + IWYU sweep, and coordinator promised to "take it to Ray".
- L6036 dag-tick: Ray chose the NON-default answer label "I unload it for you" (coordinator ran bootout at L6043, verified before rc=0/after rc=1). Handoff item 1 says "Ask Ray first" for the durable disable — consistent (durable plist removal is a NEW user-level step, not yet ruled).
- L2119 naming + every-session fn hook (/reload-skills, /reload-plugins --force, rename `<project>-<yyyyMMdd'T'HHmmss.SSSSSSSSSX>.<feature>`): NOT in stand-in handoff. (task_plan check below.)

Control arm for the user-message filter: the known-present strings "ratified" (L2919) and "/exit" (L6159) were both found by it, and so were AskUserQuestion answers L531..L6036. So the filter discriminates.

## 2. Ship queue truth table (heads measured 2026-10-03T16:36Z, `git rev-parse` on refs/heads; PR state from `gh pr list --state all`)

**Merged-count claim is WRONG.** The handoff says "10 of 25 merged" and lists #1570, KB#841, KB#853, #1571, KB#846, KB#849, #1573, #1578, #1581, #1583. It omits three lane PRs that merged during this session: KB#848 (KB3, feat/kb-826-currency-engine-r2, 23:42Z 10-02), KB#850 (audit-s29 KB half, 00:59Z) and KB#854 (audit-000 KB half, 03:25Z; the coordinator logged it itself at L5268). The true count is 13. The "10 of 25" figure came from the watcher (watch.md:29) and was never re-derived.

| Lane | Branch | Head now | PR | Handoff claim | Truth / blocker |
|---|---|---|---|---|---|
| KB3 | feat/kb-826-currency-engine-r2 | — | KB#848 MERGED | "finished and unshipped" | **WRONG**: merged. Follow-ups are KB#836 (filed) |
| A | feat/ask-quality-v2 | 80b0fc36 (local, unpushed) | none | unshipped | Blocked on "GATES GO lane-A" from the coordinator for the r4 fix plus mutation arms (A.md). PR body must use Ray's text-limit wording (A.md "Ray ruling (text limit)"). The ship-order list (queue:61, :78) ships A last |
| B | feat/handoff-check-stale-prose | ff806911 (local) | none | unshipped | Owes a TEST-INDEX row, added by the coordinator on its branch (queue:48). Not in the handoff |
| E | feat/gate-run-multi-name | 90c9c96d (local) | none | unshipped | **Merge conflict with main in `main.py`** (L5312 / queue:249). Must rebase. Not in the handoff |
| E-2 / landing-pins | feat/landing-pins | 536ec7c1 (in .claude/worktrees/agent-ac40…) | none | not listed | Needs one GATES GO slot (queue:62). After it and G merge, a NEW lane is launched: fix/pr-landing-pins-wiring (task_plan:2489). **Both omitted from the handoff** |
| G (new work) | docs/brief-review-field b9ae5699; fix/1554-1555-worktree-mount 43f4e97c (lane-G wt); docs/lane-g-reports 52d8a07c | — | none | "G docs/brief-review-field" | Lane G (2ed2df92) is BUSY and **has the MAIN checkout on docs/lane-g-reports 52d8a07c**. That breaks the one-writer main-checkout ship rule: the queue cannot ship until main is free. Ray answered #1555 = mount (watch.md:110; handoff item 10) |
| cc-repoint | docs/cc-repoint | 2727b159 | none | unshipped | Ship-ready (queue:… "cc-repoint SHIP-READY 2727b159"). Session done |
| devcontainer-cap | feat/devcontainer-cap | 7887c28f | none | "devcontainer-cap (7887c28f)" | Correct. First ship FAILED on the non-hermetic test (L5409-5423), fixed in 7887c28f (Opus SHIP). Queued after land-1583 + kb837 ship gates (L5687). cap-fix session 0d71962e is idle |
| s29-00b | fix/s29-00b-bot-pr-regenerate | 58538401 | none | unshipped | Ship-ready. After it merges, **rebase Renovate #1449** (task_plan:2490). That obligation is not in the handoff |
| worktree-ergonomics | detached 4f172ae8; branch fix/worktree-ergonomics 4f172ae8 | none | unshipped | Ray: ship from its worktree (queue:109). The coordinator removes the wt after it lands (task_plan:2489 says 0d5dfe28, now stale; the head is 4f172ae8) |
| fnox-provider | feat/doctor-fnox-provider-live | 00567df4 | none | unshipped | Gates were green at c4bcdbe0, not at the final head (queue:60) |
| audit-s29 | docs/session-audit-20261001-s29 | 6f9555c8 (local) | none (KB half = KB#850 MERGED) | "audit-s29" | Only the dotfiles half is unshipped. Also owed: the delta .agent/plans/task_plan-delta-audit-s29-20261002.md applied to task_plan, the MEMORY pointer line, and #1569-vs-#941 (queue:116). **Not in the handoff** |
| kb837 | KB feat/kb-837-offline-docs | b220a2dc (local only) | **no PR** | "admin merge per Ray" | The coordinator promised "GO kb837-ship" to kb-20261003T102535…ship after land-1583 (L5535, L5627). land-1583 finished 16:14Z, AFTER the context death, so **GO was never sent**. The shipper is idle. Ray ruled the merge path = admin merge (watch.md:103-110). PR body = "Closes #837. Closes #847." (L5535/L5655) |
| llvm-23 | feat/llvm-23-detect-bump | f12e9aff (moved past d2be1693) | none | "waits on lock-format" | **INCOMPLETE**: after the coordinator died, the lane did fix round 3 (4d6c666c Renovate LLVM group + daily apt-pin check) and the IWYU sweep (83dcb0ad, f12e9aff), filed #1587/#1588, and has 2 untracked reports. It needs: a Ray ruling on the IWYU sweep result (the coordinator promised "I take it to Ray", L6056), a ship slot, and lock-format first |
| lock-format (ledger) | chore/lock-format-upgrade | a2719c65 (rebased copy of backup/lock-format-upgrade-pre-rebase-20261002 d8b57ca1) | none | **NOT LISTED** as a ship item | **14 UNCOMMITTED files** in lock-format-upgrade-20261002 (backend_guard.py, mise-system.toml, ci.yml, hk.pkl, mise.toml …; the newest mtime is 18:11 10-02), so this is loss risk. Session 45bec37a is idle waiting "GATES GO ledger" (L5758). Ships LAST, one container slot (task_plan:2491). At ship it must file tickets: offline-trust §8.1 and R3 musl §6.5 (queue:108). llvm-23 depends on it |
| model-registry MR-B | KB feat/model-registry 71ca4a57; dotfiles feat/model-registry 5fb387a9 | — | none | handoff item 8 (R-1) | The coordinator granted SLOT at L5749. The sweep found a regression (L5784), and the re-run was pre-approved (L5785). Next: KB receipt, then hand to the NEW KB shipper (not the old kb-20261002.ship), then KB merge, then dotfiles D1-D6, which needs R-1 (Ray). Tickets KB#855-#861 filed |
| #1502 saved-searches | feat/1502-saved-searches | 785c3708 + 8 uncommitted files (uv.lock, mise.toml, suites.toml…) | none | not listed | Lane 8d6e7252 is BUSY (codex implementer). It waits for "SLOT 1502" once the implementer settles (L5963). The IWYU saved-search format is coordinated with it (L6056) |
| session-autostart | feat/session-autostart-no-prompts | 060de30b (dag-tick fix committed) | none | handoff item 1 "ship it" | It waits for "SLOT autostart", promised right after land-1583 (L5871, L6055) and **never sent**. Scope also includes the sibling dev.mise.dotfiles-dag-project check, the launch recipe with `--disallowedTools EnterWorktree`, coordinator self-wake, the external watchdog and the /tmp read fix (L6055) |
| lane-completion | docs/lane-completion-protocol | 1dcf0d4b (pushed) | none | item 3 | Correct |
| handoff docs | docs/handoff-2026-10-02 79a0c686 (pushed); docs/session-2026-10-01 985030ac (pushed) | — | none | **NOT LISTED** | Both are queued docs ships (queue:57, :109, :125) with no PR. Omitted |
| orch-research-fixes | docs/orchestration-research-fixes | aac2c0b8 (local) | none | **NOT LISTED** | Queued (queue:31, :61). Omitted |

Lanes listed as "unshipped" in handoff §2.7 that are actually merged: KB3 only.

Control arm for "unmerged": `git cherry` does NOT discriminate. Squash merges give "+" even for the merged control fix/host-load (6). The content test was used instead: `git diff --quiet origin/main <branch> -- <first changed file>`. The merged control fix/host-load matches main. docs/orchestration-research-fixes, docs/session-2026-10-01 and docs/handoff-2026-10-02 all DIFFER, so they really are unmerged. `gh pr list --search head:<branch>` returns [] for each.

## 3. Obligations still unfulfilled (LOST = absent from the stand-in handoff)

### 3a. Inbound messages that arrived AFTER the context death and were never processed (L6083-6153, 15:54Z-16:19Z). ALL LOST from the handoff
The stand-in handoff never mentions these. Every one was rejected with "Prompt is too long" (L6075-6155, 11×).
1. **L6083 session-autostart:** "Ray asks YOU to have subagents research this". The durable dag-tick stopgap: plist rename/move vs `launchctl disable gui/<uid>/dev.mise.dotfiles-dag-tick` vs a mise.local.toml override; whether `mise bootstrap launchd-agents apply` honours `launchctl disable`; whether the fix PR should also gate the `[bootstrap.macos.launchd.agents.dotfiles-dag-tick]` declaration. Handoff item 1 says "ask Ray first" but omits that Ray asked for a SUBAGENT RESEARCH pass.
2. **L6089 model-registry:** KB MR-B READY at 71ca4a57 (round-4 fix, Opus delta SHIP, receipt minted). Residuals are ticketed (KB#861 exists, filed 16:33Z). After the KB merge, dotfiles D1-D6 runs on the merged SHA. R-1 is still Ray's.
3. **L6102 kb-20261003…ship:** MR-B KB READY. **Needs GO plus an ORDER vs kb837.** Both are classifier REQUIRED, so both need **Ray's admin merge**. Whichever merges second must rebase and re-mint under strict. The shipper's default is kb837 first. Also: MR-B edits .codex/config.toml, and the full-diff shasum will change from 30cd898a (expected, not drift). NOT in the handoff.
4. **L6108 ledger-20261002.native-codex: NEW RAY RULINGS (round-5 grilling, 2026-10-03) R17-R20.**
   - R17: backend guard stays BLOCKING.
   - R18: host guard installs the pinned mise.
   - R19: ALSO upgrade the HOST locks (mise.lock, .config/mise/mise.lock) to format v3 in THIS PR. Ray: "we always want to follow mise modern best practices… all our repos/projects to be mise first".
   - R20: nothing more.
   These rulings live ONLY in an UNCOMMITTED WIP (lock-format-upgrade-20261002 report §8.4, line 414). They are absent from task_plan (grep 'R19' → only :2491) and from the handoff. R19 widens the GATES GO slot: bare `mise lock --upgrade` then prune, host sidecars at .mise/locks/ and .config/mise/locks/ added to refresh.yml paths, and the mcp2cli / deepagents-cli wheel closures are unverified. The lane will ASK before applying the azure-cli `uvx=false` pattern.
5. **L6114 lane G: NEW RAY RULINGS.**
   - (1) PR A = promote the lane-G reports verbatim, docs-only, now. This is docs/lane-g-reports 52d8a07c, and it currently occupies the MAIN checkout.
   - (2) PR B = #1554 + #1555, after A.
   - (3) #1554: container_image_id derives from docker_container_rows plus an rc-checked docker inspect.
   - (4) #1555: an rw mount of the .git common dir, NOT a refusal. Research same-host-path vs relative worktree paths with throwaway-container probes, then bring Ray ONE decision.
   - (5) PR B retires the #1481 ship refusal, proven by verify-local from a real linked worktree.
   - (6) MEMORY.md curation is the coordinator's.
   - Requests: (a) a light slot for PR A gates (lint, lint-docs, verify); (b) a container slot later.
   The handoff item 10 has only the "#1555 mount" gist. task_plan has nothing (grep '1555' → 0 hits).
6. **L6127 llvm-23-bump: the IWYU sweep ANSWER plus a recommendation FOR RAY.**
   - No prebuilt IWYU for LLVM 23 exists. conda-forge is at 0.26/libllvm22, and the recipe hard-pins 22.*.
   - Recommendation: (a) KEEP the conda gate and build nothing; (b) escalate to a pinned-SHA clang_23 source-build stage only if Ray wants 23 early; (c) separate p2996-IWYU ticket.
   - The coordinator promised "I take it to Ray" (L6056). **Never relayed to Ray.** LOST.
   - Tickets filed afterwards by the lane: #1587 (sweep false gap) and #1588 (p2996 IWYU).
7. **L6133:** land-1583 finished rc=0 (the bzc368yvs notification). It was never acted on, so every "after land-1583" GO below is still unsent.
8. **L6153 session-autostart:** fix A is now committed (060de30b). The research sweep **corrects the coordinator's own heartbeat design**:
   - `claude respawn` returns the session IDLE and is for binary upgrades only. Re-task a lane with `claude --resume <uuid> --bg "<prompt>"`.
   - It adds a trust PREFLIGHT, because since v2.1.281 `claude --bg` exits in an untrusted dir.
   - tmp-read fix: Read tool on the output path, or `--add-dir /private/tmp/claude-501`.
   - It still needs "SLOT autostart".
   This makes ship-queue.md:262 ("Native relaunch = claude respawn <id> (works on stopped/retired)") STALE.

### 3b. Promises the coordinator made to lanes, unsent at death
| Lane (name) | Waiting for | Source |
|---|---|---|
| kb-20261003T102535.932032000-05.ship (80dc41fe, idle) | "GO kb837-ship" after land-1583, plus the ORDER ruling vs MR-B KB; then Ray admin merge(s) | L5535, L5627, L6102 |
| dotfiles-20261003T103159.259690000-05.session-autostart (cc451742) | "SLOT autostart" for full gates plus live arms; the dag-tick durability research the coordinator was asked to run | L5871, L6055, L6083, L6153 |
| dotfiles-20261002T215620.021158000-05.saved-searches-1502 (8d6e7252, busy) | "SLOT 1502" when its codex implementer settles (one slot: scoped pytest + token-audit) | L5963 |
| dotfiles-20261002T204357.298786000-05.llvm-23-bump (6fae0fec, busy) | The coordinator must relay the IWYU recommendation to Ray and return the ruling; send "lock-format landed" when it lands; ship slot | L5750, L6056, L6127 |
| ledger-20261002.native-codex (45bec37a, idle) | "GATES GO ledger" (widened per R19); ships LAST, one container slot; at ship, file offline-trust §8.1 and R3-musl §6.5 tickets | L5758, L6108, queue:108 |
| dotfiles-20261002.lane-G (2ed2df92, busy) | light slot for PR A gates; container slot for the #1555 probes plus verify-local | L6114 |
| dotfiles-20261003T102555…devcontainer-cap-fix (0d71962e, idle) | none. Its branch 7887c28f ships from main after the kb837 ship gates | L5687 |
| lane-A (session done; branch 80b0fc36) | "GATES GO lane-A" (r4 fixes + mutation arms) | A.md |
| model-registry (54a3c59c) | KB merge of MR-B (via shipper + Ray admin), then dotfiles D1-D6; R-1 by Ray | L6089 |
| dotfiles-20261002.audit-000 (7934b36e, idle) | Ray ends it. The coordinator removes both audit-000 worktrees and applies delta V9, §A V4/V6/V8/V11/V15/V16, §E | audit-000.md |

### 3c. Other owed work missing from the handoff
- **Owed review batch** (task_plan:2488/:2494): #1523 first, then /code-review on #1503 #1505 #1520 #1531 #1533 #1535, mattpocock on #1531/#1532, and the codex lens on 11 SHAs. Ray ruled "right AFTER MR-A ships" (L531). MR-A shipped 22:43Z/23:08Z on 10-02, but the batch was never dispatched. Evidence: 0 assistant mentions after L2000; the control is 2 mentions before L600. LOST.
- **Rebase Renovate #1449 after s29-00b merges** (task_plan:2490). LOST.
- **fix/pr-landing-pins-wiring** lane launch after G + landing-pins merge (task_plan:2489). LOST.
- **audit-s29**: delta .agent/plans/task_plan-delta-audit-s29-20261002.md to task_plan, a MEMORY pointer line, and the #1569 vs #941 cross-link (queue:116). LOST.
- **Owner actions (Ray)**: credential rotation (task_plan:2480; Doppler DB_PASSWORD, dotfiles/dev AUTH_TOKEN plus the AWS key pair printed into the 10-02 transcript). Herdr update (:2481/:2485). Both missing from the handoff's "Ray-owned" list, which names only R-1.
- **Context-exhaustion guard PLAN** (:2481 (1)) and the **pr.py land guard PLAN** for mise.lock stashes (:2481 (3)): planned, not ticketed.
- **ship-time /code-review gate is "P0 NEXT SESSION"** (:2485). LOST.
- **kb-ship standing rulings** were copied to .agent/plans/kb-ship-rulings-2026-10-02.md (L5471). The successor should know the file exists.
- **Stale worktree inventory promotion** (:2488 tail). LOST.
- Issue drafts in ~/.claude/jobs/7541ae79/tmp: all filed. issue-rulesync→#1575, issue-hc→#1576, issue-rc→#1577, i1→#1579, i2→#1580, i3→KB#851, cfu→#1582, llvm-f→#1584, c1497→comment on #1497 (posted 23:40Z, verified via API). Nothing pending.

## 4. Background runs / crons
- **Session cron 12f94384** (`17,47 * * * *` heartbeat, L5901/L5905) was session-only (CronCreate). It fired at L6063 (15:53Z) and L6071 (16:18Z), and both turns died with "Prompt is too long". The session is now `stopped` (`claude agents --json --all`, after Ray's `/exit` at L6158-6160, 16:29:13Z), so the cron is DEAD. No on-disk copy exists: grep for 12f94384 under ~/.claude/*.json and ~/.claude/jobs/7541ae79/ returned nothing. As a control, the same grep found the id in the ship queue. **It matters**: nothing now self-wakes a coordinator or respawns retired lanes unless the successor re-creates it, using the corrected `claude --resume <uuid> --bg` mechanism (L6153), not respawn.
- **land-1583** (bzc368yvs, pid 9834): finished rc=0 at 16:14Z ("land: OK — PR #1583 merged, main green, Mac synced"; tail of land-1583.log). Done.
- **bounded-wait 1583** (wait-1583.log): rc=0, done.
- **Subagents**: LLVM churn research a4b4f7dc… delivered (L5982). The claude-code-expert a93fca87420401f3c hit its turn limit (L5935), was told to write the report (L5937), and the report exists: session-autostart-20261003/docs/research/kb/reports/agents/claude-code-expert-autostart-stall-review-2026-10-03.md (19 KB, 10:46 local). Done.
- **Live heavy runs now** (pgrep 16:36Z): only saved-searches-1502's own `bounded-wait --file …codex-sol-implementer-log-39853…rc`. No coordinator-owned ship/land/sync. The control arm `pgrep claude` matched.
- **dag-tick**: absent from `launchctl list`. **dev.mise.dotfiles-dag-project is STILL LOADED**, and the coordinator asked the autostart lane to audit it for stop/kill (L6055). Both plists remain in ~/Library/LaunchAgents, so dag-tick reloads at the next login or `mise bootstrap`.
- **DO NOT `claude respawn 7541ae79`**: state.json carries respawnFlags, and a respawn would revive a session that is still full.

## 5. Vague handoff items, rewritten concretely
- §0 "rejects every turn with 'Context limit reached'". Actual: 11 turns failed with "Prompt is too long" (L6075-L6155). Ray then ran `/exit` at 16:29:13Z, and the session is `stopped`. **Retire step**: `mise run coordinator-handoff -- retire` now has a state file (7541ae79…json, launch → successor dotfiles-20261003T113006.726261000-05.coordinator, census []). The session is already stopped, so retire only formalises it. Run it with `--dry-run` first.
- §0 "no state file for 7541ae79". Now stale: the watcher wrote 7541ae79…json and …started.json at 11:30 CDT.
- Item 1 "Ship it". Concretely: autostart lane branch feat/session-autostart-no-prompts @060de30b. It needs "SLOT autostart" (full lint/pytest/verify + live arms: in-worktree + `--disallowedTools EnterWorktree` vs control; tmp-read; trust preflight). Then `mise run ship` from main once main is free. Durable stopgap: run the research Ray asked for (L6083), then ask Ray with options: launchctl disable / move plist / mise.local.toml override.
- Item 2 "Make it durable (supervisor or LaunchAgent)". Concretely: the autostart spec already scopes the "external watchdog (launchd → `claude --resume <sid> --bg`, probing in-place vs copy first)" (L6055). Fold it there rather than a new lane. The startup self-check = alert when a `dotfiles-*.coordinator` session has no `.agent/state/coordinator-handoff/<sid>.json` within N min of start.
- Item 5 "kb837 launched with --sandbox workspace-write. Check the launch path." Concretely: this was a DELIBERATE KB design, not a bug (queue line "kb837: codex lane network-free by design (KB do-not #13 forbids danger-full-access; KB network form = -c sandbox_workspace_write.network_access=true)"). Re-state it as "verify KB do-not #13 vs dotfiles ai-cli-invocation.md and file a cross-repo reconciliation ticket", not "a mistake".
- Item 6 "Unsubmitted input boxes". Concretely: the coordinator already answered by SendMessage ("Ignore the unsent line in your input box; this message is the go-ahead", L5749). Rule to record: grants are ONLY SendMessage. The watcher must distinguish an `inputDraft` from a delivered message.
- Item 7 ship queue. Replace it with the §2 table above: 13 merged, not 10; KB3 merged; add lock-format (ledger), the landing-pins / pr-landing-pins-wiring pair, docs/handoff-2026-10-02, docs/session-2026-10-01, docs/orchestration-research-fixes, #1502 and session-autostart. Order constraints: E conflicts in main.py; lock-format ships LAST; llvm after lock-format; kb837/MR-B KB order is an open question with Ray admin merges. **Main checkout is currently on docs/lane-g-reports (lane G PR A)**, so nothing ships until it is freed.
- Item 10 "lane G's PR A/B rulings… See lane G's last turn". Replace with the six rulings at L6114 (§3a.5).
- Item 11 MEMORY.md 24.1 KB. Concretely: run `mise run memory-index`, then the memory-index-curation skill (verify → migrate → shorten). Note the coordinator ADDED a line at L5131 (feedback_launch_lane_inside_worktree).
- §1 "Put rulings that need Ray in Queued questions". Concretely, the queue is: (Q1) IWYU recommendation a/b/c (L6127); (Q2) kb837 vs MR-B KB merge order plus two admin merges (L6102); (Q3) durable dag-tick stopgap choice (L6083); (Q4) #1555 mount design decision when lane G brings it (L6114); (Q5) R-1 codex config move; (Q6) credential rotation status (:2480).

## 6. task_plan.md stale vs reality (line numbers as of 2511-line file)
- :11 `### Phase 1 — update-all runs clean [check 1 OPEN, checks 2-4 MET]` conflicts with Current Phase. This is audit-000 delta V9 (audit-000 inbox), still unapplied.
- :2482 "**OPEN before phase 1 launches:** (a)…". Answered by :2483; mark it resolved.
- :2488 "Owed reviews = ONE coordinator-owned batch lane at/after 2026-10-03 12:01" and :2493 "ASK Ray whether the batch can run earlier". Superseded by :2494. The batch is still NOT run although MR-A landed (:2503), so it is overdue.
- :2489 "coordinator removes the worktree-ergonomics worktree after 0d5dfe28 lands". The head is now 4f172ae8, unshipped.
- :2489 "landing-pins pr.py wiring = a FRESH lane … after G + landing-pins merge". G (#1570) merged; landing-pins 536ec7c1 is unshipped. Still pending.
- :2491 "Ships LAST (touches root mise.toml + host locks)". It needs the R17-R20 addendum (R19 = host locks to v3 in this PR); missing.
- :2504 R-1 still owed (no change). MR-B KB is now READY at 71ca4a57 (L6089).
- :2509 "HOLD the 22→23 bump until conda-forge ships IWYU 0.27". Still valid, but the sweep answer and its recommendation (L6127) are not recorded, and Ray has not ruled.
- :2511 "coordinator unloaded the agent". True for dag-tick, but dag-project is still loaded and unaudited. The fix-A lane has since committed 060de30b.
- MISSING entirely: R17-R20 (ledger round 5), the lane-G rulings (L6114), the respawn→`--resume --bg` correction (L6153), the merges KB#848/#850/#854, and the "main checkout occupied by lane G PR A" state.
- ship-queue.md:262 ("Native relaunch = claude respawn <id> (works on stopped/retired)") is contradicted by the autostart research (L6153).

## Probe/control log
- User-message filter: known-present "ratified" (L2919) and "/exit" (L6159) were both found.
- Review-batch absence after L2000: 0 hits. Control: 2 hits before L600, same regex.
- "Unmerged": the file-content diff discriminates (merged control fix/host-load matches main). `git cherry` does NOT (control = 6).
- Cron 12f94384 on disk: 0 hits under ~/.claude/*.json and the job dir. The same id was found in ship-queue.md:262.
- R19 in task_plan: 0 hits. Control: "dag-tick" = 1 hit, same file.
- launchctl: dag-tick absent while dag-project is present. That shows the grep sees dag agents.

## GitHub repos touched
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): PR and issue state (#1570-#1588), and the #1497 comment check
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): PR state (#841-#854) and issues (#836, #851, #855-#861)
