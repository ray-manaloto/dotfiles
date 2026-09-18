Respec round 1 is implemented in the two allowlisted files:

- [claude_doctor.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/claude_doctor.py)
- [test_claude_doctor.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_claude_doctor.py)

Changes include bounded stderr diagnostics without treating stderr as the version, explicit merged-stream handling for `claude doctor`, and non-enforcing `UNKNOWN` verdicts for unreadable running versions. Independently provable install-method and cleanliness findings remain reported.

Required verification:

- Targeted pytest: `rc=0`, 41 passed
- Ruff check: `rc=0`
- Ruff format check: `rc=0`
- M-a through M-d: each `rc=1`, with the intended regression tests failing
- Default uv cache attempt: `SANDBOX: rc=2`; isolated-cache rerun passed

Repository-wide validation remains blocked outside the allowlist:

- Full suite initially: `rc=1` after 779 passed and 11 deselected
- Isolated control rerun: `rc=1`
- Failure: `tests/test_dag_tick.py:1355`; `read_proc_start(os.getpid())` returned `None`

The staged round-0 work and two pre-existing staged reports remain intact. Only the two allowlisted files have new working-tree changes. Nothing was unstaged or committed.

### Specialists spawned:

- `sdlc-python-specialist` — `/root/python_doctor_oracle_respec1`

No others were spawned.

