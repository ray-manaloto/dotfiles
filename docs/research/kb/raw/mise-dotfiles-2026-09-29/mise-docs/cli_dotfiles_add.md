[Skip to content](https://mise.jdx.dev/cli/dotfiles/add.html#VPContent)

On this page

# `mise dotfiles add` [​](https://mise.jdx.dev/cli/dotfiles/add.html\#mise-dotfiles-add)

- **Usage:**`mise dotfiles add [FLAGS] [TARGET]…`
- **Effect:** modifies state
- **Source code:** [`src/cli/dotfiles/add.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/add.rs)

Add or update dotfiles in `[dotfiles]`

If the target is already managed, this updates its source from the live target. Otherwise it creates a `[dotfiles]` entry and seeds the source under `dotfiles.root` unless `--source` is provided. Captured entries are applied unless `--no-apply` is passed. Use `--dry-run` to preview both the source capture and config write without making those changes.

## Arguments [​](https://mise.jdx.dev/cli/dotfiles/add.html\#arguments)

- **`[TARGET]…`** — Targets to add or update

## Flags [​](https://mise.jdx.dev/cli/dotfiles/add.html\#flags)

- **`--changed`** — Update the sources of every changed file managed in copy mode
- **`-f --force`** — Overwrite existing sources without prompting
- **`-g --global`** — Write to the global config
- **`-l --local`** — Write to the local config instead of the global config
- **`-m --mode <MODE>`** — Dotfile mode to write
- **`-n --dry-run`** — Print the config/source updates without writing anything
- **`--no-apply`** — Add the entry without applying it
- **`-p --path <PATH>`** — Write to this config file or directory
- **`-s --source <PATH>`** — Source path to use for a single target
- **`-y --yes`** — Skip the confirmation prompt
- **`--prompt-secrets`** — Prompt securely for missing bootstrap secret inputs
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/dotfiles/add.html\#examples)

```
mise dot add ~/.zshrc
mise dot add --mode copy ~/.config/starship.toml
mise dot add --source dotfiles/gitconfig ~/.gitconfig
mise dot add --changed
```

## Related documentation [​](https://mise.jdx.dev/cli/dotfiles/add.html\#related-documentation)

- [Getting started](https://mise.jdx.dev/getting-started.html).
- [`mise dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)