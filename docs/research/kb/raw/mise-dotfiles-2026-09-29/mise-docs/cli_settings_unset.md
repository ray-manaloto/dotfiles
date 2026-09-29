[Skip to content](https://mise.jdx.dev/cli/settings/unset.html#VPContent)

On this page

# `mise settings unset` [​](https://mise.jdx.dev/cli/settings/unset.html\#mise-settings-unset)

- **Usage:**`mise settings unset [-l --local] <KEY>`
- **Aliases:**`rm`, `remove`, `delete`, `del`
- **Effect:** modifies state
- **Source code:** [`src/cli/settings/unset.rs`](https://github.com/jdx/mise/blob/main/src/cli/settings/unset.rs)

Clear a setting

This modifies ~/.config/mise/config.toml by default, or the local config with `--local`.

## Arguments [​](https://mise.jdx.dev/cli/settings/unset.html\#arguments)

- **`<KEY>`** — The setting to remove

## Flags [​](https://mise.jdx.dev/cli/settings/unset.html\#flags)

- **`-l --local`** — Use the local config file instead of the global one
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/settings/unset.html\#examples)

```
mise settings unset jobs
```

## Related documentation [​](https://mise.jdx.dev/cli/settings/unset.html\#related-documentation)

- [Settings reference](https://mise.jdx.dev/configuration/settings.html).
- [`mise settings [FLAGS] [SETTING] [VALUE] [SUBCOMMAND]`](https://mise.jdx.dev/cli/settings.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)