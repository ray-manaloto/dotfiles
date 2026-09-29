[Skip to content](https://mise.jdx.dev/cli/dotfiles/paths.html#VPContent)

On this page

# `mise dotfiles paths` [​](https://mise.jdx.dev/cli/dotfiles/paths.html\#mise-dotfiles-paths)

- **Usage:**`mise dotfiles paths [FLAGS]`
- **Effect:** read-only
- **Source code:** [`src/cli/dotfiles/paths.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/paths.rs)

Show what history tracks and under which policies

Every entry is listed with the file that declared it, its policies, and how many files it currently covers. Declarations that history could not honour are listed as invalid, omitted, or incomplete, so a failed enrollment is never mistaken for protection.

## Flags [​](https://mise.jdx.dev/cli/dotfiles/paths.html\#flags)

- **`-J --json`** — Output in JSON format
- **`--preview <PATH>`** — Show what tracking this path would capture
- **`--noisy`** — List the paths the watcher found changing constantly
- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/dotfiles/paths.html\#related-documentation)

- [Getting started](https://mise.jdx.dev/getting-started.html).
- [`mise dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)