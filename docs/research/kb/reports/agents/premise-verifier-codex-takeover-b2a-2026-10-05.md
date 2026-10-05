# premise-verifier — codex-takeover Phase B2a spec (2026-10-05, verbatim)

PREMISE REPORT — docs/specs/codex-takeover-phaseB2a-spec.md (read-only lane; I wrote nothing, so the coordinator needs to persist this report)

ROWS: 8 checked. 5 CONFIRMED (0 with provenance corrected), 0 REFUTED, 0 UNVERIFIABLE, 3 ASSUMED (1 of them checkable).

- **R1 — CONFIRMED.** handoff_inbox.py:174-204. The function takes `(env, jobs_dir)` positionally. It globs `*/state.json`, keeps the max `createdAt` among coordinator names (strict `>`), and refuses at :198 when `newest[0] != own_at`. The comparison is timestamp-only (tie-break hole below).
- **R2 — CONFIRMED.** The `authorize` closure is at :390-391, the pre-input call at :395, and the under-lock call is `_locked_write` :254-255 (defined at :240).
- **R3 — CONFIRMED.** handoff_inbox.py:80 reads `SESSION_ENV = "CLAUDE_CODE_SESSION_ID"`.
- **R4 — CONFIRMED.** main.py:556-557 is session-review's `--codex-session-id` default, `os.environ.get("CODEX_THREAD_ID", "").strip() or None`. The data matches: same env var, same "nonempty only" semantics.
- **R5 — CONFIRMED.** session_common.py:94-96, with the regex at :41: `^dotfiles-.+\.coordinator$`.
- **R6 — CONFIRMED.** handoff_inbox.py:22-28 (the "whatever its state" ruling).
- **R7 — ASSUMED.** No code sets `CODEX_THREAD_ID`. Only consumers exist (main.py:556, tests/test_session_review.py:1199/1275). Probe 4 settles this live. This is not load-bearing for the unit design.
- **R8 — ASSUMED (checkable).** Two other callers exist, and both pass two positional args, so a keyword-only `claims_dir` with a default breaks neither:
  - session_registry.py:735-737 (`lane-cards --write`): `require_newest_coordinator(os.environ, default_jobs_dir())`, called before and under its state lock at :538/:540.
  - coordinator_handoff.py:1470-1472 (`snapshot-cards`).
  - This should have been a cited row. Its semantic consequence is the first MISSING item.

MISSING:

- **The default for `claims_dir` decides whether the other two callers see codex claims.** docs/agents/session-orchestration.md:173 counts card-snapshot writes as coordinator writes. Neither caller is in the allowlist (§2).
  - Option A: default None means "no claims". Then a codex coordinator is refused for `lane-cards --write` and `snapshot-cards`. A worse effect: a codex claim newer than every Claude record is invisible there, so an older Claude coordinator still passes. That breaks the "one rule, both directions" premise.
  - Option B: default resolves `main_checkout(Path.cwd())` inside the function. Then `test_newest_coordinator_check_has_both_arms` (tests:147) and `test_an_idle_newer...` (tests:319) read the LIVE main-checkout claims store, because they run without the `repos` fixture and cwd is the real worktree. A live codex claim would turn the existing tests red, which violates "pass unmodified".
  - The architect must pick one and either widen the allowlist to session_registry.py and coordinator_handoff.py or state the gap. **Blocking.**
- **`_dispatch` gates every unknown verb.** handoff_inbox.py:386-395: every verb except list/read/append falls into the `else` that calls `authorize()` first. `coordinator-claim` and `coordinator-release` need their own branches ahead of that `else`, or a codex caller is refused by the Claude-only check. The spec doesn't say this. Add one line.
- **No CLI override for the claims location.** Probe 4 needs "a temp claims dir", but §3 defines no flag. The `--jobs-dir` loop at :334-337 adds a flag to every verb. Without a matching flag, the probe can only redirect the store by running from a throwaway git repo, because `main_checkout` follows cwd. Add `--claims-dir` to §3, or state the throwaway-repo method.
- **The timestamp is too coarse and ties are not broken.**
  - `now_iso()` (session_common.py:155-157) has seconds resolution and cannot be injected. Claude records carry milliseconds ("…19:41:32.500Z", tests:82).
  - Ties pass both callers: at :198 two records with equal `createdAt` both satisfy `newest[0] == own_at`. Two claims in the same second are therefore BOTH authorized, so §5.2 "exactly one newest" fails by construction.
  - Specify: inject `now`, store at least microseconds with an offset (a naive stamp is dropped at :171), and break ties deterministically (e.g. by provider + id), comparing identity, not just the timestamp.
- **A re-claim seizes the role back.** "append/replace" means one thread re-running claim refreshes `createdAt`, which beats a Claude coordinator that took the role back after it. The spec doesn't say whether a re-claim may supersede a newer Claude record.
- **Claim name uniqueness is not specified.** The regex accepts any self-asserted `dotfiles-<anything>.coordinator`. On the Claude side the name comes from the harness record; on the codex side it is caller text. The spec doesn't say whether a claim may reuse a name a Claude record already carries; that makes refusal messages ambiguous.
- **`state_lock` fits.**
  - session_common.py:130-152: flock on `<file>.lock`, a 10 s bound, and `StateLockedError` (an OSError), which `main` turns into rc 2 at :426-428.
  - Pair it with `read_state` (:104-116), which raises `StateUnreadableError` on corrupt data and never resets, and `write_state` (:119-127, an atomic replace). That pairing gives "fail closed, never reset" for free; the spec should name both.
  - Lock order: `authorize` runs under the TARGET lock (:254). If it also took the claims lock, `claim` must never take a target lock, or the two can deadlock. Recommend that `authorize` read claims WITHOUT the claims lock, which is safe because writes are atomic replaces. State this.
- **Fixtures for the lane to reuse:** `repos` (tests:38-59, a real linked worktree, cwd = lane), `_job` (:62-75), `jobs_dir` (:78-84), `_run` through `setup_parser`/`coordinator_handoff.main` (:87-89), and the under-lock race pattern at :284-316. That race test uses `threading` + `time.sleep(0.5)`, which conflicts with §4 "No wall-clock sleeps". Either allow that pattern for §5.2 or require an Event-based handshake.
- **Any codex process can claim.**
  - The only identity is a nonempty `CODEX_THREAD_ID` plus a regex-valid name. Any `codex-sol-implementer`/`sdlc-team` lane, which runs with full access (CLAUDE.md lane table; codex_lane.py:140 shows lanes inherit the environment plus `PLANNING_DISABLED=1`), could run `coordinator-claim` and seize every coordinator write from a LIVE Claude coordinator, without any expired-budget condition.
  - Under the "mistake-preventer, not access control" stance (:30-34) deliberate forgery is acceptable. An ACCIDENTAL claim by a lane that was handed a spec saying "ship" is exactly the class the gate exists to stop, and it is worse than the Claude case: the Claude gate can only be passed by inheriting a coordinator's id, but a claim actively displaces the coordinator.
  - Cheapest guard: compare-and-swap. `coordinator-claim --name <n> --supersedes <current newest coordinator name>`, re-checked under the claims lock and refused if the current newest differs. This stops a blind or accidental claim, gives a race between two claims exactly one winner, and stops a stale re-claim from silently overriding a hand-back.
  - Optional second line: refuse when `PLANNING_DISABLED=1` (the `codex_lane` lane marker). But only `codex_lane.py` sets it, so it is not a general lane marker; flag it as partial.
- **The objective lists three writes, but the runbook has a fourth.** §1 lists plan-apply, queue-append and inbox-edit. session-orchestration.md:173 also blocks card-snapshot writes until B2. Either add them via the first MISSING item or say they stay Claude-only.

VERDICT: correct the spec first. Two items block:

- the `claims_dir` default and caller scope (the other two gated writers either ignore claims, which breaks hand-over symmetry, or the existing unit tests read live state);
- the seconds-resolution, tie-passing timestamp, which makes §5.2 unsatisfiable.

R7 is a non-blocking residual: probe 4 settles it live. R8 is confirmed.

Recommended amendments:

1. Make `claims_dir` explicit and caller-resolved. `_dispatch` resolves it from `main_checkout` (or `--claims-dir`). Decide whether session_registry.py:735 and coordinator_handoff.py:1470 pass it, and add them to the allowlist or record that they stay Claude-only.
2. Add `--claims-dir` to the CLI in §3 so probe 4 can use a temp store.
3. Store claim `createdAt` with an injected clock and at least microsecond precision, tz-aware. Change the newest rule to compare (timestamp, provider, id) and authorize only an identity match, not a timestamp match.
4. Add `--supersedes <expected newest name>` compare-and-swap to `coordinator-claim`, refused under the claims lock on a mismatch. This is the cheapest guard against an accidental claim by a lane and against a stale re-claim.
5. Name `read_state`/`write_state`/`state_lock` as the store primitives. `authorize` reads claims without taking the claims lock.
6. State that the claim and release branches in `_dispatch` come before the coordinator-gated `else`.
7. Settle §4 "no wall-clock sleeps" against the existing race-test pattern (tests:306).
8. Add PREMISES rows: I for `read_state`/`write_state` (session_common.py:104-127); I for the two external callers; L for `now_iso` resolution (:155-157); L for the tz-aware requirement in `_created_at` (handoff_inbox.py:170-171).


## Re-verify of Amendments r2 (verbatim)

RE-VERIFY of Amendments r2 (A1-A8) in docs/specs/codex-takeover-phaseB2a-spec.md:125-177

VERDICT: ready to dispatch. Amendments r2 adds no new blocker and clears both earlier blockers: A1 settles the `claims_dir` default and caller scope, and A3 closes the timestamp tie. The three residuals below are non-blocking and need the architect's acceptance on record.

- **Allowlist (A1): holds.** I checked:
  - The two external callers sit exactly where A1 says: session_registry.py:734-737 and coordinator_handoff.py:1469-1472. Both call positionally, so a keyword-only `claims_dir=None` breaks neither.
  - Both test files exist (tests/test_session_registry.py, tests/test_coordinator_handoff.py), and both are uncommitted B1 work. The spec's "do not revert" rule must cover them; it reads that way.
  - The existing tests never run the real closure for these callers. They inject stub `authorize` callables (test_session_registry.py:205-260, 469; test_coordinator_handoff.py:1960-2035), so setting `None` to mean "no claims" keeps them unmodified. The two direct-call tests in test_handoff_inbox.py (:149-152, :333-337) never read live state.
  - The CLI tests in test_handoff_inbox.py go through `_dispatch` in the temporary `repos` main checkout, so their claims store is temporary and empty and their behaviour is unchanged.
- **Flag placement (A2): holds for handoff-inbox only.** The loop at :334-337 applies `--claims-dir` to every inbox verb. A1 also says "the dir comes from `--claims-dir` when given" for the other two callers, but those parsers have no such flag:
  - `snapshot-cards` has only `--jobs-dir` (coordinator_handoff.py:1465);
  - `lane-cards` has neither flag (session_registry.py:709-716).
  - Residual 1 (non-blocking): add `--claims-dir` beside the existing flags (and `--jobs-dir` on lane-cards), or state that both resolve `main_checkout` unconditionally. Otherwise any new end-to-end test of the real closure there reads the live `~/.claude/jobs` and the live claims store.
- **CAS under the claims lock (A4): sound.**
  - Racing claims each re-read the current newest under the claims lock, so the second one sees a mismatch.
  - Two edge cases are unspecified. When no coordinator exists at all, `--supersedes` needs a sentinel value (e.g. `none`). And a Claude job record created between the claim's check and its write is not covered by the claims lock, so it loses to the claim by timestamp.
  - Residual 2 (non-blocking): both edges are inherent to the design; the first needs one sentence in the spec.
- **Lock order (A5): no inversion.**
  - The writers hold the target lock, or the session_registry state lock at :539, then call `authorize`, which reads claims without a lock.
  - claim/release take only the claims lock and never a target lock.
  - Reading without the lock is safe because `write_state` is an atomic replace (session_common.py:119-127). A corrupt store makes `read_state` raise `StateUnreadableError`, an OSError. All three paths treat that as a refusal: the `main` handler at handoff_inbox.py:426, session_registry.py:756, and coordinator_handoff.py:1477.
- **A3, A6, A7, A8: consistent with the code.**
  - The anchors check out: `_created_at` :162-171, the dispatch `else` :386-395, the race test :284-316, and `now_iso` :155-157 (seconds resolution, no clock parameter).
  - Residual 3 (non-blocking): A3's identity match on the Claude side should use the record's `sessionId`, as `job_record` already does (session_common.py:83).