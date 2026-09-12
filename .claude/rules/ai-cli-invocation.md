# AI CLI Invocation Policy

> **EAGER on purpose** — behavior-triggered, so no glob predicts it. While
> scoped, this rule loaded only after the wrong invocation. Archaeology:
> `docs/rules-evidence/ai-cli-invocation.md`.

Use the pinned CLI through mise and re-probe its help before copying flags.
Wrong flags are version-sensitive and may waste a lane before anyone notices.
Prefer `mise run codex-lane` for repository orchestration; use the canonical
direct forms below only when the task genuinely needs a raw CLI call.

## Canonical invocation block

```bash
# Codex research: stdin prompt, ephemeral state, read-only sandbox
printf '%s\n' "prompt" | mise exec -- codex exec --ephemeral -s read-only -

# Codex implementation: workspace writes and explicit reasoning effort
printf '%s\n' "prompt" | mise exec -- codex exec --ephemeral \
  -s workspace-write -c model_reasoning_effort='"xhigh"' -

# Gemini/Antigravity pinned lane: headless text output
printf '%s\n' "prompt" | mise exec -- agy --print --output-format text

# OpenCode research: stdin prompt and structured event output
printf '%s\n' "prompt" | mise exec -- opencode run --format json
```

This is the only hand-kept argv block. Agent definitions, workflows, and task
documentation point here or to `mise run codex-lane`; do not duplicate a flag
recipe that can drift independently.

## Codex facts at 0.152.1

- `codex exec --full-auto` does not exist. `codex exec --help` contains zero
  `--full-auto` matches and two `workspace-write` matches.
- `-s workspace-write` is the documented writable sandbox form.
- `--approve-for-me` is mutually exclusive with `--sandbox`; combining them
  exits 2 with the parser error recorded in the evidence note.
- `-p` is `--profile`, not a prompt flag.
- A positional `[PROMPT]` is valid. With no prompt, or with `-`, instructions
  come from stdin. If stdin is piped and a positional prompt is also supplied,
  stdin is appended as a `<stdin>` block. Prefer stdin for large prompts and
  unambiguous composition, not because positional prompts fail.
- `--full-context` does not exist.

The operator-specific control plane and error history remain in
`.claude/agents/codex-sol-operator.md`; this rule owns only the shared invocation
contract.

## Gemini and OpenCode traps

Use the pinned `agy`/Antigravity path through `mise exec -- agy`. A stale user
installation can exist at `~/.local/bin/agy`, so keep the explicit `mise exec`
form rather than relying on lookup order.

⚠️ **Do not restate this as "a bare `agy` resolves the stale copy" — measured
2026-09-10, it does not.** Bare `agy --version` -> **1.1.24** (mise's install
dir precedes `~/.local/bin` on this PATH) while `~/.local/bin/agy --version` ->
**1.1.12**, so the stale copy is real but is NOT what runs here. `which -a agy`
is the arm that settles it; PATH order is a property of the machine, not of the
tool, so assert the explicit form and let the probe speak for the order. For raw
Gemini, `gemini "prompt"` remains interactive and can hang; `-p`/`--prompt`
selects headless mode and piped stdin is appended to that prompt.

OpenCode accepts positional messages and `-m provider/model`; its `-p` means
`--password`, not prompt. Use `--format json` when a caller needs machine-
readable events.

## Background results

Do not assume streaming stdout is the durable result of a background task.
Recover background output by `Read`ing the task's output file path — the
`TaskOutput` tool is **deprecated** in favour of exactly that
(`$CC/agent-sdk__python.md:3022`, and the changelog entry at
`$CC/changelog.md:3722`) — or have Codex write its final message with
`-o <path>`. Nothing about listing or context pressure
belongs in this file: it is a user/session concern, and no environment variable
is a reason to invent new argv here.

⚠️ An earlier draft of this section credited Claude Code 2.1.261 with three
environment variables. Two exist but neither is new nor about background
output — `SLASH_COMMAND_TOOL_CHAR_BUDGET` is an explicitly *legacy* name for
the skill-listing budget (`$CC/env-vars.md:466`) and `ENABLE_TOOL_SEARCH`
governs MCP tool search (`$CC/agent-sdk__tool-search.md:32`). The third,
`SLASH_COMMAND_TOOL_TOKEN_BUDGET`, **does not exist** — 0 hits across the
corpus while the other two return hits on the same command. All three are
absent from the saved 2.1.261 changelog. A plausible-looking variable name is
the cheapest thing for a lane to invent; grep it before citing it.

## Re-probe rule

The invariant is **wrong flags fail or misbehave silently enough to waste the
lane**. Before changing any invocation, run the pinned CLI's own help:

```text
mise exec -- codex exec --help
mise exec -- agy --help
mise exec -- opencode run --help
```

Record positive and negative arms in the evidence note. Help output, not this
file's age, decides whether a flag remains valid.

## Applies to

All direct Codex, Gemini/Antigravity, and OpenCode CLI calls from this repo.

## See also

- `.claude/agents/codex-sol-operator.md` — operational lane policy.
- `mise.toml` — pinned tools and `codex-lane` task.
- `docs/rules-evidence/ai-cli-invocation.md` — live probe output.
- `.claude/rules/md-size-budgets.md` — why this rule remains eager.
