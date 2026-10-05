# Coordinator router + standing specialists (design rev 3, 2026-10-04)

Status: DRAFT rev 3, NOT ratified; measured-majority acceptance is BLOCKED.
This is an evidence-backed interface correction, not an implemented router or
a claim that the free-text objective has been achieved. Required exact-grammar,
declared-sender, actual-helper and LLM measurements remain separate acceptance
requirements in `coord-router-freetext-2026-10-04.md`.
Rev 1 was reviewed by sdlc-team run 20bbca95
(`docs/research/kb/reports/agents/sdlc-review-coord-router-20bbca95.md`, Block 7)
and by premise-verifier (`premise-verifier-coord-router-2026-10-04.md`). Both
said "correct the spec before implementation". Rev 2 corrected those findings;
rev 3 applies the revised free-text brief and saved S0 sender-hook evidence.
Research: `coord-router-research-2026-10-04.md`. Inventory:
`coord-router-inventory-2026-10-04.md`.

## Ray's ask and the rulings that bind

Ray (2026-10-04 ~19:10 CDT, verbatim): "reduce the work the coordinator does and
have specialized agents perform the work it was doing that run in parallel
similar to the watcher so the coordinator successor handoffs reduce … find a
claude mods solution to funnel requests to the coordinator to be these
specialized agents instead so that the fanout sessions have to do less work on
who to route to … if it sends a request to the coordinator, it gets intercepted
and a decider agent or code runs instead and forwards it to the correct agent".

Binding: scheduler Q3 = "neither" (`task_plan.md:2845-2847`; no scheduler daemon
of any kind); one shipper per repo (Q:156, `coordinator_handoff.py:692-693`);
one heavy run host-wide (Q:252, `coordinator_handoff.py:692`); ruled slot order
then holds then FIFO plus load cap (Q:444; PH §8 Q1); `task_plan.md` and the
queue writer gate stay with the coordinator (`handoff_inbox.py:15-20`); python
decides, TS transports (`coordinator-handoff/hooks/register.ts:7-11`); mods are
a convenience layer, never sole enforcement (PH review a945f229 :49, :98). Q:
line anchors drift because the queue is prepended; quote the ruling text.

## What already exists — build ON it (missed in rev 1)

- **#1624 "Role-addressed session messaging"** (OPEN; hold lifted for "PR2 role
  routing after PR1", `task_plan.md:2663`). Its research recommends one JSON
  per role at `<main>/.agent/state/roles/<role>.json` written only by
  launch/retire, resolved with `mise run role -- resolve <role>`, delivery
  two-channel with `handoff-inbox` as the durable copy.
- **R-a3 PR2 "Durable coordinator identity and inbox"**
  (`sdlc-review-coordinator-roles-a3d6e816.md:206-215`): `role resolve`,
  `candidate-ready`, `promote --expected-epoch`, durable event
  append/read/ack/reconcile; owns `role_state.py`, `session_common.py`,
  `handoff_inbox.py`, `coordinator_handoff.py` changes.
- **relay-rule-r2** is the intended owner of supersession-aware resolution and
  retired-session relay. The formerly cited
  `handoff-relay-rule-r2-2026-10-04.md` is absent in this checkout; its precise
  interface is **UNBUILT / dependency unverified**, not a source premise.

**Therefore this lane does NOT own role identity, epochs, the roster, or the
durable inbox.** It owns three things on top of PR2: (1) routing POLICY —
message → role; (2) the native sender hook so lanes stop
choosing an address; (3) the SPECIALIST ROLES and their standing briefs.

## Architecture (rev 3; proposed interfaces are UNBUILT)

```
 lane (Claude) ─SendMessage(to:"coordinator", free text)─► native PreToolUse
                                                   │ pretooluse-guard.sh → hook_dispatch → Python routing branch
                                                   │ PR2 durable ingress ID → coord-router route → role
                                                   │ python: role resolve <role> (PR2) → concrete name @ epoch
                                                   ▼
                                     updatedInput.to (original body retained) ──► specialist / coordinator
 lane (codex, KB, devcontainer, unmodded Claude) ─► mise run coord-router submit (PR2 durable event append)
                                                   └─ optional native notify of the resolved session
 every route/submit = one PR2 event with message id, repo, hop count; the event log is the custody record
```

- Alias `coordinator` resolves at the SENDER. A sender without the hook gets a
  loud refusal ("no agent named coordinator"); its documented recovery is
  `mise run coord-router submit` (durable), never a guessed name.
- Fallback `route_to` is always a CONCRETE resolved name, never the alias.
- Retired-session precedence: a message from a retired coordinator to its
  successor (relay-rule-r2) is passthrough, never re-routed to a specialist.
- Repository identity is derived from verified main-checkout/session metadata
  or supplied by `submit`; ordinary lane prose need not repeat it. Missing or
  conflicting identity cannot authorize a repository specialist action.
- No keyword grammar is required of lanes. Helpers may attach authenticated
  operation metadata; raw text, mixed requests, and relays remain supported.
- Container sessions: OUT OF SCOPE v1 by Ray's ruling; they use `submit` only if
  the main checkout's state is reachable, otherwise the coordinator via Ray.

## Ranked specs — order S0 → S1 → S4 → S2 → S3 → S5 (sdlc review §5)

### S0 — saved live probe (historical Ray GO; no new sessions here)

Saved experiment: Claude Code 2.1.289, auto mode, isolated names. P2 mod
readdress was refused (`s0-probe/events.jsonl:7-8`), while direct delivery
worked (`:11-14`); P5 native full-input PreToolUse rewrite reached the receiver
(`:68-69`, `pretool.py:6-7`). See research report §8. This fixes the primary
transport choice; P4 production worktree inheritance remains unmeasured.

Original probe inventory retained for future verification scope: P1 which
event carries a local peer message
(`session.receive` vs `prompt.submit`, anthropics/claude-code#99417); P2 a bg
model's `SendMessage` raises `session.send` and `next({...e,to})` is honoured;
P2b hooks run ONCE per send (no re-entry on readdress — loop question); P3
`$.session.send` forwards vs any send cap (#94000); P4 a project
`.claude/skills/<mod>` loads in a `--bg` lane started in a linked worktree whose
branch CONTAINS the mod, and does not in one whose branch lacks it; P5 compare
PreToolUse `updatedInput` on `SendMessage` as the settings-hook alternative
(native, no mod). Each with a fail arm. No pytest/lint/image work.

### S1 — routing policy over PR2 (`coord_router.py`), DEPENDS ON PR2

1. **Objective:** ordinary free-text coordinator-bound reports reach the
   appropriate standing specialist without lanes learning grammar. Acceptance
   requires correctly routing more than 50% of every validated corpus record
   off-coordinator, with zero observed specialist misroutes on a held-out
   sample; report raw off-coordinator coverage, both error denominators, and
   abstentions separately. This is a corpus-scoped criterion, not a forecast of
   future traffic or a guarantee of zero runtime errors. It is BLOCKED until
   all required candidate tiers and the actual combined chain are measured.
2. **Files:** `python/src/dotfiles_setup/coord_router.py`, `main.py`
   (registration precedent `_add_session_mod_subcommands`,
   `main.py:1786-1800`, dispatch entry like
   `:3013-3016`), `mise.toml` (`[tasks.coord-router]` like `[tasks.session-start]`
   `:1713-1717`), `schemas/coord-router-route.schema.json`, generated model +
   `[tool.datamodel-codegen]` job in `python/pyproject.toml`,
   `tests/test_coord_router.py`.
3. **Interfaces (UNBUILT):** `coord-router submit` accepts ordinary text plus
   sender and repository metadata, allocates or validates a PR2 ingress ID,
   appends the original body before notification, and returns an event ID.
   `coord-router route` reads `{to, text, repo, sender, message_id, hops,
   envelope?}` and returns `{role, route_to, epoch, tier, reason,
   confidence, policy_version, model_revision?, passthrough, event_id}`.
   Python calls PR2 `role resolve`; it owns the entire acceptance chain.
   The native hook uses the same policy in-process rather than paying a full
   CLI startup per send. `coord-router grammar --json` exposes any optional
   compatibility grammar; rev 2 did not define a complete table.

   Proposed chain, pending measurement and ratification:
   (0) preserve non-coordinator addresses, retired→successor relays,
   recovery events, and `hops ≥ 1`; coordinator-only writer/admission
   decisions and ambiguous mixed responsibilities stay with coordinator;
   (1) accept helper envelope metadata only with validated operation/schema
   and trusted provenance, never a destination copied from gold labels;
   (2) match an optional, explicitly published legacy grammar;
   (3) accept a sender default only from an independently declared narrow
   report contract and only for that report type; a lane name is not authority
   for every message; (4) optionally classify residual free text in Python;
   (5) unsure, conflicting, invalid, timed-out or unsupported input → concrete
   resolved coordinator. No tier may grant a slot, shipping custody or queue
   writer admission merely by routing.

   **Superseded by Ray's ruling "Router agent session" (2026-10-04) and the
   evidence review `coord-router-evidence-review-2026-10-04.md` (run 5317956b):**
   tier 4 is NOT an in-hook SDK call. Python deterministic policy appends the
   message to PR2 custody and delivers residual free text to the resolved
   `router` ROLE (a slim-context standing session); the router agent forwards
   only after custody is preserved, and ambiguous cases return to the
   coordinator. The stage stays disabled/shadow until the paired offline
   replay (policy A vs A+excerpt vs A+full-body, temporal hold-out ≥150, second
   reviewer) in that review's "Smallest additional decision measurement" is
   run. The text below is retained for history only.

   ~~Tier 4 is **disabled pending evaluation**. If selected, use a Python
   Anthropic SDK call with fixed labels `{slot-arbiter, shipper,
   question-batcher, handoff-scribe, coordinator}` plus explicit `abstain`,
   a versioned prompt/model, and a validated confidence field. A self-score
   must be calibrated on held-out labels before setting an acceptance
   threshold; `$.model.classify` supplies no confidence. Auth would be native
   `ANTHROPIC_API_KEY` for this SDK route, independently verified by presence
   and a real call; neither CLI login nor Exa/Firecrawl injection proves that
   credential exists. No credential is read into the audit body.~~

   Every decision is cached by PR2 message ID with original policy/model/prompt
   revision, label, confidence (`null` for non-probabilistic tiers), reason,
   tier, repository, sender, hop and disposition in the PR2 event. Replays
   reuse the decision; notification resolves the current role epoch. Stable
   hook-call identity requires a verified public field or persisted ingress
   receipt; identical text alone is never a deduplication key. The native
   message transport is not assumed to supply `repo`, `message_id`, or `hops`.

   `coord-router return --message-id ID --reason TEXT` is a proposed one-call
   recovery: append a return event retaining the original body/ID, notify the
   current coordinator, increment the hop and bypass specialist reclassification.
   A return does not undo effects; reconcile completed/uncertain obligations
   before retrying. No specialist availability or notification receipt may
   erase the pending durable event. A queued send is not completion/ack.

   Deterministic tiers and cache hits add zero model-call cost. Classifier
   cost must report measured usage and billing basis per message:
   `(input_tokens × input_rate + output_tokens × output_rate) / 1e6`, with
   retries included. Numeric latency, threshold and cost are UNMEASURED.
   The 20-second native hook budget includes ingress, classification, role
   resolution and serialization; an enabled model call needs a shorter bounded
   deadline and measured headroom, otherwise coordinator fallback.
4. **Constraints:** no own roster/epoch/inbox (PR2's); resolves main-checkout
   state via `session_common.main_checkout` (`:183-203`), never cwd; never
   drops; unknown → coordinator (concrete name); passthrough for non-alias,
   non-coordinator `to`, for retired→successor relays, and when `hops ≥ 1`;
   dedup by `message_id`; repo required.
5. **Verification (future; not run by this docs task):** independent hand
   labels from full inbound bodies, at least 150 deduplicated messages across
   five October 3/4 coordinator sessions, positive-control delivery present,
   declared corpus/sampling bias, policy frozen before held-out evaluation.
   Report standalone and incremental-chain coverage/error for all four tiers;
   helper counterfactuals are separate from an actual helper run. Exercise the
   public CLI/native hook with isolated PR2 state: precedence, metadata absence,
   ambiguity, classifier timeout, duplicate/replay, unavailable role and return.
   **Fail arms:** remove free-text handling → correct offload falls at/below 50%;
   override coordinator-only decisions → corresponding gold errors appear;
   remove return bypass/hop bound → the same ID loops and fails; erase pending
   custody after send refusal → reconcile cannot recover the original body.
6. **Commit:** lane.
7. **PREMISES:** L `COORDINATOR_NAME_RE` —
   `python/src/dotfiles_setup/session_common.py:41`; I `main_checkout` —
   same file `:183-203`; I PR2 role/event interfaces **UNBUILT**, proposed in
   `docs/research/kb/reports/agents/sdlc-review-coordinator-roles-a3d6e816.md:206-214`;
   E classifier output lacks confidence —
   `docs/research/kb/raw/coord-router/mod-api-session-send-receive.d.ts.txt:458-476`;
   A declared sender contracts, helper provenance, calibrated threshold and
   measured-majority chain remain acceptance blockers, not available interfaces.

### S4 — standing specialist roles (briefs + launch via PR2), DEPENDS ON PR2

1. **Objective:** move D1/D2/D3/D4/D15/D16 and D9/D10 out of the coordinator
   into parallel standing `claude --bg` sessions like the watcher.
2. **Files:** `.claude/skills/coord-router/roles/{slot-arbiter,shipper,handoff-scribe,question-batcher}.md`
   (briefs), role entries in PR2's role registry; launch through
   `coordinator-handoff [--role R] launch` (relay-rule-r2 owns that file).
3. **Interfaces:** specialist names `dotfiles-<stamp>.<role>`
   (`session_common.stamped_name`); promotion via PR2 `candidate-ready` /
   `promote --expected-epoch`.
4. **Constraints:** shipper = the only main-checkout GIT writer (ship/land/
   stash/worktree custody); `task_plan.md` + queue gate stay with the
   coordinator; slot-arbiter only ADMITS through `host_lock` leases (command-
   owning, PH items 4/14) — a prose "GO" is not admission; it runs nothing
   heavy; land backlog = PH25 (shipper calls it); procedures = PH10;
   specialist death: obligations live in PR2 events (queued/applied/completed),
   reconcile effects before replay; question-batcher batches but the watcher's
   direct-to-Ray alert stays (`WATCHER.md:29`) unless Ray amends it.
5. **Verification:** a SLOT request round-trips via slot-arbiter with no new
   row in the coordinator transcript; kill the shipper mid-queue → successor
   resumes from events. **Fail arm:** grant without a lease → admission check fails.
6. **Commit:** lane.
7. **PREMISES:** P watcher template — `WATCHER.md:3`, `tick.py:94-127` (a
   revival pattern, not self-succession); A `--role` CLI shape per
   `watcher-handoff-plan-2026-10-03.md:31-38` (prefix form).

### S2 — native sender-side PreToolUse hook (Python), DEPENDS ON S1/PR2

1. **Objective:** tested model `SendMessage` calls addressed to coordinator
   enter the Python policy before delivery. S0 supports this transport choice;
   it does not establish production availability, majority coverage, SDK sends,
   or inheritance across every linked worktree. No TypeScript sender decider.
2. **Files (future implementation scope, not this docs task):**
   `.claude/settings.json` matcher, `python/src/dotfiles_setup/hook_dispatch.py`,
   the S1 policy module and public-hook tests; reuse
   `scripts/pretooluse-guard.sh`. Extend the existing Python dispatch rather
   than adding a second hook process. `hook_guard` remains the payload/deny
   helper; its existing deny-reason return type is not an `updatedInput` API.
3. **Interfaces (UNBUILT):** add `SendMessage` to the native settings matcher;
   wrapper → `hook_dispatch` → new Python route branch. Parse the full native
   payload with `hook_guard.parse_payload`, resolve verified repository and
   sender context, map native `tool_use_id` to a PR2 ingress ID, append custody,
   route/cache, resolve concrete name/epoch, emit
   `{"hookSpecificOutput":{"hookEventName":"PreToolUse",
   "updatedInput":{...original_tool_input,"to":route_to}}}`.
   This notation describes an object copy, not Python/JSON implementation.
   Preserve message text, summary and every unrelated field: `updatedInput`
   replaces the complete tool input. Omit any permission-decision override;
   existing safety denials retain precedence. Pass unrelated tools/addresses
   through their current public behavior.
4. **Constraints:** keep the current 20-second settings-hook ceiling; measure
   startup/state/fallback headroom before enabling a model tier. Classification
   timeout returns a persisted coordinator decision while time remains.
   A whole-hook timeout discards its output and normal permissions continue;
   it does **not** automatically reroute to coordinator. Pre-registered PR2
   custody, reconcile and a loud `submit` recovery are required for incomplete
   sends. If failure precedes custody, preserve the original call and expose
   the failed ingress rather than claim durable acceptance. Alias refusal
   requires `submit`; never guess a concrete name. SDK defaults (long timeout
   and automatic retries) must be explicitly bounded before any hook inference.
   Native peer `msg_id` and sender `tool_use_id` are different identities:
   their PR2 mapping remains UNBUILT. Do not assume this hook covers plugin
   `$.session.send`; S3 is a separately optional receive safety net.
5. **Verification (future, not run here):** isolated real repositories and PR2
   state, public hook stdin/stdout and actual model-send integration. Assert
   full-input preservation, unchanged denies, concrete fallback, one ingress ID,
   replay, expired hook budget and pending-custody recovery. **Fail arms:**
   remove matcher/dispatch branch → alias still fails; emit only `to` → body/
   summary preservation fails; remove durable append → refusal leaves no
   recoverable obligation; remove denial precedence → an existing denied call
   is incorrectly admitted. A production worktree-inheritance arm remains
   required; saved S0 alone does not satisfy it.
6. **Commit:** lane, only after PR2 and measured-policy acceptance; none here.
7. **PREMISES:** L matcher/20-second timeout — `.claude/settings.json:72-77`;
   L current wrapper invokes dispatch — `scripts/pretooluse-guard.sh:35-40`;
   L dispatch excludes `SendMessage` and ignores unmapped tools —
   `python/src/dotfiles_setup/hook_dispatch.py:39,50-72`;
   I payload parser/deny-only helper —
   `python/src/dotfiles_setup/hook_guard.py:1044-1073,1081-1125`;
   E full-input native rewrite —
   `docs/research/kb/raw/coord-router/s0-probe/pretool.py:6-7`, delivered receiver
   `events.jsonl:68-69`; E mod readdress refusal — same `events.jsonl:7-8`;
   I PR2 custody/role resolution and native→PR2 ID mapping **UNBUILT**;
   A production loading, timeout recovery and all-sender coverage remain
   unverified. These anchors name existing evidence, not an implemented branch.

### S3 — optional receive-side safety net (separate from native S2)

Separate transport mod, coordinator sessions only: `session.receive` / `prompt.submit` with
origin `peer`/`peer-send-message` → `route` → `$.session.send` → consume ONLY
when the result is `{isDelivered: true}` (types :11074-11094), else `next(e)`;
dedup by message id; never forward a retired-session relay. Note: it cannot
rescue an alias send (refused before delivery) — it only covers senders that
used the concrete coordinator name. If S0 P1 shows `prompt.submit` delivery,
`{drop}` leaves a notice row (#99417) — acceptable, measured.

Saved S0 shows forward-then-consume for a matching peer message and passthrough
for a non-match (`s0-probe/events.jsonl:72-79`). Production PR2 custody,
identity mapping and dedup are still UNBUILT. A consumed message must have
durable custody and a delivered forward; on either failure keep the original.
This tier may use TypeScript as transport only; Python still decides. It cannot
be counted as a measured sender-chain contribution from the saved transport
probe alone.

### S5 — saved-search `repositories` kind (independent, lowest priority)

Files: `schemas/saved-search-file.schema.json` and
`schemas/saved-search-snapshot.schema.json` (`kind` enum :22,
`additionalProperties:false` :6), both generated models, `saved_searches.py`
(explicit REST branch in `_direct` :523-534 — today non-code/issues falls to
the discussions GraphQL; `_SOURCE_KINDS` :78-82; diff on `html_url` urls
:291/:327/:623-625/:656), tests, research-sweep SKILL + mirror. Sort
`updated` top-window churn yields false GONE: page fully (≤1000 cap) or mark
`uncollectable`. Fail arm: known topic → 0 marks the run unverified.

## Delivery custody ↔ spec 04 authority-bound commands (Ray ruling 80d2f842, 2026-10-04 21:25)

Ray ruled that authority-bound command IDs go into the ph04, coord-router and
#1692 contracts. Each GO carries a command id, the receiver, the coordinator's
authority, the spec revision and the lease generation. The receiver ACKs it and
rejects duplicates and GOs from a superseded coordinator. HOLD keeps precedence.
Evidence: `.claude/worktrees/handoff-2026-10-04p/docs/research/kb/reports/agents/sdlc-unsent-prompt-review-80d2f842-2026-10-04.md` §(c).

The split was agreed with the process-hardening lane on 2026-10-04:

| Owner | Owns |
|---|---|
| Spec 04 stage 2 (process-hardening) | `GrantRecord` and `AckRecord` types, the lease-generation counter under `lock_dir()`, the durable seen-command-id set, and receiver-side validation in `slot run --grant` against an injected `resolve_current_coordinator() -> CoordinatorIdentity \| Unknown` |
| coord-router (this spec) | transport and custody of the GO and the ACK only. Both travel as PR2 durable events, routed by ROLE and never by a stale session name. The router validates nothing about authority. |
| R-a3 PR2 + relay-rule / #1692 | the real authority resolver: `role resolve coordinator` returns role, name, session_id and epoch |

Alignment (not a router-owned type; Ray rulings via process-hardening, 2026-10-04):
1. **`command_id` = PR2's `event_id`** — the opaque id PR2 assigns when it
   appends the durable event. It is the ONE identifier: this spec's "ingress
   ID" and the `message_id` field in `coord-router route` input are names for
   that same `event_id` (:62, :68, :124-128, :184), and both the router's dedup
   and 04's seen-set key on it. **No minting** (Ray): 04 stage 2 ships code
   now, and live grants start only when PR2 lands and supplies `event_id`.
2. `CoordinatorIdentity` = PR2's coordinator role binding; "coordinator
   authority" is its epoch. **Unknown authority → refuse** (Ray). Clearing a
   HOLD requires `hold_id` AND the current coordinator (Ray). Read-only checks
   run before the id is consumed, so a GO held in the #1692 window can be
   retried with the same `event_id` (Ray, "check before claiming").
3. An enqueued or delivered GO is not an ACK. Only 04's `AckRecord` closes a
   grant, and the router carries that record back to the granting role.

## Ray rulings (2026-10-04, AskUserQuestion answers, verbatim labels)

- Build order: "Build on PR2 (Recommended)".
- S0 probe: "GO, no slot needed (Recommended)".
- Asking Ray: "Batcher + watcher (Recommended)" — the watcher's direct alert stays.
- Containers: "Out of scope v1 (Recommended)".
- Classifier (2026-10-04 ~20:55): "Router agent session (Recommended)" — the
  PreToolUse hook sends any message it cannot place to a standing router
  session (the decider agent), which forwards to a specialist or the
  coordinator.
- Measure first: "Yes, measure now (Recommended)" — result in
  `docs/research/kb/reports/agents/coord-router-research-2026-10-04.md` §9:
  sonnet ≥0.80 confidence ≈11% offload / 0.6% misroute on 300-char excerpts;
  ungated 36% / 11.7%; haiku cannot run with the default session context, so
  the router session needs a slim context profile.
