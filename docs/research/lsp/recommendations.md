---
okf_version: "0.2"
type: "decision-record"
title: "Recommendations: LSP plugins after the Directory move"
description: "Keep the official LSP plugins on claude-plugins-official, file one claude-code issue for the Directory path, keep a local-marketplace fallback, and do not adopt Piebald claude-code-lsps."
package: "npm:@anthropic-ai/claude-code"
version: "2.1.317"
timestamp: "2026-11-03T21:00:00Z"
status: "draft"
tags: [claude-code, plugins, lsp, decisions]
sources:
  - id: root-cause
    resource: "repo:docs/research/lsp/root-cause.md"
  - id: piebald
    resource: "repo:docs/research/lsp/piebald-claude-code-lsps.md"
---

# Recommendations: LSP plugins after the Directory move

Each of these is a recommendation. Any plugin install, switch, enable or disable waits for the owner's OK.

1. **Keep the 12 LSP plugins on `claude-plugins-official` for now.**
   - The Directory route loads 0 LSP servers; the [root cause](root-cause.md) explains why. The official route
     was confirmed by one real `documentSymbol` call on a `.py` file (pyright-lsp); the other 11 were not called.
   - Move a plugin to the Directory only when its own listing passes, checked per listing for all 12:
     - Its `reviewed_commit` in `~/.claude/plugins/plugin-directory-cache-v2.json` has moved past `ea0a38e`
       (`1aa8f02` for lua-lsp).
     - The plugin folder carries `.lsp.json` **at that `reviewed_commit`**, not just on `main`. Check with
       `gh api 'repos/anthropics/claude-plugins-official/contents/plugins/<name>?ref=<reviewed_commit>'`.
2. **File one issue on anthropics/claude-code.** This is outward-facing, so the owner decides. claude-plugins-official
   refuses outside PRs (#378), so the channels are a claude-code issue or a comment on claude-plugins-official#379.
   - Title: "Anthropic Directory installs of the official `*-lsp` plugins load 0 LSP servers: the synthesized
     `anthropic-plugin-directory` entry is `strict: true` without the official entry's `lspServers`".
   - Body: the 5-step trace at 2.1.317, the 12 listings and their `reviewed_commit`s, and the probable skills cases
     from [affected plugins](affected-plugins.md). Link #379, #5667, #99117, #102145 and #93474.
   - Ask for either:
     - (a) a `.lsp.json` in each official folder, plus a listing bump; or
     - (b) the Directory honouring the source marketplace's entry for Anthropic-reviewed claude-plugins-official
       listings.
3. **Fallback, if the Directory becomes forced or the official marketplace is retired.** Use a local directory-source
   marketplace in dotfiles with one folder per server, each holding `.lsp.json`. Because the folder holds the config, it should
   survive every copy path (inferred from the source, not tested), and it needs no third-party code. The [dotfiles marketplace plugin](dotfiles-marketplace-plugin.md) page lists its
   requirements.
4. **Do not adopt Piebald claude-code-lsps.** Its packaging is right, but recommendation 3 gives the same result
   without a dormant, unlicensed third-party repository. If it is ever enabled, first disable the official plugin
   that covers the same extensions.
