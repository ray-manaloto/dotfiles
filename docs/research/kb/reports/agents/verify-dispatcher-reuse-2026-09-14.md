Read-only review completed; nothing was modified.

### Dispatcher selection

`sdlc-dispatcher` selected:

- `sdlc-config-specialist` — owns [hk.pkl](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/hk.pkl:1) and [hk-common.pkl](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/hk-common.pkl:8).
- `sdlc-documentation-specialist` — owns [AGENTS.md](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/AGENTS.md:74) and `.claude/rules/`.

It excluded the Python, workflows, and image specialists because their owned paths are outside the issue.

### Consolidated findings

- The current exact hk package pin is `1.57.0`:
  - `hk.pkl`: lines 1, 8, and 11.
  - `hk-common.pkl`: lines 17–18, plus the example at line 8.
- Each URL repeats the version in both `download/vX.Y.Z` and `hk@X.Y.Z`; both components must remain aligned.
- `min_hk_version = "1.49.0"` at [hk.pkl:19](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/hk.pkl:19) is a compatibility floor, not the exact package pin. It should only be raised if the new behavior requires it.
- The `pin_parity` check at [hk.pkl:540](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/hk.pkl:540) also covers `hk-image.pkl` and `.config/mise/conf.d/shared.toml`. Changing only the two issue-named Pickle files may fail lint unless those other pin surfaces already match the target.
- Primary documentation surfaces are [AGENTS.md:74](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/AGENTS.md:74) and [.claude/rules/ci-local-parity.md:52](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/ci-local-parity.md:52).
- Scheduling, locking, caching, timeout, staging, and fix-mode claims should only be changed if contradicted by the confirmed new behavior.
- [.claude/rules/long-running-command-hangs.md:110](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/long-running-command-hangs.md:110) describes a linked rule as cache-clearing guidance even though that rule says cache clearing is retired.
- Two rule frontmatters include `hk.pkl` but omit `hk-common.pkl`, potentially preventing those rules from loading for isolated shared-config edits.
- `AGENTS.md` is generated above its manual marker and is already 195 lines/11,999 bytes against a 12,000-character budget. Future wording should replace or shorten existing prose and must be applied through the durable generation source.
- The target hk version and exact new behavior were not provided, so neither specialist invented replacement values or prose.
- Future verification would include `mise run lint` and `mise run lint-docs`, including pin parity and documentation-size enforcement.

The mandatory Graphify query was attempted but returned `rc=1` because the read-only sandbox blocked mise log and temporary-file creation. Existing graph data was used where useful; it was stale and lacked nodes for the Pickle files.

### Agent types actually spawned

Exactly three agent instances were spawned:

1. `sdlc-dispatcher`
2. `sdlc-config-specialist`
3. `sdlc-documentation-specialist`

The two specialists were exactly those selected by the dispatcher. No Python, workflows, image, or other agents were spawned.
## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — second dispatcher test; its unprompted findings became #1126 and #1127.
