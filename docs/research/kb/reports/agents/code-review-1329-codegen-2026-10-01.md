# /code-review high — #1329 `64fd545e..a9e633d1`

Reviewer: built-in `/code-review` (forked), effort high. Persisted verbatim by the coordinator.

---

Eight angles run, findings deduplicated, 10 kept. I armed the top finding live: a pyproject that uses `[[tool.datamodel-codegen.jobs]]` (an array of tables) makes `codegen_check_main` raise an uncaught `AttributeError: 'list' object has no attribute 'values'`. I also ran the real gate on HEAD as a control, and it returned rc=0 (in sync). This lane wrote nothing, so `findings.md` and the report file still need persisting.

```json
[
  {
    "file": "python/src/dotfiles_setup/codegen_check.py",
    "line": 107,
    "summary": "codegen_check_main only catches OSError/KeyError/TOMLDecodeError/ValueError. A malformed config raises AttributeError or TypeError, main() turns that into sys.exit(1), and the result reads as DRIFT. That is the exact error/drift collapse the DriftVerdict enum was introduced to end.",
    "failure_scenario": "Armed: pyproject with `[[tool.datamodel-codegen.jobs]]` (array of tables) → job_outputs calls `jobs.values()` → AttributeError escapes codegen_check_main → main.py:3144 `logger.exception` + `sys.exit(1)` → hk/caller sees rc 1 = DRIFT ('regenerate') on a check that never decided. The same happens with `output = 5` (TypeError in the Path join)."
  },
  {
    "file": "python/src/dotfiles_setup/main.py",
    "line": 3146,
    "summary": "Wrong depth: the schema's $comment says every uncaught exception exiting 1 is the defect DriftVerdict fixes, but the generic handler still does `sys.exit(1)` for any unexpected exception (and re-raises RuntimeError, which also exits 1). Each check has to list exceptions on its own instead of the CLI mapping 'unexpected failure' to ERROR (2).",
    "failure_scenario": "Any drift-style subcommand (codegen-check today, the next DriftVerdict consumer tomorrow) that hits an exception not on its own list exits 1, so a crashed check unlocks a producer on a drift-free tree. Fix it once in main(), e.g. `sys.exit(DriftVerdict.ERROR)` in the generic handler, instead of per-check except tuples."
  },
  {
    "file": "python/verification/suites.toml",
    "line": 3001,
    "summary": "The contract token hard-codes the generator version (`codegen = [\"datamodel-code-generator==0.83.0\"]`), so every Renovate bump of the codegen group fails `mise run verify` / contract-preflight until someone hand-edits suites.toml.",
    "failure_scenario": "Renovate opens 'Update datamodel-code-generator to 0.84.0' → pyproject no longer contains the 0.83.0 literal → workflow.codegen-toolchain-wired fails → bot PR blocked or needs manual edits. knowledge-base's currency.toml already records this exact trap ('codegen-version-literal-is-load-bearing-in-a-test'). Bind a version-agnostic token such as `codegen = [\"datamodel-code-generator==`."
  },
  {
    "file": "python/pyproject.toml",
    "line": 200,
    "summary": "The comment says the pin 'Mirrors knowledge-base's setup', but KB pins `datamodel-code-generator[protobuf]==0.76.0` while this repo pins 0.83.0. The generator is also not in this repo's currency.toml or pin-parity, so the two repos' generators drift silently.",
    "failure_scenario": "The two repos already resolve different generator versions (0.76.0 vs 0.83.0), so the same schema plus the same settings table can render different code across them. Nothing here reports currency for the new tool, unlike KB's tracked `[tool.datamodel-code-generator]` currency entry."
  },
  {
    "file": "mise.toml",
    "line": 8,
    "summary": "`[deps.uv] auto=true run=\"uv sync --locked\"` is an exact sync of the default groups only, so it removes the `codegen` group each time it fires. The new hk/mise steps then have to reinstall it through `uv run --group codegen`.",
    "failure_scenario": "A mise deps auto-sync strips datamodel-code-generator and its deps from python/.venv. The next `mise run lint` codegen_check re-resolves and installs them, which needs network when the uv cache is cold, and fails (uv error → ERROR/lint red) when offline. Sync and reinstall churn on every deps trigger."
  },
  {
    "file": "python/src/dotfiles_setup/codegen_check.py",
    "line": 89,
    "summary": "When the generator binary is missing, check() returns ERROR even though the stale scan has already found definite drift (orphaned modules), so a known DRIFT is reported as 'could not decide'.",
    "failure_scenario": "A generated/orphan.py exists and the run lacks `--group codegen` (e.g. a bare `uv run --project python dotfiles-setup codegen-check`): stderr names the orphan, but the rc is 2. A caller that regenerates or deletes on rc 1 does nothing."
  },
  {
    "file": "python/src/dotfiles_setup/codegen_check.py",
    "line": 59,
    "summary": "The stale scan globs only top-level `generated/*.py`, yet the docstring says the directory is generator-owned and 'any module in it other than __init__.py must be some job's output'. Orphaned subpackages (datamodel-codegen modular/directory output) and stray `.pyi` files are never flagged.",
    "failure_scenario": "A job that wrote `generated/foo/` (modular output) is renamed or removed → `generated/foo/__init__.py` and `generated/foo/models.py` stay importable but are flagged by neither the stale scan nor native `--check` → stale models remain in use while the gate is green."
  },
  {
    "file": "hk.pkl",
    "line": 381,
    "summary": "The codegen_check step has no `glob`, so every hk run (pre-commit and check) does a `uv run --group codegen` sync, starts datamodel-codegen, and runs ruff check and ruff format per job, even when no schema, pyproject, uv.lock or generated file changed.",
    "failure_scenario": "Every unrelated commit (e.g. a markdown edit) pays the generator plus 2×ruff subprocess cost per job, and that cost grows as jobs are added. A glob such as [\"schemas/*.schema.json\", \"python/pyproject.toml\", \"python/uv.lock\", \"python/src/dotfiles_setup/generated/**\"] would skip it."
  },
  {
    "file": "python/src/dotfiles_setup/generated/drift_verdict.py",
    "line": 7,
    "summary": "Possible duplicate: DriftVerdict re-adds a 0/1/2 exit-code IntEnum that is already importable as `kb_setup.result.Rc` (OK/FINDINGS/BAD_REQUEST, a dependency already on this venv). Its 2 means BAD_REQUEST rather than ERROR, so the match is partial. Hand-written siblings `CurrencyCode`/`PluginHealthCode` (also 0=OK, 1=DRIFT/OUTDATED) stay unconverted.",
    "failure_scenario": "The repo now has multiple parallel exit-code vocabularies with overlapping integers but different member names and meanings. The new python/AGENTS.md says enums are 'generated, never hand-written', yet the existing ones stay hand-written, which creates the drift the enum was meant to stop."
  },
  {
    "file": "tests/test_codegen_check.py",
    "line": 52,
    "summary": "The test docstring says 'refresh.yml and hk read these as raw rcs', but nothing in .github (refresh.yml included) consumes DriftVerdict or codegen-check. The test's stated contract is false.",
    "failure_scenario": "A future reader keeps the 0/1/2 ints frozen for a refresh.yml consumer that does not exist, or trusts that refresh.yml branches on rc 2 when it does not. `git grep` over .github finds no codegen-check/DriftVerdict reference."
  }
]
```
