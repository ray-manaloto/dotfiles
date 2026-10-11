# Spec — codex-takeover Phase D: make B1+B2a+C committable, then commit (2026-10-05)

Context: Phase C (`af70d2d4`) is partial; see
`docs/research/kb/reports/agents/codex-takeover-phaseC-2026-10-05.md`. The worktree has 291
staged/dirty paths at base 85e5eaf7. Nothing is committed. The coordinator's SLOT wait needs a
commit SHA. Umbrella #1721.

## 1. Objective

One green commit (or two) on `feat/codex-takeover`. The pre-commit hook passes with no
suppression and no `--no-verify`. Then the coordinator gets its SLOT trigger.

## 2. Work

1. **The 2 remaining `py_ty` errors** are at `tests/test_command_audit.py:29` and
   `tests/test_session_review.py:36` (`from tests.test_session_ledger import digest_fixture`).
   - Ruling: do NOT change `python/pyproject.toml`. Move `digest_fixture`
     (`tests/test_session_ledger.py:3129`) into `tests/conftest.py` as a pytest FIXTURE that
     takes `tmp_path` and returns the same tuple.
   - Make all three test files request the fixture instead of importing or calling the function.
   - Behaviour is unchanged. The canonical `ty check --project python python/src tests plugins`
     must report 0 diagnostics.
2. **The snapshot is too big:** `docs/handoffs/lane-snapshot-2026-10-05.json` is 8.5 MB, which
   fails `check_added_large_files`.
   - Rewrite it to keep ONLY working/blocked/stopped sessions (~70 rows): every field the
     START-HERE table needs, plus the 11 omissions.
   - Keep it under 500 KB.
   - Do not commit the full raw inventory; reference its regeneration command
     (`mise run lane-cards -- --json`) instead.
3. **Commit** with `git commit -F .agent/plans/commit-msg-b1b2a.txt`, after re-staging only the
   files you changed (the index already holds the intended set). If the hook reports anything,
   fix the CODE and retry; at most 3 attempts. Record the literal SHA.
4. **Then append to the coordinator inbox:**
   `mise run handoff-inbox -- append --lane codex-takeover --title "B2a SETTLED" --body "B2a SETTLED <SHA>; START-HERE ready (partial: 0 issues created, 45 blocked by 11 omissions; codex hand-back launch is a manual BLOCKED seam)"`.
   Record its rc.

## 3. Files (allowlist)

- `tests/conftest.py`, `tests/test_session_ledger.py`, `tests/test_command_audit.py`, `tests/test_session_review.py`
- `docs/handoffs/lane-snapshot-2026-10-05.json`, `docs/handoffs/codex-takeover-START-HERE.md` — the latter ONLY to fix references to the slimmed snapshot
- `docs/research/kb/reports/agents/codex-takeover-phaseD-2026-10-05.md` (new)

## 4. Constraints

- No `--no-verify`, no inline suppressions, no `--ephemeral`, no push, no `gh pr`.
- No user-level files. No research fan-out is needed for this mechanical fix.
- Gates:
  - the pre-commit hook;
  - targeted pytest of the 3 test files;
  - the canonical `ty` command.
- Full lint, pytest and verify wait for the coordinator's SLOT.

## 5. Verification

- `ty` rc 0.
- Targeted pytest rc 0 (expect ≈306 passed).
- Commit rc 0 and its SHA.
- The snapshot is < 500 KB.
- The inbox append rc 0.

## 6. Commit

`lane`.

## 7. PREMISES

| # | Kind | Claim | Source |
|---|---|---|---|
| 1 | L | 2 remaining ty errors at those import lines | phaseC report:89 |
| 2 | I | `digest_fixture(tmp_path) -> tuple[...]` | `tests/test_session_ledger.py:3129-3131` |
| 3 | L | `tests/conftest.py` exists; no other test imports `tests.*` | `ls`/`grep`, 2026-10-05 |
| 4 | L | snapshot 8,493,751 bytes | `ls -la`, 2026-10-05 |
| 5 | L | `.agent/plans/commit-msg-b1b2a.txt` holds the prepared message | written this session |
