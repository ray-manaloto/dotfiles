[Skip to content](https://mise.jdx.dev/cli/packslip/forget.html#VPContent)

On this page

# `mise packslip forget` [​](https://mise.jdx.dev/cli/packslip/forget.html\#mise-packslip-forget)

- **Usage:**`mise packslip forget <PROJECT>`
- **Effect:** modifies state
- **Source code:** [`src/cli/packslip/forget.rs`](https://github.com/jdx/mise/blob/main/src/cli/packslip/forget.rs)

Forget a project's pinned signer, so the next release accepted sets it again

Do this when the vendor has announced a new signing identity or key. The project is named as the packslip backend names it: `github.com/owner/repo`, `owner/repo`, or a host such as `tool.example.com`, with or without the `packslip:` prefix.

## Arguments [​](https://mise.jdx.dev/cli/packslip/forget.html\#arguments)

- **`<PROJECT>`** — The project whose pin to drop

## Flags [​](https://mise.jdx.dev/cli/packslip/forget.html\#flags)

- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/packslip/forget.html\#related-documentation)

- [Signer verification](https://mise.jdx.dev/dev-tools/packslip-verification.html).
- [`mise packslip [SUBCOMMAND]`](https://mise.jdx.dev/cli/packslip.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)