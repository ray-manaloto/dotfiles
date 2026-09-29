[Skip to content](https://mise.jdx.dev/cli/shell-alias/unset.html#VPContent)

On this page

# `mise shell-alias unset` [​](https://mise.jdx.dev/cli/shell-alias/unset.html\#mise-shell-alias-unset)

- **Usage:**`mise shell-alias unset <shell_alias>`
- **Aliases:**`rm`, `remove`, `delete`, `del`
- **Effect:** modifies state
- **Source code:** [`src/cli/shell_alias/unset.rs`](https://github.com/jdx/mise/blob/main/src/cli/shell_alias/unset.rs)

Remove a shell alias

This modifies the contents of ~/.config/mise/config.toml

## Arguments [​](https://mise.jdx.dev/cli/shell-alias/unset.html\#arguments)

- **`<shell_alias>`** — The alias to remove

## Flags [​](https://mise.jdx.dev/cli/shell-alias/unset.html\#flags)

- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/shell-alias/unset.html\#examples)

```
mise shell-alias unset ll
```

## Related documentation [​](https://mise.jdx.dev/cli/shell-alias/unset.html\#related-documentation)

- [Shell aliases](https://mise.jdx.dev/shell-aliases.html).
- [`mise shell-alias [--no-header] [SUBCOMMAND]`](https://mise.jdx.dev/cli/shell-alias.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)