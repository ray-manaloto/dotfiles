[Skip to content](https://mise.jdx.dev/cli/bootstrap/services.html#VPContent)

Return to top

# `mise bootstrap services` [​](https://mise.jdx.dev/cli/bootstrap/services.html\#mise-bootstrap-services)

- **Usage:**`mise bootstrap services <SUBCOMMAND>`
- **Effect:** read-only
- **Source code:** [`src/cli/bootstrap.rs`](https://github.com/jdx/mise/blob/main/src/cli/bootstrap.rs)

Manage services from `[bootstrap.services]`

System-scope entries (the default) converge existing Linux systemd system units. `scope = "user"` entries are services mise defines for the current user on every platform: a systemd user unit on Linux, a LaunchAgent on macOS, a Scheduled Task on Windows.

## Flags [​](https://mise.jdx.dev/cli/bootstrap/services.html\#flags)

- **`-h --help`** — Print help

## Subcommands [​](https://mise.jdx.dev/cli/bootstrap/services.html\#subcommands)

- [`mise bootstrap services apply [-n --dry-run] [-y --yes]`](https://mise.jdx.dev/cli/bootstrap/services/apply.html)
- [`mise bootstrap services remove [-n --dry-run] <NAME>`](https://mise.jdx.dev/cli/bootstrap/services/remove.html)
- [`mise bootstrap services status [-J --json] [--missing]`](https://mise.jdx.dev/cli/bootstrap/services/status.html)

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/services.html\#related-documentation)

- [System services](https://mise.jdx.dev/bootstrap/services.html).
- [`mise bootstrap [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/bootstrap.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).