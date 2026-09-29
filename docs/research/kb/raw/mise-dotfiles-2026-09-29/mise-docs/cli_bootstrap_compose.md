[Skip to content](https://mise.jdx.dev/cli/bootstrap/compose.html#VPContent)

On this page

# `mise bootstrap compose` [​](https://mise.jdx.dev/cli/bootstrap/compose.html\#mise-bootstrap-compose)

- **Usage:**`mise bootstrap compose <SUBCOMMAND>`
- **Effect:** read-only
- **Source code:** [`src/cli/bootstrap.rs`](https://github.com/jdx/mise/blob/main/src/cli/bootstrap.rs)

Manage Docker Compose projects from `[bootstrap.compose]`

Requires a working Docker engine and Compose command on the target host. `apply` reconciles declared project state; `status` inspects the existing projects.

## Flags [​](https://mise.jdx.dev/cli/bootstrap/compose.html\#flags)

- **`-h --help`** — Print help

## Subcommands [​](https://mise.jdx.dev/cli/bootstrap/compose.html\#subcommands)

- [`mise bootstrap compose apply [-n --dry-run] [-y --yes]`](https://mise.jdx.dev/cli/bootstrap/compose/apply.html)
- [`mise bootstrap compose status [-J --json] [--missing]`](https://mise.jdx.dev/cli/bootstrap/compose/status.html)

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/compose.html\#related-documentation)

- [Compose projects](https://mise.jdx.dev/bootstrap/compose.html).
- [`mise bootstrap [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/bootstrap.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)