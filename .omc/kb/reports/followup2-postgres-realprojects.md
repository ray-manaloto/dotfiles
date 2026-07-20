# Follow-up 2 — Postgres as the "prebuilt substrate" for an AI-agent orchestrator: REAL projects, evidence-first

Agent: followup2-postgres-realprojects · Date: 2026-07-19 · Host: Ray's single Mac (with a devcontainer)

## What changed since the first Postgres report (`followup-postgres-infra.md`)

The prior report's headline — "Postgres is over-engineered, use SQLite" — rested
almost entirely on **one premise: a resident daemon fights the host-only,
single-Mac constraint.** This follow-up was commissioned because that premise is
wrong for the control plane:

- **Host-only is a constraint on the *graphify knowledge substrate*, not on the
  orchestrator's control plane.** The two were conflated.
- **This repo has a devcontainer.** A containerized Postgres is a
  `docker compose` service (or a devcontainer feature) with a named volume — no
  Homebrew daemon on the Mac, no `launchd` plist, no host `shared_preload_libraries`
  ritual. `shared_preload_libraries` becomes **one line in a container config
  file**, exactly the thing containers exist to make disposable.

Once the "no daemon on the host" objection is void, the prior report's own
threshold table (Q4) already conceded the flip conditions — *"need SQL analytics
/ joins / concurrent readers"*, *"one store for queue+state+vector+graph"*, *"many
truly-concurrent workers"* — and every one of those is squarely in play for
"autonomous multi-agent orchestration + observability + write-back queue growing
toward many specialist agents." So the honest re-read is: **the first report
answered a different (host-bound) question and its conclusion does not transfer to
the containerized case.** Below is the evidence the first report never gathered:
the real projects doing exactly this.

---

## Q1 — REAL projects using Postgres as the AI-agent orchestration backbone

This is the core ask, and the evidence is overwhelming: **Postgres-as-agent-backbone
is not a thesis, it is the mainstream 2026 pattern.** Star counts and last-push
dates fetched live from the GitHub API on 2026-07-19.

### Durable agent state / memory / checkpointing

| Project | Stars | What it is | Who / how it's used |
|---|---|---|---|
| **[langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)** + `langgraph-checkpoint-postgres` | 37.6k | LangGraph's `PostgresSaver` checkpointer persists graph/agent state to Postgres | The **de-facto standard** for durable LangGraph agents in production. `MemorySaver` is dev-only; production docs explicitly route you to Postgres for durability, pause/resume, human-in-the-loop, and crash replay. [Persistence docs](https://docs.langchain.com/oss/javascript/langgraph/persistence) · [PyPI](https://pypi.org/project/langgraph-checkpoint-postgres/) |
| **[getzep/zep](https://github.com/getzep/zep)** | 4.8k | Agent memory layer (temporal knowledge graph + facts) | Memory-as-a-service for agents; the community edition is Postgres-backed. Relevant to the graphify work — it's the "memory + graph" shape done on Postgres. |
| **[pgvector/pgvector](https://github.com/pgvector/pgvector)** | 22.3k | Vector similarity search extension | The vector-memory / RAG standard. Used in production by **OpenAI, Supabase, Neon**. Handles ~2M vectors on a single server before you feel it; HNSW indexes; `halfvec`/Matryoshka quantization for scale. This is the "agent long-term memory" substrate most teams pick in 2026. [pgvector RAG 2026](https://www.digitalapplied.com/blog/build-self-hosted-rag-postgres-pgvector-tutorial-2026) |

### Durable execution / workflow orchestration for agents (the "write only your logic" layer)

| Project | Stars | What it is | Agent relevance |
|---|---|---|---|
| **[dbos-inc/dbos-transact-py](https://github.com/dbos-inc/dbos-transact-py)** | 1.5k | **Durable workflows as a pip-installable Python library, Postgres as the *only* infrastructure** | **The single most on-target project for this ask.** Annotate a function `@DBOS.workflow` and it checkpoints each step to Postgres; on crash/restart it resumes from the last completed step. Ships **first-party integrations with Pydantic AI, OpenAI Agents SDK, and LlamaIndex** — `DBOSAgent` wraps `Agent.run` as a durable workflow, model/MCP calls as steps. Its **queues** (concurrency limits, rate limits, timeouts, retries, priority) live in the same Postgres — no separate broker. [Pydantic AI + DBOS](https://ai.pydantic.dev/durable_execution/dbos/) · [dbos.dev](https://www.dbos.dev/) |
| **[temporalio/temporal](https://github.com/temporalio/temporal)** | 21.7k | Durable-execution engine; **Postgres is a supported persistence backend** | The heavyweight incumbent for durable agent workflows ("resume a 50-step research task from the last tool call after a restart"). Self-host = Temporal server (Go) + **Postgres** + optional Elasticsearch. More infra than DBOS. [Temporal for AI agents 2026](https://effloow.com/articles/temporal-ai-agents-durable-execution-guide-2026) |
| **[microsoft/pg_durable](https://github.com/microsoft/pg_durable)** | 2.7k | **Microsoft's in-*database* durable execution** (open-sourced 2026-06) | Durable, fault-tolerant SQL functions **entirely inside Postgres** — a `pgrx` extension with a background worker (built on Rust `duroxide`/`duroxide-pg`). Explicitly targets *"vector embedding pipelines, ingest pipelines, fan-out aggregation, external API workflows"* — i.e. agent plumbing — without stitching together cron + workers + queues + external orchestrators. Ships to **Azure HorizonDB**. Needs `shared_preload_libraries` (fine in a container). [InfoQ](https://www.infoq.com/news/2026/06/postgresql-pg-durable/) · [MS techcommunity](https://techcommunity.microsoft.com/blog/adforpostgresql/introducing-durable-functions-in-postgresql/4526821) |

### Postgres-backed job/task queues (the durable claim + retry + DLQ layer)

| Project | Stars | Lang | Notes for an agent orchestrator |
|---|---|---|---|
| **[pgmq/pgmq](https://github.com/pgmq/pgmq)** | 5.0k | SQL ext (Rust) | SQS/RSMQ-style: visibility timeout, exactly-once-within-VT, archive/DLQ, **no background worker** (pure SQL). **Adopted by Supabase as its official Queues product.** The canonical "Postgres message queue for agents." [Supabase Queues](https://supabase.com/blog/supabase-queues) |
| **[riverqueue/river](https://github.com/riverqueue/river)** | 5.5k | Go | Fast, typed, `SKIP LOCKED` job queue; strong chaos-recovery in benchmarks. |
| **[oban-bg/oban](https://github.com/oban-bg/oban)** | 3.9k | Elixir | Robust job processing; one of only three queues to survive all sustained-pressure scenarios in the benchmark below. |
| **[timgit/pg-boss](https://github.com/timgit/pg-boss)** | 3.8k | Node | Queueing + scheduling + pub/sub on Postgres; basis of `pg-workflows` (a Temporal-lite). |
| **[graphile/worker](https://github.com/graphile/worker)** | 2.3k | Node | High-perf; ~100–200 jobs/s before lock contention on typical hardware. |
| **[procrastinate-org/procrastinate](https://github.com/procrastinate-org/procrastinate)** | 1.3k | **Python** | Celery-alternative task queue on Postgres 13+; `LISTEN/NOTIFY` + `SKIP LOCKED`; sync+async, Django/ASGI. Python-native fit for this repo. |
| **[janbjorge/pgqueuer](https://github.com/janbjorge/pgqueuer)** | 1.5k | **Python** | `LISTEN/NOTIFY` for instant wakeups + `FOR UPDATE SKIP LOCKED`; first-class async/await. Python-native. |
| **[NikolayS/pgque](https://github.com/NikolayS/PgQue)** | 1.7k | SQL | Zero-bloat PgQ revival (TRUNCATE rotation → no dead tuples); ticks via `pg_cron`. |

### Graph in Postgres (directly relevant to the graphify program)

| Project | Stars | What it is |
|---|---|---|
| **[apache/age](https://github.com/apache/age)** | 4.7k | Apache AGE — openCypher graph queries **as a Postgres extension**. Hybrid graph+SQL in one query. Marketed explicitly for knowledge graphs / agent episodic memory: "write entities, relationships, and episode nodes to a graph during each interaction." Azure Database for PostgreSQL ships it. [age.apache.org](https://age.apache.org/) |

**Takeaway for Q1:** every layer an autonomous multi-agent orchestrator needs —
durable state (LangGraph PostgresSaver, DBOS, Temporal, pg_durable), a task queue
(pgmq + 6 others), vector memory (pgvector, 22k stars, OpenAI/Supabase/Neon), and
even the knowledge graph (Apache AGE) — has a **mature, well-starred, actively-pushed
(all pushed within the last ~2 weeks) project that puts it on Postgres.** This is
not a fringe pattern; it is the center of gravity of 2026 agent infrastructure.

---

## Q2 — The "one substrate, many extensions" thesis: does it hold?

**Yes, and it's a named, productized movement — "Postgres maximalism" / "Postgres-first."**
A single containerized Postgres can provide, via extensions, all of:

| Need | Extension / feature | Resident-server / bgw? |
|---|---|---|
| Durable task queue | **pgmq** | No bgw (pure SQL) — but needs the server for multi-client access |
| Async events / wakeups | **LISTEN/NOTIFY** (core) | Needs the server (multi-backend) |
| Scheduling (cron) | **pg_cron** | **Yes** — bgw + `shared_preload_libraries` |
| In-DB durable workflows | **pg_durable** (Microsoft) | **Yes** — bgw + `shared_preload_libraries` |
| Vector memory / RAG | **pgvector** | No bgw |
| Knowledge graph | **Apache AGE** | No bgw (loaded lib) |

**Who runs this in production:**

- **Supabase** — "the complete Postgres platform built for agentic workloads":
  Postgres + pgvector (Supabase Vector) + pgmq (Supabase Queues) + auth + storage,
  "one dashboard, one connection string, one bill." Explicitly positions itself as
  replacing "a vector database + auth + file store + API layer + a separate
  Postgres" with one Postgres. [Supabase for Agents](https://supabase.com/solutions/agents) · 106k-star repo.
- **Tembo** — "Postgres Stacks": pre-bundled extension sets (message-queue stack =
  pgmq, VectorDB stack = pgvector + `pg_vectorize`, OLAP, search) so you *"replace
  multiple separate services with a single Postgres deployment."* pgmq itself is a
  Tembo project. [PostgreSQL maximalism](https://datalabtechtv.com/posts/postgresql-maximalism/)

**The real limit of the thesis** (stated so the next reader can check it *here*):
the "many extensions" story only fully works on a **real server** — the two
highest-value orchestration extensions (`pg_cron` for scheduling, `pg_durable` for
in-DB durable execution) require a background worker via `shared_preload_libraries`,
which the embedded PGlite path **cannot** run (the first report's Q3 finding stands).
**In a container that limitation evaporates** — you run the real server, so
`shared_preload_libraries = 'pg_cron,pg_durable'` is a one-line container config.
The thesis holds *precisely because* we accepted a containerized server.

---

## Q3 — What did the single-Mac report miss?

Three things, in order of importance:

1. **It scoped the whole decision to "no daemon on the host," then never asked
   the container question.** The report's own words: *"a resident daemon to
   install/run/monitor on the Mac (fighting the host-only… posture)."* A container
   *is* the standard answer to "I don't want a daemon fighting my host" — the
   daemon lives in a disposable, volume-backed, `docker compose down`-able box.
   Every "cost" the report charges to Postgres (install/run/monitor on the Mac,
   `shared_preload_libraries` restart rituals, "a second data store to back up")
   is a container concern, not a host concern, once you containerize — and this
   repo already runs a devcontainer as its *real* dev environment.

2. **It evaluated Postgres as a *queue*, and missed Postgres as a *prebuilt agent
   platform*.** The report's Q1–Q5 are entirely about queue mechanics (pgmq vs pgq
   vs LISTEN/NOTIFY vs SQLite claim patterns). It never surfaced **DBOS, LangGraph
   PostgresSaver, Temporal, pg_durable, pgvector, or Apache AGE** — i.e. the
   layers that make Postgres a "just add your logic" substrate. The maintainer's
   ask — "prebuilt plumbing, write only our logic" — is answered *far* better by
   DBOS-on-Postgres (annotate a Python function, get durable checkpointed
   workflows + queues + scheduling) than by hand-rolling a 40-line SQLite claim
   loop, which is exactly the "write your own plumbing" outcome the maintainer
   said they wanted to avoid.

3. **It optimized for today's workload and ignored the stated trajectory.** The
   brief says *"growing toward many specialist agents."* The report's flip table
   already marks "many truly-concurrent workers contending on one queue" and
   "one store for queue+state+vector+graph" as the Postgres-wins conditions —
   then recommended against Postgres anyway on the host-only premise. Remove that
   premise and the report's *own* analysis points at Postgres for the target
   state.

**What the report got right and still stands:** for a *pure queue* at a handful of
jobs/minute, raw Postgres throughput (pgmq benchmarked at ~11k jobs/s) is
irrelevant, and `LISTEN/NOTIFY` is a nice-to-have wakeup, not a backbone. Those
facts are true — they just don't decide the platform question, because the value
of Postgres here is **consolidation + prebuilt agent frameworks + optionality**,
not throughput.

---

## Q4 — Honest comparison vs SQLite + native-CC primitives (container available)

### The genuinely hard counter-argument, stated fairly

The strongest anti-Postgres case is **no longer "no server on the host"** — it's
**"the prebuilt durable-workflow win doesn't require Postgres either."** As of
2026, **DBOS Transact supports a SQLite backend** ("SQLite is all you need for
durable workflows"), so you can get `@DBOS.workflow` durability, resume-from-step,
and queues **on SQLite, zero server.** [DBOS June 2026](https://www.dbos.dev/blog/new-in-dbos-june-2026)
That means the "write only your logic" ergonomic is available *without* committing
to Postgres. This is the real decision axis, and it's a closer call than either
report acknowledged.

### Where Postgres clearly wins (container assumed)

| Dimension | Why Postgres wins | Evidence |
|---|---|---|
| **One store for queue + state + vector + graph** | pgmq + PostgresSaver/DBOS + pgvector + Apache AGE under **one connection string**, updated in **one transaction** (workflow metadata + app data atomic). SQLite would be file + `sqlite-vec` (less adopted) + no real graph ext. | Supabase/Tembo consolidation story; DBOS "same transaction" atomicity. |
| **Vector memory maturity** | pgvector: 22k stars, OpenAI/Supabase/Neon in prod, HNSW, quantization to millions of vectors. `sqlite-vec` is real but far less battle-tested for agent memory at scale. | [pgvector adoption](https://www.digitalapplied.com/blog/build-self-hosted-rag-postgres-pgvector-tutorial-2026) |
| **Cross-process/agent pub-sub** | `LISTEN/NOTIFY` gives **real inter-process events** so N specialist agents react to "new ticket / state changed" without each polling a file. SQLite has **no pub/sub** — many agents = many pollers on one file, and SQLite serializes writes. | First report Q1; procrastinate/pgqueuer both build on NOTIFY. |
| **Off-the-shelf durable-execution + framework integration** | LangGraph, Pydantic AI, OpenAI Agents SDK, LlamaIndex, Temporal, pg_durable all target **Postgres first**. Choosing Postgres means the prebuilt integration exists; SQLite is the second-class backend where it exists at all. | DBOS first-party integrations; LangGraph PostgresSaver. |
| **Concurrency at the target state** | "Many specialist agents" contending on one queue is exactly what `SKIP LOCKED` on a real server is for. SQLite serializes writers — fine for a handful, a ceiling as you fan out. | Benchmark: pgmq 11k jobs/s vs SQLite's single-writer model. |
| **Observability / write-back queue as SQL** | The brief wants "observability + write-back queue." Postgres gives ad-hoc SQL joins across live queue+state+memory, plus tools (DBOS Argus, Supabase dashboard) that read the same DB. | DBOS Argus; Supabase agent dashboard. |

### Where Postgres is still overkill

- **If you stay at a handful of jobs AND don't use vector/graph**, DBOS-on-SQLite
  gives durable workflows with **zero server** — Postgres buys nothing.
- **Queue bloat under sustained load is real** but doesn't bite here: the
  benchmark found `SKIP LOCKED` queues (pgmq, river, pg-boss, oban, graphile)
  churn dead tuples needing VACUUM, and **5 of 8 queues timed out under
  sustained pressure** (only awa, oban, pgque survived all four). At a
  handful of multi-minute jobs you are nowhere near that regime — but it means
  "pgmq at 11k jobs/s" is a peak headline, not a sustained guarantee.
  [hardbyte/postgresql-job-queue-benchmarking](https://github.com/hardbyte/postgresql-job-queue-benchmarking)
- **`pg_cron`/`pg_durable` background-worker config** is a container-config line,
  but it is still a moving part SQLite doesn't have. Scheduling can equally come
  from the harness primitives (Routines/`schedule`, `loop`, `SessionEnd`/`Stop`
  hooks, background tasks) the first report correctly identified.

### Evidence-based verdict

**For THIS project — autonomous multi-agent orchestration + observability +
write-back queue, explicitly growing toward many specialist agents, with a
container available — a containerized Postgres is now an *attractive and
proportionate* control-plane substrate, not over-engineering.** The first report's
verdict inverts once its host-only premise is removed, and the maintainer's
instinct is correct: it missed the container flip and missed the prebuilt-platform
projects (DBOS, PostgresSaver, pgvector, AGE, pg_durable) that make Postgres a
"just add your logic" backbone rather than a bare queue.

The one honest caveat: **the durable-workflow ergonomic itself is now
backend-agnostic (DBOS runs on SQLite too).** So the decision is not "Postgres for
durability" — it's **"Postgres for *consolidation*"**: do you want queue + durable
state + vector memory + knowledge graph + cross-agent pub/sub behind one
connection string and one transaction, with first-party agent-framework
integrations? For the stated trajectory, **yes.** If you were certain you'd stay
at a handful of jobs and skip vector/graph, DBOS-on-SQLite would be the leaner
call.

### Concrete recommended stack if you go Postgres

Run Postgres as a `docker compose` service beside the devcontainer (named volume
for the data dir; **not** on the Mac host), `shared_preload_libraries =
'pg_cron'` (add `pg_durable` only if you want in-DB workflows). Then, per layer:

1. **Durable workflows + queue + scheduling (the "write only your logic" layer):**
   **DBOS Transact (Python)** — `@DBOS.workflow`/`@DBOS.step`, DBOS queues for
   ticket dispatch, DBOS scheduled workflows for polling/escalation. Postgres is
   its only dependency. Wrap agents with `DBOSAgent` (Pydantic AI / OpenAI Agents
   SDK) for free crash-resume. **This is the piece that delivers the maintainer's
   ask most directly.**
2. **Agent state / checkpoints:** if you adopt LangGraph, use its `PostgresSaver`
   in the same DB; otherwise DBOS already checkpoints workflow state.
3. **Vector memory:** **pgvector** (HNSW) in the same DB for agent long-term
   memory / RAG.
4. **Cross-agent events:** `LISTEN/NOTIFY` for "new ticket / state changed"
   wakeups so specialist agents don't poll.
5. **Message queue (if you prefer an explicit queue over DBOS queues):** **pgmq**
   (Supabase-blessed) for SQS-shaped visibility-timeout/archive semantics.
6. **Knowledge graph (optional, revisit host-only):** **Apache AGE** *could*
   co-locate the graph in the same Postgres — but **the graphify knowledge
   substrate is under the host-only constraint**, so putting it in the
   containerized control-plane DB is a **policy decision to confirm with the
   maintainer**, not a free default. Flagged, not assumed.

Scheduling can still come from the harness primitives (Routines/`schedule`,
`loop`, `SessionEnd`/`Stop` hooks) instead of `pg_cron` if you want one fewer
background worker — the first report's guidance there remains sound.

---

## Bottom line

The first report answered "does a resident daemon fit a host-only Mac?" (no) and
mislabeled it "is Postgres right for this orchestrator?" With a container in play,
the correct question — **"is a consolidated Postgres a good prebuilt substrate for
autonomous multi-agent orchestration?"** — has a strong, evidence-backed **yes**,
demonstrated by the mainstream of 2026 agent infrastructure (LangGraph
PostgresSaver, DBOS, Temporal, Microsoft pg_durable, pgmq/Supabase Queues,
pgvector, Apache AGE). The sharpest remaining nuance is that DBOS now runs on
SQLite too, so the real choice is **consolidation (Postgres) vs minimalism
(SQLite)** — and for a project explicitly scaling toward many specialist agents
with observability and memory needs, consolidation wins.

## GitHub repos touched

- [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) — 37.6k★; `PostgresSaver` checkpointer = the standard for durable LangGraph agent state.
- [pgvector/pgvector](https://github.com/pgvector/pgvector) — 22.3k★; vector memory/RAG standard (OpenAI/Supabase/Neon in prod).
- [temporalio/temporal](https://github.com/temporalio/temporal) — 21.7k★; durable-execution engine with Postgres persistence backend for agents.
- [electric-sql/pglite](https://github.com/electric-sql/pglite) — 15.6k★; embedded WASM Postgres (context for the "embedded can't run bgw extensions" limit that the container removes).
- [pgmq/pgmq](https://github.com/pgmq/pgmq) — 5.0k★; SQS-style Postgres queue, no bgw; Supabase Queues is built on it.
- [riverqueue/river](https://github.com/riverqueue/river) — 5.5k★; Go `SKIP LOCKED` job queue; strong chaos recovery.
- [getzep/zep](https://github.com/getzep/zep) — 4.8k★; Postgres-backed agent memory layer (temporal knowledge graph).
- [apache/age](https://github.com/apache/age) — 4.7k★; openCypher graph as a Postgres extension; knowledge-graph / agent episodic memory.
- [oban-bg/oban](https://github.com/oban-bg/oban) — 3.9k★; Elixir Postgres job queue; survived all sustained-pressure benchmark scenarios.
- [timgit/pg-boss](https://github.com/timgit/pg-boss) — 3.8k★; Node Postgres queue + scheduling + pub/sub.
- [microsoft/pg_durable](https://github.com/microsoft/pg_durable) — 2.7k★; Microsoft in-database durable execution (2026-06); bgw via `shared_preload_libraries`.
- [graphile/worker](https://github.com/graphile/worker) — 2.3k★; Node Postgres job queue (~100–200 jobs/s ceiling).
- [NikolayS/PgQue](https://github.com/NikolayS/PgQue) — 1.7k★; zero-bloat PgQ revival; ticks via pg_cron.
- [dbos-inc/dbos-transact-py](https://github.com/dbos-inc/dbos-transact-py) — 1.5k★; **durable Python workflows, Postgres-only (now also SQLite); first-party Pydantic AI / OpenAI Agents / LlamaIndex integrations — the closest fit to "write only your logic."**
- [dbos-inc/dbos-transact-ts](https://github.com/dbos-inc/dbos-transact-ts) — 1.3k★; TypeScript sibling of the above.
- [janbjorge/pgqueuer](https://github.com/janbjorge/pgqueuer) — 1.5k★; Python Postgres queue (LISTEN/NOTIFY + SKIP LOCKED, async).
- [procrastinate-org/procrastinate](https://github.com/procrastinate-org/procrastinate) — 1.3k★; Python Postgres task queue (Celery alternative).
- [hardbyte/postgresql-job-queue-benchmarking](https://github.com/hardbyte/postgresql-job-queue-benchmarking) — benchmark harness; peak throughput + sustained-pressure survival (only awa/oban/pgque passed all four) + dead-tuple/VACUUM caveat.
- [supabase/supabase](https://github.com/supabase/supabase) — 106k★; "Postgres platform for agentic workloads" (pgvector + pgmq consolidation reference).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo; the devcontainer that makes a containerized Postgres control plane viable, and the host-only constraint that applies to graphify (not the control plane).
