# pwf 3.20.7 skills/commands inventory and adoption proposal (Brief A)

Session 2026-09-23d (`a6750a24`). Brief: `docs/research/kb/reports/agents/session-2026-09-23d-agent-briefs.md` § Brief A.
Lane: read-only research. The only repo file written is this report. Throwaway probes ran under the session scratchpad.
Status: COMPLETE.

`$P` = `~/.claude/plugins/cache/planning-with-files/planning-with-files/3.20.7`. `$CC` = KB `agent-harness-docs/docs/claude-code`.
Upstream latest release = `v3.20.7`, published 2026-09-23T20:43Z (`gh api repos/OthmanAdi/planning-with-files/releases/latest`). The installed version is current.

## TL;DR

1. **A D4 gap (measured).** `init-session.sh --autonomous|--gated` attests the plan by running `attest-plan.sh` as a
   child process. The D4 deny rules only match the Bash command string (`.claude/settings.json:31-41`), so the model
   can run this command. In a throwaway repo it **re-blessed an edited plan** at rc=0. It also rewrote `.mode` and
   dropped `inject-smart`. `/pwf` is model-invocable and tells the model to run exactly this command
   (`commands/pwf.md:12`). As a result, `.claude/CLAUDE.md`'s claim "all model routes denied" is false. Details in F1.
2. **pwf's machine view of our plan is stale.**
   - Only 7 of the 19 `### Phase` headings carry a `**Status:**` line.
   - The first `in_progress` phase is `Phase 2b: 2026-09-10 …` (`task_plan.md:650`). That is what the injected
     `RUN LEDGER` block names on every turn, and what inject-smart expands.
   - Phases 7–11 are invisible to pwf.
   - The ledger has 0 entries, so `progress.md` never reaches injection in autonomous mode.

   Details in F2.
3. **`/plan-goal` and `/plan-loop` do not reduce attest stops in this repo, and `/plan-loop` would increase them.**
   `/plan-goal` tells the model to issue `/goal`, which is a built-in the model cannot invoke. Its default condition
   ("ALL PHASES COMPLETE") also cannot be reached with this plan. `/plan-loop`'s default tick edits the `**Status:**`
   lines in `task_plan.md`, and every such edit breaks the attestation.
4. **Three things reduce attest stops without weakening the human-approval boundary:**
   - fewer, batched plan edits: volatile state goes to the ledger or `progress.md`, and `task_plan.md` stays stable;
   - one operator attest per **phase boundary**, which is upstream's stated cadence (`MIGRATION.md:188-190`);
   - a smaller, task-scoped plan. Upstream's model is 3–7 phases in an ephemeral per-task plan
     (`templates/task_plan_autonomous.md` § Phases, `docs/workflow.md:117`).

   pwf has no mode in which an agent is allowed to attest.

## 1. Surface map (measured)

- **Size and layout.** `$P` holds 733 files. The Claude-plugin surface is:
  - `commands/*.md` (13);
  - `skills/planning-with-files/SKILL.md`. The 5 i18n copies under `skills/i18n/` are not registered by the plugin
    scan (`CHANGELOG.md:435`);
  - `scripts/*` (27);
  - `hooks/hooks.json` plus `hooks/claude-hook.sh`;
  - `hooks/codex-hooks.json`.

  The dot-directories (`.cursor`, `.gemini`, `.codex`, `.hermes`, `.kiro`, `.opencode`, …) are per-IDE mirrors.
- **Plugin hooks** (`hooks/hooks.json:4-99`). There are six events: `SessionStart` (matcher
  `startup|resume|clear|compact`), `UserPromptSubmit`, `PreToolUse` (`Write|Edit|Bash|Read|Glob|Grep`),
  `PostToolUse` (`Write|Edit`), `PreCompact` (`*`) and `Stop`. Each runs `sh claude-hook.sh <event>` with a 10 s timeout.
- **SKILL.md frontmatter hooks** (`SKILL.md:6-29`) all start with `[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && exit 0`, so they
  do nothing on the plugin route.
- **Which commands set `disable-model-invocation` (DMI).** Two routes, same answer:
  - Frontmatter: DMI is set on `plan-attest.md:3`, `plan-doctor.md:3`, `plan-goal.md:3`, `plan-loop.md:3` and `start.md:3`.
  - This session's Skill listing: it exposes `planning-with-files:{plan,pwf,status,plan-ar,-de,-es,-zh,-zht,planning-with-files}`
    and none of the five DMI commands.

## 2. Inventory with dispositions

"D4 interaction" refers to the deny rules at `.claude/settings.json:31-41`:
- `*attest-plan.sh[ *]`, `*attest-plan.ps1[ *]`;
- `*set-active-plan.sh[ *]`;
- `mise run plan-attest[ *]`, `*mise run plan-attest *`;
- `*dotfiles-setup plan-attest[ *]`.

### 2a. Commands (`$P/commands/`)

| Command | What it does (source) | DMI | Writes / attests | D4 interaction | Disposition |
|---|---|---|---|---|---|
| `/planning-with-files:plan` | Invokes the skill and creates the 3 files if missing (`plan.md:5-12`) | no | Writes planning files. SKILL Quick Start may lead to `init-session.sh "<name>"` (`SKILL.md:82`) | A slug init inherits the root `.mode` floor and **auto-attests the new plan** (F1 step 5). Nothing matches it | **SKIP (model)** here. PRO: none, the root plan already exists. CON: a model-created slug would be model-attested and would shadow the root plan |
| `/planning-with-files:pwf` | Alias of `/plan`. When the user says "autonomous" or "gated" it runs `init-session.sh --autonomous`/`--gated` (`pwf.md:12`) | **no** | Writes and **attests** | **Bypasses D4** (F1) | **SKIP + DENY** (`init-session.sh` deny or `/pwf` skill deny). PRO of keeping: none here. CON: it is a live self-attest route |
| `/planning-with-files:start` | Invokes the skill (`start.md:6`) | yes | Same as `/plan` | none | **SKIP** (redundant) |
| `/planning-with-files:status` | Reads `./task_plan.md` directly and prints phases, errors and a file check (`status.md:5-49`). It does **not** use the resolver | no | Read-only | none | **ADOPT as a cheap read.** PRO: model-invocable, no writes. CON: its output depends on `**Status:**` lines, which are stale here (F2). `check-complete.sh` is the more exact oracle |
| `/planning-with-files:plan-doctor` | Runs `plan-doctor.sh`: resolution, injection, canonicalizer, attestation, install surfaces, latency. "Diagnostic only" (`plan-doctor.md:7-20`). The script "Writes nothing except inject-plan.sh's own SHA cache. Always exits 0" (`plan-doctor.sh:17-18`) | yes | No (SHA cache only) | none. The script stays model-runnable through Bash | **ADOPT**, operator-invoked. Automation is Brief B's question. PRO: catches silently dark hooks. CON: rc is always 0, so it cannot gate on its own |
| `/planning-with-files:plan-attest` | Writes the SHA-256 to `./.plan-attestation` or `.planning/<id>/.attestation`. Has `--show` and `--clear` (`plan-attest.md:7-26`) | yes | **Attests** | Denied. Operator route: `! mise run plan-attest` | **SKIP.** Keep the operator-only route (D4) |
| `/planning-with-files:plan-goal` | Derives a condition from the plan and "Issue[s] Claude Code's `/goal <condition>`" (`plan-goal.md:9-17`). The default condition is "all phases … Status: complete and check-complete.sh reports ALL PHASES COMPLETE" (`:14`) | yes | None itself | none | **SKIP the command, keep the idea.** It cannot complete: `/goal` is a built-in, not a skill (§4), and the default condition cannot be reached here (F2). The repo already has a better recipe (`docs/specs/goal-writing-and-phase2-dependency-currency.md:18-35`) |
| `/planning-with-files:plan-loop` | Wraps `/loop <interval> <prompt>` with a default tick. The tick reads the plan and progress, runs `check-complete.sh`, appends to `progress.md` and **updates `Status:` in `task_plan.md`** (`plan-loop.md:11-24`) | yes | **Edits `task_plan.md`** | Indirect: every status edit leaves the attested plan TAMPERED until the operator re-attests | **SKIP.** Under `autonomous`, each tick that edits a status blocks injection and adds an attest stop |
| `/plan-ar`, `-de`, `-es`, `-zh`, `-zht` | Language variants (`plan-*.md:5-19`) | no | Write | Same as `/plan` | **SKIP** |

### 2b. Scripts (`$P/scripts/`, canonical)

| Script | What it does | Writes / attests | D4 interaction | Disposition |
|---|---|---|---|---|
| `init-session.sh` / `.ps1` | Creates the 3 files. Root mode skips files that already exist (`:398-428`). `--autonomous`/`--gated` write `.mode`, `.nonce` and `.stop_blocks=0`, then **auto-attest** (`:184-255`). A slug inherits the root `.mode` floor (`:170-182`, `:472`) | **Writes and attests** | **Not denied. Bypasses D4** (F1) | **SKIP + DENY** for the model. The operator may still run it deliberately |
| `attest-plan.sh` / `.ps1` | Writes the plan SHA-256. Has `--show` and `--clear` (`attest-plan.sh:1-18`) | **Attests** | Denied | **SKIP.** Operator-only |
| `set-active-plan.sh` / `.ps1` | `--list`, `--verify-root`, or a `PLAN_ID` to switch the shared pointer atomically (`set-active-plan.sh:1-4`) | Pointer write (`--list` is read-only) | Denied. The pattern matches **any** command containing the filename: in this session a plain `sed -n 1,45p …/set-active-plan.sh` was denied, so `--list` and plain reads are collateral | **SKIP.** There is one root plan here. Revisit an operator-run `--list` if worktree-per-task is ever adopted |
| `resolve-plan-dir.sh` / `.ps1` | Resolution order: `PLAN_ID` (a binding since #237), `.active_plan`, newest slug, legacy root. Includes containment and `--check-ambiguity` (`SKILL.md:227`) | none | none | **ADOPT** (already in use internally) |
| `inject-plan.sh` / `inject-plan.py` | Injection engine; `.py` is the fast-path twin (`CHANGELOG.md:199-202`). The tamper check runs whenever an attestation exists (`inject-plan.sh:1106-1118`). v3 modes refuse an unattested plan (`:1129-1134`) and drop pretool injection (`:983-988`) | SHA cache | none | **ADOPT** (in use) |
| `check-complete.sh` / `.ps1` | Without `--gate`: an advisory report such as "ALL PHASES COMPLETE" (`:128`). With `--gate`: the Stop-gate decision table (`:146-287`) | `--gate` writes `.stop_blocks` and `.gate_last_ledger` | none | **ADOPT without `--gate`** as the read-only status oracle. Measured here at rc=0: "2/19 phases complete … 2 in progress … 3 pending" |
| `gate-stop.sh` | Stop dispatcher that calls `check-complete.sh --gate` (`gate-stop.sh:1-32`) | via check-complete | none | **Keep (inert).** It never blocks while `.mode` lacks `gate` |
| `ledger-append.sh` / `.ps1` | Appends one JSON line to `<plan-dir>/ledger-<agent>.jsonl`. Events: `progress phase_complete error gate_block attest note`. Summary is capped at 200 chars. The tick counter is global and taken under flock (`ledger-append.sh:1-40`, `:229-276`). A rejected selector is refused (`:55-60`). It does **not** check `PLANNING_DISABLED`: 0 grep hits, control `inject-plan.sh`=2 | Ledger file, **not attested** | none | **ADAPT. This is the attest-reducing primitive.** PRO: progress lives outside the plan hash, and autonomous mode already injects the ledger summary. CON: it adds a channel next to `progress.md`, the repo's existing lane-return convention |
| `ledger-summary.sh` / `.ps1` | Fixed-shape block: entries, phases, first `in_progress` heading, last event per agent. No free text, no timestamps (`ledger-summary.sh:1-40`) | none | none | **ADOPT** (already injected in autonomous mode). Its current output here is stale (F2) |
| `phase-status.sh` / `.ps1` | The only lock-safe writer of a phase `Status:`. The script itself says editing "changes its SHA, so the orchestrator must re-attest at phase boundaries" (`phase-status.sh:1-15`) | **Edits `task_plan.md`** | Indirect (hash break) | **ADAPT later, SKIP now.** Useful only once status lines are back in sync (F2). Each call still costs an attest |
| `plan-doctor.sh` | See `/plan-doctor` | SHA cache | none | **ADOPT** (Brief B) |
| `session-catchup.py` | Bare invocation or `--no-history`: no host-store access. `--metadata`: aggregate counts. `--replay`: bounded, nonce-framed excerpts (`session-catchup.py:1-16`, `:526-530`). SessionStart runs `--no-history` (`claude-hook.sh:266`) | none | none | **ADOPT the automatic path as-is. SKIP the explicit modes**: this repo recovers through `/session-resume` and AgentsView |
| `skill-hook.sh` | Hook entrypoint for the standalone-skill route (`skill-hook.sh:1-20`) | turn marker | none | **N/A.** It no-ops on the plugin route |
| `sync-ide-folders.py` | pwf maintainer release tool. Syncs `skills/planning-with-files/` into the IDE mirrors; supports `--dry-run` and `--verify` (`sync-ide-folders.py:1-28`) | Writes inside a pwf checkout | none | **SKIP.** Not a user tool |
| `check-continue.sh` | Checks that the Continue.dev integration files exist (`check-continue.sh:1-34`) | none | none | **SKIP** |
| `bump-version.py`, `build-clawhub-upload.py`, `_v240_update_hook_bodies.py` | Maintainer release tooling | pwf repo | none | **SKIP** |

### 2c. Hooks, modes and environment variables

| Item | What it does | Disposition |
|---|---|---|
| `SessionStart` | Runs a `--no-history` catchup plus the userprompt context, and emits it as `additionalContext` (`claude-hook.sh:256-280`, `:290-298`) | **ADOPT** (in use) |
| `UserPromptSubmit` | Turn-start plan context; re-arms the PostToolUse nudge (`:299-305`) | **ADOPT** (in use) |
| `PreToolUse` | Plan head. **Dropped in autonomous and gated modes** (`inject-plan.sh:983-988`) | In use. Autonomous mode drops it, which was the point of PR #879 |
| `PostToolUse` | Progress nudge as `additionalContext`, at most once per turn (`CHANGELOG.md:242-244`) | **ADOPT** (in use) |
| `PreCompact` | Diagnostic reminder plus `Plan-SHA256`. Cannot inject context (`SKILL.md:297-299`) | **ADOPT** (in use) |
| `Stop` + gated mode | Blocks a stop only when all of these hold: `.mode` contains `gate`, a phase is `in_progress`, `stop_hook_active` is false, blocks are under the cap (20), and the ledger advanced since the last block (`check-complete.sh:146-287`, `SKILL.md:403-411`). The gate **never reads attestation**: 0 `attest` hits in `check-complete.sh` | **SKIP now**, for four reasons below the table |
| `.mode` tokens | `autonomous`, `gate`, `inject-smart`, `plan-guard-off` (`SKILL.md:367-397`). The root `.mode` is a floor for slugs (#238) | Current value is `autonomous inject-smart` (tracked; measured with `cat .mode`). Keep (§5) |
| `PLAN_ID` | Slug pin; a binding since v3.15.0 (`CHANGELOG.md:263`) | **ADAPT** for worktree-per-task only. **SKIP** at root |
| `PWF_PLAN_ROOT` | Absolute root pin; fails closed (`CHANGELOG.md:554`) | **ADAPT** if a lane's cwd is ever a parent directory. Not needed today |
| `PLANNING_DISABLED=1` | Silences every hook entry point (`docs/codex.md:126-149`) | **ADOPT.** Already set for codex lanes (`codex_lane.py:136`, applied at `:469`) |
| `PWF_SESSION_ID`, `.planning/sessions/` | Session attachment (`README.md` env table) | **SKIP** |
| `PWF_INJECT=smart` | Same as the `inject-smart` token | Already set via `.mode` |
| `PWF_PLAN_GUARD=0` | Turns off the parallel-write guard | **SKIP.** Keep the guard on; it is a free advisory |
| `PWF_GATE_CAP` | Gate cap | N/A (not gated) |
| `PWF_FAST_PATH=0` | Forces the shell chain | **SKIP** (debug only) |
| `templates/loop.md` | Default prompt for a bare `/loop`. Step 2 edits `Status:` in `task_plan.md` (`templates/loop.md:27-30`) | **SKIP.** Neither `.claude/loop.md` nor `~/.claude/loop.md` exists (checked with `ls`) |
| `templates/task_plan_autonomous.md` | "Break the task into three to seven verifiable phases" (§ Phases). Coordination fields are descriptive only (`MIGRATION.md:178-183`) | **ADAPT** as the shape of any future per-task plan |

Why gated mode is a SKIP for now:
1. This plan always has an `in_progress` phase, and it is the wrong one (F2).
2. No agent writes to the ledger. After the first block, `BLOCKS` stays at 1 and every later stop gets "no progress
   since last gate block — allowing stop" (`:244-248`). The net effect is at most **one forced continuation per init**.
3. Repo memory `feedback_stop_hooks_force_a_turn` records the cost of a forced turn.
4. The orchestrator legitimately stops for operator-only actions, including the attestation itself.

**ADAPT it only** if a future per-task slug plan in a worktree gets agents that write ledger entries.

## 3. Codex integration (`docs/codex.md`)

**What pwf ships.**
- A codex plugin (`.codex-plugin/plugin.json`, `hooks/codex-hooks.json`) with 7 events: SessionStart, UserPromptSubmit,
  PreToolUse, PermissionRequest, PostToolUse, PreCompact and Stop (`docs/codex.md:102-112`).
- Changed hook definitions need `/hooks` trust after an upgrade (`:200`).
- Do not enable plugin mode and a workspace `.codex/hooks.json` together, or every hook fires twice (`:77-79`, `:186-194`).
- `PLANNING_DISABLED=1` is upstream's documented opt-out for `codex exec` one-shots (`docs/codex.md:126-149`).
- With multiple named plans, each codex session needs its own `PLAN_ID` (`:232-236`).

**What is set up here.**
- `~/.codex/config.toml:257-258` enables `planning-with-files@planning-with-files` **globally**, with trusted hook
  state for all 7 events (`:499-517`). Only lines matching `planning` were read.
- `codex_lane.py:136` / `:469` scrubs lanes with `PLANNING_DISABLED=1`.
- `sdlc_team.py` passes **no `env=`** at either `Popen` (`:805`, `:961`), and has 0 hits for `PLANNING` or
  `LANE_ENV_OVERRIDES`. Control: `codex_lane.py` does hit. **So SDLC-team lanes run with the pwf codex hooks live.**
  This matches the 2026-09-22 observation that codex lanes saw `PLAN TAMPERED`
  (`plan-attest-history-2026-09-23.md` § 5).

**Disposition: ADOPT upstream's shape.** One orchestrator owns the plan; workers are either scrubbed or pinned.
- Read-only and verdict lanes get `PLANNING_DISABLED=1`, as `codex_lane` does today.
- For SDLC implement lanes, choose explicitly: scrub them, or share the plan read-only. That decision is #1307.
- Workers report through `progress.md` or a ledger, never through `task_plan.md` (`README.md:486`, `SKILL.md:85,259`).

## 4. `/plan-goal` vs Claude Code `/goal`; `/plan-loop` vs Claude Code `/loop`

**`/goal` is a built-in command, not a skill.**
- `$CC/commands.md:92` has no **Skill** marker. By contrast `/loop` (`:106`) and `/code-review` (`:68`) carry one.
- It is "a wrapper around a session-scoped prompt-based Stop hook". Its evaluator judges only "what Claude has
  surfaced in the conversation. It doesn't run commands or read files" (`$CC/goal.md:56`, `:120`, `:173`).
- The Skill tool reaches only a few built-ins (`$CC/skills.md:744`). A scheduled `/loop` fire delivers built-ins as
  plain text (`$CC/scheduled-tasks.md:43-47`).
- The repo already records this: "`/goal` is NOT model-invocable. The operator types it"
  (`docs/specs/goal-writing-and-phase2-dependency-currency.md:31-32`).

**So `/plan-goal` is a prompt that drafts a condition. Its step 4 cannot execute.** The model can print the text; the
human has to paste it after `/goal`. (Doc-derived; not tested live.)
- Its default condition relies on `check-complete.sh` printing "ALL PHASES COMPLETE". The evaluator only sees that if
  Claude prints it, and for this 19-phase program plan it can never become true (F2).
- It composes with `/goal` rather than replacing it (`plan-goal.md:27`). What it adds is the idea: derive the
  termination criterion from the plan file rather than from how the conversation feels.

**`/loop` is a bundled Skill.** It runs on an interval or self-paced, defaults to `loop.md`, expires after 7 days, and
is session-scoped (`$CC/scheduled-tasks.md:33-124`, `:181`, `:208-210`).
- `/plan-loop` only composes `/loop <interval> <plan-aware prompt>` (`plan-loop.md:11-24`).
- Upstream's combination is `/plan-loop 10m` plus `/plan-goal`: the first sets the cadence, the second the termination
  (`plan-loop.md:36`, `SKILL.md:322`).
- In this repo the plan-aware tick is harmful. Its step "If a phase finished, update its Status: line in task_plan.md"
  (`plan-loop.md:21`) changes the hash. Under `autonomous` plus D4, every such tick leaves the plan TAMPERED until the
  operator re-attests.

**Do any of these reduce operator attest stops without weakening the boundary?** None of the four, as shipped:

| Mechanism | Effect on attest stops |
|---|---|
| `/plan-goal` | Neutral. No plan edits, but the model cannot execute it |
| `/plan-loop` | Increases them |
| gated mode | Neutral to negative. One forced turn, and the gate ignores attestation |
| `/goal` | Neutral |

What does reduce them:
- **Ledger-first progress.** `ledger-append.sh` writes outside the hash, and autonomous injection already reads the
  ledger instead of `progress.md`.
- **Phase-boundary attest cadence.** The orchestrator batches plan edits, and the operator attests once per boundary
  (`MIGRATION.md:188-190`).
- **A smaller, stable plan.** Program history belongs in tracked docs such as `docs/agents/goal-history.md`; upstream
  treats the plan as ephemeral task memory (`docs/workflow.md:117-127`).

What does not work:
- Legacy mode plus `--clear` removes the stops **and** the boundary.
- Dropping `autonomous` alone does not remove the stops. Once an attestation exists, tamper blocking applies in every
  mode (`inject-plan.sh:1106-1118`, `:1147-1151`, `:1177-1180`).

## 5. CHANGELOG 3.0 → 3.20.7: features for long-running, multi-agent and `/goal`-style work

Source: `$P/CHANGELOG.md:7-960`, read in full for this range. "Raymond" / `@sortakool` is credited upstream for #234,
#236, #237, #238 and #239 (`:256`, `:284`, `:359`).

| Ver | Feature | Relevance here |
|---|---|---|
| 3.0.0 | Autonomous mode (drops per-tool recitation); gated mode; run ledger (`ledger-append`/`ledger-summary`, `phase-status`); `task_plan_autonomous.md`; v3 refuses an unattested plan; nonce delimiters; `progress.md` tail no longer injected in v3 (`:929-959`) | This is where the attest friction comes from. Ledger-first is the matching remedy |
| 3.1.0 | Codex Stop no longer blocks on an incomplete plan (#178); codex PreCompact (`:899-927`) | Codex lanes are safe from forced continuation |
| 3.3.0 | Pi `/plan-execute` approval gate: hooks stay passive until a human approves the plan (`:773-789`) | A **human-approval pattern exists upstream, on Pi only**. It is the closest native analogue to D4's intent |
| 3.4.0 | `PLANNING_DISABLED=1` per-invocation opt-out (#195) (`:753-771`) | Adopted in `codex_lane` |
| 3.6.0 | `/plan-doctor`; 289 ms per hook fire (`:649-677`) | Brief B |
| 3.8.0 | `PWF_INJECT=smart`; `## Next Step`; Stop hook now fires on macOS and Linux (`:608-629`) | inject-smart is in use, but it expands the stale first `in_progress` phase (F2) |
| 3.9.0 | `PWF_PLAN_ROOT`; fails closed on an ambiguous cwd; `PWF_SCRIPT_DIR` (`:540-576`) | Worktree and nested-root safety |
| 3.10.0 | Parallel-write guard, on by default (`:516-538`) | Free advisory against two writers clobbering each other |
| 3.12.0 | Automatic catchup never reads host stores; phase-status lock (`:361-394`) | Privacy default |
| 3.13.0 / 3.14.0 / 3.20.0 | First-class Hermes, OpenCode and DSH plugins with gate parity (`:314-342`, `:286-312`, `:89-111`) | N/A |
| 3.15.0 | `PLAN_ID` becomes a binding (#237); root `.mode` is a floor for slugs (#238); plan-doctor classification (#236) (`:258-284`) | #238 is why a slug init inherits `autonomous` and auto-attests (F1 step 5) |
| 3.16.0 / 3.16.1 | PostToolUse nudge moves to `additionalContext`, once per turn, and `Bash` is dropped (#239); isolation requires `PLAN_ID` when there are multiple plans (`:237-256`, `:217-235`) | In use |
| 3.17.0 / 3.17.1 | Single-process Python fast path; multiple named plans refuse to inject without `PLAN_ID` (`:185-215`) | Relevant to the latency question (Brief B) |
| 3.18.0 | `set-active-plan.sh --list` (`:160-175`) | Denied here by the D4 pattern |
| 3.18.3 | Completed plans stay silent at Stop (`:134-138`) | — |
| 3.19.0 / 3.20.x | PowerShell slug init; `--verify-root`; a failed attestation is reported as NOT attested (#276); pointer hardening (`:14-132`) | — |

**Upstream-recommended workflow for one orchestrator plus worker lanes.** Sources: `SKILL.md:82-86`, `:239-259`;
`README.md:482-497`; `MIGRATION.md:171-190`; maintainer comments on #50 (2026-03-04, 04-15 and 09-05), read with
`gh api repos/OthmanAdi/planning-with-files/issues/50/comments`.
1. One orchestrator owns `task_plan.md` and the shared summaries. Workers never edit it; they report through their own
   `ledger-<agent>.jsonl` or assigned files.
2. Each independent task gets its own plan: `.planning/<date>-<slug>/` with `PLAN_ID` pinned on the host before start,
   or **separate worktrees** when the host cannot be pinned.
3. In v3 modes, the orchestrator re-attests at phase boundaries.
4. Workers that should not see the plan run with `PLANNING_DISABLED=1`.
5. Plans are ephemeral working memory. Anything durable gets promoted to docs or commits.
6. For work in a single stream, the maintainer recommends one plan, with a `Blocked` status for phases that wait on
   something external.

This repo already follows items 1, 4 and 5 in part. It follows item 2 through worktree-per-task; D1 was rejected
(`plan-attest-history-2026-09-23.md` § Rejected alternatives). It differs from upstream on plan size and lifetime: 1,640
lines, 19 phases, carried across sessions.

## 6. Findings

### F1 (measured): `init-session.sh --autonomous|--gated` is an attestation route no rule denies

**Mechanism.**
- `apply_v3_mode` (`init-session.sh:184-255`) runs `attest-plan.sh` as a child process (`:227`, `:235`).
- In root mode it attests the **existing** `./task_plan.md`: it skips files that already exist (`:398-406`), then
  attests (`:485`).
- D4 matches the Bash command string, so `sh …/init-session.sh --autonomous` does not match.
- No guard mentions it: `git grep init-session` over `python/src`, `.claude/settings.json`, `.claude/rules` and
  `docs/specs` returns 0 hits. Control: `git grep attest-plan` over `python/src` hits `hook_selfcheck.py`, `main.py`
  and `plan_attest.py`.

**Probe.** A `mktemp -d` git repo at `<scratchpad>/pwf-d4probe.gXCggG`, with `.mode`=`autonomous inject-smart`.

| Step | Action | Result |
|---|---|---|
| 1 | `init-session.sh --autonomous` | rc=0, "Mode: autonomous (attested, gate counter reset)". `.plan-attestation` = `76a50ce7…`, equal to `shasum -a 256 task_plan.md` |
| 2 | Appended a phase (a simulated agent rewrite; sha now `64c6e9cb…`), then ran `init-session.sh --autonomous` again | rc=0, `.plan-attestation` = `64c6e9cb…`. **A model-runnable command blessed the edit** |
| 3 | Side effect of step 1–2 | `.mode` rewritten from `autonomous inject-smart` to `autonomous` (`:202-206`), **dropping inject-smart**. The repo's `.mode` is tracked, so this also produces a diff |
| 4 | Control: bare `init-session.sh` with no flag | Attestation **unchanged**; `.mode` untouched (`MODE` is empty, `:187`) |
| 5 | Slug: `init-session.sh "Probe Slug"` | Inherited the root floor. New `.planning/<date>-probe-slug/` containing `.attestation`, `.mode`=`autonomous`, `.nonce` and `.stop_blocks` |

**Reach.** `/pwf` is model-invocable and instructs `init-session.sh --autonomous`/`--gated` (`commands/pwf.md:12`).

**Related gap (not exercised).** Nothing stops a direct write of the attestation file:
- `.plan-attestation` is gitignored (`.gitignore:151`), so `branch_guard` does not cover it.
- `permissions.deny` (settings.json:24-67) has no rule for a `Write` to it or for `shasum … > .plan-attestation`.
  There are 0 `plan-attestation` hits in `python/src` and in the settings.
- pwf states the digest "is an ordinary local SHA-256 value, not a keyed signature" (`SKILL.md:470`).

**Recommendation** (not applied; this lane is read-only):
- Add `Bash(*init-session.sh*)` and `Bash(*init-session.ps1*)` deny rules. A narrower `*--autonomous*` / `*--gated*`
  pattern would miss the slug-floor auto-attest in step 5.
- Add `Write`/`Edit` deny rules for `./.plan-attestation` and for `.planning/**/.attestation`.
- Add `hook_selfcheck` `plan-attest-deny` arms for each new rule.
- Consider a `skillOverrides` entry or a `Skill` deny for `planning-with-files:pwf` and `:plan`.
- Correct `.claude/CLAUDE.md`'s "all model routes denied" in the same diff.

### F2 (measured): pwf's machine view of `task_plan.md` is stale

**Observed.**
- `check-complete.sh` (read-only, rc=0) reports "2/19 phases complete … 2 phase(s) still in progress … 3 pending".
- `ledger-summary.sh` (read-only, rc=0) reports `entries: 0`, `phases: 2/19 complete` and
  `in_progress: ### Phase 2b: 2026-09-10 grilling outcomes — cleanup PR + codex substrate`.
- `**Status:**` lines exist only at `task_plan.md:628,636,650,658,669,675,695`, that is, Phases 1–6. Phase 2b and
  Phase 6 are `in_progress`. Phases 7–11, including the current Phase 11, have no status line.

**Consequences.**
- The `RUN LEDGER` block injected on every turn names a phase from 2026-09-10.
- inject-smart's "full first in_progress phase section" (`SKILL.md:389`) is Phase 2b, not Phase 11. This is inferred
  from the documented rule, not observed in a live injection.
- `progress.md` never reaches injection: autonomous mode replaces its tail with the ledger, which is empty.

**Remedy.** This is part of the migration and needs one operator attest. Either:
- mark stale phases `complete`/`blocked` and give every live phase a `**Status:**` line (values
  `pending|in_progress|complete`, per `task_plan_autonomous.md` § Phases); or
- move to a per-task plan with 3–7 phases.

## 7. Adoption proposal (ranked)

1. **Close F1 now.** Add the `init-session.sh`/`.ps1` and attestation-file deny rules, with selfcheck arms.
   - PRO: restores D4's stated invariant.
   - CON: the operator loses nothing, since the `!` prefix still runs it.
2. **Fix F2 in the plan edit the migration already needs.** Give every live phase a `**Status:**` line and close the
   stale phases, covered by one operator attest.
   - PRO: turn-start injection names the right phase.
   - CON: costs one attest, and it is the attest the migration needs anyway.
3. **Ledger-first progress for the orchestrator and SDLC lanes** (ADAPT `ledger-append.sh`). Lanes append `progress`,
   `phase_complete` and `error` events; `task_plan.md` changes only at phase boundaries.
   - PRO: fewer hash breaks, so fewer attest stops, and the boundary stays intact. The gate's stall detector gets a
     real signal if gating is ever enabled.
   - CON: a second channel alongside `progress.md`. The ledger scripts ignore `PLANNING_DISABLED`. Call sites are
     `sh <plugin-cache>/scripts/…` paths that change with every plugin upgrade, so they need a mise task to resolve
     the path, plus a guard review.
4. **Write down a phase-boundary attest cadence.** The agent batches plan edits and asks once per boundary for
   `! mise run plan-attest`. If the operator wants to see the diff first, precede it with `-- --show` and a
   `git diff --no-index` against a snapshot.
   - PRO: matches upstream's orchestrator model (`MIGRATION.md:189`).
   - CON: none beyond the discipline it takes.
5. **Keep `.mode` = `autonomous inject-smart`. Do not adopt gated mode, `/plan-loop` or `/plan-goal`** (reasons in §2c
   and §4). If a future task wants unattended "until done", write a native `/goal` from the repo's goal-writing spec,
   with printed `check-complete.sh` output as its evidence.
6. **Codex.** Keep the pwf codex plugin enabled and keep `PLANNING_DISABLED=1` on `codex_lane`. Decide #1307 for
   `sdlc_team` explicitly: either scrub it like `codex_lane`, or share the plan read-only and refuse dispatch on an
   unattested plan (Ray's Q50 ruling).
7. **Optional upstream ask.** Request a Claude Code analogue of Pi's `/plan-execute` (`CHANGELOG.md:777`), or a
   documented "operator-only attest" mode that lets `init-session`'s auto-attest be turned off. Not filed. An upstream
   issue search for `approval` returned 5 hits, none of them this request.

## 8. Gaps and unverified items

- That `/plan-goal`'s step 4 cannot execute is derived from docs (`$CC/commands.md:92`, `$CC/skills.md:744`) and
  matches the repo's own spec. It was not tested live, because invoking `/plan-goal` is user-only (DMI).
- That inject-smart expands Phase 2b is inferred from `SKILL.md:389` and the `ledger-summary` output. No live capture of
  `inject-plan.sh --context=userprompt` was taken here, because Brief B owns the injection measurements.
- The Write-tool bypass of `.plan-attestation` is reasoned from the deny list and the gitignore, **not exercised**:
  this lane must not write attestation files in the repo.
- Only 3.20.7 was read. Changes after 2026-09-23 are not covered.
- The throwaway probe used a `.mode` without `gate`. The gated-init behavior is inferred from `init-session.sh:202-203`.

## GitHub repos touched

- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files): installed plugin cache 3.20.7
  read locally (commands, SKILL.md, scripts, hooks, CHANGELOG 3.0–3.20.7, README, MIGRATION, docs/codex.md,
  docs/long-running-agent-tasks.md, docs/workflow.md); latest release, issue searches (`attest`, `approval`, open
  issues) and #50 comments via `gh api`.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): `.claude/settings.json`, `task_plan.md`,
  `.mode`, `python/src/dotfiles_setup/{codex_lane,sdlc_team}.py`, `docs/specs/goal-writing-and-phase2-dependency-currency.md`,
  prior report `plan-attest-history-2026-09-23.md`.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): offline Claude Code docs
  (`goal.md`, `scheduled-tasks.md`, `commands.md`, `skills.md`).
