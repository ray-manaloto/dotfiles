# Spec: fix the 2 failing session_registry tests on the codex-takeover ship branch (2026-10-05)

## 1. Objective

`ship/codex-takeover-b2a` @ 3df4de14 is queued 3rd for the host-slot ship. The coordinator measured these
two failures on 2026-10-05:
- `tests/test_session_registry.py::test_lane_cards_public_write_uses_codex_claim_and_claude_handback[True]`
- the same test's `[False]` case

Both fail with `AssertionError: assert 2 == 0`; the run was `uv run --project python pytest
tests/test_session_registry.py -q`, rc 1, 2 failed / 16 passed. The full pytest gate in `mise run ship` will
fail on them. Find the ROOT CAUSE and fix it. A likely candidate is that the test reads LIVE host state
(real claims store, live sessions, the heavy-gate lock) instead of a fixture. Decide whether the defect is in
the code or in the test, and say which, with evidence.

## 2. Files (allowlist)

- `tests/test_session_registry.py`
- `python/src/dotfiles_setup/session_registry.py`
- `python/src/dotfiles_setup/handoff_inbox.py` (only if the root cause is there)

## 3. Constraints

- No inline suppressions. Do not skip or xfail the tests.
- The tests must be hermetic: no dependence on this Mac's live sessions, claims or locks.
- Targeted tests only: `uv run --project python pytest tests/test_session_registry.py tests/test_handoff_inbox.py -q`.
  No full lint/pytest/verify: the host slot belongs to the coordinator.
- `COMMIT: caller`: leave the changes uncommitted and report the file list plus the root cause.

## 4. Verification

- Before your fix: the 2 tests fail. After your fix: rc 0 for both files.
- Control arm: revert only your fix line and show the failure returns, then restore the fix.

## 5. Commit

`caller`.

## 6. PREMISES

- A: the failure is reproducible on 3df4de14. Measured by the coordinator, 2026-10-05; log at
  `/Users/rmanaloto/.claude/jobs/71b633d9/tmp/reg-baseline.log`.
