[Skip to content](https://mise.jdx.dev/cli/tool-alias/get.html#VPContent)

On this page

# `mise tool-alias get` [​](https://mise.jdx.dev/cli/tool-alias/get.html\#mise-tool-alias-get)

- **Usage:**`mise tool-alias get <TOOL> <ALIAS>`
- **Effect:** read-only
- **Source code:** [`src/cli/tool_alias/get.rs`](https://github.com/jdx/mise/blob/main/src/cli/tool_alias/get.rs)

Show a configured version alias for a tool

Reads the merged `[tool_alias.TOOL.versions]` configuration. This prints the stored request, which may itself be a prefix. Backend-provided aliases are listed by `mise tool-alias ls`; they are not entries returned by this command.

## Arguments [​](https://mise.jdx.dev/cli/tool-alias/get.html\#arguments)

- **`<TOOL>`** — The tool to show the alias for
- **`<ALIAS>`** — The alias to show

## Flags [​](https://mise.jdx.dev/cli/tool-alias/get.html\#flags)

- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/tool-alias/get.html\#examples)

```
mise tool-alias set node project 20
mise tool-alias get node project
20
```

## Related documentation [​](https://mise.jdx.dev/cli/tool-alias/get.html\#related-documentation)

- [Tool version aliases](https://mise.jdx.dev/dev-tools/aliases.html).
- [`mise tool-alias [-p --tool <TOOL>] [--no-header] [SUBCOMMAND]`](https://mise.jdx.dev/cli/tool-alias.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)