# Clarify Before Acting: Ask Until Sure on Ambiguous Work

When a task is ambiguous, admits multiple reasonable approaches, or is
hard to reverse, ask clarifying questions (via `AskUserQuestion`) and
keep asking across rounds until you are confident what to do. Do not
guess and proceed.

## Why this rule exists

Session 2026-06-29: the user asked for hk-hang prevention and explicitly
said *"keep asking questions until 100% sure on what to do"* and to
record the preference so it need not be repeated. In the same session the
user's chosen approach ("per-step hk timeouts") turned out to be
**impossible** — hk has no timeout support. Surfacing that and
re-confirming the pivot (an outer timeout wrapper) before building
avoided shipping the wrong thing.

## Rules

1. **Ask before acting on ambiguous / multi-path / irreversible work.**
   If there is genuine uncertainty about scope, approach, or intent, or
   the action is hard to undo (deletes, pushes, merges, external/
   outward-facing effects), resolve it with the user first.

2. **Recommend, don't just enumerate.** Lead with the option you'd pick,
   marked `(Recommended)`, and give the trade-offs. A question is a
   proposal to confirm, not a blank survey.

3. **Proceed directly on clear, low-risk, reversible tasks.** Do not
   manufacture questions for things with an obvious default or facts you
   can verify yourself — over-asking is its own failure mode. Pick the
   obvious option, state it, and move.

4. **Surface infeasibility immediately.** If a chosen approach turns out
   impossible or much worse than expected mid-flight, stop and
   re-confirm the pivot with evidence — never silently substitute a
   different solution for the one that was agreed.

5. **Keep asking until sure.** A second clarifying round is cheaper than
   rework. Don't stop at one question if the answer revealed new
   ambiguity.

## Applies to

All non-trivial work: planning, multi-file changes, design choices,
destructive or outward-facing actions, and any task where the request
under-determines what to build.

## See also

- `do-not.md` — project invariants (some actions are never OK regardless
  of clarification).
- CLAUDE.md → `AGENTS.md` "Agent Instructions" — the policy index that
  references this rule.
