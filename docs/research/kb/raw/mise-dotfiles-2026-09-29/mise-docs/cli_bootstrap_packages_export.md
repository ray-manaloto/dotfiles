[Skip to content](https://mise.jdx.dev/cli/bootstrap/packages/export.html#VPContent)

On this page

# `mise bootstrap packages export` [​](https://mise.jdx.dev/cli/bootstrap/packages/export.html\#mise-bootstrap-packages-export)

- **Usage:**`mise bootstrap packages export <--format <FORMAT>>`
- **Effect:** read-only
- **Source code:** [`src/cli/bootstrap.rs`](https://github.com/jdx/mise/blob/main/src/cli/bootstrap.rs)

Export active Nix bootstrap packages as a NixOS module

Writes to stdout without invoking Nix. Import the output into an existing NixOS configuration; packages resolve against that configuration's `pkgs`. Only shorthand attribute paths are exportable. Explicit flake references and package-version pins cannot be represented by the importing package set.

## Flags [​](https://mise.jdx.dev/cli/bootstrap/packages/export.html\#flags)

- **`--format <FORMAT>`** — Output format

**Choices:**`nix`

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/bootstrap/packages/export.html\#examples)

```
mise bootstrap packages export --format nix > packages.nix
```

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/packages/export.html\#related-documentation)

- [Host packages](https://mise.jdx.dev/bootstrap/packages/).
- [`mise bootstrap packages <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/packages.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)