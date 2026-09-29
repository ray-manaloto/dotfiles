[Skip to content](https://mise.jdx.dev/cli/bootstrap/packages/prune.html#VPContent)

On this page

# `mise bootstrap packages prune` [​](https://mise.jdx.dev/cli/bootstrap/packages/prune.html\#mise-bootstrap-packages-prune)

- **Usage:**`mise bootstrap packages prune [FLAGS]`
- **Effect:** destructive — may delete or irreversibly overwrite
- **Source code:** [`src/cli/system/prune.rs`](https://github.com/jdx/mise/blob/main/src/cli/system/prune.rs)

Prune installed system packages no longer declared in `[bootstrap.packages]`

Supports Homebrew formulae, conservatively removable mise-owned casks, and packages installed by package plugins that implement `PackageUninstall`. Pruning keeps packages needed by the current config or by trusted, loadable tracked configs. Plugin packages that were already installed before mise first applied them are never claimed or removed.

## Flags [​](https://mise.jdx.dev/cli/bootstrap/packages/prune.html\#flags)

- **`-m --manager <MANAGER>`** — Only prune packages for this manager

**Default:**`brew`

- **`-n --dry-run`** — Print what would be removed without deleting anything

- **`-y --yes`** — Skip the confirmation prompt

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/bootstrap/packages/prune.html\#examples)

```
mise bootstrap packages prune --manager brew
mise bootstrap packages prune --manager brew --dry-run
mise bootstrap packages prune --manager brew --yes
mise bootstrap packages prune --manager brew-cask --dry-run
mise bootstrap packages prune --manager vscode --dry-run
```

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/packages/prune.html\#related-documentation)

- [Host packages](https://mise.jdx.dev/bootstrap/packages/).
- [`mise bootstrap packages <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/packages.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)