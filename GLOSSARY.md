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
on its own. Each ticket has one line in the roadmap that links it, and its own ticket plan. The
same holds in every repository that uses the workflow; a ticket is never a file in the repository.
_Avoid_: Task, subtask, source issue, file ticket

**Roadmap**:
The planning-with-files `task_plan.md` that lists every ticket the repository is working on, one
line each, linking the ticket's issue and naming its ticket plan. It is local, never committed, and
can be rebuilt from the issues.
_Avoid_: Backlog, todo list, master plan

**Ticket plan**:
The planning-with-files plan for one ticket, kept in its own named folder outside every checkout,
so several worktrees and sessions can each work their own ticket at the same time.
_Avoid_: Session plan, scratch plan

**Coordinator**:
The one session that turns a spec into tickets: it creates each ticket's issue and ticket plan and is
the only writer of the roadmap.
_Avoid_: Lead, orchestrator, main agent

**Worker**:
A session that works one ticket in its own worktree, pinned to that ticket's plan. It never creates
a plan and never edits the roadmap.
_Avoid_: Subagent, helper

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
A trial or prepare that changes it has failed; the allowlisted writes to the shared mise store, and
the install step's allowlisted writes to mise's state and cache folders, are not changes to it.
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

### Agent workflow

**Agents folder**:
The one tracked home of everything every coding agent shares: the shared AGENTS.md, the workflow
docs and the workflow skills. Each agent reaches it through links, so none keeps its own copy.
_Avoid_: Agent config, skills repo, prompt folder

**Shared AGENTS.md**:
The instructions every agent reads in every repository, kept in the agents folder. A repository's
own AGENTS.md adds to it; it never repeats it.
_Avoid_: Global prompt, system prompt, CLAUDE.md

**Installer**:
A tool from outside this repository that sets an agent up and maintains instructions tied to that
setup.
_Avoid_: Setup script, bootstrap

**Managed block**:
A marked section of an instruction file that a named tool maintains.
_Avoid_: Generated section, injected block

**Snapshot block**:
A marked section taken from a tool and kept by the repository. Its text changes only through
review; the tool it came from never writes the delivered file.
_Avoid_: Frozen block, vendored block

**User scope**:
Delivery that reaches every repository on the machine, from the home folder, as opposed to project
scope, which reaches only the repository that holds the file.
_Avoid_: Global, machine-wide

**Workflow docs**:
The documents that say how work moves from an idea to a merged change, and which skills each step
uses. The workflow skills read them from the agents folder.
_Avoid_: Process docs, playbook

**Workflow facts**:
The few facts about one repository that the workflow docs leave open: its check, how a change
ships, where research goes and how a review is approved. Each repository states them in its own
AGENTS.md, after it has been set up for the workflow skills.
_Avoid_: Repo config, project settings

### Dependency maps

**Dependency map**:
The code graph (cbm, plus SCIP for Rust) of one dependency at one pinned version, kept outside the
repo.
_Avoid_: Index, snapshot

**Blast radius**:
The functions of a dependency that changed between two pinned versions and that our usage surface can
reach through callers.
_Avoid_: Impact, diff

**Host build**:
The code one machine actually compiles, meaning its target OS, family, arch and env.
_Avoid_: Platform build

**Inactive-code edge**:
An edge whose site is inside `#[cfg]` code that is off for the host build; kept in the blast radius
and flagged.
_Avoid_: Dead edge

### Agent sessions

**Reviewer**:
The read-only Codex session that reviews a change and gives the owner's approval line for it. It
reads and judges; it never changes the files it reviews.
_Avoid_: Approvals reviewer, guardian, checker

**Auto-reviewer**:
Codex's built-in model check that decides, in place of a person, whether an escalated command may
run. It is consulted only when the session's approval policy asks for approvals. It judges a command
against what the session's user messages asked for, whoever sent them.
_Avoid_: Guardian, Reviewer, approvals reviewer (except as the name of the Codex setting)

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
