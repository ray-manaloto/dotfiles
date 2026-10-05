# Graphify First

Before broad source search, run `mise run graphify-health`.

- `fresh`: use `mise run graphify-query -- "<question>"` and cite returned
  source paths.
- `missing`, `stale`, `corrupt`, version drift, warnings, or truncation: say the
  graph is unavailable and fall back to source. Never translate these states to
  an empty or complete answer. A `stale` graph names the fix in its own detail
  line: `mise run graphify-rebuild`.
- **Always the mise tasks, never a bare `graphify` on `PATH`.** Query with
  `mise run graphify-query`, rebuild with `mise run graphify-rebuild` — never
  `graphify query`/`graphify update` directly.
- Use `mise run graphify-check` for read-only currency diagnosis plus a typed
  health line; it resolves the PATH binary from the ambient agent-shell PATH
  captured at SessionStart, not from the uv venv. Use `mise run
  graphify-upgrade` when package/skills and graph must move together.
- `permissions.deny` blocks any Bash string containing `graphify label`, even
  inside a quoted grep; search for that phrase with the Grep tool instead.

## What `fresh` means

Health implementation reference: `docs/rules-evidence/graphify-first.md`.

⚠️ **Ancestry is deliberately not the test.** This repo squash-merges, so a graph
built on a PR branch records a commit that never enters main's history. An "is it an ancestor" check would report `stale` on nearly every
graph: the mirror of the defect. Git compares the two endpoint trees instead;
if the build commit is unknown to Git, health fails closed as `stale`.

A graph carrying no `built_at_commit` is `stale` too. The pinned runtime always
writes it, so its absence means the bytes did not come from that runtime — and
silence is what this axis exists to end. A missing or unreadable manifest and
an unknown build commit are also `stale`. Uncommitted edits are out of scope:
this answers "what committed corpus changed since the build", not "is the worktree
dirty".

## Nothing records WHICH graphify built the graph

So the guarantee here is **procedural, not enforced**: always run
`mise run graphify-query`/`graphify-rebuild`, never the bare binary, and
`graphify-first.md`'s `version drift`/`stale` states only ever catch the
*checking* process itself drifting (a broken `uv` env, a bad `uv.lock`
edit) — not a graph built by the wrong installed graphify. Never run a
global Graphify binary or installer as a substitute for the project tasks —
the generated skill is reference material, repository tasks are
authoritative, by convention, not by verification.

A present KB-style build receipt (`graphify-out/build-receipt.json`) is
still verified byte-for-byte when one exists, but its absence is not a
fault.

For every dependency/session review, check the latest Graphify release and the
project's critical/currency dependencies. Review release notes and source diffs,
record actionable changes, and explicitly record what the graph/source corpus
still cannot answer so the next review compounds knowledge instead of repeating
the same search.
