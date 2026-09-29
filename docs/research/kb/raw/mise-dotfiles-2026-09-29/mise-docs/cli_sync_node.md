[Skip to content](https://mise.jdx.dev/cli/sync/node.html#VPContent)

On this page

# `mise sync node` [​](https://mise.jdx.dev/cli/sync/node.html\#mise-sync-node)

- **Usage:**`mise sync node [FLAGS]`
- **Effect:** modifies state
- **Source code:** [`src/cli/sync/node.rs`](https://github.com/jdx/mise/blob/main/src/cli/sync/node.rs)

Symlink node versions installed by nvm, nodenv, or Homebrew into mise

Use this to make versions installed by another version manager available to mise.

This won't overwrite managed installs, runtime aliases, or links from other providers.

## Flags [​](https://mise.jdx.dev/cli/sync/node.html\#flags)

- **`--brew`** — Get tool versions from Homebrew
- **`--nodenv`** — Get tool versions from nodenv
- **`--nvm`** — Get tool versions from nvm
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/sync/node.html\#examples)

```
brew install node@20
mise sync node --brew
mise use -g node@20 # uses Homebrew-provided node
```

## Related documentation [​](https://mise.jdx.dev/cli/sync/node.html\#related-documentation)

- [Node.js](https://mise.jdx.dev/lang/node.html).
- [`mise sync <SUBCOMMAND>`](https://mise.jdx.dev/cli/sync.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)