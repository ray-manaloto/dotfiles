# ADRs — mostly not here

The mattpocock engineering skills look for `docs/adr/`. This file exists so they find a real answer
instead of an empty directory.

## The ADRs are `.claude/rules/*.md`

This repo filled the ADR role before those skills arrived. Every file in `.claude/rules/` is a
decision record: the decision, a **"Why this rule exists"** section naming the incident that forced
it, what it applies to, and a "See also" graph. That is an ADR in everything but filename.

Duplicating them here would create a second decision store to keep in sync — and several rules are
**machine-enforced** (hk steps, the PreToolUse guard, `python/verification/suites.toml` contracts),
so the rule file is the one that has teeth. A copy under `docs/adr/` would be the copy that rots.

**So: read `.claude/rules/` for decisions.** `CONTEXT.md` is the glossary; `docs/domain.md` explains
the consumption order.

## What DOES belong here

Decisions that are **domain-shaped rather than agent-behaviour-shaped** — a choice about the
devcontainer/image/CI domain that isn't a rule for how an agent should work, and therefore has no
natural home in `.claude/rules/`.

Expect this directory to stay small. One decision lives here today:

| ADR | Decision |
|---|---|
| [`0001-hk-hooks-do-not-run-in-ci.md`](0001-hk-hooks-do-not-run-in-ci.md) | CI installs git hooks as a side effect of installing tools; they must be skipped, not satisfied |

## Numbering

`NNNN-kebab-title.md`, zero-padded, monotonic. Never renumber — a stale link is worse than a gap.
