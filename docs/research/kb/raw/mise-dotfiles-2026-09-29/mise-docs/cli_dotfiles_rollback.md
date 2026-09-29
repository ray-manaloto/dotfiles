[Skip to content](https://mise.jdx.dev/cli/dotfiles/rollback.html#VPContent)

On this page

# `mise dotfiles rollback` [​](https://mise.jdx.dev/cli/dotfiles/rollback.html\#mise-dotfiles-rollback)

- **Usage:**`mise dotfiles rollback [FLAGS] [PATH]…`
- **Effect:** destructive — may delete or irreversibly overwrite
- **Source code:** [`src/cli/dotfiles/rollback.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/rollback.rs)

Return files to the version a checkpoint holds

Without `--to`, each path returns to its most recent saved version that differs from what is on disk; unrelated checkpoints never influence the choice. With `--to <ref>`, the named checkpoint is the source, and `--all` selects everything it covers. The current state is saved in a protective checkpoint first, so `mise dot undo` can reverse it.

## Arguments [​](https://mise.jdx.dev/cli/dotfiles/rollback.html\#arguments)

- **`[PATH]…`** — Paths to roll back (files or directories)

## Flags [​](https://mise.jdx.dev/cli/dotfiles/rollback.html\#flags)

- **`--to <REF>`** — The checkpoint to roll back to: numeric ID, `latest`, `latest~N`, or `commit:<sha>`
- **`--all`** — With --to: everything the checkpoint covers
- **`-n --dry-run`** — Show the plan without changing anything
- **`-y --yes`** — Apply without prompting
- **`--force`** — Replace a path whose type changed (file, symlink, directory)
- **`-h --help`** — Print help

Examples:

```
mise dot rollback ~/.config/hypr/bindings.lua
mise dot rollback ~/.zshrc --to 42
mise dot rollback --to latest~3 --all --dry-run
```

## Related documentation [​](https://mise.jdx.dev/cli/dotfiles/rollback.html\#related-documentation)

- [Getting started](https://mise.jdx.dev/getting-started.html).
- [`mise dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)