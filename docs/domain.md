# Domain Docs

How the mattpocock engineering skills should consume this repo's domain documentation.
Adapted from the `setup-matt-pocock-skills` seed.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root — the glossary.
- **`docs/adr/`** — but read `docs/adr/README.md` first: **this repo's ADRs live in
  `.claude/rules/*.md`**, not here. See below.
- There is **no `CONTEXT-MAP.md`** — this is a single-context repo (no monorepo signals: no
  `package.json`, no `pnpm-workspace.yaml`, no `packages/*/src`).

If a file doesn't exist, **proceed silently.** Don't flag its absence or suggest creating it.

## ⚠️ Our ADRs are `.claude/rules/*.md`

The seed template assumes `docs/adr/NNNN-*.md`. This repo already had that role filled before the
skills arrived: **each file in `.claude/rules/` is an ADR** — a decision plus a *"Why this rule
exists"* section citing the incident that produced it, plus a "See also" graph.

So when a skill says *"read ADRs that touch the area you're about to work in"*, read
**`.claude/rules/`**. `docs/adr/` holds only decisions that are genuinely domain-shaped rather than
agent-behaviour-shaped; it is expected to stay small.

Worked examples of rules-as-ADRs:

| Decision | Rule file | The incident |
|---|---|---|
| Bound every long-running command | `long-running-command-hangs.md` | a 7-hour hk hang at 0% CPU, 2026-06-29 |
| Prefer native tool features over custom code | `use-tool-builtins.md` | ~20 lines of custom chezmoi container-detection that `chezmoi.os` already did |
| Canonical mise tasks over one-off commands | `mise-tasks-only.md` | the whole ship/land guard programme |
| Never trust a piped tail's exit code | *(memory)* `feedback_pipe_kills_exit_code` | a killed hk run reporting exit 0 |

## Use the glossary's vocabulary

When output names a domain concept (an issue title, a refactor proposal, a hypothesis, a test name),
use the term as defined in `CONTEXT.md`. Don't drift to synonyms it avoids.

If a concept isn't in the glossary, that's a signal — either you're inventing language the project
doesn't use (reconsider), or there's a real gap (note it).

## Flag ADR conflicts

If output contradicts an existing rule, surface it rather than silently overriding:

> _Contradicts `.claude/rules/zero-bash-logic.md` — but worth reopening because…_

This matters more here than in a typical repo: several rules are **machine-enforced** (hk steps,
the PreToolUse guard, verification contracts). Contradicting one doesn't just disagree with a
document — it fails a gate.
