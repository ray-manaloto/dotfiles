[Skip to content](https://mise.jdx.dev/cli/bootstrap/dotfiles/recover.html#VPContent)

On this page

# `mise bootstrap dotfiles recover` [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/recover.html\#mise-bootstrap-dotfiles-recover)

- **Usage:**`mise bootstrap dotfiles recover [--keep-current] [-y --yes] [OPERATION]`
- **Effect:** destructive — may delete or irreversibly overwrite
- **Source code:** [`src/cli/dotfiles/recover.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/recover.rs)

Recover an interrupted dotfile operation

Retries safe recovery without overwriting later edits. If recovery cannot determine what is safe, inspect the listed files first. `--keep-current` explicitly accepts their live contents and discards only the selected operation's temporary recovery copies; it does not erase Git history.

## Arguments [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/recover.html\#arguments)

- **`[OPERATION]`** — Pending numeric ID or an unambiguous operation UUID prefix

## Flags [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/recover.html\#flags)

- **`--keep-current`** — Accept live files instead of restoring temporary recovery copies
- **`-y --yes`** — Confirm discarding the selected operation's temporary recovery copies
- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/recover.html\#related-documentation)

- [Dotfile ownership and modes](https://mise.jdx.dev/dotfiles.html).
- [`mise bootstrap dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)