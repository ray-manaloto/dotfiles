# SPEC v5 — settlement reconciles the codex SDLC team's spawn self-report against the descendant session records, and fails closed

Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles
Branch: fix/sdlc-team-settlement-verifies-spawn (checked out, clean, at ca6cd57 = origin/main bce4ffd + three docs commits)
Tracking: GitHub issue #1142 decision 2; task_plan.md Phase 6c P0.
Revision: v5 — corrected after four premise-verification passes (report: docs/research/kb/reports/agents/premise-verifier-spawn-2026-09-16.md, all four passes appended verbatim). Changes are marked [v2], [v3], [v4], [v5] by the revision that introduced them. v5 adds ONLY the ambiguity rule below — a strict fail-closed tightening that rests on no new factual premise (the verifier's own counterexample), so it was not sent back for a fifth pass.

## 1. Objective

When a `mise run sdlc-team` run settles, its `settlement.json` must state which specialists the dispatcher CLAIMED to spawn (the closing `Specialists spawned:` list in its final message) and which specialists were OBSERVED to spawn (the codex rollout files on disk whose `parent_thread_id` is this run's session id), and the run must settle `failed` — never `completed` — whenever those two disagree, whenever the observed side could not be read (parent session id not found, sessions root missing/unreadable), or whenever zero specialists were observed. Today (`sdlc_team.py:483-524`) the OBSERVED source is hard-coded unavailable and settlement status comes from the codex return code alone (`:549-553`), so a dispatcher that spawns nothing and writes a plausible list settles `completed` with rc=0. That is the failure this prevents: on 2026-09-15 run `2c97f4bc…` claimed four specialists, spawned zero (four router spawn errors), and settled `completed` — and the fabricated sentence was later cited as evidence. #1145 fixed the spawn; this change makes the report verifiable so a regression cannot hide behind the model's sentence again.

[v2] The rule must ALSO hold on the real successful run `4e6f6a4d…`: its output quotes the literal `Specialists spawned:` in prose at line 9 before the real list at lines 125-131, and the existing first-match parser returns one bogus item for it. A reconciler that fails that run is a false negative, not a gate.

Outcome, not keystrokes: a reader of `settlement.json` alone must be able to tell claimed from observed, and a settlement whose observed side is unknown must read as a failure to every consumer of `SdlcSettledStatus`.

## 2. Files

Modify:
- `python/src/dotfiles_setup/lane_result.py` — add `parse_parent_thread_id`, `collect_spawn_report` [v2], and `collect_session_files` (pure, testable, no subprocess). Leave `collect_self_report` byte-identical: its first-block semantics are pinned by `tests/test_lane_result.py:61` and used by the standalone CLI.
- `python/src/dotfiles_setup/sdlc_team.py` — carry `sessions_root` in `_SupervisorPayload` (resolved at dispatch from `CODEX_HOME`, default `~/.codex`), consume the new collectors in `_write_lane_receipts`/`_supervise`, add the three settlement fields, apply the fail-closed rule, fix the dispatcher prompt.
- `schemas/sdlc-team-settlement.json` — regenerate: `json.dumps(generate_settlement_schema(), indent=2) + "\n"` reproduces the committed formatting byte-for-byte (verified); the parity test compares parsed objects.
- `tests/test_sdlc_team.py` — `:299-347` currently expects `completed` for "claims one specialist, zero child records": it BECOMES the negative arm. `:111` asserts the prompt clause this spec deletes — update it (see §4). Add the arms in §5.
- `tests/test_lane_result.py` — unit tests for the three new functions (fixtures under `tmp_path`, never `~/.codex`).
- `.claude/skills/codex-sdlc-team/SKILL.md` (`:78-100`) — one short paragraph: settlement carries claimed vs observed and fails closed.
- `.claude/rules/codex-sdlc-team.md` (`:34`) — extend that sentence by one clause; eager + budgeted (200 lines / 24,000 bytes; currently 77 lines / 3,905 bytes).
- `docs/specs/codex-sdlc-subagent-team.md` — add a short "Spawn reconciliation (2026-09-16)" subsection stating the rule and the negative arm. Do not rewrite V3/V4 (separate P1).

Do NOT touch: `lane_result.collect_observed` (agentsview; standalone CLI at `:630`), `schemas/lane-result.json` / `LaneResult`, `.codex/agents/*.toml`, anything under `.github/`.

## 3. Interfaces

In `lane_result.py` (public, added to `__all__`):

```python
def parse_parent_thread_id(log_text: str) -> str | None:
    """Return the `session id: <uuid>` value from the codex exec banner, else None.

    The banner is the first block of captured stdout: `OpenAI Codex v…`, a
    `--------` line, `key: value` lines, a closing `--------` line. Read ONLY that
    first delimited block so a `session id:` string quoted later by the model
    cannot satisfy the parse.
    """

def collect_spawn_report(report_text: str) -> CollectorOutcome:   # [v2]
    """SELF_REPORT source for the dispatcher's CLOSING `Specialists spawned:` list.

    Anchor on the LAST line matching `specialists spawned:` (case-insensitive) — the
    prompt instructs the dispatcher to END with it, and prose earlier in the report
    may quote the phrase. Parse list items after it with the existing `_AGENT_LINE`
    (skip blank lines; stop at the first non-item line once an item was seen).
    No anchor → available=False; anchor with no items → available=False; otherwise
    available=True with one node per item (name/role exactly as `collect_self_report`
    would build them).
    """

def collect_session_files(parent_thread_id: str, sessions_root: Path) -> CollectorOutcome:
    """OBSERVED source read from codex's own rollout files under ``sessions_root``.

    A child is any `rollout-*.jsonl` whose FIRST line is a `session_meta` record with
    `payload.parent_thread_id == parent_thread_id`. [v3] Each child has an OBSERVED
    IDENTITY SET = {`payload.agent_role` if present, `payload.agent_path` if present};
    node name = agent_role if present, else agent_path if present, else `payload.id`
    (the child uuid, so the child stays visible and the reconciliation names it);
    node role = `payload.agent_path` or "". Read ONLY the top-level `agent_role`/
    `agent_path` keys: the nested `source.subagent.thread_spawn.agent_role` is present
    on 0 of the 326 role-less children on this host, so it is not a fallback. Filter on
    `parent_thread_id` FIRST and type-guard every nested access: `payload.source` is a
    STRING on 2,429 of 2,740 parent records, and `payload.source.subagent` is a STRING
    on 239 of 495 children — an unguarded `.get` chain raises. NEVER use
    `payload.session_id`: on a child it holds the PARENT's uuid (449 of 495 children
    on this host). available=False only when parent_thread_id is empty or sessions_root
    is not a readable directory; a scan that ran and found nothing is available=True
    with zero agents (mirror of `test_observed_unavailable_is_distinct_from_available_empty`).
    Files whose first line is missing/unparsable/not `session_meta` are skipped and
    COUNTED in `error` text (e.g. "skipped 1 unreadable rollout file(s)") while
    available stays True — one zero-byte rollout file exists on this host today.
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
    parent_thread_id: str | None = None        # NEW — parse_parent_thread_id(codex.log)
    specialists_claimed: tuple[str, ...] = ()  # NEW — canonical roster name per claimed item, report order
    specialists_observed: tuple[str, ...] = () # NEW — observed node names (agent_role, or child id when absent), sorted

class _SupervisorPayload(codec.Struct, frozen=True):
    ...existing fields unchanged...
    sessions_root: str = ""                    # NEW — resolved in dispatch(); "" means unknown → fail closed
```

Reconciliation rule (a small pure function, unit-tested directly; module of your choice):
- IDENTITY GRAMMAR [v3]: an identity token is a string matching EITHER the roster-name grammar `^[a-z0-9][a-z0-9_-]{0,63}$` (kebab/snake names like `sdlc-python-specialist`; all 29 `name` fields in `.codex/agents/*.toml` pass) OR the agent-path grammar `^/[A-Za-z0-9_./-]{1,200}$` (`/root/config_review`). Whitespace-bearing prose (`no thread with id`, `initial spawn failed …`) is never an identity.
- Claimed identity set of a SELF_REPORT item = {its `name`} ∪ {every backticked token in its `role` text}, FILTERED by the identity grammar. Two real shapes must both work: role-first `` - `sdlc-python-specialist` — `/root/python_review` `` (identities: the role name AND the path) and path-first `` - `/root/config_pin_review` — `sdlc-config-specialist`; initial spawn failed with `no thread with id`, … `` (identities: the path AND the role token; the prose token is filtered out). An item with an EMPTY identity set can never match and yields the error `spawn reconciliation: claimed item '<raw name>' names no roster specialist or agent path`.
- [v3] A list item whose `name`, lower-cased and stripped of trailing punctuation, is `none` (the model writes `- None.` for an empty list) is NOT a claim — it contributes zero claimed items, so such a run reaches the honest `zero specialists observed` error rather than a misleading grammar error.
- [v4] PAIRING (replaces v3's set-intersection-with-"exactly one"): `agent_role` is NOT unique among siblings — 13 of 330 parent groups on this host repeat a role (`explorer`×16, `default`×14 under one parent) — while `agent_path` is never repeated (0 of 330), and no role-less child shares a roled sibling's path (0). So pair claimed items to observed children as a one-to-one assignment: walk claimed items in report order; for each, take the first UNMATCHED child whose `agent_path` equals one of the item's path identities; if none, take the first UNMATCHED child whose `agent_role` equals one of the item's role identities; a child is consumed once. Two claimed items with the same role and distinct paths pair with two same-role children by path; two claimed items with the same role and NO paths pair with two same-role children in either order. A role-less child that carries `agent_path` pairs with a claimed item naming that path (80 of the 326 role-less children carry a path, and 244 of the 326 have `originator == "codex_exec"` — our own tool's shape). A child with NEITHER role nor path has identity {uuid}, can never pair, and yields `spawn reconciliation: observed child '<uuid>' carries neither agent_role nor agent_path`.
- [v5] AMBIGUITY: a claimed item whose identity set holds MORE THAN ONE path identity or MORE THAN ONE roster-name identity is ambiguous (greedy pairing can then consume the wrong child while a valid assignment exists — verifier counterexample: item 1 backticks `/root/p1` and `/root/p2`, item 2 names only `/root/p2`). Such an item is never paired; it yields `spawn reconciliation: claimed item '<raw name>' carries more than one path or role identity` and the run fails closed. The pinned prompt format emits exactly one role and one path per item, and both real reports already do, so a well-formed report is never ambiguous.
- consistent ⇔ parent_thread_id known AND observed source available AND len(observed) ≥ 1 AND no claimed item is ambiguous AND no claimed item is left unpaired AND no observed child is left unpaired.
- inconsistent ⇒ `status = FAILED` (even when codex rc == 0) and `errors` gains one line per cause, each prefixed `spawn reconciliation:` — e.g. `parent thread id not found in codex.log banner`, `claimed 'sdlc-python-specialist' has no observed child session`, `observed child 'sdlc-config-specialist' (/root/config_review) was not claimed`, `observed child '<uuid>' carries neither agent_role nor agent_path`, `zero specialists observed under <sessions_root>`, `observed source unavailable: <reason>`, `self-report unavailable: <reason>`.
- `TIMED_OUT` stays `TIMED_OUT`; a codex rc≠0 stays `FAILED`; reconciliation only ever demotes `COMPLETED` → `FAILED`, never promotes.
- The `skipped N unreadable rollout file(s)` note lives in the receipt's CollectorOutcome.error ONLY — never in settlement `errors`, and never a cause of FAILED [v2].
- `specialists_claimed` = per claimed item, the matched observed name when matched, else the first identity-set member, else the raw `name`; `specialists_observed` = sorted observed node names. Both recorded on EVERY settlement, failed ones included.
- RECEIPT CANONICALIZATION [v2]: before `merge_sources`, rename each matched SELF_REPORT node to its matched observed name and set its role to the observed `agent_path` when the item's own name was a path; unmatched items keep their raw name. `merge_sources` keys on `name`, so without this a path-first report produces name-mismatch disagreements in the receipt even when reconciliation passes.

## 4. Constraints and invariants

- Zero-bash-logic: everything in python; no new scripts. No inline suppressions (`noqa`, `type: ignore`) — `no_lint_skip` rejects them.
- Isolated test state: fixtures build a fake `sessions_root` under `tmp_path` with hand-written `rollout-*.jsonl` files; never read `~/.codex`. Real child first line to reproduce (verified 2026-09-16): `{"timestamp": "2026-09-16T06:16:17.947Z", "ordinal": 0, "type": "session_meta", "payload": {"id": "<child-uuid>", "session_id": "<PARENT-uuid>", "parent_thread_id": "<parent-uuid>", "originator": "codex_exec", "thread_source": "subagent", "agent_role": "sdlc-python-specialist", "agent_path": "/root/python_review", "agent_nickname": "Bacon", "source": {"subagent": {"thread_spawn": {"parent_thread_id": "<parent-uuid>", "depth": 1, "agent_path": "/root/python_review", "agent_nickname": "Bacon", "agent_role": "sdlc-python-specialist"}}}, "cwd": "..."}}`. Real child files carry a SECOND `session_meta` line at ordinal 1 — read only line 1.
- Scan ALL `rollout-*.jsonl` under `sessions_root` recursively (3,236 files on this host; first-line reads only). Do NOT bound the scan by date directory: directory/filename dates are LOCAL time while the record's `timestamp` is UTC (`rollout-2026-09-16T01-16-17-…` ↔ `"timestamp":"2026-09-16T06:16:17.947Z"`) — a date bound is a false-negative hazard (`.claude/rules/probes-need-a-control-arm.md` rule 3).
- `_supervise` opens the log with `"wb"` (`sdlc_team.py:537`) and codex writes the banner as its first stdout — in tests the fake `Popen` must write the banner bytes into the `stdout` file object it receives; the existing fake at `tests/test_sdlc_team.py:319` is `lambda *_a, **_kw: child` and discards that handle, so it must change.
- Parse the parent id from the log AFTER codex exits. Do not add `--json` to the argv — the human transcript in `codex.log` is the primary evidence file #1142's investigation and the skill rely on.
- The HOOK source is always unavailable for codex runs (no Claude hooks fire; `hook_events_path` resolves to `.agent/lane-results/<run>.hooks.jsonl`, absent) and `merge_sources` reports that as a disagreement; the fail-closed rule keys on the spawn-reconciliation conditions above, NOT on "any disagreement".
- Prompt fix in `build_prompt` (`sdlc_team.py:238-244`): DELETE "If a specialist spawn fails with `no thread with id` before the agent exists, retry once without conversation history. If spawning still fails, do the work yourself and report every spawn failure." — derived from a fabricated retry (#1145) and it licenses exactly the generalist fallback this change fails. REPLACE with: "If a specialist cannot be spawned, stop and report the spawn failure with its error text; do not do that specialist's work yourself." Pin the closing list: "End with a Markdown list under `Specialists spawned:` with exactly one item per spawned specialist, each item formatted `- `<agent_role>` — `<agent_path>``, and state that no others were spawned." Keep every other prompt clause byte-identical. [v2] `tests/test_sdlc_team.py:111` asserts `"retry once without conversation history" in prompt` — change it to assert the NEW clause is present AND `"do the work yourself" not in prompt` (a fail arm on the prompt itself).
- `CODEX_HOME` resolution: `Path(os.environ.get("CODEX_HOME") or "~/.codex").expanduser() / "sessions"`, resolved in `dispatch()` and carried on the payload as a string; the supervisor never re-reads the environment. `os` is already imported (`sdlc_team.py:11`). The payload crosses the process boundary as base64-encoded argv (`sdlc_team.py:284-291`) — a longer payload is fine.
- Old on-disk `settlement.json` files (seven fields) must still decode: new fields are defaulted (verified: seven-field bytes decode into the extended struct; control arm: a missing `run_id` raises).
- `collect_observed` (agentsview 0.42.0 at a hard-coded path) is NOT wired into settlement: it is an index with unverified lag and an unverified row schema; the rollout file is codex's primary record. Leave it and its tests untouched.
- Commit message: conventional `fix(sdlc-team): …`; body states the rule, the negative arm, the v2 corrections (last-anchor parse; identity grammar), and file-captured gate rcs; end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01R3V8ff1cnaWEp1QXtmvAYC`.
- Licensed dissent applies to every premise below.

## 5. Verification

Smallest bundle, file-captured rc:

```
uv run --project python pytest tests/test_sdlc_team.py tests/test_lane_result.py -x -q > /tmp/sdlc-spawn-pytest.log 2>&1; echo "rc=$?" >> /tmp/sdlc-spawn-pytest.log
mise run lint > /tmp/sdlc-spawn-lint.log 2>&1; echo "rc=$?" >> /tmp/sdlc-spawn-lint.log
```

Required arms (each a test that fails if the change is reverted):
1. NEGATIVE (the P0 arm): output claims `` - `sdlc-python-specialist` ``, codex.log carries a banner with a session id, sessions_root has ZERO child files → `failed`, `errors` contains `spawn reconciliation: zero specialists observed`, `specialists_claimed == ("sdlc-python-specialist",)`, `specialists_observed == ()`.
2. POSITIVE: same claim, one child file with `parent_thread_id` == banner id and `agent_role == "sdlc-python-specialist"` → `completed`, `parent_thread_id` set, both tuples `("sdlc-python-specialist",)`.
3. MISMATCH: claim `sdlc-python-specialist`, observed `sdlc-config-specialist` → `failed`, two `spawn reconciliation:` errors.
4. PARENT UNKNOWN: fake codex writes no banner → `failed`, error names the missing banner; a matching child under sessions_root is NOT credited.
5. Path-first shape: item `` - `/root/config_pin_review` — `sdlc-config-specialist`; initial spawn failed with `no thread with id`, retry … `` reconciles against observed `agent_role == "sdlc-config-specialist"`; the receipt names that agent ONCE (canonicalized), and `no thread with id` never appears as an identity.
6. `parse_parent_thread_id`: banner → uuid; a log whose only `session id:` line is AFTER the closing `--------` → None.
7. [v2] REAL-SHAPE POSITIVE: output text mirrors `4e6f6a4d…/output.md` — a prose line near the top quoting `Specialists spawned:` inside a sentence, the real three-item list near the bottom followed by "No other specialists were spawned." — with three matching children → `completed`, `specialists_observed` has the three roles. Also a direct `collect_spawn_report` test showing `collect_self_report` returns the bogus first-match item on the same text while `collect_spawn_report` returns the three.
8. [v2] Zero-byte rollout file beside a valid child → still `completed`; the receipt's OBSERVED error text notes 1 skipped file; settlement `errors` is empty.
9. [v3] Child with NEITHER `agent_role` nor `agent_path` → `failed`, error names the child uuid and both missing fields.
10. [v2] Prompt: new clause present, `do the work yourself` absent.
11. [v3] Role-less child WITH `agent_path == "/root/config_pin_review"` reconciles against the path-first claimed item of arm 5 → `completed`; `specialists_observed == ("/root/config_pin_review",)`.
12. [v3] Output whose list is `- None.` (and a variant `- none`) → zero claimed items; with zero children → `failed` with the `zero specialists observed` error and NO `names no roster specialist` error.
13. [v3] Fixture root containing a parent-shaped record with `"source": "exec"` (string), a child whose `source.subagent` is a string, and a child whose `source` is a dict → the collector raises nothing and reports only the real children.
15. [v5] A claimed item backticking two paths (`` - `/root/p1` — `sdlc-python-specialist`, also `/root/p2` ``) with children at both paths → `failed` with the `more than one path or role identity` error naming the item; the sibling well-formed item still pairs.
14. [v4] Two children with the same `agent_role` (`sdlc-python-specialist`) and distinct paths (`/root/python_a`, `/root/python_b`): claimed as two role+path items → `completed`, `specialists_observed` lists the role twice; claimed as ONE item → `failed` with one `was not claimed` error naming the unpaired child; claimed as two role-only items (no paths) → `completed`.
The full suite, `mise run verify`, `mise run lint-docs` run at integration by the caller.

## 6. Commit

COMMIT: lane — commit on the current branch `fix/sdlc-team-settlement-verifies-spawn`; report the hash.

## 7. PREMISES

- L — `SdlcTeamSettlement` fields are exactly run_id, status, codex_returncode, codex_pid, finished_at, duration_s, errors — `python/src/dotfiles_setup/sdlc_team.py:103-112`
- L — `_SupervisorPayload` fields: run_id, argv, prompt_file, output_file, log_file, receipt_json, receipt_md, settlement_file, workdir, started_at, timeout_s — `sdlc_team.py:115-128`
- I — `_write_lane_receipts(payload, duration_s) -> tuple[str, ...]` builds SELF_REPORT from `output_file`, hard-codes OBSERVED unavailable ("parent session id is not carried by SdlcTeamRequest"), then `merge_sources(self_report, observed, hook)` — `sdlc_team.py:483-524` (observed stub :497-501)
- I — `_supervise` derives status solely from codex rc (`COMPLETED if returncode == 0 else FAILED`), TIMED_OUT on timeout, opens the log `"wb"` — `sdlc_team.py:527-582` (status :549-553, log :537)
- L — `dispatch()` argv is `codex exec -s <sandbox> -c model_reasoning_effort="…" -C <workdir> -o <output_file> -`, no `--ephemeral`, no `--json` — `sdlc_team.py:371-383`
- L — `build_prompt` carries the retry/do-it-yourself clause at :238-240 and the `Specialists spawned:` instruction at :243-244 — `sdlc_team.py`
- L — the payload crosses to the supervisor as urlsafe base64 of `codec.encode(payload)` — `sdlc_team.py:284-291`; `os` imported at `:11`
- I — `lane_result.AgentSource` = {SELF_REPORT, OBSERVED, HOOK}; `AgentNode(name, role="", parent=None, sources=(), status="")`; `CollectorOutcome(source, agents=(), available=True, error="")` — `python/src/dotfiles_setup/lane_result.py:41-56, 70-76`
- I — `collect_self_report(report_text)` anchors on the FIRST line matching `_SECTION_LINE` anywhere in the text — `lane_result.py:138-141`; item regex `_AGENT_LINE` at `:92-97`, section regex `:87-91`
- P — that first-match behaviour is pinned by `tests/test_lane_result.py:61` `test_self_report_collects_the_first_selected_block_with_roles`; DATA match: the same function, same regexes — hence a separate `collect_spawn_report` rather than a semantics change
- L — [v2] the real successful run's output quotes `Specialists spawned:` in prose at `.agent/sdlc-runs/4e6f6a4d042745beae6619557c630b70/output.md:9` and carries the real list at `:125-131`; `collect_self_report` on that file returns available=True with ONE item named `P1 — `4d91064`'s workflow policy loses setup/run ordering.` (run live this session)
- I — `merge_sources(*outcomes)` records "source <x> unavailable: …" (`:434`) and "agent 'n' seen by …; missing from …" per name mismatch (`:462-463`) — `lane_result.py:425-478`
- I — `collect_observed` uses the agentsview binary at a hard-coded 0.42.0 path and is called only by the standalone CLI — `lane_result.py:80-84, 250-299, 630`
- P — HOOK source is unavailable when its log is missing: `tests/test_lane_result.py:215-224`; DATA match: `hook_events_path` → `.agent/lane-results/<run>.hooks.jsonl`, absent for codex runs (checked for run `2c97f4bc`)
- L — codex exec banner: line 1 `OpenAI Codex v0.154.0`, line 2 `--------`, line 10 `session id: 01a0a8da-6d39-74e3-a8fc-fe66f5505378`, line 11 `--------`, line 12 `user` — `.agent/sdlc-runs/4e6f6a4d042745beae6619557c630b70/codex.log:1-12`
- L — child rollout first line: `type: session_meta`, payload keys include `id`, `session_id`, `parent_thread_id`, `thread_source`, `agent_role`, `agent_path`, `agent_nickname`, `originator`, `cwd`, `source.subagent.thread_spawn.{parent_thread_id, depth, agent_path, agent_nickname, agent_role}` — `~/.codex/sessions/2026/09/16/rollout-2026-09-16T01-16-17-01a0a8db-de4d-7c93-a96f-8d001939aecd.jsonl:1` (+ two siblings, same shape); the parent's first line has `parent_thread_id: null`, `source: "exec"` — `rollout-2026-09-16T01-14-43-01a0a8da-6d39-74e3-a8fc-fe66f5505378.jsonl:1`
- L — the same child file's line 2 is ALSO `type: session_meta` (ordinal 1) — direct read of `…01a0a8db-de4d….jsonl:2`
- L — [v2] corpus measurement over the first line of all 3,236 rollout files this session: 495 children (`parent_thread_id` set); 326 have NO `agent_role`, 169 have one; 449 of 495 have `session_id == parent_thread_id`; `thread_source` is `subagent` for all 495; 1 file unparsable
- L — [v3] of the 326 role-less children: 0 carry `source.subagent.thread_spawn.agent_role`, 80 carry `agent_path`, 246 carry neither (type-guarded count over the same first lines, this session)
- L — [v3] `payload.source` is a str on 2,429 parent records and a dict on 311; a dict on all 495 children; `payload.source.subagent` is a str on 239 children and a dict on 256 (same count) — an unguarded `.get` chain raised `AttributeError` on the first probe this session
- L — [v3] `_AGENT_LINE` live results this session: `- None.` → item name `None.`; `- none` → `none`; `- No other specialists were spawned.` and the bare `No other specialists were spawned.` → no match (so the closing terminator ends the list); the two real item shapes parse to (`sdlc-python-specialist`, role `` `/root/python_review` ``) and (`/root/config_pin_review`, role `` `sdlc-config-specialist`; initial spawn … ``)
- L — [v4] sibling uniqueness over the same first lines this session: 330 parent groups; 13 repeat an `agent_role` among children (e.g. `explorer`×16 + `default`×14 + `worker`×5 under one parent); 0 repeat an `agent_path`; 0 role-less children share a roled sibling's path
- L — [v3] all 29 `.codex/agents/*.toml` `name` fields match `^[a-z0-9][a-z0-9_-]{0,63}$` (tomllib read this session); filenames carry a `codex-` prefix the `name` fields do not
- L — [v2] the unparsable file is zero bytes: `~/.codex/sessions/2026/04/16/rollout-2026-04-16T16-14-05-019d9824-dcb7-7fb2-bba5-066ee60efbdf.jsonl` (`find -size 0`)
- L — real self-report shapes: role-first `` - `sdlc-python-specialist` — `/root/python_review` `` — `4e6f6a4d…/output.md:125-131`; path-first `` - `/root/config_pin_review` — `sdlc-config-specialist`; initial spawn failed … `` — `.agent/sdlc-runs/2c97f4bcd31443dd9ad598f4cce08dd0/output.md:134-140`
- L — `CODEX_HOME` defaults to `~/.codex` and roots Codex state — `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/codex/config-file__environment-variables.md:17`, `config-file__config-advanced.md:71`
- L — filename/dir dates are local while the record `timestamp` is UTC: `rollout-2026-09-16T01-16-17-…` has `"timestamp":"2026-09-16T06:16:17.947Z"` — same child file, line 1
- I — the supervisor test builds `_SupervisorPayload(...)` by keyword, fakes `Popen` with `lambda *_a, **_kw: child` (stdout handle discarded), and asserts `COMPLETED` for a one-specialist claim with no child records — `tests/test_sdlc_team.py:299-347` (fake at :319)
- L — [v2] `tests/test_sdlc_team.py:111` asserts `"retry once without conversation history" in prompt`; the prompt-assertion block is `:105-115`
- I — committed-schema parity: parametrize `tests/test_sdlc_team.py:454-461`, test `:462-470`, compares parsed JSON; `json.dumps(schema, indent=2) + "\n"` reproduces the committed bytes (verified; indent=4 does not); no mise task regenerates it (`mise.toml:280` is the only `sdlc` task)
- L — [v2] seven-field settlement bytes decode into the extended struct (defaults fill); a missing `run_id` raises (control arm) — verified live against `codec.decode`
- L — [v2] no gate greps the changed files: zero hits for `sdlc_team`/`lane_result` in `python/verification/suites.toml` and `hk.pkl`; `.claude/rules/codex-sdlc-team.md` is 77 lines / 3,905 bytes against 200 / 24,000
- E — `SdlcTeamSettlement.parent_thread_id` ← `parse_parent_thread_id(codex.log)`; UUID string or None; bounded (36 chars); not PII
- E — `SdlcTeamSettlement.specialists_claimed` ← names derived from the model's closing list (identity-set member or raw item name); model-authored text, so the raw fallback can be ANY string — bounded per item by `_AGENT_LINE`; not PII by design but not guaranteed
- E — `SdlcTeamSettlement.specialists_observed` ← `payload.agent_role`, else `payload.agent_path`, else child `payload.id` of child session_meta records; codex-authored roster names / `/root/<name>` paths / uuids; bounded; not PII
- E — `SdlcTeamSettlement.errors` gains `spawn reconciliation: …` lines ← composed by our code from the above plus `sessions_root` (an absolute path under the user's home — a path, not a secret; never file CONTENTS or model prose beyond the raw item name)
- E — lane receipt OBSERVED nodes ← the new collector (name=agent_role, else agent_path, else child id; role=agent_path); SELF_REPORT nodes canonicalized to matched names; receipt `error` text carries the skipped-file count
- A — codex 0.154.0's banner format (`session id:` key, `--------` delimiters) is stable across the patch versions this repo pins; held because it is observed on the pinned version and no doc describes the exec banner. If it changes, the parse fails closed (settlement `failed`, error names the missing banner) — the safe direction.
