# Codex Upstream Research — 2026-09-10

**Goal:** Establish facts about codex for running it as an automated agent lane, including models, reasoning effort, agent support, headless/automation surface, version-to-version breakage, and known bugs.

**Status:** In progress. Incremental research findings below.

---

## 1. Models Supported

### gpt-6-astra
- **Model ID:** `gpt-6-astra`
- **Status:** Current default model as of codex 0.154.0 (verified by Ray: CLI resolves to this model)
- **Verified working:** Yes, confirmed in 0.154.0 by team-lead
- **Prior issue:** HTTP 400 errors in codex 0.152.1 when calling gpt-6-astra (now fixed in 0.154.0)

### gpt-5.6-sol
- **Model ID:** `gpt-5.6-sol`
- **Status:** Explicitly supported via `-m` flag
- **Example:** `-m gpt-5.6-sol` works correctly
- **Verified working:** Implied by being in codex examples for reasoning-heavy work

### Other models
_To be researched: what other model IDs are supported, if any._

### Security work claim (UNVERIFIED)
**Claim to verify:** `gpt-6-astra` REFUSES authorized security work while `gpt-5.6-sol` does not.
- **Source of claim:** Sibling repo (stated by owner to be potentially buggy, NOT trustworthy)
- **Primary evidence:** NOT YET FOUND in codex upstream
- **Status:** UNVERIFIED — no evidence found yet in official docs, GitHub issues, or release notes

---

## 2. Reasoning Effort

### Supported values
_Researching: which values are valid, what they cost/buy, defaults._

### Interaction with model choice
_To be researched: does effort change behavior per model?_

---

## 3. Agent / Multi-Agent Support

_To be researched: what codex offers for defining roles, spawning sub-agents, orchestrating work._

---

## 4. Headless/Automation Surface

### Exit codes
_To be researched: what exit codes signal failure vs success._

### Output capture
- `-o <file>` flag: Captures output to a file (verified working by team-lead)
- Streaming vs file: TBD

### Failure detection
- **Prior incident:** Silent HTTP 400 errors in 0.152.1 papered over by calling code
- **Current behavior:** TBD — need to verify exact failure signatures in 0.154.0

### Timeouts, retries, rate limits
_To be researched: documented behavior._

---

## 5. Version-to-Version Breakage

### 0.152.1 → 0.154.0
- **Breaking issue:** HTTP 400 errors when calling default model (now fixed)
- **Root cause:** TBD
- **Implication:** Pinned versions can silently fail if the default model becomes unreachable
- **Lesson:** Explicit `-m` model flag is safer for automation than relying on default

---

## 6. Known Bugs and Open Issues

_To be researched: scan GitHub issues and discussions for automation-relevant bugs._

---

## Research Plan

Next steps:
1. Review codex GitHub repository (https://github.com/openai/codex) for README, docs, issues
2. Check release notes/CHANGELOG for models, reasoning effort, known issues
3. Consult official documentation for automation best practices
4. Search GitHub discussions for reported failures in headless/agent use

---

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex) — official codex repository (pending deeper research)


## 1. Models Supported (VERIFIED from codex_models.json 0.153.4)

### Current Model Catalog
- **gpt-6-astra** (priority 1, highest): "Our most capable model for complex, demanding work"
  - Context: 272K base, 872K max
  - Default reasoning: low
  - Supported reasoning efforts: low, medium, high, xhigh, max, ultra
  - Visibility: list (was hidden in 0.153.3, visible in 0.153.4)
  - Source: https://raw.githubusercontent.com/openai/codex/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/docs/codex_models.json

- **gpt-5.6-sol** (priority 6): "Latest frontier agentic coding model"
  - Context: 272K base, 872K max
  - Default reasoning: low
  - Supported reasoning efforts: low, medium, high, xhigh, max, ultra
  - Visibility: list

- **gpt-5.6-terra** (priority 3): Faster, lower-cost option for lighter work
  - Context: 272K base, 872K max

- **gpt-5.6-luna** (priority 5): "Fast model for narrowly scoped work"
  - Context: 272K base, 272K max

- **gpt-5.4-mini** (priority 23): "Small, fast, cost-efficient model"
  - Context: 272K base, 272K max

- **gpt-5.2** (priority 29): "Optimized for professional work and long-running agents"
  - Context: 272K base, 272K max

- **gpt-5.4** (priority 16): (DEPRECATED — retired 2026-08-31, migrate to gpt-5.6-terra)
  - Visibility: hide

- **codex-auto-review** (priority 43): "Automatic approval review model for Codex" (hidden)
  - Context: 272K base, 872K max
  - Visibility: hide

### Security Work Claim — UNVERIFIED
**Claim:** gpt-6-astra REFUSES authorized security work while gpt-5.6-sol does not.
- **Status:** No evidence found in:
  - Official model catalog (codex_models.json)
  - Official documentation (learn.chatgpt.com)
  - GitHub repository README, docs, or CHANGELOG
  - GitHub issues (scanned top 20 recent)
- **Conclusion:** Claim is UNVERIFIED. Likely false — no capability distinction noted in any official source. If true, it would be documented as a model capability limitation.

---

## 2. Reasoning Effort (VERIFIED from documentation)

### Supported Values and Descriptions
Per the subagents documentation and model catalog:

| Effort  | Description                                              | Use Case                                              |
|---------|----------------------------------------------------------|-------------------------------------------------------|
| `low`   | Fast responses with lighter reasoning                    | Straightforward tasks where speed matters most        |
| `medium`| Balances speed and reasoning depth for everyday tasks    | Balanced default for most agents                      |
| `high`  | Greater reasoning depth for complex problems             | Complex logic, trace assumptions, edge cases          |
| `xhigh` | Extra high reasoning depth for complex problems          | Especially demanding reasoning                        |
| `max`   | Maximum reasoning depth for the hardest problems         | Hardest problems requiring maximum depth             |
| `ultra` | Maximum reasoning with automatic task delegation         | Deepest reasoning + proactive subagent delegation     |

### Model Support Matrix
- **All current models support:** low, medium, high, xhigh, max, ultra
  - Source: codex_models.json supported_reasoning_levels for each model
- **Default effort per model:** "low" across all current models (gpt-6-astra, gpt-5.6-sol, gpt-5.6-terra, etc.)
  - Source: codex_models.json default_reasoning_level field

### CLI Flag
- Use `-c model_reasoning_effort="<effort>"` to set reasoning effort
- Example: `codex exec -c model_reasoning_effort="xhigh" -m gpt-5.6-sol "...prompt..."`
- If omitted, uses model's default_reasoning_level (currently "low" for all models)

---

## 3. Agent / Multi-Agent Support (VERIFIED from documentation)

### Subagent Workflows (Enabled by Default)
- **Availability:** Enabled in current Codex releases (0.146.0+)
- **Spawning:** Request explicitly ("spawn two agents", "delegate in parallel") OR via project/skill instructions
- **Orchestration:** Codex handles spawning, routing, waiting for results, closing threads
- **Token consumption:** Subagent workflows consume MORE tokens than single-agent (each subagent does own model + tool work)

### Built-In Agents (always available)
- `default`: general-purpose fallback
- `worker`: execution-focused for implementation and fixes
- `explorer`: read-heavy codebase exploration

### Custom Agents
- Define in `~/.codex/agents/<name>.toml` (personal) or `.codex/agents/<name>.toml` (project-scoped)
- Each file defines ONE custom agent with required fields:
  - `name`: agent identifier
  - `description`: human-facing guidance
  - `developer_instructions`: core behavior instructions
- Optional fields: `model`, `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`, `skills.config`
- Model resolution order: explicit spawn value → `[agents]` config default → parent value → model's default effort
- Example use: `Review this PR with parallel subagents. Spawn one for security, one for tests, one for maintainability. Wait for all three, then summarize by category.`

### Global Configuration (in config.toml `[agents]` section)
- `agents.enabled` (bool, default=true): enable/disable multi-agent tools
- `agents.max_concurrent_threads_per_session` (int): cap concurrent spawned-agent threads
- `agents.default_subagent_model` (string): default model for spawned agents
- `agents.default_subagent_reasoning_effort` (string): default reasoning for spawned agents
- `agents.interrupt_message` (bool, default=true): record model-visible message on agent interruption

### Approval and Sandbox
- Subagents inherit parent's sandbox policy and approval mode
- In CLI, approval requests can surface from inactive threads; press `o` to open that thread before approve/reject

---

## 4. Headless/Automation Surface (VERIFIED from documentation)

### Non-Interactive Mode: `codex exec`
- **When to use:** pipelines, CI jobs, scheduled work, piped output
- **Invocation:** `codex exec "<prompt>"` or `echo "prompt" | codex exec -`
- **Output:** Streams progress to stderr, final message to stdout (allows piping)

### Output Capture
- **Text output:** Default stdout or via pipe
- **File output:** `-o <path>` / `--output-last-message <path>` (writes final message to file AND stdout)
- **JSON Lines streaming:** `--json` flag enables JSONL stream on stdout (every event: thread.started, turn.started, turn.completed, turn.failed, item.*, error)
- **Structured output:** `--output-schema <schema.json>` constrains final response to JSON Schema
  - Example: `codex exec "Extract metadata" --output-schema ./schema.json -o ./output.json`

### Sandbox and Safety
- **Default:** read-only sandbox (`--sandbox read-only`)
- **Allow edits:** `--sandbox workspace-write`
- **Allow broader access:** `--sandbox danger-full-access` (only in controlled environments)
- **Deprecated flag:** `--full-auto` (use `--sandbox workspace-write` instead)
- **Skip config:** `--ignore-user-config` (don't load $CODEX_HOME/config.toml)
- **Skip execpolicy:** `--ignore-rules` (skip user/project .rules files)
- **MCP servers:** Required servers with `required = true` cause exit with error if initialization fails

### Authentication in Automation
- **Default:** Reuses saved CLI authentication (~/.codex/auth.json or OPENAI_API_KEY)
- **API key:** Set `CODEX_API_KEY` only for the single invocation (don't export as job-level env)
  - Example: `CODEX_API_KEY=<key> codex exec --json "<task>"`
- **GitHub Action:** Use `openai/codex-action` instead (reduces API key exposure via secure proxy)

### Session Control
- **Ephemeral mode:** `--ephemeral` flag (don't persist rollout files to disk)
- **Resume:** `codex exec resume --last "<next-task>"` or `codex exec resume <SESSION_ID>`
- **Git requirement:** Codex requires running inside a Git repo; override with `--skip-git-repo-check`

### Exit Codes (IMPLICIT from documentation)
- Non-interactive flows: "whenever a run can't surface a fresh approval, an action that needs new approval fails and Codex surfaces the error back to the parent workflow"
- Implication: Exit 0 on success, non-zero on failure (failure includes approval denials, missing required MCP servers, Git repo check)
- **NOT EXPLICITLY DOCUMENTED** what specific exit codes mean; only that approval failures and MCP failures cause non-zero exits

### Stdin Piping Patterns
1. **Prompt-plus-stdin:** `command | codex exec "<instruction>" | next-command`
   - Instruction explicit, piped output as context
2. **Stdin-as-prompt:** `command | codex exec -` or `codex exec -`
   - Entire prompt comes from stdin

---

## 5. Version-to-Version Breakage

### 0.152.1 → 0.154.0 (DOCUMENTED REGRESSION)
- **Issue:** HTTP 400 errors when calling gpt-6-astra in 0.152.1
- **Fix:** Resolved in 0.154.0 (verified working by team-lead)
- **Root cause:** NOT DOCUMENTED in CHANGELOG
- **Lesson:** Pinned versions can silently fail if model routing breaks; explicit `-m gpt-5.6-sol` is safer than relying on default

### Model Deprecations
- **gpt-5.4:** Retired 2026-08-31, migrate to gpt-5.6-terra
  - Source: codex_models.json upgrade field with retirement_at timestamp

### Visibility Changes (0.153.3 → 0.153.4)
- **gpt-6-astra:** Changed from `visibility: "hide"` → `visibility: "list"`
  - Implication: gpt-6-astra was not available to users in 0.153.3, became available in 0.153.4

### Known Version History
- Codex versions with documented releases: 0.125.0 through 0.153.4
- Full CHANGELOG available at: https://github.com/openai/codex/releases

---

## 6. Known Bugs and Open Issues (FROM GITHUB)

### Automation-Relevant Issues (scanned 2026-09-10)

#### High-Priority for Agent Lanes
1. **#44456: Remote compaction fails on full context with GPT-6 Astra**
   - Status: Linux + VS Code
   - Impact: Thread becomes unrecoverable when context full
   - URL: https://github.com/openai/codex/issues/44456

2. **#44382, #44405, #44395: "Selected model is at capacity" errors**
   - Status: Multiple reported, affects usability
   - Impact: Model becomes unavailable mid-run
   - Mitigation: May need to retry with different model or lower reasoning effort
   - URL: https://github.com/openai/codex/issues/44382

#### Windows-Specific (Less relevant for Linux automation)
- #44447: Windows 11 IoT Enterprise sandbox setup fails
- #44454: WSL project creation fails
- #44401: Windows app-server queue blocks plugins

#### Old Issues (May be Fixed)
- #29546: gpt-5.5 returns 404 (likely related to deprecation cycle)
- #31935: 60-second blocking wait limit (affects long-running agents)

### No Issues Found Regarding:
- gpt-6-astra refusing security work (supports the UNVERIFIED claim)
- gpt-5.6-sol having different refusal patterns
- Exit code behavior in automation
- Reasoning effort breakage between versions

---

## Summary & Recommendations for Automation

### Safe Automation Pattern
```bash
# Explicit model, explicit reasoning, explicit sandbox
codex exec \
  -m gpt-5.6-sol \
  -c model_reasoning_effort="xhigh" \
  --sandbox workspace-write \
  --ephemeral \
  -o /tmp/result.md \
  "$(cat prompt.txt)"
```

### Key Takeaways
1. **Always use explicit `-m` model flag** — default model availability changed between 0.152.1 and 0.154.0
2. **Reasoning effort defaults to "low"** — explicitly set if you need deeper reasoning (xhigh, max, ultra)
3. **Model capacity errors are real** — have a retry strategy and fallback model (gpt-5.6-terra)
4. **Subagent workflows consume more tokens** — appropriate for parallel work but not for simple tasks
5. **Exit code behavior not fully documented** — test locally; approval failures and MCP init failures cause non-zero exit
6. **Security work capabilities undocumented** — no evidence that gpt-6-astra refuses authorized security; claim is likely false

---

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex) — official repository with CLI source, docs, and issues tracker
- [openai/codex-action](https://github.com/openai/codex-action) — GitHub Action for secure API key handling
- [openai/codex-docs](https://github.com/ray-manaloto/knowledge-base/tree/main/sources/codex-docs) — community mirror synced in this KB (reference for weekly updates and capability snapshots)

