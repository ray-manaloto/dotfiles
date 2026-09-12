# agentsview in the wild — field research

**Lane:** field research (read-only). **Date:** 2026-09-12.
**Question:** how do other projects actually use `kenn-io/agentsview` data to make
their agents better — specifically self-improvement, self-healing, self-optimisation
of a Claude Code + Codex setup?

**Status: IN PROGRESS — appended as work proceeds.**

## Tool availability (reported up front, per the brief)

| Named lane | Available to me? | Evidence |
|---|---|---|
| `/last30days:last30days` | **YES** (skill listed) | in my skill listing |
| `/firecrawl:firecrawl-search` | **NO** | `ToolSearch "firecrawl search scrape"` returned only `WebSearch` + a Chrome `find` tool; no `mcp__firecrawl*` anything |
| `/firecrawl:firecrawl-developer-index` | **NO** | same probe |
| `/exa:search` | **NO** | `ToolSearch "exa context7 docs library search"` returned `WebSearch`/`WebFetch`/Chrome tools only |
| `/context7:docs` / `/context7:context7-mcp` | **NO** (as MCP) | same probe. A *project skill* `context7-cli` exists, which shells out to a `ctx7` binary — a different mechanism |

**This confirms the previous lane's report.** Firecrawl, Exa and Context7 are not
registered MCP servers in this session's tool pool. Control arm: the same
`ToolSearch` calls DID return `WebSearch`, `WebFetch` and
`mcp__claude-in-chrome__*` / `mcp__computer-use__*` tools, so the probe
discriminates — the deferred-tool index is readable and those servers are simply
absent from it. Lanes fall back to `WebSearch`/`WebFetch`, `gh`, and
`/last30days`.

## Method log

- Step 00 (offline KB corpus, `~/dev/github/ray-manaloto/knowledge-base/sources/`):
  `grep -ril agentsview` over 216 trees → **2 hits, both metadata**
  (`agentsview.manifest`, `REGISTRY.md`). There is **no cloned agentsview source
  tree** — the manifest exists but `sources/agentsview/` is gitignored and
  un-cloned. Control arm: the same grep returned hits, and a grep for
  `graphify` over the same corpus returns many trees, so the corpus is
  readable; agentsview is simply not ingested.
- Step 0 (local mintlify cache, `docs/research/mintlify-cache/`): **0 hits**.
  Cache holds only `devcontainers jdx knowsuchagency starship twpayne wagoodman
  yeachan-heo`. agentsview is not cached.
- Therefore the primary surfaces for this lane were `gh search repos`,
  `gh search code`, `gh api` on issues/discussions, and `WebFetch`.
- ⚠️ **Environment trap for the next lane:** in this repo `timeout` is a broken
  mise shim (`mise ERROR No version is set for shim: timeout`). Do not prefix
  `gh` calls with `timeout`; it kills the call and still reports `RC=0` because
  the shim's failure is the last pipeline element.

## What the manifest and REGISTRY already establish

From `knowledge-base/sources/agentsview.manifest` (read verbatim):

- pin `v0.42.0`, peeled commit `ff8fb4e84823b9583eba417afc243140caabdcb0`,
  added 2026-09-11, `kind = code`.
- **The pin is deliberately one release behind the feature the KB wants.**
  `effort` capture for Claude Code AND Codex sessions is **upstream PR #1677,
  merged 2026-09-10, in no release yet**. Bumping to the release that carries it
  "triggers a documented FULL SESSION RESYNC to populate effort from source
  transcripts, which against a ~5 GB archive is a real cost, not a formality."
- The tag is annotated — the commit above is the peeled commit, not the tag
  object `94b3676f3cfcb32d95ff07547db727e3c95564ba`.

From `knowledge-base/sources/REGISTRY.md` rows 153+ (read verbatim), two
measured facts its own docs get wrong:

1. **Only `usage daily` reads SQLite directly.** `session search`, `session list`,
   `stats`, `projects` and `health` all exit 1 with *"daemon autostart is
   disabled"* under `AGENTSVIEW_NO_DAEMON=1` — including `session list`, which the
   README annotates as "read from the daemon if warm, otherwise SQLite".
2. **`open_issues_count` is not the issue count** — REST read 94 on 2026-09-01;
   issues-only search read 71; 23 open PRs.

Also from REGISTRY: `agentsview serve` starts a local web UI and is deliberately
NOT a mise task (a server gives an agent no bounded output, and
`long-running-command-hangs.md` rule 2 forbids `&`-detaching a local `mise run`);
`agentsview daemon stop` ends the background daemon the search path autostarts.

## FINDING 0 — the headline: the feedback loop is FIRST-PARTY and DOCUMENTED

The operator asked for techniques other people have already worked out. The
single largest one is that **the maintainer has already designed and shipped the
loop**, and publishes it as a nine-stop tour: `https://agentsview.io/guide.md`
("The session intelligence loop"), linked from `docs/llms.txt` under `## Product`.

⚠️ **`curl` it with `-L`.** A bare `curl https://agentsview.io/guide.md` returns
**15 bytes of `Redirecting...`** — a false negative that reads like an empty
page. Control arm: `curl -sSL` on the same URL returns 3,574 bytes.

Verbatim, stop **08 of 09** — this is the operator's stated goal in the vendor's
own words:

> ## 08. Give your agents the archive
>
> The loop closes when agents read their own history. The MCP server exposes
> session history as assistant tools, the REST API and CLI serve scripts and
> hooks, and SSE streams live messages. An agent can check what a previous run
> tried before repeating it. [MCP server](/docs/mcp/) · [Session API](/docs/session-api/).

And stop **06**, which is the self-diagnosis half:

> ## 06. Assess session health
>
> Session intelligence classifies outcomes and scores health from the transcript
> itself: tool failures, context pressure, and loop signals. Deterministic quality
> rules turn recurring patterns into recommendations, each backed by the source
> sessions that triggered it.

The practical consequence: **most of what a self-healing/self-optimising layer
needs already exists as a deterministic, model-free, JSON-emitting surface.**
Do not build a transcript analyser. Read the one that ships.

## FINDING 1 — `session-intelligence` is the self-healing substrate (first-party, deterministic)

Source: `docs/session-intelligence.md` @ `v0.42.0` (7,324 bytes, fetched via
`gh api contents`). Shipped in **0.23.0**, so it is well-aged, not a preview.

**Health score** — penalty-based out of 100, graded A(90-100)/B(75-89)/C(60-74)/
D(40-59)/F(0-39), from three categories (Outcome, Tool health, Context pressure).
The published penalty table, verbatim:

| Signal | Penalty |
|---|---:|
| `errored` outcome | 30 |
| `abandoned` outcome | 15 |
| tool failure signal | 3 each, capped at 30 |
| tool retry | 5 each, capped at 25 |
| edit churn | 4 each, capped at 20 |
| consecutive failure streak of 3+ | 10 |
| extra compactions after the first | 5 each, capped at 15 |
| mid-task compaction | 8 each, capped at 18 |
| context pressure above 0.9 | 10 |

**These are exactly the anti-patterns the operator wants detected**, already
named and counted:

- **Retries** — "repeated identical tool calls when the same tool name and
  identical input are invoked 3 or more times in a row". That is a loop detector.
- **Edit churn** — "files that were edited or written 3 or more times within a
  tight ordinal window, which usually signals rework".
- **Consecutive failure max** — "the longest run of failed tool calls in a session".
- **Failure signals** — from "explicit `errored` or `cancelled` status events or
  from content heuristics such as shell errors and `FAILED` write/edit results".
- **Mid-task compactions** — "compactions that interrupted active work instead of
  happening at a clean boundary", weighted higher "because they are a stronger
  sign that the agent lost working context and had to recover".

**Outcome classification**: `completed` / `abandoned` / `errored` / `unknown`,
each with `high`/`medium`/`low` confidence. Documented rules include "sessions
that end on a user turn skew toward `abandoned`" and "sessions with a final
failure streak of 3 or more skew toward `errored`".

⚠️ **Documented honesty caveat, quote it when citing a score:** "These signals
are heuristics, not ground truth. They are meant to help with triage and
pattern-finding, not to replace your own judgment."

⚠️ **Unscored is a real third state, not a zero.** "Some sessions remain
unscored… when AgentsView cannot infer a meaningful result beyond an `unknown`
low-confidence outcome". And per `docs/quality.md`: "Sessions that cannot be
scored remain visible in the coverage counts instead of being silently treated as
healthy." A gate that reads unscored as healthy inverts the signal — this is the
control-arm trap built into the data model.

**The automation-facing surface** (verbatim from the doc):

```bash
agentsview health                       # recent sessions, grade + outcome columns
agentsview health <session-id> --json   # detailed signal counts for one session
agentsview session get <id> --format json          # incl. health_score_basis, health_penalties
agentsview session list --health-grade A,B --outcome completed
agentsview session list --min-tool-failures 0
```

`session list` filters `--health-grade`, `--outcome`, `--min-tool-failures` are
what make a **scan** possible: "exposes health and outcome filters for
automation-friendly scans" (their words).

## FINDING 2 — `quality` is a rule-based RECOMMENDATION engine, explicitly model-free

Source: `docs/quality.md` @ `v0.42.0`. This is the piece that matters most for
"self-optimisation without adding an LLM call", verbatim:

> Quality summarizes observable patterns in your session archive. Unlike
> [Generated insights](/docs/recall/#current-surface), every score, count, and
> recommendation on this page is computed directly from stored session data; the
> page does not call a model.

> The first section translates measured patterns into rule-based next actions. A
> recommendation appears only when its corresponding threshold is met.

> Use Generated insights when you want a model-written report over a chosen
> scope. Use Quality when you need repeatable metrics whose results do not depend
> on a model response.

So upstream ships **two** insight tiers and draws the line the operator would
want drawn: deterministic rules for gates, model-written reports for reading.
A gate must sit on Quality, never on Generated Insights.

⚠️ **Premise I could NOT settle:** `docs/quality.md` documents the `/quality`
**web page** and does not name a CLI or JSON route for the recommendations. I did
not find a `agentsview quality --json` in the docs I read (`commands.md` is 75 KB
and I did not exhaust it). Whether the rule-based recommendations are reachable
headlessly is **UNVERIFIED and load-bearing** for any gate design — check
`docs/commands.md` for a `quality` verb before designing around it.

## FINDING 3 — the MCP angle: upstream ships its OWN MCP server. Prefer it.

Source: `docs/mcp.md` @ `v0.42.0`. **`agentsview mcp` is a first-party,
read-only MCP server.** This substantially changes the architecture question and
makes both third-party MCP repos redundant.

Six tools, verbatim from the doc's table:

| Tool | Purpose |
|---|---|
| `search_sessions` | Full-text search across recorded sessions |
| `list_sessions` | List recent or filtered sessions |
| `get_session_overview` | Fetch metadata and a compact message preview |
| `get_messages` | Read paginated message bodies from one session |
| `search_content` | Substring, regex, semantic, or hybrid search over raw session text |
| `get_usage_summary` | Aggregate token and cost usage |

Design details that matter here:

- Modes: stdio (default, "safest choice for local MCP clients"),
  `--http 127.0.0.1:8085` StreamableHTTP, `--server <url>` against a running
  daemon, and `--pg` to read PostgreSQL directly.
- **`search_content` carries citations**: every match returns an `ordinal_range`
  `[start, end]` plus `subordinate`, `relationship`, `parent_session_id`,
  `is_sidechain` — so **subagent and sidechain hits are flagged**, which a
  multi-lane setup like this repo's needs to avoid attributing a lane's failure
  to the coordinator.
- ⚠️ **MCP mode is daemon-backed and INCOMPATIBLE with `AGENTSVIEW_NO_DAEMON=1`**:
  "If you need to disable daemon auto-start for general CLI work with
  `AGENTSVIEW_NO_DAEMON=1`, do not use local MCP mode for that archive." It never
  opens SQLite directly, by design.
- Non-loopback binds require `--http-allow-insecure` **and** a bearer token.
  "The local config `auth_token` is not sent to explicit `--server` URLs."
- Security note worth carrying: "The MCP server can reveal prompts, assistant
  responses, tool output, file paths, project names, and usage totals. Treat it
  like access to your session archive."

**Relevance to this repo's MCP lane policy** (`research-doc-sources.md`
§ "MCP: two lanes"): this is our own lookup, so it is lane 2 — CLI/API first.
But note the CLI and the MCP server are the *same* first-party binary over the
*same* daemon, so the usual lane-2 objections (a new process to pin, a new auth
path, a new failure mode for the doctor) mostly do not apply: the daemon is
already there either way. The honest framing is that `agentsview mcp` is a
*presentation* of the CLI we already run, not a new dependency.

## FINDING 4 — SETTLED: the schema DOES store individual tool calls with their command strings

This is the KB's issue **#638 §11** premise, described in the brief as UNVERIFIED
and load-bearing. **It is now settled POSITIVELY from the upstream API spec**, not
from a summary. Source: `docs/session-api.md` @ `v0.42.0`, section
`### agentsview session tool-calls` (line 371), verbatim response shape:

```json
{
  "tool_calls": [
    {
      "ordinal": 3,
      "timestamp": "2026-04-18T12:05:00Z",
      "tool_use_id": "toolu_01abc...",
      "tool_name": "Bash",
      "category": "Bash",
      "input_json": "{\"command\":\"ls\"}",
      "skill_name": "",
      "subagent_session_id": "",
      "result_length": 128
    }
  ],
  "count": 1
}
```

**So policy-compliance detection IS possible.** `input_json` carries the tool
input verbatim — for `Bash` that is the command string. Two fields make it
better than expected for this repo specifically:

- **`skill_name`** — attributes a call to the skill that made it.
- **`subagent_session_id`** — attributes a call to a delegate lane. With a
  codex/Claude multi-lane setup, this is what stops you blaming the coordinator
  for a lane's violation.

Corroborating evidence from a second route (`docs/session-api.md:599`): the
`session search` `--in` flag takes `messages,tool_input,tool_result` (default
all), and `:1072` names a fourth location `tool_result_event`. So tool inputs are
not merely returned by one command — they are an indexed, searchable location.

⚠️ **Three caveats that decide a gate's design:**

1. **`input_json` is a STRING, and its shape is agent-dependent.** Verbatim:
   *"`input_json` is a string — usually a serialized JSON object but may be a
   plain string (e.g. `"echo hello world"` from Codex)."* A parser that assumes
   `json.loads(input_json)["command"]` **breaks on Codex sessions** — precisely
   the half of this operator's setup that motivated adopting agentsview. Handle
   both shapes.
2. **`tool-calls` gives you command text but NOT result text** — only
   `result_length`. To read what a command *did*, use
   `session search --in tool_result` or `session export <id>` (raw source JSONL).
3. **`session export` is LOCAL-ONLY and rejects `--server`, `--pg`, `--format`
   and `--json`** — it streams raw bytes from a path resolved out of the local
   SQLite archive. Four documented exit states, all exit 1 with distinct
   messages. A pipeline that can run against a remote daemon cannot use `export`.

⚠️ **A prior artifact in the sibling KB overclaimed and should be corrected.**
`knowledge-base/docs/artifacts/three-questions-before-the-spec.html` records the
resolution as *"structured tool input/output, full Bash command text including
heredocs"*. The **input** half is confirmed above. The **output** half is not:
`tool-calls` returns `result_length`, not the result. And I found no upstream
statement about heredoc handling specifically — that word appears nowhere in the
docs I fetched. Treat "including heredocs" as **unverified**; the general claim
that full command text is retained is supported by `input_json` being the raw
serialized input.

## FINDING 5 — the single most copyable technique: `agentsview skills install`

**Upstream ships a skill GENERATOR that teaches a coding agent to search its own
history — and it targets Claude Code AND Codex explicitly.** Source:
`docs/commands.md:1277` (`### agentsview skills`), verbatim:

> Install or list the bundled skill files that teach coding-agent harnesses
> (Claude Code, Codex, and other `.agents/skills` readers) to search AgentsView
> history.

```bash
agentsview skills install [--harness claude|agents] [--project] [--force]
agentsview skills list [--project] [--format json]
```

Mechanics, verbatim: it *"renders the embedded `agentsview-finding-history` skill
for each `--harness` (default both) and writes `SKILL.md` under
`~/.claude/skills/agentsview-finding-history/` and/or
`~/.agents/skills/agentsview-finding-history/`, or under `.claude/skills/` /
`.agents/skills/` at the current git root with `--project`. It overwrites an
unmodified generated file, refuses a hand-edited or foreign file unless
`--force` is passed, and exits non-zero on any refusal."*

`skills list` reports **HARNESS, LEVEL, STATE (`missing`, `current`, `stale`,
`modified`, `foreign`), PATH** — and `--format json`.

**Why this is the top recommendation for this repo.** It is a first-party,
versioned, drift-aware installer with a machine-readable state check. Three
properties this repo's gates actually want:

- `--project` writes into `.claude/skills/` at the git root — a **reviewed diff**,
  not a mutation of `~/.claude`. This is the exact shape `do-not.md` #8 demands
  of `graphify install` (always `--project`, never let a tool mutate `~/.claude`).
- `skills list --format json` with a `stale`/`modified` STATE is a ready-made
  **currency check** — a `tool-currency-and-native-first.md`-style drift gate
  with no custom code.
- It "refuses a hand-edited or foreign file unless `--force`… and exits non-zero
  on any refusal" — it fails loud, which is what a gate needs.

⚠️ **BUT: the generated skill has a MEASURED, upstream-acknowledged defect in the
exact recipe this repo would rely on.** Upstream issue **#1511**, *"SKILL.md's
search recipe cannot find identifiers: --fts excludes tool_input, and prescribes
it exactly for identifier hunts"* — filed against v0.40.1, **CLOSED 2026-09-03**,
which is **after v0.41.1 and before v0.42.0 (2026-09-01)**… note the ordering:
closed 2026-09-03 is *after* the v0.42.0 release of 2026-09-01, so **v0.42.0 may
still ship the defective skill text.** Verify with `skills install` then read the
rendered SKILL.md; do not assume the pin carries the fix.

The defect itself is a textbook probe-with-no-control-arm, in the reporter's own
measurement (verbatim table):

| Mode | Hits in the session that actually created it |
|---|---|
| `--fts` (what SKILL.md prescribes) | **0** — only the *currently running* session's chatter came back |
| plain + `--in tool_input` | **19** (plus 3 in a sibling session) |

> The causer session is invisible on the prescribed path. Nothing errors; you get
> a smaller answer that reads like a finding. That is the part worth fixing — a
> wrong mode here does not fail loudly.

Three operational traps from that issue, all of which apply to any query this
repo writes:

1. **`--fts` and `--in` are mutually exclusive**, enforced client-side:
   `fatal: --fts searches messages only; drop --in or --fts`. So the correct
   mode table is: prose/reasoning → `--fts`; **identifiers (ids, paths, commands,
   error strings) → plain search + `--in tool_input,tool_result`**. Plain search
   (neither flag) is the mode that reaches tool calls, and the generated skill
   "never mentions it as a mode at all".
2. **There is no `--exclude-session`.** "The archive ingests the live session, so
   for anything the current conversation just discussed, its own echoes are the
   freshest matches and outrank real history." A self-inspecting agent reads its
   own noise first. Workaround: `--limit 60` plus post-filtering the current
   session id. **This is the load-bearing gotcha for a self-improvement loop** —
   the loop's own output pollutes its input.
3. **Remote-daemon installs render wrong examples.** Every generated example
   omits `--server` / `--server-token-file` and "silently queries the local
   SQLite index instead — under-reporting without any signal."

## FINDING 6 — real-world usage patterns, with what they pull and what it drives

Ranked by evidence strength. "Acts" vs "looks at" is the operator's distinction.

### 6a. `danbri/factoidal` — `skills/session-cost-accounting/SKILL.md` — ACTS (budget decisions)
A Claude Code skill wrapping a `tools/session-cost.sh` one-liner. Pulls
`session list --include-children --json` then `session usage <id> --json` per id;
sums `cost_usd`. Drives: subagent fan-out planning against a budget, and
retrospectives that carry real spend.

⚠️ **The measured trap worth copying outright — and it is the single most
relevant number in this report for a multi-lane setup.** Verbatim:

> **Main-session usage alone under-counts badly.** On 2026-07-05 the main
> session read ~$1,044 while the 103 subagent children carried another ~$617 —
> **37% of real spend invisible without `--include-children`.**

Because *"subagent transcripts are separate sessions with `agent-<id>` ids,
EXCLUDED by default"*. This repo runs codex lanes and named Claude subagents
constantly; **any cost or health figure computed without `--include-children`
is wrong by roughly a third**, and wrong in the direction that looks fine.

Two more traps from the same file, both false-signal shapes:

- **`started_at`, never `created_at`.** Verbatim: *"`created_at` … is the DB
  row's insertion time and reads as 'just now' after any resync."* A freshness
  check built on `created_at` can only pass.
- **No bulk usage endpoint** (as of v0.36.1) — `session usage` takes one id, so a
  per-id loop is required (104 ids ≈ a minute).
- Cost is an **estimate** from public pricing for the models in `models`; the
  skill mandates labelling it "estimated" and reporting the main/subagent split
  rather than a bare total.

### 6b. `durandom/fullsend-sessions` — `skills/agentsview/SKILL.md` (8.5 KB) — the best-engineered consumer
A container-backed (Podman) AgentsView service queried by a Claude skill. It is
the most disciplined design I found, and four of its rulings are directly
transplantable:

- **A preflight script, not ad-hoc probing**: `python scripts/preflight.py --json`
  returns `binary`, `server_url`, `server_token_file`, `available`, `working`.
- **"Consume the complete JSON output. Do not pipe it through `head`, `tail`, or
  `grep`."** — independently arrives at this repo's own
  `feedback_pipe_kills_exit_code` rule.
- **It sidesteps the daemon entirely**: `export AGENTSVIEW_NO_DAEMON=1` plus
  `--server "$AGENTSVIEW_SERVER_URL"`, because *"the container owns the database
  and indexing"*. This is the clean answer to every daemon-reliability issue in
  Finding 8.
- **It reads the token file by path and never into context**: *"append
  `--server-token-file <path>` … without reading the token into context."*

Its three `<essential_principles>`, verbatim, are an architectural ruling the
operator should decide on deliberately:

> `evidence_not_analysis`: Retrieve and summarize what AgentsView records. Do not
> judge whether a session was good, efficient, or successful, and do not
> recommend prompt, skill, or workflow changes. **Those conclusions belong to a
> later session-analysis skill.**

> `heuristics_are_labels`: Report health scores, outcomes, confidence, and
> penalties as AgentsView-derived heuristics. Attribute them explicitly to
> AgentsView and do not convert them into ground truth about delivery success.

> `read_only_default`: Use read commands only. Do not run `prune`, `import`,
> `update`, PostgreSQL or DuckDB writes, secret reveal, or other administrative
> commands. … use `--full` only when the user specifically agrees to a full resync.

**Note what that first principle concedes**: the most sophisticated public
consumer deliberately **stops short of self-optimisation** and defers it to a
skill that does not exist in that repo. That is evidence for Finding 7.

### 6c. `Lazymindz/agentsview-hermes-ops` — ACTS (scheduled, threshold-driven)
Python, stdlib-only, **the clearest "automation that acts" example**: a
deterministic daily summary run by Hermes cron, delivered to chat. Pulls
`agentsview sync`, `stats`, `usage`, plus direct reads of
`~/.agentsview/sessions.db`. Emits cost/tokens, sessions/messages/failures/
retries/abandoned/secrets, session-intelligence rollups, an **"attention
sessions"** list (worst by health/failures/retries/prompt/context), agent mix,
and **exactly one concrete recommendation**.

Thresholds are explicit flags: `--cost-warn 20.0`, `--retry-warn 25`,
`--days`, `--no-sync`, `--sync-timeout 180`. Its README documents the query set:

```bash
agentsview session list --min-tool-failures 1 --limit 20
agentsview session get SESSION_ID --json
agentsview session messages SESSION_ID --json --limit 20
agentsview session tool-calls SESSION_ID --json
agentsview session search "Traceback" --in tool_result
agentsview secrets scan
agentsview secrets list
```

Two design choices to copy: it *"fails soft with a short diagnostic instead of a
traceback wall"*, and the cron job is **script-only** — *"script-only jobs
deliver the script stdout verbatim and do not require an LLM call."* A
deterministic report with no model in the loop is exactly the gate shape this
repo prefers.

⚠️ **Maintenance: DEAD.** 0 stars, last commit 2026-06-30, and it names signal
families ("prompt maturity", "runaway loops", "context health") whose provenance
I did not verify — some are its own computations over `sessions.db`, not
necessarily agentsview-native fields. Copy the *shape*, re-derive the *signals*.

### 6d. `mrojas54/tool-benchmarks` — ACTS (the closest thing to self-optimisation)
**1 star, but ALIVE and serious**: 1.8 MB, last commit 2026-09-08, PR #138
merged, Python stdlib-only. Description: *"analyzes tooling inefficiencies
(context cost, retries, deferral tax) across Claude Code, Codex, Hermes and
other AgentsView agents from their session transcripts — markdown report +
tool-vs-shell probes."*

What it measures, verbatim from its README:

1. **Cross-agent tool cost** — which tools, agents, projects and workflows dump
   the most context back into sessions.
2. **Tooling inefficiency patterns** — repeated failed calls, slow tools, edit
   churn, retry loops, context pressure, subagent fan-out.
3. **Deferral / discovery tax** — what deferred-tool loading and searching
   (e.g. `ToolSearch`) costs across Claude Code, Codex and Hermes.
4. **Controlled tool-vs-shell probes** — when native tools (Grep/Glob/Read) are
   cheaper or more reliable than shell commands.

Primary metric: **context cost = joined tool-result payload tokens (`chars / 4`)**.
*"Cache flags are caveat-only and never rank tools."*

⚠️ **Its most important ruling for this repo — it deliberately does NOT use
`session tool-calls` as its data source.** From
`docs/2026-07-07-tool-benchmarks-design.md`, verbatim:

> `agentsview session tool-calls <id> --json` is useful for validation/debugging
> only; do not use it as the primary context-cost source because the benchmark
> needs the raw joined result payload.

> Do not compute benchmark metrics from `agentsview session tool-calls`; it may
> be used only for spot-check validation because it is already parsed/normalized
> by AgentsView.

It uses `session export <id>` (raw source JSONL) instead, and parses itself. This
is consistent with Finding 4's caveat 2: `tool-calls` returns `result_length`,
not the result body. **If you need result payloads, `tool-calls` cannot serve
you; if you need command strings, it can.**

Its `--index-source auto|raw|agentsview` pattern is worth copying: `auto` tries
agentsview and *"falls back to raw filesystem scanning if the CLI is missing or
exits nonzero (for example, local daemon 'running but not responding')"*;
`agentsview` is strict and errors clearly. It also notes the CLI **caps pages at
500 sessions** and *"implementation must follow returned cursors"*.

And a false-negative lesson that mirrors this repo's own rules — verbatim:

> **No parser is the default.** An unrecognized transcript raises `UnknownSchema`
> … Previously such a session fell through to the Claude parser, matched nothing,
> and **reported a healthy zero.**

### 6e. Dashboards and status bars — LOOK AT only (not automation)
- `cpcloud/herdr-agentsview` — Rust TUI, "AgentsView activity, compressed into
  one very busy terminal". 2 stars, last commit 2026-08-24. Notable commit:
  *"fix: keep Activity reports when AgentsView adds fields (#17)"* — i.e. it was
  bitten by upstream schema drift. **Budget for that.**
- `riclib/omarchy-agentsview` — Omarchy status bar: sessions active now, today's
  scoreboard, search, resume.
- `franroa/chezmoi` — `tmux-context-inspector`: a 20-script tmux popup suite
  including `executable_show_health.sh`, `executable_show_health_overview.sh`
  and **`executable__recommend.sh` (7.6 KB)** — a consumer of the health +
  recommendations surface. Its help text maps `prefix+K → h` to
  *"Salud/inteligencia SESIÓN actual (`agentsview health <id>`) + Recommendations
  (secrets/fallo/friccion/insights-obsoleto/edit-churn — máx. 2, sólo si aplica)"*
  — note **"máx. 2, sólo si aplica"**: it caps recommendations at two and only
  when applicable. A good anti-nag default. Its
  `executable_show_context_files.sh` uses the `tool-calls` + `jq` recipe to rank
  files by read/edit/write count, filtering
  `.category=="Read"|"Edit"|"Write"|"MultiEdit"|"NotebookEdit"`.
- `sefk/llm-use-charts`, `managedkaos/agentsview-docker-compose` (run it as a
  service via compose), `christoph-jerolimov/agentsview-rhdh-extension`,
  `statik/agentsview-rstudio-addin`, `davlion/agentsview-thinking` (rank sessions
  by extended-thinking volume), `ochen1/agentsview-prompts` (export clean
  prompt-response history), `calvinchengx/synapse` (unify AgentsView with other
  agent tooling), `zhangyimin870220/agentsview-cn` (Chinese fork of v0.33.1).
- Other skill-shaped consumers found but not read in full:
  `akunzai/agent-skills` (`skills/agentsview-resume/SKILL.md` — resume-context
  reconstruction from `session messages --role user` + `tool-calls`),
  `jay-aye-see-kay/.pi` (`agent/skills/agentsview-history/SKILL.md`),
  `MooseGooseConsulting/frozenSkillz` (`personal-skills/chat-history`),
  `prateek/dotfiles` (`home/dot_agents/docs/agentsview.md`),
  `colinmollenhour/dotfiles` (`.claude/skills/colin-ultra-review/SKILL.md`),
  `radiator-engineering/eventlog` (an `agentsview-follow` template using
  `session watch`).

## FINDING 7 — self-healing / self-optimising precedents: THE HONEST ANSWER IS "ALMOST NOBODY"

The operator asked me to say so plainly if nobody does this. **Nobody publicly
closes the loop.** Here is the evidence, with control arms.

**What I searched for (GitHub code index), all returning 0:**

| Query | Hits |
|---|---:|
| `agentsview SessionStart` | 0 |
| `agentsview SessionEnd` | 0 |
| `agentsview PreToolUse` | 0 |
| `agentsview hooks settings.json` | 0 |
| `agentsview launchd` | 0 |
| `agentsview crontab` | 0 |
| `agentsview health-grade F` | 0 |

**Control arms (same command shape, same session, run alongside):**

- **Positive arm:** `gh search code 'agentsview session list'` → **5 hits**
  (`kenn-io/agentsview` README + 4 docs). So the index is reachable and the
  query shape works.
- **Negative arm:** `gh search code 'agentsview kwibbletron9'` → **0 hits**.
  Freshly invented for this run, never written to any tracked file before this
  report — and now that it appears here, **it is burned; invent a new one next
  time.** (`zxqprobe7` and `zzqqxx` were already burned per the brief.)

So the probe discriminates, and the zeros are real zeros.

⚠️ **Bound on that negative, stated rather than hidden:** GitHub code search
indexes public repositories' default branches and has its own coverage rules; a
private dotfiles repo, a gist, or a blog post would not appear. The claim I can
support is *"no public GitHub-indexed repository wires agentsview into a Claude
Code lifecycle hook, launchd job, or crontab"* — **not** "nobody has done it".

**What DOES exist, and it is nearer than zero:**

1. **Scheduled deterministic reporting with thresholds** —
   `Lazymindz/agentsview-hermes-ops` (6c). It runs on a cron, applies numeric
   thresholds, and emits one recommendation. That is automation that *acts* on a
   schedule; it does not act on the agent.
2. **Repeated-failure and waste detection** — `mrojas54/tool-benchmarks` (6d)
   measures exactly the operator's list: repeated failed calls, retry loops, edit
   churn, context pressure, subagent fan-out, and the deferred-tool discovery
   tax. But it emits a **markdown report for a human**; nothing feeds back.
3. **First-party recommendations** — `docs/quality.md`'s rule-based engine, and
   `franroa/chezmoi`'s `executable__recommend.sh` consuming it in a tmux popup.
   Again: surfaced to a human, capped at two, never enforced.
4. **The nearest thing to self-improvement upstream: `recall`** (experimental).
   From `docs/recall.md`: it *"stores compact facts, procedures, preferences, and
   warnings as entries"* with evidence links back to the source transcript, and
   **`recall brief` produces "a packed, trusted task briefing"**. That is the
   loop: distil past sessions → brief the next one. Commands: `recall list |
   get | stats | query | brief | extract | import --dry-run`.

   ⚠️ Upstream's own warning, verbatim: *"Recall's schema, scoring, trust policy,
   and workflows may change. Treat its entries and measurement rows as a
   rebuildable research corpus. Until Recall stabilizes, upgrades may require
   rebuilding its new tables instead of migrating them."* Do not build a gate on
   it yet. Also: *"The session archive remains authoritative and must not be
   deleted, truncated, or recreated to reset Recall."*

   Useful privacy detail: Generated insights can point at **any
   OpenAI-compatible endpoint, including a loopback local model** (the doc's own
   example is `http://127.0.0.1:11434/v1` with `llama3.1`), so model-written
   reports need not leave the machine. *"The endpoint receives transcript-derived
   content, so review the provider's privacy and retention behavior."*

**The structural reason the loop is missing** is visible in
`durandom/fullsend-sessions`' own principle (6b): the best-engineered consumer
*deliberately* refuses to judge sessions and defers that to *"a later
session-analysis skill"* that it never ships. Retrieval is solved and published;
**evaluation-and-enforcement is the unbuilt half, everywhere.**

**Therefore: if the operator builds a policy-compliance / self-healing gate on
this data, it is original work, not a copy.** The copyable parts are the data
access patterns (6a-6d), the traps, and upstream's own deterministic signal set
(Findings 1-2). The enforcement layer has no prior art to borrow.

## FINDING 8 — staying current, and running it as a service

### Release cadence: fast. Treat any pin as stale by default.
From `gh api repos/kenn-io/agentsview/releases` and `/tags`:

- **78 tags**, repo created **2026-02-19** — about 7 months. That is ~11
  releases/month.
- Recent: v0.42.0 (2026-09-01), v0.41.1 (08-18), v0.41.0 (08-17), v0.40.1
  (08-04), v0.40.0 (08-03), v0.39.0 (07-27), v0.38.1/.0 (07-13), v0.37.5→.1
  (07-08→07-10, five patches in three days), v0.36.1/.0 (07-03).
- **5,879 stars**, Go, `pushed_at = 2026-09-12T17:32Z` (today).
- **`main` is 11 days ahead of the newest release** — consistent with the KB
  manifest's note that `effort` capture (PR #1677, merged 2026-09-10) is in no
  release yet.
- ⚠️ **`has_discussions = false`** — there is **no Discussions tab**. The brief
  asked me to read issues *and* discussions; discussions do not exist. Issues
  are the only forum. (And per the KB's prior measurement, `open_issues_count`
  = 106 today mixes issues and PRs — do not quote it as an issue count.)

### Is there a daemon? Yes, and it is the main operational risk.
`docs/mcp.md`: *"Local MCP mode talks to the AgentsView daemon. Each tool call
resolves the local daemon and starts it when needed."* `agentsview daemon stop`
ends it; `AGENTSVIEW_NO_DAEMON=1` disables autostart but then **most read
commands fail** (per the KB's own measurement: `session search`, `session list`,
`stats`, `projects`, `health` all exit 1 — only `usage daily` reads SQLite
directly).

**Three open/recent daemon defects that bear directly on "run it as a service":**

1. ⚠️ **#1688 — idle daemon burns most of the machine's CPU. FILED AGAINST THIS
   REPO'S EXACT PIN.** Verbatim: *"agentsview v0.42.0 (commit ff8fb4e8, built
   2026-09-01T19:37:16Z), and still present on `main` at 988c7406"* — `ff8fb4e8`
   **is** the commit in `sources/agentsview.manifest`. Symptom: *"the serve
   daemon sits at eight to nine cores with no clients connected and startup sync
   long finished."* Cause: `readUsageRollupInstalls` in
   `internal/db/usage_rollup.go` reads all installed rollup rows per 256-session
   batch — *"the pass is therefore quadratic in archive size"*. Measured on a
   128,343-session archive: **3,161 CPU-seconds, 27,798 GC cycles**, 57% of
   allocation in that one function, ending in *"could not stabilize after 3
   attempts"*. **CLOSED 2026-09-10 — i.e. after v0.42.0, so the fix is
   UNRELEASED.** At ~3,276 sessions the operator's archive is ~40× smaller, so
   the effect should be far milder — but it is *quadratic*, so it worsens as the
   archive grows, and a background daemon at 8-9 cores on a Mac is exactly the
   failure the operator would notice as "everything is slow".
2. ⚠️ **#1249 (OPEN) — stale daemon record + macOS PID reuse = permanent
   deadlock.** *"AgentsView writes a daemon runtime record to
   `~/.agentsview/daemon.<pid>.json` on startup. On shutdown/crash, this file is
   not cleaned up."* The liveness check is `kill(pid, 0)`, and *"on macOS, PIDs
   are reused after reboot"* — the reporter's stale pid 1594 was reused by
   `FindMyMacd`, so agentsview concluded its backend was already running but
   unhealthy and `serve --background` refused to start. *"The desktop app has no
   path out of this state."* **This is a macOS-specific, reboot-triggered, hard
   wedge, and it is still open.** It is also a textbook liveness probe with no
   control arm — `kill(pid,0)` cannot distinguish "my daemon" from "some
   process".
3. **#1081 / #1082 (both OPEN) — daemon autostart races produce FALSE
   NEGATIVES.** #1081: *"daemon startup can make a successful ingest report 0
   sessions synced."* #1082: *"daemon autostart unexpectedly blocks a following
   artifact-folder sync."* A gate reading "0 sessions synced" as truth would be
   reading a race.

Other open performance issues worth knowing at this archive size: **#1375**
(feature request: *"official compaction/compression story for large sessions.db
(tool results dominate)"*), **#1592** (*"Opening the app takes 5 to 6 seconds
because the dashboard's year-range analytics queries read the whole archive on
every page load"*), **#1717** (*"Project extraction costs 12% of resync time
rescanning directories per session"*).

**The mitigation the field already uses:** `durandom/fullsend-sessions` (6b) runs
agentsview **in a container that owns the DB**, sets `AGENTSVIEW_NO_DAEMON=1` on
the host, and talks to it over `--server`. That removes host daemon lifecycle
from the equation entirely, and `managedkaos/agentsview-docker-compose` is a
ready-made compose file for exactly that. If the operator wants this running as a
service, **that is the shape with prior art**, not a host launchd job.

### Does the DB go stale? Yes — and `sync` is mandatory before any read.
- `danbri/factoidal`: *"**Sync first** — the DB lags the live transcripts:
  `uvx agentsview sync`."*
- `Lazymindz/agentsview-hermes-ops` runs `agentsview sync` before summarizing and
  exposes `--no-sync` / `--sync-timeout 180`.
- `agentsview doctor sync` exists as a diagnostic (per hermes-ops' prerequisites).
- Upstream's stop 01: the daemon *"keeps watching, so the archive stays
  current while you work"* — so with a live daemon, staleness is bounded; without
  one, an explicit `sync` is required.
- ⚠️ **A version bump can force a full resync.** Per
  `sources/agentsview.manifest`: bumping to the release carrying PR #1677
  *"triggers a documented FULL SESSION RESYNC to populate effort from source
  transcripts, which against a ~5 GB archive is a real cost, not a formality."*
  Budget for it; do not bump casually mid-session.

## FINDING 9 — current chatter (`/last30days`, the one named lane that WAS available)

Ran `last30days v3.24.0` on "agentsview session analytics for coding agents"
(engine + host-authored `--plan`, `--github-repo=kenn-io/agentsview`,
`--x-handle=kenn`, 5 subreddits). Window 2026-08-13 → 2026-09-12. 34 items across
5 sources. Raw saved to
`~/Documents/Last30Days/agentsview-session-analytics-for-coding-agents-raw-v3.md`.

**This is an INDEPENDENT route to Finding 7's negative, and it agrees.** Code
search found no automation; social listening finds no conversation. Over 30 days
the only agentsview-specific social item in the entire corpus is **one X post
with 3 likes**:

> "Local first session search for 20 plus coding agents. kenn-io/agentsview ships
> token stats and analytics: - Reads logs from Claude Code, Codex, others - Built
> by Wes McKinney's Kenn team The observability layer for coding agents."
> — [@so_sthbryan](https://x.com/so_sthbryan/status/2088487849700048943), 2026-08-15, 3 likes

**5,879 stars and 3 likes of monthly conversation.** The tool is widely installed
and essentially undiscussed as an analytics/self-improvement surface. (That post
also supplies a provenance fact I had not seen elsewhere — "Wes McKinney's Kenn
team" — which I am marking **unverified**: it is one low-engagement post and I
did not corroborate it.)

⚠️ **But the DEMAND is loud, and people are solving it with different
architecture.** The highest-signal adjacent item is exactly this operator's
problem, solved without agentsview:

> "sharing some notes from running hundreds of automated agent sessions across
> Claude Code, Codex, and Cursor. We started logging raw API request payloads
> **over a local proxy** to see where the token budget actually vanishes during
> long refactoring runs. Here are 18 specific token drains…"
> — [r/ClaudeCode](https://www.reddit.com/r/ClaudeCode/comments/1wcognm/18_hidden_token_drains_in_ai_coding_agent/), 2026-09-10, 56 pts, 21 comments

A **local proxy** captures request payloads live; agentsview reads transcripts
after the fact. For token-waste attribution the proxy sees things a transcript
cannot. Worth knowing before committing to a transcript-only design.

Two more signals that the category is hot while agentsview is absent from it:
- [Portal by Spotify cut my Claude Code token usage by 90%](https://engineering.atspotify.com/2026/9/portal-by-spotify-cut-my-claude-code-token-usage-by-90)
  — Hacker News, 2026-09-04, **277 points, 177 comments**. The single biggest
  engagement in the window on agent token waste, and it is not agentsview.
- ["How I keep track of ~100 parallel Claude Code sessions: Beads as a private
  work graph between GitHub and my agents"](https://www.reddit.com/r/ClaudeCode/comments/1wdrgz0/how_i_keep_track_of_100_parallel_claude_code/)
  — r/ClaudeCode, 2026-09-11. Four tmux sessions, 20-30 chats each: *"The agents
  cope fine. I didn't."* Solved with a hand-rolled work graph, not session
  analytics.

`--x-handle=kenn` resolved to the real maintainer (a 201-like post the same day),
confirming Kenn Ejima as the author's X account — but his own posting in the
window is unrelated to the product.

**Partial coverage, stated rather than hidden:** Web returned HTTP 422; Instagram
and TikTok both returned HTTP 402 (credits exhausted). Those three are *not*
"no discussion" — they are "never asked". Reddit, X, YouTube, HN and GitHub all
completed.

```
---
✅ All agents reported back!
├─ 🟠 Reddit: 9 threads │ 12,179 upvotes │ 388 comments
├─ 🔵 X: 9 posts │ 567 likes │ 48 reposts
├─ 🔴 YouTube: 5 videos │ 1,005,419 views │ 5/5 with transcripts
├─ 🟡 HN: 10 storys │ 780 points │ 422 comments
├─ 🐙 GitHub: 1 item │ 5,879 stars │ 106 comments
├─ 🗣️ Top voices: @kenn, @so_sthbryan │ r/ClaudeCode, r/VibeCodeDevs, r/SideProject
└─ 📎 Raw results saved to ~/Documents/Last30Days/agentsview-session-analytics-for-coding-agents-raw-v3.md
---
```

## RANKED RECOMMENDATION

Ranked by evidence strength, not by appeal. Each row says what the evidence is.

| # | Do this | Evidence strength | Why |
|---|---|---|---|
| 1 | **`agentsview skills install --harness claude --harness agents --project`**, then read the rendered SKILL.md and fix the `--fts` recipe per #1511 | **Documented first-party practice.** `docs/commands.md:1277` | One command gets a maintained, drift-checkable skill for BOTH harnesses, as a reviewed diff in `.claude/skills/`. `skills list --format json` gives a free currency gate. Cheapest real capability in this report. |
| 2 | **Build the gate on `session-intelligence` + `quality`, not on a homegrown transcript parser** | **Documented first-party, shipped since 0.23.0.** `docs/session-intelligence.md`, `docs/quality.md` | Retries, edit churn, failure streaks, mid-task compactions, outcome classification and a model-free recommendation engine already exist with a published penalty table and `--health-grade` / `--outcome` / `--min-tool-failures` filters. Re-implementing this is the mistake. |
| 3 | **Use `session tool-calls --json` for policy-compliance detection — `input_json` + `skill_name` + `subagent_session_id`** | **Settled from the API spec.** `docs/session-api.md:371` | Answers KB #638 §11 positively. Handle the Codex plain-string shape. For result *bodies* use `session search --in tool_result` or `session export`. |
| 4 | **Put `--include-children` on every query, without exception** | **Measured, third-party.** `danbri/factoidal` skills/session-cost-accounting | 37% of real spend was invisible without it (103 subagent children). This repo is multi-lane; the default excludes exactly the lanes it runs. |
| 5 | **Copy `durandom/fullsend-sessions`' shape: container-owned DB + `AGENTSVIEW_NO_DAEMON=1` + `--server`** | **One well-engineered example, plus a ready compose file.** Its SKILL.md; `managedkaos/agentsview-docker-compose` | Removes every host-daemon defect in Finding 8 (#1249 macOS PID reuse is still open, #1688 idle-CPU fix is unreleased). Also adopt its preflight-JSON and never-pipe-the-JSON rules. |
| 6 | **Model the report on `Lazymindz/agentsview-hermes-ops`: deterministic, threshold-driven, one recommendation, script-only** | **One dead repo, but the shape is right.** Its README | Explicit `--cost-warn` / `--retry-warn` thresholds, "attention sessions", fails soft. Copy the shape; re-derive the signals (some are its own DB computations). |
| 7 | **Steal `mrojas54/tool-benchmarks`' method for waste measurement** | **One live repo, 1 star, serious.** Its README + design doc | `--index-source auto\|raw\|agentsview`; context cost = joined payload chars/4; cursor-page past the 500-session cap; **no default parser** so an unknown schema raises instead of reporting a healthy zero. |
| 8 | **Treat `recall` as promising, not buildable-on yet** | **First-party but self-declared experimental.** `docs/recall.md` | `recall brief` is the real self-improvement primitive (distil history → brief the next task, with provenance). Upstream says the schema may need rebuilding on upgrade. Prototype, don't gate. |
| 9 | **Do NOT use `rgr4y/agentsview-mcp` or `mjacobs/agentsview-mcp`** | **Measured dead + superseded.** `gh api repos/…` | 0 stars each; last commits 2026-05-01 and 2026-06-19. Upstream ships `agentsview mcp` with six tools and citation metadata. Use the first-party server. |
| 10 | **Do not bump the pin casually** | **The manifest's own note.** `sources/agentsview.manifest` | 78 tags in 7 months; `main` 11 days ahead of v0.42.0. The release carrying PR #1677 forces a full session resync against a ~5 GB archive. |

## Premises I could NOT settle

1. **Is the `quality` rule-based recommendation set reachable headlessly?**
   `docs/quality.md` documents only the `/quality` web page. I did not exhaust
   the 75 KB `docs/commands.md` for a `quality` verb. **This decides whether a
   deterministic gate is possible without scraping a web page.** Highest-value
   open question in this report.
2. **Does v0.42.0's generated SKILL.md still carry the #1511 `--fts` defect?**
   The issue closed 2026-09-03; v0.42.0 shipped 2026-09-01. Ordering says
   probably yes. Settle by running `skills install` and reading the file.
3. **Is full bash command text retained verbatim, heredocs included?**
   `input_json` is the raw serialized input, which supports the general claim,
   but I found **no upstream statement about heredocs** — the word appears
   nowhere in the docs I fetched. The sibling KB artifact asserts it; that
   assertion is unverified and its "structured tool input/**output**" half is
   contradicted by `tool-calls` returning only `result_length`.
4. **Provenance of `agentsview-hermes-ops`' signal families** ("prompt maturity",
   "runaway loops", "context health") — native fields or its own SQLite
   computations? I did not read its script.
5. **"Built by Wes McKinney's Kenn team"** — one 3-like X post, uncorroborated.
6. **How much #1688's idle-CPU bug bites at ~3,276 sessions.** Measured at
   128,343 sessions; the pass is quadratic, so the operator's archive is ~40×
   smaller, but I did not measure it here.

## Named tools that were NOT available to me

Repeating Finding 0's table because the brief asked for it explicitly:
**`/firecrawl:firecrawl-search`, `/firecrawl:firecrawl-developer-index`,
`/exa:search`, and `/context7:docs` / `/context7:context7-mcp` are all absent
from this lane's tool pool.** Two `ToolSearch` probes returned only `WebSearch`,
`WebFetch` and the Chrome/computer-use MCP tools — which is the control arm
proving the deferred-tool index was readable. `/last30days:last30days` WAS
available and was used (Finding 9). The fallbacks were `gh` (repos, code search,
contents, issues, releases), `curl` against `agentsview.io`, and `WebSearch`.

⚠️ **Environment note for the coordinator:** the GitHub **search** quota (30/min
class) was exhausted mid-run, while the **core** quota stayed at ~4,966. Prefer
`gh api repos/...` over `gh search code` when both work.

## GitHub repos touched

- [kenn-io/agentsview](https://github.com/kenn-io/agentsview) — the subject; docs (`llms.txt`, `mcp.md`, `session-intelligence.md`, `quality.md`, `commands.md`, `session-api.md`, `recall.md`), tree, releases, tags, issues #1511/#1688/#1249/#1081/#1082/#1375/#1592/#1717/#346.
- [mrojas54/tool-benchmarks](https://github.com/mrojas54/tool-benchmarks) — the closest self-optimisation precedent; README + design doc read.
- [Lazymindz/agentsview-hermes-ops](https://github.com/Lazymindz/agentsview-hermes-ops) — scheduled deterministic ops summary; README read.
- [danbri/factoidal](https://github.com/danbri/factoidal) — `skills/session-cost-accounting/SKILL.md` read; the `--include-children` measurement.
- [durandom/fullsend-sessions](https://github.com/durandom/fullsend-sessions) — `skills/agentsview/SKILL.md` read; container + preflight design.
- [rgr4y/agentsview-mcp](https://github.com/rgr4y/agentsview-mcp) — maintenance assessed (dead); not recommended.
- [mjacobs/agentsview-mcp](https://github.com/mjacobs/agentsview-mcp) — maintenance assessed (dead); not recommended.
- [cpcloud/herdr-agentsview](https://github.com/cpcloud/herdr-agentsview) — Rust TUI; metadata + schema-drift commit.
- [franroa/chezmoi](https://github.com/franroa/chezmoi) — `tmux-context-inspector` scripts incl. `executable__recommend.sh`; health + recommendations consumer.
- [managedkaos/agentsview-docker-compose](https://github.com/managedkaos/agentsview-docker-compose) — run-as-a-service prior art.
- [akunzai/agent-skills](https://github.com/akunzai/agent-skills) — `skills/agentsview-resume/SKILL.md` (surfaced, not read in full).
- [jay-aye-see-kay/.pi](https://github.com/jay-aye-see-kay/.pi) — `agent/skills/agentsview-history/SKILL.md` (surfaced).
- [prateek/dotfiles](https://github.com/prateek/dotfiles) — `home/dot_agents/docs/agentsview.md` (surfaced).
- [MooseGooseConsulting/frozenSkillz](https://github.com/MooseGooseConsulting/frozenSkillz) — `personal-skills/chat-history` reference (surfaced).
- [colinmollenhour/dotfiles](https://github.com/colinmollenhour/dotfiles) — `colin-ultra-review` skill (surfaced).
- [radiator-engineering/eventlog](https://github.com/radiator-engineering/eventlog) — `agentsview-follow` template using `session watch` (surfaced).
- [riclib/omarchy-agentsview](https://github.com/riclib/omarchy-agentsview) · [sefk/llm-use-charts](https://github.com/sefk/llm-use-charts) · [davlion/agentsview-thinking](https://github.com/davlion/agentsview-thinking) · [ochen1/agentsview-prompts](https://github.com/ochen1/agentsview-prompts) · [calvinchengx/synapse](https://github.com/calvinchengx/synapse) · [christoph-jerolimov/agentsview-rhdh-extension](https://github.com/christoph-jerolimov/agentsview-rhdh-extension) · [statik/agentsview-rstudio-addin](https://github.com/statik/agentsview-rstudio-addin) · [zhangyimin870220/agentsview-cn](https://github.com/zhangyimin870220/agentsview-cn) · [mariusvniekerk/agentsview-docs](https://github.com/mariusvniekerk/agentsview-docs) · [cocktailpeanut/agentsview.pinokio](https://github.com/cocktailpeanut/agentsview.pinokio) · [conda-forge/agentsview-feedstock](https://github.com/conda-forge/agentsview-feedstock) · [x-cmd-install/agentsview](https://github.com/x-cmd-install/agentsview) · [managedkaos/agentsview](https://github.com/managedkaos/agentsview) — satellite inventory; metadata only.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `sources/agentsview.manifest`, `sources/REGISTRY.md`, and the two `docs/artifacts/*.html` whose tool-call premise this report settles and partly corrects.
- Not a repo, but the primary doc surface: <https://agentsview.io/guide.md> and `agentsview.io/docs/*.md`.

**END OF REPORT.**

---

## ⚠️ COORDINATOR ANNOTATION (2026-09-12, added after delivery — report above is verbatim)

Per `agent-report-persistence.md` rule 4 the report is preserved unedited; this annotation
corrects one framing that a later reader would otherwise take at face value.

**#1688's "idle daemon at 8-9 cores" does NOT describe what this pin actually does.** Measured
on this host, same commit `ff8fb4e8` / v0.42.0:

| observation | value |
|---|---|
| daemon at peak | pid 24234, **105.2% CPU**, 280 MB RSS |
| lifetime | **~15 min, then it EXITED on its own** — `daemon status` -> "No agentsview daemon is running" |
| load WITH daemon running | 20.72 / 11.57 / 12.78 |
| load with daemon **GONE** | **51.98** / 18.28 / 13.52 |

Two consequences:

1. **The daemon is TRANSIENT here, not idle-burning.** ~One core for ~15 minutes, consistent
   with initial INGEST of 3,276 sessions (matching the report's own ">120s first run" and
   #1688's "quadratic in archive size"), then self-termination. So the cost is a **one-time
   ingest, re-paid as the archive grows** — a real but much weaker argument against an
   auto-start hook than "8-9 cores while idle".
2. ⚠️ **The coordinator originally cited load 20.72 as evidence of #1688 and that attribution
   was WRONG** — load with agentsview entirely absent is 51.98. The load was this session's own
   concurrent subagent lanes. One process at 105% cannot produce a load of 20. All three inputs
   (105% CPU, load 20.72, #1688 naming our commit) were individually TRUE; the causal claim
   joining them was never tested, and the test was arithmetic. See
   `verify-before-advancing.md` — *carry a number with its CONDITION, not just its source*.

**What the report gets right and still binds:** #1688, #1249 and #1081/#1082 are genuinely
open-or-unreleased at this pin, and #1249's precondition is real and present — **the exit leaves
`~/.agentsview/daemon.lock` behind**. Any auto-start hook must check for a stale lock FIRST,
because starting into one is precisely how #1249's unrecoverable wedge is triggered.

Nothing else in the report rested on the daemon framing: the first-party loop at
`agentsview.io/guide.md` stop 08, the dual-harness `skills install` generator and its
`missing|current|stale|modified|foreign` currency gate, #1511's silent 0-vs-19 recipe defect,
`--include-children` being mandatory for a multi-lane repo, `started_at` over `created_at`, the
dead third-party MCP repos, and the control-armed "nobody closes the loop" all stand unchanged.
