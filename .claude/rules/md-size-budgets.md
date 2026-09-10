---
paths:
  - "hk.pkl"
  - "**/CLAUDE.md"
  - "**/AGENTS.md"
  - ".claude/rules/*.md"
  - ".claude/skills/**/SKILL.md"
---

# Markdown Size Budgets: By Load Class, With Provenance

Instruction budgets differ by load class because cost depends on when bytes
enter context. `kb-setup md-budget` (hk step `md_size_budget`) enforces the
table below using the SHA-pinned implementation from the knowledge-base repo.
This rule is itself `paths:`-scoped, so it receives the `rule_scoped` budget.

## Anthropic's current guidance and real cliffs

Claude Code's memory documentation targets project instructions below 200
lines because larger files consume context and reduce adherence. That is a soft
quality gradient, not this repository's enforcement source.

A `CLAUDE.md` up to 4 MiB loads in full; a larger one is **skipped in full**,
not truncated. The 200-line/25 KiB truncation is for auto-memory `MEMORY.md`,
not `CLAUDE.md`. These are native runtime behaviors; this repo's much smaller
budgets remain preventive backstops.

Skill listing has a different, partly non-deterministic cliff:

- `skillListingMaxDescChars` defaults to 1,536 characters across the combined
  `description` + `when_to_use` text. It is a setting, not a hard per-file cap.
- `skillListingBudgetFraction` defaults to 0.01 (1% of context). On overflow,
  names remain but descriptions are dropped least-used-first, so a skill can
  become undiscoverable without violating its file budget.
- `skillOverrides` with `name-only` is the native way to recover listing space.

This repository deliberately sets none of those three controls. Inspect their
actual effect with `/context`, not a guessed per-file threshold.

## Why this rule exists: a true number assigned to the wrong vendor

The predecessor `claude_md_size_limit` enforced **200 lines and 12,000 bytes**
for every `CLAUDE.md`/`AGENTS.md`, calling both Claude Code memory limits.
Twelve thousand is instead **Windsurf's** rule:

> Workspace `.devin/rules/*.md` … **Limited to 12,000 characters per file.**
> `AGENTS.md` — Any directory in your workspace — **Processed by the same Rules
> engine**.
> — <https://docs.windsurf.com/windsurf/cascade/memories>

`mise run lint-docs` enforces that vendor rule as agnix AGM-003 for the
`AGENTS.md` files Windsurf reads. `md_size_budget` does not duplicate it or
misapply it to Claude-only files.

The historical failure was provenance loss:

1. `1f05365` created a 200-line gate with the correct source.
2. `99a8506` (no longer resolvable in this repo) described an unenforced
   12,000-character limit, likely copied from
   agnix without its vendor bound.
3. `010009d` (also no longer resolvable) changed code to match the prose and
   credited Anthropic.

   ⚠️ Only `1f05365` still resolves (`git cat-file -t` -> commit; the other two
   -> unresolvable, same command, so the probe discriminates). The chain is
   preserved as narrative, not as three followable refs.

The initial correction also overreached: a zero-hit search in Anthropic's
corpus became "not documented anywhere," although the probe never searched
Windsurf. A control arm validates a probe only inside its stated bound. A true
fact must travel with its owner before it becomes an invariant.

## The budgets

| Class | Load semantics | Lines | Bytes |
|---|---|---|---|
| `eager_root` — root `CLAUDE.md` + `@import` closure, `.claude/CLAUDE.md` | loaded at launch | **200** | 24,000 |
| `rule_unscoped` — rules without `paths:` | loaded at launch with project instructions | **200** | 24,000 |
| `nested` — subdirectory `CLAUDE.md` + closure | loads on applicable file reads; reloads that way after `/compact` | **400** | 32,000 |
| `rule_scoped` — rules with `paths:` | loads on matching file reads; reloads that way after `/compact` | **400** | 32,000 |
| `skill` — `.claude/skills/**/SKILL.md` | invocation/relevance only; listing governed separately | **500** | 32,000 |

The byte ceilings are self-imposed anti-gaming backstops, not Anthropic limits.
Lines bind first. The constants live in the knowledge-base
`kb_setup.md_budget` module; changing them requires a knowledge-base PR, never
a local prose-only edit.

Every `AGENTS.md` also has Windsurf's 12,000-character ceiling through agnix.
When one outgrows it, move reference material to a sibling doc and link it;
do not add Claude-only imports to an agent-agnostic file or its guarded stub.

## Measure both authored bytes and received context

- Run the md-budget gate for deterministic pre-commit line/byte budgets.
- Run `/context`: **Memory files** shows which project instructions actually
  loaded, while **Skills** reports the listing after its budget was applied.
- Use `/doctor` for the listing estimate and largest contributors.
- On Claude Code 2.1.261+, `/skill-doctor` reportedly shows loaded-but-unused skills and
  their context cost. This command is documented in the saved 2.1.261
  changelog because the offline corpus stops before that version.

Interactive measurement supplements the gate: disk bytes cannot reveal a rule
that failed to load or a skill description dropped from the listing.

## Measurement rules

- Budget the complete `@import` closure. Imports organize content but do not
  reduce launch context.
- Replace the import directive with imported content when counting; do not add
  both.
- Only `CLAUDE.md` is a native entry point. An `AGENTS.md` enters Claude Code
  context through its stub import and is counted inside that closure.
- Discount HTML comments only where native docs guarantee stripping. Rules and
  skills pay full price because that behavior is undocumented for them.

## Scoping: the trigger test

Path-scoped rules load when Claude reads matching files. Scope only when the
rule's trigger is genuinely a file read.

- **File-triggered → safe to scope.** `ci-local-parity`; this rule.
- **Behavior-triggered → keep eager.** `zero-skip-policy`, `clean-git-state`,
  `do-not`, `verify-before-advancing`, `clarify-before-acting`, and
  `probes-need-a-control-arm` govern decisions no glob predicts.
- **Creation-triggered → keep eager.** `zero-bash-logic` and
  `agent-artifact-conventions` must act before the new file exists.
- **Behavior-triggered but niche → use a skill.** Relevance/invocation is the
  native lazy-loading mechanism.

A rule's whole `paths:` list shares a budget of **1,000 expanded patterns and
4 MiB**; patterns without braces do not count. An expansion that would exceed
the budget is used literally, braces included, and therefore may match
nothing. That silent absence is the same class of defect scoping is meant to
avoid. Keep brace expansion small and verify loading with `/context`.

The 2026-07-15 failure demonstrated the trigger test: `zero-skip-policy` and
`clean-git-state` were scoped, so both were absent when their listed files were
untouched. The correct response was to restore eager loading and trim evidence,
not to keep a cheap rule absent.

Move archaeology and long probe logs to
`docs/rules-evidence/<rule>.md`; keep the directive, constraints, and one worked
failure eager. That preserves evidence without repeatedly injecting it.

## Applies to

Every tracked `CLAUDE.md`, `AGENTS.md`, `.claude/rules/*.md`, and
`.claude/skills/**/SKILL.md`. Vendored plugin content is out of scope.

## See also

- `docs/rules-evidence/md-size-budgets.md` — 2026-09-09 anchor and probe record.
- `docs/research/runs/research-20260715-md-size-limits/report.md` — original
  multi-vendor audit.
- `kb_setup.md_budget` — knowledge-base-owned enforcer.
- `.claude/rules/probes-need-a-control-arm.md` — bounded-search doctrine.
- `.claude/rules/agent-artifact-conventions.md` — evidence extraction pattern.
