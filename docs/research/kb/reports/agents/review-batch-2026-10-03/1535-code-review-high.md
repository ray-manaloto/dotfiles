# #1535 — /code-review high

- Target: merge SHA `aeeb9164de56d492b74ece9f648d6d417f97dbc0` (fix(deps): make codegen a default uv group)
- Lens: built-in `/code-review high` (forked, task `ace281304923eb75b`, 20 tool uses, 191s)
- Verdict: **FINDINGS** — 7

## Verbatim result

The target commit `aeeb9164` adds 8 lines to `python/pyproject.toml`: `[tool.uv] default-groups = ["dev", "codegen"]` plus a comment explaining it. I checked it against `uv` 0.12.13's own help text, the locked dependency set and every `uv` call site in the repo. I found 7 issues: none breaks the build today; the most costly is the extra install work every default sync now does. I wrote no files; persisting this report is up to you.

- **Cost of the change:** a full default sync now resolves 181 packages instead of 152. The 29 extra are what `datamodel-code-generator[all,httpx2,ryaml]` brings in, including grpcio, grpcio-tools, protobuf, black, isort and httpx2. Only the `codegen` and `codegen-check` tasks ever use them.
- **Root cause is misstated:** `uv run --help` shows `--exact` as opt-in, and `uv sync --help` shows `--inexact` as opt-out. So plain `uv run` never uninstalls anything; only the exact `uv sync` calls (`mise.toml:8` and `:248`) do. The new comment blames "each hk step", which is wrong.
- **Wheel coverage:** in the lock, `ryaml` 0.5.1 has no musllinux wheel, and its Linux wheels need glibc 2.28 or newer.

```json
[
  {
    "file": "python/pyproject.toml",
    "line": 65,
    "summary": "Making `codegen` a default group installs datamodel-code-generator[all,httpx2,ryaml] (29 extra packages, including grpcio, grpcio-tools, protobuf, black, isort and httpx2) into every default sync, though only the codegen/codegen-check tasks use them.",
    "failure_scenario": "Each fresh CI runner now downloads and installs the 29 extra packages, including the large grpcio/grpcio-tools native wheels, every time it runs `uv run --project python …`. That covers ci.yml verify, pytest and promote-eligibility, dev-cache-probe once per build leg, setup-claude-code, refresh.yml's pytest jobs, and scripts/web-setup.sh's `uv sync --project python`. The default set grows from 152 to 181 packages for no benefit to those callers. Cheaper option: keep the group opt-in and stop the one exact sync that strips it (mise [deps.uv] `uv sync --locked`)."
  },
  {
    "file": "python/pyproject.toml",
    "line": 59,
    "summary": "The new comment (and the commit message) gives the wrong root cause: plain `uv run` does an inexact sync and never uninstalls anything; only exact `uv sync` does (mise [deps.uv] `uv sync --locked` at mise.toml:8 and the `deps:python` task's `uv sync` at mise.toml:248).",
    "failure_scenario": "`uv run --help` lists `--exact` as opt-in and `uv sync --help` lists `--inexact` as opt-out. A maintainer who believes 'each hk step' strips groups will look for races between hk steps, and won't touch the real stripper. If default-groups is later trimmed, the [deps.uv] exact sync silently brings the original race back."
  },
  {
    "file": "python/src/dotfiles_setup/codegen_check.py",
    "line": 137,
    "summary": "The underlying race is still there. codegen-check finds the generator next to sys.executable some time after uv's sync, so any exact sync that leaves out the group still deletes it in the middle of the check. The fix changes the shared default environment instead of fixing the gate's check-then-use gap.",
    "failure_scenario": "Any exact sync that leaves out codegen while the hk codegen_check step is running deletes datamodel-codegen between `uv run --group codegen` finishing its sync and `generator_binary().exists()` or the subprocess spawn. Examples: `uv sync --only-group dev`, `uv sync --no-default-groups`, or any `uv sync` with `UV_NO_DEFAULT_GROUPS=1` set. The step then reports ERROR ('not found'), the same CI failure as #1534. A fix at the right depth would run the generator through `uv run --group codegen datamodel-codegen` or import it, instead of probing a path beside the interpreter."
  },
  {
    "file": "python/pyproject.toml",
    "line": 205,
    "summary": "The [dependency-groups] comment still calls codegen an 'Exact pin, isolated group', and python/AGENTS.md:117 still describes it as an opt-in group; neither was updated when the group became a default.",
    "failure_scenario": "Breaks .claude/rules/tool-currency-and-native-first.md rule 5: 'Sync the describing docs/skills in the SAME change.' The group is no longer isolated: every default sync installs it. A reader who relies on 'isolated' could add heavy extras on the assumption that they cost ordinary syncs nothing."
  },
  {
    "file": "python/src/dotfiles_setup/dependency_currency.py",
    "line": 166,
    "summary": "datamodel-code-generator is exact-pinned (==0.83.0) and is now always present in the project venv, so `uv pip list --outdated` reports it whenever upstream releases a newer version. Before, it showed up only if the last sync happened to include the codegen group.",
    "failure_scenario": "The doctor's dependency-currency check (rc=verdict) changes behavior: once a datamodel-code-generator release past 0.83.0 exists, it returns OUTDATED (rc=1) on every session, where before it flipped depending on which sync ran last. Nobody reviewed or recorded this new doctor signal in the change."
  },
  {
    "file": "python/pyproject.toml",
    "line": 65,
    "summary": "Every default sync now needs ryaml 0.5.1. In the lock, its only Linux wheels are manylinux_2_28 (no musllinux, nothing for glibc older than 2.28), so on such a host the default sync falls back to building from source.",
    "failure_scenario": "On a musl host (Alpine) or a glibc older than 2.28, the mise [deps.uv] auto sync and every `uv run --project python …` now has to build ryaml from source, which needs a Rust toolchain. If that build fails, the whole dotfiles-setup CLI and every hk python step stop working, where before only the opt-in codegen task was affected."
  },
  {
    "file": "python/pyproject.toml",
    "line": 63,
    "summary": "The comment calls the `--group codegen` flags in mise.toml and hk.pkl 'now redundant' while suites.toml (lines 3040-3043) binds them as required lines. The flags can't be removed, and the contract no longer guarantees what it set out to: that the generator comes only from an explicitly selected group.",
    "failure_scenario": "A cleanup that removes the 'redundant' flags fails `workflow` contract verification. If the contract is updated together with the flags, the codegen tasks quietly start depending on default-groups, and narrowing the default list later brings back the #1534 'datamodel-codegen not found' failure."
  }
]
```

## Lane triage (second read) — appended after receipt

Re-read at main `785c3708`. `pyproject.toml` lines 58-65 are unchanged.

| # | Severity | Second read | Disposition |
|---|---|---|---|
| 1 | MED | CONFIRMED by inspection: `default-groups = ["dev", "codegen"]` (`pyproject.toml:65`) puts the codegen extras into every CI `uv run --project python` | Issue H |
| 2 | LOW | CONFIRMED with arms. `uv run --help` lists `--exact` as an opt-in ("Perform an exact sync, removing extraneous packages"). `uv sync --help` lists `--inexact` as an opt-out (logs in `.agent/logs/review-batch/uv-{run,sync}-help.txt`). The real stripper is mise `[deps.uv]` `uv sync --locked` (`mise.toml:8`). The comment at `pyproject.toml:59-60` blames "plain `uv run`" and "each hk step" | folded into H |
| 3 | MED | CONFIRMED: `codegen_check.py:136` probes `Path(sys.executable).with_name("datamodel-codegen")` after uv's sync, so a sync that excludes the group still races the gate | Issue H |
| 4 | LOW | doc drift (`[dependency-groups]` comment, `python/AGENTS.md:117`) | folded into H |
| 5 | LOW | dependency-currency now always sees the pinned generator; this is a behaviour change, not a defect | folded into H as a note |
| 6 | LOW | the musl/old-glibc case is not a supported target (Ubuntu devcontainer, macOS host, ubuntu runners) | noted |
| 7 | LOW | "redundant" flags are contract-bound | folded into H |

Duplicate search: `default-groups codegen` → 1 hit (#1535 itself); `codegen race` → 3; `datamodel-codegen not found` → 6. None of these covers the finding.

## GitHub repos touched

_None._ (local git objects + uv help)

## Issues filed

- H → [#1601](https://github.com/ray-manaloto/dotfiles/issues/1601)
