# Coordinator router + standing specialists (design rev 2, 2026-10-04)

Status: DRAFT rev 2, NOT ratified. Rev 1 was reviewed by sdlc-team run 20bbca95
(`docs/research/kb/reports/agents/sdlc-review-coord-router-20bbca95.md`, Block 7)
and by premise-verifier (`premise-verifier-coord-router-2026-10-04.md`). Both
said "correct the spec before implementation"; this revision applies them.
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
- **relay-rule-r2** owns supersession-aware resolution and the retired-session
  relay (`handoff-relay-rule-r2-2026-10-04.md:103`).

**Therefore this lane does NOT own role identity, epochs, the roster, or the
durable inbox.** It owns three things on top of PR2: (1) routing POLICY —
message → role; (2) the sender-side TRANSPORT adapter (a mod) so lanes stop
choosing an address; (3) the SPECIALIST ROLES and their standing briefs.

## Architecture (rev 2)

```
 lane (Claude) ─SendMessage(to:"coordinator")─► coord-router mod (sender, session.send)
                                                   │ python: coord-router route  → role
                                                   │ python: role resolve <role> (PR2) → concrete name @ epoch
                                                   ▼
                                     readdressed `to` (engine re-judges)  ──► specialist / coordinator
 lane (codex, KB, devcontainer, unmodded Claude) ─► mise run coord-router submit (PR2 durable event append)
                                                   └─ optional native notify of the resolved session
 every route/submit = one PR2 event with message id, repo, hop count; the event log is the custody record
```

- Alias `coordinator` resolves at the SENDER. A sender without the mod gets a
  loud refusal ("no agent named coordinator"); its documented recovery is
  `mise run coord-router submit` (durable), never a guessed name.
- Fallback `route_to` is always a CONCRETE resolved name, never the alias.
- Retired-session precedence: a message from a retired coordinator to its
  successor (relay-rule-r2) is passthrough, never re-routed to a specialist.
- Repository identity travels with every message (`repo: dotfiles|knowledge-base`);
  bare `SHIP`/`MERGED #N` is rejected by the grammar.
- Container sessions: OUT OF SCOPE v1 (no Claude messaging bridge into the
  container — `.devcontainer/devcontainer.json:129`); they use `submit` only if
  the main checkout's state is reachable, otherwise the coordinator via Ray.

## Ranked specs — order S0 → S1 → S4 → S2 → S3 → S5 (sdlc review §5)

### S0 — live probe (Ray GO required; no repo code)

Throwaway `claude --bg --plugin-dir <scratch mod>` sender + receiver(s) on
2.1.289, isolated names. Measure: P1 which event carries a local peer message
(`session.receive` vs `prompt.submit`, anthropics/claude-code#99417); P2 a bg
model's `SendMessage` raises `session.send` and `next({...e,to})` is honoured;
P2b hooks run ONCE per send (no re-entry on readdress — loop question); P3
`$.session.send` forwards vs any send cap (#94000); P4 a project
`.claude/skills/<mod>` loads in a `--bg` lane started in a linked worktree whose
branch CONTAINS the mod, and does not in one whose branch lacks it; P5 compare
PreToolUse `updatedInput` on `SendMessage` as the settings-hook alternative
(native, no mod). Each with a fail arm. No pytest/lint/image work.

### S1 — routing policy over PR2 (`coord_router.py`), DEPENDS ON PR2

1. **Objective:** one deterministic answer to "which role handles this
   message", so no lane decides routing and no LLM turn is spent on transport.
2. **Files:** `python/src/dotfiles_setup/coord_router.py`, `main.py`
   (`add_subcommands`/`main` per `main.py:1786-1800`, dispatch entry like
   `:3013-3016`), `mise.toml` (`[tasks.coord-router]` like `[tasks.session-start]`
   `:1713-1717`), `schemas/coord-router-route.schema.json`, generated model +
   `[tool.datamodel-codegen]` job in `python/pyproject.toml`,
   `tests/test_coord_router.py`.
3. **Interfaces:** `coord-router route` (stdin `{to, text, repo, sender, message_id, hops}`
   → `{role, route_to, epoch, rule, reason, passthrough}`), calling PR2's
   `role resolve`; `coord-router submit` (stdin same + body → PR2 event append,
   returns event id); `coord-router grammar --json` (the table, for docs/tests).
4. **Constraints:** no own roster/epoch/inbox (PR2's); resolves main-checkout
   state via `session_common.main_checkout` (`:183-203`), never cwd; never
   drops; unknown → coordinator (concrete name); passthrough for non-alias,
   non-coordinator `to`, for retired→successor relays, and when `hops ≥ 1`;
   dedup by `message_id`; repo required.
5. **Verification:** isolated public-CLI tests: grammar rows, passthrough,
   retired precedence, dedup, hop bound, repo missing → coordinator. **Fail
   arms:** delete the SLOT row → slot test fails; drop the hop check → a
   loop test re-routes and fails.
6. **Commit:** lane.
7. **PREMISES:** L `COORDINATOR_NAME_RE` — `session_common.py:41`; I
   `main_checkout` — `session_common.py:183-203`; I PR2 `role resolve`
   (UNBUILT — dependency); A grammar vocabulary: needs a labelled sample of
   inbound lane messages (the queue records outputs, not inputs) — collect from
   transcripts before ratifying.

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

### S2 — sender-side mod (`session.send`)

1. **Objective:** every dotfiles Claude session's `SendMessage` to
   `coordinator` lands on the right role with zero coordinator tokens.
2. **Files:** `.claude/skills/coord-router/{.claude-plugin/plugin.json,hooks/hooks.json,hooks/register.ts,SKILL.md}`,
   generated mirror `.agents/skills/coord-router/SKILL.md` (`mise run skills-mirror`),
   bun harness `tests/fixtures/coord_router_hook/harness.ts` +
   `tests/test_coord_router_hook.py` (precedent
   `tests/test_coordinator_handoff_hook.py:11,36-39`). **Prerequisite:** refresh
   vendored `.claude/types/claude-code.d.ts` (2.1.277, no `SessionSendInput`)
   via `mise run schema-vendor-refresh` to ≥2.1.289, or `fnhook_gates`
   tsc fails.
3. **Interfaces:** `on('session.send')`: alias/coordinator-name `to` →
   `$.process.run(uv … coord-router route, {stdin, cwd, timeoutMs: 60_000})`
   → `next({...e, to: route_to})`; else `next(e)`. Status `router <role>` /
   `router ERROR`. `export const register: Register` (typed, `fnhook_gates.py:320-335`).
4. **Constraints:** fail-open = `next(e)` (alias then refused loudly → caller
   uses `submit`); never refuse; never key on `origin.plugin`; if S0 P5 shows
   PreToolUse `updatedInput` covers the same sends, prefer the native settings
   hook and keep the mod only for `$.session.send` coverage.
5. **Verification:** `claude plugin validate --strict`; bun harness under
   pytest; live arm from S0 setup. **Fail arm:** remove readdress → alias
   refused.
6. **Commit:** lane.
7. **PREMISES:** I `session.send` re-judge — types 2.1.289 :4208-4219,
   :11006-11035; P `$.process.run` → python — `coordinator-handoff/hooks/register.ts:116-131`;
   A loads in every lane (S0 P4); A raised for bg model sends (S0 P2).

### S3 — receive-side safety net (only if S0 justifies it)

Same mod, coordinator sessions only: `session.receive` / `prompt.submit` with
origin `peer`/`peer-send-message` → `route` → `$.session.send` → consume ONLY
when the result is `{isDelivered: true}` (types :11074-11094), else `next(e)`;
dedup by message id; never forward a retired-session relay. Note: it cannot
rescue an alias send (refused before delivery) — it only covers senders that
used the concrete coordinator name. If S0 P1 shows `prompt.submit` delivery,
`{drop}` leaves a notice row (#99417) — acceptable, measured.

### S5 — saved-search `repositories` kind (independent, lowest priority)

Files: `schemas/saved-search-file.schema.json` and
`schemas/saved-search-snapshot.schema.json` (`kind` enum :22,
`additionalProperties:false` :6), both generated models, `saved_searches.py`
(explicit REST branch in `_direct` :523-534 — today non-code/issues falls to
the discussions GraphQL; `_SOURCE_KINDS` :78-82; diff on `html_url` urls
:291/:327/:623-625/:656), tests, research-sweep SKILL + mirror. Sort
`updated` top-window churn yields false GONE: page fully (≤1000 cap) or mark
`uncollectable`. Fail arm: known topic → 0 marks the run unverified.

## Ray rulings (2026-10-04, AskUserQuestion answers, verbatim labels)

- Build order: "Build on PR2 (Recommended)".
- S0 probe: "GO, no slot needed (Recommended)".
- Asking Ray: "Batcher + watcher (Recommended)" — the watcher's direct alert stays.
- Containers: "Out of scope v1 (Recommended)".
