---
okf_version: "0.2"
type: "concept"
title: "Upgrading codebase-memory-mcp"
description: "Why CBM has an exact pin that bulk upgrades skip, the manual upgrade order that keeps one build per account, what the forced-drain installer flags do to indexes, and why upgrades stay manual."
package: "github:DeusData/codebase-memory-mcp"
version: "0.12.1"
timestamp: "2026-11-04T02:59:21Z"
status: "draft"
tags: [codebase-memory-mcp, mise, upgrade, daemon]
sources:
  - id: mise-upgrade
    resource: "https://github.com/jdx/mise/blob/v2026.11.0/src/cli/upgrade.rs"
    title: "--bump rewrites pins; pin = true rewrites latest (lines 566-590)"
  - id: cbm-cli
    resource: "https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/src/cli/cli.c"
    title: "install quiesce and --reset-indexes (lines 10642-10667, 11192-11229, 11557-11561)"
  - id: mise-lock
    resource: "https://github.com/jdx/mise/blob/v2026.11.0/src/cli/lock.rs"
    title: "mise lock locks without installing (lines 170-180); --global selects global configs (lines 2203-2222)"
  - id: adr-0001
    resource: "repo:docs/adr/0001-cbm-upgrade-trial-pr-apply.md"
    title: "Superseded: the upgrade pipeline was dropped for the manual upgrade"
---

# Upgrading codebase-memory-mcp

## Why upgrades are deliberate

Every CBM process in a runtime namespace (one per account in the default setup) must be the same build with the
same cache root. An open Claude or Codex
session holds its server process, and so the old build, until it ends. A pin change while sessions are open leaves
old and new builds side by side, and the daemon refuses the mismatch (`fingerprint_mismatch`, logged in
`~/.cache/codebase-memory-mcp/logs/daemon-conflicts.ndjson`).

So the pin is exact (`version = "0.12.1"`) and kept out of bulk upgrades:
- Plain `mise upgrade` keeps exact pins, and `auto_update` never updates them.
- `mise upgrade --bump` rewrites pins (with `pin = true` even `latest` becomes exact). The routine update script
  (`~/.config/mise/scripts/update_mise.py`, not yet tracked here) passes
  `--exclude github:DeusData/codebase-memory-mcp`. Checked with a dry run on a 0.12.0 scratch pin: bumped without
  the exclusion, untouched with it.
- `minimum_release_age = "0s"` stays; a delay is not a hold.
- New releases: `mise outdated --bump github:DeusData/codebase-memory-mcp`, or the `updates` set in
  `data/saved-searches.json`. `update:check` does not show bump-only updates.

## Manual upgrade

Upgrades are manual, and stay that way: they are rare and a rollback is the same steps with the previous
version. The trial-PR pipeline of ADR 0001 (spec #412) was dropped.

1. Read the release notes for the new tag; note index-format changes and installer changes.
2. Close every Claude and Codex session (and anything else that runs CBM).
3. Stop the old daemon with the old binary: `codebase-memory-mcp daemon stop` through the launcher, before the pin
   moves. It refuses while sessions are attached. Confirm no `--cbm-daemon-internal` process is left.
4. Bump the pin in `unix/home/.config/mise/config.toml`, apply it, and run `mise install`. The global link moves.
5. `mise run //cbm:install`, never CBM's own `install`, `update` or `install.sh` (see `install.md`) (the installer rewrites the agent setup for the new build; configs keep the launcher
   path).
6. Start one session; check one executable path in `ps`, no new conflict lines, and the tools in `/mcp`.
7. Reindex each project once: index-format changes force a full rebuild (0.12.0, and again 0.12.1).
8. Codex: re-trust in `/hooks` if it lists the CBM hooks as changed.

The daemon runs from the resolved install folder (`~/.local/share/mise/installs/codebase-memory-mcp-<hash>/`), not
from the link. Moving the link does not move a running daemon, which is why step 3 comes before step 4.

## Installer facts

- `install --skip-binary` alone does not drain sessions: it quiesces only when it validates a binary or deletes
  indexes (`quiesce_required = has_binary_validator || delete_indexes`, cli.c:11557-11561).
- `install --skip-binary --reset-indexes -y` is CBM's own forced drain, and it keeps every index. The reset flag
  makes the installer stop every CBM process; it drains only when at least one index exists (cli.c:10642-10645).
  With `--skip-binary`, the install returns (cli.c:11192-11195) before the index deletion (cli.c:11222-11229). A
  reindex then refreshes the kept indexes. Without `--skip-binary`, a successful reset install deletes every
  index under the cache; a failed activation or cleanup can leave indexes behind (cli.c:11215-11232).
- A newer build drains an older daemon by itself only when that daemon is permanent (`daemon start`), not the
  default session-managed one.
- A mise tool `postinstall` runs before the runtime links move, from `/`, with no stdin, under the 30-minute
  `tool-update` service cap. It cannot read release notes first, so it is the wrong place for the protocol.
- Open sessions after a drain: this Claude Code 2.1.317 session's CBM server was killed mid-session (the retired
  0.11.0 setup). Afterwards it was listed as failed to connect, and its MCP log has no reconnect attempt. Claude Code
  offers `/mcp reconnect <server>|all`; Codex needs a restart. Automatic respawn should not be assumed.
- The `//cbm:install` checks expect exactly what 0.12.1 writes: 7 Claude hooks with a 5 s timeout, 2 Codex hooks,
  each agent's tool profile and the 13 read-only analysis tools. A release that adds a tool, renames a hook trigger
  or changes a timeout fails them even when the setup works: read the failure against the release notes, then
  update the constants in `python/cbm/src/cbm/setup.py`.
- Codex re-trust: the configs name the launcher, so hook commands do not change on upgrade. Whether Codex still
  asks for a re-trust after the installer rewrites `hooks.json` is untested.
