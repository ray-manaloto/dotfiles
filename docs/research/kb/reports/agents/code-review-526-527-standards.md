# Code review — STANDARDS axis — `b7ad7a8...HEAD` (#526 fd57fb4, #527 18d4e14)

Scope: `branch_guard.py`, `tests/test_branch_guard.py`, `tests/test_hook_guard.py`,
`tests/AGENTS.md`, `tests/TEST-INDEX.md`. Spec conformance is a separate axis.

## A. Documented-standard violations

### A1 (hard) — `repo_root()` is now dead public API

`python/src/dotfiles_setup/branch_guard.py:129`. #527 replaced its only caller
(`_protected`) with `_probe_dir` + `_git_capture`; the function survives with
**zero callers repo-wide**.

Control arm (same command shape, siblings that ARE called):

```
repo_root        0
is_ignored       2
default_branch   2
_probe_dir       2
```

Breaches `.claude/rules/tool-currency-and-native-first.md` rule 3 — "when a
native feature supersedes custom code, RETIRE the custom code … don't leave it
lingering". Second-order: it is now untested (no arm reaches it), so per
`probes-need-a-control-arm.md` it is a symbol with no arm in either direction.
Fix: delete it, or make `_separate_facts` call it (which also fixes B2).

### A2 (judgement, leaning hard) — an undocumented silent ALLOW

`_protected`, `branch_guard.py:~215`:

```python
if code == 0 and len(lines) == _COMBINED_FACT_COUNT:
    ...
elif code == _UNRESOLVED_REF_RC:
    ...
else:
    return None
```

The docstring enumerates exactly three cases (`0`, `1`, anything else). A git
that **returns 0 but prints an unexpected line count** is a fourth case, and it
lands in the `else` branch — i.e. the guard allows the write on the strength of
"no usable repository", which is not what happened. The code disagrees with its
own documented case analysis, nothing arms it, and the failure direction is
open. `zero-skip-policy.md` (no dismissed diagnostic) + the guard's own
fail-closed intent. Either document it as a deliberate allow, or route it to
`_separate_facts` like the rc=1 case.

## B. Baseline smells (judgement calls)

### B1 — Duplicated Code: default-branch derivation, twice

`default_branch()`:

```python
if out and "/" in out:
    return (out.split("/", 1)[1],)
return _FALLBACK_DEFAULTS
```

`_protected()`:

```python
defaults = (advertised.split("/", 1)[1],) if "/" in advertised else _FALLBACK_DEFAULTS
```

Same rule, two sites; a change to how the advertised default is parsed must be
made in both. → extract `_defaults_from(advertised: str) -> tuple[str, ...]` and
call it from both.

### B2 — Duplicated Code: root resolution, twice

`repo_root()`'s body and `_separate_facts()`'s first three lines are the same
shape (`_git(["rev-parse", "--show-toplevel"], probe)` → `Path(out).resolve()`).
Collapsing A1 into `_separate_facts` removes this too.

### B3 — Primitive Obsession / positional tuple

`_git_capture` returns a bare `tuple[int, str] | None` that `_git` reads
positionally (`res[0] != 0`, `res[1]`). The `(rc, stdout)` pair is a concept
worth naming — a `NamedTuple` costs nothing and makes `_protected`'s
`code, out = combined` self-describing. Related: `_COMBINED_FACTS` is a mutable
module-level `list` while every sibling constant is a `tuple`/`frozenset`
(`_FALLBACK_DEFAULTS`, `_TOOLS`); it is a `list` only because `_git` types its
parameter that way.

### B4 — the measured number lives in three places

`_GIT_CALLS_ON_FEATURE_BRANCH = 1`, the test **name**
(`..._costs_one_git_call`), and the docstring/TEST-INDEX prose. This diff had to
rename two tests for a pure constant change — Shotgun Surgery in miniature, and
the diff is its own evidence. Name the tests for the *property*
(`..._costs_the_pinned_number_of_git_calls`) and let the constant carry the
value.

### B5 — `_import_surface` clobbers `PYTHONPATH`

`tests/test_hook_guard.py`, `env={**os.environ, "PYTHONPATH": str(probe)}`
replaces rather than prepends. Harmless on a clean host, silently drops a
developer's or CI's `PYTHONPATH`. → `os.pathsep.join(filter(None, [str(probe),
os.environ.get("PYTHONPATH", "")]))`.

## C. Explicitly NOT flagged (repo standard wins over the baseline)

- `except OSError, subprocess.SubprocessError:` — endorsed by
  `python/AGENTS.md` (PEP 758 comma-except, py3.14).
- Inline `timeout=120` in `_import_surface` — matches the same file's existing
  convention (`test_hook_guard.py:696`), even though `test_branch_guard.py`
  names `_WRAPPER_TIMEOUT_S`.
- `assert` statements inside the `_import_surface` helper, real subprocesses,
  zero mocks — exactly `tests/AGENTS.md` "mock at system boundaries only" and
  "public interface".
- The very long narrative docstrings/comments — this repo's house style; every
  neighbouring function carries them.
- The #526 control arm (`test_the_import_surface_probe_sees_a_lean_process`) and
  the snapshot-existence assert are textbook
  `probes-need-a-control-arm.md` rules 1–2. Good, not a finding.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo
  under review; source, tests and `.claude/rules/` standards read locally.
