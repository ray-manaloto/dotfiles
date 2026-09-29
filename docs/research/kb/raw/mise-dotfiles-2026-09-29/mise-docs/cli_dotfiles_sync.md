[Skip to content](https://mise.jdx.dev/cli/dotfiles/sync.html#VPContent)

On this page

# `mise dotfiles sync` [​](https://mise.jdx.dev/cli/dotfiles/sync.html\#mise-dotfiles-sync)

- **Usage:**`mise dotfiles sync [FLAGS]`
- **Effect:** modifies state
- **Source code:** [`src/cli/dotfiles/sync.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/sync.rs)

Publish, fetch, and record what is pending now

Fetches the origin branch and publishes the ordinary local commit history. A rejected push fetches again and reconciles without rewriting history. Records incoming changes to apply and conflicts to decide. Live files are never changed here: `mise dot pull` does that. In `fetch-only` mode nothing is published.

The history watcher does this on its own in `sync` and `fetch-only` mode (`settings.history.sync`); this command is for right now.

## Flags [​](https://mise.jdx.dev/cli/dotfiles/sync.html\#flags)

- **`--fetch-only`** — Fetch without publishing
- **`--allow-plaintext-history`** — Allow publishing older unencrypted versions of encrypted files
- **`--best-effort`** — Warn instead of failing when the origin is unreachable
- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/dotfiles/sync.html\#related-documentation)

- [Getting started](https://mise.jdx.dev/getting-started.html).
- [`mise dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)