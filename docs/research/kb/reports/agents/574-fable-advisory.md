# Advisory — #574 node granularity and the first-slice role set (Fable pass)

**Status:** COMPLETE
**Date:** 2026-08-06
**Read:** all four worker reports in full (`574-context-engineering.md` 1101 ln, `574-model-selection.md` 261 ln, `574-fable-skeptic.md` 395 ln, `574-orchestrator-budget.md` 362 ln); `.agent/notepad.md` lines 7525–7830 (the full "#574 grill" section, R1–R7 + evidence log); `docs/receipts/573.md`; `docs/receipts/578.md`; issue #556 body via `gh`; `docs/specs/agent-team-first-slice.md`.

## Verdict in one paragraph

R1–R6 are sound and I ratify all six — R1 on a stronger mechanism than the decision log
currently records (see §4). For R7 I recommend: **research → Sonnet 5 @ `high`, implement →
Codex `sol` @ extra-high (standing), review → Opus 5 @ `high`, Haiku nowhere in slice 1,
Fable nowhere in the stage table** — with a deliberate **bring-up phase** that runs research
on Opus 5 for the first few tickets, per the vendor's "distinguish model failures from setup
failures" argument, then demotes it by a table PR (§1, §3). The Fable advisory consult goes
**behind a probe, not into slice 1** (§2). The one real defect this pass found is in the
*justification*, not the decisions: the R7 resolution in the decision log leans on the
"separate rate-limit pools ⇒ heterogeneous models are a throughput win" fact, which is an
**API-metering** fact that does not transfer to the **subscription meter** the DAG actually
runs on — and the claim that model choice even lowers subscription window burn is
single-route and unverified (§5, misses 1–2). Fix the rationale before it lands in the
receipt; the decisions themselves survive the fix.

## 1. The stage → model/effort table

| Stage | Runner | Model | Effort | One-line reason |
|---|---|---|---|---|
| `research` | `claude --bg --agent researcher --model sonnet --effort high` | **Sonnet 5** (bring-up: Opus 5, see §3) | `high`; trial `xhigh` only on observed missed-source failures | 1M context for the 6,446-file corpus; the vendor names Sonnet for *"high-volume sub-agents in multi-agent orchestration setups"* (ctx-eng §3, source 5 verbatim); Haiku is disqualified twice over (below) |
| `implement` | `codex exec` | **`sol`** | extra-high | Standing decision (R7 brief); the only lane adding Anthropic-side headroom (map #563: *"parallelism is the spend lever, Codex is the capacity lane"*); and it is *what makes* the Opus reviewer cold — moving implement onto a Claude model would force review off-family instead (model-select §6, "Don't reverse this casually") |
| `review` | `claude --bg --agent adversarial-reviewer --model opus --effort high` | **Opus 5** | `high`; raise to `xhigh` only on an observed miss (model-select §6, S5's rule) | Highest judgment density, smallest input — the most expensive sanctioned per-token model is cheapest in absolute terms here; the only sourced advisor numbers put cheap-model quality at 92–96% of frontier, and *"a 4–8 pt deficit is worst on a tail-catching adversarial pass"* (orch-budget §4.6) — do not downgrade this stage |
| `gate` | human | — | — | Escalation-only kind (R5); no model to pick |
| *(scheduler)* | python | — | — | R3: deterministic, no LLM |
| *(Fable)* | **absent from the table by design** | — | — | Planning/advising/complex only (R7 ruling, confirmed by 2× price + 25–40% API throughput + the entitlement gate); the advisory-consult shape is §2 |

Five constraints the table must carry into R2's config schema:

1. **Effort is a mandatory column, not an optional one.** Both Anthropic-corpus workers
   converged (*"Effort is the primary control for the trade-off between intelligence, latency,
   and cost"* — ctx-eng §4; model-select suggestion 2), and the repo's own corpus makes it
   *operationally* mandatory: `wf-dag-model-routing.md:699` (via the decision log's correction)
   — a non-interactive `/effort` cannot release the model-default hold, so **`--effort` must be
   passed at launch**. R6's recorded launch shape should be amended to
   `claude --bg --agent <role> --model <m> --effort <e> "<brief>"`.
2. **Haiku 4.5 cannot appear in a row of this schema as written.** Two hard blockers for
   `research` (200K context vs a 1M-needing corpus sweep; three routes confirm it has **no
   effort parameter at all** — model-select C3), plus a third nobody connected: a launcher that
   mandatorily passes `--effort` (constraint 1) cannot launch Haiku uniformly. Either the
   schema forbids `haiku` or effort becomes nullable with a distinct launch shape. For slice 1
   the clean answer is: **Haiku has no stage, and that is a feature** — there is no
   mechanical/formatting stage left once the scheduler is deterministic python.
3. **The `review` role definition needs two measured prompt rules now** (model-select §6, S7,
   both with silent failure modes): coverage-first — **no** "be conservative"/severity-filter
   instruction (measured recall drop on Opus 4.7/4.8/5 and Sonnet 5; filter downstream
   instead); and **delete** any self-verification instruction (measured over-verification on
   Opus 5, *"removing them reduces over-verification with no capability regression"*).
4. **Date-stamp the cost model:** Sonnet 5 intro pricing ($2/$10) ends **2026-08-31**;
   research-node input cost rises 50% on 2026-09-01 (model-select D6). Any budget figure
   written this week silently breaks in September.
5. **Record the advisor capability-ordering constraint in the schema now** even though the
   advisor is deferred (§2): advisor ≥ executor is vendor-enforced with a 400
   (orch-budget §4.4, verified against the primary vendor doc). The schema should be unable to
   express cheap-advises-expensive, or the invalid pair is discovered at runtime in a
   background node nobody is watching.

## 2. Fable advisory consult — slice 1 or probe?

**Behind a probe. Not in slice 1.** The convergence of two workers on the *shape* (a bounded
consult inside a node, never a node) is real and I endorse the shape — the advisor is the one
pattern that adds frontier judgment **without paying a ~78–85k spawn floor**, because it runs
server-side over the request's existing transcript (orch-budget §4.3, verified against the
primary vendor doc: *"Reads the full transcript, returns strategic guidance"* inside one
request). But three facts make it a probe, not a slice-1 dependency:

- **Reachability from `claude --bg` is unverified**, and both sources describe it strictly as
  a Messages API request parameter + beta header with *"no mention of Claude Code, CLI, or
  subagents"* (model-select §4). Load-bearing and single-route — exactly what this repo's
  rules say not to build on.
- **It is a beta, and the DAG runs on subscription auth.** Even if Claude Code exposes it, the
  billing meter is unknown (API-key dollars vs subscription window — see §5 miss 2).
- **It cannot cover the highest-volume stage anyway**: the advisor tool is Anthropic-only, so
  the Codex `sol` implement lane is out of reach (orch-budget §4.4). Its slice-1 payoff is
  limited to research/review, both of which work without it.

Adding an unverified beta to a brand-new harness also doubles the vendor's own warned-against
confound (*"harder to distinguish between model failures and setup failures"*) — slice 1
should have exactly one novel thing in it: the harness.

**What the probe must show, in order — stop at the first failure:**

1. **Surface exists:** Claude Code (this pinned version, subscription auth) exposes advisor
   configuration at all — a settings key, flag, or model string. A `claude-code-expert` /
   step-00 KB grep question first, then a live probe; do not web-search it.
2. **A call succeeds on subscription auth** from a background (`--bg`) session — not just from
   an API key. Both arms: a valid pairing succeeds AND an invalid pairing (cheap-advises-
   expensive) returns the documented 400, proving you exercised the real feature.
3. **The economics survive the CLI path:** the consult consumes the *existing* session
   transcript (no re-upload of a fresh project-context load) and its cost lands on a meter you
   can name. If the CLI path requires re-sending context into a fresh call, the "no spawn
   floor" saving — the entire reason to prefer advisor over a Fable node — is gone.
4. **Frequency is controllable** (`max_uses` or prompt steering) — explainx's honest-limits
   note that *"once-per-task is a target, not a guarantee"* (orch-budget §2.3).

**Meanwhile, Fable-for-advising has a slice-1-compatible form that needs no probe:** a
human-invoked Fable advisory session over a decision's evidence — which is literally this run,
and is what Ray's R7-final instruction already exercised. The escalation `gate` can route to
it. That keeps the ruling's "advising" lane real while the API path is unproven.

## 3. Vendor selection procedure vs our throughput argument

**Neither wins outright — they answer different phases, and the design should encode both.**

The vendor's procedure (*"start with the most intelligent generally available model and use
effort level to dial in"*; *"Starting with a smaller model can also make it harder to
distinguish between model failures and setup failures"* — ctx-eng §3, verbatim) is
specifically an argument about **attribution during bring-up**. For a brand-new harness with
no baseline it is the sharp argument, and I would honor it: **for the first N end-to-end
tickets (suggest 3–5), run `research` on Opus 5 @ `high`** — so the first time a research node
misses, hallucinates, or stalls, the model is above suspicion and the harness is the suspect.
Review is already on Opus. Then demote research to Sonnet 5 via a table PR, which is exactly
the reviewable-config surface R2 was designed to be. ("Most intelligent generally available"
literally means Fable, but Ray's ruling and the supply evidence overrule that endpoint; Opus
is the honest bring-up compromise.)

The throughput argument wins at **steady state** — but here I must flag that it is
**mis-stated in the decision log** (§5 miss 1, dissent D1). As recorded, it rests on S4's
*"rate limits are applied separately for each model"* — an **API-tier** fact. The DAG runs on
the **Claude Code subscription**, whose binding constraint the repo's own corpus states is the
**shared five-hour/seven-day window** (*"model choice lowers the burn RATE but adds no
headroom; only the Codex second-vendor lane does"* — `wf-dag-model-routing.md` §5, quoted in
the decision log itself). On that meter, separate per-model API pools buy nothing. What
actually survives on the subscription meter: (a) cheaper models burn the shared window slower
— *if* the window weights by model, which is inherited and unverified (miss 2); (b) **Codex is
the only real headroom**; (c) Fable additionally sits behind its own credit/entitlement gate
(the native `model_fable_consent` substitution — map #563), which is supply-rationing
regardless of meter. The 25–40% API throttle remains good *corroborating evidence that the
vendor itself rations Fable* — cite it as that, not as the DAG's operative ceiling.

So: vendor procedure for bring-up; cost/supply (correctly re-grounded) for steady state; the
configurable table is what makes holding both positions cheap.

## 4. Is R1 safe? (and R2–R6)

**R1 is safe, and on stronger grounds than the decision log records.** The orch-budget
objection is real as far as it goes — under a ~78–85k per-spawn floor, decomposition is a cost
multiplier, and both third-party posts' "decompose finer, fan out wider" advice inverts
(orch-budget §4.2, control-armed: neither post models a per-spawn cost at all). But it does
not reach stage-per-issue, for four independent reasons — the first is mine and nobody stated
it:

1. **Prompt caches do not cross models, so the merge alternative saves nothing on this
   chain.** The slice-1 stages run on three different executors (Sonnet / Codex `sol` / Opus).
   ctx-eng's rescue (changing *effort* between requests destroys cached prefixes, so per-stage
   effort is unobtainable in one session) is correct but is the weaker half — changing *model*
   is a different inference stack entirely; there is no cached prefix to preserve across
   research→implement→review even in principle. The ~80k×3 floor is the price of heterogeneous
   models, not of R1. The "fewer, larger nodes" caution binds **below** stage granularity and
   on **fan-out width** — exactly where the decision log's own reading put it.
2. **Two stages are hard process boundaries regardless.** Implement is another vendor's CLI;
   and spec #550 US-14 requires the reviewer to see the diff **without design context** — a
   merged session structurally cannot produce a cold reviewer. Only research is even a
   candidate for merging, and it has nothing same-model adjacent to merge into.
3. **R1 is what makes #573's rework semantics real** — rework = reopen the *upstream issue*,
   which requires an upstream issue to exist (decision log, R1 grounds). A whole-ticket node
   has nothing to reopen.
4. **A whole-ticket single-context node is what trips the ~30% context gate** (R1 grounds),
   converting one floor into a restart-with-handoff anyway.

**Adopt the objection as a standing table-review question rather than a redesign:** any PR
adding a stage row must answer *"does this split save more than one ~80k floor, or differ from
a neighbor in model or effort?"* That is the durable form of orch-budget suggestion 2. Two
residual caveats, both acceptable: R5's fixed template spends one research floor on tickets
that need none (accepted cost, revisit with template variants in a later slice); and the
78–85k figure was measured on Agent-tool delegations — a fresh `claude --bg` session loads the
same project context so I treat it as transferable, but that is inference, labelled.

**R2** — sound; amend per §1 (effort column mandatory; haiku/effort schema constraint;
advisor-ordering constraint). The fail-closed rule for a label with no table row is exactly
right. **R3** — sound; no notes. **R4** — sound; the narrowing MUST land verbatim in the
receipt (the decision log already says this; I re-flag it because the original #573 sentence
is quoted in the map and a future session reading the map will "fix" it back). **R5** — sound;
the every-ticket-research cost is priced above. **R6** — sound; amend the launch shape to
carry `--model` and `--effort` explicitly (§1 constraint 1).

## 5. What the four workers missed

1. **The meter mismatch — the biggest one.** model-select's decisive finding (Fable at 25–40%
   ITPM/OTPM) and its architectural corollary (*"separate pools ⇒ heterogeneous stage models
   are a throughput win independent of quality"*) are **API-metering facts**. The DAG runs on
   the subscription. The decision log flags "TWO DIFFERENT METERS" for *pricing* — and then
   imports the separate-pools throughput claim into the R7 resolution anyway. No worker, and
   no synthesis line, reconciled the two meters end-to-end. Consequence: rewrite the R7
   rationale for the receipt as §3 states it. The *decisions* all survive; the *stated ground*
   does not.
2. **Nobody knows what the shared window actually meters.** *"Model choice lowers the burn
   RATE"* is inherited from `wf-dag-model-routing.md` §5 — single-route, and load-bearing for
   the entire cheap-model-routing argument on the subscription. If the window meters raw
   tokens unweighted by model, Sonnet-vs-Opus buys **nothing** against the binding constraint,
   and the steady-state argument reduces to "Fable is gated + Codex adds headroom" alone.
   Second route: the vendor's usage/limits docs for subscriptions (a step-00 KB grep first),
   or an observed `/usage` delta across two known same-shape workloads on different models.
   Worth settling before the receipt asserts the burn-rate claim as ground.
3. **Two workers flatly contradict each other on where `research` belongs, and no line
   resolves it.** fable-skeptic §4: both third-party posts name research/synthesis as Fable's
   *flagship* strength — *"the sources' own logic says the research node is a Fable-shaped
   task"* — and honestly calls the tension "resolved by fiat". model-select/ctx-eng assign it
   to Sonnet on cost/positioning. The resolution exists scattered across the corpus (research
   is many-turn, and many-turn is where Fable's superlinear turn cost and throttled supply
   bite hardest — fable-skeptic's own ruben mechanism), but the receipt should state it in one
   place, or the next reader of fable-skeptic's report reopens R7.
4. **The Haiku ∧ mandatory-`--effort` collision** (§1 constraint 2). model-select proved Haiku
   has no effort dial; the decision log's own correction proved `--effort` at launch is
   mandatory. Nobody put the two together: the launcher cannot treat Haiku uniformly, which is
   itself a schema-level argument for keeping Haiku out of the table.
5. **The advisor economics were verified against the API, not against Claude Code's client
   shape.** orch-budget verified "reads the existing transcript server-side" from the vendor
   doc — true for a Messages API caller. Whether the *CLI's* advisor path (if one exists)
   preserves that no-fresh-context property is exactly probe step 3 in §2; a consult that
   re-uploads context is a worse Fable node, not a cheaper one.
6. **Effort governance for the Codex lane is asserted, never validated.** "Codex `sol` at
   extra-high" is standing (fine), but no worker checked what validates or bounds it — #558
   covered exhaustion detection and the verdict contract, not effort. Minor; note it in the
   stage-table PR so the Codex row's effort value is not decorative.
7. **A positive miss worth recording:** ctx-eng's elicitation finding (*"Defining the tool is
   not sufficient on its own; without an instruction in the system prompt, Claude Fable 5
   rarely calls it"*) is the best available mechanism for this repo's 3-for-3
   SendMessage-before-idle failure, and it generalizes to every DAG node's evidence-comment
   contract: **the role definition must elicit the delivery act, not merely permit it.** The
   decision log logs it; make sure it lands in all three role definitions, not just the
   advisory post-mortem.

## Dissents — where I disagree with a decision already taken

- **D1 (correction, not reversal): the R7 resolution's stated ground is partly wrong.** The
  "separate pools ⇒ throughput win" sentence must not reach the receipt unqualified — it is
  true on the API meter and irrelevant on the subscription meter the DAG runs on (§3, §5
  miss 1). Re-ground R7 on: 2× price (API-corroborated), the Fable entitlement gate, the
  25–40% throttle *as evidence of vendor-side rationing*, and Codex as the only headroom.
  The ruling itself stands.
- **D2 (mild): a straight Sonnet assignment for `research` skips the vendor's bring-up
  argument.** Run research on Opus 5 for the first 3–5 tickets, then demote by table PR (§3).
  Cheap to do, and it buys clean failure attribution exactly when the harness is least
  trusted.
- **No dissent on R1–R6.** An advisory pass that ratifies everything is worth nothing, so I
  looked hardest at R1 (the invited target) and at R2's schema; R1 survives on four
  independent mechanisms (§4), and my R2 notes are amendments, not objections.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issue #556 body read via
  `gh`; all other sources were local files in this repo (worker reports, notepad, receipts,
  spec). No external repository source, README, issue, or docs tree was consulted.
