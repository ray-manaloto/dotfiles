# Spec-axis code review — #526 (`fd57fb4`) + #527 (`18d4e14`)

Diff: `git diff b7ad7a8...HEAD`, against the acceptance-criteria checklists in
#526 / #527 (+ their comments) and parent #524.

**Verdict: both checklists are met.** One low-severity gap, one dead-code
residue, no wrong implementations found.

## (a) Missing / partial

### F1 (low) — #527: only rc==1 reaches the fallback

> "When the combined invocation fails, the guard falls back to the separate
> invocations and returns the identical decision"

`_protected` branches three ways: `rc==0 and len(lines)==3` → parse; `rc==1` →
`_separate_facts`; **everything else → `return None` (allow), no fallback**. So
the fallback fires on *one* failure code, not on "fails".

I probed every other reachable failure and each is decision-identical to the
separate path, so nothing regressed:

| case | combined rc | new | pre-#527 |
|---|---|---|---|
| outside any repo | 128 | allow | allow |
| unborn HEAD (`git init`, no commit) | 128 (stdout has 2 lines) | allow | allow (`_git` → None on 128) |
| bare repo | 128, empty stdout | allow | allow (empty toplevel → falsy) |
| no `origin/HEAD` | 1 | fallback | — |

Residual: `rc==0 and len(lines)!=3` allows *without* falling back and carries no
comment or test; I could not construct it (rc 0 implies all three printed). The
docstring's "which is what the fallback would conclude anyway" is argued, not
armed — no test drives a non-1 non-zero rc *inside* a repo. Worth one armed
test (unborn-HEAD repo → allow) since that is the only claim standing between
the collapse and the criterion's literal wording.

### F2 — #527 criteria I cannot verify from the diff

"The lint gate, the full test suite and the verification contracts are green"
and "the live arms are re-run through the real wrapper before shipping" are
process criteria; the PR body records the before/after table as required
(criterion: *"The pull request body records the before and after measurement"*
— present in #532, all four rows).

## (b) Scope creep

### F3 — `repo_root()` is now dead production code

`_protected` no longer calls it (`_probe_dir` + the combined vector replaced
it); grep across `python/`, `tests/`, `scripts/`, `.claude/` finds no caller.
Neither ticket asked to retain a superseded public helper — the shape
`tool-currency-and-native-first.md` rule 3 names ("retire the custom code in the
same change").

Otherwise clean. #526 touches only `tests/test_hook_guard.py` plus the two doc
indexes, honouring *"It changes no production code"*.

## (c) Implemented but looks wrong

_None found._

## The two criteria weighed explicitly

**"A path outside any repository is still allowed, and still short-circuits
before the full walk."** Honoured, not merely un-contradicted. Probed: the
longer arg vector still fails `fatal: not a git repository` at rc 128 *before
any ref work*, so the cost is one process — pinned as equality by
`test_a_write_outside_any_repo_costs_one_git_call` (`_GIT_CALLS_OUTSIDE_REPO =
1`). The `--quiet --verify` choice is what earns this: without it a missing
`origin/HEAD` is also 128, the codes become indistinguishable, and the
short-circuit would have to be surrendered (a redundant fallback on the
hot scratchpad path). The `_probe_dir` ancestor walk is filesystem-only and
unchanged from before.

**"When the combined invocation fails, the guard falls back…"** — see F1. Not
every failure mode reaches it; all of them are nonetheless decision-identical.
I would call this satisfied in substance, under-armed in evidence.

## #526 checklist walk (all green)

- *"dispatches a real hook payload through the real entry point in a fresh
  interpreter"* — real console script `dotfiles-setup hook pretooluse`, real
  Bash payload, subprocess.
- *"reports which of a named set of heavy modules are resident"* — the
  `resident` list is in the failure message.
- *"reflects today's reality … and fails if that set is described wrongly"* —
  `resident == list(_HEAVY_MODULES)`, equality both ways.
- *"includes the settings module and its transitive validation dependency"* —
  `dotfiles_setup.config`, `pydantic_settings`, `pydantic`.
- *"No wall-clock threshold"* — none; the comment's `-X importtime` ban from the
  ticket comment is honoured.
- *"does not depend on import ordering within the test session"* — fresh
  interpreter + `atexit`, per the settling comment.
- Both traps from the load-bearing comment are encoded: `rc == 0` **and**
  `snapshot.exists()`, in that order, with the `os._exit` rationale inline.

Nit (non-spec): `_import_surface` sets `PYTHONPATH` to the probe dir only,
discarding any inherited `PYTHONPATH`; harmless here, but it is the shape that
broke `check_offroot_arm`'s env scrubbing once before.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo
  under review; issues #524/#526/#527 and PR #532.
