[Skip to content](https://mise.jdx.dev/cli/bootstrap/repos/update.html#VPContent)

On this page

# `mise bootstrap repos update` [​](https://mise.jdx.dev/cli/bootstrap/repos/update.html\#mise-bootstrap-repos-update)

- **Usage:**`mise bootstrap repos update [FLAGS] [PATH]…`
- **Effect:** modifies state
- **Source code:** [`src/cli/bootstrap.rs`](https://github.com/jdx/mise/blob/main/src/cli/bootstrap.rs)

Pull the latest changes into configured git repos

## Arguments [​](https://mise.jdx.dev/cli/bootstrap/repos/update.html\#arguments)

- **`[PATH]…`** — Update only matching configured or expanded paths

## Flags [​](https://mise.jdx.dev/cli/bootstrap/repos/update.html\#flags)

- **`-n --dry-run`** — Print the commands that would run without running them
- **`-y --yes`** — Skip the confirmation prompt
- **`--skip-dirty`** — Skip repos with local changes instead of failing
- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/repos/update.html\#related-documentation)

- [Repository checkouts](https://mise.jdx.dev/bootstrap/repos.html).
- [`mise bootstrap repos <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/repos.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)