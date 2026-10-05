<!-- Verbatim final report of the read-only Explore inventory lane (coord-router), persisted at receipt 2026-10-04. -->

# Coordinator duty inventory (read-only lane, 2026-10-04)

**I did not write anything.** This lane is read-only, so nothing was appended to findings.md or progress.md. You need to persist this report verbatim.

Paths below are relative to the main checkout `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles` unless they start with `/`. Two abbreviations:
- **PH** = `.claude/worktrees/process-hardening`
- **Q** = `.agent/plans/main-checkout-ship-queue.md`

On line counts: `wc` says Q has 606 lines and the Read tool showed 607.

## (a) Duty table

Counts come from `grep -cE` over Q (whole file, 2026-10-02 to 2026-10-04). Each count is a lower bound on how often the duty happens.

| # | Duty | Trigger | Inputs | Outputs / side effects | Files and tasks touched | Frequency (evidence count) | Judgement or mechanical | Evidence |
|---|---|---|---|---|---|---|---|---|
| D1 | **Slot arbitration**: grant "SLOT X GO/GRANTED", "GATES GO", watch releases, keep the ruled order | A lane SendMessage asking for a slot; a run finishing (rc in a log); a ship or land ending | The ruled order list, holds, host load, what is running | A SendMessage grant to a lane; the order rewritten in Q | Q; lane briefs (`.agent/plans/brief-kb837-20261002.md:13`) | 80 lines mention "SLOT"; 27 grant or "SLOT →" transitions; 12 "GATES GO" | Mostly mechanical: Ray fixed the order and "before EVERY slot grant, check the next item" (Q:440-441). Judgement only on conflicts, which go to Ray. Grants still went out of order (Q:452) | Q:248, Q:440-452, Q:466; PH spec row 7 (`PH/docs/specs/process-hardening-2026-10-04.md:54`) |
| D2 | **Shipper for the dotfiles main checkout**: run `mise run ship`, rebase lane branches, detach lane worktrees, switch main back to `main` | Its turn in the queue, plus a lane reporting "READY sha" | Branch and head, the lane's gate and review verdicts | PR opened with auto-merge armed; ship log; main-checkout HEAD changes | `pr.py` via `mise run ship`; Q; job-dir logs | 31 SHIPPED/SHIPPING lines; about 1 ship per coordinator session on 10-04 | Mechanical, apart from rebase-conflict calls | Q:1, Q:235, Q:351-352, Q:366, Q:398, Q:402; 04l:34, 04l:47-54 |
| D3 | **Lander**: keep the merged-but-unlanded list, run land loops and retries (`DOTFILES_SMOKE_TIMEOUT_S=3600`) | A PR merge (from a wait log or the watcher), then a free slot | List of merged PRs; land logs | Main checkout synced and smoke-validated; list carried into every handoff | `mise run land`; Q; handoffs | 39 lines; the list appears in ≥14 places (PH spec row 8) | Mechanical | Q:18-19, Q:54-56, Q:467; 04l:40-43; 04l:110 (F4 "lands owed"); PH spec:55 |
| D4 | **KB-shipper GO relay**: send "GO <item>" to the standing KB shipper and track its results | A KB lane is ready, or a KB receipt has been minted | KB receipt state, load, KB queue ruling | SendMessage GO; KB queue order in Q | Q; `.agent/plans/kb-ship-rulings-2026-10-02.md` | 35 "GO <x>" lines | Mechanical | Q:290, Q:296, Q:362, Q:375; `.agent/plans/brief-kbship-20261003.md:3-9` |
| D5 | **Relay / router**: forward lane reports, Ray's asks that arrive via lanes, and PR numbers owed back to lanes; run the retired-coordinator relay rule | Any inbound SendMessage, task notification, or wakeup; a ship result (PR# owed) | Message text, sender | SendMessage to the right lane, Ray, or successor; "Promises to lanes" lists | Handoffs, Q | 15 broadcast/told/relayed lines; 32 ack lines; "PR# owed to: capfix, autostart, lane-G… SLOT GOs owed: …" | Mechanical routing, though today it is done by an LLM interpreting text | 04l:8-13 (RELAY RULE), 04l:56-59; Q:213-220 (21 misrouted messages triaged); Q:230 |
| D6 | **Takeover and broadcast announcements**: tell every lane "I am the coordinator"; PAUSE, PREP and RESUME broadcasts | Successor start; a Ray directive (for example "no codex until MR-A lands") | ListAgents | 14–19 SendMessages per event, then ack storms | `coordinator_handoff.py:705-706` (brief step 2) | 9 OWNER CHANGE blocks; 19 PAUSE/RESUME/PREP lines; "All 19 bg lanes told" | Mechanical | Q:283-287, Q:299, Q:307-321, Q:497, Q:521, Q:526, Q:538; PH spec row 9 (:56) |
| D7 | **Question batcher**: queue questions to Ray in the AskUserQuestion format (Recommended first, PRO/CON, citation, closing "anything else?") | A lane escalation, a spec decision, a residual risk | Lane reports, specs | AskUserQuestion; a "Queued questions" section in every handoff | Handoffs; `coordinator_handoff.py:685-688` (format rule) | 17 "ask/asked Ray" lines; 12 of 12 handoffs carry "Queued questions" (88 lines total) | Judgement: framing the options and the recommendation | 04l:68-80; `coordinator_handoff.py:132` and the `queued_questions()` function at :441-449 |
| D8 | **Ruling recorder**: write Ray's rulings verbatim into `task_plan.md` coordinator blocks, Q, and handoffs; act on them | An AskUserQuestion answer; a Ray message; a ruling relayed by a lane | The answer text | `task_plan.md` blocks, Q lines, handoff "Ray rulings" sections | `task_plan.md` (the coordinator is its sole writer), `mise run handoff-inbox -- plan-apply` | 48 "Ray …" lines in Q (107 mentions of "Ray"); 5 handoffs carry a "Ray rulings" section (71 lines) | Judgement, because of provenance: PH row 1 found side-agent advice recorded as a "Ray ruling" | `handoff_inbox.py:15-20`; `coordinator_handoff.py:704`; `task_plan.md:2660-2668`, `task_plan.md:2716-2721`, `task_plan.md:2843-2847` |
| D9 | **Handoff scribe**: write the handoff at 30% context; the successor reviews the transcript and adds errata | `session.measure` hook at 30% (`DEFAULT_LIMIT_PCT`) | The whole session state | A tracked `docs/handoffs/session-…md`, shipped as a docs PR (itself a ship and land) | `.claude/skills/coordinator-handoff/SKILL.md`; `coordinator_handoff.py:81` | 13 handoffs on 10-04 (a–m); 10 of them carry Corrections/Errata sections (254 lines) | Judgement (recall), which is the defect: every audit found lost or incorrect items | PH spec row 2 (:49), row 15 (:62); `coordinator_handoff.py:702-704` |
| D10 | **Successor takeover mechanics**: census of heavy runs, adopt or wait, retire gate, delete crons, copy the job dir | Successor launch | The census in the brief, the old session's state.json | `retire` rc; adopted waits; `.agent/state/retired-jobs/<id>` | `mise run coordinator-handoff -- retire`; bounded-wait | 24 OWNER CHANGE/RETIRED lines | Mechanical, except the `--accept-inflight` judgement | `coordinator_handoff.py:707-722`; Q:415, Q:430, Q:460, Q:481, Q:532; 04l:86-88 |
| D11 | **Lane launcher**: write the brief, run `claude --bg` inside the worktree, follow with SendMessage START | Ray asks for a lane; the queue needs one | Spec or brief | New lane session; brief file | `.agent/plans/brief-*.md`; `parallel-work-split` skill | 16 LAUNCHED lines | Judgement on scope and brief; launching is mechanical | Q:370, Q:376, Q:393, Q:425 (START trap), Q:433 (Ray: START after every launch) |
| D12 | **SDLC dispatcher and settler**: dispatch sdlc-team or codex runs; on settlement, persist verbatim, check arms, commit, gate, then Opus cold review | A Ray "/codex-sdlc-team" ask; a lane needing a respec; a settlement | Spec, run id, wait log | Persisted reports; commits on lane branches; review verdicts | `mise run sdlc-team`; `docs/research/kb/reports/agents/` | 92 "review" lines in Q; every handoff's In-flight table is mostly sdlc runs | Judgement (reading verdicts, deciding to respec) | 04l:35-38; 04i:27-38; PH row 11 (:58) |
| D13 | **Ticket filer** | Review LOW findings, gaps, Ray asks | Findings | GitHub issues | `gh` | 19 "Filed/filed" lines | Mechanical once a finding is ruled "ticket" | Q:438, Q:485, Q:316; 04l:104-106 |
| D14 | **Heartbeat, self-wake, respawn**: session cron that respawns retired lanes and reads the inbox | Cron at minutes 17 and 47 | Inbox, ListAgents | Respawns, inbox actions; crons that must be deleted at retire | CronCreate/CronDelete | 13 cron/heartbeat lines; recreated by each successor | Mechanical | Q:411, Q:426, Q:431, Q:460, Q:470, Q:479; 04l:15-18 (revival defect) |
| D15 | **Host health and orphans**: watch load, orphaned container pytest or smoke, ask Ray to `pkill` | Land smoke timeout; load spike | `docker exec ps`, load | Ray asked to kill; slot freeze ("HOST GATE FREEZE") | Q | 11 census lines; 18 FAILED/rc=1 lines | Detection is mechanical; the kill is Ray-only (harness-denied) | Q:19, Q:38, Q:208, Q:248, Q:377; 04l:28, 04l:40-43 |
| D16 | **Main-checkout custodian**: drop stashes by SHA, clear stale index.lock, return HEAD to main, remove or archive worktrees and branches | After ships; Ray rulings | git state | A clean main checkout | git | 6 stash lines, plus index.lock and worktree-removal entries | Mechanical, apart from "is this stash mine" | Q:203, Q:272, Q:352, Q:467 (fetch race), Q:487, Q:511-512 |
| D17 | **Admin-merge broker**: hand KB REQUIRED PRs to Ray; verify `enforce_admins` is restored | The KB shipper reports green-except-live-evidence | PR number and head | A ping to Ray; protection verified | `gh api` reads | 6 or more | Ray-only action; the verification is mechanical | Q:300-304, Q:345, Q:349, Q:433(1); PH §8 Q7 (:223) |
| D18 | **Inbox reader**: read `.agent/plans/handoff-inbox/*.md` at start and on heartbeat | Session start; heartbeat | 16 inbox files (502 lines) | Actions on what it finds | `mise run handoff-inbox -- list/read` | Every takeover | Mechanical | `coordinator_handoff.py:690-691`; Q:209, Q:220 |
| D19 | **Plan and queue writer**: prepend a "CURRENT" block to Q and edit `task_plan.md` | Every state change | — | Q now has 38 header blocks and 103,537 B, 37 of them stale (PH row 7) | Q via `handoff-inbox queue-append` | 38 blocks | Mechanical but done by hand | `handoff_inbox.py:15-20`; PH spec:54 |

## (b) Proposed owner per duty

| Duty | Proposed owner | One-line reason |
|---|---|---|
| D1 slot arbitration | **slot-arbiter** | Ray ruled order, then holds, then FIFO, plus a load cap (PH §8 Q1, :216). It is a deterministic policy and needs no coordinator context. The deterministic home is `host_lock` leases and tickets (PH spec items 4/14). |
| D2 ship | **shipper** | The "one shipper per repo" ruling already exists, and the KB shipper is the working precedent (`brief-kbship-20261003.md:3`). |
| D3 land and land-backlog | **shipper** | Land shares the main checkout with ship and needs the canonical-checkout writer key (PH row 22, :74). The backlog can be derived (`land-backlog`, PH row 8). |
| D4 KB GO relay | **slot-arbiter**, which sends GO directly to the KB shipper | The GO is a slot grant on the host resource. |
| D5 relay and PR# promises | **relay/router** | This is what Ray asked for: a router that intercepts coordinator-bound messages (PH §8 Q3, :218). Overlaps R-a3 PR2 (durable inbox). |
| D6 takeover broadcasts | **relay/router** | Lanes address a stable role, not a session, so a takeover needs zero broadcasts (PH row 9 :56; R-a3 PR2 `sdlc-review-coordinator-roles-a3d6e816.md:206-210`). |
| D7 question batching | **question-batcher** | The AskUserQuestion format is a fixed contract (`coordinator_handoff.py:685-688`). Batching across specialists stops each one interrupting Ray. |
| D8 ruling recording | **coordinator-keeps** (the question-batcher records answers to its own questions) | `task_plan.md` has one writer (`handoff_inbox.py:15-20`), and provenance needs judgement (PH row 1). |
| D9 handoff writing | **handoff-scribe** | Most of a handoff is derivable from specialist state (see e). The scribe assembles the capsule (R-a3 PR1; PH §8 Q5 blocks launch on lost custody). |
| D10 takeover mechanics | **handoff-scribe** (and the relay-rule-r2 code) | This is lifecycle code in `coordinator_handoff.py`, owned by relay-rule-r2 (PH review :630). |
| D11 lane launch | **coordinator-keeps** (decomposition and briefing); the launch itself is the #1675/#1688 python | Choosing scope is judgement. The START and liveness quirks are mechanical (PH row 24). |
| D12 sdlc dispatch and settle | **coordinator-keeps**, routed through the slot-arbiter | Verdicts need judgement. Settlement waits should become typed (PH rows 11 and 17). |
| D13 ticket filing | **question-batcher** (it already batches "ticket or fix?") or **coordinator-keeps** | Low volume. Filing is mechanical once ruled. |
| D14 heartbeat and respawn | **relay/router** (or a watcher-style supervisor) | This is the watcher's existing job (`.agent/state/watch/WATCHER.md`). |
| D15 host health and orphans | **slot-arbiter** | A load-aware admission policy (PH row 10c); the kill stays Ray-only. |
| D16 main-checkout custody | **shipper** | It is the single main-checkout writer (PH row 22). |
| D17 admin-merge broker | **question-batcher**, which pings Ray | Ray-only command; never agents (PH §8 Q7). |
| D18 inbox reading | **relay/router** | The inbox is the router's durable queue. |
| D19 queue and plan blocks | Q → **slot-arbiter** (`slot queue --json` replaces Q, PH row 7); `task_plan.md` → **coordinator-keeps** | Q stops being an authority. |

## (c) Rulings that bind (citations)

1. **One shipper per repo.** Lane briefs say: "The coordinator ships from the main checkout (one shipper per repo)" (`.agent/plans/brief-lane-A-2026-10-02.md:14`, and the same line in lanes B, C, E, G, KB2 and KB3). Origin: "Only ONE session ships/lands from the dotfiles MAIN checkout at a time. Agreed 2026-10-02" (Q:152). Restated in the successor brief: "one shipper per repository (dotfiles ships from its main checkout)" (`python/src/dotfiles_setup/coordinator_handoff.py:692-693`); also in `task_plan.md:1002` and `.agent/plans/coordinator-creation-requirements-2026-10-02.md:26`. The KB repo has its own shipper: "the ONLY shipper for the knowledge-base repo" (`.agent/plans/brief-kbship-20261003.md:3`). The per-repo reading was raised as an open question at `.agent/plans/parallel-lane-plan-2026-10-02.md:71`.
2. **One heavy run host-wide.** "Policy tightened: ANY test run (targeted too) needs a 'SLOT <lane>' — one at a time host-wide" (Q:248). "HOST SLOT: one heavy test/gate run host-wide at a time" (`coordinator_handoff.py:692`). Handoff headers say "ONE heavy run host-wide" (04a:82, 03q:32, 03r:59, 03s:64, 03t:64); see also 04b:61, 04h:57, Q:550. Widened: "no pytest/container/image work of ANY size while a land is in its smoke step" (04l:64). "A push = a heavy run" (Q:437, Q:441). KB container work holds the host slot; dotfiles does not, pending an A/B test (04j:13).
   - **The exact phrase "one test slot" returned nothing.** Control: "one heavy" hit 14 lines in the same paths.
3. **Ruled slot order is fixed** and checked before every grant. "The slot is free and the run is short" never overrides it; conflicts go to Ray (Q:440-441, re-affirmed Q:462).
4. **Scheduler, advisory or executing.** The rulings moved in four steps:
   - Ray asked for a specialist review of a ship/land scheduler (04h:12-17).
   - Ray ruled "Scheduler = **EXECUTING**, not advisory … the ONLY authority on when to ship/land" (04i:14-19; `task_plan.md:2664`).
   - Ray then adopted D1/D4/D5/D7 option 1: per-resource queues, one launchd daemon, ship/land only via the scheduler (04j:11-12; `task_plan.md:2718-2721`).
   - The R-a3 review recommends an *advisory* scheduler (`sdlc-review-coordinator-roles-a3d6e816.md:1, :190, :216-221`). The PH review flags "Adopt an executing scheduler daemon" as "Needs Ray's decision" (`PH/docs/research/kb/reports/agents/sdlc-review-process-hardening-1d8f7d46.md:148`).
   - **Latest ruling, 2026-10-04 ~19:15: "Q3 scheduler: neither."** Ray instead wants specialised parallel standing agents like the watcher, plus a Claude-mods router that intercepts coordinator-bound messages. Recorded at PH spec §8 :218 and `task_plan.md:2845-2847`; the owning lane is `dotfiles-20261004T191624-05.coord-router`.
5. **Slot through CI:** release after push, which is today's behaviour (PH §8 Q2 :217; `pr.py:682-707`).
6. **Load policy:** recorded order and holds first, then FIFO, plus a load cap (PH §8 Q1 :216).
7. **Capsule blocks launch on lost custody,** with an override flag (PH §8 Q5 :221).
8. **The coordinator delegates and never works inline** (Q:5). Keep the 30% handoff limit (04h:10-11; `task_plan.md:2661`; `coordinator_handoff.py:81`). Cut takeover messaging and handoff tokens; Ray does not trust the handoff (04h:11-13).
9. **Relay rule (mandatory):** a retired session forwards everything verbatim to its successor by name and acts on none of it (04l:8-13).
10. **Autonomy:** ask Ray only for items that need a human (`coordinator_handoff.py:682-684`; Q:302). Ping Ray per KB PR when an admin merge is needed (Q:433). Admin merge is a Ray-only command (PH §8 Q7 :223).
11. **Writes:** never route a refused main-checkout write through Bash; use a mise task instead (03f "Rulings"; memory `project_session_2026-10-03-watch.md`). `plan-apply` and `queue-append` are for the newest coordinator only (`handoff_inbox.py:15-20`).
12. **Watcher rulings (12:57):** a separate launchd supervisor; the lane runs after llvm23; the watcher limit is configurable with a default of 30%; interim mutual revival is allowed; keep `coordinator-handoff --role` (Q:469; `task_plan.md:2561`). Scope was extended to unattended `/session-handoff` for watchers and every lane (Q:493).
13. **Process-hardening specs:** auto-dispatch each as its own lane after premise-verifier, one heavy slot at a time (`task_plan.md:2827-2828`).

**Search for the literal "RULING" in uppercase:** it hit 04a:131/137, 04b:19, many `task_plan.md` lines, and `kb-ship-rulings-2026-10-02.md:38/40/131/136`. None of these is a slot or shipper ruling beyond those listed above.

## (d) Coordinator naming and addressing

**Name format and matching**
- Format: `dotfiles-yyyyMMdd'T'HHmmss.<9-digit ns><offset>.coordinator`, Chicago time (`coordinator_handoff.py:424-426` → `session_common.stamped_name`, `session_common.py:178-180`).
- Role match is the regex `^dotfiles-.+\.coordinator$` (`session_common.py:41`), read from the bg job record (`session_common.py:94-96`). Legacy names still match: `dotfiles-20261002b.coordinator`, `dotfiles-20261002.coordinator` (Q:184). `dotfiles-20261001.000` does not match.

**Rename frequency on 10-04**
- 13 distinct coordinator names appear on 10-04, from `…T004823.636657000-05` through `…T181409.677303000-05` (grep over handoffs, Q and `task_plan.md`). The address changes about every 1–2 h.
- Each successor's name is new: it is `successor_name(now_ns)`, so nothing about it can be predicted.

**How lanes find the coordinator**
- Lanes report BY NAME. If the coordinator has handed off, they use "the newest coordinator by ListAgents recency"; the fallback is `.agent/plans/handoff-inbox/<lane>.md` (`.claude/skills/parallel-work-split/SKILL.md:152`; `coordinator_handoff.py:690-697`).
- Briefs hard-code the coordinator name current at launch. Examples: "Coordinator: `dotfiles-20261002b.coordinator`. Report to it BY NAME" (`.agent/plans/brief-1502-20261002.md:3`, `brief-kb837-20261002.md:3`, `brief-llvm23-20261002.md:3`, `brief-kbship-20261003.md:3`). That is why every takeover needs a broadcast (D6).

**Three different "newest coordinator" rules are in use**
1. ListAgents recency (`coordinator_handoff.py:694-697`).
2. Newest `createdAt` across coordinator-named job records, used for the `handoff_inbox` write gate (`handoff_inbox.py:22-27`, `:174`).
3. The watcher sorts by `startedAt` (`.agent/state/watch/tick.py:101-102`; WATCHER.md "Alert rules"). This caused the revival or spurious-successor defect (04l:15-18; #1681). The premise was settled by a live probe: `startedAt` is the live process start, falling back to `createdAt` when stopped (`task_plan.md:2838-2839`).

**Inbox**
- Inbox constant: `HANDOFF_INBOX = .agent/plans/handoff-inbox` (`session_common.py:44`). `append` is open to any caller and works from linked worktrees (`handoff_inbox.py:1-13`). An older gap, where worktree lanes could not write the inbox, is recorded at Q:507-508.
- Retiring coordinators leave `coordinator-<short>-late.md` notes in the inbox. Examples: `handoff-inbox/coordinator-fa773e-late.md:1`; the eba10b and f5b237 files.
- The inbox currently holds 16 files, 502 lines in total.

**Non-coordinator names**
- Standing-specialist names: `kb-20261004T160517.615658000-05.ship` (KB shipper, Q:39) and `dotfiles-20261003.watch` (watcher, date-only legacy format, 03f:4).
- Newer lanes use a short stamp without nanoseconds: `dotfiles-20261004T191624-05.coord-router` (PH spec :218) and `dotfiles-20261004T175336-05.graphify-plan` (`coordinator-fa773e-late.md`).

### Watcher template (source 4)
- **Standing instructions** live in the main checkout at `.agent/state/watch/WATCHER.md`, with `tick.py` (134 lines), `q.py`, `tail.py`, `agents.json` and `coord-watch.json`. The state directory *is* the handoff: "launch your successor the same way you were launched: copy nothing" (WATCHER.md, last section).
- **Each tick is every 10 minutes.** It reports state, status and waitingFor; uncommitted files; branch heads and merged PRs; codex launches; and coordinator health.
- **Alerts go only to the newest coordinator.** After 30 minutes unreachable, it falls back to `handoff-inbox/watch.md`. It never alerts on intentional "SLOT/GATES GO" holds, re-alerts at most every 30 minutes, and tells Ray directly when a lane needs him (WATCHER.md "Alert rules"; the `watch.md` inbox shows about 30 such entries).
- **It auto-launches a successor coordinator** via `mise run coordinator-handoff -- launch` once the newest coordinator has been done or blocked for at least 10 minutes (`tick.py:94-127`; Ray ruling, WATCHER.md "Coordinator auto-launch").
- **It holds its own heavy push** until "SLOT watch-push GRANTED", so the watcher consumes slots too (WATCHER.md; Q:464).
- **End condition:** every tracked branch is merged and no lane is blocked.
- **Watcher succession:** `dotfiles-20261002.watch` (998ab91b) → `dotfiles-20261003.watch` (7585361b). The old cron 3cb12569 was deleted (03f:4). The memory file `project_session_2026-10-03-watch.md` records that an auto-handoff needs a trigger outside the session.
- **Planned generalisation:** a `Role` registry with `coordinator-handoff --role watch`, plus a `fanout-watch` mise task porting `tick.py` (`.agent/kb/raw/watcher-handoff-plan-2026-10-03.md:20-52`). This is the natural template for standing specialists.
- **The watcher's own launch command was not found.**
  - Searched: `claude --bg.*watch|watch.*claude --bg|/loop 10m|launched .*watch` over the 10-03 handoffs, `task_plan.md`, Q and WATCHER.md. Nothing came back.
  - Control: the term `claude --bg -n dotfiles-<Chicago ISO ns>.coordinator` hits `.claude/skills/coordinator-handoff/SKILL.md:86`.
  - Likely cause: the watcher was launched ad hoc by a Ray ruling (`recovery-handoff-7541ae79.md:30`).

## (e) Handoff weight

**Totals**
- The 10-04 handoffs a–l total **1,374 lines and 129,429 B** (12 files; per file: a 160, b 136, c 163, d 156, e 123, f 57, g 50, h 91, i 128, j 107, k 87, l 116).
- Adding 04m (90 lines, 9,901 B; it exists only in the worktree `.claude/worktrees/handoff-2026-10-04m`) gives **1,464 lines and 139,330 B over 13 handoffs in one day**, about 113 lines each.
- Each handoff is also a docs-only ship plus a land, so it consumes slots (Q:1, Q:442, Q:455).

**Carried state files**
- Q: 103,537 B, 606 lines, 38 header blocks; PH says 37 of the blocks are stale (PH spec row 7 :54).
- `task_plan.md`: 271,950 B now. PH measured 267,714 B (PH spec P10 :198), so it is still growing.

**Section totals across a–l** (each H2 section's lines summed; the rest is headers and preamble)

| Lines | Files | Section |
|---|---|---|
| 254 | 10 | Corrections / Errata / Successor review |
| 244 | 11 | Done this session |
| 113 | 8 | Owed next |
| 109 | 10 | In flight |
| 90 | 4 | State at handoff |
| 88 | 12 | Queued questions |
| 71 | 5 | Ray rulings |
| 68 | 12 | Gotchas / Traps |
| 50 | 4 | Ship queue |
| 28 | 1 | Ready / queued |
| 21 | 2 | Late update |
| 16 | 1 | Lane notes |
| 13 | 2 | Promises to lanes |
| 11 | 1 | Relay rule |
| 10 | 1 | Ratified specs |
| 7 | 1 | Root cause |

**Sections that exist only because the coordinator holds the state** (my classification):
- **Ship queue, Ready/queued, Owed next** (slot order, ship and land lists): about 191 lines. Would move to the slot-arbiter and shipper (`slot queue --json`, `land-backlog`).
- **In flight** (109): mostly the coordinator's own land loops, wait logs and sdlc runs (04i:27-38; 04l:30-38). Would move to per-specialist state and typed waits.
- **Promises to lanes and Lane notes** (29): router state (04l:56-59).
- **Queued questions** (88): question-batcher state. The successor brief re-parses it (`coordinator_handoff.py:441-449`).
- **State at handoff** (90): fully derivable from git and gh (04d:7-30).
- **Late update** (21) plus the `coordinator-*-late.md` inbox notes.

That totals about **528 lines, roughly 38% of a–l**. A further **254 lines (about 18%)** are Corrections/Errata, which exist because the handoff is written from memory (PH row 2 :49: every audit found LOST or INCORRECT items). Most of the remaining "Done", "Ray rulings" and "Gotchas" content is what the coordinator would keep or what the capsule derives.

## PH synthesis: findings on coordinator load (reused, not redone)

**Ledger rows** (`PH/docs/specs/process-hardening-2026-10-04.md`)

| Row | Line | Topic |
|---|---|---|
| 7 | :54 | Slot is free-text SendMessage; the queue file is the authority; fix is command-owning leases plus a FIFO in `host_lock`; "the coordinator stops granting" |
| 8 | :55 | `land-backlog` |
| 9 | :56 | 17–20+ takeover messages; R-a3 PR2 role binding |
| 15 | :62 | About 12 auto-handoffs a day; "context is spent relaying and waiting"; move slot, land and R-a3 PR2/PR3 work out of the coordinator; tokens per coordinator-hour as a metric |
| 22 | :74 | Per-repo canonical-checkout writer key |
| 25 | :77 | Lost messages; durable inbox |
| 1 / 2 | :48-49 | Asks ledger and obligation carry-forward, the handoff-size and recall fix |
| 14 | :61 | Plan and queue bytes |

Class mapping: classes C2 and C8 (:92, :98) carry these rows. Candidate spec #1 (:165-167) is the slot queue.

**Review** (`…sdlc-review-process-hardening-1d8f7d46.md`)
- **:73:** a returning `slot acquire` cannot keep a flock, so the slot must be command-owning.
- **:84 (C2):** CPU, canonical-checkout and worktree ownership are separate resources and must not become one lock (:97).
- **:143-149 (licensed dissent)**, open for Ray:
  - expanding the slot across a whole ship or session;
  - an executing scheduler daemon;
  - "send zero takeover messages" requires amending every-lane delivery while keeping reachability evidence.
- **Item 14 (:443-449):** FIFO tickets; "no daemon authority"; hard order and holds come before FIFO.
- **Ownership map (:625-638):**
  - R-a3 PR2: roles, epochs, durable inbox.
  - R-a3 PR3: advisory scheduling.
  - relay-rule-r2: all `coordinator_handoff.py` changes.
- The router lane must coordinate with all three.

**PH §8 (:212-226):** Ray's Q1–Q8, including Q3 "neither", which creates the coord-router lane. Items 10 (the procedure kernel) and 25 (pending land) coordinate with it.

## Search controls and empty results

| Search | Result | Control |
|---|---|---|
| "one test slot" | Empty | "one heavy" returned 14 hits |
| Watcher launch command | Empty | `claude --bg -n …coordinator` hit `SKILL.md:86` |
| `session-2026-10-04m.md` in the main checkout's `docs/handoffs/` | Absent | Found in the worktree `handoff-2026-10-04m` |

Some greps were blocked mid-run: the guard denied unquoted `echo ====`. They were re-run with quoted separators.

**Caveat on counts:** they are regex counts over prose, so treat them as order-of-magnitude, not exact.

