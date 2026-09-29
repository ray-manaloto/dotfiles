[Skip to content](https://mise.jdx.dev/cli/bootstrap/dotfiles/capture.html#VPContent)

On this page

# `mise bootstrap dotfiles capture` [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/capture.html\#mise-bootstrap-dotfiles-capture)

- **Usage:**`mise bootstrap dotfiles capture [--label <LABEL>] <-- COMMAND>…`
- **Source code:** [`src/cli/dotfiles/capture.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/capture.rs)

Record tracked files before and after an external command

Runs the command directly, inheriting its terminal and environment. Keeps a linked checkpoint pair, including when the command fails or changes no files. Capture failures warn and never replace the command's exit status. Only tracked files are recorded: package, service, and other system effects are not reversible. Concurrent editor changes are part of the same interval.

## Arguments [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/capture.html\#arguments)

- **`<-- COMMAND>…`** — Command and arguments to run, after --

## Flags [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/capture.html\#flags)

- **`--label <LABEL>`** — Describe this operation in history
- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/capture.html\#related-documentation)

- [Dotfile ownership and modes](https://mise.jdx.dev/dotfiles.html).
- [`mise bootstrap dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)