<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-07 | Updated: 2026-04-07 -->

# tests/ — Pytest + Bats Test Suite

## Purpose

Repo-root-level test suite. Tests live here (not under `python/tests/`)
because they exercise the repo as a whole — Python package behavior,
bootstrap tool availability, shell integration, GHCR prerequisites, and
Docker image smoke outputs.

## Key Files

| File | Framework | Purpose |
|------|-----------|---------|
| `test_audit.py` | pytest | `dotfiles-setup audit` command output structure and exit codes |
| `test_bootstrap.py` | pytest | Bootstrap tool availability (`mise`, `chezmoi`, `uv`, `pixi`, python) |
| `test_config.py` | pytest | Pydantic `DotfilesConfig` and container-path constants |
| `test_ghcr.py` | pytest | GHCR prerequisite validation and token scope parsing |
| `test_image_smoke.py` | pytest | Smoke-test script generation, `_parse_human_size`, the #143 tool-set jq/diff block (host-bash), and the #223 shared cores — tier-1 (`build_tier1_script`, HEAD-vs-merge-base identity resolvers, a real bash EXECUTION test that the identity loop gates on a wrong hash) and tier-3 (`build_tier3_script` sanitizer+reflection substrate, `resolve_expected_p2996_ref_at_base` merge-base ref-pin, TSan-skip/ref-strict injection, golden byte-parity with `build_smoke_script`); plus the #231 image-analysis resolver (`decide_analysis_target` FAIL/quiet-skip, `_lookup_pr_number` empty-array trap, `resolve_analysis_ref_main`) and scope-(b) benchmark instrumentation (`classify_layer_source`, `estimate_pull_time_s`, `compare_payloads`, trend summary) |
| `test_image_smoke_exec.py` | pytest (`image_exec`, gated) | Containerized real-toolchain EXEC tests (#231 backlog): run the generated tier-1/tier-3 smoke cores against the real local `:dev` image — tier-1 happy + tool-set jq/diff FAIL-on-tampered, tier-3 compiler substrate compiles + ref-pin FAIL-on-wrong-ref. Deselected by default (root `pytest.ini` `addopts = -m 'not image_exec'`); run only via `mise run smoke-exec` (needs Docker + `mise run sync`) |
| `test_container.py` | pytest | `verify-container-latest` gate (`dotfiles_setup.container`) — running/bind-mount/smoke freshness checks |
| `test_sync.py` | pytest | `mise run sync` workflow (`dotfiles_setup.sync`) — staleness detection, action matrix, CI awareness, check/full/wait modes |
| `test_pr.py` | pytest | `mise run ship`/`land` workflow (`dotfiles_setup.pr`) — surface detection, gate matrix, bucket verification, pinned merge |
| `test_hook_guard.py` | pytest | PreToolUse mise-tasks-only guard (`dotfiles_setup.hook_guard`) — deny/redirect rules, false-positive guards, JSON contract |
| `test_hook_selfcheck.py` | pytest | Host-side hook self-check (`dotfiles_setup.hook_selfcheck`, the ship/land `hook-selfcheck` gate) — settings.json wiring + Bash-matcher assertions, and an end-to-end real-repo pass driving the wired PreToolUse guard |
| `test_tool_currency.py` | pytest | Daily tool-currency signal (`dotfiles_setup.tool_currency`) — release-link backends, report rendering |
| `test_renovate.py` | pytest | Renovate status signal (`dotfiles_setup.renovate`) — app-id/privilege check, report rendering |
| `test_autofix.py` | pytest | autofix.ci artifact applier (`dotfiles_setup.autofix`) — additions, traversal/shape/deletion refusal |
| `test_bash_budget.py` | pytest | Zero-bash-logic enforcer (`dotfiles_setup.bash_budget`) — allowlist/growth/shrink/stale logic, real-repo `allowlist == tracked` pin, end-to-end CLI |
| `test_gcc_sha.py` | pytest | gcc-latest sha auto-repair (`dotfiles_setup.gcc_sha`, #249) — pin parse/rewrite (strict subn), injected-fetcher sha compute, drift/no-drift repair, check-mode dry-run, CLI rc |
| `test_shell_integration.py` | pytest | Tool reachability in login shells (mise, chezmoi, uv, pixi, claude, gemini, codex) |
| `infra/foundation.bats` | Bats | Bash-level foundation checks (shell script integration) |
| `infra/runtimes.bats` | Bats | Runtime installation checks (bash) |

Total: **475 pytest tests** run by default (`pytest tests/` collects all
`test_*.py` files) plus **4 gated `image_exec`** exec tests (deselected by
default; run via `mise run smoke-exec`) and Bats scenarios under `infra/`.

## Running tests

```bash
# Full pytest suite (from repo root):
uv run --project python pytest tests/ -x -q

# Single file:
uv run --project python pytest tests/test_audit.py -x -q

# Single test by nodeid:
uv run --project python pytest tests/test_config.py::test_container_paths -x -q

# Bats tests (require bats-core):
bats tests/infra/
```

**Always `--project python`**, never `--directory python` — `--directory`
changes cwd and breaks `Path(__file__).parent.parent` resolution in the
test fixtures.

## Working in this directory

- **Imports from `python/src/`:** tests add
  `python/src` to `sys.path` at module import. New tests should follow
  the same pattern rather than requiring `pip install -e`.
- **Zero inline suppressions:** `noqa`, `type: ignore`, `pylint: disable`,
  `nosec` are rejected by the `no_lint_skip` hk step — applies to test
  files too.
- **Subprocess usage:** `test_audit.py` and `test_shell_integration.py`
  shell out. Use absolute paths (`Path(__file__).parent.parent.absolute()`)
  so tests pass regardless of pytest invocation cwd.
- **Parametrize over hardcoding:** `test_bootstrap.py` and
  `test_shell_integration.py` use `@pytest.mark.parametrize` over tool
  name lists. Add new tools to those lists rather than copying tests.
- **Named constants for magic numbers:** `test_image_smoke.py` uses
  `_PLAIN_BYTES_VALUE = 512` etc. rather than inline literals.

## CI integration

- `contract-preflight` job runs `uv run --project python pytest tests/
  -x -q` as a blocking gate.
- `smoke-test` job runs the image smoke check separately (not pytest).
- Test failures must be investigated, not suppressed. See
  `.claude/rules/zero-skip-policy.md`.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
