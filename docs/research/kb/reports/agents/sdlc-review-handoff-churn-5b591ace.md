The highest-priority fix is **sharing the session-start ledger across worktrees**. The same coordinator UUID was initialized in two checkouts, permitting repeated forced reloads. Those reloads precede the transcript’s largest observed input increase: **62,811 tokens**.

Review completed at `13af28480ae4d07e718494b696b44c9c5dcb104c`. The checkout remained clean. No edits, report files, commits, or repository gates were produced. External research coverage is **partial**, with the failed and blocked routes recorded below.

## Q1 — What actually consumes context?

The motivating “64 KB per incoming message” diagnosis is contradicted by the supplied transcript. Long hook output was persisted and represented by a short preview.

Measurements from [the coordinator transcript](/Users/rmanaloto/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles--claude-worktrees-handoff-2026-10-04g/c769e1a1-f655-4771-b94f-a07abe6cf541.jsonl:38):

| Source | Measured amount | Evidence and interpretation |
|---|---:|---|
| Transcript storage | 2,831,682 bytes; 888 records | Includes metadata and repeated representations; not context tokens. |
| PWF prompt attachments | Six × 2,408 rendered bytes = **14,448 bytes** | JSONL lines 38, 169, 183, 185, 187, 189. |
| Persisted hook output | Seven × 66,703 bytes | Six prompt blobs plus startup; stored bytes are not automatically model input. |
| Initial instructions | 29 files; 168,538 rendered bytes | JSONL line 39. |
| Reloaded instructions | 28 files; 157,052 rendered bytes | JSONL line 538. |
| Skill listings | Four; 112,845 rendered bytes cumulatively | Not unique context or an isolated token attribution. |
| Cross-session queued attachments | Fourteen; 37,220 rendered bytes | May overlap subsequent user-message carriage. |
| User text | 30,284 bytes | Fifteen string records plus one text block; tool results counted separately. |
| Tool results | 113 blocks; 118,515 content bytes | Excludes some transcript metadata. |
| Takeover announcements | **Sixteen** `SendMessage` calls | JSONL lines 115–130. |

The supplied primary-doc mirror explicitly describes persisted output plus preview at [hooks.md:941](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/hooks.md:941) and line 1023.

**Control:** the same tool-input scan finds the actual ship-queue read at JSONL line 54 but no explicit read naming a persisted hook payload. This supports absence of a named blob read, rather than ruling out every conceivable indirect read. All seven blobs were recovered under the migrated transcript directory; their original paths had become stale.

### Recorded input growth

Deduplicating assistant blocks by `message.id` yields **78 API messages**, rather than 158 assistant records.

| Milestone | Input tokens, including cache fields |
|---|---:|
| First response, line 51 | 124,902 |
| Announcements complete, line 130 | 151,860 |
| Retirement milestone, line 205 | 168,147 |
| Before forced reload sequence, line 507 | 226,923 |
| After instruction reload, line 548 | 289,734 |
| First request above 300,000, line 563 | 301,416 |
| Final response, line 882 | 370,269 |

Between lines 507 and 548, the transcript records two `/reload-plugins --force` commands and `/reload-skills`, followed by instruction reinjection. Their origin is the `session-start` plugin. The second worktree entry occurs later, at line 607.

The **62,811-token increase is an observed association**, not an isolated measurement of instruction cost or guaranteed savings.

Cumulative root-message accounting was:

- Uncached input: 164.
- Cache creation: 341,365.
- Cache reads: 19,764,510.
- Output: 37,767.

Summing these input fields across requests repeatedly counts retained history. The transcript also records a broader `$17.239064` cost snapshot whose aggregation scope differs from the root-message totals; it cannot support source-specific cost attribution.

**Timing correction:** the handoff command was queued at JSONL line 575, **11:59:23 CDT**, approximately nine minutes after startup. The specification’s approximate 12:05 time is not the observed trigger time.

**Proposed change:** measure rendered attachments and deduplicated request usage separately. Do not rank fixes using persisted-file size as token cost.

## Q2 — What does 30% mean?

**Verdict:** it measures resident input against the model’s context window, including cached input. It is not elapsed time, spend, or cumulative token consumption.

The hook consumes `e.context.percent` unchanged when `changed` includes `context`: [register.ts:296](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-churn/.claude/skills/coordinator-handoff/hooks/register.ts:296). The contract defines input/cache accounting and freshness at [claude-code.d.ts:8781](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-churn/.claude/types/claude-code.d.ts:8781).

Read-only inspection of installed Claude **2.1.289** confirms rounded percentage calculation and recognition of `[1m]`. The transcript identifies `claude-opus-5-5[1m]`; its actual `session.measure.context.window` envelope was not retained.

Assuming the supported 1M denominator:

| Handoff threshold | Earliest input producing that rounded percentage | Headroom after the 168,147-token retirement milestone |
|---|---:|---:|
| 30% | 295,000 | 126,853 |
| 50% | 495,000 | 326,853 |
| 60% | 595,000 | 426,853 |

Raising to 50% provides 200,000 additional input tokens; 60% provides 300,000. **Neither saves context.**

The repository sets `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=33` at [settings.json:5](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-churn/.claude/settings.json:5). Installed source applies that percentage to an effective compaction window after output reservation. With a 1M window and 20K reserve, the calculated threshold is **323,400**, subject to runtime overrides.

Consequently, raising handoff to 50–60% alone risks native compaction occurring first. No actual compaction event was established in this transcript.

There is also **no takeover grace period**. A successor’s new UUID starts fresh; the trigger suppresses completed launches and permits a five-point retry after an unsuccessful fire. See [coordinator_handoff.py:282](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-churn/python/src/dotfiles_setup/coordinator_handoff.py:282).

**Recommendation:** remove repeat reloads first, then trial **50% together with a compatible compaction policy** and measured outgoing-handoff headroom. Thirty percent is currently conservative and close to the configured compaction threshold; the evidence does not establish it as an inherently correct value for every 1M coordinator.

**Controls inspected, not executed:** changed-context events versus rate-limit-only/missing-percentage events; first-fire state versus persisted fire and completed-launch state.

## Q3 — Can native PWF controls bound injection?

**Verdict:** native shape controls exist, but smart mode alone does not fix this plan.

Current primary source supports `PWF_INJECT=smart`; its byte limit remains hard-coded to 65,536. Autonomous/gated modes suppress pre-tool injection while retaining turn-start injection and changing other planning behavior. [Primary injection implementation](https://github.com/OthmanAdi/planning-with-files/blob/dab9d16fbd9314448b319d112e99f497d7638d89/scripts/inject-plan.py#L1095)

Read-only native extraction measured:

| Plan representation | Bytes |
|---|---:|
| Live plan | 253,162 |
| Ordinary first 50 lines | 2,860 |
| Native smart extraction before bounding | **75,679** |
| Bounded smart extraction | **65,536** |

Smart extraction retains whole Goal, Next Step and Current Phase sections. This plan embeds substantial historical phase material inside those sections. See [task_plan.md:3](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/task_plan.md:3) and [the native parser](https://github.com/OthmanAdi/planning-with-files/blob/dab9d16fbd9314448b319d112e99f497d7638d89/scripts/inject-plan.py#L693).

**Proposed change:** normalize the active headings, reconcile every unsettled obligation, archive completed/superseded material verbatim to tracked files, then use native smart mode.

Archiving also decreases completion counters and can trigger the plugin’s regression guard. Preserve accounting or explicitly reconcile the one-time archival warning through the native protocol; do not globally disable the guard. [Guard implementation](https://github.com/OthmanAdi/planning-with-files/blob/dab9d16fbd9314448b319d112e99f497d7638d89/scripts/inject-plan.py#L1185)

**Controls:** the source search finds implemented `PWF_INJECT`, mode and disable controls while the byte cap remains a constant. Genuine stale-writer checkbox loss must continue warning after archival.

**Identity limitation:** current primary source and cached **3.22.0** matched byte-for-byte. The transcript does not verify which PWF version was loaded; **3.20.4 remains the specification’s supplied premise**. Confirm loaded identity before applying its settings.

## Q4 — Can takeover be cheaper?

### Shared initialization state: confirmed defect

Session-start derives its default ledger from the loaded checkout: [main.py:3242](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-churn/python/src/dotfiles_setup/main.py:3242), [session_start.py:413](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-churn/python/src/dotfiles_setup/session_start.py:413).

The same UUID has separate `keep` records:

- Main checkout: 11:50:22.
- `coordinator-bgisolation`: 11:57:13.

An existing ledger suppresses reload; an empty checkout-local ledger grants another first-run reload. The existing tests exercise one injected state directory, rather than this migration axis.

**Change:** reuse [session_common.main_checkout](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-churn/python/src/dotfiles_setup/session_common.py:183) for the default state directory across `decide`, `pending`, and `renamed`.

### Smaller active queue: reconcile before archiving

The live queue is **90,833 bytes**. Its first CURRENT block is only 2,455 bytes, but newer authoritative updates appear beneath HISTORY at [queue:441](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/plans/main-checkout-ship-queue.md:441), lines 474 and 493.

**Licensed dissent:** keeping only the first CURRENT block would discard newer state. Stop that literal operation.

**Change:** construct one reconciled active queue, then archive superseded text verbatim. Retain outstanding handbacks, slot holds, live ownership, queued questions and evidence links. The observed initial combined read was already previewed, so an 88 KB disk reduction is not an established 88 KB context saving.

**Control:** a pending obligation appended after HISTORY must survive reconciliation.

### Broadcast and audit: preserve current requirements

Approved requirements mandate a successor audit subagent and announcement to **every lane**: [requirements:22](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-churn/docs/specs/coordinator-auto-handoff-2026-10-02-requirements.md:22). The generated successor brief repeats those duties at [coordinator_handoff.py:699](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-churn/python/src/dotfiles_setup/coordinator_handoff.py:699).

**Licensed dissent:** a registry pointer alone, or removal of the audit, conflicts with that contract.

**Change:** retain delivery to every intended lane and inbox fallback; avoid requesting unnecessary acknowledgements. A native broadcast remains conditional on verified delivery semantics. Bound the audit’s returned findings while preserving full obligation coverage; do not substitute a transcript tail.

**Controls:** an idle lane must receive the successor identity; an early unanswered request omitted from the handoff must be recovered by the audit.

Preserve mandated handoff worktree isolation and existing-worktree reuse: [handoff skill:45](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-churn/.claude/skills/coordinator-handoff/SKILL.md:45). Blanket suppression of behavior rules also conflicts with [md-size-budgets.md:111](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-churn/.claude/rules/md-size-budgets.md:111).

## Q5 — Ranked fixes

| Rank | Fix | Evidence-backed benefit | Principal risk |
|---|---|---|---|
| **1** | Canonical session-start ledger | Prevents repeat initialization; reload sequence is associated with +62,811 input tokens | Migration conflicts or lost pending rename state |
| **2** | Normalize plan; reconcile/archive plan and queue history | Smaller, relevant active material; smart extraction currently still saturates its cap | Losing obligations or breaking completion accounting |
| **3** | Joint handoff/compaction policy | 50% provides 200K additional headroom on 1M | Compaction ordering and settings inheritance |
| **4** | Bound audit output and avoid acknowledgement storms | Plausible savings; not isolated in this transcript | Incomplete recovery or undelivered routing updates |

Exact savings per fix are unmeasured. Rank 1 has the strongest measured association; ranks 2–4 require controlled before/after evidence.

### Implementation outline 1 — Canonical session-start ledger

1. **Objective:** one initialization claim per repository/session UUID across linked worktrees, preserving first-start reloads and rename recovery.
2. **Files:** `python/src/dotfiles_setup/session_start.py`, `tests/test_session_start.py`, affected hook fixtures, and mirrored session-start skill documentation.
3. **Interfaces:** preserve public `session-start {decide,pending,renamed}`, JSON fields and explicit `--state-dir`; canonicalize only the default state root. Keep naming decisions tied to event `cwd`.
4. **Constraints:** reuse the existing Git resolver; preserve locking and persistence before return; define migration precedence and refuse conflicting ledgers; fail safely if canonical resolution fails; no Bash logic.
5. **Verification, future only:** isolated real Git repository with linked worktrees, invoking public CLI from both loaded checkouts. Same UUID must reload once; new UUID must reload. Cover pending/confirmed rename, concurrency, explicit override and corrupt/conflicting state. **Fail arm:** restoring checkout-local default state must cause the same-UUID migration assertion to fail. A controlled Claude replay measures actual context savings.
6. **Commit:** caller.
7. **PREMISES:** **L** checkout-local default at `session_start.py:413`; **I** UUID-keyed ledger at line 277; **P** existing repeat suppression at lines 279–287; **E** existing JSON decision/reload fields retain their schema; **A** precise savings and complete reload causality remain unproven.

### Implementation outline 2 — Active plan and queue with tracked archives

1. **Objective:** concise native-format active planning artifacts containing every unsettled obligation, with historical content preserved.
2. **Files:** coordinator-owned `task_plan.md`, `.agent/plans/main-checkout-ship-queue.md`, proposed tracked `docs/handoffs/coordinator-plan-archive-2026-10-04.md` and `docs/handoffs/ship-queue-archive-2026-10-04.md`; relevant handoff instructions.
3. **Interfaces:** existing authorized `handoff-inbox plan-apply --edits` and plan attestation; unique replacement anchors; native `PWF_INJECT=smart`. Queue reconciliation remains coordinator-authored unless a transaction capability proves necessary.
4. **Constraints:** archive verbatim; reconcile later updates first; preserve quoted rulings, completion accounting, live ownership and inbox fallback; coordinator remains sole plan writer.
5. **Verification, future only:** isolated artifacts/job state; assert archive exactness, unresolved-obligation retention, stale-caller/ambiguous-anchor rejection, valid attestation and smaller nontruncated injection. **Fail arms:** naïve HISTORY splitting loses a later pending obligation; original malformed smart sections exceed the active budget; genuine stale checkbox loss still warns.
6. **Commit:** caller.
7. **PREMISES:** **L** measured plan/queue sizes and headings; **I** authorized atomic edits at [handoff_inbox.py:240](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-churn/python/src/dotfiles_setup/handoff_inbox.py:240); **P** native smart extraction and progress guard; **E** active text emits obligation/archive references, with a budget established before implementation; **A** exact token savings remain unmeasured.

### Implementation outline 3 — Coordinated context policy

1. **Objective:** increase useful coordinator headroom while retaining enough room for outgoing audit and handoff.
2. **Files:** `python/src/dotfiles_setup/coordinator_handoff.py`, `tests/test_coordinator_handoff.py`, mirrored coordinator-handoff skill files and approved policy documentation.
3. **Interfaces:** existing [launch_argv](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-churn/python/src/dotfiles_setup/coordinator_handoff.py:726) supplies inline `--settings` JSON. Extend that native settings seam with coordinated handoff and compaction values, retaining cross-session acceptance. Trial handoff 50%; establish the compaction value from measured runtime headroom.
4. **Constraints:** do not assume `--autocompact` bypasses the legacy percentage override. Preserve ordinary-lane policy and verify child inheritance; changing only successor settings does **not** establish coordinator-only scope.
5. **Verification, future only:** isolated public launch-argument tests, 200K/1M denominator arms, override precedence, boundary rounding and ordinary-lane inheritance; controlled runtime measurement of effective compaction/handoff ordering. **Fail arms:** retaining 33% must expose earlier compaction ordering; removing child-policy isolation must fail the lane-boundary assertion.
6. **Commit:** caller.
7. **PREMISES:** **L** default handoff 30 and repository compaction override 33; **I** inline native launch settings and documented precedence; **P** existing cross-session settings carriage; **E** launch argv/settings change only the intended policy fields; **A** effective runtime window, required outgoing headroom and inheritance isolation require verification.

## Execution and validation receipt

| Specialist | Owned review | Normal gate | This review |
|---|---|---|---|
| Python | Transcript accounting and state interfaces | pytest | **NOT RUN; no exit code** |
| Config | Hooks, thresholds and launch settings | `mise run lint` | **NOT RUN; no exit code** |
| Documentation | Plugin controls, takeover contracts and research | `mise run lint-docs` | **NOT RUN; no exit code** |

Research processes used native `fnox … --profile codex_research … exec`; secrets were not printed or persisted.

| Route | Actual execution/result |
|---|---|
| Exa | Plain API; **rc 0** |
| Context7 | `ctx7 library` and `ctx7 docs`; **rc 0** |
| GitHub | `gh api`, repository/code search and primary-source reads; **rc 0** |
| Firecrawl | Native search; **rc 1**, HTTP **402** |
| Last30Days | Read-only `--preflight`; **rc 0**, `local_writes: []`. Full engine **NOT RUN** because it unconditionally writes run state. Preflight emitted a dependency `SyntaxWarning`. |
| Live harness-doc refresh | HTTP **403**, **rc 1**; supplied primary-doc mirror and transcript controls used |

Five-provider research therefore remains **incomplete**.

Skills read/applied: `codex-sdlc-team`, planning-with-files, Exa search, Firecrawl search, Context7 CLI, Last30Days, coordinator-handoff and session-handoff. CLIs used included `fnox`, `gh`, `ctx7`, `firecrawl`, `uv`, Python, Git, `rg`, `cat`, and filesystem inventory commands. No connector apps or MCP provider tools ran; no new Claude session or plugin hook was executed.

Exploratory failures included unmatched zsh globs (**rc 1**), missing guessed paths (**rc 1/2**), two Python inspection errors (**rc 1**) and pre-execution JavaScript syntax errors. Corrected reads supplied the reported evidence. None were treated as proof of absence.

## GitHub repos touched

Read/search only; no remote mutations:

- `ray-manaloto/dotfiles`
- `ray-manaloto/knowledge-base`
- `OthmanAdi/planning-with-files`

Specialists spawned:

- `sdlc-python-specialist` — `/root/python_review`
- `sdlc-config-specialist` — `/root/config_review`
- `sdlc-documentation-specialist` — `/root/documentation_review`

No others were spawned.

