[Skip to content](https://mise.jdx.dev/cli/daemons.html#VPContent)

On this page

# `mise daemons` [​](https://mise.jdx.dev/cli/daemons.html\#mise-daemons)

- **Usage:**`mise daemons [--json] [SUBCOMMAND]`
- **Aliases:**`daemon`
- **Effect:** read-only
- **Source code:** [`src/cli/daemons.rs`](https://github.com/jdx/mise/blob/main/src/cli/daemons.rs)

\[experimental\] Manage project daemons with pitchfork

Define commands or managed service presets in \[daemons\]: cockroachdb, nats, postgres, redis, spicedb. With no subcommand, list configured and previously managed daemons.

## Flags [​](https://mise.jdx.dev/cli/daemons.html\#flags)

- **`--json`**
- **`-h --help`** — Print help

## Subcommands [​](https://mise.jdx.dev/cli/daemons.html\#subcommands)

- [`mise daemons logs [ARGS]…`](https://mise.jdx.dev/cli/daemons/logs.html)
- [`mise daemons ls [--json]`](https://mise.jdx.dev/cli/daemons/ls.html)
- [`mise daemons providers [SUBCOMMAND]`](https://mise.jdx.dev/cli/daemons/providers.html)
- [`mise daemons prune [-n --dry-run]`](https://mise.jdx.dev/cli/daemons/prune.html)
- [`mise daemons register`](https://mise.jdx.dev/cli/daemons/register.html)
- [`mise daemons restart [ARGS]…`](https://mise.jdx.dev/cli/daemons/restart.html)
- [`mise daemons start [ARGS]…`](https://mise.jdx.dev/cli/daemons/start.html)
- [`mise daemons status [ARGS]…`](https://mise.jdx.dev/cli/daemons/status.html)
- [`mise daemons stop [ARGS]…`](https://mise.jdx.dev/cli/daemons/stop.html)
- [`mise daemons tui [ARGS]…`](https://mise.jdx.dev/cli/daemons/tui.html)
- [`mise daemons urls [--json]`](https://mise.jdx.dev/cli/daemons/urls.html)

## Related documentation [​](https://mise.jdx.dev/cli/daemons.html\#related-documentation)

- [Getting started](https://mise.jdx.dev/getting-started.html).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)