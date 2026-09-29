[Skip to content](https://mise.jdx.dev/cli/settings/set.html#VPContent)

On this page

# `mise settings set` [​](https://mise.jdx.dev/cli/settings/set.html\#mise-settings-set)

- **Usage:**`mise settings set [-l --local] <SETTING> [VALUE]`
- **Aliases:**`create`
- **Effect:** modifies state
- **Source code:** [`src/cli/settings/set.rs`](https://github.com/jdx/mise/blob/main/src/cli/settings/set.rs)

Add/update a setting

This modifies the contents of ~/.config/mise/config.toml by default. With `--local`, modifies the local config file instead. See [https://mise.jdx.dev/configuration.html#target-file-for-write-operations](https://mise.jdx.dev/configuration.html#target-file-for-write-operations)

## Arguments [​](https://mise.jdx.dev/cli/settings/set.html\#arguments)

- **`<SETTING>`** — The setting to set
- **`[VALUE]`** — The value to set (optional if provided as KEY=VALUE)

## Flags [​](https://mise.jdx.dev/cli/settings/set.html\#flags)

- **`-l --local`** — Use the local config file instead of the global one
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/settings/set.html\#examples)

```
mise settings set jobs 4
```

## Related documentation [​](https://mise.jdx.dev/cli/settings/set.html\#related-documentation)

- [Settings reference](https://mise.jdx.dev/configuration/settings.html).
- [`mise settings [FLAGS] [SETTING] [VALUE] [SUBCOMMAND]`](https://mise.jdx.dev/cli/settings.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)