**Keep the 30% threshold. Implement a checked state capsule first, durable coordinator routing second, and an advisory scheduler third.** Generalize lane handoff after ownership transfer is explicit.

All three specialists finished. This review made no checkout changes, wrote no report, and ran no repository gates. External research coverage is **partial**, with failures recorded below.

The final reviewed base is **`ad4dbc62bce8989928210007e4487f84109e1cfe`**, containing #1658 and #1667. `origin/main` advanced during review; specialists reconciled affected evidence against that commit. The checkout remains at `13af2848`, with the same pre-existing session-start ledger changes. That separate fix was neither redesigned nor modified.

Repository module citations below refer to `python/src/dotfiles_setup/` at the reviewed commit.

## Q1 — Handoff fidelity

**Verdict: the missing guarantee is completeness across a recorded source boundary. Better prose alone cannot provide it.**

| Finding and evidence | Concrete proposal | Control arm |
|---|---|---|
| Handoff prose became stale after creation: a later human instruction, finished premise reports, and a newly started ship were omitted. [04g audit:9](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-04h/docs/research/kb/reports/agents/handoff-audit-2026-10-04g.md:9). Launch reads the handoff once; `coordinator_handoff.py:780–784,918–927`. | Record source cursors and reconcile subsequent events during takeover. | Append a human turn, final handback, and ship start after collection. The original capsule must become stale; refresh must preserve all three. |
| The existing checker validates citations, task names, attestation, and recognizable PR claims; it explicitly cannot prove completeness. `handoff_check.py:4–12,637–670`. | Add obligation coverage validation alongside the existing checker. | Omit an early unanswered request while retaining valid citations and PR facts. The new validator must fail. |
| Final reports can reside in `SubagentHandback.input.message`, including a report without assistant text blocks. Audit:89–97. | Parse actual handback records and preserve final payloads verbatim. | Progress prose followed by a final tool-carried report must yield the final report. Reverting to “last assistant text” must fail. |
| Retirement checks recorded processes, adoption, and in-flight tasks, rather than unconsumed instructions or reports. `coordinator_handoff.py:1084–1137`. | Couple takeover readiness to captured obligations and pending ingress. | All recorded processes finish, but a late human request remains. Transfer must preserve it and refuse a claim of complete reconciliation. |

The proposed **handoff capsule** should contain:

- Repository/worktree identity, full HEAD, working-tree fingerprint, observed base, and capture time.
- Stable lane ID, role, session UUID, ownership, permissions, and predecessor/successor relationship.
- Each source’s identity, record/byte cursor, digest, and observation time.
- Human requests, rulings, reports, and unfinished tasks with IDs, source references, and explicit dispositions: applied, pending, blocked, or superseded with evidence.
- Run records and terminal evidence.
- Pending events arriving after the captured boundary.

Readiness must detect changed or replaced sources. Later arrivals must remain durable for the successor; waiting for a permanently quiet inbox could prevent takeover indefinitely.

**Reuse `session-state`, but do not treat it as a complete ledger.** `session_state.gather()` provides branch, dirty paths, recent commits, PR summaries, query window, and truncation information (`session_state.py:87–106,378–428`). Its current CLI renders Markdown and has no JSON option (`:516–600`). It does not inventory obligations, handbacks, coordinator ownership, locks, or terminal run provenance.

Unavailable GitHub state must remain unavailable. **Control:** successful Git reads combined with failed GitHub reads must not become an apparently successful empty PR list.

**Run outcomes need stronger provenance.** `HeavyRun` records PID, argv, and log path (`coordinator_handoff.py:455–460`). `GateResult` lacks run ID, revision/fingerprint, and start/finish timestamps; its latest file is overwritten (`gate_result.py:43–52,127–164`). Preserve legacy receipts as observed evidence, without treating them as proof that another revision passed.

Required controls:

- Process exits without a terminal receipt → `UNKNOWN`.
- Green receipt belongs to another SHA → cannot authorize shipping.
- Reused PID with a different start identity → different process.
- Wrapper exits zero while child evidence reports failure → failure remains visible.

**Prose remains necessary** for rationale, ambiguity, tradeoffs, rejected approaches, and unresolved questions. Preserve literal human instructions and the required independent audit. Machine validation can establish recorded coverage and provenance; it cannot prove correct interpretation.

## Q2 — Messaging without takeover broadcasts

**Verdict: use stable role bindings over the existing durable inbox, with native messaging as a wake-up signal.**

Existing inbox writes already use bounded locking and atomic replacement: `handoff_inbox.py:240–278`. Native messaging addresses concrete sessions and can hold, refuse, expire, or drop messages; it does not establish durable application of their contents. [Primary messaging documentation](https://code.claude.com/docs/en/cross-session-messaging).

Proposed interfaces:

| Record | Required fields |
|---|---|
| `RoleBinding` | Repository, role, epoch, session UUID, native address, phase, predecessor, capsule ID, readiness receipt |
| `LaneEvent` | Message ID, lane ID, producer, kind, timestamp, payload reference, observed epoch |
| `AppliedReceipt` | Message ID, consumer epoch, effect reference, outcome including `UNKNOWN_RECONCILE` |

The transfer sequence should be:

1. Persist events before attempting native notification.
2. Start a candidate without granting mutation authority.
3. Validate its role definition, capsule, audit, and captured inbox boundary.
4. Promote through compare-and-swap of the active epoch.
5. Admit successor planning/ship actions, apply audited corrections, publish readiness, and drain pending events.
6. Retire the predecessor through existing settlement/adoption checks.

**Writer admission must change with routing.** Current admission uses the newest coordinator job’s creation time (`handoff_inbox.py:174–203`). A candidate can therefore displace its predecessor before readiness. A registry alone would leave routing and authorization inconsistent.

**Control:** before promotion, predecessor A’s sanctioned planning write succeeds and candidate B’s fails; afterward, the results reverse. Restoring creation-time election must fail this test.

Other required controls:

- Native delivery fails during swap; the successor still discovers the durable event.
- Duplicate message ID produces one applied disposition.
- Competing promotions cannot both acquire the active epoch.
- Crash after a GitHub effect but before acknowledgement produces reconciliation, rather than blind repetition.

Do not promise exactly-once distributed effects or power-loss durability merely from atomic replacement.

**Contract amendment required:** current requirements and generated briefs mandate every-lane announcements and concrete coordinator naming (`requirements.md:22–33`; `coordinator_handoff.py:690–706`). The new specification authorizes reviewing a replacement; implementation must explicitly amend those duties while preserving audit, reachability, and safe retirement.

## Q3 — Role decomposition and scheduling

**Verdict: separate judgment from execution. Keep one designated shipper per repository.**

| Role | Native shape | Typed input/output | Authority and context survival |
|---|---|---|---|
| Ship/land scheduler | Independent constrained `claude --agent … --bg` session; Python/mise admission and ordering | Reconciled queue, dependencies, holds, blast-radius evidence, revisions, CI and resource state → versioned schedule with eligibility and reasons | Own schedule state only. Existing designated operator executes `ship`/`land`. Reconstruct at its own 30% takeover. |
| Work decomposer | Short-lived read-only subagent; native workflow for suitable bounded batches | Spec, premises, ownership, dependencies → small seven-part task specs | Returns proposed plan edits. Coordinator remains sole `task_plan.md` writer. Prefer finishing bounded work over maintaining another permanent session. |
| Lane context steward | Each managed lane’s context hook plus generalized handoff task; independent background steward where needed | Registration, context measurement, capsule, ownership and live work → successor reservation/readiness | No worker-branch or shipping mutations. Successor acquires explicitly transferred ownership. |

Independent agent-backed background sessions are documented native functionality. [Agent-view documentation](https://code.claude.com/docs/en/agent-view). Workflows and scheduled wake-ups do not replace durable role state: workflow replay is session-bound, and scheduled tasks have session scope and expiry. [Scheduled-task documentation](https://code.claude.com/docs/en/scheduled-tasks).

A missing original agent definition can resume with default tools. **Control:** remove or change the constrained definition between sessions; admission must refuse work instead of silently accepting broader tools. [Session documentation](https://code.claude.com/docs/en/sessions).

Current coordinator write guards cover selected editing tools and leave Bash writes outside their scope; see `coordinator_write_guard.py:19,36–81` and coordinator-handoff `SKILL.md:74–81`. Enforce active-epoch admission through sanctioned planning and shipping interfaces without claiming universal shell-write protection.

### Priority model

Apply deterministic admission before ranking:

1. Exclude explicit holds, unresolved prerequisites, ownership conflicts, missing reviews, and unsafe or unknown operation identity.
2. Preserve hard ordering rulings.
3. Give old **eligible** work a finite bypass limit, persisted across scheduler replacements.
4. Otherwise favor blocker release, critical-path progress, and tasks that release a lane quickly.
5. Use blast radius to estimate conflict and validation cost. Broad impact alone does not justify priority.
6. Use measured durations when available; unknown duration must not behave like zero.
7. Record factors and evidence with every decision.

Reuse existing Graphify and parallel-work-split seams (`parallel-work-split/SKILL.md:28–39,62–83`). No graph task ran in this review, so current graph freshness and actual scheduling gains remain unmeasured.

**Controls:** dependency cycles remain blocked; age cannot override an explicit hold; continual small arrivals cannot starve old eligible work; stale Graphify data cannot become “zero dependencies.”

### Licensed dissent: push overlap conflicts with current rules

The literal proposal to push PR N while PR N−1 owns the heavy local slot conflicts with present enforcement:

- `pr.py:671–707` holds the slot across gates **and push**.
- `mise.toml:310–314` runs the pre-push suite through that lock.
- `suites.toml:3158–3172` pins the wiring.
- Coordinator-handoff `SKILL.md:57–60` nevertheless says to push while another ship owns the slot.

**Stop that push-now path and correct the contradictory prose.** Compatible pipelining is:

```text
local gates + push + arm auto-merge(A)
                    ├── remote CI(A)
                    └── next admitted local gates + push(B)
```

Remote CI overlaps the next local operation after slot release. Coding, bounded reviews, decomposition, and read-only metadata inspection can also overlap. Dependent work still waits for required merge/land state.

Use canonical shipping and native auto-merge; GitHub already waits for required reviews/checks. [GitHub auto-merge documentation](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/automatically-merging-a-pull-request).

**Control:** two public shipping operations share an isolated lock; B cannot start its pre-push suite while A holds it. A failing pre-push must never open/arm that PR.

### Host-load boundary

The host lock coordinates host clones/worktrees, but explicitly excludes container home-volume locks despite shared CPU (`host_lock.py:30–32`). Scheduler admission must account for container heavy work; the existing lock alone does not enforce that boundary.

**Control:** a container heavy operation is refused while the host slot is occupied. Two host-worktree fixtures alone do not exercise this gap.

No increased heavy-run count or second shipper is proposed. Continuous useful CI depends on eligible work and dependencies; it cannot be guaranteed by weakening local validation.

## Q4 — Lane handoff at 30%

**Verdict: generalize explicit managed-lane admission, rather than making every lane a coordinator.**

Current decision, launch, and retirement reject noncoordinators (`coordinator_handoff.py:341–352,798–814,1094–1100`). The hook caches that classification (`register.ts:227–251`). Merely setting the percentage variable does not enroll a lane.

Measurements occur after main-thread turns, with execution queued until idle (`claude-code.d.ts:3594–3604,2624–2629`). The supported promise is **submission at the first observed eligible measurement ≥30%**, rather than an exact mid-turn interruption. Ordinary subagents should remain bounded; independent sessions provide the appropriate lane shape.

Register stable lane ID, role, session UUID, repository/worktree, ownership, spec, and successor policy. Preserve 30%, the existing +5% retry step, duplicate-launch protection, and retirement/adoption checks.

Successors must inherit:

- Exact spec, literal rulings, outstanding obligations and questions.
- Owned files, worktree, branch/HEAD/base, and dirty/untracked work.
- Review/gate evidence with revision provenance and unresolved failures.
- Pending events and applied boundary.
- Child/run identities, logs, terminal evidence, and adoption status.
- Dependency state, resource grants, and mutation restrictions.

The predecessor must relinquish implementation ownership before successor writes.

`dag_tick.execute_respawn()` currently lacks handoff-supersession checking (`dag_tick.py:1240–1271`). **Control:** a superseded predecessor remains retired while an unrelated genuinely dead lane remains recoverable.

Additional controls: 29.9% does not fire; 30% fires once; repeated measurements do not duplicate launch; unregistered sessions remain ineligible; failed delivery retries correctly; failed readiness never permits concurrent writers.

## Q5 — Other workflow and token improvements

**Verdict: reduce repeated discovery and intermediate-result carriage while retaining coordinator accountability.**

- **Reconcile before archiving.** Newer queue obligations occur below HISTORY, including lines 441, 474, and 493. Keeping only the first CURRENT block loses authoritative state. **Control:** a later pending obligation survives the active projection.
- **Return bounded decision briefs:** verdict, changed facts, blockers, evidence, next action. Complete backing reports remain available. **Control:** an early unanswered instruction remains discoverable even when omitted from the brief.
- **Preserve exception-only watcher behavior.** `WATCHER.md:19–30` excludes intentional holds and rate-limits unchanged blockers. **Control:** unchanged SLOT holds remain quiet; new permission blocks and merges surface.
- **Normalize the plan before native smart extraction.** The prior review found historical content inside active sections still saturated injection limits. Preserve archival accounting and the regression guard. **Control:** genuine checkbox loss still warns after archival.
- **Keep coordinator reading focused.** It must read human instructions, rulings, and decision evidence. A literal “no reading” coordinator would repeat the audit’s lost-instruction failure. **Control:** input arriving after capsule collection remains an outstanding obligation.

The prior review observed 16 takeover announcements; removing repeated discovery and acknowledgement cycles is a plausible saving. Exact token and latency savings remain unmeasured. The canonical session-start ledger fix remains separate, and the withdrawn threshold increase is excluded.

## Q6 — Ranking and seven-part implementation outlines

| Rank | Change | Tokens/latency and trust benefit per risk |
|---|---|---|
| 1 | Checked state capsule | Strongest trust benefit; prevents stale-result reruns and repeated reconstruction. Main risk: incomplete source coverage. |
| 2 | Durable role routing and inbox processing | Clearest reduction in takeover broadcasts and acknowledgements. Main risk: inconsistent writer ownership during promotion. |
| 3 | Advisory scheduler with deterministic admission | Removes scheduling burden and improves permitted CI overlap. Main risk: stale authorization or a second shipper. |
| 4 | Managed-lane 30% handoff | Bounds lane contexts after reliable transfer exists. Main risk: concurrent ownership and incorrect respawn. |
| 5 | Plan/queue normalization and bounded native workflows | Reduces recurring context carriage. Main risk: lost obligations or assumed cross-session replay. |

These are qualitative rankings, not measured savings.

### PR 1 — Checked handoff capsule

1. **Objective:** verify factual provenance and obligation coverage through a declared source boundary, preserving later pending input.
2. **Files:** new `schemas/handoff-capsule.schema.json`, `python/src/dotfiles_setup/generated/handoff_capsule.py`, `python/src/dotfiles_setup/handoff_capsule.py`, `tests/test_handoff_capsule.py`; existing `main.py`, `session_state.py`, `handoff_check.py`, `coordinator_handoff.py`, `python/pyproject.toml`, `mise.toml`, `python/verification/suites.toml`, and mirrored coordinator-handoff instructions.
3. **Interfaces:** `handoff-state collect`; read-only `handoff-state check`. Proposed rc: 0 valid for declared boundary; 1 stale/incomplete; 2 malformed/unreadable. Reuse `gather()` and `check_with_claims()`. Validity grants no shipping authority.
4. **Constraints:** schema-generated models and codec; Python logic; standard `.agent/` paths; bounded reads with explicit overflow; unchanged 30%; preserve audit, ownership, and unknown outcomes. Exclude session-start ledger changes.
5. **Verification:** future public-CLI tests against isolated real repositories/worktrees and fixture transcripts/inboxes. Cover late input, tool-carried finals, missing obligations, replaced sources, unavailable/truncated PR state, and stale receipts. Reverting coverage or provenance checks must fail realistic assertions.
6. **Commit:** caller; separate PR.
7. **PREMISES:** **L:** launch reads prose once (`coordinator_handoff.py:780–784`). **I:** existing gather/check interfaces (`session_state.py:378`; `handoff_check.py:637`). **P:** bounded locks/atomic replacement (`session_common.py:104–152`). **E:** source cursors and evidence references come from inspected records; bounded rendering explicitly reports overflow; no environment secrets emitted. **A:** semantic interpretation and exact savings remain unproven.

### PR 2 — Durable coordinator identity and inbox

1. **Objective:** replace takeover broadcast/ack cycles while preserving every lane’s reachability and pending reports.
2. **Files:** new role-state schema, generated model, `python/src/dotfiles_setup/role_state.py`, and tests; existing `session_common.py`, `handoff_inbox.py`, `coordinator_handoff.py`, their tests, `main.py`, `mise.toml`, verification wiring, requirements, and mirrored skills.
3. **Interfaces:** `role resolve`, `candidate-ready`, `promote --expected-epoch`, and event append/read/ack/reconcile operations using the Q2 records.
4. **Constraints:** shared promotion boundary for routing and writer admission; preparing candidates cannot mutate; legacy inbox migration; native wake optional; preserve audit/retirement and designated shipper.
5. **Verification:** isolated public-interface tests for competing promotion, candidate failure, stale writers, notification refusal, events spanning swap, duplicate IDs, and crash-after-effect reconciliation. Removing persistence or epoch admission must fail the corresponding controls.
6. **Commit:** caller; separate PR dependent on capsule readiness.
7. **PREMISES:** **L:** election currently follows creation time (`handoff_inbox.py:174–203`). **I:** sanctioned locked writer (`:240–278`). **P:** existing durable fallback. **E:** binding/event receipts derive from admitted identities and source references, with bounded payloads. **A:** installed delivery/adoption behavior needs controlled integration proof; exactly-once external effects are not assumed.

### PR 3 — Advisory ship/land scheduler

1. **Objective:** produce a trustworthy next-operation proposal outside coordinator context while preserving local validation and resource rules.
2. **Files:** new scheduling schema/model, `python/src/dotfiles_setup/ship_scheduler.py`, `tests/test_ship_scheduler.py`, `tests/test_ship_scheduler_cli.py`, constrained `.claude/agents/ship-scheduler.md`, and scheduler skill/mirror; existing `main.py`, `mise.toml`, verification wiring, and the contradictory coordinator-handoff instruction. Reuse existing `pr.py` and `host_lock.py` execution seams.
3. **Interfaces:** read-only `schedule inspect --json` with explicit input roots and deterministic clock; emits observation revision, eligible/blocked candidates, reasons, and proposed operation. Designated operator rechecks revision, prerequisites, ownership, and lock before canonical execution.
4. **Constraints:** advisory scheduler; no direct merge path or receipt-based validation bypass; holds outrank age; finite bypass limit; fresh Graphify or explicit fallback; container heavy work excluded from simultaneous admission. Bounded decomposition returns specs and proposed edits only.
5. **Verification:** future public-interface tests for cycles, held blockers, starvation, unknown durations, stale observations, failing pre-push, competing host requests, container admission, missing role definitions, and reconstruction after rotation. Removing each admission/fairness guard must fail its realistic control.
6. **Commit:** caller; separate PR. Actual automated execution and expanded container locking require their own reviewed scope.
7. **PREMISES:** **L:** gates/push share the lock (`pr.py:671–707`; `mise.toml:310–314`). **I:** native agent-backed background sessions and canonical ship/land. **P:** existing blast-radius/dependency workflow. **E:** schedule reasons derive from pinned observations and explicitly carry unknowns. **A:** queue estimates, graph freshness, host-load measurements, and actual savings require measurement.

All verification above is proposed implementation work. **None ran during this review.**

## Execution and research receipt

| Specialist | Ownership | Normal gate | Review result |
|---|---|---|---|
| Python | State, capsule, lifecycle and lane transfer | pytest | **NOT RUN; no exit code** |
| Configuration | Hooks, addressing, admission and resource boundaries | `mise run lint` | **NOT RUN; no exit code** |
| Documentation | Scheduling, workflow policy, ranking and external research | `mise run lint-docs` | **NOT RUN; no exit code** |

**Overall:** review completed with blocking findings; external research coverage partially failed. No green gate verdict is claimed.

External processes used native `fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults --no-daemon --non-interactive exec`. Secrets were neither printed nor persisted.

| Route | Actual execution and result |
|---|---|
| Exa | HTTPS Search/Contents APIs: **HTTP 200**; primary documentation retrieved |
| Firecrawl | HTTPS v2 Search API: **HTTP 402**, insufficient credits |
| Context7 | `ctx7 library` and `ctx7 docs`: **rc 0** |
| Last30Days | Engine `--help`: **rc 0** only. Full retrieval blocked because installed engine writes run/cache files; no no-write-safe full route established |
| GitHub | Repository/code searches and README metadata: **rc 0**. Positive `npm` search returned files; fresh absent control returned none. Earlier empty title query was not trusted |
| Direct official `.md` fetches | **HTTP 403** on three pages; Exa Contents supplied fallback |

**RESEARCH INCOMPLETE:** no strict-five receipt was produced. Last30Days capability discovery does not count as completed research. Installed harness lifecycle behavior was not exercised.

Actual tools included Git, `rg`, `cat`, Python, uv source extraction, fnox, ctx7, gh, and collaboration tools. Applied skills included codex-sdlc-team, coordinator-handoff, pr-workflow, parallel-work-split, Exa search, Firecrawl search, Last30Days guidance, and Context7 guidance. No connector app or provider MCP server ran.

One configuration source-read command returned **rc 1** after nested `git show` returned **128** for a nonexistent rule path; a **rc 0** tree lookup recovered it, and no finding relies on that path. Truncated reads were followed by bounded rereads.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): local source, tests, documents, state and commit comparisons.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): offline harness documentation.
- [mrkhachaturov/agent-harness-docs](https://github.com/mrkhachaturov/agent-harness-docs): mirrored vendor documentation.
- [anthropics/claude-code](https://github.com/anthropics/claude-code): read-only repository/code search and README metadata.
- [anthropics/claude-code-action](https://github.com/anthropics/claude-code-action) and [anthropics/claude-code-security-review](https://github.com/anthropics/claude-code-security-review): search results only; code not reviewed.

No GitHub mutations occurred. No other specialists were spawned.

### Specialists spawned:

- `sdlc-python-specialist` — `/root/python_review`
- `sdlc-config-specialist` — `/root/config_review`
- `sdlc-documentation-specialist` — `/root/documentation_review`

