# Cold review — #1329 codegen toolchain (`64fd545e..a9e633d1`)

- **Subject:** `git diff 64fd545e..a9e633d1`. Head `a9e633d11156a0e4927707f209eda8e573594319`,
  base `64fd545ec32ea1acb54b7dca9a4dda7a1708ddac`, branch `feat/1329-codegen-toolchain`. There are 13
  files: +586/−2 lines.
- **Reviewer:** cold-reviewer (Opus). Diff-only, by ref. I consulted memory at
  `.claude/agent-memory-local/cold-reviewer/` and applied its lessons (bind consumers, not
  producers; tokens that sit in comments; plumbing-only git in scratch).
- **Spec:** issue #1329, with the owner's substitution of the DriftVerdict exit-code enum as the pilot.
  The reference implementation is knowledge-base `pyproject.toml` `[tool.datamodel-codegen]`,
  `kb-codegen`/`kb-codegen-check` (`mise.toml:899-905`) and `kb_setup/guard_codegen.py`, at KB
  `d8a205da`.
- **Method:** every arm ran in a scratch clone (`/tmp/cr-1329/repo`, detached at the subject head)
  with its own venv. That venv was built by `uv run --project python --locked --group codegen`.
  `GIT_CONFIG_GLOBAL` was set to an empty file, and the tree was reset between arms with
  `reset --hard` + `clean -fd`. Read-only runs in the real worktree were `mise run codegen-check`,
  `mise run lint` and `mise run token-check`. Arm scripts are in `/tmp/cr-1329/*.py` and logs in
  `/tmp/cr-1329/*.log`.
- **Status:** COMPLETE.

## Verdict

**SHIP WITH FIXES.** The gate discriminates correctly on every in-scope drift shape the brief
named: hand edit, unregenerated schema change, top-level orphan, deleted module.
`mise run lint` is green with `codegen_check` executing.

Four MEDIUM findings should be fixed in this unit of work:
- **F1:** `extra-fields = "forbid"` is a no-op for msgspec output in this config. That fails the
  spec AC and breaks the "mirrors KB" claim.
- **F2 and F3:** the 0/1/2 contract the pilot exists to guarantee collapses to 1 on at least six
  non-drift inputs.
- **F4:** the contract is passed by a commented-out hk step. A native `require_lines` handler
  already kills that case (armed).

F5 is a fail-open branch that no test pins.

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| F1 | MEDIUM | `extra-fields = "forbid"` has no effect on generated msgspec Structs: no `forbid_unknown_fields`, and an unknown field decodes silently. KB's table carries `use-generic-base-class = true`, which this table drops; that key is what carries the kwarg. The spec AC "extra fields forbidden" is therefore unmet and the pilot cannot exercise it, because it is an enum. | `python/pyproject.toml:218` (and the "mirror" claim at `:199`, `:206`) | `/tmp/cr-1329/q6a.log`. Full config: `forbid_unknown_fields` absent. Adding `use-generic-base-class = true`: present. Generic base without `extra-fields`: absent, which is the two-arm control. Decoding `{"klass":"pr-open","evidence":"x","bogus":1}` into the generated `Issue` returns `Issue(...)` with no error. The KB carrier is `knowledge-base/pyproject.toml:364` → `generated/fetch_receipt.py:11` `class Struct(_Struct, forbid_unknown_fields=True)`. |
| F2 | MEDIUM | `codegen-check` exits **1 (DRIFT)** on inputs where the check could not decide. Examples: an uncaught `TypeError`/`AttributeError` in `job_outputs`, any import-time failure anywhere in `main.py`'s import graph, and a deleted or syntax-broken generated module. That last case also takes down **every** `dotfiles-setup` subcommand. This contradicts the task's "2 error" and the schema's "the three must never collapse". | `python/src/dotfiles_setup/codegen_check.py:108` (catches only 4 types), `:28` (module-level import of a generated file), `python/src/dotfiles_setup/main.py:30`, `schemas/drift-verdict.schema.json:9` | `/tmp/cr-1329/armsB.log` and `armsA.log`, through the real entrypoint: B5 `output = 7` gave rc=1 (TypeError). B6 jobs as array gave rc=1 (AttributeError). B10 unrelated module raising at import gave rc=1. B4 SyntaxError in the generated module gave rc=1. A4 deleted module gave rc=1 (ModuleNotFoundError traceback, not a verdict). Controls answering 2 correctly: B7 missing `output` key, B12 no `jobs`, A5c output outside root, B11 stale lock (uv). Today no consumer branches on 1 vs 2 (hk is nonzero-only), so the harm is the false contract plus the first future producer that trusts it. |
| F3 | MEDIUM | A formatter failure reads as DRIFT. The generator wraps ruff failures in a `UserWarning` and emits **unformatted** code (upstream `parser/base.py:2258-2266`), so `--all-jobs --check` returns 1 and `codegen-check` reports drift. Triggers include a broken `[tool.ruff]` value, a venv without ruff (the PATH fallback here is a versionless mise shim), or ruff missing everywhere. | `python/src/dotfiles_setup/codegen_check.py:95-101` (treats native rc=1 as drift unconditionally) | `/tmp/cr-1329/armsB.log` B9 (`line-length = "x"`): rc=1, stderr `Failed to format code ... Emitting unformatted output`. `/tmp/cr-1329/arms_ruff.log` C1 (venv ruff moved aside, PATH shim): rc=1. C2/C2b (no ruff anywhere, native and via `dotfiles-setup codegen-check`): rc=1 each. C0 control after restore: rc=0. KB's `_native_check_ran` markers would also be fooled, because the output carries a real `---` diff. Fix shape: treat `Failed to format code` on stderr, or the warning promoted to an error, as ERROR. |
| F4 | MEDIUM | The `workflow.codegen-toolchain-wired` contract binds the hk step by **substring**. Commenting the step out ("temporarily disabled") removes it from the `check` hook while the contract and tests stay green. The repo already ships `require_lines` (whole line, whitespace-normalised), which kills this mutant. | `python/verification/suites.toml:2990`, `:2999-3017` | `/tmp/cr-1329/q5.log` M1: suite rc=0, tests rc=0. `/tmp/cr-1329/m1.log` `pkl eval -x 'hooks["check"].steps.keys.contains(...)'`: `codegen_check` true→**false**, control `ruff` true→true, token count still 1. `/tmp/cr-1329/m1_fix.log` with `handler = "require_lines"` + `per_path_lines` (test tokens widened to full `def` lines): unmutated rc=0, M1 **rc=1** (`hk.pkl: missing line 'check = ...'`). M2 (step deleted) and M5 (`--group codegen` dropped) both fail the suite, which are the discriminating controls. |
| F5 | MEDIUM | The fail-open guard `if rc not in {IN_SYNC, DRIFT}` is pinned by neither the contract nor the tests, because the parametrised table feeds only rc∈{0,1,2}. The realistic narrowing to `if rc == DriftVerdict.ERROR:` passes suite + tests and maps a generator exit of 3 (its own `KeyboardInterrupt` code) or a signal kill (−9) to **IN_SYNC (0)**. | `python/src/dotfiles_setup/codegen_check.py:96`; `tests/test_codegen_check.py:89-99` | `/tmp/cr-1329/q5.log` M3: suite rc=0, tests rc=0, behaviour `rc3-> 0 rc-9-> 0`. Unmutated control: `the generator itself failed (rc=3)` / `(rc=-9)` → ERROR. Add (3,0,ERROR) and (−9,0,ERROR) rows. |
| F6 | LOW | The stale scan is non-recursive (`glob("*.py")`), so an orphan in `generated/sub/` or a stray `.pyi` is invisible. Yet `generated/__init__.py` says "Every module here except this one is written by `mise run codegen`". KB fixed exactly this as its F4 (`rglob`, `guard_codegen.py` `_stale_generated_files`). | `python/src/dotfiles_setup/codegen_check.py:59`; `python/src/dotfiles_setup/generated/__init__.py:4-7` | `/tmp/cr-1329/armsA.log`: A3b subdir orphan rc=0; A3c `orphan.pyi` rc=0; A3 top-level orphan rc=1 (control). |
| F7 | LOW | Nothing confines a job's output to `generated/`, or even to `python/`. Such a job is accepted, and removing it later leaves an orphan that no check can see. The pyproject comment "every output stays under python/" and the AGENTS.md layout (`→ src/dotfiles_setup/generated/<name>.py`) are unenforced. | `python/pyproject.toml:204-205`; `python/AGENTS.md:112-113`; `codegen_check.py:43-51` | `/tmp/cr-1329/armsB.log`: A5a output `src/dotfiles_setup/outside_enum.py` rc=0; A5b same job removed with the module left behind rc=0; A5d output `../tests/gen_outside.py` (outside python/) regenerated, rc=0. A5c outside the repo root gave rc=2, which is correct. |
| F8 | LOW | Q-CLAIM: "Code generation is the ONLY way models and enums are produced" / "generated, never hand-written" is stated in the present tense. At this head there are **10** hand-written `Struct` classes and **40** hand-written `Enum` classes outside `generated/`, and no gate rejects a new one. Narrow it to "new models", or ticket a ban/migration gate (Q-SCOPE: sibling under #1326). | `mise.toml:1348`; `python/pyproject.toml:196`; `python/AGENTS.md:111`; `python/verification/suites.toml:2987` | `grep -rn -E '^class \w+\([^)]*Struct'` → 10 (e.g. `gate_result.py:42`, `sdlc_team.py:64`). `...Enum` → 40 (e.g. `gate_result.py:32`). The control grep hits `generated/drift_verdict.py:7`. |
| F9 | LOW | Lint and codegen-check can disagree with no byte divergence. The generator's ruff pass accepts unfixable violations (upstream `format.py:844`: rc=1 with stdout is accepted). A schema whose object `$defs` lack `description` (D101), or one with a long description (E501), therefore generates a module that `codegen-check` passes (rc=0) and hk `ruff` rejects (rc=1). The only remedy is a schema edit, and only E501 is documented. | `schemas/drift-verdict.schema.json:9`; `python/pyproject.toml:223` (`use-schema-description`) | `/tmp/cr-1329/q2.log` rich-verdict: hk `ruff check` rc=1 (D101 `class Issue`), `codegen-check` rc=0. long-desc: E501 + D101, rc=1 vs rc=0. Control: a planted `import os` gives hk ruff rc=1, format rc=1. |
| F10 | LOW | Q-CLAIM: the test docstring says "refresh.yml and hk read these as raw rcs, so the ints are the contract". At this head refresh.yml invokes no DriftVerdict producer and branches only on `outcome == 'failure'` (`refresh.yml:350-475`), and hk is nonzero-only. The schema `$comment` frames the enum as the answer to S29-00b F4, but no F4 consumer adopts it in this diff. | `tests/test_codegen_check.py:52`; `schemas/drift-verdict.schema.json:9` | `grep -rn 'codegen\|DriftVerdict' .github/` → 0 hits (control: the same grep over `python/src` hits `main.py:30`). |
| F11 | LOW | Q-CLAIM: "see the comments there for why `use-annotated`/`field-constraints` and `disable-timestamp` are non-optional". KB has no comment on `disable-timestamp` (only the setting at KB `pyproject.toml:342`). KB's use-annotated rationale was measured on 0.75.1/0.76.0 and does **not** reproduce on the 0.83.0 pinned here: dropping either or both keys leaves the output byte-identical (4 `Meta(` in every arm). The keys are harmless, but the cited reason is stale. | `python/pyproject.toml:206-208` | `/tmp/cr-1329/q6a.log`. The sensitivity control (the `use-generic-base-class` arm) changes the output, so edits do take effect. |
| F12 | LOW | Q-CLAIM: the contract text says "Bound at CALL SITES, not definitions" and "its tests bind ... the decode/reject arms". The two test tokens are `def` lines (definitions), the decode test is unbound, and the load-bearing `dir = "{{config_root}}/python"` line is unbound. Deleting that line passes the contract but fails loudly at use. | `python/verification/suites.toml:2987`, `:3015-3016`; `mise.toml:1354` | `/tmp/cr-1329/q5.log` M4: suite rc=0, tests rc=0; behaviour `uv run --project . ...` at the repo root rc=2 `No [tool.datamodel-codegen] section found`, i.e. loud. |
| F13 | LOW | The message "the generator itself failed (rc=2)" is printed for **input** rejections: an invalid-JSON schema, a deleted schema, and an invalid schema type. That misattributes the fault to the tool. | `python/src/dotfiles_setup/codegen_check.py:97` | `/tmp/cr-1329/armsB.log` B1/B2/B3: rc=2. The verdict is correct and only the wording is wrong. |
| F14 | INFO | The Q2 premise "the generator pins its own ruff" is false. datamodel-code-generator 0.83.0 declares no ruff dependency. Its `_find_ruff_path` uses `Path(sys.executable).parent / "ruff"` (the dev-group ruff 0.16.5 from uv.lock) and otherwise falls back to PATH. hk's `ruff`/`ruff_format` steps (`uv run --project python ruff`) run the same binary with the same config (`python/pyproject.toml`). | upstream `format.py:865-874`; `hk.pkl:61-89`; `python/uv.lock` (`datamodel-code-generator` deps: no ruff) | See Q2 below. |

## Question log

### Q1 — Does `codegen-check` / hk `codegen_check` discriminate both ways on a real tree?

Yes, for every named shape, through `uv run --project python --locked --group codegen dotfiles-setup
codegen-check` (byte-identical to the mise task and hk step `run`/`check`). Baseline in the real
worktree: `mise run codegen-check` rc=0 (`/tmp/cr-1329/A0-real.log`).

| Arm | Mutation | rc | Correct? |
|---|---|---|---|
| A0 | none (control) | 0 | yes |
| A1 | hand edit: add `TIMEOUT = 124` | 1 | yes |
| A1b | hand edit: extra trailing blank line | 1 | yes |
| A1c | hand edit: comment-only line | 1 | yes |
| A1d | hand edit: docstring reworded | 1 | yes |
| A2 | schema: add enum 3/TIMEOUT, no regen | 1 | yes |
| A2b | schema: `$comment` only, no regen | 0 | yes (output unaffected) |
| A2c | schema: description edit, no regen | 1 | yes |
| A2d | schema: varname rename, no regen | 1 | yes |
| A3 | orphan `generated/orphan.py` | 1 | yes |
| A3n | same orphan, **native** `--all-jobs --check` only | 0 | proves the gap the scan closes |
| A3b | orphan `generated/sub/orphan.py` | **0** | no → F6 |
| A3c | orphan `generated/orphan.pyi` | **0** | no → F6 |
| A4 | delete `generated/drift_verdict.py` | 1 (traceback) | verdict right, mechanism wrong → F2 |
| A4n | same, native only | 1 (`MISSING:`) | yes |
| A4b | delete `generated/__init__.py` | 0 | acceptable (hk ruff INP001 would catch it; not armed) |
| A5a | job output outside `generated/`, regenerated | 0 | accepted → F7 |
| A5b | that job removed, module left | **0** | no → F7 |
| A5c | job output outside repo root | 2 | yes |
| A5d | job output `../tests/…` (outside python/) | 0 | accepted → F7 |

### Q2 — Can generated bytes differ between the generator's ruff pass and hk's ruff/ruff_format?

**Bytes: no divergence found. Lint verdicts: yes, they can disagree (F9).**

- Both passes run the same binary. The generator resolves `python/.venv/bin/ruff` via
  `Path(sys.executable).parent` (upstream `format.py:865-874`). hk's steps run `uv run --project
  python ruff` (`hk.pkl:63,86`) and hit the same file, ruff 0.16.5 from `python/uv.lock`. The
  generator's formatter cwd is the output dir, and the ruff config resolved from there is
  `python/pyproject.toml` (KB documents the cwd coupling at KB `pyproject.toml:314-319`).
- On the committed file, hk `ruff check` gives rc=0 and `ruff format --check` gives rc=0
  (`/tmp/cr-1329/q2-ruff*.log`).
- On three generated schemas (rich Struct with constraints/`$ref`/enum/array/nullable; long
  description; `types.py` stdlib-shadow name), `ruff format --check` gave rc=0 every time. hk
  fix-mode (`ruff check --fix` then `ruff format`) left the generator's bytes **identical** in all
  three (`/tmp/cr-1329/q2.log`).
- Control: a planted `import os` gives hk ruff rc=1 and format rc=1, so the probe discriminates.
- Disagreement exists at the lint-verdict level (F9). Byte agreement also depends on the venv
  having the dev-group ruff. Without it the generator falls back to PATH, which here is a mise shim
  with no version set, and F3 follows.

### Q3 — Does CI's lint job actually run `codegen_check` with the group installable?

**Yes by configuration and by local execution of the CI command. No CI run of this head exists**
(`gh run list --branch feat/1329-codegen-toolchain` → `[]`), so on-runner behaviour is **UNVERIFIED**
and is inferred from the following:
- `ci.yml:123` runs `hk run check --all`. `codegen_check` is in `allSteps`, which is spread into
  `check` (`hk.pkl:845-848`). `pkl eval -x 'hooks["check"].steps.keys.contains("codegen_check")'`
  returns `true` (`/tmp/cr-1329/m1.log`).
- No `HK_SKIP_STEPS` is set anywhere in `.github/`. The only `HK_SKIP_HOOKS` hits are refresh.yml
  and gcc-sha-repair, not the lint job.
- `mise run lint` on the subject tree gave **rc=0**. The log shows `❯ codegen_check` …
  `codegen-check: every generated module matches its job` … `✔ codegen_check`
  (`/tmp/cr-1329/lint.log:232-290`).
- Installability on linux: `python/uv.lock` has a `py3-none-any` or `manylinux…x86_64` wheel for all
  13 new packages. The probe discriminates: `ty` has 0 none-any wheels.
- Exact `uv sync --locked` (`mise.toml:5-8` `[deps.uv] auto`) **removes** the codegen group (14
  packages uninstalled). The next `codegen-check` reinstalls it, rc=0. That is self-healing, not a
  finding.
- **Silent-skip/pass paths:** F4 (step commented out, contract green), F6/F7 (scope holes), F3
  (formatter env reads as drift, which is loud but mislabelled). The step has no `glob`, so it also
  runs on every pre-commit.

### Q4 — ERROR (2) vs DRIFT (1): inputs where a broken check reports 1 or 0

**Reports 1 when broken:**
- B4: SyntaxError in the generated module.
- B5: `output = 7` (TypeError).
- B6: jobs as an array (AttributeError).
- B9: broken `[tool.ruff]`, formatter downgraded to a warning.
- B10: unrelated import-time error.
- A4: deleted generated module (ImportError).
- C1/C2/C2b: venv ruff absent.

These are F2 and F3.

**Reports 0 when broken:** none on the subject code. One mutant does it (F5: a narrowed error branch
gives 0 for rc 3/−9). B8 (an unknown generator option such as `use-annotatedd = true`) gives rc=0
because the generator silently ignores unknown keys. That is a config-typo blind spot, **UNVERIFIED**
whether 0.83.0 offers a strict-config option.

**Correctly 2:**
- B1 invalid JSON.
- B2 schema deleted.
- B3 invalid schema type.
- B7 missing `output`.
- B11 stale lock (uv `--locked`).
- B12 no `jobs`.
- A5c output outside the repo root.

B13 (a string in an integer enum) gives rc=1 and the generator emits `ERROR = "x"`. Treated as real
drift (the schema changed), not a check failure.

### Q5 — Are the contract tokens each bound once to a call site? Mutation results

- `mise run token-check` returned rc=0 for all 13 tokens across 6 files, each matching exactly once
  (`/tmp/cr-1329/tok1.log`, `tok2.log`).
- Call-site status:
  - The mise `run =` lines, the hk `check =` line, the `main.py` handler, the codegen_check
    `stale =`/`rc = run(...)`/`if stale or ...` lines and the pyproject pin/output lines are
    call-site-shaped.
  - The two test tokens are **definitions** (`def …(`).
  - `from … import DriftVerdict` is an import (F12).

| Mutant | Realistic? | suite | tests | Survives? |
|---|---|---|---|---|
| M0 none | control | 0 | 0 | — |
| M1 hk step commented out | yes ("temporarily disable") | **0** | 0 | **yes** → F4. pkl eval shows the step gone |
| M2 hk step deleted | yes | 1 | 0 | killed (control) |
| M3 error branch narrowed to `rc == ERROR` | yes | **0** | **0** | **yes** → F5. rc 3/−9 → 0 |
| M4 `[tasks.codegen]` loses `dir` | yes | 0 | 0 | survives the contract, fails loudly at use (rc=2) → F12 |
| M5 hk step drops `--group codegen` | yes | 1 | 0 | killed (control) |
| M6 stale result ignored in the verdict | contrived (token kept) | 0 | 1 | killed by tests |

### Q6 — Q-CLAIM on every added comment/help/docstring

| Clause | Location | Enforcing line / arm | Status |
|---|---|---|---|
| "every generated model matches its schema" | `hk.pkl:377` | native `--check` (`codegen_check.py:95`) | holds for job outputs |
| "no generated module is orphaned" | `hk.pkl:377-378` | `stale_modules` (`:54-61`) | top level only → F6 |
| "A hand edit … or a schema edit without `mise run codegen`, fails here" | `hk.pkl:378-379` | A1–A2d | holds |
| "The generator comes from the locked `codegen` group, never PATH" | `hk.pkl:379-380`; `mise.toml:1349-1350`; AGENTS.md | `generator_binary()` `:68-75` | holds for the generator. Its **ruff** falls back to PATH (F14/F3) |
| "ONLY way models and enums are produced" / "never hand-written" | `mise.toml:1348`; `pyproject.toml:196`; `AGENTS.md:111`; suites `:2987` | none | false at this head → F8 |
| "`dir` is python/ because datamodel-codegen discovers its table from the cwd's pyproject.toml" | `mise.toml:1350-1351` | upstream `__main__.py:859-873` walks up from cwd and stops at `.git` | true. M4 is loud |
| task description "(rc: 0 in sync, 1 drift, 2 error)" | `mise.toml:1358` | `:96-108` | partially false → F2/F3 |
| "Exact pin, isolated group … never a PATH copy" | `pyproject.toml:197-198` | uv.lock `specifier = "==0.83.0"` | holds |
| "Mirrors knowledge-base's setup" / "Settings mirror knowledge-base's proven table" | `pyproject.toml:199`, `:206` | none | false on a load-bearing key → F1. Also pin 0.83.0 vs KB 0.76.0, and top-level `use-schema-description` (KB: per-job only) |
| "Paths are relative to THIS file's directory" | `pyproject.toml:203-204` | upstream `_resolve_pyproject_relative_paths` (`__main__.py:1227-1239`) | true, independent of cwd |
| "so every output stays under python/" | `pyproject.toml:204-205` | none | unenforced → F7 (A5d) |
| "the formatter pass picks up this file's ruff config" | `pyproject.toml:205-206` | formatter cwd = output dir → walk-up | true for outputs under python/ |
| "see the comments there for why use-annotated/field-constraints and disable-timestamp are non-optional" | `pyproject.toml:206-208` | KB comment covers use-annotated only | stale/dangling → F11 |
| "This gate adds one thing the native `--all-jobs --check` cannot see" | `codegen_check.py:8-10` | A3n rc=0 vs A3 rc=1 | true |
| "knowledge-base measured that gap … wrapping its check the same way" | `codegen_check.py:10-11` | KB `guard_codegen.py` docstring §2 | measured: true. "Same way": KB's scan is recursive and marker-keyed; this one is neither (F6) |
| "any module in it other than `__init__.py` must be some job's output" | `codegen_check.py:11-13`; `generated/__init__.py:4-7` | `:59` `glob("*.py")` | top level only → F6 |
| "2 the check itself could not decide" | `codegen_check.py:17` | `:96`, `:108` | partially → F2/F3 |
| "Job paths … relative to its own directory, which is also the generator's cwd" | `codegen_check.py:33-34` | `:95` cwd = `(root / PYPROJECT).parent` | true |
| `generator_binary` docstring | `codegen_check.py:69-73` | `:75` | true under `uv run` |
| "codegen-check: the generator itself failed" | `codegen_check.py:97` | — | misattributes input errors → F13 |
| main.py help "a module in generated/ has no … job" | `main.py:602-607` | `:59` | top level only (F6) |
| test docstring "refresh.yml and hk read these as raw rcs" | `tests/test_codegen_check.py:52` | none for refresh.yml | false at this head → F10 |
| schema `$comment` "must never collapse … before this enum every uncaught exception also exited 1" | `schemas/drift-verdict.schema.json:9` | `:108` catches 4 types | still collapses → F2. "Rejected … by Ray 2026-10-01" is **UNVERIFIED** (not checkable from the tree) |
| schema `$comment` "ruff's E501 applies to generated code too" | same | `pyproject.toml` `select=ALL`, no per-file ignore; q2 long-desc E501 | true (and D101 also applies → F9) |
| suites description "Bound at CALL SITES, not definitions" / "tests bind … decode/reject arms" | `suites.toml:2987` | tokens `:3015-3016` | partially false → F12 |
| hk-builtins-audit counts 75/47 | `docs/hk-builtins-audit.md:12,53` | the hk `hk_builtins_audit --check` step inside `mise run lint` rc=0 | holds |

## Spec AC cross-check (#1329, pilot substituted)

| AC | Status |
|---|---|
| Exact pin, isolated group; msgspec output; ruff-check+ruff-format; use-annotated + field-constraints; specialized enums; strict schema version + refs; disable timestamps | present (`pyproject.toml:200`, `:209-229`) |
| extra fields forbidden | **declared but not effective** for msgspec output → F1 |
| `mise run codegen` + `codegen-check` in hk, plus a stale scan | present. Scope holes F6/F7 |
| FAIL arms: hand edit / schema change without regen fail lint | armed A1–A2d (rc=1). Lint ran it (`lint.log`) |
| Pilot decodes a valid fixture and rejects an invalid value | `tests/test_codegen_check.py:41-48`. 14 tests passed in scratch (`q5.log` M0) |
| Gate matrix green | `mise run lint` rc=0 seen. pytest/verify for the whole tree were **not run by this review** (the target test file and the one suite passed) |

## Not done / limits

- No CI run exists for the head, so Q3's on-runner claim is an inference (UNVERIFIED).
- The caller restricted writes in the worktree to this report. Therefore `findings.md`,
  `progress.md` and the agent memory dir were **not** written. Proposed memory lessons are in the
  handback.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — subject diff, issue #1329 body,
  `gh run list` / `gh pr list` for the branch.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — reference
  `pyproject.toml` `[tool.datamodel-codegen]`, `kb-codegen*` tasks, `kb_setup/guard_codegen.py`, and
  generated models (local clone at `d8a205da`).
- [koxudaxi/datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator) — installed
  0.83.0 source read from the venv: `__main__.py` (Exit enum, pyproject discovery, path resolution),
  `format.py` (ruff resolution and rc tolerance), `parser/base.py` (format-failure warning).
