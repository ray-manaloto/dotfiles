[Skip to content](https://mise.jdx.dev/cli/bootstrap/services/remove.html#VPContent)

On this page

# `mise bootstrap services remove` [​](https://mise.jdx.dev/cli/bootstrap/services/remove.html\#mise-bootstrap-services-remove)

- **Usage:**`mise bootstrap services remove [-n --dry-run] <NAME>`
- **Effect:** destructive — may delete or irreversibly overwrite
- **Source code:** [`src/cli/bootstrap.rs`](https://github.com/jdx/mise/blob/main/src/cli/bootstrap.rs)

Remove an installed user-scope service, declared or not

Deleting a `scope = "user"` declaration leaves its installed unit, agent, or task in place; this removes it once. The next `mise bootstrap` recreates it if it is still declared.

## Arguments [​](https://mise.jdx.dev/cli/bootstrap/services/remove.html\#arguments)

- **`<NAME>`** — The installed user-service name to remove (declared or not)

## Flags [​](https://mise.jdx.dev/cli/bootstrap/services/remove.html\#flags)

- **`-n --dry-run`** — Print what would change without changing anything
- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/services/remove.html\#related-documentation)

- [System services](https://mise.jdx.dev/bootstrap/services.html).
- [`mise bootstrap services <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/services.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)