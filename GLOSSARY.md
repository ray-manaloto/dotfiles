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
