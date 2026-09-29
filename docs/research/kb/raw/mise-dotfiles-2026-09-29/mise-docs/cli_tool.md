[Skip to content](https://mise.jdx.dev/cli/tool.html#VPContent)

On this page

# `mise tool` [​](https://mise.jdx.dev/cli/tool.html\#mise-tool)

- **Usage:**`mise tool [FLAGS] <TOOL>`
- **Effect:** read-only
- **Source code:** [`src/cli/tool.rs`](https://github.com/jdx/mise/blob/main/src/cli/tool.rs)

Show information about a tool

## Arguments [​](https://mise.jdx.dev/cli/tool.html\#arguments)

- **`<TOOL>`** — Tool name to get information about

## Flags [​](https://mise.jdx.dev/cli/tool.html\#flags)

- **`-J --json`** — Output in JSON format
- **`--active`** — Only show active versions
- **`--backend`** — Only show backend field
- **`--config-source`** — Only show config source
- **`--description`** — Only show description field
- **`--installed`** — Only show installed versions
- **`--requested`** — Only show requested versions
- **`--tool-options`** — Only show tool options
- **`--url`** — Only show the project URL from the registry
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/tool.html\#examples)

```
mise tool node
Backend:            core
Installed Versions: 20.0.0 22.0.0
Active Version:     20.0.0
Requested Version:  20
Config Source:      ~/.config/mise/mise.toml
Tool Options:       [none]
```

## Related documentation [​](https://mise.jdx.dev/cli/tool.html\#related-documentation)

- [Development tools](https://mise.jdx.dev/dev-tools/).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)