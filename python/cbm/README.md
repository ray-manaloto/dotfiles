# cbm commands

`cbm install` installs and verifies the live agent setup. `cbm verify` checks it. Any other
arguments return `invalid_usage` with exit code 2.

Install runs only when both the current directory and the loaded Python package are in primary
Git checkouts on `main`. Running a linked worktree's CLI from a primary checkout does not bypass the guard.
Linked worktrees (including one on `main`), other branches, detached HEADs, and directories
outside a checkout are refused before any setup change, with `install_checkout_refused`,
exit code 1 and a final `failed` Done event. If Git cannot identify the checkout, install
also refuses, and the error message reports Git's startup, timeout or exit failure.
Running `mise run //cbm:install` from the main checkout works as before.
Empty repositories without a commit are refused with the same checkout guidance.

Each Git command used for checkout discovery has a 10-second timeout.
`CBM_INSTALL_GIT_TIMEOUT_SECONDS` can shorten it to a number of seconds greater than zero and at most 10.
Invalid values produce `invalid_setting`
with exit 2 and a message naming the variable, before Git discovery. Actual Git failures remain
checkout refusals with exit 1. SIGINT or SIGTERM during discovery emits the refusal and failed Done
events without setup changes, then exits with status `128 + signal`.

Each launcher run that install or verify makes has a 60-second timeout; one that stalls fails its check with
`command_timeout` instead of hanging the run. `CBM_PROBE_TIMEOUT_SECONDS` can shorten it to a number of
seconds greater than zero and at most 60. Invalid values produce `invalid_setting` with exit 2 and a
message naming the variable.

For a deliberate install from another checkout, opt in for that invocation:

```text
CBM_INSTALL_ALLOW_NON_MAIN=1 mise run //cbm:install
```

The same variable works with `cbm install`; only the exact value `1` opts in. This permits
changes to the live setup; it does not isolate the installer. `cbm verify` remains read-only
and works from any directory without an opt-in.

Codex hooks are supported only in `~/.codex/hooks.json`. When Codex is a selected client and that path
holds nothing, install first creates it as `{"hooks": {}}`. This makes CBM's installer write its hooks
there and move any old block out of `config.toml`. An existing file or link is never replaced. If the
installer fails while `hooks.json` is there and a CBM hook is still in `config.toml`, install fails with
`codex_hook_migration_refused`, exit code 1 and a final `failed` Done event. The installer's own Codex
`agent_config` line (`op=hook_preflight` or `op=hook_install`) gives the reason; with no such line,
the installer failed before its Codex step. The hook stays for you to remove. If the empty file cannot be
created, install fails with `codex_hooks_seed_failed` before the installer runs. `cbm verify` fails
`Codex config.toml has no CBM hooks; hooks.json holds them` while any CBM hook is in `config.toml`.
See `docs/research/codebase-memory-mcp/install.md`.

`cbm verify` reads each client config's hooks and CBM MCP entry level by level. A level that parses but is
not the expected table or list (such as `"SessionStart": 4` in Claude's `settings.json`, or `mcp_servers = 4`
in a Codex config) holds no CBM entry: the check that reads it fails by name, with no error event, and verify
still ends with its Done event. Malformed entries beside the CBM ones are skipped, so they do not fail a check.

Upgrades are manual: see `docs/research/codebase-memory-mcp/upgrades.md`.
