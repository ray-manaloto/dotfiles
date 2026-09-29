[Skip to content](https://mise.jdx.dev/cli/which.html#VPContent)

On this page

# `mise which` [​](https://mise.jdx.dev/cli/which.html\#mise-which)

- **Usage:**`mise which [FLAGS] [BIN_NAME]`
- **Effect:** read-only
- **Source code:** [`src/cli/which.rs`](https://github.com/jdx/mise/blob/main/src/cli/which.rs)

Show the path a tool's executable resolves to

Use this to figure out what version of a tool is currently active.

## Arguments [​](https://mise.jdx.dev/cli/which.html\#arguments)

- **`[BIN_NAME]`** — The executable to look up

## Flags [​](https://mise.jdx.dev/cli/which.html\#flags)

- **`-t --tool <TOOL@VERSION>`** — Use a specific tool@version e.g.: `mise which npm --tool=node@20`
- **`--plugin`** — Show the plugin name instead of the path
- **`--version`** — Show the version instead of the path
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/which.html\#examples)

```
mise which node
/home/username/.local/share/mise/installs/node/20.0.0/bin/node
```

```
mise which node --plugin
node
```

```
mise which node --version
20.0.0
```

## Related documentation [​](https://mise.jdx.dev/cli/which.html\#related-documentation)

- [Shims and executable lookup](https://mise.jdx.dev/dev-tools/shims.html).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)