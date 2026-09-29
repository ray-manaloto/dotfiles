[Skip to content](https://mise.jdx.dev/cli/fmt.html#VPContent)

On this page

# `mise fmt` [​](https://mise.jdx.dev/cli/fmt.html\#mise-fmt)

- **Usage:**`mise fmt [FLAGS]`
- **Effect:** modifies state
- **Source code:** [`src/cli/fmt.rs`](https://github.com/jdx/mise/blob/main/src/cli/fmt.rs)

Format mise TOML configuration

Sorts keys and normalizes whitespace using TOML 1.1 syntax, including multiline inline tables. Lists whose order carries no meaning are sorted as well: task `sources` and `outputs`, `task_config.global_inputs` and `input_groups`, and `redactions`. File pattern lists sort by reach — `@group:` references, then globs, then literal paths — and a list is left as written when an entry excludes with `!` or carries a comment. By default, formats config files in the current directory; `--all` includes every loaded config. Use `--check` in CI or `--stdin` to format a supplied document without rewriting a file.

## Flags [​](https://mise.jdx.dev/cli/fmt.html\#flags)

- **`-a --all`** — Format every config file mise currently loads, not just those in the current directory
- **`-c --check`** — Check whether the configs are formatted without rewriting them; exits 1 if any are not
- **`-s --stdin`** — Read config from stdin and write its formatted version into stdout
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/fmt.html\#examples)

```
mise fmt
mise fmt --check
cat mise.toml | mise fmt --stdin
```

## Related documentation [​](https://mise.jdx.dev/cli/fmt.html\#related-documentation)

- [Configuration](https://mise.jdx.dev/configuration.html).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)