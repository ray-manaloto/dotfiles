# Agent briefs — session 2026-09-23d (`a6750a24`): pwf current-workflow migration research

Persisted verbatim at dispatch (`.claude/rules/agent-report-persistence.md`). Ruling:
`task_plan.md` § "Addendum — pwf current-workflow migration is Phase 11's FIRST PRIORITY".

Shared context for every brief below:

- Repo: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`, branch `docs/session-2026-09-23d-handoff`.
- pwf plugin installed: `~/.claude/plugins/cache/planning-with-files/planning-with-files/3.20.7`
  (latest release, 2026-09-23). Upstream repo: `OthmanAdi/planning-with-files`.
- Current setup: legacy ROOT plan (`./task_plan.md`, ~1,600 lines, many phases), `./.plan-attestation`,
  `.mode` = `autonomous inject-smart`, no ledgers, a leftover `.planning/2026-09-21-graphify-…/` holding only
  `task_plan.archived.md`. `plan-doctor.sh` rc=0: `PASS resolver: legacy root plan`, `WARN injection: hash
  mismatches`, one `inject-plan.sh` fire 4,058 ms.
- Model attest routes are denied in `.claude/settings.json` (D4, commit `f6ee355d`); the operator attests with
  `! mise run plan-attest`. History: `docs/research/kb/reports/agents/plan-attest-history-2026-09-23.md`.
- Harness docs on disk: `$CC=~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`,
  codex docs under `.../docs/codex`.
- Read-only: edit NOTHING except your own report file. Never run `attest-plan.sh`, `/plan-attest`,
  `mise run plan-attest` (bare form WRITES), `init-session.sh`, `set-active-plan.sh` or `ledger-append.sh` in
  the repo. If you need to exercise a pwf script, do it in a throwaway `mktemp -d` git repo only.
- Never run an `agentsview` command without `--server`; never `agentsview health`. `timeout` is a broken mise shim.
- Persist incrementally: create your report early and update it as you go. Every claim cites `file:line` or a
  URL you actually read; mark anything unverified as such. End with `## GitHub repos touched`.
- Return the full report text as your final message.

## Brief A — pwf skills/commands inventory and adoption proposal

Report path: `docs/research/kb/reports/agents/pwf-skills-inventory-2026-09-23.md`.

Inventory EVERY pwf 3.20.7 command, skill, script and hook the plugin ships (`commands/*.md`,
`skills/**/SKILL.md`, `scripts/*`, `hooks/*`), with priority on `/planning-with-files:plan-loop`,
`/planning-with-files:plan-goal`, `/planning-with-files:status`, `/planning-with-files:start`,
`/planning-with-files:plan-doctor`, `/pwf` (with `--autonomous`/`--gated`), gated mode's Stop gate,
`ledger-append.sh`/`ledger-summary.sh`, `set-active-plan.sh`, `PLAN_ID`/`PWF_PLAN_ROOT`, `session-catchup.py`,
`check-complete`, `phase-status`, `sync-ide-folders.py`, and the codex integration (`docs/codex.md`).
For each: what it does (cite source), whether it has `disable-model-invocation`, whether it writes files or
attests, how it interacts with this repo's D4 deny rules (`.claude/settings.json:31-41`), and a disposition
ADOPT / ADAPT / SKIP with pros and cons. Also read `CHANGELOG.md` for 3.0–3.20.7 and extract every feature
aimed at long-running, multi-agent, or `/goal`-style autonomous work, and the upstream-recommended
workflow for a multi-session, multi-agent program like this repo's (one orchestrator, codex worker lanes).
Explicitly answer: how does `/plan-goal` relate to Claude Code's native `/goal` (`$CC/goal.md`), and how does
`/plan-loop` relate to Claude Code `/loop`? Which of these reduce operator attest stops without weakening the
human-approval boundary?

## Brief B — plan-doctor as a Claude function hook and a codex hook

Report path: `docs/research/kb/reports/agents/pwf-plan-doctor-hooks-2026-09-23.md`.

Question: should `/planning-with-files:plan-doctor` (`scripts/plan-doctor.sh`) run automatically as (1) a Claude
Code FUNCTION hook and (2) a codex hook, at session start or at specific turns — and if so, which events,
what output, and with what failure behavior? Deliver 2-4 cited options with pros/cons and a recommendation.

Research:
- What `plan-doctor.sh` checks and emits, its exit codes (can it fail? does it ever exit non-zero on WARN?),
  whether it writes anything, and its cost. Measure its wall clock and one `inject-plan.sh` fire in a throwaway
  repo AND (read-only) here; explain the 4,058 ms fire vs pwf's quoted ~289 ms (`docs/perf-notes.md`,
  README) — is it the plan size, the SHA cache (`~/.cache/pwf-sha`), `inject-smart`, or something else?
- Claude Code function hooks: the `plugin-authoring` skill, `$CC/hooks.md` (SessionStart, UserPromptSubmit,
  InstructionsLoaded, etc.), and how this repo already wires hooks: `.claude/settings.json`, the SessionStart
  doctor (`doctor.toml`, `mise run doctor`), `python/src/dotfiles_setup/hook_selfcheck.py`, and the memory note
  that `@skills-dir` loads a function hook with no install and that runtime failures fail OPEN and SILENT.
  Would plan-doctor be better as a `doctor.toml` check inside the existing SessionStart doctor (silent when
  healthy) than as a new hook? Compare.
- Codex hooks: codex docs in the KB corpus, this repo's `.codex/hooks.json` / `.codex/config.toml`, the pwf
  codex integration (`docs/codex.md` in the plugin), `codex_lane.LANE_ENV_OVERRIDES` (`PLANNING_DISABLED=1`)
  in `python/src/dotfiles_setup/codex_lane.py`, and #1334/#1336 (codex SessionStart/PreToolUse additions
  awaiting `/hooks` trust). Is a codex SessionStart hook the right place, given codex lanes run with planning
  disabled?
- Which specific turns (beyond session start) make sense — e.g. after a `task_plan.md` write, before an
  `/implement` dispatch, at `/session-handoff` — and whether pwf's own hooks already cover them.

## Brief C — Fable synthesis (`fable-orchestrator:fable-advisor`, read-only)

Report path (persisted by the coordinator at receipt): `docs/research/kb/reports/agents/pwf-migration-fable-synthesis-2026-09-23.md`.

Decision: how to migrate to pwf 3.20.7's current workflow with the least upstream drift, keeping `autonomous` and
D4, and what to change in this project and in `/session-handoff` / `/session-resume`. Inputs: the three reports
above (`plan-attest-history`, `pwf-skills-inventory`, `pwf-plan-doctor-hooks`), this briefs file, the two
SKILL.md files, `handoff_check.py` / `plan_pointer.py` / `session_state.py` / `plan_attest.py`, pwf SKILL.md
78-86 / 370-386 / 465-490, MIGRATION.md 183-191, docs/workflow.md 195-245, commands/pwf.md, init-session.sh
150-215, and the rules `agent-report-persistence.md`, `goal-history.md`, `.claude/CLAUDE.md`. Deliverables:
verdict; target workflow (layout, plan creation + attestation without an agent self-attest route, status
location, exact operator stop events, codex/sdlc-team fit); ordered change list (incl. the init-session/`/pwf`
self-attest hole, `.plan-attestation` write path, the plan-doctor doctor check, stale Status lines, migrating the
1,640-line plan, the leftover `.planning/2026-09-21-graphify-*`); concrete handoff/resume changes; what not to
adopt (incl. F2 disposition); open questions for Ray with recommended answers; file:line for every claim.

## Brief D — codex-astra completeness review of the research + Fable proposal (`codex-astra-adversarial-critic`)

Report path: `docs/research/kb/reports/agents/pwf-migration-astra-review-2026-09-23.md`.

Ray's instruction (verbatim): "have a codex astra agent review the findings of the research and fable adviser's
proposal to make sure nothing was missed". Attack the PROPOSAL `pwf-migration-fable-synthesis-2026-09-23.md`
against its inputs (`plan-attest-history-2026-09-23.md`, `pwf-skills-inventory-2026-09-23.md`,
`pwf-plan-doctor-hooks-2026-09-23.md`, this briefs file) and the real code: the installed pwf 3.20.7 plugin
(`~/.claude/plugins/cache/planning-with-files/planning-with-files/3.20.7`), `.claude/settings.json`,
`python/src/dotfiles_setup/{plan_attest,plan_pointer,handoff_check,session_state,sdlc_team,codex_lane,hook_selfcheck,doctor}.py`,
`.claude/skills/{session-handoff,session-resume}/SKILL.md`, `.codex/hooks.json`, `~/.codex/config.toml` (pwf plugin
block only — read no other part; it may hold credentials). Find: (1) omissions — attest/self-attest routes,
selection/shadowing paths, codex-side pwf hooks (the pwf codex plugin + `PLAN_ID`/`.active_plan` under codex),
knowledge-base parity, goal-history/plan-pointer/handoff-check consumers, tests/contracts (`suites.toml`,
`hook_selfcheck`) that pin the current root-plan assumptions and would break; (2) claims in the proposal that the
code contradicts (cite file:line, replay them); (3) whether each ordered change actually closes its motivating
defect; (4) anything the three research reports found that the proposal dropped. Read-only: edit nothing except
your report; do NOT run `attest-plan.sh`, `init-session.sh`, `set-active-plan.sh`, `ledger-append.sh`,
`mise run plan-attest`, or any repo gate; a throwaway `mktemp -d` repo is allowed for pwf probes. Persist the report
incrementally; every finding cites file:line plus a probe and its control arm; end with `## GitHub repos touched`.

## Brief E — Fable revision (round 2) of the migration proposal (`fable-orchestrator:fable-advisor`)

Report path (persisted by the coordinator at receipt): `docs/research/kb/reports/agents/pwf-migration-fable-revision-2026-09-23.md`.

Revise `pwf-migration-fable-synthesis-2026-09-23.md` into a spec-ready design that (1) absorbs every finding of
`pwf-migration-codex-astra-verdict-2026-09-23.md` (C1-C7, §2 A-F, §4 table, gates/tests list) and the useful
parts of `pwf-migration-astra-review-2026-09-23.md` (incl. its coordinator annotations); (2) obeys Ray's
rulings recorded in `task_plan.md` § "Addendum — pwf current-workflow migration" (rounds 1-2): upstream-first
("assume what we are doing is wrong"), root roadmap + per-ticket slugs, ignored archive + tracked extract,
`PLAN_ID` per worktree, ONE merged workflow for knowledge-base AND dotfiles with per-repo/per-task flags on a
shared skill/mise task/python library, attestation posture "upstream + its hardening"; (3) specifies the merged
workflow against knowledge-base's current pwf usage (`~/dev/github/ray-manaloto/knowledge-base/.planning/`,
its `.claude/skills/session-resume/SKILL.md`, `.claude/skills/clear-prep/references/plan-archive.md`,
`.claude/settings.json`) — where the shared code lives (the SHA-pinned `kb_setup` package already shared via
uv git dep is a candidate; verify) and which flags differ per repo; (4) answers the open design items: root
re-attest while a slug is live (C2), close/archival semantics and parent-phase mapping (C3/C7), init-session
lifecycle (C4), the exact deny list for "new named plans allowed, re-bless denied", codex-side parity (the codex
pwf plugin's own install + 7 hooks), sdlc_team env scrub, the doctor probe choice, the 7-step plan migration
with obligation mapping and goal-history 032 (writer = the coordinator), and every consumer/test/contract to
change. Output: verdict; target workflow; ordered ticket list (each with files, closes-which-defect, upstream
drift, verification); `/session-handoff` + `/session-resume` changes; not-adopted list; remaining open questions
with recommendations; file:line for every claim; unverified items named.

## Brief F — Fable round 3: re-derive under upstream's trust model (`fable-orchestrator:fable-advisor`)

Report path (persisted by the coordinator at receipt): `docs/research/kb/reports/agents/pwf-migration-fable-round3-2026-09-23.md`.

Ray's round-4 ruling ADOPTS UPSTREAM'S TRUST MODEL and supersedes D4 (read `task_plan.md` § "Addendum — pwf
current-workflow migration", rounds 1-5, and `pwf-upstream-tracker-review-2026-09-23.md`). Re-derive
`pwf-migration-fable-revision-2026-09-23.md` into the FINAL spec-ready design: (1) drop or rework every item that
existed only for operator-only attestation (D4 deny list and its extension, `plan_attest.py` wrapper, the
`plan-attest` selfcheck arms/contracts at `hook_selfcheck.py:756-762` and `suites.toml:1862-1866`,
`.claude/CLAUDE.md` operator-only paragraph, `plan-init` as a deny route, `--force` operator-only, `--from`
rejection) — say for each whether it is retired, kept for a non-D4 reason, or replaced by upstream behavior;
(2) keep every non-D4 codex finding (C1 one-live-slug/`PLAN_ID` per worktree, C3/C7 close via
`.planning/.archive/`, C4 init post-state, C6 status data, reader/test/mirror consumers, doctor probe); (3) state
who attests when (orchestrator at phase boundaries per pwf `MIGRATION.md:188-190`; can the agent now just use
`/pwf` and `attest-plan.sh` directly — minimize wrappers to what upstream lacks); (4) answer Ray's question:
should sdlc_team changes wait for Phase 10 (fable-orchestrator + other plugin retirement; sdlc_team becomes the
one codex entry point) — read Phase 10 in `task_plan.md` (grep "## Phase 10") and propose the split; lanes SEE the
plan per round 5; (5) keep the merged KB+dotfiles workflow in `kb_setup` with per-repo flags, KB slug archive via
`plan-close`, goal-history 032 with changed goal text (writer = coordinator); (6) the operator's remaining stops.
Output: verdict; target workflow; final ordered ticket list (files, closes-which-defect, upstream drift,
verification arms); `/session-handoff` + `/session-resume` changes; retired-items table; open questions (if any)
with recommendations; file:line for every claim; unverified items named. Aim ~1,800-2,500 words.
