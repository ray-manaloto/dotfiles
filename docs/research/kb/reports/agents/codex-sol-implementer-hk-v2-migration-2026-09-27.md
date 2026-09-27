# Codex implementation report: hk v2 migration

Date: 2026-09-27
Branch: `chore/hk-v2.3-migration`
Spec: `docs/specs/hk-v2-migration-dotfiles.md` rev 2, ratified by Ray 2026-09-27
Commit owner: caller; this implementation remains uncommitted.

## Execution constraints observed

- Every shell invocation began with `unset HK_PKL_BACKEND`.
- No file outside the repository was modified.
- No `hk install` or `hk uninstall` command was run in any scope.
- No bare `mise lock`, local base-image build, `mise run build`, or local
  `docker buildx bake` command was run.
- The four untracked input artifacts present before implementation were
  preserved unchanged:
  `docs/research/kb/reports/agents/hk-v2-global-hooks-wrong-or-adapt-2026-09-27.md`,
  `docs/research/kb/reports/agents/hk-v2-migration-research-2026-09-27.md`,
  `docs/research/kb/reports/agents/premise-verifier-hk-v2-migration-2026-09-27.md`,
  and `docs/specs/hk-v2-migration-dotfiles.md`.

## Orientation and live version selection

- The full ratified spec was read from disk before implementation (`rc=0`).
- `mise run graphify-query -- "..."` returned `rc=3`: the graph was stale at
  `9f5bd67a` versus HEAD `453aa39b`, naming 12 changed corpus files. Per the
  repository rule, implementation fell back to the exact source files named by
  the ratified spec; the graph was not rebuilt because its artifacts are outside
  this migration's file allowlist.
- `mise ls-remote editorconfig-checker` returned `rc=0`; the latest listed 4.x
  release was **4.0.2**, so 4.0.2 is the selected editorconfig-checker version.

## Implementation observations

- Updated the manifest/Pkl pins, minimum hk version, postinstall recipe,
  CI defense-in-depth prose, Renovate grouping, smoke assertion, parser flag
  tables, and their tests in the files allowed by the spec.
- Added the autouse Git-global-config isolation fixture and a real subprocess
  test with a deliberately contaminated second config. These edits were not
  executed because the required lock step blocked before verification.
- A login-shell startup side effect rewrote the changed root editorconfig lock
  block to 4.0.2 (macOS-arm64 only) and the shared hk block to 2.3.0 before the
  explicit lock tasks. Those blocks were deleted again, together with the old
  image hk block, to restore the spec's required precondition for scoped
  regeneration. Subsequent commands used non-login shells.

## Licensed-dissent stop

The first required lock command was run exactly as specified:

`mise run lock -- "aqua:editorconfig-checker/editorconfig-checker"`

It returned **rc=1** with:

> lock: not declared in the host config:
> ['aqua:editorconfig-checker/editorconfig-checker']. `mise lock` exits 0
> without locking anything for a name it does not recognise, so this would
> look like success. Use the FULL key as written in mise.toml /
> .config/mise/conf.d/shared.toml.

This contradicts section 4's mandated command. `mise.toml` declares the config
key `editorconfig-checker`, while `mise.lock` records the backend
`aqua:editorconfig-checker/editorconfig-checker`; the repository wrapper accepts
the former key and rejects the latter. The spec says a refusing lock task is a
STOP condition and forbids guessing, so implementation stopped here.

Consequently, the three lock blocks are currently absent and must not be
treated as a finished migration:

- `[[tools.editorconfig-checker]]` in `mise.lock`
- `[[tools.hk]]` in `.config/mise/mise.lock`
- `[[tools.hk]]` in `.devcontainer/mise-system.lock`

`mise run lock-shared -- "hk"`, `mise run lock-image`, `mise run hk-audit`,
the AGENTS.md staging-doctrine update, and all section 5 verification steps
were not run after this stop.

## Verification evidence

Every verification command below records its real exit status in a file before
the status is reported here. No gate is piped into `head` or `tail`.

| Step | Command / observation | Result |
|---|---|---|
| 1 | `mise install`; `hk --version`; `mise which editorconfig-checker` | NOT RUN — licensed-dissent stop before verification |
| 2 | `mise run pin-parity` | NOT RUN — licensed-dissent stop before verification |
| 3 | `hk validate` | NOT RUN — licensed-dissent stop before verification |
| 4 | `mise run lint` | NOT RUN — licensed-dissent stop before verification |
| 5 | `mise run fmt` on clean staged tree; rewrite inventory | NOT RUN — licensed-dissent stop before verification |
| 5b | Scratch-copy staged/unstaged behavior | NOT RUN — licensed-dissent stop before verification; AGENTS.md unchanged |
| 6 | `uv run --project python pytest tests/ -x -q` | NOT RUN — licensed-dissent stop before verification |
| 7 | `mise run verify` | NOT RUN — licensed-dissent stop before verification |
| 8 | `mise run pin-actions`; `mise run lint-docs` | NOT RUN — licensed-dissent stop before verification |
| 9 | `hk test` | NOT RUN — licensed-dissent stop before verification |
| 10 | Pin-parity failure control and restored pass | NOT RUN — licensed-dissent stop before verification |
| 11 | `grep -n 'hk install' mise.toml` | NOT RUN — licensed-dissent stop before verification |
| 12 | Git-global isolation test and asserted control arm | NOT RUN — licensed-dissent stop before verification |

## Final worktree status

Exact `git status --short` at the stop point (`rc=0`):

```text
 M .config/mise/conf.d/shared.toml
 M .config/mise/mise.lock
 M .devcontainer/mise-system.lock
 M .github/workflows/gcc-sha-repair.yml
 M .github/workflows/refresh.yml
 M hk-common.pkl
 M hk-image.pkl
 M hk.pkl
 M mise.lock
 M mise.toml
 M python/src/dotfiles_setup/workflow_claude_code.py
 M python/src/dotfiles_setup/workflow_hooks.py
 M renovate.json
 M tests/conftest.py
 M tests/test_image_smoke.py
 M tests/test_workflow_claude_code.py
?? docs/research/kb/reports/agents/codex-sol-implementer-hk-v2-migration-2026-09-27.md
?? docs/research/kb/reports/agents/hk-v2-global-hooks-wrong-or-adapt-2026-09-27.md
?? docs/research/kb/reports/agents/hk-v2-migration-research-2026-09-27.md
?? docs/research/kb/reports/agents/premise-verifier-hk-v2-migration-2026-09-27.md
?? docs/specs/hk-v2-migration-dotfiles.md
```
