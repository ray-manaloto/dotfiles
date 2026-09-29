[Skip to content](https://mise.jdx.dev/cli/link.html#VPContent)

On this page

# `mise link` [​](https://mise.jdx.dev/cli/link.html\#mise-link)

- **Usage:**`mise link [-f --force] <TOOL@VERSION> <PATH>`
- **Aliases:**`ln`
- **Effect:** modifies state
- **Source code:** [`src/cli/link.rs`](https://github.com/jdx/mise/blob/main/src/cli/link.rs)

Symlink a tool version into mise

Use this to register an install that was compiled by hand or built with another tool.

## Arguments [​](https://mise.jdx.dev/cli/link.html\#arguments)

- **`<TOOL@VERSION>`** — Tool name and version to create a symlink for
- **`<PATH>`** — The local path to the tool version e.g.: ~/.nvm/versions/node/v20.0.0

## Flags [​](https://mise.jdx.dev/cli/link.html\#flags)

- **`-f --force`** — Overwrite an existing tool version if it exists
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/link.html\#examples)

build node-20.0.0 with node-build and link it into mise

```
node-build 20.0.0 ~/.nodes/20.0.0
mise link node@20.0.0 ~/.nodes/20.0.0
```

have mise use the node version provided by Homebrew

```
brew install node
mise link node@brew "$(brew --prefix node)"
mise use node@brew
```

## Related documentation [​](https://mise.jdx.dev/cli/link.html\#related-documentation)

- [Development tools](https://mise.jdx.dev/dev-tools/).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)