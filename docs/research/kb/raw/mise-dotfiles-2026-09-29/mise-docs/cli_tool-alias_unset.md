[Skip to content](https://mise.jdx.dev/cli/tool-alias/unset.html#VPContent)

On this page

# `mise tool-alias unset` [​](https://mise.jdx.dev/cli/tool-alias/unset.html\#mise-tool-alias-unset)

- **Usage:**`mise tool-alias unset <TOOL> [ALIAS]`
- **Aliases:**`rm`, `remove`, `delete`, `del`
- **Effect:** modifies state
- **Source code:** [`src/cli/tool_alias/unset.rs`](https://github.com/jdx/mise/blob/main/src/cli/tool_alias/unset.rs)

Clear an alias for a tool/backend

This modifies the contents of ~/.config/mise/config.toml

## Arguments [​](https://mise.jdx.dev/cli/tool-alias/unset.html\#arguments)

- **`<TOOL>`** — The tool/backend to remove the alias from
- **`[ALIAS]`** — The alias to remove

## Flags [​](https://mise.jdx.dev/cli/tool-alias/unset.html\#flags)

- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/tool-alias/unset.html\#examples)

```
mise tool-alias unset ripgrep
mise tool-alias unset node project
```

## Related documentation [​](https://mise.jdx.dev/cli/tool-alias/unset.html\#related-documentation)

- [Tool version aliases](https://mise.jdx.dev/dev-tools/aliases.html).
- [`mise tool-alias [-p --tool <TOOL>] [--no-header] [SUBCOMMAND]`](https://mise.jdx.dev/cli/tool-alias.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)