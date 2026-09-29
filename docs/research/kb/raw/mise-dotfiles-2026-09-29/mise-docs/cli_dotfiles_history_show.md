[Skip to content](https://mise.jdx.dev/cli/dotfiles/history/show.html#VPContent)

On this page

# `mise dotfiles history show` [​](https://mise.jdx.dev/cli/dotfiles/history/show.html\#mise-dotfiles-history-show)

- **Usage:**`mise dotfiles history show [FLAGS] [REF]`
- **Effect:** read-only
- **Source code:** [`src/cli/dotfiles/history/show.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/history/show.rs)

Show one checkpoint: what triggered it, what changed, and its journal

## Arguments [​](https://mise.jdx.dev/cli/dotfiles/history/show.html\#arguments)

- **`[REF]`** — Numeric checkpoint ID, `latest` (the default), `latest~N`, or `commit:<sha>`

## Flags [​](https://mise.jdx.dev/cli/dotfiles/history/show.html\#flags)

- **`-J --json`** — Output in JSON format
- **`--files`** — List every file in the snapshot
- **`--path <PATH>`** — Resolve `latest~N` among the checkpoints where this path changed
- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/dotfiles/history/show.html\#related-documentation)

- [Getting started](https://mise.jdx.dev/getting-started.html).
- [`mise dotfiles history [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/dotfiles/history.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)