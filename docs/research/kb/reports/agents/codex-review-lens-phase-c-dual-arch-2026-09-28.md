# Codex read-only review lens — Phase C `f93bb776` (2026-09-28)

Command: `mise exec -- codex exec -s read-only --ignore-rules review --commit f93bb776… -c 'sandbox_mode="read-only"'` rc=0. Final message verbatim. DUPLICATES `code-review-phase-c-dual-arch-2026-09-28.md` finding 1, and adds the latest-switches-between-installed-versions scenario; both covered by `select(.active)` and pinned by `tests/test_persistence_parity.py` (extracts the real PARITY_KEY from mise.toml).

---

The persistence filter mishandles retained inactive versions, producing false gate failures. The comparison regression was reproduced against the requested commit; pytest could not run because the read-only sandbox blocked uv cache access.

Review comment:

- [P2] Exclude inactive versions from floating-tool parity — /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:610-612

## GitHub repos touched

_None._
