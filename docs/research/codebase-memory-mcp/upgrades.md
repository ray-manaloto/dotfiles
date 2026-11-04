---
okf_version: "0.2"
type: "concept"
title: "Upgrading codebase-memory-mcp"
description: "Why CBM has an exact pin that bulk upgrades skip, the manual upgrade order that keeps one build per account, what the forced-drain installer flags do to indexes, and why upgrades stay manual."
package: "github:DeusData/codebase-memory-mcp"
version: "0.12.1"
timestamp: "2026-11-04T23:05:00Z"
status: "draft"
tags: [codebase-memory-mcp, mise, upgrade, daemon]
sources:
  - id: mise-upgrade
    resource: "https://github.com/jdx/mise/blob/v2026.11.0/src/cli/upgrade.rs"
    title: "--bump rewrites pins; pin = true rewrites latest (lines 566-590)"
  - id: cbm-cli
    resource: "https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/src/cli/cli.c"
    title: "install quiesce and --reset-indexes (lines 10642-10667, 11192-11229, 11557-11561)"
  - id: mise-links
    resource: "https://github.com/jdx/mise/blob/v2026.11.0/src/runtime_symlinks.rs"
    title: "global runtime links are rebuilt from installed versions (lines 48-72, 267-320)"
  - id: cbm-runtime
    resource: "https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/src/daemon/runtime.c"
    title: "daemon stop refuses attached clients (1872-1895); peer fingerprint check (2074-2148)"
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
same cache root. An open Claude, Codex or OpenCode
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

1. Review the release notes for the new tag; note index-format and installer changes. Bump the pin (and
   `mise.lock`) in a separate worktree, then review and merge it. Leave the primary checkout alone:
   `~/.config/mise/config.toml` links into it, so moving it moves the live pin.
2. Close every Claude, Codex and OpenCode session (and anything else that runs CBM), and start no new one until
   step 7.
3. Stop the old daemon with the still-old launcher: `codebase-memory-mcp daemon stop`. It refuses while sessions
   are attached, and success can mean "stopping" (runtime.c:1872-1895), so wait until no
   `--cbm-daemon-internal` process is left.
4. Fetch and fast-forward the primary checkout to `origin/main`. This moves the live pin.
5. `mise install`, then confirm the global link and the launcher resolve to the new build. Until mise rebuilds the
   link, the launcher still reaches the old binary (mise `runtime_symlinks.rs:48-72`, `cli/install.rs:420-455`).
   `//cbm:install` compares the link with the launcher, not with the pin, so check the build yourself.
6. `mise run //cbm:install` from the primary checkout on `main`, never CBM's own `install`, `update` or
   `install.sh` (see `install.md`). It rewrites the agent setup for the new build; configs keep the launcher path.
   Keep sessions closed: it removes the launcher for a moment and opens an MCP session to verify.
7. Open one session. Codex: re-trust in `/hooks` if it lists the CBM hooks as changed.
8. Reindex each project with the new build (index-format changes force a full rebuild: 0.12.0, and again 0.12.1)
   and wait for it to finish; with `auto_index` off, startup proves nothing. Check the tools in `/mcp`, one
   executable path in `ps`, and no new lines in `daemon-conflicts.ndjson`.
9. Resume the other sessions.

The daemon runs from the resolved install folder (`~/.local/share/mise/installs/codebase-memory-mcp-<hash>/`), not
from the link, and running processes keep their old executable when the pin moves. A new launch after step 5 runs
the new build; if the old daemon were still up, the daemon would refuse it (`fingerprint_mismatch`,
runtime.c:2074-2148). That is why steps 2 and 3 come before steps 4 and 5.

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
