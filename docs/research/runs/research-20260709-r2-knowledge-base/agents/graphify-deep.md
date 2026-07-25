# Graphify-Labs/graphify — deep review (Run G, angle #1)

Date: 2026-07-09 (remote research container; Bash unavailable — all evidence via
GitHub search API/MCP, raw.githubusercontent.com fetches, and github.com page
fetches). Repo under review: <https://github.com/Graphify-Labs/graphify>.

## Executive answer to the framing question

**Graphify is BOTH a periodic synthesis tool AND a queryable agent-time KB — and
the query side is deterministic and local.** Build time uses LLM extraction only
for non-code content (markdown, PDFs, media); query time (`graphify query/path/
explain`, plus an optional stdio MCP server) is pure BFS/DFS traversal over a
NetworkX `graph.json` with zero LLM round-trips. It additionally ships a
first-class **agent work-memory loop** (`save-result` → `reflect` →
`.graphify_learning.json` overlay surfaced in query output) that directly
overlaps the domain's "agent memory" requirement. Its stdio/one-shot MCP mode
and plain CLI mean it fits the repo's no-registration constraint (mcp2cli
process-spawn or direct CLI) without any workaround.

## Findings

### 1. What it is / positioning

- Repo description: "AI coding assistant skill (Claude Code, Codex, OpenCode,
  Cursor, Gemini CLI, and more). Turn any folder of code, SQL schemas, R
  scripts, shell scripts, docs, papers, images, or videos into a queryable
  knowledge graph." Topics include `graphrag`, `knowledge-graph`, `leiden`,
  `tree-sitter`, `claude-code`, `skills`. Homepage <https://graphifylabs.ai/>.
  (GitHub repo metadata via search API, 2026-07-10.)
- README core promise: "Type `/graphify` in your AI coding assistant and it
  maps your entire project (code, docs, PDFs, images, videos) into a knowledge
  graph you can query instead of grepping through files."
  (README.md @ v8 branch.)
- Distribution: PyPI package **`graphifyy`** (note double-y), v0.9.12 in
  `pyproject.toml`; install `uv tool install graphifyy && graphify install`;
  entry points `graphify` (CLI) and `graphify-mcp` (server). Supports 20+
  assistants via platform-specific skill installs. (README.md; pyproject.toml
  @ v8.)

### 2. Ingestion — yes, arbitrary markdown and directories

- Input formats (README.md @ v8): code in ~36 languages via tree-sitter;
  structured data (JSON/YAML/manifests/Terraform); **documentation: "Markdown,
  MDX, HTML, reStructuredText, plain text, with wikilinks and file references
  becoming graph edges"**; media (PDF/images/video/audio via transcription);
  Google Workspace files.
- Invocation is directory-oriented: `/graphify .`, `/graphify ./docs --update`,
  `graphify clone <github-url>`, `graphify add <url>` (fetch URL into corpus).
  (README.md command examples; graphify/skill.md.)
- A markdown-only research corpus (this repo's case) is a supported, not
  degenerate, input: markdown goes through the semantic (LLM) extraction pass;
  wikilinks/file references become EXTRACTED edges. Code files are explicitly
  NOT sent to the LLM ("code files are not sent to the LLM semantic extractor
  in the normal pipeline", docs/how-it-works.md @ v8).

### 3. Pipeline

Three passes (docs/how-it-works.md @ v8):

1. **Local, no LLM**: tree-sitter AST extraction of classes/functions/imports/
   call graphs/inline comments; deterministic SQL table/view/FK extraction.
   Inline `# NOTE:` / `# WHY:` / `# HACK:` comments become graph nodes
   (README.md).
2. **Local**: faster-whisper transcription for media, seeded by current god
   nodes; cached.
3. **LLM-powered**: markdown/PDF/image/transcript content processed by "Claude
   subagents ... in parallel, outputting JSON fragments that merge into the
   unified graph."

Then: graph construction with edge lineage tags — `EXTRACTED` (confidence 1.0),
`INFERRED` (0.55–0.95 rubric), `AMBIGUOUS` (flagged) — and **Leiden community
detection** ("no embeddings needed"; `leiden` is an optional extra in
pyproject.toml). Hyperedges (3+ node group relations) live in
`G.graph["hyperedges"]`. (docs/how-it-works.md.)

Incremental: content-addressed SHA256 caching — re-runs skip unchanged files;
`--update` re-extracts only changed files; `--cluster-only` re-clusters without
re-extraction; a manifest (`.graphify_root`) tracks the corpus. Shrink guard
(#479) refuses to overwrite `graph.json` with a smaller graph without
`--force`. (docs/how-it-works.md; graphify/skill.md.)

### 4. Storage model — files, not a server

- **File-based by default**: `graphify-out/` holds `graph.json` (NetworkX
  node-link JSON: nodes with `id/label/file_type/source_file`; edges with
  `source/target/relation/confidence/confidence_score`), `GRAPH_REPORT.md`
  (god nodes, surprises, suggested questions — the audit output),
  `graph.html` (self-contained interactive viz), plus `cost.json` (cumulative
  token tracking), `.graphify_labels.json` (community names), and
  `graphify-out/memory/` (Q&A outcome docs — see §6).
  (README.md "Storage Model"; docs/how-it-works.md; graphify/skill.md output
  structure.)
- `graph.json` paths are relative and re-anchored on load — "safe to commit
  alongside code"; a **git union-merge driver** for graph.json handles parallel
  commits. (README.md.)
- Optional exports, not required: Obsidian vault, wiki, Neo4j/FalkorDB cypher
  push (`--neo4j-push`/`--falkordb-push`; `neo4j`/`falkordb` optional extras in
  pyproject.toml). There is **no resident database or daemon** in the default
  flow. (README.md; pyproject.toml.)
- Note: `docs/docker-mcp-sqlite.md` is a runbook for a *generic* SQLite MCP
  server in Docker MCP Toolkit — it is NOT graphify's storage; graphify's own
  storage is the JSON file set above.

### 5. Query/retrieval surface — deterministic, local, context-budgeted

- CLI: `graphify query "<question>"`, `graphify path "A" "B"`,
  `graphify explain "Node"`, `graphify export callflow-html` (Mermaid).
  (README.md.)
- The skill file states query semantics explicitly: "Queries are **local and
  deterministic** — they traverse the in-memory graph using BFS (broad context)
  or DFS (trace specific paths). Vocab-expansion aligns user wording to graph
  node IDs before traversal. Query results cite `source_location` ... **No LLM
  round-trips during query.**" Fast-path rule: if `graphify-out/graph.json`
  exists, answer questions via `graphify query` without rebuilding.
  (graphify/skill.md @ v8.)
- MCP server (`python -m graphify.serve graph.json` / `graphify-mcp` entry
  point): **stdio transport by default (one-shot, "no registration; runs
  one-shot, connects to caller's stdin/stdout")** plus streamable-HTTP for
  team-shared mode with optional API key. 11 tools: `query_graph`, `get_node`,
  `get_neighbors`, `get_community`, `god_nodes`, `graph_stats`,
  `shortest_path`, `list_prs`, `get_pr_impact`, `triage_prs`.
  (graphify/serve.py @ v8.)
- **Context-efficiency is engineered, not incidental** (graphify/serve.py):
  responses are compact `NODE ... [src= loc= community= learning=]` /
  `EDGE A --relation [confidence]--> B` text lines; **default token budget
  2000 (~6KB) per query, configurable**, truncating with a
  `… (truncated)` footer; trigram index pre-filters candidate nodes; a P99
  hub-degree threshold blocks BFS/DFS explosion through god nodes;
  LLM-derived fields are sanitized against prompt injection (F-010).
- Hot-reload: the server watches graph.json (mtime,size) and reloads — but for
  this repo's constraint the relevant mode is **stdio one-shot**, which is
  exactly the mcp2cli process-spawn shape; the plain CLI needs no MCP at all.

### 6. Agent work-memory loop (directly relevant to Run G's memory question)

Graphify ships a closed-loop experiential memory layer (all deterministic at
read time):

- `graphify save-result --type query|path_query|explain --nodes N1 N2
  --outcome useful|dead_end|corrected [--correction TEXT]` writes outcome-
  tagged Q&A markdown docs into `graphify-out/memory/`; outcomes go into
  frontmatter (for deterministic aggregation) AND an `## Outcome` body section
  so the signal "round-trips into the graph on the next semantic
  re-extraction" — "the system grows smarter from both what you add AND what
  you ask." (graphify/ingest.py docstring; graphify/__main__.py help.)
- `graphify reflect` aggregates those outcomes into a deterministic
  `reflections/LESSONS.md`; `--if-stale` makes it a cheap session-start no-op;
  `--graph` groups lessons by community and writes the **work-memory overlay
  sidecar `.graphify_learning.json`** next to graph.json, tagging nodes
  preferred/tentative/contested (recency-weighted, with provenance and a
  content fingerprint of the cited code so stale verdicts are flagged
  "code changed — re-verify"). (README.md `graphify reflect` block;
  CHANGELOG.md work-memory entry; graphify/reflect.py.)
- The overlay is display-only and surfaced everywhere you read: `explain`/
  `query` print a `Lesson:` hint, MCP NODE lines gain `learning=<status>`,
  GRAPH_REPORT.md grows a `## Work-memory lessons` section, the HTML viewer
  shows a colored node ring. Structural truth stays separate (no `learning_*`
  in graph.json); letting verdicts influence traversal is deliberately
  deferred to avoid self-reinforcing feedback. (CHANGELOG.md; graphify/serve.py,
  cli.py, report.py, exporters/html.py comments; tests/test_reflect.py,
  test_serve.py, test_explain_cli.py.)
- A git post-commit hook (`graphify hook install`) auto-rebuilds the code graph
  and refreshes LESSONS.md, but the loop "no longer depends on the git hook" —
  the skill has the agent run `reflect --if-stale` at session start.
  (graphify/hooks.py; CHANGELOG.md.)

### 7. LLM dependencies + cost

- **Zero LLM cost for code-only corpora** (tree-sitter is local). Semantic
  extraction (markdown/PDF/media — i.e., this repo's research corpus) needs an
  LLM via one of: Anthropic API (default model claude-sonnet-4-6), Gemini,
  OpenAI(-compatible), Ollama (local, no key), Bedrock, DeepSeek,
  Kimi/Moonshot, Azure, or **the Claude CLI / host agent itself with no API
  key** ("the host agent itself becomes the LLM"; the skill says never to
  prompt for `ANTHROPIC_API_KEY`). Headless:
  `graphify extract ./docs --backend gemini`. (README.md "LLM Dependencies";
  graphify/skill.md.)
- Core pip deps are only networkx/numpy/rapidfuzz/tree-sitter grammars; every
  LLM provider, leiden, pdf, watch, neo4j etc. are optional extras.
  (pyproject.toml @ v8.)
- Measured ingest cost from the project's own harness: LOCOMO (n=300
  conversational corpus) ingest ≈ **$1.40** vs mem0 $3.48 and supermemory
  $15.67. Token spend is tracked per-run in `cost.json` and reports must "show
  token cost" per the skill's Honesty Rules. Incremental SHA256 caching bounds
  re-ingest cost to changed files. (BENCHMARKS.md; graphify/skill.md.)

### 8. Benchmarks (self-published — treat as vendor numbers)

From BENCHMARKS.md @ v8 (single judge model Kimi K2.6; judge agreement 90.6%,
kappa 0.81; "may not generalize"):

- LOCOMO (n=300): recall@10 **0.497** vs mem0 0.048, BM25 0.362; QA accuracy
  45.3% vs supermemory 49.7%, mem0 27.3%, BM25 31.3% (supermemory recall
  flagged as embedder-confounded).
- LongMemEval-S (n=50): **76% QA accuracy, tied with dense RAG** — i.e., the
  graph does not beat a good vector baseline on QA accuracy; its edge is
  recall, cost, and zero-embedding operation.
- ERPNext ~1M-line code intelligence: coverage 70.8% → 82.0%.

### 9. Maturity signals (as of 2026-07-10)

| Signal | Value | Source |
|---|---|---|
| Stars / forks / watchers | 81,284 / 8,002 / 285 | GitHub API repo object |
| Created | 2026-04-03 — **~3 months old** | GitHub API repo object |
| Last push | 2026-07-09 (yesterday) | GitHub API repo object |
| Releases | **157 releases**, latest v0.9.11 (2026-07-09); ~1–2 per day pace (v0.9.4→v0.9.11 spanned Jul 1–Jul 9) | github.com/…/releases |
| Open issues / PRs | 206 issues + 234 PRs (the API's 440 `open_issues_count` combines both) | issues page vs API field |
| License | MIT | GitHub API license field; LICENSE in root |
| Language | 100% Python; requires ≥3.10 | repo page; pyproject.toml |
| Default branch | `v8` (unusual; versioned branch scheme) | GitHub API |
| Bus factor | ~20+ distinct commit authors in recent history, but **safishamsi dominates** as author/committer on most recent commits; "claude" co-authors nearly every commit (AI-assisted development); org = Graphify-Labs with commercial homepage | commits/v8 page |
| Pre-1.0 | v0.9.x — API/format churn risk is real (e.g., legacy node-ID scheme handling in serve.py, hyperedge key aliasing fixes in CHANGELOG) | pyproject.toml; CHANGELOG.md |

Interpretation: explosive traction (81k stars in 3 months) with very active,
heavily AI-co-authored maintenance concentrated in one primary maintainer;
release cadence is daily-ish bugfix waves focused on per-language extraction
correctness. Not yet 1.0; the on-disk format has documented compat shims.

### 10. Fit against this repo's constraints

- **No-MCP-registration rule**: satisfied three ways — (a) plain CLI
  (`graphify query/path/explain/reflect`), (b) stdio one-shot MCP via
  `graphify-mcp` under mcp2cli process-spawn, (c) never needed for build (the
  `/graphify` skill drives the host agent). No conflict with
  `no_mcp_registration`.
- **Skill already in Ray's toolbox**: the in-repo `graphify/skill.md` matches
  the user-level `~/.claude/skills/graphify/SKILL.md` described in the R2
  inventory (`docs/research/runs/research-20260709-r2-inventory/report.md:109-111`);
  the KB pilot must run on the Mac (skill absent in the remote container).
- **Corpus shape**: `docs/research/runs/**` + `docs/research/**` + `.claude/rules/`
  are markdown → the entire ingest is Pass-3 LLM extraction (the one part that
  costs tokens), then all subsequent retrieval is free/deterministic. The
  mintlify-cache llms-full.txt files are large plain-text — they would inflate
  the semantic pass and should likely be excluded from ingest scope.
- **Committable artifacts**: relative-path graph.json + union merge driver +
  the `.agent/**`-is-committable fact (inventory report :112-116) mean
  `graphify-out/` could live in the repo or a branch.
- **Role verdict this angle supports**: graphify is credible BOTH as periodic
  synthesis/audit (GRAPH_REPORT.md, HTML, communities) AND as an agent-time
  query surface (deterministic, 2000-token-budgeted responses, source-location
  citations). The real adoption question is therefore not "synthesis-only vs
  KB" but whether the *build-time* LLM pass over a growing markdown corpus
  (cost + freshness cadence) beats grep's zero-cost baseline — an evaluation
  for the domain synthesis, not a disqualifier found here.

## Uncertainties / gaps

- **Vendor benchmarks**: LOCOMO/LongMemEval numbers are self-published, single
  judge model, and memory-benchmark-shaped (conversational QA), not
  research-corpus retrieval. No independent replication found in this pass.
- **Bus factor precision**: contributor counts came from a JS-degraded commits
  page ("~20+ authors, safishamsi dominant"); exact distribution unverified
  (api.github.com returned 403 through the session proxy).
- **Markdown ingest cost for THIS corpus**: no per-MB token figure published;
  the $1.40 LOCOMO figure is conversational data. A local pilot on
  `docs/research/` is the only way to get a real number (cost.json will
  report it).
- **Query quality on pure-prose corpora**: vocab-expansion + trigram matching
  is engineered for code symbols; how well node labeling works when the corpus
  is 100% research prose (no AST pass at all) is untested here.
- **Pre-1.0 format churn**: legacy-schema shims exist; a committed graph.json
  may need rebuilds across upgrades. Daily releases cut both ways.
- **`graphifyy` PyPI name**: the double-y package name is confirmed in
  pyproject.toml but I could not fetch the PyPI page to check for
  typosquatting concerns around the obvious `graphify` name.
- The `docs/superpowers/` directory and `node-summaries-rfc.md` were not
  reviewed (fetch budget); node summaries RFC may change the context-efficiency
  story further.

## GitHub repos touched

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — subject of the deep review: README, docs/how-it-works.md, docs/docker-mcp-sqlite.md, pyproject.toml, graphify/skill.md, graphify/serve.py, CHANGELOG.md (via code search), releases/commits/issues pages, repo metadata.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — grounding baseline read from the working tree (`docs/research/runs/research-20260709-r2-inventory/report.md`).
