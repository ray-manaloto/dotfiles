# STANDARDS axis — `feat/tool-currency-engine` (7 commits, 22 files)

Lint is green; nothing below is tooling-visible.

## A. Documented-standard breaches

**1. `mise-tasks-only.md` — HARD. `.claude/settings.json:47`**
The new SessionStart hook runs `… -- uv run kb-setup currency check`, but this
same diff adds `mise.toml:167 [tasks.kb-currency-check]` whose body is exactly
`uv run kb-setup currency check`. Rule: *"When a task exists, USE IT — never
hand-roll the underlying command sequence."* The two copies can drift, and
`mise.toml`'s own comment ("what lets the SessionStart hook run it every
session") shows the task was meant to be the hook. Use `mise run kb-currency-check`.
(The sibling PreToolUse hooks are exempt — no task exists for them.)

**2. `zero-skip-policy.md` — HARD. `docs/currency/runs/2026-07-24-graphify.md`**
The committed run ships two DRIFT findings (`resolution: PATH reaches 0.9.23 but
the pin is 0.9.25`; `build-stamp: artifacts have never been stamped`) and the
sole gate reads `**Answer:** _not yet answered_`. Rules 3–4 require the
AskUserQuestion escalation to be *answered*, or the deferral tracked as a
`gh issue`. The branch does neither — it commits an open finding as the record.

**3. `probes-need-a-control-arm.md` — judgement. `decide.py:198`**
`_REQUIRED_OK = ("resolution", "build-stamp")` omits `extra-probes` and
`manifest`, so those may SKIP and a bump still auto-applies — against the
comment three lines above it (*"SKIP means 'not checked' … reading it as consent
is the absence-of-evidence trap"*). Either include them or say why they differ.

## B. Baseline smells (judgement calls)

- **Duplicated Code — `upstream.py:129-174`.** `latest_pypi` and `pypi_versions`
  are the same `HTTPSConnection` → `GET /pypi/{pkg}/json` → `json.loads` body;
  `probe()` calls both, fetching the identical payload twice. Extract `_pypi_json`.
- **Duplicated Code — `sync.py:131-146` vs `375-388`.** `resolve_from_path` and
  `_install_root_from_path` both do `shutil.which` → `.parts` → `index("installs")`.
- **Mysterious Name / implicit coupling — `graph.py:_stamp_build`.** Docstring says
  *"which graphify version"*, code says `next((s for s in config.load(repo_root)
  if s.stamp), None)` — whichever tool sorts first. `currency.toml` is explicitly
  multi-tool ("mise, hk, uv, ruff and ty adopt the same shape"), so a second
  stamped tool silently mis-stamps. Name the tool.
- **Primitive Obsession — `OK`/`DRIFT`/`SKIP` bare strings;** `decide.py:215`
  compares the literal `"ok"` rather than `sync.OK`. A rename breaks it silently.
- **Data Clump — `(repo_root, spec, pinned)`** threads through eight `sync.py`
  helpers.
- **Test gap.** `issues.py` (203 lines, the carry-forward/baseline logic two
  commits fixed) has no `tests/test_currency_issues.py`; the other four modules
  each have one.

Non-findings checked: `except A, B:` is valid PEP 758 (py3.14); absolute paths in
`settings.json` match the file's existing convention; zero-bash holds throughout.

## GitHub repos touched

- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the reviewed diff (PR #4).
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — `export.py` read as ground truth.
