# Cold review — #1329 codegen fix round (round 2)

- Subject: `git diff a9e633d1..6d7617c3` (base `a9e633d11156a0e4927707f209eda8e573594319`, head `6d7617c3373b11f45b54ffb86c11bb92bddb646f`)
- Branch: `feat/1329-codegen-toolchain` (worktree `dotfiles.worktrees/s29-00b-finish-20261001`)
- Reviewer: cold-reviewer (Opus), diff-only, probes in `/tmp` scratch clones only
- Memory: consulted (`.claude/agent-memory-local/cold-reviewer/`)
- Stop condition: BOUNDED. There are 5 enumerated questions. Answering them completes the round.

## Status

COMPLETE. All 5 questions are answered.

## Verdict

**SHIP WITH FIXES.** Of the five prior MEDIUMs, F1, F3, F4 and F5 are closed, each re-armed with its original arm
and a control. F2 is only partly closed.
- **Closed shapes:** deleted or syntax-broken generated module, malformed job config, and an AttributeError in the
  config now exit 2.
- **Still exit 1:** a NameError or TypeError in the generated module, and any failing eager import in main.py.
  Each lands in `main.py:3166-3168` `sys.exit(1)`.
- **Unbound fail-closed lines:** the two lines that carry the F2 fix are bound by neither the contract nor a test.
  Three realistic mutants (R4, R5, R6) flip 2→1 with the suite and all 32 tests green.
- **Symptom sniff:** the F3 fix matches upstream's exact warning text, and no real-generator test pins it. A
  reworded warning (a simulated bump of the deliberately unbound pin) re-opens F3 with every test green.

Q4: one small scope widening (doc_refs) and one unguarded "verbatim" claim. Q5: nothing depends on referencing
0.37.

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| R2-F1 | MEDIUM | F2 is only partly closed. The lazy dispatcher catches only `ImportError, SyntaxError`, so a NameError or TypeError raised while importing the gate or the generated module, or any failing eager import in main.py, reaches main.py's catch-all, which exits **1 (DRIFT)**. That contradicts the dispatcher's own docstring ("hand-broken generated module … Imported here, it is ERROR (2)") and the suite's "a broken generated module is rc 2, never 1". | `python/src/dotfiles_setup/main.py:626`, `:3166-3168`, `:617-622`; `python/verification/suites.toml:2987` | `/tmp/cr-1329r2/arms.log`: N1 (`IntEnumm` NameError) rc=1, N2 (metaclass TypeError) rc=1, B10 (unrelated eager import raises) rc=1. N1's stderr carries `Unexpected command failure`. Controls B4, A4, B5, B6 and N3 give rc=2. |
| R2-F2 | MEDIUM | The two lines that carry the F2 fix, the dispatcher's `except ImportError, SyntaxError:` and `codegen_check_main`'s `except Exception:`, are bound by neither `require_lines` nor any test. Three realistic regressions survive suite and tests. `test_any_unanticipated_failure_is_an_error_not_drift` feeds an *anticipated* `CodegenConfigError` (a ValueError), so it passes against the pre-diff except tuple. | `python/src/dotfiles_setup/main.py:626`; `python/src/dotfiles_setup/codegen_check.py:181`; `python/verification/suites.toml:2999-3027`; `tests/test_codegen_check.py:190-212` | `/tmp/cr-1329r2/mutants.log`. R4 (drop SyntaxError): suite 0, tests 0, behaviour rc 1 (unmutated 2). R5 (second eager DriftVerdict consumer in `classifier_tables.py`, plus the generated module deleted): 0 / 0 / rc 1 (2). R6 (except reverted to the pre-diff tuple, plus `[tool] datamodel-codegen = 5`): 0 / 0 / rc 1 (2). Control (formatter branch disabled): suite 1, tests 1. |
| R2-F3 | MEDIUM | F3's fix is a symptom sniff on upstream's exact warning text, and the only test injects the repo's own constant, which makes it tautological against upstream. A generator bump that rewords the warning (the pin is deliberately unbound, so Renovate bumps freely) re-opens F3 with every test green. Python's warning filters also gate it: under `PYTHONWARNINGS=ignore` a broken ruff config reads as DRIFT. This is the shape `.claude/rules/probes-need-a-control-arm.md` rule 9 forbids. | `python/src/dotfiles_setup/codegen_check.py:53`, `:157`; `tests/test_codegen_check.py:162-170` | `/tmp/cr-1329r2/reword.log`. Scratch-venv `base.py` reworded + `line-length = "x"`: gate rc=**1**, tests rc=0 (32 passed). Text restored: rc=2. `/tmp/cr-1329r2/arms.log` W1: `PYTHONWARNINGS=ignore`, rc=1. The repo sets PYTHONWARNINGS nowhere (0 hits vs control `HK_MISE` 4). Live arms B9/C1/C2 confirm 0.83.0 does print the text on stderr (`base.py:2263`). |
| R2-F4 | LOW | A side effect of the F1 fix: the generator emits a docstring-less `class Struct(_Struct, forbid_unknown_fields=True): pass`, which the repo's ruff rejects (D101). No schema edit can supply that docstring, so the first Struct job will fail hk `ruff` while `codegen-check` passes. That falsifies the comment "(ruff's D101 needs one)". | `python/pyproject.toml:232`, `:240` | `/tmp/cr-1329r2/f1b.log`: a realistic Struct job (custom header + package `__init__`) gives `ruff check` rc=1 with the single error `probe.py:10:7 D101`, and `ruff format --check` rc=0. Control: the committed pilot gives `ruff check` rc=0. |
| R2-F5 | LOW | The `poetry.lock` and `runtime.txt` exemptions are added to doc_refs' GLOBAL allowlist, so every in-scope agent doc may now cite them stale. The module already has a path-scoped precedent for vendored skills (`DOC_PATHSPECS` `:!.claude/skills/graphify/SKILL.md`). | `python/src/dotfiles_setup/doc_refs.py:96-99` (precedent `:84`) | `/tmp/cr-1329r2/docrefs.log`. `.claude/rules/do-not.md` citing absent `runtime.txt`: rc=0. Positive control `zz-not-a-file.txt`: rc=1. Entries removed: rc=1. |
| R2-F6 | LOW | "Vendored verbatim by `--install-skill`" holds at 0.83.0, but nothing keeps it true. The pin is deliberately unbound and no gate diffs the vendored skill against the pinned package's `resources/datamodel-code-generator`, so a Renovate bump leaves both copies silently stale. | `.agnix.toml:41-46`; `tests/test_skills_mirror.py:229-232`; `python/verification/suites.toml:2987` | `diff -r` resource vs `.claude` copy rc=0, vs `.agents` copy rc=0, control vs a different skill rc=1. Grep for `install-skill`/`resources/datamodel` over src/hk/mise/suites/tests/renovate finds only a docstring. Control `graphify_skill_surface`: 5 files. |
| R2-F7 | LOW | `require_lines` tests set membership. The bound line `assert _real_check(root) == DriftVerdict.DRIFT` occurs twice, so either real-generator drift arm can be deleted. The new hk `glob` line is unbound too. | `tests/test_codegen_check.py:253`, `:266`; `hk.pkl:384`; `python/src/dotfiles_setup/verify.py:376-389` | `/tmp/cr-1329r2/q3_extra.log`: dropping the schema-drift test gives suite 0 (31 passed). Narrowing the glob gives suite 0. The glob's pre-commit consequence is **UNVERIFIED** (hk pre-commit not armed). CI `hk run check --all` should still select the step via `python/pyproject.toml`, which is an inference. |
| R2-F8 | INFO | The agnix exclusion drops every rule for the three reference files, where `[[overrides]] disabled_rules` could have scoped it to the two rule classes that fire. | `.agnix.toml:41-46` | `/tmp/cr-1329r2/agnix_arm.log`: with the exclusion removed, 6 `Unclosed XML tag` + 1 XP-003, all in `references/cli-options.md`. Head rc=0. |
| R2-F9 | INFO | The vendored SKILL.md's availability steps (`uvx`, `pipx run`, `uv run --with`, `pip install`) bypass the locked `codegen` group that hk says is "never PATH". This is guidance, not a gate, and `codegen-check` catches version-skewed output loudly. | `.claude/skills/datamodel-code-generator/SKILL.md:30-55` | read |

## Q1 — prior MEDIUMs F1-F5 re-armed

**Method.** Each arm ran in the scratch clone `/tmp/cr-1329r2/repo`, detached at `6d7617c3`, with
`GIT_CONFIG_GLOBAL` set to an empty file. Every arm goes through the real entrypoint, `uv run --project python
--locked --group codegen dotfiles-setup codegen-check`, and the clone is reset with `reset --hard` + `clean -fd`
between arms. Runner: `/tmp/cr-1329r2/arms.py`. Log: `/tmp/cr-1329r2/arms.log`.

### F1 (`extra-fields = "forbid"` was a no-op for msgspec) — CLOSED

`/tmp/cr-1329r2/f1.py` → `f1.log`. The probe generated a Struct with the head's `[tool.datamodel-codegen]` table
and a probe job; the schema has a nested `$ref` and an array of `$ref`.

| Config | `forbid_unknown_fields=True` in source | top-level unknown | nested unknown | in-array unknown | valid control |
|---|---|---|---|---|---|
| head (full) | 1 | rejected | rejected (`$.child`) | rejected (`$.kids[0]`) | accepted |
| without `use-generic-base-class` | 0 | accepted | accepted | accepted | accepted |
| without `extra-fields` | 0 | accepted | accepted | accepted | accepted |

Two control arms show the probe discriminates. The repo's own tests
(`test_generated_structs_reject_unknown_fields` and its control) also pass (32 passed, in `reword.log`'s control
run).

**Side effect of the fix (finding R2-F5).** The fix makes the generator emit
`class Struct(_Struct, forbid_unknown_fields=True): pass`, which has no docstring. I ran a realistic Struct job
(custom file header, package `__init__.py`, `/tmp/cr-1329r2/f1b.py` → `f1b.log`) and then the repo's ruff 0.16.5
with the repo's `[tool.ruff]`:
- `ruff check` rc=1, with exactly one error: `probe.py:10:7: D101 Missing docstring in public class`, on the base
  class.
- `ruff format --check` rc=0.
- Control: the committed pilot gives `ruff check` rc=0.

No schema edit can fix this, because the base class has no schema node. The pyproject comment
"`use-schema-description` … (ruff's D101 needs one)" (`python/pyproject.toml:240`) therefore does not hold for the
class this fix introduces. The first Struct-emitting job will fail hk's `ruff` step while `codegen-check` passes,
which is round 1's F9, now certain to recur.

### F2 (a broken check reads as DRIFT) — PARTIALLY CLOSED

| Arm | Shape | rc | Expected |
|---|---|---|---|
| A0 | control, clean tree | 0 | 0 |
| A1 | control, hand edit adds TIMEOUT=124 | 1 | 1 |
| B4 | SyntaxError in the generated module | **2** | 2 (was 1) |
| A4 | generated module deleted | **2** | 2 (was 1) |
| B5 | `output = 7` | **2** | 2 (was 1) |
| B6 | jobs as an array of tables | **2** | 2 (was 1) |
| N3 | `[tool] datamodel-codegen = 5` (AttributeError) | 2 | 2 |
| B10 | unrelated eager import in main.py raises | **1** | 2, still 1 |
| N1 | generated module hand edit raises NameError | **1** | 2 |
| N2 | generated module hand edit raises TypeError (metaclass conflict) | **1** | 2 |

N1's stderr carries `Unexpected command failure`. That is the logger call in `main.py:3166-3168`, which then runs
`sys.exit(1)`. `run_codegen_check` (`main.py:624-628`) catches only `ImportError, SyntaxError`, so anything else
raised while importing the gate or the generated module escapes to that catch-all.

### F3 (a formatter failure reads as DRIFT) — CLOSED for every prior arm

| Arm | Shape | rc | Text on stderr |
|---|---|---|---|
| B9 | `line-length = "x"` | **2** | yes: `base.py:2263: UserWarning: Failed to format code: RuntimeError('Ruff command failed with exit code 2 …` |
| C1 | venv ruff moved aside, PATH falls back to the unversioned mise shim | **2** | yes (`exit code 1 … No version is set for shim: ruff`) |
| C2 | no ruff anywhere: venv ruff aside, PATH = real uv dir + `/usr/bin:/bin` | **2** | yes (`Ruff executable was not found`) |
| W1 | B9 + `PYTHONWARNINGS=ignore` | **1** | no |

### F4 (hk step commented out, contract stayed green) — CLOSED

`/tmp/cr-1329r2/mutants.py` → `mutants.log`, with the detail in `m1_reason.log`. The M1 mutant comments out the
whole step (including the new `glob`). Results:
- Suite rc=1, failing on `hk.pkl: missing line 'check = "uv run --project python --locked --group codegen
  dotfiles-setup codegen-check"'`.
- Control M0: suite rc=0, tests rc=0 (32 passed).

### F5 (fail-open guard unpinned) — CLOSED

The M3 mutant narrows the guard to `if result.returncode == DriftVerdict.ERROR:`. Suite rc=1 (the line is bound)
and tests rc=1 (2 failed: the new `(3,0,ERROR)` and `(-9,0,ERROR)` rows). It is now killed twice.

## Q2 — broken checks that report 0/1 instead of 2

**Does 0.83.0 really print `Failed to format code` on stderr?** Yes, by both source and live run.
- Source: `datamodel_code_generator/parser/base.py:2259-2267`. `_format_body_safe` catches `Exception` around the
  formatter and calls `warnings.warn(f"Failed to format code: {exc!r}. Emitting unformatted output.")`.
- Every ruff failure raises `RuntimeError` into that wrapper: `format.py:827-853` (`_run_ruff_command`) and
  `:865-875` (`_find_ruff_path`).
- The wrapper's only callers are `base.py:6429` and `:6464`.
- The one formatter path that bypasses it is `format_directory` (`format.py:888-898`, via `__init__.py:1599-1601`).
  It is reached only when `defer_formatting` is set, which requires a suffix-less (directory) `output`
  (`__init__.py:1326`). No job has one today.
- `cli_migration_warning_scope` (`deprecations.py:252-258`) installs no warnings filter.
- Live: B9, C1 and C2 above all carried the text on stderr.

The match is still a symptom sniff, and the environment controls it (W1: `PYTHONWARNINGS=ignore` → rc=1). The
repo sets PYTHONWARNINGS nowhere. A grep over the tree excluding `.venv`/`docs` returned 0 hits, with a control arm
below.

## Q3 — require_lines call-site binding

Handler semantics, read from the source rather than assumed: `verify.py:329-403` `require_lines` normalises
whitespace and then tests set **membership**. There is no count, no position and no enclosing-context check. A
line present anywhere in the file satisfies it.

Occurrence count per bound line at the head (`/tmp/cr-1329r2/count_lines.py`):
- 21 of the 22 lines occur exactly once.
- `assert _real_check(root) == DriftVerdict.DRIFT` occurs twice (`tests/test_codegen_check.py:253,266`), so either
  arm can be deleted without failing the suite.
- Control: an invented absent line counts 0.

### Mutation matrix

Each mutant runs the suite (`dotfiles-setup verify run --suite workflow.codegen-toolchain-wired`), the full test
file (`tests/test_codegen_check.py`, which includes the real-generator tests), and a behaviour arm through the
real gate. Log: `/tmp/cr-1329r2/mutants.log`.

| Mutant | Realistic? | suite | tests | behaviour rc (unmutated) | Survives? |
|---|---|---|---|---|---|
| M0 none | control | 0 | 0 (32 passed) | — | — |
| CTL formatter branch → `if False:` | control (destroys a bound line) | **1** | **1** | 1 (2) | killed |
| R7 formatter branch moved below the DRIFT return | yes (reorder) | 0 | **1** | 1 (2) | killed by tests |
| **R4** dispatcher `except ImportError, SyntaxError:` → `except ImportError:` | yes ("simplify" a PEP 758 except that reads like py2) | **0** | **0** | SyntaxError in generated: **1** (2) | **survives** |
| **R5** a second eager consumer: `classifier_tables.py` imports `DriftVerdict` | yes. The schema `$comment` names S29-00b's drift checks as the enum's next consumers, and main.py imports every subcommand module eagerly | **0** | **0** | generated module deleted: **1** (2) | **survives** |
| **R6** `codegen_check_main` `except Exception:` → the PRE-DIFF tuple `(OSError, KeyError, tomllib.TOMLDecodeError, ValueError)` | yes (a partial revert or merge resolution back to the base text) | **0** | **0** | `[tool] datamodel-codegen = 5`: **1** (2) | **survives** |

Unmutated behaviour controls, all rc=2: generated module deleted, SyntaxError in the generated module,
AttributeError config, broken ruff config.

**Answer.** Every line the contract names is bound at a whole-line call site. F4's mutant is dead. But the two
lines that carry the F2 fix are not in the contract:
- `except ImportError, SyntaxError:` (`main.py:626`);
- `except Exception:` (`codegen_check.py:181`).

The tests do not reach their behaviour either:
- `test_a_gate_that_cannot_import_is_an_error_not_drift` monkeypatches `importlib.import_module` to raise
  `ImportError`, so R4's SyntaxError half is never exercised. R5 bypasses the dispatcher entirely.
- `test_any_unanticipated_failure_is_an_error_not_drift` feeds an array of jobs, which raises the *anticipated*
  `CodegenConfigError` (a `ValueError`). It therefore passes against the pre-diff tuple (R6), so its name claims
  more than it tests.

The suite description clause "main.py's lazy dispatcher (a broken generated module is rc 2, never 1); … fail-closed
branches" (`suites.toml:2987`) is therefore stated but not enforced.

## Q4 — vendored skill + .agents mirror gate weakening

| Gate | What the diff did | Weakened? | Evidence |
|---|---|---|---|
| **agnix** (`.agnix.toml:41-46`) | excludes `.claude/skills/datamodel-code-generator/references/**` | **Scoped as claimed.** It hides exactly 6 `Unclosed XML tag` errors and 1 XP-003 hard-coded `.claude/` warning, all in `references/cli-options.md`. SKILL.md stays validated. It is still a whole-path exclude (every rule) where the repo's own `[[overrides]] disabled_rules` mechanism could have scoped it to the two rules that fire. | `/tmp/cr-1329r2/agnix_arm.log`. Head `agnix . --strict` rc=0 "No issues found"; with that one line removed rc=1 with the 7 findings. `.agents/skills/**` was already wholly excluded before this diff (`.agnix.toml`, ChatGPT-sync entry), so the mirror adds no new blind spot. |
| **doc_refs** (`doc_refs.py:96-99`) | adds `poetry.lock` and `runtime.txt` to the GLOBAL `_ALLOWED_ABSENT` | **Yes, slightly.** Any agent doc in scope (`AGENTS.md`, rules, every `SKILL.md`) can now cite either name stale and pass. The module already has a path-scoped precedent (`DOC_PATHSPECS` `:!.claude/skills/graphify/SKILL.md`, `doc_refs.py:84`). | `/tmp/cr-1329r2/docrefs.log`. Head + `.claude/rules/do-not.md` citing absent `runtime.txt`: rc=0. Positive control `zz-not-a-file.txt`: rc=1. Entries removed: rc=1 (also flags `SKILL.md:117`, `:156`). |
| **md budget** (`kb-setup md-budget`) | none | No. `_SKILL_RE = ^\.(claude\|agents)/skills/.*/SKILL\.md$` budgets both copies (227 lines < `SKILL_LINE_LIMIT` 500). `references/*.md` match no class, which is pre-existing for context7. | `kb_setup/md_budget.py:88,156` (venv copy) |
| **skill listing** (doctor `[listing]`) | +1 project skill | No. The row is 671 chars (description 647 < 1,536 cap). The listing is 40,961 against a ceiling of 48,110 (40,290 without it). The only over-cap entry is pre-existing (`antigravity-delegate` 1,789). | `/tmp/cr-1329r2/listing.log` (control: `adversarial-review` present) |
| **skills mirror** (`tests/test_skills_mirror.py:226-247`) | the exact-set assertion widened to 6 named (skill, file) pairs | No. Still an exact set, so a new vendored `references/` dir fails it. The dropped `"context7-cli" in str(source)` is subsumed. | Mirror and source `cmp` byte-identical (SKILL.md + 3 references) |
| **verbatim claim** | "vendored verbatim by `datamodel-codegen --install-skill claude-code`" | Holds at 0.83.0. **Nothing keeps it true across a Renovate bump.** The pin is deliberately unbound (`suites.toml:2987`), and no gate diffs the vendored copy against `datamodel_code_generator/resources/datamodel-code-generator`. | `diff -r` against the package resource rc=0 for `.claude` and `.agents`, and rc=1 for the control (a different skill). Grep for `install-skill`/`resources/datamodel` across src/hk/mise/suites/tests/renovate: only a test docstring. Control `graphify_skill_surface`: 5 files. |
| (guidance, not a gate) | SKILL.md `:30-55` tells agents to run `uvx datamodel-codegen`, `pipx run`, `uv run --with …` or `pip install` | Not a gate weakening. In this repo those commands bypass the locked `codegen` group that `hk.pkl:379-380` says is "never PATH". `codegen-check` would catch the version-skewed output loudly. | `.claude/skills/datamodel-code-generator/SKILL.md:30-55,217` |

## Q5 — referencing 0.37.0 -> 0.36.2

**Answer: no code or test depends on 0.37 behaviour, and 0.37.0 has none.**

- **Lock delta.** The fix round's only version change in `python/uv.lock` is `referencing 0.37.0 → 0.36.2`. Fifteen
  packages were added and none removed (`/tmp/cr-1329r2/lockdiff.log`).
- **Cap provenance.** It is verified: `jsonschema_path-0.3.4.dist-info/METADATA` declares `Requires-Dist:
  referencing (<0.37.0)`. The chain is jsonschema-path ← openapi-spec-validator ← `datamodel-code-generator[all]`
  (`/tmp/cr-1329r2/q5.log`).
- **Dependents of referencing:**
  - base: jsonschema, jsonschema-specifications;
  - head: the same two, plus jsonschema-path.
  - jsonschema 4.26.0 requires `referencing>=0.28.4`.
- **Importers.** Nothing in `python/src` imports `referencing` or `jsonschema`. The two importers in the
  environment use only the validator API:
  - `tests/test_orchestration_contracts.py:11,25-26` (`Draft202012Validator`);
  - `kb_setup/plugin_validate.py:184-187` (`validator_for`).
- **Upstream delta.** v0.36.2...v0.37.0 is 102 commits and 14 files. In `referencing/`, the changes are
  `Union`→`|`, `typing.Callable`→`collections.abc.Callable`, and removed `type: ignore` comments (`_core.py`,
  `jsonschema.py`, `retrieval.py`, `_attrs.pyi`). The rest is metadata: `requires-python >=3.10`, a 3.14 classifier,
  and the changelog entry "Declare support for Python 3.14. Drop support for Python 3.9"
  (`/tmp/cr-1329r2/referencing_patch.txt`).
- **Live.** On the head venv (referencing 0.36.2, jsonschema 4.26.0), `pytest tests/test_orchestration_contracts.py
  tests/test_codegen_check.py` gives 52 passed, rc=0.
- **Pin/currency configs.** `pin-parity.toml`, `currency.toml`, `renovate.json` and `doctor.toml` contain no
  `referencing`. The only hit is the pyproject cost comment (control: `jsonschema-path` counts 1 in pyproject).
- Residual (INFO, recorded as an accepted cost in `python/pyproject.toml:202-204`): the dev-only `codegen` group now
  caps a transitive dependency of runtime-path jsonschema users for the whole lock. A future jsonschema needing
  `referencing>=0.37` would be held back silently by resolution.

## Outside the enumeration (ticket recommendations, not change requests)

- `python/pyproject.toml:211-214` says ruff "discovers [config] by walking up from the caller's cwd … A run from
  anywhere else needs `--settings-path`". Upstream instead chdirs to the OUTPUT directory for file outputs
  (`datamodel_code_generator/__init__.py:2399`). CodeFormatter's `settings_path` defaults to `Path.cwd()`
  (`format.py:544-545`), and ruff runs with `cwd=self.settings_path` (`format.py:841`). Discovery therefore starts at
  `generated/`, and today's outcome (`python/pyproject.toml`'s `[tool.ruff]`) is unchanged. Source-read only, not
  armed.
- Deferred formatting (directory outputs, `__init__.py:1326`, `:1599-1601`) calls `format_directory`
  (`format.py:888-898`) without the `_format_body_safe` wrapper. A future directory-output job's ruff failure would
  therefore surface as a generator exception, not the sniffed text. No job is affected today.

## Limits

- `mise run lint`, the full `pytest tests/` and the full `mise run verify` were **not** run on the head. The run
  covered the one suite, the two test files, `agnix . --strict` and `check-doc-refs`, all in the scratch clone.
- The worktree was not modified except for this report. `findings.md`/`progress.md` were not written because the
  caller restricted worktree writes to this file.
- The hk pre-commit consequence of the unbound `glob` (R2-F7) is UNVERIFIED.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — subject diff `a9e633d1..6d7617c3`; scratch clone arms.
- [koxudaxi/datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator) — installed 0.83.0 source read from the venv: `parser/base.py` (`_format_body_safe`), `format.py` (ruff invocation and resolution, `format_directory`), `__main__.py` (Exit enum, `_run_jobs`/`_run_jobs_text` exception flow, `--check` comparison), `__init__.py` (settings_path, chdir, deferred formatting), `agent_skill.py` + `resources/datamodel-code-generator` (bundled skill).
- [python-jsonschema/referencing](https://github.com/python-jsonschema/referencing) — v0.36/v0.37 releases and the `v0.36.2...v0.37.0` compare via `gh api`.
- [python-jsonschema/jsonschema](https://github.com/python-jsonschema/jsonschema) — installed 4.26.0 METADATA (`referencing>=0.28.4`) only.
- [p1c2u/jsonschema-path](https://github.com/p1c2u/jsonschema-path) — installed 0.3.4 METADATA (`referencing <0.37.0`) only.
- [agent-sh/agnix](https://github.com/agent-sh/agnix) — the pinned 0.56.1 binary run on the scratch tree.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `kb_setup.md_budget` (venv copy) for the skill budget classes.
