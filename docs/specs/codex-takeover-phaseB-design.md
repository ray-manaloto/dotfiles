# Codex takeover Phase B design — W0–W5 (#1721)

Status: incremental Phase A design; no production implementation or host installation.
The caller owns commits. The architect must ratify a separate Phase B implementation spec.
Requirements are the ratified table in `docs/specs/codex-takeover-2026-10-05.md:93`
and the evidence-only restriction in `docs/specs/codex-takeover-phaseA-research.md:5`.
All interfaces, paths and schemas labelled **proposed** below are design decisions,
not claims of installed behavior. **A** marks an unverified prerequisite.

## Decision and dependency ledger

| Work | Design outcome | Delivery prerequisite |
|---|---|---|
| W0 | Retain current `@AGENTS.md` import stubs and `.claude/CLAUDE.md`. | Any later migration needs real load proof plus synchronized gates/rules. |
| W1 | One Python registry, both repositories, provider-qualified identities and live lane cards. | Complete inventory with explicit unknowns. |
| W2 | Idempotent issue intentions and coordinator-owned plan deltas. | Phase B issue-write authorization and verified repo identity. |
| W3 | Extend existing audit/review discovery with date selection and a command projection. | Privacy-safe controls prove both providers contribute. |
| W4 | Typed check plus disabled self-heal design and 900-second launchd checks. | OFF directive superseded explicitly; verified persistent Codex launch identity and guard parity. |
| W5a | Compact root bootstrap explicitly reads a tracked policy index; reuse `.agents/skills`. | Reclaim root characters and prove the actual policies reached Codex. |
| W5b | Shared coordinator runbook; main checkout shipping and SLOT GO. | Codex writer identity supported without impersonating a Claude session. |

**Licensed dissent — enabled self-heal is stopped.** The main watcher handoff explicitly says
“Coordinator AUTO-LAUNCH is OFF” until the relay-rule r3 / #1681 launch-record resolver lands
and its lane says to switch (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/plans/handoff-inbox/watch.md:122`).
The ratified W4 request permits self-heal in principle
(`docs/specs/codex-takeover-2026-10-05.md:101`). That does not establish that the OFF condition
has been discharged. Implement and validate checks first; retain disabled self-heal until a
new cited ruling and live resolver evidence supersede OFF. A closed issue alone is insufficient.

Dependencies only: process-hardening guard parity; credit-fallback-finish / #1577;
handoff-automation-research at 703e5612. These are named exclusions in
`docs/specs/codex-takeover-phaseA-research.md:61`. Do not implement their guards, hook changes
or successor machinery in this lane. **A:** the process-hardening spec directory is absent in
this worktree; consume its ratified version from its owning lane before self-heal enablement.

## W0 — retain the import stubs

Recommendation: keep today's `CLAUDE.md` import-stub pattern and `.claude/CLAUDE.md` through
Phase B. Claude's primary changelog says AGENTS.md support shipped in 2.1.277
(`docs/research/kb/raw/codex-takeover/claude-changelog.md:1055`) and provider/telemetry support
expanded later (`:892`). Built-in absence cannot be inferred from an installed-plugin listing.
**A:** the exact active mode and successful instruction loading in this host's current session
remain unproved. Preserve the working instruction route until an isolated real marker-load
probe confirms its replacement. This corrects the inherited “not active because not listed”
premise rather than relying on it.

The mirrored primary mod source describes fallback stand-down when a project CLAUDE.md,
.claude/CLAUDE.md or CLAUDE.local.md exists (`docs/research/kb/raw/codex-takeover/links/agents-md/README.md:8`),
both-mode import deduplication (`:20`) and user/explicit/managed-only plugin option scope (`:62`).
It also describes specific nested Read attachment behavior (`:96`). Do not generalize those
source statements into an installed-runtime proof or remove stubs based on shipping status.
The report records GitHub issue/PR/discussion evidence, saved searches and outstanding limits
in `docs/research/kb/reports/agents/codex-takeover-phaseA-2026-10-05.md:59`.

Retaining stubs leaves `claude_md_import_stub`, `claude_agents_md_pairs` and the `.claude`
rule-sync target intact; configuration evidence records those existing contracts
(`docs/research/kb/raw/codex-takeover/config/audit.md:59`). No knowledge-base or user-settings
migration is needed for this recommendation. A future zero-CLAUDE candidate needs its own
proven load controls, cross-repo synchronized gates and exact reviewed settings change.

## W1 — registry and cards (proposed)

Reuse `session_common.main_checkout` for canonical worktree resolution
(`python/src/dotfiles_setup/session_common.py:183`), `TranscriptBases` and provider-qualified
`TranscriptSource` for source selection (`python/src/dotfiles_setup/session_ledger.py:569`),
and existing handoff/inbox paths (`python/src/dotfiles_setup/session_common.py:43`).
The fleet interface is `claude agents --json --all`, returning an array. **Licensed dissent:**
the seven-fields-in-every-row premise in `docs/specs/codex-takeover-phaseA-research.md:44` is
contradicted by the current public probe: 133 mapping rows, rc 0, with only `cwd, id, kind,
sessionId, startedAt, state` in their key intersection; `name` is optional
(`docs/research/kb/raw/codex-takeover/config/session-inventory-receipt.json:19`).
Stop work that assumes a required name. Proposed amendment: preserve optional display name,
fall back to stable provider/session ID for cards, and block takeover when role ownership
cannot be reconciled. Architect must ratify that amendment before Phase B implementation.

Public interfaces:

- `mise run lane-cards -- --repo-root <absolute-root> --repo-root <absolute-kb-root> --json`:
  collect bounded read-only inventory and print `RegistrySnapshot`; no file writes by default.
- `mise run lane-cards -- ... --write`: write live cards and registry state to each canonical
  main checkout. Reject an unknown repo or unavailable writer authorization. Never edit plans.
- `session_registry.collect(roots, *, runner, bases, clock) -> RegistrySnapshot` and
  `session_registry.write_cards(snapshot, *, state_root) -> CardWriteResult`: injectable
  boundaries; modules perform mechanics, the runbook supplies judgment.

Snapshot shape: `schema_version, collected_at, repositories[], sessions[], chains[], omissions[]`.
Repository rows: `repo_key, github_repo, canonical_main, worktrees[{path, branch, head_sha}]`.
Session rows: `provider, session_id, name, role, repo_key, cwd, started_at, raw_state,
normalized_state, liveness, lineage, task_refs[], issue_urls[], evidence_refs[]`.
`name` and `role` may be unknown; fallback card display is `provider-session_id`. Missing names
never erase rows or prove the absence of a coordinator. Liveness is `live|dead|unknown` with `observed_at, probe_kind, process_identity`; raw harness
state remains separate. A stopped/done label or old transcript timestamp never proves death.
Missing/malformed inventory produces omissions and unknowns, not an empty live fleet.

Scope roots are the canonical dotfiles and knowledge-base main checkouts plus their registered
worktrees. Derive repository membership from Git worktree topology, not a `dotfiles-` name
prefix. Registry IDs are `provider:session_id`; disambiguate equal session IDs across providers.
Unregistered paths become unresolved rows. Existing Codex discovery currently matches metadata
`cwd` exactly (`python/src/dotfiles_setup/session_ledger.py:1438`); enumerate each registered
worktree as an input and deduplicate sources. Do not silently reuse it as an all-worktrees query.

Collapse coordinator and watcher successor chains by `(repo_key, role)` for their issue/card
summary, while preserving every member session, raw state and explicit predecessor edge.
Choose the display member by parsed `started_at` with a deterministic ID tie-break. A latest
row is display precedence only, never ownership authority. Prefer recorded handoff/launch
edges; flag incompatible live members instead of guessing a successor. Ordinary named lanes
retain individual identity unless a verified predecessor edge connects them. The user selected
working/blocked/stopped sessions and one issue per role-chain
(`docs/specs/codex-takeover-2026-10-05.md:87`).

Cards: `<canonical-main>/.agent/lanes/<validated-name>.md`; duplicate names get a stable
provider/session suffix, and path components reject traversal. Include absolute repo/worktree
paths, head SHA, member IDs, observed state/liveness, done/open tasks, research questions,
blockers, suggestions, issue links, source timestamps and omissions. Derive tasks from
`task_plan.md`, lane inbox and issue evidence; never infer done from a return code alone.
Write atomically under `state_lock`; preserve an existing card if inventory fails. Archive
stale cards in state rather than deleting evidence. Proposed registry snapshot lives at
`.agent/state/session-registry/registry.json`; snapshots are copied into a tracked handoff,
not relied on as clone-durable history. This follows the ratified tracked-doc/live-card split
(`docs/specs/codex-takeover-2026-10-05.md:98`).

## W2 — issues and plan deltas (proposed)

Phase A files no issues. The W0–W5 issues and umbrella are already recorded as #1715–#1721
(`docs/specs/codex-takeover-2026-10-05.md:106`). Phase B reads those before producing intentions.
For each unresolved working/blocked/stopped lane or coordinator/watcher chain lacking an issue,
produce `IssueIntent{repo, stable_key, title, body, member_session_ids, source_refs}`. The
stable marker includes repo/provider/identity (chain role for coordinator/watch), never only
its title. Search existing issue bodies for that marker and imported issue references before
creation; API/read failures are blocked intentions, never permission to create duplicates.
Skip done sessions unless an eligible chain member has unresolved work; retain their history.
Existing issues are reused even if their title changes.

Default `lane-cards --issue-plan <output>` emits a preview containing `reuse|create|blocked`
intentions. A separate explicit Phase B `--apply-issues` operation may create issues using
`gh api` only after its own authorization; serialize intention application per repository,
recheck the stable marker inside that lock and atomically record returned URLs. The remote
API has no proven create idempotency token (**A**): an ambiguous network outcome requires a
fresh search/reconciliation, and must not immediately retry creation. No launchd tick files issues.

Emit `.agent/plans/task_plan-delta-<lane>-<timestamp>.md` with a task per request item and
eligible session/chain, stable IDs, issue URL, evidence and blocked status. Coordinator applies
it through the existing typed handoff-inbox plan route, then runs `plan-attest`; lanes do not
rewrite the whole plan. `handoff_inbox` already supports exact-anchor typed replace/append
and refuses drift (`python/src/dotfiles_setup/handoff_inbox.py:36`). Its coordinator-only
writer authorization currently resolves `CLAUDE_CODE_SESSION_ID` to a Claude job record and
newest `createdAt` (`python/src/dotfiles_setup/handoff_inbox.py:22`). **A/blocker:** a Codex
coordinator identity is not established by this route. Phase B must provide explicit
provider-qualified identity validation as a separately reviewed extension; never export a
Claude identity to bypass it. Read-only preview and inbox append remain usable independently.

## W3 — digest miner (proposed)

Current audit extracts Claude `tool_use` named `Bash`, pairs results, and classifies execution
proof (`python/src/dotfiles_setup/command_audit.py:276`, `:320`, `:367`). The command window
counts roots before recursively including their subagents (`:236`). `command-audit` has a
host-wide single-instance lock and can return rc 0 while skipped (`:796`); digest receipts
must therefore assert artifact freshness and selected-source counts, not rc alone.

`session-review` reuses audit classifications for command shapes, ranks by distinct sessions,
and additionally surfaces narrative costs from notes/handoffs/goal history
(`python/src/dotfiles_setup/session_review.py:10`, `:20`, `:322`). Its default transcript shape
path still selects Claude transcripts (`:770`); the requirements branch already uses a separate
coverage route (`:763`). Do not claim the shape lane already mines Codex.

Reuse `session_ledger.discover_sources` for both providers (`python/src/dotfiles_setup/session_ledger.py:1464`),
`TranscriptBases` for isolated fixtures (`:589`) and `SessionStore` for fingerprinted source
cache (`python/src/dotfiles_setup/session_store.py:132`). Existing Codex tool parsing emits
call/result structure while digesting opaque arguments/output, not command text
(`python/src/dotfiles_setup/session_ledger.py:2119`). Minimal extension: add a public bounded
command projection at the native parse boundary plus a `since` selection policy, and route
both audit and review shape consumers through it. Do not write a second general rollout parser.

New shared selection: `providers={claude,codex}, since=2026-10-02T00:00:00-05:00,
repo_roots, session_limit, bases`. Store the normalized UTC cutoff in the receipt. Include a
selected root and its children when it has in-window command events; filter commands by event
timestamp, not rollout filename or mtime. Missing/invalid timestamps are explicit omissions.
If limits truncate the date window, label coverage partial and show excluded counts.

Command projection shape: `provider, source_id, event_ref, call_id, session_id, timestamp,
command_shape, command_sha256, execution_status, result_ref`. Accept direct structured
`exec_command`/supported tool namespace arguments with a string `cmd`, and Claude Bash input
`command`; correlate results by native `call_id`/tool-use ID. Count an attempted/refused command
separately from executed commands. A wrapper such as `functions.exec` containing JavaScript
is opaque unless a validated structured child event exists: do not regex-infer execution from
embedded source. Unknown outputs, missing results, malformed lines and schema drift remain
unknown/omitted, never credited as executed. **A:** installed-version result semantics require
fixture and read-only primary source verification before classifying Codex refusals.

Digest output defaults to `.agent/session-review/codex-takeover-digest.md` plus sibling JSON;
tracked promotion follows human/SDLC review. Emit only approved command shapes, counts,
provider-qualified hashed source identifiers, record line numbers/digests, time window,
source/omission counts and candidate rationale. Never emit raw arguments, tool output,
transcript snippets, environment values, URLs with userinfo/query credentials, or secret-like
path names. Keep source resolution local. The store already hashes provider-qualified file
identities (`python/src/dotfiles_setup/session_store.py:116`); do not undo that property in a
report. A safety scanner alone is not a sufficient boundary: default projection must be an
allowlist and unknown payloads have digest-only treatment.

Named control arm: **dual-provider since-and-execution control**. Build isolated native-shaped
Claude + Codex roots in two temporary Git repos/worktrees. One unique allowed one-off command
shape appears in both after cutoff, another only before cutoff, a refusal shares the hit
shape, and a fresh random absent shape appears nowhere. Public audit and review output must
show both providers, correct executed/attempt counts, the in-window hit and zero absent/before
hits. Reverting Codex projection, timestamp filter, result pairing or repo filter must fail
an assertion; include unrelated repo and subagent records to expose leakage/omission.
A separate planted fake credential in args, outputs, URLs and nested values must never appear
in either digest artifact. No test reads the real home directory or real transcripts.

## W4 — takeover check and guarded recovery (proposed)

Public task: `mise run takeover-check -- --check-only --json --repo-root <root>`.
Proposed Python seam: `takeover_check.check(snapshot, launch_state, *, clock) -> TakeoverResult`;
`--self-heal` is explicit, disabled by policy until the ledger prerequisites are proven.
Watcher tick and Codex session start invoke the same check-only seam; none independently
implements a coordinator selector or shell launcher. Unknown identity, inaccessible source,
stale inventory, ambiguous chains and logging failure all block recovery.

Result: `schema_version, checked_at, repo_key, mode, status, reason_codes[],
claude_coordinators[], codex_coordinators[], evidence_refs[], launch_attempt_id,
launch_record, omissions[]`. Each coordinator has session ID, verified process identity,
liveness and successor/retirement evidence. Proposed stable rc mapping:

| rc | Status | Operational meaning |
|---|---|---|
| 0 | `healthy` or `started-recorded` | One verified owner, or a newly verified launch with durable receipts. |
| 1 | `takeover-needed` | Complete evidence proves no live coordinator; check-only creates no launch. |
| 2 | `blocked` | Unknown/ambiguous liveness, multiple owners, policy disabled, existing launch/pending record, lock or input failure. |
| 3 | `launch-failed` | Definite failure before a persistent coordinator was confirmed. |
| 4 | `started-unrecorded` | Start may have occurred; never retry automatically, reconcile identity/receipt first. |

This is a new task contract, not a restatement of handoff rc. Existing handoff `launch`
already distinguishes refused/failed/started-unrecorded (`python/src/dotfiles_setup/coordinator_handoff.py:844`).
Use its `session_common.state_lock` and atomic `write_state` primitives
(`python/src/dotfiles_setup/session_common.py:119`, `:131`), reservation before the unlocked
bounded external start (`python/src/dotfiles_setup/coordinator_handoff.py:947`) and independent
started receipt pattern (`:977`). Do not call its `launch_argv`: it starts Claude explicitly
(`:749`). Do not equate successful process spawn with confirmed coordinator ownership.

Guarded transaction, once enabled:

1. Resolve canonical repo and shared host launch-lock path
   `<dotfiles-main>/.agent/state/takeover-check/host-launch.json` (same path from watcher,
   launchd and linked worktrees). Hold a bounded 10-second transaction lock. Namespace repo
   generations inside the state. A single Codex coordinator host-wide for these two repos is
   the proposed conservative ownership rule; it has a primary repo and explicit managed roots.
2. Refresh BOTH provider inventories and liveness inside the lock. A live Claude coordinator
   in either managed repo blocks launch. Zero live Codex coordinators is required to start:
   “≤1” is the invariant after launch, not permission to start a second when one exists.
   One verified Codex coordinator is healthy; more than one is blocked for reconciliation.
   No `done`/`stopped` label, elapsed age or nonexistent rollout alone proves process death.
3. Validate approval/policy generation, verified process/death probes, executable/CLI identity,
   guard parity, owned roots, readable handoff/queue and sanctioned inbox route. Append a
   durable inbox `launch-intent` containing attempt ID, source census hashes, reason, repo
   roots and time. A failed intent append or state write means no launch.
4. Atomically reserve `launch_pending{attempt_id, generation, at, owner_probe, inbox_ref}`,
   then release the lock for a bounded persistent coordinator adapter start. Concurrent
   callers see the reservation and never start. Recheck pre-start liveness in the adapter;
   a freshly appeared Claude/Codex owner cancels launch. **A:** external harnesses can launch
   independently of this lock; guard parity must specify shared exclusion or acknowledge
   that the at-most-one proof only covers participating callers. Until proven, self-heal stays off.
5. Adapter records supervisor PID + OS process-start token, executable identity, native Codex
   thread/session ID, exact cwd, selected roots and stdout/rc receipt paths. **A:** the concrete
   persistent Codex launcher/API and its startup acknowledgement are not yet verified; Phase B
   must prove them in an isolated persistent session. No `--ephemeral`, arbitrary shell-detach
   assumption, Claude background flag, or review-lane launcher substitution.
6. Write a separate durable started receipt before finalizing the transaction and append the
   inbox outcome. If spawn/timeout is ambiguous or any post-start write fails, return rc 4;
   retain/quarantine the reservation and do not relaunch. A confirmed no-start failure returns
   rc 3 and records evidence. Pending state does not expire into retry eligibility on age alone:
   reconcile process identity + native session evidence and require explicit abandoned-attempt
   resolution. PID reuse must be checked against start token and executable, not `kill -0` alone.
7. Coordinator acknowledgement includes runbook/instruction proof, owned registry roots and
   sanctioned writer identity. Started without acknowledgement remains quarantined. Successful
   acknowledgement retires no predecessor automatically; use the existing handoff retire gate
   after heavy-run adoption/settlement (`python/src/dotfiles_setup/coordinator_handoff.py:734`).

If a Claude coordinator remains live but blocked on usage, rc is healthy/blocked with a reason;
that is not death and cannot authorize takeover. Proposed operator action is a recorded
ownership transfer using the existing handoff audit and retirement procedure, never a kill.
Logging contains structured reasons and identity hashes, not prompts, secrets or raw transcripts.

### launchd contract

Proposed host job is a tracked declaration and expanded plist proposal, not installed by Phase A. It runs check-only
once every 900 seconds, with `RunAtLoad=false` and `KeepAlive=false`; no retry storm or implicit
boot launch. Repository ownership uses a new `[bootstrap.macos.launchd.agents.dotfiles-takeover-check]`
declaration in `mise.toml`, following the existing declaration at `mise.toml:1602`.
Proposed values: `program="~/.local/bin/mise"`,
`args=["-C", "/Users/rmanaloto/dev/github/ray-manaloto/dotfiles", "run", "takeover-check", "--", "--check-only"]`,
`start_interval=900`, `working_directory="~/dev/github/ray-manaloto/dotfiles"`,
`stdout_path="~/Library/Logs/dotfiles-takeover-check.log"`,
`stderr_path="~/Library/Logs/dotfiles-takeover-check.err.log"` and literal
`PATH="/Users/rmanaloto/.local/share/mise/shims:/Users/rmanaloto/.local/bin:/opt/homebrew/bin:/usr/bin:/bin"`.
The current pattern documents that environment values are not tilde-expanded (`mise.toml:1609`)
and requires shim-first PATH (`mise.toml:1612`). Use only these observed native declaration fields; do not invent `run_at_load`/`keep_alive`
configuration keys. The expanded candidate XML carries explicit false RunAtLoad/KeepAlive.
Existing installed tick/project plists omit both keys
(`docs/research/kb/raw/codex-takeover/config/installed-launchd-receipt.json:17`);
**A:** omission defaults require primary documentation verification before accepting an omitted-key
preview as equivalent. If native bootstrap cannot emit the reviewed contract, hold installation
for a ratified exact plist action rather than build a custom generator.
The full candidate XML and bootstrap label/destination evidence are in
`docs/research/kb/raw/codex-takeover/config/audit.md:139`.
The proposed label is `dev.mise.dotfiles-takeover-check` with host destination
`~/Library/LaunchAgents/dev.mise.dotfiles-takeover-check.plist`; require the generator's exact
output and `plutil` proof before installation. Approval to install is a separate final host action as required by
`docs/specs/codex-takeover-2026-10-05.md:62`. The same shared launch state is used if the reviewed
plist later adds explicit `--self-heal`; launchd receives no independent kill/restart policy.

## W5a — explicit policy bootstrap (proposed)

Use the existing AGENTS hierarchy plus one short root instruction that requires reading
`docs/agents/codex-policy-index.md` before work. The index contains an ordered eager-policy
read list, a table of scoped rule paths and matching edit conditions, `.claude/CLAUDE.md`
context, and canonical `.agents/skills` pointers. Its reader explicitly opens required targets;
Markdown links alone do not automatically inject content. No duplicated full rules in root.

The pinned Codex primary source returns the first found instruction candidate in each
directory (`docs/research/kb/raw/codex-takeover/codex-agents-md.rs:242`) and orders fallback
filenames after AGENTS.override.md/AGENTS.md, rejecting path-containing entries (`:272`).
Therefore `project_doc_fallback_filenames` is an alternative-file mechanism, not an additive
`.claude/rules/*.md` loader. A nested `.claude/AGENTS.md` does not bridge root-cwd policy reading.
Primary source URL:
<https://github.com/openai/codex/blob/823ea830c0fd418b09ff02d36cad9a1fff66465b/codex-rs/core/src/agents_md.rs>.

Current root size is 11,978 UTF-8 bytes but 11,892 Unicode characters, leaving 108 characters
against the repo's 12,000-character cap (`docs/research/kb/raw/codex-takeover/config/audit.md:32`).
Reclaim enough measured root text before adding the bootstrap; retain every invariant by moving
explanatory detail to the index/runbook, and validate the root character and native byte limits
separately. The exact root replacement is Phase B's reviewable diff, not a permission to discard
rules. Runtime `project_doc_max_bytes` is a separate effective config limit: record its current
value in the isolated load proof rather than infer it from the repo's character cap.

Reuse `.agents/skills` canonical generated mirrors; current check rc 0 is recorded in
`docs/research/kb/raw/codex-takeover/config/audit.md:42`. No third copied skill corpus and no
user-level global instructions changes. A fresh Codex probe must report an eager rule marker,
a matched scoped-rule marker and a discovered skill from the actual workspace; the control
removes the bootstrap/read and must fail those assertions. Record omissions explicitly if
context budget truncates the bridge.

## W5b — shared coordinator runbook (proposed)

Tracked destination: `docs/agents/session-orchestration.md`. It must be usable from Claude and
Codex, with provider adapters clearly separated from shared repo mechanics.

1. Read root instructions and the W5a index, then explicitly read linked eager rules and the
   scoped rules applicable to the intended edits. A Markdown link is a pointer, not proof the
   harness loaded its target. Run takeover-check in check-only mode; reconcile any unknown or
   duplicate owner before taking coordinator authority.
2. Recover predecessor transcript, tracked handoff, all lane inboxes, ship queue, task plan,
   registry cards, SDLC settlement/output and live processes/logs. Compare effective gated SHA
   and rc, record corrections before announcing ownership. This reuses the existing successor
   brief sequence (`python/src/dotfiles_setup/coordinator_handoff.py:721`).
3. Preserve one heavy host gate and one shipper per repo. Read the queue and carry order/held
   decisions; a dashboard state or stale `CURRENT` heading is not a live SLOT grant. The source
   queue contains evolving authoritative entries (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/plans/main-checkout-ship-queue.md:4`)
   and the shared brief states the host/shipper rule (`python/src/dotfiles_setup/coordinator_handoff.py:712`).
4. Each lane sends `SLOT REQUEST <lane> <repo> <head SHA> <commands>` through its available
   approved communication surface or `mise run handoff-inbox -- append`. Record one matching
   `SLOT GO` before heavy gates; completion records per-command rc + effective SHA and
   `SLOT RELEASED`. No grant inferred from silence, elapsed time or another lane's release.
5. Apply task-plan deltas and queue changes through sanctioned public interfaces. The current
   Codex authorization gap remains blocking for `plan-apply`/`queue-append`; read-only recovery
   and ordinary inbox append can proceed. Phase B's provider identity extension must have a
   stale/superseded identity refusal arm before enabling Codex coordinator writes.
6. Ship/land dotfiles from its main checkout through `mise run ship` / `mise run land -- <PR>`
   under SLOT GO, keeping implementation edits in registered isolated worktrees. Do not bypass
   a writer guard, switch branches during someone else's ship, or treat merged as installed.
   Knowledge-base delivery remains its own repository policy and existing human-only rulings;
   neither this runbook nor takeover grants cross-repo shipping permission.
7. Adopt or wait for recorded heavy runs, resolve actual log paths, and retire predecessors
   through `coordinator-handoff -- retire --state-dir <exact-dir>`. Harness-output logs lack
   rc files; wait for PID exit and inspect output (`python/src/dotfiles_setup/coordinator_handoff.py:727`).
   An in-flight run must be settled/adopted; no bare `claude stop`.
8. Snapshot live cards and ownership evidence into the tracked next handoff. Include queued
   questions, failed/provisional research routes and unresolved A prerequisites. Links to
   process-hardening and #1577 identify dependencies; this lane does not alter their guards/hooks.

## Proposed complete Phase B file list

This is the proposed implementation allowlist for the architect to ratify; it does not expand
Phase A's four-path allowlist. New paths have no observed implementation behind them.

| Work | Proposed tracked paths | Change |
|---|---|---|
| W0 | `CLAUDE.md` and existing nested stubs: retain; `hk.pkl`, `rule-sync.toml`: retain | No removal/retargeting unless instruction-load proof later changes verdict. |
| W1 | `python/src/dotfiles_setup/session_registry.py`; `python/src/dotfiles_setup/main.py`; `mise.toml`; `tests/test_session_registry.py` | Collector/card renderer, CLI and task. |
| W1/handoff | `.claude/skills/coordinator-handoff/SKILL.md`; `.agents/skills/coordinator-handoff/SKILL.md`; `python/src/dotfiles_setup/coordinator_handoff.py`; `tests/test_coordinator_handoff.py` | Snapshot cards into handoff; preserve existing launch/retire machinery. |
| W2 | `python/src/dotfiles_setup/session_registry.py`; `python/src/dotfiles_setup/handoff_inbox.py`; `tests/test_session_registry.py`; `tests/test_handoff_inbox.py` | Issue preview/application seam and typed delta identity extension, if its separate guard dependency is cleared. |
| W3 | `python/src/dotfiles_setup/session_ledger.py`; `python/src/dotfiles_setup/session_store.py`; `python/src/dotfiles_setup/command_audit.py`; `python/src/dotfiles_setup/session_review.py`; `python/src/dotfiles_setup/main.py`; `tests/test_session_ledger.py`; `tests/test_command_audit.py`; `tests/test_session_review.py` | Shared source/date selection, bounded projection, versioned cache policy and both consumers. |
| W4 | `python/src/dotfiles_setup/takeover_check.py`; `python/src/dotfiles_setup/codex_coordinator_supervisor.py`; `python/src/dotfiles_setup/main.py`; `mise.toml`; `tests/test_takeover_check.py`; `tests/test_codex_coordinator_supervisor.py` | Typed read-only check, shared reservation and persistent adapter interface; self-heal disabled. |
| W4 launchd | `mise.toml` bootstrap declaration; candidate plist remains cited in Phase A raw evidence | Native bootstrap-supported 900-second check-only declaration and reviewed expanded plist; separate host install. Unsupported keys block installation rather than trigger a homegrown generator. |
| W5 | `docs/agents/session-orchestration.md`; `docs/agents/codex-policy-index.md`; `AGENTS.md`; generated `.agents/skills` mirrors only where affected | Shared runbook and compact explicit policy bootstrap; measured budget. |
| Evidence | `docs/research/kb/reports/agents/codex-takeover-phaseB-validation-2026-10-05.md` | Effective SHAs, real rc, source counts, control arms and explicit held prerequisites. |

No new `.codex/skills` tree: the repository generates `.agents/skills` from Claude skills
(`python/src/dotfiles_setup/skills_mirror.py:2`, `:249`). Update canonical Claude skill first,
then the existing generator and parity gate; do not hand-fork the mirror. Do not add W0 user
settings or knowledge-base instruction edits to this implementation without their explicit
repo/host review. The Phase B installer may write the reviewed launchd plist and its runtime
logs only after the separate host action. Production launch/state/log paths are runtime
artifacts, not files authored in Phase A.

## Public-interface verification and realistic fail arms

Every new public Python function needs a meaningful behavior test. Fixtures use temporary Git
repositories and isolated transcript/state roots with controlled clock and injected subprocess
boundary. CLI integration exercises `dotfiles-setup` / `mise run` public commands; no private
function-only assertion is the sole proof. Assertions check outcomes, identity/coverage,
no unintended side effects and real rc. Local validation runs after a matching SLOT GO.

| Work | Public-interface success proof | Fail arm that catches reverting the requested behavior |
|---|---|---|
| W0 | Installed Claude native instruction-load proof in an isolated checkout with a unique AGENTS marker and controlled stubs. | Remove/disable the candidate AGENTS loading path; marker must disappear. Deletion of stubs cannot ship on plugin-list evidence alone. |
| W1 | `lane-cards --json` and `--write` include both repos, registered linked worktrees, absolute paths, all member IDs, task evidence and fresh timestamps. | Drop KB rows or child worktree discovery: membership assertions fail. Malformed inventory must report unknown without erasing prior cards. A malicious session name must not write outside card root. |
| W1/W2 | Same-role coordinator/watch chains form one issue intention while preserving live predecessor evidence. | Disable collapse: issue count fails. Over-collapse ordinary named lanes or erase live predecessor: member/liveness assertion fails. |
| W2 | Public issue-plan shows reuse for renamed existing marker, create only for missing eligible sessions, no done-only intention; delta has one stable task per item/session/role-chain. | Lose stable marker search: duplicate intent fails. Change repo assignment: repo assertion fails. Simulated ambiguous create outcome must reconcile without second POST. Reapplying preview performs no duplicate writes. |
| W3 | Dual-provider since-and-execution control described above produces expected public audit/review artifacts and coverage. | Revert any one of provider adapter, date filter, result pairing, root filter or secret projection; the respective coverage/count/leak assertion goes red. Unknown wrapper payload stays explicitly opaque. |
| W4 liveness | A verified live Claude process blocks launch even when its harness row is `done`, `stopped`, or recorded retired; one live Codex owner blocks a second. | Trust row state/retirement/age over process identity: fake launcher count becomes nonzero and test fails. A live predecessor hidden by chain collapse must still block. Missing/unknown census, missing optional name with unresolved role, or native start identity must produce rc 2 and zero launches. |
| W4 concurrency | Two public takeover-check processes share a temporary canonical state root and a barrier-synchronized fake persistent adapter; exactly one attempted launch and durable intent/receipt. | Remove lock or reservation, or use separate per-worktree locks: two launches violate assertion. Repeat tick after finalization failure must keep rc 4/quarantine and zero additional launches. |
| W4 logging/failure | Unwritable inbox/state before spawn yields rc 2, zero spawn calls; post-start receipt failure yields rc 4, retained reservation and no retry. | Allow append/write failure to fall through: spawn count fails. Ambiguous timeout cannot be treated as safe no-start; retry-count assertion fails. PID reused with a different start token remains unknown/blocked. |
| W4 host recipe | Parse exact generated plist with `plutil -lint`, confirm arguments/cwd/PATH, 900 interval, false RunAtLoad/KeepAlive; run check-only executable from empty env in isolated state. | Replace executable with nonexistent path or strip required runtime PATH: command must fail with recorded rc. Change interval/enable self-heal: plist contract assertion fails. Phase A does not load the plist. |
| W5a | Budget check and real Codex bootstrap reading the index plus one eager and one matching scoped policy in isolated checkout. | Remove explicit read/bootstrap and assert missing markers; mere hyperlinks or nested `.claude/AGENTS.md` cannot pass the proof. |
| W5b | Public sanctioned plan/queue writer admits a verified current provider identity; runbook recovery fixture retains matching SLOT GO, effective SHA and rc before main-checkout land invocation. | Superseded/missing/spoofed identity must refuse. Without SLOT GO no fake heavy-run invocation occurs; wrong head or worktree origin cannot emit a delivery claim. |

Phase B gates: `mise run lint`, `uv run --project python pytest tests/ -x -q`,
`mise run verify`, `mise run lint-docs`, plus relevant skills parity, plist and real isolated
instruction/persistent-session probes. Record exact effective SHA and file-captured rc; annotate
NOT_RUN/blocked, and do not substitute rc 0 from a skipped audit for coverage. No automatic
production launch is part of these controls. Concurrency/identity dependencies require the
architect's premise verification before an implementation task can enable self-heal.

## Phase A design validation

This document changes no Python module or test. Python gate is not run for this documentary
change; Phase A requires `lint-docs` via the documentation specialist. Read-only source
inspection and the isolated verification plan are not implementation test results. The final
Phase A report owns strict-five/provider receipt and saved-search replay outcomes. Await those
recorded outcomes before declaring the evidence complete.
