---
name: lsp-server
description: "Add, update, remove, or check a language server that Claude Code runs (typescript, clangd): status, which, has-update, health, smoke, verify, doctor, conflicts. Use for /lsp-server, or when an LSP server is missing, broken, outdated, or claimed by two plugins."
argument-hint: "<action> [server] [--json]"
disable-model-invocation: false
---

Run the skill's arguments through the global mise task, unchanged, and report its output:

```
mise run lsp $ARGUMENTS
```

The task does all the work and a person can run the same command. It exits 0 when every check passed,
1 when one failed (each `FAIL` line names the check and what it found), and 2 when it could not run, with
one JSON error on stderr.

- **Read-only actions:** `status`, `which`, `has-update`, `health`, `smoke`, `verify`, `doctor`, and
  `conflicts`. Run them from any folder. `has-update` fails when an update is waiting.
- **Write actions:** `add`, `update`, and `remove` edit the pin and lock in a dotfiles worktree, never the main
  checkout, and turn the plugin on or off with `claude plugin`. Run them from a dotfiles worktree, then commit
  the change through the normal review. A server that mise bootstrap installs (clangd, `brew:llvm`) refuses
  them; change it with `mise bootstrap packages`.
- **New server:** add an entry and a fixture under `python/lsp/src/lsptools/` in dotfiles.

When a check fails, quote its `FAIL` line and the fix it suggests. Don't try other commands first.
