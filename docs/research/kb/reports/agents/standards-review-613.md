# Standards-axis review — branch `536e0ec` (#613)

Reviewer: standards axis (documented repo standards + smell baseline).
Status: IN PROGRESS — findings appended as found.

## Findings

### F1 — JUDGEMENT CALL — Speculative Generality: `build_codex_argv(sandbox=...)`

`python/src/dotfiles_setup/codex_lane.py:195-200`

```python
def build_codex_argv(
    run_dir: Path,
    *,
    sandbox: str = READ_ONLY_SANDBOX,
    model: str | None = None,
) -> list[str]:
```

`sandbox` is **never passed by any caller**. Control-armed against its sibling:
`model` IS exercised (`main.py:840` `--model`, `codex_lane.py:350`
`model=request.model`, `tests/test_codex_lane.py:298`), so the grep
discriminates. Every call site is `build_codex_argv(run_dir)` or
`build_codex_argv(run_dir, model=...)`:

- `codex_lane.py:350`, `tests/test_codex_lane.py:265,277,290,297,298`,
  `tests/test_codex_lane_e2e.py:146,158` — zero `sandbox=`.

The module's own docstring says a review lane "must not write" — i.e. the value
is an **invariant**, not a knob. A parameter that can only ever hold one value
is an abstraction for a need the spec does not have (smell: Speculative
Generality). Inlining `READ_ONLY_SANDBOX` into the argv list would make the
invariant unbreakable rather than merely un-exercised. Minor: the test
`test_the_argv_sandboxes_the_review_lane_read_only` pins the default, so
nothing is unguarded today — this is design tidiness, not a defect.

### F2 — JUDGEMENT CALL (strong) — Divergent Change + Mysterious Name: `_add_report_parsers` grew a second mutating command, and its docstring was not updated

`python/src/dotfiles_setup/main.py:790` adds `_add_codex_lane_subcommand(subparsers)`
inside `_add_report_parsers`, whose docstring (`main.py:709-723`) still reads:

> "Register the **read-only** scan-and-report commands, **plus dag-tick**. …
> these share a shape (scan something, render markdown, **change nothing**) …
> `dag-tick` (#578) is grouped here too for the same statement-budget reason
> **even though it can act**"

`codex-lane` is the most side-effecting command in the file: it mkdirs, unlinks
four artifacts, writes two files and spawns a **paid** subprocess. The docstring
now under-enumerates its own contents, and the container's name describes a
minority of what it registers.

The #578 respec already named this exact smell ("the divergent-change smell of a
mutating command inside a function documented as read-only") and accepted it once,
on the narrow grounds that moving `dag-tick` out trips ruff PLR0915 on
`setup_parser` (51 > 50 statements). That justification was for **one**
exception; the diff takes a second without re-arguing it or extending the note.

Cheapest fix that keeps ruff green: a sibling grouping function (e.g.
`_add_agent_lane_parsers`) called from `setup_parser` alongside
`_add_report_parsers` — one added statement, not the four an inline registration
would cost. At minimum, the docstring should name `codex-lane` so the file does
not document a shape it no longer has.

### F3 — JUDGEMENT CALL — Duplicated Code (prose) / Shotgun Surgery: the "why not `run-lane.sh`" justification is written out three times

The same four-clause argument is stated near-verbatim in three un-gated places:

- `python/src/dotfiles_setup/codex_lane.py:11-21` (module docstring)
- `mise.toml:535-540` (`[tasks.codex-lane]` comment)
- `python/verification/suites.toml:1826` (suite `description`)

Measured by shared distinctive terms — `mktemp` hits all three,
`plugins/marketplaces` hits all three, `mid-reasoning` hits `codex_lane.py:34`,
`codex_lane.py:253` and `suites.toml:1826`.

`use-tool-builtins.md` rule 3 asks for the justification "in the code comment
**or** PR body" — one home, not three. The drift hazard is concrete, not
stylistic: two of the three copies cite the plugin script by **line number**
(`codex_lane.py:14` "``mktemp``s both its output paths (``:56-57``)";
`suites.toml:1826` "(`:56-57`)") against a file the module itself notes is
"replaced wholesale on plugin update". When that file moves, the citation is
wrong in two places and nothing checks either.

Suggested: keep the full argument in the module docstring (the one place a
reader of the code lands), and reduce `mise.toml` and `suites.toml` to a pointer.

### F4 — NOT A VIOLATION (measured, recorded so it is not re-raised)

The new `suites.toml` description is **4,834 chars** — large, but within repo
precedent: across 121 descriptions in that file the max is **12,767** and this is
2nd-largest (measured with a python `re` scan over
`python/verification/suites.toml`). Median 213. The repo endorses the long-form
contract description, so the baseline "too long" reaction is suppressed here.

Likewise **skipped as tooling-enforced** per the brief: `per_path_tokens`
uniqueness (`hk.pkl:305-307` runs `dotfiles-setup token-audit`), ruff/ty/hk
formatting, and the `md_size_budget` / agnix budgets.

### F5 — STRONGEST FINDING — the diff's own anti-drift invariant is applied to the dirname but NOT to the status string

The module goes to unusual lengths for one shared literal
(`python/src/dotfiles_setup/codex_lane.py:61-66`):

```python
# IMPORTED from the consumer, never restated. A duplicated "codex-lane" literal
# is two sources of one truth, and the drift is silent in the worst direction:
# the launcher keeps writing to a directory the reaper stopped scanning, and
# every lane goes quiet.
LANE_DIRNAME = CODEX_LANE_DIRNAME
```

`python/verification/suites.toml:1826` elevates that to a contract:
"⭐ THE ANTI-DRIFT INVARIANT: the producer IMPORTS `CODEX_LANE_DIRNAME` from the
consumer rather than restating 'codex-lane'."

**Eighteen lines later the same file restates a different consumer literal:**

- `python/src/dotfiles_setup/codex_lane.py:84` — `_IN_PROGRESS = "in_progress"`
- `python/src/dotfiles_setup/codex_verdict.py:91` — `_IN_PROGRESS = "in_progress"`
  (the value the CAS compares against at `codex_verdict.py:456-461`)
- and a third copy in `tests/test_codex_lane.py:133` —
  `assert lane["status"] == "in_progress"`, a restated literal in the file whose
  own docstring (`:8-15`) declares "assert through the real consumer, never
  against a restated literal".

The drift direction is **identical to the one the comment argues about, and
equally silent**. If the consumer's value changes, every lane the producer writes
becomes `STATUS_MISMATCH` — which the diff's own test docstring
(`tests/test_codex_lane.py:140-142`) describes as "a no-op edge, so the reaper
would be silent rather than wrong". That is precisely the failure mode #613 exists
to close, reintroduced through the one constant that was not imported.

Mitigations, stated fairly: the consumer's name is **private** (`_IN_PROGRESS`), so
there is nothing public to import today — the fix is to export it from
`codex_verdict` (every other shared name here already is: `LANE_FILENAME`,
`LANE_LOG_FILENAME`, `VERDICT_FILENAME`, `PROCESSED_FILENAME`,
`EXIT_MARKER_FILENAME`, `VERDICT_SCHEMA`). And `tests/test_codex_lane.py:137-165`
drives the real CAS in both directions, so the agreement is *tested* even though
it is not *structural* — which is exactly the weaker guarantee the dirname comment
rejects for its own case.

### F6 — JUDGEMENT CALL (minor) — `CODEX_BIN = "codex"` resolves through `PATH`

`python/src/dotfiles_setup/codex_lane.py:72` hardcodes the bare binary name, and
`run_codex` (`:285-291`) execs it with no `shutil.which` check. `codex` is pinned
host-only in `mise.toml`, and `.claude/rules/mise-tasks-only.md` says to use "the
mise-pinned binary directly". Under `mise run codex-lane` the shim is on `PATH`, so
this works; invoked from launchd (which the module explicitly anticipates —
`:36` "where launchd logs it") the `PATH` may not carry mise's shims. The failure
is at least loud and correctly handled: `FileNotFoundError` from `subprocess.run`
is a `BaseException`, so `launch_lane`'s handler settles the lane
(`LAUNCHER_FAILED_EXIT`) and it escalates to `needs_human` on the next tick — the
design already covers it. Noting it only because the escalation reads as a review
failure rather than "the binary was not found".

### F7 — POSITIVE (recorded so the axis is not read as one-sided)

Genuinely compliant against the documented standards I checked:

- `.claude/rules/ai-cli-invocation.md` — the argv
  (`codex_lane.py:225-239`) matches the prescribed research/debate form exactly
  (`codex exec --ephemeral --sandbox read-only … -`), including the trailing `-`
  for stdin and the ARG_MAX rationale. No `-p`-as-prompt, no `codex exec "prompt"`.
- `.claude/rules/zero-bash-logic.md` — both new `mise.toml` tasks are thin callers;
  zero new `.sh`.
- `.claude/rules/use-tool-builtins.md` rule 3 — the "why not the plugin script"
  justification is written down (over-written, see F3, but present).
- `.claude/rules/probes-need-a-control-arm.md` — every arm in
  `tests/test_codex_lane.py` has a paired control
  (`:152`, `:211`, `:227`, `:317`, `:359`, `:489`, `:552`), and
  `tests/test_codex_lane_e2e.py:158-167` arms the schema check with a knowingly-
  invalid schema that must fail.
- `tests/AGENTS.md` § Mocking — the `codex` subprocess is **injected** as `runner`
  (`codex_lane.py:316`), not monkeypatched; no internal module is mocked.
- `tests/AGENTS.md` test-count line and `tests/TEST-INDEX.md` were both updated in
  the same commit (1,453 -> 1,552; two new rows).

### F8 — JUDGEMENT CALL — Duplicated Code in the paid arm: two identical `codex exec` launches where one would do

`tests/test_codex_lane_e2e.py:88` and `:118` are the same call:

```python
result = cl.launch_lane(tmp_path, _request())  # :88,  then asserts the edge
result = cl.launch_lane(tmp_path, _request())  # :118, then asserts the payload
```

Plus two more real invocations at `:145` and `:157`. That is **4 paid `codex exec`
calls per run** for 3 tests.

The file's own docstring argues for frugality — `:6-7`: "It costs real credits per
run — that is the reason for the gate, and the reason it is a handful of tests
rather than a matrix" — then pays twice for one launch whose two assertion sets are
independent. A module-scoped fixture returning one `LaunchResult` (or folding the
raw-payload assertions into the first test) removes a call without weakening
anything: the two tests assert different things about the *same* artifact, which is
what a shared fixture is for.

The `:145`/`:157` pair is **not** redundant — that is the required control arm and
must be a second, differently-configured call.

Related, minor: `:145-152` re-implements the `subprocess.run` invocation instead of
calling `cl.run_codex`. Justified (it needs `capture_output=True`, which `run_codex`
deliberately refuses — `codex_lane.py:269-274`), so noting it only to record that
the duplication was checked and is intentional.

## Summary

No **hard** violation of a documented standard found. The diff is unusually
well-aligned with `ai-cli-invocation.md`, `zero-bash-logic.md`,
`probes-need-a-control-arm.md` and `tests/AGENTS.md` (see F7).

Ranked judgement calls:

1. **F5** — the anti-drift invariant the diff documents and contracts for the
   dirname is not applied to `"in_progress"`, whose drift has the same silent
   failure mode. Highest value to fix.
2. **F2** — `_add_report_parsers` now registers a second mutating command; its
   docstring still says "read-only … change nothing".
3. **F3** — the run-lane.sh justification lives in three files, two of them
   carrying a line-number citation into a file that is replaced on plugin update.
4. **F8** — the paid e2e arm makes two identical launches.
5. **F1** — `build_codex_argv(sandbox=...)` is never overridden.
6. **F6** — bare `codex` on `PATH` under launchd (design already degrades safely).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo
  under review; all standards sources and the diff read from the working tree.

