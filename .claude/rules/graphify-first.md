# Graphify First

Before broad source search, run `mise run graphify-health`.

- `fresh`: use `mise run graphify-query -- "<question>"` and cite returned
  source paths.
- `missing`, `stale`, `corrupt`, version drift, warnings, or truncation: say the
  graph is unavailable and fall back to source. Never translate these states to
  an empty or complete answer.
- **Always the mise tasks, never a bare `graphify` on `PATH`.** Query with
  `mise run graphify-query`, rebuild with `mise run graphify-update` — never
  `graphify query`/`graphify update` directly. Two different graphify
  versions run on this machine: `graphify` on `PATH` resolves the
  **user-global** pin (`~/.config/mise/config.toml`, currently 0.9.53,
  outside this repo's review), while both mise tasks run **this repo's
  pinned 0.9.42** (`python/pyproject.toml`) — the version `graphify_health`
  actually checks against. A bare invocation can silently answer from, or
  rebuild the graph with, the wrong binary; the mise tasks are the only
  invocations guaranteed to match the health check that gates them. Never
  run a global Graphify binary or installer as a substitute for the project
  tasks — the generated skill is reference material, repository tasks are
  authoritative.
- `mise run graphify-update` also stamps which graphify version built the
  graph, so a later health check can tell a graph built by the drifted PATH
  binary from one built by this repo's pin — that stamp is what
  `version drift`/`stale` are actually detecting for a graph you rebuilt
  yourself. A present KB-style build receipt
  (`graphify-out/build-receipt.json`) is still verified byte-for-byte when
  one exists, but neither it nor the stamp is a fault when absent: nothing
  in this repo writes a receipt (that's the knowledge-base's
  committed-corpus pipeline), and the stamp only exists after a
  `graphify-update` run.

For every dependency/session review, check the latest Graphify release and the
project's critical/currency dependencies. Review release notes and source diffs,
record actionable changes, and explicitly record what the graph/source corpus
still cannot answer so the next review compounds knowledge instead of repeating
the same search.
