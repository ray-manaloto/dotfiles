[Skip to content](https://mise.jdx.dev/cli/config/get.html#VPContent)

On this page

# `mise config get` [​](https://mise.jdx.dev/cli/config/get.html\#mise-config-get)

- **Usage:**`mise config get [FLAGS] [KEY]`
- **Effect:** read-only
- **Source code:** [`src/cli/config/get.rs`](https://github.com/jdx/mise/blob/main/src/cli/config/get.rs)

Display a value from one mise TOML file

Reads the highest-precedence loaded TOML file by default. Select another with `--file`, `--global`, or `--system`. This reads stored values, not the merged or template-expanded environment; use `mise env` for the resolved environment.

## Arguments [​](https://mise.jdx.dev/cli/config/get.html\#arguments)

- **`[KEY]`** — Dotted key path to display, e.g. `tools.python`; omit to print the whole file

## Flags [​](https://mise.jdx.dev/cli/config/get.html\#flags)

- **`-f --file <FILE>`** — The path to the mise.toml file to read

Can be a file path or directory. If a directory is provided, the config file in that directory is used.

If not provided, the highest-precedence loaded TOML file is used

**Aliases:**`--path`

- **`-g --global`** — Read the global config file.

- **`--system`** — Read the system config file.

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/config/get.html\#examples)

```
mise config get tools.python
3.12
```

## Related documentation [​](https://mise.jdx.dev/cli/config/get.html\#related-documentation)

- [Configuration](https://mise.jdx.dev/configuration.html).
- [`mise config [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/config.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)