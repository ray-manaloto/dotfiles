# Cold review r2 — staged `claude_doctor` diff vs `ebaf702`

- **Resolved ref**: the STAGED diff against HEAD
  `ebaf702b0b49a3d67f3d39b36bb1532320fabf21`
  (`ebaf702 chore(deps): update dependency npm:renovate to v44.97.6 (#1195)`).
- **Scope**: `git diff --cached HEAD -- python/src/dotfiles_setup/claude_doctor.py
  tests/test_claude_doctor.py` — +141/−40 production, +235/−6 tests.
- **Method**: read-only against the working tree; prior form via
  `git show HEAD:<path>` and `git show :<path>` for the index; every mutation
  run on a scratch copy outside the repo. No source, config, test or fixture
  was edited. `git status --short` re-checked at the end: unchanged apart from
  this report.
- No intent framing was supplied. Findings are against the resolved diff and
  its consumers.

## Harness and control arms

Scratch harness (memory `stream-split-and-oracle-review`): `cp -R python` +
the test file into the scratchpad; `tests/test_claude_doctor.py` does its own
`sys.path.insert(0, __file__/../../python/src)`, so the scratch copy imports the
scratch module. Whole file runs in ~0.05 s.

- **Baseline**: 41 passed, rc=0.
- **Control arm (full production revert to `HEAD`)**: 26 failed / 15 passed,
  rc=1. The harness discriminates.
- **Gate inventory**: `grep -c claude_doctor python/verification/suites.toml
  hk.pkl` → `0` / `0`; control `grep -c 'PLANNING_DISABLED=1' suites.toml` → 7;
  fresh known-absent arm `qhx7vv2wnb` → 0. **No contract suite and no hk step
  binds this module — `tests/test_claude_doctor.py` is the entire gate**, so the
  mutation table below is the complete enforcement picture.
- **Caveat, stated**: my mutation runs copied the WORKING-TREE test file, which
  carries one unstaged line the index does not (see H2). That line is a return
  annotation; `from __future__ import annotations` is in force and annotations
  are never evaluated at runtime, so every runtime result below holds for the
  staged blob identically. H2 is reported against the staged blob directly.

### Callers of every changed signature (whole-repo search)

`_run` changed from `-> tuple[int, str]` to `-> tuple[int, str, str]` and gained
`stdout_only`. Searched `--include='*.py' --include='*.toml' --include='*.pkl'
--include='*.md' --include='*.ts' --include='*.json' --include='*.yml'`:

| Symbol | Callers found | Status |
|---|---|---|
| `_run` | `claude_doctor.py:305`, `:399`; test stub `_fake_run` | all three updated; **no external caller** |
| `latest_version` | `claude_doctor.py:435`, tests only | signature unchanged |
| `parse_doctor` | `claude_doctor.py:406`, tests only | signature unchanged |
| `evaluate` | `doctor.py:1262`, tests | signature unchanged |
| `claude_doctor_main` | `main.py:30`, `main.py:2854` | unchanged |
| `DoctorVerdict.to_json` | `.claude/skills/claude-doctor/hooks/register.ts:25` (`DoctorReport`) | key set unchanged |
| `_installation_findings` | new, private, `claude_doctor.py:420` only | — |

No signature change escapes the module.

**JSON contract, checked explicitly (verified negative).** `to_json()`
(`claude_doctor.py:168-182`) is not touched by the diff and still emits
`verdict, enforcement_eligible, running_version, install_method, latest_version,
clean_marker_present, findings`. `register.ts:25-32`'s `DoctorReport` declares
all of those except `clean_marker_present` — a pre-existing, harmless
under-declaration (`JSON.parse(...) as DoctorReport` tolerates extra keys), and
the diff neither adds nor removes a key. The hook reads `verdict` and `findings`
only (`register.ts` SessionStart/PreToolUse handlers), both of which keep their
types. **No consumer breakage.** What DOES reach the hook differently is the
*value* of `verdict` in the H1 case and the *contents* of `findings` in H1/M1/M4.

## Findings

| # | Sev | Claim | Location |
|---|---|---|---|
| H1 | HIGH | A previously-ENFORCING state became non-enforcing AND lost a repo-state finding: an unreadable running token now suppresses the `schemas/sources.toml` pin-currency finding, which has no dependence on the running version | `python/src/dotfiles_setup/claude_doctor.py:422-433` |
| H2 | HIGH — **RESOLVED mid-review** | The STAGED test blob failed `ty` (`error[invalid-return-type]`) — `_fake_run`'s outer annotation said `tuple[int, str]` while its inner stub returns a 3-tuple. The fix was staged while this report was being written; both staged blobs now pass `ty` | `tests/test_claude_doctor.py:88` (index blob) |
| M1 | MEDIUM | The oracle-failure `UNKNOWN` branch computes `installation_findings` and then discards it — the same masking the diff exists to fix, left open in the sibling branch; no test notices | `python/src/dotfiles_setup/claude_doctor.py:420`, `:436-448` |
| M2 | MEDIUM | `_VERSION_RE`'s prerelease/build suffix branch matches 0/100 real releases and is the only remaining path admitting a non-release token to `enforcement_eligible=True`; entirely untested | `python/src/dotfiles_setup/claude_doctor.py:86` |
| M3 | MEDIUM | The sole test pinning the merged `_run` default asserts a stream split the real `claude doctor` never produces (re-measured: 0 bytes to stderr) | `tests/test_claude_doctor.py:271-292` |
| M4 | MEDIUM | Finding ORDER in the `INVALID` path changed (clean-marker moved from last to second) and is wholly unasserted — a full inversion leaves 41/41 green | `python/src/dotfiles_setup/claude_doctor.py:355-360`, `:450-457` |
| L1 | LOW | The new boundary stub monkeypatches PROCESS-GLOBAL `shutil.which` and `subprocess.run`, departing from the file's module-local `setattr(claude_doctor, "_run", …)` convention | `tests/test_claude_doctor.py:142-143` |
| L2 | LOW | Findings are bounded at 200 chars but `running_version` flows into `to_json()` untruncated; the new `bounded-value` case asserts exactly that asymmetry | `python/src/dotfiles_setup/claude_doctor.py:423`, `:429`; `tests/test_claude_doctor.py:348` |
| L3 | LOW | The "shape is the question" doctrine is applied to `\n` but not to spaces/tabs: `version` is `.strip(" \t")` while `method` is still full `.strip()` | `python/src/dotfiles_setup/claude_doctor.py:249-253` |
| L4 | LOW | On oracle failure the 200-char budget is spent on merged `stdout+stderr`, so a chatty stdout can truncate the stderr reason away; the success path got a dedicated `stderr_reason`, the failure path did not | `python/src/dotfiles_setup/claude_doctor.py:312-314` |
| L5 | LOW | No `suites.toml` / `hk.pkl` contract binds `claude_doctor.py` (control-armed), so nothing outside this one test file guards any of the above | `python/verification/suites.toml`, `hk.pkl` |

### What round 1 closed (verified, not inherited)

Both headline holes from `cold-review-doctor-oracle-2026-09-18.md` are now armed:

- flipping `stdout_only`'s **default** to `True` → **1 failed** (was 35/35 green
  in r1): `test_claude_doctor_is_read_across_stdout_and_stderr`.
- the reasonless empty-oracle string now carries stderr, and removing it →
  **1 failed**: `test_empty_oracle_stdout_is_unknown_even_when_stderr_has_text`.
- the shape doctrine is now applied to BOTH operands (`running` as well as the
  oracle), which is r1's finding #3.

## Mutation table

Every row run on the scratch copy; `cp` restore between rows; baseline 41/41.

| # | Mutation | Result | Reads as |
|---|---|---|---|
| M1 | `stdout_only: bool = False` → `True` (the DEFAULT) | 1 failed | teeth |
| M2 | drop `stdout_only=True` at the oracle call site | 3 failed | teeth |
| M3 | `if done.returncode == 0 and stdout_only:` → `if stdout_only:` | 1 failed | teeth |
| M4 | delete the `_VERSION_RE.fullmatch(running)` block in `evaluate` | 5 failed | teeth |
| M5 | UNKNOWN branch drops `findings.extend(installation_findings)` | 2 failed | teeth |
| M6 | `.strip(" \t")` → `.strip()` in `parse_doctor` | 1 failed | teeth |
| M7 | delete the `_VERSION_RE.fullmatch(version)` block in `latest_version` | 1 failed | teeth |
| M8 | delete `stderr_reason` | 1 failed | teeth |
| **M9** | **ADD `*installation_findings` to the oracle-failure UNKNOWN branch** | **41 passed** | **blind → M1 finding** |
| M10 | move the clean-marker finding out of `_installation_findings` back to HEAD's position | 1 failed | teeth (via the UNKNOWN case only) |
| **M11** | **`_VERSION_RE` loses `(?:[-+][0-9A-Za-z.-]+)?`** | **41 passed** | **blind → M2 finding** |
| M12 | `_VERSION_RE` → `(?s).+` | 6 failed | teeth |
| **M13** | **INVALID-path finding order fully inverted (installation findings last)** | **41 passed** | **blind → M4 finding** |

## Evidence per finding

### H1 — an unreadable running token now suppresses the repo-pin finding (HIGH)

`evaluate` short-circuits to `UNKNOWN` at `claude_doctor.py:422` **before**
calling `latest_version`. `pin_currency_findings` needs `latest`, so it is never
reached. But the pin question — "does `schemas/sources.toml` still pin the newest
claude-code?" — is a statement about a tracked file and has **zero** dependence on
what the host's `claude` reports. The module's own docstring says so
(`claude_doctor.py:386-389`: "the two have different subjects … that one is about
a tracked file").

Armed, HEAD vs staged, identical stub (`Running: native (unknown)`, oracle
`99.99.99`, real `project_root`, `check_pin=True`):

```
[HEAD]   verdict=invalid eligible=True
   - claude on PATH is unknown but 99.99.99 is published (install method: native)...
   - schemas/sources.toml pins claude-code at 2.1.273 but 99.99.99 is published...
[STAGED] verdict=unknown  eligible=False
   - `claude doctor` returned a non-version running value: 'unknown'
```

Two consequences, both silent:

1. `enforcement_eligible` flips `True` → `False`. The `classic.PreToolUse`
   handler at `.claude/skills/claude-doctor/hooks/register.ts` denies on
   `verdict === "invalid"` alone, so this state stops enforcing. That half may be
   deliberate (it is the diff's stated doctrine), but it is the definition of
   "a previously-enforcing state has become non-enforcing" and should be an
   explicit decision, not a side effect of where the short-circuit landed.
2. The pin finding **disappears entirely** — it is not downgraded to advisory,
   it is absent from `findings`, so neither the SessionStart `additionalContext`
   nor `doctor.check_claude_doctor` (`doctor.py:1268`, `return
   list(verdict.findings)`) can show it.

This is live, not hypothetical: the repo pins `claude-code = 2.1.273`
(`schemas/sources.toml`) while the host's `claude doctor` reports `2.1.277`, so
the pin finding fires today. Any upstream reword of the version token inside
`Running: … (…)` now takes a currently-firing finding off the board.

### H2 — the staged test blob did not typecheck (HIGH — RESOLVED mid-review)

**As first resolved**, `git show :tests/test_claude_doctor.py` line 88 was
`) -> Callable[..., tuple[int, str]]:` while the inner `run` it returns was
changed by this same diff to `-> tuple[int, str, str]` (staged line 96).

```
$ uv run --project python ty check <scratch>/tests/test_claude_doctor.py
error[invalid-return-type]: Return type does not match returned value
Found 1 diagnostic
rc=1
```

The repo bans inline suppressions (`no_lint_skip`, `zero-skip-policy.md`), so
that was a hard gate failure on the staged ref. At the time it was an UNSTAGED
working-tree edit (`git status` showed `MM`), i.e. the fix existed but was not in
the reviewed ref.

**Re-checked at the end of the review — it has since been staged.** The index
blob now reads `) -> Callable[..., tuple[int, str, str]]:` and both staged files
are clean:

```
$ uv run --project python ty check <scratch>/tests/test_claude_doctor.py   -> All checks passed! rc=0
$ uv run --project python ty check <scratch>/.../claude_doctor.py          -> All checks passed! rc=0
```

Recorded rather than deleted because it is the reason the review's runtime
harness and the reviewed ref briefly disagreed (see the harness caveat above),
and because it is the one finding whose fix arrived from outside this review.
No action outstanding.

### M1 — the oracle-failure branch discards findings it just computed (MEDIUM)

`installation_findings` is computed at `claude_doctor.py:420`, consumed by the
non-version branch at `:426`, and then **ignored** by the branch at `:436-448`,
which builds `findings=[…one message…]` from scratch.

Armed (wrong method + missing clean marker + failing oracle):

```
verdict=unknown eligible=False
  - cannot determine latest version, so currency is unknown (NOT 'current'): ...
```

The `npm-global`-not-`native` fact and the missing clean marker are both
established, both independent of the oracle, and both dropped. M9 (adding
`*installation_findings` there) leaves **41/41 green**, so nothing would notice
either way.

Not a regression against HEAD — HEAD masked them too. It is the diff's own
doctrine (`_installation_findings.__doc__`: "a known-wrong method or missing
clean marker still deserves an operator-visible finding") applied to one of the
two UNKNOWN branches, and the one left out is the far more common one (network,
mise, rate-limit).

The same gap exists one branch earlier: the `running is None` parse-failure
return at `:407-418` also drops the clean-marker finding, which is knowable
there (`clean` is already computed and is passed to `clean_marker_present`).

### M2 — the suffix branch is untested widening that re-opens enforcement (MEDIUM)

`_VERSION_RE` (`claude_doctor.py:86`) is
`[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?`.

Corpus arm, re-derived this session (not inherited — `mise ls-remote
github:anthropics/claude-code`, rc=0, control `github:junegunn/fzf` rc=0/86
tags):

```
tags: 100
bare 3-component fullmatch: 100
with-suffix  fullmatch    : 100
tags needing the suffix branch: []
tags matching neither:          []
```

**0 of 100 published releases require the suffix branch.** M11 (deleting it)
leaves 41/41 green, so no test requires it either. What it does buy is the
opposite of the diff's stated doctrine — it lets a local/dev build through as a
"version":

```
Running: native (2.1.277-dev)     vs latest 2.1.277 -> INVALID, eligible=True
Running: native (2.1.277+local.1) vs latest 2.1.277 -> INVALID, eligible=True
```

Both reach `enforcement_eligible=True`, i.e. the `classic.PreToolUse` hook
denies every non-repair tool call with "claude on PATH is 2.1.277-dev but
2.1.277 is published". The diff closes the bare `dev` / `unknown` shapes
(tested) and leaves the `<version>-dev` / `<version>+local` shapes — the ones a
real local build actually produces — as the only remaining route into the deny.
If that is intended, it deserves a test and a comment; today the comment at
`:83-85` says the opposite ("a line that does not have this shape is an
unanswered question, never a version") while the regex hands the suffix a pass.

### M3 — the default-pinning test rests on a counterfactual fixture (MEDIUM)

`test_claude_doctor_is_read_across_stdout_and_stderr`
(`tests/test_claude_doctor.py:271-292`) puts `Running: native (2.1.270)` on
**stderr** and asserts `Verdict.OK`. It is the only test that fails under M1, so
it alone pins `stdout_only`'s merged default.

Re-measured this session:

```
$ claude doctor > out 2> err ; rc=0
stdout bytes: 655   stderr bytes: 0
out:Running: native (2.1.277)
```

The real command writes **0 bytes** to stderr and the `Running:` line to stdout.
So the "process-boundary contract" the docstring claims is pinned has no
production referent: the merged default is now locked in by a test describing a
world that does not exist, and a future change to `stdout_only=True` — which
would be correct for the real tool — fails a test with no production
counterpart. Per `probes-need-a-control-arm.md` #8, the fixture admits only one
answer by construction.

### M4 — finding order changed silently (MEDIUM)

HEAD order in the `INVALID` path was: method → version-mismatch → pin-currency →
clean-marker. The diff moves the clean-marker finding into
`_installation_findings` (`:355-360`), so the order is now: method →
clean-marker → version-mismatch → pin-currency.

Armed (wrong method + stale version + missing clean marker):

```
[0] claude on PATH is a 'npm-global' install, not the expected 'native'. ...
[1] `claude doctor` did not report 'No installation issues found.' — it found ...
[2] claude on PATH is 2.1.270 but 2.1.277 is published (install method: npm-global)...
```

M13 inverts the order completely and leaves 41/41 green — nothing asserts it.
The consumer joins all findings with `" "` into one deny/`additionalContext`
string (`register.ts`, `register` handlers), so no finding is lost, but the
lead sentence an operator reads first changed and nothing records the decision.

The whole test file was read to confirm this rather than sampled. Four tests
index `findings[0]` — `tests:412`, `:495`, `:602`, `:692` — and **every one of
them is a single-finding fixture** (current version + clean marker, so only the
method finding exists; or the BLIND / disabled short-circuits, which return
exactly one). None constrains the relative order of two findings.

### L1 — the new stub patches process-global stdlib attributes

`tests/test_claude_doctor.py:142-143` does
`monkeypatch.setattr(claude_doctor.shutil, "which", …)` and
`monkeypatch.setattr(claude_doctor.subprocess, "run", …)`. Verified:

```
claude_doctor.subprocess is subprocess -> True
claude_doctor.shutil    is shutil     -> True
```

So both rebind the stdlib module attribute for every module in the process for
the duration of the test. `monkeypatch` undoes it at teardown, so the blast
radius is one test, but the rest of this file uses the module-local
`monkeypatch.setattr(claude_doctor, "_run", …)` convention precisely to avoid
that. Testing through the real `_run` is the right call; binding it to
`claude_doctor`-local indirections (or `subprocess.run` via a module-level
seam) would get the same coverage without the global.

### L2 — bounded findings, unbounded `running_version`

`claude_doctor.py:423` truncates the finding to `running[:200]`, and
`:429` sets `running_version=running` with no bound. `to_json()` serialises the
field, and `register.ts` `readVerdict` `JSON.parse`s the whole payload. The new
`bounded-value` parametrisation asserts both halves of the asymmetry in one
test: `result.running_version == running` (the full 250+ char blob,
`tests:348`) alongside `all("OMITTED" not in finding …)` (`tests:353`). If the
truncation exists because upstream text is untrusted, the field is the larger
hole. Pre-existing on the other return paths; the diff adds one more.

### L3 — the strip doctrine is half-applied

`parse_doctor` now uses `match["version"].strip(" \t")` (`:251`) so a captured
newline survives and fails `fullmatch` → `UNKNOWN`
(`test_running_version_shape_rejects_a_trailing_newline`, M6 red). But leading
and trailing spaces/tabs are still silently normalised, and `method` is still
full `.strip()` (`:252`). `Running: native (   2.1.277   )` is accepted as a
version; `Running: native (\n2.1.277\n)` is not. The line between "framing" and
"content" is drawn at whitespace class rather than at a stated rule. The
direction is monotone (strictly more `UNKNOWN`), so nothing becomes enforcing
that was not before.

### L4 — the failure path has no dedicated stderr budget

`claude_doctor.py:312`: `f"version oracle failed (rc={rc}): {out.strip()[:200]}"`
where `out` is `stdout + stderr` merged. The success path got a dedicated
`stderr_reason` (`:314`) precisely so an empty answer keeps its reason; the
failure path did not, so a command that fails *after* writing 200+ chars to
stdout truncates its own stderr reason away.
`test_oracle_stderr_is_diagnostic_on_success_and_reason_on_failure` uses an
empty stdout, so this arm is unexercised.

### L5 — no contract binds this module

`grep -c claude_doctor python/verification/suites.toml hk.pkl` → `0`, `0`.
Control: `PLANNING_DISABLED=1` → 7 in the same file with the same command shape;
fresh known-absent arm `qhx7vv2wnb` → 0. The only `claude-doctor` matches in
`suites.toml:2773,2779` are the fnhook `register.ts` surface, not this module.
So every finding above is guarded by `tests/test_claude_doctor.py` alone.

Related: `pin-parity.toml:87-88` exempts this test file's version fixtures in
**description prose**, not a machine `sites` entry. The diff adds six new
`2.1.277` literals (`tests:201,205,258,268,365,370`); nothing enforces or
forbids them either way.

## Tests that pass for the wrong reason / would survive a revert

- None found that pass on a full revert — the control arm is 26 failed / 15
  passed, and every asserted claim in the diff has a red mutation (M1–M8, M10,
  M12).
- Three behaviours are asserted by **nothing**: M9 (oracle-failure branch's
  finding set), M11 (the suffix branch), M13 (finding order).
- `_fake_run` (`tests:83-103`) `del`s `stdout_only` and always returns
  `stderr=""`, so no `_fake_run`-based test can observe the split. That is fine
  now only because `_stub_process_boundary` covers the real boundary; if the
  five `_stub_process_boundary` tests were ever removed, the entire feature
  would go untested while 30+ tests stayed green.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — release
  tag corpus enumerated via `mise ls-remote github:anthropics/claude-code` to arm
  `_VERSION_RE` (100 tags), and `claude doctor` run locally to measure its
  stdout/stderr split.
- [junegunn/fzf](https://github.com/junegunn/fzf) — control arm for the
  `mise ls-remote` probe (86 tags, rc=0), proving the 0-tag first attempt was a
  broken `timeout` shim rather than an empty corpus.
