# Five-stage workflow for substantial work

Before substantial implementation, recovery, or resuming a ticket graph, read
`.claude/skills/five-stage-workflow/SKILL.md` and follow **grill-with-docs →
to-spec → to-tickets → implement-spec → retro**. The durable contract is
[five-stage-workflow.md](../../docs/agent-workflows/five-stage-workflow.md).

Carry the user's standing authorization for this selected chain across turns;
retain required design/spec/ticket reviews and project delivery rules. Record
actual native skill invocation separately from direct file-guided fallback.
Preserve vendor plugin instructions and authored/generated skill parity.

Use the trivial-edit route only for settled, reversible work without ambiguous
behavior, shared global policy, credential policy or frozen proof. Diff size
does not establish triviality.

Workers own isolated integration-based worktrees and path allowlists; a separate
MERGER checks changed paths and integrates serially. One owner runs heavy gates
and one owns shared global writes. Hold competing writes during owned commit/hook
intervals. These are procedural constraints until native qualification proves
specific mechanisms; no shared-stash or complete race-prevention claim follows.

Preserve sealed failures. New proof permits at most three fresh immutable
attempts, each at most 60 active minutes; bounded slot wait is separate. Named
integration/delivery gates keep canonical timeouts and at most three attempts
at a failed gate. Reversible preflight fixes stay autonomous within scope;
budget exhaustion or unsupported material authority requires escalation.

Prefer existing compact status/read-result interfaces. Close with actual gate
and delivery evidence plus linked retrospective dispositions and residual limits.

Evidence and scope: [five-stage-workflow](../../docs/rules-evidence/five-stage-workflow.md).
