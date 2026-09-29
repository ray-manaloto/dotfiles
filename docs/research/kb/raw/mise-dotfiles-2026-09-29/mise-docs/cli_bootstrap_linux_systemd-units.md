[Skip to content](https://mise.jdx.dev/cli/bootstrap/linux/systemd-units.html#VPContent)

On this page

# `mise bootstrap linux systemd-units` [​](https://mise.jdx.dev/cli/bootstrap/linux/systemd-units.html\#mise-bootstrap-linux-systemd-units)

- **Usage:**`mise bootstrap linux systemd-units <SUBCOMMAND>`
- **Aliases:**`systemd`
- **Effect:** read-only
- **Source code:** [`src/cli/bootstrap.rs`](https://github.com/jdx/mise/blob/main/src/cli/bootstrap.rs)

Manage systemd user services from `[bootstrap.linux.systemd.units]`

Installs unit files and reconciles services in the current user manager. This is separate from system services declared in `[bootstrap.services]`.

## Flags [​](https://mise.jdx.dev/cli/bootstrap/linux/systemd-units.html\#flags)

- **`-h --help`** — Print help

## Subcommands [​](https://mise.jdx.dev/cli/bootstrap/linux/systemd-units.html\#subcommands)

- [`mise bootstrap linux systemd-units apply [-n --dry-run] [-y --yes]`](https://mise.jdx.dev/cli/bootstrap/linux/systemd-units/apply.html)
- [`mise bootstrap linux systemd-units status [-J --json] [--missing]`](https://mise.jdx.dev/cli/bootstrap/linux/systemd-units/status.html)

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/linux/systemd-units.html\#related-documentation)

- [systemd user units](https://mise.jdx.dev/bootstrap/systemd.html).
- [`mise bootstrap linux <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/linux.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)