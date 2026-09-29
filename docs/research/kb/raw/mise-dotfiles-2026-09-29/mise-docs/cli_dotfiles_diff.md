[Skip to content](https://mise.jdx.dev/cli/dotfiles/diff.html#VPContent)

On this page

# `mise dotfiles diff` [​](https://mise.jdx.dev/cli/dotfiles/diff.html\#mise-dotfiles-diff)

- **Usage:**`mise dotfiles diff [--prompt-secrets] [TARGET]…`
- **Effect:** read-only
- **Source code:** [`src/cli/dotfiles/diff.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/diff.rs)

Show the changes needed to apply dotfiles from `[dotfiles]`

## Arguments [​](https://mise.jdx.dev/cli/dotfiles/diff.html\#arguments)

- **`[TARGET]…`** — Only show these targets

## Flags [​](https://mise.jdx.dev/cli/dotfiles/diff.html\#flags)

- **`--prompt-secrets`** — Prompt securely for missing bootstrap secret inputs
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/dotfiles/diff.html\#examples)

```
mise dot diff
mise dot diff ~/.zshrc
```

## Related documentation [​](https://mise.jdx.dev/cli/dotfiles/diff.html\#related-documentation)

- [Getting started](https://mise.jdx.dev/getting-started.html).
- [`mise dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)