# The agent team — design, evidence, and what we borrowed

**Status: research synthesis, nothing built yet.** This is the living document for the
reusable agent team. Iterate on it; file bugs against it; do not treat any section as
settled once reality moves.

Research run 2026-08-04c by seven parallel agents. Their verbatim reports are the
evidence base and are kept alongside this file:

| Report | Covers |
|---|---|
| `docs/research/kb/reports/agents/fw-alpha-frameworks.md` | oh-my-claudecode · cc-native · claude-code-harness |
| `docs/research/kb/reports/agents/fw-beta-frameworks.md` | claude-code-kit · conductor-skills · claude-self-reflect |
| `docs/research/kb/reports/agents/fw-gamma-frameworks.md` | claude-relay · claude-code-gauntlet · cc10x · cc-dm |
| `docs/research/kb/reports/agents/symphony-and-ports.md` | openai/symphony + stokowski · hatice · phonyhuman · itervox |
| `docs/research/kb/reports/agents/market-scan.md` | 2,298-plugin marketplace enumeration · independent sweep · `/last30days` |
| `docs/research/kb/reports/agents/harness-settings-reference.md` | every knob: frontmatter × env vars × settings.json × mode |
| `docs/research/kb/reports/agents/lane-economics.md` | Codex offload · Fable routing · cost model |

Offline vendor docs are cited as `$CC/<page>.md:<line>`, where `$CC` is
`~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`.
Live equivalents are `https://code.claude.com/docs/en/<page>.md`.

---

## 1. The finding that reframes the whole request

**`openai/symphony` has no role taxonomy.** It is a single-agent-per-ticket daemon: one
Codex session per issue, in an isolated workspace, driven by an issue tracker. What looks
like roles are tracker *states* and on-demand *skill files* the one agent opens.

Control-armed, in the symphony clone: `role|persona|planner|architect|sub-?agent|multi-agent`
returns **0** across `SPEC.md`, `README.md` and `elixir/WORKFLOW.md`, while the control term
`orchestrator|workspace` returns **202** in `SPEC.md` with the same command shape. The probe
discriminates, so the zero is real.

> "Symphony is a scheduler/runner and tracker reader." — symphony `SPEC.md:38`

**Consequence: a nine-role taxonomy is an addition to symphony, not a port of it.** The one
port that added roles — `Sugar-Coffee/stokowski`, 112★ — says so itself:

> "Symphony uses a flat model — issues are either active or terminal, and agents run until
> the issue moves to a done state. There's no concept of stages, gates, or transitions."
> — stokowski `README.md:175`

Stokowski's replacement is the most directly useful artifact in the survey: a configurable
state machine with three typed states — `agent` (dispatches a runner), `gate` (moves to a
review state and **waits for a human**), `terminal` (cleans up the workspace) — with
per-state `runner`, `model`, `max_turns`, `turn_timeout_ms`, `stall_timeout_ms`,
`permission_mode`, `allowed_tools`, `hooks`, `transitions`, `rework_to` and `max_rework`
(`stokowski/config.py:101-120`, validated at `:633-645`).

That is a better shape than "nine agents", because it makes the **human gate** a first-class
node rather than an implicit pause.

---

## 2. The mechanism decision

Claude Code offers three ways to run work in parallel. They differ in **who holds the plan**,
and therefore in what you can version and improve later (`$CC/workflows.md:23-32`):

| | Subagents | Agent teams | Workflows |
|---|---|---|---|
| Who decides what runs next | Claude, turn by turn | The lead agent, turn by turn | The script |
| Where intermediate results live | Claude's context | A shared task list | Script variables |
| **What's repeatable** | **the worker definition** | **the team definition** | **the orchestration itself** |
| Scale | a few per turn | a handful of peers | dozens to hundreds per run |
| Interruption | restarts the turn | teammates keep running | resumable in-session |

### The decision: subagents are the spine

Orchestrator at layer 1, the role agents at layer 2, their helpers at layer 3. Workflows
carry any DAG worth versioning. Agent teams are reserved for the one thing subagents
structurally cannot do — lateral argument between peers.

**Four pieces of evidence drive this.**

**(a) Nested subagents make an orchestrator agent possible.** Default depth is **3 layers**
below the main conversation, adjustable with `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`
(`$CC/sub-agents.md:862`). Verified three independent ways: the docs page, the changelog,
and `gh api repos/anthropics/claude-code/releases` → v2.1.219 *"Subagents can now spawn
nested subagents up to depth 3 by default (was 1)"*. The history matters — 2.1.172–216
nested five deep and uncapped, 2.1.217–218 defaulted to **one**, 2.1.219 settled on three.

**(b) Teammates lose most of the tuning surface.** `$CC/agent-teams.md` states plainly that
*"the `skills` and `mcpServers` frontmatter fields in a subagent definition are not applied
when that definition runs as a teammate"*, that permissions are the lead's and cannot be set
per teammate at spawn, and — separately — that **teammates cannot spawn teammates**
(`agent-teams.md:425`, byte-identical in the live doc and the offline snapshot at the same
line number).

**(c) Teams cost multiples.** Official: *"approximately **7x** more tokens than standard
sessions when teammates run in plan mode, because each teammate maintains its own context
window and runs as a separate Claude instance"* (`$CC/costs.md:246`), with usage *"roughly
proportional to team size"* (`:139-140`) and each idle teammate still consuming
(`:141`). Third-party [CloudZero](https://www.cloudzero.com/blog/claude-code-agents/)
measures multi-agent at 4–7× and **Agent Teams at ~15×**, because every inter-agent message
is a full model round trip.

**(d) A team's composition is not a file you can keep.** *"There is no project-level
equivalent of the team config"*, and the generated one *"holds runtime state … don't edit it
by hand or pre-author it: your changes are overwritten on the next state update"*
(`$CC/agent-teams.md` § Architecture). With teams, the **roles** are versionable and **the
team is not** — which is fatal for "reuse and keep improving".

### The cost of this decision, stated

Subagents have **no mailbox**. Roles report upward; they cannot challenge each other
laterally. Where genuine disagreement is the point — adversarial review, competing
hypotheses — a team is the only native mechanism, and it is worth its 7–15× there and
nowhere else.

And a hybrid can be **silently misconfigured**: `skills:` set on a role that is later spawned
as a teammate does nothing and raises no error. Mitigation is cheap and mandatory — every
role file states which execution modes it is meant for.

---

## 3. The nine roles, after contact with the evidence

Ray's list: orchestrator · planner · researcher · executor · qa · adversarial-review ·
self-learning/self-optimizer · documentation · suggestions.

Two of them are not agents.

**`self-learning/self-optimizer` is mostly a field, not a role.** `memory` is per-agent
frontmatter with `user` / `project` / `local` scope, described as *"Enables cross-session
learning"*, writing to `.claude/agent-memory/<agent>/` (`$CC/sub-agents.md:287`, `:512-514`).
Under `project` scope, what an agent learns is **checked into git**. So: memory on the
working roles, and *one* optimizer agent that periodically reads the accumulated memories and
proposes edits to the role files. ⚠️ It is gated — `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`
disables auto memory **and with it the `memory` frontmatter field entirely**
(`$CC/sub-agents.md:518`).

**`provide suggestions` is an output contract, not a role.** Every role's report ends with
what it would change. A dedicated suggester has no privileged view.

That leaves **seven working roles plus one optimizer**. The remaining question — and it is a
real one — is whether to build all eight before the team has ever run. The vendor's own
advice is to start small (`$CC/agent-teams.md` § Choose an appropriate team size).

**Add a ninth node that Ray did not ask for: a `gate`.** Stokowski's typed `gate` state is
the mechanism that makes unattended running safe, and `cc10x`'s `AUTO_PROCEED` dial shows the
shape — an autonomy setting with a carved-out exception list that **cannot** auto-answer a
revert, a failure-stop, a destructive finishing option, or a plan with unresolved open
decisions, and that logs every auto-choice.

---

## 4. The tuning surface

Sixteen frontmatter fields exist (`$CC/sub-agents.md:277-292`), covering every knob Ray
named plus four he did not:

`name` · `description` · `tools` · `disallowedTools` · `model` · `permissionMode` ·
`maxTurns` · `skills` · `mcpServers` · `hooks` · `memory` · `background` · `effort` ·
`isolation` · `color` · `initialPrompt`

Which apply in which mode is **partly undocumented**, and the honest state is recorded in
Table D of `docs/research/kb/reports/agents/harness-settings-reference.md`, where every cell
is `DOCUMENTED-APPLIES`, `DOCUMENTED-IGNORED` or `UNDOCUMENTED` — **none guessed**, each
undocumented cell carrying the experiment that would settle it. Two near-resolutions from the
changelog rather than a probe: v2.1.186 fixed teammates to *"inherit the leader's `--effort`
level"*, which implies per-teammate `effort` frontmatter is not honoured; v2.1.183 records
that background tasks started by a teammate are **killed when the teammate finishes a turn**.

### The limits that bound any design

| Variable | Default | What happens at the limit |
|---|---|---|
| `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` | **3** | the `Agent` tool is *withheld* from subagents at depth; `1` turns nesting off |
| `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` | **200** | `Subagent spawn limit reached`; `/clear` resets it |
| `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` | **20** | spawn fails, retry discouraged; **ultracode sessions are exempt** |
| `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` | **10** | the parallel-execution scheduler, distinct from the spawn gate |
| `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` | **8** | after 8 consecutive blocks Claude Code **overrides the hook** and ends the turn |
| Workflow runtime | 16 concurrent / 1,000 per run | hard caps inside a single workflow |

Every numeric variable above **ignores an unparsable value** rather than erroring, so a
typo silently restores the default — with the exception of `CLAUDE_CODE_MAX_TURNS`, which is
rejected at startup. Full enumeration, including 329 uppercase tokens shape-grepped from the
env-var page rather than an expected list, is in the settings report's Table B.

**One coordination primitive worth knowing:** `CLAUDE_CODE_TASK_LIST_ID` shares a single task
list **across sessions** — the only documented cross-session coordination mechanism besides
agent teams.

---

## 5. Codex offload vs maximizing Fable — the tension dissolves

Ray asked for both *"use my codex subscription plan to offload some of the tokens"* and
*"maximize my fable-5 model tokens whenever possible"*. They act on different layers and do
not compete.

**This machine is on a ChatGPT Pro subscription.** `auth_mode: chatgpt`,
`chatgpt_plan_type: pro` (read from the `id_token` entitlement claim), `OPENAI_API_KEY`
absent from both `~/.codex/auth.json` and the shell environment — determined without printing
any credential. So Codex work is **consumption against a plan, not a marginal dollar cost**.

**Only one of the two levers actually buys headroom.** From `$CC/costs.md:128`:

> "These windows are shared across all models, so switching models with `/model` doesn't
> restore access"

Moving Claude work from Fable to Sonnet does **not** recover a hit weekly cap. Offloading to
Codex is the only lever that extends the Claude budget at all.

**Model precedence, exact** (`$CC/sub-agents.md:303-308`) — highest wins:

1. `CLAUDE_CODE_SUBAGENT_MODEL` (covers subagents, teammates **and** workflow agents)
2. the per-invocation `model` parameter
3. the definition's `model:` frontmatter
4. the main conversation's model

`fable` is a documented value at every one of those layers (`$CC/model-config.md:35`,
`$CC/sub-agents.md:298`, `$CC/model-config.md:154`). Two constraints: **Fable 5 is never a
default** — *"Sessions use Fable 5 only after you choose it"* (`$CC/model-config.md:342`) —
and **thinking cannot be disabled on Fable 5**, so its per-token spend is governed by
`/effort`, not by turning thinking off (`$CC/model-config.md:530`).

**Mechanically, Codex is always `Bash` shelling out.** There is no MCP transport and no
in-harness binding; both installed plugins declare `tools: Bash, …` and run a subprocess. The
`fable-orchestrator` lane's real command (`run-lane.sh:63-66`):

```
codex exec --model "${MODEL:-gpt-5.6-sol}" -c model_reasoning_effort=high $FAST \
    --sandbox workspace-write --skip-git-repo-check --cd "$(pwd)" \
    --output-last-message "$FINAL" - < "$SPEC" > "$LOG" 2>&1
```

It runs detached with its own process group and a bash watchdog (default 1800s for
implementation, 600s for review/research) because *"the harness caps any foreground tool call
at 10 minutes"*, and the wrapper polls in ≤90s slices because the harness auto-backgrounds a
foreground call after ~2 minutes.

**The wrapper is not free.** A Sonnet wrapper pays for its own system prompt and definition,
for writing the full spec as output tokens, for one tool-call round trip **per 90 seconds of
Codex wall clock**, for reading the diff and verification evidence, and for the report that
then lands in the architect's context at architect prices. What is free at the margin is
everything inside `codex exec`. **The corollary is a break-even: a small task's wrapper tax
exceeds what it offloads.** The exact per-delegation cost on this machine is **UNVERIFIED**;
`/usage` (press `w`) attributes recent usage to skills, subagents, plugins and MCP servers
and is the instrument that would settle it (`$CC/costs.md:36`).

⚠️ **Fast mode is a credit trade, not a saving** — *"~1.5x output speed for ~2–2.5x credit
burn"*, and it requires ChatGPT sign-in, which is satisfied here.

⚠️ **UNVERIFIED and worth filling before sizing a build:** OpenAI's published Codex rate
limits for ChatGPT Pro. Do not infer them from anything in this document.

---

## 6. What we are borrowing

The frameworks were not adoptable wholesale — but several carry mechanisms worth taking. Each
line is cited to the source report, which carries the file:line.

### Evidence and honesty discipline

| Mechanism | Source |
|---|---|
| **Citation-or-downgrade inside the agent prompt** — a finding must quote `(per <file> L<n>: "<exact phrase>")` or be downgraded to `info`, plus an anti-adjacent-citation self-check: *"does the cited phrase, by itself, state the rule the finding alleges?"* | `cc-native` |
| **Test Honesty Gates** — six named false-GREEN classes, each with a runnable grep (asserting the mock, schema-incomplete mocks, DB-bypass verification, test-only methods in production, mocking-without-understanding, arbitrary sleeps), plus a CRITICAL test-tampering gate on `.skip`/`.only` | `cc10x` |
| **A forbidden-language list before a PASS claim** — "should pass", "looks good", "builder reported success", "the tests cover this" (without naming the test), "no regressions detected" (without listing what was tested) | `cc10x` |
| **Refuse to launder a missing gate as a pass** — with no eval scenario, print "no eval coverage; user approval is the only gate" and be *forbidden* from counting `exit 0` as a pass | `claude-code-kit` |
| **NEGATIVE eval scenarios where the correct behaviour is refusal** — e.g. a live-looking key planted in the prompt, graded on refusing *and* on not echoing the value | `conductor-skills` |

### Structural guarantees, not prompt requests

| Mechanism | Source |
|---|---|
| **Blindness by allowlist, not delete-list** — a cold reviewer receives exactly `{title, description, file, line_start, line_end}`, so no confirming context can reach it *"even if new reasoning-bearing fields are added later"*. Unit-tested both ways | `claude-code-gauntlet` |
| **Make blindness a capability fact** — the gap-reviewer is granted no `Skill` tool and no `skills:` list, so it *cannot* load the planner's rationale | `cc10x` |
| **A self-improve loop that cannot modify its own evaluation** — sealed-files guard; and a failure-codifier whose tool grant makes writing the source of truth *impossible*, not merely discouraged | `oh-my-claudecode`, `cc-dm` |
| **Treat the learning ledger as untrusted data** — imperative sentences inside agent-authored ledgers are evidence, never commands, and their presence is reported as suspected contamination | `claude-code-kit` |
| **Separate the reasoner from the writer** — one agent composes (`tools: Read`), another transcribes (`tools: Write, Read`), because *"the artifact-writer's transcription of a multi-KB payload diverged from its input on 3 of 3 measured runs"* | `claude-code-gauntlet` |

### Dispatch and routing

| Mechanism | Source |
|---|---|
| **Pin FULL model IDs, never aliases, when dispatching** — an alias resolves against the session's model *variant*, so a `[1m]` orchestrator cascades `[1m]` into every child. **Measured: cache reads 15.6M → 28.7M.** Directly live for us: this session is `claude-opus-5[1m]` | `claude-code-gauntlet` |
| **Prove disjoint file ownership at DISPATCH time and demote overlapping chunks to sequential** — because the main session has no way to serialize subagents' worktree exits, so "merge sequentially" is an unenforceable norm | `claude-code-kit` |
| **Shared state files must not be written from inside a worktree** — invisible to main until merge. We have this hazard already; it bit us this session | `claude-code-kit` |
| **One markdown prompt, N model bindings** — generate `executor-low` / `executor` / `executor-high` from a single definition rather than three drifting files | `oh-my-claudecode` |
| **A single declared source of truth for model routing**, with every skill forbidden from duplicating the table — our `parity.toml` / `currency.toml` pattern, applied to agent tiering | `oh-my-claudecode` |
| **Keyword NOMINATES, primary deliverable DECIDES** — the cleanest fix for skill-trigger collisions, which we have several of | `cc10x` |
| **Model/effort ladder tied to read-vs-write** — haiku+low for read-only scanners, opus+max only for adversarial review and requirement clarification | `claude-code-kit` |

### Contracts and enforcement

| Mechanism | Source |
|---|---|
| **Versioned JSON contracts between agents** — every agent's output is a schema-validated object with a `schema_version`, not prose. This is what makes a multi-vendor swap safe | `cc-dm` |
| **The external-CLI verdict file contract** — a codex/gemini worker cannot call the task tools, so it writes typed JSON to a pre-agreed path and the leader reads it and updates on its behalf. Exactly the missing piece in our current codex lane, where the report is free prose | `oh-my-claudecode` |
| **A `Stop` hook returning `{"decision": "block", "reason": …}`** to force a review before a turn can end — *"Stop hooks cannot spawn subagents directly; `decision: block` is the documented mechanism"*. Note the loop-guard trap: anchor on the last auditor invocation, not the last user turn, or every block reads as a new user turn | `cc-native` |
| **An LLM gate wired into `PreToolUse`** — a `"type": "agent"` hook, `model: haiku`, adjudicating every `Write`/`Edit` with authority to **deny**. The judgment-shaped complement to our deterministic Python guard | `oh-my-claudecode` |
| **`SubagentStop` wired to a contract audit** — the mechanism our repeatedly-failing "a subagent must deliver before going idle" rule actually needs | `cc10x` |
| **A three-key strictness dial per concern** (`block` vs `audit`), so a guard can be introduced in audit mode and promoted | `cc10x` |

### Handoff hazards, learned the expensive way by someone else

| Mechanism | Source |
|---|---|
| **Measure the artifact in the same command that writes it, and pass the measurement to the reader** — a `Read` of a large file returns part of it and emits **no truncation notice**. Recorded incident: all 7 agents' first read of a 95,057-byte file returned 58,145 chars ending at line 1083 with no notice; six inferred it and paginated, one did not and reviewed half the diff while returning `complete: true` | `claude-code-gauntlet` |
| **Never resolve a plugin root by searching the filesystem** — a recorded run picked 3.2.3 out of a four-version cache while 3.3.1 was installed. *"The path you were loaded from is the only correct answer; a `find` hit is a coin flip between every version ever installed"* | `claude-code-gauntlet` |
| **Fail loud on an unguarded handoff read** — a missing rules file means the collection step never ran, and *"the write must fail loudly rather than produce a context file whose empty rules section is indistinguishable from a repo with no convention files"* | `claude-code-gauntlet` |
| **Deliberate verbatim duplication of critical instructions, with an explicit anti-refactor note** — collapsing them into a cross-reference reintroduces the exact failure they fixed | `claude-code-gauntlet` |
| **A `PreCompact` hook that re-injects identity the model is about to lose**, and stamping durable context onto every tool response so the first call after any context loss re-establishes state | `cc-dm` |
| **Exit on stdin EOF plus a parent-pid liveness poll** for any long-lived process spawned from a session — *"Claude Code sends no shutdown signal, and the MCP stdio transport ignores stdin EOF, so a channel would otherwise outlive its session forever"* | `claude-relay` |

---

## 7. What the field says, and what it warns about

The marketplace was enumerated in full rather than sampled: **2,298 plugins**, of which 216
strongly match orchestration vocabulary and **~58** are generic agent-team frameworks (2.5%).

**A hype wave that crested in Feb–March 2026 and receded.** Of thirteen projects built on
native Agent Teams, seven have not moved since March — including the two most-starred
(`clawport-ui`, 899★, frozen 2026-03-24; `HydraTeams`, 68★, frozen 2026-02-08).

**There is no maintained, popular, general-purpose Claude↔Codex team framework.** Nine
projects run the exact pattern; every one is a solo effort under 10 stars. The pattern is
widely reinvented and nowhere consolidated — which is an argument for building on native
primitives rather than adopting anyone's framework.

**Three warnings worth internalising:**

- **The parallelism often isn't there.** [@liustack](https://x.com/liustack/status/2082576866083536983)
  (2026-07-29) reports a tester finding *an enormous volume of useless inter-agent
  communication, all of it tokens*, and cites a Google evaluation concluding these team
  architectures are ineffective most of the time and good only on highly-parallel tasks —
  while most real tasks are not highly parallel. Single-source, and **the cited evaluation is
  UNVERIFIED**.
- **Observability, from the highest-engagement item in the window.**
  [IndyDevDan](https://www.youtube.com/watch?v=WAFUMBLOjHo) (32,449 views):
  *"An agent you can't SEE is an agent you can't improve. Spinning up 20 agents in a loop and
  looking the other way isn't agentic engineering, it's gambling with tokens."* That is a
  critique of exactly the "fan out nine roles" shape.
- **The failure modes are already catalogued.** [arXiv:2607.22917v2](https://arxiv.org/abs/2607.22917v2)
  (submitted 2026-07-24) names four for long-lived Claude Code agent teams: irrecoverable
  state when processes end, compaction eroding working detail, decisions trapped in compacted
  chats, and heavy prompt-writing burden. **None is solved by the native feature**, and all
  four are requirements for the "reusable, self-improving" half of the ask. Its remedy is a
  filesystem operations layer — per-agent directories, periodic backups, single-command
  restoration, inter-agent document sharing.

⚠️ **Coverage caveat on the sentiment sweep:** web grounding returned HTTP 422, and TikTok
and Instagram both returned HTTP 402 (quota exhausted). Those three sources were never asked,
so their silence is not evidence.

---

## 8. This project's current setup — the audit

Full detail in Part 2 of `docs/research/kb/reports/agents/harness-settings-reference.md`. The
audit produced a **live measurement** worth recording first: the auditing agent observed its own
tool inventory and found that **a teammate runs with the BACKGROUND tool set, not the foreground
one** — a fact neither `$CC/agent-teams.md` nor `$CC/sub-agents.md` states outright. n=1,
self-observed, control-armed by the fact that the absences are not a generic empty list
(`Agent`, `SendMessage` and the task tools *are* present, so the inventory discriminates).
Confirm on a second session before building on it.

### Already correct

`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is `"1"` at both user and project scope and they agree.
`CLAUDE_CODE_FORK_SUBAGENT` is on — and a fork **inherits the full parent context and reuses its
prompt cache**, the cheapest way to hand an agent the lead's context. `permissions.defaultMode:
"auto"` is at **user** scope, which is the only scope where it is honoured.

### Defects found

| | Finding |
|---|---|
| 🔴 | **`AskUserQuestion` does not exist inside a delegated agent** — filter 1 removes it (`$CC/sub-agents.md:329`), confirmed by direct observation. But `.claude/rules/clarify-before-acting.md` says using that tool is *"the **mechanism** rule and it is unconditional"*. So **every teammate is structurally incapable of obeying it**, and the only available fallback — prose options — is what the rule forbids. The `ask_quality` gate never fires because the tool is never called. **The rule needs a clause: a delegated agent escalates via `SendMessage`; the lead owns every `AskUserQuestion`.** |
| 🔴 | **The branch guard denies teammate writes, and the denial arrives *after* the work.** At nine agents this scales from annoyance to total loss, because `agent-report-persistence.md` requires each to persist verbatim. A **`SubagentStart` hook refusing to start a writing agent on the default branch** would move the failure to before the work. |
| 🟠 | **Teammates share one working directory and nothing isolates them** — *"Two teammates editing the same file leads to overwrites."* Disjoint file ownership has to be enforced in the spawn prompt, because no config enforces it. |
| 🟠 | **The PreToolUse guard is paid per agent.** Three hook entries mean a Bash call fires two hook processes. The write guard is already measured at **~340 ms/edit**; nine agents pay it independently. That is a quantified reason to finish that optimisation *before* scaling, not after. |
| 🟠 | **The graphify nudge is injected into every Bash/Grep/Read/Glob of every agent** — observed **7 times** inside one agent's run, and pure noise for an agent working outside the graph's scope. Scope the matcher, or make it one-shot per agent. |
| 🟡 | **`ship`/`land` are single-writer verbs with no team story.** Once `ship` arms auto-merge the branch is closed; any teammate calling it ends the branch for everyone. The spawn prompt must forbid both and reserve them for the lead. |
| ⚠️ | **`teammateMode` conflicts**: user says `"tmux"`, project says `"auto"`, project wins — silently overriding an explicit user choice. |
| ⚠️ | **`permissions.defaultMode: "auto"`** means a teammate's own `permissionMode` frontmatter is **ignored entirely** (`$CC/sub-agents.md:467`). |
| 🔴 | **INERT, and failing permissive:** `~/.claude/settings.json` carries `ENABLE_CLAUDEAI_MCP_SERVERS: "false claude"` — the seven-character string, not `false`. The evident intent was to disable those servers; a non-`false` value almost certainly leaves them **enabled**. Looks like a paste accident. *Not touched* — user-level file, flagged only. |
| 🟡 | Four more user-scope keys have **0 hits** in the live docs (control-armed against keys that do resolve): `autoDreamEnabled`, `skipWorkflowUsageWarning`, `skipAutoPermissionPrompt`, `CLAUDE_CODE_BRIEF`. Assume inert. |

### Absent, and what it costs

- **`teammateDefaultModel`** — teammates do **not** inherit the lead's `/model`. Nothing sets a
  default, so nine agents land on the harness default rather than a deliberate choice. **The
  single largest unmanaged cost lever.**
- **`worktree.baseRef`** — defaults to `"fresh"`, i.e. `origin/<default-branch>`. Any agent given
  `isolation: worktree` branches from **`origin/main`, not the working branch** — so on a feature
  branch it gets a tree without the branch's commits. In a repo where all work must be on a
  branch, `"head"` is almost certainly what is meant. Highest-value absent setting after the model.
- **`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`** — inherited silently at 3. Worth pinning explicitly,
  since the default has changed **three times in five releases** (5 → 1 → 3).
- **`~/.claude/agents/` does not exist**, and the watcher covers only directories present at
  session start — so the first file created there **will not be picked up without a restart**.
  Create the directory before the session that needs it.
- **Only 2 agent definitions exist** for a 9-role design.

### One constraint on the design itself

A reviewer agent **cannot be given `/code-review` by preloading**: skills marked
`disable-model-invocation: true` cannot be preloaded through a definition's `skills:` field
(`$CC/sub-agents.md:487`). That matches this repo's existing finding that the protocol verbs are
user-invoked only.

Also worth knowing: `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` is on, and with two sibling
repos added, **every agent inherits three repos' rule sets** — a context cost multiplied by the
team size.

---

## 9. Before any team ships — the blocking fixes

The audit turned three of these from "nice to have" into preconditions:

1. **Amend `.claude/rules/clarify-before-acting.md`** so a delegated agent escalates by
   `SendMessage` and the lead owns every `AskUserQuestion`. Until then the rule is a requirement
   nine agents will violate silently.
2. **Set `worktree.baseRef: "head"`** before any agent runs with `isolation: worktree`, or it
   works from a tree without the branch's commits.
3. **Set `teammateDefaultModel`** deliberately rather than inheriting the harness default.
4. **Reserve `ship` / `land` / `automerge` to the lead**, in the spawn prompt.
5. **Finish the ~340 ms/edit guard optimisation** before multiplying it by the team size.
6. Decide whether the branch precondition becomes a **`SubagentStart` hook** rather than a habit.

## 10. Open questions

1. **How many roles to build before the first run?** Eight definitions written before the
   team has run once are eight guesses. The vendor advises starting small.
2. **`memory` scope per role** — `project` puts what an agent learns into git and makes it
   reviewable; `local` keeps it out. This is a per-role decision, not one global choice.
3. **The undocumented cells** in Table D — each has a one-line experiment attached; none has
   been run.
4. **The wrapper tax**, in real numbers, from `/usage`.
5. **OpenAI's Codex rate limits on ChatGPT Pro** — the one factual gap that a build size
   would depend on.
6. **Observability** — the field's loudest warning, and we have nothing designed for it yet.

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo this design is for
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — release notes cross-checking nesting depth and team fixes
- [anthropics/claude-plugins-community](https://github.com/anthropics/claude-plugins-community) — the 2,298-plugin marketplace enumeration
- [openai/symphony](https://github.com/openai/symphony) — the reference design; source of the no-role-taxonomy finding
- [Sugar-Coffee/stokowski](https://github.com/Sugar-Coffee/stokowski) — the only port with a role taxonomy; typed state machine and gate states
- [mksglu/hatice](https://github.com/mksglu/hatice) — closest structural port, on the Claude Agent SDK
- [manav03panchal/phonyhuman](https://github.com/manav03panchal/phonyhuman) — hard fork of symphony's Elixir with a protocol shim
- [vnovick/itervox](https://github.com/vnovick/itervox) — symphony port
- [yeachan-heo/oh-my-claudecode](https://github.com/yeachan-heo/oh-my-claudecode) — CLI-worker verdict contract, agent-tier source of truth, sealed-files self-improve guard
- [GarySonyak/cc-native](https://github.com/GarySonyak/cc-native) — Stop-hook review gate, citation-or-downgrade discipline, per-version subagent changelog
- [Chachamaru127/claude-code-harness](https://github.com/Chachamaru127/claude-code-harness) — reviewed
- [This-HW/claude-code-kit](https://github.com/This-HW/claude-code-kit) — dispatch-time disjointness, false-green refusal, ledger trust boundary
- [conductor-oss/conductor-skills](https://github.com/conductor-oss/conductor-skills) — rubric-graded skill evals with negative scenarios
- [ramakay/claude-self-reflect](https://github.com/ramakay/claude-self-reflect) — compared against the native `memory` field
- [vildanbina/claude-relay](https://github.com/vildanbina/claude-relay) — peer naming, anti-broadcast rule in the tool schema, parent-liveness watchdog
- [liatrio-labs/claude-code-gauntlet](https://github.com/liatrio-labs/claude-code-gauntlet) — allowlist blindness, full-model-ID pinning, silent-truncation incident, reasoner/writer split
- [romiluz13/cc10x](https://github.com/romiluz13/cc10x) — test honesty gates, forbidden-language list, routing rule, autonomy dial
- [Akram012388/cc-dm](https://github.com/Akram012388/cc-dm) — versioned JSON agent contracts, capability-enforced self-promotion ban, skeptic lens
- [JohnRiceML/clawport-ui](https://github.com/JohnRiceML/clawport-ui), [Pickle-Pixel/HydraTeams](https://github.com/Pickle-Pixel/HydraTeams), [aws-samples/sample-claude-code-agent-team](https://github.com/aws-samples/sample-claude-code-agent-team), [Gr122lyBr/claude-teams-brain](https://github.com/Gr122lyBr/claude-teams-brain), [ShawhinT/subagents-vs-teams](https://github.com/ShawhinT/subagents-vs-teams), [shirleyfuxw/team-forge](https://github.com/shirleyfuxw/team-forge) — the native-Agent-Teams ecosystem and its maintenance dates
- [M-yer/claude-agent-squad-codex](https://github.com/M-yer/claude-agent-squad-codex), [a1-ceo/claude-agent-squad](https://github.com/a1-ceo/claude-agent-squad), [jonathanavni/tinytandem](https://github.com/jonathanavni/tinytandem), [chorious/AgentCall](https://github.com/chorious/AgentCall), [ZaMpAdAKiNg/orchestrate-skill](https://github.com/ZaMpAdAKiNg/orchestrate-skill) — the Claude↔Codex offload pattern, independently reinvented
