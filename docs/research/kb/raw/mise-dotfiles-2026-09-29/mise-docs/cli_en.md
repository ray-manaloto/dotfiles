[Skip to content](https://mise.jdx.dev/cli/en.html#VPContent)

On this page

# `mise en` [​](https://mise.jdx.dev/cli/en.html\#mise-en)

- **Usage:**`mise en [-s --shell <SHELL>] [DIR]`
- **Source code:** [`src/cli/en.rs`](https://github.com/jdx/mise/blob/main/src/cli/en.rs)

Start a new shell with the mise environment built from the current configuration

This is an alternative to `mise activate` for starting a mise session explicitly. The new shell has the tools and environment variables from the config loaded. Unlike an activated shell, changing directories does not update the environment.

## Arguments [​](https://mise.jdx.dev/cli/en.html\#arguments)

- **`[DIR]`** — Directory to start the shell in

**Default:**`.`


## Flags [​](https://mise.jdx.dev/cli/en.html\#flags)

- **`-s --shell <SHELL>`** — Shell to start

Defaults to $SHELL

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/en.html\#examples)

Start a shell and check node. Example output: `v20.0.0`.

```
mise en .
node -v
```

Skip loading bashrc.

```
mise en -s "bash --norc"
```

Skip loading zshrc.

```
mise en -s "zsh -f"
```

## Related documentation [​](https://mise.jdx.dev/cli/en.html\#related-documentation)

- [Shell activation](https://mise.jdx.dev/getting-started.html#activate-mise).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)