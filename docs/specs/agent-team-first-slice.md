# Spec — the agent team, first slice

**Source design:** `docs/agent-team.md` (on `main`). **Evidence:** `prototype/RESULTS.md`
claims 0–6, on the never-merged `prototype/agent-team-mechanisms` branch.

**The GitHub issue is the canonical tracker entry** for triage and `/to-tickets`; this file is
the reviewed copy that survives a clone. If the two disagree, the issue is newer.

## Problem Statement

Nothing of the agent team is built. Every delegation this repo performs today is ad-hoc: the
session writes a brief by hand, spawns an agent, and hopes. That has failed in measurable,
repeated ways — in one recent research run, four agents were spawned, **two died leaving
nothing on disk and one finished but went idle without reporting**, and the surviving reports
had to be chased by hand because three of them ended with a section still reading
`_(to be filled)_`.

The failures are not random, and they are not fixed by writing the instruction down again:

- **Delivery is unenforced.** `agent-report-persistence.md` requires verbatim persistence at
  receipt, and it has been violated three times, twice with the requirement sitting in the
  agent definition itself. Prose cannot stop an agent from ending its turn.
- **Orchestration is not repeatable.** The plan lives in one session's context window, so
  nothing about a delegation can be reviewed, diffed, or improved — only re-typed.
- **The knobs silently do not apply.** Passing `name` to the Agent tool converts a role into a
  teammate, which drops `skills`, `mcpServers` and `hooks` with no warning and no error. A
  carefully tuned role definition can run with none of its tuning and look like it worked.
- **Cost is unmanaged.** Every delegated agent pays a full project-context load — measured at
  **~78–85 k tokens regardless of task size** — and Claude's session and weekly windows are
  shared across all models, so switching models recovers nothing.

The maintainer wants a reusable team he can point at a task and improve over time. What exists
is a pile of research and two agent definitions.

## Solution

Build the **smallest slice that runs a real task end to end**, so the design stops being a
document and starts producing evidence.

That slice is three things:

1. **A workflow orchestration script** — the plan as versioned, diffable, resumable JavaScript
   rather than a model deciding turn by turn. Roles are dispatched by `agent()`, results are
   typed via `schema:`, and per-stage `model:` is the seam through which work is routed to
   Codex or to Fable.
2. **Three role definitions** — `researcher`, `executor`, `adversarial-reviewer` — the smallest
   set that exercises every mechanism the design bets on: structured output, cross-family cold
   review, and per-stage model routing.
3. **Enforcement that actually fires** — a `SubagentStop` hook in **session-level
   `settings.json`** that refuses to let a role end its turn without having persisted its
   report, plus the settings that are absent today and get multiplied by team size.

The human stays in the loop through a **`gate`** node: because a workflow cannot take user
input mid-run, a gated pipeline is *one workflow per gated stage*, and the gate is a
first-class stop rather than an implicit pause.

Correctness is checked by a **single new seam**: one validator module with a pure entry point
that reads the role definitions, the orchestration script and the settings, and returns
violations. Unit tests exercise that function directly. **No agent is ever executed in CI** —
a runner has no Claude Code subscription — so nothing in the automated gate depends on a model
being reachable.

## User Stories

1. As a maintainer, I want the plan for a delegated task to live in a script I can read and
   diff, so that I can improve an orchestration instead of retyping a brief.
2. As a maintainer, I want each role's output to arrive as a validated object rather than
   prose, so that the next stage can consume it without me parsing it by hand.
3. As a maintainer, I want a role to be physically unable to end its turn without persisting
   its report, so that a dead or idle agent still leaves its work on disk.
4. As a maintainer, I want a role that writes its findings incrementally, so that an agent that
   dies at 60% leaves 60% rather than nothing.
5. As a maintainer, I want a report that still contains a placeholder to be treated as
   unfinished, so that "it emitted its final heading" stops being mistaken for "it is done".
6. As a maintainer, I want every role definition to declare which execution modes it supports,
   so that a role tuned with `hooks:` is never silently spawned in a mode that ignores them.
7. As a maintainer, I want a gate that stops the pipeline and waits for me, so that unattended
   running never silently passes a decision I wanted to make.
8. As a maintainer, I want the gate to refuse to auto-answer a destructive or irreversible
   option, so that autonomy never extends to the choices I would want to be asked about.
9. As a maintainer, I want one stage of a run routed to Codex without changing the rest of the
   run, so that I can offload volume against a subscription I already pay for.
10. As a maintainer, I want the judgment-heavy stages routed to the most capable model while
    breadth goes to cheaper ones, so that spend tracks the value of the decision.
11. As a maintainer, I want a deliberate default model for delegated work, so that roles do not
    land on a harness default nobody chose.
12. As a maintainer, I want a run to be resumable after I interrupt it, so that a long pipeline
    is not all-or-nothing.
13. As a maintainer, I want the pipeline shaped so an interrupt is cheap, so that stopping a
    run does not discard agents that had already finished.
14. As a maintainer, I want the reviewer to see the diff without being told what it was
    supposed to do, so that design context does not prime it to confirm the happy path.
15. As a maintainer, I want the reviewer to come from a different model family than whatever
    implemented the change, so that the review does not inherit the author's blind spots.
16. As a maintainer, I want every review finding to carry a citation or be labelled unverified,
    so that a plausible-sounding claim is distinguishable from a checked one.
17. As a maintainer, I want the researcher to check the offline vendor docs on disk before
    reaching the network, so that a question already answered locally costs nothing.
18. As a maintainer, I want each role to record which repositories it consulted, so that the
    research corpus stays bisectable after the fact.
19. As a maintainer, I want a role to escalate a question to the lead rather than asking the
    user directly, so that it stops violating a rule it is structurally incapable of obeying.
20. As a maintainer, I want the lead to own every user-facing question, so that the quality gate
    on questions still applies to work a role initiated.
21. As a maintainer, I want a role to be told at spawn that it is on the wrong branch, so that
    it does not do an hour of work whose every write is then denied.
22. As a maintainer, I want roles forbidden from shipping, merging and landing, so that one role
    cannot close a branch the rest of the run is still using.
23. As a maintainer, I want roles given disjoint file ownership at dispatch, so that two roles
    never overwrite each other's work.
24. As a maintainer, I want a role that needs an isolated tree to branch from the working
    branch, so that it does not silently get a tree missing the branch's commits.
25. As a maintainer, I want a validator that fails the lint gate when a role definition is
    malformed, so that a broken role is caught at commit rather than at run time.
26. As a maintainer, I want the validator to fail when a role declares a knob its declared mode
    ignores, so that the silent-misconfiguration failure becomes a loud one.
27. As a maintainer, I want the validator to fail when the enforcement hook is missing from
    session settings, so that enforcement cannot quietly regress to nothing.
28. As a maintainer, I want the validator to fail when a role file exists that the orchestration
    script never dispatches, so that dead roles do not accumulate.
29. As a maintainer, I want the validator to fail when the script dispatches a role that has no
    definition, so that a typo is caught before a run.
30. As a maintainer, I want the whole validation chain asserted by a contract, so that the hk
    step, the CLI and the tests cannot drift apart.
31. As a maintainer, I want every check to run without a Claude Code subscription, so that CI
    can gate it on a runner.
32. As a maintainer, I want the validator's failure direction pinned by a test, so that a check
    that can only pass is caught as decoration.
33. As a developer, I want the validator exposed as one pure function over explicit inputs, so
    that tests substitute values instead of patching internals.
34. As a developer, I want expected values in tests to come from an independent source rather
    than being recomputed the way the code computes them, so that a test can actually disagree
    with the implementation.
35. As a developer, I want the test suite to parametrize over role definitions rather than
    copying a test per role, so that adding a fourth role does not mean adding a fourth test.
36. As a developer, I want the module to satisfy the repo's strict lint and type configuration
    with no inline suppressions, so that it holds the same bar as everything else here.
37. As a maintainer, I want the first slice to run one genuinely useful task, so that the design
    is judged on output rather than on its own plausibility.
38. As a maintainer, I want the run's per-agent transcripts retained, so that I can audit what
    an agent actually did rather than what it said it did.
39. As a maintainer, I want a record of what a run cost, so that the wrapper tax stops being an
    unverified number in the design doc.
40. As a maintainer, I want each role to carry its own memory index if it is meant to learn, so
    that a recorded lesson is not written to a store nothing reads.
41. As a maintainer, I want roles spawned in the mode that keeps memory isolated, so that
    several roles do not collide in one shared store and index themselves into the file loaded
    into every session.
42. As a maintainer, I want the slice documented well enough that the remaining roles can be
    added by following it, so that the second slice is cheaper than the first.

## Implementation Decisions

### Orchestration

- **The orchestrator is a script, not an agent.** Roles live as definitions; the thing that
  sequences them is a dynamic workflow script — the versioned, reviewable artifact. The
  coordination a role would have done becomes code.
- **The script coordinates and never acts.** It has no filesystem or shell access by design;
  every side effect goes through a role. This is the write/review isolation boundary.
- **Structured output is the contract between stages.** Each role is dispatched with a JSON
  Schema, so its result is validated at the tool-call layer rather than parsed hopefully.
- **Per-stage `model:` is the only routing seam.** Codex offload and Fable routing are both
  expressed there, so neither requires a change to a role definition.
- **A gated pipeline is one workflow per gated stage.** A run cannot take user input mid-flight,
  so the `gate` is a boundary between workflow invocations, not a node inside one.

### Interrupt economics — this shapes the script, not just its documentation

Measured (`prototype/RESULTS.md` claim 6, confirmed against the harness's replay code): resume
replays only up to the **first agent that did not finish**, and everything dispatched after it
re-runs **even when its result is already journaled**. The mechanism is a sticky first-miss
flag, so the boundary is **positional**, fixed by `agent()` dispatch order.

Three consequences the script must honour:

- Keep concurrent groups **narrow**. A wide fan-out interrupted while one member is slow
  discards every finished member dispatched after it, at ~78–85 k tokens each.
- Within a group, order the **likely-slowest work last**, so faster members survive an
  interrupt.
- Put stage boundaries **before** long-running work rather than after it.

Renaming a stage is cache-safe (`label` and `phase` are excluded from the journal key);
**reordering one is not**, because the key chains over the preceding call sequence.

### Roles

Three definitions, chosen as the smallest set that exercises every bet:

| Role | Why it is in the first slice |
|---|---|
| `researcher` | breadth work; exercises structured output and the offline-docs-first chain |
| `executor` | the volume lane; exercises Codex routing and the write path |
| `adversarial-reviewer` | exercises cold, cross-family review — the one thing that catches what the author cannot |

- **Every role file declares the execution modes it is valid for.** This is mandatory because a
  hybrid can be silently misconfigured, and the validator enforces it.
- **Roles are dispatched through the workflow**, which keeps them on the subagent path — where
  their frontmatter actually applies, and where their memory stores stay isolated.
- **`provide suggestions` is an output contract, not a role.** Every role's report ends with
  what it would change.
- **`self-learning` is a field, not a role**, and it is not automatic: a role that records a
  lesson must maintain its own memory index, or it has written to a store nothing reads.
- **Incremental persistence goes in the role definition**, not in the per-run brief — a
  requirement that must be remembered per-brief is one that will be forgotten.

### Enforcement

- **Enforcement lives in session-level settings, never in role frontmatter.** A frontmatter hook
  is dropped whenever a role is spawned with a `name`; session-level hooks apply inside
  subagents however they were spawned.
- **`SubagentStop` is the delivery gate.** It is measured to fire, block, and force an agent to
  do work it was never asked for, and its payload carries the agent's transcript path — so the
  hook can *inspect what the agent did* rather than merely nag. A report containing an
  unfilled placeholder is not a delivered report.
- **`SubagentStart` can only inject context.** It cannot block, and an exit-2 there renders in
  the subagent's own transcript where the parent never sees it — a gate that can only pass. The
  branch precondition is therefore injected as context, not enforced at spawn.
- **The block cap is finite.** After a bounded number of consecutive blocks the harness
  overrides the hook and ends the turn, so the hook must converge rather than nag forever.
- **`ship` / `land` / `automerge` are reserved to the lead**, stated in the dispatch prompt.
- **Disjoint file ownership is stated at dispatch**, because no configuration enforces it.

### Settings that are absent today

These are prerequisites, and each is multiplied by team size: a deliberate default model for
delegated work; an isolated tree that branches from the working branch rather than the default
branch; an explicitly pinned spawn depth, since the default has changed three times in five
releases; and the user-scope agent directory, which must exist *before* the session that needs
it because the watcher only covers directories present at session start.

### The validation seam

One new module, `dotfiles_setup.agent_team`, exposing a **pure `find_violations()`** over
explicit inputs — the role-definition set, the orchestration script, and the settings — mirroring
`bash_budget`, `hook_guard` and `ask_quality`. Around it, thin wrappers only: a CLI subcommand, an
hk step that calls it, and a `suites.toml` contract asserting the whole chain exists so it cannot
drift apart. The rule the module encodes:

- every dispatched role resolves to a definition, and every definition is dispatched;
- every definition declares its valid execution modes, and declares no knob its declared mode
  ignores;
- the enforcement hook is present in session settings;
- the prerequisite settings above are set.

## Testing Decisions

**What a good test is here:** it exercises a **public interface** — an exported function, a
CLI's rc and output — never an implementation detail. A test that breaks under refactor while
behaviour is unchanged is coupled to structure and is wrong.

Two anti-patterns are disqualifying, both of which surface as a green suite rather than a
failure:

- **Tautological** — the assertion recomputes the expected value the way the code does, so it
  can never disagree with the code. Expected values come from an **independent source**: a
  known-good literal, a worked example, a real artifact.
- **A probe with no control arm** — a check that can only pass is not a check. Every rule the
  validator enforces is tested in **both directions**: a fixture that violates it must FAIL, and
  a fixture that satisfies it must PASS. The failing fixture must break the rule *realistically*
  — deleting the wiring, not renaming a symbol whose original survives as a substring.

**What gets tested:** `dotfiles_setup.agent_team` through `find_violations()`, parametrized over
the rule set so a fourth role or a fourth rule does not mean a fourth copied test. Fixtures are
built in `tmp_path`; the function takes its inputs as parameters, so there is no patching.

**What does not get tested automatically:** anything requiring a model. CI has no Claude Code
subscription, so no automated gate spawns an agent, runs a workflow, or asserts a role's output.
Runtime behaviour is verified the way `prototype/RESULTS.md` verifies it — a deliberate probe
run by hand, reporting both arms, recorded with its numbers.

**Mocking** happens at system boundaries only — never our own modules. Where a boundary exists,
the dependency is **injected as a parameter** rather than constructed inside the function, which
is the pattern already in use here.

**Toolchain:** Python 3.14 under `uv`, `ruff` with `select = ["ALL"]` and the repo's documented
ignore set, `ty` for type checking, full annotations, Google-convention docstrings, and **zero
inline suppressions** — `noqa`, `type: ignore`, `pylint: disable` and `nosec` are rejected by
the lint gate, tests included. New tests follow the existing `sys.path` convention rather than
requiring an editable install, use named constants over magic numbers, and are invoked as
`uv run --project python pytest tests/` — never `--directory`.

**Prior art to follow:** `test_hook_guard.py` and `test_ask_quality.py` for a pure decision
function tested through its public entry point in both directions; `test_bash_budget.py` for an
allowlist-plus-budget validator; `test_hook_selfcheck.py` for driving a wiring chain end to end;
`workflow.branch-write-guard-wiring` in `suites.toml` for asserting that the chain exists.

## Out of Scope

- **The remaining roles** — `planner`, `qa`, `documentation`, and the `optimizer`. They are
  deliberately deferred: eight definitions written before the team has run once are eight
  guesses, and the vendor's own advice is to start small.
- **Agent teams.** The first slice uses the subagent path exclusively. Teams stay reserved for
  lateral argument between peers, which is the one thing neither subagents nor workflows can do,
  and they are worth their cost only there.
- **Shipping the team as a plugin.** Plugin-scoped agents ignore `permissionMode`, `mcpServers`
  and `hooks`, which this design depends on.
- **Cross-session durability.** Workflow resume works only within a session; surviving a
  `/clear` is a separate problem.
- **Channels and permission relay.** A research preview, and relay hands the approver full
  tool-approval authority over the session.
- **The self-improving loop.** An optimizer that edits role files on the strength of its own
  evals inherits the blind spot that evals are already known to miss. It needs the borrowed
  guards designed first.
- **Any change to the existing `staleness-auditor` and `dockerfile-reviewer` definitions.**
- **Fixing the inert user-scope settings key** flagged in the audit — a user-level file, out of
  bounds without a separate decision.

## Further Notes

- **Three hazards must survive into implementation**, because each has already produced a wrong
  result: a **named** spawn is a teammate and silently drops `skills`/`mcpServers`/`hooks`;
  **`memory:` is not automatic learning**, and on the teammate path it pollutes the shared
  project memory index; and an **interrupt discards every agent dispatched after the earliest
  unfinished one**.
- **A known prerequisite defect:** the rule requiring a delegated agent to use the question tool
  is unobeyable inside a delegated agent, because that tool does not exist there. The rule needs
  its escalation clause before any role is expected to comply.
- **A known cost defect:** the write guard is measured at ~340 ms per edit and is paid per
  agent. Finish that optimisation before multiplying it.
- **The agent-type registry lags disk.** Definitions created mid-session were not resolvable on
  the unnamed spawn path for roughly two hours. Create role files, then start a fresh session.
- **The wrapper tax is unverified.** The per-delegation cost of the Codex lane on this machine
  has never been measured; the harness's own usage view is the instrument that would settle it,
  and doing so would replace a guess in the design doc with a number.
- **Do not infer OpenAI's Codex rate limits** from anything in the design doc — they are
  explicitly unverified there.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo this spec is for
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the installed binary was
  read directly to confirm the workflow resume mechanism
