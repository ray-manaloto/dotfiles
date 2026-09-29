[Skip to content](https://mise.jdx.dev/cli/bootstrap/packages/brew/tap.html#VPContent)

On this page

# `mise bootstrap packages brew tap` [​](https://mise.jdx.dev/cli/bootstrap/packages/brew/tap.html\#mise-bootstrap-packages-brew-tap)

- **Usage:**`mise bootstrap packages brew tap [FLAGS] <TAP> [URL]`
- **Effect:** modifies state
- **Source code:** [`src/cli/system/brew/mod.rs`](https://github.com/jdx/mise/blob/main/src/cli/system/brew/mod.rs)

Add a Homebrew tap URL to \[bootstrap.brew.taps\]

## Arguments [​](https://mise.jdx.dev/cli/bootstrap/packages/brew/tap.html\#arguments)

- **`<TAP>`** — Tap name, e.g. `owner/repo`
- **`[URL]`** — Repository URL for the tap; defaults to GitHub's owner/homebrew-repo.git naming

## Flags [​](https://mise.jdx.dev/cli/bootstrap/packages/brew/tap.html\#flags)

- **`-l --local`** — Write to the local config instead of the global config

- **`-n --dry-run`** — Print the config change without writing it

- **`-p --path <PATH>`** — Write to this config file or directory

**Aliases:**`--file`

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/bootstrap/packages/brew/tap.html\#examples)

```
mise bootstrap packages brew tap railwaycat/emacsmacport
mise bootstrap packages brew tap acme/tools https://github.com/acme/homebrew-tools.git
```

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/packages/brew/tap.html\#related-documentation)

- [Homebrew packages and taps](https://mise.jdx.dev/bootstrap/packages/brew.html).
- [`mise bootstrap packages brew <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/packages/brew.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)