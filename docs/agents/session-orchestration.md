---
name: session-orchestration
description: Shared Claude and Codex coordinator recovery and delivery runbook.
---

# Session orchestration — Claude and Codex

Use this runbook when recovering a coordinator, running a specialist lane,
watching the fleet, transferring ownership or handing work back. It covers the
canonical dotfiles and knowledge-base main checkouts and their registered
worktrees. Repository membership comes from Git topology, not session names.
Read [the policy index](codex-policy-index.md), its eager rules and applicable
scoped rules first. Preserve the CLAUDE.md import stubs and nested AGENTS rules.

## Phase B1 inventory and B2a authority

B1 supplies registry/cards, issue-plan **preview**, digest, policy bootstrap and
this runbook. B2a adds explicit Codex claim/release and provider-qualified writer
authorization for `handoff-inbox plan-apply`, `queue-append`, `inbox-edit` and
card snapshots (`lane-cards --write` and `coordinator-handoff snapshot-cards`).
The newest coordinator identity must authorize each write; a handoff or registry
display alone never grants authority. Ordinary inbox append and read-only recovery
remain available. Never export a Claude identity to pass a Codex writer check.

W4 automation remains deferred beyond B2a: `takeover-check`, a disabled launcher,
provider liveness/ownership checks, watcher/session-start/launchd integration,
900-second checks, and any self-heal enablement. Do not invoke a proposed W4
command as though it were installed. Automatic W4 coordinator launch remains OFF
until its separate prerequisites and explicit ruling are satisfied.
Process-hardening and
[credit fallback #1577](https://github.com/ray-manaloto/dotfiles/issues/1577)
are dependencies, not work authorized by this runbook. See the
[B1 spec](../specs/codex-takeover-phaseB1-spec.md),
[B2a spec with r2/r3 amendments](../specs/codex-takeover-phaseB2a-spec.md) and
[adopted design](../specs/codex-takeover-phaseB-design.md).

## Roles and shared state

| Role | Responsibility | Authority boundary |
|---|---|---|
| Architect/coordinator | Recover evidence, settle decisions, maintain plan/ship queue, grant SLOT GO, dispatch and accept lane reports | One reconciled owner; current public writer checks still govern every change. |
| Specialist lane | Work in a registered isolated worktree within its allowlist; persist findings and return effective SHA, rc and controls | No plan rewrite, independent slot grant or takeover by inference. |
| Watcher | Read WATCHER.md every tick, inspect newest coordinator by startedAt, report blockers/merges and uncertain ownership | Read-only; no implicit coordinator launch or lane mutation. |
| Shipper | Run gated ship/land for one repository from its main checkout | One shipper per repo; matching host SLOT GO and queue order required. |
| Successor | Reconcile handoff against transcripts, live runs and durable receipts before retiring predecessor | Registry display precedence never grants authority; the provider-qualified writer check decides it. |

Live state lives in each canonical main checkout: `.agent/lanes/`,
`.agent/state/session-registry/registry.json`, `.agent/plans/`, lane inboxes and
`.agent/plans/main-checkout-ship-queue.md`. Tracked handoffs live in
`docs/handoffs/`. Live cards are not clone-durable; snapshot their content and
source evidence into the tracked handoff before transfer.

## Recover before dispatching or taking ownership

1. Resolve both repositories' main checkouts and registered worktrees. Read the
   predecessor's full handoff, relevant transcript, task plan, every lane inbox,
   ship queue, registry cards, SDLC `settlement.json`, output/log paths and live
   PIDs. Reconcile typed but unsubmitted text before sending or clearing it.
2. Run the public read-only inventory and compare its counts with
   `claude agents --json --all`:

   ```bash
   mise run lane-cards -- --json
   mise run lane-cards -- --issue-plan
   ```

   Both support repeated `--repo-root <absolute-root>` when explicit roots are
   needed. Exit 0 means complete; exit 2 means unknown/partial inventory and
   still prints available evidence. A failed inventory call never proves an
   empty fleet. Preserve unknowns and omissions; do not overwrite prior cards
   with a failed census. No B1 issue-plan invocation writes GitHub issues.
3. Compare each announced SHA with the actual gate's effective SHA and real
   per-command rc. Dashboard labels, return codes without outputs, and a merged
   PR alone do not prove installed delivery. Record corrections before claiming
   completion or ownership. Read provisional/failed research routes as gaps.
4. Reconcile all coordinator/watch successor chains and live predecessors.
   Keep raw state separate from process liveness: `done`, `stopped`, age or an
   absent rollout never proves death. A nameless row remains keyed by session
   ID with unknown role; never invent a coordinator from it.
5. Adopt recorded safe-to-die runs or wait for them to finish. `harness-output:`
   logs have no rc file: wait for the PID exit and read output. With no readable
   log, record that omission; no elapsed-time or `rc=141/143` completion claim.
6. If ownership, identity, census or logs conflict, stop affected authority work
   and report the exact contradiction. A Codex reader can assemble recovery
   evidence and an inbox report before claiming; only the currently authorized
   provider-qualified coordinator applies plan/queue changes.

## Lane cards and issue intentions

The sanitized session key determines `.agent/lanes/<key>.md`; duplicate names
get stable provider/session suffixes. Registry identity is `provider:session_id`.
Same-role coordinator/watch chains have one summary while retaining every
member ID, predecessor edge and observed state. Ordinary named lanes retain
individual identity unless verified lineage connects them. Newest started_at
plus deterministic ID tie-break selects a display member, not a writer.

A card carries canonical repo/worktree paths, branch/head SHA, member IDs,
raw/normalized states, liveness and its probe timestamp, done/open task evidence,
research questions, blockers, suggestions, issue links, source timestamps and
omissions. A card is evidence for reconciliation, not authorization.
`lane-cards --write` uses the same provider-qualified coordinator authorization.
Its `--jobs-dir` and `--claims-dir` flags isolate the authority stores for tests.
The registry preserves earlier evidence on collection failure and archives
stale card state rather than treating deletion as proof of completion.

`--issue-plan` emits `reuse`, `create` or `blocked` intentions and task-plan delta
text. Existing stable markers or issue references win over changed issue titles;
failed issue reads block creation intentions. Done-only sessions get no issue
intention; eligible unresolved coordinator/watch members collapse to one chain
intention. The coordinator reviews and applies deltas through sanctioned plan
interfaces and runs `mise run plan-attest`; lanes never rewrite the whole plan.
B1 has no issue application command or GitHub writes. B2a adds coordinator writer
authorization, without an issue application command.

## Queue, SLOT GO and fan-out

Read the authoritative main-checkout ship queue before heavy work. Preserve
its order, held decisions and already-running gates. A stale CURRENT heading,
silence, elapsed time, or another lane's release is not a matching grant.

1. A lane sends `SLOT REQUEST <lane> <repo> <head SHA> <commands>` through its
   approved communication surface or `mise run handoff-inbox -- append`.
2. The authorized coordinator records a matching `SLOT GO` for that lane,
   repository, SHA and commands. Permit one heavy host gate at a time, with one
   shipper per repository. Remote CI may overlap the next lane's permitted
   local gates; this does not permit concurrent heavy host runs.
3. Run only granted commands, bound long runs and capture outputs and real rc
   in files. Never pipe a gate into a pager or infer its rc from a wrapper.
4. Report each command's effective SHA, rc, evidence path and omissions, then
   `SLOT RELEASED`. Re-request if the head or command set changes. Record
   NOT_RUN for any gate lacking permission; do not silently drop it.

Dispatch independent specialists in parallel with explicit ownership and file
allowlists. Share the same ratified spec, dissent clause and realistic fail-arm
contract. Persist each returned report while it is fresh; wait for all spawned
specialists and synthesize blockers before advancing. No specialist report
replaces the architect's verification of real gate outputs and delivery.

## Main-checkout ship and land

Keep implementation edits in registered isolated worktrees under
`<main>/.claude/worktrees/`. Ship and land dotfiles from its **main checkout**
through `mise run ship` and `mise run land -- <PR#>` under matching SLOT GO.
One exception, enforced in code: a docs-only change may ship from a linked
worktree, because `pr._ship_preflight` refuses a linked worktree only when
`needs_full_sync(paths)` is true (`python/src/dotfiles_setup/pr.py:612-627`). This
is the same exception `/coordinator-handoff` §1 uses for its handoff copy.
Do not bypass a writer guard, switch branches during someone else's ship,
perform raw push/merge, or use a worktree redirect to write main files.
Review/stage formatter output before validation; all applicable checks need real
rc 0 before committing/shipping. Preserve an exact gated SHA through delivery.

Knowledge-base shipping follows that repository's policy and existing human-only
rulings. A dotfiles takeover does not grant permission to deliver another repo.
After land, verify the live checkout/install identity and remaining gates; report
observed merge, installed delivery and unresolved blockers separately.

## Claude to Codex takeover

The outgoing Claude coordinator writes a tracked handoff with settled decisions,
queued questions, ship queue, SLOT grants, live heavy-run census and exact state
path. Run the existing card snapshot before shipping the handoff:

```bash
mise run coordinator-handoff -- snapshot-cards --handoff <absolute-tracked-handoff>
```

Use repeated `--repo-root <root>` to include explicit managed roots. The snapshot
embeds fresh registry JSON and card content in a replaceable handoff section;
an inventory/authorization failure is a blocker, not an empty snapshot.
The [coordinator-handoff skill](../../.agents/skills/coordinator-handoff/SKILL.md)
remains the canonical Claude launch/retire workflow. It launches Claude explicitly;
B2a adds no Codex launcher. `snapshot-cards` accepts `--jobs-dir` and
`--claims-dir` for isolated authority stores.

A separately authorized persisted Codex session reads the index/runbook, performs
the recovery above, then claims using its real, nonempty `CODEX_THREAD_ID` with
`CLAUDE_CODE_SESSION_ID` absent:

```bash
mise run handoff-inbox -- coordinator-claim \
  --name <dotfiles-unique-name.coordinator> --supersedes <current-newest-coordinator-name>
```

The name must match the coordinator naming rule and must not already belong to
a Claude job record or another claim. If no coordinator exists, pass
`--supersedes none`. Read and reconcile the current coordinator before claiming;
`--supersedes` is a compare-and-swap expectation, rechecked under the claims lock.
A mismatch refuses a blind/stale claim, including a stale re-claim after hand-back;
two racing claims with the same expectation have one winner.

Claims live in the canonical main checkout's gitignored
`.agent/state/coordinator-claims/coordinator-claims.json`. `--claims-dir <dir>`
overrides that directory; `--jobs-dir <dir>` overrides the Claude job store.
Every CLI writer resolves and passes the claims directory explicitly. The shared
helper's `claims_dir=None` preserves isolated Claude-only direct-call behavior.
Corrupt claims fail closed and are never silently reset.

Writer checks select the maximum `(createdAt, provider, id)` across Claude
coordinator jobs and active Codex claims, then match the caller's provider and
ID. Claude uses the record's `sessionId`; Codex uses the claim's `threadId`.
The deterministic provider/ID tie-break means equal timestamps do not authorize
both callers. Job `state` is ignored because `done` may be a live idle session.
Authorization runs before input reads and again under each target's write lock.

Claims are atomic replacements under the claims lock; authorization reads them
without that lock to avoid target/claims lock-order inversion. Claude job creation
sits outside the claims lock: a Claude record created between a claim's check and
write can lose to the claim's later timestamp. The r3 amendment accepts this race.
This mechanism prevents mistakes; caller-supplied identity variables mean it is
not access control or proof of liveness.

Do not retire the predecessor until live runs are settled/adopted and successor
identity and authority have been reconciled. Use
`mise run coordinator-handoff -- retire --state-dir <exact-dir>` through the
existing authorized workflow; no bare `claude stop` or agent-admin shortcut.

## Codex to Claude hand-back

The outgoing authorized Codex coordinator prepares its tracked handoff and card
snapshot before transfer, preserving provider/session identity, source timestamps,
recovered cards, actual gate SHAs
and rc, held SLOT/queue decisions, open questions and failed/provisional research.
Append a hand-back request through the existing public inbox. A Claude coordinator
with a newer `createdAt` automatically becomes the authorized writer and the Codex
claim is refused on subsequent plan/queue/card writes. Reconcile the incoming
record's actual provider/session identity; do not fabricate a Claude launch record.
The outgoing Codex owner retires its own claim explicitly, even after supersession:

```bash
mise run handoff-inbox -- coordinator-release
```

Release uses the same `--jobs-dir`/`--claims-dir` overrides, requires an unambiguous
Codex identity with its own existing claim, and retains the retired record.
A retired claim never authorizes a write. Release does not terminate a session.

The incoming Claude coordinator explicitly reads the same policies, handoff,
transcript, inboxes, queue, cards, settlement and live logs, then reconciles owner
identity before applying deltas or granting slots. Confirm the outgoing Codex
session's disposition through supported provider evidence; the existing Claude
retire command is not a Codex termination adapter. B2a does not authorize
automatic restart, cross-provider retirement, identity spoofing or self-heal.

## Handover (both directions)

At every milestone, Claude and Codex keep the tracked
[START-HERE pack](../handoffs/codex-takeover-START-HERE.md), its raw lane snapshot
and live cards current. Card writes still require the newest provider-qualified
coordinator. A specialist proposes updates through the inbox; a partial census
retains its omissions and never erases earlier evidence. Record what is doing,
done and pending, issues, open questions, exact gate SHAs and rc, current SLOT
grants, live heavy runs and the canonical main-checkout state paths. Either
provider follows the same policy/read order and reconciliation before taking over.

Ray's [Round 6 ruling](../specs/codex-takeover-2026-10-05.md#round-6--claude-at-95-via-codex-sdlc-team-answered-1150-cdt)
authorizes a Claude availability probe for this hand-back case despite W4's
general default-OFF launcher. At milestones, at most once every 30 minutes,
the Codex coordinator runs exactly one cheap `claude -p "reply OK"` invocation
under a hard deadline and records its real rc and output. A polling wrapper
that retries failed commands is not a one-shot probe. Timeout or nonzero rc
means retain ownership and record the failure. Success establishes availability,
not a new coordinator's identity or authority.

On probe success, refresh START-HERE and cards, reconcile the existing Claude
coordinator records against a real process census, and request the supported
successor launch through the existing coordinator-handoff path. Unknown liveness
is a blocker; recorded `done` or `stopped` does not prove no live coordinator.
One live Claude coordinator or a recorded start prevents another launch. Append
the hand-back record through `mise run handoff-inbox -- append --lane codex-takeover`.
The incoming coordinator reads the same pack, inboxes, queue and raw evidence;
after supported successor identity/authority reconciliation, retire the outgoing
Codex claim with `mise run handoff-inbox -- coordinator-release`.

**Current manual runbook blocker:** the existing
`mise run coordinator-handoff -- launch --handoff <absolute-path> --old-session <full-Claude-UUID>`
requires a predecessor UUID resolving to a Claude coordinator job. It has no
Codex predecessor adapter. Its duplicate guard is per predecessor, rather than
a global live-Claude census. A Codex thread ID cannot use this interface, and
a historic Claude identity must not be substituted. Phase C therefore supplies
this manual reconciliation procedure and records the launch seam as BLOCKED;
it does not implement or claim ready automatic hand-back. Release before this
blocked launch would leave no confirmed successor. Preserve the Codex claim
until the valid transfer can be reconciled, and report the release-order conflict
with [Phase C C4](../specs/codex-takeover-phaseC-handover-spec.md#2-work-items-in-order).

When the supported path becomes available, its rc 0 means started and recorded;
rc 2 means refused; rc 3 means failed; rc 4 means STARTED but unrecorded and
**must not be relaunched**. Follow the
[coordinator-handoff skill](../../.agents/skills/coordinator-handoff/SKILL.md)
and preserve its durable launch/retirement receipts. This protocol performs no
provider spoofing, historical identity substitution, automatic W4 enablement
or resumption of held meta/orchestration lanes.
