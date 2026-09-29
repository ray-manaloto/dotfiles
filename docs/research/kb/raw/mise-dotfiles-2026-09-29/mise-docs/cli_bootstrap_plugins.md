[Skip to content](https://mise.jdx.dev/cli/bootstrap/plugins.html#VPContent)

On this page

# `mise bootstrap plugins` [​](https://mise.jdx.dev/cli/bootstrap/plugins.html\#mise-bootstrap-plugins)

- **Usage:**`mise bootstrap plugins <SUBCOMMAND>`
- **Effect:** read-only
- **Source code:** [`src/cli/bootstrap.rs`](https://github.com/jdx/mise/blob/main/src/cli/bootstrap.rs)

Manage package manager plugins declared in `[bootstrap.plugins]`

Install these plugins before applying packages they manage. Installing a plugin does not itself install the host packages in `[bootstrap.packages]`.

## Flags [​](https://mise.jdx.dev/cli/bootstrap/plugins.html\#flags)

- **`-h --help`** — Print help

## Subcommands [​](https://mise.jdx.dev/cli/bootstrap/plugins.html\#subcommands)

- [`mise bootstrap plugins apply [-n --dry-run]`](https://mise.jdx.dev/cli/bootstrap/plugins/apply.html)
- [`mise bootstrap plugins status [--missing]`](https://mise.jdx.dev/cli/bootstrap/plugins/status.html)

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/plugins.html\#related-documentation)

- [Package plugins](https://mise.jdx.dev/bootstrap/packages/plugins.html).
- [`mise bootstrap [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/bootstrap.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)