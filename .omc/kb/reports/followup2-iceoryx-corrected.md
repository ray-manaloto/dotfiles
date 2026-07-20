# Corrected ground-truth re-assessment: iceoryx / iceoryx2 for a distributed AI-agent orchestrator

**Date:** 2026-07-19
**Supersedes (on the multi-machine facts):**
`followup-iceoryx-fit.md` in this same directory.
**Why this exists:** the maintainer flagged the prior report's core premise —
"iceoryx is same-machine only, cross-machine is a weak in-development bolt-on,
category mismatch, don't use" — as **factually wrong and unfairly dismissive**.
This report re-establishes ground truth from current (2025-2026) sources and
real-project evidence, then re-judges fit honestly. **Two of the prior report's
factual claims were wrong or stale; one structural objection survives the
correction and is still decisive for *our* use.** Details below, not a verdict
inherited from the earlier file.

---

## 0. What the prior report got wrong (the corrections, up front)

| Prior claim | Corrected fact | Evidence |
|---|---|---|
| "iceoryx2 is **same-machine only**; cross-machine exists only through add-on gateways." | **False as of v0.7.0 (2025-09-13).** iceoryx2 ships a **Zenoh network tunnel** (`iceoryx2-tunnels-zenoh` crate, run via `iox2 tunnel zenoh`) that makes **publish-subscribe and event** communication work **across machines** out of the box, "with no complicated configuration." | [v0.7 release](https://ekxide.io/blog/iceoryx2-0-7-release/); [iceoryx2-tunnels-zenoh on crates.io](https://crates.io/crates/iceoryx2-tunnels-zenoh) |
| "cross-machine is iceoryx's **weak, in-development** path" (used as a disqualifier) | **Half-right, over-weighted.** The tunnel *is* still early-stage/in-development and does **not yet** carry request-response or blackboard across hosts — but it is **released and functional** for pub-sub + event, not vaporware. The dismissive framing was overstated. | [v0.7 release](https://ekxide.io/blog/iceoryx2-0-7-release/) |
| "Blackboard status?" left as an open question; "Python binding is young, worst fit (GIL kills it)." | **Blackboard is DONE and usable from Python** (bindings finalized v0.8.0, 2025-12-23). Python is a **first-class binding**; v0.9.0 (2026-05-18) made Python blocking APIs **release the GIL while waiting**, directly addressing the GIL objection. | [v0.8 release](https://ekxide.io/blog/iceoryx2-0.8-release/); [v0.9 release](https://ekxide.io/blog/iceoryx2-0.9-release/) |
| (implicit) "category mismatch, do not use." | **Not a-priori true.** iceoryx2 is a legitimate, cross-language, cross-machine-*capable* data plane used in real robotics systems. The honest verdict is narrower and rests on one real gap (durability), not on a category error — see §4. | this report |

**What the prior report got right and still stands:** iceoryx2 is a
zero-copy, sub-microsecond *data plane*; its headline value (avoiding a copy of
a large payload) is inert for KB-scale JSON at minute cadence; and it has **no
durability across restarts**. Those points survive the correction and turn out
to be the load-bearing ones (§4).

---

## 1. Multi-machine / network transport — the corrected facts (with versions + dates)

**iceoryx2 (Rust core) cross-machine, via the Zenoh tunnel:**

- **Shipped v0.7.0, 2025-09-13.** The `iceoryx2-tunnels-zenoh` package was
  published at 0.7.0. You run `iox2 tunnel zenoh` on each host and
  "publish-subscribe and event communication is instantly available across
  machines." ([v0.7 release](https://ekxide.io/blog/iceoryx2-0-7-release/),
  [crates.io versions](https://crates.io/crates/iceoryx2-tunnels-zenoh/versions))
- **What crosses the network today:** pub-sub ✅, event ✅.
  **Request-response ❌ and blackboard ❌** are *not yet* supported over the
  tunnel — "still in development, so some patterns, like request-response and
  blackboard, aren't supported yet."
  ([v0.7 release](https://ekxide.io/blog/iceoryx2-0-7-release/))
- **Gateway roadmap:** the tunnel is "the first step toward a full gateway"
  where "you start a gRPC, MQTT, or DDS gateway, and suddenly your iceoryx2
  application can talk to anything" without code changes. The
  [ROADMAP](https://github.com/eclipse-iceoryx/iceoryx2/blob/main/ROADMAP.md)
  lists host-to-host via `smoltcp`, Zenoh (MVP), plus MQTT/DDS/SOME-IP/DBus/
  WebSocket gateways as future work.
- **Latest release:** **v0.9.0, 2026-05-18.** ekxide states iceoryx2 **v1.0 is
  planned before the end of 2026.**
  ([v0.9 release](https://ekxide.io/blog/iceoryx2-0.9-release/))

**iceoryx v1 (C++) cross-machine:** production-proven path is the **Cyclone DDS
gateway** (`iceoryx-gw-iox-dds`), long used in the ROS 2 ecosystem. This is the
mature, battle-tested cross-machine story if you want DDS/ROS 2 interop today.
([iceoryx README](https://github.com/eclipse-iceoryx/iceoryx))

**Bottom line:** cross-machine messaging is real and released — but as of
mid-2026 the network tunnel is a **pub-sub + event** transport, still pre-1.0,
and does **not** yet carry the request-response or blackboard patterns across
hosts. "Weak bolt-on" was too harsh; "released, early, pattern-limited" is
accurate.

## 2. Full current feature set (v0.9.0, 2026-05)

**Messaging patterns — all implemented today (same-machine):**

| Pattern | Status | Notes |
|---|---|---|
| Publish-Subscribe | ✅ done | zero-copy; cross-machine via tunnel |
| Event / signalling | ✅ done | cross-machine via tunnel |
| Request-Response (streams) | ✅ done | v0.9 added source `UniqueNodeId` in headers; **same-machine only** across the tunnel |
| **Blackboard** (shared-memory **key-value** repository) | ✅ done | introduced v0.7 (Rust), **C/C++/Python bindings finalized v0.8**; **same-machine only** |
| WaitSet (event multiplexer, reactor pattern) | ✅ done | multiplex across many services |
| Pipeline | ⏳ planned | on roadmap |

Sources: [iceoryx2 README](https://github.com/eclipse-iceoryx/iceoryx2),
[v0.7](https://ekxide.io/blog/iceoryx2-0-7-release/),
[v0.8](https://ekxide.io/blog/iceoryx2-0.8-release/),
[v0.9](https://ekxide.io/blog/iceoryx2-0.9-release/),
[iceoryx2 Book](https://ekxide.github.io/iceoryx2-book/main/introduction.html).

Note on the **blackboard**: it is a *key-value repository in shared memory* for
the "one writer, many readers of current state" case (introduced to serve
"hundreds or thousands of subscribers" from a single publisher). It is a
*current-state* store — conceptually adjacent to an "agent blackboard," but it
is sensor/state-repository semantics, **not** a durable/queryable database.

**Language bindings:** Rust (core), **C, C++, Python, C#** — all shipping.
Python got **full bindings in v0.7** and **GIL-release on blocking calls in
v0.9**. Cross-language **zero-copy** works across Rust/C/C++/Python (no
serialization). Go/Lua/Java/Zig are mentioned as further targets.
([README](https://github.com/eclipse-iceoryx/iceoryx2),
[v0.9](https://ekxide.io/blog/iceoryx2-0.9-release/))

**Platforms:** Linux (x86_64/aarch64/32-bit), macOS, Windows, FreeBSD, QNX 7.1
& 8.0 done; Android/VxWorks experimental. **no_std** support added (v0.8),
enabling bare-metal / RTOS. v0.9 added **Docker support with PID-namespace
handling** and a **decentralized crash-recovery** mechanism (recovers leaked
indices when a process dies — *within a live session*).

**Durability — the persistent gap:** iceoryx2's shared memory is **volatile /
ephemeral**. v0.9's recovery survives *process crashes within the same system
session*; it does **not** persist across a full stop / reboot. The sender owns
the payload and cleans it up when it goes out of scope — this is a *data-plane*
lifetime model, not a durable message queue.
([v0.9 release](https://ekxide.io/blog/iceoryx2-0.9-release/);
[FAQ](https://github.com/eclipse-iceoryx/iceoryx2/blob/main/FAQ.md);
["The Many Challenges of Shared Memory"](https://www.danscoding.world/posts/iceoryx2/))

## 3. Real projects using iceoryx / iceoryx2 (the core ask)

I searched GitHub, crates.io reverse-deps, release notes, blogs, HN, and FOSDEM.
Honest findings — what's real, and how central iceoryx2 actually is in each:

**Genuine adopters (robotics / middleware):**

- **Copper** — [`copper-project/copper-rs`](https://github.com/copper-project/copper-rs),
  a deterministic robot OS in Rust. Ships a **`cu_iceoryx2_bridge`** for IPC,
  bumped to **iceoryx2 0.8** in Copper v0.13.0 (Feb 2026). **Honest nuance:**
  iceoryx2 is an **optional transport bridge**, *not* Copper's backbone —
  Copper's runtime is CopperList local scheduling, and its **distributed /
  multi-robot** deployments actually go through **Zenoh bridges** and explicit
  multi-Copper topology configs, not the iceoryx2 tunnel. So Copper is real
  usage, but it is *not* evidence that iceoryx2 is a multi-machine backbone —
  it's evidence that even a Copper-scale robotics project reaches for **Zenoh**
  for the cross-machine tier. ([Copper release notes](https://github.com/copper-project/copper-rs/wiki/Copper-Release-Notes))
- **rmw_iceoryx2** — [`ekxide/rmw_iceoryx2`](https://github.com/ekxide/rmw_iceoryx2),
  a **ROS 2 middleware (RMW) implementation** on iceoryx2. This *does* make
  iceoryx2 a messaging backbone for ROS 2 robotics stacks. Maintained by ekxide
  (the company behind iceoryx2).
- **iceoryx v1** in production ROS 2 via `rmw_iceoryx` + the Cyclone DDS
  gateway; automotive/AUTOSAR Adaptive heritage (Bosch origin).
- ekxide states iceoryx2 "is already used in **robotics, automotive, medical,
  finance**" — but **customers are unnamed** (open-core model; named production
  users are not public). Treat the domain list as vendor claim, not verified
  deployments. ([ekxide philosophy](https://ekxide.io/philosophy/))

**AI / model-serving interest (proposed, not adopted):**

- **LitServe** (Lightning AI's LLM/model serving framework) —
  [issue #559 "Iceoryx2 queues"](https://github.com/Lightning-AI/litserve/issues/559):
  a user **proposed** iceoryx2 for LitServe's inter-process queue mechanism,
  citing zero-copy, <1µs latency, GB/s transfers. **Status: open, no maintainer
  buy-in, no PR, no decision.** So there is *interest* in the AI-serving space —
  but for the **data plane** (moving large tensors/batches between serving
  processes), not for agent orchestration.

**Multi-agent AI orchestration / LLM message bus / agent blackboard —
searched, found NONE.** Despite iceoryx2 having a "blackboard" pattern, I found
**no** project using iceoryx/iceoryx2 as an AI/LLM multi-agent coordination bus
or an agent-state blackboard. The "blackboard" in iceoryx2 is a shared-memory
current-state key-value store for high-fan-out sensor/state distribution — the
name collides with the AI "blackboard architecture," but the real usage is
robotics state, not agent reasoning. This is an **honest negative**, reported as
requested: the AI-agent-bus use case is not one iceoryx2 is used for in the
wild today.

## 4. Honest fit re-assessment for OUR use

Our need: a distributed AI-agent orchestrator with (a) a pub-sub or blackboard
bus for agent-to-agent coordination + shared state, (b) possibly multi-machine,
(c) control plane may run **in a container** (host-only constraint applies to
the graphify substrate, not the control plane).

**Where iceoryx2 genuinely could fit (correcting the prior over-dismissal):**

- It **does** have pub-sub + event **across machines** (Zenoh tunnel), and a
  **blackboard** shared-state store usable **from Python** — the two primitives
  the ask names. This is no longer a "same-machine only" tool.
- **Container is fine.** v0.9 added Docker/PID-namespace support; running the
  control plane in a container is not a blocker.
- **Polyglot zero-copy** is a real asset *if* the fleet mixes Rust/C++/Python
  processes moving large payloads (model outputs, artifacts) between co-located
  agents.

**Where it still falls short — and these are decisive for a control plane:**

1. **No durability across restarts (the killer, unchanged by the corrections).**
   Agent tickets run minutes-to-hours and must survive an orchestrator
   restart/reboot. iceoryx2 is a *volatile data plane*: the blackboard and
   queues live in shared memory that is gone on a full stop. v0.9's recovery is
   *crash-recovery within a live session*, not persistence. A control plane
   needs a durable store (SQLite/Postgres/pgmq, or a broker with persistent
   subscriptions) — a **different category of tool**. This is architectural, not
   a maturity gap that a version bump fixes.
2. **Cross-machine covers the wrong patterns for coordination.** The tunnel
   carries **pub-sub + event** across hosts, but **not request-response or
   blackboard**. Multi-machine *shared agent state* (blackboard) and *ask-and-
   wait* coordination (request-response) — the two things an agent orchestrator
   most wants across hosts — are exactly what the tunnel does **not** do yet.
3. **No queue/broker semantics.** No at-least-once-across-restart, no
   dead-letter, no durable consumer groups, no ack/retry. You'd rebuild all of
   that on top. It's sensor-firehose semantics, not work-queue semantics.
4. **Its headline value is inert for us.** Nanosecond zero-copy of large
   payloads buys nothing for KB JSON tickets at minute cadence — a real cost
   (pre-1.0 IPC core, shared-memory ops) for a benefit we don't consume. (Prior
   report was right here.)
5. **Human escalation** (GitHub/Slack/Discord) is cloud-API territory and never
   belongs on a shared-memory bus. Unchanged.
6. **Pre-1.0** (0.9.0). API still converging toward the end-of-2026 1.0.

**Evidence-based verdict (not a-priori):**

- For the **durable control plane / message bus / agent blackboard we actually
  need** — the answer is still **no, don't build it on iceoryx2**, but for a
  *corrected and narrower* reason than the prior report gave: not "same-machine
  category mismatch," but **"it is a non-durable data plane, and its
  cross-machine transport doesn't yet carry the coordination patterns
  (request-response, blackboard) we'd depend on."** The real-project evidence
  agrees — even Copper reaches for **Zenoh**, not the iceoryx2 tunnel, for its
  distributed tier, and the one AI-serving nibble (LitServe) is about the *data
  plane*, not orchestration.
- For a hypothetical **future high-throughput data-plane tier** — co-located
  polyglot processes shovelling large tensors/artifacts with zero copies —
  iceoryx2 is a **legitimate, credible option** (that's precisely what LitServe
  and Copper eye it for). If the program ever grows that tier, revisit it there.
  That is not our control-plane need today.

**Recommended primitive (unchanged in destination, corrected in reasoning):**
a **durable queue/store** for control-plane state and restart-survival (SQLite
or file on one node; Postgres + pgmq / a persistent broker when multi-process
or multi-machine), plain files / a small DB for the shared blackboard, and
**Zenoh** (not the iceoryx2 tunnel) if/when a true cross-machine pub-sub bus is
needed — because Zenoh is the mature, durable-capable, routed transport the
robotics projects themselves pick for that job, and iceoryx2 sits *on top of*
Zenoh for its own cross-machine story anyway.

**One-line honest summary:** the prior report's *facts* about multi-machine were
outdated (cross-machine pub-sub/event is real and released; blackboard + Python
are done) and its *tone* was unfairly dismissive — but its *conclusion for our
control plane* happens to survive on a different, correct basis: iceoryx2 is a
non-durable data plane whose network tier doesn't yet carry request-response or
blackboard, so it is the wrong tool for a durable, coordinating agent control
plane, while remaining a genuine candidate for a future co-located zero-copy
*data* tier.

## GitHub repos touched

- [eclipse-iceoryx/iceoryx2](https://github.com/eclipse-iceoryx/iceoryx2) — README feature/binding matrix, ROADMAP, FAQ (durability), versions/patterns.
- [eclipse-iceoryx/iceoryx](https://github.com/eclipse-iceoryx/iceoryx) — iceoryx v1 (C++): Cyclone DDS gateway cross-machine path, ROS 2 / AUTOSAR heritage.
- [ekxide/rmw_iceoryx2](https://github.com/ekxide/rmw_iceoryx2) — ROS 2 RMW implementation on iceoryx2 (real messaging-backbone usage).
- [copper-project/copper-rs](https://github.com/copper-project/copper-rs) — Rust deterministic robot OS; `cu_iceoryx2_bridge` on iceoryx2 0.8, but uses Zenoh for its distributed tier.
- [Lightning-AI/litserve](https://github.com/Lightning-AI/litserve) — issue #559 proposing iceoryx2 for AI model-serving queues (open, no adoption).
- [eclipse-zenoh/zenoh](https://github.com/eclipse-zenoh/zenoh) — the routed transport behind iceoryx2's cross-machine tunnel; the primitive robotics projects pick for the distributed tier.

_Non-repo sources also consulted:_ ekxide release blogs v0.7 (2025-09-13), v0.8
(2025-12-23), v0.9 (2026-05-18); the iceoryx2 Book; `iceoryx2-tunnels-zenoh` on
crates.io; FOSDEM 2026 "Meet iceoryx2" listing; "The Many Challenges of Shared
Memory" (danscoding.world).
