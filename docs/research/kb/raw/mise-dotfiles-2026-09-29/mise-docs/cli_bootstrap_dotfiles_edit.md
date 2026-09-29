[Skip to content](https://mise.jdx.dev/cli/bootstrap/dotfiles/edit.html#VPContent)

On this page

# `mise bootstrap dotfiles edit` [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/edit.html\#mise-bootstrap-dotfiles-edit)

- **Usage:**`mise bootstrap dotfiles edit [FLAGS] <TARGET>`
- **Effect:** modifies state
- **Source code:** [`src/cli/dotfiles/edit.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/edit.rs)

Edit a managed dotfile source

## Arguments [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/edit.html\#arguments)

- **`<TARGET>`** — Target to edit

## Flags [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/edit.html\#flags)

- **`--apply`** — Apply this target after the editor exits
- **`-m --mode <MODE>`** — Dotfile mode to use if the target is not yet managed
- **`-s --source <PATH>`** — Source path to use if the target is not yet managed
- **`-y --yes`** — Skip the confirmation prompt when adding an unmanaged target
- **`--prompt-secrets`** — Prompt securely for missing bootstrap secret inputs
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/edit.html\#examples)

```
mise dot edit ~/.zshrc
mise dot edit --apply ~/.config/starship.toml
```

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/edit.html\#related-documentation)

- [Dotfile ownership and modes](https://mise.jdx.dev/dotfiles.html).
- [`mise bootstrap dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)