[Skip to content](https://mise.jdx.dev/cli/daemons/urls.html#VPContent)

On this page

# `mise daemons urls` [​](https://mise.jdx.dev/cli/daemons/urls.html\#mise-daemons-urls)

- **Usage:**`mise daemons urls [--json]`
- **Effect:** read-only
- **Source code:** [`src/cli/daemons.rs`](https://github.com/jdx/mise/blob/main/src/cli/daemons.rs)

Show each project daemon's port and its proxy hostname URL.

Hostnames do not move between git worktrees, so an HTTP service can be addressed by URL while concurrent checkouts keep separate ports. A daemon with no port, or with proxy = false, is listed with its port alone.

## Flags [​](https://mise.jdx.dev/cli/daemons/urls.html\#flags)

- **`--json`**
- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/daemons/urls.html\#related-documentation)

- [Getting started](https://mise.jdx.dev/getting-started.html).
- [`mise daemons [--json] [SUBCOMMAND]`](https://mise.jdx.dev/cli/daemons.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)