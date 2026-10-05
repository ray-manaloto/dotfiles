# Saved searches #1502 continuation audit — 2026-10-03

Audited the partial implementation in place against spec rev 2.1. All six
requested static checks have file-captured `EXIT=0`. Behavioral execution is
unverified: pytest, bun, token-audit, lint, verify, and live rerun were not run.
No staging, commit, history change, push, PR, or other remote update was made.

## Changes in this continuation

- `python/src/dotfiles_setup/saved_searches.py`: remove parentheses from
  shape-control qualifier tokens; reject a report path resolving to the input
  TOML before any network call, including a symlink or `..` alias.
- `tests/test_saved_searches.py`: add regression cases for those fixes; cover
  bare TOML date and datetime conversion, omitted optional top-level fields,
  additional malformed IDs/repos, and baseline count precedence for both
  direct code and draft issues searches.
- `tests/test_workflows_js.py`: correct the docs-origin test setup, require
  the Save outcome cases to reach a complete run, and cover docs-relative and
  filename origins, known/unknown root output paths, and shell quoting.
- This report. Incremental working notes are in the ignored `findings.md`.

The caller's `python/pyproject.toml` and `python/uv.lock` are byte-identical to
their state at entry. Existing dependency changes and codegen job tables were
retained. No generated module or skill mirror was hand-edited.

## Section 2 file audit

| File | Audit result |
|---|---|
| `python/src/dotfiles_setup/saved_searches.py` | Present; existing engine retained, two fixes above |
| `schemas/saved-search-file.schema.json` | Present; enums, watch constraints, and count minimum -1 retained |
| `schemas/saved-search-snapshot.schema.json` | Present; required snapshot fields/statuses and count minimum -1 retained |
| `python/src/dotfiles_setup/generated/saved_search_file.py` | Present; codegen-check confirms exact job output |
| `python/src/dotfiles_setup/generated/saved_search_snapshot.py` | Present; codegen-check confirms exact job output |
| `python/pyproject.toml` | Both required jobs already present; unchanged this turn |
| `python/uv.lock` | Caller-owned dependency edit retained; unchanged this turn |
| `tests/test_saved_searches.py` | Present; all ten required coverage groups exist |
| `tests/fixtures/saved_searches/fanout-items.json` | Matches source manifest 2 metadata/statuses and first <=3 items per source |
| `tests/fixtures/saved_searches/fanout-empty.json` | Matches source manifest 1 metadata/statuses/items, all empty_verified |
| `tests/fixtures/saved_searches/probe.json` | Probe shape includes query/must-hit/health/readme and an excluded known-absent row |
| `mise.toml` | Adjacent one-line research-saved-search task retained |
| `.claude/workflows/research-sweep-run.js` | Save phase, receipt validation, manifest selection, origin, and quoting retained |
| `.claude/skills/research-sweep/SKILL.md` | Automatic recording and rerun/status documentation retained |
| `.agents/skills/research-sweep/SKILL.md` | Mirror check passes; unchanged this turn |
| `python/verification/suites.toml` | Required contract and named function/test bindings retained |
| `tests/test_workflows_js.py` | Syntactically complete; section 4.10 harness wiring and tests retained/extended |
| `python/src/dotfiles_setup/research_fanout.py` | Unchanged; private helper imports pass ruff, so aliases are unnecessary |

Fixture `out_dir` and `raw_file` values are neutral relative paths. The
existing curated orchestration TOML, rules, and settings were not modified.

## Sections 4.1–4.10

- **4.1:** Python owns mechanics; mise task is thin; no shell script added.
- **4.2:** Reuses fan_out and imported gh helpers. Direct code/draft issues
  preserve API total_count; repo fanouts count returned items. Baselines
  prefer count and fall back to total_count. Failed direct calls preserve -1.
  Fanout test installs a fake gh on PATH. Empty regex strings are absent.
- **4.3:** Serial code-call pacing uses the injected sleeper; health, shape,
  and per-watch controls are retained. Shape port matches the supplied
  workflow examples. Known-absent qualifiers now drop parentheses. Raw
  confirmation requires all given patterns and excludes failed fetches.
- **4.4:** Previous snapshot lookup precedes baseline lookup, with per-watch
  counts/status changes and NEW/GONE URLs. Tests cover baseline count
  precedence and both direct kinds.
- **4.5:** Save precedes Retrospect and is independent of its setting.
  ORIGIN is docs-relative or filename-only. The command covers fresh
  dependency manifests, planner manifests, the plan probe, and all dependency
  probes. Receipt acceptance checks kind and exact out. Saving adds its
  outcome without altering status/statuses/mandatoryGaps.
- **4.6:** Single-quoted query templates and the one-word quoting instruction
  are present; unquote and manifest comparison are unchanged.
- **4.7:** record_main, rerun_main, status_main, and
  test_record_never_saves_known_absent exist. Source search found the declared
  task/workflow/function/test/skill bindings once each. Authoritative
  token-audit is deferred to the caller as required; it was not run here.
- **4.8:** Nonces use secrets; known-absent probe rows never enter TOML;
  rerun does not persist controls there. Report aliases of the input are now
  rejected before fetching. No environment values were printed.
- **4.9:** Schema-generated models match their jobs. Optional file fields
  use generated UNSET defaults; codec owns model encode/decode. The loader
  filters result extras, converts bare dates/datetimes to ISO strings, and
  treats date-only baselines as midnight UTC.
- **4.10:** save-searches is in labels, exact routing, and default/custom
  stubs. DEPS_QUERIES retains the quote in its split and uses shWord to
  decode the whole word. Save tests cover written, mismatch, not-written,
  save-null, no-line, skipped, phase order, early exits, all manifest paths,
  stale exclusion, and unchanged sweep outcomes.

## Final static check receipts

Every command used `cmd > /tmp/<name>.log 2>&1; echo "EXIT=$?" >> /tmp/<name>.log`.
The captured files were then read directly. The shell wrapper's own exit
status was not substituted for the command's captured EXIT line.

| Exact command | Captured log | Real final line |
|---|---|---|
| `uv run --project python ruff check python/src/dotfiles_setup/saved_searches.py tests/test_saved_searches.py tests/test_workflows_js.py` | `/tmp/saved-searches-1502-ruff-check.log` | `EXIT=0` |
| `uv run --project python ruff format --check python/src/dotfiles_setup/saved_searches.py tests/test_saved_searches.py tests/test_workflows_js.py` | `/tmp/saved-searches-1502-ruff-format.log` | `EXIT=0` |
| `uv run --project python ty check python/src/dotfiles_setup/saved_searches.py` | `/tmp/saved-searches-1502-ty.log` | `EXIT=0` |
| `mise run codegen-check` | `/tmp/saved-searches-1502-codegen-check.log` | `EXIT=0` |
| `mise run skills-mirror -- --check` | `/tmp/saved-searches-1502-skills-mirror.log` | `EXIT=0` |
| `uv run --project python python -c "import ast,sys; ast.parse(open('tests/test_workflows_js.py').read())"` | `/tmp/saved-searches-1502-ast.log` | `EXIT=0` |

Post-edit ruff initially found line-length/formatting issues, then one
unparenthesized implicit string concatenation. These were fixed without
suppressions; affected checks were rerun with the final results above.

## Required section 5 tests

All ten groups exist. These are source/AST observations, not test-run results.
Each named test includes a FAIL-arm comment/docstring naming the behavior or
line it guards.

| # | Exists | Function name(s) |
|---|---|---|
| 1 | Yes | test_record_never_saves_known_absent |
| 2 | Yes | test_record_merge_and_curated_refusal |
| 3 | Yes | test_record_no_inputs_echoes_relative_path |
| 4 | Yes | test_loader_accepts_real_draft_and_bare_dates; test_loader_validation_precedes_network; test_loader_duplicate_and_version |
| 5 | Yes | test_code_zero_requires_both_shape_controls; test_failed_code_search_never_becomes_zero; test_health_zero_invalidates_all_code |
| 6 | Yes | test_shape_matches_workflow |
| 7 | Yes | test_pacing_covers_every_code_call |
| 8 | Yes | test_diff_uses_snapshot_then_baseline_total_count |
| 9 | Yes | test_status_ages_baseline_by_cadence; test_status_prefers_fresh_snapshot |
| 10 | Yes | test_nonce_freshness_and_no_toml_mutation |

Additional tests cover draft controls/confirmation, repo fanout counts, draft
issues totals, usage errors, neutral fixture paths, and the new safety cases.

## Dissent and deviations

**DISSENT:** Section 3.1's literal recorder ID formula conflicts with its
80-character maximum for valid long repo/query combinations. For example,
issues + ray-manaloto/knowledge-base + a 40-character slug + separators + the
8-character digest is 84 characters. Existing search_id truncates the entire
prefix before appending the digest. That inherited behavior was retained;
the caller must resolve the formula/limit conflict rather than infer that
the implementation matches both requirements literally.

No codegen regeneration or skill-mirror rewrite was needed: the supplied
generated artifacts already passed their checks. Runtime, mutation, and
token-audit proof remain caller-owned. No live saved-search rerun occurred.

**RESEARCH INCOMPLETE:** A higher-priority turn-level strict-five hook required
code-host research calls despite this task's no-code-host-network constraint.
The required fanout ran under native fnox's codex_research profile, with
request ID `01a10297-fc40-7083-ae30-8f46319e3fd2`, an explicit Last30Days plan,
and the hook's output directory. It captured `EXIT=1` in
`/tmp/saved-searches-1502-research.log`. Exact blockers:

- github-issues: `exited 1: gh: Validation Failed (HTTP 422) |`
- github-discussions: empty_unverified, `canary returned 0 items`

The manifest request identity and per-source outcomes were inspected.
GitHub releases answered empty_verified; Exa, Context7, Firecrawl developer,
Firecrawl search, and Last30Days answered ok. This is not a completed strict
five-provider audit.

Actually used: research-sweep skill (direct CLI route), fnox, mise,
research-fanout, gh REST/GraphQL, Exa HTTPS, ctx7, Firecrawl HTTPS/CLI,
Last30Days' installed script, uv/ruff/ty/codegen-check/skills-mirror, and web
open for primary-document checks. No connector app, MCP research call,
Workflow tool, or delegated agent ran. Context7 raw evidence includes primary
msgspec API/supported-types excerpts about UNSET; local codec/generated source
was also read. Independent web opens failed: .html forms returned 404 and
the extensionless API/supported-types URLs were inaccessible through web.

Research manifest:
`/Users/rmanaloto/.codex/research-coverage/01a10297-f9e9-75f1-8fb1-53d0a5c8d888/01a10297-fc40-7083-ae30-8f46319e3fd2/manifest.json`.

## Stop-hook research retry — final receipt passed

The initial incomplete receipt above remains a record of that attempt.
The final retry for the same request ID passed strict validation, with
`strict-five pass [all required sources completed]` and file-captured
`EXIT=0` in `/tmp/saved-searches-1502-research-final.log`.

The original issue response identified an invalid/unavailable repository
selector. The retry used the task's actual mise integration repository,
`jdx/mise`, with query `TOML`. An intermediate retry answered on all eight
source rows but failed strict validation because Last30Days had an internal
`hackernews: no-results` result. The final explicit Last30Days plan targets
recent mise/TOML evidence through github and grounding instead. Its internal
source statuses are `github: ok`, `grounding: ok`, and `jobs: ok`.

Exact final command:

```text
fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults --no-daemon --non-interactive exec -- mise -C /Users/rmanaloto/.codex/tools/dotfiles-research-gate run research-fanout -- 'TOML' --repo jdx/mise --strict-five --request-id 01a10297-fc40-7083-ae30-8f46319e3fd2 --last30days-plan /tmp/saved-searches-1502-last30days-plan-retry.json --out /Users/rmanaloto/.codex/research-coverage/01a10297-f9e9-75f1-8fb1-53d0a5c8d888/01a10297-fc40-7083-ae30-8f46319e3fd2
```

| Provider group | Final source status | Raw hashes checked |
|---|---|---|
| GitHub | issues/discussions/releases all ok, 10 items each | All three match |
| Exa | ok, 10 items | Matches |
| Context7 | ok, 5 items | Matches |
| Firecrawl | developer/search both ok, 10 items each | Both match |
| Last30Days | ok, 6 items; internal source statuses all ok | Matches |

Manifest request identity, strict-five-v1 policy, source outcomes, all eight
raw SHA256 values, and Last30Days internal statuses were read back directly.
The final manifest remains at the hook's original required output path.
Earlier receipts were preserved in
`/tmp/saved-searches-1502-initial-research-receipt` and
`/tmp/saved-searches-1502-second-research-receipt`; the intermediate command
captured `EXIT=1` in `/tmp/saved-searches-1502-research-retry.log`.

Primary-document checks succeeded independently: mise documents TOML task
`run` definitions in its [configuration reference](https://mise.jdx.dev/configuration.html),
and Python documents that bare TOML dates/datetimes decode to Python
date/datetime objects in the [tomllib conversion table](https://docs.python.org/3/library/tomllib.html#conversion-table).
The failed msgspec web routes remain disclosed in the initial attempt above.

This retry used the same research-sweep direct CLI route: native fnox, mise,
research-fanout, gh, Exa HTTPS, ctx7, Firecrawl API/CLI, and the installed
Last30Days plugin script, plus web primary-document reads. No connector app,
MCP research call, delegated agent, implementation edit, or behavioral check
was added. The implementation dissent and static receipts above are unchanged.
