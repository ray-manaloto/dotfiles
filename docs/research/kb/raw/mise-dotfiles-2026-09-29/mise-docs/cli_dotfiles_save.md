[Skip to content](https://mise.jdx.dev/cli/dotfiles/save.html#VPContent)

On this page

# `mise dotfiles save` [​](https://mise.jdx.dev/cli/dotfiles/save.html\#mise-dotfiles-save)

- **Usage:**`mise dotfiles save [FLAGS] [PATH]…`
- **Effect:** modifies state
- **Source code:** [`src/cli/dotfiles/save.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/save.rs)

Save a checkpoint of the tracked files now

Fails when history cannot save or a requested path is not tracked, so a script or an agent gets a trustworthy result; a save that finds nothing changed succeeds as a no-op. `--best-effort` turns save errors into a warning for `set -e` update scripts.

## Arguments [​](https://mise.jdx.dev/cli/dotfiles/save.html\#arguments)

- **`[PATH]…`** — Paths to save; every one must be tracked

## Flags [​](https://mise.jdx.dev/cli/dotfiles/save.html\#flags)

- **`-d --description <TEXT>`** — A description for the checkpoint

- **`--trigger <TRIGGER>`** — What is saving: save (the default), agent, or update

**Default:**`save`

- **`--task <ID>`** — The task an agent is working on

- **`--label <LABEL>`** — A label to find the checkpoint by later

- **`--best-effort`** — Warn instead of failing when history cannot save

- **`-h --help`** — Print help


## Related documentation [​](https://mise.jdx.dev/cli/dotfiles/save.html\#related-documentation)

- [Getting started](https://mise.jdx.dev/getting-started.html).
- [`mise dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)