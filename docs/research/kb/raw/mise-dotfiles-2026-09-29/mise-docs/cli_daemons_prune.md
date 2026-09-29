[Skip to content](https://mise.jdx.dev/cli/daemons/prune.html#VPContent)

On this page

# `mise daemons prune` [​](https://mise.jdx.dev/cli/daemons/prune.html\#mise-daemons-prune)

- **Usage:**`mise daemons prune [-n --dry-run]`
- **Effect:** destructive — may delete or irreversibly overwrite
- **Source code:** [`src/cli/daemons.rs`](https://github.com/jdx/mise/blob/main/src/cli/daemons.rs)

Remove daemon state left behind by deleted project directories.

Scan `$MISE_STATE_DIR/daemons/` for state belonging to deleted projects, including removed Git worktrees. Stop their daemons, unregister their configuration, and delete their state and data. Existing projects are preserved.

Use `--dry-run` to preview the paths and sizes. Removal is irreversible and requires confirmation. Pass the global `--yes` flag for non-interactive cleanup; entries that may belong to an unmounted volume or a deleted symlink are skipped with `--yes` and require separate interactive confirmation.

Pitchfork must be available. State is kept when mise cannot confirm that the daemons have stopped or cannot unregister their configuration.

## Flags [​](https://mise.jdx.dev/cli/daemons/prune.html\#flags)

- **`-n --dry-run`** — Show what would be removed without deleting anything
- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/daemons/prune.html\#related-documentation)

- [Getting started](https://mise.jdx.dev/getting-started.html).
- [`mise daemons [--json] [SUBCOMMAND]`](https://mise.jdx.dev/cli/daemons.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)