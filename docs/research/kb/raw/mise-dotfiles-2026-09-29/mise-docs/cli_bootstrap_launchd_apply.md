[Skip to content](https://mise.jdx.dev/cli/bootstrap/launchd/apply.html#VPContent)

On this page

# `mise bootstrap launchd apply` [​](https://mise.jdx.dev/cli/bootstrap/launchd/apply.html\#mise-bootstrap-launchd-apply)

- **Usage:**`mise bootstrap launchd apply [-n --dry-run] [-y --yes]`
- **Effect:** modifies state
- **Source code:** [`src/cli/bootstrap.rs`](https://github.com/jdx/mise/blob/main/src/cli/bootstrap.rs)

Install and load LaunchAgents from `[bootstrap.macos.launchd.agents]`

## Flags [​](https://mise.jdx.dev/cli/bootstrap/launchd/apply.html\#flags)

- **`-n --dry-run`** — Print the commands that would run without running them
- **`-y --yes`** — Skip the confirmation prompt
- **`-h --help`** — Print help

This is a compatibility spelling. Use [`mise bootstrap macos launchd-agents apply [-n --dry-run] [-y --yes]`](https://mise.jdx.dev/cli/bootstrap/macos/launchd-agents/apply.html) in new scripts.

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/launchd/apply.html\#related-documentation)

- [LaunchAgents](https://mise.jdx.dev/bootstrap/launchd.html).
- [`mise bootstrap [FLAGS] [SUBCOMMAND]`](https://mise.jdx.dev/cli/bootstrap.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)