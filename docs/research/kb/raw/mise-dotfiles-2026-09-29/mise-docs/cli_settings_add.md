[Skip to content](https://mise.jdx.dev/cli/settings/add.html#VPContent)

On this page

# `mise settings add` [​](https://mise.jdx.dev/cli/settings/add.html\#mise-settings-add)

- **Usage:**`mise settings add [-l --local] <SETTING> [VALUE]`
- **Effect:** modifies state
- **Source code:** [`src/cli/settings/add.rs`](https://github.com/jdx/mise/blob/main/src/cli/settings/add.rs)

Append a value to an array setting

Adds the value to an array setting such as `disable_hints`, keeping existing entries. This modifies ~/.config/mise/config.toml by default, or the local config with `--local`.

## Arguments [​](https://mise.jdx.dev/cli/settings/add.html\#arguments)

- **`<SETTING>`** — The setting to set
- **`[VALUE]`** — The value to set (optional if provided as KEY=VALUE)

## Flags [​](https://mise.jdx.dev/cli/settings/add.html\#flags)

- **`-l --local`** — Use the local config file instead of the global one
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/settings/add.html\#examples)

```
mise settings add disable_hints python_multi
```

## Related documentation [​](https://mise.jdx.dev/cli/settings/add.html\#related-documentation)

- [Settings reference](https://mise.jdx.dev/configuration/settings.html).
- [`mise settings [FLAGS] [SETTING] [VALUE] [SUBCOMMAND]`](https://mise.jdx.dev/cli/settings.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)