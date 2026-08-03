# Code review #525 — Standards axis

Diff: `472a63e` (`49ef5bb..HEAD`), one file — `tests/test_branch_guard.py`, +171 −17.
Scope: documented repo standards + baseline smells only. Correctness/spec is a sibling agent's.

Tooling (ruff/ty/hk) already passes; nothing tooling enforces is reported here.

---

## H1 — HARD: the three cost tests assert implementation detail

`tests/AGENTS.md` § "What a good test is here":

> Tests verify behavior through a **public interface** … never through
> implementation details. **The tell for an implementation-coupled test is that
> it breaks under a refactor while behavior hasn't changed.**

The diff's own comment states the tell verbatim:

```python
# ... #527 lowers them by collapsing the three
# `rev-parse`/`symbolic-ref` calls into one; that ticket updates these.
_GIT_CALLS_OUTSIDE_REPO = 1  # rev-parse --show-toplevel, which fails
_GIT_CALLS_ON_FEATURE_BRANCH = 3  # + abbrev-ref HEAD, + symbolic-ref origin/HEAD
_GIT_CALLS_DENY_ON_DEFAULT = 4  # + check-ignore
```

After #527 the guard's *behaviour* is byte-identical — same decision, same
reason — and three tests go red. The per-constant comments name the exact git
subcommands, which is the coupling made explicit.

The underlying intent (pin the ~340ms/edit cost so it cannot regress) is
legitimate and worth keeping. The standard-conforming shape is a **ratchet, not
an equality**: `assert calls <= _GIT_CALL_BUDGET_*`. That still fails on
regression (a 5th call), still fails if the early exit stops being early, and
#527 then *lowers the budget* instead of being forced to edit a test to land an
improvement it did not change behaviour with.

## H2 — Judgement: the trace probe cannot distinguish "0 calls" from "no tracing"

```python
text = trace.read_text() if trace.exists() else ""
return proc.stdout, text.count("built-in: git ")
```

`"built-in: git "` is git's human-readable `GIT_TRACE` line format — undocumented
and version-dependent. If it changes, or `GIT_TRACE` is suppressed in another
environment, `count` silently becomes 0 and all three tests fail *attributing the
change to the guard*. `probes-need-a-control-arm.md` rule 4: "A redirect/timeout/
parse-error is not a 'no'." Partially armed already — three distinct expected
counts (1/3/4) do discriminate between the paths — but nothing separates a broken
tracer from a changed guard. One line fixes it: assert the trace file is non-empty
(or contains `rev-parse`) before counting.

## H3 — Documented standard, trivial: `timeout=120` is an unnamed magic number

`tests/AGENTS.md` § "Named constants for magic numbers" ("`test_image_smoke.py`
uses `_PLAIN_BYTES_VALUE = 512` etc. rather than inline literals"). The diff
carefully names the three call counts, then leaves `timeout=120` inline in
`_guard_via_wrapper`. `_WRAPPER_TIMEOUT_S = 120`.

## H4 — Smell (judgement): Primitive Obsession / Data Clump on the helper seam

`_guard_via_wrapper(target, trace) -> tuple[str, int]` makes every call site
destructure an unnamed pair *and* invent the trace path:

```python
stdout, calls = _guard_via_wrapper(outside / "MEMORY.md", tmp_path / "t.log")
```

repeated three times with the literal `"t.log"`. The trace file is an
implementation detail of the helper leaking into all three callers. Take
`tmp_path` and derive the path inside (`tmp_path / "git-trace.log"`), or return a
small named result. Also **Mysterious Name**: `t.log` reveals nothing.

## H5 — Low: index/count drift the diff perpetuates

`tests/TEST-INDEX.md` has no row for `test_branch_guard.py` (control arm:
`test_hook_guard` → 1 hit, so the grep discriminates), and `tests/AGENTS.md`
still says "Total: **1,144 pytest tests**" against **1,228 collected** today.
Both predate this diff (`test_branch_guard.py` arrived in #523, and
`test_ask_quality.py` is unindexed too), so neither is a violation *by* this
change — but a diff adding a whole new labelled section to that file is the
natural place to add the row.

---

## What conforms, explicitly

- **No mocking** — `tests/AGENTS.md` § "Mocking" is satisfied well: real git
  repos, the real `scripts/pretooluse-guard.sh` through `bash`, no
  monkeypatched `subprocess.run`, no PATH shim. The docstring's reasoning
  (`use-tool-builtins.md`: git's own tracing over a homegrown shim) is the right
  call and correctly cited.
- **Absolute paths** — `_PROJECT_ROOT = Path(__file__).parent.parent.absolute()`
  matches the § "Subprocess usage" requirement exactly.
- **Control arms** — `test_advertised_default_wins_over_the_conventional_names`
  runs both arms in one test and names the inversion it would catch;
  `test_a_denied_write_costs_four_git_calls` pins the decision alongside the
  count and says why. This is `probes-need-a-control-arm.md` rules 1–2 applied
  properly.
- **`_advertise_default` uses `https://example.invalid`** — no network in tests.
- **No inline suppressions.**

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under review; its `tests/AGENTS.md`, `tests/TEST-INDEX.md`, `.claude/rules/*`, `python/src/dotfiles_setup/branch_guard.py`.
