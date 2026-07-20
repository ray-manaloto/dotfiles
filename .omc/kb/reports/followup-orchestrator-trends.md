# Follow-up: Strong-Model-as-Orchestrator over Cheaper/Local Workers — Techniques to Build

**Date:** 2026-07-19
**Scope:** Techniques and features (not just products) for a strong model
(Claude/Fable 5) acting as an ORCHESTRATOR that plans and delegates to
cheaper/local worker models, optimizing cost + context + code-output quality.
Anchored on the maintainer's reference to **BuildContext/fable-orchestrator**
(Fable 5 conducts, Grok 4.5 Heavy implements).

**How to read the citations:** claims traced to a primary source (a repo's own
files, an arXiv paper, a vendor doc) are marked plainly. Claims that survive
only on a blog/newsletter/vendor-marketing source are labelled **[secondary]**
or **[informal]**, per the repo's "a fact needs its source AND its condition"
discipline (`.claude/rules/verify-before-advancing.md`,
`probes-need-a-control-arm.md`). Benchmark numbers are reported WITH the
condition that makes them true (model pairing, dataset) — a bare percentage is
not carried forward.

---

## 1. BuildContext/fable-orchestrator — concrete read of the source

Read directly from the repo (`master` branch, v1.2.2, updated 2026-07-19):
`README.md`, `skills/orchestration/SKILL.md`, `agents/grok-implementer.md`,
`agents/fable-advisor.md`, `scripts/run-grok-headless.sh`, `hooks/`.

### What it is

A **Claude Code plugin** that runs the "architect pattern": the smartest model
in the chair (Claude **Fable 5**) owns requirements, decomposition, specs,
routing, and accept/reject; a **cheaper cross-vendor lane** (Grok 4.5 Heavy via
its headless CLI) does all the typing. It is a hardened fork of
`DannyMac180/fable-advisor` (the "pure cost/routing essay"); this fork adds
**hard gates** (deny-hooks, a shell launcher, a completion contract) learned
from real React-Native/Expo autonomous sessions. Tagline: *"Fable thinks. Grok
types. STATUS decides. Ledger remembers."*

### The orchestration model — yes, strong-plans / cheap-executes

The README's own diagram: Fable 5 = "session architect · specs · routing ·
STATUS accept/reject · ledger"; below it three MODE lanes (`explore` /
`implement` / `verify`) all feeding **Grok 4.5 Heavy · headless CLI**. The core
principle, verbatim:

> **"Tokens route by role, not by habit:** Fable emits judgment; Grok emits
> volume; Argent evidence comes back as paths, not screenshot dumps into the
> architect transcript."

The `orchestration` SKILL states it as a cost model: *"Architect tokens are the
scarce resource; external CLI tokens are the volume path… Inline architect
implementation is a **quota failure**."* The strong model is explicitly
forbidden from editing product code — enforced by a hook, not prose (see below).

### Token / context optimizations it actually implements

These are the reusable parts — each is a buildable technique, not a product:

1. **Role-partitioned token budget.** The architect emits only specs +
   accept/reject verdicts. Any "broad search/read/log/diff" is pushed to a Grok
   lane; only *conclusions* return to the architect session. The architect has
   an explicit **"no-touch" table**: no `Write/Edit` under `src/`, no reading
   product files >~80 lines "to understand", no full `git diff`/`tsc`/jest logs
   in the transcript — those become `MODE: explore`/`verify` specs that return
   "tables + exit codes".

2. **Compressed structured reports as the only interface.** Workers return one
   of three fixed shapes — `EXPLORE REPORT` (paths, symbols, ≤15-line
   excerpts), `GROK REPORT` (STATUS, CHANGES one-line-per-file, DIFF STAT, ≤3
   RISKY HUNKS of ≤15 lines, VERIFIED, GAPS), `VERIFY REPORT` (commands, exit
   codes, first N errors). The architect *"does not re-read the whole tree to
   double-check"* — it trusts the structured evidence. This is the single
   biggest context saver: the expensive context never ingests the raw tree.

3. **Doctrine in an on-demand skill, not always-on context.** The routing rules
   live in `skills/orchestration/SKILL.md` (loaded only when orchestration is
   relevant), keeping the always-on `CLAUDE.md` to "~one screen". Rationale
   verbatim: *"Always-on project docs stay thin… Full doctrine loads when
   orchestration is relevant — less permanent context tax."* Device/UI ("Argent")
   skills are likewise loaded on demand ("Fourteen full device skill bodies
   would drown the architect").

4. **A durable ledger to survive compaction.** `docs/LEDGER.md` holds one
   checkbox line per work unit; ticked `[x]` **only** on a `STATUS: pass|complete`
   report + evidence. It is the "shared truth across turns when chat context is
   compacted" — an external, cheap state store so the long chain doesn't
   recompute what it already accepted. *"Do not dump full agent reports into the
   ledger — paths and STATUS only."*

5. **Metrics without transcript bloat.** Each headless run appends ONE JSON line
   to `~/.claude/fable-orch/metrics.jsonl` — `{ts, rc, wall_s, best_of_n, cwd,
   status, stall_s}`, **no prompt text** (confirmed in `run-grok-headless.sh`).
   Observability that costs zero context.

### How it routes work

- **Five-part spec contract** on every delegation (workers share *none* of the
  architect's context): **Objective (with MODE) · Files · Interfaces ·
  Constraints · Verification**. "Can't finish the spec → the decision isn't made
  yet. That's architect work, not a reason to dump ambiguity on Grok."
- **Two-level parallelism.** *Level A* — the architect fans out N
  `grok-implementer` agents in ONE message over independent (non-overlapping
  write-path) units (prefers 3–6 parallel explores). *Level B* — a single Grok
  session spawns its own depth-1 `explore`/`plan` subagents and merges before
  reporting (`SUBAGENTS: N`). Routing rule: independent units with separate
  accept/reject → Level A; one unit with internal parallel research → Level B.
- **A second opinion via `fable-advisor`** — same strong model, *fresh context*,
  read-only, ≤300 words, invoked at commitment boundaries (architecture,
  migration, "are we done?", or after two failed attempts). Fresh context =
  "reads code without the conversation's sunk-cost bias."

### The hard-gate mechanisms (the "field manual" delta over upstream)

These are the parts worth stealing wholesale, because each fixes a *measured*
autonomous-agent failure:

- **`hooks/block-architect-product-write.py`** (PreToolUse deny): the strong
  model physically cannot write `src/`, `ios/`, `android/`, lockfiles,
  `app.config.*`, `eas.json`, `locales/`, `assets/`. Rationale: *"Prose ('don't
  implement yourself') is ignored under pressure. Hooks deny."* (This is exactly
  our repo's own PreToolUse-guard philosophy — `mise-tasks-only.md`.)
- **`hooks/block-named-cli-lane.py`**: blocks spawning the worker **with** a
  `name` parameter. Combat bug: a *named* spawn "can strip the agent tool
  whitelist → Sonnet **silently self-implements** and fakes a Grok report." The
  fix is a hook + "spawn without name." (A concrete instance of a cheap-model
  handoff silently degrading to the expensive model doing the work — worth
  guarding against in any router.)
- **`STATUS:` completion contract + `run-grok-headless.sh`.** Done ⇔ the report
  body contains `STATUS: …`. If the model exits without it, the launcher
  **stamps `STATUS: incomplete`** (never auto-`complete`). The launcher also
  carries a **wall-clock + stall watchdog** (kills the headless PID if
  `final.txt` stops growing; default stall = timeout/3, clamped 300–900s),
  uses `${FINAL}.pid` for lane identity (never `ps | grep grok` — a false-alive
  trap), and forces one-shot headless flags: `--prompt-file · -m grok-4.5 ·
  --always-approve · --output-format plain · --cwd · stdin /dev/null`. The
  "worker claims done but did nothing / hangs forever" class is solved
  mechanically, not by hope.
- **Optional best-of-N** for *hard* implement tasks only: `GROK_BEST_OF_N=3`
  (5th arg). A cheap-model quality knob applied selectively, logged in metrics.

### Reusable-as-technique summary

The transferable ideas: (a) role-partitioned token budget with a strong-model
no-touch list enforced by a **deny-hook**; (b) **compressed structured reports**
as the only cross-model interface; (c) a **five-part spec contract** so workers
need zero shared context; (d) an **external ledger** for state across
compaction; (e) a **machine completion contract** (`STATUS:` + watchdog +
incomplete-stamp) so autonomy can't hang or fake success; (f) **on-demand skill
loading** to keep permanent context thin; (g) **selective best-of-N** only where
quality is hard.

---

## 2. Orchestrator → worker patterns generally

### Plan-and-execute (planner/executor split)

A planner LLM produces an inspectable step plan; a cheaper executor carries out
each step and the planner revises on results. "The Executor can be a much
simpler, more specialized, less computationally expensive component than the
Planner — a smaller/faster LLM, a simple ReAct agent, or even deterministic
code" [secondary — futureagi.com, aimultiple.com, 2026]. Security-hardened
"plan-then-execute" variants exist as a design guide (arXiv 2509.08646). Fits
**multi-step agent tasks** and **ticket implementation** best: the plan is the
audit surface, execution nodes are swappable/cheap.

### Strong-plans + cheap-executes / router + cascade

Two production idioms, both measured:

- **Routing** (pick the cheapest capable model per query up front) and
  **cascading** (flow through increasingly capable models, stop when a quality
  threshold is met). "Pre-request rules are cheapest; at-inference cascades are
  most accurate; post-response retry is the safety net" [secondary — TianPan,
  digitalapplied.com]. A unified routing+cascading treatment: ETH Zürich, arXiv
  2410.10347; calibrated-uncertainty cascade routing, arXiv 2605.18796; cluster-
  route-escalate, arXiv 2606.27457.
- **RouteLLM** (LMSYS) is the canonical open router: in its own evals, **85%
  cost savings while keeping 95% of GPT-4 quality — condition: MT-Bench, GPT-4-
  Turbo vs Mixtral-8x7B pairing**; with LLM-judge data augmentation, 95% quality
  at 14% strong-model calls (~75% cost reduction). The authors explicitly say
  these numbers are "proof the technique works, not the number you will hit"
  [RouteLLM paper via LMSYS, cited in leanlm.ai/burnwise 2026]. Best cost/quality
  trade for **high-volume, heterogeneous-difficulty** work; less so for a small
  number of hard tickets where you'd always route strong anyway.

### Draft-then-verify (cheap draft, strong critique)

Two distinct things share this name — don't conflate:

- **Token-level speculative decoding**: a small draft model proposes N tokens;
  the target verifies them in one forward pass; output is *provably identical* to
  the target alone. 2–5× faster inference, up to 3.78× on code-gen benchmarks
  with no quality loss (arXiv 2510.00294, 2412.00061; BentoML/Friendli guides
  2026). This is an *inference-speed* optimization inside one model pair, mostly
  a serving-layer concern (vLLM/SGLang) — relevant only if we self-host workers.
- **Agent-level draft-then-critique**: cheap model drafts an artifact, strong
  model critiques/repairs. This is the orchestration-level pattern and is where
  the cost/quality lift for **code generation** comes from (see §4).

### Map-reduce over chunks

Split a large corpus/task into independent chunks, process each with a cheap
worker (map), then a strong model reduces/merges. This is exactly Fable's Level-A
explore fan-out, and exactly GraphRAG's "extract per chunk → summarize community
clusters" pipeline (Microsoft GraphRAG, arXiv 2404.16130). **Best fit for
knowledge-graph extraction** and for repo-wide exploration.

### Spec-then-implement

Strong model writes a precise spec (interfaces, constraints, verification), cheap
model implements against it. Fable's five-part contract is the concrete
instance. Best cost/quality for **code generation with clear interfaces**; the
strong model's tokens go into the spec once, the cheap model absorbs the volume.

### Which pattern wins per workload

| Workload | Best pattern | Why |
|---|---|---|
| (a) Code generation (tickets) | **spec-then-implement + cheap-executes + a hard verify gate** | interfaces pin the cheap model; the gate (tests/compiler) is what actually lifts quality (§4) |
| (b) KG extraction (graphify) | **map-reduce + structured-output workers + strong-model reduce** | per-chunk extraction is embarrassingly parallel; strong model only merges/dedupes entities |
| (c) Multi-step agent tasks | **plan-and-execute + router/cascade + ledger** | inspectable plan, cheap steps, escalate hard steps, external state across compaction |

---

## 3. Context + token optimization techniques (buildable)

Ranked by build-value for our orchestrator:

1. **Sub-agent context isolation (highest value, already native).** Route the
   main loop to the strong model; spawn small-model sub-agents for cheap,
   parallelizable sub-tasks so the main loop's cache and budget stay intact. In
   the Claude Agent SDK every `ResultMessage` carries `total_cost_usd` + per-model
   token usage, so you can measure the split [secondary — helply.com,
   totalum.app 2026; consistent with Anthropic SDK docs]. This is Fable's whole
   design and our existing sub-agent model — extend it, don't rebuild it.

2. **Prompt caching (highest ROI, must design for).** Anthropic cached reads
   cost **10% of normal input** ($0.50/M vs $5/M); at a 90% hit rate a "$100
   session costs ~$19" [secondary — finout.io, mindstudio 2026; primary:
   platform.claude.com prompt-caching doc]. **Buildable lever:** put the STABLE
   prefix (system prompt, orchestration doctrine, spec templates, graph schema)
   FIRST and identical across calls so it caches; put volatile per-task content
   last. This interacts with our concern about MCP schema injection — a stable
   tool schema is cache-friendly; a churning one busts the cache.

3. **Context compaction / summarization.** Anthropic ships server-side
   compaction (beta header `compact-2026-01-12`) that condenses older history to
   a summary as the window fills [secondary — mindstudio; primary: platform docs].
   For our own orchestrator the buildable equivalent is the **external ledger**
   (Fable's `LEDGER.md`) — cheaper and more controllable than re-summarizing,
   because *we* decide what persists (STATUS + evidence paths only).

4. **RAG over our own graphify graph (strong fit for our goal).** GraphRAG's
   "traverse the subgraph for multi-hop context" is the retrieval story; a May-2026
   benchmark across 47 deployments claims agentic-RAG-with-KG cut hallucination
   ~62% at the cost of latency/orchestration complexity [secondary — MLOps
   Community via jobsbyculture 2026]. **Buildable:** the graphify graph becomes
   the retrieval index that injects *just the relevant subgraph* into a worker's
   context instead of raw files — turning "read the tree to understand" into a
   cheap, targeted injection. This is the highest-leverage synergy with our
   existing graphify investment.

5. **Structured-output constraint to cut retries.** Constrained/grammar decoding
   (Outlines, Guidance, XGrammar — the default backend for vLLM/SGLang/TensorRT-LLM
   as of March 2026) compiles a JSON schema into an FSM so only schema-valid
   tokens are emitted. Reported effect: retry rates **5–15% → <1%** in production
   pipelines [secondary — letsdatascience, aipromptarchitect 2026]; small-model-
   specific reliability study at arXiv 2605.02363. Directly relevant to KG
   extraction (entities/relations must be schema-valid) and to any tool-calling
   worker.

6. **Semantic caching of results.** Cache worker outputs keyed by a semantic hash
   of the sub-task so repeated/near-repeated extractions or implementations skip
   the model entirely [secondary — multiple 2026 routing guides]. Buildable as a
   thin layer keyed on (spec-hash, file-hash); high value for graphify re-ingestion
   of unchanged inputs.

7. **KV-cache reuse (only if we self-host workers).** Serving-layer reuse of the
   attention KV cache across requests with a shared prefix; overlaps with prompt
   caching conceptually but lives in vLLM/SGLang. Skip unless local workers are
   self-served.

**Worth building into the orchestrator (in order):** prompt-cache-friendly stable
prefix → external ledger for compaction → structured-output constraints on
workers → RAG-over-graphify subgraph injection → semantic result cache. KV-cache
and speculative decoding are serving-layer, deferred until/unless we self-host.

---

## 4. Code-output QUALITY when a cheap model writes the code

The consistent 2026 finding: **the quality lift comes from the verification
loop, not from the model.** Evidence:

- **Iterative self-repair is universally effective.** "How Many Tries Does It
  Take?" (arXiv 2604.10508): with ≤5 attempts and error feedback, pass rates rise
  **+4.9 to +17.1 pts on HumanEval and +16.0 to +30.0 pts on MBPP**, across seven
  models / three families. Condition: the feedback must be real execution/error
  output, not self-reflection alone.
- **Compiler + static-analysis + test loops stack.** LLMLOOP (arXiv 2603.23613)
  runs five refinement loops (fix compile errors → fix static-analysis issues →
  fix failing generated tests → improve tests via mutation) and reports **pass@10
  90.24% vs 76.22% baseline**. Compiler-guided inference-time adaptation for a
  typed language: arXiv 2602.11481. "Is Three the Magic Number?" (arXiv
  2607.05197) studies repair-budget limits — diminishing returns set in, so cap
  the loop (≈3 iterations is a common sweet spot).
- **Best-of-N with a strong verifier** lifts a cheap generator when a reliable
  discriminator scores samples — this is Fable's optional `--best-of-n` and the
  RouteLLM "LLM-judge augmentation" result. Works only when the verifier is
  cheaper-than-generation and trustworthy (a compiler/test suite is the ideal
  verifier: free and objective).
- **Spec-conformance checks**: the strong model's spec doubles as the
  acceptance oracle (Fable's `Verification` field: "commands / checklist that
  prove it works — not `true`/`echo ok`").

**Takeaway for us:** a cheap worker's code becomes acceptable *when it must pass
an objective gate the strong model defined*. Our repo already has the perfect
gate — **`mise run lint` + `pytest` + `dotfiles-setup verify run`**. The
buildable pattern: cheap worker implements against a spec → runs the gate →
self-repairs on failure (cap ~3) → returns STATUS + evidence → strong model
accepts only on green. This is `verify-before-advancing.md` mechanized as an
orchestration loop, and TDD-first (`mattpocock-skills:tdd`) makes the gate exist
before the worker writes a line.

---

## 5. Trends, last ~1 month (2026-06 / 2026-07)

**Router/orchestration models became first-class products.**

- **Sakana AI Fugu / Fugu Ultra** (launched **2026-06-22**): an orchestration
  *model* — "a language model trained to call other LLMs in an agent pool,
  including instances of itself, recursively," exposed via one OpenAI-compatible
  API. It learns *when to delegate, how agents communicate, how to combine
  outputs*. Builds on two ICLR-2026 papers, **Trinity** (a lightweight evolved
  coordinator assigning Thinker/Worker/Verifier roles) and **the Conductor**.
  Primary: Sakana Fugu technical report, arXiv 2606.21228. Benchmark numbers are
  **inconsistent across write-ups** and should be treated cautiously: MarkTechPost
  [secondary] reports Fugu Ultra **73.7 on SWE-Bench Pro** vs "Claude Opus 69.2",
  while another [secondary — theplanettools] reports **Fable 5 at 86.0 vs Fugu
  Ultra 73.7** on the same bench. The *direction* (a learned orchestrator over a
  swappable pool is now a shipped category) is the load-bearing trend; the exact
  deltas are not settled — cross-check before quoting.
  → The meaningful signal for us: orchestration is being *productized as a model*,
  which validates building the routing logic as a first-class, measurable layer
  rather than ad-hoc prompt glue.

- **Multi-model routing is now claimed production infra** with **40–85% cost
  cuts** while "holding quality within 2–3 points of frontier baselines"
  [secondary — mindstudio, velsof, scalacode 2026; the 40–85% band traces back to
  RouteLLM's conditioned numbers, so treat as order-of-magnitude, not a promise].
  Cascade chains, ensemble+judge merging, and "optimize-for-cost/latency/quality"
  per-route policies are the recurring buildable primitives.

- **`fable-orchestrator` itself** (our anchor repo) is part of this wave — a
  Claude-Code-plugin instance of strong-plans/cheap-executes, actively updated
  (v1.2.2, 2026-07-19), i.e. this pattern is being battle-tested *in the exact
  harness we use*.

- **Local-model-as-worker / edge specialists** [secondary — agentcommunity.org
  2026-07-13 newsletter, treat as informal]: claims of tiny tool-calling
  specialists (a "Needle" 26M-param model at ~1,200 tok/s on a Pi) and very-long-
  context workers. Provenance is a newsletter; the *specific model names are not
  independently verified here* and some read as illustrative — do not cite as
  fact. The verifiable local-stack reality: Ollama v0.21.x (~June 2026) with MLX
  on Apple Silicon, plus vLLM/SGLang/llama.cpp, is the practical worker substrate
  [secondary — multiple local-LLM roundups].

- **Anthropic cost levers shipped/hardened**: automatic prompt caching and
  server-side context compaction (beta `compact-2026-01-12`) are the platform's
  answer to long-agent cost; Agent SDK exposes per-model cost tracking. These are
  the native features our orchestrator should lean on rather than reinvent
  (aligns with `use-tool-builtins.md`).

**Net trend:** the field converged this quarter on "frontier model orchestrates,
cheap/local models execute, a learned or rules-based router decides, and an
objective gate verifies" — precisely the fable-orchestrator shape, now with a
productized model (Fugu) proving the category.

---

## Synthesized recommendation

**Goal:** autonomous agents doing (i) graphify ingestion and (ii) ticket
implementation *cheaply*, with Claude/Fable 5 as the smart layer.

**Architecture — adopt the fable-orchestrator shape, mapped onto our existing
gates:**

1. **Strong model = architect only.** Fable 5 owns decomposition, five-part
   specs, routing, and accept/reject. Enforce a **no-product-write deny-hook** on
   the architect (we already run a PreToolUse guard — `hook_guard.py`; add an
   architect-role rule). Prose is not enough; a hook is (`mise-tasks-only.md`
   precedent, and Fable's own combat lesson).

2. **Cheap/local models = workers, addressed by a five-part spec** (Objective+MODE
   · Files · Interfaces · Constraints · Verification). Workers share zero
   architect context; they return **only compressed structured reports** (STATUS
   + CHANGES + evidence paths). Start with an existing cheap cloud tier (Haiku /
   a Grok/Sonnet lane); add local (Ollama/vLLM) workers behind the same spec+report
   interface once the contract is stable.

3. **Route with a simple cascade first, learn later.** Rules-based routing (easy
   → cheap, hard/ambiguous → strong, escalate on gate-failure) captures most of
   the 40–85% savings with days of work; a learned router (à la Fugu/Trinity) is
   a later optimization, not a v1 need.

4. **Quality gate = our real checks, mechanized as a self-repair loop.** Every
   ticket worker must pass `mise run lint` + `pytest` + `dotfiles-setup verify
   run`, self-repairing on failure (cap ~3 iterations — arXiv 2607.05197), and
   may only report `STATUS: pass` on green. TDD-first so the gate exists before
   the worker writes code. This is where cheap-model code quality is actually
   made acceptable (§4 evidence), and it is `verify-before-advancing.md` turned
   into an orchestration primitive.

5. **For graphify ingestion: map-reduce + structured-output workers + RAG over
   the graph itself.** Chunk inputs → parallel cheap workers extract
   entities/relations under a **constrained JSON schema** (retries 5–15% → <1%) →
   strong model reduces/dedupes into the graph. Then close the loop: the graph
   becomes the **retrieval index** that injects the relevant subgraph into ticket
   workers instead of raw files — the highest-leverage reuse of our graphify
   investment.

**Buildable techniques to prioritize (in order):**

1. Deny-hook enforcing the architect no-touch list (cheapest, biggest safety win).
2. Five-part spec contract + three fixed report shapes as the only cross-model
   interface (the core context saver).
3. Machine completion contract: `STATUS:` + wall/stall watchdog +
   incomplete-stamp launcher — steal `run-grok-headless.sh` almost verbatim so
   autonomy can neither hang nor fake success.
4. External ledger for state across compaction (STATUS + evidence paths only).
5. Prompt-cache-friendly stable prefix (system+doctrine+schema first, volatile
   last) — free ~10× read savings on the stable portion.
6. Constrained/structured output on all extraction + tool-calling workers.
7. Self-repair-against-our-gate loop for ticket workers (capped ~3).
8. RAG-over-graphify subgraph injection.
9. Selective best-of-N only for *hard* implement tasks, logged in a
   `metrics.jsonl`-style one-line-per-run ledger.

**Defer:** speculative decoding and KV-cache reuse (serving-layer; only if we
self-host workers); a learned router model (v2). **Lean on native, don't
rebuild:** Anthropic prompt caching, server-side compaction, and Agent-SDK cost
tracking (`use-tool-builtins.md`).

**Caveats carried forward:** the "40–85%" and Fugu SWE-Bench numbers are
condition-bound and inconsistent across secondary write-ups — use them as
direction, not targets, and re-measure on our own workloads
(`probes-need-a-control-arm.md`). The single most important design choice is #4:
without an objective gate, cheap-model code quality does not hold.

---

## GitHub repos touched

- [BuildContext/fable-orchestrator](https://github.com/BuildContext/fable-orchestrator) — primary anchor; read README, orchestration SKILL, both agent defs, `run-grok-headless.sh`, hooks for the strong-plans/cheap-executes model, token optimizations, completion contract, and hard-gate hooks.
- [DannyMac180/fable-advisor](https://github.com/DannyMac180/fable-advisor) — the upstream "architect pattern" essay that fable-orchestrator forks (referenced via README lineage; not deep-read).
- [lm-sys/RouteLLM](https://github.com/lm-sys/RouteLLM) — canonical open router; cost/quality-threshold benchmark numbers cited via LMSYS write-ups (repo referenced, numbers from paper/secondary blogs).
- [microsoft/graphrag](https://github.com/microsoft/graphrag) — map-reduce KG-extraction + community-summary pipeline referenced for graphify ingestion pattern (via arXiv 2404.16130; repo not deep-read).
- [SakanaAI](https://github.com/SakanaAI) — Fugu / Trinity / Conductor learned-orchestration line referenced via the arXiv 2606.21228 tech report and secondary coverage (org referenced; no Fugu repo deep-read).
- [dottxt-ai/outlines](https://github.com/dottxt-ai/outlines) and [mlc-ai/xgrammar](https://github.com/mlc-ai/xgrammar) — constrained/grammar decoding backends cited for structured-output retry reduction (referenced, not deep-read).
- [ollama/ollama](https://github.com/ollama/ollama) — local-worker substrate (Apple-Silicon MLX) referenced as the practical local-model runtime (referenced, not deep-read).
