# Process Enforcement Design: Durable Lane Work and Operator Questions

**Date:** 2026-09-01  
**Status:** Researched design; no implementation  
**Scope:** Claude Code's parent session, its `codex-*` wrapper subagents, the
inner `codex exec` calls they make, and this repo's planning-with-files plan.

`$CC` below means the vendor-doc snapshot at
`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`.
`$SCRATCH` means
`/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/ec02aa30-c480-4828-8d9c-3d7872e23daf/scratchpad`.

## Executive verdicts

### R1 — Codex lane work is always recorded in `task_plan.md`

**Verdict: PARTIALLY ENFORCEABLE — the harness can deterministically require a
machine-owned dispatch record before a codex wrapper starts work, but a local
record cannot prove that its description is accurate, complete, or current.**

### R2 — Operator-needed answers are always surfaced as usable prompts

**Verdict: NOT ENFORCEABLE as stated — no deterministic mechanism can detect a
semantically necessary question that the agent never recognized or chose to
ask; the strongest honest substitute is a checkable declaration and prompt
queue at lifecycle boundaries.**

## Decisive evidence

### A1 is refuted: parent settings hooks do see subagent tool calls

The premise that a subagent's tool calls do not fire the parent session's
project hooks is false in the current offline vendor docs:

- Settings-file hooks "also fire inside subagents"; `PreToolUse` and
  `PostToolUse` run on their tool calls, while `SubagentStart` and
  `SubagentStop` mark lifecycle boundaries (`$CC/sub-agents.md:671-678`).
- The hook payload inside a subagent carries a unique `agent_id` and its
  `agent_type` (`$CC/hooks.md:719-740`). The hooks reference repeats this
  inheritance explicitly (`$CC/hooks.md:252-265`).
- The parent conversation still does **not** receive intermediate tool calls or
  outputs; it receives the final result (`$CC/tools-reference.md:97-100`). Hook
  observability and parent-context visibility are different mechanisms.

This changes the design: parent-side hooks can enforce a structural record for
subagent work. It does not make the work's meaning machine-readable.

### The observable lifecycle

| Moment | Deterministically observable? | Useful payload | Limitation |
|---|---|---|---|
| Parent `PreToolUse(Agent)` | Yes | `tool_use_id`, exact `prompt`, `description`, `subagent_type` (`$CC/hooks.md:1526-1528`, `:1656-1667`) | No future `agent_id` yet |
| `SubagentStart` | Yes | `agent_id`, `agent_type`, session/cwd (`$CC/hooks.md:2251-2269`) | Cannot block creation; can only inject context (`:2272-2276`) |
| Each subagent tool call | Yes | `agent_id`, `agent_type`, tool input (`$CC/hooks.md:733-738`, `:1526-1528`) | Project hook can fail open or be bypassed |
| Parent `PostToolUse(Agent)` | Yes | Original input, `tool_use_id`, and response `agentId`; both completed and async launches carry it (`$CC/hooks.md:1667-1683`, `:1898-1919`) | Foreground completion is late, though the pre-dispatch record already exists |
| `SubagentStop` | Yes | `agent_id`, `agent_type`, transcript path, final message (`$CC/hooks.md:2287-2314`) | It cannot reconstruct work the report omitted |
| Commit | Sometimes | A `git commit` command or changed ref | Not every lane commits; commits can be made outside this harness |
| Caller's next turn | Yes, if it occurs | Agent result and current files | Too late for a lane that died without writing |

Dispatch is therefore R1's enforcement point. A report, commit, or later turn is
too late to prevent the observed loss.

### Existing mechanisms and their exact limits

- The current settings wire only a project `PreToolUse` hook for
  `Bash|AskUserQuestion|Edit|Write|NotebookEdit`, plus SessionStart/SessionEnd;
  there is no `Agent`, `PostToolUse(Agent)`, `SubagentStart`, `SubagentStop`, or
  `Stop` project hook today (`.claude/settings.json:39-95`).
- `ask_quality.py` deliberately says it can gate recommendation, trade-offs,
  and citations but cannot observe an ask that never happened
  (`python/src/dotfiles_setup/ask_quality.py:8-41`). Its public validator and
  deny decision are reusable seams (`:194-227`).
- `hook_guard.decide_payload` is the existing Python dispatcher behind the one
  PreToolUse wrapper, and its own doc says an internal crash fails open
  (`python/src/dotfiles_setup/hook_guard.py:788-830`).
- The ask-quality suite asserts the settings → dispatcher → validator →
  selfcheck → tests → rule chain, while explicitly disclaiming whether asking
  was the right call (`python/verification/suites.toml:1203-1218`). This is the
  right contract pattern to extend, not a substitute for runtime behavior.
- The installed planning-with-files 3.12.0 plugin already has active-plan
  resolution, a per-agent append-only JSONL ledger, plan attestation, and an
  opt-in Stop gate. Its ledger explicitly says workers write ledgers while the
  orchestrator owns `task_plan.md` (`scripts/ledger-append.sh:1-33` in the
  installed plugin). Its Stop gate only checks an `in_progress` phase and then
  allows stop after a cap or no ledger progress (`scripts/check-complete.sh:16-25`,
  `:132-217`). It does **not** make R1 or R2 hold.
- The plugin's own contributor guidance says not to log subagent returns in
  `task_plan.md`; use `progress.md` (`AGENTS.md:153-160` in that plugin). The
  operator's R1 intentionally overrides that upstream convention. The design
  should borrow its resolver and append-only ledger pattern, not pretend the
  unmodified plugin already meets R1.

The failure record is consistent with those limits. The repo rule reports that
the persistence requirement reached none of four briefs, two agents died after
about 40 minutes and wrote nothing, and one survivor persisted only on its own
initiative (`.claude/rules/agent-report-persistence.md:31-44`). The plan records
three codex lanes dying without a structured report (`$SCRATCH/task_plan-snapshot.md:796-800`).

## R1 design — a machine-owned lane event registry inside the active plan

### Recommendation

Extend the existing Python hook chain so a canonical codex dispatch cannot
proceed until it has appended a structured `dispatch` event under a reserved
`## Codex lane registry (machine-owned)` section of the active `task_plan.md`.
Use the planning plugin's active-plan resolution semantics, but bind the
parent-resolved absolute plan path to `session_id`; do not rediscover the plan
from a worktree subagent's cwd. Premise L5 makes this necessary: the only real
plan is in the primary checkout.

The registry should be append-only JSON Lines inside a fenced block. Appending
events is safer than rewriting a mutable table when multiple lanes overlap.
Each event has `schema_version: 1` and these minimum fields:

```json
{"event":"dispatch","dispatch_id":"toolu_...","session_id":"...","prompt_id":"...","agent_type":"codex-advisor","description":"Review the enforcement design","brief_path":".agent/plans/codex-lane-toolu_....md","brief_sha256":"..."}
{"event":"start","agent_id":"agent-...","agent_type":"codex-advisor","session_id":"..."}
{"event":"launched","dispatch_id":"toolu_...","agent_id":"agent-...","status":"async_launched"}
{"event":"stop","agent_id":"agent-...","outcome":"reported","report_path":"docs/research/kb/reports/agents/...md","report_sha256":"..."}
```

The exact dispatch prompt is persisted before launch to the standard
`.agent/plans/` area; the plan record carries a bounded human description plus a
path and digest. A dead lane therefore leaves both its assignment and its plan
index entry. A report path is required only at the terminal event because it
does not exist at dispatch.

### Runtime invariants

1. **Reserve before launch.** On `PreToolUse(Agent)`, when `subagent_type`
   identifies a `codex-*` wrapper, persist the exact brief and append `dispatch`.
   Return a deny if either write cannot be verified. This is before the subagent
   sees its prompt.
2. **Bind the runtime identity.** `SubagentStart` appends `start` using the
   vendor-provided `agent_id`; `PostToolUse(Agent)` joins the original
   `tool_use_id` to `tool_response.agentId` and appends `launched`. A foreground
   lane still has its pre-dispatch row even though `PostToolUse` arrives later.
3. **Deny unregistered work.** Any tool hook whose `agent_type` is `codex-*`
   checks that a matching `start` or pending dispatch exists. This protects the
   interval after `SubagentStart`, which itself cannot block. It also avoids
   parsing the inner `codex exec` shell string.
4. **Close, do not erase.** `SubagentStop` appends a terminal event and can block
   stop until the declared report path exists. Never delete the dispatch event;
   a failed/died lane is itself plan state.
5. **Reconcile at parent boundaries.** Parent `Stop`, handoff, and ship checks
   fail locally when a dispatch lacks a runtime or terminal event. They report
   the exact IDs instead of guessing what happened.
6. **Cover the canonical non-wrapper lane.** Extend the existing
   `mise run codex-lane` Python producer to append the same event schema. Do not
   create a second shell-string detector. Direct raw `codex exec` from the main
   conversation remains a named bypass and should be redirected to a canonical
   task if this requirement is adopted.

### What a machine can and cannot assert

The checker can assert all of the following without semantic judgment:

- a unique dispatch event exists for each observed canonical launch;
- the referenced brief exists and matches its recorded digest;
- the runtime `agent_id` is bound to one dispatch;
- the lane has a terminal event and its declared report exists;
- no duplicate or impossible lifecycle transition exists.

It **cannot** assert that the description is truthful, the prompt includes
everything the lane later considered, the report is accurate, the report is current,
or work launched outside the observed harness was recorded. A row-existence
gate proves the row and referenced bytes exist. Calling that "all work is
accurately in the plan" would be security theatre.

### R1 options

1. **Dispatch reservation + lifecycle reconciliation (recommended).**  
   **PRO:** It acts before work begins, survives a lane dying, uses vendor IDs,
   and records both successes and failures. It reuses the current Python hook,
   canonical mise-task, selfcheck, and suites contract patterns.  
   **CON:** It adds synchronized writes to a large machine-local plan and remains
   bypassable with hooks disabled, a hook crash, raw CLI use outside the harness,
   or edits to its own project-controlled checker.

2. **SubagentStop/report-only registration.**  
   **PRO:** The final message and report path are available, so the record can be
   richer and simpler to join.  
   **CON:** It exactly misses the motivating failure: a lane that dies before
   reporting leaves no record.

3. **Planning-plugin ledger only.**  
   **PRO:** Existing, append-only, per-agent, and concurrency-aware.  
   **CON:** It does not put work in `task_plan.md`, its event schema has no
   dispatch identity, and its Stop gate intentionally degrades to allow. It does
   not satisfy R1 without an adapter and plan projection.

**Risk that decides the recommendation:** the only irreversible loss window is
before a report exists. Therefore the first durable write must occur at
dispatch, not completion.

## R2 design — explicit declarations plus an operator-prompt queue

### The literal guarantee is impossible

The existing rule and validator both state the mechanism limit correctly:
"What no hook can see is an ask that never happened"
(`.claude/rules/clarify-before-acting.md:68-93`; also
`python/src/dotfiles_setup/ask_quality.py:8-41`). A diff classifier, LLM hook, or
keyword scan can guess that a question may exist, but cannot deterministically
prove a missing semantic dependency. Making such a detector blocking would
automate false assurance.

An explicit `none` is checkable only as a statement: a machine can prove the
agent emitted `none` at a named boundary. It cannot prove the statement is true.
That is still useful as a forcing function and audit trail, provided the report
never calls it detection or completeness.

### The artifact

Create one append-only `operator-prompts.jsonl` beside the resolved active
`task_plan.md` (root mode: `./operator-prompts.jsonl`; scoped mode:
`.planning/<plan-id>/operator-prompts.jsonl`). It shares the plan's lifetime and
resolver; it is not a tracked policy artifact or a substitute for the tool UI.

Each `open` event contains:

- a stable prompt ID and status;
- origin: `session_id`, optional `agent_id`, report path and citation;
- boundary: `immediate`, `turn`, `handoff`, or `ship`;
- the exact `questions` array accepted by `AskUserQuestion`;
- created/surfaced/resolved event links, never in-place deletion.

The stored question must reuse the existing project shape exactly: recommendation
first, one `(Recommended)` label, `PRO:` and `CON:` for every option, and a
citation or `[no prior evidence]`. Feed that stored `questions` array through
`ask_quality.find_violations`; do not create a parallel prompt validator.

The operator consumes the artifact only through the real `AskUserQuestion`
tool. The vendor documents it as the decision/clarification surface, with
free-form input through `Other`, and says questions remain open until answered
by default (`$CC/tools-reference.md:125-137`). A file entry alone is **queued**,
not surfaced.

### Boundary protocol

1. **Lane boundary.** Every findings-bearing subagent report must end with a
   machine-parseable operator-input declaration: either exact prompt objects or
   explicit `none`, plus origin citations. `SubagentStop` checks only that the
   declaration exists and is well-shaped. It does not certify `none` as true.
   Subagents cannot call `AskUserQuestion` at all; the vendor removes it from
   every non-fork subagent (`$CC/sub-agents.md:372-381`). The parent therefore
   imports any prompts to the queue.
2. **Parent turn boundary.** A project `Stop` hook requires a fresh declaration
   for the current `prompt_id`: prompt IDs to surface, or explicit `none`. If the
   queue has unsurfaced `immediate`/`turn` entries, stop is blocked with the exact
   IDs and the agent must call `AskUserQuestion`.
3. **Successful ask.** `PreToolUse(AskUserQuestion)` continues to enforce shape.
   A `PostToolUse(AskUserQuestion)` hook appends `surfaced`, linking the tool-use
   ID to the queue ID. Resolution is appended after the answer is returned.
4. **Handoff and ship.** The relevant mise-task gates require: no unsurfaced
   blocking prompt; every answered/withdrawn prompt has a terminal event; and a
   fresh explicit declaration after the last plan/report change. These gates
   check bookkeeping, not whether the agent noticed every question.
5. **Audit the escape.** Count and display explicit-`none` declarations in the
   session audit. A constant stream of `none` with later reconstructed questions
   is evidence that the forcing function has become a rubber stamp, not a reason
   to call it green.

Claude Code's Stop hook can ask the model to continue, but it is not absolute:
the harness overrides it after eight consecutive blocks
(`$CC/hooks.md:2436-2442`, `:2498-2517`). That bound must appear in the
implementation's wording and tests; "cannot stop" would be false.

### R2 options

1. **Boundary declaration + exact prompt queue + real AskUserQuestion
   (recommended).**  
   **PRO:** It converts every *recognized* need into a durable, validated,
   operator-actionable prompt; it catches buried prose and gives later audits a
   falsifiable `none`. It reuses `ask_quality.py` and natural hook/task
   boundaries.  
   **CON:** An agent can rubber-stamp `none`; local hooks can fail open or be
   disabled; the eight-block host cap eventually permits stop.

2. **Heuristic "unasked question" detector over prose/diffs.**  
   **PRO:** It may flag suspicious words such as "decision", "blocked", or
   "your call" before a turn ends.  
   **CON:** It cannot distinguish a resolved fact from a needed answer, can be
   evaded by phrasing, and would falsely advertise semantic detection. Advisory
   lint is acceptable; enforcement is security theatre.

3. **Prose rule plus existing ask-quality gate only.**  
   **PRO:** No new state or lifecycle integration.  
   **CON:** This is the current system, and the motivating failure occurred
   under it. It validates only attempted asks and provides no queue, explicit
   none, or boundary reconciliation.

**Risk that decides the recommendation:** a false claim that missing questions
are detected is worse than an explicit, auditable forcing function that admits
its semantic blind spot.

## Layer placement and concrete bypasses

| Layer | R1 role | R2 role | Concrete bypass / limit |
|---|---|---|---|
| Rule prose | Defines what counts as a codex lane and forbids unregistered raw launches | Requires declarations and immediate use of the queue | Omitted from a brief, ignored by the model, or decays from context; this failure is already recorded |
| Pre/PostToolUse + SubagentStart/Stop + Stop hooks | Reserve, bind, and close lane records | Validate stored/live prompt shape; require boundary declaration; record surfaced prompts | Project-controlled and local; `disableAllHooks`, another harness, raw terminal use, editing settings/checker, or a hook crash. This repo also records the existing PreToolUse wrapper as fail-open (`.claude/rules/mise-tasks-only.md:55-75`) |
| Mise task gate | Canonical `codex-lane` producer writes the same schema; handoff/ship reconcile | Handoff/ship reject unsurfaced blocking queue entries | Direct `git`, `gh`, API, or raw `codex exec` bypasses the task; local agent can edit it |
| hk step | Lints tracked implementation and tests; no live-plan authority | Same; may lint tracked report declaration shapes | `--no-verify`, another client, and—decisively—`task_plan.md`/queue are gitignored and absent in CI/staging |
| `suites.toml` contract | Asserts settings → dispatcher/module → task → selfcheck → tests remains wired | Extends `workflow.ask-quality-enforcement` to the queue/boundary chain | Static tokens can be satisfied by dead code or stand-ins unless each production call site and failing arm is bound; it proves wiring exists, not runtime use |
| CI | Verifies the tracked mechanism and control arms | Verifies tracked mechanism only | Cannot read the primary checkout's machine-local plan or queue and arrives after the live interaction. It cannot enforce either standing runtime guarantee |

The advisor report's trust-layer conclusion carries over: local hooks and tasks
are useful feedback/enforcement inside one cooperative harness, but code and
configuration controlled by the same agent are advisory in an adversarial
sense (`$SCRATCH/advisor-report.md:81-150`). Independent server recomputation
works for commit-bound facts; it cannot help here because the authoritative plan
and prompt queue are deliberately machine-local.

## Verification design for a later implementation

No implementation is part of this report. A future change should, at minimum:

- extend the real wrapper/selfcheck with passing and failing arms for
  `PreToolUse(Agent)`, `PostToolUse(Agent)`, `SubagentStart`, `SubagentStop`, and
  `Stop`, including a foreign cwd/worktree whose local tree has no plan;
- mutation-test that deleting the dispatch write allows no codex wrapper to
  start, and that a dead lane still leaves its exact brief and dispatch event;
- test duplicate parallel `codex-*` types under one `prompt_id` so correlation
  does not rely on type or prompt ID alone;
- prove `explicit_none` is fresh per current `prompt_id`, while an existing open
  queue entry prevents it from satisfying the boundary;
- drive a compliant stored question through the existing
  `ask_quality.find_violations`, and prove one missing `CON:` or citation fails;
- add a suites contract that binds settings event names, Python entrypoints,
  canonical mise-task call sites, selfcheck arms, and the rule text. Do not use a
  bare union token where `per_path_tokens` is required.

## What could not be settled

- **UNVERIFIED:** The offline hooks reference documents `PostToolUse` as carrying
  the tool response and documents the AskUserQuestion input/answer shape, but I
  did not find an explicit hook-reference schema for the interactive
  `PostToolUse(AskUserQuestion).tool_response`. A live two-option probe through
  the wired hook, including an `Other` answer, is required before automatic
  answer capture is designed. Until then, append resolution from the parent
  turn, not from a guessed response field.
- **UNVERIFIED:** Atomic cross-process insertion into this session's 854-line
  root `task_plan.md` under overlapping parent/subagent hooks. The planning
  plugin's JSONL ledger uses an advisory lock, but the operator requires a
  projection into `task_plan.md`; implementation needs a real concurrent-write
  arm on macOS before claiming durability.
- **UNVERIFIED:** Whether every non-Agent codex launch in the operator's actual
  workflow already passes through `mise run codex-lane`. The four current
  `codex-*` wrappers visibly invoke `codex exec` directly (for example,
  `.claude/agents/codex-advisor.md:68-91`), so a canonical-task-only design is
  insufficient today.
- Graphify was unavailable in this isolated worktree. With mise and uv caches
  redirected to `/private/tmp`, `mise run graphify-health` reached the repo task
  and reported missing `graphify-out/graph.json` (rc=3). Per the graphify rule,
  source files—not an empty graph result—were the authority.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — rules,
  settings, Python hook/validator code, verification contracts, plan snapshots,
  and codex wrapper definitions under design.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) —
  host of the offline vendor-doc snapshot used to settle all harness claims.
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — vendor
  documentation for subagents, hooks, settings, and AskUserQuestion behavior.
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) —
  installed 3.12.0 plugin source inspected for its resolver, ledger,
  attestation, and Stop-gate semantics.
