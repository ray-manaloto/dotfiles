# SPEC: part (2) only. sdlc-team implement mode refuses a spec that is not committed under `docs/specs/`

Status: REVISED DRAFT by `spec-scribe`, 2026-10-04 (04h), applying the premise-verifier report
`docs/research/kb/reports/agents/premise-verifier-jobdir-part2.md` (in the 04h worktree) to the
04d draft `handoff-2026-10-04e/docs/research/kb/raw/specs-2026-10-04d/spec-jobdir-part2-dispatch-gate.md`.
NOT ratified, NOT dispatched. It is extracted from the ratified parent spec
`HW/docs/research/kb/raw/specs-2026-10-04d/spec-jobdir-preservation.md` (§3.8, §5.1 S1-S4,
§5.2 M8-M9, §R). Every `file:line` in §7 was re-read in this run, in the 04h worktree, a
checkout of `13af2848`. §8 lists the choices the architect still has to make. Stop there for
ratification.

Memory: the spec-scribe local memory directory was empty at the start of this run, so no
prior convention was applied.

## Revision log (04h)

Report letters and numbers refer to the premise-verifier report's VERDICT list (1-4), its
"Non-blocking residuals" list, its MISSING list, and its ROWS.

| # | Correction (report item) | Kind | Where applied |
|---|---|---|---|
| R1 | VERDICT 1: S5 safety. S5 must patch `sdlc_team.subprocess.Popen` with the F1 git-passthrough raising fake, and `shutil.which`, so M8 cannot launch a real supervisor or codex. Generalised as a class rule: **no §5.1 arm that calls `dispatch` may reach a real launcher** | blocking | §5.1 preamble ("Boundary rule"), §5.1 S5, §5.2 M8 row, §7 rows 45-46 |
| R2 | VERDICT 2: rows 1-3 and the provenance caveat. Base is `13af2848` (local main = origin/main). The "unpulled main" narrative is dropped | blocking | "Provenance" paragraph (replaces the old caveat), §7 rows 1-3 |
| R3 | VERDICT 2: the #1662 paragraph and U3. #1662 is in the base, so the "+4/+5" caveat is fact, not forecast. Cut from `13af2848` or later | blocking | "Provenance" paragraph, §2, §8 U3 (closed), §7 rows 4-8 |
| R4 | VERDICT 2: row 17. argv `:811-828`, try/except `:830-878` | blocking | §7 row 17 |
| R5 | VERDICT 2: row 21. Test `:1651-1673`, `sdlc_team_main` `:1093-1110` | blocking | §7 row 21 |
| R6 | VERDICT 2: row 23. Test `:1698-1714`, `generate_dispatch_schema` `:1067-1069` | blocking | §7 row 23 |
| R7 | VERDICT 2: row 14 control anchor `:1666` → `:1671` (and the count is now 7, including the `.agents` mirror) | blocking | §7 row 14, §5.3 |
| R8 | VERDICT 2: rows 7-8 restated as anchors at the base | blocking | §7 rows 7-8 |
| R9 | VERDICT 2: row 9 dropped (re-derived). Its number is kept, marked retired, so report cross-references stay valid | blocking | §7 row 9 |
| R10 | VERDICT 3: git env scrub. Every gate git call passes `env=child_env.without_git_context()`, precedent `pr.py:244` | blocking | §2 (sdlc_team.py row), §3.2, §7 rows 47-48 |
| R11 | VERDICT 4: capture types. Checks 1, 3 and 5 use `text=True`; check 4 alone captures bytes | blocking | §3.2, §7 row 49 |
| R12 | Residual: row 6, the PR number is unverified. It has no effect on code | residual | §7 row 6, §8 "Residuals on the record" |
| R13 | Residual: rows 43-44 are settled by the design and by the equality test | residual | §7 rows 43-44, §8 residuals |
| R14 | Residual: the d921a3f6-vs-base relation is unverified. The coordinator runs `git merge-base --is-ancestor d921a3f6 13af2848` before cutting | residual | "Provenance" paragraph, §7 row 5, §8 residuals |
| R15 | Residual: `.gitattributes`. There is none today; a future eol rule fails closed | residual | §4 "Fail closed", §7 row 50, §8 residuals |
| R16 | Residual (MISSING): the skill example request becomes a refused shape. Applied conditionally on U1 | residual | §2 (SKILL.md row), §3.7, §5.1 S4, §7 row 51 |
| R17 | MISSING: S2.9 setup order. `_committed_spec` runs before PATH is emptied | residual (applied) | §5.1 S2.9 |
| R18 | MISSING: M9 does not make S2.1 fail. Recorded as expected survival | residual (applied) | §5.2 M9 row |
| R19 | MISSING: every other `Popen`-patching test is review mode, so F1 need not touch them | residual (recorded) | §4 "Unchanged behaviour", §7 row 52 |
| R20 | NEW (this run): the `python/AGENTS.md` "models are generated, never hand-written" doctrine vs. this module's hand-written model → schema direction | new premise, non-blocking | §7 row 53, §8 U6 |
| R21 | NEW (this run): the row-35 probe now also hits `GATED_IMPLEMENTATION` in `tests/test_workflows_js.py` (a substring). The sdlc conclusion is unchanged | anchor refresh | §7 row 35 |
| R22 | U5 (premise-verifier) closed: the verifier ran, and this revision applies its report | status | §8 U5 |
| R23 | NEW (this run, negative finding): the hk token-uniqueness gate that breaks the sibling dag-tick spec does not reach this change. No `per_path_tokens` binds any §2 file | control | §7 row 55 |

**Provenance (replaces the 04d "provenance caveat" and "#1662 interaction" paragraphs).**
Base = `13af28480ae4…`. In the main checkout, `.git/HEAD` is `ref: refs/heads/main`, and
`refs/heads/main` and `refs/remotes/origin/main` both read `13af2848…`. The origin/main reflog
records `ee3b29da → 13af2848` as a fast-forward fetch, so `ee3b29da` (the premise-verifier's
baseline) is an ancestor of the base. The 04h worktree, where every anchor here was read, sits
at `13af2848` (§7 rows 1-3). The banner fix's hunk (`"--color", "never"` plus a 2-line comment)
**is in the base** at `sdlc_team.py:819-822` (§7 row 4). Every `sdlc_team.py` anchor at or
after `:819` and every test anchor after about `:409` in §7 is therefore stated as it reads at
the base, and nothing is forecast. That `d921a3f6` is the merged #1662 and an ancestor of the
base is **caller-stated**: no file under `.git/{refs,logs,packed-refs,FETCH_HEAD}` names
`d921a3f6` (control: `ee3b29da` hits 5 files there). It is corroborated by content (row 4), but
before cutting the branch the coordinator runs:

```bash
git -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles merge-base --is-ancestor d921a3f6 13af2848; echo "rc=$?"
```

---

## 1. Objective

**Ratified wording (load-bearing, verbatim).** From Ray's 2026-10-04 ruling as briefed
(parent spec `:50-54`):

> (2) ratified specs must be committed (docs/specs/) before sdlc implementation dispatch

and from §R (parent `:678`):

> **Q7:** ship part (2) first, on its own: the implement-mode dispatch gate requiring a
> committed spec under `docs/specs/`. It touches only `sdlc_team.py`. Parts (1) and (3) follow
> after #1658 and retire-harness-ship merge.

**The failure this prevents.** Today `sdlc-team` in `implement` mode only checks that the
file exists (§7 rows 13, 16). It will happily dispatch from an ignored scratch path. On
2026-10-04 the ratified specs' only copies sat in a coordinator job dir and in `.agent/`
scratch, and both get deleted with the session (parent spec §1, rows 49-51 there; not
re-read here, so this spec does not depend on them). A lane that implements a spec nobody
committed leaves no durable record of what it was told to build.

**Outcome.** `dispatch` in `implement` mode returns a new status, `spec_uncommitted`, and
launches nothing, writes no prompt and calls no `Popen` for the supervisor, **unless** all of
these hold:

- the spec is a file tracked under `<spec's worktree>/docs/specs/`;
- its working-tree bytes equal its blob at that worktree's `HEAD`.

On success the dispatch result carries `spec_commit` (the HEAD sha) and `spec_path` (the
path relative to the repo), and the prompt gains `SPEC COMMIT: <sha> <rel>`. `review` mode
is unchanged and makes no git call, so drafts stay legal there.

## 2. Files

Implementation worktree: `<main>/.claude/worktrees/jobdir-dispatch-gate`, branch
`fix/jobdir-dispatch-gate`, cut from origin/main at `13af2848` or later (R3; #1662 is already
in that base). Never the main checkout. Allowlist (modify only these):

| Path | Change |
|---|---|
| `python/src/dotfiles_setup/sdlc_team.py` | `SPEC_UNCOMMITTED`; two dispatch fields; `_DispatchState` passthrough; `_spec_commit_error`; the gate in `dispatch`; one prompt line (§3); `from dotfiles_setup import child_env` for the git env scrub (R10) |
| `schemas/sdlc-team-dispatch.json` | regenerated from `generate_dispatch_schema()` only (one-off command, §3.6). Never hand-edited |
| `tests/test_sdlc_team.py` | git passthrough in `_capture_dispatch`; a committed-spec helper; the IMPLEMENT cell of `test_no_mode_passes_a_sandbox_or_ephemeral_flag` gets a committed-spec fixture **plus** a `DISPATCHED` assertion (§5.1 T0); new arms S1-S5 |
| `.claude/skills/codex-sdlc-team/SKILL.md` | **pending U1 (recommended: include).** Implement-mode committed-spec requirement; `spec_uncommitted` in the status list; the example request's `spec_file` moved under `docs/specs/` (R16) |
| `.agents/skills/codex-sdlc-team/SKILL.md` | **generated** by bare `mise run skills-mirror` only, and only if U1 is accepted |

**Do not touch:** `schemas/sdlc-team-request.json` and `schemas/sdlc-team-settlement.json`
(their models do not change, so the equality test must keep passing on the committed bytes);
`coordinator_handoff.py`, `session_common.py`, `child_env.py` (imported, not edited), and
everything else that belongs to parts (1) and (3); `.claude/agents/spec-scribe.md` and
`.claude/rules/agent-artifact-conventions.md` (U2); `tests/conftest.py`;
`python/verification/suites.toml`; `.claude/settings.json`; `hook_guard.py`; `python/AGENTS.md`
and `python/pyproject.toml` (U6); anything under `~/.claude/` or `~/.codex/`.

## 3. Interfaces

### 3.1 Enum and models (`sdlc_team.py`)

```python
class SdlcStatus(enum.StrEnum):
    DISPATCHED = "dispatched"
    SPEC_MISSING = "spec_missing"
    SPEC_UNCOMMITTED = "spec_uncommitted"   # new
    CLI_MISSING = "cli_missing"
    INVALID_REQUEST = "invalid_request"

class SdlcTeamDispatch(codec.Struct, frozen=True):
    ...                       # every existing field unchanged, in order
    errors: tuple[str, ...] = ()
    spec_commit: str = ""     # new, appended: HEAD sha of the spec's worktree; implement mode only
    spec_path: str = ""       # new, appended: path of the committed spec relative to the repo; implement mode only

class _DispatchState(codec.Struct, frozen=True):
    ...                       # existing fields unchanged
    spec_commit: str = ""     # new; _resolved_dispatch copies both onto SdlcTeamDispatch
    spec_path: str = ""
```

`SdlcTeamRequest` is **unchanged**, and so is `schemas/sdlc-team-request.json`.

### 3.2 The committed-spec check

```python
_GIT_TIMEOUT_S: Final = 30   # same bound as session_common.MAIN_CHECKOUT_TIMEOUT_S (§7 row 33)

def _spec_commit_error(spec_file: Path) -> tuple[str | None, str, str]:
    """Return (error, commit, rel). error is None only when the spec is committed under docs/specs/."""
```

The checks run in this order, and the first failure returns its error **verbatim** (parent
§3.8, `:326-335`):

1. `git -C <spec_file.parent> rev-parse --show-toplevel` gives `top`. A nonzero exit returns
   `spec is not inside a git work tree`. Use `top = Path(stdout.strip()).resolve()`. On
   macOS `tmp_path` sits under the `/private/var` symlink, so resolve both sides.
2. `rel = spec_file.resolve().relative_to(top)`. `rel.parts` must be at least three long and
   begin with `("docs", "specs")`. This is a **path-component** check, never a string prefix,
   so `docs/specsX/x.md` fails. A `ValueError` or a mismatch returns
   `ratified specs live in docs/specs/`. (No git call.)
3. `git -C top rev-parse --verify --quiet HEAD:<rel>`. A nonzero exit returns
   `spec is not committed at HEAD`. This covers the untracked, staged-only and unborn-HEAD
   cases.
4. Read the blob with `git -C top cat-file blob HEAD:<rel>`, captured as **bytes**. If the
   sha256 of that stdout differs from the sha256 of `spec_file.read_bytes()`, return
   `working tree differs from the committed spec`. A nonzero exit fails closed with the same
   message.
5. `commit = git -C top rev-parse HEAD` (stdout stripped). The function returns
   `(None, commit, rel.as_posix())`.

Every git call uses
`subprocess.run([...], capture_output=True, check=False, timeout=_GIT_TIMEOUT_S, env=child_env.without_git_context())`
with the **literal** program name `"git"` (R10). The scrub is the repository convention for
every production git probe (precedent `pr.py:244`; also `session_state.py:120`,
`doctor.py:1524`, `:1656`, `sync.py:414`, `pr_facts.py:53`): an inherited `GIT_DIR` or
`GIT_WORK_TREE` from a hook or editor overrides `git -C` and would retarget both
`rev-parse --show-toplevel` and `HEAD:<rel>` away from the spec's worktree (`doctor.py:1654-1655`
states the same hazard). The scrub drops only the six `GIT_CONTEXT_NAMES` and `__MISE_DIFF`
(`child_env.py:36-45`, `:71-74`). It keeps `PATH` and `GIT_CONFIG_GLOBAL`/`GIT_CONFIG_NOSYSTEM`, so
S2.9's emptied PATH and conftest's git-config isolation both still reach the child.

**Capture types (R11).** Checks 1, 3 and 5 pass `text=True` (precedent
`session_common.py:186-192`), so `Path(stdout.strip())` in check 1 and the returned sha in
check 5 are `str`. Check 4 alone omits `text=`, so its stdout is `bytes` for the digest.
Passing bytes into `Path` would raise `TypeError`, which escapes the `OSError`/`TimeoutExpired`
catch below. That is why the types are stated rather than left to the implementer.

Never use `shutil.which("git")`: the test boundary fakes `which` to return a codex stub (§7 row
24). An `OSError` (including `FileNotFoundError`) or a `subprocess.TimeoutExpired` returns
`git unavailable: <exception text>`. An `OSError` from reading the spec's bytes does the
same. No exception escapes `_spec_commit_error`.

### 3.3 The gate in `dispatch`

The gate goes after the existing `SPEC_MISSING` return (`sdlc_team.py:741-753`) and before
`_codex_launcher()` (`:755`). That gives the order INVALID_REQUEST, then SPEC_MISSING, then
**SPEC_UNCOMMITTED** (implement only), then CLI_MISSING, then DISPATCHED. In code:
`if request.mode is SdlcMode.IMPLEMENT:` call `_spec_commit_error(spec_file)`. On error, return
`_resolved_dispatch(..., _DispatchState(status=SPEC_UNCOMMITTED, errors=(error,), ...))`
with `pid=None` and `argv=()`. Do this **before** the prompt is written (`:833`), before
`settlement_file.unlink` (`:834`), and before any `Popen` (`:852`).

Every result produced **after** the gate passes carries `spec_commit` and `spec_path`: the
DISPATCHED result (`:880-891`), the post-gate CLI_MISSING result, and the launch-failure
INVALID_REQUEST result at the `except OSError` branch (`:866-878`). In review mode and in every
pre-gate result both stay `""`.

### 3.4 Prompt

```python
def build_prompt(
    request: SdlcTeamRequest, repo_root: Path, *, spec_commit: str = "", spec_path: str = ""
) -> str: ...
```

When `request.mode is SdlcMode.IMPLEMENT` and `spec_commit` is non-empty, emit exactly one
line, `SPEC COMMIT: <spec_commit> <spec_path>`, directly after the `SPEC FILE:` line
(`sdlc_team.py:274`). In every other case the prompt is byte-identical to today's. `dispatch`
passes the two values it got from the gate.

### 3.5 CLI

No change to `sdlc_team_main`. It already returns rc 0 only for `DISPATCHED`
(`sdlc_team.py:1110`), so `spec_uncommitted` exits 1 and prints the typed result (§7 row 21).

### 3.6 Schema regeneration (one-off, §R Q9)

The lane regenerates `schemas/sdlc-team-dispatch.json` once, from the model:

```bash
uv run --project python python -c 'import json, pathlib; from dotfiles_setup import sdlc_team; pathlib.Path("schemas/sdlc-team-dispatch.json").write_text(json.dumps(sdlc_team.generate_dispatch_schema(), indent=2) + "\n")'
```

The committed file is 2-space-indented JSON with a trailing newline (§7 row 22). If the
equality test (row 23) passes but `mise run lint`'s JSON formatter rewrites the file, keep
the formatter's bytes: the test compares parsed JSON, not bytes. Two new `properties`
(`spec_commit`, `spec_path`, both `{"type": "string", "default": ""}`) and the enum value
`spec_uncommitted` are the **only** semantic diff, and `required` stays `["run_id", "status"]`.
A follow-up issue for a `--write-schemas` task is §R-ratified (Q9) and goes to the caller,
not the lane.

### 3.7 Skill text (only if U1 is accepted)

- Next to "`spec_file` must be absolute and exist at dispatch" (§7 row 26), add
  `in implement mode it must be committed under docs/specs/` (a parent §3.9 token, verbatim).
- In the status list (row 27), add
  ``- `spec_uncommitted` — implement mode only; the spec is not a file committed under `docs/specs/` whose working-tree bytes equal `HEAD`; no process launched, `pid` is null and `argv` is empty.``
- **R16:** in the example request (`SKILL.md:37-48`), which uses `"mode": "implement"`, change
  `"spec_file": "/absolute/path/to/spec.md"` to
  `"spec_file": "/absolute/path/to/repo/docs/specs/<name>.md"`. Otherwise the skill's own
  example is a shape the gate refuses. The mirror then regenerates.
- Do not write a capital `Claude` in the new text. The mirror rewrites it (row 29).

## 4. Constraints and invariants

- **Ratified scope only.** Part (2). No job-dir inventory, no cleanup verb, no retire change,
  no `claude rm` guard, no gating of the `codex-sol-implementer` wrappers or
  `/gated-implementation` (§R Q5: follow-up issue, filed by the caller).
- **"Committed" means a reachable commit's bytes at the spec worktree's `HEAD`, nothing
  weaker.** An indexed-only or working-tree-only copy never passes. Pushed is **not**
  required (§R Q4).
- **Fail closed.** Every git error, timeout, missing binary, unborn HEAD, path outside the
  repo, or mismatch of path components or bytes leads to `SPEC_UNCOMMITTED` with no launch.
  No branch may fall through to DISPATCHED. Check 4 compares blob bytes to working-tree bytes,
  which assumes no eol/smudge filter. There is no `.gitattributes` in the repo today (§7 row
  50). A future eol rule would make check 4 refuse, which is the safe direction (R15).
- **Review mode untouched.** No git call, no new field values, prompt byte-identical, and the
  same status for every input it has today.
- **Unchanged behaviour.** No existing expected value in `tests/test_sdlc_team.py` is edited.
  The only edits to existing tests are fixture changes (`_capture_dispatch` git passthrough;
  the IMPLEMENT cell's spec now committed) and **one added assertion** (§5.1 T0). Every other
  existing test that patches `Popen` dispatches in review mode, so F1 does not need to touch
  them (§7 row 52, R19).
- **Zero-bash-logic.** Logic stays in `sdlc_team.py`. No new mise task and no script.
  `mise run sdlc-team` stays the only entry point.
- **Serialization.** Models stay `codec.Struct`. Never call msgspec directly.
- **Contract `workflow.sdlc-team-no-planning-scrub` must keep passing.** The new code must not
  contain `PLANNING_DISABLED` or `LANE_ENV_OVERRIDES`, not even in a comment (row 31).
  `child_env` contains neither name, so importing it does not affect the contract, which scans
  only `sdlc_team.py`.
- **Tests use public surfaces.** Use `sdlc_team.dispatch`, `main.run_command`, and real git
  repos in `tmp_path`. The only faked boundaries are `shutil.which` and the supervisor
  `Popen`. `conftest.py`'s autouse `isolated_git_config` already isolates global and system
  git config and supplies `user.name`/`user.email` (row 32). Pass
  `-c commit.gpgsign=false` on fixture commits, as in the existing precedent (row 34).
- **Implementer lane (`codex-sol-implementer`, effort `xhigh`).** `hook_guard` cannot see a
  codex lane, so this spec is the only thing binding these rules. The lane runs **no**
  pytest, lint, verify, lint-docs, `claude`, `gh`, `kill`, `git push`, `git commit`,
  `mise run ship`, nothing in the main checkout, and nothing that touches `~/.claude/` or
  `~/.codex/`. It may run `uv run --project python ruff format` and `ruff check` on the
  touched files, the §3.6 one-off, and (only with U1) bare `mise run skills-mirror`. No edits
  outside §2.
- **Zero inline suppressions.**

## 5. Verification

### 5.1 Test arms (`tests/test_sdlc_team.py`)

**Boundary rule (R1, load-bearing): no arm that calls `dispatch` may reach a real launcher.**
Every arm in this section that calls `sdlc_team.dispatch`, directly or through
`main.run_command`, patches **both** `sdlc_team.shutil.which` (codex stub, as in
`_capture_dispatch`) **and** `sdlc_team.subprocess.Popen` (an F1 fake). Why: the gate is the
only thing between an implement request and a real detached supervisor running real
`codex exec` (`sdlc_team.py:712-720`, `:852`). Under mutation M8 the gate is gone, so an arm
without both fakes would spend codex credits instead of failing by assertion. The 04d draft's
S5 (shaped like `tests/test_sdlc_team.py:1651-1673`, which fakes neither) was exactly that
hole.

**Fixture F1: git passthrough at the `Popen` boundary (load-bearing).** `subprocess.run`
calls the module-global `Popen` (§7 row 25). `_capture_dispatch` and every raising-`Popen`
test patch `sdlc_team.subprocess.Popen`, which is the global `subprocess.Popen` (rows 17-19),
so they would also catch the gate's git calls. With the current fake,
`with _DetachedProcess()` raises `TypeError`, and the test errors for the wrong reason. Fix:

- at module scope, `_REAL_POPEN = subprocess.Popen`, bound at import, before any
  monkeypatch;
- in `_capture_dispatch`'s fake, `if command and command[0] == "git": return
  _REAL_POPEN(command, **kwargs)`, without recording the call. It forwards `env=`, so the §3.2
  scrub reaches the real git. Every other command is recorded exactly as now, so the existing
  `len(calls) == 1` assertions keep their meaning;
- new raising fakes pass `git` through the same way and raise `AssertionError` only for
  non-git commands. This refines the parent S2's "a `Popen` that raises if called" (§8 U4).

**Helper F2, `_committed_spec(tmp_path, rel="docs/specs/x.md", body=b"# spec\n") -> Path`.**
It runs `git init -b main` in `tmp_path`, writes `rel`, `git add`s it, and commits with
`-c commit.gpgsign=false`. It returns the absolute spec path. The test reads the expected
sha with its own `git rev-parse HEAD` in the fixture repo, which is the fixture's truth and
not a recomputation by the code under test. Run F2 and read that sha **before** the boundary
fakes are installed. After installation the test's own `subprocess.run` also goes through the
patched global `Popen`. It would still pass through, because it is `git`, but that ordering
is not one the arm should depend on.

- **T0, the IMPLEMENT cell of `test_no_mode_passes_a_sandbox_or_ephemeral_flag` (§7 row 20).**
  For `IMPLEMENT`, build the request on `_committed_spec(tmp_path)`. The `REVIEW` cell keeps
  `_request(tmp_path, mode=mode)`. **Add `assert result.status is
  sdlc_team.SdlcStatus.DISPATCHED`** for both cells. Why: after F1, a refused implement
  dispatch has `argv == ()`, so the existing flag-absence loop passes **vacuously**. Without
  the status assertion that cell could only pass. This corrects parent row 64, which said the
  gate "turns it red". Today it turns red only by crashing on the fake `Popen`.
- **S1, a committed spec dispatches.** Use `_committed_spec`, implement mode, and
  `_capture_dispatch`. Assert `DISPATCHED`; `spec_commit ==` the fixture's
  `git rev-parse HEAD`; `spec_path == "docs/specs/x.md"` (a literal); the prompt has the line
  `f"SPEC COMMIT: {sha} docs/specs/x.md"` **immediately after** the `SPEC FILE:` line;
  `len(calls) == 1` (the supervisor only).
- **S2, refusals (parametrized).** Every cell patches `which` and an F1 raising fake (boundary
  rule) and asserts `SPEC_UNCOMMITTED`, `pid is None`, `argv == ()`,
  `errors == (<the exact §3.2 message>,)` (or for git-unavailable,
  `errors[0].startswith("git unavailable:")`), `not Path(result.prompt_file).exists()`, and
  that no non-git `Popen` happened:
  1. an untracked file with identical bytes at `docs/specs/x.md`, in a repo whose HEAD holds
     another file, gives `spec is not committed at HEAD`;
  2. staged only (`git add`, no commit, HEAD holds another file) gives the same message;
  3. `git init` plus `git add`, with no commit at all (unborn HEAD), gives the same message;
  4. committed, then the working-tree file edited, gives
     `working tree differs from the committed spec`;
  5. committed at `docs/research/x.md` gives `ratified specs live in docs/specs/`;
  6. committed at `.agent/sdlc-specs/x.md` (force-added with `git add -f`) gives the same
     message;
  7. committed at `docs/specsX/x.md` (the component-versus-prefix trap) gives the same
     message;
  8. a spec in a `tmp_path` directory with no `git init` gives
     `spec is not inside a git work tree`. Pytest's default basetemp is outside any
     repository; if the run's basetemp sits inside one, the cell fails loudly rather than
     passing wrongly;
  9. git unavailable. **Setup order matters (R17):** first build the committed fixture with
     `_committed_spec`, because its own git calls need `git` on PATH, and **then**
     `monkeypatch.setenv("PATH", str(empty_dir))`. The result is a `git unavailable:` prefix.
     (On this host `git` resolves through a mise shim, `tests/conftest.py:61-64`. That is
     irrelevant once PATH is emptied. The §3.2 scrub keeps the emptied PATH, `child_env.py:67-74`.)
- **S3, the draft path is preserved (control for S2).** The same untracked spec as S2.1, in
  **review** mode, gives `DISPATCHED`. The prompt has no `SPEC COMMIT:`, `spec_commit == ""`
  and `spec_path == ""`, and the fake recorded **zero git commands**. Record git calls in a
  separate list for this arm, so the claim "review makes no git call" is measured rather than
  assumed.
- **S4, skill tokens (only with U1).** `.claude/skills/codex-sdlc-team/SKILL.md` contains
  `in implement mode it must be committed under docs/specs/` and `` `spec_uncommitted` ``.
- **S5, the public CLI route (R1).** Shaped like
  `test_main_cli_registration_emits_typed_missing_spec_result` (§7 row 21), **but unlike that
  precedent it installs both boundary fakes before `main.run_command`**:
  `monkeypatch.setattr(sdlc_team.shutil, "which", <codex stub>)` and
  `monkeypatch.setattr(sdlc_team.subprocess, "Popen", <F1 git-passthrough fake that raises
  AssertionError for any non-git command>)`. `main.run_command` reaches `sdlc_team_main`
  in-process (`main.py:3056-3058`), so the patches hold. Request: implement mode, on an
  untracked existing spec. Assert `SystemExit` code 1, decoded status `SPEC_UNCOMMITTED`,
  `pid is None`, `argv == ()`. Under M8 the dispatch reaches the fake supervisor `Popen`. Its
  `AssertionError` is not an `OSError` (`sdlc_team.py:866`), so it propagates and S5 fails by
  assertion. No real supervisor or codex is ever launched.
- **Schema.** The existing `test_committed_schema_matches_its_canonical_model` (row 23) must
  pass against the regenerated dispatch schema, unchanged for request and settlement.

### 5.2 Mutation (FAIL) arms: coordinator, after `git add` of the lane's diff

Each mutation is a realistic regression. After each one, run
`git checkout -- <file>` (safe, because staged), then re-run the module green.

| Arm | Regression | Must fail |
|---|---|---|
| M8 | Delete the `if request.mode is SdlcMode.IMPLEMENT:` gate call from `dispatch` | every S2 cell (non-git `Popen` raises, or status ≠ SPEC_UNCOMMITTED) and S5, **by assertion, with no real launch** (boundary rule, R1) |
| M9 | Replace check 3 with a working-tree/index check (e.g. `git ls-files --error-unmatch <rel>`) | S2.2 (staged only) and S2.3 (unborn HEAD): `ls-files` succeeds, so check 4's `cat-file HEAD:<rel>` returns the check-4 message instead of the expected check-3 one. **S2.1 is expected to SURVIVE M9 (R18):** an untracked file still fails `ls-files` and gets the same check-3 message. Do not report that as a broken arm |
| M10 | Replace the component check with `str(rel).startswith("docs/specs")` | S2.7 |
| M11 | Delete the check-4 blob/working-tree digest comparison | S2.4 |
| M12 | Drop the mode condition, so review is gated too | S3 |
| M13 | Delete the `SPEC COMMIT:` line from `build_prompt` | S1 |
| M14 | Let the `OSError` branch return `None` (fail open) | S2.9 |
| M15 (test-side vacuity arm) | Revert T0's IMPLEMENT fixture to `_request(tmp_path, mode=mode)` | T0's IMPLEMENT cell, on the `DISPATCHED` assertion. This proves the cell cannot pass vacuously |
| M16 | Restore the pre-change `schemas/sdlc-team-dispatch.json` | the dispatch cell of the schema-equality test |

### 5.3 Control arms

- **Positive control:** S1 (committed gives DISPATCHED) runs beside S2, so a gate that
  refuses everything fails S1.
- **Mode control:** S3 (the same draft in review mode dispatches).
- **Negative-probe controls used while drafting** (§7 rows 14-15): `SPEC_UNCOMMITTED`
  matches nothing in the repo while `SPEC_MISSING` matches 7 lines (including the `.agents`
  mirror); `sdlc_team.py` has 0 `git` or `subprocess.run` hits while the same pattern matches 6
  lines in `session_common.py`.
- **Tracked-path probe control (this run):** the worktree index contains
  `sdlc-team-review-jobdir-artifacts-29a5dcc4.md` (1 hit). The untracked
  `premise-verifier-jobdir-part2.md` and an invented name give 0. So the §6 report citation is
  tracked at the base.

### 5.4 Gate bundle (coordinator, host slot, each rc read from the artifact)

1. `uv run --project python pytest tests/test_sdlc_team.py -x -q > "$LOG" 2>&1; echo "rc=$?" >> "$LOG"`
2. M8-M16 (§5.2).
3. `mise run gate -- run lint` (includes `skills_mirror_parity`), then
   `mise run gate -- run pytest`, `mise run gate -- run verify`, and, with U1,
   `mise run gate -- run lint-docs`.
4. **Real-integration arm** (`.claude/rules/real-integration-evidence.md`): run the public
   `mise run sdlc-team -- <request.json>`, implement mode, on an **untracked** draft spec. It
   must print `"status":"spec_uncommitted"` and exit rc 1 with no process launched. That is
   safe, because the gate stops before any launch. The positive real arm (implement mode on a
   committed spec) would launch a paid codex lane. It is recorded as **unverified** until the
   first real implement dispatch after merge (the parts-1+3 spec, committed to `docs/specs/`),
   and that dispatch's `spec_commit` and `spec_path` are checked then. No mock stands in for it.
5. Cold review by ref. The diff is codex-authored, so the reviewer is Opus `cold-reviewer`,
   plus `/code-review` and `/mattpocock-skills:code-review` against this spec. The review
   reads every error and timeout branch of `_spec_commit_error`, and confirms every git call
   carries the §3.2 `env=` scrub and the stated capture type.

## 6. Commit

`COMMIT: caller`. The mutation arms need the diff staged. Branch `fix/jobdir-dispatch-gate`,
cut from `13af2848` or later.

Subject: `feat(sdlc-team): refuse implement dispatch unless the spec is committed under docs/specs/`.

The body cites the parent spec, the review report
`docs/research/kb/reports/agents/sdlc-team-review-jobdir-artifacts-29a5dcc4.md` (tracked at the
base, §5.3), and Ray's 2026-10-04 §R Q7 ruling (part 2 first, on its own). It says that review
mode is unchanged, that the implementer wrappers and `/gated-implementation` are not gated
(follow-up, §R Q5), that the schema was regenerated one-off (follow-up task, §R Q9), and that
pushing is not required (§R Q4). It ends with the session's attribution trailers. The lane does
not push or ship.

Before dispatch, commit this spec, once ratified, to
`docs/specs/jobdir-dispatch-gate-2026-10-04.md` on the branch. It is the first spec the gate
will govern.

## 7. PREMISES

Every row was read by me in this run. Repo-relative paths are read in the **04h worktree**
(`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-04h`, at
`13af2848`) unless prefixed. `.git/…` paths are the main checkout's git dir. `HW/` =
`…/.claude/worktrees/handoff-2026-10-04d/`. Kind: L = layout/fact, I = interface, P = test
precedent, A = assumption. Rows 1-9 are rewritten (R2-R9). The **R** column of the 04d draft is
retired, because every row is now stated at the base.

| # | Kind | Premise | Citation |
|---|---|---|---|
| 1 | L | Main checkout HEAD is `main`, and `refs/heads/main` = `13af28480ae4…` | `.git/HEAD:1`; `.git/refs/heads/main:1` |
| 2 | L | `refs/remotes/origin/main` = `13af28480ae4…`, the same as local main. Its reflog records `ed8e1a96 → ee3b29da` (pull) and then `ee3b29da → 13af2848` (`fetch -q origin main: fast-forward`), so `ee3b29da` is an ancestor of the base | `.git/refs/remotes/origin/main:1`; `.git/logs/refs/remotes/origin/main:213-214` |
| 3 | L | The 04h worktree, where every repo anchor below was read, is on `docs/handoff-2026-10-04h` at `13af2848` | `.git/worktrees/handoff-2026-10-04h/HEAD:1`; `.git/worktrees/handoff-2026-10-04h/logs/HEAD:1-2` |
| 4 | L | The banner fix is in the base: the argv carries the 2-line comment plus `"--color", "never"`, and `dispatch` is at `:723` | `python/src/dotfiles_setup/sdlc_team.py:819-822`, `:723` |
| 5 | A | **`d921a3f6` is the merged #1662 and an ancestor of `13af2848`.** Caller-stated. No file under `.git/{refs,logs,packed-refs,FETCH_HEAD}` names `d921a3f6` (Grep → 0; control `ee3b29da` → 5 files), so it is unverifiable here. Row 4 corroborates it by content. The Provenance command settles it | — |
| 6 | A | **The banner change is PR #1662.** Caller-stated; no PR metadata is readable without a shell. No effect on code (residual R12) | — |
| 7 | I | At the base: `generate_dispatch_schema` `:1067`, `sdlc_team_main` `:1093` | `python/src/dotfiles_setup/sdlc_team.py:1067`, `:1093` |
| 8 | P | At the base: `_request` `:171`, `_capture_dispatch` `:185`, sandbox test def `:270`, `--color` asserts `:412-416`, schema test def `:1706` | `tests/test_sdlc_team.py:171`, `:185`, `:270`, `:412-416`, `:1706` |
| 9 | — | *Retired (R9).* The 04d row assumed `eba2e4e4` did not touch the §2 files. Every cited file was instead re-read at the base | — |
| 10 | I | `SdlcStatus` = dispatched, spec_missing, cli_missing, invalid_request | `python/src/dotfiles_setup/sdlc_team.py:56-62` |
| 11 | I | `SdlcTeamDispatch` fields end with `errors: tuple[str, ...] = ()` | `sdlc_team.py:83-98` |
| 12 | I | `_DispatchState(run_id, status, started_at, errors, pid, argv)`; `_resolved_dispatch` builds `SdlcTeamDispatch` by keyword | `sdlc_team.py:172-180`, `:214-253` (keywords `:237-251`) |
| 13 | I | `build_prompt(request, repo_root)` emits `SPEC FILE:` at `:274` and a REVIEW-only clause at `:261-267` | `sdlc_team.py:256-293` |
| 14 | L | No `SPEC_UNCOMMITTED`, `spec_uncommitted` or `spec_commit` exists in python/, tests/, schemas/, .claude/skills/ or .agents/skills/. Control: `SPEC_MISSING\|spec_missing` over the same glob matches 7 lines | Grep (0 hits); control hits `sdlc_team.py:60`, `:748`, `schemas/sdlc-team-dispatch.json:85`, `.claude/skills/codex-sdlc-team/SKILL.md:75`, `.agents/skills/codex-sdlc-team/SKILL.md:75`, `tests/test_sdlc_team.py:340`, `:1671` |
| 15 | L | `sdlc_team.py` invokes no git today. Control: the same pattern `\bgit\b\|subprocess\.run` matches 6 lines in `session_common.py` | Grep over `sdlc_team.py` → 0; over `session_common.py` → `:184`, `:186`, `:187`, `:194`, `:197`, `:202` |
| 16 | I | `dispatch`: invalid → INVALID_REQUEST `:727-739`; `is_file()` false → SPEC_MISSING `:741-753`; then `_codex_launcher()` → CLI_MISSING `:755-767`; paths `:769-777` | `sdlc_team.py:723-777` |
| 17 | I | argv tuple, then a `try` that writes the prompt (`:833`), unlinks the settlement (`:834`) and `subprocess.Popen`s the supervisor (`:852`); `except OSError` → INVALID_REQUEST carrying argv; DISPATCHED after | `sdlc_team.py:811-828`, `:830-878`, `:880-891` |
| 18 | L | `sdlc_team.py` does `import subprocess` (module-level, so `sdlc_team.subprocess` is the global module) | `sdlc_team.py:16` |
| 19 | P | `_capture_dispatch` monkeypatches `sdlc_team.subprocess.Popen` with a fake that records every call and returns `_DetachedProcess` (no `__enter__`), and `sdlc_team.shutil.which` → codex stub | `tests/test_sdlc_team.py:185-203`, `:28-31` |
| 20 | P | The IMPLEMENT cell of `test_no_mode_passes_a_sandbox_or_ephemeral_flag` builds an untracked spec via `_request` and asserts only flag absence in `result.argv` | `tests/test_sdlc_team.py:266-286`, `:171-182` |
| 21 | P | CLI route precedent: `main.run_command` → `SystemExit` 1 and a typed SPEC_MISSING result. It fakes neither `which` nor `Popen` (see rows 45-46). `sdlc_team_main` returns 0 only for DISPATCHED | `tests/test_sdlc_team.py:1651-1673`; `sdlc_team.py:1093-1110` (`:1110`) |
| 22 | L | The committed dispatch schema: 2-space JSON; `required` = run_id, status; enum has 4 values | `schemas/sdlc-team-dispatch.json:1-97`, `:73-76`, `:81-86` |
| 23 | I | The schema-equality test compares parsed JSON of all three committed schemas with `generate_*_schema()`; `generate_dispatch_schema` = `codec.schema(SdlcTeamDispatch)` | `tests/test_sdlc_team.py:1698-1714` (equality `:1711-1714`); `sdlc_team.py:1067-1069` |
| 24 | P | `_codex_launcher` resolves `mise` and `codex` via `shutil.which`, the boundary the tests fake | `sdlc_team.py:700-720` (`:712`, `:715`) |
| 25 | L | CPython 3.14 `subprocess.run` does `with Popen(*popenargs, **kwargs) as process:`, a module-global lookup, so patching `subprocess.Popen` intercepts `run` | `~/.local/share/uv/python/cpython-3.14-macos-aarch64-none/lib/python3.14/subprocess.py:512`, `:554`. That dir is the venv's home per the **main checkout's** `python/.venv/pyvenv.cfg:1`; the 04h worktree has no `.venv` |
| 26 | L | The skill: "`spec_file` must be absolute and exist at dispatch" | `.claude/skills/codex-sdlc-team/SKILL.md:51` |
| 27 | L | The skill's status list, including `spec_missing` | `.claude/skills/codex-sdlc-team/SKILL.md:72-77`; mirror `.agents/skills/codex-sdlc-team/SKILL.md:75` |
| 28 | L | `skills-mirror` bare form writes the mirror; hk `skills_mirror_parity` runs `--check` | `mise.toml:1389-1392`; `hk.pkl:733-734` |
| 29 | L | The mirror rewrites `.claude/skills/`→`.agents/skills/`, `Claude Code`→`Codex`, `Claude`→`Codex` | `python/src/dotfiles_setup/skills_mirror.py:122-125` |
| 30 | L | The only production callers: `mise run sdlc-team` → `dotfiles-setup sdlc-team` → `sdlc_team_main` | `mise.toml:294-296`; `python/src/dotfiles_setup/main.py:3056-3058` |
| 31 | L | Contract `workflow.sdlc-team-no-planning-scrub` forbids `PLANNING_DISABLED\|LANE_ENV_OVERRIDES` in `sdlc_team.py` | `python/verification/suites.toml:3046-3052` |
| 32 | P | The autouse `isolated_git_config` sets `GIT_CONFIG_GLOBAL` (user.name/email) and `GIT_CONFIG_NOSYSTEM=1` for every test | `tests/conftest.py:27-49` |
| 33 | L | `MAIN_CHECKOUT_TIMEOUT_S = 30` | `python/src/dotfiles_setup/session_common.py:32` |
| 34 | P | A real-git fixture precedent: `git init -b main`, `-c commit.gpgsign=false commit`, `subprocess.run(..., timeout=10)` | `tests/test_worktree_guard.py:19-22`, `:30`, `:35` |
| 35 | L | `IMPLEMENT` mode is used by exactly one existing sdlc test cell | Grep `IMPLEMENT\|"implement"` over tests/ → `tests/test_sdlc_team.py:268` is the only sdlc hit. The others are `cv.Edge.REOPEN_IMPLEMENT` (`test_codex_lane.py`, `test_codex_verdict.py`, `test_codex_lane_e2e.py`), the substring `GATED_IMPLEMENTATION` (`tests/test_workflows_js.py:440`, `:454`, `:533`, `:559`, `:588`) and two session-review fixture lines. These show that the probe matches (R21) |
| 36 | P | Raising-`Popen` precedent for no-launch arms | `tests/test_sdlc_team.py:326-344`, `:364-367` |
| 37 | L | Rule 4: "Specs go in `docs/specs/`"; `docs/specs/` is a tracked durable tree | `.claude/rules/agent-artifact-conventions.md:75`, `:48` |
| 38 | L | `docs/specs/` is not gitignored (no match), while `.agent/` is. Control: the same file matches `.agent/` at `:125` | `.gitignore` Grep → `.agent` at `:41`, `:45`, `:50`, `:125`; 0 for `docs/specs` |
| 39 | L | Parent §3.8 (ratified body): check order, error strings, review unchanged, one-off regen | `HW/docs/research/kb/raw/specs-2026-10-04d/spec-jobdir-preservation.md:310-341`. The same file is **tracked at the base** in the 04h worktree (index Grep → 1), and its anchors there sit at the same lines (`:53`, `:310`, `:468`, `:492`, `:600`, `:676`, `:678` re-hit) |
| 40 | L | Parent S1-S4 and M8-M9 | same file `:466-479`, `:492-493` |
| 41 | L | Parent row 64: "P2 turns it red unless its fixture commits the spec". Corrected in §5.1 T0 | same file `:600` |
| 42 | L | §R rulings: Q7 part 2 first, only `sdlc_team.py`; Q1-Q6, Q8-Q9 recommended options | same file `:676-679` |
| 43 | A | **`git rev-parse --show-toplevel` prints a symlink-resolved path on macOS.** Not probed; §3.2 resolves both sides, so the spec does not depend on it (residual R13) | — |
| 44 | A | **msgspec emits the two new `str = ""` fields as `{"type":"string","default":""}`**, by analogy with every existing `str = ""` field (`schemas/sdlc-team-dispatch.json:33-36`, `:61-64`). The equality test settles it (residual R13) | — |
| 45 | L | **S5 hazard (R1).** The CLI precedent fakes neither boundary, and today it is safe only because SPEC_MISSING returns before launch. With the gate deleted (M8), an implement request on an existing spec would reach the real `_codex_launcher` and the real `subprocess.Popen` | `tests/test_sdlc_team.py:1651-1673`; `sdlc_team.py:741-753`, `:712-720`, `:852` |
| 46 | I | The supervisor launch catches only `OSError`, so a fake's `AssertionError` propagates out of `dispatch` and fails the arm | `sdlc_team.py:866` |
| 47 | I | `child_env.without_git_context()` drops `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_COMMON_DIR`, `GIT_OBJECT_DIRECTORY`, `GIT_ALTERNATE_OBJECT_DIRECTORIES` and `__MISE_DIFF`, and copies everything else from `os.environ` at call time (so a monkeypatched PATH survives). `child_env` imports only `os` and `re` (no cycle) | `python/src/dotfiles_setup/child_env.py:36-45`, `:60-74`, `:30-31` |
| 48 | P | The scrub is the convention for production git probes, and the reason is stated in source | `python/src/dotfiles_setup/pr.py:244`, `:259`; `session_state.py:120`; `doctor.py:1524`, `:1654-1656`; `sync.py:414`, `:436`; `pr_facts.py:53` |
| 49 | P | `text=True` precedent for a git probe parsed as `str` | `python/src/dotfiles_setup/session_common.py:186-192` |
| 50 | L | There is no `.gitattributes` in the repo, so blob bytes equal working-tree bytes today. Control: the same Glob shape finds `.gitignore` | Glob `**/.gitattributes` → 0; Glob `**/.gitignore` → `.gitignore` |
| 51 | L | The skill's example request is implement mode on `/absolute/path/to/spec.md`, a shape the gate will refuse (R16) | `.claude/skills/codex-sdlc-team/SKILL.md:37-48` |
| 52 | P | Every other existing test that patches `sdlc_team.subprocess.Popen` dispatches in review mode, so F1 need not touch them. `:133` is the supervisor harness, not `dispatch` | `tests/test_sdlc_team.py:337`, `:367`, `:402`, `:434`, `:466`, `:1614`; IMPLEMENT only at `:268` (row 35) |
| 53 | L | **NEW (R20).** `python/AGENTS.md` says "Models and enums are **generated, never hand-written** (R16/D23): `schemas/<name>.schema.json` → a `[tool.datamodel-codegen]` job". The only codegen job is `drift-verdict`, and `generated/` holds only `drift_verdict.py`. The sdlc_team models are hand-written and their schema is generated *from* them, the reverse direction | `python/AGENTS.md:109-111`; `python/pyproject.toml:225`, `:258-260`; Glob `python/src/dotfiles_setup/generated/*.py` → `__init__.py`, `drift_verdict.py`; `sdlc_team.py:56-98`, `:1067-1069` |
| 55 | L | No `per_path_tokens` entry binds `sdlc_team.py`, `tests/test_sdlc_team.py`, the dispatch schema or the skill, so hk `contract_token_uniqueness` (`hk.pkl:388-395`) cannot be tripped by this change. The only contract on `sdlc_team.py` is the `regex_forbid` in row 31. Control: the same Grep shape `"python/src/dotfiles_setup/dag_tick\.py" = \[` hits 3 suites | Grep over `python/verification/suites.toml` → 0 for the four sdlc paths; `sdlc_team\|sdlc-team\|codex-sdlc-team` → only `:2427`, `:2434` (prose/lines, `.claude/CLAUDE.md`), `:3046-3051` |
| 54 | L | The §6 review report is tracked at the base. Control: the untracked premise-verifier report, an invented name, and this revision's own untracked path are absent from the same index | Grep of `.git/worktrees/handoff-2026-10-04h/index`: `sdlc-team-review-jobdir-artifacts-29a5dcc4\.md` → 1; `premise-verifier-jobdir-part2\.md\|<invented>` → 0; `specs-2026-10-04h/spec-jobdir-part2-dispatch-gate\.md` → 0 |

## 8. Open choices for the architect (stop for ratification)

**U1: does the codex-sdlc-team skill (plus its generated mirror) ship with part 2?**
- **Recommended: include it.** PRO: the skill's status list (row 27) would otherwise go stale
  the moment `spec_uncommitted` exists, and its own example request (row 51) would become a
  refused shape (`.claude/rules/tool-currency-and-native-first.md` rule 5: sync describing
  docs in the same change). The parent §3.9 token is P2-only. CON: it goes beyond §R's literal
  "touches only `sdlc_team.py`" and adds `lint-docs` and mirror steps.
- **Alternative: code, schema and tests only; the skill goes with parts 1+3.** PRO: §R
  literally. CON: a window where the doc and the code disagree, and the example is refused.

**U2: the `spec-scribe.md` sentence and the `agent-artifact-conventions.md` rule-4 clause.**
- **Recommended: defer both to the parts-1+3 PR.** PRO: the rule-4 clause also names
  `coordinator-handoff cleanup`, which does not exist yet; keeping both in one place avoids
  editing the rule twice. CON: the scribe definition does not mention the commit step until
  then (the coordinator already does it, §6).
- **Alternative: add only the spec-scribe sentence now.** CON: scope growth for one line.

**U3: CLOSED by fact (R3).** #1662's hunk is in the base (row 4), so the branch is cut from
`13af2848` or later and no anchor is forecast. The only open item is the caller-stated ancestry
check in the Provenance paragraph.

**U4: the refinement of parent S2's "a `Popen` that raises if called".**
- **Recommended: raise only for non-git commands (F1).** PRO: without it the gate's own git
  calls hit the fake, and every refusal arm errors with `AssertionError` instead of returning
  `SPEC_UNCOMMITTED` (row 25). CON: it departs from the parent's literal wording.
- **Alternative: run git through an injected runner parameter on `dispatch`.** PRO: no
  passthrough in the fixture. CON: changes a public signature that `sdlc_team_main` and
  external callers use, for test convenience only.

**U5: CLOSED.** The premise-verifier ran over the 04d draft
(`docs/research/kb/reports/agents/premise-verifier-jobdir-part2.md`), and this revision applies
its four blocking corrections and records every residual (Revision log). A re-run over this
revision is optional; rows 45-54 are new.

**U6 (NEW, non-blocking; R20): the "models are generated" doctrine.** `python/AGENTS.md:109-111`
says models and enums are generated from schemas. This module is the reverse: hand-written
`codec.Struct` models with a schema generated from them (row 53).
- **Recommended: extend the existing hand-written models for part 2, unchanged in direction,
  and name the doctrine gap in the §R Q9 follow-up issue** (the `--write-schemas` task). PRO:
  this matches the module as it exists and the ratified one-off regen (Q9), and keeps part 2 to
  its ratified scope. CON: it adds two fields to a module that the written doctrine says should
  not hold hand-written models.
- **Alternative: convert the sdlc-team models to a datamodel-codegen job first.** PRO: the
  doctrine holds. CON: it touches `pyproject.toml`, `generated/` and every importer, which is far
  outside §R Q7's "touches only `sdlc_team.py`", and it would need its own spec.

### Residuals on the record (not blocking; from the report)

- Row 6: the PR number is unverified, with no effect on code.
- Rows 43-44: settled by the design (§3.2 resolves both sides) and by the equality test.
- Row 5: the `d921a3f6` ancestry is caller-stated. Run the Provenance command before cutting.
- Row 50: there is no `.gitattributes` today; a future eol rule fails closed.
- Row 51: the skill example path matters only if U1 is accepted (it is applied in §3.7 under U1).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): local reads only (04h worktree at `13af2848`: source, tests, schema, skills, rules, conftest, `mise.toml`, `hk.pkl`, `suites.toml`, `python/AGENTS.md`, `pyproject.toml`; main-checkout git refs, reflogs and worktree index; the parent spec in the handoff-2026-10-04d worktree).

---

## Architect ratification (coordinator 5a11da, 2026-10-04 ~12:40 CDT)

U1, U2, U4 and U6: the recommended option of each is RATIFIED (U1 = include the skill + regenerated mirror; U6 = extend
as-is and name the generated-models gap in the Q9 follow-up issue). U3 and U5 are closed. d921a3f6 (#1662) is an ancestor
of the base 13af2848 (`merge-base --is-ancestor` rc=0; reverse control rc=1). Next: premise re-verification, then dispatch.

## Base pin + re-verification corrections (coordinator 5a11da, 2026-10-04, from premise-verifier-recheck-2026-10-04h.md)

- **Base: cut from origin/main `ad4dbc62`** (13af2848 + #1667 docs, #1665 saved-searches, #1658 bgisolation). This supersedes every "13af2848 or later". `git diff --stat 13af2848 ad4dbc62` over this spec's §2 paths touches only `python/verification/suites.toml` (+16 lines: a new `workflow.research-saved-search-wiring` suite inserted at :1501, plus token edits in two unrelated suites) and `coordinator_handoff.py` (`CROSS_SESSION_SETTINGS`, :106-112; launch_argv docstring). So every `suites.toml` anchor after :1500 shifts **+16** (e.g. :2630→:2646, :2638→:2654, :2619→:2635, :1963→:1979, :1974→:1990). Re-read anchors at ad4dbc62 before editing; the token text itself is unchanged.
- The "04h worktree has no `.venv`" parentheticals are stale (it now has one); cosmetic.
- Spec A residual: `dispatch` gains a 6th return = ruff PLR0911 ceiling; split `_spec_commit_error` so no function exceeds 6 returns.
