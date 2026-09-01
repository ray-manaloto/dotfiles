---
name: graphify
description: Query this repository's provenance-bound Graphify knowledge graph before source search.
---

<!-- DELIBERATE STUB: this file is a hand-authored redirect, NOT
     `graphify agents install` output. A real install here would ship the
     vendor's ~41 KB generic workflow reference (the same content already
     installed for Claude Code at `.claude/skills/graphify/`); this file
     intentionally stays small and points at the reviewed project tasks
     instead, matching the same "repository tasks over vendor instructions"
     posture as the Claude skill body. Enforced by hk's
     `graphify_skill_surface` step and `doctor.toml`'s `[graphify]` check —
     if this marker line is gone, either the stub was silently overwritten
     by a real install (update `doctor.toml` to match) or the note was lost
     by accident (restore it). -->

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
