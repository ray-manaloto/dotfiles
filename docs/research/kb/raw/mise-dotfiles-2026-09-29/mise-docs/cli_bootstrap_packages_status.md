[Skip to content](https://mise.jdx.dev/cli/bootstrap/packages/status.html#VPContent)

On this page

# `mise bootstrap packages status` [​](https://mise.jdx.dev/cli/bootstrap/packages/status.html\#mise-bootstrap-packages-status)

- **Usage:**`mise bootstrap packages status [-J --json] [--missing]`
- **Aliases:**`ls`
- **Effect:** read-only
- **Source code:** [`src/cli/system/status.rs`](https://github.com/jdx/mise/blob/main/src/cli/system/status.rs)

Show the status of system packages from `[bootstrap.packages]`

## Flags [​](https://mise.jdx.dev/cli/bootstrap/packages/status.html\#flags)

- **`-J --json`** — Output in JSON format
- **`--missing`** — Exit with code 1 if any configured packages are not in their desired state
- **`-h --help`** — Print help

## Examples [​](https://mise.jdx.dev/cli/bootstrap/packages/status.html\#examples)

```
mise bootstrap packages status
mise bootstrap packages status --json
mise bootstrap packages status --missing # exit 1 if anything is out of sync
```

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/packages/status.html\#related-documentation)

- [Host packages](https://mise.jdx.dev/bootstrap/packages/).
- [`mise bootstrap packages <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/packages.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)