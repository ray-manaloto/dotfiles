[Skip to content](https://mise.jdx.dev/cli/bootstrap/systemd/apply.html#VPContent)

On this page

# `mise bootstrap systemd apply` [​](https://mise.jdx.dev/cli/bootstrap/systemd/apply.html\#mise-bootstrap-systemd-apply)

- **Usage:**`mise bootstrap systemd apply [-n --dry-run] [-y --yes]`
- **Effect:** modifies state
- **Source code:** [`src/cli/bootstrap.rs`](https://github.com/jdx/mise/blob/main/src/cli/bootstrap.rs)

Install and start systemd user services from `[bootstrap.linux.systemd.units]`

## Flags [​](https://mise.jdx.dev/cli/bootstrap/systemd/apply.html\#flags)

- **`-n --dry-run`** — Print the commands that would run without running them
- **`-y --yes`** — Skip the confirmation prompt
- **`-h --help`** — Print help

This is a compatibility spelling. Use [`mise bootstrap linux systemd-units apply [-n --dry-run] [-y --yes]`](https://mise.jdx.dev/cli/bootstrap/linux/systemd-units/apply.html) in new scripts.

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/systemd/apply.html\#related-documentation)

- [systemd user units](https://mise.jdx.dev/bootstrap/systemd.html).
- [`mise bootstrap [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/bootstrap.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)