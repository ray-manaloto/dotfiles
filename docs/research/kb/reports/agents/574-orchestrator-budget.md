# Research — orchestrator / advisor patterns and token budgets for Fable 5 (#574)

**Status:** COMPLETE
**Agent:** orchestrator-budget (named agent, branch `docs/574-node-granularity-grill`)
**Date of research:** 2026-08-06

**Sources:**

1. `https://www.mindstudio.ai/blog/claude-fable-5-orchestrator-token-budget-optimization`
   — THIRD-PARTY. Fetched 2026-08-06 via WebFetch. **Published 2026-07-09** (age ~28 days).
   Title: *"How to Use Claude Fable 5 as an Orchestrator Without Burning Your Token Budget"*.
   Author: "MindStudio Team". **Vendor content-marketing for MindStudio** (see bias note §1.0).
2. `https://explainx.ai/blog/fable-5-advisor-orchestrator-patterns-july-2026`
   — THIRD-PARTY. Fetched 2026-08-06 via WebFetch + Exa `web_fetch_exa` (raw markdown).
   **Published 2026-07-08** (age ~29 days) — page states `**Published:** 2026-07-08T00:00:00.000Z`,
   which **confirms the slug's "july-2026" claim against the page itself**, as instructed.
   Title: *"Fable 5 Advisor and Orchestrator Patterns: 92% Quality at 63% Cost (July 2026)"*.
   Author: **Yash Thakker**.

Neither URL 404'd. Both resolved to real, substantive articles at the assigned addresses; no
substitution was needed.

> **Grading key (as mandated):** `MEASURED` = author ran something and reports method + numbers.
> `REPORTED` = number with no method, or a number relayed from someone else's run.
> `ANECDOTE` = experience claim. `OPINION` = assertion.

---

## 1. mindstudio — the token-budget argument

### 1.0 Bias disclosure (material to how much weight this carries)

This is a **content-marketing post for the MindStudio product**, not a neutral write-up. It carries
a dedicated sales section headed **"Building This in MindStudio"**, verbatim:

> "MindStudio's visual no-code builder lets you set up orchestrator-worker workflows using 200+
> available AI models — including Claude Fable 5, Sonnet, and Haiku — without writing
> infrastructure code."

and closes that section with a CTA: *"You can try MindStudio free at mindstudio.ai."* The FAQ
contains a question — *"Can this pattern work without writing code?"* — whose answer is the
product. Treat every unattributed number here as marketing copy until independently sourced.

### 1.1 What it advocates (verbatim, § "Understanding the Orchestrator-Worker Pattern")

> "**Orchestrator:** Decides what needs to happen, in what order, and validates the result"
> "**Worker (sub-agent):** Executes a specific task based on clear instructions"

> "The orchestrator-worker pattern fixes this by treating the most capable model as a coordinator,
> not a workhorse. It sets the strategy, breaks down the job, routes tasks to the right sub-agents,
> and reviews the final output. The sub-agents do the heavy lifting."

Orchestrator is **in the loop per step**, not consulted once. Evidence — § "What Claude Fable 5 Is
Actually Good At" gives it four recurring jobs (decomposition, routing, output review, exception
handling), and § "How to Implement This in Practice" Step 5 wires a return path:

> "Build a pathway for sub-agents to flag uncertainty back to the orchestrator. A simple pattern:
> if the sub-agent's confidence in its output is below a threshold, it returns a structured
> exception object instead of an answer. The orchestrator then decides how to handle it."

### 1.2 Claims table

| Claim (verbatim or close) | Grade | Method stated? | My assessment |
|---|---|---|---|
| § intro: "this approach can cut token costs by **10x** without any meaningful drop in output quality" | **REPORTED** | **None.** No baseline, no workload, no measurement | The headline number and it is unsupported. No baseline named ⇒ per this repo's standard, not a saving. See 1.3 |
| § FAQ: "the token cost difference between Claude's frontier reasoning models and Sonnet … typically **an order of magnitude or more per token**" | **REPORTED** | List-price ratio, not a run | Plausible as *price* arithmetic. Note it is a **per-token rate ratio**, not a workload result |
| § FAQ: "In workflows where Sonnet can handle **80%** of the execution, overall token spend can drop by **10x** or more" | **OPINION** (arithmetic dressed as a result) | None | This is where the 10x comes from — it is *derived from the price ratio times an assumed 80% split*, not measured. The 80% is itself assumed |
| § Step 1: "This exercise alone usually reveals that **70–80%** of your steps are execution tasks" | **ANECDOTE** | "usually reveals" — no sample, no n | Unfalsifiable as written |
| § FAQ: "Does using cheaper sub-agents hurt output quality? **For well-defined tasks … no.**" | **OPINION** | None. No eval, no benchmark | Directly contradicted in *magnitude* by explainx's sourced figures, which show a real 4–8 point quality gap (§2). "No drop" is stronger than anyone's data |
| § "Control Extended Thinking Carefully": extended thinking "should not be on by default for every orchestrator call" | **OPINION** (sound) | None | Reasonable engineering advice; costless to adopt |
| § "Cache Shared Context": "Anthropic's prompt caching feature can significantly reduce costs on repeated context" | **REPORTED** | None (no figure at all) | True in direction; explainx gives the actual break-even (§2.2) |

### 1.3 Assessment of §1

**The mindstudio post contains zero measurements.** Its central "10x" is price-ratio arithmetic
over an assumed task split, presented in the introduction as an outcome ("can cut token costs by
10x"). It never names a workload, a baseline run, an eval, or a token count. Under the grading
scheme I was given, nothing on this page reaches `MEASURED`.

What it **is** good for: it is a clean, correctly-reasoned *taxonomy* of the pattern, and its
§ "Common Mistakes That Inflate Token Costs" is the most useful part of the page — particularly:

> "**Passing full documents to the orchestrator.** The orchestrator should receive summaries or
> metadata, not raw content."

That is a real design constraint and it bears directly on our design (§4).

---

## 2. explainx — advisor vs orchestrator patterns

Substantially the stronger source. It is a **secondary report of Anthropic's own claims**, and —
to its credit — **it says so itself**, unprompted, in a section headed "Honest limits":

> "1. **Benchmarks are Anthropic-reported** — SWE-bench Pro and BrowseComp numbers come from
> @ClaudeDevs tweets, not third-party replication on explainx.ai."

The provenance chain is therefore: **Anthropic internal eval → a @ClaudeDevs tweet thread
(July 8, 2026) → this blog post → me.** Nobody in that chain published a method.

### 2.1 The two patterns, verbatim

**Advisor** (§ "Pattern 1 — Fable 5 as advisor, Sonnet 5 as executor"), quoting the tweet:

> "Use Fable 5 as an 'advisor.' An executor (Sonnet 5) calls Fable 5 for guidance. Most tokens are
> billed at the lower executor rate."

**Orchestrator** (§ "Pattern 2 — Fable 5 as orchestrator, Sonnet 5 as workers"), quoting the tweet:

> "Use Fable 5 as an orchestrator. Fable 5 plans and delegates to workers (Sonnet 5). Most tokens
> are billed at the lower worker rate."

The article's own architectural contrast table (§ "Advisor vs orchestrator — architectural
difference") answers the brief's question 3 directly:

| Dimension | Advisor pattern | Orchestrator pattern |
|---|---|---|
| **Fable's job** | "Mid-task course correction inside one agent loop" | "Task decomposition + sub-agent dispatch" |
| **Sonnet's job** | "Primary tool loop + code generation" | "Parallel workers on scoped subtasks" |
| **Call frequency** | "~1 advisor call per task (Anthropic tweet)" | "Fable plans once; many Sonnet worker turns" |

and its plain-English gloss, verbatim:

> "Think of **advisor** as *'ask the principal engineer before you commit to the approach'* inside a
> single Claude Code session. Think of **orchestrator** as *'principal writes the work breakdown;
> juniors run the searches'* across managed sub-agents."

### 2.2 Claims table

| Claim (verbatim) | Grade | Method stated? | My assessment |
|---|---|---|---|
| "Sonnet 5 + Fable 5 advisor tool reaches **~92%** of Fable 5's score at **~63%** of the price" on **SWE-bench Pro** | **REPORTED** | Benchmark **named**; run by Anthropic; no config, no n, no variance, no error bars | Best-sourced number in either post. Still second-hand from a tweet. Benchmark named ⇒ better than anything in §1 |
| "**~96%** of Fable 5 solo performance / **~46%** of the price" on **BrowseComp** with CMA | **REPORTED** | Benchmark named; Anthropic-run; no method published | Same standing. Note **both** figures are *price*-denominated (§4) |
| Advisor output "**400–700 text tokens** (or **1,400–1,800** including thinking on harder tasks)" | **REPORTED** | From vendor docs; no method | Useful magnitude. Implies the advisor's *output* is trivially small — the pattern's saving is not in the advice, it is in **who writes the patch** |
| `max_tokens` cap table: unset → "~4,200–5,900"; **2048** → "~630–840", truncation "~0%"; 1024 → "~370–480", truncation "~10%" | **REPORTED** (relayed measurement) | "Anthropic's internal table on **a hard reasoning benchmark**" — benchmark **not named** | Shaped like a real measurement (three arms, a truncation rate) but the workload is anonymous, so unreproducible |
| "**~7 percentage point** pass-rate lift on Haiku" from a turn-2 nudge; "**Do not** nudge Opus executors (slightly lowered pass rates)"; "Sonnet showed no measurable nudge effect" | **REPORTED** | "in behavioral eval" — Anthropic's; not described | Notable for reporting a **null** (Sonnet) and a **negative** (Opus) — a marketing post rarely does. Raises my confidence this relays a real internal eval |
| Advisor prompt caching: "Break-even at roughly **three calls**" | **REPORTED** | None | Actionable threshold; direction is trivially right |
| "**Sonnet executor at medium effort + Fable advisor** ≈ Sonnet at default effort intelligence at lower cost per docs" | **REPORTED** | "per docs" | Relevant to our fixed-effort implement stage (§4) |
| API surface: tool `advisor_20260301`, beta header `advisor-tool-2026-03-01`, result `advisor_redacted_result` with `encrypted_content` "round-trip verbatim" | **REPORTED** (vendor-doc relay) | Cites `platform.claude.com` advisor-tool docs + a code sample | **Verified independently — see §5 control arms.** Highly checkable, which is why I checked it |
| "The advisor must be **at least as capable** as the executor"; invalid pairs "return **400 `invalid_request_error`**" | **REPORTED** | Cites a compatibility table | Constrains any advisor design: **you cannot advise Fable with Sonnet.** Advice only flows down-tier |
| "Anthropic runs a **separate inference** on Fable with the **full transcript**" — all "inside **one** `/v1/messages` request" | **REPORTED** (vendor-doc relay) | Cites docs; gives the 4-step sequence | **The single most consequential mechanical fact in either source for us** (§4) |

### 2.3 When NOT to use it — explainx answers this, mindstudio does not

Brief question 5. explainx § "When advisor is a strong fit" names the **weak** fits verbatim:

> "**Weaker fit:** single-turn Q&A, workloads where every turn genuinely needs frontier reasoning,
> or pass-through model pickers where users already chose their cost/quality tradeoff."

and its § "Decision matrix" contains two rows that are effectively "do not use this pattern":

> "**Simple Q&A, one-shot codegen** → Sonnet alone — advisor adds latency without payoff"
> "**Every turn needs frontier reasoning** → Fable solo — **patterns optimize cost, not max
> intelligence**"

That last clause is the honest framing of the whole thing and I would carry it into our design
verbatim. Plus, from § "Honest limits":

> "4. **Orchestrator adds orchestration complexity** — sub-agent failures, vault secrets, and CMA
> scheduling are operational overhead the advisor pattern avoids."
> "5. **Once-per-task is a target, not a guarantee** — without `max_uses` and system-prompt
> steering, executors may over- or under-call the advisor."

mindstudio's equivalent section (§ "Common Mistakes That Inflate Token Costs") lists mistakes
*within* the pattern; it never contemplates the pattern being the wrong choice. **Only explainx
answers "when not to".**

---

## 3. What the pattern actually is, stated in one paragraph

Both posts describe the same economic move under two different couplings. A high-capability model
is confined to the work whose *quality* determines the outcome — decomposing an ambiguous goal,
choosing a route, and judging the result — while the token-heavy mechanical work (writing the
patch, running the searches, reformatting the data) is executed by a cheaper model that receives
instructions precise enough that it does not need to improvise. The **orchestrator** coupling puts
the expensive model *above* the workers: it plans once, dispatches sub-agents, and reviews what
comes back (explainx: *"Fable plans once; many Sonnet worker turns"*). The **advisor** coupling
inverts the control flow: the *cheap* model drives the loop and *pulls* the expensive model in
roughly once per task for a course correction, mid-generation, without ever handing over control
(explainx: *"Mid-task course correction inside one agent loop"*). The handoff artifact differs
accordingly and this is the operative distinction for our design: an orchestrator hands **down** a
work breakdown — a plan/spec that becomes the sub-agent's prompt — whereas an advisor hands **back**
a critique or plan *into an already-running context*, as an opaque blob the executor consumes. On
the mindstudio account the orchestrator is in the loop **per step** (it also owns exception
handling and final review); on the explainx account the advisor is consulted **once per task**, and
the orchestrator plans **once** up front.

## 4. Does it survive our economics (78-85k fixed per agent, shared weekly window)?

**Partially, and the two headline numbers do not transfer at all.** Four findings, ordered by how
much they should change the design.

### 4.1 Every saving in both posts is denominated in PRICE. Our binding constraint is not price.

"~63% of the price", "~46% of the price", "cut token costs by 10x" — these are all **dollar
per-token-rate** ratios, computed against API list pricing. Our stated ground truth is that Claude's
five-hour and seven-day windows are **shared across all models**, so the constraint that actually
stops work here is a quota ceiling, not a bill.

Precisely: moving work from Fable to Sonnet **does** lower the burn rate against that window (per
the ground truth I was given), so the *direction* survives. What does **not** survive is the
*magnitude*: 63% and 46% are ratios of dollar prices, and the window's internal weighting between
models is not the dollar-price ratio — it is not something either post knows or discusses. **Do not
carry 46%/63% into a capacity plan for our DAG.** *(Inference, labelled: I have no figure for how
the shared window weights models; neither source has one either.)*

Probed and control-armed (§5): `quota`, `usage limit`, `usage window`, `5-hour`, `five-hour` return
**0 in both articles**. The handful of `weekly`/`subscription` hits are newsletter chrome and
related-article teasers, not analysis. **Neither source models a shared-window economy at all.**

### 4.2 Neither source addresses the fixed per-agent context cost — and their advice inverts under it

`per-agent`, `context floor`, `fixed cost`, `spawn`, `startup` → **0 hits in both** (control-armed,
§5). Both posts implicitly assume the marginal cost of *adding a delegate* is negligible, so the
only thing that matters is which model does the tokens.

Under our measured ~78–85k fixed context load **per spawned agent regardless of task size**, that
assumption fails, and one specific recommendation reverses. mindstudio § "How to Implement This in
Practice" Step 6, verbatim:

> "If Fable 5 decomposes a job into five parallel sub-tasks, run them concurrently rather than
> sequentially. This reduces end-to-end latency and **keeps costs proportional to task count**
> rather than multiplied by wait time."

"Proportional to task count" is offered as the reassurance. For us it is the **problem**: five
parallel sub-agents cost ~400k tokens of pure context floor before any task-specific work happens.
**Their prescription — decompose more finely, fan out wider — is a cost multiplier in our system,
not a saving.** A pattern tuned for a cost we do not pay, silent on the cost that dominates us.

The corollary is a rule they never state and we must: **the decomposition granularity that
minimises cost under per-token billing is finer than the one that minimises it under a fixed
per-spawn floor.** Node granularity should be set by the floor, not by task tidiness — which is
directly the question #574 is grilling.

### 4.3 The advisor pattern's saving comes precisely from NOT spawning an agent — which is why it fits us better

This is the most useful mechanical fact I found, and I verified it against the **primary vendor
doc** rather than taking explainx's word (§5). From `platform.claude.com` advisor-tool docs,
verbatim:

> "The advisor reads the full conversation, produces a plan or course correction, and the executor
> continues with the task."

and, from the sequence diagram: *"Reads the full transcript,<br/>returns strategic guidance"* — as a
server-side `server_tool_use`, **inside a single request**. explainx's relay of this is accurate.

So the advisor pays **no fresh context-loading cost**: it re-reads a transcript that already exists
on the server. That is the exact structural opposite of our DAG, where every node is a separate
Claude Code session that pays the full ~78–85k floor on arrival.

**Labelled inference — the load-bearing one in this report:** for a system whose dominant cost is a
fixed per-spawn context load, **the advisor coupling dominates the orchestrator coupling**, because
it adds a second model's judgement *without adding a second agent*. Everything expensive about our
setup is spawning; the advisor is the one pattern here that buys capability without spawning. If
Fable is to be used at all under the maintainer's "planning / advising / very complex only" ruling,
**advisor-shaped consultation is the cheap way to spend it and a `research`/`review` node is the
expensive way.**

### 4.4 Two hard constraints that bound how far we can take this

- **Capability ordering is enforced, not advisory.** Vendor doc: the advisor must be *"at least as
  capable"* as the executor; explainx adds that invalid pairs return `400 invalid_request_error`.
  Advice flows **down-tier only**. Fable may advise haiku/sonnet/opus executors — compatible with
  the maintainer's ruling — but we can never have a cheap model advise an expensive one. Any design
  where a Sonnet node critiques a Fable node cannot use this mechanism.
- **Our `implement` stage is fixed to Codex `sol`, and the advisor tool is an Anthropic API
  feature.** It cannot advise a non-Anthropic executor. **The advisor pattern is therefore
  unavailable on our single highest-volume stage** — the one where it would pay the most. explainx
  links a related post claiming you can "swap executor to Sol while advisor stays Fable"; I did
  **not** fetch or verify that, and it appears to describe a Claude Code harness configuration
  rather than the API advisor tool. **Flagging as an unverified lead, not a finding.**

### 4.5 Where the sources actively support the maintainer's existing rulings

Worth recording, since two rulings are already made and these are the better source's own words:

- **"Fable reserved for planning / advising / very complex"** is exactly explainx's decision matrix:
  *"Every turn needs frontier reasoning → Fable solo — patterns optimize cost, not max
  intelligence."* The ruling is well-aligned with the best-sourced material I found.
- **"The mapping must be configurable"** is mindstudio Step 2 in all but name — a per-step tier
  assignment across Orchestrator / Execution / High-volume. Both posts treat the model↔stage map as
  configuration, never as something inferred at runtime.

### 4.6 One quality caveat the maintainer should see before trusting "no drop"

mindstudio asserts a 10x saving *"without any meaningful drop in output quality"* and answers its
own FAQ *"Does using cheaper sub-agents hurt output quality?"* with *"For well-defined tasks with
clear inputs and outputs, no."* The only sourced numbers anywhere in either post say **92%** and
**96% of Fable solo** — i.e. a real **4–8 point** quality deficit. mindstudio's "no drop" is
stronger than anybody's data, including the data in the other source.

That deficit lands worst on exactly one of our stages: an **adversarial cold `review`** node whose
entire value is catching what the earlier stages missed. A cheaper model that is 96% as good on
average is not 96% as good at the tail-of-distribution catch, which is the only thing that node is
for. **Downgrading `review` on the strength of these numbers is the least defensible move
available.** *(Assessment, not a source claim.)*

## 5. Control arms run

Per this repo's standard, no absence is reported below without a probe proven able to see.

| # | Probe | Control arm | Result |
|---|---|---|---|
| 1 | Are the two URLs real, or did the slug lie? | Fetched both by two independent routes (WebFetch + Exa `web_fetch_exa`), then `curl` to disk | **Both real.** Neither 404'd; no substitution needed |
| 2 | Is explainx's date really July 2026, or am I trusting the slug? | Page body states `**Published:** 2026-07-08T00:00:00.000Z`; Exa metadata independently returned `2026-07-08` | **Confirmed 2026-07-08** by two routes that are not the slug |
| 3 | mindstudio date | Exa metadata `Published: 2026-07-09`; WebFetch read "July 9, 2026" from the page | **Confirmed 2026-07-09** |
| 4 | Did `curl` get real article text or an SPA shell? *(bounded-probe hazard — a shell would make every absence below fake)* | `orchestrator-worker` → **8** hits, `70–80%` → **1** in mindstudio; `advisor_20260301` → **13**, `BrowseComp` → **32** in explainx | **Probe can see.** Real bodies, not shells |
| 5 | Do either discuss **quota / usage-window** economics? | Same `grep -oic` shape as the passing control in #4 | `quota` **0/0**, `usage limit` **0/0**, `usage window` **0/0**, `5-hour` **0/0**, `five-hour` **0/0**. `weekly` 2/4 and `subscription` 0/11 inspected in context → **all newsletter chrome and related-article teasers**, none in article body. mindstudio's single `rate limit` hit is its own sales copy ("the platform handles… rate limiting, retries"). **Genuine absence** |
| 6 | Do either discuss a **fixed per-agent context cost**? | Same shape | `per-agent` **0/0**, `context floor` **0/0**, `fixed cost` **0/0**, `spawn` **0/0**, `startup` **0/0**. mindstudio's `context window` (1) is "Keep its context window lean"; `overhead` (1) is "carries significant token overhead" — both about *depth of reasoning per call*, neither about a *per-spawn floor*. **Genuine absence** |
| 7 | Is explainx's API surface real, or plausible-sounding invention? *(the most falsifiable thing in either post)* | Fetched the **primary vendor doc** it cites and string-matched | `advisor_20260301` **18**, `advisor-tool-2026-03-01` **27**, `advisor_redacted_result` **5**, `at least as capable` **1**, `full transcript` **3**, `advisor_message` **4**, `max_uses` **5**. Positive control `advisor` → **372**; freshly-invented negative control → **0**. **explainx is accurate on mechanics** |
| 8 | Is mindstudio's "10x" a finding or house boilerplate? | Cross-checked against its own related-article teasers in the raw page | Its teaser for a **different** pairing (Fable + GPT-5.6 Sol, Jul 10) reads *"This model routing pattern cuts costs by 10x without sacrificing quality."* **Identical claim, different models — 10x is a house number, not a measurement** |

**Note on grading:** applying the mandated scheme strictly, **not one claim in either post reaches
`MEASURED`.** Neither author ran anything. explainx is a *faithful and verifiable relay* (probe #7)
of Anthropic-run evals it names and whose provenance it discloses; mindstudio is marketing whose
central number is recycled boilerplate (probe #8).

## Suggestions — what I would change in the design given this

1. **Strike 46% / 63% / 10x from any capacity planning for the DAG.** They are dollar-price ratios;
   our ceiling is a shared usage window. Keep the *direction* (cheap model does the volume), discard
   the *magnitudes*. If a capacity number is needed, it has to be measured on our own window — no
   source supplies one.
2. **Set node granularity from the ~80k spawn floor, not from task tidiness.** This is the direct
   answer to #574's grilling question. Both sources push toward finer decomposition and wider
   fan-out; under a fixed per-spawn floor that advice is inverted. Prefer **fewer, larger nodes**,
   and treat every proposed extra node as costing ~80k before it does anything. A stage split that
   does not save more than ~80k of work is a net loss.
3. **Spend Fable as an *advisor*, not as an extra *node*.** The one pattern here that adds
   frontier-model judgement without adding a spawn is the advisor coupling (§4.3, vendor-verified).
   A dedicated Fable planning *node* pays the full floor; a Fable consult inside an existing node
   does not. This is the cheapest possible way to honour "Fable for planning / advising".
4. **Do not downgrade the `review` node on these numbers.** The sourced figures are 92–96% of Fable
   solo, not the "no meaningful drop" mindstudio claims, and an adversarial cold review is a
   tail-catching job where an average-case deficit is worst (§4.6). If any stage keeps a strong
   model, it should be this one.
5. **Record the capability-ordering constraint in the config schema now.** "Advisor must be at least
   as capable as the executor" is vendor-enforced with a `400`. Whatever shape the configurable
   model mapping takes, it should be unable to express a cheap-advises-expensive pairing, or the
   invalid combination will be discovered at runtime in a background DAG node where nobody is
   watching.
6. **Adopt explainx's framing verbatim in the design doc:** *"patterns optimize cost, not max
   intelligence."* It is the honest one-line statement of the tradeoff and it sets the right
   expectation for a stage map that will be tuned for burn rate.
7. **Two things worth a follow-up probe, neither established here:** (a) whether Claude Code exposes
   an advisor-style consult inside a running session (explainx links a post claiming `/advisor
   fable`; **unverified — I did not fetch it**), which would make suggestion 3 directly
   implementable; and (b) whether an advisor can pair with our Codex `sol` implement stage at all
   (§4.4 says the API tool cannot). Both are `claude-code-expert` questions, not blog questions.

## GitHub repos touched

- **`_None read._** No GitHub repository source, README, issue, or doc was opened in producing this
  report. The three sources consulted were two third-party blog posts and one vendor documentation
  page (`platform.claude.com`), none of which are GitHub-hosted.
- Cited by a source but **deliberately not fetched**, recorded so a later session need not re-derive
  the pointer: [anthropics/claude-cookbooks](https://github.com/anthropics/claude-cookbooks) —
  explainx cites `managed_agents/CMA_plan_big_execute_small.ipynb` as the reference implementation
  of the orchestrator pattern. Reading it would be the natural next step if the orchestrator
  coupling is pursued despite §4.2.

