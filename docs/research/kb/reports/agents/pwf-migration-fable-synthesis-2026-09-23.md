# pwf 3.20.7 migration — Fable synthesis (Brief C)

> Persisted verbatim by the coordinator at receipt (session `a6750a24`, 2026-09-23). Agent:
> `fable-orchestrator:fable-advisor` (read-only; no shell). Brief: `session-2026-09-23d-agent-briefs.md` § Brief C.
> Only change: the harness had neutralized `<` as `&lt;`; restored here.

Read-only lane; no shell, so nothing below was executed. Every fact is cited or marked unverified.

## 1. Verdict

Adopt upstream's shape almost verbatim: a small root `task_plan.md` as the **program roadmap** (changes only at rulings and phase boundaries), one **per-ticket plan** under `.planning/<date>-<slug>/` created *by the operator* with `! mise run plan-init`, all tick-level status in the run ledger, and `**Status:**` lines as the only phase signal. Close the F1 hole by denying `init-session.sh` outright — in this repo every slug init auto-attests because the tracked root `.mode` is a floor (`init-session.sh:170-182`, `:208-242`), so there is no model-safe form of it. Do not adopt `/plan-loop`, `/plan-goal`, gated mode, or any new hook; put the dark-hooks probe in the existing doctor. The deciding risk is the resolver: with no `.active_plan`, the **newest slug shadows the root plan** (`resolve-plan-dir.sh:287-300`), which is exactly the 2026-09-22c wrong-plan injection — so selection and close must be operator-owned steps, not conventions.

Note: this reverses D1 (slug mode REJECTED 2026-09-02). Both defects that justified D1 are fixed upstream — B by the `.mode` floor (#238, `init-session.sh:157-162`) and A by `PLAN_ID` becoming a binding (#237, `resolve-plan-dir.sh:315-324`) — and Ray's addendum already rules for slugs (`task_plan.md:588-593`).

## 2. Target workflow

**Layout.** Root `task_plan.md` (gitignored, `.gitignore:143`) = program: Goal / Next Step / `## Current Phase` / `### Phase N` with `**Status:**` / Decisions / Errors — the `task_plan_autonomous.md` shape (`templates/task_plan_autonomous.md:13-91`), ≤150 lines. Each `/implement` ticket = `.planning/<date>-<slug>/{task_plan.md,findings.md,progress.md,ledger-*.jsonl}` (`/.planning/` ignored, `.gitignore:146`), 3–7 phases. Root `.mode` stays `autonomous inject-smart` (tracked, `.gitignore:150`); slugs inherit it.

**Plan creation and attestation (no agent route).** Operator: `! mise run plan-init -- "<slug>" [--from .agent/plans/draft-<slug>.md]`. The task runs `init-session.sh "<slug>"` (auto-attests via the inherited floor), optionally copies the agent's draft over the template and re-attests with `PLAN_ID` bound (the same two calls init-session makes itself, `init-session.sh:226-230`), then pins `.planning/.active_plan` via `set-active-plan.sh`. Every write in that chain is already operator-only (`settings.json:31-36`); the `!` prefix bypasses tools and hooks (`plan_attest.py:46-49`). The agent drafts to `.agent/plans/draft-<slug>.md` — the same proposal path the file-roles rule uses for `task_plan.md` deltas (agent-report-persistence §3). ⚠️ Unverified: whether slug-mode `init-session.sh` writes `.active_plan` itself, and its behaviour on a pre-existing slug dir; the ticket must probe both in a throwaway repo.

**Status.** `**Status:** pending|in_progress|complete` in the plan = the phase signal (`check-complete.sh:95-97`, `:267-271`), edited only at boundaries. Tick-level progress = `mise run plan-log -- <event> "<summary>" --phase N [--agent <lane>]` wrapping `ledger-append.sh` (events at `ledger-append.sh:18`; path via `listing_budget.plugin_root` as `plan_attest.py:68,149` does). Autonomous mode injects the ledger summary, not `progress.md` (`SKILL.md:381`, `:482`), so the ledger is what the model sees; `progress.md` stays the human log and `/session-resume` recovery input. Ledger ignores `PLANNING_DISABLED` (inventory §2b), so scrubbed codex lanes can still log.

**Exactly when Ray is stopped.**
1. `! mise run plan-init` — new ticket plan (creation = approval).
2. `! mise run plan-attest` — after a root-plan ruling/phase-boundary edit, or after the agent's first fill of a fresh slug plan when `--from` was not used (`MIGRATION.md:188-190`).
3. `! mise run plan-close -- <slug>` — task done: renames `task_plan.md` → `task_plan.archived.md` (resolver then skips it, `resolve-plan-dir.sh:300`; the leftover dir already uses this name), clears `.active_plan`, flips the root phase Status, re-attests root. One stop for three writes.
4. `AskUserQuestion` on genuine ambiguity / missing spec (clarify-before-acting).
5. Protocol verbs (`/to-spec`, `/to-tickets`, `/implement`, `/goal`) and codex `/hooks` trust — user-typed by design.
Nothing else stops: gates, ship, land, cold review run autonomously.

**Codex lanes / sdlc-team.** `codex_lane` already scrubs (`codex_lane.py:136`). `sdlc_team.py` passes no `env` at either `Popen` (`:805-815`, `:961-968`) — #1307 fix: `env={**os.environ, **LANE_ENV_OVERRIDES}` on both, plus the Q50 pre-dispatch refusal when `sha256(resolved plan) != attestation` (read-only python; no deny pattern touched). Lanes report via `progress.md` append or `plan-log --agent <lane>`; never the plan (`SKILL.md:85`).

## 3. Ordered change list

| # | Change | Why | Files | Drift | Route |
|---|---|---|---|---|---|
| 1 | Deny `Bash(*init-session.sh)`, `(*init-session.sh *)`, `.ps1` twins; `Bash(*.plan-attestation*)`, `Bash(*/.attestation*)`, `Bash(*.active_plan*)`; `Edit(.plan-attestation)`, `Edit(.planning/**/.attestation)`, `Edit(.planning/.active_plan)`; extend `_ATTEST_DENY_BASES` (`hook_selfcheck.py:756-762`) and the `plan-attest-deny` arm; fix `.claude/CLAUDE.md:20-22` "all model routes denied" | F1 measured: model-runnable re-bless at rc=0 (inventory F1 step 2); `/pwf` instructs it (`commands/pwf.md:12`). ⚠️ `Write()` path rules are never consulted (secrets rule §8, `$CC/permissions.md:316`) — the Write-tool path stays a residual; cover it with a `hook_guard` Write/Edit rule, fail-open acknowledged | `.claude/settings.json`, `hook_selfcheck.py`, `.claude/CLAUDE.md` | none | ticket (security, first) |
| 2 | `sdlc_team.py` env scrub + attestation pre-check | #1307; lanes saw `PLAN TAMPERED` 09-18/09-21 | `sdlc_team.py`, tests | none | ticket |
| 3 | `plan-status` module + task: resolved plan dir, `## Current Phase`, sha vs attestation MATCH/MISMATCH, `check-complete.sh` (no `--gate`) + `ledger-summary.sh` output, `.active_plan` state, ambiguity (`resolve-plan-dir.sh --check-ambiguity`, `SKILL.md:227`) | The model cannot run `-- --show` (`settings.json:38`), so today it learns tamper only from the hook banner; both skills need this one read | `python/.../plan_status.py`, `mise.toml` | none | ticket |
| 4 | `plan-pointer` / `handoff-check`: resolve the active dir; read `## Current Phase` instead of the `NEXT SESSION` heading (`plan_pointer.py:19`, `handoff_check.py:221-229`); pointer gains `plan_id` | Two conventions in one file is why pwf names Phase 2b while our pointer names Phase 11 (F2) | `plan_pointer.py`, `handoff_check.py`, `docs/agents/plan-pointer.json`, tests | removes our only divergence | ticket |
| 5 | `plan-init` / `plan-close` / `plan-log` thin tasks (python resolves plugin root; no flag enumeration, per `plan_attest.py:169-173`) | Script paths change per plugin version (inventory §7.3); close must be atomic | new module(s), `mise.toml`, deny list (plan-init/close are operator-only like plan-attest) | none — wraps upstream scripts | ticket |
| 6 | Doctor `pwf-hooks` check (Lane B option B): FAIL-only, skip under `PLANNING_DISABLED`, shims dir stripped from child PATH, canary test with a `PLANNING_DISABLED=1` fixture; add "slug resolves but `.active_plan` unset" as a finding | Dark hooks are the one signal hooks cannot give (`plan-doctor.sh:72`); rc is always 0 (`:18`,`:170`); silent-selection is the 09-22c trap | `doctor.py` `CHECKS` (`:1323`), `doctor.toml` `[pwf]` | none | ticket |
| 7 | Migrate the plan (operator + agent, not a ticket): agent drafts a ≤150-line root plan (Phases 10, 11 as `### Phase` + Status; Decisions table; Errors); the 1,640-line file → `.planning/archive/2026-09-23-program/task_plan.archived.md` (gitignored); rulings/traps worth citing → goal-history iteration 032 (required anyway for a topology change) and a tracked `docs/agents/plan-archive-2026-09-23.md` decisions extract (upstream's suggested opt-in archive, `workflow.md:127`). Operator attests once | F2; upstream: plans are ephemeral, durable content is promoted (`workflow.md:117-123`) | `task_plan.md`, `docs/agents/goal-history.md` | none | operator ruling + one attest |
| 8 | Leftover `.planning/2026-09-21-graphify-…`: already inert (`task_plan.archived.md`, no `task_plan.md`); move under `.planning/archive/` for uniformity; confirm `.planning/.active_plan` is absent (my Glob listed none — treat as unverified until the doctor asserts it) | It is the first instance of the close convention | fs only | none | part of 7 |
| 9 | Skill edits (§4) | — | two SKILL.md | none | same ticket as 3/4 |

## 4. `/session-handoff` and `/session-resume`

**Handoff** (`session-handoff/SKILL.md`):
- §0 (`:17-29`): "active phase in `task_plan.md`" → "the resolved plan (`mise run plan-status`)". Rulings still go to the root plan; add: *batch all plan edits, then request `! mise run plan-attest` ONCE at the end of §0, never mid-session.*
- §1 (`:46-53`): keep `mise run plan-pointer` (now slug-aware); add `mise run plan-status` and `mise run doctor` (Lane B §7: a skill step, not a hook). Add `mise run plan-log -- note "handoff <date>" ` so the ledger tick moves.
- §3b (`:221-231`): handoff records `plan_id`, sha, attestation MATCH/MISMATCH, ledger tick. If MISMATCH, the handoff's "owed" list must name `! mise run plan-attest` (this is the 09-23 recurrence, attest-history §6).
- §5 (`:286-297`): unchanged text; `handoff-check` now resolves slugs.
- Checklist (`:307-325`): add "`plan-status` MATCH or attest explicitly owed", "no slug with a live `task_plan.md` lacks `.active_plan`", "completed task closed via `plan-close`".

**Resume** (`session-resume/SKILL.md`):
- §1 (`:22-45`): after reading the handoff, list `.planning/*/task_plan.md`; >1 live and no `.active_plan` = report **AMBIGUOUS** before anything else.
- §2 (`:47-66`): add `mise run plan-status` beside `session-state` (keep `session_state.py` git/PR-only; plan facts belong to the new module).
- §3 shape (`:81-91`): `PLAN: <root|plan_id> → <Current Phase> [attested | TAMPERED — owed: ! mise run plan-attest]`.
- §4 (`:96-100`): when TAMPERED, the first offer is the attest, not "begin the phase" — hooks inject nothing until then (`inject-plan.sh:1129-1134` per inventory; Lane B F3).

## 5. Not adopted

- `/plan-loop`: each tick edits Status → tamper (`plan-loop.md:21`). `/plan-goal`: `/goal` is not model-invocable; default condition unreachable (inventory §4). Gated mode: one forced turn, gate never reads attestation, and stops for operator-only actions are legitimate (inventory §2c). `/pwf`, `/plan`, `start`: model-invocable init routes. `phase-status.sh`: revisit only if concurrent Status writers appear. A Claude function hook or codex hook for plan-doctor: fails open/silent, false FAIL in every lane (Lane B §4, §6). `PLAN_ID` in `settings.json` env: a global pin defeats per-task selection — use `.active_plan`, operator-written.
- **F2 (coreutils shim tax)**: out of scope; file one KB ticket (`knowledge-base/mise.toml:247`); the doctor check only strips the shims dir from its child PATH. F1 (doctor times the wrong chain) → upstream issue, optional.

## 6. Open questions for Ray

1. Deny `init-session.sh` entirely (recommended — the floor makes every form attest) vs flag-only patterns?
2. Root `task_plan.md` stays the program plan (recommended; zero drift, resolver falls back to it when no slug is live) vs a `.planning/program/` slug (needs a perpetual pointer)?
3. Archive: gitignored `.planning/archive/` + tracked decisions extract (recommended) vs tracked verbatim 1,640 lines?
4. `plan-init --from <draft>` (one stop per ticket; ~20 lines python over two upstream calls, recommended) vs init-then-edit-then-attest (two stops, zero custom code)?
5. `sdlc_team`: scrub like `codex_lane` (recommended) vs share read-only with the Q50 refusal only?
6. `plan-close` operator-only (recommended — it clears `.active_plan`, and D4's arbiter put selection in the operator set) vs agent-runnable?

**Deciding risk:** the newest-mtime resolver. Without operator-owned `plan-init`/`plan-close` and the doctor's "slug live, pointer unset" finding, a stray slug silently replaces the program plan again.

Unverified (name in the ticket): slug-mode `init-session.sh` and `.active_plan`; inject behaviour when the pointer names a dir without `task_plan.md`; Write-tool reach of the `Edit()` deny; current absence of `.planning/.active_plan`.

Files: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/settings.json`, `python/src/dotfiles_setup/{plan_attest,plan_pointer,handoff_check,session_state,sdlc_team,codex_lane,hook_selfcheck,doctor}.py`, `.claude/skills/{session-handoff,session-resume}/SKILL.md`, `task_plan.md`, `docs/agents/plan-pointer.json`, `docs/agents/goal-history.md`, `.planning/2026-09-21-graphify-0-9-65-skill-refresh/`.

## GitHub repos touched

- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — installed 3.20.7 source (init-session, resolver, templates, MIGRATION, workflow docs).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — settings, skills, python modules, reports.
