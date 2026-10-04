# Cold review — `f8a8f402` (session-start canonical ledger)

- **Diff**: `13af2848..f8a8f402`, one commit on branch `fix/coordinator-handoff-churn`.
- **Reviewer**: cold-reviewer (Opus), by ref, round 1. Open hunting, plus Q-FRESH, Q-SCOPE and Q-CLAIM.
- **Spec checked against**: `docs/specs/session-start-canonical-ledger.md` @ `f8a8f402`.
- **Memory**: consulted (`.claude/agent-memory-local/cold-reviewer/`: review_method, mutation_harness, harness_identity_facts, handoff_claim_checker_review).
- **Status**: COMPLETE (static review; see E3 for why there is no pytest or mutation run).
- **Verdict**: **SHIP, conditional.** Static reading found 0 HIGH and 0 MEDIUM. The implementation matches spec §3 and constraints 1–6, and every V1–V6 arm has a test that, read statically, has teeth. The condition: one targeted run of `uv run --project python pytest tests/test_session_start.py -x -q` from the `handoff-churn` worktree, plus mutations M1/M3/M5 below. I could not execute either (E3). The commit's "pytest/lint/verify/lint-docs rc=0, nine mutation controls failed" is an INHERITED claim I could not re-derive.
- ⚠️ **Location.** The caller asked for this report at
  `.claude/worktrees/handoff-churn/docs/research/kb/reports/agents/cold-review-canonical-ledger-f8a8f402.md`. A stub
  was created there first. The harness then isolated this session in worktree `handoff-2026-10-04i`, and every later
  write to the `handoff-churn` path was refused with *"Edit the worktree copy of this file instead of the
  shared-checkout path"*. This file in `handoff-2026-10-04i` is therefore the full report. The `handoff-churn` copy is
  a STALE stub (`Status: IN PROGRESS`, no findings), untracked, in the reviewed worktree. Delete or overwrite it.

## Findings

| # | Sev | Claim | file:line | Evidence |
|---|---|---|---|---|
| F1 | LOW | "Shared across all linked worktrees" holds only for a worktree whose **checked-out code contains `f8a8f402`**. The hook runs the firing checkout's own Python. A worktree branched before the merge keeps writing a checkout-local claim and re-granting the reload. The SKILL.md sentence and the commit message state it unconditionally. | `.claude/skills/session-start/SKILL.md:11-13`; mechanism `python/src/dotfiles_setup/main.py:3242` + `register.ts` `python()` (`cwd: CLAUDE_PROJECT_DIR ?? session.root()`) | E2 (the defect fires from a worktree's own `project_root`), E4 |
| F2 | LOW | The fallback warning is operator-invisible. It goes to the module logger, which writes to stderr, and `register.ts` `python()` keeps only `exitCode`/`stdout`. The `StartDecision.warnings` channel is not used either. When `git worktree list` fails in a worktree, the double-claim defect silently returns. Spec constraint 2 is met literally. | `session_start.py:452-458` | E5 |
| F3 | LOW | Worst-case `decide` latency now exceeds the hook's `DECIDE_TIMEOUT_MS = 60_000`. `main_checkout` (30 s timeout) runs before the canonical lock (10 s), plus a nested legacy lock (10 s), on top of the pre-existing `ps` (30 s) and two `git` calls (10 s each). A timeout after `write_state` consumes the claim with no reload. The overrun already existed; the diff widens it from ~60 s to ~100 s. | `session_start.py:450`, `:291`; `session_common.py:32,191`; `register.ts:28` | E6 |
| F4 | LOW | Wrong log text: the `renamed` pre-import logs "state write failed" for a lock timeout or for an unreadable **legacy** file, which are read-side failures. The test pins rc 1 but not the message. | `session_start.py:465-467` | E7 |
| F5 | LOW | Migration covers only the **firing** checkout's local ledger, so the rationale of spec constraint 3 ("a session already claimed must not be re-granted after this change ships mid-session") is only partly met. Example: a session claimed by pre-fix code in worktree W, which later fires from main, is re-granted, because main's legacy dir *is* the canonical dir. The literal constraint (checkout-local) is met; this is a spec gap and transient. Two live UUIDs are in exactly this state (E2: `bee298cf`, `4daaf7e1`). | `session_start.py:450-451`, `:282-290` | E2, E8 |
| F6 | INFO | Help text and SKILL.md omit the fallback: on resolver failure the default is `<project>/.agent/state/session-start`, not `<main-checkout>/…`. | `session_start.py:436`, `:453`; SKILL.md:11-12 | read |
| F7 | INFO | The `resolve()` self-equality guard in `_read_claim` is reachable only when the canonical file exists **without** an `action` key, which no writer produces. It is effectively an equivalent mutant and is untested. Removing it would make the same process re-flock its own lock file, giving `state-locked` after 10 s. Harmless. | `session_start.py:285-286` | E9 |
| F8 | INFO | `pending` used to be read-only and is now a writer, because migration calls `write_state` under the canonical lock. Spec constraint 4 says locking and persistence are "unchanged". The change is implied by constraint 3 and is done under the right lock. Noted for the record. | `session_start.py:383-385`, `:294` | read |
| F9 | INFO / UNVERIFIED | The new `linked_checkout` fixture runs `git worktree add`, which fires `post-checkout`, under the ambient global gitconfig (any `core.hooksPath`). It shares the class of the pre-existing `repo` fixture (`git commit`). This is out of scope (Q-SCOPE: sibling, test hermeticity). | `tests/test_session_start.py:529-531` | memory `chezmoi_template_and_git_ownership_review` |

No HIGH and no MEDIUM.

## Spec conformance (§2–§5)

| Spec item | Verdict | Where |
|---|---|---|
| §2 allowlist | holds. The diff touches only `session_start.py`, `tests/test_session_start.py`, the two SKILL.md files and the spec itself. `test_session_start_hook.py` is untouched. Its harness scripts `$.process.run`, so it never reaches Python (`harness.ts:64-72`). | `git diff --stat` (E1) |
| §3 CLI unchanged | holds. Same args, same JSON; only the help string changed (F6). | `session_start.py:431-441` |
| §3 `--state-dir` absolute precedence | holds. When it is set, `main_checkout` is never called and `legacy_state_dir` stays `None`. | `:446-448` |
| §3 default = `main_checkout(project_root)/STATE_SUBDIR` | holds | `:450` |
| §3 naming stays on the event cwd | holds. `_classify` still reads `request.cwd`. | `:235-239` |
| C1 reuse `main_checkout`, no env scrub | holds. `main_checkout` has a `runner` seam but no env seam, so it is left as is. | `session_common.py:183-203` |
| C2 fail safe on `SessionError` + warning | holds (F2: the warning cannot be seen) | `:452-458` |
| C3 migration, local counts, no delete | holds for the firing checkout (F5) | `_read_claim` `:274-296` |
| C4 lock/persistence semantics | holds in substance. Lock order is always canonical→legacy, so there is no cycle (E9). `pending` now writes (F8). | `:307-317`, `:291` |
| C5 ruff/ty/no suppressions | no suppressions in the diff (read). ruff/ty were not run (E3). | — |
| C6 real git fixtures, no `main_checkout` mock | holds. `git init -b main` + `git worktree add`. | test `:45-52`, `:524-542` |
| V1–V6 | each has a test whose assertions would fail under the matching mutation, by static reading (table below) | test `:572-856` |
| A1 "no other consumer reads `<checkout>/.agent/state/session-start`" | **UNVERIFIED** (no grep possible, E3). Partial: `coordinator_handoff.py:108` uses its own `.agent/state/coordinator-handoff`, and `session_orphans.py` has no ledger reference. | read |

### Mutation table (STATIC — none executed, E3)

| M | Mutation | Expected red test (by reading) |
|---|---|---|
| M1 | `:450` → `project_root / STATE_SUBDIR` | V1 both params: the second decide returns `keep`/`reload=True` |
| M2 | delete `:451` (legacy off) | V5 all three commands |
| M3 | delete the `renamed` pre-import `:460-467` | V5[renamed]: `mark_renamed` finds no action, rc 2 |
| M4 | drop `legacy_state_dir=` from the `pending` call `:477` | V5[pending]: `already-ran`/`None` ≠ `rename`/name |
| M5 | delete `write_state(path, legacy)` `:294` | V5[decide], at the follow-up `decide` from `repo`: new claim instead of `already-ran` |
| M6 | delete the `except SessionError` fallback | V4: an uncaught exception |
| M7 | swap precedence (legacy first) | `test_canonical_claim_wins_over_conflicting_local_claim` |
| M8 | delete the `resolve()` guard `:285-286` | none (F7, equivalent) |

## Q-FRESH

| Decision → action | Re-validated under the lock immediately before acting? |
|---|---|
| `decide`: claim read → `_classify` → `write_state` | yes. Everything happens inside `state_lock(path)` `:307-317`. |
| migration: legacy read → canonical write | yes. The legacy read is under the legacy lock and the canonical write under the caller's canonical lock (`:291-294`). The `stat()` at `:288` is outside the lock, but a racing delete only yields `{}`, so it degrades to "no import". |
| `renamed`: pre-import (lock, release) → `mark_renamed` (re-lock, re-read) | yes. `mark_renamed` re-reads under its own lock (`:347-348`). |
| `main_checkout` resolved once per process, then used | acceptable. It is a single CLI call. |

## Q-SCOPE

All of F1–F8 are in scope for this spec, as cheap docs or log fixes or accepted gaps. F9 (fixture git hermeticity) is a
sibling, and the ticket recommendation is: "isolate `GIT_CONFIG_GLOBAL`/`core.hooksPath` in
`tests/test_session_start.py` fixtures". The sibling module `coordinator_handoff.main` resolves
`main_checkout(Path.cwd())` and fails **closed** (rc 2, `:1266-1272`). This module resolves
`main_checkout(project_root)` and fails **safe**. The two conventions coincide in production because the process cwd
is `projectDir`. The spec chose fail-safe deliberately, so this is not a finding.

## Q-CLAIM — every operator-facing string added or changed

| String (clause) | Enforcing line | Outcome |
|---|---|---|
| SKILL.md "state by default in the repository's main checkout" | `session_start.py:450` | holds, except on fallback `:453` (F6) |
| SKILL.md "shared across all linked worktrees" | `:450` + the running checkout's code | conditional on that worktree's code containing the fix (F1) |
| SKILL.md "written before it answers" | `:317` | holds |
| help "Override `<main-checkout>`/.agent/state/session-start" | `:450` | fallback omitted (F6) |
| warning "canonical checkout unavailable; using <dir>: <exc>" | `:452-458` | holds; invisible to the operator (F2) |
| `_read_claim` docstring "import an old local claim without moving it" | no unlink anywhere; V5 asserts the legacy bytes are unchanged | holds |
| log "session-start renamed: state write failed" (new call site) | `:465-467` catches read and lock failures | clause wrong (F4) |
| commit "Linked worktrees now share the main checkout's ledger" | same as SKILL | conditional (F1) |
| commit "local records migrate without deletion" | `_read_claim` | holds for the firing checkout (F5) |
| commit "overrides keep precedence" | `:446-448` | holds |
| commit "pytest/lint/verify/lint-docs rc=0, nine mutation controls failed" | — | **UNVERIFIED** (inherited; E3) |

## Evidence log

### E1 — refs resolved

`13af2848` = `13af28480ae4…`, `f8a8f402` = `f8a8f402127a…`; one commit, 5 files (+496/-13). Worktree `handoff-churn`
was on `fix/coordinator-handoff-churn` at HEAD `f8a8f402`, and `git status --short` printed nothing at review start.
Line numbers come from `git show f8a8f402:<path>` for `session_start.py`. Lines for tests and SKILL.md were read from
the clean worktree at that HEAD; the worktree could not be re-checked for drift after E3.

### E2 — premise P4 reproduced from live gitignored ledgers (both arms)

I scanned every `.claude/worktrees/*/.agent/state/session-start/*.json` and checked whether the same UUID exists in the
main checkout's `.agent/state/session-start/`. Control arm: the main ledger holds 56 files, so the scan can see claims.

| worktree | uuid8 | worktree claim `at` | in main? | main claim `at` |
|---|---|---|---|---|
| coordinator-bgisolation | c769e1a1 | 2026-10-04T11:57:13 | yes | 2026-10-04T11:50:22 |
| handoff-2026-10-03l | c1a35607 | 2026-10-03T19:37:10 | yes | 2026-10-03T19:30:36 |
| handoff-2026-10-03n | aacf2ab7 | 2026-10-03T20:06:27 | yes | 2026-10-03T19:49:23 |
| L1-docs-rules | bee298cf | 2026-10-03T14:34:52 | no | — |
| handoff-automation-research | 4daaf7e1 | 2026-10-03T14:15:36 | no | — |

The defect is real and recurs: three UUIDs were each claimed twice. P4 holds exactly. In production `project_root`
does follow into the worktree. `main.py:3242` is `project_root = Path(__file__).parent.parent.parent.parent`, which
is the running checkout's editable install. `register.ts` `python()` runs `uv run --project python …` with
`cwd: (await $.env.get("CLAUDE_PROJECT_DIR")) ?? (await $.session.root())`.

The Claude Code docs (`$CC/worktrees.md:46-49`, `$CC/hooks.md:626-631`) say `${CLAUDE_PROJECT_DIR}` "stays put" after
entering a worktree. In the function-hook engine, though, the worktree-local claims prove that `projectDir` resolved
to the worktree for those calls. Which branch of the `??` produced that is **UNVERIFIED**; the code path is the same
either way.

### E3 — Bash became unavailable mid-review (harness isolation guard)

After about 15 tool calls, every Bash call was refused, even a bare `pwd` or `echo probe`, with *"This session is
isolated in the worktree …/handoff-2026-10-04i, but this command's working directory resolved to the shared
checkout … Refusing to run it there"*. Re-probed once more later, with the same refusal. A leading
`cd <isolated worktree> &&` is refused as well, because the guard judges the tool call's cwd, which resets to the
shared checkout on every call, not the command text. Read still works. Write/Edit work only inside
`handoff-2026-10-04i`. **Consequence**: the allowed targeted pytest run, every mutation in the table above, the
skills-mirror check, ruff/ty, and the A1 grep could not be executed. Everything they would have settled is labelled
STATIC or UNVERIFIED.

### E4 — F1 mechanism

The Python that `decide` runs is `<projectDir>/python`'s editable install, so `project_root` (`main.py:3242`) is that
checkout, and so is the code. A checkout without `f8a8f402` runs the old `main()` (`args.state_dir or project_root /
STATE_SUBDIR`) and writes locally. 40 worktrees exist under `.claude/worktrees/`, and each branch's ancestry decides
its behaviour. In practice this is transient: new handoff worktrees are cut from main. The doc sentence, however, is
unconditional.

### E5 — F2 surface

`register.ts:103-111` `python()` returns `{exitCode, stdout}`, and `parseStart` (`:85-99`) reads only
`action/reload/name/prefix`. stderr is never surfaced, and neither is `warnings`. The fallback's only trace is
therefore in a stream nobody reads.

### E6 — F3 budget arithmetic

| Source | Bound |
|---|---|
| `register.ts:28` | `DECIDE_TIMEOUT_MS = 60_000` |
| `session_common.py:32` | `MAIN_CHECKOUT_TIMEOUT_S = 30` |
| `session_common.py:33` | `STATE_LOCK_TIMEOUT_S = 10.0`, now taken twice (canonical, then legacy, `:291`) |
| `reap.py:72` | `_PS_TIMEOUT_S = 30.0` (in `user_name`) |
| `session_start.py:77` | `_GIT_TIMEOUT_S = 10` × 2 (`current_branch`, `default_branch`) |

Pre-diff worst case: 10 + 30 + 20 = 60 s, plus `uv` startup. Post-diff: 30 + 10 + 10 + 30 + 20 = 100 s.

### E7 — F4

`main()` `:459-467`:

```python
with state_lock(path):
    _read_claim(path, legacy_state_dir, timeout_s=STATE_LOCK_TIMEOUT_S)
except OSError:
    logger.exception("session-start renamed: state write failed")
```

`StateLockedError` and `StateUnreadableError` are both `OSError` subclasses (`session_common.py:51-56`). The test
`test_canonical_corrupt_legacy_claim_fails_closed[renamed]` asserts `rc == 1` only.

### E8 — F5 scenario

Session U is claimed in W by pre-fix code, so only `W/.agent/state/session-start/U.json` exists. U then fires from
main running post-fix code. `state_dir = main/…` and `legacy_state_dir = main/…` are the same dir, `_read_claim`
returns `{}` at `:285-286` (or at `:288-290` when the file is missing), and U gets a fresh claim with `reload=True`.
`bee298cf` and `4daaf7e1` (E2) are worktree-only claims of exactly this shape.

### E9 — lock order

New code always takes canonical (`main/U`) then legacy (`W/U`) and never the reverse. Pre-fix code takes only its own
local file. In the main checkout, legacy equals canonical and the guard skips the second lock. No two-lock cycle is
possible, and every lock is bounded at 10 s regardless.

## Appendix — reviewer memory update (BLOCKED, for the coordinator to apply or drop)

The write to `.claude/agent-memory-local/cold-reviewer/` in the shared checkout was refused by the same isolation
guard as E3. I did not write an orphan copy into this worktree, because a copy there would never be loaded. Two
durable entries are proposed:

1. **New `per_checkout_state_review.md`.** For a fix that moves `.agent/state/*` to a canonical main-checkout
   location, the decisive arm is the LIVE ledger cross-check (E2), which is one `find` + `jq` call with the main
   ledger count as control. The code that runs in a worktree is that worktree's own (`main.py:3242` + `register.ts`
   `python()` cwd), so "shared across worktrees" holds only for branches that contain the fix. Recurring gaps:
   logger warnings are invisible to `register.ts`; `DECIDE_TIMEOUT_MS=60_000` budget arithmetic; check that the
   nested-lock order is global. Sibling convention: `coordinator_handoff` uses `main_checkout(Path.cwd())` and fails
   closed, while `session_start` uses `main_checkout(project_root)` and fails safe.
2. **Append to `harness_identity_facts.md`.** When the PARENT session becomes worktree-isolated mid-review, the
   subagent loses ALL Bash, even `pwd`, because its tool cwd resets to the shared checkout and a leading `cd` does not
   help. Write/Edit are refused outside the isolated worktree, and that includes this memory dir. Run the test and
   mutation arms FIRST and create the report early. A report path in a sibling worktree becomes unwritable.

## GitHub repos touched

_None._ Local repo sources and the knowledge-base offline Claude Code docs only.
