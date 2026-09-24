> Persisted verbatim by the coordinator at receipt from the subagent transcript (`fable-orchestrator:fable-advisor`, Brief F, session `a6750a24`, 2026-09-23).

# pwf 3.20.7 migration — Fable round 3: FINAL design under upstream's trust model (Brief F)

Persist at `docs/research/kb/reports/agents/pwf-migration-fable-round3-2026-09-23.md`. Base: `pwf-migration-fable-revision-2026-09-23.md`; supersedes its §2.3, §2.5 step 5, §2.7, §3 flag rows "D4 deny set", §4 T1, §8 Q2–Q5.

## 1. Verdict

Adopt upstream's model whole: attestation is a local SHA-256 that detects a changed plan while the digest is trusted, "not a keyed signature or proof of human approval" (`docs/attestation-locking.md:9-13`, `SKILL.md:470`); the orchestrator re-attests at phase boundaries (`MIGRATION.md:188-190`). Everything in this repo that existed to make attestation an operator boundary is retired (table §7); what remains is (a) path resolution upstream leaves to `CLAUDE_PLUGIN_ROOT`, (b) resolver facts (C1–C7) that hold regardless of trust, and (c) the human-review boundary **moved to tracked artifacts** — `docs/agents/plan-pointer.json` (root + ticket digests, committed at every handoff) and `goal-history.md` — which a PR reviews and attestation never could (the plan is gitignored, `.gitignore:143-146`).

Deciding risk: stale memory. MEMORY.md, `.claude/CLAUDE.md:20-22`, `mise.toml:997`, `main.py:1547`, ~20 transcripts and `test_plan_attest.py:1-10` all say "operator-only"; a later session acting on that will re-add the deny from habit. So T1 ships a one-token `regex_forbid` contract that FAILS if `attest-plan.sh` reappears in `permissions.deny` — the reversal's own control arm, not a D4 artifact.

## 2. Target workflow

**Layout** unchanged from revision §2.1: root roadmap `./task_plan.md` (≤150 lines, autonomous template shape) + `./.plan-attestation`; tracked root `.mode = autonomous inject-smart` (the floor every slug inherits, `init-session.sh:170-182,472`); one `.planning/<date>-<slug>/` per `/implement` ticket; `.planning/.archive/<id>/` for closed tickets (hidden ⇒ unscannable, `plan-archive.md:36-37`); tracked `plan-archive-2026-09-23.md`, `goal-history.md`, `plan-pointer.json`.

**Binding (C1, kept):** main clone carries no `PLAN_ID`; at most one live slug there, so `.active_plan` and newest-mtime agree by construction. Parallel tickets run in worktrees with `PLAN_ID` exported — exactly what init prints (`init-session.sh:476-477`) and upstream #50 prescribes. Enforcement is **detection, not denial**: `plan-status` and the doctor report ">1 live slug" and "env `PLAN_ID` names an archived dir".

**Create (upstream literal):** `/pwf` and `init-session.sh "<title>"` work as shipped. ⚠️ `/pwf`'s body creates ROOT files first and only then chooses `--autonomous` (`pwf.md:7-12`); with root files present that is the root-mode branch (`:481-485`) which re-attests root — harmless now, but not what a ticket wants. The documented route is therefore `mise run plan-init -- "<ticket title>"`: a thin exec of `sh <resolved root>/scripts/init-session.sh "<title>"` (slug mode; auto-attested template, `:226-230`), printing `PLAN_ID=` and `plan-status`; `--pin` appends `[env] PLAN_ID` to the worktree's gitignored `mise.local.toml`. No refusal logic, no deny. The agent then fills the plan (3–7 phases, one `in_progress`) and **runs `mise run plan-attest` itself** — the tamper gate is re-armed on the agent's own bytes, which is upstream's autonomous-mode contract (`SKILL.md:483`).

**Root edits (C2, kept):** `attest-plan.sh` reaches root only when no slug resolves (*inherited*: `attest-plan.sh:44-56,73-76`; `set-active-plan.sh` has no `--clear`, `:3,303-308`). Root is edited after `plan-close` and before the next `plan-init`, then `mise run plan-attest` (target printed: root). No operator involvement.

**Who attests when:** the orchestrator (the Claude architect session), immediately after each intentional edit — post-fill, post-boundary root edit, and at `/session-handoff`. Workers never attest; that prohibition travels in the lane spec (`codex-sdlc-team.md` "blind spot"), and a worker that edits the plan "would break the hash by design" (`MIGRATION.md:189-190`) — surfacing as MISMATCH at the orchestrator's next status, which is the tamper signal doing its job. `attest-plan.sh` direct is also fine; the wrapper exists because `CLAUDE_PLUGIN_ROOT` is unset in an agent's Bash and the cache path is version-pinned (`plan_attest.py:22-25,51-54`), plus the `--show` argparse fix (`:86-133`).

**Close (C3/C7, kept):** `mise run plan-close -- <id>` model-runnable: resolve == id; `check-complete.sh` prints ALL PHASES COMPLETE or `--force`; `ledger-append.sh phase_complete`; `mv` to `.planning/.archive/<id>`; never touch `.active_plan` (stale pointer ⇒ root, `set-active-plan.sh:321`); drop the mise.local pin and warn about the live shell; print the parent-phase reminder. `--force` is **model-runnable** but the skill requires an `AskUserQuestion` first — judgment under `clarify-before-acting.md`, not a permission.

**Status/pointer (C6, kept):** phase = first `### Phase` followed by `**Status:** in_progress` (the rule `ledger-summary.sh:114-137` and `check-complete.sh:95-97` use — *inherited*); pointer schema `{root:{sha,phase}, ticket:{id,sha,phase}|null}`; `MISSING_ROOT_PLAN` when root is absent (`handoff_check.py:217-219` returns `[]` today — *inherited*).

**Codex parity:** interactive codex uses the globally enabled pwf codex plugin, 7 trusted hooks (*inherited*: `~/.codex/config.toml:257-258,499-518`); same `.planning/`, `.active_plan`, `PLAN_ID`. Lanes: see §4. Doctor probe = Lane B option B, FAIL-only, SessionStart, dispatcher variant (`pwf-plan-doctor-hooks:275-296,314-319`); reaches interactive codex via the existing `.codex/hooks.json:35-45` doctor mirror; no new hook of either kind.

## 3. Operator's remaining stops

1. `AskUserQuestion` on genuine ambiguity or irreversibility: `plan-close --force` on an incomplete ticket; any obligation marked dropped-with-reason in the migration extract; the 032 goal-text wording (an accepted goal change, `goal-history.md` rule).
2. User-invoked protocol verbs: `/to-spec`, `/to-tickets`, `/implement`, `/triage`, `/grill-with-docs`.
3. Codex `/hooks` trust after a pwf upgrade (#1334/#1336) — this design adds none.
4. Plugin upgrades (operator installs; `plugin-health`), and `/clear` after handoff.
5. PR review — where the roadmap's digest and phase (`plan-pointer.json`) and goal changes (`goal-history.md`) are actually read by a human.

Not a stop: attestation, plan creation, closing a complete ticket, `plan-log`, `plan-status`.

## 4. sdlc_team: split now vs Phase 10 (Ray's question)

Today `sdlc_team.py` passes no `env=` at either `Popen` (`:805`, `:961`), so lanes already inherit the session env and **already see the plan** — round 5 needs no code to take effect; it needs a guard so it is not "fixed" back (Phase 10's own step-5 text still says `PLANNING_DISABLED=1 for sdlc_team (+ test)`, `task_plan.md:415-418`, and inventory §7.6 recommends the same).

**Now (this migration, one small ticket, T6):**
- `regex_forbid` contract: no `PLANNING_DISABLED` in `sdlc_team.py`; a test that a spawned child inherits `PLAN_ID` when set (positive) and lacks `PLANNING_DISABLED` (control).
- Pre-dispatch check at `:805`: resolve the plan as the shell resolver would; if v3 mode and sha256(`task_plan.md`) ≠ attestation (MISSING/MISMATCH), refuse and name `mise run plan-attest` — which the orchestrator can now run in the same turn. Closes the blind-lane defect (`PLAN TAMPERED` in lanes 09-18/09-21, attest-history §5) without auto-blessing at dispatch, which would silently defeat tamper detection.
- Supersede Phase 10 step 5's `PWF_PLAN_ROOT` in settings `env` (an absolute path in a tracked file breaks worktrees), the scrub, and the lint forbidding `.planning/*/task_plan.md`/`.active_plan` — record the supersession in the Phase 10 rulings block.

**Phase 10 (unchanged):** RESEARCH mode, role-typed model, `codex exec review`, one-entry-point consolidation, retirement of `codex_lane` and its scrub plus the `workflow.codex-lane-planning-isolation` contract (`suites.toml:1868-1899`) and the `PLANNING_DISABLED=1 codex exec` prose in `.claude/agents/codex-sol-*.md`. Rationale: T6 is ≤50 lines around the two spawn sites, and Phase 10 keeps `sdlc_team` as THE codex entry point, so it is not thrown away; everything larger takes its shape from Phase 10's design. `codex_lane` keeps its scrub until then (round 5 names sdlc_team only; codex_lane is advisory, not a worker).

## 5. Ordered tickets

| # | Ticket | Files | Closes | Drift | Verification |
|---|---|---|---|---|---|
| T1 | **Retire D4.** Delete the 11 deny rules (`settings.json:31-41`); delete `_ATTEST_DENY_BASES`/`check_plan_attest_deny` and the `:811` registration; delete `workflow.plan-attest-operator-only` (`suites.toml:1831-1866`); delete deny tests (`test_plan_attest.py:81-126`), keep resolver + passthrough tests; rewrite `.claude/CLAUDE.md:20-22`, `mise.toml:997`, `main.py:1547`, `plan_attest.py` docstring; add `workflow.plan-attest-model-runnable` (`regex_forbid` `attest-plan` in settings deny + `require_tokens` on the new CLAUDE.md sentence) | as listed | round-4 ruling; inventory F1 becomes non-defect | none (matches `attestation-locking.md`) | live: model runs `mise run plan-attest -- --show` → rc 0 (control: `cat ~/.netrc` still denied); `hook-selfcheck` green without the arm; mutation: re-add one deny rule → contract fails |
| T2 | **`kb_setup.pwf` + `kb-setup plan {status,init,close,log,attest,pointer,doctor-probe}`** (KB PR, then pin bump `pyproject.toml:40` — *inherited*); `plugin_root` resolver moves or is mirrored (verify KB lacks one) | KB `python/src/kb_setup/pwf.py`, `cli.py`, tests | C1 diag, C2 diag, C3, C4 print, C7, codex §2B | none — wraps unmodified upstream scripts | throwaway-repo tests: close refuses incomplete; log refuses ambiguous; attest prints target; init prints PLAN_ID; status names stale pin/pointer/archived-dir |
| T3 | **Reader migration** — pointer schema, `active_phase` rule, `MISSING_ROOT_PLAN`; keep the `mise run plan-pointer` fence token (`suites.toml:1707-1730` — *inherited*) | `plan_pointer.py`, `handoff_check.py`, `plan-pointer.json`, both tests | C6, codex E | removes our only divergence | old `NEXT SESSION` fixture fails; `### Phase`+`**Status:**` passes |
| T4 | **mise tasks both repos** (`plan-status/init/close/log/attest/pointer` → `kb-setup plan …`); `dotfiles-setup plan-attest` becomes a re-export until deleted | `mise.toml`, KB `mise.toml`, `main.py:1544-1550,2817,3086-3089` | codex change 5 | none | `mise run plan-status` rc 0 here; passthrough `-- --show` still reaches the script |
| T5 | **Doctor `pwf-hooks`** per Lane B option B + live-slug/stale-pin findings | `doctor.py`, `doctor.toml`, `test_doctor.py` | Lane B dark hooks; codex §2F | none | canary: `PLANNING_DISABLED=1` in the CHILD → FAIL; unset → clean; doctor's own env disabled → skipped |
| T6 | **sdlc_team minimal** (§4) | `sdlc_team.py:805`, `test_sdlc_team.py`, `suites.toml` | blind lanes; round 5 durability | none | tampered fixture → no `Popen`, message names the task; attested → dispatches; child env probe both arms |
| T7 | **Skills/rules/agents** (§6) + `pwf-scribe.md`, `agent-report-persistence.md` §3 wording, `_SETTINGS_WIRING` tokens, `.claude/rules/pwf-workflow.md` via `rule-sync.toml`; regenerate `.agents/skills` | as listed | codex change 9, gate list | none | `mise run lint` (mirror parity), `lint-docs`, `rule-sync`, `hook-selfcheck` |
| T8 | **Plan migration** — the revision's seven outcomes, now with **no operator step**: coordinator archives bytes, writes the obligation map, installs the roadmap, appends 032 (goal text: "the root roadmap plus the attested ticket plan are task authority; attestation is tamper detection (upstream #150); the orchestrator attests at phase boundaries"), runs `plan-pointer`, `plan-attest`, `plan-status`, `doctor` | `task_plan.md`, `.planning/.archive/`, `plan-archive-2026-09-23.md`, `goal-history.md` | A-F2, Lane B F3 | none | root MATCH + Phase 11; ledger heading == pointer heading; next prompt injects a body |
| T9 | **KB parity** — root `.mode` floor (KB `.gitignore` does not ignore `.mode`: grep matched only `statusline-mode` at `:203`, so it will track); drop the `3.12.0` literal; resume/clear-prep call `kb-setup plan status`/`plan-close`; close the 11-day slug via `plan-close` after confirming the round is done (round 5). **No deny set** | KB settings untouched, `/.mode`, two skills, `rule-sync.toml` both | codex §2D | none | `rule-sync` green both repos; `kb-setup plan status` on KB |
| T10 | **Upstream asks** (file, not block): `attest-plan.sh --target root`; a Claude/Codex analogue of Pi `/plan-execute` (the only way an approval boundary returns upstream-first, tracker review §Implications) | OthmanAdi issues | — | — | — |

Order: T1 → T2 → pin bump → T3/T4/T5/T6 → T7 → T8; T9 after T2. T3 before T8 (new root shape vs `handoff-check`).

## 6. `/session-handoff` and `/session-resume`

**Handoff:** §1 fence keeps `mise run plan-pointer` verbatim; add `mise run plan-status`; if MISMATCH **and this session edited the plan** → `mise run plan-attest` (target printed) then re-status; if MISMATCH and it did not → a finding ("plan changed outside this session"), reported, **not** attested — this is the one place tamper detection still pays. Then `mise run plan-log -- note "handoff <date> <session-id>"`, `mise run plan-pointer` (both digests), `mise run doctor`. Checklist: both MATCH, ≤1 live slug, completed ticket closed. OWED never contains an attest; the memory-index note flips "operator-only" → "model-runnable" at this handoff.

**Resume:** after the handoff, `mise run plan-status`, then a three-way compare — file sha vs attestation vs committed pointer: all equal → clean; file ≠ attestation → "unattested edit after handoff" (classify agent-owned; first offer is `mise run plan-attest`, clickable as the command); attestation ≠ pointer → "re-attested after the pointer was committed" → disagreement, fix-first (Phase 11 Q1/Q8). `PLAN:` line: `root → <phase> [MATCH] | ticket <id> → <phase> [MATCH|TAMPERED]`. Stale env pin → first offer "new terminal".

## 7. Retired-items table

| Item | Disposition |
|---|---|
| D4 deny rules `settings.json:31-41` (attest/set-active-plan/task/CLI) | **Retired.** `set-active-plan.sh` deny also removed (collateral: it denied a `sed -n` read, inventory §2b) |
| Revision T1 deny extension (`init-session.*`, `Edit(.plan-attestation)`, `Edit(.active_plan)`, `Edit(.mode)`, `plan-close --force`) | **Dropped, never built** |
| `plan_attest.py` wrapper | **Kept, non-D4 reasons:** plugin-root resolution + `insert_passthrough_separator` (#1051); docstring rewritten; migrates to `kb_setup.pwf attest` |
| `hook_selfcheck.py:756-762,765-794,811` | **Retired** (presence check of a boundary that no longer exists) |
| `suites.toml:1831-1866` | **Retired; replaced** by `workflow.plan-attest-model-runnable` + `workflow.pwf-workflow-wiring` |
| `.claude/CLAUDE.md:20-22`, `mise.toml:997`, `main.py:1547` | **Replaced** by the §2 posture text |
| `plan-init` as a deny route | **Dropped**; `plan-init` survives only as path-resolving convenience, `/pwf` allowed |
| `--force` operator-only | **Replaced** by model-runnable + mandatory `AskUserQuestion` |
| `--from` rejection | **Moot** — the agent writes and attests the ticket plan directly (upstream literal) |
| Operator stops 1–3 (revision §2.7) | **Retired**; become orchestrator steps |
| Q50 refusal in `sdlc_team` | **Kept, re-derived** as blind-lane prevention (§4), not a boundary |
| `codex_lane` scrub + its contract | **Kept until Phase 10 retires the lane** |
| C2 root-while-slug diagnostic, one-live-slug detection, `.archive/` close, root `.mode` floor, doctor probe | **Kept** (resolver facts, upstream #238 behaviour) |

## 8. Not adopted

Unchanged from revision §7 (`/plan-loop`, `/plan-goal`, gated mode, `phase-status.sh` now, function/codex hooks for plan-doctor, `PLAN_ID` in settings env, rename-archival, automatic root status flips). Added: any Claude-side approval gate for attestation (T10 asks upstream instead); auto-attest at dispatch or in any hook (would make tamper detection a no-op).

## 9. Open questions (recommendation first)

1. `codex_lane` scrub: leave until Phase 10 retires it (recommended) vs drop now for symmetry with round 5.
2. `plan-init` wrapper: keep as thin exec + `--pin` (recommended; upstream lacks only path resolution) vs none (skill documents the raw path).
3. Pre-dispatch check placement: dispatch site `:805` (recommended, fixable in-turn) vs supervisor `:961` (fresher, later).

## 10. Unverified

No shell: graphify queries, `pytest`, and every live deny/allow arm; `~/.codex/config.toml` pwf block, `resolve-plan-dir.sh`, `attest-plan.sh`, `ledger-*.sh`, `check-complete.sh`, `handoff_check.py:217`, `pyproject.toml:40` line cites are inherited from the revision/codex verdict; whether `kb_setup` already has a plugin-root resolver; that `mise.local.toml [env]` reaches a `claude` launched from that shell.

## GitHub repos touched

- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — 3.20.7 `init-session.sh`, `set-active-plan.sh`, `commands/pwf.md`, `commands/plan-attest.md`, `MIGRATION.md`, `docs/attestation-locking.md`, `SKILL.md`; tracker #50/#150/#190/#193/#202/#238 via the review report.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — `task_plan.md`, `.claude/settings.json`, `.codex/hooks.json`, `.gitignore`, `plan_attest.py`, `hook_selfcheck.py`, `sdlc_team.py`, `codex_lane.py`, `suites.toml`, `test_plan_attest.py`, the six input reports.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `.gitignore`, `clear-prep/references/plan-archive.md`.
