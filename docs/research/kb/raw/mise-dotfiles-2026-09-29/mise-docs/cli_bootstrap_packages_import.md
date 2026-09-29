[Skip to content](https://mise.jdx.dev/cli/bootstrap/packages/import.html#VPContent)

On this page

# `mise bootstrap packages import` [​](https://mise.jdx.dev/cli/bootstrap/packages/import.html\#mise-bootstrap-packages-import)

- **Usage:**`mise bootstrap packages import [FLAGS]`
- **Effect:** modifies state
- **Source code:** [`src/cli/system/import.rs`](https://github.com/jdx/mise/blob/main/src/cli/system/import.rs)

Import installed system packages into `[bootstrap.packages]`

Currently supports Homebrew formulae only. By default, imports linked formulae whose active keg receipt says they were installed on request. Pass `--all` to import every linked formula, including dependencies.

## Flags [​](https://mise.jdx.dev/cli/bootstrap/packages/import.html\#flags)

- **`-e --env <ENV>`** — Write to the config file for this environment (mise.<ENV>.toml)

- **`-g --global`** — Write to the global config (~/.config/mise/config.toml)

- **`-m --manager <MANAGER>`** — Only import packages for this manager. Currently only `brew` is supported.

**Choices:**`brew`

**Default:**`brew`

- **`--all`** — Import every linked formula, including dependencies

- **`-n --dry-run`** — Print the config change without writing config

- **`-p --path <PATH>`** — Write to this config file or directory

**Aliases:**`--file`

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/bootstrap/packages/import.html\#examples)

```
mise bootstrap packages import --manager brew
mise bootstrap packages import --manager brew --all
mise bootstrap packages import --manager brew --global
mise bootstrap packages import --manager brew --dry-run
```

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/packages/import.html\#related-documentation)

- [Host packages](https://mise.jdx.dev/bootstrap/packages/).
- [`mise bootstrap packages <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/packages.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)