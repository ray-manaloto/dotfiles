# Graphify First

Before broad source search, run `mise run graphify-health`.

- `fresh`: use `mise run graphify-query -- "<question>"` and cite returned
  source paths.
- `missing`, `stale`, `corrupt`, version drift, warnings, or truncation: say the
  graph is unavailable and fall back to source. Never translate these states to
  an empty or complete answer.
- **Always `mise run graphify-query`, never a bare `graphify query`.** Two
  different graphify versions run on this machine: `graphify` on `PATH`
  resolves the **user-global** pin (`~/.config/mise/config.toml`, currently
  0.9.53, outside this repo's review), while `mise run graphify-query` runs
  **this repo's pinned 0.9.42** (`python/pyproject.toml`) — the version
  `graphify_health` actually checks against. A bare invocation can silently
  answer from the wrong binary; the mise task is the only one that is
  guaranteed to match the health check that gated it. Never run a global
  Graphify binary or installer as a substitute for the project tasks — the
  generated skill is reference material, repository tasks are authoritative.
- A present build receipt (`graphify-out/build-receipt.json`) is still
  verified byte-for-byte when one exists, but its absence is not a fault:
  only the knowledge-base's committed-corpus pipeline writes one, and this
  repo builds its graph on demand. Do not expect one here.

For every dependency/session review, check the latest Graphify release and the
project's critical/currency dependencies. Review release notes and source diffs,
record actionable changes, and explicitly record what the graph/source corpus
still cannot answer so the next review compounds knowledge instead of repeating
the same search.
