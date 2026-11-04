---
okf_version: "0.2"
type: "report"
title: "Piebald-AI/claude-code-lsps"
description: "How the claude-code-lsps marketplace (38 plugins) ships LSP config, its maintenance, overlap with the official LSP plugins and its risks; verdict: not needed."
resource: "https://github.com/Piebald-AI/claude-code-lsps"
timestamp: "2026-11-03T21:00:00Z"
status: "draft"
tags: [claude-code, plugins, lsp, piebald, claude-code-lsps]
sources:
  - id: piebald-repo
    resource: "https://github.com/Piebald-AI/claude-code-lsps/tree/92afe66527"
    title: "Piebald-AI/claude-code-lsps at 92afe665 (2026-07-25)"
  - id: piebald-marketplace
    resource: "https://github.com/Piebald-AI/claude-code-lsps/blob/92afe66527/.claude-plugin/marketplace.json"
    title: "marketplace.json, 38 plugins"
---

# Piebald-AI/claude-code-lsps

## How it ships LSP config

- **The config is in the folder.** Each plugin folder carries its own `.lsp.json` and a root `plugin.json`.
- **The marketplace entry repeats it inline.** Each entry also carries `lspServers`, and no entry is `strict: false`
  (0 of 38).
- **Example, `clangd/.lsp.json`:** server key `cpp`, `command: clangd`, `args: []`, `transport: stdio`,
  `maxRestarts: 3`. Its extensions include `.hh` and `.c++`, which the official clangd-lsp lacks.
- **Why it survives:** Claude Code reads a plugin-root `.lsp.json` (see [root cause](root-cause.md), step 5), so the
  config should survive every copy path: CLI cache, Desktop `--plugin-dir`, SSH sync and a Directory install.
  This is inferred from the source; only the CLI-cache route is backed by the user reports, and none was re-tested
  here.

## Maintenance

- **Activity.** 522 stars and 61 forks. Last push 2026-07-25: three plugins added by an outside contributor. Earlier
  commits on 2026-06-17 and 2026-06-01. 46 PRs in total, none open.
- **Open issues.** Seven, all about Windows spawning, extension routing and the LSP tool schema: #84, #75, #74, #72,
  #69, #67, #62. Issues #7–#19 (2025-12, "missing lspServers config in marketplace.json") were fixed by 2026-01-30.
- **No licence.** The repository has no LICENSE file; the plugin manifests name the upstream servers' licences.
- **Not in the Directory.** It is not listed in the Anthropic Directory.

## Overlap with the official LSP plugins

- **Coverage.** It covers 11 of the 12 official languages, all but Lua: clangd, pyright/basedpyright/ty, vtsls or
  typescript-language-server, gopls, rust-analyzer, jdtls, kotlin-lsp, ruby-lsp, php-lsp/phpactor, swift-lsp and
  omnisharp. That is out of 38 plugins in all, including Vue, Svelte, Terraform and LaTeX.
- **Conflicts with the official plugins.** Server keys differ (`cpp` against `clangd`), so enabling both for one
  extension makes them compete. Claude Code resolves the clash silently
  ([claude-code#64422](https://github.com/anthropics/claude-code/issues/64422), closed;
  [#101008](https://github.com/anthropics/claude-code/issues/101008), open).

## Risks

- **Little upkeep.** One maintainer, and the repository has been quiet for over three months.
- **No licence.** The repository itself has no licence.
- **Third-party code.** Third-party commands run as the user.

## Verdict

**Not needed.** The official marketplace works today for the tested Python route. If it stops being an option, a local marketplace whose folders
carry `.lsp.json` (see [recommendations](recommendations.md)) gives the same result with no third-party dependency.
