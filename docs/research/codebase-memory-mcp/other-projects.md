---
okf_version: "0.2"
type: "report"
title: "How other projects set up codebase-memory-mcp"
description: "Public dotfiles and agent setups found by 73 GitHub searches on 2026-11-03: binary sources, how harness configs are written, the same-build rule, which hooks are kept, upgrade practice, and where this setup differs."
package: "github:DeusData/codebase-memory-mcp"
version: "0.12.1"
timestamp: "2026-11-03T23:50:00Z"
status: "draft"
stale_after: "2026-12-03T00:00:00Z"
tags: [codebase-memory-mcp, dotfiles, mise, nix, hooks, research]
sources:
  - id: saved-searches
    resource: "repo:docs/research/codebase-memory-mcp/data/saved-searches.json"
  - id: overdrive
    resource: "https://github.com/kevinold/overdrive"
  - id: technicalpickles
    resource: "https://github.com/technicalpickles/dotfiles"
  - id: sini
    resource: "https://github.com/sini/nix-config"
  - id: llmenv
    resource: "https://github.com/phaedrus1992/llmenv"
---

# How other projects set up codebase-memory-mcp

None of the 73 searches run found a public repository with exactly this setup (one mise-pinned CBM for Claude, Codex,
Antigravity and OpenCode on one Mac). Every link is to the file at the commit of its search hit; the claims are
from reading those files, not from running them.

## Binary source and configs

| Repository | Binary | Configs | Same-build rule |
|---|---|---|---|
| [kevinold/overdrive](https://github.com/kevinold/overdrive/blob/36fb70c72aea5d6f2999359348a48082156fddfb/scripts/bootstrap.sh) ([mise.toml](https://github.com/kevinold/overdrive/blob/36fb70c72aea5d6f2999359348a48082156fddfb/mise.toml), [inventory](https://github.com/kevinold/overdrive/blob/36fb70c72aea5d6f2999359348a48082156fddfb/docs/harness-inventory.md)) | mise `github:` 0.11.0 | one bootstrap script runs `claude mcp add --scope user … mise exec github:…@0.11.0 -- codebase-memory-mcp` and `codex mcp add`, plus Gemini | the exact version in every launch command; a test fails when a config drifts from `mise.toml` |
| [technicalpickles/dotfiles](https://github.com/technicalpickles/dotfiles/blob/78c96ea0d4824d205bb8cd8cbb0aeeafc7124b28/config/mise/conf.d/dotfiles.toml) ([hooks](https://github.com/technicalpickles/dotfiles/blob/78c96ea0d4824d205bb8cd8cbb0aeeafc7124b28/claude/roles/work.jsonc), [reindex](https://github.com/technicalpickles/dotfiles/blob/78c96ea0d4824d205bb8cd8cbb0aeeafc7124b28/bin/cbm-reindex), [renovate](https://github.com/technicalpickles/dotfiles/blob/78c96ea0d4824d205bb8cd8cbb0aeeafc7124b28/renovate.json)) | mise `github:` 0.11.0, commented "all running instances must be the same build; bump, then restart agents" | hooks hand-written with the bare command, "because `install` writes machine-specific binary paths"; scripts use the mise shim | Renovate never automerges CBM; a reindex script stops the old daemon after a bump |
| [jeffbski/wait-on](https://github.com/jeffbski/wait-on/blob/fae57e2e074a241551a8a5e9089e48099247ac41/.mcp.json) ([reindex](https://github.com/jeffbski/wait-on/blob/fae57e2e074a241551a8a5e9089e48099247ac41/scripts/reindex-codebase-memory.sh)) | mise `github:` 0.11.0 | project `.mcp.json` runs `mise exec -- codebase-memory-mcp`; a SessionStart hook reindexes | none |
| [jellydn/my-ai-tools](https://github.com/jellydn/my-ai-tools/blob/8f92057485e166274ccf3a83f6f60caf0e2d5e30/configs/codex/config.toml) ([OpenCode](https://github.com/jellydn/my-ai-tools/blob/8f92057485e166274ccf3a83f6f60caf0e2d5e30/configs/opencode/opencode.json)) | binary on PATH | bare name for Codex and OpenCode; keeps the installer's Claude hook | one binary |
| [sini/nix-config](https://github.com/sini/nix-config/blob/1fc1b29287b28b6347c09ad7b3ad60850b3cdcb3/modules/den/aspects/applications/dev/ai/mcp/codebase-memory-mcp.nix), [derangga/dotfiles](https://github.com/derangga/dotfiles/blob/694e15d9c6656624ca76f52fe8d77c1c98ab64c9/modules/llm-agents/codebase-memory-mcp.nix), [NixOS/nixpkgs](https://github.com/NixOS/nixpkgs/blob/ca481e4480aafcaae45fa36dcbbeb8e94a060c33/pkgs/by-name/co/codebase-memory-mcp/remove-install-update.diff) | nix (flake input; release tarball with the v0.12.1 sha256) | home-manager renders hooks with the store path | nixpkgs patches out `install`, `uninstall`, `update`; sini notes an open session keeps the old build across a switch |
| [harlanljones/dotfiles](https://github.com/harlanljones/dotfiles/blob/ff7687dcd30a6b14a3c7651ccddf4951e0d9facb/dot_gemini/config/mcp_config.json.tmpl) | install.sh (`~/.local/bin`) | chezmoi writes the absolute path for Antigravity | one path |
| [phaedrus1992/llmenv](https://github.com/phaedrus1992/llmenv/blob/14d52e4d80a38b456ecdce1f8ff6be0fac460923/docs/design/issue-2155-cbm-augment-hooks.md) | its own renderer | renders MCP and, opt-in, hooks; its doctor warns on duplicate installer hooks | adds a `CBM_CACHE_DIR` prefix so hooks see the server's cache |

Counts across GitHub: Codex `mcp_servers.codebase-memory-mcp` 227, `opencode.json(c)` 201, `.mcp.json` 133,
`"github:DeusData/codebase-memory-mcp"` 106 (mostly nix), `mcp_config.json` 28, `npm:codebase-memory-mcp` 23,
`mise.toml` 15. These searches found no public script that runs `install --skip-binary` and no real config that
uses the upstream Claude plugin, which exists only on upstream `main`.

## Hooks

| Repository | Kept | Dropped |
|---|---|---|
| technicalpickles | all events, `timeout: 5`, errors ignored | installer shim, replaced by the bare command |
| several dotfiles (283 hits for the installer hook name) | installer hooks as written | none |
| sini | PreToolUse Grep and Glob, its own reminders | Bash and Read augmentation |
| llmenv | augmentation opt-in, default off: "users choose that cost"; flags a median above 300 ms | installer shim |
| nixpkgs | none (installer removed) | all |

Problems on record upstream: per-call hashing of the ~330 MB executable (#1335, #2683, #2834); Codex hooks need
`/hooks` trust and config-ownership bugs (#2228, #2435); OpenCode augmentation bugs (#1167, #2618, #1737);
Antigravity gets MCP only, at the legacy Gemini path (#1161, #1797); the installer aborts on symlinked configs
(#2671).

## Upgrades

- "Bump, then restart agents", with the old daemon stopped (technicalpickles) or tolerated (sini).
- Renovate's mise manager with a 7-day minimum release age and no automerge (technicalpickles).
- Stable launch paths in use: `mise exec github:…@<ver> --`, `mise exec --` (works only inside a folder that pins
  CBM), the mise shim (follows the current folder's pins), `~/.local/bin`, the bare name on PATH. Upstream #2856
  (open) lists the same options.

## Where this setup differs, and why

- **The installer is used.** Others avoid it because of machine-specific paths and #2722. Here `--dir` points it
  at a version-free launcher, which fixes the path problem, and the macOS `--skip-binary` bug is worked around
  (see `install.md`).
- **Launcher, not `mise exec`.** The mise global runtime link follows only the global config, so no project pin
  can move it, and it costs no `mise exec` start-up per hook call.
- **All hooks kept for now.** The research advised leaving augmentation off until measured; the owner chose the
  full install first, with a token and latency A/B to decide (see `effectiveness.md`).
- **Manual upgrades for now**, with automation as its own follow-up (see `upgrades.md`).
