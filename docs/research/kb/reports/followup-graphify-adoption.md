# Follow-up: graphify real-world adoption, best-practices, and maturity

**Question (from maintainer):** before we build a whole agent-memory architecture on
graphify, did we research *other projects that use it* and *its documented best
practices*? Prior research only read graphify's own source + competitors' docs.

**Package:** PyPI `graphifyy` · **Repo:** `Graphify-Labs/graphify` (moved from
`safishamsi/graphify` on 2026-07-18; the old path still redirects) ·
**Author:** Safi Shamsi · **License:** MIT · **Backing:** Y Combinator S26.

**Bottom line up front:** graphify is NOT a thin/abandoned hobby project — it is one
of the most-starred AI-coding-skill repos on GitHub (91k★) with ~1.4M PyPI
downloads/month, YC backing, and a real third-party ecosystem that already uses it
*specifically as agent memory*. The risk is not abandonment; it is **pre-1.0 schema/CLI
churn** on a **near-daily release cadence driven by essentially one maintainer**.
Net verdict: **MEDIUM risk**, well-mitigated by our chosen posture (pinned version,
host-only/removable, portable NetworkX JSON, thin `/graphify` skill coupling).

All figures captured **2026-07-19**; a viral repo's counts move fast.

---

## 1. Adoption signals (primary: `gh api`, PyPI, pypistats)

| Signal | Value | Source |
|---|---|---|
| Stars | **91,449** (cross-checked via two API routes: `repos/...` and `search/repositories`) | `gh api repos/Graphify-Labs/graphify` |
| Forks | 8,918 | same |
| Watchers/subscribers | 315 | `gh api` |
| Contributors | **100+** (API page capped at 100; site claims 71 "real" contributors) | `contributors?per_page=100` |
| Open issues (real, non-PR) | 258 | `search/issues type:issue state:open` |
| Closed issues | 712 | same |
| Open PRs | 323 | `search/issues type:pr state:open` |
| Closed/merged PRs | 633 | same |
| Commits (~default branch) | ~1,181 | `stats/participation` |
| Repo created | **2026-04-03** (≈3.5 months old) | `gh api` |
| Last push | 2026-07-18 | `gh api` |
| Default branch | `v8` | `gh api` |
| Org `Graphify-Labs` created | 2026-06-28; 162 followers; email `founders@graphify.com`; site graphify.com | `gh api orgs/Graphify-Labs` |

**PyPI `graphifyy`:**
- Version **0.9.20** (2026-07-18); requires Python ≥3.10; MIT, © 2026 Safi Shamsi.
- **188 releases** on PyPI in ~3.5 months.
- Downloads (pypistats): **last day 46,173 · last week 442,808 · last month 1,409,515**.
- Bare name `graphify` on PyPI is unclaimed (404) — the shipping name is the
  double-y `graphifyy`.

**Release cadence (primary: `releases` API).** Effectively **one release every 1–2
days**: v0.9.1 (2026-06-28) → v0.9.20 (2026-07-18) is 20 minor bumps in 3 weeks, on
top of a prior 0.8.x line (…0.8.43–0.8.51 tags visible). Momentum is *high*, not
stagnant.

**Versioning oddity worth flagging:** a `v1.0.0` git tag exists but is dated
**2026-04-05** — i.e. an early throwaway tag from the repo's first days, *behind* the
entire 0.8.x/0.9.x line. The real project is **pre-1.0** (current 0.9.20); the
"1.0.0" tag does **not** signal API maturity. Do not read it as a stability guarantee.

**Team vs one-maintainer:** functionally **one dominant maintainer** with a long tail
of drive-by fixers. Contribution counts: `safishamsi` **853** vs the next contributor
**27**, then 17, 16, 10, … The recent commit log confirms it — `safishamsi` authors
almost all release/changelog/docs commits and the bulk of fixes; others land single
targeted patches (Windows path bugs, language-specific extraction fixes). So: a
funded solo-lead project with community patch flow, **not** a multi-maintainer team.

---

## 2. Who uses it in the wild (beyond the author)

Yes — there is a **real third-party ecosystem**, and notably several projects use
graphify **exactly as persistent agent memory / a knowledge base**, not just one-shot
code graphing:

- **`lucasrosati/claude-code-memory-setup`** — **867★**, created 2026-04-12, PT-BR
  included. Description: *"Up to 71.5x fewer tokens per session on Claude Code with
  Obsidian + Graphify. Persistent memory, codebase knowledge graphs, and chat import
  pipeline."* This is a full agent-memory stack built on graphify.
- **`mir_mursalin_ankur` — "Graphify + code-review-graph: Build a Self-Updating
  Knowledge Graph for Claude Code"** (DEV Community, long technical writeup). Treats
  graphify as a *persistent knowledge layer* that replaces per-session file re-reads;
  wires auto-updates via **git hooks** and a "smart grep" PreToolUse hook. (Its
  companion repo `code-review-graph`/CRG is currently 404 — renamed or private — but
  the article is detailed and load-bearing; see §5 for its cautionary notes.)
- **Issue #152 (8 comments): "Integration idea: agentmemory for temporal memory +
  graphify for structural knowledge."** The community explicitly frames graphify as
  the *structural* knowledge layer, to be paired with a separate *temporal* memory —
  a useful mental model for our architecture.
- **GitHub code search:** `graphifyy` appears in **142** `pyproject.toml` and **106**
  `requirements.txt` files; `"graphify-out" filename:graph.json` matches **105**
  repos that have **committed a built graph** (the author's recommended
  "commit graphify-out/ to git" pattern, in the wild).
- **Third-party writeups / coverage** (leads, not primary): MindStudio (two posts,
  incl. "70x large-codebase cost cut" and "knowledge graph for your AI agent"),
  Augment Code ("Graphify hits 58.3K stars"), Analytics Vidhya ("From Karpathy's LLM
  Wiki to Graphify: Building AI Memory Layers"), Developers Digest ("Codebase Graphs
  Are the New Agent Map"), AlphaMatch, knightli.com setup guide, plus skill
  directories (openagentskill.com, skillsllm.com — the latter shows the star count
  climbing **58.3k → 76.3k → 91k** across successive snapshots, corroborating rapid
  organic growth).

**Honest caveat:** I found **little first-person critical discussion on HN/Reddit/X**
in these searches — most web hits are SEO-flavored vendor/tool blogs rather than
independent user postmortems. The strongest *independent* signals are the two
third-party GitHub projects above and the graphify issue tracker itself (§5), not
forum threads. So "widely adopted" is well-supported; "battle-tested by many
independent voices writing up failures" is only weakly supported.

---

## 3. Documented best-practices (author's recommended usage)

There is a docs site at **graphify.com** (with an `llms.txt` / `llms-full.txt` LLM
index) plus a marketing mirror at **graphify.net**; the substantive how-to lives in
the **README** and the installed **SKILL.md**. Author-recommended workflow for using
it as a persistent knowledge base:

- **Build cadence / auto-rebuild:** commit `graphify-out/` to git so a team clones a
  pre-built map; run **`graphify hook install`** to auto-rebuild after each commit
  (AST-only, no API cost).
- **Incremental updates:** **`--update`** re-extracts only changed files;
  **`--watch`** mode keeps the graph live as the codebase changes.
- **Provenance:** **`graphify add <url> --author "Name" --contributor "Name"`** tags
  external papers/videos/docs with attribution; every edge is tagged **EXTRACTED**
  (explicit in source) vs **INFERRED** (resolved by graphify) so query results carry
  confidence.
- **Multi-repo / global:** **`graphify global add graphify-out/graph.json --as
  myrepo`** registers project graphs into a unified index;
  **`graphify merge-graphs a.json b.json`** combines corpora into one searchable
  graph (issue #585 shows users actively asking how to combine graphs).
- **Wiki export:** **`graphify export … --wiki`** emits an agent-crawlable markdown
  wiki (Obsidian-compatible reports; community detection via Louvain/Leiden).
- **MCP server:** `python -m graphify.serve graphify-out/graph.json --transport http
  --host 0.0.0.0 --api-key "$SECRET"` exposes tools (`query_graph`, `get_node`,
  `shortest_path`, `semantic_search_nodes_tool`, …) for always-on access across
  sessions.
- **Agent-memory overlay (most relevant to our program):** `save-result` / `reflect`
  build an overlay under `graphify-out/memory/` recording which query paths were
  useful, dead ends, or later corrected; **`graphify reflect`** aggregates outcomes
  into a `LESSONS.md` and tags nodes preferred/tentative/contested by recency. This
  is the author's own "graph that learns from your query patterns" story — i.e.
  graphify explicitly markets a persistent-memory mode, not just static code graphing.
- Extraction is **local, deterministic, tree-sitter AST across 33 languages, zero API
  calls** for the code-parsing step; the optional semantic layer is where an LLM is
  involved.

---

## 4. Maturity / bus-factor / risk verdict

**Verdict: MEDIUM risk** (well-mitigated for our specific use).

**What lowers the risk (healthy momentum):**
- Enormous, *growing* adoption (91k★, 1.4M downloads/mo, 58k→91k in weeks); YC S26
  backing and a founding org with a website and revenue motion ("graphify
  Enterprise" per recent commits) — this is being built as a company, not abandoned.
- Very fast fix turnaround; active community PR flow; MIT-licensed; built on trusted
  libs (NetworkX, tree-sitter).
- Our coupling is *shallow*: we invoke via a `/graphify` skill, we **pin** the
  version, it's **host-only and removable**, and the artifact is a **portable
  NetworkX node-link JSON** — no proprietary lock-in, exportable/queryable outside
  graphify if we ever drop it.

**What raises the risk (real, concrete):**
- **Single-maintainer concentration.** 853 vs 27 contributions. If Safi Shamsi
  stops, the release engine largely stops. YC funding mitigates but does not remove
  this.
- **Pre-1.0, schema/CLI NOT stable — churn is frequent and behavioral.** Evidence
  from the tracker: node-ids broke at **v0.9.0** (per our prior notes); **`source_file`
  changed shape twice** — relative path → bare basename in **0.9.16**, which *broke
  resolution against a code root* (#1941, since patched); **non-deterministic
  community assignments across identical-corpus runs** (#1667, 0.9.6) — a
  reproducibility hazard for a knowledge base; **silent "wrote 0 entries" / wrong
  checkpoint dir** bugs with `--out` (#1990/#1991); **weight:null edges crash the
  build** (#1960). A near-daily release cadence means the graph format and CLI flags
  are a moving target across versions.
- **The installed skill marker / hook wiring churns** (recent commits: search-nudge
  now fires on Grep as well as Bash #1986; Windows hook-path fixes #1987) — so the
  *integration surface* we'd wire into agent memory is itself unstable release-to-release.

**Mitigations we should keep / add:**
1. **Pin `graphifyy==0.9.20`** and bump deliberately, reading release notes each time
   (schema shape can change between patch releases — see #1941).
2. Treat the graph JSON as the **source of truth we own** (portable node-link format);
   never build logic that can't survive a graphify uninstall.
3. If we ever auto-rebuild, use **git hooks, not PostToolUse/Stop hooks**, with CPU/
   memory guards — see §5; this is the single most important operational caution.
4. Keep graphify **host-only** and out of the devcontainer image (matches the PRD
   #310 pin 0.9.20 host-only decision), so image reproducibility is unaffected by its
   churn.

---

## 5. Cautionary tales / known limitations (from real users + issues)

From the `mir_mursalin_ankur` third-party writeup (independent operational experience):
- **Do NOT put `graphify update` in Claude `PostToolUse`/`Stop` hooks.** On large
  monorepos it runs **~10s+**, spawning **hanging background processes, CPU spikes,
  and swap exhaustion** — observed 3 concurrent processes at 65–73% CPU, load average
  12+, machine unresponsive. Move rebuilds to **git hooks** (detached, post-developer-
  action) with **CPU load checks (≤50% cores), memory guards (≥2GB free), and
  `pgrep` dedup**, or rapid commit chains (amend/rebase) saturate the box.
- **MCP tool-schema bloat:** graphify's ~25 MCP tool schemas cost **~6,000 tokens
  always in context**; the author strips to ~8 via an allow-list (−70% schema
  overhead). Relevant if we register its MCP server (weigh against our
  `mcp2cli`-first preference).
- **Query output bloat:** `graphify query` BFS depth=2 returns 87–378 nodes
  (~1,500 tokens) regardless of query specificity — great for exploration, wasteful
  for symbol lookup; route targeted lookups to a cheaper semantic tool.

From the graphify issue tracker (author's own repo):
- **#1941** — `source_file` silently reduced to bare basename in 0.9.16 (was relative
  path in 0.9.13), breaking resolution against a code root. (Schema regression.)
- **#1667** — non-deterministic community/cluster assignments across identical-corpus
  runs (0.9.6). (Determinism/reproducibility gap.)
- **#198** — "semantic layer is mostly disconnected from the AST graph." (The LLM
  concept layer and the deterministic AST graph don't fully join.)
- **#1948 / #1954** — semantic-doc gating bugs cause promised re-runs to silently not
  happen / docs to be quick-scanned instead of fully processed. (Silent under-processing.)
- **#162 / #265** — open questions about upper file/word limits and the need for
  hierarchical aggregation on very large corpora. (Scale ceiling not fully characterized.)
- **#722** — `manifest.json` writes absolute paths and no `graphify-out/.gitignore`
  by default. (Portability/commit-hygiene footgun for the "commit graphify-out/"
  workflow.)

---

## GitHub repos touched

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — primary
  subject: repo metadata, contributors, releases/tags, commits, issues, README.
- [safishamsi/graphify](https://github.com/safishamsi/graphify) — former repo path
  (redirects to Graphify-Labs/graphify); confirms the 2026-07-18 org move.
- [lucasrosati/claude-code-memory-setup](https://github.com/lucasrosati/claude-code-memory-setup)
  — third-party agent-memory stack built on graphify (867★); primary evidence of
  in-the-wild persistent-memory usage.
- [mir-mursalin-ankur/code-review-graph](https://github.com/mir-mursalin-ankur/code-review-graph)
  — companion repo to the DEV writeup (currently 404 — renamed/private); article
  used as the operational-cautions source.
