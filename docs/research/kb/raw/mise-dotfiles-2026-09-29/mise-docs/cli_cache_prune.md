[Skip to content](https://mise.jdx.dev/cli/cache/prune.html#VPContent)

On this page

# `mise cache prune` [​](https://mise.jdx.dev/cli/cache/prune.html\#mise-cache-prune)

- **Usage:**`mise cache prune [-v --verbose] [--dry-run] [TOOL]…`
- **Aliases:**`p`
- **Effect:** modifies state
- **Source code:** [`src/cli/cache/prune.rs`](https://github.com/jdx/mise/blob/main/src/cli/cache/prune.rs)

Remove stale cache files

By default, this command will remove files that have not been accessed in 30 days. Change this with the MISE\_CACHE\_PRUNE\_AGE environment variable.

## Arguments [​](https://mise.jdx.dev/cli/cache/prune.html\#arguments)

- **`[TOOL]…`** — Tool(s) to prune cache for e.g.: node, python

## Flags [​](https://mise.jdx.dev/cli/cache/prune.html\#flags)

- **`-v --verbose`** — Show pruned files
- **`--dry-run`** — Show what would be pruned without deleting anything
- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/cache/prune.html\#related-documentation)

- [Cache behavior](https://mise.jdx.dev/cache-behavior.html).
- [`mise cache [SUBCOMMAND]`](https://mise.jdx.dev/cli/cache.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)