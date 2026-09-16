# SPEC — settlement reconciles the codex SDLC team's spawn self-report against the descendant session records, and fails closed

Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles
Branch: fix/sdlc-team-settlement-verifies-spawn (already checked out, clean, at bce4ffd = origin/main)
Tracking: GitHub issue #1142 decision 2; task_plan.md Phase 6c P0.

## 1. Objective

When a `mise run sdlc-team` run settles, its `settlement.json` must state which specialists the dispatcher CLAIMED to spawn (the `Specialists spawned:` list in its final message) and which specialists were OBSERVED to spawn (the codex rollout files on disk whose `parent_thread_id` is this run's session id), and the run must settle `failed` — never `completed` — whenever those two disagree, whenever the observed side could not be read (parent session id not found, sessions root missing/unreadable), or whenever zero specialists were observed. Today (`sdlc_team.py:483-524`) the OBSERVED source is hard-coded unavailable and settlement status comes from the codex return code alone (`:549-553`), so a dispatcher that spawns nothing and writes a plausible list settles `completed` with rc=0. That is the failure this prevents: on 2026-09-15 run `2c97f4bc…` claimed four specialists, spawned zero (four router spawn errors), and settled `completed` — and the fabricated sentence was later cited as evidence. #1145 fixed the spawn; this change makes the report verifiable so a regression cannot hide behind the model's sentence again.

Outcome, not keystrokes: a reader of `settlement.json` alone must be able to tell claimed from observed, and a settlement whose observed side is unknown must read as a failure to every consumer of `SdlcSettledStatus`.

## 2. Files

Modify:
- `python/src/dotfiles_setup/lane_result.py` — add the parent-id banner parser and the rollout-file OBSERVED collector (pure, testable, no subprocess).
- `python/src/dotfiles_setup/sdlc_team.py` — carry `sessions_root` in `_SupervisorPayload` (resolved at dispatch from `CODEX_HOME`, default `~/.codex`), consume the new collector in `_write_lane_receipts`/`_supervise`, add the three settlement fields, apply the fail-closed rule, and fix the dispatcher prompt (see constraints).
- `schemas/sdlc-team-settlement.json` — regenerate from `generate_settlement_schema()` so `tests/test_sdlc_team.py::test_committed_schema_matches_its_canonical_model` stays green (there is no mise task for this; write the generator's JSON with the same indent the committed file uses).
- `tests/test_sdlc_team.py` — the existing supervisor test at `:299-347` currently expects `completed` for "claims one specialist, zero child records": it BECOMES the negative arm (must now settle `failed` with the reconciliation error). Add: positive arm; claimed≠observed arm; parent-id-missing arm.
- `tests/test_lane_result.py` — unit tests for the banner parser and the rollout collector (fixtures under `tmp_path`, never `~/.codex`).
- `.claude/skills/codex-sdlc-team/SKILL.md` (`:78-100` describe settlement/receipts) — one short paragraph: settlement now carries claimed vs observed and fails closed.
- `.claude/rules/codex-sdlc-team.md` (`:34` "writes `SdlcTeamSettlement` when the run ends") — extend that sentence by one clause; the file is eager and budgeted (200 lines / 24,000 bytes) so keep it to one clause.
- `docs/specs/codex-sdlc-subagent-team.md` — add a short "Spawn reconciliation (2026-09-16)" subsection stating the rule and the negative arm. Do not rewrite V3/V4 (that is a separate P1).

Do NOT touch: `python/src/dotfiles_setup/lane_result.py::collect_observed` (the agentsview collector stays as-is for the standalone `lane-receipt` CLI at `:630`), `schemas/lane-result.json` / `LaneResult` (unchanged shape), `.codex/agents/*.toml`, anything under `.github/`.

## 3. Interfaces

In `lane_result.py` (public, added to `__all__`):

```python
def parse_parent_thread_id(log_text: str) -> str | None:
    """Return the `session id: <uuid>` value from the codex exec banner, else None.

    The banner is the first block of the captured stdout: `OpenAI Codex v…`, a
    `--------` line, key: value lines, a closing `--------` line. Read ONLY that
    first delimited block (before any `user`/model text) so a `session id:`
    string quoted later by the model cannot satisfy the parse.
    """

def collect_session_files(parent_thread_id: str, sessions_root: Path) -> CollectorOutcome:
    """OBSERVED source read from codex's own rollout files under ``sessions_root``.

    A child is any `rollout-*.jsonl` whose FIRST line is a `session_meta` record with
    `payload.parent_thread_id == parent_thread_id`. Node name = `payload.agent_role`,
    role = `payload.agent_path` (empty allowed), source = OBSERVED. Returns
    available=False (with a reason) when parent_thread_id is empty or sessions_root
    is not a directory; returns available=True with zero agents when the scan ran and
    found nothing — those two outcomes must stay distinct (mirror of
    `test_observed_unavailable_is_distinct_from_available_empty`).
    """
```

In `sdlc_team.py`:

```python
class SdlcTeamSettlement(codec.Struct, frozen=True):
    run_id: str
    status: SdlcSettledStatus
    codex_returncode: int | None = None
    codex_pid: int | None = None
    finished_at: str = ""
    duration_s: float = 0.0
    errors: tuple[str, ...] = ()
    parent_thread_id: str | None = None        # NEW — from parse_parent_thread_id(codex.log)
    specialists_claimed: tuple[str, ...] = ()  # NEW — roster names from the SELF_REPORT list, report order
    specialists_observed: tuple[str, ...] = () # NEW — agent_role of each depth-1 child, sorted

class _SupervisorPayload(codec.Struct, frozen=True):
    ...existing fields unchanged...
    sessions_root: str = ""                    # NEW — resolved in dispatch(); "" means unknown → fail closed
```

Reconciliation rule (implement as a small pure function in `sdlc_team.py` or `lane_result.py`, your choice, unit-tested directly):
- claimed identity of a SELF_REPORT item = {its `name`} ∪ {every backticked token in its `role` text}. This is because the model has written both real shapes: `` - `sdlc-python-specialist` — `/root/python_review` `` (name = role) and `` - `/root/config_pin_review` — `sdlc-config-specialist`; … `` (name = path, role text carries the roster name). An item MATCHES an observed child when the child's `agent_role` is in the item's identity set.
- consistent ⇔ parent_thread_id known AND observed source available AND len(observed) ≥ 1 AND every claimed item matches exactly one observed child AND every observed child is matched by exactly one claimed item.
- inconsistent ⇒ `status = FAILED` (even when codex rc == 0) and `errors` gains one line per cause, prefixed `spawn reconciliation:` — e.g. `spawn reconciliation: parent thread id not found in codex.log banner`, `spawn reconciliation: claimed 'sdlc-python-specialist' has no observed child session`, `spawn reconciliation: observed child 'sdlc-config-specialist' (/root/config_review) was not claimed`, `spawn reconciliation: zero specialists observed under <sessions_root>`.
- `TIMED_OUT` stays `TIMED_OUT`; a codex rc≠0 stays `FAILED`; reconciliation only ever demotes `COMPLETED` → `FAILED`, never promotes.
- `specialists_claimed` = the roster name per claimed item when one is identifiable (the identity-set member that matched, else the item's `name`); `specialists_observed` = sorted agent_roles. Both are recorded on EVERY settlement, including failed ones, so the reader sees the disagreement.

## 4. Constraints and invariants

- Zero-bash-logic: everything in python; no new scripts.
- No inline suppressions (`noqa`, `type: ignore`) — the `no_lint_skip` hk step rejects them.
- Isolated test state: fixtures build a fake `sessions_root` under `tmp_path` with hand-written `rollout-*.jsonl` files; never read `~/.codex`. The real record shape to reproduce (first line of a child file, verified 2026-09-16): `{"timestamp": "...", "ordinal": 0, "type": "session_meta", "payload": {"id": "<child-uuid>", "parent_thread_id": "<parent-uuid>", "originator": "codex_exec", "agent_role": "sdlc-python-specialist", "agent_path": "/root/python_review", "agent_nickname": "Bacon", "source": {"subagent": {"thread_spawn": {"parent_thread_id": "<parent-uuid>", "depth": 1, "agent_path": "/root/python_review", "agent_nickname": "Bacon", "agent_role": "sdlc-python-specialist"}}}, "cwd": "..."}}`. Real child files carry a SECOND `session_meta` line at ordinal 1 — read only the first line; a file whose first line is not `session_meta` is skipped, a file that fails to parse is skipped AND counted in the collector's error text (never silently).
- Scan ALL `rollout-*.jsonl` under `sessions_root` recursively (3,236 files on this host today; first-line reads only). Do NOT bound the scan by date directory: directory/filename dates are LOCAL time while record timestamps are UTC (`rollout-2026-09-16T01-16-17-…` ↔ `"timestamp":"2026-09-16T06:16:17.947Z"`), so a date bound is a false-negative hazard (`.claude/rules/probes-need-a-control-arm.md` rule 3).
- `_supervise` opens the log with `"wb"` (`sdlc_team.py:537`) and codex writes the banner as its first stdout — so in tests the fake `Popen` must write the banner bytes into the `stdout` file object it is handed; a pre-written codex.log is truncated by the supervisor.
- Parse the parent id from the log AFTER codex exits (the whole log is on disk then). Do not add `--json` to the argv — the human transcript in `codex.log` is the primary evidence file that #1142's investigation and the skill rely on.
- The HOOK source is always unavailable for codex runs (no Claude hooks fire) and `merge_sources` reports that as a disagreement; the fail-closed rule must key on the spawn-reconciliation conditions above, NOT on "any disagreement", or every run fails.
- Prompt fix in `build_prompt` (`sdlc_team.py:238-245`): DELETE the clause "If a specialist spawn fails with `no thread with id` before the agent exists, retry once without conversation history. If spawning still fails, do the work yourself and report every spawn failure." — it was derived from a fabricated retry (#1145 body) and licenses exactly the generalist fallback this change fails. REPLACE with: "If a specialist cannot be spawned, stop and report the spawn failure with its error text; do not do that specialist's work yourself." Pin the closing list format: "End with a Markdown list under `Specialists spawned:` with exactly one item per spawned specialist, each item formatted `- `<agent_role>` — `<agent_path>``, and state that no others were spawned." Keep every other prompt clause byte-identical; `tests/test_sdlc_team.py` asserts on prompt text elsewhere — run it.
- `CODEX_HOME` resolution: `Path(os.environ.get("CODEX_HOME") or "~/.codex").expanduser() / "sessions"`, resolved in `dispatch()` and carried on the payload as a string, so the supervisor process never re-reads the environment. (codex docs: `CODEX_HOME` defaults to `~/.codex` and roots all state incl. sessions.)
- Existing `collect_observed` (agentsview) is NOT wired into settlement: it is an index with unverified lag and an unverified row schema; the rollout file is codex's primary record. Leave it and its tests untouched.
- Commit message: conventional `fix(sdlc-team): …`, body states the rule, the negative arm, and file-captured gate rcs; end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01R3V8ff1cnaWEp1QXtmvAYC`.
- Licensed dissent applies to every premise below.

## 5. Verification

Smallest bundle, file-captured rc:

```
uv run --project python pytest tests/test_sdlc_team.py tests/test_lane_result.py -x -q > /tmp/sdlc-spawn-pytest.log 2>&1; echo "rc=$?" >> /tmp/sdlc-spawn-pytest.log
mise run lint > /tmp/sdlc-spawn-lint.log 2>&1; echo "rc=$?" >> /tmp/sdlc-spawn-lint.log
```

Required arms (each a test that fails if the change is reverted):
1. NEGATIVE (the P0 arm): output claims `` - `sdlc-python-specialist` ``, codex.log carries a banner with a session id, sessions_root has ZERO child files → `status == failed`, `errors` contains `spawn reconciliation: zero specialists observed`, `specialists_claimed == ("sdlc-python-specialist",)`, `specialists_observed == ()`.
2. POSITIVE: same claim, sessions_root has one child file with `parent_thread_id` == banner id and `agent_role == "sdlc-python-specialist"` → `status == completed`, `parent_thread_id` set, both tuples equal `("sdlc-python-specialist",)`.
3. MISMATCH: claim `sdlc-python-specialist`, observed child `sdlc-config-specialist` → `failed`, two `spawn reconciliation:` errors (unclaimed observed + unobserved claimed).
4. PARENT UNKNOWN: fake codex writes no banner → `failed`, error names the missing banner; a child file present under sessions_root is NOT credited.
5. Path-first shape: self-report item `` - `/root/config_pin_review` — `sdlc-config-specialist`; initial spawn … `` reconciles against observed `agent_role == "sdlc-config-specialist"` (the identity-set rule).
6. `parse_parent_thread_id`: banner → uuid; a log whose only `session id:` line is AFTER the closing `--------` (model-quoted) → None.
The full suite, `mise run verify`, `mise run lint-docs` run at integration by the caller.

## 6. Commit

COMMIT: lane — commit on the current branch `fix/sdlc-team-settlement-verifies-spawn`; report the hash.

## 7. PREMISES

- L — `SdlcTeamSettlement` fields are exactly run_id, status, codex_returncode, codex_pid, finished_at, duration_s, errors — `python/src/dotfiles_setup/sdlc_team.py:103-111`
- L — `_SupervisorPayload` fields: run_id, argv, prompt_file, output_file, log_file, receipt_json, receipt_md, settlement_file, workdir, started_at, timeout_s — `sdlc_team.py:115-128`
- I — `_write_lane_receipts(payload, duration_s) -> tuple[str, ...]` builds SELF_REPORT from `output_file`, hard-codes OBSERVED unavailable with error "parent session id is not carried by SdlcTeamRequest", then `merge_sources(self_report, observed, hook)` — `sdlc_team.py:483-524` (observed at :496-501)
- I — `_supervise` derives status solely from codex rc (`COMPLETED if returncode == 0 else FAILED`), TIMED_OUT on timeout, and opens the log `"wb"` — `sdlc_team.py:527-583` (status :549-553, log :537)
- L — `dispatch()` argv is `codex exec -s <sandbox> -c model_reasoning_effort="…" -C <workdir> -o <output_file> -` with NO `--ephemeral` and NO `--json` — `sdlc_team.py:371-383`
- L — `build_prompt` carries the retry/do-it-yourself clause and the `Specialists spawned:` instruction — `sdlc_team.py:238-245`
- I — `lane_result.AgentSource` = {SELF_REPORT, OBSERVED, HOOK}; `AgentNode(name, role="", parent=None, sources=(), status="")`; `CollectorOutcome(source, agents=(), available=True, error="")` — `python/src/dotfiles_setup/lane_result.py:41-57, 70-75`
- I — `collect_self_report(report_text)` parses the first list under a `specialists spawned:`-like line; item name = backticked/bold/plain token, optional `— role` text — `lane_result.py:125-172`; regexes at `:87-97`
- I — `merge_sources(*outcomes)` records "source <x> unavailable: …" for every unavailable source and "agent 'n' seen by …; missing from …" per name mismatch — `lane_result.py:425-478`
- I — `collect_observed` uses the agentsview binary at a hard-coded path pinned to 0.42.0 and is called by the standalone CLI — `lane_result.py:80-84, 250-299, 630`
- P — HOOK source is unavailable when its log is missing (so codex runs always carry that disagreement): `tests/test_lane_result.py:215` `test_missing_hook_log_is_unavailable_but_empty_log_saw_nothing`; DATA match: sdlc runs write no hook log under `.agent/` for a codex process, same missing-file condition.
- L — codex exec banner: line 1 `OpenAI Codex v0.154.0`, line 2 `--------`, line 10 `session id: 01a0a8da-6d39-74e3-a8fc-fe66f5505378`, line 11 `--------`, then `user` — `.agent/sdlc-runs/4e6f6a4d042745beae6619557c630b70/codex.log:1-12` (delimiters confirmed at :2 and :11 by grep)
- L — child rollout first line: `type: session_meta`, payload keys include `id`, `parent_thread_id`, `agent_role`, `agent_path`, `agent_nickname`, `originator`, `cwd`, `source.subagent.thread_spawn.{parent_thread_id, depth, agent_path, agent_nickname, agent_role}` — `~/.codex/sessions/2026/09/16/rollout-2026-09-16T01-16-17-01a0a8db-de4d-7c93-a96f-8d001939aecd.jsonl:1` (and two siblings, same shape); the parent's first line has `parent_thread_id: null`, `source: "exec"` — `rollout-2026-09-16T01-14-43-01a0a8da-6d39-74e3-a8fc-fe66f5505378.jsonl:1`
- L — a child file carries a second `session_meta` line at ordinal 1 — `codex.log:10065-10066` of the same run shows `.jsonl:1` and `.jsonl:2` both `"type":"session_meta"`
- L — real self-report shapes: role-first `` - `sdlc-python-specialist` — `/root/python_review` `` — `.agent/sdlc-runs/4e6f6a4d042745beae6619557c630b70/output.md:125-131`; path-first `` - `/root/config_pin_review` — `sdlc-config-specialist`; initial spawn failed … `` — `.agent/sdlc-runs/2c97f4bcd31443dd9ad598f4cce08dd0/output.md:134-140`
- L — `CODEX_HOME` defaults to `~/.codex` and roots Codex state — `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/codex/config-file__environment-variables.md:17`, `config-file__config-advanced.md:71`
- L — filename/dir dates are local while timestamps are UTC: `rollout-2026-09-16T01-16-17-…` has `"ts":"2026-09-16T06:16:17.947Z"` — same child file, line 1
- I — the supervisor test builds `_SupervisorPayload(...)` by keyword with a fake `Popen` that writes nothing and asserts `COMPLETED` for a one-specialist claim with no child records — `tests/test_sdlc_team.py:299-347`
- I — committed-schema parity test decodes `schemas/sdlc-team-settlement.json` and compares to `generate_settlement_schema()` — `tests/test_sdlc_team.py:450-470`; no mise task regenerates it (grep of `mise.toml` for `sdlc`: only `[tasks.sdlc-team]` at :280)
- E — `SdlcTeamSettlement.parent_thread_id` ← `parse_parent_thread_id(codex.log)`; a UUID string or None; bounded (36 chars); not PII
- E — `SdlcTeamSettlement.specialists_claimed` ← roster names parsed from the model's `Specialists spawned:` list; model-authored text, so it can contain ANY string (paths, prose) — bounded per item by the list-item regex; not PII by design but not guaranteed
- E — `SdlcTeamSettlement.specialists_observed` ← `payload.agent_role` of child session_meta records; codex-authored roster names from `.codex/agents/*.toml`; bounded; not PII
- E — `SdlcTeamSettlement.errors` gains `spawn reconciliation: …` lines ← composed by our code from the above plus `sessions_root` (an absolute path under the user's home — a path, not a secret; never include file CONTENTS or the model's prose in an error line)
- E — lane receipt (`receipt.json`/`receipt.md`) OBSERVED nodes ← the new collector; name=agent_role, role=agent_path
- A — codex 0.154.0's banner format (`session id:` key, `--------` delimiters) is stable across the patch versions this repo pins; held because it is observed on the pinned version and no doc describes the exec banner. If it changes, the parse fails closed (settlement `failed`, error names the missing banner), which is the safe direction.
