[Skip to content](https://mise.jdx.dev/cli/settings/get.html#VPContent)

On this page

# `mise settings get` [​](https://mise.jdx.dev/cli/settings/get.html\#mise-settings-get)

- **Usage:**`mise settings get [-l --local] <SETTING>`
- **Effect:** read-only
- **Source code:** [`src/cli/settings/get.rs`](https://github.com/jdx/mise/blob/main/src/cli/settings/get.rs)

Show the effective value of a setting

Includes defaults, configuration, and environment overrides. With `--local`, read only the selected local config's explicit settings; an unset key is an error. Use `mise config get settings.KEY --file path/to/mise.toml` to inspect one file.

## Arguments [​](https://mise.jdx.dev/cli/settings/get.html\#arguments)

- **`<SETTING>`** — The setting to show

## Flags [​](https://mise.jdx.dev/cli/settings/get.html\#flags)

- **`-l --local`** — Use the local config file instead of the global one
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/settings/get.html\#examples)

```
mise settings get jobs
mise settings get python.compile
```

## Related documentation [​](https://mise.jdx.dev/cli/settings/get.html\#related-documentation)

- [Settings reference](https://mise.jdx.dev/configuration/settings.html).
- [`mise settings [FLAGS] [SETTING] [VALUE] [SUBCOMMAND]`](https://mise.jdx.dev/cli/settings.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)