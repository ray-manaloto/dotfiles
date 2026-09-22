# Plugin CLI requirements audit — dotfiles (2026-09-22)

> Persisted verbatim at receipt by the coordinator (session 2026-09-22d), from the
> delegate's final message. The harness neutralised `<` as `&lt;` in transit;
> restored here.

The CLIs you named (firecrawl, ctx7, agy, codex) are already pinned in this repo's mise config and all run. The real gaps are elsewhere:

1. **`timeout` is a broken mise shim here, and it breaks Antigravity delegation.** The plugin wraps every `agy` call in `timeout`.
2. **Nothing in the repo pins `node`.** The npm-installed `firecrawl`, `ctx7` and `codex` all start with `#!/usr/bin/env node`, so they only run because of your user-global mise config.
3. **`gh` isn't pinned either.** It comes from user-global only, but last30days, mattpocock-skills and the repo's own tasks call it.

This lane was read-only, so I didn't write to `findings.md` or `progress.md`. This report still needs to be saved verbatim, e.g. `docs/research/kb/reports/agents/plugin-cli-requirements-2026-09-22.md`.

## Scope

**Enabled here (15 plugins):** skill-creator, explanatory-output-style, learning-output-style, codex, mattpocock-skills, fable-orchestrator, antigravity, context7, last30days, exa, firecrawl, eli5, i-have-adhd, planning-with-files, plus ponytail.
- **ponytail** is turned off by `.claude/settings.local.json`. `mise run plugin-health` exits 1 with `declared_disabled_here: ["ponytail@ponytail"]`.
- **firecrawl** is installed only at user scope (1.0.9). The user-level `~/.claude/settings.json` sets `firecrawl@firecrawl=false`, but the project setting (`true`) wins here, and its skills load.

## Key findings (each with its control check)

1. **The `timeout` shim breaks `/antigravity:delegate` and the Antigravity doctor.**
   - `scripts/agy-delegate.sh:204-205` picks `timeout` first. Line 434 then runs `"$TO_CMD" --kill-after=10 N agy …`. `scripts/doctor.sh:38,54` works the same way.
   - `command -v timeout` finds `~/.local/share/mise/shims/timeout`, which fails with `mise ERROR No version is set for shim: timeout`, rc=1.
   - Both sides checked:
     - `timeout … agy models` fails (rc=1); plain `agy models` succeeds (rc=0, 14 models).
     - `bin/agy-doctor` fails as-is (rc=1, "agy could not list models"). With GNU `timeout` 9.11 first on PATH it passes (rc=0, "All checks passed — ready to delegate").
   - Where the shim comes from: `conda-coreutils/9.11` and `pkgx-gnu-org-coreutils/9.11.0` are installed, but only knowledge-base activates coreutils (`knowledge-base/mise.toml:247`).
   - The fable-orchestrator doctor has the same flaw (`scripts/doctor.sh:17` then `:70` `${T:+$T 180} codex exec`). Its implementation lanes are unaffected: `run-lane.sh` uses its own pure-bash watchdog. I read this code but didn't run that doctor, because it makes live, billable calls.

2. **`node` isn't pinned, so the repo's own npm CLIs can't run from repo config alone.** Running each CLI with the user-global config ignored (`MISE_IGNORED_CONFIG_PATHS=~/.config/mise/config.toml mise exec -- <cli> --version`):

   | CLI | Result |
   |---|---|
   | `firecrawl` | rc=1, "No version is set for shim: node" |
   | `ctx7` | rc=1, same error |
   | `codex` | rc=1, same error |
   | `gh` | rc=1 |
   | `yt-dlp` | rc=1 |
   | `agy` (control) | rc=0 |
   | `jq` (control) | rc=0 |

   The plugin hooks also run `node`: codex's hooks, the context7 `headersHelper`, i-have-adhd, and ponytail.

3. **Firecrawl ships a standalone binary.** `firecrawl/cli` v1.24.3 has release assets for darwin and linux. The darwin-arm64 tarball's sha256 matches `checksums.txt`. It is a Mach-O executable that runs with no node: `env -i PATH=/usr/bin:/bin ./firecrawl-darwin-arm64 --version` gives 1.24.3, rc=0. `ctx7` has no release assets (tags `ctx7@0.5.x` have 0 assets), so npm is its only backend. Neither is in the mise registry (`mise registry firecrawl` and `ctx7` both say "tool not found"; control `codex` resolves).

4. **Credentials (presence only):**
   - SET: `FIRECRAWL_API_KEY`, `EXA_API_KEY`, `CONTEXT7_API_KEY`, `SCRAPECREATORS_API_KEY`, `GEMINI_API_KEY`, `GITHUB_TOKEN`.
   - ABSENT: `XAI_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `GH_TOKEN`.
   - Control: `HOME` reads SET.
   - `firecrawl --status`: rc=0, "Authenticated via FIRECRAWL_API_KEY".
   - `codex login status`: "Logged in using ChatGPT". `codex-companion.mjs setup --json` returns `ready:true` and took no actions.
   - `ctx7 whoami` says "Not logged in", but that only covers OAuth. The ctx7 code reads `CONTEXT7_API_KEY` (found in `dist/index.js`).
   - **The exa plugin never uses `EXA_API_KEY`.** Its MCP server entry sends only an `x-exa-source` header, so it runs anonymously or via OAuth.

5. **Other notes:**
   - `firecrawl --status` reports ".firecrawl ignored: no". The firecrawl skills write output to `.firecrawl/`, and `git check-ignore .firecrawl/x` returns rc=1 (control: `.agent/x` is ignored by `.gitignore:124`).
   - Codex is one version behind (0.154.0 pinned, npm latest 0.155.1).
   - skill-creator needs PyYAML, which isn't declared anywhere. It happens to be in mise python 3.14.7 (6.0.3), and `quick_validate` returned rc=0.

## Table

"Pinned" means in dotfiles' mise config. `plugin cache` is `~/.claude/plugins/cache/<plugin>/<version>/`. File:line references are inside the plugin.

| Plugin | Binary | Needed by (file:line) | Pinned in dotfiles? | Latest | Runs? | Action |
|---|---|---|---|---|---|---|
| firecrawl | `firecrawl` | `skills/*/SKILL.md:6` `Bash(firecrawl *)` (10 skills); `README.md:25-28` | `mise.toml:140` `npm:firecrawl-cli` 1.24.3 | 1.24.3 (npm; GitHub release 2026-09-22) | yes; `--status` rc=0 | none. Optional: switch to `github:firecrawl/cli` to drop node |
| firecrawl | `npx` (fallback) | `skills/*/SKILL.md:7` `Bash(npx firecrawl-cli *)` | no (user-global npm 12.0.2) | — | yes | none (fallback only) |
| firecrawl, ctx7, codex | `node` | each npm bin starts `#!/usr/bin/env node` | **no** (user-global 26.10.0) | 26.10.0 | only via user-global | **add pin** |
| context7 | `node` | `.mcp.json` `headersHelper` → `scripts/headers.mjs` | no | — | yes (user-global) | covered by the node pin |
| (repo's own skills and the doc-source rule) | `ctx7` | `.claude/skills/context7-cli`; `research-doc-sources.md` step 3. Not a plugin need | `mise.toml:66` `npm:ctx7` 0.5.11 | 0.5.11 | yes | none (npm is the only backend) |
| codex | `node`, `codex` | `hooks/hooks.json` (node ×3); `commands/setup.md:4,22`; `scripts/lib/app-server.mjs:190` | `shared.toml:44` `npm:@openai/codex` 0.154.0 | 0.155.1 | yes; setup `ready:true` | **bump to 0.155.1**. Keep npm (reason at `mise.toml:119-126`) |
| codex | `git` | `commands/review.md:5` `Bash(git:*)` | no; the shim falls through to `/usr/bin/git` 2.54.0 | — | yes | none |
| fable-orchestrator | `codex` | `scripts/run-lane.sh`, `scripts/doctor.sh` | as above | — | yes | as above |
| fable-orchestrator | `grok` | `agents/grok-*.md`, `run-lane.sh` | no (not installed) | `aqua:x.ai/cli/grok` exists | no | **do NOT pin**: codex-only lanes (`.claude/CLAUDE.md`) |
| fable-orchestrator | `jq` | `scripts/premise-gate.sh:123`. Gate stays open if jq is missing | `shared.toml:38` 1.8.2 | — | yes | none |
| fable-orchestrator | `timeout` / `gtimeout` | `scripts/doctor.sh:17,70,104` | **no**; broken shim | coreutils 9.12 (conda) | **no**, rc=1 | **add** `conda:coreutils` |
| antigravity | `agy` | `hooks/check-agy.sh:10,16`; `bin/agy-delegate` | `mise.toml:127` `antigravity-cli` 1.2.8 | 1.2.8 (2026-09-22) | yes; `agy models` rc=0 | none |
| antigravity | `timeout` | `scripts/agy-delegate.sh:204,361,434`; `scripts/doctor.sh:38,54` | **no**; broken shim | coreutils 9.12 | **no**: delegate and doctor fail (rc=1) | **add** `conda:coreutils` (fix confirmed: doctor rc=0) |
| antigravity | `python3` | `hooks/nudge-delegation.sh`, `hooks/validate-delegate-bash.sh` | `shared.toml:49` 3.14.7 | — | yes | none |
| last30days | `python3` ≥3.12 | `skills/last30days/SKILL.md:34-35,426-493` | `shared.toml:49` 3.14.7 | — | yes | none |
| last30days | `node` | `SKILL.md:34`; `lib/bird_x.py:206` (X/bird backend) | no | — | user-global | covered by the node pin |
| last30days | `yt-dlp` | `lib/youtube_yt.py:293`; `lib/setup_wizard.py:142-152` (falls back to `brew install`) | no (user-global 2026.08.19) | 2026.08.19 | yes | optional pin |
| last30days | `gh` | `lib/github.py:59` (`gh auth token` fallback; `GITHUB_TOKEN` is SET so it isn't reached); `lib/doctor.py:656` | no (user-global `github-cli` 2.101.0) | v2.101.0 | yes | **add pin** |
| last30days | `digg-pp-cli`, `arxiv-pp-cli`, `techmeme-pp-cli` | `lib/setup_wizard.py:207-211` (installs via `npx @mvanhorn/printing-press-library@0.1.16`) | no (in `~/.local/bin`) | — | yes, rc=0 | **do NOT pin**: the plugin installs these itself |
| last30days | `ffmpeg` (optional) | `lib/transcribe.py:56` | `mise.toml:86` `conda:ffmpeg` 9.0.1 (macOS only) | — | yes | none |
| planning-with-files | `sh`, `python3`; `flock` optional | `hooks/hooks.json`; `hooks/claude-hook.sh:74`; `scripts/ledger-append.sh:330` (fallback when flock is absent) | python pinned; flock absent | — | yes | none |
| skill-creator | `python3` + PyYAML; `claude` | `scripts/quick_validate.py:9`; `SKILL.md:432` (`claude -p`) | python pinned; PyYAML not declared; `claude` falls through to `~/.local/bin/claude` 2.1.280 | — | yes (`quick_validate` rc=0) | none (PyYAML unmanaged, noted) |
| i-have-adhd | `node` | `hooks/hooks.json` (`node -e`, silent on failure) | no | — | user-global | covered by the node pin |
| explanatory- / learning-output-style | `bash` | `hooks/hooks.json` | system | — | yes | none |
| mattpocock-skills | `gh`, `git` | `skills/engineering/setup-matt-pocock-skills/SKILL.md:40` (`gh issue create`); wizard `gh secret` | gh not pinned | — | yes | covered by the gh pin |
| exa | none (hosted MCP at `https://mcp.exa.ai/mcp`) | `.claude-plugin/plugin.json` `mcpServers` | n/a | — | n/a | none |
| eli5 | none | `skills/eli5/SKILL.md` (writes HTML only) | n/a | — | n/a | none |
| ponytail (off here) | `node` | `hooks/claude-codex-hooks.json` | — | — | — | none while disabled |

## Recommended mise.toml entries

```toml
# node: the runtime for the npm-backend CLIs this file pins (firecrawl-cli, ctx7,
# @openai/codex all start `#!/usr/bin/env node`) and for plugin hooks (codex,
# context7 headersHelper, i-have-adhd). mise registry: core:node only.
node = "26.10.0"
# gh: last30days (github source), mattpocock triage/to-tickets, and this repo's own
# gha-dispatch/ship/land. Registry `gh` = aqua:cli/cli (knowledge-base uses the same key).
gh = "2.101.0"
# GNU timeout for the antigravity (agy-delegate, doctor) and fable-orchestrator
# (doctor) wrappers; the undeclared name is an erroring shim (rc 1). Same pin as
# knowledge-base/mise.toml:247. os-gated like conda:ffmpeg (mise.toml:78-86):
# conda/rattler can't write linux lock URLs (jdx/mise#7700); linux has GNU already.
"conda:coreutils" = { version = "9.11", os = ["macos"] }   # 9.12 is latest
# optional — last30days YouTube source only; registry backend github:yt-dlp/yt-dlp
yt-dlp = "2026.08.19"
```

**Bumps:** `@openai/codex` 0.154.0 → 0.155.1. It lives in `shared.toml`, so it needs `mise run lock-shared` and `mise run lock-image`, not `mise run lock`.

**Optional backend change:** `"github:firecrawl/cli" = { version = "1.24.3", rename_exe = "firecrawl" }` in place of the npm entry. This moves it up a backend tier and removes its node dependency. I have not tested how mise installs it: the asset inside the tarball is named `firecrawl-darwin-arm64`, so the `rename_exe` setting needs checking with a real install.

**Backend notes:**
- firecrawl-cli: GitHub releases exist (above); npm otherwise.
- ctx7: npm only (no release assets, not in the registry).
- codex: the repo deliberately uses npm over `aqua:openai/codex`.
- node: `core:node` only.
- coreutils: the registry's `coreutils` points to `aqua:uutils/coreutils`, which **can't** supply a `timeout` command. Its aqua registry entry exposes only the multicall `coreutils` binary.
- mise's `filter_bins` option is documented for the github backend, not conda (`conda.md:107`).

**Risks before adding these pins:**
- **`conda:coreutils` puts about 101 GNU commands** (`ls`, `date`, `stat`, `readlink`, …) ahead of the BSD versions whenever you work in this repo on the host. knowledge-base accepted that trade-off. It also moves the host closer to CI and the container, which are GNU. Run lint, pytest, `verify` and `hook-selfcheck` under the new PATH before shipping.
- **A root `node` pin also affects the CI lint job,** which runs `mise install --locked` at the repo root. Lock it with a scoped `mise run lock -- "node"` and run `mise run pin-parity`: the image has `node = "latest"` at `.devcontainer/mise-system.toml:22`. The Renovate task's per-task `node 24` pin (`mise.toml:939`) is unaffected.
- **Also add `.firecrawl/` to `.gitignore`.**

## Comparison with knowledge-base

| Tool | dotfiles | knowledge-base (`mise.toml` line) |
|---|---|---|
| firecrawl-cli | 1.24.3 | 1.23.3 (:242), behind |
| ctx7 | 0.5.11 | 0.5.9 (:241), behind |
| @openai/codex | 0.154.0 | 0.154.0 (:239) |
| antigravity-cli | 1.2.8 | 1.2.2 (:240), behind |
| gh | — (user-global 2.101.0) | 2.98.0 (:157) |
| conda:coreutils | — | 9.11 (:247), pinned for exactly this `timeout` shim problem |
| conda:ffmpeg | 9.0.1 (macOS) | 9.0.1 (:52) |
| python / uv | 3.14.7 / 0.12.13 | 3.14.7 (:44) / 0.12.8 (:45) |
| node | not pinned | not pinned |

## What I didn't check

- **fable-orchestrator doctor:** not run, because it makes live, billable codex/grok calls. Its `timeout` problem is inferred from code, and the same pattern was confirmed live on Antigravity.
- **last30days doctor:** not run live, because it rewrites `~/.config/last30days/doctor-cache.json`. The cached result (2026-09-15, engine 3.24.0) is older than the installed 3.25.0: every external command "available", web "degraded". I re-checked its binaries directly today (yt-dlp, gh, the three pp-cli tools, ffmpeg all rc=0).
- **The antigravity doctor's working run** (with GNU `timeout` on PATH) made one tiny live model call ("--model takes effect").
- **Latest versions** for jq, python and uv weren't re-checked; `pin-parity` and Renovate cover those.

## GitHub repos touched

- [firecrawl/cli](https://github.com/firecrawl/cli) — v1.24.3 release assets and checksum; standalone darwin binary tested in the scratchpad (since deleted)
- [upstash/context7](https://github.com/upstash/context7) — release tags; `ctx7@0.5.x` has 0 assets, so npm only; context7 plugin read from local cache
- [openai/codex](https://github.com/openai/codex) — latest release rust-v0.155.1; codex plugin read from local cache
- [google-antigravity/antigravity-cli](https://github.com/google-antigravity/antigravity-cli) — latest release 1.2.8
- [yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp) — latest release 2026.08.19
- [cli/cli](https://github.com/cli/cli) — latest gh v2.101.0
- [uutils/coreutils](https://github.com/uutils/coreutils) — latest 0.12.0 (multicall only)
- [aquaproj/aqua-registry](https://github.com/aquaproj/aqua-registry) — `pkgs/uutils/coreutils/registry.yaml` `files:` exposes only `coreutils`
- [jdx/mise](https://github.com/jdx/mise) — docs via the knowledge-base offline copy (`backends/github.md` filter_bins/bin/rename_exe, `aqua.md` symlink_bins, `conda.md:107`)
- [mar3co/fable-orchestrator](https://github.com/mar3co/fable-orchestrator) — plugin 1.21.0 scripts (local cache)
- [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) — plugin 3.25.0 engine and setup wizard (local cache)
- [exa-labs/exa-mcp-server](https://github.com/exa-labs/exa-mcp-server) — exa plugin 3.4.1 manifest (local cache)
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — plugin 3.17.2 hooks (local cache)
- [mattpocock/skills](https://github.com/mattpocock/skills) — plugin 1.2.3 skills (local cache)
- [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) — skill-creator and output-style plugins (local cache)
