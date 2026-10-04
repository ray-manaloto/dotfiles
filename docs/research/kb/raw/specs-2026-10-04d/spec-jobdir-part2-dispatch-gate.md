# SPEC: part (2) only. sdlc-team implement mode refuses a spec that is not committed under `docs/specs/`

Status: DRAFT by `spec-scribe`, 2026-10-04. NOT ratified, NOT dispatched. It is extracted
from the ratified parent spec
`HW/docs/research/kb/raw/specs-2026-10-04d/spec-jobdir-preservation.md` (§3.8, §5.1 S1-S4,
§5.2 M8-M9, §R). Every `file:line` below was re-read in this run. §8 lists the choices the
architect still has to make. Stop there for ratification.

Memory: the spec-scribe local memory directory was empty at the start of this run, so no
prior convention was applied.

**Provenance caveat (read before dispatch).** This lane has no shell. Anchors come from the
**working tree of the main checkout** (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`).
That checkout is on `main` at `36ab6bba…`, but **`refs/remotes/origin/main` already reads
`eba2e4e4…`**. A `fetch` fast-forwarded it and the local `main` was never pulled (§7 rows
1-3). I could not read what `eba2e4e4` changed. Before dispatch the coordinator must run the
command below. The cited files must print nothing, or every row they touch gets re-derived:

```bash
git -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles diff --stat 36ab6bba origin/main -- \
  python/src/dotfiles_setup/sdlc_team.py tests/test_sdlc_team.py tests/conftest.py \
  schemas/sdlc-team-dispatch.json .claude/skills/codex-sdlc-team/SKILL.md \
  .agents/skills/codex-sdlc-team/SKILL.md python/verification/suites.toml
```

**#1662 interaction.** The banner fix is local branch `fix/codex-banner-ansi`, commit
`2d81c36d`, worktree `.claude/worktrees/codex-banner-ansi` (§7 rows 4-5). I am assuming it
is #1662 (row 6). It inserts four lines (`--color never` plus a comment) into the argv tuple at
`sdlc_team.py:819`. So every `sdlc_team.py` anchor at or after `:819` moves by about **+4**,
and every `tests/test_sdlc_team.py` anchor after about `:409` moves by about **+5** (rows
7-8). None of this spec's edits touch those lines. The rows marked **R** in §7 still have to
be re-read against whatever origin/main the branch is cut from.

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
`fix/jobdir-dispatch-gate`, cut from origin/main (timing in §8 U3). Never the main
checkout. Allowlist (modify only these):

| Path | Change |
|---|---|
| `python/src/dotfiles_setup/sdlc_team.py` | `SPEC_UNCOMMITTED`; two dispatch fields; `_DispatchState` passthrough; `_spec_commit_error`; the gate in `dispatch`; one prompt line (§3) |
| `schemas/sdlc-team-dispatch.json` | regenerated from `generate_dispatch_schema()` only (one-off command, §3.6). Never hand-edited |
| `tests/test_sdlc_team.py` | git passthrough in `_capture_dispatch`; a committed-spec helper; the IMPLEMENT cell of `test_no_mode_passes_a_sandbox_or_ephemeral_flag` gets a committed-spec fixture **plus** a `DISPATCHED` assertion (§5.1 T0); new arms S1-S5 |
| `.claude/skills/codex-sdlc-team/SKILL.md` | **pending U1 (recommended: include).** Implement-mode committed-spec requirement; `spec_uncommitted` in the status list |
| `.agents/skills/codex-sdlc-team/SKILL.md` | **generated** by bare `mise run skills-mirror` only, and only if U1 is accepted |

**Do not touch:** `schemas/sdlc-team-request.json` and `schemas/sdlc-team-settlement.json`
(their models do not change, so the equality test must keep passing on the committed bytes);
`coordinator_handoff.py`, `session_common.py`, and everything else that belongs to parts (1)
and (3); `.claude/agents/spec-scribe.md` and `.claude/rules/agent-artifact-conventions.md`
(U2); `tests/conftest.py`; `python/verification/suites.toml`; `.claude/settings.json`;
`hook_guard.py`; anything under `~/.claude/` or `~/.codex/`.

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
   `ratified specs live in docs/specs/`.
3. `git -C top rev-parse --verify --quiet HEAD:<rel>`. A nonzero exit returns
   `spec is not committed at HEAD`. This covers the untracked, staged-only and unborn-HEAD
   cases.
4. Read the blob with `git -C top cat-file blob HEAD:<rel>`, captured as **bytes**. If the
   sha256 of that stdout differs from the sha256 of `spec_file.read_bytes()`, return
   `working tree differs from the committed spec`. A nonzero exit fails closed with the same
   message.
5. `commit = git -C top rev-parse HEAD` (stdout stripped). The function returns
   `(None, commit, rel.as_posix())`.

Every git call uses `subprocess.run([...], capture_output=True, check=False,
timeout=_GIT_TIMEOUT_S)` with the **literal** program name `"git"`. Never use
`shutil.which("git")`: the test boundary fakes `which` to return a codex stub (§7 row 24). An
`OSError` (including `FileNotFoundError`) or a `subprocess.TimeoutExpired` returns
`git unavailable: <exception text>`. An `OSError` from reading the spec's bytes does the
same. No exception escapes `_spec_commit_error`.

### 3.3 The gate in `dispatch`

The gate goes after the existing `SPEC_MISSING` return and before `_codex_launcher()`. That
gives the order INVALID_REQUEST, then SPEC_MISSING, then **SPEC_UNCOMMITTED** (implement
only), then CLI_MISSING, then DISPATCHED. In code: `if request.mode is SdlcMode.IMPLEMENT:`
call `_spec_commit_error(spec_file)`. On error, return
`_resolved_dispatch(..., _DispatchState(status=SPEC_UNCOMMITTED, errors=(error,), ...))`
with `pid=None` and `argv=()`. Do this **before** the prompt is written, before
`settlement_file.unlink`, and before any `Popen`.

Every result produced **after** the gate passes carries `spec_commit` and `spec_path`: the
DISPATCHED result, the post-gate CLI_MISSING result, and the launch-failure INVALID_REQUEST
result at the `except OSError` branch. In review mode and in every pre-gate result both stay
`""`.

### 3.4 Prompt

```python
def build_prompt(
    request: SdlcTeamRequest, repo_root: Path, *, spec_commit: str = "", spec_path: str = ""
) -> str: ...
```

When `request.mode is SdlcMode.IMPLEMENT` and `spec_commit` is non-empty, emit exactly one
line, `SPEC COMMIT: <spec_commit> <spec_path>`, directly after the `SPEC FILE:` line. In
every other case the prompt is byte-identical to today's. `dispatch` passes the two values it
got from the gate.

### 3.5 CLI

No change to `sdlc_team_main`. It already returns rc 0 only for `DISPATCHED`, so
`spec_uncommitted` exits 1 and prints the typed result (§7 row 21).

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
  No branch may fall through to DISPATCHED.
- **Review mode untouched.** No git call, no new field values, prompt byte-identical, and the
  same status for every input it has today.
- **Unchanged behaviour.** No existing expected value in `tests/test_sdlc_team.py` is edited.
  The only edits to existing tests are fixture changes (`_capture_dispatch` git passthrough;
  the IMPLEMENT cell's spec now committed) and **one added assertion** (§5.1 T0).
- **Zero-bash-logic.** Logic stays in `sdlc_team.py`. No new mise task and no script.
  `mise run sdlc-team` stays the only entry point.
- **Serialization.** Models stay `codec.Struct`. Never call msgspec directly.
- **Contract `workflow.sdlc-team-no-planning-scrub` must keep passing.** The new code must not
  contain `PLANNING_DISABLED` or `LANE_ENV_OVERRIDES`, not even in a comment (row 31).
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

**Fixture F1: git passthrough at the `Popen` boundary (load-bearing).** `subprocess.run`
calls the module-global `Popen` (§7 row 25). `_capture_dispatch` and every raising-`Popen`
test patch `sdlc_team.subprocess.Popen`, which is the global `subprocess.Popen` (rows 17-19),
so they would also catch the gate's git calls. With the current fake,
`with _DetachedProcess()` raises `TypeError`, and the test errors for the wrong reason. Fix:

- at module scope, `_REAL_POPEN = subprocess.Popen`, bound at import, before any
  monkeypatch;
- in `_capture_dispatch`'s fake, `if command and command[0] == "git": return
  _REAL_POPEN(command, **kwargs)`, without recording the call. Every other command is
  recorded exactly as now, so the existing `len(calls) == 1` assertions keep their meaning;
- new raising fakes pass `git` through the same way and raise only for non-git commands.
  This refines the parent S2's "a `Popen` that raises if called" (§8 U4).

**Helper F2, `_committed_spec(tmp_path, rel="docs/specs/x.md", body=b"# spec\n") -> Path`.**
It runs `git init -b main` in `tmp_path`, writes `rel`, `git add`s it, and commits with
`-c commit.gpgsign=false`. It returns the absolute spec path. The test reads the expected
sha with its own `git rev-parse HEAD` in the fixture repo, which is the fixture's truth and
not a recomputation by the code under test.

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
- **S2, refusals (parametrized).** Every cell asserts `SPEC_UNCOMMITTED`, `pid is None`,
  `argv == ()`, `errors == (<the exact §3.2 message>,)` (or for git-unavailable,
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
  9. git unavailable: `monkeypatch.setenv("PATH", str(empty_dir))` on a committed fixture
     gives `git unavailable:` as a prefix.
- **S3, the draft path is preserved (control for S2).** The same untracked spec as S2.1, in
  **review** mode, gives `DISPATCHED`. The prompt has no `SPEC COMMIT:`, `spec_commit == ""`
  and `spec_path == ""`, and the fake recorded **zero git commands**. Record git calls in a
  separate list for this arm, so the claim "review makes no git call" is measured rather than
  assumed.
- **S4, skill tokens (only with U1).** `.claude/skills/codex-sdlc-team/SKILL.md` contains
  `in implement mode it must be committed under docs/specs/` and `` `spec_uncommitted` ``.
- **S5, the public CLI route.** Shaped like `test_main_cli_registration_emits_typed_missing_spec_result`
  (§7 row 21): an implement request on an untracked existing spec through
  `main.run_command` gives `SystemExit` code 1, decoded status `SPEC_UNCOMMITTED`, `pid is
  None`, `argv == ()`.
- **Schema.** The existing `test_committed_schema_matches_its_canonical_model` (row 23) must
  pass against the regenerated dispatch schema, unchanged for request and settlement.

### 5.2 Mutation (FAIL) arms: coordinator, after `git add` of the lane's diff

Each mutation is a realistic regression. After each one, run
`git checkout -- <file>` (safe, because staged), then re-run the module green.

| Arm | Regression | Must fail |
|---|---|---|
| M8 | Delete the `if request.mode is SdlcMode.IMPLEMENT:` gate call from `dispatch` | every S2 cell (non-git `Popen` raises, or status ≠ SPEC_UNCOMMITTED) and S5 |
| M9 | Replace check 3 with a working-tree/index check (e.g. `git ls-files --error-unmatch <rel>`) | S2.2 (staged only); S2.1 and S2.3 must fail too or be explained |
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
  matches nothing in the repo while `SPEC_MISSING` matches 6 times; `sdlc_team.py` has 0 git
  or `subprocess.run` hits while the same pattern matches 6 times in `session_common.py`.

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
   reads every error and timeout branch of `_spec_commit_error`.

## 6. Commit

`COMMIT: caller`. The mutation arms need the diff staged. Branch `fix/jobdir-dispatch-gate`.

Subject: `feat(sdlc-team): refuse implement dispatch unless the spec is committed under docs/specs/`.

The body cites the parent spec, the review report
`docs/research/kb/reports/agents/sdlc-team-review-jobdir-artifacts-29a5dcc4.md`, and Ray's
2026-10-04 §R Q7 ruling (part 2 first, on its own). It says that review mode is unchanged,
that the implementer wrappers and `/gated-implementation` are not gated (follow-up, §R Q5),
that the schema was regenerated one-off (follow-up task, §R Q9), and that pushing is not
required (§R Q4). It ends with the session's attribution trailers. The lane does not push or
ship.

Before dispatch, commit this spec, once ratified, to
`docs/specs/jobdir-dispatch-gate-2026-10-04.md` on the branch. It is the first spec the gate
will govern.

## 7. PREMISES

Every row was read by me in this run. Main-checkout paths are relative to
`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`. `HW/` =
`…/.claude/worktrees/handoff-2026-10-04d/`; `BA/` = `…/.claude/worktrees/codex-banner-ansi/`.
**R** = re-derive against the origin/main you cut from (after #1662 if U3 is accepted, and
after confirming the `eba2e4e4` diff).

| # | Kind | Premise | Citation | R |
|---|---|---|---|---|
| 1 | L | Main checkout HEAD is `main`, and `refs/heads/main` = `36ab6bba9a52…` | `.git/HEAD:1`; `.git/refs/heads/main:1` | |
| 2 | L | `refs/remotes/origin/main` = `eba2e4e4fdae…`, which is NOT local main | `.git/refs/remotes/origin/main:1`; `.git/FETCH_HEAD:1` | |
| 3 | L | origin/main moved `36ab6bba` → `eba2e4e4` by `fetch -q origin: fast-forward`; the local main was not pulled | `.git/logs/refs/remotes/origin/main:211` | |
| 4 | L | Branch `fix/codex-banner-ansi` = commit `2d81c36d` "fix(sdlc-team): settle codex runs whose exec banner is ANSI-coloured", parent `4fdbac59` | `.git/logs/refs/heads/fix/codex-banner-ansi:2`; `.git/logs/HEAD:1057-1058` | |
| 5 | L | That branch inserts `"--color", "never"` with a 2-line comment into the argv at `:819-822`; `dispatch` stays at `:723` | `BA/python/src/dotfiles_setup/sdlc_team.py:819-822`, `:723` | |
| 6 | A | **The banner branch is #1662.** The caller said so; no PR metadata is readable without a shell | — | |
| 7 | L | With the banner change, `generate_dispatch_schema` moves 1063→1067 and `sdlc_team_main` 1089→1093 (+4) | `BA/…/sdlc_team.py:1067`, `:1093`; main `sdlc_team.py:1063`, `:1089` | |
| 8 | L | With the banner change, the test file's `_request`/`_capture_dispatch`/sandbox test stay at 171/185/270; the schema test moves 1701→1706; new `--color` assertions at `:412-414` | `BA/tests/test_sdlc_team.py:171`, `:185`, `:270`, `:412-414`, `:1706` | |
| 9 | A | **`eba2e4e4` does not touch the files in §2.** Unreadable without a shell; the caveat command settles it | — | R |
| 10 | I | `SdlcStatus` = dispatched, spec_missing, cli_missing, invalid_request | `python/src/dotfiles_setup/sdlc_team.py:56-62` | |
| 11 | I | `SdlcTeamDispatch` fields end with `errors: tuple[str, ...] = ()` | `sdlc_team.py:83-98` | |
| 12 | I | `_DispatchState(run_id, status, started_at, errors, pid, argv)`; `_resolved_dispatch` copies them onto the dispatch | `sdlc_team.py:172-180`, `:214-253` | |
| 13 | I | `build_prompt` emits `SPEC FILE:` at `:274` and a REVIEW-only clause at `:262-267` | `sdlc_team.py:256-293` | |
| 14 | L | No `SPEC_UNCOMMITTED`, `spec_uncommitted` or `spec_commit` exists in python/, tests/, schemas/ or .claude/skills/. Control: `SPEC_MISSING\|spec_missing` over the same glob matches 6 lines | Grep (0 hits); control hits `sdlc_team.py:60`, `:748`, `schemas/sdlc-team-dispatch.json:85`, `SKILL.md:75`, `tests/test_sdlc_team.py:340`, `:1666` | |
| 15 | L | `sdlc_team.py` invokes no git today. Control: the same pattern `\bgit\b\|subprocess\.run` matches 6 times in `session_common.py` | Grep over `sdlc_team.py` → 0; over `session_common.py` → 6 | |
| 16 | I | `dispatch`: invalid → INVALID_REQUEST `:727-739`; `is_file()` false → SPEC_MISSING `:741-753`; then `_codex_launcher()` → CLI_MISSING `:755-767`; paths `:769-777` | `sdlc_team.py:723-777` | |
| 17 | I | argv tuple, then a `try` that writes the prompt, unlinks the settlement and `subprocess.Popen`s the supervisor; `except OSError` → INVALID_REQUEST carrying argv | `sdlc_team.py:811-824`, `:826-874` | R |
| 18 | L | `sdlc_team.py` does `import subprocess` (module-level, so `sdlc_team.subprocess` is the global module) | `sdlc_team.py:16` | |
| 19 | P | `_capture_dispatch` monkeypatches `sdlc_team.subprocess.Popen` with a fake that records every call and returns `_DetachedProcess` (no `__enter__`), and `sdlc_team.shutil.which` → codex stub | `tests/test_sdlc_team.py:185-203`, `:28-31` | |
| 20 | P | The IMPLEMENT cell of `test_no_mode_passes_a_sandbox_or_ephemeral_flag` builds an untracked spec via `_request` and asserts only flag absence in `result.argv` | `tests/test_sdlc_team.py:266-286`, `:171-182` | |
| 21 | P | CLI route precedent: `main.run_command` → `SystemExit` 1 and a typed SPEC_MISSING result; `sdlc_team_main` returns 0 only for DISPATCHED | `tests/test_sdlc_team.py:1646-1668`; `sdlc_team.py:1089-1106` | R |
| 22 | L | The committed dispatch schema: 2-space JSON; `required` = run_id, status; enum has 4 values | `schemas/sdlc-team-dispatch.json:1-97`, `:73-76`, `:81-86` | |
| 23 | I | The schema-equality test compares parsed JSON of all three committed schemas with `generate_*_schema()`; `generate_dispatch_schema` = `codec.schema(SdlcTeamDispatch)` | `tests/test_sdlc_team.py:1693-1709`; `sdlc_team.py:1063-1065` | R |
| 24 | P | `_codex_launcher` resolves `mise` and `codex` via `shutil.which`, the boundary the tests fake | `sdlc_team.py:700-720` | |
| 25 | L | CPython 3.14 `subprocess.run` does `with Popen(*popenargs, **kwargs) as process:`, a module-global lookup, so patching `subprocess.Popen` intercepts `run` | `~/.local/share/uv/python/cpython-3.14-macos-aarch64-none/lib/python3.14/subprocess.py:512`, `:554` (that dir is the venv's home, `python/.venv/pyvenv.cfg:1`) | |
| 26 | L | The skill: "`spec_file` must be absolute and exist at dispatch" | `.claude/skills/codex-sdlc-team/SKILL.md:51` | |
| 27 | L | The skill's status list, including `spec_missing` | `.claude/skills/codex-sdlc-team/SKILL.md:72-77`; mirror `.agents/skills/codex-sdlc-team/SKILL.md:75` | |
| 28 | L | `skills-mirror` bare form writes the mirror; hk `skills_mirror_parity` runs `--check` | `mise.toml:1389-1392`; `hk.pkl:733-734` | |
| 29 | L | The mirror rewrites `.claude/skills/`→`.agents/skills/`, `Claude Code`→`Codex`, `Claude`→`Codex` | `python/src/dotfiles_setup/skills_mirror.py:122-125` | |
| 30 | L | The only production callers: `mise run sdlc-team` → `dotfiles-setup sdlc-team` → `sdlc_team_main` | `mise.toml:294-296`; `python/src/dotfiles_setup/main.py:3056-3058` | |
| 31 | L | Contract `workflow.sdlc-team-no-planning-scrub` forbids `PLANNING_DISABLED\|LANE_ENV_OVERRIDES` in `sdlc_team.py` | `python/verification/suites.toml:3045-3052` | |
| 32 | P | The autouse `isolated_git_config` sets `GIT_CONFIG_GLOBAL` (user.name/email) and `GIT_CONFIG_NOSYSTEM=1` for every test | `tests/conftest.py:27-49` | |
| 33 | L | `MAIN_CHECKOUT_TIMEOUT_S = 30` | `python/src/dotfiles_setup/session_common.py:32` | |
| 34 | P | A real-git fixture precedent: `git init -b main`, `-c commit.gpgsign=false commit`, `subprocess.run(..., timeout=10)` | `tests/test_worktree_guard.py:19-22`, `:30-35` | |
| 35 | L | `IMPLEMENT` mode is used by exactly one existing test cell | Grep `IMPLEMENT\|"implement"` over tests/ → `tests/test_sdlc_team.py:268` is the only sdlc hit (the others are `cv.Edge.REOPEN_IMPLEMENT`, which proves the probe matches) | |
| 36 | P | Raising-`Popen` precedent for no-launch arms | `tests/test_sdlc_team.py:326-344`, `:364-372` | |
| 37 | L | Rule 4: "Specs go in `docs/specs/`"; `docs/specs/` is a tracked durable tree | `.claude/rules/agent-artifact-conventions.md:75`, `:48` | |
| 38 | L | `docs/specs/` is not gitignored (no match), while `.agent/` is. Control: the same file matches `.agent/` at `:125` | `.gitignore` Grep → `:41`, `:45`, `:50`, `:125` for `.agent`; 0 for `docs/specs` | |
| 39 | L | Parent §3.8 (ratified body): check order, error strings, review unchanged, one-off regen | `HW/…/spec-jobdir-preservation.md:310-341` | |
| 40 | L | Parent S1-S4 and M8-M9 | same file `:466-479`, `:492-493` | |
| 41 | L | Parent row 64: "P2 turns it red unless its fixture commits the spec". Corrected in §5.1 T0 | same file `:600` | |
| 42 | L | §R rulings: Q7 part 2 first, only `sdlc_team.py`; Q1-Q6, Q8-Q9 recommended options | same file `:676-679` | |
| 43 | A | **`git rev-parse --show-toplevel` prints a symlink-resolved path on macOS.** Not probed; §3.2 resolves both sides, so the spec does not depend on it | — | |
| 44 | A | **msgspec emits the two new `str = ""` fields as `{"type":"string","default":""}`**, by analogy with `prompt_file` at `schemas/sdlc-team-dispatch.json:33-36`. The equality test settles it | — | |

## 8. Open choices for the architect (stop for ratification)

**U1: does the codex-sdlc-team skill (plus its generated mirror) ship with part 2?**
- **Recommended: include it.** PRO: the skill's status list (row 27) would otherwise go stale
  the moment `spec_uncommitted` exists, and a caller following the skill would read the new
  status as undocumented (`.claude/rules/tool-currency-and-native-first.md` rule 5: sync
  describing docs in the same change). The parent §3.9 token is P2-only. CON: it goes beyond
  §R's literal "touches only `sdlc_team.py`" and adds `lint-docs` and mirror steps.
- **Alternative: code, schema and tests only; the skill goes with parts 1+3.** PRO: §R
  literally. CON: a window where the doc and the code disagree.

**U2: the `spec-scribe.md` sentence and the `agent-artifact-conventions.md` rule-4 clause.**
- **Recommended: defer both to the parts-1+3 PR.** PRO: the rule-4 clause also names
  `coordinator-handoff cleanup`, which does not exist yet; keeping both in one place avoids
  editing the rule twice. CON: the scribe definition does not mention the commit step until
  then (the coordinator already does it, §6).
- **Alternative: add only the spec-scribe sentence now.** CON: scope growth for one line.

**U3: when to cut `fix/jobdir-dispatch-gate`.**
- **Recommended: from origin/main after #1662 merges**, then re-derive the R rows. PRO: final
  anchors, no rebase. CON: waits on #1662.
- **Alternative: cut now.** PRO: the hunks are textually disjoint (this spec edits
  `sdlc_team.py` above `:777` plus `build_prompt`/models; #1662 edits `:819-822`), so a
  rebase is likely clean. CON: the anchors at or after `:819` and the test anchors after
  `:409` shift once.

**U4: the refinement of parent S2's "a `Popen` that raises if called".**
- **Recommended: raise only for non-git commands (F1).** PRO: without it the gate's own git
  calls hit the fake, and every refusal arm errors with `AssertionError` instead of returning
  `SPEC_UNCOMMITTED` (row 25). CON: it departs from the parent's literal wording.
- **Alternative: run git through an injected runner parameter on `dispatch`.** PRO: no
  passthrough in the fixture. CON: changes a public signature that `sdlc_team_main` and
  external callers use, for test convenience only.

**U5: premise-verifier.** Parent §4 made it mandatory for the process-lifecycle parts.
- **Recommended: run it over §7 anyway** (it is cheap, and rows 2, 3 and 9 are surprising).
  Alternative: skip it, since part 2 deletes nothing.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): source, tests, schema, skills, rules, the parent spec and the banner-fix worktree (local reads only).
