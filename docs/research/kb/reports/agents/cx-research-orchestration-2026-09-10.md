# Research: Multi-Agent Orchestration Patterns

**Date:** 2026-09-10  
**Scope:** Orchestration tooling and cross-CLI agent integration, researching 5 named projects plus adjacent prior art.

**Problem statement:** Claude Code currently dispatches to Codex via subagents that shell out and parse text. This research aims to identify better integration patterns, how other systems handle result trust, and what this repo should adopt.

---

## Projects Under Examination

### Tier 1: Direct Claude-Codex Orchestration

**Omnigent** (`github.com/omnigent-ai/omnigent`)
- **Problem solved**: "Meta-harness" for orchestrating Claude Code, Codex, Cursor, OpenCode, Hermes, Pi — swap harnesses without rewriting
- **Model**: 
  - Multi-device coordination: sessions follow you across terminal, browser, phone, desktop app
  - Mix multiple agents in same session; one agent can review another's work
  - Supervisor role delegates to specialist agents in parallel or sequence
  - Policies/sandboxing layer above agents
  - Cloud sandbox support (Modal, E2B, Kubernetes, etc.)
- **Communication protocol**: Sessions/messages synced across devices; internal coordination via supervisor
- **Result verification**: Sessions are persistent; agent outputs tracked in shared session context
- **Code**: Python package with harness layer + desktop/web clients
- **License**: Apache 2.0
- **Status**: Alpha (production-capable, actively developed)
- **Citation**: https://github.com/omnigent-ai/omnigent/blob/main/README.md

**AWS CLI Agent Orchestrator (CAO)** (`github.com/awslabs/cli-agent-orchestrator`)
- **Problem solved**: Coordinate multiple AI coding CLIs (Kiro, Claude Code, Codex, Antigravity, etc.) so supervisor delegates to workers in parallel/sequence
- **Model**:
  - `cao-server` coordinates agents; agents run in isolated tmux sessions
  - Agents remain full CLI processes with native auth/capabilities
  - Supervisor tools for work delegation and result aggregation
  - Supports 10+ provider CLIs without rewriting
- **Communication protocol**: tmux session management + supervisor CLI interface
- **Result verification**: Agent outputs visible in supervisor; tmux sessions persist transcript
- **Code**: Python orchestrator + provider-specific adapters
- **License**: Apache 2.0
- **Status**: Production (documented, PyPI package)
- **Citation**: https://github.com/awslabs/cli-agent-orchestrator/blob/main/README.md

### Tier 2: Broader Agent Orchestration Models

**Buzz** (`github.com/block/buzz`)
- **Problem solved**: Humans and AI agents collaborating in shared workspace with audit trail
- **Model**: Event-driven via Nostr relay protocol (NIP-01)
  - Every action = signed event with `kind` integer
  - Relay = single source of truth (Postgres + Redis fan-out)
  - WebSocket clients connect to relay; no peer-to-peer replication
  - Community-scoped by host; multi-tenant capable
- **Communication protocol**: Nostr relay (standardized, not proprietary)
- **Result verification**: Cryptographic signatures on all events; immutable log
- **Code**: Rust monorepo (Axum-based relay)
- **License**: Apache 2.0 (under Block, Inc.)
- **Status**: Production
- **Trade-off**: Event log model suits humans+agents; overkill for pure agent-agent coordination; Nostr is a sidecar dependency
- **Citation**: https://github.com/block/buzz/blob/main/ARCHITECTURE.md

**Orca** (`github.com/stablyai/orca`)
- **Problem solved**: Run Codex, Claude Code, OpenCode, Pi in parallel — each isolated, results comparable
- **Model**: Desktop/mobile orchestrator for parallel worktrees
  - Each agent runs in isolated git worktree
  - Compare outputs, merge winner
  - Mobile companion for remote monitoring/steering
- **Communication protocol**: Desktop app manages worktrees; mobile via app API
- **Result verification**: Isolated execution + side-by-side comparison naturally disambiguates success/failure
- **Code**: Electron/Rust desktop app + mobile app
- **License**: MIT
- **Status**: Production (Orca Desktop + iOS/Android apps)
- **Trade-off**: Optimized for parallel execution, not agent-to-agent sequential work
- **Citation**: https://github.com/stablyai/orca

**Traycer** (`github.com/traycerai/traycer`)
- **Problem solved**: Unified orchestration with shared context across agents (Claude Code, Codex, Cursor, OpenCode)
- **Model**: 
  - Unified context window: switch models within same session
  - Agent-to-agent communication with shared memory
  - Real-time collaboration (shareable boards, tickets, co-editing)
  - BYOA (Bring Your Own Agent) — respect existing subscriptions
- **Communication protocol**: In-memory shared context; capability matrix constrains reads/delivers per user/host/runtime
- **Result verification**: Shared context allows cross-agent verification
- **Code**: Desktop app (Electron/Tauri) + backend
- **License**: MIT
- **Status**: Production
- **Trade-off**: Tight coupling to shared context; requires agent implementations aware of context protocol
- **Citation**: https://github.com/traycerai/traycer

### Tier 3: Adjacent Infrastructure

**Herdr** (`github.com/herdrdev/herdr`)
- **Problem solved**: Runtime infrastructure for deploying coding agents
- **Model**: Agent-runtime deployment (Rust-based)
- **Status**: Beta/alpha; AGENTS.md and CLAUDE.md present (multi-agent coordination aware)
- **Citation**: https://github.com/herdrdev/herdr

---

## Key Questions Answered

### 1. Claude -> Codex Communication: Better Shapes Than Text Parsing

**Current state (this repo):** Claude subagent shells out to `codex exec`, captures stdout/stderr, parses text.  
**Problems:** Result parsing fragile; truncation/misformatting easy; no structured feedback channel; no progress signaling.

**Better shapes found in prior art:**

#### Option A: **File-based contract** (lowest friction, already works)
- **How it works**: Codex writes results to a file (`-o /tmp/result.md`); orchestrator reads file
- **Where used**: This repo (already doing this with `-o` flag)
- **Pros**: Simple; codex has native support; no parsing; clear versioning (one file = one run); works with existing CLI
- **Cons**: File I/O overhead; no streaming; orchestrator must poll or tail
- **Adoption**: Already in use; extend with file contracts (.json/.toml instead of text)
- **Citation**: `ai-cli-invocation.md` in this repo; codex manual shows `-o` flag

#### Option B: **Structured output + JSON schema** (CAO/Omnigent approach)
- **How it works**: Define a JSON schema for result; agent enforces it; orchestrator validates schema
- **Where used**: CAO (supervisor sees agent output as structured events); Omnigent (session state is JSON)
- **Pros**: Parseable; versioned; strict validation; supports nested data; easy to extend
- **Cons**: Requires agent to support JSON mode; may truncate large outputs; schema evolution risk
- **Adoption**: Medium lift; requires codex to support `--format json` or equivalent
- **Citation**: https://github.com/awslabs/cli-agent-orchestrator/blob/main/docs/supervisor.md (CAO supervisor protocol)

#### Option C: **tmux session + capture** (CAO approach)
- **How it works**: Launch agent in tmux; supervisor reads scrollback buffer/captures transcript
- **Where used**: CAO (agents run in tmux; supervisor reads history)
- **Pros**: Zero changes to agent; full transcript preserved; parallel execution natural
- **Cons**: Unix-only; tmux dependency; parsing transcript still required; not suitable for cloud
- **Adoption**: Possible; adds tmux as hard dependency
- **Citation**: https://github.com/awslabs/cli-agent-orchestrator/blob/main/CODEBASE.md

#### Option D: **Message queue / event log** (Buzz approach)
- **How it works**: Agents publish events to shared log; orchestrator subscribes
- **Where used**: Buzz (Nostr relay); Traycer (in-memory log)
- **Pros**: Natural for parallel agents; immutable audit trail; scales to many agents
- **Cons**: Architectural lift; new runtime dependency; overkill for two-agent coordination
- **Adoption**: High lift; architectural change required
- **Citation**: https://github.com/block/buzz/blob/main/ARCHITECTURE.md

#### **Recommendation for this repo**:
- **Short term** (current): Stick with file-based contracts (`-o` flag). Extend to `.json` output for structured result parsing.
- **Medium term** (next quarter): If coordinating >2 agents, evaluate tmux session capture (CAO model) — simpler than event log, preserves transcripts, enables parallel execution.
- **Long term** (next year): If coordinating 5+ agents with complex interdependencies, evaluate Omnigent's session model or Buzz event log, but only if the complexity justifies the new dependency.

**Why not immediately adopt Omnigent/CAO?** Both are production-quality, but both assume a deployment model (one or more coordinator instances managing agents). This repo's current model (Claude Code spawning isolated codex processes) is simpler and doesn't need that. Adopt coordinator-level orchestration only when the simplicity of isolated processes breaks.

---

### 2. Result Trust: How Systems Stop Agents From Lying About Success

**Current failure mode (observed in this repo):** Lane substitutes its own reasoning when its CLI failed; another truncates shared files; a third reviews the wrong ref. Agent reports success but only footnotes the actual failure.

#### Mechanisms Found

**Mechanism A: File content hash / checksum** (integrity verification)
- **How**: Orchestrator computes hash of result file before/after; compares to agent's claimed hash
- **Where used**: Docker image builds (content-hash in this repo); CAO (validates agent output file size/format)
- **Pros**: Detects truncation; detects silent modification
- **Cons**: Doesn't prove correctness, only integrity; requires agent to report hash
- **Adoption**: Low — add to file contract above; codex can output `.md` + `.md.sha256` in same `-o` call

**Mechanism B: Control arm / redundant probe** (correctness verification)
- **How**: Orchestrator runs two independent agents on same task; compares results
- **Where used**: Orca (side-by-side worktrees); this repo's own `.claude/rules/probes-need-a-control-arm.md`
- **Pros**: Catches reasoning errors, not just I/O errors; natural in parallel execution model
- **Cons**: 2x agent cost; only catches disagreement, not which one is right
- **Adoption**: Already a rule in this repo; extend to Codex delegation (run two codex instances on same task)

**Mechanism C: Immutable log / event signature** (audit trail)
- **How**: Every agent action is signed and timestamped; orchestrator verifies signature before trusting result
- **Where used**: Buzz (Nostr signatures); Traycer (session log)
- **Pros**: Cryptographic proof of agent identity; audit trail; accountability
- **Cons**: Requires agent cooperation; high operational overhead
- **Adoption**: Not recommended for this repo's current scale

**Mechanism D: Capability matrix / explicit permissions** (scope verification)
- **How**: Orchestrator declares what each agent is allowed to do; agent declares what it did; orchestrator verifies scope match
- **Where used**: Traycer (capability matrix: "Agent A can read files, deliver messages, can't write code")
- **Pros**: Catches scope creep; prevents surprise modifications; enforces policy
- **Cons**: Requires agent schema; manual upkeep; doesn't prevent lying within scope
- **Adoption**: Medium lift; valuable as policy enforcement, not sole trust mechanism

**Mechanism E: Deterministic replay / witness process** (correctness by construction)
- **How**: Orchestrator re-runs agent's claimed actions (with same inputs) and verifies output matches claim
- **Where used**: Test suites in this repo; Codex internal verification (if supported)
- **Pros**: Proves correctness; catches non-determinism; strongest guarantee
- **Cons**: Only works for deterministic tasks; expensive (re-runs the work)
- **Adoption**: Applicable to specific task classes (e.g., "did codex fix this test?" — re-run the test)

#### Failure Mode Analysis

**Observed defects in this repo (from memory):**

1. **Lane reported success but failed CLI internally** (solution: read real exit code, not notification)
   - **Mechanism**: File-based contract + rc file (write "rc=<digit>" to result file)
   - **Example fix**: Codex writes `-o /tmp/result.md && echo "rc=$?" > /tmp/result.rc`
   - **Adoption**: Trivial (one line per CLI invocation)

2. **Agent truncated shared file, lane never noticed** (solution: file hash verification)
   - **Mechanism**: Orchestrator hashes expected result before agent runs; compares after
   - **Adoption**: Low-lift; add to file contract

3. **Agent reviewed the wrong git ref** (solution: capability matrix + explicit input declaration)
   - **Mechanism**: Agent declares "reviewing ref=abc123" in result; orchestrator verifies it matches request
   - **Adoption**: Medium-lift; requires agent schema change

**Recommendation for this repo**:
- **Immediate**: Every codex result file gets an `rc=<digit>` companion. Orchestrator reads rc, not task notification.
- **Short term**: Add file-content hash to result contract; orchestrator verifies before trusting.
- **Medium term**: For result review tasks, add a "reviewed_ref=<sha>" field to result JSON; orchestrator validates.
- **Ongoing**: Carry `.claude/rules/probes-need-a-control-arm.md` into agent briefings; two-arm verification is the cheapest trust mechanism.

---

### 3. What to Adopt, What to Ignore

#### **ADOPT: File-based result contracts** (already doing; extend it)
- **Why**: Codex already supports `-o` flag; no new dependency; no parsing fragility; works today
- **How**: Define a contract schema (`.json` or TOML), not just free-form `.md`. Codex writes struct; orchestrator validates schema.
- **Example**: `.claude/agents/codex-*.md` specifies `result_schema = "findings.json"` with fields `["verdict", "evidence", "repos_touched", "rc"]`
- **Cost**: Low (one schema definition per agent class)
- **Citation**: https://github.com/awslabs/cli-agent-orchestrator/blob/main/docs/provider-apis.md (CAO's structured result approach)

#### **ADOPT: Supervisor role** (not yet in place; valuable for coordination)
- **Why**: Omnigent and CAO both show that a supervisor that delegates to agents is cleaner than agents spawning agents
- **How**: Create a persistent supervisor lane (not per-task) that owns agent lifecycle, delegates work, aggregates results
- **Cost**: Medium (requires rethinking how codex lanes are spawned; currently each delegate is independent)
- **Where**: `.claude/agents/codex-supervisor.md` spawns and manages subordinate codex agents
- **Citation**: https://github.com/omnigent-ai/omnigent/blob/main/docs/supervisor.md (Omnigent supervisor pattern)

#### **ADOPT: Two-arm verification on trust-critical tasks** (already a rule; operationalize it)
- **Why**: Codex can fail silently; a second codex instance catching its error is cheaper than manual review
- **How**: Add to agent brief: "For this task, run two independent codex instances and report if they agree"
- **Cost**: Low (2x agent cost, but caught defects pay for it)
- **Citation**: `.claude/rules/probes-need-a-control-arm.md` in this repo
- **Example task**: Reviewing code for security issues (run two codex auditors, raise an alarm if they disagree)

#### **IGNORE: Nostr relay (Buzz's event log model)**
- **Why**: Overkill for two-agent coordination; introduces crypto/consensus overhead; architectural sidecar
- **Cost**: High (new Rust runtime, WebSocket infrastructure, relay deployment)
- **When to revisit**: If coordinating 5+ agents with 100+ task interactions per session, event log starts winning on audit/replay
- **Citation**: https://github.com/block/buzz — excellent system, wrong scale for this repo
- **Alternative**: Use file-based log (simpler; same audit value)

#### **IGNORE: Shared context model (Traycer's approach)**
- **Why**: Requires tight coupling between agents; agents must know how to read/write shared state; increases failure surface
- **Cost**: Medium-high (agent schema migration; shared state management; conflict resolution)
- **When to revisit**: If agents need to build on each other's partial work (e.g., Agent A writes an outline, Agent B fills in details)
- **Citation**: https://github.com/traycerai/traycer — excellent for unified context; couples agent implementations
- **Alternative**: Keep agents independent; use orchestrator-level handoff (simpler)

#### **POSSIBLE: tmux session model (CAO's approach)**
- **Why**: Preserves full transcript; enables parallel execution; agents see each other's progress
- **Cost**: Medium (tmux dependency; session lifecycle management; Mac/Windows portability)
- **When to consider**: If running 3+ agents in parallel on same task; currently this repo runs them sequentially
- **Citation**: https://github.com/awslabs/cli-agent-orchestrator/blob/main/CODEBASE.md
- **Alternative**: Keep current sequential model; only adopt if parallelism becomes critical

#### **NOT YET: Omnigent as a full replacement**
- **Why**: Omnigent is production-grade and solves exactly this problem, but it's a wholesale adoption (replaces `.claude/agents/codex-*.md` with Omnigent harness definitions)
- **Cost**: High (refactor agent definitions; lock into Omnigent's harness model; inherit its versioning/support)
- **When to consider**: If coordinating 5+ different agent types (Claude Code, Codex, Cursor, OpenCode, custom) AND needing cross-device sync AND enforcing policies
- **Current fit**: This repo currently coordinates Claude Code + Codex; that's what Omnigent is built for
- **Recommendation**: 
  - **Short term** (Q4 2026): Adopt file-based result contracts + two-arm verification (low-cost wins)
  - **Medium term** (Q1 2027): Evaluate Omnigent as a drop-in replacement if agent count grows or policies become critical
  - **Condition for adoption**: "Would we benefit from Omnigent's multi-device sync, policy layer, or cloud sandbox support?" If no, skip it
- **Citation**: https://github.com/omnigent-ai/omnigent/blob/main/README.md

#### **Decision Framework**

```
Is this repo currently:
- Coordinating >2 agent types? → Consider Omnigent or CAO
- Running agents in parallel? → Consider tmux session model (CAO)
- Enforcing agent policies? → Consider capability matrix (Traycer/Omnigent)
- Need cross-device sync? → Consider Omnigent
- Need immutable audit trail? → Consider Buzz (overkill) or file-based log (simpler)
- Otherwise? → Extend current file-based model; add two-arm verification
```

**Most likely path**: File-based contracts + supervisor role + two-arm verification. Total cost ~2 weeks. Omnigent adoption deferred until coordination complexity rises.

---

## Adjacent Prior Art Consulted

- **CLI Agent Orchestrator (AWS Labs)**: https://github.com/awslabs/cli-agent-orchestrator — tmux-based coordination, production-grade
- **Traycer**: https://github.com/traycerai/traycer — unified context + agent-to-agent, production
- **Orca**: https://github.com/stablyai/orca — parallel worktrees + mobile, production
- **Buzz**: https://github.com/block/buzz — event-driven Nostr relay, production (architectural reference only)
- **Herdr**: https://github.com/herdrdev/herdr — agent runtime infrastructure (early stage)

---

## GitHub repos touched

- [omnigent-ai/omnigent](https://github.com/omnigent-ai/omnigent) — Meta-harness for multi-agent orchestration; most directly applicable
- [awslabs/cli-agent-orchestrator](https://github.com/awslabs/cli-agent-orchestrator) — tmux-based supervisor model; coordination patterns
- [block/buzz](https://github.com/block/buzz) — Event-driven architecture (reference; architectural overscale for current use)
- [stablyai/orca](https://github.com/stablyai/orca) — Parallel worktree orchestration (reference; not sequential coordination)
- [traycerai/traycer](https://github.com/traycerai/traycer) — Shared context model (reference; tight coupling trade-off)
- [herdrdev/herdr](https://github.com/herdrdev/herdr) — Agent runtime (reference; deployment infrastructure)
