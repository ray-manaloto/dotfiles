# Follow-up: codex-plugin-cc Two-Agent Wiring, "Fable-5 prompt on Opus 4.8" Articles, and In-Claude-Code Multi-Model Trends

**Date:** 2026-07-19
**Scope:** Three concrete questions the prior two reports did **not** cover:
(1) exactly how `openai/codex-plugin-cc` wires Codex as a second agent inside
Claude Code, and how that compares to the plain `codex exec` shell-out;
(2) the specific articles Ray referenced about extracting Fable 5's system
prompt and running it on an Opus 4.8 agent — honest assessment;
(3) last-month (2026-06/07) trends for multi-model orchestration **inside Claude
Code specifically** (plugins that add non-Claude models as agents/workers).

**Builds on, does not repeat:**
- `followup-orchestrator-trends.md` — the `fable-orchestrator` architecture,
  five-part spec contract, deny-hooks, `STATUS:`+watchdog completion contract,
  structured reports, self-repair-against-the-gate, and the Fugu/RouteLLM/GraphRAG
  trend survey. **Assumed read; I reference its mechanisms, not restate them.**
- `followup-fable-opus-orchestrator.md` — the two wiring seams (A = Claude-only
  SDK `model` override; B = Bash shell-out for non-Claude), the honest read of the
  ~120k-char leaked *product* prompt vs the public "Prompting Claude Fable 5" doc,
  and the worker-guardrail stack. **Assumed read.** This report adds the *specific
  plugin/article evidence* those two summarized abstractly.

**Citation discipline** (`verify-before-advancing.md`, `probes-need-a-control-arm.md`):
plugin source / repo files / vendor docs are marked plainly; blog/newsletter/tweet
claims are **[secondary]** or **[informal]**; author-reported numbers carry that
label and their condition. Where a claim is load-bearing I traced it to the repo's
own README/DeepWiki; where I could not verify (one 429), I say so.

---

## 1. `openai/codex-plugin-cc` — the concrete two-agent wiring, and how it differs from `codex exec`

**Read from:** the repo README (raw.githubusercontent.com), the GitHub repo tree,
the DeepWiki architecture page, and the David Paluy LinkedIn article. Official
OpenAI repo; tagline *"Use Codex from Claude Code to review code or delegate tasks."*

### 1.1 The mechanism — NOT plain `codex exec`; a persistent app-server broker + slash commands + a Stop hook

The prior report modelled the Codex lane as **Seam B: a one-shot `codex exec`
process per delegation** (`echo "$SPEC" | codex exec --full-auto --sandbox
workspace-write -`), the orchestrator reading stdout. `codex-plugin-cc` is a
**heavier, stateful** realization of the same "shell-out to the local Codex" idea,
with four moving parts (file names per DeepWiki):

- **Slash commands** are the user/orchestrator interface — `/codex:review`,
  `/codex:adversarial-review`, `/codex:rescue`, `/codex:transfer`, `/codex:status`,
  `/codex:result`, `/codex:cancel`, `/codex:setup`. There is **no MCP server** and
  **no `codex exec` per call**.
- **`codex-companion.mjs`** — "main entry point for all slash commands; parses
  arguments and routes to logic" (DeepWiki). A Node dispatcher.
- **`app-server-broker.mjs`** — the load-bearing difference: it *"manages a
  persistent session with the Codex app-server to avoid startup overhead"*
  (DeepWiki). Instead of cold-spawning `codex` per task, it keeps a **long-lived
  connection to Codex's internal app-server** (the same protocol `codex` uses
  under the hood), enabling bidirectional streaming. A `tsconfig.app-server.json`
  build step generates TypeScript types for that app-server API.
- **`state.mjs` → `state.json`** — "persists job IDs, status, and results";
  background jobs run under unique IDs, queried by `/codex:status` and
  `/codex:result`.

It uses the **global `codex` binary** and honours the user's existing
`~/.codex/config.toml` / `.codex/config.toml` (default model + reasoning effort);
per-call `--model` / `--effort` override.

### 1.2 Division of labor — Codex is BOTH executor AND peer reviewer

The plugin does not pick one role; it ships both, and Paluy's article frames the
default loop as **Claude = orchestrator, Codex = executor**:

- **Claude** owns *"repository orientation, architecture decisions, task
  decomposition, implementation planning, review of completed change"*
  [secondary — Paluy].
- **Codex-as-executor** — `/codex:rescue` hands a *bounded* task to Codex (via a
  `codex:codex-rescue` **subagent**): *"focused implementation tasks, debugging,
  failing-test fixes, refactors, multi-file edits."* Supports `--background`,
  `--wait`, `--resume`, `--fresh`, `--model`. The loop is *"plan → delegate bounded
  task → review → accept/revise/revert."*
- **Codex-as-reviewer** — `/codex:review` (read-only review of uncommitted changes
  or `--base <ref>`) and `/codex:adversarial-review` (steerable challenge review)
  are peer-review, a *second model's* eyes on Claude's work.
- **`/codex:transfer`** — creates a **persistent Codex thread from the current
  Claude session, preserving context/history**, and exports a `codex resume
  <session-id>` command. This is a full context handoff, not a stateless spec.
- **The "review gate" is a Claude Code Stop hook.** `/codex:setup
  --enable-review-gate` installs a **Stop hook** that runs *"a targeted Codex review
  based on Claude's response"* and **blocks until issues are addressed.** The README
  itself warns this *"can create a long-running Claude/Codex loop and may drain
  usage limits quickly"* — i.e. it is the auto-verifier-every-turn pattern, and it
  is explicitly unbounded unless you cap it.

Paluy's headline claim: *"at least 60% savings in Fable 5 token consumption"*
[informal — author-reported, no benchmark, single-author blog]. The mechanism he
credits is the same one both prior reports credit — *"let Claude understand the
work, let Codex execute a bounded piece, then let Claude decide whether to keep
it"* — role-partitioned tokens, not a measured study.

### 1.3 How it compares to the prior report's plain `codex exec` shell-out

| Axis | Plain `codex exec` (prior report, `fable-orchestrator` launcher) | `codex-plugin-cc` |
|---|---|---|
| Invocation | one-shot `codex exec --full-auto -` per delegation | warm **app-server broker**, persistent session |
| Cold-start cost | paid every call | paid once (broker stays warm) — wins at high delegation volume |
| Cross-vendor | **generic** — same launcher wraps Grok/Gemini/local CLIs | **Codex-only**, coupled to the Codex app-server protocol |
| Completion/hang safety | **you build it** — `STATUS:` contract, wall/stall watchdog, PID identity, incomplete-stamp (`run-grok-headless.sh`) | job-lifecycle via `state.json` + `/codex:cancel`; **no watchdog/`STATUS:` contract shown** — relies on the app-server |
| Auto-review | not built in (you add a hook) | **built-in Stop-hook review gate** (but self-warns it can loop/drain) |
| Context model | workers share **zero** orchestrator context (clean spec-contract) | `/codex:transfer` deliberately **shares full context** (coupled thread) |
| Install/maintenance | a shell script you own (zero-bash-thin-wrapper) | a Node/TS plugin + marketplace install; a stateful daemon to manage |
| Governance fit | matches our `ai-cli-invocation.md` + launcher discipline | a third-party plugin; opaque broker; harder to gate |

**Reusable-as-pattern (what to steal):**
1. **Warm broker to kill cold-start** — if our orchestrator fires many small
   delegations, a persistent worker process (vs `codex exec` per call) is a real
   latency/cost win. Adopt *only if* per-call cold-start is measured to dominate;
   otherwise it adds a stateful daemon for nothing.
2. **Background-job ledger (`state.json`)** — this is the prior report's external
   ledger + `metrics.jsonl`, productized: job IDs, status, results, `--background`
   + `/status`/`/result`/`/cancel`. Confirms the ledger pattern is the right shape.
3. **Stop-hook auto-review as an optional second-model gate** — a concrete
   instance of "cheap/other model verifies every turn." Adopt it **bounded**
   (retry cap, our `long-running-command-hangs.md`), because the plugin's own README
   proves the failure mode is an unbounded loop.

**Not worth copying for our design:** the Codex-only coupling and the
`/codex:transfer` full-context handoff. Our cost win depends on workers sharing
**zero** orchestrator context (the five-part spec contract); `transfer` is the
opposite trade (context fidelity over token thrift) and belongs to a different
use case (escalating a hard, context-heavy debugging session to Codex).

**Net:** `codex-plugin-cc` is the *official, ergonomic, stateful* cousin of the
prior report's launcher-wrapped `codex exec`. It proves the two-agent-inside-CC
pattern is mainstream and gives three cherry-pickable ideas (warm broker, job
ledger, Stop-hook gate) — but its Codex-only, plugin-coupled, watchdog-less shape
is **less general** than our launcher approach, which already carries the
hang/fake-success rails and works for every vendor.

---

## 2. "Get Fable 5's system prompt, run it on an Opus 4.8 agent" — the actual articles, honestly assessed

Ray's reference resolves to a small cluster of 2026-07 posts. The two most
on-point are opposite in quality, and the contrast **is** the finding.

### 2.1 linas.substack — "Unlock Claude Fable 5 Lite: Opus 4.8" (the literal "paste the leak" article)

**Method:** paste the **complete leaked ~1,585-line Fable 5 system prompt** into
Opus 4.8's system field (API, project instructions, or Claude Code) to make
*"Claude Fable 5 Lite."* Full prompt + setup gated behind a paywall.

**The author's own honest caveat is the headline:** what transfers is *"identity,
autonomy defaults, frontend-design instincts, tool-use posture, and response
style,"* with *"visible deltas on design generation, agentic coding, structured
analysis, and long-context work"* — **but** *"on benchmarks that test raw model
intelligence, it is actually zero."* Evidence offered is a single *"public
head-to-head demonstration"* on a landing-page brief where *"the two outputs
looked like products from different companies"* — a design/style delta, no metrics
[secondary/informal — single author, paywalled, one demo].

**Assessment (confirms the prior report exactly):** this is the **leaked *product*
harness prompt** — §2a of `followup-fable-opus-orchestrator.md`. It is not an
orchestrator mode. By the author's *own* admission it moves *style, identity, and
design instinct*, not reasoning or delegation reliability. Pasting all 1,585 lines
onto Opus 4.8 buys the "looks like Fable" surface at a **~30k-token permanent
context tax** of product-harness plumbing (artifacts, web-tool schemas, safety
postmortems) that is **irrelevant to orchestration** and risks the
`reasoning_extraction` refusal traps the official doc warns about. **Do not adopt
this.** It is the exact move the prior report flagged as a context tax, not a
capability — and the author, to his credit, half-says so.

### 2.2 dev.to/toffy — "Teach Opus and Sonnet to 'behave' like Fable 5" (the good one — codify *procedures*, not the prompt)

**Method (explicitly the opposite of 2.1):** *don't* copy Fable's prompt — reverse-
engineer *how it works* and codify that as discipline rules for weaker models.
Ships as an npm package (`ccteams`) of pre-built teams. Five axes:
1. **Pre-writing routine** — read repo context before deciding (*"Read `go.mod`
   before using a language feature"*).
2. **Failure-pattern catalogs** — symptom → wrong instinct → correct move.
3. **Decision gates** — e.g. *"Before launching goroutines: who cancels it, who
   waits, where does the error go?"*
4. **Verification sequences** — ordered commands (*"`go build`, then `go vet`,
   then `go test -race`"*).
5. **Learning loops** — absorb new failures as playbook entries after approval.

Its thesis, verbatim: *"The gap between Fable 5 and Opus/Sonnet is not
intelligence."* What transfers is *"discipline, sequencing, verification
procedures"*; what does **not** is *"noticing something is off when no checklist
applies."* No benchmarks — subjective *"bugs Opus used to miss are now getting
caught… closed most of the gap for routine work."* [secondary].

**Concrete pattern worth stealing — evidence labels on every claim:** reject a
worker's claim unless tagged **`VERIFIED` (ran it) / `REASONED` (read the code) /
`ASSUMED`**, plus *"state hypothesis before touching code; a fix without a
confirmed root cause is a guess."* This is **our own repo rules mechanized**
(`verify-before-advancing.md` "read the real rc, not a piped tail";
`probes-need-a-control-arm.md" "a redirect/parse-error is not a 'no'"). The
`VERIFIED/REASONED/ASSUMED` label is a genuinely good, cheap addition to a worker
report shape (drop it into the prior report's `GROK REPORT` / `VERIFY REPORT`).

### 2.3 imCorfitz gist — "Use Fable 5 as orchestrator, Opus + Codex to execute" (ties directly to our design)

A concrete, minimal instance of exactly our target architecture, and it uses
**both** wiring seams from the prior report simultaneously:
- **Fable 5** = orchestrator/tech-lead (the session model).
- **`deep-reasoner`** subagent pinned to **Opus** (`model:` frontmatter; tools
  Read/Grep/Glob/Bash) — *"reasoning-heavy phases, architecture, debugging,
  algorithm design."* **Seam A.**
- **`fast-worker`** subagent pinned to **Sonnet** — *"mechanical tasks,
  boilerplate, tests, formatting, simple edits."* **Seam A.**
- **Codex** = cross-vendor peer review via `/codex:rescue --background`
  (i.e. `codex-plugin-cc`, §1). **Seam B, productized.**

It is built from Claude Code's **native `/agents` wizard + `.claude/agents/*.md`
`model:` pins + CLAUDE.md routing doctrine** — no custom proxy, no LiteLLM. This
gist is the cleanest published confirmation of the prior report's "Seam A for cheap
*Claude* workers, Seam B for the non-Claude worker" split, and it independently
lands on `codex-plugin-cc` for the Codex lane.

**Bottom line for Q2:** the "Fable-5 prompt on Opus 4.8" genre splits cleanly.
The *paste-the-leak* version (2.1) is style-transfer of the **product** prompt —
its own author says raw-intelligence gain is **zero** — skip it. The *codify-the-
procedures* version (2.2) is the useful one, and it is really the same thing as the
prior report's **public "Prompting Claude Fable 5" doc patterns + our verify-gate**:
model-agnostic discipline rules, not a trained-capability transfer. Adopt the
*procedure patterns* (evidence labels, hypothesis-before-fix, ordered verification,
pre-read routine); do not adopt the *leaked prompt*.

---

## 3. Last-month trends (2026-06/07): multi-model orchestration **inside Claude Code**

Distinct from the prior report's Fugu/RouteLLM/GraphRAG survey (those are *models*
and *general* routing). These are all *inside the Claude Code harness*, adding
**non-Claude** models as agents/workers. The load-bearing signal: **a whole
"`*-plugin-cc`" bridge family standardized this quarter around one shape** —
slash commands + a `<vendor>:*-rescue` subagent + shell-out to the vendor CLI +
an optional review-gate hook.

**A. The `*-plugin-cc` bridge family (the dominant pattern).**
- **`openai/codex-plugin-cc`** — §1; the reference implementation, official OpenAI,
  ~1.5k+ stars in days [secondary — CoddyKit, AIToolly coverage].
- **`abiswas97/gemini-plugin-cc`** — verified from its README: *"Based on
  `openai/codex-plugin-cc`, adapted for the Gemini CLI."* Same six-command shape
  (`/gemini:review`, `/gemini:adversarial-review`, `/gemini:rescue`,
  `/gemini:task`, status/result/cancel, `/gemini:setup`), a **`gemini:gemini-rescue`
  subagent**, shell-out to the Gemini CLI, and the same review-gate toggle. It is a
  literal fork of the Codex plugin for a different vendor — proof the pattern is now
  a template.
- **`sakibsadmanshajib/gemini-plugin-cc`** — a variant wiring Gemini via **ACP
  (Agent Client Protocol)** rather than a bespoke broker [secondary — search
  result; not deep-read]. ACP is the emerging standardized agent-to-agent wire, a
  cleaner substrate than each plugin hand-rolling a broker.
- **`m-ghalib/gemini-plugin-cc`** — review + adversarial-review only.
- **Caveat (flag, don't rely):** one search snippet claims Google retires the free
  **Gemini CLI on 2026-06-18** in favour of an **Antigravity CLI (`agy`)**, which
  would break Gemini-CLI-based bridges [informal — unverified; `abiswas97`'s README
  makes **no** mention of it and treats Gemini CLI as current]. Today is 2026-07-19,
  *past* that alleged date, and the plugins still ship — so treat the retirement
  claim as **unconfirmed**. It is a shelf-life *risk* to note, not a fact to cite.

**B. Two-agent peer-review plugins (Claude writes, other model reviews).**
- **`jcputney/agent-peer-review`** (v2.1.0, updated **2026-06-03**, 34★) — verified:
  a **symmetric** peer-review plugin. Round 0: *"Claude and Codex independently
  review the same scope with the same prompt; neither sees the other's findings"*;
  issues canonicalized by **content hash** (duplicates collapse to high-confidence
  flags); rounds 1+ run a **per-issue deterministic state machine** to debate to
  convergence **without an LLM judge**. Slash command `/codex-peer-review`
  (`--base`, `--uncommitted`); runs in a **subagent** so only the synthesized
  verdict returns to the main context; auto-trigger **hooks** remind Claude to
  dispatch review before presenting plans/architecture/refactors. This is the
  blind-independent-review-then-debate discipline our own `feedback_adversarial_
  review_convention` describes, packaged as a CC plugin.
- **Two-agent PR workflow** [secondary — salmanalibanani 2026-07-04]: Claude writes,
  Codex reviews the PR in **GitHub Actions**, *"one review pass, one fix pass, then
  merge"* — deliberately bounded to avoid an endless loop (the same bound
  `codex-plugin-cc`'s review-gate lacks by default).

**C. Whole-harness routers (the session-wide, all-or-nothing seam).**
- **Claude Code Router (`@musistudio/claude-code-router`, `ccr`)** [secondary —
  morphllm guide; direct fetch 429'd, characterized from search + guide]: an
  OpenAI-compatible **proxy** — launch `ccr code` instead of `claude`; it rewrites
  requests to any provider and **routes by request *category*** (`default`,
  `background`, `think`, `longContext`, `webSearch`). This is the prior report's
  `ANTHROPIC_BASE_URL`→LiteLLM seam, productized. The one refinement worth noting:
  because it can route the **`background`** class to a cheap model while `default`
  stays frontier, it is *slightly* more granular than "all-or-nothing" — but it
  routes by **request type, not by named subagent to arbitrary providers**, and the
  orchestrator itself runs through the proxy (not a native Anthropic key). It still
  **cannot** express "native strong Claude orchestrator + cheap non-Claude worker
  per-agent" the way Seam A + Seam B can.
- **Free-model playbooks** [informal — agentconn 2026]: pointing Claude Code + Codex
  at OpenRouter/OmniRoute free tiers via the same proxy trick.

**D. Anthropic's own native multi-agent (all-Claude, for contrast).**
- Native `/code-review` + the `anthropics/claude-code` `code-review` plugin: *"a
  fleet of specialized agents examine the diff in parallel, each looking for a
  different class of issue, then a verification step checks candidates against
  actual behavior to filter false positives"* [secondary — The New Stack, InfoQ,
  Anthropic docs]. Same fan-out-then-verify shape as the cross-vendor plugins, but
  single-vendor — useful as the "Seam A only" baseline.

**Net trend for the quarter:** the *inside-Claude-Code* ecosystem converged on one
template — **slash command + `<vendor>:rescue` subagent + shell-out to the vendor
CLI + optional review-gate hook** — and forked it across Codex and Gemini within
weeks. Peer-review-as-a-plugin (blind independent review → deterministic debate)
emerged as the second stable shape. Whole-harness routers (`ccr`) remain the
session-wide cheap-mode seam, unchanged in kind from the prior report. The
category the prior report saw productized as a *model* (Fugu) is, *inside the
harness*, being productized as a **plugin template**.

---

## 4. Concrete recommendation

**Q: codex-plugin-cc-style plugin vs raw shell-out vs LiteLLM proxy — which fits
our cost-optimized orchestrator?**

**Substrate = the prior report's launcher-wrapped shell-out (Seam B), not the
plugin, not the proxy** — for three repo-specific reasons:
1. **Cross-vendor generality.** Our design wants Codex *and* Grok *and* Gemini *and*
   local (Ollama/MLX) behind **one** contract. The `fable-orchestrator`
   `run-grok-headless.sh` launcher already does this and already carries the
   hang/fake-success rails (`STATUS:` + wall/stall watchdog + PID identity +
   incomplete-stamp) that `codex-plugin-cc` does **not** expose. A `*-plugin-cc`
   plugin is **Codex-only** (or Gemini-only) and hides its broker behind an opaque
   Node daemon we can't gate.
2. **Governance fit.** The launcher is a thin shell wrapper we own, matching
   `ai-cli-invocation.md` and our zero-bash-thin-wrapper discipline; a marketplace
   plugin with a stateful app-server is harder to pin, audit, and hook-guard.
3. **The LiteLLM/`ccr` proxy is the wrong tool for role-splitting.** It is
   session-wide (even `ccr`'s per-category routing runs the orchestrator through the
   proxy) and therefore **cannot** give "native strong Claude orchestrator + cheap
   non-Claude worker." Reserve it for a *fully-cheap, no-role-split* mode only.

**But cherry-pick three `codex-plugin-cc` ideas** as bounded add-ons to the
launcher substrate:
- a **warm worker process** (broker) *iff* measured per-call cold-start dominates;
- the **background-job ledger** (`state.json`-style) — it validates our external-
  ledger plan;
- an **optional Stop-hook auto-review gate**, **bounded with a retry cap** (the
  plugin's own README proves the unbounded version drains usage — exactly
  `long-running-command-hangs.md`).

Keep **cheap *Claude* workers on Seam A** (`.claude/agents/*.md` `model: haiku|
sonnet`) — the imCorfitz gist (§2.3) confirms this is the clean native path and
that the community independently lands on the **A-for-Claude / B-via-codex-plugin
split** the prior report recommended.

**If you want a turnkey today with zero build:** install `codex-plugin-cc` for the
Codex lane and use `agent-peer-review` for blind two-model review — both are the
`*-plugin-cc` template, work immediately, and match the gist. Accept their Codex-
coupling and unbounded-gate caveat as the price of not building. Migrate the lane
to the launcher substrate when you need Grok/Gemini/local behind the same contract.

**Q: which Fable-5 prompt patterns are worth adopting for our Opus-4.8/Fable-5
orchestrator?**

- **Reject the leaked 1,585-line product prompt** (linas "Fable 5 Lite"). By its
  own author's admission the raw-capability gain is **zero**; it transfers style/
  design-instinct at a ~30k-token tax and risks Fable's `reasoning_extraction`
  refusals. This is the harness prompt, not an orchestrator mode (prior report §2a,
  now confirmed by a concrete article).
- **Adopt the *procedure* patterns** (dev.to/toffy + the public "Prompting Claude
  Fable 5" doc from the prior report) — they are model-agnostic and map 1:1 onto
  our existing rules:
  - **`VERIFIED / REASONED / ASSUMED` evidence labels** on every worker claim —
    add to the prior report's `GROK REPORT`/`VERIFY REPORT` shapes; it is
    `verify-before-advancing.md` in one word per line.
  - **State the hypothesis before touching code** (*"a fix without a confirmed root
    cause is a guess"*) — twin of `probes-need-a-control-arm.md`.
  - **Ordered verification sequences** — ours is literally `mise run lint` →
    `pytest` → `dotfiles-setup verify run`; make the worker run them in order and
    report exit codes, not prose.
  - **Pre-read routine** (read the relevant context before deciding) and
    **failure-pattern catalogs** — cheap-worker discipline scaffolding, applied
    *thicker* for cheap workers than for a Fable worker (prior report §3's
    inverse-proportionality rule).
- These are **prompt/skill additions authored by us**, not a Fable secret; apply
  them to whichever Claude orchestrates and, in the *enumerated/thick* form, to
  every cheap worker. They buy Fable-*style* discipline, never Fable's *trained*
  long-horizon delegation — the choreography, not the stamina (prior report §2).

**Caveats carried forward:** Paluy's "60% savings", linas's design demo, and
toffy's "closed most of the gap" are all **author-reported, no benchmark** —
direction, not targets; re-measure on our own workloads
(`probes-need-a-control-arm.md`). The Gemini-CLI→Antigravity retirement is
**unconfirmed** — do not build a Gemini lane on the assumption it is permanent.
The architecture recommendation does not depend on any of these numbers; it depends
on two robust facts: the `*-plugin-cc` shape is Codex/vendor-coupled and watchdog-
less (so the launcher substrate is more general), and the leaked prompt transfers
style not reasoning (so adopt procedures, not the prompt).

---

## GitHub repos touched

- [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc) — read README (raw), repo tree, and DeepWiki architecture page for the app-server-broker + slash-command + Stop-hook review-gate wiring, background-job state, and division of labor (§1).
- [abiswas97/gemini-plugin-cc](https://github.com/abiswas97/gemini-plugin-cc) — read README; verified it is a literal fork of codex-plugin-cc for the Gemini CLI (`gemini:gemini-rescue` subagent, same command set) (§3A).
- [sakibsadmanshajib/gemini-plugin-cc](https://github.com/sakibsadmanshajib/gemini-plugin-cc) — referenced (search-level) as the ACP-based Gemini bridge variant (§3A); not deep-read.
- [m-ghalib/gemini-plugin-cc](https://github.com/m-ghalib/gemini-plugin-cc) — referenced as a review-only Gemini bridge (§3A); not deep-read.
- [jcputney/agent-peer-review](https://github.com/jcputney/agent-peer-review) — read README; verified the blind-independent-review + content-hash + deterministic-debate peer-review plugin using the Codex CLI (§3B).
- [musistudio/claude-code-router](https://github.com/musistudio/claude-code-router) — referenced (direct fetch 429'd; characterized via morphllm guide + search) as the session-wide `ccr` proxy with per-request-category routing (§3C).
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — referenced for the native `code-review` multi-agent plugin as the all-Claude baseline (§3D); not deep-read.
- [BuildContext/fable-orchestrator](https://github.com/BuildContext/fable-orchestrator) — referenced (not re-read) for the `run-grok-headless.sh` launcher / `STATUS:`-contract / watchdog mechanisms compared against codex-plugin-cc (§1.3), carried from the prior two reports.

_Non-GitHub primary/secondary sources: David Paluy, "Run Codex Inside Claude Code: A Practical Two-Agent Coding" (LinkedIn); linas.substack "Unlock Claude Fable 5 Lite: Opus 4.8"; dev.to/toffy "Want to keep using Fable 5? Teach Opus and Sonnet to 'behave' like it" (ships as npm `ccteams`); gist.github.com/imCorfitz "Use Fable 5 as orchestrator and Opus + Codex to execute"; DeepWiki openai/codex-plugin-cc; morphllm.com Claude Code Router guide; salmanalibanani.com two-agent PR workflow; The New Stack / InfoQ on Anthropic's native multi-agent review. All blog/tweet/newsletter claims labelled [secondary]/[informal] inline; the Gemini-CLI→Antigravity retirement is explicitly unconfirmed._
