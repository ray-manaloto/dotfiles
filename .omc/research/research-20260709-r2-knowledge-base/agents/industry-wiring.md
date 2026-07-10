# Run G / Angle 4 — How major projects wire knowledge bases into coding agents

Agent: industry-wiring (research analyst). Date: 2026-07-09.
Scope: survey of how serious orgs/projects give coding agents fast, low-context
knowledge access — llms.txt, Microsoft GraphRAG, Sourcegraph Cody / GitHub
Copilot context engines, Cursor rules/docs, AGENTS.md, Anthropic's own agent
guidance, and OSS agent-facing knowledge shipping — distilled into patterns
applicable to a solo maintainer with a markdown corpus and grep-first rules.

Method note: web research via WebSearch/WebFetch (Bash unavailable this
session); local grounding via Read/Glob against the working tree. Sources are
weighted to the last ~12–18 months; publication dates noted where known.

---

## Findings

### 1. The industry's strongest retrieval signal: the two leading agentic-coding vendors independently converged on live search over pre-built indexes

- **Anthropic (Claude Code)**: Claude Code's creator Boris Cherny stated (Hacker
  News) that early versions used RAG with a local vector database, but "agentic
  search outperformed it by a lot, and this was surprising." Reasons cited:
  precision (grep finds exact matches; embeddings produce fuzzy positives on
  code), freshness (a pre-built index drifts during active editing), simplicity
  (no index to build/maintain), and privacy/security (no embedding pipeline).
  Sources: [vadim.blog analysis with Cherny quotes](https://vadim.blog/claude-code-no-indexing/);
  Anthropic's own ["How Claude Code works in large codebases"](https://claude.com/blog/how-claude-code-works-in-large-codebases-best-practices-and-where-to-start)
  (published 2026-05-14) which states Claude Code "traverses the file system,
  reads files, uses grep" and that with indexes, "by the time a developer
  queries the index, it reflects the codebase as it previously existed weeks,
  days, or even hours before."
- **Sourcegraph (Cody)**: embeddings were "the backbone of Cody's retrieval
  stack since launch," but Sourcegraph **removed embeddings** in favor of its
  native code-search/code-intelligence platform — zero extra config, no code
  sent to an embedding API, scales past 100k-repo codebases where vector search
  became "complex and resource-intensive." Source: Sourcegraph blog
  ["How Cody understands your codebase"](https://sourcegraph.com/blog/how-cody-understands-your-codebase)
  (2024-02-15).
- **The counterexample is instructive**: GitHub Copilot doubled down on
  embeddings — a new code-tuned embedding model (announced Oct 2025) powering
  chat/agent/edit/ask modes with a claimed 37.6% retrieval-quality lift and 8x
  smaller index ([GitHub blog](https://github.blog/news-insights/product-news/copilot-new-embedding-model-vs-code/),
  [InfoQ](https://www.infoq.com/news/2025/10/github-embedding-model/)). But
  Copilot operates a **managed cloud index over millions of repos** — the
  economics that justify an embedding pipeline (amortized across a fleet,
  dedicated infra to keep it fresh) do not exist for a solo maintainer.
- Known tradeoff of grep-first, honestly reported by critics: token burn on
  broad terms and iterative refinement ([Milvus critique](https://milvus.io/blog/why-im-against-claude-codes-grep-only-retrieval-it-just-burns-too-many-tokens.md));
  semantic indexing still wins for "conceptual search across unfamiliar code
  with inconsistent naming" ([vadim.blog](https://vadim.blog/claude-code-no-indexing/)).
  The mitigation both vendors use is not an index — it is **better curated
  entry points** (finding 3) so the agent greps less blindly.

**Takeaway for this repo**: the grep-first rule
(`.claude/rules/research-doc-sources.md` step 0) is not a stopgap — it is the
same architecture the two most successful agentic-coding products landed on
after trying RAG. At `dozens-of-reports` scale, an embedding index would buy
the staleness problem without Copilot-scale amortization.

### 2. llms.txt: modest web adoption, but de-facto standard for *dev-tool* agent-facing docs — and its real lesson is "curated markdown index + per-page .md fetch"

- Origin: proposed by **Jeremy Howard (Answer.AI) on 2024-09-03** — a root
  markdown file giving AI systems a curated index of important content with
  one-line descriptions ([llmstxt.org](https://llmstxt.org/),
  [AnswerDotAI/llms-txt](https://github.com/AnswerDotAI/llms-txt)).
- Adoption is bifurcated: a SE Ranking study of 300k domains found **~10.13%
  adoption**; BuiltWith tracked **844k+ sites** by Oct 2025 — yet **no major
  LLM provider crawler consumes it** (Google's Gary Illyes confirmed non-support,
  July 2025), and it does not measurably improve citation odds in AI search
  ([State of llms.txt 2026](https://presenc.ai/research/state-of-llms-txt-2026),
  [codersera guide, May 2026](https://codersera.com/blog/llms-txt-complete-guide-2026/)).
- Where it *does* work: **coding agents fetching docs on demand**. Cursor,
  Windsurf, Claude Code, Copilot, Cline and Aider all look for
  `/llms.txt` / `/llms-full.txt` when pointed at a docs site (same sources).
  Mintlify auto-generates both files for every hosted site, serves every page
  as markdown via a `.md` suffix, mirrors at `/.well-known/`, and adds
  `Link: </llms.txt>; rel="llms-txt"` discovery headers "so AI tools can
  process content faster and use fewer tokens"
  ([Mintlify docs](https://www.mintlify.com/docs/ai/llmstxt)).
- OSS projects ship agent-facing knowledge natively: **Svelte** publishes
  llms.txt variants ([svelte.dev/docs/llms](https://svelte.dev/docs/llms));
  **FastHTML** goes further with `llms-ctx.txt` / `llms-ctx-full.txt` —
  pre-expanded, XML-structured context bundles generated from llms.txt via the
  `llms_txt2ctx` CLI, explicitly "because FastHTML is newer than most LLMs"
  ([docs.fastht.ml/llms-ctx.txt](https://docs.fastht.ml/llms-ctx.txt),
  [llmstxt.org/intro.html](https://llmstxt.org/intro.html)). Ecosystem demand
  is visible in issues like [vitejs/vite#19400](https://github.com/vitejs/vite/issues/19400).
- This repo already runs the consumer side of this pattern:
  `docs/research/mintlify-cache/**/llms.txt` + `llms-full.txt` for 16 repos
  (verified by glob: jdx/{mise,hk,fnox,mise-env-fnox,pitchfork,pklr,mise-action},
  devcontainers/{cli,spec,features,images}, twpayne/chezmoi, starship/starship,
  wagoodman/dive, knowsuchagency/mcp2cli, yeachan-heo/oh-my-claudecode),
  indexed by `docs/research/mintlify-catalog.md`.

**Takeaway**: the transferable mechanic is not the filename, it is the shape —
**a hand-curated, one-line-per-entry markdown index at a stable path, with
every leaf fetchable as clean markdown**. The internal research corpus
(`.omc/research/**`, `docs/research/**`) currently lacks its own llms.txt-shaped
index; the "GitHub repos touched" sections are a partial, per-artifact one.

### 3. Instruction-file layering became a cross-vendor standard: small always-on root + nearest-file overrides + conditional loading

- **AGENTS.md**: launched Aug 2025, "a README for agents"; adopted by **20k+
  repos within its first month and 60k+ open-source projects by Dec 2025 /
  early 2026**; read natively by Claude Code, Codex CLI, Cursor, Copilot,
  Gemini CLI, Aider, Devin, Windsurf, Amazon Q; now stewarded by the Agentic
  AI Foundation under the Linux Foundation (co-founded by OpenAI, Dec 2025).
  Monorepo semantics: agents read the **nearest AGENTS.md** to the file being
  edited, so subdirectory files override/supplement the root.
  Sources: [agents.md](https://agents.md/),
  [InfoQ, Aug 2025](https://www.infoq.com/news/2025/08/agents-md/),
  [Socket blog](https://socket.dev/blog/agents-md-gains-traction-as-an-open-format-for-ai-coding-agents),
  [OpenAI Agentic AI Foundation announcement](https://openai.com/index/agentic-ai-foundation/).
- **Cursor rules** add the loading-policy vocabulary: four activation modes —
  Always Apply (use sparingly; "every always-on rule eats tokens from every
  interaction"), Auto-Attached via globs (the workhorse), Agent-Requested
  (agent reads a description and decides), and Manual (`@rule-name`).
  Practitioner guidance: 5–8 rule files, <100 lines each
  ([Cursor rules docs](https://cursor.com/docs/rules); practitioner guides
  [vibecodingacademy](https://www.vibecodingacademy.ai/blog/cursor-rules-complete-guide),
  [techsy.io](https://techsy.io/en/blog/cursor-rules-guide)). Cursor's @Docs
  crawls and indexes external doc URLs for on-demand reference.
- **Anthropic's large-codebase guidance** (2026-05-14) matches: root CLAUDE.md
  = "pointers and critical gotchas only; everything else drifts into noise";
  layer nested files additively; scope skills to paths for progressive
  disclosure; **review the config every 3–6 months** because "older
  instructions may constrain newer models' capabilities"
  ([claude.com blog](https://claude.com/blog/how-claude-code-works-in-large-codebases-best-practices-and-where-to-start)).

**Takeaway**: this repo's AGENTS.md-root + per-directory AGENTS.md + hk-enforced
`claude_md_size_limit` (≤200 lines/≤12000 chars) + `.claude/rules/*.md` is a
faithful implementation of the converged standard. The missing Cursor-style
piece is explicit *conditional* loading policy for the research corpus (what an
agent loads always vs. on-topic vs. on-request).

### 4. Anthropic's context-engineering doctrine: file-based markdown memory + progressive disclosure, not a database

- ["Effective context engineering for AI agents"](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
  (Anthropic engineering, late 2025) names **structured note-taking / agentic
  memory** — "the agent regularly writes notes persisted to memory outside the
  context window, pulled back in later" — as a core strategy alongside
  compaction and tool-result clearing, and promotes **progressive disclosure**:
  "agents can incrementally discover relevant context through exploration...
  maintaining only what's necessary in working memory."
- Anthropic's productized **memory tool** (public beta on the Claude Developer
  Platform) is explicitly **a file-based system** — markdown notes in a
  directory the agent reads/writes — not a vector store or graph DB
  ([Claude cookbook: context engineering](https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools)).
- This validates the repo's existing stack (`.omc/notepad.md`,
  `.claude/rules/*.md` as distilled lessons, `notepad-enforcement.md`'s
  write-as-you-go rule) as the same architecture Anthropic ships first-party.

### 5. Microsoft GraphRAG's cost lesson: full LLM-built knowledge graphs are indexing-expensive; the field moved to deferring synthesis to query time

- **Full GraphRAG pipeline** (Microsoft Research): LLM extracts entities +
  relationships → LLM summarizes each → graph statistics extract hierarchical
  community structure (Leiden) → LLM writes community summaries used by
  global search. Every stage is LLM-priced; reported real-world indexing costs
  reached **$33,000 for large enterprise datasets** (Microsoft's own 2024
  reporting, via [articsledge summary](https://www.articsledge.com/post/lazygraphrag-retrieval-augmented-generation)).
- **LazyGraphRAG** (Microsoft Research blog, **2024-11-25**): replaces LLM
  indexing with NLP noun-phrase co-occurrence extraction and defers all LLM
  summarization to query time. Result: "data indexing costs identical to
  vector RAG and **0.1% of the costs of full GraphRAG**"; comparable global-
  search answer quality at **>700x lower query cost**; at 4% of GraphRAG's
  query cost it outperforms it on all metrics
  ([Microsoft Research blog](https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/)).
- Industry reading: graph structure adds most value for **global/thematic
  questions over a corpus** ("what are the recurring failure modes across all
  our research?"), not for point lookups — and the cost-rational way to get it
  is **lazy or periodic synthesis**, not a continuously maintained LLM-built
  index.

**Takeaway**: directly load-bearing for the graphify decision — the
economically sound slot for a knowledge-graph tool over this corpus is
**periodic/on-demand synthesis runs producing browsable artifacts** (community
maps, cluster reports), while day-to-day retrieval stays grep + curated
indexes. Building graphify into the hot retrieval path would replicate the
cost/staleness profile the field just walked away from.

### 6. The interop layer everyone standardized on is plain markdown at stable paths

Across all of the above, the common substrate is identical: Mintlify serves
every page as `.md` "so tools process content faster and use fewer tokens";
AGENTS.md is "intentionally plain Markdown with no required fields"; Anthropic's
memory tool is markdown files; Cursor rules are markdown-with-frontmatter
(.mdc); FastHTML's context bundles are generated *from* markdown; trade-press
coverage titles itself "In Agentic AI, It's All About the Markdown"
([Visual Studio Magazine, 2026-02-24](https://visualstudiomagazine.com/articles/2026/02/24/in-agentic-ai-its-all-about-the-markdown.aspx)).
Binary/DB-backed knowledge stores appear only where a vendor operates managed
infrastructure (Copilot's cloud index, Sourcegraph's search platform).

---

## The 4–6 patterns applicable to a solo maintainer with a markdown corpus and grep-first rules

1. **Grep/agentic search stays the hot path; do not add an embedding or graph
   index for retrieval.** Anthropic and Sourcegraph both abandoned index-based
   retrieval for freshness + precision + zero maintenance; the only orgs
   keeping indexes run managed fleets (Copilot). (Findings 1, 6.)
2. **Give the corpus an llms.txt-shaped index**: one curated markdown file per
   corpus area (`.omc/research/`, `docs/research/`) with one line per artifact
   — title, date, one-sentence claim scope — mirroring
   `mintlify-catalog.md`'s role for the external cache. Cheap to maintain at
   write time (the repo already mandates per-artifact "GitHub repos touched"
   sections; an index entry is the same discipline one level up), and it is
   what turns blind grep into a two-hop lookup: grep the index → Read the
   artifact. (Finding 2.)
3. **Adopt explicit loading tiers, Cursor-style**: always-on (root AGENTS.md,
   already size-capped) / auto-attached (per-directory AGENTS.md, already in
   place) / agent-requested (skills + rules with trigger descriptions) /
   manual (research artifacts, loaded only via the index). The corpus's gap is
   tier 4 discipline: artifacts should never be always-on context. (Finding 3.)
4. **Keep memory file-based and write-as-you-go** — the notepad + rules +
   verbatim-agent-report pattern already matches Anthropic's shipped memory
   tool and context-engineering doctrine; invest in curation (distill working
   research into `.claude/rules/` and index entries) rather than new storage.
   (Finding 4.)
5. **Run graph synthesis lazily and periodically, never as a live index** —
   the LazyGraphRAG lesson. Graphify's economically correct role is a
   monthly/on-demand "map the corpus" run whose *outputs* (cluster/community
   reports, HTML maps) are committed as ordinary markdown/HTML artifacts and
   themselves indexed per pattern 2 — retrieval then greps the synthesis
   output, not a graph store. (Finding 5.)
6. **Schedule a recurring config/knowledge review** (Anthropic recommends
   every 3–6 months, especially after model releases) to prune stale rules and
   index entries — staleness, not absence, is the observed failure mode of
   instruction files. (Finding 3.)

---

## Uncertainties / gaps

- **Adoption figures are secondary-sourced**: the SE Ranking 10.13% and
  BuiltWith 844k llms.txt numbers, and the AGENTS.md 20k→60k repo counts, come
  from surveys/trade coverage, not from primary datasets I could re-run
  (Bash/crawling unavailable this session). Directionally consistent across
  multiple sources, but exact figures should be treated as ±.
- **The Boris Cherny "agentic search outperformed RAG by a lot" claim** traces
  to Hacker News comments and podcast remarks quoted by third parties; no
  formal Anthropic benchmark publication backs the magnitude. Anthropic's
  official blogs assert the architecture but not comparative numbers.
- **Token-cost counterevidence is real but unquantified for this corpus**: the
  Milvus critique of grep-only retrieval (token burn on broad terms) was not
  tested against this repo's actual corpus size; at dozens of reports the
  concern is likely immaterial, but no measurement exists.
- **Internal-docs-as-markdown monorepo patterns at named companies**: searches
  surfaced the AGENTS.md/nearest-file monorepo convention and generic
  docs-as-code-for-agents guidance, but no first-party engineering-blog
  case study (e.g., a Stripe/Shopify-class writeup of an internal
  markdown KB wired to coding agents) within the research budget. The
  monorepo pattern claims here rest on the AGENTS.md spec + vendor docs, not
  on a named-company internal deployment.
- **Copilot embedding-model details** (37.6% lift, 8x smaller index) are
  GitHub's own marketing numbers; no independent replication found.
- GraphRAG dollar figures ($10k/10k-doc, $33k enterprise) are illustrative
  numbers repeated in secondary coverage of Microsoft's reporting; the primary
  Microsoft blog gives ratios (0.1%, 700x) rather than dollar amounts.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — local grounding: mintlify-cache glob, catalog, rules files, R2 inventory report.
- [AnswerDotAI/llms-txt](https://github.com/AnswerDotAI/llms-txt) — llms.txt spec origin, llms_txt2ctx CLI (via repo + llmstxt.org docs).
- [AnswerDotAI/fasthtml](https://github.com/AnswerDotAI/fasthtml) — llms-ctx.txt / llms-ctx-full.txt agent-facing context bundles (via docs.fastht.ml).
- [microsoft/graphrag](https://github.com/microsoft/graphrag) — GraphRAG/LazyGraphRAG architecture + cost (via Microsoft Research blog for the project).
- [sveltejs/svelte](https://github.com/sveltejs/svelte) — llms.txt adoption by a major OSS framework (via svelte.dev/docs/llms).
- [vitejs/vite](https://github.com/vitejs/vite) — issue #19400 as evidence of ecosystem demand for llms.txt.
- [openai/agents.md](https://github.com/openai/agents.md) — AGENTS.md spec + nearest-file monorepo semantics (via agents.md site).
- [sourcegraph/cody-public-snapshot](https://github.com/sourcegraph/cody-public-snapshot) — Cody retrieval architecture (via Sourcegraph blog "How Cody understands your codebase").
