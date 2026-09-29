[Skip to content](https://mise.jdx.dev/cli/bootstrap/status.html#VPContent)

On this page

# `mise bootstrap status` [​](https://mise.jdx.dev/cli/bootstrap/status.html\#mise-bootstrap-status)

- **Usage:**`mise bootstrap status [FLAGS]`
- **Aliases:**`ls`
- **Effect:** read-only
- **Source code:** [`src/cli/bootstrap.rs`](https://github.com/jdx/mise/blob/main/src/cli/bootstrap.rs)

Show the aggregate bootstrap status

Inspect configured resource state without applying changes. `--missing` sets a nonzero exit status for drift; it does not restrict the listing to missing entries. Dotfile status can render trusted templates, including their `exec()` calls.

## Flags [​](https://mise.jdx.dev/cli/bootstrap/status.html\#flags)

- **`-J --json`** — Output in JSON format
- **`--missing`** — Exit with code 1 if any configured bootstrap state is not in its desired state
- **`--prompt-secrets`** — Prompt securely for missing bootstrap secret inputs
- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/status.html\#related-documentation)

- [Bootstrap workflow](https://mise.jdx.dev/bootstrap.html).
- [`mise bootstrap [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/bootstrap.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)