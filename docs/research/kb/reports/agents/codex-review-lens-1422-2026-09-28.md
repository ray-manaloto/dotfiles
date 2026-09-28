# Codex read-only review lens — #1422 `1554a079` (2026-09-28)

Command: `mise exec -- codex exec -s read-only --ignore-rules review --commit 1554a079… -c 'sandbox_mode="read-only"'` rc=0. Final message verbatim. Both findings DUPLICATE `code-review-1422-2026-09-28.md` (moving tags; marker platform) and are fixed in the follow-up commit on the same branch (`_moving_tags_hold_markers`, `_marker_digests`).

---

The new success path can mask incomplete tag publication and bypass marker-platform validation. Tests were blocked by uv cache permissions; findings target the requested commit, not subsequent working-tree edits.

Full review comments:

- [P2] Verify all moving tags before returning already_current — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/image_promote.py:356-357
  If an earlier promotion updates `:dev` but fails before updating `:latest` or `:dev-<arch>`, this branch reports success based solely on `:dev`. In `.github/workflows/ci.yml`, `eligible=false` skips the entire retag step, including per-architecture updates and verification, leaving supported tags stale while CI succeeds. Require all tags maintained by that step to match their expected content before returning `already_current`.

- [P2] Validate each marker's platform before accepting its digest — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/image_promote.py:214-218
  When the candidate is stale on amd64, `check_promote_eligibility` returns before validating the arm64 marker. This helper then checks only digest equality: an arm64 marker resolving to the wrong platform can still produce `already_current` if the `:dev` arm64 descriptor references that digest. `_resolve_marker` verifies a single-platform shape, not the expected platform. Apply the existing `marker.platform == expected_platform` validation here so a mislabeled marker remains a hard failure rather than becoming success.

## GitHub repos touched

_None._
