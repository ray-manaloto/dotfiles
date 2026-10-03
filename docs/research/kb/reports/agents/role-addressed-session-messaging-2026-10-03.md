# Role-addressed session messaging: stop broadcasting "the coordinator changed" (2026-10-03)

- **Question:** a coordinator, a watcher and fan-out lane sessions each run as their own `claude --bg` session and talk over cross-session `SendMessage`/`ListAgents`. How do they stop broadcasting "the coordinator/watcher changed" to every session at every handoff? The options weighed are (a) a role registry (a sqlite db or a file), (b) a proxy/router that peers address by role, and (c) a native Claude Code alias. The question also asks which projects already ship this, and which saved searches would track the space.
- **Builds on, does not repeat:** `session-role-identification-research-2026-10-03.md` and `docs/specs/session-handoff-automation.md` rev 4. Both are in worktree `.claude/worktrees/handoff-automation-research`.
- **Produced by:** the `research-sweep-run` synthesize node. Its inputs are the fan-out manifests listed under Evidence, plus a re-read of the load-bearing primary sources by this node. Raw copies are in `.agent/kb/raw/role-addressed-session-messaging-2026-10-03/`, which is machine-local.
- **Write location:** the brief named the main checkout's `docs/research/kb/reports/agents/` path. The harness blocks writes to the shared checkout from this un-isolated background agent, so the report was written to the same relative path inside the coordinator worktree `coord-97ffeddb` (branch `docs/coordinator-97ffeddb-2026-10-03`).

## Answer

**Build (a), a small role registry. Back it with Claude Code's own session listing, read through one resolver task. Senders call the resolver at send time, so nothing is announced at handoff.** Do not build (b) as a daemon yet: the earlier claim that no script transport exists was REFUTED on verification (the vendor documents a per-session inbox socket), so (b) is deferred until a live probe shows whether a non-child process can post peer messages, not ruled out for lack of transport. Treat (c) as a later simplification that has to be armed first; the `--bg` collision behaviour is documented as not checked, which weakens (c) as a stable alias (see Verification).

1. **No native mechanism maps a stable alias to the newest session across a succession.**
   - What the native layer does give: `SendMessage` delivers on a bare name when exactly one live session answers to it. A new interactive session that asks for a live session's name is renamed to a variant (`$CC/cross-session-messaging.md:147-150`, `$CC/sessions.md:127`).
   - The old coordinator is still live while its successor reviews the handoff, so the successor cannot take a stable name such as `dotfiles.coordinator`.
   - A session cannot rename itself: there is no `claude rename` CLI (`$CC/cli-reference.md:28-47`), and `/rename` is a user-typed command.
   - Agent teams are ruled out: "Lead is fixed … One team per session … can't share a team across sessions" (`$CC/agent-teams.md:472-475`).
   - **Qualification (verification, UPHELD misleading):** the variant rename is not universal. `$CC/sessions.md:129-133` says Claude Code does not check the `--name` of a background or `-p` session at startup, and `cross-session-messaging.md:147` says sessions can still share a name. A `claude --bg --name coordinator` successor can therefore coexist with its predecessor under one name and force id-disambiguated addressing. Conversely, if the predecessor has exited first, the bare name resolves to the successor alone, so retire-first succession works within documented rules.
   - Channels are an MCP push surface in research preview (`$CC/channels.md:10-13`). That makes them lane 2 under `research-doc-sources.md`.
2. **Most of the registry already exists in this repo, and it lives in the wrong place.**
   - `handoff_inbox.require_newest_coordinator` (L0 branch, `81be2fc0`, `python/src/dotfiles_setup/handoff_inbox.py:174-204`) already resolves "the newest live coordinator" from `~/.claude/jobs/*/state.json`.
   - The successor brief tells peers to find the coordinator "by ListAgents recency or the notify message" (`coordinator_handoff.py:696` on `main`). It then broadcasts anyway: "SendMessage every ListAgents lane your session name as the new coordinator" (`:707`).
   - The fix is to make that resolution a callable task. Each sender runs it right before it sends, and step 2 of the brief is deleted.
3. **Other projects ship per-agent identity, mailboxes and leases. None ships a role alias.**
   - `Dicklesworthstone/mcp_agent_mail` ships memorable per-agent identities, inboxes and TTL file leases over SQLite plus Git (its README). Its project-addressed mailbox, the closest thing to role addressing, is **only proposed**: #263 was closed and moved to `mcp_agent_mail_rust#282`, which is **open**.
   - `jamditis/claude-peers-mcp#99` **proposes** TTL work claims on a peer broker.
   - `firstintent/ccteam` **ships** a central "brain" that addresses sessions by broker handle (`@s2`; its README).
4. **Two reliability facts shape the design.**
   - **`SendMessage` success is not delivery.** In #90890 (open), 8 sends reported `success` and none arrived. So the registry must pair with the durable `handoff-inbox`, and a send may not be gated on its return value.
   - **`state: done` does not mean dead.** `done` means "the last turn finished … whether or not its process is still alive" (`$CC/agent-view.md:726`). So "superseded" has to be an explicit registry write, never inferred from `state`.

**Sweep completeness:** the input carried no MANDATORY GAPS list and no failed stages, so the sweep is not marked INCOMPLETE. The refute, critic and adjudicate steps all ran. Seven sources came back `empty_unverified` or `error`, and the critic added ten further gaps. They are named under Gaps and must not be read as "nothing found". Verification overturned one claim (no script transport) and qualified one more (name collision); see Verification.

## Evidence

### Claims (claim | URL or file:line | quote)

| Claim | URL or file:line | Quote |
|---|---|---|
| **Native, shipped:** a bare session name addresses a session only while exactly one live session answers to it | `$CC/cross-session-messaging.md:147-150` | "One session answers to the name: Claude Code delivers the message on the name alone. Several sessions share the name … Claude adds a short identifier" |
| **Native, shipped:** a new session asking for a live session's name gets a variant name | `$CC/sessions.md:127` | "Claude Code leaves the name with the session that already has it, renames yours to a variant with a two-word suffix" |
| **Native, shipped:** each session registers itself in files on disk, and discovery reads them | `$CC/cross-session-messaging.md:166` | "Each session registers itself in files on disk. When Claude lists or messages your local sessions, Claude Code reads those files" |
| **Native, shipped:** `claude agents --json` is the supported session-state reader; the job files are not a stable interface | `$CC/agent-view.md:720,731` | "`claude agents --json` is the supported way to read session state from outside Claude Code" / "The files under `~/.claude/jobs/<id>/` are not a stable interface" |
| **Native, shipped:** `done` is not a liveness signal | `$CC/agent-view.md:726` | "`done`: The last turn finished what you asked for … whether or not its process is still alive" |
| **Native, shipped:** agent teams cannot carry a succession | `$CC/agent-teams.md:472-475` | "One team per session … Lead is fixed: the main session is the lead for its lifetime. You can't promote a teammate to lead or transfer leadership." |
| **Native, shipped:** a held or refused message is reported back to the sender, and a drop is not | `$CC/cross-session-messaging.md:237,241` | "Claude Code sends a notice back to it when the receiver holds the message" |
| **Upstream bug, open:** SendMessage reports success on a silent drop | https://github.com/anthropics/claude-code/issues/90890 | "8 consecutive `SendMessage` calls to 5 different peers all returned `success` with a `msg_id`. None of them appear in any recipient's transcript." |
| **Upstream request, open (CORRECTED by verification):** there is no first-class `claude send` CLI. The earlier gloss "so a script-level router has no transport" is STRUCK: `$CC/cross-session-messaging.md:262-300` documents a script-postable per-session inbox socket (`CLAUDE_CODE_MESSAGING_SOCKET`/`_TOKEN`, `env-vars.md`) | https://github.com/anthropics/claude-code/issues/99049 | "it can only be reached from inside a session, through a model tool call … every message costs 10–15 s and a paid model turn" |
| **Upstream request, open:** hooks cannot read the addressable name | https://github.com/anthropics/claude-code/issues/97220 | "`CLAUDE_CODE_SESSION_NAME` does not exist" |
| **Upstream bugs, open:** name aliases are fragile | https://github.com/anthropics/claude-code/issues/86531, https://github.com/anthropics/claude-code/issues/93619, https://github.com/anthropics/claude-code/issues/98981 | #86531: "Renaming one session with `/rename` renames other concurrently running sessions too"; #93619: "SessionStart hook sessionTitle never reaches ListAgents alias" |
| **Upstream request, open:** no first-party coordination story; subagent hooks carry the parent's session id | https://github.com/anthropics/claude-code/issues/76727 | "A subagent's hook payload carries the PARENT's `session_id` — session-keyed locks/claim registries are silently broken for subagents" |
| **In repo, shipped on `main`:** the successor broadcasts its name to every lane | `python/src/dotfiles_setup/coordinator_handoff.py:707` (main) | "2. SendMessage every ListAgents lane your session name as the new coordinator" |
| **In repo, shipped on `main`:** the newest coordinator is resolved by recency, never by name sort | `python/src/dotfiles_setup/coordinator_handoff.py:696` (main) | "NEWEST COORDINATOR is found by ListAgents recency or the notify message, never by sorting names" |
| **In repo, shipped on `main`:** successor names are unique timestamps, not a stable alias | `python/src/dotfiles_setup/coordinator_handoff.py:426-428` (main) | "`dotfiles-yyyyMMdd'T'HHmmss.<9-digit ns><X>.coordinator` in Chicago" |
| **In repo, unshipped (L0 `81be2fc0`):** a working newest-live-coordinator resolver already exists | `python/src/dotfiles_setup/handoff_inbox.py:174-204` @ `81be2fc0` | "it must carry a coordinator name and the newest `createdAt` of every coordinator-named record that is still live (a `done` or `stopped` record is skipped" |
| **In repo, draft spec:** the spec's "role registry" classifies a name into a role. It does not map a role to a session | `docs/specs/session-handoff-automation.md:88-99` (handoff-automation-research worktree) | "`role_of(name, session_root, plugin_root) -> Role \| Unplaced \| None`" |
| **In repo, draft spec:** handoffs still message "the newest coordinator" and notify every session | same spec, `:121`, `:145` | "SendMessage a digest to the newest coordinator" / "the coordinator's SendMessage loop sends 'main → `<sha>`'" |
| **Third party, shipped:** agent-mail gives agents identities, inboxes and TTL leases over SQLite plus Git | https://github.com/Dicklesworthstone/mcp_agent_mail (README:7,23-27,314-316) | "It gives agents memorable identities, an inbox/outbox, searchable message history, and voluntary file reservation 'leases'" |
| **Third party, proposed:** agent-mail's project/role-style mailbox is not shipped | https://github.com/Dicklesworthstone/mcp_agent_mail/issues/263, https://github.com/Dicklesworthstone/mcp_agent_mail_rust/issues/282 | "Add a project-addressed shared mailbox so a sender can route work to a repository rather than a particular agent"; maintainer: "no timeline promised"; rust#282 state `open` |
| **Third party, shipped bug fix:** agent-mail's live identity resolution has had locator bugs | https://github.com/Dicklesworthstone/mcp_agent_mail/issues/270 | "the documented composite pane form returns 'no identity registered' for that same live pane" |
| **Third party, shipped failure mode:** a SQLite registry under multi-agent load has corrupted | https://github.com/Dicklesworthstone/mcp_agent_mail/issues/246 | title: "SQLite 'database disk image is malformed' → reconstruct-from-archive loop under multi-a…" |
| **Third party, proposed:** advisory TTL work claims on a peer broker | https://github.com/jamditis/claude-peers-mcp/issues/99 | "A peer has at most one active claim … Calling `set_work_claim` replaces that peer's prior claim and refreshes its expiry … ordinary heartbeats must not keep abandoned work alive" |
| **Third party, research write-up (not code):** keep the role separate from the runtime instance; use an epoch per incarnation and fencing for writes | https://github.com/frarteaga/agent-swarm-protocol/issues/3 | "agent capability/role != runtime instance != current task" / "The epoch distinguishes a restarted process at the same network address from its previous incarnation" / "FencingToken: monotonic authorization generation for protected writes" |
| **Third party, research write-up:** these are separate problems, and the recommended design is a hybrid | https://github.com/frarteaga/agent-swarm-protocol/issues/3 | "these are different problems and robust systems model them separately … The recommended design is a hybrid" |
| **Third party, measured and closed in their tracker:** bare-name SendMessage plus `notify_when_idle` replaces polling | https://github.com/samosunaz/agent-skills/issues/66 | "(a) `SendMessage` to a bare session name (`claude --name X`) delivers with no `[ref]` … (b) `notify_when_idle: true` yields exactly one `[Cross-session idle notice]` per subscription" (Spike #63, CC 2.1.288) |
| **Third party, proposed:** a Monitor-run supervisor script for non-Claude workers | https://github.com/samosunaz/agent-skills/issues/67 | "it acks heartbeats, resends a lost Enter once, and prints one line only when the coordinator must act" |
| **Third party, shipped:** ccteam addresses sessions by a broker handle, from one brain | https://github.com/firstintent/ccteam (README:42-43) | "`/new [vendor] [role] …` / `@s2 run the test suite  # address any session directly`" |
| **Third party, proposal (tangential):** session affinity for an HTTP AI gateway | https://github.com/higress-group/higress/issues/4799 | "A configurable logical session key would consistently select one named AI provider" (a gateway-routing proposal; no agent sessions) |

### Code search (from CODE SEARCH; `plan/code-search.json`)

| Query | Role | Source | Count | rc |
|---|---|---|---|---|
| `agent role registry heartbeat lease filename:README.md` | query | planner | 4784 | 0 |
| `agent mail inbox role alias coordinator` | query | planner | 12338 | 0 |
| `agent registry filename:README.md` | must-hit | planner | 345088 | 0 |
| `agent mail` | must-hit | planner | 25559040 | 0 |
| `qvxjzkw7blorptn3dgs` | known-absent | planner | 0 | 0 |
| `repo:cli/cli filename:README.md` | health | workflow | 9 | 0 |
| `repo:anthropics/claude-code filename:README.md` | must-hit | workflow | 29 | 0 |
| `repo:Dicklesworthstone/mcp_agent_mail filename:README.md` | must-hit | workflow | 3 | 0 |
| `repo:ruvnet/ruflo filename:README.md` | must-hit | workflow | 157 | 0 |
| `repo:smtg-ai/claude-squad filename:README.md` | must-hit | workflow | 2 | 0 |

- No row was rate-limited.
- Both `query` rows are armed: the must-hits returned more than 0 and the fresh known-absent returned 0, so the probe discriminates.
- The code-search tokenizer drops punctuation, so a count measures loose token overlap, not relevance.

**Notes (these are not gaps):**
- `anthropics/claude-code` has discussions disabled (repos API), so github-discussions is not searchable there.
- `Dicklesworthstone/mcp_agent_mail` has discussions disabled (repos API), so github-discussions is not searchable there.

### Dependency-repo fan-out (from DEPENDENCY RUNS)

| Repo | Query | Required sources failed | Manifest |
|---|---|---|---|
| anthropics/claude-code | session role registry | none | `.agent/kb/raw/research-fanout/research--kb--reports--agents--role-addressed-session-messaging-2026-10-03/deps/anthropics--claude-code/1/manifest.json` |
| anthropics/claude-code | mcp_agent_mail | none | `…/deps/anthropics--claude-code/2/manifest.json` |
| anthropics/claude-code | ruflo | none | `…/deps/anthropics--claude-code/3/manifest.json` |
| anthropics/claude-code | claude-squad | none | `…/deps/anthropics--claude-code/4/manifest.json` |
| Dicklesworthstone/mcp_agent_mail | claude-code | none | `…/deps/Dicklesworthstone--mcp_agent_mail/1/manifest.json` |
| ruvnet/ruflo | claude-code | none | `…/deps/ruvnet--ruflo/1/manifest.json` |
| smtg-ai/claude-squad | claude-code | none | `…/deps/smtg-ai--claude-squad/1/manifest.json` |

- The topic manifest is `.agent/kb/raw/research-fanout/session-role-registry/manifest.json`, covering github-issues, github-discussions, exa and firecrawl-search.
- The `ruflo` and `claude-squad` queries against `anthropics/claude-code` returned off-topic issues, such as #97515 and #80652. They measured token overlap, not relevance, and nothing from them is cited above.

### Offline mirrors (from MIRRORS)

| Link | Mirror file | rc | Bytes | Failure |
|---|---|---|---|---|
| _(no input rows: MIRRORS was `[]`; the request named no links to mirror)_ | | | | |

The primary sources this node re-read were fetched with `gh api` into `.agent/kb/raw/role-addressed-session-messaging-2026-10-03/`, with rc 0 for every fetch. Those are raw copies, not firecrawl mirrors:
- `*_claude-code-{76727,90890,97220,99049,93619,86531}.json`
- `Dicklesworthstone_mcp_agent_mail-{263,270,234,246}.json`, plus `mam-263-comments.json` and `mamrust-282.json`
- `jamditis_claude-peers-mcp-99.json`
- `frarteaga_agent-swarm-protocol-3.json`
- `samosunaz_agent-skills-{66,67}.json`
- `higress-group_higress-4799.json`
- `mam-README.md` and `ccteam-README.md`

## Conflicts resolved

1. **"The dotfiles spec implements a role registry … without broadcasting changes"** (input claim) is **wrong on all three counts.**
   - The spec is "DRAFT rev 4. Nothing is implemented" (`session-handoff-automation.md:3`).
   - Its "role registry" (`role_of`, §3b) classifies a name into coordinator, lane or watch. It does not map a role to the current session.
   - The spec still sends to "the newest coordinator" (`:121`) and keeps the all-sessions `notify_sessions` loop (`:145`).
   - Trusted: the spec text over the claim's summary, because the primary source wins.
2. **"Proxy/router pattern (Option B alternative) …"** (input claim) quotes the **user's own request**, not the prior report. The prior report contains no such passage; it was read in full. The claim is the question restated, not evidence.
3. **The "session title is only on SessionStart" claim, from the prior report, is superseded by spec rev 4.**
   - Rev 4 (§3b, `:93`) says `classic.UserPromptSubmit` carries the current title after a rename (`d.ts:11291`). Rev 4 is newer, so it wins.
   - Separately, #93619 (open) shows that a title *set by* a SessionStart hook never reaches the `ListAgents` alias. Writing the name from a hook does not change the address.
4. **mcp_agent_mail #263 is "closed / completed", but it did not ship.** The maintainer's closing comment moves it to `mcp_agent_mail_rust#282`, which this node fetched: state `open`. The comment and the live rust issue are trusted over the closed state. Likewise PR #150 (the inbox-check hook fix) is `closed` with `merged: false`.
5. **ccteam: is it "refuses an empty role" or "roleless by default"?**
   - The code-level claim comes from the prior report's read of `crates/ccteam-harness/src/execution/claude_bg.rs:200-202`.
   - The README's "Roleless by default" line (README:234) is about not rewriting project `CLAUDE.md`/`AGENTS.md`. It is not about worker roles.
   - So the two do not conflict. Code beats README where they touch.
6. **The newest-coordinator resolver skips `done` records** (L0 F2, `handoff_inbox.py:22-25`). The docs say `done` covers a session whose process is alive and idle (`agent-view.md:726`).
   - It is not a bug for the caller: the caller is running a turn, so it is `working`.
   - It is wrong as a general resolver. A newer successor sitting idle reads `done` and would be skipped, which makes an older coordinator look newest.
   - Trusted: the vendor docs over the code's assumption. That is why the recommendation below records supersession explicitly.

## Gaps

- **session-role-registry: github-discussions, `empty_unverified`.** Unknown, not empty. The control ran with `count: 0` on query `claude-code`, so the probe never discriminated.
- **session-role-registry: firecrawl-search, `error`.** The `.raw` file is 0 bytes and the content is unknown. No web-scale search of the space ran.
- **anthropics/claude-code/1, /2, /3, /4: github-discussions, `empty_unverified`.** These are expected, because discussions are disabled on that repo (see the notes). They are listed here because the harness classed them unverified.
- **Dicklesworthstone/mcp_agent_mail/1: github-discussions, `empty_unverified`.** Expected for the same reason: discussions are disabled.
- **Not covered, because no rows exist for them:** `mcp_agent_mail_rust`, where the role/project mailbox now lives; `louislva/claude-peers-mcp`, the upstream of the jamditis fork; and `firstintent/ccteam`. None had a dependency fan-out. Their READMEs and issues were read directly, but their issue and release history was not swept.
- **The ruflo and claude-squad release bodies were not read.** The manifests record only "release body mentions a query term: yes" for `ruflo v3.50.0` and `v3.51.1`, so what those releases change is unknown. The claude-squad Podiom discussion (#316) was read at snippet level only.
- **Unarmed native behaviour (corrected).** The variant rename on a name collision is documented for interactive sessions (`cli-reference.md:106`). For `--bg` and `-p` sessions the docs say the name is NOT checked at startup (`sessions.md:131`), so no rename happens; the earlier text calling this undocumented was wrong. What is unmeasured is the live behaviour of two `--bg` sessions on one name and whether a stopped predecessor frees it. Option (c) depends on it.
- **The inbox socket is documented, but its peer-posting behaviour is unverified.** The docs describe the socket, the auth line (`cross-session-messaging.md:278-283`) and the shared inbound controls; the message-line payload schema beyond the auth line is not specified, and whether a non-child process can post a peer message is unprobed. (The earlier wording "undocumented protocol, no transport" overstated the absence.)

Critic gaps (verification step; each with its next probe):

- **Option (c) never measured.** Whether `claude --bg -n <live name>` yields a variant or silently collides, and whether a stopped predecessor frees the name. Next: launch two `claude --bg -n probe.coordinator` sessions, read `claude agents --json` and ListAgents, stop the first, try a third into the freed name; record the CC version.
- **Resolver sufficiency unchecked.** The `mise run role -- resolve` cross-check against `claude agents --json` cites only the doc claim, not the JSON schema. Next: run `claude agents --json` on live coordinator/watcher/lane sessions, diff its fields against what `require_newest_coordinator` reads from `~/.claude/jobs/*/state.json`, save a sample as raw evidence.
- **Inbox-socket wire protocol for a non-model sender unverified.** It is now the basis for deferring option (b). Next: read `cross-session-messaging.md:270-290` in full, inspect the socket files and the sender code path, re-check #99049 and recent release notes for a `claude send`.
- **#90890 not reproduced.** Frequency, affected version and current reproducibility untested; the "never gate on success" rule rests on one open issue (confirmed, version 2.1.247). Next: N sends between two `--bg` sessions on the current CC version, check recipient transcripts, re-read the #90890 comments and latest release notes.
- **Sources not swept.** `mcp_agent_mail_rust` (issue and release history, #282 design), `louislva/claude-peers-mcp`, `firstintent/ccteam` (issues, releases), ruflo v3.50.0 and v3.51.1 release bodies, claude-squad discussion #316. Next: `gh api` issues/releases/discussions per repo with role, successor, handoff, alias queries; read release bodies in full; record shipped versus proposed.
- **Two cross-repo leads read by title only.** `edisonshen/fleet#332` (fleet-owned /handoff skill) and `jdylanmc/cmux-maestro#113` may be proven coordinator-succession workflows, the "just use it" case the user asked about. Next: fetch READMEs, issue bodies and handoff/registry code; compare with the JSON-per-role design.
- **Empty or errored searches never re-run.** github-discussions (control did not discriminate), firecrawl-search (0-byte output), off-topic exa results, and no non-GitHub sources (blogs, HN, Reddit). Next: re-run firecrawl-search and exa with sharper queries (for example "agent leader election lease handoff Claude Code"), use last30days for HN and Reddit, use a control that returns nonzero.
- **Saved searches only armed once.** Counts are loose token overlap, precision not scored, no stability check across reruns, #1502 unmerged so no freshness record, the `crossSessionInbound` code watch named but not armed. Next: re-run with `is:open` and `created:` filters, score the top 10 hits, arm the code watch with a control hit and a fresh known-absent query, confirm the #1502 schema accepts these `[[watch]]` entries before committing the toml.
- **Design claims derived from a write-up, not an implementation.** Generation as a fencing epoch, no sqlite, the atomic-replace lock come from agent-swarm-protocol#3; nothing checks that the `handoff_inbox` lock discipline covers a role file or that two concurrent successors cannot both win. Next: read `handoff_inbox.py` at `81be2fc0` and its lock code, prototype a test racing two writers on one role file, check generation monotonicity and crash recovery between pending and committed writes.
- **Secondhand reads not pinned.** The ccteam `claude_bg.rs:200-202` claim came from the prior report, and the spec lines were read in a different worktree. Next: pin commit SHAs and re-read ccteam `crates/ccteam-harness/src/execution/claude_bg.rs`, `coordinator_handoff.py:696,707` on current main, and spec lines `:88-99`, `:121`, `:145`; add SHA and line citations.
- **The exa results were off-topic:** casbin, Spring `SessionRegistry` and similar. They contribute nothing and are not a negative finding about agent registries.
- **The saved searches proposed below were armed once by this node** (control-hit 8922, fresh known-absent 0; see `saved-search-arm.tsv`). No `watches.toml` freshness record exists, because #1502 (the `research-saved-search` task) is still OPEN and unmerged.

## Recommendation

**Adopt (a): an explicit succession record, with a resolve-at-send task.** Delete the broadcast.

1. **Registry = one JSON file per role, written only by the handoff tooling.**
   - Path: `<main checkout>/.agent/state/roles/<role>.json`. It sits beside the existing `handoff-inbox` state, so it survives `claude rm` of a worktree (spec §3b, "State placement").
   - Fields: `role` (`dotfiles.coordinator`, `dotfiles.watch`, `dotfiles.lane.<feature>`), `name`, `session_id`, `generation` (a monotonic integer, the epoch/fencing idea from agent-swarm-protocol#3), `since`, `superseded_by`.
   - The writer is an atomic replace under the existing `handoff_inbox` lock discipline.
   - **No sqlite.** One writer per role per succession does not need a database. agent-mail's #234 (the lock model) and #246 (a malformed DB) are the failure modes a file avoids.
2. **Writes happen at the two moments that already exist.**
   - `coordinator-handoff launch` records `pending: <successor>`.
   - The successor's first action (or `retire`) flips the record to `name=<successor>, generation+1`.
   - The same applies to `watch-handoff` and `lane-handoff` (spec §3c). Supersession is explicit, so `state: done` is never read as dead.
3. **Reads go through one task: `mise run role -- resolve <role>`** (Python, zero-bash).
   - It reads the record and cross-checks it against `claude agents --json`, the supported interface, not `~/.claude/jobs/*/state.json`.
   - It prints the addressable name. On a mismatch it falls back to newest-live-by-`startedAt`, and it says which source answered.
   - Port `require_newest_coordinator` onto it. Lanes, the watcher and `notify_sessions` call `resolve` immediately before `SendMessage`.
4. **Delivery stays two-channel.**
   - Send with `SendMessage` to the resolved name. Never treat a `success` result as delivery (#90890).
   - Anything that must survive goes to `handoff-inbox append` as well. The new coordinator reads that inbox at start, which it already does (`coordinator_handoff.py:692-693`).
5. **Delete brief step 2** ("SendMessage every ListAgents lane your session name", `coordinator_handoff.py:707`). The spec's lane-digest and `notify_sessions` rows then say "to `role resolve dotfiles.coordinator`" instead of "the newest coordinator".
6. **Defer (b), the proxy daemon, pending a live socket probe.** (Corrected: the earlier text rejected it because "no non-model process can send", which verification REFUTED.)
   - There is no first-class `claude send` (#99049 is open), but the vendor documents a script-postable per-session inbox socket with an auth line. A router could use it without a model turn; whether a non-child process can post peer messages, and the payload schema, are unverified. herdr's `agent prompt` / `pane send-text` is another non-model path to a running agent. The registry-plus-resolver in items 1-5 is still the cheaper first step and does not need a daemon.
   - Adopting `mcp_agent_mail` buys identities and leases, but not role addressing: rust#282 is open. It would also be our own MCP choice, which is lane 2.
   - Revisit if #99049 ships a `claude send`.
7. **Keep (c), the stable-name alias, as a later simplification, gated on two arms.**
   - Arm 1: `claude --bg -n <name of a live session>`. The docs (`sessions.md:131`) say a `--bg` name is not checked, so expect a silent collision rather than a variant; measure it. The retire-first path (stop the predecessor, then take the name) is the one that works within documented rules.
   - Arm 2: a stopped predecessor frees the name, so the successor can be launched or renamed into `dotfiles.coordinator`.
   - Even if both pass, the open rename bugs (#86531, #98981) argue for keeping the registry as the source of truth.
8. **Borrow, do not adopt:**
   - from agent-mail: per-agent identity kept apart from role, and an inbox-check hook that emits `additionalContext`;
   - from claude-peers#99: TTL claims, and "heartbeats must not renew ownership";
   - from samosunaz#66: the `notify_when_idle` supervision measured on CC 2.1.288.

**Proposed saved searches.** These use the draft `[[watch]]` schema in `docs/research/saved-searches/orchestration-2026-10-02.toml`. Each was armed once on 2026-10-03 against control-hit `repo:anthropics/claude-code hooks` = 8922 and a fresh known-absent nonce = 0.

| id | kind | query | count (2026-10-03) | top hit |
|---|---|---|---|---|
| `role-cc-session-name-alias` | issues | `repo:anthropics/claude-code SendMessage session name` | 493 | #99049, #97220 |
| `role-cc-listagents` | issues | `repo:anthropics/claude-code ListAgents` | 231 | #98981, #93619 |
| `role-cc-crosssession-rename` | issues | `repo:anthropics/claude-code cross-session rename name` | 160 | #86531, #88992 |
| `role-cc-sendmessage-dropped` | issues | `repo:anthropics/claude-code SendMessage silently` | 366 | #96849 |
| `role-mam-project-mailbox` | issues | `repo:Dicklesworthstone/mcp_agent_mail_rust project mailbox` | 120 | rust#282 |
| `role-mam-identity` | issues | `repo:Dicklesworthstone/mcp_agent_mail_rust identity` | 93 | rust#332 |
| `role-peers-claims` | issues | `repo:jamditis/claude-peers-mcp claim` | 30 | #99 |
| `role-xrepo-coordinator-successor` | issues | `"claude code" coordinator successor session` | 2488 | edisonshen/fleet#332 ("Fleet-owned /handoff skill") |
| `role-xrepo-role-registry-agent` | issues | `"role registry" agent session` | 10252 | jdylanmc/cmux-maestro#113 |
| `role-xrepo-agent-lease-heartbeat` | issues | `agent lease heartbeat coordinator` | 4095 | david-rzepa/zzzops#504 |

Tune them by narrowing with `is:open` / `created:>YYYY-MM-DD`. The cross-repo rows are broad: GitHub tokenises loosely, so read the top 10 rather than trusting the count. Add a code watch for `"crossSessionInbound" "claude agents --json"`. The two cross-repo leads, `edisonshen/fleet` and `jdylanmc/cmux-maestro`, were title-level only and are next to read.

## Verification

Five load-bearing claims were refuted-or-confirmed by independent refuters, then two UPHELD verdicts were adjudicated. The critic and adjudicator both ran (neither null).

| # | Claim | Result | Evidence |
|---|---|---|---|
| 1 | No native mechanism resolves a stable alias to the newest session (bare name only with one live session; collision yields a variant; no rename CLI; teams fixed lead) | **UPHELD misleading** (adjudicator agreed). Core absence confirmed | `cross-session-messaging.md:147-150`, `sessions.md:127`, `agent-teams.md:472-475`, `cli-reference.md:28-47` confirm. Omission: `sessions.md:129-133` says `--bg`/`-p` names are not checked at startup, so a `--bg` successor can share the live name; "no rename CLI" means no subcommand, since `/rename` and `--name` exist. Report line saying bg behaviour is "not documented" was wrong |
| 2 | SendMessage can return success for an undelivered message; registry needs the inbox fallback | **Confirmed** (refuter said misleading, adjudicator overturned to not misleading) | #90890 open, v2.1.247, three observers on two OSes, 0 arrivals. Intermittent, root cause unknown, harness has fixed other silent-success cases at older versions; display names rotate while sessionId persists, which argues for keying on sessionId |
| 3 | No non-model CLI or script path exists to send a message, so a router has no supported transport | **UPHELD refuted and misleading** (adjudicator agreed). Struck | `cross-session-messaging.md:262-300` documents the per-session inbox socket for scripts; `env-vars.md` documents `CLAUDE_CODE_MESSAGING_SOCKET`/`_TOKEN`; changelog L1092 "scripts posting to it". True remainder: no `claude send` (#99049 open); payload schema and non-child posting unverified |
| 4 | mcp_agent_mail project-addressed mailbox has not shipped (#263 closed, moved to rust#282, open); ships per-agent identity, inboxes, TTL leases | **Confirmed** (refuter misleading, adjudicator overturned) | #263 closed/completed, rust#282 open, maintainer "No implementation or release claim yet", "No timeline". Omitted context only: accepted `project:<key>` single-copy design, bead br-vsj5s, contacts/threads/product bus; product bus role semantics unverified |
| 5 | Successor brief step 2 broadcasts; `require_newest_coordinator` unshipped at `81be2fc0` and skips `done`; supersession must be an explicit write | **Confirmed** | `coordinator_handoff.py:707` on main; `81be2fc0:handoff_inbox.py` lines 80, 174-204; only the fix branch contains the commit; `agent-view.md:726`. Resolver is a caller-side refusal check ordered by `createdAt` |

**How the conclusion changes.** The recommendation (a, a role registry with a resolve-at-send task, plus the inbox fallback, no broadcast) stands. Two things move. First, option (b) is no longer rejected for want of a transport; it is deferred until a live probe of the documented inbox socket, so the report no longer claims a router is impossible. Second, option (c) is weaker than stated: `--bg` names are unchecked, so a stable alias works only if succession retires the predecessor first, and that must be measured. The "delete the broadcast" step and explicit supersession writes are unaffected.

## Provenance

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| deps:anthropics/claude-code | general-purpose | sonnet | low |
| deps:Dicklesworthstone/mcp_agent_mail | general-purpose | sonnet | low |
| deps:ruvnet/ruflo | general-purpose | sonnet | low |
| deps:smtg-ai/claude-squad | general-purpose | sonnet | low |
| triage | Explore | sonnet | low |
| read:1/1 | Explore | haiku | (default) |
| synthesize | general-purpose | opus | high |
| refute:1/5 | general-purpose | sonnet | medium |
| refute:2/5 | general-purpose | sonnet | medium |
| refute:3/5 | general-purpose | sonnet | medium |
| refute:4/5 | general-purpose | sonnet | medium |
| refute:5/5 | general-purpose | sonnet | medium |
| critic | Explore | sonnet | medium |
| adjudicate | general-purpose | opus | high |
| reconcile | general-purpose | sonnet | medium |

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code): #76727, #90890, #97220, #99049, #93619, #86531, #98981 and #88992 read; dependency fan-out ×4; saved-search arms
- [Dicklesworthstone/mcp_agent_mail](https://github.com/Dicklesworthstone/mcp_agent_mail): README, #263 (and its comments), #270, #234, #246 and PR #150 read; dependency fan-out
- [Dicklesworthstone/mcp_agent_mail_rust](https://github.com/Dicklesworthstone/mcp_agent_mail_rust): #282 (the project mailbox, open) and saved-search arms
- [jamditis/claude-peers-mcp](https://github.com/jamditis/claude-peers-mcp): #99 (the TTL work-claims proposal)
- [frarteaga/agent-swarm-protocol](https://github.com/frarteaga/agent-swarm-protocol): #3 (the membership/liveness/fencing research write-up)
- [samosunaz/agent-skills](https://github.com/samosunaz/agent-skills): #66 (bare-name SendMessage plus `notify_when_idle`, as measured), #67 (a Monitor supervisor)
- [firstintent/ccteam](https://github.com/firstintent/ccteam): README (broker-handle addressing)
- [higress-group/higress](https://github.com/higress-group/higress): #4799 (gateway session affinity; tangential)
- [ruvnet/ruflo](https://github.com/ruvnet/ruflo): dependency fan-out; release titles only
- [smtg-ai/claude-squad](https://github.com/smtg-ai/claude-squad): dependency fan-out; discussion #316 at snippet level
- [cli/cli](https://github.com/cli/cli): code-search health control only
- [edisonshen/fleet](https://github.com/edisonshen/fleet), [jdylanmc/cmux-maestro](https://github.com/jdylanmc/cmux-maestro), [david-rzepa/zzzops](https://github.com/david-rzepa/zzzops): saved-search top hits, title only
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): `coordinator_handoff.py` (main), `handoff_inbox.py` at `81be2fc0`, the session-handoff-automation spec rev 4, the prior role-identification report, saved searches `orchestration-2026-10-02.toml`, and #1502
