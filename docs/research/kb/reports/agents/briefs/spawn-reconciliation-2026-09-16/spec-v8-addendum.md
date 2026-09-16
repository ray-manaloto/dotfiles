# SPEC v8 ADDENDUM to v7 (respec round 1) — one rule clarification, plus the tree state the lane inherits

Applies on top of `spec-sdlc-spawn-reconciliation-v7-respec.md` (authoritative for everything else) and its parent v5.

## Rule clarification (fixes the v7 conflict with v5 arm 11)

v7 says a child is consistent with a claim only when EVERY candidate is satisfied, and a roster-grammar candidate is satisfied by `agent_role` or by the basename of `agent_path`. A child that records NO `agent_role` can then never satisfy a role candidate, so the path-first claim `` - `/root/config_pin_review` — `sdlc-config-specialist`; … `` can no longer pair with a role-less child at `/root/config_pin_review` — and v5 arm 11 (`test_roleless_child_pairs_by_agent_path`) fails on the current tree (measured: bundle 59 passed / 1 failed).

Resolution: a roster-grammar candidate is satisfied by a child when (a) the child records an `agent_role` equal to it, OR (b) it equals the basename of the child's `agent_path`, OR (c) the child records NO `agent_role` AND the claim carries a PATH candidate that this child satisfied. A missing field does not contradict a claim that the path already anchors; it is unverifiable, not refuted. A role-less child still cannot pair with a claim that has no path candidate unless the role token equals its path basename (arm 25's shape). Arms 11 and 19 must both pass: arm 19's role-mismatch error fires only when the child RECORDS a different role.

## Tree state (single writer from here)

The working tree at HEAD holds the combined partial work of two killed/aborted codex runs on v7: 5 modified files (`docs/specs/codex-sdlc-subagent-team.md`, `python/src/dotfiles_setup/lane_result.py`, `python/src/dotfiles_setup/sdlc_team.py`, `tests/test_lane_result.py`, `tests/test_sdlc_team.py`), unstaged, nothing committed. Measured by the coordinator on that tree: `ruff check` on the four python files is clean (rc=0); the §5 pytest bundle is 59 passed / 1 failed (arm 11 above); arm tests 16-28 exist as `test_arm_NN_…` functions; the previous lane reported that `mise run lint` had failed on "complexity/branch limits, one unsafe implicit concatenation, type-only" issues it was fixing when it stopped — ruff is now clean, so whatever remains will be found by running `mise run lint` (ty, pkl/hk steps) — run it and fix real findings. Treat every inherited edit as unverified: re-derive from v7 (+ this addendum), keep what is right, fix what is not.

## PREMISES (addendum rows; the v7 block still applies)

- L — v5 arm 11 test `test_roleless_child_pairs_by_agent_path` at `tests/test_sdlc_team.py:646-670` claims `` - `/root/config_pin_review` — `sdlc-config-specialist`; … `` against a child with `agent_path: /root/config_pin_review` and no `agent_role`, and asserts `returncode == 0` and `COMPLETED` — currently FAILING (coordinator run, 2026-09-16 09:25Z)
- L — `uv run --project python ruff check` over the four changed python files → rc=0 on the current tree (coordinator run)
- L — the tree's diffstat vs HEAD: 5 files, +865/−61 (coordinator, `git diff --stat`)
- A — the previous lane's "complexity/branch limits … type-only" lint note describes ty or pkl-step findings that ruff no longer reports; held because ruff is clean now and `mise run lint` is the only way to see the rest. If `mise run lint` is clean, nothing remains.
