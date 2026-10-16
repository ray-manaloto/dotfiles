---
name: five-stage-workflow
description: Route substantial implementation and recovery through grill-with-docs, to-spec, to-tickets, implement-spec, and retro. Use before starting a substantial task, resuming its approved ticket graph, or choosing the trivial-edit path.
---

# Five-stage workflow

Read [the durable protocol](../../../docs/agent-workflows/five-stage-workflow.md)
before choosing a route. It contains stage completion, proof budgets, ownership,
evidence limits and concrete retrospective dispositions. This is a router for
the selected skills, not a replacement for their instructions.

## Route and authorization

Default substantial work across projects to **grill-with-docs → to-spec →
to-tickets → implement-spec → retro**. Preserve the project's tracker, checks,
delivery route and human-only authority. Existing explicit standing user
authorization covers all five selected stages; carry its source into the task
record and do not ask for repeat invocation. It does not resolve open design
choices or authorize actions outside the approved task.

A trivial edit may use the existing small/spec-saturated route only when its
behavior and acceptance are settled, it is reversible, and it touches no
ambiguous behavior, shared global policy, credential policy or frozen proof.
A small diff alone is insufficient. Record the reason and applicable checks;
uncertainty routes to the five stages.

## Run the selected instructions

1. Recover the approved task, stage artifacts, decisions, tracker and delivery
   constraints. Inventory available skill/tool interfaces before choosing one.
2. Select the installed `grill-with-docs`, `to-spec`, `to-tickets`,
   `implement-spec`, and `retro` instructions. Record package/version, exact
   source and hash, actual invocation mode and output pointer for each stage.
   Prefer native invocation when available and authorized. A user-only verb's
   invocation restriction remains in force; never claim the model called it.
3. If the runtime has no Skill tool or cannot invoke a selected verb, apply its
   exact installed instructions as a **file-guided fallback** under the recorded
   user authorization. Report unavailable routes and the actual files read.
   If required instructions are missing, recover them or report the blocker;
   do not invent their contents or edit vendor plugin caches.
4. Complete each stage's required review before advancing. Grilling settles the
   decision tree and shared understanding. Spec records behavior, user stories,
   confirmed public seams and testing decisions. Ticketing reviews granularity
   and real blocking edges before publication. Implementation uses the reviewed
   graph and selected `tdd` guidance; reuse existing checks for reversible docs.
   Whole-spec review and applicable gates precede readiness and delivery.
5. Assign each implementer one branch/worktree based on the spec's integration
   tip and a changed-path allowlist. Workers preserve others' edits and reconcile
   integration before handoff. A separate MERGER checks the path subset and
   integrates serially. Keep host-heavy gates, repository shipping and shared
   global writes with their single designated owners.
6. Hold competing writes during the owned commit/hook interval. Do not claim
   mechanical exclusion, shared stash behavior or native enforcement without
   qualification. Record unsupported boundaries and linked follow-ups.
7. For sealed proof, prepare saved compiler-checked, hash-bound verifier bytes
   before START. Permit at most three fresh immutable attempts, each at most
   **60 active minutes** after slot admission. Record bounded queue wait
   separately. Full named integration/delivery gates retain canonical timeouts
   and at most three attempts at a failed gate. Preserve every old failure.
8. Observe through existing compact status/read-result interfaces first. Name
   actual exit codes, artifact paths/hashes and evidence class; expand bounded
   source/log excerpts only to answer a concrete unresolved question.
9. Finish `retro` with each learning linked to an implemented fix, explicit
   merge into another candidate, or deferred follow-up with owner and reason.
   Reconcile tracker delivery evidence and residual limits; an open draft or
   passing source check alone does not close the spec.

## Source and generated copy

The durable protocol identifies the authored source. Edit that source, then
regenerate the client mirror with `mise run skills-mirror`; verify with
`mise run skills-mirror -- --check`. Never hand-edit the generated copy.
Global navigation pointers are separately owned deployment, with fresh-session
loading evidence required before claiming activation.
