[Skip to content](https://mise.jdx.dev/cli/generate/config.html#VPContent)

On this page

# `mise generate config` [​](https://mise.jdx.dev/cli/generate/config.html\#mise-generate-config)

- **Usage:**`mise generate config [FLAGS] [PATH]`
- **Effect:** modifies state
- **Source code:** [`src/cli/generate/config.rs`](https://github.com/jdx/mise/blob/main/src/cli/generate/config.rs)

Generate a mise.toml file

## Arguments [​](https://mise.jdx.dev/cli/generate/config.html\#arguments)

- **`[PATH]`** — Path to the config file to create

## Flags [​](https://mise.jdx.dev/cli/generate/config.html\#flags)

- **`-g --global`** — Generate the global config file (~/.config/mise/config.toml)
- **`-n --dry-run`** — Show what would be generated without writing to file
- **`-t --tool-versions <TOOL_VERSIONS>`** — Path to a .tool-versions file to import tools from
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/generate/config.html\#examples)

```
mise generate config             # generate mise.toml interactively
mise generate config .mise.toml  # generate a specific file
mise generate config -g          # generate the global config file
mise generate config -y          # skip interactive editor
mise generate config -n          # preview without writing
```

## Related documentation [​](https://mise.jdx.dev/cli/generate/config.html\#related-documentation)

- [Configuration](https://mise.jdx.dev/configuration.html).
- [`mise generate <SUBCOMMAND>`](https://mise.jdx.dev/cli/generate.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)