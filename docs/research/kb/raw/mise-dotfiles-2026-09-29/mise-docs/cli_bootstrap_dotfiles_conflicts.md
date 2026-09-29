[Skip to content](https://mise.jdx.dev/cli/bootstrap/dotfiles/conflicts.html#VPContent)

On this page

# `mise bootstrap dotfiles conflicts` [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/conflicts.html\#mise-bootstrap-dotfiles-conflicts)

- **Usage:**`mise bootstrap dotfiles conflicts [--difftool] [--tool <TOOL>] [PATH]…`
- **Effect:** read-only
- **Source code:** [`src/cli/dotfiles/conflicts.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/conflicts.rs)

Inspect the local and remote sides of sharing conflicts

By default, prints a unified diff from this machine's saved version to the fetched repository version. `--difftool` opens the comparison in Git's configured diff tool; when `diff.tool` is unset, Git falls back to `merge.tool`. This command does not change either side or resolve a conflict.

## Arguments [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/conflicts.html\#arguments)

- **`[PATH]…`** — Only inspect these conflicted paths

## Flags [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/conflicts.html\#flags)

- **`--difftool`** — Open the comparison in Git's configured diff or merge tool
- **`--tool <TOOL>`** — Use this Git diff tool instead of the configured default
- **`-h --help`** — Print help

Examples:

```
mise dot conflicts
mise dot conflicts ~/.zshrc
mise dot conflicts --difftool ~/.zshrc
mise dot conflicts --difftool --tool meld ~/.zshrc
```

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/conflicts.html\#related-documentation)

- [Dotfile ownership and modes](https://mise.jdx.dev/dotfiles.html).
- [`mise bootstrap dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)