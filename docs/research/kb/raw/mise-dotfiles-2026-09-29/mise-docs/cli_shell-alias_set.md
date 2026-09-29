[Skip to content](https://mise.jdx.dev/cli/shell-alias/set.html#VPContent)

On this page

# `mise shell-alias set` [​](https://mise.jdx.dev/cli/shell-alias/set.html\#mise-shell-alias-set)

- **Usage:**`mise shell-alias set <shell_alias> [COMMAND]`
- **Aliases:**`add`, `create`
- **Effect:** modifies state
- **Source code:** [`src/cli/shell_alias/set.rs`](https://github.com/jdx/mise/blob/main/src/cli/shell_alias/set.rs)

Add/update a shell alias

This modifies the contents of ~/.config/mise/config.toml

## Arguments [​](https://mise.jdx.dev/cli/shell-alias/set.html\#arguments)

- **`<shell_alias>`** — The alias name
- **`[COMMAND]`** — The command to run (optional if provided as ALIAS=COMMAND)

## Flags [​](https://mise.jdx.dev/cli/shell-alias/set.html\#flags)

- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/shell-alias/set.html\#examples)

```
mise shell-alias set ll "ls -la"
mise shell-alias set gs "git status"
```

## Related documentation [​](https://mise.jdx.dev/cli/shell-alias/set.html\#related-documentation)

- [Shell aliases](https://mise.jdx.dev/shell-aliases.html).
- [`mise shell-alias [--no-header] [SUBCOMMAND]`](https://mise.jdx.dev/cli/shell-alias.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)