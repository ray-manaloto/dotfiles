# Coordinator router — research + design (lane `coord-router`, 2026-10-04)

Ray's ask (verbatim, 2026-10-04 ~19:10 CDT): reduce coordinator work by moving
it to specialized agents running in parallel like the watcher; find a Claude
Code "mods" solution so a message addressed to the coordinator is intercepted
and a decider (agent or code) forwards it to the correct specialist; search
GitHub issues/PRs/discussions and saved searches.

Status: IN PROGRESS — written incrementally.

## 1. Native mechanisms (step 00: offline `$CC` corpus, claude 2.1.289 installed)

| # | Mechanism | Finding | Source |
|---|---|---|---|
| N1 | Cross-session messaging | Same-machine delivery over a per-session Unix socket; `SendMessage` by name; receiver reads between tool calls or a new turn starts when idle. Plain text only. | `raw/coord-router/cc-cross-session-messaging.md` :68-89 |
| N2 | Inbound controls | `crossSessionInbound` = accept/hold/refuse only — a filter, NOT a router. No hook event fires on an inbound peer message (hook event list `hooks.md` :1120-3429 has none). | same :210-244; `$CC/hooks.md` |
| N3 | **Sender-side intercept** | `PreToolUse` `updatedInput` "replaces a tool's arguments before it runs" and permission rules are re-evaluated against the returned input. A `PreToolUse` hook matched on `SendMessage` can rewrite `to: <coordinator>` → `to: <specialist>`. This is the native intercept point. | `raw/coord-router/cc-hooks-pretooluse-decision.md` (`hooks.md` :1800-1842, :1060) |
| N4 | Inbox socket for scripts | `CLAUDE_CODE_MESSAGING_SOCKET`/`_TOKEN` exported to hooks + Bash; a script can post to its OWN session's socket (own-child rule). Posting to ANOTHER session's socket is not documented as supported. | same :261-295 |
| N5 | `notify_when_idle` | Main conversation only, one-shot, same machine. Useful for a router/specialist waking the coordinator only on idle. | same :91-118 |
| N6 | Sub-agent / bg session replies | A reply to a subagent-authored cross-session message lands in the PARENT session's main conversation. | same :201 |
| N7 | **Mod `session.receive` (receiver-side intercept)** | Fires "when a delivery reaches the session (... a peer's message ...) before it is queued". `return { consumed: reason }` → "not queued, not written to the transcript and never reaches the model". Matchable on `origin: { kind: 'peer' }`. **This is exactly Ray's "intercepted, then forwarded" shape, at zero coordinator tokens.** | `raw/coord-router/mod-api-session-send-receive.d.ts.txt` :47-58, :98-220 (types `claude-code.d.ts` 2.1.289 :4185, :10789) |
| N8 | Mod `session.send` + `$.session.send` | Sender-side dual: readdress `to` with `next({...e, to})` (re-judged), or refuse. `$.session.send({to, text})` lets a mod forward; receiver sees `origin.plugin` — a CLAIM, "never key a guard on it". | same :10-23, :72-82, :268-404 |
| N9 | `$.model.classify(text, labels)` / `$.model.complete({model:"haiku"})` | In-mod LLM decider for messages the deterministic pre-filter can't place. | same (appended, types :2489-2560) |
| N10 | Mod loading | A skills-dir plugin (`.claude/skills/<name>/` with `.claude-plugin/plugin.json` + `hooks/hooks.json`) auto-loads and hot-reloads; `CLAUDE_CODE_PLUGIN_DIRS`/`--plugin-dir` alternatives. | plugin-authoring `reference.md` :68-72 |

### Repo precedent (REUSE)

`.claude/skills/coordinator-handoff/hooks/register.ts` already ships a mod in
this repo with the exact architecture the router needs: a cheap TS pre-filter +
visible status line, and **python owns every judgement**
(`dotfiles-setup coordinator-handoff decide`, role check against the bg job
record, fail-as-value never throw). Siblings: `install-doctor`, `plugin-health`,
`session-start` skill-plugins. A `coord-router` skill-plugin is a fifth instance
of an existing pattern, not new machinery.

## 2. GitHub sweep (anthropics/claude-code; `gh api search/issues`, control arms run)

Control: `repo:anthropics/claude-code "PreToolUse"` → 3594 (must-hit); fresh
nonce → 0 (absent). Discussions: `has_discussions=false` on the repo (API), so
no discussion search applies. Raw: `raw/coord-router/gh-issue-search-1.txt`,
bodies `raw/coord-router/gh-issue-bodies.txt`, code search `raw/coord-router/gh-code-search.txt`.

| Issue | State | Why it binds the design |
|---|---|---|
| #99417 | open (2026-10-04, 2.1.288) | **CONTRADICTS N7 in one path**: a reporter saw a *local* peer ping arrive via `prompt.submit` (origin `peer`), NOT `session.receive`; there the only refusal is `drop`, which leaves a visible "Prompt dropped by a hook" row. → the router must hook BOTH events and the delivery path is a **premise to probe live** before any spec ships. |
| #94000 | open | A cross-session **send cap (10 per human input)** — measured on Desktop's `ccd` tool. Whether CLI `SendMessage`/`$.session.send` shares it is UNVERIFIED; an autonomous router forwarding all coordinator mail would hit any such cap first. Probe. |
| #89462 | open | No durable addresses / store-and-forward: names rotate on restart. Our coordinator **renames on every successor handoff** → fan-outs must address a STABLE alias, not the coordinator's dated name. |
| #91105 | open | `SendMessage` can return success and drop silently → the router needs a delivery ledger + an ack, not trust in the receipt. |
| #97220 | open | Hooks can't read the session display name → identify roles from our bg job record (coordinator-handoff precedent), not from the name. |
| #99049 | open | No `claude send` CLI; a non-model sender costs a paid `claude -p` turn → forwarding must happen INSIDE a mod (`$.session.send`), not a script. |
| #91870 | open | "Claude Mods" = function hooks, GA'd ~2026-10-01; built-in mod sources at `anthropics/claude-code/mods/` (agents-md, diff, sec-default, telemetry) — none is a router. |
| #76727 | open | Field report on many independent sessions on one repo: "a deny that NAMES the exact command causes self-correction" — supports a sender-side `session.send` refusal whose reason names the right specialist as the fallback. |

GitHub code search: no public repo implements a `session.receive` router
(query noisy; `ericbuess/claude-code-docs` mirrors the mods API doc only).
**No prior art to adopt — the native primitive exists, the router does not.**

## 3. Design direction (pre-inventory, for the sdlc-team review)

**Primary: sender-side readdress in every session of this repo.** A skills-dir
mod (`.claude/skills/coord-router/`, auto-loaded by every dotfiles session per
N10, same as `coordinator-handoff`) hooks `session.send`: when `to` is the
STABLE alias `coordinator` (or any `*.coordinator` dated name), it asks python
(`dotfiles-setup coord-router route`) for the specialist and calls
`next({ ...e, to: <specialist> })`. The engine re-judges the new `to`. Gains:
the coordinator model never spends a token; no send cap is consumed on the
coordinator (#94000); fan-outs address one alias forever (#89462 rename
problem); no `consumed`/`drop` ambiguity (#99417).

**Safety net: receiver-side in the coordinator.** `session.receive` (origin
`peer`) AND `prompt.submit` (origin `peer`/`peer-send-message`, per #99417)
forward via `$.session.send` + `{consumed}` / `{drop}` for senders without the
mod (knowledge-base sessions, codex lanes posting through a Claude wrapper).

**Decider = python, mod = transport** (coordinator-handoff precedent): a
deterministic grammar first (`SLOT <lane> GO?`, `SHIP <PR|branch>`,
`RELAY to <x>`, `RAY? …`), then `$.model.classify` (haiku) only for
unparseable text, then fallback to the coordinator itself (never drop).

**Roster**: each standing specialist is a `claude --bg --name dotfiles.<role>`
launched like the watcher; the launcher writes `.agent/state/coord-roster.json`
(role → name, pid, started) because hooks cannot read display names (#97220).
A dead specialist (pid gone) ⇒ route falls back to the coordinator, logged.

**Delivery ledger**: every routed message appended to
`.agent/state/coord-router/ledger.jsonl` (ts, from, alias, routed_to, kind,
isDelivered, reason) — the answer to #91105 silent drops, and the coordinator's
handoff shrinks to "read the ledger tail".

Open premises to PROBE before any implement spec (all need a live 2-session
test, i.e. Ray's hot-reload consent or a `--plugin-dir` bg session):
P1 local peer delivery path: `session.receive` vs `prompt.submit` (#99417);
P2 `session.send` hook fires for the MODEL's `SendMessage` in a bg session and
`next({...e,to})` re-routes; P3 whether `$.session.send` counts toward any send
cap (#94000); P4 skills-dir mods load in `claude --bg` sessions.
P4 is **CONFIRMED by precedent**: the skills-dir `coordinator-handoff` mod's
`session.measure` hook auto-fired in bg coordinator sessions
(`docs/handoffs/session-2026-10-03p.md:38`, `session-2026-10-04j.md:91`).

## 4. Coordinator duty inventory (Explore lane, verbatim at `coord-router-inventory-2026-10-04.md`)

19 duties (D1–D19). Headline numbers: 13 coordinator names on 10-04 (address
changes every ~1–2 h); 13 handoffs = 1,464 lines in one day; ~38% of handoff
lines exist only because the coordinator holds state, +18% is errata from
writing from memory. Latest ruling (2026-10-04 ~19:15): scheduler "neither" →
standing specialists + mods router (`task_plan.md:2845-2847`). Must coordinate
with R-a3 PR2 (roles/epochs/durable inbox), R-a3 PR3, relay-rule-r2.

## 5. Full Claude Mods capability catalogue (claude 2.1.289, `claude-code.d.ts`)

Ray asked (2026-10-04): "review all available changes that a claude mods
function can do". Every event in the engine's event map, first doc lines
verbatim (extracted from the types file, lines ~3880-4420):

| Event | What a hook can do |
|---|---|
| `ui.resolve` |  |
| `ui.press` | Fires when a `Button` a render hook drew is pressed on a surface; `e` is `{ plugin, element, component, surface }`, `element` the button's `key`. `next(e)` runs the hooks beneath, then core: the element's own `onPress` closure, in its plugin's environment, resolving to `{ element }`. Return |
| `ui.input` | Fires when an `Input` a render hook drew changes or is submitted; `e` is `{ plugin, element, component, surface, kind, value }`. `next(e)` runs the hooks beneath, then the element's own `onInput` or `onSubmit` with `e.value` as the chain left it, resolving to `{ element, |
| `ui.select` | Fires when a `Select` a render hook drew is picked from; `e` is `{ plugin, element, component, surface, value }`. `next(e)` runs the hooks beneath, then the element's own `onSelect` with `e.value` as the chain left it, resolving to `{ element, value }`; |
| `ui.message` | Fires when a `Client` THIS plugin drew posts from its surface module (`surface.post(data)`); only this plugin's hooks see it. `next.origin` names `client`: `data` came from code. Core answers `{}`; `next({ ...e, data })` rewrites the data; `{ props }` hands the posting |
| `ui.fault` | Fires when a `Client` THIS plugin drew failed on a surface: its module did not load, its drawing failed, or its code failed after it had drawn. Only this plugin's hooks see it; `e.phase` says when, `e.reason` why. Observe only: core answers `{}`. The engine then draws that site again, |
| `ui.scroll` | Fires before a site's window moves: the person's wheel or scroll keys on a `Pane` body or the `AbovePrompt` band, at its edges too; `$.ui.scroll`. `next(e)` moves it to `e.offset` and draws: `{}`; `next({ ...e, offset })` elsewhere; no `next` (`{}` or `{ deny }`) leaves it undrawn, so a hook |
| `ui.focus` | Fires before a site's focus ring moves: the person's Tab, arrows or click in a `Pane` or the band; an `autoFocus` element taking it; `$.ui.focus`. `next(e)` lands it on `e.element` (absent: one of the engine's stops) and draws: `{}`; `next({ ...e, element })` on another of `e.plugin`'s; no |
| `agent.offer` | Fires when the engine offers an agent type to the model, in the agent listing and again at dispatch; `next(e)` resolves to `{ isOffered: true }`. Return `{ isOffered: false }` to keep the type out of the listing and refuse its dispatch. A hook that fails passes it through. |
| `agent.spawn` | Fires when the Agent tool is about to start a subagent, everything decided and its model not yet resolved. `next(e)` resolves to `{ model }`. Return it, `next({ ...e, model })`, `{ model }` of your own (an alias resolves like the tool's parameter), or |
| `prompt.submit` | Fires when a prompt is submitted, before the turn starts. `next(e)` runs the hooks beneath and the UserPromptSubmit settings hooks. Rewrite with `next({ ...e, text })` (the user message on screen follows) or stop it with `{ drop: reason }`; a broken plugin never blocks a prompt. |
| `prompt.fill` | Fires when a text is about to be put in the prompt box as the person's draft (a plugin's `$.prompt.fill`); `next(e)` writes it by `e.mode`. `replace` over the draft, `append` after it, `insert` at the cursor; rewrite `text` or `mode` going down, or answer `{ isFilled: false }` |
| `prompt.suggest` | Fires when a text is proposed as the prompt box's dim suggestion, Tab to take: the engine's guess after a turn, or a plugin's `$.prompt.suggest`. `next(e)` shows it: `{ isShown }`. Rewrite with `next({ ...e, text })`, or answer `{ isShown: false }` without `next` to drop it; core answers |
| `prompt.edit` | Fires when the person edits the main prompt box: a key the editor took as an edit, or a paste; `next(e)` resolves the box the editor shows. `e` is the draft before and the splice (`start`, `end`, `inputText`); a burst of keys is one edit. Rewrite `inputText` going down or the box |
| `prompt.section` | Fires once per named section of the system prompt, when the engine assembles it; `next(e)` resolves to `{ text }` as core computed it. `e.name` is the section's id, on every model the one `prompt.compose` lists. Cached until `$.ui.invalidate("prompt.section")`: an unstable |
| `prompt.context` | Fires once per conversation, when the engine computes the context blocks its first user message carries; `next(e)` resolves to `{ blocks }`. Append, drop, reorder or rewrite with `next({ ...e, blocks })`; the engine renders what comes back, in order, until |
| `prompt.compose` | Fires when the engine renders a system prompt; `next(e)` resolves to `{ sections }`, each `{ id, text, scope }`, in the order they are sent. The ids depend on the prompt composed (`lean`, `bare` in `e.traits`): read them off `next(e)`. Append (as `session`), replace, reorder or drop; a list |
| `prompt.attachment` | Fires once per message the engine injects for the model on its own (a reminder, a mode transition, a mentioned file), as a request carries it. `next(e)` resolves to `{ text }`; `{ text: null }` leaves it out. The answer holds per attachment for the process (asked again on resume or |
| `tool.describe` | Fires once per tool, when the engine first renders the tool's schema in a session; `next(e)` resolves to `{ description, isDeferred? }`. Cached for the session until `$.ui.invalidate("tool.describe")`: an unstable answer spends the model's prompt cache. An explicit `isDeferred` |
| `command.run` | Fires when a slash command is about to run (`/name args` typed, or a plugin's `$.command.run`); `next(e)` resolves to `{ text }`, its output. Core is the engine's command (a registered one has none). Rewrite `args` with `next`, or return `{ text }` without it to answer in its place; one |
| `command.describe` | Fires once per command, when the engine lists it for the typeahead and `/help`; `next(e)` resolves to `{ description, argumentHint, isHidden }`. Listed answers are cached for the session until `$.ui.invalidate("command.describe")`. A hook that fails passes it |
| `config.set` | Fires when a `/config` row is about to change, from the menu or a plugin's `$.config.set`; `next(e)` resolves to `{ value }` once written. Return `{ deny: reason }` to leave the row as it is (the menu says why), or `next({ ...e, value })` to clamp it; a value of the wrong kind for |
| `config.describe` | Fires once per `/config` row, when the menu lists it and for `$.config.list`; `next(e)` resolves to `{ label, description, isHidden }`. Relabel, re-describe or hide with `next({ ...e, isHidden: true })`; the answers are cached until `$.ui.invalidate("config.describe")` or the |
| `telemetry.log` | Fires when a record is about to be logged to the destination `e.to` names: a built-in's `$.telemetry.log`, or the engine's own events. `e.to` is pinned: a hook rewrites what the record carries, never where it goes. `next(e)` resolves `{ value: undefined }`; `{ deny }` rejects the |
| `telemetry.mark` | Fires when one use of a feature is marked (`$.telemetry.mark`), as the CLI's own feature events mark one; always for `anthropic`, no `to`. `next(e)` resolves `{ value: undefined }`; `{ deny }` rejects the caller. The engine does nothing with a mark: the built-ins hooked here do. |
| `skill.prompt` | Fires when the engine expands a skill's prompt for the model (`/name`, the Skill tool, a preload); `next(e)` resolves to `{ text }` as computed. Return `{ text }` with the text the model reads instead. A hook that fails passes it through. |
| `attribution.text` | Fires when the engine composes a git text the model is to write (`kind`: `commit`, `pr`, `exemption`, `remedy`); `next(e)` resolves to `{ text }`. Return `{ text }` with the text the model reads instead. A hook that fails passes it through. |
| `session.start` | Fires once per process for each loaded plugin, before the first prompt, then once per fresh load of one (never `/clear`); `next(e)` is `{ cwd }`. Observe. The first is awaited: a `$.tool.register` is listed by turn one. A later one runs its hooks alone: an enable, a worker respawn, or a reload |
| `session.receive` | Fires when a delivery reaches the session (a relay's event, a peer's message, a Remote Control prompt), before it is queued; `{ text }`. Rewrite with `next({ ...e, text })`, or return `{ consumed: reason }` to take it: nothing is queued, shown or read by the model. `origin`, |
| `session.append` | Fires once per row a conversation of this session keeps (a prompt, a response block, a tool result, a notice), before it is stored. `next({ ...e, message })` rewrites `content`: stored and sent after. The screen, an SDK stream or Remote Control may show the row just before its |
| `session.send` | Fires when a plain-text message is about to leave this conversation for another agent or session (the SendMessage tool, or `$.session.send`). `e.origin` says who sends, `e.agentId` which loop. Rewrite `text` or readdress `to` with `next` (a new `to` is judged again); `{ isDelivered: |
| `session.compact` | Fires when the conversation is about to be compacted (`/compact`, the threshold, a plugin, or ahead of time); `next(e)` resolves `{ messages }`. Rewrite `instructions` or `messages` on the way down, the messages on the way up, or answer `{ messages }` of your own; `{ skip: reason }` |
| `session.attach` | Fires when a remote client joins the session's roster of attached surfaces: it said so (ui_attach), or it first asked to draw. Observe (a phone joined: draw the lobby); `next(e)` resolves to `{ clientId }`, a different return changes nothing. `$.session.surfaces()` |
| `session.detach` | Fires when a client leaves the roster: it detached, or the session ended with it attached (`e.reason`). Observe; `next(e)` echoes `{ clientId }`. With reason `end` it runs inside `session.end`'s one short bound: there `next.budget` reads that bound and `next.signal` aborts at it. |
| `session.measure` | Fires when the engine measures the session and a unit moved: after each main-thread turn, and when a rate-limit window moves a whole point. Observe; `next(e)` echoes `{ changed }`. `$.session.usage()`'s figures, pushed, not polled: compare them with your own threshold here, call the |
| `session.end` | Fires once when the session ends (exit, /clear, resume, logout, signal, a `-p` run done), after its SessionEnd settings hooks; `e.reason` says which. `next(e)` runs the engine's end step, `{ sessionId }`; `e.resume.id` is `--resume`'s. Exits stay fast whatever is loaded: the whole chain shares |
| `plugin.register` | Fires once per hooks module about to join the chain, at load (the set folded and built, nothing swapped in) and at reload; core allows. Return `{ refuse: reason }` and it never joins: no hook, no noun, no tool of it; the debug log names who refused. Its judges, `$` whole, are the |
| `turn.start` | Fires when a model turn begins, before its first model call; `next(e)` resolves to `{ turnId }`. Observe: a different return changes nothing. |
| `turn.step` | Fires when the engine is about to send a model request of a turn, main's or a subagent's (`e.agentId`); `next(e)` resolves to the whole response. `next({ ...e, model })` or `effort` sends another; the turn, the index and the message count are pinned. An answer without `next` sends no request. |
| `turn.complete` | Fires when a model turn has ended, at the point its duration is reported; `next(e)` resolves to `{ text }`, the answer. `e.reason` says why. Return `{ text }` with a different text to show it beneath the answer (a synopsis, a TL;DR line); the transcript's record is never rewritten. A |
| `engine.create` | Runs while `$` is being built, once per load or reload of this plugin and before any other hook of it; `next(e)` resolves to `$` built so far. A step may ADD nouns and WITHHOLD nouns (leave one out, or return without `next`); it may NOT REPLACE one another step added: the step fails, named |
| `tool.call` | `{ result, context? }`, `{ deny }`, or core's `{ ref, result }`. |
| `tool.check` | `{ decision, reason?, rule?, hook? }`. |
| `ui.render` | The tree to draw; `{ type: "engine", ref }` is core's own drawing. |

`$` nouns (types :2489-3756): `model` (complete/fork/classify), `audio`, `mcp`,
`session` (cwd/root/model/turns/id/repo/surfaces/usage/version/compact/**send**/append/authorize),
`turn`, `prompt` (read/fill/suggest/**submit**), `tool` (register/call), `command`
(register/run), `config`, `telemetry`, `agent` (list/spawn), `fs`, `store`
(cross-session KV), `state` (session KV), `clock` (timers), `http`, `process`
(run), `settings`, `env`, and the surface tables `terminal`/`desktop`/`mobile`/`vscode`.

**Routing-relevant subset:** `session.receive` (consume inbound), `session.send`
(readdress outbound), `prompt.submit` (peer-origin turns, `drop`), `$.session.send`
(forward), `$.model.classify` (decider), `$.store` (cross-session roster/ledger),
`$.clock` (heartbeat without cron), `agent.offer`/`agent.spawn` (gate which
agent types a session may launch), `turn.complete` (synopsis line), `session.measure`
(already used for auto-handoff).

## 6. GitHub topics sweep + ecosystem prior art (Ray's follow-up, 2026-10-04)

Ray: "add github topics to the /research-sweep skill ... track what topics a
repo has applied and add that to our list" + "create a saved github search".

- Topics swept via `gh api -X GET search/repositories -f q=topic:<t>`; control:
  fresh nonexistent topic → `total_count` 0. Totals: claude-code-mods 58,
  claude-code-plugin 8175, claude-code-plugins 639, claude-mods 45,
  function-hooks 51. Snowball found three mod-specific topics on example repos:
  claude-code-mod (34), claude-mod (11), claude-code-hooks (26). 457 unique
  repos. Raw: `raw/coord-router/gh-topics-sweep.jsonl`. Registry (seeds,
  discovered topics, examples WITH their topics, catalog):
  `docs/research/github-topics.toml`. Skill wiring: research-sweep in-lane step 1.
- Saved search (issues/PRs; discussions N/A on anthropics/claude-code):
  `docs/research/saved-searches/claude-mods-routing-2026-10-04.toml`; baseline
  rerun rc=0, all 6 controls ok (`raw/coord-router/saved-search-baseline.md`);
  one noisy query dropped (windhawk-mods). Repository/topic reruns need a
  `repositories` saved-search kind → spec S5 in `docs/specs/coord-router-2026-10-04.md`.

| Repo | Mechanism (read from source) | Relevance |
|---|---|---|
| kbrdn1/claude-crosstalk | `on('session.receive', {origin:{kind:['peer','peer-send-message']}})` at `hooks/register.ts:376`; `tool.call` SendMessage at :386; parses sender name+address from the envelope in `e.text` (`hooks/thread.ts:114`). Built on 2.1.277. | **Direct prior art for S3**: receive-side interception works in a published mod. Copied to `raw/coord-router/claude-crosstalk/`. |
| tsurutanmen/session-bridge | Own file mailbox (`bridge.py`) + `prompt.submit`, `/tell`, `/namae`; tested 2.1.286-288 on Windows. | Custom transport — what we avoid by using native SendMessage + `session.send`. |
| RedesignedRobot/cdx | Function-hooks plugin running codex/antigravity as detached execution. | Pattern for codex lanes (they run no Claude hooks). |
| bennewton999/claude-code-mods | session-fleet / session-activity panes. | Presentation only. |
| shuizhengqi1/cc-mod-hub | "checked CC mod" hub, 377 mods at PR #53. | Catalog to re-sweep. |
| cluesmith/codev#1761 | "adopt Claude Code mods as an extension surface (discussion)". | Ecosystem signal. |

Process-hardening lane (2026-10-04, review a945f229) peer input adopted: mods
are observation/convenience, never sole enforcement; TS thin → python decides;
prove admission per lifecycle path. Reply sent: neither PH item 10 nor 25 is
subsumed (both are consumers: the specialists call 10; the shipper runs 25).

## 7. Reviews and revision (2026-10-04)

- sdlc-team review 20bbca95 (5 specialists, codex rc 0): "correct the
  specification before implementation"; sender-side primary confirmed; S1
  must consume R-a3 PR2 roles/epochs + relay-rule-r2 resolver; S4 custody and
  admission corrections; durable ingress for codex/KB; order S0→S1→S4→S2→S3→S5.
  Research-coverage audit INCOMPLETE (firecrawl-search HTTP 402; discussions
  canary 0 on a repo with discussions disabled). Verbatim:
  `sdlc-review-coord-router-20bbca95.md`.
- premise-verifier: 17 rows, 11 confirmed, 0 refuted; 5 blocking gaps.
  Verbatim: `premise-verifier-coord-router-2026-10-04.md`.
- **Own-tracker miss, corrected:** #1624 (role-addressed messaging, OPEN, hold
  lifted for PR2 after PR1 at `task_plan.md:2663`) already researched role
  JSON + `role resolve`. Rev 2 builds the router ON PR2/#1624 instead of a
  parallel roster.
- Spec rev 2: `docs/specs/coord-router-2026-10-04.md`.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — issues #99417 #94000 #89462 #91105 #97220 #99049 #91870 #76727; mods dir; has_discussions=false
- [kbrdn1/claude-crosstalk](https://github.com/kbrdn1/claude-crosstalk) — session.receive peer capture source (register.ts:376)
- [tsurutanmen/session-bridge](https://github.com/tsurutanmen/session-bridge) — custom file mailbox + prompt.submit
- [tsurutanmen/session-dash](https://github.com/tsurutanmen/session-dash) — sessions pane
- [bennewton999/claude-code-mods](https://github.com/bennewton999/claude-code-mods) — fleet board mods
- [RedesignedRobot/cdx](https://github.com/RedesignedRobot/cdx) — codex/antigravity detached execution via function hooks
- [NovusEdge/a2a-mod](https://github.com/NovusEdge/a2a-mod) — A2A hand-off mod
- [shuizhengqi1/cc-mod-hub](https://github.com/shuizhengqi1/cc-mod-hub) — mod catalog (377)
- [cluesmith/codev](https://github.com/cluesmith/codev) — #1761 mods adoption discussion
- [notdp/hive](https://github.com/notdp/hive) — PR #255 mods version gating
- [devohmycode/claude-mods](https://github.com/devohmycode/claude-mods) — PR #1 claude-message-mod
- GitHub topic searches: claude-code-mods, claude-code-plugin, claude-code-plugins, claude-mods, function-hooks, claude-code-mod, claude-mod, claude-code-hooks (457 repos, raw jsonl)
