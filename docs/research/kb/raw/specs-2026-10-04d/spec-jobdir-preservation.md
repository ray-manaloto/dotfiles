# SPEC — job-dir artifact preservation: cleanup gate, committed specs at dispatch, owed-migration inventory

Status: DRAFT by `spec-scribe`, 2026-10-04. NOT ratified as a spec, NOT dispatched. The
decision it implements was ratified; the open choices in §8 still need the architect.

Ratified scope: Ray 2026-10-04, "combine proposals 1-3" of
`docs/research/kb/reports/agents/sdlc-team-review-jobdir-artifacts-29a5dcc4.md:24-58`
(recommendation `:72`). Proposal 4 (native `WorktreeCreate`/`WorktreeRemove` hooks,
`:60-70`) is **out of scope**.

Memory: the spec-scribe local memory directory was empty at the start of this run, so no
prior convention was applied.

**Provenance caveat (read before dispatch).** This lane has no shell, so it could not run
`git show origin/main:<path>`. Every `file:line` in §7 was read from the **working tree of
the main checkout** (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`), whose `HEAD` is
`ref: refs/heads/main` and whose `refs/heads/main` and `refs/remotes/origin/main` both read
`36ab6bba9a52…` (§7 rows 1-2). A dirty working tree cannot be ruled out from file reads alone
(§7 row 60). Before dispatch the coordinator must confirm this prints nothing:

```bash
git -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles diff --stat origin/main -- \
  python/src/dotfiles_setup/coordinator_handoff.py python/src/dotfiles_setup/session_common.py \
  python/src/dotfiles_setup/sdlc_team.py tests/test_coordinator_handoff.py tests/test_sdlc_team.py \
  .claude/skills/coordinator-handoff/SKILL.md .claude/skills/codex-sdlc-team/SKILL.md \
  .claude/agents/spec-scribe.md .claude/rules/agent-artifact-conventions.md mise.toml
```

**Re-derivation is mandatory, not optional (C-0).** Two in-flight changes edit the same files:

- PR #1658 (`fix/coordinator-bgisolation-none`, OPEN, auto-merge armed) edits
  `coordinator_handoff.py`. Its tip `c3569d61` is based on an older main: it lacks
  `handoff_inbox` in the imports and redefines `SHIP_QUEUE`/`HANDOFF_INBOX` locally, so every
  anchor below line ~45 shifts by about +4 after it merges (§7 rows 55-57).
- The ratified-but-undispatched `spec-retire-harness-ship.md` (branch
  `fix/retire-harness-ship`) rewrites the retire predicate, brief steps 3-4 and the
  coordinator-handoff skill (§7 rows 58-59).

Every row marked **R** in §7 must be re-read against the origin/main that contains BOTH, then
`premise-verifier` runs over §7 (this is a process-lifecycle safety gate), and only then is the
lane dispatched.

---

## 1. Objective

**Ratified wording (load-bearing, verbatim from the coordinator's brief of Ray's 2026-10-04
ruling):**

> combine proposals 1-3 from the sdlc review … — (1) a cleanup gate that refuses removing a
> coordinator session while its job dir holds unpreserved artifacts (artifact-specific discard
> override, separate from --accept-inflight); (2) ratified specs must be committed
> (docs/specs/) before sdlc implementation dispatch; (3) the coordinator-handoff launch brief
> inventories the old job dir (tmp/, codex-lane/, dag-binding.json) as owed migrations.

**The failure this prevents.** A coordinator's job dir `~/.claude/jobs/<short-id>/` is
deleted with the session: `tmp/` is "Removed when the session is deleted" (§7 row 46), and
`claude rm` is the documented deletion verb (row 47). On 2026-10-04 five ratified specs and
the `land-1659.log` rc carrier lived only there (rows 49-51). Today:

- `launch` censuses live **processes** only — PID, argv, log path (rows 7, 9) — and never
  enumerates authored artifacts.
- `retire` checks live runs and `inFlight.tasks`, then `claude stop`s (rows 15-17). Nothing
  checks preservation, and no repository verb wraps `claude rm` at all (row 30).
- `sdlc-team` dispatches `implement` mode from any existing file, including ignored
  `.agent/` scratch (rows 34-36).

**Outcome.**

1. **(P1) Cleanup gate.** `mise run coordinator-handoff -- cleanup --old-session <id>` is the
   only routed way to `claude rm` a coordinator. It re-inventories the old job dir and refuses
   (rc 1, zero `claude rm` calls) while any owed artifact is neither verified-preserved in a
   commit nor discarded by an exact `--discard REL=SHA256` with a recorded `--reason`.
   `--accept-inflight` never discharges an artifact. `retire` gains a non-blocking preflight
   warning naming the owed count (§8 Q3).
2. **(P2) Committed authority at dispatch.** `sdlc-team` in `implement` mode refuses (new
   status `spec_uncommitted`, no process launched) unless the spec is a tracked file under
   `<repo>/docs/specs/` whose working-tree bytes equal its blob at that worktree's `HEAD`.
   `review` mode is unchanged, so drafts stay legal.
3. **(P3) Owed-migration inventory in the brief.** `launch` inventories the old job dir —
   `tmp/`, `codex-lane/`, `dag-binding.json`, everything else non-native — and the successor
   brief lists every owed artifact (path, kind, size, digest) plus a cleanup step. An
   unavailable inventory is printed as such and never as "nothing owed"; launch still proceeds.

## 2. Files

Implementation worktree: `<main>/.claude/worktrees/jobdir-preservation`, branch
`fix/jobdir-preservation`, cut from origin/main **after** #1658 and `fix/retire-harness-ship`
both merge (§8 Q7). Never the main checkout. Allowlist (modify only these):

| Path | Change |
|---|---|
| `python/src/dotfiles_setup/job_artifacts.py` | **new**: inventory, classification, preservation/discard verification (§3.1-3.2) |
| `python/src/dotfiles_setup/session_common.py` | add `job_dir()`; `job_record_path` delegates to it (§3.3) |
| `python/src/dotfiles_setup/coordinator_handoff.py` | launch inventory + brief section + step 7; `inventory`/`preserve`/`cleanup` verbs; retire preflight warning (§3.4-3.7) |
| `python/src/dotfiles_setup/sdlc_team.py` | `SPEC_UNCOMMITTED`; committed-spec check in implement mode; two dispatch fields; one prompt line (§3.8) |
| `schemas/sdlc-team-dispatch.json` | regenerated from `generate_dispatch_schema()` only — never hand-edited (§8 Q9) |
| `tests/test_job_artifacts.py` | **new** (§5.1) |
| `tests/test_coordinator_handoff.py` | new arms (§5.1); no existing expected value edited |
| `tests/test_sdlc_team.py` | new arms; the IMPLEMENT cell of `test_no_mode_passes_a_sandbox_or_ephemeral_flag` gets a committed-spec fixture (fixture change, not an expected-value change) |
| `tests/TEST-INDEX.md` | one row for `test_job_artifacts.py` |
| `.claude/skills/coordinator-handoff/SKILL.md` | §2 inventory sentence; §3 cleanup paragraph (§3.9) |
| `.claude/skills/codex-sdlc-team/SKILL.md` | implement-mode committed-spec requirement; `spec_uncommitted` status (§3.9) |
| `.agents/skills/{coordinator-handoff,codex-sdlc-team}/SKILL.md` | **generated** only, by bare `mise run skills-mirror`; never hand-edited |
| `.claude/agents/spec-scribe.md` | one sentence: drafts are scratch; the coordinator commits the ratified spec to `docs/specs/` before implement dispatch |
| `.claude/rules/agent-artifact-conventions.md` | rule 4 gains the committed-before-dispatch clause and the cleanup-gate pointer |
| `mise.toml` | `[tasks.coordinator-handoff]` description and comment name the new verbs; `run` unchanged |
| `docs/specs/coordinator-auto-handoff-2026-10-02.md` | append `## 13.` (or next free number) before `## GitHub repos touched` quoting §1's ratified block |

**Not to touch:** `.claude/settings.json`; `hook_guard.py` (no `claude rm` guard rule, §8 Q6);
`codex_lane.py`, `dag_tick.py`, `dag_project.py` (read for constants only); any
`docs/handoffs/*`; the real `.agent/state/coordinator-handoff/`; anything under `~/.claude/`.

## 3. Interfaces

### 3.1 `job_artifacts.py` — inventory and classification

```python
type ArtifactKind = Literal[
    "native", "scratch", "lane-evidence", "binding", "unknown", "unreadable", "symlink"
]

#: Harness-owned operational files at the job-dir top level; never owed (§7 rows 41, 46).
NATIVE_FILES: Final = frozenset({"state.json", "timeline.jsonl"})
SCRATCH_DIR: Final = "tmp"
LANE_DIR: Final = "codex-lane"          # == dag_tick.CODEX_LANE_DIRNAME (row 39)
BINDING_FILE: Final = "dag-binding.json"  # == dag_project.BINDING_FILENAME (row 40)

@dataclass(frozen=True)
class Artifact:
    rel: str             # POSIX path relative to the job dir
    kind: ArtifactKind
    size: int | None     # None for unreadable / symlink
    sha256: str | None   # full 64-hex; None for unreadable / symlink

class JobDirUnavailableError(OSError): ...

def inventory(job_dir: Path) -> tuple[Artifact, ...]:
    """Every regular file and symlink under job_dir, sorted by rel. Never follows a symlink.
    Raises JobDirUnavailableError when job_dir is absent, not a directory, or unlistable."""

def owed(artifacts: Iterable[Artifact]) -> tuple[Artifact, ...]:
    """Every artifact whose kind is not "native"."""
```

- Import `LANE_DIR`/`BINDING_FILE` from `dag_tick`/`dag_project` if that creates no import
  cycle; otherwise keep the literals and add a test asserting equality with those constants.
- Classification is by path only: top-level `state.json`/`timeline.jsonl` → `native`;
  `tmp/**` → `scratch`; `codex-lane/**` → `lane-evidence`; top-level `dag-binding.json` →
  `binding`; any other path → `unknown`. A symlink anywhere → `symlink`; a file whose bytes
  cannot be read → `unreadable`. `unknown`, `symlink` and `unreadable` are owed like any other.
- A zero-byte file is owed like any other (a name can be evidence, e.g. an rc marker).

### 3.2 `job_artifacts.py` — preservation and discard

```python
@dataclass(frozen=True)
class Preservation:
    rel: str; sha256: str; destination: str; commit: str; recorded_at: str

@dataclass(frozen=True)
class Discard:
    rel: str; sha256: str; reason: str; recorded_at: str   # sha256 == "UNREADABLE" allowed only for kind unreadable/symlink

def verify_preserved(
    artifact: Artifact, record: Preservation, *, repo: Path, runner: Runner | None = None
) -> str | None:
    """None when preserved; otherwise the first failing reason, verbatim in logs."""
```

`verify_preserved` fails closed, in order: digest of record ≠ artifact's current digest;
`git -C repo cat-file -e <commit>^{commit}` nonzero; `git -C repo for-each-ref --contains
<commit> --count=1 --format=%(refname)` prints nothing (commit not reachable from any ref);
`git -C repo cat-file blob <commit>:<destination>` nonzero, or the sha256 of its stdout bytes ≠
`artifact.sha256`. Any `OSError`/timeout → reason `git-unavailable: …`. Every git call has a
timeout (reuse `session_common.MAIN_CHECKOUT_TIMEOUT_S`). A staged-only or uncommitted copy
can never pass: only a commit's tree is read.

Recommended evidence model: an explicit ledger (§8 Q1). The ledger lives in the existing
per-session state file under `state["artifacts"]`:

```json
{"inventory": [<Artifact as dict>, ...],        // written by launch (non-dry-run)
 "preserved": {"<rel>": <Preservation as dict>},
 "discarded": {"<rel>": <Discard as dict>}}
```

All reads/writes go through `session_common.read_state`/`write_state` under `state_lock`,
like every other state mutation in the module.

### 3.3 `session_common.py`

```python
def job_dir(session_id: str, jobs_dir: Path) -> Path:
    """The harness job directory; callers validate the full id first."""
    return jobs_dir / session_id[:SHORT_ID_LEN]
```

`job_record_path` returns `job_dir(...) / "state.json"`; behaviour unchanged.

### 3.4 Launch inventory (P3)

- `BriefContext` gains `job_dir: Path` and
  `artifacts: tuple[Artifact, ...] | str = ()` (a `str` is the unavailability reason).
- `_gather` (or a sibling called from `_launch_locked`) runs
  `job_artifacts.inventory(job_dir(old_session_id, deps.jobs_dir))`. A
  `JobDirUnavailableError` becomes the reason string; it **never** refuses the launch (unlike
  `census-unavailable`, which stays rc 2).
- Non-dry-run launch records `state["artifacts"]["inventory"]` in the same write that records
  `census` and `launch_pending`. Dry-run records nothing (unchanged contract).

### 3.5 Brief rendering (P3)

`successor_brief` adds, inside "Handover record", after the census lines:

```text
- job-dir artifacts owed migration (old job dir `<job_dir>`; specs → docs/specs/, evidence → docs/research/kb/raw/<slug>/):
  - <kind> `<rel>` <size>B sha256:<first 12 hex>[ — LIVE: a recorded run still writes here; settle it first]
  - … (+<K> more — `mise run coordinator-handoff -- inventory --old-session <id> --state-dir <dir>`)
```

- At most `BRIEF_ARTIFACT_LIMIT = 40` rows (argv length bound for `claude --bg`), then the
  overflow line.
- `LIVE` is set when a census `HeavyRun.log_path` resolves inside the job dir and equals that
  artifact's absolute path.
- Zero owed → `  - none owed (native files only)`.
- Unavailable → `  - INVENTORY UNAVAILABLE (<reason>) — this is NOT "nothing owed": run
  inventory before any cleanup; cleanup refuses until it succeeds`.
- New first action **7** (appended, so steps 1-6 keep their numbers):
  `7. Clean up the old session ONLY through the gate — never a bare \`claude rm\`: for each owed
  artifact either commit a copy and record it (\`mise run coordinator-handoff -- preserve
  --old-session <id> --state-dir <dir> --source REL --dest REPO_PATH --commit SHA\`) or discard
  it deliberately, then \`mise run coordinator-handoff -- cleanup --old-session <id>
  --state-dir <dir> [--discard REL=SHA256 ... --reason TEXT]\`. Codes: 0 = removed;
  1 = BLOCKED (owed artifacts, live runs, harness tasks in flight, or bytes changed during
  cleanup); 2 = refused (invalid id/role, missing launch, unreadable state, git unavailable,
  out-of-scope or malformed --discard); 3 = claude rm failed. --accept-inflight never
  discharges an artifact.`
- Keep the f-string `\` continuation discipline: no test-bound token may span a newline in
  the generated brief.

### 3.6 New CLI verbs (`add_subcommands`, `main`)

```text
coordinator-handoff inventory --old-session ID [--json]
coordinator-handoff preserve  --old-session ID --source REL --dest REPO_PATH --commit SHA
coordinator-handoff cleanup   --old-session ID [--discard REL=SHA256 ...] [--reason TEXT]
                              [--accept-inflight] [--dry-run]
```

All three take the existing `--jobs-dir`/`--state-dir` overrides. Each validates the id and
coordinator role first (rc 2 otherwise), exactly as `retire` does.

- **inventory** — read-only; prints one line per artifact (or one JSON array with `--json`),
  owed ones marked, plus ledger status (`preserved`/`discarded`/`OWED`). rc 0, or 2 when the
  job dir is unavailable.
- **preserve** — rescans; `--source` must name an owed inventoried artifact (else rc 2); runs
  `verify_preserved` with a provisional record; on success writes it under
  `state["artifacts"]["preserved"]` and returns 0; on failure prints the reason and returns 1.
  `repo` is `main_checkout(Path.cwd())`.
- **cleanup** — in order, stopping at the first refusal:
  1. identity, role and a valid launch record (rc 2), reusing retire's checks;
  2. **liveness**: any recorded census run still alive with the same argv blocks (rc 1) —
     with **no** `--adopted` escape, because an adopted run may still be appending to a
     job-dir log; `inFlight.tasks` blocks per `_in_flight_blocks` (`--accept-inflight`
     overrides only this). Factor the shared predicate out of `retire` rather than copying it;
  3. inventory A (unavailable → rc 2);
  4. validate every `--discard`: `REL` must be an owed artifact in A and `SHA256` must equal
     its full digest (or be `UNREADABLE` for an `unreadable`/`symlink` artifact), and
     `--reason` must be non-empty when any `--discard` is given — otherwise rc 2, zero calls;
  5. every owed artifact must be discarded (step 4) or carry a ledger `Preservation` that
     passes `verify_preserved` against its CURRENT digest — otherwise rc 1, naming each
     artifact and its reason (`OWED`, `digest changed since preserve`, a git reason …);
  6. inventory B; any difference from A (added, removed, or changed digest) → rc 1
     `bytes changed during cleanup`;
  7. dry-run → log `DRY RUN — would run claude rm <short>` and return 0;
  8. record the discards (with reason and timestamp) under `state["artifacts"]["discarded"]`,
     then run `["claude", "rm", short_id]` with a 60 s timeout through the injectable runner:
     rc 0 → 0; nonzero, missing binary or timeout → 3.
- **CLI seam**: like `_retire_main`, `_cleanup_main` takes a real `reap.snapshot()`; tests
  drive the CLI only with `--dry-run`, and drive `cleanup()` directly with an injected runner.

```python
@dataclass(frozen=True)
class CleanupRequest:
    old_session_id: str
    discards: tuple[tuple[str, str], ...] = ()   # (rel, sha256 | "UNREADABLE")
    reason: str = ""
    accept_inflight: bool = False
    dry_run: bool = False

@dataclass(frozen=True)
class CleanupDeps:
    jobs_dir: Path
    state_dir: Path
    processes: tuple[reap.Process, ...]
    repo: Path
    runner: Runner | None = None

def cleanup(request: CleanupRequest, deps: CleanupDeps) -> int: ...
```

### 3.7 Retire preflight (P1, "early visibility")

After retire's blockers pass and before dry-run/`_stop`, retire inventories the job dir and
logs **one WARNING**: `coordinator-handoff retire: <n> job-dir artifact(s) still owed for
<short>; cleanup will refuse until each is preserved or discarded`, or `… inventory unavailable
(<reason>) …`. It never changes retire's rc, its flags, or its stop decision.

### 3.8 `sdlc_team.py` (P2)

```python
class SdlcStatus(enum.StrEnum):
    ...
    SPEC_UNCOMMITTED = "spec_uncommitted"

class SdlcTeamDispatch(codec.Struct, frozen=True):
    ...
    spec_commit: str = ""   # HEAD sha of the spec's worktree, implement mode only
    spec_path: str = ""     # repo-relative path of the committed spec, implement mode only
```

- After the existing `SPEC_MISSING` check and before `_codex_launcher()`, when
  `request.mode is SdlcMode.IMPLEMENT`, run `_spec_commit_error(spec_file)`, which returns
  `(error, commit, rel)`:
  1. `git -C <spec dir> rev-parse --show-toplevel` → `top` (failure → `spec is not inside a
     git work tree`);
  2. `rel = spec_file.resolve().relative_to(top)` must start with `docs/specs/`
     (`ratified specs live in docs/specs/`);
  3. `git -C top rev-parse --verify HEAD:<rel>` must succeed (`spec is not committed at
     HEAD` — this is the staged-only and untracked case);
  4. sha256 of `git -C top cat-file blob HEAD:<rel>` stdout must equal sha256 of the
     working-tree bytes (`working tree differs from the committed spec`);
  5. `commit = git -C top rev-parse HEAD`.
  Any `OSError`/timeout → `git unavailable: …`. Every call has a timeout.
- Any error → `SPEC_UNCOMMITTED`, `pid=None`, `argv=()`, the error in `errors`, no `Popen`.
- On success the dispatch carries `spec_commit`/`spec_path`, and `build_prompt` adds one line
  after `SPEC FILE:` in implement mode only: `SPEC COMMIT: <sha> <rel>`.
- `review` mode: no git call, no new field values, prompt unchanged.
- Regenerate `schemas/sdlc-team-dispatch.json` from `generate_dispatch_schema()`;
  `schemas/sdlc-team-request.json` must be unchanged.

### 3.9 Docs and skills (required tokens; tests bind to the skill ones)

- **coordinator-handoff SKILL.md §2**: one sentence — launch also inventories the old job dir
  (`tmp/`, `codex-lane/`, `dag-binding.json`) and the brief lists each owed artifact.
  **§3**: a paragraph carrying `mise run coordinator-handoff -- cleanup`,
  `never a bare \`claude rm\``, `--discard REL=SHA256`, `--reason` and
  `--accept-inflight never discharges an artifact`. Do not write capital `Claude` in new
  text (the mirror rewrites it, §7 row 45); lowercase `claude rm` is fine.
- **codex-sdlc-team SKILL.md**: beside "`spec_file` must be absolute and exist at dispatch"
  add `in implement mode it must be committed under docs/specs/`, and add
  `spec_uncommitted` to the status list.
- **spec-scribe.md**: `Drafts may live in scratch; the coordinator commits the ratified spec
  to docs/specs/ before implement dispatch.` The scribe still writes only its scratchpad and
  memory (it has no shell).
- **agent-artifact-conventions.md rule 4**: append `A ratified spec is committed there before
  implement dispatch (sdlc-team refuses otherwise); a coordinator job dir is removed only
  through \`coordinator-handoff cleanup\`.` Keep the file inside its `rule_unscoped` budget.

## 4. Constraints and invariants

- **Ratified scope only.** No `claude rm` guard rule (§8 Q6), no WorktreeRemove hook (P4), no
  change to retire's rc or flags, no new override on retire. The only artifact override is
  `cleanup --discard REL=SHA256 --reason`, modelled on the native exact-value
  `claude rm --discard-unpushed <commit>@<worktree-id>` (§7 row 48).
- **`--accept-inflight` is orthogonal.** On cleanup it overrides only the in-flight blocker;
  it never satisfies, records or implies an artifact disposition.
- **Fail closed everywhere.** Unknown kind, symlink, unreadable file, unavailable job dir,
  unavailable git, unreachable commit, digest mismatch, bytes changed between scans, a live
  census run (adopted or not) — each refuses cleanup. "Inventory unavailable" is never
  rendered or treated as "nothing owed".
- **"Committed" means reachable-commit bytes, nothing weaker.** Indexed-only or
  working-tree-only copies never pass either gate. Published (pushed) is NOT required (§8 Q4).
- **Unchanged behaviour (regression arms in §5):** every existing launch, brief, retire and
  CLI test stays green with no expected-value edits; `review`-mode dispatch is byte-identical
  apart from schema field defaults; the brief's steps 1-6 keep their numbers.
- **Zero-bash-logic.** All logic lives in `python/`; the existing `mise run coordinator-handoff`
  and `mise run sdlc-team` tasks stay the only entry points (no new task, no shell script).
- **Serialization.** Follow each module's existing pattern: `coordinator_handoff` state stays
  dataclass + `session_common.write_state`; `sdlc_team` models stay `codec.Struct`; never call
  msgspec directly.
- **Tests go through public surfaces only** — `job_artifacts.inventory/verify_preserved`,
  `ch.launch(dry_run=True)` for the brief, `ch.retire`/`ch.cleanup` with injected deps,
  `ch.main` with `--dry-run` for CLI arms, `sdlc_team.dispatch`. Real git repositories in
  `tmp_path` (git is a base tool); the process table, `lsof` and `claude` are the only
  injected boundaries. Never touch the real `~/.claude/jobs`, never call a real `claude`.
- **Implementer lane (`codex-sol-implementer`, effort `xhigh`).** `hook_guard` cannot see a
  codex lane, so these bind by this spec alone: it runs **no** pytest, lint, verify,
  lint-docs, `claude`, `gh`, `kill`, `git push`, `git commit`, `mise run ship`, nothing under
  the main checkout, and nothing touching `~/.claude/`. It may run
  `uv run --project python ruff format`/`ruff check` on touched files, bare
  `mise run skills-mirror`, and the schema regeneration named in §8 Q9. No edits outside §2.
- **Safety gate.** Process-lifecycle and deletion paths: `premise-verifier` over §7 before
  dispatch and again over every corrected revision's changed rows; the cold review adds an
  Opus read of every error, empty and timeout branch.
- **Zero inline suppressions.**

## 5. Verification

### 5.1 New test arms

`tests/test_job_artifacts.py`:

- **J1 classification**: a fixture job dir with `state.json`, `timeline.jsonl`,
  `tmp/spec.md`, `tmp/land.log`, `tmp/empty`, `codex-lane/run/lane.log`, `dag-binding.json`,
  `stray.txt`, and a symlink → exactly the kinds of §3.1; `owed()` excludes only the two
  native files. Expected digests are literals computed independently (e.g. sha256 of
  `b"spec\n"` written as a hex literal), never recomputed by the code under test.
- **J2 unavailable**: absent dir and a regular file in place of the dir both raise
  `JobDirUnavailableError`. **Control**: an empty existing dir returns `()`.
- **J3 unreadable**: a `chmod 000` file → kind `unreadable`, digest `None` (skip only when
  running as root, with that stated reason).
- **J4 verify_preserved, real git**: commit `docs/specs/x.md` with the artifact's bytes on a
  branch → `None`. Each fail arm returns a reason: staged-only copy (never committed);
  working-tree edit after commit (wrong bytes at the commit); a commit reachable from no ref
  (create, then delete its branch); destination absent at the commit; record digest ≠
  current digest; `repo` not a git repo (`git-unavailable` or the git reason).

`tests/test_coordinator_handoff.py` (reuse `_job`, `_record_launch`, `_retire`, `_Recorder`,
`_deps`, `_wait_for`):

- **H1 brief lists every owed kind (P3)**: launch dry-run against a job dir holding a spec,
  a ruling, a completed rc log and a `codex-lane/` verdict, plus `dag-binding.json` → each of
  the five rels appears in `argv[6]`, natives do not, step `7.` and
  `never a bare \`claude rm\`` appear.
- **H2 unavailable inventory**: no job dir → launch dry-run still rc 0, brief contains
  `INVENTORY UNAVAILABLE` and `NOT "nothing owed"`; **control**: an empty-of-owed job dir
  prints `none owed (native files only)`.
- **H3 overflow**: 45 owed files → exactly 40 rows plus `(+5 more`.
- **H4 LIVE marker**: a census row whose log is `tmp/land.log` in the job dir → that row
  carries `LIVE`.
- **H5 launch records the inventory** (non-dry-run, `_Recorder(0)`): state has
  `artifacts.inventory` with the owed rels.
- **C1 refuses scratch-only artifacts**: owed `tmp/spec.md` and `tmp/land.log`, no ledger →
  `cleanup` rc 1, `runner.calls == []`, both rels named in caplog.
- **C2 exact committed copies pass**: real repo with both bytes committed on a branch, both
  `preserve` calls rc 0 → `cleanup` (non-dry-run, `_Recorder(0)`) rc 0 and exactly one call
  `["claude", "rm", SESSION[:8]]`.
- **C3 parametrized refusals, each rc 1 or 2 with zero calls**: staged-only copy (preserve
  rc 1); log appended after `preserve` (rc 1, `digest changed`); artifact added after launch
  and after preserve of the rest (rc 1 — rescan, not the launch record); git unavailable
  (`repo` = non-repo dir, rc 2 or the preserve fail); `--discard` naming a rel outside the
  inventory (rc 2); `--discard` with a wrong or 12-char digest (rc 2); `--discard` without
  `--reason` (rc 2); `--accept-inflight` alone with owed artifacts (rc 1).
- **C4 discard passes and is recorded**: `--discard tmp/land.log=<full sha> --reason "copied
  by hand"` plus preserve of the spec → rc 0, one call, state `artifacts.discarded` carries
  the reason.
- **C5 live run blocks even when "adopted"**: real `/bin/sh` child recorded in the census
  (shape of the existing real-process retire test) → cleanup rc 1, zero calls; after it
  exits → rc 0. **Control**: retire with `--adopted <pid>` on the same state still returns 0
  (existing behaviour preserved).
- **C6 changed between scans**: inject a runner whose `git` passthrough appends to
  `tmp/land.log` on its last call before scan B → rc 1 `bytes changed during cleanup`, zero
  `claude` calls.
- **C7 rm failure**: `_Recorder(1)` → rc 3; missing binary / timeout → rc 3.
- **C8 CLI**: `ch.main` `cleanup --dry-run` against a fully preserved fixture → rc 0 and
  `DRY RUN`; against an owed fixture → rc 1. `inventory --json` prints the owed rels.
- **R1 retire preflight is non-blocking**: owed artifacts present → retire rc unchanged (0
  in dry-run) and the WARNING with the count is logged; unavailable job dir → the
  `inventory unavailable` WARNING, rc unchanged.
- **K1 skill tokens**: parametrize over the §3.9 coordinator-handoff tokens against
  `.claude/skills/coordinator-handoff/SKILL.md`; assert no capital `Claude` in the new
  paragraph.

`tests/test_sdlc_team.py`:

- **S1 committed spec dispatches**: real repo, `docs/specs/x.md` committed → implement
  dispatch `DISPATCHED`, `spec_commit` = the repo's HEAD sha, `spec_path` =
  `docs/specs/x.md`, prompt contains `SPEC COMMIT:`.
- **S2 refusals, each `SPEC_UNCOMMITTED`, `pid is None`, `argv == ()`, and a `Popen` that
  raises if called**: identical bytes untracked; staged-only; committed then edited in the
  working tree; committed outside `docs/specs/` (e.g. `.agent/sdlc-specs/x.md` force-added,
  or `docs/research/x.md`); spec outside any git repo.
- **S3 draft arm preserved**: the same untracked spec in `review` mode → `DISPATCHED`, no
  `SPEC COMMIT:` line, empty `spec_commit`.
- **S4 skill token**: `in implement mode it must be committed under docs/specs/` and
  `spec_uncommitted` present in `.claude/skills/codex-sdlc-team/SKILL.md`.
- The existing schema-equality test must pass against the regenerated dispatch schema.

### 5.2 Mutation (FAIL) arms — coordinator, after `git add` of the lane's diff

| Arm | Realistic regression | Must fail |
|---|---|---|
| M1 | Delete the artifact check (step 5) from `cleanup` | C1 and every owed-artifact cell of C3 |
| M2 | Delete the rescan (step 6) | C6 |
| M3 | Let `--accept-inflight` short-circuit the artifact check | C3 accept-inflight cell |
| M4 | Accept a 12-char digest prefix in `--discard` | C3 short-digest cell |
| M5 | Drop the `for-each-ref --contains` reachability check | J4 unreachable-commit cell |
| M6 | Delete the inventory section from `successor_brief` | H1, H2, H3, H4 |
| M7 | Render the unavailable case as `none owed` | H2 |
| M8 | Delete the implement-mode committed check from `dispatch` | S2 (every cell) |
| M9 | Accept working-tree bytes when `HEAD:<rel>` is missing (staged/untracked) | S2 staged-only and untracked cells |

After each arm, `git checkout -- <file>` (safe because staged), then re-run the module green.

### 5.3 Gate bundle (coordinator, host slot, each rc read from the artifact)

1. `uv run --project python pytest tests/test_job_artifacts.py tests/test_coordinator_handoff.py tests/test_sdlc_team.py -x -q > "$LOG" 2>&1; echo "rc=$?" >> "$LOG"`
2. M1-M9 (§5.2).
3. `mise run gate -- run lint` (includes `skills_mirror_parity` and `md_size_budget`),
   `mise run gate -- run pytest`, `mise run gate -- run verify`, `mise run gate -- run lint-docs`.
4. **Real-integration arm** (`.claude/rules/real-integration-evidence.md`): on a disposable
   coordinator-named fixture session created only for this purpose — never e67105a8 or any live
   session — run the public `mise run coordinator-handoff -- cleanup --dry-run` once with an
   owed artifact (rc 1) and once after preserve (rc 0). If no disposable session can be made
   safely, record the capability as unverified rather than substituting a mock.
5. Cold review by ref: the diff is codex-authored, so the reviewer is Opus `cold-reviewer`;
   plus `/code-review` and `/mattpocock-skills:code-review` against this spec.

## 6. Commit

One commit, owner **`caller`** (recommended, §8 Q7): the mutation arms need the diff staged.

Subject: `feat(coordinator-handoff): gate session cleanup on preserved job-dir artifacts;
require committed specs for sdlc implement dispatch`.

Body: cites the review report path and Ray's 2026-10-04 ratification of proposals 1-3; states
that P4 and a `claude rm` guard rule are not implemented and that direct native deletion
(agent view, bare `claude rm`) remains a bypass; lists the §8 rulings. Ends with the session's
attribution trailers. No push and no ship from the lane.

After ratification, this spec itself is committed to
`docs/specs/jobdir-artifact-preservation-2026-10-04.md` before dispatch (it is the first spec
P2 would govern).

## 7. PREMISES

Read by me in this run. Main-checkout paths are relative to
`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`; `HW/` =
`…/.claude/worktrees/handoff-2026-10-04d/`; `BG/` = `…/.claude/worktrees/coordinator-bgisolation/`;
`$CC/` = `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/`.
**R** = must be re-derived after #1658 and `fix/retire-harness-ship` merge.

| # | Kind | Premise | Citation | R |
|---|---|---|---|---|
| 1 | L | origin/main = `36ab6bba9a5297497610f08c114bad7f94fe5558` | `.git/refs/remotes/origin/main:1` | |
| 2 | L | The main checkout is on `main` at the same sha | `.git/HEAD:1`; `.git/refs/heads/main:1` | |
| 3 | L | Ratified proposals 1-3 text, files, fail-closed rules and test/control arms | `HW/docs/research/kb/reports/agents/sdlc-team-review-jobdir-artifacts-29a5dcc4.md:24-58` | |
| 4 | L | Recommendation "combine proposals 1–3"; settled vs live adoption; "tracked" thresholds | same file `:72`, `:74`, `:76` | |
| 5 | L | Census must be taken by the OLD session at launch, inside its own tree | `python/src/dotfiles_setup/coordinator_handoff.py:19-21` | R |
| 6 | L | `STATE_SUBDIR = .agent/state/coordinator-handoff` | `coordinator_handoff.py:108` | R |
| 7 | I | `HeavyRun(pid, argv, log_path)` is the only census record | `coordinator_handoff.py:451-457` | R |
| 8 | L | `harness-output:` prefix set when fd 1 is a `tasks/*.output` file | `coordinator_handoff.py:495-500` | R |
| 9 | I | `census` returns outermost heavy descendants only; no artifact enumeration | `coordinator_handoff.py:585-624` | R |
| 10 | I | `BriefContext` fields (no job dir, no artifacts) | `coordinator_handoff.py:630-642` | R |
| 11 | I | `successor_brief` structure; first actions 1-6; step 4 is the retire gate text | `coordinator_handoff.py:645-723`, `:698-722`, `:711-720` | R |
| 12 | I | `LaunchDeps` carries `jobs_dir` (default `~/.claude/jobs`) and an injectable runner | `coordinator_handoff.py:739-753` | R |
| 13 | I | `_gather` returns census + handoff text; any census failure is a string → launch rc 2 | `coordinator_handoff.py:760-781`, `:891-894` | R |
| 14 | I | Dry-run launch returns before recording; real launch writes `census` + `launch_pending` in one write | `coordinator_handoff.py:912-924` | R |
| 15 | I | `RetireRequest(old_session_id, adopted, dry_run, accept_inflight)`; `RetireDeps(jobs_dir, state_dir, processes, runner)` | `coordinator_handoff.py:1014-1031` | R |
| 16 | I | Blocking predicate: same argv AND not adopted; inFlight gate separate | `coordinator_handoff.py:1119-1124`, `:1132-1147` | R |
| 17 | I | Blockers decided before dry-run and `_stop`; `_stop` runs `["claude","stop",short_id]`, 60 s | `coordinator_handoff.py:1148-1170`, `:86` | R |
| 18 | I | `_in_flight_blocks`: 0 passes; accept overrides positive/unknown with a WARNING | `coordinator_handoff.py:1061-1078` | R |
| 19 | I | `in_flight_tasks` reads the job record's `inFlight.tasks` | `coordinator_handoff.py:1051-1058` | R |
| 20 | I | Subcommands today: decide, release, name, launch, retire, inbox; `--jobs-dir`/`--state-dir` added per child | `coordinator_handoff.py:1176-1257` | R |
| 21 | I | `--accept-inflight` and `--adopted` (`type=int, nargs="*"`) are retire-only flags | `coordinator_handoff.py:1229-1239` | R |
| 22 | I | `main` dispatch; `_retire_main` takes a real `reap.snapshot()` with no runner seam | `coordinator_handoff.py:1260-1298`, `:1319-1334` | R |
| 23 | I | `job_record_path = jobs_dir / session_id[:8] / "state.json"` | `python/src/dotfiles_setup/session_common.py:72-74` | |
| 24 | I | `read_state` (missing → {}, corrupt raises), `write_state` atomic, `state_lock` flock with 10 s default | `session_common.py:104-152` | |
| 25 | I | `main_checkout` = first `git worktree list --porcelain` entry, 30 s timeout | `session_common.py:183-203`, `:32` | |
| 26 | I | `SdlcStatus` values: dispatched, spec_missing, cli_missing, invalid_request | `python/src/dotfiles_setup/sdlc_team.py:56-62` | |
| 27 | I | `SdlcTeamRequest` fields; `mode` defaults to REVIEW | `sdlc_team.py:65-80` | |
| 28 | I | `SdlcTeamDispatch` fields | `sdlc_team.py:83-98` | |
| 29 | I | `build_prompt` emits `SPEC FILE:` and a REVIEW-only clause | `sdlc_team.py:256-293` (`:262-267`, `:274`) | |
| 30 | L | No repository code wraps `claude rm`; it appears only in comments of `dag_tick.py:249` and `dag_project.py:100` | Grep `"claude", "rm"\|claude rm\|…` over `python/src/dotfiles_setup` → those two comment hits plus unrelated `plugin remove` argv in `plugin_remove.py:1273,1401,1428` (the hits prove the probe matches) | |
| 31 | I | `_request_error` checks only absolute path, effort/model, timeout, allowlist | `sdlc_team.py:648-671` | |
| 32 | I | `dispatch`: invalid → `INVALID_REQUEST`; `spec_file.is_file()` false → `SPEC_MISSING`; then `_codex_launcher()` | `sdlc_team.py:723-767` | |
| 33 | L | `sdlc_team.py` invokes no git today | Grep `git\|subprocess\.run` over the file → 0 hits; the same tool returned hits on this file for other patterns (rows 26-32), so the file is readable to the probe | |
| 34 | L | The skill: `spec_file` "must be absolute and exist at dispatch" | `.claude/skills/codex-sdlc-team/SKILL.md:51` | |
| 35 | L | The skill's status list | `.claude/skills/codex-sdlc-team/SKILL.md:72-77` | |
| 36 | L | Spec-contract seven parts and premise-verifier trigger | `.claude/skills/codex-sdlc-team/SKILL.md:158-177` | |
| 37 | I | Schemas are generated by `codec.schema(...)` and an equality test binds the committed JSON | `sdlc_team.py:1058-1070`; `tests/test_sdlc_team.py:1693-1709` | |
| 38 | I | CLI rc is 0 only for DISPATCHED | `sdlc_team.py:1089-1106` | |
| 39 | L | `CODEX_LANE_DIRNAME = "codex-lane"`, colocated in the node's job dir so `claude rm` takes it | `python/src/dotfiles_setup/dag_tick.py:246-251` | |
| 40 | L | `BINDING_FILENAME = "dag-binding.json"`, written inside the node's job dir | `python/src/dotfiles_setup/dag_project.py:99-102` | |
| 41 | L | Measured: a job dir holds only `state.json`, `timeline.jsonl` and `tmp/` (pre-scheduler) | `dag_project.py:88-90` | |
| 42 | L | `codex_lane` run dirs are `jobs_dir / node_id / LANE_DIRNAME`; `lane.log` carries the `EXIT:` marker | `python/src/dotfiles_setup/codex_lane.py:184`, `:429-431` | |
| 43 | L | `sdlc-team` and `coordinator-handoff` mise tasks are thin `uv run … dotfiles-setup …` callers | `mise.toml:294-296`, `:1695-1700` | |
| 44 | L | `skills-mirror` bare form writes the `.agents` mirror | `mise.toml:1389-1392` | |
| 45 | L | The mirror rewrites `.claude/skills/`→`.agents/skills/`, `Claude Code`→`Codex`, `Claude`→`Codex` | `python/src/dotfiles_setup/skills_mirror.py:123-125` | |
| 46 | L | `~/.claude/jobs/<id>/tmp/` is "Removed when the session is deleted"; `state.json` is per-session native state | `$CC/agent-view.md:764-765` | |
| 47 | L | `claude rm` and agent view delete a session; transcript survives via `--resume` | `$CC/agent-view.md:530`, `:697` | |
| 48 | P | Native precedent for an exact-value discard override after a refusal: `claude rm <id> --discard-unpushed <commit>@<worktree-id>` | `$CC/agent-view.md:698` (also `:537`, `:544`) | |
| 49 | L | An active spec pointed into `.agent/sdlc-specs/` | `HW/docs/handoffs/session-2026-10-04d.md:79` | |
| 50 | L | Ratified specs' originals lived in `~/.claude/jobs/e67105a8/tmp/` and "die with `claude rm`" | same file `:81` | |
| 51 | L | `land-1659.log` in the job dir was the rc carrier; never `claude rm` before reading and copying it | same file `:96`, `:126` | |
| 52 | L | Tracked durable trees include `docs/specs/` and `docs/research/kb/raw/`; "Promote anything … a later session will cite" | `.claude/rules/agent-artifact-conventions.md:44-58` | |
| 53 | L | Rule 4: "Specs go in `docs/specs/`" | `.claude/rules/agent-artifact-conventions.md:75` | |
| 54 | L | spec-scribe writes "to the requested scratchpad path"; only scratchpad + memory are writable | `.claude/agents/spec-scribe.md:14-18`, `:22-23` | |
| 55 | L | PR #1658's branch ref = `c3569d61…` | `.git/packed-refs:221` | |
| 56 | L | PR #1658 changes `CROSS_SESSION_SETTINGS` to add `worktree.bgIsolation none` | `BG/python/src/dotfiles_setup/coordinator_handoff.py:110-113` | |
| 57 | L | PR #1658's tip imports `reap, session_common` (no `handoff_inbox`) and defines `SHIP_QUEUE`/`HANDOFF_INBOX` locally, so its anchors differ from main (`census` 589 vs 585, `retire` 1085 vs 1081) | `BG/…/coordinator_handoff.py:45`, `:108-109`, `:589`, `:1085`; main `coordinator_handoff.py:45`, `:585`, `:1081` | |
| 58 | L | `spec-retire-harness-ship.md` edits `coordinator_handoff.py` (retire predicate, brief steps 3-4), its tests, and the coordinator-handoff skill | `HW/docs/research/kb/raw/specs-2026-10-04d/spec-retire-harness-ship.md:73-79` | |
| 59 | L | Its ruling: branch after bgisolation merges; re-derive every anchor first | same file `:473-475` | |
| 60 | A | **The main checkout's working tree equals origin/main for every cited file.** UNVERIFIED: no shell, so no `git diff`. The command in the caveat settles it | — | R |
| 61 | P | Test helpers: `_job` writes `jobs/<short>/state.json`; `_Recorder` passes git through and fakes lsof rc 1; `_deps`; launch dry-run brief is `argv[6]` | `tests/test_coordinator_handoff.py:45-62`, `:436-456`, `:459-477`, `:493-506` | R |
| 62 | P | `_record_launch`, `_retire`, `_wait_for`; real-process retire arm incl. adoption pass | `tests/test_coordinator_handoff.py:570-610`, `:620-652` | R |
| 63 | P | `_request` builds an untracked tmp spec; `_capture_dispatch` fakes only `which` and `Popen` | `tests/test_sdlc_team.py:171-203` | |
| 64 | P | The IMPLEMENT cell of the sandbox test dispatches that untracked spec, so P2 turns it red unless its fixture commits the spec | `tests/test_sdlc_team.py:266-286` | |
| 65 | P | Missing-spec arm uses a raising `Popen` | `tests/test_sdlc_team.py:326-344` | |
| 66 | L | The auto-handoff spec's last numbered section is §11, then `## GitHub repos touched` | `docs/specs/coordinator-auto-handoff-2026-10-02.md:508`, `:543` | R |
| 67 | L | Coordinator-handoff skill: §2 launch text incl. the harness-output line; §3 go-idle text | `.claude/skills/coordinator-handoff/SKILL.md:64-102`, `:100`, `:104-109` | R |
| 68 | A | **The native operational files are exactly `state.json` and `timeline.jsonl`.** Row 41 is a pre-scheduler measurement and row 46 documents only `state.json` and `tmp/`; current harness versions may add others. Fail-closed `unknown` makes a miss visible, not silent | — | |
| 69 | A | **No other repository code removes job dirs.** Row 30 covers only `python/src/dotfiles_setup`; the DAG reaper and `session-orphans` were not read in full for deletion paths | — | |
| 70 | A | **`claude rm <short-id>` accepts the 8-char short id** (as `claude stop` does at row 17). Row 47's table uses `<id>`; not probed | — | |

## 8. Open choices for the architect (stop for ratification)

**Q1 — preservation evidence model.**
- **Recommended: explicit ledger (`preserve` verb records source digest, destination, commit;
  cleanup re-verifies).** PRO: matches the review's mechanism ("record source digest,
  committed destination, revision, disposition", report `:26`); O(1) verification; no false
  match. CON: one more verb and one more step per artifact.
- **Alternative: content search, `git log --all --find-object=<blob>`.** PRO: no ledger, no
  new verb. CON: a tiny file (`rc=0\n`) can match an unrelated committed blob → false
  "preserved"; walks all history per file.

**Q2 — cleanup scope.**
- **Recommended: coordinators only** (ratified wording "removing a coordinator session"; reuse
  `is_coordinator`). PRO: exact ratified scope. CON: DAG nodes' `codex-lane/` and
  `dag-binding.json` (rows 39-40) stay unprotected on their own `claude rm`.
- **Alternative: any bg session.** PRO: covers DAG nodes. CON: beyond ratification; DAG
  tick's own removal path would need wiring.

**Q3 — retire preflight.**
- **Recommended: WARNING only** (§3.7). PRO: the review's "early visibility" (report `:26`);
  no rc change, so no conflict with `spec-retire-harness-ship`'s predicate. CON: a warning can
  be ignored; cleanup is the real gate.
- **Alternative: none.** PRO: zero retire churn. CON: drops part of proposal 1 as written.

**Q4 — "committed" threshold (both gates).**
- **Recommended: reachable commit on this host, not necessarily pushed.** PRO: protects
  same-host deletion, which is the loss path (report `:76`); no network in a gate. CON:
  another clone cannot read it until published.
- **Alternative: reachable from `refs/remotes/origin/*`.** PRO: survives a lost host. CON:
  forces a push before every dispatch/cleanup; stale remote refs read as "absent".

**Q5 — other implementation dispatch routes.** `codex-sol-implementer` wrappers and the
`/gated-implementation` workflow take a spec path but do not go through `sdlc_team.dispatch`.
- **Recommended: file a follow-up issue; ratified (2) names sdlc dispatch.** PRO: scope
  discipline. CON: the most common implement route stays ungated for now.
- **Alternative: also gate them now** (shared `_spec_commit_error` exposed as a CLI check).
  PRO: closes the class. CON: touches agent/workflow files outside ratification.

**Q6 — guard redirect for bare `claude rm`.**
- **Recommended: follow-up issue, not now.** PRO: a redirect to `cleanup` would deny `claude
  rm` of lanes too, which `cleanup` refuses — an outage, not enforcement
  (`.claude/rules/mise-tasks-only.md`). CON: bare `claude rm` and agent view stay a bypass.
- **Alternative: guard only when the target is a coordinator.** CON: the guard sees a command
  string, not a job record; fails open (review `:13`).

**Q7 — commit owner, branch, sequencing.**
- **Recommended: `caller`; branch `fix/jobdir-preservation` cut after BOTH #1658 and
  `fix/retire-harness-ship` merge; re-derive every R row; premise-verifier; then dispatch.**
  PRO: no three-way conflict in `coordinator_handoff.py`. CON: waits on two merges.
- **Alternative: split** — P2 (`sdlc_team.py` only, no shared files) ships first; P1+P3
  after the other two. PRO: P2 lands today. CON: two PRs, two reviews.

**Q8 — empty and native-unknown files.** Scribe default: zero-byte files and unknown paths are
owed (fail closed). Confirm, or name additional native files to exempt.

**Q9 — schema regeneration route.** No mise task regenerates `schemas/sdlc-team-*.json`
(Grep for the filename found only tests and the two skills).
- **Recommended: the lane runs `uv run --project python python -c "…generate_dispatch_schema()…"`
  once and the equality test (row 37) proves it; file a follow-up for a `--write-schemas` task.**
  PRO: smallest change. CON: a one-off command for a recurring workflow
  (`.claude/rules/mise-tasks-only.md`).
- **Alternative: add the task in this change.** CON: scope growth.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — source, tests, skills, rules, handoff, sibling specs (local reads only).
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline Claude Code agent-view docs (local reads only).
