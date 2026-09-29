[Skip to content](https://mise.jdx.dev/cli/settings/ls.html#VPContent)

On this page

# `mise settings ls` [​](https://mise.jdx.dev/cli/settings/ls.html\#mise-settings-ls)

- **Usage:**`mise settings ls [FLAGS] [SETTING]`
- **Aliases:**`list`
- **Effect:** read-only
- **Source code:** [`src/cli/settings/ls.rs`](https://github.com/jdx/mise/blob/main/src/cli/settings/ls.rs)

List configured settings and their sources

By default, list explicit settings from loaded TOML files. `--all` also includes effective defaults. Use `--local` to restrict output to the selected local file, and `--json-extended` to include source information in machine-readable output. Use `mise settings get KEY` when you need one effective value.

## Arguments [​](https://mise.jdx.dev/cli/settings/ls.html\#arguments)

- **`[SETTING]`** — Name of setting

## Flags [​](https://mise.jdx.dev/cli/settings/ls.html\#flags)

- **`-a --all`** — List all settings
- **`-J --json`** — Output in JSON format
- **`-l --local`** — Use the local config file instead of the global one
- **`-T --toml`** — Output in TOML format
- **`--json-extended`** — Output in JSON format with sources
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/settings/ls.html\#examples)

```
mise settings ls
mise settings ls --all
mise settings ls python --json-extended
```

## Related documentation [​](https://mise.jdx.dev/cli/settings/ls.html\#related-documentation)

- [Settings reference](https://mise.jdx.dev/configuration/settings.html).
- [`mise settings [FLAGS] [SETTING] [VALUE] [SUBCOMMAND]`](https://mise.jdx.dev/cli/settings.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)