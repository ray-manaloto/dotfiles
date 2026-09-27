<!-- verbatim -o outputs of three read-only codex review passes over fix/mise-state-isolation (the first commit, the trust-store fix, then --base main at bb74c02d), session dotfiles-20260926.000 -->

=== dfix ===
The autouse fixture isolates trust records as well as tracking, breaking existing real-mise tests on normally trusted checkouts. Runtime validation was limited by the read-only sandbox.

Review comment:

- [P2] Restore narrowly scoped trust when isolating mise state — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/conftest.py:39-40
  On a checkout trusted through `mise trust`, without blanket `trusted_config_paths` or automatic approval, this also hides mise's `trusted-configs` records. Existing tests such as `test_claude_doctor_hook_behaviour_under_bun` invoke `mise exec` from the repository without supplying trust, so they now reject the repository configuration instead of running their assertions. Establish narrowly scoped trust for the configurations these tests execute while keeping tracking isolated, and verify the case without the author's global trust settings.
=== dfix2 ===
The new regression test bypasses the trust boundary under CI and therefore cannot detect the regression there. Full pytest execution was blocked by the read-only sandbox.

Review comment:

- [P2] Disable automatic trust in the regression test — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_mise_state_isolation.py:190-190
  On GitHub Actions, the child inherits `CI=true`, which makes mise automatically trust configs in non-paranoid mode despite the bogus `MISE_TRUSTED_CONFIG_PATHS`. Consequently, this test passes even if the fixture's trust-store symlink is removed, leaving the regression undetected by `contract-preflight`. Force explicit trust checking in both subprocesses (for example, `MISE_PARANOID=1` and `MISE_YES=0`) and verify that the no-record control fails, per [tests/AGENTS.md:68–72](tests/AGENTS.md#L68-L72).
=== dfix3 ===
No actionable regressions were identified in the three-file diff. Runtime validation remains unverified because the read-only sandbox blocked required mise and uv writes.
