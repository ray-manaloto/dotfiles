[Skip to content](https://mise.jdx.dev/cli/daemons/register.html#VPContent)

On this page

# `mise daemons register` [​](https://mise.jdx.dev/cli/daemons/register.html\#mise-daemons-register)

- **Usage:**`mise daemons register`
- **Effect:** modifies state
- **Source code:** [`src/cli/daemons.rs`](https://github.com/jdx/mise/blob/main/src/cli/daemons.rs)

Prepare all project daemons for on-demand startup without starting them.

Install missing tools, validate daemon definitions and dependencies, and register the generated configuration with Pitchfork. Includes imported dependencies and daemons outside the default group. Existing daemons keep running; this command does not start or restart them.

A running Pitchfork supervisor with its proxy enabled can then start a registered HTTP daemon when a request reaches its hostname.

## Flags [​](https://mise.jdx.dev/cli/daemons/register.html\#flags)

- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/daemons/register.html\#related-documentation)

- [Getting started](https://mise.jdx.dev/getting-started.html).
- [`mise daemons [--json] [SUBCOMMAND]`](https://mise.jdx.dev/cli/daemons.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)