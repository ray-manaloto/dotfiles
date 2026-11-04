---
okf_version: "0.2"
type: "concept"
title: "Installing codebase-memory-mcp for Claude Code and Codex"
description: "mise owns the CBM binary; the //cbm:install task runs CBM's own installer for the agent setup, writing one stable launcher path into every config, and works around a macOS --skip-binary bug."
package: "github:DeusData/codebase-memory-mcp"
version: "0.12.1"
timestamp: "2026-11-03T23:50:00Z"
status: "draft"
tags: [codebase-memory-mcp, mise, claude-code, codex, mcp, install]
sources:
  - id: cbm-cli
    resource: "https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/src/cli/cli.c"
    title: "install: --skip-binary, --dir, macOS signing (lines 11240-11600)"
  - id: mise-runtime-symlinks
    resource: "https://github.com/jdx/mise/blob/v2026.11.0/src/runtime_symlinks.rs"
    title: "The global runtime link follows the global config only"
  - id: task
    resource: "repo:python/cbm"
---

# Installing codebase-memory-mcp for Claude Code and Codex

## Layers

| Layer | Owner | Where |
|---|---|---|
| Binary | mise, exact pin | `"github:DeusData/codebase-memory-mcp" = { version = "0.12.1", minimum_release_age = "0s" }` in the global mise config |
| Stable path | mise global runtime link (v2026.10.8+) | `~/.local/share/mise/installs/github-deus-data-codebase-memory-mcp/global/codebase-memory-mcp`; it follows the global config only, so a project pin cannot change it |
| Launcher | `//cbm:install` | `~/.local/share/codebase-memory-mcp/bin/codebase-memory-mcp`, a symlink to the global link |
| Agent setup | CBM's installer, run by `//cbm:install` | MCP entry, hooks, skill, three agents, Codex AGENTS.md pointer |

Every config names the launcher, so a version bump changes no config. No plugin is used: the upstream Claude plugin
exists only on `main` (not in the v0.12.1 tag) and launches a second, npx-downloaded copy.

## Run

```
mise install                 # the pinned binary
mise run //cbm:install       # agent setup, then the checks
mise run //cbm:verify        # the checks only
```

Run them from a dotfiles checkout: the tasks belong to the `python/cbm` package (`//cbm` is its monorepo alias), so
any checkout or worktree that holds the package works, before or after the merge. Then restart Claude and Codex
sessions. Codex lists the two new hooks under `/hooks` until they are trusted.
`CBM_CLIENTS` overrides the client list (default `claude,codex`; Antigravity and OpenCode come later).
One install runs at a time (`~/.local/share/codebase-memory-mcp/cbm-install.lock`); a second is refused.
`//cbm:verify` also opens a live MCP session over stdio through the launcher.

## Only through `//cbm:install`

Install, reinstall and upgrade the agent setup only with `mise run //cbm:install`. CBM's own routes skip the launcher
workaround and break a working setup:
- `codebase-memory-mcp install` run from the mise binary detects mise as the binary's manager, so it places no
  binary and edits no shell file (cli.c:11355-11358, :11192). But without `--dir` it writes
  `~/.local/bin/codebase-memory-mcp` into every agent config, a path that does not exist under mise (#2722), so
  CBM fails in every session.
- `install.sh` (what CBM's `update` points to) downloads a second, unmanaged binary into `~/.local/bin` and runs
  that binary's `install` (install.sh:20, :345). The configs then name that copy, which the mise pin and upgrades
  do not track, and a build that differs from the mise one is refused by the daemon. Because that copy is not
  externally managed, its `install` also appends an `export PATH=…` line to `~/.zshrc` when `~/.local/bin` is not
  on `PATH` (cli.c:11206-11209, `cbm_ensure_path` at :6637); `~/.zshrc` is linked from the dotfiles main checkout.
- `install --force-binary` overrides the manager detection and behaves like the `install.sh` case.

## The macOS `--skip-binary` workaround

Pointing the installer at the mise folder (`install --skip-binary --dir=<global link dir>`) fails on macOS:
`error: failed to stage install candidate: activation transaction I/O failed`, exit 1, nothing written. Two spots in
`install` ignore `--skip-binary`:

- `bool sign_binary = do_copy || target_exists;` (cli.c:11406): an existing target is copied, ad-hoc signed and
  staged for publication, which also turns on the session drain. Staging refuses the symlinked path.
- The "a different binary already exists, replace it?" prompt (cli.c:11392) is answered yes under `-y` and sets
  `do_copy` (source reading; not reproduced).

With `--dir` at an empty folder nothing exists at the target, so the installer only writes configs ("No CBM session
needs to stop"). `//cbm:install` removes its own symlink, runs the installer, and restores the symlink. Both spots are
still on `main` (e0c7a1d); an upstream issue is drafted, not filed.

Other installer facts at v0.12.1:
- `--dir` is used verbatim, with no `realpath` (cli.c:11304-11319), so configs get the launcher path, not a
  versioned one. Without `--dir`, 0.12.1 writes a `~/.local/bin` path that does not exist under mise (#2722).
- With `--skip-binary` the installer returns before any shell rc edit (cli.c:11186-11194); the closing
  "source ~/.zshrc" line is printed unconditionally.
- The dry run skips the binary-preparation branch, and `--plan` lists every detected client before `--clients`
  is applied, so neither proves what a real run does.
- A real rehearsal needs a short `CBM_RUNTIME_DIR`: the runtime folder holds unix sockets.

## What the installer writes

Created: `~/.claude/agents/codebase-memory{,-scout,-auditor}.md`, `~/.claude/hooks/cbm-{code-discovery-gate,
session-reminder,subagent-reminder}`, `~/.claude/skills/codebase-memory/SKILL.md`,
`~/.codex/agents/codebase-memory{,-scout,-auditor}.toml`, `~/.codex/skills/codebase-memory/SKILL.md`.
Edited: `~/.claude.json` (one `mcpServers` entry), `~/.claude/settings.json` (7 hook groups), `~/.codex/config.toml`
(one `mcp_servers` table forwarding `CBM_CACHE_DIR` and `CBM_RUNTIME_DIR`), `~/.codex/hooks.json` (2 hooks),
`~/.codex/AGENTS.md` (a managed pointer). `config set auto_index false` creates CBM's `config.json`.

A rollback removes those created files and only CBM's entries from the edited ones. Copying a backup back would also
undo unrelated changes made since (another session enabled a plugin between the backup and the install here).

## Settings

- `auto_index = false`: index on demand (`index_repository`), so a session in a large folder does not start a
  full index. Existing indexes are still kept current by the watcher.
- One cache root per account (the default `~/.cache/codebase-memory-mcp`). CBM refuses a second cache root in the
  same runtime namespace (`cache_root` conflicts), so `CBM_CACHE_DIR` and `CBM_RUNTIME_DIR` are never set.
- The daemon serves the CBM Lens UI on `127.0.0.1:9749` (loopback); kept on.
