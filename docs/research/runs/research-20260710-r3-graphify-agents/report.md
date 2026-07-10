# Graphify + per-tool subagent pilot — domain synthesis

Run: `research-20260710-r3-graphify-agents` · Domain: graphify usefulness +
per-tool specialized subagents to cut token/context as the research corpus
grows. Synthesizes three angle reports (`pilot-agents.md`, `graphify-corpus.md`,
`measure-expand.md`), grounded on r2 Run G's KB architecture
(`.omc/research/research-20260709-r2-knowledge-base/report.md`), and filtered
through a 3-vote adversarial verification pass on the 8 load-bearing claims.
Written 2026-07-10.

---

## Executive summary — the recommendation

**Build the subagent pilot now; keep graphify's seed as a separate, lower-priority,
Mac-only experiment. They are two independent bets and the subagent bet is the
cheaper, surer win.**

1. **Build two read-only "librarian" subagents first — `mise-librarian` and
   `docker-family-librarian`** — as `.claude/agents/*.md` files with
   `tools: Read, Grep, Glob` (no Write/Edit/Bash), `model: haiku`, and a system
   prompt that names an explicit, prioritized corpus file list (mintlify cache →
   repo research reports → live repo config) plus a hard ~700-token response cap.
   These two have the deepest existing research corpus to compress, so they give
   the cheapest *real* (non-synthetic) query for measuring savings. Add a third,
   `hk-librarian`, only as a "+1" if the first two clear the bar.

2. **The token-savings mechanism is real and free.** Subagent context isolation
   is automatic and primary-source-confirmed: a subagent greps/reads its corpus
   in *its own* context window; only its final ~summary (plus a small metadata
   trailer) returns to the main conversation. Anthropic's own worked example is
   6,100 tokens read → 420 tokens returned. This is a mechanism that exists today
   with zero new tooling — that is why the subagent pilot is the surer bet.

3. **Measure before expanding.** Run each pilot query in two arms (baseline: main
   loop greps/reads the raw corpus itself; subagent: delegate to the librarian),
   in fresh `/clear`ed sessions, and compare **main-loop context growth** (not
   total system tokens — those are roughly conserved). Instrument with the free
   `count_tokens` API (deterministic cross-check), `/context` + `/usage`
   (per-subagent attribution, Pro/Max/Team/Enterprise only), and JSONL transcript
   parsing (`isSidechain` filtering). Pair every token number with a
   **gold-key-facts coverage check** so a subagent can't "win" by dropping
   information. Proposed GO bar: median main-loop token ratio ≤ **0.35** (≥65%
   reduction) AND subagent coverage ≥ baseline coverage on every query. The 0.35
   figure is a judgment call to falsify, not a literature number — confirm with
   Ray first.

4. **Graphify: yes it is genuinely useful, but keep it in its Run G box.** The
   brief's "is graphify even useful?" challenge resolves to: it *is* a real
   queryable KB (deterministic BFS/DFS, ~2000-token query budget, zero LLM at
   query — CONFIRMED 3/3), but its *build* over an all-prose corpus is 100%
   LLM-priced, so it belongs as a **gated, Mac-only, periodic synthesis layer**,
   never wired into the subagents' hot query path. Seed it with
   `graphify extract . --backend claude-cli --update` (first run omits `--update`)
   and a root `.graphifyignore` excluding `docs/research/mintlify-cache/`. The
   librarian subagents grep the committed corpus directly; a future
   `GRAPH_REPORT.md`, if the graphify pilot pays off, is added as one more corpus
   file, not a live MCP/CLI dependency.

5. **One loud caveat (see Contradictions):** the "user-approved" label the brief
   and the r3 reports attach to the graphify pilot is **not backed by a located
   approval record**, and the repo's own plan
   (`.omc/plans/plan-20260710-r2-implementation.md:220-223`) lists "graphify
   cadence" as a still-open **P2** question. The *subagent* pilot is low-risk and
   reversible enough to start regardless; the *graphify* seed/cadence should get
   an explicit Ray sign-off before spending build-time LLM tokens.

**Bottom line: start the subagent pilot (mise + docker-family) this week — it is
reversible, needs no new tools, and its savings mechanism is doc-confirmed. Treat
graphify seeding as a parallel, gated, Ray-approved experiment, not a dependency
of the subagent work.**

---

## Q1 — Is graphify actually useful, or is the subagent pattern the better lever?

**Both are useful, for different jobs, and they do not compete.** The brief's
framing ("challenged whether graphify is useful") collapses two separate
mechanisms:

- **Subagent context isolation** is the *retrieval-time* lever. It is free,
  automatic, and needs no new tooling. Primary source
  (`code.claude.com/docs/en/sub-agents.md`, fetched 2026-07-10): "the subagent
  does that work in its own context and returns only the summary." The companion
  `context-window.md` gives the mechanistic worked example — a subagent reads
  6,100 tokens of files, returns a 420-token summary, "That's the context
  savings" — the literal numeric field the doc's own visualization renders
  (`measure-expand.md:346-357`, verified 3/3). This is the mechanism the pilot
  exists to exploit and measure.

- **Graphify** is a *synthesis-time* lever. It answers a query shape grep can't:
  "what connects / what recurs across all our research runs?" It is a real
  queryable KB — `graphify/serve.py` @ v8 loads a NetworkX graph and answers via
  deterministic trigram-indexed BFS/DFS with **no LLM client imported in the
  query path** and a `token_budget` default of 2000 confirmed in the MCP tool's
  own JSON schema (`graphify-corpus.md:247-268`; Run G Q1; verified 3/3). But its
  *build* over a 100%-prose corpus routes every file through the LLM semantic
  pass (Run G Q1), so it carries a real, per-run token cost.

The correct read: **subagents are the primary token lever and the thing to pilot
first; graphify is a complementary periodic layer, gated behind its own separate
go/no-go.** They are explicitly not to be conflated (`measure-expand.md:304-315`).

## Q2 — Which 2-3 subagents first, and what does each read?

**Selection criterion: corpus depth already on disk + query re-derivation
frequency, not "most complex tool"** (`pilot-agents.md:47-59`). Ranked:

| Candidate | Dedicated corpus already on disk | Rank |
|---|---|---|
| **mise** | Run D §1 release-mining, Run B topology, r3 `mise-dotfiles` (×3), r3 `mise-bootstrap` (×3), r3 `watchlist-releasenotes` — plus 4-5 config tiers to reason about | **1st** |
| **docker-family** | Run B topology report (~356-371 lines), `P2996-CACHE.md`, existing `dockerfile-reviewer.md`, docker-benchmarks | **2nd** |
| **hk** | Run D §2 only (`hk-pkl-pitchfork.md`) — no dedicated topology-scale report | **3rd / "+1"** |

The mise > docker-family > hk corpus-depth asymmetry is empirically real (Glob
over `.omc/research/research-20260709-r2-*/report.md` = 9 files; the r3 mise
angle-report directories all exist; no hk topology-scale report or r3 hk
directory exists). **Build mise + docker-family first; hk as "+1" only if the
first two show measurable savings** (verified CONFIRMED — but see the Refuted /
unverified section: the *"measurable savings"* prediction is not yet empirically
evidenced, only the corpus-depth proxy is).

**mise-librarian corpus** (priority order, `pilot-agents.md:74-107`):
1. `docs/research/mintlify-cache/jdx/mise/{llms.txt,llms-full.txt}` — with an
   explicit staleness caveat (see Q4).
2. `.omc/research/research-20260709-r2-release-mining/report.md` §1 (mise) +
   Retire/Adopt/Watch table.
3. `.omc/research/research-20260709-r2-topology/report.md` (Run B).
4. `docs/research/runs/research-20260710-r3-mise-{dotfiles,bootstrap,watchlist-releasenotes}/agents/*.md`.
5. Live repo config (`mise.toml`, `.config/mise/conf.d/shared.toml`,
   `.devcontainer/mise-{system,runtime}.toml`, `mise.lock`) for current pins.
6. `.claude/rules/tool-currency-and-native-first.md`, `use-tool-builtins.md`.
   - Pilot query: *"Has the mise base-tier core/cpp split landed yet, and what
     three things must ship in the same PR if it does?"*

**docker-family-librarian corpus** (`pilot-agents.md:116-142`):
`.omc/research/research-20260709-r2-topology/report.md` (Run B, full);
`P2996-CACHE.md`, `docker-bake.hcl`, `.devcontainer/{Dockerfile,AGENTS.md}`;
`docs/research/mintlify-cache/devcontainers/{cli,spec,features,images}/`;
`dockerfile-reviewer.md` (complementary — it reviews diffs, the librarian answers
"what does the corpus say about topology X"); docker-benchmarks (surface the
staleness caveat); `.github/workflows/{AGENTS.md,build-publish.yml}`.
   - Pilot query: *"Why was a lean `:ci` image rejected for CI, and what's the
     actual measured pull-time number the rejection rests on?"*

**hk-librarian corpus** (the "+1", `pilot-agents.md:151-168`):
`docs/research/mintlify-cache/jdx/{hk,pklr,pitchfork}/`; Run D §2;
`hk.pkl`/`hk-common.pkl`/`hk-image.pkl`;
`.claude/rules/{long-running-command-hangs,ci-local-parity}.md`;
`python/src/dotfiles_setup/lint.py`.
   - Pilot query: *"Does hk support per-step or per-run timeouts natively yet,
     and if not, what wraps it?"* — a single-fact lookup (hk pinned at 1.50.0 in
     `.config/mise/conf.d/shared.toml:26`; no native timeout through 1.50.0 —
     verified 3/3 against live CHANGELOG + pkl schema).

## Q3 — The subagent definition shape

Each subagent is a `.claude/agents/*.md` file (skills/agents live under
`.claude/`, never `.omc/`, per `omc-directory-conventions.md`). Confirmed
mechanics from `code.claude.com/docs/en/sub-agents.md` (fetched 2026-07-10,
verified 3/3): only `name` and `description` are required; `tools` and `model`
are optional; the Tips block says "Limit tool access: grant only necessary
permissions for security and focus" and "Design focused subagents: each should
excel at one specific task."

Concrete template (`pilot-agents.md:185-219`):

```markdown
---
name: mise-librarian
description: Answers questions about mise (jdx/mise) config, release history,
  and this repo's mise tooling decisions by reading the mintlify doc cache and
  the repo's mise-focused research reports. Use when a question is about mise
  CLI behavior, mise.toml semantics, the repo's mise tool tiers, or "does mise
  do X natively now."
tools: Read, Grep, Glob
model: haiku
---

You are a read-only research librarian for mise (jdx/mise) in this repo.
Answer ONLY from: [prioritized corpus file list, per Q2].
Grep before you Read a whole file. If none of the above answers the question,
say so explicitly and name the mintlify llms.txt page to fetch next — do not guess.
Return format (hard constraint): 3-8 sentences or a short bullet list, each
claim followed by its file:line or URL citation. Never paste raw corpus content
longer than one sentence. Target under ~500 words / ~700 tokens total. If the
honest answer needs more, say what's missing and stop rather than dumping source.
```

Design choices, each source-justified:
- **`tools: Read, Grep, Glob` only.** Doc best-practice ("limit tool access"); a
  read-only librarian never writes; omitting `Bash` also sidesteps this session's
  own broken-PreToolUse-hook failure mode by construction.
- **`model: haiku`.** Matches `.claude/CLAUDE.md` `<model_routing>` ("haiku =
  quick lookups"). Grep-then-cite is a quick lookup, not architecture. *Caveat:*
  whether haiku reliably honors a prompted ~700-token cap is unverified —
  escalating to `model: sonnet` is a one-line change if the pilot shows it
  blowing past.
- **No `mcpServers` field, no live-fetch-by-default.** Directly implements Run G's
  Layer-1/Layer-2 split — the subagent operates over committed markdown + the
  mintlify cache, escalating to a live `mise.jdx.dev/<page>.md` fetch only as an
  explicit last resort. It never touches graphify's MCP server or CLI.
- **Deliberate deviation from `dockerfile-reviewer.md`.** That existing agent has
  only `name`/`description` frontmatter and embeds *static* project knowledge — a
  fine shape for a small stable checklist (I confirmed its 12-item checklist
  form). A librarian over a corpus that grows every session needs the
  file-pointer shape instead: `Grep`/`Read` over a named, updatable list.

*Honest scoping note (from verification):* the doc confirms the *mechanics*
(only name/description required; limit tools). The specific prescriptions —
"prioritized corpus file list", "hard response-size cap", "haiku over sonnet" —
are this design's own recommendations layered on the doc-confirmed mechanics, not
patterns the docs themselves attest. They are sound design choices, not documented
defaults; the pilot measurement is what validates them.

## Q4 — The mintlify cache is stale; the prompt must say so

The cache each librarian relies on was last refreshed **2026-04-07**
(`docs/research/mintlify-cache/README.md:89`), while mise shipped ~10 releases
between v2026.6.11 (2026-06-16) and v2026.7.5 (2026-07-09) — a 2-3 month gap,
verified live against `github.com/jdx/mise/releases` (CONFIRMED 3/3). So the
mise/hk librarian prompts **must name the cache's staleness explicitly and fall
back to a live per-page `.md` fetch** rather than treat the cache as current
(e.g. the cache has zero hits for "timeout" despite it being a real, answerable
question). This means some pilot queries will correctly land as "not in cache,
here's the live page to check" rather than a clean zero-network answer — that is
honest gap-reporting (a feature), but it means not every query is a pure
low-token win.

## Q5 — How the pilot is measured, and when to expand

**Compare main-loop context growth, not total system tokens** (the corpus gets
read by *somebody* either way — the scarce compounding resource is the main
conversation) (`measure-expand.md:36-67`).

Three instruments, in order of rigor (`measure-expand.md:68-130`):
1. **`count_tokens` API** — deterministic, free (rate-limited only), model-pinned.
   Feed it the literal baseline corpus files, and separately the subagent's
   returned text. Caveat: newer-tokenizer models produce ~30% more tokens —
   count with the *actual* model the subagent uses. Needs Ray's key/subscription
   (repo provisions no `ANTHROPIC_API_KEY`) — an open dependency, not a blocker.
2. **`/context` + `/usage`** — free, in-session; `/usage` attributes usage to
   subagents/skills/MCP servers as a % of total on Pro/Max/Team/Enterprise. Live
   snapshot; capture manually right after each arm.
3. **JSONL transcript parsing** (`~/.claude/projects/.../<session>.jsonl`) — the
   only scriptable instrument (`mise run pilot-measure`, logic in `python/`). Sum
   `input+output+cache_creation` tokens over `isSidechain:false` turns only.
   Caveats: `isSidechain` is confirmed from third-party reverse-engineering, not
   primary docs — verify empirically first; and `claude-code#27361` reports
   occasionally-missing `message_stop` events — which is why instrument 1 is the
   cross-check of record.

**Protocol per query** (`measure-expand.md:186-219`): write the gold-key-facts
list from the source report lines *before* running either arm; `/clear` → baseline
arm (main loop greps/reads named files, answers) → capture; `/clear` → subagent
arm (delegate, record only what returns) → capture (JSONL excludes
`isSidechain:true`; cross-check returned text with `count_tokens`); compute
per-query ratio + coverage delta. Run ≥3 queries per agent (single query = cherry-
pick risk).

**GO bar** (`measure-expand.md:222-276`): median main-loop token ratio ≤ **0.35**
(≥65% reduction) AND subagent coverage ≥ baseline coverage on *every* query. The
0.35 is deliberately less aggressive than mcp2cli's proven 96-99% schema-discovery
reduction and graphify's code-enforced 2000-token budget, because a subagent's
~700-token cap is *prompted, not enforced*. It is a judgment call to falsify —
**confirm with Ray before the pilot runs.** Correctness pairing is mandatory:
three independent sources (graphify's own coverage-formula benchmark, arXiv
2605.15184 "Is Grep All You Need?", arXiv 2602.23368 Amazon Science) all pair a
token/cost metric with a graded-correctness metric.

**Expansion, staged (never batch)** (`measure-expand.md:278-315`): Stage 0 = mise
+ docker-family must both clear the bar → Stage 1 = build hk-librarian, same
protocol (its thinner corpus is exactly the variable this stage tests) → Stage 2 =
the remaining 6 (chezmoi, python, uv/ruff/ty, doppler, renovate, devcontainer) as
*independent* per-agent go/no-go decisions. Expect some Stage-2 NO-GOs simply
because their corpus is too thin yet (e.g. doppler) — a "not yet — corpus too
thin" no-go is informative, not a failure of the pattern. A **routing gate**
(ambiguous cross-domain queries with no explicit `@agent` — does auto-delegation
pick the right librarian?) is informational for the 2-3 pilot but *blocking* for
9-agent expansion, since misrouting risk compounds with agent count.

## Q6 — Graphify seed design (the parallel, gated experiment)

Per Run G's user-noted architecture, graphify stays **Mac-only, periodic, gated,
never in the hot query path** (`.omc/research/research-20260709-r2-knowledge-base/report.md:343-345`:
"Do not wire graphify's MCP server or CLI into the hot day-to-day retrieval path
regardless of pilot outcome"). The `/graphify` skill is user-level on Ray's Mac,
absent in the remote container — so the seed/build step can only run on the Mac;
this container reads committed `docs/research/graph/*` via plain Read/Grep.

- **Build command:** `graphify extract . --backend claude-cli --update` (first run
  omits `--update`). `--backend claude-cli` uses the host agent, no API key —
  matching the repo's deliberate absence of `ANTHROPIC_API_KEY`. Verified 3/3
  (each flag documented separately at README @ v8; the exact 3-flag string is a
  reasonable synthesis, not a verbatim README line).
- **Scope control:** root `.graphifyignore` (gitignore syntax, merged with
  `.gitignore`) entry `docs/research/mintlify-cache/` — excludes ~75k lines of
  third-party docs from the LLM semantic pass for zero synthesis value (Run G
  Layer 2).
- **Committed output:** `docs/research/graph/{graph.json, GRAPH_REPORT.md,
  graph.html, cost.json}`. Git-safe (relative re-anchored paths). **Correction to
  Run G:** the union-merge driver is wired by running `graphify hook install`
  (which also installs a post-commit AST-only rebuild hook), not by hand-authoring
  `.gitattributes` — and that post-commit hook should be opt-in only, consistent
  with a Mac-only human-gated pilot (`graphify-corpus.md:147-196`).
- **Cost risk:** graphify issue #730 reports a "truncation cascade" (~3× cost
  overhead, $1.50→$4.31) on a 1,094-file dense-markdown corpus from a hardcoded
  `max_tokens=8192`. Today's corpus (~60 files ex-cache) is ~5% of that trigger
  size — low-risk now, but check `cost.json` before scaling ingest scope, and
  re-confirm #730's fix status before the build (`graphify-corpus.md:120-145`).
- **Query pattern (if piloted):** CLI fast-path (`graphify query "..."`) against
  the committed `graph.json` first; `mcp2cli --mcp-stdio` spawn second for
  structured tool output — never a registered server, satisfying the
  no-registration constraint by construction. A future `GRAPH_REPORT.md` is added
  to a librarian's corpus list as one more grep-equivalent file, not a live
  dependency — the subagent shape does not change (`pilot-agents.md:234-245`).
- **Version caveat:** graphify is pre-1.0, near-daily releases (~81k stars, repo
  now at `Graphify-Labs/graphify`, redirected from `safishamsi/graphify`). Re-pin
  the exact version at build time; any version number in a research artifact is
  stale within days.

---

## Refuted / unverified claims

The adversarial pass returned **CONFIRMED on all 8** load-bearing claims, so none
are refuted outright. But three carry dissent/scoping notes that must not be
asserted more strongly than the evidence supports:

1. **"mise+docker first, hk as +1 will show *measurable token savings*" — the
   predictive half is UNVERIFIED.** The corpus-depth *proxy* (mise > docker-family
   > hk research volume) is empirically solid (verified via Glob; Run B topology
   report is ~356-371 lines; the r3 mise directories exist; no hk topology report
   exists). But the *causal* claim — that building mise+docker first will yield
   measurable savings hk wouldn't — has **zero primary evidence**; the source
   report's own Uncertainties section states "No empirical token-count evidence
   yet... the actual before/after token deltas... are the sibling measurement
   angle's job, not verified here," and calls the hk-as-+1 framing "this report's
   own recommendation, not something independently re-derived." Treat the build
   order as a well-grounded prior; treat "measurable savings" as the hypothesis
   the pilot exists to test.

2. **"The subagent system prompt should name a prioritized corpus file list + a
   hard response-size cap, and use `model: haiku`" — mechanics confirmed,
   prescriptions are design choices, not documented patterns.** The doc confirms
   "only name and description required" and "limit tool access", and
   `dockerfile-reviewer.md` is confirmed as the only existing agent with a static
   embedded prompt. But the docs do **not** attest a "corpus file list" system-
   prompt pattern, a "response-size cap" convention, or `haiku` as a recommended
   default over `sonnet`/`inherit`. These are sound, source-*compatible* design
   recommendations — not primary-source-mandated features. The synthesis presents
   them as recommendations, which is the correct altitude.

3. **"Per the *user-approved* Run G architecture, graphify stays gated / out of
   the hot path" — the architecture is confirmed; the "user-approved" provenance
   is NOT.** The technical substance is verbatim-accurate (Run G report.md:343-345;
   `pilot-agents.md:234-245` implements it with no `mcpServers` field). But the
   "user-approved" qualifier has no located primary evidence: Run G frames the
   decision as the *research's own recommendation*, and the only documents
   asserting "user-approved" are sibling r3 agent reports circularly citing the
   same Run-G lines. The most authoritative subsequent artifact —
   `.omc/plans/plan-20260710-r2-implementation.md:220-223` — lists "graphify
   cadence" under **P2 open questions still pending Ray's decision**. See
   Contradictions in the structured output. (The *substantive* architectural claim
   — gate graphify, keep it out of the hot path — stands on its own technical
   merits regardless of provenance.)

Everything else — subagent context isolation is free/automatic (3/3), mintlify
cache is 2-3 months stale (3/3), hk pinned 1.50.0 with no native timeout (3/3),
graphify build command + `.graphifyignore` (3/3), Run G's graphify-is-a-real-KB
conclusion (3/3) — is CONFIRMED against re-fetched primary sources.

## Open questions for Ray (with recommended answers)

1. **Approve the graphify seed/cadence explicitly?** The repo plan lists it as a
   still-open P2. *Recommended: give an explicit yes/no on the seed run and its
   cadence (monthly or on-demand, not per-run) before any build-time LLM tokens
   are spent — and decouple it from the subagent pilot, which needs no approval to
   start being low-risk and reversible.*
2. **Confirm the 0.35 token-ratio GO bar?** It's a judgment call, not a literature
   number. *Recommended: accept 0.35 as the starting bar to falsify; adjust after
   the first real measurement rather than debating it in the abstract.*
3. **Which token-measurement instrument is authoritative for your account?**
   `/usage` per-subagent attribution needs Pro/Max/Team/Enterprise; `count_tokens`
   needs your key/subscription. *Recommended: use `count_tokens` as the deterministic
   cross-check (it's free) and `/usage` if your tier supports it; fall back to JSONL
   parsing otherwise.*
4. **Build mise + docker-family together, or mise alone first?** *Recommended:
   both together — they share the identical template and the measurement protocol
   is per-agent anyway, so you get two data points for the same setup cost.*
5. **Corpus boundary** (carried from Run G): promote durable run outputs to
   `docs/research/runs/<slug>/` while `.omc/research/` stays per-clone? *Recommended:
   yes — this run already lives under `docs/research/runs/`, and it's the only way a
   fresh clone's librarian can index the full corpus.*

---

## GitHub repos touched

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — subject of the graphify usefulness/seed question: `serve.py` (query path, 2000-token budget, no-LLM-import), README @ v8 (extract flags, `.graphifyignore`, storage/git-safety), `BENCHMARKS.md` (coverage-formula methodology), `graphify hook install` merge-driver mechanics.
- [safishamsi/graphify](https://github.com/safishamsi/graphify) — same project, pre-org-rename path; issue #730 (truncation-cascade cost overrun on a dense markdown corpus).
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — official subagent docs (`sub-agents.md`, `context-window.md`, `costs.md`) for context-isolation mechanics, frontmatter fields, the 6,100→420-token worked example, `/context`/`/usage` instrumentation; issue #27361 (JSONL `message_stop` reliability caveat).
- [jdx/mise](https://github.com/jdx/mise) — mintlify-cached docs proposed as the mise librarian corpus; live `github.com/jdx/mise/releases` fetch confirming v2026.6.11→v2026.7.5 cadence and the ~3-month cache-staleness gap.
- [jdx/hk](https://github.com/jdx/hk) — mintlify-cached docs for the hk librarian; live CHANGELOG/releases confirming v1.50.0 (2026-07-06) with no native timeout; pkl `Config.pkl` schema confirming no timeout field.
- [jdx/pklr](https://github.com/jdx/pklr) — mintlify-cached docs, hk librarian adjacent-ecosystem corpus.
- [jdx/pitchfork](https://github.com/jdx/pitchfork) — mintlify-cached docs, hk librarian adjacent-ecosystem corpus.
- [devcontainers/cli](https://github.com/devcontainers/cli) — mintlify-cached docs, part of the docker-family librarian corpus (spec/features/images caches likewise).
- [knowsuchagency/mcp2cli](https://github.com/knowsuchagency/mcp2cli) — mintlify-cached docs; `--mcp-stdio` stdio-spawn pattern for graphify's MCP server; 96-99% schema-discovery reduction as a savings-ratio calibration point.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo: Run G KB report, r2 inventory/topology/release-mining reports, r3 sibling angle reports, `.claude/agents/dockerfile-reviewer.md`, `.claude/rules/*`, `.config/mise/conf.d/shared.toml` (hk pin), `docs/research/mintlify-cache/README.md` (refresh date), `.omc/plans/plan-20260710-r2-implementation.md` (graphify-cadence open-question).

Secondary sources (not GitHub-owned):
- [arXiv:2605.15184](https://arxiv.org/abs/2605.15184) — "Is Grep All You Need?" — grep-vs-vector correctness+harness methodology precedent.
- [arXiv:2602.23368](https://arxiv.org/abs/2602.23368) — "Keyword search is all you need" (Amazon Science) — "percentage of baseline quality retained" framing.
- `platform.claude.com/docs/en/build-with-claude/token-counting` — `count_tokens` API (free, rate-limited; ~30% newer-tokenizer caveat).
