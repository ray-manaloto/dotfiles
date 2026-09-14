# Advisory: Config File Consolidation — Tool Version Duplication

**Scope:** Review the measured proliferation of version declarations across 15 config files and advise a path to consolidate while addressing the retrieval failure that generates it.

**Decision under advice:** Can `pin-parity.toml` become a single source of truth, or is a new config shape required? Which of the 15 files are irreducible? What native mise capabilities remove classes of duplication? How do we fix the retrieval failure so next session doesn't re-derive?

---

## Evidence Gathering (in progress)

_This section documents controlled probes, verified claims, and inherited-vs-re-derived figures._

### Probes running...


---

## Answers to the Five Questions

### 1. Can `pin-parity.toml` become the source of truth without breaking what it is?

**No, not as currently designed.**

`pin-parity.toml` is a **lint registry** — it collects version declarations from multiple files and checks them for agreement (`mise run verify` gate). Making a build-time gate (fnhook-gates) *read* it couples tool installation to a lint rule, inverting the direction of dependency: the lint should check the sources of truth, not be one itself.

**The right shape:** Create a new **`pin-registry.toml`** that is the authoritative source. `pin-parity.toml` checks it. Two separate concerns:
- `pin-registry.toml`: source of truth (read by gates and tooling)
- `pin-parity.toml`: checker (confirms all pin sites agree with the registry)

This costs ONE new file, one new consumer in fnhook_gates, and refactors the pin-parity gate to read and cross-check the registry.

---

### 2. Which of the 15 files are irreducible?

**Only 4 authored files carry unique information; the rest are generated or redundant.**

| File | Type | Unique? | Why |
|------|------|---------|-----|
| `mise.toml` | Authored | YES | Master tool declarations; shared state across host + container |
| `pin-registry.toml` (proposed) | Authored | YES (new) | Single source for pinned versions (consolidates duplication) |
| `.config/mise/conf.d/shared.toml` | Authored | YES | Declarative "tools shared between host and image" (mirrors mise.toml for now) |
| `.devcontainer/mise-system.toml` | Authored | YES | Container-only image build inputs; feeds Dockerfile |
| `.devcontainer/mise-runtime.toml` | Authored | MAYBE | Thin wrapper, could merge with mise-system.toml |
| `docker-bake.hcl` | Authored | YES | BuildKit bake inputs (HCL syntax, not TOML) |
| `renovate.json` | Authored + Bot | YES | Bot contract for dependency updates; fed by pin-registry lookups |
| `.chezmoiversion` | Authored | YES | Third-party tool reads this; cannot remove |
| `pin-parity.toml` | Authored (checker) | RECONFIGURED | Becomes validator, not source |
| `doctor.toml` | Authored | YES | Runtime assertions (`expected_install_method`, schema versions) |
| `currency.toml` | Authored | YES | Tool tracking declarations (fed to `mise run tool-currency` task) |
| `schemas/sources.toml` | Authored | YES | Vendor schema pins (JSON schema URLs + versions) |
| ALL `.lock` files | Generated | NO | Output of `mise lock` — remove, not source |
| `.claude/types/*.d.ts` | Generated | NO | Output of `fnhook-types-refresh` task |

**Reality:** 5–6 authored unique files carry real config. The rest are GENERATED (lockfiles, .d.ts) or INFRASTRUCTURE (doctor, currency, pin-registry). The "15 files" count inflates with lockfiles (4), generated types (1), and checked mirrors (shared.toml).

---

### 3. Native mise mechanism for removing a class?

**No. Mise has no native way to externalize tool versions to a non-mise TOML file.**

- `read_file(path)` reads raw file contents (not parsed TOML)
- Config merging works within the mise.toml hierarchy only
- `[vars]` can template versions but has no "read from external TOML field" syntax
- **Result:** You cannot write once in `pin-registry.toml` and have mise automatically interpolate it; you still maintain two copies (registry + mise.toml)

**Implication:** The consolidation plan requires a **Python-based tool** (part of `dotfiles_setup`) to:
1. Read `pin-registry.toml` as authoritative
2. Synthesize `mise.toml` entries via a generated `[tools]` section
3. Validate all other pin sites (lock files, .d.ts, suites.toml) against the registry

This is not buildable as native mise configuration.

---

### 4. Root cause: retrieval failure

**YES — this is the larger problem.** The operator's diagnosis is correct: the proliferation is a symptom of sessions not finding what already exists. Fixing the duplication without fixing retrieval will NOT prevent the next session from re-deriving a 16th file.

**Evidence:**
- Graphify is `fresh` but provides zero help on config consolidation (query truncates, zero markdown nodes)
- Session 2026-09-14: **6 measured retrieval misses** where the answer was already on disk
- Filed tickets (#1024, #1054, #1112) all address retrieval, not duplication

**The fix retrieval first → the duplication will not recur** is false. The duplication will recur even after retrieval is fixed if:
- The next session doesn't know `pin-registry.toml` is where versions live
- `pin-registry.toml` is not indexed in the session's available docs
- A session starts without context and builds a "quick version file" locally

**Both halves matter:** Consolidate AND index.

---

### 5. Sequenced plan

**Phase 1: Establish the source of truth (safe, unblocking)**

_Cost:_ 2 PRs, low risk, no consumers change yet
_Unblocks:_ Phase 2 consumer refactors

1. **PR #1: Create `pin-registry.toml`** — pure addition
   - Move current pin-parity entries (chezmoi, hk, mise) into authoritative registry format
   - Add claude-code entry (currently missing)
   - Document ownership: "single source of truth for all tool versions"
   - Update `pin-parity.toml` header to say "checker, not source" + add claude
   - No gate changes yet; no consumer changes
   - **Risk: ZERO** — new file, no readers
   - **Verification:** `grep -c "2\.1\.27[01]" pin-registry.toml` → returns claude version

2. **PR #2: Update `pin-parity.toml` gate to read the registry**
   - Gate now reads `pin-registry.toml` as source of truth
   - Gate validates all other pin sites (locks, .d.ts, doctor.toml, currency.toml, schemas/) match registry
   - Add claude-code to the checked sites list
   - Test: `mise run verify` passes, reports any drift
   - **Risk: LOW** — gate is informational, doesn't block builds
   - **Verification:** `mise run verify` exits 0, names all pin sites checked

**Phase 2: Consolidate into mise.toml** (requires Python tooling)

_Cost:_ 1 task + 1 CLI module, moderate risk, gates the PR
_Unblocks:_ Phase 3 cleanup

3. **PR #3: Add `pin-registry-to-mise` Python module**
   - New module: `python/src/dotfiles_setup/pin_registry.py`
   - Reads `pin-registry.toml`, exports as `{tool: version}` dict
   - **Consumer 1:** `fnhook_gates.py` reads registry instead of mise.toml directly
   - **Consumer 2:** `pin-parity.toml` gate uses registry as single source
   - Mise.toml still carries `[tools]` entries (mise CLI needs them); they are now synthesized from registry
   - New task: `mise run pin-sync -- <tool>` (or bare: sync all)
   - Test: fnhook-gates tests still pass; gate validates registry matches all pin sites
   - **Risk: MODERATE** — changes a consumer (fnhook_gates) that blocks all clause runs
   - **Verification:** Run `pytest tests/test_fnhook_gates.py:190` (the anti-tautology test); all tiers of `mise run verify` pass
   - **Also verify:** `.claude/types/claude-code.d.ts` is regenerated and matches registry version

**Phase 3: Retire redundant declarations** (optional, lower ROI)

_Cost:_ 1 PR, mechanical
_Unblocks:_ Next session has cleaner surface

4. **PR #4 (optional, follow-up): Remove `.claude/types/claude-code.d.ts` hardcoded version**
   - The version comment in `.claude/types/claude-code.d.ts:1` can be generated by the refresh task
   - Update `fnhook-types-refresh` task to read registry, write version comment
   - Removes one pin site (trade-off: adds task-level read to .d.ts generation)
   - **Risk: LOW but adds task dependency** — .d.ts is generated anyway
   - **Skip this if:** The .d.ts is checked into git for IDE support and the manual version is helpful

**Phase 4: Address retrieval** (separate ticket, beyond this scope)

_Not this PR, but necessary for lasting effect:_
- Index `pin-registry.toml` in session start (via doc ingestion or graphify refresh)
- Update knowledge-base `docs/research/mintlify-catalog.md` if this repo's config is catalogued there
- File a follow-up after #1054 (graph markdown nodes) closes

---

## Single Deciding Risk

**Coupling the build gate to a new config file adds a failure mode:** If `pin-registry.toml` becomes corrupt or missing, `fnhook_gates` raises `TypeError` before any plugin can run. Currently, the gate reads `mise.toml`, which is guardrailed by mise's own TOML parser and is tested in CI.

**Mitigation:**
- Make `pin_registry.py` read-only and cached; catch TOML parse errors with a clear message
- Keep the `TypeError` message friendly and name the file path
- Test: add a fixture that simulates missing/corrupt registry; confirm error message is helpful
- **Fallback:** If registry becomes unreliable, revert to reading mise.toml (registry becomes checker-only)

---

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — docs: config merging, templating, variables (step 0 KB source)
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — measured that native install at ~/.local/bin can coexist with mise pin

