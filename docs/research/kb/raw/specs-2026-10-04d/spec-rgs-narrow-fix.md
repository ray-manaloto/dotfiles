# SPEC (DRAFT, awaiting architect ratification): research-gate-sync r1.3, the narrow spec, hint and test correction

- **Drafted by** spec-scribe on 2026-10-04. Status: **DRAFT. Do not dispatch** until the architect answers Q0-Q4 (§0).
- **Ratified input.** Ray ratified this on 2026-10-04 as **proposal 2** of the SDLC rc-143 review. Its wording, verbatim
  (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-04c/docs/research/kb/reports/agents/sdlc-team-review-rgs-rc143-0087b182.md:52-56`):
  > Amend `docs/specs/research-gate-sync.md`; correct `doctor.py`; strengthen `tests/test_doctor.py` and
  > `tests/test_research_gate_sync.py`. Keep applicable gates before any further commit. Through public interfaces in
  > isolated repositories, cover unsafe-and-behind hints, exact gate/repository paths, and unsafe-and-ahead refusal
  > ordering. Removing the guard, swapping paths, or moving AHEAD ahead of refusals must fail. Preserve the recorded
  > red-first and `-n 0` deviations instead of claiming retroactive compliance.
- **Subject.** Worktree `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/research-gate-sync` (`WT`
  below), branch `feat/research-gate-sync`, HEAD `291e0d1548547e3f3c8f94a4991d55c2141900ac`. The brief calls the
  branch "research-gate-sync", but its real name has the `feat/` prefix (P1).
- **Memory.** Consulted (`.claude/agent-memory-local/spec-scribe/`). Two rules applied from it:
  - Every copied rewrite gets a consumer grep.
  - This lane has no Bash, so anything that needs a command is marked `A` and routed to the coordinator.
- **How the untracked set was found without Bash.** `git status` was not runnable here. Instead, the set was derived by
  grepping the worktree's git index. That probe has a control arm: three known-tracked paths hit, and an invented token
  missed. Details are in P20. The coordinator still re-confirms the set with `git -C WT status --porcelain`
  (Coordinator action 1).

All paths below are relative to `WT` unless absolute.

## 0. Open choices for the architect (STOP: ratify before dispatch)

| # | Question | Recommendation | Alternative |
|---|---|---|---|
| **Q0** | **Conflict in the brief.** The brief says "Exclude #1655's N1–N3 unless trivially adjacent." But #1655 *is* the ticket for cold-review N1, N2 and N3 (handoff `session-2026-10-04c.md:32`). Proposal 2's scope (hint = N1, exact paths = N2, AHEAD ordering = N3) is those same three items (cold review `:45-47`). Both cannot hold. | **Proposal 2 governs**, because Ray ratified it and the exclusion is coordinator wording. This change implements #1655's N1–N3 in full. The commit says `Closes #1655` if the ticket holds only N1–N3, and `Refs #1655` otherwise. The #1655 body was not readable here (P21, `A`). | Read "exclude" as "exclude anything #1655 carries *beyond* N1–N3". The scope is the same, so only the `Closes`/`Refs` line changes. |
| **Q1** | How should the N4 pointer be placed? | **Two edits.** First, add an inline pointer at the end of `:56`, without changing the ratified text. Second, append `## Revision D` and `## Revision D.1` after `:193`. Every earlier amendment used an appended section (`:107`, `:134`, `:179`). The inline pointer is what the owed item literally asks for (handoff `:33`, cold `:48`). | Append the sections only, and leave `:56` byte-identical. |
| **Q2** | What should the composite unsafe-and-behind finding say? | **Keep the behind fact and drop the suffix.** The finding stays `research-gate: <path> is <N> commits behind origin/main (<h7> vs <t7>)`, with no fix suffix. The sibling dirty or not-main finding already names the fix. No new operator string is created, so nothing new has to be made true. | Add a new suffix such as `— resolve the checkout findings first`. That is a new string to pin and keep true, and it still points away from the command that works. |
| **Q3** | Commit mode. | **`caller`.** The lane stages by explicit path but does not commit. The coordinator runs the broad gates and then commits, because proposal 2 says "Keep applicable gates before any further commit". This also removes the conflict where the r1 respec said "lane commits, coordinator gates later" (SDLC review `:44`). | The lane commits after the targeted gates and the coordinator gates before ship. That repeats r1's recorded conflict. |
| **Q4** | xdist flag for this round. | **`-n 0`.** It matches the host-slot instruction in the r1 dispatch brief (P15). Every log must show the flag that actually ran. | `-n 2`, as r1 respec §4 says (P16). Whichever is chosen, it is written once, here. |

## 1. Objective

Close the last open claims in research-gate-sync before ship, without widening the feature:

- **N1 (behaviour).** Today a dirty, non-main or detached gate that is also behind gets a doctor finding that names
  `mise run research-gate-sync`, and sync refuses that exact state. This breaks respec §1: "A doctor hint never names a
  command that is guaranteed to refuse." The fix: the behind finding names the sync **only** when the sync would
  proceed. That means the checkout is on `main` and clean.
- **N2 (tests).** Every fix hint's **exact** `git -C <path>` is pinned: the gate for dirty and not-main, and this repo
  for the fetch hints. Swapping either path must turn a test red. The unknown-head arm must **run the command the
  finding names**, not a hard-coded fetch.
- **N3 (tests).** A gate that is unsafe (dirty, tracked-dirty, branch or detached) and also AHEAD must be refused in both
  dry and real runs. Moving the AHEAD no-op above those refusals must turn a test red.
- **N4 (docs).** `docs/specs/research-gate-sync.md` points at the respec's D1 = C amendment of `:56` and records this
  round. The recorded deviations stay on record as deviations.
- **Ship hygiene.** The five untracked reports are committed by name. The F6 PR or squash text is drafted (§6).

**Non-goals:**

- No change to `research_gate_sync.py`, the schema, generated code, `main.py`, `mise.toml`, `doctor.toml` or
  `python/AGENTS.md`.
- No F1b stamp; that is #1648, still OPEN.
- No implementer-lane class fix; that is proposal 3.
- No real, non-dry sync.

## 2. Files (ALLOWLIST; touch nothing else)

| Path | Change | Owner |
|---|---|---|
| `python/src/dotfiles_setup/doctor.py` | Edit `check_research_gate` only, in the behind branch at `:1842-1847`. Gate the `BEHIND_FIX` suffix on `state.branch == "main" and not state.dirty`. | implementer |
| `tests/test_doctor.py` | Edit only `_alter_research_gate_history` (`:2165-2188`) and `test_research_gate_findings_use_real_history` (`:2191-2299`). Add the composite states and exact-path assertions (§5.2 D-rows). | implementer |
| `tests/test_research_gate_sync.py` | Edit `test_history_states` (`:97-121`), `test_unsafe_checkout_is_refused` (`:198-240`) and `test_unknown_head_fetch_hint_recovers` (`:344-377`). Add three new tests (§5.2 S-rows). Helpers may be added. | implementer |
| `docs/specs/research-gate-sync.md` | Add the inline pointer at the end of `:56` (per Q1). Append `## Revision D` and `## Revision D.1` after `:193`, with the text given in §3.3. | implementer (docs) |
| `docs/research/kb/reports/agents/cold-review-research-gate-sync-34b8651a.md` | Commit by name. Content unchanged. | coordinator |
| `docs/research/kb/reports/agents/premise-verifier-research-gate-sync-r1.md` | Commit by name. Content unchanged. | coordinator |
| `docs/research/kb/reports/agents/premise-verifier-research-gate-sync-r2.md` | Commit by name. Content unchanged. | coordinator |
| `docs/research/kb/reports/agents/codex-sol-implementer-research-gate-sync-r1.md` | Commit by name. Content unchanged. | coordinator |
| `docs/research/kb/reports/agents/cold-review-research-gate-sync-r1.2-291e0d15.md` | Commit by name. Content unchanged. | coordinator |
| any NEW report this round produces (implementer report, cold review of the new diff) | Commit by name, under the same rule. | coordinator |

The five report paths come from the index probe (P20). Each is consistent with a count stated independently in three
documents: the handoff F3 (`:136`, "5"), the cold review's cleanup (`:167-168`), and the implementer (`:226-227`). They
are records, so their content stays verbatim (`agent-report-persistence.md` rule 4).

**Explicitly NOT touched:**

- `python/src/dotfiles_setup/research_gate_sync.py`. Its refusal order and strings are already correct (P6, P7). The
  property test in §5.2 S3 binds doctor and sync together through behaviour.
  - Rejected alternative: a shared "would-proceed" predicate in this module. It would widen the diff, and the property
    test catches the same drift.
- `python/AGENTS.md:128-134`. "unsafe states name their own fix" stays true after N1 (P19).
- `schemas/research-gate-sync.schema.json`, `python/src/dotfiles_setup/generated/*`, and `python/src/dotfiles_setup/AGENTS.md`.

## 3. Interfaces

The public signatures are **unchanged**: `inspect`, `sync`, `check_research_gate(setup, *, runner)`,
`research_gate_sync_main`.

### 3.1 Doctor behind finding (`doctor.py:1842-1847`)

```python
elif state.behind:
    line = (
        f"research-gate: {path} is {state.behind_by} commits behind origin/main "
        f"({(state.head or '')[:7]} vs {(state.target or '')[:7]})"
    )
    # Name the sync only when sync would proceed: sync refuses a non-main
    # (research_gate_sync.py:320) or dirty (:322) checkout before acting.
    if state.branch == "main" and not state.dirty:
        line += f" {research_gate_sync.BEHIND_FIX}"
    findings.append(line)
```

The resulting strings are exact:

- **Clean `main` and behind.** Byte-identical to today: `… (<h7> vs <t7>) — run \`mise run research-gate-sync\``.
- **Dirty, non-main or detached, and behind.** `… (<h7> vs <t7>)`, with no trailing space and no suffix. This is the Q2
  recommendation.
- **Order and other findings are unchanged:** dirty, then not-main, then UNVERIFIABLE / behind / diverged.

Two facts make the guard complete:

- `state.reason` empty implies `branch_known` is true (`research_gate_sync.py:168-184` sets it on a successful
  symbolic-ref probe, and records an error otherwise). Within the behind branch, `state.branch == "main"` is therefore
  exactly sync's S3 test.
- Behind excludes diverged and ahead (`research_gate_sync.py:229-236`). No other sync refusal can fire on a behind
  state.

### 3.2 Unchanged sync decision order (bound, not changed)

The order is `research_gate_sync.py:316-340`: absent → UNVERIFIABLE → not main → dirty → diverged → AHEAD → dry
plan → actions. N3 tests bind "not main" and "dirty" ahead of AHEAD.

### 3.3 Spec text to add (Q1 recommendation)

**Inline at the end of `docs/specs/research-gate-sync.md:56`.** Append the text below. Leave the existing wording
untouched.

```
 **Amended by Revision D (D1 = C): the merge target is the inspected SHA, not `origin/main`.**
```

**Appended after `:193`** (verbatim; the quoted D1 wording is the ratified text from respec `:4`):

```markdown
## Revision D — respec r1 (BINDING; supersedes everything above where they conflict)

Source: `docs/research/kb/raw/specs-2026-10-04b/spec-research-gate-sync-r1.md` (on `main` via #1650), including its
§8 (r1.1) and §9 (r1.2) corrections. Implemented at `291e0d15`; cold review round 2 (SHIP):
`docs/research/kb/reports/agents/cold-review-research-gate-sync-r1.2-291e0d15.md`.

- **D1 = C.** "One target, the inspect-read SHA. This deliberately amends parent §3 step 3." After
  `git -C <gate> fetch origin main`, sync runs `git -C <gate> merge --ff-only <SHA>`, where `<SHA>` is this repo's
  local `origin/main` as read by `inspect`. Plan, action and doctor share that one commit.
- **D2 = ticket.** The control-verified-SHA stamp (F1b) is #1648.
- **D3 = no-op.** An AHEAD gate returns rc 0 `ahead of origin/main (<h7> vs <t7>) — nothing to sync`, in dry and real
  runs, with no actions.

## Revision D.1 — r1.3 hint correction (BINDING; supersedes Revision D and everything above where they conflict)

Ratified by Ray 2026-10-04 (proposal 2 of SDLC review run 0087b182). It closes #1655 (cold-review N1–N3) and N4.

- **N1. This amends respec §3.2 "behind → … ending in `BEHIND_FIX`".** The behind finding ends in `BEHIND_FIX` only
  when the checkout is on `main` and clean. A dirty, non-main or detached gate that is behind reports the behind fact
  without a fix suffix; its sibling finding names the fix. This restores respec §1: "A doctor hint never names a
  command that is guaranteed to refuse."
- **N2 / N3.** Tests pin the exact `git -C <gate>` / `git -C <repo>` path in every fix hint. They also bind the refusal
  of unsafe-and-ahead gates ahead of the AHEAD no-op.
- **Recorded deviations. These are NOT retroactive compliance:**
  - (a) r1 red-first: the final doctor `fix_markers` assertions were never shown red against `34b8651a`. The red run
    predates the C901 rewrite. Mutation rows MR4, MR5 and MR6a-c bind them instead (cold review I2).
  - (b) r1 xdist: the r1 dispatch brief required `-n 0`. Respec §4 named `-n 2`, and every recorded r1 run used `-n 2`.
  - (c) r1.3: the N2 and N3 arms bind code that was already correct, so they could not be shown red first. Mutation
    rows bind them; only the N1 arms are red-first.
```

When the D.1 text is pasted, the "It closes #1655" sentence follows Q0. If #1655 carries more than N1–N3, use
"addresses".

## 4. Constraints and invariants

- **Parent constraints stay binding** (`docs/specs/research-gate-sync.md:73-82`, respec §4):
  - argv lists;
  - timeouts on every subprocess;
  - no credentials printed;
  - **tests never touch the real `~/.codex`**;
  - never stash, reset, clean, force or rebase;
  - **no real non-dry sync** against `~/.codex/tools/dotfiles-research-gate`.
- **The doctor stays offline and SessionStart-fast.** The N1 guard reads fields `inspect` already filled. It adds no
  subprocess.
- **Public interfaces only, isolated repos only:**
  - Tests drive `doctor.check_research_gate`, `doctor.collect`, `gate_sync.inspect`, `gate_sync.sync` and the existing
    CLI test.
  - Every fixture is a temp bare origin plus clones (the existing `history` fixture, `tests/test_research_gate_sync.py:59-72`,
    and the doctor fixture at `tests/test_doctor.py:2236-2243`).
  - Only `uv` and the hook interpreter are stubbed, through `hook_runner` (`:82-94`). Git stays real.
- **Independent expectations** (`tests/AGENTS.md`, "Tautological"):
  - Expected strings are **literals** in the test, built from fixture variables (`gate`, `repo`, and SHAs read with
    `git rev-parse`).
  - Tests never import `BEHIND_FIX`, `DIRTY` or the other constants. This is also what makes an N1 red-first an
    assertion failure rather than an ImportError (respec §5.1 precedent).
- **Host-gate patching.** Every doctor assertion patches `doctor.platform.system` to `"Darwin"`, following the
  precedent at `tests/test_doctor.py:2212`. One new doctor arm also carries the `"Linux"` → `[]` control, following
  respec §9 M1-c.
- **Fixture arm** (`probes-need-a-control-arm.md` rule 8). Every composite fixture first asserts that the composite
  really exists before it asserts any outcome:
  - unsafe + behind: `inspect(...).behind is True` plus the unsafe field;
  - unsafe + ahead: `inspect(...).ahead is True` plus the unsafe field.
- **Codex lanes are invisible to `hook_guard`, so this spec is the guard:**
  - no `git add -u/-A/.`;
  - no `commit -a`;
  - no `--amend`;
  - no push;
  - no `--no-verify`;
  - no `HK_SKIP_*`;
  - no commit at all if Q3 = `caller`.
- **Lane gates (shared host slot). Run ONLY these:**
  - `uv run --project python pytest tests/test_research_gate_sync.py tests/test_doctor.py -n 0 -q` (or `-n 2` per Q4).
    Both whole files, matching the cold review's C1/C2 scope (cold `:88-89`).
  - `uv run --project python ruff check` and `ruff format --check`, on the three changed `.py` files.
  - `uv run --project python ty check --project python python/src tests plugins` (the Rev C M2 command,
    `docs/specs/research-gate-sync.md:165`).
  - **NO** full pytest, and no `mise run lint/verify/gate/ship/land/sync`.
- **Mutation hygiene** (respec §4 precedent):
  - Stage the finished allowlisted files with an explicit `git add <paths>` BEFORE any mutation.
  - Revert each mutation with `git checkout -- <file>`.
  - After every revert, record `git diff --quiet; echo rc=$?` → `rc=0`.
- **Evidence.** Every rc is file-captured (`… > LOG 2>&1; echo "rc=$?" >> LOG`), never read from a piped tail.

## 5. Verification

### 5.1 Red first, against unmodified `291e0d15` source (N1 only)

Write the D-composite and S3 tests first. Run them before touching `doctor.py`, and record the failing node ids and
assertion lines.

- **Expected red** (it reproduces cold Q1, `:91`): every `*-behind` composite cell fails on "no line contains
  `mise run research-gate-sync`".
- **Expected green already:** the N2 path assertions and N3 ordering cells. The code is correct today; record them as
  green-at-baseline. Only mutation can bind them (Revision D.1 (c)).

### 5.2 New and changed arms

| Arm | Test | Asserts |
|---|---|---|
| **D-c** (N1) | `test_research_gate_findings_use_real_history` gains the states `dirty-behind`, `tracked-dirty-behind`, `branch-behind` and `detached-behind`. `_alter_research_gate_history` advances `origin/main` for any state containing `behind`, then applies the unsafe component. | Fixture arm: `inspect` reports `behind`, plus `dirty` or `branch != "main"`. Exactly **2** findings. One contains `f"1 commits behind origin/main ({gate_head[:7]} vs {target[:7]})"`; both SHAs are read independently with `git rev-parse`. **No** line contains `mise run research-gate-sync`. The other finding contains the exact gate-path hint: `f"git -C {gate} status"` for dirty, or `f"git -C {gate} switch main"` for branch and detached. |
| **D-b** (N1 control) | the existing `behind` cell | The single finding ENDS with `` — run `mise run research-gate-sync` ``. This proves the guard does not over-suppress. |
| **D-p** (N2) | the existing single-state cells | dirty and tracked-dirty contain `f"git -C {gate} status"`. branch and detached contain `f"git -C {gate} switch main"`. unknown and broken contain `f"git -C {repo} fetch origin"`. These replace the path-free markers at `:2287-2297`. |
| **S1** (N2) | `test_unsafe_checkout_is_refused` | The markers at `:233-236` become exact: dirty and tracked-dirty `f"git -C {gate} status"`; detached and branch `f"git -C {gate} switch main"`. Everything else is unchanged. |
| **S1h** (N2) | `test_history_states[unknown]` | `f"git -C {repo} fetch origin"` in `actual.reason` (it replaces the bare `"fetch origin"` at `:121`). |
| **S2** (N2, "run the hint") | `test_unknown_head_fetch_hint_recovers` | Extract the backticked command from the doctor finding with `` re.search(r"`(git -C [^`]+ fetch origin)`", findings[0]) ``. Assert it **equals** `f"git -C {repo} fetch origin"`. Then **execute that extracted command** with `shlex.split` and the sanitized env, instead of the hard-coded `git(repo, "fetch", "origin")` at `:372`. Every later assertion is unchanged. |
| *(fixture note)* | S3, S4 | Build "behind" with `advance(repo)` (`tests/test_research_gate_sync.py:75-79`), which PUSHES. Do not use the doctor test's `update-ref` recipe (`tests/test_doctor.py:2172-2174`): its target never reaches the bare origin, so a real sync would fail with MISSING_TARGET rather than test the hint. |
| **S3** (N1 property, NEW) | `test_doctor_sync_hint_is_never_refused`, parametrized over `behind`, `dirty-behind`, `tracked-dirty-behind`, `branch-behind`, `detached-behind`, `equal` and `ahead` | Darwin patched. `findings = doctor_findings(repo, gate)` (helper `:294-299`). `named = any("mise run research-gate-sync" in f for f in findings)`. The **independent** expectation is `named == (state == "behind")`. Then run `result = gate_sync.sync(gate, repo, runner=hook_runner)`. If `named`, then `result.ok and result.rc == 0` and the gate HEAD equals the target. For each `*-behind` composite, `result.rc == 1` and no fetch or merge ran. One cell (`branch-behind`) also patches `"Linux"` and asserts `doctor_findings(...) == []` (the M1-c control). |
| **S4** (N1 + N2 chain, NEW) | `test_composite_hint_chain_recovers` (`branch-behind`) | The doctor shows the not-main finding and the behind finding without a suffix. Extract `` `git -C <gate> switch main` `` from the not-main finding, assert it equals `f"git -C {gate} switch main"`, and **execute it**. The doctor then shows exactly 1 finding, which ends in the sync hint. `sync` then gives rc 0 `<old7> -> <target7>`, and the doctor is `[]`. |
| **S5** (N3, NEW) | `test_unsafe_and_ahead_is_refused_before_no_op`, parametrized over `unsafe` ∈ {dirty, tracked-dirty, branch, detached} and `dry_run` ∈ {False, True} | Fixture: `commit(gate, "gate-only")`, then `git(repo, "fetch", str(gate), "main")` (precedent `:273-274`), then apply the unsafe component. Fixture arm: `inspect(gate, repo).ahead is True`, plus the unsafe field. Outcome: `not result.ok`, `result.rc == 1`, and the reason contains the exact refusal (`f"git -C {gate} status"` or `f"git -C {gate} switch main"`). `"nothing to sync" not in result.reason`. Every call is git, none is fetch or merge, and the gate HEAD is unchanged. |

### 5.3 Mutation rows (each MUST turn red; record the command, the failing ids and the revert rc)

Every mutation changes **only the guarded line it names**. That keeps the mutations sharp
(`feedback_sharp_vs_coarse_mutation`), and each must be a regression that could really happen.

| Row | Mutation (in the staged, finished code) | Must fail |
|---|---|---|
| MN1 | Guard removed: `if state.branch == "main" and not state.dirty:` → `if True:` | D-c (all 4 cells); S3 (4 composite cells) |
| MN1a | Guard loses its dirty half: `… and not state.dirty` deleted | D-c `dirty-behind`, `tracked-dirty-behind`; S3 same |
| MN1b | Guard loses its branch half: `state.branch == "main" and` deleted | D-c `branch-behind`, `detached-behind`; S3 same |
| MN1c | Over-suppression: guard → `if False:` | D-b; S3 `behind`; S4 |
| X1 | `research_gate_sync.py`: the `elif state.ahead:` block (`:326-330`) moved to directly after the `state.reason` refusal (`:318-319`) | S5 (all 8 cells) |
| X1b | The AHEAD block moved between not-main (`:320-321`) and dirty (`:322-323`) | S5 dirty and tracked-dirty cells (sharp: proves the dirty half separately) |
| X2a | sync `NOT_MAIN.format(path=gate)` → `path=repo_root` (`:321`) | S1 branch and detached; S5 branch and detached |
| X2b | sync `DIRTY.format(path=gate)` → `path=repo_root` (`:323`) | S1 dirty and tracked-dirty; S5 dirty and tracked-dirty |
| X3 | `UNKNOWN_HEAD.format(…, repo=repo_root)` → `repo=state.path` (`:227`) | S1h; S2; D-p `unknown` |
| X4a | doctor `DIRTY.format(path=path)` → `path=setup.repo_root` (`doctor.py:1834`) | D-p dirty and tracked-dirty; D-c `dirty-behind` |
| X4b | doctor `NOT_MAIN.format(path=path)` → `path=setup.repo_root` (`doctor.py:1838`) | D-p branch and detached; D-c `branch-behind`, `detached-behind`; S4 |
| X5 | `NO_TARGET.format(…, repo=repo_root)` → `repo=state.path` (`:212-214`) | D-p `broken` |

X1, X1b, X2, X3 and X5 mutate `research_gate_sync.py`, which is not on the allowlist. That file is only mutated and then
restored, never changed. After the final revert, prove `git diff --quiet -- python/src/dotfiles_setup/research_gate_sync.py`
gives rc 0.

X1-X4 reproduce the cold review's surviving rows (`:114-117`). They SURVIVED at `291e0d15` and must now go red.

### 5.4 Real-path read-only arm (allowed; report the output)

Run the C.1 H4 one-check command from `WT` (`docs/specs/research-gate-sync.md:189`):

```
uv run --project python python -c "from pathlib import Path; from dotfiles_setup import doctor; print('\n'.join(doctor.check_research_gate(doctor.collect(Path.cwd().resolve()))) or 'research-gate: NO FINDINGS')"
```

- **Expected, if the real gate is still clean `main` and behind:** the single behind line, still ending in the sync
  hint. That proves N1 did not suppress the real-world clean case. This expectation is inherited (P22, `A`).
- **If it is not, report the output verbatim.** Do not "fix" the real gate.

### 5.5 Coordinator gates (before the commit, per Q3)

Run each through `mise run gate -- run <name>`, whose rc is the gate's (`verify-before-advancing.md`). Run them after
the host slot frees:

- `lint`
- `pytest`
- `verify`
- `lint-docs`: cheap insurance for the spec markdown. `docs/specs/` is not in the matrix row, but it costs little.

`pin-actions` is N/A because no `.github/**` file changes.

After that, a cold review of the new diff (`291e0d15..<new>`) by an Opus lane: the diff is codex-authored, so the other
model family reviews it. The r1.2 review was "round 2 of a maximum of 2" (cold `:3`). Whether this new diff opens a
fresh review budget is the **architect's call** (Coordinator action 6).

### 5.6 Report (implementer)

Write the report to `docs/research/kb/reports/agents/codex-sol-implementer-research-gate-sync-r1.3.md`. It is a new
untracked report and is committed by name. It must contain:

- the red-first table, with N1 cells red and the N2/N3 cells recorded as green-at-baseline;
- the green gate rcs and the exact `-n` flag used;
- the mutation table, with failing ids and revert rcs;
- the §5.4 output;
- the line "real uv refresh + real gate path UNVERIFIED until the post-merge run".

## 6. Commit

**Mode: `caller` (Q3 recommendation).** The lane stages its four allowlisted files and stops. After §5.5 passes, the
coordinator commits on `feat/research-gate-sync`, by explicit path only.

**Commit 1: the change.**

```
fix(research-gate-sync): name the sync only when it can run; bind hint paths and refusal order

- N1: the doctor's behind finding names `mise run research-gate-sync` only for a clean
  `main` checkout; a dirty, non-main or detached gate gets the behind fact and its own fix
- N2: tests pin the exact `git -C <gate>` / `git -C <repo>` path of every fix hint and
  execute the hint they name
- N3: unsafe-and-ahead gates are refused before the AHEAD no-op, dry and real
- N4: docs/specs/research-gate-sync.md gains Revision D (respec r1, D1 = C) and D.1
- On record, not retroactive compliance: the r1 dispatch asked for `-n 0` but the runs used
  `-n 2`; r1's final doctor fix_markers were never shown red (mutation-bound); the
  r1.3 N2/N3 arms bind already-correct code (mutation-bound)

Closes #1655
```

The last line is `Refs #1655` if Q0 resolves that way.

**Commit 2: the records, by name.** These are the five paths in §2, plus this round's implementer report and cold
review:

```
docs(research-gate-sync): persist review, premise and implementer reports
```

**Owed F6 PR/squash text** (cold F6 `:43`; folds in the Q-CLAIM nit at `:160`). Put this in the PR body, or in the
squash message if ship builds the body itself (P23, `A`):

```
Correction to 34b8651a: sync fetches from the gate's own origin, then fast-forwards to the exact
origin/main SHA that this repo's `inspect` read (D1 = C). This repo supplies doctor.toml, that
target SHA and the ancestry probes; the gate's origin supplies only the objects.

Still open: #1648 (doctor blind to a gate moved but never control-verified).
Real uv refresh + real gate path UNVERIFIED until the post-merge `mise run research-gate-sync`
(Ray 2026-10-03: only after credit-fallback and this PR land).
```

## 7. PREMISES

Legend:

- **L** = read by spec-scribe during this run (2026-10-04), at the cited file:line.
- **A** = assumed or inherited; the reason is stated.

| # | Premise | Cite | Class |
|---|---|---|---|
| P1 | The worktree's branch is `feat/research-gate-sync` at `291e0d1548547e3f3c8f94a4991d55c2141900ac` | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.git/worktrees/research-gate-sync/HEAD:1`; `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.git/refs/heads/feat/research-gate-sync:1` | L |
| P2 | Parent spec §3 step 3 still reads `git -C <gate> merge --ff-only origin/main`. The file's last section is Revision C.1, ending at `:193`. Earlier amendments were appended sections. | `docs/specs/research-gate-sync.md:56`, `:107`, `:134`, `:179`, `:193` | L |
| P3 | The respec ratified "D1 = C. One target, the inspect-read SHA. This deliberately amends parent §3 step 3." Its §1 says "A doctor hint never names a command that is guaranteed to refuse". §3.2 makes behind end in `BEHIND_FIX`. §3.4 says "first match wins". | `.claude/worktrees/handoff-2026-10-04c/docs/research/kb/raw/specs-2026-10-04b/spec-research-gate-sync-r1.md:4`, `:78-79`, `:145`, `:158` (absolute root `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/`) | L |
| P4 | The respec is NOT present in `WT`. It is on main via #1650, so Revision D cites it as a backticked path, not a link. | Glob of `docs/research/kb/raw/specs-2026-10-04b/*` in `WT` → none; the same glob in the handoff-2026-10-04c worktree → 3 files, so the probe discriminates. Cold review E6 `:71-75`. | L |
| P5 | The doctor emits the behind finding with `BEHIND_FIX` regardless of dirty or branch. Dirty and not-main findings are appended first and are independent of the `reason`/`behind` elif chain. | `python/src/dotfiles_setup/doctor.py:1831-1850` | L |
| P6 | Sync refuses in this order: absent → `state.reason` → `branch != "main"` → dirty → diverged → AHEAD → dry plan → actions | `python/src/dotfiles_setup/research_gate_sync.py:316-340` | L |
| P7 | Shared strings: `DIRTY` and `NOT_MAIN` carry `git -C {path}`; `NO_TARGET` and `UNKNOWN_HEAD` carry `git -C {repo} fetch origin`; `BEHIND_FIX` = `` — run `mise run research-gate-sync` ``. Sync formats with `path=gate` and `_history` with `repo=repo_root`. | `research_gate_sync.py:23-37`, `:212-214`, `:227`, `:321`, `:323` | L |
| P8 | `branch_known` is set only on a successful symbolic-ref probe, and a failure is recorded in `reason`. Behind, ahead and diverged are mutually exclusive. | `research_gate_sync.py:168-184`, `:229-236` | L |
| P9 | The doctor fixture has no composite unsafe-and-behind state. Hint markers are checked only on `findings[0]` and carry no path. | `tests/test_doctor.py:2165-2188`, `:2191-2207`, `:2287-2297` | L |
| P10 | The sync U1 markers for dirty are the path-free `"git -C"`, and for branch/detached `"switch main"` | `tests/test_research_gate_sync.py:229-239` | L |
| P11 | The L2 arm hard-codes `git(repo, "fetch", "origin")` rather than running the named hint. `test_history_states[unknown]` asserts only `"fetch origin"`. | `tests/test_research_gate_sync.py:372`, `:119-121` | L |
| P12 | Reusable test seams exist: the `history` fixture, `hook_runner` (stubs uv and the hook only), the `doctor_findings` helper, and the ahead-fixture recipe | `tests/test_research_gate_sync.py:59-72`, `:82-94`, `:294-299`, `:273-274` | L |
| P13 | Cold review r1.2: N1 is reproduced (Q1); N2 survivors are X2, X3 and X4; the N3 survivor is X1; N4 is the `:56` pointer; F6's PR text is owed; I2 says the final `fix_markers` were never shown red | `cold-review-research-gate-sync-r1.2-291e0d15.md:43`, `:45-48`, `:50`, `:91`, `:114-117` | L |
| P14 | The cold review ran only the two targeted files and no broad gates. The reviewed tree was clean against HEAD apart from the untracked reports. | `cold-review…r1.2-291e0d15.md:24-26`, `:54-56`, `:167-168` | L |
| P15 | The r1 dispatch brief to the rgs lane said "run ONLY the targeted pytest files the spec names (`-n 0`)" | `/Users/rmanaloto/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/03b81398-b483-4caa-a92a-35f1a0031da7.jsonl:855` (read by regex; the same line names `spec-research-gate-sync-r1.md` and the rgs worktree) | L |
| P16 | Respec §4 and the preserved dispatch text name `-n 2`. The recorded r1 runs used `-n 2`. | respec `:208-209`; `.agent/kb/raw/codex-sol-implementer-log-94405-1791105274.txt:220-221`; `docs/research/kb/reports/agents/codex-sol-implementer-research-gate-sync-r1.md:72`, `:135-136` | L |
| P17 | The SDLC synthesis names both the `-n 0` deviation and the lane-commit-versus-gates conflict | `.claude/worktrees/handoff-2026-10-04c/docs/research/kb/reports/agents/sdlc-team-review-rgs-rc143-0087b182.md:44`, `:52-56` | L |
| P18 | `#1655` = "N1, N2 and N3"; N4 and F6 are owed at ship; ship refuses untracked reports (F3) | `.claude/worktrees/handoff-2026-10-04c/docs/handoffs/session-2026-10-04c.md:32-33`, `:135-138` | L |
| P19 | `python/AGENTS.md` says "unsafe states name their own fix", which stays true after N1 | `python/AGENTS.md:128-134` | L |
| P20 | Untracked reports in `WT` (rgs-named): the five in §2. Tracked: `premise-verifier-research-gate-sync-round{1,2,3}.md` and `sdlc-team-review-research-gate-sync-revB.md`. | Probe: a regex grep of the worktree index `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.git/worktrees/research-gate-sync/index` for `reports/agents/*research-gate-sync*.md` hit only those 4 of the 9 on disk (the Glob of `WT`). Control arm: in the same index, `docs/specs/research-gate-sync.md`, `research_gate_sync.py` and `test_research_gate_sync.py` hit, and a fresh invented token missed. | L for the 9 rgs-named files. **A for completeness:** a non-rgs-named untracked file anywhere in `WT` was not enumerated (no Bash, hundreds of files). Coordinator action 1 closes it. |
| P21 | #1655's body holds only N1–N3 | not readable (no `gh`). The only local mention is the handoff `:32`. | **A** (Q0) |
| P22 | The real gate is still clean `main`, behind origin/main, at `2d763acb` | cold review E8 `:96-98`; implementer `:181` | **A**: inherited and not re-probed (no Bash). A later fetch or a manual sync could have changed it. |
| P23 | How `mise run ship` builds the PR body, and therefore where the F6 text goes | not read | **A**: the coordinator places the text |
| P24 | `ship` refuses a dirty working tree, untracked files included (`status --porcelain`) | `python/src/dotfiles_setup/pr.py:559-562`, `:602-607` | L |
| P25 | `doctor.collect` passes `repo_root` through unresolved, so `setup.repo_root` equals the fixture's `repo` path and exact-path assertions are stable | `python/src/dotfiles_setup/doctor.py:425-443` | L |

## Coordinator actions (not the implementer's)

1. **Re-confirm the untracked set:** run `git -C WT status --porcelain`. Every `??` under
   `docs/research/kb/reports/agents/` goes into commit 2 by name. Any other `??` or ` M` entry is triaged before ship
   (P20 `A`).
2. Read `gh issue view 1655 --json title,body`, then settle Q0 and the `Closes`/`Refs` line.
3. Answer Q0-Q4, then dispatch to `codex-sol-implementer` (effort xhigh) with this file.
4. After the lane hands back:
   - read its report from disk;
   - run §5.5;
   - make commits 1 and 2;
   - check that the branch base contains the paths Revision D cites, or accept that they are on main only (P4).
5. At ship, apply the F6 text (§6). The post-merge real sync stays owed (Ray 2026-10-03, `docs/specs/research-gate-sync.md:132`).
6. Decide the review budget for `291e0d15..<new>` (§5.5).

## §0 RULINGS (coordinator e67105a8, 2026-10-04)

- **Q0:** implement N1–N3. #1655 IS those items (its body was read: N1 is the hint, N2 the paths, N3 the ordering), so the commit trailer is `Closes #1655`.
- **Q1:** use the inline pointer at the end of `:56`, plus the appended Revision D and D.1 sections, as drafted.
- **Q2:** drop the suffix in composite states (recommended).
- **Q3:** commit mode `caller`. The lane stages; the coordinator runs lint, full pytest, verify and lint-docs, then commits.
- **Q4:** `-n 2`, the repo norm. D.1 records the r1 `-n 0` instruction as a deviation.
- **P20 CONFIRMED:** `git -C .claude/worktrees/research-gate-sync status --porcelain` lists exactly the five `??` reports named in this spec, and nothing else.
- **Premise-verifier r1.3** (`docs/research/kb/reports/agents/premise-verifier-research-gate-sync-r1.3.md`): READY TO DISPATCH. Fold in these MISSING items:
  - **(a) §5.2 `_alter_research_gate_history`:** use EXPLICIT set membership for the new composite cell names. Never test a substring with `in`: `"dirty"` also matches `tracked-dirty-behind`/`unknown-dirty-branch`, and `"branch"` also matches `branch-failure`/`branch-behind`.
  - **(b) S3:** wrap `hook_runner` in a call-recording runner (precedent `tests/test_research_gate_sync.py:276-280`), so that "no fetch or merge ran" is actually asserted.
  - **(c) S3 `ahead` cell:** build it with the `:273-274` recipe.
  - **(d)** Log X5 as green-at-baseline in §5.1, like X1–X4.
  - **(e)** Commit the r1.3 premise report by name, along with the five untracked reports.
