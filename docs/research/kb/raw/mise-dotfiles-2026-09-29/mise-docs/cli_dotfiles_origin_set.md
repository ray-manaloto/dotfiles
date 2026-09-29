[Skip to content](https://mise.jdx.dev/cli/dotfiles/origin/set.html#VPContent)

On this page

# `mise dotfiles origin set` [​](https://mise.jdx.dev/cli/dotfiles/origin/set.html\#mise-dotfiles-origin-set)

- **Usage:**`mise dotfiles origin set [FLAGS] <URL>`
- **Effect:** modifies state
- **Source code:** [`src/cli/dotfiles/origin.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/origin.rs)

Connect a setup repository

## Arguments [​](https://mise.jdx.dev/cli/dotfiles/origin/set.html\#arguments)

- **`<URL>`** — The repository url (any git url; a private repository is recommended)

## Flags [​](https://mise.jdx.dev/cli/dotfiles/origin/set.html\#flags)

- **`--branch <BRANCH>`** — The setup branch (default: the repository's own default branch)

Reconnecting a repository this machine already follows keeps that connection's branch. A repository with no branches at all takes `main`, which the first publication creates.

- **`--sync <MODE>`** — How the repository is used: sync, fetch-only, or manual

Prompts when omitted. With --yes, accepts the configured mode (default: sync), including automatic publication and incoming writes. Use --sync manual to keep automatic local history without automatic network activity.

- **`-y --yes`** — Skip the confirmation prompt

- **`-h --help`** — Print help


## Related documentation [​](https://mise.jdx.dev/cli/dotfiles/origin/set.html\#related-documentation)

- [Getting started](https://mise.jdx.dev/getting-started.html).
- [`mise dotfiles origin [--remove] [SUBCOMMAND]`](https://mise.jdx.dev/cli/dotfiles/origin.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)