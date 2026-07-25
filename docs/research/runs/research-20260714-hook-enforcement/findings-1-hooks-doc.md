# Stream 1 — Authoritative Claude Code hooks doc (policy-enforcement surface)

Source: <https://code.claude.com/docs/en/hooks> (fetched 2026-07-14). Verbatim
extraction below; quotes are from the doc's own sections.

## Decision-control table (verbatim)

| Events | Decision pattern | Key fields |
|---|---|---|
| UserPromptSubmit, UserPromptExpansion, PostToolUse, PostToolUseFailure, PostToolBatch, Stop, SubagentStop, ConfigChange, PreCompact | Top-level `decision` | `decision: "block"`, `reason`. Stop/SubagentStop also accept `hookSpecificOutput.additionalContext`. |
| PreToolUse | `hookSpecificOutput` | `permissionDecision` (allow/deny/ask/defer), `permissionDecisionReason` |
| PermissionRequest | `hookSpecificOutput` | `decision.behavior` (allow/deny) |
| PermissionDenied | `hookSpecificOutput` | `retry: true` |

## additionalContext vs systemMessage (verbatim)

> The `additionalContext` field passes a string from your hook into Claude's
> context window. Claude Code wraps the string in a system reminder and inserts
> it into the conversation at the point where the hook fired. Claude reads the
> reminder on the next model request, but it doesn't appear as a chat message.

Where it appears, by event:
- SessionStart/Setup/SubagentStart: start of conversation, before first prompt
- **UserPromptSubmit/UserPromptExpansion: alongside the submitted prompt**
- **PreToolUse/PostToolUse/PostToolUseFailure/PostToolBatch: next to the tool result**
- Stop/SubagentStop: end of the turn (conversation continues)

`systemMessage` = "Warning message shown to the user" (user-facing only; NOT
model-visible). `additionalContext` = model-facing.

## ★ Official guidance — the load-bearing quote (verbatim)

From "Add context for Claude":

> Use `additionalContext` for information Claude should know about the current
> state of your environment or the operation that just ran:
> - **Environment state**: the current branch, deployment target, or active feature flags
> - **Conditional project rules**: which test command applies to the file just edited, which directories are read-only in this worktree
> - **External data**: open issues assigned to you, recent CI results, content fetched from an internal service
>
> **For instructions that never change, prefer CLAUDE.md. It loads without
> running a script and is the standard place for static project conventions.**

→ A STATIC "use mise tasks" directive belongs in CLAUDE.md/AGENTS.md, not a
per-turn UserPromptSubmit additionalContext injection. `additionalContext` is
sanctioned for DYNAMIC/CONDITIONAL context ("which test command applies to the
file just edited" — a contextual nudge), not standing conventions.

## Common fields (verbatim highlights)

- `if`: permission-rule syntax (`"Bash(git *)"`), evaluated ONLY on tool events
  (PreToolUse, PostToolUse, PostToolUseFailure, PermissionRequest,
  PermissionDenied). "The filter also fails open ... Because the `if` filter is
  best-effort, **use the permission system rather than a hook to enforce a hard
  allow or deny.**"
- `once`: "Only honored for hooks declared in skill frontmatter; ignored in
  settings files and agent frontmatter." → not usable from settings.json.
- `timeout`: UserPromptSubmit lowers command default to 30s.

## Exit-code semantics (verbatim)

| Event | Can block? | Exit 2 |
|---|---|---|
| PreToolUse | Yes | Blocks the tool call |
| UserPromptSubmit | Yes | **Blocks prompt processing and erases the prompt** |
| PostToolUse | No | Shows stderr to Claude; tool already ran |
| PostToolUseFailure | No | Shows stderr to Claude; tool already failed |

> For most hook events, only exit code 2 blocks... Claude Code treats exit code
> 1 as a non-blocking error and proceeds... **If your hook is meant to enforce a
> policy, use `exit 2`.**

Confirms: an exit-2 UserPromptSubmit hook ERASES the prompt (my advisory
directive must never exit non-zero → validates the fail-open wrapper design).

## Hook types (verbatim)

`type`: `"command"`, `"http"`, `"mcp_tool"`, `"prompt"`, `"agent"`. prompt/agent
return a yes/no DECISION via an LLM call (default fast model) — they are
evaluators, not context injectors.

## Implications for our design (pre-synthesis)

1. **Static directive → CLAUDE.md/AGENTS.md, not per-turn UserPromptSubmit.**
   The doc explicitly routes static conventions to memory files.
2. **Hard enforcement → permission system / PreToolUse deny**, not a soft hook.
   We already have the PreToolUse deny guard (hook_guard.py) — the doc endorses
   this class for enforcement.
3. **PostToolUse additionalContext is doc-sanctioned when CONTEXTUAL** ("which
   test command applies to the file just edited"). A generic static nudge on
   every command is weaker than a targeted "this command has mise task X".
4. `prompt`/`agent` hooks can't inject reminders (decision-only) → not a fit for
   the nudge/directive.

## GitHub repos touched

_None._ (Product documentation only: code.claude.com/docs.)
