# AI CLI Invocation Policy

> **This rule is deliberately EAGER (no `paths:` frontmatter).** It guards an
> *action* — invoking an external AI CLI from Bash — not a file. Path-scoped
> rules "trigger when Claude **reads** files matching the pattern", and no glob
> predicts the moment you are about to shell out to `codex`. It was scoped to
> `AGENTS.md`/`.claude/**`/`scripts/**`/`.omc/**` until 2026-07-20, which meant
> it could only fire by accident: a session invoked `codex exec "prompt"`
> positionally (the documented-wrong form), wasted a probe on the resulting
> stdin hang, and only saw this rule *afterwards*, because it happened to write
> into `.omc/**`. That is the same defect `zero-skip-policy` and
> `clean-git-state` were un-scoped for on 2026-07-15. See
> `.claude/rules/md-size-budgets.md` § "Scoping: the trigger test" — this rule
> is **behaviour-triggered**, and behaviour-triggered rules stay eager.

When calling external AI CLIs (Codex, Gemini, OpenCode) from Bash, you MUST use the
correct invocation patterns. Incorrect flags waste tokens and cause silent failures.

## Codex CLI

```bash
# Research/debate (no tool execution, fast):
echo "prompt" | codex exec --ephemeral --sandbox read-only -

# Implementation (with tool execution):
echo "prompt" | codex exec --full-auto --sandbox workspace-write -

# With reasoning effort override:
echo "prompt" | codex exec --ephemeral -c model_reasoning_effort="high" -

# Capture to file (for background use):
cat prompt.md | codex exec --ephemeral -o /tmp/result.md -
```

**WRONG patterns (will silently fail):**
- `codex -p "prompt"` — `-p` is `--profile`, not prompt
- `codex exec "prompt"` — positional arg without `-` stdin flag
- `codex --full-context` — flag does not exist

The `-` at the end means "read prompt from stdin." Always pipe prompts via stdin
to avoid ARG_MAX limits on large prompts.

## Gemini CLI

```bash
# Research/debate (headless, no approval prompts):
echo "prompt" | gemini -o text --approval-mode yolo -p ""

# On macOS without API key (avoids Keychain prompts):
echo "prompt" | env GEMINI_FORCE_FILE_STORAGE=true gemini -o text --approval-mode yolo -p ""
```

**WRONG patterns:**
- `gemini -p "prompt"` — `-p ""` triggers headless mode, prompt comes via stdin
- `gemini "prompt"` — no headless flag, will hang waiting for interactive input

## OpenCode CLI

```bash
# Research:
echo "prompt" | opencode run

# With specific model:
echo "prompt" | opencode run -m provider/model
```

## Background Mode Warning

Claude Code's `run_in_background` does NOT reliably capture streaming stdout from
Codex or Gemini. For background tasks, use:
- `codex exec -o /tmp/result.md` (file-based capture)
- Or run foreground with adequate timeout

## Reference

The octopus `orchestrate.sh` (lib/dispatch.sh + lib/spawn.sh) has the canonical
invocation patterns. When in doubt, check `get_agent_command()` in dispatch.sh.
