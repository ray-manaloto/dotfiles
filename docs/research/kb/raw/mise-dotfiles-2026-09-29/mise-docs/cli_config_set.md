[Skip to content](https://mise.jdx.dev/cli/config/set.html#VPContent)

On this page

# `mise config set` [​](https://mise.jdx.dev/cli/config/set.html\#mise-config-set)

- **Usage:**`mise config set [FLAGS] <KEY> [VALUE]`
- **Effect:** modifies state
- **Source code:** [`src/cli/config/set.rs`](https://github.com/jdx/mise/blob/main/src/cli/config/set.rs)

Set a value in one mise TOML file

Edits the highest-precedence loaded TOML file by default, which may be an environment-specific override. Use `--file` to select an existing project file, or `--global`/`--system` to edit or create those config files.

This edits configuration without installing tools. Use `mise use` to install and select a version together. Known settings use their declared type; other values are strings or booleans unless `--type` is given. Use `--type string` when a value such as `true` should remain literal text.

## Arguments [​](https://mise.jdx.dev/cli/config/set.html\#arguments)

- **`<KEY>`** — Dotted key path to set, e.g. `tools.python`
- **`[VALUE]`** — The value to set the key to (optional if provided as KEY=VALUE)

## Flags [​](https://mise.jdx.dev/cli/config/set.html\#flags)

- **`-f --file <FILE>`** — The path to the mise.toml file to edit

Can be a file path or directory. If a directory is provided, the config file in that directory is used.

If not provided, the highest-precedence loaded TOML file is used

**Aliases:**`--path`

- **`-g --global`** — Edit the global config file.

- **`--system`** — Edit the system config file.

- **`--append`** — Append the value without duplicating an existing entry.

- **`--remove`** — Remove the value from an existing collection.

- **`-t --type <TYPE>`** — TOML type to store the value as; inferred from the value by default

**Choices:**`infer`, `string`, `integer`, `float`, `bool`, `list`, `set`

**Default:**`infer`

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/config/set.html\#examples)

```
mise config set tools.python 3.12
mise config set settings.always_keep_download true
mise config set env.TEST_ENV_VAR ABC
mise config set settings.disable_tools node,rust
mise config set --append env._.path ~/.local/bin
mise config set --remove env._.path ~/.local/bin
```

Type for `settings` is inferred

```
mise config set settings.jobs 4
```

## Related documentation [​](https://mise.jdx.dev/cli/config/set.html\#related-documentation)

- [Configuration](https://mise.jdx.dev/configuration.html).
- [`mise config [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/config.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)