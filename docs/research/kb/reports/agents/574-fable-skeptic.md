# Research — Fable 5 in agentic workflows: the third-party case, for and against (#574)

**Status:** COMPLETE
**Agent:** 574-fable-skeptic
**Date:** 2026-08-06

**Bottom line:** the ruling (Fable = planning/advising/complex only) is **supported**,
but by much less than it looks. Between two posts there is **one** hard datum — a
paywalled personal invoice I could not confirm by a second route — and **zero** measured
comparisons. The support that survived cross-checking is *structural* (Fable is a rung
above Opus in a 4-tier lineup) and *rhetorical* (the skeptic's own senior-lawyer analogy
restates the ruling). The one place the sources push **back** is `research`: both name
research/synthesis as Fable's flagship strength, while the ruling assigns it to
haiku/sonnet/opus. Justify the ruling from vendor pricing and this repo's own measured
token figures — **not** from these posts.

**Sources (both THIRD-PARTY; neither is a vendor source):**

| # | URL | Published | Age at 2026-08-06 | Author |
|---|---|---|---|---|
| 1 | `https://www.mindstudio.ai/blog/how-to-use-claude-fable-5-agentic-workflows` | 2026-06-12 | **55 days** | "MindStudio Team" (corporate, unattributed) |
| 2 | `https://ruben.substack.com/p/dont-use-claude-fable-5` | 2026-07-08 | **29 days** | Ruben Hassid (named individual) |

> ⚠️ **Provenance caveat on every quote below.** I did not read raw HTML. `WebFetch`
> converts the page and answers a prompt against it **using a small fast model**, so
> every "verbatim" string here is verbatim *as relayed by that summarizer*. That is a
> weaker evidence tier than reading the page. It bit me immediately — see §5.

---

## 5. Control arms run (put first — it changes how to read §1)

**Arm 1 — the absence claim was FALSE.** My first `WebFetch` of the mindstudio post
reported, under "Not mentioned in article": *"Orchestrator vs. worker patterns,
subagent delegation, rate limits, specific cost comparisons"*. I re-probed the same
URL asking for PRESENT/ABSENT per literal token, with two terms I already knew were
present as the control.

| probe | result |
|---|---|
| CONTROL `"thinking budget"` | **PRESENT** — probe can see |
| CONTROL `"200,000"` | **PRESENT** — probe can see |
| `"orchestrator"` | **PRESENT** (but see arm 2 — suspect) |
| `"subagent"` | ABSENT |
| `"rate limit"` | ABSENT |
| `"Haiku"` / `"Sonnet"` | **PRESENT** — and materially so |

So the controls fire, and the first fetch's "not mentioned" list was a **summarizer
false negative**, not a property of the article. The single most decision-relevant
passage in either source — the explicit cheap-model-tiering recommendation — was in
the article all along and the first pass reported it absent. **Do not act on any
absence claim in §1/§2 that I have not explicitly armed.**

**Arm 2 — a positive result that is itself suspect (cross-check disagreement).** The
`"orchestrator"` hit came back as *"Use Claude Code as an orchestrator and Clay as
your data source"*, and the probe volunteered an adjacent sentence *"Remy is the
latest expression of years of platform work. Not a hastily wrapped LLM."* **Clay** and
**Remy** are unrelated third-party products with no plausible reason to appear in this
article's body. Most likely explanation: the fetch is picking up a related-posts /
sidebar / footer block from the mindstudio blog template, not article body text.
**I therefore grade the `orchestrator` hit UNRELIABLE and do not rely on it.**

**Arm 4 — SECOND ROUTE on source 2, and it changes the evidence tier. ⚠️ The ruben
post is PAYWALLED.** I re-fetched it via a different tool (`web_fetch_exa`) to
cross-check the numbers. That route returned the raw article text — and it **stops
dead** mid-sentence at *"I won't waste your time explaining why this model is widely
better than the…"*, i.e. it retrieved only the **free preview**. Consequences:

- Everything `WebFetch` reported from the *preview* region **cross-checks exactly**
  (the "orange one. Better at everything" line; the July 12 free-access deadline). So
  `WebFetch` is not fabricating wholesale — good.
- But **every load-bearing number — the $14 invoice, "$10 per million input / $50 per
  million output", the "$0.15 → $14 at 40 turns" curve, and all four concessions —
  sits BEHIND the paywall and I could NOT confirm any of it by a second route.** The
  section headings `WebFetch` listed do not appear in the preview either.
- I therefore **downgrade every one of those to single-route, unconfirmed**. They may
  be perfectly accurate; a summarizer model with paywalled access is simply not a tier
  of evidence I will let a design decision rest on — and this same tool already
  produced one false negative today (arm 1).

**Arm 5 — a fact the preview establishes that neither fetch summary surfaced: the tier
stack has FOUR levels, and Fable sits above Opus.** Verbatim:

> "Claude comes in different flavors of intelligence: **Haiku**, the fastest but dumbest
> model. **Sonnet**, the middle one. Good fast/smart ratio. **Opus**, the big one. Very
> smart, used to be the smartest. **Mythos**, the new smartest model. But also the most
> expensive."
> "they launch a 'Mythos-level' of Claude with a name associated with it instead of just
> a number. And it's called '**Fable-5**'."

So Fable-5 is a *Mythos-tier* model — a rung **above** Opus, not a variant of it. The
maintainer's "stage models come from haiku / sonnet / opus, Fable is reserved" is
therefore drawing the line exactly at the published tier boundary, not at an arbitrary
point. **This is the cleanest structural support for the ruling in either source.**
(Grade: **REPORTED** — it is a blogger's description of the vendor's lineup, not a
vendor page. Trivially checkable and worth checking.)

**Arm 6 — the analogy that IS the ruling, verbatim from the free preview.** This is the
one substantive passage I can quote at full confidence, because it is outside the
paywall and cross-checked:

> "Fable-5 is the expensive senior lawyer with 20 years of experience. He costs $1,000
> per hour. Sonnet-5 is the cheap intern, and only costs $100/hour. […] **You don't want
> to pay the expensive lawyer for every quick contract review. You want to pay the
> expensive senior lawyer to define the overall international contract strategy. Then
> the drafting assistant (Sonnet-5) follows that strategy consistently.**"

The $1,000/$100 figures are an **illustrative analogy, NOT pricing** — a 10× ratio
invented to make the point. Do not quote them as cost data. But the *pattern* — expensive
model sets strategy, cheap model executes it consistently — is precisely the maintainer's
architecture, stated by the skeptic himself in his own framing. Grade: **OPINION**
(analogy), but it is the clearest statement of the position in either post.

Also from the preview, worth logging: *"Make Claude conduct market research for 11
minutes, through 258 sources"* (**REPORTED**, no method) — and a bias disclosure the
author volunteers: *"I'm not paid by Anthropic. […] I don't pick sides."*

**Arm 3 — a staleness tell inside the "present" text.** The cheap-model sentence names
**"Claude 3.5 Haiku or even Claude 3.5 Sonnet"**. A post published 2026-06-12 that
reaches for the *3.5* generation is either recycling older boilerplate or was
substantially written long before publication. This does not falsify the *pattern* it
advocates (tier expensive→cheap by step), but it is direct evidence the article's
model-specific detail is stale, and it lowers my confidence in the whole post as a
guide to current model behaviour. **Inference, labelled: this reads as SEO content
with a Fable-5 headline bolted onto an older generic "agentic workflows" body.**

---

## 1. mindstudio — patterns advocated

Section headings, in order: *What Makes Claude Fable 5 Different for Agentic Work* ·
*Understanding Claude Fable 5's Extended Reasoning* · *Setting Up Agentic Workflows
with Claude Fable 5* · *Managing Token Costs Without Sacrificing Quality* · *Common
Agentic Workflow Patterns That Work Well* · *How MindStudio Fits Into Claude Fable 5
Workflows* · *Troubleshooting Common Issues* · *FAQ* · *Key Takeaways*.

Note heading 6: the post is **vendor content marketing for MindStudio's own platform**.
That is a standing bias, not a disqualification, but it explains the "use different
models at different steps — most agentic platforms let you" framing, which is also a
pitch for their product.

### The one passage that actually bears on the decision

From **"Managing Token Costs Without Sacrificing Quality"** (verbatim, via arm-1 probe):

> "Claude Fable 5 is more expensive per token than Claude's lighter models."
> "For a single query this doesn't matter much, but agentic workflows run many
> queries — and thinking tokens compound quickly."
> "Not every step in a complex workflow needs Fable 5."
> **"A common pattern is to use Fable 5 for the reasoning-heavy steps and a cheaper
> model for execution steps."**
> "Step 1 benefits from Fable 5's extended reasoning."
> "Step 3 is mostly formatting work — Claude 3.5 Haiku or even Claude 3.5 Sonnet
> handles it well at a fraction of the cost."
> "Most agentic platforms let you specify different models at different steps. Use
> that flexibility."

And from **"Understanding..."**, on the cost mechanism:

> "The thinking tokens don't appear in the output — they're internal computation. But
> they do count toward your usage costs, so setting an appropriate budget for the task
> is worth the attention."

From the same section, on where Fable earns its place:

> "Extended thinking adds real value when: [1] The task has ambiguity... [2] There are
> dependencies between steps... [3] The model needs to generate a plan... [4] Tool
> calls need to be sequenced... [5] The output will be used downstream..."

> "Not every task benefits from a high thinking budget. For straightforward tasks —
> filling out a template, translating text, classifying something with clear criteria —
> extra thinking time doesn't produce meaningfully better outputs."

From **"Common Agentic Workflow Patterns That Work Well"** — the four patterns are
*research and synthesis*, *code review and debugging*, *multi-step data processing*,
*document generation*. On research:

> "This is where Fable 5 consistently outperforms lighter models."

On review:

> "Asking it to review a PR, identify security vulnerabilities, or debug a multi-file
> issue produces better results than lighter models — particularly when the bug
> involves non-obvious interactions between components."

### Claims table

| claim | grade | method | my assessment |
|---|---|---|---|
| "Fable 5 is more expensive per token than Claude's lighter models" | **OPINION**/common knowledge | none stated; no prices given anywhere in the post | Almost certainly true, but the post supplies **zero** numbers to size it. Useless for budgeting. |
| "use Fable 5 for the reasoning-heavy steps and a cheaper model for execution steps" | **OPINION** (architectural advice) | none — no A/B, no cost delta, no quality measurement | This is the maintainer's ruling, stated by a third party with no evidence behind it. **Agreement is not corroboration.** Two parties asserting the same unmeasured thing is still unmeasured. |
| "Fable 5 consistently outperforms lighter models" at research/synthesis | **OPINION** | "consistently" implies repetition; **no eval, no sample, no task set, no numbers** | The word "consistently" is doing evidentiary work it has not earned. Reject as evidence; it is a vibe. |
| Thinking-budget bands: low 1,000–4,000 / med 4,000–10,000 / high 10,000–32,000+ tokens | **REPORTED** | numbers with no method and no vendor citation | Plausible-looking API-parameter guidance. Unverified here; another agent has the vendor sources. Treat as *unconfirmed*. |
| "Start at 4,000–6,000 budget tokens for most agentic tasks" | **REPORTED** | none | A specific number with no derivation — the most dangerous shape of claim. Do not adopt. |
| "Claude Fable 5 supports a 200,000 token context window" | **REPORTED** | none; no vendor link | ⚠️ **Checkable and worth checking** — this session's own model id is `claude-opus-5[1m]`, i.e. a 1M-context variant exists in this product line. A flat 200K claim for Fable may be wrong or may be the non-extended default. Flagging for the vendor-source agent. |
| Context-control tactics: summarize intermediate results, clear tool history, external memory, break into sub-tasks with fresh context | **OPINION** | none | Generic and sound. Notably this is *exactly* a per-stage-fresh-context DAG — see §4. |
| Prompt caching reduces repeated system-prompt cost | **OPINION** (true, but unmeasured here) | none | True as a vendor feature; the post gives no discount figure. |
| "Claude 3.5 Haiku or even Claude 3.5 Sonnet handles it well" | **STALE** | none | See control arm 3. Names a two-generation-old model tier in a 2026-06 post. |

**Net on source 1:** it contains **not one measured claim**. Zero prices, zero
latencies, zero benchmark scores, zero percentages, zero eval results. Its entire
evidentiary content is an author asserting architectural preferences. Its *conclusion*
happens to match the maintainer's ruling, which makes it tempting and therefore
dangerous.

---

## 2. ruben — the case against

Section headings, in order: *Don't prompt Fable 5* · *Expensive super-intelligence* ·
*Some Fable-5 worthy tasks* · *Connect Fable to everything* · *What the f\*\*\* is
Claude Cowork?* · *What the f\*\*\* is Claude Code?* · */fable-prompter* · *Your team's
brain, in a folder* · *I don't know nothing*.

**The title is clickbait and the author says so by the end.** The headline is "Don't
use Claude Fable-5"; the actual thesis is *don't use it for many turns*. That is a
much narrower and much more useful claim.

### The cost argument — the only part with a method

> ⚠️ **Read this table through arm 4: the entire cost argument is behind the paywall
> and is SINGLE-ROUTE.** I could not confirm one figure in it by a second tool. Grades
> below are what the claims *would* rate **if accurately relayed**; the relay itself is
> unverified.

| claim | verbatim | grade |
|---|---|---|
| turn count is the cost driver | "But it quickly gets crazy expensive if you do too many turns. Don't." · **"Turns are the most expensive habit."** | **OPINION** (mechanism) — but the mechanism is real and well-understood: each turn re-sends accumulated context as input |
| his own spend | spent **"$14 (!!!), one-shot, on top of my $100 plan"** producing 30 newsletters | **MEASURED-ish → I grade it REPORTED.** It is a real number from a real invoice, i.e. an **ANECDOTE with a receipt**: n=1, one workload, no control, not reproducible by me. Real, but not generalisable. |
| the per-turn curve | "$0.15 for a one short question" through **"$14 when you hit 40 turns"** | **REPORTED** — derived arithmetic, not a measurement |
| list price | **"$10 per million input tokens, $50 per million output tokens"** | **REPORTED** — quoted as fact, no vendor link shown in what I retrieved |

**My assessment of the $0.15 → $14 curve.** This is the single most useful number in
either source *if* the pricing is right, and its shape is the point: cost is
**superlinear in turns**, because turn *n* pays input on everything from turns 1..n-1.
40 turns costing ~93× a single turn is consistent with that quadratic-ish growth, so
the number is at least internally coherent. But it is **arithmetic, not a measurement** —
he did not instrument 40 turns and read a bill; he computed it. Grade accordingly.

**Is he comparing like with like?** On cost, there is nothing to compare — he never
prices Opus/Sonnet/Haiku against Fable, so "Fable is expensive" has **no denominator**
anywhere in the piece.

On capability the comparison is worse:

> "Sonnet 5 is only a tiny little bit better than Opus 4.8"

— shown against a **single "Knowledge work" metric**, with no speed or cost weighting.
And the Fable case rests on a chart described as *"the orange one. Better at
**everything**"* **with no citation**. That is **not like-for-like** and it is not
evidence; it is a screenshot of a marketing chart with an arrow on it. Grade **REPORTED
at best, functionally OPINION**.

### The concessions — which are the actually useful part

| context | verbatim |
|---|---|
| high-value planning | **"Ask Fable super hard goals, for one or two turns max."** |
| hand-off pattern | "Fable-5 (High) + Opus 4.8 (High)" — **"You use it, few turns, and then you switch the model to Opus"** |
| research synthesis | "end-to-end research plus self-verification is exactly the long-horizon, evidence-grounded work Fable 5 was built for" |
| complex decisions | excels at "multi-angle reasoning" in decision reviews |

All four: **OPINION**, no method.

### Supply / rate-limit claims

| claim | grade | note |
|---|---|---|
| free until 2026-07-12, then pay-per-use | **REPORTED** | **time-bound and now EXPIRED** — 25 days stale as of today |
| org settings allow per-user spend limits | **REPORTED** | product feature, checkable |
| Anthropic said Fable returns to subscriptions **"as soon as capacity allows"** | **REPORTED** (2nd-hand vendor quote) | ⚠️ **This is the load-bearing supply claim** and it is a *paraphrase of a vendor statement relayed by a blogger*. If true it directly supports "Fable is supply-constrained". It is also the claim most likely to have changed in 29 days. **Must be checked against the vendor, not accepted from here.** |
| "Somehow we can't switch model during Cowork" | **ANECDOTE** | product-surface complaint about Claude Cowork; irrelevant to a `claude --bg` DAG, which selects a model per process at spawn |

---

## 3. Where they disagree

**They barely disagree at all, and that is itself worth noticing.** Strip the
rage-bait title off source 2 and both posts land on the *same* recommendation:

> Use Fable for a small number of high-value reasoning turns; hand everything else to a
> cheaper model.

- mindstudio: *"use Fable 5 for the reasoning-heavy steps and a cheaper model for execution steps"*
- ruben: *"Ask Fable super hard goals, for one or two turns max"* → then *"switch the model to Opus"*

Where they differ is only in **emphasis and in what they measure**:

| axis | mindstudio | ruben |
|---|---|---|
| framing | Fable is great, here's how to afford it | Fable is a trap, here's the narrow case |
| cost numbers | **none at all** | list price + a personal invoice + a derived curve |
| what drives cost | *thinking tokens* compounding | ***turns*** compounding |
| the cheap tier | Haiku/Sonnet (named, but stale 3.5) | **Opus 4.8** as the step-down |
| bias | selling an agent platform | selling a newsletter/prompt-pack |

**The turns-vs-thinking-tokens split is the one substantive disagreement**, and ruben
is more nearly right for *our* case: in a long agent session the dominant term is
re-sent context per turn, not the internal thinking budget. Both are real; only ruben
names the one that scales quadratically.

**Versus the vendor:** neither post cites Anthropic for anything except ruben's
second-hand "as soon as capacity allows". Two vendor-checkable claims I am escalating
rather than asserting: (a) **200K context for Fable** — suspicious, since this very
session runs `claude-opus-5[1m]`, a 1M-context id, so a flat 200K may be wrong or
variant-specific; (b) **$10/M in, $50/M out**. I did not verify either; the vendor-source
agent should.

---

## 4. Does this support or undermine "Fable for planning/advising/complex only"?

**It supports the ruling — but far more weakly than it first appears, and it undermines
one specific part of it.**

**The strongest support is structural, and it survived cross-checking.** Ruben's free
preview lays out a **four-rung** lineup — Haiku → Sonnet → Opus → **Mythos**, with
Fable-5 being a *Mythos-tier* release. The maintainer's "stages draw from haiku /
sonnet / opus; Fable is reserved" therefore cuts at the **published tier boundary**,
not at an arbitrary line. And the skeptic's own analogy states the ruling almost
word-for-word: pay the senior lawyer to *"define the overall international contract
strategy"*, then let the intern *"follow that strategy consistently"*. That passage is
outside the paywall and confirmed by two routes — it is the highest-confidence evidence
in this report, and it points **at** the ruling.

**Where the support is real.** Both independent third parties, with opposite biases
(one selling an agent platform, one selling a Claude newsletter), converge on
expensive-model-for-planning / cheap-model-for-execution. Convergence across opposed
incentives is a mild positive signal. Ruben's cost mechanism — **cost is superlinear in
turns** — is the strongest single argument in either post, and it maps directly onto our
architecture: a `research` or `implement` node is a *many-turn* session by construction.
Putting Fable on a many-turn node is precisely the shape he priced at $14.

**Where I must be honest that this is thin.** Between the two posts there is **exactly
one** hard datum: a single personal invoice (n=1, no control, one workload) plus
arithmetic off a list price I have not verified. Everything else is assertion. If the
maintainer's ruling rested on these two posts it would be resting on nearly nothing.
**My finding is that the ruling is right for reasons these posts gesture at but do not
establish** — and it should be justified from the vendor's pricing and this repo's own
measured token figures (MEMORY records ~78k tokens per agent regardless of size, and a
weekly window shared across models), not from blog agreement.

**Where a source actively undermines part of the ruling.** The ruling reserves Fable for
"planning / advising / very complex tasks" and assigns `research` to haiku/sonnet/opus.
But **both** posts single out *research and synthesis* as Fable's flagship strength:

- mindstudio: research/synthesis is the **first** listed pattern — *"this is where Fable 5 consistently outperforms lighter models"*, explicitly because the model must "track what it's already found, decide what additional searches would be valuable, and maintain a coherent synthesis".
- ruben: *"end-to-end research plus self-verification is exactly the long-horizon, evidence-grounded work Fable 5 was built for"*.

So the sources' own logic says the `research` node is a **Fable-shaped** task. The
counter-argument that saves the ruling is ruben's, not mindstudio's: research is
*many-turn*, and many-turn is exactly what makes Fable ruinous. **Both things are true
at once** — research is where Fable is best AND where it is most expensive. That is a
genuine tension the ruling currently resolves by fiat, and neither source resolves it.

**One thing neither source touches, which matters more than anything they do say:** our
constraint is not only price, it is **supply** — a shared weekly window. A per-token
cost argument does not capture a rationing constraint. Ruben's *"as soon as capacity
allows"* is the only gesture at it and it is second-hand and 29 days old.

---

## Suggestions — what I would change in the design given this

1. **Keep the ruling; replace its justification.** Do not cite either post as support
   in a receipt or ADR. Cite vendor pricing + this repo's own measured per-agent token
   figures. Two blogs agreeing is not evidence, and one of them is 55 days old with
   3.5-era model names in its body.
2. **Adopt "turns", not "model tier", as the budgeting primitive.** Ruben's is the one
   real mechanism here: cost is superlinear in turns. A DAG node's expected *turn count*
   should be what gates it away from Fable — which automatically keeps Fable off
   `research`/`implement` (long-horizon) without needing a per-role rule at all, and
   automatically permits it on a bounded 1–2-turn advisory call.
3. **Consider a bounded Fable *advisory* call inside `research`, not a Fable research
   node.** This is the shape both sources actually endorse ("super hard goals, one or
   two turns max"; "reasoning-heavy steps"): the node stays sonnet/opus for the many-turn
   sweep, and spends *one* bounded Fable turn on plan-shaping or final synthesis. It
   captures the strength both posts name while staying inside the cost mechanism ruben
   identifies. **This is my inference, not either source's recommendation.**
4. **Do not import any number from these posts** — not the 200K context, not
   $10/$50 per M, not the 4,000–6,000 thinking-budget default. Every one is ungrounded
   here; the 200K figure is actively suspect against this session's own `[1m]` model id.
5. **Re-verify the supply claim before it loads any design.** "Returns to subscriptions
   as soon as capacity allows" is the only supply evidence in either source, it is
   second-hand, and it is 29 days old. If the DAG's model policy leans on scarcity, that
   leans on a blogger's paraphrase.
6. **Note the vendor-content bias in source 1** if it is ever quoted: heading 6 is *"How
   MindStudio Fits Into Claude Fable 5 Workflows"*. Its "use different models at different
   steps — most agentic platforms let you" advice is simultaneously a product pitch.

## GitHub repos touched

_None._ Both sources are non-GitHub web posts (a corporate marketing blog and a
Substack newsletter); no repository source, README, issue tracker, or docs tree was
consulted in producing this report.
