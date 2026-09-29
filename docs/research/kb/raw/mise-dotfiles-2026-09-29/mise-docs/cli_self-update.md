[Skip to content](https://mise.jdx.dev/cli/self-update.html#VPContent)

On this page

# `mise self-update` [​](https://mise.jdx.dev/cli/self-update.html\#mise-self-update)

- **Usage:**`mise self-update [FLAGS] [VERSION]`
- **Effect:** modifies state
- **Source code:** [`src/cli/self_update.rs`](https://github.com/jdx/mise/blob/main/src/cli/self_update.rs)

Update mise itself

Selects the newest stable release satisfying the minimum release age (24h by default). Explicit versions bypass the delay. Downloads binaries from GitHub Releases. By default, this will also update any installed plugins. Uses mise's GitHub token resolution chain for authenticated requests.

Packagers can disable this command so that mise is updated through the package manager instead. See [https://mise.jdx.dev/contributing.html#packaging-and-self-update-instructions](https://mise.jdx.dev/contributing.html#packaging-and-self-update-instructions)

## Arguments [​](https://mise.jdx.dev/cli/self-update.html\#arguments)

- **`[VERSION]`** — Update to a specific version

## Flags [​](https://mise.jdx.dev/cli/self-update.html\#flags)

- **`--minimum-release-age <MINIMUM_RELEASE_AGE>`** — Override the minimum release age for unpinned updates (default: 24h)
- **`-f --force`** — Update even if already up to date
- **`-y --yes`** — Skip confirmation prompt
- **`--no-plugins`** — Disable auto-updating plugins
- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/self-update.html\#related-documentation)

- [Installing and updating mise](https://mise.jdx.dev/installing-mise.html).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)