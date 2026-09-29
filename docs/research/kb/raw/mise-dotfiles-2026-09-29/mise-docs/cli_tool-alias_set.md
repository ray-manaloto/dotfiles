[Skip to content](https://mise.jdx.dev/cli/tool-alias/set.html#VPContent)

On this page

# `mise tool-alias set` [​](https://mise.jdx.dev/cli/tool-alias/set.html\#mise-tool-alias-set)

- **Usage:**`mise tool-alias set <ARGS>…`
- **Aliases:**`add`, `create`
- **Effect:** modifies state
- **Source code:** [`src/cli/tool_alias/set.rs`](https://github.com/jdx/mise/blob/main/src/cli/tool_alias/set.rs)

Add/update an alias for a tool/backend

This modifies the contents of ~/.config/mise/config.toml

## Arguments [​](https://mise.jdx.dev/cli/tool-alias/set.html\#arguments)

- **`<TOOL>`** — The tool/backend to set the alias for
- **`<ALIAS>`** — The alias to set
- **`[VALUE]`** — The value to set the alias to

## Flags [​](https://mise.jdx.dev/cli/tool-alias/set.html\#flags)

- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/tool-alias/set.html\#examples)

```
mise tool-alias set ripgrep aqua:BurntSushi/ripgrep
mise tool-alias set node project 20
```

## Related documentation [​](https://mise.jdx.dev/cli/tool-alias/set.html\#related-documentation)

- [Tool version aliases](https://mise.jdx.dev/dev-tools/aliases.html).
- [`mise tool-alias [-p --tool <TOOL>] [--no-header] [SUBCOMMAND]`](https://mise.jdx.dev/cli/tool-alias.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)