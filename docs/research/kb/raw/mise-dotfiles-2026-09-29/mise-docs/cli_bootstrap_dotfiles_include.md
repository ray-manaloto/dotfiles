[Skip to content](https://mise.jdx.dev/cli/bootstrap/dotfiles/include.html#VPContent)

On this page

# `mise bootstrap dotfiles include` [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/include.html\#mise-bootstrap-dotfiles-include)

- **Usage:**`mise bootstrap dotfiles include <GLOB>`
- **Effect:** modifies state
- **Source code:** [`src/cli/dotfiles/exclude.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/exclude.rs)

Stop excluding paths matching a glob

Removes the specified glob from `[history] exclude` in the global configuration. Pass the same pattern used with `mise dot exclude`:

```
mise dot exclude '~/.codex/sessions/**'
mise dot include '~/.codex/sessions/**'
```

Other matching exclusion rules still apply. This command does not edit a tracked directory's `include` list; change that field in `[dotfiles]` to select which files the directory saves.

## Arguments [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/include.html\#arguments)

- **`<GLOB>`** — The glob as written by `mise dot exclude`

## Flags [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/include.html\#flags)

- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/include.html\#related-documentation)

- [Dotfile ownership and modes](https://mise.jdx.dev/dotfiles.html).
- [`mise bootstrap dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)