# Claude-specific project config

Claude-only configuration. The root `CLAUDE.md` is byte-exactly `@AGENTS.md`
(`claude_md_import_stub`) and `AGENTS.md` is at 200/200 lines, so anything that
is Claude-specific and doesn't fit there lives here. `.claude/**` is exempt from
the stub and pair checks precisely so this file can exist.

## Agent skills, trackers and domain docs

The `mattpocock-skills` config here is **hand-placed and stays that way** —
`/setup-matt-pocock-skills` writes to paths our gates reject. Issue tracker:
GitHub Issues via `gh` (`docs/issue-tracker.md`); triage labels:
`docs/triage-labels.md`; domain: `CONTEXT.md` + `docs/domain.md`. **Our ADRs are
`.claude/rules/*.md`**; `docs/adr/` holds only domain-shaped decisions.

**`gh pr create`/`merge` are guard-denied. One verb per PR provenance:**
`mise run ship` (your branch), `mise run automerge -- <PR#>` (bot PR, #369),
`mise run land -- <PR#>` (post-merge).

## graphify + project doctor

graphify is registered project-scoped and host-only; query with
`mise run graphify-query`, refresh with `mise run graphify-update` — never a
bare `graphify` on `PATH` (`.claude/rules/graphify-first.md`). The doctor runs
from the SessionStart hook against `doctor.toml`, is silent when healthy, and
always exits 0.

⚠️ Two traps that bite: **MCP registrations come from FOUR places** — `.mcp.json`,
each enabled plugin, and `~/.claude.json`'s user-global *and* per-project blocks
— and a same-name user-global entry **shadows** a project one silently. And
**changing your setup means changing `doctor.toml` in a reviewed diff**: adding
to `[fnox].env_true` widens a credential's blast radius.

⚠️ **Both registrations live HERE, never in the root `CLAUDE.md`** — the
`claude_md_import_stub` gate locks that file to byte-exactly `@AGENTS.md`, and
re-running `graphify install` or the fable setup wizard re-appends there; revert
that hunk. Full detail: `docs/claude-plugin-config-hygiene.md`.

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
