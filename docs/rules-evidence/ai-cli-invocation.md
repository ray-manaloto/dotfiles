# Evidence — `ai-cli-invocation`

Archaeology behind `.claude/rules/ai-cli-invocation.md`. Extracted so the eager
copy is just the invocation patterns, and this file carries why the rule is
un-scoped and why it no longer points at a canonical script.

## Why the rule is EAGER, and the accident that proved it

The rule guards an *action* — shelling out to an external AI CLI — not a file.
Path-scoped rules "trigger when Claude **reads** files matching the pattern", and
no glob predicts the moment you are about to run `codex`.

It was scoped to `AGENTS.md` / `.claude/**` / `scripts/**` / `.agent/**` until
2026-07-20, which meant **it could only fire by accident**. And it did: a session
invoked `codex exec "prompt"` positionally — the documented-wrong form — wasted a
probe on the resulting stdin hang, and only saw this rule *afterwards*, because
it happened to write into `.agent/**`.

That is the same defect `zero-skip-policy` and `clean-git-state` were un-scoped
for on 2026-07-15. See `md-size-budgets.md` § "Scoping: the trigger test":
behaviour-triggered rules stay eager.

## Why there is no canonical script to consult

The "Reference" section used to point at the octopus `orchestrate.sh` /
`get_agent_command()`.

**That file does not exist in this repo.** Control-armed: `find . -name
orchestrate.sh` → **0**, while `find . -maxdepth 1 -name hk-common.pkl` → **1**,
so the probe discriminates and the zero is a real negative. It lives only inside
the `octo@nyldn-plugins` plugin cache, which is `false` in **both**
`.claude/settings.json` and `~/.claude/settings.json`, and may vanish on plugin
GC. A reader could not have acted on the pointer.

Hence the rule's standing instruction: when a pattern looks wrong, **re-probe the
CLI itself** (`codex exec --help`, `gemini --help`) rather than hunting for a
canonical script. These flags change between releases — which is exactly how the
wrong forms got documented in the first place.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the rule,
  `.claude/settings.json`.

_Named in the extracted text but **not** resolved during this extraction: the
`octo@nyldn-plugins` plugin and the Codex / Gemini / OpenCode CLIs. The flag
forms in the rule are dated — re-probe `--help` before trusting one._

## 2026-09-09 — audit refactor

**Findings applied:** `rule-ai-cli-invocation-1` through `-7`.

**Native/current anchors re-read:** `.claude/agents/codex-sol-operator.md:73-79`
records the sandbox conflict and missing `--full-auto`; Claude Code
`hooks.md:1773` covers headless behavior. (An earlier draft also cited
`hooks.md:664` for "background/task behavior"; that line is about
subagent-FRONTMATTER hooks and their `Stop`->`SubagentStop` conversion, so it
is dropped rather than re-captioned.) The
newer listing controls are from the saved verbatim
`docs/research/kb/raw/claude-code-changelog-2.1.258-2.1.266.md:67-71` because
the KB corpus predates 2.1.261. The promoted excerpt is tracked so a fresh clone
can verify those 2.1.261-era claims.

**Live Codex probe (0.152.1):** `mise exec -- codex exec --help` exited 0 and
printed `Usage: codex exec [OPTIONS] [PROMPT]`; it says missing/`-` prompts use
stdin and piped stdin is appended to a positional prompt. Positive arm:
`grep -c workspace-write` = **2**. Negative arm: `grep -c -- --full-auto` =
**0**. `-p, --profile` remains the profile flag. Running both approval modes
exited 2 with:

```text
error: the argument '--approve-for-me' cannot be used with '--sandbox <SANDBOX_MODE>'
```

**Live companion probes:** bare `agy --version` resolved stale **1.1.12**;
`mise exec -- agy --version` resolved pinned **1.1.24**. Pinned `agy --help`
exited 0 and showed `--print` plus `--output-format text|json|stream-json`.
`gemini --help` exited 0 and said it defaults interactive and uses
`-p/--prompt` for headless mode. `opencode run --help` exited 0 and showed
`--format json`, `-m/--model`, and `-p/--password`.

**Motivating defect still caught:** the canonical block now uses only flags
proved by the pinned CLIs, while the standing rule still requires positive and
negative help probes before a copied invocation can silently waste a lane.

## A lane invented an environment variable (2026-09-10)

The A-2 draft's "Background results" section credited Claude Code 2.1.261 with
three environment variables. Probed against the offline corpus
(`$CC` = the knowledge-base `agent-harness-docs/docs/claude-code` tree), same
command shape for each:

| Cited as new in 2.1.261 | Corpus hits | Reality |
|---|---|---|
| `SLASH_COMMAND_TOOL_CHAR_BUDGET` | 2 files | Real, but an explicitly **legacy** name for the skill-listing budget (`env-vars.md:466`); nothing to do with 2.1.261 |
| `ENABLE_TOOL_SEARCH` | 8 files | Real, but governs **MCP tool search** (`agent-sdk__tool-search.md:32`), not listing or background output |
| `SLASH_COMMAND_TOOL_TOKEN_BUDGET` | **0 files** | **Does not exist** |

**Control arms.** The two real names returning hits on the identical command is
the positive arm — the probe can find variables of this shape. A freshly-minted nonce, invented for that run,
returned 0 — the negative arm. ⚠️ **The literal is deliberately not written
here.** An earlier draft published it, which is precisely what
`probes-need-a-control-arm.md` rule 3 forbids: a control string committed to the
corpus now MATCHES, so the next run's "absent" arm returns hits and the probe
silently stops discriminating. Mint a new one every time. All three names are
also absent from the tracked saved source
`docs/research/kb/raw/claude-code-changelog-2.1.258-2.1.266.md`, whose own
`2.1.261` string returns 1 hit — so that probe discriminates too.

None of the three is about background results, which was the section's subject.
The whole clause was removed rather than corrected.

**The durable lesson:** a plausible-looking `SCREAMING_SNAKE_CASE` name is the
cheapest thing for a lane to invent, and it survives review because it *reads*
like the two real names beside it. Grep a variable before citing it; the cost is
one command.
