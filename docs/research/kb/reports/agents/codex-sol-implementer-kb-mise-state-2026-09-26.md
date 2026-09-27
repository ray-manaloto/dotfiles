Implemented on `fix/mise-state-isolation`; changes remain uncommitted.

Changed paths:

- [tests/conftest.py](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/tests/conftest.py:35) — autouse per-test mise isolation plus Git-shim-safe exclusion.
- [tests/test_mise_state_isolation.py](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/tests/test_mise_state_isolation.py:28) — real nested-pytest regression with exact name→target mapping.
- [python/src/kb_setup/evals.py](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/python/src/kb_setup/evals.py:202) — optional subprocess environment threaded through the redaction reader.
- [python/src/kb_setup/eval_cases.py](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/python/src/kb_setup/eval_cases.py:733) — production control gets its own temporary mise state.
- [tests/test_eval_cases.py](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/tests/test_eval_cases.py:112) — verifies that production environment handoff.
- The pre-existing untracked spec remains untouched.

Premise 7 survived the repository-wide grep: no third site both writes a throwaway mise config and invokes real mise.

Verification history:

- Exact `mise run kb-check -- …`
  - Initial: `rc=1` — Ruff/formatting only; ty and pytest passed.
  - After formatting: `rc=0`.
  - After lazy-state adjustment: `rc=0`.
  - Final candidate after Git-shim handling: `rc=0`.
- Additional `mise run kb-check -- tests/test_eval_cases.py`: `rc=0`.
- Exact `mise run test`
  - Initial: `rc=2` — three eager-directory interactions.
  - Second: `rc=2` — two Git-clean tests; `git` resolves through a mise shim and created the registry inside their fixture repositories.
  - Final: `rc=0`, 100%.
- Final fail arm:
  - Fixture `setenv` removed: `rc=1`; outer mapping gained the scratch config.
  - Fixture restored: `rc=0`; `1 passed`.

One deliberate adjustment: the fixture sets `MISE_STATE_DIR=tmp_path/mise-state`, but lets mise create the directory on first use. Eager creation invalidated existing empty-directory tests. A narrowly scoped Git exclude for `/mise-state/` prevents shim-created harness state from appearing as source drift.

Graph health was warning-bearing: direct Graphify query returned `rc=0` with the pre-#1504 node-ID warning and truncation (69/897 nodes); the repository wrapper rejected that output with `rc=3` and no matches, so source inspection was used as fallback authority.

Execution caveat: before discovering that `git` resolves through a mise shim, several early read-only Git inspections were not wrapped in a temporary `MISE_STATE_DIR`; the session environment had no such variable set. I did not inspect or repair host state afterward, so I cannot prove those shim reads caused zero host-state writes. All actual Graphify/mise/pytest experiments and subsequent Git audits used temporary state directories.