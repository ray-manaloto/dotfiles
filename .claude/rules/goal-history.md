# Append-Only Goal History

After an accepted goal change, orchestration-topology change, major milestone,
landing, or handoff, append one iteration to `docs/agents/goal-history.md`
before advancing. Never rewrite, reorder, squash, or delete prior iterations.

Each iteration must contain the exact field labels `Iteration ID`, `Prior goal
digest`, `Current goal digest`, `Changed requirement`, `Reason`, `Evidence`,
`Affected tickets`, `Disposition`, and `Topology and ownership`, followed by
the current goal text and a Mermaid workflow. Use `NONE (bootstrap)` only when
no prior tracked iteration exists. A digest identifies exact goal text; it does
not prove that the goal was completed.

Session review enforces append-only bytes against the fixed `origin/main`
merge-base, every first-parent branch revision in order, and the current
working tree. A branch cannot authorize its own rewrite by naming a different
baseline. If the baseline cannot be resolved, review fails closed.

One repository has one implementation writer by default. Record every ownership
handoff. If a Desktop task restarts while a fallback subagent owns the same
repository, stop one writer before either mutates files; never infer disjointness
from different task or worktree names.

Session review must read the bounded tail of the history and distinguish an
accepted decision from verified delivery. It validates the complete file and
its authorized Git baseline before applying that semantic tail bound. Missing
evidence stays explicit; do not backfill it with assistant narrative.

The one-writer restart protocol is not an executable inter-task lock. Issue #753
tracks the native startup/pre-mutation ownership lease. Until that lands,
the supervisor must perform the handshake and stop one writer manually.
