[Skip to content](https://mise.jdx.dev/cli/bootstrap/packages/brew.html#VPContent)

On this page

# `mise bootstrap packages brew` [​](https://mise.jdx.dev/cli/bootstrap/packages/brew.html\#mise-bootstrap-packages-brew)

- **Usage:**`mise bootstrap packages brew <SUBCOMMAND>`
- **Effect:** read-only
- **Source code:** [`src/cli/system/brew/mod.rs`](https://github.com/jdx/mise/blob/main/src/cli/system/brew/mod.rs)

Manage Homebrew taps used by bootstrap packages

These commands edit `[bootstrap.brew.taps]` so tapped formulae and casks can be fetched directly by mise without a Homebrew installation.

## Flags [​](https://mise.jdx.dev/cli/bootstrap/packages/brew.html\#flags)

- **`-h --help`** — Print help

## Subcommands [​](https://mise.jdx.dev/cli/bootstrap/packages/brew.html\#subcommands)

- [`mise bootstrap packages brew tap [FLAGS] <TAP> [URL]`](https://mise.jdx.dev/cli/bootstrap/packages/brew/tap.html)
- [`mise bootstrap packages brew untap [FLAGS] <TAPS>…`](https://mise.jdx.dev/cli/bootstrap/packages/brew/untap.html)

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/packages/brew.html\#related-documentation)

- [Homebrew packages and taps](https://mise.jdx.dev/bootstrap/packages/brew.html).
- [`mise bootstrap packages <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/packages.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)