# SPEC (RESPEC round 1 of max 2) — research-gate-sync: fix the DO NOT SHIP cold review

- Drafted by spec-scribe, 2026-10-04. **RATIFIED by architect 633cd8, 2026-10-04:**
  - **D1 = C.** One target, the inspect-read SHA. This deliberately amends parent §3 step 3.
  - **D2 = ticket.** The coordinator files the F1b stamp issue.
  - **D3 = no-op.**
  - **P17 VERIFIED.** The probe read the man page at `/Library/Developer/CommandLineTools/usr/share/man/man1/git.1:2180-2182`:
    - `GIT_OPTIONAL_LOCKS` has 2 hits;
    - the control arm `GIT_TERMINAL_PROMPT` has 1 hit;
    - an invented absent name has 0 hits.

    The implementer still re-checks the installed git.
- Subject: worktree `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/research-gate-sync`,
  branch `feat/research-gate-sync` @ `34b8651a`.
- Input: `docs/research/kb/reports/agents/cold-review-research-gate-sync-34b8651a.md` (in that worktree),
  which returned **DO NOT SHIP** with three MEDIUMs (F1-F3) and four LOWs (F4-F7). It also owes
  `mise run codegen-check` and the M3 red-to-green evidence.
- Parent spec: `docs/specs/research-gate-sync.md`, including Revisions B, C and C.1. Those revisions stay
  BINDING except where this respec amends them, and every amendment is named as such.
- Implementer: `codex-sol-implementer`, effort xhigh. **Only targeted tests may run, because the host test
  slot is shared.**
- Memory: consulted (`.claude/agent-memory-local/spec-scribe/`).
- This lane has no Bash, so every claim that needs a command is marked `A` in PREMISES and routed to
  verification.

## 0. Decisions: each finding's disposition

| # | Finding | Disposition | Ratify? |
|---|---|---|---|
| F1 | A failed sync moves the checkout before verifying it, and that move silences the doctor | **F1a, in scope.** Every failure AFTER a successful merge appends a fixed suffix that says the checkout moved, where it is now, that the hooks run it UNVERIFIED, and how to recover. **F1b, ticket:** a stamp of the last control-verified SHA that the doctor compares with HEAD. Rollback is **rejected**, because parent §3 step 1 says "Never stash, reset, clean or force" (`docs/specs/research-gate-sync.md:54`). | **D2** (F1b scope) |
| F2 | Two targets: sync lands on the gate's fetched `origin/main`, while the doctor judges against this repo's local `origin/main` | **Option C (recommended): one target.** Sync captures `state.target`, the SHA of this repo's local `origin/main` as read by `inspect`. After `fetch origin main` it runs `git -C <gate> merge --ff-only <state.target SHA>`, so the dry-run plan, the real action and the doctor's oracle are the same commit. Both history-probe errors (missing `origin/main`, unknown gate head) carry a fetch hint naming `git -C <repo_root> fetch origin`, so refusing on them is no longer a lockout. **This AMENDS ratified §3 step 3** (`docs/specs/research-gate-sync.md:56`, "`git -C <gate> merge --ff-only origin/main`"). | **D1** |
| F3 | The fix hint names a command that refuses | Each unsafe state gets its own working fix. Only "behind" keeps `run \`mise run research-gate-sync\``. The doctor and sync use the same strings, from one module (§3). | no |
| F4 | A dry run on an AHEAD gate says `already at` | AHEAD returns rc 0 with `ahead of origin/main (<head7> vs <target7>) — nothing to sync` in BOTH dry and real runs. The real run performs no actions. | **D3** (real-run AHEAD is a no-op) |
| F5 | The SessionStart `git status` can take `index.lock` | Set `GIT_OPTIONAL_LOCKS=0` in `_git`'s env for every call except `fetch` and `merge`. It is the documented environment equivalent of `--no-optional-locks` (premise P17, `A`). An env var is used rather than an argv flag because the tests index argv by position (`args[3]`, `args[3:5]`); see P12. | no |
| F6 | The commit message falsely says the sync runs "from this repo" | The new commit's body carries a one-line correction. The coordinator fixes the PR body or squash message. | no |
| F7 | No test covers a dry-run refusal (M1 and M2 survived) | `test_unsafe_checkout_is_refused` gains a `dry_run` axis with a per-state reason marker. M1 and M2 become required-red mutation rows. | no |
| owed | `codegen-check`; M3 red-to-green evidence | The schema is unchanged in this round. The implementer runs `mise run codegen-check`, records the red run of every new or changed test against the unmodified `34b8651a` code, and runs the mutation table in §5. | no |

### D1: the target design for F2. Recommendation: C.

- **C (recommended).** Merge the exact SHA that `inspect` read from this repo. PRO: one oracle, so
  plan == action == doctor. A success always leaves the doctor clean. A foreign or forked gate `origin`
  cannot move the gate off the authoritative SHA (P7 becomes benign). The gate can never get ahead of the
  repo through sync, so the unknown-head lockout cannot be produced by sync. CON: the sync lands at this
  repo's last-fetched `origin/main`, which may be older than GitHub until someone fetches here. It also
  amends ratified §3 step 3, so it needs ratification.
- **A (the cold review's proposal).** Keep merging the gate's `origin/main` and let a non-dry run proceed
  when the only error is a history probe. PRO: the sync always takes the newest upstream commit, and
  §3 step 3 is untouched. CON: two oracles remain. A successful sync can still leave the doctor
  `UNVERIFIABLE` until this repo fetches, and the success line still cannot be checked against the doctor's
  target. If A is chosen, §3 rows S6-S8 and §5 arms L1/L3 must be rewritten. Do not dispatch this draft
  under A.

### D2: F1b scope. Recommendation: ticket.

- **Ticket (recommended).** PRO: keeps round 1 small. The CLI line from F1a is loud at the moment of
  failure, which is when the operator is watching. CON: later SessionStarts stay blind to a checkout that
  moved but was never verified.
- **In scope.** A stamp under `git rev-parse --git-path`, written only after the controls pass, plus a
  doctor finding when HEAD differs from the stamp. PRO: closes the blindness. CON: it is new state and a
  new finding (the real gate, set up by hand in #1409, has no stamp and would be flagged until its first
  sync). It also adds tests and widens round 1 of a two-round budget.

### D3: real-run AHEAD. Recommendation: no-op.

- **No-op, rc 0 (recommended).** Under C, merging an ancestor SHA is a no-op anyway. Running uv and the
  controls would then end in a misleading "already at". PRO: plan == action. CON: the venv of an AHEAD
  gate is not re-verified. (Only a hand-made state is AHEAD, and the doctor ignores AHEAD per H1, `:139-140`.)
- **Re-verify.** Run uv and the controls without fetch or merge. PRO: re-verifies the venv. CON: a new
  code path, and a new string to pin.

## 1. Objective

Make `research-gate-sync` shippable by closing cold-review F1-F7 without widening the feature.

- A sync either lands the gate exactly on the commit the doctor judges against (D1), or refuses with a fix
  that works.
- Every operator-facing line has a line of code that makes it true. A doctor hint never names a command
  that is guaranteed to refuse.
- A failure after the checkout moved says so.
- Every dry-run refusal is bound by a test that turns red when the refusal is deleted.

## 2. Files (ALLOWLIST; touch nothing else)

All paths are relative to the worktree root.

- `python/src/dotfiles_setup/research_gate_sync.py`: F1a, F2, F3 strings, F4, F5.
- `python/src/dotfiles_setup/doctor.py`: `check_research_gate` only (`:1811-1846`). Use the shared F3
  strings.
- `tests/test_research_gate_sync.py`: new and changed arms (§5).
- `tests/test_doctor.py`: `test_research_gate_findings_use_real_history` only (`:2191-2288`). Change the
  hint assertions and add the fetch-hint markers.
- `python/AGENTS.md`: lines 128-134 only. Restate the paragraph so it says the real run also lands on
  "this repo's local `origin/main`" (D1) and that unsafe states name their own fix. Keep the length about
  the same.

**NOT touched:**

- `schemas/research-gate-sync.schema.json`: no field changes. `SyncResult` already carries
  old/new/actions/ok/reason/rc (`schemas/research-gate-sync.schema.json:83-124`).
- `python/src/dotfiles_setup/generated/*`, `python/pyproject.toml`, `main.py`, `mise.toml`, `doctor.toml`.
  The doctor.toml comment at `:320-321` stays true under D1.
- `python/src/dotfiles_setup/AGENTS.md`, which E2 marks as untouchable (`docs/specs/research-gate-sync.md:193`).

## 3. Interfaces

The public signatures are UNCHANGED:

- `inspect(gate, repo_root, *, runner, timeout) -> GateState`
- `sync(gate, repo_root, *, dry_run, runner) -> SyncResult`
- `check_research_gate(setup, *, runner)`
- `research_gate_sync_main(repo_root, *, dry_run)`

The private `_sync_actions` gains a `target: str` parameter, which is the SHA from `inspect`.

### 3.1 Shared strings (module-level in `research_gate_sync.py`; the doctor imports them)

Keep the wording verbatim. The tests pin substrings of these strings.

```python
DIRTY = "has uncommitted changes — review `git -C {path} status`; sync never stashes, resets or cleans"
NOT_MAIN = "is not on main — run `git -C {path} switch main`"
DIVERGED = "diverged from origin/main — sync never forces; reconcile it by hand"
BEHIND_FIX = "— run `mise run research-gate-sync`"
NO_TARGET = "this repo has no origin/main (git rc {rc}: {stderr}) — run `git -C {repo} fetch origin`"
UNKNOWN_HEAD = (
    "gate HEAD {head7} is unknown to this repo — run `git -C {repo} fetch origin`; "
    "a commit that exists only in the gate must be reconciled by hand"
)
UNVERIFIED = (
    " — checkout now at {new7} (was {old7}); the hooks run it UNVERIFIED and doctor cannot "
    "detect this — fix the cause, then re-run `mise run research-gate-sync`"
)
AHEAD = "ahead of origin/main ({head7} vs {target7}) — nothing to sync"
```

### 3.2 Doctor findings (`check_research_gate`)

The findings are emitted in the current order. The `path` is the resolved gate path.

- dirty → `research-gate: {path} ` + `DIRTY.format(path=path)`
- known non-main → `research-gate: {path} ` + `NOT_MAIN.format(path=path)`
- `state.reason` → `research-gate: UNVERIFIABLE — {state.reason}`. This stays unchanged; the reason
  carries NO_TARGET or UNKNOWN_HEAD where they apply.
- behind → the existing text at `doctor.py:1840-1843`, ending in `BEHIND_FIX`
- diverged → `research-gate: {path} ` + `DIVERGED`

### 3.3 `inspect` / `_history` (F2 hints)

- `rev-parse --verify origin/main` in repo_root: when it **returns** a non-zero rc, raise
  `ValueError(NO_TARGET.format(...))`. Use the rc, `stderr.strip()` and `repo=repo_root`.
- `cat-file -e <head>^{commit}` in repo_root: when it **returns** a non-zero rc, raise
  `ValueError(UNKNOWN_HEAD.format(head7=head[:7], repo=repo_root))`.
- A timeout or OSError keeps today's generic propagation. No other probe's message changes.

### 3.4 `sync` decision table

Refusals run in this order, first match wins, and the order is the same for dry and real runs.

| Row | State | Dry run | Real run |
|---|---|---|---|
| S1 | absent | rc 2 `{gate} is not installed (#1409)` (unchanged) | same |
| S2 | `state.reason` | rc 1 `UNVERIFIABLE — {reason}` (unchanged) | same, no fetch or merge |
| S3 | branch != `main` | rc 1 `checkout ` + `NOT_MAIN.format(path=gate)` | same |
| S4 | dirty | rc 1 `checkout ` + `DIRTY.format(path=gate)` | same |
| S5 | diverged | rc 1 `checkout ` + `DIVERGED` | same, **no fetch or merge** (new: the refusal now happens up front) |
| S6 | ahead | rc 0, `AHEAD.format(...)`, `actions == []` | same, no subprocess beyond inspect (D3) |
| S7 | behind | rc 0 `would fast-forward …` (unchanged) | `fetch origin main` → `merge --ff-only <target SHA>` → re-read HEAD → uv → controls → rc 0 `<old7> -> <new7>` |
| S8 | equal | rc 0 `already at <head7>` (unchanged) | same action sequence as S7 → rc 0 `already at <new7>` |

**F1a.** In `_sync_actions`, once `merge` has returned rc 0, every later failure appends
`UNVERIFIED.format(new7=..., old7=...)` to its reason. That covers:

- the HEAD re-read, where `new7 = "unknown"` if it failed;
- uv;
- each control;
- the `except` handler.

A failure at `fetch` or `merge` appends nothing.

## 4. Constraints and invariants

- All parent constraints stay binding (`docs/specs/research-gate-sync.md:73-82`):
  - argv lists only;
  - timeouts on every subprocess;
  - no credentials printed;
  - tests never touch the real `~/.codex`;
  - never stash, reset, clean, force or rebase;
  - no real non-dry sync against `~/.codex/tools/dotfiles-research-gate`. A `--dry-run` there IS allowed;
    report its output.
- The doctor stays offline and SessionStart-fast. No new subprocess may be added to `check_research_gate`.
- `GIT_OPTIONAL_LOCKS=0` goes on every `_git` call whose subcommand is not `fetch` or `merge`. Add it
  beside the existing `GIT_TERMINAL_PROMPT` conditional (`research_gate_sync.py:49-51`).
  - **Precondition:** before writing it, run `man -P cat git` (or `git help -m git`) and record the
    `GIT_OPTIONAL_LOCKS` paragraph in your report.
  - **Control arm:** the same command must also show `GIT_TERMINAL_PROMPT`.
  - If the paragraph is absent, STOP and DISSENT. Do not switch to an argv flag, because the tests index
    argv by position.
- No inline suppressions (`noqa` / `type: ignore`). Serialization goes only through `codec`.
- The codex lane is invisible to `hook_guard`, so this spec is the guard:
  - no `git add -u/-A/.`;
  - no `commit -a`;
  - no `--amend`;
  - no push;
  - no `--no-verify`;
  - no `HK_SKIP_*`.
- **Gates (host slot shared). Run ONLY these:**
  - `uv run --project python pytest tests/test_research_gate_sync.py -n 2 -q`
  - `uv run --project python pytest tests/test_doctor.py -n 2 -q -k "research_gate or every_check or shipped_baseline"`
  - `uv run --project python ruff check <changed .py>` and `ruff format --check <changed .py>`
  - `uv run --project python ty check --project python python/src tests plugins` (M2)
  - `mise run codegen-check`

  NO full pytest, and NO `mise run lint/verify/gate/ship/land/sync/lint-docs`.
- **Mutation hygiene.** Stage the finished change with an explicit `git add <allowlisted paths>` BEFORE
  any mutation. Revert each mutation with `git checkout -- <file>`, which restores the STAGED version.
  Prove the tree matches the index with `git diff --quiet; echo rc=$?` → `rc=0` after every revert.

## 5. Verification

### 5.1 Red first (M3)

Write or alter every test below FIRST. Run it against the unmodified `34b8651a` source and record the
failing node ids and assertion lines. An ImportError or NameError on a new constant does not count as red,
so reference the strings by literal substring in the tests, not by importing the constants.

### 5.2 New and changed arms

| Arm | Test | Asserts |
|---|---|---|
| U1 | `test_unsafe_checkout_is_refused` gains `@pytest.mark.parametrize("dry_run", [False, True])` | rc (2 for absent, else 1). The per-state reason marker: absent `not installed (#1409)`; not-git and nested `UNVERIFIABLE`; dirty and tracked-dirty `uncommitted changes` + `git -C`; detached and branch `switch main`; diverged `sync never forces`. Also: `"mise run research-gate-sync" not in reason`, no non-git call, and **no fetch or merge for every state, diverged included** (drop the exemption at `tests/test_research_gate_sync.py:225`). |
| D | `test_research_gate_findings_use_real_history` (`tests/test_doctor.py:2287-2288`) | behind: contains `mise run research-gate-sync`. dirty and tracked-dirty: contains `status` + `never stashes`, and NOT `mise run research-gate-sync`. branch and detached: contains `switch main`, and NOT the sync hint. diverged: contains `reconcile it by hand`, and NOT the sync hint. unknown: contains `fetch origin` + `unknown to this repo`. broken: contains `has no origin/main` + `fetch origin`. |
| H | `test_history_states[unknown]` | `reason` contains `unknown to this repo` and `fetch origin`. |
| A4 | NEW: AHEAD, dry and real | rc 0. reason == `ahead of origin/main ({head7} vs {target7}) — nothing to sync`. `actions == []`. Gate HEAD unchanged. No fetch, merge or uv call. |
| L1 | NEW two-target lockout arm (inverts cold P1). Steps: advance repo (T1); a second clone pushes T2 to origin without this repo fetching | sync rc 0 `<old7> -> <T1_7>`. Gate HEAD == T1 (NOT T2). The doctor's `check_research_gate` is `[]`. A re-sync gives rc 0 `already at <T1_7>`; a dry run gives rc 0 `already at <T1_7>`. Then run `git -C repo fetch origin`: the doctor reports `1 commits behind`, and a sync gives rc 0 with gate == T2. |
| L2 | NEW lockout-escape arm. Steps: put the gate by hand on T2, which this repo has not fetched (simulating the pre-fix sync) | The doctor reports `UNVERIFIABLE` with `fetch origin`. Sync and dry run both give rc 1 with `fetch origin`, and sync performs no fetch or merge. Then **run the hint** (`git -C repo fetch origin`): the doctor is `[]`, and sync gives rc 0 `already at <T2_7>`. |
| L3 | NEW foreign origin (inverts cold P7). Steps: re-point the gate `origin` at a fork that contains T1 plus one fork-only commit | sync rc 0, gate HEAD == this repo's `origin/main` (T1), NOT the fork tip, and the doctor is `[]`. |
| F1 | `test_failure_order_stops` | For `fail_at` in {new-head, uv, heartbeat, submit, stop}: reason contains `UNVERIFIED` and `(was {old7})`. For uv/heartbeat/submit/stop it also contains `now at {target7}`. For `fail_at` in {fetch, merge}: `UNVERIFIED` NOT in reason. |
| F1r | NEW recovery arm (inverts cold P4 uv case) | uv fails → rc 1 with `UNVERIFIED`. Then a sync with the good runner gives rc 0 `already at <target7>`, which proves the hint "re-run" works. |
| E | `test_sync_pins_sanitized_env` | For each git call: `env.get("GIT_OPTIONAL_LOCKS") == "0"` iff `args[3] not in {"fetch", "merge"}`. Also `result.new_sha == target` (already present). |

### 5.3 Mutation rows (each MUST turn red; record the command and the failing ids)

Apply each mutation to the staged, finished code, run the narrowest `-k` selection, then revert.

| Row | Mutation | Must fail (at least one) |
|---|---|---|
| MR1 (cold M1 survivor) | the diverged refusal `elif state.diverged:` → `elif False:` | U1 `[diverged-True]`, and `[diverged-False]` (no-fetch assertion) |
| MR2 (cold M2 survivor) | the not-main and dirty refusals each gain `not dry_run and` | U1 `[dirty-True]`, `[tracked-dirty-True]`, `[branch-True]`, `[detached-True]` |
| MR3 | the merge argv uses the literal `"origin/main"` instead of the target SHA | L1, L3 |
| MR4 | UNKNOWN_HEAD loses its fetch clause | L2, H, D `[unknown]` |
| MR5 | NO_TARGET loses its fetch clause | D `[broken]` |
| MR6a/b/c | the doctor's DIRTY / NOT_MAIN / DIVERGED finding reverts to the old `{fix}` suffix | D `[dirty]` / `[branch]` / `[diverged]` |
| MR7 | AHEAD reverts to `already at {head7}` | A4 |
| MR8a | the UNVERIFIED suffix is never appended | F1 `[uv]`, F1r |
| MR8b | the suffix is appended on fetch and merge failures too | F1 `[fetch]`, `[merge]` |
| MR9 | the `GIT_OPTIONAL_LOCKS` line is deleted | E |
| MR10 | the real-run AHEAD path calls `_sync_actions` | A4 (real) |
| Regression (cold M4, M6, M10) | re-apply each exactly as described in the cold review (`cold-review…:58-60`) | still red |

### 5.4 Real-path arms (read-only, allowed)

- `uv run --project python dotfiles-setup research-gate-sync --dry-run`, run from the worktree. Report
  its stdout and rc. It is expected to show `would fast-forward 2d763ac -> <this repo origin/main7> …`.
  This expectation is inherited (P20).
- The C.1 H4 one-check command (`docs/specs/research-gate-sync.md:189`). Report its output.

### 5.5 Report

Write the report to the lane's standard output path. It must contain:

- the man-page excerpt (§4);
- the red-first table;
- the green gate rcs, read from file-captured `rc=`, never from a piped tail;
- the mutation table with the failing ids;
- the two real-path outputs;
- the line "real uv refresh + real gate path UNVERIFIED until the post-merge run".

## 6. Commit

- Make ONE new commit on top of `34b8651a` in the worktree, on branch `feat/research-gate-sync`. **No
  amend, no squash, no push.**
- Stage only the §2 files, by explicit path.
- Let the pre-commit hook run. If it fails, fix the cause and commit again; never bypass it.
- Message:

  ```
  fix(research-gate-sync): one sync target, working fix hints, loud unverified moves

  - F2: merge --ff-only the SHA inspect read from this repo's origin/main; fetch hints for
    missing origin/main and unknown gate HEAD (no lockout)
  - F3: dirty / not-main / diverged findings and refusals name a fix that works
  - F1: failures after the merge say the checkout moved and runs UNVERIFIED (stamp: ticketed)
  - F4: AHEAD reports "ahead … nothing to sync" (dry and real)
  - F5: GIT_OPTIONAL_LOCKS=0 on read-only git probes
  - F7: dry-run refusal arms; cold-review M1/M2 survivors now red
  - Correction to 34b8651a: sync fetches from the gate's own origin; this repo supplies
    only doctor.toml and the target SHA.
  ```

## 7. PREMISES

Legend:

- `L` = read by spec-scribe this run (2026-10-04) at the cited file:line.
- `A` = assumed or inherited; the reason is stated.

Paths are relative to the worktree root unless absolute.

| # | Premise | Cite | Class |
|---|---|---|---|
| P1 | Sync refuses on any `state.reason`, before the branch and dirty checks | `python/src/dotfiles_setup/research_gate_sync.py:281-282` | L |
| P2 | The real run fetches and merges the gate's own `origin/main` | `research_gate_sync.py:305-308` | L |
| P3 | The new HEAD is re-read after the merge; uv and control failures return with no note of the move | `research_gate_sync.py:322`, `:336-345` | L |
| P4 | The dry run's diverged refusal sits inside the `dry_run` branch, and ahead falls through to `already at` | `research_gate_sync.py:287-297` | L |
| P5 | Target and ancestry are computed in repo_root; the unknown head comes from `cat-file -e` through `_required` | `research_gate_sync.py:174-191`, `:62-72` | L |
| P6 | The env conditional pattern exists: `GIT_TERMINAL_PROMPT=0` is set for fetch only | `research_gate_sync.py:49-51` | L |
| P7 | The doctor `status --porcelain` probe runs through `_git` | `research_gate_sync.py:143`, `:52-59` | L |
| P8 | The doctor's single `fix` names `mise run research-gate-sync` for dirty, not-main, behind and diverged | `python/src/dotfiles_setup/doctor.py:1832-1845` | L |
| P9 | The test pins the sync hint on every non-UNVERIFIABLE finding | `tests/test_doctor.py:2287-2288` | L |
| P10 | The doctor fixture states include unknown, broken (deleted `origin/main`) and unknown-dirty-branch (3 findings) | `tests/test_doctor.py:2175-2188`, `:2283-2286` | L |
| P11 | The unsafe-refusal test runs non-dry only and exempts diverged from the no-fetch/merge assertion | `tests/test_research_gate_sync.py:220`, `:225-226` | L |
| P12 | The tests index argv by position (`args[3]`, `args[3:5]`, `args[5]`, `args[6]`), so a global git flag would shift them | `tests/test_research_gate_sync.py:150-156`, `:226`, `:302-304` | L |
| P13 | `child_env.without_git_context` strips only routing names; `GIT_OPTIONAL_LOCKS` is not among them | `python/src/dotfiles_setup/child_env.py:36-45`, `:71-74` | L |
| P14 | Ratified §3 step 3 merges `origin/main`; D1 amends it | `docs/specs/research-gate-sync.md:56` | L |
| P15 | The parent spec says never stash, reset, clean or force, which is why rollback is rejected for F1 | `docs/specs/research-gate-sync.md:54` | L |
| P16 | H1: AHEAD needs proven ancestry and produces no finding; an unknown head is UNVERIFIABLE | `docs/specs/research-gate-sync.md:138-141` | L |
| P17 | `GIT_OPTIONAL_LOCKS=0` is git's documented env equivalent of `--no-optional-locks` | none readable here. The KB `sources/` grep for `OPTIONAL_LOCKS` returned 0 (control: `GIT_TERMINAL_PROMPT` hit 1 file in the same corpus, so the probe can match). The man page is not on any readable path. | **A**: the implementer must verify (§4 precondition) |
| P18 | `git merge --ff-only <sha>` refuses when the SHA is absent from the gate, and fast-forwards when the SHA is a descendant | none; git behaviour not read here | **A**: verified by arms L1/L3 |
| P19 | The schema already carries every field this round needs | `schemas/research-gate-sync.schema.json:83-124` | L |
| P20 | The real gate is at `2d763ac`, 117 commits behind, clean, on `main`, with origin = the dotfiles repo | `cold-review-research-gate-sync-34b8651a.md:64-66` | **A**: inherited from the cold review's R1-R3; not re-probed (no Bash) |
| P21 | Cold probes P1/P4/P7 reproduced F1/F2, and M1/M2 survived with 78/78 green | `cold-review…:38-42`, `:61-62` | **A**: inherited |
| P22 | The CLI `--repo-root` help says "Repository supplying doctor.toml and local origin/main", which stays true under D1 | `python/src/dotfiles_setup/main.py:1854-1858`, `:3057-3060` | L |
| P23 | The doctor.toml comment stays true under D1 | `doctor.toml:319-321` | L |
| P24 | The python/AGENTS.md paragraph describes only the dry run as "against this repo's local origin/main" | `python/AGENTS.md:128-134` | L |
| P25 | The parent's targeted-gate and no-real-sync constraints | `docs/specs/research-gate-sync.md:80-81` | L |

## Coordinator actions (not the implementer's)

1. Ratify D1-D3, or amend them, before dispatch. Under D1 = A, return this draft for round-1 edits; do
   not dispatch it.
2. If D2 = ticket, file the F1b issue ("doctor: stamp the control-verified research-gate SHA so a failed
   sync stays visible") through `issue-filer`.
3. F6: fix the PR body or squash message at ship time.
4. After implementation, the coordinator owns `mise run lint-docs` (python/AGENTS.md), the full pytest,
   lint, verify and pin-actions. The post-merge real sync stays owed (Ray 2026-10-03 ~23:12, `:132`).
5. Run the cold review again on the new commit (diff `34b8651a..HEAD`). This is round 2 of 2.

## 8. BINDING CORRECTIONS (r1.1, after premise verification; they override the sections above)

Premise report: `docs/research/kb/reports/agents/premise-verifier-research-gate-sync-r1.md` in the worktree. Verdict FIX FIRST: 0 refuted, M1-M3 load-bearing.

- **(M1) Host gate.**
  - Every L1/L2/L3 doctor assertion must `monkeypatch.setattr(doctor.platform, "system", lambda: "Darwin")`, following the precedent at `tests/test_doctor.py:2212`, and must call `doctor.collect(repo, home=..., environ={})`.
  - Without the patch, `check_research_gate` returns `[]` on Linux CI (`doctor.py:1816-1821`).
  - Add a control assertion that the same fixture WITHOUT the patch yields `[]`. This proves the patch is what makes the arm discriminate.
- **(M2) Inherited `GIT_OPTIONAL_LOCKS`.**
  - `_git` sets `GIT_OPTIONAL_LOCKS=0` for every call except `fetch`/`merge`, and REMOVES any inherited `GIT_OPTIONAL_LOCKS` for `fetch`/`merge`. The production behaviour matches the test's "iff" (hk 2.3 may export it; see the report).
  - The E arm runs once with `monkeypatch.setenv("GIT_OPTIONAL_LOCKS", "0")` pre-set, and asserts that fetch/merge envs lack the name. It runs again with the variable unset.
  - Add a mutation row: drop the pop, and the E arm must go red.
- **(M3) F1a handler.**
  - Track an explicit `merged` flag, set only when the merge call returned rc 0. The UNVERIFIED suffix is appended iff `merged` is true. This covers OSError/TimeoutExpired raised at fetch/merge too: no suffix there.
  - If the post-merge HEAD re-read fails, the suffix says `now at unknown (was <old7>)`. It never reuses `result.new_sha` when that was not refreshed.
  - Add arms:
    - TimeoutExpired at fetch → no `UNVERIFIED`;
    - TimeoutExpired at merge → no `UNVERIFIED`;
    - a failed new-head read → `now at unknown`.
  - Add mutation rows:
    - always append the suffix → red;
    - use the stale `new_sha` → red.
- **(M4) Absent target. ACCEPTED INTO SCOPE as arm L3b.**
  - Fixture: a gate whose `origin` is a fork lacking the repo's `origin/main` SHA.
  - Expected: sync returns rc 1, the gate does not move, and there is no `UNVERIFIED`.
  - The reason must carry a fix hint: `gate origin lacks <target7>; git -C <gate> remote -v and fetch the authoritative remote`.
  - Map the raw `not something we can merge` error to that hint using the shared-strings module from §3.
- **(M5) Raising outside `_required`.** `_history` raises NO_TARGET / UNKNOWN_HEAD with their fetch hints directly via `_git`, not through `_required`'s generic message. Timeout and OSError still propagate. MR4/MR5 bind this.
- **P17.** The implementer re-checks the installed git's man page or help (`git help git` or the man file) before relying on it, with `GIT_TERMINAL_PROMPT` as the control arm, and STOPs if the name is absent.

## 9. BINDING CORRECTIONS (r1.2, after premise round 2; they override §8)

Report: `docs/research/kb/reports/agents/premise-verifier-research-gate-sync-r2.md`. Verdict FIX FIRST: one REFUTED item, M1-c.

- **(M1-c, replaces §8's control clause.)** The control arm patches `system` explicitly to `"Linux"` (precedent `tests/test_doctor.py:2156-2157`, then `[]` at `:2162`). It sits on an arm that is NON-empty under the Darwin patch: L1 after the fetch (`1 commits behind`) or L2 (`UNVERIFIABLE`). Under Linux the same fixture must yield `[]`. Nothing may depend on the real host.
- **(N1)** Every doctor arm writes `(repo / "doctor.toml").write_text(f'[research_gate]\npath = "{gate}"\n')` before `doctor.collect(...)` (precedent `tests/test_research_gate_sync.py:430`).
- **(N2)** `doctor` is imported at module top in `tests/test_research_gate_sync.py`. No `noqa`; §4 stands.
- **Accepted residuals, on record:**
  - **M4-b.** The hint is mapped from stderr text that may be locale-dependent. Record the real stderr in the red-first evidence. If the mapping misses, the result is rc 1, no move and a raw message, never an unsafe move.
  - **P17.** The installed-git re-check stays.
  - **N3.** A merge killed by timeout might already have moved HEAD before the kill. That case reports "not moved"; the window is small, and #1648 (the F1b stamp) is the durable cover.
