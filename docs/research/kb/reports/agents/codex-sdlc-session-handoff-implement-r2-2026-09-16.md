# codex SDLC team — Phase 7 IMPLEMENTATION run, ROUND 2 (2026-09-16), verbatim

Brief: `mise run sdlc-team` implement mode, run `phase7-session-handoff-implement-r2-20260916`, effort xhigh, 3600 s ceiling, round-1 allowlist + `.agents/skills/`, `COMMIT: caller`; the round-2 spec (gate reds R1-R8, team findings F1-F4, cold-review items C1-C12) is appended below. Settlement line in the architect dispositions at the tail. Output copied verbatim at receipt.

---

Outcome: **partial failure, blocked by the session sandbox**. Round-2 implementation is complete, but the tree cannot be declared gate-green because `.agents/skills/` is read-only even to the full-access implementer.

Key results:

| Check | rc | Result |
|---|---:|---|
| Typos | 0 | Passed |
| Python type check | 0 | Supplemental run passed |
| Skills mirror check | 1 | Three expected drifts; generator cannot write mirror |
| Document references | 0 | Passed after staging intended new files |
| Targeted pytest | 0 | 438 passed |
| `mise run verify` | 0 | 157 passed, 0 failed, 4 skipped |
| `mise run lint-docs` | 0 | No issues found |
| Full pytest | 1 | 761 passed; sandbox denied `ps` (`rc=127`) |
| `mise run lint` | 2 | Sandbox blocked required state/cache paths before a source verdict |
| `git diff --check` | 0 | Clean |

The canonical `mise run skills-mirror` failed with `PermissionError` on `.agents/skills/session-handoff/SKILL.md`. Both the config specialist and the added full-access implementer reproduced this. No generated files were hand-edited.

All 13 new allowlisted artifacts were staged explicitly. Five unrelated research reports remain untracked and unstaged. Existing modified files remain uncommitted. No commit or push occurred.

To finish outside this sandbox:

```bash
mise run skills-mirror
mise run lint
uv run --project python pytest tests/ -x -q
```

Then rerun the complete eight-command matrix from the round-2 spec. The implementation findings R1–R8, F1–F4, and C1–C12 are addressed, but final closure awaits those unrestricted gates.

No other specialists were spawned.

### Specialists spawned:

- `sdlc-python-specialist` — `/root/phase7_r2_python`
- `sdlc-config-specialist` — `/root/phase7_r2_config`
- `sdlc-documentation-specialist` — `/root/phase7_r2_docs`
- `codex-astra-implementer` — `/root/phase7_r2_mirror_unblock`


---

## Appendix — the round-2 spec (verbatim)

# Spec — Phase 7 IMPLEMENTATION, ROUND 2 (2026-09-16): make the tree gate-green and close the confirmed review findings

Repo: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`, branch `feat/phase7-session-handoff-sdlc-review`, base `3d03ea8`.
Mode: **IMPLEMENT**, `COMMIT: caller`. This is a corrected spec for the SAME uncommitted tree your round-1 run produced (`.agent/sdlc-runs/phase7-session-handoff-implement-20260916/output.md`); the round-1 spec is `docs/research/kb/reports/agents/codex-sdlc-session-handoff-implement-2026-09-16.md` (appendix) and still binds everything not restated here.

## 1. Objective
The architect ran every gate outside the sandbox and an Opus cold review on your tree. Fix EXACTLY the items below so `mise run lint`, the full pytest, `mise run verify` and `mise run lint-docs` are all rc=0, and the confirmed review findings are closed. Do not widen scope; do not touch files outside the round-1 allowlist.

## 2. Gate reds (architect-measured; logs under the architect's scratchpad, verbatim lines quoted)

R1 `typos` (rc=2): `python/src/dotfiles_setup/hook_guard.py:163` and `python/src/dotfiles_setup/session_orphans.py:15` — the regex fragment `(?:ba|z|da)?sh` reads as the word `ba`. Rewrite as an explicit alternation `(?:bash|zsh|dash|sh)` (keep behaviour; the shared regex stays ONE definition imported by `agentsview_pass.py`). No `typos.toml` allowlist entry.

R2 `fix_smart_quotes`: `.claude/skills/session-review/SKILL.md:99` has curly quotes (`“It would be nicer”`). ASCII quotes only.

R3 `py_ty`: `tests/test_plan_pointer.py:45` — `capsys` is annotated as `object`; annotate `capsys: pytest.CaptureFixture[str]`.

R4 `contract_token_uniqueness` + `mise run verify` `workflow.goal-history`: `.claude/skills/session-review/SKILL.md` must contain, verbatim, `validate the entire`, `fixed `origin/main` merge-base`, and `docs/agents/goal-history.md` — each EXACTLY ONCE (the uniqueness step rejects 0× and >1×). Restore the goal-history judgment paragraph (it is judgment, not mechanics — it belongs in the skill). Keep the skill ≤ 150 lines.

R5 `contract_token_uniqueness` `workflow.mise-tasks-enforcement`: `hook_guard.py` now has `_inert_masked(command)` at lines 181, 186 and 811; the contract binds that token to ONE site. Keep the single call at ~811 (`target = _inert_masked(command)`) and have the wait-loop helpers take the ALREADY-MASKED text (e.g. `def is_unbounded_wait_loop(masked: str) -> bool`), with `agentsview_pass.py` masking via a shared helper whose name is not that token. Add no `AMBIGUITY_ALLOWED` entry.

R6 `skills_mirror_parity`: `skills-mirror DRIFT: session-handoff / session-resume / session-review` and `STALE PER_FILE: session-review`. Run `mise run skills-mirror` (the generator; `python/src/dotfiles_setup/skills_mirror.py`) and include the regenerated `.agents/skills/**` output in the tree; then `uv run --project python dotfiles-setup skills-mirror --check` must be rc=0.

R7 `doc_refs` (fails `mise run lint` AND `tests/test_doc_refs.py::test_real_tree_has_zero_unresolved_refs`): `.claude/rules/persistence-gate-retry.md:60` and `:67` cite `tests/<file>.py::<test>` in prose; the checker treats the whole token as a path. Cite the file in backticks and the test name separately (`tests/test_bash_budget.py`, test `test_cli_wires_end_to_end`). Do not add `_ALLOWED_ABSENT` entries.

R8 `renovate_config_validate` failed inside `mise run lint` but `uv run --project python dotfiles-setup renovate-validate` passes alone (rc=0, "RE2 engine confirmed live") — treat as transient; if it recurs in your `mise run lint`, report it as SANDBOX/transient with the log, do not change `renovate.json`.

## 3. Confirmed review findings (architect re-read each cited line)

F1 HIGH `session_ledger.py` `_claude_attachment_event` (~2755): an UNKNOWN attachment type carrying `path`/`image_url`/`file_url` is classified `file_like` and bypasses unknown-blocking. Only `file|image|document` may be file_like; any other type with a payload key is unknown → grouped omission, parser-blocking. Add the fail arm: a fixture row `{"type":"future_shape_zzq","path":"/x"}` → one grouped omission, rc=1.

F2 HIGH `agentsview_pass.py:147-166` `_session_ids`: the census works on real data (architect measured 2 sessions selected) but the selection is fragile: it accepts rows with EMPTY provider/project metadata and the daemon applies `--limit` BEFORE any client-side filter. Use the daemon's native filters instead of path comparison: `agentsview session list --agent claude --project <repo_root.name> --limit <N> --json` (both flags measured on `session list --help` 2026-09-16), then verify each returned row's `agent == "claude"` and `project == repo_root.name`, rejecting rows missing either (an `AgentsViewError`, never silently included). Keep `--session` overrides.

F3 MEDIUM `session_orphans.py:139-166`: with `--kill` and an unallowed OTHER, WAIT-LOOPs are not reaped. Ratified design: reap WAIT-LOOPs regardless, THEN exit 1 for the blocking OTHER. Reorder: reap first (when `--kill`), then block. Test both arms.

F4 MEDIUM `python/verification/suites.toml` `workflow.session-orphans-wiring`: extend (or add a sibling `workflow.bounded-wait-wiring`) so the contract also binds `[tasks.bounded-wait]` + `dotfiles-setup bounded-wait'` in `mise.toml`, `"bounded-wait": lambda: sys.exit(` in `main.py`, `def main(` in `bounded_wait.py`, the guard rule name `"unbounded wait loop"` in `hook_guard.py`, and the skill/rule lines naming `mise run bounded-wait`. Every token must match exactly once (`contract_token_uniqueness`).

F5 (cold review, Opus) — see §4.

## 4. Opus cold-review findings — architect-refuted, each CONFIRMED unless marked (report: `docs/research/kb/reports/agents/cold-review-phase7-2026-09-16.md`, arm tables there)

C1 (M1+M2+M3+M4, `hook_guard.py:159-174`) — rebuild the `unbounded wait loop` predicate as a CAPABILITY assertion, not a word sniff:
  - prefix: reuse the module's `_WRAPPER`/`_CMD` machinery so `nohup`/`env`/`setsid`/`bash -c`, `( … )`, `if …; then …`, `$( … )` do not hide the loop;
  - what counts as a WAIT: `until`/`while` whose CONDITION (the span between the keyword and `; do`/`\ndo`) is a wait-family predicate — a `!`-negated command, `test`/`[ … ]` with `-f/-e/-s/-d/-r`, `pgrep`, `grep -q`, `kill -0`, `curl`, `gh`, `docker`, `nc` — AND whose body contains `sleep`. A counter loop (`while [ $i -lt 40 ]`), a `while read` iteration, and `"$SLEEP"` must NOT fire (pin all three as non-fire tests);
  - bounded means: the CONDITION references `SECONDS`, `$deadline`/`$DEADLINE`/`$end`/a `date +%s` comparison, or the loop is wrapped by `timeout <n>` / `mise run bounded-wait` in COMMAND position before it. A `# timeout` comment, `--connect-timeout`, a path containing `timeout`, or a `DEADLINE=` assignment outside the condition must NOT exempt (pin as fire tests);
  - the terminator `done` counts only in command position (`(?:^|[;&|\n])\s*done\b`), never inside a predicate or echo (`grep -q DONE`, `/tmp/done/x` must still fire);
  - keep `quoted_blind=False` (the rule must read inside `sh -c '…'`), and a commit message quoting the shape (`git commit -m "…until [ -f x ]; do sleep 1; done…"`) must NOT fire — add that test; if that needs a second masked view, add it in the module without a second `_inert_masked(command)` call site (see R5).
C2 (M5, `bounded_wait.py:40-50`) — run the predicate with `start_new_session=True` and on `TimeoutExpired` `os.killpg` the group (TERM, short grace, KILL). Test: a predicate `sleep 47 | cat` with a 1 s per-attempt timeout leaves no surviving pid (poll `os.kill(pid, 0)`).
C3 (M6, `agentsview_pass.py:79-81, 322-328`) — a missing/unreadable skill file → `UNVERIFIABLE` (rc=2), never a traceback; catch `OSError` at the read and convert to `AgentsViewError`. Test both arms.
C4 (M7, `agentsview_pass.py:249-254, 189`) — ordinal 0 is a value: use `is not None`; a row without `ordinal` is a malformed row → `AgentsViewError`, not 0.
C5 (M8, `session_orphans.py:63-73`) — DELIBERATE, document it: at handoff every session-local wait loop is an orphan whether bounded or not, so `session-orphans` classifies with `is_wait_loop` on purpose. State that in the module docstring, in `format_plan` (label each WAIT-LOOP `bounded`/`unbounded`), and in the skill's step-1 text.
C6 (M9) — test the `--kill` happy path: a fake `Runtime` records the signals sent; assert the WAIT-LOOP pid is TERM'd then re-checked, and that `result.survivors` → rc=1.
C7 (M10, `session_review.py:908-911, 984-1023`) — with zero segments `newest_omission_segment` must be `None`/omitted, never `.0000.json`; add a docstring line that two concurrent runs on the SAME report path are unsupported (prune is per-name) and have the index carry the generation so a reader can detect a mismatch.
C8 (M11 + §3 F1, `session_ledger.py:2740-2758`) — one rule: `file_like` is exactly `type in {file, image, document}`. A known diagnostic type carrying `path`/`files` is a DIAGNOSTIC (digest only) — intended; an UNKNOWN type carrying a payload key is unknown → grouped, blocking. Add both fixture arms (`instructions` with a `files` list → DIAGNOSTIC; `future_shape_zzq` with `path` → grouped omission rc=1).
C9 (L1, `handoff_check.py:35-36`) — make the carrier scan fence-aware (skip ``` … ``` blocks) and add a non-fire test for prose "The next task is X" mid-line and for a fenced `next:` line. Keep the heading rule.
C10 (L2, `handoff_check.py:186-188`) — when `task_plan.md` exists and `docs/agents/plan-pointer.json` is absent → `MISSING_PLAN_POINTER` (new verdict), so deleting the pointer cannot silence the stale check.
C11 (L4, `session_ledger.py:4320-4324`) — derive the primary reason from the certification/status enums, not substring sniffs of messages.
C12 (L7, `bounded_wait.py:40-50`, `main.py:1585`) — one real-subprocess test of `_run_command` (predicate `true` → satisfied; `false` with a 1 s deadline → 124), and import `bounded_wait.DEFAULT_INTERVAL_S` in `main.py` instead of re-declaring `15.0`.
Not changed by ruling: L3 (the pointer is unverifiable from a clone — Ray accepted that on 2026-09-16; say so in the session-resume skill in one sentence), L5, L6, L8.

## 5. Verification (config specialist runs; report real rc; `SANDBOX:` when the sandbox blocks — the architect re-runs)
```
typos --force-exclude python/src/dotfiles_setup/hook_guard.py python/src/dotfiles_setup/session_orphans.py python/src/dotfiles_setup/agentsview_pass.py .claude/skills/session-review/SKILL.md
uv run --project python ty check --project python python/src tests plugins
uv run --project python dotfiles-setup skills-mirror --check
uv run --project python dotfiles-setup check-doc-refs
uv run --project python pytest tests/test_doc_refs.py tests/test_session_ledger.py tests/test_session_orphans.py tests/test_agentsview_pass.py tests/test_hook_guard.py tests/test_plan_pointer.py -x -q
mise run verify
mise run lint
uv run --project python pytest tests/ -x -q
```

## 6. Commit
COMMIT: caller. Leave the tree uncommitted.

## 7. PREMISES (fresh reads this session)
- L `_inert_masked(command)` occurs at `hook_guard.py:181, 186, 811`; the contract token `"_inert_masked(command)"` is bound once by `suites.toml:1329` (`workflow.mise-tasks-enforcement`).
- L `workflow.goal-history` per-path tokens for the skill: `["validate the entire", "fixed `origin/main` merge-base", "docs/agents/goal-history.md"]` — `suites.toml:2494`.
- L the typos hits: `hook_guard.py:163` and `session_orphans.py:15`, word `ba` — `typos` rc=2, architect log `gates/typos-direct.log`.
- L smart quote at `.claude/skills/session-review/SKILL.md:99`.
- L `py_ty` diagnostic at `tests/test_plan_pointer.py:45:16` (`capsys.readouterr()` on `object`).
- L doc_refs hits `.claude/rules/persistence-gate-retry.md:60` and `:67` — `gates/01-lint.log:458-459`, `gates/04-pytest.log:21`.
- L `skills_mirror_parity` step = `dotfiles-setup skills-mirror --check` (`hk.pkl:706`); generator task `[tasks.skills-mirror]` (`mise.toml:1338-1341`).
- L `agentsview session list` supports `--agent`, `--project <name>`, `--limit` (`session list --help`, 2026-09-16); rows carry `project: "dotfiles"` and `agent: "claude"` (measured).
- L `_claude_attachment_event` `file_like` clause — `session_ledger.py:2752-2756`.
- L `session_orphans.main` kill/block ordering — `session_orphans.py:139-166`.
- L `workflow.session-orphans-wiring` contract — `suites.toml:1497-1525`.
- A `renovate_config_validate` red was transient (direct run rc=0 minutes later).
