[Skip to content](https://mise.jdx.dev/cli/bootstrap/repos.html#VPContent)

On this page

# `mise bootstrap repos` [​](https://mise.jdx.dev/cli/bootstrap/repos.html\#mise-bootstrap-repos)

- **Usage:**`mise bootstrap repos <SUBCOMMAND>`
- **Effect:** read-only
- **Source code:** [`src/cli/bootstrap.rs`](https://github.com/jdx/mise/blob/main/src/cli/bootstrap.rs)

Manage git repo checkouts from `[bootstrap.repos]`

Use `apply` to clone or reconcile the configured checkout, `update` to refresh it, and `exec` to run a command in selected repositories. Existing local changes can block convergence; `--skip-dirty` skips those repositories without discarding edits.

## Flags [​](https://mise.jdx.dev/cli/bootstrap/repos.html\#flags)

- **`-h --help`** — Print help

## Subcommands [​](https://mise.jdx.dev/cli/bootstrap/repos.html\#subcommands)

- [`mise bootstrap repos apply [FLAGS]`](https://mise.jdx.dev/cli/bootstrap/repos/apply.html)
- [`mise bootstrap repos exec [-c --continue-on-error] [-n --dry-run] [PATH]… <-- COMMAND>…`](https://mise.jdx.dev/cli/bootstrap/repos/exec.html)
- [`mise bootstrap repos status [-J --json] [--missing]`](https://mise.jdx.dev/cli/bootstrap/repos/status.html)
- [`mise bootstrap repos update [FLAGS] [PATH]…`](https://mise.jdx.dev/cli/bootstrap/repos/update.html)

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/repos.html\#related-documentation)

- [Repository checkouts](https://mise.jdx.dev/bootstrap/repos.html).
- [`mise bootstrap [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/bootstrap.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)