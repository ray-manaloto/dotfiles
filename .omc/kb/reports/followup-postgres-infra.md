# Follow-up — Is Postgres (+ extensions) the right "prebuilt substrate" for the orchestrator's plumbing?

Agent: followup-postgres-infra · Date: 2026-07-19 · Host: Ray's single Mac
(host-only is a HARD constraint — already ruled out Neo4j and
Postgres-server-based memory tools). Scope: evaluate Postgres + extensions
(pgmq, pgq, LISTEN/NOTIFY, pg_cron) as the queue / async / scheduling / state
substrate for a single-node autonomous AI-agent orchestrator so the team writes
only their logic, not queue/async machinery.

**Workload under evaluation (the number that decides everything):** ONE machine,
a *handful* of *multi-minute* LLM-agent tickets in flight, occasional human
escalation via GitHub/Slack/Discord. Low frequency (jobs/minute, not
jobs/second), high latency per job (minutes), single control plane. No
horizontal scaling, no multi-writer contention, no cross-host coordination.

**Headline recommendation (stated up front):** For THIS workload, a resident
Postgres server is **over-engineered** — it buys durability and SKIP-LOCKED
concurrency you can already get from SQLite (or even a directory of files),
while imposing a background daemon, `shared_preload_libraries` config, and a
service-lifecycle burden that fights the host-only, single-Mac constraint. The
right substrate is **SQLite in WAL mode with a `SELECT ... FOR UPDATE SKIP
LOCKED`-equivalent claim pattern** for the queue + state, plus the **native
harness primitives** (background tasks, `SessionEnd`/`Stop` hooks, Routines/the
`schedule` skill, the `loop` skill) for scheduling and the agent event loop.
**Postgres becomes the correct answer at a specific, nameable threshold — the
moment the control plane must be shared by more than one machine (or many
truly-concurrent workers contending on one queue).** Below that line it is
weight without payoff. The threshold is scale-of-*coordination*, not
scale-of-*data*.

Two important nuances the naive "no server" story misses, both verified below:

1. **You CAN get `pgmq` with no resident server** — via PGlite (in-process WASM
   Postgres) + `@electric-sql/pglite-pgmq`. So "we want pgmq specifically"
   does not force a daemon. But PGlite is single-connection, JS/WASM-hosted, and
   *is itself* the embedded-DB story — at which point it competes with SQLite,
   not with server Postgres, and SQLite wins on maturity/footprint for this job.
2. **`pg_cron` CANNOT run without a resident server** (it is a background worker
   loaded via `shared_preload_libraries`) — so the scheduling half of the
   "Postgres does everything" pitch is exactly the half that requires the daemon
   we are trying to avoid. Scheduling should come from the harness, not the DB.

---

## Q1 — Postgres for queues: pgmq vs pgq vs LISTEN/NOTIFY

### pgmq (PostgreSQL Message Queue) — the modern, maintained choice

`pgmq` is a lightweight SQS/RSMQ-style message queue implemented as a Postgres
extension, created and backed by **Tembo** (the repo has since moved to its own
`pgmq/pgmq` org). Supported on Postgres 14–18.
[[pgmq/pgmq](https://github.com/pgmq/pgmq)] [[docs](https://pgmq.github.io/pgmq/latest/)]

What it gives you:

| Capability | pgmq behavior | Evidence |
|---|---|---|
| **Visibility timeout (VT)** | `read()` makes a message invisible for VT seconds; if not deleted/archived it reappears — the SQS model, done in-DB with `FOR UPDATE SKIP LOCKED`. | [Tembo "self-regulating queue" blog](https://legacy.tembo.io/blog/pgmq-self-regulating-queue/) |
| **Delivery guarantee** | **Exactly-once *within* a visibility timeout** (i.e. at-least-once overall with a dedup window — the standard queue semantic). Not distributed exactly-once. | [Supabase PGMQ docs](https://supabase.com/docs/guides/queues/pgmq) |
| **Dead-letter / archive** | `archive()` moves a message to an `a_<queue>` archive table (replayable, auditable) rather than deleting. Retries via VT expiry; you build DLQ policy on `read_ct`. | [pgmq docs](https://pgmq.github.io/pgmq/latest/) |
| **No background worker** | Core queue is **pure SQL functions** — no daemon, no `shared_preload_libraries`. This is the headline design point and why it embeds cleanly. | [Tembo blog: "No Background Worker"](https://legacy.tembo.io/blog/pgmq-self-regulating-queue/) |
| **Partitioned queues (optional)** | Only if you want time/size-partitioned queues do you add `pg_partman` (which *does* use a bgw, `pg_partman_bgw` in `shared_preload_libraries`). Unpartitioned queues need none of that. | [pgxn pgmq README](https://pgxn.org/dist/pgmq/1.4.0/README.html), [pgpartman/pg_partman](https://github.com/pgpartman/pg_partman) |

Maturity/backers: actively maintained (1.8.x on PGXN as of mid-2026), adopted by
**Supabase** as its official Queues product, packaged for PGlite by ElectricSQL.
This is the one to pick *if* Postgres is chosen.

### pgq (Skype PgQ) — battle-proven but effectively legacy

`pgq` was designed at **Skype in 2006** to run messaging for hundreds of
millions of users; **Londiste** (replication) is a consumer built on it. It is
genuinely battle-tested, but for a greenfield single-Mac orchestrator it is the
wrong tool:

- It depends on a **C extension (`pgq`) AND an external daemon (`pgqd`)** — two
  native moving parts, neither of which runs on managed/embedded Postgres.
  [[pgq.github.io](https://pgq.github.io/)] [[pgq/skytools-legacy — "Obsolete"](https://github.com/pgq/skytools-legacy)]
- Its model is **batch/snapshot consumption**, not per-message visibility
  timeouts — a coarser fit for "claim one ticket, work it for minutes, ack".
- The original Skytools tree is marked **obsolete**; maintained code moved to
  the `pgq/` org but the ecosystem energy is clearly on pgmq.

A modern pure-PL/pgSQL revival, **PgQue** (`NikolayS/pgque`, by Nikolay
Samokhvalov), rebuilds the PgQ engine with **no C extension, no
`shared_preload_libraries`, no daemon** — one SQL file + `pg_cron` to "tick". It
is interesting (TRUNCATE-based rotation → zero dead tuples, no autovacuum
pressure) but it is young and it *depends on pg_cron for the tick* — i.e. it
re-introduces the resident-server requirement through the back door.
[[NikolayS/pgque](https://github.com/NikolayS/pgque)] [[pgque.dev](https://pgque.dev/)]

### LISTEN/NOTIFY — native async pub/sub, but not a queue

`LISTEN`/`NOTIFY` is built into core Postgres: a session `LISTEN`s on a channel,
another issues `NOTIFY channel, 'payload'`, and listeners get an async event.
What it *is*: cheap in-process pub/sub for "something changed, go look". What it
is **not**:

- **Not durable** — a notification delivered while no one is listening is
  **lost**; there is no replay, no persistence, no visibility timeout, no DLQ.
- **Payload-limited** (~8000 bytes) and fire-and-forget.

So the canonical Postgres queue pattern is **table-as-queue + `SKIP LOCKED` for
the durable claim + LISTEN/NOTIFY only as a low-latency wakeup** so workers
don't poll. pgmq essentially packages the first half; NOTIFY is an optional
latency optimization on top. For a handful of multi-minute jobs, **polling every
few seconds is completely adequate** and NOTIFY's wakeup latency win is
irrelevant.

---

## Q2 — Postgres for scheduling + async

### pg_cron — real cron in the DB, but requires a resident server

`pg_cron` is a cron-syntax job scheduler by **Citus Data (now part of
Microsoft)**, widely deployed on RDS/Aurora/Supabase.
[[citusdata/pg_cron](https://github.com/citusdata/pg_cron)]

The disqualifying detail for a "no-server" ambition: pg_cron **registers a
background worker** that wakes every minute and reads `cron.job`, and it **must
be added to `shared_preload_libraries`** — `CREATE EXTENSION` alone fails with
*"pg_cron can only be loaded via shared_preload_libraries"* and requires a
server restart.
[[pg_cron#167](https://github.com/citusdata/pg_cron/issues/167)]
[[DeepWiki install guide](https://deepwiki.com/citusdata/pg_cron/3.1-installation-and-configuration)]

Consequence: **pg_cron cannot run in an embedded/in-process Postgres** (PGlite
has no background workers — see Q3). The scheduling half of "Postgres does
everything" is precisely the half that mandates the resident daemon we are
trying to avoid on this Mac.

### Does LISTEN/NOTIFY cover the async/event needs of an agent loop?

Partially, and not the important part. An autonomous agent loop needs:
(a) "a new ticket arrived / a timer fired" wakeups, and (b) durable state so a
crash mid-multi-minute-job doesn't lose work. LISTEN/NOTIFY gives (a) with
**no durability** — exactly backwards for multi-minute jobs where the whole
point is surviving a restart. You would still need the durable claim table
underneath. And the *scheduling* trigger (run every N minutes, escalate after a
timeout) is better served by the harness's own timer primitives than by holding
a Postgres session open to `LISTEN`. **Net: LISTEN/NOTIFY is a nice-to-have
wakeup, never the backbone.**

---

## Q3 — Can Postgres be EMBEDDED / zero-server? (the concrete question)

Three candidate "no daemon" paths, and what each actually delivers:

### PGlite (`electric-sql/pglite`) — genuinely in-process, and it CAN run pgmq

PGlite is a **WASM build of Postgres packaged as a TypeScript library** (~3 MB
gzipped) that runs in-process in Node/Bun/Deno/browser with no separate server.
[[electric-sql/pglite](https://github.com/electric-sql/pglite)]
[[pglite.dev](https://pglite.dev/)]

Crucially for this question: **pgmq is officially available for PGlite** as a
separate package, `@electric-sql/pglite-pgmq` — you `import { pgmq }`, register
it, and `CREATE EXTENSION IF NOT EXISTS pgmq;`.
[[PGlite extensions catalog](https://pglite.dev/extensions/)]
This works precisely *because* pgmq's core is pure SQL with **no background
worker**. So the concrete answer to "can we get pgmq WITHOUT a resident server?"
is **yes — via PGlite**.

But the fine print reframes it as an anti-recommendation for our stack:

- **Single-connection, single-process.** PGlite runs Postgres in *single-user
  mode* (Emscripten can't fork), so it is one in-process instance — great for
  embedding, but it is not a shared control plane and gives no more concurrency
  than SQLite. [[pglite.dev/docs/about](https://pglite.dev/docs/about)]
- **No background workers → no pg_cron, no pg_partman bgw.** The extensions
  requiring `shared_preload_libraries` are simply **not available** in PGlite.
  The catalog lists pgmq and pgvector; **pg_cron and pg_partman are absent.**
  [[PGlite extensions](https://pglite.dev/extensions/)]
- **It's a JS/WASM runtime.** Adopting PGlite means hosting the plumbing in a
  Node/Bun process. If the orchestrator is Python (this repo's world), that is a
  foreign runtime dependency to carry for a queue.

So PGlite proves the "embedded pgmq" point but, being a single-connection
in-process DB, it **competes with SQLite, not with server Postgres** — and for a
Python-centric single-Mac orchestrator, SQLite is the more mature, zero-dep,
same-language choice (Q5).

### electric-sql (the sync product) — not relevant here

ElectricSQL's flagship is **Postgres→client sync** (a sync engine over a
*real, resident* Postgres). That is a multi-device data-sync story, not an
embedded-server story; it does not remove the server. PGlite is the piece of
ElectricSQL's world that matters for this question, and it's covered above.

### embedded-postgres binaries (`zonkyio`, `fergusstrange`, etc.) — a *managed* server, not serverless

These libraries (JVM: `zonkyio/embedded-postgres`; Go:
`fergusstrange/embedded-postgres`; Python: `pyben`/`testing.postgresql`-style
wrappers) **download a real `postgres` binary and spawn it as a child process**,
usually for tests. You *do* get full extension support (including
`shared_preload_libraries`, so pg_cron works) — but that is **exactly a resident
Postgres server**, just one your process starts and stops. It carries the full
initdb/data-dir/port/lifecycle burden. It is "embedded" only in the packaging
sense; operationally it is the daemon we set out to avoid.

### Verdict on Q3

To get the **full** Postgres extension experience (pgmq partitioned + pg_cron +
NOTIFY across sessions), a **real resident `postgres` server is unavoidable** —
because pg_cron/pg_partman need `shared_preload_libraries` and multi-session
NOTIFY needs multiple backends. You can get **pgmq alone** with no server via
PGlite, but PGlite is a single-connection in-process DB that is functionally in
SQLite's weight class, minus SQLite's maturity and Python-native fit.

---

## Q4 — Fit assessment (honest, YAGNI lens)

For **one machine, a handful of multi-minute tickets, occasional human
escalation**, Postgres+pgmq is **over-engineered**. The reasoning:

**What a durable queue actually needs to buy here:**
1. *Don't lose a ticket if the process crashes mid-job* → durability.
2. *Don't hand the same ticket to two workers* → an atomic claim.
3. *Retry a ticket that timed out / escalate after N tries* → visibility-timeout
   + retry-count semantics.

**What pgmq/Postgres buys beyond that** — and why it's wasted here:
- **High-concurrency `SKIP LOCKED` claiming** across many contending consumers.
  With a *handful* of jobs and effectively one control loop, there is **no
  contention to solve.**
- **Multi-writer / networked access** — a server on a socket many clients hit.
  Single Mac, single process: **not needed.**
- **MVCC, autovacuum tuning, partitioning for queue bloat** — real operational
  concerns *at throughput*, pure overhead at a handful of jobs/minute.

**What it costs:** a resident daemon to install/run/monitor on the Mac (fighting
the host-only, "no server-based tools" posture that already killed
Neo4j/Postgres-memory), `shared_preload_libraries` + restart rituals for the
scheduling/partitioning extensions, and a second data store to back up and
reason about alongside whatever else the orchestrator persists.

**What a file/SQLite queue buys instead:** items 1–3 above, with **zero
daemon**, a single file, and (for SQLite) `SELECT ... RETURNING` +
`BEGIN IMMEDIATE` giving an atomic claim that is entirely sufficient for
single-writer-ish workloads. YAGNI says: build the three semantics you need on
the substrate you already trust, not a queue product sized for SQS traffic.

**The scale threshold where the answer flips to Postgres** (name it, so the next
reader can check "is it true HERE?"):

| Condition | Still SQLite/files? | Postgres justified? |
|---|---|---|
| 1 machine, 1 orchestrator loop, handful of jobs | ✅ yes | ❌ no |
| 1 machine, **many truly-concurrent workers** contending on one queue (dozens+ claiming/sec) | borderline (SQLite serializes writes) | ⚠️ leaning yes |
| **>1 machine sharing one control plane / queue** | ❌ no (SQLite is not a network DB) | ✅ **clearly yes** |
| Need SQL analytics / joins / concurrent readers over live queue+state | ⚠️ | ✅ yes |
| Need managed durability, PITR, replication, RBAC across a team | ❌ | ✅ yes |

The single load-bearing flip is the **shared control plane**: the day a second
machine (or a genuinely concurrent worker pool) must claim from the same queue,
SQLite's single-file/single-writer model stops fitting and a networked server
(Postgres + pgmq) becomes the right — and now proportionate — substrate. Until
that day, it is weight without payoff.

---

## Q5 — Lightweight alternatives for THIS workload

| Option | What it gives | Fit for single-Mac, handful of multi-min tickets |
|---|---|---|
| **SQLite (WAL) + claim pattern** | Durable state + queue in one file. WAL → concurrent readers + one writer. Atomic claim via `UPDATE ... WHERE id IN (SELECT ... WHERE status='ready' LIMIT 1) RETURNING` inside `BEGIN IMMEDIATE`. Visibility-timeout = a `claimed_at`/`lease_until` column + a sweep. Same-language (Python `sqlite3`, zero dep). | ✅ **Best fit.** Delivers durability + atomic claim + retry/lease with no daemon. Matches host-only perfectly. |
| **File-based queue** (a dir of JSON files, atomic `rename()` to claim; e.g. maildir-style) | Dead-simple, inspectable, git-diffable, no dependency at all. `rename()` is atomic on the same filesystem → the claim primitive is free. | ✅ Great for *very* low volume + human-auditable tickets. Weaker on rich queries/ordering; fine at "handful". A strong default if you value inspectability over SQL. |
| **Redis** (lists/streams) | Fast queues, pub/sub, consumer groups (Streams gives visibility/ack/DLQ-ish semantics). | ⚠️ **Another resident server** — same host-only objection as Postgres, and *less* durable by default. No advantage over SQLite here; the concurrency it exists to solve isn't present. |
| **PGlite + pgmq** | Embedded pgmq semantics, no server. | ⚠️ Single-connection in-process DB in SQLite's weight class, but JS/WASM runtime + younger. Only compelling if the stack is already Node/Bun *and* you specifically want SQS-shaped semantics off the shelf. |
| **Postgres server + pgmq + pg_cron** | The full SQS+cron+SQL substrate. | ❌ Over-scaled per Q4 until the shared-control-plane threshold. |
| **Native harness primitives** (background Bash tasks, `SessionEnd`/`Stop` hooks, Routines / the `schedule` skill for cron, the `loop` skill for intervals) | Scheduling, recurring polls, one-shot timers, and "run this on completion" — **already built, already on this Mac, zero new infra.** Routines/`schedule` = cron-style cloud/local recurring agents; `loop` = run a prompt on an interval; `SessionEnd` = fire-once-at-end (cannot block); background tasks = long-running work that re-invokes on exit. | ✅ **Use these for the scheduling + event-loop half** in place of pg_cron/LISTEN-NOTIFY. They cover "wake every N minutes", "escalate after a timeout", "run on completion" natively. |

**Recommended composition for the workload:**
- **Queue + state:** SQLite (WAL) with a `tickets` table carrying
  `status/lease_until/attempts`, claimed atomically; sweep expired leases to
  re-queue. (Or a file/dir queue if inspectability trumps SQL.) This *is* the
  "write only your logic" win — the claim + lease + retry is ~40 lines, not a
  new service.
- **Scheduling + async wakeups:** the harness's Routines/`schedule` (cron) and
  `loop` (intervals) + background tasks + `SessionEnd`/`Stop` hooks — not
  pg_cron, not LISTEN/NOTIFY.
- **Escalation:** the existing GitHub/Slack/Discord paths, triggered from the
  sweep/loop.

This gives the team "write only their logic" *more* cheaply than Postgres would,
because there is **no substrate daemon to operate at all** — the substrate is a
file and the primitives the harness already ships.

---

## Recommendation

**For a single-Mac agent orchestrator doing handfuls of multi-minute tickets,
Postgres is heavier than the workload warrants.** Its distinctive value —
networked multi-client access, high-concurrency `SKIP LOCKED` claiming, MVCC,
managed durability — is exactly the value this workload does not consume, while
its cost (a resident daemon, `shared_preload_libraries`/restart rituals for the
scheduling extensions) directly contradicts the host-only constraint that
already retired Neo4j and Postgres-memory tools.

- **Do:** SQLite (WAL) + an atomic-claim/lease table for queue+state (or a
  file/dir queue for max inspectability), and the **native harness primitives**
  (Routines/`schedule`, `loop`, background tasks, `SessionEnd`/`Stop` hooks) for
  scheduling and the event loop. This is the true "write only your logic"
  outcome — no substrate service to run.
- **Don't (yet):** stand up a resident Postgres for pgmq+pg_cron. If you want
  *pgmq specifically* with no server, PGlite+`pglite-pgmq` exists — but it's a
  single-connection in-process DB in SQLite's weight class on a foreign
  (JS/WASM) runtime, so it's not worth displacing SQLite for.
- **The flip point (watch for it):** adopt Postgres+pgmq the moment the control
  plane must be **shared across more than one machine**, or a genuinely
  concurrent worker pool contends on one queue (dozens+ claims/sec). That is
  when SQLite's single-file/single-writer model stops fitting and Postgres
  becomes proportionate rather than aspirational. It is a coordination
  threshold, not a data-size one.

---

## GitHub repos touched

- [pgmq/pgmq](https://github.com/pgmq/pgmq) — the message-queue extension; visibility timeout, exactly-once-within-VT, archive/DLQ, "no background worker" design; Postgres 14–18; Tembo-originated. Also [docs](https://pgmq.github.io/pgmq/latest/) and [PGXN 1.4.0 README](https://pgxn.org/dist/pgmq/1.4.0/README.html) (partitioned-queue → pg_partman/`shared_preload_libraries` caveat).
- [citusdata/pg_cron](https://github.com/citusdata/pg_cron) — cron-in-DB by Citus/Microsoft; background worker + `shared_preload_libraries` requirement ([issue #167](https://github.com/citusdata/pg_cron/issues/167)) that disqualifies it from embedded/PGlite use.
- [electric-sql/pglite](https://github.com/electric-sql/pglite) — in-process WASM Postgres (single-user mode, single connection); the [extensions catalog](https://pglite.dev/extensions/) confirms pgmq + pgvector present, pg_cron/pg_partman absent; [`@electric-sql/pglite-pgmq`](https://pglite.dev/extensions/) is the no-server pgmq path.
- [pgq (Skytools/PgQ)](https://github.com/pgq) — Skype-origin queue + `pgqd` daemon + C extension; original tree marked [obsolete](https://github.com/pgq/skytools-legacy); [docs](https://pgq.github.io/). Legacy for a greenfield single-node orchestrator.
- [NikolayS/pgque](https://github.com/NikolayS/pgque) — modern pure-PL/pgSQL PgQ revival (no C ext, no daemon) but ticks via pg_cron; [pgque.dev](https://pgque.dev/).
- [pgpartman/pg_partman](https://github.com/pgpartman/pg_partman) — partition manager pgmq uses for partitioned queues; its bgw needs `shared_preload_libraries`.
- [zonkyio/embedded-postgres](https://github.com/zonkyio/embedded-postgres) / [fergusstrange/embedded-postgres](https://github.com/fergusstrange/embedded-postgres) — "embedded" binaries that spawn a real `postgres` child process (full extensions, but a resident server in practice).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo; host-only single-Mac constraint and native-harness-primitives context that frame the recommendation.
