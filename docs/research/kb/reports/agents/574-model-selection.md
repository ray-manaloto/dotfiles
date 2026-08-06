# Research — choosing the right Claude model per DAG stage (#574)

**Status:** COMPLETE
**Agent:** model-selection researcher (named agent, spawned by team-lead)
**Date:** 2026-08-06

**Sources** (all fetched 2026-08-06):

| # | Source | Date on page | Role |
|---|---|---|---|
| S1 | <https://claude.com/blog/claude-models-explained-choosing-the-best-model-for-your-use-case> | **July 24, 2026** | **PRIMARY (assigned)** |
| S2 | `https://platform.claude.com/docs/en/about-claude/models/overview.md` | undated | Prices, context windows, positioning |
| S3 | `https://platform.claude.com/docs/en/build-with-claude/effort.md` | undated | Effort levels + per-model guidance |
| S4 | `https://platform.claude.com/docs/en/api/rate-limits.md` | undated | **Settled the Fable supply question** |
| S5 | <https://claude.com/blog/claude-model-and-effort-level-in-claude-code> | **July 7, 2026** | Linked from S1; Claude Code routing |
| S6 | <https://claude.com/blog/the-advisor-strategy> | **April 9, 2026** | Linked from S1; advisor numbers |
| S7 | Local skill `claude-api` (bundled 2.1.223) | model table cached **2026-06-24** | Cross-check |

Nothing here is stale: the newest source is 13 days old, the oldest (S6, advisor) is 4 months and is superseded on its headline numbers by S1 — see §5 disagreement D4.

⚠️ **Fetch caveat, stated once and applying to every blog quote below.** WebFetch refused a verbatim full-page reproduction of S1 (copyright guard), so blog quotes are short extracts returned by targeted question-answering, i.e. the fetcher's transcription rather than my own read of raw HTML. The `platform.claude.com` `.md` sources (S2/S3/S4) came back as full document text and are quoted directly.

> ## ⚠️ CORRECTION — read this before anything else
>
> **An earlier draft of this report (written after S1+S2 only) stated that the maintainer's "Fable is supply-limited" premise was NOT supported by the docs.** That was wrong. S4 (`api/rate-limits.md`) confirms it quantitatively: **Fable 5 carries 2.5×–4× lower token throughput than every other current model at every usage tier.** The premise is correct and the ruling that follows from it is well-founded. Details in §2. I am flagging this rather than silently fixing it because the wrong version existed on disk for part of this run and the correction changes a decision input.

---

## 1. Per-model positioning — verbatim

S1 frames these as model **classes**, not individual models:

| Class | Verbatim (S1) |
|---|---|
| **Haiku** | "Haiku is our lowest cost and fastest model class." |
| **Sonnet** | "Sonnet is our versatile model class for everyday tasks." |
| **Opus** | "Opus is our powerful model class for reasoning-intensive enterprise tasks." |
| **Mythos** | "Mythos is Anthropic's most capable model class, with frontier capabilities across domains." |

⚠️ S1's top class is named **Mythos**, not Fable — see disagreement D1 in §5.

Per-model descriptions from S2's comparison table:

| Model | Description (S2, verbatim) |
|---|---|
| Claude Fable 5 | "Next-generation intelligence for long-running agents" |
| Claude Opus 5 | "For complex agentic coding and enterprise work" |
| Claude Sonnet 5 | "The best combination of speed and intelligence" |
| Claude Haiku 4.5 | "The fastest model with near-frontier intelligence" |

S2 § *Choosing a model*, verbatim: *"If you're unsure which model to use, start with **Claude Opus 5** for complex agentic coding and enterprise work. For workloads that need the highest available capability, use Claude Fable 5."*

S5 § model recommendations gives the cleanest task-shaped rule anywhere in the corpus:

> "Pick a smaller model when the work is routine. For example, edits you can describe precisely, mechanical changes, or questions about code that's already in context."

> "Pick a larger model when the problem is genuinely hard. For example, problems like subtle bugs, unfamiliar domains, or architecture decisions."

And on Fable, verbatim (S5): *"On long, multi-step work it pulls furthest ahead. In our testing, it finished jobs Opus and Sonnet can't reach at any effort level."*

⚠️ That last sentence is a **capability claim, not a cost claim** — "can't reach at any effort level" means there exists work no amount of Opus effort completes. It is the strongest argument in the corpus for keeping a Fable escape hatch, and it cuts against a blanket "Fable is only for planning."

## 2. Price / limits table

### Price (S2, cross-checked against S7 — exact agreement on every figure)

| Model | Input $/MTok | Output $/MTok | Context | Max output | Latency (S2's word) |
|---|---|---|---|---|---|
| Claude Fable 5 | **$10** | **$50** | 1M | 128k | "Slower" |
| Claude Opus 5 | **$5** | **$25** | 1M | 128k | "Moderate" |
| Claude Sonnet 5 | **$3** | **$15** (intro **$2 / $10** to 2026-08-31) | 1M | 128k | "Fast" |
| Claude Haiku 4.5 | **$1** | **$5** | **200k** | 64k | "Fastest" |

Clean 10 / 5 / 3 / 1 input ladder. Fable is **2× Opus** on both directions.

### Rate limits (S4) — this is the finding that settles the Fable question

Per-model, per-tier. **Fable is the only model that is throttled below the others, and it is throttled at every tier:**

| Tier | Metric | Fable 5 | Opus 5 | Sonnet 5 | Haiku 4.5 | Fable as % of the rest |
|---|---|---|---|---|---|---|
| Start | RPM | 1,000 | 1,000 | 1,000 | 1,000 | 100% |
| Start | **ITPM** | **500,000** | 2,000,000 | 2,000,000 | 2,000,000 | **25%** |
| Start | **OTPM** | **100,000** | 400,000 | 400,000 | 400,000 | **25%** |
| Build | RPM | 2,000 | 5,000 | 5,000 | 5,000 | 40% |
| Build | **ITPM** | **1,500,000** | 5,000,000 | 5,000,000 | 5,000,000 | **30%** |
| Build | **OTPM** | **300,000** | 1,000,000 | 1,000,000 | 1,000,000 | **30%** |
| Scale | RPM | 4,000 | 10,000 | 10,000 | 10,000 | 40% |
| Scale | **ITPM** | **4,000,000** | 10,000,000 | 10,000,000 | 10,000,000 | **40%** |
| Scale | **OTPM** | **800,000** | 2,000,000 | 2,000,000 | 2,000,000 | **40%** |

**The maintainer's ruling is correct on both stated grounds.** Fable is 2× the price *and* runs at 25–40% of the throughput of every other model. Reserving it for planning/advising is not a budget compromise — it is the only way to use it without the DAG stalling on 429s.

**Three more S4 facts that matter architecturally:**

1. **Opus 5, Sonnet 5 and Haiku 4.5 have *identical* limits at every tier.** So among the three models the maintainer sanctioned, **model choice costs nothing in quota** — only in dollars. There is no throughput argument for Haiku over Opus.
2. Verbatim (S4): *"Rate limits are applied separately for each model; therefore you can use different models up to their respective limits simultaneously."* A DAG that runs research on Sonnet and review on Opus has **strictly more aggregate throughput** than one running both on the same model. Heterogeneous stage models are a throughput win, independent of quality.
3. Verbatim (S4): *"`cache_read_input_tokens` … ✗ **Do NOT count toward ITPM** for most models"* (Haiku 3.5 is the only exception, and it's retired). A research node that re-reads a cached corpus is nearly free against quota. **Caching is a throughput multiplier, not just a cost one** — S4's worked example: a 2M ITPM limit at 80% cache hit rate processes 10M input tokens/min.

Also from S7 (local skill): **Fable 5 requires 30-day data retention** — ZDR orgs get a 400 on every request — and **Fable thinking cannot be disabled** (400 on `{"type":"disabled"}`), so there is no cheap Fable call.

## 3. Effort levels

S3 is the authority. Five levels, `output_config: {effort: ...}`, GA, no beta header. Verbatim level table (S3):

| Level | S3's "Typical use case" |
|---|---|
| `max` | "Tasks requiring the deepest possible reasoning and most thorough analysis" |
| `xhigh` | "Long-running agentic and coding tasks (over 30 minutes) with token budgets in the millions" |
| `high` | "Complex reasoning, difficult coding problems, agentic tasks" |
| `medium` | "Agentic tasks that require a balance of speed, cost, and performance" |
| `low` | "Simpler tasks that need the best speed and lowest costs, **such as subagents**" |

⚠️ **`low` names subagents explicitly.** Every DAG node here *is* a subagent-shaped background session, so this row is directly on point — and it argues the opposite of "give every node high effort".

**Two S3 statements that land squarely on the `research` stage** (from the Opus 4.7 guidance table, and repeated in § *When to adjust*):

> `xhigh`: "The recommended starting point for coding and agentic work, and for **exploratory tasks such as repeated tool calling, detailed web search, and knowledge-base search**."

> "Use **xhigh effort** for advanced coding and complex agentic work requiring extended exploration, such as repeated tool calling and detailed search."

"Knowledge-base search" and "detailed web search" is the research stage's literal job description.

**Per-model defaults and starting points (S3):**

- Default is `high` on every supported model; *"Setting `effort` to `"high"` produces exactly the same behavior as omitting the `effort` parameter entirely."*
- **Opus 5:** *"Start with `high`, the default … and use `low` and `medium` liberally as your primary control for token cost and response time wherever your evals show quality holds. If you carried effort settings over from an earlier model, run a fresh effort sweep."*
- **Sonnet 5:** `high` default; `xhigh` "for the hardest coding and agentic tasks"; `medium` "Comparable to Claude Sonnet 4.6 at high effort"; `low` "For high-volume or latency-sensitive workloads."
- **Fable 5:** *"Effort is the primary control for trading off intelligence, latency, and cost on Claude Fable 5. Start with `high` … Lower effort settings on Claude Fable 5 still perform well and often exceed `xhigh` performance on prior models."*

**Haiku 4.5 does not support effort at all.** S3's supported-model list is `claude-fable-5`, `claude-mythos-5`, `claude-mythos-preview`, `claude-opus-5`, `claude-opus-4-8/4-7/4-6`, `claude-sonnet-5`, `claude-sonnet-4-6`, `claude-opus-4-5-20251101`. **Haiku 4.5 is absent.** A Haiku node has no effort dial — see control arm C3.

**Two operational constraints on effort (S3):**

- Effort affects *all* tokens including tool calls: *"lower effort would mean Claude makes fewer tool calls."* For a research node, low effort literally means less searching.
- Effort is request-level and **cache-hostile**: *"changing it between requests does not preserve cached prefixes … pick an effort level at the start and keep it constant."* Per-node effort is fine; per-turn effort within a node is not.

**Tempering note from S5** (Claude Code, July 7): *"For most tasks you should use the model's default effort level"*, and raise it *"if Claude got it wrong by skipping a file, not running the tests, or not double-checking its work."* So: default `high`, and treat a raise as a response to observed failure rather than a guess.

## 4. Cheap-for-breadth / expensive-for-judgment — endorsed, but not in the assumed form

**The vendor's endorsed pattern is the ADVISOR STRATEGY** — a cheap **executor** runs the turn while an expensive **advisor** model is consulted server-side. S6's defining line: *"Pair Opus as an advisor with Sonnet or Haiku as an executor."*

Published numbers, all verbatim:

| Pairing | Benchmark | Result | Cost |
|---|---|---|---|
| Sonnet + Opus advisor (S6) | SWE-bench | "2.7 percentage point increase" | "reducing cost per agentic task by 11.9%" |
| **Haiku + Opus advisor (S6)** | **BrowseComp** | "scored 41.2%, more than double its solo score of 19.7%" | "costs 85% less per task" than Sonnet solo |
| Sonnet 5 + Fable 5 advisor (S1) | not named | "within 10% of Fable 5's score" | "at 63% of the price of using Fable 5 for the whole task" |

⚠️ **The BrowseComp row is the research stage's benchmark shape** — browse/search/retrieve. Haiku-with-an-Opus-advisor **more than doubles** solo Haiku there. That is the strongest evidence in the corpus that a cheap executor + expensive advisor beats either model alone on breadth work. It is also the single result most likely to change this design.

**But S1 explicitly warns against the naive "just use a smaller model" version:**

> "Higher-class models at higher efforts offer the best possible performance, and higher-class models at lower efforts can sometimes be more efficient than smaller models."

i.e. **Opus at `low` may beat Haiku at its ceiling on both quality and total cost**, because a weaker model takes more turns. S1's stated framework is:

> "start with the most intelligent generally available model and use effort level to dial in performance and cost."

**The vendor's primary cost lever is EFFORT, not model class.** A design that routes by class and pins effort has picked the secondary lever and discarded the primary one.

**Advisor constraints (S7 + S6):**

- The advisor model must be **at least as capable as the executor**; invalid pairs return 400. Valid here: executor Haiku 4.5 / Sonnet 5 → advisor Opus 5 / Fable 5; executor Opus 5 → advisor Opus 5 / Fable 5.
- Availability (S6, verbatim): *"Available now in beta natively on the Claude Platform"* via the Messages API, requiring a beta header and the advisor tool in the request — **"no mention of Claude Code, CLI, or subagents."**
- `platform-availability.md` (S7) marks the advisor tool **β, first-party Claude API only** (❌ Bedrock / Vertex / Foundry).

⚠️ **UNVERIFIED and load-bearing:** whether the advisor tool is reachable from a `claude --bg --agent` CLI session. Both sources describe a Messages API request parameter. **Do not design the DAG around advisor pairing until this is probed.** See §7.

## 5. Disagreements found

| # | Disagreement | Detail | Resolution |
|---|---|---|---|
| **D1** | **S1 calls the top class "Mythos"; S2/S7 call the GA model "Fable 5"** | S1: "Mythos is Anthropic's most capable model class." S2: Fable 5 "is Anthropic's most capable **widely released** model"; Mythos 5 "shares Claude Fable 5's specs and pricing", is Project Glasswing, **"invitation-only and there is no self-serve sign-up"**, and is "offered separately for **defensive cybersecurity workflows**". | **Trust S2.** S1 writes at class level and named the frontier-class flagship. For a system that must run today, **Fable is the accessible member of that class**; Mythos is unreachable without a Glasswing invitation and is scoped to a different domain anyway. |
| **D2** | **My own earlier finding vs S4** | The draft written from S1+S2 alone concluded "Fable is supply-limited" was unsupported, because neither page mentions Fable rate limits. S4 shows Fable at **25–40% of every other model's ITPM/OTPM at every tier**. | **S4 wins; my earlier finding was wrong.** The cause was a bounded search — I searched the two pages I had, not the page that owns the fact. Corrected at the top of this report. |
| **D3** | **S1 vs S5 on how much to touch effort** | S1: "use effort level to dial in performance and cost" (effort as the primary lever). S5: "For most tasks you should use the model's default effort level." | **Not a contradiction — different audiences.** S1 is API/platform guidance, S5 is Claude Code end-user guidance. For a programmatic DAG, S1's framing applies; S5's "don't fiddle" advice is for humans at a terminal. Net: expose effort in config, default it to `high`, change it on evidence. |
| **D4** | **S6 (April) vs S1 (July) on advisor pairings** | S6: "Pair **Opus** as an advisor with Sonnet or Haiku." S1: "**Sonnet 5 with a Fable 5 advisor**." | **Both true, S1 is current.** The strategy generalised upward as Fable shipped. S6's Haiku+Opus BrowseComp number is still the most relevant one here because it is the only *browse-shaped* measurement published. |
| **D5** | **S7 (skill, cached 2026-06-24) vs S2 (live)** | Every price and context figure agrees exactly. S2 additionally carries a Fable GA date (2026-06-09) and a 300k batch-output beta that S7's model table omits. | **Agreement on the load-bearing numbers**; S2 is authoritative and slightly fresher. No correction needed. |
| **D6** | Sonnet 5 introductory pricing end date | S2 and S7 both say **2026-08-31**. | Agreement. ⚠️ **That is 25 days away.** Sonnet 5 rises from $2/$10 to $3/$15 on 2026-09-01 — a **50% increase** on whichever node runs Sonnet. Any cost model written this week silently breaks in September. |

## 6. Stage → model recommendation

Constraints honoured: stage models drawn from haiku / sonnet / opus; Fable reserved for planning/advising/very-complex; mapping configurable.

### `research` — breadth, 6,446-file corpus + web → **Sonnet 5 @ `high`**

**Not Haiku.** Two independent blockers, either one sufficient:

1. **Context.** Haiku 4.5 is **200k** (S2); Sonnet 5 and Opus 5 are **1M**. The stage sweeps a 6,446-file corpus. 200k is ~150k words — S2's own tooltip. This is a wall, not a preference.
2. **No effort dial.** Haiku 4.5 is absent from S3's supported-model list. The stage cannot be tuned, and per S3 effort is what governs *how many tool calls* a node makes — precisely the knob a search-heavy node needs.

**Justifying sentence:** S1's *"Sonnet is our versatile model class for everyday tasks"* plus S2's *"The best combination of speed and intelligence."* Breadth with modest judgment is the everyday-task shape, and S5's *"Pick a smaller model when the work is routine"* points the same way — research here is high-volume and well-specified, not hard.

**Effort: start `high` (the default), and treat `xhigh` as the tested alternative, not the default.** S3 says `xhigh` is the starting point for *"exploratory tasks such as repeated tool calling, detailed web search, and knowledge-base search"* — a direct hit on this stage. But that sentence sits in the **Opus 4.7** guidance block; the **Sonnet 5** block scopes `xhigh` to *"the hardest coding and agentic tasks."* So the evidence for `xhigh` here is real but is about a different model. **Run both and measure**; do not ship `xhigh` on the strength of a sentence written for another model. `medium` is the cost step-down (S3: "Comparable to Claude Sonnet 4.6 at high effort").

### `implement` — fixed to Codex. Nothing in these sources argues to move it, but two things belong in front of the maintainer

- **The vendor's default for this exact shape is Opus 5**: S2 says *"start with Claude Opus 5 for complex agentic coding"*, and Opus 5's one-liner is literally *"For complex agentic coding and enterprise work."* If the Codex lane ever needs a fallback, Opus 5 at `xhigh` is the documented setting.
- **The cross-family review requirement makes the Codex choice load-bearing.** Review must come from a different family than the implementer. Keeping implement on Codex is *what makes* an Opus reviewer cold. Moving implement to a Claude model would force review onto a non-Claude model and invert the whole arrangement. **Don't reverse this casually.**
- ⚠️ One genuine capability caveat (S5): Fable *"finished jobs Opus and Sonnet can't reach at any effort level"* on long multi-step work. That claim is about Claude models and says nothing about Codex — but it means "very complex implementation" is a real category, and the maintainer's carve-out for Fable on very complex tasks is well-founded rather than decorative.

### `review` — highest judgment density, smallest input → **Opus 5 @ `high`**

**Justifying sentence:** S1's *"Opus is our powerful model class for reasoning-intensive enterprise tasks"*, reinforced by S5's *"Pick a larger model when the problem is genuinely hard. For example, problems like subtle bugs …"* — subtle-bug-finding is adversarial diff review's entire job.

The economics are favourable in a way worth stating: review has the **smallest input** of the three stages, so the most expensive sanctioned per-token model costs the least in absolute dollars here. Paying Opus rates on a diff is cheap; paying them on a 6,446-file sweep would not be.

**Effort `high` (default), raising to `xhigh` only on observed misses** — per S5's rule: raise *"if Claude got it wrong by skipping a file, not running the tests, or not double-checking its work."*

**Two prompt requirements for this node, both from S7 and both non-optional:**

1. **Coverage-first, no conservatism filter.** S7 records a measured trap on Opus 4.7/4.8/5 and Sonnet 5: *"if a review harness says 'only report high-severity issues' or 'be conservative', [the model] follows it literally and measured recall can drop even though underlying bug-finding improved."* The prescribed fix is to ask for every finding with confidence + severity and filter in a **separate downstream pass**. The failure is silent — the node looks like it is working while recall falls.
2. **Delete verification scaffolding.** S7 on Opus 5: instructions telling it to verify now cause over-verification, and *"Removing them reduces over-verification with no capability regression."* This inverts the usual "ask the model to self-check" best practice, specifically on this model.

### Where Fable fits — the maintainer's ruling, restated with its evidence

Fable for **planning / advising / very complex only** is exactly what the corpus supports, on three independent grounds:

- **Price** — 2× Opus (S2).
- **Throughput** — 25–40% of Opus/Sonnet/Haiku ITPM and OTPM at every tier (S4). This is the decisive one for a DAG that runs many nodes.
- **Vendor-endorsed use** — S1: *"Sonnet 5 with a Fable 5 advisor is within 10% of Fable 5's score at 63% of the price."* Fable-as-advisor is a published Anthropic pattern, not a workaround.

## 7. Control arms run

Every negative below has an armed probe. Control terms invented fresh for this run.

| # | Claim | Probe | Control arm | Verdict |
|---|---|---|---|---|
| **C1** | S1 quotes no per-token prices | Asked the fetcher for prices/context/limits, "quote exactly what numbers appear" | **The same fetch returned other numbers from the same page** — "63%", "10%", and the date "July 24, 2026". The extractor demonstrably reads numbers off this page. | **ARMED.** The absence of $/MTok in S1 is real, not a blind probe. |
| **C2** | *(superseded — this is the one that failed)* "Neither source states a Fable supply limit" | Read S1+S2 for supply language | The probe *did* surface supply language when present — "invitation-only", "no self-serve sign-up", "limited availability to approved customers" — all attached to **Mythos**, plus a positive GA statement for Fable. So the probe discriminated correctly **on the pages it was pointed at**. | ⚠️ **ARMED BUT MIS-AIMED.** The probe could see; I aimed it at the wrong corpus. Rate limits live on `api/rate-limits.md`, which I had not fetched. **A control arm proves the probe can see — not that you pointed it at the right thing.** Fetching S4 reversed the finding. |
| **C3** | Haiku 4.5 cannot use `effort` | S3's supported-models list | The same list **positively includes** nine other model IDs including `claude-opus-4-5-20251101` — an older model — so it is not a "current models only" list that would omit Haiku incidentally. Haiku 4.5's absence is a real exclusion. Independently corroborated by S7's effort table ("errors on Sonnet 4.5 / Haiku 4.5") and by S2's table row "Adaptive thinking: No" for Haiku. **Three routes agree.** | **ARMED.** |
| **C4** | Skill/docs price agreement is a real match, not one source read twice | Compared two independently-fetched artifacts | The two **disagree elsewhere**: S2 carries a Fable GA date (2026-06-09) and a `output-300k-2026-03-24` batch beta that S7's model table lacks; S7 carries advisor pairing tables S2 lacks. | **ARMED.** The comparison discriminates; the price agreement is genuine. |
| **C5** | Fable's rate limits are genuinely lower, not a table-reading error | Read all three tier tabs in S4 | **Opus 5, Sonnet 5 and Haiku 4.5 are identical to each other** in all three tabs (1M/2M/400k → 5M/1M → 10M/2M). Fable is the *only* row that differs, and it differs in the same direction across all three tiers and all three metrics. A misread would not produce that consistency. | **ARMED.** |

**Explicitly unverified — do not build on these:**

- **Advisor-tool reachability from `claude --bg --agent`.** S6 and S7 both describe a Messages API request parameter + beta header. Neither mentions the CLI. This is the single highest-value open question for the design (see §4).
- **Claude Code subscription weekly windows vs Fable.** Out of scope for these API sources. The repo's own memory index (`project_session_2026-08-04c`) records "Claude's weekly window is SHARED across models" — but that is an **inherited, unverified note**, not a measurement I made, and per this repo's rules I am labelling it rather than repeating it as fact.
- **Whether `claude --bg` exposes `effort` at all.** Every effort recommendation in §6 assumes the CLI surfaces `output_config.effort`. S3 documents the API parameter and shows an `ant` CLI form (`--output-config '{effort: medium}'`), but `ant` is not `claude`. **If the DAG's CLI cannot set effort, half of §6 is unactionable** — probe this before the model mapping.

## Suggestions — what I would change in the design

1. **Don't put Haiku on `research`.** 200k context against a 6,446-file corpus, plus no effort dial. If cost is the driver, the vendor's answer is **Sonnet 5 at lower effort**, not a smaller class — S1: *"higher-class models at lower efforts can sometimes be more efficient than smaller models."*

2. **Make `effort` a first-class per-node config field alongside `model`** — but **probe CLI support first** (§7). S1's entire framework is *"start with the most intelligent … model and use effort level to dial in performance and cost."* A config that exposes model but not effort has shipped the secondary lever and dropped the primary one. Defaults: research `high`, review `high`. Hold it constant within a node (S3: changing effort invalidates the prompt cache).

3. **Add the coverage-first instruction to the `review` brief, and remove any conservatism/severity filter and any self-verification instruction.** Both are measured vendor guidance with silent failure modes (§6).

4. **Probe advisor-tool reachability from the CLI, then decide.** If it works, `Sonnet 5 executor + Fable 5 advisor` is the vendor's own published trade (within 10% of Fable quality at 63% of Fable price) and fits the maintainer's "Fable for advising" ruling exactly. **The BrowseComp result — Haiku + Opus advisor scoring 41.2% vs 19.7% solo, at 85% less than Sonnet solo — is browse-shaped and therefore the closest published analogue to the research stage.** If advisor works in the CLI, it may beat the whole per-stage-model approach for research.

5. **Correction for the maintainer's premise, in their favour:** "Fable is expensive and supply-limited" is **confirmed on both halves** — 2× price and 25–40% throughput at every tier. My earlier draft said the supply half was unsupported; that was wrong and is corrected in §2. Nothing about the ruling needs to change.

6. **Exploit the separate-pool fact.** S4: *"Rate limits are applied separately for each model."* Opus 5 / Sonnet 5 / Haiku 4.5 have **identical** limits, so a heterogeneous stage mapping gets strictly more aggregate throughput than a homogeneous one — a throughput argument for per-stage models that is independent of quality. And because `cache_read_input_tokens` don't count toward ITPM, **caching the offline corpus prefix raises the research node's effective throughput several-fold.**

7. **Date-stamp the cost model.** Sonnet 5 introductory pricing ends **2026-08-31** (25 days out); the research node's token cost rises 50% on 2026-09-01.

## GitHub repos touched

_None._ All sources were vendor documentation (`claude.com`, `platform.claude.com`) and a locally bundled Anthropic skill. No GitHub repository source, README, issue, discussion, or doc tree was consulted.
