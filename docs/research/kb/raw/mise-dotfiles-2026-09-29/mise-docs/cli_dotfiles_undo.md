[Skip to content](https://mise.jdx.dev/cli/dotfiles/undo.html#VPContent)

On this page

# `mise dotfiles undo` [​](https://mise.jdx.dev/cli/dotfiles/undo.html\#mise-dotfiles-undo)

- **Usage:**`mise dotfiles undo [-n --dry-run] [-y --yes] [REF]`
- **Effect:** destructive — may delete or irreversibly overwrite
- **Source code:** [`src/cli/dotfiles/undo.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/undo.rs)

Reverse the tracked-file changes from an operation

Restores exactly the paths that operation changed from the protective checkpoint it took, leaving everything else as it is now. Without a reference, the newest operation not yet undone is reversed. Bootstrap, captured commands, rollback, undo, and pull are supported. Package installations, service state, and untracked files are not reversed.

## Arguments [​](https://mise.jdx.dev/cli/dotfiles/undo.html\#arguments)

- **`[REF]`** — The operation's checkpoint: numeric ID, `latest`, `latest~N`, or `commit:<sha>`

## Flags [​](https://mise.jdx.dev/cli/dotfiles/undo.html\#flags)

- **`-n --dry-run`** — Show the plan without changing anything
- **`-y --yes`** — Apply without prompting
- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/dotfiles/undo.html\#related-documentation)

- [Getting started](https://mise.jdx.dev/getting-started.html).
- [`mise dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)