# Claude-specific project config

Claude-only configuration. The root `CLAUDE.md` is byte-exactly `@AGENTS.md`
(`claude_md_import_stub`) and `AGENTS.md` sits at agnix AGM-003's 12,000-char
cap, so anything Claude-specific that doesn't fit there lives here. `.claude/**`
is exempt from the stub and pair checks precisely so this file can exist.

## Agent skills, trackers and domain docs

The `mattpocock-skills` config here is **hand-placed and stays that way** —
`/setup-matt-pocock-skills` writes to paths our gates reject. Issue tracker:
GitHub Issues via `gh` (`docs/issue-tracker.md`); triage labels:
`docs/triage-labels.md`; domain: `CONTEXT.md` + `docs/domain.md`. **Our ADRs are
`.claude/rules/*.md`**; `docs/adr/` holds only domain-shaped decisions.

**`gh pr create`/`merge` are guard-denied. One verb per PR provenance:**
`mise run ship` (your branch), `mise run automerge -- <PR#>` (bot PR, #369),
`mise run land -- <PR#>` (post-merge).

**Attestation is OPERATOR-ONLY; all model routes denied**, `/plan-attest` too —
use `! mise run plan-attest` (`-- --show` reads, bare WRITES). Why:
`python/src/dotfiles_setup/plan_attest.py`.

## graphify + project doctor

Use `mise run graphify-query` for queries; `graphify-check`/`graphify-update`
for currency; `graphify-rebuild` for extraction; or `graphify-upgrade` for
both. Use these mise tasks instead of PATH `graphify`
(`.claude/rules/graphify-first.md`). SessionStart doctor reads `doctor.toml`,
exits 0, and is silent when healthy.

⚠️ Two traps that bite: **MCP registrations come from FOUR places** — `.mcp.json`,
each enabled plugin, and `~/.claude.json`'s user-global *and* per-project blocks
— and a same-name user-global entry **shadows** a project one silently. And
**changing your setup means changing `doctor.toml` in a reviewed diff**: adding
to `[fnox].env_true` widens a credential's blast radius.

⚠️ **Project registrations live HERE, never in the root `CLAUDE.md`** — the
`claude_md_import_stub` gate locks that file to byte-exactly `@AGENTS.md`, and
re-running `graphify install` re-appends there; revert that hunk. Full detail: `docs/claude-plugin-config-hygiene.md`.

## Cross-vendor orchestration (architect + executor lanes)

- Without being reminded, on ANY session model: non-trivial implementation runs the architect-as-orchestrator flow — invoke this repo's routing-doctrine skill (`codex-sdlc-team` in dotfiles, `orchestrator-routing` in knowledge-base) before delegating and follow it as authoritative for routing, the spec contract, review tiers, and advisor escalation.

The trigger is **deliberately UN-gated** (it fires on any session model) and is
rule-synced byte-for-byte with knowledge-base. The doctrine lives in the
`codex-sdlc-team` skill, versioned and gated here.

### Lane routing — codex and Claude only

Every lane resolves to codex or to Claude. Route by this fixed table:

| Lane | Use |
|---|---|
| Implementation | `codex-{sol,astra}-implementer`, effort `xhigh` — OURS, at full access |
| Cold review of a codex diff | an Opus subagent, diff-only (`Agent`, `model: "opus"`) |
| Cold review of a Claude-authored diff | a read-only codex review lens — the exact command lives once, in the `codex-sdlc-team` skill § Review tiers |
| Advisory / critique / audit / harness | `codex-{sol,astra}-{advisor,adversarial-critic,staleness-auditor,claude-code-expert}` |
| Premise verification | `premise-verifier` (Claude, read-only) |
| Research | a read-only `Explore`/`Agent` lane |
| Multi-domain SDLC review | codex-side team — [[codex-sdlc-team]] |

Repo-owned agents: `gate-runner`, `cold-reviewer`, `graphify-operator`, `graphify-researcher`,
`spec-scribe`, `pwf-scribe`, `issue-filer`, `claude-advisor`, `premise-verifier`.
Saved workflows: `/gated-implementation`, `/graphify-refresh`.

Two model families per role: `codex-sol-*` (authored) and `codex-astra-*`
(generated — `mise run codex-lane-mirror`). Neither is a default.

⚠️ **No `codex-*` lane is the cold-review lens for a codex diff** — same model
family as the implementer, so it inherits its blind spots. Claude is the
other family, so an Opus cold pass on a codex diff is the full gate, not a
degraded one.

⚠️ Permanent advisor-consult routing and escalation: see @token-routing.md.

Adopted plugin (enabled in `.claude/settings.json`): `antigravity@antigravity-for-claude-code`
(Google Antigravity/Gemini 3.x via `agy`). `antigravity-cli` is pinned in `mise.toml`; codex runs
the native install on the host (`disable_tools`) and the shared npm pin in the image/CI; auth is per-user. The Claude architect plans and **verifies evidence**
before "done" — only execution is delegated; terminal fallback is Claude Opus. knowledge-base
carries the same doctrine in its `orchestrator-routing` skill.

## DAG topology pins (#567)

`.claude/settings.json` pins the DAG substrate (map #556): the `env` block plus
`fallbackModel` + `switchModelsOnFlag`. `CLAUDE_*` pins go in settings `env`, NEVER a
shell export (background launch strips them; respawn re-reads only settings). Evidence:
`docs/receipts/567.md`.

**NOT set — do not "fix" back:** `DISABLE_AUTO_COMPACT` (kills the PreCompact gate),
`CLAUDE_CODE_SUBAGENT_MODEL` (overrides per-node model choice),
`CLAUDE_CODE_NO_MODEL_FALLBACK` (kills the availability chain AND Fable credit substitution).
