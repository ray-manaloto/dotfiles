# Unattended /session-handoff for every session role, merged to main with zero human steps (2026-10-03)

- **Lane:** `handoff-automation-research`, branch `research/session-handoff-automation`. Brief: `.agent/plans/brief-handoff-automation-research-20261003.md` (main checkout). Reports to `dotfiles-20261003T140808.926861000-05.coordinator`.
- **Sweep (ran first, per the brief):** `research-sweep-run` run `wf_fb80194b-e1e`. 17 agents, status `complete`, no mandatory gaps, 5 load-bearing claims refuted or adjudicated. Full output: `docs/research/kb/reports/agents/session-handoff-automation-sweep-2026-10-03.md`. This report adds the local findings, the decision options and the spec outline.
- **Scope:** research only. Nothing is implemented. Every recommendation below waits on coordinator or Ray ratification.

## Answer

**No single native Claude Code feature does this end to end, and none is coming:**

- The three upstream requests that would have provided it were closed *not_planned*:
  - #80269, a context-threshold hook (closed 2026-09-04 by the inactivity bot);
  - #85289, injecting a control command into a running session (closed 2026-09-15 by the stale bot);
  - #77869, worktree auto-sync (closed 2026-09-18). Probe: `gh issue view`; control #80269 reads CLOSED on the same route.
- #90089 (threshold auto-clear) and #95199 (PreClear) are still open requests.

So the answer is the design this repo already shipped for coordinators (#1583: `session.measure` → python `decide` → `$.command.run(skill)` → successor via `claude --bg` → retire). It needs three changes to cover every role:

1. **Make the trigger immune to hook/CLI version skew** (F1). Without this, extending it to lanes extends a known failure.
2. **Replace the coordinator-only name gate with a role registry** (`coordinator`, `watch`, `lane`), each role with its own handoff skill.
3. **Route lane and watcher output through channels a worktree can reach:**
   - its own branch;
   - GitHub issues;
   - native cross-session messaging.

   Do not route it through the main-checkout inbox (the Lane-G gap). Merge rides `mise run ship` plus GitHub auto-merge, already proven unattended by #1604 and #1608.

**Propagation to sessions already running is the part with no native answer.** Successors pick up `main` when they start. Live sessions need an explicit "main moved" message, plus a rebase and `/reload-plugins` at their next boundary. That custom step is justified because #77869 is closed *not_planned*.

## Local findings (each with its control arm)

### F1: "decide rc 2" and "pending rename failed" come from hook/CLI tree skew, a class defect

The coordinator confirmed this independently, by a second route: `docs/research/kb/reports/agents/llvm23-lane-hook-errors-2026-10-03.md`.

**The lane's tree predates #1583:**
- Lane `…llvm-23-bump` (`6fae0fec`) is at `87599224`.
- #1583's merge is not an ancestor of it (`git merge-base --is-ancestor` → NO).
- Its `python/src/dotfiles_setup/main.py` registers no `coordinator_handoff` or `session_start` subcommand. Its one match is a help string at `:575`. Control arm: the same grep on main returns 11 matches.

**The hook module and the CLI it calls come from different trees:**
- The job record (`~/.claude/jobs/6fae0fec/state.json`) has `cwd` set to the **main checkout**. Project `@skills-dir` plugins load from the primary working directory at session start (`$CC/plugins-reference.md:402`), so the hook modules came from main.
- The hooks then run `uv run --project python dotfiles-setup …` with cwd `$.env.get("CLAUDE_PROJECT_DIR") ?? $.session.root()` (`coordinator-handoff/hooks/register.ts:113-136`, `session-start/hooks/register.ts:106-108`), and that resolved to the lane's tree.
  - **Correction (2026-10-03, proposals report, and `session-role-identification-research-2026-10-03.md`):** an earlier revision said `CLAUDE_PROJECT_DIR` "is the lane's tree". That contradicts the docs and upstream. `CLAUDE_PROJECT_DIR` stays at the launch directory across `EnterWorktree` (`$CC/hooks.md:626-630`; anthropics/claude-code#87890, staff-reproduced; #99145).
  - The worktree most likely came from the `$.session.root()` fallback, which follows a worktree move (`.claude/types/claude-code.d.ts:2362-2368`). This is inferred, not proven: an in-process env is invisible to `ps`.
- In the lane's tree argparse rejects the unknown subcommand and exits with rc 2.

**Why `/reload-plugins` does not fix it:** it re-registers the same modules, and they call the same stale CLI.

**The main checkout's own branch also drifts.** It read `docs/handoff-2026-10-03e` at `git worktree list` time and `main` a few minutes later. "Resolve from the main checkout" therefore means "from whatever the main checkout holds right now", not "from main".

**The hook can name its own tree.** The function-hook API exposes `$.plugin.root`, "the plugin's directory (the one holding plugin.json), absolute" (`.claude/types/claude-code.d.ts:2026-2028`). The module can therefore invoke the CLI of the **same tree it was loaded from**. That makes module and CLI consistent by construction, whatever branch either side is on.

### F2: Native building blocks (offline docs, `$CC` = KB `agent-harness-docs/docs/claude-code`)

| Need | Native mechanism | Citation | Limit for this problem |
|---|---|---|---|
| Context % producer, in session | Function-hook event `session.measure` | `register.ts:296`; works live here (#1583 receipt) | Not in the `$CC` corpus (0 hits), so stability is unverified; loads only at start or `/reload-plugins` |
| Context % producer, display | statusLine `context_window.used_percentage` | `$CC/statusline.md:62,104,186` | Runs only while the UI renders; unverified for unattached `--bg` sessions |
| Earlier compaction | `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` (1-100, can only lower the threshold) | `$CC/env-vars.md:196` | Compacts; it does not hand off. Interaction with idle compaction (#98747) is unmeasured |
| Before/after compaction | `PreCompact` (`auto`/`manual`, can block), `PostCompact` (`compact_summary`), `SessionStart` `source:"compact"` | `$CC/hooks.md:3046-3100`, `:1152` | A command hook gets no turn |
| Hot-reloading hooks | `settings.json` hooks reload live | `$CC/settings.md:584` | Read from the session's project `.claude/settings.json`, which is branch-scoped in a worktree |
| A hook posting text into its own session | Inbox socket `CLAUDE_CODE_MESSAGING_SOCKET`, plus `CLAUDE_CODE_MESSAGING_TOKEN` | `$CC/cross-session-messaging.md:264-279` | Arrives as a peer message, not as a slash command; untested as a trigger |
| Session to session | `ListAgents` / `SendMessage` | `$CC/cross-session-messaging.md:13-17` | Text only; cannot run `/clear` (#85289 maintainer reply, via the sweep) |
| Successor | `claude --bg "<prompt>"`, `claude stop`, `claude respawn` | `$CC/agent-view.md:430-436,693-696` | `--bg` rejects `-p`, so `SessionStart.initialUserMessage` cannot seed it (`$CC/hooks.md:1190`) |
| Telling done from paused | Stop input `background_tasks` and `session_crons` | `$CC/hooks.md:2542-2546` | Stop hooks force a turn (memory `feedback_stop_hooks_force_a_turn`) |
| Native PR from a lane | A bg worktree session may open a **draft** PR | `$CC/agent-view.md:519-522` (current body) | Only when the task calls for it; never merges; collides with the `gh pr create` guard and ship-only rule |
| Merge | GitHub auto-merge | Repo: `allow_auto_merge=true`; ruleset `19868073` "main: require a pull request" (0 approvals); required check `ci-gate`; **no merge queue rule** (`gh api` 2026-10-03) | Concurrent handoff PRs serialise only through ship's host slot |

### F3: Lane-G, the inbox gap, has a native replacement

Worktree lanes cannot write `.agent/plans/handoff-inbox/` in the main checkout (brief; the watcher-plan report's Bash refusal is the same boundary). `SendMessage` to the newest coordinator, plus tracked files on the lane's own branch, covers the same need without crossing the worktree boundary. The receiving coordinator persists the message at receipt, under `agent-report-persistence.md`.

## Options (with a recommendation for each decision)

### D1: How to make every hook survive hook/CLI skew

| Option | PRO | CON | Evidence |
|---|---|---|---|
| **S1 (Recommended): the module invokes the CLI from the tree it was loaded from.** `uv run --project <git toplevel of $.plugin.root>/python …`. Every `@skills-dir` module (coordinator-handoff, session-start, install-doctor) uses one shared resolver | Consistent by construction; no user-level write; a small TS change in each module; F1 cannot recur | `uv run` now syncs the **main checkout's** venv from inside lane sessions. Concurrent syncs need a check against the host's one-test-slot rule. State paths must stay explicit, since `main_checkout(Path.cwd())` changes meaning | `.claude/types/claude-code.d.ts:2026-2028`; F1 |
| S2: resolve the CLI from the first entry of `git worktree list` (the sweep's option (a)) | No API dependency | Equals S1 only when the session started in the main checkout. It still skews when a session starts elsewhere, and it binds to whatever branch the main checkout holds | sweep §Recommendation 2; F1's branch-drift note |
| S3: personal-scope plugin (`~/.claude/skills/`) plus a versioned `uv tool` CLI | Loads in every project; versioned; no trust gate | A user-level write (memory `feedback_no_user_level_file_updates`) that needs Ray's ruling; adds an install and update step for the doctor to police | `$CC/plugins-reference.md:387-389` |
| S4: in addition to the above, a failure caused by a missing subcommand becomes a `handoff n/a (CLI skew: rebase onto main)` status instead of `ERROR` | Honest signal; cheap | Not a fix on its own; a lane at the limit still has no handoff | `register.ts:136` |

Recommend **S1 + S4**.

### D2: What triggers a lane's or watcher's handoff

| Option | PRO | CON | Evidence |
|---|---|---|---|
| **T1 (Recommended): the existing `session.measure` hook with a role registry.** Thresholds per role: coordinator 30, watch 50, lane 40. The `decide` JSON names which skill to submit | Reuses shipped, live-proven machinery; one `uv run` per measurement | `session.measure` is undocumented; skew-fragile until D1 lands | `register.ts:283,296`; watcher plan §1 (role registry already drafted) |
| T2: a settings `PreCompact`/`Stop` command hook posting to the session's own inbox socket | Hot-reloads (immune to the "started 45 s early" failure) | Untested; a message is not a command; Stop forces turns; settings are branch-scoped in a worktree | `$CC/settings.md:584`, `$CC/cross-session-messaging.md:264-279` |
| T3: an external launchd `KeepAlive` supervisor reading transcript `usage` | Fires even when the session is wedged or full | A host daemon with its own spec (event-driven report Rec 1); larger scope | event-driven report (lane branch `0ac9bacd`) |

Recommend **T1 now and T3 as a separate follow-up** (agrees with watcher plan §3). End of lane, as opposed to the threshold, is a **brief-mandated final step** (`/lane-handoff --final`). It is not a Stop hook, because Stop hooks force turns.

### D3: How lane and watcher handoff output reaches main

| Option | PRO | CON | Evidence |
|---|---|---|---|
| **M1 (Recommended):** the lane writes `docs/handoffs/lane-<feature>-<date><letter>.md` and verbatim reports **on its own branch**, files fix-candidate issues through `issue-filer`, and `SendMessage`s a digest to the newest coordinator. The coordinator's next auto-handoff folds the digests into its tracked handoff, which ships with `mise run ship` (proven: #1604, #1608) | Zero new ship traffic (the host slot is the bottleneck); lessons reach main with the lane's PR or the coordinator's next handoff; issues are visible at once | A lane whose PR never merges strands its handoff file. The coordinator must persist the digest at receipt | ruleset / auto-merge probe; `agent-report-persistence.md` |
| M2: each lane ships a separate `docs/lane-handoff-*` PR | Lessons reach main independently | Doubles ship-queue load; a linked-worktree ship is fine for a non-surface diff, but it still takes the host slot | `pr-workflow` SKILL table row `ship: linked worktree` |
| M3: the native bg draft PR | No custom code | Conditional, never merges, bypasses gates, guard-denied path | `$CC/agent-view.md:519-522` |

Recommend **M1**. Add a merge queue only if handoff PRs measurably race; it is unresearched (named gap in the sweep).

### D4: How other live sessions pick up main

There is no native mechanism (#77869 closed *not_planned*). **Recommended:**

1. After `mise run land`, the coordinator `SendMessage`s every live dotfiles session "main → `<sha>`; at your next boundary run the `sync-to-main` step".
2. That step is `git fetch && git rebase origin/main` for a lane, `git pull --ff-only` for the main checkout, then `$.command.run('reload-plugins --force')`. The session-start mod already queues that last command (`docs/specs/coordinator-auto-handoff-2026-10-02.md:356`).
3. Every successor brief starts with the same step.

PRO: closes the F1 class for lanes over time; uses only native messaging. CON: a rebase can conflict, and that must surface as a queued question rather than be resolved automatically. A `watchPaths`/`FileChanged` pointer file is an untested alternative (sweep critic gap).

## What is native, and what custom code survives

- **Adopt (native):**
  - `session.measure` (trigger);
  - `$.command.run` (submit the skill);
  - `$.plugin.root` (skew fix);
  - `claude --bg` (successor);
  - `SendMessage`/`ListAgents` (Lane-G replacement, propagation notices);
  - `claude agents --json --all` (state, per the lane-completion report);
  - GitHub auto-merge with the `ci-gate` ruleset (merge);
  - `reload-plugins` via `command.run` (pickup).
- **Survives (custom), with justification:**
  - `coordinator_handoff.py` decide/launch/retire, extended to a role registry. Nothing native launches a successor with a census of heavy runs, or retires the old session safely (#1609: `claude stop` keeps crons, and the supervisor revives).
  - The per-role handoff skills. These carry judgment, so they are skills, not code.
  - The `sync-to-main` step (#77869 closed *not_planned*).
  - The S1 resolver (the module/CLI pairing is ours).
- **Retire or avoid:**
  - lane writes into the main-checkout inbox;
  - any `/clear` from automation (#85429; not possible);
  - `initialUserMessage` seeding (`-p` only);
  - the native draft PR;
  - a second, parallel trigger mechanism.
- **Dependency:** #1609's ruling (retire through `claude rm`, plus CronDelete enforced before idle) applies to every role. A lane successor that inherits crons revives the same way.

## Proposed seven-part spec outline (for coordinator ratification)

1. **Objective.** Every dotfiles session role (`coordinator`, `watch`, `lane`) runs an unattended role-specific `/session-handoff` at its context limit, and lanes also at end of work. Output reaches main with zero human steps, and live sessions are told to re-sync. Hook/CLI skew can no longer break any `@skills-dir` hook.
2. **Files.**
   - `.claude/skills/{coordinator-handoff,session-start,install-doctor}/hooks/register.ts`: add the S1 resolver and the S4 skew status.
   - `python/src/dotfiles_setup/coordinator_handoff.py`:
     - add the `Role` registry (watcher plan §1 interfaces, plus a `lane` role);
     - match lanes by `^dotfiles-.+\.(?!coordinator$|watch$)[A-Za-z0-9-]+$` with a worktree cwd.
   - New skills `lane-handoff` and `watch-handoff`.
   - `session-handoff/SKILL.md`: add an "Unattended run — lane/watch" section.
   - The `sync-to-main` step:
     - as a `dotfiles-setup` subcommand plus a mise task (zero-bash-logic);
     - with a `land` post-step that messages live sessions.
   - Tests beside the existing `coordinator_handoff` tests and the bun harnesses.
3. **Interfaces.**
   - `decide` returns `{fire, reason, role, skill, level, …}`, and the hook submits `skill`.
   - `launch --role R` and `retire --role R` (default `coordinator`, so existing callers are unchanged). A lane successor is launched **in the lane's worktree**; a coordinator's or watcher's in the main checkout.
   - `sync-to-main [--worktree PATH]` returns rc 0 (synced), 3 (conflict, queued question written) or 2 (refused).
   - Thresholds: `DOTFILES_<ROLE>_HANDOFF_PCT`.
4. **Constraints.**
   - Zero-bash-logic, and no new MCP.
   - No writes outside the session's own tree, except by the coordinator.
   - No user-level writes (unless D1 is ruled S3).
   - Never `task_plan.md` from a lane.
   - Never `/clear`.
   - Ship only through `mise run ship`, under the host-slot rule.
   - #1609's cron cleanup before idle, for every role.
   - Stop hooks only where they force no turn.
5. **Verification** (each item with its fail arm; live, per `real-integration-evidence.md`):
   - (a) A pre-#1583-shaped lane tree with the S1 module gets a real decision, not rc 2. **Fail arm:** revert the resolver and rc 2 returns.
   - (b) The role registry maps coordinator, watch and lane names. **Fail arm:** an unmatched name returns n/a.
   - (c) A live throwaway lane crosses a lowered threshold. Its successor starts in the same worktree, the old lane retires with no revival for 2 h, and the digest arrives at the coordinator. **Control:** below the threshold, nothing fires.
   - (d) A coordinator handoff PR auto-merges with `ci-gate` green.
   - (e) After `land`, a sibling lane receives the message, rebases and reloads, and its next measurement succeeds. **Fail arm:** without the sync, the skew status shows.
6. **Commit.** Three PRs:
   - `fix(hooks): resolve the CLI from the module's tree` (D1, ships first: it is a prerequisite);
   - `feat(handoff): role registry; lane + watch unattended handoff` (D2, D3);
   - `feat(handoff): sync-to-main propagation after land` (D4).
7. **PREMISES** (each to be verified by `premise-verifier`):
   - `$.plugin.root` is absolute and inside the loaded tree (`claude-code.d.ts:2026-2028`, not live-armed);
   - `session.measure` fires in unattached `--bg` lane sessions (unverified for lanes; live only for coordinators);
   - `$.command.run('reload-plugins …')` works from a hook (spec `:356`, as used by session-start);
   - `SendMessage` reaches `--bg` lanes (observed this session: the coordinator ↔ this lane);
   - the role-gate sites are as listed in the watcher plan (`coordinator_handoff.py:74-78,106,197-199,345,426-428,650-728,809,1098`; `register.ts:22,48,99-102,154,221-238`), to be re-read before implementation because they rot;
   - `uv run` in the main checkout from many lane sessions does not collide (unmeasured).

## Queued questions (ask-quality shape, for the coordinator to put to Ray)

1. **D1 skew fix:**
   - **S1 (Recommended):** PRO: no user-level write, consistent by construction. CON: lanes sync the main checkout's venv. Evidence: F1, `claude-code.d.ts:2026`.
   - S3, a personal plugin: PRO: versioned, loads everywhere. CON: a user-level write. Evidence: `$CC/plugins-reference.md:387`.
2. **Lane threshold:**
   - **40% (Recommended):** PRO: lanes are task-bounded and churn less. CON: a larger successor review.
   - 30%, same as the coordinator: PRO: one knob. CON: more handoffs.
   - Evidence: brief cadence (4 coordinator handoffs per day at 30%).
3. **Lane output path:**
   - **M1 own-branch + issues + SendMessage (Recommended):** PRO: no extra ship traffic. CON: a stranded branch strands its handoff.
   - M2 separate docs PR: PRO: independent merge. CON: doubles the ship queue.
   - Evidence: ruleset probe; `pr-workflow` SKILL.
4. **Propagation step:**
   - **Message plus rebase at the next boundary (Recommended):** PRO: native messaging; conflicts surface. CON: custom sync code.
   - Leave lanes stale until their PR lands: PRO: zero code. CON: F1 recurs on every hook change.
   - Evidence: #77869 closed *not_planned*.

## Gaps (not closed by this lane)

- None of S1, T1-for-lanes, the `sync-to-main` step or the inbox-socket trigger was live-armed. This lane was research-only.
- Merge queue is unresearched beyond "not configured".
- Third-party handoff tools are title-only (sweep Gaps).
- `session.measure` documentation and stability are unknown.
- Idle compaction (#98747) versus a 40% lane threshold is unmeasured.
- Every critic gap listed in the sweep report stands.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): #1583, #1604, #1608, #1609; ruleset 19868073; repo merge settings; lane branches (`llvm23` at 87599224, `docs/lane-completion-protocol` at 0ac9bacd); the coordinator-handoff, session-start and session-handoff skills; `coordinator_handoff.py`
- [anthropics/claude-code](https://github.com/anthropics/claude-code): #77869, #80269 (direct `gh issue view`); every other issue via the sweep report
- [anthropics/claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python): via the sweep's dependency fan-out
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): offline `agent-harness-docs` corpus (`$CC`)
- Third-party repos (title only) are listed in the sweep report's enumeration
