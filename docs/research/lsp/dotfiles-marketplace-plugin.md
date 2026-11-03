---
okf_version: "0.2"
type: "concept"
title: "LSP in a dotfiles marketplace plugin"
description: "What a marketplace plugin built in dotfiles, loaded by dotfiles and any other project, must do so its language servers load; the cross-route claims are inferred, not yet tested."
package: "npm:@anthropic-ai/claude-code"
version: "2.1.317"
timestamp: "2026-11-03T21:00:00Z"
status: "draft"
tags: [claude-code, plugins, lsp, dotfiles, marketplace]
sources:
  - id: root-cause
    resource: "repo:docs/research/lsp/root-cause.md"
  - id: cc-53399
    resource: "https://github.com/anthropics/claude-code/issues/53399"
    title: "A plugin-root .lsp.json works; inline lspServers alone is ignored"
  - id: cpo-379
    resource: "https://github.com/anthropics/claude-plugins-official/issues/379"
    title: "Comment of 2026-08-26: lspServers in .claude-plugin/plugin.json registers"
---

# LSP in a dotfiles marketplace plugin

**LSP should work, as long as each plugin carries its server config inside its own folder.** The evidence:
- the 2.1.317 source, which reads `.lsp.json` and `plugin.json` `lspServers` from the installed folder;
- third-party reports of `.lsp.json` plugins working (claude-code#53399, claude-plugins-official#379);
- one real probe on this Mac: a headless `documentSymbol` call on a `.py` file through claude-plugins-official.

No dotfiles-built plugin has been tested yet. The Desktop `--plugin-dir`, Desktop SSH and Directory routes are
inferred from the source and from the issue reports, and have not been verified here.

## Requirements

1. **Config in the folder.** Put a `.lsp.json` at the plugin root, or `lspServers` in `.claude-plugin/plugin.json`.
   Claude Code 2.1.317 reads both from the installed folder ([root cause](root-cause.md), step 5). Real use confirms
   it: Piebald, claude-code#53399 and the claude-plugins-official#379 comments.
2. **Never rely on the marketplace entry.** Do not depend on `lspServers` written only in the marketplace entry with
   `strict: false`. That is the official plugins' layout, and the Directory, Desktop `--plugin-dir` and SSH copies
   all drop it.
3. **Server binaries on Claude Code's PATH.** Claude Code starts servers by command name (`clangd`,
   `pyright-langserver`, …). With mise-installed servers, Claude Code needs mise's shims or bin directories on its
   PATH, including when it is started by the Desktop app or over SSH. Otherwise a server fails with "not found or in
   an unsafe location" (claude-code#75612, #73961).
4. **One server per file extension.** Disable the official plugin that covers the same extensions (for example
   `clangd-lsp` and `pyright-lsp`); otherwise the two compete and Claude Code picks one silently (#64422, #101008).
   This is a plugin change, so it waits for the owner's OK.
5. **One plugin per language or language group.** Each project then enables only the servers it uses, instead of one
   plugin starting every server everywhere.
6. **Fix the known defaults.** Add `.hh` to the clangd extensions (claude-plugins-official#2284). Decide whether to
   keep, bound or drop `--background-index`, which grows memory without limit per session (claude-code#101351).

## Done when

- `/reload-plugins` reports a non-zero "plugin LSP server" count.
- An LSP `documentSymbol` call returns symbols for a `.cpp` and a `.py` file.
- Both checks also pass in a second project, which covers the "any project" case.

## Limit

Folder-held config should fix LSP for the dotfiles marketplace on every install route; this is inferred and stays
unverified until the Done-when checks pass on each route the owner uses. It does not fix the official plugins under the
Directory; only an upstream packaging change does (see [recommendations](recommendations.md)).
