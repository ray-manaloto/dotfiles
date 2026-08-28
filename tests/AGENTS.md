<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-07 | Updated: 2026-04-07 -->

# tests/ — Pytest + Bats Test Suite

## Purpose

Repo-root-level test suite. Tests live here (not under `python/tests/`)
because they exercise the repo as a whole, not just the python package.

## Key Files

The per-file index lives in `tests/TEST-INDEX.md` — read it when you need to
know what a given test file covers, or before adding one.

It is split out because agnix **AGM-003** caps an `AGENTS.md` at 12,000 chars
for **Windsurf** compatibility (real and vendor-documented:
<https://docs.windsurf.com/windsurf/cascade/memories> — "Limited to 12,000
characters per file"; `AGENTS.md` is "processed by the same Rules engine").
It is referenced, NOT `@import`ed: agnix rejects `@import` in an `AGENTS.md`
(Claude-only syntax in an agent-agnostic file) and `claude_md_import_stub`
requires every non-`.claude/` `CLAUDE.md` be solely `@AGENTS.md`. So the index
is on-demand reference — which is what it should be anyway.

Total: **2,491 pytest tests** run by default (`pytest tests/` collects all
`test_*.py` files) plus **10 gated exec tests** deselected by default — 4
`image_exec` (`mise run smoke-exec`, needs Docker + the `:dev` image) and 6
`codex_exec` (`mise run codex-lane-e2e`, spawns the real `codex` CLI and
**costs credits** — 4 paid calls) — and Bats scenarios under `infra/`.

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

Three anti-patterns have already cost this repo real bugs. All are **silent
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
- **Both arms, one axis** — you pinned the true and the false branch of the
  condition you changed, and stopped. That is not coverage: enumerate every
  axis the condition *interacts with*, which is derivable with no judgement —
  **the axes are the union of the function's own parameters and every subject
  field read by any predicate it calls** (for `classify()`, that is its
  parameters plus every `Node` field its predicates read). The `classifier_axes`
  gate derives this for you — but only for **same-module predicates called by
  bare name**; for an imported or method predicate it is blind, and you carry
  the rule yourself. When the table gains a cell, add the axis; **never edit an expected value to make a test pass**,
  which converts an independent expectation into a transcription of behaviour.
  ⚠️ The mutation result that reads as proof is this shape's tell:
  **"deleting the fix breaks ONLY the arm you just wrote" is the SIGNATURE OF
  THE FAILURE, not evidence of quality** — it means test space and fix space
  are the same size, which is exactly the condition under which an unenumerated
  neighbouring cell exists. This is NOT a licence to skip mutation testing, and
  it does not soften `probes-need-a-control-arm.md`: the mutation here is a
  GOOD one — deleting the fix is the realistic regression — and its narrow
  blast radius is a fact about your AXIS ENUMERATION, not about the mutation.
  All three mutation-verified fixes in #601's review
  loop directly caused the NEXT round's HIGH finding, and the phrase went into
  three commit bodies as a boast
  (`docs/research/kb/reports/session-20260806-review-loop-reflection.md`).

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
