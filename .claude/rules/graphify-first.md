# Graphify First

Before broad source search, run `mise run graphify-health`.

- `fresh`: use `mise run graphify-query -- "<question>"` and cite returned
  source paths.
- `missing`, `stale`, `corrupt`, version drift, warnings, or truncation: say the
  graph is unavailable and fall back to source. Never translate these states to
  an empty or complete answer.
- Never run a global Graphify binary or installer as a substitute for the
  project tasks. The generated skill is reference material; repository tasks
  and receipts are authoritative.

For every dependency/session review, check the latest Graphify release and the
project's critical/currency dependencies. Review release notes and source diffs,
record actionable changes, and explicitly record what the graph/source corpus
still cannot answer so the next review compounds knowledge instead of repeating
the same search.
