[Skip to content](https://mise.jdx.dev/cli/bootstrap/dotfiles/exclude.html#VPContent)

On this page

# `mise bootstrap dotfiles exclude` [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/exclude.html\#mise-bootstrap-dotfiles-exclude)

- **Usage:**`mise bootstrap dotfiles exclude <GLOB>`
- **Effect:** modifies state
- **Source code:** [`src/cli/dotfiles/exclude.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/exclude.rs)

Never capture paths matching a glob

Adds a glob to `[history] exclude` in the global configuration. The rule applies to all tracked paths. Quote the glob to prevent your shell from expanding it.

Use exclusions for logs, caches, databases, and session state. For configuration you want to save manually, use `--no-autosave` instead. To scope selection to one directory, edit that `[dotfiles]` entry's `exclude` or `include` list.

## Arguments [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/exclude.html\#arguments)

- **`<GLOB>`** — A glob such as `~/.config/hypr/plugins/**`

## Flags [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/exclude.html\#flags)

- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/exclude.html\#related-documentation)

- [Dotfile ownership and modes](https://mise.jdx.dev/dotfiles.html).
- [`mise bootstrap dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)