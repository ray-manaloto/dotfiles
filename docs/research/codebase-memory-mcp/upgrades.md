---
okf_version: "0.2"
type: "concept"
title: "Upgrading codebase-memory-mcp"
description: "Why CBM has an exact pin that bulk upgrades skip, the manual upgrade order that keeps one build per account, the forced-drain installer flag that wipes every index, and the open questions for the upgrade automation PR."
package: "github:DeusData/codebase-memory-mcp"
version: "0.12.1"
timestamp: "2026-11-03T23:50:00Z"
status: "draft"
tags: [codebase-memory-mcp, mise, upgrade, daemon]
sources:
  - id: mise-upgrade
    resource: "https://github.com/jdx/mise/blob/v2026.11.0/src/cli/upgrade.rs"
    title: "--bump rewrites pins; pin = true rewrites latest (lines 566-590)"
  - id: cbm-cli
    resource: "https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/src/cli/cli.c"
    title: "install quiesce and --reset-indexes (lines 10642-10667, 11557-11561)"
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

## Manual upgrade, today

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

## Facts for the automation PR

- `install --skip-binary` alone does not drain sessions: it quiesces only when it validates a binary or deletes
  indexes (`quiesce_required = has_binary_validator || delete_indexes`, cli.c:11557-11561).
- `install --skip-binary --reset-indexes -y` is CBM's own forced drain: it stops every CBM process, then deletes
  **every** index under the cache, not only the projects the upgrade plans to rebuild. It drains only when at least
  one index exists (cli.c:10642-10645). The automation must decide which projects to rebuild (for example from
  `list_projects` before the drain) or accept losing the others.
- A newer build drains an older daemon by itself only when that daemon is permanent (`daemon start`), not the
  default session-managed one.
- A mise tool `postinstall` runs before the runtime links move, from `/`, with no stdin, under the 30-minute
  `tool-update` service cap. It cannot read release notes first, so it is the wrong place for the protocol.
- Open sessions after a drain: this Claude Code 2.1.317 session's CBM server was killed mid-session (the retired
  0.11.0 setup). Afterwards it was listed as failed to connect, and its MCP log has no reconnect attempt. Claude Code
  offers `/mcp reconnect <server>|all`; Codex needs a restart. Automatic respawn should not be assumed.
- The `//cbm:install` checks expect exactly what 0.12.1 writes: 7 Claude hooks with a 5 s timeout, 2 Codex hooks,
  each agent's tool profile and the 13 read-only analysis tools. A release that adds a tool, renames a hook trigger
  or changes a timeout fails them even when the setup works. The automation must update those expected values
  from each release's notes and source, and treat a check FAIL after an upgrade as "needs review", not "broken".
- Codex re-trust: the configs name the launcher, so hook commands do not change on upgrade. Whether Codex still
  asks for a re-trust after the installer rewrites `hooks.json` is untested.

## Automation MVP (designed, not built)

The owner's protocol: on a new release, review its notes for what affects this setup, stop the services, update
the tool and rerun the installer, restart and reindex. It runs even with sessions open. The draft shape, agreed in
an adversarial review:

1. Candidate from `mise latest github:DeusData/codebase-memory-mcp`; equal to the launcher's `--version`, stop.
2. Fetch the notes for that tag and run a bounded, tool-less review into
   `~/.local/state/dotfiles/cbm-upgrade/v<version>/`. Missing notes or a failed review stops before any change.
3. `mise use -g github:DeusData/codebase-memory-mcp@<version>`.
4. The forced-drain install (`--skip-binary --reset-indexes`), with the launcher workaround from `install.md`.
5. Reindex the chosen projects; check version, `daemon status`, `index_status` and the conflict log.
6. Print what open sessions need (`/mcp reconnect`, Codex restart and `/hooks`).

Open: the scheduler (pitchfork `cron` running the same task, or something else), the reindex list, tracking
`~/.config/mise/scripts/` in this repository, and whether sessions recover without a restart.
