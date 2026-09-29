[Skip to content](https://mise.jdx.dev/cli/shell-alias/ls.html#VPContent)

On this page

# `mise shell-alias ls` [​](https://mise.jdx.dev/cli/shell-alias/ls.html\#mise-shell-alias-ls)

- **Usage:**`mise shell-alias ls [--no-header]`
- **Aliases:**`list`
- **Effect:** read-only
- **Source code:** [`src/cli/shell_alias/ls.rs`](https://github.com/jdx/mise/blob/main/src/cli/shell_alias/ls.rs)

List shell aliases

Shows the shell aliases that are set in the current directory. These are defined in `mise.toml` under the `[shell_alias]` section.

## Flags [​](https://mise.jdx.dev/cli/shell-alias/ls.html\#flags)

- **`--no-header`** — Don't show table header
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/shell-alias/ls.html\#examples)

```
mise shell-alias ls
alias    command
ll       ls -la
gs       git status
```

## Related documentation [​](https://mise.jdx.dev/cli/shell-alias/ls.html\#related-documentation)

- [Shell aliases](https://mise.jdx.dev/shell-aliases.html).
- [`mise shell-alias [--no-header] [SUBCOMMAND]`](https://mise.jdx.dev/cli/shell-alias.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)