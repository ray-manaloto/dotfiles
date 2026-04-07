<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-07 | Updated: 2026-04-07 -->

# python/ — Python Package (dotfiles_setup)

## Purpose

Python package providing the `dotfiles-setup` CLI for bootstrap
orchestration, structured verification contracts, and typed configuration.
Requires **Python 3.14**.

## Key Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Package metadata; includes `[tool.ty]` section for ty type checker |
| `uv.lock` | Reproducible dependency lockfile (managed by uv) |
| `requirements.txt` | Legacy; prefer `uv sync` |
| `src/dotfiles_setup/` | Package source; `DotfilesConfig(BaseSettings)` centralizes 16 env vars via Pydantic config DI |
| `verification/suites.toml` | Structured verification contracts run by `dotfiles-setup verify run` (CI: contract-preflight) |

## Working in this directory

- **Dependency manager:** `uv`. Always `uv run --project python ...`
  from the repo root. **Never `uv run --directory python`** — that
  changes cwd and breaks relative test paths.
- **Type checker:** `ty` (configured in `[tool.ty]`). Runs as part of
  hk pre-commit.
- **Linter/formatter:** `ruff` (configured in `pyproject.toml`). Runs
  as part of hk pre-commit.
- **Zero inline suppressions:** `noqa`, `type: ignore`, `pylint: disable`,
  `nosec` are rejected by the `no_lint_skip` hk step.
- **Python 2 comma-except trap:** `except A, B:` is valid Python 3 but
  catches only `A` and rebinds `B` as the exception instance — always
  use `except (A, B):`. See `feedback_python2_comma_except` memory.

## Testing

```bash
uv run --project python pytest tests/ -x -q                # All 65 tests
uv run --project python pytest tests/test_audit.py -x -q   # Single file
```

Tests live at repo-root `tests/`, **not** `python/tests/`. They cover
config, audit, bootstrap, ghcr, image smoke, and shell integration.

## Verification contracts

`dotfiles-setup verify run` executes contracts defined in
`verification/suites.toml`. This gate is **distinct** from `hk run
pre-commit --all` — some contracts (e.g., `build.no-stderr-suppression`)
only run through the verify CLI. Run both locally before pushing
Dockerfile changes.

Contracts use handler types like `policy_doc` (references a doc file)
and `regex_forbid` (pattern-based rejection). Note: static contract
substring matches false-positive on prefixed ENV vars (e.g.,
`CARGO_HOME=` matches `MISE_CARGO_HOME=`); prefer leading-space anchors
or `regex_forbid` handlers. See `feedback_forbid_tokens_substring_fragile`.

## Dependencies

Key packages: `pydantic` (config), `pytest` (testing). Full lockfile at
`uv.lock`.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
