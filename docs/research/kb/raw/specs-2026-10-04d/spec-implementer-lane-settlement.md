# Spec: implementer-lane settlement — durable artifact acceptance kept separate from process settlement

Status: DRAFT for architect ratification (spec-scribe, 2026-10-04). Not dispatched. Open decisions D-1 to D-8 sit at
the end of §4; PREMISES is §7.

**Provenance limit (read first).** This lane has Read/Grep/Glob/Write but **no Bash**, so `git show origin/main:<path>`
could not run. Every citation below comes from the **main-checkout working tree**, which was on branch
`fix/coordinator-bgisolation-none` (clean at session start; its three branch commits touch `hook_guard` and
`coordinator-handoff`). The architect's anchors `sdlc_team.py ~:890` and `lane_result.py ~:807` match the tree I read
exactly, which is a good sign but not proof. **Coordinator action C-0, before dispatch:** run
`git diff --stat origin/main -- <every file in §2>`. It must be empty, or the citations get re-checked.

Memory: spec-scribe local memory was consulted (conventions file). Auto memory is enabled.

---

## 1. Objective

Ratified by Ray on 2026-10-04: proposal 3 of `sdlc-team-review-rgs-rc143-0087b182.md` (handoff-04c worktree, lines 58–66).
Quoted verbatim:

> 3. **Separate durable artifact acceptance from process settlement — preferred class fix.**
>
>    **PRO:** Addresses both observed post-commit terminations. **CON:** Requires a carefully specified lifecycle adapter; more budget or a TERM trap alone is insufficient.
>
>    The credit-fallback reap matched **both Codex and its wrapper shell**, and the subsequent `.rc` read found no file. Recurrence is established; its population-wide frequency is unmeasured.
>
>    Reuse the detached supervisor and atomic receipt machinery in `sdlc_team.py` and `lane_result.py` through an explicit single-implementer interface. Preserve existing dispatcher specialist reconciliation. Update the canonical implementer Markdown/TOML contracts, task/schema interfaces, and `tests/test_sdlc_team.py`; regenerate Astra counterparts through `codex_lane_mirror.py`. Publish implementation delivery promptly; assign independent review to the coordinator. Record true completed/failed/timed-out/abandoned status separately from validated commit/report evidence.
>
>    Required controls: normal exit; TERM before/after valid delivery; missing/truncated or wrong-SHA receipt; dirty mutation restoration; wrapper-shell death; TERM-resistant child; supervisor death; and dispatcher rc0 without specialist evidence. Commit-plus-report must never imply unconditional success.

The defect in concrete terms: the `codex-{sol,astra}-implementer` wrapper reaps its lane once the 1800 s budget runs
out (P-1). It reaps by a pattern built from the `$OUT` path, which also matches the wrapper's own backgrounded shell
(P-2, P-3). That shell is the only thing that writes `$LOG.rc` (P-4), so after the reap there is no receipt. A lane
that had already committed then reports `COMMIT: none — timeout` (P-5), and its work goes unreported.

This change ships three things:

1. **The supervisor owns the process lifecycle; the wrapper only waits.** The implementer lane is launched through
   the same detached, process-group-owning supervisor `mise run sdlc-team` already uses (P-6, P-7). The supervisor
   enforces the budget and writes an atomic settlement. The wrapper never signals any process.
2. **Two separate axes.** Process status is one of `completed`, `failed`, `timed_out` or `abandoned`. Delivery
   evidence is a validated commit plus report, recorded from an atomic **delivery receipt** that the lane publishes
   as soon as it has committed. Neither axis is ever derived from the other.
3. **The reconciliation defect from the same run.** The settlement failed with "parent thread id not found in
   codex.log banner" even though the banner **did** contain the id. Codex 0.160.0 colours the banner keys with ANSI
   SGR escapes, and the parser compares raw text (P-20 to P-23). The parser is fixed. Dispatcher specialist
   reconciliation logic is otherwise left unchanged.

## 2. Files

The lane works ONLY in the worktree `.claude/worktrees/lane-settlement`, never in the main checkout. Every path
below is relative to that worktree.

| # | Path | Change |
|---|---|---|
| F1 | `python/src/dotfiles_setup/lane_result.py` | ANSI-SGR-tolerant `parse_parent_thread_id`. New delivery-receipt model, atomic writer and validator (§3.1). |
| F2 | `python/src/dotfiles_setup/sdlc_team.py` | Generalise the supervisor: add a lane kind, a generic env-override field, a configurable kill grace, and process-group survivor reaping. Add the explicit single-implementer interface (`ImplementerLaneRequest`, `ImplementerDispatch`, `ImplementerSettlement`, `ImplementerStatus`, `dispatch_implementer`, `read_implementer_status`, `build_implementer_prompt`, schema generators). Team path is behaviour-identical. |
| F3 | `python/src/dotfiles_setup/implementer_lane.py` (NEW) | Thin CLI with `dispatch` / `status` / `deliver` subcommands. It is the ONLY place that binds `codex_lane.LANE_ENV_OVERRIDES` to the implementer dispatch (see D-1 for why this is not in F2). |
| F4 | `python/src/dotfiles_setup/main.py` | Register and dispatch the `implementer-lane` subcommand, next to `sdlc-team` (P-30). |
| F5 | `mise.toml` | New `[tasks.implementer-lane]`, a thin caller (`run = "uv run --project python dotfiles-setup implementer-lane"`) placed next to `[tasks.sdlc-team]`. |
| F6 | `schemas/implementer-lane-request.json`, `schemas/implementer-lane-dispatch.json`, `schemas/implementer-lane-settlement.json`, `schemas/lane-delivery-receipt.json` (NEW) | Write each from its `generate_*_schema()` output. Existing `sdlc-team-*.json` and `lane-result.json` must stay byte-identical. |
| F7 | `.claude/agents/codex-sol-implementer.md` | Rewrite the invocation, wait and report sections (§3.4). |
| F8 | `.codex/agents/codex-sol-implementer.toml` | Add the delivery contract to `developer_instructions`. Keep the sentinel (§3.5). |
| F9 | `.claude/agents/codex-astra-implementer.md`, `.codex/agents/codex-astra-implementer.toml` | **Regenerate** with `mise run codex-lane-mirror`. Never hand-edit. |
| F10 | `tests/test_sdlc_team.py` | Controls K1–K10 (§5). |
| F11 | `tests/test_lane_result.py` | Controls K11–K13 (§5). |
| F12 | `python/verification/suites.toml` | `workflow.codex-lane-planning-isolation`: swap the implementer `.md` token for the F3 call-site token. Reword the "six wrappers" description (§4 C7). |
| F13 | `.claude/skills/codex-sdlc-team/SKILL.md` + regenerated `.agents/skills/codex-sdlc-team/SKILL.md` | One short "Implementer lane" subsection: task, statuses, delivery axis. Regenerate the mirror with `mise run skills-mirror`. |
| F14 | `.claude/rules/ai-cli-invocation.md` | Lines 44–45: the implementer pair now dispatches through `mise run implementer-lane`, so only 10 wrappers still carry their own argv and `$LOG.rc`. |
| F15 (only if D-3 = default) | `python/src/dotfiles_setup/codex_agent_parity.py`, `tests/test_codex_agent_parity.py` | Accept the task-dispatch effort pin form for a wrapper that invokes `mise run implementer-lane` (§3.6). |

Out of scope, and the lane must not touch them: `reap.py`; `hook_guard.py`; the other five `codex-sol-*` roles
(D-7); `.claude/workflows/gated-implementation.js` (its consumer contract is preserved instead, §4 C9); `task_plan.md`.

## 3. Interfaces

### 3.1 `lane_result.py` (F1)

```python
_SGR = re.compile(r"\x1b\[[0-9;]*m")          # ANSI Select Graphic Rendition only

def parse_parent_thread_id(log_text: str) -> str | None
    # unchanged signature and contract; strip _SGR from EVERY line before the
    # "OpenAI Codex v" / "--------" / "session id:" comparisons (the value is
    # also prefixed by "\x1b[0m", so strip the whole line, not just the key).

class DeliveryVerdict(enum.StrEnum):
    VALID = "valid"; MISSING = "missing"; INVALID = "invalid"

class DeliveryReceipt(codec.Struct, frozen=True):       # written by the lane via `deliver`
    run_id: str
    commit_sha: str          # full 40-hex
    report_path: str         # absolute
    report_sha256: str       # hex digest of the report bytes at delivery time
    written_at: str          # UTC ISO-8601

class DeliveryEvidence(codec.Struct, frozen=True):      # computed by the supervisor / status reader
    verdict: DeliveryVerdict
    commit_sha: str | None = None
    report_path: str | None = None
    report_sha256: str | None = None
    dirty_paths: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

def write_delivery_receipt(path: Path, receipt: DeliveryReceipt) -> None
    # temp file + Path.replace, the _write_result pattern (P-12); never a partial file
def validate_delivery(workdir: Path, receipt_file: Path, *, run_id: str, base_sha: str) -> DeliveryEvidence
def generate_delivery_schema() -> dict[str, object]     # codec.schema(DeliveryReceipt)
```

Rules for `validate_delivery`. It is pure observation: it **never modifies the worktree** and never restores
anything. It accumulates every error and does not stop at the first.

- Receipt file absent → `MISSING`.
- Undecodable receipt (including a truncated one) → `INVALID` (`receipt undecodable: …`).
- Any of the following → `INVALID`:
  - `run_id` mismatch.
  - `commit_sha` is not 40 lowercase hex, or `git -C workdir cat-file -e <sha>^{commit}` fails.
  - `base_sha` is not a strict ancestor of `commit_sha`.
  - `commit_sha` is not an ancestor-or-equal of the worktree `HEAD`.
  - The report is missing, or its sha256 differs from the receipt.
  - `git -C workdir status --porcelain=v1 --untracked-files=no` is non-empty. List those paths in `dirty_paths`.
- Otherwise → `VALID`.

Git is called through `subprocess.run(("git", "-C", …), capture_output=True, check=False)`. That is the system
boundary, and the tests use a real git repository in `tmp_path`.

### 3.2 `sdlc_team.py` (F2)

```python
class SdlcLaneKind(enum.StrEnum):
    TEAM = "team"; IMPLEMENTER = "implementer"

# _SupervisorPayload gains ONLY defaulted fields (an old payload must still decode):
#   kind: SdlcLaneKind = SdlcLaneKind.TEAM
#   env_overrides: tuple[tuple[str, str], ...] = ()     # generic; team never sets it (D-1)
#   kill_grace_s: float = _TIMEOUT_GRACE_S
#   base_sha: str = ""
#   delivery_file: str = ""
#   codex_pid_file: str = ""

class ImplementerLaneRequest(codec.Struct, frozen=True):
    spec_file: str                 # absolute, must exist
    model: str = SOL_MODEL
    effort: str = "xhigh"
    timeout_s: float = 1800.0      # finite, > 0; an implementer lane ALWAYS has a budget
    run_id: str = ""
    prompt_file: str = ""; output_file: str = ""; log_file: str = ""

class ImplementerDispatch(codec.Struct, frozen=True):
    run_id: str; status: SdlcStatus; pid: int | None = None; argv: tuple[str, ...] = ()
    prompt_file: str = ""; output_file: str = ""; log_file: str = ""
    delivery_file: str = ""; settlement_file: str = ""; workdir: str = ""
    base_sha: str = ""; started_at: str = ""; errors: tuple[str, ...] = ()

class ImplementerSettlement(codec.Struct, frozen=True):
    run_id: str
    status: SdlcSettledStatus                 # PROCESS truth only — never upgraded by delivery
    delivery: DeliveryEvidence                # artifact truth only — never derived from status
    codex_returncode: int | None = None
    codex_pid: int | None = None
    parent_thread_id: str | None = None       # audit only; NO spawn reconciliation for this kind
    base_sha: str = ""
    finished_at: str = ""; duration_s: float = 0.0
    errors: tuple[str, ...] = ()

class ImplementerStatus(codec.Struct, frozen=True):
    run_id: str
    status: SdlcSettledStatus | None          # None = still live (supervisor alive, or orphaned codex)
    supervisor_alive: bool
    codex_group_alive: bool
    delivery: DeliveryEvidence | None = None  # always computed when status is ABANDONED
    settlement: ImplementerSettlement | None = None

def build_implementer_prompt(request: ImplementerLaneRequest, run_id: str, spec_text: str) -> str
def dispatch_implementer(request: ImplementerLaneRequest, repo_root: Path, *,
                         env_overrides: tuple[tuple[str, str], ...]) -> ImplementerDispatch
def read_implementer_status(repo_root: Path, run_id: str, *, pid: int | None) -> ImplementerStatus
def generate_implementer_request_schema() / generate_implementer_dispatch_schema()
    / generate_implementer_settlement_schema() -> dict[str, object]
```

`env_overrides` is a **required keyword with no default**, so no caller can forget the planning scrub.

**`dispatch_implementer`.** Validation works as `_request_error` does (P-31), plus three refusals, each returning
`INVALID_REQUEST`:

- `repo_root` is not a git work tree;
- tracked files are dirty at dispatch (D-6);
- `timeout_s` is `None`.

`base_sha` comes from `git rev-parse HEAD`. The run dir is `.agent/sdlc-runs/<safe id>/`. That reuses
`SDLC_RUNS_DIR` (P-32), so `hook_guard`'s hand-rolled-dispatcher rule already covers it (P-33). The run dir holds:

- `prompt.md`, `output.md`, `codex.log`;
- `delivery.json`;
- `codex.pid`;
- `implementer-settlement.json` (a distinct filename, so `read_status` never decodes it as a team settlement).

The argv is:

```python
(*launcher, "--sandbox", "danger-full-access", "--model", model,
 "-c", f'model_reasoning_effort="{effort}"', "-C", workdir, "-o", output_file, "-")
```

It is the wrapper's current argv, and ai-cli-invocation pins this sandbox for implementers (P-34). The launcher is
`_codex_launcher()`. Never `--ephemeral`.

The supervisor is spawned exactly as the team supervisor is: `start_new_session=True` and DEVNULL stdio (P-6).

**`_supervise`.**

- The codex child gets `env={**os.environ, **dict(payload.env_overrides)}`. With empty overrides this equals the
  inherited environment, so the team path is behaviour-identical.
- For `IMPLEMENTER` only:
  - right after `Popen`, atomically write `codex.pid`;
  - at the end, run `lane_result.validate_delivery`;
  - then atomically write `ImplementerSettlement`.
- For `TEAM`: `_write_lane_receipts` and `reconcile_spawns` run exactly as today (P-8), and `SdlcTeamSettlement` is
  unchanged.
- The implementer status map:

  | Process outcome | Status |
  |---|---|
  | rc 0 | `COMPLETED` |
  | rc ≠ 0 | `FAILED` |
  | budget expiry | `TIMED_OUT` |
  | `OSError` | `FAILED` |

  The status is never changed by `delivery.verdict`.

**`_terminate_process_group(process, grace_s)`.** Today it waits only for the group leader, so a TERM-ignoring
descendant outlives a leader that exited on TERM (P-9). New behaviour:

1. TERM the group.
2. Wait up to `grace_s` for the leader.
3. Then probe the group with `os.killpg(pgid, 0)`. If it is still alive, or the leader did not exit, send SIGKILL to
   the group.
4. Re-probe within a bounded loop of at most `grace_s`. Record surviving members in `errors` and never hang.

This applies to both kinds; it only strengthens the team's timeout path.

**`read_implementer_status`** returns:

| Condition | Result |
|---|---|
| Settlement present | `status` comes from the settlement. |
| No settlement, supervisor alive | `status=None`. |
| No settlement, supervisor dead, `codex.pid` group alive | `status=None`, `codex_group_alive=True`. This is **orphaned**: never `ABANDONED`, and never signalled. |
| No settlement, supervisor dead, codex group gone | `ABANDONED`, plus `delivery=validate_delivery(...)` computed now. |

`ABANDONED` is never written to disk (P-10).

### 3.3 `implementer_lane.py` CLI (F3, F4, F5)

```text
mise run implementer-lane -- dispatch --spec <abs> --run-id <id> --timeout-s <s> --model <slug> --effort <id>
    -> stdout: ImplementerDispatch JSON; rc 0 iff status == dispatched, else 1
mise run implementer-lane -- status --run-id <id> --pid <supervisor pid>
    -> stdout: ImplementerStatus JSON; rc 0 whenever an answer was produced (live, settled or abandoned), 2 on bad args
       (callers read FIELDS, never the rc, as the outcome)
mise run implementer-lane -- deliver --run-id <id> --commit <sha> --report <abs path>
    -> validates commit exists + report exists, computes sha256, write_delivery_receipt(); stdout: receipt JSON;
       rc 0 on write, 1 on validation failure (nothing written)
```

`dispatch` calls `sdlc_team.dispatch_implementer(..., env_overrides=tuple(LANE_ENV_OVERRIDES.items()),)`, and that
line is the F12 contract token. `--repo-root` defaults to cwd, as `sdlc-team` does.

### 3.4 Wrapper contract (F7) — what `.claude/agents/codex-sol-implementer.md` must say

- **Setup.** Unchanged in substance: the `LANE_ID` claim and its validation. The spec is written VERBATIM to an
  absolute `.agent/kb/raw/codex-sol-implementer-spec-$LANE_ID.md`; the wrapper still never rewrites or summarises
  it. The dispatch `TIMEOUT:` line maps to `--timeout-s` (default 1800).
- **Launch.** One foreground call:
  `mise run implementer-lane -- dispatch --spec "$SPEC" --run-id "$LANE_ID" --timeout-s "$TIMEOUT" --model gpt-6.1-sol --effort xhigh`.
  Print the dispatch JSON, and re-assign the supervisor `pid` and `settlement_file` literals in every later call.
- **Wait.** Repeat bounded slices until settled, ABANDONED, or overdue. Each slice is one Bash call with timeout
  `600000`:

  ```bash
  mise run bounded-wait -- --deadline 540 --file "<settlement_file>"; echo "wait_rc=$?"
  mise run implementer-lane -- status --run-id "<LANE_ID>" --pid "<pid>"
  ```

  Overdue means the settlement is still absent more than `TIMEOUT + 300` s after dispatch. The wrapper then reports
  `STATUS: partial — supervisor overdue` **without signalling anything**.
- **Never.**
  - **The wrapper never runs `mise run reap`, `kill`, `pkill` or `pgrep`-and-kill.** The supervisor owns
    termination.
  - The old background launch, `$LOG.rc` and the reap block are deleted.
  - Keep "A SLOW lane is not a FAILED lane".
  - Keep "Never substitute your own reasoning for a failed codex call" verbatim (parity marker, P-26).
- **Early-death relaunch rule.** Kept, re-keyed: `ABANDONED` within the first 60 s with a clean `git status` gets
  one relaunch with `LANE_ID="${LANE_ID}-r1"`.
- **Report.** The fields are:

  ```text
  STATUS: complete | partial | timeout | dissent | unavailable
  LANE: <LANE_ID> — <run dir>
  RC: <settlement.codex_returncode, or "none — <abandoned | orphaned | overdue>">
  SETTLEMENT: <settlement.status> — <settlement.errors joined, or "none">
  DELIVERY: valid <commit_sha> <report_path> | invalid — <errors; dirty_paths> | missing
  GATES: <every EXIT= line from codex's output, verbatim; or "none reported — <why>">
  COMMIT: <commit_sha> | none — <reason>
  FILES / PREMISES / DISSENT: (as today)
  PROCESS: <the final `implementer-lane status` JSON — supervisor_alive and codex_group_alive must both be false, or say why>
  ```

  Mapping:

  | Settlement | Delivery / output | Wrapper `STATUS` |
  |---|---|---|
  | `completed` | `valid`, and no refusal in output | `complete` |
  | `completed` | any delivery, and a refusal in output | `dissent` |
  | `completed` | `missing` or `invalid` | `partial` |
  | `failed` | any | `partial` |
  | `timed_out` | any | `timeout`, **always**, even when DELIVERY is `valid` |
  | `abandoned`, orphaned, or overdue | any | `partial` |

  `COMMIT:` carries the sha **only when DELIVERY is `valid`** (D-4). Otherwise it reads `none — <reason>`, a value
  with spaces, so the gated-implementation regex does not capture it (P-28).

### 3.5 Codex-side contract (F8, and the generated prompt)

`build_implementer_prompt` emits the spec verbatim, then a separator, then the LANE CONTRACT block below. The block
must be in the prompt itself, because the `.toml` `developer_instructions` reach only *spawned* sessions, not a
top-level `codex exec` (P-19).

The LANE CONTRACT block is fixed text:

1. When, and only when, your commit exists and your report file is written, immediately run
   `mise run implementer-lane -- deliver --run-id <id> --commit <full sha> --report <absolute report path>`.
   Then end with your final report.
2. Do not spawn, wait for, or run any review after delivery. Independent review belongs to the coordinator.
3. Restore every mutation before delivery. A delivery is refused while any tracked file is modified.
4. Never pipe a command into a pager. Capture its rc.
5. A refusal is a complete run. Do not deliver.

Add the same five points to the `.toml` `developer_instructions`. Keep the sentinel line (P-27).

### 3.6 Parity gate (F15, only if D-3 = default)

`MD_REQUIRED_MARKERS` requires the literal `model_reasoning_effort="xhigh"` in every wrapper (P-26), so a wrapper
that passes `--effort xhigh` to the task would fail. Accept `--effort xhigh` as the effort pin **only** for a
wrapper whose flattened body contains `mise run implementer-lane -- dispatch`. Keep `--model <family model>`
required for all lanes. It is already satisfied by the §3.4 launch line, and the mirror rewrites it to
`gpt-6-astra` for astra (P-18).

## 4. Constraints and invariants

- **C1 — Two axes, never fused.** `ImplementerSettlement.status` is process truth and `delivery.verdict` is artifact
  truth. No code path sets one from the other. `TIMED_OUT` + `VALID` is a legal, distinct, reportable state, and it
  is never `COMPLETED` and never `STATUS: complete`. This is Ray's ratified sentence: "Commit-plus-report must
  never imply unconditional success."
- **C2 — Team reconciliation unchanged.** `reconcile_spawns`, `_write_lane_receipts`, `SdlcTeamSettlement`,
  `read_status` and the `sdlc-team-*.json` schemas stay byte-identical in behaviour and schema. The only team-path
  changes are these two:
  - the SGR-tolerant banner parse in F1;
  - the stronger group-kill in `_terminate_process_group`.

  Every existing `test_sdlc_team.py` / `test_lane_result.py` test stays green **unmodified**, apart from one
  allowed edit: K10 may add new fixtures.
- **C3 — No destructive recovery.** Nothing in this change restores, resets, stashes or checks out worktree files.
  Dirty state is recorded, never repaired. Nothing outside the supervisor's own codex process group is ever
  signalled.
- **C4 — Atomic artifacts.** The settlement, `codex.pid` and the delivery receipt are each published by temp file +
  `replace` (P-11, P-12). `ABANDONED` stays derived-only (P-10).
- **C5 — No `PLANNING_DISABLED` / `LANE_ENV_OVERRIDES` token in `sdlc_team.py`.** The
  `workflow.sdlc-team-no-planning-scrub` regex_forbid enforces this (P-15). The implementer scrub is bound in F3 only.
- **C6 — Argv invariants.** Never `--ephemeral`. `--sandbox danger-full-access` is explicit for the implementer.
  The model and effort are pinned. The trailing `-` is supplied (P-34).
- **C7 — Contract surgery is exact.** In `workflow.codex-lane-planning-isolation`, make these changes:
  - replace the `".claude/agents/codex-sol-implementer.md" = ["PLANNING_DISABLED=1 mise exec -- codex exec"]` entry
    with `"python/src/dotfiles_setup/implementer_lane.py" = ["env_overrides=tuple(LANE_ENV_OVERRIDES.items()),"]`;
  - swap that path in `paths` the same way;
  - reword "each of the six `.claude/agents/codex-sol-*.md` wrappers" to five wrappers plus the implementer's typed
    task.

  The bare `tokens` union keeps `PLANNING_DISABLED=1 mise exec -- codex exec`, which the other five still carry
  (P-14).
- **C8 — Generated files are regenerated, never edited.** Astra lanes: `mise run codex-lane-mirror`. Skill mirror:
  `mise run skills-mirror`.
- **C9 — Consumer contract preserved.** gated-implementation reads `^COMMIT:\s*(\S+)\s*$` and branches on its
  absence (P-28). The report must keep a single-token sha line on VALID delivery, and a multi-word `none — …` line
  otherwise.
- **C10 — Repo policies.**
  - Zero inline suppressions.
  - All serialization goes through `codec`.
  - No new `.sh` file.
  - Tests mock only system boundaries (`Popen`, `os.killpg`, the clock) or use real `sh`/`git` processes.
  - Every assertion has a realistic fail arm.
  - Real-process tests are bounded, so no test can hang. Wrap each in a subprocess or `wait` timeout of at most
    30 s, and make the grace configurable through `kill_grace_s`.
- **C11 — Worktree.** The lane implements in `.claude/worktrees/lane-settlement`. It never edits the main checkout
  and never writes `task_plan.md`. `findings.md` and `progress.md` are append-only.

### Open decisions for the architect (each has a recommendation; the spec stops here for ratification)

- **D-1 — Generic env-override field in the shared supervisor.** `workflow.sdlc-team-no-planning-scrub` forbids the
  tokens in `sdlc_team.py` and records Ray's ruling that team lanes SEE the plan (P-15). The implementer lane must
  NOT see it (P-16). **Recommended:** a generic `env_overrides` payload field, set only by F3, with K9 pinning that
  team dispatch leaves it empty. **Alternative:** move the whole implementer interface out of `sdlc_team.py`. That
  needs the private `_SupervisorPayload` / `_payload_argument` exported, which is a larger surface. Ray's ruling
  needs confirming here, because a generic field is within the regex's letter, and its spirit needs his reading.
- **D-2 — Hand-written models vs. the codegen policy.** python/AGENTS.md says new models are "generated, never
  hand-written" (R16/D23, P-35). But only one codegen job exists, the pilot (P-36), and every `sdlc_team` /
  `lane_result` model is a hand-written `codec.Struct`. **Recommended:** hand-written here, for one consistent
  module, with a follow-up issue to migrate the sdlc models together. **Alternative:** four new schema-first codegen
  jobs, which is heavier and splits each model family across two styles. This needs Ray's ruling.
- **D-3 — Parity effort-marker form (§3.6).** **Recommended:** the narrow exception (F15). **Alternative:** the
  CLI accepts a literal `-c model_reasoning_effort="xhigh"` passthrough flag. No gate change, but it is a mimicry
  flag on a typed task.
- **D-4 — Surface the sha on `timeout` + `valid`.** This changes gated-implementation's behaviour. A timed-out lane
  that delivered now proceeds to Gates and Review instead of `implementer-no-commit` (P-28, P-29). **Recommended:**
  yes. This is proposal 1's "qualify the recovered commit independently", and `STATUS: timeout` stays visible.
- **D-5 — The ANSI fix.** Two questions:
  - (a) **Recommended:** strip in the parser only. Optionally also pass a no-colour flag, but **only after**
    coordinator action C-2 proves one exists. The offline codex docs show no colour flag (P-24).
  - (b) **Recommended: split F1's parser hunk + K11/K12 into a first, tiny PR.** Every team dispatch on codex
    0.160.0 currently settles `failed` (P-22), so the fix should not wait on the larger lifecycle work.
- **D-6 — Refuse a dirty tracked tree at dispatch.** **Recommended:** yes. Otherwise the `dirty_paths` evidence
  cannot tell lane mutations from pre-existing edits.
- **D-7 — The other five roles.** advisor, operator, adversarial-critic, claude-code-expert and staleness-auditor
  carry the same `$OUT` background launch and `reap --pattern "$OUT" --kill` (P-37), so they are exposed to the same
  wrapper-shell kill. **Recommended:** out of scope here; file a follow-up issue naming this spec as the pattern.
- **D-8 — Orphan detection for the team kind.** **Recommended:** no. `codex.pid` and orphan status apply to
  `IMPLEMENTER` only, which keeps C2 strict.

## 5. Verification

### Lane-run gates

The lane runs these and reports each `EXIT=` verbatim:

```bash
uv run --project python pytest tests/test_lane_result.py tests/test_sdlc_team.py -x -q -n 0 > /tmp/targeted.log 2>&1; echo "EXIT=$?" >> /tmp/targeted.log
# only if D-3 = default:
uv run --project python pytest tests/test_codex_agent_parity.py tests/test_codex_lane_mirror.py -x -q -n 0 > /tmp/parity.log 2>&1; echo "EXIT=$?" >> /tmp/parity.log
mise run codex-lane-mirror > /tmp/mirror.log 2>&1; echo "EXIT=$?" >> /tmp/mirror.log
mise run skills-mirror > /tmp/skills-mirror.log 2>&1; echo "EXIT=$?" >> /tmp/skills-mirror.log
```

The lane commits only when the targeted run is `EXIT=0`. It then delivers.

### Coordinator-run gates (after the lane, in the worktree, never by the lane)

1. Targeted pytest re-run.
2. `mise run gate -- run lint`.
3. `mise run gate -- run pytest`.
4. `mise run gate -- run verify`. This covers F12 and `workflow.sdlc-team-no-planning-scrub`.
5. `mise run gate -- run lint-docs`. This covers F7, F13 and F14.
6. `mise run codex-lane-mirror -- --check` and `mise run skills-mirror -- --check`.
7. `mise run codex-agent-parity`.

### Required controls

Each control must go red under the named realistic mutation. The lane applies each mutation, records the red
`EXIT=`, and restores with `git diff --exit-code` on the touched file.

| K | Control (test file) | Pass arm | Realistic mutation → must go red |
|---|---|---|---|
| K1 | Normal exit (sdlc) | A real `sh` fake codex commits in a temp git repo, writes the report, runs `deliver` (via `sys.executable -m dotfiles_setup.implementer_lane deliver`) and exits 0. Result: `COMPLETED` + `VALID`. A second arm exits 0 with no receipt: `COMPLETED` + `MISSING`. | Treat a missing receipt as `VALID` → arm 2 red. |
| K2 | TERM before valid delivery (sdlc) | The fake codex sleeps with no receipt; `timeout_s=1`. Result: `TIMED_OUT` + `MISSING`, and the codex group is gone. | Delete the timeout branch's `_terminate_process_group` call → red (bounded). |
| K3 | TERM after valid delivery (sdlc) | The fake codex commits, reports, delivers, then sleeps; `timeout_s` is short. Result: `TIMED_OUT` + `VALID` with the right sha, and `status != COMPLETED`. | Set `status = COMPLETED` when delivery is `VALID` → red. |
| K4 | Missing / truncated / wrong-SHA receipt (lane_result) | Real git repo cases: (a) absent → `MISSING`; (b) first half of valid receipt bytes → `INVALID` "undecodable"; (c) 40-hex sha not in the repo → `INVALID`; (d) report edited after delivery → `INVALID` sha256 mismatch; (e) `commit == base` → `INVALID`. | Delete the `cat-file` check → (c) red. Delete the report-hash comparison → (d) red. |
| K5 | Dirty-mutation restoration (lane_result + sdlc) | (a) The lane delivers, then modifies a tracked file and exits: `INVALID`, `dirty_paths` names it, and the file's bytes are **unchanged** by the supervisor. (b) It modifies then restores: `VALID`. | Delete the porcelain check → (a) red. Add any restore call → the byte-preservation assertion is red. |
| K6 | Wrapper-shell death (sdlc) | A helper python process started in **its own session** calls `dispatch_implementer` and prints the dispatch. The test then `os.killpg`s that session (simulating the reap that hit the wrapper shell). The detached supervisor still writes `implementer-settlement.json`. | Remove `start_new_session=True` from the supervisor `Popen` in dispatch → no settlement within the bound → red. |
| K7 | TERM-resistant child (sdlc) | (a) The leader ignores TERM (`trap '' TERM`): SIGKILL is sent, `codex_returncode == -9`, and the group is gone. (b) The leader exits on TERM, but a TERM-ignoring grandchild stays in the group: after settlement, `os.killpg(pgid, 0)` raises `ProcessLookupError` (bounded poll). | Delete the post-leader group probe / SIGKILL → (b) red. Today's code fails (b), so this arm is red-first. |
| K8 | Supervisor death (sdlc) | Dispatch with a long-sleeping fake codex, then SIGKILL the supervisor. (a) `read_implementer_status` returns `status=None`, `codex_group_alive=True`, never `ABANDONED`. (b) After the test's own cleanup kills that group, `ABANDONED` and `delivery` computed. A variant where the fake had delivered first gives `ABANDONED` + `VALID`. | Drop the codex-liveness branch → (a) red. |
| K9 | Planning scrub binds only the implementer (sdlc) | (a) The implementer path's real child sees `PLANNING_DISABLED=1`. Prove it through `implementer_lane` dispatch with a fake codex that writes `$PLANNING_DISABLED` to a file. (b) A team `dispatch` payload has `env_overrides == ()`. Decode it from the captured `Popen` argument. | Drop `env=` from the codex `Popen` → (a) red. Set overrides in team dispatch → (b) red, and the regex_forbid also fails. |
| K10 | Dispatcher rc 0 without specialist evidence (sdlc) | The existing `test_supervisor_fails_when_claimed_specialist_has_no_child_session` stays green unmodified. Add: a team-kind payload with rc 0, a claimed specialist and no rollouts gives `SdlcTeamSettlement` `FAILED`. An implementer-kind payload's settlement carries no specialist fields and runs no reconciliation. | Route `TEAM` through the implementer settle branch → red. |
| K11 | ANSI banner parse (lane_result) | Fixture built from the exact run-0087b182 bytes (codex.log lines 1–11, ESC = `\x1b`) gives `01a1068f-53a0-7540-a774-b8222ab83864`. The existing plain-banner tests stay green. | Delete the SGR strip → red. |
| K12 | ANSI banner end-to-end (sdlc) | `_run_supervisor` with the coloured banner: `settlement.parent_thread_id` is set and the "not found in codex.log banner" error is absent. | Same mutation → red. |
| K13 | Schemas (lane_result + sdlc) | Each new `schemas/*.json` equals its generator. The existing three `sdlc-team-*.json` and `lane-result.json` are unchanged. | Add a field without regenerating → red. |

### Real integration arm

The coordinator runs this; it costs credits, per real-integration-evidence. Once, in a scratch worktree, run
`mise run implementer-lane -- dispatch` on a trivial ratified spec (one-line doc edit + commit + deliver). Record:

- `completed` + `valid`;
- a second dispatch with `--timeout-s 60` on a spec that sleeps after delivering: `timed_out` + `valid`;
- `status` showing `codex_group_alive=false`.

### Coordinator actions this lane could not perform (no Bash)

- **C-0:** the `origin/main` diff check from the header.
- **C-1:** `git log -1 --format=%H origin/main` recorded as the dispatch base.
- **C-2:** `mise exec -- codex exec --help`. Is there a colour/`--color never` flag? This settles D-5(a).
- **C-3:** choose the lane budget. This lane is itself subject to the defect it fixes. Dispatch it with
  `TIMEOUT: 5400` and treat any post-commit reap per proposal 1.
- **C-4:** file the D-7 follow-up issue if ratified.

## 6. Commit

One commit, on a branch in `.claude/worktrees/lane-settlement`, made by the lane after the targeted gate is green:

```text
fix(sdlc): settle implementer lanes in the detached supervisor; delivery evidence is a separate axis

The codex-{sol,astra}-implementer wrappers reaped their own lane at the 1800 s
budget by an $OUT pattern that also matched the wrapper shell, so a lane that
had already committed lost its .rc receipt and reported no commit. The lane now
launches through `mise run implementer-lane`, which reuses sdlc_team's detached
process-group supervisor and records process status (completed / failed /
timed_out / abandoned) separately from a validated delivery receipt (commit +
report sha256 + clean tracked tree). Commit-plus-report never implies success.

Also strips ANSI SGR from the codex exec banner before reading the session id:
codex 0.160.0 colours the banner keys, which failed every team settlement with
"parent thread id not found in codex.log banner".
```

If D-5(b) is ratified, the parser hunk, K11 and K12 ship first as their own commit/PR:
`fix(lane-result): read the codex session id through ANSI-coloured banners`.

## 7. PREMISES

Legend:

- **V** — verified by my own Read/Grep this run, at the cited line (working tree; see the provenance limit).
- **C/R** — confirmed / refuted, with a control arm.
- **A** — assumed or inherited, with the reason.

| ID | Premise | St | Citation |
|---|---|---|---|
| P-1 | The wrapper's third end-signal is the budget (default 1800 s), and the wrapper reaps on it. | V | `.claude/agents/codex-sol-implementer.md:37-38`, `:216-224` |
| P-2 | The reap matches on `"$OUT"` with `--kill`. | V | `.claude/agents/codex-sol-implementer.md:221-222` |
| P-3 | `reap.select` matches the pattern with `re.search` over the full command line, unless `--full-match` is given. A shell whose argv contains the `$OUT` literal therefore matches. | V | `python/src/dotfiles_setup/reap.py:307-313` |
| P-3a | The wrapper's backgrounded shell carries the `$OUT` path literally in its command line, because each Bash call re-assigns the printed literals. | A | Inferred from `codex-sol-implementer.md:140-142` + `:154-158`. Harness `ps` argv shape not probed (no Bash). |
| P-4 | `$LOG.rc` is written only by the same shell that ran codex (`…; echo "$?" > "$LOG.rc"`). It is the only trusted completion signal. | V | `.claude/agents/codex-sol-implementer.md:158`, `:166-170` |
| P-5 | The report's `COMMIT:` is `none` on timeout. | V | `.claude/agents/codex-sol-implementer.md:273` |
| P-5a | The rgs lane was reaped about 5 min after committing (commit 04:40:47, reap 04:46:00, PID 94562, one TERM, rc 143). | A | Inherited: review report `:34-36`; transcripts not re-read. |
| P-5b | The credit-fallback reap matched codex AND its wrapper shell; the `.rc` read then found no file. | A | Inherited: review report `:62`; transcript `agent-aa041f8b1a94ed0b3.jsonl:48` not re-read. |
| P-6 | Team dispatch starts the supervisor with `start_new_session=True` and DEVNULL stdio. | V | `python/src/dotfiles_setup/sdlc_team.py:848-861` |
| P-7 | The supervisor starts codex in its own session/process group and enforces `timeout_s` via `wait(timeout=…)`. | V | `sdlc_team.py:1003-1024` |
| P-8 | A team rc-0 run is downgraded to FAILED when reconciliation is inconsistent. | V | `sdlc_team.py:1029-1033` |
| P-9 | `_terminate_process_group` waits only for the leader; SIGKILL fires only if the leader outlives the 5 s grace (`_TIMEOUT_GRACE_S`). | V | `sdlc_team.py:890-901`, `:186` |
| P-10 | ABANDONED cannot be written; `read_status` derives it from a missing settlement plus a dead supervisor pid. | V | `sdlc_team.py:682-687`, `:904-925` |
| P-11 | `_atomic_write` is a temp file + `replace`. | V | `sdlc_team.py:674-679` |
| P-12 | `lane_result._write_result` is atomic (temp + `replace`). This is the architect's "~:807". | V | `python/src/dotfiles_setup/lane_result.py:806-812` |
| P-13 | The team argv passes no `-s` and no `--ephemeral`, pins model and effort, and ends in `-`. | V | `sdlc_team.py:811-824` |
| P-14 | `workflow.codex-lane-planning-isolation` requires `PLANNING_DISABLED=1 mise exec -- codex exec` in `codex-sol-implementer.md` (and five siblings). | V | `python/verification/suites.toml:1879-1923` (implementer entry `:1916-1918`) |
| P-15 | `workflow.sdlc-team-no-planning-scrub` regex-forbids `PLANNING_DISABLED\|LANE_ENV_OVERRIDES` in `sdlc_team.py`, per Ray's ruling. | V | `suites.toml:3036-3043` |
| P-16 | `LANE_ENV_OVERRIDES = {"PLANNING_DISABLED": "1"}`, merged at the codex_lane call site. | V | `python/src/dotfiles_setup/codex_lane.py:140`, `:480` |
| P-17 | The astra mirror is generated from the sol `.md`/`.toml` by substituting the prefix and model only. | V | `python/src/dotfiles_setup/codex_lane_mirror.py:59-74`; task `mise.toml:1394-1397` |
| P-18 | The mirror rewrites `gpt-6.1-sol` → `gpt-6-astra`, so `--model gpt-6.1-sol` in the sol wrapper becomes the astra pin. | V | `codex_lane_mirror.py:32-33`, `:61` |
| P-19 | Codex loads `.codex/agents/*.toml` "as configuration layers for **spawned** sessions". The wrapper's top-level `codex exec` names no agent, so the TOML's `developer_instructions` do not reach that lane. | V (doc) / A (runtime) | `knowledge-base/sources/agent-harness-docs/docs/codex/agent-configuration__subagents.md:237-238`; invocation `codex-sol-implementer.md:154-158`. Runtime not probed. |
| P-20 | **Banner premise: REFUTED** that the banner lacked the thread id. The run-0087b182 banner carries it on line 10, with SGR escapes. Arms: the regex `^\x1b\[1msession id:\x1b\[0m [0-9a-f-]+$` matched line 10; the plain `^session id: ` scored 0 in that file but 46 hits across other logs, so the plain probe discriminates. | R (and root cause C) | `.agent/sdlc-runs/0087b1820d1c4b6aa3b186c6436d8bab/codex.log:1`, `:10` (main checkout) |
| P-21 | **Root cause CONFIRMED:** `parse_parent_thread_id` compares `key.strip().lower() == "session id"` on raw text. With the SGR prefix the key is `\x1b[1msession id`, and the value also starts with `\x1b[0m`, so it returns None. `reconcile_spawns` then emits the observed error. | C | `lane_result.py:188-220` (compare `:216-219`); error `sdlc_team.py:588-591`; settlement `.agent/sdlc-runs/0087b182…/settlement.json:1` |
| P-22 | All 3 coloured logs are codex v0.160.0 and all 3 settled with this error. The 46 plain logs run up to v0.158.0. Coloured-ness tracks the version in this corpus. | V (counts) / A (cause) | Greps over `.agent/sdlc-runs/*/codex.log` and `*/settlement.json`; heads `1b42df2a…/codex.log:1-11`, `2dab7794…/codex.log:1-11`. Version vs. environment as the cause is not established. Three other failed settlements carrying the same string (`962b…`, `efa1…`, `aaa0…`) have no `output.md` and were not examined. |
| P-23 | The test fixtures use only plain banners, so the suite was green while live runs failed. | V | `tests/test_sdlc_team.py:46-54`; `tests/test_lane_result.py:116-135`, `:138-163` |
| P-24 | The offline codex CLI reference documents no colour flag. Arms: `colou?r\|ansi` → 0 in `cli__reference.md`; the control `--json\|output-last-message` → 7 hits in the same file. | V (absence within that doc only) | `knowledge-base/.../docs/codex/cli__reference.md:194`, `:304` (control hits) |
| P-25 | The existing timeout test pins TERM to the pgid and TIMED_OUT, with rc `-SIGTERM`. K7 extends it, not replaces it. | V | `tests/test_sdlc_team.py:1569-1643` |
| P-26 | Parity requires each wrapper to carry `--model <family model>`, the literal `model_reasoning_effort="xhigh"`, and the no-substitute sentence. | V | `python/src/dotfiles_setup/codex_agent_parity.py:138-150`, `:340-372` |
| P-27 | The implementer TOML carries the `dotfiles-hand-authored-codex-lane` sentinel. | V | `.codex/agents/codex-sol-implementer.toml:1` |
| P-28 | gated-implementation reads `^COMMIT:\s*(\S+)\s*$` and returns `implementer-no-commit` without a match. Its default `TIMEOUT` is 3600. | V | `.claude/workflows/gated-implementation.js:85`, `:94-95`, `:108-111` |
| P-29 | `test_workflows_js.py` exercises that `COMMIT:` consumer. | V | `tests/test_workflows_js.py:277`, `:514-542` |
| P-30 | `sdlc-team` is registered in `main.py` with the request positional, and dispatched by a lambda. | V | `python/src/dotfiles_setup/main.py:1239-1250`, `:3056-3057` |
| P-31 | `_request_error` validates the absolute spec, the effort/model slugs, a finite positive timeout and the allowlist. | V | `sdlc_team.py:648-671` |
| P-32 | `SDLC_RUNS_DIR = ".agent/sdlc-runs"`. | V | `sdlc_team.py:183` |
| P-33 | `hook_guard` denies a hand-rolled `codex exec` naming a `.agent/sdlc-runs` path. | V (tree) / A (origin/main) | `python/src/dotfiles_setup/hook_guard.py:439-460`, `:471-480`. This branch modified `hook_guard`, so origin/main line numbers may differ. |
| P-34 | Policy: implementer wrappers pin `danger-full-access` explicitly; never `--ephemeral`; 12 wrappers carry their own argv + `$LOG.rc`. | V | `.claude/rules/ai-cli-invocation.md:33-45` |
| P-35 | "Models and enums are generated, never hand-written" (R16/D23). | V | `python/AGENTS.md:109-111` |
| P-36 | Exactly one codegen job exists (`drift-verdict`). | V | `python/pyproject.toml:258-260`; `python/src/dotfiles_setup/generated/` holds only `drift_verdict.py` |
| P-37 | Five other sol roles use the same `$LOG.rc` + `reap --pattern "$OUT" --kill` shape. | V | e.g. `.claude/agents/codex-sol-advisor.md:104`, `:133`; `codex-sol-operator.md:71`, `:100`; `codex-sol-adversarial-critic.md:107`, `:136`; `codex-sol-claude-code-expert.md:118`, `:147`; `codex-sol-staleness-auditor.md:84`, `:113` |
| P-38 | `bounded-wait` returns 124 on expiry. | V | `python/src/dotfiles_setup/bounded_wait.py:22`, `:71` |
| P-39 | The skill documents the settlement lifecycle and routes implementation to the implementer pair. | V | `.claude/skills/codex-sdlc-team/SKILL.md:93-103`, `:149` |
| P-40 | The cited files at origin/main equal the working tree I read. | A | No Bash: `git show origin/main:` could not run. Coordinator action C-0. |

## RULINGS (Ray via coordinator e67105a8, 2026-10-04)

- **D-1:** add a generic `env_overrides` field to the shared supervisor. Only the new `implementer_lane.py` sets the planning scrub, and `sdlc_team.py` stays free of the banned tokens.
- **D-2: CODEGEN NOW.** Author JSON schemas for the new models and generate them via datamodel-codegen, per `python/AGENTS.md:109-111`. Do not hand-write them.
- **D-3:** a narrow parity-gate exception. The gate accepts either the `model_reasoning_effort="xhigh"` literal, or a `mise run implementer-lane` call whose Python sets xhigh, test-pinned.
- **D-4 (coordinator):** yes. A timed-out lane with valid delivery hands its sha to gates and review.
- **D-5b:** the ANSI banner fix ships FIRST as its own small PR, and is REMOVED from this spec's scope.
- **D-7:** the other five wrappers become a follow-up issue.
- **C-0:** re-derive every file:line after the bgisolation PR merges.
- **C-3:** dispatch with TIMEOUT 5400.
- **D-6/D-8:** coordinator decides at ratification.
