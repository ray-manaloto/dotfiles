# Graphify First

Before broad source search, run `mise run graphify-health`.

- `fresh`: use `mise run graphify-query -- "<question>"` and cite returned
  source paths.
- `missing`, `stale`, `corrupt`, version drift, warnings, or truncation: say the
  graph is unavailable and fall back to source. Never translate these states to
  an empty or complete answer. A `stale` graph names the fix in its own detail
  line: `mise run graphify-update`.
- **Always the mise tasks, never a bare `graphify` on `PATH`.** Query with
  `mise run graphify-query`, rebuild with `mise run graphify-update` — never
  `graphify query`/`graphify update` directly.

## `fresh` now means "built from HEAD" — it did not until 2026-09-13

Health used to check only that the graph file existed, parsed, matched the schema,
and that the INSTALLED graphify was the pinned version. **Nothing compared the
graph to the code.** The graph in this clone was built 2026-08-31 and reported
`fresh` for thirteen days and 76 commits, while this rule told every agent a
`fresh` graph is citable and a PreToolUse hook made querying it MANDATORY before
grepping. Two symbols a session needed that day — `plan_attest_main`,
`claude_doctor_main` — were absent because their modules postdated the build,
and the graph answered as though they did not exist. Measured against controls:
`setup_parser` 76 hits, `handle_pr` 21, both subjects 0.

`_staleness_problem` closes it by comparing `built_at_commit` — a field
**graphify itself** writes from HEAD at export time
(its own `graphify.export` module, via that package's `_git_head`) — against a
HEAD read independently. Two sources,
so both answers are reachable; that is exactly what the removed rebuild stamp
below lacked.

⚠️ **Ancestry is deliberately not the test.** This repo squash-merges, so a graph
built on a PR branch records a commit that never enters main's history — the
2026-08-31 graph's `b75fa3b` has six commits unreachable from HEAD and no branch
contains it. An "is it an ancestor" check would report `stale` on nearly every
graph: the mirror of the defect. Equality with HEAD is the whole test.

A graph carrying no `built_at_commit` is `stale` too. The pinned runtime always
writes it, so its absence means the bytes did not come from that runtime — and
silence is what this axis exists to end. Uncommitted edits are out of scope:
this answers "which commit built it", not "has anything changed since".

## Nothing records WHICH graphify built the graph

**The two installs are aligned as of 2026-09-14 — both 0.9.61.** `graphify`
on bare `PATH` resolves the **user-global** pin
(`~/.config/mise/config.toml`, outside this repo's review);
`mise run graphify-query`/`graphify-update` resolve **this repo's pinned
version** (`python/pyproject.toml`), which is what `graphify_health`'s
`version drift` check compares against. They agree today, but nothing keeps
them in sync, so treat the alignment as a fact with a date on it, not an
invariant.

The check reads whatever graphify package is installed in the process
*checking* health right now. It says nothing about which binary actually
*built* the graph bytes on disk — a graph rebuilt by a drifted PATH binary
(a bare `graphify update .`) is indistinguishable from one built by the
repo's pin, because nothing records who built it. **An earlier
version of this rule claimed a rebuild stamp closed that gap; it did not —
the stamp could only ever record whatever `graphify-update` itself always
resolves, so the check it fed could never fail, and the one drift it
existed to catch wrote no stamp at all. It was removed rather than kept as
a check that always reports "fine".**

So the guarantee here is **procedural, not enforced**: always run
`mise run graphify-query`/`graphify-update`, never the bare binary, and
`graphify-first.md`'s `version drift`/`stale` states only ever catch the
*checking* process itself drifting (a broken `uv` env, a bad `pyproject.toml`
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
