---
okf_version: "0.2"
type: "report"
title: "Other strict:false and inline-component plugins under the Directory"
description: "Every strict:false marketplace entry in the local marketplaces, cross-referenced with the Anthropic Directory listings, and what a Directory install of each probably loads."
package: "npm:@anthropic-ai/claude-code"
version: "2.1.317"
timestamp: "2026-11-03T21:00:00Z"
status: "draft"
tags: [claude-code, plugins, anthropic-plugin-directory, strict, skills, mcpServers]
sources:
  - id: directory-cache
    resource: "file:~/.claude/plugins/plugin-directory-cache-v2.json"
    title: "Directory listing cache, 2026-11-03"
  - id: local-marketplaces
    resource: "file:~/.claude/plugins/marketplaces/*/.claude-plugin/marketplace.json"
    title: "39 local marketplace copies"
  - id: cc-94762
    resource: "https://github.com/anthropics/claude-code/issues/94762"
    title: "Inline skills under strict:false not registered (open)"
  - id: cc-78604
    resource: "https://github.com/anthropics/claude-code/issues/78604"
    title: "Stale or synthesized plugin.json shadows entry components (open)"
---

# Other strict:false and inline-component plugins under the Directory

The Directory's synthesized entry drops every component (see [root cause](root-cause.md), step 3). Any listed plugin
whose components live only in its marketplace entry is exposed to the same gap. Every `strict: false` entry in the
local marketplaces was matched to Directory listings by repository URL and path:

| Plugin (marketplace) | Inline components | Directory listing | Probable Directory result |
|---|---|---|---|
| 12 `*-lsp` (claude-plugins-official) | lspServers | yes | 0 LSP servers (**observed**) |
| amd-skills (claude-plugins-official) | skills: 5 named paths | `amd/skills#skills` @ `6916fb37` | The folder holds 8 skill directories and neither a manifest nor a nested `skills/`. Probably 0 skills, or a different set from the 5 named. Not verified |
| learn-with-coursera (official, community, knowledge-work) | skills `./learn-with-coursera` | `coursera/skills#skills` @ `ac28fd6e` | Same shape as amd-skills. Not verified |
| document-skills, example-skills, claude-api, academy-guide, discernment-nudge (anthropic-agent-skills) | skills: each a different subset of `./skills/*` | one listing (`document-skills`) at the repo root of anthropics/skills @ `33375500` | The root has only `.claude-plugin/marketplace.json` and `skills/` (19 skills). Auto-discovery would likely load all 19 under one plugin instead of 4, and the other four plugins have no listing. Not verified |
| testdino, tres-finance-plugin (claude-community) | mcpServers | none | Not reachable through the Directory |
| eli5, html-plan, next-steps, quickdesign and others (claude-community) | none inline | none | Not affected |

The unverified rows need a real install through the Directory, ideally in a throwaway Claude Code config. This
research was read-only and did not install anything.

Related failures outside the Directory:
- [claude-code#94762](https://github.com/anthropics/claude-code/issues/94762): inline `skills` under
  `strict: false` are not registered.
- [#78604](https://github.com/anthropics/claude-code/issues/78604): comments of 2026-10-01 and 2026-10-24 report that
  Desktop-synthesized `plugin.json` files broke `strict: false` skill plugins with "conflicting manifests" until
  Desktop 3.1623.0 stopped writing them.
