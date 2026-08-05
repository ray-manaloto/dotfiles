# Claude Code expertise — Fable-first model routing & fallback (2026-08-05, v2.1.222)

`claude --version` → `2.1.222 (Claude Code)`
Binary audited: `/Users/rmanaloto/.local/share/claude/versions/2.1.222` (271,289,792 bytes, Mach-O 64-bit arm64)
Docs corpus: `$CC` = `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code` (174 pages)

Corpora consulted: **binary byte-scan**, **`claude --help`** (+ `claude agents --help`), **`$CC` docs**, `graphify query` (repo orientation). **No live exhaustion probe** — exhausting the Fable cap is not an ethical probe, so every reactive-shape claim below is flagged for how many routes confirm it.

---

## Verdict table

| # | Verdict | Claim | Corpus + control arm |
|---|---|---|---|
| 1 | **CONFIRMED** | A native availability fallback chain exists: `--fallback-model` flag / `fallbackModel` settings array | `$CC/model-config.md:357-383`; `claude --help`; binary zod `.describe()` @239849936 |
| 2 | **CONFIRMED** | **That chain explicitly excludes HTTP 429 / rate-limit / billing.** It cannot carry Fable-*exhaustion* fallback | docs `:359` **and** binary `tR_=new Set([401,407,429,404,403,413])` + `S.type==="billing_error"` guard @242894961/@242887688 — two routes |
| 3 | **CONFIRMED** | **A SECOND, UNDOCUMENTED native path DOES handle Fable credit exhaustion** — `model_fable_consent` → `hVe()` substitutes Opus → Sonnet → Haiku | binary @246376864, @240965321; docs **0 of 174**, control `fallbackModel` → 8 files |
| 4 | **SUSPECT** | That substitution fires **without a dialog** in a headless/background node (`no_dialog_fallback` telemetry branch) | one route only (binary control flow); no second corpus, no live probe |
| 5 | **CONFIRMED** | Fable exhaustion is **credit / spend-cap / seat-entitlement** shaped, not a weekly-bucket: `You've reached your Fable 5 limit.` / `Fable 5 requires usage credits.` | binary `N0_()` @242876500 |
| 6 | **CONFIRMED** | **There is no `seven_day_fable` bucket.** `seven_day_opus` and `seven_day_sonnet` exist; Fable draws the shared `seven_day` | binary: `seven_day_fable` → **0**, control `seven_day_opus` → **15** |
| 7 | **CONFIRMED** | Proactive quota surface = `rate_limits.{five_hour,seven_day}.{used_percentage,resets_at}`, **only after the first API response** — no pre-flight quota API | `$CC/statusline.md:762`; binary field table |
| 8 | **CONFIRMED** | 15 distinct `anthropic-ratelimit-unified-*` response headers carry the real state | binary shape-enumeration; control `anthropic-vqzmk-*` → 0 |
| 9 | **CONFIRMED** | Session + weekly windows are **shared across all models**; only Opus/Sonnet have model-scoped sub-buckets | `$CC/costs.md:128` **and** `$CC/errors.md:321` |
| 10 | **CONFIRMED** | `--bg` and `--print` are **mutually exclusive** (hard error since v2.1.198), while `--help` labels `--fallback-model` "(only works with --print)" | `$CC/errors.md:1191-1195`; `claude --help` |
| 11 | **REFUTED** (of my own suspicion) | …but a backgrounded session **does** carry `--fallback-model` through | `$CC/agent-view.md:402-408` names `--fallback-model` in the carry-over list |
| 12 | **SUSPECT** | The doc-promised literal `You've hit your Opus limit` is **not in the binary** | binary `"hit your Opus limit"` → **0**; shape probe `"You've hit your [a-z ]{0,20}limit"` → 9 (none Opus); control `zzqjjxwv9pl` → 0. One route only |
| 13 | **CONFIRMED** | `CLAUDE_CODE_SUBAGENT_MODEL` is a **global hammer** that overrides per-invocation `model` AND frontmatter — for subagents, workflow agents **and agent teams** | `$CC/sub-agents.md:306-311`; `$CC/model-config.md:607`; `$CC/changelog.md:1447` |
| 14 | **CONFIRMED** | `CLAUDE_CODE_NO_MODEL_FALLBACK=true` collapses the availability chain to `[primary]` **and** disables Fable substitution — undocumented | binary `yIe()`/`iJr()`/`hVe()` @240965321; docs **0 of 174**, control `ANTHROPIC_MODEL` → 14 files |
| 15 | **CONFIRMED** | Fable constraints: never a default on any account type; thinking **cannot** be disabled; effort `low..max` with a model-default **hold** | `$CC/model-config.md:338`, `:526`, `:444`, `:452` |
| 16 | **CONFIRMED** | `--max-budget-usd <amount>` is a hard per-invocation spend cap for headless nodes; `--task-budget <tokens>` is its API-side sibling | `claude --help`; binary @260881312 (validates `>0`) |

---

## 1. How Fable exhaustion / limits SURFACE

### 1a. Proactive — thin, and post-hoc by construction

**The statusline JSON is the only documented proactive read.** `$CC/statusline.md:762`, verbatim:

> Display Claude.ai subscription rate limit usage in the status line. The `rate_limits`
> object contains `five_hour` (5-hour rolling window) and `seven_day` (weekly) windows.
> Each window provides `used_percentage` (0-100) and `resets_at` (Unix epoch seconds when
> the window resets).
>
> This field is only present for Claude.ai subscribers (Pro/Max) **after the first API
> response.**

That last clause is the whole constraint: **there is no pre-flight quota API a node can consult before it spends.** A statusline script is a *hook* the harness invokes with session JSON on stdin — the router can read it, but only from inside a session that has already made a request.

**The binary's window schema is wider than the docs' two fields.** Read out of the schema tables at `@86910112`, `@212850816`, `@235729920`:

```
five_hour   seven_day   seven_day_opus   seven_day_sonnet
seven_day_overage_included   seven_day_oauth_apps
overage   extra_usage   cinder_cove   limits
```

Adjacent status/label strings in the same tables: `warning`, `rejected`, `pro`, `max`,
`overage`, `Run /usage-credits to raise the cap`, `Run /usage-credits to ask your admin
for more`, `/upgrade to keep using Claude Code`.

**Wire headers — shape-enumerated** (`anthropic-ratelimit-[a-z0-9-]+`), with a freshly
invented known-absent control:

| Header | occ |
|---|---:|
| `anthropic-ratelimit-unified-status` | 2 |
| `anthropic-ratelimit-unified-reset` | 8 |
| `anthropic-ratelimit-unified-fallback` | 2 |
| `anthropic-ratelimit-unified-upgrade-paths` | 2 |
| `anthropic-ratelimit-unified-representative-claim` | 8 |
| `anthropic-ratelimit-unified-grace-status` | 2 |
| `anthropic-ratelimit-unified-grace-5h-utilization` | 2 |
| `anthropic-ratelimit-unified-grace-7d-utilization` | 2 |
| `anthropic-ratelimit-unified-overage-status` | 8 |
| `anthropic-ratelimit-unified-overage-in-use` | 2 |
| `anthropic-ratelimit-unified-overage-reset` | 4 |
| `anthropic-ratelimit-unified-overage-disabled-reason` | 13 |
| `anthropic-ratelimit-unified-overage-period-channel-utilization` | 2 |
| `anthropic-ratelimit-unified-overage-period-monthly-utilization` | 2 |
| **control** `anthropic-vqzmk-[a-z-]+` | **0** |

`$CC/errors.md:337` names these headers as the client's own discriminator:
*"Claude Code tells these apart from your plan limit by the absence of the unified quota
headers a real limit response carries."*

`/usage` is **local + cached, not an API**: `$CC/costs.md:36` — *"The figures are approximate
and computed from local session history on this machine, so usage from other devices or
claude.ai is not included"*; `:38` — when the usage endpoint is rate-limited it shows a
≤60-min-old snapshot with a `Showing last-known usage` note. **Do not build the router on
`/usage`.**

### 1b. Reactive — the exact shapes

**Shared window / plan limit** (`$CC/errors.md:317`, verbatim):

```text
You've hit your session limit · resets 3:45pm
You've hit your weekly limit · resets Mon 12:00am
You've hit your Opus limit · resets 3:45pm
```

⚠️ **`You've hit your Opus limit` is NOT a literal in the binary.**

```
probe   "hit your Opus limit"                 -> 0 occurrences
shape   "You've hit your [a-z ]{0,20}limit"   -> 9 occurrences  (monthly spend / monthly / fast)
control "zzqjjxwv9pl"                         -> 0 occurrences
```

The nine real hits are `monthly spend limit`, `monthly limit`, `fast limit` — never `Opus
limit`. **SUSPECT**: the per-model banner is almost certainly server-supplied text or a
template my literal probe cannot span. **Do not build a string matcher on that phrase.**

**Fable-specific exhaustion copy** lives in one function, `N0_(e,t)` @242876500, verbatim:

```js
function N0_(e,t){
  let r = t ? "You've reached your Fable 5 limit." : "Fable 5 requires usage credits.";
  switch(e){
    case"out_of_credits":
      return n0() ? "You're out of usage credits. Run /usage-credits to keep using Fable 5 or /model to switch models."
                  : "You're out of usage credits. /model to switch models.";
    case"org_spend_cap_reached": case"org_level_disabled_until":
      return n0() ? "You've hit your monthly spend limit. Run /usage-credits to manage your limit and keep using Fable 5 or switch models to continue this chat."
                  : "You've hit your monthly spend limit. /model to switch models.";
    case"org_level_disabled": case"org_service_level_disabled":
    case"seat_tier_level_disabled": case"seat_tier_zero_credit_limit":
    case"member_level_disabled": case"member_zero_credit_limit":
    case"group_zero_credit_limit":
      return n0() ? `${r} Run /usage-credits to continue or switch models with /model.` : `${r} /model to switch models.`;
    default:
      return n0() ? `${r} Run /usage-credits to continue or switch models with /model.` : `${r} /model to switch models.`;
  }
}
```

`e` is the value of the **`anthropic-ratelimit-unified-overage-disabled-reason`** header,
which the 429 branch reads at `@242885528`. Full enum, shape-enumerated from the switch:

`out_of_credits` · `org_spend_cap_reached` · `org_level_disabled_until` ·
`org_level_disabled` · `org_service_level_disabled` · `seat_tier_level_disabled` ·
`seat_tier_zero_credit_limit` · `member_level_disabled` · `member_zero_credit_limit` ·
`group_zero_credit_limit`

**Fable UNAVAILABILITY is a different string** (`vft`, @242879500), sibling of the Opus one
(`Tft`):

```
"Fable is experiencing high load, please use /model to switch to Sonnet"
"Opus is experiencing high load, please use /model to switch to Sonnet"
```

**Structured surface for a headless node** — `$CC/headless.md:191` gives the `error`
category enum on `--output-format json`/`stream-json`:

```
authentication_failed | oauth_org_not_allowed | billing_error | rate_limit |
overloaded | invalid_request | model_not_found | server_error | max_output_tokens | unknown
```

**This is the machine-readable discriminator the router should key on** — `rate_limit`
(quota) vs `overloaded` (availability) vs `model_not_found` — not on prose.

**Also:** `$CC/errors.md` "Automatic retries" — Claude Code retries **temporary 429s that do
NOT carry plan-quota headers** (up to 10 attempts, exponential backoff). A 429 that *does*
carry the quota headers is a real limit and is surfaced, not retried. So a `rate_limit`
result reaching your script has already exhausted the retry budget.

### 1c. Fable has no weekly bucket

```
probe   "seven_day_fable"  -> 0 occurrences
control "seven_day_opus"   -> 15 occurrences
```

**Fable spend lands in the SHARED `five_hour` + `seven_day` windows.** Fable's *own* gate is
the credits / spend-cap / seat-entitlement axis in `N0_()` — a different meter with a
different error shape. Two meters, two failure modes, two handlers.

---

## 2. Native model-fallback-on-error: THREE mechanisms, only one of which does quota

### (a) Fallback model chains — availability only

`$CC/model-config.md:359`, verbatim:

> When the primary model is overloaded, unavailable, or returns another non-retryable
> server error, Claude Code can switch to a fallback model instead of failing the request.
> **Authentication, billing, rate-limit, request-size, and transport errors never trigger a
> switch**; those follow their normal retry and error handling.

**Binary confirmation by an independent route.** The exclusion sets, @242894961:

```js
eR_=["invalid_request_error","authentication_error","billing_error","permission_error",
     "not_found_error","request_too_large","rate_limit_error","timeout_error",
     "api_error","overloaded_error"],
tR_=new Set([401,407,429,404,403,413]),
rR_=[Grn,ONt,rys,aSo,I1u,zrn]
```

and the last-resort guard, @242887688:

```js
let M = S instanceof Oi && (
    (S.status!==void 0 && tR_.has(S.status) && !(S.status===404 && r.isNonStreamingRequest))
    || S.type==="billing_error"
    || rR_.some((L)=>L(S)));
if (S instanceof Oi && S.status!==void 0 && !M && r.fallbackModel && r.fallbackModel!==r.model) {
    … throw new v7(r.model, r.fallbackModel, "last_resort", S)
}
```

**429 ∈ `tR_` ⇒ `M` is true ⇒ no fallback.** The 429 branch instead retries/backs-off
(@242885528):

```js
if (T && !kUe() && S instanceof Oi && (S.status===429 || uEe(S))) {
    let M = S.headers?.get("anthropic-ratelimit-unified-overage-disabled-reason");
    if (M!==null && M!==void 0) { q7c(M), o.fastMode=!1; continue }
    let L = pR_(S);                                   // Retry-After
    if (L!==null && L<uR_) { await _r(L, r.signal, …); continue }
    let H = Math.max(L??cR_, dR_), j = uEe(S)?"overloaded":"rate_limit";
    F7c(Date.now()+H, j); if (Ql()) o.fastMode=!1; continue
}
```

Every `FallbackTriggeredError` (`v7`) construction site (`v7\(` → 6 occ, 5 in the API layer):

| `reason` | Trigger | Site |
|---|---|---|
| `"model_not_found"` | `v1u(S)` | @242885528 |
| `"permission_denied"` | `E1u(S)` | @242885528 |
| `"server_error"` | `wys(S)` when not `kUe()` | @242885528 |
| `"overloaded"` | repeated 529s past `wSo`; also mid-stream | @242886508, @250271794 |
| `"last_resort"` | non-retryable, **not** in `tR_`, not `billing_error` | @242887688 |
| `"model_blocked"` | per-model server block (`tengu-model-error-overrides`) | @250224426 |

**No usage-limit reason exists.**

Operational properties:

| Property | Source |
|---|---|
| `--help` label: **"only works with `--print`"** | `claude --help` |
| Flag beats setting | `:377`; binary `.describe()` "CLI --fallback-model takes precedence" |
| Chain capped at **3** after dedup | `:361` |
| Switch lasts the **current turn only**; primary retried each user turn | `:361`; `--help` |
| No startup confirmation; `/status` does **not** show the chain | `:379` |
| Entries outside `availableModels` dropped before the walk | `:383` |
| Won't fall back to a smaller context window during compaction | `:383` |
| `"default"` expands to the default model | `:377` |
| Same-as-primary is **rejected**: `Fallback model cannot be the same as the main model. Please specify a different model for fallbackModel option.` | binary @222731826, thrown at @252624315 |
| **`fallbackModel` arrays REPLACE across settings scopes** (other arrays union) | binary `gae()`: `if(r==="fallbackModel")return t;` @239909258 |
| **`--fallback-model` IS carried into a backgrounded session** | `$CC/agent-view.md:402-408` |
| It is in the **job respawn allowlist** `Cce` — survives supervisor restart | binary @246144430 + `[jobs] stripped non-allowlisted respawnFlags token(s)` warning |

Settings schema `.describe()` verbatim (@239849936):

> `fallbackModel`: *Fallback model(s) tried in order when the primary model is overloaded or
> unavailable. Each element accepts a model name or alias; "default" expands to the default
> model. CLI --fallback-model takes precedence.*

### (b) Automatic model fallback — content classifier only

`$CC/model-config.md:390-392`:

* **Fable 5**: biology → **Opus 5**; cybersecurity → **Opus 4.8**
* **Opus 5**: cybersecurity → Opus 4.8; biology → **refusal** (no fallback)

Requires v2.1.219+ (`:399`) — live on this host (2.1.222).

Three properties that bite an unattended framework:

* **After a fallback the SESSION CONTINUES on the fallback model** (`:397`) — *sticky*,
  unlike the per-turn availability chain. Implemented as `refusalFallbackModelLatch`
  (@238507344) storing `previousOverride` / `previousAppStateModel` /
  `previousModelForSession`, so the demotion is recorded and revertible.
* **Can fire on the FIRST request** (`:405`) — that request carries CLAUDE.md + git status;
  a security-adjacent repo trips it on context alone. Diagnostic: `claude --safe-mode`.
* **With `switchModelsOnFlag: false`, a flagged request in `-p` / SDK ENDS THE TURN WITH A
  REFUSAL** (`:417`) because the prompt cannot be shown. **Leave `switchModelsOnFlag` at its
  default `true` for unattended nodes**, or a flagged Fable node dies instead of demoting.

Undocumented kill-switches on this path (0 doc hits): `CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK`,
`CLAUDE_CODE_REFUSAL_FALLBACK_CATCH_ALL`.

### (c) ⭐ `model_fable_consent` — the UNDOCUMENTED Fable-exhaustion substitution

**This is the answer to the caller's question 2, and it is in no doc page.**

Control-armed absence:

| Token | doc files (of 174) |
|---|---:|
| `model_fable_consent` | **0** |
| `model_consent_fallback` | **0** |
| `no_dialog_fallback` | **0** |
| `overage_enable_deferred` | **0** |
| `buildAvailabilityFallbackChain` | **0** |
| `usage_limit_grace_wrapup` | **0** |
| *control* `fallbackModel` | 8 |
| *control* `switchModelsOnFlag` | 2 |
| *control* `bqx9tzm` (invented) | 0 |

The substitution-target resolver, @240965321, verbatim:

```js
function yIe(){ return te.CLAUDE_CODE_NO_MODEL_FALLBACK===!0 }
function iJr(e,t){ if(yIe()) return [e]; return [e, ...t.filter((r)=>r!==e)] }   // buildAvailabilityFallbackChain
function hVe(){
  if(yIe()) return null;
  let e = gC();                        // getDefaultMainLoopModel
  if(!i0(e)) return e;                 // not-Fable ⇒ use it
  for(let t of [xv(), o0(), fVe()]){   // getDefaultOpusModel → getDefaultSonnetModel → getDefaultHaikuModel
    if(i0(t)) continue;
    if(F4(t) ?? uc(t)) return t;       // policy-allowed?
  }
  return null;
}
```

**`hVe()` walks Opus → Sonnet → Haiku, filtered by the model policy.** That *is* the
Fable→Opus fallback the design wants, and it is native.

The driving flow, @246376864, verbatim (abridged only where noted):

```js
if(uo && B.requestDialog) { … sr = await B.requestDialog(zUe,{overagesEnabled:Wut()},…) }
let Oo = sr==="consent" && await KFu();
…
if(Oo) Se("model_fable_consent");
else if(sr==="consent")        Oe("model_fable_consent","overage_enable_deferred");
else if(sr==="switch_default") me("model_fable_consent","declined");
else if(!oo)                   Oe("model_fable_consent","dismissed");

if(!Oo){
  if(!uo && q) Oe("model_fable_consent","no_dialog_fallback");
  let Cn = hVe();
  if(Cn===null){
    let Un = yIe();
    if(q) me("model_fable_consent", Un?"no_model_fallback_env":"no_allowed_fallback");
    let io = Xu({content: Un
        ? "CLAUDE_CODE_NO_MODEL_FALLBACK is set: model substitution is disabled · unset it to allow the swap"
        : "Your model policy only allows Fable 5, which requires usage credits · /model to set it up", …});
    return yield io, …, {reason:"model_error", error: Un
        ? Error("CLAUDE_CODE_NO_MODEL_FALLBACK forbids model substitution")
        : Error("Fable consent declined and the model policy allows no non-Fable fallback")};
  }
  let Tn=!1;
  if(q){ if(sr==="switch_default") Tn = VFu(Cn);
         B.setAppState((Un)=>({...Un, mainLoopModel:Cn, mainLoopModelForSession:null})); wv(Cn); … }
  B.options={...B.options, mainLoopModel:Cn}; At=Cn; j=Cn;
  yield {type:"query_model_change", toModel:Cn};
  if(q) yield {type:"system", subtype:"model_consent_fallback",
               content:`Switched to ${hm(Cn)} ${Tn?"— now your default model":"for this session"}`};
}
```

**What this means for the router:**

1. When Fable hits its credit/entitlement gate, Claude Code **substitutes a non-Fable model
   itself** and the session continues — it does **not** die. It emits a
   `query_model_change` event and a `system` / `model_consent_fallback` message. On
   `--output-format stream-json` those are **machine-observable**, which is the router's
   detection hook.
2. `sr==="switch_default"` can make the substitution **your saved default** (`VFu(Cn)`) —
   a persistent side-effect the framework must be prepared to undo.
3. **`CLAUDE_CODE_NO_MODEL_FALLBACK=true` turns all of this off** and turns exhaustion into a
   hard `model_error`. It also collapses `buildAvailabilityFallbackChain()` to `[primary]`,
   with a tripwire that throws if any pivot is attempted anyway:
   `"CLAUDE_CODE_NO_MODEL_FALLBACK tripwire: a model-fallback pivot was attempted while the
   no-fallback guarantee is active. This branch should be unreachable…"` — i.e. it is a
   *hard guarantee*, useful if a node must be Fable-or-nothing.
4. Compaction has its own copy of the branch: `compact_no_model_fallback_env`,
   `compact_no_allowed_fallback`, `compact_substituted`, and
   `"Compaction unavailable: your model policy only allows Fable 5, which requires usage
   credits · /model to set it up"`.

**SUSPECT (one route):** the `no_dialog_fallback` telemetry branch reads as "no consent
dialog was available, so we substituted anyway" — which is exactly the headless case. The
control flow supports it, but I have no second corpus and no live probe. **Design for both:
assume substitution happens, but detect it, and also handle a hard `model_error`.**

### Answer to question 2, stated plainly

**Partly native, partly not.**

| Failure | Native handling | Framework must |
|---|---|---|
| Fable **overloaded / 529 / unavailable** | ✅ `fallbackModel` chain (per-turn) | just configure the chain |
| Fable **blocked by policy** | ✅ `"model_blocked"` → chain | configure the chain |
| Fable **flagged by bio/cyber classifier** | ✅ sticky demote to Opus 5 / Opus 4.8 | keep `switchModelsOnFlag: true`; detect the demotion |
| Fable **out of credits / spend cap / seat gate** | ✅ `model_fable_consent` → `hVe()` Opus→Sonnet→Haiku (undocumented; headless behaviour SUSPECT) | **detect `query_model_change` / `model_consent_fallback`, and handle `model_error` as a respawn trigger** |
| **Shared session / weekly window exhausted** | ❌ **nothing** — 429 retries then fails | **catch-and-hold**: no Anthropic model helps; only the Codex lane or waiting for `resets_at` |

So: **you must catch-and-respawn, but only for the shared-window case and as a safety net
for the `model_error` tail.** Do not build a bespoke Fable→Opus swapper for the credit case
— the harness already does it, and a competing swapper would fight the latch.

---

## 3. The full per-node model-selection surface

### Main session (interactive or headless), precedence high→low

`$CC/model-config.md:83-89` + `$CC/errors.md:995`:

1. `/model <alias|name>` during the session (in `-p` mode: **session-only, not saved**)
2. `--model <alias|name>` at launch
3. `ANTHROPIC_MODEL` env var
4. `model` field in settings — **local → project → user** in that precedence
   (`.claude/settings.local.json` → `.claude/settings.json` → `~/.claude/settings.json`)
5. account-type default / organization default

**Overriding facts a router must encode:**

* **Managed/policy settings and `--settings` beat everything below them**, including an org
  default with override on (`$CC/model-config.md:295`).
* **A resumed session keeps its transcript model** regardless of the current `model` setting
  (`:97`) — *unless* the model is retired or excluded, in which case it falls through the
  normal precedence. **`--model`/`ANTHROPIC_MODEL` at relaunch still win** (`:99`).
  ⇒ A DAG node that resumes will **not** pick up a routing change unless you pass `--model`.
* `default` resolves per account type (`:323`): Max / Team Premium / Enterprise PAYG /
  Anthropic API → **Opus 5**; Pro / Team Standard / Enterprise seats → **Sonnet 5**.
* `--model` and `ANTHROPIC_MODEL` are **not** validated at launch — a typo produces
  *There's an issue with the selected model* on the first request (`:113`). Only SDK
  `setModel()` / Desktop-style switches get the pre-check.

### Background sessions (`claude --bg`) — the DAG's durable nodes

| Lever | Effect | Source |
|---|---|---|
| `claude --bg --model <m> "<task>"` | per-session model | `$CC/agent-view.md:527` |
| `claude agents --model <m>` | **dispatch default** for every session started from agent view | `claude agents --help`; `$CC/agent-view.md:545-548` |
| `claude agents --effort <level>` | dispatch default effort | `claude agents --help` |
| `/model` inside agent view | changes dispatch default for the rest of that `claude agents` run, `(session)` marker, **does not write settings** | `$CC/agent-view.md:516` |
| project `.claude/settings.json` `env.ANTHROPIC_MODEL` | applies to background sessions **run in that directory** | `$CC/agent-view.md:533` |
| dispatching shell's `ANTHROPIC_DEFAULT_*_MODEL`, `CLAUDE_CODE_USE_*` | **inherited from the shell that dispatched**, applied to the worker | `$CC/agent-view.md:535`, `:632` |
| carry-over on backgrounding | MCP servers, settings **and `--fallback-model`** remain in effect | `$CC/agent-view.md:402-408` |
| supervisor restart | permission mode, model, effort and carried flags **all persist**; a mid-session `/model` change is kept | `$CC/agent-view.md:539` |
| respawn allowlist | binary `Cce` set includes `--model`, `-m`, `--effort`, `--fallback-model`, `--max-budget-usd`, `--task-budget`, `--agent`, `--settings`, `--thinking`; **anything not in it is stripped** with a `[jobs] stripped non-allowlisted respawnFlags token(s)` warning | binary @246144430 |

⚠️ **`--bg` and `--print` conflict** (`$CC/errors.md:1191`, hard error since v2.1.198):

```text
--bg and --print conflict: --print never starts the interactive session that `claude agents`
attaches to, so the job would be unattachable. The prompt is the positional — drop --print:
`claude --bg '<task>'`.
```

⇒ **A durable `--bg` node cannot be a `-p` node.** Since `--help` labels `--fallback-model`
"(only works with --print)" but `$CC/agent-view.md:408` lists it among the flags a
backgrounded session carries, the two corpora disagree. **Safest resolution: put the chain
in `fallbackModel` (settings), which carries no `--print` caveat in any corpus, and pass
`--fallback-model` as well where the node is genuinely `-p`.**

### Subagents / workflow agents / teammates

`$CC/sub-agents.md:304-311`, precedence high→low:

1. `CLAUDE_CODE_SUBAGENT_MODEL` (alias or ID; `inherit` ≡ unset as of v2.1.196)
2. per-invocation `model` parameter on the Agent tool
3. subagent frontmatter `model`
4. the main conversation's model

⚠️ **`CLAUDE_CODE_SUBAGENT_MODEL` is a global hammer.** `$CC/model-config.md:607` — it applies
to *"all subagents, agent teams, and agents in a workflow"*, and `$CC/changelog.md:1447`
records the fix that made it reach **teammate processes** too. **Setting it destroys every
per-role Fable/Opus decision in the DAG.** If the framework wants per-node routing, this
variable must be **unset** (or `inherit`) and routing must go through frontmatter /
per-invocation / per-session `--model`.

`$CC/workflows.md:359`: *"Every agent in a workflow uses your session's model unless the
script routes a stage to a different one or `CLAUDE_CODE_SUBAGENT_MODEL` is set, which
overrides both."*

### What happens when a requested model is DENIED

| Situation | Behaviour | Source |
|---|---|---|
| Subagent model excluded by `availableModels` | **silently skipped; runs on the inherited model** | `$CC/sub-agents.md:313` |
| Session model excluded by `availableModels` | dropped; falls back to Default (or, with `enforceAvailableModels`, the first allowed entry) with a notice naming requested + substituted | `$CC/model-config.md:159`, `:213` |
| Alias whose newest version is outside the allowlist | resolves to the newest **permitted** version of the family (v2.1.205+) | `:159` |
| Fallback-chain entry excluded | dropped **before** the walk | `:383` |
| Content-fallback target excluded | **no fallback** — the refusal stands, session model unchanged | `:401` |
| Model not on the plan | hard error `Claude Opus is not available with the Claude Pro plan · Select a different model in /model` — **no auto-substitution** | `$CC/errors.md:1022` |
| Unrecognised model string via SDK `setModel()` | rejected locally: `Model "<n>" is not a recognized model id.` — session keeps its model | `$CC/errors.md:1002` |
| Bad `--model` / `ANTHROPIC_MODEL` / `model` setting | **no pre-check** — *There's an issue with the selected model* on the first request | `$CC/model-config.md:113` |
| Org effort cap exceeded | runs at the cap; **in background agents and json/stream-json output the clamp is SILENT** | `$CC/model-config.md:315` |

**Undocumented model-routing env vars** (binary shape-enumeration
`(CLAUDE_CODE|ANTHROPIC|CLAUDE)_[A-Z0-9_]*(MODEL|EFFORT|FALLBACK|THINKING)[A-Z0-9_]*`),
doc-hit counts control-armed against `ANTHROPIC_MODEL` → 14 files and `wq7vzmr` → 0:

| Var | binary occ | doc files |
|---|---:|---:|
| `CLAUDE_CODE_NO_MODEL_FALLBACK` | 11 | **0** |
| `CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK` | 3 | **0** |
| `CLAUDE_CODE_REFUSAL_FALLBACK_CATCH_ALL` | 5 | **0** |
| `CLAUDE_CODE_BG_CLASSIFIER_MODEL` | 6 | **0** |
| `CLAUDE_CODE_AUTO_MODE_MODEL` | 6 | **0** |
| `CLAUDE_CONTEXT_COLLAPSE_MODEL` | 6 | **0** |
| `FALLBACK_FOR_ALL_PRIMARY_MODELS` | — | 1 |
| `CLAUDE_CODE_SUBAGENT_MODEL` | 13 | 5 |
| `CLAUDE_CODE_EFFORT_LEVEL` | 17 | 5 |
| `ANTHROPIC_DEFAULT_FABLE_MODEL` | 24 | 4 |

---

## 4. Documented Fable constraints worth encoding

All from `$CC/model-config.md`:

* **`:66` / `:338` — Fable 5 is NEVER a default on any account type.** *"Sessions use Fable 5
  only after you choose it, with `/model fable`, a `model` setting, or the `best` alias where
  Fable 5 is available."* ⇒ **A Fable node must name Fable explicitly, every launch.** There
  is no "inherit Fable" path except the session model.
  ⚠️ *"Choosing it with `/model` saves it as the selected model in your user settings, so
  later sessions start on Fable 5 until you change models."* — an interactive `/model fable`
  **contaminates every later session on the machine**, including cheap ones. Route with
  `--model fable` per node, never with a saved user-settings default.
* **`:34` — the `best` alias**: *"Uses Fable 5 where your organization has access to it,
  otherwise the latest Opus model."* This is a **static-capability** fallback resolved at
  selection time, **not** a runtime exhaustion fallback. Useful as the node's declared model
  when Fable availability is uncertain; useless as an exhaustion guard.
* **`:526` — thinking cannot be turned off on Fable 5.** *"The session toggle,
  `alwaysThinkingEnabled`, and `MAX_THINKING_TOKENS=0` have no effect there, and Fable 5
  decides per step how much to think based on the effort level."* ⇒ **`/effort` is the ONLY
  spend dial on a Fable node.**
* **`:512`** — Fable 5, Sonnet 5, Opus 4.7+ always use adaptive reasoning; the fixed-budget
  mode and `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING` do not apply.
* **`:444` / `:450` — effort levels `low, medium, high, xhigh, max`; default `high`.**
* **`:452` — the model-default HOLD**: *"When you first run Fable 5 … Claude Code applies
  that model's default effort even if you previously set a different level for another
  model, and holds it across sessions until you make an explicit effort choice."*
  **`:456`: a non-interactive `/effort` CANNOT release the hold — it reports `Not applied`.
  Pass `--effort` at launch instead.** ⇒ **every headless Fable node must pass `--effort`
  explicitly**; a `/effort` in the prompt is a silent no-op.
* **`:458` — `max` is session-only** unless set via `CLAUDE_CODE_EFFORT_LEVEL`.
* **`:462` — `ultracode`** is `xhigh` + dynamic workflow orchestration, session-only;
  `CLAUDE_CODE_EFFORT_LEVEL` and the persisted `effortLevel` setting do **not** accept it,
  and a set `CLAUDE_CODE_EFFORT_LEVEL != xhigh` silently deactivates ultracode's
  orchestration.
* **`:76` — Fable 5 requires v2.1.170+, and is UNAVAILABLE under zero data retention**
  (picker omits or disables it).
* **`:532`/`:534`** — Fable 5 always runs the 1M window on the Anthropic API. `$CC/errors.md:343`:
  the 1M entitlement check is separate from quota and *"fires even when your session and
  weekly allowances have capacity remaining."*
* **`:178`** — when the auto-mode classifier's Sonnet 5 default is excluded and the session
  runs on **Fable 5**, the classifier runs on an **Opus** model. A Fable node therefore pays
  Opus for its own permission classifier.

---

## 5. The weekly-window fact, and the router's economics

`$CC/costs.md:128`, verbatim:

> **"You've hit your session limit" or "You've hit your weekly limit"**: a seat-based usage
> window on a subscription plan. **These windows are shared across all models, so switching
> models with `/model` doesn't restore access**, though it does keep the developer working
> after the model-specific "You've hit your Opus limit" message.

`$CC/errors.md:321-323`, second independent route:

> The session and weekly limits are shared across all models, so switching models doesn't
> restore access. The Opus limit applies only to Opus requests, so switching to another model
> with `/model` keeps you working.
>
> Usage counts against the session and weekly allowances **at the same time. A single burst
> of heavy activity, such as a large workflow fanout, can exhaust the weekly allowance before
> the session window resets.**

That last sentence names this framework's exact hazard by name. **An autonomous DAG *is* a
large fanout.**

Binary corroboration of the *shape*: the window schema has `five_hour`, `seven_day` (shared)
plus `seven_day_opus` / `seven_day_sonnet` (model-scoped) and **no `seven_day_fable`**.

### The router's economics, stated explicitly

| Fallback edge | Protects | Does **NOT** protect |
|---|---|---|
| **Fable → Opus 5** | the Fable **credit / spend-cap / seat-entitlement** allowance | the shared `five_hour` + `seven_day` windows — Opus draws the **same** meter, and additionally burns `seven_day_opus` |
| **Fable/Opus → Sonnet** | `seven_day_opus`; lowers the shared-window burn **rate** per unit of work | the shared windows themselves |
| **→ Codex (`codex exec`)** | **the shared windows entirely** — different vendor, different meter | nothing on the Anthropic side |
| **Wait for `resets_at`** | everything | throughput |

**Therefore, for the wayfinder DAG:**

1. **Fable→Opus fallback buys capability continuity, not headroom.** It keeps a node alive
   when the *Fable-specific* gate closes. It does nothing when the shared weekly window
   closes — at that point *every* Anthropic node in the DAG is dead simultaneously.
2. **The only lane that adds Anthropic-side headroom is the Codex second-vendor lane**
   already in the design. That makes Codex a **capacity** dependency, not merely a
   cross-family-review nicety. If the DAG's throughput target assumes N concurrent Anthropic
   nodes, that assumption is bounded by one shared weekly meter.
3. **Parallelism is the primary spend lever, not model choice.** `$CC/costs.md` attributes
   plan-limit burn to *"parallel sessions, subagents, cache misses, and long context"*
   (`whats-new__2026-w16.md:59`). A DAG that fans out 6 nodes burns the weekly window ~6× as
   fast regardless of which Claude model each one runs.
4. This corroborates the ledger row *"~78-85k tokens per agent spawned regardless of size"* —
   the fixed per-node cost multiplied by fan-out, against a single shared weekly meter, is
   the binding constraint on the whole design.

---

## 6. Concrete recommendations for the wayfinder DAG

**Per-node launch shape (Fable node):**

```bash
claude --bg --model fable --effort high --max-budget-usd <cap> "<task>"
```

* `--model fable` **explicitly, every launch** — Fable is never inherited (§4).
* `--effort` **at launch, not via `/effort`** — the model-default hold makes a
  non-interactive `/effort` a no-op (`$CC/model-config.md:456`).
* `--max-budget-usd` is a real hard cap and is in the respawn allowlist. ⚠️ `--help` labels it
  "(only works with --print)", which collides with `--bg` — **verify per node** (NEEDS-PROBE
  below).

**Project settings for every node** (`.claude/settings.json`):

```json
{
  "fallbackModel": ["opus", "sonnet"],
  "switchModelsOnFlag": true
}
```

* `fallbackModel` covers overload/unavailable/blocked. Remember it **replaces** rather than
  merges across scopes, and the chain is capped at 3.
* `switchModelsOnFlag: true` (the default) — `false` turns a bio/cyber flag into a **turn-ending
  refusal** in headless mode.
* **Do NOT set `CLAUDE_CODE_SUBAGENT_MODEL`** anywhere the DAG can see it — it overrides every
  per-node and per-subagent model decision including teammates.
* **Do NOT set `CLAUDE_CODE_NO_MODEL_FALLBACK`** unless a node must be Fable-or-fail; it
  disables *both* the availability chain and the Fable credit substitution.

**Detection (what the router watches), in priority order:**

1. `--output-format stream-json` `error` category: **`rate_limit`** (shared window or plan
   limit — HOLD the whole DAG until `resets_at`), **`overloaded`** (transient — the native
   chain already handled it), **`billing_error`** / **`model_not_found`** (config fault —
   escalate).
2. `type:"query_model_change"` and `subtype:"model_consent_fallback"` events — **a node was
   silently demoted off Fable.** Record it; the node is still alive but is no longer the model
   the DAG budgeted for.
3. The statusline `rate_limits.seven_day.used_percentage` — read it from the session JSON and
   **stop dispatching new nodes above a threshold**. This is the only proactive lever, and it
   is the right one: throttle fan-out, not model choice.
4. `resets_at` (Unix epoch) from `rate_limits.*` — the DAG's resume time.

**Do NOT build:** a bespoke Fable→Opus swapper. The harness's `model_fable_consent` path
already does it and persists its own latch; a competing swapper will fight it.

---

## NEEDS-PROBE (exact probes written out, none run)

1. **Does `--fallback-model` actually take effect outside `--print`?** `--help` says print-only;
   `$CC/model-config.md:363` shows it bare; `$CC/agent-view.md:408` says a backgrounded session
   carries it. I found the help string but **no enforcement code** gating it on print mode.
   *Probe:* `claude --debug-file /tmp/fb.log --fallback-model sonnet -p "hi"` vs the same
   without `-p` under a PTY, and grep the debug log for `fallbackModel` in the request context.
   Control arm: a run with no `--fallback-model` at all.
2. **Does `--max-budget-usd` apply to a `--bg` session?** Same help-label collision.
   *Probe:* `claude --bg --max-budget-usd 0.01 "count to 3"`, then
   `claude agents --json` and inspect whether the job records the flag; cross-check the
   `[jobs] stripped non-allowlisted respawnFlags` warning path (`--max-budget-usd` **is** in
   `Cce`, so it should survive).
3. **Does the `model_fable_consent` substitution fire headlessly?** This decides whether a
   Fable node self-heals or dies. Cannot be probed without exhausting credits. *Cheapest
   ethical proxy:* run a Fable node with `CLAUDE_CODE_NO_MODEL_FALLBACK=1` and confirm the
   tripwire/`model_error` copy appears, which at least proves the branch is reachable in that
   surface. Control arm: the same node without the var.
4. **Is `You've hit your Opus limit` server-supplied?** *Probe:* capture a real limit response's
   body with `--debug api` when one naturally occurs, and compare to the binary's local strings.

---

## Ledger entries to append to `.claude/agents/claude-code-expert.md`

| Claim | Verdict | Evidence | Ver | Date |
|---|---|---|---|---|
| **The `fallbackModel` chain EXCLUDES 429/rate-limit/billing** — it cannot carry quota-exhaustion fallback | CONFIRMED | docs `$CC/model-config.md:359` + binary `tR_=new Set([401,407,429,404,403,413])`; two routes | 2.1.222 | 2026-08-05 |
| **An UNDOCUMENTED `model_fable_consent` path DOES substitute off Fable on credit exhaustion** — `hVe()` walks Opus→Sonnet→Haiku under the model policy; emits `query_model_change` + `model_consent_fallback` | CONFIRMED | binary @246376864/@240965321; docs **0 of 174**, control `fallbackModel` → 8 | 2.1.222 | 2026-08-05 |
| **`CLAUDE_CODE_NO_MODEL_FALLBACK=true` disables BOTH mechanisms** and collapses the availability chain to `[primary]`, with a throwing tripwire | CONFIRMED | binary `yIe()`/`iJr()`; 0 doc hits | 2.1.222 | 2026-08-05 |
| **There is no `seven_day_fable` bucket** — Fable draws the SHARED weekly window; Opus/Sonnet have their own sub-buckets | CONFIRMED | binary: probe 0, control `seven_day_opus` → 15 | 2.1.222 | 2026-08-05 |
| **No pre-flight quota API exists** — `rate_limits` appears in statusline JSON only AFTER the first API response, and `/usage` is a ≤60-min-old LOCAL cache | CONFIRMED | `$CC/statusline.md:762`, `$CC/costs.md:36,38` | 2.1.222 | 2026-08-05 |
| The doc-promised literal `You've hit your Opus limit` is **absent from the binary** (shape probe finds 9 other limit strings, none Opus) | SUSPECT | binary only; control `zzqjjxwv9pl` → 0 | 2.1.222 | 2026-08-05 |
| **`--bg` and `--print` are mutually exclusive** (hard error since v2.1.198), while `--help` labels `--fallback-model` and `--max-budget-usd` "only works with --print" — a real collision for durable background nodes | CONFIRMED | `$CC/errors.md:1191`; `claude --help` | 2.1.222 | 2026-08-05 |
| **`CLAUDE_CODE_SUBAGENT_MODEL` overrides per-invocation `model` AND frontmatter, for subagents, workflow agents AND teammates** — setting it destroys all per-node routing | CONFIRMED | `$CC/sub-agents.md:306`, `model-config.md:607`, `changelog.md:1447` | 2.1.222 | 2026-08-05 |
| A subagent whose model is excluded by `availableModels` is **silently run on the inherited model**, not failed | CONFIRMED | `$CC/sub-agents.md:313` | 2.1.222 | 2026-08-05 |
| **A non-interactive `/effort` cannot release the Fable model-default effort HOLD** — it reports `Not applied`; `--effort` must be passed at launch | CONFIRMED | `$CC/model-config.md:456` | 2.1.222 | 2026-08-05 |
| **Thinking cannot be disabled on Fable 5** — session toggle, `alwaysThinkingEnabled` and `MAX_THINKING_TOKENS=0` all no-op; `/effort` is the only spend dial | CONFIRMED | `$CC/model-config.md:526` | 2.1.222 | 2026-08-05 |
| **Fable 5 is never a default on any account type**, and choosing it with `/model` writes it into USER settings, contaminating later sessions | CONFIRMED | `$CC/model-config.md:338` | 2.1.222 | 2026-08-05 |
| Content-classifier fallback (bio→Opus 5, cyber→Opus 4.8) is **sticky for the session** and, with `switchModelsOnFlag:false`, **ends a headless turn in a refusal** | CONFIRMED | `$CC/model-config.md:397, 417` | 2.1.222 | 2026-08-05 |
| Org **effort caps clamp SILENTLY in background agents** and under json/stream-json output | CONFIRMED | `$CC/model-config.md:315` | 2.1.222 | 2026-08-05 |
| `fallbackModel` arrays **REPLACE** across settings scopes (every other array setting unions) | CONFIRMED | binary `gae()` @239909258 | 2.1.222 | 2026-08-05 |
| A background job's respawn flags are **allowlist-filtered** (`Cce`); non-listed flags are stripped with a `[jobs] stripped non-allowlisted respawnFlags` warning. `--model`, `--effort`, `--fallback-model`, `--max-budget-usd`, `--task-budget` are all IN the list | CONFIRMED | binary @246144430 | 2.1.222 | 2026-08-05 |
| Headless `--output-format json` exposes a **structured `error` category** (`rate_limit` / `overloaded` / `billing_error` / `model_not_found` / …) — key the router on this, never on prose | CONFIRMED | `$CC/headless.md:191` | 2.1.222 | 2026-08-05 |

---

## GitHub repos touched

- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the offline `agent-harness-docs/docs/claude-code` corpus (174 pages) that supplied every `$CC/*` citation.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo; `graphify query` orientation over existing Fable/Opus orchestrator research reports, and the report's destination.

_No third-party repository source or docs were read; the binary is a locally installed artifact, not a repo._
