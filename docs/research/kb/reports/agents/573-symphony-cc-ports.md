# 573 — Symphony Claude Code ports survey

**STATUS: complete** (2026-08-05)

**Headline:** cymphony is a full Elixir rewrite of symphony behind a pluggable
agent-CLI adapter, and it is **Linear-only — it does not use GitHub Issues as a
tracker**, so its value to #573 is dispatch and env mechanics, not tracker design. The
tracker-as-database pattern comes from stokowski, whose entire durable-state layer is
**165 lines** of HTML-comment marshalling. The one architectural decision both ports
put in front of us: DAG gating belongs either in the tracker adapter (symphony's
`dispatchable` boolean) or in the scheduler (cymphony's choice, which its own code
comment misattributes to a SPEC section that says the opposite — §1.6).

**§5 (added on request, Linear vs GitHub Issues):** symphony ships **five** adapters
including GitHub, but only **Linear and Jira** have real blocker support — GitHub,
GitLab and Asana all hardcode `blocked_by: []` (§5.3). That reads as a point for Linear
until you check why: **GitHub Issues has since gained native dependencies and
sub-issues, and this repo already uses them.** `issue_dependencies_summary.blocked_by
== 0` is the entire ready-check, server-computed, and it rides along on the **list**
endpoint — so the whole DAG gate costs one paginated call per tick, strictly less work
than symphony's Linear adapter does (§5.4–5.6).

Ticket: #573 (pull-loop scheduler on Claude Code, GitHub Issues as tracker DB).
Brief: survey `zaalipro/cymphony` (new), go deeper on two `Sugar-Coffee/stokowski`
mechanisms, and enumerate recent active forks of `openai/symphony`.

Prior art in this repo (read first, not redone):
`docs/research/kb/reports/agents/wf-dag-symphony-gaps.md` §I,
`docs/research/kb/reports/agents/symphony-and-ports.md`.

Offline corpora (preferred over re-fetch):
- `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/symphony` — openai/symphony itself (SPEC.md 91 KB, elixir reference impl).
- `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/OpenSymphony` — a separate Rust/TS project (NOT openai/symphony).

---

## 0. Orientation notes (probe hygiene)

- **graphify was not usable for the cymphony read.** The project graph
  (`knowledge-base/graphify-out/graph.json`, 498 MB, built 2026-08-05) indexes the
  knowledge-base corpus, not a repo freshly cloned into the scratchpad. cymphony was
  read directly from its git tree; that is the "modify/debug specific lines" branch of
  the rule, not a skipped step.
- **Offline corpora identified:**
  - `knowledge-base/sources/symphony` — **the real `openai/symphony`**: `SPEC.md`
    (91 KB, 2,311 lines, 18 sections + Appendix A), the `elixir/` reference impl,
    `.codex/`. This is the spec the ports implement.
  - `knowledge-base/sources/OpenSymphony` — **NOT openai/symphony.** A separate
    Rust+TypeScript monorepo (`Cargo.toml`, `crates/`, `apps/`, `packages/`,
    `.opensymphony/`, `WORKFLOW.md` 36 KB, `PRODUCT.md` 20 KB). Name collision only;
    it is not a port and was not surveyed further under this brief.

---

## 1. zaalipro/cymphony — Elixir rewrite of symphony with a pluggable agent adapter

**Measured 2026-08-05** via `gh api repos/zaalipro/cymphony`, then a `--depth 50` clone
at `fb1660d282b26182eb45784f455416cefb048826` (2026-07-17 14:00:01 +0400,
"v2.2.0: live model/effort catalog from codex debug models"), 155 tracked files.

| Field | Value |
|---|---|
| Description | "OpenAI Symphony converted to use Claude Code CLI instead of Codex CLI" |
| `fork` | **false** — a re-implementation, not a GitHub fork |
| Stars / forks / open issues | **1 / 0 / 0** |
| Language | **Elixir** |
| License | Apache-2.0 |
| Created / last push | 2026-04-19 / **2026-07-17T10:00:07Z** |

Self-description (`README.md:3`): *"A modern rewrite of openai/symphony, using
**Claude Code** instead of Codex."* Module namespace is `CymphonyElixir.*`, mirroring
symphony's `SymphonyElixir.*` — it is symphony's Elixir tree renamed and extended,
with the Codex app-server client replaced by a CLI-adapter behaviour.

### 1.1 Tracker / database — **Linear only. Not GitHub Issues.**

This is the headline answer to the brief's first question, and it is a negative:
**cymphony does not use GitHub Issues as its tracker.** It narrows symphony's five
adapters to one.

- `lib/cymphony_elixir/tracker.ex` (80 lines) is the behaviour; the only real
  implementation is `lib/cymphony_elixir/linear/adapter.ex`. The sole sibling is
  `lib/cymphony_elixir/tracker/memory.ex` (97 lines) — an in-memory test double.
- `WORKFLOW.md` front matter pins `tracker.kind: linear` with a `project_slug`.
- The setup wizard asks for a **GitHub repo URL** (step 2) *and* a **Linear project
  slug** (step 3) — GitHub is the code host, Linear is the tracker. The two roles are
  distinct throughout.
- `GH_TOKEN` / `GITHUB_TOKEN` are inherited into the agent's env
  (`agent/runner.ex:304`) purely so the agent can drive `gh` for PR work — not for
  tracker reads.

So for our GH-Issues-as-database design, **cymphony contributes dispatch and env
mechanics, not tracker mechanics.** Its state model is symphony's: tracker states
(`Todo`, `In Progress`, `Merging`, `Rework` active; `Closed`/`Cancelled`/`Canceled`/
`Duplicate`/`Done` terminal) plus an in-memory orchestrator, with durable per-issue
state living in the workspace and a persistent tracker comment ("workpad").

### 1.2 Dispatch shape — headless `claude -p`, one process per turn, resumed by session id

`lib/cymphony_elixir/agent.ex` defines a five-callback behaviour
(`default_command/0`, `build_command/1`, `parse_output/3`, `auth_env_prefixes/0`,
`auth_env_fallback/0`) with two implementations, `Agent.Claude` and `Agent.Codex`
(`agent.ex:37,43-44`). `Agent.Runner` owns everything CLI-agnostic — workspace
validation, port spawn, env injection, output collection, turn timeout.

`agent/claude.ex:21-46` `build_command/1` composes, in order:

```
claude [--bare] -p <escaped prompt>
       [--output-format stream-json] [--verbose]        # --verbose iff stream-json
       [--permission-mode <mode>] [--allowedTools <csv>]
       [--model <m>] [--effort <e>] [--fallback-model <m>]
       [--max-turns <n>] [--max-budget-usd <d>]
       [--mcp-config <path>]                            # 0600 file in the workspace
       [--resume <session_id>]                          # turn 2+
```

**Every one of those flags is real** — control-armed against the offline vendor docs
(`$CC` = `knowledge-base/sources/agent-harness-docs/docs/claude-code`), which is worth
stating because two of them look invented:

- `--max-budget-usd` → `$CC/cli-reference.md:98` ("Maximum dollar amount to spend on
  API calls before stopping (print mode only)"; subagent spend counts; cap enforcement
  needs v2.1.217+).
- `--effort` → `$CC/workflows.md:152`, `$CC/settings.md:271` (`low|medium|high|xhigh`,
  plus `ultracode`; v2.1.203+).
- `--bare` → `$CC/authentication.md:197` — **and the doc carries a trap cymphony
  respects by accident:** *"Bare mode does not read `CLAUDE_CODE_OAUTH_TOKEN`. If your
  script passes `--bare`, authenticate with `ANTHROPIC_API_KEY` or an `apiKeyHelper`."*
  cymphony's `auth_env_fallback` is exactly `["ANTHROPIC_API_KEY"]` (`claude.ex:18`).

Control arm: `--output-format` returned 39 hits over the same tree with the same
command shape, so the flags-present results discriminate.

**Turn model:** one OS process per turn. `run_turn` spawns a port, collects output to
process exit, parses, and returns; it reports `turn_id: 1` unconditionally
(`runner.ex:117`). Continuity is carried **only** by `--resume <session_id>`, where the
id is scraped from the terminal `type == "result"` event of the stream
(`claude.ex:107-133`) or the last JSON line in `json` mode (`claude.ex:85-105`). This
is the correct mapping of symphony's `thread_id` reuse (`SPEC.md:1011`) — and it is
the thing `manav03panchal/phonyhuman` got wrong (no `--resume` at all; see
`symphony-and-ports.md` §2.3).

**No native Claude Code multi-agent primitives.** cymphony drives the CLI as a
subprocess exactly as the other three ports do. Its `.claude/skills/{commit,debug,land,
linear,pull,push}/SKILL.md` are symphony's Codex skills translated to Claude format —
capabilities the single agent loads, not a team.

### 1.3 The Claude-Code-specific hazards it works around — the most transferable part

These are the findings worth carrying into #573 regardless of tracker choice.

**(a) rc-file sourcing is CONDITIONAL, because unconditional sourcing clobbers the
injected env.** `runner.ex:215-227`:

```elixir
if ! command -v <cmd> >/dev/null 2>&1; then
  for __cymphony_rc in "$HOME/.cld" "$HOME/.zshrc" "$HOME/.bashrc"; do
    [ -f "$__cymphony_rc" ] && . "$__cymphony_rc" 2>/dev/null || true
  done
  unset __cymphony_rc
fi
exec <command>
```

The comment states the reason verbatim: sourcing happens *only* when the first word of
the command isn't already on `$PATH`, so plain binaries (`claude`, `codex`) "don't
trigger rc-file sourcing — that would otherwise override env vars we explicitly pass
via `Port.open`'s `:env` option." The motivating case is a shell *function* as the
agent command (`cz`, `cm`, `cv1` in `~/.cld`), which only resolves after sourcing.

This is our `__MISE_DIFF` problem from the other side: we worry about the parent's env
leaking into the child; cymphony worries about the child's **rc file overwriting what
the parent deliberately injected**. Both are the same class — *the shell between you
and the agent is not neutral*.

**(b) The child env is an ALLOWLIST, not `inherit=all`.** `runner.ex:259-317` builds
the child env from scratch:

- base: `PATH` + `HOME` only (local spawn; empty for SSH, which uses `export` lines);
- agent auth: either a named provider's env via
  `ShellProvider.load_env(provider, agent_module.auth_env_prefixes())` — filtered to
  `ANTHROPIC_`, `API_TIMEOUT`, `CLAUDE_CODE_` (`claude.ex:15`) — or, failing that, the
  inherited `ANTHROPIC_API_KEY` alone;
- integrations: `LINEAR_API_KEY` (from config, not the environment) plus inherited
  `GH_TOKEN` / `GITHUB_TOKEN`;
- then `valid_env_map/1` drops any name failing `^[A-Za-z_][A-Za-z0-9_]*$`
  (`runner.ex:20,332-340`).

Contrast symphony's reference workflow, which runs Codex with
`shell_environment_policy.inherit=all` (`elixir/WORKFLOW.md:33`). cymphony **inverted
that default**. Given this repo's `env = true` / 50-credentials-everywhere posture
(`secrets-out-of-the-shell-env.md`), the allowlist shape is the one to copy.

**(c) Secrets never reach argv.** MCP servers are handed over as a JSON descriptor
file written **0600 inside the workspace**, referenced by `--mcp-config <path>`
(`claude.ex:73-81`, `Mcp.ConfigWriter`). The inline comment says why: "so the API key
never appears in argv". Symphony's equivalent guarantee is host-side tool execution
(`SPEC.md:1107-1111`); cymphony achieves it with file-mode instead.

**(d) MCP injection is local-only by construction.** `runner.ex:176-177` returns a
`nil` descriptor whenever `worker_host` is set — "a remote workspace cannot read a
local descriptor file, and remote argv rendering is untested". An explicit capability
downgrade rather than a silent breakage.

**(e) Turn timeout is a receive-deadline, and it kills the port.**
`runner.ex:365-392`: the output collector is a tail-recursive `receive` with
`after config.agent.turn_timeout_ms -> stop_port(port); {:error, :turn_timeout}`. Note
this bounds *total silence on the port*, and a non-zero exit is a distinct
`{:error, {:agent_exit, status, remaining}}` — the two failure shapes are not
conflated.

**(f) Stall detection is separate from turn timeout, and is pure.**
`orchestrator/stall.ex` (55 lines) is deliberately side-effect-free: `stalled?/3`
compares `now` against `:last_agent_timestamp` falling back to `:started_at`, with
`timeout_ms <= 0` disabling detection and a missing timestamp never counting as
stalled (`stall.ex:47-53`). The orchestrator owns the impure reaction — "terminating
the session and rescheduling it with backoff" (`stall.ex:6-8`). Two independent
watchdogs: the port-level deadline (e) and the orchestrator-level silence check (f).

**(g) Workspace containment is canonicalized, and symlink escape is its own error.**
`runner.ex:394-420` canonicalizes both workspace and root, rejects
`workspace == root`, and distinguishes `:symlink_escape` (passes the textual prefix
check but fails the canonical one) from `:outside_workspace_root`. This implements
`SPEC.md:928-948`, which calls containment "the most important portability
constraint".

### 1.4 What cymphony added over symphony (per `README.md:19-42`)

Multi-project orchestration in one daemon with a per-project concurrency cap (default
10, changeable live); **per-project custom Claude command** (point one project at
`claude`, another at a wrapper injecting z.ai / Kimi / OpenRouter credentials);
**provider rotation** — list two or more Claude-compatible backends and new sessions
are spread across them randomly "to avoid hitting any single backend's rate limit";
a Phoenix LiveView dashboard with per-session kill / retry / pause / set-provider;
`/api/v1/*` HTTP API with optional `CYMPHONY_API_TOKEN` bearer auth; a `cymphony
setup` wizard writing `~/.cymphony/config.json` (from which a per-project
`WORKFLOW.md` is **generated** at runtime — the committed one is then not consulted);
`cymphony start` as a background daemon; Homebrew / `.deb` distribution with Erlang
bundled.

### 1.5 Claim, tick, reconcile, retry — mechanics

**Claim** is an in-memory `MapSet` in the orchestrator GenServer's `%State{}`
(`orchestrator.ex:56`), tested at `:577` (`!MapSet.member?(claimed, issue.id)`) and
released at `:1124-1125`. There is **no distributed claim and no lease** — mutual
exclusion comes entirely from the single GenServer serializing all state mutations,
exactly as `SPEC.md:727` prescribes. Nothing survives a restart; recovery is by
re-reading the tracker (symphony's "no persistent database" goal, `SPEC.md:57-58`).

**Tick**: `schedule_tick(state, state.poll_interval_ms)` via `Process.send_after`
with a `tick_token` (`orchestrator.ex:139,1769`) — a token-guarded timer, so a stale
timer firing after a reschedule is ignored. `WORKFLOW.md` sets `polling.interval_ms:
5000`. Per-tick order matches the spec: reconcile running (stalled first, then
tracker states, then missing ids) → dispatch (`:265-269`, `:319-334`).

**Backoff** (`:1225-1236`):

```elixir
@continuation_retry_delay_ms 1_000        # clean exit, still active → immediate re-dispatch
@failure_retry_base_ms       10_000
failure_retry_delay(attempt, cap) = min(10_000 * (1 <<< min(attempt - 1, 10)), cap)
```

Same curve as `SPEC.md:799-801`, with the shift **clamped at 2^10** so a long-lived
retry chain cannot overflow into a nonsense delay before the cap applies.

**A retry cap and an abandon path — cymphony's own addition** (`:1160-1212`).
Symphony retries forever under a capped backoff; cymphony adds
`agent.max_retry_attempts`, and on exceeding it: posts a tracker comment ("🛑 Cymphony
abandoned this issue after N consecutive failed agent attempts… Move it back to an
active state to retry"), moves the issue to a configurable `agent.failure_state`,
cleans the workspace, and drops the claim.

The load-bearing detail is **which failures count** (`:1163-1166`, verbatim):

> "Only genuine agent failures (crash, spawn failure, stall) increment `failures`;
> backpressure ("no slots") and transient poll failures preserve it, so a
> healthy-but-slot-starved issue is never abandoned."

That distinction — *failure* vs *backpressure* — is the one I would carry into #573
verbatim. A naive attempt counter that increments on "no slots" will abandon exactly
the tickets that were healthiest and busiest.

Abandonment's tracker side effects go through `safe_tracker_call/3` (`:1214-1223`),
which catches both `{:error, _}` and raises, **logs** them, and continues — "never let
a tracker error crash the orchestrator, but log it rather than swallow it."

**Terminal / failure reasons** are distinguished, not collapsed: `:turn_timeout`
(port silence deadline, `runner.ex:388-390`), `{:agent_exit, status, remaining}`
(non-zero exit, `runner.ex:383-386`), stall (`stall.ex` + `restart_stalled_issue`,
recorded as `error: "stalled for Nms without agent activity"`, `:532`), startup
failure, and abandonment. `SPEC.md:692` gives the reason: "Distinct terminal reasons
are important because retry logic and logs differ."

Other lifecycle: a **workspace sweep every 6 hours** (`@workspace_sweep_interval_ms 6
* 60 * 60 * 1_000`, `:1040-1044`); terminal-workspace cleanup at startup (`:93`).

### 1.6 ⚠️ Cross-check: cymphony's blocker rule cites a SPEC section that does not contain it

`orchestrator.ex:631-656` implements DAG gating and attributes it:

```elixir
# Implements the dispatch rule from openai/symphony SPEC §8.2:
# > "If state is `Todo`, do not dispatch when any blocker is non-terminal."
```

**SPEC §8.2 does not say that.** Read directly (`SPEC.md:754-776`, "Candidate
Selection Rules"), §8.2's eligibility list is: required fields present; state active
and not terminal; **adapter-provided `dispatchable` is true**; required labels;
not already running; not already claimed; global and per-state slots available. No
blocker clause.

Control-armed (offline `sources/symphony`, same command shape each arm):

| Arm | Result |
|---|---|
| `"do not dispatch when any blocker"` in `SPEC.md` + `elixir/` | **0** |
| `blocker.*non-terminal` in `SPEC.md` + `elixir/` | **1** — and it is `elixir/README.md:221`, not `SPEC.md` |
| CONTROL `dispatch-eligible` in `SPEC.md` | 1 (present, as expected) |
| CONTROL `blocked_by` in `elixir/` | 23 (the sweep reaches the impl) |

The one real hit resolves the discrepancy — the rule exists in symphony, but **in the
Linear adapter, not the scheduler** (`elixir/README.md:220-222`, verbatim):

> "Dispatchability: the adapter marks an issue dispatchable only when optional
> assignee routing matches and a `Todo` issue has no non-terminal blocker. The generic
> scheduler then applies active/terminal states, required labels, claims, retries, and
> concurrency."

And the SPEC forbids the *scheduler* from doing this: the orchestrator "MUST NOT …
branch on provider-specific blocker, board, transition, or comment semantics"
(`SPEC.md:1243`); `blocked_by` is "best-effort provider metadata" (`:187-193`) and
"adapters MUST NOT invent blocker semantics they cannot [infer safely]" (`:1277`).
`SPEC.md:2115` states the intended shape outright: "Provider-specific
routing/blocker/assignment rules become explicit `dispatchable`."

**So this is a real architectural divergence, mislabelled as conformance.** cymphony
hoisted blocker evaluation *out of* the adapter and *into* the core scheduler. It kept
a vestigial `issue_routable_to_worker?/1` reading an `assigned_to_worker` boolean
(`:625-629`) — the remains of `dispatchable`, now carrying only the assignee half of
the rule.

**Why this matters for #573:** it is the cleanest statement of the design choice we
face. DAG gating can live in (a) the tracker adapter, as one precomputed boolean the
scheduler never interprets — symphony's answer, and the one that keeps the scheduler
provider-agnostic; or (b) the scheduler, which must then understand issue-state
vocabulary of *other* issues — cymphony's answer, simpler to write and harder to port.
Note also cymphony's semantics, which are worth keeping either way: **the block is
checked only in `Todo`** ("issues already in progress are allowed to run even when
blockers remain open, so an in-flight worker can finish what it started",
`:636-638`) — a ready-check at admission, not a running invariant.

---

## 2. Sugar-Coffee/stokowski — the two mechanisms asked for

Clone at `6e51bdf26c8cf6206893beb7c01b71297539469d` (2026-06-23, "Release v0.5.0 (#39)").
General survey already in `symphony-and-ports.md` §2.1 and `wf-dag-symphony-gaps.md` §I —
not repeated. This section covers only (a) the tracker-comment state format and (b) the
rework cycle.

### 2.1 The machine-readable tracker-comment state pattern

Whole mechanism is `stokowski/tracking.py` — **165 lines, no dependencies beyond
`json`/`re`/`datetime`.** That is the entire "tracker is the database" layer.

**Two markers** (`tracking.py:13-14`):

```python
STATE_PATTERN = re.compile(r"<!-- stokowski:state ({.*?}) -->")
GATE_PATTERN  = re.compile(r"<!-- stokowski:gate ({.*?}) -->")
```

**Payload fields** — small and closed, no nesting:

| Marker | Fields | Where |
|---|---|---|
| `state` | `state` (pipeline state name), `run` (int, default 1), `timestamp` (ISO-8601 UTC) | `tracking.py:19-23` |
| `gate` | `state`, `status`, `run`, `timestamp`, **`rework_to` only when set** | `tracking.py:37-44` |

`status` takes `waiting` / `approved` / `rework` / `escalated` (`tracking.py:48-67`).

**Every comment is dual-audience — one machine line, one human line, separated by a
blank line** (`tracking.py:24-26`):

```
<!-- stokowski:state {"state": "implement", "run": 2, "timestamp": "..."} -->

**[Stokowski]** Entering state: **implement** (run 2)
```

The human half is rendered per status, so a rework comment reads *"Rework requested at
**code_review**. Returning to: **implement** (run 2)"* (`tracking.py:54-60`). This is
the detail I'd copy first: the same comment is both the state record and the changelog
a human reads, so there is no separate audit trail to keep in sync.

**Append-only, not edit-in-place.** Symphony keeps exactly ONE persistent workpad
comment and rewrites it (`elixir/WORKFLOW.md:86,281`); stokowski **posts a new comment
per transition** and derives current state by scanning. Trade: full history and no
lost-update race, at the cost of comment clutter on a long-running ticket.

**Parsing back / crash recovery** (`tracking.py:72-104`): `parse_latest_tracking`
walks the comment list, and for every body matching either pattern, `json.loads` the
capture and **overwrites** `latest`, tagging it `type: "state"` or `"gate"`. The last
match in list order wins. A `JSONDecodeError` is swallowed (`pass`) so one corrupt
comment degrades to the previous good one rather than crashing recovery.

Recovery consumes it in `orchestrator.py:300-354` — the resume ladder:

| Tracking found | Resumes as |
|---|---|
| none | entry state, run 1 |
| `state`, name known | that state, that run |
| `state`, name **unknown** | entry state, run 1 (config changed under a live ticket) |
| `gate` + `waiting` | that gate, run preserved, **re-registered in `_pending_gates`** |
| `gate` + `approved` | the gate's `transitions["approve"]` target |
| `gate` + `rework` | `rework_to` from the comment, falling back to the gate's config |
| anything else | entry state, run 1 |

So the durable state is *entirely* in tracker comments; the orchestrator's dicts
(`_issue_current_state`, `_issue_state_runs`, `_pending_gates`) are pure cache. That is
the property we want for #573.

**Two fragilities worth designing around** (both are ours to avoid, not defects I can
call proven):

1. **Ordering is delegated to the provider.** `parse_latest_tracking`'s docstring says
   "comments (oldest-first)" but nothing enforces it — `fetch_comments`
   (`linear.py:319-327`) returns `nodes` verbatim from `comments(orderBy: createdAt)`
   (`linear.py:103`) with no client-side sort (target grep for `sort|orderBy|reverse`
   in `tracking.py` + `linear.py` → 2 hits, both the query strings; control `createdAt`
   → 6 and 1 in the same files, so the sweep reaches them). **⚠️ UNVERIFIED: I could
   not confirm Linear's default sort DIRECTION for `orderBy: createdAt`** — no Linear
   API docs in the offline corpus (control: 104 source trees present, so the corpus is
   reachable). If Linear returns newest-first, "last match wins" silently resolves to
   the *oldest* tracking entry. The payload carries a `timestamp` that would settle it,
   and **nothing ever reads it for ordering.** For us: sort by our own embedded
   timestamp; never inherit the provider's order.
2. **No pagination.** The comments connection is requested with no page size or cursor,
   so recovery sees only the provider's default first page. A ticket with a long
   comment history can push its own tracking comments out of view.

**Refuted en route, recorded so it isn't re-derived:** I expected `({.*?})` to truncate
at the first `}` and break on any nested JSON. **Wrong** — armed both ways in Python:
flat payload (control) parsed, and `{"state":"implement","meta":{"a":1},"run":2}` also
parsed, because the non-greedy quantifier still backtracks until the trailing ` -->`
matches. The regex is safe for nested objects.

### 2.2 `rework_to` / `max_rework` cycle mechanics

**Declaration** (`config.py:115-116`) — both are gate-only fields:

```python
rework_to:  str | None = None     # gate only
max_rework: int | None = None     # gate only
```

Validation is a hard gate at load (`config.py:643-647`): a `gate` state with no
`rework_to`, or one naming a state not in `all_state_names`, is a config **error**.
`config.py:682-683` folds `rework_to` into the reachability set, so a rework-only
target isn't flagged as orphaned. Rework targets may be **any** earlier state, which is
what makes the graph a cycle rather than a DAG (`README.md:180`).

**How a rework is represented on the tracker** — the answer is a *split*, and it is
the design insight of the whole port:

- The **Linear state** goes back to the generic `linear_states.active`
  (`orchestrator.py:630-631`).
- The **pipeline stage** is carried in the comment's `rework_to` field
  (`orchestrator.py:622-626`).

Linear's own workflow states are only a **coarse six-value vocabulary** —
`active`, `awaiting_ci`, `review`, `gate_approved`, `rework`, `terminal`
(`config.py:627`) — while the fine-grained pipeline state (`investigate`, `implement`,
`code_review`, `merge`, …) lives *only* in the structured comments. The tracker's
native state field is a bucket; the comment is the state machine.

**The cycle, end to end** (`orchestrator.py:575-641`):

1. A human moves the ticket to the `Rework` Linear state. The orchestrator polls that
   state each tick (`fetch_issues_by_states([linear_states.rework])`, `:577-579`).
2. Skip if already `running` or `claimed` (`:586-587`).
3. Recover which gate it came from: `_pending_gates.pop(issue.id)`; **on a cache miss
   (i.e. after a crash) re-read the comments** and accept a `gate`+`waiting` entry
   (`:589-594`). This is the crash-recovery path in §2.1 doing real work.
4. Resolve `rework_to` from that gate's config; **no target ⇒ log a warning and skip**
   — the ticket is left in `Rework` rather than guessed at (`:598-601`).
5. **`max_rework` check, BEFORE incrementing**: `if max_rework is not None and run >=
   max_rework` → post a `status="escalated"` gate comment, log, and `continue`
   (`:603-617`). Note what escalation *is*: **no transition at all.** There is no
   escalation state and no reassignment — the ticket simply stays in `Rework` with a
   comment saying a human must step in. Cheap, and it cannot loop.
6. Otherwise `new_run = run + 1` (`:619-620`), post the `status="rework"` gate comment
   carrying `rework_to` + `new_run` (`:622-626`), set the cached pipeline state to
   `rework_to` (`:628`), and move the Linear state back to `active` (`:630-635`) —
   a failed move is logged, not fatal.

**`run` vs `attempt`.** `run` is the rework generation and is the field that
`max_rework` bounds; retry-within-a-run is separate. Both are exposed to prompts as
`{{ run }}` and `{{ last_run_at }}` (`symphony-and-ports.md` §2.1), which is how a
re-entered stage prompt knows it is a redo. Symphony has only a single `attempt` and
explicitly puts this distinction out of scope (`SPEC.md:1347-1349`).

**Gate context survives the Rework state**: `orchestrator.py:702-706` appends the
rework state to the gate-polling set with the comment "Also include Rework — reworked
tickets still hold pending gate context."

---

## 3. Recent active forks of `openai/symphony`

**2,680 forks total** (`gh api repos/openai/symphony --jq .forks_count`, 2026-08-05).
I enumerated all forks pushed since 2026-06-01, then measured real divergence with
`gh api repos/openai/symphony/compare/main...<owner>:<default_branch>` — because
**recency and repo size are both bad proxies**: eight of the ten most recently pushed
forks are `ahead=0` (they are sync-only mirrors), and `ProlokGmbH/Symphony` sits at
baseline size while being 336 commits ahead.

| Fork | ahead / behind | Stars | Last push | Note |
|---|---|---|---|---|
| **Pimpmuckl/symphony-plus-plus** | **596** / 31 | 4 | 2026-08-04 | Only fork with its own description: *"Symphony++ builds onto the foundation of OpenAI's symphony playbook to build a fully functional pipeline and work-package control plane."* **The one to watch** — "pipeline" + "work-package control plane" is exactly #573's problem statement. |
| **ProlokGmbH/Symphony** | **336** / 34 | 2 | 2026-08-04 | Heavily divergent, upstream description retained. Size gives no hint — found only by the compare probe. |
| **EmberAGI/symphony** | **120** / 31 | 0 | 2026-08-04 | Substantive divergence, org-owned (EmberAGI). |
| **acancelas/symphony** | 51 / 12 | 0 | 2026-08-02 | Moderate; +5.8 MB over baseline suggests vendored assets. |
| **kingzeus/symphony** | 9 / 0 | 1 | 2026-08-04 | Small, fully up to date with upstream. |
| `371-Minds`, `Pauca-Technologies`, `Max-Levitskiy`, `Girolino`, `zeguo1`, `Care-Core`, `stslgn`, `aroakpm-svg`, `Orchestra-Bio`, `Quest1Codes`, `manafuel`, `laiye-ai`, … | **0** ahead | 0 | Aug 2026 | Sync-only mirrors. No divergent work. |

**Judgment:** only `Pimpmuckl/symphony-plus-plus` clears the bar the brief set ("real
divergent commits relevant to Claude Code or GitHub-Issues-as-tracker") on its stated
purpose; `ProlokGmbH/Symphony` and `EmberAGI/symphony` clear it on volume alone and
their relevance is unassessed. Per the brief's "one line each, deep-dive only if
clearly relevant", I did not clone them — **all three are unread, and their relevance
to Claude Code / GitHub Issues is UNVERIFIED**, resting on description and commit
count only.

---

## 4. Adopt / reject for a GitHub-Issues-backed pull loop (#573)

### Adopt

1. **Structured HTML-comment state, dual-audience** (stokowski §2.1). Renders as an
   invisible marker plus a human line in one comment; GitHub Issues renders HTML
   comments the same way Linear does. This is the mechanism that makes a tracker a
   database.
2. **Coarse tracker vocabulary + fine state in the comment** (stokowski §2.2). GitHub
   Issues offers only `open`/`closed` plus labels for *state*, so this split is not
   merely convenient for us, it is *forced*. Labels take the role of `linear_states`'
   six buckets; the comment carries the real stage. (Scope note added with §5: this
   applies to **state** only. GitHub's *dependency* surface is not impoverished — it is
   richer and cheaper to query than Linear's, see §5.4–5.6.)
3. **Sort by your OWN embedded timestamp, and paginate explicitly** — the two things
   stokowski leaves to the provider (§2.1). It already writes the timestamp; read it.
4. **Failure vs backpressure in the retry counter** (cymphony §1.5). Only genuine
   agent failures increment; "no slots" and transient poll errors must not. Then a
   bounded `max_retry_attempts` with an abandon path — comment, move to a failure
   label, clean the workspace, drop the claim.
5. **Two independent watchdogs** (cymphony §1.3 e/f): a per-turn output deadline that
   kills the process, and an orchestrator-side silence check on last-activity. Keep
   the stall predicate **pure** and the reaction in the loop — `stall.ex` is 55 lines
   and trivially testable.
6. **Distinct terminal reasons, never collapsed** — timeout / non-zero exit / stall /
   startup failure / abandoned. `SPEC.md:692`: retry logic and logs differ per reason.
7. **Child env as an allowlist, built from empty** (cymphony §1.3 b). Given this repo's
   `env = true` posture — all 50 credentials in every shell and inherited by every
   child ([[secrets-out-of-the-shell-env]]) — inheriting the ambient environment into a
   spawned agent is the *worst* available default here. cymphony starts from
   `PATH`+`HOME` and adds only prefix-matched auth.
8. **Never put a secret in argv** (cymphony §1.3 c): MCP config as a 0600 file in the
   workspace referenced by `--mcp-config`. argv is world-readable via `ps`.
9. **Beware the shell between you and the agent** (cymphony §1.3 a). rc-file sourcing
   overrides deliberately injected env; cymphony sources only when the command isn't
   already on `PATH`. Our mirror-image hazard is documented — `CLAUDE_*` pins must live
   in settings `env`, never a shell export, because background launch strips them
   (`.claude/CLAUDE.md` §"DAG topology pins", #567).
10. **Gate the DAG at admission only, not while running** (cymphony §1.6): check
    blockers when the ticket is in the queued state; let an in-flight worker finish
    even if a blocker reopens.
11. **Token-guarded timers** (cymphony §1.5) so a stale timer firing after a reschedule
    is ignored rather than double-dispatching.
12. **Escalation = stop and comment, not a new state** (stokowski §2.2 step 5). Cheapest
    correct answer, and it cannot loop.

### Reject / don't copy

1. **cymphony's tracker choice.** Linear-only; it contributes nothing to
   GitHub-Issues-as-database. Its value here is dispatch and env mechanics.
2. **cymphony's placement of blocker logic in the scheduler** (§1.6). Symphony's shape
   — the tracker adapter precomputes one `dispatchable` boolean the scheduler never
   interprets — is the better seam, and cymphony's own code comment misattributes its
   divergence to a SPEC section that says the opposite. Independently confirmed in §5.3:
   symphony's orchestrator references `blocked_by` in exactly one place, a log line. If
   we ever want a second tracker, the adapter seam is what makes it cheap — and on
   GitHub that adapter is nearly free, since `issue_dependencies_summary.blocked_by == 0`
   is the whole predicate (§5.4).
3. **In-memory-only claims as the whole story.** Both cymphony and stokowski rely on a
   single process serializing claims, with nothing durable. Acceptable for them; for us
   the harness already ships a persistent, cross-session task list with native
   `blocks`/`blockedBy` edges (`CLAUDE_CODE_TASK_LIST_ID`, task-list id `dotfiles-dag`,
   #567) — reimplementing a weaker claim table would violate [[use-tool-builtins]].
4. **Append-a-comment-per-transition, unqualified.** Fine on a Linear ticket; on a
   GitHub issue that is also the human discussion thread it is noisier. Prefer one
   edited state comment (symphony's workpad) **plus** an append only at genuine
   phase boundaries — and note that editing needs the anchor-assert discipline from
   [[feedback_issue_body_edit_needs_anchor_assert]].
5. **Provider-default ordering and unpaginated reads** (stokowski §2.1) — the two
   things to fix rather than inherit.
6. **`--dangerously-skip-permissions` as the default posture** (stokowski's
   `permission_mode: auto`; hatice's `bypassPermissions` default). Our guard layer —
   PreToolUse `hook_guard`, `branch_guard`, settings deny rules — is the thing keeping
   an autonomous loop from committing to `main` or running `chezmoi apply` on the host.
   Use `--permission-mode` with an explicit `--allowedTools` set instead.
7. **Any port's coordination layer wholesale.** All four ports (and cymphony makes
   five) drive Claude Code as a **headless single-agent subprocess** and reimplement
   dispatch/concurrency/retry in a host language. None uses the harness's native
   multi-agent primitives. Our advantage over every one of them is that we have those
   primitives; the ports are worth mining for *policy* (backoff curves, failure
   taxonomy, env hygiene), not for *architecture*.

### Two facts to carry into the design regardless

- **`--resume <session_id>` is the whole of session continuity** in the headless CLI
  shape, and it is the thing a port most easily drops: cymphony and stokowski map it
  correctly, phonyhuman omits it entirely and silently degrades to workspace + tracker
  comment as the only memory.
- **`--max-budget-usd` exists and counts subagent spend** (`$CC/cli-reference.md:98`,
  needs v2.1.217+ for cap enforcement) — a per-run cost ceiling we get for free, which
  matters for an unattended loop given the shared weekly window
  ([[project_session_2026-08-04c]]).

---

## 5. Tracker providers across all five codebases — Linear vs GitHub Issues

Added 2026-08-05 at team-lead's request, for Ray's Linear-vs-GitHub-Issues decision.

### 5.1 Who ships what

| Codebase | Tracker adapters shipped | Generic contract? |
|---|---|---|
| **openai/symphony** (elixir ref impl) | **five** — `linear`, `github`, `gitlab`, `jira`, `asana` | **Yes** — `SPEC.md` §11, RFC-2119 normative |
| **zaalipro/cymphony** | **Linear only** (+ `tracker/memory.ex` test double) | behaviour exists, one real impl |
| **Sugar-Coffee/stokowski** | **Linear only** (`tracker.kind` accepts `"linear"`, `README.md:553`) | no |
| **mksglu/hatice** | `linear`, `github`, `gitlab` | mirrors symphony's |
| **manav03panchal/phonyhuman** | **Linear only** (deleted symphony's other four) | inherited, unused |

Symphony's file layout is a consistent three-file shape per provider —
`adapter.ex` + `client.ex` + `agent_tool.ex` — under
`elixir/lib/symphony_elixir/<provider>/`.

**The `adapter.ex` files are thin shims; the real normalization is in `client.ex`.**
Each `adapter.ex` is 50–63 lines and contains **zero** occurrences of
`dispatchable`/`blocked_by`. Control-armed, because a 0 across all five is exactly the
shape of a broken probe: `grep -c 'def '` on the same five files returns **6 each**, so
the sweep reaches them; and `grep -rln dispatchable` over the impl returns all five
`client.ex` files plus `tracker/issue.ex`. The zero was real.

### 5.2 The generic adapter contract (`SPEC.md` §11)

Two REQUIRED operations only (`SPEC.md:1187-1205`): `fetch_issues_by_states(state_names)`
and `fetch_issues_by_ids(issue_ids)`. Both return `ok(list<Issue>)` or an adapter error;
an empty input list MUST return empty **without a provider request**.

The division of labour is stated explicitly and is the thing worth copying
(`SPEC.md:1193-1196`):

> "When used for candidate polling, include active scoped issues even when
> `dispatchable=false`; the scheduler owns that final filter. The orchestrator applies
> `required_labels`, `dispatchable`, claims, retries, and concurrency after
> normalization."

Required normalized fields are `id`, `identifier`, `title`, `state`, and **explicit
`dispatchable`** (`SPEC.md:1214-1216`) — everything else may normalize to null/empty
without making the record malformed. Two asymmetries worth keeping: a state-list call
MAY drop a malformed record (it was never safe to dispatch) but an ID-refresh MUST fail
rather than omit, "because omission is meaningful" (`:1220-1222`); and refresh returns
**full snapshots, not just state strings**, because "label, assignment, routing, and
provider-specific dispatchability can change while a run is active" (`:1227-1228`).

**Claim state is NOT part of the tracker contract.** `claimed`/`running` live only in
orchestrator memory (§1.5). Nothing is written to the tracker to claim an issue — the
tracker is read-mostly, and the only durable per-issue writes are the workpad comment
and state transitions, both performed by the *agent*, not the orchestrator
(`SPEC.md:1309-1319`).

### 5.3 ⚠️ The finding that matters: symphony's GitHub adapter has NO blocker support

Verbatim, all five clients, same two normalized fields:

| Provider | `blocked_by` | `dispatchable` | file:line |
|---|---|---|---|
| **linear** | `blockers` (real, from inverse `blocks` relations) | `dispatchable?(state_name, blockers, assignee, assignee_filter)` | `linear/client.ex:482,484` |
| **jira** | `blockers` (real, inward `Blocks` links) | `dispatchable?(state, status_category, blockers, terminal_states)` | `jira/client.ex:253,254` |
| **github** | **`[]` — hardcoded empty** | `not Map.has_key?(issue, "pull_request")` | `github/client.ex:193,194` |
| **gitlab** | **`[]` — hardcoded empty** | **`true` — constant** | `gitlab/client.ex:192,193` |
| **asana** | **`[]` — hardcoded empty** | `task["completed"] == false and task["resource_subtype"] != "section"` | `asana/client.ex:222,223` |

Only **Linear and Jira** have a worked-out DAG story. Symphony's **GitHub Issues
adapter's entire `dispatchable` logic is "this row is not a pull request"** — because
GitHub's Issues API returns PRs in the issues list (`elixir/README.md:253`: "pull
requests returned by the Issues API are not dispatchable"). It carries no assignee
routing and no blocker evaluation at all.

The two real implementations, for reference:

```elixir
# linear/client.ex:496-513
defp dispatchable?(state_name, blockers, assignee, assignee_filter) do
  assigned_to_worker?(assignee, assignee_filter) and
    not blocked_before_dispatch?(state_name, blockers)
end
defp blocked_before_dispatch?(state_name, blockers) ... do
  normalize_state_name(state_name) == "todo" and
    Enum.any?(blockers, fn
      %{state: blocker_state} when is_binary(blocker_state) -> not terminal_state?(blocker_state)
      _ -> true                      # unparseable blocker ⇒ treat as blocking
    end)
end
```

Jira's is the same shape with a Jira-native twist — it gates on the **status category**
`new` when present, falling back to the state name `todo`/`to do`
(`jira/client.ex:337-356`), i.e. it uses the provider's own coarse grouping rather than
hardcoding state spellings. `elixir/README.md:266-267` states the policy: "issues in
Jira's `new` status category wait until blockers reach configured terminal states, while
in-progress categories keep running" — the same admission-only gating cymphony
reimplemented in its scheduler (§1.6).

**This also confirms §1.6 independently.** The only `blocked_by` reference in
symphony's `orchestrator.ex` is a **log line** —
`"…state=… blocked_by=#{length(refreshed_issue.blocked_by)}"` (`orchestrator.ex:930`).
The scheduler counts blockers for the log and never branches on them. Adapter owns the
semantics; scheduler owns one boolean. Exactly as `SPEC.md:2115` specifies.

### 5.4 …but that is a statement about symphony's AGE, not about GitHub

**GitHub Issues today has native issue dependencies and sub-issues, and symphony's
adapter predates them.** Probed live 2026-08-05 against this repo, fully armed in both
directions:

| Probe | Result |
|---|---|
| `gh api repos/ray-manaloto/dotfiles/issues/573` → keys matching `sub_issue\|depend\|parent\|type` | **`issue_dependencies_summary`, `parent_issue_url`, `sub_issues_summary`, `type`** |
| CONTROL — total keys on that payload | 35 (endpoint live) |
| `GET .../issues/573/dependencies/blocked_by` | **200** |
| `GET .../issues/573/dependencies/blocking` | **200** |
| `GET .../issues/573/sub_issues` | **200** |
| CONTROL (good) — `.../issues/573/comments` | 200 |
| CONTROL (bad) — `.../issues/573/zzqnotarealsubres` | **404** |

The bad arm 404s, so the 200s discriminate.

**This repo is already using it.** Issue #573's own payload:

```json
"issue_dependencies_summary": {"blocked_by": 0, "blocking": 4, "total_blocked_by": 2, "total_blocking": 4}
```

and its `blocked_by` list resolves to **#564 (closed)** and **#565 (closed)** — the two
probes this work depended on. Control: issue #1 returns `"issue_dependencies_summary":
null`, so the field discriminates present-from-absent.

**Semantics, proven rather than assumed:** `total_blocked_by: 2` counts all declared
blockers while `blocked_by: 0` counts the ones still **open**. So:

> **`issue_dependencies_summary.blocked_by == 0` IS the ready-check predicate — a
> single precomputed integer on the issue payload, no extra request, no client-side
> blocker-state evaluation.**

That is **strictly less work than symphony's Linear adapter does**, which fetches each
blocker and evaluates its state name against the terminal set client-side
(`linear/client.ex:501-518`). GitHub computes it server-side and hands it over for free.

### 5.5 What this means for the decision

The naive reading of §5.3 — *"symphony ships a worked-out Linear adapter and a stub
GitHub one, so Linear wins"* — **inverts once §5.4 is on the table.** Symphony's GitHub
adapter is thin because GitHub Issues had no dependency graph when it was written, not
because GitHub can't carry one. Today it can, and this repo already does.

Weighing the two for #573:

**Favours GitHub Issues**
- Native `blocked_by`/`blocking`/`sub_issues` **already in use on our tickets**, with the
  ready-predicate precomputed (§5.4). Adopting Linear would mean re-entering that graph.
- The tracker is where the work already lives — issues #556/#565/#567/#573 and the whole
  wayfinder map. No sync layer, no second source of truth.
- `gh` is already authenticated, already guard-wrapped (`mise run ship`/`land`/
  `automerge`), and `GITHUB_TOKEN` is already in the credential set.
- Sub-issues give a second, orthogonal edge type (containment) that Linear's blocker
  relation alone doesn't.

**Favours Linear**
- Symphony's *worked example* is Linear, and it is the one with assignee routing +
  blocker gating already written (§5.3). Porting Jira's status-category variant is the
  closer analogue than porting the GitHub stub.
- Rich native workflow states. GitHub gives only `open`/`closed`, so the fine-grained
  pipeline stage must live in labels or a structured comment (stokowski's split, §2.2) —
  though note that split is *good practice anyway*, and stokowski adopted it **despite**
  running on Linear.
- Four of the five codebases surveyed are Linear-only, so borrowed code lands on Linear
  with less translation.

**My read:** the Linear advantage is *borrowed-code convenience*; the GitHub advantage
is *the data is already there, in the right shape, with the predicate precomputed*. The
strongest single argument is that #573's own dependency edges are already correct in
GitHub — a Linear migration starts by rebuilding a graph we can currently query in one
field. What we'd give up is workflow-state richness, and stokowski's comment-state
pattern (§2.1–2.2) already solves that on a tracker that has richer states than GitHub.

### 5.6 Follow-up probe: the summary rides along on the LIST endpoint (resolved)

The load-bearing open question was whether `issue_dependencies_summary` appears only on
the single-issue GET. If so, a poll loop would pay **one extra request per candidate per
tick** for its ready check. Probed 2026-08-05:

```
gh api "repos/ray-manaloto/dotfiles/issues?state=open&per_page=3"
  → #583 {"blocked_by":1,"blocking":0,"total_blocked_by":1,"total_blocking":0}  sub:{...}
  → #582 {"blocked_by":1,"blocking":1,"total_blocked_by":1,"total_blocking":1}  sub:{...}
  → #581 {"blocked_by":1,"blocking":0,"total_blocked_by":1,"total_blocking":0}  sub:{...}
CONTROL (single GET, known present) → #573 {"blocked_by":0,"blocking":4,...}
```

**Both `issue_dependencies_summary` and `sub_issues_summary` are present on the list
endpoint.** So symphony's REQUIRED `fetch_issues_by_states` operation (§5.2) can compute
`dispatchable` — including full blocker gating — from **one paginated list call per
tick**, with zero per-issue follow-ups.

That is better than symphony's Linear adapter manages, and it removes the last
GitHub-side objection: the ready predicate is free, batched, and server-computed. (Live
data incidentally confirms the graph is real and in active use — #581/#582/#583 each
currently report one open blocker.)

**Still NOT verified, deliberately: the dependency WRITE surface.** Creating or removing
an edge would mutate Ray's real issue graph, so I did not probe it — an unrequested
write to the tracker under evaluation is not a probe I should run unasked. If the design
needs the loop to *author* edges (rather than only read them), that endpoint shape must
be confirmed first, ideally against a throwaway repo.

---

## GitHub repos touched

- [zaalipro/cymphony](https://github.com/zaalipro/cymphony) — primary survey target; cloned at `fb1660d` and read (agent adapter, runner, orchestrator, WORKFLOW.md, README).
- [openai/symphony](https://github.com/openai/symphony) — upstream spec; read from the offline copy (`SPEC.md` §8.2/§14, `elixir/README.md`, `elixir/WORKFLOW.md`) and used as the cross-check authority for cymphony's blocker-rule citation.
- [Sugar-Coffee/stokowski](https://github.com/Sugar-Coffee/stokowski) — cloned at `6e51bdf`; deep-read `tracking.py`, `orchestrator.py`, `config.py`, `linear.py`.
- [Pimpmuckl/symphony-plus-plus](https://github.com/Pimpmuckl/symphony-plus-plus) — most divergent active fork (596 ahead); metadata + description only, **not read**.
- [ProlokGmbH/Symphony](https://github.com/ProlokGmbH/Symphony) — 336 ahead; metadata only, **not read**.
- [EmberAGI/symphony](https://github.com/EmberAGI/symphony) — 120 ahead; metadata only, **not read**.
- [acancelas/symphony](https://github.com/acancelas/symphony) — 51 ahead; metadata only, **not read**.
- [kingzeus/symphony](https://github.com/kingzeus/symphony) — 9 ahead; metadata only, **not read**.
- [manav03panchal/phonyhuman](https://github.com/manav03panchal/phonyhuman) — not re-surveyed; cited from `symphony-and-ports.md` §2.3 for the missing-`--resume` contrast.
- [mksglu/hatice](https://github.com/mksglu/hatice) — not re-surveyed; cited from `symphony-and-ports.md` §2.2 for the `bypassPermissions` default and its `linear`/`github`/`gitlab` adapter set (§5.1).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo; its live Issues API was the probe target for GitHub's native dependency/sub-issue surface (§5.4, §5.6). Read-only — no dependency edges were created or removed.

