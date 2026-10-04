# Unattended session handoff for every session role, threshold-triggered and merged to main: research sweep (2026-10-03)

- **Node:** synthesize (research-sweep-run), model opus, effort high
- **Question:** how can every Claude Code session (coordinator, watcher, many `claude --bg` fan-out lanes, several in git worktrees) run the session-handoff procedure (reconcile plan, persist docs, emit a resume prompt, then `/clear` or hand over to a successor) unattended when context crosses a threshold such as 30%? And how do the resulting doc and plan changes get committed, PR'd, auto-merged and picked up by every other live session with zero human intervention?
- **Companion lane report:** `docs/research/kb/reports/agents/session-handoff-automation-research-2026-10-03.md` (local findings F1 and F2: hook/CLI tree skew, and the native building-block table)

## Answer

**Short version:** Claude Code has **no documented, native, single feature** that does this end to end. It does ship every building block except two:

- an in-session **"context crossed N%" hook event**;
- a supported way for a hook or command to **run `/clear`**.

This repository has already worked around both for the **coordinator role only**, and that path is merging to main unattended today (`#1604`, `#1608`: "auto-handoff at 30% context"). The open problem is the **other roles**, plus propagation to sessions that are already running.

Three kinds of claim are kept apart below: what the vendor **ships**, what users **propose** in issues, and what **third parties** say they built.

1. **Threshold trigger. Shipped: partly, and none of it is the documented hook surface.**
   - The statusLine payload carries `context_window.used_percentage` (`$CC/statusline.md:186`). It is a display producer, not a hook.
   - `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` (1-100, can only *lower* the threshold) moves **compaction** earlier for main conversations and subagents (`$CC/env-vars.md:196`). It compacts; it does not hand off.
   - `PreCompact` / `PostCompact` / `SessionStart(source:"compact")` fire around compaction (`$CC/hooks.md:63,315,1152`).
   - The documented hooks reference has **no** threshold event. `onContextThreshold` and `PreClear` return 0 hits in the offline docs corpus. That probe was armed: `PreCompact` and `used_percentage` hit in the same corpus, and a fresh nonsense string returned 0.
   - The **function-hook plugin API** emits `session.measure` with a percent. This repo subscribes to it (`.claude/skills/coordinator-handoff/hooks/register.ts:296`) and submits a skill through `$.command.run` (`register.ts:283`). The handoff memory of 2026-10-02 records that this path works live. `session.measure` does not appear in the offline `$CC` corpus (0 hits), so it is **shipped but undocumented in that corpus**.
   - **Proposed, not shipped:** `onContextThreshold` plus `CLAUDE_CONTEXT_PERCENT` (issue #80269, **CLOSED not_planned on 2026-09-04 by the inactivity bot, not rejected on merit**); threshold auto-clear with an early-warning interrupt at 90% of the threshold (#90089, open); `PreClear` (#95199, open). `SessionEnd` with reason `clear` (`$CC/hooks.md:312`) exists but fires after the clear with a 1.5s default budget, so it is not a PreClear.

2. **Clearing context from automation. Not shipped.**
   - Custom commands and hooks cannot invoke built-ins such as `/clear` or `/compact` (#85429, an open request).
   - There is no first-party API that delivers a **control command** (`/clear`, `/compact`) into a named running session (#85289, **closed not_planned 2026-09-15 by the stale bot**). **Plain prompt text CAN be delivered** (corrected after verification): `$CC/cross-session-messaging.md:13-17` documents ListAgents/SendMessage, `:264` and `:279` document a per-session socket plus `CLAUDE_CODE_MESSAGING_TOKEN` for script or hook posts, and channels push external events. A `/clear` inside such a message arrives as plain text and is not executed (maintainer reply on #85289).
   - **The working route sidesteps `/clear`:** start a **successor** session with `claude --bg "<prompt>"` (`$CC/agent-view.md:430-436`), then let the old one idle or `claude stop <id>` (`$CC/agent-view.md:694`). That is the design this repo ratified: "there is no `/clear`" (`docs/specs/coordinator-auto-handoff-2026-10-02.md:247`).
   - **A route that does not fit:** `SessionStart.initialUserMessage` seeds a first turn **only in non-interactive `-p` mode** (`$CC/hooks.md:1190`), and `--bg` rejects `-p` (`$CC/agent-view.md:436`). The community "PreCompact + SessionStart(initialUserMessage)" chain cited in #90089 therefore cannot seed an interactive or bg successor.

3. **Commit, PR and auto-merge. Shipped by GitHub, and by Claude Code only in narrow forms.**
   - GitHub auto-merge is what this repo already uses: `mise run ship` arms it.
   - Claude Code **Desktop** monitors a PR and squash-merges it once checks pass, when auto-merge is enabled (`$CC/desktop.md:170`).
   - A worktree-isolated **background session** may commit, push its own branch and open a **draft** PR (`$CC/agent-view.md:989` is a stale v2.1.198 CHANGELOG row). **Qualified after verification:** the current body (`agent-view.md` ~519-522) says it does so only when the task calls for it, and never pushes to main/master, force-pushes or merges. In this repo any such PR would collide with the `gh pr create` guard and the ship-only rule.
   - Cloud lane omitted earlier: `/autofix-pr` (`$CC/commands.md:58`) and claude.ai/code auto-fix push fixes to an existing PR on CI failure or review comments, and routines can open PRs. None of these merge.
   - No native CLI feature turns an agent's doc edits into a merged PR on main (0 hits for merge queue across `$CC`). The sweep claim that "no native feature auto-merges" holds for the **CLI**, not for Desktop (see Conflicts).

4. **Propagation to live sessions. Not shipped as a feature. Native partial levers exist:**
   - Project-root `CLAUDE.md` is re-read after compaction (`$CC/memory.md:464`).
   - `settings.json` hooks reload live (`$CC/settings.md:584`, per the companion report F2).
   - A `SessionStart` hook can register `watchPaths` for `FileChanged` events and request `reloadSkills` (`$CC/hooks.md:1192-1193`).
   - `claude respawn <id>` and `claude respawn --all` restart sessions onto their saved conversation (`$CC/agent-view.md:695-696`).
   - Closest vendor statement on propagation (found in verification): `$CC/claude-code-on-the-web.md:307` says GitHub emits no webhook when the base branch advances, so auto-fix cannot react and the user must ask Claude to rebase.
   - **None of these moves a worktree lane's branch onto new `main`.** A lane keeps reading its own branch's tracked files. The companion report's F1 is a measured instance: hook/CLI skew on the llvm-23 lane. Built-in worktree auto-sync is only a request (#77869, seen through a third-party mirror).

**Coverage:** no MANDATORY GAPS input was supplied, and FAILED READS and MIRRORS were empty. The sweep is **not** declared incomplete on that basis. It does have material named gaps (see Gaps):

- the discussions surfaces;
- context7 and firecrawl-search on the second query;
- any source for GitHub merge queue;
- any source for live-session propagation;
- no offline mirror of any link.

## Evidence

| Claim | URL or file:line | Quote |
|---|---|---|
| Context % is exposed to the statusline (display producer) | `$CC/statusline.md:186` | "`context_window.used_percentage` — Pre-calculated percentage of context window used" |
| Compaction threshold can be lowered, not raised; it applies beyond cloud | `$CC/env-vars.md:196` | "Set the percentage (1-100) of the auto-compact window at which auto-compaction triggers… can't raise the threshold… Applies to both main conversations and subagents" |
| Cloud sessions set the override themselves (third-party restatement of vendor docs, from the claims) | https://code.claude.com/docs/en/cloud-environments | "Cloud sessions set `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` themselves, so compaction triggers partway through the auto-compact window" |
| The auto-compact window is a separate knob | https://code.claude.com/docs/en/env-vars | "set `CLAUDE_CODE_AUTO_COMPACT_WINDOW`… or run `/autocompact` with a token count" |
| PreCompact/PostCompact exist; their matcher is `manual`/`auto` | `$CC/hooks.md:63`, `:315` | "`PreCompact` — Before context compaction"; "`PreCompact`, `PostCompact` — what triggered compaction — `manual`, `auto`" |
| SessionStart `source` distinguishes `clear`/`compact`/`fork` | `$CC/hooks.md:1152` | "`\"clear\"` after `/clear`, `\"compact\"` after compaction, or `\"fork\"`…" |
| `initialUserMessage` creates a turn only in `-p` mode | `$CC/hooks.md:1190` | "Applies in non-interactive mode with the `-p` flag, where it becomes the first turn" |
| `--bg` rejects `-p`; the prompt is positional | `$CC/agent-view.md:436` | "Claude Code rejects `--bg` combined with `-p` or `--print` before any session is created" |
| Session control verbs exist | `$CC/agent-view.md:693-696` | "`claude stop <id>` Stop a session… `claude respawn --all` Restart every running session" |
| A bg worktree session may open a draft PR on finish (STALE changelog row; current body makes it conditional and never merges, see Verification) | `$CC/agent-view.md:989` | "A background session that isolated its work in a worktree commits, pushes its own isolated branch… and opens a draft pull request when it finishes" |
| Desktop auto-merges a monitored PR | `$CC/desktop.md:170` | "Auto-merge: when enabled, Claude merges the PR once all checks pass. The merge method is squash." |
| Propagation levers: `watchPaths` and `reloadSkills` | `$CC/hooks.md:1192-1193` | "Array of absolute paths to watch for FileChanged events"; "re-scans the skill and command directories after the SessionStart hooks complete" |
| Root CLAUDE.md is re-read after compaction | `$CC/memory.md:464` | "after `/compact`, Claude re-reads it from disk and re-injects it into the session" |
| SHIPPED HERE: the threshold trigger via a function hook | `.claude/skills/coordinator-handoff/hooks/register.ts:296`, `:283` | `on("session.measure", …)`; "never await command.run inside the hook" |
| SHIPPED HERE: the coordinator role, 30% default, successor via `claude --bg` | `.claude/skills/coordinator-handoff/SKILL.md:3` | "`claude --bg` successor from the main checkout, then idle. Auto-submitted by this plugin's session.measure hook when a coordinator's context reaches the limit (default 30%)" |
| SHIPPED HERE: the role gate excludes lanes | `.claude/skills/coordinator-handoff/SKILL.md` (§ header) | "Lanes write no handoff state." |
| SHIPPED HERE: the coordinator handoffs merge unattended | `git log` e2f49ccd, e2cf723c | "docs(handoff): 2026-10-03d auto-handoff at 30% context (#1608)" |
| Measured: hook module and CLI come from different trees on a lane | companion report F1 | "the hook module and the CLI it calls come from different git trees" |
| PROPOSED (issue CLOSED not_planned 2026-09-04, inactivity bot): a threshold hook event and env var | https://github.com/anthropics/claude-code/issues/80269 | "New hook event `onContextThreshold`… Expose `CLAUDE_CONTEXT_PERCENT` as an env var in all hook invocations" |
| PROPOSED: auto-clear plus an early-warning handover | https://github.com/anthropics/claude-code/issues/90089 | "`autoClear.thresholdPercent` (e.g. 30)… At 90% of that threshold… 'Please stop where you are and write a handover document'" |
| PROPOSED: a PreClear hook | https://github.com/anthropics/claude-code/issues/95199 | "`/clear` currently has no associated hook… `PreCompact`… never on `/clear`" |
| PROPOSED (issue CLOSED not_planned 2026-09-15, stale bot; covers control commands only, text delivery exists via cross-session messaging): an API to drive a running session | https://github.com/anthropics/claude-code/issues/85289 | "there is no supported, first-party way for an authorized local process to deliver a turn or a control command into a specific running session" |
| PROPOSED: commands invoking built-ins | https://github.com/anthropics/claude-code/issues/85429 | "Custom slash commands are prompts, so they can't trigger built-in commands" |
| REPORTED: abrupt ends write no handoff | https://github.com/anthropics/claude-code/issues/93799 | "the sessions that end abruptly — limit, crash, kill — never write one… Only the host knows a session is about to stop." |
| REPORTED (bug): additionalContext is dropped on fork | https://github.com/anthropics/claude-code/issues/93458 | "SessionStart hook additionalContext silently dropped when source=fork (rewind)" |
| REPORTED (bug): idle compaction since 2.1.286, no opt-out | https://github.com/anthropics/claude-code/issues/98747 | "idle sessions are compacted automatically before the prompt cache expires… There is no opt-out and no warning." |
| REPORTED: a hook-layer workaround (user-built) | https://github.com/anthropics/claude-code/issues/70555 | "PreCompact hook that snapshots… SessionStart hook that re-injects… Watchdog (UserPromptSubmit hook)… nudges a checkpoint-and-/clear" |
| REQUESTED: native context visibility | https://github.com/anthropics/claude-code/issues/18027 | "Claude Code has no visibility into its own context usage" (manifest snippet, dep run 1) |
| THIRD PARTY: an auto handoff at about 90% | https://github.com/dannguyen9x/autosessionclaude (the manifest URL is the mirror `github.laiyagushi.com`) | "at ~90% context it summarises the session and continues in a fresh one (plugin + CLI)" |
| THIRD PARTY: a PreCompact + SessionStart plugin | https://github.com/who96/claude-code-context-handoff | title only (exa) |
| THIRD PARTY: a workflow mod | https://www.reddit.com/r/ClaudeWorkflows/comments/1wwm74u/workflow_automating_claude_code_context_handoff/ | "Automating Claude Code Context Handoff and Clearing with the `handoff-compact` Mod" |
| THIRD PARTY (another agent, Pi): handoff over compact | https://www.reddit.com/r/PiCodingAgent/comments/1wqatix/killed_context_anxiety_with_automatic_session/ | "My own custom compact plugin basically ended up turning into a handoff." |

### Code search

| Query | Role | Source | Count | rc |
|---|---|---|---|---|
| `repo:anthropics/claude-code PreCompact handoff` | query | planner | 0 (armed) | 0 |
| `repo:anthropics/claude-code autocompact threshold` | query | planner | 0 (armed) | 0 |
| `repo:anthropics/claude-code README` | must-hit | planner | 41 | 0 |
| `repo:anthropics/claude-code qvxjwk7pzmtrq` | known-absent | planner | 0 | 0 |
| `repo:cli/cli filename:README.md` | health | workflow | 9 | 0 |
| `repo:anthropics/claude-code filename:README.md` | must-hit | workflow | 29 | 0 |
| `repo:anthropics/claude-agent-sdk-python filename:README.md` | must-hit | workflow | 3 | 0 |

Notes:

- `anthropics/claude-code` has discussions disabled (repos API), so GitHub Discussions cannot be searched there. This is not a gap.
- `anthropics/claude-agent-sdk-python` has discussions disabled (repos API), so GitHub Discussions cannot be searched there. This is not a gap.
- Reading the two armed zeros: `anthropics/claude-code` is a mostly closed-source repo (plugins, examples, CHANGELOG). A 0 says that repo's tracked files do not contain those phrases. It says nothing about the CLI binary's behaviour.

### Dependency-repo fan-out

| Repo | Query | Required sources failed | Manifest |
|---|---|---|---|
| anthropics/claude-code | session handoff context threshold | none | `.agent/kb/raw/research-fanout/research--kb--reports--agents--session-handoff-automation-sweep-2026-10-03/deps/anthropics--claude-code/1/manifest.json` |
| anthropics/claude-code | claude-agent-sdk-python | none | `.agent/kb/raw/research-fanout/research--kb--reports--agents--session-handoff-automation-sweep-2026-10-03/deps/anthropics--claude-code/2/manifest.json` |
| anthropics/claude-agent-sdk-python | claude-code | none | `.agent/kb/raw/research-fanout/research--kb--reports--agents--session-handoff-automation-sweep-2026-10-03/deps/anthropics--claude-agent-sdk-python/1/manifest.json` |

Topic manifests: `.agent/kb/raw/research-fanout/auto-handoff-context-threshold-sessionstart-clear/manifest.json`, `.agent/kb/raw/research-fanout/claude-bg-session-continuation-worktree-auto-merge/manifest.json`.

### Offline mirrors

| Link | Mirror file | rc | Bytes | Failure |
|---|---|---|---|---|
| _(no input rows: MIRRORS was empty)_ | — | — | — | No link was mirrored. See Gaps. |

## Conflicts resolved

1. **"No native Claude Code feature auto-merges agent-written docs to main" (sweep claim, sourced from the repo URL alone) vs `$CC/desktop.md:170` and `$CC/agent-view.md:989`.**
   - I trusted the vendor's docs, which are primary, over an absence inferred from searching a mostly closed-source repo.
   - Resolution: **Desktop** auto-merges a monitored PR (squash, after checks), and a **CLI bg worktree session** opens a **draft** PR on finish.
   - The claim holds only in the narrow form: "the CLI has no native path from agent edits to a merged PR on main".

2. **"`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` controls auto-compaction timing in cloud sessions" vs `$CC/env-vars.md:196`.**
   - The env-vars reference says it applies to main conversations and subagents in any session that compacts before the context limit. The cloud page only says cloud sessions set it **themselves**.
   - I trusted the reference page, which is the more specific and canonical surface.
   - In every case it changes **when compaction happens**. It is not a handoff trigger.

3. **"Community tools chain PreCompact + SessionStart(initialUserMessage)" (#90089) vs `$CC/hooks.md:1190` and `$CC/agent-view.md:436`.**
   - The vendor docs say `initialUserMessage` creates the turn only under `-p`, and `--bg` rejects `-p`.
   - I trusted the vendor docs. The chain can at best seed a **headless** successor, not an interactive or `--bg` one.
   - #90089 is a proposal thread, and its description of prior art is a third-party claim.

4. **"Custom commands and hooks cannot invoke built-ins like `/clear`" (#85429, #85289) vs this repo's `$.command.run` (`register.ts:283`) working live.**
   - These do not contradict each other. `command.run` here submits a **skill**, and the repo's design avoids `/clear` by launching a successor instead.
   - Whether `command.run` can issue `/clear` was **not** tested. It stays unverified and is not treated as a counter-example.

5. **"No native context-threshold trigger" (#80269) vs `session.measure` in the function-hook API (`register.ts:296`).**
   - The documented hooks reference has no threshold event, so the issue is right about the **documented** surface.
   - The function-hook event carries a percent and is measured working in this repo, but it is absent from the offline `$CC` corpus.
   - I trusted shipped behaviour (code that runs here) for "it exists", and the docs for "it is not a documented, supported hook". Both are kept.

6. **Duplicate and overlapping sweep claims (#90089 four times, #93458 twice, #85429 twice).** I merged them into one evidence row each, and kept the proposal distinct from the user-reported prior art.

7. **The autosessionclaude URL:** the claim cites `github.com/dannguyen9x/autosessionclaude`, but the exa manifest item is a mirror domain (`github.laiyagushi.com`). The canonical repo was not read. Its existence and content are **unverified**, and only the title quote is carried.

## Verification

Five load-bearing claims went through a refute pass and an adjudicator (both ran). Where the adjudicator overturned a refuter flag, the adjudicator's verdict stands.

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| 1 | No threshold or PreClear event in the hooks reference; all three issues (#80269, #95199, #90089) are open requests | **Absence half: confirmed. Tracker half: UPHELD as refuted.** Refuter's "misleading" flag **overturned** by the adjudicator | `grep` of `$CC` for `onContextThreshold\|PreClear` returned 0 files (control: PreCompact 13 hits in hooks.md). `gh api` shows #80269 CLOSED, not_planned, 2026-09-04 (inactivity bot); #95199 and #90089 open. Struck "open" for #80269 in the Answer and Evidence. The `session.measure` omission is disclosed in the same paragraph, so not misleading |
| 2 | Hooks cannot invoke `/clear`; no supported API injects a prompt or control command into a running session | **Control-command half: confirmed. "Prompt" half: UPHELD as refuted. Also UPHELD misleading** | #85429 open: custom commands cannot trigger built-ins. But `$CC/cross-session-messaging.md:13-17, 264, 279` documents text delivery (SendMessage, socket plus `CLAUDE_CODE_MESSAGING_TOKEN`), confirmed by a maintainer reply on #85289. #85289 is closed not_planned (2026-09-15), not open. Answer corrected to "control commands only". Omission now stated: a successor or lane can be prompted without `--bg` |
| 3 | `initialUserMessage` works only in `-p`; `--bg` rejects `-p`; so the PreCompact+SessionStart chain cannot seed an interactive or bg successor | **Confirmed. Refuter's "misleading" flag overturned** | `hooks.md:1190` and `agent-view.md:436` re-read. The claim is scoped to that chain. The report line 186 names the working alternative (`claude --bg "<prompt>"`). Note: `additionalContext` adds context but does not create a turn |
| 4 | Repo ships a percent-carrying `session.measure` -> `$.command.run` trigger (coordinator only); #1604/#1608 auto-merged via `mise run ship` | **Confirmed. Refuter's "misleading" flag overturned** | `register.ts:254, 283, 296`; SKILL.md:3, :17, :46-47; `gh pr view` #1604 and #1608 show autoMergeRequest SQUASH. Caveat: auto-merge metadata plus the SKILL instruction imply `ship` as the invoker; no ship log was read |
| 5 | No native CLI mechanism turns agent doc edits into a merged PR on main or moves a live lane onto new main; only Desktop auto-merge and a bg draft PR exist; no source on merge queue or propagation | **Core absence: confirmed. UPHELD as misleading** | 0 hits for merge queue across `$CC`. Omissions now stated in the Answer: `agent-view.md:989` is a stale changelog row (current body: draft PR only when the task calls for it, never merges); `/autofix-pr` and web auto-fix exist; `claude-code-on-the-web.md:307` is a vendor source on base-branch propagation. Merge queue remains unresearched |

Other claims (not put through refute):

| Claim | Status |
|---|---|
| `used_percentage` in statusline; `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` semantics; PreCompact/PostCompact/SessionStart source values; `claude stop`/`respawn`; `watchPaths`/`reloadSkills` | Confirmed against `$CC` file:line in Evidence (single-pass read) |
| `session.measure` is absent from the offline `$CC` corpus; payload and per-role stability | Unverified (see Gaps) |
| Third-party tools (autosessionclaude, who96, ddaanet, etc.) | Unverified, title or snippet only |
| #77869 worktree auto-sync request | Unverified, via a third-party mirror |
| Tree skew F1 (companion report) | Inherited from the companion lane, not re-derived here |

**How the conclusion changes.** The core conclusion stands: no single native feature does this end to end; extend the shipped coordinator design with a successor launched via `claude --bg`. Three adjustments follow. (a) Two of the three "open feature request" issues are actually closed not_planned by bots, so there is no upstream roadmap signal to wait on. (b) A supported text-delivery path into running sessions exists (cross-session messaging, channels), so propagation and coordinator-to-lane nudging have a native option the sweep missed; it still cannot run `/clear`. (c) The native bg draft-PR behaviour is weaker than stated, which strengthens the case for `mise run ship`. The `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` backstop is downgraded to unverified.

## Gaps

- **GitHub Discussions, anthropics/claude-code (set 1):** `empty_unverified`; the canary returned 0 items. (The code-search note says discussions are disabled on that repo, so this is likely structural. It is still recorded as unverified because the canary could not discriminate.)
- **GitHub Discussions, anthropics/claude-code (set 2):** `empty_unverified`; the canary returned 0 items.
- **GitHub Discussions, anthropics/claude-agent-sdk-python:** `empty_unverified`; the canary returned 0 items.
- **context7 on query 2 (bg session continuation, worktree, auto-merge):** error, exited 1. Content unknown.
- **firecrawl-search on query 2:** error, HTTP 402 (billing/quota). Content unknown.
- **Code-search rows `PreCompact handoff` and `autocompact threshold`:** count 0 but armed, and **unverified against ground truth**. The repo is mostly closed source, so a 0 there cannot speak to binary behaviour.
- **No source covered GitHub auto-merge or merge queue for agent-written docs, or propagation of `main` to live sessions and worktrees.** Only #77869 touches it, and only through a third-party mirror (claudeissues.com). Everything said above about merge queue is unresearched. Propagation rests on the offline vendor docs and local code only.
- **Deep reads were capped at 6:** #90089, #80269, #95199, `docs/en/sessions`, `docs/en/worktrees`, and who96/claude-code-context-handoff. Every other third-party tool (autosessionclaude, ddaanet/handoff, Gibraltar-Context, claudikins, pi-handoff, Continuous-Claude-v3, cc-worktree-ops, the npm `claude-code-handoff`) is **title or snippet only**. How any of them work is unverified.
- **No offline mirrors:** MIRRORS was empty, so no link this report cites has a firecrawl mirror under `docs/research/kb/raw/<slug>/links/`. That breaks `research-doc-sources.md` "Always" item 4 and is a named gap.
- **`session.measure` is undocumented in the offline `$CC` corpus** (0 hits). Its stability guarantees, payload and per-role behaviour in `--bg` sessions are unverified beyond this repo's live coordinator arm.
- **The statusLine as a trigger for bg sessions is unverified:** the statusline runs only while the UI renders (companion report F2), and nothing here measured whether a bg session that is not attached renders it.
- **`command.run` issuing a built-in (`/clear`, `/compact`):** not tested.
- **Idle compaction (#98747) vs a 30% handoff:** this sweep did not measure whether 2.1.286+ idle compaction pre-empts a threshold handoff in a long-idle lane.

Critic gaps (appended; each with its next probe):

- **GitHub merge queue and auto-merge for agent-written docs never researched.** The recommendation still says "research merge queue first" when handoff PRs race, with no evidence on required-check behaviour, queue config, or other projects. Next probe: read docs.github.com on merge queue and auto-merge; `gh api repos/ray-manaloto/dotfiles/rulesets` and branch protection; `gh search code 'merge_group'` with 'handoff'; test two concurrent `mise run ship` PRs touching handoff files.
- **Propagation to live sessions unmeasured.** The `watchPaths`/`FileChanged`, `reloadSkills` and respawn claims come from offline docs only. Untested: whether `watchPaths` fires in a `--bg` session, whether a file in the main checkout is visible from a sibling worktree, whether `additionalContext` is delivered on `FileChanged` (#93458 hints at a related drop on fork). Next probe: two `claude --bg` sessions in different worktrees, `watchPaths` on a pointer file, touch it, log the event and the context; check `hooks.md` for a FileChanged `additionalContext` field.
- **`session.measure` is load-bearing but undocumented and unconfirmed.** Payload, stability, firing in unattached `--bg` sessions, introducing release, and whether the function-hook API is public or experimental are unknown. Shipped-here and vendor-documented are partly merged in the Answer. Next probe: CHANGELOG and plugin-authoring docs for `session.measure`; run `claude --bg` with a debug hook logging events with no UI attached; pin the working `claude --version`.
- **statusLine in bg sessions and `command.run` issuing `/clear` or `/compact`: both untested.** These decide whether lanes could use `/clear` at all. Next probe: in a `--bg` session, a statusLine command appending `used_percentage` to a file; separately call `$.command.run('/clear')` from a throwaway hook.
- **Third-party tools cited by title only** (autosessionclaude via a mirror domain, who96, ddaanet, Continuous-Claude-v3, claudikins, the Reddit handoff-compact mod): trigger, continuation mechanism and unattended viability unverified. Next probe: fetch canonical READMEs and hook configs; record trigger, continuation (`claude -p`, `--resume`, manual) and worktree handling.
- **Idle compaction and the `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` backstop.** The override can only lower the threshold, so "just above the handoff threshold" may be invalid, and compaction could fire before the handoff. Next probe: read the 2.1.286 notes and #98747; run an idle lane at about 25-35% context with the override set and record whether PreCompact fires before `session.measure` triggers.
- **Worktree-lane propagation and the tree-skew fix unevidenced beyond the companion report.** #77869 seen only via a mirror; recommended option (a) (resolve the CLI from the primary checkout) was not tried; interaction of the bg draft-PR behaviour with ship gates, and whether it can be disabled, unchecked. Next probe: `gh issue view 77869` directly; prototype option (a); look for a setting or hook that turns the draft PR off.
- **Native alternatives not probed from the SDK, agent-teams, routines or cloud side.** The SDK `query`/`resume`/Stop-hook continuation path was only fan-out searched; agent teams, `/schedule` routines and a Stop hook with `decision:block` as a handoff driver were never read. Next probe: read those docs pages; test whether a Stop hook can submit the handoff skill at a threshold. (Note: Stop hooks force a turn, per repo memory.)
- **Failed sources never retried:** context7 (rc 1) and firecrawl-search (HTTP 402) on query 2, plus the discussions canaries; the no-offline-mirror breach is still open. Next probe: re-run after fixing quota; `gh api graphql` discussions listing with a positive-control repo; mirror cited URLs under `docs/research/kb/raw/`.
- **Added by verification:** the vendor doc `claude-code-on-the-web.md:307` and `cross-session-messaging.md` were found only by the refute pass, which suggests the original sweep's offline-corpus coverage was incomplete beyond the pages it cited.

## Recommendation

Extend the shipped coordinator design to the other roles. Do not build a second mechanism.

1. **Trigger (all roles):** keep `session.measure` → `decide` → `$.command.run(<role skill>)`. It is the only in-session, percent-carrying trigger found.
   - Widen the role gate from "coordinator only" to an explicit role table: coordinator, watcher, lane.
   - Give each role its own handoff skill, because a lane's handoff differs from a coordinator's.
   - Consider `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` as a **backstop**, set just above the handoff threshold, so a missed fire degrades to compaction rather than overflow. **Unverified (critic gap):** it can only lower the threshold, and idle compaction since 2.1.286 (#98747) could compact before the handoff fires; do not adopt until measured.

2. **Fix the tree skew before widening (companion report F1).** A lane must not run a hook module from one tree against a CLI from another.
   - Options, in order:
     - (a) resolve the `decide` CLI from the primary checkout (`git worktree list`, first entry), not from `CLAUDE_PROJECT_DIR`;
     - (b) ship the CLI as a versioned `uv tool` that both trees call;
     - (c) install the hook at personal plugin scope (`~/.claude/skills/`), which is a user-level write and needs Ray's approval.
   - This needs a ruling. Recommend (a): no user-level write, and one source of truth.

3. **Never `/clear`; always hand over to a successor.** The successor is `claude --bg "<resume prompt>"` launched **in the same worktree** for a lane, and from the main checkout for the coordinator. Then the old session idles or stops (`claude stop <id>`). This sidesteps #85429, #85289 and #95199 entirely, and does not depend on `initialUserMessage`.

4. **Merge (zero-touch):**
   - A lane's handoff writes only to its **own branch**, as tracked handoff and report files, and never to `task_plan.md` (coordinator-only).
   - The coordinator handoff already ships through `mise run ship`, which arms GitHub auto-merge (#1604, #1608).
   - Do **not** rely on the native bg-worktree draft PR. Its documented behaviour is conditional (only when the task calls for it, never merges; `agent-view.md:989` is a stale changelog row), it bypasses the ship gates, and it would collide with the `gh pr create` guard.
   - If several handoff PRs race, research GitHub merge queue first. It is a named gap here.

5. **Propagation:**
   - Successors pick up `main` naturally at their `SessionStart(startup)`.
   - For live sessions, register a `watchPaths` entry on a single handoff-pointer file in the **main checkout**, and react on `FileChanged` with `additionalContext`.
   - Lanes still need an explicit `git fetch` and rebase at the next handoff boundary. Nothing native moves a worktree branch.
   - Use `claude respawn --all` only as an operator-level reset.

6. **Arm every one of these live** (`real-integration-evidence.md`): one real lane crossing the threshold, a successor launched, its PR auto-merged, and a sibling session observing the `FileChanged` event. Each needs its control arm (below-threshold: no fire; non-matching role: no fire).

## Provenance

| Node | agentType | Model | Effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| deps:anthropics/claude-code | general-purpose | sonnet | low |
| deps:anthropics/claude-agent-sdk-python | general-purpose | sonnet | low |
| triage | Explore | sonnet | low |
| read:1/2 | Explore | haiku | (default) |
| read:2/2 | Explore | haiku | (default) |
| synthesize | general-purpose | opus | high |
| refute:1/5 | general-purpose | sonnet | medium |
| refute:2/5 | general-purpose | sonnet | medium |
| refute:3/5 | general-purpose | sonnet | medium |
| refute:4/5 | general-purpose | sonnet | medium |
| refute:5/5 | general-purpose | sonnet | medium |
| critic | Explore | sonnet | medium |
| adjudicate | general-purpose | opus | high |
| reconcile (this node) | general-purpose | sonnet | medium |

All stages ran; FAILED STAGES was empty.

Local probes run by the synthesize node:

- greps of the offline `$CC` corpus (`~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`). Must-hit: `used_percentage`, `PreCompact`, `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`. A freshly invented known-absent string returned 0.
- greps of `.claude/skills/coordinator-handoff/` and `docs/specs/coordinator-auto-handoff-2026-10-02.md`;
- `git log --grep auto-handoff`.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code): issues #90089, #80269, #95199, #85289, #85429, #70555, #93799, #93458, #98747, #18027, #75378, #81412, #48185, #59580, #77869 (via mirror); releases v2.1.284/285; code search
- [anthropics/claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python): dependency fan-out issues; code search must-hit
- [cli/cli](https://github.com/cli/cli): code-search health probe only
- [who96/claude-code-context-handoff](https://github.com/who96/claude-code-context-handoff): third-party PreCompact + SessionStart handoff plugin (title only)
- [dannguyen9x/autosessionclaude](https://github.com/dannguyen9x/autosessionclaude): third-party ~90% auto handoff (title only, via a mirror domain)
- [ddaanet/handoff](https://github.com/ddaanet/handoff): third-party handoff tool (title only)
- [Dikestra-ai/Gibraltar-Context](https://github.com/Dikestra-ai/Gibraltar-Context): third-party hook-based context tool (title only)
- [povvo/claudikins-automatic-context-manager](https://github.com/povvo/claudikins-automatic-context-manager): third-party context manager (title only)
- [ogulcancelik/pi-handoff](https://github.com/ogulcancelik/pi-handoff): Pi-agent handoff extension (title only)
- [parcadei/Continuous-Claude-v3](https://github.com/parcadei/Continuous-Claude-v3): session lifecycle hooks, via DeepWiki (title only)
- [luandv92/cc-worktree-ops](https://github.com/luandv92/cc-worktree-ops): third-party worktree ops (title only)
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): coordinator-handoff skill and hook, spec, #1583/#1604/#1608
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): offline `agent-harness-docs` corpus (`$CC`)
