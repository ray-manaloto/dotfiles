# /code-review medium — doc/agent branch `7f5b2d21` (2026-09-28)

Verbatim fork report. Coordinator disposition: finding 1 CONFIRMED (`git grep 78-85` hit the sol + astra TOML bodies) and
fixed in the sol TOML (astra regenerated; the untracked Codex-app export is #1425); the md↔toml drift CLASS is a PLAN
row in `task_plan.md`. Finding 2 CONFIRMED against `ai-cli-invocation.md:46` (0.152.1) and re-probed live at codex
0.158.0 (`--full-auto` rc=2, control `--sandbox` rc=0); the operator now reads "0.152.1 and 0.158.0".

---

I found 2 real issues in 7f5b2d21. There is no ReportFindings tool in this session, so the findings are only in this reply. Most of the diff is documentation, so both findings are about wrong or inconsistent guidance, not runtime bugs.

**Findings**

1. `.codex/agents/codex-sol-claude-code-expert.toml:71` (also `.codex/agents/codex-astra-claude-code-expert.toml:72` and `.codex/agents/claude-code-expert.toml:82`) — **medium, fix incomplete.** The commit says it removed the "volatile token figure", but it only changed the `.claude/agents/*.md` wrappers. These three codex TOML bodies still say "~78-85 k per agent spawned". The TOML `developer_instructions` is what the codex lanes actually read, so they keep getting the figure the mattpocock Standards review asked to drop. The Claude-side and codex-side copies of the same role now disagree. `codex-lane-mirror --check` passing doesn't catch this: it seems to compare sol with astra, not the Markdown wrappers with the TOML bodies.

2. `.claude/agents/codex-sol-operator.md:137` (also `.claude/agents/codex-astra-operator.md:139`) — **low.** The new version condition says `--full-auto` was probed "at codex 0.152.0 and 0.158.0", and cites `.claude/rules/ai-cli-invocation.md` as the source. That rule says the probe ran at **0.152.1** (`ai-cli-invocation.md:46`). So the fact that was just made version-accurate now contradicts its own citation. Anyone re-checking it will find two different probe versions for the same claim. The host does currently run `codex-cli 0.158.0`, which makes the 0.158.0 half believable, but I did not re-run the `--full-auto` probe myself.

**Checked and correct**

- **Guard probes:** I replayed all six `=`-separator commands through `bash scripts/pretooluse-guard.sh`. The first three were denied and the last three printed 0 bytes, as the verify skill says.
- **graphify hook script:** `scripts/graphify-hook-guard.sh` is mode 644, and `.claude/settings.json` runs it as `bash <path>`, so that gotcha is accurate.
- **Hook selfcheck command:** `hook selfcheck` is the exact command `ship` runs (`python/src/dotfiles_setup/pr.py:341`), and its OK line matches `hook_selfcheck.py:820`.
- **Other CLI facts:** `verify-promote-eligibility --image-ref` exists (`main.py:1462-1471`), and so does `sync --check`.
- **Referenced reports:** the brief and review files the skills point to all exist under `docs/research/kb/reports/agents/`.

## GitHub repos touched

_None._
