**Verdict: SHIP for static review.** Round-1 P2 is resolved. No blocking correctness or test-design regression was found.

**Overall status: partial completion.** Static review completed; required runtime verification remains **NOT RUN** because it conflicts with your review-mode instruction. No specialist reported a failed gate.

Reviewed `origin/main` at `25bceb1e9af02c5cbb4a574e50b51413b3c353ad` through `b3399c2a074d43f9d9465a48722e53629c9baddc`, including the round-2 delta from `a1fb05ce`. All source anchors below refer to **b3399c2a**, rather than checkout HEAD.

### Confirmed findings

- **P2 resolved:** `tests/test_sync.py:49` sets temporary `HOME` instead of patching private `sync._state_file`. Production resolves `Path.home()` dynamically at `python/src/dotfiles_setup/sync.py:287–289`, so real reads and writes use isolated state. The writer creates parent directories at `sync.py:378–379`; pytest restores the environment afterward.
- **Literal state paths confirmed:** `_STATE_REL` and `_state_path` at `tests/test_sync.py:55–63` express the expected path independently. Seeding tests use that path at lines 826, 836, and 859. The positive legacy-record read at lines 845–848 provides a fail direction for an incorrect literal path.
- **Requested selection case added:** `tests/test_sync.py:582` supplies a newer exited container and an older restarting container, expecting the restarting container’s image ID. Removing `restarting` from `_LIVE_STATES` would contradict that expected value.
- **No new internal mocks:** Changed tests substitute environment variables, temporary filesystem state, and fake executables at system boundaries. Internal patches elsewhere in the file predate this diff.
- **Docker errors propagate correctly:** `container_image_id` calls checked `docker_container_rows` at `sync.py:528`, preserves running/paused/restarting preference at lines 531–535, bounds inspection, and raises on inspection failure at lines 536–543.
- **The late-failure regression covers the motivating defect:** `sync_main` catches `DockerUnavailableError` around the complete operation at `sync.py:870–874`, including record writing after lifecycle success. The test at `tests/test_sync.py:616–670` calls public `sync_main` through fake `docker`, `mise`, and `gh` executables. It requires rc 2 and evidence that `mise run up` occurred. Reverting the expanded exception boundary would let the exception escape.
- **Environment isolation is suitable:** The regression explicitly sets `USER` and `DOTFILES_PLATFORM` and removes the ambient SSH-port override at `tests/test_sync.py:659–662`. Executables, markers, logs, and workspace reside under `tmp_path`; fake programs precede inherited PATH.
- **No prohibited inline suppressions found:** Pinned-source `git grep` returned rc **1**, indicating no matches.

The fail-arm conclusions above are **static reasoning**, not executed mutation evidence.

### Nonblocking observation

**P3 — inherited docstring mismatch, `python/src/dotfiles_setup/sync.py:516`.** “Prefers a RUNNING match” understates the implementation, which prefers the newest running, paused, or restarting container. A newer paused container can precede an older running container. This preserves existing selection behavior; “Prefers a live match” would describe it accurately.

### Verification conflict and evidence

The spec at `spec-review-1554-r2.md:22–24` requires pytest execution and its rc; line 3 permits targeted pytest/ruff and a scratch worktree. Your current instruction prohibits repository gates and checkout modification. Those conflicting execution steps were stopped.

| Check | Observed result |
|---|---|
| Python specialist’s pytest gate; specifically `uv run --project python pytest tests/test_sync.py tests/test_pr.py -x -q` | **NOT RUN; no rc** |
| Ruff, mutation tests, builds, other repository gates, real Docker integration | **NOT RUN; no rc** |
| Read-only Git show/diff commands | **rc 0** |
| Suppression search | **rc 1; no matches** |
| Final `git status --porcelain=v1` | **rc 0; empty output** |

The spec’s “189 passed; ruff clean” remains an **unverified historical claim**. The target commit message repeats the test-count claim; it does not establish execution evidence for this review.

No checkout changes, report files, scratch worktrees, commits, or pushes were made. The Python specialist owned both changed files; no other roster domain was implicated.

## GitHub repos touched

- `ray-manaloto/dotfiles` — local-only review of pinned Git objects; no remote writes.

No others were spawned.

### Specialists spawned:

- `sdlc-python-specialist` — `/root/python_review_1554_r2`

