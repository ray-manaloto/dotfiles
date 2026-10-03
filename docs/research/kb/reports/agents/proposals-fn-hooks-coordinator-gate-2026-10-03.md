# Can function hooks ("mods") gate the coordinator-only handoff-inbox verbs?

> Persisted verbatim at receipt by coordinator 28f1a8f7, 2026-10-03. Producer: Plan subagent (read-only), answering
> Ray's question "have [you] researched using claude mod function hooks for this?". Harness note on receipt: output
> matched an instruction-shaped pattern (bypass-permissions); control tags neutralized; no directives acted on.

This lane was read-only, so nothing was written to `findings.md` or `progress.md`. Please save this report under `docs/research/kb/reports/agents/`. No env var values were printed; I checked presence only. The L0 worktree has moved since the brief: it is at `912e843c` ("re-check coordinator authority inside the write lock"), not `767ff5b7`. The gate is unchanged at `python/src/dotfiles_setup/handoff_inbox.py:162-192`.

## Verdict
Yes, mods can help, but not the way the brief imagined.

**What works: a mod-registered tool.** A tool the plugin registers with `$.tool.register` is the strongest mod-based option:
- It is answered by a `tool.call` hook matched only to the plugin's own tool name. That hook gets the session id from the host (`$.session.id()`) and the subagent marker (`e.agentId`). The model and Bash cannot forge either one.
- It **fails closed.** If the hook throws or overruns, the engine runs core on its behalf, and core for a registered tool is "a call no hook answers fails".
- It avoids #92533 (see Hazards).
- It is the only design that can tell the coordinator's main thread apart from its own subagents.

**What does not work:**
- **Denying Bash from a mod** with `tool.call{Bash}` or `classic.PreToolUse`.
- **Injecting a capability through `$.env.set`.**

**Recommendation:** ship ancestry, option (a) of the prior report, as the floor. Add the mod tool as the coordinator's write route. Close the Bash route with a one-time nonce only if you rule that coordinator subagents must not write.

## 1. What the function-hook API exposes when a tool is called
All line numbers are in `.claude/types/claude-code.d.ts`, which matches the installed claude 2.1.288. The `$CC` docs say nothing about function hooks: grepping `plugins-reference.md`, `hooks.md` and `plugins.md` for "function hook" or "hooks module" found nothing. The `.d.ts` is the only contract.

- **`tool.call` event (`:3252`).** "Return `{ deny: reason }` to refuse or `{ result }` to answer yourself". Its input is `ToolCallInput = ToolCallEnvelope & AgentLoop` (`:9797`).
- **`agentId` (`AgentLoop`, `:164-175`).** "absent on the main loop", and "Pinned: a different value is refused". So it is host-set. The envelope fields `tool`, `tool_use_id` and `agentId` are reserved, and "a rewrite of any is refused" (`:9789-9797`).
- **`classic.PreToolUse` (`:951-953`).** Its `e` is only `ToolCallEnvelope`, which carries **no `agentId`**. Its result is `allow`/`ask`/`deny` plus `updatedInput` (`:6445-6494`), so it can deny a Bash call or rewrite it.
- **`$.session.id()` (`:2382`).** "the session's id (the transcript file's name)", supplied by the host.
- **`$.session.root()` (`:2369`).** This is not an identity.
- **`$.env.set` (`:3005-3033`).** Sets the variable "for this process and everything it starts after". That covers every later Bash child, MCP server and `$.process.run`, session-wide. **There is no per-call env for Bash children.**
- **`$.process.run(argv, {cwd, env, stdin, timeoutMs})` (`:2977`, `:6505-6520`).** Per-child `env` and `stdin` are possible, but only for children the hook starts itself.
- **Time limits.** `$` calls do not count against the hook's time budget (`HookBudget`, `:4214-4228`). A cold `uv run` is therefore fine.
- **`$.tool.register` (`:2588-2609`).** Registers `mcp__<plugin>__<name>`, "Serve it with a `tool.call` hook on `{ tool: "mcp__<plugin>__<name>" }`… a call no hook answers fails".
- **`$.command.register` and `command.run` (`:2636-2649`, `:1480-1508`, `:3471-3481`).** Registers a slash command "for this session". `e.origin` is engine-stamped. `kind: 'composer'` means the person's own Enter, and "a channel the engine cannot attest… arrives as `unclassified`" (`:7025-7034`).
- **`$.fs.write` (`:2764`)** exists, so a hook can perform a write itself.

## 2. Can a hook inject a capability, or do the write itself?
- **An env capability through `$.env.set`: weak.**
  - It is process-wide, so the coordinator's subagents and any nested `claude -p` inherit it.
  - It is visible to `env` in Bash, so it can land in a transcript and be copied. That is the accident we are guarding against.
  - Python still needs a stored value to check it against.
  - #99137 (poteat, OPEN): where `sec-default` is installed, "With no policy to read every variable counts as pinned", and a plugin's `env.set` is refused.
- **The hook performs the privileged write: yes.** The model calls the registered tool. The hook checks `$.session.id()` and `e.agentId`, then either:
  - runs `$.process.run(["uv","run",…,"handoff-inbox","plan-apply",…])`, or
  - writes with `$.fs.write`.

  No Bash verb is needed.
- **Per-session scoping.** A registered tool exists in every session that loads the plugin, because skills-dir plugins load in lanes too. Lanes therefore see the tool, but its handler refuses them on `$.session.id()`.
- **A slash command restricted to its own session: yes, and human-only.** `$.command.register` scopes the command to the session. With `origin.kind === 'composer'` the hook can require that Ray typed it. That is unforgeable, but it cannot be driven autonomously.

## 3. Known hazards
- **#92533 is OPEN.** Probed live: `state=OPEN`, updated 2026-10-03T00:27Z, labels `has repro, area:hooks, area:agents`.
  - Two reporters reproduced it on **2.1.287**, with no fix noted.
  - rapuckett: mods now load by default with no `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS`, so a Bash-matched `tool.call` hook breaks `isolation:"worktree"` subagents in every session on the machine.
  - Same comment: "A `tool.call` hook that serves a plugin's own registered tool is safe". Their table: own-tool matcher ok 3/3 (and 3/3 after calling the tool); adding a `{tool:'Bash'}` passthrough refused 2/2; control with the plugin uninstalled ok 2/2.
  - cstarlea: `{tool:'Edit'}` is safe, while an unfiltered hook or `{tool:'Bash'}` breaks it.
  - The repo's own 2.1.269 arms agree (`docs/agents/goal-history.md:858-862`, main checkout): `classic.PreToolUse{tool=Bash}` did not break isolation.
- **`classic.PreToolUse` avoids the isolation bug but may not enforce, or even be delivered. This is new and unknown to the repo** (grep for `96831` in the repo docs: zero hits).
  - **#96831** (OPEN, 2.1.281): "classic.PreToolUse and skill.prompt not dispatched to modules". A `*` logger saw `tool.call`, `tool.check`, `command.run`, `turn.*` and `session.*`, but "no classic.* event".
  - **cstarlea on #92533** (2.1.287): a `classic.PreToolUse` `{deny}` on Bash "fired… but the command still ran, in both the main loop and a subagent".
  - These contradict the repo's 2.1.269 measurement that the deny was enforced even under bypassPermissions (`2026-09-11-function-hooks-firing-probe.md:95,112`).
  - **Consequence: install-doctor's gate (`.claude/skills/install-doctor/hooks/register.ts:385-428`) may have been silently inert since about 2.1.281.** It needs a probe on 2.1.288.
- **Failures fail open and silent.** Memory `project_session_2026-09-11-d` records wrong shape, overrun, wedge, or a forgotten `next`: the hook is skipped and the tool proceeds. Engine doc: "a hook that fails… is skipped: the hooks beneath and core run in its place" (`:3239-3241`).
  - For a deny gate that means fail-open.
  - For a registered tool, core is "a call no hook answers fails", so it **fails closed**.
- **`$.session.cwd()` inside a worktree subagent returns the parent's directory** (cstarlea, 2.1.287). Do not use cwd or root as identity.
- **#76726** (OPEN): settings-hook payloads for a subagent carry the parent's `session_id`. For settings hooks, only `agent_id` tells the subagent apart. For mods, only `e.agentId` does.
- **API churn.** Mods are pre-documentation (#91870, OPEN, 242 comments). Contract changes ship weekly, and a green `plugin validate` plus `tsc` does not prove runtime behaviour (`install-doctor/register.ts:13-18`).

## 4. Repo precedent
- **coordinator-handoff** (`.claude/skills/coordinator-handoff/hooks/register.ts:296-303`) already follows this pattern: `$.session.id()` → `$.process.run(["…coordinator-handoff","decide","--session-id",id])`, and Python owns the role check. `claude plugin validate` passes and lists `$.session.id` and `$.process.run`.
- **install-doctor** (`:385-428`) is the deny-gate precedent. It uses `classic.PreToolUse`, calls `next(e)` first, then returns `{deny}`. It is exposed to #96831.
- **session-start** (`:220,291`) uses `$.session.id()`.
- **No repo module uses `$.tool.register`, `$.command.register` or `$.env.set` today.**

## 5. GitHub sweep (gh `search/issues`, anthropics/claude-code; discussions are disabled there)
Each query's control arm is that it returned #91870 or #92533, both known to contain the term, which shows the search works.

| Query | Total | Relevant hits |
|---|---|---|
| `"tool.register"` | 4 | #99045 (VS Code never draws mod UI), #91870 |
| `"classic.PreToolUse"` | 5 | **#96831**, #92533, #95354 (a session hangs after a PreToolUse hook returns) |
| `"$.env.set"` | 2 | **#99137**, #91870 |
| `"command.register"` | 5 | #92533 (cstarlea's workaround keeps guard logic in a settings command hook and only slash commands in the mod) |
| `"agentId" "tool.call"` | 3 | #91870, #90347 |
| `hooks session_id spoof OR forge` | 561 | #84926 (no caller identity in the PreToolUse payload), #76726 |

**Negative result:** nobody upstream reported using a registered tool as a privileged write gate. rapuckett's own-tool evidence is about isolation, not about gating.

## 6. Probe evidence from this lane (claude 2.1.288)
- **P1.** `claude plugin list` shows four `@skills-dir` plugins (plugin-health, session-start, coordinator-handoff, install-doctor) with `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` **unset**, which is consistent with "default-on". `CLAUDE_CODE_SESSION_ID` is set.
  - Control: the `/usr/bin/timeout` call fell through to a mise shim error, so I reran without it. The listing alone does not prove the hooks fire.
- **P2.** `claude plugin validate .claude/skills/coordinator-handoff` passed and reported `$.session.id`, `$.process.run` and the env reads.
- **P3.** `~/.claude/debug/` holds one file (`latest`, Sep 2) with no `classic.PreToolUse` or `tool.call` lines. That is an empty result with no useful control, so it neither confirms nor refutes #96831.
- **Not run because this lane is read-only; each requires writing a probe plugin.** These are owed as **P4-P9** under Arms below.

## Options, recommended first

**1. Ancestry floor plus a mod-registered privileged tool. RECOMMENDED.**
How it works:
- Python keeps option (a): ps ancestry → `claude agents --json` → `lstart <= startedAt` → the env must agree → newest coordinator. `--jobs-dir` is dropped from the privileged verbs.
- The `coordinator-handoff` plugin, or a new `handoff-inbox@skills-dir`, registers `inbox_plan_apply`, `inbox_queue_append` and `inbox_edit` at `session.start`. It serves them with `on("tool.call", { tool: ["mcp__…__inbox_plan_apply", …] }, …)` and **never with a matcher that can hit Bash**.
- The handler denies when `e.agentId` is set (main loop only). Otherwise it runs `$.process.run([... "plan-apply", "--session-id", await $.session.id()], { stdin: editsJson })`. Python cross-checks that `--session-id` equals the session resolved by ancestry.

PRO:
- Host-supplied identity (`:2382`) plus the only subagent discriminator (`:164-175`). This answers the prior report's open question with "no, subagents may not".
- **Fails closed** when the hook breaks.
- Avoids #92533, per the own-tool table.
- The edit list travels as structured tool input, not shell text, so there is no quoting and no Bash route. That aligns with Ray's 2026-10-03 ruling (b) ("forbids routing that write through Bash", quoted in the `handoff_inbox.py` docstring).
- Same shape as the coordinator-handoff precedent.

CON:
- The Bash route still exists for coordinator subagents unless option 2 is added.
- Mods are undocumented and change often; there is a version-drift risk.
- The tool appears in every lane's tool list (context cost, a refusal on use).
- Rejects "inside a hook the turn is waiting on" applies to `$.command.run`, not here, but this still needs an arm.
- #99045: on the VS Code surface, mod UI does not draw. Tools are probably unaffected, but this is unverified.

**2. Option 1 plus a one-time nonce that closes the Bash route. Do this only if subagents must not write.**
How it works:
- For each call, the hook generates `T` with `crypto.getRandomValues`.
- It writes `sha256(T)`, the session id and an expiry of about 10 s to `<main>/.agent/state/handoff-inbox/grants/<tool_use_id>.json` with `$.fs.write`.
- It passes `T` **only on stdin**: not argv (visible in ps), not env, not the transcript.
- Python's privileged verbs require a matching unexpired grant and delete it on use.

PRO:
- `T` never appears anywhere a lane or a subagent could copy it, so neither the copied-command accident nor a subagent's Bash can pass.
- Replay is dead after one use.

CON:
- More moving parts: grant directory, clock skew, cleanup of orphaned grants.
- Not proof against a hostile same-uid process: the Write tool could forge a grant.
- If mods break, the coordinator loses its write path. That is fail-closed, which is correct, but it needs a documented break-glass, for example a Ray-typed slash command (option 4).

**3. `classic.PreToolUse` mod deny on Bash text. NOT RECOMMENDED now.**
PRO:
- In-process.
- Safe for isolation (repo arm F; cstarlea).
- Existing precedent in install-doctor.

CON:
- #96831 (not delivered on 2.1.281), and cstarlea's report that the deny was not enforced on 2.1.287.
- `e` has no `agentId` (`:951-953`).
- It matches command text, so a script gets past it.
- It fails open and silent.

Use it only if probe P5 shows it is delivered and enforced on 2.1.288. Otherwise use the settings command hook (`hook_guard`, the prior report's option c′), which carries `agent_id` and is cstarlea's working workaround.

**4. A Ray-typed slash command (`$.command.register` with `origin.kind==='composer'`). Optional, for human approval or break-glass.**
PRO:
- An engine-stamped human gesture (`:7025-7034`), scoped to the session (`:2636`).
- The model cannot impersonate it.

CON:
- The coordinator cannot use it autonomously.
- Whether the Skill tool can invoke a registered command, and with what origin, is unverified (probe P8).
- Same mod fragility as option 1.

**5. `tool.call{tool:"Bash"}` deny or rewrite. REJECTED.**
PRO: structured args; can deny or rewrite.
CON: #92533 is OPEN and reproduced on 2.1.287. Because mods are default-on, it would break every `isolation:"worktree"` subagent for every session on this machine.

**6. `$.env.set` capability. REJECTED.**
CON:
- Session-wide, not per-call (`:3005-3033`).
- Inherited by subagents and nested claude.
- Readable and copyable from `env`.
- Refused under sec-default (#99137).
- Still needs a Python-side store.

## Arms the implementation needs
**Probes to run first (each with a no-plugin control arm):**
- **P4.** An own-tool `tool.call` hook coexists with `isolation:"worktree"` Bash on 2.1.288. Repeat rapuckett's table locally.
- **P5.** Are `classic.PreToolUse` deny on Bash and on Read delivered and enforced on 2.1.288? If not, open an issue to audit install-doctor (#96831).
- **P6.** Inside a subagent's call to the registered tool, `e.agentId` is present; on the main loop it is absent. Also, is `$.session.id()` the parent's id inside a subagent? Expect yes.
- **P7.** A lane session calling the tool is refused on `$.session.id()`.
- **P8.** Can the Skill tool run a `$.command.register` command, and what origin does it report?
- **P9.** Does a hook throw or overrun leave the registered tool failing closed?

**Unit and integration arms:**
1. Main loop of the newest coordinator → write ok.
2. Same session, `e.agentId` set → deny.
3. Lane session → deny.
4. Superseded coordinator → deny.
5. Python `--session-id` disagrees with ancestry → refuse.
6. All prior-report ancestry arms (1-13).
7. The handler's Python call fails or returns bad JSON → `{result}` reports an error and nothing is written.
8. If option 2 is adopted:
   - a missing grant, an expired grant, a reused grant and a wrong hash → refuse;
   - `T` is absent from argv (checked against ps) and absent from the transcript.
9. A `plugin validate` and `tsc` gate over the module, plus a behavioural probe at each claude upgrade, because a green build proves nothing at runtime.
10. A static check that no module's `tool.call` matcher can match Bash: no bare `tool.call`, no `*`, no `{tool:"Bash"}`.

## GitHub repos touched
None were modified: no edits, commits, PRs or comments. Read from:
- `ray-manaloto/dotfiles`: the coord-28f1a8f7 worktree, the L0-urgent-code worktree at `912e843c`, and the main checkout's `docs/agents/goal-history.md`.
- `ray-manaloto/knowledge-base`: `$CC` docs.
- `anthropics/claude-code` through `gh`: issues #92533, #96831, #76726, #84926, #99137 and #91870, plus six search queries.

### Critical files for implementation
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/L0-urgent-code/python/src/dotfiles_setup/handoff_inbox.py
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/coord-28f1a8f7/.claude/skills/coordinator-handoff/hooks/register.ts
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/coord-28f1a8f7/.claude/skills/install-doctor/hooks/register.ts
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/coord-28f1a8f7/.claude/types/claude-code.d.ts
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/L0-urgent-code/tests/test_handoff_inbox.py
