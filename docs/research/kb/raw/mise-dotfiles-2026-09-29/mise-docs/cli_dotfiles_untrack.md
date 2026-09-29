[Skip to content](https://mise.jdx.dev/cli/dotfiles/untrack.html#VPContent)

On this page

# `mise dotfiles untrack` [​](https://mise.jdx.dev/cli/dotfiles/untrack.html\#mise-dotfiles-untrack)

- **Usage:**`mise dotfiles untrack <PATH>…`
- **Effect:** modifies state
- **Source code:** [`src/cli/dotfiles/untrack.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/untrack.rs)

Stop tracking a file or directory

Removes the `[dotfiles]` track entry (or switches an inherited one off in config.local.toml) and stops future captures. The file itself and its existing checkpoints are left exactly as they are.

## Arguments [​](https://mise.jdx.dev/cli/dotfiles/untrack.html\#arguments)

- **`<PATH>…`** — Paths to stop tracking

## Flags [​](https://mise.jdx.dev/cli/dotfiles/untrack.html\#flags)

- **`-h --help`** — Print help

Examples:

```
mise dot untrack ~/.zshrc
```

## Related documentation [​](https://mise.jdx.dev/cli/dotfiles/untrack.html\#related-documentation)

- [Getting started](https://mise.jdx.dev/getting-started.html).
- [`mise dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)