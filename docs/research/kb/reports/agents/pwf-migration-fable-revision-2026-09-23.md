> Persisted verbatim by the coordinator at receipt from the subagent transcript (`fable-orchestrator:fable-advisor`, Brief E, session `a6750a24`, 2026-09-23).

# pwf 3.20.7 migration — Fable revision, round 2 (Brief E)

Lane: `fable-orchestrator:fable-advisor`, read-only (Read/Grep/Glob only — no shell, so `mise run graphify-query` could not run; `findings.md`/`progress.md` could not be appended). Every claim below cites what I read this turn; items I could not check are listed in §10. The coordinator persists this at `docs/research/kb/reports/agents/pwf-migration-fable-revision-2026-09-23.md`.

## 1. Verdict

Keep the round-1 shape (root roadmap + per-ticket slug, `autonomous inject-smart`, D4) but change four mechanisms the codex verdict showed do not hold:

1. **Selection is structural, not a pointer.** Every `.planning/` holds at most ONE live slug (`plan-init` refuses otherwise). With one live slug the resolver never reaches the ambiguity branch (`resolve-plan-dir.sh:343-361`), so `.active_plan` and newest-mtime agree by construction; `PLAN_ID` is pinned only in ticket worktrees, never in the main clone (C1, §2.2).
2. **Root is edited and attested only when no ticket is live.** Upstream has no "attest root" operation while a slug resolves (`attest-plan.sh:44-56,73-76`); rather than add one, the workflow sequences root edits to the boundary where root IS the resolved plan (C2, §2.4).
3. **Close = move to `.planning/.archive/<id>/`** (the knowledge-base convention, `plan-archive.md:24`), never rename: a hidden dir is skipped by the scan (`resolve-plan-dir.sh:295-297`) and a moved dir fails both `PLAN_ID` and pointer resolution closed (`:259`, `:278`) — rename does not (C3). Close never writes the pointer, so it needs no operator stop (C7, §2.5).
4. **The model-allowed creation route is `mise run plan-init -- "<name>"`** (slug mode only, unmodified upstream script underneath, template auto-attested by the inherited floor); the raw `init-session.sh/.ps1` is denied because its ROOT form re-blesses an existing plan (F1: `init-session.sh:398-406` skip-existing then `:485` attest). This is "upstream + its hardening" in substance; it does break `/pwf`'s literal step (§9 Q2).

Deciding risk: a stale `PLAN_ID` in a long-lived process env silently darkens hooks after close (`inject-plan.py:905-910` bails on a dir without `task_plan.md`). §2.2 confines `PLAN_ID` to worktrees so that state is one process lifetime long, and `plan-status`/doctor name it.

## 2. Target workflow

### 2.1 Layout

| Path | Role | Tracked |
|---|---|---|
| `./task_plan.md` | Program roadmap: Goal / Next Step / `## Current Phase` / `### Phase N` + `**Status:**` / Decisions (≤10 rows) / Errors — `templates/task_plan_autonomous.md` shape; ≤150 lines; edited only at phase boundaries | no (`.gitignore:143`) |
| `./.mode` = `autonomous inject-smart` | The floor every slug inherits (`init-session.sh:170-182`) | yes (`.gitignore:150`) |
| `./.plan-attestation` | Root digest, operator-written | no (`:151`) |
| `.planning/<date>-<slug>/{task_plan.md,findings.md,progress.md,.attestation,.mode,.nonce,ledger-*.jsonl}` | One per `/implement` ticket, 3–7 phases | no (`:146`) |
| `.planning/.active_plan` | Written by upstream init (`init-session.sh:468`); informational here | no |
| `.planning/.archive/<id>/` | Closed tickets + the 2026-09-23 program archive | no |
| `docs/agents/plan-archive-2026-09-23.md` | Tracked decisions/traps/obligation extract | yes |
| `docs/agents/goal-history.md` | Program record, append-only (iteration 032 here) | yes |
| `docs/agents/plan-pointer.json` | Digest pointer, new two-authority schema (§2.6) | yes |

### 2.2 Binding (C1, Ray's `PLAN_ID`-per-worktree ruling)

- **Main clone:** no `PLAN_ID`. `plan-init` refuses when `.planning/*/task_plan.md` already matches one live dir ("close `<id>` or start a worktree"). One live slug ⇒ `PLAN_COUNT=1` ⇒ `.active_plan` selects it (`:367`) and mtime would too (`:368`); root is reached only when none is live.
- **Ticket worktree:** `.planning/` is gitignored so each worktree has its own; `plan-init --pin` writes `[env] PLAN_ID = "<id>"` into that worktree's gitignored `mise.local.toml` (the existing per-clone override file, root `AGENTS.md`), so the shell that launches `claude`/`codex` carries the binding upstream requires (`docs/codex.md:234`). `plan-init` also refuses when the process env already has a `PLAN_ID` that differs from the id it just created — the exact stale-pin trap.
- Ledger binding (codex §2B): `plan-log` resolves once (env `PLAN_ID` → `.active_plan` → the single live dir), passes that id explicitly as `PLAN_ID` to `ledger-append.sh`, and refuses when resolution is empty or ambiguous — never the `.` fallback at `ledger-append.sh:59-64`.

### 2.3 Creation and attestation (Q1 ruled, Q4)

1. Agent: `mise run plan-init -- "<ticket title>"` → wrapper execs `sh <root>/scripts/init-session.sh "<title>"` from the project root (never `--autonomous`, never root mode); captures the printed `PLAN_ID=` (C4: names collide to `-2`, `init-session.sh:454-458`), then verifies post-state: dir exists, `.mode` inherited (`autonomous`, `:202-206`), `.attestation` == sha256(template) (attest failure is rc=0 upstream, `:244-254`, so the wrapper must check bytes), `.active_plan` == id. Any miss → rc≠0 and the wrapper prints what to remove.
2. Agent fills the ticket plan (Goal `#NNNN`, 3–7 phases, exactly one `in_progress`). Hash now differs → injection refused until attested (`SKILL.md:481`).
3. **Operator stop 1:** `! mise run plan-attest` — the review point. The wrapper first prints `Target: .planning/<id>/task_plan.md` (resolver output) and refuses when root `task_plan.md` is unattested while a slug resolves (C2 diagnostic; no new flag).
4. `--from <draft>` is dropped: it would have the agent's own bytes attested by an agent-runnable command — the principal D4 forbids (attest-history §Synthesis 2). Upstream's init only ever blesses generated template bytes (`attestation-locking.md:12-13`).

### 2.4 Root roadmap edits (C2)

Root is injected only when no slug resolves. So: root edits happen after `plan-close` and before the next `plan-init`; **operator stop 2** = `! mise run plan-attest` then (resolver empty → `attest-plan.sh:73-76` root). A mid-ticket ruling goes to the ticket plan's Decisions row or the handoff, and the root edit is batched to the boundary. `plan-status` shows root MATCH/MISMATCH at all times so a premature root edit is visible.

### 2.5 Close (C3, C7, Q6)

`mise run plan-close -- <id>` (model-runnable; `--force` denied to the model):
1. Resolve; refuse unless resolved id == `<id>`.
2. `check-complete.sh` (no `--gate`) must print `ALL PHASES COMPLETE` (`check-complete.sh:126-128`) or `--force` was given (ledger `note` records the reason).
3. `ledger-append.sh phase_complete "closed <id>"` (bound as §2.2).
4. `mv .planning/<id> .planning/.archive/<id>` (verify post-condition; hidden dir ⇒ never selectable).
5. Never touch `.active_plan` (it now names a missing dir → `resolve_from_active_file` returns 1, `:278` → root; `set-active-plan.sh:320-321` calls that "stale pointer"; next `plan-init` overwrites it via upstream). No pointer write ⇒ no D4 surface.
6. If `mise.local.toml` `[env] PLAN_ID == <id>`, delete the line and print "your running session still carries PLAN_ID=<id>; start a new terminal before the next ticket".
7. Print the parent-phase reminder: grep root `task_plan.md` for `#NNNN` and report "ticket belongs to `### Phase N`; N lists K other open tickets" — flipping a root `**Status:**` is a coordinator edit at the boundary (§2.4), never automatic (C7: Phase 11 has 16 tickets).
Non-transactional by design; every step verifies its post-condition and `plan-status` names each partial state (archived dir still live-shaped, pointer stale, env pin stale).

### 2.6 Status and pointer (C6, codex E)

- Phase signal = the first `### Phase` heading followed by `**Status:** in_progress` — the rule `ledger-summary.sh:114-137` and `check-complete.sh:95-97` already use. `plan_pointer.active_phase` and `handoff_check._plan_findings` switch to that rule and the `NEXT SESSION` convention is retired (`plan_pointer.py:19`, `handoff_check.py:221-229`). Parser and pwf then cannot disagree; `plan-status` warns on >1 `in_progress`.
- Pointer schema: `{"root":{"plan_sha256","active_phase"},"ticket":{"plan_id","plan_sha256","active_phase"}|null,"recorded_at"}`; `handoff-check` verifies both against disk and reports `MISSING_ROOT_PLAN` when root is absent (today it returns `[]`, `handoff_check.py:217-219`).
- `plan-status` (one module, one resolution passed to every reader): resolved target, root and ticket sha vs attestation (MATCH/MISMATCH/UNATTESTED), `.active_plan` state (live/stale/absent), env `PLAN_ID` state, live-slug count, `check-complete.sh` report, `ledger-summary.sh` block, and "archived dir referenced by pointer/pin".

### 2.7 Exact operator stops

1. `! mise run plan-attest` after the agent fills a new ticket plan (per ticket).
2. `! mise run plan-attest` after a root-roadmap edit at a phase boundary (per phase).
3. `! mise run plan-close -- <id> --force` when closing an incomplete ticket.
4. `AskUserQuestion` on genuine ambiguity; protocol verbs and codex `/hooks` trust (user-typed by design).
Nothing else — gates, ship, land, cold review, `plan-init`, `plan-close`, `plan-log`, `plan-status` run autonomously. Cadence correction (codex): attest per phase boundary, which may be several times in one session.

### 2.8 Codex parity (codex §2C)

- Interactive codex sessions: the pwf codex plugin is enabled globally with all 7 hooks trusted (`~/.codex/config.toml:257-258`, `:499-518`); it resolves the same `.planning/`, `.active_plan`, `PLAN_ID` (`docs/codex.md:232-236`), so the layout serves both hosts. Gated mode stays off in both repos (the codex Stop can `block`, `.codex/hooks/stop.py:26-30`).
- Lanes: `codex_lane` scrubbed (`codex_lane.py:136,469`); `sdlc_team` gets `env={**os.environ, **LANE_ENV_OVERRIDES}` on BOTH `Popen` (`sdlc_team.py:805`, `:961`) plus the Q50 refusal executed in the supervisor immediately before `:961`: resolve as §2.2, sha256(resolved `task_plan.md`) must equal its attestation; MISSING/AMBIGUOUS/MISMATCH → refuse naming `! mise run plan-attest`; no plan at all → allow (spec file carries the task).
- Claude `permissions.deny` does not bind codex; a lane's prohibitions travel in its spec (`codex-sdlc-team.md` blind spot) — the deny list below is Claude-side only, stated as such in `.claude/CLAUDE.md`.
- The doctor probe certifies the Claude dispatcher only (`listing_budget.plugin_root` reads `~/.claude/plugins/cache`, `listing_budget.py:152`); a codex arm through `~/.codex/plugins/cache/…/.codex/hooks/run_sh.py user-prompt-submit.sh` is an optional follow-up (T11).

## 3. One merged workflow (knowledge-base + dotfiles)

KB today: slug mode, `.planning/.active_plan` = `2026-09-12-session-review-round-dag` (live 11 days, `.mode`=`autonomous`, attested), no root plan and no root `.mode`; **no `permissions` block at all in `.claude/settings.json`** (grep for `permissions|"deny"` → 0 hits), no attest task, `kb_setup/codex_lane.py` has 0 `PLANNING_DISABLED` hits, the resume skill hard-codes plugin `3.12.0` (`KB session-resume:139`) and treats the plan as intra-round state under `next-ticket` (`:157-162`); archive = `mv` to `.planning/.archive/<id>` + conditional pointer clear (`plan-archive.md:18-26`).

**Shared code lives in `kb_setup`** — already the SHA-pinned uv git dep dotfiles consumes for `currency`, `cc`, `md-budget` (`python/pyproject.toml:40`; `mise.toml:659,668,1497`). New module `kb_setup/pwf.py` + CLI `kb-setup plan {status,init,close,log,attest,pointer,doctor-probe}` (dispatch is the `if cmd ==` chain, `cli.py:449,536,696`). Both repos add thin mise tasks `plan-status|plan-init|plan-close|plan-log|plan-attest|plan-pointer` calling `uv run --project python kb-setup plan …`; dotfiles' `plan_attest.py`/`plan_pointer.py` become re-exports and are deleted once the pin lands (their tests move). The shared rule text (`.claude/rules/pwf-workflow.md`) rides `rule-sync.toml` (`mise run rule-sync`), the existing cross-repo mechanism.

Per-repo flags live in a `[plan]` section of each repo's `doctor.toml`-style baseline (read by the library, `--config` on the CLI):

| Flag | dotfiles | knowledge-base |
|---|---|---|
| `root_roadmap` | `true` (Ray Q2) | `false` (`docs/direction/` + `next-ticket` are the program record) |
| `pointer_path` | `docs/agents/plan-pointer.json` | none (skipped) |
| `program_record` | `docs/agents/goal-history.md` | `docs/direction/*.md` |
| `ticket_ref` regex | `#\d+` (GitHub) | `next-ticket` id |
| `archive_dir` | `.planning/.archive` | same (KB's today) |
| `handoff_skill` | `/session-handoff` | `/clear-prep` |
| D4 deny set | present | **must be added** (T9) |
| root `.mode` floor | tracked | **must be added** (T9; without it a KB slug's attestation requirement is an agent-chosen flag, #238) |

## 4. Ordered ticket list

| # | Ticket | Files | Closes | Drift | Verification (both arms) |
|---|---|---|---|---|---|
| T1 | **Deny extension.** `_ATTEST_DENY_BASES` += `*init-session.sh`, `*init-session.ps1`, `*set-active-plan.ps1`, `*kb-setup plan attest` (bare + ` *` each, `hook_selfcheck.py:756-762`); explicit `Bash(*plan-close*--force*)`; `Edit(.plan-attestation)`, `Edit(.planning/**/.attestation)`, `Edit(.planning/.active_plan)`, `Edit(.mode)`, `Edit(.planning/**/.mode)` (Edit rules cover Write + `>`/`tee`/`sed -i`, NOT subprocess writes — `permissions.md:334-341`; C5 accepted, the synthesis's Write residual withdrawn); rewrite `.claude/CLAUDE.md:20-22` | `.claude/settings.json`, `hook_selfcheck.py`, `tests/test_plan_attest.py`, `.claude/CLAUDE.md`, `suites.toml:1862-1866` | A-F1 root re-bless; codex §2A `.ps1` gaps | none | live arms in a throwaway repo: `sh …/init-session.sh --autonomous` denied, `echo x > .plan-attestation` denied, `shasum task_plan.md` allowed; presence test `test_the_deny_check_notices_a_half_written_ban` extended per base |
| T2 | **sdlc_team scrub + Q50 refusal** | `sdlc_team.py:805,961`, `tests/test_sdlc_team.py`, `suites.toml` (add the two call sites to `workflow.codex-lane-planning-isolation` per-path tokens) | #1307; codex §2C | none | spawned child prints `PLANNING_DISABLED`; mutation: drop `env=` → fails; refusal arm: tampered fixture → no `Popen`, message names the attest task; control: attested fixture dispatches |
| T3 | **`kb_setup.pwf` library + CLI** (resolve mirror of `resolve-plan-dir.sh:343-368`, status, init, close, log, attest wrapper with target print, pointer, doctor probe) — KB PR, then pin bump in dotfiles `pyproject.toml:40` | KB `python/src/kb_setup/pwf.py`, `cli.py`, KB tests | C1, C2 (diagnostic), C3, C4, C7, codex §2B, change-5 gaps | none (wraps unmodified upstream scripts by resolved plugin root) | throwaway-repo tests for every refusal in §2.2/2.3/2.5; `init` post-state check fails on a forged rc=0; `close` on incomplete plan refused; `log` with 2 live slugs refused |
| T4 | **Reader migration** — pointer schema + `active_phase` rule + `MISSING_ROOT_PLAN`; keep `mise run plan-pointer` line and fence in the handoff skill unchanged (`suites.toml:1707-1730`) | `plan_pointer.py`, `handoff_check.py`, `docs/agents/plan-pointer.json`, `tests/test_plan_pointer.py:22-38`, `tests/test_handoff_check.py:116-127` | A-F2 (with T8), codex C6/E | removes our only divergence | old `NEXT SESSION` fixture now fails; `### Phase` + `**Status:**` fixture passes; ledger-summary and pointer name the same heading on the same file |
| T5 | **mise tasks + deny wiring in both repos** (`plan-*` thin callers; `--force` deny; `main.py` passthrough repair extended to `plan attest`, `main.py:3086-3089`) | `mise.toml`, KB `mise.toml`, `main.py`, `suites.toml` wiring contracts | change 5 | none | `mise run plan-status` rc=0 here; `plan-init` refused with a live slug fixture |
| T6 | **Doctor `pwf-hooks`** (`doctor.py:1323` CHECKS row, `doctor.toml [pwf] enabled`): skip when `PLANNING_DISABLED` in the doctor's own env; run `claude-hook.sh user-prompt-submit` with `CLAUDE_PLUGIN_ROOT`, 10 s timeout, shims dir stripped from child PATH; FAIL only when our resolver says a plan exists and output is empty; findings also for "env `PLAN_ID`/pointer names an archived dir" and ">1 live slug"; side effects (turn marker, pwf-prog marker) documented | `doctor.py`, `doctor.toml`, `tests/test_doctor.py` | Lane B dark hooks; codex §2F | none | canary: live-plan fixture with `PLANNING_DISABLED=1` in the CHILD env → FAIL; same fixture unset → clean; doctor process with `PLANNING_DISABLED=1` → skipped, not FAIL |
| T7 | **Skills + agents** — `/session-handoff`, `/session-resume` (§6), `pwf-scribe.md` ("root findings.md" → resolved plan dir), agent-report-persistence §3 wording, SubagentStart contract tokens in `_SETTINGS_WIRING`; regenerate `.agents/skills/session-*` (`skills_mirror_parity`, `hk.pkl:719-721`) | two SKILL.md + mirrors, `pwf-scribe.md`, `agent-report-persistence.md`, `hook_selfcheck.py:96-111` | change 9; codex gate list | none | `mise run lint` (mirror parity), `mise run lint-docs`, `hook-selfcheck` |
| T8 | **Plan migration** (operator + coordinator, §5) | `task_plan.md`, `.planning/.archive/`, `docs/agents/plan-archive-2026-09-23.md`, `goal-history.md` 032 | A-F2, Lane B F3 | none | `plan-status` root MATCH + Phase 11; ledger-summary names Phase 11; doctor clean |
| T9 | **KB parity** — add the D4 deny set + selfcheck equivalent, tracked root `.mode`, `PLANNING_DISABLED` in `kb_setup/codex_lane.py`, drop the `3.12.0` literal, resume/clear-prep call `kb-setup plan status`, archive via `plan-close`; close or re-attest the 11-day live slug | KB `.claude/settings.json`, `/.mode`, `codex_lane.py`, two skills, `rule-sync.toml` in both repos | codex §2D | none | same arms as T1/T2 in the KB clone; `mise run rule-sync` green in both |
| T10 | **Upstream asks** (optional): plan-doctor times the reference chain not the dispatcher (Lane B F1); `attest-plan.sh --target root`; `init-session.sh --no-root` | issues on `OthmanAdi/planning-with-files` | — | — | — |
| T11 | **KB `conda:coreutils` shim tax** (Lane B F2, `knowledge-base/mise.toml:247`) — KB ticket, out of scope here | — | — | — | — |

Order: T1 and T2 first (security, independent); T3 → pin bump → T4/T5/T6 → T7 → T8; T9 in parallel once T3 lands. T4 must land before T8 or the new root shape fails `handoff-check`.

## 5. Plan migration — seven verifiable outcomes, and iteration 032

1. **Preserve bytes:** copy `task_plan.md` (1,647 lines; re-derive sha at execution, codex read `4dd740b2…`) and `.plan-attestation` to `.planning/.archive/2026-09-23-program/`; move `.planning/2026-09-21-graphify-0-9-65-skill-refresh/` under `.archive/` (no live `task_plan.md`, `.mode`=`autonomous`; no `.active_plan` exists — my Glob of `.planning/**` listed dotfiles and none).
2. **Obligation map:** the agent enumerates every `- [ ]`, every "still open" (`task_plan.md:619` names #986/#997/#995/#985; Phase 2b items `:664-668`; Phase 10 step 0; #1327–#1342) into the tracked extract with one of: roadmap phase line / existing issue # / dropped-with-reason; the coordinator files gaps via `issue-filer`.
3. **Install the roadmap:** ≤150 lines, upstream autonomous template shape, Phases 10 and 11 with `**Status:**` (11 `in_progress`), the pwf addendum condensed to Decisions rows, no `NEXT SESSION` heading.
4. **Iteration 032 — writer: the coordinator (Claude architect session), on the branch, before the first `plan-init`.** Fields per `session_review.py:131-139`; prior digest = 031's `sha256:afd44520…` (`goal-history.md:1525`); goal text changes ("Keep task_plan.md as the sole task authority" → "the root roadmap plus the attested ticket plan are task authority"), so current digest changes; Mermaid workflow; append-only against the `origin/main` merge-base (`:517,538-575`).
5. **Reconcile selection:** no live slug, pointer absent/stale, env `PLAN_ID` unset (verify in the session, §10).
6. `mise run plan-pointer` (new schema) then `! mise run plan-attest` (target printed: root) then `-- --show`.
7. **Verify agreement:** `mise run plan-status` root MATCH, Phase 11; `ledger-summary.sh` in_progress heading == pointer heading; `mise run doctor` clean; next `UserPromptSubmit` injects a body (Lane B F3 ends).

## 6. `/session-handoff` and `/session-resume`

**Handoff:** §0 — "active phase in `task_plan.md`" → "the resolved plan (`mise run plan-status`)"; rulings go to the ticket plan mid-ticket, root only at a boundary; attest owed once per boundary crossed this session (not "never mid-session"). §1 — keep the `mise run plan-pointer` fence verbatim; add a second fence: `mise run plan-status`, `mise run plan-log -- note "handoff <date>"`, `mise run doctor`. §3b — handoff records `plan_id`, both shas, MATCH/MISMATCH, ledger tick; a MISMATCH puts `! mise run plan-attest` in OWED. Checklist adds: "plan-status MATCH or attest explicitly owed", "no second live slug", "completed ticket closed via `plan-close`", "`.agents/skills` mirror regenerated".

**Resume:** §1 — after the handoff, `mise run plan-status`; AMBIGUOUS/stale-pin/dark states are reported before anything else. §3 shape: `PLAN: root → <phase> [MATCH] | ticket <id> → <phase> [MATCH|TAMPERED — owed: ! mise run plan-attest]`. §4 — when TAMPERED the first offer is the attest; when a closed ticket is still referenced by the env pin, the first offer is "new terminal".

KB: `session-resume` §3 and `clear-prep` step 7 call `kb-setup plan status` / `plan-close`; the "surviving plan is a disagreement" logic stays (it is KB's `root_roadmap=false` variant of the same check).

## 7. Not adopted (with the reason, so it reads as considered)

- `/plan-loop`: each tick edits `**Status:**` → tamper (`plan-loop.md:21`). `/plan-goal`: `/goal` is not model-invocable and the default condition is unreachable (inventory §4). Gated mode: always an `in_progress` phase; one forced turn per init; the gate never reads attestation; codex Stop can block. `/pwf`, `/plan`, `start`, raw `init-session`: replaced by `plan-init` (`start` is DMI, correction to round 1). `phase-status.sh`: revisit only with concurrent status writers. Function hook / codex hook for plan-doctor: fail open and silent, false FAIL in lanes (Lane B §4, §6). `PLAN_ID` in `settings.json` env or in the main clone. `plan-init --from`. Rename-archival. Automatic root status flips on close. A shared `.active_plan` as the binding.

## 8. Open questions for Ray (recommendation first)

1. **Archive dir:** `.planning/.archive/` (KB's, hidden = unselectable by construction; recommended) vs round-1's `.planning/archive/`.
2. **`/pwf` literal:** deny the raw script and route creation through `mise run plan-init` (recommended — root-mode `init-session.sh --autonomous` re-blesses, F1 step 2, and no pattern can separate root from slug form) vs keep `/pwf` working and accept the re-bless route.
3. **Q4:** drop `--from`; the per-ticket attest IS the review (recommended).
4. **Q5:** scrub `sdlc_team` + Q50 refusal (recommended) vs share read-only.
5. **Q6:** `plan-close` model-runnable when complete, `--force` operator-only, never writes the pointer (recommended) vs fully operator-only (adds a stop per ticket).
6. **Shared code in `kb_setup` now** (recommended; KB PR + pin bump per change) vs build in dotfiles and lift later.
7. **Goal text change in 032** to name "root roadmap + attested ticket plan" as task authority (recommended).
8. **KB's live 11-day slug:** close it via the new `plan-close` (recommended) or re-attest and keep.

## 9. Consumers, tests, contracts that change

`plan_pointer.py`, `handoff_check.py`, `tests/test_plan_pointer.py`, `tests/test_handoff_check.py`, `tests/test_plan_attest.py`, `tests/test_sdlc_team.py`, `tests/test_doctor.py`, `hook_selfcheck.py` (`_ATTEST_DENY_BASES`, `_SETTINGS_WIRING` tokens), `suites.toml` (`workflow.plan-pointer-wiring`, D4 contract `:1862-1866`, `workflow.codex-lane-planning-isolation` + a new `workflow.pwf-workflow-wiring`), `main.py` (`:1544-1567`, `:2817-2823`, `:3086`), `mise.toml` (`:996-1004`), `.agents/skills/session-{handoff,resume}`, `pwf-scribe.md`, `agent-report-persistence.md` §3, `.claude/CLAUDE.md:20-22`, `doctor.toml`, `docs/agents/plan-pointer.json`, `rule-sync.toml` (both repos), KB: `settings.json`, `/.mode`, `codex_lane.py`, `session-resume`, `clear-prep` + `references/plan-archive.md`, `cli.py`.

## 10. Unverified (name in the tickets)

- Env `PLAN_ID` in the current session, and whether `mise.local.toml [env]` reaches the `claude` process (mise activation exports to the launching shell — standard, unmeasured).
- `Edit()` deny live behaviour on `>` redirection (doc-derived, `permissions.md:341`); a `Skill(planning-with-files:pwf)` deny rule shape.
- Whether KB's `.gitignore` covers a root `.mode` (my grep pattern did not include `mode`).
- Codex hook trust currency: `trusted_hash` rows exist for the 3.20.7 `codex-hooks.json` events but I did not compare them to current file bytes.
- `resolve_from_active_file` falling through on a moved dir is read from source (`:266-283`), not executed.
- Both Graphify orientation queries required by the read hook could not run in this lane.

## GitHub repos touched

- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — installed 3.20.7 Claude and codex plugin source (resolver, init, attest, selector, ledger, check-complete, inject-plan.py, docs, templates, codex hooks).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — settings, python modules, tests, suites.toml, skills, agents, task_plan addendum, goal-history, the five input reports.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `.planning/`, settings, `.codex/`, skills (session-resume, clear-prep, plan-archive), `kb_setup` package, vendored `permissions.md`.
