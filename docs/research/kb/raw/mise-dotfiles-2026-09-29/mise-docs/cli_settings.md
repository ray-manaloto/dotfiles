[Skip to content](https://mise.jdx.dev/cli/settings.html#VPContent)

On this page

# `mise settings` [​](https://mise.jdx.dev/cli/settings.html\#mise-settings)

- **Usage:**`mise settings [FLAGS] [SETTING] [VALUE] [SUBCOMMAND]`
- **Effect:** modifies state
- **Source code:** [`src/cli/settings/mod.rs`](https://github.com/jdx/mise/blob/main/src/cli/settings/mod.rs)

Manage settings

## Arguments [​](https://mise.jdx.dev/cli/settings.html\#arguments)

- **`[SETTING]`** — Name of setting
- **`[VALUE]`** — Setting value to set

## Global Flags [​](https://mise.jdx.dev/cli/settings.html\#global-flags)

- **`-l --local`** — Use the local config file instead of the global one

## Flags [​](https://mise.jdx.dev/cli/settings.html\#flags)

- **`-a --all`** — List all settings
- **`-J --json`** — Output in JSON format
- **`-T --toml`** — Output in TOML format
- **`--json-extended`** — Output in JSON format with sources
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/settings.html\#examples)

list explicitly configured settings

```
mise settings
```

get the value of the setting "always\_keep\_download"

```
mise settings always_keep_download
```

set the value of the setting "always\_keep\_download" to "true"

```
mise settings always_keep_download=true
```

set the value of the setting "node.mirror\_url" to " [https://npmmirror.com/mirrors/node/](https://npmmirror.com/mirrors/node/)"

```
mise settings node.mirror_url https://npmmirror.com/mirrors/node/
```

## Subcommands [​](https://mise.jdx.dev/cli/settings.html\#subcommands)

- [`mise settings add [-l --local] <SETTING> [VALUE]`](https://mise.jdx.dev/cli/settings/add.html)
- [`mise settings get [-l --local] <SETTING>`](https://mise.jdx.dev/cli/settings/get.html)
- [`mise settings ls [FLAGS] [SETTING]`](https://mise.jdx.dev/cli/settings/ls.html)
- [`mise settings set [-l --local] <SETTING> [VALUE]`](https://mise.jdx.dev/cli/settings/set.html)
- [`mise settings unset [-l --local] <KEY>`](https://mise.jdx.dev/cli/settings/unset.html)

## Related documentation [​](https://mise.jdx.dev/cli/settings.html\#related-documentation)

- [Settings reference](https://mise.jdx.dev/configuration/settings.html).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)