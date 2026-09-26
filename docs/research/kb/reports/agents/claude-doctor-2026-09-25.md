# Built-in `/doctor` — 2026-09-25 (session-plan step 0, item 1; goal-history iteration `dotfiles-goal-20260925-036`)

Run in session "dotfiles-20260925.000" (Opus 5.5). Ray upgraded the binary 2.1.282 → 2.1.283 with
`claude install latest` but did not restart, so the session itself ran 2.1.282 (every transcript record says so). `/doctor` is the built-in health-check prompt:
the model runs checks 0–9 read-only, then applies only what Ray confirmed. Ray chose
**"Clean up everything (Recommended)"** at the single cleanup gate. No permission gate was
asked, because checks 8 and 9 proposed nothing.

Scan window: **all 590 top-level transcripts, 31 days (2026-08-25 → 2026-09-25)**. The
default of 50 transcripts covered 1.0 day, too thin to judge usage. Control arms: 151 of 590
transcripts carry `toolDenialKind`, 24 carry an `mcp__` tool_use and 266 carry a `Bash`
tool_use, so a zero from the scan means absent rather than invisible. Token figures are
est. (chars / 4).

## Findings and dispositions

| # | Check | Finding (verbatim numbers) | Disposition |
|---|---|---|---|
| 1 | 0 install | `which -a claude` → `~/.local/share/mise/shims/claude` **before** `~/.local/bin/claude`. That shim came from orphaned mise installs `github:anthropics/claude-code` 2.1.270 + 2.1.271 and `npm:@anthropic-ai/claude-code` 2.1.269, and `mise which claude` → "claude is a mise bin however it is not currently active". No mise config references either backend: the grep found 0 hits, while the control arm on `oh-my-claude-sisyphus` in `~/.config/mise/config.toml` found 1. The shim fell through to native 2.1.283 | **FIXED** (host, not tracked): `mise uninstall github:anthropics/claude-code --all` (rc=0), `mise uninstall npm:@anthropic-ai/claude-code --all` (rc=0), `mise reshim` (rc=0). After the fix, `which -a claude` → only `~/.local/bin/claude`, reporting 2.1.283. Undo: `mise install <backend>@<v>` |
| 2 | 0 install | `installMethod` = native, matching the running launcher. No npm-global copy, no `~/.claude/local`, and `~/.local/bin` is on PATH | healthy |
| 3 | 0 settings | `jq empty` rc=0 on `~/.claude/settings.json`, `.claude/settings.json`, `.claude/settings.local.json`, `~/.claude.json` and `.mcp.json`. No managed-settings file exists | healthy |
| 4 | 0 agents/skills | 25 project agents, 0 user agents: 0 missing `description`, 0 same-directory `name` collisions. Every project and user `SKILL.md` has YAML frontmatter that parses | healthy |
| 5 | 1 skills | 10 user skills `source-command-memory-index-curation-skill-<8 hex>` are symlinks (created 2026-09-11) into `~/.agents/skills/`, all with the description `"Description delivered above."`. Lifetime uses 0, window hits 0; about 0.9k est. listing tokens | **FIXED** (user scope): `skillOverrides` `"off"` ×10 in `~/.claude/settings.json` (backup: `~/.claude/settings.json.bak-doctor-2026-09-25`). Undo: delete the 10 keys (never restore the backup: it predates the addendum's keys). What created them is not established — origin open, `task_plan.md` remainder item 21 |
| 6 | 1 skills | `herdr` (user): 0 uses. It fires only on an explicit request | **ACCEPTED** (Claude's call, not put to Ray; the cleanup gate covered rows 1, 5, 11 only): Phase 9 (herdr) is queued in `task_plan.md` |
| 7 | 1 skills | 25 project skills have 0 lifetime uses and 0 window hits (e.g. `lock-shared`, `reap`, `pin-parity`, `plugin-removal`) | **ACCEPTED** (Claude's call, not put to Ray): they are repo runbooks triggered by rare events, and turning them off locally would hide them exactly when their trigger fires |
| 8 | 1 plugins | All 12 effectively-enabled plugins have `usageCount` > 0 with `lastUsedAt` inside the window | healthy |
| 9 | 1 MCP | User-scope `MCP_DOCKER`: 0 calls in 31 days across every project. `.mcp.json` `exa` has 0 bare-name calls; the plugin-provided exa has 6. Both are already in this project's `disabledMcpServers` | **ACCEPTED**: nothing to do here. Removing either server is permanent (`claude mcp remove` wipes config and OAuth), so it was not proposed |
| 10 | 2 local CLAUDE.md | No `~/.claude/CLAUDE.md`, no `CLAUDE.local.md` | healthy |
| 11 | 3/4 checked-in | Always-loaded: 25 eager rules, **125,589 chars (~31.4k est. tok)**, plus root `CLAUDE.md`/`AGENTS.md`/`.claude/CLAUDE.md`/`token-routing.md` at 19,284 (~4.8k est.). No file exceeds the ~40k-char warning. The largest is `AGENTS.md` at 11,605; the largest rule is `probes-need-a-control-arm.md` at 9,331. The cost comes from restatements repeated across rules and from 3 niche behavior-triggered rules | **FILED** as a re-measurement on the existing #283 ([comment](https://github.com/ray-manaloto/dotfiles/issues/283#issuecomment-5840614053)); related #938, #916. Ray approved "files one issue"; the outcome was a comment on the existing #283. Not edited in place: a trim changes the eager-rule set that `rule-sync.toml`'s `rules` list binds across both repos (by stem), and rules are `md_size_budget`-gated |
| 12 | 5 hooks | planning-with-files `UserPromptSubmit` (`claude-hook.sh user-prompt-submit`) was cancelled at about 10 s on 12 prompts, 2026-08-31 → 09-12, with none since. Its `pre-tool-use` hook exceeded 2 s on 216 of the `PreToolUse:Bash` runs. `graphify-hook-guard.sh search` exceeded 2 s 58 times. `PreToolUse:Bash` overall: 16,280 runs, median 265 ms, max 34.8 s | **ACCEPTED** as a warning (the doctor contract edits no hooks). The plugin is NOT-OURS (upstream planning-with-files); the graphify guard is ours: its latency is tracked on #536 (remainder item 21 posts these numbers there) |
| 13 | 5 hooks | `SessionStart:startup` median 1,217 ms, max 40,957 ms. One `SessionStart:clear` run took 311,279 ms (2026-08-28), a `MISE_GLOBAL_CONFIG_FILE="${CLAUDE_PLUGIN_ROOT}/mise.toml"` plugin hook | **NOT-OURS**: that plugin hook has had no runs since, consistent with the fable-orchestrator removal (#1363) |
| 14 | 6 context | Listing: 49 project+user skills = 15,191 chars (~3.8k est.). `MEMORY.md` ~24.8 KB (~6.2k est.). Plugin agent `antigravity-delegate` has a 1,789-char description, over the 1,536 hard cap (SessionStart `doctor[listing-budget]`) | **NOT-OURS** for the agent (`~/.claude/plugins/cache/antigravity-for-claude-code/antigravity/0.28.0/agents/antigravity-delegate.md`); `MEMORY.md` is curated through the `memory-index-curation` skill |
| 15 | 7 version | Installed 2.1.283 = `https://downloads.claude.ai/claude-code-releases/latest` (2.1.283; `stable` = 2.1.274). Channel `latest`. `autoUpdates: false` is Ray's own choice, not an admin lock | healthy |
| 16 | 7 (repo) | `schemas/sources.toml` pinned the vendored claude-code types at 2.1.278 (SessionStart `doctor[claude-doctor]`). The upstream `.d.ts` exists at tag v2.1.283: HTTP 200, while control arms v2.1.278 → 200 and v2.1.999 → 404 | **FIXED** in dotfiles #1378 (squash `f68f943d`; branch commit `1b6cae72`): `version` + `source` tag bumped, `.claude/types/README.md` pin line bumped (pin-parity rc=0), `mise run schema-vendor-refresh` rc=0 → `.claude/types/claude-code.d.ts` +54 lines. Its header still reads 2.1.277, and the README now records that |
| 17 | 8 auto mode | `~/.claude/settings.json` `permissions.defaultMode` = `"auto"`. No project or local `defaultMode` shadows it, and no `disableAutoMode` is set | healthy |
| 18 | 9 denials | Top denials: `AskUserQuestion` 123 (58 permission-rule, 65 user-rejected), `cd …/knowledge-base` compounds 42, `cd …/dotfiles` compounds 30, `Agent` 26, `uv run` 21, `python3 -` 13, `git status` 12. All of these are `permission-rule` (this repo's PreToolUse guards: ask-quality, cd-compound, mise-tasks-only) or `user-rejected` | **ACCEPTED**: no allow rule proposed. A hook deny overrides allow rules, and the guards are deliberate |
| 19 | (incidental) | A 0-byte `.git/index.lock` (mtime 17:37:09) blocked `git add`. No git process held it on the host (only `fsmonitor--daemon`) or in the devcontainer (`ps` showed only sshd/sleep); `lsof` showed only the Docker Desktop VM holding a read handle through the bind mount | **FIXED**: removed; staging then succeeded. Origin not established; see `session-audit-dismissed-errors-2026-09-25b.md` |

## Addendum — after the report shipped (same session)

- **Antigravity model (Ray: "latest gemini 3.8 model for both repos").** `agy models` lists no Gemini 3.8 Pro, only
  3.8 Flash (High/Medium/Low). Bare `agy` and the `flash` tier already ran 3.8 Flash (High) (`~/.gemini/antigravity-cli/cli.log`);
  only the `pro` tier mapped to Gemini 3.1 Pro (High). **FIXED** (user scope, both repos): `pluginConfigs`
  `antigravity@antigravity-for-claude-code.options.tier_pro` and `env.CLAUDE_PLUGIN_OPTION_TIER_PRO` =
  `"Gemini 3.8 Flash (High)"` in `~/.claude/settings.json`. The `pluginConfigs` key alone did not reach a Bash-invoked
  `agy-delegate` (still 3.1 Pro); the `env` key did. Verified: `--print-command --tier pro|flash|flash-lo` → 3.8 Flash
  (High)/(High)/(Low). Undo: delete both keys. Row 5's backup predates these keys — undo row 5 by deleting its 10
  `skillOverrides` keys, never by restoring the backup. From here on `--tier pro` is a label, not a model class: it runs
  3.8 Flash (High).
- **knowledge-base `antigravity-cli` 1.2.2 → 1.2.11** (KB #814): agy updates itself in place, so the 1.2.2 install
  reported 1.2.11 and `kb-review-receipt` refused the drift.

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — `mods/types/claude-code.d.ts` fetched at v2.1.278 / v2.1.283 / v2.1.999 (control) to verify the pin bump.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issue search (#283, #938, #916) and the #283 re-measurement comment.
