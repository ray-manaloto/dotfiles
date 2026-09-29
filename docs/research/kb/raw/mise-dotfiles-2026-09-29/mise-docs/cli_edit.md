[Skip to content](https://mise.jdx.dev/cli/edit.html#VPContent)

On this page

# `mise edit` [​](https://mise.jdx.dev/cli/edit.html\#mise-edit)

- **Usage:**`mise edit [FLAGS] [PATH]`
- **Effect:** modifies state
- **Source code:** [`src/cli/edit.rs`](https://github.com/jdx/mise/blob/main/src/cli/edit.rs)

Edit mise.toml interactively

## Arguments [​](https://mise.jdx.dev/cli/edit.html\#arguments)

- **`[PATH]`** — Path to the config file to create

## Flags [​](https://mise.jdx.dev/cli/edit.html\#flags)

- **`-g --global`** — Edit the global config file (~/.config/mise/config.toml)
- **`-n --dry-run`** — Show what would be generated without writing to file
- **`-t --tool-versions <TOOL_VERSIONS>`** — Path to a .tool-versions file to import tools from
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/edit.html\#examples)

```
mise edit             # edit mise.toml interactively
mise edit .mise.toml  # edit a specific file
mise edit -g          # edit the global config file
mise edit -y          # skip interactive editor
mise edit -n          # preview without writing
```

## Related documentation [​](https://mise.jdx.dev/cli/edit.html\#related-documentation)

- [Configuration](https://mise.jdx.dev/configuration.html).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)