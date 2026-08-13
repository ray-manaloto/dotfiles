---
name: graphify
description: Query this repository's provenance-bound Graphify knowledge graph before source search.
---

# Graphify in dotfiles

Use the repository's reviewed tasks. Do not invoke a global Graphify binary or
the upstream installer before attempting the project graph.

## Before reading source

1. Run `mise run graphify-health`.
2. When health is fresh, run `mise run graphify-query -- "<question>"`.
3. Treat missing, stale, corrupt, warning-bearing, or truncated graph evidence as
   unavailable, never as an empty or complete answer.
4. If the graph is unavailable, say so and use source as the fallback authority.

Never hide Graphify stderr, warnings, truncation, source omissions, or receipt
failures. Never treat an existing `graphify-out/graph.json` as proof that the
graph is current. Cite graph source locations when an answer uses graph evidence.

Detailed upstream workflows remain in the generated Claude reference tree under
`.claude/skills/graphify/references/`; repository tasks and rules take precedence.
