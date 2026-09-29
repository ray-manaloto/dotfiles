[Skip to content](https://mise.jdx.dev/cli/packslip.html#VPContent)

On this page

# `mise packslip` [​](https://mise.jdx.dev/cli/packslip.html\#mise-packslip)

- **Usage:**`mise packslip [SUBCOMMAND]`
- **Effect:** read-only
- **Source code:** [`src/cli/packslip/mod.rs`](https://github.com/jdx/mise/blob/main/src/cli/packslip/mod.rs)

The signers mise accepts packslips from

A tool installed with the `packslip:` backend is verified against the identity its project name implies, and mise then remembers which signer it accepted, the way SSH remembers hosts. A later release from another signer, a weaker scheme, a repackager where the vendor signed before, or one that drops build provenance is refused until a person says so.

## Flags [​](https://mise.jdx.dev/cli/packslip.html\#flags)

- **`-h --help`** — Print help

## Subcommands [​](https://mise.jdx.dev/cli/packslip.html\#subcommands)

- [`mise packslip forget <PROJECT>`](https://mise.jdx.dev/cli/packslip/forget.html)
- [`mise packslip pins [-J --json]`](https://mise.jdx.dev/cli/packslip/pins.html)

## Related documentation [​](https://mise.jdx.dev/cli/packslip.html\#related-documentation)

- [Signer verification](https://mise.jdx.dev/dev-tools/packslip-verification.html).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)