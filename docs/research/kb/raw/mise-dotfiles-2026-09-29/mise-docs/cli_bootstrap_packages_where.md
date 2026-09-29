[Skip to content](https://mise.jdx.dev/cli/bootstrap/packages/where.html#VPContent)

On this page

# `mise bootstrap packages where` [​](https://mise.jdx.dev/cli/bootstrap/packages/where.html\#mise-bootstrap-packages-where)

- **Usage:**`mise bootstrap packages where <PACKAGE>`
- **Effect:** read-only
- **Source code:** [`src/cli/system/where.rs`](https://github.com/jdx/mise/blob/main/src/cli/system/where.rs)

Print the stable root of an installed Homebrew formula

Use an explicit brew:<formula> or brew:<owner>/<tap>/<formula> with the canonical installed formula name. Qualified names use the final component as the local rack name; aliases and tap provenance are not resolved. Settings come from environment variables and global CLI options only. The returned opt path follows upgrades and may change after this lookup. Missing or invalid installations produce empty stdout and a nonzero exit status.

## Arguments [​](https://mise.jdx.dev/cli/bootstrap/packages/where.html\#arguments)

- **`<PACKAGE>`** — Explicit brew formula to locate

## Flags [​](https://mise.jdx.dev/cli/bootstrap/packages/where.html\#flags)

- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/packages/where.html\#related-documentation)

- [Host packages](https://mise.jdx.dev/bootstrap/packages/).
- [`mise bootstrap packages <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/packages.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)