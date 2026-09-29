[Skip to content](https://mise.jdx.dev/cli/dotfiles/history/diff.html#VPContent)

On this page

# `mise dotfiles history diff` [​](https://mise.jdx.dev/cli/dotfiles/history/diff.html\#mise-dotfiles-history-diff)

- **Usage:**`mise dotfiles history diff [FLAGS] [A] [B]`
- **Effect:** read-only
- **Source code:** [`src/cli/dotfiles/history/diff.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/history/diff.rs)

Compare checkpoints, or the working tree against one

Without arguments, shows what changed by hand since the latest checkpoint. With one reference, shows what that checkpoint changed against the one before it. With two, compares the two states.

## Arguments [​](https://mise.jdx.dev/cli/dotfiles/history/diff.html\#arguments)

- **`[A]`** — Numeric checkpoint ID, `latest`, `latest~N`, or `commit:<sha>`
- **`[B]`** — Compare `A` with this checkpoint instead of its predecessor

## Flags [​](https://mise.jdx.dev/cli/dotfiles/history/diff.html\#flags)

- **`--operation`** — Compare an operation with its recorded protective checkpoint

With no reference, use the newest operation, ignoring later saves. With one reference, use that operation. Fails if its before checkpoint is unavailable instead of comparing an unrelated preceding save.

- **`-p --patch`** — Print the full patch instead of a per-file summary

- **`--path <PATH>`** — Restrict to one path (a file or a directory)

- **`--exit-code`** — Exit 1 when the two sides differ

- **`-h --help`** — Print help


## Related documentation [​](https://mise.jdx.dev/cli/dotfiles/history/diff.html\#related-documentation)

- [Getting started](https://mise.jdx.dev/getting-started.html).
- [`mise dotfiles history [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/dotfiles/history.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)