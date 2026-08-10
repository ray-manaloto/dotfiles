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
- **Comma-except (PEP 758, py3.14):** `except A, B:` (no `as`) catches
  BOTH `A` and `B` — parens are optional style, and ruff actively strips
  them to the no-paren form (verified: it does not rebind `B`, the old
  Python-2 trap). Parens are still REQUIRED to bind multiple types:
  `except (A, B) as e:`. See `feedback_python2_comma_except` memory.

## Testing

```bash
uv run --project python pytest tests/ -x -q                # Run the test suite
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

Two engine defaults bind every contract you write (#299):

- **`paths_required` defaults to `true`** — a declared path that no longer
  exists FAILS the suite, for every handler, enforced in `run_suite` before
  dispatch. Opt out with an explicit `paths_required = false`. Without this,
  *partial* path loss is silent: handlers resolve paths through
  `_resolve_paths`, which drops what is gone, so a suite naming two files
  keeps passing on the strength of the one that survives.
- **Bare `tokens` is a UNION** (combined text): a token in ANY listed file
  satisfies the contract for all of them. Use **`per_path_tokens`** to state
  which file must carry which token — otherwise a contract has no opinion
  about the files it names (`build.path-includes-mise-shims` named a file that
  stopped wiring PATH and stayed green ~3.5 months).
- **A single-path `require_tokens` suite MUST use `per_path_tokens`** (#397,
  gated by `dotfiles-setup token-audit`). With one path the two forms mean the
  same thing, but only `per_path_tokens` is read by the uniqueness audit — the
  bare form silently exempts the suite. Ask the audit's question yourself when
  adding a token: **how many places in that file match it?** More than one and
  a stand-in can satisfy it. 33 of 33 tail rebindings closed a LIVE hole, and
  in **11** of them the sole stand-in was a **comment** — so a file's own
  documentation can satisfy a contract about its wiring.

Contracts use handler types like `policy_doc` (references a doc file)
and `regex_forbid` (pattern-based rejection). Note: static contract
substring matches false-positive on prefixed ENV vars (e.g.,
`CARGO_HOME=` matches `MISE_CARGO_HOME=`); prefer leading-space anchors
or `regex_forbid` handlers. See `feedback_forbid_tokens_substring_fragile`.

## Serialization: route every call through `codec` (#675)

`msgspec` is the project's model system (#669). **Never call it directly** —
use `dotfiles_setup.codec.encode` / `.decode`. Machine-enforced by ruff
**TID251**, whose ban list covers all **14** msgspec entry points that accept a
conversion hook (enumerated from the library, not hand-written: `Encoder`/
`Decoder`, `convert` and `to_builtins` are the ones a from-memory list misses).
`codec.py` carries the only per-file allowance.

The reason is that msgspec's hooks are **per-call keyword arguments**, not a
global registration — so a direct call works fine while carrying its own copy of
the conversion table, and the copies drift. `pathlib.Path` is unsupported in
**both** directions, and the decode half is the quiet one: it raises only
because the annotation says `Path`, so a field annotated `str` accepts the value
and hands you a string that behaves like a path until something calls `.parent`.

Teach it a new type with `codec.register(T, encode=…, decode=…)` — both
directions, because a half-registration encodes cleanly and loses the type at
read time in another process. Never add a branch to the hook itself.

## Dependencies

Key packages: `msgspec` (models + serialization — via `codec` only, above),
`pydantic` (config; leaving the tree in #683), `python-debian` (deb822 parsing
for `apt_repo`; Ubuntu ships the same code as `python3-debian`), `pytest`
(testing). Full lockfile at `uv.lock`.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
