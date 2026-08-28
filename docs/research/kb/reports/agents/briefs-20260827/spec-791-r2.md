# Spec — #791 respec round 1 (on top of commit af7a9e1)

Repo /Users/rmanaloto/dev/github/ray-manaloto/dotfiles, branch `fix/791-writer-lease-recovery`, HEAD `af7a9e1` (the round-0 implementation of /private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/ad30e818-09f6-47c5-9e0a-57208e0dcfec/scratchpad/spec-791.md — read that spec first; everything in it still binds, especially section 4's HARD constraint that the wire protocol and on-disk schemas are frozen). This round fixes confirmed cold-review findings (report: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/cold-read-791-opus-20260827.md — H1, H2, H3, M5, M9, L10; the others were refuted or accepted as design and need no change).

## 1. Objective

The recovery verb must find a leaked entry's evidence regardless of WHICH worktree or subdirectory the registering session was launched from (H1); an owner whose genuinely-running tool was drained out from under it by another session must not have its session stopped when its own PostToolUse arrives (H2); and `drain` must always report what it did, even when one entry's finish transaction fails mid-run (H3). Plus three small hardenings (M5, M9, L10).

Outcomes:

- **R1 (H1) — evidence lookup is session-keyed, not worktree-keyed.** `command_audit.session_result_ids` locates a session's transcripts by SESSION ID across every project directory under the transcripts base: root `<base>/*/<session_id>.jsonl` and nested `<base>/*/<session_id>/**/*.jsonl` (session ids are UUIDs / thread ids, unique across projects). Drop the `cwd` parameter; `drain` no longer passes the worktree. `None` still means "no transcript anywhere". Test (c) must place the transcript under a project directory that is NOT the worktree's encoding (e.g. `<base>/-some-other-project/<sid>.jsonl`) and prove the entry drains — that is the H1 regression arm.
- **R2 (M5) — a session id is validated BEFORE it becomes a path or glob component.** In `_drain_reason`, a `session_id` not matching `^[A-Za-z0-9_-]{1,128}$` is never passed to `session_result_ids` (R1's glob treats `*?[` as metacharacters, and `_hook_fields` only requires a non-empty string, so an on-disk id is unconstrained): the entry is kept with the fixed reason `"session id is not a safe path component"`. The guard precedes the lookup — that ordering is part of the contract. Add the reason to the docs' reason list.
- **R3 (H2) — a PostToolUse / PostToolUseFailure with NO matching in-flight entry is a no-op.** In `_finish_tool`, `entry is None` returns without raising or publishing (the mutation has already happened; a stop protects nothing and wedges a healthy owner whose entry was drained by a third party). The identity-mismatch case (an entry exists but `session_id`/`tool_name` differ) KEEPS raising. Accepted consequence, state it in the docstring: if a third party finishes an entry between `drain`'s snapshot and its `_drain_one`, that `_drain_one` is now a silent no-op and `drain` still reports the id as `drained` — the entry IS gone, which is what the caller asked for. Test (e) changes accordingly: keep the bootstrap `exempt` arm as an OUTCOME check (it no longer isolates the exemption mechanism — say so in its docstring); add a positive arm — a Post for a NON-bootstrap Bash command with no entry returns no output — and make the negative arm an identity mismatch (register an entry under session A, send the Post as session B → `{"continue": false}`). The bootstrap-command Post exemption from round 0 stays as is (redundant but harmless) — do not widen or remove it.
- **R4 (H3 + M9) — `drain` always reports, with FIXED reasons only.** Read the snapshot under the shared state lock (as `status` does), release it, then act. Wrap each `_drain_one` call in `try/except LeaseError`: on failure `kept[tool_use_id] = "finish transaction failed"` (fourth fixed reason) and write ONE stderr line `writer-lease: <tool_use_id>: <exc>` for the detail (a `LeaseError` message can carry a state path and OS error text — that belongs on stderr, never in the JSON contract); continue with the next entry. The `{"drained": [...], "kept": {...}}` line is always written; rc stays 0 (rc 2 only for the up-front `LeaseError`s: no state, unknown explicit id, no mode given). The JSON contract therefore stays "IDs and fixed reasons, never transcript content" — `docs/specs/codex-writer-lease.md:99` remains true and just gains the two new reasons.
- **R5 (L10) — the holder's one-time stderr wait line is written OUTSIDE the exclusive state lock** (set a flag inside the `with`, write after it).
- **R6 — docs.** `.claude/rules/writer-lease.md` and `docs/specs/codex-writer-lease.md`: (i) the two new kept reasons (`session id is not a safe path component`, `finish transaction failed`); (ii) one sentence that an explicit `--tool-use-id` on a LIVE holder's still-running tool is the caller's judgment call — the owner's later Post is then a no-op, so the risk is a concurrent writer transferring in while that tool still runs, not a stopped session; (iii) `drain` reports a per-entry finish failure as `kept` with the fixed reason and the detail on stderr. Keep every contract token listed in the round-0 spec verbatim.

## 2. Files

- `python/src/dotfiles_setup/command_audit.py` (`session_result_ids` signature + lookup)
- `python/src/dotfiles_setup/writer_lease.py` (`_drain_reason`, `drain`, `_finish_tool`, `_release_when_drained`)
- `tests/test_writer_lease.py` (tests (c) and (e) amended as above; add nothing else unless a change needs an arm)
- `.claude/rules/writer-lease.md`, `docs/specs/codex-writer-lease.md`
- Do NOT touch anything the round-0 spec forbids; do not change `main.py`, `mise.toml`, `suites.toml` (no new tokens needed; `def drain(` and the test names stay).

## 3. Interfaces

- `def session_result_ids(base: Path, session_id: str) -> set[str] | None` (cwd parameter removed; update its docstring and the one call site).
- `_drain_reason(base, recorded, entry, tool_use_id)` (worktree parameter removed) or equivalent — the implementer chooses; the observable contract is the JSON output.
- Fixed kept reasons (the complete set): `"no transcript for session"`, `"no result recorded yet"`, `"session id is not a safe path component"`, `"finish transaction failed"`.

## 4. Constraints and invariants

- All round-0 constraints (frozen protocol/schemas, one finish path via `_finish_tool`, no `holder_token` output, zero suppressions, `uv run --project python`, `mise run lint` only, tests real-process and revert-sensitive).
- `_finish_tool`'s no-op MUST NOT publish a generation or append an audit event (nothing happened).
- The shared-lock read in `drain` must not hold the lock across the finish transactions (each `_drain_one` takes the exclusive lock itself) — read, release, then act.

## 5. Verification

- `uv run --project python pytest tests/test_writer_lease.py -x -q` (all pass; expect ~2 min).
- Then the gate with rc read from files: `mise run lint`, `uv run --project python pytest tests/ -x -q` (the pre-existing host failure `tests/test_process_env.py::test_real_pre_push_poison_cannot_modify_outer_repository` — `~/.local/bin/env` not executable, #792 — is known; report it and re-run with it deselected), `mise run verify`, `mise run lint-docs`.
- Control arms to report: revert R1 (look up under the worktree only) → amended test (c) fails; revert R3 (`entry is None` raises again) → test (e)'s NON-bootstrap no-entry arm fails while its identity-mismatch arm still passes (the bootstrap `exempt` arm is expected to keep passing under this revert — it is covered by the round-0 exemption, which is why it is an outcome check, not the control).

## 6. Commit

lane — one follow-up commit on the branch, `fix(agents): …` subject, body naming R1–R6 and the cold-read findings by id; cite #791.

## 7. PREMISES

- I1 `_finish_tool` — writer_lease.py (moved by round 0; find by `def _finish_tool(`): reads the snapshot under the exclusive state lock, `entry = snapshot.inflight.get(tool_use_id)`, raises "tool completion has no matching in-flight mutation" when `entry is None` and "tool completion identity does not match its in-flight mutation" on a session/tool mismatch, then publishes `tool_finished` and removes the entry (round-0 spec I2; cold read cites the no-match raise at :2091)
- I2 `status` reads its snapshot inside `with _state_lock(state_dir, create=False, exclusive=False):` — writer_lease.py `def status(` body (round-0 read at the then-:1751; cold read cites :1788); `drain` (round 0, `def drain(` ~:1855-1893) calls `_read_snapshot(state_dir)` with no lock
- I3 `_drain_reason(base, worktree, recorded, entry, tool_use_id)` builds the transcript path via `command_audit.session_result_ids(base, worktree, session_id)` → `project_dir(base, cwd)` → `<base>/<encode_cwd(cwd)>/<sid>.jsonl` — writer_lease.py `def _drain_reason(` (round 0) and command_audit.py `def session_result_ids(` (round 0, after `project_transcripts` :271); `encode_cwd` :224-226 replaces `/` and `.` with `-`
- I4 `_release_when_drained` writes the one-time stderr line inside the `with _state_lock(... exclusive=True)` block — writer_lease.py round-0 hunk at `@@ -1676,6 +1686,14 @@` (`if not warned:` … `sys.stderr.write(...)` before `time.sleep(0.05)`)
- I5 The current tests: (c) `test_drain_completed_uses_transcript_results_as_the_only_evidence` writes its fake transcript via `_write_transcript` under `project_dir(base, repo)`; (e) `test_posttooluse_for_the_pinned_bootstrap_does_not_stop_the_session` has an `exempt` arm (stdout `""`) and a `mismatched` arm asserting `json.loads(stdout)["continue"] is False` — tests/test_writer_lease.py round-0 additions (names from `git diff 6755fd5..af7a9e1`)
- L1 `_TOOL_USE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")` — writer_lease.py round-0 constants block (after `_LOCK_TOKEN_KEYS`); reuse the same shape for session ids
- L2 Claude Code session ids are UUIDs (e.g. `ad30e818-09f6-47c5-9e0a-57208e0dcfec`) and Codex thread ids look like `thr_123` — knowledge-base codex/hooks.md:537 for Codex; the Claude form is this session's own id; both match L1's pattern
- E1 `drain`'s JSON emits, per kept entry, one of four FIXED reason literals; the detail of a failed `_finish_tool` goes to stderr as `writer-lease: <tool_use_id>: <exc>` — and that `<exc>` is NOT a fixed literal: `_finish_tool` reaches `_read_snapshot`/`_publish_generation`, whose messages can embed an absolute state path and OS error text (writer_lease.py:560 `f"unsafe writer lease path {path}: {exc}"`, also :526, :540, :737 per the verifier) — so stderr may carry a home-directory path (username); never the holder token, never transcript content
- E2 the new fixed reason strings `"session id is not a safe path component"` and `"finish transaction failed"` — new literals (grep: 0 occurrences today)
- A1 A transcript root named `<sid>.jsonl` exists in at most one project directory under the base (session ids are unique); if a second exists, the union of both is still correct evidence for "this id finished" — held without a read; harmless either way
