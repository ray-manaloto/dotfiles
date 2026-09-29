[Skip to content](https://mise.jdx.dev/cli/dotfiles/unapply.html#VPContent)

On this page

# `mise dotfiles unapply` [​](https://mise.jdx.dev/cli/dotfiles/unapply.html\#mise-dotfiles-unapply)

- **Usage:**`mise dotfiles unapply [FLAGS] [TARGET]…`
- **Effect:** destructive — may delete or irreversibly overwrite
- **Source code:** [`src/cli/dotfiles/unapply.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/unapply.rs)

Remove dotfiles applied from `[dotfiles]`

Removes configured whole-file entries and edits while preserving files mise cannot identify as managed. Modified copies, templates, and plain-line edits require `--force`. Source files and configuration entries are retained. Run this before deleting a declaration so mise can still identify its targets.

## Arguments [​](https://mise.jdx.dev/cli/dotfiles/unapply.html\#arguments)

- **`[TARGET]…`** — Only unapply these targets

## Flags [​](https://mise.jdx.dev/cli/dotfiles/unapply.html\#flags)

- **`-f --force`** — Remove modified or otherwise ambiguous managed files and lines
- **`-n --dry-run`** — Print the actions that would run without writing anything
- **`-y --yes`** — Skip the confirmation prompt
- **`--prompt-secrets`** — Prompt securely for missing bootstrap secret inputs
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/dotfiles/unapply.html\#examples)

```
mise dot unapply
mise dot unapply ~/.zshrc
mise dot unapply --dry-run
mise dot unapply --force --yes
```

## Related documentation [​](https://mise.jdx.dev/cli/dotfiles/unapply.html\#related-documentation)

- [Getting started](https://mise.jdx.dev/getting-started.html).
- [`mise dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)