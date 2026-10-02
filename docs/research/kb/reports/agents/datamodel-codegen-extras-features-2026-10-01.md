# datamodel-code-generator 0.83.0: extras, the ruff formatters, features to adopt, and real-world configs

Date: 2026-10-01. Branch: `feat/1329-codegen-toolchain` (worktree `s29-00b-finish-20261001`).
Question: a jsonschema → `msgspec.Struct` project pinned to `datamodel-code-generator==0.83.0`
(`python/pyproject.toml:200`). (1) Which pip extras exist and what does `[all]` pull in? (2) How do
`--formatters ruff-check ruff-format` work? (3) Which other features should we adopt? (4) Are there real-world
`[tool.datamodel-codegen]` configs that use msgspec and ruff?

## Answer

**The sweep is complete for its declared inputs.** No mandatory gaps, no mirror gaps, and no failed reads were
reported. The named gaps are listed under Gaps. One upstream answer was settled by the **installed 0.83.0 wheel**
rather than by docs, because two of the fan-out sources disagree (see Conflicts resolved).

**Offline, agent-optimized access is already in place on this branch, but not committed yet.** It has two parts:
`docs/research/mintlify-cache/datamodel-code-generator/datamodel-code-generator/{llms.txt,llms-full.txt}`
(12,988 B and 1,405,335 B), and catalog row `docs/research/mintlify-catalog.md:97`. `git status` shows the cache
directory as untracked and the catalog as modified, so neither reaches another clone until it is committed. The
caller link (https://datamodel-code-generator.koxudaxi.dev) is mirrored at
`docs/research/kb/raw/datamodel-codegen-extras-features-2026-10-01/links/1.md`. Note that the site documents the
upstream **default branch**, which is about 104 commits past 0.83.0. Where the two differ, the installed wheel is
authoritative for us.

1. **Extras. 0.83.0 ships 12:** `all, black, debug, graphql, http, httpx2, isort, protobuf, ruff, ryaml, validation,
   watch`.
   - **`[all]`** equals black + debug + graphql + http + isort + protobuf + ruff + validation + watch. It
     deliberately **excludes `httpx2` and `ryaml`**.
   - **Installing `[all]` adds:** `pysnooper`, `graphql-core`, `httpx`, `grpcio-tools` (heavy), `ruff>=0.9.10`,
     `openapi-spec-validator` + `prance`, and `watchfiles`. black and isort come along regardless, because they are
     still **core** requirements in 0.83.0.
   - **For us:** none of this is needed for jsonschema → msgspec except `ruff`.
2. **Ruff formatters. Ruff is NOT bundled:** it is only the optional `ruff` extra, with a floor of `ruff>=0.9.10`
   and no upper bound.
   - **How it runs:** datamodel-codegen shells out to a `ruff` executable. It looks beside the running interpreter
     first, then on `PATH`. `ruff-check` runs `ruff check --fix --unsafe-fixes` and `ruff-format` runs
     `ruff format -`, in sequence.
   - **Which config it uses:** no config flag is passed. Ruff runs with `cwd` set to the formatter's
     `settings_path`, which on the emit path defaults to the **caller's working directory** (not simply the output
     directory), and `--settings-path` overrides it (corrected after adjudication; see Verification). Ruff's own
     discovery then walks up from there. For us that is `python/pyproject.toml [tool.ruff]`, the same config hk
     lints with, **only because both entrypoints run the generator from `python/`** (`mise.toml [tasks.codegen]`
     `dir`, and `codegen_check.py:156`). A run from the repo root without `--settings-path` could discover a
     different ruff config.
   - **Which ruff version runs here:** `python/.venv/bin/ruff`, 0.16.5, resolved by `uv.lock`. It arrives through
     the **`dev`** dependency group, not through a `[ruff]` extra. Our `codegen` group declares the bare package.
     It works today only because uv installs default groups.
   - **black/isort:** the current default formatters are still `(black, isort)`, and the documented **future**
     default is `builtin`.
     - Omitting `--formatters` emits the `format.default-formatters` deprecation.
     - Naming black or isort emits `dependency.external-formatters-optional`.
     - Our explicit `formatters = ["ruff-check", "ruff-format"]` avoids both. The real
       `datamodel-codegen --all-jobs --check` exited rc=0 with no warnings.
3. **Features: most of the high-value ones are already adopted.** In use now: named jobs plus `--all-jobs`; `--check`
   (inside `dotfiles-setup codegen-check`); `x-enum-varnames` (the DriftVerdict schema);
   `use-annotated`/`field-constraints`; `use-specialized-enum`; `disable-timestamp`; and `custom-file-header`.
   - **Worth adopting:** declare the `[ruff]` extra. Consider `--diff-against` for schema-change review. Keep the
     upstream Agent Skill and `--generate-prompt` as on-demand tools.
   - **Measured, do NOT adopt blindly:** the `standard-py314-20260909` preset. It **changes our output**: it
     lower-cases the enum members to `in_sync/drift/error`, overriding `x-enum-varnames` casing (from the msgspec
     group's `snake_case_field=True`). The docstring loss first reported here was an artifact of the probe arm
     (it omitted `use-schema-description`, which our real config sets); it is NOT a preset effect.
   - **Not yet needed:** profiles, custom templates, and remote-ref lock files. We have one model type, no
     template needs, and no remote `$ref`s.
4. **Real-world examples: no external repo combines msgspec with ruff formatters in a `[tool.datamodel-codegen]`
   table.** The code-search claim found only upstream itself, a fork of upstream, and our own knowledge-base. Each
   half exists separately in real repos:
   - ruff formatters with other model types: open-telemetry/opentelemetry-python (dataclasses) and
     Mirascope/mirascope (TypedDict);
   - a msgspec.Struct + ruff pairing in a script rather than a table: bmcfee/bopp (per the code-search notes; not
     read by me).

## Evidence

| # | Claim | URL or file:line | Quote |
|---|---|---|---|
| E1 | Installed version is 0.83.0, and it declares 12 extras | `python/.venv/lib/python3.14/site-packages/datamodel_code_generator-0.83.0.dist-info/METADATA` | `Provides-Extra: all` … `black` `debug` `graphql` `http` `httpx2` `isort` `protobuf` `ruff` `ryaml` `validation` `watch` |
| E2 | black and isort are CORE requirements in 0.83.0 | same METADATA | `Requires-Dist: black>=19.10b0; sys_platform != 'emscripten'` / `Requires-Dist: isort<9,>=4.3.21; sys_platform != 'emscripten'` |
| E3 | `[all]` pulls these packages and omits httpx2 and ryaml | same METADATA | `graphql-core>=3.2.3; extra == 'all'` … `grpcio-tools<2,>=1.62; extra == 'all'` … `prance>=0.18.2; extra == 'all'` … `ruff>=0.9.10; extra == 'all'` … `watchfiles>=1.1; extra == 'all'` (no `httpx2`/`ryaml` line under `all`) |
| E4 | The same extras list appears at the upstream tag | https://github.com/datamodel-code-generator/datamodel-code-generator/blob/0.83.0/pyproject.toml#L44 | `optional-dependencies.all = [ "datamodel-code-generator[black]", … "[watch]",` |
| E5 | Docs say `[all]` intentionally excludes httpx2 | `docs/research/mintlify-cache/.../llms-full.txt` (via the fan-out claim) | "`datamodel-code-generator[all]` includes the stable `http` extra but intentionally does not include the experimental `httpx2` extra." |
| E6 | The default formatters are black and isort | `python/.venv/.../datamodel_code_generator/_format_types.py:136` | `DEFAULT_FORMATTERS: tuple[Formatter, ...] = (Formatter.BLACK, Formatter.ISORT)` |
| E7 | The CLI help states the current and future defaults and the ruff install path | `datamodel-codegen --help` (installed 0.83.0, rc=0) | "Formatters (current default: black, isort; future default: builtin). For Ruff projects, use --formatters ruff-check ruff-format (install with pip install 'datamodel-code-generator[ruff]') … New 20260909 presets include builtin; explicit formatters override presets." |
| E8 | ruff is looked up beside the interpreter, then on PATH; it is not bundled | https://github.com/datamodel-code-generator/datamodel-code-generator/blob/0.83.0/src/datamodel_code_generator/format.py#L865 (format.py:865-874) | "Ruff executable was not found. Install it with `pip install 'datamodel-code-generator[ruff]'`." |
| E9 | The ruff-check command line | format.py#L855 (0.83.0) | `command: tuple[str, ...] = (ruff_path, "check", "--fix", "--unsafe-fixes")` |
| E10 | ruff runs with cwd = `settings_path` (caller cwd on the emit path, overridable by `--settings-path`; NOT simply the output dir, per adjudication, `__init__.py:1922,2689`), so ruff's native config discovery applies | format.py#L833 (0.83.0; settings_path at :544-555) | `result = subprocess.run(command, capture_output=True, check=False, cwd=self.settings_path,` |
| E11 | Docs: formatters read pyproject from the output directory and its parents | https://raw.githubusercontent.com/datamodel-code-generator/datamodel-code-generator/main/docs/formatting.md | "The effective search path starts from the output path directory, or the current working directory when no output path is available, and then checks parent directories." |
| E12 | The deprecation that fires when the formatter is unset | https://github.com/datamodel-code-generator/datamodel-code-generator/blob/0.83.0/src/datamodel_code_generator/deprecations.py#L127 | "Default formatters will change to builtin. Set --formatters or --preset explicitly; see --help." |
| E13 | The deprecation that fires when black or isort is named | `llms-full.txt:42127` | "Black/isort will become optional. Declare the corresponding extras; see --help." |
| E14 | Our config sets the formatters explicitly | `python/pyproject.toml:216` | `formatters = ["ruff-check", "ruff-format"]` |
| E15 | Our codegen group pins the bare package, and ruff comes from `dev` | `python/pyproject.toml:192,199` | `"ruff",` (in `dev`) / `codegen = ["datamodel-code-generator==0.83.0"]` |
| E16 | The installed ruff is 0.16.5, in the same venv | `python/.venv/lib/python3.14/site-packages/ruff-0.16.5.dist-info` | (directory present) |
| E17 | The real `--all-jobs --check` passes with no warnings | `uv run --project . --locked --group codegen datamodel-codegen --all-jobs --check` (cwd `python/`) | `rc=0`, empty stderr |
| E18 | Our config already uses jobs plus `--all-jobs` | `python/pyproject.toml:225`; `mise.toml:1355` | `[tool.datamodel-codegen.jobs.drift-verdict]` / `run = "uv run --project . --locked --group codegen datamodel-codegen --all-jobs"` |
| E19 | `--check` is already wired, wrapped by our gate | `python/src/dotfiles_setup/codegen_check.py:156` | `result = run([str(generator), "--all-jobs", "--check"], (root / PYPROJECT).parent)` |
| E20 | x-enum-varnames is already in use | `schemas/drift-verdict.schema.json` | `"x-enum-varnames": ["IN_SYNC", "DRIFT", "ERROR"]` |
| E21 | x-enum-varnames is parsed natively | https://github.com/datamodel-code-generator/datamodel-code-generator/blob/0.83.0/src/datamodel_code_generator/parser/jsonschema.py#L1075 | `x_enum_varnames: list[str \| None] = Field(default_factory=list, alias="x-enum-varnames")` |
| E22 | msgspec implies use-annotated, and the job path applies it in 0.83.0 | `python/.venv/.../datamodel_code_generator/__main__.py:721-731`, call site `:1305-1307` | `if config.output_model_type is DataModelType.MsgspecStruct and "use_annotated" not in explicit_fields: config.use_annotated = True` |
| E23 | **Measured:** a jobs-mode msgspec run with no `use-annotated` key still emits `Meta` constraints; the control (`use-annotated = false`) drops them | `/tmp/dmcg-arm/{a,b}` (both rc=0) | a: `name: Annotated[str, Meta(max_length=5)]` · b: `name: str` |
| E24 | Named jobs are experimental | https://raw.githubusercontent.com/datamodel-code-generator/datamodel-code-generator/main/docs/pyproject_toml.md | "Named batch jobs are experimental; their configuration schema, batch output, and transactional/watch execution contracts may change. Jobs always run sequentially in their TOML declaration order." |
| E25 | Profiles are reusable fragments, selectable per job | same page | "Profiles are reusable configuration fragments. A job is a runnable generation that supplies its own input and output and can select one profile." |
| E26 | Presets exist in 0.83.0, dated and immutable; the `py314` variants are present | `datamodel-codegen --help` and `preset.py:127-136` | `--preset {standard-py310-20260619, … practical-py314-20260909}` |
| E27 | The msgspec option group in the presets | `preset.py:380-387` | `title="msgspec Struct output", config=PresetConfig(snake_case_field=True, use_standard_primitive_types=True)` |
| E28 | The 20260909 presets select the builtin formatter | `preset.py:504-516` | "Format generated models without running an external formatter. For projects using Ruff, override with --formatters ruff-check ruff-format." |
| E29 | **Measured:** `preset = "standard-py314-20260909"` in pyproject is honoured under jobs, and it changes the DriftVerdict output | `/tmp/dmcg-arm/c` (rc=0) | `class DriftVerdict(IntEnum):` / `in_sync = 0` / `drift = 1` / `error = 2` (no docstring in this arm only because the arm omitted `use-schema-description`; with it the docstring is kept, members stay lowercase), against the committed `IN_SYNC = 0 …` |
| E30 | `--diff-against` exists | https://github.com/datamodel-code-generator/datamodel-code-generator/blob/0.83.0/src/datamodel_code_generator/arguments.py#L1374 | "Generate BASELINE_INPUT and the current --input into temporary outputs, then show the generated-code diff from baseline to current." |
| E31 | Remote-ref lock files exist (experimental) | arguments.py#L262 (0.83.0); `--help` lines for `--locked`/`--lockfile`/`--update-lock` | "Create or atomically update the selected remote lock after generation (experimental)." |
| E32 | The Agent Skill is bundled with the CLI and installs to `.claude/skills` | `python/.venv/.../datamodel_code_generator/agent_skill.py:37-38`; https://raw.githubusercontent.com/datamodel-code-generator/datamodel-code-generator/main/docs/coding-agent-skill.md | `case "claude-code": skill_directory = Path(".claude") / "skills"` / "The skill is bundled with the CLI and can be installed without checking out this repository." |
| E33 | The vendor skill is NOT installed in this repo | `ls .claude/skills \| grep -i -E 'datamodel\|codegen'` → rc=1, while the same `ls` lists `adversarial-review` etc. | (no match) |
| E34 | `--generate-prompt` exists, for asking an LLM about options | https://datamodel-code-generator.koxudaxi.dev (mirror `links/1.md`) | `datamodel-codegen --generate-prompt "Best options for Pydantic v2?" \| claude -p` |
| E35 | msgspec output must be selected explicitly; the default is Pydantic v2 | https://datamodel-code-generator.koxudaxi.dev (mirror `links/1.md`) | "When `--output-model-type` is omitted, datamodel-code-generator generates Pydantic v2 BaseModel output" |
| E36 | The official GitHub Action exists | https://datamodel-code-generator.koxudaxi.dev | `- uses: datamodel-code-generator/datamodel-code-generator@vX.Y.Z` |
| E37 | Real-world: OpenTelemetry uses ruff formatters with dataclasses and a custom template dir | `gh api repos/open-telemetry/opentelemetry-python/contents/pyproject.toml` (rc=0), pyproject.toml:191-204 | `output-model-type = "dataclasses.dataclass"` / `formatters = ["ruff-format", "ruff-check"]` / `custom-template-dir = "opentelemetry-configuration/codegen"` |
| E38 | Real-world: Mirascope uses ruff formatters with TypedDict | `gh api repos/Mirascope/mirascope/contents/python/pyproject.toml` (rc=0), :232-246 | `output-model-type = "typing.TypedDict"` … `formatters = ["ruff-check", "ruff-format"]` |
| E39 | Real-world: Airflow's task-sdk uses pydantic v2 with a custom formatter, not msgspec or ruff | `gh api repos/apache/airflow/contents/task-sdk/pyproject.toml` (rc=0), :251-267 | `output-model-type='pydantic_v2.BaseModel'` … `custom-formatters = ['datamodel_code_formatter']` |
| E40 | Control arm for the `gh api` contents probe | `gh api repos/open-telemetry/opentelemetry-python/contents/no-such-file-qx8v.toml` | `rc=1`, `gh: Not Found (HTTP 404)`, so the probe discriminates |
| E41 | Code search: msgspec + ruff-format in a `[tool.datamodel-codegen]` table occurs only in upstream, a fork, and our KB | https://github.com/search?q=%22tool.datamodel-codegen%22+msgspec+ruff-format+filename%3Apyproject.toml&type=code (fan-out claim; not re-run by me) | "datamodel-code-generator/datamodel-code-generator pyproject.toml; guardicore/datamodel-code-generator pyproject.toml; ray-manaloto/knowledge-base pyproject.toml" |
| E42 | The KB reference config (pinned to 0.76.0) uses the same msgspec + ruff shape plus a custom template dir | `knowledge-base/pyproject.toml:90,327-366` | `codegen = ["datamodel-code-generator[protobuf]==0.76.0"]` / `custom-template-dir = "schemas/templates"` / `use-generic-base-class = true` |
| E43 | `use-specialized-enum` requires Python 3.11+ | `llms-full.txt:28354`; `preset.py:361-364` | "Generate StrEnum/IntEnum for string/integer enums (Python 3.11+)." / `requires_python_strenum=True` |

### Code search

| query | role | source | count | rc |
|---|---|---|---|---|
| `tool.datamodel-codegen msgspec filename:pyproject.toml` | query | planner | 20 | 0 |
| `output-model-type msgspec.Struct filename:pyproject.toml` | query | planner | 2 | 0 |
| `datamodel-codegen ruff-format filename:pyproject.toml` | query | planner | 35 | 0 |
| `formatters ruff-check filename:pyproject.toml` | query | planner | 31 | 0 |
| `repo:datamodel-code-generator/datamodel-code-generator filename:README.md` | must-hit | planner | 1 | 0 |
| `qzvkwpt7nx9 filename:pyproject.toml` | known-absent | planner | 0 | 0 |
| `repo:cli/cli filename:README.md` | health | workflow | 9 | 0 |
| `repo:datamodel-code-generator/datamodel-code-generator filename:README.md` | must-hit | workflow | 1 | 0 |
| `repo:ray-manaloto/knowledge-base filename:README.md` | must-hit | workflow | 15 | 0 |

Code-search notes:

- The first query's top hits were apache/airflow `task-sdk/pyproject.toml`, lipu-linku/ilo, iscc/iscc-search and
  ray-manaloto/knowledge-base. The "msgspec" term matched somewhere in those files, not necessarily in the codegen
  table: Airflow's table is pydantic v2 (E39). lipu-linku/ilo and iscc/iscc-search were **not read**.
- The second query (2 hits): bmcfee/bopp uses `msgspec.Struct` with `ruff-check ruff-format` **in a script, not a
  `[tool.datamodel-codegen]` table**, plus ray-manaloto/knowledge-base.
- The third and fourth queries' top hits were open-telemetry/opentelemetry-python, Mirascope/mirascope,
  apify/apify-client-python and AISecurityLab/hackagent. The first two were read (E37, E38); apify and hackagent
  were not.
- A source-dive control from the fan-out claims (not in the table above): the broader query without
  msgspec/ruff-format returned total_count 126, and a fresh nonsense token returned 0.
- No row is rate-limited.

### Dependency-repo fan-out

| repo | query | rc | manifest |
|---|---|---|---|
| datamodel-code-generator/datamodel-code-generator | `datamodel-codegen msgspec extras ruff` | 0 | `.agent/kb/raw/research-fanout/datamodel-codegen-extras-features-2026-10-01/deps/datamodel-code-generator--datamodel-code-generator/1/manifest.json` |
| datamodel-code-generator/datamodel-code-generator | `knowledge-base` | 0 | `.agent/kb/raw/research-fanout/datamodel-codegen-extras-features-2026-10-01/deps/datamodel-code-generator--datamodel-code-generator/2/manifest.json` |
| ray-manaloto/knowledge-base | `datamodel-code-generator` | 0 | `.agent/kb/raw/research-fanout/datamodel-codegen-extras-features-2026-10-01/deps/ray-manaloto--knowledge-base/1/manifest.json` |

Two further fan-out manifests fed the triage: `.agent/kb/raw/research-fanout/datamodel-codegen-pyproject-jobs-msgspec-ruff/manifest.json`
(context7 `status: error`, "exited 1"; firecrawl-developer and exa ok) and
`.agent/kb/raw/research-fanout/datamodel-codegen-use-annotated-msgspec-x-enum-varnames-cust/manifest.json`.

### Offline mirrors

| link | mirror file | rc | bytes | failure |
|---|---|---|---|---|
| https://datamodel-code-generator.koxudaxi.dev | `docs/research/kb/raw/datamodel-codegen-extras-features-2026-10-01/links/1.md` | 0 | 18241 | — |

In addition (not a caller-link mirror), the site's `llms.txt`/`llms-full.txt` are cached at
`docs/research/mintlify-cache/datamodel-code-generator/datamodel-code-generator/`. That is catalog row
`docs/research/mintlify-catalog.md:97`, with HTTP 200 for both files on 2026-10-01.

## Conflicts resolved

1. **Extras count: 9 vs 12.** One fan-out claim said 9 extras with no black or isort, reading
   `knowledge-base/sources/datamodel-code-generator/pyproject.toml`. That KB source copy is **0.75.1**: its CHANGELOG
   head is `## [0.75.1] … - 2026-08-24`. The 0.83.0 tag and the **installed 0.83.0 METADATA** both show 12, including
   `black` and `isort` (E1, E4). **Trusted: the installed wheel**, because it is what our generator runs, and the
   newer version wins. The black and isort extras arrived with upstream #4009 ("Prepare optional Black and isort
   dependencies"), after 0.75.1.
2. **Whether black and isort are optional.** The extras exist, but METADATA keeps both as **core**
   `Requires-Dist` (E2). The upstream docs say so too: "The current default remains Black/isort, which are still
   required dependencies." **Trusted: METADATA.** The extras are a migration staging step: installing any variant
   still pulls black and isort.
3. **Whether msgspec implies `use-annotated` under jobs.** The KB comment (`knowledge-base/pyproject.toml:344-351`)
   says the implication runs "ONLY on the direct-CLI code path", so a job "silently drops every `Meta(...)`
   constraint". That was measured against the KB's pin (0.76.0 or earlier). Installed 0.83.0 calls
   `_apply_implicit_cli_config_values` on the **job** path (`__main__.py:1305-1307`). My two-arm run confirms it: a
   job with no key emits `Meta(max_length=5)`, and `use-annotated = false` drops it (E22, E23). **Trusted: the
   measured 0.83.0 behaviour.** The KB comment is accurate for its own pin and stale for 0.83.0. Our explicit
   `use-annotated`/`field-constraints = true` keys are therefore redundant in 0.83.0, but harmless, and they guard
   against regression.
4. **`use-specialized-enum`: Python 3.10+ or 3.11+?** A fan-out claim quoting the main-branch typing-customization
   page said "(Python 3.10+)". The offline `llms-full.txt:28354` and the 0.83.0 preset code
   (`requires_python_strenum=True`) say 3.11+, and `StrEnum` is stdlib from 3.11. **Trusted: 3.11+.** The question is
   moot for our `target-python-version = "3.14"`.
5. **Whether the airflow example uses msgspec or ruff.** The fan-out listed apache/airflow as a real-world config.
   Reading both tables shows they are Pydantic v2, and task-sdk uses a `custom-formatters` module (E39). **It is not
   a msgspec or ruff example.**
6. **Whether formatter or extras behaviour changed since the tag.** The source-dive's pyproject diff
   0.83.0..main shows only dependency-group hunks. Its `format.py` conclusion rests on **commit titles only**, so it
   is an inference (see Gaps).

## Gaps

- **context7** for `datamodel-codegen pyproject jobs msgspec ruff`: `status: error`, "exited 1". Its content is
  unknown. This is a gap, not an absence.
- **github-discussions on ray-manaloto/knowledge-base**: `empty_unverified` (the canary returned 0 items), so the
  discussions there are unread.
- **firecrawl-developer** on the use-annotated/msgspec/x-enum-varnames run was `empty_verified`. Listed as reported;
  its control arm discriminated, so this is a confirmed empty rather than a blind one.
- **Item 1 (pip extras) had no fan-out source.** The gap was filled by reading the installed METADATA and the
  0.83.0 tag directly (E1-E4). The PyPI page (https://pypi.org/project/datamodel-code-generator/) was **not read**.
- **Triage hits not read:**
  - https://datamodel-code-generator.koxudaxi.dev/formatter-behavior/ (formatter facts were taken from source and
    `--help` instead);
  - /presets/, /custom_template/, /faq/, /cli-reference/* pages (only the offline `llms-full.txt` greps cover them);
  - discussion #2233;
  - PRs #2829, #3906 (msgspec alias defaults: may matter once we generate Structs with aliased fields), #3885 and
    #2881;
  - KB issues #816, #329 and #412;
  - lipu-linku/ilo, iscc/iscc-search, apify/apify-client-python, AISecurityLab/hackagent and bmcfee/bopp configs.
- **`format.py` changes between 0.83.0 and main** were inferred from commit titles, not from a diff.
- **The positive arm of `--check`** (a stale generated file making `--check` fail) was not run by me. E17 is a
  pass-only observation. The fail arm is owned by `tests/test_codegen_check.py`, which I did not run.
- **The real-world msgspec + ruff search was not re-run.** The finding that there are "no external examples" (E41)
  is the fan-out's code-search result, carried forward with its stated controls (126 broad, 0 nonsense). I did not
  re-derive it.
- **Not run:** `--install-skill` (it writes into `.claude/skills`, a reviewed decision) and `--generate-prompt` (no
  LLM call made). Both were confirmed present only through `--help` (E26 region of `/tmp/dmcg-help.txt`, lines
  672-706).

### Critic gaps (appended; each with its next probe)

- **No-external-example claim rests on a carried-forward search.** Unread hits: lipu-linku/ilo, iscc/iscc-search,
  apify-client-python, hackagent, bmcfee/bopp. Next: read each `pyproject.toml` via `gh api
  repos/<o>/<r>/contents/pyproject.toml` and grep for msgspec plus ruff; paginate `gh search code
  'output-model-type msgspec' --filename pyproject.toml` fully, with a nonsense-token control.
- **0.83.0 release itself unconfirmed.** PyPI JSON metadata, the release notes and any newer release were never
  read. Next: `curl https://pypi.org/pypi/datamodel-code-generator/0.83.0/json`, compare `provides_extra` and
  `requires_dist`; read the GitHub release page.
- **Docs describe main (~104 commits past 0.83.0).** Which documented features exist unchanged in 0.83.0 is partly
  unverified. Next: `git diff 0.83.0..main -- src/datamodel_code_generator/format.py arguments.py preset.py` in a
  clone; confirm each recommended flag with `datamodel-codegen --help` on the installed wheel.
- **`--check` positive arm and the ruff-not-found path not run.** The `[ruff]` extra recommendation rests on
  inference. Next: edit a generated file in a scratch copy and expect `--all-jobs --check` nonzero; run `uv run
  --no-default-groups --group codegen datamodel-codegen --all-jobs` expecting "Ruff executable was not found"; run
  `tests/test_codegen_check.py`.
- **Unread primary pages and PRs:** formatter-behavior, presets, custom_template, faq, cli-reference, the PyPI
  page, discussion #2233, PRs #2829/#3906/#3885/#2881 (msgspec alias defaults may affect aliased-field Structs);
  context7 errored; KB discussions unverified-empty. Next: grep `llms-full.txt` for msgspec alias/default
  behaviour, read PR #3906 and #2829, retry context7 `query-docs`.
- **Unadopted features dismissed by absence of need, not tested:** custom msgspec templates (kw_only, frozen,
  omit_defaults, array_like), `--use-generic-base-class`, `--use-frozen-field`, `--keyword-only`,
  `--use-union-operator`, `--enum-field-as-literal`, the GitHub Action for `--check` in CI. Next: grep
  `llms-full.txt` for every msgspec option, generate in a scratch dir against `schemas/*.json`, diff, and compare
  with the KB's `custom-template-dir`/`use-generic-base-class` usage.
- **Agent Skill and `--generate-prompt` known only from `--help`.** Next: read `agent_skill.py` and the bundled
  `SKILL.md` in the installed wheel (read-only); run `--generate-prompt` to stdout only (no LLM) to see its content.
- **Preset measurement covered one preset only** (`standard-py314-20260909`). Next: run each py314 preset with
  explicit overrides (formatters, `use-schema-description`, snake-case-field off) in `/tmp` copies and diff against
  the committed models.

## Verification

All five verifier, critic and adjudicator steps ran (no failed stages, no null results). Four claims were
checked by refuters (a fifth refute slot produced no separate verdict); the adjudicator ruled on the two the
refuters called misleading plus the two overturned.

| # | Claim | Status | Evidence and effect |
|---|---|---|---|
| V1 | 0.83.0 declares 12 extras; `[all]` omits `httpx2` and `ryaml`; black/isort still core | **Confirmed** | METADATA has exactly 12 `Provides-Extra`; the 0.83.0 `pyproject.toml` agrees. Control: both extras exist on their own but are absent under `extra == 'all'` while `httpx` is present. Minor qualifier: black/isort are core only when `sys_platform != 'emscripten'`; `httpx2`/`ryaml` are alternatives to `httpx`/`pyyaml`, so the omissions look deliberate. Line `#L44` was not checked by number. |
| V2 | Ruff not bundled; found beside interpreter then on PATH; cwd = output directory; ruff 0.16.5 from dev group | **UPHELD as misleading (cwd point only)** | Not bundled, `[ruff]` extra `>=0.9.10`, lookup order and 0.16.5 from `dev` all confirmed (format.py:865-874; cited lines 833/855 drifted slightly, `_run_ruff_command` cwd is at :841). INACCURATE: cwd is `settings_path`, i.e. the caller's cwd on the emit path (`__init__.py:1922`, `:2689`), or the output dir on the parser path (`:2638-2642`), overridable by `--settings-path`. Struck "ruff runs from the output directory" in the Answer, E10 and Recommendation 3. It holds here only because both entrypoints run from `python/`. The refuter's second omission (implicit dev-group coupling) was **rejected** by the adjudicator: the report already says it works only because uv installs default groups, and Recommendation 2 names `--no-default-groups`. |
| V3 | In 0.83.0 jobs mode with msgspec implies `use-annotated`; the KB comment is stale for 0.83.0 | **Confirmed; "misleading" verdict OVERTURNED by the adjudicator** | Two-arm run discriminates (`Meta(max_length=5)` without the key, bare `str` with `use-annotated=false`; `__main__.py:728-729`, `:1307`). The refuter's omission (KB pins 0.76.0, so its comment is not shown stale for that pin) is already stated at E42, Conflicts resolved 3 and Recommendation 5. No change. |
| V4 | `standard-py314-20260909` preset lowercases enum members and drops the docstring | **UPHELD as misleading** | Lowercasing confirmed twice (adjudicator re-run, `snake_case_field=True` from the msgspec group, overriding `x-enum-varnames`; no-preset control gives `IN_SYNC/DRIFT/ERROR`). Docstring loss is an arm artifact: the arm omitted `use-schema-description`, which the preset does not set and our real config does (`python/pyproject.toml:223`). With it, the docstring is kept. Struck the docstring claim in the Answer, E29 and Recommendation 4. The "do not adopt as-is" conclusion stands on the lowercasing alone. |
| V5 | No external repo combines msgspec with ruff formatters in a `[tool.datamodel-codegen]` table | **Confirmed; "misleading" verdict OVERTURNED by the adjudicator** | The query reproduces exactly 3 hits (upstream, guardicore, knowledge-base); controls: 32, 86 and 0 for the ruff-table, pydantic_v2 and nonsense-token queries. The refuter found bmcfee/bopp (`--output-model-type msgspec.Struct --formatters ruff-check ruff-format` in a task string); the report already names it (item 4, code-search notes). The headline is scoped to "in a table". |

**How the conclusion changes.** The recommendations survive (declare the `[ruff]` extra, keep formatters
explicit, do not adopt the preset blindly), but two stated mechanisms were wrong. (1) Ruff config discovery
depends on the generator's working directory, not the output directory, so "same ruff config as hk" is a property
of running from `python/`. (2) The preset's only measured regression is enum-member lowercasing, so a preset with
an explicit override is a more plausible path than the report first implied (untested).

## Recommendation

1. **Commit the offline docs.** That means the cache directory and the catalog row 97 edit. Without the commit,
   "offline agent access" exists on this one machine only (`agent-artifact-conventions.md`, "Promote anything …
   cite").
2. **Declare the ruff dependency where it is consumed:** `codegen = ["datamodel-code-generator[ruff]==0.83.0"]`.
   - Today the formatter's ruff arrives from the unpinned `dev` group. A `--no-default-groups --group codegen` run,
     or a future group split, would fail with "Ruff executable was not found" (E8, E15).
   - The extra adds only `ruff>=0.9.10`, which `uv.lock`'s 0.16.5 already satisfies, so generated bytes should not
     change. Verify with `mise run codegen-check` after `uv lock`.
   - Do **not** use `[all]`. It pulls `grpcio-tools`, `prance`, `graphql-core`, `httpx` and `watchfiles`, which a
     jsonschema → msgspec pipeline never uses.
3. **Keep the formatters set explicitly** to `["ruff-check", "ruff-format"]`.
   - This is the docs' recommendation for ruff projects.
   - It suppresses both deprecations.
   - It gives generated code the same ruff config and version as hk, because ruff runs from the caller's cwd
     (`python/`, set by both the mise task and `codegen_check.py`) and resolves `python/pyproject.toml
     [tool.ruff]`. Keep that cwd: a run from another directory would need `--settings-path`.
4. **Do not adopt `preset = "standard-py314-20260909"` as-is.** Measured (E29, re-run by the adjudicator), it
   lower-cases the `x-enum-varnames` members through the msgspec group's `snake_case_field`. It does NOT drop the
   docstring: that was a probe artifact, and our explicit `use-schema-description = true` keeps it. If a preset is
   wanted, pin the dated name, keep `formatters` and `use-schema-description` explicit, try an explicit
   snake-case-field override (untested), and diff the output against the committed models first. The
   use-annotated, use-union-operator, enum_field_as_literal and formatter differences vs our config were not
   measured on this schema.
5. **Keep `use-annotated`/`field-constraints` explicit.** They are redundant in 0.83.0 (E23), but they cost nothing
   and survive a regression. Consider correcting the KB comment at `knowledge-base/pyproject.toml:344-351` when the
   KB bumps past 0.76.0. Before rewriting it, re-run its A5/A6 arms on the new pin.
6. **Adopt later, triggered by need:**
   - `--diff-against <baseline schema>` in review of a schema-changing PR;
   - `[tool.datamodel-codegen.profiles.*]` once a second output model type appears;
   - `custom-template-dir` when a generated shape needs a template (the KB and OpenTelemetry both use one);
   - `--lockfile`/`--locked` only if a schema ever takes a remote `$ref`.
7. **Agent Skill:** run `datamodel-codegen --install-skill claude-code` from the repo root only as a reviewed change.
   It writes `.claude/skills/datamodel-code-generator/` (E32), which costs skill-listing budget. The upstream
   `llms-full.txt` cache already gives agents grep-able offline docs. `--generate-prompt "<question>"` stays an
   ad-hoc tool and needs no adoption.
8. **Remember that jobs are experimental** (E24). The `codegen-check` gate is the guard: a schema or CLI change in a
   bump surfaces as drift or as rc=2 there.

## Provenance

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| deps:datamodel-code-generator/datamodel-code-generator | general-purpose | sonnet | low |
| deps:ray-manaloto/knowledge-base | general-purpose | sonnet | low |
| mirror:1/1 | general-purpose | haiku | (default) |
| triage | Explore | sonnet | low |
| mirror-index | general-purpose | haiku | (default) |
| read-link:1 | Explore | sonnet | low |
| read:1/2 | Explore | haiku | (default) |
| read:2/2 | Explore | haiku | (default) |
| source-dive | general-purpose | sonnet | medium |
| synthesize | general-purpose | opus | high |
| refute:1/5 | general-purpose | sonnet | medium |
| refute:2/5 | general-purpose | sonnet | medium |
| refute:3/5 | general-purpose | sonnet | medium |
| refute:4/5 | general-purpose | sonnet | medium |
| refute:5/5 | general-purpose | sonnet | medium |
| critic | Explore | sonnet | medium |
| adjudicate | general-purpose | opus | high |
| reconcile | general-purpose | sonnet | medium |

## GitHub repos touched

- [datamodel-code-generator/datamodel-code-generator](https://github.com/datamodel-code-generator/datamodel-code-generator): the 0.83.0 tag source, docs, extras, formatter code, presets and Agent Skill; issues and PRs from the fan-out.
- [guardicore/datamodel-code-generator](https://github.com/guardicore/datamodel-code-generator): a fork of upstream, surfaced only as a code-search hit (not read).
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): the reference `[tool.datamodel-codegen]` config, the 0.75.1 source copy, and issues #329/#488.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): the config under evaluation (`python/pyproject.toml`, `mise.toml`, `codegen_check.py`, `schemas/drift-verdict.schema.json`).
- [open-telemetry/opentelemetry-python](https://github.com/open-telemetry/opentelemetry-python): a real-world config with ruff formatters and dataclasses.
- [Mirascope/mirascope](https://github.com/Mirascope/mirascope): a real-world config with ruff formatters and TypedDict.
- [apache/airflow](https://github.com/apache/airflow): real-world configs (airflow-ctl via the fan-out, task-sdk read), both pydantic v2.
- [lipu-linku/ilo](https://github.com/lipu-linku/ilo), [iscc/iscc-search](https://github.com/iscc/iscc-search), [apify/apify-client-python](https://github.com/apify/apify-client-python), [AISecurityLab/hackagent](https://github.com/AISecurityLab/hackagent), [bmcfee/bopp](https://github.com/bmcfee/bopp): code-search hits, not read.
- [cli/cli](https://github.com/cli/cli): the code-search health probe only.
