# Research: restructure task_plan.md into planning-with-files' NATIVE layout (2026-09-29)

Lane: read-only research (writes only this report + `.agent/kb/raw/pwf-native-*.md`).
Brief: Ray's ruling 2026-09-29 — adopt pwf's native plan template (Goal / Next Step / Current Phase /
`### Phase N` + `- **Status:**`, driven by `phase-status.sh`) instead of the custom `NEXT SESSION` token
read by `handoff_check.active_phase`. Status: COMPLETE (2026-09-29).

## Q1 Prior decisions

**Yes — this was already decided, on 2026-09-23, and published as spec #1351 plus 18 tickets.** Ray's 2026-09-29
ruling mostly re-states that design. There is one real divergence, covered under (e) below.

(a) **Layout (decided).** #1351 § Layout: "The root plan is the roadmap: at most 150 lines, upstream's autonomous
template shape with primary status markers, exactly one phase in progress, no 'next session' heading. Edited only
at rulings and phase boundaries. Gitignored, as today." Per-ticket plans go under `.planning/<date>-<slug>/` via
upstream `init-session.sh` in slug mode. Closed plans go to `.planning/.archive/`
(raw: `.agent/kb/raw/pwf-native-issue-1351.md` lines 38-43, 251-252; task_plan.md:612-617, 628-629).

(b) **Canonical phase rule (decided, #1354 D3).** #1351: "the first phase heading whose following primary status
marker says in progress. That is the format upstream's completion check and ledger summary agree on; inline
bracketed status tokens or more than one phase in progress produce the non-canonical-markup warning. The 'next
session' heading convention is retired" (raw 1351 lines 333-336). #1354: "The 'next session' heading convention is
retired from every reader". Its acceptance arm: "a fixture using the old 'next session' heading now fails; a
canonical primary-marker fixture passes" (`.agent/kb/raw/pwf-native-issue-1354.md`).

(c) **Plan migration (decided, #1360 D9).** Seven outcomes: archive the program plan and its attestation
byte-for-byte; extract every unchecked item into a tracked extract with a mapping (each drop is asked); install the
≤150-line roadmap; append a goal-history iteration; reconcile selection; attest; verify, including that the next
prompt injects a plan body. It is blocked by #1354-#1359 ("readers must accept the new shape") and closes #910
(`.agent/kb/raw/pwf-native-issue-1360.md`).

(d) **Trust model (Ruling round 4, task_plan.md:651-661).** Adopt upstream's trust model. Agents are trusted plan
writers. Attestation is tamper detection only. The orchestrator re-attests at phase boundaries (pwf
`MIGRATION.md:188-190`). D4 and the operator-only attest posture are retired (#1352 D1). `.claude/CLAUDE.md` already
reflects this: "Attestation is agent-runnable (Ray, 2026-09-26)".

(e) **DIVERGENCE: `phase-status.sh` was explicitly OUT of scope.** #1351 § Out of Scope: "Adopting the plugin's
plan-loop or plan-goal commands, gated mode, session isolation, **the phase-status script**, or any Claude-side
approval gate …" (raw 1351 line 519). Ray's 2026-09-29 ruling names `phase-status.sh` as the driver. That conflicts
with the ratified spec, so it must be re-asked with the conflict named (per `feedback_clarify_before_acting`: "A user
ruling conflicting with a protocol ⇒ re-ask NAMING the conflict").

(f) **Later amendment that changes the ticket set.** On 2026-09-28c Ray ruled to DELETE the plan pointer, done in PR
#1437. The comment on #1351 (2026-09-29T04:14:22Z) says "Drift detection is now native pwf: handoff-check asks the
installed plugin (`attest-plan.sh --show`) … Finding: `unattested_plan`". The comment on #1354 says "What remains
here: the canonical active-phase rule replacing the `NEXT SESSION` heading convention, and the `plan-attest` →
shared verb cutover." The two-authority pointer and M-7 are void. So #1354's remaining dotfiles scope is small: the
phase rule plus the attest cutover.

(g) **Assumptions the 2026-09-23 decisions rested on** (these are re-verified in Q2):
1. The plugin is 3.20.7 and its `init-session.sh` slug mode, `PLAN_ID`, `.active_plan` hint and `.planning/.archive`
   invisibility behave as described (resolution order: env binding → live pointer → single live slug → root).
2. Upstream's completion check (`check-complete`) and ledger summary both read `### Phase N` +
   `- **Status:** in_progress` ("primary status marker").
3. The injection hook injects the plan body with a `## Current Phase` prefix, capped at 10,000 chars (S27-13 found
   42/65 injections at 19.4-19.9 KB, task_plan.md:1189). A short roadmap fixes #910 and S27-13.
4. Attestation is not a keyed signature (upstream #150 @ v3.16.1).
5. Upstream's autonomous template is the target shape.
6. `attest-plan.sh` has no `--target` (asked upstream in OthmanAdi/planning-with-files#296).
7. `PWF_PLAN_ROOT` is NOT to be set in settings env (task_plan.md:429); `PLANNING_DISABLED` is used only by the
   advisory `codex_lane` (round 6).

(h) **Current code state.** `handoff_check.py:43` still has
`_ACTIVE_HEADING = re.compile(r"(?im)^##\s+(?P<heading>[^\n]*NEXT SESSION[^\n]*)\s*$")`, and `active_phase`
(`:278-279`) is documented as "Return the last level-two heading containing `NEXT SESSION`". #1354's phase-rule half
has not landed. All of #1351-#1360 are OPEN (`gh issue view`, 2026-09-29).

(i) **Session history (AgentsView).** Probes ran with `--exclude-session dcb0b106-…`, the current session. Without
that flag, the first run returned only this session's own echoes.

- Control arm: `"planning-with-files"` returns hits, so the archive is reachable.
- Negative arm: `"roadmap at most 150 lines"` returns 0. Treat it as a phrasing miss, not an absence: the same fact
  hits under `"autonomous template shape"`.

Decisive hits, all Ray's own prompts (role=user) in the 2026-09-23/24 migration sessions:

- `a6750a24-770a-419d-996e-985bd27de611` `#311 @311`, and the same brief replayed in codex
  `01a0d2a0-e40f-7491-808f-832b473f1643` `#319 @319`. The design was: "`task_plan.md`: the program roadmap, ≤150 lines,
  upstream's autonomous template shape (Goal / Next Step / Current Phase / `### Phase N` blocks …". The
  2026-09-29 ruling is therefore a RE-statement of that design, not a new one.
- codex `01a0d2a0…` `#136 @136`: "`phase-status.sh` | Later; each call still breaks the attestation". And `#154 @154` /
  `#208 @208`: "`phase-status.sh`: revisit only if concurrent Status writers appear".

**Why `phase-status.sh` was deferred.** `pwf-skills-inventory-2026-09-23.md:93` says: "The only lock-safe writer of a
phase `Status:` … **ADAPT later, SKIP now.** Useful only once status lines are back in sync (F2). Each call still
costs an attest". Both premises have since moved:

1. Attest is agent-runnable since 2026-09-26, per `.claude/CLAUDE.md`, so "costs an attest" no longer means "costs
   Ray".
2. "Status lines back in sync" is exactly what the native restructure delivers.

The deferral reason is therefore largely dissolved, but #1351 still lists the script as out of scope. Re-ask with the
conflict named.

## Q2 Current plugin vs assumptions

**Versions.**

- Latest upstream is `v3.21.0`, published 2026-09-27T02:43:41Z
  (`gh api repos/OthmanAdi/planning-with-files/releases`). Before it: v3.20.8 (2026-09-25), v3.20.7 (2026-09-23),
  v3.20.6, v3.20.5.
- The local cache holds 3.17.2 through 3.21.0.
- ⚠️ **The dotfiles install RECORD is stale at 3.17.2.** `~/.claude/plugins/installed_plugins.json` has two
  project-scope entries: knowledge-base → 3.21.0 (lastUpdated 2026-09-27), and **dotfiles → 3.17.2** (lastUpdated
  2026-09-13). `claude plugin list` (rc=0) shows the same pair: `Version: 3.21.0 Scope: project` and
  `Version: 3.17.2 Scope: project`, both enabled.
- The repo resolves the plugin differently. `plan_attest` → `listing_budget.plugin_root` picks the **highest version
  dir** (3.21.0), and says it deliberately ignores `installed_plugins.json` (`listing_budget.py:122-147`).
- Which version this session's hooks actually load is **UNPROVEN**:
  - `hooks/hooks.json` and `hooks/claude-hook.sh` are byte-identical between 3.17.2 and 3.21.0 (`diff` rc=0), so hook
    TEXT cannot discriminate.
  - `inject-plan.py` differs only in symlinked-plan-dir rejection (#270).
  - `attest-plan.sh` differs in `--target`.
  - No transcript records a resolved `CLAUDE_PLUGIN_ROOT`. The only "Base directory for this skill" hit for pwf is
    an old 3.12.0.

  So "task_plan.md:429 — the plugin is already 3.20.7" was true of the cache, not provably of the dotfiles install
  record.
- **Fix:** update the dotfiles project-scope install to 3.21.0 through the native plugin CLI. This is an operator
  action. Verify afterwards with `claude plugin list` showing a single 3.21.0 for dotfiles.

**Changes since the 2026-09-23 decisions (3.20.7 → 3.21.0).** Raw source:
`.agent/kb/raw/pwf-native-changelog-3.20.7-3.21.0.md`.

- **3.21.0: `attest-plan.sh --target root|<plan-id>` SHIPPED** (#296, PR #297). This is OUR upstream ask. The #1351
  constraint "re-attest the root plan only with no slug plan selected" (task_plan.md:606-610) is **lifted**. Attest
  writes now print the resolved plan and hash-file paths first. Empty or trailing targets are rejected. #1351's
  "attest prints the target the resolver chose" is now native.
- **3.20.8:** the Stop check is silent when no plan exists (#288). The rest is Cursor/Gemini/PowerShell fixes, not
  relevant to Claude/Codex on macOS.
- **3.21.0 inject/resolver:** a symlinked plan dir is never selectable (#270).

**Assumptions from Q1(g), re-verified against 3.21.0 source:**

| # | Assumption | Verdict | Evidence |
|---|---|---|---|
| 1 | Resolution: `PWF_PLAN_ROOT` pin → `PLAN_ID` binding → `.active_plan` → single live slug → root; >1 live slug without `PLAN_ID` = ambiguous | **HOLDS** | See the resolver note below this table |
| 2 | Completion check and phase-status read `### Phase N` + first `**Status:**` in the block | **HOLDS** | `phase-status.sh:86-120`: `^### Phase N` then rewrites the first `**Status:**`; allowlist `pending\|in_progress\|complete` |
| 3 | Smart injection extracts Goal / Next Step / Current Phase / the in-progress phase | **HOLDS** | README:643 `PWF_INJECT=smart`: "goal, next step, current phase, the full in-progress phase, and the last three decisions". Root `.mode` is already `autonomous inject-smart` (tracked) |
| 4 | Attestation = tamper detection, not approval | **HOLDS** | Unchanged; template: "Re-attest after an intentional edit so hooks can inject the approved version" (`templates/task_plan_autonomous.md` § Runtime Behavior) |
| 5 | Autonomous template is the target shape | **HOLDS** | `skills/planning-with-files/templates/task_plan_autonomous.md`: `## Runtime Behavior`, `## Goal`, `## Next Step`, `## Current Phase` (body "Phase 1"), `## Phases` with 3-7 `### Phase N: …` blocks each ending `- **Status:** …`, then `## Key Questions`, `## Decisions Made`, `## Errors Encountered`, `## Notes` |
| 6 | No `--target` on attest | **REFUTED (now fixed upstream)** | 3.21.0 CHANGELOG |
| 7 | Env posture (no `PWF_PLAN_ROOT` in settings; `PLANNING_DISABLED` only for `codex_lane`) | **HOLDS** (see Q3) | `codex_lane.py:135` |

Resolver note (row 1): `resolve-plan-dir.sh:27-38, 315-370`. `PLAN_ID` is a binding (#237) and `PWF_PLAN_ROOT` fails
closed (#212). ⚠️ The header comment at `:7` still says "Newest … by mtime". The code counts live slugs and exits
empty on >1 (#240), so the comment is stale and the code is authoritative.

**Live measurement of the CURRENT plan against the native readers (3.21.0, run in this repo, read-only):**

- `resolve-plan-dir.sh` → empty (root). `--check-ambiguity` → no marker. Both `.planning/2026-09-2*` dirs hold only
  `task_plan.archived.md`, so they are not live. `attest-plan.sh --show` rc=0 → `./task_plan.md`, `./.plan-attestation`.
- `check-complete.sh` rc=0 reports "**2/20 phases complete** … **2 phase(s) still in progress** … 3 pending". The
  custom plan has 19 `### Phase` headings but only 8 `**Status:**` markers. Upstream therefore already reads it as
  non-canonical: more than one phase is in progress, and most phases have no status.
- `inject-plan.py smart_plan_extract(task_plan.md)` → **47,199 bytes**. The plan is 2,333 lines and 188,140 bytes,
  and its first `## Goal` is the SUPERSEDED 2026-09-09 program. Smart injection is on, but the plan's shape defeats
  it: the view is 4.7× the 10,000-char hook cap (S27-13, task_plan.md:1189). This is the measured harm the native
  restructure removes.

## Q3 Settings + env vars

**What upstream 3.21.0 reads.**

Method: grep of `scripts/*.sh|*.py` and `hooks/*.sh` for `${PWF_*|PLAN*}` and `os.environ`, then a cross-check against
README:632-647. Raw source: `.agent/kb/raw/pwf-native-readme-envvars.md`.

| Var | Since | Documented meaning | This repo sets it? | Verdict |
|---|---|---|---|---|
| `PLANNING_DISABLED=1` | v3.4.0 | "Skips all plan reading for this invocation" (README:639) | `codex_lane.LANE_ENV_OVERRIDES = {"PLANNING_DISABLED": "1"}` (`codex_lane.py:135`); the 12 `.claude/agents/codex-*.md` wrappers each carry `PLANNING_DISABLED=1` (grep: 2 hits per file) | Still read upstream. Kept by ruling: round 6 for `codex_lane`, and round 7(4) for the wrappers "until the codex class fix". `sdlc_team` correctly does NOT set it (round 5). The `sdlc_team.py` grep shows no inherited-`PLANNING_DISABLED` warn yet, which is #1357 and still open. |
| `PLAN_ID` | v2.x | A per-thread binding. A non-empty bad value fails closed (#237, `resolve-plan-dir.sh:315-340`) | Not set anywhere, which is correct | #1351: per worktree only, via the pin in `mise.local.toml`. Never in settings or the main clone. |
| `PWF_PLAN_ROOT` | v3.9.0 | Absolute plan-root pin for shared-parent cwds (README:641) | Not set | Correct. task_plan.md:429 retired the "add it to settings env" idea. ⚠️ `phase-status.sh` refuses to fall back to `./task_plan.md` when `PLAN_ID` or `PWF_PLAN_ROOT` is set, so a stale pin blocks status writes (`phase-status.sh` `resolve_plan_file`). |
| `PWF_INJECT=smart` | v3.8.0 | Structure-aware injection (README:643) | Equivalent `.mode` token `inject-smart` in TRACKED root `.mode` = `autonomous inject-smart` (`git ls-files .mode` → tracked; `inject-plan.sh` `mode_has 'inject-smart'`) | Already on. Its value is currently defeated by the plan's shape (Q2). |
| `PWF_SESSION_ID` | v2.36.0 | Session isolation, active only if `.planning/sessions/` exists (README:642) | Not set; no `.planning/sessions/` | Correct. #1351 does not adopt it. |
| `PWF_PLAN_GUARD=0` | v3.10.0 | Disables the parallel-write guard (default ON) (README:645) | Not set | Leave the default ON. |
| `PWF_FAST_PATH=0` | v3.17.0 | Forces the shell chain instead of `inject-plan.py` (README:644) | Not set | Leave the default. |
| `PWF_GATE_CAP` | v3.0.0 | Stop-gate cap, gated mode only (README:647) | Not set | N/A. The mode is autonomous, not gated. |
| `PWF_PYTHON`, `PWF_TRUSTED_PYTHON`, `PWF_ROOT_PIN`, `PWF_SHELL_PWD` | — | Undocumented. All are internal: assigned inside the scripts (e.g. `PWF_ROOT_PIN=""` at the top of scripts) or only in the Python twin | Not set | Internal; do not set. |
| `PWF_MODE` | v2.39.0 | Pi extension only (README:646) | — | N/A |

**Repo surfaces checked.**

- `.claude/settings.json`:
  - The `env` block has no pwf variable. Its keys are `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`,
    `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD`, `…FUNCTION_HOOKS`, `…AGENT_TEAMS`, `…MAX_*SUBAGENT*`,
    `…TASK_LIST_ID` and `OTEL_LOG_RAW_API_BODIES`.
  - `enabledPlugins."planning-with-files@planning-with-files": true` (`:193`).
  - The marketplace is `github OthmanAdi/planning-with-files` with no ref pin (`:238-242`), so `claude plugin update`
    takes the latest.
- `mise.toml` / `.config/mise/conf.d/*.toml`: no pwf variable. The grep matched only `codex_lane.py` in the python
  tree.
- `.codex/config.toml` / `.codex/hooks.json` (repo): no pwf references.
- User `~/.codex/config.toml`:
  - `[plugins."planning-with-files@planning-with-files"] enabled = true`.
  - The codex plugin cache holds **3.21.0**.
  - `trusted_hash` entries exist for all 7 codex pwf hook events: pre_tool_use, permission_request, post_tool_use,
    pre_compact, session_start, user_prompt_submit, stop.
  - Whether those hashes match 3.21.0's `codex-hooks.json` is exactly what the #1356 fail-only `pwf-hooks` doctor
    probe is for. It is NOT verified here, because codex's hash recipe was not reproduced.

**Gaps.**

1. The dotfiles Claude install record is at 3.17.2. That is the one real currency gap (Q2). It is an operator
   action.
2. Nothing is set that upstream no longer reads. Every variable the repo sets, `PLANNING_DISABLED`, is still
   honoured.
3. No env var is REQUIRED for the native layout. It needs the tracked `.mode` (already `autonomous inject-smart`) plus
   a plan in the template shape. The `inject-smart` token makes `PWF_INJECT` redundant, so do not add it to settings.
4. Optional, and decided against in #1351: `PLAN_ID` pins per worktree. That is not needed for a root-only roadmap.

## Q4 Native restructure: what it needs

**Scope choice.** There are two ways to do this.

- **(A) Root-only now.** Restructure only the root `task_plan.md` into the template. Keep `.planning/<slug>/`
  per-ticket plans for later (#1353/#1355/#1357, which need the `kb_setup` shared verbs).
- **(B) The full #1351.** The root roadmap plus per-ticket slug plans through shared `kb-setup plan` verbs, blocked on
  knowledge-base K1-K9.

S29-0 as worded (task_plan.md:992-995) is achievable as (A). (A) is also forward-compatible with (B): the roadmap
shape is identical, and per-ticket plans only add `.planning/<slug>/` beside it. Recommend (A) as a carved-out slice
of #1354 + #1360, and ask Ray to confirm, because it re-orders the ratified ticket DAG. #1360 is "Blocked by" #1354-#1359.

**Target shape.** This is upstream `skills/planning-with-files/templates/task_plan_autonomous.md`, verbatim headings:

- `# Task Plan: …`
- `## Runtime Behavior` (template text, kept)
- `## Goal`: one sentence
- `## Next Step`: one action
- `## Current Phase`: `Phase N`
- `## Phases`, containing 3-7 `### Phase N: <title>` blocks, each with checkboxes and a final
  `- **Status:** pending|in_progress|complete`. Exactly one is `in_progress`.
- `## Key Questions`
- `## Decisions Made`: a table. Smart injection surfaces its last 3 rows.
- `## Errors Encountered`
- `## Notes`

The #1351 budget is ≤150 lines. The binding criterion is that the smart view fits the 10,000-char hook cap:
`smart_plan_extract` keeps only Goal, Next Step, Current Phase, the `in_progress` phase block, and the last 3 decision
rows (`inject-plan.sh:1000-1050`, `inject-plan.py:686-705`). Candidate phases are Phase 11 (pwf migration and the
rest), Phase 10, Phase 9, Phase 8, plus a "carried/queued" phase that points at issues. The S29-* order becomes the
checkboxes of the in-progress phase.

**What happens to the 2,333-line program text.** Following round 1 Q3 (task_plan.md:628-629) and #1360 outcomes 1-2:

- Archive it byte-for-byte to gitignored `.planning/.archive/`. The resolver never scans hidden dirs.
- Move the two dead slug dirs (`.planning/2026-09-21-*`, `.planning/2026-09-24-*`, each holding only
  `task_plan.archived.md`) to the same place.
- Extract every unchecked item into a TRACKED `docs/agents/plan-archive-2026-09-29.md`, one row each, mapped to a
  roadmap line, an issue, or dropped-with-reason. Every drop is asked.
- Control count: the unchecked items in the archive equal the extract's rows.

**Consumers that break or change.** Found by `git grep` over `python tests .claude/skills .claude/rules suites.toml hk*.pkl
mise.toml .claude/agents docs/agents`. Control: the same grep finds `task_plan.md` at `suites.toml:1873`, so the probe
can see those files.

| Consumer | Today | Change |
|---|---|---|
| `handoff_check.py:43` `_ACTIVE_HEADING`, `:278-297` `active_phase`, `MISSING_ACTIVE_PLAN` (`:115`) | Last `##` heading containing `NEXT SESSION`. A plan without one → `missing_active_plan`, rc≠0 | Canonical rule (#1354): the first `### Phase` under `## Phases` whose first `**Status:**` is `in_progress`. Warn on >1 in progress or on inline `[in_progress]` tokens. **Must land BEFORE the plan rewrite**, or `/session-handoff`'s final gate (SKILL.md:281-298) fails. Use expand/contract: first accept both, then drop `NEXT SESSION`. |
| `tests/test_handoff_check.py:117-138` | Fixtures write `## Phase N — NEXT SESSION` | Rewrite to canonical fixtures. Add the #1354 arm "old heading now FAILS". |
| `.claude/skills/session-resume/SKILL.md:79,91` | "Read the active phase heading directly from `task_plan.md`" → `PLAN: task_plan.md → <active phase heading>` | Read `## Current Phase` plus the in-progress `### Phase` block. Optionally quote upstream `check-complete.sh`'s "N/M phases complete" line as the native cross-check. |
| `.claude/skills/session-handoff/SKILL.md:19-22, 281-298` | "inspect the active phase"; the final gate is attest + `handoff-check` | Phase-boundary edits. If ruled, flip status with `phase-status.sh <N> <status>` and then re-attest. Keep the rule "rulings go in `task_plan.md` only", but put them in `## Decisions Made` rows and phase checkboxes rather than prose sections. |
| `plan_attest.py` (resolves the highest cache dir → 3.21.0) | `attest-plan.sh` with no target | Optionally pass `--target root` (native since 3.21.0) to make the root explicit, which removes the #296 constraint at task_plan.md:606-610. Arm both sides: with a live slug plan, `--target root` still writes `./.plan-attestation`. |
| pwf `UserPromptSubmit` smart injection (`.mode` = `autonomous inject-smart`) | Keeps the old `## Goal` (the 2026-09-09 program) + `## Next Step` + the 300-line `## Current Phase`, then counts phases from the ARCHIVE's `## Phases` (task_plan.md:1311) → 47,199 B | The template shape brings the view under the cap. **This is the verification arm**, with the 47,199 B control. |
| `docs/agents/goal-history.md` (43 iterations; last is 2026-09-29 dcb0b106) | — | Append the #1360 outcome-4 iteration: authority = root roadmap, attestation = tamper detection. The wording is asked. |
| `suites.toml` / hk | No contract binds `NEXT SESSION` or `active_phase` (0 hits; control above) | Add one contract: the handoff-check reader uses the canonical rule. Pick its tokens with `mise run token-check`. |
| `hook_selfcheck.py:541,676`; `suites.toml:1873` ("coordinator ONLY" row) | File-role contract | Unchanged. The `task_plan.md` path is the same. |
| `doc_refs.py:133` allowed-absent `task_plan.md` | — | Unchanged |

**Not affected:** the pwf hooks and resolver (root stays the resolved plan), `codex_lane`'s `PLANNING_DISABLED`, and
KB (KB has no root roadmap per #1351's no-root profile).

## Recommendation

Ordered **research → spec → tickets → implement**. Each step is ask-first where it changes a ratified ruling.

0. **Operator (Ray), before anything else: bring the dotfiles install to latest.**
   Run `claude plugin update planning-with-files@planning-with-files --scope project` from the dotfiles clone, then
   restart. Verify that `claude plugin list` shows a single dotfiles 3.21.0 entry and that
   `installed_plugins.json` dotfiles `version` is 3.21.0. The control is today's 3.17.2 record. Nothing else is
   needed for settings or env: no pwf env var is missing, and none that is set is dead (Q3).

1. **Re-ask, naming the conflicts, via AskUserQuestion.**
   - (a) `phase-status.sh` is listed OUT of scope in #1351, and Ray's 2026-09-29 wording makes it the driver.
     Recommend adopting it: its deferral premise ("each call costs an attest") dissolved when attest became
     agent-runnable on 2026-09-26. Scope it to coordinator-only use at phase boundaries, each followed by
     `mise run plan-attest`.
   - (b) Carve root-only slice (A) out of #1354 + #1360 ahead of the blocked tickets #1353/#1355-#1359. Recommended.
   - (c) Drop the #296 "no slug selected" constraint, now that `--target root` ships in 3.21.0.

2. **Spec.** Post it as an amendment comment on #1351, or as a slim spec
   `docs/specs/pwf-native-root-roadmap.md` linked from #1354/#1360. It names:
   - the target template (headings above);
   - the canonical phase rule;
   - the expand/contract order;
   - the archive + extract recipe;
   - the goal-history iteration;
   - verification arms:
     - smart view < 10,000 B, control 47,199 B;
     - `check-complete.sh` reports exactly 1 in progress, control "2 phase(s) still in progress";
     - `handoff-check` rc=0 on the new plan and rc=1 on a `NEXT SESSION`-only fixture;
     - `attest-plan.sh --show` → `./task_plan.md`;
     - the next prompt injects the new `# Task Plan:` title.

3. **Tickets**, in dependency order:
   - **T1 (reader, expand; #1354 subset).** `handoff_check` accepts the canonical rule, and still the old token during
     the transition. `session-resume` reads `## Current Phase`. Tests and the contract. Gates: lint, pytest, verify,
     lint-docs, hook-selfcheck.
   - **T2 (migration; #1360 subset).** Archive plus the dead slug dirs to `.planning/.archive/`. Write the tracked
     extract, with each drop asked. Write the ≤150-line roadmap from the template. Append goal-history.
     `mise run plan-attest`. Run the verification arms. This is an orchestrator edit; codex lanes must not write
     `task_plan.md`.
   - **T3 (contract).** Drop `NEXT SESSION` from the reader. The old-heading fixture now fails (mutation arm).
   - **T4 (only if 1a is ruled yes).** `/session-handoff` flips phase status via `phase-status.sh` and re-attests.
     Add a doc line in the skill.
   - The rest of #1351 (per-ticket `.planning/<slug>/`, shared `kb-setup plan` verbs, D5 doctor, D6 refusal matrix)
     continues on its existing tickets, unchanged in shape.

4. **Implement** through the `codex-sdlc-team` doctrine. T2 is coordinator-authored because it edits the
   coordinator-only `task_plan.md`. T1 and T3 go to a codex implementer with an Opus cold review.

## GitHub repos touched

- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files): releases v3.20.4-v3.21.0 via
  `gh api`; #296 state (CLOSED 2026-09-27); the 3.17.2/3.20.7/3.21.0 plugin source read from the local cache (CHANGELOG,
  README env table, `resolve-plan-dir.sh`, `phase-status.sh`, `inject-plan.{sh,py}`, `check-complete.sh`,
  `attest-plan.sh`, the `task_plan_autonomous.md` template, `hooks/*`).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): issues #1351-#1360 bodies and comments, plus
  repo source.
