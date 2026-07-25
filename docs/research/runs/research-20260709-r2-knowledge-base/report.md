# Run G — Knowledge Base for Research Artifacts + Agent Memory (graphify et al.)

Domain: `docs/research/runs/research-20260709-r2-knowledge-base/`. Five angle
reports (graphify-deep, memory-field, plugins-native, industry-wiring,
repo-fit-design), cross-checked against a 3-vote adversarial verification
pass that reached CONFIRMED on 8 of 10 selected load-bearing claims before
running out of usage credits on the final two claims' verifier lenses and
the synthesize step (see "Refuted / unverified claims" below — those two
are treated as **unverified-by-credit-exhaustion**, not refuted, per the
run's own evidence). Repo baseline: R2 inventory report
(`docs/research/runs/research-20260709-r2-inventory/report.md`).

## Executive summary — the recommendation

**Keep markdown + grep as the retrieval substrate. Adopt graphify as a
periodic, gated synthesis/audit layer whose outputs are committed markdown/
HTML/JSON, never the hot retrieval path. Defer every standalone agent-memory
server (graphiti, mem0, cognee, basic-memory, semtools) behind a named,
observable trigger. Close the one real gap the corpus has today — it has no
index — with a small, python-native, hk-enforced generator.** This is not a
compromise position; it is what the strongest and most current evidence in
this run converges on independently from four different angles (Anthropic's
own doctrine, both leading agentic-coding vendors' product history, two
2026 academic papers, and this repo's own already-encoded conventions).

| Candidate | Verdict | Why |
|---|---|---|
| **markdown + grep + conventions (baseline)** | **Adopt / keep as primary** | Evidence-backed default: Anthropic's context-engineering doctrine, Claude Code's and Sourcegraph Cody's abandonment of pre-built indexes, and two 2026 papers (arXiv:2605.15184, arXiv:2602.23368) all land here for this exact workload shape (small, frequently-changing technical-markdown corpus). CONFIRMED 3/3. |
| **Corpus INDEX.md + front-matter + hk validator ("Candidate A")** | **Build now** | Completes an enforcement gap two existing rules (`research-repo-enumeration.md`, `agent-report-persistence.md`) already promise but don't machine-check; ~1 PR, zero recurring cost, zero new tools. |
| **Graphify (Graphify-Labs/graphify)** | **Adopt as a periodic synthesis/audit layer, gated by a one-run pilot** — NOT as the live query path | It genuinely is a queryable, deterministic, zero-LLM-at-query-time KB (CONFIRMED 3/3) — the framing question's "periodic tool vs. queryable KB" is a false dichotomy — but its build-time ingest of an all-prose corpus is 100% LLM-mediated (CONFIRMED 3/3), and the industry's own cost lesson (Microsoft's GraphRAG → LazyGraphRAG) says defer that LLM cost to periodic/on-demand synthesis, not the hot path. |
| **graphiti (getzep)** | **Defer** | Heaviest infra (graph DB server), mandatory LLM+embedding key, no CLI — none of which this corpus needs. |
| **mem0** | **Reject** for this use | Conversational-preference memory, not a document KB; own README concedes its headline benchmark wins are platform-only, not OSS. |
| **cognee** | **Defer** | Lightest-infra graph contender (embedded Kuzu+LanceDB+SQLite, real `cognee-cli`) but still needs an LLM key this repo deliberately doesn't provision, plus a deliberate build step per corpus change. Re-evaluate only if a queryable graph — not just synthesis — becomes a demonstrated need. |
| **basic-memory** | **Defer / optional convention alignment** | Closest philosophical fit (plain markdown as source of truth, real CLI, no LLM key) but adds a second retrieval surface with no demonstrated grep failure to justify it; consider only as an authoring-convention upgrade (frontmatter/wikilinks) later. |
| **semtools** | **Pre-approved escape hatch, not adopted now** | Zero-key, zero-server, CLI-native local embeddings — the correct first move *if and when* grep starts missing on synonym/conceptual queries. No architectural change needed to adopt later. |
| **claude-plugins-community memory plugins (claude-mem, agent-knowledge, agent-recall)** | **Reject** | Every one with real retrieval ships it as a plugin-bundled MCP server — the exact context-tax the `no_mcp_registration` rule exists to prevent, even though plugin install technically bypasses the CLI's `mcp add` subcommand. `auto-memory` (the one MCP-free plugin) is CLAUDE.md maintenance, not retrieval, and Ray already evaluated and disabled it. |
| **`@modelcontextprotocol/server-memory`** | **Reject** | Source-verified (`src/memory/index.ts`): unranked case-insensitive substring search over a single JSONL file that's fully re-parsed on every call and returned in full on `read_graph` — an anti-pattern at multi-hundred-artifact scale, and the README positions it as a reference/demo, not a production KB. |
| **Native Claude Code auto-memory (`MEMORY.md`)** | **Keep as-is, for what it is** | Machine-local, not git-synced — can't be the corpus store (Ray's Mac and this remote container would never share it) — but its *shape* (bounded always-loaded index + lazy on-demand topic files) is exactly the shape Candidate A should copy for the tracked research corpus. |

The no-MCP-registration constraint the brief flags as a hard design
constraint turned out, on investigation, to be a **non-issue for every
serious candidate** (CONFIRMED 3/3 for graphify specifically): plain CLIs
exist for graphify, basic-memory, cognee, and semtools, and any MCP-shaped
tool can run as a one-shot stdio process under `mcp2cli` — the exact shape
the repo's `.claude/skills/mcp2cli/SKILL.md` already documents. The
constraint only bites the claude-plugins-community memory plugins, which
bundle their own MCP servers as the *plugin's* wiring, not something this
repo would register itself.

---

## Q1 — Is graphify a queryable agent-time KB or a periodic synthesis tool?

**Answer: both, and the distinction the brief poses is a false dichotomy —
build time is (partly) LLM-mediated synthesis; query time is 100%
local/deterministic retrieval.** All four sub-claims below are CONFIRMED
3/3 by independent adversarial verification against primary sources
(`Graphify-Labs/graphify` @ branch `v8`, cross-checked at HEAD and against
the live GitHub API on 2026-07-10).

- **Query surface is local, deterministic BFS/DFS with zero LLM
  round-trips.** `graphify/serve.py` loads a NetworkX graph from
  `graph.json` via `json_graph.node_link_graph` and answers
  `query_graph`/`get_node`/`get_neighbors`/`shortest_path`/`god_nodes`/
  `graph_stats` purely via trigram-indexed BFS/DFS traversal; the module's
  imports contain no LLM client. The CLI (`graphify query "<question>"`,
  `graphify path A B`, `graphify explain "Node"`) hits the same fast path:
  if `graphify-out/graph.json` exists, answer without rebuilding. The one
  nuance surfaced by all three verifier passes: the PR-triage tools
  (`list_prs`/`get_pr_impact`/`triage_prs`) shell out to the GitHub API, so
  "local" isn't absolute for that narrow tool subset — the core
  query/path/explain surface is unaffected.
- **Ingestion is genuinely arbitrary-markdown-native**, not a degenerate
  case: `.md .mdx .qmd .html .txt .rst(.yaml .yml in newer releases)`, with
  wikilinks and file references becoming `EXTRACTED` graph edges
  (`docs/how-it-works.md` @ v8, `graphify/extractors/markdown.py`). But
  **all markdown/PDF/media content goes through Pass 3, the LLM semantic
  extraction pass** — "code files are not sent to the LLM semantic
  extractor in the normal pipeline," but markdown always is. For this
  repo's 100%-prose research corpus, that means the *entire* ingest is the
  LLM-priced pass, bounded only by SHA256 content-hash incremental caching
  (`--update` re-extracts only changed files; `--cluster-only` re-clusters
  without re-extraction).
- **Storage is plain files, no daemon.** `graphify-out/{graph.json (NetworkX
  node-link, relative paths re-anchored on load, git union-merge driver),
  GRAPH_REPORT.md, graph.html, cost.json}`. Neo4j/FalkorDB/Obsidian exports
  are opt-in flags, gated in `pyproject.toml [project.optional-dependencies]`
  — core deps are only networkx/numpy/rapidfuzz/tree-sitter grammars.
  Adoption adds **zero server infrastructure** to this repo.
- **The no-registration fit is real, not incidental.** The MCP server
  (`graphify-mcp` / `python -m graphify.serve graph.json`) defaults to
  `--transport stdio`, is engineered for context efficiency (default
  2000-token/~6KB budget, compact `NODE`/`EDGE` text lines,
  `source_location` citations, a P99 hub-degree guard against BFS/DFS
  explosion through highly-connected nodes) — exactly the `mcp2cli`
  process-spawn shape, no CLI registration needed. One evidence nit
  surfaced by all three verifiers: the literal phrase "no LLM round-trips
  during query" / "no registration; runs one-shot" does not appear verbatim
  in `serve.py` — it's a fair paraphrase of the stdio-default,
  per-invocation-spawn behavior, not a misquote of substance.
- **A closed-loop agent work-memory feature already exists inside
  graphify** and directly overlaps this run's "memory" question:
  `graphify save-result --outcome useful|dead_end|corrected` writes
  outcome-tagged Q&A markdown to `graphify-out/memory/`; `graphify reflect`
  aggregates them into a deterministic `LESSONS.md` plus a
  `.graphify_learning.json` overlay sidecar (preferred/tentative/contested
  verdicts, provenance, content-fingerprint staleness flags — "code
  changed — re-verify"), surfaced as display-only hints in
  `explain`/`query`/MCP output/`GRAPH_REPORT.md`/the HTML viewer.
  Structural graph truth is deliberately kept separate from the overlay
  (no `learning_*` fields feed back into traversal) to avoid
  self-reinforcing feedback loops. Shipped in released versions (v0.8.47,
  v0.9.3), not experimental.
- **Maturity is a real caveat, not disqualifying.** ~81.7k stars / 8k forks,
  MIT, created 2026-04-03 (~3 months old at write time), 157+ releases at
  near-daily cadence, pre-1.0 (`v0.9.x`), one clearly dominant maintainer
  (`safishamsi`, though verifiers found ~12 distinct recent contributors —
  "dominant," not sole) with `Claude`-co-authored commits throughout. The
  self-published benchmarks (BENCHMARKS.md, single judge model) show real
  recall/cost wins over mem0/BM25 on LOCOMO but only a **tie with dense RAG
  on LongMemEval-S QA accuracy (76%)** — the vendor's own numbers do not
  claim graph retrieval beats a good vector baseline on accuracy; the
  claimed edge is recall, cost, and zero-embedding operation. Because
  every committed artifact is plain markdown/HTML/JSON, exit cost from a
  failed pilot is near zero (`rm -rf docs/research/graph/`).

## Q2 — The agent-memory field (graphiti, mem0, cognee, basic-memory) vs. the grep-first baseline

**The contrarian evidence — grep beats RAG for this workload — is strong,
recent, and CONFIRMED 3/3 across every source checked.**

- **The benchmark evidence commonly cited for these tools cannot justify
  adopting any of them here.** LoCoMo is vendor-contested three times over
  (Zep's claimed 84% → mem0's recalculation 58.44% → Zep's corrected
  75.14%, [getzep/zep-papers#5](https://github.com/getzep/zep-papers/issues/5)),
  its conversations are only ~16k–26k tokens — inside modern context
  windows — and, decisively, **Zep's own corrected run showed the
  full-context no-memory baseline (~73%) beating mem0's best result
  (~68%)**. No published benchmark — LoCoMo, LongMemEval, cognee's own
  HotPotQA-family evals — measures retrieval over a *technical research
  markdown corpus*, the exact shape of this workload.
- **Anthropic's own guidance, plus two 2026 papers, converge on the
  opposite prescription.** Anthropic's context-engineering doctrine names
  just-in-time file navigation (lightweight identifiers + glob/grep) and
  structured note-taking (a NOTES.md pattern = this repo's
  `.agent/notepad.md` + `.claude/rules/*.md`) as the primitive, not a vector
  or graph store. arXiv:2605.15184 ("Is Grep All You Need?", May 2026,
  116-question LongMemEval sample across Claude Code/Codex/Gemini-CLI
  harnesses) found grep generally yields higher accuracy than vector
  retrieval, though harness/tool-calling style dominates results more than
  retrieval method. arXiv:2602.23368 ("Keyword search is all you need,"
  Amazon Science) found agentic keyword search reaches >90% of RAG
  performance with no standing vector DB, and is "particularly useful in
  scenarios requiring frequent updates" — this corpus changes every
  session.
- **Per-candidate assessment** (memory-field's independent verdict table,
  corroborated by repo-fit-design's independent re-probe):

  | Candidate | Infra | LLM key needed | CLI (no-MCP fit) | Verdict |
  |---|---|---|---|---|
  | graphiti | Graph DB server (Neo4j/FalkorDB/Neptune) | Yes | None — SDK scripts or mcp2cli only | Defer |
  | mem0 | Local Qdrant/SQLite (lib) or Postgres (server) | Yes (default OpenAI) | None | Reject |
  | cognee | Embedded Kuzu+LanceDB+SQLite | Yes | `cognee-cli` exists | Defer |
  | basic-memory | Local files + SQLite index | **No** | Real CLI (`bm`) | Defer / optional convention |
  | semtools | Local LanceDB, model2vec embeddings | **No** | Real CLI, unix-piped | Pre-approved escape hatch |
  | markdown + grep | none | No | native | **Keep as primary** |

  basic-memory is the philosophically closest fit — "plain text on your
  disk, forever" plus a real CLI (`bm project add`, `bm tool
  search-notes`) — but its knowledge-graph value comes from a note format
  (frontmatter + typed observations + `[[wikilink]]` relations) this
  corpus doesn't use yet; adopting it now means adopting a writing
  convention with no demonstrated retrieval gain over grep, which
  conflicts with `use-tool-builtins.md` / `tool-currency-and-native-first.md`
  rule 6's "written justification required" bar. cognee is the credible
  graph contender on infra-lightness and has a genuine CLI-not-MCP
  philosophy but still requires an LLM key this repo deliberately doesn't
  provision.

## Q3 — claude-plugins-community + Claude Code native memory surfaces

- **`anthropics/claude-plugins-community`** is a read-only, nightly-synced
  mirror (272★, Apache-2.0) whose `.claude-plugin/marketplace.json` pins
  ~450+ plugins by SHA to external repos. **No plugin in the marketplace is
  built on graphify** (code search 0 hits, corroborated by manifest
  fetches and open-web searches). The KB-shaped candidates found:
  - **claude-mem** (thedotmack) — 86.6k stars, daily-active, 296 releases:
    5-lifecycle-hook tool-call capture, SQLite FTS5 + Chroma vector hybrid,
    3-layer progressive-disclosure retrieval via **MCP tools**. Wrong
    corpus (session tool-call history, not curated research artifacts) and
    the exact schema-injection shape `no_mcp_registration` targets. Already
    in `.claude/settings.json:50` as `claude-mem@thedotmack`, **disabled**.
  - **agent-knowledge** (keshrath) — git-synced markdown KB + SQLite typed
    knowledge graph, hybrid TF-IDF+embedding search — but 7 stars, 6 MCP
    tools, and stale (~3 months since last push). Not viable.
  - **agent-recall** (mnardit) — SQLite KG via MCP tools, 13 stars. Not
    viable.
  - **auto-memory** (severity1) — the **only** MCP-free candidate (hooks +
    Stop-hook agent, maintains CLAUDE.md/AGENTS.md AUTO-MANAGED sections),
    151 stars, actively maintained. It is complementary, not a KB — it
    doesn't retrieve, it writes. Already evaluated and **disabled** in
    `.claude/settings.json:54` (governance risk against the hk-enforced
    `claude_md_size_limit`).
  - **claude-plugins-official** has nothing corpus-shaped beyond
    **claude-md-management**, already enabled (`.claude/settings.json:29`).
  - **Structural point (relevant to the hard constraint):** every plugin
    with real corpus retrieval bundles its own MCP server. Installing such
    a plugin bypasses the CLI's registration subcommand *technically*, but
    reproduces the exact per-conversation schema-injection tax that
    subcommand's ban exists to prevent — so this run treats
    plugin-bundled-MCP retrieval as disqualified in spirit, not just letter.
- **Claude Code native memory surfaces**, mapped as KB candidates (all
  verified against `code.claude.com/docs/en/memory.md`, fetched
  2026-07-09):

  | Surface | Load behavior | Sync | Fits as the corpus store? |
  |---|---|---|---|
  | CLAUDE.md/AGENTS.md | Loaded in full every session, `@imports` also load in full | git-tracked | No — it's the always-paid tax; already hk-capped (`claude_md_size_limit`). Correct role: pointer/index layer only |
  | `.claude/rules/*.md` (`paths:` frontmatter) | Path-scoped rules lazy-load; unscoped rules always load | git-tracked | Partial — real lazy-load primitive, but keyed to code paths not topics; wrong key for a research corpus |
  | Native auto memory (v2.1.59+) | Bounded `MEMORY.md` index (≤200 lines/25KB) always loaded; topic files read on demand | **machine-local**, not git-synced | No as the store (Ray's Mac and this container never share it) — but its shape (bounded index + lazy topic files) is exactly what Candidate A below should copy |
  | Skills | Load only on trigger/invocation | git-tracked | Yes for procedural knowledge (already used this way); wrong shape for findings/evidence artifacts |
  | `@modelcontextprotocol/server-memory` | On-request MCP tools, no auto-load | Single JSONL, fully re-parsed every call | No — source-verified as unranked substring search over a whole-file re-read; README positions it as reference/demo |
  | OMC notepad + `project-memory.json` | As-you-go via MCP tools | worktree-local, `.agent/**` committable | No — session-scale, not corpus-scale; correct role is the working layer that *feeds* the corpus |

  **Anthropic's own first-party memory tool** (`memory_20250818`, GA on
  the Messages API) is a directory of files with view/create/str_replace/
  insert/delete/rename — no graph, no embeddings, no query language,
  explicitly framed as "just-in-time context retrieval." Every first-party
  Anthropic memory surface converges on "structured files + bounded index
  + lazy read." This repo's existing architecture already matches that
  shape; what it's missing is the *bounded always-loaded index* discipline
  native auto memory gets for free.

## Q4 — How major projects wire KBs into coding agents

Four converging, independently-sourced patterns, all CONFIRMED at
high confidence:

1. **Both leading agentic-coding vendors abandoned pre-built retrieval
   indexes for live file search.** Claude Code's creator (Boris Cherny, via
   third-party quotes) said early RAG-with-vector-DB was dropped because
   agentic grep "outperformed it by a lot" — precision, freshness, zero
   index maintenance; Anthropic's own 2026-05-14 guidance states plainly
   that a pre-built index "reflects the codebase as it previously existed
   weeks, days, or even hours before." Sourcegraph independently removed
   embeddings from Cody in favor of its native code-search platform, citing
   the same freshness/scale tradeoffs. The counterexample, GitHub Copilot,
   *kept* embeddings — but only because it operates a managed cloud index
   amortized across millions of repos, economics that don't exist for a
   solo maintainer.
2. **llms.txt's real lesson is the shape, not the filename**: a
   hand-curated, one-line-per-entry markdown index at a stable path, with
   every leaf fetchable as clean markdown. This repo already runs the
   *consumer* side (`docs/research/mintlify-cache/**` for 16 repos,
   indexed by `docs/research/mintlify-catalog.md`) but has no equivalent
   index for its *own* internal research corpus.
3. **Instruction-file layering converged cross-vendor**: small always-on
   root + nearest-file overrides + conditional/scoped loading (AGENTS.md,
   Cursor's four activation modes, Anthropic's "pointers only" root-file
   guidance). This repo's AGENTS.md-root + per-directory AGENTS.md +
   hk-enforced size cap + `.claude/rules/*.md` already implements this;
   the missing piece is explicit tiering for research artifacts
   specifically (they should never be always-on context).
4. **Microsoft's GraphRAG → LazyGraphRAG trajectory is the direct cost
   lesson for the graphify decision.** Full LLM-built knowledge graphs hit
   real-world indexing costs Microsoft itself reported near $33,000 for
   large enterprise datasets; LazyGraphRAG (Microsoft Research,
   2024-11-25) replaced LLM indexing with local NLP extraction and
   deferred all LLM summarization to query time, landing "0.1% of the
   costs of full GraphRAG" at comparable global-search quality and >700x
   lower query cost. Graph structure's real value concentrates in
   global/thematic questions over a corpus, not point lookups — and the
   economically sound way to get it is periodic/lazy synthesis, exactly
   graphify's Candidate-B slot below, never a continuously-maintained
   live index.

---

## Recommended KB architecture

### Layer 1 (build now) — Corpus INDEX + front-matter + hk validator

Directly closes the one real gap this run's own repo-fit characterization
found: **the internal research corpus has no index at all**, while the
external mintlify cache does (`docs/research/mintlify-catalog.md`). This
repo already mandates the two conventions an index needs — cache-first
grep (`research-doc-sources.md` step 0) and a per-artifact `## GitHub
repos touched` enumeration (`research-repo-enumeration.md`) — but has no
machine check that either is honored at corpus scale, and
`research-repo-enumeration.md`'s own "Enforcement" section anticipates
exactly this gap ("a future commit can add an hk step... when the first
tracked research artifact lands" — it landed; the step still doesn't
exist).

- `docs/research/INDEX.md` (llms.txt-shaped: H1, summary, then one line
  per artifact — title/date/run-slug/one-sentence claim scope), generated,
  not hand-maintained.
- YAML front-matter on new research artifacts (`date`, `run`, `status:
  working|tracked|superseded`, `topics: []`, `repos: []`), added to the
  report template used by research-launching skills; existing artifacts
  grandfathered.
- Generator + validator live in `python/` (zero-bash-logic invariant):
  `dotfiles-setup research index` / `dotfiles-setup research validate`,
  wired as `mise run research-index` (per `mise-tasks-only.md`) and as an
  hk step reusing the whole-tree-grep idiom already used by
  `claude_md_size_limit` (`hk.pkl:322`) and `no_mcp_registration`
  (`hk.pkl:301-303`) — CI-local parity for free.
- Rule patches: `research-doc-sources.md` gains a step 0.5 ("grep the
  corpus INDEX before corpus-wide grep"); `agent-report-persistence.md`
  gains "regenerate INDEX.md in the same commit that adds an artifact."

Cost: one PR. Recurring cost: zero LLM, zero network. Token cost per
session: a few hundred lines at most, loaded only on demand (never
always-on — matching the native-auto-memory shape from Q3 and the Cursor
"tier 4: manual" discipline from Q4).

### Layer 2 (gated pilot) — graphify as periodic synthesis/audit

On the Mac (the `/graphify` skill is user-level, confirmed absent in the
remote container — inventory report:109-111), on a cadence — after a
research run, or monthly, never live:

1. Run graphify over `docs/research/` + `docs/research/runs/`, **excluding
   `mintlify-cache/`** (its ~75,400 lines of third-party docs would
   dominate the LLM semantic pass for zero synthesis value).
2. Read `cost.json` for the real per-run token cost (no published figure
   exists for prose-only corpora; the LOCOMO $1.40 number is
   conversational-data, not comparable). The `claude-cli` backend runs on
   Ray's subscription with no API key — consistent with this repo's
   deliberate absence of `ANTHROPIC_API_KEY`.
3. Go/no-go: judge `GRAPH_REPORT.md` against ~10 real "what connects /
   what recurs across our research?" questions the INDEX alone can't
   answer.
4. If go: commit `docs/research/graph/{GRAPH_REPORT.md, graph.html,
   graph.json}` (verified safe to commit — relative re-anchored paths +
   git union-merge driver), add a `.gitattributes` entry for the merge
   driver, wrap invocation in `mise run research-graph` (thin wrapper,
   logic stays in the tool per zero-bash-logic), and index the outputs in
   `INDEX.md` per Layer 1.
5. If no: drop with zero residue — everything graphify touches is plain
   markdown/HTML/JSON.

**Do not** wire graphify's MCP server or CLI into the hot day-to-day
retrieval path regardless of pilot outcome — that's the LazyGraphRAG
lesson from Q4, and it's what would turn a cheap periodic synthesis into
the cost/staleness profile the field already abandoned. The
`save-result`/`reflect` agent work-memory loop (Q1) is a further later
opt-in, not part of this pilot.

### Layer 3 (deferred, named triggers) — semtools / basic-memory / cognee

Record the trigger explicitly rather than leaving "defer" open-ended:
*when the corpus INDEX + grep demonstrably misses on ≥N synonym/
conceptual queries per month (an observational threshold — no literature
boundary exists for this corpus size), adopt semtools first* (no key,
CLI-native, afternoon-scale, zero architecture change — local model2vec
embeddings via a LanceDB workspace that auto-re-embeds changed files).
Consider basic-memory only if wikilink traversal/typed relations become a
wanted *authoring* convention independent of retrieval. Reject mem0
outright (wrong workload). Defer graphiti and cognee behind the same
"demonstrated need for a queryable graph, not just synthesis" bar
graphify's pilot will have already answered.

### The specialized agent that reads/writes this KB

A `research-librarian` role (or an equivalent skill invoked by existing
research-launching skills), with three responsibilities, each mapped to
one of the layers above:

1. **At artifact-persist time** (mechanical, no LLM judgment beyond a
   one-line description): write front-matter, append the `## GitHub repos
   touched` enumeration (already required), regenerate `INDEX.md`. This is
   what `mise run research-index` / the hk validator enforce; the agent's
   job is to call it, not hand-roll it.
2. **At retrieval time**: two-hop lookup — grep `INDEX.md` first, then
   `Read` the named artifact(s); fall back to full-corpus grep only when
   the index doesn't resolve the question. Never load more than the
   artifacts a question actually names — the same just-in-time discipline
   Anthropic's context-engineering doctrine prescribes (Q2) and what the
   native auto-memory `MEMORY.md` pattern already does natively (Q3).
3. **At synthesis time** (cadence-gated, Layer 2 only): seed load is
   `INDEX.md` + the previous `GRAPH_REPORT.md` + `.agent/notepad.md` — a few
   hundred lines total instead of re-reading dozens of full reports —
   then drive the graphify run and distill anything durable into
   `.claude/rules/*.md` via the existing curation pipeline
   (`agent-artifact-conventions.md` rule 5).

### Migration order

1. **Corpus-boundary decision (needs Ray — flagged below, not resolved
   here per `clarify-before-acting.md`):** decide whether durable run
   outputs get promoted to `docs/research/runs/<slug>/` while agent
   working files stay per-clone in `docs/research/runs/`, so the KB has one
   canonical, clone-portable corpus rather than today's split (Ray's Mac
   has a 104-agent historical run invisible to fresh clones).
2. **PR 1 — Layer 1** (index + front-matter + validator + rule edits).
3. **Pilot — Layer 2** (graphify, Mac-only, manual go/no-go).
4. **Standing review**: fold "prune stale INDEX entries + rules" into the
   existing tool-currency cadence — Anthropic recommends a config review
   every 3–6 months, especially after model releases.

---

## Refuted / unverified claims

Nothing in this run's 10 selected load-bearing claims was genuinely
refuted by evidence. Two entries in the verification output require a
different label than their raw verdict field shows, because the run
exhausted usage credits partway through the adversarial-verify phase
(the run's own logs: "You're out of usage credits" on `verify:8` and
`verify:9` lenses and the final `synthesize` step):

- **"Graphify can ingest an arbitrary local markdown corpus and produce
  clustered knowledge-graph outputs, invocable as a CLI without
  registering an MCP server."** Verdict shown: CONFIRMED, but with only
  **1 of 3 verifier lenses actually run** (correctness passed; recency and
  source-quality both credit-failed before returning a verdict). Treat as
  **CONFIRMED but thin** — fully corroborated in substance by two other
  claims in this same run that *did* receive full 3/3 votes
  (ingestion-is-markdown-native and no-MCP-registration-is-a-non-issue),
  so no material risk attaches to relying on it.
- **"Anthropic's own context-engineering guidance recommends
  file-system/grep-based agentic retrieval over embedding-based RAG for
  coding agents in most cases."** Verdict shown: **REFUTED, 0/3 votes** —
  but the notes array is empty and all three verifier lenses for this
  claim credit-failed before producing any judgment. **This is not a
  refutation; it is an unscored claim.** Reclassify as **UNVERIFIED**. It
  is, in substance, a near-duplicate of a different claim in this same run
  that *did* receive full adversarial scrutiny and passed 3/3 — "Recent
  evidence directly supports the repo's existing grep-first architecture,"
  which cites the identical Anthropic source
  (anthropic.com/engineering/effective-context-engineering-for-ai-agents,
  2025-09-29) alongside arXiv:2605.15184 and arXiv:2602.23368, all three
  independently verified against primary text.

No other claim across the five angle reports' 30 collected claims shows a
genuine adversarial refutation. Angle-report-level caveats worth
preserving: graphify's "one dominant maintainer" framing is directionally
right but recent commit history shows ~12 distinct contributors; the exact
phrase "no LLM round-trips during query" was not found verbatim in
graphify's source (the *substance* is independently confirmed by reading
`serve.py`); and mem0's "abandoned graph layer" claim rests on one
practitioner analysis, not a code-verified audit.

## Open questions for Ray

1. **Corpus boundary**: should durable run outputs (`report.md`,
   `synthesis-*.md`) be promoted into a new `docs/research/runs/<slug>/`
   tracked location, leaving `docs/research/runs/` purely as per-clone agent
   working files? *Recommended: yes* — without it, the historical
   104-agent run on your Mac stays invisible to fresh clones, and the
   INDEX (Layer 1) can only index what a given clone happens to have.
2. **Graphify pilot cadence**: after every research run, or monthly? The
   `claude-cli` backend needs no API key but does need your subscription
   and a Mac session (the skill is user-level, absent in remote
   containers). *Recommended: monthly or on-demand*, not per-run — matches
   the LazyGraphRAG "periodic, not live" economics.
3. **Go/no-go threshold for the graphify pilot**: a cost ceiling from
   `cost.json`, a qualitative bar on `GRAPH_REPORT.md`'s answers, or both?
   *Recommended: both, informal* — no published number exists for this
   workload.
4. **INDEX.md granularity**: one index for the whole corpus, or one per
   layer (`docs/research/INDEX.md` + a separate per-clone
   `docs/research/runs/INDEX.md`)? *Recommended: the split* — matches the
   existing committed/gitignored-per-clone split.
5. **Semtools trigger**: track the "grep+INDEX is missing queries" trigger
   informally or in a concrete miss-log? *Recommended: informal for now* —
   a miss-log is one more artifact to maintain for a trigger unlikely to
   fire soon at this corpus size.

## GitHub repos touched

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — subject of the deep review: ingestion, query surface, storage model, maturity, work-memory loop, benchmarks (README, docs/how-it-works.md, graphify/skill.md, graphify/serve.py, graphify/reflect.py, CHANGELOG.md, BENCHMARKS.md, pyproject.toml).
- [getzep/graphiti](https://github.com/getzep/graphiti) — bi-temporal graph-memory candidate: infra, LLM dependency, maturity, deferred verdict.
- [getzep/zep-papers](https://github.com/getzep/zep-papers) — issue #5, the LoCoMo score-correction dispute underpinning the "benchmarks are unreliable" finding.
- [mem0ai/mem0](https://github.com/mem0ai/mem0) — conversational-preference memory candidate: OSS/platform split, default stack, rejected verdict.
- [topoteretes/cognee](https://github.com/topoteretes/cognee) — embedded graph-memory candidate: Kuzu+LanceDB+SQLite defaults, cognee-cli, deferred verdict.
- [basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory) — markdown-native memory candidate: CLI, no-key core ops, note-format requirement for graph value.
- [run-llama/semtools](https://github.com/run-llama/semtools) — local-embedding CLI escape-hatch candidate.
- [AnswerDotAI/llms-txt](https://github.com/AnswerDotAI/llms-txt) — llms.txt spec origin; the INDEX.md format this run's architecture borrows.
- [microsoft/graphrag](https://github.com/microsoft/graphrag) — full GraphRAG vs. LazyGraphRAG cost lesson anchoring graphify's periodic-synthesis role.
- [sveltejs/svelte](https://github.com/sveltejs/svelte) — llms.txt adoption precedent by a major OSS framework.
- [openai/agents.md](https://github.com/openai/agents.md) — AGENTS.md spec and nearest-file monorepo loading semantics.
- [sourcegraph/cody-public-snapshot](https://github.com/sourcegraph/cody-public-snapshot) — Cody's removal of embeddings in favor of native code search.
- [anthropics/claude-plugins-community](https://github.com/anthropics/claude-plugins-community) — community plugin marketplace mirror; enumerated for memory/KB-relevant plugins.
- [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) — official marketplace; confirmed no KB/graph plugin beyond claude-md-management.
- [severity1/claude-code-auto-memory](https://github.com/severity1/claude-code-auto-memory) — the one MCP-free memory plugin (CLAUDE.md maintenance, not retrieval); already disabled in this repo.
- [thedotmack/claude-mem](https://github.com/thedotmack/claude-mem) — largest community memory plugin; session-observation memory with MCP retrieval layer, rejected for wrong corpus + integration shape.
- [keshrath/agent-knowledge](https://github.com/keshrath/agent-knowledge) — markdown+graph KB plugin candidate; rejected for stale/tiny + MCP-required.
- [mnardit/agent-recall](https://github.com/mnardit/agent-recall) — SQLite knowledge-graph plugin candidate; rejected for tiny + MCP-required.
- [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) — reference "memory" MCP server; source-verified as unranked substring search over a whole-file JSONL, rejected as an anti-pattern at scale.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo: rules, hk.pkl steps, mise tasks, mintlify catalog/cache, `.claude/settings.json` plugin state, and the R2 inventory baseline grounding every recommendation.
