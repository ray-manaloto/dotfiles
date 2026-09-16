# cold-review-67a6cad — verbatim report (2026-09-16)

Brief: cold review by ref of `67a6cad` (codex lane, 6c items 2–4) against `7c555a8`, diff only, no intent framing. Lane: `cold-reviewer` on Opus (the cross-family lens for a codex diff). Report file copied verbatim below; the architect's refutation pass follows it.

---

# Cold review — 67a6cad (parent 7c555a8)

Reviewer: cold-reviewer (Opus 5), 2026-09-16.
Resolved refs: `7c555a8311a738e43149c43ba2c264deadcaf09c` -> `67a6cad3820408f64683daac25b782d1b3c0c81f`.
Diff: `git diff 7c555a8..67a6cad` — 3 files, +687/-58.

| File | Change |
|---|---|
| `hk.pkl` | +2 glob entries (`mise.toml`, `python/src/dotfiles_setup/lint.py`) |
| `python/src/dotfiles_setup/workflow_claude_code.py` | +427/-58 |
| `tests/test_workflow_claude_code.py` | +316 |

No intent framing was supplied and none was inferred beyond the diff.

## Environment / method

- graphify graph is **stale** (built at `13ff702c`, HEAD `67a6cad3`, 4 commits
  behind). Per `.claude/rules/graphify-first.md` the graph is unavailable, so
  every claim below is grounded in source and live probes, not the graph.
- The repo spells local action refs `uses: $/.github/actions/...` (5 in
  `ci.yml`, 0 with `./`). Control arm: a literal `./` written to the scratchpad
  round-trips intact through the same tooling, and `git show 67a6cad:...` shows
  the same bytes — so `$/` is the real committed sequence, not a display
  artifact. `_expand_local` handles both spellings.
- **Mutation harness:** `scan_workflows(root)` is parameterised by root, so the
  commit was extracted with `git archive 67a6cad | tar -x` into the scratchpad
  and mutated there. No tracked file was edited. Control arm on the unmutated
  copy: `violations=0 skipped=0`.
- Baseline: `uv run --project python dotfiles-setup workflow-claude-code` ->
  `rc=0`; `pytest tests/test_workflow_claude_code.py` -> `49 passed`, `rc=0`;
  `ruff check` clean; `ruff format --check` clean; `ty check` clean.

## Findings

| # | Sev | Claim | Location |
|---|---|---|---|
| 1 | HIGH | Four of hk's long-form global flags are missing from the flag group, so `hk --verbose run check --all` evades the gate; the comment claims the group is "the complete hk 1.57.0 GLOBAL-flag surface" | `python/src/dotfiles_setup/workflow_claude_code.py:79` |
| 2 | HIGH | The hook name must immediately follow `run`, but hk's own usage is `hk run [FLAGS] [FILES]… <SUBCOMMAND>`, so `hk run --all check` evades | `python/src/dotfiles_setup/workflow_claude_code.py:84` |
| 3 | HIGH | `_MISE_TASK_RE` has no flag tolerance, so `mise run --force lint` and `mise --cd . run lint` evade, though `mise run --help` says "Put mise flags before the task name" | `python/src/dotfiles_setup/workflow_claude_code.py:97` |
| 4 | MED | A malformed `mise.toml` raises `TOMLDecodeError` out of the gate — the unhandled-traceback failure mode this same commit's YAML comment says it fixed — and the commit adds `mise.toml` to the step glob | `python/src/dotfiles_setup/workflow_claude_code.py:150` |
| 5 | MED | `:::` multi-task invocations lose every task after the first: `mise run render ::: lint` is missed | `python/src/dotfiles_setup/workflow_claude_code.py:97` |
| 6 | MED | The mise lookahead excludes `"`, so `bash -c "mise run lint"` is missed; the hk regex has no such lookahead and catches its equivalent | `python/src/dotfiles_setup/workflow_claude_code.py:99` |
| 7 | MED | `job_installs_before_gate` reports False for the live compliant `ci.yml::lint` job when given an unresolved `Job`, while `job_runs_the_gate` on the same object reports True | `python/src/dotfiles_setup/workflow_claude_code.py:502` |
| 8 | LOW | Three exported predicates are unreachable from the production path; the only test exercising them asserts behaviour the gate never calls | `python/src/dotfiles_setup/workflow_claude_code.py:465` |
| 9 | LOW | A shell comment mentioning the tool now creates a false violation; the pre-change regex did not match it | `python/src/dotfiles_setup/workflow_claude_code.py:85` |
| 10 | LOW | `_expand_local` resolves `./../…` above the repo root and will read and expand an `action.yml` there | `python/src/dotfiles_setup/workflow_claude_code.py:419` |
| 11 | LOW | `.config/mise/conf.d/*.toml` is tracked and merged by mise but is not read; the docstring excuses only `mise.local.toml` | `python/src/dotfiles_setup/workflow_claude_code.py:33` |
| 12 | LOW | The route parametrize list enumerates exactly the flags the regex covers, so it cannot detect finding 1 | `tests/test_workflow_claude_code.py:157` |

## Evidence

### Arm table — evasion shapes (mutated copy, fresh probe workflow per arm)

Each arm is one job running the named command with **no** setup action. CAUGHT
means the gate produced a violation.

| Result | Command |
|---|---|
| CAUGHT | `hk run check --all` (baseline, matched by the pre-change regex too) |
| CAUGHT | `mise run lint` |
| CAUGHT | `uv run --project python dotfiles-setup lint` |
| CAUGHT | `HK_FIX=1 hk run pre-commit --all` |
| CAUGHT | `hk -v run check --all` (short form) |
| CAUGHT | `hk check --all` |
| CAUGHT | `mise exec -- hk run check --all` |
| **MISSED** | `hk --verbose run check --all` |
| **MISSED** | `hk --quiet run check --all` |
| **MISSED** | `hk --slow run check --all` |
| **MISSED** | `hk --no-progress run check --all` |
| **MISSED** | `hk run --all check` |
| **MISSED** | `mise run --force lint` |
| **MISSED** | `mise --cd . run lint` |
| **MISSED** | `mise run render ::: lint` |
| **MISSED** | `bash -c "mise run lint"` |

The seven CAUGHT rows are the control arm: the probe discriminates, so each
MISSED row is a property of the gate, not of the harness. Cleanup control after
removing the probe file: `violations == ()`.

### Finding 1 — the flag surface is not complete

`mise exec -- hk --help` on **hk 1.57.0** lists eleven behavioural global flags:

```
      --cd <DIRECTORY>     --format <FORMAT>    -j, --jobs <JOBS>
  -p, --profile <PROFILE>  -s, --slow           -v, --verbose
  -n, --no-progress        -q, --quiet              --silent
      --trace                  --json
```

Line 79 lists the boolean set as `-s|-v|-n|-q|--silent|--trace|--json`. The
long spellings `--slow`, `--verbose`, `--no-progress` and `--quiet` are absent,
and `-v` cannot match inside `--verbose` because the alternation must start at
the first `-` after `\s+`. When the flag group fails, the whole match at that
`hk` fails and `finditer` finds no other `hk`, so the command yields **no**
hooks and the job is exempt. Lines 69-71 assert the opposite: "the complete hk
1.57.0 GLOBAL-flag surface measured for this gate".

### Finding 2 — hk's own usage puts flags before the hook

`mise exec -- hk run --help` prints `Usage: hk run [FLAGS] [FILES]… <SUBCOMMAND>`.
Line 84 requires `[A-Za-z]` immediately after `run\s+`, so both documented
prefixes — a flag (`hk run --all check`) and a file list (`hk run src/x.py check`)
— defeat it.

### Finding 3 — the two regexes are asymmetric

`_HK_COMMAND_RE` was given a flag-tolerance group; `_MISE_TASK_RE` (lines 97-100)
was not, despite the same exposure. `mise run --help` states the shape
explicitly: "Put mise flags before the task name; following arguments are passed
to that task."

### Finding 4 — malformed `mise.toml` is an unhandled traceback

`tomllib.loads` at line 150 is unguarded. Appending `[tasks.broken` to the
copied `mise.toml`:

```
RAISED: TOMLDecodeError - Expected ']' at the end of a table declaration (at line 1668, column 14)
main RAISED: TOMLDecodeError - ...
```

Control arm, same probe after restoring the file: `scan ok: 0 0` / `main rc: 0`.

This is the failure shape the commit's own comment (lines ~560-566) says was
fixed for YAML: "a workflow that did not parse produced a raw
`yaml.scanner.ScannerError` traceback under 'Unexpected command failure'
instead of naming the file." The commit then added `"mise.toml"` to the step's
glob (`hk.pkl:442`), so the step now fires precisely while `mise.toml` is being
edited. `hk.pkl` has a separate `taplo` step (`hk.pkl:167`) but it cannot shield
this one: `no_hk_depends` (`hk.pkl`, 2 hits) bans step ordering, so they race.

`hk.pkl`'s own read at the top of `hooks_running_the_gate` is unguarded too,
but that predates this diff.

### Finding 7 — the compatibility views disagree

`Job`'s docstring says "``run_commands`` and ``uses`` remain available to
existing callers." `job_runs_the_gate` honours that with a fallback
(`step.reached_hooks or _hooks_in_command(step.command)`, line 469);
`_first_gate_step` (line 486) has no fallback, and `job_installs_before_gate`
is built on it. Measured on the live `ci.yml::lint` job:

```
UNRESOLVED job (straight from parse_jobs):
  job_runs_the_gate       = True
  job_installs_claude_code= True
  _first_gate_step        = None
  job_installs_before_gate= False      <-- compliant job reported as not-before
RESOLVED job:
  job_runs_the_gate       = True
  _first_gate_step        = 8
  job_installs_before_gate= True
```

Separately, `job_installs_before_gate` also returns False when the job has no
gate at all, so `not job_installs_before_gate(...)` reads as a violation for
every ungated job.

### Finding 8 — the exported predicates are dead in production

`scan_workflows` (lines 551-581) calls `_first_gate_step` and
`_first_install_step` only. A repo-wide grep finds `job_runs_the_gate`,
`job_installs_claude_code` and `job_installs_before_gate` referenced nowhere
outside the module and `tests/test_workflow_claude_code.py:416-418`. That test,
`test_live_composite_expansion_retains_setup_before_the_first_gate`, therefore
asserts three predicates the gate itself never executes.

### Finding 9 — two of three prose false positives are new

```
old=[]         new=['fix']    :: # hk fix is run by autofix.yml
old=[]         new=['check']  :: echo "remember to run hk check before pushing"
old=['check']  new=['check']  :: grep -rn "hk run check" docs/
```

`old` is the pre-change `\bhk\s+run\s+([A-Za-z][\w-]*)`. The `check|c|fix|f`
alternation (lines 85-86) turns a two-token mention into a match, so a shell
comment or an `echo` inside a `run:` block now produces a violation. A run
block containing `./tools/hk-wrapper.sh check` correctly stays clean.

### Finding 10 — expansion escapes the repo root

`action_dir = root / uses[2:]` (line 419) accepts `./../zz-outside`. Probed by
writing a composite one level above the copied root:

```
C5 traversal '../zz-outside' expanded steps: (RunStep(command='hk fix', reached_hooks=frozenset({'fix'})),)
```

### Probed and NOT defects

- **`HK_COMMAND[2]` (line 121) is not a silent-decay risk.** Mutating
  `lint.py` to `HK_COMMAND = ("hk", "run", "--all", "check")` in the archived
  copy and re-running the file's tests under a shadowing `PYTHONPATH` gives
  `5 failed, 44 passed`, `rc=1`, including
  `test_live_mise_task_routes_are_derived_from_the_tracked_graph`. The index is
  bound by tests. File restored from `git show` afterwards.
- **`except yaml.YAMLError, OSError, UnicodeDecodeError:` (line 426, no
  parentheses) is valid here.** `python/pyproject.toml:5` sets
  `requires-python = ">=3.14"`, the interpreter is 3.14.0, and PEP 758 permits
  the unparenthesised form when there is no `as` clause. The sibling at line
  ~560 needed parentheses only because the commit added `as error`.
- **Ordering and composite semantics are correct.** Eleven arms, all as
  intended: install-before passes, install-after yields the "AFTER the first hk
  step" message, a composite that runs hk is caught, an outer install before a
  gated composite passes, an install nested *inside* a composite after its own
  hk step is flagged late, a nested `setup-claude-code` inside a composite
  satisfies the gate, and both `./` and `$/` install spellings resolve.
- **The mise dependency walk works on the live tree.** Derived routes:
  `lint -> {check}`, `fmt -> {fix}`, `pre-commit -> {pre-commit}`,
  `check -> {pre-commit}` (inherited through `depends = ["pre-commit", "test"]`
  at `mise.toml:290`, the only live `depends` assignment). Cycle fixture
  terminates.
- **No `suites.toml` contract binds this chain** — 0 hits for
  `workflow_claude_code` at `67a6cad` *and* 0 at `7c555a8`, so this is a
  pre-existing gap, not a regression introduced here. Sibling gates such as
  `workflow.bash-logic-enforcement` do have one.
- `hk.pkl:441-443` glob additions are asserted by
  `tests/test_workflow_claude_code.py:490-493`.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repository under review.
- [jdx/hk](https://github.com/jdx/hk) — `hk --help` / `hk run --help` on the installed 1.57.0, for the global-flag and usage claims.
- [jdx/mise](https://github.com/jdx/mise) — `mise run --help` on the installed 2026.9.9, for the flag-position and `:::` claims.

---

## Architect refutation pass (2026-09-16, cited-first, severity order)

Probes re-run by the architect with literal argv (a first attempt through a
shell variable failed its own control arm — zsh does not word-split — and was
discarded): `hk run check --all --plan` rc=0 "Plan: check"; `hk run --all --plan
check` rc=0 "Plan: check"; `hk run pc --plan` rc=0 "Plan: pre-commit";
control `hk run zzqnothook --plan` rc=1 "Hook 'zzqnothook' not found".

| # | Sev | Verdict | Disposition |
|---|---|---|---|
| 1 | HIGH | **CONFIRMED** | `:78-79` carries only the short spellings of `--slow/--verbose/--no-progress/--quiet`; `hk --help` lists both. Respec: flag tables pinned as data with both spellings, tests derived from the table. |
| 2 | HIGH | **CONFIRMED** | `hk run --help`: `Usage: hk run [FLAGS] [FILES]… <SUBCOMMAND>`; measured `hk run --all --plan check` rc=0. Hooks are `run` subcommands with aliases (`pc`, `cm`, `pp`, `pcm`) — a second route the review did not name. Respec. |
| 3 | HIGH | **CONFIRMED** | `mise run --help`: "Put mise flags before the task name"; `--force` documented; `mise --help` lists `-C/--cd`. Respec with both flag tables. |
| 4 | MED | **CONFIRMED** | `:150` `tomllib.loads` unguarded. Respec: a malformed `mise.toml` raises a NAMED error (fail loud, mise itself cannot run on it) — never a traceback. |
| 5 | MED | **CONFIRMED** | `mise run --help`: `:::` separates tasks. Respec. |
| 6 | MED | **CONFIRMED** | `:99` lookahead `(?=\s|[;&|)]|$)` excludes quotes. Respec: quotes and backticks terminate a token. |
| 7 | MED | **CONFIRMED** | `job_installs_before_gate` reads `reached_hooks` only; `job_runs_the_gate` falls back to direct parsing. Respec: identical behaviour on resolved and unresolved jobs, and the production scan uses the public predicates (#8). |
| 8 | LOW | **CONFIRMED** | `scan_workflows` uses `_first_gate_step`/`_first_install_step`; the three public predicates are off the production path. Respec (with #7). |
| 9 | LOW | **CONFIRMED, narrow fix** | a `run:` line that is a shell comment can flag. Respec: comment lines (`^\s*#`) are ignored; inline comments stay a documented residual. |
| 10 | LOW | **CONFIRMED** | `:419` `root / uses[2:]` has no containment check. Respec: a local action resolving outside the root contributes nothing. |
| 11 | LOW | **CONFIRMED** | mise merges `.config/mise/conf.d/*.toml`; the gate reads only `mise.toml`. Respec: read tracked conf.d fragments too; docstring names both. |
| 12 | LOW | **CONFIRMED** | the parametrize list mirrors the regex. Respec: derive the flag arms from the module's pinned flag table (both spellings) and keep an adversarial list including the nine MISSED spellings. |

Round 1 of 2 for the codex diff; the respec goes back to the codex lane.
