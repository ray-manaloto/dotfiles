<!-- verbatim SubagentHandback of premise-verifier afe482f8f0481c9c4, coordinator 5a11da, 2026-10-04 -->

PREMISE REPORT — re-verification of two revised specs (04h). Baseline: worktree `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-04h` at 13af2848. This lane was read-only and wrote nothing. The coordinator persists this report.

Neither spec is ready to dispatch yet. Both need a fix to the base-commit pin. Spec B also needs one more token rule.

**A finding that applies to both specs: origin/main has moved past the base.**
- `.git/refs/remotes/origin/main:1` now reads `f1b1b0e70624…`.
- `.git/logs/refs/remotes/origin/main:215` records `13af2848 → f1b1b0e7 "fetch -q origin: fast-forward"`.
- Local `refs/heads/main:1` is still `13af2848`.
- So Spec A rows 1-2 and Spec B P1 ("origin/main = 13af2848") are no longer true. Both specs say to cut the branch "from 13af2848 or later". "Later" now means f1b1b0e7, and I could not read what it changes: there is no shell, and the commit subject is in no ref or log.

========================================================================
## SPEC A — spec-jobdir-part2-dispatch-gate.md

ROWS: 54 checked (rows 1-55, with row 9 retired) — 46 CONFIRMED (0 provenance corrected) / 2 REFUTED (rows 1-2, stale because origin/main moved; row 25's parenthetical is also stale but the row is not refuted) / 0 UNVERIFIABLE / 4 ASSUMED (rows 5, 6, 43, 44; row 5 is now settled by the ratification's merge-base rc=0 / reverse rc=1)

Revision-log rows:
- **R2 (rows 1-3) — partly REFUTED.**
  - Row 1 still holds: local main = 13af2848.
  - Row 2 is REFUTED. Decisive line: `.git/refs/remotes/origin/main:1` = `f1b1b0e70624755ee2993484a1a853fb425d4dc1`.
  - Row 3 is CONFIRMED: `.git/worktrees/handoff-2026-10-04h/HEAD:1` = `ref: refs/heads/docs/handoff-2026-10-04h`.
- **R3 / row 4 — CONFIRMED.** `sdlc_team.py:819-822` has the comment plus `"--color", "never"`; `dispatch` is at `:723`.
- **R4 / row 17 — CONFIRMED.** argv is at `:811-828`, the try is at `:830-865`, `except OSError` is at `:866-878`, prompt write `:833`, unlink `:834`, Popen `:852`, DISPATCHED `:880-891`.
- **R5 / row 21 — CONFIRMED.** Test `:1651-1673` fakes neither boundary. `sdlc_team_main` is at `:1093-1110`, and `:1110` returns 0 only for DISPATCHED. `main.py:3056-3058` passes `--repo-root project_root`, so S5's repo_root is `tmp_path`.
- **R6 / row 23 — CONFIRMED.** `:1698-1714` is a parsed-JSON equality test; `generate_dispatch_schema` is at `:1067-1069`.
- **R7 / row 14 — CONFIRMED.** There are 0 hits for `SPEC_UNCOMMITTED|spec_uncommitted|spec_commit`. The control matches exactly 7 lines: `sdlc_team.py:60,:748`, `schemas/sdlc-team-dispatch.json:85`, both `SKILL.md:75`, `tests/test_sdlc_team.py:340,:1671`.
- **R8 / rows 7-8 — CONFIRMED.** `:1067`, `:1093`; tests `:171`, `:185`, `:270`, `:412-416`, `:1706`.
- **R10 / rows 47-48 — CONFIRMED.**
  - `child_env.py:36-45` (the six names) and `:71-74` (`without_git_context` = `without_env_diff` minus GIT_CONTEXT_NAMES). It reads `os.environ` at call time (`:67`), so an emptied PATH survives. It imports only `os` and `re` (`:30-31`).
  - Precedents: `pr.py:244,:259`, `session_state.py:120`, `doctor.py:1524,:1656`, `sync.py:414,:436`, `pr_facts.py:53`.
- **R11 / row 49 — CONFIRMED.** `session_common.py:186-192` uses `text=True`. `sdlc_team_main:1107` catches `(OSError, ValueError, TypeError)`, so a bytes→Path `TypeError` would be turned into INVALID_REQUEST rather than escape. The typing rule matters for that reason too.
- **R1 / rows 45-46 — CONFIRMED.** The only catch around the supervisor launch is `except OSError` (`:866`). `sdlc_team_main` does not catch `AssertionError`, so S5 under M8 fails by assertion.
- **Row 52 / R19 — CONFIRMED.**
  - Popen patches are at `:133` (supervisor harness), `:202`, `:337`, `:367`, `:402`, `:434` (lambda), `:466` (lambda) and `:1614`.
  - `SdlcTeamRequest.mode` defaults to REVIEW (`sdlc_team.py:69`), so every `_request(tmp_path)` caller is review mode.
  - `:337` (SPEC_MISSING) and `:367` (CLI_MISSING under review) are unaffected.
- **Row 55 / R23 (uniqueness claim) — CONFIRMED.**
  - `token_audit.count_tokens` (`:351-354`) and `find_ambiguous` (`:358-367`) read only `per_path_tokens`. `find_violations` (`:389-407`) fails any count ≠ 1 that is not allowlisted.
  - `AMBIGUITY_ALLOWED` (`:87-287`) has no sdlc entry.
  - hk `contract_token_uniqueness` is at `hk.pkl:393-395`, inside `allSteps` (`:34`), and runs in `["check"]` (`:848-850`).
  - In suites.toml, `sdlc` appears only at `:2427/:2434` (the `.claude/CLAUDE.md` trigger-line suite) and `:3046-3052`. The latter is `regex_forbid 'PLANNING_DISABLED|LANE_ENV_OVERRIDES'` on `sdlc_team.py`, confirmed at `:3050-3052`.
  - No `per_path_tokens` entry binds any §2 file. That includes the schema and both SKILL.md files.
- **Row 53 / R20 — CONFIRMED.** `python/AGENTS.md` § "Generated models and enums" says models are "generated, never hand-written". `sdlc_team.py:56-98` holds hand-written `codec.Struct` models.
- **Row 54 — CONFIRMED.** The worktree index contains `sdlc-team-review-jobdir-artifacts-29a5dcc4.md` and `specs-2026-10-04d/spec-jobdir-preservation.md`. A freshly invented name returns 0.
- **Row 15 — CONFIRMED.** `\bgit\b|subprocess\.run` returns 0 hits in `sdlc_team.py`. The control is `session_common.py:186-187`.
- **Row 25 — CONFIRMED on substance** (`subprocess.py:512,:554` `with Popen(*popenargs, **kwargs)`). **But the parenthetical "the 04h worktree has no `.venv`" is now false:** `…/handoff-2026-10-04h/python/.venv/pyvenv.cfg:1` exists, with home = the same cpython-3.14 dir. Not blocking.
- **Rows 10-13, 16, 18-20, 22, 24, 26-27, 31-33, 51 — CONFIRMED** as cited.
  - `SKILL.md:37-48` is an implement-mode example with `/absolute/path/to/spec.md`.
  - `:51` is the "must be absolute and exist" sentence; `:72-77` is the status list.
- **Rows 5 and 6 — ASSUMED.** Row 5 is now settled on the record by the ratification (merge-base rc=0, reverse rc=1). Row 6 is not checkable and does not affect code.
- **Rows 43 and 44 — ASSUMED.** Code does not contradict either. Both are settled by design and by the equality test.

MISSING:
- **Base pin (load-bearing).** "Cut from 13af2848 or later" now resolves to f1b1b0e7, whose diff I could not read. The coordinator should either cut from exactly 13af2848, or first run `git diff --stat 13af2848 f1b1b0e7 -- python/src/dotfiles_setup/sdlc_team.py tests/test_sdlc_team.py schemas/sdlc-team-dispatch.json .claude/skills/codex-sdlc-team .agents/skills/codex-sdlc-team python/verification/suites.toml` and confirm it is empty.
- **ruff return ceiling (non-blocking).**
  - `dispatch` has 5 returns today (`:739, :753, :767, :878, :891`). The gate adds a 6th, which sits exactly at ruff's default PLR0911 ceiling (6; fails at >6). Any second new return trips it.
  - `_spec_commit_error` as described (5 checks + success + the git-unavailable path) will likely exceed 6 returns, so the lane must split it.
  - §4 already lets the lane run `ruff check`, so it will see this. It is not stated in the spec.
- **Fixture git under an inherited GIT_DIR (non-blocking).** F2's own `git init/add/commit` runs without a scrub, and conftest (`tests/conftest.py:27-49`) does not clear GIT_DIR. That is safe under the pre-push suite, because `mise.toml:314` runs it via `process git-isolated`. A manual run from a hook-exported shell would aim the fixture at the real repo. Same exposure as precedent `tests/test_worktree_guard.py`.

VERDICT: **FIX SPEC FIRST** — one line. Replace "13af2848 or later" (§2, §6) with "13af2848, or later only after `git diff --stat 13af2848 <origin/main> -- <§2 paths>` is empty". Once that is pinned, Spec A is ready, with these named residuals:
- the stale `.venv` parenthetical (cosmetic);
- the ruff return ceiling (the lane's ruff run catches it);
- F2 under GIT_DIR (pre-push isolates it);
- rows 6, 43 and 44 (no code effect, or settled by test).

========================================================================
## SPEC B — spec-dag-tick-pr1.md

ROWS: 59 checked (P1-P55, A1-A4) — 54 CONFIRMED / 1 REFUTED (P1, origin/main moved; P18's no-.venv parenthetical is also stale but the row is not refuted) / 0 UNVERIFIABLE / 4 ASSUMED (A1 plain; A2, A3, A4 checkable)

Revision-log rows:
- **(a) / P1, P46 — P1 REFUTED, P46 CONFIRMED.**
  - P1 fails on `.git/refs/remotes/origin/main:1` = `f1b1b0e7…`. The reflog `:214` record (`ee3b29da→13af2848`) is real, but `:215` moved origin/main again.
  - P46: the index holds `sdlc-team-review-dag-tick-aba49c5d.md` and `specs-2026-10-04d/spec-dag-tick-safety.md`. An invented name returns 0.
- **(b) / P49 — CONFIRMED.**
  - `suites.toml:2628` is the name. `:2630` contains "the CAS and all ten reap outcomes".
  - `:2638` binds `'fcntl.flock(handle.fileno(), fcntl.LOCK_EX)'`, `'gate = lane_is_settled if is_settled is None else is_settled'`, `'if not gate(run_dir):'` and `'result = codex_verdict.reap('` (dag_tick.py), plus both keyword lines.
  - The proposed replacement `'… LOCK_EX | fcntl.LOCK_NB)'` cannot contain the old `LOCK_EX)` token, as the spec says.
  - `'ReapOutcome.LOCK_BUSY: Edge.NONE'` matches only the OUTCOME_EDGES row. A `ReapResult(ReapOutcome.LOCK_BUSY, Edge.NONE, …)` construction uses a comma, not a colon, so it does not count against the token.
- **(c) / N1 / P48 / constraint 9 — mechanism CONFIRMED, enumeration INCOMPLETE** (see MISSING).
  - `token_audit.py:351-354` uses `text.count(token)`; `:389-407` fails ≠1 unless allowlisted. `AMBIGUITY_ALLOWED` (`:87-287`) has no `dag_tick.py`/`codex_verdict.py` entry.
  - The hk step at `hk.pkl:393-395` is in `allSteps`, and `["check"]` (`:848-850`) spreads `allSteps`.
- **(d) / P51 — CONFIRMED.** `tests/test_dag_tick.py:2438-2454` uses `_fake_popen` with `popen_calls == [["claude","respawn","dead1"]]` (claude_bin "claude", `_ctx` `:118`). The dry-run test `:2418-2435` has a DEAD node (`:2422-2423`) and a raising `_fail_popen` (`:2426-2431`).
- **(e) — CONFIRMED.**
  - `session_common.py:38` `_SESSION_ID_RE` needs 8+ characters; `:41` is the coordinator regex `^dotfiles-.+\.coordinator$`.
  - `_read_launch_state` (`coordinator_handoff.py:263-279`) re-raises `StateUnreadableError` when no started receipt exists, so the "unreadable" cell is reachable.
  - With only a receipt present, it injects `launch_pending` = receipt (`:275-276`), so the "receipt only" cell reads as launched via `_started_pending` (`:251-255`).
- **(f) / P54, P55 — CONFIRMED.** `LAUNCH_TIMEOUT_S = 60` (`:87`); `launch_pending = {"name","at"}` (`:923`); the `--state-dir` default is `main_checkout(Path.cwd()) / STATE_SUBDIR` (`:1267`); `STATE_SUBDIR` is at `:108`.
- **(g) / N2 — CONFIRMED.** Stale text sits at `dag_tick.py:102-115`, `:1171`, `:1193`, `:1203-1213`, `:1222-1234` and `:1236-1239`. "already-running" appears at `:510`, `:680`, `:688`, `:1269`. No test or python file outside `dag_tick.py` pins any of those strings (grep over tests/ and python/).
- **N3 / P20, P53 — CONFIRMED.** `main_checkout` (`session_common.py:183-203`) passes no `env=` and has `timeout=MAIN_CHECKOUT_TIMEOUT_S` (30, `:32`).
- **N4 — CONFIRMED.** The details at `codex_verdict.py:476-497`, `:512-534` and `:551-575` interpolate `VERDICT_FILENAME`/`LANE_FILENAME`, the owner and the status, but never `run_dir`.
- **D6-A (ratified) — CONFIRMED feasible.**
  - Indented at 8 spaces, `reaper = codex_verdict.preview if ctx.dry_run else codex_verdict.reap` is 77 characters. That is under `line-length = 88` (`pyproject.toml:68`), so ruff format will not wrap and break the token.
  - The `seams=codex_verdict.ReapSeams(lock_timeout_s=ctx.reap_lock_timeout_s),` line at 12 spaces is 83 characters.
  - The single call keeps `expected_owner=classified.node_id,` and `max_rework=ctx.max_rework,` unique.
- **D3-A — CONFIRMED.** `is_settled=` appears only at `tests/test_codex_verdict.py:499,:517` (grep over tests/ and python/src). No other test passes it. The `cv.reap` calls in `test_codex_lane.py`/`_e2e.py` use only the 4 current keywords.
- **Constraint-9 token `if is_needs_human(fresh.state, fresh.needs, queued_prompt=fresh.queued_prompt):` — CONFIRMED once at `dag_tick.py:1248`.** A sharper hazard than the spec states: if the split helper names its parameter `node`, the line becomes the `classify()` token `'if is_needs_human(node.state, node.needs, queued_prompt=node.queued_prompt):'`. That token then counts 2, and the `fresh` token drops to 0. The spec's "keep the variable name `fresh`" covers this.
- **P2, P3, P9-P17, P19, P21-P45, P50, P52 — CONFIRMED** as cited. Spot checks:
  - `TickContext` has 10 fields (`:360-382`); `build_tick_context` is at `:1372-1392`.
  - `test_build_tick_context_*` (`:2296-2324`) assert individual fields, not object equality, so a new field cannot break them.
  - No other `TickContext(` exists in python/src besides `:1381`.
  - The import closure has no `dag_tick` (importers are only `codex_lane.py:82`, `dag_project.py:72`, `main.py:50`; `reap.py` imports nothing from `dotfiles_setup`).
  - `test_codex_lane.py:504-540` exercises `prepare_lane` only, never `reap`.
- **P18 — CONFIRMED on substance.** `subprocess.py:129` `class SubprocessError`, `:169` `class TimeoutExpired(SubprocessError)`, `:554-573` POSIX kill-then-wait. The "04h worktree has no `.venv`" parenthetical is now false: `python/.venv/pyvenv.cfg` exists, with the same home.
- **A1 — ASSUMED.** Not settleable from code.
- **A2 — ASSUMED (checkable).** Nothing in the repo contradicts ruff's default `max-returns = 6`. It was not read in the ruff source.
- **A3 — ASSUMED (checkable).** The stdlib source supports it.
- **A4 — ASSUMED (checkable).** It holds for PR 1; `mise.toml:1565` was not re-read here.

MISSING:
- **(load-bearing) Constraint 9 says "This binds three suites". It misses test-file bindings that the V-a/V-b/V-d test edits can break.**
  - `workflow.classifier-axis-enforcement` (`suites.toml:2619`) binds `tests/test_dag_tick.py` to `'from dotfiles_setup import classifier_tables, codex_verdict, dag_tick'` (today at `tests/test_dag_tick.py:37`). It also binds `'_AXIS_VALUES: dict['`, `'expected_cells = set(itertools.product(*_AXIS_VALUES.values()))'`, etc.
  - The same suite binds `tests/test_codex_verdict.py` to `'from dotfiles_setup import classifier_tables'` (`:24`).
  - Ruff's isort ordering makes the hazard concrete. Adding `child_env` (which V-a3's "the names `child_env.GIT_CONTEXT_NAMES` lists" invites) or `coordinator_handoff` to line 37's import gives `from dotfiles_setup import child_env, classifier_tables, …` or `… codex_verdict, coordinator_handoff, dag_tick`. The token's count then goes to 0, and both `mise run verify` (presence) and `mise run lint` (uniqueness) fail. Appending `session_common` is harmless.
  - `workflow.dag-tick-wiring` (`:1974`) also binds 40 test function names in `tests/test_dag_tick.py`, which constraint 9 does not mention.
  - The lane runs no gates, so it cannot see any of this.
  - Fix: add a bullet to constraint 9: "`workflow.classifier-axis-enforcement` and `workflow.dag-tick-wiring` bind test-file tokens. Keep `tests/test_dag_tick.py:37` and `tests/test_codex_verdict.py:24` import lines byte-identical; add any new `dotfiles_setup` import on a separate `from dotfiles_setup import …` line, and spell V-a3's six names as literals. Do not reuse or redefine any bound test name or `_AXIS_VALUES`."
- **Base pin (load-bearing, same as Spec A).** It matters more here: the §3(d) token-edit table is written against `suites.toml:2638` at 13af2848. If f1b1b0e7 touched that line, the table is stale. Use the same correction: cut from 13af2848 exactly, or diff `suites.toml`, `dag_tick.py`, `codex_verdict.py`, `main.py` and both test files first.
- **(non-blocking) Constraint 9's codex_verdict.py list omits some bound tokens.** It names "the schema/parse tokens" loosely but leaves out `'is not Edge.ADVANCE'`, `'def edge_for('`, `'def demands_rework('` and `'def parse_verdict('` (`suites.toml:2638`). All must also stay exactly once. The risk is low because no planned code writes them.
- **(non-blocking) Stale prose outside the allowlist.** `python/src/dotfiles_setup/codex_lane.py:6` says the reaper "maps ten outcomes onto edges". It is not a token, and `codex_lane.py` is outside §2. List it for the PR body or a follow-up.
- **(non-blocking) A test's real git call.** `test_build_tick_context_defaults_claude_bin_and_cwd` (`:2317-2324`) will now trigger a real `git worktree list` through D1's `main_checkout`. It has no field assertion on `handoff_state_dir`, so it stays green. It is the only existing test that gains a real git call (P52).

VERDICT: **FIX SPEC FIRST.** Two corrections:
1. Add the classifier-axis-enforcement / dag-tick-wiring test-file token bullet above to constraint 9.
2. Replace "13af2848 or later" in the header and §6 with the pinned base, or with the diff check, as in Spec A.

After those, these residuals remain named and non-blocking:
- A1, A2, A3, A4;
- the incomplete codex_verdict token list;
- the `codex_lane.py:6` stale prose;
- the stale `.venv` parenthetical.

## GitHub repos touched
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — local reads only. In the 04h worktree: both specs, `sdlc_team.py`, `child_env.py`, `session_common.py`, `coordinator_handoff.py`, `codex_verdict.py`, `dag_tick.py`, `main.py`, `token_audit.py`, `hk.pkl`, `suites.toml`, `pyproject.toml`, `mise.toml`, tests (`test_sdlc_team`, `test_dag_tick`, `test_codex_verdict`, `test_codex_lane`, `conftest`), `SKILL.md`, `python/.venv/pyvenv.cfg`. In the main checkout's `.git`: refs, the origin/main reflog, and the worktree index. Also the uv CPython 3.14 `subprocess.py`.
