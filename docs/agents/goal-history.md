---
name: dotfiles-goal-history
description: Append-only record of accepted dotfiles goal and ownership changes.
---

# Dotfiles goal history

This is the append-only record of accepted goal changes for dotfiles. It exists
so session review and SkillOpt can inspect how goals drift, where prompts are
ambiguous, and which orchestration choices repeatedly cost time. An entry
records a decision; it does not certify that the described work landed.

## Entry contract

- Append new iterations at the end. Never rewrite, reorder, squash, or delete
  earlier entries.
- `Prior goal digest` is the SHA-256 of the exact prior iteration's current goal
  text, excluding the Markdown quote prefix and trailing newline. The first
  tracked iteration uses `NONE (bootstrap)`.
- Append-only verification uses the fixed `origin/main` merge-base, checks every
  first-parent branch revision sequentially, then checks the working tree
  against committed `HEAD`. An unresolved baseline fails closed.
- Evidence must be independently inspectable. Missing evidence remains named as
  missing rather than inferred from assistant prose.
- `Topology and ownership` names the single current implementation writer for
  each repository and every handoff or collision risk.
- Every entry includes the current goal text and a current Mermaid workflow.

## 2026-08-14 — establish the tracked orchestration goal

- **Iteration ID:** `dotfiles-goal-20260814-001`
- **Prior goal digest:** `NONE (bootstrap)`
- **Current goal digest:** `sha256:12db9f86a5d17902e58b0cdc7330939cf2f1e025fb2a06d96c056860f6349385`
- **Changed requirement:** Establish an append-only goal history, make it a
  default session-review source, and enforce its required structure. Record the
  move from resumed Desktop tasks to one fallback subagent writer per repository.
- **Reason:** Both Desktop tasks completed their resumed goals. Peer task
  messaging was unavailable, so continued implementation required an explicit
  ownership handoff without allowing two writers to mutate one repository.
- **Evidence:** dotfiles PR #750 landed the task-orchestration skill; PR #752
  landed the final #671 acceptance test; knowledge-base coordination handshake
  v14 is recorded on issue #292. The local Graphify 0.9.42 health check reported
  a missing graph, so source files—not graph output—were authoritative here.
- **Affected tickets:** knowledge-base #292 and #299; dotfiles #750 and #752;
  dotfiles #753; this dotfiles goal-history implementation lane.
- **Disposition:** `ACCEPTED_AND_ACTIVE` — the Graphify-first MVP continues;
  this entry does not claim that knowledge-base #299 or later MVP tickets landed.
- **Topology and ownership:** The supervisor owns cross-repository coordination.
  One fallback subagent owns dotfiles and one owns knowledge-base. If a user
  restarts either Desktop task, that creates a duplicate-writer hazard: the
  Desktop task and fallback writer must handshake, and one must stop before
  either changes repository bytes. This is a manual coordination protocol, not
  executable prevention; dotfiles issue #753 tracks the native ownership lease.

### Current goal

> Implement and land the dotfiles append-only goal-history contract. Keep it discoverable to session review, enforce required iteration structure, and record orchestration topology changes without duplicating knowledge-base Graphify, SkillOpt, shared expert-bundle, or devcontainer work.

### Current workflow

```mermaid
flowchart LR
    U["Accepted goal or topology change"] --> H["Append goal-history iteration"]
    H --> S["Session review reads bounded history tail"]
    S --> D["Disposition: preserve, pivot, or backlog"]
    D --> O["Confirm one writer per repository"]
    O --> I["Implement current tracer bullet"]
    I --> V["Independent review and gates"]
    V --> L["Ship and land"]
    L --> H
    R["Desktop task restarts"] --> C{"Writer collision?"}
    C -->|"yes"| X["Handshake; stop one writer"]
    C -->|"no"| O
    X --> O
```

## 2026-08-14 — distinguish subagents from Desktop peer tasks

- **Iteration ID:** `dotfiles-goal-20260814-002`
- **Prior goal digest:** `sha256:12db9f86a5d17902e58b0cdc7330939cf2f1e025fb2a06d96c056860f6349385`
- **Current goal digest:** `sha256:123c4c2c1ae590ecc2f24123e89ec840bd4aae809f3ba3a448856d384277ae9f`
- **Changed requirement:** Update the landed orchestration skill after PR #755
  so it distinguishes parent-controlled subagents from independent Desktop
  sidebar tasks using the current callable tool catalog. Add recovery-vault-first
  missing-file lookup and a tracked Mermaid mirrored and read back from the
  authorized PR.
- **Reason:** Official Subagents documentation now explicitly describes
  enabled, inspectable agent threads under the main task. The installed Desktop
  bundle and reviewed peer-message screenshot describe a separate sidebar-task
  plane. Earlier orchestration could still conflate a finished wait/turn with
  goal completion or infer transport availability from a model slug.
- **Evidence:** `origin/main` was verified at PR #755 squash
  `307c95baf866b1c3ae591239479cf7e5b815b819`; the official Subagents page was
  read on 2026-08-14; the user-supplied Reddit screenshot matched SHA-256
  `cc4411af0b12b75daa23b82dbee63f646f31e3b354742d7961f08f3ecae81c30` and is
  retained only as non-authoritative evidence. Focused RED/GREEN receipts are
  in the branch-local structured contract; they do not certify live transport.
- **Affected tickets:** dotfiles PR #750; dotfiles issue #753; dotfiles PR #755;
  the current post-#755 task-orchestration delivery lane and its future PR.
- **Disposition:** `ACCEPTED_AND_ACTIVE` — implementation and focused
  verification are active. No PR, remote mirror, ship, or landing is claimed by
  this entry.
- **Topology and ownership:** The root supervisor owns cross-repository
  coordination. This task is the sole dotfiles implementation writer in
  `/Users/rmanaloto/dev/github/ray-manaloto/worktrees/dotfiles-codex-task-orchestration-v2`
  on `codex/codex-task-orchestration-v2`; the separate knowledge-base writer
  owns KB work. Parent-controlled subagents remain under their main task;
  independent Desktop tasks remain peer sidebar tasks. A restarted peer must
  handshake and stop one writer before touching this repository.

### Current goal

> Implement, validate, ship, and land the post-#755 Codex task-orchestration skill update from exact origin/main 307c95baf866b1c3ae591239479cf7e5b815b819. Distinguish parent-controlled subagents from independent Desktop sidebar tasks using only currently callable tools, preserve single-writer ownership and recovery-vault-first lookup, and keep the tracked Mermaid synchronized with the authorized PR mirror and readback. Synthetic evals test routing decisions but do not certify live transport.

### Current workflow

```mermaid
flowchart TB
    U["Accepted post-#755 orchestration goal"] --> C["Inspect currently callable tools"]
    C --> A{"Requested and callable plane"}
    A -->|"collaboration"| P["Parent-controlled subagents"]
    A -->|"Desktop task tools"| D["Independent Desktop sidebar tasks"]
    P --> O["One writer with acknowledged ownership"]
    D --> O
    O --> I["Implement RED then GREEN slices"]
    I --> V["Verify outcome; wait or turn is not goal completion"]
    V --> T["Track newcomer Mermaid"]
    T --> M["Mirror exact block to authorized PR"]
    M --> R["Read back and compare"]
    R --> L["Ship and land through project workflow"]
```

## 2026-08-14 — bound successor creation to Wayfinder transfers

- **Iteration ID:** `dotfiles-goal-20260814-003`
- **Prior goal digest:** `sha256:123c4c2c1ae590ecc2f24123e89ec840bd4aae809f3ba3a448856d384277ae9f`
- **Current goal digest:** `sha256:d50b4e3afefdc2a6310cce301ae6ad62327b57fa8a54275d75a97549fd28b521`
- **Changed requirement:** At a completed Wayfinder ticket or explicit
  ownership-transfer boundary, use a content-addressed handoff and a verified
  successor. Prefer a fresh visible Desktop task only when requested and
  `create_thread` is callable; otherwise disclose a bounded subagent fallback.
- **Reason:** Creating a task is identity setup, not communication, goal
  transfer, or proof that the successor started. Unbounded task-per-step
  creation would manufacture duplicate writers and an unsupported queue.
- **Evidence:** The user-approved refinement requires asynchronous identity
  resolution, peer-owned `create_goal`, full handoff acknowledgment, and
  independent verification before retiring the prior writer. Hostile evals
  14-17 reproduce premature retirement, successor churn, missing goal
  acknowledgment, and unavailable task creation; the focused structured
  contract failed before each corresponding skill rule was added and then passed.
- **Affected tickets:** dotfiles PR #750; dotfiles issue #753; dotfiles PR #755;
  the current post-#755 task-orchestration delivery lane and its future PR.
- **Disposition:** `ACCEPTED_AND_ACTIVE` — the successor-transfer protocol and
  synchronized tracked diagram are implemented locally. Independent review,
  full gates, PR mirror/readback, ship, and landing remain unclaimed.
- **Topology and ownership:** This task remains the sole dotfiles writer in
  `/Users/rmanaloto/dev/github/ray-manaloto/worktrees/dotfiles-codex-task-orchestration-v2`.
  A successor receives no write authority from creation alone. The prior writer
  remains authoritative until the coordinator independently verifies the
  successor's inherited SHA, issue, ownership, first action, return channel,
  checkout identity, and peer-owned goal acknowledgment; then the prior writer
  retires so exactly one writer remains.

### Current goal

> Implement, validate, ship, and land the post-#755 Codex task-orchestration skill update from exact origin/main 307c95baf866b1c3ae591239479cf7e5b815b819. At a completed Wayfinder ticket or explicit ownership transfer, freeze a content-addressed handoff and dispatch a verified successor through callable Desktop task creation or a disclosed bounded subagent fallback while preserving exactly one writer. Keep the tracked Mermaid and authorized PR mirror synchronized; synthetic evals test decisions but do not certify live transport.

### Current workflow

```mermaid
flowchart TB
    B["Completed Wayfinder ticket or explicit transfer"] --> F["Freeze content-addressed handoff"]
    F --> C{"Visible task requested and create_thread callable?"}
    C -->|"yes"| T["Create asynchronously; resolve threadId + hostId"]
    T --> G["Send handoff; peer calls its own create_goal and begins"]
    C -->|"no"| S["Fresh bounded subagent; report not sidebar-visible"]
    G --> A["Acknowledge SHA, issue, ownership, first action, return channel"]
    S --> A
    A --> V["Independently verify acknowledgment and checkout"]
    V --> R["Retire prior writer; exactly one writer remains"]
    R --> M["Mirror tracked Mermaid to authorized PR"]
    M --> Q["Read back and compare before ship"]
```

## 2026-08-14 — make successor ownership transfer non-overlapping

- **Iteration ID:** `dotfiles-goal-20260814-004`
- **Prior goal digest:** `sha256:d50b4e3afefdc2a6310cce301ae6ad62327b57fa8a54275d75a97549fd28b521`
- **Current goal digest:** `sha256:16675f8af4fe99579fa867b5a82e1dbc4d4552c18b2dbd37996ba2a8d8959a26`
- **Changed requirement:** Bind handoffs to canonical bytes and a successor-
  acknowledged digest; gate Desktop operations independently; transfer write
  authority only after predecessor relinquishment; recover a spawn thread-limit
  by explicitly reusing a suitable confirmed-idle agent when available.
- **Reason:** Independent review showed that one acknowledgment could authorize
  the successor before the predecessor stopped, while bundled Desktop gating
  unnecessarily rejected existing peers. A live spawn-capacity failure also
  established the safe idle-agent reuse branch.
- **Evidence:** Hostile evals 18-23 cover digest substitution, missing creation
  with existing peers, premature Desktop and subagent starts, safe idle reuse,
  and rejection of active-writer reuse. The parsed structured eval contract
  fails malformed JSON and missing required eval IDs. The operative protocol
  and newcomer diagram are co-located in
  `docs/agents/codex-task-orchestration.md`; synthetic results remain routing
  evidence, not live-transport certification.
- **Affected tickets:** dotfiles PR #750; dotfiles issue #753; dotfiles PR #755;
  the current post-#755 task-orchestration delivery lane and its future PR.
- **Disposition:** `ACCEPTED_AND_ACTIVE` — focused implementation and review are
  active; full gates, remote mirror/readback, PR, ship, and landing are unclaimed.
- **Topology and ownership:** This task remains the sole dotfiles writer. A
  successor stays read-only until the predecessor explicitly relinquishes and
  confirms idle/no ownership, after which the coordinator sends a separate
  bounded start signal. Active agents cannot be repurposed as successors.

### Current goal

> Implement, validate, ship, and land the post-#755 Codex task-orchestration update from exact origin/main 307c95baf866b1c3ae591239479cf7e5b815b819. Bind each successor to canonical handoff bytes and a verified digest, transfer write authority only after read-only acknowledgment and predecessor relinquishment, gate Desktop operations independently, and recover agent-thread capacity only by explicitly reusing a suitable confirmed-idle agent. Keep the tracked Mermaid and authorized PR mirror synchronized; synthetic evals test decisions but do not certify live transport.

### Current workflow

```mermaid
flowchart LR
    F["Freeze canonical bytes + SHA-256"] --> S{"Select eligible successor"}
    S -->|"existing peer"| P["Gate only needed peer operations"]
    S -->|"fresh task/subagent"| N["Resolve or spawn identity"]
    N -->|"thread limit"| I["Reuse suitable confirmed-idle agent"]
    P --> A["Read-only digest + checkout acknowledgment"]
    N --> A
    I --> A
    A --> R["Predecessor relinquishes; confirms idle/no ownership"]
    R --> G["Separate coordinator start signal"]
    G --> V["Verify successor start and bounded ownership"]
    V --> M["Mirror tracked Mermaid to authorized PR; read back"]
```

## 2026-08-14 — enforce repository writer ownership with a native lease

- **Iteration ID:** `dotfiles-goal-20260814-005`
- **Prior goal digest:** `sha256:16675f8af4fe99579fa867b5a82e1dbc4d4552c18b2dbd37996ba2a8d8959a26`
- **Current goal digest:** `sha256:09a7817194767104656947976c06e0a6abda9911eec6089d07698273d3fd9944`
- **Changed requirement:** Implement issue #753's executable startup and
  pre-mutation ownership lease after the orchestration protocol landed in PR
  #756. Bind ownership to the shared Git common directory, not a checkout path,
  and prove contention, handoff, and stale recovery through real processes.
- **Reason:** Different tasks, branches, and worktrees do not prove disjoint
  ownership. PR #756 made the handoff ordering explicit but deliberately left
  collision prevention to this follow-up.
- **Evidence:** Canonical `main`, `origin/main`, and GitHub main were verified at
  PR #756 squash `5274363a218b4deaf1bce93ae51392c182a5d047`. The successor
  independently acknowledged canonical handoff digest
  `db873355c4d00e15e7ce3ee210b2446260d0ded60f6af6685dd570d1f4132e19`,
  the predecessor confirmed idle, and the coordinator sent a separate START.
  Graphify is source-fallback because the fresh worktree has no graph artifact.
- **Affected tickets:** dotfiles issue #753 and the future writer-lease PR.
- **Disposition:** `ACCEPTED_AND_ACTIVE` — the Wayfinder design is frozen;
  implementation, review, gates, PR, and landing remain unclaimed.
- **Topology and ownership:** This task is the sole dotfiles writer in
  `/Users/rmanaloto/dev/github/ray-manaloto/worktrees/dotfiles-issue-753-writer-lease`
  on `codex/issue-753-writer-lease`. `/root` remains coordinator. Knowledge-base
  work stays exclusively in its separate lane.

### Current goal

> Design, implement, validate, ship, and land dotfiles issue #753: a project-native startup and pre-mutation repository ownership lease that identifies the Git common directory, fails closed on a live competing writer, supports content-addressed handoff and audited stale-owner recovery, preserves .omc/ and dirty evidence, and is proven by real hostile two-writer and clean handoff controls.

### Current workflow

```mermaid
flowchart LR
    F["Freeze design and public seam"] --> T["Real subprocess RED tests"]
    T --> I["Git-common-dir flock implementation"]
    I --> H["Hostile two-writer and recovery replay"]
    H --> V["Independent review and full gates"]
    V --> P["Ship PR and mirror exact visuals"]
    P --> L["Land; verify clean synchronized main"]
```

## 2026-08-14 — promote the Codex native hook to the enforcement boundary

- **Iteration ID:** `dotfiles-goal-20260814-006`
- **Prior goal digest:** `sha256:09a7817194767104656947976c06e0a6abda9911eec6089d07698273d3fd9944`
- **Current goal digest:** `sha256:e1c57ba574fd51956530556620e6c4b1945a612af64c2cdd0bc5cda363ccb8f0`
- **Changed requirement:** Replace explicit/manual Codex pre-mutation checks as
  the acceptance boundary with the installed Codex 0.147.0 native synchronous
  `PreToolUse` hook. It must intercept Bash and apply-patch calls for Desktop
  tasks and fallback subagents and deny a non-owner before execution.
- **Reason:** An advisory flock only excludes cooperating processes; prose or
  an optional check cannot intercept a raw Codex filesystem tool. The issue
  requires executable Desktop and fallback-subagent integration.
- **Evidence:** `codex features list` reports stable hooks. The current official
  Hooks reference confirms Bash/unified-exec/apply-patch coverage, synchronous
  pre-execution denial, `Edit|Write` aliases, and parent session IDs for
  subagents. A hostile linked-worktree control wrote its probe, and pinned
  Codex 0.147.0 source explains that linked worktrees intentionally load hook
  declarations from the canonical root checkout. Certification therefore runs
  from an independent temporary clone of the committed candidate.
- **Affected tickets:** dotfiles issue #753 and its writer-lease PR.
- **Disposition:** `ACCEPTED_AND_ACTIVE` — native hook integration and local
  subprocess controls are green; independent-clone Codex replay, reviews,
  gates, ship, and land remain unclaimed.
- **Topology and ownership:** `/root/dotfiles_753_writer_lease` remains the sole
  dotfiles writer in the registered issue #753 worktree; `/root` coordinates.
  The certification clone is disposable test input and never a work lane.

### Current goal

> Complete dotfiles issue #753 by landing a Git-common-dir flock lease with canonical receipts, native Codex and Claude pre-mutation hook enforcement, exact-digest handoff and recovery, real hostile subscription-authenticated Codex replay, synchronized visual documentation, independent review, full gates, and clean remote-main landing.

### Current workflow

```mermaid
flowchart LR
    H["Coordinator sends START + handoff digest"] --> A["Task acquires native flock lease"]
    A --> C["Codex or Claude PreToolUse intercepts mutation"]
    C --> Q{"Live task and worktree identity match?"}
    Q -->|"no"| D["Deny before tool execution"]
    Q -->|"yes"| W["Allow bounded mutation"]
    W --> V["Real-process tests + independent-clone Codex replay"]
    V --> R["Independent reviews + full gates"]
    R --> P["Ship, mirror diagrams, land, verify clean main"]
```

## 2026-08-14 — harden the writer lease after hostile review

- **Iteration ID:** `dotfiles-goal-20260814-007`
- **Prior goal digest:** `sha256:e1c57ba574fd51956530556620e6c4b1945a612af64c2cdd0bc5cda363ccb8f0`
- **Current goal digest:** `sha256:ccdb0f73970ca88baae2f85974abc81986aa83149abc1c1b336570930fa1bccd`
- **Changed requirement:** Keep issue #753 blocked after both frozen reviews found
  eight executable bypasses. Bind the receipt to the actual lock holder, make
  every state path private and no-follow, publish validated state atomically,
  pin bootstrap execution, track in-flight mutations through PostToolUse,
  derive transfer type from audit facts, cover Claude Bash, and preserve all
  dirty and `.omc/` evidence byte-for-byte.
- **Reason:** A cooperative flock and startup-only check could still report a
  false owner, follow hostile filesystem objects, publish partial state, run a
  PATH-substituted command, or transfer while an earlier Bash tool could still
  write. Those behaviors violate the single-writer acceptance boundary.
- **Evidence:** The first frozen hostile replay produced seven RED cases and one
  preservation control. The v1 lease state was retained at
  `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.git/codex-writer-lease-v1-preserved-007acb42`.
  The replacement uses a live token challenge plus lock record, private regular
  no-follow files, immutable content-addressed generations, validated canonical
  audit, audit-derived transitions, pinned Pre/Post hook runners, and an exact
  in-flight tool-ID ledger. Nineteen real-process controls now cover the review
  findings; independent review, live Codex replay, full gates, ship, and land
  remain unclaimed.
- **Affected tickets:** dotfiles issue #753 and its writer-lease PR.
- **Disposition:** `ACCEPTED_AND_ACTIVE` — review findings are implemented;
  second frozen review is the next gate.
- **Topology and ownership:** `/root/dotfiles_753_writer_lease` remains the sole
  writer in the registered issue #753 worktree. `/root` coordinates and owns
  reviewer dispatch after the writer freezes the exact diff.

### Current goal

> Complete dotfiles issue #753 by landing a challenge-bound Git-common-dir lease with private transactional content-addressed state, audit-derived transfer, native Codex and Claude Pre/PostToolUse in-flight drain, exact pinned bootstrap, real hostile and subscription-authenticated Codex replay, synchronized visual documentation, independent review, full gates, and clean remote-main landing.

### Current workflow

```mermaid
flowchart LR
    S["Pinned START + handoff digest"] --> H["Challenge-bound holder + private atomic generation"]
    H --> PRE["Codex or Claude PreToolUse records exact tool ID"]
    PRE --> M["Real mutation runs"]
    M --> POST["PostToolUse or write_stdin completion drains tool ID"]
    POST --> D{"Validated audit permits transfer?"}
    D -->|"released"| T["Derive clean handoff"]
    D -->|"dead holder, no in-flight tools"| R["Derive recovery"]
    D -->|"unsafe or active"| X["Fail closed"]
    T --> V["Hostile tests, dual review, live Codex replay"]
    R --> V
    V --> L["Full gates, ship, land, verify clean main"]
```

## 2026-08-14 — bound state growth and drain failed tools

- **Iteration ID:** `dotfiles-goal-20260814-008`
- **Prior goal digest:** `sha256:ccdb0f73970ca88baae2f85974abc81986aa83149abc1c1b336570930fa1bccd`
- **Current goal digest:** `sha256:17f5b65417b9cf0d13291a0223ecdb734b1a2680aa2c625a22635673c091c65f`
- **Changed requirement:** Keep the second freeze blocked until immutable state
  has bounded retention, Claude failed tools drain through
  `PostToolUseFailure`, and the branch-write plus token-uniqueness verification
  contracts remain green after the new integration.
- **Reason:** Retaining a complete audit in every immutable generation made
  cumulative disk use quadratic. A failed Claude Bash call emitted a different
  lifecycle event and could strand its in-flight ID forever. The integration
  also changed one branch-guard call-site token and introduced duplicate
  tokens, weakening existing verification even while focused tests passed.
- **Evidence:** The hostile controls now run 32 real Pre/Post pairs and require
  one retained generation, 65 canonical audit events, less than 128 KiB of
  state, no reclaim tombstones, and under 30 seconds. A real `/bin/sh` rc=23
  lifecycle drains via `PostToolUseFailure` and then proves both clean handoff
  and crash recovery. `dotfiles-setup token-audit` reports no binding problems.
- **Affected tickets:** dotfiles issue #753 and its writer-lease PR.
- **Disposition:** `ACCEPTED_AND_ACTIVE` — implementation and focused controls
  are green; full gates and the third frozen dual review remain unclaimed.
- **Topology and ownership:** `/root/dotfiles_753_writer_lease` remains the sole
  writer; `/root` owns reviewer dispatch after the new manifest freeze.

### Current goal

> Complete dotfiles issue #753 by landing a challenge-bound Git-common-dir lease with private transactional state, one retained content-addressed generation carrying the full canonical audit, audit-derived transfer, native Codex and Claude Pre/Post/failure in-flight drain, exact pinned bootstrap, real hostile and subscription-authenticated Codex replay, synchronized visual documentation, independent review, full gates, and clean remote-main landing.

### Current workflow

```mermaid
flowchart LR
    PRE["PreToolUse records exact tool ID"] --> RUN["Mutation runs"]
    RUN --> OK["PostToolUse drains success"]
    RUN --> FAIL["PostToolUseFailure drains failure"]
    OK --> PUB["Publish one durable current generation with full audit"]
    FAIL --> PUB
    PUB --> GC["Atomically rename and reclaim superseded generations"]
    GC --> XFER{"Validated audit and in-flight set permit transfer?"}
    XFER -->|"yes"| REVIEW["Full gates and dual frozen review"]
    XFER -->|"no"| DENY["Fail closed; preserve evidence"]
    REVIEW --> LIVE["Post-commit native Codex clone replay"]
    LIVE --> LAND["Ship, land, verify clean main"]
```

## 2026-08-14 — anchor cleanup and make completion race-safe

- **Iteration ID:** `dotfiles-goal-20260814-009`
- **Prior goal digest:** `sha256:17f5b65417b9cf0d13291a0223ecdb734b1a2680aa2c625a22635673c091c65f`
- **Current goal digest:** `sha256:81f81ed9945e7e51defe002a9d104dcf1a8a59fefa8f150954bfba9858385535`
- **Changed requirement:** Keep the third freeze blocked until generation
  reclaim is anchored to a validated directory descriptor, cleanup failures
  after state publication become non-denying typed debt, and completion plus
  release tolerate bounded state-lock overlap.
- **Reason:** Path validation followed by later path deletion retains a
  parent-swap race. Raising from cleanup after `current` was durably switched
  falsely denied a tool whose `tool_started` had already committed, stranding
  its in-flight ID. Nonblocking completion could lose an ordinary concurrent
  state transaction and create the same strand.
- **Evidence:** Real controls rename the state directory, replace its old path
  with a symlink to an external byte victim, and prove descriptor-relative
  reclaim touches only the originally opened directory. A malformed reclaim
  remains byte-identical typed debt while start and finish both return allow.
  Twenty-four alternating success/failure completions and holder release pass
  while independent processes repeatedly hold the real state lock.
- **Affected tickets:** dotfiles issue #753 and its writer-lease PR.
- **Disposition:** `ACCEPTED_AND_ACTIVE` — the construction controls are green;
  full staged-checkout gates and the fourth frozen dual review remain unclaimed.
- **Topology and ownership:** `/root/dotfiles_753_writer_lease` remains sole
  writer; `/root` owns reviewer dispatch after exact manifest freeze.

### Current goal

> Complete dotfiles issue #753 by landing a challenge-bound Git-common-dir lease with private transactional state, directory-FD-anchored no-follow reclamation, non-denying typed cleanup debt, bounded synchronous completion and release lock retry, native Codex and Claude success/failure drain, exact pinned bootstrap, real hostile and subscription-authenticated Codex replay, synchronized visual documentation, independent review, full gates, and clean remote-main landing.

### Current workflow

```mermaid
flowchart LR
    P["Publish and validate current generation"] --> FD["Retain validated state directory fd"]
    FD --> GC["Relative no-follow rename, unlink, rmdir"]
    GC -->|"success"| CLEAN["One current generation"]
    GC -->|"failure after commit"| DEBT["Typed cleanup_debt; do not deny tool"]
    PRE["Tool start committed"] --> RUN["Mutation succeeds or fails"]
    RUN --> RETRY["Bounded state-lock retry"]
    RETRY --> FINISH["Exact tool ID drained"]
    FINISH --> RELEASE["Release retries; audited handoff"]
    CLEAN --> REVIEW["Staged full gates and dual review"]
    DEBT --> REVIEW
    RELEASE --> REVIEW
    REVIEW --> LIVE["Post-commit native Codex clone replay"]
```
