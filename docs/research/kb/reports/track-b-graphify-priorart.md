# Track B — graphify as shared knowledge substrate + prior-art gate

Agent: track-b-graphify-priorart · Date: 2026-07-19 · Host: Ray's Mac (installed
`graphify` 0.9.17 on PATH; read source of the installed wheel + official docs of
each competitor). Answers the four questions and applies the `use-tool-builtins`
HARD GATE: **before we build a read-through/write-back knowledge layer, confirm
we use graphify correctly AND that no existing tool/feature already provides part
or all of it.**

**Headline finding (load-bearing):** graphify's node/edge schema **already**
carries provenance (`source_url`, `captured_at`, `author`, `contributor`),
confidence (`EXTRACTED|INFERRED|AMBIGUOUS` + numeric `confidence_score`), and
source-cited query output — the exact primitives Track B assumed it would have to
build. The prior teardown (`named-graphify.md`) never surfaced this schema, so we
were about to **rebuild capabilities graphify ships**. Most of Track B is WIRING,
not new engine code. The genuinely-missing pieces are narrow (age-based staleness
scoring; a lightweight single-fact append; per-tool "expert view" selection; the
read-through routing seam).

**Evidence base (all run/fetched 2026-07-19):**
- Installed wheel source `~/.local/share/mise/installs/pipx-graphifyy/0.9.17/graphifyy/lib/python3.14/site-packages/graphify/*.py`
  — cited below as `graphify/<file>.py:<line>`.
- `graphify --help`, `graphify save-result --help`, and probes of `god-nodes`/`tree`/`global`/`export` subcommands.
- Official docs/READMEs of Graphiti, mem0, Microsoft GraphRAG, the MCP memory
  server, cognee, Letta, LlamaIndex PropertyGraphIndex (URLs in repos-touched).
- Prior teardown `docs/research/runs/research-20260719-harness-knowledge-landscape/agents/named-graphify.md`.

---

## Q1 — graphify best practices + are we using it right?

### The actual command/feature surface (0.9.17, verified)

- **`query "<q>"`** — BFS traversal of `graph.json` (`--dfs` for depth-first),
  `--budget N` tokens (**default 2000**), `--context C` **edge-relation filter**
  (repeatable), `--graph <path>`. Output is **source-cited**: the subgraph
  serializer emits `[src=<source_file> loc=<source_location> …]` and the edge
  `confidence` inline for every node/edge (`graphify/serve.py:220-234`). So
  read-through queries return citations *for free* — no extra layer needed.
- **`affected "X"`** — reverse traversal (impact analysis); `explain "X"` —
  plain-language node+neighbors; `path "A" "B"` — shortest path.
- **`update <path>`** — re-extract code, **no LLM** (AST via tree-sitter);
  `--watch` is a resident process (needs the `watch` extra). `check-update`
  prints a **needs_update / "pending non-code changes"** notice, cron-safe
  (`graphify/watch.py:1268-1279`).
- **`add <url> [--author --contributor]`** — fetch a URL (tweet / webpage /
  arxiv / binary), write it to `./raw` **with YAML provenance frontmatter**, then
  fold it into the graph (`graphify/ingest.py:103-251`). This is the write-back
  path (see Q2b).
- **`cluster-only` / `label`** — (re)detect communities and LLM-name them; the
  `--wiki` skill step emits `wiki/index.md` + one article per community — the
  **agent-crawlable index** a librarian subagent Greps.
- **`merge-graphs <g1> <g2>` / `global add|list`** — cross-repo / multi-corpus
  graphs (`~/.graphify/global-graph.json`).
- **`save-result` / `reflect`** — a **Q&A feedback loop**: persist a query
  outcome (`--outcome {useful,dead_end,corrected}`, `--correction`) to
  `graphify-out/memory/`; `reflect` merges them and marks entries `stale`
  (`graphify/reflect.py:863-868`). A lightweight, non-LLM write-back of *agent
  experience* (distinct from ingesting new source facts).

### God nodes — what they actually are, and a task-premise correction

`god_nodes(G, top_n=10)` = the **top-N highest-degree "real entity" nodes** —
degree centrality, **excluding** file-level hub nodes, concept nodes, and
JSON-key nodes (which accrue edges mechanically) and built-in-noise labels
(`graphify/analyze.py:100-124`). They are the graph's core abstractions.

**Correction to the brief:** there is **no `graphify god-nodes` CLI subcommand**
at 0.9.17 — the probe returned `error: unknown command 'god-nodes'`. God nodes
are exposed two ways only: (1) the **MCP tool `god_nodes`** (`serve.py:394`,
`_tool_god_nodes` → `analyze.god_nodes`, `serve.py:493-495`), and (2) the
`GRAPH_REPORT.md` "god nodes" section. There is **no per-domain god-node "view"**
as a first-class feature — you approximate per-domain hubs by (a) per-community
subgraphs (each community has its own local hubs) plus (b) `query --context`
edge-relation filtering, or (c) a per-domain `merge-graphs` sub-graph file.

### The MCP server (`graphify-mcp` = `python -m graphify.serve`)

Exposes **7 tools** (`graphify/serve.py:340-416`): `query_graph`, `get_node`,
`get_neighbors`, `get_community`, `god_nodes`, `graph_stats`, `shortest_path`.
`graph_stats` returns node/edge/community counts **and a confidence breakdown**
(`serve.py:400,500-511`). No LLM is imported on the serve/query path — query is
deterministic and ~free. (Confirms `named-graphify.md`; the older R2 claim of "11
tools incl. list_prs/triage_prs" is stale — those are not in the 0.9.17 set.)

### Are we using it right?

`named-graphify.md`'s operational verdict is sound — **build periodic/gated,
query on-demand, deterministic `graphify query`/committed `wiki/` shell-out as the
default subagent path, `mcp2cli`→`graphify-mcp` as the structured escalation, no
native `claude mcp add`.** That holds.

**But the teardown missed the single most Track-B-relevant fact:** graphify's
schema **already models provenance and confidence** (Q2). We are therefore
*under-using* graphify — the `add --author --contributor` provenance path, the
`captured_at` timestamp, and the `confidence`/`confidence_score` edge fields are
unexploited in our current design, which assumed we'd have to add them.

---

## Q2 — does graphify natively support the pattern we want?

The extraction contract graphify hands its LLM/subagents is the ground truth for
what the schema can hold (`graphify/llm.py:437`, verbatim shape):

```json
{"nodes":[{"id":"stem_entity","label":"…","file_type":"code|document|paper|image|rationale|concept",
  "source_file":"relative/path","source_location":null,"source_url":null,
  "captured_at":null,"author":null,"contributor":null}],
 "edges":[{"source":"…","target":"…",
  "relation":"calls|implements|references|cites|conceptually_related_to|shares_data_with|semantically_similar_to",
  "confidence":"EXTRACTED|INFERRED|AMBIGUOUS","confidence_score":1.0,
  "source_file":"…","source_location":null,"weight":1.0}],
 "hyperedges":[{…,"confidence":"EXTRACTED|INFERRED","confidence_score":0.75,…}]}
```

| Track-B requirement | graphify native? | Evidence / caveat |
|---|---|---|
| **(a) read-through query with source citations** | **YES, out of the box** | `query` output embeds `[src= loc=]` + `confidence` per node/edge (`serve.py:220-234`); MCP `get_node` prints `Source: <source_file> <source_location>` (`serve.py:444`). |
| **(b) write-back of NEW facts w/ provenance + timestamp + confidence** | **YES, with a caveat** | `add <url> --author --contributor` writes frontmatter `source_url` / `captured_at: {now}` / `author` / `contributor` (`ingest.py:119-192`); schema propagates them to node attrs; edges get `confidence` + `confidence_score`. **Caveat:** write-back is **URL/document-oriented → re-extract**, and re-extracting prose spends LLM/host-agent tokens (a *gated/priced* build — which actually **fits** the "gated/priced builds" constraint). There is **no API to append one structured fact node without a re-extract**; `save-result` appends *Q&A outcomes*, not source facts. |
| **(c) staleness / freshness (know a node is out of date)** | **PARTIAL** | Three mechanisms: `check-update` needs_update pending flag (`watch.py:1268`); `_stale_graph_sources` + `_prune_graph_json_sources` prune nodes whose **source file was deleted** (`cli.py:108,203`); `reflect._is_stale` marks stale Q&A-memory entries (`reflect.py:868`). **Gap:** `captured_at` is *stored but not scored* — there is **no age-based freshness ranking and no bi-temporal "was true then, invalid now" invalidation**. This is the one capability a competitor (Graphiti) clearly beats it on. |
| **(d) per-domain subgraphs / god-node "expert views"** | **PARTIAL** | Communities (auto-clustered, `cluster-only`/`label`), per-graph `god_nodes`, `query --context` edge-relation filter, and cross-corpus `merge-graphs`/`global`. **Gap:** no first-class "god-node-anchored expert view per tool/domain" — you assemble it from communities + context filters + per-domain sub-graph files (a thin config/selection layer, not an engine). |

**Net:** (a) and (b) are native; (c) and (d) are partial. The pattern is ~70%
built-in.

---

## Q3 — prior-art scan (the use-tool-builtins gate)

Does an established tool already do "agent memory over a KG with read-through /
write-back + provenance"? Capability matrix, then per-tool verdict.

| Tool | Graph? | Read-through | Write-back | Provenance | Confidence | Staleness | Sub-graphs/NS | MCP | Infra weight | Verdict vs graphify |
|---|---|---|---|---|---|---|---|---|---|---|
| **graphify** 0.9.20 | ✅ NetworkX | ✅ cited | ✅ (URL→re-extract) | ✅ url/author/ts | ✅ 3-level+score | ⚠️ prune+pending, no age | ⚠️ communities/context/merge | ✅ 7 tools | **host pipx, zero infra** | (baseline) |
| **Graphiti / Zep** | ✅ Neo4j/FalkorDB | ✅ w/ lineage | ✅ real-time incremental | ✅ episodes→facts | (temporal, not per-edge score) | ✅✅ **bi-temporal invalidation** | ✅ `group_id` | ✅ | Neo4j + server + LLM extract | **adopt-partial (steal staleness pattern)** |
| **mem0 / OpenMemory** | ⚠️ optional graph store | ✅ vector+BM25+entity | ✅ ADD-only | ⚠️ limited | ✗ | ⚠️ temporal reasoning, ADD-only | ✅ user/session/agent | ✅ OpenMemory (local: Qdrant+PG) | Qdrant+Postgres | **adopt-partial (vector memory, not KG-provenance)** |
| **cognee** | ✅ graph+vector | ✅ auto-router | ✅ ECL "remember" | ✅ audit/OTEL lineage | ⚠️ | ⚠️ session timelines | ✅ dataset/tenant | ✅ | Docker, Postgres+pgvector | **adopt-partial (heavier)** |
| **Letta / MemGPT** | ✗ **blocks+vector** | ✅ archival recall | ✅ self-editing | ✗ | ✗ | ✗ | ✅ per-agent shareable blocks | ✅ | server | **not-a-fit (different paradigm)** |
| **MS GraphRAG** | ✅ | ✅ global/local | ⚠️ incremental *index* | ⚠️ references | ✗ | ✗ | community reports | ✗ | LLM-heavy batch pipeline | **not-a-fit as live memory (overlaps build, pricier)** |
| **LlamaIndex PropertyGraphIndex** | ✅ BYO store | ✅ multi-retriever | ✅ `insert()` | ⚠️ dev-added | ✗ | ✗ | ⚠️ schema/labels | (via server) | library, BYO store | **construction-kit, not turnkey** |
| **MCP memory server** (in our `.mcp.json`) | ✅ (thin) | ✅ search/open/read | ✅ create/add | ✗ | ✗ | ✗ | ✗ | ✅ (is one) | JSONL file | **incumbent but too thin — superseded by graphify** |

### Per-tool notes (primary-sourced)

- **Graphiti / Zep (getzep/graphiti, ~2.8k★, backed by Zep).** The **closest fit
  and the only tool that beats graphify on staleness.** README: "Episodes &
  Provenance — every entity and relationship traces back to the episodes that
  produced it. Full lineage." "Explicit **bi-temporal** tracking with **automatic
  fact invalidation** … old facts are invalidated — not deleted … query what's
  true now, or what was true at any point." Incremental real-time write-back;
  `group_id` namespaces; ships an MCP server. **Cost of adoption:** requires
  Neo4j/FalkorDB + a resident server + LLM extraction — a database/service
  footprint that contradicts our host-only/gated/pipx model. **Verdict:
  adopt-partial — copy the bi-temporal/`captured_at`-scored staleness *pattern*
  into our graphify wiring; do NOT adopt the Neo4j+server infra for a Mac-host
  periodic KB.**
- **mem0 (mem0ai/mem0, YC S24).** Vector-first memory layer: "multi-signal
  retrieval — semantic, BM25, entity matching"; **multi-level user/session/agent**
  scoping; "temporal reasoning"; **ADD-only** extraction (conflicts accumulate
  rather than resolve); optional graph store. Provenance is limited. **OpenMemory
  MCP** is a real, **local-first** server (Qdrant + Postgres; tools
  `add_memories`/`search_memory`/`list_memories`). **Verdict: adopt-partial** for
  *agent working memory*, but it is not a provenance-centric KG — wrong axis for
  "shared knowledge substrate with citations."
- **cognee (topoteretes/cognee, ~13k★).** ECL ("remember" = add+cognify+improve)
  graph+vector engine; tenant/dataset isolation with "audit traits, OTEL
  collector" lineage; MCP server; runs on a single Postgres+pgvector (Docker).
  **Verdict: adopt-partial but heavier** — Docker + Postgres is more infra than a
  host pipx tool, for overlapping capability.
- **Letta / MemGPT (letta-ai/letta).** Memory = **core memory blocks + archival
  (vector) memory + recall**, self-editing; **not a knowledge graph**; per-agent
  shareable blocks; MCP-capable. No provenance/confidence/staleness graph.
  **Verdict: not-a-fit** as the KG substrate (it solves per-agent working memory,
  a complementary layer, not shared cited knowledge).
- **Microsoft GraphRAG.** **Offline batch indexing pipeline** (global/local
  search, LLM-heavy GPT-4-class extraction + community summarization); has
  incremental *indexing* but is a RAG indexer, **not live agent memory**; no
  first-class provenance/confidence/staleness-as-memory. **Verdict: not-a-fit as
  write-back memory** — it overlaps graphify's *build* role at higher price and
  heavier ops.
- **LlamaIndex PropertyGraphIndex.** Strong **library building block**:
  multi-retriever read-through (LLMSynonym/VectorContext/TextToCypher),
  `index.insert()` incremental write-back, BYO store (Neo4j/Nebula/FalkorDB).
  **Provenance/confidence/staleness are explicitly developer-added, not
  built-in.** **Verdict: a construction kit** — if we were building from scratch
  we'd reach for it, but graphify already *is* the assembled tool.
- **MCP memory server (`@modelcontextprotocol/server-memory`) — already shipped in
  this repo's `.mcp.json`.** Entities/relations/observations over a JSONL file;
  read (`search_nodes`/`open_nodes`/`read_graph`) + write (`create_entities`/
  `add_observations`/`create_relations`). **No provenance, timestamps, confidence,
  staleness, or namespaces** — explicitly a "basic/reference implementation."
  **Verdict: the incumbent write-back store, but too thin to be the substrate** —
  graphify supersedes it for the provenance-bearing KG role.

---

## Q4 — Recommendation

**Build the knowledge layer ON graphify (hybrid: adopt graphify's under-used
native features + borrow one pattern from Graphiti). Do NOT adopt a graph-DB
memory service.**

The `use-tool-builtins` gate resolves clearly. graphify natively provides (a)
read-through with citations and (b) write-back with provenance/timestamp/
confidence, and partially provides (c) staleness and (d) sub-graphs. Adopting
Graphiti/cognee/mem0 would introduce **Neo4j/Postgres/Qdrant + a resident server
+ an LLM-extraction bill** — directly against our constraints (host-only,
project-scoped, gated/priced builds) — to buy capability we ~70% already have on
a zero-infra host pipx tool. That fails the gate: an existing tool (graphify)
already provides most of it, so custom/heavier alternatives are the last resort.

**What to wire (native, not new engine code):**
1. **Read-through** = the `named-graphify.md` path (c): deterministic `graphify
   query` shell-out over committed `graph.json` + Grep of committed `wiki/`. Query
   already returns citations. The "query graphify before web" rule is a thin
   agent/skill seam, not graphify's job.
2. **Write-back with provenance** = the `add <url> --author --contributor` path —
   a research miss becomes a queued `add`, folded in at the next **gated** build
   (re-extract is priced, which the gating constraint *wants*). This gives
   `source_url` + `captured_at` + `author` + `contributor` + `confidence_score`
   automatically — the anti-poisoning provenance Track B needs.
3. **Per-tool specialists** = per-domain views assembled from communities +
   `query --context` + optional per-domain `merge-graphs` sub-graph files, anchored
   on each domain's `god_nodes`. Selection/config layer only.

**The genuine gaps to fill either way (scope them small):**
- **G1 — age-based staleness scoring / invalidation.** graphify stores
  `captured_at` but never scores on it. This is the ONE place a competitor
  (Graphiti's bi-temporal auto-invalidation) is clearly ahead. Fill by ranking/
  flagging nodes by `captured_at` age at query time (a thin post-filter over the
  committed graph) — borrow Graphiti's *pattern*, not its Neo4j.
- **G2 — lightweight single-fact append.** graphify write-back is URL/doc→
  re-extract; there is no "append one structured fact node" API. If we want a
  cheap non-LLM append for a single research finding, that's small custom code
  over `graph.json` (or lean on `save-result` for Q&A-shaped facts). Justify per
  `use-tool-builtins` before writing it — the `add`+gated-rebuild path may suffice.
- **G3 — per-tool "expert view" selection.** No first-class feature; a thin config
  mapping domain → community/context/sub-graph. Not an engine.
- **G4 — read-through routing seam.** "Query graphify before web" is agent/skill
  wiring (a rule + the shell-out), not a graphify capability.

**Also:** the repo already ships the MCP memory server in `.mcp.json`; it lacks
provenance/staleness, so it is **not** the durable substrate — graphify is. Keep
it only for ephemeral scratch entity-notes if at all; do not build Track B on it.

**Confidence:** HIGH on the capability facts (read from the installed wheel +
primary docs). MEDIUM on adopt/no-adopt — carries `named-graphify.md`'s still-open
flag: **the graphify seed/build cadence is an unratified P2; do not spend build
tokens without Ray's explicit go.** The bi-temporal-staleness gap (G1) is the one
finding that could, in principle, tip a future high-scale deployment toward Zep —
but not at our host-only/periodic scale.

---

## GitHub repos touched

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — subject; read installed 0.9.17 wheel source (`serve.py`, `analyze.py`, `ingest.py`, `llm.py`, `watch.py`, `cli.py`, `reflect.py`, `manifest_ingest.py`) + ran the CLI read-only.
- [getzep/graphiti](https://github.com/getzep/graphiti) — closest competitor; README on episodes/provenance, bi-temporal invalidation, group_id, MCP server.
- [mem0ai/mem0](https://github.com/mem0ai/mem0) — README + OpenMemory MCP (local Qdrant+Postgres) multi-level memory, temporal reasoning, ADD-only.
- [microsoft/graphrag](https://github.com/microsoft/graphrag) — via microsoft.github.io/graphrag docs; global/local search, batch indexing pipeline, LLM-heavy.
- [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) — `src/memory` reference server (entities/relations/observations, JSONL, no provenance) — the one already in our `.mcp.json`.
- [topoteretes/cognee](https://github.com/topoteretes/cognee) — README; ECL pipeline, graph+vector, tenant isolation/OTEL lineage, MCP, Postgres+pgvector.
- [letta-ai/letta](https://github.com/letta-ai/letta) — docs.letta.com; memory blocks + archival(vector), self-editing, MCP; not a KG.
- [run-llama/llama_index](https://github.com/run-llama/llama_index) — PropertyGraphIndex docs (developers.llamaindex.ai); multi-retriever, incremental insert, provenance/confidence dev-added.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo: prior `named-graphify.md` teardown, `.mcp.json` (incumbent memory server), `.claude/rules/use-tool-builtins.md` gate.
