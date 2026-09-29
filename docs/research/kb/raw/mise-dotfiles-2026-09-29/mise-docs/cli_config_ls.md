[Skip to content](https://mise.jdx.dev/cli/config/ls.html#VPContent)

On this page

# `mise config ls` [​](https://mise.jdx.dev/cli/config/ls.html\#mise-config-ls)

- **Usage:**`mise config ls [FLAGS]`
- **Aliases:**`list`
- **Effect:** read-only
- **Source code:** [`src/cli/config/ls.rs`](https://github.com/jdx/mise/blob/main/src/cli/config/ls.rs)

List config files currently in use

## Flags [​](https://mise.jdx.dev/cli/config/ls.html\#flags)

- **`--truncate`** — Truncate long terminal output to fit the available width

**Default:**`true`

- **`-J --json`** — Output in JSON format

- **`--no-header`** — Do not print table header

- **`--tracked-configs`** — List all tracked config files

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/config/ls.html\#examples)

```
mise config ls
Path                        Tools
~/.config/mise/config.toml  pitchfork
~/src/mise/mise.toml        bun, cargo-binstall, cargo:cargo-insta
```

## Related documentation [​](https://mise.jdx.dev/cli/config/ls.html\#related-documentation)

- [Configuration](https://mise.jdx.dev/configuration.html).
- [`mise config [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/config.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)