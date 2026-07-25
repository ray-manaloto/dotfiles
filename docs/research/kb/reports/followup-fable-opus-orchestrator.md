# Follow-up: Fable 5 / Opus 4.8 as a Cost-Efficient ORCHESTRATOR over Cheap/Free/Local Workers

**Date:** 2026-07-19
**Scope:** How to run a Claude **Fable 5** (`claude-fable-5`) or **Opus 4.8**
(`claude-opus-4-8`) orchestrator that spends minimal tokens itself and dispatches
well-specified work to cheaper workers — paid (Codex), free-hosted (NVIDIA NIM /
Gemini free tier), or local (Ollama/MLX). Focuses on the *Anthropic-model* side of
the question: the Agent-SDK model-override layer, the honest "Fable-5 system
prompt" analysis, and official Fable-5 worker-guardrail prompting.

**Builds on, does not repeat:**
- `followup-orchestrator-trends.md` — the fable-orchestrator (`BuildContext/fable-orchestrator`)
  architecture, five-part spec contract, deny-hooks, `STATUS:`+watchdog completion
  contract, structured reports, self-repair-against-the-gate. **Assumed as read; I
  reference its mechanisms rather than restate them.**
- `followup-multiprovider.md` — the *plumbing* to reach non-Claude workers:
  `ANTHROPIC_BASE_URL` + LiteLLM/`fcc-server` proxies, free NVIDIA NIM, Ollama/MLX,
  `codex exec`, Gemini free tier, and graphify's `--backend {openai,ollama,gemini}`
  + `OPENAI_BASE_URL`. **Assumed as read; §1 below adds only the SDK-subagent layer
  those reports don't cover and the routing decision between the two seams.**

**Citation honesty (repo discipline, `verify-before-advancing.md` /
`probes-need-a-control-arm.md`):** primary sources (Anthropic platform docs, the
Agent-SDK docs) are marked plainly. Blog/newsletter/tweet-sourced claims are
**[secondary]** or **[informal]**. Benchmark numbers are carried **with the
condition that makes them true**; a bare percentage is not carried forward.

---

## 1. How a Claude orchestrator dispatches to OTHER models — two seams, and which is which

There are exactly **two** wiring seams, and the crucial fact the other two reports
don't state outright is that **they operate at different layers and only one of
them can address non-Claude models per-worker.**

### Seam A — the Agent-SDK `model` override: powerful, but **Claude-only**

The Claude Agent SDK lets an orchestrator define subagents with a per-agent
`model` override. From the SDK `AgentDefinition` reference (primary —
code.claude.com/docs/en/agent-sdk/subagents):

> `model` … *"Model override for this agent. Accepts an alias such as `'fable'`,
> `'opus'`, `'sonnet'`, `'haiku'`, `'inherit'`, or a full model ID. Defaults to
> main model if omitted."*

So a Fable-5 (or Opus-4.8) main loop can fan out Haiku/Sonnet subagents, each with
its own `prompt`, `tools` allowlist, `skills`, `effort`, `maxTurns`,
`permissionMode`, and `background` — full context isolation (each subagent gets a
fresh window; only its final message returns to the parent). The `model` field
also works in filesystem subagents (`.claude/agents/*.md` YAML frontmatter:
`model: haiku|sonnet|opus|fable|inherit`) [secondary — developersdigest, consistent
with the SDK doc].

**The limit that matters for this task:** every value the `model` field accepts is
a *Claude* alias or a Claude model ID. The whole SDK/harness authenticates against
one Anthropic-compatible endpoint (`ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`),
and a subagent inherits that endpoint. **There is no per-subagent provider field.**
A GitHub feature request against `github/copilot-cli` (#2939) asks for exactly this
cross-provider parity and frames the Claude Agent SDK as *"supports `model` field
on AgentDefinition"* but still single-provider [secondary — github issue, treated
as a statement of the gap, not proof]. Consequence: **you cannot make a Fable-5
orchestrator's SDK subagent run on Codex/Grok/NIM/Ollama by setting `model`.** Those
workers are not subagents at all — they are Bash tool calls (Seam B).

The one way to bend Seam A to a non-Claude model is to point the *entire harness*
at a translating proxy (`ANTHROPIC_BASE_URL` → LiteLLM/`fcc-server` → NIM/Ollama).
But that is **session-wide** — it swaps the model under the orchestrator *and* every
subagent at once (`followup-multiprovider.md` §1). It cannot give you "strong Claude
orchestrator, cheap non-Claude worker" because there is only one endpoint for the
whole tree. Proxy-swapping is how you run *the whole thing* cheap, not how you split
roles across vendors.

### Seam B — shell-out to an external CLI: the real cross-vendor path

Cross-vendor delegation is a **tool call**, not a subagent. The orchestrator (native
Anthropic API, its own key) calls Bash to run a headless worker CLI and reads its
stdout as a structured report:

- **`codex exec`** — `echo "$SPEC" | codex exec --full-auto --sandbox workspace-write -`
  for implementation, or `--ephemeral --sandbox read-only -` for research
  (`.claude/rules/ai-cli-invocation.md`; plumbing in `followup-multiprovider.md` §3).
- **`gemini -o text --approval-mode yolo -p ""`** (stdin prompt), free tier.
- **`graphify … --backend {ollama,openai,gemini}`** — extraction workers where
  `--backend ollama` is $0/local, `--backend openai` + `OPENAI_BASE_URL` reaches a
  free NIM endpoint, `--backend gemini` the free tier (`followup-multiprovider.md`
  §4). graphify also **auto-detects** a backend by API-key priority
  (Gemini→Kimi→Claude→OpenAI→DeepSeek→Azure→Bedrock→Ollama) if `--backend` is
  omitted [secondary — safishamsi/graphify README].
- **A LiteLLM-fronted generic worker CLI** — one OpenAI-compatible endpoint that
  fans out to NIM/Ollama/OpenRouter behind config, so the orchestrator's Bash call
  is provider-agnostic.

This is precisely what `fable-orchestrator` does: Grok 4.5 is reached through
`run-grok-headless.sh` (a Bash launcher), **not** an SDK subagent
(`followup-orchestrator-trends.md`). The launcher is load-bearing because a raw
shell-out has none of the SDK's safety rails — so it must carry the completion
contract (`STATUS:` + incomplete-stamp), the wall/stall watchdog, and PID-file lane
identity itself.

### The clean wiring for "strong Claude orchestrator → cheap/free/local workers"

Combine both seams by *worker vendor*, not by habit:

| Worker | Seam | Mechanism | Why |
|---|---|---|---|
| Cheap **Claude** (Haiku/Sonnet) | **A (SDK subagent)** | `model: 'haiku'` / `'sonnet'` + `tools` allowlist + `effort` | free context isolation, tool restriction, per-agent skills, cost tracking — all native |
| **Non-Claude** (Codex/Grok/NIM/Gemini) | **B (Bash shell-out)** | `codex exec` / CLI behind a completion-contract launcher | SDK can't address a foreign provider per-subagent; a wrapped CLI can |
| **Local** (Ollama/MLX) | **B (Bash shell-out)** | `graphify --backend ollama`, or a llama.cpp/Ollama CLI | $0, private, no rate limit; still needs the launcher's watchdog |
| *Everything cheap, no role split* | **proxy (session-wide A)** | `ANTHROPIC_BASE_URL` → LiteLLM → NIM/Ollama | only when you don't need a strong orchestrator at all |

**Net:** keep the **orchestrator native** (real Anthropic key, so it's genuinely
Fable/Opus and not a proxied impostor); use **Seam A** for cheap *Claude* workers
(the SDK does the isolation for free) and **Seam B** for every *non-Claude/local*
worker (wrapped in `fable-orchestrator`'s launcher so a foreign CLI can't hang or
fake success). Do **not** try to force non-Claude workers through the `model` field —
it silently can't, and the failure mode is the orchestrator quietly doing the work
itself (`fable-orchestrator`'s `block-named-cli-lane.py` guards exactly this class).

---

## 2. "Opus 4.8 with Fable 5's system prompts" — precise and honest

### Is there a "Fable 5 system prompt"? Two very different artifacts — don't conflate them.

**(a) The leaked prompt is the Claude *product* harness prompt, NOT an "orchestrator
mode."** On ~2026-06-10 (a day after Fable 5's June 9 launch) a ~**120,040-char /
1,585-line / ~30k-token** file surfaced (Pliny "the Liberator"; mirrored in
`asgeirtj/system_prompts_leaks` and the CL4R1T4S repo). Multiple write-ups agree it
*"reads like a product spec: tool schemas, search rules, safety postmortems"* with
**18 full tool definitions** and an identity line (*"The assistant is Claude…"*) not
appearing until line 1,351 — and a section on *"Claudeception"* (Claude artifacts
calling the Claude API) [secondary — nowrap.ai "what we could verify", horiamc.com,
analyticsvidhya, alphasignal; **Anthropic has not confirmed it**, and extraction can
introduce gaps or hallucinated passages]. **This is the consumer/Claude-Code product
system prompt.** It is *not* an orchestration playbook, contains no "delegate to
cheap workers" doctrine, and copying it onto Opus 4.8 would only import ~30k tokens
of product-harness plumbing (artifacts, web tools, safety) irrelevant to
orchestration — a context tax, not a capability. **Do not use the leak as an
"orchestrator system prompt." It isn't one.**

**(b) The real, official, citable orchestration guidance is a public Anthropic doc:
"Prompting Claude Fable 5"** (primary — platform.claude.com/…/prompting-claude-fable-5).
It contains the actual delegation/long-run prompt snippets (quoted in §3). *This* is
what "Fable-5 orchestration prompting" means, and it is not secret or leaked — it's
documentation. There is also an official Anthropic **webinar** *"Building on the
Claude Platform: Claude Fable 5 and model orchestration patterns"* whose page
teaches *"when Fable or Opus should plan and delegate while Sonnet and Haiku
execute"* and cost management via *"effort levels, prompt caching, batch processing,
and task budgets"* — but the page carries **no benchmark numbers or concrete
orchestrator-prompt text** (recording not posted at fetch time) [primary page,
thin].

### What transferring a system prompt to Opus 4.8 CAN and CANNOT do

This is the crux the maintainer flagged, and the honest answer is a clean split:

- **CAN transfer (workflow / behavior / output-format):** the *instructions* in the
  "Prompting Claude Fable 5" doc — act-when-ready, state-boundaries, ground-progress,
  the autonomous-operation stop-contract, the send-to-user tool, fresh-context
  verifier subagents. **These are model-agnostic system-prompt ADDITIONS authored by
  the user** (not weights, not secret to Fable). They will make Opus 4.8 *behave*
  more like a disciplined orchestrator — shorter messages, fewer fabricated status
  reports, cleaner stop conditions. **You should apply them to Opus 4.8.** There is
  nothing to "leak" here; it's a docs page.

- **CANNOT transfer (trained capability):** the doc explicitly frames Fable 5's edge
  over Opus 4.8 as *trained*, not promptable — *"Long-horizon autonomy… completing
  multiday, goal-directed runs"* and *"Delegation and collaboration. Claude Fable 5
  is significantly more dependable at dispatching and sustaining parallel subagents,
  and reliably manages ongoing communication with long-running subagents and peer
  agents"* (primary). A system prompt cannot give Opus 4.8 Fable's trained
  delegation reliability or its multiday instruction-retention. You get the
  *choreography*, not the *stamina*. Prompt = the score; the model = the musician.

- **A real trap when copying prompts to/from Fable:** the same doc warns *"Prompts,
  skills, or harness instructions that tell the model to echo, transcribe, or explain
  its internal reasoning as response text can trigger the `reasoning_extraction`
  refusal category on Claude Fable 5, causing elevated fallbacks to Claude Opus 4.8"*
  (primary). And *"Skills developed for prior models are often too prescriptive for
  Claude Fable 5 and can degrade output quality."* So the transfer is **not
  symmetric**: heavy scaffolding that helps Opus (or a cheap worker) can *hurt* Fable,
  and a show-your-reasoning instruction that's fine on Opus can force refusals on
  Fable. Prompts must be tuned per model, not cloned.

**Bottom line for Q2:** There is no secret "Fable 5 orchestrator prompt" to graft
onto Opus 4.8. The leaked file is the product prompt (skip it). The *useful*
Fable-orchestration prompting is a public doc, is model-agnostic, and *should* be
applied to whichever Claude you orchestrate with — but applying it to Opus 4.8 buys
you Fable-*style behavior*, never Fable's *trained* long-horizon-delegation ability.

---

## 3. Worker-guardrail design — official Fable-5 additions on top of the prior report

`followup-orchestrator-trends.md` already establishes the buildable guardrail stack
(tight role/scope; five-part spec contract — Objective+MODE · Files · Interfaces ·
Constraints · Verification; structured/constrained output; PreToolUse **deny**
tool-allowlist; `STATUS:` completion contract + wall/stall watchdog + retry cap ~3;
verify-gate-as-oracle = `mise run lint` + `pytest` + `dotfiles-setup verify run`).
The new, **primary-sourced** contribution here is that Anthropic's "Prompting Claude
Fable 5" doc ships *exact prompt text* for several of those guardrails — use these
verbatim as worker/orchestrator system-prompt blocks (all primary):

- **Explicit completion / stop contract** (the mechanism behind "worker claims done
  but stalls"): *"You are operating autonomously. The user is not watching in real
  time… asking 'Want me to…?' will block the work. For reversible actions that follow
  from the original request, proceed without asking… Before ending your turn, check
  your last paragraph. If it is a plan, an analysis, a question, a list of next steps,
  or a promise about work you have not done ('I'll…'), do that work now with tool
  calls. End your turn only when the task is complete or you are blocked on input only
  the user can provide."* This is the prose twin of `fable-orchestrator`'s `STATUS:`
  contract — put it in every autonomous worker.
- **Progress-claim grounding (anti-hallucinated-status):** *"Before reporting
  progress, audit each claim against a tool result from this session. Only report work
  you can point to evidence for; if something is not yet verified, say so explicitly.
  If tests fail, say so with the output."* The doc reports this *"nearly eliminated
  fabricated status reports even on tasks designed to elicit them"* — directly the
  same failure our `verify-before-advancing.md` guards against. Pair it with the
  gate-as-oracle so "done" means an exit code, not a sentence.
- **Verification by a fresh-context verifier subagent, not self-critique:**
  *"Separate, fresh-context verifier subagents tend to outperform self-critique… Run
  this every [X interval], verifying your work with subagents against the
  specification."* Matches `fable-advisor`'s "fresh context = no sunk-cost bias" role
  in the prior report.
- **Scope containment:** *"Don't add features, refactor, or introduce abstractions
  beyond what the task requires… Only validate at system boundaries."* and *"the
  deliverable is your assessment. Report your findings and stop. Don't apply a fix
  until they ask for one."* — cheap workers burn the most context on unrequested
  tidying; this is the brevity lever.
- **Verbatim-output channel:** the `send_to_user` tool + elicitation snippet, so a
  long worker surfaces a deliverable *"exactly as written"* without ending its turn
  (tool inputs are never summarized).

**Honest caveat on applying these to *cheap/local* workers.** These snippets were
written for Fable 5, which *"you can steer… with a brief instruction rather than
enumerating each behavior."* A Haiku/Sonnet or a small local model is the **opposite**
— it needs the *more* prescriptive, enumerated version, plus the hard mechanical
rails (constrained decoding, deny-hook, watchdog) because it will not reliably follow
a terse instruction. So the guardrail intensity is **inversely proportional to worker
capability**: thin prose for a Fable worker, thick prose + machine gates for a cheap
one. One measured cheap-worker knob [secondary — explainx, attributed to Anthropic
internal evals]: for a Haiku executor, *"nudge on turn 2 if [the] advisor [was]
skipped turn 1"* gave a **~7-percentage-point lift** — condition: Haiku-executor +
advisor pattern, Anthropic-internal, not independently reproduced.

**The single most load-bearing guardrail remains the objective gate.** Everything
above shapes *behavior*; only the verify-gate (compiler/tests/`verify run`) makes a
cheap model's *output* trustworthy, and it's the one the strong model defines and
reads (`followup-orchestrator-trends.md` §4; carried forward).

---

## 4. Articles / blogs, last ~1 month (2026-06 / 2026-07)

Ordered primary → secondary → informal. Trace load-bearing numbers to their stated
condition.

**Primary (Anthropic):**
- **"Introducing Claude Fable 5 and Claude Mythos 5"** — launch June 9, 2026;
  `claude-fable-5`; **1M context, 128k output; $10/M in, $50/M out**; adaptive
  thinking only; raw CoT never returned; safety classifiers can return
  `stop_reason:"refusal"` and route to a fallback (Opus 4.8). (platform.claude.com)
- **"Prompting Claude Fable 5"** — the orchestration/delegation prompt snippets used
  in §3; the `reasoning_extraction` refusal trap; "skills too prescriptive for Fable
  can degrade output." (platform.claude.com)
- **Webinar: "Fable 5 and model orchestration patterns"** — official framing of
  advisor/orchestrator ("*a smaller, cheaper model does the work and Fable 5 sets the
  strategy*", "*frontier-level results at a fraction of the token cost*"); no numbers
  on the page. (anthropic.com/webinars)
- **"Redeploying Fable 5"** — Anthropic news noting access to Fable 5 was
  *restored* (there was an interruption; details not load-bearing here).
  (anthropic.com/news)

**Secondary (numbers, condition-flagged — treat as direction, not targets):**
- **explainx "Fable 5 Advisor & Orchestrator patterns" (July 2026)** — the two named
  patterns and their evals: **Advisor (Sonnet 5 executes, Fable advises): ~92%
  quality / ~63% cost vs Fable-solo on SWE-bench Pro**; **Orchestrator (Fable plans,
  Sonnet workers execute): ~96% quality / ~46% cost vs Fable-solo on BrowseComp
  (CMA)**. Attribution stated in-article: *"@ClaudeDevs July 8 tweets… Anthropic
  internal evals, not independent reproduction."* Also: advisor tokens bill as
  `type:"advisor_message"` in `usage.iterations[]`; cap advisor output via
  `max_tokens` (≥1,024; 2,048 rec.); enable ephemeral prompt caching on tool defs if
  ≥3 advisor calls. **[secondary/informal — tweet-sourced, unreproduced].**
- **developersdigest "Fable 5 Orchestrator Playbook"** — worked 12-worker audit:
  Fable-orchestrator **$2.50**; mixed Fable+Sonnet fleet **$6.10**; all-Fable
  **$14.50** → *"58% savings vs all-Fable; 74% with Haiku workers."* Worker routing:
  Sonnet=implementation, Haiku=search/read-only, Opus 4.8=escalation for
  safeguarded/complex. Hard constraints: **Haiku 200k context cap** (vs 1M);
  Fable/Opus tokenizer produces *"up to 35% more tokens for the same text"*; Fable
  30-day retention (incompatible with ZDR). **[secondary — the dollar figures are an
  illustrative worked example, not a benchmark].**
- **mindstudio "Fable 5 orchestrator without burning your token budget"** — general
  cost framing consistent with the above. **[secondary].**
- Leak analyses (**ayautomate, analyticsvidhya, alphasignal, horiamc, nowrap,
  memeburn, Medium/Mehul Gupta**) — all describe the same ~120k-char product-prompt
  leak (§2a). nowrap's *"what we could verify"* is the most careful. **[secondary;
  Anthropic-unconfirmed].**

**Informal:** the `@socialwithaayan` / `@ClaudeDevs` X posts are the origin of the
leak-size figures and the advisor/orchestrator eval numbers respectively; both are
**tweets**, load-bearing claims traced above to the more careful secondary write-ups
and, where possible, to the primary docs.

**Net trend for this quarter:** Anthropic itself is now *promoting* the
strong-plans/cheap-executes split as the headline cost pattern for Fable 5 (a
webinar, a prompting doc section, an official advisor/orchestrator vocabulary) — the
category the prior report saw productized in Sakana Fugu is, for the Claude stack,
now first-party guidance.

---

## 5. Concrete recommended orchestrator setup (has BOTH Opus 4.8 + Fable 5 + free/local workers)

**Which model orchestrates: Fable 5, at `effort: high`, kept token-thin — Opus 4.8
as the *fallback* target, not the primary orchestrator.** The reasoning is
cost-honest, not brand loyalty:

- The orchestrator's job *is* the one thing Fable 5 is specifically trained to do
  better than Opus 4.8 — *"dispatching and sustaining parallel subagents… long-horizon
  autonomy"* (primary). Spend the frontier rate ($10/$50) on the **small,
  role-partitioned orchestrator token budget** (specs + accept/reject only), and the
  commodity rate on the volume — *"the frontier rate where errors compound and the
  commodity rate where they do not"* [secondary — developersdigest]. In the worked
  example the Fable orchestrator was ~$2.50 of a $6.10 mixed run; the delegation
  reliability is worth the small premium exactly because the orchestrator emits few
  tokens.
- **Opus 4.8 earns two roles regardless:** (1) it is the **mandatory refusal
  fallback** — Fable's safety classifiers return `refusal` on cybersecurity/bio/
  reasoning-extraction and the docs route those to Opus 4.8 (wire `fallbacks` or SDK
  middleware); (2) it is the **cheaper-orchestrator option** ($5/$25) when the run is
  latency-sensitive, ZDR-bound (Fable mandates 30-day retention), or the orchestrator
  token budget is *not* small — then orchestrate on Opus 4.8 and accept somewhat
  weaker trained delegation. Give Opus 4.8 the §3 prompt snippets to close as much of
  the behavioral gap as prompting can (which is the choreography, not the stamina).

**Prompt / skill scaffolding (thin, on-demand):**
1. **Thin orchestrator system prompt** built from the *public* "Prompting Claude Fable
   5" snippets (§3): act-when-ready, state-boundaries, autonomous-operation
   stop-contract, ground-progress, self-verification-via-fresh-context-verifier,
   `send_to_user`. **Do NOT paste the leaked product prompt** (~30k-token tax,
   product-not-orchestrator, unconfirmed). Do NOT add show-your-reasoning
   instructions (Fable `reasoning_extraction` refusal trap).
2. **Orchestration doctrine as an on-demand skill**, not always-on context
   (`fable-orchestrator`'s pattern; keeps the permanent prompt to ~one screen and
   prompt-cache-friendly). Refactor/trim prescriptive legacy skills for Fable
   (docs: over-prescription degrades its output).
3. **Five-part spec contract** as the only orchestrator→worker interface; workers
   share zero orchestrator context and return only compressed structured reports
   (`followup-orchestrator-trends.md`).

**Guardrails on workers (intensity inversely proportional to worker capability):**
- **Cheap Claude workers (Seam A subagents):** `model: 'haiku'|'sonnet'`, a hard
  `tools` allowlist, `effort` tuned down, `maxTurns` capped; the §3 prompt blocks in
  the *enumerated* (thicker) form.
- **Non-Claude / local workers (Seam B shell-outs):** wrap every `codex exec` /
  `graphify --backend ollama` / LiteLLM-CLI call in `fable-orchestrator`'s
  completion-contract launcher (`STATUS:` + incomplete-stamp + wall/stall watchdog +
  PID-file identity); **constrained/structured output** (Ollama's native `format:`
  JSON-schema, `followup-multiprovider.md`) to cut retries; retry cap ~3.
- **Everyone:** the **objective verify-gate as the completion oracle** — `mise run
  lint` + `pytest` + `dotfiles-setup verify run`; `STATUS: pass` only on green
  exit codes; self-repair-against-the-gate loop (cap ~3, arXiv 2607.05197 per prior
  report). Enforce the orchestrator's no-product-write with a **PreToolUse deny-hook**
  (our `hook_guard.py` precedent), because "prose is ignored under pressure."

**Honest trade-offs:**
- **Seam A can't reach non-Claude models** — the `model` field is Claude-only; every
  free/local worker is a Bash shell-out (Seam B), which *loses* the SDK's automatic
  context-isolation and cost-tracking and *gains* vendor diversity + $0/local cost.
  You maintain the launcher yourself.
- **`ANTHROPIC_BASE_URL` proxying is session-wide**, so it cannot express "strong
  orchestrator + cheap worker" — it's an all-or-nothing cheap mode. Don't reach for it
  to split roles.
- **Fable specifics:** 30-day retention (no ZDR); tokenizer ~35% more tokens for the
  same text (so its per-token price bites a bit harder than the sticker); refusal
  classifiers mean you *must* build the Opus-4.8 fallback path before shipping.
- **The eval numbers (92/63, 96/46, 58%/74%) are tweet-/example-sourced, Anthropic-
  internal or illustrative, and unreproduced** — use them as direction and
  **re-measure on our own workloads** (`probes-need-a-control-arm.md`). The
  architecture recommendation does **not** depend on the exact deltas; it depends on
  the two robust facts: (a) Fable is *trained* for delegation and (b) the orchestrator
  emits few tokens, so paying frontier rate for it is cheap in absolute dollars.
- **The maintainer's real lever is the worker contract, not the orchestrator model.**
  Whether you orchestrate on Fable or Opus, a cheap worker stops burning context on
  wrong turns because of the spec contract + constrained output + tool-allowlist +
  watchdog + verify-gate — the same stack in both reports. The model choice moves the
  cost/reliability of the *dispatch*; the guardrails move the cost of the *work*.

---

## GitHub repos touched

- [BuildContext/fable-orchestrator](https://github.com/BuildContext/fable-orchestrator) — referenced (not re-read) for the launcher / deny-hook / STATUS-contract mechanisms carried from `followup-orchestrator-trends.md`.
- [safishamsi/graphify](https://github.com/safishamsi/graphify) (a.k.a. Graphify-Labs/graphify) — read README/search for `--backend {ollama,openai,gemini}`, `OPENAI_BASE_URL`/`OLLAMA` overrides, and the API-key backend auto-detect priority.
- [asgeirtj/system_prompts_leaks](https://github.com/asgeirtj/system_prompts_leaks) — the `Anthropic/claude-fable-5.md` leaked *product* system prompt (§2a); cited as the leak artifact, **not** as an orchestrator prompt; Anthropic-unconfirmed.
- [github/copilot-cli](https://github.com/github/copilot-cli) (issue #2939) — cited as evidence that per-subagent *provider* override is a not-yet-shipped feature, and that the Claude Agent SDK's `model` override is single-provider.

_Primary docs consulted (not GitHub repos): platform.claude.com "Introducing Claude Fable 5 / Mythos 5", "Prompting Claude Fable 5", and code.claude.com/docs Agent-SDK "Subagents in the SDK"; anthropic.com webinar + "Redeploying Fable 5" news. Secondary/informal blogs enumerated in §4._
