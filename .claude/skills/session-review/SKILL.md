---
name: session-review
description: Review Claude and Codex requirements, promises, and manual-work candidates via `mise run session-review`. Use before a handoff or major milestone so typed requirement coverage and both automation-candidate lanes remain visible.
user-invocable: true
---

# session-review: judge what should become code

## Invoke it

```bash
mise run session-review
mise run session-review -- --output .agent/session-review.md
mise run session-review -- --narrative-only
mise run session-review -- --sessions 6
mise run session-review -- --rebuild-cache
mise run session-requirements -- /absolute/source/checkout
mise run session-requirements -- /absolute/source/checkout 3 5
mise run session-review -- --requirements-only --source-repo-root "$PWD" \
  --codex-session-id "$CODEX_THREAD_ID" --output .agent/session-review.md
```

Always use an explicit `--output` when `--source-repo-root` differs from the
invoking repository. The CLI refuses an implicit cross-root destination.

The report is bounded evidence plus a template. The Python command collects
and classifies; **the judgment remains with the reviewing agent**. Low-level
cache, provider, attachment, and finalization contracts live in
`docs/session-review-reference.md`.

## Read both automation lanes

**Lane 1 — recurring command shapes** ranks a normalized command by the number
of distinct sessions containing it. Repetition inside one session is one
costly episode; repetition across sessions is a reusable-workflow candidate.

**Lane 2 — passages in the notepad and newest handoff** surfaces prose that
looks like manual work. It is semantic discovery, not completion authority.
Read the passage before accepting it: a regex cannot distinguish an expensive
workflow from a sentence explaining why not to perform one.

Neither lane subsumes the other. Frequency is only a proxy for cost, while a
one-off workflow can contain expensive reasoning that no repeated command
captures.

## Interpret the verdict

The report opens with `VERDICT: COMPLETE|INCOMPLETE — <primary reason>`. It
also names the selected session, source and invoking roots, pytest-temp state,
counts, omission histogram, generation, omissions index, newest segment, and
the next iteration action.

Requirement coverage is fail-closed and bounded. It reads Codex and Codex
native transcripts, preserves typed user authority, tool pairing, lineage,
prefix hashes, and byte cutoffs, and emits **UNREVIEWED evidence**, not an
assistant-inferred completion verdict.

An unknown or malformed transcript record, missing pair, unreadable external
attachment, unresolved explicit session identity, or unreviewed requirement
makes the review `INCOMPLETE` and non-zero. Current known telemetry and harness
attachments may be skipped or represented by bounded diagnostics; a fresh
unknown type remains blocking and is summarized once per provider/type with a
count and first source location.

`INCOMPLETE` is a useful finding, not permission to ignore the report. Follow
its primary reason and omission histogram, repair the evidence boundary, and
rerun. Never infer success from a task notification; capture the command's real
exit code.

Before trusting the bounded tail, validate the entire
`docs/agents/goal-history.md` structure, every first-parent revision from its
fixed `origin/main` merge-base, and working-tree append-only bytes. Then judge
its bounded tail for repeated pivots, prompt ambiguity, duplicate ownership,
and work no longer advancing the current destination. A history entry records
a decision, not proof that its work landed. Apply `.claude/rules/goal-history.md`
whenever the review accepts a goal change.

## Orchestrate review before implementation

For consequential cross-domain findings, use this order:

1. Resolve ambiguity in the active plan.
2. Snapshot deterministic state and run this tool with an explicit output.
3. Run an SDLC review and the Codex AgentsView pass in parallel.
4. Wait for both; disposition every finding.
5. Use SDLC `implement` mode only for accepted repository changes, with an
   exact allowlist and `COMMIT: caller`.
6. The caller runs gates, commits, and runs `mise run handoff-check`.

AgentsView is the archive-discovery lane: use it to recover context, missed
obligations, contradictions, and agent activity. The ledger remains the
authority lane for hashes, cutoffs, user authority, tool pairing, lineage, and
fail-closed record coverage. Filesystem receipts and SDLC settlement—not
archive prose—prove repository work landed.

Skip a team round for a typo or single-file edit. A review run costs time and
coordination; use it when independent domain review can avoid a concrete
cross-domain failure.

## Apply the cost gate

Ask of every candidate:

> **What concrete cost would this have avoided?**

A wrong-platform run, re-derivation, spurious red gate, or near-committed
corruption qualifies. "It would be nicer" is a preference, not a candidate.

## Disposition every finding

Every accepted or rejected finding needs a stable ID, source artifact and
SHA-256, terminal disposition, rationale, concrete avoided cost, carrier,
owner, and receipt. Use these destinations:

- dotfiles defect: issue, rule, test, implementation, or the active plan;
- AgentsView product defect: `docs/handoffs/agentsview-<date>.md`, never a fix
  in this repository;
- SDLC finding: persisted report plus architect disposition;
- requirement or promise: semantic disposition with typed receipt references;
- automation candidate: carrier/receipt or explicit rejection rationale;
- stable historical lesson: memory, never task selection.

Missing dispositions remain `NEEDS_AGENT_ACTION`, `INCOMPLETE`, and non-zero.
Assistant prose cannot grant authority, and persisted receipts are audit
evidence—not reusable completion authority. Finalization must run the
registered mutation and normal gate in the same process; see the reference for
the exact contract.

Every prevention round assigns a `specialized fixer`, `independent QA`, and
an `adversarial reviewer`. Its disposition names the `mutation_receipt`,
`gate_receipt`, and `issue_receipt`. A report without the verified
disposition cannot become `COMPLETE`.

## Write accepted automation candidates

Use one candidate per issue in the shape used by #650–#653: what was done by
hand, the concrete cost avoided, and the proposed
`skill → mise task → python library` carrier. Make it reusable by parameter;
this repository's case is a default, never a hard-coded special case.

## Technical reference

Read `docs/session-review-reference.md` when changing parser fields, cache
behavior, attachment limits, provider selection, artifact publication, or the
finalize state machine. Those mechanics are deliberately kept out of this
judgment-focused skill.
