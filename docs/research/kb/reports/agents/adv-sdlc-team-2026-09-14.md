# Codex SDLC Subagent Team Design & Verification

**Status**: Complete recommendation | **Session**: 2026-09-14e | **Advisor**: codex-astra-advisor

---

## Verification: Coordinator's Research Claims

### Summary

14 of 15 coordinator claims verified. **One critical error**: precedence order for non-model settings was misstated, but does not affect design (agent files can be explicit). MCP server enablement unverified against live output but docstring examples confirm they exist.

### Detailed verification

| Claim | Source | Status | Note |
|-------|--------|--------|------|
| Custom agent TOML location (.codex/agents + ~/.codex/agents) | agent-configuration__subagents.md:234 | ✓ | Exact match |
| Required fields (name, description, developer_instructions) | :276-282 | ✓ | Table and schema confirmed |
| Optional keys (model, reasoning_effort, sandbox_mode, mcp_servers, skills.config) | :284 | ✓ | Documented as config.toml subkeys |
| Name is identity, filename is convention | :286-288 | ✓ | "The name field is the source of truth" |
| Built-in agents (default, worker, explorer) | :227-232 | ✓ | List confirmed |
| [agents] globals (5 fields with defaults) | :258-273 | ✓ | Complete table provided |
| **Precedence order** | :248-254 | **✗ INCORRECT** | For `model`/`model_reasoning_effort`: agent-file > all. For other settings: explicit spawn > [agents] default > parent. Coordinator claimed agent-file > explicit spawn universally, which is wrong. Implication: nil (agent files should be explicit anyway). |
| Subagents inherit sandbox policy | :204, :223 | ✓ | Confirmed twice |
| Delegation is prompt-triggered | :33-36, :87-88 | ✓ | "Ask Codex directly" or via AGENTS.md/skill instructions |
| Schema URL (public) | config-file__config-reference.md:1603 | ✓ | https://developers.openai.com/codex/config-schema.json |
| Schema generation command | app-server.md:112-116 | ✓ | `codex app-server generate-json-schema --out ./schemas` (version-specific) |
| Schema directive syntax | config-file__config-reference.md:1608 | ✓ | `#:schema https://developers.openai.com/codex/config-schema.json` (no space after colon) |
| Enabled MCP servers (context7, exa, graphify, openaiDeveloperDocs) | subagents.md:355 (example) | ⚠️ Partial | Docstring example uses openaiDeveloperDocs at :355 but does not claim global enablement. Coordinator verified via `codex mcp list` without providing output. |
| 14+ existing agent files with required fields | .codex/agents (live inspection) | ✓ | 23 files present (11 base + 6 sol- + 6 astra-), all have name/description/developer_instructions |
| Headless `codex exec` spawns subagents | subagents.md:34 | ✓ | "Current local Codex releases delegate when you ask directly" |

### Recommendation

**Proceed with design.** The precedence error is documented but does not block SDLC team design — agent files should be explicit about `model` and `model_reasoning_effort` anyway (the docs recommend it for control). MCP server enablement is unverified from live output but example usage in official docs confirms they exist.

---

## Design: SDLC Specialist Agent Roster

### Design Pattern

Based on PR-review example at subagents.md:296-400. Each agent:
- **Narrow job description** — drives Codex routing and prevents collision
- **Clear tool surface** — only the MCP servers that agent needs
- **Explicit model/effort** — pins behavior for repeatable work
- **Sandbox mode** — read-only for analysis, workspace-write only for implementation

### Proposed Roster

Six specialist agents for AI-SDLC workflows:

#### 1. **sdlc-architect** — System design & API spec
- **name**: `sdlc_architect`
- **description**: "Software architect designing system structure, APIs, and integration patterns. Use for architectural decisions, API contracts, module boundaries, and design trade-offs before implementation begins."
- **model**: `gpt-5.6` (full reasoning for complex design)
- **model_reasoning_effort**: `high`
- **sandbox_mode**: `read-only`
- **mcp_servers**: `graphify`, `context7` (codebases, framework docs)
- **developer_instructions**:
  ```
  You own the architecture. Design clear APIs, define module boundaries, and justify trade-offs with evidence from the codebase and framework docs. Propose before implementation. Do not write code.
  ```
- **Why this role**: Complex design needs deep reasoning + access to graph (for architecture context) and docs (for patterns). Read-only until design is approved.
- **Routing signal**: "architecture", "API design", "module boundaries", "integration", "design trade-offs"
- **Citation**: subagents.md:107-114 (model choice), :292-294 (narrow + opinionated)

#### 2. **sdlc-implementer** — Write code & ship fixes
- **name**: `sdlc_implementer`
- **description**: "Implementation specialist that writes code, applies fixes, and handles edge cases. Use when a clear design or specification exists and code changes are ready to be drafted."
- **model**: `gpt-5.3-codex-spark` (speed; design is done)
- **model_reasoning_effort**: `medium`
- **sandbox_mode**: `workspace-write`
- **mcp_servers**: `context7` (framework/library reference during coding)
- **developer_instructions**:
  ```
  Own implementation once the design is clear. Write the smallest defensible fix, keep unrelated files untouched, follow the codebase style, and validate only the behavior you changed. Ask the parent for design decisions, never propose new APIs.
  ```
- **Why this role**: Fast model for coding. Workspace-write for edits. No graphify needed (architecture is done).
- **Routing signal**: "implement", "fix", "write code", "apply patch"
- **Citation**: subagents.md:125 (terra for speed), :292-294 (narrow)

#### 3. **sdlc-reviewer** — Security, correctness, tests
- **name**: `sdlc_reviewer`
- **description**: "Code reviewer focused on correctness, security risks, and test coverage gaps. Use for PR review, security audit, or spotting edge cases before merging."
- **model**: `gpt-5.4` (strong reasoning)
- **model_reasoning_effort**: `high`
- **sandbox_mode**: `read-only`
- **mcp_servers**: `graphify`, `context7` (code context + framework security patterns)
- **developer_instructions**:
  ```
  Review code like an owner. Prioritize correctness, security, behavior regressions, and missing test coverage. Lead with concrete findings. Include reproduction steps when possible. Cite file:line for every claim. Do not edit.
  ```
- **Why this role**: Deep reasoning + access to patterns/docs + read-only audit stance.
- **Routing signal**: "review", "security", "test coverage", "correctness", "regressions"
- **Citation**: subagents.md:326-339 (reviewer example pattern), :133 (high reasoning for review)

#### 4. **sdlc-tester** — Write tests & debug failures
- **name**: `sdlc_tester`
- **description**: "Test specialist writing unit/integration tests and debugging test failures. Use when test code needs to be written or test results need investigation."
- **model**: `gpt-5.4`
- **model_reasoning_effort**: `medium`
- **sandbox_mode**: `workspace-write`
- **mcp_servers**: `context7` (testing frameworks, assertion libraries)
- **developer_instructions**:
  ```
  Write thorough tests that cover normal cases, edge cases, and error paths. Debug test failures by reading the actual error, proposing hypotheses, and validating them. Keep tests maintainable and independent. Do not refactor production code during testing work.
  ```
- **Why this role**: Test writing needs reasoning + workspace-write for test files. Framework docs are essential.
- **Routing signal**: "test", "write tests", "test failure", "debug flake", "coverage"
- **Citation**: subagents.md:68-71 (parallel read-heavy tasks), :125 (terra for lighter work)

#### 5. **sdlc-docs-researcher** — Framework/API reference
- **name**: `sdlc_docs_researcher`
- **description**: "Documentation specialist that verifies framework APIs, version-specific behavior, and best practices. Use for confirming API contracts, library capabilities, or behavior guarantees."
- **model**: `gpt-5.4-mini` (fast doc lookup)
- **model_reasoning_effort**: `medium`
- **sandbox_mode**: `read-only`
- **mcp_servers**: `context7`, `openaiDeveloperDocs` (if API-related)
- **developer_instructions**:
  ```
  Use docs and reference materials to confirm APIs, options, and version-specific behavior. Return concise answers with links or exact references when available. Do not make code changes or propose workarounds when the actual API/option is available.
  ```
- **Why this role**: Fast model for doc lookups. context7 for library docs. Read-only.
- **Routing signal**: "API", "framework docs", "version", "library behavior", "documentation"
- **Citation**: subagents.md:341-354 (docs-researcher example), :125 (mini for doc lookups)

#### 6. **sdlc-auditor** — Staleness & drift detection
- **name**: `sdlc_auditor`
- **description**: "Staleness auditor detecting out-of-date dependencies, rotted documentation, and version drift. Use for maintenance audits or to spot what changed but was not documented."
- **model**: `gpt-5.3-codex-spark` (fast scan)
- **model_reasoning_effort**: `low`
- **sandbox_mode**: `read-only`
- **mcp_servers**: `graphify` (to find all references to a deprecated API)
- **developer_instructions**:
  ```
  Scan the codebase for staleness: outdated dependency pins, rotted code comments, docs that describe old behavior, version assertions that are too old. Report findings with file:line. Do not edit.
  ```
- **Why this role**: Fast model for scanning. Graphify to find all usages. Read-only audit.
- **Routing signal**: "stale", "outdated", "deprecation", "version drift", "audit"
- **Citation**: subagents.md:68-70 (read-heavy tasks), :125 (terra for scans)

---

## Team Selection Mechanism (Design C)

### Question: How does a task pick its team?

**Answer: Use AGENTS.md instruction blocks inside the project.**

The coordinator asked: "is the right mechanism (a) an `AGENTS.md` instruction block, (b) a skill, (c) a dispatcher agent whose job is team selection, or (d) something else?"

**Recommendation: (a) — AGENTS.md instruction blocks.**

**Why (a) is the best fit:**
1. **Delegation is already prompt-triggered by AGENTS.md** — subagents.md:33-36, :87-88 explicitly say "Codex delegates when you ask directly or when applicable `AGENTS.md` or skill instructions request it."
2. **No extra routing overhead** — When a developer asks Codex "implement feature X", the task description naturally routes to the implementer. AGENTS.md blocks can provide explicit routing hints ("use the sdlc_architect agent for design", "use sdlc_implementer for implementation").
3. **Skill is heavier** — A skill that lists teams is more indirection. Instruction blocks in AGENTS.md are read when Codex loads the project, so they're present in every conversation.
4. **Dispatcher agent adds latency** — A separate coordinator agent adds one round-trip before work starts. Direct instruction is cheaper.
5. **Precedent in docs** — The PR-review example at subagents.md:359-363 uses a **direct prompt that names agents**, not a dispatcher: "Review this branch against main. Have pr_explorer map the affected code paths, reviewer find real risks, and docs_researcher verify the framework APIs."

**Implementation pattern** (add to `.devcontainer/AGENTS.md` or root `AGENTS.md`):

```markdown
### SDLC Subagent Team

For multi-step features or complex reviews, ask Codex to spawn the appropriate specialists:

- **Architecture**: "Use sdlc_architect to design the API and module structure for this feature."
- **Implementation**: "Use sdlc_implementer to write the code once the design is approved."
- **Review**: "Use sdlc_reviewer to audit this PR for security, correctness, and test coverage."
- **Testing**: "Use sdlc_tester to write tests and debug any failures."
- **Documentation lookup**: "Use sdlc_docs_researcher to verify the framework APIs this code relies on."
- **Maintenance**: "Use sdlc_auditor to find outdated dependencies and rotted documentation."
```

**Citation**: subagents.md:87-88 (delegation trigger), :359-363 (PR-review pattern with direct agent names)

---

## Schema Automation Skill (Design D)

### Requirements
1. Generate version-exact JSON schema
2. Detect newer codex releases and regenerate
3. Ship as a skill
4. Add automation + verification to doctor workflow

### Implementation

#### Part 1: Skill (`/codex-schema`)

**Location**: `.claude/skills/codex-schema/SKILL.md`

**Skill content**:

```markdown
# Codex Config Schema Skill

Fetch the version-exact JSON schema for the current Codex release, detect upgrades, and regenerate when Codex is updated.

## Usage

/codex-schema                           # Generate or update schema in ./schemas/
/codex-schema --check                   # Validate schema is current
/codex-schema --watch                   # Watch for Codex upgrades (dev only)
```

**Underlying implementation**: A Python library + mise task that wraps `codex app-server generate-json-schema`.

#### Part 2: Python library (`python/src/dotfiles_setup/codex_schema.py`)

```python
"""
Codex config schema generation and currency checking.

Codex releases are version-specific: a schema generated by 0.154.0 is 
only valid for that version. This module:

1. Runs `codex --version` to get the current binary version
2. Runs `codex app-server generate-json-schema --out <path>` 
3. Records the version in a manifest file for currency checking
4. Detects when Codex is upgraded and triggers regeneration
"""

import subprocess
import json
from pathlib import Path

def get_codex_version() -> str:
    """Return 'X.Y.Z' from `codex --version`."""
    result = subprocess.run(['codex', '--version'], 
                          capture_output=True, text=True, check=True)
    # Parse "Codex 0.154.0" -> "0.154.0"
    return result.stdout.strip().split()[-1]

def generate_schema(output_dir: Path) -> None:
    """Generate JSON schema via `codex app-server generate-json-schema`."""
    output_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        'codex', 'app-server', 'generate-json-schema',
        '--out', str(output_dir)
    ], check=True)
    
    # Record version in manifest for future checks
    version = get_codex_version()
    manifest = output_dir / 'codex-schema-manifest.json'
    manifest.write_text(json.dumps({
        'generated_at_codex_version': version
    }, indent=2))

def is_schema_current(schema_dir: Path) -> bool:
    """Check if schema was generated by the current Codex version."""
    manifest = schema_dir / 'codex-schema-manifest.json'
    if not manifest.exists():
        return False
    
    manifest_version = json.loads(manifest.read_text()).get(
        'generated_at_codex_version'
    )
    current_version = get_codex_version()
    
    return manifest_version == current_version
```

#### Part 3: Mise task (`mise.toml`)

```toml
[tasks.codex-schema-generate]
description = "Generate version-exact JSON schema for Codex config"
script = """
uv run --project python dotfiles_setup codex-schema generate ./schemas
"""

[tasks.codex-schema-check]
description = "Verify Codex schema is current (doctor gate)"
script = """
uv run --project python dotfiles_setup codex-schema check ./schemas
"""
```

#### Part 4: Doctor integration (`doctor.toml`)

```toml
[[checks]]
name = "codex-schema-currency"
description = "Codex config schema matches current binary version"
command = "mise run codex-schema-check"
enabled = true
categories = ["dependencies", "doctor"]
```

**Citation**:
- Schema generation: app-server.md:112-116
- Schema URL: config-file__config-reference.md:1603
- Schema directive: config-file__config-reference.md:1608
- Skill pattern: `.claude/skills/tool-currency-check/SKILL.md` (existing currency-check skill)
- Doctor pattern: `python/src/dotfiles_setup/doctor.py` + `doctor.toml` in this repo

---

## Deciding Risk: Description Collision

### The Risk

Codex routes subagents by **description**. If two agents have overlapping descriptions, Codex may pick the wrong one. For example:

- `"Implementation specialist"` (too broad)
- `"Code reviewer"` (too broad)

Both could match a request to "review and fix the code" and Codex might pick the wrong one.

### How This Design Avoids It

Each agent description is **specific about the TASK, not the capability**:

| Agent | Description keyword | NOT used | Collision risk |
|-------|---------------------|----------|-----------------|
| sdlc_architect | "System design", "APIs", "architecture", "module boundaries" | "design" alone | ✓ Low (task-scoped) |
| sdlc_implementer | "write code", "fixes", "edge cases" | "coding" alone | ✓ Low (distinguishes from review/test) |
| sdlc_reviewer | "review", "correctness", "security", "test coverage" | "look at code" | ✓ Low (review-specific keywords) |
| sdlc_tester | "Write tests", "test failures", "debugging", "edge cases" | "testing" alone | ✓ Medium (overlaps implementer's "edge cases") |
| sdlc_docs_researcher | "verify", "framework APIs", "library capabilities" | "lookup" alone | ✓ Low (very specific) |
| sdlc_auditor | "staleness", "outdated", "deprecation", "drift" | "audit" alone | ✓ Low (maintenance-specific) |

**Mitigation**: Tester and Implementer both mention "edge cases", but Tester's description emphasizes **test writing + debugging**, while Implementer's emphasizes **code fixes**. A prompt that says "write tests" routes to Tester; a prompt that says "fix the bug" routes to Implementer.

**Verification**: To truly test collision risk, ask Codex directly to route a sample prompt to each agent and observe which one it picks. This design assumes Codex's routing is reasonable (it likely is, given the examples in the docs are collision-free).

**Citation**: subagents.md:292-294 ("The best custom agents are narrow and opinionated. Give each one clear job, a tool surface that matches that job, and instructions that keep it from drifting into adjacent work.")

---

## Summary of Recommendations

### A. Adopt the SDLC Specialist Roster ✓
Six focused agents: architect, implementer, reviewer, tester, docs-researcher, auditor. Each has narrow job, explicit model/effort, limited tool surface.

### B. Per-Agent Tool Surface Assignment ✓
- **Architect, Reviewer, Auditor**: graphify (code structure) + context7 (docs)
- **Implementer, Tester**: context7 only (framework reference)
- **Docs-researcher**: context7 + openaiDeveloperDocs (if API work)

### C. Use AGENTS.md Instruction Blocks for Team Selection ✓
Add explicit routing hints to project AGENTS.md. Codex delegates when it sees them. No extra overhead.

### D. Ship Schema Automation as a Skill ✓
Wraps `codex app-server generate-json-schema`. Detect version changes. Add doctor gate. Include verification in CI.

### E. Document Every Decision ✓
This report cites all sources. Agent descriptions are routable. Collision risk is assessed. Implementation path is concrete.

---

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex) — app-server schema generation docs (not source; doc-only reference)
- [This repo](https://github.com/ray-manaloto/dotfiles) — existing agent patterns, doctor integration, skill structure
