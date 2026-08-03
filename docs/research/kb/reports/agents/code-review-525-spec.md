# Code review — Spec axis — #525 (`472a63e`, `tests/test_branch_guard.py` +171 −17)

Verdict: **the diff implements #525.** All nine acceptance criteria are
satisfied; three carry qualifications below. No scope creep of substance. No
finding rated above NIT.

## Criterion-by-criterion

| # | Criterion (abbrev.) | Verdict |
|---|---|---|
| 1 | fixture whose remote default resolves, distinct from the no-remote one | **PASS** — `remote_repo` (`_advertise_default` sets `refs/remotes/origin/HEAD`); `repo` keeps the no-remote shape |
| 2 | write on the advertised default denied, *same reason text as today* | **PASS, with a NIT** (below) |
| 3 | write on a feature branch of that repo allowed | **PASS** — `test_allows_a_feature_branch_when_the_default_is_advertised` |
| 4 | unconventional default protected; conventionally-named branch not | **PASS** — `test_advertised_default_wins_over_the_conventional_names`, both arms in one test |
| 5 | git invocation count asserted at today's value | **PASS** — 1 / 3 / 4, matching `branch_guard.decide`'s real call sequence |
| 6 | count from git's own tracing facility written to a path | **PASS — verified, not taken on trust** (below) |
| 7 | count runs through the real wired guard | **PASS — verified** (below) |
| 8 | existing tests still pass unchanged | **PASS in behaviour; one body edited** (NIT below) |
| 9 | lint / suite / contracts green | **CANNOT TELL from the diff** — I ran `tests/test_branch_guard.py`: `18 passed`, `rc=0`. `mise run lint` and `mise run verify` are the sibling axis / ship gate |

## The two criteria worth checking carefully — both hold

**#6 "git's own tracing facility written to a path — no monkeypatched subprocess
call and no shim executable."** Real, not comment-deep. `_guard_via_wrapper`
passes `GIT_TRACE=<abs path>` in the child env and counts
`text.count("built-in: git ")` from the file. There is no `monkeypatch` and no
PATH manipulation anywhere in the file (`import` list is `json, os, subprocess,
pathlib`). Control arm run directly: `GIT_TRACE=<abs> git rev-parse
--abbrev-ref HEAD` → file created, exactly one line
`trace: built-in: git rev-parse --abbrev-ref HEAD`. So the counter both fires
and discriminates.

*NIT (forward-looking):* the token counts **builtins only**. If #527 ever routes
a call through an alias or an external subcommand, the count would silently drop
rather than fail — the gate would read as an improvement it did not make.

**#7 "runs through the real wired guard, not the module in isolation."** Real.
The three count tests `subprocess.run(["bash", str(_WRAPPER)], …)` with a JSON
`{"tool_name": "Write", …}` payload on stdin, `CLAUDE_PROJECT_DIR` set. That
script is byte-identically the one `.claude/settings.json` wires for matcher
`Bash|AskUserQuestion|Edit|Write|NotebookEdit`, so the assertion crosses
wrapper → `uv run` → CLI → `hook_guard` → `branch_guard`. Two incidental
strengths: `uv`/the CLI contribute **0** git calls (proved by the
outside-repo arm being exactly 1), and the deny test pins the *decision*
(`'"permissionDecision": "deny"' in stdout`) alongside the count, so a guard
that decided nothing cannot pass it.

## (a) Missing / partial

- **NIT, criterion 2** — *"denied, **with the same reason text as today**"*. The
  new `test_denies_on_the_advertised_default_branch` asserts `"default branch"`
  and `"git checkout -b"`, but drops the `"tracked.md"` assertion its no-remote
  twin (`test_denies_tracked_file_on_default_branch:138`) makes. One assertion
  weaker than "today", so a reason that lost its path interpolation would pass
  on the resolvable path and fail only on the fallback path.

## (b) Scope creep

None material. The refactors (`_init_repo`, `_head_sha`) exist to serve the new
fixture and are the minimum needed. `_GIT_CALLS_*` constants and the `#527`
pointer are within #525's stated intent ("arms the gate the next ticket will
move").

## (c) Implemented but wrong

None found. Specifically checked and clean: `_advertise_default` uses an
**unreachable** remote URL (`https://example.invalid`) plus a local
`update-ref`, so nothing touches the network and `symbolic-ref` resolves
locally; per-test `tmp_path` trace files mean no cross-test accumulation; the
criterion-4 second arm (`checkout -b main` in a `develop`-default repo) is
genuinely armed — `origin/HEAD` still points at `develop`, so the allow is the
real inverted-guard detector the docstring claims.

- **NIT, criterion 8** — *"All existing write-guard tests still pass unchanged."*
  Behaviourally true (18 pass). Literally, one existing test body changed:
  `test_allows_when_detached_head` had its inline `rev-parse HEAD` swapped for
  `_head_sha(repo)`. Mechanical, no assertion changed — flagged only because the
  criterion says "unchanged".

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issues #525 and #524 (the spec under review) and the working tree at `472a63e`.
