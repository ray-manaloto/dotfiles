Implemented the claude-doctor oracle fix within the exclusive allowlist. No commit was created, and the caller’s `doctor.toml` edit was preserved.

Changes:

- [claude_doctor.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/claude_doctor.py:186) now reads successful oracle values from stdout only, retains stderr for failed-command reasons, and validates version shape.
- `claude doctor` retains its existing merged-output behavior.
- [test_claude_doctor.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_claude_doctor.py:183) adds four subprocess-boundary tests covering valid stdout with stderr warning, empty stdout, malformed stdout, and nonzero stderr.

`★ Insight ─────────────────────────────────────`
The fix uses two defenses: stream provenance prevents diagnostics becoming data, while version validation prevents arbitrary stdout becoming enforcement evidence. Either defense catches a different regression class.
`─────────────────────────────────────────────────`

Verification:

| Gate | Result |
|---|---|
| Focused pytest | rc 0; 35 passed |
| Ruff check | rc 0 |
| Ruff format check | rc 0 |
| ty | rc 0 |
| `git diff --check` | rc 0 |
| Exact-HEAD mutation | rc 1; all four new tests failed independently |

The unmodified `uv` commands encountered `SANDBOX: rc 2` because the default cache was unwritable. With only `UV_CACHE_DIR` redirected to `/private/tmp`, the results above passed.

Repository-wide readiness is not green: the full suite returned rc 1 with 774 passed, 1 failed, and 11 deselected. The failure was [test_dag_tick.py:1355](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_dag_tick.py:1355), where `read_proc_start(os.getpid())` returned `None`; a focused reproduction also returned rc 1. That file is outside the allowlist and was not modified.

The review found no specification contradiction. The highest-priority remaining instance of this failure class is [session_gate.py:261](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/session_gate.py:261), where the last line of merged output is parsed as sentinel JSON. Other enforcement-relevant sites include authentication parsing in `audit.py`, the `lock-shared` marker, GHCR token scopes, and SDLC parent-session-ID parsing. Diagnostic-only merged streams were also identified in `container.py`, `gate_result.py`, `renovate_validate.py`, and transcript-digest code.

The proposed cached-verdict repair—not implemented because it is outside the allowlist—is:

1. Revalidate a cached `INVALID` before denying a normally blocked operation.
2. While still invalid, permit `Edit`/`Write` only for the exact repository-root `doctor.toml`, enabling the documented off-switch.
3. Retain controls denying neighboring `doctor.toml` files, backups, unrelated paths, and freshly confirmed invalid states.

The isolated prior-source tree remains at `/private/tmp/claude-doctor-prior.WmoDp9`; cleanup was blocked before execution.

No other specialists were spawned.

Specialists spawned:

- `sdlc-python-specialist` — `/root/python_doctor_oracle`
- `sdlc-documentation-specialist` — `/root/doctor_oracle_review`

