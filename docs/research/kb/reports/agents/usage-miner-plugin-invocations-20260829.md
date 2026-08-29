# usage-miner — skill/agent invocation counts across 310 transcripts (2026-08-29)

Agent: `general-purpose` (sonnet). Read-only. Verbatim report below the brief.

## Brief (what was asked)

Measure which Claude Code skills and agents have ACTUALLY been invoked in this
project by mining `~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/*.jsonl`
(plus the knowledge-base sibling, reported separately). Count two mechanisms
separately: `Skill` tool_use `input.skill` (plus slash-command text), and `Agent`
tool_use `input.subagent_type`. Explicitly warned: transcript filenames are
`<uuid>.jsonl` — do NOT glob `agent-*.jsonl`, which matches nothing and yields a
false "no transcripts". Required a control arm before trusting any zero (named
four known-used positives), the file count and date range, a real JSON parse
rather than grep, incremental writes to `.agent/notepad.md`, and a **rollup by
plugin prefix** as the actual deliverable.

## Report (verbatim)

> **Files scanned:** dotfiles 137 files (2026-07-16 → 2026-08-29, 118,996 lines), KB 173 files (2026-07-27 → 2026-08-29, 253,267 lines). 0 malformed lines.
>
> **Control arm** (before trusting any 0-count): all four positive controls non-zero.
>
> | Control | dotfiles | KB |
> |---|---|---|
> | Skill `fable-orchestrator:orchestration` | 6 | 17 |
> | Skill `claude-api` | 2 | 4 |
> | Agent `fable-orchestrator:fable-advisor` | 6 | 15 |
> | Agent `fable-orchestrator:codex-reviewer` | 4 | 158 |
>
> Also caught my own bug via the control arm: first pass on slash-command extraction returned 0 everywhere, but raw grep found `command-name` in 87 dotfiles files — turned out `message.content` is a plain string (not a block list) for user slash-invocations. Fixed.
>
> **Zero-invocation candidates for disabling** (never fired via Skill or Agent tool_use in 310 combined transcripts): `firecrawl`, `hookify`, `commit-commands`, `context7`, `exa`, `claude-md-management`, `astral`, `aggregated-research`, `claude-code-setup`. `codex` plugin is 1 total call (KB, `codex:codex-rescue` agent) — borderline.
>
> ### Plugin rollup (Skill + Agent tool_use combined; excludes CLI slash noise)
>
> | Plugin | dotfiles | KB | Total |
> |---|---|---|---|
> | **fable-orchestrator** | 33 | 297 | **330** |
> | **mattpocock-skills** | 30 | 26 | **56** |
> | antigravity | 2 | 20 | 22 |
> | skill-creator | 3 | 6 | 9 |
> | eli5 | 2 | 6 | 8 |
> | ponytail | 2 | 5 | 7 |
> | builder-skills | 5 | 0 | 5 |
> | i-have-adhd | 2 | 3 | 5 |
> | last30days | 1 | 1 | 2 |
> | codex | 0 | 1 | 1 |
> | pr-review-toolkit | 0 | 1 | 1 |
> | firecrawl / hookify / commit-commands / context7 / exa / claude-md-management / astral / aggregated-research / claude-code-setup | 0 | 0 | **0** |
> | unprefixed (project skills + built-in agent types) | 180 | 511 | 691 |
>
> **Roster coverage:** 128 roster entries checked. Zero in dotfiles: 108/128. Zero in KB: 105/128.
>
> **Top agents — dotfiles:** general-purpose 106, Explore 11, claude-code-expert 11, codex-implementer 9, premise-verifier 8, fable-advisor 6, staleness-auditor 5, codex-reviewer 4, proto-stop-blocker 4, proto-memory 3, adversarial-critic 1, antigravity-delegate 1.
>
> **Top agents — KB:** codex-reviewer 158, general-purpose 144, codex-implementer 69, premise-verifier 36, Explore 28, fable-advisor 15, antigravity-delegate 11, kb-adversarial-verifier 10, kb-advisor 8, kb-tool-researcher 8.
>
> Never invoked in either repo: `dockerfile-reviewer`, `statusline-setup`, `fable-orchestrator:grok-implementer`, `fable-orchestrator:grok-researcher`, `hookify:conversation-analyzer`.
>
> **Caveat (the agent's own):** this is invocation-only. A skill/agent with 0 calls could still be providing passive value (e.g. a hookify rule firing without an explicit skill invocation, or `astral:ruff`/`astral:ty` guidance being read but not tool-invoked) — I did not check hook-fire logs, only Skill/Agent tool_use + slash commands, per the brief.

## Disposition + the two caveats I resolved before acting

The passive-value caveat was load-bearing, so both plausible false positives were
checked rather than trusted:

- **`hookify`** — verified NO hookify rules exist and no hookify wiring in either
  `settings.json`. The 0 is real.
- **`astral`** — `ruff`/`ty` appear 28× in `hk.pkl`, but the plugin ships guidance
  SKILLS; the binaries are mise-pinned and independent. Confirmed by `mise run
  lint` rc=0 after disabling.

Acted on in PR #812: disabled the nine zero-use plugins plus `builder-skills`
(5 invocations for 3,864 chars — worst ratio among kept plugins, zero uses in KB).
Listing 45,294 → ~32,438 chars, under the 34,000 ceiling.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the plugin config trimmed.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — second transcript corpus.
