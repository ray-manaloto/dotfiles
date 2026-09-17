# codex SDLC team — Phase 7 IMPLEMENTATION run report (2026-09-16), verbatim

Brief: `mise run sdlc-team` implement mode, run `phase7-session-handoff-implement-20260916`, effort xhigh, 5400 s ceiling, 30-path allowlist, `COMMIT: caller`; spec appended below. Settlement: `completed`, 4,242 s, claimed == observed = {python, config, documentation}, errors=[]. Output copied verbatim at receipt; the architect's gate re-runs, cold review and dispositions follow in the PR body and the tail of this file.

---

## Ordered workstream → specialist map

1. W1–W3 and W6, plus Python portions of W4/W7/W8 → `sdlc-python-specialist`.
2. Config portions of W4/W7/W8 and final §5 verification → `sdlc-config-specialist`.
3. W4/W5 documentation, W7/W8 guidance, and whole-diff review → `sdlc-documentation-specialist`.

Overall status: **partial failure; not ready for caller commit.** Changes remain uncommitted as required.

`★ Insight ─────────────────────────────────────`
The focused tests passed, but the independent whole-diff review found three behavioral fail-open paths. This demonstrates why this repository separates unit tests, verification contracts, and cold review: each detects a different defect class.
`─────────────────────────────────────────────────`

## Implementation completed

The team implemented the Phase 7 Python modules, CLI wiring, mise tasks, verification contract, tests, fixtures, skills, rules, technical reference, AgentsView handoff, and generated [plan-pointer.json](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/agents/plan-pointer.json) through `mise run plan-pointer`.

No files were staged, committed, pushed, or submitted as a PR. The three pre-existing untracked review inputs were preserved.

## Gate evidence

| Gate | Result |
|---|---|
| Python-owned pytest matrix | `rc=0` — 537 passed |
| Python Ruff | `rc=0` |
| Python `ty check` | `rc=0` |
| Focused §5 pytest matrix | `rc=0` — 537 passed |
| Ruff check + format check | `rc=0` — 217 files formatted |
| `mise run lint-docs` | `rc=0` |
| `git diff --check` | `rc=0` |
| `mise run lint` | `rc=1`, **SANDBOX** — could not create the hk log under `~/.local/state/dotfiles/` |
| Full pytest | `rc=1`, **SANDBOX** — process introspection was denied; 751 passed before `test_read_proc_start_reads_a_stable_value_for_a_live_process` |
| `mise run verify` | `rc=1` — **real failure**, 155 passed, 1 failed, 4 skipped |
| `mise run session-review` | `rc=1`, expected incomplete verdict |
| Historical `handoff-check` control | `rc=1`, expected; exactly one `forbidden_task_carrier` finding |

The new session-review header reported:

- `VERDICT: INCOMPLETE — selection certification is explicit_session_id_unresolved`
- 3,910 omissions.
- Leading families: `atis-latch` 2,791; reviewer semantic 373; `ai-title` 371; `auto_mode` 142.
- Generation: `383057e4d8264e4f94c3ff4de1885e6a`.

## Fail-arm evidence

The combined fail-arm test batch passed: `rc=0`, 16 tests.

- Forbidden `## Next task`: bad `rc=1`; restored handoff `rc=0`.
- Missing `NEXT SESSION`: bad `rc=1`; refreshed active plan/pointer `rc=0`.
- Cross-root implicit output: `rc=2`; report and sidecar sentinel bytes unchanged.
- 100 renamed records: one grouped `×100` omission and `rc=1`; 100 `token_usage_record` rows: zero unknown omissions and `rc=0`.
- Segment publication: three segments followed by one, new generation, zero stale reachable segments.
- Unbounded wait: denied `rc=1`; deadline-bearing wait allowed `rc=0`.
- `bounded-wait` without deadline: `rc=2`; missing file deadline: `rc=124`; existing-file control: `rc=0`.
- Fake orphan tree: unallowed `OTHER` `rc=1`; explicitly allowed PID `rc=0`.

## Unresolved review findings

- **HIGH:** `workflow.goal-history` remains red. [session-review/SKILL.md](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/skills/session-review/SKILL.md:26) lacks three literals required by [suites.toml](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/verification/suites.toml:2494).
- **HIGH:** Fresh path-bearing Claude attachment types can bypass parser-blocking unknown classification in [session_ledger.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/session_ledger.py:2755).
- **HIGH:** The default AgentsView census accepts missing provider/project metadata and applies its limit before filtering, so it can certify an incomplete or incorrect session set in [agentsview_pass.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/agentsview_pass.py:147).
- **MEDIUM:** `session-orphans --kill` does not reap known wait loops when any unallowed `OTHER` descendant exists, contrary to W7, in [session_orphans.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/session_orphans.py:139).
- **MEDIUM:** The W7 verification contract covers `session-orphans` but omits the bounded-wait helper and hook-guard redirect chain in [suites.toml](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/verification/suites.toml:1492).

Per the dispatcher contract, the team did not repair or rerun the failed verification gate after these findings.

One orchestration anomaly was also preserved: an unescaped backtick in a later memory search accidentally attempted `mise run sdlc-team`. It failed before dispatch because the sandbox denied the uv cache and was not retried; no additional specialist was spawned.

## Specialists spawned:

- `sdlc-python-specialist` — `/root/phase7_python`
- `sdlc-config-specialist` — `/root/phase7_config`
- `sdlc-documentation-specialist` — `/root/phase7_docs`

No others were spawned.


---

## Appendix — the implementation spec handed to the team (verbatim)

# Spec — Phase 7 IMPLEMENTATION: the accepted findings of the two `/session-handoff` reviews (2026-09-16)

Repo: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`
Branch: `feat/phase7-session-handoff-sdlc-review` (already checked out, off `origin/main` = `3d03ea8`).
Mode: **IMPLEMENT** — workspace-write. `COMMIT: caller` (the architect commits; leave the tree uncommitted).
Ruling (Ray, 2026-09-16, session `dotfiles-20260916.002`): everything accepted from both reviews ships in ONE PR, and the codex SDLC team does the planning, implementation, code review and verification. The tracked continuity carrier is a plan DIGEST pointer only — never task text.

Inputs (read first, they are the ratified findings):
- `docs/research/kb/reports/agents/codex-sdlc-session-handoff-review-2026-09-16.md` (your team's review + the spec it answered)
- `docs/research/kb/reports/agents/agentsview-session-handoff-review-2026-09-16.md` (the Claude AgentsView pass; its "Proposed AgentsView pass" and "Recurring learnings" sections are load-bearing)
- `docs/research/kb/reports/agents/2026-09-14j-hung-process-review.md` § "Ratified design (operator, 2026-09-15)" — the never-shipped fix, workstream W7

Dispatcher: plan first (write the plan into your final report's head as the ordered workstream → specialist map), then spawn the specialists in parallel on DISJOINT files (python vs config vs documentation), then have the config specialist run the gates listed in §5 and the documentation specialist review the whole diff against §3. Report every gate's real exit code. If a gate fails for SANDBOX reasons (permission denied outside the workspace, mise state dir, DNS), say `SANDBOX: <command>` — the architect re-runs it outside; do not report a sandbox failure as a code failure and do not stub around it.

## 1. Objective

Make the `/session-handoff` workflow honest and mechanically checkable: the plan is the only task carrier and a check enforces it; the session-review tool stops destroying its own evidence, explains its own failure, and stops flooding on harness records; the 2026-09-15 ratified orphan/bounded-wait fix finally lands; and an AgentsView census becomes a named, tasked step. Failure prevented: a fourth session resuming stale task prose, a fifth pytest run clobbering the operator's only review evidence, and a third session leaving an unsatisfiable wait loop alive past `/clear`.

## 2. Workstreams, files, outcomes

### W1 — session-review test isolation + output safety (python)
- `tests/test_session_review.py:1176` and `:1269` run the CLI from `REPO_ROOT` without `--output`; `command_audit.write_report` (`python/src/dotfiles_setup/command_audit.py:771`) resolves a relative destination against `project_root`, so both overwrite the operator's real `.agent/session-review.md` + sidecars. Give both tests an explicit `--output` under `tmp_path`. Add a sentinel test: seed `.agent/session-review.md` (+ one sidecar) in an isolated fake repo root with known bytes, run the mismatched-root case, assert the bytes are unchanged.
- CLI rule: when `--source-repo-root` is given and does not resolve to the invoking repo root, an implicit destination is refused (exit 2, message names `--output`). Explicit `--output` always honored.

### W2 — record classification + bounded unknown-type diagnostics (python)
- Codex: add `token_usage_record` to the `known` set in `_parse_codex` (`session_ledger.py:2536`) as known telemetry — no event needed beyond what other bounded records emit; never a per-record omission.
- Claude attachments (`_claude_attachment_event`, `session_ledger.py:2670-2730`): the harness reminder/context types measured on 2026-09-16 — `total_tokens_reminder`, `batching_reminder_sent`, `hook_system_message`, `prompt_snapshot`, `bash_output_audience_note`, `environment`, `date`, `model`, `instructions`, `session_context`, `remote_session_change`, `output_style_instructions` — become known: reminders as known-and-skipped counters, context-bearing ones as bounded diagnostics (digest + byte count, never user authority). Fixture-derive the safe fields from real rollouts under `~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/` (read structurally, never grep raw; copy ONLY the structural envelope into `tests/fixtures/session_review/`, no message text).
- Fresh unknown types (both providers) stay PARSER-BLOCKING but are summarized ONCE per provider/type: one omission line `unknown <Provider> <record|attachment> '<type>' ×<count> (first <source_id>:<line>)`, plus the census entry carries the count. Keep `CoverageStatus.INCOMPLETE` and rc=1 semantics.

### W3 — operator-first report block + generation-safe artifacts (python)
- `render_coverage` (`session_ledger.py:4215`) opens with `VERDICT: COMPLETE|INCOMPLETE — <one primary reason>` (the largest omission family, or the selection certification when that is the blocker), then: selected session id, source root, invoking repo root, `pytest-temp detected` when either root contains `pytest-of-`, counts, `omission total` + a histogram by (provider, type) top 10, the generation id, the omissions index path and newest referenced segment, and the iteration action. Keep every existing section after it.
- `_write_segmented_artifact` (`session_review.py:915`): write the new generation's segments, then the index, then PRUNE stale numbered segments (`<name>.NNNN.json` with NNNN > new count) and record a `generation` id in every index. A crash before the index leaves the previous index consistent with its own segments — so write new segments under a temporary generation suffix and rename into place last, or an equivalent that satisfies the fail arms in §5.

### W4 — goal 1: plan-only task authority (docs + python)
- `.claude/skills/session-handoff/SKILL.md`: remove every next-task CARRIER — the `$ARGUMENTS` task text and its inference (frontmatter `argument-hint` too), step 3a "what's next", step 3b "next task + preload pointers", the step-6 `Resume <task>:` form (emit exactly `Run /session-resume`), the checklist's first box wording. Step 0 stays, renamed "Resolve active-plan ambiguity" — rulings are recorded in `task_plan.md` only. Step 5 + checklist: drop the retired "ref loop" wording; `handoff-check` is the single carrier. Add to step 3c: every report written this session gets an inbound pointer (handoff + the rule/skill it governs) or is recorded as deliberately orphaned. Add step 1's task call (`mise run session-orphans`, W7) and step 1b (`mise run session-agentsview-pass`, W8) and the plan-pointer refresh (`mise run plan-pointer`, below). Keep ≤ 500 lines / 32,000 bytes (`md_size_budget`, skill class).
- `.claude/skills/session-resume/SKILL.md`: `NEXT:` line becomes `PLAN: task_plan.md → <active phase heading>` read from the plan; step 4 offers to begin the active phase without copying it. Keep the DISAGREEMENT-first shape.
- `docs/agents/plan-pointer.json` (NEW, tracked): `{"plan_sha256": …, "active_phase": "<heading text>", "recorded_at": "<ISO UTC>"}` written by a new `mise run plan-pointer` (module `python/src/dotfiles_setup/plan_pointer.py`, thin task in `mise.toml`, wired in `main.py` like `handoff-check` at `main.py:1540`/`:2739`). The active phase is the LAST `## ` heading in `task_plan.md` containing `NEXT SESSION` (case-insensitive); if none, exit 1 with `missing_active_plan`. Never writes task text.
- `python/src/dotfiles_setup/handoff_check.py`: add verdicts `FORBIDDEN_TASK_CARRIER` (a heading or a line-start token matching `next[ -]task` case-insensitively, or a line starting `NEXT:`/`NEXT TASK`), `MISSING_ACTIVE_PLAN` (when `task_plan.md` exists at the repo root and has no `NEXT SESSION` heading), `STALE_PLAN_POINTER` (when both `task_plan.md` and `docs/agents/plan-pointer.json` exist and the sha or heading disagree). When `task_plan.md` is absent (fresh clone) emit an informational line and no failure. `handoff-check` exits 1 on any finding (it already does for citations — keep).

### W5 — docs (documentation)
- `.claude/skills/session-review/SKILL.md` → judgment only, target 120-150 lines: invocation, the two lanes, verdict semantics, unknown-record failure, the AgentsView/SDLC orchestration order (from the review's G3 table), the cost gate, disposition rules. Move cache mechanics, provider field catalogues, attachment limits and finalize internals verbatim to `docs/session-review-reference.md` (NEW) and link it. `doc_refs` must stay green (`mise run lint`).
- `.claude/rules/persistence-gate-retry.md` § "The dubious-ownership transient": add the second sighting — 2026-09-16 `mise run land -- 1158` → `FAIL smoke-tiers-1-3` on `tests/test_bash_budget.py::test_cli_wires_end_to_end`, `git ls-files` rc=128 in `/workspaces/dotfiles`; a standalone `mise run smoke` reproduced it once (rc=1), the in-container probe minutes later showed uid 1000 = owner 1000 and git rc=0, and the smoke retry passed (3521 tests). Still unattributed; two sightings now, both on the FIRST git call of a pytest run.
- `docs/handoffs/agentsview-2026-09-16.md` (NEW): the four AgentsView product defects D1–D4 from the AgentsView report, verbatim evidence, written for that project's agents (Ray's ruling: never fixed here).
- `.claude/rules/long-running-command-hangs.md` rule 2: name `mise run bounded-wait` as the sanctioned wait (W7) and state that the in-turn poll shape keeps its `deadline` — the guard allows any loop carrying `SECONDS`/`deadline`/`timeout`.

### W6 — session-review lane-1 noise + candidate dispositions (python)
- `shape_candidates` (`session_review.py:286`): normalize or reject structural prefixes, control operators, continuation markers, comments, `timeout` wrappers and duration-bearing `sleep N`; test through the public seam with realistic `BashCommand` inputs and positive controls (`gh issue`, `uv run` stay ranked).
- Give each lane-1/lane-2 candidate a stable id in the report (sha256 of the normalized shape, 12 hex) so a disposition can name it. The typed disposition MANIFEST itself is deferred (issue) — only the ids land here.

### W7 — the 2026-09-15 ratified fix: session-orphans + bounded-wait + guard (python + config)
- `python/src/dotfiles_setup/session_orphans.py` (NEW) + `mise run session-orphans` + `main.py` wiring: enumerate processes whose ancestor chain reaches a root pid (default: the nearest ancestor of the current process whose command matches `claude`; `--root <pid>` overrides). Reuse `reap.snapshot/parse_processes/Process/ancestor_pids` (`reap.py:96-250`); add `descendant_pids(processes, root)`. Classify each descendant: WAIT-LOOP (a shell whose command matches `until|while … do … sleep`) vs OTHER. Print an auditable plan (reap's `format_plan` style). `--kill` reaps WAIT-LOOPs via `reap.reap` semantics (TERM→KILL, group); OTHER is reported and the exit code is 1 (BLOCK) unless `--allow <pid>` names each one. Dry-run default. Never selects by pattern; never touches a pid outside the descendant set. Exclude the invoking process's own chain.
- `python/src/dotfiles_setup/bounded_wait.py` (NEW) + `mise run bounded-wait -- --deadline <s> (--file <path> | --cmd '<sh -c>') [--interval <s>]`: polls until the file exists / the command exits 0, or the deadline passes → exit 124 with a loud message naming what it waited on. `--deadline` is REQUIRED (argparse error otherwise). Interval default 15s, minimum 1s.
- `hook_guard.py`: new `Rule("unbounded wait loop", …, since="2026-09-16")` denying a Bash command containing an `until`/`while` … `do` … `sleep` loop with NO deadline token (`SECONDS`, `deadline`, `timeout`, `bounded-wait`) in the command, redirecting to `mise run bounded-wait`. It MUST allow the in-turn poll shape prescribed by `long-running-command-hangs.md` rule 2 (`while [ $SECONDS -lt $deadline ] …`) and a quoted mention of itself (`echo "until [ -f x ]; do sleep 1; done"` inside a commit message with `quoted_blind`). Add tests for both arms in `tests/test_hook_guard.py`. The helper lands in the same diff BEFORE the rule is exercised (the redirect target must exist).
- `python/verification/suites.toml`: one contract binding the chain (task ↔ module ↔ tests ↔ the skill step naming the task), shaped like the existing `workflow.bash-logic-enforcement` contract.

### W8 — the AgentsView pass as a named, tasked step (python + config + docs)
- `python/src/dotfiles_setup/agentsview_pass.py` (NEW) + `mise run session-agentsview-pass` + wiring. Reads the remote-daemon flags from the frontmatter `install-remote` JSON of `~/.claude/skills/agentsview-finding-history/SKILL.md` (path overridable by `--skill`), never hardcodes them. Runs `agentsview session list --limit <n> --json` to resolve this project's recent Claude sessions (default: current + 2 prior; `--session <id>` repeatable overrides), then `agentsview session tool-calls <id> --json` per session (row keys measured 2026-09-16: `ordinal`, `timestamp`, `tool_use_id`, `tool_name`, `category`, `input_json`, `result_length`). Emits the block from the AgentsView report:
  ```
  AGENTSVIEW PASS — <session-id> (<n> tool calls)
    unbounded waits : <k>  (ords …)
    AskUserQuestion : <k>
    handoff Skill   : ord <n> | not invoked   (vs first `git commit` at ord <m>)
    step-3c writes  : <k> under docs/research/kb/reports/agents/
  ```
  Unbounded-wait detection parses `input_json` as JSON and inspects the Bash `command` field with the SAME predicate the guard uses (share the regex via import, one definition). Exit 1 when any session has an unbounded wait (a finding), else 0. All subprocess calls bounded by a timeout; a daemon failure is `UNVERIFIABLE`, never zero hits.
- The skill text (W4) names the task in the same change.

## 3. Interfaces
- New CLI subcommands, each `uv run --project python dotfiles-setup <name>`: `plan-pointer`, `session-orphans [--root PID] [--kill] [--allow PID]...`, `bounded-wait --deadline S (--file P | --cmd C) [--interval S]`, `session-agentsview-pass [--session ID]... [--limit N] [--skill PATH]`. Each a thin `mise.toml` task in the style of `[tasks.handoff-check]` (`mise.toml:989-992`).
- `handoff_check.Verdict` gains `FORBIDDEN_TASK_CARRIER`, `MISSING_ACTIVE_PLAN`, `STALE_PLAN_POINTER`; `check(repo_root, text)` signature unchanged.
- `session_ledger.OmissionCensusEntry` gains `count: int = 1`.
- Guard rule name: `unbounded wait loop`, `since = "2026-09-16"`.

## 4. Constraints and invariants
- Zero-bash-logic: no new `.sh`; logic in `python/`. Zero inline suppressions (`noqa`, `type: ignore`). ruff + ty clean.
- `md_size_budget`: skills ≤ 500 lines / 32,000 bytes; rules unscoped ≤ 200 lines / 24,000 bytes (`persistence-gate-retry.md`, `long-running-command-hangs.md` are eager — trim an equal number of lines if you add).
- `doc_refs`: every `mise run <task>` named in a skill/rule must exist in `mise.toml` in the same diff.
- Do not touch `task_plan.md`, `findings.md`, `progress.md` (coordinator-owned / append-only), `.claude/settings.json`, `CLAUDE.md`, `AGENTS.md`.
- `hook_guard` rules match AFTER `_inert_masked`; do not add quote-awareness to a pattern (`.claude/rules/mise-tasks-only.md` § Extending).
- Never print a credential value; the agentsview token file is passed as a path only.
- Tests: isolated state (tmp_path), every assertion must fail when the change is reverted, no wall-clock dependence (bounded-wait tests inject a fake clock / tiny deadline with a file that appears).
- Licensed dissent: if a premise below is contradicted by the code, stop that workstream and report it; implement the rest.

## 5. Verification (the config specialist runs these; report real rc; `SANDBOX:` if the sandbox blocks one)
```
uv run --project python pytest tests/test_session_review.py tests/test_session_ledger.py tests/test_handoff_check.py tests/test_hook_guard.py tests/test_reap.py tests/test_session_orphans.py tests/test_bounded_wait.py tests/test_agentsview_pass.py tests/test_plan_pointer.py -x -q
uv run --project python ruff check python tests && uv run --project python ruff format --check python tests
mise run lint            # hk read-only gate, incl. doc_refs + md_size_budget + bash_logic_budget
uv run --project python pytest tests/ -x -q
mise run verify
mise run session-review  # report the rc AND the new VERDICT line + histogram (it may still be INCOMPLETE for non-record reasons — say why)
mise run handoff-check   # against .agent/plans/session-2026-09-16c.md: must now report forbidden_task_carrier (that handoff carries task text) — a POSITIVE control
```
Fail arms to demonstrate in the report (mutate, observe red, restore, observe green): (a) add `## Next task` to a fixture handoff → `forbidden_task_carrier`; (b) remove the `NEXT SESSION` heading from a fixture plan → `missing_active_plan`; (c) seed sentinel report bytes, run the mismatched-root CLI → unchanged; (d) 100 `token_usage_record` rows → zero omissions; rename the type → ONE omission with `×100`, rc=1; (e) publish 3 segments then 1 → only 1 reachable, index generation new; (f) guard: `until [ -f x ]; do sleep 5; done` → deny; `deadline=$((SECONDS+60)); while [ $SECONDS -lt $deadline ]; do sleep 5; done` → allow; (g) `bounded-wait` without `--deadline` → argparse error; with a 2s deadline and no file → rc 124; (h) `session-orphans --root <pid of a fake tree in the test's ps fixture>` classifies a `sh -c 'until [ -f x ]; do sleep 1; done'` row as WAIT-LOOP and a `codex exec` row as OTHER (rc 1 without `--allow`).

## 6. Commit
COMMIT: caller. Leave every change uncommitted on `feat/phase7-session-handoff-sdlc-review`. Do not `git add`, commit, push, or open a PR.

## 7. PREMISES (each read fresh this session by the architect)
- L `write_report` resolves a relative `output` against `project_root`, not cwd — `python/src/dotfiles_setup/command_audit.py:771`.
- L default report destination `Path(".agent/session-review.md")` — `python/src/dotfiles_setup/session_review.py:864`.
- L both unsafe tests use `cwd=REPO_ROOT` with no `--output` — `tests/test_session_review.py:1176-1200` and `:1269-1300`; `REPO_ROOT = Path(__file__).parent.parent` at `:34`.
- L codex `known` record set (7 entries, no `token_usage_record`) — `session_ledger.py:2536-2544`; the unknown-record omission is appended per record at `:2594-2597`.
- L Claude attachment classification sets `warning_types`/`diagnostic_types`; unknown types append one omission per record — `session_ledger.py:2670-2730`.
- L `render_coverage` opens with `# Session requirement and promise ledger` and `Coverage: **STATUS**` — `session_ledger.py:4215-4240`; `OmissionCensusEntry(omission_id, category, authority, disposition, statement)` — `:337-344`; `RequirementCoverage.omissions: tuple[str, ...]` — `:795`; `omission_census()` — `:1005`.
- L `_write_segmented_artifact` writes segments then the index and never prunes — `session_review.py:915-935`; `_write_coverage_artifacts` — `:939-975`.
- L `handoff_check.Verdict` = {OK, MISSING_PATH, BAD_LINE_RANGE, UNKNOWN_TASK}; `check()` returns path+task findings; `main()` returns 0 on no handoff — `python/src/dotfiles_setup/handoff_check.py:33-50,155-200`.
- L `main.py` registers `handoff-check` via `subparsers.add_parser` at `:1540` and dispatches at `:2739`; `reap` at `:666`, `bash-budget` at `:775`.
- I `hook_guard.Rule(name, pattern, reason, since, quoted_blind=False)` — `hook_guard.py:48-95`; `_RULES` tuple at `:274`; the `backgrounded mise run` rule shape at `:493-506`.
- I `reap.Process(pid, ppid, age_s, state, command)` `:96-105`; `ancestor_pids(processes, start_pid)` `:217-236`; `protected_pids` `:239-247`; `select(processes, *, pattern, min_age_s, protected, full_match)` `:271`; `[tasks.reap]` `mise.toml:1624`.
- L `[tasks.handoff-check]` thin-caller shape — `mise.toml:989-992`; `[tasks.session-state]` `:979-982`.
- L `doc_refs._TASK_RE = \bmise run ([A-Za-z0-9][A-Za-z0-9:_.-]*)` scans skills/rules for task names — `python/src/dotfiles_setup/doc_refs.py:314`.
- L `task_plan.md`, `findings.md`, `progress.md`, `.plan-attestation` are gitignored — `.gitignore:143-151`.
- L the plugin attestation writes `./.plan-attestation` (sha256 of the plan) — plugin `scripts/attest-plan.sh:76-89`; it is operator-only and untracked, so the tracked pointer is a separate artifact.
- L `agentsview session tool-calls <id> --json` returns `{"tool_calls": [...], "count": N}` with row keys `ordinal, timestamp, tool_use_id, tool_name, category, input_json, result_length` — measured 2026-09-16 on this session; `session list` prints an "Excluded 3515 sessions by default" line on stderr before the JSON.
- L the AgentsView skill's remote flags live in its frontmatter comment `# install-remote: {"server":…, "token_file":…}` — `~/.claude/skills/agentsview-finding-history/SKILL.md:3`.
- L `long-running-command-hangs.md` rule 2 PRESCRIBES `deadline=$((SECONDS+540)); while [ $SECONDS -lt $deadline ]; do … sleep 15; done` — the guard must allow it.
- P `hook_guard` rule `backgrounded mise run` (`:493-506`) is the precedent for a shape-denial with a redirect reason; same data shape (whole Bash command string, masked view).
- P `workflow.bash-logic-enforcement` in `python/verification/suites.toml` is the precedent for a task↔module↔tests↔rule chain contract.
- A `session-review` may remain INCOMPLETE after W2 for non-record reasons (open turns, provenance omissions measured 3,246 + 944 rows) — the check is that record-type omissions drop to zero, not that rc becomes 0.
- A `agentsview` exits 0 on `tool-calls` for a valid id and non-zero for an unknown id (the AgentsView lane measured one rc=1 on a bad id).
