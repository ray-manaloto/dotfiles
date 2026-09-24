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

`_staleness_problem` decides it from two independent sources: Git says what
changed after `built_at_commit` — a field **graphify itself** writes from HEAD
at export time — while `graphify-out/manifest.json` says which relative paths
Graphify scanned. Equality with HEAD is immediately fresh. Otherwise a
manifest-listed path is stale for any change status; an unlisted path is stale
only when newly added with an extension already present in the manifest. A
modified or deleted unlisted path stays outside the corpus even when its
extension matches a scanned file.

⚠️ **Ancestry is deliberately not the test.** This repo squash-merges, so a graph
built on a PR branch records a commit that never enters main's history — the
2026-08-31 graph's `b75fa3b` has six commits unreachable from HEAD and no branch
contains it. An "is it an ancestor" check would report `stale` on nearly every
graph: the mirror of the defect. Git compares the two endpoint trees instead;
if the build commit is unknown to Git, health fails closed as `stale`.

A graph carrying no `built_at_commit` is `stale` too. The pinned runtime always
writes it, so its absence means the bytes did not come from that runtime — and
silence is what this axis exists to end. A missing or unreadable manifest and
an unknown build commit are also `stale`. Uncommitted edits are out of scope:
this answers "what committed corpus changed since the build", not "is the worktree
dirty".

## Nothing records WHICH graphify built the graph

`graphify` on bare `PATH` resolves the **user-global** pin
(`~/.config/mise/config.toml`, outside this repo's review); the mise tasks
resolve **this repo's locked version** (`python/uv.lock`), which
`graphify_health`'s `version drift` check compares against. `mise run
pin-parity` binds every repository-owned pin site; the SessionStart doctor's
offline check names the user-global fix when the PATH binary drifts from the
lock.

Health reads the graphify installed in the *checking* process. Nothing records
which binary *built* the graph bytes, so a graph rebuilt by a drifted PATH
binary (a bare `graphify update .`) is indistinguishable from one built by the
pin.

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
fault: nothing in this repo writes one (that's the knowledge-base's
committed-corpus pipeline; see `_receipt_problem`'s docstring in
`python/src/dotfiles_setup/graphify.py` for why this repo cannot build one
of its own for an on-demand graph).

For every dependency/session review, check the latest Graphify release and the
project's critical/currency dependencies. Review release notes and source diffs,
record actionable changes, and explicitly record what the graph/source corpus
still cannot answer so the next review compounds knowledge instead of repeating
the same search.
