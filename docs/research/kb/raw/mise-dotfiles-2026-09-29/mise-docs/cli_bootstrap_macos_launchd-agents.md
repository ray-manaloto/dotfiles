[Skip to content](https://mise.jdx.dev/cli/bootstrap/macos/launchd-agents.html#VPContent)

On this page

# `mise bootstrap macos launchd-agents` [​](https://mise.jdx.dev/cli/bootstrap/macos/launchd-agents.html\#mise-bootstrap-macos-launchd-agents)

- **Usage:**`mise bootstrap macos launchd-agents <SUBCOMMAND>`
- **Aliases:**`launchd`
- **Effect:** read-only
- **Source code:** [`src/cli/bootstrap.rs`](https://github.com/jdx/mise/blob/main/src/cli/bootstrap.rs)

Manage macOS LaunchAgents from `[bootstrap.macos.launchd.agents]`

Installs plist files and reconciles agents in the current GUI login domain. Run from the intended user session; an SSH-only session may not have that domain.

## Flags [​](https://mise.jdx.dev/cli/bootstrap/macos/launchd-agents.html\#flags)

- **`-h --help`** — Print help

## Subcommands [​](https://mise.jdx.dev/cli/bootstrap/macos/launchd-agents.html\#subcommands)

- [`mise bootstrap macos launchd-agents apply [-n --dry-run] [-y --yes]`](https://mise.jdx.dev/cli/bootstrap/macos/launchd-agents/apply.html)
- [`mise bootstrap macos launchd-agents status [-J --json] [--missing]`](https://mise.jdx.dev/cli/bootstrap/macos/launchd-agents/status.html)

## Related documentation [​](https://mise.jdx.dev/cli/bootstrap/macos/launchd-agents.html\#related-documentation)

- [LaunchAgents](https://mise.jdx.dev/bootstrap/launchd.html).
- [`mise bootstrap macos <SUBCOMMAND>`](https://mise.jdx.dev/cli/bootstrap/macos.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)