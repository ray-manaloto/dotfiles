[Skip to content](https://mise.jdx.dev/cli/sync/ruby.html#VPContent)

On this page

# `mise sync ruby` [​](https://mise.jdx.dev/cli/sync/ruby.html\#mise-sync-ruby)

- **Usage:**`mise sync ruby <--brew>`
- **Effect:** modifies state
- **Source code:** [`src/cli/sync/ruby.rs`](https://github.com/jdx/mise/blob/main/src/cli/sync/ruby.rs)

Symlink ruby versions installed by Homebrew into mise

## Flags [​](https://mise.jdx.dev/cli/sync/ruby.html\#flags)

- **`--brew`** — Get tool versions from Homebrew
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/sync/ruby.html\#examples)

```
brew install ruby
mise sync ruby --brew
mise ls ruby --installed # inspect linked versions, then select one with mise use
```

## Related documentation [​](https://mise.jdx.dev/cli/sync/ruby.html\#related-documentation)

- [Ruby](https://mise.jdx.dev/lang/ruby.html).
- [`mise sync <SUBCOMMAND>`](https://mise.jdx.dev/cli/sync.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)