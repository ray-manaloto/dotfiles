# Agent Artifact Conventions: Where Working Files Go

Agent working artifacts live under **`.agent/`** (gitignored, machine-local).
Anything that should survive a clone is **tracked**, and lives under `docs/` —
never in `.agent/`. Do not create ad-hoc directories in either.

> **Renamed from `.omc/` (2026-07-25).** That tree was named after the
> `oh-my-claudecode` plugin, which is **not enabled** — a convention named for
> a tool nothing loads. `.agent/` was verified before adopting, not assumed:
> control-armed over Claude Code's full docs corpus, `.agent/` → **0 hits**
> while `CLAUDE.md` → 439, so the probe discriminates. Claude Code claims
> `.claude/**` exclusively and has no opinion about `.agent/`.

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

**Promoting is the default for anything an eval, a rule, or a future session
will cite.** The migration surfaced why: five eager rules cited research that
had never been tracked, so every reader outside this one machine hit a dead
link — and `doc_refs` could not see it, because the whole `.omc/` prefix sat in
its allowlist. A citation to something only you can open is not a citation.

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

## Why `.gitignore`, not `.git/info/exclude`

`.omc/*` was excluded via `.git/info/exclude`, which is **per-clone and does
not survive a fresh clone** — which is exactly why every artifact anyone
actually wanted tracked had to be force-added with `git add -f`. An ignore rule
that exists on one machine is not a convention, it is an accident. `.agent/` is
in the real `.gitignore`.

`.omc/` also remains ignored: the statusline HUD configured in the **user-level**
`~/.claude/settings.json` still recreates `.omc/state/` in whichever repo is
cwd. Retiring that is a user-config change this repo does not make unasked.

## Why this rule cannot be `paths:`-scoped

It is **creation-triggered**: it governs *where to create* an artifact, so you
never read the file first. A scoped version would be absent exactly when it is
needed. See `md-size-budgets.md` § "Scoping: the trigger test".
