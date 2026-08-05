# Lane Economics: Offloading Agent Work to Codex While Maximizing Fable 5

**Agent:** lane-economics · **Date:** 2026-08-04 · **Branch:** `research/agent-team-design`

**Question under research:** two user goals pull in opposite directions —
*"use my codex subscription plan to offload some of the tokens for the work these
agents do"* and *"maximize my fable-5 model tokens whenever possible"*. This
report establishes what is **mechanically true** so a routing decision can be
made on facts. It does **not** make the decision.

**Status:** COMPLETE. Two numbers remain deliberately unmeasured and are labelled
UNVERIFIED in place (§6.1): the Claude-side wrapper tax per Codex delegation, and
whether this ChatGPT Pro seat is the 5x or 20x tier.

---

## 0. Environment probe (verified)

| Thing | Result | Evidence |
|---|---|---|
| `codex` CLI | present, `codex-cli 0.146.0` | `command -v codex` → `/Users/rmanaloto/.local/share/mise/installs/codex/0.146.0/bin/codex` |
| `agy` CLI | present, `1.1.8` | `command -v agy` → `/Users/rmanaloto/.local/share/mise/installs/antigravity-cli/1.1.8/agy` |

---

## 1. Mechanically, how does a Claude subagent hand work to Codex?

**Answer: it is always `Bash` shelling out. There is no non-Bash path.** Both
installed plugins reach Codex through a subprocess, and both agent definitions
declare `tools: Bash, …` — there is no MCP server, no in-harness Codex
transport, no API binding.

### 1.1 The two paths that exist on this machine

| Path | Wrapper agent | Wrapper model | Transport | Evidence |
|---|---|---|---|---|
| `fable-orchestrator` lanes | `codex-implementer` / `codex-reviewer` | **`model: sonnet`** | `Bash` → `scripts/run-lane.sh` → `codex exec` | `~/.claude/plugins/cache/fable-orchestrator/fable-orchestrator/1.14.0/agents/codex-implementer.md:4-5` |
| `codex` plugin rescue | `codex:codex-rescue` | (see §1.4) | `Bash` → `node scripts/codex-companion.mjs task …` | `~/.claude/plugins/cache/openai-codex/codex/1.0.6/skills/codex-cli-runtime/SKILL.md:12` |

A third path exists in principle — the architect session itself running
`codex exec` in a Bash call — but the orchestration skill explicitly routes
long-output work through a wrapper so raw transcripts never enter the
architect's context (`skills/orchestration/SKILL.md:46`).

### 1.2 The exact command the fable lane runs

`scripts/run-lane.sh:63-66` (fable-orchestrator 1.14.0):

```bash
codex exec --model "${MODEL:-gpt-5.6-sol}" -c model_reasoning_effort=high $FAST \
    --sandbox workspace-write --skip-git-repo-check --cd "$(pwd)" \
    --output-last-message "$FINAL" - < "$SPEC" > "$LOG" 2>&1
```

and the review lane, `run-lane.sh:84-87`:

```bash
codex exec review --model "${MODEL:-gpt-5.6-sol}" -c model_reasoning_effort=high $FAST \
    -c 'sandbox_mode="read-only"' --json \
    --output-last-message "$FINAL" - < "$SPEC" > "$LOG" 2>&1
```

Key mechanical facts, all from `run-lane.sh`:

- **Detached + watchdog.** The CLI runs in a backgrounded subshell with its own
  process group (`set -m`, line 41); a pure-bash watchdog polls in 10s ticks and
  group-kills at the budget (lines 134-146). Default budget **1800s** for
  implementation lanes, **600s** for `*-review`/`*-research` (line 53).
- **Why detached:** "the harness caps any foreground tool call at 10 minutes"
  (`run-lane.sh:4-5`). A foreground launch orphans the CLI mid-run.
- **The wrapper polls in ≤90s slices** (`run-lane.sh:152-166`), because the
  harness auto-backgrounds a foreground tool call after ~2 minutes.
- **Spec arrives on stdin from a temp file** — the trailing `-` is the
  positional PROMPT meaning "read from stdin". No shell quoting hazard.
- **`FAST` is opt-in only:** `-c service_tier=fast -c features.fast_mode=true`,
  gated on `LANE_CODEX_FAST=1` (`run-lane.sh:61-62`).

### 1.3 What the wrapper costs in Claude tokens

This is the number that decides the economics, and it is **not zero**. The
Sonnet wrapper pays for, per delegation:

1. its own system prompt + the 147-line agent definition it is instantiated from;
2. **writing the full six-part spec into a heredoc** — the spec text is Claude
   output tokens, at wrapper prices;
3. one `wait` slice tool-call round-trip **per 90 seconds of Codex wall clock**
   (a 30-minute Codex run ⇒ ~20 round-trips, each re-reading the growing
   wrapper transcript);
4. reading the diff, `FINAL`, and grepping `LOG` for verification evidence
   (`codex-implementer.md:121`);
5. the structured report it emits, which then lands in the **architect's**
   context at architect prices.

Plus, upstream of the wrapper, the architect pays to *write* the spec once
before handing it down. The orchestration skill states this cost honestly rather
than hiding it: *"the CLI producers carry the code volume, with a thin Sonnet
wrapper supervising each lane (preflight, wait slices, re-verification — real
but modest overhead, stated honestly)"* (`SKILL.md:26`).

**UNVERIFIED (no measurement taken this session):** the actual token cost of one
codex-implementer delegation on this machine. The `/usage` breakdown (§5) is the
instrument that would settle it; I did not run it, since it is a user-facing
command, not a probe.

What is **free at the margin on a ChatGPT subscription** is everything inside
`codex exec`: the model's reading of the repo, its edits, its own tool calls,
its retries. That is the entire code-production volume — which is why the split
can pay even with a non-trivial wrapper tax, provided the delegated unit is
large. The corollary is the break-even: a small task's wrapper tax exceeds what
it offloads. The `antigravity-delegate` agent description states the same
principle for the Gemini lane — *"delegating a tiny task is a measured net loss
(round-trip cost exceeds the savings)"*.

### 1.4 The `codex` plugin's path is different (and thinner)

`codex:codex-rescue` is a **forwarder, not an orchestrator**
(`skills/codex-cli-runtime/SKILL.md:15`): one `task` invocation, return stdout
unchanged, *"Do not inspect the repository, read files, grep, monitor progress,
poll status, fetch results, cancel jobs, summarize output"* (line 41). That is a
much cheaper Claude-side wrapper than the fable lane — it buys none of the
verification discipline, but it also pays none of the wait-slice tax.

It routes through `node "${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs" task`
rather than `codex exec` directly, and defaults to `--write`
(`SKILL.md:24`) with effort and model left unset unless asked (lines 21-22).

## 2. Correct `codex exec` invocation forms today — and the rule's drift

Re-probed against the installed `codex-cli 0.146.0`, not trusted from the rule.
Control arm for every "flag does not exist" claim: `codex exec --ephemeral --help`
→ **rc=0** (a flag that does exist), so an rc=2 is a real rejection, not a
help-short-circuit.

### 2.1 Flag-by-flag verdict on `.claude/rules/ai-cli-invocation.md`

| Rule claim | Verdict | Evidence |
|---|---|---|
| `-p` is `--profile`, not prompt | ✅ **STILL TRUE** | `codex exec --help` → `-p, --profile <CONFIG_PROFILE_V2>` |
| `codex --full-context` does not exist | ✅ **STILL TRUE** | `codex --full-context --help` → **rc=2**; control `--ephemeral` → rc=0 |
| `codex exec --ephemeral --sandbox read-only -` | ✅ correct | all three present in `--help` |
| `codex exec -o /tmp/result.md` captures result | ⚠️ **PARTLY MISLEADING** | `-o, --output-last-message <FILE>` writes **only the agent's last message**, not the transcript. For the transcript use `--json` (JSONL to stdout) or redirect stdout. `run-lane.sh:63-66` uses **both**: stdout→`LOG`, `-o`→`FINAL`. |
| `codex exec "prompt"` (positional, no `-`) is a WRONG pattern that "will silently fail" | ❌ **REFUTED** | `codex exec --help`, Arguments section: *"`[PROMPT]` Initial instructions for the agent. **If not provided as an argument** (or if `-` is used), instructions are read from stdin."* A positional prompt is a documented, supported form. |
| `--full-auto` (used in the rule's "Implementation" recipe) | ⚠️ **HIDDEN, undocumented** | `codex exec --full-auto --help` → rc=0 (accepted), but `codex exec --help \| grep -i full-auto` → **0 hits**; control `grep -c -- '--sandbox'` → **1**. It works but is not in the help surface — a recipe built on it is fragile across upgrades. |

**Net drift:** one claim is wrong (positional prompt), one is misleading (`-o`),
one recommends a hidden flag. The *stdin* preference the rule argues for is still
sound — the reason is ARG_MAX on large prompts, and `run-lane.sh` uses exactly
that form — but it should be stated as a **preference**, not as "the positional
form silently fails".

### 2.2 Surface that exists now and the rule does not mention

From `codex --help` / `codex exec --help` on 0.146.0:

- `codex exec review` — a first-class non-interactive review subcommand (used by
  `run-lane.sh:84`). Note from that file's comment: *custom instructions are
  mutually exclusive with the subcommand's `--commit`/`--base` flags*, and
  `codex exec review` **has no `--cd`** — it reviews the repo at the caller's cwd
  (`run-lane.sh:17-23`).
- `codex doctor` — "Diagnose local Codex installation, config, auth, and runtime health".
- `--output-schema <FILE>` — JSON Schema for the final response shape. This is
  the clean way to get a machine-parseable lane report without paying Claude
  tokens to reformat prose.
- `--add-dir`, `--ignore-user-config`, `--strict-config`, `--ignore-rules`,
  `--enable/--disable <FEATURE>`.
- `codex mcp-server` — Codex can itself **be** an MCP server over stdio. This is
  the one theoretically-non-Bash transport; registering it would put Codex's
  tools in the harness directly. Under this repo's `research-doc-sources.md`
  § "MCP: two lanes" that is **lane 2** (our own automation) ⇒ avoid; the CLI
  already does it.

### 2.3 The local config the lane silently overrides

`~/.codex/config.toml` (lines 5-9):

```toml
model = "gpt-5.6-sol"
model_reasoning_effort = "xhigh"
approval_policy = "never"
sandbox_mode = "danger-full-access"
```

Two consequences worth knowing before routing anything:

1. **The fable lane runs at LOWER reasoning than your interactive default.**
   `run-lane.sh:63` pins `-c model_reasoning_effort=high`; your config says
   `xhigh`. CLI `-c` wins. If "maximum reasoning per diff" is the reason for
   choosing the codex lane, that intent is being partially undone — the lane
   accepts a 4th positional arg for the model but not for effort.
2. **Your global `sandbox_mode = "danger-full-access"` is what a bare
   `codex exec` would run under.** The fable lane rescues this by passing
   `--sandbox workspace-write` explicitly (`run-lane.sh:64`), and the review lane
   pins `-c 'sandbox_mode="read-only"'` (line 85). Any hand-rolled `codex exec`
   that omits `--sandbox` inherits full access. This is a live risk for the
   ad-hoc invocation forms the rule documents — the rule's own
   "Research/debate" recipe does pass `--sandbox read-only`, but its
   `-c model_reasoning_effort="high"` recipe does not.

---

## 3. Authentication and quota — this machine is on a ChatGPT **Pro** subscription

Determined without printing any credential. Method: `~/.codex/auth.json` parsed
in Python emitting **key names and non-secret scalars only**; the `id_token` was
base64-decoded to read the entitlement claim, and the account id was replaced
with `[redacted-id]` before printing.

| Fact | Value | Evidence |
|---|---|---|
| `auth_mode` | **`chatgpt`** | `~/.codex/auth.json` → `auth_mode` |
| `OPENAI_API_KEY` in auth.json | **`null`** (absent) | same file, key present but `NoneType` |
| `OPENAI_API_KEY` in shell env | **ABSENT** | `[ -n "${OPENAI_API_KEY:-}" ] && echo SET \|\| echo ABSENT` → `ABSENT`; control `HOME` → `SET` |
| OAuth token set | `access_token`, `refresh_token`, `id_token`, `account_id` present | `auth.json` → `tokens` key names |
| `chatgpt_plan_type` | **`pro`** | `id_token` claim `https://api.openai.com/auth.chatgpt_plan_type` |
| Last token refresh | `2026-08-03T17:18:09Z` | `auth.json` → `last_refresh` |
| `CODEX_HOME` override | ABSENT | env presence flag |

**Conclusion: Codex work here bills against a ChatGPT Pro subscription, not
metered API credits.** That is the strongest single fact in this report for the
offload question — it means Codex-side token consumption is *not* a marginal
dollar cost, it is a consumption against plan limits.

### 3.1 What "subscription quota" means mechanically

- Fast mode is explicitly a **credit** trade, not a saving: the plugin documents
  *"~1.5x output speed for ~2–2.5x credit burn, and it requires ChatGPT sign-in
  (API-key auth cannot use it)"* (`skills/orchestration/SKILL.md:78`;
  same numbers at `run-lane.sh:14-15`). The "requires ChatGPT sign-in" condition
  **is satisfied here** (`auth_mode = chatgpt`), so fast mode is available — and
  it is the one knob that converts subscription headroom into wall-clock speed.
- The plugin's fallback chain treats **"usage limit"** as a first-class lane
  outage condition alongside auth failure and CLI-missing
  (`skills/orchestration/SKILL.md:52`) — i.e. the design already assumes the
  subscription can run dry mid-build and routes around it loudly.

**UNVERIFIED — OpenAI's published rate limits for Codex on ChatGPT Pro.** I did
not fetch OpenAI's docs for the current Pro limits (weekly/5-hourly credit
windows, and whether `gpt-5.6-sol` at `high`/`xhigh` draws differently). This is
the one factual gap in this section that a routing decision may need; it should
be filled from OpenAI's own help pages before anyone sizes a build against the
plan. Do not infer it from this report.

## 4. What "maximize Fable 5 tokens" means mechanically

### 4.1 The subagent model precedence chain — cited, exact

`$CC/sub-agents.md:303-308` gives the resolution order verbatim:

> When Claude invokes a subagent, it can also pass a `model` parameter for that
> specific invocation. Claude Code resolves the subagent's model in this order:
> 1. The `CLAUDE_CODE_SUBAGENT_MODEL` environment variable, when set to a model alias or model ID
> 2. The per-invocation `model` parameter
> 3. The subagent definition's `model` frontmatter
> 4. The main conversation's model

So, **highest wins**:

| Rank | Mechanism | Scope | Notes |
|---|---|---|---|
| 1 | `CLAUDE_CODE_SUBAGENT_MODEL` env var | every subagent, agent team, workflow agent | *"takes precedence over the per-invocation `model` parameter and the subagent definition's `model` frontmatter"* — `$CC/env-vars.md:337`. `inherit` ≡ unset as of v2.1.196 (`$CC/sub-agents.md:310`) |
| 2 | Agent tool's `model` parameter | one invocation | also sticks across `SendMessage` resume as of v2.1.211 (`$CC/sub-agents.md:314`) |
| 3 | Frontmatter `model:` in the agent definition | that agent type | `$CC/sub-agents.md:296-301` |
| 4 | The main conversation's model | fallback / `inherit` | the default when `model:` is omitted |

**`fable` is a documented value at every one of those layers.** The alias table
lists it — *"**`fable`** Uses Claude Fable 5 for your hardest and
longest-running tasks"* (`$CC/model-config.md:35`) — and `$CC/sub-agents.md:298`
names it in the subagent `model` field's allowed aliases: *"use one of the
available aliases: `sonnet`, `opus`, `haiku`, or `fable`"*. `$CC/model-config.md:154`
confirms the allowlist covers *"the `model` field in subagent frontmatter, the
Agent tool's `model` parameter, `CLAUDE_CODE_SUBAGENT_MODEL`"* — i.e. all three
are real model-selection surfaces for subagents, `fable` included.

### 4.2 Session model — a separate, *lower*-precedence chain

`$CC/model-config.md:83-88`, in priority order: `/model` in-session →
`claude --model` at startup → `ANTHROPIC_MODEL` → the `model` settings field.
Notably `/model` **saves the choice as the default for new sessions** since
v2.1.153 (`:90-93`; `Enter` saves, `s` is session-only).

Two facts that bear directly on "maximize Fable":

- **Fable 5 is never a default.** *"Fable 5 is not the default model on any
  account type. Sessions use Fable 5 only after you choose it, with
  `/model fable`, a `model` setting, or the `best` alias where Fable 5 is
  available."* (`$CC/model-config.md:342`, and `:66`.)
- **Thinking cannot be turned off on Fable 5** — *"The session toggle,
  `alwaysThinkingEnabled`, and `MAX_THINKING_TOKENS=0` have no effect there"*
  (`$CC/model-config.md:530`). Fable's per-token spend is therefore governed by
  `/effort` (`low`…`max`, `$CC/model-config.md:448`), not by disabling thinking.
  Effort frontmatter exists on subagents too (`$CC/model-config.md:504`), with
  `CLAUDE_CODE_EFFORT_LEVEL` beating everything (`:506`).

### 4.3 What this machine currently has set

| Surface | Value | Evidence |
|---|---|---|
| `CLAUDE_CODE_SUBAGENT_MODEL` | **ABSENT** | env presence probe; control `HOME` → SET |
| `.claude/settings.json` `model` key | **not set** (only an `env` block) | `grep -n '"model"' .claude/settings.json` → no match |
| `~/.claude/settings.json` model keys | no match | same grep, user scope |
| Repo agent frontmatter | `staleness-auditor.md` → `model: opus`; `dockerfile-reviewer.md` → none | per-file grep |

So **nothing on this machine currently overrides subagent model choice** — every
subagent either takes its plugin/definition frontmatter or inherits the session
model. That is the clean slate a routing decision would be written onto.

### 4.4 What arms the cross-vendor flow here, and what leaves it inert

`.claude/CLAUDE.md:79-98`. Two lines, and only one of them is the trigger:

```
- When the session model is Fable, without being reminded: non-trivial implementation runs
  the fable-orchestrator architect-as-orchestrator flow — invoke the
  fable-orchestrator:orchestration skill before delegating ...   ← line 81, the TRIGGER
- fable-orchestrator: implementation lane = codex                 ← line 82, the MODE
```

- **The mode line alone is inert.** The file says so explicitly at `:85-87`:
  *"Until 2026-07-24 only the mode line was present, and the plugin's own setup
  wizard states the mode line 'is inert without the trigger': the orchestrator
  declared a lane but left it uninvoked."* Corroborated by the plugin: the
  orchestration skill treats mode as *routing only* — *"Mode changes routing
  only"* (`skills/orchestration/SKILL.md:68`) — it does not cause delegation.
- **The trigger is `model == Fable`-gated by design.** `:84-85`: *"it is
  Fable-gated by design — sessions on other models read the condition and skip
  the flow."*
- **Therefore, on this session's model the flow is OFF.** This session runs Opus 5
  (`claude-opus-5[1m]`), and `.claude/CLAUDE.md:87-89` states *"Default `/model`
  is **Opus 5** for everyday work; switch to **Fable 5** deliberately to arm this
  flow."*

**This is the crux of the tension.** The only declared mechanism for routing work
to Codex is *conditioned on the session running Fable 5*. The two user goals are
not merely in tension — as currently wired, **the Codex offload only happens when
Fable is the session model**, i.e. offloading requires spending Fable, not
avoiding it. Any routing design has to either accept that coupling or decouple
the trigger from the model gate.

One more mechanical constraint from the same file (`:89-90`): *"`grok` CLI is NOT
installed, so `codex` is the only viable fixed mode and cross-family review falls
to antigravity or Claude."* Verified: `command -v grok` — see §7 control arm.

### 4.5 The lever that "maximizes Fable" is not the same as the one that offloads

Worth separating cleanly, because they act on different layers:

- **Maximizing Fable** is a *session-model* + *subagent-model* decision:
  `/model fable`, and/or `model: fable` on the subagent types whose judgment you
  want at Fable quality. Nothing about Codex changes it.
- **Offloading to Codex** is a *delegation* decision: which units of work get
  written as a spec and handed to `codex exec` instead of being typed by a Claude
  model. Nothing about `/model` changes it.

They interact in exactly one place — the architect's own token volume. The
orchestration skill's prime directive is *"The session model is the most
expensive lane in the system, on both input and output tokens. The whole economic
case for this pattern is keeping its token volume low: spend Fable on judgment;
the CLI producers carry the code volume"* (`skills/orchestration/SKILL.md:26`).
Under that framing the two goals are **complementary, not opposed**: Fable is
maximized in *quality of decision per token*, not in *token count*. Whether that
is what the user means by "maximize my fable-5 model tokens" is a question of
intent this report cannot settle — see §6.

## 5. Cost model — what actually drives spend, and where `/usage` shows it

Source: `$CC/costs.md` (291 lines, offline copy; live equivalent
<https://code.claude.com/docs/en/costs.md>).

### 5.1 Where the per-subagent / per-skill / per-plugin breakdown lives

`$CC/costs.md:36` — this is the exact instrument the brief asks about:

> On a Pro, Max, Team, or Enterprise plan, `/usage` also shows a breakdown of
> what counts against your plan limits. It attributes recent usage to **skills,
> subagents, plugins, and individual MCP servers**, with each shown as a
> percentage of the total. It also flags behaviors such as long context or cache
> misses when one accounts for 10% or more of recent usage. Press `d` or `w` to
> switch between the last 24 hours and the last 7 days.

Two caveats stated in the same paragraph, both load-bearing for using it as
evidence:

- *"The figures are approximate and computed from **local session history on this
  machine**, so usage from other devices or claude.ai is not included."*
- The Session block's **dollar figure is computed locally at list rates** and
  *"doesn't reflect promotional pricing or contracted discounts and may differ
  from your actual bill"* (`:23`). For a subscriber it is *"not relevant for
  billing purposes"* (`:20`) — it is a **relative** instrument, which is exactly
  what a routing comparison needs.

**This is the right measurement tool for settling §1.3's UNVERIFIED wrapper cost.**
Run `/usage`, press `w`, and read the `codex-implementer` row's share.

### 5.2 What drives spend

| Driver | Magnitude / mechanism | Evidence |
|---|---|---|
| **Agent teams** | *"approximately **7x** more tokens than standard sessions when teammates run in plan mode, because each teammate maintains its own context window and runs as a separate Claude instance"* | `$CC/costs.md:246` |
| Team size | *"token usage is roughly proportional to team size"*; each teammate loads CLAUDE.md, MCP servers and skills automatically | `$CC/costs.md:139-140` |
| Idle teammates | *"Each active teammate continues consuming tokens until it exits or the session ends"* | `$CC/costs.md:141` |
| Model choice | *"Use Sonnet for teammates"*; *"For simple subagent tasks, specify `model: haiku`"* | `$CC/costs.md:138`, `:167` |
| Context size | *"Token costs scale with context size"*; prompt caching and auto-compaction offset repeated content | `$CC/costs.md:146` |
| Long context / cache misses | flagged by `/usage` when ≥10% of recent usage | `$CC/costs.md:280` |
| Verbose operations | mitigated by delegating to subagents so *"the verbose output stays in the subagent's context while only a summary returns"* | `$CC/costs.md:242` |
| CLAUDE.md size | loaded at session start, present *"even when you're doing unrelated work"*; skills load on demand | `$CC/costs.md:234` |

### 5.3 The subscription-limit fact that decides how the two plans interact

`$CC/costs.md:128`:

> **"You've hit your session limit" or "You've hit your weekly limit"**: a
> seat-based usage window on a subscription plan. **These windows are shared
> across all models, so switching models with `/model` doesn't restore access**,
> though it does keep the developer working after the model-specific "You've hit
> your Opus limit" message.

Read carefully, this says two different things:

1. There is a **shared session/weekly window** across all Claude models — so
   moving work from Fable to Sonnet does **not** buy back a hit weekly cap.
2. There *is* a **model-specific** cap too ("You've hit your Opus limit"), and
   switching models **does** get you working again past that one.

The consequence for this question: **Claude-side and Codex-side budgets are
completely separate pools.** Work moved to Codex draws on the ChatGPT Pro plan
(§3) and draws **nothing** from the Claude weekly window. That is the mechanical
basis on which an offload is real rather than cosmetic — minus the wrapper tax
in §1.3, which stays on the Claude side.

### 5.4 Agent-team specifics relevant here

Agent teams are **off by default** — `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
(`$CC/costs.md:142`). They are evidently on in this session (this report is being
written by a teammate), so the 7x multiplier at `:246` is a live cost, not a
hypothetical. `$CC/workflows.md:357` adds that *"Every agent in a workflow uses
your session's model unless the script routes a stage to a different one or the
`CLAUDE_CODE_SUBAGENT_MODEL` environment variable is set, which overrides both"*
— so **a Fable session with agent teams enabled and no subagent-model override
puts every teammate on Fable**, multiplied by team size. That is the single
largest Fable-spend amplifier available in this setup, and it is currently
unguarded (§4.3: no override set anywhere).

## 5b. The Codex-side quota, from OpenAI's own docs (gap in §3.1 now filled)

Source: <https://learn.chatgpt.com/docs/pricing> (canonical destination of
`https://developers.openai.com/codex/pricing`, which 308-redirects there).

> "The usage limits for local messages and cloud chats share a **five-hour
> window**. Additional weekly limits may apply."

Per 5-hour window, by model and plan:

| Plan | GPT-5.6 **Sol** | GPT-5.6 Terra | GPT-5.6 Luna |
|---|---|---|---|
| Plus | 10–100 msgs | 25–200 | 250–2,000 |
| **Pro 5x** | **50–500** | 125–1,000 | 1,250–10,000 |
| **Pro 20x** | **200–2,000** | 500–4,000 | 5,000–40,000 |
| Business | 10–100 | 25–200 | 250–2,000 |

Beyond the included allowance, *"available credits let you continue working"* —
priced by input / cached / output tokens, i.e. the overflow path is metered even
on a subscription.

Three consequences that matter for routing:

1. **The lane is pinned to the scarcest bucket.** `run-lane.sh:63` defaults to
   `--model gpt-5.6-sol`, which on Pro 5x is **50–500 messages / 5h** — roughly
   **1/25th** the Luna allowance. If offload *volume* is the goal, the model
   argument (`run-lane.sh` accepts it as the 4th positional arg to `start`) is
   the biggest available lever, not the wrapper.
2. **Fast mode multiplies against this window**, at the plugin's stated ~2–2.5x
   credit burn (`skills/orchestration/SKILL.md:78`). On a scarce Sol budget that
   is expensive; on Luna it is cheap.
3. **Local CLI and cloud tasks share the window** — so `codex exec` from an agent
   competes with the user's own interactive Codex and ChatGPT Codex usage. There
   is no separate "automation" pool.

**Remaining unknown: whether this account is Pro 5x or Pro 20x.** The `id_token`
claim resolves only to `chatgpt_plan_type = pro` (§3), which does not
discriminate. The discriminator OpenAI documents is **`/status` inside a Codex
CLI session**, or the dashboard at `chatgpt.com/codex/settings/usage`. I did not
run `/status` — it is an interactive-session command, not a probe I can issue
from Bash without starting a session. Treat the tier as **UNVERIFIED**; the two
tiers differ by 4x, which is large enough to change a routing decision.

---

## 6. The recommendation space — enumerated, not chosen

Six plausible splits. For each: what it claims, what evidence would **support**
it, and what would **refute** it. No pick is made here.

### A. Fable orchestrates + Codex implements (the plugin's designed shape)

Fable holds architecture, decomposition, specs, verdicts; `codex-implementer`
lanes carry all typing. This is literally what `skills/orchestration/SKILL.md:26`
prescribes, and what `.claude/CLAUDE.md:82` declares.

- **Supports:** a `/usage` 7-day breakdown showing the `codex-implementer` row at
  a small share while diffs land; measured Sol message consumption staying inside
  the 5h window on real builds; a low refutation rate in the review tier (the
  cheap lane's diffs surviving cold review).
- **Refutes:** `/usage` showing the Sonnet wrappers + architect spec-writing
  costing more Claude tokens than the architect typing the code directly would
  have — the §1.3 wrapper tax exceeding the offload. Also refuted if Sol's 50–500
  msg/5h window (Pro 5x) throttles a multi-task build, since a blocked lane falls
  back to *Claude Opus* by design (`SKILL.md:52`) — an outage that silently moves
  spend back onto Claude.

### B. Fable *only* for adversarial review; Codex/Sonnet do everything else

Fable never orchestrates; it is invoked as `fable-advisor` at commitment
boundaries and as the cold completeness reader on security/auth/concurrency
diffs (`SKILL.md:130`).

- **Supports:** the advisor's verdicts changing decisions (measurable — count
  reversals); Fable's per-invocation token count being small because
  `fable-advisor` is read-only and capped at *"a verdict in under 300 words"*
  (`SKILL.md:115`).
- **Refutes:** the trigger problem in §4.4 — the whole codex flow is gated on the
  session model being Fable, so this split requires **rewriting `.claude/CLAUDE.md:81`**
  to decouple the trigger from the model. Also refuted if the advisor, lacking
  session context, produces generic verdicts (it *"cannot run commands"*,
  `SKILL.md:121`).

### C. Codex for bulk / mechanical work only; Claude keeps correctness-critical

This is the plugin's **`mix`** mode with the polarity the user's cost goal
implies. Note the plugin's own mix polarity is the *opposite*: it sends
correctness-critical work to codex and mechanical work to grok
(`SKILL.md:66`) — and **grok is not installed here** (control-armed: `command -v
grok` → ABSENT, control `codex` → PRESENT). So `mix` as shipped is unusable on
this machine; only `codex` and `grok` fixed modes parse, and grok mode would
route everything to a missing CLI.

- **Supports:** a per-task-class breakdown showing mechanical diffs surviving
  cold review at a high rate while correctness-critical ones don't.
- **Refutes:** the plugin's stated experience that *"When in doubt, codex"*
  (`SKILL.md:66`) — i.e. the vendor's own tuning says Codex is the *stronger*
  lane, not the bulk lane. Adopting C means overriding that with local evidence.

### D. Codex-first with Claude as verifier only

Everything is specced to Codex; Claude reads diffs and judges evidence, never
types. The most aggressive offload.

- **Supports:** `/usage` Claude-side share dropping sharply while the merge rate
  holds; `codex exec --output-schema` producing structured lane reports so the
  Claude verifier reads JSON rather than prose (§2.2).
- **Refutes:** Sol quota exhaustion (§5b) forcing repeated Opus fallbacks; the
  documented degradation of long-lived wrappers — *"end-of-task discipline
  (waiting, reaping, reporting) degrading as the wrapper's transcript grows —
  field-observed as early as ~144k tokens"* (`SKILL.md:111`).

### E. Cheap-teammate discipline instead of cross-vendor offload

Leave Codex out; set `CLAUDE_CODE_SUBAGENT_MODEL=sonnet` (or per-agent
`model: sonnet|haiku`) so a Fable session's teammates stop inheriting Fable.
Directly targets the largest identified amplifier (§5.4: 7x teammate cost,
currently unguarded).

- **Supports:** `/usage` attributing a large share to subagents/teammates today —
  which is checkable *right now* and costs nothing to try.
- **Refutes:** the breakdown showing the architect's own turns dominating, with
  teammates a minor share. Also refuted as a *complete* answer if the user's goal
  is genuinely to shift load onto a **second subscription** they already pay for,
  which E does not do at all.

### F. Antigravity (`agy` / Gemini) as a third lane

`agy 1.1.8` is installed and its plugin ships a break-even-aware delegate agent.
Independent of both budgets.

- **Supports:** `/usage` showing bulk file-generation and long-context digestion
  as a large Claude-side share — exactly what `antigravity-delegate` targets.
- **Refutes:** its own stated break-even — *"delegating a tiny task is a measured
  net loss (round-trip cost exceeds the savings)"* — if the repo's actual work
  units are small. Also a third auth surface and a third quota to reason about.

### 6.1 The decision inputs that are still missing

A routing choice made today would rest on two unmeasured numbers:

1. **The Claude-side wrapper tax per Codex delegation** (§1.3, UNVERIFIED) —
   settled by `/usage`, `w`, reading the `codex-implementer` row.
2. **Pro 5x vs Pro 20x** (§5b, UNVERIFIED) — a 4x difference in Codex headroom,
   settled by `/status` in a Codex session or the usage dashboard.

Both are cheap. Neither is guessable, and this report deliberately does not.

### 6.2 The one thing that is not a matter of taste

The trigger coupling in §4.4 is a **mechanical fact, not a preference**: as
`.claude/CLAUDE.md` is written today, Codex offload only engages when the session
model is Fable. Any option above that assumes "Codex carries the work while I
spend less Fable" requires editing line 81 first. Options A and D are compatible
with the current wiring; B, C, E and F are not, without that edit.

---

## 7. Control arms run (per `probes-need-a-control-arm.md`)

| Negative claim | Probe | Control arm | Verdict |
|---|---|---|---|
| `codex --full-context` does not exist | rc=2 | `codex exec --ephemeral --help` → rc=0 | discriminates ✓ |
| `--full-auto` not in help | `grep -i full-auto` → 0 | `grep -c -- '--sandbox'` → 1 | discriminates ✓ |
| `grok` CLI absent | `command -v grok` → ABSENT | `command -v codex` → PRESENT | discriminates ✓ |
| `OPENAI_API_KEY` absent from env | `[ -n "${OPENAI_API_KEY:-}" ]` → ABSENT | `HOME` → SET | discriminates ✓ |
| `CLAUDE_CODE_SUBAGENT_MODEL` unset | ABSENT | `HOME` → SET | discriminates ✓ |
| Offline harness docs present | `ls $CC/model-config.md $CC/costs.md` → both | `ls $CC \| wc -l` → 175 | discriminates ✓ |

**No credential value was printed at any point.** `auth.json` was parsed for key
names and non-secret scalars only; the `id_token` was decoded to read the
entitlement claim with the account id replaced by `[redacted-id]` before output.
No `security find-generic-password` was run.

---

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex) — the `codex` CLI (v0.146.0) whose `exec` surface, flags and auth model were probed directly on disk.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under study: `.claude/CLAUDE.md` orchestration declaration, `.claude/rules/ai-cli-invocation.md`, `.claude/settings.json`, `.claude/agents/*.md`.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline `agent-harness-docs` tree supplying `$CC/model-config.md`, `$CC/sub-agents.md`, `$CC/costs.md`, `$CC/env-vars.md`, `$CC/workflows.md`.

Non-GitHub sources consulted:

- `fable-orchestrator` plugin v1.14.0 — local marketplace cache at `~/.claude/plugins/cache/fable-orchestrator/`; no public GitHub URL was resolved for it this session (**UNVERIFIED** upstream location).
- `openai-codex/codex` Claude Code plugin v1.0.6 — local cache at `~/.claude/plugins/cache/openai-codex/codex/`; upstream GitHub URL **UNVERIFIED**.
- <https://learn.chatgpt.com/docs/pricing> — OpenAI's Codex plan limits (canonical target of `developers.openai.com/codex/pricing`).
- <https://code.claude.com/docs/en/model-config.md> / `/costs.md` — live equivalents of the offline docs cited above.
