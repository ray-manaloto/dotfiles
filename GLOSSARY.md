# dotfiles

A mise monorepo for the global tool config, the zsh startup files, Claude Code mods and the C++26
toolchain. Its work queue lives in this repository's GitHub Issues, including the work carried over
when the claude-code-marketplace repository was sunset.

## Language

### Work items

**Source issue**:
An issue that records work as it was found, before it is specified: an issue transferred from
claude-code-marketplace, or a `Sunset port: ...` issue that gathers items which had none.
It closes only once its tickets cover it.
_Avoid_: Ticket, task, backlog item

**Spec group**:
The source issues that share one `group:<slug>` label and are specified together, through
grill-with-docs, `/to-spec` and `/to-tickets`, into one spec.
_Avoid_: Epic, batch, lane

**Ticket**:
One issue `/to-tickets` creates from a spec: a unit of work small enough to implement and review
on its own. Each ticket has one line in the planning-with-files `task_plan.md` that links it.
_Avoid_: Task, subtask, source issue

### Triage outcomes

Every item from the sunset was given exactly one outcome. Only PORT and PARK items came here.

**PORT**:
The work is still needed and moves to this repository.
_Avoid_: Migrate, keep

**DONE**:
The work is already done, here or elsewhere, so it does not move.
_Avoid_: Closed, fixed

**OBSOLETE**:
The work is no longer needed, so it does not move.
_Avoid_: Won't do, dropped

**PARK**:
The work is still valid but deferred; it moves here and waits, labelled `parked`.
_Avoid_: Backlog, later, someday

### Priorities

**P0**:
A blocker for this repository: `main`'s tests, its review gate or a rule it states is broken.
P0 work comes before anything else.

**P1**:
P2996 (C++26 reflection), the C++26 core and their prerequisites.

**P2**:
Other global-config and migration work.

**P3**:
Everything else.

### Repository rules

**Zero-bash finding**:
One place where the repository breaks its zero-bash rule: a tracked shell file, a shell shebang, or a
mise `run` that spans more than one line.
_Avoid_: Violation, leftover, bash debt

**Zero-bash exception**:
Shell the zero-bash rule itself allows, so it is not a finding. AGENTS.md states each one; today
the only exception is the zsh startup files under `unix/home`.
_Avoid_: Waiver, skip, ignore

### CBM upgrades

**Upgrade trial**:
A run of a candidate CBM release with private client configs and its own CBM runtime namespace, without model
tokens, that captures what the release would change in the setup. It is the only place a candidate runs before its PR merges.
_Avoid_: Sandbox run, dry run, test install

**Live setup**:
The CBM build, launcher and client integrations (configs, hooks, agents, skills) that open sessions use.
A trial or prepare that changes it has failed; the allowlisted writes to the shared mise store are not changes
to it.
_Avoid_: Production, real install

**Upgrade change**:
One difference between a release and the reviewed baseline that is reviewed on its own: either an observed
setup difference or a changed source file the policy marks for review.
_Avoid_: Diff, delta, finding

**Acceptance**:
The owner's explicit approval of one upgrade change, valid only for that change as reviewed in that run.
Nothing generates it, and a policy violation cannot have one.
_Avoid_: Waiver, sign-off, approval record

**Apply**:
Moving the live setup to a merged release: closing sessions, installing, reindexing and restarting.
_Avoid_: Upgrade (for this step alone), deploy, rollout

### Labels

**`needs-triage`**:
The issue has not been specified into tickets yet. Every source issue starts with it.

**`from-marketplace`**:
The issue came from the claude-code-marketplace sunset.

**`group:<slug>`**:
The spec group the issue belongs to, such as `group:p2996-build`.

**`P0`, `P1`, `P2`, `P3`**:
The issue's priority, as defined above.

**`parked`**:
The issue's outcome was PARK: it waits, and gets no priority until it is picked up.
