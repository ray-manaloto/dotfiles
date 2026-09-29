[Skip to content](https://mise.jdx.dev/cli/bootstrap/dotfiles/origin.html#VPContent)

On this page

# `mise bootstrap dotfiles origin` [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/origin.html\#mise-bootstrap-dotfiles-origin)

- **Usage:**`mise bootstrap dotfiles origin [--remove] [SUBCOMMAND]`
- **Effect:** destructive — may delete or irreversibly overwrite
- **Source code:** [`src/cli/dotfiles/origin.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/origin.rs)

Connect or disconnect the setup repository

`set <url>` connects the ordinary tracked-file repository to an origin. All committed history becomes eligible for synchronization, including intermediate commits made before connecting. Preview the sync mode and tracked paths before confirming. Encrypted-file policy is checked across every reachable commit; unrelated histories are never replaced. The connection is written to machine-local `[history.origin]` configuration; the mode is `settings.history.sync`.

## Flags [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/origin.html\#flags)

- **`--remove`** — Disconnect: remove `[history.origin]` (local checkpoints and fetched refs stay)

**Effect:** destructive — may delete or irreversibly overwrite

- **`-h --help`** — Print help


## Subcommands [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/origin.html\#subcommands)

- [`mise bootstrap dotfiles origin set [FLAGS] <URL>`](https://mise.jdx.dev/cli/bootstrap/dotfiles/origin/set.html)

Examples:

```
mise dot origin set https://github.com/you/setup.git
mise dot origin set git@github.com:you/setup.git --sync manual
mise dot origin              # what is connected
mise dot origin --remove
```

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/origin.html\#related-documentation)

- [Dotfile ownership and modes](https://mise.jdx.dev/dotfiles.html).
- [`mise bootstrap dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)