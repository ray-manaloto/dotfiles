# wf-dag-codex-lane — Codex executor lane: limits, inspection, failure signals, verdict contract

**Status:** COMPLETE (written incrementally per `.claude/rules/agent-report-persistence.md`)
**Date:** 2026-08-05
**Harness:** `claude --version` → `2.1.222 (Claude Code)`
**Codex:** `codex --version` → `codex-cli 0.146.0`, path
`/Users/rmanaloto/.local/share/mise/installs/codex/0.146.0/bin/codex` (Mach-O arm64)

Scope: facts that bound the Codex second-vendor executor lane in the autonomous DAG
framework (`docs/agent-team.md`). Five questions: (1) ChatGPT Pro limits, (2)
programmatic budget inspection, (3) exhaustion failure signal, (4) prior-art typed
verdict-file contract, (5) wrapper-tax measurement.

**Method note — every number is dated, and inherited numbers are labelled.**
Per `probes-need-a-control-arm.md` rule 6, figures carried in from
`lane-economics.md` are marked **[INHERITED]** and were NOT re-measured unless
stated. Figures I measured this session are marked **[MEASURED 2026-08-05]**.

---

## 0. ⚠️ Probe hazard discovered first — `codex <unknown-subcommand> --help` exits 0

**[MEASURED 2026-08-05] CONFIRMED.** `codex` forwards unknown leading tokens to the
interactive CLI, so an absent subcommand does **not** produce a non-zero rc:

| Probe | rc | stdout |
|---|---|---|
| `codex usage --help` | **0** | top-level `Codex CLI` help |
| `codex status --help` | **0** | top-level help |
| `codex limits --help` | **0** | top-level help |
| `codex account --help` | **0** | top-level help |
| **control:** `codex exec --help` | 0 | `Run Codex non-interactively` + exec-specific flags |
| **control:** `codex login --help` | 0 | `Manage login` + `status` subcommand |

The probe discriminates only on **stdout content**, never on rc. Anyone writing a
"does codex support X" check must compare the first line of output, not the exit
code. `codex --help`'s `Commands:` block is the authoritative list:
`exec, review, login, logout, mcp, plugin, mcp-server, app-server, remote-control,
app, completion, update, doctor, sandbox, debug, apply, resume, archive, delete,
unarchive, fork, cloud, exec-server, features, help`. **There is no `usage`,
`status`, `limits` or `account` top-level subcommand in 0.146.0.**

---

## 1. Rate limits / usage windows on ChatGPT Pro

### 1.1 What the account is — [INHERITED from `lane-economics.md` §3, measured 2026-08-04]

`~/.codex/auth.json` → `auth_mode = chatgpt`; `id_token` claim
`https://api.openai.com/auth.chatgpt_plan_type` = **`pro`**; `OPENAI_API_KEY`
absent from both `auth.json` and the shell env. Re-confirmed cheaply this session:
`codex login status` → **`Logged in using ChatGPT`** (rc=0)
**[MEASURED 2026-08-05]**. So Codex here consumes *subscription* quota, not metered
API credits — Codex-side spend draws **nothing** from the Claude weekly window.

### 1.2 OpenAI's published numbers — RE-DERIVED 2026-08-05, table unchanged

`lane-economics.md` §5b fetched <https://learn.chatgpt.com/docs/pricing> on
**2026-08-04**. Per `probes-need-a-control-arm.md` rule 6 I did **not** repeat the
number on trust — **I re-fetched the same page on 2026-08-05 and the table is
byte-equivalent**, so this is a measurement, not an inherited figure:

> "The usage limits for local messages and cloud chats share a **five-hour
> window**. Additional weekly limits may apply."

| Plan | GPT-5.6 Sol | GPT-5.6 Terra | GPT-5.6 Luna |
|---|---|---|---|
| Plus | 10–100 msgs / 5h | 25–200 | 250–2,000 |
| **Pro 5x** | **50–500** | 125–1,000 | 1,250–10,000 |
| **Pro 20x** | **200–2,000** | 500–4,000 | 5,000–40,000 |
| Business | 10–100 | 25–200 | 250–2,000 |

Beyond the allowance, "available credits let you continue working" — the overflow
path is metered even on a subscription. **These are PUBLISHED numbers, re-derived
2026-08-05, and they are ranges, not guarantees.** A range that spans 10×
("50–500") cannot be scheduled against directly; only the *observed* `usedPercent`
(§2) can.

**New fact from the 2026-08-05 re-fetch, not in `lane-economics.md`** — verbatim:

> "We want you to be able to complete work already in progress. If you reach your
> usage limits during an active turn, the agent will be able to continue working on
> that turn, subject to fair use limits."

**Scheduler consequence:** exhaustion does not necessarily kill the *in-flight*
turn. So a DAG node that is already running when the window closes may still land
its diff — the failure surfaces on the *next* dispatch. The governor must therefore
gate **dispatch**, and must not interpret "budget hit" as "the running node is
doomed".

### 1.2b Practitioner reports — ANECDOTAL, and one claim is uncorroborated

Separated deliberately from §1.2. All of the below are **secondary sources** found
by web search on 2026-08-05; none is a primary OpenAI statement.

| Claim | Source class | Verdict |
|---|---|---|
| "5-hour rolling window plus a weekly cap that stacks on top; the 5-hour one is what people hit first" | SEO/blog aggregators (morphllm, simplemetrics, ofox) | **SUSPECT but consistent** with the primary page's "five-hour window … additional weekly limits may apply" |
| A single long refactor can drain a **weekly** limit in ~3 hours on the $20 Plus plan | blog anecdote, undated in the excerpt | **ANECDOTAL** — plausible and directionally important (one job can eat a window), unusable as a number |
| A user hit the cap at "78% 5-hour remaining and 68% weekly remaining" — i.e. one long agent run collapsed both windows at once | blog anecdote | **ANECDOTAL**; if true it implies `usedPercent` can jump discontinuously, so a headroom gate needs a wide margin, not a 5% threshold |
| **OpenAI temporarily REMOVED the 5-hour limit on 2026-07-12, then restored it ~2026-07-30** | eesel.ai / explainx.ai blogs | ⚠️ **UNCORROBORATED — do not act on it.** The primary pricing page re-fetched **2026-08-05** still states the five-hour window and contains **no** removal/restoration language. Per the "source beats secondary artifact" habit, the primary page is authoritative and the claim is at best stale |

**What survives as design input:** the *shape* of the anecdotes (one long agent run
can consume a large fraction of a window) matters more than any figure. It argues
for per-node budget accounting and a conservative headroom threshold, which is what
§2's `usedPercent` gate provides.

### 1.3 The binary knows about MORE windows than the pricing page names — [MEASURED 2026-08-05] CONFIRMED

`strings` over the 0.146.0 binary yields the status-line placeholder catalogue:

```
Remaining usage on the 5-hour usage limit      (id: usage-limit)
Remaining usage on the daily usage limit       (id: daily-limit)
Remaining usage on the weekly usage limit      (id: weekly-limit)
Remaining usage on the monthly usage limit     (id: monthly-limit)
Remaining usage on the annual usage limit      (id: annual-limit)
Remaining usage on the primary usage limit
Remaining usage on the secondary usage limit   (id: secondary-usage-limit)
```

Control arm: fresh known-absent token `zzqvvkbb` → **0 hits**; `rate_limit` → 80,
`usage_limit` → 33, `"usage limit"` → 20, `"rate limit"` → 24. The probe
discriminates.

**Implication for a scheduler:** the enforcement surface is not just "5h + weekly".
The client models **five** named windows plus a primary/secondary pair, and the
wire protocol (§2) carries an arbitrary `windowDurationMins` — so a scheduler must
read the window duration from the payload, never hard-code 300 minutes.

### 1.4 Pro 5x vs Pro 20x — still UNVERIFIED, and now known NOT to be in `planType`

**[MEASURED 2026-08-05] REFUTED (as a discriminator).** The app-server protocol's
`PlanType` enum is exhaustively:

```
free, go, plus, pro, prolite, team, self_serve_business_usage_based,
business, ent26, enterprise_cbp_usage_based, enterprise, edu, unknown
```

There is **no `pro_5x` / `pro_20x` member**. So neither the `id_token` claim
(`lane-economics.md` §3) nor the protocol's `planType` field can tell the two Pro
tiers apart — the 4× headroom difference is invisible to any programmatic probe of
plan identity. It is only observable through `usedPercent` movement per message, or
out-of-band at `chatgpt.com/codex/settings/usage`.

**Consequence for the DAG design: do not build routing on a static per-plan message
budget.** Build it on the *observed* `usedPercent` / `resetsAt` telemetry, which is
tier-agnostic.

---

## 2. Programmatic inspection of remaining Codex budget — CONFIRMED, and richer than expected

Three read-only surfaces exist in 0.146.0. **None of them requires running a
`codex exec` job.**

### 2.1 The authoritative artifact: the app-server JSON-Schema bundle

`codex app-server generate-json-schema --out <DIR>` (rc=0, **[MEASURED
2026-08-05]**) writes 40 files including
`codex_app_server_protocol.v2.schemas.json` (498 KB). This is the *binary's own*
protocol description — the strongest corpus tier available for Codex, the analogue
of the three-corpus rule for Claude Code. It is generated offline, costs no quota,
and needs no network.

> Note it takes `--out <DIR>` and **errors rc=2 without it** — the one place in this
> investigation where a wrong invocation *does* fail loudly.

### 2.2 The methods — `account/rateLimits/read` and `account/usage/read`

Enumerated from `ClientRequest.json` (regex over method enums; control arm:
`thread/*` methods enumerate 8+, fresh-absent token `vqxmzz9/` → 0):

```
account/login/start           account/rateLimits/read
account/login/cancel          account/rateLimitResetCredit/consume
account/logout                account/usage/read
account/read                  account/workspaceMessages/read
account/sendAddCreditsNudgeEmail
```

`account/rateLimits/read` takes **`params: null`** — a bare JSON-RPC request over
the app-server's stdio transport. Transport options: `codex app-server` (stdio),
`codex app-server proxy` (proxies stdio to a running daemon's control socket), or
`codex debug app-server send-message-v2`.

### 2.3 The payload shape (verbatim from the generated v2 schema)

`GetAccountRateLimitsResponse`:

| Field | Type | Notes |
|---|---|---|
| `rateLimits` (required) | `RateLimitSnapshot` | "Backward-compatible single-bucket view; mirrors the historical payload." |
| `rateLimitsByLimitId` | `{[limitId]: RateLimitSnapshot}` \| null | "Multi-bucket view keyed by metered `limit_id` (for example, `codex`)." |
| `rateLimitResetCredits` | `RateLimitResetCreditsSummary` \| null | `availableCount` + optional `credits[]` |

`RateLimitSnapshot`: `primary`, `secondary` (each a `RateLimitWindow`|null),
`credits` (`CreditsSnapshot`|null), `individualLimit`
(`SpendControlLimitSnapshot`|null), `limitId`, `limitName`, `planType`,
`rateLimitReachedType`, `spendControlReached` (bool|null — *"`None` is unavailable,
not a sparse-update recovery"*).

`RateLimitWindow` — **the number a scheduler actually wants**:

```json
{ "usedPercent": <int32, REQUIRED>,
  "windowDurationMins": <int64|null>,
  "resetsAt": <int64|null, unix seconds> }
```

`CreditsSnapshot`: `hasCredits` (bool, req), `unlimited` (bool, req), `balance`
(string|null). `SpendControlLimitSnapshot`: `limit`, `used`, `remainingPercent`,
`resetsAt` — all required.

`account/usage/read` → `GetAccountTokenUsageResponse`: `summary`
(`AccountTokenUsageSummary`: `lifetimeTokens`, `peakDailyTokens`,
`currentStreakDays`, `longestStreakDays`, `longestRunningTurnSec` — all nullable)
plus `dailyUsageBuckets[]` of `{startDate: string, tokens: int64}`.

### 2.4 Push, not just pull — `AccountRateLimitsUpdatedNotification`

The server *pushes* rolling updates. Verbatim from the schema description:

> "Sparse rolling rate-limit update. Clients should merge available values into the
> most recent `account/rateLimits/read` response or refetch that snapshot. Nullable
> account metadata may be unavailable in a rolling update and does not clear a
> previously observed value."

**Design consequence:** a long-lived scheduler should hold a snapshot and merge
sparse updates — and must treat a `null` in an update as "unknown", never as
"cleared". Getting that backwards would silently zero out a live budget reading.

### 2.5 ⚠️ CORRECTED — `codex exec --json` carries **no** rate-limit telemetry

**My first inference here was WRONG, and a cross-check caught it.** Binary strings
showed `struct TokenCountEvent with 2 elements` = `{info, rate_limits}`, and I
initially concluded the exec JSONL stream carries budget telemetry for free. A
second route — the upstream source — **REFUTES** that:

- `codex-rs/protocol/src/protocol.rs:2154-2157` — `TokenCountEvent { info:
  Option<TokenUsageInfo>, rate_limits: Option<RateLimitSnapshot> }`. The struct is
  real, but it belongs to the **core/app-server** protocol.
- `codex-rs/exec/src/exec_events.rs` — the exec JSONL surface. Its event enum is
  exactly `thread.started`, `turn.started`, `turn.completed`, `turn.failed`,
  `item.started`, `item.updated`, `item.completed`, `error`.
  `TurnCompletedEvent { usage: Usage }` where `Usage` is **token counts only**
  (`input_tokens`, `cached_input_tokens`, `cache_write_input_tokens`,
  `output_tokens`, `reasoning_output_tokens`). **No `rate_limits` field anywhere.**
  Control arm: `grep -ci rate` → 1 (a comment, line 266), `grep -ci usage` → 3,
  fresh-absent `xqvbz42` → 0 — the probe discriminates.
- `codex-rs/exec/src/event_processor_with_jsonl_output.rs` only ever consumes
  `ServerNotification::ThreadTokenUsageUpdated` to populate that `Usage`; it never
  reads `AccountRateLimitsUpdated`. The human-output processor mentions rate limits
  **zero** times.

**CONFIRMED (REFUTING the earlier inference): a `codex exec` run tells you nothing
about remaining budget.** A scheduler that wants budget must query
`account/rateLimits/read` over the app-server out-of-band (§2.2), on its own
cadence. This is the single most load-bearing correction in this report — building
the DAG's budget governor on a `codex exec --json` field that does not exist would
have failed silently (the field would simply always be absent).

_Generalisation worth keeping: binary `strings` proves a symbol EXISTS in the
binary; it says nothing about WHICH protocol surface exposes it._

### 2.6 The interactive-only surfaces (for a human, not a scheduler)

TUI slash commands, from the binary's command catalogue:

- `/status` — *"show current session configuration and token usage"*
- `/usage` — *"view account usage or use a usage limit reset"*; its menu offers
  *"Show usage"*, *"Redeem usage limit reset"*, *"Full reset — Reset your current
  usage limits. Does not expire."*

These are TUI-only. The `account/rateLimitResetCredit/consume` method is the
programmatic equivalent of redeeming a reset — **a mutating call; a scheduler must
not fire it without a human decision.**

---

## 3. The exhaustion failure signal — what a scheduler can actually detect

All of §3 is **CONFIRMED from upstream source** at `openai/codex` `main`
(104,045 stars, `pushed_at` 2026-08-05T08:26:01Z, fetched 2026-08-05 via `gh api`).

### 3.1 Exit code: **1, generic. There is no distinct exhaustion exit code.**

`codex-rs/exec/src/lib.rs:961-1063` — the entire exec session tracks one boolean:

```rust
let mut error_seen = false;
…
if let ServerNotification::Error(payload) = &notification {
    if payload.thread_id == … && payload.turn_id == task_id && !payload.will_retry {
        error_seen = true;
    }
} else if let ServerNotification::TurnCompleted(payload) = &notification
    && matches!(payload.turn.status, TurnStatus::Failed | TurnStatus::Interrupted)
{ error_seen = true; }
…
event_processor.print_final_output();
if error_seen { std::process::exit(1); }
```

Every other `std::process::exit` in that file is also **1** (bad `-c` override,
missing codex home, exec-policy load failure, login restriction, untrusted
directory, unreadable/invalid `--output-schema`, missing stdin prompt). So:

> **`codex exec` exit code 1 means "something went wrong". It does NOT mean "out of
> quota". A scheduler cannot distinguish exhaustion from a compile error, a bad
> flag, or a sandbox denial by exit code alone.**

Two subtleties worth encoding in the framework:

1. **`will_retry` gates the failure.** An `Error` notification with
   `willRetry: true` does **not** set `error_seen` — Codex retries internally and
   the run may still exit 0. So transient 429s are absorbed; only a terminal error
   surfaces. Good for us: exit 1 on a usage limit means *really* exhausted, not a
   blip.
2. **`Interrupted` also yields exit 1**, so a killed/timed-out run is
   indistinguishable from a failed one by rc.

### 3.2 The discriminating signal is the **message string** — exact texts

`codex-rs/protocol/src/error.rs:622-760`. `UsageLimitReachedError` carries
`{plan_type, resets_at, rate_limits, promo_message, rate_limit_reached_type}` and
its `Display` impl produces, **in this priority order**:

| Condition | Exact message (verbatim from source) |
|---|---|
| `rate_limits.limit_name` set and ≠ `"codex"` | `You've hit your usage limit for {limit_name}. Switch to another model now,{suffix}` |
| `WorkspaceOwnerCreditsDepleted` | `Your workspace is out of credits. Add credits to continue.` |
| `WorkspaceMemberCreditsDepleted` | `Your workspace is out of credits. Ask your workspace owner to refill in order to continue.` |
| `WorkspaceOwnerUsageLimitReached` | `You hit your spend cap set in your workspace. Increase your spend cap to continue.` |
| `WorkspaceMemberUsageLimitReached` | `You hit your spend cap set by the owner of your workspace. Ask an owner to increase your spend cap to continue.` |
| `promo_message` present | `You've hit your usage limit. {promo_message},{suffix}` |
| plan = **Pro / ProLite** ← **this machine** | `You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage to purchase more credits{suffix}` |
| plan = Plus | `You've hit your usage limit. Upgrade to Pro (https://chatgpt.com/explore/pro), visit https://chatgpt.com/codex/settings/usage to purchase more credits{suffix}` |
| plan = Free / Go | `You've hit your usage limit. Upgrade to Plus to continue using Codex (https://chatgpt.com/explore/plus),{suffix}` |
| plan = Team/Business/Ent* | `You've hit your usage limit. To get more access now, send a request to your admin{suffix}` |
| plan = Enterprise/Edu/Unknown/None | `You've hit your usage limit.{suffix}` |

Suffix helpers (`:731-747`):

- `retry_suffix_after_or` → `" or try again at {ts}."` / `" or try again later."`
- `retry_suffix` → `" Try again at {ts}."` / `" Try again later."`

**The one string every variant shares is the case-sensitive prefix
`You've hit your usage limit`** (note the typographic-vs-ASCII apostrophe: the
source uses a plain `'`). Two spend-cap variants (`You hit your spend cap …`) and
two credit variants (`Your workspace is out of credits …`) do **not** contain it —
so a detector matching only that prefix misses 4 of 11 shapes. A robust matcher
is the union: `You've hit your usage limit` OR `out of credits` OR `spend cap`.

Also present in the binary but from the API layer:
`Usage limit reached. You've reached your usage limit. Increase your limits to
continue using codex.` and `You're out of credits.` — treat the detector as a
**set of substrings**, not one regex.

### 3.3 ⚠️ The reset timestamp is rendered in LOCAL time, human format — do not parse it

`format_retry_timestamp` (`:749-760`) converts `resets_at` to the **local**
timezone and formats it as either `%-I:%M %p` (**when the reset is today — no date
at all**) or `%b %-d{st|nd|rd|th}, %Y %-I:%M %p`. There is no timezone marker and
no ISO form.

**Design consequence:** a scheduler must NOT parse the reset time out of the error
text. Get `resetsAt` (unix seconds, int64) from `account/rateLimits/read` →
`RateLimitWindow.resetsAt` instead. The text is for humans.

### 3.4 The typed error code exists — but only on the app-server surface

`CodexErrorInfo` (v2 protocol, schema description verbatim: *"This translation
layer make sure that we expose codex error code in camel case. When an upstream
HTTP status is available … it is forwarded in `httpStatusCode`"*):

```
contextWindowExceeded | sessionBudgetExceeded | usageLimitExceeded | serverOverloaded
| cyberPolicy | internalServerError | unauthorized | badRequest
| threadRollbackFailed | sandboxError | other
+ object variants: httpConnectionFailed{httpStatusCode}
                   responseStreamConnectionFailed{httpStatusCode}
                   responseStreamDisconnected{httpStatusCode}
                   responseTooManyFailedAttempts{…}
```

`ErrorNotification { error: TurnError, threadId, turnId, willRetry }`, and
`TurnError { message (req), codexErrorInfo (nullable), additionalDetails }`.

The internal (core) snake_case enum is wider — from binary strings:
`usage_limit_reached, server_overloaded, cyber_policy, response_stream_failed,
connection_failed, quota_exceeded, usage_not_included, internal_server_error,
retry_limit, internal_agent_died, sandbox,
landlock_sandbox_executable_not_provided, unsupported_operation,
refresh_token_failed, fatal, io, tokio_join, env_var`. Control arm: those tokens
appear **0** times in the generated app-server schema bundle while
`rate_limit_reached` appears 5 and fresh-absent `kmqzvv31` 0 — so the two enums
really are different surfaces, not a spelling artefact.

⚠️ **But `codex exec --json` does not expose `codexErrorInfo`.**
`exec_events.rs` defines `ThreadErrorEvent { message: String }` and
`ErrorItem { message: String }` — **a bare string, no code**. So the typed
`usageLimitExceeded` value is reachable only by driving the app-server directly,
not by running `codex exec`.

### 3.5 The scheduler's detection contract, stated

| Route | Cost | Signal quality |
|---|---|---|
| `codex exec` rc | free | rc=1, **undiscriminating** |
| `codex exec --json` → `turn.failed` / `error` → `.error.message` | free | substring match; brittle across releases but the only in-band signal |
| `codex exec` stderr | free | same strings, human-formatted |
| app-server `account/rateLimits/read` **before** dispatch | one RPC, no model call | typed `usedPercent` + `resetsAt` — **pre-emptive, the right primitive** |
| app-server run → `ErrorNotification.error.codexErrorInfo == "usageLimitExceeded"` + `willRetry` | requires driving app-server instead of `codex exec` | typed, exact |

**Recommendation for the DAG:** gate dispatch on a pre-flight
`account/rateLimits/read` (cheap, typed, no quota) and treat the exec-side
substring match as a *backstop* for the race between check and dispatch. Do not
build the primary detector on rc or on message text.

---

## 4. The typed verdict-file contract — prior art, read in full, plus what it misses

Built on `fw-alpha-frameworks.md` (OMC section) and `lane-economics.md` §1–2.
`fw-alpha` cited `cli-worker-contract.ts:1-46` at OMC **4.15.6**; the local plugin
cache also has **4.15.7**, and I read that version end-to-end (201 lines) **plus its
consumer** `runtime-v2.ts:2990-3130`, which `fw-alpha` did not cover. Path:
`~/.claude/plugins/cache/omc/oh-my-claudecode/4.15.7/src/team/cli-worker-contract.ts`.
The plugin is disabled in this repo; the cache is source, read-only.

### 4.1 The payload (verbatim, 4.15.7 — unchanged from `fw-alpha`'s 4.15.6 reading)

```ts
export type CliWorkerVerdict = 'approve' | 'revise' | 'reject';
export type CliWorkerFindingSeverity = 'critical' | 'major' | 'minor' | 'nit';
export interface CliWorkerFinding { severity; message: string; file?: string; line?: number }
export interface CliWorkerOutputPayload {
  role: CanonicalTeamRole; task_id: string; verdict: CliWorkerVerdict;
  summary: string; findings: CliWorkerFinding[];
}
```

`CONTRACT_ROLES = {critic, code-reviewer, security-reviewer, test-engineer}`.
Path convention, single-sourced so spawn and reap agree (`:193-200`):
`{teamStateRoot}/workers/{workerName}/verdict.json`.

### 4.2 What `fw-alpha` did not extract — the four mechanisms that make it work

These are the reusable parts, and they are in the **consumer**, not the type file.

1. **Liveness gate before reading** (`runtime-v2.ts:3047-3048`): the verdict is only
   read once `getWorkerPaneLiveness(worker.pane_id) === 'dead'`. A file present
   while the worker still runs is ignored — no half-written-JSON race.
2. **Compare-and-swap under a file lock** (`:3109-3114`): inside
   `withFileLockSync(taskPath + '.lock')` it re-reads the task and **bails unless
   `status === 'in_progress' && owner === worker.name`**. The stated reason
   (`:3016-3019`) is that *"the worker process is gone and cannot re-enter
   `transitionTaskStatus` with its claim token"* — the leader writes the terminal
   status on the dead worker's behalf, so it must re-verify ownership itself.
3. **Idempotency by rename** (`:3020-3021`): `verdict.json` →
   `verdict.processed.json` so a later monitor cycle cannot reprocess it.
4. **A typed result enum for the reap itself**: `file_missing`, `parse_failed`,
   `no_in_progress_task`, plus success — each also emitting a
   `team_leader_nudge` team event. The *reaper's* outcome is as typed as the
   verdict.

Validation is hand-rolled and **fails loudly with specific reasons** —
`verdict_json_parse_failed`, `verdict_not_object`, `verdict_missing_role`,
`verdict_missing_task_id`, `verdict_invalid_verdict:<x>`, `verdict_missing_summary`,
`verdict_findings_not_array`, `verdict_finding_{i}_invalid_severity:<x>`,
`verdict_finding_{i}_missing_message` (`cli-worker-contract.ts:125-187`). Unknown
top-level keys are dropped, not rejected — the parser is lenient on extras, strict
on the contract fields.

### 4.3 Two design defects to NOT copy

**(a) The failure mode is a stuck task, not an escalation.** The prompt fragment
tells the worker (`:115`): *"The team leader reads this file to mark the task
complete; omitting it leaves the task stuck in_progress pending human review."*
And the handler docstring confirms (`:3023-3024`): *"On parse failure, emits a
warning event and leaves the task untouched for human review."* So a worker that
dies, or writes malformed JSON, leaves a node **silently in_progress forever**.

> For an *unattended* DAG this is the wrong default. `file_missing` /
> `parse_failed` must both be **escalation edges**, not warnings — a dead node with
> no verdict is exactly the "retry cap exhausted" gate the framework already plans
> for. Wire the reaper's typed result enum straight into the escalation path.

**(b) `revise` and `reject` collapse to the same terminal status** (`:3106`:
`payload.verdict === 'approve' ? 'completed' : 'failed'`). The distinction survives
only in task metadata. In a DAG where `revise` should re-enter the implement node
and `reject` should escalate, that collapse erases the routing signal at exactly
the point the scheduler reads it. Keep three terminal states, not two.

### 4.4 ⚠️ The contract is prompt-enforced — and Codex has a NATIVE alternative OMC does not use

OMC's contract is **rendered into the worker's prompt** as markdown
(`renderCliWorkerOutputContract`) and hand-validated after the fact. Nothing
*makes* the worker emit conforming JSON. The file header explains why OMC is stuck
there: *"Codex team workers are launched as persistent `codex` panes, not `codex
exec`"* — an interactive pane has no structured-output channel, so a prompt is the
only lever. (The same header notes `cursor` workers are excluded from
`CONTRACT_ROLES` entirely because they *"cannot perform the write-verdict-and-exit
dance"*.)

**Our lane is not stuck there.** `codex exec` in 0.146.0 ships two native
mechanisms **[MEASURED 2026-08-05, `codex exec --help`]**:

```
--output-schema <FILE>        Path to a JSON Schema file describing the model's
                              final response shape
-o, --output-last-message <FILE>  Specifies file where the last message from the
                              agent should be written
--json                        Print events to stdout as JSONL
```

`--output-schema` is confirmed by the vendor docs as *"request a final response
that conforms to a JSON Schema … useful for automated workflows that need stable
fields"* (<https://learn.chatgpt.com/docs/non-interactive-mode>, fetched
2026-08-05). And `lane-economics.md` §2 already established
`-o/--output-last-message` writes **only the agent's last message**, which is
precisely the verdict slot.

> **Recommendation (and a `use-tool-builtins` gate item): express the verdict
> contract as a JSON Schema file passed to `--output-schema`, captured via
> `-o verdict.json`, rather than as a prompt fragment.** The schema is enforced by
> the provider, not by the worker's diligence; the parser becomes a schema
> validation instead of nine hand-rolled type checks; and the same schema file is
> the machine-readable contract the Claude verifier reads. Keep OMC's *consumer*
> mechanisms (liveness gate, CAS-under-lock, rename-for-idempotency, typed reap
> outcomes) — those are transport-independent and are the genuinely hard-won part.
>
> ⚠️ **NEEDS-PROBE before building on it:** I did not run `codex exec
> --output-schema` (the brief forbids exec jobs), so I have not verified how it
> behaves on a *refusal* or a *usage-limit abort* — specifically whether a failed
> turn still writes `-o` (probably not: `print_final_output()` runs before
> `exit(1)` at `lib.rs:1061-1063`, so a partial write is plausible). The reaper
> must therefore treat "file exists" as necessary but not sufficient, exactly as
> OMC does.

### 4.5 Cross-vendor note

`fw-alpha` §"WORTH STEALING" #1 already flagged this as *"exactly the missing piece
in our `fable-orchestrator` codex lane, where the implementer's report is currently
free prose"*, and its portfolio observation stands: *"The one idea all three
converge on … an agent's output should be a typed artifact, not prose."* The
`harness` project's 29 `*.v1.schema.json` contracts (`fw-alpha` §3) are the
generalisation — every inter-agent message schema-validated with a
`schema_version`. If the DAG adopts one convention, adopt `schema_version` on the
verdict from day one; OMC's payload has no version field, which is why a contract
change there is a silent breakage.

---

## 5. Measuring the per-delegation wrapper tax on this machine

### 5.1 The instrument, cited

`$CC/costs.md:36` (offline copy, 291 lines; live equivalent
<https://code.claude.com/docs/en/costs.md>), verbatim:

> "On a Pro, Max, Team, or Enterprise plan, `/usage` also shows a breakdown of what
> counts against your plan limits. It attributes recent usage to **skills,
> subagents, plugins, and individual MCP servers**, with each shown as a percentage
> of the total. It also flags behaviors such as long context or cache misses when
> one accounts for 10% or more of recent usage. Press `d` or `w` to switch between
> the last 24 hours and the last 7 days. The figures are approximate and computed
> from **local session history on this machine**, so usage from other devices or
> claude.ai is not included."

Supporting lines: `$CC/costs.md:20` (for a subscriber the Session dollar figure
*"isn't relevant for billing purposes"* — it is a **relative** instrument, which is
what a routing comparison needs); `:280` (the ≥10% behaviour flags); `:40` (the same
breakdown appears in the VS Code Account & usage dialog with a Day/Week toggle,
*"Requires Claude Code v2.1.174 or later"* — **this machine is 2.1.222**, so that
route is available too).

### 5.2 ⚠️ It is TUI-only — there is no `claude usage` subcommand

**[MEASURED 2026-08-05] CONFIRMED.** `claude --help` `Commands:` block at 2.1.222 is
exactly: `agents, auth, auto-mode, doctor, gateway, import, install, mcp,
plugin|plugins, project, setup-token, ultrareview, update|upgrade`. `grep -ci "^  usage"`
→ **0**; control `agents`/`doctor` present in the same block. This matches the
settled ledger row at `.claude/agents/claude-code-expert.md:195`.

**Consequence:** `/usage` cannot be read by the DAG scheduler itself. It is a
**human measurement step**, not an automatable one.

### 5.3 The measurement procedure, stated so it is reproducible

To settle `lane-economics.md` §6.1's first open number (the Claude-side wrapper tax
per Codex delegation):

1. Run a **known number** of `codex-implementer` delegations in a bounded period
   (the count is the denominator; without it a percentage is unattributable).
2. In an interactive session, run `/usage` and press **`w`** (7-day) — the
   `codex-implementer` subagent row's percentage is the wrapper tax's share.
3. Press **`d`** (24h) as a second arm: if the two disagree wildly, the 7-day window
   is contaminated by earlier work and the number is not yet a measurement.
4. Record the date and the delegation count alongside the figure. Per
   `probes-need-a-control-arm.md` rule 6, a percentage without its denominator and
   its window is not reportable.

**Control arm for the instrument itself:** before trusting a small
`codex-implementer` share, confirm the breakdown is populated at all — a row you
*know* is large (this repo's own subagent-heavy sessions) must show a large share.
A breakdown where everything reads ~0% means the local session history is the
problem, not the wrapper.

### 5.4 The scriptable second route (needed, because §5.2 blocks automation)

`/usage` is approximate and interactive. For an automatable, absolute-token
attribution the substrate is the **transcript JSONL under
`~/.claude/projects/<slug>/`** — the same corpus this repo's
`dotfiles_setup.command_audit` already mines, and the same corpus the
`session-report` skill renders (*"tokens, cache, subagents, skills, expensive
prompts"*). That route gives absolute per-subagent token counts rather than
percentages, and it runs headless.

⚠️ **NEEDS-PROBE:** I did not verify that transcript records carry a per-subagent
token attribution field at 2.1.222 — I am asserting the corpus exists and is
already mined here, not that the specific field is present. Confirm before making
it the framework's cost governor.

### 5.5 The two budgets do not net against each other

`$CC/costs.md:128` (via `lane-economics.md` §5.3): the Claude session/weekly windows
are *"shared across all models"*, so moving Claude work between Claude models buys
nothing. Codex draws on the ChatGPT Pro plan instead (§1.1). Therefore **the offload
is real** — but the wrapper stays on the Claude side, which is exactly why §5.3's
number decides whether a given delegation is worth making. `$CC/costs.md:246`'s
*"approximately **7x** more tokens"* for agent teams in plan mode is the amplifier
sitting on the same side of the ledger.

---

## 6. Verdict table

| # | Claim | Verdict | Route |
|---|---|---|---|
| 1 | ChatGPT Pro Codex limits share a 5-hour window; Pro 5x = 50–500 Sol msgs, Pro 20x = 200–2,000 | **CONFIRMED (published, RE-DERIVED 2026-08-05)** | learn.chatgpt.com/docs/pricing, re-fetched; matches `lane-economics.md` §5b |
| 1b | OpenAI removed the 5-hour Codex limit in July 2026 | **SUSPECT / uncorroborated** | secondary blogs only; primary pricing page on 2026-08-05 still states the five-hour window |
| 1c | A mid-turn exhaustion aborts the running turn | **REFUTED** | pricing page: *"the agent will be able to continue working on that turn, subject to fair use limits"* |
| 2 | The client models 5 named windows (5-hour, daily, weekly, monthly, annual) + primary/secondary — more than the pricing page names | **CONFIRMED** | binary strings, control-armed |
| 3 | `planType` can discriminate Pro 5x from Pro 20x | **REFUTED** | `PlanType` enum has a single `pro` member |
| 4 | Remaining budget is programmatically readable without running a job | **CONFIRMED** | app-server `account/rateLimits/read` → `RateLimitWindow{usedPercent, windowDurationMins, resetsAt}` |
| 5 | `codex exec --json` carries rate-limit telemetry | **REFUTED** (my own earlier inference) | `exec_events.rs` event enum + both processors; control-armed |
| 6 | `codex exec` has a distinct exit code for usage exhaustion | **REFUTED** | `lib.rs:1062` — one generic `exit(1)` for every failure |
| 7 | Exhaustion is detectable in-band only by message substring | **CONFIRMED** | `ThreadErrorEvent{message}` only; `error.rs:622-727` message table |
| 8 | The typed code `usageLimitExceeded` exists but not on the exec surface | **CONFIRMED** | `CodexErrorInfo` in app-server v2 schema; absent from `exec_events.rs` |
| 9 | The reset timestamp in the error text is safely parseable | **REFUTED** | `format_retry_timestamp` — local tz, no date when same-day, no tz marker |
| 10 | OMC's verdict contract is prompt-enforced, not schema-enforced | **CONFIRMED** | `renderCliWorkerOutputContract` + hand-rolled `parseCliWorkerVerdict` |
| 11 | Codex offers a native structured-output path OMC does not use | **CONFIRMED** | `--output-schema` + `-o` in `codex exec --help`; OMC uses persistent panes |
| 12 | `--output-schema` still writes `-o` on a failed/limit-aborted turn | **NEEDS-PROBE** | not run (brief forbids exec jobs) |
| 13 | `/usage` attributes to subagents and is the right wrapper-tax instrument | **CONFIRMED** | `$CC/costs.md:36` |
| 14 | `/usage` is scriptable | **REFUTED** | no `usage` subcommand at 2.1.222; control-armed against `agents`/`doctor` |
| 15 | `codex <unknown> --help` returning rc=0 proves the subcommand exists | **REFUTED** | rc=0 for `usage`/`status`/`limits`/`account`; stdout is the discriminator |

## 7. Control arms run

| Negative claim | Probe | Control arm | Verdict |
|---|---|---|---|
| No `usage`/`status`/`limits` subcommand | `codex X --help` → top-level help | `codex exec --help` → exec-specific help; `codex login --help` → `Manage login` | discriminates ✓ |
| Rate-limit symbols in the binary | `rate_limit` 80, `usage_limit` 33 | fresh-absent `zzqvvkbb` → 0 | discriminates ✓ |
| `account/*` method set | 9 methods from `ClientRequest.json` | `thread/*` → 8+ enumerated; fresh-absent `vqxmzz9/` → 0 | discriminates ✓ |
| Core error enum absent from app-server schema | `server_overloaded`/`quota_exceeded`/… → 0 in bundle | `rate_limit_reached` → 5 in same bundle; fresh-absent `kmqzvv31` → 0 | discriminates ✓ |
| No rate-limit field in exec events | `grep -ci rate` → 1 (a comment) | `grep -ci usage` → 3; fresh-absent `xqvbz42` → 0 | discriminates ✓ |
| No `claude usage` subcommand | `grep -ci "^  usage"` → 0 | `agents`, `doctor`, `plugin` present in same block | discriminates ✓ |
| Offline `$CC` corpus reachable | `costs.md` 291 lines, `:36` present | `--print` → 5 hits in `cli-reference.md`; fresh-absent `wbqz73x` → 0 | discriminates ✓ |

**No credential value was printed at any point.** `codex login status` prints only
`Logged in using ChatGPT`. `~/.codex/auth.json` was **not** re-read this session —
the auth facts are inherited from `lane-economics.md` §3 and labelled as such.

## 8. Ticket implications for the DAG framework

1. **The budget governor queries the app-server, not `codex exec`.** A ticket is
   needed for a thin `account/rateLimits/read` client (stdio JSON-RPC, `params:
   null`) that returns `{usedPercent, resetsAt, windowDurationMins}` per window.
   Everything else in the scheduler reads that.
2. **Pre-flight gate, substring backstop.** Dispatch is gated on `usedPercent`
   headroom; the exec-side detector (union of `You've hit your usage limit`,
   `out of credits`, `spend cap`) exists only to catch the check→dispatch race.
   Never rc, never parsed reset text.
3. **The verdict contract ships as a JSON Schema file**, passed to
   `codex exec --output-schema` and captured with `-o`, carrying a
   `schema_version`. Not a prompt fragment.
4. **`file_missing` and `parse_failed` are escalation edges**, not warnings —
   inverting OMC's "leave it stuck for human review" default, which is
   incompatible with unattended operation.
5. **Keep three verdict terminal states** (`approve` / `revise` / `reject`) mapped
   to three DAG edges; do not collapse `revise` into `failed`.
6. **Port OMC's reaper mechanics verbatim**: liveness gate, CAS-under-file-lock on
   the task record, rename-for-idempotency, typed reap outcomes.
7. **Two numbers stay unmeasured and block sizing**: the Claude-side wrapper tax
   (§5.3 procedure) and Pro 5x vs Pro 20x (§1.4 — *not* obtainable from
   `planType`; only the dashboard or observed `usedPercent` movement). Neither is
   guessable.
8. **A Codex SDK exists upstream** (`sdk/python`, `sdk/typescript`, plus
   `codex-rs/app-server-protocol/schema/typescript/v2/`) — before hand-rolling a
   JSON-RPC client, check it, per `use-tool-builtins`. **NEEDS-PROBE:** I confirmed
   the directories exist in `openai/codex` but did not evaluate the SDKs.

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex) — primary source of truth for §2–§3: `codex-rs/exec/src/lib.rs`, `codex-rs/exec/src/exec_events.rs`, `codex-rs/exec/src/event_processor_with_jsonl_output.rs`, `codex-rs/protocol/src/error.rs`, `codex-rs/protocol/src/protocol.rs`, `docs/exec.md`; repo meta and code search via `gh api`.
- [Yeachan-Heo/oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) — the prior-art verdict contract, read from the local plugin cache at v4.15.7 (`src/team/cli-worker-contract.ts`, `src/team/runtime-v2.ts`).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo: prior reports `docs/research/kb/reports/agents/{fw-alpha-frameworks,lane-economics}.md`, ledger `.claude/agents/claude-code-expert.md`.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline `agent-harness-docs` supplying `$CC/costs.md` and `$CC/cli-reference.md`.

Non-GitHub sources consulted:

- <https://learn.chatgpt.com/docs/non-interactive-mode> (canonical target of `developers.openai.com/codex/noninteractive`, 308) — `codex exec` `--json` event set and `--output-schema`, fetched 2026-08-05.
- <https://learn.chatgpt.com/docs/pricing> — Codex plan limits, **re-fetched 2026-08-05** (matches `lane-economics.md` §5b's 2026-08-04 reading); also the source of the mid-turn continuation quote in §1.2.
- Practitioner/secondary, all fetched 2026-08-05 and labelled ANECDOTAL in §1.2b: <https://www.morphllm.com/codex-pricing>, <https://simplemetrics.xyz/chatgpt-codex-limits-2026/>, <https://ofox.ai/blog/codex-weekly-limit-drained-2026/>, <https://www.eesel.ai/blog/gpt-remove-5-hour-limits>, <https://www.explainx.ai/blog/chatgpt-codex-5-hour-limit-removed-weekly-reset-july-2026>, <https://www.jdhodges.com/blog/how-to-check-codex-usage-chatgpt-plus/>.
- <https://code.claude.com/docs/en/costs.md> — live equivalent of `$CC/costs.md`.
