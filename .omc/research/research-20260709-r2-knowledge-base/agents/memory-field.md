# Run G / Angle 2 — Agent-memory field: graphiti, mem0, cognee, basic-memory vs baselines

Analyst: memory-field agent, 2026-07-09.
Scope: compare the agent-memory tools on **coding-agent-retrieval merits for THIS
repo's research corpus** (markdown research artifacts, rules, notepad; solo dev,
Mac, Docker Desktop; hard constraint: no MCP server registration via the Claude
CLI's `mcp add` subcommand — CLI/SDK/mcp2cli process-spawn only).
Grounding: `.omc/research/research-20260709-r2-inventory/report.md` (corpus =
`.omc/research/**`, `docs/research/**` incl. mintlify-cache for 16 repos,
`.claude/rules/*.md`; current retrieval = cache-first grep).

---

## Findings

### F1. Candidate comparison matrix (solo-dev-on-a-Mac lens)

| Criterion | graphiti (getzep) | mem0 | cognee | basic-memory | markdown+grep (baseline) | semtools (light local vector) |
|---|---|---|---|---|---|---|
| Infra | Graph DB server: Neo4j 5.26+/FalkorDB 1.1.2+/Neptune; Kuzu deprecated; embedded "FalkorDB Lite" only on Py3.12+ | Lib mode: local Qdrant at `/tmp/qdrant` + SQLite; server mode: Docker Compose + Postgres/pgvector | Fully embedded defaults: Kuzu (graph) + LanceDB (vector) + SQLite — no external services | Local markdown files + SQLite index; no server | none | Rust CLI; LanceDB workspace at `~/.semtools/workspaces/` |
| LLM/API key required | Yes — defaults to OpenAI for LLM + embeddings (`OPENAI_API_KEY`); Anthropic/Gemini/Groq supported | Yes — default OpenAI `gpt-5-mini` + `text-embedding-3-small` | Yes — "Users must provide an LLM API key (OpenAI by default)" | **No** — pure knowledge layer; the client LLM does the thinking | No | No — local model2vec `potion-multilingual-128M` embeddings |
| Markdown-corpus ingestion | Episodes API (text/JSON); per-episode multi-stage LLM extraction — "fires many LLM calls per episode" (practitioner report) | Conversation-memory-first: `add()` runs LLM fact extraction — lossy for documents | `cognee.remember("text")` / add over files; batched LLM extraction (Extract-Cognify-Load) | Indexes markdown directly (files are "the source of truth"); graph value requires its Observations/Relations note format | Corpus is already the store | `workspace` indexes files, auto re-embeds on change |
| Retrieval surface | Hybrid search (embeddings+BM25+graph traversal); Python SDK + FastAPI REST + MCP server; **no CLI** | Semantic search API w/ filters; SDK + REST + MCP | `recall` auto-routed search; Python/Rust/TS SDKs + `cognee-cli` + MCP (stdio/HTTP/SSE) | MCP tools AND full CLI: `basic-memory sync`, `basic-memory tool search-notes --query ...`, `build_context` wikilink traversal | Grep/Glob/Read (native agent tools) | `semtools search` CLI, unix pipes, JSON output (v3.0.0) |
| MCP-free agent integration | Script the Python SDK; or mcp2cli against its MCP server | Script the SDK | `cognee-cli` or SDK scripts | CLI is first-class (`bm` alias) — cleanest fit for the no-registration rule after grep | Already native | CLI-native, designed for coding agents |
| Maturity (July 2026) | 28.6k★, v0.29.2 (Jun 2026), 255 open issues, Apache-2.0 | 60.5k★, 356 releases, active | 27.4k★, v1.2.2.dev4 (Jul 2026), 8.4k commits, peer-reviewed paper arXiv:2505.24478 | 3.4k★, v0.22.1 (Jun 2026), 86 releases | n/a | LlamaIndex-backed, v3.0.0 (2026), crates.io |
| Maintenance risk | Schema/version migrations of a graph DB + prompt-extraction drift; ingestion re-cost on model change | Platform-first vendor (benchmark wins are "managed platform… proprietary optimizations not available in the open-source SDK" — own README); graph layer de-emphasized | "Most complex operational model; requires deliberate build-step invocation" (practitioner review); pre-1.0-style dev releases | Low: files stay plain markdown even if tool dies | Zero | Low: index is disposable, files untouched |

Sources: [getzep/graphiti README](https://github.com/getzep/graphiti);
[mem0ai/mem0 README](https://github.com/mem0ai/mem0) and
[mem0 OSS overview docs](https://docs.mem0.ai/open-source/overview);
[topoteretes/cognee README](https://github.com/topoteretes/cognee);
[basicmachines-co/basic-memory README](https://github.com/basicmachines-co/basic-memory),
[CLI reference](https://docs.basicmemory.com/guides/cli-reference/),
[knowledge-format guide](https://basicmachines.mintlify.app/guides/knowledge-format);
[run-llama/semtools](https://github.com/run-llama/semtools).

### F2. The benchmark evidence is unreliable — and the strongest single data point favors "no memory system"

- **LoCoMo is broken as a decision input.** Zep's audit (["Is Mem0 Really SOTA in
  Agent Memory?"](https://blog.getzep.com/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/),
  May 2025, corrected Jun 2026) documents missing Category-5 ground truth,
  wrong speaker attributions, multimodal questions lacking image descriptions,
  and — decisively — conversations of only ~16k–26k tokens, i.e. **inside modern
  context windows**.
- **The full-context baseline (~73%) beat mem0's best (~68%)** on Zep's corrected
  LoCoMo run — "If simply providing all the text yields better results than the
  specialized memory system, the benchmark isn't adequately stressing memory
  capabilities" (same post).
- The numbers are also **vendor-contested in both directions**: Zep's 84% claim
  was corrected by Mem0 to 58.44% ([getzep/zep-papers#5](https://github.com/getzep/zep-papers/issues/5)),
  counter-corrected by Zep to 75.14%; a May 2026 meta-analysis
  (["The Benchmark Theatre"](https://essays.bloo-mind.ai/posts/2026-05-20-mem-eval/))
  found each vendor runs its own answer model, judge model, judge prompt, and
  question subset, and that a judge-model swap alone moved scores ~10 points.
- **None of the published memory benchmarks measure code/research-document
  retrieval.** LoCoMo/LongMemEval are conversational-recall benchmarks. There
  is no published evidence that graphiti/mem0/cognee improve retrieval over
  a *technical markdown corpus* — the exact workload here. The May 2026
  practitioner comparison ([codepointer](https://codepointer.substack.com/p/agent-memory-systems-and-knowledge))
  explicitly "provides no targeted analysis for code or technical content."

### F3. The contrarian evidence is strong and recent: grep/agentic file search wins for this workload

- **Anthropic's own guidance** ([Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents),
  2025-09-29): agents should "maintain lightweight identifiers (file paths,
  stored queries, web links…)" and load just-in-time; Claude Code's design is
  the hybrid — "CLAUDE.md files are naively dropped into context up front,
  while primitives like glob and grep allow it to navigate its environment."
  Its recommended memory primitive is *structured note-taking*: "your custom
  agent maintaining a NOTES.md file" — which is literally this repo's
  `.omc/notepad.md` + `.claude/rules/` architecture, already in place.
- **arXiv:2605.15184** ("Is Grep All You Need?", May 2026): on a 116-question
  LongMemEval sample across Claude Code/Codex/Gemini-CLI harnesses, "grep
  generally yields higher accuracy than vector retrieval," and results depend
  more on harness/tool-calling style than on retrieval method
  ([abs](https://arxiv.org/abs/2605.15184)).
- **arXiv:2602.23368** ("Keyword search is all you need", Dec 2025): agentic
  keyword-search tools attain ">90% of the performance metrics compared to
  traditional RAG systems" with no vector DB, and are "particularly useful in
  scenarios requiring frequent updates" ([abs](https://arxiv.org/abs/2602.23368)) —
  the research corpus here changes every session.
- **LlamaIndex's own experiment** ([semtools blog](https://www.llamaindex.ai/blog/semtools-are-coding-agents-all-you-need),
  2025-09-05, 1,000 arXiv papers): "giving an agent access to the CLI proves
  to be a powerful baseline for document search"; adding local semantic search
  helped mainly on cross-referencing and temporal-analysis questions (more
  thorough answers, fewer tool calls), not on basic search/filter — both
  approaches found accurate information there.
- Net: for a corpus of dozens-to-hundreds of markdown files with an existing
  greppable index convention (`## GitHub repos touched`, mintlify-catalog),
  the evidence says the current grep-first architecture is not a naive
  placeholder — it is the pattern the strongest recent evidence supports.

### F4. Per-candidate assessment for THIS corpus

**graphiti — defer.** Best-in-class *bi-temporal* fact tracking (valid time +
transaction time, full edit history), but that solves conversational-fact
churn, not research-artifact retrieval. Costs for a solo Mac: a running graph
DB (Neo4j/FalkorDB; the embedded FalkorDB-Lite path needs Python 3.12+ and is
new), a mandatory LLM+embedding key, "many LLM calls" per ingested episode for
extraction + contradiction resolution, and **no CLI** — integration without MCP
registration means writing and maintaining Python SDK scripts. High capability,
wrong workload, highest infra+ingestion cost of the field.

**mem0 — reject for this use.** It is a *conversational preference* memory
("remembers user preferences… continuously learns"), not a document KB; its
`add()` path LLM-extracts atomic facts (lossy for research reports with
evidence tables); its headline benchmark gains are platform-only by its own
README; and the practitioner review reports the OSS graph layer was
de-emphasized ("abandoned graph layer; lost single and multi-hop reasoning").
Default stack still needs an OpenAI key + local Qdrant.

**cognee — the credible graph contender, but still defer.** Lightest infra of
the graph tools (embedded Kuzu+LanceDB+SQLite, `uv pip install cognee`,
`cognee-cli` exists — MCP-free integration is genuinely easy), peer-reviewed
paper, very active. But it still requires an LLM key and a deliberate
Extract-Cognify-Load build step per corpus change ("most complex operational
model" per the practitioner review), version string is `v1.2.2.dev4` — API
churn risk — and there is no evidence its graph retrieval beats grep on
technical markdown. If Ray later wants graph *synthesis* over the corpus, note
that the **/graphify user-level skill already covers the synthesis niche**
(inventory report:109-111) without adopting a second graph stack.

**basic-memory — closest philosophical fit; adopt-only-if a convention upgrade
is wanted.** It is the only candidate that agrees with the repo's architecture:
"Plain text on your disk. Forever." + SQLite index, no LLM key, and a
first-class CLI (`basic-memory sync`, `basic-memory tool search-notes --query
…`, `bm` alias) that satisfies the no-MCP-registration constraint without
wrappers. Two caveats: (a) its knowledge-graph value comes from its note
format — frontmatter + `- [category] observation` + `relation [[wikilink]]`
lists — which the existing corpus does not use; plain files are indexed for
search but the docs "do not explicitly address" how unstructured files
participate in the graph, so adoption ≈ adopting a *writing convention*, with
FTS search + wikilink traversal as the payoff; (b) smallest community of the
field (3.4k★) — though exit risk is ~zero because the store is the markdown
itself. The realistic adoption shape: keep grep primary, optionally teach the
report template basic-memory-compatible frontmatter/relations so a future
index is free.

**markdown + grep (do-nothing baseline) — the evidence-backed default.** Zero
infra, zero keys, zero maintenance; native to every agent harness; supported by
Anthropic guidance, arXiv:2605.15184, and arXiv:2602.23368 (F3). Its real
weaknesses are *synonym misses* and *cross-report synthesis* — the first is
cheaply patched by conventions (repos-touched enumerations, consistent slugs,
an index file per research run), the second is what /graphify periodic
synthesis is for.

**semtools (lightweight local vector) — the best "one notch up" if grep starts
missing.** `cargo install semtools`; local 128-dim model2vec embeddings (no
API key, no server); LanceDB workspace that auto-re-embeds changed files;
unix-piped CLI with JSON output — an agent can call it exactly like grep.
LlamaIndex's eval shows where it pays: cross-referencing/temporal questions
over large corpora. At today's corpus size (dozens of reports + 16-repo
mintlify cache) grep suffices; semtools is the pre-identified escape hatch,
adoptable in an afternoon with no architectural change.

### F5. Integration constraint check (no MCP registration)

Every candidate has a registration-free path, but the ergonomics differ sharply:
- native: **grep** (agent built-in), **semtools** + **basic-memory** (real CLIs),
  **cognee** (`cognee-cli`);
- scripted: **graphiti**/**mem0** (Python SDK scripts, or mcp2cli process-spawn
  against their MCP servers per `.claude/skills/mcp2cli/SKILL.md`) — workable
  but adds a maintained script surface for zero proven retrieval gain (F2/F3).

## Uncertainties / gaps

- **No benchmark exists for this exact workload** (agent retrieval over a
  technical research-markdown corpus). All quantitative evidence is adjacent
  (LongMemEval samples, arXiv-paper QA, enterprise doc QA). A cheap in-repo
  A/B (grep vs semtools on 10 real "which past report said X?" questions)
  would beat any published number.
- Stars/release figures were read from repo pages on 2026-07-09 via WebFetch
  summarization and may be slightly stale; graphiti's "FalkorDB Lite embedded"
  maturity was not independently probed (docs page fetch returned only a
  landing stub).
- basic-memory's handling of *unstructured* legacy markdown (indexed-but-
  graphless?) is undocumented — verify empirically before any adoption.
- Scale threshold where grep degrades (corpus size / synonym density) is not
  established in the literature; the semtools blog and arXiv:2602.23368 imply
  keyword-first holds well into the thousands-of-files range, but no hard
  boundary is published.
- mem0's "abandoned graph layer" claim comes from one practitioner analysis
  (codepointer, 2026-05-28); mem0 docs still market graph memory — the actual
  OSS graph-memory state was not code-verified.

## Verdict summary (this angle's input to the domain recommendation)

| Candidate | Verdict |
|---|---|
| markdown + grep + conventions | **Keep as primary** (evidence-backed, F3) |
| semtools | **Adopt-on-trigger** (pre-approved escape hatch when grep misses) |
| basic-memory | **Defer / optional convention alignment** (frontmatter+wikilinks in new reports) |
| cognee | **Defer** (re-evaluate if a queryable graph, not just synthesis, becomes a need) |
| graphiti | **Defer** (wrong workload; heaviest footprint; no CLI) |
| mem0 | **Reject** for research-KB use (conversation-preference memory) |

## GitHub repos touched

- [getzep/graphiti](https://github.com/getzep/graphiti) — capabilities, infra backends, maturity from README
- [mem0ai/mem0](https://github.com/mem0ai/mem0) — OSS/platform split, defaults, benchmark claims
- [topoteretes/cognee](https://github.com/topoteretes/cognee) — embedded defaults, CLI/MCP surfaces, maturity
- [basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory) — markdown-native model, CLI, maturity
- [run-llama/semtools](https://github.com/run-llama/semtools) — local-embedding CLI baseline details
- [getzep/zep-papers](https://github.com/getzep/zep-papers) — issue #5, LoCoMo score-correction dispute
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — grounding inventory report + corpus conventions
