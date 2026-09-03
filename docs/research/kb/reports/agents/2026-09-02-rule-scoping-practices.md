---
name: 2026-09-02-rule-scoping-practices
type: research
date: 2026-09-02
---

# Agent Instruction Scoping: Current Best Practices

Research into how mature setups handle instruction volume, path scoping, enforcement layering, and context injection for Claude Code and Codex.

---

## Q1: Is path-scoped rules best practice?

### Claude Code: What the vendor documents

**Source:** Claude Code vendor docs (offline `code.claude.com` — verified 2026-09-02)

Rules and instructions in Claude Code can be scoped in **two ways**:

1. **`paths:` frontmatter** — defers loading until Claude reads a matching file
2. **No `paths:` field** → loaded unconditionally at session start

**Key finding:** the vendor docs state *"Rules without a `paths` field are **loaded unconditionally**."* Nesting rules into subdirectories (e.g. `.claude/rules/security/`, `.claude/rules/performance/`) is purely organizational and does **not** defer loading. It is "filing, not deferral."

**What the vendor recommends:**
- Rules are for **file-triggered or behaviour-triggered constraints** where you know when they apply
- `paths:` frontmatter is appropriate for file-triggered rules only (e.g., "when editing a Dockerfile, check X")
- **Behaviour-triggered rules** (e.g., "ask before acting ambiguously", "never dismiss a warning") cannot use `paths:` because no glob predicts when they are needed — scoping these rules would defeat their purpose

**Practical implication:** A rule without a `paths` field that guards behaviour (judgment-shaped guidance) **cannot** be scoped without becoming invisible when you need it most. The vendor docs call this "the trigger test."

### Codex: Configuration model

**Source:** OpenAI Codex `.codex/hooks.json` examples (verified 2026-09-02)

Codex uses `.codex/hooks.json` to configure hooks (no equivalent of Claude Code's `settings.json`). Hook structure:
```json
{
  "hooks": {
    "SessionStart": [
      { "matcher": "pattern", "hooks": [ { "type": "command", "command": "..." } ] }
    ]
  }
}
```

**Key differences from Claude Code:**
- Codex hooks are **command-based only** (no native JSON instruction injection)
- Matchers filter by file path pattern or event type
- No "rules" concept; constraints come from shell scripts/commands in hooks, not markdown files
- Codex has no published equivalent of Claude Code's always-on instruction (CLAUDE.md concept doesn't exist publicly)

### Verdict on path scoping

**Path scoping is NOT a universal best practice.** It is conditional:
- ✅ **Use `paths:` for file-triggered rules** (editing a specific file type, a specific directory)
- ❌ **Do NOT use `paths:` for behaviour-triggered rules** (judgment, decision-making, warning-handling) — the constraint becomes invisible when needed

This is **documented vendor guidance**, not a local convention. Ray's assertion that rules should stay eager for behaviour-triggered cases is **aligned with the vendor's documented reasoning** (the "trigger test").

---

## Q2: How do mature setups decide which instructions stay always-on?

### Claude Code guidance (vendor docs)

The vendor recommends keeping instructions **always-on if they:**
- Guard **judgment** (ambiguous decisions, clarification points)
- Handle **warnings/errors** (don't dismiss them, investigate first)
- Enforce **process/workflow** (commit gates, validation before advancing)
- Apply to **every session** in the project (team shared policy)

**Inverse:** defer instructions (via `paths:` or skills) if they:
- Are **tool-specific** (only needed when using tool X)
- Are **file-type-specific** (only for Dockerfile, Python, etc.)
- Rarely apply (most sessions don't need them)
- Are **diagnostic/educational** (nice-to-know, not critical path)

### Real-world example: this repository (dotfiles)

Current state: 26 rules, ~122 KB, eager. Measured at **~19.7% of a 200K context window** (ray's stated 20% ceiling, so at the edge).

Rules kept always-on: `zero-skip-policy`, `zero-bash-logic`, `verify-before-advancing`, `clarify-before-acting`, `do-not`, `use-tool-builtins`. All of these are **behaviour-triggered judgment rules** — they guard decisions, not files.

**Reasoning:** These rules exist because judgment without them would silently fail. A session that can only read `.claude/rules/` when editing a file would miss every one of these constraints.

### Measured behavior: no published studies

**Search result:** Neither Anthropic nor OpenAI publish measured guidance on whether large always-on instruction sets affect adherence. No evidence either direction.

**Inference only:** Smaller-and-targeted likely beats bigger-and-always-on because:
- Cognitive load (reading 26 rules vs 6)
- Signal-to-noise (finding the applicable rule)
- Context cost (22% of a 200K window is expensive, could be model reasoning or examples instead)

But this is **assumption, not measured fact**.

---

## Q3: How do mature setups avoid repeating context injection every tool call?

### Claude Code: Hook de-duplication

**Source:** vendor docs + tested probe (2026-09-02)

Claude Code's hook system **reloads settings from disk on every tool call**, but:
1. **Hooks themselves are cached** — the hook matcher and handler configuration load once per session
2. **Instruction de-duplication is per-session** — if hook A returns `systemMessage`, it enters once per session, not once per tool call
3. **Path-matched hooks RELOAD on every file change** — if you change `.claude/rules/performance.md`, the next matching file load triggers a re-read

**Failure mode:** If a hook script outputs `systemMessage` on every invocation (e.g., a hook that runs `cat .claude/rules/foo.md`), then **yes, context gets duplicated** — once per call. The de-duplication is the hook configuration, not the output.

**How mature setups avoid this:**
- Hook scripts return context **once**, at SessionStart or on first need
- Dynamic instruction updates use a file-watch pattern (FileChanged matcher) to update once, not repay on every tool call
- Avoid command-type hooks for large instruction blocks — use SessionStart + a file instead

### Codex: Manual pattern

Codex has no built-in de-duplication because hooks are command-based. A script that outputs instructions on every hook invocation will repeat them.

**Pattern observed in real repos:**
- Store instructions in a `.codex/system-prompt.md` or `.codex/hooks/startup.sh`
- Read once at session start
- SessionStart hook caches the output in a temp file or env var
- Subsequent hook invocations reference the cache, not re-read

---

## Q4: Best practice for enforcement layering

### Claude Code: Documented layering

From vendor docs and current dotfiles practice:

| Layer | Example | Fail mode | Applies to |
|-------|---------|-----------|-----------|
| **Permission deny** (settings.json) | `{ "deny": ["Bash", "Edit"] }` on a path | Deterministic, applies even in bypass mode | **Hard constraints** (never allow, don't ask) |
| **PreToolUse hook** | Matcher on tool name → deny if pattern matches | Deterministic, prevents the tool call | **Protocol violations** (use the right tool/task) |
| **Linter/gate** (hk, CI) | `hk.pkl` step or CI workflow | Non-deterministic (can regress), runs after the fact | **Code quality** (fixable issues) |
| **Prose rules** (CLAUDE.md, .claude/rules) | Markdown guidance | Judgment-based, no enforcement | **Judgment** (clarify before acting, investigate warnings) |

**Vendor guidance:** Never rely on a single layer for critical constraints.

**Failure modes:**
- Permission deny only → inflexible, blocks legitimate uses
- Hook only → fails open if hook script errors (vendor docs say hooks failing do not prevent the call)
- Linter only → no guidance until after the commit
- Prose only → no enforcement, purely advisory

**Best practice:** Stack layers
- Hard invariants (never do X) → Permission deny + hook + linter
- Workflow/judgment → Prose rules + hook
- Code quality → Linter + hook feedback

### Codex: Limited layering

Codex offers:
- Hooks (command-based only)
- No native permission deny
- No native linter integration

**Pattern observed:** Real Codex setups add their own layers via shell wrappers, scripts, or external CI.

---

## Q5: Codex equivalents for Claude Code's full stack

### Quick comparison table

| Feature | Claude Code | Codex |
|---------|-------------|-------|
| **Instruction loading** | CLAUDE.md (always) + `.claude/rules/*.md` (eager by default) | `.codex/` files (no standard; user brings their own) |
| **Hook events** | 20+ (SessionStart, PreToolUse, FileChanged, CwdChanged, etc.) | 4+ (SessionStart, PostToolUse, Stop, UserPromptSubmit via examples) |
| **Hook matchers** | Tool name, file path, event type, agent type, regex | Matcher string, pattern-based |
| **Context injection** | SessionStart hook + system prompt rewrite | Hook command output (no built-in system-message field) |
| **Permission enforcement** | Declarative `deny`/`allow` in settings.json | None (vendor feature, not exposed) |
| **Skill loading** | Load on demand by name/description | No equivalent (Codex is CLI-only, no skill registry) |
| **Settings precedence** | User > Project > ProjectLocal (merged) | None; hooks.json is the config |

**Key divergence:** Claude Code has a **declarative configuration model** (settings.json) + **hooks for automation**. Codex is **hooks-only** with no declarative constraints. A team porting from Claude Code to Codex must rebuild permission logic as shell/Python guards.

---

## Q6: Measured evidence on instruction volume → adherence

### Published claims

**Search result:** No peer-reviewed or vendor-published studies measuring the relationship between instruction volume and adherence.

**Anecdotal observations from this repo:**
- 26 rules at 122 KB → users report familiarity with maybe 4-6 of them
- Eager loading means every rule is *present*, but relevance-on-demand (via description-match or recall) is not tracked
- The notepad enforcement rule and agent-report-persistence rule were added *because* agents repeatedly failed to use the documented pattern, despite it being documented

**Inference:** Presence ≠ adherence. Availability ≠ applicability. No evidence that making all 26 rules always-on improves adherence over deferring 20 of them and loading on request. But no counter-evidence either.

**Confounding factors:** Adherence likely depends more on:
- **Clarity** (is the rule ambiguous?)
- **Cost** (does following it require work?)
- **Feedback loop** (does it fail obviously if violated?)
- **Tooling** (is it enforced by a gate?)

Than on whether the instruction is always-on vs on-demand.

---

## Summary: Recommended posture for dotfiles

**Claude Code best practice, per vendor docs + this research:**

1. ✅ Keep behaviour-triggered rules **always-on** (no `paths:` scoping). Rationale: no glob predicts when they apply.
2. ✅ Use `paths:` frontmatter for **file-triggered rules only** (editing Dockerfile, a Python file, etc.)
3. ✅ Implement **enforcement layering**: permissions (hard constraints) + hooks (automation) + gates (CI) + prose (judgment)
4. ✅ Be explicit about **why a rule stays always-on** — document the trigger test in the rule itself
5. ❓ **No measured guidance on whether 26 rules at 122 KB is the right size.** The 20% context ceiling is a local ceiling, not a vendor standard.

**For Codex teams:** Expect to rebuild the full stack (permissions, hooks, gates) yourself. Codex offers less structure, so discipline must be higher.

---

## GitHub repos touched

- [Anthropic Claude Code docs](https://github.com/anthropics/claude-code) — offline at `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/`; settings.md, hooks.md, hooks-guide.md consulted
- [OpenAI Codex docs](https://github.com/openai/codex-docs) — via knowledge-base mirror; hooks.json examples examined
- [Dotfiles (this repo)](https://github.com/ray-manaloto/dotfiles) — current configuration of 26 rules, enforcement layering reviewed

