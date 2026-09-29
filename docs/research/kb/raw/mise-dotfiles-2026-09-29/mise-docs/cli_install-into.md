[Skip to content](https://mise.jdx.dev/cli/install-into.html#VPContent)

On this page

# `mise install-into` [​](https://mise.jdx.dev/cli/install-into.html\#mise-install-into)

- **Usage:**`mise install-into <TOOL@VERSION> <PATH>`
- **Effect:** modifies state
- **Source code:** [`src/cli/install_into.rs`](https://github.com/jdx/mise/blob/main/src/cli/install_into.rs)

Install a tool version to a specific path

Used for building a tool to a directory for use outside of mise

## Arguments [​](https://mise.jdx.dev/cli/install-into.html\#arguments)

- **`<TOOL@VERSION>`** — Tool to install e.g.: node@20
- **`<PATH>`** — Path to install the tool into

## Flags [​](https://mise.jdx.dev/cli/install-into.html\#flags)

- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/install-into.html\#examples)

install node@20.0.0 into ./mynode

```
mise install-into node@20.0.0 ./mynode && ./mynode/bin/node -v
v20.0.0
```

## Related documentation [​](https://mise.jdx.dev/cli/install-into.html\#related-documentation)

- [Development tools](https://mise.jdx.dev/dev-tools/).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)