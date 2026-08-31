# Claude Code plugin config: how `enabledPlugins` actually resolves

Investigation and fix for a `/plugin` panel reporting **30 load errors**, 2026-07-30.
The headline finding is not the errors — it is the resolution model underneath them,
which is easy to get wrong and which bit this repo twice in one session.

## TL;DR

| | |
|---|---|
| **Symptom** | `/reload-plugins --force` → *"30 errors during load"*, each *"Plugin X is enabled in project settings but isn't installed here"* |
| **Root cause** | An `enabledPlugins` entry has an effect **by being present**, not by being `true`. Entries also **aggregate across every project's settings on the machine**, not just the open one. Accounts for 29 of 30 — the last one needed a restart (see "What was left alone"). |
| **Fix** | **Delete** stale entries; do not set them `false`. 187 removed across three files. |
| **Result** | 30 errors → **1**, and that one is correct configuration. Zero behavioural change: every file's set of *enabled* plugins was byte-identical afterwards. |

## The two facts that make this counter-intuitive

### 1. Presence has an effect; the boolean does not gate the check

`zoominfo`, `srclight` and `remember` were all reported as *"is enabled in project
settings"* while being **`false`** in that settings file. So the loader's validation
walks the **keys** of `enabledPlugins` and complains about any whose plugin is not
installed for the current project — regardless of value.

This makes the error text actively misleading, and it is why the first repair
attempt failed: it removed entries whose plugin was not installed *for the project
that declared them*, when the criterion is *not installed **for the project you have
open***.

> **Consequence for hygiene:** a `false` entry is not free. It is not "disabled and
> harmless" — it is a live key that participates in validation. Remove entries you
> do not want; only keep a `false` when it is doing real work (below).

### 2. Enablement aggregates across unrelated projects

`superpowers` was among the errors. It is declared in
`guilde-lite-tdd-sprint/.claude/settings.json` — **a repo never opened in the
session**. Others traced to `macos-development-environment`, which was only present
as an *additional working directory*.

So the panel's "project settings" means *the union of settings files it can see*,
which on a machine with many checkouts is a large set. Config in one repo shows up
as an error in another.

## When a `false` IS load-bearing — the rule that prevents breakage

Precedence, per the panel's own remediation text
(*"project settings override `~/.claude/settings.json`"*, *"set … in
`.claude/settings.local.json` instead"*):

```
settings.local.json   >   .claude/settings.json   >   ~/.claude/settings.json
      (local)                   (project)                    (user)
```

A `false` is meaningful **only when some other in-scope file marks the same plugin
`true`**. Deleting such an entry silently *enables* the plugin.

**This is not hypothetical.** A first pass compared each `false` against **user
scope only** and concluded nothing was load-bearing. A second pass, comparing
against *all* loaded scopes, found **10** that were — including **both** entries in
this repo's `settings.local.json`:

| entry | local | project | deleting it would have… |
|---|---|---|---|
| `explanatory-output-style@claude-plugins-official` | `false` | `true` | switched the output style **on** |
| `learning-output-style@claude-plugins-official` | `false` | `true` | switched the output style **on** |

The lesson generalises: **check the key against every scope that loads, not just the
one above it.**

## The procedure that worked

1. **Back up everything first** — all settings files *and* `installed_plugins.json`.
2. **Classify, don't bulk-delete.** For each file, a `false` entry is removable only
   if no other in-scope file marks that key `true`.
3. **Delete by line, not by JSON round-trip.** Rewriting via `json.dump` reorders and
   reformats the whole file, burying a 20-line change in a 200-line diff. Matching
   `^\s*"key"\s*:\s*(true|false),?$` and dropping those lines leaves every other line
   byte-identical, then repair any dangling comma with `,(\s*[}\]])` → `\1`.
4. **Gate on parse.** `json.loads(text)` before writing — never write an unparsed
   result.
5. **Verify the enabled SET, not the entry count.** The invariant that matters is
   that the set of `true` keys is unchanged:

   ```
   user      entries 28  -> 6    TRUE 1  -> 1    identical_true=True
   mde       entries 164 -> 22   TRUE 22 -> 22   identical_true=True
   dotfiles  entries 42  -> 19   TRUE 14 -> 14   identical_true=True
   ```

6. **Predict the outcome before asking for a reload.** State the expected error count
   and treat a miss as information. The first attempt predicted a drop and produced
   none — which is what exposed fact #1 above.

## What was left alone, and why

- **`challenger@claude-community`** — the single residual error, and the one that
  **bounds the root-cause claim above**. Entry-presence explains 29 of the 30: they
  vanished exactly when the keys were deleted. It does **not** explain this one.
  Removing its settings entry changed nothing; removing its **install record**
  (`claude plugins uninstall … --scope project`) changed nothing either. Afterwards
  it appeared in **zero** on-disk sources — 55 `settings*.json` files, `~/.claude.json`
  top-level and all 31 per-project blocks, `installed_plugins.json`, and
  `plugins/config.json` — each check control-armed, and it was *still* reported.
  It only cleared on a **session restart**.

  So the honest statement of the mechanism is two-part: **entry presence is what you
  can fix, and it accounts for the bulk — but the panel also holds error state that no
  on-disk change clears within a session.** If a residue survives deletion, stop
  editing files and restart.
- **`codex@openai-codex`** — a ⚠ warning, not an error: this repo's tracked settings
  enable it, which overrides a `false` at user scope. Intended. To make the user-level
  disable win, put `"codex@openai-codex": false` in `.claude/settings.local.json`.
- **The plugin caches.** `~/.claude/plugins/cache` is **5.7 GB** and live — 234
  install records point into it; clearing it uninstalls every plugin. `cache.bak` is
  **1.1 GB**, last written 2026-04-08, and provably orphaned (**0** references,
  against a control of 234 into the live cache) — safe to delete, deliberately left
  in place for now. `claude plugins prune --dry-run` reports **nothing to prune** at
  either scope; it only handles auto-installed dependencies.

## After the restart: a different failure, and a real one

The restart cleared `challenger` and surfaced two errors that are **not** stale:

```
fable-orchestrator (project)  Plugin not cached at …/cache/fable-orchestrator/fable-orchestrator/1.14.0
antigravity (project)         Plugin not cached at …/cache/antigravity-for-claude-code/antigravity/0.21.1
```

These have consequences — the session's agent roster lost
`fable-orchestrator:{codex-implementer,codex-reviewer,fable-advisor,grok-*}` and
`antigravity:antigravity-delegate`. But **the cache is correct**: both directories
exist at exactly the named paths, both carry `.claude-plugin/plugin.json`, and the
cached version matches the marketplace checkout's (`1.14.0`, `0.21.1`) in each case.
Control arm: `last30days`, which loads fine, has the identical structure.

So "not cached" is the loader's index disagreeing with the filesystem, not missing
content. The remediation printed by the panel — **refresh the plugin cache from
`/plugin`** — is the supported fix; a forced reinstall is the fallback.

## Cost worth knowing about

Adding a second repo as a working directory **inherits its entire plugin surface**.
After adding `macos-development-environment`, the reload reported **19 plugins · 34
skills · 42 agents · 12 hooks** — skills and agents from that repo's plugin set now
load into every turn, charged against the eager-context budget this repo works to
keep near ~112 KB ([[md-size-budgets]], #414). Add the directory to read source;
drop it when done.

**It also silently widens MCP scope.** The #418 doctor caught this on the next
session start:

> `mcp-scope`: the `filesystem` server declares 2 directories but the harness sends
> **3** roots (this workspace plus `permissions.additionalDirectories`) — **and roots
> REPLACE the server's arguments, so the declared scope restricts nothing.**

That is the same shape as the rest of this document and as the fnox `env` wipe: **a
declaration that reads like a constraint while enforcing nothing.** Either declare
the same set in `.mcp.json` or drop the extra working directory.

## Where this connects

The shape is the same one this repo hit with the fnox `env` wipe the same day:
**declarative config in one location silently changing behaviour in another, with a
status readout that reports the wrong thing.** Both were found by distrusting a
message and measuring the artifact instead. See
`docs/rules-evidence/secrets-out-of-the-shell-env.md` and
`.claude/rules/probes-need-a-control-arm.md`.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — `.claude/settings.json`, `.claude/settings.local.json`.
- [ray-manaloto/macos-development-environment](https://github.com/ray-manaloto/macos-development-environment) — `.claude/settings.json`; the source of most stale entries, being retired into this repo.
- [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) — installed project-scoped during this work.
- [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc) — installed project-scoped; source of the residual warning.

## Moved from `.claude/CLAUDE.md` (2026-08-31, eager-context trim)

The sections below were reference inventories carried in every session's
standing context. `.claude/CLAUDE.md` keeps the operative constraints and
points here.

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

- Codebase questions: follow `.claude/rules/graphify-first.md`
  (`mise run graphify-query`, never a bare `graphify` on `PATH`).
- After changing code: `mise run graphify-update` (AST-only, no API cost).

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
