[Skip to content](https://mise.jdx.dev/cli/bootstrap/firewall.html#VPContent)

On this page

# `mise bootstrap firewall` [​](https://mise.jdx.dev/cli/bootstrap/firewall.html\#mise-bootstrap-firewall)

- **Usage:**`mise bootstrap firewall <SUBCOMMAND>`
- **Effect:** read-only
- **Source code:** [`src/cli/bootstrap.rs`](https://github.com/jdx/mise/blob/main/src/cli/bootstrap.rs)

Manage the Linux host firewall from `[bootstrap.linux.firewall]`

This manages host firewall policy and rules. Review `apply --dry-run` before applying a policy to a remote machine, including the rule that permits your SSH connection.

## Flags [​](https://mise.jdx.dev/cli/bootstrap/firewall.html\#flags)

- **`-h --help`** — Print help

## Subcommands [​](https://mise.jdx.dev/cli/bootstrap/firewall.html\#subcommands)

- [`mise bootstrap firewall apply [-n --dry-run] [-y --yes]`](https://mise.jdx.dev/cli/bootstrap/firewall/apply.html)
- [`mise bootstrap firewall status [-J --json] [--missing]`](https://mise.jdx.dev/cli/bootstrap/firewall/status.html)

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/firewall.html\#related-documentation)

- [Host firewall](https://mise.jdx.dev/bootstrap/firewall.html).
- [`mise bootstrap [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/bootstrap.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)