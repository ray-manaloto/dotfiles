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
