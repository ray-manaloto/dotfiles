# Agent Artifact Conventions: Where Working Files Go

Agent working artifacts live under **`.agent/`** (gitignored, machine-local).
Anything that should survive a clone is **tracked**, and lives under `docs/` —
never in `.agent/`. Do not create ad-hoc directories in either.

> **Renamed from `.omc/` (2026-07-25)** — that tree was named after a plugin
> that is not enabled. `.agent/` was control-armed before adopting, not assumed
> (`.agent/` → 0 hits in Claude Code's docs, `CLAUDE.md` → 439). Archaeology,
> and why the ignore lives in `.gitignore` rather than `.git/info/exclude`:
> `docs/rules-evidence/agent-artifact-conventions.md`.

## Local, gitignored — swept away by `git clean -xdf`

| Path | Purpose |
|------|---------|
| `.agent/state/` | General state (session ids, mode tracking) |
| `.agent/state/sessions/{id}/` | Per-session state |
| `.agent/notepad.md` | Working notepad — findings as you go |
| `.agent/plans/` | Plans + session handoffs (`session-{date}[-letter].md`) |
| `.agent/logs/` | Execution logs, pipeline traces |
| `.agent/command-audit.md` | The SessionEnd one-off-command report |
| `.agent/project-memory.json` | Cross-session project knowledge |
| `.agent/kb/raw/` | Raw fetched sources backing a report |

## Tracked, durable — survives a clone

| Path | Purpose |
|------|---------|
| `docs/specs/` | Design specs and deep-dive/interview output |
| `docs/research/runs/` | Research artifacts: `<run>/report.md` + `<run>/agents/*.md` |
| `docs/research/kb/reports/` | Persisted verbatim agent reports |
| `docs/handoffs/` | Cross-surface session handoffs |
| `docs/adr/` | Domain-shaped decisions (our ADRs are `.claude/rules/*.md`) |
| `docs/rules-evidence/` | Archaeology extracted OUT of an eager rule: one `<rule>.md` per `.claude/rules/<rule>.md` |

**`docs/rules-evidence/` exists to buy back eager context.** Unscoped
`.claude/rules/*.md` are ~88% of the eager corpus and scoping cannot fix that
(`md-size-budgets.md` § "the trigger test"), so the lever is moving case
histories, provenance tables and worked-failure logs into a tracked sibling the
rule links by path. The rule keeps its directive, its operative constraints, and
**one** canonical worked example; nothing leaves git, it just stops being
re-injected every session. Name the file after the rule, one-to-one.

**Promoting is the default for anything an eval, a rule, or a future session
will cite** — the migration found five eager rules citing research that had
never been tracked, so every reader outside this one machine hit a dead link.
A citation to something only you can open is not a citation.

## Two things that must NOT be normalised

1. **Persisted agent reports stay VERBATIM** (`agent-report-persistence.md`).
   `docs/research/runs/**` and `docs/research/kb/**` are therefore excluded
   from every hk builtin in `hk-common.pkl`'s `excludePaths` — running a
   typo-fixer or whitespace normaliser over archived agent output would edit
   the record the rule exists to preserve.
2. **Ingested corpus records what a source SAID**, including paths that have
   since moved. Rewriting it to keep links tidy falsifies provenance. Fix the
   pointer in the authored doc instead.

## Rules

1. **No ad-hoc directories.** Not `.agent/handoffs/`, `.agent/temp/`,
   `.agent/output/`. Map your artifact to the closest path above.
2. **A handoff is a plan** — `.agent/plans/session-{date}.md`.
3. **Findings go to the notepad as you go**, appended with Write/Edit. See
   `notepad-enforcement.md`. (The MCP notepad tools this once named ship with
   the disabled `oh-my-claudecode` plugin and are absent from every session.)
4. **Specs go in `docs/specs/`** — not in plans, not in research.
5. **Learned skills go in `.claude/skills/<name>/SKILL.md`**, never under
   `.agent/` — Claude Code's loader does not scan anywhere else. Frontmatter
   `name` should match the directory name so slash-invocation and auto-loading
   stay consistent. Same for `.claude/rules/` and `.claude/agents/`.

6. **A skill is the TOP of a three-layer stack, never the whole thing**
   (Ray, 2026-08-08). Build downward: **skill → mise task → python library**
   (modular modules/functions). The skill carries only what needs *judgement* —
   when to reach for this, and the non-obvious failure modes; every mechanic
   lives in the library, and the task is the seam. **No bash**
   ([[zero-bash-logic]]).

   **Make each layer reusable by PARAMETER, not by copy.** The skill passes
   arguments through to the task, the task to the library function. A library
   function that hard-codes this repo's case cannot serve the next caller — make
   that case the parameter's *default* instead.

   **Author skills with `/skill-creator:skill-creator`, and shape the prose with
   `/writing-for-agents`.** Hand-written skills drift from the frontmatter and
   description shape the loader and the matcher depend on — and a `description`
   over 1,536 chars is silently truncated, taking the keywords Claude matches on
   with it ([[md-size-budgets]]).

   **The point is token economy.** Every step an agent performs by hand it will
   perform by hand again, paying full reasoning cost each time. Worked case: the
   image-lock recipe was re-derived from CI config across ~15 turns and produced
   a silent 51% lock truncation on the way (#650); three sibling candidates from
   the same session are #651–#653, and #654 is the skill that finds them.

## Why this rule cannot be `paths:`-scoped

It is **creation-triggered**: it governs *where to create* an artifact, so you
never read the file first. A scoped version would be absent exactly when it is
needed. See `md-size-budgets.md` § "Scoping: the trigger test".
