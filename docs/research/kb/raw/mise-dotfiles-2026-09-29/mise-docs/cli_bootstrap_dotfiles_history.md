[Skip to content](https://mise.jdx.dev/cli/bootstrap/dotfiles/history.html#VPContent)

On this page

# `mise bootstrap dotfiles history` [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/history.html\#mise-bootstrap-dotfiles-history)

- **Usage:**`mise bootstrap dotfiles history [FLAGS] [SUBCOMMAND]`
- **Effect:** read-only
- **Source code:** [`src/cli/dotfiles/history/mod.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/history/mod.rs)

Browse the checkpoints of your dotfiles

Every save, every mutating bootstrap command, and the watcher record a checkpoint of explicitly enrolled `[dotfiles]` entries with `mode = "track"`. Configuration and deployment sources are not implicitly enrolled. A checkpoint holds files, never package or service state: restoring one restores files. Without a subcommand this lists them, newest first.

## Flags [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/history.html\#flags)

- **`-J --json`** — Output in JSON format

- **`-n --limit <LIMIT>`** — Show at most this many checkpoints (0 for all)

**Default:**`20`

- **`--path <PATH>`** — Only checkpoints where this path (or something under it) changed

- **`--trigger <TRIGGER>`** — Only checkpoints with this trigger (edit, save, bootstrap, …)

- **`--label <LABEL>`** — Only checkpoints with this label

- **`--pending`** — Only checkpoints recorded by operations that did not finish

- **`-h --help`** — Print help


## Subcommands [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/history.html\#subcommands)

- [`mise bootstrap dotfiles history describe <REF> <TEXT>`](https://mise.jdx.dev/cli/bootstrap/dotfiles/history/describe.html)
- [`mise bootstrap dotfiles history diff [FLAGS] [A] [B]`](https://mise.jdx.dev/cli/bootstrap/dotfiles/history/diff.html)
- [`mise bootstrap dotfiles history ls [FLAGS]`](https://mise.jdx.dev/cli/bootstrap/dotfiles/history/ls.html)
- [`mise bootstrap dotfiles history show [FLAGS] [REF]`](https://mise.jdx.dev/cli/bootstrap/dotfiles/history/show.html)

Examples:

```
mise dot history
mise dot history --path ~/.config/hypr/bindings.lua
mise dot history show latest
mise dot history diff          # the working tree against the latest checkpoint
mise dot history diff 11 12 --patch
mise dot save --description "before the theme change"
mise dot rollback ~/.config/hypr/bindings.lua
mise dot undo
```

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/history.html\#related-documentation)

- [Dotfile ownership and modes](https://mise.jdx.dev/dotfiles.html).
- [`mise bootstrap dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)