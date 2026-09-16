# fable-advisor — commitment boundary for 6c P0 (branch fix/sdlc-team-settlement-verifies-spawn), 2026-09-16

> PERSISTED VERBATIM at receipt (agent-report-persistence.md rule 1). Agent: `fable-orchestrator:fable-advisor` (read-only), consulted before declaring the deliverable done, with the commits 22bee5a / 301472a / a506b12, the three review reports and the pasted gate evidence.

Verdict: ship the PR, but do not declare 6c P0 done until one live run settles under this code. Order: C (one review-mode `mise run sdlc-team`, sequential, not concurrent with ship) → A. Read B if it lands meanwhile; do not wait for it.

Fail-closed design holds. Demotion is exactly `COMPLETED and not consistent → FAILED` (python/src/dotfiles_setup/sdlc_team.py:964); TIMED_OUT and FAILED are never upgraded. Every unknown appends an error before `consistent` is computed: missing banner id, unavailable self-report or observed side, during-run unreadable rollout, zero children, unmatched claim, unclaimed child (sdlc_team.py:557-620). Nothing I read can settle `completed` on a fabricated list.

Deciding risk: zero live settlements exist under this code. The newest `.agent/sdlc-runs/*/settlement.json` is from 01:29 today; 22bee5a is 03:31; none carries `specialists_claimed` or `specialists_observed`. All evidence is replay over historical files plus mutation-armed unit tests. The objective is a claim about live settlements, and `.claude/rules/real-integration-evidence.md` requires one real invocation through the public entrypoint before a completion claim. Only a live run answers three things: whether the new prompt's actual closing list survives the LAST-anchor parser (otherwise a false FAILED and another round); whether the banner parse holds against the pinned codex; and whether the supervisor reaches `_write_settlement` at all. `_write_lane_receipts` runs with no catch-all in `_supervise` (sdlc_team.py:958-987), so an unexpected exception yields no settlement, which reads as still-running. All three fail loud, never `completed`, so shipping is safe. "Done" is not yet earned.

Two notes, non-blocking. First, review-thread children count toward the zero-observed check, because children are built before review exclusion (sdlc_team.py:585-598). A none-claim run whose only child is a codex review thread settles `completed`. Untested: the review-thread test at tests/test_sdlc_team.py:1030 has non-empty roles. Add it to the residuals list in the spec. Second, the "verify not re-run" residual is closed by ship itself: lint → pytest → verify → hook-selfcheck → lint-docs (python/src/dotfiles_setup/pr.py:325-357), and suites.toml binds neither module.

Findings appended to findings.md under "advisor verdict — 6c P0 commitment boundary".

## Coordinator disposition

- Order accepted: one live review-mode `mise run sdlc-team` run under this code BEFORE `ship`; its `settlement.json` must carry `parent_thread_id`, `specialists_claimed`, `specialists_observed` and a status that agrees with the on-disk children.
- Note 1 is a real residual gap (review-thread-only child + `- None.` claim → `completed`); surfaced to the user with the ship decision rather than opened as a third review round (two-round bound reached).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under change.
