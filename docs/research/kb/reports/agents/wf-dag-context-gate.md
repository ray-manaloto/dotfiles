# Claude Code expertise — context-usage gate for durable DAG nodes (2026-08-05, v2.1.222)

`claude --version` → `2.1.222 (Claude Code)`

Corpora consulted: installed binary (`/Users/rmanaloto/.local/share/claude/versions/2.1.222`,
271,289,792 bytes, Mach-O 64-bit arm64) / `claude --help` / offline docs (`$CC`, 175 pages)
/ live probes on this host (205 transcripts) / repo prior art.

`$CC` = `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`

| # | Verdict | Claim | Corpus + control arm |
|---|---|---|---|
| 1 | **CONFIRMED** | **No hook event receives context utilization.** The common hook input base is exactly 8 fields: `{session_id, transcript_path, cwd, prompt_id, permission_mode, agent_id, agent_type, effort}` | binary `function $m(e,t,r)`, enumerated by SHAPE over all 64 `hook_event_name:` construction sites; control = the statusline builder `rRT` in the SAME binary DOES spread `context_window` |
| 2 | **CONFIRMED** | The **status line** is the only harness surface handed a pre-computed `context_window.used_percentage`, and it is a **sensor only** — nothing reads a decision from its stdout | `$CC/statusline.md:185`; binary `tRT`/`rRT` |
| 3 | **CONFIRMED** | `PreCompact` **can block** compaction (exit 2 / `"decision":"block"`), and its matcher separates `manual` from `auto` | `$CC/hooks.md:2742-2755`; binary `$we` builder |
| 4 | **CONFIRMED** | The auto-compact trigger is **exactly** `min(window − round(window×buffer), min(floor(window×pct/100), window−13000))`. `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=30` on a 200K window puts the trigger at **60,000 tokens = 30%** | binary `FTo`/`ISs` verbatim; docs `$CC/env-vars.md:189` |
| 5 | **CONFIRMED** | The `Math.min` in `FTo` is *why* the override can only lower, never raise — the code, not just the prose | binary `FTo` |
| 6 | **CONFIRMED** | A live transcript carries every token needed to compute utilization; measured **263,184** input-side tokens on this host's newest transcript | live probe; 3-way control arm (long file → number, 149-byte file → `None`, missing path → error) |
| 7 | **CONFIRMED** | The transcript's `compactMetadata` is far richer than the one documented field: `{trigger, preTokens, postTokens, cumulativeDroppedTokens, durationMs, preservedSegment, preservedMessages}`. **3 of those are 0-of-175 in docs** | live transcript dump; binary 51/17/7/14; control `wfdagNoSuchToken91` → 0 both corpora |
| 8 | **CONFIRMED** | `SessionStart` `hookSpecificOutput.initialUserMessage` **creates the first turn of a `-p` session even with no prompt** — the native restart-injection point | `$CC/hooks.md` SessionStart decision control; binary 23 |
| 9 | **CONFIRMED (new)** | **`claude respawn <id>\|--all` exists** as a hidden root subcommand — but it restarts *with the conversation intact*, so it is **not** a context-resetting restart | live `claude respawn --help`; control: `claude wfdagbogus --help` falls through to root help |
| 10 | **REFUTES A LEDGER ROW** | **`claude attach <id>` DOES exist at 2.1.222.** The ledger says it does not. That row's probe was bounded to the *visible* `--help` list; `attach` is hidden | live `claude attach --help` → `Usage: claude attach <id>`; control `claude peek --help` → falls through to root help |
| 11 | **NEEDS-PROBE** | Setting the auto-compact window **below 200,000** hits a `if(a<XPe) return !1` branch (`XPe=200000`) in `yFu`, whose semantics I did not settle. Prefer window=200000 + `PCT_OVERRIDE` over shrinking the window | binary `yFu` |

---

## 1. How a running session can MEASURE its own context utilization

### 1a. Status-line input JSON — the only pre-computed surface

`$CC/statusline.md:167-209` enumerates every field the harness writes to the status-line
command's **stdin**. Context-relevant rows, verbatim:

| Field | Anchor | Meaning |
|---|---|---|
| `context_window.total_input_tokens`, `.total_output_tokens` | `$CC/statusline.md:183` | Tokens **currently in the context window**, from the most recent API response. Input includes cache reads and writes. *Before v2.1.132 these were cumulative session totals* — do not copy an old recipe. |
| `context_window.context_window_size` | `:184` | Max window in tokens. `200000` default, `1000000` for extended-context models. |
| `context_window.used_percentage` | `:185` | **Pre-calculated % of context used.** |
| `context_window.remaining_percentage` | `:186` | Pre-calculated % remaining. |
| `context_window.current_usage` | `:187` | `{input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens}` from the last API call. |
| `exceeds_200k_tokens` | `:188` | Boolean at a **fixed 200k threshold regardless of the actual window size**. Useless for a 30% gate. |
| `transcript_path` | `:197` | Path to the conversation transcript JSONL. |
| `session_id` | `:194` | Session identifier. |

Binary confirmation (verbatim from the installed 2.1.222):

```js
function tRT(e,t){let r=NXo(e,t);return{
  total_input_tokens: e ? e.input_tokens+e.cache_creation_input_tokens+e.cache_read_input_tokens : 0,
  total_output_tokens: e?.output_tokens??0,
  context_window_size: t,
  current_usage: e,
  used_percentage: r.used,
  remaining_percentage: r.remaining}}
```

and the payload assembler
`rRT({permissionMode, exceeds200kTokens, fastMode, settings, messages, addedDirs,
mainLoopModel, gitWorktree, repo, prStatus, vimMode, cwd, effortValue, thinkingEnabled})`
returning `{...$m(), cwd, ...session_name, model, workspace, version, …}`.

**Three hazards that break a naive gate:**

1. `used_percentage` is **input-tokens-only**:
   `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`, excluding
   `output_tokens` (`$CC/statusline.md:335`). Match that formula or your number disagrees
   with the harness's.
2. `current_usage` is `null` **before the first API call** and again **after `/compact`
   until the next API call** (`:313`, `:339`); `used_percentage` / `remaining_percentage`
   "may be `null` early in the session" (`:314`). A gate that coerces `null`→`0` never
   fires; one that coerces `null`→`100` fires at startup. Treat it as three-state.
3. ⚠️ **Setting `CLAUDE_CODE_AUTO_COMPACT_WINDOW` desynchronises the two numbers.**
   `$CC/env-vars.md:201`, verbatim: *"The status line's `used_percentage` always measures
   against the model's full context window, so once this variable is set, that percentage
   no longer indicates when compaction will run."* Different denominators.

### 1b. What the status line can and cannot do

It runs an arbitrary command with the JSON on stdin, **locally, consuming no API tokens**
(`$CC/statusline.md:165`). So it is a legitimate **sensor** — it can write
`used_percentage` to a file every tick. It is **not an actuator**: its stdout is rendered
as UI text and nothing in the harness reads a decision out of it.

Refresh behaviour matters for an unattended node: updates are **event-driven, debounced
at 300 ms**, an in-flight script is **cancelled** when a new update arrives
(`:151`), and — critically —

> "The event-driven triggers can go quiet when the main session is idle, for example
> **while a coordinator waits on background subagents**." — `$CC/statusline.md:153`

That is exactly the DAG-node situation. The documented fix is `refreshInterval`, which
also re-runs the command on a fixed timer. **Any status-line-based sensor in this design
MUST set `refreshInterval` or it will go blind during the node's longest phases.**

### 1c. Hook events get NO context utilization — CONFIRMED, enumerated by SHAPE

I did not grep for the fields I expected (that is how 18 of 29 hook events were once
missed). I enumerated every hook-payload construction site by its **shape** — a
`hook_event_name:` key immediately following a spread — **64 hits** in the binary. Every
one has the identical form:

```js
{...$m(<permissionMode>, <sessionId>, <toolUseContext>), hook_event_name:"<Event>", …event-specific…}
```

Verbatim samples:

```js
let u={...$m(o,void 0,n),hook_event_name:"PreToolUse",tool_name:e,tool_input:r,tool_use_id:t};
let c={...$m(i,void 0,o),hook_event_name:"PostToolUse",tool_name:e,tool_input:r,tool_response:n,tool_use_id:t,duration_ms:l};
let p={...$m(s,void 0,o),hook_event_name:"PostToolUseFailure",…};
let n={...$m(void 0),hook_event_name:"PreCompact",trigger:e.trigger,custom_instructions:e.customInstructions};
let n={...$m(void 0),hook_event_name:"PostCompact",trigger:e.trigger,compact_summary:e.compactSummary};
let n={...$m(void 0),hook_event_name:"ConfigChange",source:e,file_path:t};
let l={...$m(void 0),hook_event_name:"InstructionsLoaded",file_path:e,memory_type:t,…};
```

So the question reduces entirely to `$m()`. Verbatim:

```js
function $m(e,t,r){
  let n=t??Ot(), o=r?.agentType??nU(), i=r?.options?.mainLoopModel, s=r?.getAppState?.().effortValue;
  for(let l of r?.permissionLayers??[]) if(l.kind==="effort"&&l.effort!==void 0) s=l.effort;
  let a = i&&r?.getAppState&&EO(i) ? {level:Wq(i,s)} : void 0;
  return {session_id:n, transcript_path:jH(n), cwd:Mt(), prompt_id:YPt()??void 0,
          permission_mode:e, agent_id:r?.agentId, agent_type:o, effort:a};
}
```

**Eight fields. No `context_window`, no token count, no percentage, no window size.**

**Control arm, same binary, same probe shape:** `context_window` → **21** occurrences and
the status-line assembler demonstrably spreads it, so the byte-scan *can* see the token —
it simply is not in the hook base. Known-absent controls invented fresh for this run:
`wfdagNoSuchToken91` → **0**, `QqZzVv7Fresh` → **0**, `ContextGateXyzzy` → **0**.

> **Design consequence: a hook cannot read context utilization from its own stdin at this
> version.** Any hook-based gate must (a) derive the number from `transcript_path`
> itself (§1d), or (b) read it out of a file the status line wrote (§1b), or (c) let the
> harness's own threshold fire `PreCompact` (§2, §4).

*Undocumented bonus from the same function:* every hook payload carries `agent_id`,
`agent_type`, `prompt_id` and `permission_mode`. A DAG node's hooks can therefore
identify which node they are running inside with no extra plumbing.

### 1d. Transcript-derived token counts — the route a hook actually has (LIVE PROBE)

Every hook payload carries `transcript_path`. I enumerated the transcript record shape by
SHAPE (all top-level keys, all `message.usage` keys) over the newest transcript on this
host — 321 records, 961,285 bytes:

```
types:  {'custom-title':19,'mode':18,'file-history-snapshot':4,'attachment':105,'user':56,
         'system':3,'last-prompt':17,'assistant':89,'file-history-delta':2,'frame-link':2,'agent-name':6}
usage keys (89 records): input_tokens, cache_creation_input_tokens, cache_read_input_tokens,
         output_tokens, server_tool_use, service_tier, cache_creation, inference_geo, iterations, speed
LAST usage: {"input_tokens":2,"cache_creation_input_tokens":463,"cache_read_input_tokens":262719,
             "output_tokens":166, …}
```

So the computation a hook can run:

```
used = usage.input_tokens + usage.cache_creation_input_tokens + usage.cache_read_input_tokens
pct  = 100 * used / <context_window_size>
```

taking the **last** record with a `message.usage` block. This reproduces the harness's own
formula (`$CC/statusline.md:335`).

**Control arm (3-way, so the probe demonstrably discriminates):**

| Arm | Input | Result |
|---|---|---|
| A — long live session | newest transcript, 961,285 B | `(263184, 'claude-fable-5')` |
| B — trivial sessions | the 6 smallest transcripts (149 B … 3,532 B) | `(None, None)` — correctly "no data", **not** `0` |
| C — absent file | `/tmp/no-such-transcript-vhqz41.jsonl` | `ERR [Errno 2] No such file or directory` |

⚠️ **The denominator is NOT in the transcript.** There is no `context_window_size` field.
`message.model` *is* present (`claude-fable-5` above), so a hook must maintain its own
model→window map — and that map drifts (200K vs 1M vs `[1m]` variants vs Sonnet 5's
implicit 1M vs the 200K Bedrock/GCP/Foundry configurations, `$CC/context-window.md:1634`).
**This is the single weakest link in a transcript-derived gate**, and it is why the
status-line sensor (which is handed `context_window_size` directly) is the better source
for the denominator even if a hook does the arithmetic.

⚠️ Also, from `$CC/hooks.md` Stop input: *"the transcript file isn't guaranteed to include
the final message at Stop time on all versions."* A Stop-hook reader can be one turn stale.

### 1e. `compact_boundary` / `preTokens` — a tripwire, not a gate

Docs give one field (`$CC/sub-agents.md:985-993`: `"subtype":"compact_boundary"`,
`"preTokens":167189`). **The real on-disk record is much richer.** Verbatim from a
transcript on this host:

```json
{"type":"system","subtype":"compact_boundary","content":"Conversation compacted","level":"info",
 "compactMetadata":{
   "trigger":"manual","preTokens":310973,"postTokens":14517,
   "cumulativeDroppedTokens":296456,"durationMs":109064,
   "preservedSegment":{"headUuid":"…","anchorUuid":"…","tailUuid":"…"},
   "preservedMessages":{"anchorUuid":"…","uuids":[…5 uuids…],"allUuids":[…]}}}
```

Doc-vs-binary, control-armed:

| Token | Doc pages (of 175) | Binary |
|---|---:|---:|
| `preTokens` | 1 | 14 |
| `compactMetadata` | 1 | 51 |
| `postTokens` | **0** | 17 |
| `cumulativeDroppedTokens` | **0** | 7 |
| `preservedSegment` | **0** | 14 |
| `wfdagNoSuchToken91` *(control)* | 0 | 0 |

Empirically: **7 of 205 transcripts** on this host contain a `compact_boundary`
(control: 192 of 205 contain `"assistant"`, so the file-scan works).

This is a **post-hoc** signal — by the time it exists, compaction already happened. It is
a fine *tripwire* ("this node blew its budget; the gate failed") and a fine metric
(`296,456` tokens dropped in that one event), but it cannot be the gate itself.

### 1f. `/context`

`$CC/context-window.md:1639`: *"To see your actual context usage at any point, run
`/context` for a live breakdown by category with optimization suggestions."* It renders to
the interactive UI. **NEEDS-PROBE** whether it yields machine-readable output under `-p`;
I did not spend a live `-p` run on it because §1a/§1d already give the number by two
independent routes.

---

## 2. Native auto-compact machinery, and why restart-from-file bypasses it

### 2a. Full knob enumeration (each byte-scanned in the binary)

| Knob | Kind | Doc anchor | Binary | Semantics |
|---|---|---|---:|---|
| `autoCompactEnabled` | setting | `$CC/settings.md:234` | 21 | Default `true`. `/config` → **Auto-compact**. |
| `autoCompactWindow` | setting | `$CC/settings.md:235` | 57 | Window in **tokens, 100000–1000000**. Unset ⇒ model-tuned. |
| `DISABLE_AUTO_COMPACT` | env | `$CC/env-vars.md:368` | 6 | `1` disables auto-compaction; **overrides `autoCompactEnabled`**. `/compact` stays available. |
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | env | `$CC/env-vars.md:201` | 17 | Window in tokens, **plain integer only** (`500k` parses as `500` → clamped to the 100K min). **Highest precedence.** |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | env | `$CC/env-vars.md:189` | 6 | Percentage **1-100** of the window at which compaction triggers. **Lower-only.** Applies to **subagents too**. |
| `--autocompact <auto\|tokens>` | CLI flag | `$CC/cli-reference.md:67` | — | Per-launch window; **v2.1.221+** (we are on 2.1.222 — confirmed present in `claude --help:27`). Not preempted by managed settings. |
| `/autocompact` | slash cmd | `$CC/context-window.md:1619` | — | Writes `autoCompactWindow` to **user** settings. |
| `DISABLE_COMPACT` | env | 3 pages | 15 | Hard off — checked *first* in the gate function. |
| `CLAUDE_CODE_MAX_CONTEXT_TOKENS` | env | 2 pages | 7 | Caps the model window. |
| `CLAUDE_CODE_BLOCKING_LIMIT_OVERRIDE` | env | **0 pages** | 3 | **Undocumented.** Overrides the hard "blocked" limit. |
| `CLAUDE_AFTER_LAST_COMPACT` | env | **0 pages** | 3 | **Undocumented.** |
| `PreCompact` / `PostCompact` | hooks | `$CC/hooks.md:2742`, `:2772` | 45 / 47 | §4. |

Precedence, `$CC/context-window.md:1619-1621` — and the binary agrees exactly. `qX()`,
verbatim resolution order:

```js
function qX(e,t){ // e = model, t = settings window
  …
  if(process.env.CLAUDE_CODE_AUTO_COMPACT_WINDOW){ …clamp to [BTo,DSs]… return {…, source:"env"} }
  if(t!==void 0) return {window:Math.min(o,t), configured:t, source:"settings"};
  let i=aP_(r); if(i.window!==null) return {…, source:"clientdata"};   // remote gate `rowan_thicket`
  let s=HSs(r); if(s!==void 0)      return {…, source:"experiment"};   // remote experiment
  if(o<1e6&&(sP_.has(r)||NSs(e,n))) return {window:Math.min(o,XPe), configured:XPe, source:"model-default"};
  let a=i.replacesDefault?void 0:iP_(r); if(a!==void 0) return {…, source:"model-default"};
  return {window:o, configured:o, source:"auto"};
}
var BTo=1e5, DSs=1e6, XPe=200000;
```

⚠️ **Two of the seven resolution steps are undocumented remote gates**
(`clientdata` / `rowan_thicket`, and `experiment`). A window you did not set can be
imposed remotely. Pin it explicitly if the design depends on it.

### 2b. The threshold arithmetic — exact, from the binary

```js
var aFu=13000, hFu=20000;
function FTo(e,t){                       // e = effective window, t.testPctOverride = PCT_OVERRIDE
  let r = e - 13000;
  let n = t.testPctOverride;
  if (n !== undefined && !isNaN(n) && n > 0 && n <= 100)
      return Math.min(Math.floor(e*(n/100)), r);
  return r;
}
function ISs(e,t){ return Math.min(e - Math.round(e*t.precomputeBufferFraction), FTo(e,t)); }
function EEe(e,t){ let r=Math.min(Vpr(e), hFu); let {window:o}=qX(e,…); return o - r; }  // reserve output tokens
function dFu(e,t,r,n=t){
  let o=FTo(t,r), i=r.enabled?o:t, s=i-20000,
      l=(r.testBlockingOverride>0)?r.testBlockingOverride:n-3000,
      c=Math.max(0,Math.round((i-e)/i*100));
  if(e>=l)            return {level:"blocked", pctLeft:c};
  if(r.enabled&&e>=o) return {level:"compact", pctLeft:c};
  if(e>=s)            return {level:"warn",    pctLeft:c};
  return {level:"ok"};
}
function DO(){                            // "is auto-compact enabled"
  if(te.DISABLE_COMPACT) return false;
  if(tr(process.env.DISABLE_AUTO_COMPACT)) return false;
  return hu("autoCompactEnabled", true).value;
}
function LSs(e,t,r){ return {enabled:DO(), precomputeBufferFraction:dP_(e,t,r),
  testPctOverride: process.env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE ? parseFloat(…) : undefined,
  testBlockingOverride: process.env.CLAUDE_CODE_BLOCKING_LIMIT_OVERRIDE ? wp(…) : undefined}; }
```

**`Math.min` in `FTo` is the mechanism behind "the variable can't raise the threshold"** —
this is the code, not a paraphrase of the docs.

Worked numbers for a 200K-window model, `precomputeBufferFraction` default `xSs = 0.2`,
max-output reserve capped at `hFu = 20000`:

| `PCT_OVERRIDE` | effective window `EEe` | `FTo` | `ISs` (trigger) | ≈ % of 200K |
|---:|---:|---:|---:|---:|
| unset | 180,000 | 167,000 | min(144,000, 167,000) = **144,000** | 72% |
| `50` | 180,000 | min(90,000, 167,000) = 90,000 | **90,000** | 45% |
| **`30`** | 180,000 | min(54,000, 167,000) = 54,000 | **54,000** | **27%** |
| `35` | 180,000 | 63,000 | **63,000** | 31.5% |

**So `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=33` lands the native trigger at almost exactly the
user's ~30% mark**, and it is the *only* native knob that fires an event at a percentage
you choose. Gate design B in §5 is built on it.

Two caveats, stated so they can be attacked:

- ⚠️ **`enabled` is not a remote gate here.** `DO()` is `!DISABLE_COMPACT && !DISABLE_AUTO_COMPACT
  && autoCompactEnabled(default true)`. So the pct override is live by default. Good news,
  and it contradicts a plausible reading of the doc caveat ("applies only in sessions that
  compact before the model's context limit") — that caveat maps to `MKe()` (`source !== "auto"`),
  which is about which *window* is used, not whether the pct applies inside `FTo`. **SUSPECT
  on the doc's phrasing; CONFIRMED on the code.** Verify in a live run before shipping.
- ⚠️ **NEEDS-PROBE — do not shrink the window below 200,000.** `yFu` contains
  `let {window:a}=qX(t,i); if(a<XPe) return !1;` with `XPe=200000`. I did not settle what
  `yFu` decides, but a configured window under 200K takes a hard `false` branch there.
  **Prefer window = 200000 (or leave it model-default) and move the trigger with
  `PCT_OVERRIDE`.** Probe: launch two `-p` sessions, one at
  `CLAUDE_CODE_AUTO_COMPACT_WINDOW=100000` and one at `200000`, both with
  `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=30`, feed each ~70K tokens of file reads, and check
  which emits a `compact_boundary` record.

### 2c. Why the restart-from-file design deliberately bypasses this

What compaction actually loses, `$CC/context-window.md:1584-1600`:

| Mechanism | After compaction |
|---|---|
| System prompt and output style | Unchanged |
| Project-root CLAUDE.md and unscoped rules | Re-injected from disk |
| Auto memory | Re-injected from disk |
| **Rules with `paths:` frontmatter** | **Lost until a matching file is read again** |
| **Nested CLAUDE.md in subdirectories** | **Lost until a file in that subdirectory is read again** |
| Invoked skill bodies | Re-injected, capped 5,000 tok/skill, 25,000 total, oldest dropped first |
| Hooks | N/A — hooks run as code, not context |

Plus, from the timeline data at `$CC/context-window.md:47` (the skill-descriptions event
carries `noSurviveCompact: true`): *"Unlike the rest of the startup content, this listing
is **not re-injected after `/compact`**. Only skills you actually invoked get preserved."*

So a compacted node is a node whose **skill catalogue has silently shrunk** and whose
`paths:`-scoped rules have silently unloaded. It keeps running and looks fine. In *this*
repo that means `md-size-budgets.md` and every other scoped rule quietly leave context
mid-node.

Four reasons the restart design is right, stated so the caller can attack each:

1. **Compaction is lossy in a way you cannot audit.** A summariser decides what survives.
   A durable file is written by the node, reviewable, diffable, re-readable.
2. **Skills and `paths:` rules do not survive** — silent capability decay in an
   unattended node.
3. **It is nondeterministic and can thrash** — *"If a single file or tool output is so
   large that context refills immediately after each summary, Claude Code stops
   auto-compacting after a few attempts and shows an error instead of looping"*
   (`$CC/how-claude-code-works.md:133`).
4. **This repo already ruled on it** — memory `feedback_no_compact`: *"never /compact;
   resume file + /clear"*, and `.claude/skills/clear-prep/SKILL.md` is that rule's worked
   procedure. The DAG design is clear-prep scaled from a human session to an autonomous
   node.

### 2d. ⚠️ The counter-argument the design must answer (this is the real finding)

Auto-compaction is *free*: zero engineering, zero restart latency, and it never loses the
tail that fits. A restart pays a **full cold start every hop**. Measured on this host and
already in the ledger: **~78–85k tokens per agent spawned** (2026-08-04c), against a 30%
gate that on a 200K window fires at **~54,000 tokens**.

**Those numbers do not fit.** If a node's cold start is anywhere near 54K, a 30%-of-200K
gate spends its entire budget re-orienting and never does work. The gate is only viable
if at least one of these holds:

- the node runs on a **1M-context model**, where 30% = 300,000 tokens and an 80K cold
  start is 27% of the hop rather than 150% of it; **or**
- the "~30%" is measured **against the hop's own working budget** rather than the raw
  window; **or**
- the durable context file plus the node's system prompt is genuinely small (a few
  thousand tokens) and the 78–85k figure was dominated by things a lean node avoids.

**Recommendation to the caller: re-derive the cold-start cost for the actual node shape
before fixing 30% as the number.** Do not inherit 78–85k as a measurement — it is an
inherited figure from a different agent shape, and repeating it without re-derivation is
exactly what `probes-need-a-control-arm.md` rule 6 forbids. The mechanics in this report
work at any threshold; the threshold itself is an unsettled empirical question.

---

## 3. The restart mechanic — what a fresh run can be handed

### 3a. What a fresh `claude -p` inherits automatically vs what must be in the file

| Thing | Survives a fresh `claude -p` automatically? | Why / how |
|---|---|---|
| System prompt | ✅ | Rebuilt |
| Project `CLAUDE.md` + `@import` closure | ✅ | Read from disk at launch |
| `.claude/rules/*.md` (unscoped) | ✅ | Loaded at launch |
| `.claude/rules/*.md` with `paths:` | ⚠️ **only when a matching file is read** | Same as after compaction — but at least deterministic |
| Auto memory `MEMORY.md` | ✅ | Read from disk |
| Skill **descriptions** | ✅ | Re-scanned — **and this is the thing compaction destroys**, so a restart is strictly better here |
| `.claude/settings.json` (incl. its `env` block, hooks, permissions) | ✅ | Read from disk |
| `CLAUDE_CODE_TASK_LIST_ID` DAG (tasks, `blocks`/`blockedBy` edges) | ✅ **if the id is set** | Ledger, CONFIRMED 2026-08-05: persistent, file-locked, cross-session |
| Team roster / agent name registry | ✅ *for a teammate launch* | Ledger: the roster is injected into the agent's prompt |
| **Conversation history** | ❌ **by design** | That is the point |
| **What the node decided, tried, and rejected** | ❌ | **MUST be in the durable file** |
| **Which ticket/subtask it is on and why** | ❌ | Task list holds the *what*; the file holds the *why* |
| Exported shell `CLAUDE_*` vars | ⚠️ **NO, in `exec` background mode** | Ledger: the child's env is stripped of every `CLAUDE_*` except `CLAUDE_JOB_DIR`, `CLAUDE_CONFIG_DIR`, `CLAUDE_BG_PTY_AUTH` |

> ⚠️ **The single most important operational consequence:**
> **`CLAUDE_CODE_TASK_LIST_ID`, `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` and every other
> `CLAUDE_*` pin MUST live in the project `.claude/settings.json` `env` block, never in an
> exported shell variable** — otherwise the restarted node loses its DAG identity and its
> gate at the same moment. (Ledger, CONFIRMED; and settings `env` assigns *onto*
> `process.env`, so settings beat the shell.)

### 3b. `--resume` / `--continue` / `--fork-session` are the WRONG tool here

All three **restore the conversation**, which is the thing the gate exists to discard:

- `--resume, -r` — "Resume a specific session by ID or name" (`$CC/cli-reference.md:116`)
- `--continue, -c` — "Load the most recent conversation in the current directory" (`:75`)
- `--fork-session` — "When resuming, create a new session ID instead of reusing the
  original" (`:87`) — a *new id* over the *same history*.

Same for **`claude respawn <id>|--all`**, which I confirmed exists as a hidden root
subcommand (live probe; control `claude wfdagbogus --help` falls through to root help):
`Restart a background session (or all of them) so it picks up the current Claude binary`,
and `$CC/agent-view.md:597`: *"Restart a session, running or stopped, **with its
conversation intact**"*. **Not a context reset.**

**The correct restart is a NEW session** — `claude -p` (or `claude --bg`) with a fresh
session id — handed the durable file. `--session-id <uuid>` (`:118`) lets the DAG assign
the successor's id deterministically, which matters if edges are addressed by session.

### 3c. The four native channels for handing state to the fresh run

Ranked by how much they cost and how reliably they land:

1. **The prompt itself** — `claude -p "Read and follow <path-to-durable-file>"`. This is
   exactly the `clear-prep` step-6 pattern (`.claude/skills/clear-prep/SKILL.md:210-231`):
   *"The resume prompt is therefore a **one-line pointer**, nothing more. Do NOT inline
   the task plan, issue summaries, gotchas, preload lists, or gate commands — those are
   all in the handoff; duplicating them in the prompt is the failure mode this skill
   exists to prevent."* **Adopt that verbatim.** It is the framework's cheapest, most
   proven channel.
2. **`SessionStart` hook → `hookSpecificOutput.initialUserMessage`** — from
   `$CC/hooks.md`, verbatim: *"String used as the first user message of the session.
   Applies in **non-interactive mode with the `-p` flag, where it becomes the first turn
   even if no prompt is provided**. If a prompt is provided, it follows as the next turn.
   Unlike `additionalContext`, which attaches to an existing turn, this creates the
   turn."* Binary count 23; docs 2 pages. **This lets the framework inject the resume
   pointer with no prompt argument at all** — a node's launcher becomes `claude -p --bg`
   and the hook decides what it resumes from. Strictly more robust than a shell-quoted
   prompt.
3. **`SessionStart` hook → `additionalContext`** — plain stdout also works for this
   event (`$CC/hooks.md:746`). Use for small, always-true facts (node id, team name,
   ticket number). Do **not** dump the whole state file here — it enters context
   untruncated on **every** session start including `compact` and `clear`.
4. **`--append-system-prompt-file`** (`$CC/cli-reference.md:66`) — for the node's *role*,
   which does not change between hops. Keep the *state* out of it; a system prompt is not
   a place to put a mutable file.

Plus two supporting fields worth knowing:

- **`sessionTitle`** — name the successor session from the ticket, so `claude agents` and
  `claude --resume <name>` can find it. Applies on `startup`/`resume`/`fork`, ignored on
  `clear`/`compact`.
- **`CLAUDE_ENV_FILE`** — SessionStart hooks get a file path where they can persist env
  vars for subsequent Bash commands (binary 10, docs 6 pages).
- **`reloadSkills: true`** — re-scan skill dirs after SessionStart completes, if the node
  writes skills.

### 3d. What the durable context file should contain

Generalise what already works in this repo. `.claude/skills/clear-prep/SKILL.md:157-166`
already specifies the shape and the test:

> "The handoff must be **self-sufficient** — the resume prompt (step 5) only points here,
> so *everything the next session needs lives in this file*. Include: **State at handoff**
> (branch/PR/merge state, gate results), **what shipped**, **next task + preload
> pointers** (epic/issue/spec links), and **gotchas**."

and its acceptance test (`:34-37`):

> "if I `/clear` right now and only have MEMORY.md + the handoff + the research artifacts,
> can the next session continue with no gaps?"

For a DAG node, the same file plus four machine fields:

| Section | Human/machine | Why |
|---|---|---|
| `node_id`, `ticket`, `task_list_id`, `attempt` | machine | Re-addressable; `attempt` drives the retry cap |
| Phase + exit criterion | machine | The escalation gate needs a testable condition |
| State at handoff (branch, PR, gate `rc`s) | both | clear-prep §1 |
| Decisions made, with the evidence | human | The part compaction destroys |
| **Dead ends explored** | human | Otherwise the successor re-walks them and the DAG livelocks |
| Preload pointers (paths, issue refs) | both | Cheaper than inlining |
| Open questions / escalation triggers hit | both | Feeds the dynamic escalation gate |

⚠️ **Note the difference from clear-prep**: its handoff lives in `.agent/plans/`, which is
**gitignored**. For a DAG whose nodes may run in different worktrees or be inspected after
the fact, put the durable node file somewhere **tracked** (`docs/research/kb/…` or a
tracked `docs/` path), per `.claude/rules/agent-artifact-conventions.md`. A gitignored
state file is invisible to a reviewer and dies with a `git clean -xdf`.

---

## 4. Which hook events could ENFORCE the gate

**No hook can read context utilization from its input** (§1c). So "enforce" splits into
*detect* and *act*, and only some hooks can act.

| Event | Sees `transcript_path` | Can block | Fires when | Verdict as a gate |
|---|:---:|:---:|---|---|
| **`PreCompact` (matcher `auto`)** | ✅ | ✅ **exit 2 / `"decision":"block"`** | Exactly at the (movable) auto-compact threshold | ⭐ **The only native "we hit N%" event.** |
| **`Stop`** | ✅ | ✅ (block ⇒ Claude continues) | End of every assistant turn | ⭐ Best *polling* point; see caps below |
| `PreToolUse` | ✅ | ✅ (deny the tool) | Every tool call | High frequency ⇒ high overhead; blunt |
| `PostToolUse` | ✅ | ❌ (tool already ran) | After every tool call | Sensor only |
| `SessionStart` | ✅ | ❌ | Session begin/resume/clear/compact/fork | The **restart injection** point, not the gate |
| `SessionEnd` | ✅ | ❌ | Session end | Post-mortem only |
| `PostCompact` | ✅ | ❌ (*"no decision control"*, `$CC/hooks.md:2798`) | After compaction | Tripwire: the gate already failed |
| `SubagentStop` | ✅ | ✅ (ledger: can block and force more work) | Subagent finish | Useful inside a node, not for the node |
| `TeammateIdle` | ✅ | — | Teammate goes idle | Adjacent; not context-aware |

### 4a. `PreCompact` — the closest thing to a native gate

`$CC/hooks.md:2742-2755`, verbatim:

> "The matcher value indicates whether compaction was triggered manually or
> automatically: `manual` → `/compact`; `auto` → Auto-compact when the context window is
> full.
> **Exit with code 2 to block compaction.** … You can also block by returning JSON with
> `"decision": "block"`.
> Blocking automatic compaction has different effects depending on when it fires. **If
> compaction was triggered proactively before the context limit, Claude Code skips it and
> the conversation continues uncompacted.** If compaction was triggered to recover from a
> context-limit error already returned by the API, the underlying error surfaces and the
> current request fails."

That second paragraph is the load-bearing one. With the threshold moved down by
`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`, compaction fires **proactively**, far from the limit —
so blocking it is safe and the conversation simply continues. That gives the framework a
**free, harness-fired, percentage-accurate tripwire** with a block it can hold while the
node writes its state file.

Its limits, stated plainly:

- `PreCompact` input is `{…$m(), trigger, custom_instructions}` — **no token count**. It
  tells you "you crossed the threshold", not what the threshold or the current usage is.
- It cannot **end** the session. Blocking merely prevents compaction. The node still has
  to write its file and stop, and something outside has to launch the successor.
- It fires only while auto-compact is enabled. `DISABLE_AUTO_COMPACT=1` (the naive
  "we never compact" setting) **turns the gate off**. ⚠️ **Do not set
  `DISABLE_AUTO_COMPACT` if you use design B** — the two are mutually exclusive.

### 4b. `Stop` — the polling point, with two hard caps

`$CC/hooks.md` Stop input gives `stop_hook_active`, `last_assistant_message`,
`background_tasks[]`, `session_crons[]`. A Stop hook can read `transcript_path`, compute
the percentage (§1d), and block-with-feedback to make the node write its file.

Two caps to design around:

1. **"Claude Code overrides the hook and ends the turn after 8 consecutive blocks."**
   Your gate gets at most 8 chances.
2. **`stop_hook_active`** must be checked, or you build a loop that cannot resolve — the
   docs say so explicitly.
3. `background_tasks` / `session_crons` (v2.1.145+) let the hook distinguish *"session is
   done"* from *"session is paused waiting for background work"*. **A DAG node waiting on
   subagents will hit Stop with a non-empty `background_tasks`** — do not fire the gate
   there or you will interrupt a node mid-fan-out.
4. ⚠️ *"the transcript file isn't guaranteed to include the final message at Stop time on
   all versions"* — your reading can be one turn stale. Budget for the overshoot.

Related: **`/goal`** is *"a built-in shortcut for a session-scoped prompt-based Stop
hook"* (`$CC/hooks.md`). Worth a look before hand-rolling.

### 4c. What no hook can do

- Read context utilization from its stdin (§1c).
- **Terminate the session.** Nothing in the hook decision-control tables ends a session.
  Termination must come from outside: `claude stop <id>` (confirmed hidden subcommand,
  live probe), or the node calling `TaskStop`, or `--max-turns` exiting the `-p` run.
- Launch the successor. That is the orchestrator's job, or a `SessionEnd` hook's.

---

## 5. Concrete gate designs, with the exact fields each relies on

### Design A — Status-line sensor + Stop-hook actuator (*most portable*)

```
statusline command (with refreshInterval set!)
  └─ reads .context_window.used_percentage + .context_window_size + .session_id from stdin
  └─ writes  <state>/<session_id>.pct   (atomic rename)
  └─ echoes the same string so the operator can see it
Stop hook
  └─ reads <state>/<session_id>.pct
  └─ if pct >= 30 AND background_tasks == [] AND stop_hook_active != true:
        block with feedback: "Context gate: write your durable node file to <path>, then stop."
  └─ else: exit 0
SessionEnd hook (matcher: the exit reasons you care about)
  └─ if the durable file exists and the node is unfinished: launch the successor
```

**Relies on:** `context_window.used_percentage`, `context_window.context_window_size`,
`session_id` (status line); `transcript_path`, `stop_hook_active`, `background_tasks`
(Stop).
**Strengths:** uses the harness's own pre-computed number — no model→window map to
maintain; threshold is a plain constant you can change without touching env vars.
**Weaknesses:** two moving parts; the status line goes quiet when the session idles unless
`refreshInterval` is set (`$CC/statusline.md:153`); ≤8 consecutive Stop blocks; one-turn
staleness.

### Design B — Native threshold + `PreCompact` block (*fewest moving parts*)

```
.claude/settings.json  env:  { "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "33" }
        (NOT an exported shell var — exec-mode strips CLAUDE_*)
        do NOT also set DISABLE_AUTO_COMPACT — it turns this off
        leave the window model-default or at 200000; do NOT shrink below 200000 (§2b caveat)
PreCompact hook, matcher "auto"
  └─ write a marker: "context gate tripped at the native threshold"
  └─ exit 2  (or {"decision":"block"})  → compaction is skipped, conversation continues
  └─ its stderr/reason reaches the node
Stop hook (or the node's own instructions)
  └─ on seeing the marker: write the durable node file, then stop
```

**Relies on:** `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` (env), `PreCompact` matcher `auto`,
`PreCompact` exit-2 block, `$CC/hooks.md:2755` ("skips it and the conversation continues
uncompacted").
**Strengths:** the harness computes the percentage against the correct denominator; no
transcript parsing, no model→window map, no status line; fires precisely once.
**Weaknesses:** the threshold is expressed as an env var, not a constant your code owns;
`PreCompact` carries **no token count**, so the marker is the only signal; two undocumented
remote gates can move the window under you (§2a); and the whole design depends on the
`yFu` / `MKe` semantics I marked NEEDS-PROBE (claim 11).

### Design C — Stop-hook transcript arithmetic (*self-contained, one hook*)

```
Stop hook
  └─ parse transcript_path; take the LAST record with message.usage
  └─ used = input + cache_creation + cache_read     (NOT output — matches statusline.md:335)
  └─ pct  = 100*used / windowFor(message.model)     ← the weak link
  └─ same gating logic as Design A
```

**Relies on:** `transcript_path`, `message.usage.*`, `message.model`.
**Strengths:** one file, no status line, no env var, no compaction interaction.
**Weaknesses:** ⚠️ **you own the model→window map**, and it drifts (200K vs 1M vs `[1m]`
vs Sonnet 5's implicit 1M vs the 200K Bedrock/GCP/Foundry configurations,
`$CC/context-window.md:1634`). That map going stale silently mis-scales the gate.

### Design D — Belt and braces (*what I would actually build*)

**B for the trip, A's status line for the number, C as the audit, plus two tripwires.**

- `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` in `.claude/settings.json` `env` sets the primary trip
  at the percentage you want; `PreCompact(auto)` blocks and marks.
- The status line writes `used_percentage` continuously (with `refreshInterval`) so the
  operator, the node, and any post-mortem can all see the real number without parsing
  anything.
- A `Stop` hook reads the marker **and** the `.pct` file, honours `stop_hook_active` and
  empty `background_tasks`, and issues the write-and-stop instruction.
- `PostCompact` writes a **loud failure record**: if it ever fires, the gate leaked and a
  node compacted. `compactMetadata.cumulativeDroppedTokens` quantifies exactly what was
  lost (§1e).
- `--max-turns` on the `-p` launch as a hard backstop, so a wedged node cannot burn the
  window unbounded.

**And the honest caveat that outranks all four designs:** re-derive the cold-start cost
before fixing 30% (§2d). The mechanics work at any threshold; whether 30% leaves enough
room to do work is the unsettled question, and it is a bigger risk to this framework than
any of the mechanics above.

---

## 6. Ledger corrections and additions

### ⚠️ Correction to an existing ledger row

The row

> `claude attach` **DOES NOT EXIST** at this version — the subcommand list is `agents,
> auth, auto-mode, doctor, gateway, import, install, mcp, plugin, project, setup-token,
> ultrareview, update` | REFUTED | `--help`, control `agents`/`project` present | 2.1.222 |
> 2026-08-05

**is wrong and should be corrected.** `claude attach <id>` exists at 2.1.222; it is a
**hidden** subcommand, absent from the visible `--help` command list. Live probe:

```
$ claude attach --help
Usage: claude attach <id>
$ claude peek --help          # CONTROL (invented fresh)
Usage: claude [options] [command] [prompt]     ← falls through to root help
```

`claude stop <id>`, `claude rm <id>` and `claude respawn <id>|--all` are hidden the same
way. This is the founding incident's exact shape: a `--help`-bounded absence reported as a
world absence. **The bound was "the visible subcommand list"; the answer was reported about
"the CLI".**

### Rows ready to append

| Claim | Verdict | Evidence | Ver | Date |
|---|---|---|---|---|
| **No hook event receives context utilization** — the common base `$m()` is exactly 8 fields, none of them a token count | CONFIRMED | binary `$m()`; 64 `hook_event_name:` sites enumerated by shape; control = `rRT` DOES spread `context_window` | 2.1.222 | 2026-08-05 |
| The **status line** is the only surface handed `context_window.used_percentage`; it is a sensor, never an actuator | CONFIRMED | `$CC/statusline.md:167-209`; binary `tRT`/`rRT` | 2.1.222 | 2026-08-05 |
| ⚠️ **The status line goes QUIET while a session waits on background subagents** — a coordinator's sensor blinds itself unless `refreshInterval` is set | CONFIRMED | `$CC/statusline.md:153` | 2.1.222 | 2026-08-05 |
| `used_percentage` is **input-tokens-only** and is `null` before the first API call and after `/compact` | CONFIRMED | `$CC/statusline.md:313,335,339` | 2.1.222 | 2026-08-05 |
| Auto-compact trigger = `min(window−round(window×buffer), min(floor(window×pct/100), window−13000))`; `PCT_OVERRIDE=33` on a 200K window ≈ 30% | CONFIRMED | binary `FTo`/`ISs`/`EEe`; `aFu=13000`, `hFu=20000`, `xSs=0.2` | 2.1.222 | 2026-08-05 |
| The `Math.min` in `FTo` is *why* `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` can only lower | CONFIRMED | binary `FTo` | 2.1.222 | 2026-08-05 |
| `DO()` (auto-compact enabled) is `!DISABLE_COMPACT && !DISABLE_AUTO_COMPACT && autoCompactEnabled` — **no remote gate** | CONFIRMED | binary `DO()` | 2.1.222 | 2026-08-05 |
| ⚠️ **Two of the seven window-resolution steps are undocumented REMOTE gates** (`clientdata`/`rowan_thicket`, `experiment`) — a window you did not set can be imposed | CONFIRMED | binary `qX()` | 2.1.222 | 2026-08-05 |
| ⚠️ A configured auto-compact window **below 200000** hits `if(a<XPe) return !1` in `yFu` (`XPe=200000`) — prefer moving the pct, not shrinking the window | NEEDS-PROBE | binary `yFu`; probe written out in §2b | 2.1.222 | 2026-08-05 |
| `PreCompact` blocking is **safe when compaction is proactive** — the conversation just continues uncompacted; only limit-recovery compaction turns a block into a failed request | CONFIRMED | `$CC/hooks.md:2755` | 2.1.222 | 2026-08-05 |
| A `Stop` hook gets ≤ **8 consecutive blocks** before the harness overrides it, and `background_tasks[]` distinguishes "done" from "waiting on subagents" | CONFIRMED | `$CC/hooks.md` Stop input | 2.1.222 | 2026-08-05 |
| `SessionStart` `initialUserMessage` **creates the first turn of a `-p` run with no prompt argument** — the native restart-injection channel | CONFIRMED | `$CC/hooks.md` SessionStart decision control; binary 23 | 2.1.222 | 2026-08-05 |
| Transcript `compactMetadata` carries `postTokens`, `cumulativeDroppedTokens`, `preservedSegment` — **all 0-of-175 in docs** | CONFIRMED | live transcript dump; binary 17/7/14; control `wfdagNoSuchToken91` → 0/0 | 2.1.222 | 2026-08-05 |
| The transcript carries `message.usage` (all 4 token fields) and `message.model` but **NOT the window size** — a transcript-derived gate must own a model→window map | CONFIRMED | live probe, 3-way control arm | 2.1.222 | 2026-08-05 |
| **`claude respawn <id>\|--all` exists** (hidden) but restarts *with the conversation intact* — not a context reset | CONFIRMED | live `--help`; control `claude wfdagbogus` | 2.1.222 | 2026-08-05 |
| ⚠️ **`claude attach <id>` DOES exist** (hidden) — corrects the prior ledger row, which was bounded to the visible `--help` list | **REFUTES prior row** | live `claude attach --help`; control `claude peek --help` falls through | 2.1.222 | 2026-08-05 |
| `CLAUDE_CODE_BLOCKING_LIMIT_OVERRIDE` and `CLAUDE_AFTER_LAST_COMPACT` are real and **undocumented** | CONFIRMED | binary 3/3, docs 0/0; control 0 | 2.1.222 | 2026-08-05 |

---

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the installed
  binary at v2.1.222 and the vendored offline documentation tree (`$CC`, 175 pages) are
  both this product's; every harness claim above is grounded in one or both.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — repo prior art:
  `.claude/skills/clear-prep/SKILL.md` (the durable-handoff pattern the node file
  generalises), `.claude/rules/agent-artifact-conventions.md`,
  `.claude/rules/probes-need-a-control-arm.md`, memory `feedback_no_compact`.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — hosts
  the offline `agent-harness-docs` tree cited throughout as `$CC/…`.
