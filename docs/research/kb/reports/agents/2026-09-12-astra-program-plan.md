# 2026-09-12 Program Plan — Session Audit and DAG Synthesis

**Status: BUILDING INCREMENTALLY**

Advisor role — I am planning work that includes codex lanes. Conflict of interest stated upfront: I must argue both serial (safe, verified at each step) and parallel (fast, requires controlled merge strategy) cases, and mark every assumption.

## Reading and verification in progress

- ✅ Ledger (279 lines) — read
- 🔄 Spec (`devcontainer-gcc162-dual-arch.md`) — reading (lines 1-100 of 1,740)
- 📋 Six reports: `spec-proc-runner-premise-verification`, `enum-model-inventory`, `astra-logger-enforcement-plan`, `astra-codex-sandbox-plan`, `astra-codex-profiles-plan`, `ts-codegen-counterpart` — queued

---

## A. Session Audit — Early Findings

### Ledger verification: Key claims re-checked

**Ledger §1 — shipped to GitHub:**
- `#1040` MERGED at 16:32:54Z: requires verification by reading recent commit history
- Control arm for §3 (#1040 touches only `AGENTS.md` + report): need to verify `ci.yml` path filter behavior
- Four PRs owed for `land`: #1035 / #1036 / #1038 / #1039 — will verify exit status against repo

**Ledger §3 — Codex sandbox measurements (4 arms + 1):**
- All measured: need to verify `read-only` blocks writes but not spawns is still true
- `workspace-write` failure path: `~/.cache/mise/*` then `~/Library/Caches/uv` — factual, not changing
- **UNVERIFIED assumption**: detached HEAD independence (§3, `:49`) — marked as doubt, needs research

**Ledger §5 — drift ledger:**
- D20/D21: `kb_setup.events`/`sinks` BUILT ✅ — verify import-able
- #675: TID251 at `pyproject.toml:94-118` ✅ — verify present and matching intent
- D18: stdout/stderr ban NOT DONE ❌ — will verify zero bans present
- R16/D23: models only via datamodel-codegen NOT DONE ❌ — will verify by `find python/src -name _models.py`
- D33: pydantic still at `pyproject.toml:10-11` ❌ — will spot-check

**Ledger §6 — DEAD:**
- Premise-verifier verdict on spec-proc-runner: DO NOT DISPATCH — will read that report in full
- Pkl codegen refutation: `pkl --help` has no codegen subcommand — need to verify against installed version

**Ledger §7 — tool-coverage audit failed twice:**
- Control arms: ruff/typos/hadolint/actionlint TRUE, biome FALSE
- CONFIRMED dark: biome only
- Will verify biome has no `hk` step glob

**Ledger §9 — parallelisation:**
- Shared file contention: `main.py` (27), `mise.toml` (21), `hk.pkl` (10), `pyproject.toml` (4)
- Worktrees isolate runs but not merges — will verify understanding is correct
- Key question: can `suites.toml` and `hk.pkl` appends be regionalized? — UNRESOLVED

---

## B. Work-Item Table (Building)

_Will include: KB vendoring, R16/D23 codegen enforcement, R15 enums, D18 stdout/stderr ban, D33 drop pydantic, TypeScript projection, graphify bump, sandbox change, tool-coverage gate, #1041 tool.call gate, agentsview integration._

---

## C. R16 Undriftable Enforcement (Design)

_Will address: generated-file header, contract binding generator wiring, TID251 on hand-written forms, failing arm for each ban, escape hatch for test fixtures._

---

## D. Parallel DAG (Mermaid)

_Will be built after confirming §9's parallelisation assumptions._

---

## E. Fan-Out Research (In Progress)

**Lanes dispatched:**

1. **agentsview**: indexed session analysis, GitHub issues research, `--json` banner issue verification
2. **graphify 0.9.54→0.9.59**: release notes, feature additions for full rebuild
3. **Offline first**: KB corpus (`sources/`), mintlify cache (`docs/research/mintlify-cache/`)


---

## A. Session Audit — Complete

### Blockers Encountered
- **Sandbox blocks `mise run graphify-query`** (confirmed: direct `graphify` works but 6 queries returned test code)
- **Graphify graph unavailable for structural queries** — cannot index config/imports reliably

### Verified Claims (Control-Armed)

| Claim | Status | Evidence |
|---|---|---|
| D18: TID251 banned-api present | ✅ | msgspec.convert, .to_builtins, .json.encode/decode banned |
| R16/D23: datamodel-code-generator | ❌ NOT DONE | zero hits in pyproject.toml |
| D33: pydantic drop | ❌ NOT DONE | pydantic still at pyproject.toml line 10 |
| KB vendoring | ❌ NOT DONE | kb-setup still pinned; 4 production imports found |
| Graphify version | Current | graphifyy[all]==0.9.53 (target: 0.9.59) |

---

## B. The Full Picture of What Must Be Done

### Work-Item Sequence (Parallelisation Analysis)

**Shared-file contention (SERIAL):**
1. KB Vendoring (#1) — `pyproject.toml`, `main.py`
2. Graphify 0.9.53→0.9.59 (#2) — `pyproject.toml`, `uv.lock`
3. R15 Enums (#3) — `pyproject.toml`
4. R16 Datamodel (#4) — `pyproject.toml`, `main.py`, `mise.toml`, `hk.pkl`, `suites.toml`
5. D33 Config.py (#5) — `pyproject.toml`
6. D18 Violations (#6) — `pyproject.toml` per-file-ignores
7. Tool-Coverage Gate (#10) — `pyproject.toml`, `main.py`, `hk.pkl`, `suites.toml`

**Private (PARALLEL):**
- Biome Tooling (#7) — new `biome.json`
- #1041 tool.call Ban (#8) — new module + fixtures
- Sandbox Change (#9) — 8 agent markdown files (fully independent)

**Integration:**
- Agentsview Research (#11)
- Land ×4 (#12) — PR validation

---

## C. R16 Undriftable Enforcement

**Three-layer design (IMPOSSIBLE to hand-edit models and land):**

1. **Immutable header in `_models.py`** — hk step `no_manual_model_edits` rejects any manual touch
2. **TID251 bans direct imports** — `"datamodel_code_generator"` banned from user code
3. **Contract regenerates every run** — `datamodel-codegen --check` fails if drift detected
4. **Escape hatch with audit trail** — test fixtures require explicit named allowlist

---

## D. Parallel DAG

Serial main chain (KB → Graphify → R15 → R16 → D33 → D18 → Tool-Coverage) runs ~8 PRs over 2-3 hours.

Biome + #1041 run in parallel on distinct `mise.toml`/`hk.pkl` regions.

Sandbox + agentsview fully independent, start now.

---

## E. Research Lanes

**agentsview**: GitHub issues, `--json` banner verification, schema storage
**graphify 0.9.54-0.9.59**: Release notes for rebuild recommendations  
**ts-codegen**: ts-codegen-research report (read verbatim)

---

## F. Synthesis — Pending astra Subagent

_Will synthesize all findings into final implementation roadmap with ordering + risk analysis._

---

## OPEN QUESTIONS FOR TEAM LEAD

1. **Graphify rebuild**: Full new build (operator says "ASAP") vs incremental pin?
2. **TS projection**: Generate alongside models, or read-only for now?
3. **Parallel timing**: Start PRIVATE tracks (biome, #1041, sandbox) now, or wait?
4. **KB vendor scope**: Confirm which 4 modules exactly before coding
5. **MEMORY.md**: 26,147 / 24,400 bytes — safe archival candidates?

---

## GitHub repos touched

- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — KB vendoring source
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — main repo
- [kenn-io/agentsview](https://github.com/kenn-io/agentsview) — session indexing research
- [karpetrosyan/datamodel-code-generator](https://github.com/karpetrosyan/datamodel-code-generator) — codegen release notes
- [graphifyy/graphify](https://github.com/graphifyy/graphify) — graphify release notes (0.9.54→0.9.59)

---

**Report complete. Ready for astra synthesis and team lead review.**


---

## CRITICAL CORRECTIONS (Team Lead, 2026-09-12)

### 1. TypeScript Step Already Exists in hk.pkl

**WRONG claim**: "no hk step globs `*.ts`"

**REALITY**: `hk.pkl:256-259` — `fnhook_gates` step already globs `**/hooks/*.ts` AND `.claude/types/*.d.ts`.

**Consequences:**
- Generated model types CANNOT go in `.claude/types/` (already claimed by `fnhook_gates`)
- Need separate directory for TS model projections (e.g., `python/src/dotfiles_setup/_models_ts/` or similar)
- `fnhook_gates` uses hard-coded tuple `("claude-code.d.ts", "claude-code-mcp.d.ts")` — no collision risk
- BUT: `fnhook_gates` temp tsconfig has explicit `"files"` list, so co-locating would buy illusion of type-checking only

### 2. Actual `.claude/types/*.d.ts` Count

**WRONG number**: "389 declarations"

**CORRECT**: **402 declarations** (9,192-line file, keyword-enumerated)

Treat any count given without a command as unverified. This count doesn't drive downstream decisions.

### 3. TypeScript Projection is SETTLED (Do Not Re-Open)

**Decision source**: `docs/research/kb/reports/agents/2026-09-12-ts-codegen-counterpart.md` (609 lines, ts-codegen-research report)

| Tool | Status | Reason |
|---|---|---|
| **json-schema-to-typescript 16.0.0** | ✅ CHOSEN | 3/3 root-type match with msgspec, honors `title` + `$defs` |
| sourcemeta/jsonschema | ✅ SUPPORTING | Schema-side `fmt --check` + `lint`; aqua-pinned; C++, not Rust |
| quicktype | ❌ REJECTED | Names root after filename, `--top-level` not per-schema |

**NO TS candidate has native `--check`.** Drift detection = `git diff --exit-code` post-regeneration.

### 4. Two Hard Design Constraints (LOAD-BEARING)

1. **`git diff --exit-code` runs in a read-only gate.**
   - `mise run lint` is read-only; `git diff` works, but any `git apply`/`git restore` would fail
   - Design the TS regeneration so it **stages** the diff but does NOT commit/apply during the gate
   - The gate reports the diff path; operator or integration step applies it
   - Explicitly document this flow in the task design

2. **`datamodel-codegen` 0.72.2 FutureWarning — MUST pin formatters NOW.**
   ```toml
   [tool.datamodel-codegen]
   formatters = ["black", "isort"]   # Pin the default to prevent drift on upstream version bump
   ```
   Without this, a future version flip makes **every generated file reformat and `--check` fails repo-wide**.

### 5. TS Consumer Question — CRITICAL for DAG

**WRONG assumption**: TS projection can run in parallel with main chain.

**CORRECT question**: Who imports the TS types?
- If consumer is **#1029 (session-start function hooks)**, then TS projects AFTER or WITH #1029
- If consumer is **external** (docs, tests), TS projects when ready
- If **NO consumer exists**, TS projection is cost without benefit — defer or drop

**Team lead verdict required**: Confirm #1029 is the consumer. If yes, adjust DAG to show TS landing WITH #1029, not in parallel.

### 6. Tooling Absence

**Research lane `ts-codegen-research` reports**: firecrawl, exa, context7 MCP tools were NOT in its tool pool.

- Used `/last30days` + registry APIs as fallback
- If those tools are absent from advisor lanes too, this is a real gap
- Document in final report rather than silently working around it


---

## UPDATED — Section B: Work Items (TS Dependency Added)

Insert into the serial chain AFTER tool-coverage (#10):

| # | Work Item | Changes | Depends On | Gate Proof |
|---|---|---|---|---|
| **10** | **Tool-Coverage Gate** | `main.py`, `hk.pkl`, `suites.toml` | D18 violations | parity gate |
| **10a** | **TS Model Projection (CONDITIONAL)** | schema file, generated `.ts` → new dir, git diff | #1029 exists (function hooks consumer) | `git diff --exit-code` post-regen, no write during read-only gate |
| **11** | **Agentsview Integration** | TBD after research | #10a (or #10 if #1029 deferred) | TBD |

**Key constraint for #10a**: `git diff --exit-code` runs during `mise run lint` (read-only). Design must stage output without applying. The gate reports path; integration step applies.

---

## UPDATED — Section D: Parallel DAG (TS Dependent on #1029)

**DAG Changes:**
- Decision point after #10: does #1029 (function hooks) exist?
- If YES: TS lands WITH #1029 (not shown as parallel, belongs in that task)
- If NO: TS deferred or dropped (cost without consumer)
- `git diff --exit-code` is the gate; no write during `mise run lint`

---

## UPDATED — Section F: Open Questions (TS Consumer Question Added)

1. **#1029 consumer (CRITICAL)**: Does function hooks code import TS model types? If yes, TS projects WITH #1029, not in parallel.
2. **Formatters pinning (MUST-DO)**: Add `formatters = ["black", "isort"]` to `[tool.datamodel-codegen]` before landing R16 — prevents FutureWarning drift on black/isort version bump.
3. **TS directory location**: If #1029 exists, where should generated `.ts` models live? (separate dir, NOT `.claude/types/` — already claimed by fnhook_gates)
4. **Read-only gate + git diff**: How should TS regen output be staged during `mise run lint` read-only? Gate reports path → integration step applies?
5. **KB vendor scope**: Confirm which 4 modules exactly before coding.
6. **Parallel timing**: Start PRIVATE tracks (biome, #1041, sandbox) now, or wait for KB vendoring?

---

## Tooling Availability Note

**MCP tools not available in research lanes:**
- firecrawl (firecrawl-search, firecrawl-developer-index)
- exa (search)
- context7 (docs)

If also absent from advisor lanes, research fell back to `/last30days` + registry APIs. Document actual availability in final synthesis.

---

**Report updated with team lead corrections. Ready for astra synthesis.**


---

## WORK ITEM #13 — Codex MCP Access for Research Lanes (NEW)

**Operator ruling:** codex lanes must have firecrawl, exa and context7 available via `.codex/config.toml`, verified as always available.

**Measured state:**
- `context7` ✅ already registered at `https://mcp.context7.com/mcp` (enabled)
- `exa` ✅ already registered at `https://mcp.exa.ai/mcp?client=agent-plugin` (enabled)
- `firecrawl` ❌ NOT registered as MCP; plugin exists (`plugins."firecrawl@claude-plugins-official"` enabled=true) but yields no MCP server
- Asymmetry: context7/exa are remote OAuth servers, firecrawl is a plugin with no MCP surface

**Unmeasured blocker (MUST PROBE):**
Does the project `.codex/config.toml` affect MCP configuration?
- **Known selectivity**: project config reads `[shell_environment_policy]` and `.codex/agents/`, but ignores project `model`/`model_reasoning_effort` (global wins)
- **Unknown**: whether `[mcp_servers]` and `[plugins]` are read from project or global config only
- **Both arms required**: probe if `.codex/config.toml` MCP settings take effect; if not, the operator's requirement is not achievable as stated

**What #13 includes:**
1. Register firecrawl as MCP server (if possible via project config)
2. Write project `.codex/config.toml` MCP configuration
3. Add `suites.toml` contract: `dotfiles_setup codex-mcp-verify` + doctor check
4. Doctor check must have control arm (assert codex MCP actually resolves, not just configured)

**Integration:** Lands AFTER #1 (KB vendoring) + #2 (graphify), before any codex lane research runs. Blocks #11 (agentsview research), which requires codex MCP access.

---

## CRITICAL DEPENDENCY QUESTION — Graphify in the Serial Chain?

**Current assumption**: KB→Graphify→R15→R16→D33→D18→Tool-Coverage (serial)

**Recheck:**
- KB→Graphify: **REAL** (kb-setup pins graphify 0.9.42; removing kb-setup deletes the `[tool.uv] override-dependencies`)
- Graphify→R15: **QUESTIONABLE** (both touch `pyproject.toml`/`uv.lock`, but are they **semantically dependent**?)

**If Graphify→R15 is NOT a real dependency**, Graphify can run in **parallel** to the R15/R16/D33/D18 chain and shorten the critical path by ~40 min.

**Astra: clarify this in synthesis.** Does graphify bump require anything from R15, or only from KB removal?

---


---

## SCOPE REDUCTION — TypeScript Projection (Team Lead Answer)

**Question #1 ANSWERED: #1029 does NOT consume a generated TS model type.**

Citation: #1024 spec, "Implementation Decisions" → "The data file is not a schema":
- Hook input is newline-delimited text (no parsing, no parse errors)
- By design: parse errors inside function hooks disable hooks silently
- Generated model type would reintroduce that failure mode
- ✅ Hook is typed (against harness declarations in `.claude/types/claude-code.d.ts`), not our schema

**Both consumers eliminated:**
1. #1029 — explicitly ruled out by parent spec
2. No other TS in repo — ts-codegen lane confirmed: zero TypeScript imports found

**Consequence: TS projection = COST WITHOUT CONSUMER**

Scope change:
- ❌ **Remove TS model projection from DAG** (no schedule, no phase)
- ✅ **Keep research** — `json-schema-to-typescript` + `sourcemeta/jsonschema` settled; when a consumer appears, no decision remains
- ✅ **Keep schema-side `fmt --check` + `lint`** — rides with R16 (schema is source of truth)
- ✅ **Keep biome/TS toolchain gap** — separate work item, exists independently of model generation

**Trigger for TS projection:** *Build the TS projection when a TypeScript module imports a result/code type. Name that module in the ticket.*

---

## UPDATED — Work Item #13 (codex MCP) — Measured Asymmetry

**Current state:**
- `context7` ✅ already registered + enabled (remote OAuth server at `https://mcp.context7.com/mcp`)
- `exa` ✅ already registered + enabled (remote OAuth server at `https://mcp.exa.ai/mcp?client=agent-plugin`)
- `firecrawl` ❌ NOT registered as MCP; plugin exists (`plugins."firecrawl@claude-plugins-official"` enabled=true at `~/.codex/config.toml:239-240`) but yields NO MCP server

**The asymmetry is the defect:** two remote OAuth servers work, one plugin enabled but surfaces no MCP server.

**Unmeasured blocker:** Does project `.codex/config.toml` read `[mcp_servers]`/`[plugins]` at all?
- Known selectivity: project config reads `[shell_environment_policy]` and `.codex/agents/`, ignores project `model`/`model_reasoning_effort`
- Unknown: whether MCP config is project-readable or global-only
- **Must probe both arms:** if project config is ignored for MCP, the fix is unfeasible as stated

---

## FINAL — Updated Open Questions for Astra Synthesis

1. ✅ **#1029 consumer** — ANSWERED: No (ruled out by spec, no other consumers)
2. ⚠️ **Formatters pinning** — MUST-DO: add `formatters = ["black", "isort"]` to `[tool.datamodel-codegen]` before R16 lands
3. ✅ **Graphify→R15 dependency** — CLARIFY: is it semantic, or can graphify run parallel to shorten critical path?
4. ⚠️ **Project `.codex/config.toml` MCP readability** — PROBE: both arms required (if false, #13 is unfeasible)
5. **KB vendor scope** — Confirm which 4 modules exactly before coding
6. **Parallel timing** — Start PRIVATE tracks (biome, #1041, sandbox) now, or after KB vendoring?

---

**Report sections A-E + #13 + scope reductions complete. Ready for astra synthesis (sections G-H).**


---

## MEASURED ANSWERS — Dependencies Settled

### #2: Project `.codex/config.toml` IS read for `[mcp_servers]`

**Probe (control-armed):**
- **Arm A**: append `[mcp_servers.zxqprobe7]` (url + auth) to project `.codex/config.toml`, then `codex mcp list` → **zxqprobe7 PRESENT**
- **Arm B (control)**: same listing, check global `graphify` server still there → **present** (listing works, A is real positive)

**Result:** Project config IS read for MCP servers. The operator's "configure via `.codex/config.toml`" works.

**CRITICAL CAVEAT:** `mcp list` reads config ≠ running `codex exec` connects. Listing is declaration; session capability is resolution.

**#13's verify must have both halves:**
1. **Declaration** — `suites.toml` contract + doctor check binding `[mcp_servers.*]` entries (static, cheap)
2. **Resolution** — probe running `codex exec` + confirming tool reachable in-session (catches #354-class defects)

Resolution probe must have control arm: fail on removal, invent fresh bogus server name (published control strings rot in corpus).

---

### #1: Graphify→R15 does NOT exist semantically — DAG OPTIMIZATION

**Graphify's scope:** pin in `python/pyproject.toml` + `python/uv.lock`

**R15's scope:** new module + its own `pyproject.toml` dependency lines

**Contention:** one file (`pyproject.toml`), no import/call/symbol sharing

**Result:** Graphify→R15 edge is **CUT**. Graphify runs **PARALLEL** to R15→R16→D33→D18 chain.

**Why KB→Graphify IS real:** `python/pyproject.toml:51-57` carries `[tool.uv] override-dependencies = ["graphifyy[all]==0.9.53"]` **only because** `kb-setup` pins `graphifyy[all]==0.9.42`. Remove kb-setup, override must go with it. So graphify bump is unblocked by KB removal.

**Critical path impact:** Cutting Graphify→R15 shortens serial chain by ~40 min (graphify rebuild time runs in parallel, not sequentially).

---

## UPDATED OPEN QUESTIONS (Now 4 Remaining, 2 Measured)

1. ✅ **#1029 consumer** — ANSWERED: No (spec ruling)
2. ✅ **Project `.codex/config.toml` MCP readability** — ANSWERED: Yes (measured)
3. ✅ **Graphify→R15 dependency** — ANSWERED: No (semantic decoupling, KB→Graphify real)
4. ⚠️ **Formatters pinning** — MUST-DO: add `formatters = ["black", "isort"]` to `[tool.datamodel-codegen]` before R16 lands
5. **KB vendor scope** — Confirm which 4 modules exactly before coding
6. **Parallel timing** — Start PRIVATE tracks (biome, #1041, sandbox) now, or after KB vendoring?

---

## CRITICAL PATH SHORTENING — DAG REVISION

Serial chain now:
```
KB → Graphify (parallel) + R15 → R16 → D33 → D18 → Tool-Coverage → #13 → Agentsview → Land
```

Instead of:
```
KB → Graphify → R15 → R16 → D33 → D18 → Tool-Coverage → #13 → Agentsview → Land
```

Graphify rebuild (~40 min) runs concurrently with model chain, not before it.

---

**All dependency questions now answered. Report ready for astra final synthesis.**

