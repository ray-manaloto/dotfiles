[Skip to content](https://mise.jdx.dev/cli/tool-alias/ls.html#VPContent)

On this page

# `mise tool-alias ls` [​](https://mise.jdx.dev/cli/tool-alias/ls.html\#mise-tool-alias-ls)

- **Usage:**`mise tool-alias ls [--no-header] [TOOL]`
- **Aliases:**`list`
- **Effect:** read-only
- **Source code:** [`src/cli/tool_alias/ls.rs`](https://github.com/jdx/mise/blob/main/src/cli/tool_alias/ls.rs)

List tool version aliases

Aliases can be defined in user config or provided by plugins via `bin/list-aliases`.

In user config, aliases are defined like the following in `~/.config/mise/config.toml`:

```
[tool_alias.node.versions]
project = "20"
```

## Arguments [​](https://mise.jdx.dev/cli/tool-alias/ls.html\#arguments)

- **`[TOOL]`** — Show aliases for <TOOL>

## Flags [​](https://mise.jdx.dev/cli/tool-alias/ls.html\#flags)

- **`--no-header`** — Don't show table header
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/tool-alias/ls.html\#examples)

```
mise tool-alias ls
node  lts-jod      22
```

## Related documentation [​](https://mise.jdx.dev/cli/tool-alias/ls.html\#related-documentation)

- [Tool version aliases](https://mise.jdx.dev/dev-tools/aliases.html).
- [`mise tool-alias [-p --tool <TOOL>] [--no-header] [SUBCOMMAND]`](https://mise.jdx.dev/cli/tool-alias.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)