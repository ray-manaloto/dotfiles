# Cold review R3 (FINAL) — staged `claude_doctor` oracle/stdout diff

- **Ref reviewed**: the STAGED diff against HEAD
  `ebaf702b0b49a3d67f3d39b36bb1532320fabf21`
  (`git diff --cached HEAD -- python/src/dotfiles_setup/claude_doctor.py tests/test_claude_doctor.py`),
  195 +/- in the module, 359 +/- in the test file.
- **Date**: 2026-09-18. Round 3, final.
- **Staged == worktree** for both files, checked at the start AND at the end of
  the review (`diff <(git show :<path>) <path>` → identical; `git status --short`
  → `M ` both times, no second-agent edit landed mid-review).
- **Graphify**: `mise run graphify-health` → `stale (built at ff2fbaf7, HEAD is
  ebaf702b, 6 commits behind)`. Per `.claude/rules/graphify-first.md` the graph
  is unavailable, so every claim below is grounded in source, not the graph.
- Memory (`memory: local`) consulted: `stream_split_and_oracle_review.md`,
  `repo_gate_locations.md`, `mutation_harness.md`.

## Verdict: **SHIP**

No blocking finding. The diff fixes a live, reproduced false positive that is
currently arming a PreToolUse DENY on this host, it never manufactures a new
deny in any of 240 cross-product cells, every one of its thirteen production
changes is guarded by at least one test, and `ty` / `ruff check` /
`ruff format --check` are clean on the staged blobs.

Eight findings follow; all are MEDIUM or LOW and all are follow-up-issue
material, not ship blockers.

## Live arm — the bug this diff fixes, both directions, on this host

`evaluate(project_root=<repo>)` with a real captured ambient `PATH`, HEAD module
versus staged module, run minutes apart against the same live `claude doctor`
and `mise latest`:

| | verdict | `enforcement_eligible` | `latest_version` | findings |
|---|---|---|---|---|
| **HEAD** | `invalid` | **True** | `'mise WARN  deprecated [python.uv_venv_auto.true]: …'` | 2 — one false (`claude on PATH is 2.1.277 but <the warning> is published`), one true-but-garbled (pin `2.1.273` vs `<the warning>`) |
| **STAGED** | `invalid` | True | `'2.1.277'` | 1 — the genuine one: `schemas/sources.toml pins claude-code at 2.1.273 but 2.1.277 is published` |

mise's `python.uv_venv_auto` deprecation warning lands on stderr; HEAD merged
the streams and took `splitlines()[-1]`, so the warning *became* the published
version. `register.ts` joins every finding into its deny string
(`.claude/skills/claude-doctor/hooks/register.ts:222-226`), so HEAD was denying
tool calls with a mise warning quoted as a version number. Staged removes the
false finding, repairs the true one, and preserves the real enforcement (the
repo pin genuinely is stale — `schemas/sources.toml:51` is `2.1.273`).

## HEAD-vs-STAGED behaviour table

240 cells = running {valid&==latest, valid&!=latest, non-version text,
unparseable `Running:` line} × oracle {valid, rc!=0, rc=0 empty stdout, rc=0
non-version stdout, valid stdout + noisy stderr} × method {expected,
unexpected} × clean marker {present, absent} × pin {current, behind,
`check_pin=False`}. Both modules driven through the same `shutil.which` /
`subprocess.run` stub; 0 exceptions either side.

**Fixture arms** (rule 8 — could the setup have produced the other answer?):
the first run of this matrix used the wrong `sources.toml` schema and produced
**0** pin findings on both sides; corrected to the real `[[schema]]` shape it
produces 24 staged / 60 HEAD. Method findings 90/54, clean findings 120/54,
non-version-running findings 24/0. All five axes are live.

| head → staged | cells | what it means |
|---|---|---|
| identical | 72 | — |
| `invalid` → `invalid` (findings differ) | 42 | content/ordering fixes, enforcement unchanged |
| `invalid` → `unknown` | 40 | **false positives removed** (see below) |
| `invalid` → `ok` | 2 | **false positive removed** — the live case above |
| `unknown` → `unknown` (findings differ) | 84 | established failures now *named* under UNKNOWN |
| anything → **newly** `invalid` | **0** | the diff never adds enforcement anywhere |

### The 40 `invalid` → `unknown` cells, grouped

| running | oracle | cells | HEAD's finding | why it was false |
|---|---|---|---|---|
| valid-eq | non-version stdout | 12 | `claude on PATH is 2.1.277 but mise WARN something is published` | compared against garbage |
| valid-ne | non-version stdout | 12 | same shape | compared against garbage |
| non-version | non-version stdout | 12 | same shape | both operands garbage |
| non-version | valid | 2 | `claude on PATH is 2.1.277-dev but 2.1.277 is published` | deliberate softening, see F-note below |
| non-version | noisy stderr | 2 | same | both causes at once |

All 40 are false-positive removals. The only judgement call is the
`2.1.277-dev` class: HEAD enforced "you are behind"; staged calls the token
unreadable and returns UNKNOWN. That is the R2 escape-hatch decision (0 of 100
real tags carry a suffix, re-derived), and it is now pinned by
`tests/test_claude_doctor.py:372`. It *removes* enforcement on a local dev
build — correct per the module's "never block on a fact that was never
established" doctrine, and a non-native dev build still enforces through the
method finding.

### The 84 `unknown` → `unknown` cells

| cells | HEAD findings | STAGED findings |
|---|---|---|
| 30 | `could not parse` | `could not parse`, **`installation issues`** |
| 18 | `cannot determine latest` | + **`installation issues`** |
| 18 | `cannot determine latest` | + **`not the expected`** |
| 18 | `cannot determine latest` | + **`not the expected`**, **`installation issues`** |

Pure gain in diagnosis — `register.ts:198-202` renders UNKNOWN findings at
SessionStart, so the operator now learns "and also, your install method is
`npm-global`" instead of only "could not determine". Enforcement unchanged.

### Finding order

Order is identical to HEAD in every cell: **method → version/non-version → pin
→ clean**, and it is now asserted by
`tests/test_claude_doctor.py:830` (`test_findings_keep_head_order_…`). The R2
gap (order inversion left everything green) is closed.

## Findings

| # | Sev | Claim | file:line |
|---|---|---|---|
| F1 | MEDIUM | `to_json`'s new bounding docstring overclaims: a *version-shaped* `running` token is never truncated, so a 5,000-char one bypasses BOTH the 200-char finding budget and the new JSON budget at `enforcement_eligible=True` | `python/src/dotfiles_setup/claude_doctor.py:170-179` (claim), `:462-466` (unbounded finding), `:174-178` (guard that misses it) |
| F2 | MEDIUM | `install_method` — the other half of the same malformed `Running:` line — is bounded nowhere: untruncated in the method finding and in the JSON, at `enforcement_eligible=True`; both proving mutations are the FIX and left 45/45 green | `python/src/dotfiles_setup/claude_doctor.py:356-359`, `:185` |
| F3 | MEDIUM | Doctrine asymmetry: the new docstring promises an established method/pin/clean failure "remains INVALID rather than being silently masked", but the sibling oracle-failure branch masks exactly those failures into UNKNOWN | `python/src/dotfiles_setup/claude_doctor.py:392-396` (doctrine) vs `:438-453` (branch) |
| F4 | LOW | Same asymmetry in the parse-failure branch: a clean-marker assertion that was made and failed is reported under UNKNOWN there, INVALID 40 lines below | `python/src/dotfiles_setup/claude_doctor.py:428-433` vs `:469` |
| F5 | LOW | The sole guard on `stdout_only`'s default is a counterfactual fixture — it puts `Running:` on a stream the real command leaves empty | `tests/test_claude_doctor.py:271-297`; tool re-measured 655 B stdout / 0 B stderr |
| F6 | LOW | `_VERSION_RE` carries no anchors; it is safe only because all three call sites use `fullmatch`. A later `.search()`/`.match()` silently becomes a substring test | `python/src/dotfiles_setup/claude_doctor.py:86`, call sites `:177`, `:330`, `:456` |
| F7 | LOW | `latest_version`'s docstring documents only `force_refresh`; the new "rc=0 but non-version stdout → `(None, reason)`" contract is undocumented at the function a caller reads | `python/src/dotfiles_setup/claude_doctor.py:313-317` |
| F8 | LOW | `.strip()` → `.strip(" \t")` also makes a bare `\r` inside the parens unreadable (HEAD `ok` → staged `unknown`); fail-safe direction, no real output produces it | `python/src/dotfiles_setup/claude_doctor.py:264` |
| F9 | LOW (pre-existing, unchanged file) | `check_claude_doctor`'s docstring says "Only INVALID is reported as a finding here" while the body returns findings for every verdict — this diff adds findings to three UNKNOWN paths, so the stale sentence now misdescribes more surface | `python/src/dotfiles_setup/doctor.py:1246-1250` vs `:1268` |

### F1/F2 — measured, with a control arm

Same stub, staged module, `check_pin=False`:

| probe | verdict | `len(findings[0])` | `len(json[<field>])` |
|---|---|---|---|
| P1 `Running: <5000-char method> (2.1.277)` | `invalid`, eligible | **5,428** | `install_method` **5,001** |
| P2 `Running: native (<5000 digits>.0.0)` | `invalid`, eligible | **5,102** | `running_version` **5,004** |
| P3 **control** `Running: native (<5000 'd's>)` | `unknown` | **256** | `running_version` **200** |

P3 is the arm that proves the new truncation works; P1 and P2 are the two paths
it does not cover — and they are precisely the two that reach
`enforcement_eligible=True`, i.e. the deny string at
`.claude/skills/claude-doctor/hooks/register.ts:222-226`. HEAD is equally
unbounded on all three (5,001 / 5,004 / 5,000), so this is **not a regression**
— it is a *new claim* the diff makes and only partly delivers. Not a DoS: the
text is local `claude doctor` stdout, and both regexes are linear (200k-char
control: `_VERSION_RE` 0.0004 s, `_RUNNING_RE` 0.0032 s).

Suggested fix, one line each: `{running[:200]}` at `:463` and `{(method or '')[:200]!r}`
at `:357`, plus `install_method` bounded in `to_json`.

### F3 — the branch where the doctrine is not applied

`evaluate`'s new paragraph (`:392-396`) says an unanswerable currency question
must not mask an established failure. The non-version-token branch honours it.
The oracle-failure branch, where the currency question is unanswerable for a
*different* reason, does not: 18 matrix cells
(`valid-*|rc-nonzero|unexpected|*`) return `verdict=unknown`,
`enforcement_eligible=False` while `findings[1]` names a real `npm-global`
shadow install. So a genuine shadowing install goes unenforced whenever the
network is down.

This is a **deliberate, pinned** choice, not an oversight: mutation M13 (make
that branch INVALID when method/clean failed) fails exactly one test —
`tests/test_claude_doctor.py:491` — which asserts
`enforcement_eligible is False` there. HEAD did not enforce there either, so
nothing regressed. The finding is that the docstring states a general rule the
code applies to one of two structurally identical situations; either narrow the
docstring to the version-token case or extend the rule. Follow-up issue.

## Mutation sweep — is every production change guarded?

Scratch harness (`cp -R python` + `git show :tests/…` into the scratchpad; the
test's own `sys.path.insert` makes the scratch copy the one that imports;
nothing in the repo touched). Baseline **45 passed**. Control arm: full
production revert to HEAD → **29 failed / 16 passed**, so the harness
discriminates.

| mutation | result | test that caught it |
|---|---|---|
| M1 drop oracle shape guard | 1 failed | `test_non_version_oracle_stdout_is_unknown_never_invalid:235` |
| M2 drop `stdout_only=True` at the oracle call site | 3 failed | `:194`, `:213`, `:392` |
| M3 flip `stdout_only` default to `True` | 1 failed | `test_claude_doctor_is_read_across_stdout_and_stderr:271` |
| M4 drop `stderr_reason` | 1 failed | `:213` |
| M5 restore `splitlines()[-1]` | 1 failed | `:235` |
| M6 restore full `.strip()` | 1 failed | `test_running_version_shape_rejects_a_trailing_newline:254` |
| M7 drop `to_json` truncation | 1 failed | `:337[bounded-value]` |
| M8 drop clean-marker in the parse-fail branch | 1 failed | `test_reworded_output_is_unknown_not_a_silent_pass:477` |
| M9 drop known facts in the oracle-fail branch | 1 failed | `test_an_oracle_failure_is_unknown_never_current:491` |
| M10 revert the running-shape branch | 7 failed | `:337` ×4, `:372`, `:786`, `:808` |
| M11 drop the UNKNOWN verdict arm | 5 failed | `:254`, `:337` ×2, `:372`, `:808` |
| M12 `failed_assertion = bool(findings)` | 5 failed | same five |
| M13 make oracle-fail INVALID when method failed | 1 failed | `:491` (pins the F3 choice) |
| **M14 bound `install_method` in JSON** (the FIX) | **45 passed** | **nothing guards either choice** |
| **M15 truncate `method` in the finding** (the FIX) | **45 passed** | **nothing guards either choice** |

M1–M13: every production change is guarded. M14/M15 are the F1/F2 evidence —
applying the doctrine leaves the suite green, so the omission is unrecorded.

## Tests that would still pass if the production change were reverted

2 of the 11 new tests, and neither is a defect:

- `test_claude_doctor_is_read_across_stdout_and_stderr:271` — characterises the
  *unchanged* merged default; it passes at HEAD because HEAD always merged.
  M3 shows it is the only guard on that default. See F5 for its fixture.
- `test_findings_keep_head_order_method_version_pin_then_clean:830` — asserts
  order is preserved, so passing at HEAD is the point.

The other 9 all fail against the reverted module.

## Tests passing for the wrong reason

None found. One convention deviation worth naming:
`_stub_process_boundary` monkeypatches `claude_doctor.shutil` /
`claude_doctor.subprocess` (`tests/test_claude_doctor.py:142-143`), which are
the real stdlib module objects (`claude_doctor.shutil is shutil` → `True`), not
this file's `setattr(claude_doctor, "_run", …)` convention. It is acceptable
here — the stub's `assert command in scripted` turns any stray subprocess call
into a loud failure rather than a silent hijack, and `monkeypatch` undoes it —
but it reaches one layer deeper than the rest of the file and should stay
deliberate. The older `_fake_run` stub was correctly widened to the 3-tuple
signature with `del extra_env, stdout_only` (`:83-105`), so a caller passing
the new kwarg cannot pass for the wrong reason.

## Callers of any changed signature, repo-wide

`_run` is the only changed signature (`(int, str)` → `(int, str, str)` plus
`stdout_only`). Repo-wide grep over `*.py`/`*.ts`/`*.toml`/`*.pkl`/`*.json`:
**no caller outside the module and its test**. The three other `_run` symbols
(`sync.py:376`, `graphify.py:378`, `skillopt_provenance.py:233`) are unrelated
module-private functions. Both in-module call sites are updated
(`:318` oracle, `:412` doctor).

Public surface is unchanged, so all three consumers are unaffected:

- `python/src/dotfiles_setup/doctor.py:1262` — `evaluate(expected_method=…)`,
  advisory; sees more findings on UNKNOWN paths (see F9).
- `python/src/dotfiles_setup/main.py:2854` — `claude_doctor_main(…, project_root=project_root)`.
- `.claude/skills/claude-doctor/hooks/register.ts:71` — reads the JSON; keys
  and types unchanged (`verdict`, `enforcement_eligible`, `findings`).

## Gates

| gate | result |
|---|---|
| `uv run --project python pytest tests/test_claude_doctor.py -x -q` (in-repo) | **rc=0, 45 passed** |
| `uv run --project python ty check` on both staged files | **rc=0, All checks passed** — the R2 `invalid-return-type` on the stale `Callable[..., tuple[int, str]]` annotation is fixed (`tests/test_claude_doctor.py:88`) |
| `uv run --project python ruff check` | rc=0 |
| `uv run --project python ruff format --check` | 2 files already formatted |

Not run by design (another agent owns them, shared checkout): `mise run lint`,
the full pytest suite, `mise run verify`.

**Gate blindness, unchanged from R2 and re-confirmed**: no `suites.toml` suite
and no `hk.pkl` step binds `claude_doctor.py` (`grep -c claude_doctor` → 0 in
both; control `PLANNING_DISABLED=1` → 7). `tests/test_claude_doctor.py` is the
entire gate for this module.

## Follow-up issues to file (none blocking)

1. Bound `running_version` and `install_method` on the enforcing path, and
   either fix or narrow `to_json`'s docstring claim (F1 + F2).
2. Resolve the oracle-failure-branch doctrine asymmetry — extend the rule or
   narrow the docstring (F3 + F4).
3. Replace or supplement the counterfactual `stdout_only` default guard (F5).
4. Docstring/anchoring tidy-ups (F6 + F7) and the stale `check_claude_doctor`
   docstring (F9).
5. Separately, and visible from the live arm: `schemas/sources.toml` pins
   `claude-code` at `2.1.273` while `2.1.277` is published, so this check is
   INVALID on this host for a genuine reason. That is the check working, not a
   diff defect.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the
  `github:anthropics/claude-code` release tag set is the version oracle whose
  three-component shape `_VERSION_RE` encodes; its `claude doctor` output is
  the parsed text.
- [jdx/mise](https://github.com/jdx/mise) — `mise latest` is the oracle
  subprocess, and its `python.uv_venv_auto` stderr deprecation warning is the
  live input that produced the false INVALID this diff fixes.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the
  repository under review.
