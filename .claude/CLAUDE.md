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
**`gh pr create`/`merge` are guard-denied. One verb per PR provenance: `mise run ship`
(your branch), `mise run automerge -- <PR#>` (bot PR, #369), `mise run land -- <PR#>`
(post-merge).**

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

## Project doctor — declared setup vs reality on this host (#418)

`SessionStart hook → mise run doctor → dotfiles_setup.doctor`, baseline
**`doctor.toml`** (sibling of `currency.toml` / `parity.toml`). Silent when
healthy; always exits 0, so it cannot disrupt a session. `-- --verbose` for a PASS
line per check, `-- --live` adds the MCP spawn + `claude mcp list` probes,
`-- --strict` exits 1.

It lives here, not in `AGENTS.md`, because everything it reads is Claude Code's own
setup plus `~/.config/fnox`. **No hk step, no CI job** — a runner has none of that
state, so the hook is the only place it runs, which is why `hook_selfcheck` gates
the wiring in `ship`/`land`.

Two invariants worth knowing before editing it:

- **MCP registrations come from FOUR places** — `.mcp.json`, each enabled plugin,
  and `~/.claude.json`'s user-global *and* per-project blocks. A same-name
  user-global entry **shadows** a project one silently; that is how a broken
  `mde-mcp-filesystem` wrapper took this repo's filesystem server down. Checks that
  say "fix this repo's declaration" run only on what the repo declares
  (`Server.repo_owned`); "your setup is broken" checks run on everything.
- **Changing your setup means changing `doctor.toml` in a reviewed diff.** Adding
  to `[fnox].env_true` widens a credential's blast radius; adding to
  `[mcp.mutating_tools]` declares something needs a permission decision.

Version currency is delegated to `kb-setup currency check` and health to
`claude mcp list` — neither is re-implemented.

## Cross-vendor orchestration (Fable-5 architect + executor lanes)

- Without being reminded, on ANY session model: non-trivial implementation runs the fable-orchestrator architect-as-orchestrator flow — invoke the fable-orchestrator:orchestration skill before delegating and follow it as authoritative for routing, verification, review tiers, and advisor consults.
- fable-orchestrator: implementation lane = codex
- fable-orchestrator: codex effort = xhigh

The first line is the **trigger**, **deliberately UN-gated**, matching
knowledge-base. The plugin ships it Fable-gated — but default `/model` here is
**Opus 5**, so the gated line was false every session and the flow stayed
dormant. So `/fable-orchestrator:setup` reads an un-gated trigger as a shape to
upgrade away from and offers to re-gate it — **decline**. It also writes to the
root `CLAUDE.md`, which the stub gate rejects: config belongs in THIS file.
`grok` CLI is NOT installed, so `codex` is the only viable fixed mode.

Adopted plugins (enabled in `.claude/settings.json`): `fable-orchestrator@fable-orchestrator`
(Fable-5 architect + `codex` implementer lane, GPT-5.6 Sol) and
`antigravity@antigravity-for-claude-code` (Google Antigravity/Gemini 3.x via `agy`). CLIs pinned
host-only in `mise.toml` (`codex`, `antigravity-cli`); auth is per-user. The Claude architect plans
and **verifies evidence** before "done" — only execution is delegated; terminal fallback is Claude
Opus. The authoritative routing/fallback doctrine (and its KB-graph grounding) is the
`orchestrator-routing` skill in the **knowledge-base** repo.

## DAG topology pins (#567)

`.claude/settings.json` pins the DAG substrate (map #556): the `env` block plus
`fallbackModel` + `switchModelsOnFlag`. `CLAUDE_*` pins go in settings `env`, NEVER a
shell export (background launch strips them; respawn re-reads only settings). Evidence:
`docs/receipts/567.md`.

**NOT set — do not "fix" back:** `DISABLE_AUTO_COMPACT` (kills the PreCompact gate),
`CLAUDE_CODE_SUBAGENT_MODEL` (overrides per-node model choice),
`CLAUDE_CODE_NO_MODEL_FALLBACK` (kills the availability chain AND Fable credit substitution).
