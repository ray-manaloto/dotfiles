# codex SDLC team — live settlement probe + third cold review (run live-settlement-probe-20260916), 2026-09-16

> PERSISTED VERBATIM at receipt. The FIRST live settlement under the reconciliation code (22bee5a + 301472a + a506b12 + f0935f2 on `fix/sdlc-team-settlement-verifies-spawn`), dispatched through the public entrypoint `mise run sdlc-team` in review mode as the advisor required (`real-integration-evidence.md`). Two arms were run by the coordinator on the live artifacts.

## Settlement (verbatim `settlement.json`)

```json
{"run_id":"live-settlement-probe-20260916","status":"completed","codex_returncode":0,"codex_pid":31259,"finished_at":"2026-09-16T10:19:26.054577+00:00","duration_s":361.2288436247036,"errors":[],"parent_thread_id":"01a0a9b4-f865-7212-b269-9247e6edd8be","specialists_claimed":["sdlc-python-specialist","sdlc-documentation-specialist"],"specialists_observed":["sdlc-documentation-specialist","sdlc-python-specialist"]}

```

## Control arms (coordinator, on the live artifacts)

- Independent route: exactly two child rollout files carry `parent_thread_id` `01a0a9b4-f865-7212-b269-9247e6edd8be`: roles `sdlc-documentation-specialist` (`/root/docs_spawn_reconciliation_review`) and `sdlc-python-specialist` (`/root/python_spawn_reconciliation_review`) — matches `specialists_observed`.
- Banner: `codex.log:10` `session id: 01a0a9b4-…` — matches `parent_thread_id`.
- The dispatcher's real closing list (`output.md:44-49`) used the pinned `- <role> — <path>` shape and the terminator `No others were spawned.`; `collect_spawn_report` parsed both items.
- NEGATIVE, same output + banner against an EMPTY sessions root → `consistent=False`, 3 errors (zero specialists observed; both claimed paths match no child). NEGATIVE, against the WRONG parent id (the 01:14 run's three children) → `consistent=False`, 5 errors. The live check discriminates.
- Receipt (`.agent/lane-results/live-settlement-probe-20260916.json`): both agents seen by self_report AND observed; disagreements = the HOOK-unavailable line and the `skipped 1 unreadable rollout file(s)` note (the April zero-byte file, older than the run).

## The team's review output (verbatim `output.md`)

Verdict: **HOLD**. Two confirmed fail-open inputs can settle a run as `completed` despite claimed and observed specialist disagreement.

## Findings

- **HIGH / A claimed role can match an observed path basename even when the observed role differs / `python/src/dotfiles_setup/sdlc_team.py:390`**

  `_candidate_satisfied()` accepts either `child.agent_role` or the basename of `child.agent_path`. A claim for `sdlc-python-specialist` paired with an observed `sdlc-config-specialist` at `/root/sdlc-python-specialist` returned:

  ```text
  consistent=True
  claimed=('sdlc-python-specialist',)
  observed=('sdlc-config-specialist',)
  errors=()
  ```

  An rc=0 supervisor can therefore settle `completed` despite direct role disagreement.

- **HIGH / A review-thread-only child masks zero specialist spawns / `python/src/dotfiles_setup/sdlc_team.py:595`**

  The zero-child check runs before review threads are excluded from pairing. An empty claimed roster plus one observed review thread returned `consistent=True` with no errors. The ordinary-child control correctly returned `consistent=False`.

  This contradicts `docs/specs/codex-sdlc-subagent-team.md:163` and the skill mirrors at line 98, which promise zero-specialist and claimed/observed mismatches fail closed.

- **MEDIUM / Supervisor tests bypass the required public interface and omit both fail arms / `tests/test_sdlc_team.py:135`**

  Tests isolate filesystem state, but call private `_SupervisorPayload` and `_supervise` objects through `vars()`. Existing tests also lack controls for role/path-basename collision and the review-thread-only case.

- **MEDIUM / The reviewed skill incorrectly promises a spawn-retry clause / `.claude/skills/codex-sdlc-team/SKILL.md:56`**

  The same wording appears in the `.agents` mirror. `build_prompt` instead requires stopping on spawn failure. This was corrected after the reviewed range in current `HEAD` `f0935f2`, but remains defective at `a506b12`.

- **LOW / The specification still labels the implemented team “NOT implemented” / `docs/specs/codex-sdlc-subagent-team.md:3`**

  Later sections describe the live implementation, making the status header stale.

## Requested answers

1. **Yes.** Both the role/path-basename collision and review-thread-only input can produce a completed settlement with mismatched rosters.
2. **Yes.** `collect_spawn_report` correctly parsed the exact two-item closing form used below, preserving roles, paths, and order.
3. **Not completely.** The detailed reconciliation prose is largely accurate, but the fail-closed promises are disproven by the two HIGH findings; the reviewed skill also contains the stale retry claim.

No repository gates were run, no report file was written, and this review made no checkout changes. The mandatory Graphify query was attempted but returned `rc=1` because the read-only sandbox denied mise log/temp-file creation.

Specialists spawned:

- `sdlc-python-specialist` — `/root/python_spawn_reconciliation_review`
- `sdlc-documentation-specialist` — `/root/docs_spawn_reconciliation_review`

No others were spawned.
## Coordinator refutation pass

- HIGH 1 CONFIRMED (fail-open input): a roster token may be satisfied by the path BASENAME even when the child RECORDS a different `agent_role` (`_candidate_satisfied`, `sdlc_team.py:390`). Contrived but real. Fix: when the child records a role, at least one of the claim's roster tokens must equal it; the others may match role or basename.
- HIGH 2 CONFIRMED (the advisor's note): review-thread children count toward the zero-children check before their exclusion (`sdlc_team.py:595`). Fix: count non-review children only.
- MEDIUM (tests use private objects via `vars()`) — pre-existing test style from before this change; out of scope. MEDIUM (skill retry wording) — fixed in `f0935f2` after the reviewed range. LOW (spec status header says NOT implemented) — CONFIRMED stale; one-line fix.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under change.
