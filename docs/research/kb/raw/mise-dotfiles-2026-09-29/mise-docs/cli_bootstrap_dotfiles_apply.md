[Skip to content](https://mise.jdx.dev/cli/bootstrap/dotfiles/apply.html#VPContent)

On this page

# `mise bootstrap dotfiles apply` [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/apply.html\#mise-bootstrap-dotfiles-apply)

- **Usage:**`mise bootstrap dotfiles apply [FLAGS] [TARGET]…`
- **Effect:** modifies state
- **Source code:** [`src/cli/dotfiles/apply.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/apply.rs)

Apply dotfiles from `[dotfiles]`

Applies configured whole-file entries and edits that aren't in their desired state. Whole-file entries may symlink, copy, or render templates. Edit entries manage a marker-delimited block or a single line in a file mise doesn't otherwise own.

## Arguments [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/apply.html\#arguments)

- **`[TARGET]…`** — Only apply these targets

## Flags [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/apply.html\#flags)

- **`-f --force`** — Overwrite existing files that conflict with whole-file dotfile entries
- **`-n --dry-run`** — Print the actions that would run without writing anything
- **`-y --yes`** — Skip the confirmation prompt
- **`--prompt-secrets`** — Prompt securely for missing bootstrap secret inputs
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/apply.html\#examples)

```
mise dot apply
mise dot apply --dry-run
mise dot apply --force --yes
```

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/apply.html\#related-documentation)

- [Dotfile ownership and modes](https://mise.jdx.dev/dotfiles.html).
- [`mise bootstrap dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)