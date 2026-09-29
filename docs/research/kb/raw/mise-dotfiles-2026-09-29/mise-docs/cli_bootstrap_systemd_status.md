[Skip to content](https://mise.jdx.dev/cli/bootstrap/systemd/status.html#VPContent)

On this page

# `mise bootstrap systemd status` [​](https://mise.jdx.dev/cli/bootstrap/systemd/status.html\#mise-bootstrap-systemd-status)

- **Usage:**`mise bootstrap systemd status [-J --json] [--missing]`
- **Effect:** read-only
- **Source code:** [`src/cli/bootstrap.rs`](https://github.com/jdx/mise/blob/main/src/cli/bootstrap.rs)

Show the state of systemd user services from `[bootstrap.linux.systemd.units]`

## Flags [​](https://mise.jdx.dev/cli/bootstrap/systemd/status.html\#flags)

- **`-J --json`** — Output in JSON format
- **`--missing`** — Exit with code 1 if any configured systemd user service is not in its desired state
- **`-h --help`** — Print help

This is a compatibility spelling. Use [`mise bootstrap linux systemd-units status [-J --json] [--missing]`](https://mise.jdx.dev/cli/bootstrap/linux/systemd-units/status.html) in new scripts.

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/systemd/status.html\#related-documentation)

- [systemd user units](https://mise.jdx.dev/bootstrap/systemd.html).
- [`mise bootstrap [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/bootstrap.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)