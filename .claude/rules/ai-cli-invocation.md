# AI CLI Invocation Policy

> **EAGER on purpose** — behaviour-triggered, so no glob predicts it
> (`md-size-budgets.md` § "the trigger test"). While it was scoped it could only
> fire *after* the mistake, and did. Archaeology:
> `docs/rules-evidence/ai-cli-invocation.md`.

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

**The patterns above ARE the reference — there is no script to consult.** When a
pattern here looks wrong, **re-probe the CLI itself** (`codex exec --help`,
`gemini --help`) rather than hunting for a canonical script; these flags change
between releases, which is how the wrong forms got documented in the first
place. (This section once pointed at a file that does not exist in this repo —
control arm and detail: `docs/rules-evidence/ai-cli-invocation.md`.)
