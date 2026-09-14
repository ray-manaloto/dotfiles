# goalrev telemetry sweep — 2026-09-13

Agent: telemetry-research (read-only). Repo `dotfiles` @ `feat/enable-research-plugins`, 5f96509.

## Coverage caveat — read this before any of the numbers below

`.agent/telemetry/` holds **527 files**: 266 `*.request.json` (UUID-named) +
261 `*.response.json` (`req_<id>`-named, one response per request but not
1:1 filename-matched — response count is the analysis unit below). File
mtimes span **2026-08-26 23:56:xx through 2026-08-29 12:39:xx — under 3
calendar days**, verified by `ls -lt`. That is a narrow slice against the
project's much longer session history (MEMORY.md alone documents sessions
from 2026-09-01 through 2026-09-13, none of which appear in this telemetry
corpus at all — telemetry writing evidently stopped or was reconfigured
after 2026-08-29). **Every number in this report describes those ~3 days
only.** Nothing here should be read as "this project's total effort" or
extrapolated to a per-session average without re-deriving the number of
sessions those 3 days actually contained (not established here — the
telemetry files carry no session id field).

Command: `ls -lt .agent/telemetry/*.response.json | head -3` / `tail -3`.

## 1. Model mix and spend (261 response records)

Command:
```
jq -s 'group_by(.model) | map({model:.[0].model, count:length,
  input_tokens:(map(.usage.input_tokens//0)|add),
  output_tokens:(map(.usage.output_tokens//0)|add),
  cache_creation:(map(.usage.cache_creation_input_tokens//0)|add),
  cache_read:(map(.usage.cache_read_input_tokens//0)|add),
  thinking_tokens:(map(.usage.output_tokens_details.thinking_tokens//0)|add)})' \
  *.response.json
```

| model | turns | fresh input | output | cache_creation | cache_read | thinking |
|---|---:|---:|---:|---:|---:|---:|
| claude-sonnet-5 | 147 | 3,398 | 73,926 | 2,299,413 | 85,986,622 | 22,439 |
| claude-opus-5 | 112 | 2,324 | 80,659 | 299,926 | 23,492,895 | 37,410 |
| claude-haiku-4-5-20251001 | 2 | 2,004 | 35 | 0 | 0 | 0 |
| **total** | **261** | **7,726** | **154,620** | **2,599,339** | **109,479,517** | **59,849** |

Top spender by turn count and by cache-read volume in this window: **Sonnet 5**
(56% of turns, 78.5% of cache-read tokens). Opus 5 accounts for 62.5% of
thinking tokens despite fewer turns — its turns think harder on average.
Haiku is negligible (2 turns) — not a meaningful presence in this window.

## 2. Cache efficiency

Overall ratio `cache_read / (cache_read + cache_creation + fresh_input)` =
**109,479,517 / 112,086,582 = 97.7%** — healthy on average; almost all
context in this window was served from cache, not rebuilt.

**Where it collapses:** sorting all 261 turns by `cache_creation_input_tokens`
descending (`jq -r '[.model,(.usage.cache_creation_input_tokens//0),
(.usage.cache_read_input_tokens//0),.id]|@tsv' *.response.json | sort -k2 -rn`),
**4 of 261 turns account for 77.2% of ALL cache-creation tokens in the window**
(2,006,376 of 2,599,339 total), each with `cache_read_input_tokens: 0` — a
total cold-cache miss, not a partial one:

| cache_creation | cache_read | output | file | timestamp |
|---:|---:|---:|---|---|
| 680,740 | 0 | 139 | req_011CeXQ88FCuVdVTJDigpfr8 | 2026-08-29 12:02:17 |
| 504,880 | 40,644 | 703 | req_011CeXKmDyCKKcoDdyxabx5o | 2026-08-29 11:05:07 |
| 410,782 | 0 | 217 | req_011CeXHqAWDYqyB8QdJeFgkW | 2026-08-29 10:39:40 |
| 409,974 | 0 | 203 | req_011CeXHpDDQNCMR36EtWcxrR | 2026-08-29 10:39:26 |

All four are `claude-sonnet-5`, all inside one ~85-minute window on
2026-08-29 morning. **Root cause is directly recorded by the API itself**,
not inferred: 6 of the 261 responses carry a `diagnostics.cache_miss_reason`
field, and the four largest collapses (plus two smaller ones) all show
`"type": "tools_changed"` — one shows `"system_changed"`. Command:
```
jq -c 'select(.diagnostics!=null) | {id, cache_miss: .diagnostics.cache_miss_reason,
  cache_creation: .usage.cache_creation_input_tokens, cache_read: .usage.cache_read_input_tokens}' \
  *.response.json
```
This is the signature of the tool schema changing between turns — consistent
with fresh subagent/fork launches (each starts a new context with a
different tool set than its parent) or `ToolSearch`'s deferred/on-demand tool
loading changing which tool schemas are present turn to turn. Either way,
**every tool-set change in this window paid for a full context rebuild at
roughly the cost of the whole rest of the session's cache-creation combined.**

Control arm for "no truncated turns": `stop_reason` values across all 261
records are `tool_use` (222) and `end_turn` (39) only — 0 occurrences of
`max_tokens`/`refusal`/`stop_sequence`-driven truncation (`jq -r .stop_reason
*.response.json | sort | uniq -c`, confirmed no other value exists and no
`max_tokens` string appears at all).

## 3. Waste signature — command-audit.md (50 sessions, 19,226 Bash commands)

Per `mise-tasks-only.md`: **`bypass` = 0.** No command evaded a live guard
rule in this window. That is the only alarm-worthy class, and it is clean.

Raw class counts (not alarms — reported for completeness, per the brief's
own instruction not to treat these as alarms):

| class | count | meaning |
|---|---:|---|
| bypass | 0 | real evasion — **the only alarm class** |
| blocked | 64 | guard denied it (working as intended) |
| pre_rule | 0 | matched a rule that postdates the command |
| one_off | 4,363 | mutating hand-run, candidate for a mise task |
| mise | 965 | already routed through a mise task/CLI |
| diagnostic | 13,834 | read-only, legitimately direct |

The genuine signal here is **one_off = 4,363 (22.7% of all 19,226 commands)**
— hand-rolled shapes that recur often enough to be a real "package this as a
task" backlog, not evidence of guard evasion. Top recurring shapes (from the
report's own "One-off culprits" table):

| count | shape |
|---:|---|
| 767 | `mkdir -p` (mostly `mkdir -p docs/research/... && cat > ...` — ad hoc report scaffolding) |
| 546 | `python3 -` (heredoc scripts) |
| 217 | `while [` (hand-rolled polling loops — the exact anti-pattern `gh-cli-watch.md` and `long-running-command-hangs.md` warn against) |
| 205 | `python3 -c` |
| 176 | `uv run` (ad hoc python one-liners, not via a task) |
| 137 / 24 / 13 / 11 | `"$RL" wait` / the full fable-orchestrator `run-lane.sh` path / `"$RL" reap` / `"$RL" start` — hand-invoked lane-runner script instead of a wrapping task |
| 64 | `guard denial: gate command piped to head/tail` (§blocked, working as intended) |

`guard fail-open` count in the same report: **159**, almost all
(`guard-error-rc=1`, 158 of 159) — the guard erroring out and failing open
rather than a missing interpreter. That is a real, quantified gap in the
"only bypass is an alarm" model: a fail-open is not a bypass by the report's
own taxonomy, but it is 159 windows where the guard provided zero
enforcement. Not investigated further here (out of scope for this lane —
flagging it as a candidate finding for whichever lane owns `#343`).

## 4. `instructions-loaded` — are eager rules actually loading?

50 session `.jsonl` files (`.agent/instructions-loaded/`), matching the 50
sessions in `command-audit.md`.

**All 26 files in `.claude/rules/*.md` appear at least once** across the 50
sessions (`comm -23` of the full rule-basename list against the
loaded-rule-basename list = empty). Control arm: injecting a synthetic
`bogus-rule-zzqrx7.md` into the "all rules" list and re-running the same
`comm -23` correctly reports it as never-loaded — the diff logic
discriminates, so the empty result for the real 26 is not an artifact of a
broken probe.

Load counts range from **58** (`md-size-budgets.md`, loaded more than once
per session on average — consistent with it firing per markdown edit, not
just at session start) down to **28** (`ci-local-parity.md`, of 50 sessions)
— every eager rule loads in the majority of sessions, none is silently dead.
`load_reason` breakdown: 1,251 `session_start`, 433 `nested_traversal`, 425
`include`, 86 `path_glob_match`, 26 `compact`.

Command:
```
cat .agent/instructions-loaded/*.jsonl | jq -r 'select(.file_path|startswith(".claude/rules/")).file_path' \
  | sort | uniq -c | sort -rn
```

## What I measured vs. what I inferred

**Measured directly:** the model/token totals (§1), the cache-read ratio and
the 4 cold-cache turns with their API-reported `cache_miss_reason` (§2), the
`bypass=0` / `one_off=4363` counts and shapes verbatim from
`command-audit.md` (§3), and the full-coverage eager-rule load counts (§4).

**Inferred, not measured:** that the 4 cold-cache turns correspond to
subagent/fork launches specifically (plausible from the `tools_changed`
reason and the clustering in one 85-minute window, but the telemetry has no
field naming the caller — could equally be `/clear` or a model/tool-version
transition); that 4,363 one-offs represent avoidable future cost (they are a
backlog signal, not a proven regression, since `mise-tasks-only.md` treats
non-bypass one-offs as noise by design).

## Candidate `/goal` statements, ranked

1. **(Recommended) Package the highest-frequency one-off shapes as mise
   tasks, starting with the 217 hand-rolled `while [` polling loops.**
   Evidence: §3 — `while [` polling is the exact anti-pattern
   `gh-cli-watch.md`/`long-running-command-hangs.md` already ban, yet it is
   the 3rd most common one-off shape at 217 occurrences across only 50
   sessions. It's also the one-off class most likely to hide a real
   `verify-before-advancing.md` violation (masked exit code via `tail`/loop
   exit). **Counter-argument:** `bypass=0` says the guard already prevents
   the dangerous variants (piped-to-tail, backgrounded); the remaining 217
   may just be the harness-sanctioned in-turn-poll idiom
   (`long-running-command-hangs.md` rule 2's own recommended pattern) counted
   as "one_off" because it isn't wrapped in a mise task — i.e., not a defect,
   just an un-canonicalized-but-correct idiom.

2. **Investigate whether `ToolSearch`/subagent tool-set churn is the real
   driver of the 77%-cache-creation-concentration finding, and whether it
   recurs after 2026-08-29 (telemetry gap prevents saying either way).**
   Evidence: §2 — a mechanism this concentrated (4 of 261 turns = 77% of
   cache-creation cost) is worth knowing whether it is one-time (a session
   restart) or systemic (every subagent launch pays it). **Counter-argument:**
   the telemetry corpus is 3 days old and untouched since; without live data
   past 2026-08-29 this cannot be measured further today, only reasoned about
   — a `/goal` built on stale telemetry risks solving a problem that current
   sessions no longer exhibit (or exhibit worse, unmeasured).

3. **Restore/extend telemetry capture past 2026-08-29 before drawing any
   further conclusions from `.agent/telemetry/`.** Evidence: the coverage
   caveat itself — 15 days of session history (per MEMORY.md, 2026-09-01
   through 2026-09-13) have zero telemetry records, so every future
   "where did effort go" question is currently unanswerable from this
   corpus. **Counter-argument:** this is process/tooling work, not a
   user-facing improvement, and may not be what `/goal` is meant to capture
   for this session — it could be filed as an issue instead of consuming a
   full session goal.

4. **Audit and fix the 159 guard fail-opens (158 of them `guard-error-rc=1`)
   in the PreToolUse hook.** Evidence: §3 — this is a real, quantified,
   currently-untracked-here gap in an enforcement layer the project relies
   on (`mise-tasks-only.md`, issue #343 already tracks the general fail-open
   class). **Counter-argument:** this data is 3 days stale (same caveat as
   #2/#3) and #343 may already be the tracked home for this; duplicating it
   as a `/goal` risks working from a superseded snapshot rather than the
   current guard-error rate.

## GitHub repos touched

_None._
