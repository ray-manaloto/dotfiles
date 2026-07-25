# DESIGN — graphify second brain for the Fable-5 orchestrator (2026-07-24)

> **STATUS (2026-07-24): DESIGN + PROTOTYPE + SEAM-COMPLETION all done & MERGED.** The
> record/aggregate/audit/query seam landed as knowledge-base **PR #7** (`bc1eec6`); the
> two deferred "partial" halves landed as **PR #8** (`e6e2f07` on KB `main`) — the read
> path (§5) is wired into `orchestrator-routing` SKILL.md (advisory-over-static +
> close-the-loop `brain-remember`), and the transcript-mining audit (§4a-3b / open-Q #1)
> ships as `kb_setup.brain.transcript_audit` (advisory SessionEnd → `.omc/brain-audit.md`,
> graduated verified-unrecorded/under-recorded/unverified; the blocking ship-gate stays
> `brain audit`). All gates green, 270 tests. **DOGFOODED 2026-07-24-g (KB PR #9 @
> `cee7d684`)**: a real codex-lane delegation ran the full loop; the session audits as
> `recorded`. Findings: transcript-audit is cwd-scoped (KB hook blind to dotfiles
> orchestration sessions → wire a dotfiles SessionEnd hook); §4a-6 decay likely closed
> (reflect is stateless — stale rows vanish on regeneration); v2 = record the routing
> MODE in outcomes. See memory `project_session_2026-07-24-g`.

**Arc:** RESEARCH (done, `.omc/research/research-20260722b-graphify-second-brain/report.md`)
→ **DESIGN (this doc)** → PROTOTYPE. This closes the DESIGN phase: it resolves the
4 open questions with evidence gathered this session, names the architecture, and
scopes the first prototype. Status of each resolution is marked **[EVIDENCE]** (probed
this session), **[DECISION]** (design choice, reversible), or **[DEFER→PROTOTYPE]**.

---

## 1. What we are building (and the one genuinely novel part)

A **routing-grounded second brain**: a git-tracked, plain-markdown **decisions/lessons
vault** whose graph the Fable-5 architect queries *at delegation time* to decide **which
lane** (codex / antigravity / grok / Claude-fallback) and **what reasoning effort** a
subtask gets — and writes outcomes back to, so the routing improves over time.

Almost every mechanical part already exists (graphify `update`/`query`, KB `kb-remember`/
`kb-reflect`, the `orchestrator-routing` skill). The research confirmed the **memory
foundation is solved/forkable** (two reference repos). **The only novel work is the
routing-grounding seam** — recording structured routing *outcomes* and querying them
*before* a routing decision. Everything else is assembly.

> Scope discipline: this is NOT "index everything the agent ever sees" (that path —
> Zep/Graphiti — measured 600k tokens/conversation and causes memory contamination).
> It is a **curated, git-reviewed** vault of decisions and their verified outcomes.

---

## 2. The four open questions — resolved

### Q3 — Does one graph span vault + codebase? → **NO. Keep them separate.** [EVIDENCE]

Probed on the **real** dotfiles graph (3,597 nodes, all `_origin=ast`, no paid layer):

| measure | value |
|---|---|
| `.py` nodes | 2,265 |
| `.md` nodes | 1,129 |
| **md ↔ py edges** | **0** |
| md ↔ md edges | 1,007 `contains` (intra-file headings) + **7** `references` (cross-file wikilink) |

Control-armed with a scratchpad vault (`index.md`, `notes/routing-decision.md`,
`code/guard.py`) run through `graphify update`:

- `[[notes/routing-decision]]` (downward path-qualified, note→note) → **resolves** ✓
- `[[code/guard.py]]`, `[[../code/guard.py]]` (note→**code**) → **do NOT resolve** ✗
- `[[../index]]` (upward `../`) → **does NOT resolve** ✗

**There is no free structural mechanism to connect a note to code** — not prose, not a
backticked path, not even an explicit `[[code/x.py]]` wikilink. graphify's markdown
extractor resolves wikilinks only against *other markdown documents*. A vault+codebase
merge therefore yields two disconnected islands; the *only* bridge is the paid semantic
(INFERRED) layer, whose cross-doc edges the research already measured as thin
("No path found" across two docs).

**DECISION:** the routing/decisions vault is its **own graph**, queried separately from
the codebase graph. The orchestrator issues up to two queries per decision — codebase
graph ("where/what is the code") and decisions vault ("how did this kind of routing go
before"). `merge-graphs` is used *only* as a union query-surface if ever wanted, never
relied on for cross-island traversal.

### Q2 — Full-semantic-build cost → **negligible at our scale (~pennies).** [EVIDENCE, estimate]

Representative vault = `.claude/rules/*.md` + `docs/adr/*.md` (24 real decision notes,
~30k tokens, ~1.25k tok/note). One full semantic build, Gemini public rates:

| vault size | Gemini Flash | Gemini Pro |
|---|---|---|
| 24 notes (measured corpus) | **$0.02** | $0.08 |
| 100 notes | $0.08 | $0.34 |
| 300 notes | $0.25 | $1.03 |
| 1000 notes | $0.85 | $3.44 |

The research treated paid-build cost as a scary unknown; it is **< $1 for any realistic
routing vault**. This **collapses Q1** (below). A real measurement (needs a key + a few
cents) would confirm the order of magnitude but the design does not hinge on it.
**[DEFER→PROTOTYPE]** the real number.

### Q1 — Two-layer refresh cadence (the "sharpest") → **dissolved by Q2.** [DECISION]

The #1915 conflict (semantic supersedes AST → an enriched doc's structure *freezes* until
a keyed rebuild) only bites when incremental semantic builds are *expensive* enough that
you must avoid re-running them. At **pennies per full build**, we sidestep the incremental
freeze entirely:

- **Free structural layer — always on.** `graphify update <vault>` on every write (git
  post-commit hook or SessionStart), clean env (strip `AWS_REGION`/`GEMINI_API_KEY` to
  avoid the auto-backend trap). Keeps wikilink/heading edges current at 0 tokens. This is
  authoritative for structure and drives day-to-day queries.
- **Paid semantic layer — periodic FULL rebuild, not incremental.** A deliberate
  `mise run brain-enrich` (keyed) does a *whole-vault* semantic build on a cadence
  (weekly, or before a heavy planning/routing session). Because it's a full rebuild, the
  "which docs are frozen" bookkeeping never arises. Output includes concept/INFERRED edges
  and (future work, §5) community summaries.
- **Never per-save paid builds.** Semantic runs are opt-in and logged.

### Q4 — Where does the vault live + who is the single writer? → **the knowledge-base repo, flat.** [DECISION]

- **Location: the `knowledge-base` repo**, not dotfiles, not a new repo. KB *already is*
  the graphify substrate — `kb-build`/`kb-update`/`kb-query`/`kb-remember`/`kb-reflect`
  tasks, single-writer `merge-graphs` discipline, git-reviewed public flow, the learning
  overlay. Adding a `brain/` vault dir reuses all of it. dotfiles is tooling and fights
  its own md-size budgets; a new repo re-implements machinery KB already has.
- **Writer:** the vault gets its **own** `graphify-out/graph.json` (separate from KB's
  aggregate codebase graph, per Q3). Its writer is plain `graphify update brain/` —
  **flock-serialized** (#1059), so fan-out-safe; no new single-writer machinery needed.
  The only op that needs the named serialized writer is `merge-graphs`, which we are
  *not* relying on here.
- **Format: FLAT vault.** All decision notes are siblings in `brain/` (shallow typed
  prefixes, each dir internally flat). This resolves the Step-0 tension (below) for free:
  in a flat dir, bare `[[wikilinks]]` resolve as siblings, so we need **no custom
  path-qualified writer rule** and can adopt the write-back "hands" almost as-is. It also
  matches the convention this repo's `~/.claude/.../memory/*.md` already uses
  (`user_*`/`project_*`/`feedback_*` typed flat files).

---

## 3. Step 0 — fork vs. build (use-tool-builtins gate)

Full report: `.omc/kb/reports/agents/step0-reference-repos.md`. All three candidates are
MIT + maintained. **Load-bearing finding: none emit path-qualified wikilinks**, so the
FLAT-vault decision (Q4) is what makes them usable.

| Repo | What to take | Verdict |
|---|---|---|
| `albertludi/second-brain-claude` | **Flat-vault model** + the **Stop→SessionStart→PreToolUse hook trio**; it wires graphify onto Claude's native flat typed `memory/*.md` — the convention we already use | **FORK-AND-ADAPT** (adapt hooks to our `hook_guard` + SessionEnd infra) |
| `lucasrosati/claude-code-memory-setup` | Taxonomy ideas + `/save` + `/resume` command prose | **STUDY** (its writer emits bare `[[stem]]`; chat-import pipeline out of scope) |
| `kepano/obsidian-skills` | `obsidian-markdown` + `defuddle` as the write-back **"hands"** (cross-agent: Claude/Codex/OpenCode — matches our lanes) | **ADOPT** the markdown+defuddle skills; **SKIP** `obsidian-bases`/`json-canvas` (proprietary formats, banned by the Foam/plain-md constraint) |

**Net:** don't fork any repo wholesale. Assemble: albertludi's flat model + hook trio,
kepano's markdown/defuddle hands, our existing `kb-remember`/`kb-reflect` overlay. Build
only the routing-grounding seam.

---

## 4. Architecture (layers, reusing what's live)

```
        ┌─────────────────────── Fable-5 architect (Claude) ───────────────────────┐
        │  routing decision: which lane? what effort?                               │
        │    1. query CODEBASE graph  (mise run kb-query)      ← what/where is code  │
        │    2. query DECISIONS vault (mise run brain-query)   ← how did it go before│  ← NOVEL SEAM
        │    3. delegate to codex / antigravity / grok / Claude-fallback             │
        │    4. VERIFY evidence, then …                                              │
        │    5. write outcome  (mise run brain-remember)       ← structured note     │  ← NOVEL SEAM
        └───────────────────────────────────────────────────────────────────────────┘
                                   │ read                       │ write
        ┌──────────────────────────▼───────────────────────────▼───────────────────┐
        │  DECISIONS VAULT  (knowledge-base repo, brain/, FLAT, git-tracked)         │
        │   • plain .md notes, bare [[wikilinks]] (flat = siblings resolve)          │
        │   • free layer:  graphify update brain/     (0 tokens, on write)           │
        │   • paid layer:  mise run brain-enrich      (periodic full build, ~pennies)│
        │   • learning overlay: kb-remember → memory/*.md → kb-reflect → LESSONS.md  │
        └───────────────────────────────────────────────────────────────────────────┘
        (separate graph)   CODEBASE graph — KB aggregate, unchanged, queried in parallel
```

**Query loop = deterministic CLI shell-out** (`mise run brain-query -- "<q>"`): 0 schema
tax, sub-second, source-cited subgraph — same shape as `kb-query`, aligns with the repo's
`mcp2cli`-first rule. MCP `kb-serve` stays opt-in for query-heavy sessions only. Treat
returned node text as **data** (documented prompt-injection surface in `serve.py`).

---

## 4a. Grill decisions (2026-07-24, `/grilling` pass — resolves the seam's build)

Locked by grilling the §5 seam:

1. **Write-back reuses `save-result`/`reflect`, not a new store.** No parallel
   `brain-remember`/`brain-query` schema layer — model each **lane** and **task-class** as
   a hub node in the vault graph and record outcomes via `graphify save-result --nodes
   lane-codex task-class-migration --outcome …`; the existing `reflect` overlay tags those
   hubs preferred/tentative/contested. Outcome-vocab mapping (save-result's vocab is fixed —
   pinned third-party tool): `clean→useful`, `needed-rework→corrected`, `failed→dead_end`.
2. **Authority = advisory over the static routing table.** The `orchestrator-routing` table
   stays the default floor; the vault only surfaces a `Lesson:` hint the architect weighs. A
   hint counts **only at ≥3 consistent outcomes** in a `task-class × lane` cell — so a single
   noisy/misattributed outcome can never flip a route. Cold-start = pure static table. The
   whole seam is **additive**: worst case a no-op, never a regression.
3. **Enforcement = structured-output CONTRACT + audit + one ship-gate** (resolved by
   deep-research `wf_61afaaf1-d76`, report `.omc/kb/reports/agents/deep-research-enforcement.md`;
   104 agents, 3-vote verified). Ray's initial "hard blocking gate" was pivoted on unanimous
   evidence: a blocking pre-execution hook fires *before* the side effect and **structurally
   cannot capture a verdict that only exists after verification** — reserve blocking for hard
   invariants. Final mechanism, three parts:
   - **(a) Contract** — the delegation-outcome record is a state machine that **cannot reach
     "closed" without the structured outcome field** (`clean|rework|failed`). Recording is
     structurally required, not optional prose. This is the "hard" part.
   - **(b) Audit** — reuse the existing `command-audit`/SessionEnd transcript-mining to flag
     any *verified* delegation whose record was never closed. (SessionEnd cannot block — it
     audits, doesn't gate.)
   - **(c) One blocking gate at `ship`/`land` only** — a closed record becomes a release
     precondition (reuses the `hook-selfcheck` gate pattern). The single place blocking is
     appropriate: a hard-invariant boundary that fires *after* verification.
   - **NO parallel watcher subagent** — unanimous (3-0 ×4): automated failure attribution
     tops out at 66%/30% (agent/step) even with full traces; a watcher can't answer
     "lane-fault vs spec-fault" and can't judge correctness without re-running verification.
     Every surveyed memory system captures outcomes via self-report, none via observer.
4. **Attribution (lane-fault vs spec-fault) deferred to v2.** Advisory authority + the ≥3 bar
   already bound misattribution; the research (66%/30% attribution accuracy) confirms an
   automated attribution field is not worth requiring now.
5. **≥3 rule needs session-deduplication** (research open-Q #3): one bad spec producing 3
   rework outcomes in a single session must NOT count as 3 independent votes. The
   deterministic aggregator dedups/decays correlated same-session outcomes. **[PROTOTYPE]**
6. **Overlay decay path** (research open-Q #4): whether a `preferred` tag needs an
   ExpeL-style downvote path to decay to `tentative`/`contested` when a lane regresses, or
   advisory-only makes stale hints harmless. **[PROTOTYPE]**

## 5. The novel seam, concretely

**Write path (post-verified-outcome).** After a delegated subtask is verified done, the
architect appends one structured decision note via `brain-remember`. Schema (flat note,
bare wikilinks):

```markdown
---
kind: routing-outcome
task_class: migration        # migration|concurrency|auth|crud|boilerplate|test-gen|research
lane: codex                  # codex|antigravity|grok|claude-fallback
effort: high
verdict: clean               # clean|needed-rework|failed
---
# 2026-07-24 codex migration — APIv1→v2 callers
Delegated the APIv1→v2 caller migration to [[codex-implementer]] at effort high.
Verdict: clean — passed [[mise-run-lint]] and pytest first try, commit abc1234.
Relates to [[task-class-migration]] and [[lane-codex]].
```

The `[[task-class-migration]]` / `[[lane-codex]]` sibling notes are the **hubs** the graph
clusters around — this is how outcomes aggregate into a queryable signal.

**Reflect.** `kb-reflect` (already built, collision-safe, never touches `graph.json`)
aggregates the outcome notes → `LESSONS.md` + a learning overlay that tags hub nodes
**preferred / tentative / contested**, so a later query surfaces a `Lesson:` hint.

**Read path (pre-decision).** Before routing, the architect runs
`brain-query -- "task_class:migration outcomes by lane"`; the overlay-tagged subgraph
answers "codex preferred for migrations (n verified clean)", "antigravity tentative for
large test-gen (1 rework)". This is Reflexion/ExpeL specialized to routing. The genuine
contribution is the **structured outcome schema + the query-at-routing-decision
integration into `orchestrator-routing`.**

**Missing GraphRAG capability (later, not v1):** graphify has no community summaries /
global search — the #1 gap for corpus-wide "what do we know about X". Add LLM-written
per-community summaries + a map-reduce global-search path, lazily cached (study
`microsoft/graphrag` + llama_index `GraphRAGStore`). Deferred; the routing seam works on
local subgraph queries without it.

---

## 6. Vault conventions (forced by evidence — these are constraints, not style)

1. **FLAT dir** (all siblings) → bare `[[wikilinks]]` resolve. If sub-dirs are ever
   introduced, links across them **must** be path-qualified `[[sub/Note]]`; `../` upward
   links **never** resolve — avoid them.
2. **Taxonomy goes in wikilinks/headings, never frontmatter `tags:`** — graphify's free
   structural pass ignores `tags:`/`aliases:` (0 nodes). Hub notes (`task-class-*`,
   `lane-*`) carry the taxonomy.
3. **No Obsidian-proprietary formats in the source of truth** (no Bases, no JSON Canvas) →
   Foam / plain-md stay drop-in; Obsidian is an optional editing layer only.
4. **Curated, git-reviewed write-back only** — human/PR diff is the contamination
   firewall. Never auto-extract-KG-from-everything.

---

## 7. Prototype plan (free layer only — Q2 estimate accepted, ~1 session)

1. Stand up `knowledge-base/brain/` flat vault: ~15–30 real routing/decision notes
   (seed from existing `memory/feedback_*` + the orchestrator-routing doctrine), with
   `task-class-*` / `lane-*` hub notes and bare wikilinks.
2. `graphify update brain/` (free) → inspect the structural graph; confirm hub notes
   cluster the outcomes (this is the query signal).
3. Wire the query + record tasks (thin wrappers over `graphify query` / `save-result` —
   zero-bash-logic python module) and a query step into the `orchestrator-routing` skill's
   decision flow. Record path uses the §4a-1 hub-node model + vocab mapping.
4. **Enforcement wiring (§4a-3):** (a) the outcome record as a state object that can't close
   without the outcome field; (b) extend the existing `command-audit` to flag verified-
   but-unclosed delegations; (c) add the closed-record precondition to the `ship`/`land`
   `hook-selfcheck` gate. Resolve the audit false-negative open-Q (distinguish "unrecorded"
   from "abandoned/never-verified").
5. **Aggregator with session-dedup (§4a-5):** the deterministic ≥3-consistent function must
   collapse correlated same-session outcomes so one bad spec ≠ 3 votes.
6. Dogfood: run one real delegated subtask through record→reflect→query and confirm the
   `Lesson:` hint surfaces; observe whether a `preferred` tag needs a decay path (§4a-6).

> Paid `brain-enrich` (semantic/concept edges) is deferred — Q2 estimate accepted, no
> spend until a concrete need for INFERRED edges over the free wikilink structure appears.

**Method:** `/grilling` the design before locking it (as the KB concurrency design did),
then finalize. Architect verifies evidence before "done" — lanes execute, architect
gates.

---

## 8. Decisions — RESOLVED (Ray, 2026-07-24)

1. **Vault location → knowledge-base repo, `brain/`.** ✓
2. **Q2 → accept the ~pennies estimate; no paid spend.** The prototype does NOT run a
   keyed build — §7 step 3 is dropped. Structural (free) layer only until a concrete need
   for concept edges justifies the (negligible) cost.
3. **Next → `/grill` this design, then prototype.** ✓

---

## GitHub repos touched

- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — 0.9.23 installed; probed `update` wikilink resolution (note→note resolves path-qualified/sibling; note→code never resolves; `../` never resolves), graph schema (`source_file`/`file_type`/`_origin`), path/query engine.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — target substrate; `kb-*` tasks, 352 MB aggregate graph, `kb-remember`/`kb-reflect` overlay, single-writer discipline.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — real 3,597-node graph used as the Q3 evidence corpus.
- [albertludi/second-brain-claude](https://github.com/albertludi/second-brain-claude) — flat-vault model + hook trio (FORK-AND-ADAPT).
- [lucasrosati/claude-code-memory-setup](https://github.com/lucasrosati/claude-code-memory-setup) — taxonomy + /save,/resume (STUDY; bare-link writer).
- [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) — markdown+defuddle write-back "hands" (ADOPT minus bases/canvas).
- [microsoft/graphrag](https://github.com/microsoft/graphrag), [run-llama/llama_index](https://github.com/run-llama/llama_index) — community-summary/global-search capability to build later (§5).
