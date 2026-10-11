# Spec — codex-takeover Phase B2a: "Codex can ship" (provider-qualified coordinator identity)

Ratified by the architect, 2026-10-05.

- Ray asked for this minimal piece BEFORE the rest of batch 2: "i want to start batch 2 (or a
  minimal 'Codex can ship' piece) sooner".
- Ruling W5b, from `docs/specs/codex-takeover-2026-10-05.md` § Round 5: "Yes, provider identity
  in Phase B".
- Issue #1720; umbrella #1721.
- Design: `docs/specs/codex-takeover-phaseB-design.md` §"W5b" items 4-6.
- This builds ON TOP OF the uncommitted, finished Phase B1 changes in this worktree. Do not revert
  or reformat them.

## 1. Objective

When Claude's budget is gone, a codex session can become the dotfiles coordinator and perform the
coordinator-only writes. Those writes are `handoff-inbox plan-apply`, `queue-append` and
`inbox-edit`, which together record SLOT GO and ship-queue entries. A later Claude coordinator
then takes the role back automatically.

The failure this prevents: nothing can be granted, queued or shipped while Claude is out, because
`require_newest_coordinator` recognises only a Claude harness job record
(`python/src/dotfiles_setup/handoff_inbox.py:174-204`).

Shape: a provider-qualified identity plus "newest coordinator wins" across BOTH providers.

- **Claude:** unchanged. The identity is the `CLAUDE_CODE_SESSION_ID` job record
  (`~/.claude/jobs/*/state.json`), with `name` + `createdAt`.
- **Codex:** a new explicit **claim**.
  - Command: `mise run handoff-inbox -- coordinator-claim --name <dotfiles-…coordinator>`. It is
    run from inside a codex session; the identity is `CODEX_THREAD_ID` (precedent:
    `python/src/dotfiles_setup/main.py:556`).
  - The claim writes a record `{provider: "codex", threadId, name, createdAt}` under the main
    checkout's gitignored state, in a location you choose under `.agent/state/`. The write is
    locked with the existing `state_lock`.
  - The name must match `is_coordinator` (`session_common.py:94`).
- **Authorization:** the caller is authorized iff its own identity is the NEWEST `createdAt`
  among all Claude coordinator job records AND all codex claim records. One rule decides both
  directions:
  - a codex claim supersedes older Claude coordinators (takeover);
  - a newer Claude coordinator supersedes the codex claim (hand-back).
- **Release:** `coordinator-release` retires the caller's own codex claim. A retired claim never
  authorizes anything.

The module docstring's honesty paragraph stays and is extended. This is a mistake-preventer, not
an access control: the identity variables are caller-supplied.

## 2. Files (allowlist)

- `python/src/dotfiles_setup/handoff_inbox.py`
- `python/src/dotfiles_setup/session_common.py` — only if a shared helper genuinely belongs there
- `tests/test_handoff_inbox.py`
- `docs/agents/session-orchestration.md` — replace the "blocked until B2" codex-write note with
  the claim/release procedure, for both directions
- `.claude/skills/coordinator-handoff/SKILL.md`, regenerated via `mise run skills-mirror` — only
  if the hand-back step must mention the release
- `docs/research/kb/reports/agents/codex-takeover-phaseB2a-validation-2026-10-05.md` (new; written
  incrementally)

## 3. Interfaces

- `require_newest_coordinator(env, jobs_dir, *, claims_dir=…) -> str` keeps its name and return.
  It raises `InboxError` with a message naming the actual newest coordinator and its provider.
- New subcommands `coordinator-claim --name <n>` and `coordinator-release`, both added to
  `add_subcommands`. Exit codes: 0 on success; non-zero with a `refused:` message on any refusal.
- Claim refusals:
  - no or empty `CODEX_THREAD_ID`;
  - a name failing `is_coordinator`;
  - `CLAUDE_CODE_SESSION_ID` is ALSO set (ambiguous provider; a Claude session must not mint a
    codex claim);
  - an unparseable existing claims store, which fails closed and never resets.

## 4. Constraints and invariants

- Claude-side behaviour is byte-for-byte unchanged when no codex claim exists. Existing
  `tests/test_handoff_inbox.py` cases must pass unmodified.
- Every check runs twice: before reading input, and again under the target's lock. This is the
  existing pattern, `handoff_inbox.py:390-396`.
- The newest-`createdAt` comparison ignores `state`. The reason is the existing ruling: a `done`
  record may be a live idle session.
- Claims are the codex analogue of job records: append/replace via an atomic write, no silent
  reset.
- Clock: inject `now` in tests (the #748 class). No wall-clock sleeps.
- No user-level files. No hook or `hook_guard` changes (process-hardening owns guard parity).
  No GitHub writes, no push, no `gh pr`. Never `--ephemeral`.
- No SLOT GO is held:
  - run ONLY targeted pytest (`tests/test_handoff_inbox.py`), ruff, ty on the touched files, and
    `mise run lint-docs`, all with file-captured rc;
  - record full lint/pytest/verify as NOT_RUN.

## 5. Verification (real arms; record each rc)

1. Unit tests: codex claim newest → authorized; an older Claude coordinator → refused;
   a newer Claude coordinator after the claim → the codex claim refused (hand-back); a released
   claim → refused; both env vars set → refused; a bad name → refused; a corrupt store → refused
   and the store is not rewritten.
2. Concurrency: two claims racing under the lock → exactly one newest; the under-lock re-check
   refuses a superseded writer.
3. A realistic mutation, shown red then restored: delete the codex branch of the newest
   comparison (as if the claim store were never read). The takeover test must fail.
4. A REAL public-entrypoint probe, against a temporary `--jobs-dir` and a temp claims dir (never
   the live main-checkout state):
   - `CODEX_THREAD_ID=<real current thread id> mise run handoff-inbox -- coordinator-claim …`
     → rc 0;
   - then `queue-append` → rc 0;
   - then a fixture Claude job record newer than the claim → `queue-append` refused.

## 6. Commit

`caller` — do NOT commit. The architect commits B1 + B2a after full gates under SLOT GO.

## 7. PREMISES

| # | Kind | Claim | Source |
|---|---|---|---|
| 1 | I | `require_newest_coordinator(env, jobs_dir) -> str` scans `jobs_dir.glob("*/state.json")`, keeps the max `createdAt` among coordinator names, refuses unless own == newest | `handoff_inbox.py:174-204` |
| 2 | I | Authorization runs before input and again under lock via `authorize` closure | `handoff_inbox.py:390-396`, `_locked_write` at `:240` |
| 3 | L | `SESSION_ENV = "CLAUDE_CODE_SESSION_ID"` | `handoff_inbox.py:80` |
| 4 | P | `CODEX_THREAD_ID` already used as the native codex thread id default | `main.py:556-557` |
| 5 | I | `is_coordinator(name)` fullmatches `COORDINATOR_NAME_RE` | `session_common.py:94-96` |
| 6 | L | Docstring ruling: newest-createdAt ignores `state` | `handoff_inbox.py:22-28` |
| 7 | A | `CODEX_THREAD_ID` is set inside every codex exec/interactive session — VERIFY in this run (probe 4 uses the real value) | — |
| 8 | A | No other module calls `require_newest_coordinator` with positional args that a new keyword would break — VERIFY by grep | — |

## Amendments r2 (architect, after premise-verifier)

The verifier report is saved verbatim at
`docs/research/kb/reports/agents/premise-verifier-codex-takeover-b2a-2026-10-05.md`. Verdict:
correct-first, with 2 blockers. All 8 recommended amendments are ADOPTED, and they override §1-§7
wherever they conflict.

- **A1 — the claims location is explicit and resolved by each caller.**
  - `require_newest_coordinator(env, jobs_dir, *, claims_dir: Path | None = None)`. `None` means
    "no claims" (unchanged Claude-only behaviour), so the existing direct-call unit tests stay
    unmodified and never read live state.
  - EVERY CLI caller passes the resolved dir: `_dispatch` in `handoff_inbox.py`,
    `session_registry.py:735-737` (`lane-cards --write`) and `coordinator_handoff.py:1470-1472`
    (`snapshot-cards`).
  - The dir comes from `--claims-dir` when given, else from `main_checkout(...)`.
  - The allowlist (§2) is widened to `python/src/dotfiles_setup/session_registry.py`,
    `python/src/dotfiles_setup/coordinator_handoff.py`, `tests/test_session_registry.py` and
    `tests/test_coordinator_handoff.py`.
  - So a codex coordinator may also write card snapshots: four coordinator writes, not three.
- **A2 — `--claims-dir` is a CLI flag**, added the same way as `--jobs-dir` (`handoff_inbox.py:334-337`).
  Probe 4 uses it with a temp dir.
- **A3 — the clock and its ordering.**
  - The claim `createdAt` comes from an injected clock, at microsecond precision or finer,
    tz-aware, and must parse with `_created_at` (`handoff_inbox.py:162-171`).
  - "Newest" is the max over `(timestamp, provider, id)`.
  - Authorization requires an IDENTITY match with that max (provider + session/thread id), not a
    timestamp match. This closes the equal-timestamp hole at `:198`.
- **A4 — compare-and-swap on the claim.**
  - `coordinator-claim --name <n> --supersedes <name of current newest coordinator>`, re-checked
    under the claims lock and refused on a mismatch.
  - This stops an accidental or blind claim by a lane, gives two racing claims exactly one winner,
    and makes a stale re-claim fail after a hand-back.
  - A claim may not reuse a name already carried by a Claude job record or another claim.
- **A5 — store primitives.**
  - Use `read_state` (fails closed on corrupt data, never resets), `write_state` (atomic replace)
    and `state_lock` (`session_common.py:104-152`).
  - `authorize` reads claims WITHOUT taking the claims lock (writes are atomic replaces), so there
    is no lock-order inversion with the target lock.
  - `coordinator-claim` and `coordinator-release` never take a target lock.
- **A6 — dispatch order.** The `coordinator-claim` and `coordinator-release` branches come BEFORE
  the coordinator-gated `else` in `_dispatch` (`handoff_inbox.py:386-395`).
- **A7 — the race test** uses `threading` with a `threading.Event`/`Barrier` handshake, not
  `time.sleep`. The pattern at `tests/test_handoff_inbox.py:284-316` may be reused with that change.
- **A8 — extra PREMISES rows.**
  - I `read_state`/`write_state`/`state_lock`: `session_common.py:104-152`.
  - I external callers: `session_registry.py:735-737`, `coordinator_handoff.py:1470-1472`.
  - L `now_iso` has seconds resolution and is not injectable: `session_common.py:155-157` (so do
    not use it for claims).
  - L a naive timestamp is dropped by `_created_at`: `handoff_inbox.py:170-171`.
- **Reuse:** the fixtures `repos`, `_job` and `jobs_dir`, and `_run` (`tests/test_handoff_inbox.py:38-89`).
- **Residual, accepted:** `CODEX_THREAD_ID` is consumed but nothing in this repo sets it (R7);
  probe 4 settles it live. A refusal on `PLANNING_DISABLED=1` is NOT added, because only
  `codex_lane.py` sets it, so it is a partial marker. CAS is the guard.

## Amendments r3 (architect, after the re-verify; verdict "ready to dispatch")

- **R1 — flags on the other callers.** Add `--claims-dir` to `snapshot-cards`
  (`coordinator_handoff.py:1465`), and add both `--jobs-dir` and `--claims-dir` to `lane-cards`
  (`session_registry.py:709-716`). Defaults resolve from `main_checkout`, so end-to-end tests can
  point at temp stores.
- **R2 — CAS edges.**
  - With no coordinator at all, `--supersedes none` is the sentinel.
  - A Claude job record created between a claim's check and its write sits outside the claims
    lock and loses to the claim by timestamp. This is ACCEPTED as inherent, and must be documented
    in the module docstring.
- **R3 — identity on the Claude side** comes from the record's `sessionId`, as `job_record`
  already does (`session_common.py:83`).
