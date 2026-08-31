# Briefs for the 2026-08-31 four-lane plugin/maintenance audit

Persisted per `.claude/rules/agent-report-persistence.md` rule 5: a
findings-bearing lane's **brief** is as much the artifact as its report. The
four reports live beside this file as `2026-08-31-lane{A,B,C,D}-*.md`.

All four ran as `fable-orchestrator:codex-implementer` lanes, `EFFORT: xhigh`,
`COMMIT: caller`, dispatched in parallel in one message, each writing its report
to the session scratchpad and touching no repo file.

## The operator's framing, verbatim

The question these lanes exist to answer, in the operator's own words:

> i want to use the planning-with-files so we dont have to maintain our own
> session tracking infrastructure and workflow which is very buggy and doesnt
> always work and does more than what we've trying to do
>
> my ideal workflow is create a plan w small granular tasks that can be done on
> a small context window so we dont waste tokens and go above the 20% context of
> the model where the efficiency of the model starts to degrade
>
> planning-with-files seems to help do this and is less maintenance on our side
> there is just overlap and the ability to conflict which can cause us problems
> we can store the planning-with-files in git if needed so they are durable
>
> for whatever is remaining that is not overlap, we need to review what is
> remaining and scrutinize them if they are still needed and/or if there other
> plugins/skills/tools/etc that would achieve what we are doing instead of
> wasting our time maintaining claude vs actual real work that i want to do

## Shared premises given to every lane

Measured by the architect this session, before dispatch:

- 26 rule files / 131,694 B; 31 skill files / 231,598 B; 4 agent files / 64,927 B
- 5 command hooks in `.claude/settings.json`; 77 mise tasks; 69 python modules
- session-related python modules: `handoff_check`, `memory_index`, `session_gate`,
  `session_ledger`, `session_review`, `session_state`, `session_store`
- five session skills: session-handoff 297 lines / 16,899 B; session-resume
  114 / 4,291; session-review 244 / 14,349; handoff 83 / 4,368; resume 74 / 2,998
- `.gitignore` ignores five planning artifacts root-anchored at lines 95-99

## Lane A — overlap and conflict map

**Objective given:** produce the decision-grade overlap map — for every piece of
our session/planning/workflow machinery, does the plugin already do it, partly
do it, or not at all, and where can the two conflict and cause bugs. *"The
outcome this enables: a delete list."*

**Required contents:** a per-item table with a DUPLICATED / PARTIAL / UNIQUE
verdict; a CONFLICT section citing file:line; DELETE CANDIDATES ordered by
confidence with byte counts and the capability lost; a KEEP section.

**Key constraints:** read the actual files, do not infer capability from names
or documentation claims; say so explicitly where undeterminable; cite file:line
for every behavioural claim.

## Lane B — does the plugin deliver the operator's workflow

**Objective given:** answer three questions from the plugin's code rather than
its marketing —

1. Does it support granular, small-context task execution? Measure the actual
   injected payload sizes from `inject-plan.sh` and the hook configuration; do
   not estimate. If injection grows with plan size, say by how much and where it
   truncates.
2. Can the planning files be tracked in git? Determine what assumes they are
   machine-local, what tracking breaks (attestation, ledger, nonce, hooks), fresh
   clone behaviour, and merge-conflict behaviour across two worktrees.
3. What are its real failure modes — gated mode and its Stop oracle, the ledger,
   attestation, plan resolution, the parallel-plan pointer, session-catchup? For
   each: what breaks, loudly or silently, and would an operator notice.

**Required contents:** a verdict per question with cited file:line, then a FIT
ASSESSMENT — as-is, with configuration, or not at all.

**Key constraint:** treat README and CHANGELOG claims as unverified until the
code confirms them.

## Lane C — does something else already do this

**Objective given:** for each significant piece of custom agent machinery in the
repo, does an existing plugin, skill, tool, or native harness feature already do
it? Framed as `use-tool-builtins.md` and `tool-currency-and-native-first.md`
*"applied to the repo's own agent tooling, which has probably never had it
applied to it."*

**Scope named:** session tracking; requirement coverage and automation mining;
the PreToolUse command guard; doc-reference integrity; markdown size budgeting;
verification contracts; agent-report persistence and notepad conventions; the
project doctor; anything else judged to be maintained-Claude-infrastructure
rather than product work.

**Required contents:** one row per item — what it does, size, whether a
replacement exists, the named replacement, REPLACE / KEEP / INVESTIGATE with
reasoning; then a ranked list of highest-value retirements.

**Key constraints:** verify a named replacement actually exists and does the job;
distinguish "an alternative exists" from "an alternative is better here"; and
explicitly — *"a report that recommends replacing everything is as useless as one
that recommends replacing nothing."*

## Lane D — context budget audit

**Objective given:** the operator's instruction surface may be working against
their small-context goal. Measure it in real bytes, then say what to cut.

**Required measurements:** the standing cost before any work (root instruction
closure, every unscoped rule, skill and agent listing strings, SessionStart
injections), sorted largest first; the per-turn and per-tool-call injection cost
by hook; and the fraction of a 200k-token window at a stated 4-bytes-per-token
assumption.

**Required contents:** a ranked cut list classifying each large item as
load-bearing judgment, relocatable reference, redundant-with-a-gate, or dead —
specific enough to act on the top five without further analysis.

**Key constraint:** distinguish what loads ALWAYS from what loads ON DEMAND —
*"getting that wrong invalidates the whole report."*

### Lane D dissented once, correctly

Round 1 stopped under the licensed-dissent clause rather than produce a report on
a false premise. The brief asserted all 31 skill descriptions are standing
context; three skills carry `disable-model-invocation: true` and are absent from
the model-facing listing, so the real number is 28. The architect verified this
independently — those three do not appear in the session's own skill listing —
and re-dispatched with the corrected premise plus a required new section asking
which of the remaining 28 could take the same flag. That section's answer: none
safely, two experiment-only.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the tree under audit.
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — the plugin all four lanes read.
