[Skip to content](https://mise.jdx.dev/cli/dotfiles/status.html#VPContent)

On this page

# `mise dotfiles status` [​](https://mise.jdx.dev/cli/dotfiles/status.html\#mise-dotfiles-status)

- **Usage:**`mise dotfiles status [FLAGS] [TARGET]…`
- **Aliases:**`ls`
- **Effect:** read-only
- **Source code:** [`src/cli/dotfiles/status.rs`](https://github.com/jdx/mise/blob/main/src/cli/dotfiles/status.rs)

Show the status of dotfiles from `[dotfiles]`

Template entries are rendered to compare their output; trusted template functions may execute. JSON includes each entry's origin and uses the states `applied`, `missing`, `differs`, `source_missing`, and `tracked`.

The management state of every declaration (applied, missing, differs, tracked) followed by the history state: what is tracked, the latest checkpoint, unfinished operations, and whether edits are saved automatically.

## Arguments [​](https://mise.jdx.dev/cli/dotfiles/status.html\#arguments)

- **`[TARGET]…`** — Only show these targets

## Flags [​](https://mise.jdx.dev/cli/dotfiles/status.html\#flags)

- **`--truncate`** — Truncate long terminal output to fit the available width

**Default:**`true`

- **`-J --json`** — Output in JSON format

- **`--missing`** — Exit with code 1 if any configured dotfiles are not in their desired state (missing, source missing, differs)

- **`--prompt-secrets`** — Prompt securely for missing bootstrap secret inputs

- **`-h --help`** — Print help


## Examples [​](https://mise.jdx.dev/cli/dotfiles/status.html\#examples)

```
mise dot status
mise dot status ~/.zshrc
mise dot status --json
mise dot status --missing # exit 1 if anything is out of sync
```

## Related documentation [​](https://mise.jdx.dev/cli/dotfiles/status.html\#related-documentation)

- [Getting started](https://mise.jdx.dev/getting-started.html).
- [`mise dotfiles <SUBCOMMAND>`](https://mise.jdx.dev/cli/dotfiles.html).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)