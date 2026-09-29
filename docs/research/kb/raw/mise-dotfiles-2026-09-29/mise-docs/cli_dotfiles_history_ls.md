[Skip to content](https://mise.jdx.dev/cli/dotfiles/history/ls.html#VPContent)

On this page

# `mise dotfiles history ls` [​](https://mise.jdx.dev/cli/dotfiles/history/ls.html\#mise-dotfiles-history-ls)

- **Usage:**`mise dotfiles history ls [FLAGS]`
- **Aliases:**`list`
- **Effect:** read-only
- **Source code:** [`src/cli/dotfiles/history/ls.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/history/ls.rs)

List checkpoints, newest first

## Flags [​](https://mise.jdx.dev/cli/dotfiles/history/ls.html\#flags)

- **`-J --json`** — Output in JSON format

- **`-n --limit <LIMIT>`** — Show at most this many checkpoints (0 for all)

**Default:**`20`

- **`--path <PATH>`** — Only checkpoints where this path (or something under it) changed

- **`--trigger <TRIGGER>`** — Only checkpoints with this trigger (edit, save, bootstrap, …)

- **`--label <LABEL>`** — Only checkpoints with this label

- **`--pending`** — Only checkpoints recorded by operations that did not finish

- **`-h --help`** — Print help


## Related documentation [​](https://mise.jdx.dev/cli/dotfiles/history/ls.html\#related-documentation)

- [Getting started](https://mise.jdx.dev/getting-started.html).
- [`mise dotfiles history [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/dotfiles/history.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)