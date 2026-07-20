# Graphify GitHub Mining — Maintainer & Community Knowledge

**Repo:** [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) —
91.5k stars, created 2026-04-03, latest release **v0.9.20** (2026-07-18).
Discussions **enabled** (83 threads, active Q&A/Ideas/Announcements). Issue
tracker is extremely active (issues in the ~2050 range as of 2026-07-19),
release cadence is ~daily-to-weekly on the `0.9.x` line. PyPI package name is
**`graphifyy`** (double-y) — `graphify` alone is a different/unclaimed package
(the `pip install 'graphify[postgres]'` error in
[#1906](https://github.com/Graphify-Labs/graphify/issues/1906) points users at
the wrong name).

Maintainer voice = **@safishamsi** ("Safi", founder), with @TPAteeq,
@FolatheDuckofDuckingburg, @daveshenal answering community threads. Commercial
turn is live: **graphify.com + Graphify Enterprise early access**
([Disc #1798](https://github.com/Graphify-Labs/graphify/discussions/1798)), and
the project **joined Y Combinator S26**
([Disc #983](https://github.com/Graphify-Labs/graphify/discussions/983)). Open
source is stated to "stay free and local."

This is a **fast-churning pre-1.0 tool**: much of what is cited below as
"fixed" landed on the `v8` branch and shipped in a subsequent `0.9.x`. Pin a
version and re-verify before betting on any single behavior.

---

## 1. Backends / cost / local + free models

**Backend auto-detect priority chain** (from the maintainer, closing
[#1086](https://github.com/Graphify-Labs/graphify/issues/1086)):
`detect_backend()` picks **Gemini → Kimi → Claude → OpenAI → DeepSeek → Bedrock
→ Ollama**, by "whichever API key is set." Historically the Python API
`extract_files_direct()` **silently defaulted to `kimi` (Moonshot AI, a Chinese
endpoint `api.moonshot.ai`)** when called as a library — a data-residency
footgun. Fixed in commit `006e159`: it now calls `detect_backend()` and raises a
clear `ValueError` listing every env var if nothing is configured.

**First-class backends today:** Gemini, Kimi, Claude (API + `claude-cli`),
OpenAI, **DeepSeek** (`DEEPSEEK_API_KEY`, default `deepseek-v4-flash`,
`DEEPSEEK_BASE_URL` for OpenAI-compat endpoints — [#1422](https://github.com/Graphify-Labs/graphify/issues/1422)),
Bedrock, Ollama. No NIM/MLX backend surfaced in issues (MLX search returned
nothing — treat MLX as unsupported/unrequested).

**The "0 tokens for code" path is real and maintainer-endorsed.** AST/structural
extraction builds the graph with **zero LLM credits**; only doc/semantic
extraction needs a model. Key threads:
- [#1734](https://github.com/Graphify-Labs/graphify/issues/1734) (CLOSED) — added
  **`graphify extract . --code-only`**: indexes code via local AST, **no API key
  needed**, explicitly reports skipped non-code files. This is the recommended
  "no API key" path.
- [Disc #1931](https://github.com/Graphify-Labs/graphify/discussions/1931) —
  maintainer (@TPAteeq): *"Build the graph from your terminal, not chat:
  `graphify extract . --code-only`. Local AST parsing, no API key, nothing in
  your chat context."* Building via `/graphify .` **inside the agent chat burns
  tokens** — a common misuse.
- **`claude-cli` backend / subscription (no per-token API bill):** when no
  headless API key is set, `SKILL.md` Part B dispatches semantic extraction to
  **Claude Code Agent-tool subagents — "the host session itself is the LLM"**
  ([#1758](https://github.com/Graphify-Labs/graphify/issues/1758)). This uses
  your Claude subscription rather than a metered API key, but has a sharp edge
  (see Part 2 / Part 5). Setup help: [#749](https://github.com/Graphify-Labs/graphify/issues/749).

**Local models (Ollama / OpenAI-compatible):** heavily requested, partially
landed, with gotchas:
- [#959](https://github.com/Graphify-Labs/graphify/issues/959) (OPEN) — OpenAI
  backend base_url was hardcoded; **vLLM / local OpenAI-compat servers blocked**.
- [#981](https://github.com/Graphify-Labs/graphify/issues/981) (OPEN) —
  configurable base URL for OpenAI **and** Anthropic backends (Z.ai, OpenRouter,
  Together, Groq, Azure). Related open PRs: **#723** (`custom` backend via
  `GRAPHIFY_LLM_BASE_URL`), **#935** (OpenRouter backend). Community advice in
  thread: separate *provider type* (openai-compatible/anthropic-compatible) from
  *transport endpoint* so response parsing is validated independently.
- Ollama-specific bugs: [#820](https://github.com/Graphify-Labs/graphify/issues/820)
  (`GRAPHIFY_OLLAMA_NUM_CTX` not wired → silent empty responses),
  [#798](https://github.com/Graphify-Labs/graphify/issues/798) (context-window
  saturation / missing session reset between chunks),
  [#792](https://github.com/Graphify-Labs/graphify/issues/792) (local-LLM perf /
  high-core CPU scaling), [#1686](https://github.com/Graphify-Labs/graphify/issues/1686)
  (a **hung Ollama request stalls the whole run despite `--api-timeout`**),
  [#1168](https://github.com/Graphify-Labs/graphify/issues/1168) (`.local`
  mDNS hosts hard-blocked as link-local). Env var confusion:
  `OLLAMA_HOST` vs `OLLAMA_BASE_URL` (PRs #1966/#2019).
- Requested-but-not-yet: **Vertex AI** ([#974](https://github.com/Graphify-Labs/graphify/issues/974)),
  **GitHub Models** ([#975](https://github.com/Graphify-Labs/graphify/issues/975)),
  **copilot-cli** ([#976](https://github.com/Graphify-Labs/graphify/issues/976)).

**Cost/token accounting is imperfect.** [#1769](https://github.com/Graphify-Labs/graphify/issues/1769)
— `cost.json` **never appends after the initial run** (token counts printed but
not persisted). [#1694](https://github.com/Graphify-Labs/graphify/issues/1694) —
`cluster-only`/`label` LLM calls had a **hardcoded `tokens={"input":0,"output":0}`
placeholder**, not a real accumulator. [#730](https://github.com/Graphify-Labs/graphify/issues/730)
— hardcoded `max_tokens=8192` caused a **truncation cascade → 3× cost overhead**
on dense docs. [#1277](https://github.com/Graphify-Labs/graphify/issues/1277) —
`cluster-only` auto-picked the wrong Gemini model and hit free-tier rate limits.

**Recommended setup (synthesized from maintainer answers):**
- For **cost-free / no-key** graphing: `graphify extract . --code-only` from the
  terminal (AST only, 0 tokens).
- To add the semantic layer cheaply: set **one** API key; the priority chain
  auto-selects. Gemini wins the chain if `GEMINI_API_KEY`/`GOOGLE_API_KEY` is set
  (watch free-tier rate limits + model auto-pick bug).
- Use the **`claude-cli`/subagent path** to spend a Claude subscription instead
  of a metered key — but cap chunk size (Part 5).
- For **local models**, Ollama is the only fully-wired local backend today;
  vLLM/OpenAI-compat needs the still-open base-URL work (#959/#981/#723).

---

## 2. Ingestion at scale / best practices

**The AST path is the token-free workhorse; the LLM/doc path is where cost and
fragility live.** Maintainer guidance and recurring issues:

**Incremental update / watch — the big correctness area.**
- [#2033](https://github.com/Graphify-Labs/graphify/issues/2033) (OPEN, PR #2050)
  — **the shipped `--update` runbook omits `kind="ast"`**, so
  `detect_incremental()` defaults to `kind="semantic"`; on an AST-only graph
  **every file reports as changed → the whole corpus is re-extracted
  semantically** every update. On a 629-file corpus, `new_total: 629`. This is a
  direct "incremental update silently degrades to full re-extract" trap.
- [#1765](https://github.com/Graphify-Labs/graphify/issues/1765) — `check-update`
  is **blind to newly-created files** (manifest-only comparison) and silent.
- [#1837](https://github.com/Graphify-Labs/graphify/issues/1837) — `graphify
  update <path>` **silently fails to discover newly-added files/dirs even with
  `--force` and a cleared cache**.
- [#1925](https://github.com/Graphify-Labs/graphify/issues/1925) — `--update`
  with a missing `manifest.json` degrades to full scan, and with `--code-only`
  **silently discards the entire semantic layer**.
- [#1915](https://github.com/Graphify-Labs/graphify/issues/1915) —
  `watch._rebuild_code` produced a **~4× bloated graph** vs `graphify . --update`
  (AST-scanned Markdown, then merged semantic nodes on top).
- **`--force` downside** ([Disc #1648](https://github.com/Graphify-Labs/graphify/discussions/1648)):
  users default to `--force` to bypass the "fewer nodes → refuse to overwrite"
  shrink guard; that guard exists precisely to stop a bad partial extract from
  clobbering a good graph, so blanket `--force` reintroduces silent data loss
  (see also the shrink-guard bypass in [#1871](https://github.com/Graphify-Labs/graphify/pull/1871)).

**Chunking / subagent sizing.**
- [#1758](https://github.com/Graphify-Labs/graphify/issues/1758) — SKILL.md
  chunking is **file-count-based (20-25 files/chunk), not output-size-aware**.
  Dense chunks blow past Claude's **64k output-token turn cap** and **silently
  crash**; a reporter measured **6/17 chunks (~35%) failing** on a ~370-file
  corpus. PR #1938 proposes output-sized chunks; #1945 adds
  `GRAPHIFY_FILE_CHAR_CAP`.
- [#450](https://github.com/Graphify-Labs/graphify/issues/450) — the "one
  subagent per image" rule forces **59 images ≈ 59 agents** (~28-30k tokens each
  for ~5 nodes); batching would be ~8× cheaper.

**Deep mode.**
- [#1894](https://github.com/Graphify-Labs/graphify/issues/1894) — semantic
  **cache key ignored extraction mode and `extract` had no `--force`, so
  `--mode deep` over a warm cache was a silent no-op** (you thought you deepened;
  nothing happened). Fixed. [#1895](https://github.com/Graphify-Labs/graphify/issues/1895)
  — deep mode wrote out-of-scope `source_file` nodes anyway.

**Caching hazards.**
- [#1939](https://github.com/Graphify-Labs/graphify/issues/1939) — **semantic
  cache had no prompt/skill-version component**, so **upgrades replayed stale
  extractions** (fixed, PR #1942 keys on the prompt).
- [#1757](https://github.com/Graphify-Labs/graphify/issues/1757) /
  [#1504](https://github.com/Graphify-Labs/graphify/issues/1504) — subagent
  mis-attributing `source_file` **overwrites another file's cache** / same-name
  docs in different dirs collide.

**Scaling large repos (maintainer patterns).**
- [Disc #645](https://github.com/Graphify-Labs/graphify/discussions/645) — split
  a large project into **type-scoped folders + one `AllFolders/` master graph**;
  read `GRAPH_REPORT.md` for daily context (token-efficient), reserve the wiki
  for onboarding/milestones (regenerating the wiki every update is wasteful).
- [Disc #1019](https://github.com/Graphify-Labs/graphify/discussions/1019) —
  **`graphify export` hard-caps at 512 MB `graph.json`**; sharded loading is
  requested ([#1708](https://github.com/Graphify-Labs/graphify/issues/1708)) and
  a **SQLite tiered storage backend for `serve`** is proposed
  ([#1297](https://github.com/Graphify-Labs/graphify/issues/1297), ~17-64× lower
  query latency).
- **Recommended cadence:** commit `graphify-out/` to git; install the
  **git post-commit hook** to keep it current
  ([Disc #1408](https://github.com/Graphify-Labs/graphify/discussions/1408)) —
  but beware the hook fires in worktrees / ignores `GRAPHIFY_SKIP_HOOK`
  ([#1809](https://github.com/Graphify-Labs/graphify/issues/1809),
  [#1810](https://github.com/Graphify-Labs/graphify/issues/1810)).

---

## 3. Agent memory / RAG usage

**Graphify markets itself as both a code index AND a long-term memory system,
and has published benchmarks for both** ([Disc #1677](https://github.com/Graphify-Labs/graphify/discussions/1677),
[BENCHMARKS.md](https://github.com/Graphify-Labs/graphify/blob/v8/BENCHMARKS.md)):
- **Code intelligence (ERPNext, ~1M LOC):** a single graphify tool takes a fixed
  agent from **70.8% → 82.0% key-fact coverage at ~1.3× floor tokens / $0.32 per
  task**, beating codebase_memory (embeddings, 2.7× tokens) and repomix
  ([Disc #1328](https://github.com/Graphify-Labs/graphify/discussions/1328)).
- **Conversational memory (LOCOMO n=300, LongMemEval-S n=50):** claims
  **recall@10 0.497 (~10× mem0)**, +18 pts accuracy-per-dollar over mem0, ~1/10
  supermemory ingest cost; LongMemEval 76% (tied with strong dense-RAG). Honest
  caveat: **supermemory still beats graphify on some axes**. Reproduction Qs in
  [#1706](https://github.com/Graphify-Labs/graphify/issues/1706). *Treat vendor
  self-benchmarks as directional, not independent.*

**Querying the graph from agents.** The install per-IDE writes an **always-on
rule/hook** that tells the agent to run `graphify query "<question>"` (or read
`GRAPH_REPORT.md`) **before** grep/read. Without that wiring, **a `graph.json` on
disk does nothing** — agents ignore it and re-read the whole codebase
([Disc #1931](https://github.com/Graphify-Labs/graphify/discussions/1931),
[#749](https://github.com/Graphify-Labs/graphify/issues/749),
[Disc #921](https://github.com/Graphify-Labs/graphify/discussions/921) "Claude
ignoring Graphify"). The PreToolUse "graphify-first" nudge has gaps: only matched
Bash not Grep ([#1986](https://github.com/Graphify-Labs/graphify/issues/1986),
fixed #2003), and fires on out-of-project files / stale graphs with no freshness
gate ([#1840](https://github.com/Graphify-Labs/graphify/issues/1840)).

**MCP server (`graphify serve` / `serve.py`).** **stdio-only today** — one local
process per IDE session against a local `graph.json`
([Disc #1052](https://github.com/Graphify-Labs/graphify/discussions/1052)).
**Streamable HTTP + OAuth/API-key for a shared team server is requested and the
maintainer wants to support it, but it is not built yet.** If you want a central
team-queryable graph now, you self-host the stdio process or commit
`graphify-out/` and let each dev query locally. Perf work landed in `serve`
(#1889/#1918 collapse per-term scoring passes).

**"Work memory" (self-improving loop)** — [Disc #1449](https://github.com/Graphify-Labs/graphify/discussions/1449),
shipped 0.8.47: `graphify save-result --question … --answer … --nodes … --outcome
useful|dead_end|corrected [--correction …]`. **Deterministic, no LLM**, records
which nodes actually answered a question and prefers them next session. This is
the closest thing to native provenance/feedback.

**god_nodes / provenance / confidence / staleness (the "can I trust it" axis):**
- **god_nodes** = highest-degree hub nodes surfaced in `GRAPH_REPORT.md`.
  Note [#2004](https://github.com/Graphify-Labs/graphify/issues/2004):
  `god_nodes` is **not a CLI subcommand**, and `affected`/reverse-dep lookups
  return **false negatives** because import-derived edge target IDs
  (`pkg_sub_mod`) don't match the scanned node's ID.
- **Confidence is poorly calibrated.** [#540](https://github.com/Graphify-Labs/graphify/issues/540)
  — INFERRED-edge confidence is **bimodal**: subagents cluster at exactly **0.5
  and ~0.85** with almost nothing between, ignoring the prompt's "most edges
  0.6-0.9" guidance (reproduced independently). Don't threshold on confidence
  expecting a smooth distribution.
- **Staleness/freshness is a live, unsolved safety problem.**
  [#2051](https://github.com/Graphify-Labs/graphify/issues/2051) (OPEN) — **stale
  semantic nodes for deleted files are preserved indefinitely and returned as
  authoritative**; one repo accumulated **1,444 nodes for files that no longer
  exist**, including deleted security surfaces (`policy_hard_deny.py`). The
  reporter argues **staleness must be enforced at query time, not just stored as
  a flag** — a stored `stale:true` that `query` still returns in canonical form
  preserves the "false authority" failure. Directly relevant if you make
  graphify the first navigation path for an agent.
  [#1650](https://github.com/Graphify-Labs/graphify/issues/1650) — temporal
  validity + recency weighting requested for living corpora.
- **Provenance `add --author/--contributor`:** **no issue surfaced** for those
  flags (searches returned nothing) — treat as unverified / possibly not a real
  feature. The durable-human-correction story is instead **PR #1871 `graphify
  curate`** (OPEN): today **every edge is extractor-derived, so hand corrections
  are transient by construction** — a deleted edge is re-injected from the
  content-keyed cache, and an added edge is destroyed by `build_merge`'s
  per-`source_file` replace, silently, while node count grows. If you need
  human-authored facts to survive rebuilds, this is unsolved in released
  versions.

---

## 4. Multi-agent / orchestration

- **One shared graph serves all agents/IDEs.** [Disc #1117](https://github.com/Graphify-Labs/graphify/discussions/1117)
  — `graphify-out/` is tool-agnostic; build once, and Codex/Antigravity/Claude
  all query the same graph. Each tool only needs its own **always-on hook**
  installed once (`graphify install --project --platform <codex|cursor|gemini|…>`).
- **Extraction itself is multi-agent** when no headless key is set: the skill
  **fans out semantic extraction to Claude Code Agent-tool subagents** (Part B,
  "the host session is the LLM"). This is the cost-optimized path (uses your
  subscription) **but** is where the 64k-output-token silent-crash and
  file-count-chunking problems bite ([#1758](https://github.com/Graphify-Labs/graphify/issues/1758),
  [#450](https://github.com/Graphify-Labs/graphify/issues/450),
  [#537](https://github.com/Graphify-Labs/graphify/issues/537) "do connections
  only get found within a subagent's file list?" — cross-chunk edges are a known
  weakness).
- **Multi-agent maintenance / deployment idea:** [#1550](https://github.com/Graphify-Labs/graphify/issues/1550)
  (dependency-manager for the many per-agent installs),
  [Disc #1730](https://github.com/Graphify-Labs/graphify/discussions/1730) (why
  per-agent installers exist vs one `--platform agents`: each tool picks its own
  dir + format + registration, so a generic copy silently fails to load).
- **agentmemory integration** ([#152](https://github.com/Graphify-Labs/graphify/issues/152))
  — proposal to pair graphify (structure) with agentmemory (cross-session
  decisions/temporal), community-endorsed, not merged.

---

## 5. Known bugs / limitations / roadmap — betting risk

**The single most important architectural caveat:
[#198](https://github.com/Graphify-Labs/graphify/issues/198) (OPEN) — "Semantic
layer is mostly disconnected from the AST graph."** Confirmed by multiple users
on real repos (e.g. OpenHarness): AST and semantic passes run **in parallel**,
the semantic pass **doesn't know which AST nodes exist this run**, so fusion
relies on **exact node-id collisions** — brittle (`SentenceTransformer` vs
`"sentence transformer"` never match). Result: **one connected code graph + one
separate semantic/document subgraph, with very few real `code↔concept` bridges.**
A contributor (@karthick1005) is exploring identifier normalization + fuzzy
bridging; **not fixed**. If your value hypothesis is "semantic docs enrich the
code graph," verify this holds on *your* corpus before committing.

**Other load-bearing limitations for a knowledge architecture:**
- **Non-determinism.** [Disc #1090](https://github.com/Graphify-Labs/graphify/discussions/1090)
  / [#1105](https://github.com/Graphify-Labs/graphify/discussions/1105) —
  identical inputs produced different node/edge/community counts across runs.
  Root cause (per maintainer): **`os.walk()` returns files in FS b-tree order**,
  and several passes are **first-writer-wins** (import resolution, label dedup,
  symbol resolution), so collisions resolve differently each run; Leiden itself
  is seeded (`random_seed=42`). Partially fixed (stable community ID ordering,
  #1667/#1753); a ~0.1% residual community-count drift remained. LLM extraction
  adds its own non-determinism ([#1695](https://github.com/Graphify-Labs/graphify/issues/1695)
  — no seed/prompt-override; `extract_corpus_parallel` ignores the extraction
  spec).
- **`source_file` path instability (schema churn across patch releases).**
  [#1941](https://github.com/Graphify-Labs/graphify/issues/1941) — `source_file`
  was reduced to a **bare basename in 0.9.16** (was a relative path in 0.9.13),
  breaking resolution against a code root; [#1789](https://github.com/Graphify-Labs/graphify/issues/1789)
  — node IDs / `source_file` **embedded the absolute scan path** (leaks
  username, makes committed `graph.json` non-portable / non-idempotent);
  residuals in [#1899](https://github.com/Graphify-Labs/graphify/issues/1899),
  reopened as [#1825](https://github.com/Graphify-Labs/graphify/issues/1825).
  **Node-ID and path semantics have shifted repeatedly within 0.9.x** — any
  tooling that parses `source_file` or node IDs is exposed to churn.
- **Silent failures are a recurring class** (this project's own "zero-skip"
  concern applies): LLM-omitted documents vanish with no reconciliation
  ([#1890](https://github.com/Graphify-Labs/graphify/issues/1890) — **53% of docs
  lost even with gpt-5**), nested `.gitignore`/`.graphifyignore` rules zero the
  entire corpus ([#1873](https://github.com/Graphify-Labs/graphify/issues/1873),
  [#1887](https://github.com/Graphify-Labs/graphify/issues/1887),
  [#1922](https://github.com/Graphify-Labs/graphify/issues/1922),
  [#1975](https://github.com/Graphify-Labs/graphify/issues/1975)), truncated LLM
  chunks promoted to cache as complete ([#1950](https://github.com/Graphify-Labs/graphify/issues/1950)),
  same-named classes across modules silently overwrite each other
  ([#1744](https://github.com/Graphify-Labs/graphify/issues/1744)), cross-language
  phantom edges bind by name ([#1749](https://github.com/Graphify-Labs/graphify/issues/1749)),
  `weight:null` edges crash clustering ([#1960](https://github.com/Graphify-Labs/graphify/issues/1960)),
  XSS in the HTML export ([#1838](https://github.com/Graphify-Labs/graphify/issues/1838)).
  The maintainer is responsive (many closed within a day), but the **rate of
  new silent-failure reports is high** and Windows is a persistent weak spot
  ([#1892](https://github.com/Graphify-Labs/graphify/issues/1892),
  [#1987](https://github.com/Graphify-Labs/graphify/issues/1987),
  [#1907](https://github.com/Graphify-Labs/graphify/issues/1907)).

**Roadmap / direction (from Announcements + maintainer):**
- **v8 branch is the near-term staging line**; fixes land there then ship in the
  next `0.9.x`. No public "v1.0" date surfaced — releases are rapid `0.9.x`.
- **Graphify Enterprise** (self-hosted, "trust AI-written code," team scale) is
  in **early access**; OSS stays free/local ([Disc #1798](https://github.com/Graphify-Labs/graphify/discussions/1798)).
  **YC S26** ([Disc #983](https://github.com/Graphify-Labs/graphify/discussions/983)).
- Actively wanted/proposed: **Streamable-HTTP MCP + auth** (#1052), **SQLite
  tiered `serve` storage** (#1297), **sharded graph loading** (#1708),
  **temporal/recency-weighted facts** (#1650/#1115), **durable human curation**
  (#1871), **AST↔semantic alignment** (#198), custom/local backend base-URLs
  (#959/#981/#723/#935).

**Net "should we bet on it" read:** graphify is a **fast-moving, single-maintainer-
led, pre-1.0, now-commercializing** tool with a compelling zero-token AST core
and published (self-run) benchmarks. The **AST/structural graph is the solid
part**. The risks that matter for a durable knowledge architecture are (a) the
**AST↔semantic disconnect (#198)**, (b) **stale-node false authority (#2051)**,
(c) **non-determinism + node-ID/`source_file` schema churn across patch
releases**, (d) **human corrections don't survive rebuilds (#1871)**, and (e)
**no shared/HTTP MCP yet**. Pin a version, prefer `--code-only` for the
deterministic token-free layer, and validate the semantic-enrichment claim on
your own corpus before depending on it.

---

## GitHub repos touched

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — primary
  subject; issues, PRs, discussions, and releases mined for backends, cost,
  ingestion, agent-memory, multi-agent, and roadmap/limitations.
- [FolatheDuckofDuckingburg/graphify](https://github.com/FolatheDuckofDuckingburg/graphify/tree/v8/benchmarks)
  — community benchmark framework fork referenced in [Disc #1328](https://github.com/Graphify-Labs/graphify/discussions/1328).
- [rohitg00/agentmemory](https://github.com/rohitg00/agentmemory) — temporal
  agent-memory tool proposed for integration in [#152](https://github.com/Graphify-Labs/graphify/issues/152).
- [oraios/serena](https://github.com/oraios/serena) — compared vs graphify in
  [Disc #1124](https://github.com/Graphify-Labs/graphify/discussions/1124).
- [HKUDS/OpenHarness](https://github.com/HKUDS/OpenHarness) — the corpus a user
  ran to demonstrate the AST↔semantic disconnect in [#198](https://github.com/Graphify-Labs/graphify/issues/198).
- [Lum1104/Understand-Anything](https://github.com/Lum1104/Understand-Anything),
  [AsyncFuncAI/deepwiki-open](https://github.com/AsyncFuncAI/deepwiki-open) —
  alternative GraphRAG-style tools named by commenters in [#198](https://github.com/Graphify-Labs/graphify/issues/198).
