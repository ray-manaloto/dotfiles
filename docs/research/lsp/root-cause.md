---
okf_version: "0.2"
type: "report"
title: "Root cause: the Anthropic Directory drops marketplace-entry components"
description: "Why the official *-lsp plugins load 0 LSP servers through the Anthropic Directory and work through claude-plugins-official, traced through Claude Code 2.1.317."
resource: "https://github.com/anthropics/claude-plugins-official/issues/379"
package: "npm:@anthropic-ai/claude-code"
version: "2.1.317"
timestamp: "2026-11-03T21:00:00Z"
status: "draft"
stale_after: "2026-12-03T00:00:00Z"
tags: [claude-code, plugins, lsp, anthropic-plugin-directory, strict, lspServers]
sources:
  - id: cc-binary
    resource: "file:~/.local/share/claude/versions/2.1.317"
    title: "Claude Code 2.1.317 native binary (Mach-O arm64); offsets are into `strings -n 6` of it"
  - id: directory-cache
    resource: "file:~/.claude/plugins/plugin-directory-cache-v2.json"
    title: "Directory listing cache, schemaVersion 2, fetched 2026-11-03T19:28:01Z, 3604 listings"
  - id: official-marketplace
    resource: "https://github.com/anthropics/claude-plugins-official/blob/a2e251d9b97b909bf728b3e84fc8d17e6aba0063/.claude-plugin/marketplace.json"
    title: "claude-plugins-official marketplace.json at HEAD a2e251d9 (2026-11-03)"
  - id: cpo-379
    resource: "https://github.com/anthropics/claude-plugins-official/issues/379"
    title: "All LSP plugins missing .lsp.json (open)"
  - id: cpo-378
    resource: "https://github.com/anthropics/claude-plugins-official/pull/378"
    title: "Add missing .lsp.json files (closed unmerged, contributor policy)"
---

# Root cause: the Anthropic Directory drops marketplace-entry components

**The Directory never sees the marketplace entry, so `strict: false` and `lspServers` cannot reach the install.
That is how the Directory works by design, not a regression; the defect is that the official LSP plugins keep their
server config only in a marketplace entry.**

## Observed

- After the 12 LSP plugins were switched to `@anthropic-plugin-directory`, `/reload-plugins --force` reported
  "0 plugin LSP servers".
- Switching back to `@claude-plugins-official` fixed the tested case: a headless LSP `documentSymbol` call on a
  `.py` file (pyright-lsp) returned symbols. The other 11 plugins were not called.
- The Directory cache copies (`~/.claude/plugins/cache/anthropic-plugin-directory/<n>-lsp/<sha>-<hash>/`) hold
  only `LICENSE` and `README.md`.

## Packaging upstream

- In anthropics/claude-plugins-official all 12 LSP entries are `"strict": false` and carry `lspServers` inline.
  Example clangd: `command: clangd`, `args: ["--background-index"]`, nine extensions.
- The plugin folders (`plugins/clangd-lsp`, `plugins/pyright-lsp`, …) contain only `LICENSE` and `README.md`, at
  HEAD `a2e251d9` as well. The LSP plugins were added inline-only in `be56d711` (2025-12-19); the folders' last
  change is `aecd4c85` (2026-02-20, LICENSE files).
- The Directory lists all 12, reviewed by Anthropic and pinned at `reviewed_commit` `ea0a38e1d671` (lua-lsp at
  `1aa8f02ec832`).

## Trace through Claude Code 2.1.317

Offsets are byte offsets into `strings -n 6` of the binary. To reproduce, search the dump for the quoted fragment.

1. **The listing has no component fields.** The listing schema accepts only `id, name, summary, description,
   release.version, publisher.name, links.documentation, surfaces, source{type:"directory", repository{url, path,
   reviewed_commit}}, checks.review` (offset ≈41580200, near `reviewed_commit:o().optional()`).
2. **A listing becomes a folder-at-commit source.** It turns into `{source:"git-subdir", url, path, sha}`, or
   `{source:"url", url, sha}` when the listing has no path (offset ≈41604300, fragment
   `{source:"git-subdir",url:c,path:g,sha:w}`). For clangd-lsp that is `plugins/clangd-lsp` at `ea0a38e`.
3. **The synthesized entry is strict and component-free.** The built-in `anthropic-plugin-directory` marketplace
   (`plugin-directory-marketplace.json`, owner "Anthropic") builds each entry from the listing alone:
   `{name, source, displayName?, description?, version?, author?, homepage?, repository, strict:!0}` (offset
   ≈41609544). `strict` is hard-coded to true, and no `lspServers`, `mcpServers`, `skills`, `hooks`, `commands` or
   `agents` exist to copy.
4. **Without a plugin.json, the entry becomes the manifest.** When the installed folder has no `plugin.json`, the
   loader canonicalizes the marketplace entry into the manifest (offset ≈30036950, fragment
   `if(!He){let Ge=$Se(e,"marketplace-entry"`). For a Directory install that is the entry from step 3, with no
   `lspServers`.
5. **The LSP loader finds nothing.** Servers come from the manifest's `lspServers` and from a plugin-root `.lsp.json`
   (offset ≈25974956, `Sho(e.path,".lsp.json")`; `.lsp.json` is also a plugin-root marker at ≈23142374). The
   Directory copy has neither, so 0 servers load.

Through `claude-plugins-official`, step 4 receives the real entry, which still has `lspServers`, so the same folder
loads 1 server.

## Status

- **Known since February 2026 as a packaging bug.**
  - [claude-plugins-official#379](https://github.com/anthropics/claude-plugins-official/issues/379) is open; its
    last comment (2026-10-06) reports it still broken on 2.1.288.
  - The fix, [PR #378](https://github.com/anthropics/claude-plugins-official/pull/378), was auto-closed on
    2026-02-11: that repository accepts contributions only from Anthropic staff.
  - [#5667](https://github.com/anthropics/claude-plugins-official/issues/5667) is open for rust-analyzer-lsp and
    clangd-lsp.
- **The same mechanism breaks other copy paths:** the Desktop `--plugin-dir` copy
  ([claude-code#99117](https://github.com/anthropics/claude-code/issues/99117)), Desktop SSH sync (#102145), a
  synthesized `plugin.json` on install (#93474) and a stale manifest (#78604). All four are open.
- **No report names the Directory path, and no fix is visible.** Upstream HEAD has no `.lsp.json` and no open PR
  adds one. The changelog through 2.1.317 has no entry for it.
- **A fix upstream is not enough on its own.** Even after files land, the Directory serves the listing's
  `reviewed_commit`, so each listing must also be bumped past `ea0a38e` (or `1aa8f02` for lua-lsp).

## Unknown

Whether Anthropic will add component fields to the listing API or keep folder-only installs is not public.
