[Skip to content](https://mise.jdx.dev/cli/bootstrap/accounts.html#VPContent)

On this page

# `mise bootstrap accounts` [​](https://mise.jdx.dev/cli/bootstrap/accounts.html\#mise-bootstrap-accounts)

- **Usage:**`mise bootstrap accounts <SUBCOMMAND>`
- **Effect:** read-only
- **Source code:** [`src/cli/bootstrap.rs`](https://github.com/jdx/mise/blob/main/src/cli/bootstrap.rs)

Manage Linux users and groups from `[bootstrap.users]` and `[bootstrap.groups]`

These are system accounts on the target Linux host. Inspect `status` or an apply preview before changing user IDs, memberships, or account state.

## Flags [​](https://mise.jdx.dev/cli/bootstrap/accounts.html\#flags)

- **`-h --help`** — Print help

## Subcommands [​](https://mise.jdx.dev/cli/bootstrap/accounts.html\#subcommands)

- [`mise bootstrap accounts apply [-n --dry-run] [-y --yes]`](https://mise.jdx.dev/cli/bootstrap/accounts/apply.html)
- [`mise bootstrap accounts status [-J --json] [--missing]`](https://mise.jdx.dev/cli/bootstrap/accounts/status.html)

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/accounts.html\#related-documentation)

- [Users and groups](https://mise.jdx.dev/bootstrap/accounts.html).
- [`mise bootstrap [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/bootstrap.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)