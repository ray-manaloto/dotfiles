# Follow-up — Graphiti embedded/no-server backends (G1 staleness re-evaluation)

Agent: followup-graphiti-embedded · Date: 2026-07-19 · Host: Ray's Mac (Python
3.14 host). Scope: ONE capability — age-based / bi-temporal staleness
invalidation of KG facts (gap "G1"). The maintainer challenged the prior
report's premise that **Neo4j (a resident server) is the only Graphiti backend**,
and therefore that host-only Graphiti is impossible. This re-verifies against
current source/docs and re-issues the G1 verdict only.

**Headline:** The maintainer is **factually right**. The prior claim ("Graphiti
needs Neo4j/FalkorDB + a resident server, violating our host-only constraint")
is **wrong as stated** — Graphiti ships **two** embedded, no-server backends in
its driver tree today (Kuzu, in-process; FalkorDB Lite, subprocess-no-Docker).
BUT the two caveats matter: Kuzu is **deprecated and being removed**, and the
FalkorDB-Lite *Graphiti driver* is **an unmerged draft**. And even fully
embedded, Graphiti **still requires an LLM API key** for its extraction pipeline
and a **second graph store** alongside graphify. So the corrected reasoning lands
on the **same G1 verdict** (build age-scoring on graphify's `captured_at`) — but
for a sounder reason than the prior report gave.

All facts below checked 2026-07-19 against `getzep/graphiti@main`
(graphiti-core **0.29.2**, `requires-python = ">=3.10,<4"`).

---

## Q1 — Does Graphiti support an embedded / no-server backend?

**Yes — two of them.** Full backend inventory from `graphiti_core/driver/`
(`falkordb_driver.py`, `kuzu_driver.py`, `neo4j_driver.py`, `neptune_driver.py`)
+ `pyproject.toml` extras:

| Backend | Extra (`graphiti-core[...]`) | Embedded / no-server? | Evidence |
|---|---|---|---|
| **Kuzu** `>=0.11.3` | `kuzu` | ✅ **Embedded, in-process, no server** | `kuzu_driver.py`: `self.db = kuzu.Database(db)`, `db: str = ':memory:'` default, file path also accepted. |
| **FalkorDB Lite** `>=0.5.0` (py≥3.12) | `falkordblite` | ✅ **Embedded subprocess, no Docker/server** | Extra declared in `pyproject.toml` (`falkordblite>=0.5.0; python_version>='3.12'` + `redis<9`). But driver **not yet merged** — see caveat. |
| **FalkorDB** (standard) `1.1.2+` | `falkordb` | ❌ **Requires a running server / Docker** | `falkordb_driver.py` `FalkorDriver(host, port, ...)`; config docs show `pip install graphiti-core[falkordb]` + `host='localhost', port='6379'` (Redis-protocol server). |
| **Neo4j** `5.26` | (default) | ❌ **Requires a running server** | Traditional server deployment. |
| **Amazon Neptune** | `neptune` | ❌ **Managed cloud service** | Needs Neptune + Amazon OpenSearch Serverless for full-text; `boto3`, `langchain-aws`, `opensearch-py`. |

### Kuzu — embedded, but a dead end
Kuzu is genuinely in-process (no server, `:memory:` or file). **However it is
deprecated in Graphiti.** `kuzu_driver.py` emits on init:

> "The Kuzu backend is deprecated and will be removed in a future release — the
> upstream Kuzu project is no longer maintained." (recommends Neo4j or FalkorDB)

So "embedded Graphiti via Kuzu" works *today* but is a **removal-scheduled path
on an unmaintained DB** — not something to build a durable dependency on. (A Kuzu
successor, "LadybugDB", is only a driver *request* — issue #1509 — not shipped.)

### FalkorDB Lite — the real embedded story, but the driver isn't merged
- The **standalone `falkordblite` package is mature**: latest **0.10.0, released
  2026-05-02**; classifiers list **Python 3.12, 3.13, and 3.14**; wheels include
  **`cp314` for macOS (x86_64 + arm64)** and Linux (x86_64 + aarch64). It "forks
  a lightweight sub-process next to your application" over a **Unix domain
  socket** — **no Docker, no server, no admin privileges, just a file path**.
  Limitation: **single-process access per DB file** (embedded-Redis constraint);
  positioned for local/dev/prototyping, not high-concurrency production.
- The **Graphiti integration is NOT GA.** Issue #1240 / **PR #1250 is a DRAFT,
  unmerged** (blocked on a CLA signature). The shipped `falkordb_driver.py` only
  accepts `host`/`port` — it does **not** accept a file/socket path. The
  `falkordblite` *extra* exists in `pyproject.toml`, but the `FalkorLiteDriver`
  class (`graphiti_core.driver.falkordb_lite_driver.FalkorLiteDriver`,
  `FalkorLiteDriver(path="~/.../knowledge.db")`) that the extra is for is **still
  in the draft PR**, not on `main`.

**Bottom line for Q1:** Neo4j is *not* the only option. Graphiti has an embedded,
no-server path — but the *supported* one (Kuzu) is deprecated/being-removed, and
the *good* one (FalkorDB Lite) is an unmerged draft. There is no GA, non-deprecated
embedded Graphiti backend as of 2026-07-19.

---

## Q2 — Is a host-only Graphiti viable on this Mac?

**Technically yes** (Kuzu today, or falkordblite once #1250 lands / by running the
draft/fork) — no Docker, no cloud, no resident server. **But "embedded backend"
removes only the database server; it does not make Graphiti lightweight.** Even
fully embedded, Graphiti-on-Mac still requires:

1. **A mandatory LLM API key for extraction.** This is the load-bearing cost.
   Graphiti's entire value is **LLM-based** entity/relationship extraction from
   "episodes" into a temporal graph; it "defaults to OpenAI for LLM inference and
   embedding" and "works best with LLM services that support Structured Output
   (OpenAI, Anthropic, Gemini)". Every write (episode ingest) spends LLM tokens.
   There is no non-LLM ingestion path — unlike graphify's `update` (AST via
   tree-sitter, no LLM).
2. **The `graphiti-core` dependency tree** (pydantic, tenacity, numpy, the
   provider SDK, diskcache, etc.) **plus** the backend driver deps — for
   falkordblite, a compiled wheel that **bundles an embedded Redis**; for kuzu, a
   compiled C++ extension. Heavier than graphify's pipx footprint.
3. **Python:** graphiti-core needs ≥3.10; **falkordblite needs ≥3.12** — the host
   is **3.14**, satisfied, and `cp314` wheels exist for both host arm64-Mac and
   the amd64 devcontainer. So the version/arch gate is clear; this is not the
   blocker.
4. **A second graph store on disk**, separate from graphify's `graph.json` — its
   own file (Kuzu DB dir / falkordblite `.db`), its own single-process-access
   constraint, its own sync problem.

So: host-only Graphiti is **possible**, not **cheap**. The real footprint is "an
LLM extraction bill on every write + a second embedded graph store + the
graphiti-core deps," not "just a Neo4j server we can't run."

---

## Q3 — Re-verdict for G1 ONLY (staleness / bi-temporal invalidation)

**Recommendation: BUILD age-scoring on graphify's existing `captured_at`. Do NOT
adopt Graphiti (even embedded) for staleness alone.** The prior report's
*conclusion* for G1 stands; its *reason* is corrected.

**Corrected reasoning.** The prior report justified "don't adopt" with "Graphiti
needs Neo4j + a server (host-only impossible)." That premise is false — embedded
backends exist. But the verdict survives on a stronger argument specific to G1:

- **G1 is one narrow capability**: rank/flag facts by age, and know "was true
  then, invalid now." graphify **already stores `captured_at`** on every node.
  Age-scoring is a **thin post-filter over the committed `graph.json`** at query
  time — no new store, no LLM, no new process.
- **Adopting Graphiti for staleness alone forces disproportionate machinery:**
  - a **second graph store** (Kuzu-file or falkordblite `.db`) running *parallel*
    to graphify — against the explicit "we already have graphify as primary; a
    second store just for temporal facts is a real cost" premise;
  - an **LLM extraction pipeline** to get facts *into* Graphiti in the first
    place — Graphiti's celebrated bi-temporal auto-invalidation only applies to
    edges **Graphiti itself** extracted (with `valid_at`/`invalid_at`), so you
    can't point it at graphify's graph and get invalidation for free; you'd
    re-ingest content through Graphiti's LLM, paying twice;
  - a **deprecated backend** (Kuzu, removal-scheduled) or an **unmerged driver**
    (falkordblite draft PR #1250) — neither is a stable foundation today;
  - a **sync/duplication** problem between the two stores.

**The trade, concretely.** Adopting Graphiti-embedded *buys* a battle-tested
bi-temporal model (automatic fact invalidation, point-in-time "what was true
when" queries, full episode→fact lineage) — genuinely better than a hand-rolled
age filter. It *costs* a second LLM-fed graph store, the graphiti-core deps, a
not-yet-GA/deprecated backend choice, and ongoing two-store sync — **to deliver
one capability we can approximate with a `captured_at` post-filter over the store
we already have.** For **staleness alone**, that is a bad trade. Borrow Graphiti's
*pattern* (score/invalidate on a stored timestamp; keep old facts flagged, not
deleted), not its engine — exactly the prior report's "steal the pattern" line,
now on firmer ground.

**Scope note (not a reversal).** The embedded-backend finding *does* matter for a
**different, larger** question the prior report foreclosed too casually: if the
program ever reconsiders its **primary** substrate wholesale, "Graphiti on
falkordblite" is a legitimate **host-only** candidate (bi-temporal invalidation
built in, no server, cp314 wheels) once PR #1250 merges. That is a
whole-substrate decision, explicitly **out of scope for G1** and against the
"graphify is primary" premise — but the maintainer's instinct that "server-only"
was an over-broad dismissal is correct and worth recording for any future
primary-store bake-off.

---

## Q4 — mem0 / cognee embedded modes (does the "too heavy" verdict change?)

Both have genuine embedded/no-external-service modes; the prior "too heavy"
verdicts **soften but do not flip for G1**, because both still (a) require an LLM
for extraction and (b) would be a **second store** — the same disqualifiers as
Graphiti for staleness-alone.

- **cognee** — the prior "Docker + Postgres" characterization is **outdated for
  its default**. cognee's **default local stack is fully embedded: SQLite +
  LanceDB + Kuzu**, file-based, **no Docker, no external services**. (It *can*
  scale to Neo4j/FalkorDB/Qdrant/Postgres, but doesn't require them.) So cognee is
  lighter than the prior report implied — **however** its default graph store is
  **Kuzu** (the same deprecated-in-Graphiti embedded DB), and its ECL pipeline
  still needs an LLM. Still a second LLM-fed store for G1's purpose.
- **mem0** — OSS mem0-core runs local: an embeddable vector store (e.g.
  Chroma/FAISS) + an **optional** graph layer (Kuzu/Neo4j/Memgraph). Its
  **OpenMemory MCP** server is the heavy part (Qdrant + Postgres/Docker), but the
  *library* need not use it. Still LLM-dependent for extraction, vector-first (not
  provenance-KG), and a second store. Verdict unchanged for G1.

Neither changes the G1 answer: for **staleness of graphify facts**, an embedded
mem0/cognee is still a second LLM-fed store, not a reason to abandon the
`captured_at` post-filter.

---

## Net answer to the maintainer's challenge

- **Is Neo4j the only option? No.** Graphiti has embedded, no-server backends
  (Kuzu in-process; FalkorDB Lite subprocess-no-Docker), and cognee/mem0 have
  embedded modes too. The prior report was **wrong** to call Graphiti
  server-only, and that correction is now recorded.
- **Does that reopen G1? No.** Kuzu is deprecated/being-removed; the falkordblite
  Graphiti driver is an unmerged draft; and *any* Graphiti/cognee/mem0 adoption
  for staleness alone means an LLM-extraction pipeline + a second graph store —
  disproportionate to a `captured_at` age post-filter over the graph we already
  have. **Build age-scoring on graphify; borrow Graphiti's bi-temporal pattern,
  not its engine.**
- **Version/arch is not the blocker:** falkordblite 0.10.0 (2026-05-02) ships
  `cp314` wheels for macOS arm64 + Linux — Python 3.14 host is fine. The blockers
  are the LLM bill, the second store, and the not-GA/deprecated backend status.

---

## GitHub repos touched

- [getzep/graphiti](https://github.com/getzep/graphiti) — subject; read `graphiti_core/driver/` tree, `falkordb_driver.py`, `kuzu_driver.py`, `pyproject.toml` (0.29.2), README, issue #1240, PR #1250 (draft), issue #1509 (LadybugDB request).
- [FalkorDB/falkordblite](https://github.com/FalkorDB/falkordblite) — via PyPI JSON (`falkordblite` 0.10.0, 2026-05-02, cp314 wheels) + FalkorDB blog on the embedded subprocess/Unix-socket model and limitations.
- [topoteretes/cognee](https://github.com/topoteretes/cognee) — docs.cognee.ai + repo: default embedded SQLite + LanceDB + Kuzu local stack, no Docker.
- [mem0ai/mem0](https://github.com/mem0ai/mem0) — embedded vector (Chroma/FAISS) + optional Kuzu/Neo4j graph; OpenMemory MCP is the heavy (Qdrant+Postgres) path.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo: prior `track-b-graphify-priorart.md` (the G1 claim under re-evaluation) and graphify's `captured_at` schema field.
