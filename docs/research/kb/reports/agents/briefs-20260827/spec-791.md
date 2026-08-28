# Spec — #791 writer-lease recovery, full fix set

Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles. Branch `fix/791-writer-lease-recovery` is checked out; HEAD `6755fd5` is the cherry-pick of PR #759 (HMAC challenge + receipt redaction) — build on it. Read the repo's `AGENTS.md` and `python/AGENTS.md` and `tests/AGENTS.md` first; they bind.

## 1. Objective

A Claude or Codex session that finds the repository writer lease wedged — a holder (live or dead) owned by ANOTHER session, with in-flight entries nobody will ever drain — must be able to recover from INSIDE the session using only the pinned `mise run writer-lease-*` commands: no hand-fed JSON to the hook runner, no hunting processes by pid, no `kill -9`.

The failure this prevents happened twice on 2026-08-27 (issue #791): a session could run NO mutating tool for ~1h because
(a) the pre-ownership bootstrap allowlist admits only `--owner codex:<session>` — a Claude session can run `writer-lease-status` and nothing else;
(b) no verb can drain an orphaned in-flight entry, and both release (`_release_when_drained`) and transfer (`_derive_transition`) block on it forever;
(c) `status` hides the holder pid/port a human needs to find the holder;
(d) entries LEAK in normal operation — measured today with a control arm: a mutating call that a sibling PreToolUse hook DENIES (e.g. `hook_guard`) is registered by the lease PreToolUse and never gets a Post; a harness-backgrounded Bash does NOT leak (it drains). Four of six old entries were calls executed while the PostToolUse hooks were temporarily unwired;
(e) the pinned `writer-lease-status` bootstrap itself trips a PostToolUse `{"continue": false}` ("tool completion has no matching in-flight mutation") because the Pre side is exempted from registration but the Post side is not.

Outcomes that must become true (the implementer chooses mechanism except where a constraint pins it):

- **O1 — bootstrap allowlist.** `_bootstrap_command` admits `--owner claude:{session_id}` exactly as it admits `codex:{session_id}` (`--task-id` must still equal the hook `session_id`). It also admits the new drain verb's exact argv shapes pre-ownership (see Interfaces) — the whole point is that a session that does NOT own the lease can run it.
- **O2 — `writer-lease drain` verb** (CLI `dotfiles-setup writer-lease drain`, mise task `writer-lease-drain`):
  - `--tool-use-id ID` (repeatable): finish that in-flight entry on behalf of its RECORDED identity — the entry's own `session_id` and `tool_name` — producing exactly what the originating PostToolUse would have produced (a `tool_finished` audit event; entry removed; one generation published). An id with no entry → `LeaseError`, rc 2, nothing published.
  - `--completed`: for every in-flight entry, look for EVIDENCE that the call is over: the registering session's Claude Code transcript records a `tool_result` block whose `tool_use_id` equals the entry id. The harness writes a result for executed AND denied calls (see PREMISES I8), so this clears the deny-leak class too. Evidence found → drain it (same transaction as above). No evidence → keep it and report why: `"no transcript for session"` or `"no result recorded yet"`. Transcript location: reuse `dotfiles_setup.command_audit` — `transcripts_base()` (env-aware, `CLAUDE_CONFIG_DIR`), `project_dir(base, worktree)`, root `<session_id>.jsonl` plus nested `<session_id>/**/*.jsonl` (the shape `project_transcripts` documents), `_json_lines`, `_content_blocks`. Do not re-implement those. (The hook payload's `transcript_path` is NOT usable here: `drain` is CLI-invoked at recovery time, when no hook payload exists, so the path is reconstructed from the entry's `session_id` — PREMISES A1.)
  - Output: one canonical JSON line on stdout — `{"drained": [ids...], "kept": {id: reason, ...}}` — via the existing `_canonical_bytes`. Rc 0 whether or not anything was drained (it is a report, not a gate); rc 2 on `LeaseError`.
  - Works whether the holder is live or dead, and whether or not the caller owns the lease. Never touches the flock, the receipt, or the holder process. Never prints transcript content, only ids and reasons.
  - No `--all` / `--force`: an entry with no evidence is drained only by an explicit `--tool-use-id` (a human decision, audited as such).
- **O3 — `status` surfaces what recovery needs.** Add `holder_pid` (← receipt `pid`), `holder_port` (← receipt `holder_port`) and `inflight_entries` (← `{id: {"session_id", "tool_name", "started_at"}}`). Keep the existing `inflight` sorted-id list unchanged (tests read it). `holder_token` must never appear in `status` output (nor anywhere new).
- **O4 — the wait names its remedy.** `_derive_transition`'s in-flight refusal message ends with the hint `run: mise run writer-lease-drain -- --completed`, and the holder prints ONE stderr line when release is requested while `inflight` is non-empty — the ids and the same hint — not one line per 50 ms poll.
- **O5 — Post exemption mirrors Pre.** In `hook_decision`, a `PostToolUse` / `PostToolUseFailure` for a `Bash` whose `tool_input.command` is a bootstrap command (`_bootstrap_command(...)` true — status, hold, or drain shapes) returns `None`, so the pinned bootstraps never produce `{"continue": false}`. Real mismatches (a non-bootstrap Post with no entry) keep raising as today.
- **O6 — docs, task, contract.** `.claude/rules/writer-lease.md`: owner is `claude:` or `codex:` (both bootstrap forms shown), the drain verb, and the recovery ORDER (`writer-lease-status` → `writer-lease-drain -- --completed` → holder Ctrl-C → `writer-lease-hold` with `--expected-prior-receipt-sha256` from status). `docs/specs/codex-writer-lease.md`: public interface gains `drain`; the "Recovery sequence" paragraph that says a human must hand-feed/investigate is rewritten to "evidence-drained via `drain --completed`; an evidence-less entry needs an explicit `--tool-use-id`"; add one sentence naming the sibling-hook deny leak as the documented residual and why (fail-closed registration is kept on purpose). `mise.toml`: `[tasks.writer-lease-drain]` beside the three existing tasks. `python/verification/suites.toml` `workflow.writer-lease` `per_path_tokens` gains: mise.toml `"[tasks.writer-lease-drain]"`, writer_lease.py `"def drain("`, tests the exact `def test_...(` line of the drain test. Prove each new token binds exactly once with `mise run token-check -- <file> "<token>"` before committing (skill `token-check`; a token matching twice can be satisfied by a stand-in).

## 2. Files

Modify:
- `python/src/dotfiles_setup/writer_lease.py`
- `python/src/dotfiles_setup/main.py` (`_add_writer_lease_subcommand` :1424-1453; nothing else)
- `mise.toml` (new task next to :662-672)
- `python/verification/suites.toml` (`workflow.writer-lease`, :2132-2155)
- `.claude/rules/writer-lease.md`, `docs/specs/codex-writer-lease.md`
- `tests/test_writer_lease.py` (append tests; reuse the existing helpers — PREMISES P1)

Do NOT touch: `scripts/writer-lease-hook-runner.py`, `.codex/hooks.json`, `.claude/settings.json`, `python/src/dotfiles_setup/codex_writer_lease_hook.py`, `python/src/dotfiles_setup/hook_guard.py`, `AGENTS.md` (it is at its 12,000-char cap).

## 3. Interfaces

- `def drain(cwd: Path, *, tool_use_ids: Sequence[str], completed: bool, transcripts_base: Path | None = None) -> int` in `writer_lease.py`. `transcripts_base=None` → `command_audit.transcripts_base()`; injected by tests. Argparse rejects a call with neither `--tool-use-id` nor `--completed`.
- `_bootstrap_command` admitted argv shapes (`prefix = [mise, "-C", worktree, "run"]`, unchanged):
  - `[*prefix, "writer-lease-status"]`
  - `[*prefix, "writer-lease-hold", "--", <today's option rules>]` with `--owner` ∈ {`codex:{sid}`, `claude:{sid}`}
  - `[*prefix, "writer-lease-drain", "--", "--completed"]`
  - `[*prefix, "writer-lease-drain", "--", "--tool-use-id", <id>]` — one id per bootstrap invocation; `<id>` must match `^[A-Za-z0-9_-]{1,128}$`. Anything else (extra flags, two ids, env prefix, bare `mise`) stays denied.
- CLI: `dotfiles-setup writer-lease drain [--tool-use-id ID]... [--completed]`; `writer_lease_main` dispatches `"drain"`.
- `status` payload: today's keys plus `holder_pid: int`, `holder_port: int`, `inflight_entries: dict[str, dict[str, str]]`.

## 4. Constraints and invariants

- **HARD — the wire protocol and on-disk schemas are frozen.** Do not change `_HolderServer._serve` (:243-281), `_challenge_holder` (:1490-1504, post-#759 shape), `_lock_token` (:1457-1463), `SCHEMA`, `_RECEIPT_KEYS` / `_AUDIT_KEYS` / `_INFLIGHT_KEYS` / `_LOCK_TOKEN_KEYS` / `_AUDIT_EVENTS` (:41-106), or the canonical bytes of any state file. Reason, measured today: hooks execute WORKING-TREE code while a live holder keeps running the code it started with; a protocol change under a live holder made every hook report `receipt is not bound to the live holder` and wedged the session. The drain must express itself with the existing `tool_finished` event — no new audit event kind.
- Fail-closed posture is unchanged: no hook-wiring edits. A sibling PreToolUse deny still leaks an entry; that is a documented residual cleared by `drain --completed`, not something to "fix" by weakening registration.
- ONE finish path: `drain --tool-use-id` reads the entry, then runs the same finish transaction `_finish_tool` runs (supplying the entry's recorded `session_id`/`tool_name`), so the audit/inflight invariant (`_validate_history` :838-840 byte-compares them) cannot diverge. Do not add a second deletion path. Keep `_finish_tool`'s identity check (:1963-1965) intact for hook-driven completions.
- `drain` reads transcripts read-only, tolerates malformed lines (the `command_audit` helpers already do), and must not follow the transcript into printing anything but ids/reasons.
- Never print `holder_token` (the loopback secret, `os.urandom(32).hex()` at :1695) anywhere new; `status` must not gain it.
- Repo conventions: zero inline suppressions (`noqa`/`type: ignore` are rejected by hk); PEP 758 comma-except style is the repo norm and ruff enforces it; no new dependencies; no bash (`.claude/rules/zero-bash-logic.md`); serialization via existing `_canonical_bytes`; `uv run --project python` never `--directory`; lint via `mise run lint` (never raw `hk`); `.claude/rules/writer-lease.md` is an unscoped rule under the `md_size_budget` gate (≤200 lines / 24,000 bytes) — keep the added prose tight.
- Tests (repo `tests/AGENTS.md` binds): real-subprocess style like the existing suite; isolated `tmp_path` repos via `_repo_with_linked_worktree`; fake transcripts under a `tmp_path` base injected as `transcripts_base` (and/or `CLAUDE_CONFIG_DIR`); every assertion must fail if the change is reverted; no wall-clock timing beyond the existing `_READY_TIMEOUT_SECONDS` readiness pattern; never mock our own modules.
- Contract tokens the doc edits must KEEP verbatim (`workflow.writer-lease` `per_path_tokens`): in `.claude/rules/writer-lease.md` — `# Repository writer lease`, `immutable, content-addressed 64-event chunks`, `` `PostToolUseFailure` drains failed tools ``; in `docs/specs/codex-writer-lease.md` — `fcntl.flock(fd, LOCK_EX | LOCK_NB)` (:32), `Pinned Python: exactly one complete runtime` (:141), `Immutable content-addressed 64-event chunks` (:153), `--dangerously-bypass-hook-trust` (:133). None sits inside the "Public interface" block (:64-93) or the "Recovery sequence" prose (:202-205) you rewrite — do not touch the mermaid node lines that carry them.
- The rule file today (`.claude/rules/writer-lease.md`) shows only the codex owner form and the `<absolute-home>/.local/bin/mise` / `/usr/local/bin/mise` paths; keep those facts, add the claude form and the drain verb.
- Commit: conventional `fix(agents): …` subject; body lists O1–O6 briefly and cites #791; author/committer as configured.

## 5. Verification

Producer dev loop (the command whose captured output is the evidence):

    uv run --project python pytest tests/test_writer_lease.py -x -q

New real-process tests that MUST exist and pass (names are yours; behaviour is not):
- (a) bootstrap: the hook admits `writer-lease-hold` with `--owner claude:<sid>` and both drain shapes for a session that does NOT own the lease; still denies `--owner other:<sid>`, a second `--tool-use-id`, and an `env` prefix.
- (b) leak → drain → transfer: a raw `PreToolUse` with no `PostToolUse` leaves an entry; `hold` from a successor refuses with the in-flight message (and the message contains `writer-lease-drain`); `drain --tool-use-id <id>` clears it; the same `hold` then succeeds (`transition` derived, not asserted).
- (c) evidence drain: two leaked entries A and B under session S; a fake transcript `<base>/<encoded worktree>/S.jsonl` holds a `tool_result` for A only (and a nested `S/subagents/x.jsonl` variant is fine to include); `drain --completed` reports `drained == [A]` and `kept == {B: "no result recorded yet"}`; an entry whose session has no transcript file is kept with `"no transcript for session"`.
- (d) status: `holder_pid == receipt["pid"]`, `holder_port == receipt["holder_port"]`, `inflight_entries[id]` carries `session_id`/`tool_name`/`started_at`, and the substring `holder_token` is absent from status stdout.
- (e) Post exemption: `_raw_hook` PostToolUse for a Bash whose command is the pinned status bootstrap returns no `"continue": false`; a non-bootstrap Post with no entry still does.

Then the full gate, each rc recorded in the report: `mise run lint` (rc=0), `uv run --project python pytest tests/ -x -q`, `mise run verify`, `mise run lint-docs`.

Control arms to report (run them, then restore): revert O5 and show (e) fails; delete the `"drain"` dispatch branch in `writer_lease_main` and show (b)/(c) fail.

## 6. Commit

lane. One commit on `fix/791-writer-lease-recovery`.

## 7. PREMISES

- L1 `MUTATION_TOOLS = frozenset({"Bash", "apply_patch", "Edit", "Write", "NotebookEdit"})` — writer_lease.py:51
- L2 `_INFLIGHT_KEYS = frozenset({"receipt_sha256", "session_id", "started_at", "tool_name"})` — writer_lease.py:105; entries keyed by tool_use_id, written inside `_begin_tool` (:1881-1936, the `inflight[tool_use_id] = {...}` block)
- L3 `_RECEIPT_KEYS` includes `holder_port`, `holder_token`, `pid` — writer_lease.py:73-90; receipt built by `_new_receipt` :1432-1454 with `"holder_port": holder.port` (:1444), `"holder_token": holder.token` (:1445), `"pid": os.getpid()` (:1448)
- L4 `_STATE_LOCK_RETRY_SECONDS = 3.0` — writer_lease.py:58; the HOLDER's release loop polls with `time.sleep(0.05)` — :1679 (this is `_release_when_drained`, not anything the drain verb waits on)
- L5 Claude Code transcripts are "written asynchronously and may lag the in-memory conversation" — knowledge-base `sources/agent-harness-docs/docs/claude-code/hooks.md:704`; hence `drain --completed` is eventual
- I1 `_bootstrap_command(command, identity, session_id) -> bool` — writer_lease.py:1856-1878; status admitted by the `arguments == [*prefix, "writer-lease-status"]` branch; hold admitted only when `values["--task-id"] == session_id and values["--owner"] == f"codex:{session_id}"` at :1876-1878; options parsed by `_bootstrap_options` :1824-1842 (lengths 6 or 8, keys `--expected-prior-receipt-sha256|--handoff-sha256|--owner|--task-id`)
- I2 `_finish_tool(identity, *, session_id, tool_name, tool_use_id) -> None` — writer_lease.py:1938-1984; "tool completion has no matching in-flight mutation" :1961; "tool completion identity does not match its in-flight mutation" :1964; publishes `tool_finished` and removes the entry in the tail of the function
- I3 `hook_decision(payload) -> str | None` — writer_lease.py:2019-2052; Pre-only bootstrap exemption is the `invocation.event == "PreToolUse" and invocation.tool_name == "Bash" and ... _bootstrap_command(...)` branch (:2025-2035); Post events call `_finish_tool` (:2043-2049); every `LeaseError` becomes "Writer lease denied this tool call: …" (:2050-2051); the runner turns a Post denial into `{"continue": false, "stopReason": …}` — scripts/writer-lease-hook-runner.py:26-27
- I4 `writer_lease_main(args, cwd) -> int` dispatches only hold/check/status — writer_lease.py:2082-2108; argparse `_add_writer_lease_subcommand` — main.py:1424-1453; dispatch entry main.py:2171
- I5 `status(cwd) -> int` — writer_lease.py:1759-1803; payload keys in the present-branch dict (:1790-1801); `"inflight": sorted(snapshot.inflight)` :1794; liveness `_holder_is_live` :1782; receipt available as `snapshot.receipt`
- I6 `_derive_transition(prior, expected_prior_receipt_sha256)` refuses on `prior.inflight` with "prior writer still has in-flight mutation tools; drain them before transfer" — writer_lease.py:1403-1429, message literals at :1423-1426
- I7 `_release_when_drained(state_dir, lease_fd, snapshot, request)` loops forever while `current.inflight` is non-empty — writer_lease.py:1644-1679; SIGINT/SIGTERM only set the event — `_release_signals` :1631-1642; `hold` :1682-1728 blocks on `release_requested.wait()` (:1723) then calls it
- I8 `command_audit.transcripts_base(env=None, home=None) -> Path` (:213-221), `encode_cwd` (:224-226), `project_dir(base, cwd)` (:229-231), `project_transcripts(base, cwd, *, limit)` (:234-271, root `<sid>.jsonl` + `rglob` under `<sid>/`), `_json_lines(path)` (:289-305), `_content_blocks(obj)` (:308-311); `tool_result` blocks carry `tool_use_id` (:341-344); a permission-refused call still produces a result line, with `toolUseResult` a str (:315-330) — command_audit.py
- I9 `_publish_generation(state_dir, receipt, audit, inflight, *, prior)` and `_event(audit, AuditEvent(...))` are the publish/audit seams `_finish_tool` uses — writer_lease.py:1364-1381, :1384-1400, and the tail of `_finish_tool` (:1966-1984)
- I10 `_hook_fields(payload)` reads `tool_input` for EVERY event (`payload.get("tool_input")` :1996) and passes it into `HookInvocation` (:2009-2016), so a Post branch of `hook_decision` can evaluate `_bootstrap_command` on `invocation.tool_input` exactly as the Pre branch does; the existing tests already send `tool_input` + `tool_use_id` on Post payloads — tests/test_writer_lease.py:287-308 (`_raw_hook`) and :1127-1136
- I11 `_begin_tool` calls `_owned_snapshot(identity, task_id=session_id, handoff_sha256=None)` (:1898-1902) before anything else, so a mutating Bash from a NON-owning session is denied ("live lease task identity does not match", `_owned_snapshot` :1552-1554) unless `hook_decision`'s bootstrap exemption (:2025-2035) short-circuits first — this is why O1/O2's bootstrap admission is the only in-session recovery path
- I12 The two Claude PreToolUse hooks are INDEPENDENT processes — `.claude/settings.json:40-50` (lease runner, matcher `Bash|Edit|Write|NotebookEdit`) and `:51-60` (`pretooluse-guard.sh`, which reaches `writer_lease.pretooluse_decision` only after its own rules pass, hook_guard.py:802-813) — so a guard deny does not stop the runner from registering the tool-use: the deny-leak mechanism behind objective (d)
- P1 Real-process test helpers: `_repo_with_linked_worktree` (:145-156), `_lease_command` (:159-177), `_start_holder` (:180-208), `_stop` (:211-215), `_status` (:218-229), `_raw_hook`/`HookCall` (:287-308, :42-50), `holders` fixture (:348-353) — tests/test_writer_lease.py. DATA match: `test_recovery_refuses_inflight_until_write_stdin_completion_drains_it` (:1078) already drives a real holder, a raw Pre without Post, a refused successor `hold`, and a Post that drains — the same inputs the new (b) test needs with `drain` substituted for the Post
- P2 `workflow.writer-lease` contract — python/verification/suites.toml:2132-2155; `per_path_tokens` binds e.g. mise.toml `"[tasks.writer-lease-hold]"`, writer_lease.py `"def hook_decision("`, `"def writer_lease_main("`, and test `def` lines. DATA match: the new tokens are the same kinds (a task header, a `def` line)
- P3 mise tasks `writer-lease-hold|check|status` — mise.toml:662-672, each `uv run --project python dotfiles-setup writer-lease <op>`
- E1 status emits `holder_pid` ← receipt `pid` (int, the holder process) and `holder_port` ← receipt `holder_port` (int, loopback port); bounded ints, no PII. `holder_token` (64-hex secret, :1695) is never emitted
- E2 status emits `inflight_entries` ← inflight.json entries: `session_id` (harness session UUID / Codex thread id — a local identifier, not a credential), `tool_name` ∈ MUTATION_TOOLS, `started_at` ISO-8601; bounded by the number of leaked entries
- E3 drain emits `{"drained": [...], "kept": {...}}` ← ids from inflight.json and reasons from the fixed pair {"no transcript for session", "no result recorded yet"}; never transcript content
- E4 the refusal message (I6) and the holder's single stderr wait line embed in-flight ids plus the fixed hint string `run: mise run writer-lease-drain -- --completed`; ids only
- E5 (measured, the evidence class `drain --completed` rests on) A HOOK-denied Claude Code call still gets a `tool_result` block carrying its `tool_use_id`, with the line-level `toolUseResult` a str holding the deny reason: this session paired session e0d8343b's two guard-denied leaked ids (`toolu_017wu13dDjoow6e6VwxyEpG2` → `str:Error: Do not pipe a gate command into tail/head…`, `toolu_01AoptctHS9r4kx73BPjv9kp` → `str:Error: Do not hand-roll gh pr checks --watch…`) 2/2 in `~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/e0d8343b-27ee-424f-85dc-e4c3886a8b2e.jsonl` (scratchpad `scan_leaked.py`, control: the same parser saw 489 tool_use / 489 tool_result blocks), and this session's own guard-denied probe `toolu_01VR5fGxMksbNexW7jjJGhgH` has a `"tool_use_id":"toolu_01VR5f…"` result line in `ad30e818-09f6-47c5-9e0a-57208e0dcfec.jsonl`. command_audit.py:315-330 records the same shape as a docstring probe (80 refusals, all non-dict). The same session measured the negative arm: a harness-backgrounded Bash (`run_in_background: true`) did NOT leak — its Post drained normally
- A1 A Claude Code hook `session_id` equals the transcript stem under `<transcripts_base>/<encode_cwd(worktree)>/` — held because today's six leaked ids were all found in `<session>.jsonl` at exactly that path (6/6), and command_audit.py:12-17 documents the layout; the harness does not promise it as a stable contract
- A3 Codex `transcript_path` is explicitly unstable (knowledge-base codex/hooks.md:398-400 — "not a stable interface for hooks and may change"; nullability is NOT stated there and is not relied on) — Codex-registered entries are not evidence-drainable and stay `kept` with "no transcript for session"; explicit `--tool-use-id` remains their path
- A4 Subagent tool calls carry the parent `session_id` in hook payloads — held because today's leaked ids from the old session were all in the ROOT transcript; nested transcripts are still searched (I8) so the assumption is not load-bearing for correctness
