[Skip to content](https://mise.jdx.dev/cli/bootstrap/dotfiles/track.html#VPContent)

On this page

# `mise bootstrap dotfiles track` [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/track.html\#mise-bootstrap-dotfiles-track)

- **Usage:**`mise bootstrap dotfiles track [FLAGS] <PATH>…`
- **Effect:** modifies state
- **Source code:** [`src/cli/dotfiles/track.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/track.rs)

Track a file or directory in place

Adds a `[dotfiles]` entry with `mode = "track"`: the file stays where it is, nothing is copied or linked, and history saves a checkpoint of it right away. With the history watcher service running, later edits are saved automatically; without it, `mise dot save` saves them.

`--os` and `--profile` declare a variant: a separate shared stream for machines matching that platform or mise environment, so a Mac and a Linux box can share the same live path with different contents.

## Arguments [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/track.html\#arguments)

- **`<PATH>…`** — Paths to track (absolute or starting with ~/)

## Flags [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/track.html\#flags)

- **`--os <OS>`** — Declare a variant for this platform (macos, linux, linux/arm64, …)
- **`--profile <PROFILE>`** — Declare a variant for this mise environment
- **`--no-autosave`** — Save only on `mise dot save <path>`, never automatically
- **`--encrypt`** — Encrypt contents before saving them to history (requires `[history.encryption].recipients`)
- **`--allow-plaintext`** — Save an explicitly tracked credential-named file in plaintext
- **`-y --yes`** — Accept without prompting
- **`-n --dry-run`** — Show what each path expands to (files, size, what is left out) without tracking it
- **`-h --help`** — Print help

Examples:

```
mise dot track ~/.zshrc ~/.config/hypr
mise dot track --dry-run ~/.codex
mise dot track ~/.zshrc --os macos
mise dot track ~/.config/app/credentials --encrypt
mise dot track ~/.config/app/state.json --no-autosave
```

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/dotfiles/track.html\#related-documentation)

- [Dotfile ownership and modes](https://mise.jdx.dev/dotfiles.html).
- [`mise bootstrap dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)