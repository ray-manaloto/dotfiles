---
okf_version: "0.2"
type: "report"
title: "Tools: from spike probes to jbax and jbctl"
description: "The spike's probes and scripts, and the tracked tools that replace them (swift/ jbax, python/jbctl)."
resource: "swift/ and python/jbctl/"
version: "2026-11-05"
timestamp: "2026-11-05T23:00:00Z"
status: "draft"
stale_after: "2026-12-05T00:00:00Z"
tags: [tools, swift, python, jbctl, jbax, rea, agent-desktop]
---

# Tools

## Tracked (issue #502)

| tool | does | background? |
|---|---|---|
| `swift/` **jbax** | Swift CLI for background AX on JBR/Swing: `windows`, `focus-owner`, `combo`, `select` (guarded AXSelected commit, row 0 only), `press`, `popup list/select`. JSON out; exit codes 0 ok, 1 not found, 2 guard refused, 3 verify failed, 4 not reachable in background, 5 AX error | yes |
| `python/jbctl` | recipe runner and CLI: rea and agent-desktop backends, Settings open/goto/press, router-direct, the DIRECT check (MCP tools/list), and the rea helper patch | yes, except opening Settings |

## Spike probes (replaced)

| spike tool | replaced by |
|---|---|
| `selpoke`, `set-direct-bg` | `jbax select` |
| `popupitems` | `jbax popup` |
| `axpressbtn` | `jbax press --window frame` |
| `comboattrs` | `jbax combo` |
| `focusowner` | `jbax focus-owner` |
| `open-settings.sh`, `check-direct.sh`, `mcpcount.sh`, `rea-patch.sh` | jbctl subcommands (zero bash) |
| `pidclick` | dropped: an inactive CLion ignores pid-posted clicks |
| `axwatch`, `inputtap` | recording only; not tracked |
