---
name: blast-radius
description: Answer "what does changing X break?" cheaply via `mise run graphify-affected -- "<node>"` (reverse traversal over calls/imports/references/inherits) and `mise run graphify-prs [-- <PR#>]` (PR dashboard; a PR number adds the graph-impact deep dive). Use before touching a widely-used symbol, before a risky refactor, or when reviewing/triaging a PR and you want to know how far its change radiates through the graph — instead of grepping callers by hand. Do not use `graphify-prs` from a gate or hook — it shells out to `gh` and makes network calls.
user-invocable: true
---

# blast-radius: reverse traversal + PR graph impact

```bash
mise run graphify-affected -- "<node>"                # what breaks if <node> changes?
mise run graphify-affected -- "<node>" --depth 3       # widen the reverse traversal
mise run graphify-prs                                  # cheap PR dashboard, no graph read
mise run graphify-prs -- <PR#>                          # + graph-impact deep dive for that PR
```

Both are thin `mise` callers over `python/src/dotfiles_setup/graphify.py`
(`affected`/`affected_main`, `prs`/`prs_main`) — the same seam as
`graphify-query`/`graphify-health`/`graphify-update`. All mechanics live
there; this file is judgement only.

## When to reach for `affected`

Before editing a symbol you did not write, or before a refactor that touches
a shared module — run `affected` first instead of grepping for callers by
hand. It is a deterministic reverse BFS/DFS over `graphify-out/graph.json`
(calls, imports, references, inherits, …), no LLM, ~free.

**Non-obvious failure modes:**

- **Graph unavailable → a clear rc≠0 error, not silence.** `affected` reuses
  `graphify_health` (never reimplements it, per `graphify-first.md`) — a
  missing/stale/corrupt/version-drifted graph raises before any subprocess
  runs (rc 3, "graph health is …"). Treat that as "fall back to source",
  exactly as the rule requires — never as "nothing depends on this".
- **An unmatched node is NOT the same as "nothing depends on it".**
  graphify's own handler prints `"No unique node match for <node>"` at
  **rc 0** — a real answer ("this name isn't in the graph"), distinct from
  "the graph says zero dependents" (which instead prints "No affected nodes
  found."). Read the message, don't just check the exit code.
- **A node is a label, not necessarily a path.** Try the bare symbol name
  first (`"graphify_health"`); fall back to a file path only if that misses.

## When to reach for `prs`

The bare dashboard (`mise run graphify-prs`) is a cheap CI/review-status
table — safe to run often. Passing a PR number adds the **graph-impact**
deep dive (which communities/how many nodes the PR's diff touches) —
deliberately expensive by design (graphify's own comment: concurrent `gh pr
diff` calls per file), which is why it fires only when you actually pass a
number, `--triage`, or `--conflicts`. Don't reach for the numbered form in a
loop over every open PR; use the bare dashboard to pick which PR is worth
the deep dive.

**Non-obvious failure modes:**

- **Needs an authenticated `gh`, and makes network calls.** A missing or
  unauthenticated `gh` surfaces as a clean one-line error ("gh CLI not found
  or not authenticated. Run: gh auth login"), never a traceback — but it is
  still a real dependency. **Never call this from a gate, hook, or anything
  that must be offline/deterministic** — that's what `graphify-query`/
  `graphify-affected` are for.
- **No graph-health gate, and that's deliberate.** The dashboard needs no
  graph at all; the impact path checks `graph_path.exists()` internally and
  silently skips impact (not an error) when the graph is missing. Don't
  expect `affected`'s health-gate error shape here.

## Not authored via `/skill-creator:skill-creator`

That's this repo's canonical skill-authoring path
(`.claude/rules/agent-artifact-conventions.md` rule 6), but it's a
Claude-side slash command an implementer lane (codex/grok) cannot invoke.
This file was hand-written to match the shape of `.claude/skills/token-check/
SKILL.md` instead — flagged here per the spec's premise 10, not hidden.
