[Skip to content](https://mise.jdx.dev/cli/bootstrap/user.html#VPContent)

On this page

# `mise bootstrap user` [​](https://mise.jdx.dev/cli/bootstrap/user.html\#mise-bootstrap-user)

- **Usage:**`mise bootstrap user <SUBCOMMAND>`
- **Effect:** read-only
- **Source code:** [`src/cli/bootstrap.rs`](https://github.com/jdx/mise/blob/main/src/cli/bootstrap.rs)

Manage current-user bootstrap settings from `[bootstrap.user]`

Currently manages the login shell. Apply as the intended user; changing the login shell affects future sessions, not the shell running this command.

## Flags [​](https://mise.jdx.dev/cli/bootstrap/user.html\#flags)

- **`-h --help`** — Print help

## Subcommands [​](https://mise.jdx.dev/cli/bootstrap/user.html\#subcommands)

- [`mise bootstrap user apply [-n --dry-run] [-y --yes]`](https://mise.jdx.dev/cli/bootstrap/user/apply.html)
- [`mise bootstrap user status [-J --json] [--missing]`](https://mise.jdx.dev/cli/bootstrap/user/status.html)

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/user.html\#related-documentation)

- [Current-user settings](https://mise.jdx.dev/bootstrap/user.html).
- [`mise bootstrap [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/bootstrap.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)