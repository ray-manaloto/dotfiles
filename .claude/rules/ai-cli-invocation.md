# AI CLI Invocation Policy

> **EAGER on purpose** — behavior-triggered, so no glob predicts it. While
> scoped, this rule loaded only after the wrong invocation. Archaeology:
> `docs/rules-evidence/ai-cli-invocation.md`.

Invoke every AI CLI through `mise exec --` and re-probe its help before copying flags. For codex that
resolves the host's NATIVE install (root `mise.toml` disables the npm pin), not a stale PATH entry.
Wrong flags are version-sensitive and may waste a lane before anyone notices.
Team work goes through `mise run sdlc-team`; single-role lanes use the `codex-{sol,astra}-*`
wrappers; `mise run codex-lane` is only the DAG review-node producer. The class fix that
replaces all three with one launcher is a Phase 11 item. Use the direct forms below only
when a task genuinely needs a raw CLI call.

## Canonical invocation block

```bash
# Codex research: stdin prompt, persisted rollout, read-only sandbox
printf '%s\n' "prompt" | mise exec -- codex exec -s read-only -

# Codex implementation: machine sandbox (no -s) and explicit reasoning effort
printf '%s\n' "prompt" | mise exec -- codex exec \
  -c model_reasoning_effort='"xhigh"' -

# Gemini/Antigravity pinned lane: headless text output
printf '%s\n' "prompt" | mise exec -- agy --print --output-format text

# OpenCode research: stdin prompt and structured event output
printf '%s\n' "prompt" | mise exec -- opencode run --format json
```

⚠️ **Never `--ephemeral`, on ANY lane** (Ray: knowledge-base 2026-09-01, dotfiles 2026-09-15;
re-applied 2026-09-23 — history in `docs/research/kb/reports/agents/codex-flag-decisions-history-2026-09-23.md`).
It means "Run without persisting session files to disk": every spawn dies with `collab spawn failed:
no thread with id` (measured 2026-09-16: 3 failures / 0 session files with it, 0 / 2 without), and
the run leaves no rollout, so agentsview and any audit of its model, effort or sandbox see nothing.
A per-lane "keep it where the lane does not delegate" exception was rejected on 2026-09-01 as a
policy that drifts. Still in code, tracked by the Phase 11 codex class fix: `codex_lane.py` passes it.
Sandbox: `sdlc-team` passes no `-s` (the machine's `danger-full-access` is the approved posture, and
`workspace-write` also cuts the network, #1039/#1142); the implementer/operator wrappers pin the same
`danger-full-access` explicitly; advisory wrappers keep `--sandbox read-only` — the only thing that stops them writing.

This is the canonical argv block. Until the class fix, the 12 codex wrappers still carry their own
(sonnet, background launch, `$LOG.rc` completion file); keep them consistent with this block.

## Codex facts (probed at 0.152.1; the host now runs native 0.156.x — re-probe before relying)

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

`which -a agy` shows which copy PATH order selects on this machine; keep the
explicit form regardless. For raw Gemini, `gemini "prompt"` remains
interactive and can hang; `-p`/`--prompt` selects headless mode and piped
stdin is appended to that prompt.

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

A plausible-looking environment-variable name is the cheapest thing for a lane
to invent; grep the `$CC/` corpus for it before citing it.

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
