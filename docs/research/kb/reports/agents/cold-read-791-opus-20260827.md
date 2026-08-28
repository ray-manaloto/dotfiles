# Cold read — af7a9e1 (base 6755fd5), writer-lease drain

## HIGH

H1. `--completed` resolves transcripts against the DRAINING caller's worktree, not the
    registering session's, so any entry left by a session in a sibling worktree is
    permanently unreachable and reported as untraced.
    `writer_lease.py:1878` (`_drain_reason(base, identity.worktree, ...)`) →
    `command_audit.py:281` (`project_dir(base, cwd)`).
    Sequence: lease is Git-common-dir scoped and explicitly spans linked worktrees;
    session A runs in `<repo>-wt2` and leaks `call-x`; a recovery session runs
    `writer-lease-drain -- --completed` from `<repo>` → project dir encodes `<repo>`,
    `session_result_ids` returns `None` → `kept={"call-x": "no transcript for session"}`,
    **rc=0**. The in-flight entry that blocks transfer can never be drained by the
    documented arm. The in-flight record carries no cwd, so the information to fix this
    is not stored (`_INFLIGHT_KEYS`, `writer_lease.py:110`).

H2. `drain --tool-use-id` has no liveness, ownership or staleness check and the bootstrap
    allowlist admits it pre-ownership, so a non-owning session can delete a LIVE holder's
    in-flight entry mid-mutation. `writer_lease.py:1855-1889` + `_bootstrap_drain`
    `writer_lease.py:1997-2007`.
    Sequence: holder H is alive running Bash `id-1`; session B (any session) runs
    `mise -C <wt> run writer-lease-drain -- --tool-use-id id-1` — exempt from the
    Pre gate, `_finish_tool` succeeds. H's own PostToolUse then hits
    `"tool completion has no matching in-flight mutation"` (`writer_lease.py:2091`) →
    the runner emits `{"continue": false}`, wedging the healthy session. Nothing in
    `drain()` consults `_holder_is_live` (which `status` does use, `writer_lease.py:1799`).

H3. Partial drain is reported as total failure and the result JSON is lost.
    `writer_lease.py:1880-1893`: `_drain_one` raises `LeaseError` out of the loop →
    `writer_lease_main` (`:2237`) prints one line and returns 2; the
    `{"drained":…, "kept":…}` write at `:1888` never runs, so the caller cannot tell
    which entries were finished. Triggering input: any concurrent legitimate
    `PostToolUse` for an entry `--completed` also selected (both call `_finish_tool`;
    the loser gets "no matching in-flight mutation"), or two drains racing. The
    snapshot at `:1866` is read with no lock, so the window is the whole run.

## MED

M4. `drain --completed` exits 0 having done nothing. `writer_lease.py:1893` returns 0
    unconditionally; `kept` is data, not a failure signal. The transfer refusal
    (`:1432`, `_DRAIN_HINT`) points the operator at exactly this arm, and under H1 it is
    the arm most likely to no-op. An automated recovery reading rc sees success.

M5. `session_result_ids` interpolates an unvalidated on-disk `session_id` into a path and
    follows symlinks. `command_audit.py:281-292`: `project / f"{session_id}.jsonl"` and
    `project / session_id` with no component check — `_hook_fields`
    (`writer_lease.py:2127`) only requires a non-empty str, so `../../x` is storable and
    later `rglob`ed outside the projects dir. `root.is_file()` / `nested.is_dir()` follow
    symlinks; this is the only reader in this state machine that opens by pathname rather
    than the `O_NOFOLLOW` descriptor-relative helpers used everywhere else.
    Also unbounded: `_json_lines` (`command_audit.py:327`) `read_text()`s every nested
    transcript whole, with no counterpart to `_AUDIT_READ_CEILING_BYTES` (8 MiB).

M6. The "evidence" is caller-environment controlled. `command_audit.transcripts_base`
    (`:213`) honours `CLAUDE_CONFIG_DIR`; `drain` calls it with no override
    (`writer_lease.py:1874`). Exporting `CLAUDE_CONFIG_DIR` to a directory holding a
    hand-written `<sid>.jsonl` with the target `tool_use_id` makes `--completed` drain
    anything. (The bootstrap allowlist does block an inline `VAR=… mise …` prefix — argv
    mismatch — but not a prior `export`.)

M7. Drain forges a completion the audit cannot distinguish from a real one. `_drain_one`
    (`writer_lease.py:1898-1908`) emits `tool_finished` with `task_id =
    entry["session_id"]` and the recorded tool name; no drain-specific event or actor is
    recorded. `_validate_tool_finished` (`:901`) therefore passes, but the audit — whose
    stated job is to derive transitions from facts, not caller flags — loses the fact that
    a third party ended the mutation.

M8. O5's fix depends on the Post payload carrying `tool_input.command`, which is unproven
    here. `hook_decision` (`writer_lease.py:2155-2163`) exempts only when
    `isinstance(invocation.tool_input, dict)`; `_hook_fields` (`:2131`) tolerates a
    missing `tool_input` (`payload.get`). If Codex's PostToolUse payload omits
    `tool_input` (the `.codex/hooks.json` Post hook is the same runner, payload shape is
    the harness's), the bootstrap Post still falls to `_finish_tool` → `{"continue":
    false}`, i.e. the reported symptom is not fixed. The new test synthesises
    `tool_input` (`tests/test_writer_lease.py:2465`), so it cannot detect this.

M9. `drain` reads state with no lock while `status` takes a shared one.
    `writer_lease.py:1866` calls `_read_snapshot(state_dir)` bare, vs `status` at `:1788`
    (`with _state_lock(..., exclusive=False)`). A concurrent `_publish_generation`
    reclaiming a superseded generation between the `current` read and the per-file reads
    surfaces as a bare `LeaseError` → rc=2. Fail-closed, but noisy and avoidable.

## LOW

L10. `_release_when_drained` writes to stderr *inside* the exclusive state lock
     (`writer_lease.py:1689-1696`). A full/unread stderr pipe blocks the write while the
     state lock is held, stalling every hook. One ~140-byte write, so narrow.

L11. `status` now publishes `holder_port` (`writer_lease.py:1813`), the loopback challenge
     port, to any caller. `holder_token` is correctly still absent, and both new fields
     are type-validated ints (`_validate_receipt_numbers`, `:734`), so no type instability
     and no secret — but the probe surface widens.

L12. The warn-once flag never re-arms: `warned = True` (`writer_lease.py:1690`) is set for
     the first non-empty in-flight set, so entries appearing later are never announced.

L13. Shape asymmetry: `drain()` supports `--tool-use-id X --completed` together, but
     `_bootstrap_drain` (`:1997`) admits only exactly `["--completed"]` or exactly
     `["--tool-use-id", ID]` — a non-owning session cannot run the combined form, and
     multiple IDs need N separate exempt commands.

## Tests — would each still pass if its change were reverted?

- `test_bootstrap_admits_claude_owner_and_both_drain_shapes` — armed for O1 (the
  `claude:` owner and both drain shapes deny without it). But 2 of its 4 deny arms are
  no-ops w.r.t. this diff: `env PATH=/nowhere …` and `…; git add README.md` deny on
  argv[0]/extra-token mismatch, which held before O1 too.
- `test_drain_clears_a_leaked_entry_by_id_and_unblocks_recovery` — armed (verb absent).
- `test_drain_completed_uses_transcript_results_as_the_only_evidence` — armed.
- `test_status_reports_holder_process_facts_without_the_holder_token` — armed (O3 fields).
- `test_posttooluse_for_the_pinned_bootstrap_does_not_stop_the_session` — armed: restoring
  `event == "PreToolUse"` makes arm 1 emit `{"continue": false}` and fail.
- Gaps: no test drains against a LIVE holder (every case `_stop(abrupt=True)` first, so H2
  is untested); no concurrent drain/hook test (H3); no cross-worktree `--completed` test
  (H1) — both worktrees exist in the fixture but drain is always run from `repo`; no test
  that a mid-loop failure loses the JSON.

## Clean branches checked (no finding)

- `drain` cannot act on a stale generation: `_finish_tool` re-reads under the exclusive
  lock and re-checks `session_id`/`tool_name` (`writer_lease.py:2088-2094`), and
  `_validate_tool_finished` binds the event to the active receipt (`:901`).
- Audit/in-flight invariant holds after drain — one `_finish_tool` path, one
  `_publish_generation`; `_validate_history` (`:847`) would reject any divergence, and
  the test's successful `recovery` acquisition exercises it.
- Drain never touches the flock, the receipt bytes, or the holder process — receipt is
  passed through unchanged to `_publish_generation`.
- `missing` ids raise before any mutation (`:1871`), so a typo'd `--tool-use-id` is a
  clean rc=2 no-op.
- No `LeaseError`/`OSError`/`json` error is swallowed in the new lease code: every path
  raises to `writer_lease_main` → stderr + rc=2. (`_json_lines`/`_result_ids` in
  command_audit *do* swallow OSError and bad JSON, but that is a pre-existing contract
  and its effect here is "no evidence" → entry kept, which is the conservative side.)
- `holder_token` is not reachable through any new field; receipt/in-flight types are
  schema-validated, so `status` and `inflight_entries` cannot emit non-str/non-int or
  raise KeyError on a malformed receipt (it fails closed earlier in `_read_snapshot`).
- `_bootstrap_command`'s owner set is exact-match on `f"{prefix}:{session_id}"`, so an
  owner with shell metacharacters or a mismatched sid is rejected; `shlex.split` keeps
  `;`/`&&` as tokens, so a suffixed command breaks the exact-list comparison.
- `_TOOL_USE_ID_PATTERN` (`^[A-Za-z0-9_-]{1,128}$`) admits nothing shell-active, and it
  gates only the exempt argv shape, not `drain()` itself.
- `_drain_reason` memoises per session id (`recorded` dict), so N entries from one session
  cost one transcript scan.
