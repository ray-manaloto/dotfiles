# Fit assessment: iceoryx / iceoryx2 as plumbing for a single-Mac autonomous AI-agent orchestrator

**Date:** 2026-07-19
**Question:** Is Eclipse iceoryx (C++) / iceoryx2 (Rust) an appropriate transport/coordination
substrate for an orchestrator that runs on ONE Mac, coordinating a handful of multi-minute
`claude -p` / subagent LLM tickets, with occasional human escalation via GitHub/Slack/Discord?

**Verdict up front:** **Category mismatch. Do not use iceoryx/iceoryx2.** It is a
microsecond-latency, zero-copy, real-time shared-memory data plane built to move camera/LiDAR
frames between C++ processes on one machine. Our unit of work is a multi-*minute* LLM ticket in
Python, often escalating cross-machine through cloud services. The workload iceoryx optimizes for
and the workload we have are separated by roughly **10 orders of magnitude in latency** and a
similar gulf in message frequency. Its entire value proposition (avoiding a memory copy of a large
payload) is worth nothing when the payload is a few KB of JSON produced once every few minutes.
The right primitive is Claude Code's native subagent/channel model plus a lightweight durable
queue (SQLite/file or Postgres-pgmq) — see §4.

---

## 1. What iceoryx actually IS

**Design goal.** iceoryx2 states its goal as: *"Move high-volume data efficiently and
deterministically inside data-intensive systems. Without moving the payload."* ([iceoryx.io](https://iceoryx.io/))
The original iceoryx describes a *"true zero-copy, shared memory approach that allows to transfer
data from publishers to subscribers without a single copy,"* giving *"data transmissions with
constant latency, regardless of the size of the payload."* ([eclipse-iceoryx/iceoryx README](https://github.com/eclipse-iceoryx/iceoryx))

**Latency profile.** This is a *real-time, sub-microsecond* IPC layer. iceoryx2 advertises
*"< 1 µs Latency"* and *"0 Copies per message"* with *"flat latency, independent of payload size"*
([iceoryx.io](https://iceoryx.io/)); benchmark commentary reports it reaching *~100 nanoseconds*
latency on some systems ([iceoryx2 v0.6 announcement](https://community.nodebb.org/topic/51c029fc-ffc5-42cc-9e86-c79abbb8f645/announcing-iceoryx2-v0.6-true-zero-copy-inter-prozess-communication)).
The whole point is *deterministic, constant* latency regardless of payload size — a hard-real-time
property.

**Origin.** Automotive. The iceoryx docs say it has *"origins in the automotive industry"* where
inter-process data transfers are critical for *"driver assistance or automated driving systems,"*
and it is *also* applied to *"robotics or game development"* ([iceoryx README](https://github.com/eclipse-iceoryx/iceoryx)).
It originated at Bosch and integrates with **AUTOSAR Adaptive** stacks (ETAS RTA-VRTE, AVIN AGNOSAR)
and **ROS 2** via `rmw_iceoryx` ([iceoryx README](https://github.com/eclipse-iceoryx/iceoryx)).
iceoryx2's own framing targets *"physical AI and other mission-critical systems"* with example
sources listed as *Camera, LiDAR, IMU, Actuators* ([iceoryx.io](https://iceoryx.io/)).

**Language.** Original iceoryx is **C++** (~91% of the repo). iceoryx2 is *"written in safe Rust"*
with a Rust core (~72% of the codebase) ([eclipse-iceoryx/iceoryx2 README](https://github.com/eclipse-iceoryx/iceoryx2)).

**Canonical use cases.** Real-time publish–subscribe streaming of large sensor payloads,
request–response, event signaling, and a shared-state *Blackboard*, between processes in
*mission-critical* systems ([iceoryx.io](https://iceoryx.io/)) — i.e. moving high-rate sensor and
actuator data inside a robot or an autonomous vehicle with bounded, predictable latency.

## 2. Transport model

**Shared-memory, same-machine.** iceoryx is fundamentally a **single-machine** shared-memory
transport — data lives in shared-memory segments and processes read it in place. iceoryx2 is
described as *"same-machine only … communication between multiple processes/applications on a single
system"* ([eclipse-iceoryx/iceoryx2 README](https://github.com/eclipse-iceoryx/iceoryx2)).
Cross-machine reach exists only through **add-on gateways**: iceoryx v1 offers a *"Gateway for
Cyclone DDS"* ([iceoryx README](https://github.com/eclipse-iceoryx/iceoryx)); iceoryx2 has a
**network tunnel** (Zenoh-based) that is *"still in development, so some patterns, like
request–response and blackboard, aren't supported yet"* ([iceoryx2 v0.7 release](https://ekxide.io/blog/iceoryx2-0-7-release/)).
So cross-machine is a bolt-on, not the design center.

**Message size/frequency it targets.** Large payloads (sensor frames), streamed at high frequency
(the "high-volume … data-intensive" framing). Its differentiator — *"many times faster for large
payloads"* — only materializes when payloads are big and copies are expensive ([iceoryx.io](https://iceoryx.io/)).

**Daemon (RouDi).** Original iceoryx **requires a central daemon, RouDi** ("Routing and Discovery"):
a broker that manages shared-memory segments, communication ports, service discovery, and process
lifecycle, connecting compatible publishers/subscribers — while *not* being in the data path
([RouDi Daemon, DeepWiki](https://deepwiki.com/eclipse-iceoryx/iceoryx/3.2-roudi-daemon)). A major
architectural change in **iceoryx2 is the elimination of the central daemon**: it *"embraces a fully
decentralized architecture, eliminating the need for a central daemon entirely"*
([RouDi/decentralization summary](https://deepwiki.com/eclipse-iceoryx/iceoryx/3.2-roudi-daemon)).
Either way you are operating shared-memory-segment infrastructure, not a job queue.

**Language bindings / Python.** iceoryx2 lists first-class bindings for C, C++, C#, Python and
others; Python is marked *"done"* in the README's binding matrix ([iceoryx2 README](https://github.com/eclipse-iceoryx/iceoryx2)).
But "done" here means the binding *exists* — it is a young binding over a young (post-1.0, formerly
0.x) core, wrapping a Rust real-time IPC API. There is no evidence of a mature, widely-deployed
Pythonic ecosystem the way there is for, say, `sqlite3`, `redis-py`, or `psycopg`. Python is also
the *worst* fit for iceoryx's premise: the GIL, garbage collection, and interpreter overhead
obliterate the nanosecond determinism that justifies the library's existence.

## 3. Fit for THIS workload — blunt quantification

The mismatch is not marginal; it is categorical. Line the two workloads up:

| Dimension | iceoryx targets | Our orchestrator | Mismatch |
|---|---|---|---|
| **Per-message latency that matters** | ~100 ns – <1 µs, *deterministic* | Multi-**minute** ticket; a scheduling decision that takes 100 ms is invisible | ~**10^9–10^10×** (nanoseconds vs minutes) |
| **Message frequency** | 10^4–10^6+ msg/s (sensor streams) | A handful of tickets; state changes every few seconds–minutes | ~**10^6–10^8×** |
| **Payload** | Large binary frames (camera/LiDAR), copy-cost-dominated | KB-scale JSON/text; copy cost irrelevant | zero-copy buys **nothing** |
| **Language** | C++ / Rust, real-time, no GC | Python / CLI, GC'd, `claude -p` subprocesses | GIL/GC negate determinism |
| **Topology** | Same-machine shared memory | Single Mac now, but escalation is **cloud/cross-machine** (GitHub/Slack/Discord) | cross-machine is iceoryx's weak, in-dev path |
| **Durability** | In-memory, ephemeral (data plane) | Tickets must **survive crashes/restarts** for minutes–hours | iceoryx has no durability story |
| **Real-time guarantee** | Load-bearing (safety-critical) | Irrelevant — we wait on network-bound LLM calls | paying for a guarantee we never use |

The killer points:

1. **Zero-copy is the whole product, and we don't need it.** iceoryx exists to avoid copying a
   large payload. Copying a few KB of JSON is free at our scale. We would adopt a library whose
   central feature is inert for us.
2. **Its latency budget is ~10 orders of magnitude tighter than ours.** When the *task* takes
   minutes and blocks on network I/O to an LLM, sub-microsecond transport latency is
   indistinguishable from any other option. Optimizing it is meaningless.
3. **Durability is the property we actually need, and iceoryx doesn't provide it.** A multi-minute
   ticket must survive an orchestrator restart. iceoryx is an ephemeral in-memory *data plane*; the
   moment the process dies, in-flight state is gone. Our real requirement is a *durable work queue*,
   which is a different category of tool entirely.
4. **We're often cross-machine, which is iceoryx's weakest path.** Escalation to GitHub/Slack/Discord
   and any cross-machine coordination go through cloud APIs — exactly where iceoryx's shared-memory
   model does not reach without an in-development gateway.
5. **Operational cost with no payoff.** iceoryx v1 means running and configuring RouDi; iceoryx2
   means driving a young Rust IPC core through young Python bindings and managing shared-memory
   segments — real complexity, in exchange for solving a problem (fast local data movement) we do
   not have.

**Bottom line for §3:** using iceoryx here is like laying fiber-optic backbone to pass notes between
two people sitting at the same desk. Impressive, correct engineering — for a different problem.

## 4. What IS the right primitive at this scale

Order the candidates by how much machinery they add, and stop at the first that covers the need:

1. **Claude Code's native channels + subagents + defer (start here).** The orchestrator is already
   an agent harness. Subagents/`Agent` delegations, `SendMessage` for continuing a running agent, and
   deferring/scheduling are the *native* coordination primitives — no external broker, no transport
   layer, no daemon. For "spawn a ticket, get its result back, escalate to a human," this is the
   intended mechanism and adds zero infrastructure. This is the `use-tool-builtins` answer: prefer
   the harness's built-in coordination before importing any transport.

2. **A durable work queue — the real gap iceoryx doesn't fill.** Because tickets run for minutes and
   must survive restarts, back the coordination with a *durable* store:
   - **File/SQLite queue** for a single Mac: one process, ACID, zero services to run, trivially
     inspectable, survives reboots. This is almost certainly the right weight for "a handful of
     multi-minute tickets on one machine." (The file-vs-SQLite choice is being researched
     separately — either is orders of magnitude better-matched than iceoryx.)
   - **Postgres + pgmq** if/when you outgrow one machine or want multiple orchestrator processes,
     `LISTEN/NOTIFY`, visibility timeouts, and SQL introspection. Adds a service to run; buys
     multi-consumer durability. (Also under separate research.)

   Either gives the two things iceoryx lacks and we actually need: **durability** and **at-least-once
   delivery across restarts** — at human-scale message rates where their overhead is irrelevant.

3. **Plain files / a directory as a blackboard.** For shared state between a few agents, a
   well-structured directory (or a single JSON/SQLite state file) is legible, greppable, diffable,
   and crash-safe. This matches the repo's existing `.omc/notepad.md` / `.omc/state/` conventions
   and needs no new dependency.

4. **An MCP-based blackboard** only if agents genuinely need a *shared, queryable* live state surface
   with typed access (the repo already ships a `memory` MCP). Use it when structured shared state
   earns its keep — not as the default; it adds a server and per-call cost.

**Human escalation** (GitHub/Slack/Discord) stays exactly where the prompt puts it: cloud APIs and
`gh`. None of that belongs on a shared-memory bus.

### Recommendation

Use **Claude Code native subagents/channels/defer** for coordination, backed by a **durable
file/SQLite (or later Postgres/pgmq) queue** for ticket state and restart-survival, with **plain
files** for shared blackboard state and **cloud APIs** for human escalation. Reserve an **MCP
blackboard** for the specific case of shared queryable live state.

**Do not adopt iceoryx or iceoryx2.** Judged purely on fit — setting aside how genuinely impressive
the technology is — it is a hard-real-time, zero-copy, same-machine *sensor data plane*. Our
orchestrator is a low-frequency, minutes-scale, durable, partly-cross-machine *control plane* in
Python. Overkill understates it; it is a category mismatch. The engineering it optimizes (nanosecond
copy-free transport) is precisely the dimension our workload does not care about, and the property we
do need (durability across restarts) is one it does not offer.

## GitHub repos touched

- [eclipse-iceoryx/iceoryx](https://github.com/eclipse-iceoryx/iceoryx) — original C++ iceoryx: zero-copy shared-memory model, automotive/AUTOSAR/ROS 2 origin, DDS gateway.
- [eclipse-iceoryx/iceoryx2](https://github.com/eclipse-iceoryx/iceoryx2) — Rust successor: latency claims, same-machine scope, Python-binding status, decentralized (no-RouDi) design.
- [ros2/rmw_iceoryx](https://github.com/ros2/rmw_iceoryx) — referenced as the ROS 2 middleware integration for iceoryx (robotics use case).
- [eclipse-zenoh/zenoh](https://github.com/eclipse-zenoh/zenoh) — the network layer behind iceoryx2's in-development cross-machine tunnel.
