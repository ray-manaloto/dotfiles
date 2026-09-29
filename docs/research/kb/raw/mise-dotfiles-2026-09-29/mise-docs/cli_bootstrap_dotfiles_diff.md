[Skip to content](https://mise.jdx.dev/cli/bootstrap/dotfiles/diff.html#VPContent)

On this page

# `mise bootstrap dotfiles diff` [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/diff.html\#mise-bootstrap-dotfiles-diff)

- **Usage:**`mise bootstrap dotfiles diff [--prompt-secrets] [TARGET]…`
- **Effect:** read-only
- **Source code:** [`src/cli/bootstrap.rs`](https://github.com/jdx/mise/blob/main/src/cli/bootstrap.rs)

Show the changes needed to apply dotfiles from `[dotfiles]`

## Arguments [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/diff.html\#arguments)

- **`[TARGET]…`** — Only show these targets

## Flags [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/diff.html\#flags)

- **`--prompt-secrets`** — Prompt securely for missing bootstrap secret inputs
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/diff.html\#examples)

```
mise dot diff
mise dot diff ~/.zshrc
```

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/diff.html\#related-documentation)

- [Dotfile ownership and modes](https://mise.jdx.dev/dotfiles.html).
- [`mise bootstrap dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)