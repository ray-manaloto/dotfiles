[Skip to content](https://mise.jdx.dev/cli/where.html#VPContent)

On this page

# `mise where` [​](https://mise.jdx.dev/cli/where.html\#mise-where)

- **Usage:**`mise where <TOOL@VERSION>`
- **Effect:** read-only
- **Source code:** [`src/cli/where.rs`](https://github.com/jdx/mise/blob/main/src/cli/where.rs)

Display the installation path for a tool

The tool must be installed for this to work.

## Arguments [​](https://mise.jdx.dev/cli/where.html\#arguments)

- **`<TOOL@VERSION>`** — Tool to look up e.g.: ruby@3 With "@<PREFIX>", shows the latest installed version matching the prefix. Otherwise, shows the current, active installed version.

## Flags [​](https://mise.jdx.dev/cli/where.html\#flags)

- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/where.html\#examples)

Show the latest installed node 20.x Errors if no matching version is installed

```
mise where node@20
/home/jdx/.local/share/mise/installs/node/20.0.0
```

Show the install directory of the active node, or of the latest installed version if no config requests node Errors if no matching version is installed

```
mise where node
/home/jdx/.local/share/mise/installs/node/20.0.0
```

## Related documentation [​](https://mise.jdx.dev/cli/where.html\#related-documentation)

- [Development tools](https://mise.jdx.dev/dev-tools/).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)