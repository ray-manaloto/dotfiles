# Stream 2 — Claude Code enforcement alternatives (cited)

Agent: claude-code-guide. Verbatim report below (findings-bearing; persisted at
receipt per agent-report-persistence.md).

## Verdict summary

Ranked recommendation for "use mise tasks, not one-off shell commands":

| Layer | Mechanism | Enforcement | Context cost | Verdict |
|---|---|---|---|---|
| Hard enforcement | **PreToolUse hook** | HARD-BLOCK (exit 2 / permissionDecision deny) | ~50 tok if blocking | ✅ PRIMARY |
| Guidance | **`.claude/rules/` path-scoped + CLAUDE.md** | SOFT-STEER | ~200 tok | ✅ SUPPORTING |
| Fallback | **permission deny rules** | HARD-BLOCK | 0 | ✅ OPTIONAL |
| — | Skills | SOFT-STEER | ~100 tok | ❌ can't enforce |
| — | CLAUDE.md alone | SOFT-STEER | ~200 tok | ❌ insufficient |
| — | Subagents | HARD only inside subagent | isolated | ❌ main session unbound |
| — | Output styles | SOFT-STEER | ~200 tok | ❌ not for policy |
| — | **UserPromptSubmit re-injection** | SOFT-STEER | per-turn cost | ❌ anti-pattern (below) |

## Load-bearing Anthropic quotes (verbatim from agent)

memory.md:
> "Claude treats them [CLAUDE.md] as context, not enforced configuration. To
> block an action regardless of what Claude decides, use a PreToolUse hook
> instead."

> "If the instruction is something that must run at a specific point, such as
> before every commit or after each file edit, write it as a hook instead.
> Hooks execute as shell commands at fixed lifecycle events and apply
> regardless of what Claude decides to do."

> "For static, unchanging project rules, prefer CLAUDE.md instead of hooks — it
> loads without running scripts."

> "CLAUDE.md content is delivered as a user message after the system prompt...
> Claude reads it and tries to follow it, but there's no guarantee of strict
> compliance, especially for vague or conflicting instructions." (Debug via
> `/memory`; make instructions specific; remove conflicts.)

hooks-guide.md (PreToolUse):
> "Hooks ... provide deterministic control over Claude Code's behavior, ensuring
> certain actions always happen rather than relying on the LLM to choose to run
> them."

hooks-guide.md (PostToolUse / resume caveat):
> "For mid-session events like PostToolUse ... resuming with --continue or
> --resume replays the saved text rather than re-running the hook for past
> turns, so values like timestamps or commit SHAs become stale on resume."

## Why UserPromptSubmit re-injection is rejected (agent's reasoning)

- Anthropic guidance says static rules → CLAUDE.md, not per-turn hook injection.
- Re-running the hook every turn is costly and "defeats Anthropic's static-rules
  recommendation."
- Same resume-staleness problem as PostToolUse.

## Nuance on permission deny rules

Deny rules are HARD-BLOCK and free, but "too blunt": they can't discriminate
intent (allow `hk run pre-commit` when invoked via `mise run lint`, deny it
raw). That discrimination is exactly what the PreToolUse guard SCRIPT does —
which is why the hook (not a deny rule) is the primary layer. (Our
`hook_guard.py` already does this: denies raw `hk run pre-commit`, redirects to
`mise run lint`.)

## Mapping to our current state

- PreToolUse hard-block guard: ALREADY HAVE (`hook_guard.py`, 11 rules). ✅ the
  endorsed primary layer.
- `.claude/rules/mise-tasks-only.md` + CLAUDE.md/AGENTS.md: ALREADY HAVE. ✅ the
  endorsed supporting layer.
- permission deny rules: partially have (chezmoi apply/update). Could extend.
- UserPromptSubmit directive (built this session): ❌ per this evidence.
- PostToolUse generic nudge (built this session): ❌ as a STATIC reminder; only
  legitimate if made CONTEXTUAL.

## Sources

- <https://code.claude.com/docs/en/memory.md>
- <https://code.claude.com/docs/en/memory.md#troubleshoot-memory-issues>
- <https://code.claude.com/docs/en/settings.md>
- <https://code.claude.com/docs/en/hooks-guide.md>
- <https://code.claude.com/docs/en/skills.md>
- <https://code.claude.com/docs/en/sub-agents.md>
- <https://code.claude.com/docs/en/output-styles.md>

## GitHub repos touched

_None._ (Claude Code product documentation only.)
