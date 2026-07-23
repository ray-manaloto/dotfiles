# Claude-specific project config

Claude-only configuration. The root `CLAUDE.md` is byte-exactly `@AGENTS.md`
(`claude_md_import_stub`) and `AGENTS.md` is at 200/200 lines, so anything that
is Claude-specific and doesn't fit there lives here. `.claude/**` is exempt from
the stub and pair checks precisely so this file can exist.

## Agent skills

Config for the `mattpocock-skills` engineering flow.

**These files are hand-placed, and stay that way.** `/setup-matt-pocock-skills` generates the same
config but writes it to the root `CLAUDE.md` and `docs/agents/*.md` — paths our gates reject (the
stub check, and agnix's `**/agents/*.md` frontmatter rule). Reach for the files below instead; they
are its output, already adapted.

### Issue tracker

GitHub Issues on `ray-manaloto/dotfiles`, via `gh`. See `docs/issue-tracker.md`.
**`gh pr create`/`merge` are guard-denied — use `mise run ship` / `mise run land`.**

### Triage labels

The five canonical roles, adopted verbatim (no remapping). See `docs/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` (glossary) + `docs/adr/`. See `docs/domain.md`.
**Our ADRs are `.claude/rules/*.md`** — each carries its own "Why this rule exists"; `docs/adr/`
holds only domain-shaped decisions.
## graphify — knowledge-graph substrate

Registered by `graphify install --project` (#310–#318 adoption). Host-only,
project-scoped; `graphify-out/` is gitignored. When the user types `/graphify`,
use `.claude/skills/graphify/SKILL.md`.

- Codebase questions: run `graphify query "<question>"` first when
  `graphify-out/graph.json` exists (`path`/`explain` for relationships/concepts) —
  a scoped subgraph, smaller than raw grep.
- After changing code: `graphify update .` (AST-only, no API cost).

**This registration lives here, NOT in the root `CLAUDE.md`:** the
`claude_md_import_stub` hk gate locks the root file to byte-exactly `@AGENTS.md`,
so graphify's default write there (which happened and was reverted) fails
`mise run lint`. `.claude/CLAUDE.md` is the repo's designated home for exactly
this kind of Claude-specific content (it is stub-exempt). Re-running
`graphify install` will re-append to the root `CLAUDE.md`; revert that hunk.

## Cross-vendor orchestration (Fable-5 architect + executor lanes)

fable-orchestrator: implementation lane = codex

Adopted plugins (enabled in `.claude/settings.json`): `fable-orchestrator@fable-orchestrator`
(Fable-5 architect + `codex` implementer lane, GPT-5.6 Sol) and
`antigravity@antigravity-for-claude-code` (Google Antigravity/Gemini 3.x via `agy`). CLIs pinned
host-only in `mise.toml` (`codex`, `antigravity-cli`); auth is per-user. The Claude architect plans
and **verifies evidence** before "done" — only execution is delegated; terminal fallback is Claude
Opus. The authoritative routing/fallback doctrine (and its KB-graph grounding) is the
`orchestrator-routing` skill in the **knowledge-base** repo.
