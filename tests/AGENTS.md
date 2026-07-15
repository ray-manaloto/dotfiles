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
| `test_hook_guard.py` | pytest | PreToolUse mise-tasks-only guard (`dotfiles_setup.hook_guard`) — deny/redirect rules, false-positive guards, JSON contract, `match()` rule lookup, per-rule `since`/`name` integrity (a rule with a malformed `since` silently classifies every match as history and darkens the audit's bypass alarm), the cd-prefixed compound denials (pinned: they pass with NO cd-unwrap in `decide()`, since `_CMD` re-anchors on the `&&`/`;`/newline every prefix ends in — probe 2026-07-14 refuting the predicted "chained-command evasion"), and the #265 inert-span masking (`_inert_masked`): the 2 real transcript false positives verbatim, every separator quoted, heredoc bodies (`<<EOF`/`<<'EOF'`/`<<-EOF`) — each paired against a recall pin, since the fix trades recall for precision and must not overshoot. The `npx` denial is pinned SEPARATELY as a true positive (its `||` is outside quotes): the audit reports "3 denials" as one number, so a fix driving `blocked` to 0 would look like success while destroying the guard's only correct denial — the bar is 3 → 1 |
| `test_hook_selfcheck.py` | pytest | Host-side hook self-check (`dotfiles_setup.hook_selfcheck`, the ship/land `hook-selfcheck` gate) — settings.json wiring + Bash-matcher assertions incl. the SessionEnd command-audit hook, and an end-to-end real-repo pass driving the wired PreToolUse guard |
| `test_command_audit.py` | pytest | Command-audit transcript scanner (`dotfiles_setup.command_audit`, the self-learning mise-tasks loop) — env-aware transcript discovery, defensive JSONL parse, attempt→result pairing (a denied Bash call is recorded exactly like an executed one; only the `stdout`-bearing `toolUseResult` separates them), the bypass/blocked/pre_rule/mise/diagnostic/one_off classifier (cd-prefix unwrap; era×outcome split — probe 2026-07-14: of 155 rule-matching commands, 147 were pre-rule, 3 denials, **0** bypasses), denials grouped by rule identity not command head, report rendering, and the `--output` path the SessionEnd hook uses (repo-anchored resolve, no-clobber on a transcript miss, real-CLI flag pin) |
| `test_memory_index.py` | pytest | Memory-index curation checker (`dotfiles_setup.memory_index`) — env-aware memory-dir discovery (sibling of the transcripts, so the shared path encoding is pinned), index parse, distinctive-fact extraction across title AND hook, and per-kind normalized matching (`25.8GB` vs `25.8 GB` is ONE fact — the prototype's over-report and the reason a checker gets ignored). Pins the index_only-vs-elsewhere split (only a fact recorded nowhere else fails), that `audit_index` drops MEMORY.md itself (the index holds every entry ⇒ including it returns a silent all-pass), that orphans/`--refs` never fail the rc, that an unreadable entry fails rather than being skipped in silence, and the first live finding verbatim: a hook claiming CI green at `3adff36` against a topic file saying `c2cecd7` — index-only but STALE, which is why the report describes instead of prescribing "migrate". The rest pin bugs an adversarial review probe-verified pre-merge, each a silent false negative: `load_cutoff_line` enforcing the BYTE cap (the only one reachable at ~149 B/line — the first draft checked lines alone and printed OVER while exiting 0); `_SHA` needing an `a-f` letter (a digit-only test read `research-20260714-*` slugs and run ids as shas, then prefix-matched them "present"); `_elsewhere` refusing to downgrade a size (17.5GB of image vs of free disk share a number, not a fact); and `inbound_refs` matching a bare stem (brackets-or-`.md` missed 4 live citations and told the reader a cited memory had none) |
| `test_apt_repo.py` | pytest | apt repository enumerator (`dotfiles_setup.apt_repo`, #251) — suite naming incl. the trap that development is the UNNUMBERED suite (`-23` is a 404), deb822 parse via python-debian, injected-fetcher seam (no network), `Section: libs` filter, and the `"latest"`/`--pin` TOML render. Pins the OpenMP naming trap: `libomp-22-dev` matches no substring of "openmp", so a list written from memory is wrong |
| `test_tool_currency.py` | pytest | Daily tool-currency signal (`dotfiles_setup.tool_currency`) — release-link backends, report rendering |
| `test_renovate.py` | pytest | Renovate status signal (`dotfiles_setup.renovate`) — app-id/privilege check, report rendering |
| `test_autofix.py` | pytest | autofix.ci artifact applier (`dotfiles_setup.autofix`) — additions, traversal/shape/deletion refusal |
| `test_bash_budget.py` | pytest | Zero-bash-logic enforcer (`dotfiles_setup.bash_budget`) — allowlist/growth/shrink/stale logic, real-repo `allowlist == tracked` pin, end-to-end CLI |
| `test_gcc_sha.py` | pytest | gcc-latest sha auto-repair (`dotfiles_setup.gcc_sha`, #249) — pin parse/rewrite (strict subn), injected-fetcher sha compute, drift/no-drift repair, check-mode dry-run, CLI rc |
| `test_shell_integration.py` | pytest | Tool reachability in login shells (mise, chezmoi, uv, pixi, claude, gemini, codex) |
| `infra/foundation.bats` | Bats | Bash-level foundation checks (shell script integration) |
| `infra/runtimes.bats` | Bats | Runtime installation checks (bash) |

Total: **638 pytest tests** run by default (`pytest tests/` collects all
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

## What a good test is here

Tests verify behavior through a **public interface** — an exported function,
a CLI's rc and output, a generated script's real execution — never through
implementation details. Code can change entirely; the test shouldn't. The tell
for an implementation-coupled test is that it breaks under a refactor while
behavior hasn't changed.

Two anti-patterns have already cost this repo real bugs. Both are **silent
false negatives**: they surface as a green suite, never as a failure, so only
a deliberate probe finds them.

- **Tautological** — the assertion recomputes the expected value the way the
  code does, so it passes by construction and can never disagree with the
  code. Expected values must come from an **independent source of truth**: a
  known-good literal, a worked example, the real artifact. The four
  `test_memory_index.py` bugs above are this shape.
- **A probe with no control arm** — a check that can only pass is not a check.
  Pin the FAIL direction next to the pass: tier-1 identity really fails on a
  wrong hash, tier-3 on a wrong ref, and every `_inert_masked` case is paired
  with a recall pin. A 2026-07-15 hook probe "passed" while its control proved
  the hook had never fired at all.

## Mocking

Mock at **system boundaries only** — the network (GHCR, `gh`, release feeds),
Docker, the clock, the filesystem where `tmp_path` won't do. Never mock our
own modules, internal collaborators, or anything we control: that couples the
test to structure and is exactly how the implementation-coupled tell appears.

At a boundary, prefer **injecting** the dependency over constructing it inside
the function. `gcc_sha`'s injected fetcher and `hook_guard`'s pure `decide()`
are the pattern already in use here — the seam is a parameter, so the test
substitutes a value and needs no patching at all.

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
